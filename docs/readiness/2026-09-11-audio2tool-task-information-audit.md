# Audio2Tool task-information audit

**Source checkout:** /home/chao/saea-worktrees/experiment-closeout-integration, commit bdfc3cab406d7c90eeb795d2635540e5d23db6c5.

This model-free audit covers the local Audio2Tool carrier, registered knowledge builders, and already-authorized closed reports. It does not authorize a new exposure, model contact, scoring run, or GPU preparation.

## Task contract

src/speech_aware_evidence_acquisition/data/audio2tool.py:1-50 records the frozen carrier layout: tier manifests, public WAVs, and tools_registry.csv. load_audio2tool (around line 314) exposes runtime-safe sample identity and media facts. load_expected_calls, load_official_gold, and load_query_rows are explicitly scorer or construction readers; annotations and query fields must not enter an evaluation request.

The eight frozen task families are tier1_direct, tier2_parametric, tier3_multi_intent, tier4_implicit, tier5_needle, tier6_correction, tier7_multiturn, and tier8_intent_blending. The task relation is speech -> intended tool name(s) -> argument keys and values -> native output. Tier 1 tests direct selection; Tier 2 adds explicit arguments; Tier 3 tests multiple calls; Tier 4 requires implicit end-state resolution; Tier 5 tests a salient requested item; Tier 6 resolves a correction; Tier 7 carries relevant earlier turns; Tier 8 blends intents.

load_tool_registry around line 687 exposes 152 registered definitions with domain, category, name, signature, description, defaults, and constraints. data/audio2tool_tools.py renders the same rows into native tools schemas. reproduction/toolcall_scoring.py:1-40 defines tool accuracy, exact match, and micro slot-F1 over tool, argument key, and canonical value triples.

The carrier supplies schemas and scores returned calls. It has no connected side-effect executor or returned tool observation in the Audio2Tool request path. The repository rails/tools.py:335-412 ToolEntry catalog can execute study-owned wrappers, but that is a separate control-plane capability. This absence is a boundary of the present quality task, not by itself a reason to reject native speech-to-tool-call evaluation.

## Existing knowledge and values

rails/knowledge_build_a2t.py:150-200 builds task-neutral construction rows containing tool/domain/category, argument-key signatures, observed value forms, call count/order, and speaker identities. It excludes evaluation utterances, labels, concrete gold values, and future turns.

rails/a2t_executable_semantic_cards.py:142-170 builds the reusable semantic VALUE artifact: exact names, legal key sets, public types and constraints, choose/avoid distinctions, construction-supported value forms, and guidance for multiple-call ordering, correction resolution, implicit end-state resolution, and relevant multiturn carryover. configs/knowledge/a2t-kc-a1/targets-v1.json and contrast-notes-v1.json add registry-local distinctions such as one light versus a group, routine versus scene, HSB versus Kelvin, and firmware update versus reboot.

Stable task knowledge is tool schemas and constraints; operation and sibling distinctions; legal key skeletons and value-form classes; and multi-call, correction, implicit-state, and relevant-multiturn rules.

Conditional corrective memory would record a validated deployment-state condition and the consequence of a bounded prior decision, such as an ambiguity between registered sibling tools or a correction pattern. It must be source-bound, exclude gold and evaluation text, and be learned or validated from sealed trajectories. It must not relabel semantic cards or a knowledge snapshot as experience memory.

## Closed evidence

docs/readiness/2026-09-03-a2t-scorer-v2-zero-contact-study.md reports 303 V1-failing A0 rows. The principal partition is 142 TOOL_SET_WRONG, 39 EXTRA_KEYS_NONDEFAULT, 38 VALUE_WRONG, 24 PARSE_FAIL, and 26 EXTRA_KEYS_DEFAULT_ONLY; the remaining 34 are MIXED (12), EMPTY (17), TOOL_ORDER_ONLY (3), and MISSING_KEYS_ONLY (2). Thus the headline categories alone do not sum to 303. V2e raised A0 overall EM from 24.25% to 31.25% and Tier-1 EM from 12% to 40%, still far below the paper 92.4%.

docs/readiness/2026-09-04-a2t-tier1-official-population-v1-verdict.md:107-114 reports official tool accuracy: 58% Tier 1, 74% Tier 2, 74% Tier 3, 34% Tier 4, 76% Tier 5, 82% Tier 6, 60% Tier 7, and 38% Tier 8. Implicit end-state selection and intent blending are especially weak, while explicit parametric and correction families are comparatively stronger.

