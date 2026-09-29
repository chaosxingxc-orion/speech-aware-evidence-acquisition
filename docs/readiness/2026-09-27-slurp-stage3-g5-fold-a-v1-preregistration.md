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
| in-chain replicate | `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` -- COMP-1's in-chain A/A, the locked plan's own request bytes (the OLD instruction), flown in the SAME chain as this arm and shared with COMP-1 under owner decision 160; G5's own A/A `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1` is superseded unflown (see the section below) |
| admission | NO HARM (owner decision 127): intent CI95 lower bound against the in-chain A/A not below -0.9943, SLU lower bound not below -1.2485 (the plan's own Fold A null, PLAN vs PLANr); never reported as a gain |
| ceiling unlocked | a Reviewer no longer ordered to perform an impossible action and to fabricate its result; -51 prompt tokens per Reviewer contact, 52.32 per row at the sealed PLAN rate |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-G5-FOLD-A-V1` / `SAEA-SLURP-STAGE3-G5-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1` / `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-FIT-V1` |
| composed config hashes | arm `94857b99ff43897853100a61d71ad6d7767bd6959fe40c7aee718d7d90308ae8`; A/A `fa5f5b2650cd1216d1e47906360c92879225d70828c2b467848fd04a2cb16084`; smoke `ab8c3f7680889ee2baa1ea84a4c4a8aa2bcfc80b6484083ffd220ffa4562703f` |
| protocol hashes | arm `7244466ab8c29b5970127ec417008b27f4086ed7cba3b2e86e62064df8a6ca7a`; A/A `cbf039dc491d5238d55a271735abd4a6d8a7179e383e5f8ed327132d001c8c05`; smoke `39e356faeac9251a3a82b0fa318f292f1bf0febd43444575725441d25af695b0` |
| split identity | arm and A/A `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |
| authority | owner decisions 127, 135, 138, 153 (docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md); docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md (G5); docs/receipts/harness-admission.json: the entry whose row is SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1 (status RETIRED, switch class phase_tools, key phase_tools.reviewer, ON = the saea-tool-task-contract-v1 toolkit the anchor-to-B5e cells carried, OFF = absent); the class and status were added to the receipt's switch_rule and status_values by item E25 on 2026-09-20 (schema_history saea-harness-admission-v3). Verdict docs/results/2026-09-20-slurp-b1-notool-verdict.md (owner decisions 55, 56; status NEUTRAL made final by decision 61 in docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md); the lock note docs/results/2026-09-22-slurp-v2-lock-v1.md row 'the Reviewer's native toolkit: phase_tools absent, RETIRED'. docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md (rules 3 and 4, section 2d); the AGREE chain shape docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1; decisions 25, 28, 86, 101, 133 |

## Decision rule (fixed here)

NO-HARM ADMITTED (owner decision 127): against the IN-CHAIN A/A arm flown in the same chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not below -0.9943 pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the guard) is not below -1.2485 pp -- each metric read at its own Fold A own-null half-width (PLAN vs PLANr, docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION: a CI that includes zero and clears the margin is exactly the reading a base item requires (decision 127). The item is NEVER reported as a gain, whatever the point estimate; two base items are never assumed to add, and the cumulative check is the next composed round (decision 138). Every verdict carries the per-scenario table in both weightings, the frontier row (decision 75), the measured Reviewer prompt-token delta per contact and per row, the Reviewer contact rate, and a model-free count of Reviewer responses that narrate a tool call or a tool result on each arm (the downstream failure docs/results/2026-09-26-system-summary001-fidelity-and-feedback-diagnostic.md recorded).

## Owner decision 160: one shared in-chain A/A

COMP-1 and G5 each registered an in-chain A/A that re-flies the locked PLAN plan's own request bytes. Owner decision 160 (2026-09-27, docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md row 160) flies ONE of them, COMP-1's `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`, in the same chain as both arms, and re-declares this arm's `replicate_run_id` to it, on a condition checked model-free before any flip: the two A/As' prepared first-phase supply digests and composed request bytes are byte-identical. They are -- proof docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/shared-aa-proof-v1.json (sha256 d3df20acf2845e1e59da23faf777c8de69c1c5e640d420e54d9a47683f98a5e0, verdict IDENTICAL, study commit abf29aec): both A/As' prepared first-phase supplies, minted model-free by core.flight.cli prepare-supply, carry output digest ba5e1faa on all 1,080 rows; their real dispatch against the real llama-server transport with a fake POST produced byte-identical canonical payloads and POST bodies on all 663 contacts of 120 rows under one scratch run id, and byte-identical POST bodies (payloads equal up to the run-id-derived custody hash) under their own run ids; every differing composed-config leaf is bookkeeping except the first-phase recall width k (60 vs 8), which is output-neutral by the equal supply digests.

G5's own A/A pair, `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1` and `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-FIT-V1`, is **superseded unflown**: never flown, never consumed, never deleted; its fragment, plans and exposure rows stay as the record of what G5 registered. The decision rule above is unchanged; "the in-chain A/A" in it now names the shared one. The G5 campaign plan carries the arm alone, the receipt is minted with `scripts/flights/g5/g5_mint_receipt.py --drop-aa`, and the family flips and flies only through `scripts/flights/comp1/comp1_g5_flip.sh` and `scripts/flights/comp1/batch_chain_comp1_g5.sh`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "SUPERSEDED UNFLOWN by owner decision 160: the G5 arm is read at COMP-1's in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1, flown in the same chain; this A/A is never flown and never consumed, and its registration stays as the record of what G5 registered. The A/A replicate is the INSTRUMENT, not a claim: it re-flies the locked plan's own form -- the OLD Reviewer instruction -- so the G5 delta is read against a within-chain null. Its expected effect is exactly zero by construction, and a non-zero read on it is a measurement of the instrument, which is what it is for.",
      "primary_metric": "intent accuracy (scenario_action exact) and official pooled SLU-F1, as the instrument",
      "replicate_run_id": "SAEA-SLURP-STAGE3-G5-FOLD-A-V1",
      "rows": 1080,
      "status": "superseded-unflown (owner decision 160)"
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
      "replicate_note": "RE-DECLARED under owner decision 160 (2026-09-27): COMP-1 and G5 fly in ONE chain with ONE shared in-chain A/A, COMP-1's SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 (registered by docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1); G5's own A/A pair SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1 / SAEA-SLURP-STAGE3-G5-AA-FOLD-A-FIT-V1 is SUPERSEDED UNFLOWN, never consumed and never deleted. The decision's condition was checked model-free before any flip -- proof docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/shared-aa-proof-v1.json (sha256 d3df20acf2845e1e59da23faf777c8de69c1c5e640d420e54d9a47683f98a5e0, verdict IDENTICAL, study commit abf29aec): both A/As' prepared first-phase supplies, minted model-free by core.flight.cli prepare-supply, carry output digest ba5e1faa on all 1,080 rows; their real dispatch against the real llama-server transport with a fake POST produced byte-identical canonical payloads and POST bodies on all 663 contacts of 120 rows under one scratch run id, and byte-identical POST bodies (payloads equal up to the run-id-derived custody hash) under their own run ids; every differing composed-config leaf is bookkeeping except the first-phase recall width k (60 vs 8), which is output-neutral by the equal supply digests. The no-harm rule, the margins and the read are unchanged; only the A/A the delta is read at moved.",
      "replicate_run_id": "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1",
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
