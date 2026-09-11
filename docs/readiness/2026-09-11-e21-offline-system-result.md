# E21 fresh offline direct to KC-E1f: final decision

**SYSTEM_NOT_ADMITTED_INSERTION_GUARD_FAILED.** PERSON error improves convincingly under the frozen discovery analysis, but inserted words increase from 10336 to 10341. The prospective natural-mixture insertion point guard requires no increase, so the system is not admitted. Five extra insertions are small in absolute terms; that does not authorize changing the rule after reading results. Preserve the useful component finding and the failed overall admission.

Both stages cover all 1593 fixed90second windows from 44 historically exposed discovery calls. Stage2 repairs these exact new first-stage drafts;1593 predecessor text/ordinal/geometry bindings were verified. Sources were frozen at b4d30c0fafd4e00856dd432d46ef7e51fe143098 for direct and64440737a401b80805cfdd4f09d5a04748a3aad7 for repair. Both used validated full-window feature packets, resident decoder-only c36864/np4,9216tokens per slot,max1024 and prefetch1. Official scores were computed once per full44call manifest after both stages sealed.

## Frozen whole-call results

Positive changes below mean improvement: error reduction, or numeric accuracy increase. All changes and confidence intervals are percentage points. Use10000 paired whole-call bootstrap replicates,seed20260903,CI90. Natural pooled PERSON error is primary; equal-call and equal-stratum estimates are secondary. The controls are the newly generated direct outputs, not historical KC-E1f outputs.

| Metric | Direct | Repair | Pooled gain | CI90 | Equal-call gain | CI90 |
|---|---|---|---|---|---|---|
| person_error_rate | 23.14021 | 19.74631 | +3.39390 | [+2.4461, +4.4005] | +3.94508 | [+2.8191, +5.1297] |
| overall_wer | 8.12086 | 8.07499 | +0.04586 | [+0.0334, +0.0592] | +0.04952 | [+0.0344, +0.0652] |
| nonentity_error_rate | 4.74681 | 4.74451 | +0.00230 | [-0.0013, +0.0060] | +0.00126 | [-0.0030, +0.0053] |
| insertion_rate | 2.87299 | 2.87438 | -0.00139 | [-0.0032, +0.0003] | -0.00184 | [-0.0037, -0.0000] |
| numeric_accuracy | 90.80542 | 90.83624 | +0.03082 | [-0.0215, +0.1124] | +0.02682 | [-0.0309, +0.1114] |

## Admission checks

| Requirement | Pass |
|---|---|
| person_primary_ci90_lower_gt_zero | True |
| equal_call_person_gain_gt_zero | True |
| overall_wer_point_gain_nonnegative | True |
| nonentity_error_rate_point_gain_nonnegative | True |
| insertion_rate_point_gain_nonnegative | False |
| numeric_accuracy_point_gain_nonnegative | True |

These nonnegative point guards are descriptive policy requirements, not independently calibrated non-inferiority/equivalence tests. The insertion CI crossing zero does not pass the predeclared point guard. No historical null margin is substituted.

## Exact counts and scorer interpretation

| Count | Direct | Repair | Repair minus direct |
|---|---|---|---|
| reference_words | 359765 | 359765 | 0 |
| substitutions | 13098 | 12933 | -165 |
| deletions | 5782 | 5777 | -5 |
| insertions | 10336 | 10341 | 5 |
| PERSON errors | 675 | 576 | -99 |
| Nonentity errors | 14446 | 14439 | -7 |
| expected_numeric_words | 9734 | 9734 | 0 |
| matched_numeric_words | 8839 | 8842 | 3 |
| spurious_numeric_words | 896 | 894 | -2 |

Total word errors fall 29216 to 29051. PERSON errors fall 675 to 576 out of 2917 reference words (99 fewer;14.67percent relative reduction).31calls improve,4worsen,9tie on PERSON. Insertion counts improve in4calls,worsen in8,tie in32. WER gains are statistically separated from zero here but small in absolute size.

Whisper-normalized whole-call WER is the standard ASR metric. ConEC uses the pinned fstalign definition mirror: official_tool_run=false, and insertions are not assigned to entity types. Numeric accuracy and semantic-impact diagnostics are repository auxiliaries. Preserve those labels instead of claiming the upstream binary was run.

## Equal-stratum estimates and every stratum
### Equal sector

