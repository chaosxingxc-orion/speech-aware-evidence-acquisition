# Close the native terminal recovery after Perception output truncation

Root decision on September 13, 2026. This supersedes the running status in
STATUS-080. Preserve the original positive exploratory pair, the failed strict
replication, the failed terminal recovery, and every source runtime separately.

## Observed failure and custody

The terminal recovery at frozen commit
64983e41527f968e7ee9c39abeb791ad01594a18 ended with exit code 1. Its attempt
automatically became ABORTED with 629 model contacts and 1733.2905625 repeated
speech seconds. These are consumed contacts, not completed task answers.
The shared queue's new abort path worked. Root verified the dead worker,
no active port-8080 connections, a free generation kernel lock and three
consecutive idle monitor samples before archiving and reconciling lease metadata.

The Perception contact flight-0544 requested max_tokens=256 and returned
finish_reason=length with 256 completion tokens. The wire envelope was structurally
valid, but its 1165-character content was truncated and not valid candidate JSON.
The role bridge correctly refused this incomplete response. Do not accept length
as stop, repair its JSON, replay its response, or manufacture a complete manifest.

The current Perception schema bounded candidate count to one through three but
left distinction strings unbounded and allowed 32 entries in each metadata array.
Its prompt asked for compact output without an enforceable size contract. This
is a mismatch between the role's output contract and its shared token allowance.
The earlier revision-limit issue and this output-contract issue are distinct.

Root failure closure:
SPEECHRL_DATA_DIR/coordination/slurp-native-terminal-system-dev1000-recovery-v1/failure-attempt-closure-v1.json
SHA256 e9237f792c5b2127e212943d2679262acc09e84b4ae2c511e3b394666eb16141.
The fit closure retains 629 request-fit receipts and 2516 endpoint rows. Raw traces,
the original failure log and the exact failed runtime remain intact.

This was the sole recovery after a failed full-system replication. Close this
flight permanently; do not append another full-roster retry. Do not score the
incomplete system population. The completed direct replication's first official
score remains unread. The original exploratory system improvement has not been
successfully replicated.

## Prospective correction and engineering proof

Keep Perception focused on candidate coverage: retain one through three distinct
legal intent IDs and let Solver choose the final intent and entities. Add optional
shared output bounds rather than a separate experiment formatter. The new
configuration limits each distinction to 128 characters and both metadata arrays
to zero entries; the prompt asks for at most 12 words per distinction and empty
arrays. Preserve the exact legacy schema when these options are absent.

Use max_tokens=512 in the separately registered four-row engineering configuration.
The owner prioritizes quality over token cost; there is no reason to squeeze the
structured intermediate result into an empirically inadequate shared allowance.
This proof changes both compactness and output space, so it does not estimate the
isolated effect of either change. A later full-system comparison must register
its complete serving/output configuration and a suitable direct comparator.

The proof uses the existing four exposed TRAIN engineering rows, the same public
OpenJiuwen graph, cached speech with no mmproj, independent slot knowledge,
Reviewer-owned task-contract calls, Solver-only final authority and the explicit
finite terminal policy. Retain legal TRAIN scorer declarations so sealing remains
valid, but permit only check and worker stages: generate and seal, never score.
Require all four Perception responses to end normally and satisfy the bounded
schema, all final answers to bind to actual Solver output, and actual fit checks
to bind to the sent requests. Stop on failure; there is no retry in this proof.

Four rows establish engineering connectivity only. They do not establish task
effectiveness, reliable completion across the full roster, or a new scientific
replication. Registration:
docs/readiness/2026-09-13-slurp-native-bounded-perception-proof-v1/.

## Independent preparation completed during the boundary

After the named stop decision, root stopped the quiescent decoder and used the
registered exclusive encoding window. All 60 released TRAIN-derived intent-boundary
keys were encoded once with the pinned local MF-7b encoder recipe. The 1000 speech
query vectors were reused under their verified dimension alias, with no re-encoding.
All 60 unique 2048-dimensional vectors passed source/order/finite/L2 readback.

Preparation receipt SHA256:
3c152fc086ed1d1858f5b3021a336570d1b68c87f9c3a5abbe16209c009e2653.
Facet vector export SHA256:
76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2.
Index SHA256:
f70cf26726143151e360015bf9a5c4b0922c9e1e9ecc0177878f9b5c77674dab.

This is completed preparation, not evidence of improved retrieval or task quality.
The next complete-system capability remains intent-discrimination knowledge at
Perception plus parameter/slot-explanation knowledge at Solver, behind a passed
engineering proof and a fresh root registration.
