# Disjoint complete-system update rounds

## Status and purpose

This is an implementation and prospective scheduling checkpoint, not a launch
registration. It connects successive semantic-memory rounds without changing
the existing prohibition on provisional self-application. GPU execution remains
closed following the CUDA/host failure. No research generation, tokenizer or
official scorer contact occurred, and no RL benefit is established.

Read the [validation receipt](../receipts/continuation/2026-09-26-system-update-round-validation.json)
and [batch synthesis contract](2026-09-26-system-batch-update-runtime.md).
The new path uses the existing complete-system summary, comparison, group
update, batch synthesis, atomic consolidation and candidate-memory runtime.

The concrete incompatibility was that the older updater required its previous
memory to have the same construction roster as the current actor cohort,
while runtime correctly refused to evaluate that memory on its construction
samples. Rewriting the older records' provenance or allowing self-application
would hide this conflict. The explicit v2 path separates three scopes:

| Scope | Meaning |
| --- | --- |
| Sampled base | The frozen memory available to every actor in this round |
| Current actor cohort | The complete roster producing new system trajectories and terminal feedback |
| Cumulative exposure | The exact union of previous construction samples and this round's cohort |

## Configuration and verification

The existing group-update source schema remains supported unchanged.
Use `saea-system-group-update-source-v2` for a new disjoint-round source.
It retains comparison_manifest, comparison_repo_root, source_construction_roster,
update_roster, memory_id and base_memory, and adds two DATA-relative JSON pins:

- round_policy: relpath and SHA-256 of the exact actor membership contract.
- cumulative_construction_roster: relpath and SHA-256 of a SLURP TRAIN
  construction receipt covering the exact old/current union.

The round policy has exactly schema, round_id, actors and
base_memory_snapshot_sha256. Its schema is
`saea-system-update-round-policy-v1`. The actors list follows the comparison
source order. Each actor has label, run_id, attempt_id, config_hash, study_commit
and protocol_hash. At least two complete actor sources are required.
Initial base memory is null. Later rounds name the original frozen memory
snapshot, before the updater adds the current cohort to cumulative exposure.

Verification reopens the sealed summary-to-actor bindings and the existing
complete native source verifier. Actual run, attempt, config, source commit,
protocol, round and sample population must match the contract. Initial actors
must have no candidate memory. Later actors must reference the exact candidate
artifact and load the complete ordered frozen record pool through the existing
runtime memory reader. Another memory channel or episode policy selector is
refused because this contract does not establish its update credit.

The resulting round_policy_receipt records identities and available record
hashes outside the model context. It proves source correspondence and memory
availability. It does not prove semantic use, that a contract was registered
before contact, identical actor policies, an action probability, or on-policy RL.
The execution registration must prospectively pin this contract and the actual
sampling protocol. Merely producing a matching contract after execution cannot
establish prospective authority.

## Memory lineage and runtime behavior

A second or later round creates a
`saea-candidate-experience-snapshot-v2`. Its construction_scopes map retains
each earlier roster hash and sample list, this round's roster, and the cumulative
union. Old ExperienceRecord bytes, original construction hash and validation
binding are preserved. New synthesized records carry cumulative construction
provenance because their text can depend on both old memory and current feedback.

The pure exposure extension rejects overlapping cohorts, missing old samples,
unobserved added samples, duplicate IDs and a reused hash naming another set.
Its caller verifies pinned roster bytes and replays the previous candidate
materializer. A content hash by itself is not provenance authority.

Atomic ADD/UPDATE/DELETE continues to use the shared implementation. Deleting
guidance does not delete exposure or make its source samples available for
evaluation. All issued identities remain reserved. Runtime verifies the scoped
snapshot, exact flattened records and full cumulative population, then applies
the existing disjoint evaluation check to that entire population.

Initial v1 behavior and request semantics remain available. The preparation
implementation fingerprint changes with this code; prior immutable preparation
receipts are not rewritten or treated as current receipts.

## Evidence from existing TRAIN roster metadata

The read-only audit checked sample IDs and utterance IDs in four existing
roster receipts. No task outcomes, reference labels, DEV6570 or test13078 were
read. The exact file hashes and pairwise counts are in the validation receipt.

