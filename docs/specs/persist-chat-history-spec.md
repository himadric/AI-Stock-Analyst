# Spec: Persist chat conversations to MongoDB

Design-stage counterpart to [docs/intents/persist-chat-history-intent.md](../intents/persist-chat-history-intent.md) (Plan stage). This is the version-controlled design spec for the feature, per the AI-Native SDLC Playbook's Plan → Design → Build → Test → Deploy → Maintain framework — written and reviewable before any implementation diff exists.

## Problem

The chat widget's history is entirely client-side (`agent-chat.tsx`'s `messages` React state) — nothing is persisted, and a page refresh loses everything. This is also a blocker for a planned follow-up (a Reflexion-style self-improve loop that would learn from live groundedness/reflection signals), which needs something durable to read from. This feature is the storage layer only — it does not build that loop.

## Scope

- Main chat (`POST /api/agent/chat`) only. `multi_agent.py`'s `/multi_analysis` flow is explicitly out of scope and stays unsaved — consistent with context compaction and reflection already being "main chat only" features.
- One growing Mongo document per session. No TTL/retention policy — sessions are explicit, user-driven boundaries (a "New chat" action), not time-expired, mirroring how Claude's own chat UI works.
- A sidebar (in practice, an in-widget overlay — see Frontend design) listing previous sessions, resumable.
- No privacy/redaction policy — single-user app (`ALLOWED_USER_EMAIL`), no multi-tenant concern.

## Backend design

### Data model — new Mongo collection `chat_sessions`

```python
{
  "_id": ObjectId,
  "title": str,          # from the first user message, truncated ~60 chars, set once at creation, never regenerated
  "messages": [
    {"role": "user", "content": str | list[dict], "created_at": datetime},
    {
      "role": "assistant", "content": str, "created_at": datetime,
      # all optional, omitted entirely when not produced that turn:
      "tool_calls": [{"tool": str, "args": dict, "status": "running"|"done"}],
      "citations": [{"cited_text": str, "source": str|None, "title": str|None}],
      "usage": {"cache_created": int, "cache_read": int},
      "context_compacted": int,
      "reflection": {"needs_revision": bool, "critique": str, "revised_answer": str|None},
      "groundedness": {"confidence_score": float, "verdict": str, "flagged_claims": list, "reasoning": str},
    },
  ],
  "created_at": datetime,
  "updated_at": datetime,   # bumped on every appended turn
}
```

A pasted image's base64 is **never stored** — a user content block with `{"type": "image", ...}` has its `source.data` replaced with a placeholder string before persisting, keeping a never-expiring, ever-growing document bounded. Tool-call entries only ever carry `{tool, args, status}`, never result text, so there's no other large payload at risk of bloating a document toward BSON's 16MB cap.

No `user_id` field — consistent with every existing collection in this app (single-user, no multi-tenant convention anywhere).

### Service: `api/app/services/chat_session_service.py`

New `ChatSessionService`, following `PortfolioService`'s shape (plain class, `_serialize` helper converting `_id`→`id` and re-attaching UTC tzinfo to naive datetimes — pymongo returns naive datetimes since BSON strips tzinfo, and the fix is the same one already applied once in `watchlist.py`'s `get_watchlist_report()`):

- `create_session(first_user_content) -> str`
- `append_turn(session_id, user_entry, assistant_entry) -> None`
- `list_sessions() -> list[dict]` — projects `{title, created_at, updated_at}` only, excludes `messages`, sorted `updated_at` desc
- `get_session(session_id) -> dict | None`
- `delete_session(session_id) -> bool`

This logic lives in a service, not inline in a router, because it needs to be called from inside `agent.py`'s own request-handling path — importing a sibling router module from there would risk the exact circular import `portfolio_service.py`'s own docstring already documents and avoids (`app/api/__init__.py` → `agent.py` → ...).

### Persist mechanism — synchronous, in a `finally` block (not a background task)

The turn's Mongo write happens inside a `try/finally` wrapped around the existing SSE generator in `/chat`'s handler, not via Starlette's `background=BackgroundTask(...)` hook on `StreamingResponse`. Rationale:

1. **Serverless reliability.** This app deploys as a Vercel Python serverless function. Whether Vercel's runtime keeps a function alive long enough to finish work scheduled *after* the HTTP response closes is unverified, and is a known rough edge on Lambda-style runtimes generally. A write inside the handler's own `finally` runs within the function's normal, guaranteed execution lifetime — the same lifecycle every other endpoint in this app already relies on.
2. **Abort correctness.** A generator's `finally` runs on `GeneratorExit` too (triggered when the client aborts the fetch via the Stop button), so a turn stopped early still gets its partial answer persisted. The background-task hook would silently skip persistence in exactly that case, since the response never completes normally.
3. **No visible cost.** The write only happens after every visible text/tool event has already reached the client — it adds a small, bounded delay before the stream's terminal chunk closes (i.e., before the frontend's `loading` indicator clears), not to anything the user is actively watching render.

`run_agent_turn()`'s `"done"` event is *not* guaranteed on every exit path (an early failure — e.g. missing API key — `return`s right after an `error` yield, with no trailing `done`), so the persist hook is structural (the `finally` itself), never keyed off observing a specific event type.

### API changes (`api/app/api/agent.py`)

- `ChatRequest` gains `session_id: str | None = None`. `None` means "create a new session on this turn."
- New `_accumulate(acc, event)` / `_build_assistant_entry(acc)` helpers mirror exactly what `agent-chat.tsx`'s `updateLast()` already does client-side per SSE event type — including folding an `error` event into the accumulated text the same way the frontend renders it (`⚠️ {message}`), so a turn that errors mid-stream persists the same content the user actually saw, not a truncated or diverging version.
- `chat()`: if `session_id` is absent, `create_session()` is called synchronously before the stream starts (wrapped in `try/except` — any failure degrades to "this turn isn't saved," never to "chat is broken"); the stream's first event is a new `{"type": "session_created", "session_id": ...}` when a session was just created, so the frontend learns the real id without an extra round trip.
- Three new routes on the existing `agent.py` router (inherit the `/agent` prefix and `dependencies=protected` auth automatically — no new router registration needed):
  - `GET /agent/sessions` — list, sorted most-recent-first.
  - `GET /agent/sessions/{session_id}` — full transcript, `404` if missing (CLAUDE.md's single-entity-lookup convention).
  - `DELETE /agent/sessions/{session_id}` — `404` if missing, else `{"ok": true}`.

## Frontend design (`src/lib/api.ts`, `src/components/dashboard/agent-chat.tsx`)

`stock-analyst-assistant.tsx` is **not** modified. A real side-by-side sidebar column would require that file's drag-resize math to split one panel width between two children, which it isn't built for, and nothing here needs simultaneous visibility of transcript + list. Instead, the session list is an overlay rendered inside `AgentChat`'s own existing root element, covering the area below a new slim toolbar when open.

- `lib/api.ts`: `AgentEvent` gains `{ type: "session_created"; session_id: string }`; `streamAgentChat(...)` gains an optional `sessionId` parameter sent as `session_id` in the request body; new `ChatSessionSummary`/`StoredChatMessage`/`ChatSessionDetail` types and `getChatSessions()`/`getChatSession(id)`/`deleteChatSession(id)` functions, following the existing `getPortfolio()`-style typed non-streaming fetch pattern.
- `agent-chat.tsx`: new `sessionId`/`sessions`/`sidebarOpen` state; a toolbar row (History + New-chat icon buttons) as the first child of the root element; an overlay panel listing sessions, click-to-resume, with per-row delete; `newChat()` is a pure local state reset with **no backend call** (a session is created lazily, only once the first message of that chat is actually sent — matching the reference UX of Claude's own "+ New chat").

## Out of scope (explicitly)

- The lesson-extraction / self-improve loop this unblocks.
- `multi_agent.py` / `/multi_analysis` persistence.
- Multi-device sync, retention policy, redaction.

## Verification plan

See the implementation plan's Verification section (`~/.claude/plans/adaptive-cooking-starlight.md` at time of writing) for the full checklist: new-session creation, append-to-existing-session, list/get/delete, image stripping, the abort-persists-partial-answer case, frontend state isolation (new chat clears without a network call, resuming repopulates all metadata correctly), and a real preview-deployment check of the synchronous persist path under Vercel's serverless runtime.
