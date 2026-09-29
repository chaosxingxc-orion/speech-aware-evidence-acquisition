# Cell E4-1 (same-flight shadow relisten, TRAIN Fold A): preregistration

Registered 2026-09-29 at study commit `b54dfb4de`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decision 185. Development numbers only.

## The cell

| item | value |
| --- | --- |
| base | the retained AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (65.1575 / 85.8333) |
| program | `phase-native-candidates-review-revise-relisten-v1` (ceiling 17) -- the only base change besides the relisten block |
| relisten block | `{"blind_template_id": "slurp_relisten_blind_v1", "confirm_template_id": "slurp_relisten_confirm_v1", "delivery": "shadow", "max_slots_per_row": 3, "policy": "saea-obs-targeted-relisten-v1", "value_max_words": 8}` |
| delivery | shadow: the delivered answer is the AGREE form's own |
| design / claim | `same-flight-shadow-relisten` / `nominated`; `shadow_delivery` true |
| columns | `relisten-replace-only`, `relisten-replace-drop-unheard`, each against the delivered column |
| primary / guard | official pooled SLU-F1 (micro) / intent identical by construction, tested per row |
| expected effect | 0.0 pp for both columns; `claims_benefit` false |
| ceilings | 4.09 pp SLU upper bound; 35 re-listen-addressable items; 253 SPURIOUS (74 with the filler in the note); hearing share 17-74 % |
| provisional null | 0.3163 pp SLU (0.735 x sqrt(200 / 1080)) |
| rosters | tuning `none`; read `SLURP-EVO-FOLD-A-V2` |
| runs | `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1` / `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1` |
| composed config hashes | arm `76d777523e93b1eac72a2d5174b1484e600231269f415e10545a3fce7c35a083`; smoke `c6be9b29ad5947066a4d69455da0becf7b2a1859158e8688c6e5079a362da077` |
| protocol hashes | arm `e6210a6ad008f669078af191feea236b1f3fd07d4288a789dd7fa58f3c102122`; smoke `e07d5bb93eb7025ca83fec88f29dcacf7e78834f9616f41891b3bd58ba428ae5` |
| split identity | arm `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `a5a7b7dee90dc1ff4a29fe05593fd8980d1e01aa74b8c2a15c2e5184c2e5fb0a` |

## Decision rule (fixed here)

SAME-FLIGHT SHADOW-COLUMN READ (owner decision 185; design section 4 with the section 8 rulings; claim ceiling 'nominated'). The DELIVERED column is the flight's own sealed answer, scored once by the flight with slurp-slu-official-train. Each shadow column -- relisten-replace-only (a: the section 1 acceptance rule) and relisten-replace-drop-unheard (b: a, plus dropping an entity when both contacts vote unheard) -- is rendered by the pure bind() from the same flight's sealed saea-relisten-v1 receipts and trace (AT1: a row with no accepted replacement and no drop renders byte-identical to the delivered text) and scored ONCE with slurp-slu-official-train through core.scoring_batch.score_complete_derived_copy; each contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260915). PRIMARY: official pooled SLU-F1 (micro), shadow column minus delivered column. GUARD: intent is identical between each shadow column and the delivered column BY CONSTRUCTION (bind() never re-opens the decided intent); it is tested per row and the read REFUSES on any difference. THE BAR: the design's own null (ruling 7: 'the bar is the twin/shadow null'), provisional until this cell measures it: scripts/checks/stage3_effect_floor_check.py design same-flight-shadow-relisten, 0.735 x sqrt(200 / n) = 0.3163 pp SLU-F1 at n = 1080. Per column: NOMINATED iff the SLU-F1 CI95 lower bound is above zero AND the point delta exceeds 0.3163 pp AND the intent guard holds; SHADOW HARM iff the SLU-F1 CI95 upper bound is below zero AND the point delta's magnitude exceeds 0.3163 pp; otherwise NOT NOMINATED (within the null). The two columns are two pre-declared rules read from one contact stream; no rule search (decision 179). A nomination claims nothing at system level: promotion means binding in delivery and a full-system read against an in-chain A/A (design section 4). Descriptive, never gating: saves and harms by error kind (gold read on the scoring side only), the per-type table, the blind-disposition and confirm-vote tallies, and equal-scenario weighting; every verdict carries the per-scenario table.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The required 4-row charged dry run (design section 6 step 2). Four Fold A rows chosen to exercise both relisten contacts (>= 3 delivered AGREE entities and an unstable entity set; 12 blind contacts on the sealed AGREE answers). It passes iff every row with a delivered entity seals saea-relisten-v1, at least one forced-choice contact fires, the realised contact count equals the AGREE-form contacts plus the receipts' contacts_used, nothing truncates, the delivered text is untouched, both shadow columns render and there are 0 intent differences. Never scored for benefit, never read.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1": {
      "ceilings": {
        "hearing_share": "17 % (71 / 407 visible hearing/span origin) to 74 % ((71 + 229 undetermined) / 407) of the delivered gold-side errors (spec section 8 ruling 1); 4.09 x p spans about 0.71-3.0 pp",
        "relisten_addressable_boundary_near_format": "35 of 142 BOUNDARY + NEAR + FORMAT items (node-gain ledger section 5.2)",
        "spurious": "253 SPURIOUS predictions, 74 of them with the predicted filler in the Perception note (ledger section 5.2); column (b) targets these",
        "upper_bound_pp_slu": "4.09 pp SLU-F1 (NEAR + WRONG-VALUE hearing class, 97 items, isolated; spec section 2), 0 pp intent by construction"
      },
      "claim": "nominated",
      "claims_benefit": false,
      "columns": [
        "relisten-replace-only",
        "relisten-replace-drop-unheard"
      ],
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-shadow-relisten",
      "note": "Ruling 7: both columns declare expected_effect_pp 0.0 with claim ceiling 'nominated', since no measured analogue exists (E-C3 is unflown; VERIFY-1's +1.40 is a precision filter, not a re-listen). claims_benefit is false for both. The ceilings are stated beside, never as the expectation: the upper bound is 4.09 pp SLU-F1 (NEAR + WRONG-VALUE, 97 items, isolated) and 0 pp intent by construction; re-listen-addressable BOUNDARY + NEAR + FORMAT 35 of 142 items; SPURIOUS 253 predictions, 74 of them with the filler in the Perception note (column b's target); hearing share 17-74 % of the 407 delivered gold-side errors, so 4.09 x p spans about 0.71-3.0 pp. The bar is the design's own null, provisionally 0.3163 pp SLU-F1 at n = 1080 (0.735 x sqrt(200 / 1080), the ROLL-AA anchor the gate registers for same-flight-shadow-relisten). Nothing was tuned on any roster: tuning_roster none; the read roster is TRAIN Fold A.",
      "per_column_expected_effect_pp": {
        "relisten-replace-drop-unheard": 0.0,
        "relisten-replace-only": 0.0
      },
      "primary_metric": "official pooled SLU-F1 (micro), each shadow column minus the delivered column; intent identical between columns by construction, tested per row as a guard",
      "provisional_floor_pp": {
        "arithmetic": "0.735 * sqrt(200 / 1080) = 0.3163 pp (ROLL-AA anchor, provisional)",
        "intent_accuracy": 0.0,
        "slu_f1": 0.3163
      },
      "read_bar": "the design's own twin/shadow null (ruling 7); provisionally the floor above, per column",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 1080,
      "shadow_delivery": true,
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds_blind_on_the_sealed_agree_answers": 3290.3193,
        "extra_audio_seconds_if_every_confirm_fires": 6580.6385,
        "extra_audio_seconds_max": 18507.1706,
        "extra_audio_seconds_per_row_mean_max": 17.1363,
        "extra_contacts_blind_on_the_sealed_agree_answers": 1018,
        "extra_contacts_blind_per_row_mean": 0.9426,
        "extra_contacts_confirm": "one per blind contact that disagrees, is unheard or is unparsed; at most 1018 (all fire -> 2036 extra contacts)",
        "extra_contacts_per_row_max": 6,
        "note": "up to 6 extra contacts per row (3 blind + 3 confirm), each re-sending the row's full speech packet, so the flight's extra audio is at most 6 x the Fold A total 3084.5284375 s = 18507.1706 s; on the sealed AGREE answers the blind contacts would number 1018 (0.9426 per row) re-sending 3290.3193 s, and at most as many confirm contacts"
      }
    }
  }
}
```

## Prohibitions

No test-split, Fold B or DEV contact; no re-flying of the AGREE arm; no second factor; no live delivery of a relisten
value; no transcript state; no Whisper or ASR contact; no paper-scale profile; no flight before the receipt is minted
and the cells flipped; no column score before the READ row is countersigned; no system-level claim;
`--allow-output-change` never passed.
