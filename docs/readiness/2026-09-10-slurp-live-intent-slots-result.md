# G6 live intent-to-slots paired result

**Status: root decided; both attempts finalized against verified derived scores and costs.** This report renders completed sealed score and paired-analysis artifacts. It does not recompute scoring or bootstrap draws, and it does not change the frozen threshold.

## Root finding

The NEW500 paired row SLU-F1 result is positive: speech minus matched control is +3.259058 percentage points with speaker-cluster CI90 [+1.089283, +5.504729]. The separate pooled-count micro SLU-F1 gain is +3.206961 points. Joint scenario-action and action each increase by +0.8 points, while scenario changes by -0.2 points.

The frozen prospective guard requires nonnegative point changes for intent, scenario, and action. The -0.2-point scenario change fails that guard. The result therefore supplies positive slot evidence but does **not** fully admit the live system. No rerun, adaptive redraw, or threshold change follows from this result.

## Analysis identity

- Paired analysis: DATA/analysis/SAEA-SLURP-LIVE-INTENT-SLOTS-PAIRED-ANALYSIS-V1/paired-contrasts.json; SHA-256 cbf7f3a21501cca9b19327a74af6c95d8aceae414bb00c068d8bc13a90d88cd5.
- Serving identity match, root-verified v3: DATA/coordination/g6-live-pair-root-serving-match-v3.json; SHA-256 d9297dffe8ae753f47e18dfd315194b8e9683e717a77f97358353a615d712ce1.
- Control integrated cost: DATA/coordination/g6-live-control-recovery-integrated-cost-v1.json; SHA-256 371e5c71185f47251aa1ad01249ca45f4ce11f575b96e8672fbe1a70aa47640d.
- Speech integrated cost, root-verified v3: DATA/coordination/g6-live-speech-root-verified-cost-v3.json; SHA-256 491dbe82fa0b939ce43e9c50fc740b05eb8a4f27e439d42e9daa16f5a60aab3e.
- Root configured-system attribution: DATA/coordination/g6-live-system-root-attribution-v1.json; SHA-256 966f02774fb56300e4d1d9cea3ce5ec774b7401f49c01e04ca47de71a402d41d.

The score analysis is the registered comparison speech minus live matched control. NEW500 is the historically exposed primary population; OLD500 and DEV1000 remain reporting populations. Speaker-cluster CI90 uses 10,000 resamples and base seed 20260903. Scenario-stratified row results are an inherited sensitivity. Equal-scenario is the unweighted mean of the observed per-scenario changes. Mean row SLU-F1 and pooled-count micro SLU-F1 are distinct estimands.

## Population summaries

Control and speech means are percentages; deltas and interval bounds are percentage points. The first interval is the primary speaker-cluster CI90; the second is the scenario-stratified row sensitivity CI90.

