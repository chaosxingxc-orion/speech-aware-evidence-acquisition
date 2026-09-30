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
