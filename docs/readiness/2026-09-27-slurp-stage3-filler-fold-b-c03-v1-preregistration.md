# Preregistration -- filler chunk c03 (owner decision 162)

Registered before contact 2026-09-27 at study commit `bf483458`. Package `docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-c03-v1/`.

## What flies

The current best SLURP system -- the locked PLAN plan plus the agreement term retained into COMP-1 (owner decision
161: w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, fuse 8-1-8) -- in cell ROLL-2's
grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality commit at min_support 3), on the 180
TRAIN Fold B rows of `docs/receipts/rosters/slurp-stage3-filler-fold-b-c03-v1.json` (split identity `053d3897eda1f0233a54ed6f622ce45e643572e80420629c1e4f65c23a4ce5cb`).
Run ids: SAEA-SLURP-STAGE3-FILLER-FOLD-B-C03-V1, SAEA-SLURP-STAGE3-FILLER-FOLD-B-C03-FIT-V1.

## Composed identity

- `slurp-native-stage3-filler-fold-b-c03-v1`: composed config `3d0b78a4c6256f5ef40f0dc200c57f13ac9772cf06839898a17624d1fbd9c817`, protocol hash `e1d60033c0f63ea3b95355dcc8cd72c85df70a78128ac464fb5965898e8acf37`

Every composed path that differs from cell ROLL-2 is an agreement pin, a roster pin or run-id / budget / prose
bookkeeping (`registered-facts-v1.json`, `composed_diff_against_roll2`; re-proved by `tests/unit/test_filler_family.py`).

## Measurement declaration

DESCRIPTIVE by construction. `registered-facts-v1.json` carries the canonical block; repeated here:

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-FILLER-FOLD-B-C03-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "offline-sealed-pool",
      "note": "Filler chunk c03 makes no effectiveness claim of its own: it seals a 180-row x 5-sample pool on TRAIN Fold B so that credit, selection, commit and verification rules of the training-free RL inner loop can be computed OFFLINE over sealed bytes. It is a batch under the instrument's 200-row MIN_BENEFIT_ROWS, so it is descriptive by size as well as by design; any benefit claim belongs to a later read over the pooled chunks, which declares its own block.",
      "primary_metric": "slu_f1",
      "rows": 180
    }
  }
}
```

## Budgets and stops

Ceilings are BOUNDS, never targets, and run-cumulative across attempts: SAEA-SLURP-STAGE3-FILLER-FOLD-B-C03-V1 generation 3420, FIT 13680, speech 10011 s, GPU 2.0 h.
Stop and preserve on the first failure; the idle-filler queue HALTS on a STOP and never skips a failed chunk. No
paper-scale profile, no test-split or DEV contact, no comparator flight, no admission entry, no transcript tokens.

## Read

`analysis-recipe-v1.json` via `scripts/flights/filler/filler_pool_read.sh 3`, registered as `SAEA-SLURP-STAGE3-FILLER-FOLD-B-C03-READ-V1`
after the seal and before any number is read. TRAIN gold (`slurp-slu-official-projected-v3-train`); development numbers only.
