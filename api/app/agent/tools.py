"""
Tool registry for the conversational analyst agent (Path A).

Every tool wraps an EXISTING service method — no new data-fetching logic
lives here. Adding a tool is: write its schema, write a one-line dispatch
function that calls the service and (if the payload is large) trims it,
add both to TOOLS / TOOL_DISPATCH. See CLAUDE.md "Adding an agent tool".

`propose_watchlist_add` is the one exception: it never touches the
database. It only signals a proposal, which the chat endpoint surfaces to
the frontend as a distinct event; the actual write happens when the user
clicks Confirm, through the existing, already-authenticated
POST /api/watchlist endpoint. The agent loop has no code path that can
write to the watchlist on its own.
"""
import json
from urllib.parse import urlparse
from app.services.finance import FinanceService
from app.services.sec import SECService
from app.services.sentiment_service import SentimentService
from app.services.institution_service import InstitutionService
from app.services.congress_service import CongressService
from app.services.simulation import SimulationService
from app.services.filing_search_service import FilingSearchService
from app.services.smart_money_service import SmartMoneyService
from app.db import db

finance_service = FinanceService()
sec_service = SECService()
sentiment_service = SentimentService()
institution_service = InstitutionService()
congress_service = CongressService()
simulation_service = SimulationService()
filing_search_service = FilingSearchService()
smart_money_service = SmartMoneyService()


def _cap_list(items, limit, label="items"):
    if isinstance(items, list) and len(items) > limit:
        return items[:limit] + [{"_note": f"truncated to {limit} of {len(items)} {label}"}]
    return items


# ---- dispatch functions -----------------------------------------------

def _search_tickers(query: str):
    return sec_service.search_tickers(query)


def _get_company_info(ticker: str):
    return finance_service.get_company_info(ticker)


def _get_quotes(tickers: list):
    return finance_service.get_quotes(tickers)


def _get_stock_history(ticker: str, period: str = "3mo", interval: str = "1d"):
    data = finance_service.get_stock_history(ticker, period, interval)
    if isinstance(data, list) and len(data) > 60:
        data = data[-60:]
        data[0]["_note"] = "showing the most recent 60 bars only"
    return data


def _get_quarterly_financials(ticker: str):
    return finance_service.get_quarterly_financials(ticker)


def _get_quarterly_balance_sheet(ticker: str):
    return finance_service.get_quarterly_balance_sheet(ticker)


def _get_quarterly_cash_flow(ticker: str):
    return finance_service.get_quarterly_cash_flow(ticker)


def _get_quarterly_ratios(ticker: str):
    return finance_service.get_quarterly_ratios(ticker)


def _get_forecast(ticker: str):
    return finance_service.get_forecast(ticker)


def _get_analyst_actions(ticker: str):
    return _cap_list(finance_service.get_analyst_actions(ticker), 15, "actions")


def _get_ownership_details(ticker: str):
    return finance_service.get_ownership_details(ticker)


def _get_peer_comparison(ticker: str):
    return finance_service.get_peer_comparison(ticker)


def _get_future_leader_score(ticker: str):
    return finance_service.get_future_leader_score(ticker)


def _get_rankings(category: str = "Small Cap", limit: int = 10):
    return finance_service.get_rankings(category, page=1, limit=min(limit, 25))


def _get_company_news(ticker: str):
    return _cap_list(finance_service.get_company_news(ticker), 10, "articles")


def _get_brand_sentiment(ticker: str):
    return sentiment_service.get_brand_sentiment(ticker)


def _get_vanguard_trades(limit: int = 10):
    return institution_service.get_vanguard_trades(limit=min(limit, 20))


def _get_munro_trades(limit: int = 10):
    return institution_service.get_munro_trades(limit=min(limit, 20))


def _get_congress_trades(limit: int = 20):
    return congress_service.get_recent_trades(limit=min(limit, 50))


def _get_macro_indicators():
    return finance_service.get_macro_indicators()


def _get_sector_performance():
    return finance_service.get_sector_performance()


def _run_dcf_simulation(ticker: str, wacc: float = 0.09, bear_case: bool = False):
    result = simulation_service.run_dcf_simulation(ticker, wacc=wacc, bear_case=bear_case)
    if isinstance(result, dict):
        result = {k: v for k, v in result.items() if k != "histogram"}
    return result


def _get_filings(ticker: str):
    return _cap_list(sec_service.get_filings(ticker), 10, "filings")


