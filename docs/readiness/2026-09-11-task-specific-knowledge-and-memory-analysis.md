# Task-specific discriminative knowledge and corrective memory

Date: September 11, 2026. Authority: OWNER-DATASET-TASK-ANALYSIS-019, OWNER-CROSS-TASK-KNOWLEDGE-020 and OWNER-DISCRIMINATIVE-VALUES-021, continuing OWNER017/018. Root synthesis of governed SLURP TRAIN, local carrier/adapter/scorer definitions, and already closed analyses. No new model result is claimed.

## Core principle and design decision

Construct values that provide source-grounded distinctions relevant to the current decision. Ask what ambiguity a value can resolve, what evidence supports that distinction, and under what conditions it applies. Relevance or similarity alone is insufficient. A discriminative value must not manufacture certainty where the source or speech is ambiguous.

Distinguish labels/tools, roles, present versus absent mentions, valid versus superseded arguments, and speech-supported versus merely plausible edits. A canonical spelling or an argument constraint can provide a distinction without being written as a pairwise contrast. Completeness and grounding still matter.

Use one control plane with task-specific knowledge construction, value schemas, consumption and experience applicability. Include Audio2Tool now. Keep SLURP as the first fast execution carrier without imposing its knowledge format on other tasks.

Analyze five links: legal source -> preserved relation -> lawful retrieval -> actual stage supply -> grounded Solver use. Retrieval accuracy addresses only the middle link. Payload length is not a quality measure.

## Native task map

| Carrier/task | Native output and outcome | Decision-relevant knowledge |
| --- | --- | --- |
| SLURP intent | Scenario/action/intent; separate label metrics | Legal label relationships, operation/object distinctions and grounded prototypes |
| SLURP slots | Type/filler mentions; official entity and SLU F1 | Conditional role frames, mention boundaries, presence/absence contrasts and annotation conventions |
| Audio2Tool | Predicted tool calls/arguments; official tool accuracy, exact match and parameter F1, plus separate multi-call/slot diagnostics | Registry semantics, sibling distinctions, argument constraints and composition/correction/state rules |
| Earnings21 | Transcript; normalized whole-call WER and labelled entity/error diagnostics | Call-specific names/terms, role relations and applicability to an uncertain speech span |
| Earnings22 | Transcript; registered ASR scoring | Existing metadata brief; separately bound contextual sources when available |

Business-tool execution is not established by tool-call prediction. Meeting-summary quality is not established by transcription accuracy.

## SLURP: root TRAIN audit

The new audit reads governed real TRAIN annotations only, resolving the source through the live umbrella lock. No DEV/test annotation, audio decoding, tokenizer, model or scorer contact was added.

Artifact: DATA `coordination/slurp-train-task-relations-audit-v1.json`; SHA256 `12ec7ed251b6658ff3abaf9dac7822f529bd09b6716b446e5731d1c9aa6e005c`. The adjacent Python analysis records the computation.

| TRAIN property | Measured count | Consequence |
| --- | ---: | --- |
| Utterances / recordings | 11,514 / 50,628 | Multiple recordings are not independent semantic knowledge units |
| Scenarios / actions / canonical intents | 18 / 46 / 60 | Flat scenario/action lists imply many nonexistent pairs |
| Slot types / entity mentions | 55 / 11,367 | A type inventory does not identify a correct mention |
| Utterances with no entities | 3,755 | Preserve leave-empty behavior |
| Utterances with several mentions of one type | 380 | Preserve mention instances and role binding |
| Type-set signatures / shared across intents | 379 / 137 | A slot signature does not identify intent |
| Filler strings observed under multiple types | 181 | Vocabulary lookup does not determine semantic role |
| Raw intent strings differing from scenario_action | 162 rows | Retain the established canonical mapping |
| Support per intent | 4 to 810 utterances | Preserve uncertainty about sparse conventions |

These are annotation counts, not model errors. TRAIN 'home' appears as definition_word, house_place and place_name; 'train' appears as event_name, news_topic and transport_type. Action 'query' occurs under 12 scenarios. Interpretation requires the surrounding request and role.

For alarm_set, 182 utterances contain 9 observed types and 26 type-multiset patterns; time occurs in 136, and 31 have no entities. For calendar_set, 810 utterances contain 16 observed types and 112 patterns, including 132 with no entities. Neither intent has a type present in every TRAIN utterance. Observed/common/rare does not mean mandatory.

### Actual value gaps

Current speech-query retrieval uses TRAIN text keys and supplies observed type=filler pairs. A value's task_target metadata is not automatically rendered into consumed content. This rendering omits the source phrase, mention boundaries, competing interpretation and evidence for whether a field is present.

The legacy builder groups, sorts and deduplicates fillers. The audit finds four repeated identical type/filler mentions beyond set cardinality. A future mention-grounded format must retain source mention identity/order when relevant; historical artifacts remain unchanged.

The three new formats are experimental primitives: typed-fillers changes serialization, slot-type-set deletes filler information, and intent-slot-frame adds the TRAIN intent relationship. They do not yet provide a source-span relation or discriminative boundary. A shorter string is not evidence of better knowledge.

