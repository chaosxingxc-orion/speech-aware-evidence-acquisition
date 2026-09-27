# Cell SLOTFILL: preregistration

Registered 2026-09-27 at study commit `583f04c99fc9b5bc8f2179761e210d6439c0a6fe`, before any contact, from the locked PLAN
fragments by script (decision 58) with one key added, under owner decisions 127, 140 and 159. Development numbers only
(owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` (63.6304 / 82.2222) |
| factor | `dispatch` = `{"gc_freeze": true, "recall_prefetch": true, "role_input_offload": true, "schema": "saea-dispatch-slot-fill-v1"}` -- scheduling only, proven byte-identical on the model-free bench |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores and their pins, exemplar k = 20, role graph, every template, normaliser, scorers, budgets |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, sealed, never re-flown |
| in-chain replicate | `SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1`, the locked form without the key, re-flown in the SAME campaign chain |
| admission | NO HARM (owner decision 127): intent CI95 lower bound against the in-chain A/A not below -0.9943, SLU lower bound not below -1.2485; never reported as a gain |
| ceiling | contacts per GPU-hour and empty slot-seconds against the A/A; offline estimate +6.0 % on the bench |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-V1` / `SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1` / `SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-FIT-V1` |
| composed config hashes | arm `4bf5297118adb89e9ace5ea77a3cb662a6743b69f98bd45b3397a17cb67b8697`; A/A `b46c65869b70b61d9105f15493e92511916cb0a6887a0640c96843b72c11c375`; smoke `a3827612c578eba7707b30c4d2c5ad4d38e9c1c999e00aa365a90c49140dbc07` |
| protocol hashes | arm `21381fcae367566af81d3a3bdaa80710bb602fe17e43c9873ec2a2394f091d43`; A/A `3457a9f2a2f5b66f0e0ded4da6942b434f5146dc44c8f5fa151636848f7b3ec3`; smoke `72222cf3e4a30e395651888ca475a693881b899203ed593ff718e19b766fbbde` |
| split identity | arm and A/A `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |

## Decision rule (fixed here)

NO-HARM ADMITTED (owner decisions 127 and 159): against the IN-CHAIN A/A arm flown in the same chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not below -0.9943 pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the guard) is not below -1.2485 pp -- each metric read at its own Fold A own-null half-width (PLAN vs PLANr, docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION (decision 127). The item is NEVER reported as a gain on either metric. Beside the no-harm read, and as the item's declared ceiling, the THROUGHPUT read: contacts per GPU-hour over each arm's contact window and empty slot-seconds from the server's own per-slot task log joined one-to-one to each arm's sealed trace (scripts/analysis/slotfill_gap_decomposition.py, the note's accounting), arm against A/A. Every verdict carries the per-scenario table in both weightings, the frontier row (decision 75), the delivered-answer agreement rate of arm and A/A, and the request-byte comparison of step 2.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the locked plan's own form without the dispatch key, so the SLOTFILL deltas -- quality and throughput -- are read against a within-chain twin.",
      "primary_metric": "intent accuracy (scenario_action exact) and official pooled SLU-F1, as the instrument",
      "replicate_run_id": "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-V1",
      "rows": 1080
    },
    "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: that the dispatch key parses and arms on the resident geometry, that every request fits and that the episode completes and seals. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-V1": {
      "admission": "no-harm",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "harm_margin_pp": 1.2485,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 0.9943,
        "slu_f1": 1.2485
      },
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "A row-127 ENGINEERING-BASE item under owner decision 159, admitted on NO HARM and never reported as a gain: expected_effect_pp is 0.0 because the item changes no byte a node sees, claims_benefit is false, and the harm margin is the measured floor of this design at n = 1,080 -- the Fold A own-null half-width of PLAN vs PLANr, SLU 1.2485 (the gate's single harm_margin_pp field) and intent 0.9943 (the primary metric's own half-width, applied by the read; harm_margin_pp_by_metric). The delta is read against the in-chain A/A replicate flown in the same chain (rule 3). The throughput read is the declared ceiling (throughput_ceiling).",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
      "replicate_run_id": "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1",
      "rows": 1080,
      "throughput_ceiling": {
        "claims_gain": false,
        "metric": "contacts per GPU-hour over the contact window, and empty slot-seconds (server per-slot task log joined to the sealed trace)",
        "note": "a declared CEILING, measured and reported; not an admission criterion and never a quality claim",
        "offline_estimate_gain_pct": 6.0,
        "read_against": "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1"
      }
    }
  }
}
```

## What the item is, and what it is not

What the item unlocks (row 127 asks for the ceiling, not a gain): throughput -- the same contacts in less wall. ROLL-2's slot capacity was 27.3 % empty (8,997 of 32,909 slot-seconds; docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md), reproduced here to the tenth of a second; the first Solver visit alone waited 2.67 s per row on the client. The model-free bench on the locked PLAN cell measured the empty share 15.56 % -> 10.55 % and 2,736 -> 2,899 contacts per hour of contact window (+6.0 %) under the sealed ROLL-2 per-role service times; the honest bound for a flown cell is about +5 % contacts per GPU-hour on a flown cell (the bench's 0.35 s of wall per row against ROLL-2's flown 7.62 s per row), bounded above by lever 1b's +10.1 % for this mechanism; no number is claimed for lever 1a (the flight's 1,055 s of all-slots-empty time is not reproduced on the bench), and the note's +37.6 % lever-1 bound is not approached.

It is not a mechanism any node can observe, not a quality gain and not a component-causal claim. Two base items are
never assumed to add.

## Budgets and failure rule

Arm and A/A each 11,880 generation contacts (run-cumulative), 47,520
FIT endpoints, 33,930 repeated speech seconds, 12.0
GPU hours, one official complete score; smoke 44 / 176
/ 117 / 1.0, never scored. Stop and
preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and
the fix is proven on a four-row dry run.

## Prohibitions

Never reported as a quality gain. No paper-scale profile. No confirmatory or test-split contact. No Fold B or DEV read.
No re-flying of the sealed comparator. No second factor; the committed configs are not re-pinned. No flight before root
mints the decision receipt and the cells are flipped, and `--allow-output-change` is never passed.
