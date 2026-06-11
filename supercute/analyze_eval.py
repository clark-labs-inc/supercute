"""Analyze data/eval_results.jsonl for the SUPERCUTE paper.

The script reports:
- per-tier and per-task exact-match accuracy with Wilson 95% intervals;
- the iterated_lut break curve by K;
- a simple one-parameter compounding fit P(correct | K) = r**K;
- transport/error counts that explain why some denominators are below the
  nominal n=8 per cell.

It writes data/eval_summary.json. Transport/provider errors are kept in the raw
JSONL but dropped from scored denominators, which makes missing cells explicit.
"""
from __future__ import annotations

import collections
import json
import math
import os
from typing import Iterable

HERE = os.path.dirname(__file__)
IN = os.path.join(HERE, "..", "data", "eval_results.jsonl")
OUT = os.path.join(HERE, "..", "data", "eval_summary.json")
SHORT = {
    "openai/gpt-5.5": "GPT-5.5",
    "anthropic/claude-opus-4.8": "Opus 4.8",
    "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro",
    "minimax/minimax-m3": "MiniMax M3",
    "qwen/qwen3.7-plus": "Qwen 3.7 Plus",
    "qwen/qwen3.5-flash-02-23": "Qwen 3.5 Flash",
    "nex-agi/nex-n2-pro:free": "Nex-N2-Pro",
    "anthropic/claude-fable-5": "Fable 5",
}
ORDER = ["GPT-5.5", "Opus 4.8", "Fable 5", "DeepSeek V4 Pro", "MiniMax M3", "Qwen 3.7 Plus", "Qwen 3.5 Flash", "Nex-N2-Pro"]
LUT_L = 22


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def load_all() -> list[dict]:
    return [json.loads(l) for l in open(IN, encoding="utf-8") if l.strip()]


def clean(rows: Iterable[dict]) -> list[dict]:
    return [r for r in rows if not r.get("err")]


def agg(rows: Iterable[dict]) -> tuple[int, int]:
    rows = list(rows)
    return sum(1 for r in rows if r["correct"]), len(rows)


def _nll_for_logit(logit_r: float, obs: list[tuple[int, int, int]]) -> float:
    """Negative binomial log likelihood for P(correct | K) = r**K."""
    r = 1.0 / (1.0 + math.exp(-logit_r))
    eps = 1e-15
    total = 0.0
    for K, k, n in obs:
        if n == 0:
            continue
        p = min(1.0 - eps, max(eps, r**K))
        total -= k * math.log(p) + (n - k) * math.log(1.0 - p)
    return total


def fit_compounding(obs: list[tuple[int, int, int]]) -> dict[str, float]:
    """Fit P(correct | K)=r**K by one-dimensional likelihood search.

    Because LUT uses fixed width L=22 in the supplied run, the corresponding
    per-cell-update survival is q = r**(1/22). The fit is descriptive, not a
    proof that errors are independent.
    """
    lo, hi = -20.0, 20.0
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    c = hi - gr * (hi - lo)
    d = lo + gr * (hi - lo)
    fc = _nll_for_logit(c, obs)
    fd = _nll_for_logit(d, obs)
    for _ in range(200):
        if fc > fd:
            lo = c
            c = d
            fc = fd
            d = lo + gr * (hi - lo)
            fd = _nll_for_logit(d, obs)
        else:
            hi = d
            d = c
            fd = fc
            c = hi - gr * (hi - lo)
            fc = _nll_for_logit(c, obs)
    x = (lo + hi) / 2.0
    r = 1.0 / (1.0 + math.exp(-x))
    q = r ** (1.0 / LUT_L)
    half_rounds = math.log(0.5) / math.log(r) if 0.0 < r < 1.0 else float("inf")
    return {
        "round_survival": r,
        "update_survival": q,
        "half_life_rounds": half_rounds,
        "half_life_updates": half_rounds * LUT_L,
        "nll": _nll_for_logit(x, obs),
        "pred": {str(K): r**K for K, _, _ in obs},
    }


