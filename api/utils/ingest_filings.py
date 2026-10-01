"""
Standalone CLI to pre-populate a ticker's filings into Pinecone, ahead of
ever asking the chat agent about it - the explicit counterpart to the
lazy, on-demand ingestion that search_filings falls back to automatically,
and to the per-filing upload button on the Overview page.

Usage:
    python api/utils/ingest_filings.py ONON
    python api/utils/ingest_filings.py ONON --max-filings 4
    python api/utils/ingest_filings.py ONON AAPL NVDA   # multiple tickers
"""
import sys
import os
from dotenv import load_dotenv

# Load .env explicitly from api/ directory
env_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(env_path)

# Add api directory to path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.filing_search_service import FilingSearchService


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python api/utils/ingest_filings.py TICKER [TICKER ...] [--max-filings N]")
        sys.exit(1)

    max_filings = 2
    if "--max-filings" in args:
        i = args.index("--max-filings")
        max_filings = int(args[i + 1])
        args = args[:i] + args[i + 2:]

    tickers = [t.upper() for t in args]
    if not tickers:
        print("No tickers given.")
        sys.exit(1)

    service = FilingSearchService()
    if not service.index:
        print("Error: Pinecone is not configured (missing PINECONE_API_KEY in api/.env).")
        sys.exit(1)

    for ticker in tickers:
        print(f"Ingesting up to {max_filings} filing(s) for {ticker}...")
        result = service.ingest_ticker_filings(ticker, max_filings=max_filings)
        if "status" in result and result["status"] == "error":
            print(f"  Error: {result['message']}")
            continue
        for r in result.get("ingested", []):
            if r.get("status") == "ingested":
                print(f"  {r['accessionNumber']}: {r['chunks']} chunks")
            else:
                print(f"  Error: {r.get('message')}")


if __name__ == "__main__":
    main()
