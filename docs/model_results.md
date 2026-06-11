# Model results

The June 2026 run evaluated six reasoning-enabled models through OpenRouter:

- `openai/gpt-5.5`
- `anthropic/claude-opus-4.8`
- `deepseek/deepseek-v4-pro`
- `minimax/minimax-m3`
- `qwen/qwen3.7-plus`
- `qwen/qwen3.5-flash-02-23`

The run has three **scored** tiers:

1. `tok`: 19 character-perception probes (homoglyphs, zero-width characters, normalization, graphemes, bytes), n=8 per task.
2. `realtok`: 8 real-life workflows (CRM edit replay, invoice cleanup, legal redlines, warehouse scans, and more), n=8 per task.
3. `lut`: `iterated_lut` break curve at K = 15, 30, 45, 60, 75 with L = 22.

`publiclift` ships in the release as self-checked infrastructure and dataset-hardening templates, but it was not part of the paid model run.

## Denominators

The raw run contains 1536 calls. Thirteen provider/transport errors are preserved in `data/eval_results.jsonl` with `err=true` and dropped from scored denominators, leaving 1523 scored rows. This is why the RealTok and Qwen 3.7 Plus LUT denominators vary.

## Tier-level accuracy

| Tier | GPT-5.5 | Opus 4.8 | DeepSeek V4 Pro | MiniMax M3 | Qwen 3.7 Plus | Qwen 3.5 Flash |
|---|---:|---:|---:|---:|---:|---:|
| Character perception | 0.980 | 0.842 | 0.895 | 0.849 | 0.862 | 0.796 |
| RealTok | 0.781 | 0.524 | 0.532 | 0.410 | 0.333 | 0.219 |
| `iterated_lut` break curve | 0.375 | 0.825 | 0.400 | 0.250 | 0.108 | 0.275 |

Read the `iterated_lut` row alongside token spend. At K=60, GPT-5.5 averages about 16.8k completion tokens and scores 0/8; Opus 4.8 averages about 34.8k completion tokens and scores 8/8. GPT-5.5's token use rises through K=45 and then mostly plateaus, while Opus keeps writing more as K grows. Smaller models can spend even more tokens and still fail, so budget matters but is not enough by itself.

## Important negative result

GPT-5.5 did not break on character perception. It was near-perfect at spotting homoglyphs, zero-width characters, combining marks, Unicode normalization differences, code points, UTF-8 byte lengths, confusable digits, and grapheme boundaries.

## Strongest positive result

The strongest positive result is not a universal frontier claim. It is a **model-specific reliability result**: when a task requires carrying exact state through hundreds of dependent updates with no shortcut, GPT-5.5 and several other models fail sharply, while Opus 4.8 stays strong on the same tier.

The descriptive compounding fit from `python -m supercute.analyze_eval` estimates:

| Model | Fitted per-round survival r | Fitted per-update survival q | Half-life updates |
|---|---:|---:|---:|
| Opus 4.8 | 0.9956 | 0.999800 | 3459 |
| DeepSeek V4 Pro | 0.9790 | 0.999034 | 717 |
| GPT-5.5 | 0.9739 | 0.998798 | 576 |
| MiniMax M3 | 0.9690 | 0.998572 | 485 |
| Qwen 3.5 Flash | 0.9659 | 0.998422 | 439 |
| Qwen 3.7 Plus | 0.9359 | 0.996993 | 230 |

This fit is descriptive only; the n=8 cells are too small and non-monotonic for strong causal claims.

## Required next experiments

- Increase LUT to at least 30-50 variants per model/K cell.
- Run a two-dimensional L x K sweep to separate state width from sequential depth.
- Add raw-output failure review with `--raw-out` and `python -m supercute.error_audit`.
- Add a human baseline for representative RealTok and PublicLift items.
- Run a paid PublicLift sweep before presenting PublicLift as an empirical result.

## Files

- Raw call metadata: `data/eval_results.jsonl`
- Summary with Wilson intervals and compounding fits: `data/eval_summary.json`
- Figure generator: `supercute/make_figure.py`
- Paper figure: `paper/figures/breakcurve.png`
