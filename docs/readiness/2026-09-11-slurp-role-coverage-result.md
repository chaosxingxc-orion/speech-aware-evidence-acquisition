# SLURP intent-role coverage: closed matched comparison

Date: September 11, 2026 local time. Both generation attempts are FINALIZED.
Root decision: **Do not adopt this knowledge package. Primary intent is negative;
primary entity improvement is unresolved.** No replication or recovery follows
this registration. Preserve the previously replicated compact-frame working
baseline; its original serving geometry remains part of its evidence identity.

## Native task results

Both arms independently generated their own plan and complete SLU answer on the
same 1,000 previously exposed DEV samples. NEW500 is primary; OLD500 and DEV1000
are secondary. Values are percentages; changes are percentage points.
The original 10,000-replicate paired speaker-cluster CI90 and seed 20260903 with
fixed metric offsets were used. Intervals are exploratory and unadjusted.

| Population | Outcome | Control | Treatment | Change, pp | Speaker CI90, pp | Equal-scenario change, pp | Verdict |
|---|---|---:|---:|---:|---|---:|---|
| NEW500 | Intent accuracy | 76.0000 | 73.8000 | -2.2000 | [-3.9497, -0.4228] | -2.7697 | negative |
| NEW500 | Official micro SLU F1 | 39.3674 | 38.8261 | -0.5413 | [-2.5457, +1.3348] | -0.2711 | unresolved |
| OLD500 | Intent accuracy | 74.0000 | 72.6000 | -1.4000 | [-2.7451, -0.1811] | -1.3962 | negative |
| OLD500 | Official micro SLU F1 | 36.5307 | 34.5714 | -1.9593 | [-3.8020, -0.2093] | -1.8377 | negative |
| DEV1000 | Intent accuracy | 75.0000 | 73.2000 | -1.8000 | [-2.9098, -0.7224] | -1.9771 | negative |
| DEV1000 | Official micro SLU F1 | 37.9749 | 36.7316 | -1.2433 | [-2.5565, +0.0408] | -1.0147 | unresolved |

The main intent comparison has 9 saves and 20 harms on NEW500. Entity micro F1
pools the six official TP/FP/FN ingredients; it is not mean per-row F1. The frozen
analysis also reports row means and scenario-stratified bootstrap sensitivity.
All 270 population/scenario/metric rows are retained in
[the complete stratum table](2026-09-11-slurp-role-coverage-strata.csv).
Root independently verified 915 arithmetic points and equal-scenario differences.

## Error attribution and interpretation

| Population | Diagnostic | Control | Treatment |
|---|---|---:|---:|
| NEW500 | missing | 302 | 309 |
| NEW500 | spurious | 104 | 69 |
| NEW500 | type swaps | 16 | 19 |
| NEW500 | predicted entities | 291 | 249 |
| OLD500 | missing | 294 | 309 |
| OLD500 | spurious | 95 | 81 |
| OLD500 | type swaps | 14 | 13 |
| OLD500 | predicted entities | 262 | 233 |
| DEV1000 | missing | 596 | 618 |
| DEV1000 | spurious | 199 | 150 |
| DEV1000 | type swaps | 30 | 32 |
| DEV1000 | predicted entities | 553 | 482 |

The role-coverage package reduced spurious entities but increased omissions.
This does not support the intended omission-reduction mechanism. Type/surface
attribution reconciles all six saved official count ingredients for all 2,000
scored outputs. Type-swap classification is a descriptive equal-normalized-filler
heuristic, not a causal explanation.

More role coverage, frequency statistics, caveats and input text were changed
together. This result does not prove that every coverage representation is harmful
or that discriminative knowledge cannot help. It rejects this particular package
as an improvement over the matched compact frame. Applicability, semantic role
relations and evidence for choosing among alternatives remain future hypotheses;
do not turn these evaluation cases into runtime rules or validated memory.

## Primary scenario table

| Scenario | NEW500 n | Intent change, pp | Micro SLU F1 change, pp |
|---|---:|---:|---:|
| alarm | 30 | +3.3333 | +1.2842 |
| audio | 2 | +0.0000 | +0.0000 |
| calendar | 33 | -3.0303 | +6.8483 |
| cooking | 9 | -22.2222 | +18.1549 |
| datetime | 33 | +6.0606 | +3.4454 |
| email | 33 | +0.0000 | +3.7681 |
| general | 33 | -9.0909 | -7.3630 |
| iot | 33 | +0.0000 | +4.2719 |
| lists | 32 | -3.1250 | +2.3568 |
| music | 23 | +0.0000 | +3.4442 |
| news | 32 | -3.1250 | -4.4285 |
| play | 32 | -12.5000 | +2.8505 |
| qa | 32 | +6.2500 | -1.2325 |
| recommendation | 32 | -9.3750 | -7.4708 |
| social | 33 | +0.0000 | -7.2190 |
| takeaway | 12 | +0.0000 | -7.7516 |
| transport | 33 | -3.0303 | -1.8125 |
| weather | 33 | +0.0000 | -14.0267 |

