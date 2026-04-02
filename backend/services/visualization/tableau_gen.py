import zipfile
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from models.enums import ChartType, ColumnType
from models.schemas import ChartRecommendation, DataProfile
from services import file_manager

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "tableau_templates"

TABLEAU_TYPE_MAP = {
    ColumnType.NUMERIC: ("real", "measure", "quantitative"),
    ColumnType.CATEGORICAL: ("string", "dimension", "nominal"),
    ColumnType.DATETIME: ("datetime", "dimension", "ordinal"),
    ColumnType.TEXT: ("string", "dimension", "nominal"),
    ColumnType.BOOLEAN: ("boolean", "dimension", "nominal"),
}

CHART_TEMPLATE_MAP = {
    ChartType.HISTOGRAM: "worksheet_histogram.xml.j2",
    ChartType.BAR: "worksheet_bar.xml.j2",
    ChartType.SCATTER: "worksheet_scatter.xml.j2",
    ChartType.LINE: "worksheet_line.xml.j2",
    ChartType.HEATMAP: "worksheet_heatmap.xml.j2",
    ChartType.GROUPED_BAR: "worksheet_bar.xml.j2",
    ChartType.BOX: "worksheet_bar.xml.j2",
    ChartType.TREEMAP: "worksheet_treemap.xml.j2",
    ChartType.BUBBLE: "worksheet_scatter.xml.j2",
    ChartType.WATERFALL: "worksheet_bar.xml.j2",
}


def generate_tableau_package(
    df: pd.DataFrame,
    profile: DataProfile,
    charts: list[ChartRecommendation],
    session_id: str,
) -> str | None:
    try:
        session_path = file_manager.session_dir(session_id)
        hyper_path = session_path / "extract.hyper"
        twb_path = session_path / "workbook.twb"
        zip_path = session_path / "tableau_export.zip"

        # Generate .hyper file
        _build_hyper(df, str(hyper_path))

        # Generate .twb file
        _build_twb(profile, charts, "extract.hyper", str(twb_path))

        # ZIP them together
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(hyper_path, "extract.hyper")
            zf.write(twb_path, "workbook.twb")

        return str(zip_path)
    except Exception:
        return None


def _build_hyper(df: pd.DataFrame, output_path: str) -> None:
    try:
        import pantab

        pantab.frame_to_hyper(df, output_path, table="Extract")
    except ImportError:
        # pantab not installed — write CSV as fallback
        csv_path = output_path.replace(".hyper", ".csv")
        df.to_csv(csv_path, index=False)


def _build_twb(
    profile: DataProfile,
    charts: list[ChartRecommendation],
    hyper_filename: str,
    output_path: str,
) -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )

    columns_meta = []
    for col in profile.columns:
        datatype, role, field_type = TABLEAU_TYPE_MAP.get(
            col.inferred_type, ("string", "dimension", "nominal")
        )
        columns_meta.append(
            {
                "name": col.name,
                "datatype": datatype,
                "role": role,
                "field_type": field_type,
            }
        )

    worksheets_xml: list[str] = []
    for i, chart in enumerate(charts):
        template_name = CHART_TEMPLATE_MAP.get(chart.chart_type)
        if not template_name:
            continue
        try:
            ws_tpl = env.get_template(template_name)
            ws_xml = ws_tpl.render(
                chart=chart,
                columns=columns_meta,
                worksheet_name=f"Sheet {i + 1} - {chart.title[:30]}",
            )
            worksheets_xml.append(ws_xml)
        except Exception:
            continue

    workbook_tpl = env.get_template("workbook.xml.j2")
    twb_content = workbook_tpl.render(
        hyper_filename=hyper_filename,
        columns=columns_meta,
        worksheets=worksheets_xml,
    )

    Path(output_path).write_text(twb_content, encoding="utf-8")
