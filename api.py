from dotenv import load_dotenv
load_dotenv()

import asyncio
import re
from pathlib import Path
from datetime import date
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

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

    from prompts import MOMENTUM_PROMPT, VALUE_PROMPT, SHARED_RULES

    # Strip SHARED_RULES from the built-in prompts to get the strategy-only part
    momentum_strategy = MOMENTUM_PROMPT.replace(SHARED_RULES, "").strip()
    value_strategy = VALUE_PROMPT.replace(SHARED_RULES, "").strip()

    seeded = []
    for name in ("momentum", "value"):
        try:
            supabase.table("agent_state").upsert(
                {"name": name, "cash": 100000.0, "holdings": {}, "last_portfolio": None},
                on_conflict="name",
            ).execute()
            seeded.append(name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to seed agent_state {name}: {e}")

    built_ins = [
        {"name": "momentum", "display_name": "MOMENTUM TRADER", "prompt_text": momentum_strategy, "color": "#ff4444", "locked": True},
        {"name": "value",    "display_name": "VALUE ANALYST",   "prompt_text": value_strategy,    "color": "#4ade80", "locked": True},
    ]
    for row in built_ins:
        try:
            supabase.table("agents").upsert(row, on_conflict="name").execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to seed agents table: {e}")

    return {"seeded": seeded}


# ---------- Agent config endpoints ----------

@app.get("/agents")
async def list_agents():
    """Return all active agents."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    result = supabase.table("agents").select("name, display_name, color, locked, prompt_text").eq("active", True).execute()
    return {"agents": result.data or []}


class AgentCreate(BaseModel):
    name: str
    display_name: str
    prompt_text: str
    color: str = "#888888"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not re.match(r"^[a-z0-9_-]{2,32}$", v):
            raise ValueError("name must be 2-32 lowercase alphanumeric/underscore/hyphen characters")
        return v

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v):
        if len(v) > 40:
            raise ValueError("display_name must be 40 characters or fewer")
        return v

    @field_validator("prompt_text")
    @classmethod
    def validate_prompt_text(cls, v):
        if len(v.strip()) < 20:
            raise ValueError("prompt_text must be at least 20 characters")
        return v


@app.post("/agents", status_code=201)
async def create_agent(body: AgentCreate):
    """Create a new custom agent."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    existing = supabase.table("agents").select("name").eq("name", body.name).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail=f"Agent '{body.name}' already exists")

    # Ensure agent_state row exists for the new agent
    supabase.table("agent_state").upsert(
        {"name": body.name, "cash": 100000.0, "holdings": {}, "last_portfolio": None},
        on_conflict="name",
    ).execute()

    supabase.table("agents").insert({
        "name": body.name,
        "display_name": body.display_name,
        "prompt_text": body.prompt_text,
        "color": body.color,
        "locked": False,
        "active": True,
    }).execute()

    return {"name": body.name, "display_name": body.display_name}


@app.delete("/agents/{agent_name}")
async def delete_agent(agent_name: str):
    """Soft-delete a custom agent (locked agents cannot be deleted)."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    result = supabase.table("agents").select("locked").eq("name", agent_name).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    if result.data["locked"]:
        raise HTTPException(status_code=403, detail="Built-in agents cannot be deleted")

    supabase.table("agents").update({"active": False}).eq("name", agent_name).execute()
    return {"deleted": agent_name}


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
    """Current portfolio values, holdings, and cash for all active agents."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    agents_result = supabase.table("agents").select("name").eq("active", True).execute()
    agent_names = [r["name"] for r in (agents_result.data or [])]

    state = load_state(agent_names)
    agents_status = {}

    for name in agent_names:
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

    if agents_status:
        leader = max(agents_status, key=lambda n: agents_status[n]["current_value"])
    else:
        leader = "none"

    return {
        "date": date.today().isoformat(),
        "leader": leader,
        "agents": agents_status,
    }


@app.get("/logs/{agent_name}", response_class=PlainTextResponse)
async def get_logs(agent_name: str, days: int = Query(default=30, ge=1, le=365)):
    """Return the last N days of log entries from Supabase."""
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
