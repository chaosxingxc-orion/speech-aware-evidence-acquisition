# Bind knowledge construction to the executed phase instruction

Owner scope:214. This is a prospective repair to the existing system-text
construction join. It grants no model, construction, scoring, retry or read
allocation and does not alter the active update1 worker.

## Reproduced problem

The shared phase executor passes `PhaseMaterial.instruction` to
`FrozenCoreClient` as `contact_instruction`. The client records that instruction
in the final CONTROL history item. The top-level `task_instruction` remains the
adapter's task contract. The old construction join compared only the top-level
field to the proposed construction instruction, so a correctly executed phase
instruction could not pass the join. Conversely, a matching top-level instruction
could pass even when the current CONTROL instruction requested a different task.

The old join also trusted the edit contract's declared source groups without
requiring the actual generating sample identities to be included. A complete
TRAIN generation could therefore lose its own sample from cumulative construction
exposure, including when it proposed no change.

## Repair

Keep using the shared bundle verifier before materialization. Bind each output
to its unique generating request and SLURP source identity. Require every actual
generating sample to occur in the contract's cumulative evidence groups. Reject
duplicate sample/request identities and tool-derived request envelopes.

For an agent request, require one current final CONTROL item, following only
agent-state items, with its exact contact identity, turn number, instruction text
and text hash. An older state mention, prefix match, stale hash or overridden
top-level instruction cannot establish execution. Preserve the legacy top-level
instruction route when no agent history exists. No prompt, tool, runtime,
response, knowledge content or policy is automatically changed.

The materialized values still enter the normal semantic preparation/release
path. A release must reproduce the generated edits exactly; the downstream
compiler continues checking the bundle's cumulative-source disjointness against
the evaluation roster. No task labels or scientific results are read by this
repair.

## Validation and its limits

Four failing assertions reproduced the two valid CONTROL cases being refused,
the overridden top-level instruction being accepted, and missing construction
ancestry being accepted. After the repair,203 related tests pass, including18
new cases; the changed construction module has100% statement coverage. Ruff,
engineering-base and harness-admission checks pass.

The request proof uses the real `FrozenCoreClient`, speech-feature payload
serialization, trace sink and shared raw-trace verifier with a synthetic
in-process transport. Its request then reaches the materializer. Separate tests
exercise both instruction locations through the real semantic preparation and
release join, including rejection of an authored row that was never generated.
Negative cases cover current-control identity, content and ordering, carrier
binding, source loss, duplicate outputs/requests and no-change ancestry.

The bundle lifecycle is a verified-bundle test double in these new join tests;
they do not claim a new end-to-end live construction flight or fresh artifact
finalization proof. Existing bundle/flight admission remains mandatory for actual
construction. Real model, tokenizer and scorer contacts added:0. Update1's active
frozen worker and artifacts are untouched. Future construction still requires its
own exact source, budget, capacity, registration and coordinator admission.
