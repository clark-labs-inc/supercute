"""SUPERCUTE PublicLift: public-dataset-derived hardening templates.

These generators are deterministic, exact-gradeable task shapes designed to be fed by
public datasets (FinQA/TAT-QA, TabFact/WikiTableQuestions, CUAD/ContractNLI,
CORD/SROIE/DocVQA, LogHub, CRUXEval/LiveCodeBench, SWE-bench, SpreadsheetBench).

The module intentionally does NOT redistribute any third-party dataset rows. Instead it
implements the same *procedural lift* you apply to public records:

    real record -> mutable state -> long changelog / patch log -> exact oracle answer

Each task is realistic enough to serve as a drop-in benchmark item and can be swapped
from synthetic seed data to public dataset records using publicdata_adapters.py.
"""
from __future__ import annotations

import json
import random
import string
import unicodedata
from typing import Any


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


# ---- tokenizer-friction normalization ---------------------------------------

CONF = {
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "І": "I", "К": "K", "М": "M",
    "О": "O", "Р": "P", "Т": "T", "Х": "X", "Υ": "Y", "Ζ": "Z", "а": "a", "е": "e",
    "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "‐": "-", "‑": "-", "–": "-",
    "—": "-", "−": "-", "．": ".", "／": "/", "＿": "_", "＃": "#", "﹣": "-",
}
ZW = ["\u200b", "\u200c", "\u200d", "\ufeff"]


def _norm_key(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in {"Cf", "Zs"}:
            continue
        out.append(CONF.get(ch, ch))
    return "".join(out).upper()


def _obf(rng: random.Random, s: str, p: float = 0.16) -> str:
    rev = {v: k for k, v in CONF.items() if len(v) == 1 and v.isalpha()}
    out = []
    for ch in s:
        c = ch
        if ch in string.digits and rng.random() < p:
            c = chr(ord("０") + int(ch))
        elif ch.upper() in rev and rng.random() < p:
            c = rev[ch.upper()]
        elif ch in "-./_#" and rng.random() < p:
            c = rng.choice(["‐", "‑", "–", "．", "／", "＿", "＃"])
        out.append(c)
        if rng.random() < p / 3:
            out.append(rng.choice(ZW))
    return "".join(out)


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100}.{cents % 100:02d}"


def _parse_money(m: str) -> int:
    sign = -1 if m.startswith("-") else 1
    m = m.lstrip("-$")
    a, b = m.split(".")
    return sign * (int(a) * 100 + int(b))


# ---- 1) FinQA/TAT-QA/MultiHiertt-style finance lift -------------------------


