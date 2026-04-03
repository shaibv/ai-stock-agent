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
    """Fetch price, P/E, market cap, 52w range, 30d momentum, and today's change via yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="30d")

        # Today's live price and intraday change via fast_info
        fi = stock.fast_info
        live_price = round(fi.last_price, 2) if fi.last_price else None
        prev_close = fi.previous_close
        today_change_pct = round((fi.last_price - prev_close) / prev_close * 100, 2) if fi.last_price and prev_close else None

        # 30-day momentum uses daily closes (yesterday back to 30 days ago)
        start = hist["Close"].iloc[0] if not hist.empty else None
        momentum = round((prev_close - start) / start * 100, 1) if prev_close and start else None

        return {
            "ticker": ticker,
            "price": live_price,
            "today_change_pct": today_change_pct,
            "prev_close": round(prev_close, 2) if prev_close else None,
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

# ── Tool 5: Yahoo Finance News ──────────────────────────────────

def get_stock_news(ticker: str, limit: int = 8) -> dict:
    """Fetch recent news headlines for a ticker via Yahoo Finance."""
    try:
        items = yf.Ticker(ticker).news or []
        news = []
        for n in items[:limit]:
            content = n.get("content", {})
            news.append({
                "title": content.get("title"),
                "publisher": content.get("provider", {}).get("displayName"),
                "published": content.get("pubDate"),
                "summary": content.get("summary", "")[:300],
            })
        return {"ticker": ticker, "news_count": len(news), "news": news}
    except Exception as e:
        return {"ticker": ticker, "error": str(e), "news": []}


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
                "Fetch current live price, today's intraday change %, previous close, "
                "P/E ratio, market cap, 52-week range, 30-day momentum, and short interest. "
                "today_change_pct reflects what the stock has done TODAY — use this to avoid "
                "buying into a stock that is already down sharply or to confirm momentum. "
                "Always call this after Reddit research to validate sentiment against real fundamentals."
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
            "name": "get_stock_news",
            "description": (
                "Fetch recent news headlines and summaries for a ticker from Yahoo Finance. "
                "Use this to identify catalysts (earnings, FDA approvals, CEO changes, lawsuits) "
                "that explain Reddit buzz or contradict it. Call this alongside get_stock_data "
                "for any ticker you're seriously considering — news explains the 'why' behind price moves."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL"},
                    "limit": {"type": "integer", "description": "Number of headlines to return (default 8)"},
                },
                "required": ["ticker"]
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
    "get_stock_news": get_stock_news,
    "get_hot_posts": get_hot_posts,
    "search_multiple_subreddits": search_multiple_subreddits,
}