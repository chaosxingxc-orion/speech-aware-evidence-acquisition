# Native knowledge reference projection: implementation handoff

Date: 2026-09-16. This is a model-free engineering successor to the context diagnosis.
It does not reopen the twice-failed typed-context flight or admit any new model contact.

## Scope and behavior

The optional flat composed-config key is:

    "native_evidence_projection": "native-knowledge-reference-v1"

The key is absent from historical configurations. No existing experiment fragment was
changed. Config hashing therefore continues to identify historical defaults as before;
an explicitly opted-in future config receives its own identity.

The registered shared projection runs after native framework source/group validation
for both precomputed speech-feature and raw-speech native request paths. It replaces
only a local knowledge result's duplicate body with a structured reference when the
same evidence ID, source URI and exact full content already appear earlier in the
current request. Ordered selections, result metadata, assistant/tool pairs and call IDs
are preserved. Source-conflicting bodies are refused; genuinely new bodies, nonknowledge
observations, rejected calls and speech packets retain their original information.

The full dispatcher observation and OpenJiuwen history remain canonical and unchanged.
References are a derived wire representation. They identify the visible body location
and content hash and explain their meaning to the core. They never depend on a historical
visibility flag, substring match, future message, or another reference.

The existing prior-role native-history projection remains unchanged. This patch addresses
the local current-role return path diagnosed in the failure; it does not implement semantic
summarization, role-specific card filtering, truncation or knowledge rewriting.

## Shared request construction and provenance

LlamaServerTransport.render_request_with_receipt returns the actual body and a separate
derivation receipt without sending anything. Existing render_request delegates to that
same builder. Dispatch uses it too, so the FIT caller and generation path do not maintain
separate projection logic.

The receipt binds source request bytes, source payload/messages, projected messages,
the rendered body's canonical hash, and each local tool document/placement. It is not
inserted into the API body. Before an opted-in request is posted, the current native trace
buffer receives exactly one ORG record for the derivation. Missing active trace custody
refuses dispatch. Receipts are invocation-local, not mutable transport-global state.

Registry and engineering-base checks cover the new key and canonical registration.
No new controller, launcher, adapter subclass, private scorer or exception was introduced.
No editable package was installed. Tests explicitly import the isolated WSL source.

## Verification

Implementation commit: e4b8798b4c023c8d0ff5f24ad596d2820da808f9.
The combined WSL regression suite passed 309 tests; one existing Windows-only junction
test was skipped. The new pure projection has 92% statement/branch coverage. Ruff,
engineering-base and diff checks passed. No real model, tokenizer, speech-tool or scorer
contact occurred.

See IMPLEMENTATION-VALIDATION.json for exact checks, counts, source hashes and tool boundary.
Verification is synthetic and model-free. Existing transport/history/rejection behavior is
covered alongside new positive and refusal cases. The 21-card synthetic case establishes
UTF-8 message reduction with complete retrievable information; it is not a tokenizer
measurement or a task-performance result.

## Limits and next admissible work

The failed final wire was not independently reconstructed. Do not state that its 302-token
overflow is now measured to fit. References can add overhead for short bodies, and new
large evidence still consumes capacity. Model understanding of the reference format needs
prospective validation. Do not suppress FIT failure or silently accept an unreviewed answer.

Keep the failed recovery source at 9bf27b28708bb93607138e7bcd1eacb66eab3f08 frozen.
After handoff/ownership reconciliation, a distinct bounded proof must register the current
source, exact route/config, actual requests, service identity, contact limits and stop rule.
It should exercise duplicate and new knowledge, rejection, raw/feature routing as relevant,
and reference use under the real model. Four rows are engineering evidence only.
The closed full-roster recovery and held replica remain ineligible.

For scientific progression, use CONTINUATION-BRIEF.md and FUTURE-EXPERIMENT-DESIGNS.md.
Task-quality evaluation and same-roster replication must follow a separately admitted
complete comparison. No partial system score or released direct-score read is supplied here.
