import altair as alt
import pandas as pd

from models.enums import ChartType
from models.schemas import ChartRecommendation

alt.data_transformers.disable_max_rows()

PALETTE = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626", "#4f46e5", "#0284c7"]

_GENERATORS: dict[ChartType, object] = {}


def _register(chart_type: ChartType):
    def decorator(fn):
        _GENERATORS[chart_type] = fn
        return fn
    return decorator


def generate_vegalite(rec: ChartRecommendation, df: pd.DataFrame) -> dict:
    generator = _GENERATORS.get(rec.chart_type)
    if not generator:
        return {}
    chart = generator(rec, df)
    return chart.to_dict()


# ---------------------------------------------------------------------------
# Chart generators
# ---------------------------------------------------------------------------

@_register(ChartType.HISTOGRAM)
def _histogram(rec: ChartRecommendation, df: pd.DataFrame) -> alt.LayerChart:
    col = rec.columns[0]
    data = pd.to_numeric(df[col], errors="coerce").dropna()
    mean_val = float(data.mean())
    median_val = float(data.median())

    bars = (
        alt.Chart(df)
        .mark_bar(color=PALETTE[0], opacity=0.85)
        .encode(
            alt.X(col, bin=alt.Bin(maxbins=30), title=col),
            alt.Y("count()", title="Frequency"),
            tooltip=[alt.Tooltip(col, bin=alt.Bin(maxbins=30)), "count()"],
        )
    )

    mean_line = (
        alt.Chart(pd.DataFrame({"x": [mean_val]}))
        .mark_rule(color=PALETTE[1], strokeDash=[6, 3], strokeWidth=2)
        .encode(x="x:Q")
    )

    median_line = (
        alt.Chart(pd.DataFrame({"x": [median_val]}))
        .mark_rule(color=PALETTE[3], strokeDash=[4, 4], strokeWidth=2)
        .encode(x="x:Q")
    )

    return (
        (bars + mean_line + median_line)
        .properties(title=rec.title, width=400, height=300)
    )


@_register(ChartType.BAR)
def _bar(rec: ChartRecommendation, df: pd.DataFrame) -> alt.LayerChart:
    col = rec.columns[0]

    bars = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            alt.X(col, type="nominal", sort="-y", title=col),
            alt.Y("count()", title="Count"),
            alt.Color(
                col, type="nominal", legend=None,
                scale=alt.Scale(range=PALETTE),
            ),
            tooltip=[col, "count()"],
        )
    )

    text = (
        alt.Chart(df)
        .mark_text(dy=-8, fontWeight="bold", fontSize=11, color="#58544f")
        .encode(
            alt.X(col, type="nominal", sort="-y"),
            alt.Y("count()", type="quantitative"),
            alt.Text("count()"),
        )
    )

    return (bars + text).properties(title=rec.title, width=400, height=300)


@_register(ChartType.SCATTER)
def _scatter(rec: ChartRecommendation, df: pd.DataFrame) -> alt.LayerChart:
    col_x, col_y = rec.columns[0], rec.columns[1]

    points = (
        alt.Chart(df)
        .mark_circle(size=50, opacity=0.6, color=PALETTE[0])
        .encode(
            alt.X(col_x, type="quantitative", title=col_x),
            alt.Y(col_y, type="quantitative", title=col_y),
            tooltip=[
                alt.Tooltip(col_x, format=",.2f"),
                alt.Tooltip(col_y, format=",.2f"),
            ],
        )
    )

    trend = (
        alt.Chart(df)
        .mark_line(color=PALETTE[3], strokeDash=[6, 3], strokeWidth=2, opacity=0.8)
        .transform_regression(col_x, col_y)
        .encode(
            alt.X(col_x, type="quantitative"),
            alt.Y(col_y, type="quantitative"),
        )
    )

    return (points + trend).properties(title=rec.title, width=400, height=300)


@_register(ChartType.LINE)
def _line(rec: ChartRecommendation, df: pd.DataFrame) -> alt.LayerChart:
    dt_col, val_col = rec.columns[0], rec.columns[1]

    line = (
        alt.Chart(df)
        .mark_line(color=PALETTE[0], strokeWidth=2)
        .encode(
            alt.X(dt_col, type="temporal", title=dt_col),
            alt.Y(val_col, type="quantitative", title=val_col),
            tooltip=[dt_col, alt.Tooltip(val_col, format=",.2f")],
        )
    )

    points = (
        alt.Chart(df)
        .mark_circle(size=30, color=PALETTE[0])
        .encode(
            alt.X(dt_col, type="temporal"),
            alt.Y(val_col, type="quantitative"),
        )
    )

    area = (
        alt.Chart(df)
        .mark_area(color=PALETTE[0], opacity=0.08)
        .encode(
            alt.X(dt_col, type="temporal"),
            alt.Y(val_col, type="quantitative"),
        )
    )

    return (area + line + points).properties(title=rec.title, width=500, height=300)