| Population | Metric | Control mean | Speech mean | Delta | Speaker CI90 | Scenario-row CI90 | Equal-scenario delta |
|---|---|---:|---:|---:|---|---|---:|
| NEW500 | Mean row SLU-F1 | 28.848720 | 32.107778 | +3.259058 | [+1.089283, +5.504729] | [+1.203155, +5.287494] | +2.941441 |
| NEW500 | Pooled micro SLU-F1 | 46.395113 | 49.602074 | +3.206961 | [+0.288475, +6.088766] | [+0.736409, +5.579771] | +3.175656 |
| NEW500 | Joint scenario-action accuracy | 69.800000 | 70.600000 | +0.800000 | [-0.735362, +2.362276] | [-0.600000, +2.400000] | +1.059661 |
| NEW500 | Scenario accuracy | 78.000000 | 77.800000 | -0.200000 | [-1.927326, +1.391650] | [-1.600000, +1.200000] | +0.195814 |
| NEW500 | Action accuracy | 72.600000 | 73.400000 | +0.800000 | [-0.397614, +2.083333] | [-0.600000, +2.200000] | +1.195530 |
| OLD500 | Mean row SLU-F1 | 24.719047 | 27.236988 | +2.517941 | [+0.583900, +4.525138] | [+0.707674, +4.342274] | +2.539836 |
| OLD500 | Pooled micro SLU-F1 | 43.041560 | 45.279111 | +2.237552 | [-0.377503, +4.851305] | [-0.052317, +4.550659] | +2.419865 |
| OLD500 | Joint scenario-action accuracy | 67.800000 | 67.400000 | -0.400000 | [-1.731602, +0.877193] | [-1.600000, +0.800000] | -0.404174 |
| OLD500 | Scenario accuracy | 76.600000 | 76.800000 | +0.200000 | [-0.959233, +1.413463] | [-0.800000, +1.200000] | +0.205761 |
| OLD500 | Action accuracy | 70.600000 | 70.600000 | +0.000000 | [-1.270456, +1.176471] | [-1.200000, +1.200000] | -0.007349 |
| DEV1000 | Mean row SLU-F1 | 26.783883 | 29.672383 | +2.888500 | [+1.354505, +4.523536] | [+1.534803, +4.284365] | +2.783998 |
| DEV1000 | Pooled micro SLU-F1 | 44.772395 | 47.478896 | +2.706501 | [+0.602412, +4.877781] | [+1.015023, +4.402941] | +3.472210 |
| DEV1000 | Joint scenario-action accuracy | 68.800000 | 69.000000 | +0.200000 | [-0.758397, +1.214241] | [-0.800000, +1.200000] | +0.303336 |
| DEV1000 | Scenario accuracy | 77.300000 | 77.300000 | +0.000000 | [-1.000000, +0.964336] | [-0.900000, +0.900000] | +0.058918 |
| DEV1000 | Action accuracy | 71.600000 | 72.000000 | +0.400000 | [-0.506073, +1.302340] | [-0.500000, +1.400000] | +0.536023 |

## Per-scenario sensitivity: NEW500

Each entry is speech minus matched control in percentage points from the saved scenario-stratified table. These rows are descriptive; none supplies an extra gate.

| Scenario | n | Mean row SLU-F1 | Joint scenario-action | Scenario | Action | Pooled micro SLU-F1 |
|---|---:|---:|---:|---:|---:|---:|
| alarm | 30 | +2.842778 | +0.000000 | -3.333333 | +0.000000 | +4.704251 |
| audio | 2 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| calendar | 33 | -6.379253 | +0.000000 | +0.000000 | +0.000000 | -4.192843 |
| cooking | 9 | +14.718615 | +11.111111 | +11.111111 | +11.111111 | +15.247660 |
| datetime | 33 | +2.293294 | +0.000000 | -3.030303 | +0.000000 | +3.592779 |
| email | 33 | +11.045943 | +0.000000 | +0.000000 | +0.000000 | +11.936168 |
| general | 33 | +3.030303 | +3.030303 | +0.000000 | +3.030303 | +2.463777 |
| iot | 33 | -3.030303 | +3.030303 | +0.000000 | +3.030303 | -5.361290 |
| lists | 32 | -0.601066 | +6.250000 | +6.250000 | +6.250000 | -3.516230 |
| music | 23 | +4.347826 | -4.347826 | -4.347826 | +4.347826 | +15.154692 |
| news | 32 | +6.784759 | +6.250000 | +6.250000 | +0.000000 | +5.312423 |
| play | 32 | -8.333333 | -3.125000 | -6.250000 | -3.125000 | -9.627295 |
| qa | 32 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +1.144631 |
| recommendation | 32 | +6.250000 | -3.125000 | -3.125000 | -3.125000 | +4.431491 |
| social | 33 | +25.809233 | +0.000000 | +0.000000 | -3.030303 | +21.801990 |
| takeaway | 12 | -13.888889 | +0.000000 | +0.000000 | +0.000000 | -15.597265 |
| transport | 33 | +0.078582 | +0.000000 | +0.000000 | +3.030303 | -2.110673 |
| weather | 33 | +7.977451 | +0.000000 | +0.000000 | +0.000000 | +11.777547 |

