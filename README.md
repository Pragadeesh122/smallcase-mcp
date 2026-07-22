# smallcase-mcp

An **unofficial, read-only** [MCP](https://modelcontextprotocol.io) server that exposes
[smallcase](https://www.smallcase.com)'s **public** discovery data — the catalog of
published smallcases, their returns, risk metrics, rationale and rebalance schedule —
to any LLM or agent (Claude Desktop, Claude Code, Cursor, …).

No API key. No browser. No login. Just clean HTTP over the endpoints the public
smallcase.com website already calls for logged-out visitors.

> ⚠️ **Disclaimer — read this.** This project is **not affiliated with, authorized by,
> or endorsed by smallcase.** It is not the official
> [smallcase Gateway](https://developers.gateway.smallcase.com) API. It calls
> smallcase's public website endpoints, which can change or break at any time, and
> some data (notably **past returns**) is presented in smallcase's own UI behind a
> consent step ("as per applicable guidelines"). Use it for personal research at your
> own discretion, and do not rely on it as financial advice or as an official data
> source. All data © smallcase / the respective publishers.

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
| `list_managers(page, page_size)` | List smallcase publishers / research houses. |

Example prompts once connected: *"find low-volatility gold smallcases under ₹5000"*,
*"compare SCET_0005 and the top smallcase by returns"*, *"what's the rationale behind SCET_0005?"*

## Setup

```bash
uv sync
```

Verify it talks to the live API:

```bash
uv run python tests/test_live.py
```

## Use it from an MCP client

Run over stdio:

```bash
uv run smallcase-mcp
```

### Claude Desktop / Claude Code config

```json
{
  "mcpServers": {
    "smallcase": {
      "command": "uv",
      "args": ["--directory", "/Users/pragadeesh/Developer/Loops", "run", "smallcase-mcp"]
    }
  }
}
```

## Stack

Python 3.11+ · [MCP Python SDK (FastMCP)](https://github.com/modelcontextprotocol/python-sdk) · `httpx`.
