"""SUPERCUTE science/engineering scenarios: biology (DNA/protein), chemistry
(SMILES, CAS), nuclear/physics (isotopes, scientific notation), engineering
(VIN, ISBN, hashes). Long character strings where one symbol is load-bearing --
maximal tokenizer blindness, exact deterministic ground truth.
"""
from __future__ import annotations

import random
import string

BASES = "ACGT"
COMP = {"A": "T", "T": "A", "C": "G", "G": "C"}
AA = "ACDEFGHIKLMNPQRSTVWY"
HEX = "0123456789abcdef"
RESTRICTION = ["GAATTC", "GGATCC", "AAGCTT", "GTCGAC", "CTGCAG", "TCTAGA"]


def _dna(rng, lo, hi):
    return "".join(rng.choice(BASES) for _ in range(rng.randint(lo, hi)))


def _prot(rng, lo, hi):
    return "".join(rng.choice(AA) for _ in range(rng.randint(lo, hi)))


# ---- biology ----------------------------------------------------------------

def dna_base_count(rng):
    s = _dna(rng, 80, 140); b = rng.choice(BASES)
    return dict(task="dna_base_count", kind="int", answer=str(s.count(b)),
                prompt=f"In this DNA sequence, how many times does base {b} occur?\n{s}\n"
                       f"Answer with only the number.", meta={"seq": s, "base": b})


def dna_point_mutation(rng):
    s = _dna(rng, 70, 120); i = rng.randint(0, len(s) - 1)
    t = s[:i] + rng.choice([b for b in BASES if b != s[i]]) + s[i + 1:]
    return dict(task="dna_point_mutation", kind="int", answer=str(i + 1),
                prompt=f"Reference and patient DNA differ at exactly one position (a point mutation).\n"
                       f"REF: {s}\nPAT: {t}\nGive the 1-indexed position of the mutation. "
                       f"Answer with only the number.", meta={"ref": s, "pat": t})


def dna_revcomp(rng):
    s = _dna(rng, 12, 24)
    rc = "".join(COMP[c] for c in reversed(s))
    return dict(task="dna_revcomp", kind="str", answer=rc,
                prompt=f"Give the reverse complement of the DNA sequence {s} (complement A<->T, C<->G, "
                       f"then reverse the order). Answer with only the resulting sequence.", meta={"seq": s})


