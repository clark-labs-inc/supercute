"""SUPERCUTE tokenization battery: a broad sweep of tokenization-adversarial task
ideas, weighted toward PERCEPTION-LAYER failures -- distinctions the tokenizer erases
so reasoning cannot recover them (homoglyphs read as their Latin twins, invisible
characters, novel/unmemorizable combining stacks, confusable digits, exact bytes).

Each generator(rng) -> dict(task, kind, answer, prompt, meta) with EXACT ground truth.
Run the sweep with: python -m supercute.sweep --module tok --model openai/gpt-5.5
Tasks GPT-5.5 fails graduate into the benchmark.
"""
from __future__ import annotations

import random
import string
import unicodedata

LOW = string.ascii_lowercase
HOMO = {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у",
        "i": "і", "s": "ѕ", "j": "ј", "h": "һ", "k": "к", "m": "м", "t": "т"}   # Cyrillic
INVIS = ["​", "‌", "‍", "﻿", "⁠", "­", "᠎"]
COMB = [chr(c) for c in range(0x300, 0x342)]                                    # combining marks
WS = ["\t", " ", " ", " ", " ", "　", " ", " "]
AR = {str(d): chr(0x0660 + d) for d in range(10)}      # Arabic-Indic digits
FW = {str(d): chr(0xFF10 + d) for d in range(10)}      # fullwidth digits
ASTRAL = ["𝔸", "𝕏", "🜔", "𐎀", "𝟙", "🂡", "𝛀", "🝳"]    # > U+FFFF


def _w(rng, n):
    return "".join(rng.choice(LOW) for _ in range(n))


# ---- perception-layer: homoglyphs -------------------------------------------

def homoglyph_count(rng):
    base = [rng.choice(list(HOMO)) for _ in range(rng.randint(8, 16))]
    k = rng.randint(1, 4)
    idx = rng.sample(range(len(base)), k)
    chars = [HOMO[c] if i in idx else c for i, c in enumerate(base)]
    s = "".join(chars)
    return dict(task="homoglyph_count", kind="int", answer=str(k),
                prompt=f'How many characters in "{s}" are NOT standard ASCII letters (i.e. are '
                       f'look-alikes from another script)? Answer with only the number.', meta={})


def homoglyph_position(rng):
    base = [rng.choice(list(HOMO)) for _ in range(rng.randint(8, 16))]
    i = rng.randrange(len(base))
    chars = [HOMO[c] if j == i else c for j, c in enumerate(base)]
    s = "".join(chars)
    return dict(task="homoglyph_position", kind="int", answer=str(i + 1),
                prompt=f'Exactly one character in "{s}" is a non-ASCII look-alike from another script. '
                       f'Give its 1-indexed position. Answer with only the number.', meta={})


def homoglyph_strip(rng):
    base = [rng.choice(list(HOMO)) for _ in range(rng.randint(8, 14))]
    idx = set(rng.sample(range(len(base)), rng.randint(1, 4)))
    s = "".join(HOMO[c] if i in idx else c for i, c in enumerate(base))
    ans = "".join(c for i, c in enumerate(base) if i not in idx)
    return dict(task="homoglyph_strip", kind="str", answer=ans,
                prompt=f'Remove every non-ASCII look-alike character from "{s}", keeping only the '
                       f'genuine ASCII letters in order. Output only the resulting string.', meta={})


# ---- perception-layer: invisible / combining --------------------------------

def invisible_count(rng):
    vis = _w(rng, rng.randint(8, 14))
    k = rng.randint(1, 6)
    chars = list(vis)
    for _ in range(k):
        chars.insert(rng.randint(0, len(chars)), rng.choice(INVIS))
    return dict(task="invisible_count", kind="int", answer=str(k),
                prompt=f"How many invisible / zero-width characters are hidden in this string?\n"
                       f"{''.join(chars)}\nAnswer with only the number.", meta={})


def invisible_position(rng):
    vis = list(_w(rng, rng.randint(8, 14)))
    i = rng.randint(0, len(vis))
    vis.insert(i, rng.choice(INVIS))
    return dict(task="invisible_position", kind="int", answer=str(i + 1),
                prompt=f"Exactly one invisible / zero-width character is hidden in this string. Give its "
                       f"1-indexed code-point position.\n{''.join(vis)}\nAnswer with only the number.", meta={})


