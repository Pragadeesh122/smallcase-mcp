# smallcase-mcp

> # ⚠️ UNOFFICIAL — this is NOT the official smallcase MCP
>
> This is an **independent, community-built** project. It is **NOT** built,
> authorized, endorsed, sponsored, or supported by **smallcase**, it is **NOT**
> "the smallcase MCP," and it uses **no official smallcase API**. "smallcase" is a
> trademark of its respective owner. It reads smallcase's **public website
> endpoints** (not the official [smallcase Gateway](https://developers.gateway.smallcase.com)
> API), which can change or break at any time. Provided for informational/research
> use only — **not investment advice**, and not an official data source. Some data
> (notably **past returns**) is shown in smallcase's own UI behind a consent step
> ("as per applicable guidelines"); use at your own discretion. All data © smallcase
> and the respective publishers.

A **read-only** [MCP](https://modelcontextprotocol.io) server that exposes
[smallcase](https://www.smallcase.com)'s **public** discovery data — the catalog of
published smallcases, their returns, risk metrics, rationale, rebalance schedule, plus
stocks, mutual funds and curated collections — to any LLM or agent (Claude Desktop,
Claude Code, Cursor, …).

No API key. No browser. No login. Just clean HTTP over the endpoints the public
smallcase.com website already calls for logged-out visitors.

## What it can and can't do

| ✅ Available (public) | ❌ Not available (gated by smallcase) |
|---|---|
| Search/list the full catalog of published smallcases | Constituents / holdings + weights |
| CAGR, returns (1D → 5Y, since inception) | Rebalance *constituent history* |
| Risk metrics (volatility, sharpe, beta, cap split, 52w hi/lo) | Your personal portfolio / investments |
| Minimum investment, monthly subscription price | Placing orders / any transaction |
| Rationale, rebalance *schedule*, publisher info | |

## Tools

| Tool | Description |
|---|---|
| `search_smallcases(query, volatility, min_amount, max_amount, sort, limit)` | Search/screen published smallcases. Text match on name/description/publisher, `volatility` = low/medium/high, min/max investment, `sort` = popularity \| min_amount \| returns \| recently_rebalanced. |
| `get_smallcase(scid)` | Full detail for one smallcase by SCID (e.g. `SCET_0005`): returns, risk, rationale, methodology. |
| `compare_smallcases(scids)` | Side-by-side of 2–5 smallcases (returns / risk / min investment). |
| `get_rebalance_schedule(scid)` | Rebalance cadence and last/next rebalance dates for a smallcase. |
| `list_managers(page, page_size)` | List smallcase publishers / research houses. |
| `search_stocks(query, limit)` | Search stocks in smallcase's public universe (name / ticker / sector). |
| `search_mutual_funds(query, limit)` | Search mutual funds (name / AMC / category). |
| `list_collections(query, limit)` | List curated smallcase collections (themed groupings). |

Example prompts once connected: *"find low-volatility gold smallcases under ₹5000"*,
*"compare SCET_0005 and the top smallcase by returns"*, *"what's the rationale behind SCET_0005?"*,
*"when does SCET_0005 next rebalance?"*, *"search bank stocks"*, *"show me energy mutual funds"*.

## Setup

```bash
git clone https://github.com/Pragadeesh122/smallcase-mcp.git
cd smallcase-mcp
uv sync
```

Verify it talks to the live API (14 checks) and speaks the MCP protocol:

```bash
uv run python tests/test_live.py
uv run python tests/test_mcp_protocol.py
```

## Use it from an MCP client

Run over stdio:

```bash
uv run smallcase-mcp
```

### Claude Code (one-liner)

```bash
claude mcp add -s user smallcase -- uv --directory /path/to/smallcase-mcp run smallcase-mcp
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "smallcase": {
      "command": "uv",
      "args": ["--directory", "/path/to/smallcase-mcp", "run", "smallcase-mcp"]
    }
  }
}
```

## Stack

Python 3.11+ · [MCP Python SDK (FastMCP)](https://github.com/modelcontextprotocol/python-sdk) · `httpx`.

## License

[MIT](LICENSE). Not affiliated with smallcase. See the notice at the top of this file and in the LICENSE.
