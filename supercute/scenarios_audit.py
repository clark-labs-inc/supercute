"""SUPERCUTE document-verification (audit) suite -- the realistic Clark use case.

Clark emits a large markdown report whose arithmetic was computed by an LLM; some
values are wrong. A byte-level verifier must read the whole document and SURFACE
every inconsistency IN NATURAL LANGUAGE. This is a separate track from the
deterministic core: free-text output scored by an LLM judge (see judge.py /
run_audit.py), not grade().

Each generator returns dict(task, kind="audit", prompt, errors=[human-readable
description, ...], answer=summary, meta). Generation guarantees that every value NOT
in `errors` is exactly internally consistent, so any extra inconsistency the
candidate claims is, by construction, a real false positive the judge can count.
All money is integer cents; percentages/means use stated round-half-up rules.
"""
from __future__ import annotations

import math
import random

_ITEMS = ["Steel brackets", "Copper tubing", "Hex bolts M8", "PVC conduit", "Cable ties",
          "Circuit breakers", "Junction boxes", "Wire spool 14AWG", "LED panels", "Relay modules",
          "Gasket set", "Mounting rails", "Surge protectors", "Terminal blocks", "Heat sinks",
          "Ferrite cores", "Solder reels", "Fuse assortment", "Standoff kit", "Ribbon cable",
          "Coolant pump", "Bearing race", "Drive belt", "Flange nut", "O-ring kit", "Bus bar",
          "Contactor", "Thermostat", "Pressure valve", "Sensor array"]
_SECTIONS = ["Electrical", "Plumbing", "Fasteners", "Enclosures", "Controls", "Materials"]
_COMPANIES = ["Northbridge Industrial", "Vance & Cole Supply", "Meridian Components",
              "Atlas Fabrication", "Keystone Distribution"]
_DEPTS = ["Engineering", "Operations", "Marketing", "Research", "Logistics", "Facilities",
          "Quality", "Procurement", "Field Service", "Compliance"]
_REGIONS = ["North America", "EMEA", "LATAM", "APAC", "Nordics", "Benelux", "MENA", "ANZ"]
_ASSAYS = ["Tensile strength", "Viscosity", "pH level", "Conductivity", "Density", "Hardness",
           "Melting point", "Yield stress", "Absorbance", "Turbidity"]


def _rhu(x):                       # round half up (positive values)
    return int(math.floor(x + 0.5))


def _money(c):
    return f"${c // 100:,}.{c % 100:02d}"


def _corrupt(rng, v, lo=1):
    while True:
        d = rng.choice([-1, 1]) * rng.randint(1, 80) * rng.choice([1, 1, 10, 100])
        if v + d >= lo and d != 0:
            return v + d


# ---- 1. financial reconciliation --------------------------------------------

def md_arithmetic_audit(rng):
    nsec = rng.randint(2, 3)
    secs = rng.sample(_SECTIONS, nsec)
    nls = [rng.randint(3, 5) for _ in range(nsec)]
    items = iter(rng.sample(_ITEMS, sum(nls)))
    target = rng.choice([0, 1, 2, 2, 3, 3, 4])

    sections = []
    for s, nl in zip(secs, nls):
        lines = []
        for _ in range(nl):
            qty = rng.randint(2, 40)
            unit = rng.randint(75, 9950)
            lines.append({"item": next(items), "qty": qty, "unit": unit,
                          "correct": qty * unit, "printed": qty * unit})
        sections.append({"name": s, "lines": lines})

    pool = [("line", l, sec) for sec in sections for l in sec["lines"]] \
        + [("sub", sec, None) for sec in sections] + [("grand", None, None)]
    chosen = rng.sample(pool, min(target, len(pool)))
    chosen_ids = {id(c[1]) for c in chosen if c[0] == "line"}
    sub_ids = {id(c[1]) for c in chosen if c[0] == "sub"}
    grand_bad = any(c[0] == "grand" for c in chosen)

    errors = []
    for sec in sections:
        for l in sec["lines"]:
            if id(l) in chosen_ids:
                l["printed"] = _corrupt(rng, l["correct"])
                errors.append(f"In the {sec['name']} section, the '{l['item']}' line: Amount is shown as "
                              f"{_money(l['printed'])} but {l['qty']} x {_money(l['unit'])} = "
                              f"{_money(l['correct'])}.")
    for sec in sections:
        cons = sum(l["printed"] for l in sec["lines"])
        sec["st"] = cons
        if id(sec) in sub_ids:
            sec["st"] = _corrupt(rng, cons)
            errors.append(f"The {sec['name']} section Subtotal is shown as {_money(sec['st'])} but its "
                          f"line amounts sum to {_money(cons)}.")
    gcons = sum(sec["st"] for sec in sections)
    gprint = _corrupt(rng, gcons) if grand_bad else gcons
    if grand_bad:
        errors.append(f"The Grand Total is shown as {_money(gprint)} but the section subtotals sum to "
                      f"{_money(gcons)}.")

    md = [f"# Purchase Reconciliation -- {rng.choice(_COMPANIES)}\n",
          f"Automated reconciliation. Amount = Qty x Unit Price; each Subtotal = sum of its "
          f"section's Amounts; Grand Total = sum of the Subtotals.\n"]
    for sec in sections:
        md.append(f"## {sec['name']}\n\n| # | Item | Qty | Unit Price | Amount |")
        md.append("|---|------|----:|-----------:|-------:|")
        for i, l in enumerate(sec["lines"], 1):
            md.append(f"| {i} | {l['item']} | {l['qty']} | {_money(l['unit'])} | {_money(l['printed'])} |")
        md.append(f"| | **Subtotal** | | | **{_money(sec['st'])}** |\n")
    md.append(f"**Grand Total: {_money(gprint)}**")
    return _pack("md_arithmetic_audit", "\n".join(md), errors,
                 "Amount=Qty x Unit Price; Subtotal=sum of section Amounts; Grand Total=sum of Subtotals")


