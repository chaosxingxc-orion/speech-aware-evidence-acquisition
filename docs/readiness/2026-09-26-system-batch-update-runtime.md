# Complete-system batch synthesis and provisional memory

## Status and scientific boundary

This is a model-free implementation checkpoint, not a launch registration.
It connects the final model-facing update stage of the pinned Training-Free
GRPO adaptation to the existing provisional memory materializer and native
agent runtime. No research model, tokenizer, tool or scorer contact occurred.
No real semantic updater, learned policy evaluation or stable RL benefit is
established. The candidate recovery remains execution-closed; preserve STOP,
the frozen generation worker and the isolated control quality-read embargo.

Read the [validation receipt](../receipts/continuation/2026-09-26-system-batch-update-validation.json)
for the exact tests, coverage scope, source substitutions and gate limitations.

## What changes

The earlier deterministic consolidator only applied already typed proposals.
That is useful infrastructure but insufficient for the pinned upstream batch
stage, which asks a model to synthesize a revision plan from all group operations
and the current experience pool. This continuation permits genuinely new model
wording, while retaining the common ExperienceRecord, atomic consolidator,
candidate source attestation and runtime memory tool.

The executable chain is now:

1. Reconstruct sealed full-system actor trajectories and official terminal counts.
2. Verify recorded summaries, comparisons and frozen-memory group operations.
3. Prepare one batch context containing every valid non-NONE group proposal and
   the entire frozen visible memory pool. Preserve unusable, tied and no-change
   groups in the separate full population report.
4. Use baseline system-batch-update-text-v1 through the existing direct-only
   controller, prepared-context-text arm, FlightRuntime and OpenJiuwen executor.
   Fit and send the same real request; retain the raw response as an artifact.
5. Parse model-authored ADD/UPDATE/DELETE with typed guidance. Assign source
   identities and provisional provenance on the host; apply all operations
   atomically against the bound frozen base.
6. Replay the resulting artifact through the existing source-attestation entry.
   A separate registered disjoint TRAIN evaluation may expose it through the
   existing corrective-memory tool. Provisional content is never automatically
   admitted or activated.

A synthetic connected test reaches actual shared runtime preflight, Reviewer
memory-tool dispatch, Solver revision and final delivery. Its answering transport
is simulated. It establishes a connection, not semantic usefulness or a valid
real sampling/update/reexecution round.

## Configuration and entry points

Use rails.system_batch_update_context for preparation. Its source file has
exactly these fields:

- schema: saea-system-batch-update-source-v1.
- group_update_manifest: DATA-relative relpath and SHA-256 of the sealed artifact.
- group_update_repo_root: absolute retained clean source checkout.
- batch_roster: pinned construction roster containing only the first original
  construction sample as a transport anchor; null is diagnostic-only.
- max_operations: prospective positive bound on the entire model revision plan.
- proposal_contract: applicability with allowed_task_ids, allowed_roles and
  allowed_component_tags; max_diagnosis_chars, max_guidance_chars,
  max_limitation_chars, max_limitations and max_option_refs.

The full construction roster comes from the verified upstream group report.
The transport anchor does not redefine that roster or erase exposure. A
nonempty batch is required for a model-contact roster. Empty or unusable-only
groups produce a no-change-no-operation diagnostic with zero new contacts.

The existing prepared_training_feedback field uses
saea-prepared-system-batch-update-v1 and pins artifact, source_bindings, language
and max_context_bytes. Preparation and runtime both rebuild the source binding.
The model sees group-1, group-2 and subsequent aliases; full trajectory hashes,
sample identities and count provenance remain in the offline source report.

Preparation CLI, in WSL with explicit checkout PYTHONPATH:

```sh
python -m speech_aware_evidence_acquisition.rails.system_batch_update_context \
  --data-root DATA --source-relpath SOURCE.json --source-sha256 SHA256 \
  --output-relpath PREPARED.json
```

Use the existing core.provisional_candidate_materialization entry for the sealed
model output. The distinct configuration schema is
saea-system-semantic-memory-materialization-v1. It has exactly schema,
materialization_id, max_candidates, batch_manifest (absolute path plus SHA-256)
and batch_repo_root. The manifest must remain under DATA. No handwritten plan
can replace its recorded response.

