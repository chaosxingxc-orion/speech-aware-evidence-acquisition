# Declared delivery from current-run phase responses

This shared extension closes the source-selection gap identified in
[LIVE-SYSTEM-EVIDENCE-GAPS.md](../superpowers/plans/experiment-handoff/LIVE-SYSTEM-EVIDENCE-GAPS.md).
It changes no historical model configuration, data roster or scientific
decision. A synthetic full-path proof is engineering evidence only.

## Declaration and execution binding

Declare each derivative in the actual experiment fragment before generation.
Preflight and manifest construction verify that the selected declaration is
present there, so a programmatic or baseline-only declaration cannot become
unrecoverable at scoring time. Keep
the ordinary parent output as the last phase's raw response. Use a
source_selector with exactly these fields:

- schema: saea-phase-response-pair-v1
- program_id: the parent's registered phase policy
- program_sha256: SHA256 of canonical JSON of PhaseProgram.as_json()
- predecessor_phase: the named earlier phase
- response_phase: the named terminal phase

Canonical JSON uses sorted keys, UTF-8, no ASCII escaping, compact separators
and no NaN. The ordinary composed config hash includes this declaration.
FlightRuntime verifies the program pin before adapter or service setup and
again against the exact program object selected for execution. It also
resolves the declared pure delivery rule and its parameters before generation.
Validate only declarations whose parent cell matches the current model,
dataset and baseline fragments, so another cell's derivative cannot block a
matching direct control in the same experiment.

A missing selector retains the existing OBS-window delivery route and its
sealed predecessor requirement. An opted-in phase selector uses the verified
parent trace instead of an external predecessor manifest or an unbound
phases.json convenience file. A malformed selector is refused, never silently
treated as the legacy route.

## Raw sources and delivered answers

Index the verified trace once for the complete roster. Select each source by
sample and the terminal control contact id
program_id:phase_name:sample_id. Require exactly one selected request and its
response; check request, control-text and response-text hashes. Match the
terminal source against the parent's raw output row. Reject missing,
duplicate, foreign, reversed or incomplete sources.

Normalize each source using its own actual request max_tokens and response
usage. Do not use a global configuration cap to reinterpret a phase override.
The existing shared saturation contract quarantines a source whose reported
completion usage reaches that cap. Missing cap/usage does not establish
saturation; the receipt records the available facts without inventing usage.
Both raw sources remain unchanged. Apply the registered pure delivery rule
to the normalized pair and write a separate saea-derived-delivery-v1 bundle.

Bind both source records, actual caps, saturation flags, normalized text
hashes, rule declaration, implementation sources and delivered text hash.
A nonterminal wire-response hash can be shape-checked and bound to the
verified trace record, but cannot be recomputed when the parent lacks raw
transport bytes. Do not describe that narrower evidence as raw-wire capture.

Reverification replays the same rule from verified source bytes and compares
the complete derivative. Charge parent generation once; the derivative has
zero additional model contacts. Retain the existing full-manifest scoring
entry and identical-output score reuse. Never finalize the parent's attempt
through a derivative. Scorer aliases with the same callable share one
invocation while retaining their configured result keys.

## Verified scope and remaining work

The integration test uses configured phase templates and a pinned synthetic
knowledge snapshot, FlightRuntime's default phase material binding, the real
EvidenceAgentController/run_program/OpenJiuwen path, the real FrozenCoreClient
with a synthetic transport, and real bundle sealing/verification. Two samples
produce four simulated contacts. Each second request contains its own current
draft; delivered source selection is correct; parent manifest, outputs and
both trace artifacts remain byte-identical. Both socket connection paths are
forbidden.

This proves shared configuration and provenance wiring. It does not establish
model quality, runtime cache behavior or actual context capacity. The complete
live SLURP experiment still needs truthful staged request fitting and explicit
phase budgets; the existing single-phase fit correctly refuses to certify a
future prompt built from an invented predecessor. E21's live reviewer/planner
observation selection and timing semantics are separate unfinished work.
No scientific flight is released by this extension.


## Shared CLI and scoring custody

A phase parent is raw evidence, not the joined system answer. Its manifest
records required_phase_deliveries. FlightRuntime.seal automatically defers
its finalization and records delivery_required plus declared_delivery_cells;
it writes an immutable generation-manifest copy and no raw-parent score job.
Explicit seal(defer_scoring=True) also supports deferred ordinary controls.
FlightRuntime.score refuses a required-derivative parent before writing jobs.

The public flight command requires --seal-only or --dry-run for a selected
phase-delivery cell, before constructing a runtime. --seal-only forwards the
seal deferral and skips score. This flag does not grant a model contact or
replace WorkerExecutionPolicy, a root-issued generation lease, preparation,
capacity and budget receipts. Root still owns the only model service.

After a lawful completed generation, use the shared build-delivery command
with --parent-manifest, --experiment-path, --derivative-cell-id, --output-dir,
--repo-root and --data-root. Its implementation calls build_delivery_bundle;
it contains no delivery algorithm. The explicit repository must match the
imported checkout. Supply the resulting manifest to one complete score-batch
job with --include-per-sample and --max-workers 1. Use score, not finalize,
for the derived manifest. Build every predeclared delivery without selecting
among them after seeing results.

The central score_bundle guard rejects raw phase parents before any scorer
or reference check. If a writer removes the manifest marker, the guard also
reads the exact recorded study_commit experiment from Git and selects the
required derivatives by the same parent fragments. Editing the current config
does not change that evidence. An unavailable commit refuses. Legacy
programmatic configurations without a committed experiment blob retain their
old path; newly declared phase flights cannot use it because preflight and
manifest construction require the actual experiment fragment. These are
local-consistency checks, not authentication against an actor forging the
study commit and all source history.

Scoring a derivative does not finalize its parent attempt. Complete
multi-delivery score-receipt settlement remains a separate lifecycle task;
do not report this workflow as fully finalized or count repeated manual score
commands as independent experiments. One complete score job is the current
operational contract, not a new global idempotency guarantee.

## SLURP building blocks

The registered phase-direct-then-slots-v1 program reuses the shared
EvidenceAgentController and OpenJiuwen executor. The baseline fragments
slurp-phase-live-intent-slots-schema-v1 and
slurp-phase-live-direct-control-v1 use matching prepared-query geometry
(4 slots, 16,384 tokens per slot), direct material and knowledge snapshot.
The two-phase baseline appends each current direct response to its own slots
request and retains the inherited TRAIN schema examples. The control uses
the existing direct-only phase program. Neither fragment selects a new output
cap, scientific budget, roster or formal experiment.

The slurp-intent-slots-delivery-v1 registry factory returns a pure two-text
rule backed by the existing roster join implementation: direct response owns
scenario/action, slot response owns entities. Extra intent fields and parser
failures are counted in per-row derivative diagnostics. This shares the
historical parser and join semantics; no second answering model is introduced.

The real configured synthetic integration also checks automatic seal deferral,
raw-parent scoring refusal, marker removal with current-config deletion,
forged empty markers, and scoring of the full joined derivative roster through
one synthetic scorer callable registered under two aliases. The raw manifest,
outputs and both trace artifacts remain byte-identical after derivation and
scoring. These tests are not official SLURP measurements.
