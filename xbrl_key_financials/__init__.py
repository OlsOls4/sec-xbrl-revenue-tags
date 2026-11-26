"""Merge the many XBRL tags companies use for the same number into one clean series.

Data source: SEC EDGAR's free companyfacts API (https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json).
The SEC asks every client to send a User-Agent with a name and contact email, and to stay under 10 requests/second.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import urllib.request
from datetime import date
from importlib import resources

__version__ = "0.1.0"

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


def load_tags() -> dict:
    """{metric: {"concepts": ["us-gaap:...", ...], "note": "..."}} from the bundled tags.json."""
    with resources.files(__package__).joinpath("tags.json").open("r", encoding="utf-8") as f:
        return json.load(f)["metrics"]


TAGS = load_tags()


def _get(url: str, user_agent: str | None) -> dict:
    ua = user_agent or os.environ.get("SEC_USER_AGENT")
    if not ua or "@" not in ua:
        raise ValueError("The SEC requires a User-Agent with contact details, e.g. 'Jane Doe jane@example.com'. "
                         "Pass user_agent=... or set SEC_USER_AGENT.")
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw)


def resolve_cik(ref: str | int, user_agent: str | None = None) -> int:
    """CIK from a CIK number ('320193', 'CIK0000320193') or a ticker ('AAPL', 'BRK.B')."""
    s = str(ref).strip()
    m = re.fullmatch(r"(?:CIK)?0*(\d{1,10})", s, re.I)
    if m:
        return int(m.group(1))
    want = s.upper().replace(".", "-")
    for row in _get(TICKERS_URL, user_agent).values():
        if row["ticker"].upper() == want:
            return int(row["cik_str"])
    raise ValueError(f"Unknown ticker {ref!r}")


def company_facts(ref: str | int, user_agent: str | None = None) -> dict:
    """Download the full companyfacts JSON for a ticker or CIK."""
    return _get(FACTS_URL.format(cik=resolve_cik(ref, user_agent)), user_agent)


def _days(a, b):
    try:
        return (date.fromisoformat(b) - date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return None


def _period_ok(v: dict, period: str) -> bool:
    dur = _days(v.get("start"), v.get("end")) if v.get("start") else None
    if period == "annual":
        return (dur is None and v.get("fp") == "FY") or (dur is not None and 340 <= dur <= 380)
    if period == "quarterly":
        return dur is not None and 80 <= dur <= 100
    return True


def key_financials(facts: dict, metrics=None, period: str = "annual", tags: dict | None = None) -> list[dict]:
    """One row per (metric, unit, period), whichever XBRL tag the company used.

    For each period the first concept in the preference list that has a value wins; within one concept the
    most recently filed value wins (restatements). period: "annual", "quarterly" (3-month durations only;
    Q4 is usually not filed separately) or "all".
    Note: companyfacts' `fy`/`fp` describe the *filing*, not the period, so 10-K comparatives carry the
    later year. Use `period_end` / `fiscal_year_end` here instead.
    """
    tags = tags or TAGS
    data = facts.get("facts") or {}
    best: dict[tuple, dict] = {}
    for metric in metrics or tags:
        for rank, qualified in enumerate(tags[metric]["concepts"]):
            tax, concept = qualified.split(":", 1)
            node = data.get(tax, {}).get(concept)
            if not node:
                continue
            for unit, values in (node.get("units") or {}).items():
                for v in values:
                    if not _period_ok(v, period):
                        continue
                    row = {"metric": metric, "concept": qualified, "unit": unit, "value": v.get("val"),
                           "period_start": v.get("start"), "period_end": v.get("end"),
                           "fiscal_year_end": int(v["end"][:4]) if v.get("end") else None,
                           "form": v.get("form"), "filed": v.get("filed"), "accession": v.get("accn"),
                           "_rank": rank}
                    key = (metric, unit, v.get("start"), v.get("end"))
                    cur = best.get(key)
                    if (cur is None or rank < cur["_rank"]
                            or (rank == cur["_rank"] and (row["filed"] or "") > (cur["filed"] or ""))):
                        best[key] = row
    rows = sorted(best.values(), key=lambda r: (r["metric"], r["unit"], r["period_end"] or "", r["period_start"] or ""))
    for r in rows:
        del r["_rank"]
    return rows


def series(facts: dict, metric: str = "Revenue", period: str = "annual", unit: str | None = None) -> dict:
    """{period_end: value} for one metric, e.g. series(facts, "Revenue") -> {"2023-09-30": 383285000000, ...}."""
    rows = [r for r in key_financials(facts, [metric], period) if unit is None or r["unit"] == unit]
    if unit is None and rows:
        units = {r["unit"] for r in rows}
        unit = "USD" if "USD" in units else sorted(units)[0]
        rows = [r for r in rows if r["unit"] == unit]
    return {r["period_end"]: r["value"] for r in rows}


__all__ = ["TAGS", "load_tags", "resolve_cik", "company_facts", "key_financials", "series"]
