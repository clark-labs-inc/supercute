"""LLM judge for the document-audit suite. Scores a candidate auditor's free-text
findings against the generator's authoritative error list. Default judge is
x-ai/grok-4.3 (a strong reasoning model) per the project contract.

The judge returns, per ground-truth error, whether the candidate caught it, plus a
count of DISTINCT false positives (asserted inconsistencies that are not real -- by
construction every non-injected value in the document is exactly consistent). A
scenario PASSES only with full recall and zero false positives.
"""
from __future__ import annotations

import json
import re

from supercute.client import chat

_INSTR = """You are grading an auditor's report of a financial/technical document.

DOCUMENT THE AUDITOR REVIEWED:
---
{doc}
---

AUTHORITATIVE LIST OF THE ONLY REAL INCONSISTENCIES in this document (ground truth).
Every value NOT named here is exactly correct/consistent:
{gt}

THE CANDIDATE AUDITOR WROTE:
---
{cand}
---

Judge the candidate. Matching is by MEANING: the candidate identifies a ground-truth
error if they point at the same row/value and say it is wrong (exact wording and the
recomputed number need not match). A false positive is any DISTINCT value the
candidate asserts is wrong/inconsistent that is NOT in the ground-truth list (since
every other value is correct, such a claim is necessarily wrong). Do not count vague
hedging or correct restatements as false positives.

Respond with ONLY a JSON object, no prose:
{{"caught": [<true/false for each ground-truth error in order>], "false_positives": <int>}}"""


def _parse(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON in judge output: {text[:200]}")
    obj = json.loads(m.group(0))
    return [bool(x) for x in obj["caught"]], int(obj["false_positives"])


def judge_audit(ep, scn, candidate):
    """Returns dict(passed, recall, false_positives, caught, error). On judge
    transport/parse failure, error=True (caller should exclude, like a transport miss)."""
    errors = scn["errors"]
    gt = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(errors)) if errors \
        else "(NONE. The document is fully consistent; a correct audit finds no errors.)"
    doc = scn["prompt"].split("\n\n", 1)[1]            # strip the instruction, keep the report
    prompt = _INSTR.format(doc=doc, gt=gt, cand=candidate)
    for _ in range(2):
        try:
            raw = chat(ep, [{"role": "user", "content": prompt}], temperature=0.0)
            caught, fp = _parse(raw)
            if len(caught) != len(errors):
                raise ValueError(f"caught length {len(caught)} != {len(errors)}")
            recall = (sum(caught) / len(errors)) if errors else 1.0
            passed = (recall == 1.0) and (fp == 0)
            return dict(passed=passed, recall=recall, false_positives=fp,
                        caught=caught, error=False)
        except Exception as e:
            last = str(e)
    return dict(passed=False, recall=0.0, false_positives=-1, caught=[], error=True, detail=last)
