"""
Reflection / self-critique loop - a second, independent technique from
groundedness_judge.py's LLM-as-judge, not a duplicate of it. The judge is a
DIFFERENT, cheaper model (Haiku) checking fact-consistency against source
data - a narrow check that deliberately doesn't need Sonnet-level capability.
Reflection is the SAME model (Sonnet) critiquing its own draft and, if it
finds a real gap, rewriting it - which does need that capability, since a
weaker model can't meaningfully critique reasoning it couldn't have produced
itself. It's also the one of the two that can actually fix a problem, not
just flag it.

Opt-in (see loop.py's `reflect` parameter), not automatic like the judge is:
this roughly doubles Sonnet usage for a turn (a critique call, plus a full
answer regeneration when something's found), so it's a per-conversation
toggle the user controls (agent-chat.tsx), not a standing cost on every
message.

Deliberately given the user's original question, unlike the judge - the
judge's job is narrow fact-consistency (doesn't need to know what was
asked); reflection's job is broader (did this actually address the
question, is it complete), which requires knowing the question. This split
keeps each function's scope honest rather than overlapping.
"""
import os

# Not imported from loop.py - that would be a circular import (loop.py
# imports reflect_on_answer from this module). Duplicated instead, same
# pattern multi_agent.py and injection_lab.py already use for their own
# MODEL constants rather than importing loop.py's.
MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 2048

SELF_CRITIQUE_TOOL = {
    "name": "self_critique",
    "description": "Report whether a draft answer needs revision, and provide the revised answer if so.",
    "input_schema": {
        "type": "object",
        "properties": {
            "needs_revision": {"type": "boolean"},
            "critique": {
                "type": "string",
                "description": "What, if anything, is incomplete, wrong, or unclear. If needs_revision is false, briefly say why the draft already holds up.",
            },
            "revised_answer": {
                "type": "string",
                "description": "The complete improved answer, same voice/format as the draft. Required if needs_revision is true, omitted otherwise.",
            },
        },
        "required": ["needs_revision", "critique"],
    },
}

REFLECTION_SYSTEM_PROMPT = """You are reviewing your own draft answer before it reaches the user. You'll be given \
the user's question, your draft, and the raw data you had available. Critique it: is anything incomplete, wrong, \
unsupported by the data, or confusingly explained? Don't nitpick style - only flag substantive issues. If the \
draft genuinely holds up, say so and set needs_revision to false. If not, write a complete revised answer that \
fixes the issue, in the same voice and format as the draft.

Call self_critique with your assessment."""


def _build_user_message(user_question: str, draft_answer: str, source_context: str) -> str:
    parts = [f"<user_question>\n{user_question}\n</user_question>" if user_question.strip() else ""]
    parts.append(f"<draft_answer>\n{draft_answer}\n</draft_answer>")
    if source_context.strip():
        parts.append(f"<source_data>\n{source_context}\n</source_data>")
    return "\n\n".join(p for p in parts if p)


def reflect_on_answer(user_question: str, draft_answer: str, source_context: str) -> dict | None:
    """
    Returns {"needs_revision", "critique", "revised_answer"?}, or None on
    any failure (missing API key, API error, no tool_use block in the
    response) - the caller skips yielding a reflection event in that case
    and the original draft stands as-is. Must never raise and must never
    block the draft already streamed to the user.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not draft_answer.strip():
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=REFLECTION_SYSTEM_PROMPT,
            tools=[SELF_CRITIQUE_TOOL],
            # Unlike groundedness_judge.py's Haiku call, tool_choice can't be
            # forced here - claude-sonnet-5-5 rejects tool_choice type "tool"
            # and "any" outright (confirmed directly against the API, not
            # assumed). Left at the default "auto" instead: reliable in
            # practice with a single tool offered and a system prompt that
            # explicitly instructs calling it (5/5 in testing) - and the
            # existing "no tool_use block found -> return None" fallback
            # below already covers the rare case where it doesn't comply.
            messages=[{"role": "user", "content": _build_user_message(user_question, draft_answer, source_context)}],
        )
        for block in message.content:
            if block.type == "tool_use" and block.name == "self_critique":
                return block.input
        return None
    except Exception as e:
        print(f"[reflection] failed: {type(e).__name__}: {e}")
        return None
