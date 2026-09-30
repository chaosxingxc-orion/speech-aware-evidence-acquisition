# Cell P-SV-1 (same-flight Perception branch, top2-contrast note) branch read: b-top2contrast vs a-agree level-2 official intent -0.19 pp CI95 [-0.56, +0.19] against a twin intent bar of 0.42 pp; level-1 top1 -1.67 pp [-2.96, -0.37], present -1.85 pp [-2.96, -0.83] on TRAIN Fold B (DESCRIPTIVE)

Read 2026-09-29 by Claude Opus 5.5 (records and read agent) in the worktree `fable/psv1read` (model-free;
`core.flight.cli` and `lease_cli` were not invoked; no GPU, model, server, encoder or tokenizer contact; three
official column scorings). READ row `SAEA-SLURP-STAGE3-PSV1-FOLD-B-BRANCH-READ-V1` and its seal-only reading
clause were root countersigned 2026-09-29T22:59:27Z (master `440a71402`), after the seal-only completion sealed
(2026-09-29T20:49:26Z) and before any branch column score existed. Recipe
`docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/analysis-recipe-v1.json` (sha256
`cc3555137bcd61eb4b95548aa3c82c86dec616ed33193d21dd471cb4226afeda`), recipe id
`slurp-stage3-psv1-fold-b-sealonly-branch-analysis-v1` (parent recipe
`slurp-stage3-psv1-fold-b-branch-analysis-v1`, sha256 `e99efa42...`). Paired row bootstrap, cluster key
`sample_id`, 10,000 draws, seed 20260929, TRAIN gold through the governed loader and
`slurp-slu-official-train`. Owner decisions 184 (the read form), 193 and 197 (the seal-only completion).

The driver was `scripts/flights/psv/psv_read.sh psv1` (sha256
`4566e59e958fb1186d204229815c81e34327162b465471845aa7aa1ce86f6a2c`, merged at `7d1b44ab1`; run once, rc 0,
with `SAEA_REPO_ROOT` pointed at this worktree; a `--dry-run` preceded it; no `--rescore`). It called
`scripts/analysis/slurp_perception_branch_read.py` (sha256
`499598f3726f97e2050c1d2bd8424afe2ab943be3e45376e91a71de3ddbe626e`).

Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PSV1-FOLD-B-BRANCH-READ-V1/`:

- receipt `perception-branch-read.json` (schema `saea-perception-branch-read-v1`) sha256
  `8afee3d4b3cbce8d4b42ef425f8a8d4791c0e3dbb6403cc1b0d81d0f739b8d92`;
- `twin-null/`: `verdict.json` `417858130fde4280d9dbff8d0d3cddde9ae4fdd9cab1c327bb9b26c31175b51d`,
  `score-contrasts.json` `753fffc16e18e9e8260ddae3495fb68d0f1d8fe7f6989790c1e2299279a6476d`,
  `per-scenario-tables.json` `c92c9eca930eb5864d7c7e2623092347d842f6e6ab6ad04ee2cb7907f3158342`;
- `branch/`: `verdict.json` `04433910bd73b487c4c425e547b0ef2e454f16ef6c18d822b7cef932bc3b3774`,
  `score-contrasts.json` `19261d59bbf27b7c66a07763a85e2be83f8e30b9a17fa1644525f74509f41bd0`,
  `per-scenario-tables.json` `cac4fcc3be62a3ebb4fbae62465f9fe35b24524a1c5e72225fe2684de8d29176`;
- the three column scorings: `supply-variants/score-summary.json` under the sealed attempt, sha256
  `10faee03d96adf3bceaaf34275f3da9176bc9e4b6edcb7df57bd1e1d5565845c`.

No utterance text, gold label, slot filler, note text or model output was printed or persisted. Only counts,
rates, deltas, ids and hashes appear below.

**DESCRIPTIVE.** This note gives the numbers and says which side of the pre-declared rule they fall on. The
verdict word belongs to the coordinator (decision 139). These are development numbers on a TRAIN construction
fold (decisions 28 and 86), branch-local, never a system-level or test claim. The claim ceiling is
"nominated"; a nomination admits nothing.

## 1. What was read

Run `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1`, sealed through the seal-only attempt
`attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only` (owner decision 197): 1,080 rows kept from the
aborted attempt `attempt-slurp-native-stage3-psv1-fold-b-generation-v1` (predecessor trace
`0c1edb20c37756ec8567fbba8edc56d8ff24ce3ea32b94bccad8c3667285d20a`), 0 flown, 0 new contacts. Run manifest
sha256 `122cd5f17b54d6c3ba4b5addd60022e2702b867be2e9f412703967fd99dbce17`, outputs
`3d97b42bd14889a9c673f1f0981538273abe818f6e36c50b11c45cc6fa75357e`.

The seal-only completion sealed before the E10e fix and lacked the two paired-read inputs. They were
backfilled model-free before the countersignature with `scripts/analysis/backfill_sealonly_read_inputs.py`
(writes only the two files; 1,080 roster rows, 1,080 phase results): generation manifest sha256
`e8e2a60e19daca2220baae02c054b89959a81341b254e54dec01e2c4b698126f`, phases sha256
`de0d4c8609f691939ed764ac55d38658b743d14aeefb8f06a9fdf5061c5ee60e`. The summed predecessor costs:

| run | rows | contacts | speech s | prompt / completion tokens | latency s (summed per contact) | GPU-h |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1` (seal-only, costs inherited) | 1,080 | 8,709 | 25,428.698 | 67,824,629 / 551,270 | 31,074.22 | not available (no serving-monitor GPU-h on a seal-only completion) |

