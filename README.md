# sec-xbrl-revenue-tags

**One clean revenue (and 15 other key financials) series per company from SEC XBRL, even when the company
changed tags.** A JSON map of which `us-gaap` / `ifrs-full` concepts mean the same thing, plus a small
zero-dependency Python helper that applies it to EDGAR's free `companyfacts` API.

## The problem

Ask EDGAR for "revenue" and you'll find it under different tags depending on the company and the year:

```
2013-01-31  468,651,000,000  us-gaap:Revenues
2016-01-31  482,130,000,000  us-gaap:Revenues
2017-01-31  481,317,000,000  us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax   <- ASC 606 switch
2026-01-31  706,413,000,000  us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax
```
(Walmart, `python -m xbrl_key_financials WMT -m Revenue`.) Query one tag and you get a series with a hole in it.
Others in use: `SalesRevenueNet`, `RevenueFromContractWithCustomerIncludingAssessedTax`, and `ifrs-full:Revenue` for
foreign filers. Cost of revenue, net income, debt and cash flow have the same issue.

## The map

[`xbrl_key_financials/tags.json`](xbrl_key_financials/tags.json): 16 metrics, concepts in order of preference.

| Metric | Concepts (first one with a value wins, per period) |
|---|---|
| Revenue | RevenueFromContractWithCustomerExcludingAssessedTax, Revenues, SalesRevenueNet, RevenueFromContractWithCustomerIncludingAssessedTax, ifrs-full:Revenue |
| CostOfRevenue | CostOfRevenue, CostOfGoodsAndServicesSold, CostOfGoodsSold, ifrs-full:CostOfSales |
| GrossProfit | GrossProfit, ifrs-full:GrossProfit |
| ResearchAndDevelopment | ResearchAndDevelopmentExpense |
| OperatingIncome | OperatingIncomeLoss, ifrs-full:ProfitLossFromOperatingActivities |
| NetIncome | NetIncomeLoss, ProfitLoss, ifrs-full:ProfitLoss |
| EpsBasic / EpsDiluted | EarningsPerShareBasic / Diluted, ifrs-full equivalents |
| TotalAssets / TotalLiabilities / StockholdersEquity | Assets / Liabilities / StockholdersEquity, ifrs-full equivalents |
| CashAndEquivalents | CashAndCashEquivalentsAtCarryingValue, ifrs-full:CashAndCashEquivalents |
| LongTermDebt | LongTermDebtNoncurrent, LongTermDebt |
| OperatingCashFlow | NetCashProvidedByUsedInOperatingActivities, ifrs-full:CashFlowsFromUsedInOperatingActivities |
| CapitalExpenditure | PaymentsToAcquirePropertyPlantAndEquipment, ifrs-full:PurchaseOfPropertyPlantAndEquipment... |
| SharesOutstanding | dei:EntityCommonStockSharesOutstanding |

(us-gaap prefix omitted where obvious.) Use the JSON from any language.

## The helper

```bash
pip install git+https://github.com/OlsOls4/sec-xbrl-revenue-tags
export SEC_USER_AGENT="Your Name you@example.com"   # the SEC requires a contact in the User-Agent

xbrl-key-financials AAPL -m Revenue -m NetIncome             # JSON
xbrl-key-financials 320193 --period quarterly --csv > aapl.csv
xbrl-key-financials --tags                                    # print the map
```

```python
from xbrl_key_financials import company_facts, key_financials, series

facts = company_facts("MSFT")                    # one request to data.sec.gov
print(series(facts, "Revenue"))                  # {"2010-06-30": 62484000000, ..., period_end: value}
rows = key_financials(facts, period="annual")    # all 16 metrics, one row per metric/unit/period
```

Rules it applies:
- **Per period, the highest-preference tag wins**, so comparatives re-reported under a new tag replace the old one.
- **Within one tag, the latest filing wins**, so restatements (10-K/A) replace the original.
- `annual` = durations of 340–380 days (plus balance-sheet instants from FY filings); `quarterly` = 80–100 days.
  Q4 is rarely filed as its own fact: derive it as FY − Q1 − Q2 − Q3 if you need it.
- **Gotcha:** in companyfacts, `fy`/`fp` belong to the *filing*, not the period (a FY2024 10-K reports FY2023 comparatives
  with `fy=2024`). Rows here carry `period_end` and `fiscal_year_end` (from the period end) instead.

## Need filings, many companies, or a schedule?

This repo covers the tag mapping. For full filings lists (10-K, 10-Q, 8-K, 13F...), document links, company
profiles, these key financials for many companies at once, daily new-filing monitoring, and exports to
CSV/Excel/Sheets or n8n/Make, there's a hosted **[SEC EDGAR Filings & XBRL Financials API on Apify](https://apify.com/olsols4/sec-edgar-filings-financials)**,
also callable by AI agents over MCP (`https://mcp.apify.com?tools=olsols4/sec-edgar-filings-financials`).
Pay per use, no subscription.

## Tests

```bash
python -m unittest discover -s tests -v                                  # offline, synthetic data
SEC_USER_AGENT="Name you@example.com" python -m unittest discover -s tests # also hits data.sec.gov
```

## Licence

MIT. Data comes from the SEC's public APIs; follow the SEC's [fair access rules](https://www.sec.gov/os/accessing-edgar-data) (≤10 requests/second, a User-Agent with contact details). Not investment advice.