| Metric | Gain | CI90 |
|---|---|---|
| person_error_rate | +3.58588 | [+2.7543, +4.6497] |
| overall_wer | +0.04676 | [+0.0358, +0.0585] |
| nonentity_error_rate | +0.00218 | [-0.0015, +0.0055] |
| insertion_rate | -0.00134 | [-0.0031, +0.0001] |
| numeric_accuracy | +0.03723 | [-0.0250, +0.1121] |


| Stratum | Calls | person_error_rate | overall_wer | nonentity_error_rate | insertion_rate | numeric_accuracy |
|---|---|---|---|---|---|---|
| Basic Materials | 5 | +3.66133 | +0.04485 | +0.00000 | +0.00000 | +0.00000 |
| Conglomerate | 4 | +3.14136 | +0.02203 | -0.00288 | -0.00245 | +0.00000 |
| Consumer Goods | 5 | +3.36134 | +0.05803 | +0.00472 | +0.00000 | +0.00000 |
| Financial | 5 | +1.77936 | +0.00471 | -0.00820 | +0.00000 | -0.09921 |
| Healthcare | 5 | +4.15335 | +0.09132 | +0.01617 | -0.00277 | +0.43431 |
| Industrial Goods | 5 | +2.55102 | +0.07067 | +0.00540 | +0.00228 | +0.00000 |
| Services | 5 | +6.93069 | +0.08228 | +0.01057 | -0.00294 | +0.00000 |
| Technology | 5 | +4.06977 | +0.02844 | -0.00853 | +0.00000 | +0.00000 |
| Utilities | 5 | +2.62467 | +0.01849 | +0.00241 | -0.00616 | +0.00000 |

### Equal sample_rate

| Metric | Gain | CI90 |
|---|---|---|
| person_error_rate | +3.19455 | [+2.2610, +4.3965] |
| overall_wer | +0.04211 | [+0.0303, +0.0552] |
| nonentity_error_rate | +0.00113 | [-0.0033, +0.0049] |
| insertion_rate | -0.00140 | [-0.0034, +0.0005] |
| numeric_accuracy | +0.00075 | [-0.0444, +0.0426] |


| Stratum | Calls | person_error_rate | overall_wer | nonentity_error_rate | insertion_rate | numeric_accuracy |
|---|---|---|---|---|---|---|
| 11025 | 5 | +0.88496 | +0.00625 | -0.00492 | +0.00208 | +0.00000 |
| 16000 | 6 | +6.00601 | +0.08436 | +0.00281 | -0.00234 | +0.00000 |
| 22050 | 5 | +3.00752 | +0.03177 | +0.00000 | -0.00578 | -0.09381 |
| 24000 | 21 | +4.30438 | +0.05603 | +0.00423 | -0.00241 | +0.09756 |
| 44100 | 7 | +1.76991 | +0.03213 | +0.00350 | +0.00146 | +0.00000 |

## Secondary attribution, costs and limits

The retained per-window statistics reconstruct each official whole-call aggregate exactly before window attribution is admitted. Call-cluster resampling of those windows reproduces the whole-call comparison, so this corroboration is not a second independent result. Available within-call speaker/window strata remain descriptive; no diarization accuracy, summary quality or meeting-minutes metric is claimed.

OBS consumes the same validated full-window speech packet geometry. ORG retains existing public ConEC context; no gold transcript or future generated turn enters runtime. SUPPLY combines that context with the exact fresh draft. USE is the same frozen Solver with the registered constrained delivery. Each stage recorded one saturated slice and zero skipped slices, with saturation on call4363614 in both. Full outputs remain in the official scoring population.

Generation costs: direct1593calls,1.0769731465823122 utilization GPU hours,0.18356200261799813kWh; repair1593calls,1.2582756753040685GPUhours,0.1986948864272039kWh. Total3186calls,2.335248821886381GPUhours,0.382256889045202kWh,5477221prompt and878686completion tokens. Both stages process141345.8526875speechseconds each; this is repeated model input, not unique corpus duration. The two fit receipts account9560 separate endpoints. The quoted generation integrals exclude fit, model load and historical feature preparation; do not call them total lifetime system cost. No new encoding occurred for these warm packets. Generation contact windows were7245.155177116394 and7953.895875692368seconds; whole-score times1929.26 and1912.13seconds. The scorer performed three sequential whole-call alignments, an observed CPU tail. Native bundle GPU fields are NOT_AVAILABLE; the external10second monitor receipts supply the generation integrals with complete sampled coverage.

