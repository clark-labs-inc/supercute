# SUPERCUTE-RealTok Upgrade

This patch adds `supercute/scenarios_realtok.py`, a realistic tokenizer-friction tier for SUPERCUTE.

## Why this tier exists

The prior tokenizer probes show that GPT-5.5 can usually perceive Unicode, bytes, code points, invisibles, homoglyphs, and static character properties when the task is short and explicit. The reliable failure mechanism is not isolated perception; it is **exact character state under long, realistic workflows**.

RealTok therefore embeds tokenizer-sensitive details inside work-like tasks:

- CRM/support typing reconstruction
- API ticket-board patch logs
- messy CSV invoice cleanup
- compliance redaction audit over obfuscated synthetic PII
- legal redline merge
- warehouse SKU scan reconciliation
- clinical CIGAR-like sequence reconstruction
- localization string-table merge

All data is synthetic. No live prompt-injection payloads, malware, or real PII are included.

## Run

```bash
PYTHONPATH=. python -m supercute.sweep --module realtok --self
OPENROUTER_API_KEY=... PYTHONPATH=. python -m supercute.sweep --module realtok \
  --model openai/gpt-5.5 --per-task 4 --timeout 240 --workers 4
```

The module is also merged into `supercute.scenarios.TASKS`, so normal `run.py`/`benchmark.py` can include these tasks by name.

## Calibration guidance

Start with `--per-task 4`. If GPT-5.5 is above 20% on a task, increase that generator’s event count until it is near the 0–10% region. Avoid yes/no or low-entropy answers. Prefer exact JSON/string outputs or line-number sets.

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
