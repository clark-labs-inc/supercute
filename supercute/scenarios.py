"""SUPERCUTE scenario generators: realistic finance / healthcare byte-string tasks
with exact deterministic ground truth. Designed to be hard for tokenizer LLMs
(long IDs, exact character positions, checksums, transpositions) and tractable for
a model with true character access.

Each generator(rng) -> dict(task, prompt, answer, kind, meta). kind in {int,yn,str}.
"""
from __future__ import annotations

import random
import string

DIGITS = "0123456789"
ALNUM = string.ascii_uppercase + DIGITS

# ---- checksum primitives ----------------------------------------------------

def luhn_check_digit(body: str) -> str:
    tot = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch)
        if i % 2 == 0:          # becomes an even position from right in the full number -> doubled
            d *= 2
            if d > 9:
                d -= 9
        tot += d
    return str((10 - tot % 10) % 10)


def luhn_valid(num: str) -> bool:
    tot = 0
    for i, ch in enumerate(reversed(num)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
    return tot % 10 == 0


def _iban_check(country: str, bban: str) -> str:
    rear = bban + country + "00"
    n = "".join(str(int(c, 36)) if c.isalpha() else c for c in rear)
    return f"{98 - int(n) % 97:02d}"


def iban_valid(iban: str) -> bool:
    s = iban[4:] + iban[:4]
    n = "".join(str(int(c, 36)) if c.isalpha() else c for c in s)
    return int(n) % 97 == 1


# ---- realistic string makers ------------------------------------------------

def _card(rng):
    body = "4" + "".join(rng.choice(DIGITS) for _ in range(14))
    return body + luhn_check_digit(body)


def _iban(rng):
    country = rng.choice(["GB", "DE", "FR", "NL", "ES", "IT"])
    bban = "".join(rng.choice(DIGITS) for _ in range(18))
    return country + _iban_check(country, bban) + bban


def _npi(rng):
    body = "".join(rng.choice(DIGITS) for _ in range(9))
    return body + luhn_check_digit("80840" + body)


def _acct(rng, lo=20, hi=34):
    return "".join(rng.choice(DIGITS) for _ in range(rng.randint(lo, hi)))


def _mrn(rng, lo=28, hi=44):
    return "".join(rng.choice(ALNUM) for _ in range(rng.randint(lo, hi)))


LASA = [  # real ISMP look-alike/sound-alike drug pairs (different drugs)
    ("hydroxyzine", "hydralazine"), ("dopamine", "dobutamine"), ("prednisone", "prednisolone"),
    ("cycloserine", "cyclosporine"), ("vinblastine", "vincristine"), ("clonidine", "clonazepam"),
    ("metformin", "metronidazole"), ("lamotrigine", "lamivudine"), ("hydromorphone", "morphine"),
    ("chlorpromazine", "chlorpropamide"), ("glipizide", "glyburide"), ("tramadol", "trazodone"),
    ("nifedipine", "nicardipine"), ("celebrex", "celexa"), ("zantac", "zyrtec"),
]


# ---- generators -------------------------------------------------------------

def count_digit_in_id(rng):
    acct = _acct(rng, 90, 170)
    d = rng.choice(DIGITS)
    return dict(task="count_digit_in_id", kind="int", answer=str(acct.count(d)),
                prompt=f"In the account number {acct}, how many times does the digit {d} appear? "
                       f"Answer with only the number.", meta={"id": acct, "d": d})


def nth_char_id(rng):
    mrn = _mrn(rng, 90, 150)
    pos = rng.randint(1, len(mrn))
    return dict(task="nth_char_id", kind="str", answer=mrn[pos - 1],
                prompt=f"What is character number {pos} (1-indexed) of the medical record number "
                       f"{mrn}? Answer with only that single character.", meta={"id": mrn, "pos": pos})


def transposition_locate(rng):
    a = _acct(rng, 22, 34)
    i = rng.randint(0, len(a) - 2)
    while a[i] == a[i + 1]:
        i = rng.randint(0, len(a) - 2)
    b = a[:i] + a[i + 1] + a[i] + a[i + 2:]
    return dict(task="transposition_locate", kind="int", answer=str(i + 1),
                prompt=f"The correct account number is {a} but it was entered as {b}. Two adjacent "
                       f"digits were transposed. Give the 1-indexed position of the FIRST of the two "
                       f"swapped digits. Answer with only the number.", meta={"a": a, "b": b})


def diff_locate(rng):
    a = _acct(rng, 85, 150)
    i = rng.randint(0, len(a) - 1)
    new = rng.choice([c for c in DIGITS if c != a[i]])
    b = a[:i] + new + a[i + 1:]
    return dict(task="diff_locate", kind="int", answer=str(i + 1),
                prompt=f"These two reference numbers differ in exactly one position:\n{a}\n{b}\n"
                       f"Give the 1-indexed position where they differ. Answer with only the number.",
                meta={"a": a, "b": b})


def luhn_validate(rng):
    num = _card(rng)
    if rng.random() < 0.5:
        i = rng.randint(0, 15)
        num = num[:i] + rng.choice([c for c in DIGITS if c != num[i]]) + num[i + 1:]
    yes = luhn_valid(num)
    return dict(task="luhn_validate", kind="yn", answer="yes" if yes else "no",
                prompt=f"Is {num} a valid credit-card number under the Luhn checksum? Answer yes or no.",
                meta={"num": num})


def luhn_localize(rng):
    num = _card(rng)
    i = rng.randint(0, 15)
    bad = num[:i] + rng.choice([c for c in DIGITS if c != num[i]]) + num[i + 1:]
    return dict(task="luhn_localize", kind="int", answer=str(i + 1),
                prompt=f"The credit-card number {bad} fails the Luhn checksum because exactly one digit "
                       f"was mistyped. Give the 1-indexed position of the incorrect digit. Answer with "
                       f"only the number.", meta={"orig": num, "bad": bad})


def iban_validate(rng):
    iban = _iban(rng)
    if rng.random() < 0.5:
        i = rng.randint(4, len(iban) - 1)
        iban = iban[:i] + rng.choice([c for c in DIGITS if c != iban[i]]) + iban[i + 1:]
    yes = iban_valid(iban)
    return dict(task="iban_validate", kind="yn", answer="yes" if yes else "no",
                prompt=f"Is {iban} a valid IBAN under the ISO-7064 mod-97 checksum? Answer yes or no.",
                meta={"iban": iban})


def npi_validate(rng):
    npi = _npi(rng)
    if rng.random() < 0.5:
        i = rng.randint(0, 9)
        npi = npi[:i] + rng.choice([c for c in DIGITS if c != npi[i]]) + npi[i + 1:]
    yes = luhn_valid("80840" + npi)
    return dict(task="npi_validate", kind="yn", answer="yes" if yes else "no",
                prompt=f"Is {npi} a valid 10-digit US National Provider Identifier (NPI) under its "
                       f"Luhn check (prefix 80840)? Answer yes or no.", meta={"npi": npi})


def dosage_safety(rng):
    drug = rng.choice(["metformin", "warfarin", "digoxin", "insulin", "heparin", "morphine"])
    val = rng.choice(["1", "2", "5", "10", "0.5", "2.5", "0.25"])
    unit = rng.choice(["mg", "mcg", "mL", "units"])
    safe = f"{drug} {val} {unit}"
    issue = "safe"
    if rng.random() < 0.6:
        kind = rng.choice(["trailing_zero", "naked_decimal", "U_for_units"])
        if kind == "trailing_zero":
            txt = f"{drug} {val}.0 {unit}" if "." not in val else f"{drug} {val}0 {unit}"
            issue = "trailing_zero"
        elif kind == "naked_decimal":
            txt = f"{drug} .{rng.choice('5 25 75'.split())} {unit}"
            issue = "naked_decimal"
        else:
            txt = f"{drug} {val} U"
            issue = "U_for_units"
    else:
        txt = safe
    return dict(task="dosage_safety", kind="yn", answer="no" if issue != "safe" else "yes",
                prompt=f'Per ISMP safe-notation rules (no trailing zero after a decimal, no naked '
                       f'decimal point, never abbreviate "units" as "U"), is this medication order '
                       f'written safely: "{txt}" ? Answer yes or no.', meta={"txt": txt, "issue": issue})


def lasa_same(rng):
    if rng.random() < 0.5:
        a, b = rng.choice(LASA)
        ans = "no"
    else:
        a = b = rng.choice([x for pair in LASA for x in pair])
        ans = "yes"
    return dict(task="lasa_same", kind="yn", answer=ans,
                prompt=f'Do "{a}" and "{b}" refer to the SAME medication? Answer yes or no.',
                meta={"a": a, "b": b})


def decimal_magnitude(rng):
    base = rng.choice([5, 25, 125, 75])
    a = base / rng.choice([1, 10, 100])
    b = base / rng.choice([1, 10, 100])
    while a == b:
        b = base / rng.choice([1, 10, 100])
    bigger = "A" if a > b else "B"
    return dict(task="decimal_magnitude", kind="str", answer=bigger,
                prompt=f"Two doses: (A) {a:g} mg and (B) {b:g} mg. Which is the LARGER dose? "
                       f"Answer with only A or B.", meta={"a": a, "b": b})


TASKS = {f.__name__: f for f in [
    count_digit_in_id, nth_char_id, transposition_locate, diff_locate,
    luhn_validate, luhn_localize, iban_validate, npi_validate,
    dosage_safety, lasa_same, decimal_magnitude,
]}

# science / engineering task families (biology, chemistry, nuclear, engineering)
from supercute import scenarios_sci  # noqa: E402
from supercute import scenarios_byte  # noqa: E402
from supercute import scenarios_unicode  # noqa: E402
from supercute import scenarios_code  # noqa: E402
from supercute import scenarios_construct  # noqa: E402
from supercute import scenarios_invisible  # noqa: E402
from supercute import scenarios_net  # noqa: E402
from supercute import scenarios_finqa  # noqa: E402  (real-doc verification; empty if no data)
from supercute import scenarios_tabfact  # noqa: E402  (real-doc verification; empty if no data)
from supercute import scenarios_hard  # noqa: E402  (adversarial tier: break frontier models)
from supercute import scenarios_tok  # noqa: E402  (tokenization/perception diagnostic tier)
from supercute import scenarios_realtok  # noqa: E402  (realistic tokenizer-friction workflows)
from supercute import scenarios_publiclift  # noqa: E402  (public-dataset lift templates)
for _m in (scenarios_sci, scenarios_byte, scenarios_unicode, scenarios_code,
           scenarios_construct, scenarios_invisible, scenarios_net,
           scenarios_finqa, scenarios_tabfact, scenarios_hard, scenarios_tok, scenarios_realtok,
           scenarios_publiclift):
    TASKS.update(_m.TASKS)

# NOTE: scenarios_crypto.py was tested vs qwen 3.5 flash and the WHOLE module CUT --
# eip55_uppercase_count / eth_addr_compare / base58_alphabet_check all scored 1.000.
# Byte-favorable crypto tasks reduce to counting/compare/char-class that frontier
# models already do; hash-based checksum validation is a coin-flip (not a capability
# gap). The verified Keccak-256 lives in git history if ever needed.

# NOTE: the document-audit suite (scenarios_audit.py) is a SEPARATE track: free-text
# findings scored by an LLM judge (judge.py / run_audit.py), not the deterministic
# grade(). It is intentionally NOT merged into this registry.
