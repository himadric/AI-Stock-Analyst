import json
from typing import List, Literal

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.loop import run_agent_turn
from app.agent.tools import filing_search_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class IngestFilingRequest(BaseModel):
    ticker: str
    accessionNumber: str
    form: str
    filingDate: str
    link: str


# Sync (not async def): run_agent_turn calls the Anthropic SDK and tool
# dispatch functions synchronously (yfinance, requests, pymongo are all
# blocking), so this runs in FastAPI's threadpool rather than blocking
# the event loop. See CLAUDE.md "Backend" conventions.
@router.post("/chat")
def chat(request: ChatRequest):
    def event_stream():
        try:
            messages = [m.model_dump() for m in request.messages]
            for event in run_agent_turn(messages):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Sync: ingest_filing fetches from SEC and calls Pinecone, both blocking.
# Triggered by the upload button next to each filing in the Overview page's
# "Recent SEC Filings" list, and used internally (via ingest_ticker_filings)
# as the lazy fallback inside the search_filings tool when a ticker's
# namespace is empty - see FilingSearchService's module docstring.
@router.post("/ingest_filing")
def ingest_filing(request: IngestFilingRequest):
    return filing_search_service.ingest_filing(request.ticker, request.model_dump())


# Sync: one Pinecone fetch() call, but still a blocking network call.
# Called by the Overview page right after it loads the filings list, so the
# upload button can render as already-done instead of re-offering it.
@router.get("/filing_status")
def filing_status(ticker: str, accessionNumbers: str = Query(..., description="Comma-separated accession numbers")):
    accession_list = [a for a in accessionNumbers.split(",") if a]
    return filing_search_service.get_indexed_status(ticker, accession_list)
