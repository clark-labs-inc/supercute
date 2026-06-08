"""Grading for SUPERCUTE scenarios. Robust to reasoning-model verbosity."""
from __future__ import annotations

import re


def _answer_span(resp: str) -> str:
    s = resp.strip()
    if "answer:" in s.lower():
        s = re.split(r"[Aa]nswer:?", s)[-1]
    # take the first non-empty line (the answer; reasoning models trail explanation).
    # strip surrounding backticks/quotes -- code-oriented models wrap short answers
    # in `...`; a lone ``` fence line strips to empty and we fall through to the next.
    for line in s.splitlines():
        line = line.strip().strip('`').strip('"').strip()
        if line:
            return line
    return s.strip()


def grade(scn: dict, resp: str) -> bool:
    ans, kind = scn["answer"], scn["kind"]
    span = _answer_span(resp)
    low = span.lower()

    if kind == "int":
        m = re.search(r"-?\d+", span.replace(",", ""))
        return m is not None and m.group() == str(int(ans))

    if kind == "yn":
        toks = re.findall(r"[a-z]+", low)
        first = toks[0] if toks else ""
        if first in ("yes", "no"):
            pred = first
        else:
            yes = any(w in low for w in ("yes", "valid", "safe", "same", "identical"))
            neg = any(w in low for w in ("no", "not", "invalid", "unsafe", "different", "isn't",
                                         "doesn't", "fails"))
            pred = "no" if neg and not first.startswith("yes") else ("yes" if yes else "no")
        return pred == ans

    if kind == "exact":
        # case-SENSITIVE exact match (cipher output, IPv6 canonical form, masked
        # email, EIP-55 case). Strip wrapping punct but never '*' (mask answers).
        return span.strip(" .,'\"`") == ans

    # str: exact (case-insensitive), tolerate surrounding quotes/punct/backticks.
    # NOTE: never strip '*' -- redact_span answers can legitimately begin/end with it.
    return low.strip(" .,'\"`") == ans.strip().lower()


def _last_line(seg: str) -> str:
    for L in reversed(seg.splitlines()):
        L = L.strip().strip("`").strip('"').strip("*").strip()
        if L:
            return L
    return seg.strip()


def grade_robust(scn: dict, resp: str) -> bool:
    """Grader for verbose / reasoning models (Opus, GPT). A reasoning model puts its
    conclusion at the END and may think out loud first, so we look after an explicit
    'answer' marker, else at the last number / last yes-no / last line -- not the
    first line. Used by the multi-model benchmark; the harvester keeps grade()."""
    ans, kind = scn["answer"], scn["kind"]

    if kind == "int":
        marked = re.findall(r"answer[^0-9\-]{0,25}(-?\d[\d,]*)", resp, re.I)
        cands = marked or re.findall(r"-?\d[\d,]*", resp)
        if not cands:
            return False
        try:
            return int(cands[-1].replace(",", "")) == int(ans)
        except ValueError:
            return False

    if kind == "yn":
        toks = re.findall(r"\b(yes|no)\b", resp, re.I)
        if toks:
            return toks[-1].lower() == ans
        low = resp.lower()
        neg = any(w in low for w in ("invalid", "unsafe", "different", "isn't", "doesn't", "fails", "not "))
        pos = any(w in low for w in ("valid", "safe", "same", "identical", "correct"))
        return ("no" if neg else "yes" if pos else "no") == ans

    # str / exact: a reasoning model often embeds the answer in a closing sentence
    # ("Character 38 is J.", "The decoded text is: <cipher>"). Take text after the
    # last 'answer' marker, else the last line, then accept equality, ends-with, or a
    # standalone matching token. Case-sensitive for 'exact', case-insensitive for str.
    seg = resp
    parts = re.split(r"\banswer\b\s*(?:is|:|=|\s)?", resp, flags=re.I)
    if len(parts) > 1 and parts[-1].strip():
        seg = parts[-1]
    line = _last_line(seg)
    norm = (lambda x: x) if kind == "exact" else str.lower
    target = norm(ans.strip())
    if norm(line.strip(" .,'\"`")) == target:
        return True
    tail = norm(line.rstrip(" .,'\"`*"))
    if target and tail.endswith(target) and (len(tail) == len(target) or not tail[-len(target) - 1].isalnum()):
        return True
    if " " not in ans.strip():                          # single-token answer as a word
        for t in re.findall(r"\S+", line):
            if norm(t.strip(" .,'\"`*()[]")) == target:
                return True
    return False
