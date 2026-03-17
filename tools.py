import requests
import yfinance as yf
import json

# Reddit blocks the default Python user-agent — set a custom one
HEADERS = {"User-Agent": "stock-sentiment-agent/1.0"}


# ── Tool 1: Reddit Sentiment ────────────────────────────────────

def search_reddit(ticker: str, limit: int = 10) -> dict:
    """Search r/wallstreetbets + r/investing for posts about a ticker."""
    subreddits = "wallstreetbets+investing+stocks"
    url = (
        f"https://www.reddit.com/r/{subreddits}/search.json"
        f"?q={ticker}&sort=hot&limit={limit}&restrict_sr=1&t=week"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        children = resp.json()["data"]["children"]
    except Exception as e:
        return {"ticker": ticker, "error": str(e), "posts": []}

    posts = []
    for child in children:
        d = child["data"]
        if d.get("score", 0) < 10:  # Skip low-engagement posts
            continue
        posts.append({
            "title": d.get("title", ""),
            "body": d.get("selftext", "")[:300],  # Trim body to 300 chars
            "upvotes": d.get("score", 0),
            "upvote_ratio": d.get("upvote_ratio", 0),
            "comments": d.get("num_comments", 0),
            "subreddit": d.get("subreddit", ""),
        })
    return {"ticker": ticker, "post_count": len(posts), "posts": posts}


# ── Tool 2: Stock Data ──────────────────────────────────────────

def get_stock_data(ticker: str) -> dict:
    """Fetch price, P/E, market cap, 52w range, 30d momentum via yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="30d")
        current = round(hist["Close"].iloc[-1], 2) if not hist.empty else None
        start   = hist["Close"].iloc[0]              if not hist.empty else None
        momentum = round((current - start) / start * 100, 1) if current and start else None
        return {
            "ticker": ticker,
            "price": current,
            "pe_ratio": info.get("forwardPE"),
            "market_cap_B": round(info.get("marketCap", 0) / 1e9, 1),
            "week52_high": info.get("fiftyTwoWeekHigh"),
            "week52_low": info.get("fiftyTwoWeekLow"),
            "momentum_30d_pct": momentum,
            "sector": info.get("sector"),
            "short_ratio": info.get("shortRatio"),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ── Tool 3: Hot Posts in r/investing ────────────────────────────

def get_hot_posts(subreddit: str = "investing", limit: int = 25) -> dict:
    """Fetch the hottest posts from a given subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        children = resp.json()["data"]["children"]
    except Exception as e:
        return {"subreddit": subreddit, "error": str(e), "posts": []}

    posts = []
    for child in children:
        d = child["data"]
        posts.append({
            "title": d.get("title", ""),
            "body": d.get("selftext", "")[:300],
            "upvotes": d.get("score", 0),
            "upvote_ratio": d.get("upvote_ratio", 0),
            "comments": d.get("num_comments", 0),
            "url": d.get("url", ""),
        })
    return {"subreddit": subreddit, "post_count": len(posts), "posts": posts}


# ── Tool 4: Multi-Subreddit Search ─────────────────────────────

def search_multiple_subreddits(query: str, subreddits: str = "wallstreetbets+investing+stocks", sort: str = "new", limit: int = 15) -> dict:
    """Search across multiple subreddits for a query (e.g. a ticker or topic)."""
    url = (
        f"https://www.reddit.com/r/{subreddits}/search.json"
        f"?q={query}&sort={sort}&limit={limit}&restrict_sr=1"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        children = resp.json()["data"]["children"]
    except Exception as e:
        return {"query": query, "error": str(e), "posts": []}

    posts = []
    for child in children:
        d = child["data"]
        posts.append({
            "title": d.get("title", ""),
            "body": d.get("selftext", "")[:300],
            "upvotes": d.get("score", 0),
            "upvote_ratio": d.get("upvote_ratio", 0),
            "comments": d.get("num_comments", 0),
            "subreddit": d.get("subreddit", ""),
            "url": d.get("url", ""),
        })
    return {"query": query, "subreddits": subreddits, "post_count": len(posts), "posts": posts}

# ── Tool Schemas (OpenAI function-calling format) ────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_reddit",
            "description": (
                "Search Reddit (r/wallstreetbets, r/investing, r/stocks) for posts "
                "discussing a stock. Returns titles, body text, upvote scores, upvote "
                "ratio, and comment counts. Higher upvotes + ratio = stronger signal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker, e.g. NVDA"},
                    "limit": {"type": "integer", "description": "Posts to fetch (default 10)"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_data",
            "description": (
                "Fetch current price, P/E ratio, market cap, 52-week range, "
                "30-day momentum, and short interest. Always call this after "
                "Reddit research to validate sentiment against real fundamentals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hot_posts",
            "description": (
                "Fetch the hottest posts from a subreddit. Defaults to r/investing. "
                "Use this to discover trending topics and overall market sentiment "
                "before drilling into specific tickers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subreddit": {"type": "string", "description": "Subreddit name without r/ prefix (default: investing)"},
                    "limit": {"type": "integer", "description": "Number of posts to fetch (default 25)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_multiple_subreddits",
            "description": (
                "Search across r/wallstreetbets, r/investing, and r/stocks simultaneously "
                "for a query (ticker, topic, or keyword). Returns newest posts by default. "
                "Use this for broad cross-subreddit research on a specific topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, e.g. a ticker symbol or topic"},
                    "subreddits": {"type": "string", "description": "Plus-separated subreddit names (default: wallstreetbets+investing+stocks)"},
                    "sort": {"type": "string", "description": "Sort order: new, hot, relevance, top (default: new)"},
                    "limit": {"type": "integer", "description": "Number of posts to fetch (default 15)"}
                },
                "required": ["query"]
            }
        }
    }
]

# Dispatcher: maps tool name → Python function
TOOL_FUNCTIONS = {
    "search_reddit": search_reddit,
    "get_stock_data": get_stock_data,
    "get_hot_posts": get_hot_posts,
    "search_multiple_subreddits": search_multiple_subreddits,
}