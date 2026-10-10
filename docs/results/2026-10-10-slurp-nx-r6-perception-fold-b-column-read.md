# NX round R6-P1 (Perception entity template column, TRAIN Fold B): every arm NOT NOMINATED; p1's presence tag is an additional but weak message element (E=none precision 0.57 / recall 0.60, cross-fit AUC increment +0.022 [+0.010, +0.033], declared gate +0.44 [-0.29, +1.17]); p2 / p3 are form failures of the 128-character mention channel; the twin reads +0.72 [+0.12, +1.37]

Read 2026-10-10 by Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/nx-r6-results` (base master `973380f6f`). Model-free: this note opened no model, server, encoder, embedder,
tokenizer or GPU, ran no scorer, and wrote nothing under the data root. It reads the on-file outputs of the registered
read `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-COLUMN-READ-V1`, the information-gain read
`SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1`, and the sealed run's manifests. No utterance text, transcript, gold value, slot
filler, note body, mention text, tag string or model output was printed or persisted. Only counts, rates, deltas,
slot-type and scenario labels, ids and hashes appear below.

**DESCRIPTIVE.** These are development numbers on a TRAIN construction fold (owner decisions 28 and 86). Fold B is this
design's selection roster, and the candidates and the N1 >= 0.2 gate were authored from aggregate tables computed on it
(package README section 3, tuning disclosure). Nothing here is a test claim, a system-level claim or an admission. The
cell is a measurement cell (`claims_benefit` false, claim ceiling `nominated`). The verdict words in section 8 apply the
registered rules and are proposed to the coordinator.

## 0. Answer in eight lines

1. No arm is NOMINATED. Official pooled SLU-F1 vs `lock` (64.34 %): `aa` twin **+0.72 [+0.12, +1.37]**, `p1` +0.51 [-1.07, +2.08], `p2` -0.70 [-2.47, +1.13], `p3` -1.41 [-3.13, +0.35]. None is HARM on pooled SLU-F1. `p3`'s pooled span-F1 is -3.21 [-5.58, -0.87].
2. `p1` fails the column rule on (a) (CI-LB -1.07) and (b) (+0.51 is below the twin's +0.72). It also fails the official intent guard: 61 rows differ in intent correctness (32 / 29), against 3 for the twin and a limit of 7. `p2` and `p3` fail all three conditions.
3. `p1` parses (rank-1 tag ok on 1,078 / 1,080), but its rank-1 `E=none` verdict is weak: AUC 0.671 [0.642, 0.701], precision 0.572 (235 / 411), recall 0.599 (235 / 392). That is far under the node acceptance (0.75 / 0.80) and under the Solver-side c3 verdict (precision 0.74-0.76, recall 0.81-0.83). Node-local: not accepted.
4. The tag is nevertheless ADDITIONAL on the recipe's information-gain rule. The cross-fitted AUC increment for "gold empty" is +0.0215 [+0.0096, +0.0333] over N1 + intent prior (0.858 -> 0.879), +0.0230 [+0.0110, +0.0356] over N1, and +0.0076 [+0.0011, +0.0143] over N1 + prior + the lock's own answer (0.897 -> 0.905). The `p2` and `p3` verdicts are not additional.
5. The tag converts to little. The declared gate (rank-1 `E=none` AND N1 >= 0.2, lock Solver column, v4g base) reads +0.44 [-0.29, +1.17]: 232 rows fire, false fill falls 101 -> 66, 14 non-empty exact rows are lost, 0 intent rows move. The cross-fit top-share rule reads +0.48 [-0.09, +1.05] over N1 + prior, +0.63 [+0.07, +1.17] over N1 and +0.28 [-0.34, +0.89] when conditioned on the lock's answer. The ungated verdict reads -4.44 and the N1 gate alone -3.17. The element's ceiling on this base (a perfect c3 gate, +1.08 / +1.70, R6 offline note) sits below the 1.5 pp cascade bar in practice.
6. Locked consumer (`p1`'s own level-2 Solver column vs `lock`'s): normalised exact-set 55.56 % vs 53.98 % (+1.57 [-0.37, +3.52]). Empty-gold false fill is 21.94 % vs 25.77 % (-3.83 [-7.40, +0.00]); the twin's is -1.53 [-3.32, +0.26]. The mechanical screen fails.
7. `p2` and `p3` are FORM FAILURES of the mention channel inside the 128-character distinction. Rank-1 parse is 13.3 % / 19.7 %. Over all candidates: `no_trailer` 2,136 / 1,302, `mention_after_none` 490 / 991. Mention containment is 7.20 % (68 / 944) / 11.76 % (111 / 944), option precision 32.7 % / 35.0 %. The locked consumer's false fill rises +6.38 [+1.79, +10.71] / +3.32 [-0.77, +7.40]. `p2` also fails the node-local rank-1 intent guard (-1.57 pp against a 0.84 pp bar). This is evidence for decision 248's trigger: the channel binds, not the information.
8. The twin's +0.72 [+0.12, +1.37] is the first Fold B template-column twin whose CI excludes 0 (R1 i1 +0.57 [-0.10, +1.27]; R1 i2 -0.43 [-1.08, +0.19]). It belongs in the measured twin null. Everything here is DESCRIPTIVE on TRAIN Fold B; decision 253 is the owner's.

## 1. Inputs and identities

| item | value |
| --- | --- |
| cell / experiment | `slurp-native-stage3-nx-r6-perception-fold-b-v1` (package `docs/readiness/2026-10-10-slurp-nx-r6-perception-fold-b-v1/`; candidates `docs/readiness/2026-10-10-slurp-nx-r6-perception-candidates-v1/`; design `docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md`) |
| run / attempt | `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1` / `attempt-slurp-native-stage3-nx-r6-perception-fold-b-generation-v1` |
| flight commit | `1f04ce42d7de8623a8e5e0d1e72aafe3b3bb5daf` (`study_commit` of the run manifest; status COMPLETED; `study_repo_dirt` empty) |
| smoke stop and recovery | The first smoke (`...-smoke-4-generation-v1`, flight commit `58c546b54`) stopped 2026-10-10T08:11:08Z after 20 contacts. The cause was the first level-2 Solver input: `hypothesis content does not match its source response SHA-256`. The level-2 branch view swapped the note content without rebinding `source_response_sha256`. The fix is `45c3b3633`, merged as `6030c3149` (`perception_note_view_state` in `rails/runner.py`; regression test `tests/unit/test_perception_note_view_binding.py`). The smoke re-flew whole as `...-smoke-4-generation-rec1-v1` and passed at 09:17:22Z (40 contacts). This was the cell's single recovery (package README section 6b). |
| arm seal | Started 09:17:32Z; driver done 13:37:28Z; FINALIZED / COMPLETED: 1,080 rows, 10,800 contacts (10 per row), 0 tool calls, no serving restart. READ row root countersigned 13:45:00Z (commit `0cc96a5cd`), after the seal and before any arm column was opened. |
| roster | TRAIN Fold B `SLURP-EVO-FOLD-B-V2`: 1,080 rows (392 empty-gold, 688 non-empty-gold, 944 gold entities); split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; roster file sha256 `47b89b9e...` |
| flight cost (`efficiency.json`) | 10,800 contacts; 76,905,109 prompt / 723,541 completion tokens (71,208.4 / 669.9 per row); generation wall 14,985 s; GPU-active 14,462 s (4.017 GPU-h; 3.72 per 1,000 rows); mean utilisation 81.1 %; 43.2 contacts per minute; 31,547.97 repeated speech seconds. The cost belongs to the whole flight; the passes do not split it by arm. |
| run manifest / generation manifest | `8e6aa3c096abdf6748e448ac440058069faf89df60b87e3945ec68a0c7512ba5` / `05c3d86c68c2fd16da4885bf19bcd985a046da54cf56846fcbb94eda210e142c` |
| outputs / scores / trace / trace manifest | `4a43685ee590b9bf8f4d17fccbca2d8267d1298bfcc13d151b97f4c46250174d` / `a13453e4343dd077d4009c44f8d666f35c41a905f870caeb7fc83d13e5c5f9fa` / `dd08ba6fd55314044a4fe6cd01884b06a5e0b82bf582849fef83c75640e3c422` / `b996e2038f7596147cb00aae104cf5ad348a0c13149926b0670a89a60192ca6a` |
| phases / flight receipts | `30c2a201fa07f1f0b7b5d3e4a811c822a9cddc99fe9f4bad7d875c1645799272` / `9048d3ad1d4462aa9a05de2c7dd6840dae5dfba036cefe34297e404b1f00ceab` |
| protocol hash | `894b63c4f10cf66814f978498cef7ef0422fc84307e09e6893f202430bbac870` (run manifest = ledger row) |
| READ run / recipe | `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-COLUMN-READ-V1` / `slurp-nx-r6-perception-fold-b-column-analysis-v1`. `analysis-recipe-v1.json` sha256 at this note's base: `c36bfe6132887c8e32e7508af5e7b130c5b4d8303d337494a68e170f8a3b5caa`; `registered-facts-v1.json` `7f1afe75...`; package README `79c9627c...` |
| read driver / readers | `scripts/analysis/nx_r6_read.sh` `84c61a31...`. Reader E2b `slurp_nx_perception_column_read.py` `8d4fa7fc...` (schema `saea-nx-perception-column-read-v1`, read id `SAEA-NX-PERCEPTION-TEMPLATE-COLUMN-READ-V1`). Gain driver `slurp_nx_r6_upstream_empty.py` `b14c089b...`, equal to each gain report's `driver_sha256`. Rollout scorer `stage3_rollout_score.py` `eab3df91...`. Paired driver `5c95a2e3...`, `stage3_paired_read.py` `da9485fc...`. All sha256 values are at this note's base. |
| scorer fix | The official per-arm column scoring failed on its first run: the `perception-branches` mode assumed the older `branches` declaration. Commit `37dd4e3ce` (the column scorer reads a Perception `template_variants` group) was merged as `5bc06fa97`, and the official passes then ran (generated 2026-10-10T14:41Z). Each pass's `stop.json` reproduces the official aggregate in process (`official_reproduction_1e6`; diff <= 1.2e-16; status PASSED). |
| bootstraps | Official columns: paired row bootstrap, cluster `sample_id`, 10,000 draws, seed 20260915. Node-local: whole-utterance clusters, 10,000 draws, seed 20260915. Information gain: whole-utterance clusters, 2,000 draws, seed 20261010. Gate: whole-utterance clusters, 10,000 draws, seed 20260915. |
| read contacts | model 0, encoder 0, tokenizer 0, GPU 0, network 0, paid API 0. The five official column scorings belong to the read driver's render step and are not counted in the passes' `contacts`. |

The arms (one Perception visit per row, five templates over the same state and evidence). Each non-delivering arm is
followed by its own level-2 first-visit Solver contact under the locked Solver template, over its own note (receipt
`saea-perception-branch-arms-v4`). The base is the review-off COMP-1b module graph on lock v2.2 (v4g delivery
normaliser on all 1,080 rows), program `phase-native-module-v1-c10`.

| arm | template (sha256) | words | tag set | role |
| --- | --- | ---: | --- | --- |
| `p1` | `configs/probes/nx/perception/r6/r6-p1.txt` `8cd15846...` | 187 | `none,some` | presence tag only |
| `p2` | `.../r6-p2.txt` `2a27d0d4...` | 243 | `none,some` | presence tag plus up to three `M=` heard mentions |
| `p3` | `.../r6-p3.txt` `12ff7812...` | 264 | `none,some,unsure` | presence with an `unsure` hedge, plus mentions |
| `aa` | none (`replicate_of lock`) | 128 | - | the in-chain twin |
| `lock` | `configs/probes/slurp_native_role_perception_v3.txt` `76749780...` | 128 | - | delivering, untemplated, last |

## 2. Definitions

- **Tag grammar** (`configs/probes/nx/perception/r6/TAG-GRAMMAR-v1.md`, sha256 `9c0a2e17...`): `distinction := presence [ mentions ] "; " words`; `presence := "E=" (none | some | unsure)`; `mentions := ("; M=" words){1,3}`.
  - Each mention is at most 4 words and appears only after `E=some`.
  - The trailing distinction is at most 8 words.
  - The whole distinction is at most 128 characters (v1 note contract `slurp-intent-hypotheses-v1`; `evidence_refs` and `unresolved_fields` maxItems 0).
- **Parse classes per candidate.**
  - `ok`: the grammar matched.
  - `absent`: no `E=` head.
  - `invalid`: the head is present but the grammar fails, a value is outside the arm's tag set, or a mention follows `E=none`.
  - The rank-1 candidate's tag is the node verdict. The list majority is reported beside it (`split` = no majority).
- **Node metrics** (reader E2b, against gold).
  - `E=none` AUC, precision and recall for "gold has no entity" (392 empty-gold rows).
  - `E=some` precision and recall for "gold has an entity".
  - `unsure` rate by gold class.
  - Heard-mention containment: the share of the 944 gold entities whose normalised surface equals an offered `M=` surface. It is type-free (package README section 6 item 1); a match is attributed to the slot type of the gold entity it matches.
  - Option precision: the share of offered options that are gold.
- **Intent guards** (paired vs `lock`): gold on list, rank-1 share, candidate count, prompt tokens, `note_parse_status`. Recipe rule: "a guard moving by more than the twin's own movement plus 0.65 pp fails the arm".
- **Node acceptance** (recipe `acceptance.node_local`; design 2.2): rank-1 `E=none` recall >= 0.80 AND precision >= 0.75 on empty-gold rows, with a rank-1 tag parse rate (ok) >= 0.90, and no guard failing. A parse rate below 0.90 is a FORM FAILURE, not a verdict.
- **Information gain** (design section 4, quoted): "Gain g(m) = AUC_cf(B + m) - AUC_cf(B), cross-fitted over two utterance-hash halves so no row is scored by a model that saw it; CI95 by whole-utterance cluster bootstrap". The design defines "Additional = CI-LB of g(m) > 0 on the selection roster, AND the delivered-metric estimate through the registered consumer (the gate, or the Solver column) has CI-LB > 0 after conditioning on D's own verdict". The recipe's operative rule is the first clause only: "CI95 lower bound of the cross-fitted AUC increment of the rank-1 verdict over the baseline for 'gold empty' > 0". The `additional` flag in the reports implements that rule. **Stable** is the same sign and CI-LB > 0 on TRAIN Fold A with the rule fixed on Fold B. It is R6-A's term, not this cell's.
  - Baselines B: `n1` (N1, the entity-free share of the 20 supplied exemplars); `n1+prior` (plus the TRAIN intent entity-rate prior); `n1+prior+lock` (plus the lock Solver answer).
  - The combiner is an L2 logistic regression fitted on one utterance-hash half and scored on the other.
- **Gate** (recipe `acceptance.delivered_estimate`): "empty the lock Solver row where the rank-1 verdict is E=none AND N1 >= 0.2 (and the fixed N1 grid), v4g base". Every other row keeps the lock row, so no intent label can move (intent rows moved must be 0). Reference variants:
  - the verdict ungated;
  - the N1 gate alone;
  - a cross-fitted "top-share" rule (threshold chosen on one half, applied to the other), with and without the verdict.
- **Exchange rates** (`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`): +0.033 pp per false-filled empty-gold row emptied; -0.070 pp per non-empty exact row lost (per 1,080 rows).
- **False fill.** On an empty-gold row, the column predicts at least one entity. **Non-empty exact** means the predicted set equals gold on a non-empty-gold row. **Exact-set** is the same comparison on any row. The level-2 Solver column's primary is `exact_set_normalised`: the first-visit answer after the delivered row's normaliser (v4g).
- **Nomination rule for the official column** (NX programme; design 3.2 2c). NOMINATED iff all three hold:
  - (a) the official pooled SLU-F1 delta vs `lock` has CI95 lower bound > 0;
  - (b) the delta exceeds the `aa` twin's delta (+0.72);
  - (c) the intent guard holds: rows whose official intent correctness differs from `lock` <= 7.
  - HARM iff the CI95 upper bound < 0.
  - In this cell the official passes are registered as non-gating (`gating: false`; `aa-vs-lock` "sets the bar").

## 3. The official column (paired row bootstrap vs `lock`, cluster `sample_id`, 10,000 draws, seed 20260915)

`lock` levels: pooled official SLU-F1 64.34 %, span-F1 55.25 %, intent (`scenario_action_exact`) 82.41 %, per-row mean
SLU-F1 41.27 %. Every column is the arm's level-2 first-visit Solver answer after the v4g normaliser and projection,
scored once with `slurp-slu-official-train`.

| arm | pooled SLU-F1 % | pooled delta pp [CI95] | pooled span-F1 delta pp [CI95] | per-row SLU-F1 delta pp [CI95] (saves / harms) | intent % | intent delta pp [CI95] (rows differing) |
| --- | ---: | --- | --- | --- | ---: | --- |
| `aa` twin (bar) | 65.06 | **+0.72 [+0.12, +1.37]** | +0.48 [-0.21, +1.19] | +0.39 [-0.01, +0.82] (16 / 8) | 82.50 | +0.09 [-0.19, +0.46] (3: 2 / 1) |
| `p1` | 64.85 | +0.51 [-1.07, +2.08] | +0.20 [-1.70, +2.11] | +0.34 [-0.75, +1.47] (57 / 53) | 82.69 | +0.28 [-1.11, +1.76] (**61**: 32 / 29) |
| `p2` | 63.64 | -0.70 [-2.47, +1.13] | -1.94 [-4.34, +0.53] | +1.16 [-0.24, +2.55] (104 / 105) | 81.94 | -0.46 [-1.94, +1.02] (**67**: 31 / 36) |
| `p3` | 62.93 | -1.41 [-3.13, +0.35] | **-3.21 [-5.58, -0.87]** | +0.48 [-0.89, +1.86] (100 / 114) | 82.50 | +0.09 [-1.39, +1.57] (**65**: 33 / 32) |

Other per-row channels (delta pp [CI95], saves / harms):

| arm | `action_exact` | `scenario_exact` | `slot_f1_exact_f1` |
| --- | --- | --- | --- |
| `aa` | +0.00 [-0.28, +0.28] (1 / 1) | +0.09 [-0.19, +0.46] (2 / 1) | +0.21 [-0.20, +0.64] (9 / 7) |
| `p1` | +1.02 [-0.37, +2.41] (34 / 23) | +0.00 [-1.11, +1.11] (20 / 20) | -0.04 [-1.32, +1.23] (44 / 41) |
| `p2` | +0.09 [-1.30, +1.57] (33 / 32) | **-1.67 [-2.87, -0.46]** (14 / 32) | +0.18 [-1.51, +1.82] (80 / 79) |
| `p3` | +0.83 [-0.56, +2.22] (33 / 24) | -0.46 [-1.76, +0.83] (22 / 27) | -1.08 [-2.74, +0.54] (73 / 84) |

Headset (n = 527) vs far-field (n = 553), per-row delta pp (saves / harms). The tool emits per-channel numbers for
per-row metrics only.

| arm | SLU-F1 headset | SLU-F1 far-field | intent headset | intent far-field |
| --- | --- | --- | --- | --- |
| `aa` | +0.32 (8 / 5) | +0.45 (8 / 3) | +0.19 (1 / 0) | +0.00 (1 / 1) |
| `p1` | +0.38 (28 / 25) | +0.30 (29 / 28) | +0.00 (12 / 12) | +0.54 (20 / 17) |
| `p2` | +1.75 (49 / 48) | +0.59 (55 / 57) | +0.38 (17 / 15) | -1.27 (14 / 21) |
| `p3` | +1.42 (53 / 54) | -0.41 (47 / 60) | +1.33 (16 / 9) | -1.08 (17 / 23) |

Readings:

- **The twin moved +0.72 with CI-LB > 0.** Its rows differ on 24 per-row SLU rows and 3 intent rows. The same `lock` template sampled twice at the same state therefore moves the pooled column by about 0.7 pp on this roster. Every candidate is read against that bar.
- **The candidates move intent on 61-67 rows.** Their net intent change is small (+0.28 / -0.46 / +0.09). The level-2 Solver reads each arm's own candidate list, and the Perception arms reorder it: rank-1 share b / c is 32 / 37 for `p1`, 30 / 47 for `p2` and 31 / 39 for `p3`, against 10 / 8 for the twin (section 4). This is the cost of a different note, not of the tag's content alone.
- **`p2` and `p3` have per-row SLU-F1 above 0 at the point but pooled SLU-F1 below 0.** Per-row SLU-F1 scores every empty-gold row 0 whatever the arm answers, so it is blind to their added false fills (section 6). The pooled span-F1 shows them: -1.94 / -3.21.
- No pooled SLU-F1 upper bound is below 0: no arm is HARM.

## 4. Node-local tables (reader E2b, paired vs `lock`, whole-utterance cluster bootstrap, 10,000 draws, seed 20260915, CI95)

### 4.1 Parse classes

| arm | rank-1 ok / absent / invalid | rank-1 parse rate | every candidate ok / absent / invalid (of) | invalid reasons (every candidate) | acceptance |
| --- | --- | ---: | --- | --- | --- |
| `p1` | 1,078 / 0 / 2 | 99.81 % | 3,068 / 0 / 12 (3,080) | `trailer_form` 6, `middle_not_mention` 3, `separator` 3 | parse passes |
| `p2` | 144 / 0 / 936 | 13.33 % | 340 / 0 / 2,719 (3,059) | `no_trailer` 2,136, `mention_after_none` 490, `trailer_form` 44, `mention_form` 22, `separator` 19, `middle_not_mention` 8 | **FORM FAILURE** |
| `p3` | 213 / 0 / 867 | 19.72 % | 382 / 0 / 2,440 (2,822) | `no_trailer` 1,302, `mention_after_none` 991, `mention_form` 52, `trailer_form` 49, `middle_not_mention` 22, `separator` 21, `mention_count` 3 | **FORM FAILURE** |
| `aa` / `lock` | 0 / 1,080 / 0 | - | 0 / 2,987 / 0 | - | untagged by design |

The structured `entity_presence` JSON key path is `absent` on 1,080 / 1,080 rows of every arm, by construction: the v1
contract admits no such key.

### 4.2 Presence verdict

Rank-1 candidate:

| arm | none / some / unsure / invalid | `E=none` AUC [CI95] | `E=none` precision | `E=none` recall | `E=some` precision | `E=some` recall | unsure rate |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| `p1` | 411 / 667 / 0 / 2 | **0.671 [0.642, 0.701]** | **0.572** (235 / 411) [0.523, 0.619] | **0.599** (235 / 392) [0.550, 0.647] | 0.765 (510 / 667) | 0.743 (510 / 686) | 0.00 % |
| `p2` | 0 / 144 / 0 / 936 | 0.500 [0.500, 0.500] | - | 0.000 | 0.833 | 1.000 (on its 144 ok rows) | 0.00 % |
| `p3` | 0 / 213 / 0 / 867 | 0.500 [0.500, 0.500] | - | 0.000 | 0.822 | 1.000 (on its 213 ok rows) | 0.00 % (0 / 38 empty-gold, 0 / 175 non-empty-gold) |

List majority:

| arm | none / some / unsure / split / invalid | `E=none` AUC [CI95] | `E=none` precision | `E=none` recall | `E=some` precision | `E=some` recall |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `p1` | 469 / 604 / 0 / 5 / 2 | 0.667 [0.638, 0.696] | 0.542 (254 / 469) | 0.650 (254 / 391) | 0.773 | 0.685 |
| `p2` | 10 / 140 / 0 / 1 / 929 | 0.484 [0.446, 0.537] | 0.100 | 0.040 | 0.829 | 0.928 |
| `p3` | 7 / 212 / 0 / 1 / 860 | 0.511 [0.480, 0.551] | 0.286 | 0.050 | 0.821 | 0.972 |

On every rank-1 tag that parsed, `p2` and `p3` said `E=some`. No rank-1 candidate of either arm carried a valid
`E=none`; the list majority reads `none` on only 10 / 7 rows. Over all candidates, 490 / 991 tags were invalid because a
mention followed `E=none`. `p3` never used `unsure` (0 of 213 parsed rank-1 tags).

For comparison, the Solver's own presence judgement on the R1 flights (offline note section 3): lock column recall 0.65
/ precision 0.81, aggressive c3 recall 0.81-0.83 / precision 0.74-0.76. `p1`'s Perception verdict is less precise
than both and recalls less than c3. Its AUC (0.671) is below N1 alone (0.856).

### 4.3 Heard mentions (type-free surface containment against the 944 gold entities)

| arm | source | rows offering | offered options (on empty-gold rows) | containment | containment on ok rows | option precision |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| `p1` | rank-1 / list union | 0 / 0 | 0 (0) | 0.00 % | - | - (no mentions by design) |
| `p2` | rank-1 | 144 | 196 (31) | 6.99 % (66 / 944) | 66 / 155 | 33.67 % (66 / 196) |
| `p2` | list union | 150 | 208 (35) | **7.20 % (68 / 944)** | 68 / 162 | 32.69 % (68 / 208) |
| `p3` | rank-1 | 213 | 303 (47) | 11.33 % (107 / 944) | 107 / 248 | 35.31 % (107 / 303) |
| `p3` | list union | 219 | 317 (52) | **11.76 % (111 / 944)** | 111 / 253 | 35.02 % (111 / 317) |

The candidates README predicted containment >= 0.70 and option precision >= 0.60 for `p2`. Most gold entities were
never offered, because 936 / 867 rank-1 tags did not parse. Per slot type (list union, containment, gold count in
brackets), the types with at least 20 gold entities:

| slot type (gold) | `p2` | `p3` |
| --- | ---: | ---: |
| `date` (130) | 0.77 % | 7.69 % |
| `place_name` (108) | 9.26 % | 12.96 % |
| `time` (73) | 9.59 % | 15.07 % |
| `food_type` (69) | 10.14 % | 18.84 % |
| `media_type` (62) | 4.84 % | 4.84 % |
| `person` (58) | 13.79 % | 15.52 % |
| `business_name` (48) | 4.17 % | 20.83 % |
| `event_name` (47) | 8.51 % | 4.26 % |
| `transport_type` (39) | 12.82 % | 7.69 % |
| `weather_descriptor` (31) | 3.23 % | 0.00 % |
| `order_type` (24) | 4.17 % | 16.67 % |
| `business_type` / `list_name` / `news_topic` (21 each) | 4.76 / 0.00 / 0.00 % | 9.52 / 4.76 / 14.29 % |
| `device_type` (20) | 5.00 % | 10.00 % |

`date`, the type whose rows the aggressive Solver emptied most (R1 notes), is the least contained (1 of 130 for `p2`).

### 4.4 Intent guards and note marginals (paired vs `lock`)

| arm | gold on list % | diff pp [CI95] (b / c) | rank-1 (top-1) % | diff pp [CI95] (b / c) | mean list size | diff [CI95] | prompt tokens (mean) | diff |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: | ---: |
| `lock` | 91.94 | - | 81.57 | - | 2.74 | - | 3,590.6 | - |
| `aa` | 92.22 | +0.28 [-0.28, +0.83] (6 / 3) | 81.76 | +0.19 [-0.56, +0.93] (10 / 8) | 2.74 | +0.00 [-0.02, +0.03] | 3,590.6 | 0 |
| `p1` | 92.04 | +0.09 [-0.93, +1.11] (16 / 15) | 81.11 | -0.46 [-1.94, +1.02] (32 / 37) | 2.81 | +0.08 [+0.04, +0.11] | 3,674.6 | +84 |
| `p2` | 91.67 | -0.28 [-1.39, +0.83] (17 / 20) | 80.00 | **-1.57 [-3.15, +0.00]** (30 / 47) | 2.80 | +0.07 [+0.03, +0.11] | 3,749.6 | +159 |
| `p3` | 91.57 | -0.37 [-1.39, +0.65] (15 / 19) | 80.83 | -0.74 [-2.22, +0.83] (31 / 39) | 2.58 | **-0.16 [-0.21, -0.11]** | 3,781.6 | +191 |

The guard bar is the twin's own movement plus 0.65 pp:

- **Gold on list:** |+0.28| + 0.65 = 0.93 pp.
- **Rank-1 share:** |+0.19| + 0.65 = 0.84 pp.
  - `p1` (-0.46) and `p3` (-0.74) are within it; **`p2` (-1.57) exceeds it**.
- **List size** is measured in candidates per row, not pp; the twin moved 0.00.
  - `p1` and `p2` add about 0.08 candidates per row.
  - `p3` removes 0.16, with a CI excluding 0. Its list-size histogram shifts to 210 single-candidate rows (`lock` 34).
- **Prompt tokens** grow by the template's own length (+84 / +159 / +191), as registered.
- **`note_parse_status` `duplicates-collapsed`:** lock 26, aa 25, p1 32, p2 21, p3 26.
- **Gold-rank absent:** lock 87, aa 84, p1 86, p2 90, p3 91.

### 4.5 Node acceptance

| arm | rank-1 parse >= 0.90 | `E=none` recall >= 0.80 | `E=none` precision >= 0.75 | intent guards | node-local |
| --- | --- | --- | --- | --- | --- |
| `p1` | yes (0.998) | no (0.599) | no (0.572) | within the twin (gold on list, rank-1) | **NOT ACCEPTED** |
| `p2` | no (0.133) | - | - | rank-1 guard fails | **FORM FAILURE** |
| `p3` | no (0.197) | - | - | within (rank-1 -0.74 < 0.84) | **FORM FAILURE** |

## 5. Information gain and the gate (read `SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1`; zero contacts)

### 5.1 Cross-fitted AUC increment for "gold empty" (2,000 whole-utterance draws, seed 20261010)

| arm | baseline | AUC baseline | AUC with verdict | increment [CI95] | half 0 / half 1 (533 / 547 rows) | additional (CI-LB > 0) | verdict alone AUC [CI95] |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| `p1` | n1 | 0.8558 | 0.8789 | +0.0230 [+0.0110, +0.0356] | +0.0205 / +0.0260 | **yes** | 0.6713 [0.6426, 0.7003] |
| `p1` | n1+prior | 0.8577 | 0.8793 | **+0.0215 [+0.0096, +0.0333]** | +0.0193 / +0.0235 | **yes** | 0.6713 |
| `p1` | n1+prior+lock | 0.8969 | 0.9046 | +0.0076 [+0.0011, +0.0143] | +0.0075 / +0.0073 | **yes** | 0.6713 |
| `p2` | n1 | 0.8558 | 0.8616 | +0.0058 [-0.0006, +0.0118] | +0.0051 / +0.0066 | no | 0.5566 [0.5373, 0.5755] |
| `p2` | n1+prior | 0.8577 | 0.8629 | +0.0052 [-0.0011, +0.0111] | +0.0042 / +0.0054 | no | 0.5566 |
| `p2` | n1+prior+lock | 0.8969 | 0.8993 | +0.0024 [-0.0015, +0.0060] | +0.0015 / +0.0035 | no | 0.5566 |
| `p3` | n1 | 0.8558 | 0.8596 | +0.0038 [-0.0064, +0.0140] | +0.0076 / -0.0001 | no | 0.5787 [0.5572, 0.6016] |
| `p3` | n1+prior | 0.8577 | 0.8617 | +0.0040 [-0.0053, +0.0130] | +0.0076 / -0.0016 | no | 0.5787 |
| `p3` | n1+prior+lock | 0.8969 | 0.8992 | +0.0023 [-0.0033, +0.0076] | +0.0037 / -0.0007 | no | 0.5787 |

`p1`'s increment is positive on both utterance halves and survives conditioning on the lock Solver's answer. It is an
additional message element on the selection roster: the core's Perception-node presence judgement carries information
about "gold empty" that N1, the intent prior and the lock's own answer do not. `p2` and `p3` carry verdicts only as
"`E=some` or invalid", which is close to a parse indicator, and add nothing.

### 5.2 The gate on the lock Solver column (v4g base, 10,000 whole-utterance draws, seed 20260915)

Base: lock's v4g column, pooled SLU-F1 64.34 %, 101 false-filled empty-gold rows (192 rows changed by v4g). Only `p1`
fires: `p2` and `p3` never emit a valid rank-1 `E=none`, so their verdict rows are all 0.

`p1`, the declared rule and the fixed grid (verdict AND N1 >= t):

| rule | fired | fired on empty-gold | delta SLU-F1 pp [CI95] | false fills removed (base 101) | non-empty exact lost | intent rows | exchange prediction pp |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| **declared: `E=none` and N1 >= 0.2** | 232 | 186 | **+0.44 [-0.29, +1.17]** | 35 (101 -> 66) | 14 | 0 | +0.18 |
| N1 >= 0.1 | 304 | - | -0.72 [-1.78, +0.28] | 45 | 31 | 0 | -0.69 |
| N1 >= 0.15 | 265 | - | -0.03 [-0.93, +0.85] | 40 | 23 | 0 | -0.29 |
| N1 >= 0.25 | 199 | - | +0.63 [+0.03, +1.23] | 32 | 7 | 0 | +0.57 |
| N1 >= 0.3 | 164 | - | +0.70 [+0.26, +1.16] | 23 | 1 | 0 | +0.69 |
| N1 >= 0.4 | 122 | - | +0.39 [+0.01, +0.78] | 14 | 1 | 0 | +0.39 |
| N1 >= 0.5 | 85 | - | +0.14 [-0.10, +0.37] | 7 | 0 | 0 | +0.23 |
| N1 >= 0.6 | 64 | - | +0.08 [-0.07, +0.23] | 4 | 0 | 0 | +0.13 |
| N1 >= 0.7 / 0.8 / 0.9 | 44 / 29 / 13 | - | +0.05 / +0.02 / +0.06 | 3 / 2 / 2 | 0 | 0 | +0.10 / +0.07 / +0.07 |

References (`p1`):

| variant | baseline | fired | delta SLU-F1 pp [CI95] | false fills removed | non-empty exact lost | intent rows | exchange prediction pp |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| verdict ungated | - | 411 | -4.44 [-6.14, -2.80] | 52 | 62 | 0 | -2.62 |
| N1 gate alone (N1 >= 0.2) | - | 486 | -3.17 [-4.76, -1.68] | 72 | 72 | 0 | -2.66 |
| cross-fit top-share with verdict | n1 | 216 | **+0.63 [+0.07, +1.17]** | 30 | 6 | 0 | +0.57 |
| cross-fit top-share with verdict | n1+prior | 217 | +0.48 [-0.09, +1.05] | 29 | 7 | 0 | +0.47 |
| cross-fit top-share with verdict | n1+prior+lock | 351 | +0.28 [-0.34, +0.89] | 33 | 10 | 0 | +0.39 |
| cross-fit top-share without verdict | n1 | 109 | +0.03 [-0.33, +0.35] | 10 | 4 | 0 | +0.05 |
| cross-fit top-share without verdict | n1+prior | 84 | +0.01 [-0.31, +0.29] | 8 | 3 | 0 | +0.05 |
| cross-fit top-share without verdict | n1+prior+lock | 214 | +0.01 [-0.35, +0.32] | 9 | 3 | 0 | +0.09 |

The cross-fit top-share rule of `p2` / `p3` (their verdict is an `E=some`-or-invalid indicator): `p2` +0.13 [-0.20,
+0.44] (n1), +0.11 [-0.31, +0.51] (n1+prior), -0.10 [-0.68, +0.45] (n1+prior+lock); `p3` +0.09 [-0.61, +0.76],
+0.06 [-0.43, +0.54], -0.01 [-0.24, +0.19]. Every intent-rows-moved count is 0.

Exchange arithmetic: prediction = 0.033 x false fills removed - 0.070 x non-empty exact lost.

- The declared rule predicts +0.18 and measures +0.44, so it measures 0.26 pp above the prediction.
- The grid points from N1 >= 0.25 up, and the cross-fitted rules, agree within about 0.1 pp.

Against the Solver-side analogue on the R1 flights (offline note section 4: c3 verdict x N1 >= 0.2 on v4g, false fill
91 -> 64 and 93 -> 60, 3 non-empty exact rows lost, +0.75 [+0.27, +1.24] / +0.98 [+0.50, +1.48]), `p1`'s verdict
removes a similar number of false fills (35). It loses 14 non-empty exact rows instead of 3, so the rule's yield
halves.

**The design's two-clause Additional.**

- The first clause (AUC increment CI-LB > 0) holds on all three baselines.
- The second clause (a delivered estimate with CI-LB > 0 after conditioning on D's own verdict) is not met by the declared rule (+0.44 [-0.29, +1.17]) or by the cross-fit rule over n1+prior+lock (+0.28 [-0.34, +0.89]).
- The positive lower bounds on file are:
  - the cross-fit rule over n1 (+0.63 [+0.07, +1.17]), which does not condition on the lock;
  - the fixed-grid points N1 >= 0.25 / 0.3 / 0.4, which were not declared and were read on the roster that selects them.

## 6. The locked consumer: each arm's level-2 Solver column (E2 reader inside E2b; normalised = v4g)

Marginal levels (normalised; raw first-visit text in brackets):

| arm | exact-set | empty-gold false fill (rows of 392) | non-empty exact (rows of 688) | parse valid | predicted items |
| --- | --- | --- | --- | ---: | ---: |
| `lock` | 53.98 % (583) [49.17] | 25.77 % (101) [35.97 % (141)] | 42.44 % (292) [40.70] | 99.81 % | 902 |
| `aa` | 54.72 % (591) [49.35] | 24.23 % (95) [34.69 % (136)] | 42.73 % (294) [40.26] | 99.81 % | 897 |
| `p1` | 55.56 % (600) [51.11] | 21.94 % (86) [31.63 % (124)] | 42.73 % (294) [41.28] | 100.00 % | 881 |
| `p2` | 52.31 % (565) [42.13] | 32.14 % (126) [49.23 % (193)] | 43.46 % (299) [37.21] | 99.91 % | 984 |
| `p3` | 51.94 % (561) [41.76] | 29.08 % (114) [46.68 % (183)] | 41.13 % (283) [35.17] | 100.00 % | 966 |

Paired vs `lock` (normalised; delta pp [CI95] (b arm only / c lock only); for false fill a negative delta is better):

| arm | exact-set | empty-gold false fill | non-empty exact | parse valid | mechanical screen (normalised / raw) |
| --- | --- | --- | --- | --- | --- |
| `aa` | +0.74 [-0.09, +1.57] (15 / 7) | -1.53 [-3.32, +0.26] (3 / 9) | +0.29 [-0.58, +1.16] (6 / 4) | +0.00 | twin |
| `p1` | +1.57 [-0.37, +3.52] (64 / 47) | **-3.83 [-7.40, +0.00]** (20 / 35) | +0.29 [-1.89, +2.47] (29 / 27) | +0.19 [+0.00, +0.46] (2 / 0) | fail / fail (no secondary against) |
| `p2` | -1.67 [-4.07, +0.74] (81 / 99) | **+6.38 [+1.79, +10.71]** (52 / 27) | +1.02 [-1.89, +3.92] (54 / 47) | +0.09 | fail (false fill against) / fail (false fill, non-empty exact against) |
| `p3` | -2.04 [-4.35, +0.28] (72 / 94) | +3.32 [-0.77, +7.40] (38 / 25) | -1.31 [-4.22, +1.60] (47 / 56) | +0.19 | fail / fail (false fill, non-empty exact against) |

Raw diagnostic (paired, raw first-visit text):

- `p1`: exact-set +1.94 [-0.09, +4.07], false fill -4.34 [-8.16, -0.51].
- `p2`: exact-set -7.04 [-9.72, -4.35], false fill +13.27 [+8.67, +17.86], non-empty exact -3.49 [-6.69, -0.29].
- `p3`: exact-set -7.41 [-10.00, -4.81], false fill +10.71 [+6.38, +15.05], non-empty exact -5.52 [-8.87, -2.33].
- `aa`: exact-set +0.19 [-0.74, +1.11].

The v4g normaliser repairs much of `p2` / `p3`'s raw damage:

| arm | text changed | raw false -> normalised true | raw true -> normalised false |
| --- | ---: | ---: | ---: |
| `lock` | 192 | 63 | 11 |
| `aa` | 192 | 69 | 11 |
| `p1` | 185 | 62 | 14 |
| `p2` | 297 | 120 | 10 |
| `p3` | 277 | 121 | 11 |

`p2`'s false fills fall 193 -> 126 under the normaliser, and the remainder still exceeds `lock`'s 101.

Per slot type (normalised node-local totals over 944 gold entities):

| arm | gold exact | gold missing | gold wrong | predicted | spurious |
| --- | ---: | ---: | ---: | ---: | ---: |
| `lock` | 510 | 228 | 206 | 902 | 186 |
| `aa` | 513 | 225 | 206 | 897 | 178 |
| `p1` | 506 | 229 | 209 | 881 | 166 |
| `p2` | 514 | 199 | 231 | 984 | 239 |
| `p3` | 497 | 203 | 244 | 966 | 225 |

- **`p1`** predicts 21 fewer items than `lock`.
  - Spurious falls by 20: `place_name` -6, `date` -5, `time` -5, `food_type` -4, `song_name` -4, `general_frequency` -3, `order_type` -3; against `business_name` +7 and `list_name` +4.
  - Exact falls by 4: `date` -6, `event_name` -3, `person` -3, `list_name` -2, `time` -2; against `media_type`, `transport_type` and `weather_descriptor` +2 each.
  - The Solver used the tagged note as a mild empty signal. False fill -3.83 against the twin's -1.53 is about 2.3 pp net of the twin at the point, with a CI that reaches 0.
- **`p2`** predicts 82 more items.
  - Spurious rises by 53: `person` +12, `list_name` +10, `place_name` +8, `event_name` +5, `business_type` / `media_type` / `weather_descriptor` +4 each.
  - Missing falls by 29 and wrong rises by 25. Exact is +4 net: `media_type` / `order_type` +5, `business_type` / `date` / `weather_descriptor` +4, against `list_name` -6, `food_type` -5.
  - The offered mentions read as values to fill. That matches the i2-c2 soft sentence of R1 (false fill +9.95).
- **`p3`** predicts 64 more items.
  - Spurious rises by 39: `person` +9, `place_name` +9, `list_name` +8, `event_name` +6, `media_type` +5.
  - Exact falls by 13: `food_type` -7, `event_name` -6, `list_name` -4, `person` -3; against `date` +5, `business_name` / `weather_descriptor` +4.

Section 2b of the design asks whether the locked Solver already uses tagged notes. It sets the test as "CI-LB > 0 on
normalised exact-set or false fill with no non-empty loss". For `p1` the false-fill CI upper bound is exactly 0.00 and
the exact-set CI-LB is -0.37. The answer is "at the point, a little; not with a CI".

## 7. Per-scenario tables (official columns; 18 scenarios x 60 rows; paired cluster bootstrap, 10,000 draws, seed 20260915)

Natural mixture (raw roster mean; the roster is proportional, not floored) and equal-stratum weighting, both from the
passes:

| arm | natural-mixture SLU-F1 delta pp [CI95] | equal-stratum SLU-F1 delta pp [CI95] | equal-stratum intent delta pp [CI95] | scenarios up / down / zero (SLU) |
| --- | --- | --- | --- | --- |
| `aa` | +0.72 [+0.12, +1.37] | +0.72 [+0.11, +1.37] | +0.09 [-0.19, +0.46] | 11 / 4 / 3 |
| `p1` | +0.51 [-1.07, +2.08] | +0.07 [-1.56, +1.75] | +0.28 [-1.11, +1.67] | 10 / 7 / 1 |
| `p2` | -0.70 [-2.47, +1.13] | -1.30 [-3.31, +0.74] | -0.46 [-1.94, +1.02] | 7 / 11 / 0 |
| `p3` | -1.41 [-3.13, +0.35] | -1.72 [-3.71, +0.34] | +0.09 [-1.39, +1.57] | 6 / 12 / 0 |

Per-scenario official pooled SLU-F1 delta vs `lock` (pp; `lock` level in the second column). Bold marks an interval
excluding 0; every other interval spans 0, and all are wide at 60 rows.

| scenario | `lock` SLU % | `aa` | `p1` | `p2` | `p3` |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 69.78 | +0.82 | +6.97 | -1.04 | +4.47 |
| audio | 55.29 | +2.93 | -6.03 | +3.33 | -8.71 |
| calendar | 63.79 | -1.31 | -2.63 | -2.04 | -1.47 |
| cooking | 64.28 | +1.13 | +1.32 | -0.57 | +1.40 |
| datetime | 74.93 | -0.90 | +0.00 | -3.67 | -1.53 |
| email | 72.73 | +2.02 | +2.27 | -1.27 | -0.22 |
| general | 41.83 | +0.00 | -0.78 | -7.72 | -6.77 |
| iot | 70.99 | +0.00 | +2.43 | -3.77 | -5.08 |
| lists | 56.44 | -2.71 | -9.84 | **-15.89 [-31.74, -0.34]** | -11.07 |
| music | 50.36 | +1.30 | -3.54 | -8.21 | -3.95 |
| news | 61.97 | +0.00 | +3.01 | +0.18 | +3.23 |
| play | 52.26 | +2.83 | +3.53 | +2.32 | -3.15 |
| qa | 64.69 | -0.61 | +2.18 | +1.29 | +2.87 |
| recommendation | 64.42 | +3.03 | -2.15 | -0.09 | -3.64 |
| social | 68.13 | +0.91 | -2.43 | +0.81 | -1.56 |
| takeaway | 55.31 | +0.53 | +1.29 | +5.59 | +2.15 |
| transport | 71.84 | **+2.83 [+0.35, +6.07]** | +3.62 | -1.33 | -5.67 |
| weather | 67.17 | +0.08 | +2.02 | **+8.62 [+2.86, +14.91]** | **+7.79 [+3.45, +12.92]** |

- `lists` is the largest loss for every candidate (-9.84 / -15.89 / -11.07). That is consistent with the roster-wide `list_name` spurious rise (+4 / +10 / +8, section 6); the per-scenario slot split is not on file.
- `weather` is the only stratum where `p2` / `p3` gain with a CI excluding 0.
- Per-scenario intent deltas stay within +-5.00 pp (at most 5 saves or 5 harms in a stratum, e.g. `p1` `general` 5 / 2, `p2` `music` 2 / 5); no per-scenario intent interval excludes 0.

## 8. What the verdict means and does not

Column rule (section 2): NOMINATED iff (a) CI95-LB > 0, (b) delta > the twin's +0.72, (c) official intent rows
differing <= 7. HARM iff the pooled UB < 0.

| arm | (a) CI-LB > 0 | (b) delta > +0.72 | (c) intent rows <= 7 | HARM (UB < 0) | node-local | information gain | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `p1` | no (-1.07) | no (+0.51) | no (61) | no (UB +2.08) | not accepted (0.57 / 0.60) | ADDITIONAL (AUC clause) | **NOT NOMINATED** |
| `p2` | no (-2.47) | no (-0.70) | no (67) | no (UB +1.13) | FORM FAILURE (parse 13.3 %) | not additional | **NOT NOMINATED** |
| `p3` | no (-3.13) | no (-1.41) | no (65) | no (UB +0.35) | FORM FAILURE (parse 19.7 %) | not additional | **NOT NOMINATED** |

**What it means.**

- **The presence tag carries information, but too little at this node to pay.** `p1`'s rank-1 verdict adds +0.02 cross-fitted AUC over N1 and the intent prior, stable on both utterance halves, and +0.008 even over the lock's own answer. The tag is a real message element.
  - Its quality (precision 0.57, recall 0.60) is below the 0.75 / 0.80 acceptance and below the Solver-side c3 verdict.
  - Through the deterministic gate it converts to +0.44 [-0.29, +1.17] (declared) and at most +0.63 [+0.07, +1.17] (cross-fit over N1, not conditioned on the lock).
  - The element's ceiling on the v4g base (perfect c3 gate +1.08 / +1.70) means no realistic gate on this element clears the 1.5 pp cascade bar.
- **The mention channel failed on form, not on information.** `p2` and `p3` could not fit `E=`, up to three `M=` mentions and the trailer into the 128-character distinction:
  - `no_trailer` 2,136 / 1,302;
  - they put mentions after `E=none` (490 / 991);
  - no rank-1 candidate carried a valid `E=none`;
  - `p3` never used `unsure`.
  - The mentions that did arrive contained 7-12 % of gold entities at 33-35 % option precision, and the locked Solver read them as values to fill (false fill +6.38 / +3.32).
  - Whether heard-mention options carry gain is therefore unmeasured. The v1 channel is the binding constraint, which is decision 248's 2d trigger ("tag parse rate low, mentions truncated, intent guard failing").
- **The candidates move intent on 61-67 rows** through a different candidate list, against 3 for the twin. A Perception template that rewrites the note reshuffles the Solver's intent choice even when the net intent delta is near 0.
- **The twin's +0.72 [+0.12, +1.37] is a null, not an effect.** It is the first Fold B template-column twin with CI-LB > 0 (R1 i1 +0.57 [-0.10, +1.27]; R1 i2 -0.43 [-1.08, +0.19]). Three twins now span -0.43 .. +0.72 on the same roster. That spread belongs in the measured twin null, and it is larger than `p1`'s pooled effect.

**What it does not mean.**

- It is DESCRIPTIVE, on TRAIN Fold B (decisions 28 and 86), the roster that also selected the candidates and the gate. It is not a test claim, not a system-level claim, and not evidence about other carriers.
- It admits nothing and locks nothing: no Perception template, no `presence-gate-v1`, no change to lock v2.2. The delivered answer of this flight is the lock's, byte for byte (I7).
- Stability (Fold A) was not measured; it is R6-A's term.
- `p1`'s ADDITIONAL is the recipe's AUC clause only. The design's delivered-estimate clause, conditioned on the lock, is not met.
- Under the plateau rule this is the first evaluated Perception-entity round without a node-local acceptance. Whether to close the line, fly one more round, or move to the v2 note contract is decision 253, the owner's.

One line (the only recommendation): if the line continues, the measured binding constraint is the 128-character v1
channel, so decision 248's v2 contract is the lever, ahead of another v1 wording round.

## 9. Pointers (sha256 of the on-file bytes read)

Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-COLUMN-READ-V1/`:

