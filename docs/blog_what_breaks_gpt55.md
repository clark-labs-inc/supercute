# What Breaks GPT-5.5? A Careful SUPERCUTE Summary

SUPERCUTE started with a simple suspicion: maybe the tokenizer is still the weak point. Maybe hidden Unicode, look-alike letters, zero-width characters, or byte-level details would break a frontier reasoning model.

That was mostly wrong for GPT-5.5.

On the supplied tokenizer-perception battery, GPT-5.5 was near saturation. It handled homoglyphs, invisibles, Unicode normalization, UTF-8 byte length, code points, confusable digits, and grapheme operations. These tasks still stratify weaker models, but they are not enough to break GPT-5.5 by themselves.

The harder pattern is different: long exact work over mutable state. RealTok turns character-sensitive details into realistic tasks such as CRM edit replay, invoice CSV cleanup, legal redline merge, warehouse reconciliation, and localization table merging. GPT-5.5 drops from 0.980 on tokenizer perception to 0.781 on RealTok.

The controlled synthetic version is `iterated_lut`: a random transition table applied repeatedly to a full digit state. GPT-5.5 falls sharply on this task at longer horizons, including 0/8 at one 1320-update setting. But the most important update is that this is not a universal frontier wall: Opus 4.8 scores 33/40 overall on the same LUT sweep and reaches 8/8 at that 1320-update setting.

So the careful headline is:

> GPT-5.5 is not reliably broken by isolated tokenizer perception. Long exact execution over mutable state is much harder, but the current evidence shows model-specific, high-variance failures rather than a universal frontier limit.

The next benchmark step is not another weird-character puzzle. It is larger exact-state sweeps: more samples, width-by-depth grids, raw-output failure analysis, human baselines, and public-dataset-derived workflows where the model must replay realistic changes and output an exact final state.