docs/readiness/2026-09-03-a2t-open-source-tfrl-adoption.md:96-129 reports the closed G7 comparison: same-row M0 scored 11/16 tool-correct, 4/16 exact, slot-F1 0.500000; G7 scored 7/16, 3/16, and 0.405797; the retrospective two-action oracle reached only 11/16, 4/16, and 0.514286. This supports improving the available action set before learning a routing policy. Cost remains a diagnostic under quality-first steering, not an admission penalty.

The repository comparison scorer tool_accuracy compares tool-name multisets. Ordered-call wording is a separate diagnostic concern; any ordered-call claim requires the exact scorer version and a predeclared metric.

## Eight-tier VALUE and memory relations

| Tier | Stable VALUE relation | Candidate conditional memory relation | Proposed untested comparison |
|---|---|---|---|
| 1 direct | Map operation wording to one registered tool and its legal keys. | Repeated sibling ambiguity in current observation state. | Full semantic card versus registry-only description. |
| 2 parametric | Map explicit values to typed constrained arguments. | Value-form or default-omission ambiguity for a tool family. | Full value-form card versus key-only card; report slot-F1. |
| 3 multi-intent | Preserve one call per action and spoken order. | State-conditioned detection of missing, merged, or reordered actions. | Ordering guidance versus ablation under an exact declared ordered metric. |
| 4 implicit | Resolve requested end state to the operation that reaches it. | Confusion among setter, getter, and transition siblings. | End-state guidance versus ablation. |
| 5 needle | Select the salient tool/value despite distractors. | Recurrent distractor families under deployment-visible context. | Targeted choose/avoid notes versus category-only notes. |
| 6 correction | Let a later correction supersede the earlier argument or action. | Bounded correction pattern tied to observed prior state. | Correction rule versus ablation. |
| 7 multiturn | Carry forward only relevant established facts and apply the final request. | Validated relevance/recency condition from prior turns. | Multiturn guidance versus ablation. |
| 8 intent blending | Emit required calls for blended intents with legal arguments. | State-conditioned decomposition choice validated before delivery. | Decomposition/value card versus single-pass card. |

These are hypotheses for predeclared comparisons, not claims of benefit.

## Missing relations and boundary

The repository has a strong schema-to-call contract and model-free semantic-card builders. It lacks a native Audio2Tool tool-result trajectory connecting a model-selected call to a real observation and then to a subsequent Solver response. The shared ToolEntry catalog and phase-tool bridge can supply that control-plane seam for future system work, but that would be a distinct shared-system test and must not be presented as existing benchmark execution.

The smallest quality-first next step is a matched VALUE comparison over the same frozen rows: preserve the 152-tool registry and output contract, vary one source-bound card or contrast-note artifact, and evaluate tool accuracy, exact match, slot-F1, parse failures, non-default extra keys, and tier effects. Conditional memory should be added only after a bounded trajectory supplies deployment-visible state, an explicit decision, and sealed downstream reward. No comparison should require cost improvement as an admission condition.


## Scorer identity clarification

The paper-facing scorer is the registered a2t-toolcall-official scorer (core/scorers.py:1038+, implemented in reproduction/a2t_scorer.py:507+). It uses the pinned Audio2Tool release metrics: primary tool accuracy, exact match, and macro per-sample parameter precision, recall, and F1. The tier accuracy figures above are official first-call metrics from that scorer and must not be described as repository multi-call metrics.

The repository scorers a2t-toolcall and a2t-toolcall-v2 are separate comparison scorers. reproduction/toolcall_scoring.py represents parsed call sequences and micro slot-F1 over tool/key/value triples. Its sequence handling is useful for diagnostics, especially on multi-intent rows, but it is not the official paper-facing metric. The authorized scorer-v2 report explicitly shows the divergence: on the same eight-tier whitespace cell, Tier 3 official tool accuracy was 74% versus repository v2 tool accuracy 24%, and Tier 8 was 38% versus 12%, because the official adapter evaluates the first parsed call while the repository sequence scorer evaluates the complete parsed sequence. The official scorer also reports macro parameter F1, whereas repository slot-F1 is micro over triples; these numbers must remain separate.

Accordingly, proposed VALUE comparisons should report a2t-toolcall-official as the primary metric family (tool accuracy, exact match, parameter precision/recall/F1), with repository sequence and slot-F1 measures labeled secondary diagnostics. Ordered-call effects are not implied by official tool accuracy and require an explicitly declared secondary metric.