def finqa_restatement_rollforward(rng: random.Random):
    segs = ["Cloud", "Support", "Hardware", "Services", "Licenses", "International", "Other"]
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    state = {s: {q: rng.randint(900_000, 7_500_000) for q in quarters} for s in segs}
    initial = json.loads(json.dumps(state))
    events: list[str] = []
    atomic = 0

    for i in range(rng.randint(260, 330)):
        parts = []
        for _ in range(rng.choice([2, 3, 3, 4])):
            op = rng.choices(["adjust", "move", "swap", "zero_to_other"], weights=[45, 35, 15, 5])[0]
            if op == "adjust":
                s, q = rng.choice(segs), rng.choice(quarters)
                delta = rng.randint(-85_000, 85_000)
                state[s][q] += delta
                parts.append(f"ADJUST {_obf(rng, s)} {q} by {_money(delta)}")
                atomic += 1
            elif op == "move":
                a, b = rng.sample(segs, 2)
                qa, qb = rng.choice(quarters), rng.choice(quarters)
                amt = rng.randint(5_000, 110_000)
                state[a][qa] -= amt
                state[b][qb] += amt
                parts.append(f"MOVE {_money(amt)} from {_obf(rng, a)} {qa} to {_obf(rng, b)} {qb}")
                atomic += 2
            elif op == "swap":
                a, b = rng.sample(segs, 2)
                q = rng.choice(quarters)
                state[a][q], state[b][q] = state[b][q], state[a][q]
                parts.append(f"SWAP the {q} balances of {_obf(rng, a)} and {_obf(rng, b)}")
                atomic += 2
            else:
                a = rng.choice([s for s in segs if s != "Other"])
                q = rng.choice(quarters)
                amt = state[a][q]
                state[a][q] = 0
                state["Other"][q] += amt
                parts.append(f"RECLASSIFY all of {_obf(rng, a)} {q} into {_obf(rng, 'Other')} {q}")
                atomic += 2
        events.append(f"R{i+1:03d}: " + "; ".join(parts) + ".")

    target = sorted(rng.sample(segs, 5))
    ans = {s: sum(state[s].values()) for s in target}
    prompt = (
        "PublicLift finance-restatement task, compatible with FinQA/TAT-QA/MultiHiertt records. "
        "The table uses cents. Apply every restatement in order. Segment names in the log may contain "
        "fullwidth digits, zero-width characters, or look-alike letters; normalize with NFKC, remove "
        "format controls/spaces, map obvious Cyrillic/Greek look-alikes to ASCII, and match case-insensitively. "
        "Output only minified JSON mapping each requested segment to its final full-year cents total.\n\n"
        f"Initial quarterly cents by segment:\n{json.dumps(initial, indent=2, sort_keys=True)}\n\n"
        + "Restatement log:\n" + "\n".join(events) + "\n\n"
        f"Requested segments: {', '.join(target)}\n"
    )
    return dict(task="finqa_restatement_rollforward", kind="exact", answer=_j(ans), prompt=prompt,
                meta={"source_family": "FinQA/TAT-QA/MultiHiertt", "events": len(events), "atomic_ops": atomic})


# ---- 2) TabFact/WikiTableQuestions-style table changelog --------------------


def tabfact_table_changelog(rng: random.Random):
    teams = [f"T-{i:02d}" for i in range(1, 22)]
    cities = ["Austin", "Boston", "Denver", "Fresno", "Helena", "Irvine", "Jersey", "Madison", "Omaha", "Raleigh"]
    status = ["active", "pending", "suspended", "merged"]
    rows = {
        t: {"city": rng.choice(cities), "wins": rng.randint(0, 35), "losses": rng.randint(0, 35),
            "points": rng.randint(80, 260), "status": rng.choice(status)}
        for t in teams
    }
    initial = json.loads(json.dumps(rows))
    events = []
    atomic = 0
    for i in range(rng.randint(240, 310)):
        parts = []
        for _ in range(rng.choice([1, 2, 2, 3])):
            op = rng.choices(["inc", "set_status", "move_city", "swap_points"], weights=[52, 22, 14, 12])[0]
            if op == "inc":
                t = rng.choice(teams)
                field = rng.choice(["wins", "losses", "points"])
                delta = rng.randint(-7, 11)
                rows[t][field] += delta
                parts.append(f"{_obf(rng, t)} {field} += {delta}")
                atomic += 1
            elif op == "set_status":
                t = rng.choice(teams)
                st = rng.choice(status)
                rows[t]["status"] = st
                parts.append(f"SET {_obf(rng, t)} status = {st}")
                atomic += 1
            elif op == "move_city":
                t = rng.choice(teams)
                city = rng.choice(cities)
                rows[t]["city"] = city
                parts.append(f"MOVE {_obf(rng, t)} to city {city}")
                atomic += 1
            else:
                a, b = rng.sample(teams, 2)
                rows[a]["points"], rows[b]["points"] = rows[b]["points"], rows[a]["points"]
                parts.append(f"SWAP points between {_obf(rng, a)} and {_obf(rng, b)}")
                atomic += 2
        events.append(f"C{i+1:03d}: " + "; ".join(parts) + ".")

    chosen = sorted(rng.sample(teams, 7))
    ans = {t: {k: rows[t][k] for k in ["city", "wins", "losses", "points", "status"]} for t in chosen}
    prompt = (
        "PublicLift table-change task, compatible with TabFact/WikiTableQuestions/SpreadsheetBench rows. "
        "You are given an initial semi-structured table and a changelog. Team IDs may be obfuscated with "
        "fullwidth digits, zero-width characters, and Unicode look-alikes. Normalize IDs before matching. "
        "Apply changes in order. Output only the requested rows as minified JSON sorted by team ID.\n\n"
        f"Initial table:\n{json.dumps(initial, indent=2, sort_keys=True)}\n\n"
        + "Changelog:\n" + "\n".join(events) + "\n\n"
        f"Requested teams: {', '.join(chosen)}\n"
    )
    return dict(task="tabfact_table_changelog", kind="exact", answer=_j(ans), prompt=prompt,
                meta={"source_family": "TabFact/WikiTableQuestions/SpreadsheetBench", "events": len(events), "atomic_ops": atomic})


