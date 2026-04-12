"""
Run Data Autopilot analysis locally without Claude API.

This is the non-AI version that runs the full pipeline with smart defaults.
For the AI-powered version, use the Claude Code command: /analyze <csv_path>

Usage:
    python run_local.py <path_to_csv>
    python run_local.py data.csv --title "Q1 Sales Analysis"
    python run_local.py data.csv --backend http://localhost:8000
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

import requests

DEFAULT_BACKEND = "http://localhost:8000"


def check_backend(base_url: str) -> bool:
    try:
        resp = requests.get(f"{base_url}/health", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def upload(base_url: str, csv_path: Path) -> dict:
    print(f"Uploading {csv_path.name}...")
    with open(csv_path, "rb") as f:
        resp = requests.post(
            f"{base_url}/api/v1/upload",
            files={"file": (csv_path.name, f, "text/csv")},
        )
    resp.raise_for_status()
    data = resp.json()

    profile = data["profile"]
    print(f"  Rows: {profile['total_rows']}")
    print(f"  Columns: {profile['total_columns']}")
    print(f"  Duplicates: {profile['duplicate_row_count']}")
    return data


def decide_cleaning_strategy(profile: dict) -> dict:
    """Choose cleaning options based on the data profile."""

    columns = profile["columns"]
    total_rows = profile["total_rows"]

    # Calculate overall null percentage
    total_nulls = sum(col["null_count"] for col in columns)
    total_cells = total_rows * len(columns)
    null_pct = (total_nulls / total_cells * 100) if total_cells > 0 else 0

    # Check for skewness in numeric columns
    numeric_cols = [c for c in columns if c["inferred_type"] == "numeric"]
    has_skewed = any(
        abs(c.get("stats", {}).get("skewness", 0) or 0) > 2
        for c in numeric_cols
        if c.get("stats")
    )

    # Check column type distribution
    categorical_count = sum(
        1 for c in columns if c["inferred_type"] in ("categorical", "text")
    )
    is_mostly_categorical = categorical_count > len(columns) / 2

    # Decide fill strategy
    if null_pct < 5:
        fill_strategy = "drop"
        reason = f"low null rate ({null_pct:.1f}%)"
    elif is_mostly_categorical:
        fill_strategy = "mode"
        reason = "mostly categorical columns"
    elif has_skewed:
        fill_strategy = "median"
        reason = "skewed numeric distributions"
    else:
        fill_strategy = "mean"
        reason = "roughly normal distributions"

    options = {
        "fill_strategy": fill_strategy,
        "remove_duplicates": True,
        "fix_types": True,
        "handle_outliers": has_skewed,
        "standardize_strings": categorical_count > 0,
    }

    print(f"\nCleaning strategy:")
    print(f"  Fill: {fill_strategy} ({reason})")
    print(f"  Outliers: {'yes' if has_skewed else 'no'}")
    print(f"  Strings: {'yes' if categorical_count > 0 else 'no'}")

    return options


def clean(base_url: str, session_id: str, options: dict) -> dict:
    print("\nCleaning data...")
    resp = requests.post(
        f"{base_url}/api/v1/clean",
        json={
            "session_id": session_id,
            "engine": "python",
            "options": options,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    report = data["cleaning_report"]
    orig = report["original_shape"]
    cleaned = report["cleaned_shape"]
    print(f"  Original: {orig[0]} rows x {orig[1]} cols")
    print(f"  Cleaned:  {cleaned[0]} rows x {cleaned[1]} cols")
    print(f"  Duration: {report['duration_ms']}ms")

    for step in report["steps"]:
        if step["rows_affected"] > 0:
            print(f"  - {step['description']}: {step['rows_affected']} rows affected")

    return data


def visualize(base_url: str, session_id: str) -> dict:
    print("\nGenerating visualizations & statistical analysis...")
    resp = requests.post(
        f"{base_url}/api/v1/visualize",
        json={
            "session_id": session_id,
            "formats": ["vegalite", "plotly"],
        },
    )
    resp.raise_for_status()
    data = resp.json()

    charts = data.get("charts", [])
    print(f"  Generated {len(charts)} charts")

    for i, chart in enumerate(charts[:5], 1):
        print(f"  {i}. [{chart['chart_type']}] {chart['title']}")
        if chart.get("description"):
            print(f"     {chart['description'][:80]}...")

    if len(charts) > 5:
        print(f"  ... and {len(charts) - 5} more")

    return data


def export_report(
    base_url: str, session_id: str, title: str, output_dir: Path
) -> tuple[Path, Path]:
    print("\nExporting reports...")
    encoded_title = quote(title)

    html_path = output_dir / "report.html"
    pdf_path = output_dir / "report.pdf"

    # HTML report
    resp = requests.get(
        f"{base_url}/api/v1/export/{session_id}/report_html?title={encoded_title}"
    )
    resp.raise_for_status()
    html_path.write_bytes(resp.content)
    print(f"  HTML: {html_path}")

    # PDF report (may fail if weasyprint not installed)
    try:
        resp = requests.get(
            f"{base_url}/api/v1/export/{session_id}/report_pdf?title={encoded_title}"
        )
        resp.raise_for_status()
        pdf_path.write_bytes(resp.content)
        print(f"  PDF:  {pdf_path}")
    except Exception:
        print("  PDF:  Skipped (weasyprint may not be installed)")
        pdf_path = None

    return html_path, pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Data Autopilot analysis locally"
    )
    parser.add_argument("csv_path", help="Path to the CSV file")
    parser.add_argument("--title", help="Report title", default=None)
    parser.add_argument("--backend", help="Backend URL", default=DEFAULT_BACKEND)
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    title = args.title or f"Analysis of {csv_path.stem}"

    # Check backend
    if not check_backend(args.backend):
        print(f"Error: Backend not reachable at {args.backend}")
        print("Start it with: cd backend && uvicorn main:app --reload")
        sys.exit(1)

    print(f"Data Autopilot Analysis: {csv_path.name}")
    print(f"Title: {title}")
    print("=" * 60)

    # Run pipeline
    upload_data = upload(args.backend, csv_path)
    session_id = upload_data["session_id"]
    profile = upload_data["profile"]

    options = decide_cleaning_strategy(profile)
    clean(args.backend, session_id, options)
    visualize(args.backend, session_id)

    output_dir = Path(__file__).parent / "outputs" / csv_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    html_path, pdf_path = export_report(args.backend, session_id, title, output_dir)

    # Save session info
    session_info = {
        "session_id": session_id,
        "file": csv_path.name,
        "title": title,
        "cleaning_options": options,
        "report_html": str(html_path),
        "report_pdf": str(pdf_path) if pdf_path else None,
    }
    info_path = output_dir / "session.json"
    info_path.write_text(json.dumps(session_info, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print(f"Results saved to: {output_dir}")
    print(f"\nFor AI-powered analysis with insights, use Claude Code:")
    print(f"  /analyze {csv_path}")


if __name__ == "__main__":
    main()
