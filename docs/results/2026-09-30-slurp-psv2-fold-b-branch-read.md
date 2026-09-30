# Cell P-SV-2 (same-flight Perception branch, forced three-candidate list) branch read: b-list3 vs a-agree gold-on-list +0.37 pp CI95 [-0.37, +1.20] against a twin present bar of 1.02 pp; level-2 intent 0.00, official SLU-F1 +0.81 pp [+0.11, +1.66] beside, on TRAIN Fold B (DESCRIPTIVE)

Read 2026-09-30 (UTC; outputs generated 00:04Z to 00:11Z) by Claude Opus 5.5 (records and read agent) in the
worktree `fable/psv2read` (model-free; `core.flight.cli` and `lease_cli` were not invoked; no GPU, model, server,
encoder or tokenizer contact; three official column scorings). READ row
`SAEA-SLURP-STAGE3-PSV2-FOLD-B-BRANCH-READ-V1` was root countersigned 2026-09-29T23:49:35Z (master `881b1787c`),
after the seal (arm-inspect PASS and step-done 2026-09-29T23:23:39Z) and before any branch column score existed.
Recipe `docs/readiness/2026-09-29-slurp-stage3-psv2-fold-b-v1/analysis-recipe-v1.json` (sha256
`5d9722006395ca70b1baf941dae3bd7eb14f34afead1415ebacb9517dfd737e9`), recipe id
`slurp-stage3-psv2-fold-b-branch-analysis-v1`, rule kind `presence`. Paired row bootstrap, cluster key
`sample_id`, 10,000 draws, seed 20260929, TRAIN gold through the governed loader and
`slurp-slu-official-train`. Owner decisions 184 (the read form) and 193.

The driver was `scripts/flights/psv/psv_read.sh psv2` (sha256
`4566e59e958fb1186d204229815c81e34327162b465471845aa7aa1ce86f6a2c`; run once, rc 0, with `SAEA_REPO_ROOT` pointed
at this worktree; a `--dry-run` preceded it; no `--rescore`). It called
`scripts/analysis/slurp_perception_branch_read.py` (sha256
`499598f3726f97e2050c1d2bd8424afe2ab943be3e45376e91a71de3ddbe626e`).

Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PSV2-FOLD-B-BRANCH-READ-V1/`:

- receipt `perception-branch-read.json` (schema `saea-perception-branch-read-v1`) sha256
  `2f656c763f179ec629b14e67e19d5d6c31e9712d38498a4f3de06e46647a7c9a`;
- `twin-null/`: `verdict.json` `03a1e272f1366698d15a968ff0ba584d6efe5e9694496311dd1be288f543d9ae`,
  `score-contrasts.json` `797f5d2295e67dac84ee09102a1f7c37504c871e358cedd0f3712b0434c34a2f`,
  `per-scenario-tables.json` `e44c4ecbcd237d0e8f5b1362f7fb97428a2604bdd6035218b79b20ca03c6351d`;
- `branch/`: `verdict.json` `066219509326be8a2502488856bd59b90d5828eef780341098d3d06fc6e7e26c`,
  `score-contrasts.json` `f155e020c58456df17f29650f8a01ae4317e4fd40217915f1f02f2752bdad10b`,
  `per-scenario-tables.json` `de6e77e9a5aebf2e05d3a715216e9977ea435a357caaf68d8abe3c0fca309dc6`;
- the three column scorings: `supply-variants/score-summary.json` under the sealed attempt, sha256
  `2968b796b76b7c116c64c67933cb30388304b3ccf25ec32e6552db2f75c405fd`.

No utterance text, gold label, slot filler, note text or model output was printed or persisted. Only counts,
rates, deltas, ids and hashes appear below.

**DESCRIPTIVE.** This note gives the numbers and says which side of the pre-declared rule they fall on. The
verdict word belongs to the coordinator (decision 139). These are development numbers on a TRAIN construction
fold (decisions 28 and 86), branch-local, never a system-level or test claim. The claim ceiling is
"nominated"; a presence nomination opens no system claim.

## 1. What flew

Driver step 1 of `SAEA-Queue-NEXT`'s P-SV chain (`scripts/flights/psv/batch_chain_psv.sh psv2 psv3`) at flight
commit `c6e98e6b`, clean tree (`study_repo_dirt` empty). Smoke passed 20:52:06Z; arm 20:52:16Z to 23:23:31Z (rc 0,
2 h 31 min wall); arm-inspect PASS (attempt FINALIZED, manifest COMPLETED, one score job) and step-done at
23:23:39Z; the driver started P-SV-3 at 23:23:59Z.

| run | rows | contacts | speech s | prompt / completion tokens | GPU-h | state |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1` | 1,080 | 8,713 | 25,432.924 | 67,633,244 / 577,221 | not recorded (`cost_provenance` null); wall 2 h 31 min | COMPLETED, FINALIZED, scored once |

