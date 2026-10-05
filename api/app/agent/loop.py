"""
The conversational analyst agent's tool-use loop (Path A only — see
docs/ARCHITECTURE.md "Conversational analyst agent"). Interactive only:
bounded turns, no scheduled/autonomous runs.

Uses Claude (Anthropic Messages API), not Gemini — a deliberate split
from AIService's one-shot Gemini prompts. Tool-calling loops are a
different shape of problem than "fill in this template," and Claude's
tool-use API is the better fit for it.
"""
import os
from app.agent.tools import TOOLS, dispatch
from app.agent import mcp_client

MODEL = "claude-sonnet-5-5"
MAX_TOOL_TURNS = 8
MAX_TOKENS = 2048

SYSTEM_PROMPT = """You are the research assistant built into AI Analyst, a personal stock/ETF \
research dashboard. You help the user research tickers and think through stock picks using the \
tools available to you — never from memory or guesswork about current prices, financials, or news.

Rules:
- Always use a tool to get current data before stating a number, price, or fact. Don't rely on \
your training data for anything time-sensitive.
- If the user names a company rather than a ticker, use search_tickers first.
- Cite what you found plainly (e.g. "P/E is 28.4" not vague hedging), but be clear this is \
informational analysis, not investment advice, and that you have no ability to place trades.
- You cannot add anything to the watchlist yourself. If you think a ticker is worth adding, \
call propose_watchlist_add — the user will see a confirmation card and decide. Never say you've \
"added" something.
- Keep answers focused. Don't call tools you don't need for the question asked.
- Prefer the specific data tools (price, financials, filings, news, sentiment) over the general web search \
tools for anything about a ticker — they're faster and more precise. Reach for web search only for what \
they genuinely can't cover: breaking news in the last few hours, current macro/Fed/rate questions, or \
anything outside a ticker entirely. If a search result's content is cut short, you can fetch the full page.
- If you hit your research budget before finishing, summarize what you found so far rather than \
leaving the user with nothing.
"""


def run_agent_turn(messages: list[dict]):
    """
    Runs the agent loop for one user turn. Yields plain dicts (JSON-serializable
    events) for the caller to forward over SSE:
      {"type": "text", "text": "..."}
      {"type": "tool_start", "tool": "...", "args": {...}}
      {"type": "tool_end", "tool": "..."}
      {"type": "watchlist_proposal", "ticker": "...", "reason": "..."}
      {"type": "error", "message": "..."}
      {"type": "done"}
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        yield {"type": "error", "message": "The analyst agent isn't configured (missing ANTHROPIC_API_KEY on the server)."}
        return

    try:
        import anthropic
    except ImportError:
        yield {"type": "error", "message": "The analyst agent's dependency (anthropic) isn't installed."}
        return

    client = anthropic.Anthropic(api_key=api_key)
    conversation = [{"role": m["role"], "content": m["content"]} for m in messages]

    # Discovered once per user turn, not re-fetched on every one of the (up
    # to 8) internal tool-call rounds below - mcp_client.discover_tools()
    # caches its result after the first successful call in this process
    # anyway, but there's no reason to even check more than once per turn.
    # Whatever the MCP server exposes right now becomes available to the
    # model, with no per-tool wrapper code on this side - see mcp_client.py.
    all_tools = TOOLS + mcp_client.discover_tools()

    for turn in range(MAX_TOOL_TURNS):
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=all_tools,
                messages=conversation,
            ) as stream:
                for event in stream:
                    if event.type == "text":
                        yield {"type": "text", "text": event.text}
                final_message = stream.get_final_message()
        except Exception as e:
            yield {"type": "error", "message": f"Analyst agent error: {e}"}
            return

        conversation.append({"role": "assistant", "content": final_message.content})

        if final_message.stop_reason != "tool_use":
            yield {"type": "done"}
            return

        tool_results = []
        for block in final_message.content:
            if block.type != "tool_use":
                continue
            yield {"type": "tool_start", "tool": block.name, "args": block.input}
            result_text = dispatch(block.name, block.input or {})
            yield {"type": "tool_end", "tool": block.name}

            if block.name == "propose_watchlist_add":
                ticker = (block.input or {}).get("ticker", "")
                reason = (block.input or {}).get("reason", "")
                yield {"type": "watchlist_proposal", "ticker": ticker.upper(), "reason": reason}

            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result_text})

        conversation.append({"role": "user", "content": tool_results})

    yield {"type": "text", "text": "\n\n_(Hit my research limit for this question — happy to keep going if you narrow it down.)_"}
    yield {"type": "done"}
