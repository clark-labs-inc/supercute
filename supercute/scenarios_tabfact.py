"""SUPERCUTE real-document verification from TabFact (CC-BY-SA): real Wikipedia tables
+ human statements labeled ENTAILED (1) / REFUTED (0). Deterministic yes/no task:
render the real table and ask whether the statement is true according to it. Ground
truth is the human label. Many statements need counting / superlative / comparison
reasoning over the table -- the hard, byte-relevant subset.
"""
from __future__ import annotations

import json
import os
import random

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tabfact_records.jsonl")


def _load():
    if not os.path.exists(_PATH):
        return []
    return [json.loads(l) for l in open(_PATH, encoding="utf-8") if l.strip()]


_RECORDS = _load()


def _table_md(table):
    head = "| " + " | ".join(table[0]) + " |"
    sep = "|" + "|".join("---" for _ in table[0]) + "|"
    rows = ["| " + " | ".join(r) + " |" for r in table[1:]]
    return "\n".join([head, sep] + rows)


def tabfact_verify(rng):
    rec = rng.choice(_RECORDS)
    capv = (rec.get("caption") or "").strip()
    cap = f" (about: {capv})" if capv and capv.lower() != "none" else ""
    prompt = (f"Consider this table{cap}:\n\n{_table_md(rec['table'])}\n\n"
              f"Statement: \"{rec['statement']}\"\n\n"
              f"Is this statement TRUE according to the table? Answer yes or no.")
    return dict(task="tabfact_verify", kind="yn", answer="yes" if rec["label"] == 1 else "no",
                prompt=prompt, meta={"label": rec["label"]})


TASKS = {f.__name__: f for f in [tabfact_verify]} if _RECORDS else {}
