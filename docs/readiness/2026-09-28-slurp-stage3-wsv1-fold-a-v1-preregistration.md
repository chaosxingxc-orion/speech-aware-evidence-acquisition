# Cell W-SV-1 (same-flight supply-variant, exk30): preregistration

Registered 2026-09-28 at study commit `6cb6086de`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decision 172. Development numbers only.

## The cell

| item | value |
| --- | --- |
| base | the retained AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (65.1575 / 85.8333) |
| program | `phase-native-candidates-review-revise-variants3first-v1` (ceiling 13, uncited) -- the only base change besides the variants block |
| arms (first Solver visit) | `b-exk30` (k 30, fuse 30/30/30), `t-twin` (twin of `a-base`), `a-base` (delivering, k 20) |
| design / claim | `same-flight-supply-variant` / `nominated` |
| primary / guard | official pooled SLU-F1 of the column / intent accuracy |
| expected effect | 0.09 pp (VAR-1 exk30 vs PLANR +0.09 [-1.47, +1.60]); `claims_benefit` false |
| provisional floor | 0.3163 pp SLU (0.735 x sqrt(200 / 1080)); the bar is the twin null |
| rosters | tuning `none`; read `SLURP-EVO-FOLD-A-V2` |
| runs | `SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1` / `SAEA-SLURP-STAGE3-WSV1-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-WSV1-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-WSV1-FOLD-A-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1` |
| composed config hashes | arm `d9f9503ea77877cc0e1bc80285eeeb5515d5e85fc01614edb731c32ce6cee659`; smoke `f51360fa518198d0811cd84d2249d05e8edec0ff5e47d9c92cfea8403725077a` |
| protocol hashes | arm `e9e2fbf7251583409a8b5c5d40885a6c5e967eda1772d93291974b9be4e564f1`; smoke `d32892dade05b17e01daf1965d8d262e4bc5c55ec18cc879119813daee1f7856` |
| split identity | arm `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |

## Decision rule (fixed here)

SAME-FLIGHT COLUMN READ (owner decision 172; claim ceiling 'nominated', Q6 ruling). Every column -- a-base (the delivering arm's first-visit column), b-exk30 and t-twin -- is rendered from the sealed first Solver visit through the delivered row's normaliser and projection (the render refuses on any acceptance-test AT1 failure) and scored ONCE with slurp-slu-official-train through core.scoring_batch.score_complete_derived_copy; each contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260928). (1) THE TWIN NULL: t-twin minus a-base on official pooled SLU-F1 (primary) and intent accuracy (guard); the bar on each metric is |twin offset| + the twin's CI95 half-width (the same law as the cross-flight in-chain A/A), reported beside the provisional floor 0.3163 pp SLU / 0.0000 pp intent (scripts/checks/stage3_effect_floor_check.py, design same-flight-supply-variant: 0.735 x sqrt(200 / 1080)). (2) THE KNOB: b-exk30 minus a-base. NOMINATED iff the SLU-F1 CI95 lower bound is above zero AND the SLU-F1 point delta exceeds the twin bar AND the intent CI95 lower bound is not below minus the twin's intent bar. SOLVER-LOCAL HARM iff the SLU-F1 (or intent) CI95 upper bound is below zero and the point delta's magnitude exceeds that metric's twin bar. Otherwise NOT NOMINATED (within the twin null). A nomination claims nothing at system level: it only sends the exk30 construction to a full-system read against an in-chain A/A. The utterance-level number is reported beside the row-level one and never gates (Q4). Every verdict carries the per-scenario table in both weightings.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-WSV1-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows (the first four of the Fold A roster) prove FORM and nothing else: the 13-ceiling uncited program loads, the three Solver arms fan out at the first visit only, every arm fits its measured bound, the v3 supply-variant receipt and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1": {
      "aa_arm_id": "t-twin",
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.09,
      "measurement_design": "same-flight-supply-variant",
      "note": "The FIRST real same-flight supply-variant cell. The expectation is declared from the measured analogue only (row 139): VAR-1's exk30 arm read against the in-chain request-identical replicate PLANR on the R01C construction roster moved official pooled SLU-F1 by +0.09 pp CI95 [-1.47, +1.60] (docs/results/2026-09-27-slurp-mechanism-synthesis/mechanism-table.json (row C7: 'vs PLANR: ... K30 +0.09 [-1.47, +1.60]') from docs/results/2026-09-25-slurp-var1-complete-evidence.md (exk30 vs plan +1.95 [0.48, 3.45]; planr vs plan +1.87 [0.41, 3.36]; so exk30 vs the in-chain replicate PLANR is +0.09)), so expected_effect_pp is 0.09. That is BELOW this design's provisional floor 0.3163 pp at n = 1080 (0.735 x sqrt(200 / 1080); the ROLL-AA anchor, provisional until this very cell measures the twin null), so a benefit declaration would be refused (effect-below-floor, blocking) and the cell declares claims_benefit false: its first deliverable is the instrument's own twin null on the Solver-local estimand, its second the exk30 column read at that null, whose most likely outcome is NOT NOMINATED. The read's bar is the twin null, not the provisional floor. SLU-F1 primary (the knob changes the exemplar supply, which carries slot annotations; decision 115's shape), intent the guard.",
      "primary_metric": "official pooled SLU-F1 of the Solver-local first-visit column (primary), intent accuracy the guard",
      "provisional_floor_pp": {
        "arithmetic": "0.735 * sqrt(200 / 1080) = 0.3163 pp (ROLL-AA anchor, provisional)",
        "intent_accuracy": 0.0,
        "slu_f1": 0.3163
      },
      "read_bar": "|twin offset| + twin CI95 half-width, per metric, measured in this flight (Q3 ruling)",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 1080,
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds": 6169.057,
        "extra_audio_seconds_per_row_mean": 5.7121,
        "extra_contacts_per_row": 2,
        "note": "K - 1 = 2 extra first-visit Solver contacts per row (B and the twin T); each re-sends the row's speech packet, so the flight's extra audio is 2 x the Fold A total 3084.5284375 s"
      }
    }
  }
}
```

## Prohibitions

No test-split, Fold B or DEV contact; no re-flying of the AGREE arm; no second factor; no paper-scale profile; no
flight before the receipt is minted and the cells flipped; no column score before the READ row is countersigned;
no system-level claim; `--allow-output-change` never passed.
