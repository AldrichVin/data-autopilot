import base64
import io
import textwrap

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from models.enums import ChartType
from models.schemas import ChartRecommendation

# ---------------------------------------------------------------------------
# McKinsey-inspired palette (analogous blues + complements)
# ---------------------------------------------------------------------------
PALETTE = [
    "#2563eb", "#7c3aed", "#0891b2", "#059669",
    "#d97706", "#dc2626", "#4f46e5", "#0284c7",
]
CHROME = "#495057"
DARK = "#1a1a2e"
DPI = 150
REPORT_DPI = 200

_RC_OVERRIDES = {
    "figure.dpi": DPI,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": CHROME,
    "axes.linewidth": 0.8,
    "axes.labelcolor": CHROME,
    "axes.labelsize": 12,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "xtick.color": CHROME,
    "ytick.color": CHROME,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "patch.edgecolor": "white",
    "patch.linewidth": 0.5,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "font.family": "sans-serif",
}

_GENERATORS = {}


def _register(chart_type: ChartType):
    def decorator(fn):
        _GENERATORS[chart_type] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_matplotlib(
    rec: ChartRecommendation, df: pd.DataFrame, output_path: str
) -> str:
    return _render(rec, df, output_path=output_path, dpi=DPI)


def generate_matplotlib_base64(
    rec: ChartRecommendation, df: pd.DataFrame
) -> str:
    return _render(rec, df, output_path=None, dpi=REPORT_DPI)


# ---------------------------------------------------------------------------
# Core renderer
# ---------------------------------------------------------------------------

def _render(
    rec: ChartRecommendation,
    df: pd.DataFrame,
    *,
    output_path: str | None,
    dpi: int,
) -> str:
    generator = _GENERATORS.get(rec.chart_type)
    if not generator:
        return output_path or ""

    with plt.rc_context(_RC_OVERRIDES):
        fig, ax = plt.subplots(figsize=(8, 5.5))
        generator(rec, df, ax)
        ax.set_title(rec.title, fontsize=14, fontweight="bold", color=DARK, pad=12, loc="left")

        if rec.annotation:
            _add_insight_annotation(fig, rec.annotation)

        fig.tight_layout(rect=[0, 0.06 if rec.annotation else 0, 1, 1])

        if output_path:
            fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            return output_path

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")


def _add_insight_annotation(fig: plt.Figure, text: str) -> None:
    wrapped = textwrap.fill(text, width=90)
    fig.text(
        0.04, 0.02, wrapped,
        fontsize=9, color="#6c757d", style="italic",
        va="bottom", ha="left",
        transform=fig.transFigure,
    )


# ---------------------------------------------------------------------------
# Chart generators
# ---------------------------------------------------------------------------

@_register(ChartType.HISTOGRAM)
def _histogram(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    col = rec.columns[0]
    data = pd.to_numeric(df[col], errors="coerce").dropna()

    ax.hist(data, bins=30, edgecolor="white", alpha=0.85, color=PALETTE[0], linewidth=0.6)

    mean_val = data.mean()
    median_val = data.median()
    ax.axvline(mean_val, color=PALETTE[4], linestyle="--", linewidth=1.5, label=f"Mean: {mean_val:,.2f}")
    ax.axvline(median_val, color=PALETTE[5], linestyle="-.", linewidth=1.5, label=f"Median: {median_val:,.2f}")

    ax.set_xlabel(col)
    ax.set_ylabel("Frequency")
    ax.legend(fontsize=9, framealpha=0.9, loc="upper right")
    ax.grid(axis="y", alpha=0.25)


@_register(ChartType.BAR)
def _bar(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    col = rec.columns[0]
    counts = df[col].value_counts().head(15)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(counts))]

    bars = ax.bar(range(len(counts)), counts.values, color=colors, edgecolor="white", linewidth=0.6)

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, height,
            f"{int(height):,}", ha="center", va="bottom",
            fontsize=9, fontweight="bold", color=CHROME,
        )

    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(counts.index, rotation=45, ha="right")
    ax.set_xlabel(col)
    ax.set_ylabel("Count")
    ax.grid(axis="y", alpha=0.25)


@_register(ChartType.SCATTER)
def _scatter(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    col_x, col_y = rec.columns[0], rec.columns[1]
    x = pd.to_numeric(df[col_x], errors="coerce")
    y = pd.to_numeric(df[col_y], errors="coerce")
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]

    ax.scatter(x, y, alpha=0.6, s=40, color=PALETTE[0], edgecolors="white", linewidths=0.3)

    if len(x) >= 2:
        coeffs = np.polyfit(x, y, 1)
        trend_x = np.linspace(x.min(), x.max(), 100)
        trend_y = np.polyval(coeffs, trend_x)
        ax.plot(trend_x, trend_y, color=PALETTE[5], linewidth=1.5, linestyle="--", alpha=0.8)

    ax.set_xlabel(col_x)
    ax.set_ylabel(col_y)
    ax.grid(alpha=0.25)