def combining_count(rng):
    out, k = [], 0
    for _ in range(rng.randint(8, 16)):
        out.append(rng.choice(LOW))
        for _ in range(rng.randint(0, 2)):
            out.append(rng.choice(COMB)); k += 1
    return dict(task="combining_count", kind="int", answer=str(k),
                prompt=f"How many combining diacritical mark code points (U+0300-U+0341) are in this "
                       f"string?\n{''.join(out)}\nAnswer with only the number.", meta={})


# ---- perception-layer: confusable digits ------------------------------------

def confusable_digit_sum(rng):
    real = [rng.randint(0, 9) for _ in range(rng.randint(8, 14))]
    asc = set(rng.sample(range(len(real)), rng.randint(2, len(real) - 2)))
    chars, ssum = [], 0
    for i, d in enumerate(real):
        if i in asc:
            chars.append(str(d)); ssum += d
        else:
            chars.append(rng.choice([AR[str(d)], FW[str(d)]]))
    return dict(task="confusable_digit_sum", kind="int", answer=str(ssum),
                prompt=f'Some digits in "{"".join(chars)}" are real ASCII digits (0-9) and some are '
                       f'look-alike digits from other scripts. Sum ONLY the real ASCII digits. Answer '
                       f'with only the number.', meta={})


# ---- perception-layer: normalization / case --------------------------------

def nfc_changes(rng):
    word = _w(rng, rng.randint(4, 7))
    cmb = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "n": "ñ", "c": "ç"}
    if rng.random() < 0.5:
        # decomposed form (base + combining) -> NFC changes it
        s = "".join(c + "́" if c in "aeiou" else c for c in word)
        ans = "yes"
    else:
        s = word
        ans = "no"
    ans = "yes" if unicodedata.normalize("NFC", s) != s else "no"
    return dict(task="nfc_changes", kind="yn", answer=ans,
                prompt=f'Does applying Unicode NFC normalization CHANGE this string (i.e. is it not '
                       f'already in NFC form)?\n{s}\nAnswer yes or no.', meta={})


def casefold_count(rng):
    special = ["ß", "İ", "ﬁ", "ﬂ", "ǆ", "ﬀ", "ẞ"]
    base = [rng.choice(LOW) for _ in range(rng.randint(6, 12))]
    k = rng.randint(1, 3)
    for _ in range(k):
        base.insert(rng.randint(0, len(base)), rng.choice(special))
    s = "".join(base)
    ans = sum(1 for c in s if len(c.casefold()) != 1 or c.casefold() != c.lower())
    return dict(task="casefold_count", kind="int", answer=str(ans),
                prompt=f'In "{s}", how many characters change to MORE THAN ONE character (or otherwise '
                       f'differ) under Unicode case-folding (e.g. ß -> ss)? Answer with only the number.',
                meta={})


# ---- bytes / code points ----------------------------------------------------

def utf8_len(rng):
    pool = LOW + "中日本ñéüαβγ" + "".join(ASTRAL)
    s = "".join(rng.choice(pool) for _ in range(rng.randint(8, 16)))
    return dict(task="utf8_len", kind="int", answer=str(len(s.encode("utf-8"))),
                prompt=f"How many bytes does this string occupy in UTF-8?\n{s}\nAnswer with only the number.",
                meta={})


def codepoint_hex(rng):
    pool = "中日本ñéüαβγ" + "".join(ASTRAL) + LOW
    s = "".join(rng.choice(pool) for _ in range(rng.randint(6, 12)))
    pos = rng.randint(1, len(s))
    return dict(task="codepoint_hex", kind="str", answer=f"{ord(s[pos-1]):x}",
                prompt=f"What is the Unicode code point of character number {pos} (1-indexed) of this "
                       f"string, in lowercase hexadecimal (no 'U+' prefix)?\n{s}\nAnswer with only the hex.",
                meta={})


def astral_count(rng):
    pool = LOW + "中ñé" + "".join(ASTRAL)
    s = "".join(rng.choice(pool) for _ in range(rng.randint(10, 18)))
    ans = sum(1 for c in s if ord(c) > 0xFFFF)
    return dict(task="astral_count", kind="int", answer=str(ans),
                prompt=f"How many characters in this string are 'astral' code points above U+FFFF (they "
                       f"need a surrogate pair / 4 UTF-8 bytes)?\n{s}\nAnswer with only the number.", meta={})


