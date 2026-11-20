#!/usr/bin/env bash
# The repo's checks. Exit 0 only when the branch is fit to review.
#
# The gate runs this script from the main checkout, with the job's worktree
# as the working directory. Keep it fast, deterministic and non-interactive:
# no watch modes, no prompts, nothing that rewrites files.
#
# This repo is a two-stack monorepo (Next.js frontend + FastAPI backend), so
# both stacks are checked. Deliberately NOT included here:
# - `npm run lint`: this repo has ~180 pre-existing issues (see CLAUDE.md),
#   so gating on it would block every job on pre-existing debt, not
#   anything the job itself introduced. reviewer-code.md watches for new
#   convention breaks instead.
# - The agent evals (api/evals/run_evals.py): needs a live ANTHROPIC_API_KEY,
#   a real deployed preview, and costs real money per call. It already has
#   its own separate, slower, post-deploy gate (run_evals_on_preview.yml),
#   which still applies once a factory PR is pushed - this script is the
#   fast, cheap, pre-review gate, not a replacement for that one.
set -euo pipefail

npm ci --prefer-offline
./node_modules/.bin/tsc --noEmit
npm run build

cd api
python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate
pip install -q -r requirements.txt
python -c "from main import app"
