"""SUPERCUTE code/software + COMPOSITION + CONSTRUCTION + linguistics tasks.

Adds the operation types v1 lacked: transform/construct a string (not just report
a value), chain multiple steps, and compute edit-distance-class relations. These
are character-manipulation tasks -- easy for a model with character access, hard
for tokenizer models that must reason about positions they cannot see.
"""
from __future__ import annotations

import random
import string

ALNUM = string.ascii_lowercase + string.digits
PAIRS = {")": "(", "]": "[", "}": "{"}
OPEN = "([{"


# ---- code / software --------------------------------------------------------

def bracket_balance(rng):
    s = ""
    stack = []
    for _ in range(rng.randint(40, 80)):
        if stack and rng.random() < 0.5:
            o = stack.pop(); s += {"(": ")", "[": "]", "{": "}"}[o]
        else:
            o = rng.choice(OPEN); stack.append(o); s += o
    balanced = not stack
    if rng.random() < 0.5 and len(s) > 2:          # corrupt to unbalanced
        i = rng.randrange(len(s)); s = s[:i] + rng.choice("([{)]}") + s[i + 1:]
        st, ok = [], True
        for c in s:
            if c in OPEN: st.append(c)
            elif not st or st.pop() != PAIRS[c]: ok = False; break
        balanced = ok and not st
    return dict(task="bracket_balance", kind="yn", answer="yes" if balanced else "no",
                prompt=f"Are the brackets in this expression correctly balanced and nested?\n{s}\n"
                       f"Answer yes or no.", meta={"s": s})


# NOTE: semver_compare and diff_line_locate were tested against qwen 3.5 flash and
# CUT -- qwen scored 1.000 on both even after hardening. semver_compare is
# rule-knowledge (the model has the SemVer spec memorized, no character access
# needed); diff_line_locate works on a coarse line-unit where tokenization does not
# hurt (char-level position-finding is already covered, and hard, in diff_locate).


def escape_count(rng):
    parts = []
    real = 0
    for _ in range(rng.randint(20, 36)):
        if rng.random() < 0.4:
            parts.append(rng.choice([r"\n", r"\t", r"\\", r'\"'])); real += 1
        else:
            parts.append(rng.choice(string.ascii_lowercase)); real += 1
    s = "".join(parts)
    return dict(task="escape_count", kind="int", answer=str(real),
                prompt=f'After interpreting backslash escape sequences (\\n, \\t, \\\\, \\"), how many '
                       f'actual characters does this string literal contain?\n"{s}"\n'
                       f"Answer with only the number.", meta={"s": s})


def base_convert(rng):
    val = rng.randint(2000, 2_000_000)
    base = rng.choice([2, 2, 2, 8, 16])      # bias to binary: longest bit string, hardest to track
    enc = {2: bin, 8: oct, 16: hex}[base](val)[2:]
    name = {2: "binary", 8: "octal", 16: "hexadecimal"}[base]
    return dict(task="base_convert", kind="int", answer=str(val),
                prompt=f"What is the {name} number {enc} in decimal? Answer with only the number.",
                meta={"enc": enc, "base": base})


# ---- transformation / construction ------------------------------------------

def redact_span(rng):
    s = "".join(rng.choice(ALNUM.upper() + string.digits) for _ in range(rng.randint(60, 110)))
    i = rng.randint(1, len(s) - 10); j = rng.randint(i + 4, min(i + 14, len(s)))
    red = s[:i - 1] + "*" * (j - i + 1) + s[j:]
    return dict(task="redact_span", kind="str", answer=red.lower(),
                prompt=f"Replace characters at positions {i} through {j} (1-indexed, inclusive) of this "
                       f"identifier with asterisks '*', leaving all other characters unchanged. "
                       f"Output only the resulting string.\n{s}", meta={"s": s, "i": i, "j": j})


def insert_at(rng):
    s = "".join(rng.choice(ALNUM) for _ in range(rng.randint(60, 110)))
    i = rng.randint(1, len(s)); ch = rng.choice("XYZ#@")
    out = s[:i] + ch + s[i:]
    return dict(task="insert_at", kind="str", answer=out.lower(),
                prompt=f"Insert the character '{ch}' AFTER position {i} (1-indexed) in this string and "
                       f"output the result, nothing else.\n{s}", meta={"s": s, "i": i, "ch": ch})


# ---- composition (chain operations) -----------------------------------------

def extract_reverse_compare(rng):
    nf = rng.randint(8, 14)
    fields = ["".join(rng.choice(ALNUM) for _ in range(rng.randint(8, 14))) for _ in range(nf)]
    n, m = rng.sample(range(nf), 2)
    if rng.random() < 0.5:
        fields[m] = fields[n][::-1]; ans = "yes"
    else:
        ans = "yes" if fields[n][::-1] == fields[m] else "no"
    rec = "|".join(fields)
    return dict(task="extract_reverse_compare", kind="yn", answer=ans,
                prompt=f"In this pipe-delimited record, reverse the characters of field {n + 1}. Does the "
                       f"result equal field {m + 1} exactly? Answer yes or no.\n{rec}", meta={"rec": rec})


# ---- linguistics ------------------------------------------------------------

def _lev(a, b):
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]; dp[0] = i
        for j, cb in enumerate(b, 1):
            prev, dp[j] = dp[j], min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
    return dp[-1]


def levenshtein(rng):
    a = "".join(rng.choice("abcde") for _ in range(rng.randint(12, 20)))
    b = list(a)
    for _ in range(rng.randint(2, 7)):
        op = rng.choice(["sub", "ins", "del"])
        if op == "sub" and b:
            i = rng.randrange(len(b)); b[i] = rng.choice("abcde")
        elif op == "ins":
            b.insert(rng.randint(0, len(b)), rng.choice("abcde"))
        elif b:
            del b[rng.randrange(len(b))]
    b = "".join(b)
    return dict(task="levenshtein", kind="int", answer=str(_lev(a, b)),
                prompt=f"What is the Levenshtein (edit) distance between \"{a}\" and \"{b}\"? "
                       f"Answer with only the number.", meta={"a": a, "b": b})


def anagram(rng):
    a = "".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(28, 46)))
    if rng.random() < 0.5:
        b = list(a); rng.shuffle(b); b = "".join(b); ans = "yes"
    else:
        b = list(a); i = rng.randrange(len(b)); b[i] = rng.choice(string.ascii_lowercase); rng.shuffle(b)
        b = "".join(b); ans = "yes" if sorted(a) == sorted(b) else "no"
    return dict(task="anagram", kind="yn", answer=ans,
                prompt=f'Are "{a}" and "{b}" anagrams of each other (same letters, same counts)? '
                       f"Answer yes or no.", meta={"a": a, "b": b})


TASKS = {f.__name__: f for f in [
    bracket_balance, escape_count, base_convert,
    redact_span, insert_at, extract_reverse_compare, levenshtein, anagram,
]}
