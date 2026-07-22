"""smallcase MCP server — public, read-only, UNOFFICIAL.

Exposes smallcase's public discovery data (catalog, returns, risk metrics,
rationale, rebalance schedule) as MCP tools any LLM/agent can call. No
authentication, no browser, no affiliation with smallcase.

It cannot read holdings/weights or a personal portfolio — those are gated by
smallcase and are intentionally out of scope.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import client

mcp = FastMCP("smallcase")


@mcp.tool()
async def search_smallcases(
    query: str | None = None,
    volatility: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    sort: str = "popularity",
    limit: int = 20,
    include_private: bool = False,
) -> dict:
    """Search / screen published smallcases from the public catalog.

    Returns each smallcase's name, publisher, CAGR, minimum investment,
    volatility, monthly subscription price, constituent count, and whether it
    is private (closed to new investors).

    Args:
        query: Case-insensitive text match on name / description / publisher
            (e.g. "gold", "momentum", "Windmill").
        volatility: Filter by risk band: "low", "medium", or "high".
        min_amount: Only smallcases with minimum investment >= this (INR).
        max_amount: Only smallcases with minimum investment <= this (INR).
        sort: One of "popularity" (default), "min_amount", "returns"
            (by CAGR, high to low), or "recently_rebalanced".
        limit: Max results to return (1-50).
        include_private: Also return schemes closed to new investors (marked
            private=true). Default False shows only open, discoverable ones.
    """
    return await client.search_smallcases(
        query=query,
        volatility=volatility,
        min_amount=min_amount,
        max_amount=max_amount,
        sort=sort,
        limit=limit,
        include_private=include_private,
    )


@mcp.tool()
async def get_smallcase(scid: str) -> dict:
    """Full public detail for one smallcase by SCID (e.g. "SCET_0005").

    Includes returns across all horizons (1D-5Y, since inception), risk metrics
    (volatility, sharpe, beta, cap split, 52-week high/low), minimum investment,
    and index value. Holdings/weights are gated by smallcase and come back empty.
    """
    return await client.get_smallcase(scid)


@mcp.tool()
async def compare_smallcases(scids: list[str]) -> dict:
    """Compare 2-5 smallcases side by side (returns, risk, minimum investment).

    Args:
        scids: List of 2-5 SCIDs, e.g. ["SCET_0005", "SCSB_0001"].
    """
    return await client.compare_smallcases(scids)


@mcp.tool()
async def list_managers(page: int = 1, page_size: int = 20) -> dict:
    """List smallcase publishers / managers (the research houses).

    Args:
        page: 1-based page number.
        page_size: Results per page (1-50).
    """
    return await client.list_managers(page=page, page_size=page_size)


@mcp.tool()
async def get_rebalance_schedule(scid: str) -> dict:
    """Rebalance cadence and last/next rebalance dates for a smallcase.

    Args:
        scid: The smallcase id, e.g. "SCET_0005".
    """
    return await client.get_rebalance_schedule(scid)


@mcp.tool()
async def search_stocks(query: str | None = None, limit: int = 20) -> dict:
    """Search stocks in smallcase's public universe.

    Args:
        query: Case-insensitive match on name / ticker / sector (e.g. "HDFC", "bank").
        limit: Max results to return (1-50).
    """
    return await client.search_stocks(query=query, limit=limit)


@mcp.tool()
async def search_mutual_funds(query: str | None = None, limit: int = 20) -> dict:
    """Search mutual funds in smallcase's public universe.

    Args:
        query: Case-insensitive match on name / AMC / category (e.g. "DSP", "energy").
        limit: Max results to return (1-50).
    """
    return await client.search_mutual_funds(query=query, limit=limit)


@mcp.tool()
async def list_collections(query: str | None = None, limit: int = 20) -> dict:
    """List curated smallcase collections (themed groupings of smallcases).

    Args:
        query: Optional case-insensitive match on collection name / description.
        limit: Max results to return (1-50).
    """
    return await client.list_collections(query=query, limit=limit)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
