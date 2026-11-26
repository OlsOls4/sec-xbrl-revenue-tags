"""python -m xbrl_key_financials AAPL [--metric Revenue] [--period annual] [--csv] --user-agent "Name email" """
from __future__ import annotations

import argparse
import csv
import json
import sys

from . import TAGS, company_facts, key_financials


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="xbrl-key-financials",
                                description="Key financials from SEC XBRL with the tag mess merged into one series.")
    p.add_argument("company", nargs="?", help="Ticker (AAPL) or CIK (320193)")
    p.add_argument("-m", "--metric", action="append", choices=list(TAGS), help="Repeatable. Default: all 16")
    p.add_argument("--period", default="annual", choices=["annual", "quarterly", "all"])
    p.add_argument("--csv", action="store_true", help="CSV instead of JSON")
    p.add_argument("--user-agent", help="'Your Name you@example.com' (or set SEC_USER_AGENT)")
    p.add_argument("--tags", action="store_true", help="Just print the metric -> tag map and exit")
    a = p.parse_args(argv)
    if a.tags:
        print(json.dumps(TAGS, indent=2))
        return 0
    if not a.company:
        p.error("company is required (ticker or CIK)")
    facts = company_facts(a.company, a.user_agent)
    rows = key_financials(facts, a.metric, a.period)
    if a.csv:
        w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]) if rows else ["metric"])
        w.writeheader()
        w.writerows(rows)
    else:
        print(json.dumps({"company": facts.get("entityName"), "cik": facts.get("cik"), "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
