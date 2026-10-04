"""
MCP client for the agent's web_search tool (see agent/tools.py).

Unlike every other tool in this registry, which calls an in-process
service method directly, this one talks to a separate process - the
DuckDuckGo MCP server (github.com/nickclyde/duckduckgo-mcp-server) -
over the Model Context Protocol's stdio transport. No API key: it's a
free, unauthenticated wrapper around DuckDuckGo's own search.

run_agent_turn() (loop.py) and dispatch() (tools.py) are synchronous -
this app's convention is blocking calls in `def` handlers, run in
FastAPI's threadpool, not async. The mcp SDK is async-first, so
search_web() is a thin anyio.run() bridge over the real async client
call. anyio.run() starts its own event loop, which is only safe because
nothing in this call stack already has one running.
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


async def _search(query: str, max_results: int) -> str:
    async with Client(_SERVER_PARAMS) as client:
        result = await client.call_tool("search", {"query": query, "max_results": max_results})
        return "\n".join(block.text for block in result.content if isinstance(block, TextContent))


def search_web(query: str, max_results: int = 5) -> str:
    return anyio.run(_search, query, max_results)
