"""
Multi-agent stock research - a sibling flow to loop.py's run_agent_turn,
not a tool inside it. Deliberately NOT modeled as one more entry in
TOOL_DISPATCH: dispatch() is a simple synchronous call-and-return that 29+
tools rely on, and this needs to stream nested progress (one tool trace per
subagent, running concurrently) during a single "call" - forcing that
through dispatch()'s contract would complicate every other tool's calling
convention to serve this one unusual case. Triggered by a dedicated UI
action (see POST /api/agent/multi_analysis), not picked by the main agent
mid-conversation.

Four fixed personas, each a focused mini tool-loop over a filtered slice of
the normal tool registry, run concurrently in threads (this app is sync
throughout - yfinance, the Anthropic SDK's sync client, MCP's anyio.run()
bridge - so threads, not asyncio, matches everything else here). A
coordinator call synthesizes all four reports into the final answer.
"""
import os
import queue
import threading

from app.agent.tools import TOOLS, dispatch
from app.agent import mcp_client

MODEL = "claude-sonnet-5-5"
MAX_TOOL_TURNS = 6  # lower than the main loop's 8 - each subagent's job is narrower
# 1024 turned out too low: a live test showed the fundamentals persona batching 6 tool
# calls into one turn, then its next turn hit stop_reason="max_tokens" with ALL 1024
# tokens consumed by invisible thinking tokens and zero visible text - an empty report
# despite the research having gone fine. 2048 matches the main loop's budget; the
# fallback below is still the real safety net regardless of the number chosen here.
MAX_TOKENS = 2048

_ALL_TOOL_NAMES = {t["name"] for t in TOOLS}


def _tools_for(names: list[str]) -> list[dict]:
    wanted = set(names)
    missing = wanted - _ALL_TOOL_NAMES
    if missing:
        raise ValueError(f"Unknown tool name(s) in persona definition: {missing}")
    return [t for t in TOOLS if t["name"] in wanted]


PERSONAS = [
    {
        "id": "fundamentals",
        "label": "Fundamentals & Valuation",
        "tool_names": [
            "get_company_info", "get_quarterly_financials", "get_quarterly_ratios",
            "get_forecast", "get_analyst_actions", "get_peer_comparison",
            "get_future_leader_score", "run_dcf_simulation",
        ],
        "system_prompt": (
            "You are a fundamentals and valuation specialist researching one ticker for a stock "
            "research dashboard. Use your tools to assess the company's financial health, growth, "
            "profitability, and whether its current valuation looks rich or cheap relative to its "
            "own history and fundamentals. Write a focused analysis (3-5 short paragraphs) covering "
            "what you found and your read on valuation specifically from a fundamentals angle. This "
            "is one of four independent analyst reports that a coordinator will synthesize - stay "
            "in your lane; don't try to cover sentiment, institutional activity, or filings. "
            "Informational only, not investment advice."
        ),
    },
    {
        "id": "smart_money",
        "label": "Smart-Money & Institutional",
        "tool_names": [
            "get_congress_trades", "get_vanguard_trades", "get_munro_trades",
            "find_smart_money_convergence", "get_ownership_details",
        ],
        "system_prompt": (
            "You are a smart-money and institutional-activity specialist researching one ticker. "
            "Use your tools to check whether Congress, Vanguard, or Munro Partners have recently "
            "traded this name, and whether institutional/insider ownership patterns say anything "
            "notable. Write a focused analysis (3-5 short paragraphs) on what independent sources "
            "of informed money are doing with this stock, if anything. If you find nothing notable, "
            "say so plainly rather than stretching for a signal. This is one of four independent "
            "analyst reports that a coordinator will synthesize - stay in your lane; don't try to "
            "cover fundamentals, sentiment, or filings. Informational only, not investment advice."
        ),
    },
    {
        "id": "sentiment",
        "label": "Sentiment & News",
        "tool_names": ["get_company_news", "get_brand_sentiment"],
        "include_mcp_tools": True,  # the only persona with a real use for general web search
        "system_prompt": (
            "You are a sentiment and news specialist researching one ticker. Use your tools - "
            "including web search if you have it - to assess recent news, brand sentiment, and "
            "anything currently driving the narrative around this company. Write a focused analysis "
            "(3-5 short paragraphs) on the current sentiment picture and any recent news that matters. "
            "This is one of four independent analyst reports that a coordinator will synthesize - "
            "stay in your lane; don't try to cover fundamentals, institutional activity, or filings. "
            "Informational only, not investment advice."
        ),
    },
    {
        "id": "filings",
        "label": "Filings & Risk",
        "tool_names": ["get_filings", "get_filing_text", "search_filings"],
        "system_prompt": (
            "You are a filings and risk specialist researching one ticker. Use your tools to review "
            "this company's recent SEC filings for risk factors, notable disclosures, or anything a "
            "careful reader of the filings would flag. search_filings is semantic search across what's "
            "already indexed - it ingests the most recent filings automatically on first use if nothing "
            "is indexed yet, which is slower than your other tools, so expect it. Write a focused "
            "analysis (3-5 short paragraphs) on what the filings reveal. This is one of four independent "
            "analyst reports that a coordinator will synthesize - stay in your lane; don't try to cover "
            "fundamentals, institutional activity, or sentiment. Informational only, not investment advice."
        ),
    },
]

COORDINATOR_SYSTEM_PROMPT = """You are the coordinator for a team of four specialist stock analysts \
(fundamentals, smart-money/institutional, sentiment/news, filings/risk) who have each independently \
researched the same ticker and written their own report. Your job is to synthesize their four reports \
into one cohesive answer for the user - not just concatenate them. Note where the angles agree or \
reinforce each other, and flag it plainly if they point in different directions. Keep it readable: use \
the four angles as structure, but write it as one coherent piece, not four pasted-together sections. \
This is informational analysis, not investment advice, and you have no ability to place trades."""


