import math
from datetime import date
import yfinance as yf
from db import supabase

TRADE_COST = 3.0
STARTING_CASH = 100_000.0


def load_state(agent_names: list[str]) -> dict:
    """Load persistent state from Supabase for the given agent names."""
    state = {"agents": {}}

    for name in agent_names:
        row = (
            supabase.table("agent_state")
            .select("*")
            .eq("name", name)
            .single()
            .execute()
        )
        agent = row.data

        history_rows = (
            supabase.table("agent_history")
            .select("date, value, trades, trade_cost, portfolio")
            .eq("agent_name", name)
            .order("date")
            .execute()
        )

        state["agents"][name] = {
            "cash": agent["cash"],
            "holdings": agent["holdings"] or {},
            "last_portfolio": agent["last_portfolio"],
            "history": history_rows.data or [],
        }

    return state


def save_state(state: dict) -> None:
    """Write current agent state back to Supabase."""
    for name, agent in state["agents"].items():
        supabase.table("agent_state").update({
            "cash": agent["cash"],
            "holdings": agent["holdings"],
            "last_portfolio": agent["last_portfolio"],
            "updated_at": date.today().isoformat(),
        }).eq("name", name).execute()


def fetch_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch current prices for a list of tickers. Returns {ticker: price}."""
    prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if not hist.empty:
                prices[ticker] = round(hist["Close"].iloc[-1], 2)
        except Exception:
            pass
    return prices


def calculate_value(agent_state: dict) -> float:
    """Calculate total portfolio value = shares * price + cash."""
    holdings = agent_state["holdings"]
    if not holdings:
        return agent_state["cash"]
    prices = fetch_prices(list(holdings.keys()))
    stock_value = sum(
        shares * prices.get(ticker, 0)
        for ticker, shares in holdings.items()
    )
    return round(stock_value + agent_state["cash"], 2)


def diff_portfolios(old_portfolio: dict | None, new_portfolio: dict) -> list[dict]:
    """
    Compare old and new portfolios, return a list of trades.
    Each trade is {"ticker": str, "action": "buy"|"sell"|"rebalance"}.
    """
    old_tickers = {}
    if old_portfolio and "portfolio" in old_portfolio:
        for h in old_portfolio["portfolio"]:
            old_tickers[h["ticker"]] = h["weight_pct"]

    new_tickers = {}
    if "portfolio" in new_portfolio:
        for h in new_portfolio["portfolio"]:
            new_tickers[h["ticker"]] = h["weight_pct"]

    trades = []

    for ticker in new_tickers:
        if ticker not in old_tickers:
            trades.append({"ticker": ticker, "action": "buy"})
        elif new_tickers[ticker] != old_tickers[ticker]:
            trades.append({"ticker": ticker, "action": "rebalance"})

    for ticker in old_tickers:
        if ticker not in new_tickers:
            trades.append({"ticker": ticker, "action": "sell"})

    return trades


def execute_rebalance(agent_name: str, agent_state: dict, new_portfolio: dict) -> dict:
    """
    Convert a new portfolio (weight percentages) into actual share holdings.
    Deducts $3 per trade from cash. Persists history to Supabase.
    """
    old_portfolio = agent_state.get("last_portfolio")
    trades = diff_portfolios(old_portfolio, new_portfolio)
    num_trades = len(trades)
    trade_cost = num_trades * TRADE_COST

    total_value = calculate_value(agent_state)

    investable = total_value - trade_cost
    if investable < 0:
        investable = 0

    all_tickers = [h["ticker"] for h in new_portfolio.get("portfolio", [])]
    prices = fetch_prices(all_tickers)

    new_holdings = {}
    allocated = 0.0

    for holding in new_portfolio.get("portfolio", []):
        ticker = holding["ticker"]
        weight = holding["weight_pct"] / 100.0
        price = prices.get(ticker)
        if price and price > 0:
            target_value = investable * weight
            shares = math.floor(target_value / price)
            new_holdings[ticker] = shares
            allocated += shares * price

    remaining_cash = round(total_value - allocated - trade_cost, 2)

    agent_state["holdings"] = new_holdings
    agent_state["cash"] = remaining_cash
    agent_state["last_portfolio"] = new_portfolio

    today = date.today().isoformat()
    new_value = round(allocated + remaining_cash, 2)

    history_entry = {
        "date": today,
        "value": new_value,
        "trades": num_trades,
        "trade_cost": trade_cost,
        "portfolio": new_portfolio,
    }
    agent_state["history"].append(history_entry)

    supabase.table("agent_history").upsert(
        {
            "agent_name": agent_name,
            "date": today,
            "value": new_value,
            "trades": num_trades,
            "trade_cost": trade_cost,
            "portfolio": new_portfolio,
        },
        on_conflict="agent_name,date",
    ).execute()

    return {
        "trades": trades,
        "num_trades": num_trades,
        "trade_cost": trade_cost,
        "prev_value": total_value,
        "new_value": new_value,
        "old_portfolio": old_portfolio,
    }
