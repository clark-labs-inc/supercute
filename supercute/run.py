"""Run SUPERCUTE scenarios against a model (parallel) and harvest the FAILURES
into the benchmark. The goal: accumulate >=1000 hard scenarios a frontier LLM fails.

    OPENROUTER_API_KEY=... python -m supercute.run \
        --model qwen/qwen3.5-flash-02-23 --per-task 60 --workers 16
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor

from supercute.client import Endpoint, chat
from supercute.grade import grade
from supercute.scenarios import TASKS


def _rng(task, seed, i):
    return random.Random(int(hashlib.md5(f"{task}:{seed}:{i}".encode()).hexdigest(), 16))


def make_scenarios(tasks, per_task, seed):
    out = []
    for t in tasks:
        for i in range(per_task):
            scn = TASKS[t](_rng(t, seed, i))
            scn["id"] = f"{t}-{seed}-{i:04d}"
            out.append(scn)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen/qwen3.5-flash-02-23")
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key", default=os.environ.get("OPENROUTER_API_KEY"))
    ap.add_argument("--tasks", nargs="+", default=sorted(TASKS))
    ap.add_argument("--per-task", type=int, default=40)
    # qwen calls are I/O-bound: threads release the GIL on the socket, so high
    # concurrency is safe and necessary -- a few 60s-slow responses must not starve
    # the pool. 64 workers + a tight timeout keeps a 1600-call sweep to a few minutes.
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hard-out", default=os.path.join(os.path.dirname(__file__), "..", "data", "hard.jsonl"))
    args = ap.parse_args()

    scns = make_scenarios(args.tasks, args.per_task, args.seed)
    ep = Endpoint(args.base_url, args.model, args.api_key, timeout=args.timeout)
    print(f"SUPERCUTE: {len(scns)} scenarios ({len(args.tasks)} tasks x {args.per_task}) "
          f"vs {args.model}\n", flush=True)

    def one(scn):
        # one retry: a transport error is not a model failure, so don't let a
        # single stalled request masquerade as a "hard" scenario.
        for attempt in range(2):
            try:
                resp = chat(ep, [{"role": "user", "content": scn["prompt"]}], temperature=0.0)
                return scn, resp, grade(scn, resp), False
            except Exception as e:
                err = f"<error:{e}>"
        return scn, err, False, True

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(one, scns))

    ok, tot, errs = collections.Counter(), collections.Counter(), 0
    hard = []
    for scn, resp, good, is_err in results:
        if is_err:                       # transport failure: exclude from accuracy + harvest
            errs += 1
            continue
        ok[scn["task"]] += good
        tot[scn["task"]] += 1
        if not good:
            hard.append({"id": scn["id"], "task": scn["task"], "prompt": scn["prompt"],
                         "answer": scn["answer"], "kind": scn["kind"], "meta": scn.get("meta", {}),
                         "model": args.model, "model_response": resp[:400]})

    print(f"{'task':22s} {'acc':>7s}  {'fail':>5s}   (lower acc = harder = better)")
    print("-" * 46)
    for t in sorted(args.tasks, key=lambda t: ok[t] / tot[t] if tot[t] else 1):
        acc = ok[t] / tot[t] if tot[t] else float("nan")
        print(f"{t:22s} {acc:7.3f}  {tot[t] - ok[t]:5d}", flush=True)
    print("-" * 46)
    graded = sum(tot.values())
    overall = sum(ok.values()) / graded if graded else float("nan")
    print(f"{'OVERALL':22s} {overall:7.3f}  {len(hard):5d} hard scenarios this run"
          f"   ({errs} transport errors excluded)")

    os.makedirs(os.path.dirname(os.path.abspath(args.hard_out)), exist_ok=True)
    with open(args.hard_out, "a", encoding="utf-8") as f:
        for h in hard:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")
    # report total accumulated
    total = sum(1 for _ in open(args.hard_out, encoding="utf-8"))
    print(f"\nappended {len(hard)} -> {args.hard_out} (total accumulated: {total})", flush=True)


if __name__ == "__main__":
    main()
