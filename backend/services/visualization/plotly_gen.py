"""Plotly chart generators for complex and statistical visualizations."""

from __future__ import annotations

import base64
import io
from typing import Callable

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from models.enums import ChartType
from models.schemas import ChartRecommendation

import plotly.io as pio

# Fix Kaleido blank exports on Windows (chromium subprocess issue)
try:
    pio.kaleido.scope.chromium_args += ("--single-process",)
except Exception:
    pass

PALETTE = [
    "#2563eb", "#7c3aed", "#0891b2", "#059669",
    "#d97706", "#dc2626", "#4f46e5", "#0284c7",
]
REPORT_LAYOUT = dict(
    font=dict(family="sans-serif", size=12, color="#495057"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=60, r=30, t=50, b=60),
    title_font=dict(size=14, color="#1a1a2e"),
)

_GENERATORS: dict[ChartType, Callable] = {}


def _register(chart_type: ChartType):
    def decorator(fn):
        _GENERATORS[chart_type] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_FRONTEND_OVERRIDES: dict[ChartType, Callable] = {}


def generate_plotly_json(
    rec: ChartRecommendation, df: pd.DataFrame,
) -> dict:
    """Return Plotly JSON spec for frontend rendering."""
    import json

    # Use frontend-specific generator if available (e.g. for sunburst/treemap)
    generator = _FRONTEND_OVERRIDES.get(rec.chart_type, _GENERATORS.get(rec.chart_type))
    if not generator:
        return {}
    fig = generator(rec, df)
    # JSON round-trip to convert numpy arrays to plain Python types
    return json.loads(fig.to_json())


def generate_plotly_base64(
    rec: ChartRecommendation, df: pd.DataFrame,
) -> str:
    """Return base64 PNG for report embedding."""
    import time

    generator = _GENERATORS.get(rec.chart_type)
    if not generator:
        return ""
    fig = generator(rec, df)

    width, height = 900, 650
    MAX_RETRIES = 3

    for attempt in range(MAX_RETRIES):
        try:
            img_bytes = fig.to_image(
                format="png", width=width, height=height, scale=2,
            )
        except Exception:
            buf = io.BytesIO()
            fig.write_image(buf, format="png", width=width, height=height, scale=2)
            buf.seek(0)
            img_bytes = buf.read()

        # Kaleido can silently produce blank PNGs on Windows
        if len(img_bytes) > 2000:
            break
        time.sleep(0.5 * (attempt + 1))

    return base64.b64encode(img_bytes).decode("utf-8")


# ---------------------------------------------------------------------------
# Complex chart generators
# ---------------------------------------------------------------------------

