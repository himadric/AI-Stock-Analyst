#!/usr/bin/env python3
"""
PreToolUse hook: gates `gh pr merge` behind two signals that are already
part of this repo's CI - it doesn't invent a new approval mechanism, it
enforces that the existing ones were actually satisfied before a merge
(which triggers a real Vercel production deploy) can go through:

1. Agent evals (.github/workflows/run_evals_on_preview.yml) posted a PR
   comment for the CURRENT head commit saying "All cases passed." - that
   workflow runs with continue-on-error: true, so its GitHub check always
   shows green even when every eval case fails (confirmed live once,
   during an Anthropic billing outage) - the real signal only lives in the
   comment body, never in the check's pass/fail status. This hook reads
   the comment, not the check.
2. Claude Code review (.github/workflows/claude-code-review.yml) has a
   completed run for the current head commit, AND every inline review
   comment thread it may have created is resolved (GitHub's per-thread
   "Resolve conversation" state, queried via the GraphQL API - gh pr
   view's REST-backed --json has no field for this).

Decision is "ask", not a hard "deny", on failure - this is a solo-dev
project, not a multi-engineer team: if a check is wrong, or Anthropic
credits are out again, a human should be able to see exactly why and
choose to override, not be locked out of merging anything. See
docs/plans/merge-gate-hook-plan.md (if present) or CLAUDE.md's
"Approval gate" entry for the full design.

Never raises past its own try/except - an unexpected error here must
surface as a clear "ask" with the real reason, not an opaque crash, and
must never silently allow a merge it couldn't actually check.
"""
import json
import re
import subprocess
import sys


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"`{' '.join(cmd)}` failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def resolve_pr_number(command: str) -> int:
    match = re.search(r"\bgh\s+pr\s+merge\b\s+(\d+)", command)
    if match:
        return int(match.group(1))
    # No number in the command - gh pr merge targets the current branch's PR.
    out = run(["gh", "pr", "view", "--json", "number"])
    return json.loads(out)["number"]


def check_evals(pr: dict, head_sha_date: str) -> str | None:
    """Returns None if the check passes, else a human-readable reason it failed."""
    eval_comments = [
        c for c in pr["comments"]
        if c["body"].startswith("### Agent evals against this preview")
    ]
    if not eval_comments:
        return "no agent-evals comment found on this PR yet (it posts when a Preview deployment succeeds for the latest commit - check one has finished deploying)"

    latest = max(eval_comments, key=lambda c: c["createdAt"])
    if latest["createdAt"] < head_sha_date:
        return f"the latest agent-evals comment ({latest['createdAt']}) predates the current head commit ({head_sha_date}) - push a fresh commit's evals haven't run yet, or wait for them"
    if "All cases passed." not in latest["body"]:
        return f"the latest agent-evals comment reports failures - see {latest['url']}"
    return None


def check_code_review(pr_number: int, head_sha: str) -> str | None:
    """Returns None if the check passes, else a human-readable reason it failed."""
    runs_raw = run([
        "gh", "run", "list", "--workflow=claude-code-review.yml",
        "--json", "headSha,status,conclusion", "--limit", "20",
    ])
    runs = json.loads(runs_raw)
    matching = [r for r in runs if r["headSha"] == head_sha]
    if not any(r["status"] == "completed" and r["conclusion"] == "success" for r in matching):
        return f"Claude Code Review hasn't completed successfully for the current head commit ({head_sha[:8]}) yet"

    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 50) {
            nodes { isResolved comments(first: 1) { nodes { url } } }
          }
        }
      }
    }
    """
    owner_repo = run(["gh", "repo", "view", "--json", "owner,name"])
    info = json.loads(owner_repo)
    graphql_out = run([
        "gh", "api", "graphql",
        "-f", f"query={query}",
        "-f", f"owner={info['owner']['login']}",
        "-f", f"repo={info['name']}",
        "-F", f"pr={pr_number}",
    ])
    threads = json.loads(graphql_out)["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    unresolved = [t for t in threads if not t["isResolved"]]
    if unresolved:
        urls = ", ".join(t["comments"]["nodes"][0]["url"] for t in unresolved)
        return f"{len(unresolved)} unresolved code review comment thread(s): {urls}"
    return None


def decide(command: str) -> dict:
    pr_number = resolve_pr_number(command)
    pr_raw = run([
        "gh", "pr", "view", str(pr_number),
        "--json", "number,comments,commits",
    ])
    pr = json.loads(pr_raw)
    if not pr["commits"]:
        return ask(f"PR #{pr_number} has no commits - can't determine the head commit to check")

    head_commit = pr["commits"][-1]
    head_sha = head_commit["oid"]
    head_sha_date = head_commit["committedDate"]

    reasons = []
    eval_problem = check_evals(pr, head_sha_date)
    if eval_problem:
        reasons.append(f"Evals: {eval_problem}")
    review_problem = check_code_review(pr_number, head_sha)
    if review_problem:
        reasons.append(f"Code review: {review_problem}")

    if reasons:
        return ask("Merge gate not satisfied for PR #" + str(pr_number) + " - " + "; ".join(reasons))
    return allow(f"PR #{pr_number}: evals passed and code review resolved for commit {head_sha[:8]}.")


def allow(reason: str) -> dict:
    return _decision("allow", reason)


def ask(reason: str) -> dict:
    return _decision("ask", reason)


def _decision(permission: str, reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
            "permissionDecisionReason": reason,
        }
    }


def main() -> None:
    payload = json.load(sys.stdin)
    command = payload.get("tool_input", {}).get("command", "")
    try:
        decision = decide(command)
    except Exception as e:
        decision = ask(f"merge_gate.py hit an unexpected error checking this PR ({type(e).__name__}: {e}) - couldn't confirm evals/review status, so this needs a human look")
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
