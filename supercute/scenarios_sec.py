"""SUPERCUTE real-document audit scenarios from SEC EDGAR XBRL data.

Real company + real fiscal year + real Revenue/COGS/R&D/SG&A/Interest/Tax values
(public domain, fetched by fetch_sec.py). We reconstruct an income statement whose
derived rows (Gross Profit, Operating Income, Net Income, ...) are computed by OUR
arithmetic from the real leaf values -- so ground truth is exact even though reported
aggregates in real filings include other line items. We then inject known errors into
the computed rows. Output: audit scenarios (judge-graded, like scenarios_audit.py).

Difficulty is real: verifying these rows means adding/subtracting 10-12 digit numbers
a tokenizer model cannot see digit-by-digit.
"""
from __future__ import annotations

import json
import os
import random

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sec_records.jsonl")

# leaf concepts we combine, by priority of label match
_REV = ("Revenues", "Revenue from Contract with Customer, Excluding Assessed Tax")
_COGS = ("Cost of Revenue", "Cost of Goods and Services Sold")
_RND = ("Research and Development Expense",)
_SGA = ("Selling, General and Administrative Expense",)
_INT = ("Interest Expense",)
_TAX = ("Income Tax Expense (Benefit)",)


def _load():
    recs = []
    if not os.path.exists(_PATH):
        return recs
    for line in open(_PATH, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        d = {lbl: v for lbl, v in r["items"]}
        rev = _first(d, _REV)
        cogs = _first(d, _COGS)
        if rev is None or cogs is None:           # need at least Revenue & COGS
            continue
        recs.append({"company": r["company"], "frame": r["frame"], "d": d,
                     "rev": rev, "cogs": cogs,
                     "rnd": _first(d, _RND), "sga": _first(d, _SGA),
                     "interest": _first(d, _INT), "tax": _first(d, _TAX)})
    return recs


def _first(d, labels):
    for l in labels:
        if l in d and isinstance(d[l], int):
            return d[l]
    return None


_RECORDS = _load()


def _usd(v):
    return ("-" if v < 0 else "") + "$" + format(abs(v), ",")


def _corrupt(rng, v):
    """Flip ONE significant digit, preserving magnitude and trailing zeros -> a subtle,
    realistic typo ($10,733M -> $10,723M) that can only be caught by exact digit-level
    arithmetic, not by an order-of-magnitude eyeball."""
    s = str(abs(v))
    nz = len(s.rstrip("0")) or 1
    # bias toward the LOW-order significant digits: a small dollar delta in a huge
    # number that only exact digit-level arithmetic can catch (not an eyeball).
    lo = max(1, nz - 3)
    i = rng.randint(lo, nz - 1) if nz >= 2 else 0
    new = rng.choice([c for c in "0123456789" if c != s[i] and not (i == 0 and c == "0")])
    cand = int(s[:i] + new + s[i + 1:])
    return -cand if v < 0 else cand


def sec_income_audit(rng):
    r = rng.choice(_RECORDS)
    rev, cogs = r["rev"], r["cogs"]
    yr = r["frame"][2:]

    # which derived rows will exist, given available leaves
    keys = ["gp"]
    if r["rnd"] is not None or r["sga"] is not None:
        keys.append("opex")
    keys.append("opinc")
    if r["interest"] is not None:
        keys.append("pretax")
    if r["tax"] is not None:
        keys.append("net")
    target = min(rng.choice([0, 1, 1, 2, 2, 3]), len(keys))
    bad = set(rng.sample(keys, target))

    # build rows top-down; every derived row is computed from the PRINTED values above
    # it, so a non-corrupted row stays internally consistent even if an input is wrong.
    rows, errors = [("Revenue", rev, False), ("Cost of Revenue", cogs, False)], []

    def derived(label, key, true_val):
        val = _corrupt(rng, true_val) if key in bad else true_val
        rows.append((label, val, True))
        if key in bad:
            errors.append(f"{label} is shown as {_usd(val)} but should be {_usd(true_val)}.")
        return val

    p_gp = derived("Gross Profit", "gp", rev - cogs)
    p_opinc_input = p_gp
    if "opex" in keys:
        parts = []
        if r["rnd"] is not None:
            rows.append(("Research & Development", r["rnd"], False)); parts.append(r["rnd"])
        if r["sga"] is not None:
            rows.append(("Selling, General & Administrative", r["sga"], False)); parts.append(r["sga"])
        p_opex = derived("Total Operating Expenses", "opex", sum(parts))
        p_opinc_input = p_gp - p_opex
    p_opinc = derived("Operating Income", "opinc", p_opinc_input)
    p_pretax_input = p_opinc
    if "pretax" in keys:
        rows.append(("Interest Expense", r["interest"], False))
        p_pretax = derived("Pre-Tax Income", "pretax", p_opinc - r["interest"])
        p_pretax_input = p_pretax
    if "net" in keys:
        rows.append(("Income Tax", r["tax"], False))
        derived("Net Income", "net", p_pretax_input - r["tax"])

    md = [f"# {r['company']} — Consolidated Statement of Operations (FY{yr}, USD)\n",
          "| Line Item | Amount |", "|-----------|-------:|"]
    for label, val, _ in rows:
        bold = "**" if label in ("Gross Profit", "Operating Income", "Net Income") else ""
        md.append(f"| {bold}{label}{bold} | {bold}{_usd(val)}{bold} |")
    doc = "\n".join(md)

    rule = ("Gross Profit = Revenue − Cost of Revenue; Total Operating Expenses = R&D + SG&A; "
            "Operating Income = Gross Profit − Total Operating Expenses; Pre-Tax Income = Operating "
            "Income − Interest Expense; Net Income = Pre-Tax Income − Income Tax")
    prompt = (f"You are a meticulous financial auditor. The following income statement was generated "
              f"automatically and may contain arithmetic errors ({rule}). Each subtotal is derived only "
              f"from the line items printed above it. Check every derived value against the printed numbers "
              f"and report EVERY inconsistency, naming the line and what it should be. If everything is "
              f"consistent, say no errors were found.\n\n{doc}")
    return dict(task="sec_income_audit", kind="audit", prompt=prompt, errors=errors,
                answer=("; ".join(errors) if errors else "no errors"),
                meta={"n_errors": len(errors), "company": r["company"], "frame": r["frame"]})


TASKS = {f.__name__: f for f in [sec_income_audit]} if _RECORDS else {}
