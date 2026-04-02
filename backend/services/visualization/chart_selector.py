"""Draco-inspired chart recommendation with interestingness scoring.

Only recommends charts that reveal meaningful patterns. Each candidate
is scored; charts scoring 0 are filtered out. Capped at 12 total.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from models.enums import ChartType, ColumnType
from models.schemas import ChartRecommendation, DataProfile, StatisticalReport

MAX_CHARTS = 16


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def select_charts(
    profile: DataProfile,
    df: pd.DataFrame,
    stat_report: StatisticalReport | None = None,
) -> list[ChartRecommendation]:
    numeric_cols = [c for c in profile.columns if c.inferred_type == ColumnType.NUMERIC]
    categorical_cols = [c for c in profile.columns if c.inferred_type == ColumnType.CATEGORICAL]
    datetime_cols = [c for c in profile.columns if c.inferred_type == ColumnType.DATETIME]

    candidates: list[ChartRecommendation] = []

    # Basic chart types
    candidates.extend(_candidate_histograms(numeric_cols, df))
    candidates.extend(_candidate_bars(categorical_cols, df, profile.total_rows))
    candidates.extend(_candidate_scatters(numeric_cols, df))
    candidates.extend(_candidate_timeseries(datetime_cols, numeric_cols, df))
    candidates.extend(_candidate_heatmap(numeric_cols, df))
    candidates.extend(_candidate_box_plots(numeric_cols, categorical_cols, df))
    candidates.extend(_candidate_grouped_bars(categorical_cols, numeric_cols, df, profile.total_rows))
    candidates.extend(_candidate_missing_matrix(profile, df))

    # Complex Plotly chart types
    candidates.extend(_candidate_treemap(categorical_cols, numeric_cols, df))
    candidates.extend(_candidate_sunburst(categorical_cols, numeric_cols, df))
    candidates.extend(_candidate_sankey(categorical_cols, df))
    candidates.extend(_candidate_bubble(numeric_cols, df))
    candidates.extend(_candidate_parallel_coords(numeric_cols, df))
    candidates.extend(_candidate_radar(numeric_cols, df))
    candidates.extend(_candidate_waterfall(categorical_cols, numeric_cols, df))

    # Statistical chart types
    if stat_report:
        candidates.extend(_candidate_statistical_charts(
            stat_report, numeric_cols, df,
        ))

    # Filter and rank
    interesting = [c for c in candidates if c.interestingness > 0]
    interesting.sort(key=lambda c: c.interestingness, reverse=True)
    return interesting[:MAX_CHARTS]


# ---------------------------------------------------------------------------
# Interestingness helpers
# ---------------------------------------------------------------------------

def _has_outliers(series: pd.Series) -> bool:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 4:
        return False
    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return False
    return bool(((clean < q1 - 1.5 * iqr) | (clean > q3 + 1.5 * iqr)).any())


def _is_bimodal(series: pd.Series) -> bool:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 10:
        return False
    try:
        from scipy.signal import find_peaks
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(clean)
        x = np.linspace(clean.min(), clean.max(), 200)
        y = kde(x)
        peaks, _ = find_peaks(y, prominence=0.05 * y.max())
        return len(peaks) >= 2
    except (ImportError, np.linalg.LinAlgError):
        # Fallback: large mean-median divergence relative to std
        if clean.std() == 0:
            return False
        return abs(clean.mean() - clean.median()) / clean.std() > 0.3


def _compute_entropy(series: pd.Series) -> float:
    counts = series.value_counts(normalize=True)
    if len(counts) <= 1:
        return 0.0
    entropy = -sum(p * math.log2(p) for p in counts if p > 0)
    max_entropy = math.log2(len(counts))
    return entropy / max_entropy if max_entropy > 0 else 0.0


def _rank_pairs_by_correlation(
    col_names: list[str], df: pd.DataFrame
) -> list[tuple[str, str, float]]:
    numeric_df = df[col_names].apply(pd.to_numeric, errors="coerce")
    corr_matrix = numeric_df.corr()

    pairs: list[tuple[str, str, float]] = []
    seen: set[tuple[str, str]] = set()
    for i, col_a in enumerate(col_names):
        for col_b in col_names[i + 1:]:
            key = tuple(sorted([col_a, col_b]))
            if key not in seen:
                seen.add(key)
                val = corr_matrix.loc[col_a, col_b]
                if not np.isnan(val):
                    pairs.append((col_a, col_b, float(val)))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return pairs


# ---------------------------------------------------------------------------
# Candidate generators (each returns scored recommendations)
# ---------------------------------------------------------------------------

def _candidate_histograms(
    numeric_cols: list, df: pd.DataFrame
) -> list[ChartRecommendation]:
    results = []
    for col in numeric_cols[:8]:
        series = pd.to_numeric(df[col.name], errors="coerce").dropna()
        if len(series) < 3:
            continue

        score = 0.0
        annotations = []
        mean_val = float(series.mean())
        median_val = float(series.median())
        std_val = float(series.std())
        skew = float(series.skew()) if len(series) > 2 else 0.0
        has_out = _has_outliers(series)
        bimodal = _is_bimodal(series)

        if abs(skew) > 1.0:
            direction = "right" if skew > 0 else "left"
            score += 0.4
            annotations.append(f"The distribution is {direction}-skewed (skewness: {skew:.2f})")

        if has_out:
            score += 0.3
            annotations.append("outliers detected beyond 1.5x IQR")

        if bimodal:
            score += 0.3
            annotations.append("two distinct modes suggest possible subpopulations")

        # Always show at least 1-2 histograms for overview (lower base score)
        if score == 0 and len(numeric_cols) <= 3:
            score = 0.1

        if score > 0:
            annotation = ". ".join(annotations).capitalize() + "." if annotations else ""

            # Data-driven description
            shape_desc = (
                f"skewed right — most values cluster below the mean"
                if skew > 1.0 else
                f"skewed left — most values cluster above the mean"
                if skew < -1.0 else
                f"roughly symmetric around {mean_val:.1f}"
            )
            description = (
                f"Shows how {col.name} values are distributed. "
                f"The dashed lines mark the mean ({mean_val:.1f}) and median ({median_val:.1f}). "
                f"The distribution is {shape_desc}."
            )

            results.append(ChartRecommendation(
                chart_type=ChartType.HISTOGRAM,
                columns=[col.name],
                title=f"Distribution of {col.name}",
                description=description,
                interestingness=score,
                annotation=annotation,
                reading_guide=(
                    "Each bar shows how many records fall in that value range. "
                    "Taller bars = more common values. Dashed lines mark the mean and median — "
                    "when they diverge, the distribution is skewed."
                ),
            ))
    return results


def _candidate_bars(
    categorical_cols: list, df: pd.DataFrame, total_rows: int,
) -> list[ChartRecommendation]:
    results = []
    for col in categorical_cols[:6]:
        if col.unique_count < 2 or col.unique_count > 20:
            continue

        entropy = _compute_entropy(df[col.name].dropna())
        counts = df[col.name].value_counts()
        top_val = counts.index[0]
        top_pct = counts.iloc[0] / total_rows * 100
        top3_pct = counts.iloc[:3].sum() / total_rows * 100 if len(counts) >= 3 else top_pct

        score = 0.0
        if entropy > 0.5:
            score += 0.5
        if len(counts) >= 3:
            score += 0.3
        if top_pct > 90:
            score = 0.0

        if score > 0:
            annotation = f"'{top_val}' is the most frequent category, accounting for {top_pct:.0f}% of records."
            concentration = (
                f"; the top 3 categories account for {top3_pct:.0f}% of all records"
                if top3_pct > 50 and len(counts) >= 3 else ""
            )
            description = (
                f"Frequency of each {col.name} value. "
                f"'{top_val}' leads at {top_pct:.0f}%{concentration}."
            )

            results.append(ChartRecommendation(
                chart_type=ChartType.BAR,
                columns=[col.name],
                title=f"Counts by {col.name}",
                description=description,
                interestingness=score,
                annotation=annotation,
            ))
    return results


def _candidate_scatters(
    numeric_cols: list, df: pd.DataFrame
) -> list[ChartRecommendation]:
    if len(numeric_cols) < 2:
        return []

    pairs = _rank_pairs_by_correlation([c.name for c in numeric_cols], df)
    results = []
    for col_a, col_b, corr in pairs[:4]:
        if abs(corr) < 0.3:
            continue

        strength = "strong" if abs(corr) >= 0.7 else "moderate"
        direction = "positive" if corr > 0 else "negative"
        annotation = (
            f"There is a {strength} {direction} linear relationship "
            f"between {col_a} and {col_b} (r={corr:.2f})."
        )

        tightness = (
            "Points cluster tightly around the trend line, confirming a strong relationship."
            if abs(corr) > 0.8 else
            "Points spread moderately — a clear trend exists but with notable variation."
            if abs(corr) > 0.5 else
            "Points are widely scattered — the relationship is weak."
        )
        description = (
            f"Each point represents one record plotting {col_a} against {col_b}. "
            f"{tightness}"
        )

        results.append(ChartRecommendation(
            chart_type=ChartType.SCATTER,
            columns=[col_a, col_b],
            title=f"{col_a} vs {col_b} (r={corr:.2f})",
            description=description,
            interestingness=abs(corr),
            annotation=annotation,
            reading_guide=(
                "Each dot = one record. The trend line shows the overall direction. "
                "Tightly clustered dots = strong relationship. Scattered dots = weak relationship. "
                "r near +1 = move together, r near -1 = move opposite."
            ),
        ))
    return results


def _candidate_timeseries(
    datetime_cols: list, numeric_cols: list, df: pd.DataFrame
) -> list[ChartRecommendation]:
    if not datetime_cols or not numeric_cols:
        return []

    dt_col = datetime_cols[0]
    dt_series = pd.to_datetime(df[dt_col.name], errors="coerce")
    n_timepoints = dt_series.nunique()

    if n_timepoints < 10:
        return []

    results = []
    for num_col in numeric_cols[:2]:
        series = pd.to_numeric(df[num_col.name], errors="coerce").dropna()
        trend_desc = ""
        if len(series) > 10:
            first_half = series.iloc[:len(series)//2].mean()
            second_half = series.iloc[len(series)//2:].mean()
            pct_change = (second_half - first_half) / abs(first_half) * 100 if first_half != 0 else 0
            if abs(pct_change) > 5:
                direction = "upward" if pct_change > 0 else "downward"
                trend_desc = f" An overall {direction} trend is visible ({pct_change:+.1f}% from first to second half)."

        description = (
            f"Tracks {num_col.name} across {n_timepoints} time points.{trend_desc}"
        )
        results.append(ChartRecommendation(
            chart_type=ChartType.LINE,
            columns=[dt_col.name, num_col.name],
            title=f"{num_col.name} over time",
            description=description,
            interestingness=0.8,
            annotation=f"Tracking {num_col.name} across {n_timepoints} time points reveals temporal patterns.",
            reading_guide=(
                "X-axis = time, Y-axis = value. Look for trends (sustained rise/fall), "
                "seasonality (repeating patterns), and anomalies (sudden spikes or drops)."
            ),
        ))
    return results


def _candidate_heatmap(
    numeric_cols: list, df: pd.DataFrame
) -> list[ChartRecommendation]:
    if len(numeric_cols) < 4:
        return []

    col_names = [c.name for c in numeric_cols[:10]]
    pairs = _rank_pairs_by_correlation(col_names, df)
    if not pairs:
        return []

    max_corr = max((abs(c) for _, _, c in pairs), default=0)
    if max_corr < 0.5:
        return []

    # Find strongest positive and negative pairs
    top_pair = pairs[0]
    neg_pairs = [p for p in pairs if p[2] < 0]
    neg_pair = neg_pairs[0] if neg_pairs else None

    description = (
        f"Each cell shows how strongly two columns are related (-1 to +1). "
        f"Red = move together, blue = move opposite. "
        f"Strongest pair: {top_pair[0]} & {top_pair[1]} (r={top_pair[2]:.2f})"
    )
    if neg_pair and neg_pair[2] < -0.3:
        description += f". Most inverse: {neg_pair[0]} & {neg_pair[1]} (r={neg_pair[2]:.2f})"
    description += "."

    annotation = (
        f"Strongest pair: {top_pair[0]} & {top_pair[1]} (r={top_pair[2]:.2f})"
    )
    if abs(top_pair[2]) > 0.9:
        annotation += " — highly redundant, consider dropping one for modeling"
    annotation += "."
    if neg_pair and neg_pair[2] < -0.5:
        annotation += f" {neg_pair[0]} and {neg_pair[1]} are inversely related (r={neg_pair[2]:.2f})."

    return [ChartRecommendation(
        chart_type=ChartType.HEATMAP,
        columns=col_names,
        title="Correlation Heatmap",
        description=description,
        interestingness=max_corr,
        annotation=annotation,
        reading_guide=(
            "Each cell = correlation between two variables. "
            "Red/warm = positive (move together), Blue/cool = negative (move opposite). "
            "Darker color = stronger relationship. Look for clusters of red or blue."
        ),
    )]


def _candidate_box_plots(
    numeric_cols: list, categorical_cols: list, df: pd.DataFrame
) -> list[ChartRecommendation]:
    results = []

    # Grouped box plots: numeric grouped by small categorical
    if categorical_cols and numeric_cols:
        for cat in categorical_cols[:2]:
            if cat.unique_count < 2 or cat.unique_count > 8:
                continue
            for num in numeric_cols[:2]:
                if not _has_outliers(df[num.name]):
                    continue
                grouped = df.groupby(cat.name)[num.name].apply(
                    lambda s: pd.to_numeric(s, errors="coerce").dropna().median()
                )
                if len(grouped) < 2:
                    continue
                high_group = grouped.idxmax()
                low_group = grouped.idxmin()
                description = (
                    f"Compares {num.name} across {cat.unique_count} {cat.name} groups. "
                    f"'{high_group}' has the highest median, '{low_group}' the lowest."
                )
                results.append(ChartRecommendation(
                    chart_type=ChartType.BOX,
                    columns=[cat.name, num.name],
                    title=f"{num.name} by {cat.name}",
                    description=description,
                    interestingness=0.9,
                    annotation=(
                        f"Box plot comparing {num.name} across {cat.name} categories. "
                        f"Boxes show IQR; whiskers extend to 1.5x IQR; dots are outliers."
                    ),
                    reading_guide=(
                        "The box = middle 50% of values (IQR). Line inside = median. "
                        "Whiskers = range of typical values. Dots beyond whiskers = outliers. "
                        "Compare box positions to see which groups have higher/lower values."
                    ),
                ))
    return results


def _candidate_grouped_bars(
    categorical_cols: list, numeric_cols: list, df: pd.DataFrame, total_rows: int
) -> list[ChartRecommendation]:
    if not categorical_cols or not numeric_cols:
        return []

    results = []
    for cat in categorical_cols[:2]:
        if cat.unique_count < 2 or cat.unique_count > 15:
            continue
        for num in numeric_cols[:1]:
            entropy = _compute_entropy(df[cat.name].dropna())
            if entropy < 0.5:
                continue
            grouped = df.groupby(cat.name)[num.name].mean()
            range_ratio = (grouped.max() - grouped.min()) / grouped.mean() if grouped.mean() != 0 else 0

            highest_cat = grouped.idxmax()
            lowest_cat = grouped.idxmin()
            annotation = (
                f"Average {num.name} varies across {cat.name} categories"
                + (f" by up to {range_ratio:.0%}." if range_ratio > 0.1 else ".")
            )
            description = (
                f"Mean {num.name} across {cat.unique_count} {cat.name} categories. "
                f"'{highest_cat}' has the highest average ({grouped.max():.1f}), "
                f"'{lowest_cat}' the lowest ({grouped.min():.1f})."
            )

            results.append(ChartRecommendation(
                chart_type=ChartType.GROUPED_BAR,
                columns=[cat.name, num.name],
                title=f"Average {num.name} by {cat.name}",
                description=description,
                interestingness=min(0.7, entropy),
                annotation=annotation,
            ))
    return results


def _candidate_missing_matrix(
    profile: DataProfile, df: pd.DataFrame
) -> list[ChartRecommendation]:
    cols_with_missing = [c for c in profile.columns if c.null_pct > 1.0]
    if len(cols_with_missing) < 3:
        return []

    col_names = [c.name for c in cols_with_missing]
    avg_missing = sum(c.null_pct for c in cols_with_missing) / len(cols_with_missing)

    worst_col = max(cols_with_missing, key=lambda c: c.null_pct)
    description = (
        f"Visualizes missing data patterns across {len(col_names)} columns. "
        f"'{worst_col.name}' has the most gaps at {worst_col.null_pct:.1f}% missing. "
        f"Average missingness across flagged columns: {avg_missing:.1f}%."
    )

    return [ChartRecommendation(
        chart_type=ChartType.MISSING_MATRIX,
        columns=col_names,
        title="Missing Data Patterns",
        description=description,
        interestingness=min(1.0, avg_missing / 10),
        annotation=(
            f"{len(col_names)} columns have notable missing data. "
            f"Clustered patterns may indicate systematic data collection issues."
        ),
        reading_guide=(
            "White = data present, colored = missing. Each column = a dataset column. "
            "Look for horizontal bands (rows missing many columns simultaneously) "
            "or vertical bands (a column missing across many rows)."
        ),
    )]


# ---------------------------------------------------------------------------
# Complex Plotly chart candidates
# ---------------------------------------------------------------------------

def _detect_hierarchy(
    df: pd.DataFrame, cat_cols: list,
) -> list[tuple[str, str]]:
    """Detect parent-child categorical hierarchies (parent cardinality < child by 3:1+)."""
    hierarchies = []
    for i, parent in enumerate(cat_cols):
        for child in cat_cols[i + 1:]:
            parent_card = df[parent.name].nunique()
            child_card = df[child.name].nunique()
            if child_card >= parent_card * 2 and parent_card >= 2:
                hierarchies.append((parent.name, child.name))
            elif parent_card >= child_card * 2 and child_card >= 2:
                hierarchies.append((child.name, parent.name))
    return hierarchies


def _candidate_treemap(
    categorical_cols: list, numeric_cols: list, df: pd.DataFrame,
) -> list[ChartRecommendation]:
    if len(categorical_cols) < 2:
        return []

    hierarchies = _detect_hierarchy(df, categorical_cols)
    if not hierarchies:
        return []

    parent, child = hierarchies[0]
    cols = [parent, child]
    if numeric_cols:
        cols.append(numeric_cols[0].name)

    # Compute dominant category
    top_parent = df[parent].value_counts().index[0]
    top_parent_pct = df[parent].value_counts(normalize=True).iloc[0] * 100
    description = (
        f"Hierarchical breakdown of {child} grouped by {parent}. "
        f"Rectangle size = record count. '{top_parent}' is the largest group ({top_parent_pct:.0f}%)."
    )

    return [ChartRecommendation(
        chart_type=ChartType.TREEMAP,
        columns=cols,
        title=f"Treemap: {child} within {parent}",
        description=description,
        interestingness=0.8,
        annotation=f"Treemap reveals the hierarchical relationship between {parent} and {child}.",
        reading_guide=(
            "Larger rectangles = more records in that category. "
            "Nested rectangles show subcategories within each group. "
            "Compare rectangle sizes to see which categories dominate."
        ),
    )]


def _candidate_sunburst(
    categorical_cols: list, numeric_cols: list, df: pd.DataFrame,
) -> list[ChartRecommendation]:
    if len(categorical_cols) < 3:
        return []

    hierarchies = _detect_hierarchy(df, categorical_cols)
    if not hierarchies:
        return []

    # Use first 3 categorical columns for deeper nesting
    cols = [c.name for c in categorical_cols[:3]]
    if numeric_cols:
        cols.append(numeric_cols[0].name)

    n_levels = len(cols) - (1 if numeric_cols else 0)
    description = (
        f"Hierarchical breakdown of {' → '.join(cols[:3])}. "
        f"Inner ring = {cols[0]}, each outer ring subdivides further. "
        f"Slice size = record count. Larger slices = more prevalent combinations."
    )

    return [ChartRecommendation(
        chart_type=ChartType.SUNBURST,
        columns=cols,
        title=f"Sunburst: {' > '.join(cols[:3])}",
        description=description,
        interestingness=0.85,
        annotation="Sunburst chart shows nested hierarchical structure across multiple categorical dimensions.",
        reading_guide=(
            "Inner ring = first category. Outer rings = subdivisions. "
            "Slice size = count. Read from center outward to see how categories break down. "
            "Click a slice to zoom into that branch."
        ),
    )]


def _candidate_sankey(
    categorical_cols: list, df: pd.DataFrame,
) -> list[ChartRecommendation]:
    if len(categorical_cols) < 2:
        return []

    for i, col_a in enumerate(categorical_cols[:4]):
        for col_b in categorical_cols[i + 1:4]:
            if col_a.unique_count < 2 or col_b.unique_count < 2:
                continue
            if col_a.unique_count > 15 or col_b.unique_count > 15:
                continue

            cross = pd.crosstab(df[col_a.name], df[col_b.name])
            n_flows = (cross > 0).sum().sum()
            if n_flows < 5:
                continue

            entropy_a = _compute_entropy(df[col_a.name].dropna())
            entropy_b = _compute_entropy(df[col_b.name].dropna())

            if entropy_a < 0.4 or entropy_b < 0.4:
                continue

            # Find dominant flow
            flow_df = df.groupby([col_a.name, col_b.name]).size().reset_index(name="count")
            top_flow = flow_df.loc[flow_df["count"].idxmax()]
            description = (
                f"Shows how records flow from {col_a.name} to {col_b.name} across {n_flows} paths. "
                f"Thicker bands = more records. Dominant flow: "
                f"'{top_flow[col_a.name]}' → '{top_flow[col_b.name]}' ({top_flow['count']} records)."
            )

            return [ChartRecommendation(
                chart_type=ChartType.SANKEY,
                columns=[col_a.name, col_b.name],
                title=f"Flow: {col_a.name} → {col_b.name}",
                description=description,
                interestingness=0.9,
                annotation=f"Sankey diagram reveals {n_flows} distinct flow paths from {col_a.name} to {col_b.name}.",
                reading_guide=(
                    "Left nodes = source categories, right nodes = target categories. "
                    "Band thickness = number of records flowing between them. "
                    "Follow the thickest bands to see the most common transitions."
                ),
            )]
    return []


def _candidate_bubble(
    numeric_cols: list, df: pd.DataFrame,
) -> list[ChartRecommendation]:
    if len(numeric_cols) < 3:
        return []

    pairs = _rank_pairs_by_correlation([c.name for c in numeric_cols], df)
    if not pairs or abs(pairs[0][2]) < 0.3:
        return []

    col_a, col_b, corr = pairs[0]
    # Pick 3rd column with most variance (not in the pair)
    remaining = [c for c in numeric_cols if c.name not in (col_a, col_b)]
    if not remaining:
        return []

    size_col = max(remaining, key=lambda c: c.stats.std if c.stats else 0)

    description = (
        f"Each bubble plots {col_a} vs {col_b} (r={corr:.2f}), with bubble size "
        f"representing {size_col.name}. Larger bubbles = higher {size_col.name} values. "
        f"Look for whether large bubbles cluster in specific regions."
    )

    return [ChartRecommendation(
        chart_type=ChartType.BUBBLE,
        columns=[col_a, col_b, size_col.name],
        title=f"{col_a} vs {col_b} (sized by {size_col.name})",
        description=description,
        interestingness=abs(corr) + 0.2,
        annotation=(
            f"Bubble chart extends the scatter relationship (r={corr:.2f}) "
            f"with {size_col.name} encoded as bubble size."
        ),
    )]


def _candidate_parallel_coords(
    numeric_cols: list, df: pd.DataFrame,
) -> list[ChartRecommendation]:
    if len(numeric_cols) < 4:
        return []

    col_names = [c.name for c in numeric_cols[:8]]
    pairs = _rank_pairs_by_correlation(col_names, df)
    has_strong = any(abs(c) > 0.5 for _, _, c in pairs)

    if not has_strong:
        return []

    description = (
        f"Each line traces one record across {len(col_names)} variables. "
        f"Parallel lines between axes = correlated variables. "
        f"Crossing lines = inversely related variables."
    )

    return [ChartRecommendation(
        chart_type=ChartType.PARALLEL_COORDS,
        columns=col_names,
        title="Parallel Coordinates Overview",
        description=description,
        interestingness=0.7,
        annotation=(
            f"Parallel coordinates plot reveals multivariate patterns across "
            f"{len(col_names)} variables. Crossing lines indicate inverse relationships."
        ),
        reading_guide=(
            "Each vertical axis = one variable. Each line = one record passing through all axes. "
            "Lines running parallel between two axes = those variables are correlated. "
            "Lines that cross = inverse relationship. Dense bundles = common patterns."
        ),
    )]


def _candidate_radar(
    numeric_cols: list, df: pd.DataFrame,
) -> list[ChartRecommendation]:
    if len(numeric_cols) < 3 or len(numeric_cols) > 8:
        return []

    col_names = [c.name for c in numeric_cols]
    numeric_df = df[col_names].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_df) < 5:
        return []

    means = numeric_df.mean()
    # Check comparable scales: all positive and CV of means > 0.3
    if (means <= 0).any():
        return []

    cv = float(means.std() / means.mean()) if means.mean() != 0 else 0
    if cv < 0.3:
        return []

    # Find strongest and weakest axes
    normalized = (numeric_df - numeric_df.min()) / (numeric_df.max() - numeric_df.min() + 1e-10)
    norm_means = normalized.mean()
    strongest = norm_means.idxmax()
    weakest = norm_means.idxmin()
    description = (
        f"Compares {len(col_names)} metrics on a normalized scale (0-1). "
        f"'{strongest}' scores highest relative to its range, "
        f"'{weakest}' scores lowest. The shape reveals the dataset's characteristic profile."
    )

    return [ChartRecommendation(
        chart_type=ChartType.RADAR,
        columns=col_names,
        title="Multi-Metric Radar Profile",
        description=description,
        interestingness=0.75,
        annotation="Radar chart shows the normalized mean of each metric, revealing the dataset's characteristic profile.",
        reading_guide=(
            "Each spoke = one metric, normalized to 0-1. The filled shape shows average values. "
            "Spokes pointing further out = higher relative values. "
            "A perfectly round shape = all metrics are balanced."
        ),
    )]


def _candidate_waterfall(
    categorical_cols: list, numeric_cols: list, df: pd.DataFrame,
) -> list[ChartRecommendation]:
    if not categorical_cols or not numeric_cols:
        return []

    for cat in categorical_cols[:3]:
        if cat.unique_count < 3 or cat.unique_count > 15:
            continue
        for num in numeric_cols[:2]:
            grouped = df.groupby(cat.name)[num.name].sum()
            if len(grouped) < 3:
                continue

            # Waterfall is interesting when values have mixed signs or clear ranking
            has_negative = (grouped < 0).any()
            range_ratio = (grouped.max() - grouped.min()) / abs(grouped.mean()) if grouped.mean() != 0 else 0

            if not has_negative and range_ratio < 0.5:
                continue

            top_cat = grouped.idxmax()
            top_val = grouped.max()
            description = (
                f"Shows how each {cat.name} contributes to total {num.name}. "
                f"'{top_cat}' makes the largest contribution ({top_val:,.1f}). "
                f"Blue = positive contribution, red = negative."
            )

            return [ChartRecommendation(
                chart_type=ChartType.WATERFALL,
                columns=[cat.name, num.name],
                title=f"Waterfall: {num.name} by {cat.name}",
                description=description,
                interestingness=0.8,
                annotation=f"Waterfall chart shows how each {cat.name} contributes to the total {num.name}.",
            )]
    return []


# ---------------------------------------------------------------------------
# Statistical chart candidates
# ---------------------------------------------------------------------------

def _candidate_statistical_charts(
    stat_report: StatisticalReport,
    numeric_cols: list,
    df: pd.DataFrame,
) -> list[ChartRecommendation]:
    results: list[ChartRecommendation] = []
    col_names = [c.name for c in numeric_cols]

    if stat_report.pca and len(col_names) >= 4:
        ev = stat_report.pca.explained_variance
        total_2d = sum(ev[:2]) if len(ev) >= 2 else 0
        n_95 = stat_report.pca.n_components_95
        description = (
            f"PCA compresses {len(col_names)} variables into 2 axes capturing {total_2d:.1%} "
            f"of total variation. Arrows represent variables — direction shows axis alignment, "
            f"length shows contribution. Variables pointing the same way are correlated."
        )
        annotation = (
            f"PCA reduces {len(col_names)} dimensions to 2 components capturing "
            f"{total_2d:.1%} of total variance. "
            f"{n_95} component{'s' if n_95 != 1 else ''} needed for 95% coverage."
        )
        results.append(ChartRecommendation(
            chart_type=ChartType.PCA_BIPLOT,
            columns=col_names,
            title="PCA Biplot",
            description=description,
            interestingness=0.85,
            annotation=annotation,
            reading_guide=(
                "Dots = data points on 2 principal axes. Arrows = original variables. "
                "Direction = which axis it loads on. Length = importance. "
                "Same-direction arrows = correlated variables. Opposite arrows = inversely related."
            ),
        ))

    if stat_report.clusters and len(col_names) >= 3:
        k = stat_report.clusters.optimal_k
        sil = stat_report.clusters.silhouette_score
        sizes = stat_report.clusters.cluster_sizes
        sil_desc = "well-separated" if sil > 0.5 else "moderately distinct" if sil > 0.25 else "overlapping"
        description = (
            f"Data grouped into {k} clusters, projected to 2D. "
            f"Clusters are {sil_desc} (silhouette: {sil:.2f}, where 1.0 = perfect separation). "
            f"Each color is a cluster — look for distinct groupings vs overlap."
        )
        annotation_parts = [f"{k} natural groupings detected"]
        if sizes:
            annotation_parts.append(
                f"Largest: {max(sizes)} records, smallest: {min(sizes)}"
            )
        if sil < 0.25:
            annotation_parts.append("Significant overlap suggests the data may lack distinct subgroups")
        else:
            annotation_parts.append("Clear separation indicates meaningful subgroups")
        annotation = ". ".join(annotation_parts) + "."

        results.append(ChartRecommendation(
            chart_type=ChartType.CLUSTER_SCATTER,
            columns=col_names,
            title=f"Cluster Analysis ({k} clusters)",
            description=description,
            interestingness=0.9,
            annotation=annotation,
            reading_guide=(
                "Each color = a cluster (natural grouping). Points close together = similar records. "
                "Overlap between colors = hard-to-distinguish groups. "
                "Well-separated clusters indicate meaningful subgroups in the data."
            ),
        ))

    if stat_report.anomalies and len(col_names) >= 2:
        n = stat_report.anomalies.n_anomalies
        pct = stat_report.anomalies.anomaly_pct
        top_cols = stat_report.anomalies.top_anomaly_columns
        description = (
            f"Red X markers show {n} records ({pct}%) that are statistically unusual. "
            f"Identified using Isolation Forest — points that are easy to separate from the majority. "
            f"Check these records for data errors or genuine exceptions."
        )
        annotation = (
            f"{n} anomalous records ({pct}%) identified via Isolation Forest."
        )
        if top_cols:
            annotation += f" Most contributing columns: {', '.join(top_cols[:3])}."

        results.append(ChartRecommendation(
            chart_type=ChartType.ANOMALY_SCATTER,
            columns=col_names,
            title=f"Anomaly Detection ({n} anomalies)",
            description=description,
            interestingness=0.85,
            annotation=annotation,
            reading_guide=(
                "Blue dots = normal records. Red X = outlier. "
                "Outliers are statistically unusual compared to the majority — "
                "check for data entry errors or genuine exceptional cases."
            ),
        ))

    return results
