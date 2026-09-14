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

## Completed offline materialization

Both public compiler invocations completed successfully from clean source
da4d84ef26caed3c75434a36448fad4b109788c9. Root loaded the outputs through the
shared KnowledgeSnapshot reader and verified every key and projected value
against the pinned legacy snapshot.

| View | Tools | Schema-only tools | Total value UTF-8 bytes | Internal snapshot SHA-256 |
| --- | ---: | ---: | ---: | --- |
| tool-activation | 152 | 4 | 55,399 | cfb1e9e71660e98d21493925c4f6fe9343ff99e6a8075a7286c1e8027fed42bc |
| parameter-meaning | 152 | 4 | 205,581 | 7084f9c56b361ab8f38d2e0a6864ccb2d05bcc053dc70441de263b410ca6041f |

The original full values contain 252,102 bytes. These are corpus totals, not
request token counts or measured latency. Shared tool-name headers occur in
both views. All facet IDs, dimensions, representation kinds and representation
text equal the legacy version. Existing 152 key-vector IDs cover the exact
facet set. Both new corpora equal the original corpus bytes; the snapshots
select the different supplied values. All three original artifacts remain
unchanged. Both new snapshots preserve external-governed provenance.

Root verification:
DATA/coordination/a2t-agent-base-transfer-v1/value-view-preparation-verification-v1.json,
SHA-256 9f53ddbadacf1cbcac65660bff3084b06591140998e22586d5d281de4a93dafa.
The receipt binds both compilation receipts and snapshot files, the pre-run
input audit and the clean source-freeze receipt. Every recorded compiler
contact class is zero. Named-store release and runtime supply qualification
remain pending; exact vector-key equality alone is not that qualification.

Root's combined compiler/store/native-episode check passed 61 tests. The
compiler agent's adjacent compilation/card suites passed 69 tests and reported
87 percent compiler coverage; these counts overlap and must not be added.
Ruff, diff checks and the engineering-base check passed. Root reviewed the
implementation. The previous adapter/store integration change was already
incorporated into canonical master at 6a6c08d84d7b0cf580c215c1a69a862341c27a21.
