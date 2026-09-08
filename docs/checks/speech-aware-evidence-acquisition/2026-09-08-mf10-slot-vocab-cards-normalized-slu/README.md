# MF-10 — slot vocabulary cards and the normalized SLU scorer (2026-09-08)

Row id `SAEA-SLURP-MF10-VOCAB-CARDS-NORMALIZED-SLU-V1`, profile `model-free-check`.
**Zero model, GPU, tool, embedding, network, audio-decode and tokenizer contacts. Zero paid spend.**
Note: `docs/readiness/2026-09-08-mf10-slot-vocabulary-cards-and-normalized-slu-v1.md`.
Generator: `scripts/mf10_slot_vocab_cards_normalized_slu.py` (subcommands `classes`, `views`,
`normalized`, `ladder`).
Modules: `src/speech_aware_evidence_acquisition/reproduction/slurp_slot_normalizer.py`
(`saea-slurp-slot-normalizer-v1`, scorer id `slurp-slu-f1-normalized-v1`), 35 unit tests in
`tests/unit/test_slurp_slot_normalizer.py`;
`src/speech_aware_evidence_acquisition/analysis/slurp_slot_vocabulary.py`, 33 unit tests in
`tests/unit/test_slurp_slot_vocabulary.py`.

MF-9's attribution engine is imported **by path** and reused, never re-implemented, so the two
audits cannot disagree about what "missing", "surface" or "spurious" mass means. The one subprocess
either audit runs is the **pinned official SLURP `evaluate.py`** (commit `8eb1654…311f1`,
`~/.venvs/slurp-official-eval`, used and never modified) — the scorer, never a model. Token figures
are the **stated whitespace × 1.3 proxy**; no tokenizer was called.

## Headline

| question | answer |
|---|---|
| 1. type classes | **18 CLOSED/FORMAT, 8 MIXED, 29 OPEN/PROPER-NOUN** of 55 TRAIN types. `date` is card-able (289 forms, **90.6 %** of DEV gold verbatim); `place_name` 75.4 %, `person` 57.1 %, `song_name` and `radio_name` **0.0 %**. `time` lands in MIXED at 82.1 % — three points under the floor, and its problem is FORMAT, not vocabulary |
| 1a. the rule that was wrong | The rule this audit DECLARED before reading the table selects **4** types, because the distinct-forms-per-mention ratio is bounded below by `1/mentions`: `alarm_type` has four surface forms in the whole corpus and the declared rule calls it open. Both rules and the 18 types the corrected one moves are in `type-classes.json` |
| 1b. card cost | 18 cards, **842 surface forms**, 3,298 proxy tokens for all of them. Per intent: min 0 (7 intents card nothing), median **1,432**, worst **2,010** (`social_query`). Against KC-S1b's measured worst envelope of 10,006 in a 16,384-token slot, the worst card set **fits with 4,368 proxy tokens to spare**. The 42 full-schema fallback rows would carry every card at 3,313 |
| 2. KU-S3v, priced | Static cards on the closed types reach SLU-F1 **61.81 (+17.46)** vocabulary-limited, 62.99 unrestricted, at **zero retrieval contacts and zero seed GPU hours**. Retrieval on the open types bounds at 53.25; the combined view at **69.21**. Every figure is an ORACLE — a perfect reader of the supplied block |
| 2a. containment | **902 of 1,000 rows COLLIDE as sent** — not because a card leaks, but because the schema block already prints five example fillers per type and **194** of them are card values. Dropping the examples (`examples_per_type=0`, a parameter the loader already takes) takes the collision to **128 rows**, of which **125** are `audiobook` and `takeaway` matching inside the type names `audiobook_name` and `takeaway_order` |
| 2b. the twin | Per-intent rotation, token-matched **by construction**: **39 intents rotate in place and zero differ from the arm by a character**. 14 intents list a single carded type and cannot rotate in place; their volume delta is a reported covariate |
| 3. normalized vs official | comparator **35.80 → 36.43**, KC-S1b **44.35 → 45.09**, value-projected **45.09 → 45.24**. Strict entity F1 **21.91 → 24.98**, **31.37 → 34.44**, **34.68 → 35.29**. The normalizer removes **62.187 of 551.085 (11.28 %)** of the surface-form mass |
| 3a. per rung | R0 case+whitespace **+0.19**; R1, the whole vendored Whisper English normalizer, **+0.00** more on SLU-F1; **R2, the meridiem join Whisper does NOT carry, +0.48**; R3 +0.07. The rung that pays is the one this study had to write itself |
| 3b. per type | `time` strict entity F1 **12.07 → 34.48**; `date` +2.90; `place_name` +2.30; **`person` +0.00**. Three of the owner's types, three different answers |
| 3c. the false-merge audit | The corpus-learned R3 admitted `next`, `last`, `this`, `after`, `every`, `march`, `5th` and collapsed **17 gold values** — `next week`, `last week`, `this week` and `one week` all became `week`. REFUSED. The candidate set is now declared and the corpus only confirms; **2 merges remain** and both are the same value written twice |
| 4. the ladder | The vocabulary card KEEPS its gain under the normalized metric (**+18.64 → +18.69**) because 480 of the 565 mass units it repairs are MISSING: it is a RECALL module. The value projection does not (**+0.74 → +0.15**, and on NEW500 CI90 **[+0.47, +1.10] → [−0.02, +0.27]**): it was buying spelling |
| 4a. admission primary | **Official SLU-F1 primary, normalized SECONDARY that must agree in sign.** KC-S1b's admitted +10.85 becomes +10.96 and passes; the projection's +0.78 becomes +0.11 with an interval across zero and does not |