Extra contacts of the two non-delivering Perception branches: 4 per row, 4,320 in total, 49.6 % of the
flight's 8,709. Tool calls 0.

Custody: every row carries a level-2 `saea-perception-branch-arms-v2` receipt (1,080 / 1,080); the delivering
branch note reproduces the ledger driver's P-node parse on 1,080 / 1,080 rows (0 differ, 0 missing; 21 raw
duplicate rows; collapsed rank never differs from raw rank). The three column scorings reproduce the official
scorer to 1e-6.

| branch | note_parse_status ok | duplicates-collapsed | list size 1 / 2 / 3 | presentation |
| --- | ---: | ---: | --- | --- |
| `a-agree` (delivering) | 1,059 | 21 | 49 / 268 / 763 | none |
| `b-top2contrast` | 1,063 | 17 | 11 / 607 / 462 | rendered 1,035; skipped 45 (insufficient pool support 42, fewer than two candidates 3) |
| `t-twin` | 1,057 | 23 | 54 / 260 / 766 | none |

No note was empty or malformed, so the seal-only reading clause (empty or malformed counts as gold-absent)
changed no row.

## 2. Level 1: the branch note (gold offline)

| branch | top1 % | present % | rank 1 | rank 2 | rank 3 | absent | mean gold rank when present |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `a-agree` | 82.69 | 91.85 | 893 | 77 | 22 | 88 | 1.122 |
| `b-top2contrast` | 81.02 | 90.00 | 875 | 82 | 15 | 108 | 1.115 |
| `t-twin` | 82.13 | 91.30 | 887 | 77 | 22 | 94 | 1.123 |

| contrast (right minus `a-agree`) | metric | delta pp | CI95 pp | half-width | discordant |
| --- | --- | ---: | --- | ---: | ---: |
| twin null `t-twin` | top1 | -0.56 | [-1.11, -0.09] | 0.51 | 8 |
| twin null `t-twin` | present | -0.56 | [-1.11, -0.09] | 0.51 | 8 |
| `b-top2contrast` | top1 | -1.67 | [-2.96, -0.37] | 1.30 | 54 |
| `b-top2contrast` | present | -1.85 | [-2.96, -0.83] | 1.06 | 34 |

The twin's level-1 bar (|offset| + half-width) is 1.06 pp for both top1 and present. The B note loses both
top1 and present beyond that bar: the forced top-2 contrast shortens the list (607 two-item lists vs 268) and
drops gold from it on 20 more rows. Level 1 never gates; the utterance-level intervals equal the row-level ones
(one row per utterance).

## 3. Level 2: the branch Solver column (official, `slurp-slu-official-train`)

| column | intent % | official SLU-F1 % | per-row SLU-F1 % |
| --- | ---: | ---: | ---: |
| `a-agree` (delivering) | 83.52 | 62.74 | 43.00 |
| `b-top2contrast` | 83.33 | 62.84 | 43.14 |
| `t-twin` | 83.43 | 62.71 | 42.96 |

| contrast (right minus `a-agree`) | metric | delta pp | CI95 pp | half-width | saves / harms |
| --- | --- | ---: | --- | ---: | --- |
| twin null `t-twin` | intent | -0.09 | [-0.46, +0.19] | 0.32 | 1 / 2 |
| twin null `t-twin` | official SLU-F1 | -0.03 | [-0.41, +0.34] | 0.38 | -- |
| twin null `t-twin` | per-row SLU-F1 | -0.05 | [-0.33, +0.20] | 0.27 | 10 / 10 |
| `b-top2contrast` (primary) | intent | **-0.19** | **[-0.56, +0.19]** | 0.37 | 1 / 3 |
| `b-top2contrast` (guard) | official SLU-F1 | +0.10 | [-0.46, +0.69] | 0.58 | -- |
| `b-top2contrast` | per-row SLU-F1 | +0.14 | [-0.28, +0.56] | 0.42 | 14 / 14 |

