import altair as alt
import pandas as pd

from models.enums import ChartType
from models.schemas import ChartRecommendation

# Disable max rows for Altair
alt.data_transformers.disable_max_rows()


def generate_vegalite(rec: ChartRecommendation, df: pd.DataFrame) -> dict:
    generators = {
        ChartType.HISTOGRAM: _histogram,
        ChartType.BAR: _bar,
        ChartType.SCATTER: _scatter,
        ChartType.LINE: _line,
        ChartType.HEATMAP: _heatmap,
        ChartType.GROUPED_BAR: _grouped_bar,
    }

    generator = generators.get(rec.chart_type)
    if not generator:
        return {}

    chart = generator(rec, df)
    return chart.to_dict()


def _histogram(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    col = rec.columns[0]
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            alt.X(col, bin=alt.Bin(maxbins=30), title=col),
            alt.Y("count()", title="Frequency"),
            tooltip=[alt.Tooltip(col, bin=alt.Bin(maxbins=30)), "count()"],
        )
        .properties(title=rec.title, width=400, height=300)
    )


def _bar(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    col = rec.columns[0]
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            alt.X(col, type="nominal", sort="-y", title=col),
            alt.Y("count()", title="Count"),
            tooltip=[col, "count()"],
        )
        .properties(title=rec.title, width=400, height=300)
    )


def _scatter(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    col_x, col_y = rec.columns[0], rec.columns[1]
    return (
        alt.Chart(df)
        .mark_circle(size=40, opacity=0.6)
        .encode(
            alt.X(col_x, type="quantitative", title=col_x),
            alt.Y(col_y, type="quantitative", title=col_y),
            tooltip=[col_x, col_y],
        )
        .properties(title=rec.title, width=400, height=300)
    )


def _line(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    dt_col, val_col = rec.columns[0], rec.columns[1]
    return (
        alt.Chart(df)
        .mark_line()
        .encode(
            alt.X(dt_col, type="temporal", title=dt_col),
            alt.Y(val_col, type="quantitative", title=val_col),
            tooltip=[dt_col, val_col],
        )
        .properties(title=rec.title, width=500, height=300)
    )


def _heatmap(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    numeric_df = df[rec.columns].apply(pd.to_numeric, errors="coerce")
    corr = numeric_df.corr().reset_index().melt(id_vars="index")
    corr.columns = ["Variable 1", "Variable 2", "Correlation"]

    return (
        alt.Chart(corr)
        .mark_rect()
        .encode(
            alt.X("Variable 1:N", title=""),
            alt.Y("Variable 2:N", title=""),
            alt.Color(
                "Correlation:Q",
                scale=alt.Scale(scheme="blueorange", domain=[-1, 1]),
            ),
            tooltip=["Variable 1", "Variable 2", "Correlation"],
        )
        .properties(title=rec.title, width=400, height=400)
    )


def _grouped_bar(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    cat_col, num_col = rec.columns[0], rec.columns[1]
    grouped = df.groupby(cat_col)[num_col].mean().reset_index()

    return (
        alt.Chart(grouped)
        .mark_bar()
        .encode(
            alt.X(cat_col, type="nominal", sort="-y", title=cat_col),
            alt.Y(num_col, type="quantitative", title=f"Average {num_col}"),
            tooltip=[cat_col, alt.Tooltip(num_col, format=".2f")],
        )
        .properties(title=rec.title, width=400, height=300)
    )
