"""Automated statistical analysis: anomaly detection, clustering, PCA, tests."""

from __future__ import annotations

import pandas as pd

from models.schemas import DataProfile, StatisticalReport
from services.statistics.anomaly_detection import detect_anomalies
from services.statistics.clustering import find_clusters
from services.statistics.pca import run_pca
from services.statistics.statistical_tests import run_tests

MIN_ROWS_ANOMALY = 50
MIN_NUMERIC_COLS_CLUSTER = 3
MIN_NUMERIC_COLS_PCA = 4
MIN_ROWS_CLUSTER = 30


def run_statistical_analysis(
    df: pd.DataFrame, profile: DataProfile,
) -> StatisticalReport:
    """Orchestrate all statistical analyses, skipping when data doesn't qualify."""
    numeric_cols = [
        c.name for c in profile.columns if c.inferred_type == "numeric"
    ]
    categorical_cols = [
        c.name for c in profile.columns if c.inferred_type == "categorical"
    ]

    anomalies = None
    if len(numeric_cols) >= 1 and len(df) >= MIN_ROWS_ANOMALY:
        anomalies = detect_anomalies(df, numeric_cols)

    clusters = None
    if len(numeric_cols) >= MIN_NUMERIC_COLS_CLUSTER and len(df) >= MIN_ROWS_CLUSTER:
        clusters = find_clusters(df, numeric_cols)

    pca = None
    if len(numeric_cols) >= MIN_NUMERIC_COLS_PCA:
        pca = run_pca(df, numeric_cols)

    tests = run_tests(df, numeric_cols, categorical_cols)

    return StatisticalReport(
        anomalies=anomalies,
        clusters=clusters,
        pca=pca,
        tests=tests,
    )
