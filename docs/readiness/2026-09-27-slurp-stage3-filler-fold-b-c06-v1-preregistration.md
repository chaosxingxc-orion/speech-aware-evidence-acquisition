# Preregistration -- filler chunk c06 (owner decision 162)

Registered before contact 2026-09-27 at study commit `bf483458`. Package `docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-c06-v1/`.

## What flies

The current best SLURP system -- the locked PLAN plan plus the agreement term retained into COMP-1 (owner decision
161: w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, fuse 8-1-8) -- in cell ROLL-2's
grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality commit at min_support 3), on the 180
TRAIN Fold B rows of `docs/receipts/rosters/slurp-stage3-filler-fold-b-c06-v1.json` (split identity `fbfaf96c49e9e7d131612ad38e262ba071aec999ee45f451d7d3d7e80056036e`).
Run ids: SAEA-SLURP-STAGE3-FILLER-FOLD-B-C06-V1, SAEA-SLURP-STAGE3-FILLER-FOLD-B-C06-FIT-V1.

## Composed identity

- `slurp-native-stage3-filler-fold-b-c06-v1`: composed config `390a0b60c3770f1318ca7710f11fafb3bfe25cd5776c170f5aa99f97b5158588`, protocol hash `e5f78d6876926c51473b8d3ef681fa3d9242993b618e8a220759edf9eb0e1919`

Every composed path that differs from cell ROLL-2 is an agreement pin, a roster pin or run-id / budget / prose
bookkeeping (`registered-facts-v1.json`, `composed_diff_against_roll2`; re-proved by `tests/unit/test_filler_family.py`).

## Measurement declaration

DESCRIPTIVE by construction. `registered-facts-v1.json` carries the canonical block; repeated here:

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-FILLER-FOLD-B-C06-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "offline-sealed-pool",
      "note": "Filler chunk c06 makes no effectiveness claim of its own: it seals a 180-row x 5-sample pool on TRAIN Fold B so that credit, selection, commit and verification rules of the training-free RL inner loop can be computed OFFLINE over sealed bytes. It is a batch under the instrument's 200-row MIN_BENEFIT_ROWS, so it is descriptive by size as well as by design; any benefit claim belongs to a later read over the pooled chunks, which declares its own block.",
      "primary_metric": "slu_f1",
      "rows": 180
    }
  }
}
```

## Budgets and stops

Ceilings are BOUNDS, never targets, and run-cumulative across attempts: SAEA-SLURP-STAGE3-FILLER-FOLD-B-C06-V1 generation 3420, FIT 13680, speech 9744 s, GPU 2.0 h.
Stop and preserve on the first failure; the idle-filler queue HALTS on a STOP and never skips a failed chunk. No
paper-scale profile, no test-split or DEV contact, no comparator flight, no admission entry, no transcript tokens.

## Read

`analysis-recipe-v1.json` via `scripts/flights/filler/filler_pool_read.sh 6`, registered as `SAEA-SLURP-STAGE3-FILLER-FOLD-B-C06-READ-V1`
after the seal and before any number is read. TRAIN gold (`slurp-slu-official-projected-v3-train`); development numbers only.
