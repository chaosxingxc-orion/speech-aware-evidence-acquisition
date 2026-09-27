# Cell G5: preregistration

Registered 2026-09-27 at study commit `81307ac3`, before any contact, from the locked PLAN
fragments by script (decision 58) with one pin moved, under owner decisions 127, 135, 138 and 153. Development
numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` (63.6304 / 82.2222) |
| factor | `phase_material.reviewer.instruction_template`: `probes/slurp_native_role_reviewer_v1.txt` -> `probes/slurp_native_role_reviewer_v1_g5_v1.txt` (sha256 `724a437de1eeb1167d11395ad78605d595e324e682cff552c27cb84caa8cef35`) -- the two sentences ordering the task-contract tool retired as item E25 deleted, nothing added, nothing rephrased (deletion-only, proven word by word); 82 -> 31 tokens per Reviewer contact (52 / 82 = 63.4 % of the old instruction was the retired order) |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores and their pins, exemplar k = 20, role graph, every other template, normaliser, scorers, budgets; `phase_tools` absent |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, sealed, never re-flown |
| in-chain replicate | `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1`, the locked form with the OLD instruction re-flown in the SAME campaign chain |
| admission | NO HARM (owner decision 127): intent CI95 lower bound against the in-chain A/A not below -0.9943, SLU lower bound not below -1.2485 (the plan's own Fold A null, PLAN vs PLANr); never reported as a gain |
| ceiling unlocked | a Reviewer no longer ordered to perform an impossible action and to fabricate its result; -51 prompt tokens per Reviewer contact, 52.32 per row at the sealed PLAN rate |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-G5-FOLD-A-V1` / `SAEA-SLURP-STAGE3-G5-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1` / `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-FIT-V1` |
| composed config hashes | arm `4082465a803efd9425e79b05ae2b2a39415dd8958be9fed6768f859aaf73d829`; A/A `fa5f5b2650cd1216d1e47906360c92879225d70828c2b467848fd04a2cb16084`; smoke `57d0ff88bdf8f0c28d418056b20d0fcef48b24589e9980de9b3dfed1a4c7173a` |
| protocol hashes | arm `cc1581f468eb9851a001622c1705e44d2fd421c93f81904fb9ca8277633a18f3`; A/A `cbf039dc491d5238d55a271735abd4a6d8a7179e383e5f8ed327132d001c8c05`; smoke `602e9ef33e626ca4825d4ec6fdd013d09fca372f9f9e8f1138c8071361b98b91` |
| split identity | arm and A/A `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |
| authority | owner decisions 127, 135, 138, 153 (docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md); docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md (G5); docs/receipts/harness-admission.json: the entry whose row is SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1 (status RETIRED, switch class phase_tools, key phase_tools.reviewer, ON = the saea-tool-task-contract-v1 toolkit the anchor-to-B5e cells carried, OFF = absent); the class and status were added to the receipt's switch_rule and status_values by item E25 on 2026-09-20 (schema_history saea-harness-admission-v3). Verdict docs/results/2026-09-20-slurp-b1-notool-verdict.md (owner decisions 55, 56; status NEUTRAL made final by decision 61 in docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md); the lock note docs/results/2026-09-22-slurp-v2-lock-v1.md row 'the Reviewer's native toolkit: phase_tools absent, RETIRED'. docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md (rules 3 and 4, section 2d); the AGREE chain shape docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1; decisions 25, 28, 86, 101, 133 |

## Decision rule (fixed here)

NO-HARM ADMITTED (owner decision 127): against the IN-CHAIN A/A arm flown in the same chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not below -0.9943 pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the guard) is not below -1.2485 pp -- each metric read at its own Fold A own-null half-width (PLAN vs PLANr, docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION: a CI that includes zero and clears the margin is exactly the reading a base item requires (decision 127). The item is NEVER reported as a gain, whatever the point estimate; two base items are never assumed to add, and the cumulative check is the next composed round (decision 138). Every verdict carries the per-scenario table in both weightings, the frontier row (decision 75), the measured Reviewer prompt-token delta per contact and per row, the Reviewer contact rate, and a model-free count of Reviewer responses that narrate a tool call or a tool result on each arm (the downstream failure docs/results/2026-09-26-system-summary001-fidelity-and-feedback-diagnostic.md recorded).

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the locked plan's own form -- the OLD Reviewer instruction -- so the G5 delta is read against a within-chain null. Its expected effect is exactly zero by construction, and a non-zero read on it is a measurement of the instrument, which is what it is for.",
      "primary_metric": "intent accuracy (scenario_action exact) and official pooled SLU-F1, as the instrument",
      "replicate_run_id": "SAEA-SLURP-STAGE3-G5-FOLD-A-V1",
      "rows": 1080
    },
    "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: that the repaired Reviewer instruction loads by its new relpath, that every request fits, that the Reviewer answers on its first contact with no tool call and that the episode completes. Scored by no one, read by no one; under the measurement instrument's rule 5 a batch of four rows can never be evidence of benefit or of harm.",
      "primary_metric": "none (structural form only)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-G5-FOLD-A-V1": {
      "admission": "no-harm",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "harm_margin_pp": 1.2485,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 0.9943,
        "slu_f1": 1.2485
      },
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "A row-127 ENGINEERING-BASE item, admitted on NO HARM and never reported as a gain: expected_effect_pp is 0.0 because the cell registers no effect to look for, claims_benefit is false, and the harm margin is the measured floor of this design at n = 1,080 -- the Fold A own-null half-width of PLAN vs PLANr, SLU 1.2485 (the gate's single harm_margin_pp field, in the floor table's own unit) and intent 0.9943 (the primary metric's own half-width, applied by the read; harm_margin_pp_by_metric). The delta is read against the in-chain A/A replicate flown in the same chain (rule 3), never against the sealed comparator alone. The ceiling the item unlocks is stated in registered-facts-v1.json (ceiling_unlocked); it is a form ceiling, not a task-quality expectation. The read is neutral-by-width-is-admission (decision 127); a measured loss on either metric is HARMFUL (decision 25). Folded into the next composed round for the cumulative check (decision 138).",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
      "replicate_run_id": "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1",
      "rows": 1080
    }
  }
}
```

