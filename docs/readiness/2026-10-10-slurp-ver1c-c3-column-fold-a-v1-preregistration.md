# Cell VER-1c (verification layer, Fold A c3 verdict column): preregistration

Registered 2026-10-10 at study commit `76a9bfe3e6e228dd709964923b4f3b48fec3dd1d`, before any contact, by script (decision 58) from the committed COMP-1b Fold A fragments and the consumption-module compiler under owner decision 257 (decision 258 option A, proposed). Development numbers only.

| item | value |
| --- | --- |
| base | the COMP-1b composition as a module block on lock v2.2 (agree-vote-seed + centroid-boundary-key ON), Reviewer loop OFF, no tool schema on any role |
| program | `phase-native-module-v1-c4` (ceiling 4 = 2 + (3 - 1)) |
| arms | `r1-c3` (the R1 c3 template, pinned `configs/probes/nx/solver/r1/r1-c3.txt`, sha256 `89b81e97c0c8d5377eff2892fac548ac83fd6a24f61ceb25396a57196bb262dc`), `aa` (twin of `lock`), `lock` (delivering, `configs/probes/slurp_native_role_solver_v2.txt`) |
| design / claim | `same-flight-node-column` / descriptive; the verdict source of the VER-1 rule, `claims_benefit` false, expected effect 0.0 pp |
| rosters | tuning `SLURP-EVO-FOLD-B-V2`; read `SLURP-EVO-FOLD-A-V2` |
| runs | `SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1` / `SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-COLUMN-READ-V1`; pool `SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1` |
| composed config hashes | arm `6d527c13980250b3f5eb0b972407eb809770c77944dbcbc8e5bb40c421aef0dc`; smoke `b254d27058994e5b342f4d1dc9e7c657323048f20a453b090123ae735b5ea3fa` |
| protocol hashes | arm `40dddf78050b968dbbbee124f555c579f620bcd1b416eb8c4dac8db9211dff41`; smoke `5d6590c42c5c643861cb039cce668578e629c5cbdfb0a13ed3fe96bec7880a13` |
| split identity | arm `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |

## Attempt state (no recovery)

The smoke and the arm are FIRST attempts of their run ids. Budgets are single-attempt: smoke 16 model calls, FIT endpoint cap 64 (structural: 4 rows x 4 contacts x 4 endpoints); arm 4,320 model calls, FIT cap 17,280. At most one recovery re-registration per cell.

## Exposure disclosure

the R1 c3 template (r1-c3) was authored from AGGREGATE contrast tables computed on TRAIN Fold A (the R1 tuning roster, docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md), which is this cell's read roster, and then measured on TRAIN Fold B by the NX R1 flights; no utterance text, gold value or note body was read to author it. The VER-1 rule (support filter, c3 verdict x N1 gate, v4g) was FIXED on TRAIN Fold B; the Fold A read here is therefore a confirmation of the RULE on a roster the rule's thresholds never saw, but not an independent roster for the c3 TEMPLATE's authoring tables.

## Decision rule (fixed here)

SAME-FLIGHT NODE-TEMPLATE COLUMN READ AS THE VERDICT SOURCE OF THE VER-1 RULE (VER-1c; NX instrument E1/E2; owner decision 257, decision 258 option A proposed 2026-10-10; claim ceiling 'descriptive': the arm is NOT a nomination). One flight, one Solver visit per row of TRAIN Fold A, 3 arms over the SAME QueryState and evidence: r1-c3 (the R1 c3 template, the same hash-pinned bytes the NX R1 iteration-1 cell flew), aa (the twin, replicate_of lock) and lock (the locked template, delivering, last). Each arm's first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train per arm (never sharded; scripts/analysis/stage3_rollout_score.py --mode supply-variants writes the per-arm first-visit outputs and scores the composer reads). READS: (1) THE TWIN NULL first: aa minus lock on every metric, paired per row, whole-utterance cluster bootstrap (10,000 draws, seed 20260915), reported beside the E1 provisional floor (SLU-F1 1.49 pp, intent 0.65 pp at n = 1,080; borrowed until a node-column cell measures its own null). (2) THE c3 COLUMN: r1-c3 minus lock, pooled SLU-F1 and intent, quoted DESCRIPTIVELY with its CI95 (it gates nothing and nominates nothing; a Fold A c3 loss or gain is information about the verdict source, not a result of this cell). (3) THE VERDICT SOURCE: the c3 presence verdict is the flag 'the r1-c3 answer carried no entity after the registered v4g normaliser' (slurp_ver1_offline.verdict_flags); the number of verdict-empty rows and of verdict-empty rows on empty-gold rows is reported beside the TRAIN Fold B figures of the NX R1 flights so that a drift of the verdict between rosters is visible. (4) THE VER-1 RULE FIXED ON SLURP-EVO-FOLD-B-V2 (support filter n = 3, s = 2; c3 verdict x N1 >= 0.2; v4g) is applied offline to the VER-1b sample pool on these rows with scripts/analysis/slurp_ver1_offline.py --verdict-run; the confirmation criterion is the VER-1b READ row's (SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-POOL-READ-V1). NOTHING IS TUNED OR SELECTED HERE. The delivering arm is the lock: the delivered answer is unchanged by construction at the request level (invariant I7).

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four TRAIN Fold A rows (the COMP-1b Fold A smoke prefix) prove FORM and nothing else: the phase-native-module-v1-c4 program loads, the 3 Solver template arms fan out at the one Solver visit, every arm fits its estimated bound, the arm receipt (saea-supply-variant-arms-v4) and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1": {
      "aa_arm_id": "aa",
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-node-column",
      "note": "VER-1c (level: node column, K = 3 Solver template arms: the R1 candidate r1-c3, the aa twin, the lock). Its role is the VERDICT SOURCE of the VER-1 rule on TRAIN Fold A (the c3 presence verdict feeds the offline composer's --verdict-run); it claims no benefit and nominates nothing, so expected_effect_pp is 0 and claims_benefit is false (the claim field carries the design's ceiling 'nominated', the only value the registration gate admits for a node column; this cell's reading is descriptive). The provisional floor SLU 1.49 pp is borrowed from same-flight-supply-variant (the NX R1 iteration 1 and 2 flights have flown, but their official-score twin nulls are read, not re-used here). The rule that the column feeds was FIXED on SLURP-EVO-FOLD-B-V2; the read roster is SLURP-EVO-FOLD-A-V2. the R1 c3 template (r1-c3) was authored from AGGREGATE contrast tables computed on TRAIN Fold A (the R1 tuning roster, docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md), which is this cell's read roster, and then measured on TRAIN Fold B by the NX R1 flights; no utterance text, gold value or note body was read to author it. The VER-1 rule (support filter, c3 verdict x N1 gate, v4g) was FIXED on TRAIN Fold B; the Fold A read here is therefore a confirmation of the RULE on a roster the rule's thresholds never saw, but not an independent roster for the c3 TEMPLATE's authoring tables. The delivered row is the lock arm: delivered intent and SLU are identical by construction at the request level (invariant I7; reported, never contrasted).",
      "primary_metric": "official: pooled SLU-F1 of the arm's column (slurp-slu-official-train), r1-c3 and aa minus the delivering lock arm (paired row bootstrap), quoted descriptively; the c3 presence verdict flags are the column's product",
      "primary_metric_key": "slu",
      "provisional_floor_pp": {
        "arithmetic": "SLU 1.49 * sqrt(1080 / 1080) = 1.4900 pp (primary), intent 0.65 * sqrt(1080 / 1080) = 0.6500 pp (guard)",
        "intent_accuracy": 0.65,
        "slu_f1": 1.49
      },
      "read_bar": "|aa twin offset| + twin CI95 half-width, per metric, measured in this flight (descriptive: nothing is nominated)",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 1,
        "node": "solver",
        "twin": true
      },
      "tuning_roster": "SLURP-EVO-FOLD-B-V2",
      "variant_cost": {
        "extra_audio_seconds": 6169.06,
        "extra_audio_seconds_per_row_mean": 5.7121,
        "extra_contacts_per_row": 2,
        "extra_perception_contacts_per_row": 0,
        "extra_solver_contacts_per_row": 2,
        "note": "K - 1 = 2 non-delivering Solver arms (the candidate and the twin), each one Solver contact at the one Solver visit; every contact re-sends the row's speech packet, so 2 x the TRAIN Fold A total 3084.5284375 s per flight (review-off base: 2 contacts per row, ceiling 4)"
      }
    }
  }
}
```
