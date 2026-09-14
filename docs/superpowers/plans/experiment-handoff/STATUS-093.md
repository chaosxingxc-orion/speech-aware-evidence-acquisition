# Status 093: live recovery and prepared fold-safe selective tools

Date: 2026-09-14. Keep the owner goal active. Continue OWNER-CANDIDATE-COVERAGE-026.

## Live experiment and service

At 2026-09-14T07:50:31Z, the same service PID 767 and campaign PID 2124 are
healthy. The sole TRAIN A recovery is OPENED with 3,232 charged model contacts,
not completed samples. Its frozen checkout remains clean 826a77c7bd9030ccbc25f2b74cd6fa4ed69db561.
No service restart, model reload, active-code update, geometry change or replay
occurred in this continuation. Four slots of 24,576, total 98,304, max512,
prepared original-speech packets and no mmproj remain in use.

The last 600-second window contains 52 monitor readings, mean GPU utilization
92.81%, range 57--99%, and four busy slots in 40 readings. Latest utilization
was 98%; GPU memory remains 22,976 MiB. No partial task quality was read.

Progress receipt: DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/
runtime-progress-and-admission-preparation-v4.json.
SHA256 b25bdf9c1921e5eb99c44e578e8722738736b732a90646772a95572a019066bb.

Driver telemetry also reports 180 MHz SM clock and an active software power
limit at 100 W. This condition predates the reboot: STATUS-064/076 report
100 W and 180--232 MHz, with earlier AC/high-performance checks. Do not
attribute it to this reboot or equate occupancy with unrestricted throughput.
Current root made no power/clock/driver changes. The owner has now confirmed
that the present power configuration is optimal and instructed root to stop
investigating it. Treat this question as closed; continue useful generation. A cumulative
thermal counter does not establish a flight-specific thermal history.

Fresh raw telemetry: the same DATA coordination directory,
gpu-power-clock-observation-v1.txt,
SHA256 bc4ddbcd6de6fd8102fdd89aec46622dc4c9b46b4c69e8dd56ad23f8cb38bae7.

## Shared behavior completed and verified

Root added optional reserve-final-report policy to the public OpenJiuwen role
rail and the common actual-request builder. With a three-contact Reviewer,
the last actual fitted request has no tool schemas and tool_choice=none.
The authority rail also blocks a noncompliant last-turn tool call before the
ability runs. Each role invocation resets this scope. Two visits allow at
most four analytical actions. Omitted policy preserves historical semantics.

A delegated loader/provider implementation excludes canonical TRAIN utterances
before collecting observations and fillers. Root reviewed it, integrated the
adapter cache and runtime source/exclusion pins, and tested real dispatcher
binding. Exclude all sibling recordings; preserve empty legal-label profiles,
reject missing current TRAIN exclusions, duplicate/tampered roster pins, wrong
carrier and wrong source identity. A legacy no-argument DEV provider retains
its exact identity. Legal-ID inventory use remains distinct from profile lookup.

Validation: 331 tests passed across the affected role, episode, actual-fit,
scheduler, speech tool, provider, dispatcher and diagnostic paths. The focused
construction set passed 106 tests; the reserved-role set passed 77 including the
added noncompliant final-turn case. These are overlapping suites, not additive.
Ruff and engineering-base checks passed without growing the exception baseline.

Logs in the same coordination directory:
- refresh-tools-admission-tests-v1.log
- refresh-tools-admission-engineering-v1.json
- contract-construction-binding-tests-v1.log

Code/held-protocol commit cba83794; construction support was integrated as
320e065a from reviewed agent commit 50ef801a. Registration commit 53a9f8c4
preceded real model-free catalog construction.

## Prepared next-version inputs

The new filler-free catalog excludes both pinned A/B rosters: 2,160 utterances
and all sibling recordings. It retains 9,354 TRAIN utterances and all 60 legal
intents. Shared-runtime validation verifies coverage of all 1,080 current A
identities and the exact provider hash. No A/B trajectory or score was read.

Canonical provider SHA256:
9b7489769e73cbba1543caa5a3b0ce2a5fcad79a4e1fd82ddcb101da5b433be0.
Catalog SHA256:
fd75c3b7605f827910908c79e122412c6c736c237d7faad7bf95ffd32640a6ca.
Receipt SHA256:
e6c9c538b2d6dd35673ecae5fe2f92596318dd1847248e74de22791c4d7dbc6f.
DATA prepared/SAEA-SLURP-TRAIN-EXCLUDED-CANDIDATE-CONTRACTS-PREPARE-V1/.

Prepared CPU Whisper protocol: audio workers 1, inference threads 4, interop 1,
local large-v3 fp32, beam5, temperature0, batch1, sample_len256. This leaves at
most two aggregate background preparation workers during a live tool campaign.
Protocol SHA256 abc76adebcf824085e4c383fc55b083e664c3a8b2b00cda809d72fc15bb058bd.
No Whisper model was loaded and no audio or ASR was run. Repeated selected
full-utterance requests cache independently of distinction/response hash, so
at most one new ASR decode per sample is needed.

The held experiment now composes all four fragments and binds the prepared
catalog. Its prospective protocol freezes full-task quality, C0/C1 and
common-covered diagnostics, graph/stops, contact bounds and training-free
feedback semantics. It remains check-only with no executable generation/fit/
ASR plan or phase-supply receipt.

Read docs/readiness/2026-09-14-slurp-native-candidate-refresh-tools-train-fold-a-v1/
README.md and prepared-tools-binding-v1.json. Catalog associations do not
replace rich semantic intent/slot values in the existing separate stores.

## Next boundary

Let the active campaign perform its first complete official TRAIN score and
finalize. Use postseal-handoff-recipe-v2.md in DATA coordination; never score
again. Verify full1080, manifest COMPLETED, attempt FINALIZED and queue scored.
Wrap the existing score, build actual native reward links, then diagnostics
using pinned checkout 8f35ae1f. Source checkout stays 826a77c7.

Root then makes the full-evidence mechanism decision and binds final generation,
fit, ASR, ledger, scoring and preparation artifacts. Reuse the healthy model
service only after full identity and sole-lease checks. Fit actual requests at
that boundary, never during current generation. No second automatic recovery
is authorized. Keep Fold B untouched for a frozen candidate's disjoint
evaluation; no training-free optimization cycle is yet completed.
