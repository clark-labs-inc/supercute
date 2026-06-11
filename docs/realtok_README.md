# RealTok: character-exact details inside real jobs

`supercute/scenarios_realtok.py` is the tier that puts tricky characters where they actually show up: inside long, real-life workflows.

## Why this tier exists

The perception probes show that GPT-5.5 can usually see Unicode, bytes, code points, invisible characters, and homoglyphs when a task is short and explicit. The reliable failure mode is different: keeping exact character state correct through a long, realistic job, where each step depends on the ones before.

RealTok therefore puts character-sensitive details inside work-like tasks:

- replaying a support agent's cursor edits to reconstruct a CRM field
- applying a stream of JSON patches to a ticket board
- cleaning a messy, Unicode-noisy invoice CSV
- auditing redactions over obfuscated synthetic PII
- applying sequential legal redlines to a contract
- reconciling warehouse SKU barcode scans
- reconstructing a clinical CIGAR-like sequence
- merging localization string tables

All data is synthetic. No live prompt-injection payloads, malware, or real PII are included.

## Run

```bash
PYTHONPATH=. python -m supercute.sweep --module realtok --self
OPENROUTER_API_KEY=... PYTHONPATH=. python -m supercute.sweep --module realtok \
  --model openai/gpt-5.5 --per-task 4 --timeout 240 --workers 4
```

The module is also merged into `supercute.scenarios.TASKS`, so normal `run.py`/`benchmark.py` can include these tasks by name.

## Calibration guidance

Start with `--per-task 4`. If GPT-5.5 is above 20% on a task, increase that generator's event count until it lands near the 0-10% region. Avoid yes/no answers or anything with few ways to be wrong. Prefer exact JSON/string outputs or line-number sets.

Recommended hard track:

```bash
python -m supercute.sweep --module realtok --model openai/gpt-5.5 --per-task 8 --timeout 300 --workers 3
```

Recommended mixed benchmark:

```bash
python -m supercute.benchmark \
  --models openai/gpt-5.5 anthropic/claude-opus-4.8 qwen/qwen3.5-flash-02-23 \
  --tasks crm_typing_reconstruct json_patch_ticket_board invoice_csv_unicode_etl \
          redaction_leak_audit legal_redline_merge warehouse_scan_inventory \
          clinical_cigar_reconstruct localization_string_merge iterated_lut \
  --per-task 2 --timeout 300 --workers 4
```
