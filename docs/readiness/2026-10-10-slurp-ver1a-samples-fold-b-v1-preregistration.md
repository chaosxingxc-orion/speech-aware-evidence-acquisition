# Cell VER-1a (verification layer, sample pool): preregistration

Registered 2026-10-10 at study commit `f26ada26a618f1aa91b786639a2c004d7c6aeab9`, before any contact, by script (decision 58) from the committed R6-P1 Fold B fragments and the consumption-module compiler under owner decision 257. Development numbers only.

| item | value |
| --- | --- |
| base | the NX R5 composed arm / R6-P1 base: COMP-1b (agree-vote-seed + centroid-boundary-key ON), lock v2.2 compiled blocks, Reviewer loop OFF, no tool schema on any role |
| the one departure | Solver visit grouped at samples 5: sample 0 greedy (`decoding_overrides.greedy_first`), samples 1-4 at temperature 0.7, seed_offset 0; commit `saea-commit-plurality-support-v1` at min_support 3, similarity 0.8 |
| program | `phase-native-module-v1-c6` (ceiling 6 = 1 + 1 x 5); a registered member of the review-off module family |
| delivery | the unnormalised commit (the loader refuses a deliver_normaliser beside a grouped visit); v4g is applied offline |
| design / claim | `offline-sealed-pool` / descriptive; a POOL cell, `claims_benefit` false, expected effect 0.0 pp |
| rosters | tuning `none`; read `SLURP-EVO-FOLD-B-V2` |
| runs | `SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-V1` / `SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-POOL-READ-V1` |
| composed config hashes | arm `139226d3a46324b0533d00bba7e6238dbd5212aafdbd5a2482f8b4079ddcedd5`; smoke `29836a17c5aed96aa510c1ba04cd7034eb82873388bc6226d6ca60a4eae5ad3f` |
| protocol hashes | arm `1d269d930c3178e179fd6afdc249f21b87b712c14032078b6e1dda1d8311074b`; smoke `795724cafdf34fea0c9193639d6aca4ad88dfb91ea27d83e3eea4421834bfb0a` |
| split identity | arm `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; smoke `bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32` |

## Attempt state (no recovery)

The smoke and the arm are FIRST attempts of their run ids. Budgets are single-attempt: smoke 24 model calls, FIT endpoint cap 96 (structural: 4 rows x 6 contacts x 4 endpoints); arm 6,480 model calls, FIT cap 25,920. At most one recovery re-registration per cell.

## Decision rule (fixed here)

OFFLINE SEALED-POOL READ (VER-1a; owner decision 257, 2026-10-10; claim ceiling 'descriptive' for the pool, 'nominated' for any rule selected on it; the pool cell claims NO benefit). One flight, one Perception visit and one grouped Solver visit per row of TRAIN Fold B: sample 0 greedy, samples 1-4 at temperature 0.7, all over the SAME state and evidence, committed in flight by saea-commit-plurality-support-v1 at min_support 3. THE READS, all from this one flight's sealed bytes, model-free: (1) CUSTODY (row accounting): 1,080 in, 1,080 out; every row's solver_group carries exactly 5 samples in custody (invariant I7g) with temperatures 0, 0.7, 0.7, 0.7, 0.7 and the pinned seeds fragment_seed + seed_offset + index; the replay of the commit reproduces the sealed delivered text on every row; zero tool calls. (2) PER-SAMPLE scores: each custodied raw sample rendered to one outputs COPY (scripts/analysis/stage3_rollout_score.py --stage render, five samples auto-detected) and scored ONCE with the registered scorer, both as sealed (unprojected) and through the lock's delivery rule v4g applied OFFLINE (scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4g; the in-flight cell delivers the unnormalised commit because the loader refuses a deliver_normaliser beside a grouped visit); sample 0 is read against the NX R1 / R6 lock column on the same rows as the byte-identity audit of the greedy first sample (llama.cpp greedy decoding is not bitwise reproducible across batch shapes, so equality is measured, not assumed). (3) SELECTION AND SUPPORT: the offline aggregation rules (scripts/analysis/slurp_sample_aggregation_offline_read.py: plurality-support commit at min_support 2 and 3 (s = 2 and 3-of-5 both read offline), greedy-sample-0 default, oracle best-of-5 as an UPPER BOUND) and the candidate-support read (scripts/analysis/slurp_candidate_support_read.py), together with the existing c3 verdict columns of the NX R1 / R6 flights on this roster (grouping: scripts/analysis/group_system_rollouts.py), from which the VER-1 verification rule is SELECTED. Bar: the 0.67 pp offline sealed-pool floor of the instrument note (section 2d). NOTHING IS LOCKED HERE: the pool read selects; a selected rule is flown, if at all, under its own registration (VER-1b) and confirmed on a roster it was not selected on.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the phase-native-module-v1-c6 program loads, the Solver visit fans out to 5 custodied samples (sample 0 at temperature 0, samples 1-4 at 0.7), the plurality-support commit at min_support 3 seals and replays, every request fits, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "offline-sealed-pool",
      "note": "VER-1a makes no effectiveness claim of its own: it seals a 1,080-row x 5-sample pool on TRAIN Fold B (sample 0 greedy, samples 1-4 at temperature 0.7) so that the VER-1 verification rule -- scoring and selection over the frozen core's own sampled answers -- can be selected OFFLINE over sealed bytes, together with the existing c3 verdict columns of the NX R1 / R6 flights on the same roster, at the 0.67 pp floor of docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d. Any benefit claim belongs to a later flown cell or to the read over this pool, each of which declares its own block. Owner decisions 139 and 192: the expectation is on file before flight and it is zero because the cell is an asset.",
      "primary_metric": "slu_f1",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "tuning_roster": "none"
    }
  }
}
```
