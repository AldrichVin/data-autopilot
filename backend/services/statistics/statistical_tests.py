"""Statistical hypothesis tests: normality, independence, correlation significance."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from models.schemas import StatTestResult

MAX_NORMALITY_TESTS = 8
MAX_CHI2_PAIRS = 6
SHAPIRO_MAX_N = 5000


def run_tests(
    df: pd.DataFrame,
    numeric_cols: list[str],
    categorical_cols: list[str],
) -> list[StatTestResult]:
    results: list[StatTestResult] = []
    results.extend(_normality_tests(df, numeric_cols))
    results.extend(_chi_square_tests(df, categorical_cols))
    results.extend(_correlation_pvalues(df, numeric_cols))
    return results


def _normality_tests(
    df: pd.DataFrame, numeric_cols: list[str],
) -> list[StatTestResult]:
    results: list[StatTestResult] = []
    for col in numeric_cols[:MAX_NORMALITY_TESTS]:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 8:
            continue
        # Shapiro-Wilk (sample if too large)
        sample = series.sample(min(len(series), SHAPIRO_MAX_N), random_state=42)
        stat, p = stats.shapiro(sample)

        if p < 0.001:
            interp = f"'{col}' is not normally distributed (p < 0.001)"
        elif p < 0.05:
            interp = f"'{col}' deviates from normality (p = {p:.4f})"
        else:
            interp = f"'{col}' is consistent with a normal distribution (p = {p:.4f})"

        results.append(StatTestResult(
            test_name="Shapiro-Wilk",
            columns=[col],
            statistic=round(float(stat), 4),
            p_value=round(float(p), 6),
            interpretation=interp,
        ))
    return results


def _chi_square_tests(
    df: pd.DataFrame, categorical_cols: list[str],
) -> list[StatTestResult]:
    results: list[StatTestResult] = []
    pairs_tested = 0
    for i, col_a in enumerate(categorical_cols):
        if df[col_a].nunique() < 2 or df[col_a].nunique() > 20:
            continue
        for col_b in categorical_cols[i + 1:]:
            if pairs_tested >= MAX_CHI2_PAIRS:
                break
            if df[col_b].nunique() < 2 or df[col_b].nunique() > 20:
                continue

            contingency = pd.crosstab(df[col_a], df[col_b])
            if contingency.shape[0] < 2 or contingency.shape[1] < 2:
                continue

            chi2, p, dof, _ = stats.chi2_contingency(contingency)
            pairs_tested += 1

            if p < 0.001:
                interp = f"'{col_a}' and '{col_b}' are strongly associated (p < 0.001)"
            elif p < 0.05:
                interp = f"'{col_a}' and '{col_b}' show significant association (p = {p:.4f})"
            else:
                interp = f"No significant association between '{col_a}' and '{col_b}' (p = {p:.4f})"

            results.append(StatTestResult(
                test_name="Chi-square",
                columns=[col_a, col_b],
                statistic=round(float(chi2), 2),
                p_value=round(float(p), 6),
                interpretation=interp,
            ))
    return results


def _correlation_pvalues(
    df: pd.DataFrame, numeric_cols: list[str],
) -> list[StatTestResult]:
    results: list[StatTestResult] = []
    if len(numeric_cols) < 2:
        return results

    # Only test the strongest correlations
    numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_df) < 10:
        return results

    corr = numeric_df.corr()
    tested = 0
    pairs: list[tuple[str, str, float]] = []
    for i, col_a in enumerate(numeric_cols):
        for col_b in numeric_cols[i + 1:]:
            r = corr.loc[col_a, col_b]
            if not np.isnan(r) and abs(r) >= 0.3:
                pairs.append((col_a, col_b, float(r)))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)

    for col_a, col_b, r in pairs[:6]:
        x = numeric_df[col_a]
        y = numeric_df[col_b]
        _, p = stats.pearsonr(x, y)
        tested += 1

        sig = "significant" if p < 0.05 else "not significant"
        results.append(StatTestResult(
            test_name="Pearson correlation",
            columns=[col_a, col_b],
            statistic=round(r, 4),
            p_value=round(float(p), 6),
            interpretation=f"r = {r:.2f} between '{col_a}' and '{col_b}' is {sig} (p = {p:.4f})",
        ))
    return results
