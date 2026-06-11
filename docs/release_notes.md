# Release notes

## v0.1.0 - initial public release

First public release of SUPERCUTE: a deterministic, exactly graded benchmark
suite that measures how well LLMs perceive exact character-level details
(Unicode normalization, homoglyphs, zero-width characters, grapheme boundaries)
and how reliably they track and update precise state in long real-world
workflows, like replaying dozens of CRM record edits or applying sequential
legal redlines to a contract.

### Benchmark

- Three scored tiers: character perception probes (`tok`), real-life workflows
  with character-exact details (`realtok`), and a controlled shortcut-free
  long-horizon execution stress test (`iterated_lut`).
- PublicLift release tier: eight templates that turn public-dataset records
  (FinQA/TAT-QA, TabFact/WikiTableQuestions, CUAD/ContractNLI, CORD/SROIE/DocVQA,
  LogHub, CRUXEval/LiveCodeBench, SWE-bench, SpreadsheetBench) into fresh
  apply-this-changelog tasks, plus adapter contracts for swapping synthetic
  seeds for licensed public records. PublicLift is released infrastructure,
  not a scored result.
- Every task computes exact ground truth in Python; no model-in-the-loop labeling.
- Free, offline self-checks gate the suite before any paid sweep
  (`selfcheck`, `sweep --module <name> --self`).

### Evidence and analysis

- Six-model OpenRouter evaluation harness (`full_eval`) with optional `--raw-out`
  capture for manual failure taxonomy via `error_audit`.
- `analyze_eval` reports Wilson 95% intervals, the LUT break curve, explicit
  dropped provider/transport-error denominators, and a descriptive
  compounding-error fit P(correct | K) = r^K.
- Raw run preserved in `data/eval_results.jsonl` (1536 raw / 1523 scored
  rows) so denominator choices are auditable.

### Paper

- `paper/main.tex` ("SUPERCUTE: Measuring Exact Character Perception and
  Long-Workflow State Tracking in Language Models") by Stanislav Kirdey,
  Clark Labs Inc., with compiled `main.pdf` and the break-curve figure. The
  central claim is deliberately scoped: frontier models can see tricky
  characters, but carrying exact state through long workflows fails in
  high-variance, model-specific ways rather than at a universal wall.

### Packaging

- Standard Python package: `pyproject.toml`, `Makefile`, `CITATION.cff`,
  `MANIFEST.in`, `py.typed`, MIT `LICENSE`, contribution/security/third-party-data
  docs, GitHub Actions CI, and a unit-test suite. No required runtime
  dependencies beyond the Python standard library.
