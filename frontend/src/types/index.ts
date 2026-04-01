export interface NumericStats {
  mean: number;
  median: number;
  min: number;
  max: number;
  std: number;
}

export interface ColumnProfile {
  name: string;
  inferred_type: "numeric" | "categorical" | "datetime" | "text" | "boolean";
  dtype: string;
  null_count: number;
  null_pct: number;
  unique_count: number;
  sample_values: string[];
  stats?: NumericStats;
}

export interface DataProfile {
  columns: ColumnProfile[];
  duplicate_row_count: number;
  total_rows: number;
  total_columns: number;
}

export interface UploadResponse {
  session_id: string;
  filename: string;
  rows: number;
  columns: number;
  profile: DataProfile;
  preview: Record<string, unknown>[];
}

export interface CleaningStep {
  step: string;
  description: string;
  rows_affected: number;
  details: Record<string, unknown>;
}

export interface CleaningReport {
  steps: CleaningStep[];
  original_shape: number[];
  cleaned_shape: number[];
  duration_ms: number;
}

export interface CleanResponse {
  session_id: string;
  engine_used: string;
  cleaning_report: CleaningReport;
  cleaned_preview: Record<string, unknown>[];
}

export interface ChartSpec {
  chart_id: string;
  chart_type: string;
  title: string;
  columns_used: string[];
  vegalite_spec?: Record<string, unknown>;
  matplotlib_url?: string;
  description: string;
}

export interface VisualizeResponse {
  session_id: string;
  charts: ChartSpec[];
  tableau_download_url?: string;
}

export interface Alert {
  severity: "warning" | "info" | "danger";
  category: string;
  message: string;
  column?: string;
}

export interface ReportChart {
  title: string;
  description: string;
  chart_type: string;
  image_base64: string;
}

export interface ReportData {
  title: string;
  generated_at: string;
  dataset_filename: string;
  profile: DataProfile;
  alerts: Alert[];
  cleaning_report?: CleaningReport;
  charts: ReportChart[];
  key_findings: string[];
}

export type Engine = "python" | "r";
export type VizMode = "vegalite" | "matplotlib";
export type AppStatus =
  | "idle"
  | "uploading"
  | "profiled"
  | "cleaning"
  | "cleaned"
  | "visualizing"
  | "complete"
  | "error";
