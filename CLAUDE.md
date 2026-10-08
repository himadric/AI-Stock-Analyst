# CLAUDE.md

Guidance for Claude Code when working in this repository. For the full system design, data flows, and known issues, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## What this is

**AI Analyst** is a single-user stock and ETF research dashboard. It has three parts:

- **Frontend** (`src/`): Next.js 16 App Router, React 19, TypeScript, Tailwind v4, shadcn/ui (new-york), Recharts. Uses Google sign-in through NextAuth v5, and only the one allowed email address can log in.
- **Backend** (`api/`): a Python 3.12 FastAPI app. It wraps yfinance, SEC EDGAR, USAspending, FMP, YouTube, and Google Gemini (the LLM used for all "AI analysis" features).
- **Batch jobs** (`api/scripts/`, `api/utils/`, `.github/workflows/`): scheduled GitHub Actions that fetch slow or expensive data and store snapshots in MongoDB (`ai_stock_analyst` database). The API then reads those snapshots.

It is deployed on Vercel. The Next.js app and the FastAPI app (a Python serverless function at `api/index.py`) run in one project, and `vercel.json` rewrites `/api/*` to `/api/index`.

## Commands

```bash
# Frontend (repo root)
npm install
npm run dev            # http://localhost:3000 — proxies /api/* to 127.0.0.1:8000 in dev
npm run build
./node_modules/.bin/tsc --noEmit    # typecheck (currently clean — keep it that way)
npm run lint                        # eslint; ~180 pre-existing issues (mostly no-explicit-any / unused vars)

# Backend (MUST run from api/ — imports are `from app...`)
cd api
source ../.venv/bin/activate        # venv lives at repo root
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Swagger UI: http://127.0.0.1:8000/api/docs (also reachable at http://localhost:3000/api/docs via the dev proxy)

# Batch jobs (run from repo root, need MONGO_URI and sometimes FMP_API_KEY)
python api/scripts/update_snp_heatmap.py
PYTHONPATH=api python api/utils/generate_leaderboard.py
```

There is no automated test suite. Check your changes by running both servers and loading the affected page. You can also call the endpoint through `/api/docs` or `curl`. Every endpoint except `/api/health` needs `Authorization: Bearer <token>`. While signed in, get a token from `http://localhost:3000/session-token`. The `api/debug_*.py` and `api/verify_*.py` files are throwaway scripts, not tests.

## Environment variables