# ---- 3) CUAD/ContractNLI-style legal amendment merge ------------------------


def cuad_amendment_merge(rng: random.Random):
    clauses = {
        "C-01": "The Provider shall maintain commercially reasonable security controls for Customer Data.",
        "C-02": "Either party may terminate this Agreement upon thirty days written notice for material breach.",
        "C-03": "Confidential Information excludes information independently developed without reference to the disclosing party materials.",
        "C-04": "Fees are due net thirty days from invoice date and are non-refundable except as expressly stated.",
        "C-05": "The Service Level commitment applies only to production environments and excludes scheduled maintenance.",
        "C-06": "Customer may use the Software solely for internal business purposes during the subscription term.",
        "C-07": "Provider will indemnify Customer against third party claims alleging that the Services infringe intellectual property rights.",
        "C-08": "Neither party is liable for indirect, incidental, special, consequential, or punitive damages.",
        "C-09": "Subprocessors may be engaged if Provider remains responsible for their performance and provides notice.",
        "C-10": "The Agreement is governed by the laws of the State of New York without regard to conflict rules.",
        "C-11": "Audit rights may be exercised once annually upon reasonable prior notice during normal business hours.",
        "C-12": "Upon termination, Customer Data will be exported or deleted according to the data return schedule.",
    }
    initial = dict(clauses)
    inserts = [
        " except for emergency security patches", " subject to documented approval", " unless prohibited by law",
        " including affiliates under common control", " after written confirmation", " for the applicable renewal period",
        " but excluding beta features", " if the affected party mitigates promptly", " and only to the minimum extent necessary",
    ]
    replacements = [
        ("thirty", "forty-five"), ("commercially reasonable", "industry-standard"), ("New York", "Delaware"),
        ("Customer Data", "Protected Data"), ("production", "live"), ("internal business", "authorized business"),
        ("once annually", "twice annually"), ("non-refundable", "refundable only as stated"),
        ("third party", "unaffiliated third-party"), ("scheduled maintenance", "announced maintenance"),
    ]
    events: list[str] = []
    atomic = 0
    for i in range(rng.randint(110, 155)):
        cid = rng.choice(list(clauses))
        op = rng.choices(["append", "prepend", "replace", "delete_sentence_tail"], weights=[30, 18, 42, 10])[0]
        raw = _obf(rng, cid)
        if op == "append":
            txt = rng.choice(inserts).strip()
            clauses[cid] = clauses[cid].rstrip(".") + "; " + txt + "."
            events.append(f"A{i+1:03d}: In {raw}, APPEND sentence tail: {json.dumps(txt)}.")
            atomic += 1
        elif op == "prepend":
            txt = rng.choice(["Notwithstanding the foregoing", "For clarity", "Subject to this Section", "Except as otherwise agreed"])
            clauses[cid] = txt + ", " + clauses[cid][0].lower() + clauses[cid][1:]
            events.append(f"A{i+1:03d}: In {raw}, PREPEND leading phrase: {json.dumps(txt)}.")
            atomic += 1
        elif op == "replace":
            old, new = rng.choice(replacements)
            clauses[cid] = clauses[cid].replace(old, new, 1)
            events.append(f"A{i+1:03d}: In {raw}, REPLACE first occurrence of {json.dumps(old)} with {json.dumps(new)} if present.")
            atomic += 1
        else:
            if ";" in clauses[cid]:
                clauses[cid] = clauses[cid].rsplit(";", 1)[0].rstrip() + "."
            events.append(f"A{i+1:03d}: In {raw}, DELETE the final semicolon-delimited tail if one exists.")
            atomic += 1
    chosen = sorted(rng.sample(list(clauses), 4))
    ans = {c: clauses[c] for c in chosen}
    prompt = (
        "PublicLift legal-redline task, compatible with CUAD/ContractNLI contract records. Clause IDs may contain "
        "Unicode confusables or invisible characters; normalize IDs before matching. Apply amendments in order. "
        "For REPLACE, change only the first occurrence and do nothing if absent. Output only requested final clauses "
        "as minified JSON sorted by clause ID.\n\n"
        f"Initial clauses:\n{json.dumps(initial, indent=2, sort_keys=True)}\n\n"
        + "Amendment log:\n" + "\n".join(events) + "\n\n"
        f"Requested clauses: {', '.join(chosen)}\n"
    )
    return dict(task="cuad_amendment_merge", kind="exact", answer=_j(ans), prompt=prompt,
                meta={"source_family": "CUAD/ContractNLI/LEDGAR", "events": len(events), "atomic_ops": atomic})


