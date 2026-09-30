# S2a.1 missing-slot proposal tool, offline recall ceiling: T = 0.086 on the 70 not-in-supply items of COMP-1b Fold A, and no ranker can pass 0.47, so reading (a) is out of reach (DESCRIPTIVE, offline)

Date: 2026-09-30. Read id `SAEA-SLURP-S2A1-RECALL-CEILING-V1`, recipe `slurp-s2a1-missing-slot-recall-ceiling-v1`. This is
step S2a.1 of the S2a design (`docs/superpowers/specs/2026-09-30-slurp-s2a-missing-slot-proposal-probe-design.md`,
section 1.2 for the tool contract and section 2 for the "S2a.1 precondition"). Written by Claude Opus 5.5, the analysis
agent on the coordinator's brief, in worktree `fable/s2a1` (base master `9ec364aba`).

**Status: DESCRIPTIVE.** These are development numbers on TRAIN Fold B (tuning) and TRAIN Fold A (read), both
construction rosters (owner decisions 28 and 86). The note registers nothing, admits nothing and authorises no flight.
The verdict word belongs to the coordinator.

**Contacts: zero of every kind.** There were no model, server, tokenizer, encoder, embedder, Whisper, GPU, network or
scorer-subprocess contacts. The E5-0 transcript catalogs already existed. They were re-hashed against their receipts
(Fold A `de504e45...`, Fold B `31462f9b...`) before any transcript was read. `core.flight.cli`, `lease_cli`, re-pins,
the queue and the flight worktree were not touched. The read is CPU-only: 1 min 44 s, peak 0.75 GB.

**Gold and text discipline.** Gold entered offline, on the scoring side only, through the governed TRAIN loader
`data.slurp.load_slurp_split`. The devel and test splits were not read. The abstain threshold was fitted on Fold B.
Fold A gold was used only to classify outcomes; nothing was tuned on it. No utterance text, transcript, gold value,
span or model output is printed or persisted. Only ids, counts, rates, slot TYPE names and hashes appear.

**DEV-2000-ADDED.** No E5-0 catalog exists for DEV-2000-ADDED (`prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1/` holds
`fold-a` and `fold-b` only). A2's 80 items were therefore **not measured**, and no catalog was created. That pass is
S2a.2, which needs its own owner row.

## 0. Method

**Driver.** The driver is `scripts/analysis/slurp_s2a1_recall_ceiling.py` (new). Its unit test is
`tests/unit/test_slurp_s2a1_recall_ceiling.py` (9 synthetic tests). The driver imports these unchanged:

- from the E5 read (`scripts/analysis/e5_transcript_consistency_read.py`): `load_catalog`, `canon_tokens` (the
  canonicaliser `rails.relisten.canonical_value`), `gold_span_containment`, `gold_kinds` and `load_arm`;
- from S1 (`scripts/analysis/slurp_s1_slu_error_taxonomy.py`): `load_scores`, `supply_class` and `origin_short`;
- through S1's own imports: the node ledger's `derive_arm` / `slot_ledger`, and the headroom note's `Rescorer` and
  `evidence_class`.

**Stop checks.** The run stops unless all three of these hold. All three held.

- **S1 reproduction.** COMP-1b Fold A has MISSING 189 items on 172 rows, of which 70 are not in the supply.
- **E5 containment.** Fold A is 707 / 941 = 0.7513 and Fold B is 718 / 944 = 0.7606.
- **E5 cross-check.** The MISSING items the transcript contains number 130, equal to the E5 read's section 4 count on
  comp1b.

**The tool, built deterministically.** One call `(row, slot_type t)` returns at most **3** spans of at most **5**
tokens. Each span must meet three conditions:

1. It is a contiguous run of the row's canonical E5-0 transcript. This is the canonical token list the 0.7513
   containment uses.
2. It touches no transcript position that is covered by a canonical occurrence of an entity value in the row's
   **delivered** column (the draft filter).
3. Its score is at least the abstain threshold theta, and above 0. The score is the maximum **character-trigram
   Jaccard** similarity between the span and the distinct canonical TRAIN values of type `t`.

