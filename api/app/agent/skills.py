"""
Skills for the conversational analyst agent (loop.py only, not multi_agent.py
yet) - reusable playbooks the model can pull into context on demand, instead
of baking every piece of domain guidance into one ever-growing SYSTEM_PROMPT.

Deliberately NOT modeled on mcp_client.py's discover_tools() pattern, even
though both are "progressive disclosure": MCP tools come from an external
server that can change at any time, so loop.py re-discovers them every turn.
Skills are static local files that only change when someone edits this repo,
so the short catalog (name + one-line description) is cheap enough to bake
directly into the system prompt once, at import time - no discovery call,
no per-turn cost. Only the *full* content of a given skill is deferred,
fetched via the one load_skill tool in tools.py when the model decides a
skill is actually relevant to the question asked.

To add a skill: write app/agent/skills/<id>.md, then add one entry below.
Keep each file well under ~2,000 characters - dispatch()'s 8,000-character
tool-result cap in tools.py is a safety net, not a budget to use up; a
turn with one skill load already has 20+ other tools' worth of potential
results still to come.
"""
import os

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")

SKILLS = [
    {
        "id": "earnings_review",
        "description": (
            "Step-by-step playbook for assessing a ticker's latest quarterly earnings properly - "
            "framing beat/miss against estimates, guidance, and the market's own reaction, not just "
            "whether the raw numbers went up."
        ),
    },
    {
        "id": "filing_red_flags",
        "description": (
            "Checklist of specific things to look for in a ticker's SEC filings (going concern, "
            "material weakness, related-party transactions, litigation, auditor changes) and how to "
            "weigh a finding, rather than treating every risk-factor sentence as equally alarming."
        ),
    },
    {
        "id": "smart_money_diligence",
        "description": (
            "Guidance on interpreting Congress trades, 13F activity, and smart-money convergence "
            "without overreacting to noise - what actually counts as a meaningful signal versus one "
            "weak, stale, or coincidental data point."
        ),
    },
]

SKILL_IDS = [s["id"] for s in SKILLS]
_SKILLS_BY_ID = {s["id"]: s for s in SKILLS}


def catalog_text() -> str:
    """Short name + description list, meant to sit directly in a system
    prompt - see loop.py. Cheap enough to always include; nothing here
    needs the model to make a round trip just to find out what exists."""
    return "\n".join(f"- {s['id']}: {s['description']}" for s in SKILLS)


def load_skill(skill_id: str) -> str:
    if skill_id not in _SKILLS_BY_ID:
        return f"No such skill '{skill_id}'. Available skills: {', '.join(SKILL_IDS)}"
    path = os.path.join(SKILLS_DIR, f"{skill_id}.md")
    with open(path, encoding="utf-8") as f:
        return f.read()