# ---- 4) CORD/SROIE/DocVQA-style receipt OCR ETL -----------------------------


def cord_receipt_reconciliation(rng: random.Random):
    cats = ["meals", "office", "travel", "software", "shipping", "supplies"]
    ids = [f"L-{i:03d}" for i in range(1, 31)]
    items = {
        iid: {"cat": rng.choice(cats), "qty": rng.randint(1, 5), "unit": rng.randint(199, 19_999), "active": True}
        for iid in ids
    }
    initial = json.loads(json.dumps(items))
    credits = {c: 0 for c in cats}
    events = []
    atomic = 0
    for i in range(rng.randint(190, 245)):
        op = rng.choices(["qty", "unit", "recategorize", "void", "restore", "coupon"], weights=[24, 24, 18, 13, 8, 13])[0]
        if op == "qty":
            iid = rng.choice(ids)
            q = rng.randint(0, 8)
            items[iid]["qty"] = q
            events.append(f"O{i+1:03d}: OCR correction: line {_obf(rng, iid)} quantity is {q}.")
            atomic += 1
        elif op == "unit":
            iid = rng.choice(ids)
            cents = rng.randint(99, 29_999)
            items[iid]["unit"] = cents
            events.append(f"O{i+1:03d}: OCR correction: line {_obf(rng, iid)} unit price is {_money(cents)}.")
            atomic += 1
        elif op == "recategorize":
            iid = rng.choice(ids)
            c = rng.choice(cats)
            items[iid]["cat"] = c
            events.append(f"O{i+1:03d}: Expense policy correction: line {_obf(rng, iid)} category = {c}.")
            atomic += 1
        elif op == "void":
            iid = rng.choice(ids)
            items[iid]["active"] = False
            events.append(f"O{i+1:03d}: VOID line {_obf(rng, iid)}.")
            atomic += 1
        elif op == "restore":
            iid = rng.choice(ids)
            items[iid]["active"] = True
            events.append(f"O{i+1:03d}: RESTORE line {_obf(rng, iid)}.")
            atomic += 1
        else:
            c = rng.choice(cats)
            amt = rng.randint(50, 5_000)
            credits[c] -= amt
            events.append(f"O{i+1:03d}: Apply category coupon {c} amount -{_money(amt)}.")
            atomic += 1
    totals = {c: credits[c] for c in cats}
    for it in items.values():
        if it["active"]:
            totals[it["cat"]] += it["qty"] * it["unit"]
    ans = {c: totals[c] for c in sorted(cats) if totals[c] != 0}
    prompt = (
        "PublicLift receipt/OCR reconciliation task, compatible with CORD/SROIE/DocVQA receipt records. "
        "Line IDs may contain Unicode look-alikes or invisible characters. Apply corrections in order. "
        "An active line contributes quantity * unit_price cents to its current category; a voided line contributes 0; "
        "coupons are negative category amounts. Output only minified JSON of nonzero final category totals in cents.\n\n"
        f"Initial OCR item table:\n{json.dumps(initial, indent=2, sort_keys=True)}\n\n"
        + "Correction log:\n" + "\n".join(events)
    )
    return dict(task="cord_receipt_reconciliation", kind="exact", answer=_j(ans), prompt=prompt,
                meta={"source_family": "CORD/SROIE/DocVQA", "events": len(events), "atomic_ops": atomic})


