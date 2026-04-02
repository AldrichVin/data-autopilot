"""PCA dimensionality reduction analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.schemas import PCAResult


def run_pca(
    df: pd.DataFrame, numeric_cols: list[str],
) -> PCAResult | None:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    numeric_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_df) < 10:
        return None

    scaled = StandardScaler().fit_transform(numeric_df)
    n_components = min(len(numeric_cols), len(numeric_df))
    pca = PCA(n_components=n_components)
    pca.fit(scaled)

    explained = [round(float(v), 4) for v in pca.explained_variance_ratio_]
    cumulative = float(np.cumsum(explained)[-1]) if explained else 0.0

    # Components needed for 95% variance
    cumsum = np.cumsum(explained)
    n_for_95 = int(np.searchsorted(cumsum, 0.95) + 1)
    n_for_95 = min(n_for_95, len(explained))

    # Top loadings per component (first 3 components)
    top_loadings: dict[str, list[tuple[str, float]]] = {}
    for i in range(min(3, len(explained))):
        loadings = list(zip(numeric_cols, pca.components_[i]))
        loadings.sort(key=lambda x: abs(x[1]), reverse=True)
        top_loadings[f"PC{i + 1}"] = [
            (name, round(float(val), 3)) for name, val in loadings[:5]
        ]

    return PCAResult(
        n_components_95=n_for_95,
        explained_variance=explained,
        top_loadings=top_loadings,
    )
