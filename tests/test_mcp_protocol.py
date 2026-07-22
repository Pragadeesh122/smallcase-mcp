"""End-to-end MCP protocol test.

Launches the server as a real subprocess over stdio, performs the MCP
handshake, lists tools, and calls one — exactly what an MCP client
(Claude Desktop / Claude Code) does.

Run:  uv run python tests/test_mcp_protocol.py
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _payload(result) -> dict:
    """Read a tool result whether the SDK returns structured or text content."""
    if getattr(result, "structuredContent", None):
        return result.structuredContent
    for block in result.content:
        if getattr(block, "type", None) == "text":
            return json.loads(block.text)
    return {}


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "smallcase_mcp.server"]
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("[PASS] handshake + tools/list:", names)
            assert names == [
                "compare_smallcases",
                "get_smallcase",
                "list_managers",
                "search_smallcases",
            ], names

            result = await session.call_tool(
                "search_smallcases", {"query": "gold", "sort": "returns", "limit": 3}
            )
            data = _payload(result)
            scs = data.get("smallcases") or []
            assert scs, f"no results from tools/call: {result.content}"
            print(f"[PASS] tools/call search_smallcases -> {len(scs)} results")
            for s in scs:
                print(f"        - {s['name']} | CAGR={s['cagr']} | min={s['min_investment']}")

    print("\nMCP PROTOCOL OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