# ---- 5) LogHub-style incident replay ---------------------------------------


def loghub_incident_replay(rng: random.Random):
    hosts = [f"h{i:02d}" for i in range(1, 13)]
    svcs = ["auth", "billing", "cache", "etl", "gateway", "search", "worker"]
    severities = [1, 2, 3, 4]
    incidents: dict[str, dict[str, Any]] = {}
    events = []
    next_id = 1
    atomic = 0
    for i in range(rng.randint(260, 340)):
        op = rng.choices(["open", "ack", "escalate", "downgrade", "resolve", "reopen"], weights=[28, 16, 20, 12, 18, 6])[0]
        active = [k for k, v in incidents.items() if v["status"] != "resolved"]
        all_ids = list(incidents)
        if op == "open" or not all_ids:
            iid = f"INC-{next_id:04d}"; next_id += 1
            incidents[iid] = {"svc": rng.choice(svcs), "host": rng.choice(hosts), "sev": rng.choice(severities), "status": "open"}
            events.append(f"L{i+1:03d}: OPEN {_obf(rng, iid)} service={incidents[iid]['svc']} host={incidents[iid]['host']} severity={incidents[iid]['sev']}.")
            atomic += 1
        elif op == "ack" and active:
            iid = rng.choice(active)
            incidents[iid]["status"] = "ack"
            events.append(f"L{i+1:03d}: ACK {_obf(rng, iid)}.")
            atomic += 1
        elif op == "escalate" and active:
            iid = rng.choice(active)
            incidents[iid]["sev"] = max(1, incidents[iid]["sev"] - 1)
            incidents[iid]["status"] = "open"
            events.append(f"L{i+1:03d}: ESCALATE {_obf(rng, iid)} one level toward severity 1 and mark open.")
            atomic += 2
        elif op == "downgrade" and active:
            iid = rng.choice(active)
            incidents[iid]["sev"] = min(4, incidents[iid]["sev"] + 1)
            events.append(f"L{i+1:03d}: DOWNGRADE {_obf(rng, iid)} one level toward severity 4.")
            atomic += 1
        elif op == "resolve" and active:
            iid = rng.choice(active)
            incidents[iid]["status"] = "resolved"
            events.append(f"L{i+1:03d}: RESOLVE {_obf(rng, iid)}.")
            atomic += 1
        else:
            iid = rng.choice(all_ids)
            incidents[iid]["status"] = "open"
            events.append(f"L{i+1:03d}: REOPEN {_obf(rng, iid)}.")
            atomic += 1
    open_rows = [dict(id=iid, svc=v["svc"], host=v["host"], sev=v["sev"], status=v["status"])
                 for iid, v in incidents.items() if v["status"] != "resolved"]
    open_rows.sort(key=lambda r: (r["sev"], r["svc"], r["host"], r["id"]))
    ans = open_rows[:18]
    prompt = (
        "PublicLift incident-log replay task, compatible with LogHub/AIOps log datasets. Incident IDs may be "
        "obfuscated with Unicode confusables or zero-width characters; normalize before matching. Severity 1 is highest. "
        "ESCALATE decreases the numeric severity by 1 to a minimum of 1 and marks the incident open; DOWNGRADE increases "
        "it by 1 to a maximum of 4. RESOLVE removes it from the open list; ACK remains open/active. Output only the top "
        "18 non-resolved incidents as minified JSON array sorted by severity, service, host, id.\n\n"
        + "Log stream:\n" + "\n".join(events)
    )
    return dict(task="loghub_incident_replay", kind="exact", answer=_j(ans), prompt=prompt,
                meta={"source_family": "LogHub/AIOps", "events": len(events), "atomic_ops": atomic, "open": len(open_rows)})


