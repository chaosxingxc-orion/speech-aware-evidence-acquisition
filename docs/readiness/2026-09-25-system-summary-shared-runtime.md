# Complete-system summary through the shared runtime

## Scope and scientific unit

The owner requires optimization of the complete agentic system. Preserve the
ordered Perception, Solver, Reviewer, Planner, tool, revision and delivery
trajectory. Score the delivered task answer. A local correction counts as a
system benefit only if it survives later decisions and final delivery.

The new input route lets the frozen local model consume one complete recorded
episode per summary request through the existing controller, OpenJiuwen,
FlightRuntime, actual request fitting and artifact sealing. It adds no model
client, service manager, agent framework or automatic campaign. The candidate-recovery worker stays frozen. That recovery is now
execution-closed after a separate CUDA service failure; this development never
changed its code or service configuration.

This completes a model-facing input connection, not an executed summary stage
or a training-free RL improvement. No new research model or scorer contact has
occurred. The new prompt and preparation are not launch authorization.

## Configuration and preparation

Reuse baseline system-trajectory-summary-v1, which uses phase-direct-only-v1,
result_kind=artifact and no scorers. Supply the normal registered model,
dataset and experiment fragments, a v1 artifact-result binding for TRAIN
construction, a live-fit plan and the resident-service lease. Its sole phase
uses probes/system_trajectory_summary_v1.txt. The baseline also replaces the
adapter's original SLU-answer instruction with a literal summary instruction;
the SLURP adapter still appends its legal TRAIN ontology as background.

The prepared_training_feedback spec uses the distinct schema
saea-prepared-system-summary-v1. Its remaining fields are artifact,
source_bindings, language=en and max_context_bytes. Both pins use DATA-relative
relpath and exact file sha256. max_context_bytes is a refusal bound, never a
truncation rule or substitute for actual model capacity.

The source_bindings file is one object with exactly:

- schema: saea-system-summary-source-v1.
- round_id: the registered construction round.
- source_repo_root: the absolute retained clean checkout of the actor source.
- manifest and phases: DATA-relative relpath/sha256 pins for the sealed source.
- construction_roster: a DATA-relative relpath/sha256 pin to the exact same
  roster bytes bound by the artifact-result contract in the updater repository.

Use the model-free shared preparation entry point in WSL:

    python -B -m speech_aware_evidence_acquisition.rails.system_summary_context
      --data-root DATA
      --source-relpath REGISTERED_SOURCE_BINDING
      --source-sha256 REGISTERED_SOURCE_SHA256
      --output-relpath NEW_PREPARED_OUTPUT

Join these lines into one command and replace symbolic arguments with the
registered bindings; this is not an executable research registration. Set the
explicit source PYTHONPATH and use the existing WSL research environment.

Preparation and runtime reload both call verify_native_episode_source, retain
the recorded clean source checkout requirement, and require the complete
SLURP TRAIN construction cohort and split. A warm cache does not bypass this
verification. Shared core.preparation supplies locking, immutable publication,
input/implementation identity and cache validation.

A source verifier may read score-file bytes to validate the sealed bundle.
Neither those scores nor reference answers enter the summary context. The
summary does not interpret quality. Official terminal feedback is joined in a
later, separately declared stage.

## What reaches the model

Each ORG state contains one whole episode, not a selected successful role or
only the first Perception answer. The materializer preserves exact actor fields,
responses, tool events, raw interrupted responses where available, control and
delivery, with a lossless content pool. It retains failures and abstentions.
The upstream first-trajectory mapping is reused, then the same episode object
is presented without doubly escaped JSON strings.

The existing PreparedFeedbackStateArtifact and common serializer are reused.
The legacy source_feedback_sha256 field here binds the score-free complete
episode content; the custody receipt explicitly names this meaning. It is not
an official-reward hash. Summary output is raw scoreless artifact text, not an
admitted memory record. Typed proposals and consolidation must occur later.

One material input difference remains explicit: the shared artifact arm also
attaches the original sample speech and retains the adapter's task ontology. The prepared custody receipt names the
shared-speech-feature-artifact input contract, and the connected test verifies
speech_feature_parts in the actual request. The prompt asks for recorded
trajectory analysis, but this instruction does not make the request text-only.
Any real flight using this baseline must register the audio exposure and call
it a multimodal adaptation. For a strict text-only scholarly baseline, add and
verify a governed text-only shared route before registration. Do not silently
count extra listening as an algorithm gain.

## Next complete-system optimization cycle

1. Preserve the execution-closed incomplete comparison and diagnose the
   CUDA/host failure. There is no comparative effectiveness verdict and no
   automatic second recovery. Keep control quality unread under the existing
   registration; any later use requires its own source/read authority.
2. Define a small coordinated policy space over evidence organization/supply,
   role contexts and allowed review/revision actions. A component change is an
   implementation of a system action, not an independently qualified reward.
3. Record each decision state before choosing its action, available actions,
   actual sampling probability, and the complete subsequent trajectory.
   Do not condition the choice on gold coverage or a later role's answer.
4. Summarize complete trajectories, compare them with separately bound terminal
   TP/FP/FN, intent and format feedback, propose and consolidate experience,
   freeze the resulting policy/memory, and execute complete systems again.
   One round stays frozen until its entire feedback is sealed.
5. Compare against the locked default and strongest eligible fixed complete
   policy. Retain harmful paths, empty-target FP, failed tools, fallback and
   costs. Track whether repairs survived; this is path diagnosis, not automatic
   causal credit for a node. Require matched replication before stable gain.
6. Resolve the current disjoint TRAIN memory-use boundary before assigning
   multi-round construction samples. Do not bypass it for same-row replay.

No closed semantic-delta, VAR-2, F10 or evidence-path arm is reopened. Candidate
coverage and local role accuracy remain diagnostics. The full system is the
unit of optimization, sampling, return and advancement.

## Validation boundary

The connected synthetic test exercises the new source loader through the
actual FlightRuntime prepared-feedback binding, configured prompt material,
shared OpenJiuwen phase runner, exact fit/send payload identity, ORG tracing
and canonical raw artifact output. The source verifier and model transport are
substituted in that connection test; it is not a real sealed research flight.
The existing native-source suite separately exercises config/commit/phase
joins with real in-process native trajectories and a substituted bundle.

Other cases cover cold/warm preparation, complete TRAIN/source/roster binding,
source refusal despite cache presence, rehashed output substitution, context
size refusal without truncation, score/reference exclusion, the public
preparation entry point and unchanged legacy prepared-feedback behavior.

Validation results and exact logs are recorded in
docs/receipts/continuation/2026-09-25-system-summary-shared-runtime-validation.json.

Final WSL validation: 61 related tests, Ruff and all nine offline gates passed.
The initial handoff gate could not read Git metadata; its unchanged final rerun
passed. No gate was relaxed. Tests include 19 new preparation/connection cases.
