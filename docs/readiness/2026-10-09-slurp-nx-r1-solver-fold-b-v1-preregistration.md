# Cell NX-R1-SOLVER (node-extreme programme round R1, Solver template column): preregistration

Registered 2026-10-09 at study commit `50777775b2f6fe0b5e8356d3606fd32aecb0f725`, before any contact, by script (decision 58) from the P-SV-4 Fold B fragments and the consumption-module compiler under the NX programme (owner decisions 228-234). Development numbers only.

| item | value |
| --- | --- |
| base | the COMP-1b composition as a module block on lock v2.1 (agree-vote-seed + centroid-boundary-key ON), Reviewer loop OFF, no tool schema on any role |
| program | `phase-native-module-v1-c8` (ceiling 8 = 2 + (7 - 1)) |
| arms | `r1-c1` .. `r1-c5` (candidates, pinned under `configs/probes/nx/solver/r1/`), `aa` (twin of `lock`), `lock` (delivering, `configs/probes/slurp_native_role_solver_v2.txt`) |
| design / claim | `same-flight-node-column` / `nominated` |
| primary | node-local raw first-answer entity exact-set per row (E2), quoted on official pooled SLU-F1 through the E3 exchange rate; guard official intent (rows differing <= 7) |
| expected effect | 1.8 pp (the ROUND, carried by r1-c1), `claims_benefit` true; provisional floor SLU 1.49 pp |
| rosters | tuning `SLURP-EVO-FOLD-A-V2`; read `SLURP-EVO-FOLD-B-V2` |
| runs | `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1` |
| composed config hashes | arm `a31825ae0c0f8b03312911403c86cee3ee8f03420d2a5cf21860c6ea7284eae2`; smoke `1c407d10926d0357534fb4f5f9193d63e61acb2c4530fdff47b17493cc737a02` |
| protocol hashes | arm `82c4f0a521eeb83e88b6dac0187ce2fb0e03514ffa95971cd50a75c76f1002ae`; smoke `588358086b3e8ccb6ca243929ce4ec9f0b6c5528a4168a9a95679f021060697e` |
| split identity | arm `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; smoke `bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32` |

## Smoke recovery (the cell's single recovery re-registration)

The predecessor attempt made its 32 contacts and failed at runtime.seal() on the template-variant delivery validator (root cause fixed on master in commit 6633c9251, core/flight/runtime.py; tests tests/unit/test_template_variants_delivery.py). The smoke is re-flown whole under the rec3 attempt; the arm is untouched.

AMENDED 2026-10-09 (coordinator ruling, Fable 5.1), twice. rec1 carried the SAME plan budget as the failed attempt although the adapter enforces planned_model_calls and planned_speech_audio_seconds run-cumulatively, so it was refused before any contact (0 contacts). rec2 fixed the generation budget but also scaled the FIT contact_cap by the attempts multiplier (256); the FIT cap is a structural per-attempt number, never run-cumulative, so rec2 was refused pre-contact by the FIT gate (0 contacts; no FIT attempt records exist). Both are pre-contact registration defects of the recovery itself, not flight failures; the single recovery re-registration is amended to rec3: the generation budget stays run-cumulative (64 calls, 164 speech-seconds, SMOKE_ATTEMPTS_BUDGETED) and the FIT cap is the structural formula (fit_contact_cap). The smoke plans therefore carry run-cumulative budgets of 64 model calls / 164 speech-seconds; the FIT endpoint cap is structural, not run-cumulative (128 = 4 rows x 8 contacts x 4 endpoints): the failed attempt spent 32 / 81.453, rec1 and rec2 spent 0, rec3 is budgeted 32 / 82. The arm's budgets are unchanged.

## Decision rule (fixed here)

SAME-FLIGHT NODE-TEMPLATE COLUMN READ (NX programme C0.2/C2 R1; instrument E1/E2; claim ceiling 'nominated'). One flight, one Solver visit per row, seven arms over the SAME QueryState and evidence: r1-c1 .. r1-c5 (hand-written candidates), aa (the twin, replicate_of lock) and lock (the locked template, delivering, last). Each arm's RAW first answer is read through the E2 reader (scripts/analysis/slurp_nx_solver_column_read.py): node-local primary = raw first-answer entity exact-set per row, paired per row against lock, with the whole-utterance cluster bootstrap CI95 (10,000 draws, seed 20260915) and the paired Wilson share of the discordant rows; secondaries parse_valid, empty_gold_false_fill, nonempty_exact and per-slot-type counts. Each arm's column is also rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (never sharded); official contrasts are paired ROW bootstraps (cluster key sample_id, the stage3_paired_read constraint for column arms, 10,000 draws, seed 20260915), the whole-utterance number beside. (1) THE TWIN NULL: aa minus lock on every metric; the bar = |aa - lock offset| + its CI95 half-width, reported beside the design's provisional floor (SLU-F1 1.49 pp, intent 0.65 pp at n = 1,080; borrowed from same-flight-supply-variant until this cell measures its own null). (2) THE CONTRAST per candidate X: NOMINATED iff (a) the node-local exact-set CI95 lower bound > 0, AND (b) no secondary loss (parse_valid or nonempty_exact lower, or empty_gold_false_fill higher, with a CI95 excluding zero), AND (c) the intent guard holds: rows whose official intent correctness differs from lock <= 7 (0.65 pp of 1,080) or the official intent delta CI95 contains zero, AND (d) the official pooled SLU-F1 point delta exceeds the twin's SLU bar. HARM iff (a') the exact-set CI95 upper bound < 0. Among several NOMINATED arms the best node-local point estimate wins (ties: fewer words). PLATEAU RULE (programme C0.4): two evaluated rounds without a NOMINATED arm lock the delivering template and close the node. A nomination is confirmed once on TRAIN Fold A as a two-arm column before any lock; it admits nothing by itself. The delivering lock arm's own offline post-processing columns v4 and v4g are read beside (analysis recipe, offline_columns).

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the phase-native-module-v1-c8 program loads, the seven Solver template arms fan out at the one Solver visit, every arm fits its estimated bound, the arm receipt (saea-supply-variant-arms-v4) and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1": {
      "aa_arm_id": "aa",
      "ceiling": {
        "pp": 1.8,
        "roster": "SLURP-EVO-FOLD-B-V2",
        "rows": 32,
        "what": "the 117 Fold A MISSING entities with the value in the Solver's view (proxy for Fold B), ~32 raw-exact row equivalents at 0.0563 pp per row; the range for c1 is [-0.72, +1.80] pp depending on the precision of its new emissions"
      },
      "claim": "nominated",
      "claims_benefit": true,
      "conversion_basis": "Declared round effect +1.80 pp official pooled SLU-F1 = candidate r1-c1 alone (the value-in-supply extraction arm): docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md section 6 counts 117 MISSING entities whose value is in the Solver's view on Fold A (108 on DEV-2000-ADDED), recovered at the measured M1 delivered-filler conversion 0.2471 (docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md) = 28.9 entities x 0.0621 pp per recovered MISSING entity = +1.80 pp, about 32 raw-exact row equivalents at the node rate 0.0563 pp per raw-exact row (Fold A; DEV sensitivity +1.53 pp, 27 rows). Fold B has no sealed table, so the Fold A counts are its proxy. Harm netting (candidates README section 3): break-even precision of the new emissions 0.318; at the E5-1 precision 0.25 the arm is -0.72 pp. The other candidates declare +0.63 (c2), +0.89 (c3), +0.6 (c4, author prior), +0.28 (c5) and are below the floor alone; claims_benefit is true for the ROUND only, carried by c1. The declaration is a registered expectation, never a claim.",
      "expected_effect_pp": 1.8,
      "measurement_design": "same-flight-node-column",
      "note": "NX round R1 (level: node column, K = 7 Solver template arms). Expected effect declared from measured numbers (docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md; docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md section 4), Declared round effect +1.80 pp official pooled SLU-F1 = candidate r1-c1 alone (the value-in-supply extraction arm): docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md section 6 counts 117 MISSING entities whose value is in the Solver's view on Fold A (108 on DEV-2000-ADDED), recovered at the measured M1 delivered-filler conversion 0.2471 (docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md) = 28.9 entities x 0.0621 pp per recovered MISSING entity = +1.80 pp, about 32 raw-exact row equivalents at the node rate 0.0563 pp per raw-exact row (Fold A; DEV sensitivity +1.53 pp, 27 rows). Fold B has no sealed table, so the Fold A counts are its proxy. Harm netting (candidates README section 3): break-even precision of the new emissions 0.318; at the E5-1 precision 0.25 the arm is -0.72 pp. The other candidates declare +0.63 (c2), +0.89 (c3), +0.6 (c4, author prior), +0.28 (c5) and are below the floor alone; claims_benefit is true for the ROUND only, carried by c1. The declaration is a registered expectation, never a claim. Provisional floor SLU 1.49 pp (1.49 x sqrt(1080/1080), borrowed from same-flight-supply-variant, programme/instrument README: no node-column cell has flown yet), so expected_effect_pp 1.8 sits at about 1.2 x the floor, knowingly near it; the read's bar is the aa twin null measured in this flight, |aa - lock offset| + its CI95 half-width. The delivered row is the lock arm: delivered intent and SLU are identical by construction at the request level (invariant I7; reported, never contrasted). Tuning roster TRAIN Fold A (the contrast tables that shaped the candidates), read roster TRAIN Fold B.",
      "primary_metric": "node-local: raw first-answer entity exact-set per row (E2 reader, per arm minus lock, paired per row); official: pooled SLU-F1 of the arm's column (slurp-slu-official-train) is the quoted effect through the E3 exchange rate (+0.056 pp per raw-exact row); guard: official intent (rows differing <= floor 0.65 pp = 7 rows)",
      "primary_metric_key": "slu",
      "provisional_floor_pp": {
        "arithmetic": "SLU 1.49 * sqrt(1080 / 1080) = 1.4900 pp (primary), intent 0.65 * sqrt(1080 / 1080) = 0.6500 pp (guard)",
        "intent_accuracy": 0.65,
        "slu_f1": 1.49
      },
      "read_bar": "|aa twin offset| + twin CI95 half-width, per metric, measured in this flight",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 5,
        "node": "solver",
        "twin": true
      },
      "tuning_roster": "SLURP-EVO-FOLD-A-V2",
      "variant_cost": {
        "extra_audio_seconds": 18928.78,
        "extra_audio_seconds_per_row_mean": 17.5267,
        "extra_contacts_per_row": 6,
        "extra_perception_contacts_per_row": 0,
        "extra_solver_contacts_per_row": 6,
        "note": "K - 1 = 6 non-delivering Solver arms (five candidates and the twin), each one Solver contact at the one Solver visit; every contact re-sends the row's speech packet, so 6 x the Fold B total 3154.797375 s per flight (review-off base: 2 contacts per row, ceiling 8)"
      }
    }
  }
}
```
