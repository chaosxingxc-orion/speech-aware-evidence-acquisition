# Status036: cohort closed; owner prioritizes system optimization headroom

Date: 2026-09-11T13:30:08.719249+00:00. Progress: both paired families are generated, scored once, analyzed, decided and finalized. The original goal remains active; OWNER-SYSTEM-OPTIMIZATION-014 changes the current stage's selection criteria.

## Current owner direction

Cost is not a research-selection factor. Large gains are not required yet. First investigate whether the multimodal engineering base improves over direct model calls and identify component optimization directions. Select that system, then design and implement relative system-level training-free RL.

Historical guards remain unchanged in their reports. Their failed system admissions do not rule out selecting E21 as an optimization base. Root proposes E21 as the primary candidate, SLURP as supporting component evidence. Read docs/readiness/2026-09-11-system-selection-and-training-free-optimization.md.

## Completed cohort

- E21 fresh direct then KC-E1f:1593 windows/44 calls per stage;3186 generation calls. Both complete scores ran once and all frozen whole-call/secondary analyses completed. PERSON error23.1402% ->19.7463%; gain3.3939pp,CI90[2.4461,4.4005]. WER8.12086% ->8.07499%. Insertions10336 ->10341 fail the old point guard. Report: docs/readiness/2026-09-11-e21-offline-system-result.md.
- SLURP final program-matched pair:1000 examples and2000 generation calls per arm;4000 total,12004 fit endpoints. NEW500 mean-rowF1 gain1.0187pp,CI90[-0.9059,2.8329]; intent-0.2pp. Old admission fails primary and intent. Report: docs/readiness/2026-09-11-slurp-program-matched-result.md. OWNER011's single pair is complete; no adaptive rerun.
- Four raw generation attempts are FINALIZED through shared saved-score settlement, preserving all raw manifests. E21 uses the new raw score path; SLURP uses declared joined deliveries. DATA coordination/e21-slurp-root-settlement-closure-v1.json SHA9e6fa8582c794e599707217c5055e6bab499790ec0dd460ead9991b4d90e9db9.
- No active scorer or generation worker. Worker/lease sessions7178,20612,24915,20954 and scorer96331/comparator85731/settlement8600 are terminal. Do not restart them.

## Source, service and accounting

Frozen SLURP source21ebe2bc8f9c03469a48fe0c68e9b31f1c360dff remains unchanged at /home/chao/saea-worktrees/slurp-program-matched-generation. E21 directb4d30c0f and repair/scoring64440737 worktrees remain unchanged.

Root model remains resident, process35780, wrapper35765/session49170, monitor35824/session62129; serving-slurp-live-program-matched-np4-v1. It was independently observed alive during closure. No active experiment lease. OWNER013 still allows eligible registered GPU work; no new pause was requested.

Shared raw saved-score settlement commit22af3394 is on local master:112 relevant tests,81% branch-enabled module coverage,Ruff/base PASS. E21 raw parents have no derivative declarations; do not finalize_bundle/rescore. The four production settlements independently verified.

E21 generation-only2.335248821886381 GPUh excludes fit and prior encoding. SLURP fit-inclusive arm0.4502114679422643 GPUh excludes load and inter-arm idle. DATA coordination/e21-slurp-operational-timing-audit-v1.json SHAfdc8372ae28ea89b3995528a5de58e730da511586e49856be61f386f3d276b16 pins25 inputs. Device averages E21 53.5130/56.9506%, SLURP67.8145/70.6379%; do not claim sustained full load.419.538s handoff plus119.558s worker precontact missed the target. These are reproducibility observations, not selection penalties under OWNER014.

## Saved attribution and next useful work

- E21 insertion attribution:13 windows/12 calls,net+5 from+10/-5,none saturated. Different alignment counts do not by themselves prove invented lexical content. Receipt DATA coordination/e21-offline-direct-repair-insertion-attribution-v1.json SHAb7d96a7e9cf3c0eb140851510e133436beda133b29e140eeec8d8340817bc7ac.
- SLURP structured direct inputs match1000/1000 after transport-ID/slot exclusions; normalized direct intents match938/1000. Sent HTTP-body hashes were not retained. Receipt DATA coordination/slurp-program-matched-pair-semantic-request-identity-v1.json SHA40f5e6886f8496a3914aa1d22b4138873f6ba0863bb0a60b50435e135887753c.
- Complete shared current E21 Reviewer/Planner/selected-observation execution. Generic Planner tests do not prove this task path; current window bridge rejects phase_planner.
- Reuse AgentStateArtifact/AgentStepTransition and current registries. Existing VW adapter has helpful interfaces but fits an external policy; it is not automatically the selected parameter-free method.
- Define canonical legal state, finite component actions, sealed post-hoc reward, and policy-artifact update/freeze/evaluation. Select the system first. Do not leak gold into runtime or rewrite statistical outcomes.
- S4 sample encoding remains held by its existing dependency; E22/Audio2Tool/new summary tasks remain outside the GPU queue.
