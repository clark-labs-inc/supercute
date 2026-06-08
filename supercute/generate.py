"""Finalize the SUPERCUTE benchmark: dedup harvested hard scenarios (data/hard.jsonl)
into the canonical, domain-tagged data/benchmark.jsonl."""
from __future__ import annotations

import collections
import json
import os

HERE = os.path.dirname(__file__)
HARD = os.path.join(HERE, "..", "data", "hard.jsonl")
OUT = os.path.join(HERE, "..", "data", "benchmark.jsonl")

DOMAIN = {
    "luhn_localize": "finance", "luhn_validate": "finance", "iban_validate": "finance",
    "transposition_locate": "finance", "count_digit_in_id": "finance", "diff_locate": "finance",
    "decimal_magnitude": "finance",
    "npi_validate": "healthcare", "dosage_safety": "healthcare", "lasa_same": "healthcare",
    "nth_char_id": "healthcare",
    "dna_base_count": "biology", "dna_point_mutation": "biology", "dna_revcomp": "biology",
    "codon_at": "biology", "motif_find": "biology", "protein_residue_at": "biology",
    "hamming_distance": "biology",
    "smiles_ring_balance": "chemistry", "cas_validate": "chemistry",
    "isotope_neutrons": "nuclear", "sci_notation_compare": "nuclear",
    "vin_validate": "engineering", "isbn13_validate": "engineering", "hash_match": "engineering",
    "hash_diff_locate": "engineering", "hex_byte_at": "engineering",
    "longest_char_run": "bytes", "char_from_end": "bytes", "count_substring": "bytes",
    "field_extract": "bytes", "count_char_class": "bytes", "hamming_distance": "biology",
    "grapheme_count": "unicode", "codepoint_count": "unicode", "utf8_byte_length": "unicode",
    "nfc_equivalent": "unicode", "base64_decode_char": "unicode", "hex_decode_char": "unicode",
    "bracket_balance": "code", "escape_count": "code", "base_convert": "code",
    "redact_span": "code", "insert_at": "code", "extract_reverse_compare": "code",
    "levenshtein": "linguistics", "anagram": "linguistics",
    # construction / composition / ciphers
    "rot_n_decode": "construction", "vigenere_decode": "construction",
    "atbash_decode": "construction", "uppercase_vowels": "construction",
    "delete_every_kth": "construction", "reverse_each_word": "construction",
    "mask_email": "construction", "extract_reverse_upper": "construction",
    # invisible / zero-width unicode
    "total_codepoints_invisible": "unicode", "invisible_count": "unicode",
    "strip_invisible": "unicode", "bidi_detect": "unicode", "combining_count": "unicode",
    # networking + time/date
    "ipv6_compress": "networking", "days_between": "datetime", "iso_add_days": "datetime",
    # real-document verification (FinQA: numeric answer vs real report; TabFact: claim vs table)
    "finqa_verify": "verification", "tabfact_verify": "verification",
    # adversarial tier (built to push frontier models to the random-guess floor)
    "char_at_long": "adversarial", "pointer_chase": "adversarial",
    "iterated_lut": "adversarial", "codepoint_count_deep": "adversarial",
    "column_read": "adversarial", "deinterleave": "adversarial", "freq_rank": "adversarial",
    # RealTok: tokenizer-friction embedded in realistic long-state workflows
    "crm_typing_reconstruct": "realtok", "json_patch_ticket_board": "realtok",
    "invoice_csv_unicode_etl": "realtok", "redaction_leak_audit": "realtok",
    "legal_redline_merge": "realtok", "warehouse_scan_inventory": "realtok",
    "clinical_cigar_reconstruct": "realtok", "localization_string_merge": "realtok",

    # PublicLift: public-dataset-inspired exact-state replay templates
    "finqa_restatement_rollforward": "publiclift",
    "tabfact_table_changelog": "publiclift",
    "cuad_amendment_merge": "publiclift",
    "cord_receipt_reconciliation": "publiclift",
    "loghub_incident_replay": "publiclift",
    "cruxeval_stack_trace": "publiclift",
    "swebench_patch_manifest": "publiclift",
    "spreadsheet_cell_reconciliation": "publiclift",
}


def main():
    seen = {}
    for line in open(HARD, encoding="utf-8"):
        if line.strip():
            h = json.loads(line)
            seen[h["id"]] = h
    items = sorted(seen.values(), key=lambda h: (h["task"], h["id"]))
    with open(OUT, "w", encoding="utf-8") as f:
        for h in items:
            f.write(json.dumps({
                "id": h["id"], "task": h["task"], "domain": DOMAIN.get(h["task"], "misc"),
                "prompt": h["prompt"], "answer": h["answer"], "kind": h["kind"],
                "meta": h.get("meta", {}),
            }, ensure_ascii=False) + "\n")

    by_task = collections.Counter(h["task"] for h in items)
    by_dom = collections.Counter(DOMAIN.get(h["task"], "misc") for h in items)
    print(f"benchmark: {len(items)} scenarios -> {OUT}\n")
    print("by domain:", dict(by_dom))
    print("\nby task:")
    for t, c in by_task.most_common():
        print(f"  {t:24s} {c}")


if __name__ == "__main__":
    main()
