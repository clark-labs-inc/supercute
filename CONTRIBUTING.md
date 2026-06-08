# Contributing

SUPERCUTE tasks must be deterministic, automatically gradeable, and honest about what they test.

## Acceptance rules for a new scenario

1. The generator returns a dict with `task`, `kind`, `answer`, `prompt`, and `meta`.
2. Ground truth is computed by code, not copied from a model.
3. `python -m supercute.sweep --module <module> --self` must pass.
4. The prompt must have a high-entropy exact answer unless the task is explicitly a sanity probe.
5. Hard frontier tasks should avoid algebraic shortcuts, last-write-wins shortcuts, and yes/no labels.
6. Public-dataset tasks should use official sources under their licenses and should transform records through a fresh seeded changelog instead of asking the original benchmark question.

## Development checks

```bash
python -m pip install -e '.[dev]'
python -m unittest
python -m supercute.selfcheck
python -m supercute.sweep --module tok --self
python -m supercute.sweep --module realtok --self
python -m supercute.sweep --module publiclift --self
```

## Reporting model results

Always report the model identifier, provider, date, temperature, reasoning/effort setting, sample size, exact task list, timeout, transport errors, and completion/reasoning token accounting when available.
