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
CLAUDE.md's "Merge approval gate" section for the full design.

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
    # Only matches a PR number immediately after "merge" (e.g. "gh pr merge
    # 66 --squash"). "gh pr merge --squash 66" (flags before the number)
    # won't match and falls back to resolving via the current branch below
    # - usually correct for this repo's one-branch-checked-out-at-a-time
    # workflow, but a silent fallback, not a validated one.
    match = re.search(r"\bgh\s+pr\s+merge\b\s+(\d+)", command)
    if match:
        return int(match.group(1))
    # No number in the command - gh pr merge targets the current branch's PR.
    out = run(["gh", "pr", "view", "--json", "number"])
    return json.loads(out)["number"]


def check_evals(pr: dict, head_sha: str) -> str | None:
    """Returns None if the check passes, else a human-readable reason it failed."""
    eval_comments = [
        c for c in pr["comments"]
        if c["body"].startswith("### Agent evals against this preview")
    ]
    if not eval_comments:
        return "no agent-evals comment found on this PR yet (it posts when a Preview deployment succeeds for the latest commit - check one has finished deploying)"

    # Matched by exact commit SHA (embedded in the comment header by
    # run_evals_on_preview.yml), not by comparing timestamps - a stale
    # comment compared only by createdAt could look "newer than" a new
    # head commit after a rebase/cherry-pick that preserves an old
    # committer date, or a quick follow-up push with no new eval run yet.
    matching = [c for c in eval_comments if head_sha in c["body"].split("\n", 1)[0]]
    if not matching:
        return f"no agent-evals comment matches the current head commit ({head_sha[:8]}) - the latest one is for a different commit; wait for a fresh run"

    latest = max(matching, key=lambda c: c["createdAt"])
    if "All cases passed." not in latest["body"]:
        return f"the agent-evals comment for commit {head_sha[:8]} reports failures - see {latest['url']}"
    return None


def fetch_all_review_threads(owner: str, repo: str, pr_number: int) -> list[dict]:
    """Paginated - a PR with more than one page of review threads must not
    silently skip checking the rest for unresolved ones."""
    query = """
    query($owner: String!, $repo: String!, $pr: Int!, $after: String) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 50, after: $after) {
            nodes { isResolved comments(first: 1) { nodes { url } } }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
    """
    threads: list[dict] = []
    after: str | None = None
    while True:
        args = ["gh", "api", "graphql", "-f", f"query={query}",
                "-f", f"owner={owner}", "-f", f"repo={repo}", "-F", f"pr={pr_number}"]
        if after:
            args += ["-f", f"after={after}"]
        page = json.loads(run(args))["data"]["repository"]["pullRequest"]["reviewThreads"]
        threads.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return threads


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

    owner_repo = run(["gh", "repo", "view", "--json", "owner,name"])
    info = json.loads(owner_repo)
    threads = fetch_all_review_threads(info["owner"]["login"], info["name"], pr_number)
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

    reasons = []
    eval_problem = check_evals(pr, head_sha)
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
    # Everything, including parsing stdin itself, stays inside this
    # try/except - deliberately not relying on settings.json's
    # "onFailure": "block" to catch a crash here. That field requires
    # Claude Code v2.1.295+ (confirmed against the docs); the installed
    # version at the time this was written is 2.1.243, below that
    # threshold, so "onFailure" may be silently ignored on this exact
    # install and a crash could fall through to "continue" (allow) instead
    # of blocking. Always emitting a valid "ask" decision on any failure
    # path, with exit code 0, makes the real safety guarantee not depend
    # on that field at all - "onFailure": "block" stays in settings.json
    # as defense-in-depth for whenever this gets upgraded past 2.1.295.
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        # settings.json's "if": "Bash(gh pr merge*)" is supposed to mean
        # this script only ever runs for a matching command - but whether
        # "if" is honored on every installed version is disputed (a real
        # Claude Code review comment on this hook's own PR claimed it
        # needs v2.1.295+ too, contradicting what the docs said when this
        # was built - see CLAUDE.md). Cheap and correct either way: don't
        # depend on it. No-op immediately for anything that isn't actually
        # a gh pr merge invocation, so a wrong "if" assumption costs one
        # regex check, not a PR lookup + two CI/GraphQL round trips, and
        # can never surface an "ask" prompt on an unrelated command.
        if not re.search(r"\bgh\s+pr\s+merge\b", command):
            print(json.dumps(allow("not a gh pr merge command - nothing to gate")))
            return
        decision = decide(command)
    except Exception as e:
        decision = ask(f"merge_gate.py hit an unexpected error checking this PR ({type(e).__name__}: {e}) - couldn't confirm evals/review status, so this needs a human look")
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
