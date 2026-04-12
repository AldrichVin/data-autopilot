# Data Autopilot - AI Agent

Autonomous data analysis powered by Claude. Upload a CSV, get a complete analysis with intelligent cleaning decisions, visualizations, statistical insights, and a PDF report.

## Two Ways to Run

### Option 1: Claude Code Command (Recommended — uses your Max plan)

From the `data-autopilot` project directory in Claude Code:

```
/analyze path/to/data.csv
/analyze sales_q1.csv "Q1 2026 Sales Analysis"
```

Claude reasons about your data at every step — choosing cleaning strategies, identifying patterns, writing insights like a real analyst.

### Option 2: Local Script (No AI — smart defaults only)

```bash
pip install requests python-dotenv
python agent/run_local.py path/to/data.csv
python agent/run_local.py data.csv --title "Q1 Sales Analysis"
```

Runs the full pipeline with automatic strategy selection based on data profiling. No AI reasoning, but fast and free.

### Option 3: Managed Agents API (When you get an API key)

```bash
pip install -r agent/requirements.txt
# Set ANTHROPIC_API_KEY and DATA_AUTOPILOT_BACKEND_URL in agent/.env
python agent/create_agent.py   # One-time setup
python agent/run_session.py data.csv
```

Deploys as a serverless agent on Anthropic's infrastructure. Best for productizing as a paid service.

## Prerequisites

- Data Autopilot backend running: `cd backend && uvicorn main:app --reload`
- For Option 1: Claude Code with Max plan
- For Option 3: Anthropic API key with managed-agents beta access

## File Structure

```
agent/
├── run_local.py             # Local pipeline script (Option 2)
├── create_agent.py          # Managed Agent setup (Option 3)
├── run_session.py           # Managed Agent runner (Option 3)
├── agent_definition.json    # Agent config reference
├── system_prompt.md         # Agent instructions (used by all options)
├── requirements.txt
├── .env.example
└── outputs/                 # Generated analysis outputs

.claude/commands/
└── analyze.md               # Claude Code command (Option 1)
```
