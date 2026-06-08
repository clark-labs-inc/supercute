"""SUPERCUTE networking + time/date tasks.

IPv6 canonicalization (RFC 5952 longest-zero-run :: compression) is construction at
character precision; CIDR membership forces bit-masking; EAN-13 is a real digit
checksum; date arithmetic crosses month/year boundaries. All ground truth is exact
(computed with stdlib datetime / integer math).
"""
from __future__ import annotations

import datetime
import random
import string

HEX = "0123456789abcdef"


# ---- IPv6 ---------------------------------------------------------------------

def _canon(groups):
    """RFC 5952 canonical form from 8 ints: lowercase, no leading zeros, longest
    run (>=2) of zero groups -> '::', leftmost on ties."""
    hx = [format(g, "x") for g in groups]
    best_s, best_l, i = -1, 0, 0
    while i < 8:
        if groups[i] == 0:
            j = i
            while j < 8 and groups[j] == 0:
                j += 1
            if j - i > best_l:
                best_l, best_s = j - i, i
            i = j
        else:
            i += 1
    if best_l < 2:
        return ":".join(hx)
    return ":".join(hx[:best_s]) + "::" + ":".join(hx[best_s + best_l:])


def _rand_groups(rng):
    groups = [rng.randint(0, 0xffff) for _ in range(8)]
    # inject a zero run so compression is meaningful
    start = rng.randint(0, 6)
    for k in range(start, min(8, start + rng.randint(1, 5))):
        groups[k] = 0
    return groups


def ipv6_compress(rng):
    groups = _rand_groups(rng)
    full = ":".join(format(g, "04x") for g in groups)
    return dict(task="ipv6_compress", kind="exact", answer=_canon(groups),
                prompt=f"Compress this fully-expanded IPv6 address to its RFC 5952 canonical form (lowercase, "
                       f"drop leading zeros in each group, replace the single longest run of all-zero groups "
                       f"with '::'). Output only the address.\n{full}", meta={"full": full})


# NOTE: ipv6_expand, cidr_contains, ean13_validate were tested vs qwen 3.5 flash and
# CUT (all 1.000). Expanding '::' is trivial padding; qwen does CIDR bit-masking and
# the EAN-13 mod-10 check correctly. Only ipv6_compress (finding the longest zero run
# to collapse) actually stresses character-level work.


# ---- dates --------------------------------------------------------------------

def _rand_date(rng):
    return datetime.date(2000, 1, 1) + datetime.timedelta(days=rng.randint(0, 9000))


def days_between(rng):
    a = _rand_date(rng)
    b = a + datetime.timedelta(days=rng.randint(1, 1500))
    return dict(task="days_between", kind="int", answer=str((b - a).days),
                prompt=f"How many days are there from {a.isoformat()} to {b.isoformat()} (inclusive of the "
                       f"end, exclusive of the start)? Answer with only the number.", meta={"a": str(a), "b": str(b)})


def iso_add_days(rng):
    a = _rand_date(rng)
    n = rng.randint(15, 400)
    out = a + datetime.timedelta(days=n)
    return dict(task="iso_add_days", kind="exact", answer=out.isoformat(),
                prompt=f"What calendar date is {n} days after {a.isoformat()}? Account for month lengths and "
                       f"leap years. Output only the date in YYYY-MM-DD format.", meta={"a": str(a), "n": n})


TASKS = {f.__name__: f for f in [
    ipv6_compress, days_between, iso_add_days,
]}
