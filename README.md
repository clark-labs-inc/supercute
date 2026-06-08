# SUPERCUTE

**SUPERCUTE** is a deterministic benchmark suite for testing whether language models can do exact work over characters, identifiers, tables, documents, and long mutable state.

The current release is intentionally different from the original byte-tokenization thesis. The supplied June 2026 red-team results show that GPT-5.5 does not fail reliably on isolated Unicode, byte, or character-perception probes. Harder failures appear when exact details are embedded inside long mutable workflows. The strongest claims are deliberately scoped: the long-horizon results are model-specific, noisy at n=8/cell, and confounded by reasoning-token budgets.

## Main result

Across the supplied June 2026 OpenRouter runs:

| Tier | What it tests | GPT-5.5 result | Important caveat |
|---|---|---:|---|
| `tok` | Unicode, invisibles, homoglyphs, code points, UTF-8 bytes, graphemes | 0.980 | does not break GPT-5.5 |
| `realtok` | realistic tokenizer friction inside mutable work tasks | 0.781 | denominators exclude provider/transport errors |
| `iterated_lut` break curve | shortcut-free full-state execution over 330-1650 dependent updates | 0.375 overall; 0/8 at 1320 updates | Opus 4.8 scores 0.825 overall and 8/8 at 1320 updates |

The careful headline is:

> Isolated tokenizer perception is a weak stressor for GPT-5.5. Long exact execution over mutable state exposes high-variance, model-specific reliability failures, but the current data do not show a universal frontier wall.

## What is included

SUPERCUTE ships four benchmark layers:

1. **Classic exact-character tasks**: finance identifiers, checksums, Unicode, biology strings, code strings, networking/date tasks.
2. **Tokenization perception probes (`scenarios_tok.py`)**: homoglyphs, zero-width characters, combining marks, Unicode normalization, astral code points, UTF-8 byte length, confusable digits, grapheme segmentation.
3. **RealTok (`scenarios_realtok.py`)**: realistic office/workflow tasks with tokenizer-sensitive details embedded in long mutable state: CRM edit replay, CSV ETL, legal redlines, warehouse inventory, localization tables, redaction audit, clinical sequence reconstruction, and ticket logs.
4. **PublicLift (`scenarios_publiclift.py`)**: public-dataset-inspired templates for FinQA/TAT-QA, TabFact/WikiTableQuestions, CUAD/ContractNLI, CORD/SROIE/DocVQA, LogHub, CRUXEval/LiveCodeBench/CodeNet, SWE-bench, and SpreadsheetBench. These use synthetic seeded records by default, plus adapter contracts for replacing them with official public dataset records under their licenses. PublicLift is released infrastructure, not a scored result in the supplied paper run.

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

Any OpenAI-compatible chat endpoint can be used. The default base URL is OpenRouter.

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

## Reproduce the supplied paper tables

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

- deterministic code-computed ground truth;
- a high-entropy exact answer, not a yes/no label;
- many interdependent state updates;
- no algebraic or last-write-wins shortcut;
- tokenizer-sensitive contact points only when they matter to a realistic job;
- clear metadata reporting event counts, operation counts, and source family.

Public dataset reuse should follow the **procedural lift** pattern:

```text
public record -> mutable state -> fresh seeded changelog -> Python oracle -> exact final-state answer
```

Do not ask the original public benchmark question directly. That invites memorization and usually tests retrieval rather than faithful execution.

## Repository map

```text
supercute/                 benchmark generators and harnesses
  scenarios_tok.py         tokenizer-perception probes
  scenarios_realtok.py     realistic tokenizer-friction workflows
  scenarios_publiclift.py  public-dataset-inspired lift templates
  scenarios_hard.py        adversarial long-horizon execution tasks
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

See `CITATION.cff` and `paper/main.tex`.

## License

Code is MIT licensed. Public datasets referenced by adapters keep their original licenses; see `THIRD_PARTY_DATA.md` before redistributing derived prompts or data.