def main() -> None:
    all_rows = load_all()
    rows = clean(all_rows)
    error_counts = collections.Counter((r["tier"], SHORT.get(r["model"], r["model"])) for r in all_rows if r.get("err"))
    present = set(SHORT.get(r["model"], r["model"]) for r in rows)
    models = [m for m in SHORT if SHORT[m] in present]
    models = sorted(models, key=lambda m: ORDER.index(SHORT[m]) if SHORT[m] in ORDER else 99)
    summary = {
        "by_tier": {},
        "by_task": {},
        "break_curve": {},
        "compounding_fit": {},
        "errors_dropped": {f"{tier}|{model}": n for (tier, model), n in sorted(error_counts.items())},
        "n_total_raw": len(all_rows),
        "n_total_scored": len(rows),
    }

    print("=" * 78)
    print("PER-TIER ACCURACY (Wilson 95% CI; transport/provider errors dropped)")
    print(f"{'tier':10s} {'model':16s} {'acc':>6s} {'n':>4s} {'drop':>4s}   95% CI")
    for tier in ["tok", "realtok", "lut"]:
        for m in models:
            sub = [r for r in rows if r["tier"] == tier and r["model"] == m]
            if not sub:
                continue
            k, n = agg(sub)
            p, lo, hi = wilson(k, n)
            short = SHORT.get(m, m)
            drop = error_counts.get((tier, short), 0)
            summary["by_tier"].setdefault(tier, {})[short] = {
                "k": k,
                "n": n,
                "dropped": drop,
                "acc": p,
                "lo": lo,
                "hi": hi,
            }
            print(f"{tier:10s} {short:16s} {p:6.3f} {n:4d} {drop:4d}   [{lo:.3f}, {hi:.3f}]")
        print("-" * 58)

    print("\n" + "=" * 78)
    print("PER-TASK ACCURACY (tok + realtok)")
    for tier in ["tok", "realtok"]:
        tasks = sorted(set(r["task"] for r in rows if r["tier"] == tier))
        for t in tasks:
            line = f"  {t:28s}"
            for m in models:
                sub = [r for r in rows if r["task"] == t and r["model"] == m and r["tier"] == tier]
                k, n = agg(sub)
                p = k / n if n else float("nan")
                summary["by_task"].setdefault(t, {})[SHORT.get(m, m)] = {"k": k, "n": n, "acc": p}
                line += f" {SHORT.get(m,m).split()[0]}={p:.2f}"
            print(line)

    print("\n" + "=" * 78)
    print("iterated_lut BREAK CURVE (acc, Wilson CI, avg tokens, non-stop finishes)")
    Ks = sorted(set(r["K"] for r in rows if r["tier"] == "lut"))
    for m in models:
        short = SHORT.get(m, m)
        print(f"\n  {short} (L={LUT_L}):")
        summary["break_curve"][short] = {}
        for K in Ks:
            sub = [r for r in rows if r["tier"] == "lut" and r["model"] == m and r["K"] == K]
            if not sub:
                continue
            k, n = agg(sub)
            p, lo, hi = wilson(k, n)
            rts = [r["rtoks"] for r in sub if r.get("rtoks")]
            cts = [r["ctoks"] for r in sub if r.get("ctoks")]
            nonstop = sum(1 for r in sub if r["finish"] not in ("stop", None))
            avg_rt = int(sum(rts) / len(rts)) if rts else 0
            avg_ct = int(sum(cts) / len(cts)) if cts else 0
            summary["break_curve"][short][str(K)] = {
                "k": k,
                "n": n,
                "acc": p,
                "lo": lo,
                "hi": hi,
                "steps": LUT_L * K,
                "avg_rtoks": avg_rt,
                "avg_ctoks": avg_ct,
                "nonstop": nonstop,
            }
            print(f"    K={K:3d} steps={LUT_L*K:5d}  acc={p:.2f} [{lo:.2f},{hi:.2f}]  n={n}  avg_rtoks={avg_rt:6d} avg_ctoks={avg_ct:6d}  non-stop={nonstop}")

        obs = []
        for K in Ks:
            sub = [r for r in rows if r["tier"] == "lut" and r["model"] == m and r["K"] == K]
            k, n = agg(sub)
            obs.append((K, k, n))
        fit = fit_compounding(obs)
        summary["compounding_fit"][short] = fit
        print("    fit P(correct|K)=r^K: "
              f"r={fit['round_survival']:.4f}, q_update={fit['update_survival']:.6f}, "
              f"half-life={fit['half_life_rounds']:.1f} rounds / {fit['half_life_updates']:.0f} updates")

    json.dump(summary, open(OUT, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {OUT}  (raw rows: {len(all_rows)}, scored rows: {len(rows)}, dropped errors: {len(all_rows)-len(rows)})")


if __name__ == "__main__":
    main()