def codon_at(rng):
    k = rng.randint(15, 35); s = _dna(rng, k * 3 + 3, k * 3 + 8)
    n = rng.randint(1, len(s) // 3)
    return dict(task="codon_at", kind="str", answer=s[(n - 1) * 3:(n - 1) * 3 + 3],
                prompt=f"Reading the coding sequence {s} as non-overlapping triplets from the start, "
                       f"what is codon number {n}? Answer with only the 3-letter codon.", meta={"seq": s, "n": n})


def motif_find(rng):
    s = _dna(rng, 55, 95); motif = rng.choice(RESTRICTION)
    p = rng.randint(0, len(s) - 6); s = s[:p] + motif + s[p + 6:]
    return dict(task="motif_find", kind="int", answer=str(s.find(motif) + 1),
                prompt=f"At what 1-indexed position does the restriction site {motif} first appear in:\n"
                       f"{s}\nAnswer with only the number.", meta={"seq": s, "motif": motif})


def protein_residue_at(rng):
    p = _prot(rng, 45, 85); i = rng.randint(1, len(p))
    return dict(task="protein_residue_at", kind="str", answer=p[i - 1],
                prompt=f"What amino acid (single-letter code) is at position {i} of this protein?\n{p}\n"
                       f"Answer with only the single letter.", meta={"seq": p, "i": i})


# ---- chemistry --------------------------------------------------------------

_SMILES = [
    ("aspirin", "CC(=O)OC1=CC=CC=C1C(=O)O"), ("caffeine", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"),
    ("ibuprofen", "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"), ("glucose", "C(C1C(C(C(C(O1)O)O)O)O)O"),
    ("nicotine", "CN1CCCC1C2=CN=CC=C2"), ("acetaminophen", "CC(=O)NC1=CC=C(C=C1)O"),
]


def smiles_ring_balance(rng):
    name, sm = rng.choice(_SMILES)
    bad = False
    if rng.random() < 0.5:
        digs = [i for i, c in enumerate(sm) if c.isdigit()]
        if digs:
            j = rng.choice(digs); sm = sm[:j] + sm[j + 1:]; bad = True
    return dict(task="smiles_ring_balance", kind="yn", answer="no" if bad else "yes",
                prompt=f"In this SMILES string, every ring-bond number must appear an even number of "
                       f"times (each opening matched by a closing). Are all ring-closure digits "
                       f"correctly paired in: {sm} ? Answer yes or no.", meta={"smiles": sm})


def cas_validate(rng):
    body = "".join(rng.choice(string.digits) for _ in range(rng.randint(5, 7)))
    chk = sum((i + 1) * int(d) for i, d in enumerate(reversed(body))) % 10
    cas = f"{body[:-2]}-{body[-2:]}-{chk}"
    if rng.random() < 0.5:
        i = rng.randint(0, len(body) - 1)
        b2 = body[:i] + rng.choice([c for c in string.digits if c != body[i]]) + body[i + 1:]
        cas = f"{b2[:-2]}-{b2[-2:]}-{chk}"
    valid = sum((i + 1) * int(d) for i, d in enumerate(reversed(cas.replace("-", "")[:-1]))) % 10 == int(cas[-1])
    return dict(task="cas_validate", kind="yn", answer="yes" if valid else "no",
                prompt=f"Is {cas} a valid CAS Registry Number under its check-digit rule (the check digit "
                       f"equals the sum of position-weighted digits, mod 10)? Answer yes or no.", meta={"cas": cas})


# ---- nuclear / physics ------------------------------------------------------

def sci_notation_compare(rng):
    m1, e1 = rng.randint(10, 99) / 10, rng.randint(-12, 12)
    m2, e2 = rng.randint(10, 99) / 10, rng.randint(-12, 12)
    v1, v2 = m1 * 10 ** e1, m2 * 10 ** e2
    while abs(v1 - v2) / max(v1, v2) < 1e-9:
        e2 = rng.randint(-12, 12); v2 = m2 * 10 ** e2
    return dict(task="sci_notation_compare", kind="str", answer="A" if v1 > v2 else "B",
                prompt=f"Two measured cross-sections: (A) {m1:g}e{e1} barns and (B) {m2:g}e{e2} barns. "
                       f"Which is LARGER? Answer with only A or B.", meta={"a": (m1, e1), "b": (m2, e2)})


def isotope_neutrons(rng):
    el, z = rng.choice([("U", 92), ("Pu", 94), ("Cs", 55), ("Sr", 38), ("I", 53), ("Co", 27)])
    a = z + rng.randint(z // 2, z + 60)
    return dict(task="isotope_neutrons", kind="int", answer=str(a - z),
                prompt=f"The isotope {el}-{a} has atomic number {z}. How many neutrons does one nucleus "
                       f"contain? Answer with only the number.", meta={"el": el, "a": a, "z": z})


# ---- engineering ------------------------------------------------------------

_VINV = {**{str(d): d for d in range(10)},
         **dict(zip("ABCDEFGHJKLMNPRSTUVWXYZ",
                    [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 5, 7, 9, 2, 3, 4, 5, 6, 7, 8, 9]))}
_VINW = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
_VINCH = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"


def _vin_check(vin):
    r = sum(_VINV[c] * w for c, w in zip(vin, _VINW)) % 11
    return "X" if r == 10 else str(r)


def vin_validate(rng):
    chars = [rng.choice(_VINCH) for _ in range(17)]
    chars[8] = "0"
    chars[8] = _vin_check("".join(chars))
    vin = "".join(chars)
    if rng.random() < 0.5:
        i = rng.choice([k for k in range(17) if k != 8])
        vin = vin[:i] + rng.choice([c for c in _VINCH if c != vin[i]]) + vin[i + 1:]
    valid = _vin_check(vin) == vin[8]
    return dict(task="vin_validate", kind="yn", answer="yes" if valid else "no",
                prompt=f"Is {vin} a valid 17-character Vehicle Identification Number (VIN) under its "
                       f"mod-11 check digit (position 9)? Answer yes or no.", meta={"vin": vin})


def isbn13_validate(rng):
    body = "978" + "".join(rng.choice(string.digits) for _ in range(9))
    chk = (10 - sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(body)) % 10) % 10
    isbn = body + str(chk)
    if rng.random() < 0.5:
        i = rng.randint(0, 12)
        isbn = isbn[:i] + rng.choice([c for c in string.digits if c != isbn[i]]) + isbn[i + 1:]
    valid = (sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(isbn)) % 10) == 0
    return dict(task="isbn13_validate", kind="yn", answer="yes" if valid else "no",
                prompt=f"Is {isbn} a valid ISBN-13 / EAN-13 barcode under its mod-10 check digit? "
                       f"Answer yes or no.", meta={"isbn": isbn})


def hash_match(rng):
    a = "".join(rng.choice(HEX) for _ in range(64))
    if rng.random() < 0.5:
        b = a; ans = "yes"
    else:
        i = rng.randint(0, 63); b = a[:i] + rng.choice([c for c in HEX if c != a[i]]) + a[i + 1:]; ans = "no"
    return dict(task="hash_match", kind="yn", answer=ans,
                prompt=f"Do these two SHA-256 hashes match exactly (no tampering)?\n{a}\n{b}\n"
                       f"Answer yes or no.", meta={"a": a, "b": b})


def hash_diff_locate(rng):
    a = "".join(rng.choice(HEX) for _ in range(64))
    i = rng.randint(0, 63); b = a[:i] + rng.choice([c for c in HEX if c != a[i]]) + a[i + 1:]
    return dict(task="hash_diff_locate", kind="int", answer=str(i + 1),
                prompt=f"These two SHA-256 hashes differ in exactly one hex character.\n{a}\n{b}\n"
                       f"Give the 1-indexed position of the differing character. Answer with only the number.",
                meta={"a": a, "b": b})


TASKS = {f.__name__: f for f in [
    dna_base_count, dna_point_mutation, dna_revcomp, codon_at, motif_find, protein_residue_at,
    smiles_ring_balance, cas_validate, sci_notation_compare, isotope_neutrons,
    vin_validate, isbn13_validate, hash_match, hash_diff_locate,
]}
