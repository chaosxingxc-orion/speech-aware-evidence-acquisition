# SLURP test-sample successor 2: the NX R5 composed arm on SLURP-TEST-SAMPLE-3010-V1

Registered before contact 2026-10-10 at study commit `e13e25909a85d892b284c77f9f7b733693264bc8` (owner decisions 233 and 241). The cell is **held** and
**held** (the allowance was SIGNED 2026-10-10, decision 251 A, sha256 `4e04b23f89b9eb06c1b228649a6f991fb9399dea6efbaf4d168a4b731d9e388d`; root countersigns, mints and flips). Nothing here flies, mints, flips, re-pins or countersigns.

**What it is.** The NX R5 composed arm on the signed test sample: COMP-1b's two components ON (agree-vote-seed, w_agree 1.0, recall k 60, with THIS roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1; centroid-boundary-key) on lock v2.2 (v4g at delivery) with the Reviewer loop OFF (Perception then Solver, 2 contacts per row), the locked Solver template, nothing else -- the R5 DEV cell's bytes with only the roster moved. It is the sealed R5 DEV cell (`slurp-native-stage3-nx-r5-composed-dev2000-added-v1`, COMP-1b on module lock v2.2, review-off, policy
`phase-native-module-v1-c2`, ceiling 2) with the leaves moved that moved A2's arm to the successor-1 COMP-1b cell: the dataset view,
roster receipt, packet promotion receipt, the sample's speech-query vectors, alias and agreement table, the row-scaled budgets, the
final-report split role, the TEST scorer sibling `slurp-slu-official-test`, the one-attempt failure policy, the allowance pin and the run / attempt /
FIT ids. `successor-identity-map.json` lists the replacements and `registered-facts-v1.json` (`composed_config_diffs`) PROVES, from
`core.config.compose`, that nothing else moved: every roster- and role-bound leaf equals the sealed successor-1 COMP-1b cell's value, and
the composition delta (successor-1 COMP-1b to this cell) equals the R5 delta on DEV (A2 arm to R5 composed), path for path. Derived by
`scripts/flights/nx/write_slurp_milestone_successor2_registration.py`.

