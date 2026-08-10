# Innovation-candidate ledger (append-only)

Every entry is a falsifiable delta claim with evidence pointers. Entries are
never edited or deleted; corrections append a new entry referencing the old
one. Sources (design spec §6): (1) reproduction failure modes from probe gap
memos, (2) the contract's three capability gaps (accessibility,
currency/proper-name, verifiability), (3) structural boundary gaps
(NOT_READY lines from the readiness memo).

Entry format:

## IC-<nnn> <short title> (<YYYY-MM-DD>)

- source: failure-mode | capability-gap | boundary-gap
- axis: OBS | ORG | SUPPLY | USE
- claim: "prior P has failure mode F under our boundary; axis control C removes F"
  (or the capability/boundary-gap analogue)
- null hypothesis: what result would falsify the claim
- evidence: receipt / ledger-row / memo paths
- status: OPEN | PROMOTED_TO_2B | RETIRED

---

## IC-001 Interleaved listening-and-spelling with a compacted carried history (2026-08-10)

- source: failure-mode
- axis: OBS (primary); the compaction component spans ORG and SUPPLY
- claim: "The fixed-window / model-declared-boundary / overlap-and-stitch policy
  for long-form transcription on a frozen core — the shape Whisper's long-form
  strategy established and this study's substrate reproduces — has two failure
  modes under our boundary that are **structural, not parametric**: (F1) the
  reconciliation of overlapping chunks removes content beyond what overlap
  explains, and (F2) advancing on a boundary the model declares in seconds
  inherits that model's temporal-grounding error. An interleaved
  listening-and-spelling control policy — commit a fixed small audio step with
  left context and right lookahead, condition on a carried text history, append
  the decode, and compact the history under a token budget — removes both by
  construction: there is no merge step to over-delete, and no timestamp is asked
  for."
- measured basis for F1 and F2 (this study, `nocontext` arm, 614 slices):
  deletions are 60.6 % of all errors; excess removal at the stitch is 10,693
  words = 86.0 % of deletions, per-sample r = 0.847; advance overrun is 1,648 s
  of audio never transcribed. For F2's mechanism on our exact model, the
  chaptering evaluation reports a median timestamp deviation of 11.8 s — larger
  than our whole overlap window.
- null hypothesis: the claim is falsified if, at a **matched audio-token budget**
  (the `window ÷ step` multiplier held equal), the interleaved policy does not
  reduce the deletion share below the fixed-window policy's 60.6 %, or does not
  improve corpus WER against the 26.61 % baseline. The compaction component is
  falsified separately if a compacted history does not beat a plain verbatim
  tail at equal token budget.
- known non-novel components, recorded so the claim is not overstated: chunked
  prompting, conditioning on previously decoded text (Whisper's
  `condition_on_previous_text`), and rolling summarisation are each established.
  What is being claimed is the combination **outside** a trained model, on an
  API-only frozen core with no parameter access. A prior-art proximity search
  was commissioned 2026-08-10; its findings attach to this entry and may retire
  it.
- evidence: `docs/readiness/2026-08-10-interleaved-listening-and-spelling.md`,
  `docs/readiness/2026-08-10-segmentation-who-decides-the-cut.md`,
  `docs/readiness/2026-08-09-deletion-mass-is-made-at-the-stitch.md`,
  `docs/readiness/2026-08-09-segmentation-cost-model.md`; run bundle
  `SAEA-E-002-r4-nocontext` attempt `attempt-20260809T194151Z-ecdb38`
  (study_commit `63d0f57`)
- status: OPEN
