# Native role request integration decision

Status: root design decision after installed-framework review. The role nodes and
request scopes have synthetic proofs; the complete production episode is not
admitted. Keep the current candidate comparison on its frozen code.

## Reuse the framework

Let public OpenJiuwen Workflow own role edges and conditional routing.
Let ReActAgent own each permitted local tool loop and its conversation history.
Let AbilityManager own tool registration and dispatch. Use AgentRail to enforce
the configured authority before a backend action.

Do not add another scheduler, conversation manager, actor controller subclass,
or private experiment runner. Keep the existing controller as the interpreter
of study policy and the existing FlightRuntime as the owner of model access,
speech bindings, budget and artifacts.

A generic text-only ReAct example does not prove that the repository's original
speech packet, selected evidence and actual fit request reach the frozen core.
Complete that narrow adapter before admitting a native episode.

## One client and two distinct permissions

Use one existing FrozenCoreClient for a flight. Register its immutable tool
superset once; select the ordered subset for each actual contact. Preserve the
historical default when no subset is specified. An explicit empty subset
advertises no tools and requires tool_choice none.

Separate current execution authority from permission to consume historical
evidence. A Solver with no tools must still read a valid Reviewer observation.
The source request's sealed authority governs a past call; the current request's
subset governs only new calls.

Carry the actual request hash, contact and sample IDs, selected names and
selected schema hash in the completion and counted tool receipt. Validate
historical source authority against that receipt before projecting it. Never
authorize a historical call merely because its name is globally registered or
appears in the current subset.

## Adapt provenance; do not reconstruct conversation logic

Accept the framework's complete message sequence at the existing metered
request callback. Bind its configured system instructions and initial query to
the registered role and the sample's task state. Validate subsequent assistant
turns against preserved CoreCompletion wire messages and tool turns against
counted, source-bound tool observations.

Use existing AgentStateArtifact/history fields for versioned provenance.
Do not add arbitrary unvalidated raw-chat input or silently enlarge the D2
field set. Project only the validated sequence through the shared transport.

Keep actual assistant text, call IDs and raw argument strings. Legacy
CoreCompletion.text can contain normalized tool JSON and must not replace
assistant text. Keep the original wire bytes unchanged.

The installed AssistantMessage requires non-null content. A valid wire tool
turn can have content null. The current synthetic bridge explicitly refuses
that case; this is an integration limitation, not a malformed model response.
Production integration must use an explicit reversible representation:
framework empty content for that specific source-bound null turn, with the
original null restored from its completion receipt during request projection.
Do not guess this conversion from empty text alone and do not maintain a
second conversation history to implement it.

Retain the original query speech and scoped knowledge through the common
request builder. The first integration target is SLURP's prepared feature
path. E21 raw speech and selected re-listening need their own existing carrier
bindings and capacity proof; do not claim that the first target proves them.

## Role graph and answer authority

1. Perception consumes intent knowledge and returns ordered candidates.
2. Solver consumes candidate-specific slot contracts plus speech, selects an
   intent and creates a validated draft.
3. Reviewer examines that draft and may call its analytical tools. Its text
   completion ends a review, not the task.
4. Planner returns a structured accept, acquire or revise decision. Its allowed
   tools may differ from the Reviewer's.
5. Accept delivers the last validated Solver artifact. Revise routes to
   Solver with selected evidence. No other role can replace the answer.

Use native conditional edges for these transitions. The existing sequential
NativeRoleWorkflow is a proof scaffold and does not yet implement this graph.
Bound both per-node iterations and total episode contacts in configuration.
Handle node errors, output saturation, denied tools and exhausted budgets
explicitly; they must not become answers or unregistered recovery calls.

## Remaining integration acceptance

- One client executes a Reviewer tool turn and a later tool-free Solver turn.
- The Solver receives the exact prior observation; a changed source request,
  source scope, call ID, argument string or result is rejected.
- A globally registered but disallowed tool never reaches its backend.
- Framework completion of Reviewer advances to Planner/Solver, while only a
  valid Solver artifact is eligible for final delivery.
- Actual prepared speech requests and capacity materialization use the same
  callback and transport; null tool turns survive a complete round trip.
- Synthetic checks precede one registered real-model engineering proof. That
  proof is not task-quality evidence. Component and full-system quality remain
  separately registered comparisons.

## Knowledge construction scope

Select the already governed A/B-excluded SLURP TRAIN pool as the outer semantic
construction scope. The existing preparation receipt reports 9,354 utterances,
37,407 recording IDs, all 60 intents and 54 entity types in that remaining pool.
These are coverage counts, not quality results.

Preserve both historical A/B cohort exclusions. Do not use the full TRAIN
ontology's extra coverage to silently add support outside this pool. The
430-row exemplar roster is a different, narrower construction contract.

Each store receives its own exact support roster derived from the selected
outer pool. Its source identity and authored rows must agree with that roster;
do not attach every source ID merely to satisfy coverage. The intent store
contains activation boundaries and confusable exclusions. The slot store
contains semantic roles, extraction cues, formats, missing and ambiguity
behavior. Root authors and reviews their factual support and useful
distinctions. The shared builder verifies structure and binding, not usefulness.

Prepare source, snapshot and release through the existing builder registry and
a create-only shared preparation entry. Freeze the source reading/authoring
registration before inspecting actual TRAIN content. This decision itself
authorizes no model, encoder, tokenizer, scorer or new dataset read.

Evidence:
- docs/readiness/2026-09-13-openjiuwen-native-reuse-review-v1.md
- docs/readiness/2026-09-12-slurp-training-cycle-kb-preparation-v1.md
- docs/receipts/knowledge/slurp-kb-size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1.json
