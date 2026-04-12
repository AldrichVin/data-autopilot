"""
Run a Data Autopilot analysis session on a CSV file.

Usage:
    python run_session.py <path_to_csv>
    python run_session.py data.csv --title "Q1 Sales Analysis"

Prerequisites:
    - Run create_agent.py first to generate agent_config.json
    - ANTHROPIC_API_KEY set in .env or environment
    - Data Autopilot backend running at the configured URL
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

AGENT_DIR = Path(__file__).parent


def load_config() -> dict:
    config_path = AGENT_DIR / "agent_config.json"
    if not config_path.exists():
        print("Error: agent_config.json not found.")
        print("Run 'python create_agent.py' first to set up the agent.")
        sys.exit(1)
    return json.loads(config_path.read_text(encoding="utf-8"))


def run_analysis(csv_path: str, title: str | None = None) -> None:
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    if not csv_file.suffix.lower() == ".csv":
        print(f"Warning: File does not have .csv extension: {csv_file.name}")

    config = load_config()
    client = anthropic.Anthropic()

    report_title = title or f"Analysis of {csv_file.stem}"

    # Step 1: Create a session
    print(f"Starting analysis session for: {csv_file.name}")
    print(f"Report title: {report_title}")
    print("-" * 60)

    session = client.beta.sessions.create(
        agent_id=config["agent_id"],
        environment_id=config["environment_id"],
        beta="managed-agents-2026-04-01",
    )
    print(f"Session ID: {session.id}")

    # Step 2: Upload the CSV as a session resource
    print("Uploading dataset...")
    csv_content = csv_file.read_bytes()

    client.beta.sessions.resources.create(
        session_id=session.id,
        type="file",
        name=csv_file.name,
        content=csv_content,
        beta="managed-agents-2026-04-01",
    )
    print(f"  Uploaded: {csv_file.name} ({len(csv_content):,} bytes)")

    # Step 3: Send the analysis request
    print("\nAgent is analyzing your data...\n")

    user_message = (
        f"Analyze the uploaded dataset '{csv_file.name}'. "
        f"Use the report title '{report_title}'. "
        f"Run the full pipeline: upload to the backend API, profile the data, "
        f"decide on the best cleaning strategy based on the profile, clean it, "
        f"generate visualizations and statistical analysis, export the report, "
        f"and provide a comprehensive natural-language analysis summary. "
        f"The CSV file is available at /tmp/{csv_file.name}."
    )

    # Send message and stream the response
    event_stream = client.beta.sessions.events.create(
        session_id=session.id,
        type="user_message",
        content=user_message,
        stream=True,
        beta="managed-agents-2026-04-01",
    )

    analysis_output = []

    for event in event_stream:
        match event.type:
            case "content_block_delta":
                if hasattr(event.delta, "text"):
                    text = event.delta.text
                    print(text, end="", flush=True)
                    analysis_output.append(text)

            case "tool_use":
                tool_name = getattr(event, "name", "unknown")
                print(f"\n  [Running: {tool_name}]", flush=True)

            case "message_stop":
                print("\n")

            case "error":
                error_msg = getattr(event, "message", str(event))
                print(f"\nError: {error_msg}")
                sys.exit(1)

    # Step 4: Save the analysis output
    output_dir = AGENT_DIR / "outputs"
    output_dir.mkdir(exist_ok=True)

    analysis_path = output_dir / f"{csv_file.stem}_analysis.md"
    analysis_path.write_text("".join(analysis_output), encoding="utf-8")
    print(f"Analysis saved to: {analysis_path}")

    # Step 5: Download the report if available
    print(f"\nSession complete: {session.id}")
    print(f"Backend URL: {config['backend_url']}")
    print(
        f"Download PDF report: "
        f"{config['backend_url']}/api/v1/export/<session_id>/report_pdf"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Data Autopilot analysis on a CSV file"
    )
    parser.add_argument("csv_path", help="Path to the CSV file to analyze")
    parser.add_argument(
        "--title",
        help="Title for the analysis report",
        default=None,
    )
    args = parser.parse_args()

    run_analysis(args.csv_path, args.title)


if __name__ == "__main__":
    main()
