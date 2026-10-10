# Preregistration: SLURP test-sample successor 2 -- the NX R5 composed arm on SLURP-TEST-SAMPLE-3010-V1

Registered 2026-10-10 at study commit `e13e25909a85d892b284c77f9f7b733693264bc8`, before any contact (owner decisions 233 and 241). A MILESTONE
read: development evidence under owner decision 28; never a test claim and never the final read. Package `docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1`.

## One-shot semantics

ONE attempt per run id, ever; no smoke on the sample; no recovery; no resume; no re-score; no re-read; no re-projection; no best-of; no
tuning on the sample (decisions 151 / 207 / 213; `contracts.gate_exposure._ExposureAndCarrierMixin._require_final_report_attempt_budget`).
A failed or aborted attempt consumes the milestone; a further milestone needs a fresh run id in a successor allowance under a fresh
coordinator report to the owner. The sealed successor-1 columns are never re-flown, re-scored or re-read.

## The cell

| item | value |
| --- | --- |
| composition | The NX R5 composed arm on the signed test sample: COMP-1b's two components ON (agree-vote-seed, w_agree 1.0, recall k 60, with THIS roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1; centroid-boundary-key) on lock v2.2 (v4g at delivery) with the Reviewer loop OFF (Perception then Solver, 2 contacts per row), the locked Solver template, nothing else -- the R5 DEV cell's bytes with only the roster moved. |
| roster | SLURP-TEST-SAMPLE-3010-V1, 3,010 recordings / 682 prompts, split role final-report, scorer slurp-slu-official-test |
| comparators (SEALED, cross-flight) | `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1` (primary), `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-PLAN-V1` (context) |
| in-chain replicate | NONE, by design (declared DEV flight offset 0.7274 pp SLU-F1 / 0.2 pp intent) |
| runs | `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1` / `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1`; READ `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1` |
| composed config hash | `2eedc9f63f28910d5a491653af814c5be02dcdda8ad94abe9c80529306c36691` |
| protocol hash | `d201732eeee47ddce650eadaf48794330267b6d233d2ead518c35cb660da1a9c` |
| budgets | 6,020 generation calls, 24,080 FIT calls, 16,413 audio seconds, 4.6 GPU h |

## Decision rule (fixed here)

