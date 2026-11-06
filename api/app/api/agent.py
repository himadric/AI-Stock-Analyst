import json
import os
from typing import Any, List, Literal, Union

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.loop import run_agent_turn
from app.agent.multi_agent import run_multi_agent_analysis
from app.agent.injection_lab import run_injection_demo
from app.agent.tools import filing_search_service
from app.services.chat_session_service import chat_session_service

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
    # Opt-in self-critique pass (see agent/reflection.py) - off by default,
    # since it roughly doubles Sonnet usage for the turn.
    reflect: bool = False
    # None means "create a new session on this turn" - see
    # chat_session_service.py and docs/plans/persist-chat-history-plan.md.
    # Omitted entirely by evals/run_evals.py's direct POSTs, which is fine:
    # it just means those turns aren't persisted.
    session_id: str | None = None


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


def _new_accumulator() -> dict:
    """Fresh per-turn accumulator for _accumulate() - see its docstring."""
    return {
        "text": "",
        "tool_calls": [],
        "citations": [],
        "usage": None,
        "context_compacted": None,
        "reflection": None,
        "groundedness": None,
    }


def _accumulate(acc: dict, event: dict) -> None:
    """
    Mirrors exactly what agent-chat.tsx's updateLast() does client-side per
    SSE event type, so the Mongo-persisted turn matches what the user
    actually saw - including folding an `error` event into the same
    accumulated text field the frontend renders it into (so a turn that
    errors mid-stream persists the same content, not a truncated or
    diverging version).
    """
    event_type = event.get("type")

    if event_type == "text":
        acc["text"] += event.get("text", "")
    elif event_type == "error":
        message = event.get("message", "")
        if acc["text"]:
            acc["text"] += f"\n\n⚠️ {message}"
        else:
            acc["text"] = f"⚠️ {message}"
    elif event_type == "tool_start":
        acc["tool_calls"].append({"tool": event.get("tool"), "args": event.get("args"), "status": "running"})
    elif event_type == "tool_end":
        tool_name = event.get("tool")
        # Most recent first - a tool can be called more than once per turn,
        # and tool_end carries no other identifier to disambiguate which
        # call it's closing out.
        for entry in reversed(acc["tool_calls"]):
            if entry["tool"] == tool_name and entry["status"] == "running":
                entry["status"] = "done"
                break
    elif event_type == "citation":
        acc["citations"].append({
            "cited_text": event.get("cited_text"),
            "source": event.get("source"),
            "title": event.get("title"),
        })
    elif event_type == "usage":
        if acc["usage"] is None:
            acc["usage"] = {"cache_created": 0, "cache_read": 0}
        acc["usage"]["cache_created"] += event.get("cache_creation_input_tokens") or 0
        acc["usage"]["cache_read"] += event.get("cache_read_input_tokens") or 0
    elif event_type == "context_compacted":
        acc["context_compacted"] = event.get("messages_summarized")
    elif event_type == "reflection":
        acc["reflection"] = {
            "needs_revision": event.get("needs_revision"),
            "critique": event.get("critique"),
            "revised_answer": event.get("revised_answer"),
        }
    elif event_type == "groundedness":
        acc["groundedness"] = {
            "confidence_score": event.get("confidence_score"),
            "verdict": event.get("verdict"),
            "flagged_claims": event.get("flagged_claims"),
            "reasoning": event.get("reasoning"),
        }
    # Other event types (watchlist_proposal, trade_proposal, session_created,
    # done) don't contribute to the stored assistant entry.


def _build_assistant_entry(acc: dict) -> dict:
    """
    Builds the dict persisted as the turn's assistant message. Optional
    keys are included only if that kind of event actually fired this turn -
    never stored as null/empty for a key that never fired.
    """
    entry: dict = {"role": "assistant", "content": acc["text"]}
    if acc["tool_calls"]:
        entry["tool_calls"] = acc["tool_calls"]
    if acc["citations"]:
        entry["citations"] = acc["citations"]
    if acc["usage"] is not None:
        entry["usage"] = acc["usage"]
    if acc["context_compacted"] is not None:
        entry["context_compacted"] = acc["context_compacted"]
    if acc["reflection"] is not None:
        entry["reflection"] = acc["reflection"]
    if acc["groundedness"] is not None:
        entry["groundedness"] = acc["groundedness"]
    return entry


