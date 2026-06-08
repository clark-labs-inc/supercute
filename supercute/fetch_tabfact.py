"""Distill TabFact (real Wikipedia tables + human ENTAILED/REFUTED statements,
CC-BY-SA) into data/tabfact_records.jsonl: {table, caption, statement, label}.

Reads from a local shallow clone of github.com/wenhuchen/Table-Fact-Checking
(tables are 16k separate '#'-delimited CSVs, so a clone is the practical source).

    git clone --depth 1 https://github.com/wenhuchen/Table-Fact-Checking /tmp/tabfact_repo
    python -m supercute.fetch_tabfact --repo /tmp/tabfact_repo --max 5000
"""
from __future__ import annotations

import argparse
import json
import os
import random

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "tabfact_records.jsonl")


def _read_csv(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n").split("#") for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/tmp/tabfact_repo")
    ap.add_argument("--max", type=int, default=5000)
    ap.add_argument("--max-rows", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    ex = json.load(open(os.path.join(args.repo, "tokenized_data", "test_examples.json")))
    csv_dir = os.path.join(args.repo, "data", "all_csv")
    tids = list(ex.keys())
    random.Random(args.seed).shuffle(tids)

    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    n = 0
    with open(OUT, "w", encoding="utf-8") as fh:
        for tid in tids:
            if n >= args.max:
                break
            path = os.path.join(csv_dir, tid)
            if not os.path.exists(path):
                continue
            table = _read_csv(path)
            if len(table) < 2 or len(table) > args.max_rows or len(table[0]) < 2:
                continue
            stmts, labels, caption = ex[tid]
            for s, lab in zip(stmts, labels):
                if n >= args.max:
                    break
                fh.write(json.dumps({"table": table, "caption": caption,
                                     "statement": s, "label": int(lab)}, ensure_ascii=False) + "\n")
                n += 1
    print(f"wrote {n} TabFact records -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
