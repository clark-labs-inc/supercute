"""SUPERCUTE RealTok tier: realistic tokenizer-friction workflows.

These tasks are not isolated Unicode perception probes. They embed byte/character
exactness into work people actually ask LLMs to do: editing a CRM field, applying
API patches, cleaning CSV exports, auditing redactions, merging contract redlines,
reconstructing sequences, and inventory bookkeeping.

Design goal: break frontier reasoning models without relying on crypto, model-
specific token-count questions, or unsafe jailbreak payloads. Every item has exact
programmatic ground truth; the hard settings intentionally require long-horizon,
full-state execution plus tokenizer-sensitive input handling.

Run:
  PYTHONPATH=. python -m supercute.sweep --module realtok --self
  OPENROUTER_API_KEY=... PYTHONPATH=. python -m supercute.sweep --module realtok \
      --model openai/gpt-5.5 --per-task 4 --timeout 240 --workers 4
"""
from __future__ import annotations

import json
import random
import re
import string
import unicodedata
from collections import defaultdict

ZW = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]
SP = [" ", "\t", "\u00a0", "\u2007", "\u202f"]
DASH = ["-", "‐", "‑", "–", "—", "−"]

# Common Cyrillic/Greek confusables that appear in pasted docs, fake IDs, and CSVs.
CONF_TO_ASCII = {
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "І": "I", "К": "K",
    "М": "M", "О": "O", "Р": "P", "Т": "T", "Х": "X", "У": "Y",
    "а": "a", "с": "c", "е": "e", "і": "i", "о": "o", "р": "p", "х": "x", "у": "y",
    "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Χ": "X", "Υ": "Y",
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4", "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
}
ASCII_TO_CONF = {v: k for k, v in CONF_TO_ASCII.items() if len(v) == 1}

WORDS = [
    "shipment", "renewal", "invoice", "followup", "escrow", "clinic", "access",
    "payroll", "warehouse", "routing", "refund", "approval", "staging", "review",
    "license", "contract", "backup", "triage", "onboarding", "account", "release",
]
NAMES = ["Ada", "Ben", "Cy", "Dee", "Eli", "Gia", "Hao", "Ira", "Jo", "Kim", "Liv", "Moe"]
STATUSES = ["new", "open", "waiting", "blocked", "done", "archived"]
TAGS = ["vip", "sla", "bug", "audit", "legal", "pii", "refund", "ops", "hold", "ship"]
OWNERS = ["amy", "bo", "cy", "di", "ev", "flo", "gus", "hal"]


def _strip_format(s: str) -> str:
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cf")


def _norm_key(s: str, keep_dash: bool = True) -> str:
    """NFKC + remove controls/spaces + map confusables + uppercase.
    With keep_dash=False, also remove hyphen-like characters.
    """
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        if unicodedata.category(ch) == "Cf" or ch in SP:
            continue
        if ch in DASH:
            if keep_dash:
                out.append("-")
            continue
        out.append(CONF_TO_ASCII.get(ch, ch))
    return "".join(out).upper()


def _obfuscate_key(rng: random.Random, s: str, p_conf: float = 0.18, p_zw: float = 0.10) -> str:
    out = []
    for ch in s:
        c = ch
        if ch in ASCII_TO_CONF and rng.random() < p_conf:
            c = ASCII_TO_CONF[ch]
        elif ch.isdigit() and rng.random() < p_conf:
            c = chr(0xFF10 + int(ch))
        elif ch == "-" and rng.random() < 0.65:
            c = rng.choice(DASH)
        out.append(c)
        if rng.random() < p_zw:
            out.append(rng.choice(ZW))
        if rng.random() < 0.05:
            out.append(rng.choice(SP[1:]))
    return "".join(out)


