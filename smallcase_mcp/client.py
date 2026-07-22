"""HTTP client for smallcase's public (unofficial) endpoints.

Every endpoint used here is one the public smallcase.com website calls for a
logged-out visitor, and none require authentication. This is NOT the official
smallcase Gateway API, and this project is not affiliated with or endorsed by
smallcase.

Deliberately out of reach (gated by smallcase, not exposed here):
  - constituents / holdings + weights  -> require an authenticated, entitled session
  - a user's personal portfolio        -> requires login
"""

from __future__ import annotations

import asyncio
import html
import re
from typing import Any

import httpx

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: Any) -> str | None:
    """Turn smallcase's HTML rationale/methodology blobs into plain text."""
    if not value or not isinstance(value, str):
        return None
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip() or None

BASE = "https://api.smallcase.com"

# The public endpoints are the website's own backend, so we present as the
# website (UA + origin/referer) to avoid being rejected for looking like a bot.
_HEADERS = {
    "accept": "application/json",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "origin": "https://www.smallcase.com",
    "referer": "https://www.smallcase.com/",
}

_TIMEOUT = httpx.Timeout(20.0)


class SmallcaseError(RuntimeError):
    """Any failure talking to the smallcase public API."""


async def _get(path: str, params: dict[str, Any] | None = None) -> dict:
    url = f"{BASE}{path}"
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as http:
        try:
            resp = await http.get(url, params=params)
        except httpx.HTTPError as exc:  # network/timeout/DNS
            raise SmallcaseError(f"request to {path} failed: {exc}") from exc
    if resp.status_code != 200:
        raise SmallcaseError(
            f"{path} -> HTTP {resp.status_code}: {resp.text[:200]}"
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise SmallcaseError(f"{path} -> non-JSON response: {resp.text[:200]}") from exc


def _clamp_page_size(page_size: int) -> int:
    return min(max(int(page_size), 1), 50)


# Applied to every search so we only get real, published, active smallcases
# (without these the discovery endpoint also returns internal/test entries).
_MANDATORY_FILTERS: list[dict] = [
    {"key": "channel", "operator": "includes", "values": ["smallcase-website"]},
    {"key": "operationKeys.sc_active", "operator": "boolean", "value": True},
    {"key": "operationKeys.sc_blocked", "operator": "boolean", "value": False},
    {"key": "operationKeys.sc_state", "operator": "excludes", "values": ["BLOCKED", "PLAYEDOUT"]},
    {"key": "operationKeys.sc_status", "operator": "includes", "values": ["PUBLISHED"]},
    {"key": "operationKeys.sc_assetUniverse", "operator": "excludes", "values": ["US"]},
]

_VOLATILITY_MAP = {
    "low": "LOW_VOLATILITY",
    "medium": "MEDIUM_VOLATILITY",
    "med": "MEDIUM_VOLATILITY",
    "high": "HIGH_VOLATILITY",
}

# Server-side sorts (validated). "returns" is handled client-side by CAGR because
# the API's RETURNS_SORT is a no-op on this endpoint.
_SORT_MAP: dict[str, dict | None] = {
    "popularity": None,
    "min_amount": {"key": "operationKeys.sc_minInvestAmount", "operator": "asc"},
    "recently_rebalanced": {"key": "operationKeys.sc_lastRebalanced", "operator": "desc"},
    "returns": None,
}

_SEARCH_SCAN_PAGES = 6  # cap network calls when text/amount filtering client-side
_SEARCH_PAGE_SIZE = 40  # the discover endpoint rejects pageSize > 40 with HTTP 422


# --------------------------------------------------------------------------- #
# search_smallcases
# --------------------------------------------------------------------------- #
def _shape_list_item(it: dict) -> dict:
    return {
        "scid": it.get("scid"),
        "name": it.get("name"),
        "slug": it.get("slug"),
        "publisher": it.get("publisherName"),
        "description": it.get("description"),
        "cagr": it.get("cagr"),
        "cagr_duration": it.get("cagrDuration"),
        "min_investment": it.get("minInvestmentAmount"),
        "volatility": it.get("volatility"),
        "monthly_subscription_price": it.get("lowestScSubsPricePM"),
        "constituents_count": it.get("constituentsCount"),
        "launch_date": it.get("launchDate"),
        "asset_class": it.get("assetClass"),
        "currency": it.get("currency"),
    }


def _matches(
    it: dict, query: str, min_amount: float | None, max_amount: float | None
) -> bool:
    if query:
        haystack = " ".join(
            str(it.get(k) or "")
            for k in ("name", "description", "publisherName")
        ).lower()
        if query not in haystack:
            return False
    amount = it.get("minInvestmentAmount")
    if min_amount is not None and (amount is None or amount < min_amount):
        return False
    if max_amount is not None and (amount is None or amount > max_amount):
        return False
    return True


async def search_smallcases(
    query: str | None = None,
    volatility: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    sort: str = "popularity",
    limit: int = 20,
) -> dict:
    """Search published smallcases with optional text, volatility, amount and sort.

    Server-side: mandatory published/active filters, volatility filter, and sort.
    Client-side: `query` substring match (name/description/publisher), amount range,
    and returns-sort. Scans up to a few pages to fill `limit` when filtering.
    """
    sort = (sort or "popularity").lower()
    if sort not in _SORT_MAP:
        raise SmallcaseError(f"sort must be one of {list(_SORT_MAP)}")

    filters = [dict(f) for f in _MANDATORY_FILTERS]
    if volatility:
        mapped = _VOLATILITY_MAP.get(volatility.lower())
        if not mapped:
            raise SmallcaseError("volatility must be 'low', 'medium', or 'high'")
        filters.append(
            {"key": "operationKeys.sc_volatility", "operator": "includes", "values": [mapped]}
        )

    import json as _json

    filter_params = [_json.dumps(f) for f in filters]
    sort_obj = _SORT_MAP[sort]
    q = (query or "").lower().strip()
    limit = _clamp_page_size(limit)

    collected: list[dict] = []
    client_side = bool(q or min_amount is not None or max_amount is not None or sort == "returns")
    for page in range(1, _SEARCH_SCAN_PAGES + 1):
        params: dict[str, Any] = {
            "asset": "smallcase",
            "pageNo": page,
            "pageSize": _SEARCH_PAGE_SIZE,
            "useSemantic": "false",
            "filters": list(filter_params),
        }
        if sort_obj:
            params["sort"] = _json.dumps(sort_obj)
        data = await _get("/explore/discover/v1/smallcase", params)
        items = (data.get("data") or {}).get("items") or []
        if not items:
            break
        collected.extend(it for it in items if _matches(it, q, min_amount, max_amount))
        if not client_side and len(collected) >= limit:
            break
        if sort != "returns" and len(collected) >= limit:
            break

    if sort == "returns":
        collected.sort(key=lambda it: (it.get("cagr") is None, -(it.get("cagr") or 0.0)))

    result = collected[:limit]
    return {
        "count": len(result),
        "filters": {
            "query": query,
            "volatility": volatility,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "sort": sort,
        },
        "smallcases": [_shape_list_item(it) for it in result],
    }


# --------------------------------------------------------------------------- #
# get_smallcase
# --------------------------------------------------------------------------- #
def _shape_detail(d: dict, scid: str) -> dict:
    info = d.get("info") or {}
    stats = d.get("stats") or {}
    returns = stats.get("returns") or {}
    ratios = stats.get("ratios") or {}
    return {
        "scid": d.get("scid") or scid,
        "name": info.get("name"),
        "publisher": info.get("publisherName"),
        "type": info.get("type"),
        "short_description": info.get("shortDescription"),
        "launched": info.get("uploaded"),
        "last_updated": info.get("updated"),
        "next_rebalance_update": info.get("nextUpdate"),
        "min_investment": stats.get("minInvestAmount"),
        "index_value": stats.get("indexValue"),
        "returns": {
            "1D": returns.get("daily"),
            "1W": returns.get("weekly"),
            "1M": returns.get("monthly"),
            "3M": returns.get("quarterly"),
            "6M": returns.get("halfyearly"),
            "1Y": returns.get("yearly"),
            "3Y": returns.get("threeYear"),
            "5Y": returns.get("fiveYear"),
            "since_inception": returns.get("sinceInception"),
        },
        "risk": {
            "risk_label": ratios.get("riskLabel"),
            "risk": ratios.get("risk"),
            "sharpe": ratios.get("sharpe"),
            "beta": ratios.get("beta"),
            "pe": ratios.get("pe"),
            "pb": ratios.get("pb"),
            "div_yield": ratios.get("divYield"),
            "large_cap_pct": ratios.get("largeCapPercentage"),
            "mid_cap_pct": ratios.get("midCapPercentage"),
            "small_cap_pct": ratios.get("smallCapPercentage"),
            "52w_high": ratios.get("52wHigh"),
            "52w_low": ratios.get("52wLow"),
        },
        "rationale": _strip_html(d.get("rationale")),
        "methodology": [
            {
                "label": step.get("label"),
                "content": _strip_html(step.get("content")),
                "locked": step.get("locked", False),
            }
            for step in (d.get("methodology") or [])
            if isinstance(step, dict)
        ],
        "constituents_count": d.get("constituentsCount"),
        "constituents": d.get("constituents") or [],
        "_constituents_note": (
            "Holdings/weights are gated by smallcase and only populate for an "
            "authenticated, entitled session; empty here by design."
        ),
    }


async def get_smallcase(scid: str) -> dict:
    """Full public detail for one smallcase by its SCID (e.g. 'SCET_0005')."""
    if not scid or not isinstance(scid, str):
        raise SmallcaseError("scid must be a non-empty string, e.g. 'SCET_0005'")
    data = await _get("/sam/smallcases/v2", {"scid": scid})
    d = data.get("data") or data
    return _shape_detail(d, scid)


# --------------------------------------------------------------------------- #
# compare_smallcases
# --------------------------------------------------------------------------- #
async def compare_smallcases(scids: list[str]) -> dict:
    """Side-by-side of returns / risk / min-investment for 2-5 smallcases."""
    if not scids or len(scids) < 2:
        raise SmallcaseError("provide at least 2 SCIDs to compare")
    scids = scids[:5]
    results = await asyncio.gather(
        *(get_smallcase(s) for s in scids), return_exceptions=True
    )
    rows = []
    for scid, res in zip(scids, results):
        if isinstance(res, Exception):
            rows.append({"scid": scid, "error": str(res)})
            continue
        rows.append(
            {
                "scid": res["scid"],
                "name": res["name"],
                "publisher": res["publisher"],
                "min_investment": res["min_investment"],
                "returns": res["returns"],
                "risk_label": res["risk"]["risk_label"],
                "sharpe": res["risk"]["sharpe"],
            }
        )
    return {"comparison": rows}


# --------------------------------------------------------------------------- #
# list_managers
# --------------------------------------------------------------------------- #
def _shape_manager(it: dict) -> dict:
    strategies = it.get("investmentStrategy") or []
    return {
        "id": it.get("publisher"),
        "name": it.get("publisherDisplayName"),
        "description": it.get("description"),
        "total_smallcases": it.get("totalSmallcases"),
        "paid_smallcases": it.get("paidSmallcases"),
        "sebi_reg_number": it.get("sebiRegNumber"),
        "pricing_type": it.get("pricingType"),
        "investment_strategy": [
            s.get("displayName") for s in strategies if isinstance(s, dict)
        ],
    }


async def list_managers(page: int = 1, page_size: int = 20) -> dict:
    """List smallcase publishers / managers (research houses) from public data."""
    params: dict[str, Any] = {
        "asset": "manager",
        "pageNo": int(page),
        "pageSize": _clamp_page_size(page_size),
        "useSemantic": "false",
    }
    data = await _get("/explore/discover/v1/manager", params)
    payload = data.get("data") or {}
    items = payload.get("items") or []
    return {"count": len(items), "managers": [_shape_manager(it) for it in items]}
