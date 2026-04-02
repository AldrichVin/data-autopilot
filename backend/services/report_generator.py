"""Assemble profiling, cleaning, and visualization data into a journal-style report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from models.enums import ChartType
from models.schemas import (
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


_jinja_env.filters["enum_val"] = _enum_value


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
        ))

    # Group charts into thematic sections
    sections = _assemble_sections(charts, recommendations, profile, df)

    # Generate narratives
    executive_narrative = generate_executive_narrative(profile, alerts, df)
    data_overview_narrative = generate_data_overview_narrative(profile, df)

    cleaning_report = _load_cleaning_report(session_id)

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


def render_pdf(html: str) -> bytes:
    pdf_html = _inline_css_vars(html)
    try:
        from weasyprint import HTML
        return HTML(string=pdf_html).write_pdf()
    except (ImportError, OSError):
        import io
        from xhtml2pdf import pisa
        buf = io.BytesIO()
        pisa_status = pisa.CreatePDF(pdf_html, dest=buf)
        if pisa_status.err:
            raise RuntimeError("xhtml2pdf failed to generate PDF")
        buf.seek(0)
        return buf.read()


_CSS_VARS = {
    "var(--primary)": "#2563eb",
    "var(--dark)": "#1a1a2e",
    "var(--text-secondary)": "#495057",
    "var(--text-tertiary)": "#6c757d",
    "var(--bg)": "#ffffff",
    "var(--bg-alt)": "#f8f9fa",
    "var(--bg-tertiary)": "#f1f3f5",
    "var(--border)": "#e9ecef",
    "var(--border-medium)": "#dee2e6",
    "var(--warning-bg)": "#fff3cd",
    "var(--warning-text)": "#856404",
    "var(--info-bg)": "#cfe2ff",
    "var(--info-text)": "#004085",
    "var(--danger-bg)": "#f8d7da",
    "var(--danger-text)": "#721c24",
    "var(--success)": "#198754",
    "var(--success-bg)": "#d1e7dd",
}


def _inline_css_vars(html: str) -> str:
    for var_ref, value in _CSS_VARS.items():
        html = html.replace(var_ref, value)
    return html


def _load_cleaning_report(session_id: str) -> CleaningReport | None:
    session = file_manager.get_session(session_id)
    return session.get("cleaning_report")