This fixed two-stage offline execution does not prove live Reviewer-to-Planner selection, dynamic observation cuts, or the quality/cost of a live bounded loop. Retain that open acceptance item. Do not promote either the narrower component effect or generic model-free controller tests into complete live agentic performance.

## Reproduction and source bindings

Use experiment fragments e21-offline-direct-kc-e1f-packets-np4-v1 and e21-offline-kc-e1f-repair-packets-np4-v1 at their frozen source commits with the shared flight worker and fresh predecessor builder. Score once through core.scoring_batch; bind complete saved receipts to the unchanged analysis templates under docs/readiness/2026-09-10-e21-offline-system-v1. Existing attempts are never relaunched or rescored. The raw parents declare no derivatives; close them with shared settle_scored_attempt, never finalize_bundle.

Machine-readable [decision](2026-09-11-e21-offline-system-decision.json). DATA denotes SPEECHRL_DATA_DIR.

| Root | Artifact | SHA-256 |
|---|---|---|
| repo | docs/readiness/2026-09-10-e21-offline-system-v1/analysis-plan.json | 8b92393cb37632b7fc53fbb35686d0aef63f845b199bd5de39127e5702ccd5f5 |
| DATA | analysis/e21-offline-direct-repair-postseal-v1/call-error-contrast.json | 715ba8448990598b14882040022ab9f0334f8ac3ad702714a992d067671042f1 |
| DATA | analysis/e21-offline-direct-repair-postseal-v1/call-numeric-contrast.json | c3284582b81f46fe079da035cbb72027536588527d6fbbf88dca190d2a8e09f2 |
| DATA | analysis/SAEA-E21-OFFLINE-DIRECT-GENERATION-NP4-V1/official-scoring-v1/e21-offline-direct-generation-np4-v1.score.json | 68d2792a22f0901aa7fd8261210d6dbfee5971aae6e5678aa85ded3a93e53682 |
| DATA | analysis/SAEA-E21-OFFLINE-DIRECT-GENERATION-NP4-V1/official-scoring-v1/e21-offline-direct-generation-np4-v1.complete-score-receipt.json | 2a8aa24693d3fdfcf7c0aec31a2b7a8d93fa55e5905d9e336e0da8937f337d1d |
| DATA | analysis/SAEA-E21-OFFLINE-KC-E1F-REPAIR-GENERATION-NP4-V1/official-scoring-v1/e21-offline-kc-e1f-repair-generation-np4-v1.score.json | ae4ddb5a0a0877b290c2642b992e24dd7c7e310ecdac028b58eb4c196284f58a |
| DATA | analysis/SAEA-E21-OFFLINE-KC-E1F-REPAIR-GENERATION-NP4-V1/official-scoring-v1/e21-offline-kc-e1f-repair-generation-np4-v1.complete-score-receipt.json | 1acba8ac3247e02d2ec14daf8df54ac2c1c8175b0363dd800a66c46fe8429198 |


## Completed custody and operational audit

Both generation attempts are FINALIZED through shared saved-score settlement. Saved receipts were independently reverified and raw manifest hashes are unchanged. No new score or model contact occurred. DATA coordination/e21-slurp-root-settlement-closure-v1.json, SHA-256 9e6fa8582c794e599707217c5055e6bab499790ec0dd460ead9991b4d90e9db9, binds all four settlements and root decisions. FINALIZED is operational completion, not scientific admission.

DATA coordination/e21-slurp-operational-timing-audit-v1.json, SHA-256 fdc8372ae28ea89b3995528a5de58e730da511586e49856be61f386f3d276b16, binds25 source records and separates timing limitations. E21 generation-contact-window device averages are53.5130%/56.9506%; SLURP fit-inclusive attached-operation averages67.8145%/70.6379%. These are not sustained full GPU utilization or exact kernel time. The419.538second SLURP handoff and119.558second speech-worker precontact period are separate. Neither pair integral includes initial model loading or between-stage idle. E21 fits and historical encoding are outside its quoted generation total.

Saved attribution: net+5 insertions comes from13 changed windows across12 calls (+10 offset by-5). All have changed delivered-response hashes, none is saturated;1is a first window and12are interior. This does not establish a causal boundary failure or prove new lexical additions. DATA coordination/e21-offline-direct-repair-insertion-attribution-v1.json, SHA-256 b7d96a7e9cf3c0eb140851510e133436beda133b29e140eeec8d8340817bc7ac. No new alignment or scoring ran.