Candidates are ranked by score (descending), then earlier start, then shorter span. Identical spans are returned
once, and nothing pads the list. The gold value counts as returned when its canonical token tuple equals a
candidate's.

**Choices where the spec is under-specified.** Each one is stated here.

- **Lexicon, primary.** "Slot store v2's train-only build" is read as the TRAIN gold values of the slot store v2
  snapshot's own `source_sample_ids` (`slot-contracts-v2`, snapshot `d5992bd1...`, partition role `train`): 3,162
  records. Every utterance on the Fold A or Fold B roster is then removed, matched by `slurp_id` across recordings.
  The removal took 0 records: the store's sources do not overlap either fold. The result is **54 types and 779
  distinct values**.
- **Lexicon, sensitivity.** All of TRAIN minus the Fold A and Fold B utterances: 37,407 records (13,221 dropped),
  **54 types and 3,648 distinct values**.
- **Checks on both lexicons.** Both are asserted to hold TRAIN records only. Neither was built from S1's items.
- **Threshold fit (Fold B only).** The tuning column is the E5 tuning arm, `SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1` (the
  AGREE arm on Fold B).
  - **Targets:** each of its 181 MISSING gold items, called with its gold type.
  - **Negatives:** the 59,219 (row, type) calls over the closed 55-type set that carry no MISSING item of that type.
  - **Rule:** theta maximises Youden J = TPR - FPR on a 0.05 grid, with ties going to the lower theta. Here
    TPR = gold among the candidates and FPR = a non-empty result on a negative call.
  - **Chosen:** theta **0.50** (primary; TPR 0.4696, FPR 0.0226) and **0.60** (sensitivity; TPR 0.5470, FPR 0.0317).
  - The caps (3 spans, 5 tokens) are the contract's and were not fitted.
- **Draft.** The draft is the delivered column. The Solver's pre-review draft is not separated.

## 1. T on COMP-1b Fold A's 70 not-in-supply MISSING items

Each cell is hits / 70 = T, with the Wilson CI95.

| setting | primary lexicon (theta 0.50) | full-TRAIN lexicon (theta 0.60) |
| --- | --- | --- |
| **contract: top 3 at theta** | **6 / 70 = 0.0857 [0.040, 0.175]** | **12 / 70 = 0.1714 [0.101, 0.276]** |
| top 1 at theta | 3 / 70 = 0.0429 [0.015, 0.119] | 11 / 70 = 0.1571 [0.090, 0.260] |
| top 3, no threshold | 16 / 70 = 0.2286 [0.146, 0.340] | 24 / 70 = 0.3429 [0.243, 0.460] |
| no ranker: every span of at most 5 tokens, draft-filtered (perfect ranker) | 33 / 70 = 0.4714 [0.359, 0.587] | same |
| no ranker: containment within 5 tokens (no draft filter) | 35 / 70 = 0.5000 [0.386, 0.614] | same |
| containment, any length | 35 / 70 = 0.5000 | same |

For context, the same tool over **all 189** MISSING items gives contract T 88 / 189 = 0.4656 (primary) and
102 / 189 = 0.5397 (full TRAIN). Containment there is 130 / 189 = 0.6878.

**Containment falls from 0.75 to 0.50 on the not-in-supply subset.** The 70 items are the ones no supply printed.
Half of them are also absent from the Whisper large-v3 transcript. Every contained item is at most 5 tokens long, so
the length cap costs nothing.

**The ranker loses most of what remains.** The not-in-supply values are, by construction, values the supply did not
show. Under the primary lexicon, 27 of the 33 eligible golds score below the Fold-B theta. With no threshold, 13 still
rank below 3rd. The larger lexicon halves the threshold loss (20 below theta), but T only reaches 0.17.

## 2. Where the misses are (contract, primary lexicon)

| outcome | items of 70 |
| --- | ---: |
| hit (gold among the 3 candidates) | 6 |
| not in the transcript | 35 |
| contained but longer than 5 tokens | 0 |
| every occurrence overlaps the delivered draft | 2 |
| contained and free, but scores below theta 0.50 | 27 |
| scores at or above theta, but not ranked into the top 3 | 0 |

