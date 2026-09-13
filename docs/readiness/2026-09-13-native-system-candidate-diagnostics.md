# Native system candidate diagnostics

Use the existing analysis.slurp_topn_diagnostics_cli after the root quality
read release. The primary comparison remains the complete direct-versus-system
score comparison. Diagnose Perception candidates only within the system arm;
the direct-only arm has no candidate source.

Select the native mode with
analysis.source_diagnostics.native_system_perception_source. Retain only
analysis.inputs.system in this diagnostic configuration. Bind its complete
manifest and complete saved-score receipt using the existing input fields.
The native source binding must carry the same manifest pin, an independently
pinned phase_artifact, the full split_identity_hash, candidate_count_range
[1, 3], producer_policy_id, compact_source_phase=perception,
candidate_selection_phase=solver and
projection_policy=bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1.
Retain the existing reference_source kind=slurp-split and explicit lock,
data_root, split_id and split_identity_hash binding. Use the same full roster,
primary roster and metadata as the frozen paired analysis.

The loader verifies the complete system bundle and score receipt before
diagnostic reads. It joins each Perception state from the independently
pinned phase artifact to the bundle's verified native-role event and raw
request/response records, including role, sample, instruction, contact and
response hashes and exact content. It uses the producer's exact candidate
contract provider as the legal ID authority and the shared bounded projection.

Report gold inclusion, observed distinct width and covered-but-not-selected
outcomes as descriptive partitions. Width is not confidence. Never pad the
source or filter the task-quality comparison. The native diagnostic's rescues
and harms compare final intent with its own Perception rank one; use
score_compare_cli for direct-versus-system saves and harms.

## Distinguish source projection from preserved supply audits

The current campaign serializes phase summaries and complete task artifacts,
but does not persist its in-memory FlightReceipts ledger. The phase file is
independently pinned after sealing, not falsely presented as a manifest-pinned
artifact. Trace joins establish the source state used for the candidate
projection.

When genuine preserved flight_receipts are absent, report actual_candidate_supply
as unavailable. This does not block source-derived candidate coverage or the
paired complete-task analysis. Do not invent a candidate-selection receipt or
label a newly reconstructed supply audit as producer-authored.

When a genuine preserved FlightReceipts file is supplied, verify its hashes,
seal-to-phase binding, exact candidate provider policy, legal inventory,
named-store receipt, candidate spec store ID and selection audit provenance.
This optional path proves more than source projection and is reported
separately.

Validation: 43 focused native and legacy Top-N diagnostic tests passed in WSL.
They cover source-derived projection, genuine optional supply receipts,
candidate width, trace/state/role/sample/hash mismatches, and named-store
binding disagreement. No model, scorer, test-quality or current-run result
was accessed in implementation and review.
