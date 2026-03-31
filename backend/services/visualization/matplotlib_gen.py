import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from models.enums import ChartType
from models.schemas import ChartRecommendation

STYLE = "seaborn-v0_8-whitegrid"
DPI = 150


def generate_matplotlib(
    rec: ChartRecommendation, df: pd.DataFrame, output_path: str
) -> str:
    generators = {
        ChartType.HISTOGRAM: _histogram,
        ChartType.BAR: _bar,
        ChartType.SCATTER: _scatter,
        ChartType.LINE: _line,
        ChartType.HEATMAP: _heatmap,
        ChartType.GROUPED_BAR: _grouped_bar,
    }

    generator = generators.get(rec.chart_type)
    if not generator:
        return output_path

    plt.style.use(STYLE)
    fig, ax = plt.subplots(figsize=(8, 6))
    generator(rec, df, ax)
    ax.set_title(rec.title, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _histogram(
    rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes
) -> None:
    col = rec.columns[0]
    data = pd.to_numeric(df[col], errors="coerce").dropna()
    ax.hist(data, bins=30, edgecolor="black", alpha=0.7, color="#4C78A8")
    ax.set_xlabel(col)
    ax.set_ylabel("Frequency")


def _bar(
    rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes
) -> None:
    col = rec.columns[0]
    counts = df[col].value_counts().head(20)
    counts.plot(kind="bar", ax=ax, color="#4C78A8", edgecolor="black")
    ax.set_xlabel(col)
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=45)


def _scatter(
    rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes
) -> None:
    col_x, col_y = rec.columns[0], rec.columns[1]
    x = pd.to_numeric(df[col_x], errors="coerce")
    y = pd.to_numeric(df[col_y], errors="coerce")
    ax.scatter(x, y, alpha=0.5, s=20, color="#4C78A8")
    ax.set_xlabel(col_x)
    ax.set_ylabel(col_y)


def _line(
    rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes
) -> None:
    dt_col, val_col = rec.columns[0], rec.columns[1]
    plot_df = df[[dt_col, val_col]].copy()
    plot_df[dt_col] = pd.to_datetime(plot_df[dt_col], errors="coerce")
    plot_df = plot_df.dropna().sort_values(dt_col)
    ax.plot(plot_df[dt_col], plot_df[val_col], color="#4C78A8", linewidth=1.5)
    ax.set_xlabel(dt_col)
    ax.set_ylabel(val_col)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)


def _heatmap(
    rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes
) -> None:
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
    )


def _grouped_bar(
    rec: ChartRecommendation, df: pd.DataFrame, ax: plt.Axes
) -> None:
    cat_col, num_col = rec.columns[0], rec.columns[1]
    grouped = df.groupby(cat_col)[num_col].mean().sort_values(ascending=False).head(20)
    grouped.plot(kind="bar", ax=ax, color="#4C78A8", edgecolor="black")
    ax.set_xlabel(cat_col)
    ax.set_ylabel(f"Average {num_col}")
    ax.tick_params(axis="x", rotation=45)