## Identity anchors, fail-closed

Every read raises rather than reports if the sealed bytes stop reproducing a published verdict.
All held.

* KC-S1b entities strict / Word-F1 / Char-F1 / **SLU-F1** = 31.37 / 41.58 / 47.51 / **44.35**,
  through the normalized scorer's own official half.
* The sealed closed-list comparator = 21.91 / 33.69 / 38.20 / **35.80**.
* The rebuilt value-projected arm (`normalized` family, τ = 0.20) = **45.09**, MF-9's own number.
* MF-9's corpus TP mass **846.0** and loss mass **2,123.085**, and both of its published ceilings
  (`no_missing` **75.75**, `surface_perfect` **51.84**) rebuilt from its per-type table.
* MF-9's DEV verbatim shares for `date` **90.57**, `transport_type` **100.0**, `person` **57.14**
  and `song_name` **0.0**, checked before the rest of that receipt is read.
* The NORMALIZED per-type attribution closes against the normalized corpus mass, and the normalized
  loss table rebuilds the normalized base **45.09**.
* The retrieval upper bound's global version (**69.24**) sits above MF-9's own measured KU-S3 oracle
  (**58.06**), as a bound must.

## Files

| file | what it carries |
|---|---|
| `type-classes.json` | the 55 types under BOTH classification rules, the three TRAIN statistics per type, the 18 full vocabulary cards with every surface form and count, the per-intent card cost, and the budget check |
| `knowledge-views.json` | the three priced views, their oracle ceilings, the containment decomposition and its resolution, and the per-intent twin mapping |
| `normalized-slu.json` | the three arms official beside normalized, the per-rule cumulative table, the per-type strict F1 both ways, the paired CI90 contrasts, the false-merge audit, the R3 candidate-filter evidence, and the normalized per-type loss table |
| `ladder-both-scorers.json` | MF-9's rungs re-priced under both metrics, the two ceilings under both, and the admission-primary recommendation |

## What this is not

It admits nothing, promotes nothing, preregisters no cell, opens no roster, draws no split, re-locks
no comparator and reaches no superiority, generalization or Stage-3 conclusion. **The official
number is never replaced**: `slurp-slu-f1-normalized-v1` is an ADDITIONAL scorer id reported beside
`slurp-slu-official`, exactly as `asr-wer-whisper` sits beside `asr-wer`, and no verdict, lock or
admission in this repository is restated under it.
