"""Assemble profiling, cleaning, and visualization data into a report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from models.enums import ChartType
from models.schemas import (
    CleaningReport,
    DataProfile,
    ReportChart,
    ReportData,
)
from services import file_manager
from services.insights import derive_key_findings, generate_alerts
from services.profiler import profile_dataframe
from services.visualization.chart_selector import select_charts
from services.visualization.matplotlib_gen import generate_matplotlib_base64

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


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

    # Generate charts as base64 PNGs
    recommendations = select_charts(profile, df)
    charts: list[ReportChart] = []
    for rec in recommendations:
        image_b64 = generate_matplotlib_base64(rec, df)
        charts.append(ReportChart(
            title=rec.title,
            description=rec.description,
            chart_type=rec.chart_type,
            image_base64=image_b64,
        ))

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
    )


def render_html(report: ReportData) -> str:
    template = _jinja_env.get_template("report.html.j2")
    return template.render(report=report)


def render_pdf(html: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=html).write_pdf()


def _load_cleaning_report(session_id: str) -> CleaningReport | None:
    session = file_manager.get_session(session_id)
    return session.get("cleaning_report")