| Decision | Missing relation or risk | Proposed discriminative value and consumption |
| --- | --- | --- |
| Intent | Shared action does not identify its object/domain; copying neighbor labels can break a correct draft | Bilateral operation/object boundary with supported cues and exceptions; retrieve using competing lawful hypotheses while retaining all 60 labels |
| Mention presence | Schema encourages filling an absent field, or a real mention is missed | Optional-role frame plus supported present/absent examples; require current-speech evidence before filling |
| Type/role | Same filler can have several types; narrow schema can omit a rare valid role | Source-span-to-role example with surrounding phrase and competing role; retain a rare-type escape path |
| Surface/boundary | Paraphrase and time/date normalization change the required surface; proper names are open-ended | Minimal phrase-to-slot exemplars and annotation conventions; preserve current speech rather than substitute a catalog item |
| Acoustic ambiguity | Text alone may not identify the relevant sound | Selected source-bound speech/text/role pair; compare added audio only for an information need |

Reuse the existing source-bound decision graph: its older audit includes 117 shared-action/signature relations. Construction coverage is not model-performance evidence.

### Closed error evidence

MF-9's historical KC-S1b decomposition attributes 45.41% of entity loss mass to missing mentions, 25.96% to surface differences, 20.16% to spurious mentions and 8.48% to type swaps. Date/place_name/time jointly account for 32.70%, through different failure modes. These proportions do not automatically describe the latest system.

Official SLU F1 here aggregates entity-distance counts; intent accuracy does not enter it directly. Intent can affect schema selection indirectly and requires separate reporting.

Retain KC-S1b examples: removing them was harmful. More descriptions and three-shot worked answers were null-compatible; vocabulary cards failed their twin guard. KU-S3 supports a fixed-predecessor filler-supply component. The later matched live system has NEW500 mean-row gain +1.0187 points, CI90 [-0.9059,+2.8329], and fails its frozen system gates. Component gains do not establish full-system quality.

## Audio2Tool: all eight task items

The legal registry has 152 tools. Existing semantic cards already contain names, legal keys/types/constraints, choose/avoid distinctions and supported value forms. Recover this richer work rather than assume all values are sparse.

| Tier | Required distinction | Useful value content |
| --- | --- | --- |
| Direct | Which operation and target scope? | Sibling-tool boundaries, one object versus group, exact schema |
| Parametric | Which spoken value belongs to which argument? | Key meaning, types, units, enums/ranges and omission/default rules |
| Multi-intent | Which actions and arguments belong together? | Call-specific scope, operation composition and supported dependencies |
| Implicit | Which operation matches the desired outcome? | Source-supported operation effects, prerequisites and alternatives |
| Needle | Which instruction is actionable and which is a distractor? | Scope and relevance boundaries with minimal supporting evidence |
| Correction | What changed and what remains valid? | Replace/cancel/update semantics and field-level precedence |
| Multiturn | Which earlier referent or argument remains applicable? | State binding, lawful carryover and reset boundaries |
| Intent blending | Which purposes require distinct or shared operations? | Shared/exclusive conditions, argument ownership and compatible decomposition |

These are semantic dimensions, not runtime use of gold tier labels or eight newly authorized experiments.

Closed 400-row official tier results range from 34% tool accuracy for implicit requests to 82% for correction requests; blending is 38%. These are official first-call metrics, not complete multi-call success rates. They suggest different bottlenecks, not one retrieval problem. A separate old error audit found 142 tool-set errors among 303 failing rows, alongside argument, value and parsing errors. Do not mix scorer versions or reinterpret scorer alignment as model improvement.

Native task quality can improve through internal knowledge/observation/state tools without connecting all 152 business services. Native tool execution remains a separate capability claim.

The registered official scorer uses the released first-call parser and tool/EM/parameter metrics, with multi-tool diagnostics separately retained. The repository scorer compares tool-name and canonical-call multisets and slot triples; those are separate definitions and not official ordered-call metrics. Complex-tier full-call correctness must be reported separately so a correct first call does not hide omitted or misbound later calls.

Candidate memory should contain a validated observable symptom -> corrective procedure: sibling confusion, stale argument after correction, or a misbound conversational referent. Merely restating benchmark semantics is knowledge/policy, not learned experience.

See the [Audio2Tool audit](2026-09-11-audio2tool-task-information-audit.md) for source locations and tier-specific hypotheses.

## Earnings21 and Earnings22 task items

| Item | Required distinction | Value / state needed |
| --- | --- | --- |
| Ordinary words | What was spoken versus a fluent paraphrase? | Local speech and nearby lawful working text; usually no additional domain KB |
| PERSON/proper names | Which supported spelling fits the sound and context? | Call-local names, roles, organization relations and source-backed applicability |
| Organizations/products/terms | Which entity is being mentioned here? | Typed call-specific relation, with source section and relevant local evidence |
| Numbers/units/negation | Which quantity, unit and polarity were actually spoken? | Current-span evidence; narrowly relevant conventions, not guessed financial facts |
| Window continuity | Which fragment belongs at this boundary? | Explicitly bound local speech/draft state; avoid duplication and propagated errors |
| Speaker/topic continuity | Which lawful earlier state is relevant now? | Candidate observed turn/voice state; predicted clusters are not true identities |

