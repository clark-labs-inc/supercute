"""Plot the iterated_lut break curve (accuracy vs number of interdependent steps) for
all three models, with Wilson 95% CI error bars. Reads data/eval_summary.json,
writes paper/figures/breakcurve.png."""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
SUM = os.path.join(HERE, "..", "data", "eval_summary.json")
OUT = os.path.join(HERE, "..", "paper", "figures", "breakcurve.png")

MARK = {"GPT-5.5": ("o", "#1f77b4"), "Opus 4.8": ("s", "#d62728"),
        "DeepSeek V4 Pro": ("D", "#9467bd"), "MiniMax M3": ("v", "#ff7f0e"),
        "Qwen 3.7 Plus": ("P", "#8c564b"), "Qwen 3.5 Flash": ("^", "#2ca02c")}


def main():
    s = json.load(open(SUM))
    bc = s["break_curve"]
    plt.figure(figsize=(6.2, 3.6))
    for model, pts in bc.items():
        if not pts:
            continue
        Ks = sorted(int(k) for k in pts)
        xs = [pts[str(k)]["steps"] for k in Ks]
        ys = [pts[str(k)]["acc"] for k in Ks]
        lo = [pts[str(k)]["acc"] - pts[str(k)]["lo"] for k in Ks]
        hi = [pts[str(k)]["hi"] - pts[str(k)]["acc"] for k in Ks]
        mk, col = MARK.get(model, ("o", "gray"))
        plt.errorbar(xs, ys, yerr=[lo, hi], marker=mk, color=col, capsize=3, label=model, linewidth=1.6, markersize=5)
    plt.xlabel("interdependent steps  (state width L=22 × rounds K)")
    plt.ylabel("exact-match accuracy")
    plt.title("Long-horizon execution (iterated random transition table)")
    plt.ylim(-0.05, 1.05)
    plt.grid(True, alpha=0.3)
    plt.legend(frameon=False, fontsize=9)
    plt.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    plt.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