Read SUCCESSOR2-COMPOSED against the SEALED successor-1 COMP-1b column (SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1) on the same 3,010 rows, CROSS-FLIGHT (the columns flew 2026-10-01; nothing is re-flown; there is no in-chain replicate on the sample by design). PRIMARY: official pooled SLU-F1 (slurp-slu-official-test), post-stratified natural mixture (equal-stratum beside it), paired per recording with a prompt-clustered bootstrap, 10,000 draws, seed 20260915. GUARD: intent accuracy (scenario_action exact), same contrast. DECLARED FLIGHT OFFSET o (borrowed from the DEV R5 read, not measured on the sample): |o| = 0.7274 pp SLU-F1 / 0.2 pp intent. HARM MARGIN 2.5 pp (not tighter than the cross-flight sampling floor). NEUTRAL iff the CI95 lower bound of (composed minus COMP-1b) on SLU-F1 and on intent is at or above -2.5 pp and the read is not HARM: an EFFICIENCY RESULT -- the composition keeps COMP-1b's accuracy within what a cross-flight read can see at about half the contacts; never reported as a gain. HARM iff the CI95 upper bound of (composed minus COMP-1b) on SLU-F1 or on intent is below -|o| (a resolved loss beyond the declared offset, owner decision 25). UNRESOLVED iff the lower bound is under -2.5 pp while neither HARM nor NEUTRAL. NOMINATED is NOT a registered outcome of this cell (claims_benefit false): a point above the bar would be REPORTED, never claimed, and would need its own replicated read. Reported beside, CONTEXT ONLY: composed minus the sealed successor-1 PLAN column (intent and SLU-F1; expectation in the facts), per-intent and per-scenario tables in the post-stratified natural-mixture and equal-stratum weightings (58 intents), the recording-channel split, entity TP/FP/FN, and the cost table (contacts and tokens per row against COMP-1b's 12,214 contacts). The verdict word is the coordinator's (owner decision 139). A milestone development read (owner decisions 28, 151), never a test claim.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1": {
      "admission": "no-harm",
      "bar_pp": 2.5,
      "claim": "no-harm",
      "claims_benefit": false,
      "comparator_attempt_id": "attempt-slurp-milestone-successor1-comp1b-generation-v1",
      "comparator_run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1",
      "declared_flight_offset": {
        "intent_pp": 0.2,
        "scope": "DECLARED, borrowed from the DEV R5 read: the sample has NO in-chain replicate by design",
        "slu_pp": 0.7274,
        "source": "analysis/SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-PAIRED-ANALYSIS-V1/v4g-contrast/report.json decision_rule_arithmetic.delivered (offset_abs_slu_pp 0.7274, offset_abs_intent_pp 0.2): replicate minus the sealed A2 in-chain A/A, DEV-2000-ADDED, n 1,000"
      },
      "design_statement": "CROSS-FLIGHT AGAINST SEALED COLUMNS, NO IN-CHAIN REPLICATE, BY DESIGN: the allowance permits exactly one new generation run id, the sample's successor-1 PLAN and COMP-1b columns are sealed and must not be re-flown, and a second composed flight would consume a second attempt. Instrument rule 4 (docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 3) refuses 'a single cross-flight contrast against an older sealed comparator with no in-chain replicate' outright (stage3_effect_floor_check.py would report this declaration as a blocking cross-flight-no-replicate finding; the gate's scope test is the 'stage3' token in the fragment stem or experiment id, which this cell, like successor 1, does not carry, so today the gate does not see the cell and the refusal is NOT mechanically enforced). It is declared in this honest form rather than relabelled; the owner/coordinator must rule on the exception before the flip (README open question 1). The DEV flight offset (0.73 pp SLU / 0.20 intent) is carried as the declared offset. RULED 2026-10-10: owner decision 250 (option A) accepts the documented exception to rule 4 -- design cross-flight-no-replicate, declared DEV flight offset 0.7274 pp SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, development evidence under decision 28; no in-chain replicate on the sample.",
      "expected_effect_basis": {
        "dev_point": {
          "intent_ci95": [
            -0.5056,
            1.5167
          ],
          "intent_pp": 0.5,
          "slu_ci95": [
            -0.2904,
            2.8036
          ],
          "slu_pp": 1.2429,
          "source": "same report, delivered 'claim: a2_arm -> composed' (composed minus the sealed A2 arm); satisfies NEUTRAL"
        },
        "primary": "official pooled SLU-F1 (slurp-slu-official-test), post-stratified natural mixture, composed minus the SEALED successor-1 COMP-1b column",
        "reading": "+1.24 pp is the DEV point of composed minus COMP-1b (CI95 [-0.29, +2.80], NEUTRAL). It sits under the 2.5 pp bar a cross-flight read can resolve, so the cell claims NO benefit: its registered claim is the EFFICIENCY RESULT (2 contacts per row against about 4 for COMP-1b, so about half the contacts) plus the v4g delivered gain. Under ONE normaliser the DEV graph-and-supply effect is only +0.27 pp (v4g(A2 arm) -> composed), so most of the +1.24 is the v4g delivered gain, which the DEV rule selection makes in-sample there and a fresh sample tests honestly.",
        "vs_plan_context": {
          "coordinator_brief_stated_pp": {
            "intent": 5.3,
            "slu": 2.0
          },
          "intent_less_declared_offset_pp": 6.1,
          "intent_sum_pp": 6.3,
          "note": "CONTEXT only, never the bar. Components are all published: successor-1 test COMP-1b minus PLAN (intent +5.80, SLU +0.79, post-stratified) plus the R5 DEV composed minus COMP-1b (intent +0.50, SLU +1.24). The brief said intent 'about +5.3'; 5.80 + 0.50 is 6.30, 6.10 after the 0.20 intent offset, so the brief's 5.3 is not reproduced by the stated components (see open question 2 in the README). SLU (about +2.0) = 0.7945 + 1.2429 = 2.04 before any offset. The coordinator may re-declare.",
          "slu_less_declared_offset_pp": 1.31,
          "slu_sum_pp": 2.04
        }
      },
      "expected_effect_pp": 1.2429,
      "expected_effect_status": "the R5 DEV point (owner decision 139: a measured number, not a prior), declared at registration",
      "harm_margin_pp": 2.5,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 2.5,
        "slu_f1": 2.5
      },
      "measurement_design": "cross-flight-no-replicate",
      "note": "SUCCESSOR-2 = the NX R5 composed arm on the signed test sample (owner decisions 233 and 241). Primary: official pooled SLU-F1 (post-stratified natural mixture; equal-stratum beside it); guard: intent (scenario_action exact). Contrast: composed minus the SEALED successor-1 COMP-1b column (primary comparator, same components minus review-off and v4g); beside it composed minus the SEALED successor-1 PLAN column. No claim of benefit. tuning_roster / read_roster (item D3): the vote pool and the centroid key are TRAIN construction artifacts, the v4 rule set behind v4g was selected on the A2 DEV pool and confirmed on TRAIN Fold A and Fold B, and COMP-1b was selected on DEV-2000-ADDED; all are disjoint from the sample by its disjointness proof (docs/checks/speech-aware-evidence-acquisition/2026-09-27-slurp-test-sample-roster/disjointness.json, CLEAN); nothing was chosen or tuned on the sample.",
      "own_null": {
        "flag": "NO OWN NULL EXISTS FOR SLURP-TEST-SAMPLE-3010-V1 (no A/A pair has flown on it, and the allowance names no second PLAN read id that could measure one). Declared guard = the DEV-2000-ADDED own null scaled by sqrt(913 / 682) at the PROMPT level (rho = 1, conservative: every recording of a prompt moves together; design note section 4 'Sample paired h 1.33'). The recording-level scaling sqrt(1000 / 3010) is given beside it and is the OPTIMISTIC bound; the read reports both.",
        "h_intent": 1.3329,
        "h_intent_recording_scaled": 0.664,
        "h_slu": 1.4492,
        "h_slu_recording_scaled": 0.7219,
        "kind": "FALLBACK-SCALED-NOT-MEASURED",
        "n": 3010,
        "n_prompts": 682,
        "note": "reused from successor 1 unchanged (no own null exists for the sample; fallback scaled, flagged)",
        "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair); scaling: docs/readiness/2026-09-27-slurp-test-sample-design-v1.md section 4"
      },
      "owner_ruling_decision_250": {
        "date": "2026-10-10",
        "decision": 250,
        "option": "A",
        "ruling": "The successor-2 test read carries the documented exception to instrument rule 4: design cross-flight-no-replicate, declared DEV flight offset 0.7274 pp SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, development evidence under decision 28; no in-chain replicate on the sample.",
        "source": "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md, section 'Decisions 249-252 ruled by the owner, 2026-10-10'"
      },
      "plan_comparator_attempt_id": "attempt-slurp-milestone-successor1-plan-generation-v1",
      "plan_comparator_run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-PLAN-V1",
      "primary_metric": "official pooled SLU-F1 (slurp-slu-official-test), composed minus the sealed successor-1 COMP-1b column beyond the declared DEV flight offset; intent accuracy (scenario_action exact) the non-inferiority guard",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-TEST-SAMPLE-3010-V1",
      "roster": "TEST-SAMPLE (SLURP-TEST-SAMPLE-3010-V1, split identity 0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9), 3,010 recordings / 682 prompts",
      "rows": 3010,
      "tuning_roster": [
        "slurp-train-construction-pool-agree-kprobe-r01-excluded",
        "SLURP-EVO-FOLD-A-V2",
        "SLURP-DEV-2000-ADDED-V1"
      ]
    }
  }
}
```

## Blockers before the flip

1. OWNER SIGNATURE: RESOLVED. The owner signed the successor-2 allowance on 2026-10-10 (decision 251, option A): status authorised, sha256 4e04b23f89b9eb06c1b228649a6f991fb9399dea6efbaf4d168a4b731d9e388d, pinned by this cell's owner_allowance.
2. MEASUREMENT RULE: RULED. Owner decision 250 (option A, 2026-10-10) accepts the documented exception to instrument rule 4: design cross-flight-no-replicate, declared DEV flight offset 0.7274 pp SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, development evidence under decision 28; no in-chain replicate on the sample.
3. READER: stage3_paired_read.py --package requires arms.in_chain_replicate and checks both arms against the allowance; this design has none, so the registered driver is the pair-mode wrapper scripts/flights/nx/milestone_successor2_read.sh (see README open question 3).
4. ROOT: countersigns the three DRAFT ledger rows (naming the conversational report of R5's NEUTRAL read to the owner), mints the admission receipt, then repin_cell.py --set-ready mints the cell's own first-phase supply.
5. SERVING/LAUNCH: standard four-slot decoder-only service, clean frozen code, registered FIT, launch gates (as successor 1).

## Prohibitions

- No contact before every blocker above is cleared, root countersigns the rows, mints the decision receipt and the cell is flipped.
- ONE attempt per run id, ever: no re-fly, no recovery, no resume, no re-score, no re-projection, no best-of, no tuning on the sample.
- No smoke on the sample; no re-flight, re-score or re-read of the sealed successor-1 columns; no closure-roster or FULL-test contact.
- No k, tau, fuse_coverage, w_prior, store, release, snapshot, roster, role-graph or geometry change. --allow-output-change is never passed.
- No utterance text, gold label, transcript or model output is printed or persisted by any read.
