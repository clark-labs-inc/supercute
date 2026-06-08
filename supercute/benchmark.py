"""Head-to-head benchmark: run several models on the SAME fresh sample of SUPERCUTE
scenarios and compare accuracy per model and per domain. Uses grade_robust (handles
reasoning models that conclude at the end of their output).

  OPENROUTER_API_KEY=... python -m supercute.benchmark \
     --models anthropic/claude-opus-4.8 openai/gpt-5.5 qwen/qwen3.5-flash-02-23 \
     --per-task 2 --pilot 6        # pilot first: eyeball extraction, then drop --pilot
"""
from __future__ import annotations

import argparse
import collections
import os
from concurrent.futures import ThreadPoolExecutor

from supercute.client import Endpoint, chat
from supercute.generate import DOMAIN
from supercute.grade import grade_robust
from supercute.run import make_scenarios
from supercute.scenarios import TASKS


def _call(ep, scn):
    err = ""
    for _ in range(2):                       # one retry on transport error (fairness)
        try:
            return chat(ep, [{"role": "user", "content": scn["prompt"]}], temperature=0.0)
        except Exception as e:
            err = f"<error:{e}>"
    return err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key", default=os.environ.get("OPENROUTER_API_KEY"))
    ap.add_argument("--tasks", nargs="+", default=sorted(TASKS))
    ap.add_argument("--per-task", type=int, default=2)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pilot", type=int, default=0, help="print N raw responses (eyeball grading) and stop")
    ap.add_argument("--pilot-model", default=None)
    args = ap.parse_args()

    scns = make_scenarios(args.tasks, args.per_task, args.seed)
    eps = {m: Endpoint(args.base_url, m, args.api_key, timeout=args.timeout) for m in args.models}

    if args.pilot:
        m = args.pilot_model or args.models[0]
        print(f"PILOT: {args.pilot} scenarios on {m}\n" + "=" * 70, flush=True)
        for scn in scns[:args.pilot]:
            resp = _call(eps[m], scn)
            ok = grade_robust(scn, resp)
            tail = resp[-260:].replace("\n", " ⏎ ")
            print(f"[{scn['task']}] kind={scn['kind']} truth={scn['answer']!r}  -> graded {'OK' if ok else 'WRONG'}")
            print(f"   resp_tail: ...{tail}\n")
        return

    def run_model(m):
        ep = eps[m]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            resps = list(pool.map(lambda s: _call(ep, s), scns))
        return [grade_robust(s, r) for s, r in zip(scns, resps)], resps

    results = {}
    for m in args.models:
        print(f"running {m} on {len(scns)} scenarios ...", flush=True)
        results[m] = run_model(m)

    domains = [DOMAIN.get(s["task"], "misc") for s in scns]
    dom_set = sorted(set(domains))

    # overall
    print("\n" + "=" * (24 + 9 * len(args.models)))
    print(f"{'OVERALL':22s}" + "".join(f"{m.split('/')[-1][:8]:>9s}" for m in args.models))
    print("-" * (24 + 9 * len(args.models)))
    for label, sel in [("ALL", range(len(scns)))] + [(d, [i for i, dd in enumerate(domains) if dd == d]) for d in dom_set]:
        row = f"{label:22s}"
        for m in args.models:
            grades = [results[m][0][i] for i in sel]
            acc = sum(grades) / len(grades) if grades else float("nan")
            row += f"{acc:9.2f}"
        if label == "ALL":
            row += "   <- overall accuracy (higher = better)"
        print(row, flush=True)
    print(f"\n({len(scns)} scenarios x {len(args.models)} models; errors counted as wrong)")


if __name__ == "__main__":
    main()
