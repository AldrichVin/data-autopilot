import time

import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz

from models.enums import FillStrategy
from models.schemas import CleaningOptions, CleaningReport, CleaningStep
from services.cleaning.base import CleaningEngine


class PythonCleaningEngine(CleaningEngine):
    def clean(
        self, df: pd.DataFrame, options: CleaningOptions
    ) -> tuple[pd.DataFrame, CleaningReport]:
        start = time.time()
        original_shape = [len(df), len(df.columns)]
        steps: list[CleaningStep] = []
        df = df.copy()

        # Step 1: Remove duplicates
        if options.remove_duplicates:
            step = self._remove_duplicates(df)
            df = df.drop_duplicates().reset_index(drop=True)
            steps.append(step)

        # Step 2: Fix types
        if options.fix_types:
            df, step = self._fix_types(df)
            steps.append(step)

        # Step 3: Handle missing values
        df, step = self._handle_missing(df, options.fill_strategy)
        steps.append(step)

        # Step 4: Handle outliers
        if options.handle_outliers:
            df, step = self._handle_outliers(df)
            steps.append(step)

        # Step 5: Standardize strings
        if options.standardize_strings:
            df, step = self._standardize_strings(df)
            steps.append(step)

        # Step 6: Consistency checks
        df, step = self._consistency_checks(df)
        steps.append(step)

        duration_ms = int((time.time() - start) * 1000)
        report = CleaningReport(
            steps=steps,
            original_shape=original_shape,
            cleaned_shape=[len(df), len(df.columns)],
            duration_ms=duration_ms,
        )
        return df, report

    def _remove_duplicates(self, df: pd.DataFrame) -> CleaningStep:
        dup_count = int(df.duplicated().sum())
        return CleaningStep(
            step="remove_duplicates",
            description=f"Removed {dup_count} duplicate rows",
            rows_affected=dup_count,
        )

    def _fix_types(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, CleaningStep]:
        fixes = {}
        for col in df.columns:
            if df[col].dtype == object:
                # Try numeric
                numeric = pd.to_numeric(df[col], errors="coerce")
                non_null_original = df[col].notna().sum()
                if non_null_original > 0:
                    conversion_rate = numeric.notna().sum() / non_null_original
                    if conversion_rate >= 0.8:
                        df[col] = numeric
                        fixes[col] = "numeric"
                        continue

                # Try datetime
                try:
                    datetime_vals = pd.to_datetime(df[col], errors="coerce")
                    if non_null_original > 0:
                        conversion_rate = (
                            datetime_vals.notna().sum() / non_null_original
                        )
                        if conversion_rate >= 0.8:
                            df[col] = datetime_vals
                            fixes[col] = "datetime"
                except Exception:
                    pass

        return df, CleaningStep(
            step="fix_types",
            description=f"Fixed types for {len(fixes)} columns",
            rows_affected=0,
            details={"conversions": fixes},
        )

    def _handle_missing(
        self, df: pd.DataFrame, strategy: FillStrategy
    ) -> tuple[pd.DataFrame, CleaningStep]:
        total_filled = 0
        dropped_cols: list[str] = []

        # Drop columns with >50% null
        null_pcts = df.isna().mean()
        high_null_cols = null_pcts[null_pcts > 0.5].index.tolist()
        if high_null_cols:
            df = df.drop(columns=high_null_cols)
            dropped_cols = high_null_cols

        for col in df.columns:
            null_count = int(df[col].isna().sum())
            if null_count == 0:
                continue

            if strategy == FillStrategy.DROP:
                df = df.dropna(subset=[col])
                total_filled += null_count
            elif pd.api.types.is_numeric_dtype(df[col]):
                if strategy == FillStrategy.MEAN:
                    df[col] = df[col].fillna(df[col].mean())
                elif strategy == FillStrategy.MEDIAN:
                    df[col] = df[col].fillna(df[col].median())
                else:
                    mode_val = df[col].mode()
                    if len(mode_val) > 0:
                        df[col] = df[col].fillna(mode_val.iloc[0])
                total_filled += null_count
            else:
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    df[col] = df[col].fillna(mode_val.iloc[0])
                    total_filled += null_count

        return df, CleaningStep(
            step="handle_missing",
            description=(
                f"Filled {total_filled} missing values using {strategy.value} strategy"
                + (f", dropped {len(dropped_cols)} high-null columns" if dropped_cols else "")
            ),
            rows_affected=total_filled,
            details={"dropped_columns": dropped_cols, "strategy": strategy.value},
        )

    def _handle_outliers(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, CleaningStep]:
        capped_count = 0
        capped_cols: list[str] = []

        for col in df.select_dtypes(include=[np.number]).columns:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue

            lower = q1 - 3 * iqr
            upper = q3 + 3 * iqr

            outliers = ((df[col] < lower) | (df[col] > upper)).sum()
            if outliers > 0:
                df[col] = df[col].clip(lower=lower, upper=upper)
                capped_count += int(outliers)
                capped_cols.append(col)

        return df, CleaningStep(
            step="handle_outliers",
            description=f"Capped {capped_count} outlier values in {len(capped_cols)} columns (3x IQR)",
            rows_affected=capped_count,
            details={"capped_columns": capped_cols},
        )

    def _standardize_strings(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, CleaningStep]:
        standardized_count = 0

        for col in df.select_dtypes(include=["object"]).columns:
            original = df[col].copy()
            df[col] = df[col].str.strip()
            df[col] = df[col].str.lower()
            changed = (original != df[col]).sum()
            standardized_count += int(changed)

        return df, CleaningStep(
            step="standardize_strings",
            description=f"Standardized {standardized_count} string values (trim + lowercase)",
            rows_affected=standardized_count,
        )

    def _consistency_checks(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, CleaningStep]:
        merged_count = 0

        for col in df.select_dtypes(include=["object"]).columns:
            if df[col].nunique() > 50:
                continue

            unique_vals = df[col].dropna().unique().tolist()
            replacements: dict[str, str] = {}

            for i, val_a in enumerate(unique_vals):
                for val_b in unique_vals[i + 1 :]:
                    if fuzz.ratio(str(val_a), str(val_b)) > 85:
                        shorter = val_a if len(str(val_a)) <= len(str(val_b)) else val_b
                        longer = val_b if shorter == val_a else val_a
                        replacements[longer] = shorter

            if replacements:
                df[col] = df[col].replace(replacements)
                merged_count += len(replacements)

        return df, CleaningStep(
            step="consistency_checks",
            description=f"Merged {merged_count} similar category labels via fuzzy matching",
            rows_affected=merged_count,
            details={"merged_labels": merged_count},
        )
