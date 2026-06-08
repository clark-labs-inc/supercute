"""SUPERCUTE Unicode / encoding tasks -- the core byte-vs-token frontier.

Grapheme vs code-point vs UTF-8-byte counting (emoji ZWJ sequences, combining
marks, CJK), canonical normalization equivalence, homoglyph attacks, and
base64/hex decoding. These are where tokenizers AND naive character counting both
fail, and where a byte/grapheme-aware model has the real advantage. Ground truth
is exact (constructed from known graphemes; computed with stdlib unicodedata/base64).
"""
from __future__ import annotations

import base64
import random
import unicodedata

# (display, n_codepoints, is_single_grapheme) building blocks
_GRAPHEMES = [
    ("a", 1), ("Z", 1), ("7", 1), ("中", 1), ("ñ", 1), ("日", 1), ("π", 1),
    ("é", 2), ("ä", 2), ("ô", 2),                 # base + combining accent (1 grapheme)
    ("👍", 1), ("🎉", 1), ("🚀", 1), ("café"[:1], 1),
    ("👨‍👩‍👧", 5), ("👩‍🚀", 3), ("🏳️‍🌈", 4),  # ZWJ sequences (1 grapheme each)
    ("🇺🇸", 2), ("🇯🇵", 2),                                          # flag = 2 regional indicators (1 grapheme)
]
# NOTE: homoglyph_detect was tested vs qwen 3.5 flash and CUT -- qwen scored 1.000.
# A confusable like Cyrillic 'а' is a DISTINCT code point, so a token model sees it
# exactly as easily as a byte model would; it is anti-byte-frontier. A byte-valid
# successor (zero-width / invisible-character detection, where tokenizers drop or
# merge the char) is proposed in the README's "missing domains" section.


def grapheme_count(rng):
    pieces = [rng.choice(_GRAPHEMES) for _ in range(rng.randint(6, 14))]
    s = "".join(p[0] for p in pieces)
    return dict(task="grapheme_count", kind="int", answer=str(len(pieces)),
                prompt=f"How many user-perceived characters (extended grapheme clusters) are in this "
                       f"string? Treat each emoji (including multi-part emoji) and each accented letter "
                       f"as ONE character.\n{s}\nAnswer with only the number.", meta={"s": s})


def codepoint_count(rng):
    pieces = [rng.choice(_GRAPHEMES) for _ in range(rng.randint(6, 14))]
    s = "".join(p[0] for p in pieces)
    return dict(task="codepoint_count", kind="int", answer=str(len(s)),
                prompt=f"How many Unicode code points (not grapheme clusters, not bytes) are in this "
                       f"string?\n{s}\nAnswer with only the number.", meta={"s": s})


def utf8_byte_length(rng):
    pieces = [rng.choice(_GRAPHEMES) for _ in range(rng.randint(5, 12))]
    s = "".join(p[0] for p in pieces)
    return dict(task="utf8_byte_length", kind="int", answer=str(len(s.encode("utf-8"))),
                prompt=f"How many bytes does this string occupy when encoded as UTF-8?\n{s}\n"
                       f"Answer with only the number.", meta={"s": s})


def nfc_equivalent(rng):
    word = "".join(rng.choice("aeiounc") for _ in range(rng.randint(4, 7)))
    combine = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú",
               "n": "ñ", "c": "ç"}
    decomposed = "".join(combine.get(c, c) for c in word)
    precomposed = unicodedata.normalize("NFC", decomposed)
    if rng.random() < 0.5:
        a, b, ans = decomposed, precomposed, "yes"
    else:
        a, b = decomposed, precomposed
        i = rng.randrange(len(word)); b = unicodedata.normalize("NFC",
              "".join(combine.get(c, c) for c in word[:i] + rng.choice("xyz") + word[i + 1:]))
        ans = "yes" if unicodedata.normalize("NFC", a) == unicodedata.normalize("NFC", b) else "no"
    return dict(task="nfc_equivalent", kind="yn", answer=ans,
                prompt=f"Are these two strings canonically equivalent under Unicode NFC normalization "
                       f"(i.e. the same text, possibly composed vs decomposed)?\nA: {a}\nB: {b}\n"
                       f"Answer yes or no.", meta={"a": a, "b": b})


def base64_decode_char(rng):
    raw = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(rng.randint(24, 44)))
    enc = base64.b64encode(raw.encode()).decode()
    k = rng.randint(1, len(raw))
    return dict(task="base64_decode_char", kind="str", answer=raw[k - 1],
                prompt=f"Decode this Base64 string and give character number {k} (1-indexed) of the "
                       f"decoded text:\n{enc}\nAnswer with only the single character.", meta={"enc": enc, "k": k})


def hex_decode_char(rng):
    raw = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz ") for _ in range(rng.randint(20, 40)))
    enc = raw.encode().hex()
    k = rng.randint(1, len(raw))
    return dict(task="hex_decode_char", kind="str", answer=raw[k - 1],
                prompt=f"This is ASCII text hex-encoded. Decode it and give character number {k} "
                       f"(1-indexed) of the original text:\n{enc}\nAnswer with only the single character "
                       f"(it may be a space; if so answer the word space).",
                meta={"enc": enc, "k": k, "raw": raw})


TASKS = {f.__name__: f for f in [
    grapheme_count, codepoint_count, utf8_byte_length, nfc_equivalent,
    base64_decode_char, hex_decode_char,
]}