def _get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None, "The analyst agent isn't configured (missing ANTHROPIC_API_KEY on the server)."
    try:
        import anthropic
    except ImportError:
        return None, "The analyst agent's dependency (anthropic) isn't installed."
    return anthropic.Anthropic(api_key=api_key), None


def _run_subagent(ticker: str, persona: dict, event_queue: "queue.Queue"):
    """
    Runs one persona's bounded tool-loop, pushing its events onto the shared
    queue as they happen (not returning them - this runs in its own thread,
    concurrently with the other personas). Always pushes exactly one
    agent_done as its last event, even on error, so the merging generator's
    completion count stays correct no matter what happens in here.
    """
    agent_id = persona["id"]
    try:
        client, error = _get_client()
        if error:
            event_queue.put({"type": "agent_done", "agent_id": agent_id, "full_report": f"(unavailable: {error})"})
            return

        tools = _tools_for(persona["tool_names"])
        if persona.get("include_mcp_tools"):
            tools = tools + mcp_client.discover_tools()
        conversation = [{"role": "user", "content": f"Research {ticker} from your assigned angle."}]
        report_text = ""

        needs_fallback = True  # cleared below the moment we get a real final answer
        for _turn in range(MAX_TOOL_TURNS):
            # A turn boundary, not a mid-sentence continuation - without this,
            # one turn's trailing fragment (e.g. "Let me check the filings.")
            # runs directly into the next turn's opening line with no space.
            if report_text and not report_text.endswith("\n"):
                report_text += "\n\n"
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=persona["system_prompt"],
                tools=tools,
                messages=conversation,
            ) as stream:
                for event in stream:
                    if event.type == "text":
                        report_text += event.text
                final_message = stream.get_final_message()

            conversation.append({"role": "assistant", "content": final_message.content})

            if final_message.stop_reason != "tool_use":
                # A real finish - but only a *good* one if it actually produced
                # visible text. A live test hit stop_reason="max_tokens" with
                # zero text (the whole budget spent on invisible thinking
                # tokens after a turn that batched 6 tool calls at once) -
                # that's not a finish worth trusting, so it still falls
                # through to the fallback below rather than shipping an
                # empty report.
                if report_text.strip():
                    needs_fallback = False
                break

            tool_results = []
            for block in final_message.content:
                if block.type != "tool_use":
                    continue
                event_queue.put({"type": "agent_tool_start", "agent_id": agent_id, "tool": block.name, "args": block.input})
                result_text = dispatch(block.name, block.input or {})
                event_queue.put({"type": "agent_tool_end", "agent_id": agent_id, "tool": block.name})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result_text})
            conversation.append({"role": "user", "content": tool_results})

        if needs_fallback:
            # Either MAX_TOOL_TURNS ran out mid-research, or a turn ended
            # without producing visible text (see the max_tokens/thinking-
            # tokens case above). Either way, force one more, tool-free call
            # asking it to write up whatever it already gathered, rather than
            # let the report come back empty.
            conversation.append({
                "role": "user",
                "content": "Write up your findings now from what you've already gathered above - "
                            "don't call any more tools.",
            })
            if report_text and not report_text.endswith("\n"):
                report_text += "\n\n"
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=persona["system_prompt"],
                messages=conversation,
            ) as stream:
                for event in stream:
                    if event.type == "text":
                        report_text += event.text
                stream.get_final_message()

        event_queue.put({
            "type": "agent_done",
            "agent_id": agent_id,
            "full_report": report_text or "(no findings)",
        })
    except Exception as e:
        event_queue.put({"type": "agent_done", "agent_id": agent_id, "full_report": f"(error: {e})"})


def run_multi_agent_analysis(ticker: str):
    """
    Yields events for POST /api/agent/multi_analysis's SSE stream:
      {"type": "agent_start", "agent_id": ..., "label": ...}
      {"type": "agent_tool_start", "agent_id": ..., "tool": ..., "args": {...}}
      {"type": "agent_tool_end", "agent_id": ..., "tool": ...}
      {"type": "agent_done", "agent_id": ..., "full_report": "..."}
      {"type": "text", "text": "..."}          (coordinator narration + final synthesis)
      {"type": "error", "message": "..."}
      {"type": "done"}
    """
    client, error = _get_client()
    if error:
        yield {"type": "error", "message": error}
        return

    yield {"type": "text", "text": f"Dispatching {len(PERSONAS)} research agents for {ticker.upper()}...\n\n"}

    event_queue: "queue.Queue" = queue.Queue()
    threads = []
    for persona in PERSONAS:
        yield {"type": "agent_start", "agent_id": persona["id"], "label": persona["label"]}
        t = threading.Thread(target=_run_subagent, args=(ticker, persona, event_queue), daemon=True)
        t.start()
        threads.append(t)

    reports = {}
    done_count = 0
    while done_count < len(PERSONAS):
        event = event_queue.get()
        if event["type"] == "agent_done":
            reports[event["agent_id"]] = event["full_report"]
            done_count += 1
        yield event

    for t in threads:
        t.join()

    yield {"type": "text", "text": "\n\nSynthesizing findings across all four angles...\n\n---\n\n"}

    report_block = "\n\n".join(
        f"## {p['label']}\n{reports.get(p['id'], '(no report)')}" for p in PERSONAS
    )
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS * 2,
            system=COORDINATOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Ticker: {ticker.upper()}\n\n{report_block}"}],
        ) as stream:
            for event in stream:
                if event.type == "text":
                    yield {"type": "text", "text": event.text}
    except Exception as e:
        yield {"type": "error", "message": f"Coordinator synthesis failed: {e}"}
        return

    yield {"type": "done"}
