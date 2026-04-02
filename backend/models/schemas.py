from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from models.enums import (
    ChartType,
    ColumnType,
    Engine,
    FillStrategy,
    SessionStatus,
)


# --- Profile ---


class NumericStats(BaseModel):
    mean: float
    median: float
    min: float
    max: float
    std: float
    skewness: float = 0.0
    kurtosis: float = 0.0
    q1: float = 0.0
    q3: float = 0.0
    iqr: float = 0.0


class ColumnProfile(BaseModel):
    name: str
    inferred_type: ColumnType
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    sample_values: list[str]
    stats: Optional[NumericStats] = None


class DataProfile(BaseModel):
    columns: list[ColumnProfile]
    duplicate_row_count: int
    total_rows: int
    total_columns: int


# --- Upload ---


class UploadResponse(BaseModel):
    session_id: str
    filename: str
    rows: int
    columns: int
    profile: DataProfile
    preview: list[dict]


# --- Cleaning ---


class CleaningOptions(BaseModel):
    fill_strategy: FillStrategy = FillStrategy.MEDIAN
    remove_duplicates: bool = True
    fix_types: bool = True
    handle_outliers: bool = True
    standardize_strings: bool = True


class CleanRequest(BaseModel):
    session_id: str
    engine: Engine = Engine.PYTHON
    options: CleaningOptions = CleaningOptions()


class CleaningStep(BaseModel):
    step: str
    description: str
    rows_affected: int
    details: dict = {}


class CleaningReport(BaseModel):
    steps: list[CleaningStep]
    original_shape: list[int]
    cleaned_shape: list[int]
    duration_ms: int


class CleanResponse(BaseModel):
    session_id: str
    engine_used: str
    cleaning_report: CleaningReport
    cleaned_preview: list[dict]


# --- Visualization ---


class VisualizeRequest(BaseModel):
    session_id: str
    formats: list[str] = ["vegalite", "matplotlib", "tableau"]


class ChartSpec(BaseModel):
    chart_id: str
    chart_type: ChartType
    title: str
    columns_used: list[str]
    vegalite_spec: Optional[dict] = None
    matplotlib_url: Optional[str] = None
    plotly_spec: Optional[dict] = None
    description: str


class VisualizeResponse(BaseModel):
    session_id: str
    charts: list[ChartSpec]
    tableau_download_url: Optional[str] = None


# --- Status ---


class StatusResponse(BaseModel):
    session_id: str
    status: SessionStatus
    error: Optional[str] = None


# --- Report ---


class Alert(BaseModel):
    severity: str
    category: str
    message: str
    column: Optional[str] = None


class SectionNarrative(BaseModel):
    headline: str
    body: str = ""


class ReportChart(BaseModel):
    title: str
    description: str
    chart_type: ChartType
    image_base64: str
    annotation: str = ""


class ReportSection(BaseModel):
    id: str
    title: str
    narrative: Optional[SectionNarrative] = None
    charts: list[ReportChart] = []


class AnomalyResult(BaseModel):
    method: str
    n_anomalies: int
    anomaly_pct: float
    top_anomaly_columns: list[str] = []


class ClusterResult(BaseModel):
    optimal_k: int
    silhouette_score: float
    cluster_sizes: list[int] = []


class PCAResult(BaseModel):
    n_components_95: int
    explained_variance: list[float] = []
    top_loadings: dict[str, list[tuple[str, float]]] = {}


class StatTestResult(BaseModel):
    test_name: str
    columns: list[str]
    statistic: float
    p_value: float
    interpretation: str


class StatisticalReport(BaseModel):
    anomalies: Optional[AnomalyResult] = None
    clusters: Optional[ClusterResult] = None
    pca: Optional[PCAResult] = None
    tests: list[StatTestResult] = []


class ReportData(BaseModel):
    title: str
    generated_at: str
    dataset_filename: str
    profile: DataProfile
    alerts: list[Alert]
    cleaning_report: Optional[CleaningReport] = None
    charts: list[ReportChart]
    key_findings: list[str]
    sections: list[ReportSection] = []
    executive_narrative: str = ""
    data_overview_narrative: str = ""
    statistical_report: Optional[StatisticalReport] = None


class ReportRequest(BaseModel):
    session_id: str
    title: str = "Data Analysis Report"


# --- Internal ---


class ChartRecommendation(BaseModel):
    chart_type: ChartType
    columns: list[str]
    title: str
    description: str = ""
    interestingness: float = 0.0
    annotation: str = ""