Dispositions: finite completion 11, revision limit 4. Tool calls 0. Run manifest sha256
`f65d2bf25de894637cd0869236f8c0b11fe0921e5ab2429528d0664bbbd6e891`, outputs
`3b9c42ce45c50a35824de1af673ee2e4e2bf81ab340e2952b282ed5e4a414dbe`, scores
`d4fc6cff300316122dcd4e2385594a2d76d0cc51914ccca967bf8c95602f1572`.

Extra contacts of the two non-delivering Perception branches: 4 per row, 4,320 in total, 49.6 % of the flight's
8,713.

Custody: every row carries a level-2 `saea-perception-branch-arms-v2` receipt (1,080 / 1,080); the delivering
note reproduces the ledger driver's P-node parse on 1,080 / 1,080 rows (0 differ, 0 missing; 17 raw duplicate
rows; collapsed rank never differs from raw rank). The three column scorings reproduce the official scorer.

| branch | note_parse_status ok | duplicates-collapsed | list size 1 / 2 / 3 | min_candidates_met true / false |
| --- | ---: | ---: | --- | --- |
| `a-agree` (delivering) | 1,063 | 17 | 57 / 254 / 769 | -- |
| `b-list3` (forced three) | 1,049 | 31 | 60 / 70 / 950 | 950 / 130 |
| `t-twin` | 1,055 | 25 | 52 / 271 / 757 | -- |

As expected under the forced list, `b-list3` collapses more duplicates (31 vs 17 and 25). The forced list is
met on 950 of 1,080 rows (88.0 %); 130 notes still carry one or two candidates after collapse.

## 2. Level 1: the branch note (primary: gold-on-list)

| branch | top1 % | present % | rank 1 | rank 2 | rank 3 | absent | mean gold rank when present |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `a-agree` | 81.48 | 90.83 | 880 | 80 | 21 | 99 | 1.124 |
| `b-list3` | 81.48 | 91.20 | 880 | 84 | 21 | 95 | 1.128 |
| `t-twin` | 81.48 | 90.56 | 880 | 80 | 18 | 102 | 1.119 |

| contrast (right minus `a-agree`) | metric | delta pp | CI95 pp | half-width | discordant |
| --- | --- | ---: | --- | ---: | ---: |
| twin null `t-twin` | present | -0.28 | [-1.02, +0.46] | 0.74 | 17 |
| twin null `t-twin` | top1 | 0.00 | [-0.74, +0.74] | 0.74 | 16 |
| `b-list3` (primary) | present | **+0.37** | **[-0.37, +1.20]** | 0.79 | 20 |
| `b-list3` | top1 | 0.00 | [-0.74, +0.74] | 0.74 | 18 |

Twin present bar (|offset| + half-width): 1.0186 pp (the provisional floor 0.3163 pp is reported beside). The
forced third slot moves gold onto the list on 4 net rows (absent 99 -> 95; rank 2 80 -> 84, rank 3 unchanged at 21); top1 is
unchanged (880 rows at rank 1 in every branch).

## 3. Level 2 beside (never gating): the branch Solver column (official, `slurp-slu-official-train`)

