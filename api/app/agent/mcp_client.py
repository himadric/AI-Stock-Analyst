"""
MCP client for the agent (see agent/loop.py and agent/tools.py).

Unlike every tool in agent/tools.py, which calls an in-process service
method directly, this talks to a separate process - the DuckDuckGo MCP
server (github.com/nickclyde/duckduckgo-mcp-server) - over the Model
Context Protocol's stdio transport. No API key: it's a free,
unauthenticated wrapper around DuckDuckGo's own search.

This is a dynamic integration, not a hand-wired one: discover_tools()
asks the server what it currently exposes (as of writing: search,
fetch_content, expand_link - no resources or prompts) and converts
that directly into Anthropic's tool-use schema shape. Nothing here
names a specific tool. If the server's own tool list changes, this
app's available tools change with it automatically, with no code
change on this side - loop.py just appends whatever comes back to the
model's tool list, and dispatch() (tools.py) routes any tool name it
doesn't recognize as one of its own through call_tool() below.

run_agent_turn() (loop.py) and dispatch() (tools.py) are synchronous -
this app's convention is blocking calls in `def` handlers, run in
FastAPI's threadpool, not async. The mcp SDK is async-first, so the
public functions here are thin anyio.run() bridges over the real async
client calls. anyio.run() starts its own event loop, which is only
safe because nothing in this call stack already has one running.
"""
import os
import sys
import anyio
from mcp import Client
from mcp.types import TextContent
from mcp.client.stdio import StdioServerParameters

# Invoke the package's documented entry point (duckduckgo_mcp_server.server:main,
# per its pyproject.toml) directly through the running interpreter, rather than
# the "duckduckgo-mcp-server" console script pip normally generates. Locally
# that script works, but on Vercel's Python runtime it isn't on $PATH or next
# to sys.executable at all - console-script entry points apparently aren't
# materialized there the way a normal pip install creates them (confirmed via
# a real "No such file or directory" error in production). `python -c` only
# depends on the module being importable by this same interpreter - guaranteed,
# it's a requirements.txt dependency - EXCEPT that a freshly spawned subprocess
# starts with a cold sys.path, and on Vercel this process's own sys.path has
# extra entries injected by Vercel's own bootstrap (not a standard site-packages
# location a fresh interpreter would pick up on its own), which a plain
# subprocess doesn't inherit - confirmed via a real "ModuleNotFoundError: No
# module named 'duckduckgo_mcp_server'" in production despite the parent
# process importing it fine. Passing PYTHONPATH explicitly makes the child see
# the same import locations as this already-working parent, regardless of
# whatever Vercel's bootstrap does to get there.
_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-c", "from duckduckgo_mcp_server.server import main; main()"],
    env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
)

# Cache of the last successful discover_tools() call, reused for the life of
# this process (a warm serverless instance doesn't need to re-spawn the
# server and ask what it can do on every request) and as a fallback if a
# later discovery attempt fails.
_cached_tool_schemas: list[dict] | None = None


async def _discover() -> list[dict]:
    async with Client(_SERVER_PARAMS) as client:
        result = await client.list_tools()
        return [
            {"name": t.name, "description": t.description or "", "input_schema": t.input_schema}
            for t in result.tools
        ]


def discover_tools() -> list[dict]:
    """
    Anthropic-tool-use-schema list of whatever the MCP server currently
    exposes. Cached after the first successful call; on failure, falls back
    to that cache if one exists, else returns [] (the agent just runs
    without these tools for this turn rather than failing the whole turn).
    """
    global _cached_tool_schemas
    try:
        _cached_tool_schemas = anyio.run(_discover)
    except Exception as e:
        print(f"[mcp discover_tools] failed: {type(e).__name__}: {e}")
        if _cached_tool_schemas is None:
            return []
    return _cached_tool_schemas


async def _call(name: str, arguments: dict) -> str:
    async with Client(_SERVER_PARAMS) as client:
        result = await client.call_tool(name, arguments)
        return "\n".join(block.text for block in result.content if isinstance(block, TextContent))


def call_tool(name: str, arguments: dict) -> str:
    """Calls any tool the MCP server exposes by name - not specific to search."""
    return anyio.run(_call, name, arguments)
