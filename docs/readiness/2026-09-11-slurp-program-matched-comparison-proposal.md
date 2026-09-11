# Proposed single SLURP comparison with matched program identity

Status: OWNER DECISION PENDING. This document proposes one additional bounded comparison. It is not an ExecutionPlan, exposure registration, readiness receipt or launch authorization. Keep the active E21 repair unchanged.

## Decision purpose and existing evidence

Determine whether the live speech-retrieval system retains its slot benefit and passes the inherited protection guards when the null and treatment use the same model-visible program identity. The previous pair has positive slot evidence but a failed NEW500 scenario point guard: nine saves, ten harms, net minus 0.2 percentage points. Its first-stage prompts differed by the rendered control identifier, adding two tokens in the treatment. The failed historical decision remains in force.

Root verified that the existing common program and an empty null supply can express the proposed match without changing the renderer or controller. Eight model-free tests passed. This removes a named request mismatch; it does not establish that the mismatch caused the historical failure, guarantee response equality or promise a passing new outcome.

## Exact proposed configuration

| Field | Null arm | Treatment arm |
|---|---|---|
| Source baseline | slurp-live-intent-slots-control-recovery-v1 | slurp-live-intent-slots-speech-v1 |
| Phase program | phase-direct-then-slots-supplied-v1 | phase-direct-then-slots-supplied-v1 |
| phase_supply | Empty object | Existing frozen slots-only speech retrieval configuration |
| First stage | Existing complete closed-list SLU prompt and its own new response | Same prompt and its own new response |
| Second stage | Existing intent-conditioned slot schema, with original examples retained | Same schema plus existing five retrieved TRAIN slot facts |
| Delivery | Existing slurp-intent-slots-delivery-v1 phase-pair join | Same rule |
| Roster | Same historically exposed DEV1000; NEW500 primary | Same roster and order |
| Service | One new shared decoder-only process, total context 65,536, four slots, 16,384 per slot, max output 256, inherited greedy parameters | Same process and settings |

Use the existing model fragment q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64 with the inherited request-level max256 override, and dataset slurp-speech-native-dev1000. The historical fragment name does not determine the final output ceiling; verify the composed request parameters.

Only the null program identity changes the mechanism relative to its source; empty supply makes the intended null explicit. Fresh run/attempt/fit identities and lineage receipts must be registered. Reuse verified speech features and the existing recall inputs; bind any successor preparation through the common preparation API. Preserve independent current-run first stages. Do not substitute an old manifest or a common saved answer for either full system.

Before generation, compare all actual model-visible first-stage requests for equality. Also compare second-stage request construction with the same synthetic predecessor, allowing only the declared supply difference; independently generated predecessor differences remain observed system behavior. Capacity checks and generation must use the common request builder. Do not alter the output limit, roster, prompt text, delivery rule or guard to obtain a fit or passing result.

## Incremental budget and schedule

- Exactly one pair: 1,000 samples times two stages times two arms, or 4,000 planned generation contacts.
- Retain bounded retry headroom: 2,100 contacts per arm, 4,200 total ceiling.
- Register two actual phase fits per arm: 6,002 endpoint contacts per arm, 12,004 total, with no extra generation.
- Propose a family cap of 1.0 utilization-integrated GPU hour, at most 0.5 per arm; retain 6,000 speech seconds per arm. These are this proposed comparison's caps, not reinstated global limits.
- The previous successful pair used 0.4285784232 utilization-integrated GPU hours over intervals including fits and preparation. This is a planning reference, not a guaranteed duration. Report elapsed wall time separately.
- Run only after E21 repair seals and its source is frozen. Its complete CPU scoring may overlap this new GPU pair under the existing shared resource limits.
- Root starts one matching SLURP service and retains it across null then treatment. No new speech encoding, projector residency or private experiment runner is introduced.

## Frozen analysis and stopping rule

Reuse the original G6 analysis definitions on the same exposed population: NEW500 mean row SLU-F1 with paired speaker-cluster bootstrap, 10,000 resamples and the established seed ordering; pooled micro SLU-F1 remains a distinct estimand. Require the inherited positive slot interval, positive pooled micro and equal-scenario point gains, nonnegative intent/scenario/action point differences, and nonworsening malformed/saturated delivery counts. Report OLD500, DEV1000, per-scenario strata, all costs and failures.

This is a newly registered comparison correcting a named nuisance, not a retrospective replacement for the historical result. Do not choose an arm or analysis after outcome reading. If the guards fail again, retain that result and stop this comparison; no further repeat is authorized to search for a passing outcome.

Owner approval is requested because the previously closed G6 decision explicitly admits no further SLURP model contact. The additional 4,000 planned generations and associated fits exceed that completed pair's execution budget. If the owner declines, keep the existing SLURP component-positive/system-not-admitted conclusion and continue the E21 closure.
