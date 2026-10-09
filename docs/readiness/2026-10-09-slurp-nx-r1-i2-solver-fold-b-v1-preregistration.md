# Cell NX-R1-I2-SOLVER (node-extreme programme round R1 iteration 2, Solver template column): preregistration

Registered 2026-10-09 at study commit `c87662de068d7b5bd896db2afd8e285e5ff8f334`, before any contact, by script (decision 58) from the P-SV-4 Fold B fragments and the consumption-module compiler under the NX programme (owner decisions 228-234). Development numbers only.

| item | value |
| --- | --- |
| base | the COMP-1b composition as a module block on lock v2.1 (agree-vote-seed + centroid-boundary-key ON), Reviewer loop OFF, no tool schema on any role |
| program | `phase-native-module-v1-c8` (ceiling 8 = 2 + (7 - 1)) |
| arms | `r1-i2-c1` .. `r1-i2-c5` (candidates, pinned under `configs/probes/nx/solver/r1/`), `aa` (twin of `lock`), `lock` (delivering, `configs/probes/slurp_native_role_solver_v2.txt`) |
| design / claim | `same-flight-node-column` / `nominated` |
| primary | node-local exact_set_normalised (E2 v2: entity exact-set per row after the cell's delivery normaliser; raw exact-set diagnostic), quoted on official pooled SLU-F1 through the E3 exchange rate; guard official intent (rows differing <= 7) |
| expected effect | 1.54 pp (the ROUND, carried by r1-i2-c3), `claims_benefit` true; provisional floor SLU 1.49 pp |
| rosters | tuning `SLURP-EVO-FOLD-A-V2`; read `SLURP-EVO-FOLD-B-V2` |
| runs | `SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-COLUMN-READ-V1` |
| composed config hashes | arm `c8befb55794bc8d10d4b08471b87467663b643b51ecd958f80feb403de04bc09`; smoke `5e42312b6cc887813fe94c4c9698723ce727f29a0a483c086f51a54d0c7fe686` |
| protocol hashes | arm `0b0ee61e84deec7629e0cd6610701be724e57999e3c9a13b19fb0eac203a837f`; smoke `d465bc302b8692f13de53424b924f569241252795912555bb8352981c17e68a0` |
| split identity | arm `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; smoke `bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32` |

## Attempt state (no recovery)

The smoke and the arm are FIRST attempts of their run ids. Budgets are therefore single-attempt: smoke 32 model calls / 82 speech-seconds, FIT endpoint cap 128 (structural: 4 rows x 8 contacts x 4 endpoints); arm 8,640 / 25,239 speech-seconds, FIT cap 34,560. A recovery re-registration, if one is ever needed, must re-derive the run-cumulative generation budget (earlier attempts' spend plus the new attempt's worst case) and keep the FIT cap structural. At most one recovery re-registration per cell.

## Decision rule (fixed here)

SAME-FLIGHT NODE-TEMPLATE COLUMN READ (NX programme C0.2/C2 R1; instrument E1/E2; claim ceiling 'nominated'). One flight, one Solver visit per row, seven arms over the SAME QueryState and evidence: r1-i2-c1 .. r1-i2-c5 (hand-written candidates), aa (the twin, replicate_of lock) and lock (the locked template, delivering, last). Each arm's first answer is read through the E2 reader (scripts/analysis/slurp_nx_solver_column_read.py, schema v2) in two views: the node-local primary is exact_set_normalised = the entity exact-set per row of the answer AFTER the cell's own delivery normaliser (the delivered-equivalent answer, derived by the official column scorer's own function: the delivered row's sealed normaliser, v3 cited-answer unwrap, SLURP deliver projection), paired per row against lock, with the whole-utterance cluster bootstrap CI95 (10,000 draws, seed 20260915) and the paired Wilson share of the discordant rows; secondaries parse_valid, empty_gold_false_fill and nonempty_exact, likewise on the normalised answers, with per-slot-type counts. The RAW first-answer exact-set and its secondaries, and the per-arm table of rows whose raw exact-set flipped after normalisation, are reported as diagnostics and gate nothing. Each arm's column is also rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (never sharded); official contrasts are paired ROW bootstraps (cluster key sample_id, the stage3_paired_read constraint for column arms, 10,000 draws, seed 20260915), the whole-utterance number beside. (1) THE TWIN NULL: aa minus lock on every metric; the bar = |aa - lock offset| + its CI95 half-width, reported beside the design's provisional floor (SLU-F1 1.49 pp, intent 0.65 pp at n = 1,080; borrowed from same-flight-supply-variant until this cell measures its own null). (2) THE CONTRAST per candidate X: NOMINATED iff (a) the node-local normalised exact-set (exact_set_normalised) CI95 lower bound > 0, AND (b) no normalised secondary loss (parse_valid or nonempty_exact lower, or empty_gold_false_fill higher, with a CI95 excluding zero), AND (c) the intent guard holds: rows whose official intent correctness differs from lock <= 7 (0.65 pp of 1,080) or the official intent delta CI95 contains zero, AND (d) the official pooled SLU-F1 point delta exceeds the twin's SLU bar. HARM iff (a') the normalised exact-set CI95 upper bound < 0. Among several NOMINATED arms the best node-local point estimate wins (ties: fewer words). PLATEAU RULE (programme C0.4): two evaluated rounds without a NOMINATED arm lock the delivering template and close the node. A nomination is confirmed once on TRAIN Fold A as a two-arm column before any lock; it admits nothing by itself. The delivering lock arm's own offline post-processing columns v4 and v4g are read beside (analysis recipe, offline_columns). THIS IS THE SECOND AND LAST EVALUATED ROUND of R1 under the plateau rule: if no arm is NOMINATED here the delivering template is locked and the node closes. The iteration-1 arm r1-c5 does NOT fly in this column; each iteration-2 arm is also set beside iteration-1 r1-c5 in a cross-iteration table that is DESCRIPTIVE only (different flights, different offsets: no claim, no nomination, no input to the rule above). NODE-LOCAL PRIMARY MEASURED AFTER THE DELIVERY NORMALISER (registered here because iteration 1 showed the raw primary can be formatting the normaliser already repairs: r1-c5 read raw exact-set +2.50 [+1.02, +4.07] yet -0.15 [-1.23, +0.89] on the official pooled SLU-F1 column). Iteration 1's registered rule and verdict stand as written.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the phase-native-module-v1-c8 program loads, the seven Solver template arms fan out at the one Solver visit, every arm fits its estimated bound, the arm receipt (saea-supply-variant-arms-v4) and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1": {
      "aa_arm_id": "aa",
      "ceiling": {
        "pp": 1.54,
        "roster": "SLURP-EVO-FOLD-B-V2",
        "rows": 48,
        "what": "the predicted +48 raw-exact rows of r1-i2-c3 on Fold B (range [+38, +65]) at the class-split conversion (empty-gold 0.0333 pp, non-empty 0.0563 pp) = +1.54 pp; +2.69 pp at the uniform 0.056 pp per row"
      },
      "claim": "nominated",
      "claims_benefit": true,
      "conversion_basis": "Declared round effect +1.54 pp official pooled SLU-F1 (class-split, the conservative figure; +2.69 pp at the uniform node rate 0.056 pp per raw-exact row) = candidate r1-i2-c3 alone: +48 predicted raw-exact rows on Fold B (candidates README sections 3 and 4), built from the MEASURED iteration-1 paired discordant counts (c3: empty-gold stratum +62, non-empty -12; plus two thirds of c5's +15 carried by the conventions block; less a winner's-curse shrink of about 5 rows). Class-split conversion: an empty-gold row made exact is an emptied false-fill row, worth 0.0333 pp; a non-empty row 0.0563 pp (exchange-rate note). Iteration-1 declared vs measured raw-exact rows were c1 +32 vs -20, c3 +35 gross vs +50, c5 +5 vs +27, c2 +11 vs +12, so conversion-based priors were poorly calibrated and iteration 2 predicts from measured discordant counts instead; the roster is reused (shaped on Fold B tables, read on Fold B again), so the Fold A two-arm confirmation (programme C0.6) is the real guard. The other candidates declare +1.51 (i2-c1), +1.31 (i2-c2), +1.27 (i2-c4), +0.72 (i2-c5) class-split (+2.13, +1.74, +1.57, +0.90 uniform). claims_benefit is true for the ROUND only, carried by i2-c3. The declaration is a registered expectation, never a claim.",
      "expected_effect_pp": 1.54,
      "measurement_design": "same-flight-node-column",
      "note": "NX round R1 iteration 2 (level: node column, K = 7 Solver template arms). Expected effect declared from measured numbers (docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md; docs/readiness/2026-10-09-slurp-nx-r1-iter2-solver-candidates-v1/README.md section 4), Declared round effect +1.54 pp official pooled SLU-F1 (class-split, the conservative figure; +2.69 pp at the uniform node rate 0.056 pp per raw-exact row) = candidate r1-i2-c3 alone: +48 predicted raw-exact rows on Fold B (candidates README sections 3 and 4), built from the MEASURED iteration-1 paired discordant counts (c3: empty-gold stratum +62, non-empty -12; plus two thirds of c5's +15 carried by the conventions block; less a winner's-curse shrink of about 5 rows). Class-split conversion: an empty-gold row made exact is an emptied false-fill row, worth 0.0333 pp; a non-empty row 0.0563 pp (exchange-rate note). Iteration-1 declared vs measured raw-exact rows were c1 +32 vs -20, c3 +35 gross vs +50, c5 +5 vs +27, c2 +11 vs +12, so conversion-based priors were poorly calibrated and iteration 2 predicts from measured discordant counts instead; the roster is reused (shaped on Fold B tables, read on Fold B again), so the Fold A two-arm confirmation (programme C0.6) is the real guard. The other candidates declare +1.51 (i2-c1), +1.31 (i2-c2), +1.27 (i2-c4), +0.72 (i2-c5) class-split (+2.13, +1.74, +1.57, +0.90 uniform). claims_benefit is true for the ROUND only, carried by i2-c3. The declaration is a registered expectation, never a claim. Provisional floor SLU 1.49 pp (1.49 x sqrt(1080/1080), borrowed from same-flight-supply-variant, programme/instrument README: iteration 1 has flown but the official-score twin null is read only after this flight, so the borrowed floor stands until the READ measures it), so expected_effect_pp 1.54 sits at about 1.03 x the floor, knowingly at it; the read's bar is the aa twin null measured in this flight, |aa - lock offset| + its CI95 half-width. The delivered row is the lock arm: delivered intent and SLU are identical by construction at the request level (invariant I7; reported, never contrasted). Tuning roster TRAIN Fold A (the contrast tables that shaped the candidates), read roster TRAIN Fold B.",
      "primary_metric": "node-local: exact_set_normalised, the entity exact-set per row of the answer after the cell's own delivery normaliser (E2 reader schema v2, per arm minus lock, paired per row; the raw exact-set is a diagnostic); official: pooled SLU-F1 of the arm's column (slurp-slu-official-train) is the quoted effect through the E3 exchange rate (+0.056 pp per exact-set row); guard: official intent (rows differing <= floor 0.65 pp = 7 rows)",
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