Small strata are descriptive. Do not select a favorable stratum or a same-plan
subset to override the registered primary decision.

## Execution and comparability

Both runs used source commit 1aa6cb5d and the same resident no-mmproj decoder process,
serving-slurp-role-coverage-np8-v1/PID114585, c65536/np8, 8192 tokens per slot,
max256. All query features and prepared retrieval were reused. Each arm completed
2,000 generations and 6,002 real-request fit endpoint contacts, plus 1,000 knowledge
tool returns. No generation retry, empty response or saturation occurred. Maximum
observed completion lengths were 121 (control) and 77 (treatment). Every final output
matches its own raw response and every tool result follows its own plan response.

All 1,000 actual first-phase fit request-body hashes match between arms. Retrieval
selection and order match on all 1,000 rows. First-phase text matches on 830
rows and final text on 792. This live comparison includes generation variability.
The five prospectively named model-visible audit fingerprints also differ with
the new value package. Do not call it a pure semantic-only HTTP ablation.

The control minimum fit margins are 5,526(plan) and 4,626(solve); treatment margins
are 5,526 and 3,895, all after reserving the full 256-token completion allowance.
The fit roster covers all 1,000 requests in each phase; no guessed capacity,
shortened completion budget or mid-pair geometry change was used.

## Resource and timing receipt

Control and treatment used 5,456,222 and 5,991,277 prompt tokens, and 52,066 and 50,821
completion tokens. The added 535,055 prompt tokens are part of this package's input
difference. Speech-contact totals are 5,769.587375 seconds per arm.

Dispatch-to-seal took 1,120.07 and 1,329.31 seconds. First observed occupied slots
occurred 173.46 and 191.14 seconds after dispatch, including identity/preparation/fit
work. Observed slot-busy time was 862.35 and 1,053.50 seconds; it is not a precise
GPU-kernel duration. Peak sampled utilization was 98%; dispatch-window means were
61.80% and 65.73%, so the service was not continuously fully utilized. The observed
utilization integrals were 0.1910 and 0.2425 GPU hours, below the registered 2.0-hour
family ceiling. Monitor integration uses observed endpoints only. Model-loading
telemetry is incomplete because monitoring started after service launch.

Manifest-to-next-dispatch handoff was 65.49 seconds, exceeding the 60-second target
by 5.49 seconds while root confirmed completion, released/acquired custody and
launched the worker. Keep that deviation; do not round it into a pass. Complete
official scoring ran once per manifest, serially, in 58.10 seconds total. Scorer
aliases reuse the same callable result. Both attempts were finalized from those
saved complete-score receipts without rescoring. Scientific analysis/decision
waiting after the second seal is tracked separately in the closeout timing receipt.
The server remains resident; neither generation lease remains held.

## Provenance and next work

Root decision: DATA coordination/slurp-role-coverage-root-decision-v1.json,
SHA256 d4ca0342448b0784c127426e52b4a5b7a86f762ad7a3df2b1dbc22acdc53cb1e.

Analysis, first score/manifest pins, entity attribution, all strata, operational
lineage and both saved-score settlements are hash-bound by that decision. The
analysis artifact is 879411d328ac488f554f6f831694ab801dc2cf6150fa1fe70258643478e908f3.
The entity attribution is 3c69ed9458a15a352006ab8cce516747c4200c392789f70f513dd35e17e94e13.
The root arithmetic verification is 02a204a758a7572f51314941657fb87429556a2fe7628f046e0381e8de8a809f.
Operational lineage is 4a6e604cdd8c5f535e249231f86514802a407e3511caafd63858bb57711afd9c.

Keep the compact-frame complete-system baseline as the qualified exploratory
starting point. Define grounded task distinctions and validated experience on
declared construction/validation roles. For Audio2Tool, the shared source-bound
construction API and exact all-tier exclusions are now implemented; compilation
and live OBS-to-card routing remain pending. Preserve native E21/E22 metrics and
the planned external system-level optimization surface. No closed historical
flight is reopened, and the broad research goal remains active.