def _q(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 1. CRM / support / form typing reconstruction


def crm_typing_reconstruct(rng: random.Random):
    """Reconstruct a single text field from a realistic edit log.

    This is the real-world equivalent of replaying a support-agent transcript,
    browser autofill history, or keystroke-level bug report. It is tokenizer-
    sensitive because cursor positions count characters, pasted snippets may
    contain NBSP/zero-width characters, and every edit shifts later positions.
    """
    base = (
        f"Subject: {rng.choice(WORDS).title()} {rng.randint(10,99)} | "
        f"Owner: {rng.choice(NAMES)} | Due: 2026-{rng.randint(7,12):02d}-{rng.randint(1,28):02d} | "
        f"Note: call vendor before ship"
    )
    cur = list(base)
    cursor = len(cur)
    clips = [
        "urgent", "needs review", "PO" + rng.choice(DASH) + str(rng.randint(1000, 9999)),
        "tax" + rng.choice(SP) + "ID", "Q" + str(rng.randint(1,4)) + " hold",
        "refund approved", "site" + rng.choice(ZW) + "access", "eta " + str(rng.randint(2, 9)) + "d",
        "acct" + rng.choice(DASH) + str(rng.randint(100,999)), "ok", " ", "; ", ", ", ": ", "#" + str(rng.randint(100, 999)),
    ]
    events = ["Start with the cursor at the END of the field."]
    n_ops = rng.randint(95, 130)
    for _ in range(n_ops):
        op = rng.choices(
            ["move", "type", "paste", "backspace", "delete", "replace_next", "insert_at"],
            weights=[18, 20, 22, 12, 10, 10, 8],
        )[0]
        if op == "move":
            cursor = rng.randint(0, len(cur))
            events.append(f"Move cursor to position {cursor} (0 means before the first character).")
        elif op == "insert_at":
            pos = rng.randint(0, len(cur))
            txt = rng.choice(clips)
            cur[pos:pos] = list(txt)
            cursor = pos + len(txt)
            events.append(f"Move cursor to position {pos}; type {_q(txt)}.")
        elif op in ("type", "paste"):
            txt = rng.choice(clips if op == "paste" else WORDS + [" ", ".", ",", ";", str(rng.randint(0,9))])
            cur[cursor:cursor] = list(txt)
            cursor += len(txt)
            events.append(("Paste" if op == "paste" else "Type") + f" {_q(txt)} at the cursor.")
        elif op == "backspace" and cursor > 0:
            k = rng.randint(1, min(4, cursor))
            del cur[cursor - k:cursor]
            cursor -= k
            events.append(f"Backspace {k} character(s).")
        elif op == "delete" and cursor < len(cur):
            k = rng.randint(1, min(4, len(cur) - cursor))
            del cur[cursor:cursor + k]
            events.append(f"Delete {k} character(s) after the cursor.")
        elif op == "replace_next" and cursor < len(cur):
            k = rng.randint(1, min(5, len(cur) - cursor))
            txt = rng.choice(clips)
            del cur[cursor:cursor + k]
            cur[cursor:cursor] = list(txt)
            cursor += len(txt)
            events.append(f"Replace the next {k} character(s) after the cursor with {_q(txt)}.")
        else:
            cursor = rng.randint(0, len(cur))
            events.append(f"Move cursor to position {cursor} (0 means before the first character).")
    field = "".join(cur)
    ans = json.dumps({"field": field}, ensure_ascii=False, separators=(",", ":"))
    prompt = (
        "A support CRM field was edited through the following event log. Character positions are "
        "0-indexed insertion points. Count every Unicode code point, including NBSP and zero-width "
        "characters, as one character when moving the cursor. Replay the log exactly and output only "
        "one-line minified JSON of the form {\"field\":<final string>}.\n\n"
        f"Initial field:\n{base}\n\nEvents:\n" + "\n".join(f"{i+1}. {e}" for i, e in enumerate(events))
    )
    return dict(task="crm_typing_reconstruct", kind="exact", answer=ans, prompt=prompt,
                meta={"ops": n_ops, "answer_len": len(field)})


# ---------------------------------------------------------------------------
# 2. API / ticket-board JSON patch log


def json_patch_ticket_board(rng: random.Random):
    """Apply a long API patch log to a ticket board and output compact JSON."""
    ids = [f"TKT-{rng.randint(100,999)}-{c}" for c in rng.sample(string.ascii_uppercase, 9)]
    board = []
    for tid in ids:
        board.append({
            "id": _obfuscate_key(rng, tid, 0.12, 0.05),
            "owner": rng.choice(OWNERS),
            "status": rng.choice(STATUSES[:4]),
            "priority": rng.randint(1, 5),
            "tags": sorted(rng.sample(TAGS, rng.randint(1, 3))),
        })

    def find_idx(norm_id: str) -> int:
        for i, row in enumerate(board):
            if _norm_key(row["id"]) == norm_id:
                return i
        raise AssertionError(norm_id)

    canon_ids = [_norm_key(x["id"]) for x in board]
    events = []
    for _ in range(rng.randint(72, 96)):
        cid = rng.choice(canon_ids)
        visible = _obfuscate_key(rng, cid, 0.22, 0.12)
        i = find_idx(cid)
        op = rng.choices(["owner", "status", "priority", "add_tag", "remove_tag", "move_after"],
                         weights=[17, 20, 12, 18, 15, 18])[0]
        if op == "owner":
            val = rng.choice(OWNERS)
            board[i]["owner"] = val
            events.append(f"SET owner of ticket {visible} to {val}.")
        elif op == "status":
            val = rng.choice(STATUSES)
            board[i]["status"] = val
            events.append(f"SET status of ticket {visible} to {val}.")
        elif op == "priority":
            val = rng.randint(1, 5)
            board[i]["priority"] = val
            events.append(f"SET priority of ticket {visible} to {val}.")
        elif op == "add_tag":
            tag = rng.choice(TAGS)
            if tag not in board[i]["tags"]:
                board[i]["tags"].append(tag)
                board[i]["tags"].sort()
            events.append(f"ADD tag {tag} to ticket {visible} if absent.")
        elif op == "remove_tag":
            tag = rng.choice(TAGS)
            if tag in board[i]["tags"]:
                board[i]["tags"].remove(tag)
            events.append(f"REMOVE tag {tag} from ticket {visible} if present.")
        else:
            other = rng.choice([x for x in canon_ids if x != cid])
            row = board.pop(i)
            j = find_idx(other)
            board.insert(j + 1, row)
            events.append(f"MOVE ticket {visible} to immediately after ticket {_obfuscate_key(rng, other, 0.22, 0.12)}.")

    # Canonicalize IDs in the answer so success requires correct normalization/matching but not reproducing obfuscation.
    ans_rows = [{**r, "id": _norm_key(r["id"])} for r in board]
    ans = json.dumps(ans_rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    initial = json.dumps(board[:0], ensure_ascii=False)  # unused; keep linter quiet
    del initial
    prompt = (
        "You are replaying an API audit log for a ticket board. Ticket IDs in the log may contain "
        "zero-width characters, fullwidth digits, hyphen variants, and Cyrillic/Greek look-alike letters. "
        "For matching IDs only, normalize with NFKC, remove Unicode format controls and spaces, map common "
        "look-alike letters/digits to ASCII, uppercase, and treat all hyphen-like characters as '-'.\n"
        "Apply every event in order. Tags are sorted alphabetically after each change. Output only the final "
        "ticket list as one-line minified JSON with normalized ASCII IDs and keys sorted.\n\n"
        "Initial ticket list:\n"
        + json.dumps([{**r, "tags": sorted(r["tags"])} for r in ans_rows], ensure_ascii=False, indent=2, sort_keys=True)
        + "\n\nImportant: the initial list above is a SNAPSHOT BEFORE the events below, not the answer.\n\nEvents:\n"
        + "\n".join(f"{i+1}. {e}" for i, e in enumerate(events))
    )
    # Oops: ans_rows was mutated through events and used as initial. Rebuild true initial in a robust way below.
    # This branch is replaced by _json_patch_ticket_board_fixed via assignment at bottom.
    return dict(task="json_patch_ticket_board", kind="exact", answer=ans, prompt=prompt,
                meta={"events": len(events), "tickets": len(board)})


def _json_patch_ticket_board_fixed(rng: random.Random):
    ids = [f"TKT-{rng.randint(100,999)}-{c}" for c in rng.sample(string.ascii_uppercase, 9)]
    board = []
    for tid in ids:
        board.append({
            "id": _obfuscate_key(rng, tid, 0.12, 0.05),
            "owner": rng.choice(OWNERS),
            "status": rng.choice(STATUSES[:4]),
            "priority": rng.randint(1, 5),
            "tags": sorted(rng.sample(TAGS, rng.randint(1, 3))),
        })
    init_board = json.loads(json.dumps(board, ensure_ascii=False))

    def find_idx(norm_id: str) -> int:
        for i, row in enumerate(board):
            if _norm_key(row["id"]) == norm_id:
                return i
        raise AssertionError(norm_id)

    canon_ids = [_norm_key(x["id"]) for x in board]
    events = []
    for _ in range(rng.randint(72, 96)):
        cid = rng.choice(canon_ids)
        visible = _obfuscate_key(rng, cid, 0.22, 0.12)
        i = find_idx(cid)
        op = rng.choices(["owner", "status", "priority", "add_tag", "remove_tag", "move_after"],
                         weights=[17, 20, 12, 18, 15, 18])[0]
        if op == "owner":
            val = rng.choice(OWNERS)
            board[i]["owner"] = val
            events.append(f"SET owner of ticket {visible} to {val}.")
        elif op == "status":
            val = rng.choice(STATUSES)
            board[i]["status"] = val
            events.append(f"SET status of ticket {visible} to {val}.")
        elif op == "priority":
            val = rng.randint(1, 5)
            board[i]["priority"] = val
            events.append(f"SET priority of ticket {visible} to {val}.")
        elif op == "add_tag":
            tag = rng.choice(TAGS)
            if tag not in board[i]["tags"]:
                board[i]["tags"].append(tag)
                board[i]["tags"].sort()
            events.append(f"ADD tag {tag} to ticket {visible} if absent.")
        elif op == "remove_tag":
            tag = rng.choice(TAGS)
            if tag in board[i]["tags"]:
                board[i]["tags"].remove(tag)
            events.append(f"REMOVE tag {tag} from ticket {visible} if present.")
        else:
            other = rng.choice([x for x in canon_ids if x != cid])
            row = board.pop(i)
            j = find_idx(other)
            board.insert(j + 1, row)
            events.append(f"MOVE ticket {visible} to immediately after ticket {_obfuscate_key(rng, other, 0.22, 0.12)}.")
    ans_rows = [{**r, "id": _norm_key(r["id"]), "tags": sorted(r["tags"])} for r in board]
    ans = json.dumps(ans_rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    prompt = (
        "You are replaying an API audit log for a ticket board. Ticket IDs in the log may contain "
        "zero-width characters, fullwidth digits, hyphen variants, and Cyrillic/Greek look-alike letters. "
        "For matching IDs only, normalize with NFKC, remove Unicode format controls and spaces, map common "
        "look-alike letters/digits to ASCII, uppercase, and treat all hyphen-like characters as '-'.\n"
        "Apply every event in order. Tags are sorted alphabetically after each change. Output only the final "
        "ticket list as one-line minified JSON with normalized ASCII IDs and keys sorted.\n\n"
        "Initial ticket list:\n"
        + json.dumps(init_board, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n\nEvents:\n"
        + "\n".join(f"{i+1}. {e}" for i, e in enumerate(events))
    )
    return dict(task="json_patch_ticket_board", kind="exact", answer=ans, prompt=prompt,
                meta={"events": len(events), "tickets": len(board)})

json_patch_ticket_board = _json_patch_ticket_board_fixed
json_patch_ticket_board.__name__ = "json_patch_ticket_board"


# ---------------------------------------------------------------------------
# 3. CSV export cleanup / finance operations


def invoice_csv_unicode_etl(rng: random.Random):
    """Clean a messy invoice CSV and compute a grouped answer."""
    customers = [f"CUST-{rng.randint(100,999)}" for _ in range(9)]
    invoices = [f"INV-{rng.randint(10000,99999)}" for _ in range(48)]
    rows = []
    last = {}
    for rowno in range(1, rng.randint(62, 78)):
        cust = rng.choice(customers)
        inv = rng.choice(invoices)
        typ = rng.choice(["SALE", "SALE", "SALE", "REFUND", "VOID"])
        cents = rng.randint(75, 95000)
        raw_c = _obfuscate_key(rng, cust, 0.22, 0.12)
        raw_i = _obfuscate_key(rng, inv, 0.22, 0.12)
        # Add commas/quotes in memo so CSV parsing cannot be done by naive split.
        memo = rng.choice(["license, annual", "site access", "refund correction", "ship hold", "clinic renewal"])
        row = [str(rowno), raw_c, raw_i, typ, f"{cents//100}.{cents%100:02d}", memo]
        rows.append(row)
        last[_norm_key(inv)] = (rowno, _norm_key(cust), typ, cents)
    totals = defaultdict(int)
    counts = defaultdict(int)
    for _inv, (_rowno, cust, typ, cents) in last.items():
        if typ == "SALE":
            totals[cust] += cents; counts[cust] += 1
        elif typ == "REFUND":
            totals[cust] -= cents; counts[cust] += 1
        # VOID contributes nothing and does not count
    # choose max by absolute balance, tie by customer id
    winner = max(totals, key=lambda c: (abs(totals[c]), c))
    ans = f"{winner}|{totals[winner]}|{counts[winner]}"

    def csv_quote(field: str) -> str:
        if any(ch in field for ch in [",", '"', "\n"]):
            return '"' + field.replace('"', '""') + '"'
        return field

    csv_text = "row,customer_id,invoice_id,type,amount,memo\n" + "\n".join(
        ",".join(csv_quote(x) for x in r) for r in rows
    )
    prompt = (
        "Messy finance export cleanup task. Parse the CSV according to normal CSV quoting rules. "
        "For customer_id and invoice_id, normalize with Unicode NFKC, remove Unicode format controls and "
        "spaces, map Cyrillic/Greek/fullwidth look-alikes to ASCII, uppercase, and treat hyphen variants as '-'. "
        "If the same normalized invoice_id appears multiple times, keep only the LAST row number. SALE adds "
        "amount cents, REFUND subtracts amount cents, VOID is ignored. Group by normalized customer_id.\n\n"
        "Output only: CUSTOMER_ID|BALANCE_IN_CENTS|COUNTED_NONVOID_INVOICE_ROWS for the customer with the "
        "largest absolute final balance; break ties by lexicographically larger customer_id.\n\nCSV:\n" + csv_text
    )
    return dict(task="invoice_csv_unicode_etl", kind="exact", answer=ans, prompt=prompt,
                meta={"rows": len(rows), "unique_invoices": len(last)})


# ---------------------------------------------------------------------------
# 4. Compliance redaction audit


def redaction_leak_audit(rng: random.Random):
    """Find fake PII leaks after normalization-aware redaction rules."""
    domains = ["example.com", "test.org", "corp.invalid", "mail.example"]
    lines = []
    leaking = []
    for i in range(1, rng.randint(58, 74)):
        kind = rng.choices(["benign", "email", "phone", "acct"], weights=[44, 22, 18, 16])[0]
        name = rng.choice(NAMES).lower()
        if kind == "benign":
            text = rng.choice([
                f"line {i}: {name} confirmed lunch order",
                f"line {i}: vendor says route is green",
                f"line {i}: test user at example dot com is documentation only",
                f"line {i}: acct word appears but no digits here",
            ])
        elif kind == "email":
            addr = f"{name}{rng.randint(10,99)}@{rng.choice(domains)}"
            text = f"line {i}: contact={_obfuscate_key(rng, addr, 0.20, 0.18)} for sandbox case"
        elif kind == "phone":
            phone = f"555-{rng.randint(100,999)}-{rng.randint(1000,9999)}"
            text = f"line {i}: callback {_obfuscate_key(rng, phone, 0.15, 0.15)} before noon"
        else:
            acct = f"ACCT-{rng.randint(1000,9999)}-{rng.randint(100,999)}"
            text = f"line {i}: token {_obfuscate_key(rng, acct, 0.20, 0.18)} was pasted"
        norm = _norm_key(text, keep_dash=True)
        # The production redactor catches normalized email/phone/account patterns.
        is_leak = bool(
            re.search(r"[A-Z]+\d{2}@[A-Z.]+", norm)
            or re.search(r"555-\d{3}-\d{4}", norm)
            or re.search(r"ACCT-\d{4}-\d{3}", norm)
        )
        if is_leak:
            leaking.append(i)
        lines.append(text)
    ans = ",".join(map(str, leaking)) if leaking else "none"
    prompt = (
        "Compliance audit: all data is synthetic. A redactor normalizes each line with NFKC, removes Unicode "
        "format controls and spaces, maps common Cyrillic/Greek/fullwidth look-alikes to ASCII, uppercases, "
        "and treats all hyphen-like characters as '-'. After that normalization, it flags fake emails like "
        "NAME12@DOMAIN, fake phones like 555-123-4567, and fake account IDs like ACCT-1234-567.\n\n"
        "Which original line numbers would be flagged? Output only comma-separated line numbers in ascending "
        "order, or 'none'.\n\n" + "\n".join(lines)
    )
    return dict(task="redaction_leak_audit", kind="exact", answer=ans, prompt=prompt,
                meta={"lines": len(lines), "leaks": len(leaking)})


# ---------------------------------------------------------------------------
# 5. Contract redline merge


def legal_redline_merge(rng: random.Random):
    """Apply long redline log to contract clauses."""
    clauses = [
        "Vendor shall provide weekly status reports before Friday close.",
        "Customer may request a refund after documented service failure.",
        "Invoices are due thirty days after receipt unless disputed in writing.",
        "Confidential records must remain encrypted during transfer and storage.",
        "Support access expires when the pilot project ends or is terminated.",
        "Each shipment requires approval from operations and finance.",
    ]
    vocab = ["shall", "must", "may", "will", "before", "after", "unless", "during", "with", "without",
             "written", "verified", "quarterly", "monthly", "audit", "notice", "secure", "temporary"]
    events = []
    n_ops = rng.randint(70, 92)
    for _ in range(n_ops):
        ci = rng.randrange(len(clauses))
        words = clauses[ci].split(" ")
        op = rng.choices(["replace_word", "insert_after", "delete_word", "append_phrase", "swap"],
                         weights=[30, 22, 16, 16, 16])[0]
        if op == "replace_word" and words:
            pos = rng.randrange(len(words))
            old = words[pos]
            new = rng.choice(vocab)
            words[pos] = new
            clauses[ci] = " ".join(words)
            events.append(f"Clause {ci+1}: replace word {pos+1} ({_q(old)}) with {_q(new)}.")
        elif op == "insert_after" and words:
            pos = rng.randrange(len(words))
            new = rng.choice(vocab)
            words.insert(pos + 1, new)
            clauses[ci] = " ".join(words)
            events.append(f"Clause {ci+1}: insert {_q(new)} after word {pos+1}.")
        elif op == "delete_word" and len(words) > 3:
            pos = rng.randrange(len(words))
            old = words.pop(pos)
            clauses[ci] = " ".join(words)
            events.append(f"Clause {ci+1}: delete word {pos+1} ({_q(old)}).")
        elif op == "append_phrase":
            phrase = rng.choice(["subject to audit", "without delay", "after written notice", "during business hours"])
            clauses[ci] = clauses[ci].rstrip(".") + " " + phrase + "."
            events.append(f"Clause {ci+1}: append phrase {_q(phrase)} before the final period.")
        elif op == "swap" and len(words) > 2:
            a, b = sorted(rng.sample(range(len(words)), 2))
            words[a], words[b] = words[b], words[a]
            clauses[ci] = " ".join(words)
            events.append(f"Clause {ci+1}: swap words {a+1} and {b+1}.")
    ans = json.dumps(clauses, ensure_ascii=False, separators=(",", ":"))
    initial_clauses = [
        "Vendor shall provide weekly status reports before Friday close.",
        "Customer may request a refund after documented service failure.",
        "Invoices are due thirty days after receipt unless disputed in writing.",
        "Confidential records must remain encrypted during transfer and storage.",
        "Support access expires when the pilot project ends or is terminated.",
        "Each shipment requires approval from operations and finance.",
    ]
    prompt = (
        "A legal operations assistant must merge a redline log. Treat words as space-separated tokens. "
        "Punctuation attached to a word stays part of that word unless explicitly changed. Apply edits in order. "
        "Output only the six final clauses as a one-line minified JSON array.\n\nInitial clauses:\n"
        + "\n".join(f"{i+1}. {c}" for i, c in enumerate(initial_clauses))
        + "\n\nRedline events:\n" + "\n".join(f"{i+1}. {e}" for i, e in enumerate(events))
    )
    return dict(task="legal_redline_merge", kind="exact", answer=ans, prompt=prompt,
                meta={"ops": n_ops, "clauses": len(clauses)})


# ---------------------------------------------------------------------------
# 6. Warehouse scan / inventory state


def warehouse_scan_inventory(rng: random.Random):
    """Replay SKU scans with normalization-sensitive identifiers."""
    skus = [f"SKU-{rng.choice(['A','B','C','X','M','P'])}{rng.randint(100,999)}" for _ in range(10)]
    inv = {s: rng.randint(2, 15) for s in skus}
    init = dict(inv)
    events = []
    for _ in range(rng.randint(95, 125)):
        sku = rng.choice(skus)
        raw = _obfuscate_key(rng, sku, 0.22, 0.12)
        op = rng.choices(["receive", "ship", "adjust", "return"], weights=[34, 34, 12, 20])[0]
        if op == "receive":
            q = rng.randint(1, 8); inv[sku] += q
            events.append(f"RECEIVE {q} units of {raw}.")
        elif op == "ship":
            q = rng.randint(1, 7); inv[sku] -= q
            events.append(f"SHIP {q} units of {raw}.")
        elif op == "return":
            q = rng.randint(1, 5); inv[sku] += q
            events.append(f"RETURN {q} units of {raw}.")
        else:
            q = rng.randint(-5, 5); inv[sku] += q
            events.append(f"ADJUST {raw} by {q:+d} units.")
    ans = ";".join(f"{k}={inv[k]}" for k in sorted(inv))
    prompt = (
        "Warehouse reconciliation. SKU strings may contain zero-width characters, fullwidth digits, "
        "hyphen variants, and Cyrillic/Greek look-alikes. Normalize SKUs with NFKC, remove Unicode format "
        "controls/spaces, map look-alikes to ASCII, uppercase, and treat hyphen variants as '-'. Replay all "
        "events in order from the initial counts. Output only final counts for all SKUs sorted by normalized "
        "SKU, as SKU=count joined by semicolons.\n\nInitial counts:\n"
        + ";".join(f"{k}={v}" for k, v in sorted(init.items()))
        + "\n\nScan log:\n" + "\n".join(f"{i+1}. {e}" for i, e in enumerate(events))
    )
    return dict(task="warehouse_scan_inventory", kind="exact", answer=ans, prompt=prompt,
                meta={"events": len(events), "skus": len(skus)})


# ---------------------------------------------------------------------------
# 7. Bioinformatics / CIGAR-like sequence reconstruction


def clinical_cigar_reconstruct(rng: random.Random):
    """Reconstruct a sample DNA sequence from a CIGAR-like lab edit log."""
    alphabet = "ACGT"
    ref = "".join(rng.choice(alphabet) for _ in range(rng.randint(120, 160)))
    pos = 0
    out = []
    ops = []
    while pos < len(ref):
        op = rng.choices(["M", "D", "I", "X"], weights=[55, 14, 18, 13])[0]
        if op == "M":
            k = rng.randint(1, min(8, len(ref) - pos))
            out.extend(ref[pos:pos+k]); pos += k
            ops.append(f"M{k}")
        elif op == "D":
            k = rng.randint(1, min(5, len(ref) - pos))
            pos += k
            ops.append(f"D{k}")
        elif op == "I":
            ins = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 5)))
            out.extend(ins)
            ops.append(f"I{ins}")
        else:
            k = rng.randint(1, min(4, len(ref) - pos))
            repl = []
            for ch in ref[pos:pos+k]:
                choices = [b for b in alphabet if b != ch]
                repl.append(rng.choice(choices))
            out.extend(repl); pos += k
            ops.append(f"X{k}:{''.join(repl)}")
    # Add extra insertions after reference consumed.
    for _ in range(rng.randint(4, 9)):
        ins = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 5)))
        out.extend(ins); ops.append(f"I{ins}")
    ans = "".join(out)
    prompt = (
        "Clinical lab sequence reconstruction. Starting at reference position 1, process the operations left "
        "to right. Mk copies the next k bases from the reference to the sample and advances k reference bases. "
        "Dk skips/deletes the next k reference bases. ISEQ inserts SEQ into the sample without advancing the "
        "reference. Xk:SEQ replaces the next k reference bases with SEQ and advances k reference bases. Output "
        "only the final sample sequence.\n\nReference:\n" + ref + "\n\nOperations:\n" + " ".join(ops)
    )
    return dict(task="clinical_cigar_reconstruct", kind="exact", answer=ans, prompt=prompt,
                meta={"ref_len": len(ref), "ops": len(ops), "answer_len": len(ans)})