**Identities.** Cell `slurp-milestone-successor2-composed-v1`, baseline `slurp-milestone-successor2-composed-baseline-v1`, run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1` (attempt `attempt-slurp-milestone-successor2-composed-generation-v1`), FIT `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1` (attempt `attempt-slurp-milestone-successor2-composed-fit-v1`), READ
`SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1`, recipe `slurp-milestone-successor2-composed-paired-analysis-v1`. Roster `SLURP-TEST-SAMPLE-3010-V1` (3,010 recordings / 682 prompts; split identity `0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9`). Sample preparations
(packets, query vectors, alias, agreement table) are successor 1's, reused by pin (`sample_preparation_pins`), never rebuilt.

**One-shot terms (decisions 151 / 207 / 213), carried unchanged.** ONE attempt per id, no smoke on the sample, no recovery, no re-read, no
selection. The two comparators are the SEALED successor-1 columns `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1` (primary; same components minus review-off and v4g) and
`SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-PLAN-V1` (the direct-call-era baseline); nothing is re-flown.

## Cloned from successor 1 (quoted, not redesigned)

From `docs/readiness/2026-10-01-slurp-milestone-successor1-v1/README.md` (custody and execution):

> Owner decision 213 authorizes two fresh 3010-row trajectories sets (6020 total), after the original comparator failed seal serialization. The old comparator, its misleading COMPLETED manifest flag and all raw outputs remain immutable, unread and unscored. Its 12343 contacts are inherited exposure. The old treatment never started. This package permits no recovery, smoke, extra encoding, P-SV-4 dispatch, closure data, or additional carrier.
> The sole code repair affecting this comparison carries owner_allowance through future manifest serialization. The complete role graph, prompts, knowledge sources, model weights, geometry, output cap, roster, thresholds and analysis method are inherited. The separate F1 capabilities remain disabled. The shared registration writer proves the DEV-to-sample composition square; configuration tests prove the original-to-successor baseline equality except identities and preparation ownership. Both own preparation outputs must equal their originals, without opening old model outputs.

From the same README (analysis, fixed before contact):

> Keep COMP-1b expected intent gain 4.6 percentage points, from the existing DEV read, and the complete inherited decision rule and fallback-null disclosure in protocol-registered-v1.json. Do not tune from this sample. This is development milestone evidence, not a final test or superiority claim.
> The analysis-recipe-v1.json retains prompt-cluster pairing, post-stratified natural-mixture and equal-stratum reporting. The committed population-counts-v1.json contains existing aggregate counts; do not open complementary test rows. Gold is confined to official scoring. The analysis uses strata inside the scorer, never a per-row gold bank. No result may be read until both members independently FINALIZE with verified seals and exactly one official score each, and root countersigns the new READ row.

From the successor-1 allowance `milestone_rule`: "This allowance authorizes only the fresh original PLAN versus original COMP-1b comparison on the unchanged 3010-row sample. Keep original scientific settings and registered thresholds. Never use milestone outcomes for tuning. One complete official score per sealed arm; read only after both arms independently finalize with one score each. No reseal, retry or rescore of the old failed comparator."

Cloned files: `registered-facts-v1.json`, `protocol-registered-v1.json`, `generation-plan-registered-v1.json`, `fit-plan-registered-v1.json`,
`analysis-recipe-v1.json`, `population-counts-v1.json` (successor 1's bytes, the same roster), `root-admission-draft-v1.json`,
`read-qualification-v1.md`, `successor-identity-map.json`, the preregistration `docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1-preregistration.md`, fragments
`configs/experiment/slurp-milestone-successor2-composed-v1.json` and `configs/baseline/slurp-milestone-successor2-composed-baseline-v1.json`, the one-cell campaign plan `configs/campaign/slurp-milestone-successor2-composed-v1.json`, and the read wrapper
`scripts/flights/nx/milestone_successor2_read.sh`. Not cloned, because it records a post-hoc defect: `sparse-supply-reader-correction.md`. Not cloned, because it has no
counterpart: successor 1's PLAN plan documents (no new comparator is flown).

## Measurement

`cross-flight-no-replicate` (stated plainly: there is NO in-chain replicate on the test sample, by design -- one new generation id, sealed
comparators that must not be re-flown). n = 3,010 (682 prompts). Primary: official pooled SLU-F1 (`primary_metric_key: slu`),
post-stratified natural mixture (primary weighting) with equal-stratum beside it; guard: intent. `admission: no-harm`, `claims_benefit:
false`, `harm_margin_pp 2.5`, `expected_effect_pp 1.2429` (the DEV point of composed minus COMP-1b). The claim is the
EFFICIENCY RESULT (2 contacts per row; successor 1's COMP-1b flew 12,214 contacts on 3,010 rows, about 4.06 per row) plus the v4g delivered
gain. Declared flight offset (DEV, from the R5 read): 0.7274 pp SLU-F1 / 0.2 pp intent. Guard null: successor 1's FALLBACK
(h_SLU 1.4492, h_intent 1.3329; recording-scaled 0.7219 / 0.664), flagged.
Resampling: prompt-cluster paired bootstrap, 10,000 draws, seed 20260915. Declared effects vs the sealed PLAN column (context):
6.3 pp intent / 2.04 pp SLU-F1 before offsets (see open question 2).

## Budgets

| item | value |
| --- | ---: |
| rows | 3,010 |
| contacts per row (exact, policy c2) | 2 |
| generation calls cap | 6,020 |
| FIT endpoint cap (structural: rows x 2 x (1 + 3)) | 24,080 |
| native task-contract calls cap | 6,020 |
| repeated speech-audio seconds cap | 16,413 |
| planned GPU hours (FIT inclusive) | 4.6 (realised-rate estimate 4.18 h at R5's 24 contacts/min) |
| official complete scoring jobs | 1 |

## The allowance (signed 2026-10-10) and how it was pinned

`docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json` (schema `saea-owner-split-allowance-v1`, status `authorised` since 2026-10-10; `draft-awaiting-owner-signature` at registration) supersedes the successor-1 allowance
(`docs/receipts/owner/2026-10-01-slurp-test-sample-successor1-allowance-v1.json`, sha256 `9073ac919264a28a81c9d87a0d7e142d2a911cda2df8c07f57a67c745a3fb1c7`) by scope "new successor run identities only"; it permits EXACTLY `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1` (read)
and `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1` (preparation). Its `dated_owner_decision` quotes decision 241 and its `first_contact_gate.basis` quotes the R5 result. The
READ id `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1` is a model-free analysis identity, not a permission (as in successor 1). Draft bytes at registration: sha256 `295a570e184589e65104e0d47f09e9393cf8b525cac7a01a221b9b7f48089e6b`.

**Signed 2026-10-10 (decision 251, option A; decisions 249-252 in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`).** Status `authorised`, the owner's words recorded in the signature block; the committed bytes (master `951de831b`) hash to `4e04b23f89b9eb06c1b228649a6f991fb9399dea6efbaf4d168a4b731d9e388d`. `write_slurp_milestone_successor2_registration.py sign` pinned the fragment's `owner_allowance`, both plan documents and the facts to that sha256 and propagated the hashes that depend on the pin (composed config hash, protocol hash, protocol and plan file sha256s) through the package, the preregistration, the root-admission draft and the three DRAFT ledger rows. The cell stays HELD and the rows stay DRAFT: root countersigns, mints, flips (`milestone_successor2_flip.sh`) and re-pins the cell's own supply after the running flight. Held form, reproduced from `contracts.plan.require_owner_split_allowance`: the plan pins the path and the 64-hex sha256 of the committed bytes and refuses on any drift, any status other than `authorised`, any run id outside the permitted list (exactly the two new ids), another carrier, profile or split identity. Decision 250 (option A, same day) rules the documented rule-4 exception: `cross-flight-no-replicate`, declared DEV offset 0.7274 pp SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, no in-chain replicate.

