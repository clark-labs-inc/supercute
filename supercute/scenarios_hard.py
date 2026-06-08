"""SUPERCUTE adversarial tier: creative, compounding byte tasks built to push even
frontier models to the random-guess floor (~3-4%). The design principle: no memorized
shortcut + a wide answer space + error compounding (one wrong character anywhere ruins
the answer). Length is tunable -- crank it until the strongest model cracks.

All ground truth is exact and computed directly. Single-char answers over a 36-symbol
alphabet floor a guessing model at ~2.8%; reconstruction/counting answers floor at ~0%.
"""
from __future__ import annotations

import random
import string
from collections import Counter

A36 = string.ascii_lowercase + string.digits           # 36 symbols
VAL = {c: i + 1 for i, c in enumerate(A36)}            # a=1..z=26, 0=27..9=36

# heavy multi-code-point graphemes (display, by construction len() counts code points)
_HEAVY = [
    "👨‍👩‍👧‍👦", "👨‍👩‍👧", "👩‍🚀", "🧑‍🤝‍🧑", "🏳️‍🌈", "👨‍👨‍👦‍👦",   # ZWJ sequences (3-7 cp)
    "🇺🇸", "🇯🇵", "🇩🇪", "🇧🇷",                                       # flags (2 cp)
    "é", "ä", "ñ", "ô", "ç",                                          # base+combining (2 cp)
    "中", "日", "π", "👍", "🚀", "a", "Z", "7",                        # single cp
]


def char_at_long(rng):
    n = rng.randint(3500, 5500)
    s = "".join(rng.choice(A36) for _ in range(n))
    pos = rng.randint(int(n * 0.45), int(n * 0.95))
    return dict(task="char_at_long", kind="str", answer=s[pos - 1],
                prompt=f"What is the character at position {pos} (1-indexed) of the following "
                       f"{n}-character string? Answer with only that single character.\n{s}",
                meta={"pos": pos, "n": n})


def pointer_chase(rng):
    n = rng.randint(500, 800)
    s = "".join(rng.choice(A36) for _ in range(n))
    k = rng.randint(45, 75)
    i = 0
    for _ in range(k):
        i = (i + VAL[s[i]]) % n
    return dict(task="pointer_chase", kind="str", answer=s[i],
                prompt=f"Start on the 1st character (position 1, 1-indexed) of the string below. Each "
                       f"step: read the current character and move FORWARD by its value (a=1, b=2, ..., "
                       f"z=26, then 0=27, 1=28, ..., 9=36), wrapping back to the start if you run past the "
                       f"end. After exactly {k} steps, what character are you on? Answer with only that "
                       f"single character.\n{s}", meta={"k": k, "n": n})


def iterated_lut(rng):
    """The frontier breaker: long-horizon execution of a shortcut-free state machine.
    A RANDOM 10x10 transition table (no algebraic closed form) is applied to the FULL
    digit state for many rounds. The model cannot shortcut (random table) and cannot
    track just one value (full state mutates) -- it must simulate every cell every
    round. Over ~1500+ interdependent steps, tiny per-step error compounds to certain
    failure even for a near-perfect reasoner (validated: GPT-5.5 0/3 at L=24,K=80;
    fails by compounding error, finish_reason=stop, not budget truncation)."""
    L = rng.randint(20, 26)
    K = rng.randint(55, 85)
    T = [[rng.randint(0, 9) for _ in range(10)] for _ in range(10)]
    cur = [rng.randint(0, 9) for _ in range(L)]
    s0 = "".join(map(str, cur))
    for _ in range(K):
        cur = [T[cur[i]][cur[(i + 1) % L]] for i in range(L)]
    ans = "".join(map(str, cur))
    grid = "\n".join(f"  current={a}:  " + " ".join(str(T[a][b]) for b in range(10)) for a in range(10))
    return dict(task="iterated_lut", kind="str", answer=ans,
                prompt=f"Simulate a cellular automaton over {K} rounds. The transition table T gives the "
                       f"new digit from the current digit (row) and its right-neighbor digit (column "
                       f"0-9):\n{grid}\n\nStarting string ({L} digits): {s0}\n\nEach round, simultaneously "
                       f"replace every digit d at position i with T[d][e], where e is the digit "
                       f"immediately to its right (the last digit's right-neighbor wraps to the first "
                       f"digit). After exactly {K} rounds, output only the resulting {L}-digit string, no "
                       f"spaces.", meta={"L": L, "K": K})


def codepoint_count_deep(rng):
    pieces = [rng.choice(_HEAVY) for _ in range(rng.randint(200, 320))]
    s = "".join(pieces)
    return dict(task="codepoint_count_deep", kind="int", answer=str(len(s)),
                prompt=f"How many Unicode code points are in the following string? Count each ZWJ "
                       f"sequence, flag, and combining mark as its true number of code points (an emoji "
                       f"family or rainbow flag is several code points; a regional-indicator flag is 2; an "
                       f"accented letter written as base+combining is 2).\n{s}\nAnswer with only the number.",
                meta={"graphemes": len(pieces)})


def column_read(rng):
    rows = rng.randint(55, 85)
    width = rng.randint(9, 15)
    lines = ["".join(rng.choice(A36) for _ in range(width)) for _ in range(rows)]
    k = rng.randint(2, width)
    ans = "".join(line[k - 1] for line in lines)
    return dict(task="column_read", kind="str", answer=ans,
                prompt=f"Below are {rows} lines, each {width} characters. Take the character at position "
                       f"{k} (1-indexed) from EVERY line and concatenate them top-to-bottom. Output only "
                       f"the resulting {rows}-character string.\n" + "\n".join(lines), meta={"k": k})


def deinterleave(rng):
    L = rng.randint(60, 95)
    a = "".join(rng.choice(A36) for _ in range(L))
    b = "".join(rng.choice(A36) for _ in range(L))
    inter = "".join(a[i] + b[i] for i in range(L))
    return dict(task="deinterleave", kind="str", answer=a,
                prompt=f"The {2*L}-character string below was built by interleaving two strings A and B "
                       f"character by character: A[1] B[1] A[2] B[2] A[3] B[3] ... Recover string A (the "
                       f"characters at odd positions 1,3,5,...). Output only A, nothing else.\n{inter}",
                meta={"L": L})


def freq_rank(rng):
    n = rng.randint(600, 900)
    # bias the alphabet size so counts are close and a middle rank needs exact counting
    alpha = "".join(rng.sample(string.ascii_lowercase, rng.randint(12, 18)))
    s = "".join(rng.choice(alpha) for _ in range(n))
    cnt = Counter(s)
    order = sorted(cnt, key=lambda c: (-cnt[c], s.index(c)))
    m = rng.randint(3, min(7, len(order)))
    ords = {3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th"}
    return dict(task="freq_rank", kind="str", answer=order[m - 1],
                prompt=f"In the string below, which single character is the {ords[m]} most frequent? Break "
                       f"ties by whichever character appears earliest. Answer with only that one "
                       f"character.\n{s}", meta={"m": m, "n": n})


TASKS = {f.__name__: f for f in [
    char_at_long, pointer_chase, iterated_lut, codepoint_count_deep,
    column_read, deinterleave, freq_rank,
]}
