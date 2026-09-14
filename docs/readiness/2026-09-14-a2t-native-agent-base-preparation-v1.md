# Audio2Tool preparation for the shared native agent base

Date: 2026-09-14.
Scope: offline engineering and knowledge preparation. Preserve the running
SLURP source and the separately frozen exact SLURP replication.

## What is now proven

The actual registered Audio2Tool runtime adapter completes the shared native
Perception, Solver, Reviewer and Planner episode with synthetic model responses.
The integration test covers both acceptance without a tool and an on-demand
Reviewer task-contract lookup followed by Planner revision and a new Solver
answer. The delivered response is the eligible Solver response; its hash is
checked. Tool results remain visible to the next Reviewer and revised Solver.

The proof preserves five ordered task calls, including repeated calls to the
same tool, without imposing a SLURP Top-3 or four-call limit. Every role uses the
same bound speech packet. The direct and native adapters expose the same task
contract and roster; runtime gold/transcript access is forbidden in the test.
The requested task calls are output content, not executable analysis tools.

This is an adapter/episode integration proof with synthetic responses and
materials. It does not establish a complete real FlightRuntime admission,
request-capacity fit, official task quality or a completed Audio2Tool four-role
campaign. Do not reinterpret the older fixed-stage campaign as this system.

Root also corrected named-store composition to preserve the common source
partition role. Previously, composing external-governed stores silently
defaulted their composite to train. All-train composition retains its identity;
mixed roles require an explicit composition contract and are rejected. The
Audio2Tool stores in this preparation are both external-governed.

## Prepare different values behind reusable keys

Extend the existing native semantic-card compiler with an opt-in snapshot value
view. Preserve legacy output bytes and identity when the view is omitted or
explicitly full.

- tool-activation: exact tool name, its activation meaning and its exclusions.
- parameter-meaning: exact tool name, public signature, types, constraints,
  required/optional keys, source-scoped native forms, role-to-key guidance and
  artificial examples. Exclude the activation/exclusion paragraphs.

Retain all 152 tools, including schema-only tools. Bind each selected view into
its compilation source, snapshot identity and value provenance. Keep the
existing facet IDs and key representation text exactly, so existing key vectors
can be reused after their ordinary provenance checks. These keys still combine
activation and parameter-role guidance; this work does not create pure
activation keys or demonstrate a new retrieval method.

Use the two preparation configurations with the public compiler entry in WSL.
Set PYTHONPATH to the frozen checkout's src directory and use the research
environment's Python. Invoke the existing module with --config:

~~~text
python -B -m speech_aware_evidence_acquisition.rails.knowledge_compile_a2t --config configs/preparation/a2t-tool-activation-knowledge-v1.json
python -B -m speech_aware_evidence_acquisition.rails.knowledge_compile_a2t --config configs/preparation/a2t-parameter-meaning-knowledge-v1.json
~~~

Keep outputs under DATA, preserve historical outputs and refuse collisions.
The compiler entry does not start or contact a model service. A separate
completion receipt records the actual pins, equality checks, sizes and zero
model/encoder/scorer contacts after materialization.

The current activation exclusions name neighboring tools and warn against
matching shared nouns. They do not yet explain every pairwise semantic
distinction. Splitting these values is an organizational baseline, not evidence
that their discriminative content is sufficient. Likewise, native argument
forms are positive construction evidence, not exhaustive schema rules. For
example, setVolume can have a source-supported direction/steps form while the
public API describes deviceId/level. Preserve this distinction and its scope.

## Transfer boundaries that remain

Finish the useful SLURP base's same-setting replication before treating the
base as stable. The currently running enhanced TRAIN recovery is a separate
system and follows its existing one-recovery and complete-score contract.

Audio2Tool runtime configuration still needs explicit named-store releases,
role routing, real request capacity and an admitted complete paired comparison.
Do not force single-intent candidate semantics onto ordered multi-tool answers.
Do not equate the existence of an adapter test with complete transfer readiness.

The existing 4000-sample Audio2Tool packet and query assets use the first user
turn for all 500 Tier-7 samples. A five-dialogue pilot exists; a full dialogue
variant does not. Keep that input distinction explicit. A future full-dialogue
comparison requires matching legal input for direct and system arms, source
receipts, registered encoding and a separate protocol; do not silently replace
the current material or expose a future answer.

Only improve a capability when released complete diagnostics identify its
missing evidence or failed information flow. Keep algorithm factors, trajectory
sampling and reward-driven policy updates deferred until the useful base is
reproducible. These compiler and runtime changes are engineering, not
training-free RL results.
