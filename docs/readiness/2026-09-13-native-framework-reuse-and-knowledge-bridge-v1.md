# Reuse the native agent framework and connect task knowledge

## Framework boundary

Reuse the installed OpenJiuwen Workflow, BranchRouter, ReActAgent, ModelContext,
Tool, and role/session machinery already integrated by reproduction/ojw/native_roles.py
and native_episode.py. Keep FlightRuntime, EvidenceAgentController, shared request
construction, stable serving slots, metering, and source custody as the repository's
experimental boundary. Do not introduce an alternative agent loop or task launcher.

The completed SAEA-SLURP-NATIVE-ROLE-GPU-PROOF-V1 established four actual native
Reviewer tool calls and exact tool-result consumption. All four final outputs
came from accepted Solver responses. Its 20 model requests and 80 tokenizer
endpoints are sealed; it did not demonstrate a GPU revision, selective trigger
quality, or task improvement. Preserve that proof and its defects.

The remaining domain work supplies definitions and evidence which a generic
framework cannot infer: legal candidate IDs, role output contracts, discriminative
intent knowledge, explanatory slot knowledge, and dataset-specific scoring.
Keep knowledge construction separate from memory of general correction rules.

## Shared bridge implemented

- Keep canonical candidate-state parsing as the omitted default. Explicit
  compact_source_phase consumption validates raw bytes/hash plus the configured
  phase and shared-sealer sample identity before local canonicalization.
- Preserve candidate order and bytes. Reject illegal IDs, duplicate IDs, changed
  source identity, or malformed objects; never repair sealed predictions.
- Supply released slot values through the existing KnowledgeProvider and named
  store binding using the configured Perception state, not the immediately
  preceding role. This also works when the preceding role on revision is Planner.
- Retain a fully visible selection on Solver revisits without another acquisition
  or extra knowledge dose. Record each query-specific acquired/already-visible
  decision, and reject partial overlap.
- Separate common task facts from each role's output contract. Perception emits
  complete scenario_action candidates; Solver chooses one jointly with entities.
  Reviewer/Planner keep the analytical decision responsibilities.

Use the existing slurp-intent-hypotheses-v1 response format for Perception in the
next configuration. It enumerates legal IDs and permits one through three
candidates; the consumer still enforces unique IDs. Its pinned source catalog
is an enum authority, not an additional semantic knowledge supply.

## Prospective capacity and scientific scope

The released slot store contains 54 authored values, with 402 observed bindings
over 60 legal intents. An intent has a median of 7 associated cards and a maximum
of 16. Across every one-, two-, or three-intent combination, the largest union
contains 28 cards. These are construction-source measurements, not evaluation
results. The full legal entity inventory remains authoritative, including types
without an authored value.

The next engineering configuration retains the complete associated union
(max_values_per_candidate=16, max_total_values=28), rather than choosing a small
alphabetical prefix. Prepare a decoder-only 4-slot geometry with total context
65,536 and output ceiling 256 for actual-request capacity validation. Root alone
manages a service switch after admission. Capacity fitting stays prospective and
uses every realized native request; a failure does not permit silent truncation.

Reuse the same four already exposed TRAIN rows to prove this concrete bridge.
This is not a quality screen or a new scientific roster. Keep the new recipe
UNREADY until root binds its protocol, plans, exposure rows, pins and service.
It does not yet demonstrate consumption of both knowledge stores, task quality,
selective speech-tool benefit, or training-free optimization.

## Model-free validation

128 focused tests passed across candidate parsing, semantic supply, knowledge
providers/stores, phase material and native runner/FlightRuntime dispatch.
Ruff and the engineering base check passed. A separate bounded review found no
correctness issues in compact custody or repeated Solver supply. No model,
encoding, tokenizer or scoring contact occurred during this implementation.

The earlier broad-suite report contains 13 failures outside this feature's
touched behavior, including stale historical-readiness expectations, environment
PATH setup, and existing registry/catalog assumptions. The suite is not claimed
green. Do not expand this bridge into unrelated maintenance before the next
registered GPU work.

## Execution closure update

The proposed bridge and its sole recovery both stopped before any model,
tokenizer or analytical-tool contact. The second cause is the framework's terminal
system-prompt whitespace normalization, not structured output. The original
registered prompt and strict request guard are preserved; a successor template
removes the single terminal newline for model-free compatibility verification.
Both experiment cells are now held/check-only. See
[the closure](2026-09-13-slurp-native-knowledge-proof-closure-v1.md).
The prior successful native tool proof remains unchanged. No semantic knowledge
consumption or new task-quality gain has been demonstrated.