## Blockers before the flip

1. OWNER SIGNATURE: RESOLVED. The owner signed the successor-2 allowance on 2026-10-10 (decision 251, option A): status authorised, sha256 4e04b23f89b9eb06c1b228649a6f991fb9399dea6efbaf4d168a4b731d9e388d, pinned by this cell's owner_allowance.
2. MEASUREMENT RULE: RULED. Owner decision 250 (option A, 2026-10-10) accepts the documented exception to instrument rule 4: design cross-flight-no-replicate, declared DEV flight offset 0.7274 pp SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, development evidence under decision 28; no in-chain replicate on the sample.
3. READER: stage3_paired_read.py --package requires arms.in_chain_replicate and checks both arms against the allowance; this design has none, so the registered driver is the pair-mode wrapper scripts/flights/nx/milestone_successor2_read.sh (see README open question 3).
4. ROOT: countersigns the three DRAFT ledger rows (naming the conversational report of R5's NEUTRAL read to the owner), mints the admission receipt, then repin_cell.py --set-ready mints the cell's own first-phase supply.
5. SERVING/LAUNCH: standard four-slot decoder-only service, clean frozen code, registered FIT, launch gates (as successor 1).

## Open questions (everything successor 1 required that this package could not reproduce without a contact or a ruling)

1. **Rule 4 (RULED: decision 250, option A, 2026-10-10).** Instrument rule 4 refuses `cross-flight-no-replicate` outright (`stage3_effect_floor_check.py --explain` prints
   the refusal for that design; the gate does not scope this cell in by name, exactly as it does not scope successor 1, so its run passes
   without seeing the cell). Successor 1 satisfied rule 3 because its PLAN replicate flew in the same chain. Here the allowance gives one new generation id, so no replicate can fly. The declaration is honest, not relabelled; the
   coordinator/owner must rule an exception (or change the design, e.g. a second composed id, which this brief forbids) before countersigning. RULED A by the owner on 2026-10-10 (decision 250): the documented exception stands.
2. **Declared PLAN-contrast numbers.** The brief states composed-minus-PLAN intent "about +5.3 = 5.80 + 0.50 minus the offset". The stated
   components give 6.30 (6.10 after the 0.20 intent offset); +5.3 needs a 1.0 pp discount that no published number supplies. SLU "about +2.0" is
   0.7945 + 1.2429 = 2.04 undiscounted. Both are recorded with their arithmetic and flagged; they are context only and gate nothing.
3. **Reader.** `stage3_paired_read.py --package` requires `arms.in_chain_replicate` and checks BOTH arm ids against the allowance
   (`_require_final_report_conditions`), and the successor-1 columns are not in this allowance by the "EXACTLY" instruction. The registered driver
   `scripts/flights/nx/milestone_successor2_read.sh` therefore uses the reader's pair mode with the final-report conditions re-stated in the wrapper (TEST scorer, scorer-side
   strata, post-stratified weighting, countersigned READ row, sealed manifests). It is syntax-checked only; it has not been run. A reader change
   (accept sealed comparators by recipe) is the cleaner fix and is out of scope here.
4. **Own supply digest.** The selection-output digest the flip should expect for this cell's own first-phase supply is not recorded in a committed
   receipt for successor 1's COMP-1b (the receipt gives row counts and the pin only); the flip's re-derivation will compare against that supply.
5. **Admission mint / flip / queue wrappers (written 2026-10-10, after the signature).** Cloned from the NX R6 family, ONE cell, NO smoke: `scripts/flights/nx/milestone_successor2_preflip_check.py` (refuses on allowance pin/status/id drift, a registered smoke, a pending pin, an existing attempt), `milestone_successor2_mint_receipt.py` (root's mint of `coordination/slurp-milestone-successor2-composed-v1/root-admission-v1.json`; the two eligible run ids; `--report-date` and `--report-arm` name the conversational R5 report of the allowance first-contact gate), `milestone_successor2_flip.sh` (loop form, refuses without the receipt, writes `/home/chao/ms2-flight-commit.txt`), `milestone_successor2_repin_cell.sh`, `batch_chain_milestone_successor2.sh` (one queue step with `smoke_experiment: null`, which `batch_driver.sh` skips; session `serving-slurp-native-candidate-five-train-a-np4-v1`), and `milestone_successor2_dry_run.py` (the model-free four-row walk on the sample prefix that stands in for the forbidden smoke; root runs it after the flip). None has been run.
6. **READ id in the allowance.** Read as "the run id in the read list, the FIT id in the preparation list"; the analysis READ id is not listed as a
   permission. If the owner wants it listed, that is a one-line change to the draft.

## Ledger and checks

Three DRAFT rows (run, FIT, READ) are appended at the END of `docs/exposure-ledger.md`, root countersignature pending. Preflight:
`tests/unit/test_milestone_successor2_cell_registration.py` (model-free).

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