**The same stages with no threshold (primary).** 16 hits, 35 not in the transcript, 2 draft overlaps, 4 with score 0
(no shared trigram), and 13 not ranked into the top 3.

**Gold rank under the contract (primary).** Rank 1: 3; rank 2: 1; rank 3: 2; not returned: 64.

**Per slot type.** Each cell is items: hits / not in transcript / overlaps draft / below theta (primary; full-TRAIN
hits in brackets):

| type | items | hits (full TRAIN) | not in transcript | overlaps draft | below theta |
| --- | ---: | --- | ---: | ---: | ---: |
| place_name | 13 | 1 (4) | 7 | 0 | 5 |
| business_name | 7 | 0 (0) | 5 | 0 | 2 |
| date | 5 | 1 (2) | 2 | 0 | 2 |
| person | 5 | 0 (1) | 3 | 0 | 2 |
| media_type | 4 | 1 (2) | 0 | 0 | 3 |
| business_type | 3 | 1 (0) | 0 | 0 | 2 |
| device_type | 3 | 0 (0) | 2 | 0 | 1 |
| food_type | 3 | 0 (1) | 1 | 1 | 1 |
| list_name | 3 | 0 (1) | 2 | 0 | 1 |
| 20 other types | 24 | 2 (1) | 13 | 1 | 8 |

The two worst transcript types of the E5 read are also the two largest misses here. `business_name` is 5 of 7 not in
the transcript. `person` is 3 of 5.

**False candidates.** On the 908 Fold A rows with no MISSING item, a call with any of the 55 types returns a non-empty
result on 2.30 % of calls (primary; 0.0315 spans per call) and 3.18 % (full TRAIN). Every one of those spans is false.

## 3. The spec's decision (section 2, "S2a.1 precondition")

The spec states c <= T × uptake. At CONV's measured uptake of 0.457 (32 / 70):

- reaching 0.33 needs T >= 0.33 / 0.457 = **0.722**;
- reaching reading (a)'s 27 / 80 = 0.3375 needs T >= **0.738**.

| bound | T | c ceiling at CONV uptake 0.457 | items of 80 | reading (a), c >= 0.3375 |
| --- | ---: | ---: | ---: | --- |
| contract, primary lexicon | 0.0857 | 0.0392 | 3.1 | out of reach |
| contract, full-TRAIN lexicon | 0.1714 | 0.0784 | 6.3 | out of reach |
| any ranker (no-ranker ceiling, draft-filtered) | 0.4714 | 0.2155 | 17.2 | out of reach |
| any ranker, at 100 % uptake | 0.4714 | 0.4714 | 37.7 | the only reachable corner |

**Uptake needed at the contract T.** Reaching 27 / 80 would need an uptake of 3.94 on the primary lexicon, or 1.97 on
full TRAIN. Both are above 1, so both are impossible.

**Verdict for S2a.2 and S2a.3.** T is far below 0.72. It is 0.086 under the contract, 0.17 with the largest faithful
lexicon, and at most 0.47 for any ranker over this transcript, because half of the target values are not in the
transcript at all.

- **Reading (a) (c >= 27 / 80) is unreachable at the CONV uptake** with any ranker. The perfect-ranker ceiling is
  c <= 0.2155 (about 17 of 80).
- **Reading (b) is predicted outright.** Its first clause, a Wilson upper bound of c below 0.33 at c <= 18 / 80, is
  what the bound predicts: c <= 17.2 / 80 even with a perfect ranker. Its second clause, c at or below M1's 0.2471,
  is met by every row of the table (contract c ceiling 0.039-0.078).
- **Recommendation to the coordinator.** Do not request the S2a.2 DEV Whisper pass, and do not register S2a.3 for
  this tool form. The ceiling is set by the pinned Whisper large-v3 transcript, not by the ranker. Containment on
  the target items is 0.50. That places the missing-slot line with S2b (decision 212: a stronger ASR) and not with a
  better lexicon.
- **What could reopen it.** At the CONV uptake, a stronger transcript would need T >= 0.738 after draft filtering and
  ranking: 52 or more of the 70 items, against 33 eligible today even with a perfect ranker. That would be read
  again with this driver.

## 4. What this read does not claim

