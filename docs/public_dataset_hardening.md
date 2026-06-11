# SUPERCUTE PublicLift: turning public datasets into exact-state work

`supercute/scenarios_publiclift.py` is a set of exactly gradeable long-horizon workflows designed to be instantiated from public datasets without redistributing third-party rows.

The core idea is a **procedural lift**:

```text
public record -> realistic mutable state -> seeded operation log -> deterministic oracle -> exact answer
```

Do not ask the original public benchmark question. Frontier models may have memorized it, and the labels are usually too short to test careful work. Instead, use the public record as realistic raw material — a financial table, a contract, a receipt, a log — then generate a fresh changelog of edits against it and ask for the exact final state.

## New runnable tasks

| Task | Public dataset family it targets | What the model has to do |
|---|---|---|
| `finqa_restatement_rollforward` | FinQA / TAT-QA / MultiHiertt | apply restatements and reclassifications, report final totals to the cent |
| `tabfact_table_changelog` | TabFact / WikiTableQuestions / SpreadsheetBench | apply a table changelog, report the exact requested rows |
| `cuad_amendment_merge` | CUAD / ContractNLI / LEDGAR | apply sequential amendments to a contract, report the final clause text |
| `cord_receipt_reconciliation` | CORD / SROIE / DocVQA | fix OCR errors and voids on receipts, report category totals |
| `loghub_incident_replay` | LogHub / AIOps logs | replay open/ack/escalate/resolve events, report which incidents are still open |
| `cruxeval_stack_trace` | CRUXEval / LiveCodeBench / CodeNet | follow a program trace with ~1,500+ atomic operations, report the final stack |
| `swebench_patch_manifest` | SWE-bench / SWE-bench Verified | replay patches as line numbers shift, report what is on each line now |
| `spreadsheet_cell_reconciliation` | SpreadsheetBench | apply cell updates, copy/fill/swap operations, report final cell values |

## How to run the free oracle check

```bash
PYTHONPATH=. python -m supercute.sweep --module publiclift --self
```

Expected local result in this build:

```text
self-check: 8 tasks x40 -> ALL CONSISTENT
```

## How to run against GPT-5.5

```bash
OPENROUTER_API_KEY=... PYTHONPATH=. python -m supercute.sweep \
  --module publiclift \
  --model openai/gpt-5.5 \
  --per-task 3 \
  --workers 3 \
  --timeout 360
```

## Calibration notes

Use the existing SUPERCUTE result as the anchor: GPT-5.5 nearly aced the character-perception probes, while `iterated_lut` around 1,500-1,900 dependent exact operations broke it consistently. PublicLift therefore raises difficulty by combining realistic records with long edit histories and exact answers that have many ways to be wrong.

The most GPT-5.5-hostile items should be:

1. `cruxeval_stack_trace` — ~1,500+ atomic state operations, no semantic shortcut.
2. `finqa_restatement_rollforward` — often ~1,400+ atomic accounting operations plus look-alike identifiers.
3. `tabfact_table_changelog` — hundreds of row/cell updates over a broad table state.
4. `swebench_patch_manifest` — line numbers that shift after every edit, plus path normalization.
5. `cuad_amendment_merge` — exact text mutation over legal clauses.

## Real adapter rule

When adapting a public dataset, do **not** bundle raw third-party data in the benchmark zip unless the license clearly permits redistribution. Prefer a loader script that downloads the dataset from the official source, transforms records locally, and writes generated SUPERCUTE items with attribution metadata.

`supercute/publicdata_adapters.py` contains a recipe registry and adapter contract.
