# Cell W5 (slot-side retrieval): preregistration

Registered 2026-09-27 at study commit `29ec0008`, before any contact, from the retained AGREE
arm fragments by script (decision 58) with one store added, under owner decision 170. Development numbers only.

## The cell

| item | value |
| --- | --- |
| base | the retained AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (65.1575 / 85.8333), owner decision 161 |
| factor | `knowledge_stores.slot-exemplars` ADDED: nine slot-bearing TRAIN exemplars per row to the Solver from the R01-excluded pool (release `83f175704a09e1721e4d61666979925133a25ea80fc4918fc68a56e527a122a3`, snapshot content `6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63`), three per intent of the row's retrieval shortlist, nearest by the row's own speech, never one M1 delivers; order table `f12540f19730d713594c4f63ce7b68c66ef508b8bb2dbb897ae9541087aceb96` |
| in-chain replicate | `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (the knowledge wave's shared A/A, registered by the coordinator) |
| primary / guard | official pooled SLU-F1 / intent accuracy (decision 133 scopes intent-primary to intent-acting mechanisms) |
| entity taxonomy | the error-source read's MISSING / SPURIOUS / WRONG-TYPE / BOUNDARY / WRONG-VALUE / NEAR / FORMAT |
| admission | NO HARM: SLU lower bound >= -1.2485, intent lower bound >= -0.9943 |
| runs | `SAEA-SLURP-STAGE3-W5-FOLD-A-V1` / `SAEA-SLURP-STAGE3-W5-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-W5-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-W5-FOLD-A-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-W5-FOLD-A-PAIRED-READ-V1` |
| composed config hashes | arm `31668ed5113b748f3db9f83778a488b01efa42bed66a96725b45813273e25e06`; smoke `8c6740d1b20405d6730bdebc8b255a099c938e5d631f07ca7e4cd016f2614daf` |
| protocol hashes | arm `ab7db61205b8048f2246de1e42ef8c0eda6f59ad472ac5fa45944bf7c04097de`; smoke `f410dfdcf48fb09f7f6f101610f252250eda68454b9addf96be742c51fd300d2` |
| split identity | arm `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |

## Decision rule (fixed here)

NO-HARM ADMITTED: against the knowledge wave's SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 flown in the same chain, the paired CI95 lower bound of the official pooled SLU-F1 delta (PRIMARY -- SLU-F1 is PRIMARY because W5 acts on SLOTS: it adds row-matched slot-bearing TRAIN exemplars to the node that fills slots (the M1 mechanism, whose admitted gains were slot-only: 213 of 277 B1 saves changed only slots), and owner decision 133 makes intent primary only for intent-acting mechanisms. Among the wave's cells W1 (card selection) and W3 (intent contrast) read intent primary; W4 (slot conventions) and W5 read SLU primary -- W5 is the wave's one slot-RETRIEVAL cell (row-matched content keyed by the row's own speech), W4 a card-content cell.) is not below -1.2485 pp AND the paired CI95 lower bound of the intent-accuracy delta (the guard) is not below -0.9943 pp -- each at its own Fold A own-null half-width (docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). A SLU-F1 CI95 lower bound above zero is REPORTED as a development-fold effect beside the no-harm verdict, never as an admission of benefit (the design's benefit floor is 2.5 pp and the measured expectation sits far below it). Every verdict carries the per-scenario table in both weightings, the frontier row (decision 75), the entity item classes of the error-source read (MISSING, SPURIOUS, WRONG-TYPE, BOUNDARY, WRONG-VALUE, NEAR, FORMAT) arm vs A/A, the SPURIOUS count on empty-gold rows, and the realised prompt-token delta per Solver/Reviewer/Planner contact and per row.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-W5-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: the slot-exemplars store loads by its pins, the scope table loads, the Solver receives the nine W5 exemplars beside the M1 twenty, every request fits and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-W5-FOLD-A-V1": {
      "admission": "no-harm",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "harm_margin_pp": 1.2485,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 0.9943,
        "slu_f1": 1.2485
      },
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "W5 acts on SLOTS, so SLU-F1 is primary and intent the guard (owner decision 133 scopes intent-primary to intent-acting mechanisms). The expectation is declared from MEASURED numbers only (row 139). The entity taxonomy is the 2026-09-27 error-source read's (MISSING / SPURIOUS / WRONG-TYPE / BOUNDARY / WRONG-VALUE / NEAR / FORMAT, its entity_items function imported unchanged). On the sealed AGREE rows the W5 block prints the gold (type, value) of 72 MISSING items, but the row's own M1 block already prints 90 MISSING items' values and was not converted; W5 NEWLY prints 9 MISSING and 1 BOUNDARY items (of 173 / 75; of the audit's 157 in-list items at most these). At M1's measured delivered-filler conversion (133 newly correct printed fillers over 0.5719 x 941 printed gold fillers = 0.2471, a lower bound) and the error-source read's isolated pp per repaired item (MISSING 9.80 / 173), the expectation is 0.1355 pp (oracle, every newly printed item converted: 0.5482 pp). The directly measured analogue of more speech-keyed exemplars on a system that already has M1 agrees: VAR-1 on R01C 625, exemplar budget 30 vs 20 read +0.09 [-1.47, +1.60] SLU vs PLANR. Both sit far below the design's 2.5 pp benefit floor at n = 1,080, so a benefit declaration would be refused (effect-below-floor) and the cell is declared NO-HARM: expected_effect_pp 0.0, claims_benefit false, harm_margin_pp 1.2485 (SLU, primary) with intent 0.9943 as the guard. Named harm risks: every one of the 414 empty-gold rows receives nine slot-bearing exemplars (SPURIOUS is the largest error class, 253 items), and on 89 rows the gold intent is outside the shortlist that scopes the block (18 of them intent-correct on AGREE). Read against the shared in-chain A/A flown in the same chain (rule 3).",
      "primary_metric": "official pooled SLU-F1 (primary: a slot-acting mechanism -- slot-side retrieval of row-matched TRAIN exemplars to the Solver -- owner decision 133's scope), intent accuracy the non-inferiority guard",
      "replicate_run_id": "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1",
      "rows": 1080
    }
  }
}
```

## Prohibitions

No test-split, Fold B or DEV contact; no re-flying of the comparator; no second factor; no paper-scale profile; no
flight before the receipt is minted, the shared A/A registered and the cells flipped; `--allow-output-change` never passed.
