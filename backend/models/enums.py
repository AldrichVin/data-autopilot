from enum import Enum


class Engine(str, Enum):
    PYTHON = "python"
    R = "r"


class ColumnType(str, Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"


class ChartType(str, Enum):
    HISTOGRAM = "histogram"
    BAR = "bar"
    SCATTER = "scatter"
    LINE = "line"
    HEATMAP = "heatmap"
    GROUPED_BAR = "grouped_bar"
    BOX = "box"
    VIOLIN = "violin"
    MISSING_MATRIX = "missing_matrix"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    SANKEY = "sankey"
    BUBBLE = "bubble"
    PARALLEL_COORDS = "parallel_coords"
    RADAR = "radar"
    WATERFALL = "waterfall"
    PCA_BIPLOT = "pca_biplot"
    CLUSTER_SCATTER = "cluster_scatter"
    ANOMALY_SCATTER = "anomaly_scatter"


class SessionStatus(str, Enum):
    UPLOADED = "uploaded"
    PROFILED = "profiled"
    CLEANING = "cleaning"
    CLEANED = "cleaned"
    VISUALIZING = "visualizing"
    COMPLETE = "complete"
    ERROR = "error"


class FillStrategy(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    DROP = "drop"