@_register(ChartType.TREEMAP)
def _treemap(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    import plotly.express as px

    cat_cols = [c for c in rec.columns if df[c].dtype == "object" or str(df[c].dtype) == "category"]
    num_cols = [c for c in rec.columns if c not in cat_cols]
    value_col = num_cols[0] if num_cols else None
    if len(cat_cols) < 1:
        return go.Figure()

    plot_df = df[cat_cols].dropna()
    kwargs: dict = {"path": cat_cols}
    if value_col and value_col in df.columns:
        plot_df = df[cat_cols + [value_col]].dropna()
        kwargs["values"] = value_col

    fig = px.treemap(plot_df, **kwargs)
    fig.update_traces(textinfo="label+value+percent parent")
    fig.update_layout(title=rec.title, **REPORT_LAYOUT)
    return fig


@_register(ChartType.SUNBURST)
def _sunburst(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    import plotly.express as px

    cat_cols = [c for c in rec.columns if df[c].dtype == "object" or str(df[c].dtype) == "category"]
    num_cols = [c for c in rec.columns if c not in cat_cols]
    value_col = num_cols[0] if num_cols else None
    if len(cat_cols) < 1:
        return go.Figure()

    plot_df = df[cat_cols].dropna()
    kwargs: dict = {"path": cat_cols}
    if value_col and value_col in df.columns:
        plot_df = df[cat_cols + [value_col]].dropna()
        kwargs["values"] = value_col

    fig = px.sunburst(plot_df, **kwargs)
    fig.update_layout(title=rec.title, **REPORT_LAYOUT)
    return fig


# ---------------------------------------------------------------------------
# Frontend-safe hierarchy builders (avoid px.sunburst path ambiguity in JS)
# ---------------------------------------------------------------------------

def _build_hierarchy(df: pd.DataFrame, cat_cols: list[str]) -> tuple:
    """Build a complete hierarchy with unique ids for go.Sunburst/Treemap.

    Returns (ids, labels, parents, values) with all intermediate nodes present.
    """
    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    values: list[int] = []
    seen: set[str] = set()

    # For each depth level, group and create nodes
    for depth in range(len(cat_cols)):
        cols_at_depth = cat_cols[: depth + 1]
        grouped = df.groupby(cols_at_depth).size().reset_index(name="_count")

        for _, row in grouped.iterrows():
            node_id = " | ".join(str(row[c]) for c in cols_at_depth)
            if node_id in seen:
                continue
            seen.add(node_id)

            ids.append(node_id)
            labels.append(str(row[cat_cols[depth]]))
            values.append(int(row["_count"]))

            if depth == 0:
                parents.append("")
            else:
                parent_id = " | ".join(str(row[c]) for c in cols_at_depth[:-1])
                parents.append(parent_id)

    # Fix values: parent values must equal sum of children (for branchvalues="total")
    id_to_idx = {nid: i for i, nid in enumerate(ids)}
    child_sums: dict[str, int] = {}
    for i, pid in enumerate(parents):
        if pid:
            child_sums[pid] = child_sums.get(pid, 0) + values[i]
    for pid, total in child_sums.items():
        if pid in id_to_idx:
            values[id_to_idx[pid]] = total

    return ids, labels, parents, values


def _frontend_sunburst(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    cat_cols = [c for c in rec.columns if df[c].dtype == "object" or str(df[c].dtype) == "category"]
    if len(cat_cols) < 1:
        return go.Figure()

    plot_df = df[cat_cols].dropna()
    ids, labels, parents, values = _build_hierarchy(plot_df, cat_cols)

    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total",
    ))
    fig.update_layout(title=rec.title, **REPORT_LAYOUT)
    return fig


def _frontend_treemap(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    cat_cols = [c for c in rec.columns if df[c].dtype == "object" or str(df[c].dtype) == "category"]
    if len(cat_cols) < 1:
        return go.Figure()

    plot_df = df[cat_cols].dropna()
    ids, labels, parents, values = _build_hierarchy(plot_df, cat_cols)

    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total",
        textinfo="label+value+percent parent",
    ))
    fig.update_layout(title=rec.title, **REPORT_LAYOUT)
    return fig


_FRONTEND_OVERRIDES[ChartType.SUNBURST] = _frontend_sunburst
_FRONTEND_OVERRIDES[ChartType.TREEMAP] = _frontend_treemap


@_register(ChartType.SANKEY)
def _sankey(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    source_col, target_col = rec.columns[0], rec.columns[1]
    flow = df.groupby([source_col, target_col]).size().reset_index(name="count")

    all_nodes = list(set(flow[source_col].tolist() + flow[target_col].tolist()))
    node_map = {name: i for i, name in enumerate(all_nodes)}

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            label=all_nodes,
            color=PALETTE * (len(all_nodes) // len(PALETTE) + 1),
        ),
        link=dict(
            source=[node_map[s] for s in flow[source_col]],
            target=[node_map[t] for t in flow[target_col]],
            value=flow["count"].tolist(),
            color=["rgba(37, 99, 235, 0.3)"] * len(flow),
        ),
    ))
    fig.update_layout(title=rec.title, **REPORT_LAYOUT)
    return fig


