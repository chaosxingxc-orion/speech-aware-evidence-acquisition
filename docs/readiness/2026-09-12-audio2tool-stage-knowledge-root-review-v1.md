# Root review: Audio2Tool decomposition, decision-specific knowledge and agentic execution

## Owner input and root assessment

The owner asks whether Fable5.1's stronger Audio2Tool baseline came from selecting tools before filling arguments, and distinguishes discriminative routing knowledge from explanatory parameter knowledge. The distinction is useful and should shape the system, but the historical evidence does not isolate decomposition as the entire source of the gain. One model call measures a configured model-plus-input-plus-output-contract system; its observed accuracy is not a mathematical upper bound on the same frozen model under better evidence and control.

A second call is useful only if it changes the decision problem, adds needed evidence or performs an effective check. Repeating the same whole task can preserve correlated mistakes. The architecture should expose specific unresolved decisions and lawful actions, rather than equate a plan/draft/final label sequence with a functioning agentic system.

## Historical experiment recovered

The actual baseline fragment is configs/baseline/a2t-semantic-agentloop-select-fill-top32.json. Its historical stages use a canonical observation, local transcript-based dense retrieval of 32 candidates, routing-only SELECT, then selected-occurrence-only FILL with tool names and multiplicity locked. It is not the model-free MF-5 enabler in a2t-phase-select-then-fill-v1.json; that enabler explicitly prohibits effectiveness interpretation.

The closed 104-row experiment has 13 rows from each of eight tiers. Under its original v1 corpus/multiset scoring:

| Arm | Answer contacts per row | Exact match % | Tool multiset accuracy % | Corpus slot F1 % |
| --- | ---: | ---: | ---: | ---: |
| Direct M0 | 1 | 17.31 | 40.38 | 30.19 |
| Knowledge-matched joint one-call | 1 | 24.04 | 62.50 | 40.45 |
| Knowledge-matched joint draft/revise | 2 | 25.00 | 63.46 | 40.68 |
| SELECT then FILL | 2 | 25.00 | 59.62 | 36.52 |

The answer-contact column excludes the common observation/retrieval preparation of the knowledge arms. Direct did not receive that observation/knowledge. Split minus direct exact gain is 7.69 points, paired CI90 [0.96, 13.46]. Split minus matched two-answer-contact joint control is zero, CI90 [-2.88, 2.88], and its tool/slot points are lower. The recorded architecture admission failed.

The later v2 rescore of the same sealed responses gives exact rates 24.04, 31.73, 32.69 and 34.62 percent respectively; it does not represent new generation and did not change the recorded admission decision. Retain the original v1 mechanism decomposition as v1; no new decomposition was computed in this review.

The September 12 complete 4000-row experiment instead uses the released official first-call metrics: direct/stage/knowledge exact 18.900/17.950/18.600 percent and tool accuracy 62.025/60.525/58.550 percent. These are not directly comparable with the old 104-row corpus/multiset figures. Population, scoring, observations, retrieval query signal, K, knowledge content and output contracts differ. Do not attribute their numerical gap to decomposition alone.

## What the old evidence diagnoses

The 104-row split partition is 4 unreachable tool-set rows, 38 selection failures, 36 parameter failures after correct selection, and 26 exact successes. Retrieval reaches all required tools on 100 rows, yet selecting and consuming them remain separate bottlenecks.

SELECT omitted signatures, key/type constraints and other interface cues present in the joint arm. Its weaker selection is consistent with over-separating knowledge views; it does not prove which individual omitted field caused the difference. Neighbor substitutions dominate its selector errors. Fields such as groupId versus deviceId can identify target scope before any value is filled.

Among the 62 correct selections, only 26 final calls are exact under v1. The overlapping parameter-error taxonomy includes extra keys on 20 rows, missing keys on 6, wrong same-type values on 14 and wrong types on 4. deviceId appears on 20 error rows. Supported source evidence, argument presence, occurrence ownership, correction state and normalization need explicit representation. Public defaults and valid types do not prove a value was spoken or an operation was requested. Sparse benchmark annotations must be analyzed separately from real semantic requirements.

The old report also finds all 26 multi-call rows non-exact in every arm. Global tool selection and field-level filling alone do not resolve call occurrence and state binding.

Current production already contains build_interface_routing_knowledge_ground and build_sparse_parameter_knowledge_ground in rails/a2t_select_fill_ground.py. Recover and test those shared builders; do not create duplicate knowledge implementations. Their existence alone does not establish the unexecuted successor's quality.

