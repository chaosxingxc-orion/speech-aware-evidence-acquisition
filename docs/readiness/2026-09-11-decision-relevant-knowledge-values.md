# Decision-relevant knowledge values: root design note

Date: September 11, 2026. Authority: OWNER017-021. Status: design guidance written while the fixed SLURP task-agent family is running; no new model contact or experiment admission. This note does not change the frozen three-arm protocol.

A knowledge value should supply the grounded relation that helps resolve a task decision. Similarity finds a potentially relevant item; it does not establish that the item contains the missing information, applies to this query, or will be used correctly. Optimize those links together. More words, more candidates, or more forceful instructions do not establish useful distinctions.

## Define the decision before the value

Record the lawful decision being supported: intent choice, entity presence, role assignment, surface form, tool operation, argument ownership, correction, or state transition. Identify plausible alternatives without erasing the full legal answer space. State which permitted observation can distinguish them and which uncertainty remains.

Use the smallest sufficient value for that decision. It can be a typed relation, a source-supported spelling, a role binding, an argument constraint, a paired contrast, or a short procedure with explicit conditions. Do not require every value to contain pairwise prose or a long universal template.

At construction time retain:
- the source and its split/version, exact evidence span or aggregate support;
- the relation being asserted, its scope, supporting and contradicting cases;
- the permitted strength of the assertion: observed example, supported tendency, or governed rule;
- the consuming decision and the evidence required for applicability.

At consumption time expose the needed relation and limits in a compact view, and retain source lineage outside the prompt. Do not promote an observed co-occurrence to a required or forbidden slot. An empty training annotation means no observed annotation in that example. A catalog entry makes a candidate available; it does not prove that the current speech contains it.

## Task-specific relations

| Native task decision | Candidate useful value | Critical applicability limit | Native outcome |
|---|---|---|---|
| SLURP scenario/action | Intent boundary linked to the command's target, operation or relation | Lexical similarity alone cannot determine intent; keep all legal paired labels | Intent, scenario and action exactness |
| SLURP entities | Observed intent-role association; distinctions between a requested entity, a modifier and irrelevant context; source-supported value form | A prior example is not a mandatory-slot template and its concrete value must not be copied into the query | Official micro SLU F1, row-mean F1, omission/spurious/type/surface diagnostics |
| Audio2Tool operation | Choose/avoid semantics relative to sibling operations and the requested end state | Tool availability and semantic plausibility do not establish the user's request | Official tool and exact-call metrics |
| Audio2Tool parameters and turns | Argument roles, legal keys/types, correction scope, lawful carryover and applicable state relationships | Do not import future turns, assume unobserved execution, or present generated calls as successful business actions | Official parameter and full-call metrics by all eight tiers |
| E21 lexical/entity transcription | Source-bound spelling plus role/company relations and span applicability | A call-local list supplies candidates, not evidence that a name was spoken; preserve acoustic support | WER, PERSON, numbers, nonentity and insertion errors |
| E22 transcription | Admitted metadata can condition candidate applicability where supported | Coarse region/company metadata is not a speaker identity or a word-level supplier; no new supplier is currently admitted | Native ASR metrics supported by the carrier |

The present SLURP compact frame adds only observed intent beside the same observed fillers. It is a deliberately limited association test, not a completed boundary-rule knowledge base. Existing Audio2Tool G4 cards already express several operation/argument distinctions; their full-tier shared execution path still needs a bounded generalization. Neither fact demonstrates a task gain.

## Keep knowledge, memory and policy distinct

Knowledge describes grounded task facts and relations. Memory describes validated conditional guidance about system behavior, including what went wrong, which action helped or harmed, and where the lesson applies. Raw TRAIN rows and unvalidated model reflections are neither validated memory nor system improvement.

For example, a role relation belongs in knowledge. A separately validated lesson that a particular ambiguity requires revisiting the current speech can belong in memory. If a rule is universal, deterministic and governed, implement it as shared policy while retaining provenance. Keep conditional guidance conditional.

Construct and validate memory on declared separate roles; freeze its version before evaluation. Historically exposed discovery results can motivate labeled hypotheses but cannot supply runtime answers or become fresh validation. Preserve negative evidence and exceptions.

## Evaluate construction and consumption together

Use a chain of separately observable questions:
1. Did retrieval make the relevant grounded distinction available?
2. Did the selected value actually contain it, with correct scope?
3. Did the current query provide evidence that the relation applied?
4. Did the Solver's final decision use the evidence without copying unsupported values or suppressing valid alternatives?
5. Did native task quality improve, and what new errors appeared?

Retrieval relevance/accuracy is only the first question. Offline gold may measure these diagnostics after registered exposure; it must not label runtime applicability. Supply traces show availability, not causal use. A plausible explanation from the Solver is not a substitute for matched outcomes.

For value-content attribution, hold the selected items, ordering, stage program, legal labels, observation and delivery fixed. Report input-length and formatting differences that remain. For full-system contribution, compare the complete live agent and direct calls through the same harness, acknowledging stage-count differences. A fixed predecessor replay cannot establish complete live-system quality.

Use the declared task outcomes and paired uncertainty. Report repairs and newly introduced harms, all strata, natural/equal-stratum weightings, failures and fallback. Do not select a value merely because it helps one favorable metric or subgroup.

## External optimization after a usable system exists

Expose external choices with inspectable state and lineage:
- ORG: merge or split relations, add supported distinguishing content, retain exceptions, compress redundant values.
- SUPPLY: select applicable distinctions, view, ordering and evidence scope.
- OBS: choose additional lawful speech only when an actual uncertainty can be resolved.
- USE/control: choose the tool, evidence-use instruction, revision and stopping action.
- Memory: admit, retrieve, revise or retire validated conditional procedures separately from factual knowledge.

Keep core parameters frozen. Evaluate policy/value/memory changes on declared optimization and validation roles before a frozen evaluation cohort. Do not label arbitrary summarization or prompt editing as RL. Training-free optimization should update these explicit external objects using task outcomes and qualified credit assignment; no cost or online-latency penalty is required by the current owner objective.
