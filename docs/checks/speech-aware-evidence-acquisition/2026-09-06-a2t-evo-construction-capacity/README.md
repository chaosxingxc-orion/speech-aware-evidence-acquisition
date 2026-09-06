# EVO-A1 construction capacity — the loop's ceiling, stated before takeoff

Model-free, zero contacts. Exposure row `SAEA-A2T-MF-EVO-CONSTRUCTION-CAPACITY-V1`, registered
before the first count. Generator `scripts/build_a2t_evo_construction_capacity.py`; arithmetic
`analysis/a2t_evo_capacity.py`; tests `tests/unit/test_a2t_evo_construction_capacity.py`.
Receipt `capacity.json`. Outbound connection attempts: **0**.

Authority: `docs/readiness/2026-09-05-three-dimension-experiment-program.md` sections 4c and 5.
Target list: `configs/knowledge/a2t-kc-a1/targets-v1.json`, re-verified target by target and tool
by tool against `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-query-cue-audit/`
before a number is computed; the run refuses if the two disagree.

## Verdict

**Three of MF-1's five targets survive the loop's own row requirement, and they carry 67 of the
235 addressable misses — 28.5 % of the mass the KC-A1 gate was passed on.** The loop's arithmetic
ceiling on the sealed 4,000 is therefore **+1.68 pp**, before any question of whether a rewritten
description can move a single row.

The reason is one tool. `setAmbientLighting` is the pivot of the lighting target — it appears in
nine of that target's ten TARGET pairs, including the 88-row dominant pair — and it has **9
construction units in 9 blocks**. The loop needs three disjoint slices of every targeted tool:
fold-A reward rows, fold-B reward rows, and `M = 8` proposer exemplars. Nine units cannot yield
two folds of six plus an exemplar reserve under any assignment, so the lighting target's dominant
confusion is unrewardable from construction data, and 147 of the 235 rows go with it.
`calibrateCameras` (7 units) does the same to its own target's dominant pair.

This is the same wall MF-1 found on the other side of the corpus: `armSecuritySystem` has 3
construction units and `setSecurityMode -> armSecuritySystem` is the single largest confusion in
the release. The Audio2Tool corpus does not supply gold rows for the tools its own speakers reach
for by mistake.

## The rule, applied verbatim

```
quota_A = quota_B = min(20, floor((units - 8) / 2))
```

lowered to the largest **whole-block** split that still yields both folds and the 8-unit exemplar
reserve, because a `query_idx` block is the leakage unit and cannot be divided between rosters. A
tool is DROPPED below a quota of 6. A target survives only while its **dominant** confusion pair —
the highest sealed-miss pair inside it — keeps every tool on both sides, since a contrast is only
rewardable when both sides have rows.

## Population

The V3 exposure-free construction pool, restricted to rows whose runtime wav is at most 60 s
(program section 5): **3,201 units in 1,687 blocks**, six units and two blocks short of the full
3,207 / 1,689 pool. Block-disjoint from all 5,279 committed evaluation identities by construction
(`propose_partition`, `docs/receipts/knowledge/a2t-partition-proposal.json`).

**MF-1's per-pair unit counts were already computed on this pool**, not on an older one: every one
of the 23 tools' counts here reproduces the audit's `construction_units_left/right` exactly, except
the three tools that own one of the six over-60-second rows (`castContent` 40 → 39,
`setHapticStrength` 39 → 38, `setLighting` 90 → 89).

## Per-tool capacity

`rule` is the unit quota, `real` the block-feasible one, `fold` what a fold roster may draw.