The shared candidate source-attestation entry replays this materializer.
Generation runtime reads compact attestation and typed guidance; it does not
reopen training outcomes. A configuration fragment alone is not exposure or
generation authority.

## System-level provenance and atomic behavior

Every group alias binds all paired complete actor trajectories, their actions,
delivered responses and official terminal outcome vectors. A new
complete-system-group source reference hashes that full binding. Its composite
trajectory/action/response/outcome fields explicitly represent ordered lists of
actor sources; none claims to be an individual winning trajectory or causal
component credit. The primary alias locates the composite source; supporting
and contradicting aliases express the model's proposed evidence relation.

The full construction roster is carried into every typed record and successor
snapshot, including samples with no selected guidance. A two-group test checks
that a single batch anchor and guidance primarily citing the second sample do
not shrink the scope to the anchor or selected sample.

ADD/UPDATE proposals use the shared typed guidance validator. They must stay
inside the configured task, role, component and structural-condition scope.
The model cannot set IDs, hashes, reward fields or admission status. It may
synthesize text across groups; text equality to a prior proposal is not required.
All supporting aliases must exist; the primary alias must support the proposal;
support and contradiction sets must be disjoint.

UPDATE creates an immutable successor revision with supersedes_record_id.
DELETE retires its target. Retired identities remain reserved; no sparse-ID
reuse or overwrite occurs. Unknown targets, repeated targets, invalid scope,
duplicate JSON keys and contradictory source roles are rejected. Empty
operations preserve the frozen snapshot without invented guidance.

Invalid or capped model responses are retained under
DATA/provisional/system-semantic-rejections with raw response and no candidate
snapshot. An over-cap resulting pool is rejected rather than truncated.
Proposal and final candidate artifacts use the existing immutable preparation
interface. Historical source records are not rewritten.

## Capacity and algorithm fidelity

All valid non-NONE group operations enter one batch context. No top-K filtering,
automatic splitting, context clipping or silent output-cap reduction is used.
The byte guard is only a preparation guard; the real shared request capacity
check and a prospectively registered output bound remain mandatory before
generation. Real group output sizes do not yet exist, so fitting the intended
full batch has not been demonstrated. If it does not fit, stop before generation
and register an explicit bounded or hierarchical adaptation; do not call that
change an unchanged upstream baseline.

The pinned upstream reference is youtu-agent commit
c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d,
utu/practice/experience_updater.py, SHA-256
301d4a51136f6c0da620f1f2042d59316af494cee4b4c3329338ba1a1b937d04.
The local source was re-read and its hash verified. It collects group operations,
calls the model for new content, applies the revision plan, and reassigns IDs.

Declared adaptations remain: complete-system terminal count feedback; eligibility
based on terminal outcome-vector differences; separate numeric feedback without
reference answers; typed source-bound conditional guidance; canonical roster
order; scoreless prepared-text stages; stable immutable identities; strict
atomic failure; and no automatic retry. The pinned upstream can retry malformed
batch responses and renumber experience IDs. This repository requires separately
registered contacts and preserves failure instead. These differences must be
reported alongside any future empirical comparison.

## Remaining work before a real learned-policy claim

- Bind each sampled actor's actual policy and memory version to the updater's
  frozen base. An input snapshot alone is not on-policy evidence.
- Define and enforce the multi-round disjoint TRAIN schedule and accumulated
  construction exposure. Do not permit silent provisional self-application.
- Register full sampling, feedback, semantic stages, frozen reexecution and
  matched comparison to locked default and strongest eligible fixed policy.
- Diagnose the GPU/host failure before new GPU authority. The closed candidate
  flight cannot be replayed as a second recovery.
- Run actual whole-system evaluation and replication before claiming benefit
  or expanding the main campaign to other carriers.

The learned object is a coordinated system's conditional procedural memory.
The outcome remains the final official task return, with intent, format and
harm accounting preserved. Node-level changes remain diagnostic until they
survive full delivery and replication.