_ALLOWED_FILING_HOSTS = {"sec.gov", "www.sec.gov", "data.sec.gov"}


def _get_filing_text(url: str):
    # Restrict to sec.gov: `url` is effectively model-chosen (from filing/news
    # content it has read), so this needs a real allow-list, not just trust in
    # the tool description, to stay closed against indirect prompt injection.
    host = urlparse(url).netloc.lower()
    if host not in _ALLOWED_FILING_HOSTS:
        return {"error": "get_filing_text only fetches sec.gov URLs (use a URL from get_filings)."}
    text = sec_service.get_filing_text(url)
    if not text:
        return {"error": "Could not fetch that filing"}
    truncated = len(text) > 15000
    return {"text": text[:15000], "truncated": truncated}


def _search_filings(ticker: str, query: str, limit: int = 5):
    return filing_search_service.search_filings(ticker, query, limit=limit)


def _find_smart_money_convergence(limit: int = 10):
    return smart_money_service.find_convergence(limit=limit)


def _get_watchlist():
    return list(db.get_db().watchlist.find({}, {"_id": 0}))


def _propose_watchlist_add(ticker: str, reason: str):
    # Deliberately does NOT write anything. See module docstring.
    return {"status": "proposed", "ticker": ticker.upper(), "note": "Shown to the user for confirmation; not added yet."}


TOOL_DISPATCH = {
    "search_tickers": _search_tickers,
    "get_company_info": _get_company_info,
    "get_quotes": _get_quotes,
    "get_stock_history": _get_stock_history,
    "get_quarterly_financials": _get_quarterly_financials,
    "get_quarterly_balance_sheet": _get_quarterly_balance_sheet,
    "get_quarterly_cash_flow": _get_quarterly_cash_flow,
    "get_quarterly_ratios": _get_quarterly_ratios,
    "get_forecast": _get_forecast,
    "get_analyst_actions": _get_analyst_actions,
    "get_ownership_details": _get_ownership_details,
    "get_peer_comparison": _get_peer_comparison,
    "get_future_leader_score": _get_future_leader_score,
    "get_rankings": _get_rankings,
    "get_company_news": _get_company_news,
    "get_brand_sentiment": _get_brand_sentiment,
    "get_vanguard_trades": _get_vanguard_trades,
    "get_munro_trades": _get_munro_trades,
    "get_congress_trades": _get_congress_trades,
    "get_macro_indicators": _get_macro_indicators,
    "get_sector_performance": _get_sector_performance,
    "run_dcf_simulation": _run_dcf_simulation,
    "get_filings": _get_filings,
    "get_filing_text": _get_filing_text,
    "search_filings": _search_filings,
    "find_smart_money_convergence": _find_smart_money_convergence,
    "get_watchlist": _get_watchlist,
    "propose_watchlist_add": _propose_watchlist_add,
}

# ---- Anthropic tool schemas ---------------------------------------------
# name/description/input_schema per the Messages API tool-use format.

