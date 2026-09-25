# Evidence-path complete-system result: NOT QUALIFIED

Both full 625-input R01C arms completed, sealed, and received exactly one
complete official score. The registered read completed at 2026-09-25T17:44:44Z.
The tools policy does not pass either the terminal SLU improvement rule or
the intent protection rule. Close this comparison without default adoption,
subgroup rescue, forced-tool recovery, or larger sampling. This is a
fixed-policy system comparison, not a learned training-free RL result.

A post-hoc source audit also identifies a rendering difference before the
Reviewer boundary. Retain the complete policy results, but withdraw the
interpretation that this isolates only Reviewer tool-schema availability.
The registered specification and all original artifacts remain unchanged.

## Registered terminal comparison

All numbers retain all 625 inputs. Differences are tools minus control, in
percentage points unless stated otherwise. Use the official combined
word/character pooled SLU score; per-row F1 mean is a different estimator.

| Measure | Control | Tools | Difference / interval |
| --- | ---: | ---: | --- |
| Official pooled SLU-F1 | 60.9636 | 61.5083 | +0.5448; CI95 [-0.8827, +1.9986] |
| Intent exact accuracy | 71.84 | 71.20 | -0.64; CI90 [-2.24, +0.96] |
| Equal-scenario pooled SLU-F1 difference | -- | -- | +0.0734; CI95 [-1.8012, +1.7752] |
| Equal-scenario intent difference | -- | -- | -0.6325; CI90 [-2.2117, +0.9837] |
| Mean per-row SLU-F1 | 45.8035 | 46.1991 | +0.3956; descriptive |
| Strict complete-task exact rate | 26.56 | 27.36 | +0.80; descriptive |
| Initial candidate coverage | 76.64 | 76.16 | -0.48; diagnostic |
| Empty-target exact entity FP count | 124 | 128 | +4 |
| Nonempty-target exact entity FN count | 383 | 370 | -13 |
| Nonempty-target exact entity FP count | 297 | 298 | +1 |
| Unparsed delivered answers | 2 | 1 | -1 |

The paired utterance-cluster bootstrap used 10,000 draws and seed 20260915.
SLU CI95 lower -0.8827 is not above zero. Intent CI90 lower -2.24 is not above
the frozen operational margin -1.44. Failure to establish protection is not
proof of a statistically established intent loss. Do not substitute a
positive point estimate or per-row mean for the registered pooled endpoint.
There are 191 empty-target and 434 nonempty-target inputs in each arm.

## Complete trajectories and realized acquisition

The treatment exposes native lookup schemas in all 701 Reviewer requests.
It records zero tool attempts, accepted calls, rejected calls, or result
events across all 625 episodes. The control also has zero tool events.
This evaluates the realized availability policy, not the quality of answers
from an actually invoked tool. Do not infer that on-demand tools cannot help
or that the task difference came from newly acquired evidence.

| Whole-path diagnostic | Control | Tools |
| --- | ---: | ---: |
| Initial strict wrong answers | 480 | 473 |
| Inputs with a later Solver visit | 68 | 76 |
| Initially wrong inputs receiving revision | 66 | 74 |
| Revision makes the complete answer correct | 13 | 10 |
| These repairs retained at delivery | 13 | 10 |
| These repairs lost at delivery | 0 | 0 |
| Revision damages a previously exact task answer | 1 | 1 |
| First answer to delivery: repairs / harms | 23 / 2 | 20 / 1 |
| Final wrong inputs without revision | 406 | 390 |
| Covered-but-wrong intent without revision | 38 | 41 |
| Uncovered-and-wrong intent without revision | 110 | 105 |
| Empty-target FP without revision | 92 | 94 |
| Planner REVISE decisions | 68 | 83 |
| Revision-limit terminal dispositions | 0 | 7 |
| Illegal Planner action dispositions | 1 | 0 |

These use strict exact intermediate diagnostics, not unofficial intermediate
SLU-F1. They describe realized paths, not causal node effects. The tools arm
has seven requests for revision after its one-revision limit; a REVISE count
is not a count of executed revisions. Format normalization changed 80/88
outputs. Normalization yields further strict repairs and one control harm;
do not assign all end-to-end changes to the reasoning loop.

The observed bottleneck is sparse useful correction with residual errors,
not disappearance of these 23 complete reasoning repairs at delivery.
Their retention does not establish that every local improvement survives
integration. Independently generated prefixes and fixed control-then-tools
order also preclude causal node attribution.

## Input isolation defect in the full path

All 625 paired first-Perception requests have the same speech-packet hash,
task instruction, history, empty tool-schema list, and supplied evidence IDs.
None has identical evidence bytes. The tools arm adds the exact prefix
[knowledge store=intent-boundaries role=intent-boundaries] to each card,
before any Reviewer decision: 293,938 extra characters over 625 requests.
Every difference in those evidence bodies is exactly this prefix.
The pinned diagnostic records every request join.

The existing named-store renderer in rails/knowledge_stores.py produces this
prefix, and rails/phase_tools.py applies it when the dispatcher has named-store
authority. The tool-free automatic path retains canonical plain bodies, a
distinction also documented in rails/slot_binding_view.py. Tool configuration
therefore changes earlier model context as well as later schemas.
Preserve sealed inputs and historical answers. Future matched policies must
use the same explicit rendering before the intended action boundary.

## OBS / ORG / SUPPLY / USE

- OBS: the same frozen cached speech interface; no ASR, encoder, or alternative
  observation was invoked.
- ORG: pinned original minus-R01 stores; no learned memory or knowledge update.
  F10 and semantic-delta remain closed.
