"""Full multi-model evaluation for the SUPERCUTE / GPT-5.5 study. Runs three tiers
(tokenization battery, adversarial static, iterated_lut break curve) across three
models, capturing per-call correctness, reasoning tokens, and finish_reason. Results
append to data/eval_results.jsonl (resumable: re-running skips completed cells).

  OPENROUTER_API_KEY=... python -m supercute.full_eval --n 8 --workers 18
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from supercute.grade import grade_robust
from supercute import scenarios_tok, scenarios_hard, scenarios_realtok

MODELS = ["openai/gpt-5.5", "anthropic/claude-opus-4.8", "deepseek/deepseek-v4-pro",
          "minimax/minimax-m3", "qwen/qwen3.7-plus", "qwen/qwen3.5-flash-02-23",
          "nex-agi/nex-n2-pro:free", "anthropic/claude-fable-5"]
REALTOK_TASKS = sorted(scenarios_realtok.TASKS)
LUT_L = 22
LUT_K = [15, 30, 45, 60, 75]
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "eval_results.jsonl")


def _rng(uid):
    return random.Random(int(hashlib.md5(uid.encode()).hexdigest(), 16))


def _lut(rng, L, K):
    T = [[rng.randint(0, 9) for _ in range(10)] for _ in range(10)]
    cur = [rng.randint(0, 9) for _ in range(L)]
    s0 = "".join(map(str, cur))
    for _ in range(K):
        cur = [T[cur[i]][cur[(i + 1) % L]] for i in range(L)]
    grid = "\n".join(f"  current={a}:  " + " ".join(str(T[a][b]) for b in range(10)) for a in range(10))
    prompt = (f"Simulate a cellular automaton over {K} rounds. The transition table T gives the new "
              f"digit from the current digit (row) and its right-neighbor digit (column 0-9):\n{grid}\n\n"
              f"Starting string ({L} digits): {s0}\n\nEach round, simultaneously replace every digit d at "
              f"position i with T[d][e], where e is the digit immediately to its right (last wraps to "
              f"first). After exactly {K} rounds, output only the resulting {L}-digit string, no spaces.")
    return {"prompt": prompt, "answer": "".join(map(str, cur)), "kind": "str"}


def build_jobs(n):
    jobs = []  # (uid, tier, task, K, scn)
    for t in sorted(scenarios_tok.TASKS):
        for i in range(n):
            uid = f"tok:{t}:0:{i}"
            jobs.append((uid, "tok", t, 0, scenarios_tok.TASKS[t](_rng(uid))))
    for t in REALTOK_TASKS:
        for i in range(n):
            uid = f"realtok:{t}:0:{i}"
            jobs.append((uid, "realtok", t, 0, scenarios_realtok.TASKS[t](_rng(uid))))
    for K in LUT_K:
        for i in range(n):
            uid = f"lut:iterated_lut:{K}:{i}"
            jobs.append((uid, "lut", "iterated_lut", K, _lut(_rng(uid), LUT_L, K)))
    return jobs


# Models that do NOT engage extended thinking by default on OpenRouter must be given a
# reasoning budget, or the comparison is reasoning-on vs reasoning-off. Anthropic models
# need this explicitly; OpenAI/DeepSeek/MiniMax reason by default.
REASONING = {"anthropic/claude-opus-4.8": {"effort": "medium"},
             "anthropic/claude-fable-5": {"effort": "medium"},
             "qwen/qwen3.7-plus": {"effort": "medium"},
             "qwen/qwen3.5-flash-02-23": {"effort": "medium"},
             "nex-agi/nex-n2-pro:free": {"effort": "medium"}}


def call(model, prompt, key, timeout):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0}
    if model in REASONING:
        payload["reasoning"] = REASONING[model]
    body = json.dumps(payload).encode()
    last = ""
    for _ in range(2):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": "Bearer " + key}, method="POST")
            p = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            ch = p["choices"][0]
            u = p.get("usage", {})
            return {"content": ch.get("message", {}).get("content") or "", "finish": ch.get("finish_reason"),
                    "rtoks": u.get("completion_tokens_details", {}).get("reasoning_tokens"),
                    "ctoks": u.get("completion_tokens"), "err": False}
        except Exception as e:
            last = str(e)
    return {"content": "", "finish": "error", "rtoks": None, "ctoks": None, "err": True, "detail": last}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--workers", type=int, default=18)
    ap.add_argument("--timeout", type=float, default=320.0)
    ap.add_argument("--api-key", default=os.environ.get("OPENROUTER_API_KEY"))
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--raw-out", default=None,
                    help="optional JSONL path for raw audit records with prompt, oracle answer, and model response")
    args = ap.parse_args()

    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                done.add((r["model"], r["uid"]))
    jobs = build_jobs(args.n)
    work = [(m, j) for m in args.models for j in jobs if (m, j[0]) not in done]
    print(f"full_eval: {len(jobs)} cells x {len(args.models)} models; {len(work)} to run "
          f"({len(done)} already done)", flush=True)

    lock_f = open(OUT, "a", encoding="utf-8")
    raw_f = open(args.raw_out, "a", encoding="utf-8") if args.raw_out else None
    counter = {"i": 0}

    def run(item):
        model, (uid, tier, task, K, scn) = item
        r = call(model, scn["prompt"], args.api_key, args.timeout)
        ok = (not r["err"]) and grade_robust(scn, r["content"])
        rec = {"model": model, "uid": uid, "tier": tier, "task": task, "K": K,
               "correct": bool(ok), "err": r["err"], "finish": r["finish"],
               "rtoks": r["rtoks"], "ctoks": r["ctoks"]}
        lock_f.write(json.dumps(rec) + "\n"); lock_f.flush()
        if raw_f is not None:
            raw = {**rec, "prompt": scn["prompt"], "answer": scn["answer"], "response": r.get("content", "")}
            raw_f.write(json.dumps(raw, ensure_ascii=False) + "\n"); raw_f.flush()
        counter["i"] += 1
        if counter["i"] % 25 == 0:
            print(f"  ... {counter['i']}/{len(work)}", flush=True)
        return rec

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(run, work))
    if raw_f is not None:
        raw_f.close()
    print(f"done. results -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