Twin bars: intent 0.4167 pp, SLU-F1 0.4088 pp (the provisional floor 0.3163 pp is reported beside).

Restricted to the 1,035 rows where the top2-contrast presentation rendered: intent -0.19 pp [-0.58, +0.19],
official SLU-F1 +0.08 pp [-0.53, +0.69]. On the 45 skipped rows the intent contrast nets 0 rows (the full
contrast's net -2 rows equals the rendered subset's net -2 rows); no interval is computed on 45 rows.

Conversion P(correct intent at level 2 | gold rank r in the branch note), against the ledger's 97.57 / 26.98 /
12.0 %:

| branch | rank 1 | rank 2 | rank 3 | absent |
| --- | --- | --- | --- | --- |
| `a-agree` | 98.99 % (884 / 893) | 19.48 % (15 / 77) | 13.64 % (3 / 22) | 0.00 % (0 / 88) |
| `b-top2contrast` | 97.71 % (855 / 875) | 41.46 % (34 / 82) | 6.67 % (1 / 15) | 9.26 % (10 / 108) |
| `t-twin` | 98.87 % (877 / 887) | 22.08 % (17 / 77) | 22.73 % (5 / 22) | 2.13 % (2 / 94) |

The top-2 contrast roughly doubles conversion at rank 2 (41.5 % vs 19.5 %) and recovers 10 gold-absent rows,
which offsets its level-1 loss almost exactly: the level-2 intent column moves by 2 rows net.

## 4. The registered rule, applied mechanically

NOMINATED iff the intent CI95 lower bound is above zero AND the point delta exceeds the twin intent bar AND
the SLU-F1 CI95 lower bound is not below minus the twin SLU bar.

- intent CI95 lower bound above zero: -0.56, **no**;
- intent point exceeds the twin intent bar 0.42: -0.19, **no**;
- SLU-F1 guard, lower bound -0.46 not below -0.41: **no** (the guard would fail too).

BRANCH-LOCAL HARM iff the intent CI95 upper bound is below zero and the point magnitude exceeds the twin
bar: upper bound +0.19 (no), magnitude 0.19 < 0.42 (no).

The numbers fall in the **NOT NOMINATED** branch (driver verdict `NOT NOMINATED`).

Cross-check against the pre-read (`fable/psvreaddriver`, disclosed earlier): level-1 top1 -1.67 [-2.96,
-0.37], present -1.85, level-2 intent -0.19 [-0.56, +0.19], SLU-F1 +0.10. The official read reproduces every
pre-read number to the stated precision.

## Verdict (read agent, for the coordinator)

NOT NOMINATED by the registered rule: the top2-contrast Perception note leaves level-2 intent unchanged
(-0.19 pp [-0.56, +0.19], inside the twin bar 0.42 pp), while it measurably degrades the note itself at
level 1 (top1 -1.67 pp, present -1.85 pp, both beyond the twin's 1.06 pp bar) and buys that back through a
higher rank-2 conversion. Not a branch-local harm at level 2. The coordinator's verdict clause is pending.

## Coordinator verdict (Fable 5.1, 2026-09-30)

- **P-SV-1 top-2 contrast presentation: NOT NOMINATED; closed as a Perception component.** Level-2 intent -0.19 [-0.56, +0.19] (primary), SLU-F1 +0.10; level-1 present -1.85 [-2.96, -0.83] and top1 -1.67 [-2.96, -0.37]: the contrast block lowers Perception's recall of gold. The one positive signal, rank-2 conversion 41.5 % under B against 19.5 % under A, says the contrast helps the SOLVER choose between two shown candidates, not Perception's shortlist; it is recorded as an inner-loop knob for a Solver-side contrast action (a module column at the Solver node), not re-flown at Perception. Same-flight instrument note: twin intent null 0.09, present null 0.56 (bar 1.06). Development number (decisions 28/86).
- **Amendment (2026-09-30, after `2026-09-30-slurp-perception-block-depth-and-recall-offline.md`).** The rank-2 conversion 41.5 % vs 19.5 % is a composition artefact, not a Solver-visible effect: the contrast block reached only the Perception request; the level-2 Solver received the branch's note text with a supply identical to A on all 1,080 rows, and on the contrast branch's own 82 rank-2 rows both Solvers are right 34 times. The Solver-side contrast column is struck from the lever list (predicted effect 0 rows).
