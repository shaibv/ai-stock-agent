from datetime import date
from db import supabase


def write_daily_log(
    agent_name: str,
    prev_value: float,
    new_value: float,
    trades: list[dict],
    old_portfolio: dict | None,
    new_portfolio: dict,
    holdings: dict[str, int],
    cash: float,
) -> None:
    """Write a formatted daily entry to the agent_logs table in Supabase."""
    today = date.today().isoformat()
    pct = ((new_value / prev_value) - 1) * 100 if prev_value else 0

    old_weights = {}
    if old_portfolio and "portfolio" in old_portfolio:
        for h in old_portfolio["portfolio"]:
            old_weights[h["ticker"]] = h["weight_pct"]

    new_weights = {}
    if "portfolio" in new_portfolio:
        for h in new_portfolio["portfolio"]:
            new_weights[h["ticker"]] = h["weight_pct"]

    trade_map = {t["ticker"]: t["action"] for t in trades}
    num_trades = len(trades)
    fees = num_trades * 3

    lines = []
    lines.append(f"══ {today} {'═' * 40}")
    lines.append(f"  Value: ${prev_value:,.2f} -> ${new_value:,.2f}  ({pct:+.2f}%)")
    lines.append(f"  Trades: {num_trades}  |  Fees: ${fees}")
    lines.append("")

    all_tickers = sorted(set(list(old_weights.keys()) + list(new_weights.keys())))
    for ticker in all_tickers:
        action = trade_map.get(ticker)
        if action == "buy":
            lines.append(f"  BUY   {ticker:5}  {new_weights[ticker]:3}%  (new position)")
        elif action == "sell":
            lines.append(f"  SELL  {ticker:5}       (removed)")
        elif action == "rebalance":
            old_w = old_weights.get(ticker, 0)
            new_w = new_weights.get(ticker, 0)
            lines.append(f"  REBAL {ticker:5}  {old_w}% -> {new_w}%")
        else:
            w = new_weights.get(ticker, old_weights.get(ticker, 0))
            lines.append(f"  HOLD  {ticker:5}  {w:3}%  (unchanged)")

    lines.append("")
    holdings_str = "  ".join(f"{t}:{s}" for t, s in sorted(holdings.items()))
    lines.append(f"  Holdings: {holdings_str}")
    lines.append(f"  Cash: ${cash:,.2f}")
    lines.append("═" * (len(f"══ {today} ") + 40))
    lines.append("")

    log_text = "\n".join(lines)

    supabase.table("agent_logs").insert({
        "agent_name": agent_name,
        "date": today,
        "log_text": log_text,
    }).execute()
