"""Fetch real XBRL numeric facts from SEC EDGAR (public domain) into a local cache.

We pull each company's annual ('CY####' frame) values for a curated set of income-
statement line-item concepts. Framed facts are SEC's canonical, de-duplicated value
for a concept in a period, so each annual snapshot is coherent without restatement
noise. Output: data/sec_records.jsonl, one record per (company, fiscal year) with a
list of (real label, real value) line items -- the substrate for injected-error audit
scenarios (scenarios_sec.py).

    python -m supercute.fetch_sec --companies 40        # polite, ~10 req/s, UA required
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import time
import urllib.request

UA = "SUPERCUTE benchmark research skirdey@gmail.com"
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "data", "sec_records.jsonl")

# curated income-statement / expense line-item concepts (us-gaap, monetary USD)
CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
    "CostOfGoodsAndServicesSold", "CostOfRevenue", "GrossProfit",
    "ResearchAndDevelopmentExpense", "SellingGeneralAndAdministrativeExpense",
    "SellingAndMarketingExpense", "GeneralAndAdministrativeExpense",
    "OperatingExpenses", "CostsAndExpenses", "OperatingIncomeLoss",
    "InterestExpense", "IncomeTaxExpenseBenefit", "NetIncomeLoss",
    "DepreciationDepletionAndAmortization", "MarketingExpense",
]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def _tickers(n, skip):
    d = _get("https://www.sec.gov/files/company_tickers.json")
    rows = list(d.values())
    return rows[skip:skip + n]


def _company_records(cik, name):
    try:
        facts = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    except Exception as e:
        print(f"  ! {name}: {e}", flush=True)
        return []
    usg = facts.get("facts", {}).get("us-gaap", {})
    frames = collections.defaultdict(dict)            # 'CY2019' -> {label: val}
    for con in CONCEPTS:
        node = usg.get(con)
        if not node:
            continue
        label = node.get("label") or con
        for unit, arr in node.get("units", {}).items():
            if unit != "USD":
                continue
            for f in arr:
                fr = f.get("frame")
                if fr and len(fr) == 6 and fr.startswith("CY") and isinstance(f.get("val"), int):
                    frames[fr].setdefault(label, f["val"])
    out = []
    for fr, items in frames.items():
        if len(items) >= 5:
            out.append({"company": name, "cik": cik, "frame": fr,
                        "items": [[lbl, v] for lbl, v in items.items()]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", type=int, default=40)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.15)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    rows = _tickers(args.companies, args.skip)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    n_rec = 0
    with open(args.out, "a", encoding="utf-8") as fh:
        for i, row in enumerate(rows, 1):
            cik, name = row["cik_str"], row["title"]
            recs = _company_records(cik, name)
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n_rec += len(recs)
            print(f"[{i}/{len(rows)}] {name:40.40s} -> {len(recs)} annual records", flush=True)
            time.sleep(args.delay)
    print(f"\nwrote {n_rec} records -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