## Per-scenario sensitivity: OLD500

Each entry is speech minus matched control in percentage points from the saved scenario-stratified table. These rows are descriptive; none supplies an extra gate.

| Scenario | n | Mean row SLU-F1 | Joint scenario-action | Scenario | Action | Pooled micro SLU-F1 |
|---|---:|---:|---:|---:|---:|---:|
| alarm | 28 | +1.915646 | +0.000000 | +0.000000 | +0.000000 | +7.472909 |
| audio | 28 | +1.734694 | +0.000000 | +0.000000 | +0.000000 | +20.408163 |
| calendar | 28 | +3.425507 | -3.571429 | -3.571429 | +0.000000 | +4.119181 |
| cooking | 28 | +2.142857 | +3.571429 | +0.000000 | +3.571429 | +5.959408 |
| datetime | 28 | -2.275237 | +0.000000 | -3.571429 | +0.000000 | -4.868451 |
| email | 28 | +6.046423 | +0.000000 | +3.571429 | +0.000000 | +7.474382 |
| general | 28 | +1.190476 | -3.571429 | +0.000000 | -3.571429 | -4.013378 |
| iot | 28 | -2.952822 | -7.142857 | -3.571429 | -7.142857 | -11.599752 |
| lists | 28 | +3.571429 | +0.000000 | +0.000000 | +3.571429 | +5.826167 |
| music | 28 | +1.226597 | +3.571429 | +3.571429 | +7.142857 | -5.881439 |
| news | 28 | +3.272386 | +0.000000 | +0.000000 | +0.000000 | -2.044442 |
| play | 28 | -4.429412 | +0.000000 | +0.000000 | -3.571429 | -6.133925 |
| qa | 28 | +3.535337 | -3.571429 | -3.571429 | -3.571429 | +0.054201 |
| recommendation | 28 | +6.206334 | +7.142857 | +7.142857 | +7.142857 | +7.036323 |
| social | 27 | +18.594033 | +0.000000 | +3.703704 | +0.000000 | +17.753592 |
| takeaway | 27 | +1.204422 | +0.000000 | +0.000000 | +0.000000 | +1.068595 |
| transport | 27 | +1.308377 | -3.703704 | +0.000000 | -3.703704 | +3.852613 |
| weather | 27 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | -2.926570 |

## Per-scenario sensitivity: DEV1000

Each entry is speech minus matched control in percentage points from the saved scenario-stratified table. These rows are descriptive; none supplies an extra gate.

| Scenario | n | Mean row SLU-F1 | Joint scenario-action | Scenario | Action | Pooled micro SLU-F1 |
|---|---:|---:|---:|---:|---:|---:|
| alarm | 58 | +2.395197 | +0.000000 | -1.724138 | +0.000000 | +6.038526 |
| audio | 30 | +1.619048 | +0.000000 | +0.000000 | +0.000000 | +20.408163 |
| calendar | 61 | -1.878707 | -1.639344 | -1.639344 | +0.000000 | -1.347985 |
| cooking | 37 | +5.201825 | +5.405405 | +2.702703 | +5.405405 | +8.125570 |
| datetime | 61 | +0.196264 | +0.000000 | -3.278689 | +0.000000 | -0.731072 |
| email | 61 | +8.751082 | +0.000000 | +1.639344 | +0.000000 | +9.715249 |
| general | 61 | +2.185792 | +0.000000 | +0.000000 | +0.000000 | -0.376320 |
| iot | 61 | -2.994738 | -1.639344 | -1.639344 | -1.639344 | -7.863151 |
| lists | 60 | +1.346098 | +3.333333 | +3.333333 | +5.000000 | +1.494469 |
| music | 51 | +2.634210 | +0.000000 | +0.000000 | +5.882353 | +3.916015 |
| news | 60 | +5.145652 | +3.333333 | +3.333333 | +0.000000 | +1.669171 |
| play | 60 | -6.511503 | -1.666667 | -3.333333 | -3.333333 | -8.045247 |
| qa | 60 | +1.649824 | -1.666667 | -1.666667 | -1.666667 | +0.634254 |
| recommendation | 60 | +6.229623 | +1.666667 | +1.666667 | +1.666667 | +5.354955 |
| social | 60 | +22.562393 | +0.000000 | +1.666667 | -1.666667 | +20.767371 |
| takeaway | 39 | -3.439674 | +0.000000 | +0.000000 | +0.000000 | -2.483509 |
| transport | 60 | +0.631990 | -1.666667 | +0.000000 | +0.000000 | +0.754336 |
| weather | 60 | +4.387598 | +0.000000 | +0.000000 | +0.000000 | +4.468982 |

