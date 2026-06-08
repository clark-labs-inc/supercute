"""SUPERCUTE invisible / zero-width Unicode tasks -- the byte-valid successor to the
cut homoglyph task.

Unlike a homoglyph (a distinct VISIBLE code point any token model sees), zero-width
and bidi-control characters do not render: the visible text lies about its true
length and content. A byte/code-point-aware model sees them; a tokenizer model that
reasons from the rendered glyphs cannot. Ground truth is exact by construction.
"""
from __future__ import annotations

import random
import string

LOW = string.ascii_lowercase
ZW = ["​", "‌", "‍", "﻿", "⁠", "­"]   # zero-width / invisible
BIDI = ["‪", "‫", "‬", "‭", "‮",            # bidi embed/override
        "⁦", "⁧", "⁨", "⁩"]                      # bidi isolates
COMB = ["́", "̀", "̈", "̣", "̧", "̂"]  # combining marks


def _interleave(rng, visible, extras, n_extra):
    """Insert n_extra of `extras` at random positions among `visible` characters."""
    chars = list(visible)
    for _ in range(n_extra):
        chars.insert(rng.randint(0, len(chars)), rng.choice(extras))
    return "".join(chars)


def total_codepoints_invisible(rng):
    vis = "".join(rng.choice(LOW) for _ in range(rng.randint(8, 16)))
    n_inv = rng.randint(2, 7)
    s = _interleave(rng, vis, ZW, n_inv)
    return dict(task="total_codepoints_invisible", kind="int", answer=str(len(vis) + n_inv),
                prompt=f"How many Unicode code points are in this string, COUNTING every invisible / "
                       f"zero-width character (ZWSP, ZWNJ, ZWJ, BOM, word-joiner, soft-hyphen) as one? "
                       f"The visible text may look shorter than the true count.\n{s}\n"
                       f"Answer with only the number.", meta={"vis": vis, "n_inv": n_inv})


def invisible_count(rng):
    vis = "".join(rng.choice(LOW) for _ in range(rng.randint(8, 16)))
    n_inv = rng.randint(1, 7)
    s = _interleave(rng, vis, ZW, n_inv)
    return dict(task="invisible_count", kind="int", answer=str(n_inv),
                prompt=f"How many INVISIBLE / zero-width characters (ZWSP U+200B, ZWNJ, ZWJ, BOM U+FEFF, "
                       f"word-joiner, soft-hyphen) are hidden in this string?\n{s}\n"
                       f"Answer with only the number.", meta={"n_inv": n_inv})


def strip_invisible(rng):
    vis = "".join(rng.choice(LOW) for _ in range(rng.randint(8, 16)))
    s = _interleave(rng, vis, ZW, rng.randint(2, 7))
    return dict(task="strip_invisible", kind="exact", answer=vis,
                prompt=f"Remove every invisible / zero-width character (ZWSP, ZWNJ, ZWJ, BOM, word-joiner, "
                       f"soft-hyphen) from this string and output only the remaining visible characters.\n"
                       f"{s}", meta={"vis": vis})


def bidi_detect(rng):
    vis = "".join(rng.choice(LOW) for _ in range(rng.randint(8, 16)))
    if rng.random() < 0.5:
        s = _interleave(rng, vis, BIDI, rng.randint(1, 2)); ans = "yes"
    else:
        s = vis; ans = "no"
    return dict(task="bidi_detect", kind="yn", answer=ans,
                prompt=f'Does this string contain any Unicode bidirectional control character (e.g. '
                       f'RLO U+202E, LRE, PDF, or an isolate U+2066-U+2069) -- the class used in '
                       f'"Trojan Source" attacks? Answer yes or no.\n{s}', meta={})


def combining_count(rng):
    base = [rng.choice(LOW) for _ in range(rng.randint(8, 16))]
    n_comb = 0
    out = []
    for c in base:
        out.append(c)
        if rng.random() < 0.4:
            out.append(rng.choice(COMB)); n_comb += 1
    s = "".join(out)
    return dict(task="combining_count", kind="int", answer=str(n_comb),
                prompt=f"How many combining diacritical marks (e.g. U+0301 acute, U+0300 grave, U+0308 "
                       f"diaeresis) are in this string? Count the marks, not the base letters.\n{s}\n"
                       f"Answer with only the number.", meta={"n_comb": n_comb})


TASKS = {f.__name__: f for f in [
    total_codepoints_invisible, invisible_count, strip_invisible, bidi_detect, combining_count,
]}
