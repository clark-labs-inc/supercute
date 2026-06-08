"""Run the document-audit suite: a solver model (default qwen 3.5 flash) audits each
generated report in free text; an LLM judge (default x-ai/grok-4.3) scores its
findings against ground truth. Failures (missed an error or raised a false positive)
are harvested into data/audit_hard.jsonl.

    OPENROUTER_API_KEY=... python -m supercute.run_audit \
        --per-task 8 --workers 6              # solver=qwen, judge=grok-4.3
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
from supercute.judge import judge_audit
from supercute.scenarios_audit import TASKS as _SYNTH
from supercute.scenarios_sec import TASKS as _SEC

TASKS = {**_SYNTH, **_SEC}              # synthetic + real-document (SEC) audit scenarios


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
    ap.add_argument("--judge-model", default="x-ai/grok-4.3")
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key", default=os.environ.get("OPENROUTER_API_KEY"))
    ap.add_argument("--tasks", nargs="+", default=sorted(TASKS))
    ap.add_argument("--per-task", type=int, default=8)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "audit_hard.jsonl"))
    args = ap.parse_args()

    scns = make_scenarios(args.tasks, args.per_task, args.seed)
    solver = Endpoint(args.base_url, args.model, args.api_key, timeout=args.timeout)
    judge = Endpoint(args.base_url, args.judge_model, args.api_key, timeout=args.timeout)
    print(f"AUDIT: {len(scns)} docs ({len(args.tasks)} types x {args.per_task})  "
          f"solver={args.model}  judge={args.judge_model}\n", flush=True)

    def one(scn):
        try:
            cand = chat(solver, [{"role": "user", "content": scn["prompt"]}], temperature=0.0)
        except Exception as e:
            return scn, f"<error:{e}>", dict(passed=False, error=True, recall=0.0, false_positives=-1)
        verdict = judge_audit(judge, scn, cand)
        return scn, cand, verdict

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(one, scns))

    passed, tot, rec, fp, errs = (collections.Counter(), collections.Counter(),
                                  collections.defaultdict(list), collections.defaultdict(list), 0)
    hard = []
    for scn, cand, v in results:
        if v.get("error"):
            errs += 1
            continue
        t = scn["task"]
        tot[t] += 1
        passed[t] += v["passed"]
        rec[t].append(v["recall"])
        fp[t].append(v["false_positives"])
        if not v["passed"]:
            hard.append({"id": scn["id"], "task": t, "prompt": scn["prompt"],
                         "errors": scn["errors"], "n_errors": scn["meta"]["n_errors"],
                         "model": args.model, "judge": args.judge_model,
                         "candidate": cand[:1200], "recall": v["recall"],
                         "false_positives": v["false_positives"], "caught": v.get("caught")})

    print(f"{'doc type':22s} {'pass':>6s} {'recall':>7s} {'fp/doc':>7s} {'fail':>5s}")
    print("-" * 52)
    for t in sorted(args.tasks, key=lambda t: passed[t] / tot[t] if tot[t] else 1):
        if not tot[t]:
            continue
        mr = sum(rec[t]) / len(rec[t])
        mfp = sum(fp[t]) / len(fp[t])
        print(f"{t:22s} {passed[t] / tot[t]:6.2f} {mr:7.2f} {mfp:7.2f} {tot[t] - passed[t]:5d}", flush=True)
    print("-" * 52)
    g = sum(tot.values())
    print(f"{'OVERALL':22s} {sum(passed.values()) / g if g else float('nan'):6.2f}  "
          f"{len(hard)} hard / {g} graded   ({errs} judge/solver errors excluded)")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        for h in hard:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")
    total = sum(1 for _ in open(args.out, encoding="utf-8")) if os.path.exists(args.out) else 0
    print(f"\nappended {len(hard)} -> {args.out} (total accumulated: {total})", flush=True)


if __name__ == "__main__":
    main()
