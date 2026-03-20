from dotenv import load_dotenv
load_dotenv()

import asyncio
from pathlib import Path
from datetime import date
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from main import run_daily
from tracker import load_state, calculate_value, STARTING_CASH
from db import supabase

DIST_DIR = Path(__file__).parent / "static" / "dist"

app = FastAPI(
    title="Stock Agent Competition API",
    description="Two AI agents compete daily to build the best stock portfolio.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

_run_lock = asyncio.Lock()


@app.get("/health")
async def health():
    sb_status = "not configured"
    if supabase:
        try:
            supabase.table("agent_state").select("count", count="exact").limit(0).execute()
            sb_status = "connected"
        except Exception as e:
            sb_status = f"error: {e}"
    return {"status": "ok", "date": date.today().isoformat(), "supabase": sb_status}


@app.post("/seed-db")
async def seed_db():
    """Seed initial agent rows (run after creating tables in Supabase SQL Editor)."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    seeded = []
    for name in ("momentum", "value"):
        try:
            supabase.table("agent_state").upsert(
                {"name": name, "cash": 100000.0, "holdings": {}, "last_portfolio": None},
                on_conflict="name",
            ).execute()
            seeded.append(name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to seed {name}: {e}")

    return {"seeded": seeded}


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
async def get_logs(agent_name: str, days: int = Query(default=30, ge=1, le=365)):
    """Return the last N days of log entries from Supabase."""
    if agent_name not in ("momentum", "value"):
        raise HTTPException(status_code=404, detail="Agent must be 'momentum' or 'value'")
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    result = (
        supabase.table("agent_logs")
        .select("log_text")
        .eq("agent_name", agent_name)
        .order("date", desc=True)
        .limit(days)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail=f"No logs found for {agent_name}")

    return "\n".join(row["log_text"] for row in reversed(result.data))


@app.get("/history/{agent_name}")
async def get_history(agent_name: str, last: int = Query(default=30, ge=1, le=365)):
    """Return the last N days of history for an agent from Supabase."""
    if agent_name not in ("momentum", "value"):
        raise HTTPException(status_code=404, detail="Agent must be 'momentum' or 'value'")
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    total = (
        supabase.table("agent_history")
        .select("*", count="exact")
        .eq("agent_name", agent_name)
        .execute()
    )

    entries = (
        supabase.table("agent_history")
        .select("date, value, trades, trade_cost, portfolio")
        .eq("agent_name", agent_name)
        .order("date", desc=True)
        .limit(last)
        .execute()
    )

    rows = list(reversed(entries.data)) if entries.data else []

    return {
        "agent": agent_name,
        "total_days": total.count or 0,
        "showing": len(rows),
        "history": rows,
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Serve the React SPA for all non-API routes (production only)."""
    index = DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"detail": "Frontend not built. Run: cd frontend && npm run build"}