TOOLS = [
    {
        "name": "search_tickers",
        "description": "Resolve a company name or partial ticker to real ticker symbols, e.g. 'nvidia' -> NVDA. Use this first when the user names a company rather than a ticker.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    {
        "name": "get_company_info",
        "description": "Company/ETF profile and key metrics: sector, market cap, P/E, PEG, margins, ROE, FCF, debt/equity, dividend yield, beta, 52-week range. Start here for any single-ticker question.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_quotes",
        "description": "Live price and day change for one or more tickers.",
        "input_schema": {"type": "object", "properties": {"tickers": {"type": "array", "items": {"type": "string"}}}, "required": ["tickers"]},
    },
    {
        "name": "get_stock_history",
        "description": "Historical OHLCV price bars for a ticker. Defaults to 3 months daily; use a shorter period unless the user asks for a longer trend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "period": {"type": "string", "description": "e.g. 5d, 1mo, 3mo, 1y", "default": "3mo"},
                "interval": {"type": "string", "description": "e.g. 1d, 1wk", "default": "1d"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_quarterly_financials",
        "description": "Last four quarters of the income statement (revenue, net income, margins).",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_quarterly_balance_sheet",
        "description": "Last four quarters of the balance sheet (assets, liabilities, debt, cash).",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_quarterly_cash_flow",
        "description": "Last four quarters of cash flow (operating cash flow, capex, free cash flow).",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_quarterly_ratios",
        "description": "Derived valuation and efficiency ratios by quarter.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_forecast",
        "description": "Analyst price targets and recommendation consensus for a ticker.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_analyst_actions",
        "description": "Recent analyst upgrades/downgrades and price-target changes for a ticker.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_ownership_details",
        "description": "Top institutional holders and recent insider transactions for a ticker.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_peer_comparison",
        "description": "Key metrics for a ticker's closest competitors, side by side.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_future_leader_score",
        "description": "This app's proprietary 0-10 score (growth efficiency, R&D intensity, scalability, PEG, ROIC) for a ticker.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_rankings",
        "description": "Top-ranked tickers by Future Leader score in one market-cap category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["Small Cap", "Mid Cap", "Large Cap"], "default": "Small Cap"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "get_company_news",
        "description": "Recent news headlines for a ticker.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_brand_sentiment",
        "description": "Aggregated brand sentiment score and trending keywords for a ticker, from news and YouTube.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_vanguard_trades",
        "description": "Vanguard's recent top buys/sells from its latest 13F filing.",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}},
    },
    {
        "name": "get_munro_trades",
        "description": "Munro Partners' recent top buys/sells from its latest 13F filing.",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}},
    },
    {
        "name": "get_congress_trades",
        "description": "Recent stock trades disclosed by US Congress members (House and Senate).",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
    },
    {
        "name": "get_macro_indicators",
        "description": "Major indices, rates, currencies, commodities, and economic indicators.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_sector_performance",
        "description": "Performance of the 11 GICS sectors via their SPDR ETFs.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_dcf_simulation",
        "description": "Runs a Monte Carlo DCF valuation for a ticker (slow — several seconds; use it deliberately, not for every ticker in a broad screen). Returns expected intrinsic value, a buy-zone price, win probability, and drawdown risk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "wacc": {"type": "number", "default": 0.09},
                "bear_case": {"type": "boolean", "default": False},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_filings",
        "description": "Recent SEC filings (10-K, 10-Q, 20-F, 6-K) for a ticker, with URLs.",
        "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
    },
    {
        "name": "get_filing_text",
        "description": "Fetches the text of one SEC filing by URL (from get_filings). Truncated to ~15,000 characters.",
        "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    },
    {
        "name": "search_filings",
        "description": (
            "Semantic search across a ticker's SEC filings for a topic or question, e.g. 'margin pressure "
            "guidance' or 'risk factors about competition'. Use this instead of get_filing_text when you need "
            "to find something across filings rather than read one you already have a URL for. If nothing has "
            "been searched for this ticker yet, the most recent filings are fetched and indexed automatically "
            "on first use, which takes longer than other tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["ticker", "query"],
        },
    },
    {
        "name": "find_smart_money_convergence",
        "description": (
            "Market-wide scan (not scoped to one ticker) that cross-references three independent signals - "
            "Congress trades, Vanguard's latest 13F moves, and Munro Partners' latest 13F moves - for tickers "
            "where at least 2 of the 3 agree on the same direction (buy or sell). Each result also includes the "
            "ticker's Future Leader score and its sector's current performance, so you can see whether the "
            "convergence is happening in a hot or cold sector. Slow (10+ seconds) - use it deliberately when "
            "asked something like 'where does smart money agree' or 'any convergence on my watchlist names', "
            "not for every question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10, "description": "Max number of converged tickers to return"},
            },
        },
    },
    {
        "name": "get_watchlist",
        "description": "The user's current watchlist (tickers and names).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "propose_watchlist_add",
        "description": (
            "Propose adding a ticker to the user's watchlist. This does NOT add it — it only shows the user a "
            "confirmation card. Use this instead of claiming you've added something. Only propose a ticker you've "
            "actually looked into in this conversation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "reason": {"type": "string", "description": "One sentence on why this ticker is worth adding."},
            },
            "required": ["ticker", "reason"],
        },
    },
]


def dispatch(name: str, arguments: dict):
    fn = TOOL_DISPATCH.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    try:
        result = fn(**arguments)
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"{name} failed: {e}"}
    # Anthropic tool_result content must be a string. Slicing raw JSON text
    # can cut mid-structure, handing the model malformed data with no signal
    # it's incomplete - wrap it instead of silently truncating.
    serialized = json.dumps(result, default=str)
    if len(serialized) > 8000:
        return json.dumps({
            "truncated": True,
            "note": f"{name}'s result was too large ({len(serialized)} chars) and has been cut short. "
                    "Treat partial_json as incomplete - ask a narrower question, a shorter period, or a smaller limit instead.",
            "partial_json": serialized[:7500],
        })
    return serialized