@_register(ChartType.HEATMAP)
def _heatmap(rec: ChartRecommendation, df: pd.DataFrame) -> alt.LayerChart:
    numeric_df = df[rec.columns].apply(pd.to_numeric, errors="coerce")
    corr = numeric_df.corr().reset_index().melt(id_vars="index")
    corr.columns = ["Variable 1", "Variable 2", "Correlation"]

    base = alt.Chart(corr)

    rects = base.mark_rect().encode(
        alt.X("Variable 1:N", title=""),
        alt.Y("Variable 2:N", title=""),
        alt.Color(
            "Correlation:Q",
            scale=alt.Scale(scheme="blueorange", domain=[-1, 1]),
        ),
        tooltip=[
            "Variable 1", "Variable 2",
            alt.Tooltip("Correlation", format=".2f"),
        ],
    )

    text = base.mark_text(fontSize=11).encode(
        alt.X("Variable 1:N"),
        alt.Y("Variable 2:N"),
        alt.Text("Correlation:Q", format=".2f"),
        color=alt.condition(
            alt.datum.Correlation > 0.5,
            alt.value("white"),
            alt.value("black"),
        ),
    )

    return (rects + text).properties(title=rec.title, width=400, height=400)


@_register(ChartType.GROUPED_BAR)
def _grouped_bar(rec: ChartRecommendation, df: pd.DataFrame) -> alt.LayerChart:
    cat_col, num_col = rec.columns[0], rec.columns[1]
    grouped = df.groupby(cat_col)[num_col].mean().reset_index()

    bars = (
        alt.Chart(grouped)
        .mark_bar()
        .encode(
            alt.X(cat_col, type="nominal", sort="-y", title=cat_col),
            alt.Y(num_col, type="quantitative", title=f"Average {num_col}"),
            alt.Color(
                cat_col, type="nominal", legend=None,
                scale=alt.Scale(range=PALETTE),
            ),
            tooltip=[cat_col, alt.Tooltip(num_col, format=",.2f")],
        )
    )

    text = (
        alt.Chart(grouped)
        .mark_text(dy=-8, fontWeight="bold", fontSize=10, color="#58544f")
        .encode(
            alt.X(cat_col, type="nominal", sort="-y"),
            alt.Y(num_col, type="quantitative"),
            alt.Text(num_col, format=",.1f"),
        )
    )

    return (bars + text).properties(title=rec.title, width=400, height=300)


@_register(ChartType.BOX)
def _box_plot(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    if len(rec.columns) == 2:
        cat_col, num_col = rec.columns[0], rec.columns[1]
        return (
            alt.Chart(df)
            .mark_boxplot(extent=1.5)
            .encode(
                alt.X(cat_col, type="nominal", title=cat_col),
                alt.Y(num_col, type="quantitative", title=num_col),
                alt.Color(
                    cat_col, type="nominal", legend=None,
                    scale=alt.Scale(range=PALETTE),
                ),
                tooltip=[cat_col, alt.Tooltip(num_col, format=",.2f")],
            )
            .properties(title=rec.title, width=400, height=300)
        )

    col = rec.columns[0]
    return (
        alt.Chart(df)
        .mark_boxplot(extent=1.5, color=PALETTE[0])
        .encode(
            alt.Y(col, type="quantitative", title=col),
            tooltip=[alt.Tooltip(col, format=",.2f")],
        )
        .properties(title=rec.title, width=200, height=300)
    )


@_register(ChartType.VIOLIN)
def _violin_plot(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    col = rec.columns[0]
    return (
        alt.Chart(df)
        .transform_density(col, as_=[col, "density"])
        .mark_area(orient="horizontal", color=PALETTE[0], opacity=0.7)
        .encode(
            alt.X("density:Q", title="Density"),
            alt.Y(f"{col}:Q", title=col),
            tooltip=[alt.Tooltip(col, format=",.2f")],
        )
        .properties(title=rec.title, width=300, height=300)
    )


@_register(ChartType.MISSING_MATRIX)
def _missing_matrix(rec: ChartRecommendation, df: pd.DataFrame) -> alt.Chart:
    cols = [c for c in rec.columns if c in df.columns]
    if not cols:
        return alt.Chart(pd.DataFrame()).mark_text().encode()

    sample = df[cols].head(200)
    missing = sample.isnull().astype(int).reset_index().melt(id_vars="index")
    missing.columns = ["Row", "Column", "Missing"]

    return (
        alt.Chart(missing)
        .mark_rect()
        .encode(
            alt.X("Column:N", title=""),
            alt.Y("Row:O", title="Row", axis=None),
            alt.Color(
                "Missing:Q",
                scale=alt.Scale(domain=[0, 1], range=["#e9ecef", "#2563eb"]),
                legend=alt.Legend(title="Missing"),
            ),
            tooltip=["Row", "Column", "Missing"],
        )
        .properties(title=rec.title, width=400, height=300)
    )
