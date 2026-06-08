"""Fast battery sweep: run every generator in a scenarios_* module against a model and
rank tasks by failure rate (lowest accuracy = best breaker). --self runs the free
ground-truth/grader consistency check first (no API).

  python -m supercute.sweep --module tok --self
  OPENROUTER_API_KEY=... python -m supercute.sweep --module tok --model openai/gpt-5.5 --per-task 4
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import os
import random
from concurrent.futures import ThreadPoolExecutor

from supercute.client import Endpoint, chat
from supercute.grade import grade, grade_robust


def _rng(t, i):
    return random.Random(int(hashlib.md5(f"{t}:sweep:{i}".encode()).hexdigest(), 16))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True, help="suffix of scenarios_<module>.py (e.g. tok)")
    ap.add_argument("--model", default="openai/gpt-5.5")
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key", default=os.environ.get("OPENROUTER_API_KEY"))
    ap.add_argument("--per-task", type=int, default=4)
    ap.add_argument("--tasks", nargs="*", default=None, help="optional task names within the module")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--timeout", type=float, default=150.0)
    ap.add_argument("--self", action="store_true", help="ground-truth/grader self-check only (no API)")
    args = ap.parse_args()

    TASKS = dict(importlib.import_module(f"supercute.scenarios_{args.module}").TASKS)
    if args.tasks:
        missing = [t for t in args.tasks if t not in TASKS]
        if missing:
            raise SystemExit(f"unknown task(s) for module {args.module}: {missing}")
        TASKS = {t: TASKS[t] for t in args.tasks}

    if args.self:
        bad = 0
        for t in sorted(TASKS):
            for i in range(40):
                scn = TASKS[t](_rng(t, i))
                a = scn["answer"]
                if not (grade(scn, a) and grade_robust(scn, a)):
                    bad += 1
                    if bad <= 12:
                        print(f"  BAD {t}: answer {a!r} not self-consistent")
        print(f"self-check: {len(TASKS)} tasks x40 -> {'ALL CONSISTENT' if not bad else str(bad)+' BAD'}")
        return

    ep = Endpoint(args.base_url, args.model, args.api_key, timeout=args.timeout)

    def call(scn):
        for _ in range(2):
            try:
                return chat(ep, [{"role": "user", "content": scn["prompt"]}], temperature=0.0)
            except Exception as e:
                err = f"<error:{e}>"
        return err

    print(f"sweep module={args.module} model={args.model} per-task={args.per_task}\n", flush=True)
    rows = []
    for t in sorted(TASKS):
        scns = [TASKS[t](_rng(t, i)) for i in range(args.per_task)]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            resps = list(pool.map(call, scns))
        oks = [grade_robust(s, r) for s, r in zip(scns, resps)]
        rows.append((sum(oks) / len(oks), t, len(oks) - sum(oks), len(oks)))
        print(f"  {t:24s} acc={rows[-1][0]:.2f} ({rows[-1][2]}/{rows[-1][3]} fail)", flush=True)
    rows.sort()
    print("\n=== ranked hardest-first (breakers at top) ===")
    for acc, t, f, n in rows:
        print(f"  {t:24s} {acc:.2f}  ({f}/{n})")
    overall = sum(r[0] for r in rows) / len(rows)
    print(f"\nmean per-task acc: {overall:.3f}")


if __name__ == "__main__":
    main()