# ---- repetition / run tokenization ------------------------------------------

def long_run_len(rng):
    pre, post = _w(rng, rng.randint(2, 6)), _w(rng, rng.randint(2, 6))
    ch = rng.choice(LOW)
    n = rng.randint(40, 130)
    return dict(task="long_run_len", kind="int", answer=str(n),
                prompt=f"How many times does the character '{ch}' repeat consecutively in the run inside "
                       f"this string?\n{pre}{ch * n}{post}\nAnswer with only the number.", meta={})


def rle_char_at(rng):
    parts, expanded = [], []
    while len(expanded) < 60:
        c = rng.choice(LOW); k = rng.randint(2, 15)
        parts.append(f"{c}{k}"); expanded += [c] * k
    pos = rng.randint(1, len(expanded))
    return dict(task="rle_char_at", kind="str", answer=expanded[pos - 1],
                prompt=f"This is run-length encoded (letter then count): {''.join(parts)}. After expanding "
                       f"it, what is character number {pos} (1-indexed)? Answer with only that character.",
                meta={})


# ---- number tokenization ----------------------------------------------------

def digit_at_huge(rng):
    s = "".join(rng.choice("0123456789") for _ in range(rng.randint(120, 200)))
    s = "1" + s[1:]
    pos = rng.randint(int(len(s) * 0.4), len(s))
    return dict(task="digit_at_huge", kind="str", answer=s[pos - 1],
                prompt=f"What is digit number {pos} (counting from the left, 1-indexed) of this "
                       f"{len(s)}-digit number?\n{s}\nAnswer with only that digit.", meta={})


def count_digit_huge(rng):
    s = "".join(rng.choice("0123456789") for _ in range(rng.randint(100, 160)))
    d = rng.choice("0123456789")
    return dict(task="count_digit_huge", kind="int", answer=str(s.count(d)),
                prompt=f"How many times does the digit {d} appear in this number?\n{s}\n"
                       f"Answer with only the number.", meta={})


def compare_huge(rng):
    n = rng.randint(60, 100)
    a = "9" * rng.randint(0, n // 4) + "".join(rng.choice("0123456789") for _ in range(n))
    a = a[:n] if len(a) >= n else a + "0" * (n - len(a))
    b = list(a)
    i = rng.randrange(n)
    b[i] = rng.choice([c for c in "0123456789" if c != a[i]])
    b = "".join(b)
    return dict(task="compare_huge", kind="str", answer="A" if a > b else "B",
                prompt=f"Which {n}-digit number is larger?\nA: {a}\nB: {b}\nAnswer with only A or B.",
                meta={})


# ---- segmentation / boundaries ----------------------------------------------

def grapheme_at(rng):
    units = ["a", "Z", "中", "é", "👍", "👨‍👩‍👧", "🇺🇸", "ñ", "🚀", "ô"]
    pieces = [rng.choice(units) for _ in range(rng.randint(8, 16))]
    s = "".join(pieces)
    pos = rng.randint(1, len(pieces))
    return dict(task="grapheme_at", kind="str", answer=pieces[pos - 1],
                prompt=f"Treating each emoji (including multi-part ones) and each accented letter as ONE "
                       f"user-perceived character, what is character number {pos} (1-indexed) of this "
                       f"string?\n{s}\nOutput only that one user-perceived character.", meta={})


def reverse_graphemes(rng):
    units = ["a", "b", "中", "é", "👍", "🇯🇵", "ñ", "🚀"]
    pieces = [rng.choice(units) for _ in range(rng.randint(6, 10))]
    s = "".join(pieces)
    ans = "".join(reversed(pieces))
    return dict(task="reverse_graphemes", kind="str", answer=ans,
                prompt=f"Reverse the ORDER of the user-perceived characters in this string (keep each "
                       f"emoji and accented letter intact, just reverse their order). Output only the "
                       f"result.\n{s}", meta={})


TASKS = {f.__name__: f for f in [
    homoglyph_count, homoglyph_position, homoglyph_strip,
    invisible_count, invisible_position, combining_count, confusable_digit_sum,
    nfc_changes, casefold_count, utf8_len, codepoint_hex, astral_count,
    long_run_len, rle_char_at, digit_at_huge, count_digit_huge, compare_huge,
    grapheme_at, reverse_graphemes,
]}
