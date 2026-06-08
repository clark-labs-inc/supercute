"""Score any OpenAI-compatible model against the SUPERCUTE benchmark.

    OPENROUTER_API_KEY=... python -m supercute.evaluate \
        --model x-ai/grok-4.3 --benchmark data/benchmark.jsonl

Reports per-task and overall accuracy. Frontier tokenizer LLMs are expected to
score low; a true character-level model should score high.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
from concurrent.futures import ThreadPoolExecutor

from supercute.client import Endpoint, chat
from supercute.grade import grade


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key", default=os.environ.get("OPENROUTER_API_KEY"))
    ap.add_argument("--benchmark", default=os.path.join(os.path.dirname(__file__), "..", "data", "benchmark.jsonl"))
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    scns = load(args.benchmark)
    if args.limit:
        scns = scns[:args.limit]
    ep = Endpoint(args.base_url, args.model, args.api_key)
    print(f"SUPERCUTE eval: {len(scns)} scenarios vs {args.model}\n", flush=True)

    def one(s):
        try:
            r = chat(ep, [{"role": "user", "content": s["prompt"]}], temperature=0.0)
        except Exception as e:
            r = f"<error:{e}>"
        return s["task"], grade(s, r)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        res = list(pool.map(one, scns))

    ok, tot = collections.Counter(), collections.Counter()
    for task, good in res:
        tot[task] += 1
        ok[task] += good
    print(f"{'task':24s} {'acc':>7s} {'n':>5s}")
    print("-" * 40)
    for t in sorted(tot, key=lambda t: ok[t] / tot[t]):
        print(f"{t:24s} {ok[t] / tot[t]:7.3f} {tot[t]:5d}", flush=True)
    print("-" * 40)
    print(f"{'OVERALL':24s} {sum(ok.values()) / sum(tot.values()):7.3f} {sum(tot.values()):5d}  {args.model}")


if __name__ == "__main__":
    main()
