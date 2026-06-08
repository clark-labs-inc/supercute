"""SUPERCUTE pure byte-precision tasks on long realistic strings: counting,
positional, comparison and extraction operations with no semantic shortcut, so a
tokenizer LLM cannot fall back on world knowledge -- it must see the characters.
"""
from __future__ import annotations

import random
import string

DIGITS = "0123456789"
HEX = "0123456789abcdef"
BASES = "ACGT"
ALNUM = string.ascii_uppercase + DIGITS


def _seq(rng, alphabet, lo, hi):
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(lo, hi)))


def hamming_distance(rng):
    n = rng.randint(40, 70)
    a = _seq(rng, BASES, n, n)
    b = list(a)
    k = rng.randint(2, 8)
    for i in rng.sample(range(n), k):
        b[i] = rng.choice([c for c in BASES if c != a[i]])
    b = "".join(b)
    d = sum(x != y for x, y in zip(a, b))
    return dict(task="hamming_distance", kind="int", answer=str(d),
                prompt=f"In how many positions do these two equal-length DNA sequences differ "
                       f"(Hamming distance)?\n{a}\n{b}\nAnswer with only the number.", meta={"a": a, "b": b})


def longest_char_run(rng):
    # build a string with a guaranteed long run somewhere
    s = list(_seq(rng, "AB", 50, 90))
    ch = rng.choice("AB"); start = rng.randint(0, len(s) - 8); run = rng.randint(4, 8)
    for j in range(start, start + run):
        s[j] = ch
    s = "".join(s)
    best = 1; cur = 1
    for i in range(1, len(s)):
        cur = cur + 1 if s[i] == s[i - 1] else 1
        best = max(best, cur)
    return dict(task="longest_char_run", kind="int", answer=str(best),
                prompt=f"What is the length of the longest run of a single repeated character in this "
                       f"string?\n{s}\nAnswer with only the number.", meta={"s": s})


def char_from_end(rng):
    s = _seq(rng, ALNUM, 32, 52); k = rng.randint(2, 12)
    return dict(task="char_from_end", kind="str", answer=s[-k],
                prompt=f"What is the {k}-th character counting from the END of this identifier?\n{s}\n"
                       f"Answer with only the single character.", meta={"s": s, "k": k})


def count_substring(rng):
    s = _seq(rng, "AB", 60, 100); pat = "".join(rng.choice("AB") for _ in range(rng.randint(2, 3)))
    c = sum(1 for i in range(len(s) - len(pat) + 1) if s[i:i + len(pat)] == pat)
    return dict(task="count_substring", kind="int", answer=str(c),
                prompt=f"How many times does the pattern \"{pat}\" occur (overlapping allowed) in:\n{s}\n"
                       f"Answer with only the number.", meta={"s": s, "pat": pat})


def field_extract(rng):
    nfields = rng.randint(6, 10)
    fields = ["".join(rng.choice(ALNUM) for _ in range(rng.randint(3, 7))) for _ in range(nfields)]
    rec = "|".join(fields); n = rng.randint(1, nfields)
    return dict(task="field_extract", kind="str", answer=fields[n - 1].lower(),
                prompt=f"This pipe-delimited record has fields separated by '|'. What is field number "
                       f"{n} (1-indexed)?\n{rec}\nAnswer with only that field's value.", meta={"rec": rec, "n": n})


def hex_byte_at(rng):
    h = _seq(rng, HEX, 48, 64); k = rng.randint(2, len(h) // 2)
    byte = h[(k - 1) * 2:(k - 1) * 2 + 2]
    return dict(task="hex_byte_at", kind="str", answer=byte,
                prompt=f"Reading this hex string as bytes (pairs of hex characters), what is byte number "
                       f"{k} (1-indexed)?\n{h}\nAnswer with only the two hex characters.", meta={"h": h, "k": k})


def count_char_class(rng):
    s = _seq(rng, ALNUM, 40, 70)
    c = sum(ch.isdigit() for ch in s)
    return dict(task="count_char_class", kind="int", answer=str(c),
                prompt=f"How many digit characters (0-9) are in this identifier?\n{s}\n"
                       f"Answer with only the number.", meta={"s": s})


TASKS = {f.__name__: f for f in [
    hamming_distance, longest_char_run, char_from_end, count_substring,
    field_extract, hex_byte_at, count_char_class,
]}