The arm's block is a NO-HARM declaration: `admission` `no-harm`, `harm_margin_pp` 1.2485 (the gate's single field,
in the floor table's SLU unit, equal to this design's measured floor at n = 1,080) with `harm_margin_pp_by_metric`
intent 0.9943 / SLU 1.2485 applied by the read, `claims_benefit` false, `expected_effect_pp` 0.0, and the in-chain
replicate named. `scripts/checks/stage3_effect_floor_check.py` compares a no-harm margin with the design's SAMPLING half-width (decision 127's own
numbers), never with the rule-3 benefit bar a gain must exceed.

## What the item is, and what it is not

docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md section G5: the Reviewer's committed instruction opens by ordering it to call the task-contract tool 'exactly once through its native function schema' and to 'use only its returned source-bound result'; that toolkit is RETIRED and the audit confirms 0 tool schemas in all 2,590 contacts of the lock arm, so 52 of the instruction's 82 tokens (63 %) order an action the node cannot perform, and the same day's system-summary diagnostic records the downstream consequence: summaries treat textual tool-result claims as execution while the tool event list is empty.

What the repair unlocks (row 127 asks for the ceiling, not a gain): a Reviewer that is no longer instructed to perform an action it cannot perform and to review 'against' a tool result that does not exist -- the standing instruction to fabricate that the 2026-09-26 system-summary diagnostic traced downstream (summaries treating textual tool-result claims as execution while the tool event list is empty). It is the node-side precondition for the typed evidence link (G1/G2) and for any later Reviewer grounding, and it frees 51 prompt tokens per Reviewer contact (52.32 per row at the sealed PLAN rate, 56,508 per 1,080-row flight). No task-quality ceiling is claimed for it and none is needed under row 127.

It is not a mechanism, not a gain and not a component-causal claim. Two base items are never assumed to add; the
cumulative check is the next composed round (decision 138), which is why the pin is also prepared as
`comp2-pin-v1.json` for COMP-2 (decision 153).

## Budgets and failure rule

Arm and A/A each 11,880 generation contacts (run-cumulative), 47,520 FIT endpoints,
33,930 repeated speech seconds, 12.0 GPU hours, one official complete score; smoke
44 / 176 / 117 / 1.0, never scored -- the AGREE arithmetic; the arm's Reviewer
prefill is 51 tokens per contact lighter and no cap is denominated in tokens. Expected spend per 1,080-row cell
about 4,424 contacts and about 3.7 GPU hours at the sealed PLAN arm's own rate. Stop and preserve on the
first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is
proven on a four-row dry run.

## Prohibitions

Never reported as a gain. No paper-scale profile. No confirmatory or test-split contact. No Fold B or DEV read. No
re-flying of the sealed comparator. No second factor and no knob change; the 211 committed configs are not re-pinned.
No flight before root mints the decision receipt and the cells are flipped, and `--allow-output-change` is never
passed.
