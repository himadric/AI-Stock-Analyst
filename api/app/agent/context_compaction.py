"""
Conversation context compaction - summarizes the older portion of a long
chat history so it doesn't keep growing unbounded. The chat widget's
history is client-side only and resent in full every turn (see CLAUDE.md
Gotchas); this is also the same text-only-history limitation named there
as the suspected root of an earlier observed hallucination/false-self-
correction incident.

A real finding from testing before this was built, not assumed: a
synthetic {"role": "user", "content": "Earlier conversation summary: ..."}
message spliced into the messages array is actively distrusted by the
model - a live test produced "I don't actually have access to previous
conversations... each conversation starts fresh," i.e. the model flagged
the fake summary as an unverified claim rather than real history. The
exact same summary placed in the SYSTEM PROMPT instead was accepted
naturally in a side-by-side test (the model referenced "our previous
exchange" with no skepticism). System content reads as developer-provided
context; a user-role message reads as an assertion the model is right to
question. That's why summarize_context() just returns text for loop.py to
append to its system prompt, rather than returning a fake message.
"""
import os

# Not imported from loop.py - same circular-import reasoning
# reflection.py's MODEL constant already documents (loop.py imports this
# module, so this module importing back from loop.py would be circular).
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

SUMMARIZE_SYSTEM_PROMPT = """You summarize an earlier portion of a conversation between a user and a stock \
research AI assistant, so the assistant can keep track of what's already been established without re-reading \
the full history. Write a short bullet list of concrete facts only - not a narrative paragraph. Include: \
tickers discussed, specific numbers already given and what they were (e.g. "AAPL price quoted as $339.50"), \
conclusions reached, and any open questions the user raised but didn't get answered. Omit pleasantries and \
anything not useful for continuing the conversation accurately. Keep it concise."""


def summarize_context(messages: list[dict]) -> str | None:
    """
    One-shot Haiku call over the given (older) messages. Returns a
    structured bullet-point summary, or None on any failure - the caller
    skips compaction entirely in that case and the turn proceeds with the
    full, uncompacted history, same as if this function didn't exist.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not messages:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        # messages is already valid {"role", "content"} dicts straight out
        # of run_agent_turn's own `conversation` list - passed through
        # as-is as the transcript to summarize, wrapped in one instruction.
        transcript = "\n\n".join(
            f"{m['role'].upper()}: {m['content'] if isinstance(m['content'], str) else '[tool call/result]'}"
            for m in messages
        )
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SUMMARIZE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": transcript}],
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        return text.strip() or None
    except Exception as e:
        print(f"[context_compaction] failed: {type(e).__name__}: {e}")
        return None
