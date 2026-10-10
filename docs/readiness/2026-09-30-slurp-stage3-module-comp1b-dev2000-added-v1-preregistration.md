# The consumption module's first end-to-end cell (COMP-1b as a module block on lock v2.1, DEV-2000-ADDED): preregistration

Registered 2026-09-30 at study commit `aa053a2ea`, before any contact (migration step 6; owner
decisions 195, 196, 204). Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| composition | The evidence-consumption module saea-evidence-consumption-module-v1 (profile slurp) compiled onto lock v2.1 (owner decision 204: the v2.0 lock with ONE pin moved, the Reviewer template probes/slurp_native_role_reviewer_v1_g5_v1.txt) with COMP-1b's two components ON -- agree-vote-seed (w_agree 1.0, recall k 60, delivered 8-1-8, THIS roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) and centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) -- and every other catalogued component OFF. Every policy block is the compiler's output; the roster pins are DEV-2000-ADDED's own. |
| roster | DEV-2000-ADDED (SLURP-DEV-2000-ADDED-V1), 1,000 rows, split role dev, scorer slurp-slu-official |
| in-chain A/A | `SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1` (the module's OFF arm on lock v2.1), flown in the same campaign before the arm |
| margins | this roster's own null: h_intent 1.152, h_SLU 1.2525 |
| smoke | four rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-SMOKE-4-FIT-V1` |
| composed config hashes | arm `1f1208d9540051d454a427886d914260aaa20474b8d57cfcfe059bf081ff58eb`; A/A `d01a0fd68e83a491bfed1b2ea23e95ccb3f3ba957d9caf95e0f199dd5e350204`; smoke `67d8be44ead7d882f4a98da82a200f6cb775c828b500831ba4031c58f6ad3fe4` |
| protocol hashes | arm `3315dcdfe2dfcd26c08f7f90067f7dcaad3bc6a55a5ee35a8dbbeb0a61c41efc`; A/A `fb8f7249f5fa95ecaee1fe9233eec163bcf90574933e1e17596b62f99338e54c`; smoke `3e7428d84f16f86dd83ec796a7b6fb68d45540f0b0341f5e0957af62d6cc9067` |
| does it need to fly | This cell does NOT need to fly for the module's end-to-end proof: the byte proof (m6) shows its composed policy blocks equal cell A2's flown arm bytes except the one lock-v2.1 Reviewer pin, and its A/A equals the lock-v2.1 bytes. What a flight would add is (a) the first measured lock-v2.1 A/A on DEV-2000-ADDED and (b) a same-roster re-flight of the admitted COMP-1b bytes under the module on lock v2.1. Whether that is worth about 3.4 GPU-h is the coordinator's decision. |

## Decision rule (fixed here)

Read against the in-chain A/A (the module's OFF arm on lock v2.1) flown in the same campaign. PRIMARY: intent accuracy (scenario_action exact), paired per utterance, 10,000 bootstrap draws. GUARD: official pooled SLU-F1 (slurp-slu-official) non-inferior at this roster's own null (h_SLU 1.2525). REPLICATED: the intent CI95 lower bound above zero, the point at or above the 2.6 pp cross-flight bar at n = 1,000, AND the guard holds. NEUTRAL: both guards non-inferior at the own null (h_intent 1.152 / h_SLU 1.2525) without a replicated gain. HARMFUL: a measured loss on either guard (decision 25). Every verdict carries the per-stratum tables in both weightings. The A/A vs the sealed A2 A/A is reported beside, CONTEXT ONLY (the lock-v2.1 pin plus the recall-k no-op).

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1": {
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The in-chain A/A is the INSTRUMENT, not a claim: the module's OFF arm (every component off) on lock v2.1, which compiles byte for byte to the lock-v2.1 policy blocks on this roster. It is also the first measured lock-v2.1 A/A. Its expected effect is zero by construction.",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the guard",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "replicate_run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-V1",
      "rows": 1000,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-SMOKE-4-V1": {
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM only; scored by no one, read by no one (instrument rule 5).",
      "primary_metric": "intent accuracy (scenario_action exact)",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-V1": {
      "claim": "nominated",
      "claims_benefit": true,
      "expected_effect_pp": 4.6,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "Migration step 6: COMP-1b as a module block on lock v2.1. expected_effect_pp 4.6 is the A2 read's intent point estimate (docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md: intent +4.60 pp CI95 [+2.58, +6.73], official SLU-F1 +0.53 pp [-1.04, +2.09] against the in-chain A/A (A2 REPLICATED and ADMITTED, lock v2.0 bytes)); owner decision 139: a number measured on a sealed read is not a prior. It was measured on lock v2.0 bytes; this cell's base is lock v2.1, whose one moved pin (the G5 Reviewer template) read no harm and no gain (docs/results/2026-09-30-slurp-v2-1-lock-v1.md), and its in-chain A/A is the module's OFF arm on the same lock, so the contrast is the two components alone. The SLU-F1 guard is this roster's own null h_SLU 1.2525 (h_intent 1.152). The expectation comes from a read on THIS roster (A2), so a flight of this cell is a same-roster re-flight of admitted bytes under the module, not an independent replication; nothing in the cell was tuned on DEV-2000-ADDED (the vote pool and the centroid key are TRAIN construction-pool artifacts).",
      "own_null": {
        "h_intent": 1.152,
        "h_slu": 1.2525,
        "measured_offset_slu_pp": -0.25,
        "n": 1000,
        "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair)"
      },
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 (slurp-slu-official, DEV sibling) the non-inferiority guard (owner decision 133)",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "replicate_run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1",
      "roster": "DEV-2000-ADDED (SLURP-DEV-2000-ADDED-V1, split identity ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67)",
      "rows": 1000,
      "slu_guard_h": 1.2525,
      "tuning_roster": "slurp-train-construction-pool-agree-kprobe-r01-excluded"
    }
  }
}
```

## Where the declared 4.6 pp comes from

The A2 read, docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md: intent +4.60 pp CI95 [+2.58, +6.73], official SLU-F1 +0.53 pp [-1.04, +2.09] against the in-chain A/A (A2 REPLICATED and ADMITTED, lock v2.0 bytes). It was measured on this roster and on lock v2.0 bytes; a flight of this cell is a
same-roster re-flight of those bytes under the module on lock v2.1, not an independent replication.

## Prohibitions

- No flight before the coordinator decides it is needed, root countersigns the rows, mints the decision receipt and the three cells are flipped in one converged cycle.
- No re-flying of any sealed cell; no test, DEV-1000 or Fold B contact.
- No component beyond the declared block; no k, tau, fuse_coverage, w_prior, store, release, snapshot, roster or geometry change outside the compiler.
- No paper-scale profile. --allow-output-change is never passed.
