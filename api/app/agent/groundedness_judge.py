"""
LLM-as-judge: checks an AI-generated answer against the actual source data
it had access to, and scores how well-grounded it is. Used by both
agent/loop.py's run_agent_turn (checked against the turn's tool results)
and agent/multi_agent.py's coordinator synthesis (checked against the four
subagent reports) - a plain function, not a sibling SSE flow like
multi_agent.py/injection_lab.py, since it has no endpoint of its own and no
streaming of its own; both callers just call it once, inline, after the
real answer is already fully generated.

Deliberately a different, cheaper model (Haiku) than the one being judged
(Sonnet) - this is a second, independent check, not the same model grading
its own homework with the same weights and the same blind spots.

The verdict is forced through a tool call (tool_choice names
GROUNDEDNESS_JUDGE_TOOL explicitly) rather than parsed out of free text -
a reliable, structured score instead of regexing a number out of prose the
model might phrase inconsistently from one call to the next.
"""
import os

JUDGE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

# Cost-conscious, not a hard technical limit (Haiku's context window is far
# larger than this) - same spirit as tools.py's dispatch() 8,000-char cap
# per tool result, just applied to the judge's combined view of everything
# a turn gathered.
MAX_SOURCE_CONTEXT_CHARS = 20_000

GROUNDEDNESS_JUDGE_TOOL = {
    "name": "judge_verdict",
    "description": "Report a groundedness assessment of an AI-generated answer against the source data it was given.",
    "input_schema": {
        "type": "object",
        "properties": {
            "confidence_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "0-100: how well the answer's claims are supported by the source data.",
            },
            "verdict": {"type": "string", "enum": ["grounded", "partially_grounded", "ungrounded"]},
            "flagged_claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "issue": {"type": "string"},
                    },
                    "required": ["claim", "issue"],
                },
                "description": "Specific statements in the answer not supported by the source data. Empty if none.",
            },
            "reasoning": {"type": "string", "description": "One sentence explaining the score."},
        },
        "required": ["confidence_score", "verdict", "flagged_claims", "reasoning"],
    },
}

JUDGE_SYSTEM_PROMPT = """You are a strict fact-checker. You will be given an AI assistant's answer and the \
raw source data it was supposed to base that answer on. Check every factual claim in the answer - \
numbers, prices, dates, names, conclusions - against the source data.

A claim is grounded only if the source data actually supports it. General reasoning, qualitative \
judgment, and disclaimers (e.g. "this is not investment advice") don't need a source citation - only \
check factual claims that could be right or wrong. If the answer says something the source data \
doesn't contain or contradicts, flag it specifically - don't guess whether it's "probably fine."

Call judge_verdict with your assessment."""


def _build_user_message(answer_text: str, source_context: str) -> str:
    if len(source_context) > MAX_SOURCE_CONTEXT_CHARS:
        source_context = source_context[-MAX_SOURCE_CONTEXT_CHARS:]
        source_context = f"[earlier source data truncated]\n...{source_context}"
    return f"<answer>\n{answer_text}\n</answer>\n\n<source_data>\n{source_context}\n</source_data>"


def judge_groundedness(answer_text: str, source_context: str) -> dict | None:
    """
    Returns {"confidence_score", "verdict", "flagged_claims", "reasoning"},
    or None on any failure (missing API key, API error, no tool_use block
    in the response) - callers skip yielding a groundedness event in that
    case rather than surface a broken badge. This must never raise and must
    never block the real answer that was already delivered to the user.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not answer_text.strip() or not source_context.strip():
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=MAX_TOKENS,
            system=JUDGE_SYSTEM_PROMPT,
            tools=[GROUNDEDNESS_JUDGE_TOOL],
            tool_choice={"type": "tool", "name": "judge_verdict"},
            messages=[{"role": "user", "content": _build_user_message(answer_text, source_context)}],
        )
        for block in message.content:
            if block.type == "tool_use" and block.name == "judge_verdict":
                return block.input
        return None
    except Exception as e:
        print(f"[groundedness_judge] failed: {type(e).__name__}: {e}")
        return None
