# SLURP Perception boundary block: a new retrieval key for off-block intent recall (DESCRIPTIVE, offline)

Date: 2026-09-30. Read id `SAEA-SLURP-RETRIEVAL-KEY-RECALL-OFFLINE-V1`, recipe
`slurp-retrieval-key-recall-offline-v1`. Written by Claude Opus 5.5 (analysis agent, coordinator's brief, Fable 5.1)
in worktree `fable/recallkey` (base master `561d5395c`).

**Status: DESCRIPTIVE.** Development numbers on TRAIN Fold A and TRAIN Fold B, both construction rosters (owner
decisions 28 and 86). No test, generalisation or superiority claim. The verdict word belongs to the coordinator
(decision 139).

**Contacts: zero of every kind.** No model, server, tokenizer, encoder, embedder, GPU, network or paid-API contact;
no official-scorer subprocess (per-row official scores come from sealed score files); `core.flight.cli` and
`lease_cli` were not invoked. Every key below is arithmetic over already-pinned vectors and tables.

- **Gold** entered only through the governed TRAIN loader `data.slurp.load_slurp_split`, only to score recall on
  the two read rosters. It never entered key construction.
- **Construction labels** are each pool value's frozen build-time `task_target` (a released-store property).
- **Never printed or persisted:** utterance text, transcripts, slot fillers, note text, model output. Per-row
  records in `report.json` carry sample ids, ranks, cosines and class flags only; intent labels appear only as
  aggregate counts of the closed label set.

**Driver and outputs.**

- Driver `scripts/analysis/slurp_retrieval_key_recall.py`, sha256
  `f797793280abc3209decfdc4225120b12901ff8d04aa87270df513c1aa84af56`; unit test on fakes
  `tests/unit/test_slurp_retrieval_key_recall.py` (11 passed).
- Machine outputs `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-RETRIEVAL-KEY-RECALL-OFFLINE-V1/` (`report.json`,
  `tables.md`, `content-sha256.json`). `--check` re-derived both IDENTICAL apart from `generated_at`. Content
  hashes (without `generated_at`): `report.json` `67270fe34aee1d166010da4e40bb81eeef75e53af075eb82d5a38aea46c8359c`,
  `tables.md` `e5ee48b5271a38318af2204f65bb71edc07be24eede34bde07a0f798743119f6`.
- Wall time about 2 min per run, peak memory 0.82 GB. Every number below is from `report.json`; the key is named in
  brackets.

## Two corrections to the brief's premises

1. **The 1,040 / 34 figures belong to the description + agreement key, not the centroid + agreement key.** On Fold
   A, `desc_agree` (AGREE, and the key every P-SV cell flew) puts gold in the depth-8 block on 1,040 / 1,080 rows,
   and 34 AGREE intent-wrong rows have gold off the note and off the block. The confirmed boundary key
   `cent_agree` (COMP-1b) already reaches **1,048 / 1,080** on Fold A and **1,027 / 1,080** on Fold B
   [`comparison.<fold>.cent_agree.cent_agree.gold_in_block`]. This note measures every candidate against
   `cent_agree` and also reports it against `desc_agree`. The 34 (Fold A) and 54 (Fold B) diagnostic sets are kept
   exactly as defined in the block-depth read, and are reproduced as 34 and 90 → 54 [`target_reproduction`].
2. **The space is not LCO-Embedding-Omni.** The boundary query is the row's sealed full-utterance speech vector; the
   construction pool vectors are Omni-Embed-Nemotron-3B embeddings of the 11,514 governed TRAIN utterance texts
   (`vectors/slurp-kus3/facet-vectors.jsonl`, ledger row `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1`, per the Fold B
   agreement receipt). The centroid key is the unit mean of those text vectors, compared against the speech query.

**What this implies for the target.** The on-list gap has two parts. Under `cent_agree` on Fold A, gold is on the
Perception note on 1,004 / 1,080 rows [`implied_note_base`]; of the 76 rows without it, 32 are off the block (the
note keeps 3.1 % of off-block gold) and about 44 are in the block but not kept. **Any block key can therefore add at
most 32 rows (+2.96 pp) of block presence on Fold A and 53 rows (+4.91 pp) on Fold B.** A +4-5 pp gain in on-list
recall cannot come from block presence alone on Fold A.

## 1. Inventory of the pinned material (task 1)

| material | path (under `$SPEECHRL_DATA_DIR` unless marked repo) | sha256 | pure function of pinned bytes? |
| --- | --- | --- | --- |
| Fold A speech query, `intent-boundary` dimension (1 segment per row on 1,080 / 1,080) | `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl` | `e7a5b226...` | pinned input |
| Fold B speech query (1 segment on 1,080 / 1,080) | `vectors/slurp-intent-boundaries-train-fold-b-1080-v1/query-vectors-speech-segments.jsonl` | `83c5da61...` | pinned input |
| R01C construction-roster speech query (625 rows; hub statistics for K6-K8 only) | `vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl` | `ebaa7432...` | pinned input |
| construction pool vectors (`content` dimension, one per TRAIN utterance) | `vectors/slurp-kus3/facet-vectors.jsonl` | `5dfe7523...` | pinned input |
| construction pool membership and labels (R01-excluded, 8,554 utterances) | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json` | content `6eaa03ae...` | pinned input |
| description key (flown) | `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl` | `76e8d16a...` | pinned input |
| centroid key | `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl` | `16c33640...` | yes: recomputed here from the pool, max abs diff 2.8e-17 |
| agreement table, Fold A (top-20 exemplar share, Solver content query, full 9,354 pool, self-excluded) | `prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl` | `018ca6ef...` | pinned (built model-free by `scripts/build_slurp_intent_exemplar_agreement.py`) |
| agreement table, Fold B | `prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/agreement.jsonl` | `06990a86...` | pinned (same builder) |
| boundary store (60 facets, 1:1 values) | `knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json` | `5520b844...` | unchanged by every key here |

**How the flown key combines them** (repo `src/speech_aware_evidence_acquisition/rails/`):

- `kb_policy.multidim_segment_recall` recalls a facet only at a **positive** cosine, per segment, top `k` 60 (all 60
  facets).
- `knowledge_provider.KbFacetProvider._merge_agreement` adds the row's agreement share to recalled facets only.
- `kb_policy._rank_weighted_cosine_prior_agreement` scores `w_cos * max_cosine + w_prior * max_prior + w_agree *
  share`, with rank weights 1 / 0 / 1, ties by facet id.
- `kb_policy.fuse_associated_values_factory` (`saea-fuse-associated-values-v1`, m / c / top_l 8 / 1 / 8, tau 0)
  delivers the first 8 ranked facets' values.

This arithmetic was re-implemented in numpy and reproduces the sealed blocks exactly
[`checks`]: `desc_agree` = sealed AGREE block 1,080 / 1,080; `cent_agree` = sealed COMP-1b block 1,080 / 1,080;
`desc_agree` on Fold B = P-SV-1 and P-SV-3 `a-agree` supply 1,080 / 1,080 each.

**Construction pool used for every new key:** the R01-excluded snapshot minus every utterance of TRAIN Fold A
(`docs/receipts/rosters/slurp-evo-fold-a-v2.json`, sha256 `1fe7908c...`), TRAIN Fold B
(`slurp-evo-fold-b-v2.json`, `47b89b9e...`), R01 (`slurp-stage3-construction-r01.json`, `fdb6521a...`) and R01C
(`slurp-stage3-construction-r01c.json`, `e8abc65b...`). The explicit exclusion removed **0** utterances from each
roster, so the pool is the pinned 8,554 [`construction_pool`]. One intent (`cooking_query`) has no member and keeps
its written key under every construction, as in the pinned centroid file; the smallest intent has 6 members. The
R01C statistics queries share 0 utterances with Fold A, Fold B and the pool [`hub_statistics.overlap`].

## 2. Diagnosis of the 34 + 54 off-block rows (task 2)

Per-row records (sample id, half, gold and top-1 centroid cosine, gold's rank under eight keys, rival's centroid
cosine to gold and its rank among gold's centroid neighbours, class) are in `taxonomy.<fold>.per_row`.

**Miss taxonomy** (exclusive, applied in the brief's order) [`taxonomy.<fold>.classes`, `by_class`]:

| class | rule | Fold A (34) | of them `general_quirky` | Fold B (54) | of them `general_quirky` |
| --- | --- | ---: | ---: | ---: | ---: |
| (a) catch-all, far from every centroid | gold is `general_*` / `qa_*` and the row's best centroid cosine is in the fold's bottom quartile (< 0.2446 A, < 0.2440 B) | 5 | 4 | 5 | 4 |
| (b) sibling confusion | the flown key's top-1 shares gold's scenario | 1 | 1 | 1 | 0 |
| (c) multi-modal intent | gold's nearest construction utterance (`nn1`) ranks it in the top 8 while its centroid does not | 5 | 1 | 12 | 6 |
| (d) other | none of the above | **23** | 2 | **36** | 1 |

Non-exclusive flags [`taxonomy.<fold>.flags`]:

| flag | Fold A (34) | Fold B (54) |
| --- | ---: | ---: |
| gold is a catch-all (`general_*`, `qa_*`) | 10 | 16 |
| gold is `general_quirky` | 8 | 11 |
| rival (flown top-1) shares gold's scenario | **1** | **1** |
| rival is gold's nearest centroid / in gold's top-3 centroid neighbours | 2 / 6 | 3 / 8 |
| gold in the top 8 under `cent_agree` | 8 | 11 |
| gold in the top 8 under `nn1` | 13 | 22 |

Geometry of the misses:

- **The gap is small and the rival is not a sibling.** The median gap from the row's top centroid cosine to gold's
  is 0.026 (A) and 0.025 (B). The rival's centroid sits at median rank 25.5 (A) and 20 (B) among gold's 59
  neighbours, at a centroid cosine of 0.965 to gold's. Fine-grained sibling confusion (`iot_hue_*`, `alarm_*`) is
  almost absent: 1 row per fold.
- **The rivals are spread out, with one hub.** 19 distinct rivals on A (`calendar_set` 8, `news_query` 4) and 34 on
  B (largest 4) [`rival_intent_counts_top`].
- **The row is simply less similar to everything.** Median top-1 centroid cosine is 0.261 (A) and 0.281 (B) on the
  misses, against a fold median of 0.289 and 0.291.
- **Per-key ranks of gold on the 34 / 54** (top 8 / 9-20 / 21+ / not recalled):
  - `cent_agree`: 8 / 16 / 9 / 1 on A and 11 / 20 / 23 / 0 on B.
  - `nn1`: 13 / 16 / 5 / 0 and 22 / 16 / 16 / 0.
  - K1 (P = 3): 9 / 9 / 15 / 1 and 14 / 21 / 19 / 0.
  - K2 (m 20): 9 / 14 / 10 / 1 and 13 / 20 / 21 / 0.

**Reading.** The dominant class (d, 23 / 34 and 36 / 54) is not a catch-all, not a sibling and not reached by the
nearest exemplar. Gold is 0.02-0.03 cosine behind a cross-scenario rival in a key space where every centroid pair
sits at about 0.93-0.97 cosine. Class (c) is where exemplar-level keys help, and it is concentrated on Fold B (12).
`general_quirky` spreads across (a) and (c).

## 3. Candidate keys (task 3)

All keys are pure functions of the pinned inputs. Tuned parameters are cross-fitted by sha256(utterance id) halves
(Fold A 541 / 539, Fold B 533 / 547): chosen on one half by in-half implied note presence, applied to the other
[`crossfit_choices`]. Keys K6-K8 draw their statistics from the R01C speech queries, never from a read roster.

**Implied effects** use the measured sealed conversion by gold's block rank, P(note | r) and P(delivered intent
correct | r), r = 1..8 or off [`p_note_given_sealed_block_rank`, `p_intent_correct_given_sealed_block_rank`]:

- Fold A uses COMP-1b's tables: note 99.8 / 93.9 / 82.1 / 57.9 % at r 1-4, 3.1 % off; intent 98.3 / 62.6 / 48.7 /
  42.1 %, 3.1 % off.
- Fold B uses P-SV-1 `a-agree`'s tables.
- Applying a table to its own run's ranks reproduces the sealed count exactly.

**Key comparison against `cent_agree`** (depth-8 block; "leaves ok" = rows delivered correct today whose gold leaves
the block; "tgt" = the 34 / 54 recovered into the top 8; rank-1 = rows with gold at block rank 1, `cent_agree` has
823 on A and 789 on B; implied deltas in rows) [`comparison.<fold>.cent_agree.<key>`]:

| key | A in block (net) | A leaves ok | A tgt | A rank-1 | A note / intent Δ | B in block (net) | B leaves ok | B tgt | B rank-1 | B note / intent Δ |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | --- |
| `cent_agree` (baseline) | 1,048 | 0 | 8/34 | 823 | 0 / 0 | 1,027 | 0 | 11/54 | 789 | 0 / 0 |
| `desc_agree` (flown in AGREE, P-SV) | 1,040 (−8) | 6 | 0 | 831 | −4.3 / +2.1 | 1,015 (−12) | 5 | 0 | 800 | −7.9 / +1.9 |
| K1 P = 2 / 3 / 4, + agreement | 1,046-1,047 (−2..−1) | 0 | 7-8 | 823-827 | −2.7..−0.6 / −0.6..+1.6 | 1,023-1,025 (−4..−2) | 0-1 | 11-13 | 787 | −1.0..+0.6 / −0.2..+1.2 |
| K1* (P cross-fitted) | 1,047 (−1) | 0 | 9 | 827 | −1.5 / +0.7 | 1,025 (−2) | 0 | 13 | 787 | +0.6 / +1.0 |
| K2 m 10 / 20 / 40, cent + kNN share (no pinned agreement) | 1,038-1,045 (−10..−3) | 2-4 | 9-13 | 775-819 | −12.5..−6.7 / −23.6..−7.5 | 1,022-1,027 (−5..0) | 1-3 | 13-15 | 745-790 | −12.3..−5.4 / −23.1..−3.0 |
| K2*_cent (m, weighting cross-fitted) | 1,042 (−6) | 2 | 9 | 808 | −5.4 / −8.9 | 1,027 (0) | 1 | 15 | 799 | −4.9 / −0.0 |
| K2 m 20, cent + agreement + kNN share | 1,046 (−2) | 0 | 9 | 815 | −2.6 / −5.4 | 1,026 (−1) | 1 | 13 | 792 | −3.7 / −2.4 |
| K2*_cent_agree (m, weighting, share weight cross-fitted) | 1,048 (0) | 1 | 9 | 825 | +0.6 / +1.3 | 1,025 (−2) | 0 | 11 | 794 | −2.9 / −1.2 |
| `nn1` + agreement (nearest construction utterance) | 1,046 (−2) | 3 | 13 | 829 | −1.6 / +1.8 | 1,031 (+4) | 0 | 17 | 796 | +3.6 / +6.8 |
| K3* catch-all floor, `general_quirky` | 1,048 (0) | 0 | 8 | 823 | 0 / 0 | 1,031 (+4) | 0 | 14 | 789 | +2.0 / +1.5 |
| K3* catch-all floor, `general_quirky` + `qa_factoid` | 1,049 (+1) | 0 | 9 | 823 | +0.6 / 0.0 | 1,031 (+4) | 1 | 15 | 789 | +1.7 / +0.9 |
| K4* soft scenario prior (λ cross-fitted) | 1,044 (−4) | 1 | 6 | 823 | −2.2 / −1.4 | 1,026 (−1) | 1 | 11 | 790 | +0.4 / +0.9 |
| K4* hard scenario-first (s cross-fitted) | 1,011 (−37) | 18 | 5 | 811 | −25.5 / −17.9 | 998 (−29) | 14 | 13 | 785 | −18.5 / −10.1 |
| K5 RRF `cent_agree` + K1 P 3 + agreement | 1,046 (−2) | 0 | 8 | 827 | −0.6 / +0.9 | 1,026 (−1) | 0 | 11 | 788 | +1.3 / +2.1 |
| K5 RRF `cent_agree` + K2 m 20 | 1,045 (−3) | 0 | 9 | 816 | −1.7 / −3.6 | 1,027 (0) | 0 | 11 | 784 | −3.1 / −4.0 |
| K5 RRF `cent_agree` + `nn1` | 1,043 (−5) | 2 | 9 | 820 | −3.3 / −5.2 | 1,026 (−1) | 0 | 14 | 794 | −2.2 / +0.7 |
| K5 RRF `cent_agree` + `nn1` + K1 P 3 | 1,037 (−11) | 1 | 6 | 819 | −6.1 / −5.0 | 1,030 (+3) | 0 | 16 | 794 | −4.0 / −1.1 |
| K6 centred cosine, no agreement | 1,030 (−18) | 3 | 8 | 849 | −14.2 / −0.6 | 1,018 (−9) | 4 | 15 | 827 | −10.3 / +7.9 |
| K6 centred cosine + agreement (w 1), idealised admission | 1,039 (−9) | 2 | 6 | 844 | +1.8 / +11.1 | 1,028 (+1) | 0 | 15 | 814 | +2.6 / +10.8 |
| **K6p centred cosine + agreement (w 1), production admission** | 1,040 (−8) | 2 | 7 | **845** | +2.4 / **+11.5** | 1,029 (+2) | 0 | 15 | **815** | +3.3 / **+11.6** |
| K6p* (w cross-fitted) | 1,041 (−7) | 2 | 8 | 839 | +2.3 / +8.5 | 1,028 (+1) | 0 | 14 | 823 | +2.3 / +12.2 |
| K6 + K3* floor (`general_quirky` + `qa_factoid`) | 1,038 (−10) | 2 | 5 | 844 | +1.4 / +11.0 | 1,032 (+5) | 0 | 18 | 814 | +4.5 / +12.0 |
| K7* CSLS hub penalty + agreement | 1,046 (−2) | 1 | 8 | 827 | +2.0 / +3.9 | 1,028 (+1) | 0 | 13 | 791 | +2.0 / +3.6 |
| K8 per-key bias removal + agreement | 1,042 (−6) | 1 | 7 | 823 | −1.0 / −0.1 | 1,026 (−1) | 0 | 11 | 790 | +1.2 / +2.7 |
| K8* per-key z-score + agreement (w cross-fitted) | 1,043 (−5) | 1 | 7 | 829 | −0.7 / +3.0 | 1,027 (0) | 0 | 11 | 790 | +2.7 / +4.3 |

Key definitions:

- **K1:** per-intent spherical k-means over the intent's construction vectors (deterministic k-means++ seeded by the
  intent id; 119 / 178 / 237 prototypes at P 2 / 3 / 4); score = max prototype cosine.
- **K2:** the share of the row's top-m construction utterances by speech-query cosine, count or cosine weighted.
- **K3:** when the row's best centroid cosine is below a cross-fitted quantile, the catch-all enters block slot 8.
- **K4:** the scenario centroid is the unit mean of the scenario's construction vectors.
- **K5:** reciprocal-rank fusion with c = 60.
- **K6:** cosine between (query − mean R01C speech query) and (intent mean − pool mean). "Idealised" ranks all
  facets with a positive raw cosine. "Production" (K6p) admits only facets with a positive centred cosine, which is
  what the flown recall would do with centred vectors. It admits 25.7 (A) / 25.5 (B) facets per row, never fewer
  than 8, and leaves gold unrecalled on 11 / 16 rows, all of them off-block anyway [`k6p_admission`].
- **K7:** CSLS, 2·cos − mean cosine of the key to its 10 or 50 nearest R01C queries.
- **K8:** subtracts each key's mean R01C cosine (and divides by its standard deviation, rescaled to the mean spread).

**Against `desc_agree`** (the key the P-SV cells flew), every positive result above grows by `cent_agree`'s own +8
(A) / +12 (B) [`comparison.<fold>.desc_agree`]. For example K6p (w 1) is 0 / +14 net, and K3* (`general_quirky` +
`qa_factoid`) is +10 / +16.

**Both halves** [`by_half`]:

- **K6p (w 1), net / implied note / implied intent:**
  - A: −2 / +1.9 / +6.2 and −6 / +0.5 / +5.3.
  - B: +1 / +1.5 / +6.6 and +1 / +1.8 / +5.0.
  - Gold moves to rank 1 on 25 (A) and 27 (B) rows, and leaves rank 1 on 3 (A, all delivered correct) and 1 (B).
- **K3* (`general_quirky` + `qa_factoid`), net:** 0 / +1 (A), +2 / +2 (B).

What the table shows:

- **No key reaches +4 pp presence.** The best presence gain over `cent_agree` on both folds is +1 / +4 rows (K3*
  with `general_quirky` + `qa_factoid`; +0.1 / +0.4 pp). K6 + K3* reaches +5 on B but −10 on A. `nn1` + agreement
  gives −2 / +4. The upper bound is +32 / +53 rows.
- **Exemplar-level keys (K1, K2, `nn1`, K5) reach more of the targets but displace more.** For example, `nn1` puts
  13 / 34 and 22 / 54 into the top 8, against 8 and 11. They also push gold down on rows it already wins (rank-1
  drops to 775-819 on A for K2). On both folds none is net positive in presence and in implied intent.
- **The catch-all floor is safe and small.** It displaces no delivered-correct row on A and at most 1 on B, and
  recovers 1-4 rows. The general_quirky rows it cannot reach are the (c) and (d) rows with a normal top cosine.
- **Scenario-first is harmful.** The hard variant loses 37 / 29 rows, because the misses are cross-scenario.
- **Centring the space is the one key that changes rank quality.**
  - K6p lifts gold to block rank 1 on +22 (A) / +26 (B) net rows, with mean in-block rank 1.426 → 1.404 (A) and
    1.428 → 1.398 (B).
  - At the measured rank conversions this is +11.5 / +11.6 implied intent rows (+1.06 / +1.07 pp), consistent in
    all four halves (+5.0 to +6.6 each).
  - Its presence cost is −8 rows on A (2 delivered correct) and +2 on B. Its implied on-note gain is only +2.4 /
    +3.3 rows (+0.2 / +0.3 pp).

## 4. Recommendation

- **Plain statement.** No key built from the pinned vectors reaches +4 pp presence, or +4 pp on-list recall, on
  either fold. Block presence is capped at +2.96 pp on Fold A by construction (32 off-block rows under `cent_agree`),
  and the best measured gain is +0.1 / +0.4 pp. About 58 % of Fold A's off-note rows (44 of 76) are in the block and
  not kept by the note, which is a Perception-note lever, not a key lever.
- **Single best key: K6p, the centred centroid + agreement key.** Settings: w_cos / w_agree 1 / 1 as flown; no
  tuned parameter beyond the flown weights; centring statistics from the pinned R01C speech queries.
  - Predicted presence: 1,040 / 1,080 on A (−0.7 pp vs `cent_agree`) and 1,029 / 1,080 on B (+0.2 pp).
  - Predicted intent at the measured conversions: +11.5 / +11.6 rows, about **+1.1 pp on both folds**. This is an
    analogue: rows lifted to rank 1 are assumed to convert like today's rank-1 rows.
  - It is a rank-quality lever. It is not the on-list lever the brief asked for.
- **Cost.** Nothing is re-encoded and no store release is needed: the snapshot and delivered bodies are unchanged,
  as in COMP-1b. Two new `prepared/` artifacts are needed, both arithmetic over pinned vectors at zero encoder
  contacts:
  - a 60-row centred key file (a `facet_source`, the centroid-key receipt kind);
  - a centred query-vector file per flown roster (a `query_source`), with the R01C mean pinned in its receipt.

  Because the production recall admits only positive cosines, the K6p column (not K6) is the one that transfers
  unchanged through `load_sealed_vectors` / `load_sealed_segment_vectors`.
- **Read design.** The Perception-branch schema (`rails/supply_variants.py` `PERCEPTION_BRANCH_KNOB_TAILS`,
  `PERCEPTION_BRANCH_OPTIONAL_KEYS`) admits only these axes:
  - knobs `k`, `fuse_coverage.m|c|top_l` and `rank_weights.w_cos|w_prior|w_agree`;
  - `release_swap` (release + snapshot only, per `rails/knowledge_stores.py` `_ALTERNATE_KEYS`);
  - `presentation_id`, `min_candidates`, `prepared_seed`.

  There is no `key_source` axis that swaps `facet_source`, `query_source` or `agreement_source`. A same-flight K6p
  column therefore needs either a new branch axis (a `key_source` pin swap on the first phase's `phase_supply`, with
  a parser refusal list and tests), or a paired cell. A paired cell is a cross-flight contrast and needs an in-chain
  A/A replicate under `stage3_effect_floor_check.py`.
  - The predicted +1.1 pp intent sits at about the twin bar the block-depth read quotes (about 1.0 pp).
  - The effect is carried by rank-1 conversion, so a level-1 (note-only) branch would not show it. The column must
    be level 2 (Solver column).

## What this note does not claim

- It does not claim that any key raises intent. The implied intent and note deltas apply today's sealed
  rank-conditional conversions (COMP-1b on A, P-SV-1 `a-agree` on B) to new ranks. Rows a new key lifts may be harder
  than today's rows at the same rank. For `cent_agree` on B, the conversion table is P-SV-1's (description key).
- It does not claim that the 34 / 54 rows are unreachable. `nn1` puts 13 / 34 and 22 / 54 in the top 8, but no rule
  tried here selects those rows without displacing others.
- It does not test keys that need new encoder contacts: re-encoded descriptions, speech-side pool vectors, or
  multi-segment queries.
- K6 / K6p use R01C speech queries for the query mean, a construction roster pinned and disjoint from both folds.
  A production artifact would pin the same mean. No read-roster statistic enters any key.
- Cross-fit halves are the only guard on the tuned families (K1*, K2*, K3*, K4*, K6*, K6p*, K7*, K8*, K6 + K3*).
  In-sample per-parameter results are in `report.json` and are selected numbers.
- The taxonomy thresholds (bottom-quartile top cosine; `nn1` top 8 vs centroid off top 8) are definitions of this
  read, not measured boundaries.
- Every number is a TRAIN development number. Nothing is nominated or admitted.

## Recommendation to the coordinator

1. **Close "a new key for +4-5 pp on-list recall" as unreachable from pinned vectors.**
   - Block presence is capped at +2.96 pp on Fold A by construction.
   - Every key family tried (K1-K8) gains at most +0.1 / +0.4 pp over `cent_agree`.
   - The larger off-note mass on Fold A (44 of 76 rows) is in the block and not kept by the note.
   - Decision needed: re-point the first blank of the 95 % ceiling from "retrieval key" to "Perception keep rate
     given block rank 2-8". Record the block ceiling (+32 / +53 rows) beside the ceiling note.
2. **Register K6p (centred centroid + agreement) as a rank-quality candidate, not a recall candidate.**
   - Predicted about +1.1 pp intent on both folds and in all four halves, at a −0.7 / +0.2 pp presence cost.
   - Cost: two zero-contact `prepared/` artifacts and no store release.
   - Decision needed: authorise (a) building the centred key and centred query files with receipts, and (b) either
     a `key_source` Perception-branch axis (code, parser and tests) for a level-2 same-flight column, or a paired
     cell with an A/A replicate. Read the result against the twin bar of about 1.0 pp, knowing it is near the floor.
3. **Optionally adopt the catch-all floor (K3*, `general_quirky` + `qa_factoid`) as a zero-risk add-on only if a
   `cent_agree` Perception list is re-flown.**
   - +1 / +4 rows, 0 / 1 delivered-correct rows displaced.
   - It needs a ranker or fuser rule (a new registered policy), not a pinned file.
   - Decision needed: whether a +0.1-0.4 pp presence rule justifies a new registered policy. The recommendation is
     no on its own merits; it would ride only with item 2.

## Method and reproduce

- Rank arithmetic is `w_cos * cos + w_agree * share` over facets with a positive cosine, ties by facet id; the block
  is the first 8. It is verified against the four sealed blocks (section 1).
- Halves: `int(sha256(utterance_id), 16) % 2`, as in the supply-abstention and block-depth reads.
- "Leaves ok" uses the official `scenario_action_exact` per row of COMP-1b (A, vs `cent_agree`), AGREE (A, vs
  `desc_agree`) and P-SV-1 `a-agree` (B).
- Inputs with full hashes are in `report.json` `inputs`.

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_retrieval_key_recall.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_retrieval_key_recall.py --check \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```
