"""K-means clustering with automatic k selection via silhouette score."""

from __future__ import annotations

import pandas as pd

from models.schemas import ClusterResult

MIN_K = 2
MAX_K = 8


def find_clusters(
    df: pd.DataFrame, numeric_cols: list[str],
) -> ClusterResult | None:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_df) < MAX_K * 3:
        return None

    scaled = StandardScaler().fit_transform(numeric_df)

    best_k = MIN_K
    best_score = -1.0
    best_labels = None

    upper = min(MAX_K, len(numeric_df) - 1)
    for k in range(MIN_K, upper + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(scaled)
        score = float(silhouette_score(scaled, labels))
        if score > best_score:
            best_score = score
            best_k = k
            best_labels = labels

    if best_labels is None or best_score < 0.2:
        return None

    cluster_sizes = [
        int((best_labels == i).sum()) for i in range(best_k)
    ]

    return ClusterResult(
        optimal_k=best_k,
        silhouette_score=round(best_score, 3),
        cluster_sizes=sorted(cluster_sizes, reverse=True),
    )