| file | sha256 |
| --- | --- |
| `node-local/report.json` | `50abb1574f6474596c1e71e922203e7adccad4d859d20b36ca913f6949a2626d` |
| `node-local/tables.md` | `6a2fcc45a045bd4a9bce4b3c076f14e7fac5381ed5fb255a0d40229de9bbcdc2` |
| `aa-vs-lock/score-contrasts.json` / `verdict.json` / `per-scenario-tables.json` | `99f152cb9a2a7c8368902a5af4807882a9d5805d3be7c0c4727874eec77fd88f` / `71304653529c1796c18ec0a1b5f1b943aaa44e3e27aee309b81a627931ce91ae` / `60331afb8f7c40841f4f7ec4306b0d3995ed560125d424a70fb16dc4167c6ae3` |
| `p1-vs-lock/score-contrasts.json` / `verdict.json` / `per-scenario-tables.json` | `171f64ae52712e8c6a422848c05a410e614dd1a4b94250ee9d2f542ef3e8bdbd` / `f73f20a1ddf17293933478a40cf86c176e326ffcc0c4a838527ddf9d12a81002` / `3fe68571ebf26548405409106cf2cd4698d5c21f9cac419934f01730fa04c348` |
| `p2-vs-lock/score-contrasts.json` / `verdict.json` / `per-scenario-tables.json` | `328bfcfc181d575d66f2ee8a21556c31544bce88a3c40e7436d672eda3a3ddde` / `1a9a1b32e7b904913906db64f5d6d738621b6c49a9af4e57f4b32f497386d31b` / `dff8a7890e38d45ccace71f7ece2496fee4e7b7377790e88d8b0544eedb5ea85` |
| `p3-vs-lock/score-contrasts.json` / `verdict.json` / `per-scenario-tables.json` | `48c7322a8f463f808db796214f927c00476c14402abccf5fc14dbfd5b3ea4420` / `7820934971160e9922d359cbf7092b00beddad7efa8da22b95ebd11424577ac1` / `61c6275b692319c394c2b55df0a434d9b2d892e3126802c6b75d840e57970da0` |
| `*-vs-lock/stop.json` (aa / p1 / p2 / p3) | `e1a0233d...` / `3e7cf6b9...` / `56932b5d...` / `ddeed65e...` (all PASSED) |