# ---------------------------------------------------------------------------
# 8. Localization / Unicode-aware string table merge


def localization_string_merge(rng: random.Random):
    """Merge translation string updates with confusable keys and escaped text."""
    keys = [f"APP.{rng.choice(['MENU','PAY','AUTH','SHIP','CARE'])}.{rng.choice(WORDS).upper()}.{i}"
            for i in range(1, 10)]
    table = {k: rng.choice([
        "Save", "Cancel", "Review order", "Ship now", "Payment pending", "Access denied",
        "Call support", "Refund issued", "Upload file", "Close window",
    ]) for k in keys}
    init = dict(table)
    events = []
    snippets = ["Save", "Cancel", "Review", "Upload", "Retry", "Hold", "Approved", "Denied", "Pending", "Close"]
    for _ in range(rng.randint(78, 104)):
        k = rng.choice(keys)
        rawk = _obfuscate_key(rng, k, 0.18, 0.10)
        op = rng.choices(["set", "append", "prepend", "replace", "delete_chars"], weights=[22, 20, 18, 24, 16])[0]
        if op == "set":
            val = rng.choice(snippets) + rng.choice(["", "…", "!", " now", " later"])
            table[k] = val
            events.append(f"SET {rawk} = {_q(val)}.")
        elif op == "append":
            val = rng.choice(["!", "…", " now", " later", " (beta)", " / help"])
            table[k] += val
            events.append(f"APPEND {_q(val)} to {rawk}.")
        elif op == "prepend":
            val = rng.choice(["New: ", "Beta: ", "Action: ", "Note: "])
            table[k] = val + table[k]
            events.append(f"PREPEND {_q(val)} to {rawk}.")
        elif op == "replace":
            if table[k]:
                old = rng.choice(table[k].split(" ")) if " " in table[k] else table[k][:rng.randint(1, max(1, min(4, len(table[k]))))]
            else:
                old = ""
            new = rng.choice(snippets)
            table[k] = table[k].replace(old, new, 1) if old else new
            events.append(f"REPLACE first occurrence of {_q(old)} with {_q(new)} in {rawk}.")
        else:
            if table[k]:
                start = rng.randint(0, max(0, len(table[k]) - 1))
                n = rng.randint(1, min(3, len(table[k]) - start))
                table[k] = table[k][:start] + table[k][start+n:]
                events.append(f"DELETE {n} character(s) starting at 0-indexed character {start} in {rawk}.")
            else:
                events.append(f"DELETE 0 character(s) starting at 0-indexed character 0 in {rawk}.")
    ans = json.dumps({k: table[k] for k in sorted(table)}, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    prompt = (
        "Localization string-table merge. Keys may contain zero-width characters, fullwidth digits, hyphen/dot "
        "look-alikes, and Cyrillic/Greek look-alike letters. For matching keys, normalize with NFKC, remove "
        "Unicode format controls/spaces, map look-alikes to ASCII, uppercase, and keep punctuation such as '.' "
        "as punctuation. String values are edited as Unicode code-point strings. Apply events in order. Output "
        "only the final table as one-line minified JSON sorted by key.\n\nInitial table:\n"
        + json.dumps(init, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n\nEvents:\n" + "\n".join(f"{i+1}. {e}" for i, e in enumerate(events))
    )
    return dict(task="localization_string_merge", kind="exact", answer=ans, prompt=prompt,
                meta={"events": len(events), "keys": len(keys)})


TASKS = {f.__name__: f for f in [
    crm_typing_reconstruct,
    json_patch_ticket_board,
    invoice_csv_unicode_etl,
    redaction_leak_audit,
    legal_redline_merge,
    warehouse_scan_inventory,
    clinical_cigar_reconstruct,
    localization_string_merge,
]}
