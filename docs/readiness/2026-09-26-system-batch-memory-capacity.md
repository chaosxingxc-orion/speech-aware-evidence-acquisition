# Explicit memory capacity for whole-system semantic updates

## Problem and implemented contract

The previous batch prompt exposed the operation count and individual content
limits, but not the final candidate count enforced by the materializer.
A valid-looking response could therefore exceed an undisclosed pool limit.
This is an execution defect, not evidence against training-free learning.

The new source schema, saea-system-batch-update-source-v2, adds the required
max_memory_records integer from 1 through the existing runtime maximum of 32.
The complete value appears in both the prepared document and model context.
Use the thin baseline system-batch-update-bounded-text-v1, whose prompt explains
the count and permits explicit evidence-preserving synthesis and consolidation.

The final count includes unchanged records. ADD increases it by one, DELETE
decreases it by one, and UPDATE is count-neutral. Validation considers the
whole atomic plan; a legal ADD followed by DELETE is not rejected merely for
an intermediate overflow. Existing records remain visible even if a smaller
prospective bound requires the model to explicitly consolidate them.
No-operation preparation is rejected if an unchanged pool exceeds the bound.

Before publishing any proposal or successor, the shared materializer requires
its max_candidates to equal the model-visible max_memory_records. It validates
the final operation count before synthesizing records. An inconsistent cap or
overflow retains the raw response and an immutable rejection with no candidate
or proposal output. It does not retry, drop rules, select a convenient subset,
or replace the output with a hand-authored summary.

The source-bound proposal artifact records the visible cap. Existing source
attestation replays the same preparation and materialization; the full ordered
pool then reaches the existing Reviewer memory tool and complete downstream
system path. Applicability filtering still applies at runtime. Availability is
not proof that the model used a rule or that it helped the terminal answer.

Legacy v1 remains a distinct contract. It gains no new model-facing fields or
prompt changes, and its old post-consolidation cap behavior remains intact.
Preparation fingerprints include implementation bytes, so unchanged legacy
request semantics do not promise identical new cache-envelope hashes.
Do not rebuild or overwrite any historical prepared artifact.

## What this solves and what it does not

This change supplies an explicit system-policy constraint to the learning
model. It keeps all eligible groups in the input and lets the model express
how to consolidate its proposed experience. It does not establish an optimal
pool size, an optimal guidance length, or an RL benefit.

The numeric pool bound is not a token-fit receipt. Real shared-service checks
must cover each actual semantic request and the full frozen memory supplied to
the actor roles. Retain fixed output allowances and all source groups. If the
request does not fit, stop; do not silently prune data or memory.

The baseline uses the existing prepared-context-text arm, controller,
FlightRuntime, OpenJiuwen executor, preparation machinery, atomic consolidator
and source-attested runtime memory. No alternative experiment framework,
service, scorer or answering model is introduced.

## Upstream batch cadence audit

The pinned TF-GRPO trainer at
c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d alternates rollout and experience update
inside each training batch. Its loop uses floor division and warns that a
remainder is dropped. The proposed tail-preserving schedule here is therefore
an explicit adaptation. This was checked against local pinned source bytes,
not inferred from a paper summary.

Read the [cadence audit](../receipts/continuation/2026-09-26-system-training-cadence-audit-v1.json)
for source hashes and verified roster counts. R01C625, A1080 and B1080 each
have exactly one recording per utterance. The two construction cohorts remain
the existing exposed TRAIN data; B retains its frozen evaluation role in the
prospective algorithm comparison.

| Construction cadence | Complete actor episodes | Update opportunities | Complete actor scoring jobs |
| --- | ---: | ---: | ---: |
| Existing whole-cohort draft | 6820 | 2 | 8 |
| Proposed batches of at most 32 | 6820 | 54 | 216 |

The second option has 20 R01C batches and 34 A batches, keeping the 17-input
and 24-input tails. Opportunities are ceilings: tied or unusable groups may
produce no update, and accepted updates are not guaranteed. Its conservative
semantic generation ceiling is 10284 rather than 10232, before separately
registered fit/smoke calls. Both options retain all construction identities.

With minibatches, the four replicas of a batch share one frozen policy and
memory; only sealed complete trajectories and their official terminal scores
can update memory for the next batch. Each batch is its own declared training
manifest, scored once, not a partial score for one larger evaluation manifest.
Do not present minibatch quality as an effectiveness claim. Full B evaluation,
the default/empty-tool controls and matched replication remain necessary.

M1 would mean the memory checkpoint after R01C, not one update; M2 would mean
after R01C and A, not two updates. Their source exposure must accumulate every
earlier construction batch. Subsequent actor inputs must remain disjoint from
all earlier experience sources. No held full-cohort experiment cell can be
silently reused with a different roster or memory. The initial tool-free actor
and subsequent memory-aware actors need an explicit registered transition;
an empty initial memory must never borrow a future M2 source.

The cadence choice is pending; this document does not change the held
whole-cohort configurations or authorize a minibatch flight. A 32-input batch
is a proposed hyperparameter, not an upstream default or demonstrated optimum.
Freeze concrete ordering, batch rosters, policy identities, source construction,
stage output limits and budgets before any research contact. Do not choose
batches or omit remainders based on observed outcomes.

## Validation and remaining admission

The [validation receipt](../receipts/continuation/2026-09-26-system-batch-capacity-validation-v1.json)
records tests, coverage, proof boundaries and all gate results. Synthetic
source/scorer readers and answering transport are explicitly substituted.
The connected proof covers shared input preparation, actual fit/send equality,
typed synthesis, source attestation, Reviewer tool use and Solver revision.
It does not measure real-model adherence, capacity or task quality.

Next resolve the cadence choice, freeze executable source/config/plan bindings
and complete service-fit admission. The closed candidate recovery is not
reopened. Its isolated control quality remains unread. The CUDA/host fault,
missing current dump copy, STOP and frozen generation worker remain as recorded
in the current handoff. No new GPU, tokenizer, encoder or official scorer
contact was made by this implementation or cadence audit.