- **T is a Fold A construction-roster number (70 items).** A2's 80 DEV items were not measured, because they have no
  transcript.
- **The ranker is the simplest faithful reading of the spec,** not an optimised one. A better ranker cannot exceed the
  0.4714 no-ranker ceiling.
- **Uptake is borrowed from CONV (0.457)**, a different supply (a Perception-shortlist conversion). The verdict does
  not depend on it: at the no-ranker ceiling, (a) needs an uptake of 0.716, and at the contract T it needs one above 1.
- **The negative-call set for theta covers all closed types.** The Solver's real type choices are unknown, so the FPR
  is a lower bound on realistic false-candidate exposure.

## 5. Reproduce

```bash
# WSL, model-free; ~1 min 45 s, peak 0.75 GB
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 PYTHONPATH=src python -B scripts/analysis/slurp_s2a1_recall_ceiling.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
# the same with --check: IDENTICAL apart from generated_at
python -B -m pytest -q -p no:cacheprovider tests/unit/test_slurp_s2a1_recall_ceiling.py
```

**Outputs.** They are under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-S2A1-RECALL-CEILING-V1/`: `report.json`,
`tables.md` and `content-sha256.json`. `report.json` also carries per-item outcomes as ids, types, outcome codes and
ranks only.

**Content hashes, with `generated_at` removed.**

- `report.json`: `4a97e15dff78f3d96858398e77f584b839ab26990a1e0a89525d8066fba5910b`
- `tables.md`: `de2d509cdf0ff47f46b88604f1d57cb2d63ed7d06e066474888215e1f3aedeea`

A `--check` re-run reported IDENTICAL apart from `generated_at`.

## Addendum: perfect-ASR bound (input to owner decision 212, "pin a stronger ASR")

Date: 2026-09-30. Same read id and recipe, run with the new `--reference-source reference` flag of the same driver.
Written by Claude Opus 5.5 in worktree `fable/s2a1`. **DESCRIPTIVE; contacts zero of every kind** (no model, Whisper,
GPU, network or scorer-subprocess contact; CPU only, 1 min 52 s, peak 0.76 GB). The verdict word belongs to the
coordinator.

**Question.** Of the 35 not-in-Whisper items, how many gold values are in the SLURP reference transcript, which is
the perfect-ASR bound? And what do T and the c <= T × 0.457 bound become if the tool reads that transcript instead
of Whisper large-v3?

**Method.**

- **Source.** Each Fold A and Fold B recording gets the SLURP reference `sentence` of its utterance. The sentences
  come from the governed TRAIN loader `data.slurp.load_slurp_train_material` (11,514 utterances, 50,628 recordings)
  and enter on the scoring side only. The precedent is the E5 oracle read, which also read references offline. The
  sentences are held in memory only; no sentence, span or gold value is printed or persisted.
- **Everything else is unchanged:** the canonicaliser (`rails.relisten.canonical_value`, as in E5 and S2a.1), the
  5-token span rule, the draft filter, the two lexicons and the Youden-J threshold fit on Fold B. Theta is refitted
  on the Fold B reference rows: 0.45 primary (TPR 0.5801, FPR 0.0246) and 0.55 full-TRAIN (TPR 0.6906, FPR 0.0428).
  For sensitivity, T is also read at the Whisper-fitted theta (0.50 / 0.60).
- **Stop checks, all reproduced.** S1: 189 / 172 / 70. E5 Whisper containment: 707 / 941 and 718 / 944. E5's
  cross-check: 130 contained MISSING items.
- **Reference containment of all gold is 911 / 941 = 0.9681 (Fold A) and 909 / 944 = 0.9629 (Fold B).** It is not
  1.0, because the gold filler is joined from SLURP's annotation tokens while the reference is the sentence text.
- **Default outputs unchanged.** A `--check` of the default Whisper mode is IDENTICAL apart from `generated_at`, and
  its hashes are the ones in section 5.

### A.1 The split of the 35 not-in-Whisper items

| kind (of the 70 not-in-supply items) | items |
| --- | ---: |
| in the Whisper transcript (the S2a.1 containment) | 35 |
| **(i) not in Whisper, in the reference within 5 tokens** (an ASR miss a stronger model could recover) | **28** |
| in the reference only as a span longer than 5 tokens | 0 |
| **(ii) in neither** (never verbatim in the reference under this canonicaliser) | **7** |

- **Inside (ii).** 5 of the 7 occur in the reference once spaces are ignored. That is a tokenisation or spacing
  difference between the annotation tokens and the sentence (for example, a split or joined number or time form).
  An ASR that writes the sentence's form still misses the token-exact match. The other 2 are not present in the
  sentence in any spacing: they are normalised or derived values.
- **Across all 189 MISSING items:** 130 are in Whisper, (i) 51, too long 0, and (ii) 8. Of the 8, 6 are
  spacing-only. Reference containment is 181 / 189 = 0.9577.

**Per slot type** (the 70 items; (i) and (ii) counts; the types not listed have neither):

| type | items | in Whisper | (i) reference only | (ii) neither |
| --- | ---: | ---: | ---: | ---: |
| place_name | 13 | 6 | 7 | 0 |
| business_name | 7 | 2 | 4 | 1 |
| date | 5 | 3 | 1 | 1 |
| person | 5 | 2 | 1 | 2 |
| device_type | 3 | 1 | 2 | 0 |
| list_name | 3 | 1 | 2 | 0 |
| food_type | 3 | 2 | 1 | 0 |
| audiobook_name | 2 | 0 | 2 | 0 |
| artist_name | 2 | 0 | 1 | 1 |
| weather_descriptor | 2 | 1 | 1 | 0 |
| song_name | 1 | 0 | 0 | 1 |
| timeofday | 1 | 0 | 0 | 1 |
| currency_name, music_genre, news_topic, podcast_descriptor, podcast_name, transport_name | 6 | 0 | 6 (1 each) | 0 |
| media_type 4, business_type 3, time 2, and 8 single-item types | 17 | 17 | 0 | 0 |
| **total** | **70** | **35** | **28** | **7** |

The ASR misses concentrate in names: place_name 7, business_name 4, and the media-title types (audiobook, podcast,
artist and music) 6. These are the named-entity types the E5 read already flagged as the weakest.

### A.2 T under a perfect ASR (70 not-in-supply items)

Each cell is hits / 70 = T, with the Wilson CI95. The Whisper column repeats section 1.

| setting | Whisper large-v3 (section 1) | perfect ASR, primary lexicon | perfect ASR, full-TRAIN lexicon |
| --- | --- | --- | --- |
| **contract: top 3 at the refitted theta** | 6 (primary) / 12 (full) | **10 / 70 = 0.1429 [0.080, 0.243]** (theta 0.45) | **26 / 70 = 0.3714 [0.268, 0.489]** (theta 0.55) |
| contract at the Whisper-fitted theta | same as above | 10 / 70 = 0.1429 (theta 0.50) | 24 / 70 = 0.3429 (theta 0.60) |
| top 1 at theta | 3 / 11 | 6 / 70 = 0.0857 | 23 / 70 = 0.3286 |
| top 3, no threshold | 16 / 24 | 30 / 70 = 0.4286 | 43 / 70 = 0.6143 |
| **no ranker: every span of at most 5 tokens, draft-filtered (perfect ranker)** | 33 / 70 = 0.4714 | **61 / 70 = 0.8714 [0.773, 0.931]** | same |
| no ranker: containment within 5 tokens | 35 / 70 = 0.5000 | 63 / 70 = 0.9000 [0.808, 0.951] | same |

**Where the misses are under a perfect ASR (contract).**

| lexicon | not in the transcript | overlaps the draft | below theta | not in the top 3 |
| --- | ---: | ---: | ---: | ---: |
| primary | 7 | 2 | 51 | 0 |
| full TRAIN | 7 | 2 | 33 | 2 |

With no threshold, the full-TRAIN column loses 18 items that are not ranked into the top 3.

**False candidates also rise.** On the 908 rows with no MISSING item, the non-empty rate is 2.56 % (primary) and
4.39 % (full TRAIN), against 2.30 % and 3.18 % on Whisper.

### A.3 The bound: c <= T × 0.457, against 27 / 80 and 18 / 80

| bound (perfect ASR) | T | c ceiling at CONV uptake 0.457 | items of 80 | reaches 27 / 80 | at or below 18 / 80 |
| --- | ---: | ---: | ---: | --- | --- |
| contract, primary lexicon | 0.1429 | 0.0653 | 5.2 | no | yes |
| contract, full-TRAIN lexicon | 0.3714 | 0.1698 | 13.6 | no | yes |
| contract, full TRAIN at the Whisper theta | 0.3429 | 0.1568 | 12.5 | no | yes |
| top 3 without a threshold, full TRAIN | 0.6143 | 0.2808 | 22.5 | no | no |
| **perfect ranker, draft-filtered** | **0.8714** | **0.3984** | **31.9** | **yes** | no |
| containment within 5 tokens | 0.9000 | 0.4114 | 32.9 | yes | no |

**The thresholds.** Reading (a) needs T >= 0.7383, which is 52 or more of the 70 items. Reading (b)'s ceiling of
18 / 80 corresponds to T <= 0.492. Under a perfect ASR, the contract tool needs an uptake of 2.36 (primary) or 0.91
(full TRAIN) to reach 27 / 80.

### A.4 Verdict for decision 212 (the coordinator's word)

**A stronger ASR is necessary but not sufficient. Under this tool contract there is no path to T >= 0.72 through ASR
alone.**

- **The ceiling moves.** A perfect ASR lifts the perfect-ranker ceiling from 33 / 70 = 0.47 to 61 / 70 = 0.87,
  above the 0.738 bar. The Wilson lower bound is 0.773. So a stronger ASR removes the only absolute barrier that
  section 3 found: 28 of the 35 not-in-Whisper values are ASR misses and are recoverable in principle. Only 7 are
  not verbatim in the reference, and 5 of those 7 are spacing forms.
- **The contract tool does not follow the ceiling.** With the reference as its transcript, the contract tool reaches
  T = 0.14 (primary) or 0.37 (full TRAIN; CI95 upper 0.49). Its c ceiling is 5.2 or 13.6 of 80: under 18 / 80, and
  far under 27 / 80. Reading (b) is still predicted. The binding stage moves from "not in the transcript" to the
  ranker: 33 to 51 eligible golds score below theta, because values the supply did not print are by construction
  far from the TRAIN lexicon.
- **The joint requirement for a path to (a).** A real ASR must recover at least 19 of the 28 (i) items (52 - 33;
  68 %). That assumes a perfect ranker. It must also, together with a ranker, lose at most 9 of the 61 eligible
  values to threshold and ranking, where today's best ranker loses 35 even on perfect text. Even the best no-threshold
  ranker on perfect text reaches only 43 / 70 = 0.61.
- **Recommendation.** Decision 212 should not be taken alone on the strength of this tool. A stronger-ASR pin earns
  its cost only when it is bundled with a ranker redesign, one that is not a nearest-value lexicon match. That
  redesign can be tested offline on the reference transcript before any ASR is pinned or any contact is spent: this
  driver's `--reference-source reference` is the bench, and its gate is contract T >= 0.738 on the 70 items. If no
  ranker clears 0.738 on perfect text, no ASR choice can.
- **Scope.** These are Fold A construction-roster numbers (70 items; decisions 28 and 86). The 5-of-7 spacing
  diagnostic is a character-level check and could over-count by matching inside words.

**Reproduce the addendum.**

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 PYTHONPATH=src python -B scripts/analysis/slurp_s2a1_recall_ceiling.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \
    --reference-source reference
# the same with --check: IDENTICAL apart from generated_at
```

**Outputs.** Under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-S2A1-RECALL-CEILING-V1/perfect-asr-reference/`:
`report.json`, `tables.md` and `content-sha256.json`. The content hashes, with `generated_at` removed:

- `report.json`: `1147911e0436e2ac9435d1f95e912e077d5b851bfd5a13114f9e4cc5c976ef06`
- `tables.md`: `62ab68697f8e6dbbdf3791033a92283115febef9da9ef087884383541156cdeb`

A `--check` re-run reported IDENTICAL apart from `generated_at`. The unit test is
`test_perfect_asr_source_split_and_reference_rows`; the file now has 10 synthetic tests.