## Cost and custody

The pair completed 4,000 registered generation contacts. The retained failed original control contributes 1,000 direct contacts and zero slots contacts. The two live fits used 15,006 endpoint contacts. The control integrated utilization is 0.1957336275 GPU-hours and speech integrated utilization is 0.2328447957 GPU-hours.

Those utilization intervals include fit, preparation, and generation; they are not pure generation-kernel estimates. Preserve the per-receipt interval, coverage, and method fields rather than treating the two values as an alternative generation-only measure. The final serving-match v2 receipt is the identity authority for the paired service.

## Interpretation boundary

The saved analysis establishes a positive paired configured-system result under the stated estimator. The nonnegative scenario point guard nevertheless fails, so the system is not fully admitted.

The final attribution receipt records 2,000 generation contacts per arm, zero saturation and non-JSON closures, and 1,000 well-formed joined deliveries per arm. All 1,000 task instructions, query packets, and empty direct-phase supply inputs match. The comparison is nevertheless not a retrieval-only causal isolation: the control uses phase-direct-then-slots-v1 while speech uses phase-direct-then-slots-supplied-v1, and the shared speech history renderer exposes that phase identifier through contact_id. The treatment phase therefore carries two additional model-visible input tokens per row. Raw direct-phase responses agree on 834 of 1,000 rows. Do not normalize scores, correct outcomes, or attribute the -0.2-point scenario change to retrieval.

This report makes no rerun, new-control, threshold, confirmatory, generalization, or meeting-minutes-quality claim.

## Final root custody

- DATA/coordination/g6-live-system-root-decision-v1.json; SHA-256 a724ffc0c86a4ed32537d8e4b4ef7d23decb3ed363727c92e1dd05f5a29438b5.
- DATA/coordination/g6-live-control-attempt-settlement-v1.json; SHA-256 86c9d28e05f991549c365f263ed26f8fec726b6645d5fe0176656d05208e39fa.
- DATA/coordination/g6-live-speech-attempt-settlement-v1.json; SHA-256 85f944dfadbdc8fa92655c202b0a4dd26e76914119d039bd89ad21ee30614025.

The helper cost v2 omitted one final hex character in its embedded monitor binding and carried a copied creation time. Root v3 preserves v2, computes the full hash from the unchanged snapshot, and independently reproduces the integral. The final service-match v3 similarly corrects receipt-time metadata; the earlier v1 already bound the final speech attach bytes. Both model-free saved-score jobs succeeded, and no raw parent manifest or output was rewritten.

The successful pair used 0.4285784232 utilization-integrated GPU hours over contact windows that include fits, preparation and generation. The failed first control service adds 0.0583467484 observed utilization-integrated GPU hours; its precise generation interval is unavailable. These are utilization integrals, not reserved-device wall time. A delayed control-to-speech handoff is explicitly retained in the control handoff receipt; no throughput superiority claim follows.
