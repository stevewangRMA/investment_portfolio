#!/usr/bin/env python3
"""
Fetch portfolio data from IBKR Flex Web Service and write portfolio.json.

Required env vars:
  IBKR_FLEX_TOKEN     - Flex Web Service token (Client Portal > Settings > Flex Web Service)
  IBKR_FLEX_QUERY_ID  - ID of the Flex Query to run

The Flex Query must include (XML format, period: Last 365 Calendar Days):
  - "Equity Summary in Base by Report Date" (fields: Report Date, Total)
  - "Open Positions" (fields: Symbol, Description, Quantity, Mark Price,
     Position Value, Fifo Pnl Unrealized, Cost Basis Money)

Uses stdlib only - no pip installs needed.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "portfolio.json")
UA = {"User-Agent": "portfolio-site/1.0"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def request_statement(token: str, query_id: str) -> str:
    """Step 1: request generation, return reference code."""
    url = f"{BASE}/SendRequest?t={urllib.parse.quote(token)}&q={query_id}&v=3"
    root = ET.fromstring(get(url))
    status = (root.findtext("Status") or "").strip()
    if status != "Success":
        raise RuntimeError(f"SendRequest failed: {ET.tostring(root, encoding='unicode')[:500]}")
    return root.findtext("ReferenceCode").strip()


def fetch_statement(token: str, ref_code: str) -> ET.Element:
    """Step 2: poll until the statement is ready."""
    url = f"{BASE}/GetStatement?t={urllib.parse.quote(token)}&q={ref_code}&v=3"
    for attempt in range(12):
        time.sleep(10 if attempt else 5)
        body = get(url)
        root = ET.fromstring(body)
        if root.tag == "FlexQueryResponse":
            return root
        # Error 1019 = statement generation in progress; keep polling
        code = root.findtext("ErrorCode") or ""
        if code not in ("1019", "1021", "1001"):
            raise RuntimeError(f"GetStatement failed: {body[:500]}")
    raise RuntimeError("Statement not ready after 2 minutes of polling")


def f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def parse(root: ET.Element) -> dict:
    # NAV time series. IBKR has renamed this section over time
    # ("Equity Summary in Base by Report Date" -> "Net Asset Value (NAV) in Base"),
    # so accept any element carrying reportDate + total attributes.
    series = []
    for row in root.iter():
        date = row.get("reportDate", "")
        nav = f(row.get("total"))
        if date and nav:
            # normalize YYYYMMDD -> YYYY-MM-DD
            if len(date) == 8 and date.isdigit():
                date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            series.append({"date": date, "nav": round(nav, 2)})
    series.sort(key=lambda x: x["date"])
    # de-duplicate dates (keep last value per date)
    dedup = {}
    for p in series:
        dedup[p["date"]] = p
    series = sorted(dedup.values(), key=lambda x: x["date"])

    # Open positions (attribute names vary slightly across query configs)
    def attr(row, *names):
        for n in names:
            v = row.get(n)
            if v not in (None, ""):
                return v
        return None

    positions = []
    for row in root.iter("OpenPosition"):
        qty = f(attr(row, "position", "quantity"))
        value = f(attr(row, "positionValue", "value", "markValue"))
        pnl = f(attr(row, "fifoPnlUnrealized", "unrealizedPnl"))
        cost = f(attr(row, "costBasisMoney", "costBasis"))
        positions.append({
            "symbol": row.get("symbol", ""),
            "name": row.get("description", ""),
            "qty": qty,
            "price": f(attr(row, "markPrice", "price")),
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnlPct": round(pnl / cost * 100, 2) if cost else 0.0,
        })
    # aggregate duplicate symbols (multiple lots)
    agg = {}
    for p in positions:
        a = agg.setdefault(p["symbol"], p)
        if a is not p:
            a["qty"] += p["qty"]
            a["value"] = round(a["value"] + p["value"], 2)
            a["pnl"] = round(a["pnl"] + p["pnl"], 2)
    positions = sorted(agg.values(), key=lambda x: -x["value"])

    if not series:
        raise RuntimeError(
            "No NAV rows found - make sure the Flex Query includes "
            "'Net Asset Value (NAV) in Base' with all fields selected"
        )

    return {
        "updated": series[-1]["date"],
        "currency": "USD",
        "series": series,
        "positions": positions,
    }


def main():
    token = os.environ.get("IBKR_FLEX_TOKEN")
    query_id = os.environ.get("IBKR_FLEX_QUERY_ID")
    if not token or not query_id:
        sys.exit("Missing IBKR_FLEX_TOKEN or IBKR_FLEX_QUERY_ID env vars")

    ref = request_statement(token, query_id)
    root = fetch_statement(token, ref)
    data = parse(root)

    with open(os.path.abspath(OUT_PATH), "w") as fh:
        json.dump(data, fh, indent=2)
    print(f"Wrote portfolio.json: {len(data['series'])} NAV points, "
          f"{len(data['positions'])} positions, updated {data['updated']}")


if __name__ == "__main__":
    main()
