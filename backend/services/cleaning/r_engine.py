import json
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd

from models.schemas import CleaningOptions, CleaningReport, CleaningStep
from services.cleaning.base import CleaningEngine

R_SCRIPT_PATH = Path(__file__).parent.parent.parent / "r_scripts" / "clean.R"


class REngineError(Exception):
    pass


class RCleaningEngine(CleaningEngine):
    def clean(
        self, df: pd.DataFrame, options: CleaningOptions
    ) -> tuple[pd.DataFrame, CleaningReport]:
        start = time.time()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.csv"
            output_path = Path(tmpdir) / "cleaned.csv"
            report_path = Path(tmpdir) / "report.json"
            options_json = options.model_dump_json()

            df.to_csv(input_path, index=False)

            result = subprocess.run(
                [
                    "Rscript",
                    "--vanilla",
                    str(R_SCRIPT_PATH),
                    str(input_path),
                    str(output_path),
                    str(report_path),
                    options_json,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise REngineError(f"R script failed: {result.stderr}")

            cleaned_df = pd.read_csv(output_path)
            report_data = json.loads(report_path.read_text())

            duration_ms = int((time.time() - start) * 1000)

            report = CleaningReport(
                steps=[CleaningStep(**s) for s in report_data["steps"]],
                original_shape=report_data["original_shape"],
                cleaned_shape=report_data["cleaned_shape"],
                duration_ms=duration_ms,
            )

            return cleaned_df, report
