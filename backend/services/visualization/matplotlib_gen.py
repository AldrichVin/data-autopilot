import base64
import io

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from models.enums import ChartType
from models.schemas import ChartRecommendation

# ---------------------------------------------------------------------------
# Professional palette & styling (sweetviz / ydata-profiling inspired)
# ---------------------------------------------------------------------------
PALETTE = [
    "#0088ed", "#ff7721", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#17becf",
]
CHROME = "#58544f"
DPI = 150
REPORT_DPI = 200

_RC_OVERRIDES = {
    "figure.dpi": DPI,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": CHROME,
    "axes.linewidth": 0.8,
    "axes.labelcolor": CHROME,
    "axes.labelsize": 13,
    "axes.titlesize": 16,
    "axes.titleweight": "bold",
    "xtick.color": CHROME,
    "ytick.color": CHROME,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "patch.edgecolor": CHROME,
    "patch.linewidth": 0.5,
    "grid.alpha": 0.3,
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
        fig, ax = plt.subplots(figsize=(8, 6))
        generator(rec, df, ax)
        ax.set_title(rec.title, fontsize=16, fontweight="bold", color="#1a1a2e", pad=14)
        fig.tight_layout()

        if output_path:
            fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            return output_path

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Chart generators
# ---------------------------------------------------------------------------

@_register(ChartType.HISTOGRAM)
def _histogram(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    col = rec.columns[0]
    data = pd.to_numeric(df[col], errors="coerce").dropna()

    ax.hist(data, bins=30, edgecolor="white", alpha=0.85, color=PALETTE[0], linewidth=0.6)

    # Mean & median reference lines
    mean_val = data.mean()
    median_val = data.median()
    ax.axvline(mean_val, color=PALETTE[1], linestyle="--", linewidth=1.5, label=f"Mean: {mean_val:,.2f}")
    ax.axvline(median_val, color=PALETTE[3], linestyle="-.", linewidth=1.5, label=f"Median: {median_val:,.2f}")

    ax.set_xlabel(col)
    ax.set_ylabel("Frequency")
    ax.legend(fontsize=10, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)


@_register(ChartType.BAR)
def _bar(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    col = rec.columns[0]
    counts = df[col].value_counts().head(15)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(counts))]

    bars = ax.bar(range(len(counts)), counts.values, color=colors, edgecolor="white", linewidth=0.6)

    # Data labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, height,
            f"{int(height):,}",
            ha="center", va="bottom", fontsize=9, fontweight="bold", color=CHROME,
        )

    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(counts.index, rotation=45, ha="right")
    ax.set_xlabel(col)
    ax.set_ylabel("Count")
    ax.grid(axis="y", alpha=0.3)


@_register(ChartType.SCATTER)
def _scatter(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    col_x, col_y = rec.columns[0], rec.columns[1]
    x = pd.to_numeric(df[col_x], errors="coerce")
    y = pd.to_numeric(df[col_y], errors="coerce")
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]

    ax.scatter(x, y, alpha=0.6, s=40, color=PALETTE[0], edgecolors="white", linewidths=0.3)

    # Trend line
    if len(x) >= 2:
        coeffs = np.polyfit(x, y, 1)
        trend_x = np.linspace(x.min(), x.max(), 100)
        trend_y = np.polyval(coeffs, trend_x)
        ax.plot(trend_x, trend_y, color=PALETTE[3], linewidth=1.5, linestyle="--", alpha=0.8)

    ax.set_xlabel(col_x)
    ax.set_ylabel(col_y)
    ax.grid(alpha=0.3)


@_register(ChartType.LINE)
def _line(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    dt_col, val_col = rec.columns[0], rec.columns[1]
    plot_df = df[[dt_col, val_col]].copy()
    plot_df[dt_col] = pd.to_datetime(plot_df[dt_col], errors="coerce")
    plot_df = plot_df.dropna().sort_values(dt_col)

    ax.plot(plot_df[dt_col], plot_df[val_col], color=PALETTE[0], linewidth=1.8, marker="o", markersize=4)
    ax.fill_between(plot_df[dt_col], plot_df[val_col], alpha=0.08, color=PALETTE[0])

    ax.set_xlabel(dt_col)
    ax.set_ylabel(val_col)
    ax.grid(alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)


@_register(ChartType.HEATMAP)
def _heatmap(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    numeric_df = df[rec.columns].apply(pd.to_numeric, errors="coerce")
    corr = numeric_df.corr()
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        vmin=-1,
        vmax=1,
        ax=ax,
        square=True,
        linewidths=0.5,
        linecolor="white",
        annot_kws={"fontsize": 10},
    )


@_register(ChartType.GROUPED_BAR)
def _grouped_bar(rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes) -> None:
    cat_col, num_col = rec.columns[0], rec.columns[1]
    grouped = df.groupby(cat_col)[num_col].mean().sort_values(ascending=False).head(15)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(grouped))]

    bars = ax.bar(range(len(grouped)), grouped.values, color=colors, edgecolor="white", linewidth=0.6)

    # Data labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, height,
            f"{height:,.1f}",
            ha="center", va="bottom", fontsize=9, fontweight="bold", color=CHROME,
        )

    ax.set_xticks(range(len(grouped)))
    ax.set_xticklabels(grouped.index, rotation=45, ha="right")
    ax.set_xlabel(cat_col)
    ax.set_ylabel(f"Average {num_col}")
    ax.grid(axis="y", alpha=0.3)