# ---- 2. percentage / budget --------------------------------------------------

def md_budget_audit(rng):
    nd = rng.randint(4, 6)
    depts = rng.sample(_DEPTS, nd)
    while True:
        amts = [rng.randint(8, 90) * 1000 for _ in range(nd)]      # whole dollars
        total = sum(amts)
        pcts = [amts[i] / total * 100 for i in range(nd)]
        if all(abs(p - round(p)) > 0.07 for p in pcts):            # avoid .5 rounding disputes
            break
    cons_pct = [_rhu(p) for p in pcts]
    target = rng.choice([0, 1, 1, 2, 2, 3])

    pool = [("pct", i) for i in range(nd)] + [("total", None)]
    chosen = rng.sample(pool, min(target, len(pool)))
    pct_bad = {c[1] for c in chosen if c[0] == "pct"}
    total_bad = any(c[0] == "total" for c in chosen)

    errors = []
    pr_pct = list(cons_pct)
    for i in pct_bad:
        new = cons_pct[i] + rng.choice([-3, -2, 2, 3, 4])
        pr_pct[i] = max(0, new)
        errors.append(f"The '{depts[i]}' department shows {pr_pct[i]}% of total, but "
                      f"${amts[i]:,} / ${total:,} = {cons_pct[i]}%.")
    pr_total = total
    if total_bad:
        pr_total = _corrupt(rng, total)
        errors.append(f"The Total budget is shown as ${pr_total:,} but the department amounts sum to "
                      f"${total:,}.")

    md = [f"# FY Budget Allocation -- {rng.choice(_COMPANIES)}\n",
          f"Each department's share is its amount divided by the total of all amounts, as a "
          f"percentage rounded to the nearest whole number.\n",
          "| Department | Amount | % of Total |", "|------------|-------:|-----------:|"]
    for i, d in enumerate(depts):
        md.append(f"| {d} | ${amts[i]:,} | {pr_pct[i]}% |")
    # NOTE: the Total row deliberately shows no aggregate "%" -- injected percentage
    # errors make the column not sum to 100, which is a side effect, not a doc-stated
    # inconsistency, and must not be scored as a false positive.
    md.append(f"| **Total** | **${pr_total:,}** | -- |")
    return _pack("md_budget_audit", "\n".join(md), errors,
                 "% of Total = amount / (sum of all amounts) x 100, rounded to nearest whole number")


# ---- 3. cross-reference prose vs table ---------------------------------------