| Roster | Samples | Relation |
| --- | ---: | --- |
| R01 | 800 | Contains all R01C samples |
| R01C | 625 | Leaves only 175 R01 samples outside it |
| EVO Fold A v2 | 1080 | Disjoint from R01, R01C and Fold B by sample and utterance |
| EVO Fold B v2 | 1080 | Disjoint from R01, R01C and Fold A by sample and utterance |

The 175-sample remainder is below the repository's minimum for a paired
effectiveness claim. It is not a sufficient final evaluation cohort.
A feasible candidate schedule from existing lists is R01C625 for the first
construction round, Fold A1080 for the second, and Fold B1080 for frozen
regression. These lists are historically exposed; none becomes a fresh holdout.

This is a proposed schedule, not a roster-role change or permission to run.
Before admission, verify the selected knowledge stores' source exclusion,
prepared feature/query bindings and the chosen complete policy on all three
cohorts. Existing Fold A/B feature/config receipts are useful starting points,
not proof that the final configuration is ready. Create separate pinned
evaluation-role receipts rather than rewriting historical construction files.

## Algorithm protocol to finalize next

The learned object is conditional procedural memory affecting the complete
four-role system. Sample complete trajectories under a frozen round policy,
not several Solver answers sharing one downstream path. Use official terminal
feedback after delivery; retain failures, abstentions, unchanged answers,
repairs that survive, and repairs subsequently lost.

The proposed forward sequence is:

1. Freeze the qualified complete-system baseline, sampling settings, number of
   trajectories per sample, full contact bounds and prospective round contract.
   This is a distinct semantic-update experiment, not a restart of the closed
   candidate-expansion comparison.
2. Sample the first construction cohort with an empty memory. Score each
   complete manifest once. Run the registered summary, feedback comparison,
   group update and full batch synthesis chain to obtain frozen memory M1.
3. Sample the disjoint second cohort with M1 fixed for every actor. Keep M1
   unchanged throughout sampling and scoring. Update only after the complete
   round seals, yielding M2 with cumulative construction exposure.
4. Evaluate M1, M2, the locked default and the strongest eligible fixed complete
   policy on the same third cohort, with frozen policies and no updates from
   its answers. Register ordering and paired analysis in advance.
5. Replicate the qualifying comparison on that same evaluation roster before
   asserting stable gains. Retain official pooled SLU-F1, intent protection,
   natural/equal-stratum results, empty-target false positives, failures and
   full-system contact costs. Node metrics remain diagnostic.

Compare M2 versus M1 on the same third cohort; comparing round-one and round-two
construction scores mixes a policy change with a population change.
Same-roster replication measures execution stability, not fresh-data
generalization. A later independent claim requires separate authority.

The disjoint forward schedule is an explicit adaptation of the pinned
Training-Free GRPO implementation, not an unchanged repeated-cohort epoch
protocol. The verifier does not equate heterogeneous registered actors with
samples from one policy. Freeze and audit that distinction in the registration.
Keep the previously approved terminal feedback definition and its known
limitations explicit; this change does not introduce a new reward objective.

All group proposals and the full frozen pool must fit the real shared request.
The byte guard and synthetic tests do not prove actual capacity. If the batch
does not fit, stop and register a declared algorithm adaptation; do not silently
truncate, split the batch, lower the output limit or select convenient groups.
The CUDA/host failure must be diagnosed before new GPU admission.

## Test boundary

The tests exercise real exposure extension, immutable provenance, atomic
operations, sealed prepared-text reconstruction, semantic materialization,
source attestation and candidate runtime. A connected synthetic native run
reaches Reviewer memory-tool dispatch, Solver revision and final delivery.
A deletion regression then tries to evaluate a previously exposed sample and
confirms refusal even though the corresponding guidance has been deleted.

The synthetic actor source/scorer fixtures, prior source replay in the round
fixture, offline actor memory-loader return and answering transport are
substituted at documented boundaries. The later connected runtime uses the
production memory loader. These checks do not prove real model behavior,
real fitting or an executed multi-round training-free RL experiment.
