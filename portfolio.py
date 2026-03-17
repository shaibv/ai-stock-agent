from tracker import STARTING_CASH


def display_portfolio(name: str, data: dict, rebalance_summary: dict | None = None) -> None:
    """Print a single agent's portfolio."""
    if "error" in data:
        print(f"  Error: {data['error']}")
        return
    if "raw_response" in data:
        print(f"  JSON parse failed:\n  {data['raw_response'][:200]}")
        return

    holdings = sorted(data.get("portfolio", []),
                       key=lambda x: x["weight_pct"], reverse=True)
    stars = {"high": "★★★", "medium": "★★☆", "low": "★☆☆"}

    print(f"\n  {'─'*50}")
    print(f"  {name}")
    print(f"  {'─'*50}")

    for h in holdings:
        icon = {"bullish": "🟢", "bearish": "🔴"}.get(h.get("signal", ""), "🟡")
        pct = h["weight_pct"]
        bar = "█" * (pct // 3) + "░" * (13 - pct // 3)
        conf = stars.get(h.get("confidence", "low"), "★☆☆")
        print(f"  {icon} {h['ticker']:5} {bar} {pct:3}%  {conf}")
        print(f"       {h.get('rationale', '')[:68]}...")

    if rebalance_summary:
        trades = rebalance_summary["num_trades"]
        cost = rebalance_summary["trade_cost"]
        print(f"\n  Trades today: {trades}  |  Cost: ${cost:.0f}")

    summary = data.get("summary", "")
    if summary:
        print(f"\n  {summary}")


def validate_portfolio(data: dict) -> bool:
    """Check that a portfolio dict is structurally valid."""
    holdings = data.get("portfolio", [])
    if not holdings:
        return False
    count = len(holdings)
    total = sum(h.get("weight_pct", 0) for h in holdings)
    if abs(total - 100) > 3:
        print(f"  Warning: weights sum to {total}%, expected ~100%")
    if count < 7:
        print(f"  Warning: only {count} stocks (minimum 7)")
    if count > 20:
        print(f"  Warning: {count} stocks (maximum 20)")
    for h in holdings:
        w = h.get("weight_pct", 0)
        if w < 5:
            print(f"  Warning: {h['ticker']} at {w}% (minimum 5%)")
        if w > 25:
            print(f"  Warning: {h['ticker']} at {w}% (maximum 25%)")
    return True


def display_competition(state: dict, daily_results: dict | None = None) -> None:
    """Print the head-to-head competition scoreboard with today's actions."""
    agents = state["agents"]

    print("\n" + "═" * 62)
    print("  🏆  AGENT COMPETITION — Head to Head")
    print("═" * 62)

    header = f"  {'':20} {'MOMENTUM':>16}    {'VALUE':>16}"
    print(header)
    print(f"  {'─'*56}")

    m = agents["momentum"]
    v = agents["value"]

    m_value = _latest_value(m)
    v_value = _latest_value(v)
    m_return = (m_value / STARTING_CASH - 1) * 100
    v_return = (v_value / STARTING_CASH - 1) * 100
    m_total_trades = sum(h.get("trades", 0) for h in m["history"])
    v_total_trades = sum(h.get("trades", 0) for h in v["history"])
    m_total_fees = sum(h.get("trade_cost", 0) for h in m["history"])
    v_total_fees = sum(h.get("trade_cost", 0) for h in v["history"])

    _row("Portfolio Value", f"${m_value:,.0f}", f"${v_value:,.0f}")
    _row("Total Return", f"{m_return:+.2f}%", f"{v_return:+.2f}%")
    _row("Days Tracked", str(len(m["history"])), str(len(v["history"])))
    _row("Total Trades", str(m_total_trades), str(v_total_trades))
    _row("Total Fees", f"${m_total_fees:,.0f}", f"${v_total_fees:,.0f}")

    if m["history"] and v["history"]:
        m_daily = _daily_return(m)
        v_daily = _daily_return(v)
        _row("Today's Return", f"{m_daily:+.2f}%", f"{v_daily:+.2f}%")

    if daily_results:
        _row("Today's Trades",
             str(daily_results.get("momentum", {}).get("num_trades", "-")),
             str(daily_results.get("value", {}).get("num_trades", "-")))
        _row("Today's Fees",
             f"${daily_results.get('momentum', {}).get('trade_cost', 0):.0f}",
             f"${daily_results.get('value', {}).get('trade_cost', 0):.0f}")

    print(f"\n  {'─'*56}")

    if m_value > v_value:
        lead = m_value - v_value
        print(f"  🔴 Momentum leads by ${lead:,.0f}")
    elif v_value > m_value:
        lead = v_value - m_value
        print(f"  🔵 Value leads by ${lead:,.0f}")
    else:
        print(f"  Tied!")

    if daily_results:
        print(f"\n  {'─'*56}")
        print("  Today's Actions:")
        for name, label in [("momentum", "🔴 MOMENTUM"), ("value", "🔵 VALUE")]:
            info = daily_results.get(name)
            if not info:
                continue
            trades = info.get("trades", [])
            if not trades:
                print(f"    {label}: No changes (held)")
            else:
                actions = []
                for t in trades:
                    tag = t["action"].upper()
                    actions.append(f"{tag} {t['ticker']}")
                print(f"    {label}: {', '.join(actions)}")

    print("═" * 62 + "\n")


def _row(label: str, col1: str, col2: str) -> None:
    print(f"  {label:20} {col1:>16}    {col2:>16}")


def _latest_value(agent: dict) -> float:
    if agent["history"]:
        return agent["history"][-1]["value"]
    return agent["cash"]


def _daily_return(agent: dict) -> float:
    history = agent["history"]
    if len(history) < 2:
        return (history[-1]["value"] / STARTING_CASH - 1) * 100
    prev = history[-2]["value"]
    curr = history[-1]["value"]
    return (curr / prev - 1) * 100
