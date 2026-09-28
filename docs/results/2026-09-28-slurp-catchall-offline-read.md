# CATCHALL offline read: the catch-all intent rule over the sealed ROLL-2 (Fold A) and ROLL-3 (DEV-2000-ADDED) pools -- intent -0.19 [-0.78, +0.37] on Fold A and +0.32 [-0.28, +0.92] on DEV, below both floors; SLU-F1 unchanged by construction (DESCRIPTIVE)

Read 2026-09-28. The registered model-free read row `SAEA-SLURP-STAGE3-CATCHALL-OFFLINE-V1` (owner decision
171; package [`docs/readiness/2026-09-27-slurp-stage3-catchall-offline-v1/`](../readiness/2026-09-27-slurp-stage3-catchall-offline-v1/README.md),
preregistration [`../readiness/2026-09-27-slurp-stage3-catchall-offline-v1-preregistration.md`](../readiness/2026-09-27-slurp-stage3-catchall-offline-v1-preregistration.md))
was root countersigned at 2026-09-28 04:57 UTC by the coordinator (Fable 5.1) before the read, in commit
`887ea2d5` on branch `fable/b3read` (one row covers both pools; count asserted = 1). It was then executed
exactly as registered by Claude Opus 5.5 in worktree `/home/chao/saea-worktrees/fable-b3read`:
`scripts/analysis/catchall_offline_read.py --pool fold-a` (04:58:07 to 05:09:01 UTC) and `--pool dev2000-added`
(05:09:01 to 05:10:45 UTC). The script's bytes equal the registered sha256 `bd3dd62e...`, and the imported
aggregation read equals `e81cf5be...` (both verified, and re-reported in each `report.json`). Both `--dry-run`
passes ran first and reproduced the registered counts.

Contacts: five CPU official-scorer jobs per pool (`score_copy` over the edited per-sample copies; gold enters
only inside the registered scorer), zero model, tokenizer, encoder, embedder, llama-server, GPU and network
contacts, 0 speech-audio seconds. No utterance text, transcript, gold label string, intent name of a row,
entity value or model answer is printed or persisted here. The per-stratum tables in section 3 were derived
model-free from the same score files (counts and scores only); on Fold A the stratum is the roster's own
per-row stratum carried in the sealed `per_row.json` of the pool read, and on DEV-2000-ADDED the roster
withholds a per-item scenario, so its stratum is the channel (headset / far-field), as in the ROLL-3 read.

Status: **DESCRIPTIVE** -- development numbers on sealed pools (owner decisions 28 and 86); the coordinator
writes the verdict word from these numbers.

## 1. Inputs and outputs

| pool | role | scorer | render manifest sha256 | agreement table sha256 | report.json sha256 |
| --- | --- | --- | --- | --- | --- |
| ROLL-2 `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1`, TRAIN Fold A, 1,080 x 5 | primary | `slurp-slu-official-projected-v3-train` | `7a891fe5...` | `018ca6ef...` | `be0bfa74836686aadf075cab523d05827ce18154688dd9ac9012fe9885bfac00` |
| ROLL-3 `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1`, DEV-2000-ADDED, 1,000 x 5 | fresh-roster replication | `slurp-slu-official-projected-v3` | `5f193003...` | `283bd9f5...` | `b93d605a39d13015f144e8b0dc62256f4ac9523c3f392c0f73ea0dc7fc38d032` |

