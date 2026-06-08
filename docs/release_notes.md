# Release notes

## v0.1.0 - initial public release

First public release of SUPERCUTE: a deterministic, exactly graded benchmark
suite for tokenizer friction and long-horizon exact execution in language models.

### Benchmark

- Three scored tiers: tokenizer perception probes (`tok`), realistic
  tokenizer-sensitive workflows (`realtok`), and a controlled shortcut-free
  long-horizon execution stress test (`iterated_lut`).
- PublicLift release tier: eight public-dataset-derived hardening templates
  (FinQA/TAT-QA, TabFact/WikiTableQuestions, CUAD/ContractNLI, CORD/SROIE/DocVQA,
  LogHub, CRUXEval/LiveCodeBench, SWE-bench, SpreadsheetBench), plus adapter
  contracts for swapping synthetic seeds for licensed public records. PublicLift
  is released infrastructure, not a scored result.
- Every task computes exact ground truth in Python; no model-in-the-loop labeling.
- Free, offline self-checks gate the suite before any paid sweep
  (`selfcheck`, `sweep --module <name> --self`).

### Evidence and analysis

- Six-model OpenRouter evaluation harness (`full_eval`) with optional `--raw-out`
  capture for manual failure taxonomy via `error_audit`.
- `analyze_eval` reports Wilson 95% intervals, the LUT break curve, explicit
  dropped provider/transport-error denominators, and a descriptive
  compounding-error fit P(correct | K) = r^K.
- Supplied raw run preserved in `data/eval_results.jsonl` (1536 raw / 1523 scored
  rows) so denominator choices are auditable.

### Paper

- `paper/main.tex` ("From Tokenizer Friction to Model-Specific Long-Horizon
  Breaks") with compiled `main.pdf` and the break-curve figure. The central claim
  is deliberately scoped: isolated tokenizer perception is largely solved at the
  frontier, while exact execution over long mutable state produces high-variance,
  model-specific reliability failures rather than a universal wall.

### Packaging

- Standard Python package: `pyproject.toml`, `Makefile`, `CITATION.cff`,
  `MANIFEST.in`, `py.typed`, MIT `LICENSE`, contribution/security/third-party-data
  docs, GitHub Actions CI, and a unit-test suite. No required runtime
  dependencies beyond the Python standard library.
