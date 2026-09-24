# Inference-time sample aggregation over the sealed ROLL-1 rollout: an offline read (owner decision 112, step 1)

Read 2026-09-24 by the sample-aggregation offline read agent (worktree `/home/chao/saea-worktrees/fable-agg`,
branch `fable/agg`) with `scripts/analysis/slurp_sample_aggregation_offline_read.py`
(sha256 `e81cf5bef3196e2359b1e96378a76468cce0c04997ef00d56ff2b33a08ad7f2e`). Analysis root
`$SPEECHRL_DATA_DIR/analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1`
(`report.json` sha256 `0f8124a769bc206455b1386d3e6eec76115311bfb265b8796604d1266f989304`,
`report.md` sha256 `feb601d420e75aa9048638561e59da4057981acefdd4a27dc39689714e0328e2`).

**Zero model, tokenizer, encoder, ASR, embedder, server, network, GPU and paid-API contacts.** The only
work done outside sealed bytes is seven SCORER-ON-COPIES runs: the rules that EDIT the delivered
answer produce text no sealed scoring covers, so each is rendered into one canonical outputs copy under
the analysis root and scored once through the registered `slurp-slu-official-projected-v3-train`
scorer -- the `stage3_rollout_score.score_copy` / `slurp_verifier_measurement.score_copy` idiom, never
`core.scoring_batch`. No utterance text, transcript, model output text, gold filler or gold annotation is
printed or persisted anywhere in this note or in the read's artefacts: labels, slot TYPE names, ids,
counts, scores and hashes only. TRAIN construction numbers are development numbers (owner decisions 28
and 86) and are never a test claim. This read decides no cell, admits no mechanism and authorises no
flight.

## 0. The question and the answer in one line

Does committing N Solver samples by a deterministic rule beat delivering a single sample, before any GPU
is spent on it? **No rule that delivers one of the N sampled responses verbatim buys anything**
(R1 medoid +0.03 pp pooled SLU-F1 [-0.63, +0.71], R2 intent-plurality medoid -0.04 pp [-0.71, +0.65]).
**Rules that edit the delivered answer do clear a positive lower bound** (support filter at s=3:
+1.40 pp [+0.55, +2.29]; the already-registered plurality-support policy at s=3: +1.62 pp [+0.77, +2.51])
-- but that gain is **not** the gain the operator was proposed for: on the 225 rows where the five
samples actually disagree every rule is nil, and the whole effect is pooled false-positive suppression,
most of it on the 191 rows whose gold answer carries no entity at all. And the winning rule is the one
cell ROLL-1 **already flew**.

## 1. Provenance

