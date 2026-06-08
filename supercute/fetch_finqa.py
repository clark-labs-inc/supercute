"""Download FinQA (CC-BY-4.0; real S&P 500 report tables + gold numeric answers) and
distill to data/finqa_records.jsonl: {table, question, answer} for numeric-answer
examples only. Small (drops pre/post text + retrieval fields). Substrate for the
finqa_verify deterministic verification task (scenarios_finqa.py).

    python -m supercute.fetch_finqa
"""
from __future__ import annotations

import json
import os
import urllib.request

BASE = "https://raw.githubusercontent.com/czyssrs/FinQA/main/dataset/"
SPLITS = ["dev.json", "test.json"]
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "finqa_records.jsonl")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SUPERCUTE research"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _numeric(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _clean(s):
    # FinQA text has inline unicode-hex OCR artifacts for smart quotes/dashes
    for a, b in [(" 201c", " \""), ("201c", "\""), (" 201d", "\""), ("201d", "\""),
                 (" 2019", "'"), ("2019 ", "' "), (" 2013 ", "-"), (" 2014 ", "-")]:
        s = s.replace(a, b)
    return s


def _text(parts):
    return _clean(" ".join(p.strip() for p in parts if p and p.strip()))


def main():
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    n = 0
    with open(OUT, "w", encoding="utf-8") as fh:
        for split in SPLITS:
            data = _get(BASE + split)
            for ex in data:
                qa = ex.get("qa", {})
                table = ex.get("table", [])
                exe = qa.get("exe_ans")
                if not _numeric(exe) or len(table) < 2 or len(table[0]) < 2:
                    continue
                pre, post = _text(ex.get("pre_text", [])), _text(ex.get("post_text", []))
                if len(pre) + len(post) > 5000:        # bound, but large docs are desirable here
                    continue
                fh.write(json.dumps({"pre": pre, "table": table, "post": post,
                                     "question": _clean(qa.get("question", "")),
                                     "answer": exe, "program": qa.get("program", "")},
                                    ensure_ascii=False) + "\n")
                n += 1
            print(f"{split}: processed", flush=True)
    print(f"wrote {n} numeric FinQA records -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
