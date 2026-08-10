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
- carrier-scope decision rule (owner, 2026-08-10, recorded BEFORE the deciding
  measurement so it cannot be chosen after seeing the numbers): the long-form
  Earnings-21/22 carriers cost ~2–3 h per arm, and whether that is reducible is
  being measured as decode throughput at **long** prompt (~4,700 tokens, the
  size at which the collapse to 3.07–4.40 tok/s per slot was observed), against
  the ~13 tok/s seen at 816 tokens. Three configurations separate the competing
  explanations — plain attention scaling (all configs share the long/short
  ratio), q8_0 KV dequantisation cost (f16 improves the long number), or VRAM
  pressure (freeing the mmproj's 2,940 MiB improves the long number).
  **If there is no headroom**, the long-form carriers move under this candidate
  as their own sub-project rather than continuing to gate the study's
  knowledge-introduction track, which runs on the same carriers but does not
  need this policy to be settled first.
  An earlier note in this session calling the CPU-mmproj configuration a "net
  loss" was drawn from **short-prompt data only** (816 tokens, where the KV
  cache is too small for memory pressure to exist) and does not bear on this
  question; it is superseded by the long-prompt measurement.
- status: OPEN