# ---- 6) CRUXEval/LiveCodeBench-style long execution trace -------------------


def cruxeval_stack_trace(rng: random.Random):
    stack = [rng.randint(0, 97) for _ in range(rng.randint(5, 9))]
    initial = list(stack)
    events = []
    atomic = 0
    for i in range(rng.randint(420, 520)):
        op = rng.choices(["push", "pop", "dup", "swap", "rot", "add", "xor", "map", "trim"],
                         weights=[12, 8, 12, 12, 12, 16, 10, 12, 6])[0]
        if op == "push":
            x = rng.randint(0, 255)
            stack.append(x)
            events.append(f"{i+1:03d}. PUSH {x}")
            atomic += 1
        elif op == "pop":
            if stack:
                stack.pop()
            events.append(f"{i+1:03d}. POP if nonempty")
            atomic += 1
        elif op == "dup":
            if stack:
                stack.append(stack[-1])
            events.append(f"{i+1:03d}. DUP top if nonempty")
            atomic += 1
        elif op == "swap":
            if len(stack) >= 2:
                stack[-1], stack[-2] = stack[-2], stack[-1]
            events.append(f"{i+1:03d}. SWAP top two if present")
            atomic += 1
        elif op == "rot":
            k = rng.randint(1, 5)
            if stack:
                k %= len(stack)
                stack[:] = stack[k:] + stack[:k]
            events.append(f"{i+1:03d}. ROTATE_LEFT {k}")
            atomic += max(1, len(stack))
        elif op == "add":
            x = rng.randint(-31, 31)
            if stack:
                stack[-1] = (stack[-1] + x) % 256
            events.append(f"{i+1:03d}. ADD_TOP {x} modulo 256")
            atomic += 1
        elif op == "xor":
            x = rng.randint(0, 255)
            if stack:
                stack[-1] ^= x
            events.append(f"{i+1:03d}. XOR_TOP {x}")
            atomic += 1
        elif op == "map":
            x = rng.randint(-9, 9)
            stack[:] = [(v + x) % 256 for v in stack]
            events.append(f"{i+1:03d}. MAP_ADD {x} modulo 256 to every stack element")
            atomic += len(stack)
        else:
            n = rng.randint(4, 18)
            if len(stack) > n:
                stack[:] = stack[-n:]
            events.append(f"{i+1:03d}. TRIM keep last {n} elements")
            atomic += 1
    prompt = (
        "PublicLift code-execution trace, compatible with CRUXEval/LiveCodeBench/CodeNet transformations. "
        "Execute the stack machine exactly. All arithmetic is modulo 256 where stated. ROTATE_LEFT k moves the first k "
        "elements to the end; if the stack is empty it does nothing. Output only the final stack as a minified JSON array.\n\n"
        f"Initial stack: {initial}\n\nProgram trace:\n" + "\n".join(events)
    )
    return dict(task="cruxeval_stack_trace", kind="exact", answer=_j(stack), prompt=prompt,
                meta={"source_family": "CRUXEval/LiveCodeBench/CodeNet", "events": len(events), "atomic_ops": atomic})


# ---- 7) SWE-bench-style patch manifest replay -------------------------------


