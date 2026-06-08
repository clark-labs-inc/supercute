"""SUPERCUTE construction / composition / cipher tasks.

The benchmark was ~90% recognition (report a value/position/count). This module adds
the missing operation type: OUTPUT a transformed string, and CHAIN several steps.
Almost all are pure per-character transforms (a byte model can apply them directly;
a tokenizer model must track characters it cannot see). Answers are case-sensitive
where it matters -> kind "exact".
"""
from __future__ import annotations

import random
import string

LOW = string.ascii_lowercase
ALNUM = string.ascii_lowercase + string.digits
VOWELS = "aeiou"


def _words(rng, nmin=3, nmax=6, wmin=3, wmax=8):
    n = rng.randint(nmin, nmax)
    return " ".join("".join(rng.choice(LOW) for _ in range(rng.randint(wmin, wmax))) for _ in range(n))


# ---- ciphers: pure per-character construction --------------------------------

def rot_n_decode(rng):
    n = rng.randint(1, 25)
    plain = _words(rng, 3, 6, 3, 9)
    ciph = "".join(chr((ord(c) - 97 + n) % 26 + 97) if c.isalpha() else c for c in plain)
    return dict(task="rot_n_decode", kind="exact", answer=plain,
                prompt=f"This text is encrypted with a ROT-{n} (Caesar) cipher shifting each letter "
                       f"forward by {n}. Decrypt it. Spaces are unchanged. Output only the plaintext.\n{ciph}",
                meta={"n": n, "ciph": ciph})


def vigenere_decode(rng):
    key = "".join(rng.choice(LOW) for _ in range(rng.randint(3, 5)))
    plain = "".join(rng.choice(LOW) for _ in range(rng.randint(12, 22)))
    ciph = "".join(chr((ord(p) - 97 + (ord(key[i % len(key)]) - 97)) % 26 + 97)
                   for i, p in enumerate(plain))
    return dict(task="vigenere_decode", kind="exact", answer=plain,
                prompt=f"This text is Vigenere-encrypted with the key \"{key}\" (each letter shifted "
                       f"forward by the corresponding key letter, key repeating). Decrypt it. Output only "
                       f"the plaintext.\n{ciph}", meta={"key": key, "ciph": ciph})


def atbash_decode(rng):
    plain = _words(rng, 3, 6, 3, 8)
    enc = "".join(chr(219 - ord(c)) if c.isalpha() else c for c in plain)  # a<->z mirror
    return dict(task="atbash_decode", kind="exact", answer=plain,
                prompt=f"This text is Atbash-encrypted (each letter mapped to its mirror: a<->z, b<->y, "
                       f"...). Decrypt it. Spaces unchanged. Output only the plaintext.\n{enc}",
                meta={"enc": enc})


# ---- per-character construction ----------------------------------------------

def uppercase_vowels(rng):
    s = "".join(rng.choice(LOW) for _ in range(rng.randint(18, 32)))
    out = "".join(c.upper() if c in VOWELS else c for c in s)
    return dict(task="uppercase_vowels", kind="exact", answer=out,
                prompt=f"Rewrite this string with every vowel (a, e, i, o, u) converted to UPPERCASE and "
                       f"all other letters left lowercase. Output only the result.\n{s}", meta={"s": s})


def delete_every_kth(rng):
    s = "".join(rng.choice(ALNUM) for _ in range(rng.randint(22, 34)))
    k = rng.randint(2, 5)
    out = "".join(c for i, c in enumerate(s, 1) if i % k != 0)
    return dict(task="delete_every_kth", kind="exact", answer=out,
                prompt=f"Delete every {k}th character (1-indexed: positions {k}, {2*k}, {3*k}, ...) from "
                       f"this string and output the remaining characters joined together, nothing else.\n{s}",
                meta={"s": s, "k": k})


def reverse_each_word(rng):
    words = _words(rng, 3, 5, 4, 9).split()
    out = " ".join(w[::-1] for w in words)
    return dict(task="reverse_each_word", kind="exact", answer=out,
                prompt=f"Reverse the letters within each space-separated word, keeping the words in their "
                       f"original order. Output only the result.\n{' '.join(words)}", meta={"in": " ".join(words)})


def mask_email(rng):
    local = "".join(rng.choice(LOW + ".") for _ in range(rng.randint(6, 12)))
    local = local.strip(".") or "user"
    dom = rng.choice(["example.com", "mail.org", "corp.net", "acme.io"])
    masked = local[0] + "*" * (len(local) - 2) + local[-1] if len(local) > 2 else local
    out = f"{masked}@{dom}"
    return dict(task="mask_email", kind="exact", answer=out,
                prompt=f"Mask this email for privacy: replace every character of the local part (before the "
                       f"@) EXCEPT the first and last with '*'. Leave the domain unchanged. Output only the "
                       f"masked email.\n{local}@{dom}", meta={"local": local, "dom": dom})


# NOTE: luhn_fix (append the correct Luhn check digit) was tested vs qwen 3.5 flash
# and CUT (1.000) -- computing a Luhn check digit is arithmetic qwen handles, not a
# character-access gap.


# ---- composition (chain steps) -----------------------------------------------

def extract_reverse_upper(rng):
    nf = rng.randint(5, 9)
    fields = ["".join(rng.choice(LOW) for _ in range(rng.randint(4, 8))) for _ in range(nf)]
    n = rng.randint(1, nf)
    out = fields[n - 1][::-1].upper()
    rec = "|".join(fields)
    return dict(task="extract_reverse_upper", kind="exact", answer=out,
                prompt=f"From this pipe-delimited record, take field {n} (1-indexed), reverse its "
                       f"characters, then convert to UPPERCASE. Output only the result.\n{rec}",
                meta={"rec": rec, "n": n})


TASKS = {f.__name__: f for f in [
    rot_n_decode, vigenere_decode, atbash_decode, uppercase_vowels, delete_every_kth,
    reverse_each_word, mask_email, extract_reverse_upper,
]}