Machine results under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-CATCHALL-OFFLINE-V1/<pool>/`
(`report.json`, the five edited copies `rule-sample-<i>-outputs.jsonl` and their five score files).

## 2. The registered contrast

`RULE-mean-single` against `R0-mean-single` (the mean of the five unedited per-sample copies under the same
scorer id -- NOT the sealed delivered commit), paired row bootstrap, 10,000 draws, seed 20260915, percentile
CI95.

| pool | rows marked | samples edited / already catch-all / unmarked | R0 intent | RULE intent | intent delta [CI95] | SLU-F1 delta [CI95] | floor |
| --- | ---: | --- | ---: | ---: | --- | --- | ---: |
| Fold A (primary) | **20** | 60 / 40 / 5,300 | 82.167 | 81.981 | **-0.185 [-0.778, +0.370]** | 0.000 [0.000, 0.000] | 0.5097 |
| DEV-2000-ADDED | **19** | 66 / 29 / 4,905 | 75.760 | 76.080 | **+0.320 [-0.280, +0.920]** | 0.000 [0.000, 0.000] | 0.5299 |

Per-sample intent deltas: Fold A -0.19 / -0.19 / -0.09 / -0.19 / -0.28; DEV +0.30 / +0.30 / +0.30 / +0.40 /
+0.30. Intent-indicator changes on marked rows, summed over the five samples: Fold A 20 samples turned correct
and 30 turned wrong (net -10 sample-rows = -2 row-equivalents); DEV 31 correct and 15 wrong (net +16 = +3.2
row-equivalents). No score moved on any unmarked row (asserted). Against the registered reach ceilings (1.85 pp
Fold A, 1.32 pp DEV), the realised deltas are -0.19 and +0.32.

**SLU-F1 is exactly unchanged on both pools, by construction**: the official SLU-F1 counts entity
(span / word / char) matches only, and the rule edits scenario and action with entities byte-unchanged, so the
guard cannot move; span F1 and the per-row SLU mean are likewise identical (Fold A 61.921 / 51.321; DEV 63.097
/ 54.211).

## 3. Per stratum, both weightings

**Fold A** (18 scenario strata of 60 rows each; the natural-mixture and equal-stratum weightings therefore
coincide: intent -0.185 in both, equal-stratum CI95 [-0.778, +0.370]; SLU-F1 0.000 in both). Only strata with a
marked row are listed; the 13 others have no marked row and a delta of exactly 0.

| stratum | rows | marked | R0 intent | intent delta | SLU-F1 delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| general | 60 | 16 | 43.33 | 0.00 | 0.00 |
| cooking | 60 | 1 | 85.33 | -1.67 | 0.00 |
| email | 60 | 1 | 88.33 | 0.00 | 0.00 |
| qa | 60 | 1 | 75.00 | 0.00 | 0.00 |
| social | 60 | 1 | 73.33 | -1.67 | 0.00 |
| all 18 | 1,080 | 20 | 82.17 | -0.19 | 0.00 |

Within `general` (16 marked rows) the conversions and the losses cancel exactly (net 0 sample-rows); the net
loss comes from the two marked rows outside `general` (cooking and
social, -5 sample-rows each).

**DEV-2000-ADDED** (channel strata):

| stratum | rows | marked | R0 intent | intent delta | SLU-F1 delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| far-field | 540 | 10 | 72.04 | +0.78 | 0.00 |
| headset | 460 | 9 | 80.13 | -0.22 | 0.00 |
| natural mixture | 1,000 | 19 | 75.76 | **+0.32** [-0.28, +0.92] | 0.00 |
| equal stratum | 1,000 | 19 | 76.08 | **+0.28** [-0.29, +0.88] | 0.00 |

(The equal-stratum CI95 reuses the registered draws, seed and row resampling with per-row stratum weights; it is
supplementary to the registered natural-mixture contrast.)

## 4. The pre-declared rule and which side the numbers fall on

Pre-declared (preregistration, `registered-facts-v1.json` `decision_rule`, and the script's `clears`): the rule
CLEARS a pool iff (a) the intent delta's CI95 lower bound is above 0, AND (b) the intent delta is at least the
pool's floor, AND (c) the SLU-F1 CI95 lower bound is at least minus the floor. An arm with an in-chain A/A is
registered only if Fold A clears. The package pre-declares no separate "harmful" criterion.

| pool | (a) intent CI95 lo > 0 | (b) delta >= floor | (c) SLU-F1 lo >= -floor | `clears` |
| --- | --- | --- | --- | --- |
| Fold A | no (-0.778) | no (-0.185 < 0.5097) | yes (0.000) | **false** |
| DEV-2000-ADDED | no (-0.280) | no (+0.320 < 0.5299) | yes (0.000) | **false** |

Both pools fall on the NOT-CLEAR side of the registered rule; the Fold A condition that licenses an arm is not
met, so by the registration no arm follows. Neither intent CI95 excludes zero in either direction: the Fold A
point estimate is negative and the DEV point estimate positive, each inside its interval, and neither reaches
the floor in magnitude. The SLU-F1 guard holds trivially (section 2).

## 5. Ambiguities recorded

- The baseline is `R0-mean-single`, the mean of the five per-sample copies under the projected scorer id, not
  the pool's sealed delivered plurality commit (Fold A delivered 80.185 intent under the unprojected
  `slurp-slu-official-train`; beside, never subtracted). The rule was read on per-sample copies, as registered.
- Fold A uses the `-train` scorer sibling (`slurp-slu-official-projected-v3-train`), the registered scorer of the
  ROLL-2 pool read; DEV uses `slurp-slu-official-projected-v3`. The two pools' deltas are not pooled.
- The package README still describes the ROLL-2 stage 1-3 read as absent (true at registration); it now exists
  and the Fold A dry run gives 20 marked rows, 60 edited and 40 already-catch-all samples.
- The SLU-F1 guard is structurally inert for an intent-only edit, so condition (c) carries no information here.

## 6. Records

- Exposure ledger: the countersigned READ row `SAEA-SLURP-STAGE3-CATCHALL-OFFLINE-V1` is closed by a COMPLETED
  block citing this note.
- Results ledger: one DESCRIPTIVE entry dated 2026-09-28.

## Coordinator verdict (Fable 5.1, 2026-09-28)

**INERT.** The vote-share catch-all rule does not clear its registered floor on the primary pool: Fold A
intent -0.185 [-0.778, +0.370] against the floor 0.5097 (DEV-2000-ADDED +0.320 [-0.280, +0.920] against
0.5299, also not clear). No arm is registered. The K5 catch-all class (3.06 pp) stays open; like the W2
result, it needs evidence from outside the exemplar vote (the B1 rank-visible / contrastive family). The
agent's numbers above are unchanged.
