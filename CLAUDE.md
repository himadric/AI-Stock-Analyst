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
# Swagger UI: http://127.0.0.1:8000/docs

# Batch jobs (run from repo root, need MONGO_URI and sometimes FMP_API_KEY)
python api/scripts/update_snp_heatmap.py
PYTHONPATH=api python api/utils/generate_leaderboard.py
```

There is no automated test suite. Check your changes by running both servers and loading the affected page. You can also call the endpoint through `/docs` or `curl`. Every endpoint except `/api/health` needs `Authorization: Bearer <token>`. While signed in, get a token from `http://localhost:3000/session-token`. The `api/debug_*.py` and `api/verify_*.py` files are throwaway scripts, not tests.

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
| `api/.env` | `PINECONE_API_KEY` | RAG over SEC filings — in progress. Currently only `api/utils/create_pinecone_index.py` reads it; not yet wired into any tool |

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
- The FastAPI CORS allow-list is localhost-only. Production works because the call is same-origin through the Vercel rewrite.
- NextAuth uses `basePath: "/auth_endpoints"`, not the default `/api/auth`, so it doesn't collide with the FastAPI proxy.
- The Vercel Python function has a size limit. Don't add heavy dependencies (scipy, torch, etc.) to `api/requirements.txt`.
- The Gemini model name is hard-coded in `AIService.__init__` (`gemini-3-flash-preview`).
- `get_economic_data()` (GDP/CPI/unemployment on `/macro`) returns hard-coded 2024 values, not live data.
- **Two AI providers, deliberately.** `AIService` (Gemini, raw REST, no tool use) powers every one-shot analysis button. `api/app/agent/loop.py` (Claude, via the `anthropic` SDK, tool use) powers the chat widget only. Don't mix them — a new one-shot analysis is Gemini via `AIService`; a new tool the agent can call is Claude via `agent/tools.py`.
- **`/api/agent/chat` streams SSE over a plain `fetch`, not the browser's `EventSource`.** `EventSource` can't send the `Authorization` header `apiFetch` needs, so `streamAgentChat` in `lib/api.ts` reads `res.body` itself and parses `data: {...}\n\n` frames by hand. Keep that in mind if you touch the wire format on either side — the frontend's parser and the backend's `f"data: {json.dumps(event)}\n\n"` framing have to match.
- The chat widget's conversation history is **client-side only** (React state in `agent-chat.tsx`) — nothing is persisted to Mongo, and a page reload loses it. This was a deliberate v1 simplification, not an oversight.
- SSE streaming through Vercel's Python function + rewrite hasn't been verified in production, only locally. If the chat widget hangs or buffers on Vercel instead of streaming, this is the first thing to check.
- **The chat widget is mounted in `src/app/layout.tsx` (the true root layout), not in `DashboardLayout`.** Every page recreates its own `DashboardLayout` instance, so anything mounted there loses state on navigation; the root layout doesn't. Its popup panel is toggled with a CSS class (`open ? "flex" : "hidden"`), never `{open && <Panel/>}` — conditionally rendering it would unmount `AgentChat` (and its message state) on every close. Both of these were real bugs in an early version, not hypothetical.
- `MODEL` in `api/app/agent/loop.py` is `"claude-sonnet-5-5"`. If Anthropic ships a new default Claude model, this needs a manual bump — nothing here reads it from an env var or resolves an alias.
