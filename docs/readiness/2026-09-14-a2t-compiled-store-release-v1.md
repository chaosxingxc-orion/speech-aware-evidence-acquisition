# Release compiled Audio2Tool knowledge through shared preparation

Date: 2026-09-14. Scope: model-free preparation for the native agent base.

## Completed implementation

The existing prepare-semantic-knowledge entry now accepts a separately named
compiled-store registration schema in addition to its unchanged authored-train
schema. The compiled path consumes the already prepared native Audio2Tool
snapshots; it does not rebuild source knowledge or relabel its source role.

Each registration pins the compiler receipt and snapshot bytes independently.
Preparation verifies the snapshot content hash, source identity, view, builder,
external-governed role and source paths. It rechecks the original lock,
construction-selection and registry bytes. It also matches compilation ID,
corpus hash, compiler settings and tool/value/facet counts against the
snapshot's bound source metadata. Store role must match the selected value view.

The resulting named-store release binds the compiler receipt as its source.
Both preparation paths share the existing locking and exact-publication
implementation. Matching existing outputs are reused without rewriting;
different bytes and input/output collisions are rejected. Original snapshot
and compiler artifacts are never changed.

A root-authored regression first reproduced an independent review finding:
a repinned receipt could describe another compilation while retaining genuine
snapshot source metadata. The implementation now refuses that mismatch before
publication. Final shared preparation/store suites passed 49 tests with 82
percent coverage of semantic_knowledge_preparation; Ruff, diff checking and the
engineering-base check passed. Tests use synthetic construction material, not
task outcomes.

## Reproduce preparation

Use WSL and the research Python environment. Set PYTHONPATH to the chosen
frozen checkout's absolute src path; do not install another editable package.
Run the existing public driver for each registration:

~~~text
python -B -m speech_aware_evidence_acquisition.core.driver prepare-semantic-knowledge --registration configs/preparation/a2t-tool-activation-store-v1.json --repo-root WORKTREE --data-root DATA
python -B -m speech_aware_evidence_acquisition.core.driver prepare-semantic-knowledge --registration configs/preparation/a2t-parameter-meaning-store-v1.json --repo-root WORKTREE --data-root DATA
~~~

Use the actual absolute WORKTREE and DATA paths. Preparation returns only
source bindings, release/completion locations and counts, without exposing
construction rows. The completed invocation and round-trip pins will be
recorded under DATA/coordination/a2t-agent-base-transfer-v1.

## Next runtime integration

The existing bootstrap_first_phase and FlightRuntime phase-supply preparation
can route speech-retrieved activation values to native Perception. The native
role runner already stages the completed source-bound AgentStateArtifact,
invokes the automatic supply callback, commits selected values and renders
them for the next role. Reuse those paths.

The missing component is a registered state-to-target selection policy for
Audio2Tool parameter values. The existing candidate_semantic_supply path is
SLURP-specific: its authored slot index, hypothesis parser and three-candidate
bound do not describe Audio2Tool. Extend the same automatic supply/router
boundary with task-appropriate target extraction and the compiled snapshot's
task_target index. Preserve ordered action occurrences and alternatives in
model state; deduplicate only repeated knowledge-card deliveries.

Keep exact tool names tied to the adapter's authoritative registry. A candidate
list supplies evidence; it must not silently restrict Solver's legal answer
space. Derive and register appropriate state/output bounds from the current
task contract rather than inheriting historical G5 or SLURP limits. Preserve
the complete response and explicit handling of malformed candidate state.

This release is necessary preparation, not proof that the parameter values
already reach a real Solver request. The runtime state parser, route
configuration, actual request fit, admitted campaign and complete paired task
evaluation remain outstanding. Preserve the current SLURP recovery and the
separately frozen exact base replication. Algorithm factors and sampling remain
deferred until the agent base is useful and reproducible.

## Completed publication and shared-loader verification

Both public driver invocations completed from clean source
c05b77f40cab8b194974ced18a448265c9188104. Root then loaded both releases together
through load_knowledge_store_binding. Each store has 152 values; the composite
contains 304 namespaced values and retains external-governed source role.
This is a store inventory count, not a number of values supplied per request.

| Store | Release SHA-256 | Completion SHA-256 |
| --- | --- | --- |
| tool-activation | 3fe5686762468c34ff441ddfa3a8591889726676258d352cf04367544fca43a1 | dfdcaaccc15ca5ec7682bce3312d5566888891d1e7973f3ee2536e82c08df82e |
| parameter-meaning | 7bafef2137bbbf9b44baebf0beb70570422d496729f7846ea99a22b6708a4373 | 24071625a272ac39b64090f8f1da90d847468523185de0317c32591dbdd1f90a |

The composite snapshot identity is
70df477a371a544d76d015701fa5040cfa18d7f0a4d95f3efe603aa0538c12cf.
The source-bound runtime binding and verification record is
DATA/coordination/a2t-agent-base-transfer-v1/compiled-store-binding-v1.json,
SHA-256 915a837babe4721876057b631a56cbdbb14108ebc40d84b9dc532a2a48909a1e.
All original compiler artifacts remain unchanged. Preparation added zero
model, encoder, tokenizer, tool and scorer contacts. This verification does
not instantiate runtime supply routes or qualify a model-serving geometry.
