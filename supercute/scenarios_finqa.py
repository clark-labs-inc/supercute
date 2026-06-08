"""SUPERCUTE real-document verification from FinQA (CC-BY-4.0): real S&P 500 financial
tables + a gold numeric answer. Deterministic yes/no task -- render the real table,
state an answer (the true gold value or a plausible wrong one), ask whether it is
correct. Verifying it requires finding the right cells in a real table and doing the
arithmetic, on real messy numbers. Ground truth is exact (the gold exe_ans).
"""
from __future__ import annotations

import json
import os
import random

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "finqa_records.jsonl")


def _load():
    if not os.path.exists(_PATH):
        return []
    out = []
    for line in open(_PATH, encoding="utf-8"):
        if line.strip():
            out.append(json.loads(line))
    return out


_RECORDS = _load()


def _fmt(x):
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return f"{x:,}" if isinstance(x, int) else f"{x:,.2f}".rstrip("0").rstrip(".")


def _table_md(table):
    head = "| " + " | ".join(str(c) for c in table[0]) + " |"
    sep = "|" + "|".join("---" for _ in table[0]) + "|"
    rows = ["| " + " | ".join(str(c) for c in r) + " |" for r in table[1:]]
    return "\n".join([head, sep] + rows)


def _wrong(rng, v):
    for _ in range(20):
        f = rng.choice([0.5, 0.8, 0.9, 1.1, 1.25, 1.5, 2.0, 10.0, 0.1])
        cand = round(v * f, 2)
        if cand != v and cand != 0:
            return cand
    return v + (1 if v == 0 else v)


def finqa_verify(rng):
    rec = rng.choice(_RECORDS)
    true = rec["answer"]
    if rng.random() < 0.5:
        stated, ans = true, "yes"
    else:
        stated, ans = _wrong(rng, true), "no"
    excerpt = ""
    if rec.get("pre"):
        excerpt += rec["pre"] + "\n\n"
    excerpt += _table_md(rec["table"])
    if rec.get("post"):
        excerpt += "\n\n" + rec["post"]
    prompt = (f"Use the financial-report excerpt below (text and table) to check a claim.\n\n"
              f"{excerpt}\n\n"
              f"Question: {rec['question']}\n"
              f"Claimed answer: {_fmt(stated)}\n\n"
              f"Is the claimed answer correct according to the report? Answer yes or no.")
    return dict(task="finqa_verify", kind="yn", answer=ans, prompt=prompt,
                meta={"true": true, "stated": stated})


TASKS = {f.__name__: f for f in [finqa_verify]} if _RECORDS else {}
