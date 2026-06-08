# Red-Teaming GPT-5.5: What Breaks It, What Does Not, and What the Paper Now Claims

**Scope.** This document summarizes the exploratory red-team session that motivated SUPERCUTE. The original notes used stronger language than the revised paper. The revised claim is narrower: isolated tokenizer perception did not reliably break GPT-5.5 in our runs, while long exact execution over mutable state exposed sharp but model-specific failures. The paid six-model LUT sweep shows that this is not a universal frontier wall because Opus 4.8 performs much better than GPT-5.5 on the controlled LUT tier.

## Setup

| Item | Value |
|---|---|
| Main target | `openai/gpt-5.5` through OpenRouter, June 2026 |
| Comparators | `anthropic/claude-opus-4.8`, `qwen/qwen3.5-flash-02-23`, later six-model paid run |
| Grading | deterministic oracle plus robust final-answer extractor |
| Tool assumption | no code interpreter on the endpoint, checked with a SHA-256 diagnostic |

A reasoning-robust grader and a free self-check were prerequisites. Earlier exploratory benchmarks had produced false failures from answer-extraction artifacts, so every generator has a no-cost self-check.

## What did not break GPT-5.5

### Tokenization and perception

The tokenizer/perception battery included homoglyphs, invisibles, combining marks, Unicode normalization, case-folding expansion, astral code points, UTF-8 byte length, confusable digits, large-number digit operations, and grapheme segmentation. GPT-5.5 scored near saturation on the supplied runs. A scaled hidden-target document probe also did not break it.

**Interpretation:** tokenizer-sensitive text is still useful for stratifying weaker models, but isolated byte/code-point perception is not a strong GPT-5.5 breaker.

### Static exact character computation

Long-but-static tasks such as deep code-point counting, reading a column, deinterleaving strings, and frequency ranking were mostly solved. Length alone was not enough.

### Single-accumulator chains

Pointer chasing and relabel chains survived moderate horizons. Tracking one state variable through a chain is much easier than maintaining a wide mutable state.

### Algebraic shortcut tasks

A linear cellular automaton looked like an execution task but was solved because it has a closed-form binomial/Pascal-triangle shortcut. This motivated the random LUT design.

## What did break GPT-5.5 in exploratory runs

The exploratory `iterated_lut` task uses a random 10 x 10 transition table over a whole digit string. Each round updates every cell from the current digit and its right neighbor. The task is exact, full-state, and has no known closed form.

Early calibrated runs around 1500-1900 interdependent updates pushed GPT-5.5 to 0% in small samples while returning complete, normally stopped answers. That remains a real and useful signal: the model can finish a long exact task and still lose state.

## What the full paid run changed

The six-model paper run makes the story more nuanced.

| Model | LUT correct | Accuracy |
|---|---:|---:|
| Opus 4.8 | 33/40 | 0.825 |
| DeepSeek V4 Pro | 16/40 | 0.400 |
| GPT-5.5 | 15/40 | 0.375 |
| Qwen 3.5 Flash | 11/40 | 0.275 |
| MiniMax M3 | 10/40 | 0.250 |
| Qwen 3.7 Plus | 4/37 | 0.108 |

At K=60, GPT-5.5 scored 0/8 while Opus 4.8 scored 8/8. Therefore the correct paper framing is **model-specific long-horizon reliability**, not "all frontier models hit the same wall." The curves are also non-monotonic at n=8/cell, so they should be treated as pilot calibration.

## Current conclusion

1. Tokenization and Unicode perception are weak GPT-5.5 stressors in isolation.
2. Realistic mutable workflows are harder and more human-relevant.
3. Shortcut-free full-state execution is the most promising controlled stressor, but current results are model-specific and token-budget-confounded.
4. The next scientific step is larger n, a two-dimensional width x depth sweep, raw-output failure analysis, and a human baseline.

See `paper/main.pdf` for the reviewer-aligned version of the claims.
