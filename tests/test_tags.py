import os
import unittest

from xbrl_key_financials import TAGS, key_financials, series


def fact(val, start, end, filed, fp="FY", form="10-K"):
    return {"val": val, "start": start, "end": end, "filed": filed, "fp": fp, "fy": int(filed[:4]), "form": form,
            "accn": "0000000000-00-000000"}


# Synthetic companyfacts: a company that switched from SalesRevenueNet/Revenues to the ASC 606 tag.
FACTS = {"entityName": "Example Corp", "cik": 1, "facts": {"us-gaap": {
    "SalesRevenueNet": {"units": {"USD": [fact(100, "2015-01-01", "2015-12-31", "2016-02-20")]}},
    "Revenues": {"units": {"USD": [
        fact(110, "2016-01-01", "2016-12-31", "2017-02-20"),
        fact(120, "2017-01-01", "2017-12-31", "2018-02-20"),
        fact(30, "2017-04-01", "2017-06-30", "2017-08-01", fp="Q2", form="10-Q"),
    ]}},
    "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
        fact(121, "2017-01-01", "2017-12-31", "2019-02-20"),   # comparative re-reported under the new tag
        fact(130, "2018-01-01", "2018-12-31", "2019-02-20"),
        fact(140, "2019-01-01", "2019-12-31", "2020-02-20"),
        fact(139, "2019-01-01", "2019-12-31", "2020-05-01", form="10-K/A"),  # restatement, same tag
    ]}},
    "Assets": {"units": {"USD": [{"val": 999, "end": "2019-12-31", "filed": "2020-02-20", "fp": "FY", "form": "10-K"}]}},
}}}


class TagMapTests(unittest.TestCase):
    def test_map_shape(self):
        self.assertEqual(len(TAGS), 16)
        self.assertEqual(TAGS["Revenue"]["concepts"][0], "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")
        for m, spec in TAGS.items():
            for c in spec["concepts"]:
                self.assertRegex(c, r"^(us-gaap|ifrs-full|dei):[A-Za-z]+$", m)

    def test_merged_revenue_series(self):
        self.assertEqual(series(FACTS, "Revenue"), {"2015-12-31": 100, "2016-12-31": 110,
                                                   "2017-12-31": 121, "2018-12-31": 130, "2019-12-31": 139})

    def test_quarterly_and_instant(self):
        q = key_financials(FACTS, ["Revenue"], "quarterly")
        self.assertEqual([(r["value"], r["concept"]) for r in q], [(30, "us-gaap:Revenues")])
        a = key_financials(FACTS, ["TotalAssets"])
        self.assertEqual(a[0]["value"], 999)
        self.assertEqual(a[0]["fiscal_year_end"], 2019)


@unittest.skipUnless(os.environ.get("SEC_USER_AGENT"), "set SEC_USER_AGENT='Name email' to hit the real API")
class LiveTests(unittest.TestCase):
    def test_apple_revenue(self):
        from xbrl_key_financials import company_facts
        s = series(company_facts("AAPL"), "Revenue")
        self.assertGreater(s["2023-09-30"], 3.8e11)
        self.assertGreater(len(s), 10)


if __name__ == "__main__":
    unittest.main()
