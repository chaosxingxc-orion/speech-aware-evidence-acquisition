# Test-sample milestone MILESTONE-01 (COMP-1b) against MILESTONE-00-PLAN: preregistration

Registered 2026-09-29 at study commit `881b1787c`, before any contact (owner decisions 151 and 202).
A MILESTONE read: development evidence under owner decision 28; never a test claim and never the final read.

## One-shot semantics

ONE attempt per read run id, ever (allowance `milestone_rule` and `attempt_budget`; enforced by
`contracts.gate_exposure._ExposureAndCarrierMixin._require_final_report_attempt_budget`). No re-fly, no recovery, no
resume, no re-score, no re-projection of delivered bytes, no best-of, no tuning on the sample. A failed or aborted
attempt consumes the milestone number; a further milestone needs a fresh run id in a successor allowance under a fresh
coordinator report to the owner. The results are reported as the milestone read of decisions 151 and 202, whatever
they are.

## The cells

| item | value |
| --- | --- |
| composition | MILESTONE-01 is cell A2's arm (COMP-1b) with only the roster moved to the signed test sample: the locked v2.0 plan + (1) the agreement term (w_agree 1.0, recall k 60, delivered 8-1-8) with this roster's own vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1 + (2) the centroid boundary key + (3) no citation contract + (4) nothing else. MILESTONE-00-PLAN is the sealed DEV plan arm (the v2.0 lock as flown) with only the roster moved. |
| roster | SLURP-TEST-SAMPLE-3010-V1, 3,010 recordings / 682 prompts, split role final-report, scorer slurp-slu-official-test |
| comparator / in-chain replicate | `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1`, flown in the same campaign before the arm |
| guard null | FALLBACK (no own null): h_intent 1.3329, h_SLU 1.4492 (DEV-2000-ADDED null x sqrt(913/682)) |
| smoke | none (the allowance names no smoke run id) |
| runs | `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1` / `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1`; `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1` / `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1` |
| composed config hashes | comparator `4abf91b657898788cb6111a1e4001b5debb032161a92d64dd495310c00416014`; arm `10ff1e93ff554dff115b68001a07abbcdfca52d0e0abfa82b755dd890434173e` |
| protocol hashes | comparator `dd6ba1a507cd1b1f0f27587c7668d65c5b3513bf47bf339a60f4183461342a00`; arm `e701e272b48ce84e79647db233e02a1b6a44678f956bc8d7bf87dd5db051cd4a` |

## Decision rule (fixed here)

