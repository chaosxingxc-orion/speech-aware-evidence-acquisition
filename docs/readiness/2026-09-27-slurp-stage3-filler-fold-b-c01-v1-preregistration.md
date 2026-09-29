# Preregistration -- filler chunk c01 (owner decision 162)

Registered before contact 2026-09-27 at study commit `bf483458`. Package `docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-c01-v1/`.

## What flies

The current best SLURP system -- the locked PLAN plan plus the agreement term retained into COMP-1 (owner decision
161: w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, fuse 8-1-8) -- in cell ROLL-2's
grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality commit at min_support 3), on the 180
TRAIN Fold B rows of `docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-v1.json` (split identity `a7f41a899ee466a3819c0601c73544459a33808a84320e44ef5ae68d738995ec`). Chunk c01 first flies a four-row structural smoke on `docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-smoke-4-v1.json`.
Run ids: SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-V1, SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-FIT-V1, SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-SMOKE-4-V1, SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-SMOKE-4-FIT-V1.

## Composed identity

- `slurp-native-stage3-filler-fold-b-c01-smoke-4-v1`: composed config `a682f675bb0221ce20129a5af392dec962d108db2ebc2ac0689df77e03771c37`, protocol hash `845907979b56540ac214643946cb6def4e9fa1bf97987879b1e503e1aa7bc018`
- `slurp-native-stage3-filler-fold-b-c01-v1`: composed config `ef93a2754db38b4464364e8dcf46b2ad68d1e2ab1f924ebd0d889452b11141f7`, protocol hash `33bdecfe2011049f432ed1c5977d16b5ab9ea7f8904ad68f8de9a11f46bd7988`

Every composed path that differs from cell ROLL-2 is an agreement pin, a roster pin or run-id / budget / prose
bookkeeping (`registered-facts-v1.json`, `composed_diff_against_roll2`; re-proved by `tests/unit/test_filler_family.py`).

## Measurement declaration

DESCRIPTIVE by construction. `registered-facts-v1.json` carries the canonical block; repeated here:

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The four-row structural smoke of the filler family's composed form proves FORM and nothing else (five custodied Solver samples per row, the plurality-commit replay, the agreement table loading, zero native task-contract calls, every request fitting). Scored by no one and read by no one; under the measurement instrument's rule 5 four rows can never be evidence of benefit.",
      "primary_metric": "slu_f1",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "offline-sealed-pool",
      "note": "Filler chunk c01 makes no effectiveness claim of its own: it seals a 180-row x 5-sample pool on TRAIN Fold B so that credit, selection, commit and verification rules of the training-free RL inner loop can be computed OFFLINE over sealed bytes. It is a batch under the instrument's 200-row MIN_BENEFIT_ROWS, so it is descriptive by size as well as by design; any benefit claim belongs to a later read over the pooled chunks, which declares its own block.",
      "primary_metric": "slu_f1",
      "rows": 180
    }
  }
}
```

## Budgets and stops

Ceilings are BOUNDS, never targets, and run-cumulative across attempts: SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-SMOKE-4-V1 generation 76, FIT 304, speech 194 s, GPU 1.0 h; SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-V1 generation 3420, FIT 13680, speech 10159 s, GPU 2.0 h.
Stop and preserve on the first failure; the idle-filler queue HALTS on a STOP and never skips a failed chunk. No
paper-scale profile, no test-split or DEV contact, no comparator flight, no admission entry, no transcript tokens.

## Read

`analysis-recipe-v1.json` via `scripts/flights/filler/filler_pool_read.sh 1`, registered as `SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-READ-V1`
after the seal and before any number is read. TRAIN gold (`slurp-slu-official-projected-v3-train`); development numbers only.
