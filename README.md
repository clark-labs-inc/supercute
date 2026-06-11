# SUPERCUTE

SUPERCUTE measures how well LLMs perceive exact character-level details such as Unicode normalization, homoglyphs, zero-width characters, and grapheme boundaries, plus how reliably they track and update precise state in long real-world workflows like replaying dozens of CRM record edits or applying sequential legal redlines to a contract.

Every task is generated and graded by plain Python code, so the ground truth is exact and no model ever labels another model's answer.

The headline from our June 2026 runs is simple: looking at weird characters does not break a frontier model anymore, but doing long, careful work with them still does — for some models much more than others.

## Main result

Across the June 2026 OpenRouter runs:

| Tier | What it asks the model to do | GPT-5.5 result | Important caveat |
|---|---|---:|---|
| `tok` | spot homoglyphs, zero-width characters, normalization differences, count graphemes and bytes | 0.980 | does not break GPT-5.5 |
| `realtok` | redo real jobs exactly: replay CRM edits, clean a messy invoice CSV, merge contract redlines, reconcile warehouse scans | 0.781 | denominators exclude provider/transport errors |
| `iterated_lut` break curve | apply a random lookup table over and over — 330 to 1650 dependent updates with no shortcut | 0.375 overall; 0/8 at 1320 updates | Opus 4.8 scores 0.825 overall and 8/8 at 1320 updates |

The careful headline is:

> GPT-5.5 can see the characters just fine. What it cannot always do is carry exact state through hundreds of small dependent changes — and that failure is model-specific, not a universal frontier wall. Opus 4.8 sails through the same long task that drops GPT-5.5 to zero.

These results come from small samples (n=8 per cell), one provider route, and uneven reasoning-token budgets, so treat the long-horizon curves as a pilot, not a leaderboard.

## What is included

SUPERCUTE ships four benchmark layers:

1. **Classic exact-character tasks**: finance identifiers, checksums, Unicode, biology strings, code strings, networking/date tasks.
2. **Character perception probes (`scenarios_tok.py`)**: can the model tell `а` (Cyrillic) from `a` (Latin), notice an invisible zero-width space inside a customer ID, count graphemes in emoji-laden text, or report UTF-8 byte lengths correctly?
3. **RealTok (`scenarios_realtok.py`)**: real-life jobs where one wrong character ruins the result — replaying a support agent's cursor edits to a CRM field, cleaning a Unicode-noisy invoice CSV, merging legal redlines into a contract, reconciling warehouse barcode scans, merging localization string tables, auditing redactions, reconstructing a clinical sequence, and replaying ticket-board updates.
4. **PublicLift (`scenarios_publiclift.py`)**: templates that turn public-dataset records — financial reports (FinQA/TAT-QA), fact tables (TabFact/WikiTableQuestions), contracts (CUAD/ContractNLI), receipts (CORD/SROIE/DocVQA), system logs (LogHub), code traces (CRUXEval/LiveCodeBench/CodeNet), software patches (SWE-bench), and spreadsheets (SpreadsheetBench) — into fresh "apply this changelog and tell me the exact final state" tasks. Synthetic seeded records by default; adapter contracts let you plug in the official datasets under their own licenses. PublicLift is released infrastructure, not a scored result in the paper run.

Every task returns exact ground truth computed in Python. There is no model-in-the-loop labeling.

## Install

```bash
python -m pip install -e .
```

Optional analysis/dev tools:

```bash
python -m pip install -e '.[dev]'
```

## Free self-checks

Run these before spending any API money:

```bash
python -m supercute.selfcheck
python -m supercute.sweep --module tok --self
python -m supercute.sweep --module realtok --self
python -m supercute.sweep --module publiclift --self
python -m supercute.sweep --module hard --self
```

A clean release should print `ALL CONSISTENT` for the sweep checks and `ALL 104 TASKS CLEAN` for the full self-check.

## Run a model sweep

Any OpenAI-compatible chat endpoint works. The default base URL is OpenRouter.

```bash
OPENROUTER_API_KEY=... python -m supercute.sweep \
  --module realtok \
  --model openai/gpt-5.5 \
  --per-task 4 \
  --workers 4 \
  --timeout 240
```

Hard synthetic long-horizon tier:

```bash
OPENROUTER_API_KEY=... python -m supercute.sweep \
  --module hard \
  --tasks iterated_lut \
  --model openai/gpt-5.5 \
  --per-task 5 \
  --workers 2 \
  --timeout 420
```

PublicLift templates:

```bash
OPENROUTER_API_KEY=... python -m supercute.sweep \
  --module publiclift \
  --model openai/gpt-5.5 \
  --per-task 3 \
  --workers 2 \
  --timeout 420
```

## Reproduce the paper tables

The release includes raw per-call metadata in `data/eval_results.jsonl` and an analyzed summary in `data/eval_summary.json`. The analysis drops provider/transport errors from scored denominators and records the dropped counts explicitly.

```bash
python -m supercute.analyze_eval
python -m supercute.make_figure
```

The submission draft is in `paper/main.tex`.

```bash
cd paper
latexmk -pdf main.tex
```

## Raw failure audit for future runs

For a manual error taxonomy, run the full evaluator with raw output capture:

```bash
OPENROUTER_API_KEY=... python -m supercute.full_eval \
  --n 8 \
  --raw-out data/eval_raw.jsonl

python -m supercute.error_audit data/eval_raw.jsonl --tier lut --n 20
```

Raw audit files can contain prompts, oracle answers, and model responses; review them before sharing.

## Design rules for new hard tasks

A task is a strong SUPERCUTE candidate when it has:

- ground truth a Python function can compute exactly;
- an answer with many ways to be wrong — a full reconstructed string or table, not a yes/no label;
- many small changes that each depend on the ones before;
- no shortcut — no formula, no "only the last write matters", no single running total;
- tricky characters only where they would actually show up in real work;
- metadata that reports event counts, operation counts, and source family.

Public dataset reuse should follow the **procedural lift** pattern:

```text
public record -> mutable state -> fresh seeded changelog -> Python oracle -> exact final-state answer
```

Do not ask the original public benchmark question directly. Models may have memorized it, and answering it tests recall, not careful work.

## Repository map

```text
supercute/                 benchmark generators and harnesses
  scenarios_tok.py         character perception probes
  scenarios_realtok.py     real-life workflows with character-exact details
  scenarios_publiclift.py  public-dataset-inspired lift templates
  scenarios_hard.py        long-horizon execution stress tests
  sweep.py                 quick per-module model sweep
  full_eval.py             six-model paper evaluation harness
  analyze_eval.py          Wilson intervals, denominators, compounding fit
  make_figure.py           break-curve figure
  error_audit.py           manual failure review helper for raw-output runs

data/                      supplied generated/evaluation artifacts
paper/                     LaTeX paper, figure, compiled PDF

docs/                      findings, dataset-hardening notes, release notes
```

## Citation

```bibtex
@misc{kirdey2026supercute,
  title  = {SUPERCUTE: Measuring Exact Character Perception and
            Long-Workflow State Tracking in Language Models},
  author = {Kirdey, Stanislav and {Clark Labs Inc.}},
  year   = {2026},
  url    = {https://github.com/clark-labs-inc/supercute}
}
```

See also `CITATION.cff` and `paper/main.tex`.

## License

Code is MIT licensed. Public datasets referenced by adapters keep their original licenses; see `THIRD_PARTY_DATA.md` before redistributing derived prompts or data.
