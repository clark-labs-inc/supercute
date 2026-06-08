# SUPERCUTE PublicLift: public dataset hardening plan

This patch adds `supercute/scenarios_publiclift.py`, a set of exact-gradeable long-horizon workflows designed to be instantiated from public datasets without redistributing third-party rows.

The core idea is a **procedural lift**:

```text
public record -> realistic mutable state -> seeded operation log -> deterministic oracle -> exact answer
```

Do not ask the original public benchmark question. Frontier models may have seen it, and the labels are usually too short. Instead, use the public record as realistic substrate, then generate fresh changelogs that require exact state maintenance.

## New runnable tasks

| Task | Public dataset family it targets | What it tests |
|---|---|---|
| `finqa_restatement_rollforward` | FinQA / TAT-QA / MultiHiertt | Financial-table restatement, reclassification, exact cents totals |
| `tabfact_table_changelog` | TabFact / WikiTableQuestions / SpreadsheetBench | Semi-structured table mutation and exact row snapshot |
| `cuad_amendment_merge` | CUAD / ContractNLI / LEDGAR | Contract redline/amendment replay over clauses |
| `cord_receipt_reconciliation` | CORD / SROIE / DocVQA | OCR receipt correction, voids, category totals |
| `loghub_incident_replay` | LogHub / AIOps logs | Incident state replay over open/ack/escalate/resolve events |
| `cruxeval_stack_trace` | CRUXEval / LiveCodeBench / CodeNet | Long program-execution trace with ~1,500+ atomic operations |
| `swebench_patch_manifest` | SWE-bench / SWE-bench Verified | Patch/rebase line-edit manifest replay |
| `spreadsheet_cell_reconciliation` | SpreadsheetBench | Spreadsheet-like cell updates, copy/fill/swap, derived cells |

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

Use the existing SUPERCUTE result as the anchor: static tokenizer/perception tasks were almost solved by GPT-5.5, while `iterated_lut` around 1,500-1,900 interdependent exact operations broke it consistently. PublicLift therefore raises hardness by combining realistic records with long mutation horizons and exact high-entropy outputs.

The most GPT-5.5-hostile items should be:

1. `cruxeval_stack_trace` — ~1,500+ atomic state operations, no semantic shortcut.
2. `finqa_restatement_rollforward` — often ~1,400+ atomic accounting operations plus tokenizer-friction IDs.
3. `tabfact_table_changelog` — hundreds of row/cell updates over a broad table state.
4. `swebench_patch_manifest` — current-line-number edits and path normalization.
5. `cuad_amendment_merge` — exact text mutation over legal clauses.

## Real adapter rule

When adapting a public dataset, do **not** bundle raw third-party data in the benchmark zip unless the license clearly permits redistribution. Prefer a loader script that downloads the dataset from the official source, transforms records locally, and writes generated SUPERCUTE items with attribution metadata.

`supercute/publicdata_adapters.py` contains a recipe registry and adapter contract.
