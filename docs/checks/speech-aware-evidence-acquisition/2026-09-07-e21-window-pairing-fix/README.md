# The window-pairing instrument's saturated-slice bug, fixed and re-proved

Exposure row `SAEA-E21-MF-WINDOW-PAIRING-V1` (`model-free-check`), registered and committed before
either sealed trace below was re-read under the fixed code. **Zero model, GPU, tool, embedder,
tokenizer, network, audio-decode and paid-API contacts.** References and `wer_tags` are reached only
through the registered scoring path's own loaders (`data.references`,
`reproduction.conec_entity_scoring`), never opened by hand.

## The defect, named by the KC-E1 flight closure (commit `c0213993`)

`analysis.e21_window_pairing.stitched_windows_from_trace` recovered a window's hypothesis text from
the sealed `MODEL_RESPONSE` trace record alone. `reproduction.obs_loop` traces that record **in full,
for every slice, including a slice whose decode saturated its 1,024-token cap** — but a saturated
slice is a runaway repetition, not a transcript, and `obs_loop` itself replaces its contribution to
the stitched hypothesis with `""` before joining (`obs_loop`'s own "Saturation QUARANTINE" comment).
The reader never looked at the `OBS` record's `obs_saturated` flag, so it re-admitted exactly the raw
text `obs_loop` had excluded.

The comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2` saturated no slice, so the bug was invisible until
KC-E1 flew: two of its 1,593 windows saturated (call `4360717` at 1,980–2,070 s, 5,426 raw characters;
call `4363614` at 2,340–2,430 s, 4,195 raw characters, both against a ~1,550-character typical
window), and `assert_stitch_reproduces_outputs` refused — the recovered text differed from the sealed
`outputs.jsonl` hypothesis by exactly the raw text plus one joining space, on both calls, with no
residue.

## The fix

`WindowSpan` gets a `saturated: bool = False` field. `stitched_windows_from_trace` now reads each
slice's `OBS` record for `obs_saturated` (defaulting to `False` for a trace that predates the field)
and, when it is true, forces that window's recovered `text` to `""` — exactly what `obs_loop` actually
stitched — while keeping the window in the call's span list (only a *skip* removes a slice from
`stitched_request_ids`; a saturation never does) and setting `saturated=True` on it. The drop is now a
named, countable covariate of the pairing rather than a silent one: `WindowSpan.as_dict()` carries the
flag into every downstream row.

`tests/unit/test_e21_window_pairing.py` adds a synthetic trace with one saturated slice carrying a
large raw `MODEL_RESPONSE` (standing in for a runaway decode): before the fix the recovered text would
have been that raw string and the byte-for-byte stitch proof would have failed on it; after the fix
the window's text is `""`, `saturated` is `True` on that window alone, and
`assert_stitch_reproduces_outputs` passes against the hypothesis `obs_loop` actually emitted. All 25
tests in the file pass, `ruff` is clean on the changed files, and
`scripts/checks/engineering_base_check.py` PASSes.

`scripts/e21_window_pairing_read.py` — the runner this fix is proved through — is generalized from one
hardcoded sealed profile to a `SEALED_PROFILES` map keyed by run id, so the same instrument checks
either sealed run below by `--run-id` alone.

## The proof, on real sealed bytes — both PASS

| | `direct-baseline/` (comparator) | `kc-e1/` |
|---|---|---|
| source run | `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | `SAEA-E21-KC-E1-BRIEF-44-V1` |
| source attempt | `attempt-20260904T233816Z-bcd338` | `attempt-20260907T171238Z-f02eef` |
| saturated windows | 0 (regression check) | 2 (the case that found the bug) |
| verdict | **PASS** | **PASS** |
| corpus WER, per-window sum | **8.200 %** | **8.736 %** |
| corpus WER, sealed | 8.200 % | 8.736 % |
| S / D / I | 13,098 / 5,701 / 10,700 | 13,022 / 8,393 / 10,014 |
| reference words | 359,765 | 359,765 |
| wall clock | 585.2 s | 603.7 s |
| rows sha256 | `8fa8089fb675…` | `56b86473ba87…` |

Every published entity class reproduces exactly on both runs, class by class:

| class | comparator sum % | comparator sealed % | KC-E1 sum % | KC-E1 sealed % | ref words (both) |
|---|---:|---:|---:|---:|---:|
| PERSON | 22.49 | 22.5 | 18.34 | 18.34 | 2,917 |
| ORG | 17.21 | 17.2 | 17.99 | 17.99 | 4,363 |
| GPE | 18.67 | 18.7 | 19.52 | 19.52 | 1,537 |
| LOC | 2.47 | 2.5 | 2.68 | 2.68 | 485 |
| PRODUCT | 19.23 | 19.2 | 16.67 | 16.67 | 390 |
| EVENT | 2.43 | 2.4 | 2.43 | 2.43 | 494 |
| NORP | 9.75 | 9.7 | 11.86 | 11.86 | 236 |
| FAC | 21.31 | 21.3 | 21.31 | 21.31 | 122 |

(The comparator's sealed figures are the rounded ones its own note publishes, hence the last-digit
rounding gap already present in the 2026-09-06 receipt; KC-E1's sealed figures are quoted directly
from its own `flight/score-read.json` aggregates at the same rounding the live computation uses, so
they match to the digit.)

Also exact on both: `non_entity_wer_percent` (4.730 / 5.507), `unlabelled_reference_words` (1,479 /
1,479), `negation_critical_high_reference_words` (100 / 120), `negation_critical_high_insertions`
(56 / 43), and `numeric_expected` (9,734 / 9,734 — this count partitions exactly on both runs; only
`numeric_matched` can fall short of the call-pooled figure, module docstring, and both runs report a
shortfall under 1 % rather than hiding it).

**Spot check on the two saturated windows themselves**: `4360717#w0023` and `4363614#w0027` each
carry `saturated: true` and `reference_words: 0` in `window-rows-kc-e1-brief-44-v1.json` — because a
window that contributes zero hypothesis words is never the window a hypothesis index or a trailing
deletion's cursor lands in (`charge_operations_to_windows`), it is charged no operation at all, exactly
as a window that stitched nothing should be.

## Files

| file | what it holds |
|---|---|
| `direct-baseline/reaggregation.json` | the regression check against the comparator (0 saturated windows) — every check, the pooled entity buckets, the semantic-impact totals, the numeric counts, and the rows file's own path and SHA-256 |
| `kc-e1/reaggregation.json` | the new proof against KC-E1 (2 saturated windows) — same shape |
| `MANIFEST.sha256` | this directory's own byte manifest |

Per-window rows for both runs are written under `$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/`
(`window-rows-direct-baseline-v2-postfix.json`, `window-rows-kc-e1-brief-44-v1.json`) — per-request
derivatives of sealed model outputs, so they live where those live and never in Git. The 2026-09-06
receipt this row's earlier build produced (`docs/checks/speech-aware-evidence-acquisition/
2026-09-06-e21-window-pairing/`) is untouched and stays sealed under its own `MANIFEST.sha256`; this
receipt supersedes nothing, it proves the fixed instrument.
