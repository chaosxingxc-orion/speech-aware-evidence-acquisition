# Discriminative knowledge values: construction and consumption contract

Status: owner-directed design principle and prospective hypotheses. This note
does not register model contacts, deploy a corpus, or establish effectiveness.

## Optimize decision-relevant information

Construct a value to supply grounded evidence for distinguishing plausible
alternatives at the current decision. Relevance of the retrieved key is only an
entry condition. A useful value explains what observation supports an alternative,
what conditions limit that support, and which unresolved evidence would separate
the remaining alternatives. A valid outcome can be a targeted observation request,
not only an immediate answer change.

Distinguishing information is decision-relative. A definition can be enough for
one task; another needs a semantic relation, parameter constraint, pronunciation
clue, or evidence-bearing span. Do not force every value into a contrast table or
infer a prohibition merely because a construction example is absent.

Separate these fields when supported by the source:

| Field | Construction requirement | Consumption purpose |
|---|---|---|
| Alternatives | Identify genuinely confusable labels, roles, tools or entities | State the decision the value can help resolve |
| Positive evidence | Preserve the relevant predicate, relation, argument or speech cue | Explain when a candidate is supported |
| Applicability and exclusions | Cite documented limits or validated contrasting evidence | Prevent an overgeneral rule from suppressing a correct answer |
| Missing evidence | Name the ambiguity and a legal observation that could resolve it | Let the planner choose whether to acquire more evidence |
| Answer constraints | Preserve the native schema and only supported normalization rules | Produce the required task output without inventing content |
| Provenance and scope | Bind legal source, construction version and validation role | Keep evidence auditable and prevent evaluation leakage |

These are shared concepts, not mandatory boilerplate to append to every prompt.
Keep full legal output inventories. Missing construction support is not evidence
that a legal label or tool is unavailable.

## Specialize values by task

| Task | Candidate useful distinctions | Required limits |
|---|---|---|
| SLURP | Intent boundaries and semantic slot roles; how the utterance relates a value to a requested action | Keep all legal intents; role counts do not establish a mandatory or forbidden slot; use native intent and official SLU metrics |
| Audio2Tool | Operation and object, query versus change, parameter meaning, dependencies and user-turn applicability | Keep all 152 legal tools; preserve the dataset's all-tier output contract; never treat a historical call as a current instruction |
| E21 and later E22 transfer | Legal entity vocabulary and relations that distinguish plausible spoken forms, plus local discourse evidence | Context may support an acoustically plausible form but cannot supply unspoken content; assess native transcription/entity metrics, not an invented summary objective |

For Audio2Tool, distinguish applicability across turns from merely matching a
tool name. For Earnings, any speaker or dialogue state is an observation-derived
working state, not automatically reusable knowledge or persistent memory.

## Make distinctions usable without over-exclusion

Apply the owner principle to a concrete decision, not to global information
volume. Retrieval relevance asks whether a card concerns the request.
Discrimination asks whether its evidence separates alternatives that are still
plausible for that request. Consumption asks whether the model can use the
distinction or request the missing observation. A card may pass the first test
and fail the other two.

Prefer a compact source-supported relation:

- State the ambiguous decision and the relevant alternative when one is known.
- Connect an observable cue or relation to the supported choice.
- State the applicability boundary and what the source does not establish.
- Identify a legal follow-up observation if the evidence cannot decide.

Do not mechanically render all four fields for every card. A concise definition
or public parameter description can already carry the required distinction.
Never equate absent construction support with negative evidence, and never turn
a frequent role count or argument pattern into a mandatory answer rule.

For Audio2Tool, public signatures and documented constraints describe the public
API. The native benchmark also contains construction-supported extension or
replacement argument forms. Preserve both source roles: public API validity is
not identical to the native target contract. Construction-observed combinations
are scoped positive evidence, never an exhaustive list of permitted patterns.
Keep this distinction visible in the card header, parameter guidance and examples,
not merely in an offline provenance receipt. Discrimination can concern the
operation, its object, the meaning of a parameter or which chronological user
instruction remains active. A local observation belongs to the current state;
a stable tool meaning belongs to knowledge; an independently validated procedure
for resolving repeated mistakes belongs to memory.

For SLURP, prioritize the semantic relation connecting the spoken value to the
requested action over generic lists of typical slots. For Earnings, prioritize
evidence that distinguishes acoustically plausible entity forms and local
references; do not let topical plausibility supply words that were not spoken.
These are candidate design directions, not evaluated correction rules.

A value-content comparison should freeze the selected keys and predecessor
state when the intended estimand is consumption of different values. Describe
such a comparison as a component study. A live system comparison must generate
its own legal states and account for downstream observation and answer contacts.
Neither study substitutes for the other. Measure corrected and newly damaged
answers on the complete registered roster, with the native overall and stratum
metrics. A reduction in one error type does not by itself establish a net gain.

Training-free system optimization can then select which supported distinction
to supply, when to acquire another observation, and when a validated corrective
procedure applies. Evaluate these decisions with independently scored task
outcomes under separated update and evaluation roles. Do not reward larger
knowledge volumes, stronger self-reported confidence or more fluent explanations
as substitutes for task quality.

## Couple construction to measured use

1. Define a source-supported distinction using declared construction material.
2. Freeze the value, provenance, trigger and any legal follow-up action.
3. Verify the rendered request contains the intended value and its applicable
   context through the same shared runtime used by the direct baseline.
4. Compare task-native outcomes on the registered matched roster. Count corrected
   and newly damaged answers, omissions and unsupported additions alongside
   overall and stratum metrics. Retrieval hit rate alone is insufficient.
5. Diagnose ORG, SUPPLY and USE separately: whether the needed distinction existed,
   whether it was supplied, and whether the answer behaved consistently with it.
   Treat traces as diagnostics; controlled comparisons are needed for causal
   attribution. Do not condition the main verdict on a favorable post-hoc subset.

A future content comparison should keep the selected keys and surrounding
program fixed where feasible, and record prompt-volume and visible metadata
differences. Keep live full-system comparisons for overall quality. Do not
confuse the two estimands or erase stochastic first-stage differences.

## Separate knowledge, working state and corrective memory

Store stable task meanings, facts and supported constraints as knowledge.
Store the current utterance, tentative answer, unresolved ambiguity and legal
speaker/dialogue context as working state. Store a corrective procedure as
memory only after independent validation: its trigger, action, success evidence,
failure conditions and scope must be explicit. Raw construction examples remain
source material; evaluation errors are analysis evidence and do not become
runtime correction rules.

Training-free optimization may propose or select value structures, supply
decisions, observation actions and validated corrective procedures while the
answering core remains frozen. Evaluate updates on separated roles with native
task reward. The objective is downstream decision improvement, not knowledge
volume, retrieval similarity or agreement with the system's own explanation.

## Current evidence

The closed role-coverage package added role statistics, coverage and text but
reduced primary SLURP intent accuracy by 2.2 percentage points. Official primary
entity improvement was unresolved; omissions increased while spurious entities
fell. This rejects that package as an improvement. It neither proves the general
principle nor isolates which added field caused the loss.

Retain the replicated compact-frame exploratory baseline with its original
serving identity. Use the new principle to specify the next distinct mechanism,
not to rename or repeat the failed package. See
[the complete result](2026-09-11-slurp-role-coverage-result.md).
