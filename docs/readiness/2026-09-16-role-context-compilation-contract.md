# Role-context compilation contract

Date: 2026-09-16. Root owns design and admission.
Owner direction: make role-specific context selection, analysis, cleaning and normalization
the central system mechanism; do not mechanically forward earlier node output.

## Status and immediate decision

Keep SLURP as the only active dataset. A1 maximum-five is complete and NOT_ADVANCED.
The registered typed-context system-versus-direct package now runs under STATUS-153;
the direct comparator has one precontact invisible-source recovery. Do not modify frozen
requests or launch the prepared history-only restriction automatically.

The shared typed role-context compiler is implemented through the native role binding and
has passed 163 focused synthetic tests. Read
docs/readiness/2026-09-16-role-context-implementation.md for the exact behavior and receipt.
The configuration is registered for the paired campaign. Actual request capacity is checked
within that campaign; task benefit remains unverified until the complete paired release.
The separate history-only Reviewer selector remains available as a diagnostic option.

Prefer a typed role view over a blanket deletion policy: preserve useful candidate IDs and
alternatives while explicitly separating their model-authored explanations from observations.
Keep the history-only option as a held diagnostic capability. It is not a required extra arm.

## One responsibility

Compile a bounded context for a destination role from registered runtime sources.

Use this sequence: select source versions, parse their declared contracts, validate
structural and source bindings, retain uncertainties and conflicts, normalize representation,
then choose the role view. Produce a source-bound compilation receipt and the exact bytes
used by both request-fit and dispatch. Preserve raw records unchanged.

This module organizes information; it does not become another answering model. Deterministic
code can establish schema validity, duplicate identity, legal-label membership, citation
availability and version binding. These checks cannot establish that a claim is audible or
semantically true. The frozen Perception, Reviewer and Solver roles retain those judgments
and must label them as judgments.

## Separate information classes

| Class | Meaning | Never upgrade it to |
| --- | --- | --- |
| Query observation | Original speech identity or an authorized derived observation | A correct transcript by assumption |
| Tool observation | Source-bound ASR, replay or other admitted tool output, with failure/uncertainty status | Ground truth |
| Task knowledge | Stable construction-source rules, intent contrasts, slot meaning and annotation conventions | Evidence that an example value was spoken |
| Candidate hypothesis | A legal candidate and model-authored distinguishing interpretation | A jointly asserted fact about the speech |
| Current draft | The exact answer version under review plus a validated parsed view when available | A validated answer |
| Review finding | A declared issue, cited evidence, uncertainty and proposed next information | An automatically correct issue or routing command |
| Control state | Remaining actions, revision/contact limits and executed tool status | Task evidence |

Carry sample identity, source state identity, source artifact/content hashes, producing role,
view version, semantic class, parse/binding status and source references. Record each retained,
excluded or merged element with its rule and source position. Keep a derived-view hash distinct
from the original response hash. A model confidence statement is not an independently measured
confidence score.

## Role views

| Destination | Required information | Context restriction |
| --- | --- | --- |
| Perception | Original speech, complete legal intent inventory, compact activation/exclusion contrasts; a bounded unresolved question on an admitted refresh | Do not seed a first perception pass with a later answer. |
| Solver | Distinct candidate IDs, separately labeled candidate interpretations and uncertainties, relevant intent contrasts, slot semantics and extraction conventions, admitted observations; current finding on revision | Do not concatenate all prior opinions or treat all alternatives as true. |
| Reviewer | Current exact draft and draft identity, original speech, relevant task rules, useful candidate alternatives as hypotheses, current tool evidence | Exclude stale drafts and prior evaluative conclusions; keep useful alternative information when it can be typed. |
| Planner | Structured current findings with citation-availability status, unresolved information gaps, current draft identity, allowed actions and remaining limits, tool status | Route on bounded current state; do not inherit free-form answer authority or convert a recommendation automatically to an action. |

Preserve currently required speech and knowledge interfaces in the first integration.
Removing modalities from Planner or changing knowledge selection is a separate factor.
Do not conflate a context view with a second retrieval system.

## Cleaning and normalization rules

- Validate all candidate objects before deduplication. Reuse the existing first-occurrence
  projection and retain its position map. Preserve candidate order and actual distinct width.
  Do not pad, invent alternatives or infer confidence from a short list.
- Keep candidate distinctions labeled as hypotheses. Preserve disagreement between candidate
  interpretations rather than synthesizing an unverified common story.
- Parse a draft without silently changing entity surface forms, negation, numbers, dates,
  units or mention boundaries. A malformed draft remains malformed and source-addressable.
