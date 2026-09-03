# G8C fixed12 official-scoring successor design

## Decision

G8C is a fresh identity and run namespace over exactly all 12 rows in the frozen G8B
`support_remainder`. It performs no ranking, sampling, or outcome-dependent selection. The rows
are disjoint from both consumed G8 and G8B selected rosters. This preparation does not run the
flight or contact a model, scorer, audio byte, gold label, reference transcript, tokenizer,
service, or network.

## Frozen scientific protocol

The corrected prospective G8B state machine is reused by a thin configured launcher. Its prompts,
strict SELECT/BIND parsers, four macro-actions, G7 construction ground, support filter,
empty-selection passthrough, row-local invalid-output behavior, final-answer authority, and
OpenJiuwen workflow remain unchanged. G8C changes only the roster and split identity, the sample
count, the run/config paths, derived cost geometry, and trace/output namespaces. The corrected
audit emitter is covered against the real `TraceSink` contract before any flight.

The service context remains 32,768 tokens. Every actual request must be measured immediately
before contact against the 24,576 prompt-plus-completion cap and retain at least 8,192 tokens of
headroom. Two sample-affine slots, two concurrent requests, queue depth four, temperature zero,
and zero retry, repair, resend, and jitter testing remain frozen.

## Exact cost geometry

Each row has 29 shared contacts, exhaustive and support-only resolves, one SELECT, and a final
resolve when SELECT/BIND remains valid. This gives a base of 33 contacts per row. A nonempty valid
selection adds BIND; an invalid SELECT removes final resolve; an invalid BIND contributes both one
added BIND and one removed final resolve. Therefore realized contacts are exactly
`396 + nonempty_valid_selections - invalid_selects - invalid_binds`, with a minimum of 384 and a
maximum of 408.

The 12 frozen G1 receipt durations sum to exactly 76.694 seconds. The conservative speech budget
is `ceil(76.694 * 34) = 2,608` seconds. No audio bytes were opened to derive this value.

## Sealing, scoring, and decision

All four complete 12-row manifests must seal before gold or scorer access. Each whole manifest is
then eligible for exactly one unchanged official scorer invocation. Four independent whole-
manifest jobs may run through four outer workers; manifests must never be sharded or partial scores
averaged. One post-score branch oracle may then be built and scored under the frozen tie rule.

Oracle exact match of at least 11/12 and slot micro-F1 strictly above 0.90 are jointly required to
open only a separate approximately-100-row randomized, propensity-logged Vowpal Wabbit
registration. Failure expands knowledge or action construction on a new identity-only roster.
No approximately-100, approximately-1,000, test, confirmatory, Stage-3, or paper-scale execution is
authorized here.