def swebench_patch_manifest(rng: random.Random):
    paths = ["pkg/api.py", "pkg/auth.py", "pkg/cache.py", "pkg/etl.py", "pkg/format.py", "tests/test_api.py", "tests/test_auth.py"]
    vocab = ["return ok", "raise ValueError", "cache.clear()", "token = normalize(token)", "assert result", "status = 200",
             "payload = dict(row)", "if item is None:", "continue", "break", "log.debug(event)", "retry += 1"]
    files = {p: [rng.choice(vocab) + f"  # {p}:{i}" for i in range(1, rng.randint(9, 14))] for p in paths}
    initial = {p: list(lines) for p, lines in files.items()}
    events = []
    atomic = 0
    for i in range(rng.randint(155, 210)):
        p = rng.choice(paths)
        lines = files[p]
        op = rng.choices(["replace", "insert", "delete", "move"], weights=[42, 24, 18, 16])[0]
        rawp = _obf(rng, p)
        if op == "replace" or not lines:
            n = rng.randint(1, max(1, len(lines)))
            text = rng.choice(vocab) + f"  # patch {i+1}"
            if lines:
                lines[n-1] = text
            else:
                lines.append(text); n = 1
            events.append(f"P{i+1:03d}: In {rawp}, REPLACE current line {n} with {json.dumps(text)}.")
            atomic += 1
        elif op == "insert":
            n = rng.randint(0, len(lines))
            text = rng.choice(vocab) + f"  # inserted {i+1}"
            lines.insert(n, text)
            events.append(f"P{i+1:03d}: In {rawp}, INSERT after current line {n} text {json.dumps(text)}. Line 0 means insert at top.")
            atomic += 1
        elif op == "delete":
            n = rng.randint(1, len(lines))
            lines.pop(n-1)
            events.append(f"P{i+1:03d}: In {rawp}, DELETE current line {n}.")
            atomic += 1
        else:
            if len(lines) >= 2:
                a = rng.randint(1, len(lines))
                line = lines.pop(a-1)
                b = rng.randint(0, len(lines))
                lines.insert(b, line)
                events.append(f"P{i+1:03d}: In {rawp}, MOVE current line {a} to after current line {b} after removal. Line 0 means top.")
                atomic += 2
            else:
                events.append(f"P{i+1:03d}: In {rawp}, MOVE current line 1 to after current line 0 after removal.")
                atomic += 1
    chosen = sorted(rng.sample(paths, 4))
    ans = {}
    for p in chosen:
        lines = files[p]
        idxs = sorted(set([1, max(1, len(lines)//2), len(lines)]))
        ans[p] = {str(i): lines[i-1] for i in idxs if lines}
    prompt = (
        "PublicLift patch-manifest replay, compatible with SWE-bench/SWE-bench Verified style repositories. "
        "Paths may contain Unicode confusables or invisible characters; normalize before matching. Line numbers are always "
        "the current 1-indexed line numbers at that event. For MOVE, remove the source line first, then insert it after the "
        "specified current line number in the shortened file; line 0 means top. Output only requested final line snapshots "
        "as minified JSON sorted by path.\n\n"
        f"Initial files:\n{json.dumps(initial, indent=2, sort_keys=True)}\n\nPatch queue:\n" + "\n".join(events) + "\n\n"
        f"Requested paths: {', '.join(chosen)}\n"
    )
    return dict(task="swebench_patch_manifest", kind="exact", answer=_j(ans), prompt=prompt,
                meta={"source_family": "SWE-bench/SWE-bench Verified", "events": len(events), "atomic_ops": atomic})


# ---- 8) SpreadsheetBench-style cell reconciliation --------------------------


def spreadsheet_cell_reconciliation(rng: random.Random):
    rows = list(range(1, 25))
    cols = list("ABCD")
    grid = {(c, r): rng.randint(-200, 700) for r in rows for c in cols}
    initial = {f"{c}{r}": grid[(c, r)] for r in rows for c in cols}
    events = []
    atomic = 0

    def val(cell: str) -> int:
        c, r = cell[0], int(cell[1:])
        return grid[(c, r)]

    def setv(cell: str, v: int):
        c, r = cell[0], int(cell[1:])
        grid[(c, r)] = v

    for i in range(rng.randint(180, 240)):
        op = rng.choices(["set", "add", "copy", "swap", "fill"], weights=[26, 28, 18, 14, 14])[0]
        if op == "set":
            cell = rng.choice(cols) + str(rng.choice(rows))
            x = rng.randint(-500, 1200)
            setv(cell, x)
            events.append(f"S{i+1:03d}: SET {_obf(rng, cell)} = {x}.")
            atomic += 1
        elif op == "add":
            cell = rng.choice(cols) + str(rng.choice(rows))
            x = rng.randint(-90, 120)
            setv(cell, val(cell) + x)
            events.append(f"S{i+1:03d}: ADD {x} to {_obf(rng, cell)}.")
            atomic += 1
        elif op == "copy":
            c1, c2 = rng.sample(cols, 2)
            start = rng.randint(1, 20)
            n = rng.randint(2, 4)
            vals = [grid[(c1, start + k)] for k in range(n)]
            for k, x in enumerate(vals):
                grid[(c2, start + k)] = x
            events.append(f"S{i+1:03d}: COPY values {_obf(rng, c1+str(start))}:{_obf(rng, c1+str(start+n-1))} into {_obf(rng, c2+str(start))}:{_obf(rng, c2+str(start+n-1))}.")
            atomic += n
        elif op == "swap":
            a = rng.choice(cols) + str(rng.choice(rows))
            b = rng.choice(cols) + str(rng.choice(rows))
            va, vb = val(a), val(b)
            setv(a, vb); setv(b, va)
            events.append(f"S{i+1:03d}: SWAP {_obf(rng, a)} and {_obf(rng, b)}.")
            atomic += 2
        else:
            c = rng.choice(cols)
            start = rng.randint(1, 21)
            x = rng.randint(-20, 35)
            prev = grid[(c, start)]
            for r in range(start + 1, min(24, start + 4) + 1):
                prev = prev + x
                grid[(c, r)] = prev
            events.append(f"S{i+1:03d}: FILL_DOWN from {_obf(rng, c+str(start))} for up to 4 following rows, each next cell = previous filled value + {x}.")
            atomic += min(4, 24 - start)
    # Derived formula cells at final snapshot.
    derived = {}
    for r in rows:
        derived[f"E{r}"] = grid[("A", r)] + grid[("B", r)] - grid[("C", r)]
        derived[f"F{r}"] = grid[("D", r)] + derived[f"E{r}"]
    targets = sorted(rng.sample(list(initial.keys()) + list(derived.keys()), 18), key=lambda x: (int(x[1:]), x[0]))
    ans = {cell: (derived[cell] if cell[0] in "EF" else val(cell)) for cell in targets}
    prompt = (
        "PublicLift spreadsheet-cell reconciliation, compatible with SpreadsheetBench forum-style spreadsheets. "
        "Cells may be written with fullwidth digits or invisible characters; normalize before matching. Work on value cells A:D. "
        "At the end only, derive E(row)=A(row)+B(row)-C(row), and F(row)=D(row)+E(row). Output requested cells as "
        "minified JSON sorted by cell.\n\n"
        f"Initial A:D cells:\n{json.dumps(initial, indent=2, sort_keys=True)}\n\nOperations:\n" + "\n".join(events) + "\n\n"
        f"Requested cells: {', '.join(targets)}\n"
    )
    return dict(task="spreadsheet_cell_reconciliation", kind="exact", answer=_j(ans), prompt=prompt,
                meta={"source_family": "SpreadsheetBench", "events": len(events), "atomic_ops": atomic})


TASKS = {f.__name__: f for f in [
    finqa_restatement_rollforward,
    tabfact_table_changelog,
    cuad_amendment_merge,
    cord_receipt_reconciliation,
    loghub_incident_replay,
    cruxeval_stack_trace,
    swebench_patch_manifest,
    spreadsheet_cell_reconciliation,
]}
