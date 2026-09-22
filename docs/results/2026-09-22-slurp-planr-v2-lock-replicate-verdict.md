# REPLICATED (NEUTRAL) -- cell PLANr: the request-identical replicate of the default-plan arm, SLURP TRAIN Fold A, 1,080 rows

**The pair (PLAN, PLANr) replicates within the plan's own null, and this read reaches NEUTRAL.** Both
gating guards are non-inferior at the registered margins, neither shows a measured loss, and both
point estimates are positive with CI95s that include zero -- exactly what a request-identical second
pass should show. The two CI95 half-widths of this contrast ARE the plan's own null (owner decision
38); every later cell on the locked plan reads at these margins. With this replication the v2.0 lock
record is written (`docs/results/2026-09-22-slurp-v2-lock-v1.md`), superseding the provisional lock
of 2026-09-20.

Read 2026-09-22 by the coordinator, model-free, from the sealed bytes of five flights (the arm, the
comparator PLAN, the lock B5e, and the two B1 own-null arms). Status, tables and every number below
are the output of the stage driver `plan_cell_read.py`
(`72952d20a22dbeea5e0f67e4343c25a3f74fbea28451fd39b938b36877443af3`) run with the PLAN-derived
registered facts file `registered-planr.json`, execution profile `model-free-check`, analysis root
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-REPLICATE-PAIRED-ANALYSIS-V1/`, stages
stop / structural / contrast / lock / efficiency / frontier / verdict (23:48 to 00:20 UTC).

**Exposure.** Zero model, tokenizer, encoder, ASR, server, GPU, paid-API and network contacts. Five
registered model-free scorings over **copies** of sealed bytes under this read's own output root
(the official scorer on the arm and the comparator, the projection-v3 and the TRAIN symmetric
siblings). No sealed file was opened for writing, moved or renamed. No run directory,
exposure-ledger row, harness-admission receipt or results-ledger row was edited by the read itself;
the closures below were written afterwards by the coordinator. No utterance text, transcript, gold
filler or model output is printed here.

**Claim boundary.** Development numbers only (owner decisions 28 and 86: no development bar exists;
the 64 / 78 figures are test-set targets read once after Stage 3). Official SLURP `evaluate.py` at
its pinned commit `8eb16545762be97ace75334109d73824217311f1` on **TRAIN Fold A**, 1,080 rows, 18
scenarios of 60, 125 speaker clusters. Nothing here is a test claim, a superiority claim, a
generalisation claim, a component-causal claim, a cross-carrier claim or a geometry claim.

## 0. The replication statement

| | official pooled SLU-F1 | intent | scenario | action | span-F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| cell PLAN (the arm flown first; the sealed comparator of every Stage-3 cell) | 63.6304 | 82.2222 | 87.3148 | 83.5185 | 53.7755 |
| **cell PLANr (this replicate)** | **63.8048** | **82.5000** | **87.6852** | **83.7963** | **53.1120** |
| PLANr minus PLAN, paired | +0.1744 | +0.2778 | +0.3704 | +0.2778 | -0.6635 |

Source: `score-contrasts.json` (`fda0ca2dc5baec08bc2b659158e46d0af3f4a8e2b5041fb118ba3a67fe5c0e15`),
`official_aggregates`; both aggregates reproduce from the per-row files to 1e-6 (`consistency_check`),
and PLAN's registered aggregates reproduce exactly (`registered_aggregate_reproduction`).

**Replication verdict: MET.** Both deltas sit inside the registered margins with CI95s that include
zero (section 1); no scenario loses beyond its band (section 5); the trajectory, disposition and
cost profiles agree (sections 6 and 7). The plan is reproducible under greedy decoding to within its
own null, which is the decision-30 / decision-57 condition for the lock.

## 1. Gating contrast, PLANr against the sealed PLAN arm (the plan's own null)

Paired whole-speaker bootstrap, 10,000 draws, seed 20260915, 125 speaker clusters; margins = cell
B1r's own null (h_SLU 1.2350, h_intent 1.2212; both reproduced to the registered digits by this read).

| guard | PLAN | PLANr | delta pp | CI90 | CI95 | saves / harms / ties | non-inferior at h | gain proven |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| official pooled SLU-F1 (primary) | 63.6304 | 63.8048 | **+0.1744** | [-0.878, +1.182] | **[-1.114, +1.383]** | per-row SLU 48 / 60 / 972 | yes (lower bound -1.114 > -1.235) | no |
| intent (scenario_action) | 82.2222 | 82.5000 | **+0.2778** | [-0.580, +1.101] | **[-0.736, +1.252]** | 15 / 12 / 1,053 (McNemar p 0.70) | yes (lower bound -0.736 > -1.221) | no |
| equal-scenario weighting | | | SLU +0.459, intent +0.278 | | | | | |

**The plan's own null (decision 38), from this contrast:**

| metric | CI95 half-width = margin h for every later cell on the locked plan |
| --- | ---: |
| official pooled SLU-F1 | **1.2485** |
| intent accuracy | **0.9943** |

These supersede B1r's 1.2350 / 1.2212 for every comparator that is the sealed PLAN arm. The SLU
half-width is 1 % wider than B1r's and the intent half-width 19 % narrower.

Under the projection-v3 scorer the two arms read 63.8048 / 82.5000 and 63.6304 / 82.2222 -- identical
to the official numbers, because both arms already carry the v3 normaliser node at delivery (the v3
projection is idempotent on their outputs). Under the TRAIN symmetric scorer (`slurp-slu-f1-normalized-v1-train`)
the sign agrees (`train_symmetric_contrasts`; 34 symmetric false merges on each arm).

## 2. Lock comparison (reported, never a gate)

| PLANr against | lock side (SLU / intent) | SLU delta pp, CI95 | intent delta pp, CI95 | shortfall beyond the own null |
| --- | --- | --- | --- | --- |
| the provisional lock B5e + node applied model-free (the 2026-09-20 record) | 63.7757 / 81.8519 | +0.029 [-1.349, +1.406] | +0.648 [-0.522, +1.859] | none |
| the provisional lock's official arm B5e (as flown) | 62.3351 / 80.0926 | +1.470 [+0.086, +2.897] | +2.407 [+1.250, +3.615] | none |

Source: `lock-comparison.json` (`bac16d81d2db0f90fcfa0e80d0b28a9e0879f1eeca097c6cf8d83f8fb56245e5`). The
node-applied lock numbers reproduce exactly (63.7757 / 81.8519). Parity with the provisional lock
on SLU; the plan's advantage over the provisional lock is intent, as the PLAN read found.

## 3. Frontier row (owner decision 75)

| cell | official SLU | official intent | prefilled tokens per row (estimate) | GPU hours per 1,080 | contacts per row | contacts per minute |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B1-notool (base; remeasured) | 62.1295 | 80.0000 | 8,020 | 1.611 | -- | -- |
| PLAN (comparator; remeasured by this read) | 63.6304 | 82.2222 | 8,353 | 1.758 | 4.096 | 38.2 |
| **PLANr** | **63.8048** | **82.5000** | **8,321** | **1.665** | **4.064** | **40.1** |

PLANr sits on both Pareto planes (`frontier.json`
`b64425095948731d0d148ea32732c01ec4b40f37d69b5545610c6c90b37104c4`): the same quality at 5.3 % fewer
GPU hours than PLAN, 0.8 % fewer contacts per row, and 32 fewer prefilled tokens per row. The
difference is the realised revision count (26 rows with at least one REVISE against PLAN's 38),
i.e. greedy-decoding drift of the Planner, not a plan change. Projected test read of 13,078 rows at
this rate: 20.2 GPU hours (PLAN: 21.3).

## 4. E20 compaction diagnostic (mandatory)

`compact-or-abstain` armed; **0 rows and 0 contacts compacted**, no dropped items, one receipt per
row, receipts agree with the flight receipt (`compaction.json`
`46ccb5424feb07e15f514779d98fc5cd6319987de2b9af58aa2091c74ffdec9a`). The outcome split is not
comparable (no compacted rows). Same as PLAN.

## 5. Per-scenario intent table (natural mixture; 60 rows per scenario)

| scenario | PLAN | PLANr | delta pp (PLANr minus PLAN) | CI95 | saves / harms | flagged |
| --- | ---: | ---: | ---: | --- | --- | --- |
| alarm | 88.33 | 86.67 | -1.67 | [-6.52, +0.00] | 1 / 2 | no |
| audio | 76.67 | 78.33 | +1.67 | [+0.00, +2.83] | 1 / 0 | no |
| calendar | 80.00 | 81.67 | +1.67 | [+0.00, +5.56] | 1 / 0 | no |
| cooking | 85.00 | 90.00 | +5.00 | [+0.00, +10.71] | 3 / 0 | no |
| datetime | 90.00 | 88.33 | -1.67 | [-7.58, +3.45] | 1 / 2 | no |
| email | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | 0 / 0 | no |
| general | 43.33 | 48.33 | +5.00 | [+0.00, +11.48] | 3 / 0 | no |
| iot | 88.33 | 86.67 | -1.67 | [-5.36, +0.00] | 0 / 1 | no |
| lists | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | 0 / 0 | no |
| music | 80.00 | 80.00 | +0.00 | [-5.00, +5.00] | 1 / 1 | no |
| news | 83.33 | 83.33 | +0.00 | [-5.08, +5.00] | 1 / 1 | no |
| play | 88.33 | 85.00 | -3.33 | [-8.62, +0.00] | 0 / 2 | no |
| qa | 75.00 | 75.00 | +0.00 | [+0.00, +0.00] | 0 / 0 | no |
| recommendation | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | 0 / 0 | no |
| social | 73.33 | 75.00 | +1.67 | [-3.57, +7.55] | 2 / 1 | no |
| takeaway | 85.00 | 83.33 | -1.67 | [-5.00, +0.00] | 0 / 1 | no |
| transport | 88.33 | 88.33 | +0.00 | [-5.36, +4.05] | 1 / 1 | no |
| weather | 93.33 | 93.33 | +0.00 | [+0.00, +0.00] | 0 / 0 | no |

Zero scenarios lose beyond the null band; zero decision-17 flags (`per-scenario-tables.json`
`0103e409dc4a3264c84728c5dff3caa02e40c5868831abd6de05f248d52a8864` carries every scenario's full
row, both weightings and the SLU table).

## 6. Structural counts

| count | PLAN | PLANr |
| --- | ---: | ---: |
| contacts | 4,424 | 4,389 |
| rows with at least one REVISE | 38 | 26 |
| finite-completion (E13) rows | 10 | 9 |
| planner_action_illegal rows | 1 | 0 |
| react_exhaustion (E22) rows | 0 | 0 |
| rows changed by the v3 normaliser node (label / filler) | 102 | 105 (37 / 71) |
| requests carrying a tools array / tool calls | 0 / 0 | 0 / 0 |
| slot-contracts v2 release pin verified | yes | yes |
| trace sha256 | bbebb22f... | 53356d23... |

Source: `structural.json` (`be095a95dbcebd26105152fd24e931c4f468f354837703bfef043c94d2b0e9bf`). The
Perception request delta against PLAN stays inside the armed key set (request-identical replicate).

## 7. Efficiency and cost

| | PLAN | PLANr |
| --- | ---: | ---: |
| generation wall | 6,946 s | 6,570 s |
| GPU-active seconds | 6,328 | 5,996 |
| GPU hours (fit-inclusive, per 1,080) | 1.758 | 1.665 |
| contacts per minute | 38.2 | 40.1 |
| completion tokens | 263,684 | 258,692 |
| average latency per contact | 4.95 s | 4.96 s |
| prompt-cache hit share | 0.7545 | 0.7529 |
| run-cumulative calls / speech seconds | 4,424 / 12,652 | 4,389 / 12,525 (within the 11,880 / 33,930 ceilings) |

Source: `efficiency.json` (`99e05ddf4a1166ee82a62164a5b488ec6e3364ff41f67a9712e39a4ddc4f07c5`).

## 8. Process notes

- The driver's `DEFAULT_REGISTERED` facts are PLAN's (the arm-vs-B1-notool read); the first PLANr
  attempt of the stop stage refused with "a sealed comparator does not reproduce its registered
  aggregate" because the comparator of this read is PLAN itself. The coordinator built
  `registered-planr.json` from PLAN's sealed `score-contrasts.json` / `efficiency.json` (comparator
  aggregates, cost reference, knowledge pins, the PLAN frontier row, the PLANr authority relpaths)
  and re-ran; the driver reproduced every registered fact. The `--registered` override is the
  reusable form; a per-cell facts file should be part of every registration from now on (item E34).
- The latent `_score_copies` digest-check defect noted in the PLAN verdict is still open; the copies
  were audited byte-identical to the sealed outputs on this read as well (outputs sha256
  `17f0bc02...` arm, `2dcaa925...` comparator).

## Artefacts

Analysis root `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-REPLICATE-PAIRED-ANALYSIS-V1/`:
`score-contrasts.json` fda0ca2d..., `lock-comparison.json` bac16d81..., `frontier.json` b6442509...,
`efficiency.json` 99e05ddf..., `per-scenario-tables.json` 0103e409..., `structural.json` be095a95...,
`compaction.json` 46ccb542..., `registered-planr.json`, stage logs, `README.md` d0767458....
Arm: run `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1`, FINALIZED at study commit e367a629,
run-manifest a8451e05..., scores 8083795d..., outputs 17f0bc02.... Package
`docs/readiness/2026-09-21-slurp-default-plan-lock-replicate-v1/`.
