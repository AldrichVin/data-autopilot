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
            results.append(ChartRecommendation(
                chart_type=ChartType.HISTOGRAM,
                columns=[col.name],
                title=f"Distribution of {col.name}",
                description=f"Frequency distribution of {col.name} with mean and median reference lines",
                interestingness=score,
                annotation=annotation,
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

        score = 0.0
        if entropy > 0.5:
            score += 0.5
        if len(counts) >= 3:
            score += 0.3
        # Penalize if one category dominates >90%
        if top_pct > 90:
            score = 0.0

        if score > 0:
            annotation = f"'{top_val}' is the most frequent category, accounting for {top_pct:.0f}% of records."
            results.append(ChartRecommendation(
                chart_type=ChartType.BAR,
                columns=[col.name],
                title=f"Counts by {col.name}",
                description=f"Value distribution across {col.unique_count} categories",
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

        results.append(ChartRecommendation(
            chart_type=ChartType.SCATTER,
            columns=[col_a, col_b],
            title=f"{col_a} vs {col_b} (r={corr:.2f})",
            description=f"Scatter plot with regression trend line",
            interestingness=abs(corr),
            annotation=annotation,
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
        results.append(ChartRecommendation(
            chart_type=ChartType.LINE,
            columns=[dt_col.name, num_col.name],
            title=f"{num_col.name} over time",
            description=f"Time series of {num_col.name} across {n_timepoints} time points",
            interestingness=0.8,
            annotation=f"Tracking {num_col.name} across {n_timepoints} time points reveals temporal patterns.",
        ))
    return results


def _candidate_heatmap(
    numeric_cols: list, df: pd.DataFrame
) -> list[ChartRecommendation]:
    if len(numeric_cols) < 4:
        return []

    col_names = [c.name for c in numeric_cols[:10]]
    pairs = _rank_pairs_by_correlation(col_names, df)
    max_corr = max((abs(c) for _, _, c in pairs), default=0)

    if max_corr < 0.5:
        return []

    return [ChartRecommendation(
        chart_type=ChartType.HEATMAP,
        columns=col_names,
        title="Correlation Heatmap",
        description=f"Pairwise Pearson correlations between {len(col_names)} numeric columns",
        interestingness=max_corr,
        annotation=f"Strongest correlation: r={max_corr:.2f}. Values near ±1 indicate strong linear relationships.",
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
                results.append(ChartRecommendation(
                    chart_type=ChartType.BOX,
                    columns=[cat.name, num.name],
                    title=f"{num.name} by {cat.name}",
                    description=f"Distribution comparison of {num.name} across {cat.unique_count} groups",
                    interestingness=0.9,
                    annotation=(
                        f"Box plot comparing {num.name} across {cat.name} categories. "
                        f"Boxes show IQR; whiskers extend to 1.5x IQR; dots are outliers."
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

            annotation = (
                f"Average {num.name} varies across {cat.name} categories"
                + (f" by up to {range_ratio:.0%}." if range_ratio > 0.1 else ".")
            )

            results.append(ChartRecommendation(
                chart_type=ChartType.GROUPED_BAR,
                columns=[cat.name, num.name],
                title=f"Average {num.name} by {cat.name}",
                description=f"Mean {num.name} across {cat.unique_count} categories",
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

    return [ChartRecommendation(
        chart_type=ChartType.MISSING_MATRIX,
        columns=col_names,
        title="Missing Data Patterns",
        description=f"Missingness pattern across {len(col_names)} columns with >1% null values",
        interestingness=min(1.0, avg_missing / 10),
        annotation=(
            f"{len(col_names)} columns have notable missing data. "
            f"Clustered patterns may indicate systematic data collection issues."
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

    return [ChartRecommendation(
        chart_type=ChartType.TREEMAP,
        columns=cols,
        title=f"Treemap: {child} within {parent}",
        description=f"Hierarchical breakdown of {child} grouped by {parent}",
        interestingness=0.8,
        annotation=f"Treemap reveals the hierarchical relationship between {parent} and {child}.",
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

    return [ChartRecommendation(
        chart_type=ChartType.SUNBURST,
        columns=cols,
        title=f"Sunburst: {' > '.join(cols[:3])}",
        description=f"Nested categorical breakdown across {len(cols) - (1 if numeric_cols else 0)} levels",
        interestingness=0.85,
        annotation="Sunburst chart shows nested hierarchical structure across multiple categorical dimensions.",
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

            return [ChartRecommendation(
                chart_type=ChartType.SANKEY,
                columns=[col_a.name, col_b.name],
                title=f"Flow: {col_a.name} → {col_b.name}",
                description=f"Flow diagram showing {n_flows} connections between categories",
                interestingness=0.9,
                annotation=f"Sankey diagram reveals {n_flows} distinct flow paths from {col_a.name} to {col_b.name}.",
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

    return [ChartRecommendation(
        chart_type=ChartType.BUBBLE,
        columns=[col_a, col_b, size_col.name],
        title=f"{col_a} vs {col_b} (sized by {size_col.name})",
        description=f"Bubble chart with size encoding on {size_col.name}",
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

    return [ChartRecommendation(
        chart_type=ChartType.PARALLEL_COORDS,
        columns=col_names,
        title="Parallel Coordinates Overview",
        description=f"Multivariate view across {len(col_names)} numeric dimensions",
        interestingness=0.7,
        annotation=(
            f"Parallel coordinates plot reveals multivariate patterns across "
            f"{len(col_names)} variables. Crossing lines indicate inverse relationships."
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

    return [ChartRecommendation(
        chart_type=ChartType.RADAR,
        columns=col_names,
        title="Multi-Metric Radar Profile",
        description=f"Comparative profile across {len(col_names)} normalized metrics",
        interestingness=0.75,
        annotation="Radar chart shows the normalized mean of each metric, revealing the dataset's characteristic profile.",
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

            return [ChartRecommendation(
                chart_type=ChartType.WATERFALL,
                columns=[cat.name, num.name],
                title=f"Waterfall: {num.name} by {cat.name}",
                description=f"Cumulative contribution of each {cat.name} to total {num.name}",
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
        results.append(ChartRecommendation(
            chart_type=ChartType.PCA_BIPLOT,
            columns=col_names,
            title="PCA Biplot",
            description=f"First 2 principal components explain {total_2d:.1%} of variance",
            interestingness=0.85,
            annotation=(
                f"PCA reduces {len(col_names)} dimensions to 2 components capturing "
                f"{total_2d:.1%} of total variance. Arrows show original variable loadings."
            ),
        ))

    if stat_report.clusters and len(col_names) >= 3:
        k = stat_report.clusters.optimal_k
        sil = stat_report.clusters.silhouette_score
        results.append(ChartRecommendation(
            chart_type=ChartType.CLUSTER_SCATTER,
            columns=col_names,
            title=f"Cluster Analysis ({k} clusters)",
            description=f"K-means clustering projected to 2D via PCA (silhouette: {sil:.2f})",
            interestingness=0.9,
            annotation=f"{k} clusters detected with silhouette score {sil:.2f}. Points colored by cluster membership.",
        ))

    if stat_report.anomalies and len(col_names) >= 2:
        n = stat_report.anomalies.n_anomalies
        pct = stat_report.anomalies.anomaly_pct
        results.append(ChartRecommendation(
            chart_type=ChartType.ANOMALY_SCATTER,
            columns=col_names,
            title=f"Anomaly Detection ({n} anomalies)",
            description=f"Isolation Forest detected {n} anomalous records ({pct}%)",
            interestingness=0.85,
            annotation=(
                f"{n} anomalous records ({pct}%) identified via Isolation Forest. "
                f"Red markers show outlier points in PCA-projected space."
            ),
        ))

    return results