@_register(ChartType.BUBBLE)
def _bubble(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    col_x, col_y, col_size = rec.columns[0], rec.columns[1], rec.columns[2]
    x = pd.to_numeric(df[col_x], errors="coerce")
    y = pd.to_numeric(df[col_y], errors="coerce")
    size = pd.to_numeric(df[col_size], errors="coerce")
    mask = x.notna() & y.notna() & size.notna()

    fig = go.Figure(go.Scatter(
        x=x[mask],
        y=y[mask],
        mode="markers",
        marker=dict(
            size=_normalize_sizes(size[mask]),
            color=PALETTE[0],
            opacity=0.6,
            line=dict(width=0.5, color="white"),
        ),
        text=[f"{col_size}: {v:.1f}" for v in size[mask]],
        hovertemplate=f"{col_x}: %{{x}}<br>{col_y}: %{{y}}<br>%{{text}}<extra></extra>",
    ))
    fig.update_layout(
        title=rec.title,
        xaxis_title=col_x,
        yaxis_title=col_y,
        **REPORT_LAYOUT,
    )
    return fig


@_register(ChartType.PARALLEL_COORDS)
def _parallel_coords(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    cols = rec.columns
    numeric_df = df[cols].apply(pd.to_numeric, errors="coerce").dropna()

    if len(numeric_df) > 500:
        numeric_df = numeric_df.sample(500, random_state=42)

    dimensions = [
        dict(label=col, values=numeric_df[col].tolist())
        for col in cols
    ]

    fig = go.Figure(go.Parcoords(
        line=dict(
            color=numeric_df[cols[0]],
            colorscale="Blues",
            showscale=True,
        ),
        dimensions=dimensions,
    ))
    fig.update_layout(title=rec.title, **REPORT_LAYOUT)
    return fig


@_register(ChartType.RADAR)
def _radar(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    cols = rec.columns
    numeric_df = df[cols].apply(pd.to_numeric, errors="coerce").dropna()

    # Normalize to 0-1 range for radar comparability
    normalized = (numeric_df - numeric_df.min()) / (numeric_df.max() - numeric_df.min() + 1e-10)
    means = normalized.mean()

    categories = cols + [cols[0]]  # close the polygon
    values = means.tolist() + [means.iloc[0]]

    fig = go.Figure(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(37, 99, 235, 0.2)",
        line=dict(color=PALETTE[0], width=2),
        name="Mean (normalized)",
    ))
    fig.update_layout(
        title=rec.title,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1]),
        ),
        **REPORT_LAYOUT,
    )
    return fig


