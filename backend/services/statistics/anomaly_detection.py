"""Anomaly detection using Isolation Forest."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.schemas import AnomalyResult

CONTAMINATION = 0.05  # expect ~5% anomalies


def detect_anomalies(
    df: pd.DataFrame, numeric_cols: list[str],
) -> AnomalyResult | None:
    from sklearn.ensemble import IsolationForest

    numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_df) < 20:
        return None

    model = IsolationForest(
        contamination=CONTAMINATION, random_state=42, n_jobs=-1,
    )
    labels = model.fit_predict(numeric_df)
    anomaly_mask = labels == -1
    n_anomalies = int(anomaly_mask.sum())

    if n_anomalies == 0:
        return None

    # Rank columns by how much anomalies deviate from normal points
    top_columns = _rank_anomaly_columns(numeric_df, anomaly_mask)

    return AnomalyResult(
        method="isolation_forest",
        n_anomalies=n_anomalies,
        anomaly_pct=round(n_anomalies / len(numeric_df) * 100, 1),
        top_anomaly_columns=top_columns[:5],
    )


def _rank_anomaly_columns(
    df: pd.DataFrame, anomaly_mask: np.ndarray,
) -> list[str]:
    """Rank columns by mean absolute z-score difference between anomalies and normals."""
    normals = df[~anomaly_mask]
    anomalies = df[anomaly_mask]

    scores: list[tuple[str, float]] = []
    for col in df.columns:
        normal_mean = normals[col].mean()
        normal_std = normals[col].std()
        if normal_std == 0:
            continue
        anomaly_z = abs((anomalies[col].mean() - normal_mean) / normal_std)
        scores.append((col, float(anomaly_z)))

    scores.sort(key=lambda x: x[1], reverse=True)
    return [col for col, _ in scores]
