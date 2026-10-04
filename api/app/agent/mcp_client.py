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

# Resolve the console script next to the running interpreter rather than
# trusting $PATH - this backend is run as `.venv/bin/uvicorn ...` without
# activating the venv (see CLAUDE.md commands), so $PATH never gains
# .venv/bin, and a bare "duckduckgo-mcp-server" command fails to spawn.
# pip installs console scripts into the same bin/ dir as the interpreter
# that ran pip install, so this resolves correctly for any venv.
_SCRIPT = os.path.join(os.path.dirname(sys.executable), "duckduckgo-mcp-server")
_SERVER_PARAMS = StdioServerParameters(command=_SCRIPT if os.path.exists(_SCRIPT) else "duckduckgo-mcp-server")


async def _search(query: str, max_results: int) -> str:
    async with Client(_SERVER_PARAMS) as client:
        result = await client.call_tool("search", {"query": query, "max_results": max_results})
        return "\n".join(block.text for block in result.content if isinstance(block, TextContent))


def search_web(query: str, max_results: int = 5) -> str:
    return anyio.run(_search, query, max_results)
