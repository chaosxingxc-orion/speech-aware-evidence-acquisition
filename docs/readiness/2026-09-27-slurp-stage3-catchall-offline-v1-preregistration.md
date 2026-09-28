# Preregistration: CATCHALL, an offline catch-all intent rule over sealed sample pools

Registered 2026-09-27 under owner decision 171, before any number of the read exists. Package:
[`2026-09-27-slurp-stage3-catchall-offline-v1/`](2026-09-27-slurp-stage3-catchall-offline-v1/README.md).
Read id `SAEA-SLURP-STAGE3-CATCHALL-OFFLINE-V1` (DRAFT exposure row, root countersignature pending). No
flight is registered; an arm follows only if the primary pool clears.

## Question

When the row's `agree-1` exemplar vote gives `general_quirky` the strict maximum share, does delivering
`general_quirky` on every sample that said otherwise raise intent accuracy over the sealed samples by at
least the pool's offline floor, without lowering the official SLU-F1?

## Fixed before reading

- Pools: ROLL-2 on TRAIN Fold A (1,080 x 5, **primary**; its stage 1-3 read must run first) and ROLL-3 on
  DEV-2000-ADDED (1,000 x 5, replication). ROLL-1 on R01C carries no agreement table and is not read.
- Rule, mark and edit exactly as `scripts/analysis/catchall_offline_read.py` states them; no threshold,
  no tuning, one form.
- Contrast: `RULE-mean-single` vs `R0-mean-single`, the aggregation read's paired row bootstrap (10,000
  draws, seed 20260915, percentile CI95), imported unchanged.
- Floor: `0.67 x sqrt(625 / n)` = 0.5097 pp (Fold A), 0.5299 pp (DEV).
- CLEARS iff intent CI95 lower bound > 0 AND intent delta >= floor AND SLU-F1 CI95 lower bound >= -floor.
  A Fold A clear licenses registering an arm with an in-chain A/A; nothing else.

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-CATCHALL-OFFLINE-V1": {
      "measurement_design": "offline-sealed-pool",
      "expected_effect_pp": 0.51,
      "rows": 1080,
      "claims_benefit": true,
      "primary_metric": "intent accuracy (scenario_action_exact), RULE-mean-single minus R0-mean-single over the sealed ROLL-2 pool; official SLU-F1 the guard",
      "note": "The smallest effect the read is registered to see (its floor at n = 1,080), not a forecast; reach ceiling 1.85 pp (20 marked rows). A clear licenses an arm with an in-chain A/A, never a gain claim."
    }
  }
}
```

**Stage-3 algorithm label:** `none`.

## Claim boundary

Offline, one sealed pool per read; development numbers only (owner decisions 28 and 86); no pooled,
superiority, transfer or confirmatory claim. Gold enters only inside the registered official scorer.
