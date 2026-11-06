# Intent: Persist chat conversations to MongoDB

See [docs/specs/persist-chat-history-spec.md](../specs/persist-chat-history-spec.md) for the Design-stage spec this intent was turned into.

## What

Store the chat widget's conversation turns in MongoDB. Today, `agent-chat.tsx`'s history is client-side React state only — nothing is written server-side, and a page refresh loses it (CLAUDE.md Gotchas calls this "a deliberate v1 simplification, not an oversight").

## Why

- **Immediate:** conversations currently can't survive a refresh or be looked back on later.
- **Strategic:** this is the prerequisite for the self-improvement / lesson-store idea discussed earlier (Reflexion-style: capture lessons from live groundedness-judge and reflection verdicts, not just the static eval set). That loop needs something to read from. This feature is the storage layer only — it does not build the lesson extraction itself.

## Constraints

- Single-user app (`ALLOWED_USER_EMAIL`) — no multi-tenant isolation, but every write/read still goes through `require_auth` like any other endpoint.
- `run_agent_turn()` stays a stateless generator — persistence wraps around it (in the router or a thin service), not inside `loop.py`'s harness.
- Mongo access only via `db.get_db()` — no new `MongoClient` (CLAUDE.md convention).
- Must not change the SSE streaming contract or break the Stop-button abort behavior (CLAUDE.md Gotchas) — writing to Mongo must not block or visibly slow the stream.
- Should capture the per-turn metadata already generated and currently thrown away after the stream ends: tool calls made, the groundedness verdict (`confidence_score`, `flagged_claims`), the reflection critique/revision if requested, and `context_compacted` events — this is what makes the stored data actually useful later, not just a transcript.
- No heavy new dependency, no change to the Vercel function's size budget.

## Explicitly out of scope for this feature

- The lesson-extraction / self-improve loop itself.
- Multi-device sync, multi-user isolation beyond the existing single-`ALLOWED_USER_EMAIL` auth — not meaningful for a single-user app.
- Any retention/TTL policy or redaction — explicitly decided against below.

## Decisions (answered during the Plan stage)

1. **Schema shape:** one growing document per conversation — a session, not a per-turn log. No TTL/retention policy. Instead, session boundaries are explicit and user-driven, the same way Claude's own chat UI works: a "New chat" action starts a fresh session/document; there's no background expiry deciding when a conversation "ends."
2. **Frontend impact — bigger than originally assumed.** This is **not** backend-silent logging. The chat widget needs:
   - A **"New chat"** action that starts a new session (new Mongo document, cleared transcript).
   - A **sidebar listing previous sessions** (most recent first — needs some title/preview per session, e.g. first user message or an LLM-free truncation).
   - The ability to **click a past session and resume it** — load its full stored transcript back into the widget and continue from there (new turns append to that same document).
3. **Write path:** fire-and-forget. Persisting a turn must never block or slow the SSE stream the user is watching.
4. **Privacy/retention:** no special policy needed — single user, no redaction, no TTL.
