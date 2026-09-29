# Cell G5 (Reviewer instruction without the retired-tool order) paired read on TRAIN Fold A: intent +0.09 pp CI95 [-1.02, +1.20], official SLU-F1 -0.38 pp [-1.78, +1.04] against the shared in-chain A/A; Reviewer tool narration 1,088 -> 0 (DESCRIPTIVE)

Read on 2026-09-29 by the records and read agent (Claude Opus 5.5, on the coordinator's brief, Fable 5.1), in
worktree `fable/g5read`. The read is model-free. `core.flight.cli` and `lease_cli` were not invoked. There were no
model, server, encoder, embedder, tokenizer or GPU contacts. The read ran as a CPU sidecar while the queue driver
flew COMP-1b.

The READ row `SAEA-SLURP-STAGE3-G5-FOLD-A-PAIRED-ANALYSIS-V1` was root countersigned before the flight
(2026-09-27 15:28 UTC). On master at `dfb5c0121` (2026-09-29T19:07:33Z) it gained a post-seal confirmation clause.
That was after the seal and before any G5 score was opened. The root act was delegated by the coordinator, under
owner decisions 153, 160 and 189.

The recipe is `docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1/analysis-recipe-v1.json` (recipe id
`slurp-stage3-g5-fold-a-paired-analysis-v1`). It is a paired row bootstrap: cluster key `sample_id`, 10,000 draws,
seed 20260927.

No utterance text, gold label, slot filler, Reviewer text or model output was printed or persisted. Only counts,
rates, pp, scenario names, ids and hashes appear below.

**DESCRIPTIVE.** These are development numbers on a TRAIN construction fold (owner decisions 28 and 86). They are
never a test claim or a generalisation claim. G5 is a no-harm base item (decision 127): it is never reported as a
gain. The verdict word belongs to the coordinator (decision 139).

## 1. What flew

| run | attempt | rows | contacts | speech s | prompt / completion tokens | GPU-h (monitor) | state |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| G5 arm `SAEA-SLURP-STAGE3-G5-FOLD-A-V1` | `attempt-slurp-native-stage3-g5-fold-a-generation-v1` | 1,080 | 4,413 | 12,643.756 | 36,637,492 / 232,894 | 1.6013 | COMPLETED, FINALIZED, clean tree |
| shared in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` (decision 160) | `attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1` | 1,080 | 4,435 | 12,614.317 | 36,919,108 / 264,299 | 1.6786 | COMPLETED 2026-09-28 |

- **Flight.** The G5 arm flew at commit `fd8a01fe` in the COMP-1 seal-only + G5 chain (`queue_sealonly.sh`). The
  campaign started 14:46:23Z. The manifest was created 2026-09-29T16:26:16Z. The arm-inspect passed at 16:27:48Z
  with no fails, and the chain exited 0 at 16:28:10Z. The four-row smoke passed inspect at 14:46:13Z; it is never
  scored.
- **Seal hashes.** Run manifest `21de9d29...a472`, outputs `5a4fe01a...2766`, scores `b050f8dc...c18f`.
- **The comparator.** The shared A/A is the comparator named in the G5 recipe (`arms.in_chain_replicate`). It was
  proven byte-identical to G5's superseded own A/A before any flip (`shared-aa-proof-v1.json`, verdict `IDENTICAL`).
  G5's own A/A pair stays SUPERSEDED UNFLOWN.

The registered driver `scripts/flights/read_paired_cell.sh` on the G5 package ran unchanged. It wrote both passes
under `analysis/SAEA-SLURP-STAGE3-G5-FOLD-A-PAIRED-ANALYSIS-V1/`:

- `vs-aa`, the gating pass: verdict `581eb015...9f03179`.
- `vs-comparator`, against the sealed PLAN arm, context only: verdict `d671134d...aabc6c5`.

## 2. The gating contrast: G5 minus the in-chain A/A

| metric | A/A | G5 | delta pp | CI95 pp | CI90 pp | saves / harms |
| --- | ---: | ---: | ---: | --- | --- | --- |
| intent (scenario_action_exact) | 81.85 | 81.94 | **+0.09** | [-1.02, +1.20] | -- | 20 / 19 |
| official pooled SLU-F1 (micro) | 64.21 | 63.83 | **-0.38** | [-1.78, +1.04] | [-1.57, +0.81] | -- |
| span-F1 (micro) | 53.86 | 53.66 | -0.20 | [-1.82, +1.45] | [-1.55, +1.15] | -- |
| row SLU-F1 | 42.66 | 41.79 | -0.86 | [-1.85, +0.10] | -- | 44 / 50 |

The unrounded CI95 lower bounds are intent -1.0185 and SLU-F1 -1.7799.

| weighting | intent delta pp | intent CI95 | SLU-F1 delta pp | SLU-F1 CI95 |
| --- | ---: | --- | ---: | --- |
| natural mixture | +0.09 | [-1.02, +1.20] | -0.38 | [-1.78, +1.04] |
| equal scenario | +0.09 | [-1.11, +1.20] | -0.49 | [-2.30, +1.20] |

By channel, intent is far-field +0.72 and headset -0.57. Row SLU-F1 is far-field -1.05 and headset -0.67.

**Beside it (context, never the bar): G5 minus the sealed PLAN arm.**

- Intent 82.22 -> 81.94: -0.28 pp, CI95 [-1.30, +0.74], 15 saves / 18 harms.
- Official SLU-F1 63.63 -> 63.83: +0.20 pp, [-1.17, +1.67].

### Per-scenario (G5 minus A/A)

| scenario | n | intent A/A -> G5 | delta pp | CI95 | SLU-F1 A/A -> G5 | delta pp | CI95 |
| --- | ---: | --- | ---: | --- | --- | ---: | --- |
| alarm | 60 | 90.00 -> 88.33 | -1.67 | [-5.00, 0.00] | 75.64 -> 77.87 | +2.23 | [-1.10, 5.86] |
| audio | 60 | 80.00 -> 80.00 | 0.00 | [0.00, 0.00] | 66.52 -> 64.15 | -2.37 | [-8.49, 0.00] |
| calendar | 60 | 78.33 -> 78.33 | 0.00 | [-5.00, 5.00] | 67.61 -> 65.96 | -1.65 | [-5.76, 2.38] |
| cooking | 60 | 85.00 -> 85.00 | 0.00 | [-6.67, 6.67] | 57.42 -> 63.00 | +5.58 | [0.50, 12.14] |
| datetime | 60 | 88.33 -> 88.33 | 0.00 | [-8.33, 8.33] | 71.34 -> 75.27 | +3.92 | [-2.83, 11.68] |
| email | 60 | 85.00 -> 86.67 | +1.67 | [0.00, 5.00] | 62.49 -> 63.62 | +1.13 | [-4.37, 6.44] |
| general | 60 | 43.33 -> 41.67 | -1.67 | [-10.00, 5.00] | 32.56 -> 26.09 | -6.47 | [-25.79, 10.70] |
| iot | 60 | 88.33 -> 86.67 | -1.67 | [-5.00, 0.00] | 67.06 -> 67.77 | +0.71 | [-5.34, 6.19] |
| lists | 60 | 80.00 -> 85.00 | +5.00 | [-1.67, 11.67] | 58.60 -> 54.14 | -4.47 | [-16.49, 6.74] |
| music | 60 | 78.33 -> 80.00 | +1.67 | [0.00, 5.00] | 47.85 -> 49.99 | +2.13 | [-3.71, 8.73] |
| news | 60 | 83.33 -> 80.00 | -3.33 | [-8.33, 0.00] | 64.27 -> 65.53 | +1.26 | [-6.42, 10.47] |
| play | 60 | 83.33 -> 85.00 | +1.67 | [0.00, 5.00] | 54.50 -> 53.70 | -0.81 | [-3.84, 2.05] |
| qa | 60 | 78.33 -> 80.00 | +1.67 | [-3.33, 8.33] | 59.98 -> 62.80 | +2.82 | [-0.77, 7.30] |
| recommendation | 60 | 91.67 -> 90.00 | -1.67 | [-5.00, 0.00] | 71.20 -> 69.10 | -2.10 | [-7.91, 3.44] |
| social | 60 | 73.33 -> 73.33 | 0.00 | [-5.00, 5.00] | 59.32 -> 59.27 | -0.04 | [-2.33, 2.07] |
| takeaway | 60 | 86.67 -> 86.67 | 0.00 | [-5.00, 5.00] | 61.55 -> 57.21 | -4.34 | [-9.06, -0.53] |
| transport | 60 | 86.67 -> 86.67 | 0.00 | [-5.00, 5.00] | 69.13 -> 66.28 | -2.85 | [-8.28, 1.65] |
| weather | 60 | 93.33 -> 93.33 | 0.00 | [0.00, 0.00] | 75.82 -> 72.28 | -3.54 | [-10.25, 0.60] |

**Delivery.** The intent-boundary item was delivered on 947 rows on both arms, with 0 newly delivered and 0 newly
lost. The first-phase supply is unchanged, as the byte-identity expectation required. Among the delivered-in-both
rows, 12 went wrong -> right and 11 right -> wrong. Among the delivered-in-neither rows, 8 went each way.

## 3. Reviewer reach, repairs vs breaks, and the byte checks

Driver: `scripts/analysis/slurp_g5_reviewer_reach_read.py` (new on this branch; model-free). Output:
`analysis/SAEA-SLURP-STAGE3-G5-FOLD-A-PAIRED-ANALYSIS-V1/reviewer-reach/report.json` (`e68b6035...ffd9`). Sealed
`phases.json` agent states, the delivered outputs, and TRAIN gold read offline on the scoring side only:

| quantity | A/A | G5 |
| --- | ---: | ---: |
| Reviewer visits (phases) | 1,111 | 1,111 |
| Reviewer contacts (trace) | 1,122 | 1,111 |
| rows by Reviewer visits: 0 / 1 / 2 | 9 / 1,031 / 40 | 0 / 1,049 / 31 |
| Planner routes ACCEPT / REVISE | 1,067 / 44 | 1,075 / 36 |
| rows revised (more than one Solver answer) | 42 | 31 |
| **Reviewer responses narrating a tool call or result** | **1,088** (on 1,052 rows) | **0** (0 rows) |
| first Solver answer intent correct | 867 | 861 |
| delivered intent correct | 884 | 885 |
| intent repairs (first wrong -> delivered right) / breaks | 20 / 3 | 25 / 1 |
| of which on revised rows | 7 / 3 | 6 / 1 |
| intent changed, first -> delivered | 32 | 43 |
| entity-set repairs / breaks (exact multiset vs gold) | 29 / 10 | 27 / 2 |
| entities changed, first -> delivered (revised rows) | 93 (26) | 77 (13) |
| Reviewer prompt tokens per contact, mean / median | 9,796.43 / 10,066.5 | 9,749.62 / 9,996 |

Tool narration uses the regex of `scripts/analysis/slurp_reviewer_credit_table.py`.

- **Net repair.** The loop's net intent repair is +17 on the A/A (20 - 3) and +24 on G5 (25 - 1). Net entity-set
  repair is +19 on the A/A and +25 on G5.
  The A/A's trace carries 11 more Reviewer contacts than its phases record visits, and 9 of its rows
  record no Reviewer visit. Neither was investigated here.
- **Byte checks.** The instruction deletion was proven at registration:
  - 82 -> 31 tokens, -51 per Reviewer contact, deletion-only diff;
  - instruction file sha256 `724a437d...cef35`;
  - the first-phase supply digest `ba5e1faa...` unchanged, which the equal delivery counts above corroborate.
- **In flight.** The Reviewer prompt-token delta per contact is -46.81 (mean) and -70.5 (median). That is
  consistent with the declared -51, not equal to it: the two arms' Reviewer requests also differ in the Solver
  draft they review (cross-flight decode), so the flown delta is not a pure byte measure. Per row, prompt tokens
  fall by 260.8 and prefilled tokens by 80.2. GPU-h falls from 1.6786 to 1.6013 per 1,080 rows (monitor).
- **Tool calls.** 0 tool schemas and 0 tool calls on both arms (structural stage).

## 4. The rule and the verdict

The registered rule is NO-HARM (decision 127). G5 is ADMITTED iff:

- the intent CI95 lower bound is at or above -0.9943, and
- the SLU-F1 CI95 lower bound is at or above -1.2485.

It is HARMFUL iff either upper bound is below zero. Otherwise it is NOT ADMITTED by width. The declared expectation
is `expected_effect_pp` 0.0 and `claims_benefit` false: a base item read for no harm, never for a gain.

**Verdict (read agent, for the coordinator):**

- **NOT ADMITTED (width).** Intent lower bound -1.0185 is under the margin -0.9943, by 0.024 pp. SLU-F1 lower bound
  -1.7799 is under -1.2485, by 0.531 pp.
- **Not HARMFUL.** Both upper bounds are above zero: intent +1.20, SLU-F1 +1.04.
- Both point estimates sit inside the A/A null: intent +0.09, SLU-F1 -0.38.
- The repair did what it names. Reviewer tool narration fell 1,088 -> 0. The REVISE routes fell 44 -> 36, and net
  intent repair rose +17 -> +24. The cost fell 0.077 GPU-h per 1,080 rows.
- Under step 7 of the recipe, an unadmitted pin is withdrawn from COMP-2. The coordinator decides whether the
  narration result and the 0.024 pp intent shortfall warrant a replicate on the same roster (decision 2026-09-03
  "replicate before a fresh roster") before the withdrawal.

The coordinator's clause and the disposition are pending. Nothing is admitted.

## 5. Reproduce

```bash
# model-free; worktree fable/g5read
SAEA_REPO_ROOT=$PWD bash scripts/flights/read_paired_cell.sh docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src python -B scripts/analysis/slurp_g5_reviewer_reach_read.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```

## Coordinator verdict (Fable 5.1, 2026-09-29)

- **G5 Reviewer instruction repair: NOT ADMITTED (width), no harm.** Intent +0.09 [-1.02, +1.20], SLU-F1 -0.38 [-1.78, +1.04] vs the shared in-chain A/A; the form fix works (tool narration 1,088 -> 0 responses; Reviewer prompt tokens -46.8 per contact against the declared 51; GPU-h 1.68 -> 1.60) but reach and repairs move inside the null (REVISE 44 -> 36; intent repairs/breaks 20/3 -> 25/1).
- **Line status.** The Reviewer/Planner node shows no information gain for the third time (decision 188, B5 deferred; node-gain ledger). G5 is classed as a no-harm efficiency item: it enters the consumption module's lock layer only at a lock revision (v2.x), never as a gain component. Development number (decisions 28/86).