def md_crossref_audit(rng):
    n = rng.randint(4, 6)
    regions = rng.sample(_REGIONS, n)
    vals = [rng.randint(120, 9800) * 1000 for _ in range(n)]       # cents -> dollars below
    total = sum(vals)
    mx = max(range(n), key=lambda i: vals[i])
    pick = rng.randrange(n)
    target = rng.choice([1, 1, 2, 2, 3])

    claims = ["total", "count", "max_name", "pick_val"]
    bad = set(rng.sample(claims, min(target, len(claims))))
    errors = []

    def _m(c):
        return f"${c // 100:,}"

    st_total = _m(total) if "total" not in bad else _m(_corrupt(rng, total, lo=1000))
    st_count = n if "count" not in bad else n + rng.choice([-1, 1, 2])
    st_maxname = regions[mx] if "max_name" not in bad else regions[rng.choice([i for i in range(n) if i != mx])]
    st_pickval = _m(vals[pick]) if "pick_val" not in bad else _m(_corrupt(rng, vals[pick], lo=1000))

    if "total" in bad:
        errors.append(f"The summary states total sales of {st_total}, but the table values sum to {_m(total)}.")
    if "count" in bad:
        errors.append(f"The summary says the report covers {st_count} regions, but the table lists {n}.")
    if "max_name" in bad:
        errors.append(f"The summary calls {st_maxname} the strongest region, but the table's largest value "
                      f"is {regions[mx]} ({_m(vals[mx])}).")
    if "pick_val" in bad:
        errors.append(f"The summary reports {regions[pick]} at {st_pickval}, but the table shows "
                      f"{_m(vals[pick])}.")

    md = [f"# Regional Sales Summary -- {rng.choice(_COMPANIES)}\n",
          "| Region | Net Sales |", "|--------|----------:|"]
    for i, r in enumerate(regions):
        md.append(f"| {r} | {_m(vals[i])} |")
    md.append(f"\n## Summary\n\nThis quarter the report covers {st_count} regions with combined net sales "
              f"of {st_total}. {st_maxname} was the strongest performer. Notably, {regions[pick]} "
              f"contributed {st_pickval} to the quarter.")
    return _pack("md_crossref_audit", "\n".join(md), errors,
                 "every figure in the Summary prose must match the data table")


# ---- 4. scientific / lab table -----------------------------------------------

def md_lab_audit(rng):
    assay = rng.choice(_ASSAYS)
    n = rng.randint(5, 8)
    vals = [rng.randint(20, 990) for _ in range(n)]                # integer readings
    s = sum(vals)
    mean = _rhu(s / n)
    mx, mn = max(vals), min(vals)
    target = rng.choice([0, 1, 2, 2, 3])

    stats = ["sum", "mean", "max", "min"]
    bad = set(rng.sample(stats, min(target, len(stats))))
    pr = {"sum": s, "mean": mean, "max": mx, "min": mn}
    errors = []
    if "sum" in bad:
        pr["sum"] = _corrupt(rng, s)
        errors.append(f"The reported Sum ({pr['sum']}) does not match the total of the {n} readings ({s}).")
    if "mean" in bad:
        pr["mean"] = mean + rng.choice([-3, -2, 2, 3])
        errors.append(f"The reported Mean ({pr['mean']}) is wrong; {s} / {n} rounds to {mean}.")
    if "max" in bad:
        pr["max"] = mx + rng.randint(1, 30)
        errors.append(f"The reported Maximum ({pr['max']}) is wrong; the largest reading is {mx}.")
    if "min" in bad:
        pr["min"] = max(0, mn - rng.randint(1, min(mn, 15)))
        errors.append(f"The reported Minimum ({pr['min']}) is wrong; the smallest reading is {mn}.")

    md = [f"# Laboratory Report: {assay}\n",
          f"{n} replicate measurements. Mean is the sum divided by the count, rounded to the nearest "
          f"whole number.\n", "| Sample | Reading |", "|--------|--------:|"]
    for i, v in enumerate(vals, 1):
        md.append(f"| S-{1000 + i * 7} | {v} |")
    md.append(f"\n**Summary:** Count = {n}, Sum = {pr['sum']}, Mean = {pr['mean']}, "
              f"Max = {pr['max']}, Min = {pr['min']}.")
    return _pack("md_lab_audit", "\n".join(md), errors,
                 "Sum/Mean/Max/Min must match the readings; Mean = Sum/Count rounded to nearest integer")


# ---- packaging ---------------------------------------------------------------

def _pack(task, doc, errors, rule):
    prompt = (f"You are a meticulous auditor. The following report was generated automatically and may "
              f"contain arithmetic or consistency errors ({rule}). Read the entire report carefully and "
              f"report EVERY inconsistency you find, naming the specific row/value that is wrong and what "
              f"it should be.\n\n"
              f"IMPORTANT: An inconsistency is a value that does not match the other values EXACTLY AS "
              f"PRINTED. Check each value only against the numbers as written. If one input is wrong but a "
              f"Subtotal, Total, or other aggregate still correctly adds up the printed values above it, "
              f"that aggregate is CONSISTENT - flag only the wrong input itself; do NOT propagate the "
              f"correction into downstream totals. If the report is fully consistent, say no errors were "
              f"found.\n\n{doc}")
    return dict(task=task, kind="audit", prompt=prompt, errors=errors,
                answer=("; ".join(errors) if errors else "no errors"),
                meta={"n_errors": len(errors)})


TASKS = {f.__name__: f for f in [
    md_arithmetic_audit, md_budget_audit, md_crossref_audit, md_lab_audit,
]}
