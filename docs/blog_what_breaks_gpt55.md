# What Breaks GPT-5.5? A Careful SUPERCUTE Summary

SUPERCUTE started with a simple suspicion: maybe the tokenizer is still the weak point. Maybe hidden Unicode, look-alike letters, zero-width characters, or byte-level details would break a frontier reasoning model.

That was mostly wrong for GPT-5.5.

On the character-perception battery, GPT-5.5 was near saturation. It spotted the Cyrillic letter pretending to be a Latin one, found the zero-width space hiding inside a customer ID, told Unicode normalization forms apart, counted graphemes and UTF-8 bytes, and caught confusable digits. These probes still separate weaker models from stronger ones, but on their own they do not break GPT-5.5.

What does hurt is real work. RealTok takes the same character details and buries them inside jobs a person might delegate: replaying dozens of CRM record edits, cleaning a Unicode-noisy invoice CSV, applying sequential legal redlines to a contract, reconciling warehouse barcode scans, merging localization tables. GPT-5.5 drops from 0.980 on the perception probes to 0.781 on RealTok.

The controlled synthetic version is `iterated_lut`: apply a random lookup table to a 22-digit string, round after round, where every digit changes every round and there is no shortcut. GPT-5.5 falls apart at longer horizons — 0/8 at one 1320-update setting — while finishing its answers normally. It does the whole job and still loses the state along the way. But the most important update is that this is not a universal frontier wall: Opus 4.8 scores 33/40 overall on the same sweep and goes 8/8 at that same 1320-update setting.

So the careful headline is:

> GPT-5.5 can see the tricky characters just fine. Carrying exact state through hundreds of small dependent changes is much harder, and it fails in model-specific, high-variance ways rather than at some shared frontier limit.

The next benchmark step is not another weird-character puzzle. It is bigger exact-state sweeps: more samples per cell, width-by-depth grids, raw-output failure analysis, human baselines, and public-dataset workflows where the model must replay realistic changes and report an exact final state.