## Knowledge organization decision

Use one canonical source-bound knowledge model with purpose-specific views. Do not maintain two contradictory copies of tool facts.

| View | Retrieval key / access | Value content |
| --- | --- | --- |
| Routing | Current lawful operation, target/scope and competing tool hypotheses | Choose/avoid boundaries, effects, preconditions, closest alternatives, minimal distinguishing interface keys/types |
| Parameter | Exact selected tool plus argument and current missing/conflicting evidence | Semantic role, type/unit/range/enum, extraction anchors, normalization, required/optional/conditional/omission rules, supported compact examples |
| Occurrence and state | Current call occurrence and lawful prior dialogue state | Argument ownership, explicit correction/cancellation, carryover/reset, compatibility and multiplicity rules |

Routing should be primarily discriminative but retain interface information that changes the decision. Parameter knowledge should explain how to bind evidence and also distinguish absent from present, one argument role from another, explicit values from defaults, and current from superseded values. An explanatory paragraph that cannot change a binding decision is not sufficient.

For example, the registry-derived lighting knowledge distinguishes setGroupLightState (group scope) from setLighting (one-device scope), and setBrightness from color/temperature operations. A selected parameter view explains level's public range and which current evidence supports its value; it does not infer an unseen device ID from a convenient training example.

Long-term knowledge contains these supported semantics. Per-episode working state contains provisional tool choices, occurrences, extracted spans and conflicts. Corrective memory contains a separately validated procedure for an observable failure pattern, not raw benchmark examples or unsupported universal rules.

## Connection to the required agentic system

Distinguish Audio2Tool's predicted business calls from the system's actually executed internal reasoning/evidence tools. The native benchmark does not require contacting all 152 external business services. The agent should actually invoke local ASR, knowledge views, schema checks or permitted speech observations when the frozen main model decides they are needed.

Treat SELECT/FILL as decision responsibilities rather than an irreversible two-step conveyor. A provisional selection can load a compact argument view. If filling exposes incompatible scope, absent required evidence, a correction or a plausible sibling tool, the main model can request the relevant knowledge, call local Whisper for the current speech, or return to selection within the registered bound. Final answer authority stays with the frozen core.

Do not force every sample through every tool. Precomputed base speech packets and pinned inventories remain lawful preparation; a no-ASR decision must yield zero ASR forward and no transcript supply. Cache reuse follows a real selected request and remains separately reported.

## Next experimental consequence

Maintain the owner's SLURP-first order. Implement the shared bounded answer-or-tool loop and phase-specific knowledge access once. Use intent/slots to validate the same responsibilities quickly, then transfer the proven execution path to Audio2Tool's tools/arguments/occurrences with its own values and native metrics.

Before another full Audio2Tool comparison, bind a matched population, model/service, observation and query route, candidate access, scorer and final output contract. Compare focused decomposition with an equal-contact joint control when attributing decomposition; compare fixed versus model-selected acquisition when attributing agency. Direct remains the complete-system reference. Do not revive the old 104/128-row scale plan or change historical admissions.

Report task-native exact/tool/parameter metrics plus full-call/multiplicity diagnostics. Separate candidate reachability, selection, argument binding and observation/format failures. Conditional filling accuracy is descriptive; use full paired final outcomes for system claims.

Only after a live agentic baseline exists should TRAIN trajectories drive group-relative external-policy or corrective-memory proposals. Optimize which evidence to seek, which view to open, when to revisit a decision and when to stop, rather than only comparing final answer strings.

## Sources and scope

- docs/readiness/2026-09-03-a2t-select-fill-architecture-decision-v1.md.
- docs/readiness/2026-09-03-a2t-select-fill-agentloop-104-v1-verdict.md, including its v2 correction.
- configs/baseline/a2t-semantic-agentloop-select-fill-top32.json.
- configs/baseline/a2t-native-system-recovery-stage-control-v1.json and a2t-native-system-recovery-knowledge-v1.json; the current phase instruction asks for a complete provisional answer, then a complete final answer.
- docs/readiness/2026-09-12-a2t-native-system-final-result-v1.md.
- src/speech_aware_evidence_acquisition/rails/a2t_select_fill_ground.py.
- configs/knowledge/a2t-kc-a1/targets-v1.json.

This root review reads existing closed reports, configuration and code only. It adds no model, audio, tokenizer, encoder or scorer contact and grants no standalone flight authority.
