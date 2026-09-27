# SLURP: where the gold entry sits in the delivered block, and how free the Solver is over the intent

Date: 2026-09-26. Read id `SAEA-SLURP-MF-GOLD-POSITION-SOLVER-FREEDOM-V1`, recipe `slurp-gold-position-and-solver-freedom-read-v1`. Generated `2026-09-27T00:36:29+00:00`. A model-free read over sealed bytes: zero model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid-API contacts. A DIAGNOSTIC, never a gate: it registers no cell, admits no mechanism, authorises no flight and states no effectiveness, superiority or generalisation claim; every roster is a discovery or dev roster and every number is a development number (owner decisions 28 and 86). No utterance text, transcript, delivered answer, gold filler, predicted filler, candidate distinction or knowledge body is written or printed: every cell is an id, a position, a count, a rate or a hash. Gold is read offline on the scoring side only (the sealed bad-case bank, the sealed ROLL-1 official score file, the governed TRAIN and DEVEL splits through `data.slurp.load_slurp_split`) and reaches no query, key, selector or config.

## 0. Inputs

| Artefact | Relpath under `SPEECHRL_DATA_DIR` | sha256 |
| --- | --- | --- |
| bad-case bank | `analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl` | `26231b86b86f35251fed2b7d7c59bf33e8806b5ef71739b74bf9d5bc2b8a3ccf` |
| slot-contracts-v2 snapshot | `knowledge/slurp/semantic/slot-contracts-v2/snapshot.json` | `a48ed83eb7878e9eaedfe4dbdf4ea747e3e582e08899ff1f0edfdfe438ae8904` |
| `roll1` phases | `runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/attempt-slurp-native-stage3-rollout-r01-generation-v1/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1.phases.json` | `203aab4861e503a088af6cd67662164c908d0ecf66149ce8bf97bf1706aa4f9d` |
| `roll1` outputs | `runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/attempt-slurp-native-stage3-rollout-r01-generation-v1/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1.outputs.jsonl` | `e27faef7c7100fe66e82222f36a17dba6a8b9a5c2a0db7df83937a1e0175df0c` |
| `roll1` exemplar pool | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json` | `f549466f22bb0cae00a99849a1a811889eb82af9b632305c815fa123ad5795ca` |
| `train-fold-a-plan` phases | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.phases.json` | `7cac358a39c446c7aa13fcec70722a4669814ea0fad4fc76e9bf291d7b4b8e6f` |
| `train-fold-a-plan` outputs | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.outputs.jsonl` | `2dcaa925ab7dad77e5938002d5606189ff7f644a94ade5b7265060e94d3ae17f` |
| `train-fold-a-plan` exemplar pool | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` | `fcb5506c63653abe996dea15fdccd7c81a84a837b6377ca13f5b35d73283d6b2` |
| `dev2000-added-plan` phases | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/attempt-slurp-native-default-plan-dev2000-added-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1.phases.json` | `7853313714c58b434f306ebbc2df7de8b05801feb8695dbee4663dfacae4aed1` |
| `dev2000-added-plan` outputs | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/attempt-slurp-native-default-plan-dev2000-added-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1.outputs.jsonl` | `41ebcea4d13ef779e51cdf6c69a4210194c842886db83e892fa7cc43cf053909` |
| `dev2000-added-plan` exemplar pool | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` | `fcb5506c63653abe996dea15fdccd7c81a84a837b6377ca13f5b35d73283d6b2` |
| ROLL-1 official score file | `analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1/PS-registered-support-3-slurp-slu-official-projected-v3-train-scores.json` | `70247697eca510e9dc699983f23996bcb77113d43c94ba340d764083bb04f76d` |

**Structural checks, all rows.** Delivered answers are parsed after `apply_slurp_projection_v3_delivery` (idempotent on the two PLAN rosters, whose deliver node already applied it; the ROLL-1 pool has no deliver node and its scorer projects at scoring time), so the parsed intent and the exact-match entity counts reproduce the sealed classes. The rendered block order is the sealed query-state order: `rails.kb_policy.fuse_associated_values_factory` (kb_policy.py:893-960) walks the boundary candidates in rank order, so positions 1-8 ARE cosine ranks 1-8; `_fuse_supply_filter` returns `tuple(sorted(set(selected_value_ids)))` (kb_policy.py:859), so the twenty exemplars are rendered in string order of their value ids and the retrieval rank is not visible to the model; `core.model.transport` renders `supplied_evidence` in list order (transport.py:889-896). The trace pass below checks that order against every perception contact and every row's first Solver contact.

| Arm | rows | parsed intent == sealed class | exact FN == sealed FN | exemplar rank scores descending | exemplar block rendered in sorted id order | Perception state parsed | perception contacts: order agrees | first Solver contacts: order agrees | cosine rank == sealed position |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `roll1` | 625 | 625 | 625 | 625 | 625 | 625 | 625/625 | 625/625 | 495/495 |
| `train-fold-a-plan` | 1080 | 1080 | 1080 | 1080 | 1080 | 1080 | 1080/1080 | 1080/1080 | 947/947 |
| `dev2000-added-plan` | 1000 | 1000 | 1000 | 1000 | 1000 | 1000 | 1000/1000 | 1000/1000 | 815/815 |

## A. Is delivery necessary, or only persuasive?

**The code answer: nothing ties the delivered intent to the eight.** Two candidate sets exist and neither binds the Solver. (1) Perception's block is the k=8 boundary retrieval, but Perception's OUTPUT is constrained only by the structured-output schema, whose `intent_id` enum is `validator.legal_intent_ids` -- all 60 -- not the delivered eight (`rails/artifact_results.py:275-278`); the projection that reads it keeps at most three distinct ids (`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`, `candidate_supply.solver.max_candidates` 3). (2) The Solver receives those hypotheses as a sealed `phase:perception` state in its history, the same 8+20+contracts evidence block, and the full inventory in the shared task instruction (`configs/probes/slurp_native_role_context_v3.txt:5-8`, rendered by `data/slurp.py:1236-1250`); its own instruction says 'choose one of those candidate intents' and 'use the scenario/action pair belonging to the selected candidate' (`configs/probes/slurp_native_role_solver_v2.txt:1,6`), and that sentence is the ONLY tie. The Solver phase declares no response format (`configs/policy/phase-native-candidates-review-revise-v1.json`, solver `response_format_id: null`); `parse_slu_response` accepts any scenario/action strings (`reproduction/slurp_scoring.py:349-370`); the deliver node projects an illegal pair onto the 60-pair inventory, never onto the candidates (`rails/delivery_normalisers.py:84-110`, `rails/slurp_projection_v3.py:387-447`); the candidate route itself states that hypotheses 'never restrict the Solver's legal answer space' and indexes contracts against the full inventory (`rails/candidate_semantic_supply.py:5-6, 611-636`); the commit policy takes a plurality over parsed votes with no legality check (`rails/commit_policies.py:168-196, 267-347`); the Reviewer's verdicts steer nothing (`rails/controllers.py:666-675`) and its tool was retired (decision 135); the Planner may only route and cannot deliver (`rails/controllers.py:993-995`); and the ACCEPT route delivers the latest delivery-eligible Solver draft as is (`reproduction/ojw/native_episode.py:1023-1033`). So the Solver is free over all 60, and beyond them up to projection.

**The empirical answer.** Delivered intents by where they sit; correctness is the sealed class.

| Arm | parsed | delivered outside the 8 (n, correct) | delivered inside the 8 | delivered outside Perception's list | delivered inside the list | correct rows whose gold was NOT in the 8 | correct rows whose gold was NOT in the list | Perception widths |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |
| `roll1` | 625 | 28/49 (57.1 %) | 413/576 (71.7 %) | 7/19 (36.8 %) | 434/606 (71.6 %) | 28 | 7 | {1: 31, 2: 146, 3: 448} |
| `train-fold-a-plan` | 1079 | 28/38 (73.7 %) | 860/1041 (82.6 %) | 7/15 (46.7 %) | 881/1064 (82.8 %) | 28 | 7 | {1: 39, 2: 218, 3: 823} |
| `dev2000-added-plan` | 998 | 36/59 (61.0 %) | 730/939 (77.7 %) | 9/19 (47.4 %) | 757/979 (77.3 %) | 36 | 9 | {1: 48, 2: 188, 3: 764} |

| Arm | gold in the 8 | gold in Perception's list | gold in both | gold in the 8 but not the list | gold in the list but not the 8 | deliver-node label branches |
| --- | --- | --- | --- | --- | --- | --- |
| `roll1` | 413/495 (83.4 %) | 434/482 (90.0 %) | 411/457 (89.9 %) | 2/38 (5.3 %) | 23/25 (92.0 %) | {'None': 625} |
| `train-fold-a-plan` | 860/946 (90.9 %) | 881/942 (93.5 %) | 857/916 (93.6 %) | 3/30 (10.0 %) | 24/26 (92.3 %) | {'None': 1, 'already-legal': 1045, 'edit-distance': 3, 'r-action': 31} |
| `dev2000-added-plan` | 730/813 (89.8 %) | 757/820 (92.3 %) | 729/782 (93.2 %) | 1/31 (3.2 %) | 28/38 (73.7 %) | {'None': 2, 'already-legal': 937, 'edit-distance': 8, 'r-action': 53} |

**Reading.** The Solver does leave the block, and it is usually wrong when it does: on TRAIN Fold A 38 delivered intents sit outside the eight and 28 of them are right (73.7 %), against 82.6 % inside. It almost never leaves Perception's list (15 rows), so the practical selector is the 1-3 hypotheses, not the eight. Correct answers whose gold entry was never delivered exist -- 28 on Fold A -- so delivery is not NECESSARY; the block persuades Perception, Perception's list persuades the Solver, and the funnel is what section B measures. Rows whose gold sits in the block but not in the list convert at 10.0 %; rows whose gold reached the list convert at 93.5 %.

## B. Does position inside the delivered block predict correctness?

### B.1 Boundary block: P(intent correct | gold at position p), and Perception pass-through by position

| Arm | p=1 | p=2 | p=3 | p=4 | p=5 | p=6 | p=7 | p=8 | p=1 | p=5-8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `roll1` correct | 288/294 (98.0 %) | 54/74 (73.0 %) | 30/45 (66.7 %) | 13/22 (59.1 %) | 8/19 (42.1 %) | 10/17 (58.8 %) | 6/12 (50.0 %) | 4/12 (33.3 %) | 288/294 (98.0 %) | 28/60 (46.7 %) |
| `roll1` gold reaches Perception's list | 294/294 | 71/74 | 42/45 | 14/22 | 9/19 | 11/17 | 9/12 | 7/12 | | |
| `train-fold-a-plan` correct | 699/708 (98.7 %) | 88/119 (73.9 %) | 24/39 (61.5 %) | 19/30 (63.3 %) | 5/13 (38.5 %) | 10/17 (58.8 %) | 7/10 (70.0 %) | 8/11 (72.7 %) | 699/708 (98.7 %) | 30/51 (58.8 %) |
| `train-fold-a-plan` gold reaches Perception's list | 707/708 | 115/119 | 36/39 | 23/30 | 9/13 | 13/17 | 7/10 | 7/11 | | |
| `dev2000-added-plan` correct | 553/564 (98.0 %) | 77/94 (81.9 %) | 38/51 (74.5 %) | 17/31 (54.8 %) | 13/21 (61.9 %) | 17/22 (77.3 %) | 8/15 (53.3 %) | 7/17 (41.2 %) | 553/564 (98.0 %) | 45/75 (60.0 %) |
| `dev2000-added-plan` gold reaches Perception's list | 564/564 | 93/94 | 50/51 | 21/31 | 17/21 | 20/22 | 10/15 | 9/17 | | |

### B.2 The delivered-but-wrong rows: where gold sat, where the wrong answer sat

| Arm | delivered-but-wrong rows | gold position 1..8 (counts) | mean pos | gold at 5-8 | gold was in Perception's list | wrong answer in the block | wrong answer ABOVE gold | wrong answer at position 1 | ... and gold in the list too | wrong answer in Perception's list | intent-correct rows: position 1..8 | mean pos | at 5-8 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `roll1` | 82 | [6, 20, 15, 9, 11, 7, 6, 8] | 4.02 | 32 | 46 | 75 | 65 | 50 | 29 | 76 | [288, 54, 30, 13, 8, 10, 6, 4] | 1.72 | 28 |
| `train-fold-a-plan` | 86 | [9, 30, 15, 11, 8, 7, 3, 3] | 3.31 | 21 | 59 | 85 | 71 | 67 | 44 | 83 | [699, 88, 24, 19, 5, 10, 7, 8] | 1.42 | 30 |
| `dev2000-added-plan` | 83 | [9, 17, 13, 14, 8, 5, 7, 10] | 4.06 | 30 | 53 | 79 | 67 | 64 | 38 | 82 | [553, 77, 38, 17, 13, 17, 8, 7] | 1.6 | 45 |

### B.3 What the agree-1 reorder does to those rows (offline replay of the rank diagnostic's arithmetic)

Votes are the frozen pool intent labels of the row's own twenty delivered exemplars, self-excluded; weight 1.0 on the recomputed cosine, the rank diagnostic's `agree-1`. The CONV column is the newly delivered rows that are intent-wrong today with gold NOT on Perception's list (the bank's `INTENT-UNCOVERED`), hashed by the registered convention; on Fold A it is checked against the registered roster's id-list sha256.

| Arm | delivered-but-wrong rows | gold moves UP | unchanged | moves down, stays in | drops out of the 8 | lands at position 1 | mean pos before -> after | newly delivered: all rows | correct today | intent-wrong today | CONV analogue (intent-wrong, gold off the list) | CONV entry positions 1..8 | CONV at position 1 | position-matched P(correct) on CONV | id list matches the registered roster | rows whose gold drops out (by class) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | --- |
| `roll1` | 82 | 42 | 13 | 20 | 7 | 25 | 4.02 -> 3.32 | 86 | 23 | 63 | 61 | [20, 9, 13, 7, 6, 2, 2, 2] | 20 | 72.7 % | n/a | 9 {'ENTITY-FP-ONLY': 1, 'ENTITY-MIXED': 1, 'INTENT-WRONG': 7} |
| `train-fold-a-plan` | 86 | 45 | 15 | 24 | 2 | 35 | 3.31 -> 2.6 | 95 | 23 | 72 | 70 | [24, 18, 12, 6, 1, 4, 3, 2] | 24 | 77.8 % | yes (70 rows, sha256 5920bd6c99d1) | 2 {'INTENT-COVERED': 2} |
| `dev2000-added-plan` | 83 | 58 | 15 | 5 | 5 | 40 | 4.06 -> 2.39 | 134 | 31 | 103 | 94 | [31, 26, 16, 4, 4, 8, 4, 1] | 31 | 81.9 % | n/a | 5 {'INTENT-UNCOVERED': 5} |

### B.4 Exemplar block: gold-intent exemplars among the twenty

Rendered position is string order of value ids (arbitrary with respect to similarity); retrieval rank is the sealed cosine order the model never sees.

| Arm | gold-intent exemplars: 0 | 1-2 | 3-5 | 6-10 | 11-20 | first by rank: 1 | 2-3 | 4-8 | 9-20 | first by rendered position: 1-5 | 6-10 | 11-15 | 16-20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `roll1` | 11/60 (18.3 %) | 23/68 (33.8 %) | 39/71 (54.9 %) | 97/132 (73.5 %) | 271/294 (92.2 %) | 340/398 (85.4 %) | 51/78 (65.4 %) | 27/52 (51.9 %) | 12/37 (32.4 %) | 381/463 (82.3 %) | 33/56 (58.9 %) | 9/24 (37.5 %) | 7/22 (31.8 %) |
| `train-fold-a-plan` | 11/47 (23.4 %) | 26/70 (37.1 %) | 54/96 (56.2 %) | 130/163 (79.8 %) | 667/704 (94.7 %) | 726/795 (91.3 %) | 98/131 (74.8 %) | 42/75 (56.0 %) | 11/32 (34.4 %) | 817/916 (89.2 %) | 35/61 (57.4 %) | 21/38 (55.3 %) | 4/18 (22.2 %) |
| `dev2000-added-plan` | 5/49 (10.2 %) | 17/64 (26.6 %) | 49/90 (54.4 %) | 93/147 (63.3 %) | 602/650 (92.6 %) | 640/732 (87.4 %) | 86/131 (65.6 %) | 30/62 (48.4 %) | 5/26 (19.2 %) | 709/818 (86.7 %) | 28/60 (46.7 %) | 18/44 (40.9 %) | 6/29 (20.7 %) |

At fixed count (rows with exactly 1-2, then 3-5, gold-intent exemplars), the same two orderings:

| Arm | count | rendered position 1-5 / 6-10 / 11-15 / 16-20 | retrieval rank 1 / 2-3 / 4-8 / 9-20 |
| --- | --- | --- | --- |
| `roll1` | 1-2 | 13/34 (38.2 %) / 4/14 (28.6 %) / 2/6 (33.3 %) / 4/14 (28.6 %) | 2/12 (16.7 %) / 3/9 (33.3 %) / 8/17 (47.1 %) / 10/30 (33.3 %) |
| `roll1` | 3-5 | 23/38 (60.5 %) / 10/16 (62.5 %) / 3/9 (33.3 %) / 3/8 (37.5 %) | 18/26 (69.2 %) / 9/18 (50.0 %) / 10/21 (47.6 %) / 2/6 (33.3 %) |
| `train-fold-a-plan` | 1-2 | 11/25 (44.0 %) / 3/16 (18.8 %) / 10/17 (58.8 %) / 2/12 (16.7 %) | 6/12 (50.0 %) / 4/9 (44.4 %) / 10/24 (41.7 %) / 6/25 (24.0 %) |
| `train-fold-a-plan` | 3-5 | 37/58 (63.8 %) / 9/17 (52.9 %) / 6/15 (40.0 %) / 2/6 (33.3 %) | 22/37 (59.5 %) / 12/22 (54.5 %) / 16/31 (51.6 %) / 4/6 (66.7 %) |
| `dev2000-added-plan` | 1-2 | 7/25 (28.0 %) / 4/14 (28.6 %) / 4/8 (50.0 %) / 2/17 (11.8 %) | 4/14 (28.6 %) / 5/11 (45.5 %) / 5/18 (27.8 %) / 3/21 (14.3 %) |
| `dev2000-added-plan` | 3-5 | 37/55 (67.3 %) / 3/7 (42.9 %) / 5/16 (31.2 %) / 4/12 (33.3 %) | 16/25 (64.0 %) / 17/33 (51.5 %) / 14/27 (51.9 %) / 2/5 (40.0 %) |

| Arm | intent-wrong rows by gold-exemplar count 0 / 1-2 / 3-5 / 6-10 / 11-20 | delivered-but-wrong rows | intent-correct rows |
| --- | --- | --- | --- |
| `roll1` | [49, 45, 32, 35, 23] | [20, 19, 11, 18, 14] | [11, 23, 39, 97, 271] |
| `train-fold-a-plan` | [36, 44, 42, 33, 36] | [13, 21, 11, 17, 24] | [11, 26, 54, 130, 667] |
| `dev2000-added-plan` | [44, 47, 41, 53, 47] | [9, 13, 11, 19, 31] | [5, 17, 49, 93, 602] |

### B.5 Entity classes: where the first exemplar carrying the missed type sits

| Arm | class | rows | items | first exemplar with the type, rendered position 1-5 / 6-10 / 11-15 / 16-20 / none | by retrieval rank 1 / 2-3 / 4-8 / 9-20 / none |
| --- | --- | ---: | ---: | --- | --- |
| `roll1` | `ENTITY-MIXED` (missed types) | 168 | 235 | [189, 27, 8, 6] / 5 | [146, 43, 27, 14] / 5 |
| `roll1` | `ENTITY-FN-ONLY` (missed types) | 41 | 48 | [38, 8, 1, 0] / 1 | [32, 7, 6, 2] / 1 |
| `roll1` | `CORRECT` (gold types, all hit) | 163 | 160 | [139, 9, 4, 6] / 2 | [135, 16, 7, 0] / 2 |
| `train-fold-a-plan` | `ENTITY-MIXED` (missed types) | 193 | 250 | [206, 14, 4, 6] / 20 | [164, 35, 24, 7] / 20 |
| `train-fold-a-plan` | `ENTITY-FN-ONLY` (missed types) | 84 | 85 | [61, 12, 4, 4] / 4 | [50, 16, 8, 7] / 4 |
| `train-fold-a-plan` | `CORRECT` (gold types, all hit) | 480 | 337 | [311, 20, 4, 0] / 2 | [252, 61, 18, 4] / 2 |
| `dev2000-added-plan` | `ENTITY-MIXED` (missed types) | 195 | 239 | [180, 29, 11, 8] / 11 | [146, 46, 26, 10] / 11 |
| `dev2000-added-plan` | `ENTITY-FN-ONLY` (missed types) | 65 | 72 | [57, 6, 2, 2] / 5 | [36, 18, 9, 4] / 5 |
| `dev2000-added-plan` | `CORRECT` (gold types, all hit) | 398 | 348 | [317, 20, 7, 3] / 1 | [269, 56, 17, 5] / 1 |

## C. The entity residual, split without contacts

Per missed gold entity item (exact-match FN, the official matcher). A same-type unmatched predicted filler is paired to it greedily by normalised edit distance, as the bank does; the pair's predicted filler is then looked up, after the bank's P2r1 folding, in the row's supplied exemplar `type=filler` fields, then as a substring of the supplied exemplar utterances and slot-contract bodies. `available` says whether the GOLD filler itself sat in the supply. `span-related` counts pairs where one filler contains the other.

| Arm | class | items | copied an exemplar filler | in a supplied body's text | not from supply (speech or invented) | type-swapped | ignored, gold available in supply | ignored, gold not in supply | gold available (any) | copied and span-related | not-from-supply and span-related |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| `roll1` | `ENTITY-MIXED` | 235 | 31 (13.2 %) | 24 (10.2 %) | 92 (39.1 %) | 13 (5.5 %) | 40 (17.0 %) | 35 (14.9 %) | 106 | 18 | 50 |
| `roll1` | `ENTITY-FN-ONLY` | 48 | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 25 (52.1 %) | 23 (47.9 %) | 25 | 0 | 0 |
| `roll1` | `INTENT-WRONG` | 111 | 3 (2.7 %) | 9 (8.1 %) | 19 (17.1 %) | 6 (5.4 %) | 44 (39.6 %) | 30 (27.0 %) | 54 | 1 | 13 |
| `train-fold-a-plan` | `ENTITY-MIXED` | 250 | 53 (21.2 %) | 28 (11.2 %) | 75 (30.0 %) | 16 (6.4 %) | 40 (16.0 %) | 38 (15.2 %) | 116 | 34 | 30 |
| `train-fold-a-plan` | `ENTITY-FN-ONLY` | 85 | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 70 (82.4 %) | 15 (17.6 %) | 70 | 0 | 0 |
| `train-fold-a-plan` | `INTENT-WRONG` | 78 | 3 (3.8 %) | 3 (3.8 %) | 6 (7.7 %) | 4 (5.1 %) | 36 (46.2 %) | 26 (33.3 %) | 42 | 1 | 2 |
| `dev2000-added-plan` | `ENTITY-MIXED` | 239 | 42 (17.6 %) | 24 (10.0 %) | 79 (33.1 %) | 23 (9.6 %) | 44 (18.4 %) | 27 (11.3 %) | 108 | 19 | 31 |
| `dev2000-added-plan` | `ENTITY-FN-ONLY` | 72 | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 55 (76.4 %) | 17 (23.6 %) | 55 | 0 | 0 |
| `dev2000-added-plan` | `INTENT-WRONG` | 108 | 4 (3.7 %) | 2 (1.9 %) | 8 (7.4 %) | 11 (10.2 %) | 46 (42.6 %) | 37 (34.3 %) | 57 | 4 | 6 |

## D. Reading

**A. Delivery is persuasion, not admission.** No rail binds the delivered intent to the eight or to the 60: on TRAIN Fold A the deliver node repaired 34 pairs that were outside the legal inventory altogether, the Solver answered outside the eight on 38 rows and was right on 28 of them (73.7 %; ROLL-1 57.1 %, DEV 61.0 %), and 28 correct Fold A rows never received their gold entry at all. What it almost never leaves is Perception's 1-3 list (15 Fold A rows): gold in the block but dropped by Perception converts at 10.0 % (3/30), gold on the list at 93.5 %. The block persuades Perception; the list is what the Solver chooses from.

**B. Position predicts correctness, and the step is between position 1 and everything else.** P(correct | gold at 1) is 98.7 % on Fold A, 73.9 % at 2, 67.4 % pooled over 2-8 and 58.8 % at 5-8 (ROLL-1 98.0 / 62.2 / 46.7 %; DEV 98.0 / 70.5 / 60.0 %). Gold at position 1 reaches Perception's list on 707/708 Fold A rows; at 5-8 on 36/51. The 86 delivered-but-wrong Fold A rows sit at mean position 3.31 against 1.42 on intent-correct rows, only 21 of them at 5-8 -- so they are NOT a low-position tail; they are rows where another entry held the top. The wrong answer was itself in the block on 85 of the 86, ABOVE gold on 71, and at position 1 on 67. Perception shortlisted gold on 59 of the 86, and on 44 of those the Solver still took the position-1 entry over the shortlisted gold; on the other 27 Perception dropped gold before the Solver saw it. Either way the deciding property is which entry is on top, so re-ranking inside the delivered set is a lever on the 86 as much as on the newly delivered rows. The same shape holds on ROLL-1 (50/82 wrong answers at position 1) and DEV (64/83).

**The agree-1 reorder acts on both populations.** Replayed offline, it moves gold UP on 45 of the 86 delivered-but-wrong Fold A rows (35 land at position 1; mean position 3.31 -> 2.6), leaves 15 unchanged, moves 24 down inside the block and drops 2 out (ROLL-1: 42/82 up, 25 to position 1; DEV: 58/83 up, 40 to position 1). It newly delivers 95 Fold A rows: 23 already correct without the entry, 72 intent-wrong today, of which 70 are the registered CONV roster (intent-wrong with gold off Perception's list, the bank's `INTENT-UNCOVERED`; the id list hashes to the registered roster: yes), entering at positions [24, 18, 12, 6, 1, 4, 3, 2] -- 24 of 70 at position 1.

**The exemplar block: the COUNT of gold-intent exemplars is the signal; neither ordering shows a stable position effect.** Across all rows P(correct) climbs with how many of the twenty carry the gold intent (23.4 % at 0 to 94.7 % at 11-20 on Fold A; the same on both other rosters), and the raw rendered-position gradient (89.2 % at 1-5, 22.2 % at 16-20 on Fold A) is that count in disguise, because a row with many gold exemplars has its first one early under any ordering. Held at a fixed count (1-2, then 3-5 gold exemplars; six roster-by-count cells, bucket sizes from 11 rows), the bucket rates move by 2.0-42.1 pp across rendered-position buckets and by 7.9-31.2 pp across retrieval-rank buckets, and they are monotone in only 2 of 6 cells for rendered position and 3 of 6 for retrieval rank -- movement of the size of the cells' own sampling noise, in no consistent direction. Two facts stand regardless: the block is rendered in string order of value ids (`_fuse_supply_filter`, kb_policy.py:859), so the rank the retrieval computed never reaches the model; and the agreement vote, which the Solver only ever sees as an unordered pile, is the strongest single correlate of intent correctness in this table. On the entity classes the first exemplar carrying the missed type sits where it sits on correct rows: position is not the entity story.

**C. The entity residual splits, and copying from the supply is the smallest part.** Fold A ENTITY-MIXED, 250 missed items: 53 (21.2 %) carry a same-type filler that string-matches a supplied exemplar filler (34 of those are also span-related to gold, so the match may be coincidence), 28 (11.2 %) a filler found only inside a supplied body's text, 75 (30.0 %) a filler in no supplied body -- speech or invention, 30 of them span-related to gold -- 16 (6.4 %) the gold filler under another type, and 78 (31.2 %) no filler of the type at all, 40 of them with the gold filler sitting in the supply. ENTITY-FN-ONLY is 'ignored' by construction (no unmatched prediction exists to pair), and its informative split is 70/85 with the gold filler available in the supply. ROLL-1 and DEV carry the same shape (copied 13.2 % / 17.6 %). Used-but-wrong-source is one item in five at most; the residual is span boundary and omission.

**Re-aim, and the honest prior.** Presence is the wrong target once an entry is inside the block; SALIENCE is -- being the top entry of the eight decides Perception's list and, through it, the Solver's pick, on every roster. The retrieval line should be aimed at rank inside the delivered set, which the agreement term already moves, not at presence alone. The exemplar block is a different case: its rendered order is string order today, and this read finds no stable position effect at fixed count, so whether ordering it by rank buys anything is an open and cheap question rather than an evidenced lever; what that block demonstrably carries is the count of gold-intent exemplars, which is the agreement vote. For the CONV probe the record now holds four numbers where it held a midpoint: the naive P(intent correct | gold delivered) on Fold A is 90.9 % (860/946, the complement of the 86); the flown conversion at the positions the 70 CONV rows would enter is 77.8 %; gold delivered but NOT at position 1 converts at 67.4 %; and gold on Perception's list converts at 93.5 % while gold in the block but off the list converts at 10.0 %. The honest prior is the position-matched 77.8 %, bounded above by 90.9 % and below by the not-top rate 67.4 %; the declared persuasion factor of 0.5 sits below the whole band. It is still a prior and not a measurement, because every number above is read on rows whose cosine already ranked gold, and the CONV rows are exactly the rows where it did not. At 77.8 % the expected conversions are 54.5 of 70 against the 61 the AGREE arm needs to clear its bar, so the probe sits close to the decision it was flown to make.

## E. Boundary

Zero model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid-API contacts: no server was started, stopped or probed, no waveform decoded, no embedding computed and no subprocess run. Tools: `json` reads of three sealed `*.phases.json`, `*.outputs.jsonl` and `*.trace.jsonl` (ids only kept from the trace), the sealed bank and the ROLL-1 official score file; `data.slurp.load_slurp_split` for TRAIN and DEVEL gold; `rails.slurp_projection_v3.apply_slurp_projection_v3_delivery` and `reproduction.slurp_scoring.parse_slu_response` over delivered text in-process; the rank diagnostic's own cosine recomputation over the pinned vector files for the agree-1 replay; `hashlib` for every hash. This read admits nothing, promotes nothing, preregisters no cell, releases no store, draws no roster and reaches no superiority, generalisation or Stage-3 conclusion. Byte-reproducible apart from `generated_at`.
