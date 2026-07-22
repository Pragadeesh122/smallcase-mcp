"""Live smoke test against smallcase's public API.

Run:  uv run python tests/test_live.py
Exits non-zero if any tool fails. This hits the real network on purpose — it is
the verification loop for the MCP, not a hermetic unit test.
"""

from __future__ import annotations

import asyncio
import json
import sys

from smallcase_mcp import client


def _ok(label: str, cond: bool, detail: str = "") -> bool:
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))
    return cond


async def main() -> int:
    passed = True

    # 1) search_smallcases (baseline)
    search = await client.search_smallcases(limit=5)
    got = search.get("smallcases") or []
    passed &= _ok("search_smallcases returns items", len(got) > 0, f"{len(got)} items")
    first_scid = got[0]["scid"] if got else None
    if got:
        s0 = got[0]
        passed &= _ok(
            "search item has name+cagr+min_investment",
            bool(s0.get("name")) and s0.get("cagr") is not None and s0.get("min_investment") is not None,
            f"{s0.get('name')} | CAGR={s0.get('cagr')} | min={s0.get('min_investment')}",
        )
        print("      sample:", json.dumps(s0, ensure_ascii=False)[:220])

    # 1b) text query
    q = await client.search_smallcases(query="gold", limit=8)
    qhits = q.get("smallcases") or []
    passed &= _ok(
        "search query='gold' matches only gold smallcases",
        len(qhits) > 0 and all("gold" in (h.get("name", "") + h.get("description", "")).lower() for h in qhits),
        f"{[h.get('name') for h in qhits[:4]]}",
    )

    # 1c) volatility filter
    lv = await client.search_smallcases(volatility="low", limit=8)
    lvhits = lv.get("smallcases") or []
    passed &= _ok(
        "search volatility='low' returns only low-volatility",
        len(lvhits) > 0 and all(h.get("volatility") == "LOW_VOLATILITY" for h in lvhits),
        f"{len(lvhits)} low-vol",
    )

    # 1d) min_amount sort ascending
    cheap = await client.search_smallcases(sort="min_amount", limit=5)
    amts = [h.get("min_investment") for h in (cheap.get("smallcases") or [])]
    passed &= _ok(
        "sort='min_amount' is ascending",
        amts == sorted(a for a in amts if a is not None),
        f"{amts}",
    )

    # 1e) returns sort descending by CAGR
    top = await client.search_smallcases(sort="returns", limit=5)
    cagrs = [h.get("cagr") for h in (top.get("smallcases") or []) if h.get("cagr") is not None]
    passed &= _ok(
        "sort='returns' is descending by CAGR",
        cagrs == sorted(cagrs, reverse=True),
        f"{[round(c, 2) for c in cagrs]}",
    )

    # 2) get_smallcase
    scid = first_scid or "SCET_0005"
    detail = await client.get_smallcase(scid)
    r = detail.get("returns") or {}
    passed &= _ok(
        f"get_smallcase({scid}) has returns",
        any(v is not None for v in r.values()),
        f"1Y={r.get('1Y')} 3Y={r.get('3Y')} 5Y={r.get('5Y')}",
    )
    passed &= _ok(
        "get_smallcase has risk_label",
        bool((detail.get("risk") or {}).get("risk_label")),
        str((detail.get("risk") or {}).get("risk_label")),
    )
    passed &= _ok(
        "get_smallcase has rationale text",
        bool(detail.get("rationale")),
        (detail.get("rationale") or "")[:80],
    )

    # 3) compare_smallcases
    if len(got) >= 2:
        scids = [got[0]["scid"], got[1]["scid"]]
        cmp = await client.compare_smallcases(scids)
        rows = cmp.get("comparison") or []
        passed &= _ok(
            "compare_smallcases returns a row per scid",
            len(rows) == 2 and all("error" not in row for row in rows),
            f"{[row.get('name') for row in rows]}",
        )

    # 4) list_managers
    mgrs = await client.list_managers(page=1, page_size=5)
    mlist = mgrs.get("managers") or []
    passed &= _ok("list_managers returns items", len(mlist) > 0, f"{len(mlist)} managers")
    if mlist:
        m0 = mlist[0]
        passed &= _ok(
            "manager has id+name",
            bool(m0.get("id")) and bool(m0.get("name")),
            f"{m0.get('name')} ({m0.get('id')}) — {m0.get('total_smallcases')} smallcases",
        )
        print("      sample:", json.dumps(m0, ensure_ascii=False)[:220])

    print("\n" + ("ALL PASSED" if passed else "SOME FAILED"))
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except client.SmallcaseError as exc:
        print(f"[FAIL] SmallcaseError: {exc}")
        sys.exit(2)
