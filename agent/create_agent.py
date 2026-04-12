"""
Create the Data Autopilot Managed Agent on Anthropic's platform.

Usage:
    python create_agent.py

Prerequisites:
    - ANTHROPIC_API_KEY set in .env or environment
    - DATA_AUTOPILOT_BACKEND_URL set in .env or environment

Output:
    Prints the agent_id and environment_id to use with run_session.py
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

AGENT_DIR = Path(__file__).parent
BACKEND_URL = os.environ["DATA_AUTOPILOT_BACKEND_URL"]


def load_system_prompt() -> str:
    prompt_path = AGENT_DIR / "system_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


def create_agent(client: anthropic.Anthropic) -> dict:
    """Create the managed agent and return its configuration."""

    system_prompt = load_system_prompt()

    agent = client.beta.agents.create(
        model="claude-sonnet-4-6",
        name="data-autopilot-analyst",
        description=(
            "Autonomous data analyst that profiles, cleans, visualizes, "
            "and reports on CSV datasets."
        ),
        instructions=system_prompt,
        tools=[
            {"type": "bash_20250124", "name": "bash"},
            {"type": "text_editor_20250124", "name": "text_editor"},
        ],
        beta="managed-agents-2026-04-01",
    )

    return agent


def create_environment(client: anthropic.Anthropic) -> dict:
    """Create the cloud environment for the agent."""

    environment = client.beta.environments.create(
        name="data-autopilot-env",
        os="linux",
        arch="x86_64",
        packages=["python3", "python3-pip", "curl", "jq"],
        setup_commands=[
            "pip install requests pandas",
        ],
        env_vars={
            "BACKEND_URL": BACKEND_URL,
        },
        beta="managed-agents-2026-04-01",
    )

    return environment


def save_config(agent_id: str, environment_id: str) -> None:
    """Save agent and environment IDs for run_session.py."""

    config = {
        "agent_id": agent_id,
        "environment_id": environment_id,
        "backend_url": BACKEND_URL,
    }

    config_path = AGENT_DIR / "agent_config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Config saved to {config_path}")


def main() -> None:
    client = anthropic.Anthropic()

    print("Creating managed agent...")
    agent = create_agent(client)
    print(f"  Agent ID: {agent.id}")
    print(f"  Name: {agent.name}")

    print("Creating environment...")
    environment = create_environment(client)
    print(f"  Environment ID: {environment.id}")

    save_config(agent.id, environment.id)

    print("\nSetup complete! Run an analysis with:")
    print(f"  python run_session.py <path_to_csv>")


if __name__ == "__main__":
    main()
