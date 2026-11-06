# Plan: Persist chat conversations to MongoDB (sessions + resume)

Build-stage plan (AI-Native SDLC Playbook) for this feature. Precedes: [docs/intents/persist-chat-history-intent.md](../intents/persist-chat-history-intent.md) (Plan stage) and [docs/specs/persist-chat-history-spec.md](../specs/persist-chat-history-spec.md) (Design stage — already written and committed as of this plan). This document is the concrete file-by-file implementation plan that was reviewed and approved before any code was written.

## Context

The chat widget's history is entirely client-side (`agent-chat.tsx`'s `messages` React state) — nothing is persisted, and a page refresh loses everything. This was a deliberate v1 simplification (CLAUDE.md Gotchas), but it's now also a blocker for a planned follow-up: a Reflexion-style self-improve loop that would learn from live groundedness/reflection signals, which needs something durable to read from.

This feature is the storage layer only: one growing Mongo document per session, explicit session boundaries (a "New chat" action, like Claude's own UI — no TTL/expiry), a sidebar of previous sessions to resume, and fire-and-forget-*feeling* persistence that never visibly slows the live stream. Scope is the main chat (`POST /api/agent/chat`) only — `multi_agent.py`'s `/multi_analysis` flow stays unsaved, consistent with context compaction and reflection already being "main chat only."

Explored and confirmed before planning: `run_agent_turn()`'s `done` event isn't guaranteed on every exit path (early failures `return` right after an `error` yield with no `done`), so persistence must be structural (a `finally`), not keyed off seeing `done`. Also confirmed: no `user_id`/multi-tenant convention exists on any collection in this app, so chat-session documents need none either; and the one precedent for calling shared logic from inside `agent.py`'s request path (`portfolio_service.py`) exists specifically to avoid a circular import through `app/api/__init__.py` — the same reasoning applies here, so persistence logic must live in a service class, not router-inline code in a different module.

**Persist mechanism, decided:** synchronous, inside a `try/finally` in the `/chat` handler's own SSE generator — not Starlette's `background=BackgroundTask(...)` hook. The write happens only after every visible text/tool event has already reached the client, so there's no visible slowdown, just a small bounded delay before the stream's terminal chunk closes (i.e., before the frontend's `loading` state clears). This was chosen over the true post-response background hook because: (a) this app deploys as a Vercel serverless Python function, and whether Vercel's runtime keeps a function alive long enough to finish work scheduled *after* the response closes is unverified and a known rough edge on Lambda-style runtimes generally; (b) a `finally` also runs on `GeneratorExit` (an aborted/stopped stream), so a turn stopped early via the Stop button still gets its partial answer saved — the background-hook approach would silently lose those.

## Design

### 1. New Mongo collection `chat_sessions` + new service `api/app/services/chat_session_service.py`

One document per session:
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

A pasted image's base64 is **never stored** — a user content block with `{"type": "image", ...}` has its `source.data` replaced with a short placeholder string before persisting, to keep a never-expiring, ever-growing document bounded (tool-call entries only ever carry `{tool, args, status}`, never result text, so there's no other large payload at risk).

`ChatSessionService` (mirrors `PortfolioService`'s shape — plain class, `_serialize` helper doing `_id`→`id` + re-attaching UTC tzinfo to naive datetimes exactly like `watchlist.py`'s `get_watchlist_report()` already had to fix):
- `create_session(first_user_content) -> str` — derives `title` from the content (first ~60 chars of the text, collapsing whitespace; `"Chat with image"` fallback if the first message is image-only), inserts `{title, messages: [], created_at, updated_at}`, returns the new id.
- `append_turn(session_id, user_entry, assistant_entry)` — strips the user entry's image data, stamps both entries' `created_at`, `$push`es both onto `messages` in one `update_one` with `$each`, bumps `updated_at`.
- `list_sessions() -> list[dict]` — projects `{title, created_at, updated_at}` only (excludes `messages` for a cheap list query), sorted `updated_at` desc.
- `get_session(session_id) -> dict | None` — full document, serialized; `None` on a bad/missing id (caught `ObjectId(...)` conversion errors too, not just a missing doc).
- `delete_session(session_id) -> bool`.

### 2. `api/app/api/agent.py` changes

- `ChatRequest` gains `session_id: str | None = None`.
- New helpers `_accumulate(acc, event)` and `_build_assistant_entry(acc)` — mirror exactly what `agent-chat.tsx`'s `updateLast()` already does client-side per event type (`text` concatenates, `error` appends a `⚠️ ...` line to the same text — matching the frontend's own error-rendering exactly, so a turn that errored mid-stream doesn't persist blank/divergent content, `tool_start`/`tool_end` build the tool-call list, `citation`/`usage`/`context_compacted`/`reflection`/`groundedness` set their respective keys). Optional keys are omitted from the built entry when never produced that turn, not stored as `null`.
- `chat()`:
  1. `is_new_session = request.session_id is None`. If new, call `chat_session_service.create_session(messages[-1]["content"])` **before** constructing the generator (needs the id up front) — wrapped in `try/except`: on any failure, log and fall through with `session_id = None`, `is_new_session = False`, so a Mongo hiccup degrades to "this turn isn't saved," never to "chat is broken."
  2. `event_stream()`: if `is_new_session`, yield a new `{"type": "session_created", "session_id": session_id}` event first (so the frontend learns the real id without a second round trip) — the same per-event accumulation happens inline as today's events are yielded unchanged.
  3. `try/except/finally`: the `except` branch (today's catch-all) also accumulates its synthesized error event before yielding it; the new `finally` branch calls `chat_session_service.append_turn(...)` (only if `session_id` is set and `messages` is non-empty), itself wrapped in `try/except` with a `print` on failure — persistence must never be able to raise into the stream.
- Three new routes added directly to the existing `router` (inherit `/agent` prefix + `dependencies=protected` automatically from `app/api/__init__.py` — no new registration needed):
  - `GET /agent/sessions` → `chat_session_service.list_sessions()`.
  - `GET /agent/sessions/{session_id}` → `chat_session_service.get_session(...)`, `HTTPException(404)` if `None` (CLAUDE.md's single-entity-lookup convention).
  - `DELETE /agent/sessions/{session_id}` → `HTTPException(404)` if `delete_session` returns `False`, else `{"ok": True}` (mirrors `removeFromWatchlist`/`deletePortfolioPosition`'s existing pattern — included now rather than deferred, since a session list with no way to clear old/throwaway entries is a near-certain immediate follow-up).

### 3. `src/lib/api.ts` changes

- `AgentEvent` union gains `| { type: "session_created"; session_id: string }` (append, don't restructure the existing union).
- `streamAgentChat(messages, signal?, reflect?, sessionId?: string | null)` — adds `session_id: sessionId ?? null` to the JSON body.
- New types/functions, mirroring `getPortfolio()`'s typed non-streaming pattern:
  - `ChatSessionSummary { id, title, created_at, updated_at }`
  - `StoredChatMessage` (mirrors the backend's assistant-entry shape, all metadata fields optional)
  - `ChatSessionDetail extends ChatSessionSummary { messages: StoredChatMessage[] }`
  - `getChatSessions(): Promise<ChatSessionSummary[]>`, `getChatSession(id): Promise<ChatSessionDetail>`, `deleteChatSession(id): Promise<void>` — each a plain `apiFetch` call with the existing `if (!res.ok) throw new Error(...)` convention.

### 4. `src/components/dashboard/agent-chat.tsx` changes (the only other file touched — `stock-analyst-assistant.tsx` is NOT modified)

Rationale for not touching `stock-analyst-assistant.tsx`: a real side-by-side sidebar column would need that file's drag-resize math to split one width between two children, which it isn't built for, and nothing here requires simultaneous visibility of transcript + list. Instead, the session list is an **overlay rendered inside `AgentChat`'s own existing root div**, covering everything below a new slim toolbar when open.

- New state: `sessionId: string | null`, `sessions: ChatSessionSummary[]`, `sidebarOpen: boolean`.
- `useEffect` (new import) on mount: best-effort `getChatSessions()` into `sessions` — swallow errors, an empty list just means the overlay shows nothing.
- `send()`: pass `sessionId` into `streamAgentChat(...)`; add a `session_created` branch to the existing event if/else-if chain, setting `sessionId` and prepending the new summary into `sessions` locally (no extra round trip).
- New `newChat()`: pure local reset — `setSessionId(null); setMessages([]); setProposals([]); setTradeProposals([]); setSidebarOpen(false);`. No backend call (lazy creation — a session isn't created until the first message of that chat is actually sent, matching Claude's own "+ New" reference behavior).
- New `resumeSession(id)`: `getChatSession(id)` → convert `StoredChatMessage[]` to `DisplayMessage[]` via a new `storedToDisplay()` helper (1:1 field mapping, tolerant of missing optional keys) → `setSessionId(id); setMessages(converted); setSidebarOpen(false);`.
- New toolbar row as the **first child** of the root `<div className="flex flex-col h-full min-h-0 relative">` (adding `relative` for the overlay's positioning — there is no existing header row in this file, that lives in `stock-analyst-assistant.tsx` and stays untouched): a History icon button (opens the overlay) and a Plus icon button (`newChat()`).
- The overlay itself, conditional on `sidebarOpen`, absolutely positioned to cover the area below that toolbar: a close button, and the `sessions` list — each row click-to-resume, with a small trash icon (appears on hover) calling `deleteChatSession(id)` and removing it from local state on success.
- `lucide-react` import gains `History`, `Plus`, `Trash2`.

### 5. Docs

One-line updates: CLAUDE.md's repo-map comments for `agent-chat.tsx` (now also owns session list/resume) and `docs/ARCHITECTURE.md` §4.4's "Conversation state: client-side only" paragraph (now: client-side state mirrored to a `chat_sessions` Mongo document per session, main chat only).

## Verification

1. **Backend, local** (`cd api && uvicorn main:app --reload --port 8000`): `POST /api/agent/chat` with no `session_id` (via `/api/docs` or curl with a minted bearer token) — confirm a `session_created` event arrives first, and a `chat_sessions` document exists immediately with `messages: []` even before the turn finishes streaming, then gets the two new entries appended once the stream ends. Send a follow-up with that `session_id` and confirm it appends to the same document rather than creating a new one.
2. **List/get/delete**: confirm `GET /agent/sessions` returns entries sorted by `updated_at` desc with correct UTC-offset timestamps (the exact bug class `watchlist.py` hit once already); confirm `GET /agent/sessions/{id}` returns the full transcript with the right field shapes; confirm `DELETE` removes it and a second `GET` 404s.
3. **Image stripping**: send a message with a pasted image, confirm the stored content block has the placeholder in place of real base64 data.
4. **Abort case**: start a turn, click Stop mid-stream, confirm the partial answer is still persisted (this is the behavior the chosen `finally`-based design specifically preserves, versus the background-hook alternative which wouldn't).
5. **Frontend**: new-chat button resets to an empty transcript with *no* network request firing until the first message is actually sent (check the network tab); opening the history overlay mid-stream doesn't disturb the in-flight message's `streaming` state or content; resuming a session with tool calls/citations/usage/groundedness in its stored history renders all of that correctly after conversion; confirm `runMultiAgentAnalysis()` is completely unaffected (no `sessionId` involved there).
6. **Regression**: confirm `/multi_analysis` and `/injection_demo` are untouched, and that `evals/run_evals.py`'s direct POSTs (which don't send `session_id`) still work given the field defaults to `None`.
7. **Deploy check**: once on a preview deployment, repeat step 1 against the live Vercel URL to confirm the synchronous `finally`-based write behaves identically in the serverless environment (this is the one piece this design specifically avoids needing to gamble on, but still worth confirming once for real).

## Critical files

- `api/app/services/chat_session_service.py` (new)
- `api/app/api/agent.py`
- `src/lib/api.ts`
- `src/components/dashboard/agent-chat.tsx`
- `CLAUDE.md`, `docs/ARCHITECTURE.md` (one-line updates each)
