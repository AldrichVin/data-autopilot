import numpy as np
import pandas as pd

from models.enums import ColumnType
from models.schemas import ColumnProfile, DataProfile, NumericStats


def _infer_column_type(series: pd.Series) -> ColumnType:
    if series.dtype == "bool" or set(series.dropna().unique()) <= {True, False, 0, 1}:
        if series.nunique() <= 2:
            return ColumnType.BOOLEAN

    if pd.api.types.is_numeric_dtype(series):
        return ColumnType.NUMERIC

    if pd.api.types.is_datetime64_any_dtype(series):
        return ColumnType.DATETIME

    # Try parsing as datetime
    sample = series.dropna().head(20)
    if len(sample) > 0:
        try:
            parsed = pd.to_datetime(sample, infer_datetime_format=True)
            if parsed.notna().sum() >= len(sample) * 0.8:
                return ColumnType.DATETIME
        except (ValueError, TypeError):
            pass

    # Try parsing as numeric
    if len(sample) > 0:
        try:
            numeric = pd.to_numeric(sample)
            if numeric.notna().sum() >= len(sample) * 0.8:
                return ColumnType.NUMERIC
        except (ValueError, TypeError):
            pass

    nunique = series.nunique()
    total = len(series)
    if nunique <= 50 or (total > 0 and nunique / total < 0.5):
        return ColumnType.CATEGORICAL

    return ColumnType.TEXT


def _compute_numeric_stats(series: pd.Series) -> NumericStats:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return NumericStats(
        mean=round(float(clean.mean()), 4),
        median=round(float(clean.median()), 4),
        min=round(float(clean.min()), 4),
        max=round(float(clean.max()), 4),
        std=round(float(clean.std()), 4) if len(clean) > 1 else 0.0,
    )


def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    columns: list[ColumnProfile] = []

    for col_name in df.columns:
        series = df[col_name]
        inferred_type = _infer_column_type(series)

        sample_values = [str(v) for v in series.dropna().head(5).tolist()]

        stats = None
        if inferred_type == ColumnType.NUMERIC:
            stats = _compute_numeric_stats(series)

        columns.append(
            ColumnProfile(
                name=col_name,
                inferred_type=inferred_type,
                dtype=str(series.dtype),
                null_count=int(series.isna().sum()),
                null_pct=round(float(series.isna().mean()) * 100, 2),
                unique_count=int(series.nunique()),
                sample_values=sample_values,
                stats=stats,
            )
        )

    duplicate_count = int(df.duplicated().sum())

    return DataProfile(
        columns=columns,
        duplicate_row_count=duplicate_count,
        total_rows=len(df),
        total_columns=len(df.columns),
    )