# Sync (not async def): run_agent_turn calls the Anthropic SDK and tool
# dispatch functions synchronously (yfinance, requests, pymongo are all
# blocking), so this runs in FastAPI's threadpool rather than blocking
# the event loop. See CLAUDE.md "Backend" conventions.
@router.post("/chat")
def chat(request: ChatRequest):
    messages = [m.model_dump() for m in request.messages]

    # New-session creation happens synchronously, before the generator is
    # even constructed, since the frontend needs the real id up front (via
    # the session_created event below) - a Mongo hiccup here degrades to
    # "this turn isn't saved," never to "chat is broken."
    session_id = request.session_id
    is_new_session = session_id is None
    if is_new_session:
        try:
            session_id = chat_session_service.create_session(messages[-1]["content"]) if messages else None
        except Exception as e:
            print(f"Failed to create chat session: {e}")
            session_id = None
        is_new_session = session_id is not None

    def event_stream():
        acc = _new_accumulator()
        try:
            if is_new_session:
                yield f"data: {json.dumps({'type': 'session_created', 'session_id': session_id})}\n\n"
            for event in run_agent_turn(messages, reflect=request.reflect):
                _accumulate(acc, event)
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            _accumulate(acc, error_event)
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
            # Runs on normal completion, on the except branch above, AND on
            # GeneratorExit (the client aborting via the Stop button) - see
            # docs/plans/persist-chat-history-plan.md's Context section for
            # why this is a finally, not a StreamingResponse background
            # task. Never allowed to raise into the stream.
            if session_id and messages:
                try:
                    chat_session_service.append_turn(
                        session_id,
                        user_entry={"role": "user", "content": messages[-1]["content"]},
                        assistant_entry=_build_assistant_entry(acc),
                    )
                except Exception as e:
                    print(f"Failed to persist chat turn for session {session_id}: {e}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Sync: simple pymongo reads/writes via ChatSessionService - see
# chat_session_service.py's module docstring for the persistence design.
@router.get("/sessions")
def list_chat_sessions():
    return chat_session_service.list_sessions()


@router.get("/sessions/{session_id}")
def get_chat_session(session_id: str):
    session = chat_session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404)
    return session


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: str):
    if not chat_session_service.delete_session(session_id):
        raise HTTPException(status_code=404)
    return {"ok": True}


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


# Feature flag, not an API key gate like YOUTUBE_API_KEY/FRED_API_KEY (this
# costs real Anthropic tokens per run but needs no credential of its own) -
# lets the lab be turned off without a code change. Defaults to enabled so
# existing deployments that haven't set this var keep today's behavior.
# ENABLE_INJECTION_LAB (here) and NEXT_PUBLIC_ENABLE_INJECTION_LAB (frontend,
# dashboard-layout.tsx + injection-lab/page.tsx) are two separate env vars,
# same "keep both sides in sync" pattern as AUTH_SECRET/ALLOWED_USER_EMAIL -
# flipping only one hides the page but leaves the endpoint reachable, or
# vice versa, so set both the same way.
def _injection_lab_enabled() -> bool:
    return os.getenv("ENABLE_INJECTION_LAB", "true").lower() != "false"


# Sync, same reasoning as /chat above. Backs the Prompt Injection Lab page
# (see agent/injection_lab.py's module docstring) - a dedicated demo action,
# not a tool the main chat agent can call, and never dispatches any real
# tool regardless of what the model does in response.
@router.post("/injection_demo")
def injection_demo(request: InjectionDemoRequest):
    if not _injection_lab_enabled():
        # 404, not 403: when the flag is off, the feature should look like
        # it doesn't exist, not like it exists but is forbidden.
        raise HTTPException(status_code=404)

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