| target | tool | units | blocks | rule | real | fold | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| lighting | `getLightState` | 29 | 9 | 10 | 9 | 9 | survives |
| lighting | `resetFilterStatus` | 61 | 46 | 20 | 20 | 20 | survives |
| lighting | `setAmbientLighting` | 9 | 9 | 0 | 0 | 0 | **DROPPED** |
| lighting | `setBrightness` | 18 | 8 | 5 | 4 | 0 | **DROPPED** |
| lighting | `setColor` | 49 | 14 | 20 | 20 | 20 | survives |
| lighting | `setColorTemperature` | 30 | 10 | 11 | 10 | 10 | survives |
| lighting | `setGroupLightState` | 55 | 40 | 20 | 20 | 20 | survives |
| lighting | `setLighting` | 89 | 46 | 20 | 20 | 20 | survives |
| activateRoutine | `activateRoutine` | 65 | 46 | 20 | 20 | 20 | survives |
| activateRoutine | `activateScene` | 46 | 36 | 19 | 19 | 19 | survives |
| activateRoutine | `setApplianceMode` | 20 | 10 | 6 | 6 | 6 | survives |
| activateRoutine | `setSecurityMode` | 59 | 14 | 20 | 20 | 20 | survives |
| activateRoutine | `startCleaning` | 32 | 12 | 12 | 12 | 12 | survives |
| getBiometricData | `getBiometricData` | 56 | 41 | 20 | 20 | 20 | survives |
| getBiometricData | `getHRV` | 51 | 41 | 20 | 20 | 20 | survives |
| getBiometricData | `setHapticStrength` | 38 | 34 | 15 | 15 | 15 | survives |
| getBiometricData | `setRomanceMode` | 10 | 10 | 1 | 1 | 0 | **DROPPED** |
| calibrateCameras | `calibrateCameras` | 7 | 7 | 0 | 0 | 0 | **DROPPED** |
| calibrateCameras | `rebootDevice` | 50 | 15 | 20 | 20 | 20 | survives |
| calibrateCameras | `streamCamera` | 44 | 39 | 18 | 18 | 18 | survives |
| calibrateCameras | `updateFirmware` | 55 | 45 | 20 | 20 | 20 | survives |
| castContent | `castContent` | 39 | 10 | 15 | 14 | 14 | survives |
| castContent | `playMedia` | 22 | 7 | 7 | 7 | 7 | survives |

Three tools lose a point of quota to block indivisibility (`getLightState` 10 → 9,
`setColorTemperature` 11 → 10, `castContent` 15 → 14); the per-tier histograms and the per-bucket
block lists are in `capacity.json`.

## Per-target survival

| target | tools | dominant pair | mass | intact? | surviving tools | addressable mass |
|---|---:|---|---:|---|---:|---:|
| lighting | 8 | `setColor+setColorTemperature+setLighting` / `setAmbientLighting` | 88 | **no** | 6 | 18 |
| activateRoutine | 5 | `activateScene` / `activateRoutine` | 15 | yes | 5 | **44** |
| getBiometricData | 4 | `getBiometricData` / `getHRV` | 13 | yes | 3 | **18** |
| calibrateCameras | 4 | `calibrateCameras` / `updateFirmware` | 6 | **no** | 3 | 5 |
| castContent | 2 | `castContent` / `playMedia` | 5 | yes | 2 | **5** |

"Addressable mass" counts only pairs whose every tool still has reward rows.

## Two readings, both priced

| reading | targets | tools | targeted rows per fold | addressable | share of MF-1's 235 | ceiling on the 4,000 |
|---|---:|---:|---:|---:|---:|---:|
| **STRICT** (section 5 as written) | 3 | 10 | 153 | 67 | 28.5 % | +1.68 pp |
| RELAXED (any intact pair kept) | 5 | 19 | 310 | 90 | 38.3 % | +2.25 pp |

STRICT is what the EVO-A1 preregistration proposes. RELAXED keeps a target that has lost its
dominant pair but still holds a rewardable one — the lighting target without `setAmbientLighting`
and `setBrightness` (its `setGroupLightState` / `setLighting` pair, 18 rows), and
`calibrateCameras` without `calibrateCameras` (its `rebootDevice` / `streamCamera` pair, 5 rows).
It is the coordinator's call, and it needs **no fresh draw**: the fold rosters of
`SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V1` carry all 19 surviving tools at their fold quotas, so
ratifying RELAXED only widens which rows the selection rule slices.

## Limits

1. **`fold_quota` is capacity, not power.** 153 targeted rows per fold under STRICT is well below
   the owner's n >= 400 rule; the fold-B confirmation is an internal selection gate, not a claim,
   and the claim-bearing read stays the 4,000.
2. **The ceiling is arithmetic, not a forecast.** It says how many sealed misses lie on pairs the
   loop can be rewarded for; it says nothing about how many a rewritten description can move.
   MF-1's own lighting caveat still applies to the 18 lighting rows the RELAXED reading would add.
3. **Component mass is not re-decomposed.** MF-1's `component` column counts every sealed miss
   whose gold and predicted tool both sit inside a target; restricting it to a target's surviving
   tools would need the raw miss table, so the conservative `strict` (audited-direction) mass is
   what is reported here. Component mass is an upper bound: 278 across all five targets.
4. **Lexical and structural only.** No audio, no model, no scorer ran.
