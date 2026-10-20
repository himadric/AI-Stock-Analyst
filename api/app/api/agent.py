import json
from typing import Any, List, Literal, Union

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.loop import run_agent_turn
from app.agent.multi_agent import run_multi_agent_analysis
from app.agent.injection_lab import run_injection_demo
from app.agent.tools import filing_search_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    # Usually a plain string. For a message with a pasted image, the
    # frontend sends Anthropic content blocks instead (text + image)
    # - run_agent_turn passes content straight through to the Anthropic
    # SDK unchanged either way, so no change was needed there.
    content: Union[str, List[dict[str, Any]]]


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class MultiAnalysisRequest(BaseModel):
    ticker: str
    chart_image: str | None = None  # base64 PNG, optionally a data: URL - see multi_agent.py


class InjectionDemoRequest(BaseModel):
    scenario: Literal["filing_summary", "web_research"]
    defenses_on: bool


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


# Sync, same reasoning as /chat above. A dedicated action (see agent-chat.tsx's
# "Run full multi-agent analysis" button) - not a tool the main chat agent can
# call mid-conversation. See agent/multi_agent.py's module docstring for why.
@router.post("/multi_analysis")
def multi_analysis(request: MultiAnalysisRequest):
    image_b64 = request.chart_image
    if image_b64 and image_b64.startswith("data:"):
        # Same stripping as /ai/analyze_chart - Anthropic's inline image
        # source wants raw base64, not a data: URL prefix.
        image_b64 = image_b64.split(",", 1)[-1]

    def event_stream():
        try:
            for event in run_multi_agent_analysis(request.ticker, image_b64=image_b64):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Sync, same reasoning as /chat above. Backs the Prompt Injection Lab page
# (see agent/injection_lab.py's module docstring) - a dedicated demo action,
# not a tool the main chat agent can call, and never dispatches any real
# tool regardless of what the model does in response.
@router.post("/injection_demo")
def injection_demo(request: InjectionDemoRequest):
    def event_stream():
        try:
            for event in run_injection_demo(request.scenario, request.defenses_on):
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
