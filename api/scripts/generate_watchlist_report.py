"""
Generates a short, daily AI summary per watchlist ticker using Anthropic's
Message Batches API - a deliberate deviation from this app's usual "one-shot
analysis = Gemini via AIService" convention (CLAUDE.md), made because this
job's shape fits batching unusually well: N independent, non-interactive,
latency-insensitive per-ticker tasks, run once a day. See docs/ARCHITECTURE.md
and CLAUDE.md for the full reasoning.

Run from repo root: python api/scripts/generate_watchlist_report.py
Needs MONGO_URI (or MONGODB_URI) and ANTHROPIC_API_KEY in the environment.
"""
import sys
import os
import time
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add parent directory to path to import app modules
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(api_dir)

from pymongo import MongoClient
from app.services.finance import FinanceService

REPORT_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 512

# Polled every POLL_INTERVAL_SECONDS, capped at MAX_WAIT_SECONDS (~55 min) -
# comfortably within "most batches finish within an hour" (Anthropic's own
# guidance) and GitHub Actions' default job time limit. A batch that's still
# running past this is abandoned for today rather than left half-handled;
# tomorrow's scheduled run tries again from scratch.
POLL_INTERVAL_SECONDS = 30
MAX_WAIT_SECONDS = 55 * 60

REPORT_SYSTEM_PROMPT = """You write a short daily digest entry for one stock ticker, for someone who already \
holds it on a watchlist and just wants to know what, if anything, changed. You'll be given the ticker's \
current quote and its most recent news headlines.

Write 2-4 sentences. Lead with anything genuinely notable in the news (a real headline, not just routine \
price chatter); if nothing stands out, say so plainly rather than padding the summary. Mention the price \
move only briefly - the reader can already see the number elsewhere. Don't speculate beyond what the \
headlines actually say. This is informational only, not investment advice."""


def _build_user_content(quote: dict, news: list[dict]) -> str:
    quote_text = (
        f"Price: ${quote.get('price')}, change: {quote.get('change'):+.2f} "
        f"({quote.get('change_percent'):+.2f}%), volume: {quote.get('volume')}"
    )
    if news:
        news_text = "\n".join(f"- {n['title']} ({n['publisher']})" for n in news)
    else:
        news_text = "No recent news found."
    return f"<quote>\n{quote_text}\n</quote>\n\n<recent_news>\n{news_text}\n</recent_news>"


def main():
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    if not uri:
        print("MONGO_URI not found in environment variables.")
        sys.exit(1)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not found in environment variables.")
        sys.exit(1)

    client = MongoClient(uri)
    db = client["ai_stock_analyst"]

    watchlist_items = list(db["watchlist"].find({}))
    if not watchlist_items:
        print("Watchlist is empty, nothing to report on.")
        return

    tickers = [item["ticker"] for item in watchlist_items]
    names = {item["ticker"]: item.get("name", item["ticker"]) for item in watchlist_items}
    print(f"Building report for {len(tickers)} tickers: {', '.join(tickers)}")

    finance_service = FinanceService()
    quotes = {q["ticker"]: q for q in finance_service.get_quotes(tickers) if q}

    import anthropic
    anthropic_client = anthropic.Anthropic(api_key=api_key)

    requests = []
    for ticker in tickers:
        quote = quotes.get(ticker)
        if not quote:
            print(f"  {ticker}: no quote data, skipping")
            continue
        news = finance_service.get_company_news(ticker)
        requests.append({
            "custom_id": ticker,
            "params": {
                "model": REPORT_MODEL,
                "max_tokens": MAX_TOKENS,
                "system": [{"type": "text", "text": REPORT_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                "messages": [{"role": "user", "content": _build_user_content(quote, news)}],
            },
        })

    if not requests:
        print("No tickers had usable quote data, nothing to submit.")
        return

    print(f"Submitting a batch of {len(requests)} requests...")
    batch = anthropic_client.messages.batches.create(requests=requests)
    print(f"Batch {batch.id} submitted, status={batch.processing_status}")

    waited = 0
    while batch.processing_status != "ended":
        if waited >= MAX_WAIT_SECONDS:
            print(f"Batch {batch.id} still not done after {waited}s - giving up for today.")
            sys.exit(1)
        time.sleep(POLL_INTERVAL_SECONDS)
        waited += POLL_INTERVAL_SECONDS
        batch = anthropic_client.messages.batches.retrieve(batch.id)
        print(f"  ...status={batch.processing_status} ({waited}s elapsed)")

    print(f"Batch ended after {waited}s: {batch.request_counts}")

    reports = []
    for item in anthropic_client.messages.batches.results(batch.id):
        ticker = item.custom_id
        quote = quotes.get(ticker, {})
        if item.result.type != "succeeded":
            print(f"  {ticker}: batch item did not succeed ({item.result.type}), skipping")
            continue
        text = "".join(block.text for block in item.result.message.content if block.type == "text")
        reports.append({
            "ticker": ticker,
            "name": names.get(ticker, ticker),
            "price": quote.get("price"),
            "change": quote.get("change"),
            "change_percent": quote.get("change_percent"),
            "summary": text,
        })

    if not reports:
        print("No successful results, not overwriting the existing report.")
        sys.exit(1)

    doc = {
        "type": "daily_watchlist_report",
        "generated_at": datetime.now(timezone.utc),
        "reports": reports,
    }
    db["watchlist_report"].update_one({"type": "daily_watchlist_report"}, {"$set": doc}, upsert=True)
    print(f"Stored report for {len(reports)}/{len(tickers)} tickers.")


if __name__ == "__main__":
    main()