@_register(ChartType.WATERFALL)
def _waterfall(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    cat_col, num_col = rec.columns[0], rec.columns[1]
    grouped = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(15)

    categories = grouped.index.tolist()
    values = grouped.values.tolist()

    fig = go.Figure(go.Waterfall(
        x=categories,
        y=values,
        connector=dict(line=dict(color="rgba(0,0,0,0.2)")),
        increasing=dict(marker=dict(color=PALETTE[0])),
        decreasing=dict(marker=dict(color=PALETTE[5])),
        totals=dict(marker=dict(color=PALETTE[3])),
    ))
    fig.update_layout(
        title=rec.title,
        xaxis_title=cat_col,
        yaxis_title=num_col,
        **REPORT_LAYOUT,
    )
    fig.update_xaxes(tickangle=45)
    return fig


# ---------------------------------------------------------------------------
# Statistical chart generators
# ---------------------------------------------------------------------------

@_register(ChartType.PCA_BIPLOT)
def _pca_biplot(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    cols = rec.columns
    numeric_df = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_df) < 5:
        return go.Figure()

    scaled = StandardScaler().fit_transform(numeric_df)
    pca = PCA(n_components=2)
    projected = pca.fit_transform(scaled)
    ev = pca.explained_variance_ratio_

    fig = go.Figure()

    # Scatter of projected points
    fig.add_trace(go.Scatter(
        x=projected[:, 0],
        y=projected[:, 1],
        mode="markers",
        marker=dict(size=5, color=PALETTE[0], opacity=0.4),
        name="Data points",
    ))

    # Loading arrows — limit to top 8 by magnitude to avoid clutter
    MAX_ARROWS = 8
    loadings = pca.components_[:2, :]  # shape (2, n_features)
    magnitudes = np.sqrt(loadings[0] ** 2 + loadings[1] ** 2)
    top_indices = np.argsort(magnitudes)[-MAX_ARROWS:]

    # Scale arrows to ~40% of data range for readability
    data_range = max(
        projected[:, 0].max() - projected[:, 0].min(),
        projected[:, 1].max() - projected[:, 1].min(),
    )
    max_mag = magnitudes[top_indices].max()
    arrow_scale = (data_range * 0.4) / (max_mag + 1e-10)

    for i in top_indices:
        lx = loadings[0, i] * arrow_scale
        ly = loadings[1, i] * arrow_scale
        fig.add_annotation(
            x=lx, y=ly,
            ax=0, ay=0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowwidth=1.5,
            arrowcolor=PALETTE[5],
        )
        fig.add_annotation(
            x=lx * 1.12,
            y=ly * 1.12,
            text=cols[i],
            showarrow=False,
            font=dict(size=9, color=PALETTE[5]),
            bgcolor="rgba(255,255,255,0.8)",
            borderpad=2,
        )

    fig.update_layout(
        title=rec.title,
        xaxis_title=f"PC1 ({ev[0]:.1%} variance)",
        yaxis_title=f"PC2 ({ev[1]:.1%} variance)",
        **REPORT_LAYOUT,
    )
    return fig


@_register(ChartType.CLUSTER_SCATTER)
def _cluster_scatter(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    cols = rec.columns
    numeric_df = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_df) < 10:
        return go.Figure()

    scaled = StandardScaler().fit_transform(numeric_df)

    # Get cluster count from annotation or default to 3
    n_clusters = 3
    if rec.annotation:
        import re
        match = re.search(r"(\d+)\s*cluster", rec.annotation)
        if match:
            n_clusters = int(match.group(1))

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(scaled)

    pca = PCA(n_components=2)
    projected = pca.fit_transform(scaled)

    fig = go.Figure()
    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        fig.add_trace(go.Scatter(
            x=projected[mask, 0],
            y=projected[mask, 1],
            mode="markers",
            marker=dict(size=6, color=PALETTE[cluster_id % len(PALETTE)], opacity=0.7),
            name=f"Cluster {cluster_id + 1} (n={mask.sum()})",
        ))

    ev = pca.explained_variance_ratio_
    fig.update_layout(
        title=rec.title,
        xaxis_title=f"PC1 ({ev[0]:.1%})",
        yaxis_title=f"PC2 ({ev[1]:.1%})",
        **REPORT_LAYOUT,
    )
    return fig


@_register(ChartType.ANOMALY_SCATTER)
def _anomaly_scatter(rec: ChartRecommendation, df: pd.DataFrame) -> go.Figure:
    from sklearn.decomposition import PCA
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    cols = rec.columns
    numeric_df = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_df) < 20:
        return go.Figure()

    scaled = StandardScaler().fit_transform(numeric_df)
    model = IsolationForest(contamination=0.05, random_state=42)
    labels = model.fit_predict(scaled)

    pca = PCA(n_components=2)
    projected = pca.fit_transform(scaled)

    normal_mask = labels == 1
    anomaly_mask = labels == -1

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=projected[normal_mask, 0],
        y=projected[normal_mask, 1],
        mode="markers",
        marker=dict(size=5, color=PALETTE[0], opacity=0.4),
        name=f"Normal (n={normal_mask.sum()})",
    ))
    fig.add_trace(go.Scatter(
        x=projected[anomaly_mask, 0],
        y=projected[anomaly_mask, 1],
        mode="markers",
        marker=dict(size=8, color=PALETTE[5], opacity=0.8, symbol="x"),
        name=f"Anomalies (n={anomaly_mask.sum()})",
    ))

    ev = pca.explained_variance_ratio_
    fig.update_layout(
        title=rec.title,
        xaxis_title=f"PC1 ({ev[0]:.1%})",
        yaxis_title=f"PC2 ({ev[1]:.1%})",
        **REPORT_LAYOUT,
    )
    return fig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_sizes(
    series: pd.Series, min_size: int = 8, max_size: int = 50,
) -> list[float]:
    """Normalize a series to marker sizes between min_size and max_size."""
    s = series.values.astype(float)
    s_min, s_max = s.min(), s.max()
    if s_max == s_min:
        return [min_size + (max_size - min_size) / 2] * len(s)
    normalized = (s - s_min) / (s_max - s_min)
    return (normalized * (max_size - min_size) + min_size).tolist()
