"""Data quality alerts, key findings, and narrative generation.

Follows the McKinsey pyramid principle: lead with the conclusion,
then provide supporting evidence.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.schemas import Alert, DataProfile, ReportChart, SectionNarrative


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

    findings.append(
        f"Dataset contains {profile.total_rows:,} rows and {profile.total_columns} columns"
    )

    total_cells = profile.total_rows * profile.total_columns
    total_missing = sum(c.null_count for c in profile.columns)
    completeness = (1 - total_missing / total_cells) * 100 if total_cells > 0 else 100
    findings.append(f"Overall data completeness: {completeness:.1f}%")

    if profile.duplicate_row_count > 0:
        findings.append(
            f"{profile.duplicate_row_count:,} duplicate rows detected "
            f"({profile.duplicate_row_count / profile.total_rows * 100:.1f}%)"
        )

    corr_alerts = [a for a in alerts if a.category == "correlation"]
    if corr_alerts:
        findings.append(corr_alerts[0].message)

    missing_cols = sorted(
        [c for c in profile.columns if c.null_pct > 0],
        key=lambda c: c.null_pct, reverse=True,
    )
    if missing_cols:
        worst = missing_cols[0]
        findings.append(f"Column with most missing data: '{worst.name}' ({worst.null_pct:.1f}%)")

    type_counts: dict[str, int] = {}
    for c in profile.columns:
        key = c.inferred_type.value if hasattr(c.inferred_type, "value") else str(c.inferred_type)
        type_counts[key] = type_counts.get(key, 0) + 1
    breakdown = ", ".join(f"{v} {k}" for k, v in sorted(type_counts.items()))
    findings.append(f"Column types: {breakdown}")

    warning_count = sum(1 for a in alerts if a.severity == "warning")
    info_count = sum(1 for a in alerts if a.severity == "info")
    if warning_count or info_count:
        parts = []
        if warning_count:
            parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")
        if info_count:
            parts.append(f"{info_count} info alert{'s' if info_count != 1 else ''}")
        findings.append(f"Data quality alerts: {', '.join(parts)}")

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

    type_counts: dict[str, int] = {}
    for c in profile.columns:
        key = c.inferred_type.value if hasattr(c.inferred_type, "value") else str(c.inferred_type)
        type_counts[key] = type_counts.get(key, 0) + 1

    warnings = [a for a in alerts if a.severity in ("warning", "danger")]
    quality_desc = "high" if completeness >= 95 and not warnings else "moderate" if completeness >= 80 else "low"

    opening = (
        f"This dataset comprises {profile.total_rows:,} records across "
        f"{profile.total_columns} variables, achieving {completeness:.1f}% data completeness. "
    )

    if quality_desc == "high":
        opening += "Overall data quality is strong, with minimal issues detected."
    elif warnings:
        issue_types = list({a.category for a in warnings})
        opening += (
            f"Data quality assessment identified {len(warnings)} warning"
            f"{'s' if len(warnings) != 1 else ''}, "
            f"primarily related to {', '.join(issue_types[:3])}."
        )
    else:
        opening += "The dataset is largely clean with a few informational observations."

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
        headline = (
            f"Analysis of {chart_count} distribution"
            f"{'s' if chart_count != 1 else ''} reveals the shape and spread of key variables."
        )
        body = ""
        if skewed:
            names = ", ".join(c.name for c in skewed[:3])
            body = f"Notable skewness was detected in {names}, which may warrant transformation for modeling."
        return SectionNarrative(headline=headline, body=body)

    if section_key == "relationships":
        headline = (
            f"{chart_count} relationship visualization"
            f"{'s' if chart_count != 1 else ''} highlight correlations and dependencies between variables."
        )
        return SectionNarrative(headline=headline, body="Strong correlations may indicate redundant features or causal relationships worth investigating.")

    if section_key == "temporal":
        headline = "Temporal analysis tracks how key metrics evolve over time."
        return SectionNarrative(headline=headline, body="Look for trends, seasonality, or anomalous periods that may require attention.")

    if section_key == "data_quality":
        headline = "Data quality visualizations expose patterns in missing or problematic values."
        return SectionNarrative(headline=headline, body="Systematic patterns in missing data can reveal data collection issues.")

    return SectionNarrative(headline=f"This section presents {chart_count} visualization{'s' if chart_count != 1 else ''}.")