E21 already has ConEC names and KC-E1f participant/role, organization/division, company/ticker and product/segment class lists. Its gap is span-to-candidate applicability and grounded use, not the mere absence of a name table.

The closed fresh E21 repair reduces PERSON error 23.14021% -> 19.74631% and WER 8.12086% -> 8.07499%, with five more insertions. Preserve the useful entity result, small overall gain and failed historical insertion guard. The newer quality/headroom objective does not rewrite an old verdict.

Diarization and speaker summaries remain component hypotheses evaluated through native transcript quality. True speaker/reference alignment fields are not runtime shortcuts. The declared earlier/future-state boundary does not change silently because the motivating use case is offline meetings.

E22 currently supplies a narrow metadata brief: ticker, country/region and dialect/language-family fields. These are coarse call priors, not individual speaker identity or evidence for a word. E22's ConEC PDFs do not have an admitted equivalent of the E21 text supplier. Resolve that actual source binding rather than borrow E21 facts.

Neither task defines native minutes/summary quality in this study. Summaries may be working-state compression candidates, assessed by native task outcomes.

See the [Earnings audit](2026-09-11-e21-e22-task-information-audit.md) for current suppliers, task items and legality.

## Knowledge, memory and shared execution

Knowledge states source-supported facts and task distinctions. Working state records this request's hypotheses, bindings, corrections and observed context. Corrective memory records an execution-derived, independently evaluated procedure and its applicability, support, regressions and limits.

Examples of standing knowledge/policy, not newly learned memory: use current-speech evidence; respect an explicit correction; preserve legal argument keys. Memory must add evidence about which observable failure pattern is helped by which action. Do not store evaluation answers as guidance.

Share TaskAdapter, KnowledgeProvider, EvidenceAgentController, FlightRuntime and OpenJiuwen, plus source/version bindings, request construction, actions, delivery and scoring. Configure task-specific builders and value payloads. An SLURP role distinction, an Audio2Tool operation card and an E21 entity relation need a common envelope, not identical content.

Retrieve for a decision: task + phase + lawful hypothesis/conflict + available evidence. Preserve key -> selected value atoms -> consumed stage -> outcome lineage. Stable construction means preserving supported distinctions and exceptions, not keeping the largest catalog or repeating every source example.

The initial new experience library admits one pinned TRAIN construction only; it is not universal cross-carrier admission. Runtime memory-tool integration and real admitted memories remain pending.

## Next work and experimental criteria

1. Prepare one decision-relevant value candidate per active carrier from existing sources: SLURP role/presence/boundary relations, Audio2Tool operation/argument/state distinctions, E21 span-relevant call knowledge. Track E22's separate source gap.
2. Prioritize the first SLURP comparison. Hold selected keys/order and phase graph fixed while changing the value relation. Rebind snapshots and register actual requests. Do not bulk-encode TRAIN audio solely to consume a ready roster.
3. Evaluate value contents with task-native paired outcomes, repaired versus newly broken cases, strata, no-answer/extra-output behavior and grounded use. A generated explanation of a distinction does not prove that the evidence was used.
4. Verify direct versus complete fixed agent through the same executor; distinguish component controls from independently generated full systems.
5. Keep Audio2Tool in parallel readiness now, using its existing cards and all eight strata. Queue only prospectively registered flights through the one GPU service.
6. After useful actions exist, validate memory on/off over the same knowledge and tools. Then optimize external ORG/SUPPLY/OBS/USE and experience applicability on the declared update role, freezing them during evaluation.
7. Extend the stable control skeleton to E21/E22 with their native values and metrics. Cost and online latency are diagnostics, not mandatory reward penalties; immediate large gains are not a prerequisite for a promising system.

No new owner choice is needed to include Audio2Tool or adopt the discriminative-value principle. Exact GPU comparisons require their prospective configuration and exposure records; old held experiments remain unchanged.

## Sources and corrections

- `data/slurp.py:32-63,127-162`; `rails/adapters/slurp_runtime.py:43-87`; `rails/knowledge_build.py:216-250,665-696`.
- [Existing relation audit](../checks/speech-aware-evidence-acquisition/2026-08-22-knowledge-relation-audit/README.md).
- [MF-9 slot decomposition](2026-09-08-mf9-slurp-slot-gap-audit-v1.md).
- [KV recovery](../checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md), [KU-S3 recovery](../checks/speech-aware-evidence-acquisition/2026-09-10-ku-s3-max256-recovery-verdict/README.md), [matched live SLURP](2026-09-11-slurp-program-matched-result.md).
- [E21 live result](2026-09-11-e21-offline-system-result.md).

The September 3 SLURP information audit wrongly labels gold scenario runtime-legal. This report supersedes that statement: only predicted/current-lawful scenario state can guide runtime. Preserve the historical audit unchanged.

CPU value builds and memory tests establish engineering behavior only. This analysis adds no GPU/model/tokenizer/scoring contact and no new effectiveness claim.
