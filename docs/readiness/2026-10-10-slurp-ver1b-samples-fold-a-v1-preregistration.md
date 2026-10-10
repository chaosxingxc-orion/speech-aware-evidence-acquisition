# Cell VER-1b (verification layer, Fold A confirmation sample pool): preregistration

Registered 2026-10-10 at study commit `76a9bfe3e6e228dd709964923b4f3b48fec3dd1d`, before any contact, by script (decision 58) from the committed COMP-1b Fold A fragments and the consumption-module compiler under owner decision 257 (decision 258 option A, proposed). Development numbers only.

| item | value |
| --- | --- |
| base | the NX R5 composed arm / R6-P1 / VER-1a base: COMP-1b (agree-vote-seed + centroid-boundary-key ON), lock v2.2 compiled blocks, Reviewer loop OFF, no tool schema on any role |
| the one departure | Solver visit grouped at samples 3: sample 0 greedy (`decoding_overrides.greedy_first`), samples 1-2 at temperature 0.7, seed_offset 0; commit `saea-commit-plurality-support-v1` at min_support 2, similarity 0.8 |
| program | `phase-native-module-v1-c4` (ceiling 4 = 1 + 1 x 3); a registered member of the review-off module family |
| delivery | the unnormalised commit (the loader refuses a deliver_normaliser beside a grouped visit); v4g is applied offline |
| design / claim | `offline-sealed-pool` / descriptive; a POOL cell, `claims_benefit` false, expected effect 0.0 pp |
| the fixed rule | n = 3, s = 2, theta 0.2; FIXED on `SLURP-EVO-FOLD-B-V2`, confirmed (not re-tuned) on `SLURP-EVO-FOLD-A-V2` |
| rosters | tuning `SLURP-EVO-FOLD-B-V2`; read `SLURP-EVO-FOLD-A-V2` |
| runs | `SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1` / `SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-POOL-READ-V1`; verdict column `SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1` |
| composed config hashes | arm `0f4ab6ba682d0009dac54506355157b121c43471c968ba2e479b1c9ee8d97eb4`; smoke `290ade59bfbe6943e7e23d8077367999debec548badc79608852bbb402536f4b` |
| protocol hashes | arm `8fe37ef2fb29f3536824308cc5a62d686da5221cbfdf9b5f26c708dcaecda040`; smoke `53738967da9570b982bc8bd9189d344842171d60de4b2f85e4794e2ae0cb14d9` |
| split identity | arm `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |

## Attempt state (no recovery)

The smoke and the arm are FIRST attempts of their run ids. Budgets are single-attempt: smoke 16 model calls, FIT endpoint cap 64 (structural: 4 rows x 4 contacts x 4 endpoints); arm 4,320 model calls, FIT cap 17,280. At most one recovery re-registration per cell.

## Decision rule (fixed here)

OFFLINE SEALED-POOL CONFIRMATION READ (VER-1b; owner decision 257, decision 258 option A proposed 2026-10-10; claim ceiling 'descriptive' for the pool; the pool cell claims NO benefit). One flight, one Perception visit and one grouped Solver visit per row of TRAIN Fold A: sample 0 greedy, samples 1-2 at temperature 0.7, all over the SAME state and evidence, committed in flight by saea-commit-plurality-support-v1 at min_support 2. THE FIXED RULE (fixed on SLURP-EVO-FOLD-B-V2 by the VER-1a pool read, docs/readiness/2026-10-10-slurp-ver1a-samples-fold-b-v1; NOT re-tuned on this roster): the support filter over the first n = 3 samples at s = 2 (an entity is kept iff supported by >= 2 of the 3 samples; same type, normalised-filler character F1 >= 0.8), the base answer = sample 0 (the greedy sample) with its own labels, the c3 presence verdict (cell VER-1c's r1-c3 column answered no entity after the registered v4g normaliser) gated by the pre-Solver signature N1 >= theta = 0.2, delivered through the lock's v4g normaliser. THE READS, all from sealed bytes, model-free: (1) CUSTODY (row accounting): 1,080 in, 1,080 out; every row's solver_group carries exactly 3 samples in custody (invariant I7g) with temperatures 0, 0.7, 0.7 and the pinned seeds fragment_seed + 0 + index; the replay of the commit reproduces the sealed delivered text on every row; zero tool calls. (2) PER-SAMPLE scores: each custodied raw sample rendered to one outputs COPY (scripts/analysis/stage3_rollout_score.py --stage render, 3 samples auto-detected) and scored ONCE with the registered scorer, both as sealed (unprojected) and through the lock's delivery rule v4g applied OFFLINE (scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4g; the in-flight cell delivers the unnormalised commit because the loader refuses a deliver_normaliser beside a grouped visit); sample 0 is read against the VER-1c lock column on the same rows as the byte-identity audit of the greedy first sample (llama.cpp greedy decoding is not bitwise reproducible across batch shapes, so equality is measured, not assumed). (3) THE CONFIRMATION: the fixed rule applied to the sealed pool and the VER-1c c3 column by the offline composer (python -B scripts/analysis/slurp_ver1_offline.py --mode read --run-id SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1 --attempt attempt-slurp-native-stage3-ver1b-samples-fold-a-generation-v1 --split train --rows 1080 --n 3 --s 2 --thetas 0.2 --verdict-run SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1:attempt-slurp-native-stage3-ver1c-c3-column-fold-a-generation-v1:r1-c3 --label VER1B-FOLD-A-V1 --sealed-scorer slurp-slu-official-train); reported with the whole-utterance paired bootstrap CI95 (10,000 draws, seed 20260915) against the lock column of VER-1c (the delivering arm, request-identical to today's delivery), against the pool's own sample 0 and against the sealed delivered commit (re-scored), pooled SLU-F1 and intent, false fills removed, non-empty exact rows lost / gained, per-scenario natural and equal-stratum tables. CRITERION, on file BEFORE the flight (owner decision 258 may only tighten it): the rule is CONFIRMED iff its pooled SLU-F1 delta against the VER-1c lock column is at or above the 0.67 pp offline sealed-pool floor of the instrument note (section 2d) AND its CI95 lower bound is above zero AND the intent moves by no more than the 0.67 pp floor; anything else is reported as NOT CONFIRMED with the numbers, never softened. NOTHING IS TUNED OR SELECTED HERE: n, s and theta are the fixed rule's; the read roster is SLURP-EVO-FOLD-A-V2, the tuning roster SLURP-EVO-FOLD-B-V2; a confirmed rule is admitted, if at all, by the owner under its own registration.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four TRAIN Fold A rows (the COMP-1b Fold A smoke prefix) prove FORM and nothing else: the phase-native-module-v1-c4 program loads, the Solver visit fans out to 3 custodied samples (sample 0 at temperature 0, samples 1-2 at 0.7), the plurality-support commit at min_support 2 seals and replays, every request fits, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "offline-sealed-pool",
      "note": "VER-1b makes no effectiveness claim of its own: it seals a 1,080-row x 3-sample pool on TRAIN Fold A (sample 0 greedy, samples 1-2 at temperature 0.7) so that the VER-1 rule -- scoring and selection over the frozen core's own sampled answers -- can be CONFIRMED OFFLINE over sealed bytes, together with the c3 column of cell VER-1c on the same rows, at the 0.67 pp floor of docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d. THE FIXED RULE: n = 3, s = 2, theta 0.2 (support filter over the 3 samples at s = 2, c3 verdict x N1 >= 0.2 gate, v4g) was FIXED on the tuning roster SLURP-EVO-FOLD-B-V2 by the VER-1a pool read and is not re-tuned on the read roster SLURP-EVO-FOLD-A-V2. Any benefit claim belongs to a later flown cell, each of which declares its own block. Owner decisions 139 and 192: the expectation is on file before flight and it is zero because the cell is an asset.",
      "primary_metric": "slu_f1",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 1080,
      "tuning_roster": "SLURP-EVO-FOLD-B-V2"
    }
  }
}
```
