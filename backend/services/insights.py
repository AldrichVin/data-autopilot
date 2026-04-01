"""Auto-generate data quality alerts and key findings from profiled data."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.schemas import Alert, DataProfile


# ---------------------------------------------------------------------------
# Thresholds (inspired by ydata-profiling defaults)
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

    # Duplicate rows
    if profile.duplicate_row_count > 0:
        pct = round(profile.duplicate_row_count / profile.total_rows * 100, 1)
        alerts.append(Alert(
            severity="warning",
            category="duplicates",
            message=(
                f"Dataset contains {profile.duplicate_row_count:,} "
                f"duplicate rows ({pct}%)"
            ),
        ))

    for col in profile.columns:
        # High missing values
        if col.null_pct >= MISSING_WARN_PCT:
            alerts.append(Alert(
                severity="warning",
                category="missing",
                message=(
                    f"Column '{col.name}' has {col.null_pct:.1f}% missing "
                    f"values ({col.null_count:,} rows)"
                ),
                column=col.name,
            ))

        # Constant column
        if col.unique_count == 1:
            val = col.sample_values[0] if col.sample_values else "N/A"
            alerts.append(Alert(
                severity="warning",
                category="constant",
                message=f"Column '{col.name}' contains a single constant value: '{val}'",
                column=col.name,
            ))

        # All-unique (potential ID)
        if col.unique_count == profile.total_rows and profile.total_rows > 1:
            alerts.append(Alert(
                severity="info",
                category="unique",
                message=f"Column '{col.name}' has all unique values — possible ID column",
                column=col.name,
            ))

        # High cardinality in categorical
        if col.inferred_type == "categorical" and col.unique_count > HIGH_CARDINALITY:
            alerts.append(Alert(
                severity="info",
                category="cardinality",
                message=(
                    f"Column '{col.name}' has high cardinality "
                    f"({col.unique_count} unique values)"
                ),
                column=col.name,
            ))

    # Numeric-specific alerts
    numeric_cols = [c.name for c in profile.columns if c.inferred_type == "numeric"]
    if len(numeric_cols) >= 2:
        numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        # High correlation
        corr = numeric_df.corr()
        seen: set[tuple[str, str]] = set()
        for i, col_a in enumerate(numeric_cols):
            for col_b in numeric_cols[i + 1:]:
                key = (col_a, col_b)
                if key in seen:
                    continue
                seen.add(key)
                val = corr.loc[col_a, col_b]
                if not np.isnan(val) and abs(val) >= CORRELATION_THRESHOLD:
                    alerts.append(Alert(
                        severity="info",
                        category="correlation",
                        message=(
                            f"'{col_a}' and '{col_b}' are strongly "
                            f"correlated (r={val:.2f})"
                        ),
                    ))

        # Skewness
        for col_name in numeric_cols:
            series = pd.to_numeric(df[col_name], errors="coerce").dropna()
            if len(series) > 2:
                skew = float(series.skew())
                if abs(skew) >= SKEWNESS_THRESHOLD:
                    alerts.append(Alert(
                        severity="info",
                        category="skewed",
                        message=f"Column '{col_name}' is highly skewed (skewness: {skew:.2f})",
                        column=col_name,
                    ))

        # High zeros
        for col_name in numeric_cols:
            series = pd.to_numeric(df[col_name], errors="coerce")
            zero_pct = (series == 0).mean() * 100
            if zero_pct >= ZEROS_WARN_PCT:
                alerts.append(Alert(
                    severity="info",
                    category="zeros",
                    message=(
                        f"Column '{col_name}' has {zero_pct:.1f}% zero values"
                    ),
                    column=col_name,
                ))

    # Class imbalance in categorical columns
    cat_cols = [c for c in profile.columns if c.inferred_type == "categorical"]
    for col in cat_cols:
        if col.unique_count >= 2:
            counts = df[col.name].value_counts(normalize=True)
            if len(counts) > 0 and counts.iloc[0] >= IMBALANCE_THRESHOLD:
                dominant = counts.index[0]
                alerts.append(Alert(
                    severity="warning",
                    category="imbalanced",
                    message=(
                        f"Column '{col.name}' is imbalanced — "
                        f"'{dominant}' accounts for {counts.iloc[0]*100:.1f}%"
                    ),
                    column=col.name,
                ))

    return alerts


# ---------------------------------------------------------------------------
# Key findings (executive summary bullets)
# ---------------------------------------------------------------------------

def derive_key_findings(
    profile: DataProfile,
    alerts: list[Alert],
    df: pd.DataFrame,
) -> list[str]:
    findings: list[str] = []

    # Dataset overview
    findings.append(
        f"Dataset contains {profile.total_rows:,} rows and "
        f"{profile.total_columns} columns"
    )

    # Data completeness
    total_cells = profile.total_rows * profile.total_columns
    total_missing = sum(c.null_count for c in profile.columns)
    completeness = (1 - total_missing / total_cells) * 100 if total_cells > 0 else 100
    findings.append(f"Overall data completeness: {completeness:.1f}%")

    # Duplicate summary
    if profile.duplicate_row_count > 0:
        findings.append(
            f"{profile.duplicate_row_count:,} duplicate rows detected "
            f"({profile.duplicate_row_count / profile.total_rows * 100:.1f}%)"
        )

    # Strongest correlation
    corr_alerts = [a for a in alerts if a.category == "correlation"]
    if corr_alerts:
        findings.append(corr_alerts[0].message)

    # Most problematic column (highest missing %)
    missing_cols = sorted(
        [c for c in profile.columns if c.null_pct > 0],
        key=lambda c: c.null_pct,
        reverse=True,
    )
    if missing_cols:
        worst = missing_cols[0]
        findings.append(
            f"Column with most missing data: '{worst.name}' ({worst.null_pct:.1f}%)"
        )

    # Column type breakdown
    type_counts: dict[str, int] = {}
    for c in profile.columns:
        type_counts[c.inferred_type] = type_counts.get(c.inferred_type, 0) + 1
    breakdown = ", ".join(f"{v} {k}" for k, v in sorted(type_counts.items()))
    findings.append(f"Column types: {breakdown}")

    # Alert summary
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
