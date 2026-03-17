import json
import os
import math
from datetime import date
import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STATE_FILE = os.path.join(DATA_DIR, "history.json")

TRADE_COST = 3.0
STARTING_CASH = 100_000.0


def load_state() -> dict:
    """Load persistent state from disk, or return a fresh initial state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return _init_state()


def save_state(state: dict) -> None:
    """Write state to disk, creating the data/ directory if needed."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def _init_state() -> dict:
    return {
        "agents": {
            "momentum": _init_agent(),
            "value": _init_agent(),
        }
    }


def _init_agent() -> dict:
    return {
        "cash": STARTING_CASH,
        "holdings": {},
        "last_portfolio": None,
        "history": [],
    }


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


def execute_rebalance(agent_state: dict, new_portfolio: dict) -> dict:
    """
    Convert a new portfolio (weight percentages) into actual share holdings.
    Deducts $3 per trade from cash. Returns summary of what changed.
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

    agent_state["history"].append({
        "date": today,
        "value": new_value,
        "trades": num_trades,
        "trade_cost": trade_cost,
        "portfolio": new_portfolio,
    })

    return {
        "trades": trades,
        "num_trades": num_trades,
        "trade_cost": trade_cost,
        "prev_value": total_value,
        "new_value": new_value,
        "old_portfolio": old_portfolio,
    }