| column | intent % | official SLU-F1 % | per-row SLU-F1 % |
| --- | ---: | ---: | ---: |
| `a-agree` (delivering) | 82.96 | 61.63 | 42.91 |
| `b-list3` | 82.96 | 62.44 | 43.25 |
| `t-twin` | 82.96 | 61.81 | 42.86 |

| contrast (right minus `a-agree`) | metric | delta pp | CI95 pp | half-width | saves / harms |
| --- | --- | ---: | --- | ---: | --- |
| twin null `t-twin` | intent | 0.00 | [-0.28, +0.28] | 0.28 | 1 / 1 |
| twin null `t-twin` | official SLU-F1 | +0.18 | [-0.35, +0.73] | 0.54 | -- |
| twin null `t-twin` | per-row SLU-F1 | -0.05 | [-0.49, +0.40] | 0.45 | 14 / 18 |
| `b-list3` | intent | 0.00 | [-0.37, +0.37] | 0.37 | 2 / 2 |
| `b-list3` | official SLU-F1 | +0.81 | [+0.11, +1.66] | 0.78 | -- |
| `b-list3` | per-row SLU-F1 | +0.34 | [-0.16, +0.87] | 0.52 | 20 / 12 |

The pooled official SLU-F1 of the `b-list3` column sits above zero at CI95 and its point (+0.81) exceeds the
twin's SLU bar computed the same way (0.18 + 0.54 = 0.72) by 0.09 pp; the per-row SLU-F1 interval spans zero.
The rule makes this column descriptive only: it does not gate, and it is a single same-flight read.

Conversion P(correct intent at level 2 | gold rank r in the branch note), against the ledger's 97.57 / 26.98 /
12.0 %:

| branch | rank 1 | rank 2 | rank 3 | absent |
| --- | --- | --- | --- | --- |
| `a-agree` | 99.20 % (873 / 880) | 22.50 % (18 / 80) | 14.29 % (3 / 21) | 2.02 % (2 / 99) |
| `b-list3` | 98.52 % (867 / 880) | 29.76 % (25 / 84) | 9.52 % (2 / 21) | 2.11 % (2 / 95) |
| `t-twin` | 98.64 % (868 / 880) | 26.25 % (21 / 80) | 16.67 % (3 / 18) | 3.92 % (4 / 102) |

Gold at rank 3 converts at 9.5 % under the forced list (2 of 21 rows).

## 4. The registered rule, applied mechanically

NOMINATED (as a presence change) iff the present CI95 lower bound is above zero AND the point delta exceeds the
twin's present bar.

- present CI95 lower bound above zero: -0.37, **no**;
- present point exceeds the twin present bar 1.02: +0.37, **no**.

The numbers fall in the **NOT NOMINATED** branch (driver verdict `NOT NOMINATED`).

## Verdict (read agent, for the coordinator)

NOT NOMINATED by the registered presence rule: forcing three candidates moves gold onto the Perception list on
4 net rows (+0.37 pp [-0.37, +1.20], under the twin's 1.02 pp bar) with top1 and level-2 intent unchanged. The
level-2 SLU-F1 column reads +0.81 pp [+0.11, +1.66] beside the rule (never gating); if the coordinator wants
it followed, it needs its own registered level-2 cell. The coordinator's verdict clause is pending.

## Coordinator verdict (Fable 5.1, 2026-09-30)

- **P-SV-2 forced three-candidate list: NOT NOMINATED on presence.** Present +0.37 [-0.37, +1.20] (primary), top1 0.00, level-2 intent 0.00; `min_candidates_met` 950/1,080; duplicates rose to 31 notes. Forcing the list length does not bring the off-list gold back: the 83 off-list rows need recall (boundary depth, P-SV-3 flying), not a longer note.
- **Descriptive lead.** Level-2 SLU-F1 +0.81 [+0.11, +1.66] on the B column (twin +0.18) is above zero but under the same-flight SLU floor 1.49; it enters the inner loop as an observed knob (`min_candidates = 3`: SLU +0.81), not a cell. Development number (decisions 28/86).