| item | value |
| --- | --- |
| rollout | `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` / `attempt-slurp-native-stage3-rollout-r01-generation-v1` |
| roster | `docs/receipts/rosters/slurp-stage3-construction-r01c.json`, 625 rows, sha256 `e8abc65ba4626cccb4aae9d2eb1bd73f077a6e9a407b3dba9c18bbe4c03eeddd`, split identity `f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515` |
| study commit of the seal | `06521be3e4df4378b555f385fd9a30f5341215db` |
| S3-3 deliverables read | `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1` (`render-manifest.json`, the five `sample-<i>-outputs.jsonl` copies re-verified against their manifest sha256, the five `sample_<i>-slurp-slu-official-projected-v3-train-scores.json` files, `per_row.json`) |
| scorer | `slurp-slu-official-projected-v3-train` (official `evaluate.py` at commit `8eb16545762be97ace75334109d73824217311f1`; every side's port/official identity check passed) |
| bootstrap | paired row bootstrap, 10,000 draws, seed 20260915, cluster = row |

**How the five samples were decoded.** `native_episode.roles.solver`: `samples` 5,
`decoding_overrides` `{"temperature": 0.7, "seed_offset": 0}`, `max_iterations` 1. Each sample's seed is
`fragment_seed + seed_offset + sample_index`, so the five seeds on a row are consecutive (first row:
1249110493..1249110497) and **every one of the five is a temperature-0.7 sample -- none of them is
greedy.** The sealed commit policy is `saea-commit-plurality-support-v1` with
`{"min_support": 3, "similarity_threshold": 0.8}`.

**Reconstruction identity.** A rule that delivers one of the five sampled responses verbatim needs no new
scoring: the official SLU-F1 is a micro F1 over the pooled word- and char-distance TP/FP/FN, the official
span-F1 the micro F1 over the exact-match counts, and intent accuracy the mean of `scenario_action_exact`,
all of which the sealed per-row rows already carry. This read proves the identity rather than asserting
it: R1 reconstructed from the sealed counts is 57.90644985971403 and R1 scored as a fresh copy is
57.90644985971403, absolute difference **0.0**.

**I7g reproduction.** Re-running the registered `saea-commit-plurality-support-v1` at `min_support=3`
over each row's own sealed `solver_group` votes reproduces cell ROLL-1's delivered bytes on **625 of 625
rows**, which is the same re-derivation invariant I7g itself performs.

## 2. Every rule on all 625 rows

Deltas are against **R0-mean-single**, the mean of the five single-sample arms. "saves / harms" count rows
whose own per-row SLU-F1 is above / below that mean.

| rule | I7 status | pooled SLU-F1 | span-F1 | intent exact | per-row SLU mean | dSLU | CI95 | saves | harms | ties |
| --- | --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: |
| R0-mean-single | reference | 57.88 | 44.05 | 70.18 | 43.63 | 0.00 | -- | 0 | 0 | 625 |
| R0-sample-0 | verbatim | 58.22 | 44.57 | 70.24 | 44.05 | +0.33 | [-0.49, +1.17] | 110 | 115 | 400 |
| R0-sample-1 | verbatim | 58.12 | 43.84 | 69.92 | 43.43 | +0.24 | [-0.62, +1.10] | 109 | 115 | 401 |
| R0-sample-2 | verbatim | 57.66 | 43.38 | 70.40 | 43.42 | -0.22 | [-1.05, +0.60] | 107 | 117 | 401 |
| R0-sample-3 | verbatim | 58.31 | 45.12 | 70.08 | 44.19 | +0.43 | [-0.72, +1.53] | 121 | 104 | 400 |
| R0-sample-4 | verbatim | 57.11 | 43.38 | 70.24 | 43.04 | -0.77 | [-1.81, +0.25] | 104 | 121 | 400 |
| **R1-medoid** | verbatim | 57.91 | 44.86 | 70.40 | 44.45 | **+0.03** | **[-0.63, +0.71]** | 122 | 102 | 401 |
| **R2-intent-plurality-medoid** | verbatim | 57.84 | 44.75 | 70.56 | 44.24 | **-0.04** | **[-0.71, +0.65]** | 120 | 104 | 401 |
| R3-support-2-of-5 | edited (I7g) | 58.34 | 45.31 | 70.40 | 44.22 | +0.46 | [-0.19, +1.14] | 119 | 105 | 401 |
| **R3-support-3-of-5** | edited (I7g) | 59.28 | 46.43 | 70.40 | 43.37 | **+1.40** | **[+0.55, +2.29]** | 115 | 109 | 401 |
| R3-support-4-of-5 | edited (I7g) | 58.94 | 46.46 | 70.40 | 40.12 | +1.06 | [-0.07, +2.21] | 96 | 131 | 398 |
| PS-registered-support-2 | edited (I7g) | 56.76 | 44.76 | 70.56 | 43.65 | -1.12 | [-1.94, -0.28] | 102 | 126 | 397 |
| **PS-registered-support-3 (as flown)** | edited (I7g) | 59.50 | 46.27 | 70.56 | 43.49 | **+1.62** | **[+0.77, +2.51]** | 114 | 110 | 401 |
| PS-registered-support-4 | edited (I7g) | 59.11 | 46.49 | 70.56 | 40.24 | +1.23 | [+0.09, +2.38] | 97 | 130 | 398 |
| ORACLE best-of-5 | verbatim, **upper bound only** | 64.43 | 53.29 | 71.04 | 49.32 | +6.55 | [+5.56, +7.56] | 225 | 0 | 400 |

`R3-support-s` is the brief's own rule -- take the R1 medoid, then drop its entities whose `(type, filler)`
is supported by fewer than `s` of the five samples (same-type character-level F1 >= 0.8 counts as
support). `PS-registered-support-s` is the REGISTERED `saea-commit-plurality-support-v1` re-applied at
`min_support = s`; it is union-shaped (it emits every same-type cluster with support >= s, including
clusters the medoid never proposed), which is why it is harmful at s=2 while R3 is merely nil there.

`R1` degenerates to "the lowest sample index" on **78 of 625 rows** and `R2` on **82** -- these are rows
where every pairwise SLU-F1 agreement is 0, overwhelmingly rows on which no sample proposes an entity.
`R2`'s intent race is nearly unanimous: the plurality intent has support 5/5 on 576 rows, 4 on 28, 3 on
20 and 2 on 1.

## 3. Disagreeing versus agreeing rows

225 rows have `best_slu_f1 > worst_slu_f1` across the five samples; on the other 400 the five samples
score identically per row (they can still differ in content).

| rule | 225 disagreeing: SLU-F1 (dSLU, CI95) | 400 agreeing: SLU-F1 (dSLU, CI95) |
| --- | --- | --- |
| R0-mean-single | 60.66 (reference) | 54.57 (reference) |
| R1-medoid | 61.77 (+1.11, [-0.04, +2.31]) | 53.35 (-1.21, [-1.77, -0.68]) |
| R2-intent-plurality-medoid | 61.43 (+0.77, [-0.38, +1.98]) | 53.60 (-0.97, [-1.51, -0.44]) |
| R3-support-2-of-5 | 61.57 (+0.91, [-0.21, +2.06]) | 54.48 (-0.09, [-0.66, +0.50]) |
| R3-support-3-of-5 | 61.23 (+0.56, [-0.88, +2.01]) | 57.01 (+2.44, [+1.59, +3.39]) |
| R3-support-4-of-5 | 57.81 (-2.85, [-4.74, -1.09]) | 60.18 (+5.61, [+4.41, +6.96]) |
| PS-registered-support-2 | 60.02 (-0.64, [-1.95, +0.72]) | 52.63 (-1.94, [-2.80, -1.07]) |
| PS-registered-support-3 | 61.50 (+0.84, [-0.55, +2.24]) | 57.15 (+2.58, [+1.69, +3.56]) |
| PS-registered-support-4 | 57.99 (-2.67, [-4.54, -0.92]) | 60.33 (+5.76, [+4.53, +7.14]) |
| ORACLE best-of-5 | 73.21 (+12.55, [+10.99, +14.15]) | 54.67 (+0.10, [-0.45, +0.68]) |

This is the single most important table in the read. **On the rows where the samples disagree -- the rows
the aggregation operator exists for -- not one rule's CI95 excludes zero.** The oracle shows +12.55 pp of
headroom there, and no deterministic agreement signal this read can build reaches any of it. Every
statistically visible gain sits on the *agreeing* rows, where by construction no sample is better than any
other and the only thing a rule can change is how many entities get emitted.

## 4. Per scenario

| scenario | rows | R0-mean | R1-medoid (d) | R2 (d) | R3(s=3) (d) |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | 67.64 | 68.23 (+0.59) | 68.23 (+0.59) | 68.30 (+0.66) |
| audio | 30 | 52.53 | 57.12 (+4.59) | 51.04 (-1.49) | 59.55 (+7.02) |
| calendar | 42 | 58.07 | 59.74 (+1.68) | 59.74 (+1.68) | 61.25 (+3.18) |
| cooking | 31 | 59.58 | 55.93 (-3.65) | 56.65 (-2.93) | 60.55 (+0.97) |
| datetime | 39 | 61.87 | 62.36 (+0.49) | 62.21 (+0.34) | 63.42 (+1.55) |
| email | 33 | 50.11 | 50.65 (+0.54) | 50.46 (+0.35) | 52.77 (+2.66) |
| general | 42 | 12.54 | 12.13 (-0.41) | 12.13 (-0.41) | 14.83 (+2.29) |
| iot | 33 | 63.25 | 63.21 (-0.04) | 63.21 (-0.04) | 63.71 (+0.46) |
| lists | 37 | 46.02 | 44.87 (-1.14) | 44.87 (-1.14) | 44.64 (-1.37) |
| music | 27 | 17.09 | 16.00 (-1.09) | 16.00 (-1.09) | 18.18 (+1.09) |
| news | 36 | 48.01 | 48.54 (+0.53) | 48.54 (+0.53) | 49.89 (+1.88) |
| play | 37 | 52.70 | 53.10 (+0.40) | 52.36 (-0.35) | 53.72 (+1.01) |
| qa | 38 | 49.60 | 46.60 (-3.00) | 47.91 (-1.69) | 54.27 (+4.67) |
| recommendation | 29 | 61.87 | 61.30 (-0.56) | 61.30 (-0.56) | 61.50 (-0.36) |
| social | 35 | 66.80 | 68.39 (+1.59) | 67.77 (+0.98) | 70.34 (+3.54) |
| takeaway | 37 | 62.43 | 62.95 (+0.52) | 63.34 (+0.92) | 63.01 (+0.58) |
| transport | 32 | 71.62 | 72.82 (+1.20) | 72.82 (+1.20) | 71.00 (-0.62) |
| weather | 41 | 64.19 | 62.75 (-1.44) | 62.75 (-1.44) | 63.14 (-1.04) |

R3(s=3) is positive in 14 of 18 scenarios; its two largest scenario gains (`audio` +7.02 on 30 rows,
`qa` +4.67 on 38 rows) and its largest losses (`lists` -1.37, `weather` -1.04) are all single-scenario
cells of 26-42 rows and carry no CI here -- diagnostics, never gates.

## 5. Entity FP / FN mass by slot TYPE

Official FP/FN mass in SLU-F1 units (word- and char-distance blocks pooled), attributed to the slot TYPE
that carries it, through the scorer's own greedy same-type matching and with the same
`saea-slurp-filler-normalization-p2-v1` rule applied to predicted fillers. The 20 heaviest types (of 57
observed) plus the total; the full table is in `report.md`.

| slot type | R0-mean FP | R0-mean FN | R2 FP | R2 FN | R3(s=3) FP | R3(s=3) FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| date | 63.43 | 122.23 | 71.28 | 123.28 | 56.30 | 120.30 |
| place_name | 83.00 | 69.00 | 81.20 | 65.20 | 72.23 | 70.23 |
| event_name | 57.30 | 38.50 | 60.07 | 38.07 | 48.71 | 38.71 |
| person | 62.81 | 28.41 | 65.21 | 25.21 | 49.00 | 29.00 |
| time | 50.70 | 34.70 | 46.06 | 30.06 | 38.06 | 36.06 |
| business_name | 41.49 | 37.49 | 38.23 | 36.23 | 33.91 | 35.91 |
| news_topic | 35.69 | 37.69 | 35.75 | 39.75 | 35.75 | 39.75 |
| food_type | 36.12 | 36.52 | 36.84 | 36.84 | 36.84 | 38.84 |
| list_name | 36.56 | 28.16 | 37.79 | 29.79 | 35.79 | 31.79 |
| media_type | 34.29 | 24.69 | 33.66 | 23.66 | 31.94 | 21.94 |
| weather_descriptor | 26.33 | 29.13 | 28.94 | 30.94 | 26.94 | 30.94 |
| device_type | 38.65 | 9.85 | 43.57 | 9.57 | 31.57 | 11.57 |
| business_type | 21.46 | 24.66 | 18.66 | 24.66 | 18.66 | 24.66 |
| song_name | 36.41 | 6.81 | 36.87 | 6.87 | 27.05 | 7.05 |
| relation | 10.69 | 23.49 | 11.15 | 25.15 | 11.15 | 25.15 |
| order_type | 13.22 | 17.62 | 13.39 | 17.39 | 11.39 | 17.39 |
| house_place | 18.15 | 12.15 | 17.80 | 11.80 | 15.80 | 11.80 |
| time_zone | 18.79 | 11.19 | 18.35 | 10.35 | 15.02 | 11.02 |
| artist_name | 13.58 | 16.38 | 11.90 | 15.90 | 7.90 | 17.90 |
| music_descriptor | 16.84 | 6.44 | 20.37 | 6.37 | 12.37 | 6.37 |
| **TOTAL (all 57 types)** | **889.53** | **687.53** | **919.98** | **677.98** | **745.26** | **697.26** |

R2 is mass-neutral (FP +30.5, FN -9.6): selecting a different sample moves mass around between types
without reducing it. R3(s=3) is a **precision filter**: it removes **144.3 units of FP mass (-16.2 %)**
for **9.7 units of added FN (+1.4 %)**, concentrated in `person` (-13.8 FP), `place_name` (-10.8),
`song_name` (-9.4), `event_name` (-8.6), `device_type` (-7.1), `time` (-12.6) and `date` (-7.1).

## 6. Where the constructed gain actually comes from

Rows split by whether the row's gold answer carries any entity at all, crossed with the
agreeing/disagreeing split. "entities" is the number of entities the delivered answers carry in that cell.

| partition | rows | R0-sample-0 | R1-medoid | R2 | R3(s=3) | PS(s=3) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gold entities, samples disagree | 225 | 61.09 / 404 | 61.77 / 403 | 61.43 / 402 | 61.23 / 357 | 61.50 / 360 |
| gold entities, samples agree | 209 | 65.41 / 306 | 65.05 / 310 | 65.14 / 309 | 65.87 / 301 | 65.87 / 301 |
| no gold entity, samples disagree | 0 | -- | -- | -- | -- | -- |
| no gold entity, samples agree | 191 | 0.00 / 139 | 0.00 / 157 | 0.00 / 154 | 0.00 / 110 | 0.00 / 108 |
| all rows | 625 | 58.22 / 849 | 57.91 / 870 | 57.84 / 865 | 59.28 / 768 | 59.50 / 769 |

**191 of 625 construction rows (30.6 %) have no gold entity at all.** Their per-row SLU-F1 is 0 whatever
is predicted, so nothing a rule does there can move the per-row mean -- but every entity emitted on them
is pure pooled false positive, and pooled micro is the paper-facing number. A single sample emits 139
entities on those rows; the support filter emits 110 and the registered policy 108. That, plus a +0.46 pp
move on the 209 agreeing rows that do carry gold entities, is the entire +1.40/+1.62 pp. On the 225
disagreeing-with-gold rows the support filter throws away 47 of 404 entities (-11.6 %) and buys +0.14 pp.

The operator being evaluated is therefore **not** a "pick the better sample" operator at all. It is an
**entity abstention rule that happens to use sample disagreement as its abstention signal**, and its
measured value lives entirely on rows where no sample was better than any other.

## 7. Cost

| item | value |
| --- | --- |
| ROLL-1 sealed role contacts | 5,344 over 625 rows = **8.5504 / row at N=5** |
| per-stage contacts / row | perception 1.0000, solver 5.4000, review 1.0752, planner 1.0752 |
| non-Solver contacts / row | 3.1504 |
| Solver contacts / row / sample | 1.0800 |
| implied contacts / row at N | 3.1504 + N x 1.0800 |
| N=1 | 4.2304 (the locked v2.0 PLAN reads 4.1 -- a 3 % agreement, which is the sanity check on this decomposition) |
| N=3 | 6.3904 -- **1.56x** the plan |
| N=5 | 8.5504 -- **2.09x** the plan |

The Solver sample count is the only lever: the Perception, Reviewer and Planner visits are unchanged by N.
At the best I7g-admissible rule (s=3) the trade is **+1.62 pp pooled SLU-F1 for 2.09x the contacts**, or
**+1.40 pp for the brief's own R3 rule**, against a SLURP own-null half-width of about 1.25 pp
(`h_SLU` 1.2485 on DEV-1000, 1.2525 on DEV-2000-ADDED; R01C has no own null of its own yet).

## 8. I7, and a correction to the brief's premise

The brief asked me to say that R3 violates invariant I7 ("the delivered text must be a model response")
unless the harness gains a deterministic post-commit projection node. **That is not the state of this
harness, and the correction matters for what should be built.**

* `core/bundle/outputs.py` already carries **I7g** (E2d, 2026-09-17), written for exactly this shape: "the
  delivered text is a deterministic function of the N raw response texts and equals none of them in
  general, which I7's 'the delivered text IS one model response's bytes' reading cannot express". A row
  with a `solver_group` receipt is held to I7g instead -- *strictly stronger* custody, not a relaxation:
  every raw sample's own response bytes must be in the trace under that sample's contact id, the commit
  policy must resolve in `core.base.COMMIT_POLICIES` and be deterministic, and re-running it over the
  row's recorded samples must reproduce the delivered bytes exactly.
* Cell ROLL-1 already flew such a policy. This read re-derived its delivered bytes on **625 of 625 rows**.
* The projection-node route is in fact **closed** for a grouped arm: I7n explicitly refuses a row that
  carries both a `solver_group` receipt and a `deliver_normaliser` block, and
  `rails.native_episode_config` refuses the combination before any contact.

So: R0, R1, R2 and the oracle satisfy I7 outright (they deliver one sampled response byte for byte).
R3 and every PS variant do not, and do not need to -- what they need is **registration as a
`core.base.COMMIT_POLICIES` entry with its `commit_params` recorded on every row**, the precedent being
`saea-commit-plurality-support-v1` itself. No new invariant, no new node, no projection node. What a
delivery-normaliser node (I7n) *would* be needed for is the N=1 variant of the same idea -- see the
recommendation.

## 9. Recommendation

**No I7-compatible rule clears +1.5 pp SLU with a CI95 lower bound above zero on these construction rows,
and neither comes close:** R1 medoid is +0.03 pp [-0.63, +0.71] and R2 intent-plurality medoid is
-0.04 pp [-0.71, +0.65] -- both nil, both with intervals that comfortably contain zero, and both
degenerate to "lowest sample index" on 12-13 % of rows because entity-level agreement carries no signal
where no sample proposes an entity. Agreement-based *selection* is worth nothing here; the oracle's
+6.55 pp [+5.56, +7.56] confirms the headroom is real and that nothing deterministic in this read reaches
it. The only rules that clear a positive lower bound are the ones that edit the answer -- R3 at s=3
(+1.40 pp [+0.55, +2.29]) and the registered plurality-support policy at s=3 (+1.62 pp [+0.77, +2.51]) --
and contrary to the brief's premise these need no projection node, only registration in
`core.base.COMMIT_POLICIES` under the existing I7g custody, which the flown policy already has. **But I
recommend against spending GPU on a sample-aggregation cell as framed**, for three reasons that the
tables above make concrete: (a) the winning rule at s=3 *is already what ROLL-1 flew*, so there is no new
mechanism to buy -- only a measurement of what the grouped Solver already bought, at 2.09x the locked
plan's contacts for a gain whose point estimate barely exceeds the study's own ~1.25 pp null half-width;
(b) on the 225 rows where the samples disagree -- the rows the operator was proposed for -- every rule is
nil, so the mechanism is not doing what it was hypothesised to do; and (c) the effect that does exist is
pure pooled false-positive suppression (FP mass -16.2 % for FN +1.4 %), 30.6 % of the rows carrying it
have no gold entity at all, and it is bracketed on both sides (s=2 is harmful, -1.12 pp [-1.94, -0.28];
s=4 over-prunes the disagreeing rows, -2.85 pp [-4.74, -1.09]). The cheaper experiment the data points to
is therefore the **N=1** form of the same idea: an entity-abstention rule at the delivery node --
a registered `core.base.DELIVERY_NORMALISERS` entry under I7n, 1x contacts, no grouped Solver -- aimed at
the same false-positive mass on rows the system should have answered with no entity. If, after that, an
N>1 arm is still wanted, the only admissible form on this evidence is a registered commit policy at
exactly s=3, pre-registered against the disagreeing-row subset (where it must stop being nil for the
mechanism claim to hold) rather than against the pooled number alone.

## 10. Reproduction

```bash
cd /home/chao/saea-worktrees/fable-agg
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD:$PWD/src"
nice -n 10 /home/chao/.venvs/speechrl/bin/python \
  scripts/analysis/slurp_sample_aggregation_offline_read.py \
  --rollout-score-root "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1" \
  --analysis-root "$SPEECHRL_DATA_DIR/analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1"
```

Deterministic and re-runnable from the sealed bytes: every scored copy is cached by its own result file,
so a second invocation reports `{"scorer": 0, "scorer_copies": 7, "scorer_reused_from_cache": 7}` and
reproduces `report.md` byte for byte. Nothing is written into any sealed run directory.