- SUPPLY: every first Solver visit has exactly 20 exemplars. Their identity sets
  match in all 625 pairs. Each arm supplies 2,414 empty-entity exemplars among
  12,500 first-visit occurrences (19.312%). Empty means the original value tail
  is exactly 'none', not F10 JSON. There are 176 inputs with no such examples
  and 449 with at least one. Equal IDs do not guarantee equal rendered text.
- USE: first Reviewer sees the same evidence IDs and speech as first Solver on
  all 625 inputs per arm. No lookup evidence arrives. Repair/harm transitions
  extend through delivery; supplied IDs alone do not establish semantic use.

## Complete scenario results

Descriptive slices do not authorize subgroup admission. Equal-scenario
weighting is reported above separately from the natural-mixture primary.

| Scenario | n | SLU-F1 difference (pp) | Intent difference (pp) | Empty FP difference | Nonempty FN / FP difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | -6.2758 | +3.8462 | -1 | +2 / +3 |
| audio | 30 | -14.9499 | +3.3333 | +3 | +1 / +0 |
| calendar | 42 | +2.2130 | +0.0000 | +0 | -3 / +3 |
| cooking | 31 | +0.6524 | -3.2258 | +1 | -1 / +0 |
| datetime | 39 | +2.1988 | -2.5641 | +0 | -3 / -3 |
| email | 33 | -7.1364 | -6.0606 | +2 | +2 / +0 |
| general | 42 | +7.0550 | +2.3810 | +3 | +0 / +0 |
| iot | 33 | -0.9122 | -6.0606 | +0 | +0 / +0 |
| lists | 37 | +0.8453 | +0.0000 | -1 | +1 / +3 |
| music | 27 | +4.7619 | +0.0000 | -3 | +0 / +0 |
| news | 36 | +7.0352 | -2.7778 | -1 | -2 / +0 |
| play | 37 | -3.6876 | +2.7027 | +2 | -1 / +1 |
| qa | 38 | +0.6450 | -2.6316 | +1 | -2 / -2 |
| recommendation | 29 | +5.2321 | -3.4483 | -1 | -2 / -1 |
| social | 35 | -0.0166 | +2.8571 | -2 | -2 / -1 |
| takeaway | 37 | -0.9707 | +2.7027 | +0 | +3 / +0 |
| transport | 32 | +1.4962 | +0.0000 | +0 | +0 / -2 |
| weather | 41 | +3.1347 | -2.4390 | +1 | -6 / +0 |

## Cost and closure

| Measure | Control | Tools |
| --- | ---: | ---: |
| Frozen-core generation contacts | 2,704 | 2,728 |
| Prompt tokens | 23,143,991 | 24,639,917 |
| Completion tokens | 158,738 | 163,367 |
| Repeated speech seconds | 11,891.7161 | 11,956.5544 |
| Generation contact-window seconds | 4,034.3190 | 8,664.2003 |
| Complete score-stage seconds | 178.6552 | 173.4114 |
| Observed generation utilization integral (GPU-h) | 0.8493 | 2.0944 |
| Mean observed generation GPU utilization | 76.08% | 87.12% |

Utilization is trapezoid-integrated from consecutive monitor samples no more
than 30 seconds apart within each recorded generation contact window.
Observed time is 4,019.0806/8,654.5072 seconds, with no excluded interior gaps.
These are generation-window observations, not fit-inclusive billing or causal
latency comparisons. Per-request summed latency is not wall time. Smoke,
fit, model load and scoring are outside these integrals. The engineering
smoke added 16 core contacts and zero tool calls; it is not efficacy data.
Do not attribute the fixed-order speed difference to tool execution.

The durable WSL queue ended at 17:41:07Z; detached analysis at 17:44:44Z.
Neither depended on network or assistant credits. The source checkout stayed
clean at da443cdc1027b3c01034c26485805240ec0e671d through source validation.
No service restart, new GPU family, generation replay or scorer replay was
introduced by this read.

## Root continuation decision

Close this fixed tools-availability comparison. Its episodes remain useful
observational diagnostics, not randomized action samples with learned-policy
propensities. The numeric optimization target has not changed.

Advance the planned F4 question as a complete candidate-recovery policy:
preserve original proposals; add source-bound exemplar-supported proposals;
supply distinguishing intent values and explanatory slot contracts; carry
that derived context through Solver, Reviewer, Planner, revision and delivery.
Candidate coverage is not a hard answer filter. The historical label union
supports this hypothesis but is not an achieved task gain or gold-conditioned
runtime policy.

Reuse shared named-store and native graph interfaces. Keep common role text,
program identity, delivery and evidence rendering in matched policies.
Before GPU admission, prove rendered-prefix identity, bounded proposal
provenance, original evidence retention, actual request fit and full closure.
Pre-register the finite proposal cap; record any added or displaced cards.
Candidate-only and Solver-only scores cannot become the system reward.

After a useful complete policy is validated, sample whole continuations at
recorded pre-action states, update from complete terminal feedback, freeze the
update, and execute another round. Compare with the best fixed whole policy.
Contextual graph integration and real multi-round learning remain outstanding;
synthetic tests and this fixed comparison do not complete training-free RL.

## Reproducibility

Pre-registration: docs/readiness/2026-09-25-slurp-stage3-evidence-path-v1-preregistration.md.
The immutable specification and newly sealed bindings are in the sibling
evidence-path readiness directory. Shared entries: export_system_feedback.py,
slurp_var1_official_feedback_v2.py, slurp_system_trajectory_read.py.
Derivatives: SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-EVIDENCE-PATH-OFFICIAL-READ-V1.
Closure receipt: docs/receipts/continuation/2026-09-25-evidence-path-system-closure.json.
It pins sources, read commands, derivatives, diagnostic recipes and this report.

No new DEV6570/test13078, runtime gold, paid research API, new weights,
second answering model, ASR, model or scorer contact was introduced by analysis.