@_register(ChartType.LINE)
def _line(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    dt_col, val_col = rec.columns[0], rec.columns[1]
    plot_df = df[[dt_col, val_col]].copy()
    plot_df[dt_col] = pd.to_datetime(plot_df[dt_col], errors="coerce")
    plot_df = plot_df.dropna().sort_values(dt_col)

    ax.plot(plot_df[dt_col], plot_df[val_col], color=PALETTE[0], linewidth=1.8, marker="o", markersize=3)
    ax.fill_between(plot_df[dt_col], plot_df[val_col], alpha=0.06, color=PALETTE[0])

    ax.set_xlabel(dt_col)
    ax.set_ylabel(val_col)
    ax.grid(alpha=0.25)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)


@_register(ChartType.HEATMAP)
def _heatmap(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    numeric_df = df[rec.columns].apply(pd.to_numeric, errors="coerce")
    corr = numeric_df.corr()
    n_cols = len(corr.columns)

    # Scale figure size with column count — extra width for colorbar
    fig_width = max(8, n_cols * 0.9 + 1.5)
    fig_height = max(5.5, n_cols * 0.7)
    ax.figure.set_size_inches(fig_width, fig_height)

    # Reduce annotation font for large matrices
    annot_fontsize = 10 if n_cols <= 8 else 8 if n_cols <= 12 else 6

    # Don't force square for large matrices — it causes off-center layout
    use_square = n_cols <= 8

    sns.heatmap(
        corr, annot=True, fmt=".2f", cmap="RdBu_r",
        center=0, vmin=-1, vmax=1, ax=ax, square=use_square,
        linewidths=0.5, linecolor="white",
        annot_kws={"fontsize": annot_fontsize},
        cbar_kws={"shrink": 0.8, "pad": 0.02},
    )


@_register(ChartType.GROUPED_BAR)
def _grouped_bar(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    cat_col, num_col = rec.columns[0], rec.columns[1]
    grouped = df.groupby(cat_col)[num_col].mean().sort_values(ascending=False).head(15)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(grouped))]

    bars = ax.bar(range(len(grouped)), grouped.values, color=colors, edgecolor="white", linewidth=0.6)

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, height,
            f"{height:,.1f}", ha="center", va="bottom",
            fontsize=9, fontweight="bold", color=CHROME,
        )

    ax.set_xticks(range(len(grouped)))
    ax.set_xticklabels(grouped.index, rotation=45, ha="right")
    ax.set_xlabel(cat_col)
    ax.set_ylabel(f"Average {num_col}")
    ax.grid(axis="y", alpha=0.25)


@_register(ChartType.BOX)
def _box_plot(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    if len(rec.columns) == 2:
        cat_col, num_col = rec.columns[0], rec.columns[1]
        plot_df = df[[cat_col, num_col]].copy()
        plot_df[num_col] = pd.to_numeric(plot_df[num_col], errors="coerce")
        plot_df = plot_df.dropna()

        categories = plot_df[cat_col].value_counts().head(8).index.tolist()
        plot_df = plot_df[plot_df[cat_col].isin(categories)]

        sns.boxplot(
            data=plot_df, x=cat_col, y=num_col, ax=ax,
            palette=PALETTE[:len(categories)],
            linewidth=0.8, flierprops={"marker": "o", "markersize": 4, "alpha": 0.6},
        )
        ax.set_xlabel(cat_col)
        ax.set_ylabel(num_col)
    else:
        col = rec.columns[0]
        data = pd.to_numeric(df[col], errors="coerce").dropna()
        ax.boxplot(data, vert=True, patch_artist=True,
                   boxprops={"facecolor": PALETTE[0], "alpha": 0.7},
                   flierprops={"marker": "o", "markersize": 4})
        ax.set_ylabel(col)

    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)


@_register(ChartType.VIOLIN)
def _violin_plot(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    col = rec.columns[0]
    data = pd.to_numeric(df[col], errors="coerce").dropna()

    parts = ax.violinplot(data, showmeans=True, showmedians=True)
    for pc in parts.get("bodies", []):
        pc.set_facecolor(PALETTE[0])
        pc.set_alpha(0.7)

    ax.set_ylabel(col)
    ax.set_xticks([])
    ax.grid(axis="y", alpha=0.25)


@_register(ChartType.MISSING_MATRIX)
def _missing_matrix(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    cols = [c for c in rec.columns if c in df.columns]
    if not cols:
        return

    missing_data = df[cols].isnull().astype(int)

    # Sample rows if too many for readability
    if len(missing_data) > 200:
        missing_data = missing_data.sample(200, random_state=42).sort_index()

    ax.imshow(
        missing_data.values, aspect="auto", cmap="Blues",
        interpolation="nearest", vmin=0, vmax=1,
    )
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Row index")

    # Annotate missing % per column
    for i, col in enumerate(cols):
        pct = df[col].isnull().mean() * 100
        ax.text(i, -0.5, f"{pct:.1f}%", ha="center", va="bottom", fontsize=8, color=CHROME)
