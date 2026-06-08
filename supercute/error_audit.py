"""Sample failed raw records for manual SUPERCUTE error analysis.

This script expects a JSONL file produced by:

  python -m supercute.full_eval --raw-out data/eval_raw.jsonl

It does not grade or classify errors automatically. Instead, it prints compact
failure packets that a human can label as execution error, extraction/formatting
error, timeout/provider error, refusal, or other. Keeping this manual step small
is intentional: exact-match benchmark claims should not hide failure modes.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def clip(text: str, n: int) -> str:
    text = text.replace("\r\n", "\n")
    return text if len(text) <= n else text[: n - 20] + "\n...<clipped>..."


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", help="raw JSONL from full_eval --raw-out")
    ap.add_argument("--model", default=None)
    ap.add_argument("--tier", default=None)
    ap.add_argument("--task", default=None)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--chars", type=int, default=1600)
    args = ap.parse_args()

    rows = [json.loads(l) for l in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if not r.get("correct")]
    if args.model:
        rows = [r for r in rows if r.get("model") == args.model]
    if args.tier:
        rows = [r for r in rows if r.get("tier") == args.tier]
    if args.task:
        rows = [r for r in rows if r.get("task") == args.task]
    rng = random.Random(args.seed)
    rng.shuffle(rows)
    for i, r in enumerate(rows[: args.n], 1):
        print("=" * 88)
        print(f"[{i}] model={r.get('model')} uid={r.get('uid')} tier={r.get('tier')} task={r.get('task')} K={r.get('K')} finish={r.get('finish')} err={r.get('err')}")
        print(f"oracle: {r.get('answer')!r}")
        print("--- response ---")
        print(clip(r.get("response", ""), args.chars))
        print("--- suggested label: execution | extraction_format | timeout_provider | refusal | other")
    print(f"\nshown {min(args.n, len(rows))} of {len(rows)} matching failures")


if __name__ == "__main__":
    main()
