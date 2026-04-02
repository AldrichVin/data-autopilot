"""Data quality alerts, key findings, and narrative generation.

Follows the McKinsey pyramid principle: lead with the conclusion,
then provide supporting evidence.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.schemas import Alert, DataProfile, ReportChart, SectionNarrative, StatisticalReport


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
MISSING_WARN_PCT = 10.0
ZEROS_WARN_PCT = 10.0
CORRELATION_THRESHOLD = 0.80
SKEWNESS_THRESHOLD = 2.0
IMBALANCE_THRESHOLD = 0.80
HIGH_CARDINALITY = 50


# ---------------------------------------------------------------------------
# Alert generation
# ---------------------------------------------------------------------------

def generate_alerts(profile: DataProfile, df: pd.DataFrame) -> list[Alert]:
    alerts: list[Alert] = []

    if profile.duplicate_row_count > 0:
        pct = round(profile.duplicate_row_count / profile.total_rows * 100, 1)
        alerts.append(Alert(
            severity="warning", category="duplicates",
            message=f"Dataset contains {profile.duplicate_row_count:,} duplicate rows ({pct}%)",
        ))

    for col in profile.columns:
        if col.null_pct >= MISSING_WARN_PCT:
            alerts.append(Alert(
                severity="warning", category="missing",
                message=f"Column '{col.name}' has {col.null_pct:.1f}% missing values ({col.null_count:,} rows)",
                column=col.name,
            ))
        if col.unique_count == 1:
            val = col.sample_values[0] if col.sample_values else "N/A"
            alerts.append(Alert(
                severity="warning", category="constant",
                message=f"Column '{col.name}' contains a single constant value: '{val}'",
                column=col.name,
            ))
        if col.unique_count == profile.total_rows and profile.total_rows > 1:
            alerts.append(Alert(
                severity="info", category="unique",
                message=f"Column '{col.name}' has all unique values — possible ID column",
                column=col.name,
            ))
        if col.inferred_type == "categorical" and col.unique_count > HIGH_CARDINALITY:
            alerts.append(Alert(
                severity="info", category="cardinality",
                message=f"Column '{col.name}' has high cardinality ({col.unique_count} unique values)",
                column=col.name,
            ))

    numeric_cols = [c.name for c in profile.columns if c.inferred_type == "numeric"]
    if len(numeric_cols) >= 2:
        numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        corr = numeric_df.corr()
        seen: set[tuple[str, str]] = set()
        for i, col_a in enumerate(numeric_cols):
            for col_b in numeric_cols[i + 1:]:
                if (col_a, col_b) in seen:
                    continue
                seen.add((col_a, col_b))
                val = corr.loc[col_a, col_b]
                if not np.isnan(val) and abs(val) >= CORRELATION_THRESHOLD:
                    alerts.append(Alert(
                        severity="info", category="correlation",
                        message=f"'{col_a}' and '{col_b}' are strongly correlated (r={val:.2f})",
                    ))

        for col_name in numeric_cols:
            series = pd.to_numeric(df[col_name], errors="coerce").dropna()
            if len(series) > 2 and abs(float(series.skew())) >= SKEWNESS_THRESHOLD:
                alerts.append(Alert(
                    severity="info", category="skewed",
                    message=f"Column '{col_name}' is highly skewed (skewness: {float(series.skew()):.2f})",
                    column=col_name,
                ))
            zero_pct = (series == 0).mean() * 100
            if zero_pct >= ZEROS_WARN_PCT:
                alerts.append(Alert(
                    severity="info", category="zeros",
                    message=f"Column '{col_name}' has {zero_pct:.1f}% zero values",
                    column=col_name,
                ))

    for col in [c for c in profile.columns if c.inferred_type == "categorical"]:
        if col.unique_count >= 2:
            counts = df[col.name].value_counts(normalize=True)
            if len(counts) > 0 and counts.iloc[0] >= IMBALANCE_THRESHOLD:
                alerts.append(Alert(
                    severity="warning", category="imbalanced",
                    message=f"Column '{col.name}' is imbalanced — '{counts.index[0]}' accounts for {counts.iloc[0]*100:.1f}%",
                    column=col.name,
                ))

    return alerts


def group_alerts_by_severity(alerts: list[Alert]) -> dict[str, list[Alert]]:
    grouped: dict[str, list[Alert]] = {"danger": [], "warning": [], "info": []}
    for a in alerts:
        grouped.setdefault(a.severity, []).append(a)
    return grouped


# ---------------------------------------------------------------------------
# Key findings (executive bullets)
# ---------------------------------------------------------------------------

def derive_key_findings(
    profile: DataProfile, alerts: list[Alert], df: pd.DataFrame,
) -> list[str]:
    findings: list[str] = []

    # --- Correlation insights (actionable) ---
    numeric_cols = [c.name for c in profile.columns if c.inferred_type == "numeric"]
    if len(numeric_cols) >= 2:
        numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        corr = numeric_df.corr()
        strong_pairs = []
        for i, col_a in enumerate(numeric_cols):
            for col_b in numeric_cols[i + 1:]:
                val = corr.loc[col_a, col_b]
                if not np.isnan(val) and abs(val) >= 0.8:
                    strong_pairs.append((col_a, col_b, float(val)))
        strong_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        if strong_pairs:
            top = strong_pairs[0]
            finding = f"'{top[0]}' and '{top[1]}' are strongly correlated (r={top[2]:.2f})"
            if abs(top[2]) > 0.9:
                finding += " — consider dropping one to reduce multicollinearity"
            findings.append(finding)
        if len(strong_pairs) > 1:
            findings.append(
                f"{len(strong_pairs)} highly correlated pairs detected — "
                f"potential redundancy in the feature set"
            )

    # --- Skewness summary ---
    skewed_cols = [
        c for c in profile.columns
        if c.inferred_type == "numeric" and c.stats and abs(c.stats.skewness) > 1.5
    ]
    if skewed_cols:
        names = ", ".join(c.name for c in skewed_cols[:3])
        directions = [("right" if c.stats.skewness > 0 else "left") for c in skewed_cols[:3]]
        findings.append(
            f"Highly skewed columns: {names} ({'/'.join(directions)}-skewed). "
            f"Consider log or Box-Cox transformation for modeling"
        )

    # --- Outlier summary ---
    outlier_cols = []
    for c in profile.columns:
        if c.inferred_type == "numeric":
            series = pd.to_numeric(df[c.name], errors="coerce").dropna()
            if len(series) >= 4:
                q1, q3 = series.quantile(0.25), series.quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    n_outliers = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())
                    if n_outliers > 0:
                        outlier_cols.append((c.name, n_outliers))
    if outlier_cols:
        outlier_cols.sort(key=lambda x: x[1], reverse=True)
        worst = outlier_cols[0]
        findings.append(
            f"'{worst[0]}' has the most outliers ({worst[1]} records beyond 1.5× IQR)"
            + (f" among {len(outlier_cols)} columns with outliers" if len(outlier_cols) > 1 else "")
        )

    # --- Missing data insight (only if noteworthy) ---
    missing_cols = sorted(
        [c for c in profile.columns if c.null_pct > 5],
        key=lambda c: c.null_pct, reverse=True,
    )
    if missing_cols:
        worst = missing_cols[0]
        findings.append(
            f"'{worst.name}' has {worst.null_pct:.1f}% missing values — "
            f"investigate whether missingness is random or systematic"
        )

    # --- Duplicate rows (only if significant) ---
    if profile.duplicate_row_count > 0:
        dup_pct = profile.duplicate_row_count / profile.total_rows * 100
        if dup_pct > 1:
            findings.append(
                f"{profile.duplicate_row_count:,} duplicate rows ({dup_pct:.1f}%) — "
                f"verify these are genuine records, not data collection errors"
            )

    # --- Imbalanced categories ---
    imbalanced = [a for a in alerts if a.category == "imbalanced"]
    if imbalanced:
        findings.append(imbalanced[0].message)

    return findings


# ---------------------------------------------------------------------------
# Narrative generation (McKinsey pyramid: conclusion → evidence)
# ---------------------------------------------------------------------------

def generate_executive_narrative(
    profile: DataProfile, alerts: list[Alert], df: pd.DataFrame
) -> str:
    total_cells = profile.total_rows * profile.total_columns
    total_missing = sum(c.null_count for c in profile.columns)
    completeness = (1 - total_missing / total_cells) * 100 if total_cells > 0 else 100

    numeric_cols = [c for c in profile.columns if c.inferred_type == "numeric"]
    categorical_cols = [c for c in profile.columns if c.inferred_type == "categorical"]

    warnings = [a for a in alerts if a.severity in ("warning", "danger")]
    corr_alerts = [a for a in alerts if a.category == "correlation"]

    # Lead with the most important analytical insight
    insights = []

    if corr_alerts:
        insights.append(
            f"Strong correlations detected between {len(corr_alerts)} variable pair"
            f"{'s' if len(corr_alerts) != 1 else ''}, "
            f"suggesting potential feature redundancy"
        )

    skewed = [c for c in numeric_cols if c.stats and abs(c.stats.skewness) > 1.5]
    if skewed:
        insights.append(
            f"{len(skewed)} numeric variable{'s' if len(skewed) != 1 else ''} "
            f"show{'s' if len(skewed) == 1 else ''} significant skew, "
            f"which may affect model assumptions"
        )

    if warnings:
        issue_types = list({a.category for a in warnings})
        insights.append(
            f"{len(warnings)} data quality warning{'s' if len(warnings) != 1 else ''} "
            f"flagged in {', '.join(issue_types[:3])}"
        )

    opening = (
        f"Analysis of {profile.total_rows:,} records across "
        f"{len(numeric_cols)} numeric and {len(categorical_cols)} categorical variables "
        f"reveals a dataset with {completeness:.0f}% completeness. "
    )

    if insights:
        opening += " ".join(f"{s}." for s in insights[:2])
    elif completeness >= 95:
        opening += "The data is well-structured with no major quality concerns."
    else:
        opening += "Some data quality issues warrant attention before analysis."

    return opening


def generate_data_overview_narrative(
    profile: DataProfile, df: pd.DataFrame
) -> str:
    type_counts: dict[str, int] = {}
    for c in profile.columns:
        key = c.inferred_type.value if hasattr(c.inferred_type, "value") else str(c.inferred_type)
        type_counts[key] = type_counts.get(key, 0) + 1

    parts = []
    for t in ["numeric", "categorical", "datetime", "text", "boolean"]:
        if t in type_counts:
            parts.append(f"{type_counts[t]} {t}")

    narrative = f"The dataset contains {', '.join(parts)} column{'s' if profile.total_columns != 1 else ''}. "

    if profile.duplicate_row_count > 0:
        narrative += (
            f"{profile.duplicate_row_count:,} duplicate rows were identified, "
            f"representing {profile.duplicate_row_count / profile.total_rows * 100:.1f}% of the data. "
        )

    missing_cols = [c for c in profile.columns if c.null_pct > 0]
    if missing_cols:
        narrative += (
            f"{len(missing_cols)} column{'s' if len(missing_cols) != 1 else ''} "
            f"contain missing values."
        )
    else:
        narrative += "No missing values were detected across any column."

    return narrative


def generate_section_narrative(
    section_key: str,
    charts: list[ReportChart],
    profile: DataProfile,
    df: pd.DataFrame,
) -> SectionNarrative:
    chart_count = len(charts)

    if section_key == "distributions":
        numeric_cols = [c for c in profile.columns if c.inferred_type == "numeric"]
        skewed = [c for c in numeric_cols if c.stats and abs(c.stats.skewness) > 1.0]
        symmetric = [c for c in numeric_cols if c.stats and abs(c.stats.skewness) <= 1.0]

        headline_parts = []
        if skewed:
            names = ", ".join(c.name for c in skewed[:3])
            directions = []
            for c in skewed[:3]:
                d = "right" if c.stats.skewness > 0 else "left"
                directions.append(f"{c.name} ({d})")
            headline_parts.append(f"Skewed variables: {', '.join(directions)}")
        if symmetric and len(symmetric) <= 5:
            headline_parts.append(
                f"{', '.join(c.name for c in symmetric[:3])} are approximately normally distributed"
            )

        headline = ". ".join(headline_parts) + "." if headline_parts else (
            f"{chart_count} distributions examined across key variables."
        )
        body = ""
        if skewed:
            body = (
                f"{len(skewed)} of {len(numeric_cols)} numeric variables show notable skewness. "
                f"Skewed distributions can bias mean-based statistics — "
                f"consider median for summary and log/Box-Cox transforms for modeling."
            )
        return SectionNarrative(headline=headline, body=body)

    if section_key == "relationships":
        # Compute actual correlation info
        numeric_cols = [c.name for c in profile.columns if c.inferred_type == "numeric"]
        strong_count = 0
        top_pair_str = ""
        if len(numeric_cols) >= 2:
            numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
            corr = numeric_df.corr()
            pairs = []
            for i, a in enumerate(numeric_cols):
                for b in numeric_cols[i + 1:]:
                    val = corr.loc[a, b]
                    if not np.isnan(val) and abs(val) >= 0.7:
                        strong_count += 1
                        pairs.append((a, b, val))
            if pairs:
                pairs.sort(key=lambda x: abs(x[2]), reverse=True)
                top = pairs[0]
                top_pair_str = f"Strongest: {top[0]} and {top[1]} (r={top[2]:.2f}). "

        headline = (
            f"{top_pair_str}"
            f"{strong_count} strong correlation{'s' if strong_count != 1 else ''} found "
            f"across {len(numeric_cols)} numeric variables."
            if strong_count > 0 else
            f"Relationship analysis across {len(numeric_cols)} numeric variables."
        )
        body = (
            "Strong positive correlations suggest variables that move together — "
            "these may be redundant for predictive models. "
            "Negative correlations reveal inverse relationships worth investigating."
        )
        return SectionNarrative(headline=headline, body=body)

    if section_key == "temporal":
        headline = "Temporal analysis tracks how key metrics evolve over time."
        body = "Look for trends, seasonality, or anomalous periods that may require attention."
        return SectionNarrative(headline=headline, body=body)

    if section_key == "data_quality":
        missing_cols = [c for c in profile.columns if c.null_pct > 1]
        if missing_cols:
            worst = max(missing_cols, key=lambda c: c.null_pct)
            headline = (
                f"{len(missing_cols)} columns have >1% missing data. "
                f"'{worst.name}' is most affected at {worst.null_pct:.1f}%."
            )
        else:
            headline = "Data quality visualizations expose patterns in missing or problematic values."
        body = "Systematic patterns in missing data can reveal data collection issues rather than random gaps."
        return SectionNarrative(headline=headline, body=body)

    if section_key == "statistical_analysis":
        techniques = []
        for chart in charts:
            ct = chart.chart_type.value if hasattr(chart.chart_type, "value") else str(chart.chart_type)
            if "pca" in ct.lower():
                techniques.append("dimensionality reduction (PCA)")
            elif "cluster" in ct.lower():
                techniques.append("clustering")
            elif "anomaly" in ct.lower():
                techniques.append("anomaly detection")
        technique_str = ", ".join(techniques) if techniques else "machine learning techniques"

        headline = (
            f"Statistical analysis using {technique_str} reveals "
            f"hidden structure not visible in basic charts."
        )
        body = (
            "These analyses look at all numeric variables simultaneously to find "
            "natural groupings, unusual records, and the most important dimensions of variation."
        )
        return SectionNarrative(headline=headline, body=body)

    return SectionNarrative(headline=f"This section presents {chart_count} visualization{'s' if chart_count != 1 else ''}.")


# ---------------------------------------------------------------------------
# Statistical findings
# ---------------------------------------------------------------------------

def generate_statistical_findings(
    stat_report: StatisticalReport,
) -> list[str]:
    """Produce executive-summary bullets from statistical analysis results."""
    findings: list[str] = []

    if stat_report.clusters:
        c = stat_report.clusters
        quality = (
            "well-defined" if c.silhouette_score > 0.5
            else "moderately distinct" if c.silhouette_score > 0.25
            else "weakly separated"
        )
        finding = f"{c.optimal_k} {quality} natural groupings detected in the data"
        if c.cluster_sizes:
            finding += f" (largest group: {max(c.cluster_sizes)} records, smallest: {min(c.cluster_sizes)})"
        findings.append(finding)

    if stat_report.pca:
        p = stat_report.pca
        n = p.n_components_95
        total_vars = len(p.explained_variance) if p.explained_variance else 0
        finding = (
            f"Data complexity can be reduced: {n} principal component"
            f"{'s' if n != 1 else ''} capture 95% of variance"
        )
        if total_vars > 0:
            finding += f" (out of {total_vars} original variables)"
        findings.append(finding)

    if stat_report.anomalies:
        a = stat_report.anomalies
        finding = (
            f"{a.n_anomalies} statistically unusual records ({a.anomaly_pct}%) identified — "
            f"investigate for data errors or genuine exceptions"
        )
        if a.top_anomaly_columns:
            finding += f". Most affected columns: {', '.join(a.top_anomaly_columns[:3])}"
        findings.append(finding)

    significant_assoc = [
        t for t in stat_report.tests
        if t.test_name == "Chi-square" and t.p_value < 0.05
    ]
    if significant_assoc:
        cols_involved = []
        for t in significant_assoc[:2]:
            cols_involved.extend(t.columns)
        findings.append(
            f"{len(significant_assoc)} significant categorical association"
            f"{'s' if len(significant_assoc) != 1 else ''} found "
            f"(e.g. {', '.join(cols_involved[:4])})"
        )

    return findings
