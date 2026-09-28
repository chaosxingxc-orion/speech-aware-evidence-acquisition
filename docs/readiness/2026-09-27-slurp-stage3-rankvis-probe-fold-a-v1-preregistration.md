# Preregistration: cell RANKVIS, the rank-visible rendering conversion probe on TRAIN Fold A (119 rows)

Registered 2026-09-27, before any contact, under owner decision 171. Package:
[`2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1/`](2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1/README.md).
Status: HELD. The exposure rows are DRAFT, root countersignature pending. This document authorises no flight.

## The question

On the 119 TRAIN Fold A rows where the sealed AGREE arm delivered the gold intent's boundary entry and still
answered a wrong intent, what proportion move to the gold intent when the delivered boundary and exemplar
blocks are rendered in retrieval-rank order with the rank shown -- and nothing else changes?

## The treatment (one key)

`native_episode.knowledge_value_rendering` = `{schema saea-knowledge-value-rendering-v1, order retrieval-rank,
rank_visible true, stores [intent-boundaries, train-exemplars]}` added to the registered AGREE arm's baseline.
Every other byte of the composed configuration is the AGREE arm's (`tests/unit/test_rankvis_config.py`).

## The comparator

The sealed AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, intent-wrong on all 119 rows by construction.
It is never re-flown. The contrast is per row and offline.

## The read rule (fixed here)

1. The manifest is COMPLETED at 119 rows with the registered id-list hash; the flown config hash is this cell's.
2. **Rendering gate**: every flown Solver request carries the `retrieval rank <r>: ` labels on the two named
   stores and its exemplar order equals the recomputed retrieval-rank order; otherwise no number is produced.
3. `m` = rows whose delivered intent equals gold (the sealed official per-sample `scenario_action_exact`,
   one complete official scoring at finalize, never re-run). Wilson CI95 with Clopper-Pearson beside it.
4. `m` is read against the **no-op expectation 15.9** (the error-source read's null save rates 12/31 at gold
   position 1 and 20/226 at 2-8 applied to this roster's 18 / 101 rows), never against zero.
5. Reported beside: the four-way transition split, the split by stage, and the same read on the 89-row
   synthesis subset (no-op expectation 11.5).
6. Re-declaration, stated and not applied: `(m - 15.9) x 0.0926` pp intent accuracy for a later 1,080-row arm
   with an in-chain A/A; the 2.5 pp bar needs `m >= 43`.

## Measurement declaration

The canonical copy is `registered-facts-v1.json`, top-level `stage3_measurement`; this fence repeats it.

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1": {
      "measurement_design": "form-proof",
      "expected_effect_pp": 0.0,
      "rows": 119,
      "claims_benefit": false,
      "primary_metric": "per-row intent correctness (scenario_action_exact) as the conditional rate m/119 against the no-op flip expectation",
      "note": "Under 200 rows: a form proof by size, never evidence of benefit (instrument rule 5). The later arm declares (m - 15.9) x 0.0926 pp intent (decision 139)."
    }
  }
}
```

**Stage-3 algorithm label:** `none` (no rollout, scoring, credit, update or store evolution).

## Claim boundary

Selected using gold, offline: a conditional rate on a TRAIN roster. No pooled, roster-level, superiority,
transfer or confirmatory claim; development numbers only (owner decisions 28 and 86). The probe cannot see
harm on the rows AGREE already answers correctly; that is the arm's in-chain A/A's question.