| Where | Variable | Purpose |
|---|---|---|
| `.env.local` (Next) | `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `AUTH_URL`, `AUTH_TRUST_HOST` | NextAuth / Google OAuth |
| `.env.local` (Next) | `ALLOWED_USER_EMAIL` | The only email allowed to sign in |
| `.env.local` (Next) | `MONGO_URI` (or `MONGODB_URI`) | Used by the Next route handler `/api/heatmap/relative-strength` |
| `api/.env` | `GEMINI_API_KEY` | All `/api/ai/*` endpoints |
| `api/.env` | `MONGO_URI` (or `MONGODB_URI`) | Watchlist, leaderboard, trackers, govt contracts |
| `api/.env` | `FMP_API_KEY` | Congress/House/Senate trades |
| `api/.env` | `YOUTUBE_API_KEY` | Brand sentiment (optional; if it's missing, YouTube is skipped) |
| `api/.env` | `SEC_USER_AGENT` | `"AppName you@example.com"`, which SEC.gov requires on every EDGAR request |
| `api/.env` | `AUTH_SECRET`, `ALLOWED_USER_EMAIL` | **Same values as `.env.local`.** Used to verify API session tokens |
| `api/.env` | `ANTHROPIC_API_KEY` | The chat widget's agent (`POST /api/agent/chat`). Separate from `GEMINI_API_KEY` — see "Conversational analyst agent" below |
| `api/.env` | `PINECONE_API_KEY` | `FilingSearchService` — the agent's `search_filings` tool and the SEC Filings upload button. Run `api/utils/create_pinecone_index.py` once first |
| `api/.env` | `FRED_API_KEY` | Live GDP/unemployment/CPI/Fed-rate data on `/macro` (`FinanceService.get_economic_data`). Optional — falls back to a hardcoded 2024 snapshot if unset |

Templates live in `.env.example` (frontend) and `api/.env.example` (backend). Never commit real values: the example files hold placeholders only, and credentials, emails and connection strings are always read from the environment and never hard-coded (not even as `os.getenv` defaults). CI jobs get their values from GitHub Secrets.

## Repository map

```
src/
  app/<route>/page.tsx        one folder per dashboard page (all client components)
  app/api/heatmap/...         Next.js route handler that reads Mongo directly (checks the session itself)
  app/session-token/route.ts  issues the short-lived API token for the signed-in user
  app/auth_endpoints/...      NextAuth handlers (basePath is /auth_endpoints, not /api/auth)
  components/layout/dashboard-layout.tsx   sidebar nav + header ticker search
  components/dashboard/stock-analyst-assistant.tsx   the chat widget's bubble+popup chrome — mounted in app/layout.tsx, not a page (see Gotchas)
  components/dashboard/agent-chat.tsx      the chat transcript itself (used by the widget above)
  components/dashboard/portfolio-table.tsx  open/closed position tables for app/portfolio/page.tsx
  components/dashboard/*.tsx  feature components (kebab-case files, named exports)
  components/ui/*.tsx         shadcn primitives — generated, edit sparingly
  lib/api.ts                  ALL backend fetch wrappers live here
  lib/utils.ts                cn(), formatLargeNumber()
  auth.ts, middleware.ts      auth config + route protection
api/
  main.py                     FastAPI app, CORS, mounts router at /api
  index.py                    Vercel entrypoint (re-exports app)
  app/api/<domain>.py         thin routers; registered in app/api/__init__.py
  app/services/<domain>.py    business logic / external API calls
  app/db.py                   shared MongoClient singleton (`db.get_db()`)
  app/auth.py                 `require_auth` dependency: verifies the API token on every router but /health
  app/agent/tools.py           analyst-agent tool registry (wraps existing services, doesn't fetch data itself)
  app/agent/loop.py            the Claude tool-use loop behind POST /api/agent/chat
  app/agent/mcp_client.py       MCP client — dynamically discovers and calls tools from the duckduckgo-mcp-server subprocess
  app/agent/skills.py           skill registry (catalog_text(), load_skill()) + app/agent/skills/*.md playbooks loop.py's agent can pull in on demand
  app/agent/multi_agent.py     multi-agent stock research — a sibling flow to loop.py, not a tool inside it; see "Multi-agent stock research" below
  app/api/portfolio.py         demo portfolio CRUD + the position-aware trade-proposal endpoints multi_agent.py's coordinator writes through
  app/services/filing_search_service.py   RAG over SEC filings (chunk, Pinecone upsert/search; see search_filings tool)
  app/services/smart_money_service.py     cross-references Congress/13F/sector data; see find_smart_money_convergence + get_investment_verdict tools
  utils/create_pinecone_index.py          one-time setup: creates the "sec-filings" Pinecone index
  utils/ingest_filings.py                 CLI to pre-populate a ticker's filings into Pinecone ahead of time
  app/data/*.json             static data (S&P index constituents, UEI map)
  scripts/update_*.py         batch jobs that write Mongo snapshots
  utils/                      more batch jobs + one-off tools
.github/workflows/update_*.yml  cron schedules for the batch jobs
```

## How to add a feature (follow this pattern)

### 1. Backend endpoint

1. Put the logic in a **service** method in `api/app/services/<domain>.py`. Use `finance.py` (`FinanceService`) for anything based on yfinance. Create a new service class for a new external source.
2. Make the result JSON-safe. yfinance/pandas return NaN, Inf, and numpy types, so pass the result through `FinanceService._sanitize_data()` (or an equivalent) before returning it.
3. Add a **thin** route in `api/app/api/<domain>.py`. Create the service once at module level (`finance_service = FinanceService()`), matching the existing routers.
4. If it's a new router, register it in `api/app/api/__init__.py` with a `prefix` and `tags`.
5. Use Pydantic `BaseModel` request bodies for POST endpoints.
6. **Use `def`, not `async def`,** for any handler that calls yfinance, `requests`, `httpx.Client`, or pymongo. These calls block, and inside `async def` they block the event loop. FastAPI runs a `def` handler in a threadpool. (Several existing handlers get this wrong; don't copy them.)
7. Error conventions already used in the codebase:
   - A list or optional-data endpoint returns `[]` or `None` when there's no data. It doesn't return a 404, so the UI can degrade gracefully.
   - A single-entity lookup that fails raises `HTTPException(404)`.
   - A service that reports errors as a `{"error": ...}` dict has its router convert that to `HTTPException(400/500)`.
8. For MongoDB, use `from app.db import db` and then `db.get_db()["collection"]`. Don't create a new `MongoClient` per request (`house.py`, `senate.py`, and `institution_service.py` do this; it's legacy).

### 2. AI analysis

- Add a method to `AIService` in `api/app/services/ai.py` that builds a prompt and calls `self.generate_insight(prompt)`. That returns Markdown text, or an error string; it never raises.
- Follow the existing prompt structure: XML-style sections `<role>`, `<task>`, `<requirements>`, `<data_context>`/`<context_text>`, `<output_format>`, with explicit Markdown output and a word limit.
- The router fetches the data through the finance or SEC service, passes it to `AIService`, and returns `{"analysis": text}`. (`/analyze_filing` returns `{"summary": ...}` and `/analyze_chart` returns a bare string. These are legacy inconsistencies; use `{"analysis": ...}` for new endpoints.)
- The frontend renders the result with `react-markdown`.

### 3. Frontend fetcher

Add a typed function to `src/lib/api.ts` that calls **`apiFetch`**. **Never call `fetch` for backend endpoints directly, in `lib/api.ts` or in a component.** `apiFetch` attaches the session token the backend requires (every request without it gets a 401), and it prepends `API_BASE_URL`, which switches between `http://127.0.0.1:8000/api` (dev) and `/api` (prod). Pattern:

```ts
export async function fetchThing(ticker: string) {
    const res = await apiFetch(`/finance/thing/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch thing");   // or `return null` for optional data
    return res.json();
}
```

### 4. Page

Every page uses the same shell. `useSearchParams` requires the `Suspense` wrapper, or the Next build fails.

```tsx
"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";

function ThingContent() {
    const ticker = useSearchParams().get("ticker") || "AAPL";
    // useState + useEffect([ticker]) → call lib/api fetchers → loading / empty / data states
}

export default function ThingPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout><ThingContent /></DashboardLayout>
        </Suspense>
    );
}
```

- The ticker always comes from the `?ticker=` query string. Pages don't have their own ticker state.
- Load independent data in parallel with `Promise.all`.
- Always render three states: a loading spinner (`Loader2` + `animate-spin`), an empty/error message, and the data.
- Add the page to `navItems` in `src/components/layout/dashboard-layout.tsx`, or it can't be reached. Sidebar links automatically append `?ticker=<last stock ticker>`.

### 5. Components and UI

- Feature components go in `src/components/dashboard/<kebab-name>.tsx`, as `"use client"` with a **named export** (`export function EtfHoldings`) and a `<Name>Props` interface.
- Build with the shadcn primitives in `@/components/ui` (`Card`, `Table`, `Tabs`, `Badge`, `Button`, `Tooltip`, `Sheet`, etc.). Add new ones with `npx shadcn@latest add <name>`.
- Merge classes with `cn()`. Use the theme tokens (`bg-card`, `text-muted-foreground`, `border`) rather than raw colors. Semantic green/red for gains and losses is fine.
- Charts use **Recharts** inside `ResponsiveContainer`. Icons come from **lucide-react**. Dates use **date-fns**. Large numbers go through `formatLargeNumber()`.
- Use the `@/` import alias (it maps to `src/`).
- Prefer real TypeScript interfaces for API responses over `any` in new code.

### 6. Scheduled data (slow or rate-limited sources)

When data is too slow to fetch on each request (13F parsing, scoring hundreds of tickers, paid APIs):

1. Write `api/scripts/update_<name>_data.py`. It loads `.env` with an optional dotenv import, adds `api/` to `sys.path`, fetches the data, and **upserts one snapshot document** into `ai_stock_analyst.<name>`. Existing snapshot shapes are `{type: "recent_trades", data, updated_at}` and `{_id: "<key>", companies: [...]}`.
2. Add `.github/workflows/update_<name>.yml` with a `schedule` cron plus `workflow_dispatch`, passing `secrets.MONGO_URI`.
3. The API endpoint reads the snapshot, and if it's missing returns an empty result or falls back to a live fetch (see `InstitutionService._get_institution_trades`).

### 7. Conversational analyst agent (the chat widget)

This is a tool-calling Claude agent, not a template-filling Gemini prompt like `AIService` — see docs/ARCHITECTURE.md "Conversational analyst agent" for the full design. To add a tool:

1. Write a small dispatch function in `api/app/agent/tools.py` that calls an **existing** service method — don't write new data-fetching logic here, just wrap it. If the payload can be large (a long list, a big history, raw filing text), trim it before returning (see the existing wrappers for the pattern).
2. Add its schema to the `TOOLS` list (Anthropic tool-use format: `name`, `description`, `input_schema` as JSON Schema) and its dispatch function to `TOOL_DISPATCH`. The `description` matters a lot for tool selection quality — say what it's for and when to prefer it over similar tools.
3. That's it — `loop.py` and the router don't change. Every tool result is JSON-serialized and capped at 8,000 characters before it goes back to the model.
4. The one write-capable tool, `propose_watchlist_add`, is intentionally inert — it never touches the database. It only triggers a `watchlist_proposal` SSE event that the frontend renders as a confirm/dismiss card; confirming calls the existing `POST /api/watchlist` endpoint. Don't add a tool that writes directly; keep that confirmation step for anything mutating.
5. Tools from an MCP server are the one exception to all of the above, and don't follow this recipe at all. `agent/mcp_client.py` spawns the DuckDuckGo MCP server as a subprocess and talks the Model Context Protocol to it; `discover_tools()` asks it what it currently exposes and converts that directly into Anthropic's tool-use schema shape, with no hand-written schema or per-tool function on this side. `loop.py` appends that list to `TOOLS` before every turn, and `dispatch()` (`tools.py`) routes any tool name it doesn't recognize through `mcp_client.call_tool()`. To connect a different or additional MCP server, extend `mcp_client.py`'s discovery/dispatch — don't add entries to `TOOLS`/`TOOL_DISPATCH` for its tools individually.
6. **Skills** are a third kind of capability, distinct from both of the above — reusable playbooks (markdown files in `api/app/agent/skills/`), not data tools. `agent/skills.py` holds the `SKILLS` registry (`id`, `description`) and two functions: `catalog_text()` (a short name+description list, baked directly into `loop.py`'s `SYSTEM_PROMPT` at import time — cheap enough to always include, since skills are static local files, unlike MCP tools which need a live per-turn discovery call) and `load_skill(id)` (reads the full markdown file). There's one tool, `load_skill`, wired into `tools.py`/`TOOL_DISPATCH` like any normal tool; its `skill_id` enum is generated from `skills.SKILL_IDS` so it can't drift from the registry. To add a skill: write `api/app/agent/skills/<id>.md` (keep it well under ~2,000 characters — the model still has 20+ other tools' worth of results to fit in the same turn) and add one entry to `SKILLS`. Only `loop.py`'s single agent has this wired in today, not `multi_agent.py`'s personas.

### 8. Multi-agent stock research

A dedicated action (`POST /api/agent/multi_analysis {ticker}`, triggered by a distinct button in the chat widget — not a tool the main chat agent can call mid-conversation). Four fixed personas (`PERSONAS` in `api/app/agent/multi_agent.py`), each a focused mini tool-loop over a filtered slice of the normal `TOOLS` registry, run **concurrently in threads** (not asyncio — this app is sync throughout) and stream nested progress events (`agent_start`, `agent_tool_start`/`agent_tool_end`, `agent_done`) merged onto one SSE stream via a shared `queue.Queue()`. A final coordinator call synthesizes all four reports into the answer.

To add or change a persona: edit the `PERSONAS` list (`id`, `label`, `tool_names`, `system_prompt`) — `tool_names` must match real names in `tools.py`'s `TOOLS` (validated at runtime by `_tools_for()`, which raises on an unknown name). Each persona's `MAX_TOOL_TURNS`/`MAX_TOKENS` budget needs to be large enough for however many tools it has — a persona with many tools needs more turns, and a turn with many tool results needs enough token budget that thinking doesn't consume the whole response before any visible text comes out (see the `needs_fallback` handling in `_run_subagent` for what catches this if the budget is too tight anyway).

Why this isn't modeled as one more entry in `TOOL_DISPATCH` like a normal tool: `dispatch()` is a simple synchronous call-and-return that 29+ tools rely on. Streaming nested per-subagent progress during a single "call" would mean either turning `dispatch()` into a generator (complicating every other tool's calling convention to serve this one unusual case) or special-casing it anyway — so it's a sibling flow to `run_agent_turn`, with its own endpoint and its own SSE event vocabulary layered on top of the shared `text`/`error`/`done` events, same pattern `mcp_client.py` uses for extending capability without disturbing the existing tool contract.

### 9. Portfolio and position-aware trade proposals

A demo portfolio, not a real brokerage link. The CRUD logic (add/sell/delete a position, live-quote enrichment via the already-parallelized `FinanceService.get_quotes()`) lives in `PortfolioService` (`app/services/portfolio_service.py`) — unlike `watchlist.py`, which puts this directly in the router. It's a real service here, not just following CLAUDE.md's own stated convention more closely, because `app/agent/multi_agent.py` needs the exact same add/sell logic for auto-executed trades (see below), and `app/api/portfolio.py` is a thin wrapper that catches the service's `ValueError`s and converts them to `HTTPException`s. One simplification: **at most one open position per ticker at a time** — keeps the sell flow a simple ticker-keyed lookup rather than needing to track multiple lots.

**Don't import `app.api.portfolio` from `app.agent.multi_agent.py` (or any other non-router module).** Importing any submodule of the `app.api` package runs `app/api/__init__.py`, which imports `app.api.agent`, which imports `run_multi_agent_analysis` from `multi_agent.py` — a circular import if `multi_agent.py` is itself mid-import at that point. This is exactly why the CRUD logic lives in `PortfolioService`: both the router and the agent import the service (a strictly lower layer that never imports from `app.api` or `app.agent`), neither imports the other.

**Selling never deletes a position.** `POST /portfolio/{ticker}/sell` (and `PortfolioService.sell_position()` underneath it) sets `status: "closed"` plus `sell_price`/`sell_date` on the same document — the Portfolio page's "Closed Positions" section reads directly off that, showing buy price, sell price, and realized gain/loss. If you're adding a feature that touches a position's lifecycle, preserve this: don't add a code path that `DELETE`s an open position as part of closing it. `DELETE /portfolio/{id}` exists separately, for correcting a mistaken manual entry — a different action from selling.

**How the multi-agent coordinator becomes position-aware:** before its synthesis call, `run_multi_agent_analysis()` looks up whether an open position exists for the ticker (`_get_open_position()` in `multi_agent.py`, which calls `PortfolioService.get_open_position()`) and includes it as plain text context in the coordinator's prompt — the same way the four subagent reports are already passed in, not a new tool call. `COORDINATOR_SYSTEM_PROMPT` then asks for an explicit hold-vs-sell (if held) or buy-vs-pass (if not) read, and to call `propose_trade` only when the synthesis actually supports a buy or sell — not on every analysis. The model proposes via a real, structured tool call (never free-text parsing), mirroring `propose_watchlist_add`'s shape.

**The dollar-amount auto-execute gate.** A buy is always a fixed `PLACEHOLDER_BUY_SHARES` (10, kept in sync between `multi_agent.py` and `agent-chat.tsx`); a sell is always the full held position (never partial, consistent with the one-open-position-per-ticker rule). `run_multi_agent_analysis()` prices the trade (`shares * live price`) and checks it against `AUTO_EXECUTE_THRESHOLD` (1000): **below the threshold, it calls `PortfolioService.add_position()`/`sell_position()` directly and yields a `trade_executed` event** — no human confirmation, since the dollar amount is small enough that asking adds friction without protecting the user much. **At or above the threshold, it falls through to the existing gated `trade_proposal` event**, unchanged — the frontend renders that as a confirm/dismiss card, and nothing is written until the user clicks. If an auto-execute attempt fails on a legitimate business rule (e.g. a "buy" when a position is already open), it logs the failure and falls through to the gated path too, rather than silently dropping the proposal. `agent-chat.tsx` renders `trade_executed` by pushing a `TradeProposal` entry with `status` already `"bought"`/`"sold"` and `auto: true` — same card component as a human-confirmed trade, just no buttons and a label noting it was auto-executed. Confirmed (non-auto) buys use the live price fetched fresh at confirm time, not whatever price the coordinator saw mid-analysis; auto-executed trades price at the moment of execution for the same reason.

## Conventions

- **Python:** snake_case, service classes named `<Domain>Service`, docstrings on public methods, `print()` for logging (no logging framework yet). Wrap external calls in `try/except` and return a safe empty value.
- **TypeScript:** 4-space indent in pages, 2-space in some components (match the file you're editing). Double quotes.
- **Git:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `chore:`). Work on a feature branch and open a PR into `master`.
- **Ticker defaults:** `AAPL` for stock pages, `VOO` for `/etf`.
- The SEC ticker list (`SECService`) is downloaded from sec.gov when the service is constructed. Reuse an existing instance where you can instead of creating new ones.

## Code review checklist

Every pull request into `master` (from a branch in this repo, not a fork) gets an automated advisory review from Claude Code — see `.github/workflows/claude-code-review.yml`. It checks the diff against this list, which is also what a human or an interactive Claude Code review should check:

- **Security:** no credentials, emails, or connection strings in code. New FastAPI routers are registered with `dependencies=protected` in `app/api/__init__.py`, unless they're meant to be public like `/health`. New Next.js route handlers under `/api` call `auth()` themselves. `TOKEN_KEY_CONTEXT` stays identical between `api/app/auth.py` and `src/app/session-token/route.ts`.
- **Backend:** no `async def` handler calling blocking code (yfinance, `requests`, `httpx.Client`, pymongo) — use `def` so FastAPI runs it in its threadpool. New service data passes through `_sanitize_data()` before it's returned. Mongo access goes through `db.get_db()`, not a new `MongoClient`. New AI endpoints return `{"analysis": ...}`.
- **Frontend:** backend calls go only through `apiFetch` in `lib/api.ts` — never a hard-coded host or a bare `fetch` to the backend from a component. New pages follow the `Suspense` + `DashboardLayout` pattern and get an entry in `dashboard-layout.tsx`'s `navItems`. Avoid adding new `any` types where a real interface is easy.
- **Correctness:** logic errors, missing null/empty checks, off-by-one or wrong-sign bugs, and unhandled promise rejections.
- **Consistency with docs:** if the change adds or renames an environment variable, a route, or a data source, `README.md` / `.env.example` / this file should be updated in the same PR.

This review is advisory only. It never approves, requests changes, or edits code — treat its comments the way you'd treat a colleague's, and use your own judgment on which to act on.

## Gotchas

- **How API auth works.** `middleware.ts` protects pages only. The API is protected separately: `lib/api.ts` gets a 1-hour HS256 token from `/session-token` (issued only to the signed-in `ALLOWED_USER_EMAIL`) and sends it as `Authorization: Bearer`, and `api/app/auth.py` verifies it. Both sides derive the signing key from `AUTH_SECRET` using the context string `ai-analyst-api-token`; keep those in sync. A new router is protected automatically when you register it with `dependencies=protected` in `app/api/__init__.py`. Only `/health` is public. New Next.js route handlers under `/api` must call `auth()` themselves.
- **The `/api` namespace is shared.** The Next route `src/app/api/heatmap/relative-strength` wins over the dev rewrite and the Vercel rewrite only because filesystem routes resolve first. Don't add FastAPI routes under `/api/heatmap/`.
- **Swagger UI and the OpenAPI schema live at `/api/docs` / `/api/openapi.json`, not FastAPI's defaults (`/docs`, `/openapi.json`).** Set via `docs_url`/`openapi_url`/`redoc_url` on the `FastAPI(...)` constructor in `main.py`. This is deliberate, not a leftover: `vercel.json` only rewrites `/api/:path*` to the Python function, so anything at the app root is unreachable once deployed. If you ever add another FastAPI-internal route (a custom docs page, etc.), it needs the same `/api` prefix or it'll work locally and 404 in production.
- The FastAPI CORS allow-list is localhost-only. Production works because the call is same-origin through the Vercel rewrite.
- NextAuth uses `basePath: "/auth_endpoints"`, not the default `/api/auth`, so it doesn't collide with the FastAPI proxy.
- The Vercel Python function has a size limit. Don't add heavy dependencies (scipy, torch, etc.) to `api/requirements.txt`.
- The Gemini model name is hard-coded in `AIService.__init__` (`gemini-3-flash-preview`).
- `get_economic_data()` (GDP/CPI/unemployment/Fed rate on `/macro`) uses live FRED API data when `FRED_API_KEY` is set, falling back to a hardcoded 2024 snapshot otherwise (same optional-key degrade pattern as `YOUTUBE_API_KEY`). The CPI series uses FRED's `units=pc1` transform to get a year-over-year inflation rate server-side, rather than computing it from the raw index.
- **Two AI providers, deliberately.** `AIService` (Gemini, raw REST, no tool use) powers every one-shot analysis button. `api/app/agent/loop.py` (Claude, via the `anthropic` SDK, tool use) powers the chat widget only. Don't mix them — a new one-shot analysis is Gemini via `AIService`; a new tool the agent can call is Claude via `agent/tools.py`.
- **`/api/agent/chat` streams SSE over a plain `fetch`, not the browser's `EventSource`.** `EventSource` can't send the `Authorization` header `apiFetch` needs, so `streamAgentChat` in `lib/api.ts` reads `res.body` itself and parses `data: {...}\n\n` frames by hand. Keep that in mind if you touch the wire format on either side — the frontend's parser and the backend's `f"data: {json.dumps(event)}\n\n"` framing have to match.
- The chat widget's conversation history is **client-side only** (React state in `agent-chat.tsx`) — nothing is persisted to Mongo, and a page reload loses it. This was a deliberate v1 simplification, not an oversight.
- SSE streaming through Vercel's Python function + rewrite hasn't been verified in production, only locally. If the chat widget hangs or buffers on Vercel instead of streaming, this is the first thing to check.
- **The chat widget is mounted in `src/app/layout.tsx` (the true root layout), not in `DashboardLayout`.** Every page recreates its own `DashboardLayout` instance, so anything mounted there loses state on navigation; the root layout doesn't. Its popup panel is toggled with a CSS class (`open ? "flex" : "hidden"`), never `{open && <Panel/>}` — conditionally rendering it would unmount `AgentChat` (and its message state) on every close. Both of these were real bugs in an early version, not hypothetical.
- `MODEL` in `api/app/agent/loop.py` is `"claude-sonnet-5-5"`. If Anthropic ships a new default Claude model, this needs a manual bump — nothing here reads it from an env var or resolves an alias.
- **The installed `pinecone` SDK (v10) doesn't match Pinecone's own docs.** `upsert_records()` and `search()` are keyword-only (no positional args), and `search()` takes `top_k`/`inputs` as flat keyword arguments, not nested under a `query={"inputs": ..., "top_k": ...}` dict the way the docs show. Verified directly against the installed package, not assumed — check `inspect.signature()` again if you're touching `filing_search_service.py` and something that looks right by the docs throws a `PineconeValueError`.
- `search_filings` ingests on demand: the **first** search for a ticker with nothing in Pinecone yet fetches and chunks its 2 most recent filings before it can answer, which is much slower than every other tool. Use the "upload" button on the Overview page's SEC Filings list, or `api/utils/ingest_filings.py TICKER`, to pre-populate a ticker and avoid that first-query latency.
- Pinecone namespaces are per-ticker, and record `_id`s are `{ticker}-{accessionNumber}-{chunk_index}` — stable, so re-ingesting the same filing is a harmless no-op upsert, not a duplicate. Don't change this `_id` scheme without a migration; existing vectors won't be found or overwritten under a new scheme, just orphaned.
- **The agent's tools from `duckduckgo-mcp-server` are discovered dynamically, not hand-wired.** `mcp_client.discover_tools()` asks the server what it currently exposes (as of writing: `search`, `fetch_content`, `expand_link` — no resources or prompts) and converts that straight into Anthropic's tool-use schema; nothing in this codebase names a specific tool. If the server's own tool list changes, this app's available tools change with it with no code change here. It's also the first thing in this app that spawns a child process at request time. Verified working on Vercel, but confirm again if you touch `mcp_client.py` — this took several rounds to get right in production (console-script resolution, then `sys.path` propagation into the subprocess — see the git history on `agent/mcp_client.py` if you need the specifics).
- `mcp_client.py`'s public functions (`discover_tools()`, `call_tool()`) bridge synchronous calls (from `dispatch()`/`loop.py`) into the `mcp` SDK's async `Client` via `anyio.run()`. That's only safe because nothing in that call chain already has an event loop running (it's invoked from a sync `def` FastAPI handler, in the threadpool). Don't call either from anything that's already inside an async context — `anyio.run()` will fail if a loop is already running in that thread.
