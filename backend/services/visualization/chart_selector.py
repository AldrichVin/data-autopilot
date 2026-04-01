import numpy as np
import pandas as pd

from models.enums import ChartType, ColumnType
from models.schemas import ChartRecommendation, DataProfile


def select_charts(
    profile: DataProfile, df: pd.DataFrame
) -> list[ChartRecommendation]:
    charts: list[ChartRecommendation] = []

    numeric_cols = [c for c in profile.columns if c.inferred_type == ColumnType.NUMERIC]
    categorical_cols = [
        c for c in profile.columns if c.inferred_type == ColumnType.CATEGORICAL
    ]
    datetime_cols = [
        c for c in profile.columns if c.inferred_type == ColumnType.DATETIME
    ]

    # Rule 1: Histogram for each numeric column (up to 6)
    for col in numeric_cols[:6]:
        stats_desc = ""
        if col.stats:
            stats_desc = (
                f" (mean: {col.stats.mean:,.2f}, "
                f"std: {col.stats.std:,.2f})"
            )
        charts.append(
            ChartRecommendation(
                chart_type=ChartType.HISTOGRAM,
                columns=[col.name],
                title=f"Distribution of {col.name}",
                description=(
                    f"Frequency distribution of {col.name}{stats_desc}. "
                    f"Shows mean and median reference lines."
                ),
            )
        )

    # Rule 2: Bar chart for each categorical column (<=20 unique, up to 4)
    for col in categorical_cols[:4]:
        if col.unique_count <= 20:
            charts.append(
                ChartRecommendation(
                    chart_type=ChartType.BAR,
                    columns=[col.name],
                    title=f"Counts by {col.name}",
                    description=(
                        f"Value counts for {col.name} "
                        f"({col.unique_count} unique categories)"
                    ),
                )
            )

    # Rule 3: Scatter plots for top 3 numeric pairs by correlation
    if len(numeric_cols) >= 2:
        pairs = _rank_pairs_by_correlation(
            [c.name for c in numeric_cols], df
        )
        for col_a, col_b, corr in pairs[:3]:
            strength = "strong" if abs(corr) >= 0.7 else "moderate" if abs(corr) >= 0.4 else "weak"
            direction = "positive" if corr > 0 else "negative"
            charts.append(
                ChartRecommendation(
                    chart_type=ChartType.SCATTER,
                    columns=[col_a, col_b],
                    title=f"{col_a} vs {col_b} (r={corr:.2f})",
                    description=(
                        f"Scatter plot with trend line showing {strength} "
                        f"{direction} relationship between {col_a} and {col_b}"
                    ),
                )
            )

    # Rule 4: Time series for datetime + numeric
    if datetime_cols and numeric_cols:
        dt_col = datetime_cols[0]
        for num_col in numeric_cols[:2]:
            charts.append(
                ChartRecommendation(
                    chart_type=ChartType.LINE,
                    columns=[dt_col.name, num_col.name],
                    title=f"{num_col.name} over time",
                    description=(
                        f"Time series of {num_col.name} plotted against "
                        f"{dt_col.name} to reveal temporal trends"
                    ),
                )
            )

    # Rule 5: Correlation heatmap if >= 3 numeric columns
    if len(numeric_cols) >= 3:
        heatmap_cols = [c.name for c in numeric_cols[:10]]
        charts.append(
            ChartRecommendation(
                chart_type=ChartType.HEATMAP,
                columns=heatmap_cols,
                title="Correlation Heatmap",
                description=(
                    f"Pairwise Pearson correlations between "
                    f"{len(heatmap_cols)} numeric columns"
                ),
            )
        )

    # Rule 6: Grouped bar if categorical + numeric exist
    if categorical_cols and numeric_cols:
        cat = categorical_cols[0]
        num = numeric_cols[0]
        if cat.unique_count <= 20:
            charts.append(
                ChartRecommendation(
                    chart_type=ChartType.GROUPED_BAR,
                    columns=[cat.name, num.name],
                    title=f"Average {num.name} by {cat.name}",
                    description=(
                        f"Average {num.name} grouped by {cat.name} "
                        f"({cat.unique_count} categories)"
                    ),
                )
            )

    return charts


def _rank_pairs_by_correlation(
    numeric_col_names: list[str], df: pd.DataFrame
) -> list[tuple[str, str, float]]:
    numeric_df = df[numeric_col_names].apply(pd.to_numeric, errors="coerce")
    corr_matrix = numeric_df.corr().abs()

    pairs: list[tuple[str, str, float]] = []
    seen = set()
    for i, col_a in enumerate(numeric_col_names):
        for col_b in numeric_col_names[i + 1 :]:
            key = tuple(sorted([col_a, col_b]))
            if key not in seen:
                seen.add(key)
                corr_val = corr_matrix.loc[col_a, col_b]
                if not np.isnan(corr_val):
                    pairs.append((col_a, col_b, float(corr_val)))

    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs
