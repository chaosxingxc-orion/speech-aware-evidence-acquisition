# Preregistration: EMPTYENT, the DEV-2000-ADDED pool null and an explicit empty-entity rule

Registered 2026-09-27 under owner decision 171, before any number of either step exists. Package:
[`2026-09-27-slurp-stage3-empty-entity-offline-v1/`](2026-09-27-slurp-stage3-empty-entity-offline-v1/README.md).
Read id `SAEA-SLURP-STAGE3-EMPTY-ENTITY-OFFLINE-V1` (DRAFT exposure row, root countersignature pending).
No flight is registered.

## Fixed before reading

1. **Null first** (`--stage null`, zero scorer contacts): ten sample-index pairs of the sealed ROLL-3 pool,
   pooled official SLU-F1 under `slurp-slu-official-projected-v3`, the aggregation read's paired ROW
   bootstrap imported unchanged (`default_rng(20260915)`, 10,000 draws, percentile CI95) -- the instrument
   note's section 2c / 2d one-pool method. THE NULL = mean pairwise half-width; intent guard = mean
   pairwise intent half-width. Sealed in `null.json`; never adjusted after step 2 (instrument rule 6).
2. **Rule** (`--stage rule`, five scorer contacts on copies): emptiness vote >= 3 of 5 -> empty entity list
   on every sample of the row. One form, no tuning.
3. **CLEARS** iff SLU-F1 CI95 lower bound > 0 AND SLU-F1 delta >= THE NULL AND intent CI95 lower bound >=
   -(intent guard). A clear licenses an arm with an in-chain A/A; never a gain claim.

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-EMPTY-ENTITY-OFFLINE-V1": {
      "measurement_design": "offline-sealed-pool",
      "expected_effect_pp": 0.53,
      "rows": 1000,
      "claims_benefit": true,
      "primary_metric": "official pooled SLU-F1 (micro), RULE-mean-single minus R0-mean-single over the sealed ROLL-3 pool; intent the guard",
      "note": "0.53 is the gate's offline floor at n = 1,000 -- the smallest effect registered to be seen, not a forecast. The registered decision bar is the pool's own measured null (step 1), which may be larger."
    }
  }
}
```

**Stage-3 algorithm label:** `none`.

## Claim boundary

Offline, one sealed pool; development numbers only (owner decisions 28 and 86); DEV-2000-ADDED is an
evaluation roster read offline over already-sealed samples, never a test claim. Gold enters only inside the
registered official scorer.