Read MILESTONE-01 against MILESTONE-00-PLAN flown in the same chain, on the same 3,010 rows. PRIMARY: intent accuracy (scenario_action exact), paired per recording with prompt-clustered bootstrap, 10,000 draws, seed 20260929. GUARD: official pooled SLU-F1 (slurp-slu-official-test) non-inferior at the FALLBACK null h_SLU 1.4492 (h_intent 1.3329; the DEV-2000-ADDED own null scaled by sqrt(913 / 682), flagged). HELD: the intent CI95 lower bound above zero AND the guard holds. NEUTRAL: both metrics non-inferior at the fallback null without a held gain. HARMFUL: a measured loss on either metric (decision 25). Every verdict carries intent and SLU separately, per-intent and per-scenario tables in both weightings (post-stratified natural mixture; equal stratum over 58 intents). The number is a MILESTONE read, development evidence under owner decision 28, never a test claim.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1": {
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "MILESTONE-00-PLAN is the INSTRUMENT, not a claim: the locked v2.0 plan exactly as flown on DEV-2000-ADDED, re-targeted to the sample, flown in the same chain before MILESTONE-01. The allowance makes it THE comparator of every milestone arm; its own number is the locked system's sample read.",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the guard",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-TEST-SAMPLE-3010-V1",
      "replicate_run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1",
      "rows": 3010,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1": {
      "claim": "nominated",
      "claims_benefit": true,
      "expected_effect_pp": 4.6,
      "expected_effect_status": "RE-DECLARED 2026-09-30 from the cell A2 read (owner decision 139: a measured number, not a prior): A2's intent point estimate +4.60 pp against its in-chain A/A on DEV-2000-ADDED; supersedes the provisional 3.8",
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "MILESTONE-01 = COMP-1b on the signed test sample (owner decisions 151 and 202). expected_effect_pp 3.8 is cell A2's own declared number (docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1/registered-facts-v1.json: the COMP-1b TRAIN Fold A intent point, docs/results/2026-09-29-slurp-comp1b-fold-a-read.md), carried PROVISIONALLY because the floor gate refuses a placeholder: root RE-DECLARES it from the A2 read (owner decision 139: a measured number, not a prior) before the flip, and the flip refuses while registered-facts' redeclared_from_a2_read is false. The contrast is against MILESTONE-00-PLAN, the LOCKED plan (recall k 8), not A2's in-chain A/A (k 60), so the milestone delta includes the k 8 -> 60 recall change the composed arm carries (the allowance prescribes the locked system as the comparator). The guard is a FALLBACK null (own_null.flag). tuning_roster / read_roster (item D3): the vote pool and centroid key are TRAIN construction artifacts; the arm was SELECTED on DEV-2000-ADDED by cell A2's read; both are disjoint from the sample by the sample's own disjointness proof (docs/checks/speech-aware-evidence-acquisition/2026-09-27-slurp-test-sample-roster/disjointness.json, CLEAN); nothing was chosen or tuned on the sample.",
      "own_null": {
        "flag": "NO OWN NULL EXISTS FOR SLURP-TEST-SAMPLE-3010-V1 (no A/A pair has flown on it, and the allowance names no second PLAN read id that could measure one). Declared guard = the DEV-2000-ADDED own null scaled by sqrt(913 / 682) at the PROMPT level (rho = 1, conservative: every recording of a prompt moves together; design note section 4 'Sample paired h 1.33'). The recording-level scaling sqrt(1000 / 3010) is given beside it and is the OPTIMISTIC bound; the read reports both.",
        "h_intent": 1.3329,
        "h_intent_recording_scaled": 0.664,
        "h_slu": 1.4492,
        "h_slu_recording_scaled": 0.7219,
        "kind": "FALLBACK-SCALED-NOT-MEASURED",
        "n": 3010,
        "n_prompts": 682,
        "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair); scaling: docs/readiness/2026-09-27-slurp-test-sample-design-v1.md section 4"
      },
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 (slurp-slu-official-test) the non-inferiority guard (owner decision 133)",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-TEST-SAMPLE-3010-V1",
      "replicate_run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1",
      "roster": "TEST-SAMPLE (SLURP-TEST-SAMPLE-3010-V1, split identity 0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9), 3,010 recordings / 682 prompts",
      "rows": 3010,
      "tuning_roster": [
        "slurp-train-construction-pool-agree-kprobe-r01-excluded",
        "SLURP-DEV-2000-ADDED-V1"
      ]
    }
  }
}
```

## Post-stratification: inside the official scorer, aggregates only (2026-09-30)

Coordinator ruling 2026-09-30. The roster receipt (`docs/receipts/rosters/slurp-test-sample-3010-v1.json`, decision
141 item 5) allows gold access as "per-intent aggregate counts only; no label beside a sample id", and the allowance
(`docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json`) lets gold be read "ONLY by the official scorer,
after delivery". A per-row gold bank is therefore not a legal stratum channel for this read; the DRAFT row
`SAEA-SLURP-TEST-SAMPLE-3010-GOLD-BANK-V1` (unmerged branch `fable/samplegoldbank`) is NOT PURSUED.

- **Where.** `scripts/flights/comp1/comp1b_testsample_read.sh` passes `--strata-source scorer --population-counts
  <package>/population-counts-v1.json --weighting post-stratified`. `scripts/analysis/stage3_paired_read.py` runs the
  official-scoring step's `--strata-inside-scorer` mode (`src/speech_aware_evidence_acquisition/core/scoring_strata.py`,
  exported by `core.scoring_batch`) in its own process. That process reads each row's gold intent through the
  `slurp-slu-official-test` binding (`reproduction.slurp_official_eval.official_gold_intents`), in memory, after both
  seals; the read process never holds a per-row stratum.
- **Strata.** Gold intent `scenario_action`: 59 strata in the population counts (full-test recording counts, total
  13,078, from the roster receipt's `per_intent` table), 58 carried by the sample; general_greet (closure-only) is
  reported as dropped and the weights are renormalised over the 58.
- **Formulas.** Post-stratified intent = sum_h w_h * mean_h(scenario_action_exact) per arm, then arm minus
  MILESTONE-00-PLAN, with w_h = N_h / sum over the 58 carried strata of N_h. Post-stratified SLU-F1 =
  F1(sum_h w_h*TP_h/n_h, sum_h w_h*FP_h/n_h, sum_h w_h*FN_h/n_h) per arm, then the difference (totals weighted before
  the F1 formula, never per-stratum F1 scores). Equal stratum = the unweighted mean of the 58 per-stratum deltas. Raw =
  the roster's own mixture, labelled "not a population estimate", never the natural-mixture slot; it must equal the
  read driver's own contrast bit for bit or the read refuses.
- **Resampling.** 10,000 draws, seed 20260929, prompt clusters resampled within gold-intent strata, both arms matched
  by `sample_id` inside the scorer process, through the same shared estimators (`analysis.stratified_paired`) the
  gold-bank path uses on TRAIN/DEV rosters -- identical bootstrap indices, identical numbers.
- **Emitted.** One file, `scorer-strata-aggregate.json` (schema `saea-scorer-strata-aggregate-v1`): per stratum n_h
  and, per arm, intent-correct, TP, FP, FN totals, the per-stratum deltas and CI95s; the three weighted deltas and
  CI95s; the population weights; the input hashes; a canonical `receipt_sha256`. The read driver verifies every hash
  and the seed, draw count and cluster key before reporting.
- **Never written.** A per-row stratum; any row-level output pairing a sample id or utterance id with a gold field; a
  gold label beside any id; utterance text, transcripts or model output. The scorer step refuses a roster receipt
  without a `stratification` block, any per-row output flag, and any receipt whose bytes would carry a roster sample id.

## Blockers before the flip

1. OWNER GATE (decisions 151 and 202): cell A2 must read NOMINATED or better and the coordinator must report the dev-admitted composed arm to the owner in conversation; the root countersignature of the first milestone row names that report (allowance first_contact_gate).
2. ALLOWANCE: CLEARED -- owner decision 207 signed the successor allowance docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json (sha256 be2bfa5a612d30cf46a2356efa5e8cf5a54707370b4f57378a278bb835fd0ed8), which names both FIT run ids as preparation-kind (non-read) run ids; both fragments pin its bytes (the v1 file is superseded, never edited).
3. PREPARATIONS: preparations 2 and 3 of the sample (SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1, SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1; label-free, owner decision 156) have run and their artifacts are pinned (sample_preparation_pins: 6 pins, verified against the data-root bytes by scripts/flights/comp1/derive_slurp_comp1b_testsample_cells.py --data-root). No sample-preparation pin remains pending (this roster's agreement table and its receipt are pinned from the builder's own receipt, ledger row SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1); the only zero pins are each cell's own first-phase supply, minted at the flip (item E16): ['prepared/SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1/phase-supply-v1.json', 'prepared/SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1/phase-supply-v1.json'].
4. EXPECTATION: CLEARED -- re-declared 3.8 -> 4.6 from the A2 read on 2026-09-30 (registered-facts redeclaration; redeclared_from_a2_read true).
5. READ DRIVER: scripts/analysis/stage3_paired_read.py reports the raw roster mean as 'natural_mixture'; on the floored sample that is NOT the natural-mixture number (design note section 5: post-stratify per-intent accuracy by full-test shares, the roster receipt's weightings block). The post-stratified weighting must land in the read path, with tests on fakes, before the READ row is countersigned.

## Prohibitions

- No contact before every blocker above is cleared, root countersigns the rows, mints the decision receipt and both cells are flipped in one converged cycle.
- ONE attempt per read run id, ever: no re-fly, no recovery, no resume, no re-score, no re-projection, no best-of, no tuning on the sample.
- No smoke on the sample; no direct-baseline read; no closure-roster or FULL-test contact.
- No k, tau, fuse_coverage, w_prior, store, release, snapshot, roster or geometry change. --allow-output-change is never passed.
- No utterance text, gold label, transcript or model output is printed or persisted by any read.