- Parse structured findings with the existing strict contract. Keep a malformed or absent
  report distinct from a valid no-supported-issue report.
- Match evidence IDs to the role's actual visible source set. Mark an unknown, stale or
  unexposed citation unavailable. Availability does not establish entailment.
- Keep unresolved references and conflicting observations explicit. Do not delete uncertainty
  merely to shorten the context.
- Preserve current native tool call/result bytes and authority bindings. Compile role state
  outside that local tool chain; do not rename or summarize tool-call custody.
- Do not use evaluation labels, reference transcripts, future turns or offline error lists
  to decide runtime selection. Author new task knowledge from allowed construction sources.

## Reuse and implementation seam

Reuse AgentStateArtifact and the current phase-state ledger for source custody.
Reuse the registered phase-material/state-fill machinery and TaskAdapter/KnowledgeProvider
interfaces for task-specific values. Use the existing bounded SLURP hypothesis projector.
Move or expose the existing strict review-declaration parser at a shared runtime layer
rather than cloning its schema into a new controller.

Compile the chosen view in the existing role binding before NativeRoleSpeechBinding freezes
its messages and kwargs. The resulting request remains under FlightRuntime, OpenJiuwen,
the original service lease and the shared fit/dispatch builder. Default configurations must
retain their current behavior and identity. Do not add an experiment-specific controller,
a second history store or a separate baseline runner.

A typed projection must have an explicit derivative identity. It must not overwrite a raw
phase artifact while retaining that artifact's identity. Preserve full history for offline
attribution, even when a request exposes a smaller context.

## Smallest useful validation and experiment

Finish one coherent source-to-role compilation path before adding more tools or datasets.
Verify synthetic cases for duplicate candidates, invalid labels, malformed reports,
unavailable evidence citations, contradictory hypotheses, stale drafts, local tool history
and default-request parity. Inspect actual prepared requests, not just rendered prose.

After A1 closes, root chooses either its required replication or one context-compilation
contrast. Keep the candidate source, knowledge snapshots, model, roster and tool permissions
matched where possible. State any package differences openly. Do not run separate arms for
every field or combine larger N, new knowledge and new tools under an isolated-context claim.

Report full-task official quality, candidate coverage, common-covered intent choice,
correct-intent slot quality, review saves/harms and unsupported or missing entities.
Audit retained/excluded input classes and actual citation availability. Reduced text volume,
successful parsing and increased critique count are engineering outcomes, not task gains.

Preserve state, action and evidence records as a future trajectory-optimization workspace.
Manual context compilation remains base engineering. Define sampling, rewards and algorithmic
policy optimization only after a stable agentic base has been demonstrated.

## Verified reusable interfaces

The bounded read-only source inventory confirms the following interfaces:

| Existing interface | Reuse and limit |
| --- | --- |
| rails/slurp_intent_hypotheses.py: parse_slurp_intent_hypothesis_state and SlurpIntentHypothesisStateFill | Reuse strict sample-bound alternatives and original/projected hashes with position provenance. |
| rails/slurp_hypothesis_candidate_contract_view.py and rails/candidate_contract_lookup.py | Reuse exact ordered candidate-contract requests and source-pinned results. |
| TaskAdapter.candidate_contract_provider and candidate_inventory | Retain carrier-specific interpretation under the common adapter. |
| reproduction/slurp_scoring.py: parse_slu_response | Reuse extraction only after the declared answer schema is checked; this permissive parser alone does not prove a complete contract. |
| analysis/review_findings.py: parse_review_findings | Reuse the strict report contract through a shared-layer extraction; citations remain declarations until exposure is checked. |
| runner.speech_binding | Compile role-specific state after canonical supply resolution and before immutable request construction and FIT. |

The draft extractor accepts fenced JSON, does not enforce exact object keys and defaults a
missing entity list to empty. Consequently, do not silently turn a missing field into a valid
empty answer in the context compiler. Preserve a separate structural-invalid status using the
declared task schema. Preserve repeated entities and exact filler surface forms.

Keep candidate_semantic_supply and knowledge_target_lookup upstream of context compilation.
Never feed a reduced or normalized role view back into QueryState, a knowledge provider or
tool custody. Compilation itself must not trigger retrieval or tool contact.

Do not use a producer-wide PHASE_STATE_VIEWS transformation for this consumer-specific policy:
it would change every downstream consumer. Reuse its typed rendering primitives at the
role-binding seam while preserving full canonical history. No second controller or history
store is required.
