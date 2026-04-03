# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stock Agent Competition — an AI-powered portfolio management system where multiple GPT-4o agents compete by making stock trading decisions based on Reddit sentiment analysis and market fundamentals. FastAPI backend + React/Vite frontend deployed to Render.com.

## Commands

### Backend (Python)
```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server (development)
uvicorn api:app --reload --port 8000

# Run the daily agent trading loop manually
python main.py

# Seed the Supabase database with default agents
curl -X POST http://localhost:8000/seed-db
```

### Frontend (React)
```bash
cd frontend

# Install dependencies
npm install

# Development server (proxies API calls to localhost:8000)
npm run dev

# Build for production (outputs to /static/dist/ served by FastAPI)
npm run build

# Lint
npm run lint
```

### Full Production Build (as Render does)
```bash
pip install -r requirements.txt && cd frontend && npm install && npm run build
uvicorn api:app --host 0.0.0.0 --port $PORT
```

## Architecture

### Request Flow
1. Frontend (`Dashboard.jsx`) polls `/agents`, `/status`, and `/history/:agent` on load + every 60s
2. "RUN AGENTS" button → `POST /run` → `main.run_daily()` → runs each agent sequentially
3. Each agent: GPT-4o tool-calling loop (`agent.py`) → Reddit + yfinance data (`tools.py`) → portfolio JSON
4. Portfolio validated (`portfolio.py`) → rebalanced (`tracker.py`) → state saved to Supabase
5. Daily logs written to `agent_logs` table; history snapshot to `agent_history`

### Key Data Files
| File | Role |
|------|------|
| `agent.py` | GPT-4o tool-calling loop; enforces 200-call daily API budget shared across agents |
| `tools.py` | Reddit sentiment tools (`search_reddit`, `get_hot_posts`) + yfinance stock data; defines OpenAI tool schemas |
| `tracker.py` | Portfolio rebalancing math: converts weight % → share counts, deducts $3/trade, saves state to Supabase |
| `main.py` | Daily orchestration: loads all active agents, runs each, displays leaderboard |
| `api.py` | FastAPI routes + Supabase CRUD; uses `asyncio.Lock` to prevent concurrent runs |
| `prompts.py` | Agent strategy prompts with `{previous_portfolio}` placeholder; `SHARED_RULES` enforces 7–20 stocks, 5–25% per position, weights must sum to 100% |
| `logger.py` | Formats trade summaries → saves to `agent_logs` Supabase table |

### Supabase Schema (4 tables)
- **`agents`** — config: name (PK), display_name, prompt_text, color, locked, active
- **`agent_state`** — current holdings: cash, holdings (jsonb), last_portfolio (jsonb)
- **`agent_history`** — daily snapshots: (agent_name, date) PK, value, trades, trade_cost, portfolio
- **`agent_logs`** — human-readable daily summaries: agent_name, date, log_text

### Agent System
- Two built-in locked agents: **momentum** (Reddit hype chaser) and **value** (contrarian fundamentals)
- Custom agents: user-created via `POST /agents`, soft-deleted (active=False) via `DELETE /agents/:name`
- Locked agents cannot be deleted
- Each agent gets its own `agent_state` and `agent_history` rows

### Frontend → Backend Integration
- Vite dev config proxies `/api` and direct API paths to `localhost:8000`
- Production: FastAPI serves built frontend from `/static/dist/` with SPA fallback on `/{full_path:path}`
- `frontend/src/api.js` centralizes all fetch calls

## Environment Variables

Required in `.env` (backend root):
```
OPENAI_API_KEY=       # GPT-4o API access
SUPABASE_URL=         # Supabase project URL
SUPABASE_KEY=         # Supabase anon/service key
SUPABASE_PASSWORD=    # Database password
```

## Deployment

Configured in `render.yaml` as a Python web service on Render.com. Build installs Python deps then builds the React app; start command runs uvicorn on `$PORT`.