Every `verdict.json` has status DESCRIPTIVE, contacts model / encoder / scorer / tokenizer 0, and `stage3_algorithm` `none`.

Gain root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1/<arm>/<baseline>/report.json` (schema
`saea-slurp-nx-r6-perception-gain-v1`, status DESCRIPTIVE, all contacts 0):

| arm | n1 | n1-prior | n1-prior-lock |
| --- | --- | --- | --- |
| `p1` | `3cfede060f3637ce1fb14a03a8c6e494c4fa853a5a4c81eaa92f27cb3906f534` | `ef056f0dbbf85fa5c335156605fde6107dd76178f53e24cfc8a05111ba031ae9` | `3b4f75b113c6b46bd6ecb2f434159fd9db92a79a41a3887bac4f6330e94ddde1` |
| `p2` | `67e22b356f7aac543a95fb0f433fc590eaa06725571d273aa75fbe9e9244886e` | `61d8fb38ff1b358be694aa24a6bab5ba79d145104aedbbed3c4e89b97951c191` | `690a341e2174ba94e93d56bfe4da63f386ca04d455f1c3752c663edd9976d27d` |
| `p3` | `f04f3658fe46e0527fc12e14f3c2ca5c3a8d476768f7cfe3579bb215739af367` | `b68fde613289d286917832463b83d4aefd27b84036d030f15b8ba31606bdb3cf` | `4223f2516d9ca41a057afc37b149099d07761e9a5a3b988a57c95ea938e5f480` |

Run dir `$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1/attempt-slurp-native-stage3-nx-r6-perception-fold-b-generation-v1/`
(manifests in section 1). Official column outputs under `supply-variants/`:

| file | sha256 |
| --- | --- |
| `score-summary.json` | `20593ee55f84aab049e25e237bbb52e96dc9b5e649cc336bd5f6dbcc054c7564` |
| `render-manifest.json` | `fcdf8ca06dc6a0ac0e17f33989bb604983d6e70ce265ec881d9191b1cba3bd75` |
| `first-visit-rows.json` | `98dd24d024923139240d23246abfc9680cb228d1166dba649b13d648e2c84d83` |
| `arm-lock-slurp-slu-official-train-scores.json` | `0c528795f9038832cfbec7ba67ccd49969863cd16712a66ea8632ad32eb6ef78` |
| `arm-aa-...` | `b2dd8b9552a34f2e5907f6ea9f1803aa31121e2d46382b4b8dfc096c29382794` |
| `arm-p1-...` | `0d4dcd7e5e39e91cce2aad663afb4ba1773e68b4f1b8cc50b2061fa3eb561b08` |
| `arm-p2-...` | `c98077d771e8171b14e5992ad7851606e6b66d1d84ca2a85db313f32352616c4` |
| `arm-p3-...` | `5849b5709253a762751720e0e3aa5272dd79f0525c96d7ec8d78c2c1111f6ef8` |

Repository documents (sha256 at this note's base):

| document | sha256 |
| --- | --- |
| design `docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md` | `8d30e095...` |
| candidates README | `03574db7...` |
| R6 offline note `docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md` | `cb45b6f4...` |
| R1 i2 note `docs/results/2026-10-10-slurp-nx-r1-i2-solver-fold-b-column-read.md` | `5efc33eb...` |
| exchange-rate note `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` | `52e9525d...` |

Reproduce, from the study root in WSL (`source ~/.venvs/speechrl/bin/activate`; `SPEECHRL_DATA_DIR` set). The read is
model-free, refuses unless the READ row is root countersigned, and never overwrites a filled pass directory.

```bash
bash scripts/analysis/nx_r6_read.sh --dry-run
bash scripts/analysis/nx_r6_read.sh
A=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-COLUMN-READ-V1
G=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1
sha256sum $A/node-local/report.json $A/node-local/tables.md $A/*-vs-lock/score-contrasts.json $G/*/*/report.json
```
