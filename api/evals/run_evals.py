"""
Agent evals: runs a fixed set of golden questions (golden_questions.json)
against the chat agent and scores the results, to catch regressions in
tool selection, forbidden phrasing, and groundedness that CLAUDE.md's
"no automated test suite" note otherwise leaves uncaught.

Two modes:

  python run_evals.py                                  # in-process, local, fast
  python run_evals.py --base-url https://preview.url    # HTTP, against a real deployment

In-process mode calls run_agent_turn() directly - no network beyond the
Anthropic API itself, no auth token needed, but only ever tests local code.
HTTP mode POSTs to {base_url}/api/agent/chat and parses the SSE response
the same way streamAgentChat() in src/lib/api.ts does - the only way to
verify a real deployment (this app has real history of local/prod
divergence: the MCP subprocess resolution issue, SSE "not verified in
production" - see CLAUDE.md Gotchas) - and needs AUTH_SECRET and
ALLOWED_USER_EMAIL in the environment to mint a token via auth_helper.py.

Scores but never calls a second judge: the groundedness check reuses
whatever verdict the real run_agent_turn() already produced (via
groundedness_judge.py), read straight off the "groundedness" SSE event -
no new scoring model, no second opinion.
"""
import argparse
import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(api_dir)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

GOLDEN_SET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_questions.json")

# Same red/amber/green threshold agent-chat.tsx already uses for the
# groundedness badge - red (<50) is treated as a failed check here too.
GROUNDEDNESS_FAIL_BELOW = 50


def _run_in_process(question: str) -> dict:
    from app.agent.loop import run_agent_turn

    tools_called = []
    answer_parts = []
    groundedness = None
    for event in run_agent_turn([{"role": "user", "content": question}]):
        if event["type"] == "tool_start":
            tools_called.append(event["tool"])
        elif event["type"] == "text":
            answer_parts.append(event["text"])
        elif event["type"] == "groundedness":
            groundedness = event
        elif event["type"] == "error":
            answer_parts.append(f"[ERROR: {event['message']}]")
    return {"tools_called": tools_called, "answer": "".join(answer_parts), "groundedness": groundedness}


def _run_http(question: str, base_url: str) -> dict:
    import requests
    from auth_helper import mint_token

    auth_secret = os.environ["AUTH_SECRET"]
    allowed_user_email = os.environ["ALLOWED_USER_EMAIL"]
    token = mint_token(auth_secret, allowed_user_email)

    resp = requests.post(
        f"{base_url.rstrip('/')}/api/agent/chat",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"messages": [{"role": "user", "content": question}], "reflect": False},
        stream=True,
        timeout=120,
    )
    resp.raise_for_status()

    tools_called = []
    answer_parts = []
    groundedness = None
    buffer = ""
    # Same SSE framing streamAgentChat() (src/lib/api.ts) parses on the
    # frontend - data: {...}\n\n frames - just the Python equivalent.
    for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
        if not chunk:
            continue
        buffer += chunk
        while "\n\n" in buffer:
            frame, buffer = buffer.split("\n\n", 1)
            for line in frame.split("\n"):
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[len("data: "):])
                if event["type"] == "tool_start":
                    tools_called.append(event["tool"])
                elif event["type"] == "text":
                    answer_parts.append(event["text"])
                elif event["type"] == "groundedness":
                    groundedness = event
                elif event["type"] == "error":
                    answer_parts.append(f"[ERROR: {event['message']}]")
    return {"tools_called": tools_called, "answer": "".join(answer_parts), "groundedness": groundedness}


def _check_tools(expected, actual_tools: list[str]):
    if expected is None:
        return True, "not checked"
    expected_set, actual_set = set(expected), set(actual_tools)
    if not expected_set:
        ok = not actual_set
        detail = "no tools called, as expected" if ok else f"expected no tools, got {sorted(actual_set)}"
        return ok, detail
    ok = expected_set.issubset(actual_set)
    detail = f"called {sorted(actual_set)}" if ok else f"missing {sorted(expected_set - actual_set)}, called {sorted(actual_set)}"
    return ok, detail


def _check_phrases(must_not_contain, answer: str):
    if not must_not_contain:
        return True, "not checked"
    lowered = answer.lower()
    hits = [p for p in must_not_contain if p.lower() in lowered]
    return (not hits), ("clean" if not hits else f"contains forbidden phrase(s): {hits}")


def _check_groundedness(groundedness: dict | None):
    if groundedness is None:
        return True, "no tool call this turn, not applicable"
    score = groundedness["confidence_score"]
    ok = score >= GROUNDEDNESS_FAIL_BELOW
    return ok, f"{score}% grounded ({groundedness['verdict']})"


def main():
    parser = argparse.ArgumentParser(description="Run the chat agent's golden-question eval suite.")
    parser.add_argument("--base-url", default=None, help="If set, run in HTTP mode against this deployment instead of in-process.")
    args = parser.parse_args()

    with open(GOLDEN_SET_PATH) as f:
        cases = json.load(f)

    all_passed = True
    for case in cases:
        print(f"\n=== {case['id']} ===")
        print(f"Q: {case['question']}")
        try:
            if args.base_url:
                result = _run_http(case["question"], args.base_url)
            else:
                result = _run_in_process(case["question"])
        except Exception as e:
            print(f"  ERROR running case: {type(e).__name__}: {e}")
            all_passed = False
            continue

        checks = [
            ("tools", *_check_tools(case.get("expected_tools"), result["tools_called"])),
            ("phrases", *_check_phrases(case.get("must_not_contain"), result["answer"])),
            ("groundedness", *_check_groundedness(result["groundedness"])),
        ]
        case_passed = all(ok for _, ok, _ in checks)
        all_passed = all_passed and case_passed

        print(f"  {'PASS' if case_passed else 'FAIL'}")
        for name, ok, detail in checks:
            print(f"    [{'x' if ok else ' '}] {name}: {detail}")

    print(f"\n{'All cases passed.' if all_passed else 'Some cases failed.'}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
