"""Assemble profiling, cleaning, and visualization data into a journal-style report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from models.enums import ChartType
from models.schemas import (
    AIAnalysis,
    ChartRecommendation,
    CleaningReport,
    DataProfile,
    ReportChart,
    ReportData,
    ReportSection,
    StatisticalReport,
)
from services import file_manager
from services.insights import (
    derive_key_findings,
    generate_alerts,
    generate_data_overview_narrative,
    generate_executive_narrative,
    generate_section_narrative,
    generate_statistical_findings,
)
from services.profiler import profile_dataframe
from services.statistics import run_statistical_analysis
from services.visualization.chart_selector import select_charts
from services.visualization.matplotlib_gen import generate_matplotlib_base64
from services.visualization.plotly_gen import generate_plotly_base64

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


def _enum_value(val: object) -> str:
    return val.value if hasattr(val, "value") else str(val)


def _ai_insight_for(chart_title: str, ai_analysis: object) -> str:
    """Look up AI insight text for a chart by its title."""
    if not ai_analysis or not hasattr(ai_analysis, "chart_insights"):
        return ""
    for insight in ai_analysis.chart_insights:
        if insight.chart_title == chart_title:
            return insight.explanation
    return ""


_jinja_env.filters["enum_val"] = _enum_value
_jinja_env.globals["ai_insight_for"] = _ai_insight_for


# ---------------------------------------------------------------------------
# Section grouping
# ---------------------------------------------------------------------------

_SECTION_MAP = {
    ChartType.HISTOGRAM: "distributions",
    ChartType.BOX: "distributions",
    ChartType.VIOLIN: "distributions",
    ChartType.BAR: "distributions",
    ChartType.GROUPED_BAR: "distributions",
    ChartType.TREEMAP: "distributions",
    ChartType.SUNBURST: "distributions",
    ChartType.RADAR: "distributions",
    ChartType.WATERFALL: "distributions",
    ChartType.SCATTER: "relationships",
    ChartType.HEATMAP: "relationships",
    ChartType.SANKEY: "relationships",
    ChartType.BUBBLE: "relationships",
    ChartType.PARALLEL_COORDS: "relationships",
    ChartType.LINE: "temporal",
    ChartType.MISSING_MATRIX: "data_quality",
    ChartType.ANOMALY_SCATTER: "data_quality",
    ChartType.PCA_BIPLOT: "statistical_analysis",
    ChartType.CLUSTER_SCATTER: "statistical_analysis",
}

_SECTION_TITLES = {
    "distributions": "Distributions & Patterns",
    "relationships": "Relationships",
    "temporal": "Temporal Analysis",
    "data_quality": "Data Quality",
    "statistical_analysis": "Statistical Analysis",
}

_SECTION_ORDER = [
    "distributions", "relationships", "temporal",
    "statistical_analysis", "data_quality",
]


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

_PLOTLY_CHART_TYPES = {
    ChartType.TREEMAP, ChartType.SUNBURST, ChartType.SANKEY,
    ChartType.BUBBLE, ChartType.PARALLEL_COORDS, ChartType.RADAR,
    ChartType.WATERFALL, ChartType.PCA_BIPLOT, ChartType.CLUSTER_SCATTER,
    ChartType.ANOMALY_SCATTER,
}


def build_report(
    session_id: str,
    title: str = "Data Analysis Report",
) -> ReportData:
    session = file_manager.get_session(session_id)
    filename = session.get("filename", "unknown")

    df = file_manager.load_cleaned_df(session_id)
    profile = profile_dataframe(df)

    alerts = generate_alerts(profile, df)
    key_findings = derive_key_findings(profile, alerts, df)

    # Run statistical analysis
    stat_report = run_statistical_analysis(df, profile)
    stat_findings = generate_statistical_findings(stat_report)
    key_findings.extend(stat_findings)

    # Generate charts with interestingness filtering
    recommendations = select_charts(profile, df, stat_report)
    charts: list[ReportChart] = []
    for rec in recommendations:
        if rec.chart_type in _PLOTLY_CHART_TYPES:
            image_b64 = generate_plotly_base64(rec, df)
        else:
            image_b64 = generate_matplotlib_base64(rec, df)
        charts.append(ReportChart(
            title=rec.title,
            description=rec.description,
            chart_type=rec.chart_type,
            image_base64=image_b64,
            annotation=rec.annotation,
            reading_guide=rec.reading_guide,
        ))

    # Group charts into thematic sections
    sections = _assemble_sections(charts, recommendations, profile, df)

    # Generate narratives
    executive_narrative = generate_executive_narrative(profile, alerts, df)
    data_overview_narrative = generate_data_overview_narrative(profile, df)

    cleaning_report = _load_cleaning_report(session_id)
    ai_analysis = _load_ai_analysis(session_id)

    return ReportData(
        title=title,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        dataset_filename=filename,
        profile=profile,
        alerts=alerts,
        cleaning_report=cleaning_report,
        charts=charts,
        key_findings=key_findings,
        sections=sections,
        executive_narrative=executive_narrative,
        data_overview_narrative=data_overview_narrative,
        statistical_report=stat_report,
        ai_analysis=ai_analysis,
    )


def _assemble_sections(
    charts: list[ReportChart],
    recs: list[ChartRecommendation],
    profile: DataProfile,
    df: pd.DataFrame,
) -> list[ReportSection]:
    buckets: dict[str, list[ReportChart]] = {k: [] for k in _SECTION_ORDER}

    for chart, rec in zip(charts, recs):
        section_key = _SECTION_MAP.get(rec.chart_type, "distributions")
        buckets[section_key].append(chart)

    sections: list[ReportSection] = []
    for key in _SECTION_ORDER:
        if not buckets[key]:
            continue
        narrative = generate_section_narrative(key, buckets[key], profile, df)
        sections.append(ReportSection(
            id=key.replace("_", "-"),
            title=_SECTION_TITLES[key],
            narrative=narrative,
            charts=buckets[key],
        ))

    return sections


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_html(report: ReportData) -> str:
    template = _jinja_env.get_template("report.html.j2")
    return template.render(report=report)


def render_pdf_html(report: ReportData) -> str:
    """Render a simplified HTML designed for PDF conversion."""
    template = _jinja_env.get_template("report_pdf.html.j2")
    return template.render(report=report)


def render_pdf(html: str, report: ReportData | None = None) -> bytes:
    try:
        from weasyprint import HTML
        pdf_html = _inline_css_vars(html)
        return HTML(string=pdf_html).write_pdf()
    except (ImportError, OSError):
        # Fall back to xhtml2pdf with a dedicated simple template
        if report is not None:
            pdf_html = render_pdf_html(report)
        else:
            pdf_html = _inline_css_vars(html)
            pdf_html = _strip_unsupported_css_for_xhtml2pdf(pdf_html)
        import io
        from xhtml2pdf import pisa
        buf = io.BytesIO()
        pisa_status = pisa.CreatePDF(pdf_html, dest=buf)
        if pisa_status.err:
            raise RuntimeError("xhtml2pdf failed to generate PDF")
        buf.seek(0)
        return buf.read()


def _strip_unsupported_css_for_xhtml2pdf(html: str) -> str:
    """Strip CSS features that xhtml2pdf/reportlab cannot parse."""
    import re

    # ── Remove entire @-blocks that xhtml2pdf can't handle ──

    # :root block (already inlined by _inline_css_vars)
    html = re.sub(r":root\s*\{[^}]*\}", "", html)

    # @media blocks (print, max-width) — xhtml2pdf doesn't support them
    # and they contain properties (columns, grid, etc.) that crash it.
    html = _remove_balanced_blocks(html, r"@media\s*[^{]*\{")

    # @page — strip nested @-rules (e.g. @bottom-right) but keep outer
    html = _clean_page_blocks(html)

    # ── Remove unsupported CSS properties ──
    unsupported_props = [
        r"font-feature-settings",
        r"text-rendering",
        r"-webkit-font-smoothing",
        r"-moz-osx-font-smoothing",
        r"display\s*:\s*grid",
        r"display\s*:\s*inline-block",
        r"grid-template-columns",
        r"grid-column",
        r"column-span",
        r"column-gap",
        r"orphans",
        r"widows",
        r"transition",
    ]
    for prop in unsupported_props:
        html = re.sub(rf"\s*{prop}[^;]*;", "", html)

    # ── Remove HTML5 attributes ──
    html = re.sub(r'\s+loading="lazy"', "", html)

    return html


def _remove_balanced_blocks(html: str, pattern: str) -> str:
    """Remove balanced {}-blocks matching a regex pattern."""
    import re

    result = html
    for match in reversed(list(re.finditer(pattern, result))):
        start = match.start()
        brace_start = match.end() - 1
        depth = 0
        pos = brace_start
        while pos < len(result):
            if result[pos] == "{":
                depth += 1
            elif result[pos] == "}":
                depth -= 1
                if depth == 0:
                    break
            pos += 1
        result = result[:start] + result[pos + 1:]
    return result


def _clean_page_blocks(html: str) -> str:
    """Keep @page blocks but strip nested @-rules inside them."""
    import re

    result = html
    for match in list(re.finditer(r"@page\s*\{", html)):
        start = match.start()
        brace_start = match.end() - 1
        depth = 0
        pos = brace_start
        while pos < len(html):
            if html[pos] == "{":
                depth += 1
            elif html[pos] == "}":
                depth -= 1
                if depth == 0:
                    break
            pos += 1
        full_block = html[start : pos + 1]
        inner = html[brace_start + 1 : pos]
        cleaned_inner = re.sub(r"@[\w-]+\s*\{[^}]*\}", "", inner)
        result = result.replace(full_block, f"@page {{{cleaned_inner}}}")
    return result


_CSS_VARS = {
    # Brand
    "var(--accent)": "#0066FF",
    "var(--accent-muted)": "#4D94FF",
    "var(--accent-subtle)": "#EBF3FF",
    # Text hierarchy (warm slate)
    "var(--text-primary)": "#1D1D1F",
    "var(--text-secondary)": "#48484A",
    "var(--text-tertiary)": "#86868B",
    "var(--text-caption)": "#AEAEB2",
    # Surfaces
    "var(--bg)": "#FFFFFF",
    "var(--bg-elevated)": "#F5F5F7",
    "var(--bg-inset)": "#FAFAFA",
    # Borders
    "var(--border)": "#E8E8ED",
    "var(--border-light)": "#F2F2F7",
    # Semantic
    "var(--success)": "#34C759",
    "var(--success-bg)": "#F0FFF4",
    "var(--warning)": "#FF9500",
    "var(--warning-bg)": "#FFFBEB",
    "var(--warning-text)": "#92400E",
    "var(--danger)": "#FF3B30",
    "var(--danger-bg)": "#FFF5F5",
    "var(--danger-text)": "#9B1C1C",
    "var(--info-bg)": "#EBF3FF",
    "var(--info-text)": "#0066FF",
    # 8pt spatial scale
    "var(--s-4)": "4px",
    "var(--s-8)": "8px",
    "var(--s-12)": "12px",
    "var(--s-16)": "16px",
    "var(--s-24)": "24px",
    "var(--s-32)": "32px",
    "var(--s-48)": "48px",
    "var(--s-64)": "64px",
    "var(--s-96)": "96px",
    # Type scale (1.25 ratio)
    "var(--t-xs)": "12px",
    "var(--t-sm)": "13px",
    "var(--t-base)": "15px",
    "var(--t-md)": "16px",
    "var(--t-lg)": "20px",
    "var(--t-xl)": "25px",
    "var(--t-2xl)": "32px",
    "var(--t-3xl)": "40px",
    # Font stacks
    "var(--font-sans)": '"SF Pro Display", -apple-system, "Segoe UI", system-ui, "Helvetica Neue", sans-serif',
    "var(--font-text)": '"SF Pro Text", -apple-system, "Segoe UI", system-ui, "Helvetica Neue", sans-serif',
    "var(--font-mono)": '"SF Mono", "Cascadia Code", Consolas, "Fira Code", monospace',
    # Line heights (use % for xhtml2pdf compatibility — unitless floats crash it)
    "var(--lh-tight)": "130%",
    "var(--lh-normal)": "160%",
    "var(--lh-loose)": "180%",
    # Layout
    "var(--content-width)": "780px",
    "var(--reading-width)": "620px",
}


def _inline_css_vars(html: str) -> str:
    for var_ref, value in _CSS_VARS.items():
        html = html.replace(var_ref, value)
    return html


def _load_cleaning_report(session_id: str) -> CleaningReport | None:
    session = file_manager.get_session(session_id)
    return session.get("cleaning_report")


def _load_ai_analysis(session_id: str) -> AIAnalysis | None:
    session = file_manager.get_session(session_id)
    return session.get("ai_analysis")
