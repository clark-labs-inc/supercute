# Code review and cleanup notes

This release turns the exploratory SUPERCUTE workspace into a reusable benchmark package and incorporates the paper-review feedback that the original empirical framing was too strong.

## Main finding reflected in code

The original tokenizer-first thesis has been updated. Static character and tokenizer perception tasks remain in the benchmark because they stratify models, but the release treats long-horizon exact execution as a model-specific reliability stressor, not as a universal frontier wall. RealTok and PublicLift are included to make exact-state stressors look like real work.

## Cleanup performed

- Removed repository-local artifacts such as `.git`, `.DS_Store`, `__MACOSX`, and bundled scratch zips from the release tree.
- Added package metadata in `pyproject.toml` with console-script entry points.
- Kept runtime dependencies at zero for deterministic generation, grading, and model sweeps.
- Added optional extras for plotting, dataset loading, and development.
- Added MIT license, citation metadata, third-party data guidance, contribution notes, security notes, and CI.
- Promoted the paper to top-level `paper/` and removed stale draft locations.
- Integrated `scenarios_realtok.py` and `scenarios_publiclift.py` into the central task registry.
- Added `publicdata_adapters.py` as the intended place to connect official public datasets without redistributing third-party rows.
- Updated domain tagging so generated benchmark files categorize PublicLift tasks correctly.
- Replaced the API client with a small OpenAI-compatible stdlib client while preserving existing benchmark calls.
- Added tests for grading behavior, generator/oracle consistency, and registry coverage.

## Review-feedback changes in this revision

- Softened the paper's claims from "frontier-wide wall" to "model-specific, high-variance long-horizon failures."
- Explicitly states that PublicLift is unscored infrastructure/future work in the supplied paper run.
- Explains variable denominators: provider/transport errors are preserved in raw JSONL and dropped from scored denominators.
- Adds a descriptive compounding-error fit, `P(correct | K) = r^K`, to `supercute.analyze_eval` and `data/eval_summary.json`.
- Notes the reasoning-token/completion-token confound and the GPT-5.5 token plateau after K=45.
- Calls out non-monotonic break curves and n=8/cell as a pilot limitation.
- Adds a raw-output capture option to `full_eval.py` via `--raw-out`.
- Adds `supercute.error_audit` for manual failure review packets in future raw-output runs.
- Fixes `supercute.make_figure` so it writes to `paper/figures/breakcurve.png`, matching the paper.

## Validation results

The following checks were run on the revised release tree:

```text
python -m py_compile supercute/*.py                  PASS
python -m pytest -q                                 PASS
python -m supercute.sweep --module tok --self        PASS
python -m supercute.sweep --module realtok --self    PASS
python -m supercute.sweep --module publiclift --self PASS
python -m supercute.sweep --module hard --self       PASS
python -m supercute.selfcheck                        PASS
python -m supercute.analyze_eval                     PASS
python -m supercute.make_figure                      PASS
latexmk -pdf paper/main.tex                          PASS
PDF render verification                              PASS
```

No paid model calls were rerun during packaging. The supplied raw model metadata are preserved in `data/eval_results.jsonl`, and the summarized Wilson intervals plus compounding fit are in `data/eval_summary.json`.

## Known release limitations

- PublicLift is self-checked but not yet included in the supplied paid model results.
- Reasoning budget is provider/model dependent; benchmark reports should include output-token or reasoning-token statistics.
- Exact-match grading is intentionally strict. It measures operational reliability, not partial credit.
- The supplied results do not include raw model responses, so the current paper does not include a complete manual failure taxonomy.
- Some older data files are retained for reproducibility even if they are not part of the main release narrative.
