from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
from pathlib import Path
from datetime import date
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from main import run_daily
from tracker import load_state, calculate_value, DATA_DIR, STATE_FILE, STARTING_CASH

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Stock Agent Competition API",
    description="Two AI agents compete daily to build the best stock portfolio.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_run_lock = asyncio.Lock()


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "date": date.today().isoformat()}


@app.post("/run")
async def trigger_run():
    """Trigger a full daily run for both agents. Returns results when complete."""
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="A run is already in progress")

    async with _run_lock:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, run_daily)

    return results


@app.get("/status")
async def status():
    """Current portfolio values, holdings, and cash for both agents."""
    state = load_state()
    agents_status = {}

    for name in ("momentum", "value"):
        agent = state["agents"][name]
        current_value = calculate_value(agent)
        total_return = (current_value / STARTING_CASH - 1) * 100
        days_tracked = len(agent["history"])
        total_trades = sum(h.get("trades", 0) for h in agent["history"])
        total_fees = sum(h.get("trade_cost", 0) for h in agent["history"])

        agents_status[name] = {
            "current_value": current_value,
            "cash": agent["cash"],
            "holdings": agent["holdings"],
            "total_return_pct": round(total_return, 2),
            "days_tracked": days_tracked,
            "total_trades": total_trades,
            "total_fees": total_fees,
            "last_portfolio": agent.get("last_portfolio"),
        }

    m_val = agents_status["momentum"]["current_value"]
    v_val = agents_status["value"]["current_value"]
    leader = "momentum" if m_val > v_val else "value" if v_val > m_val else "tied"

    return {
        "date": date.today().isoformat(),
        "leader": leader,
        "agents": agents_status,
    }


@app.get("/logs/{agent_name}", response_class=PlainTextResponse)
async def get_logs(agent_name: str, lines: int = Query(default=50, ge=1, le=500)):
    """Return the last N lines from an agent's daily log file."""
    if agent_name not in ("momentum", "value"):
        raise HTTPException(status_code=404, detail="Agent must be 'momentum' or 'value'")

    log_path = os.path.join(DATA_DIR, f"{agent_name}.log")
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail=f"No log file found for {agent_name}")

    with open(log_path, "r") as f:
        all_lines = f.readlines()

    tail = all_lines[-lines:]
    return "".join(tail)


@app.get("/history/{agent_name}")
async def get_history(agent_name: str, last: int = Query(default=30, ge=1, le=365)):
    """Return the last N days of history for an agent."""
    if agent_name not in ("momentum", "value"):
        raise HTTPException(status_code=404, detail="Agent must be 'momentum' or 'value'")

    state = load_state()
    history = state["agents"][agent_name]["history"]

    entries = history[-last:]
    return {
        "agent": agent_name,
        "total_days": len(history),
        "showing": len(entries),
        "history": entries,
    }
