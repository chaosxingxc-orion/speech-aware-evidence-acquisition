# Bounded search parent selector: offline experimental interface

Status: MODEL_FREE_PROTOTYPE_ONLY. Not registered for any current actor or GPU run.
The active Update6 trial and strict-population-utility-sum acceptance are unchanged.
This helper is not an exact GEPA/TF-GRPO implementation, formal adoption gate or
complete new learning algorithm. Source qualification remains an external prerequisite.

## Implemented behavior

Reuse system_search_measurement.measured_frontier and SystemSearchArchive. Accept
aggregate measured rows only, rejecting unknown/raw-content fields. Require unique
policy/candidate identities, one cohort/measurement domain and one measurement profile.
Apply the existing reliability floor even when a row claims eligibility. Do not pool
historical cohorts into a global frontier or silently merge replicate identities.

Read capacities, selection seed and iteration from an explicit versioned configuration;
no population K is hardcoded. Retain one frontier anchor ordered by official SLU-F1,
intent, reliability, then measured mean/non-first latency and deterministic hash tie.
Select additional frontier parents by least prior use and seeded hash tie. The full
non-dominated list is preserved even when its active subset is capacity-limited.

Select a separate bounded exploration set from eligible unselected policies. Prioritize
dominated policies as experimental stepping stones, then unused frontier members;
rotate each group by least use. Never repeat a policy across active/exploration sets.
Record unfilled capacity explicitly instead of fabricating parents or proposal slots.
This is a declared exploration heuristic, not measured semantic/behavioral novelty.
It does not guarantee escape from local optima or improve SLURP by construction.

Return every input policy's disposition and updated search-use counts. Preserve all
historical records and source feedback identity. The optional archive wrapper writes
one immutable iteration record through the existing create-only archive and refuses
replacement. It does not change formal incumbents, active runtime policies, prior
acceptance decisions, proposal allocations, learner exports or model sampling.

## Integration boundary and remaining work

The API is currently uncalled by registered algorithms. A prospective algorithm
registration must bind the selector configuration into the same immutable experiment
configuration contract used for the full sequence; verify complete qualified source
custody; declare replicate handling and the eligible parent set; and produce exact
proposal allocations. This module does not authorize any of those steps.

The policy archive retains T*K history; an active-set subset does not discard learner
records or cumulative exposure. Optimizer experience updates and local/recombination/
exploration proposal scheduling are separate remaining work. Keep the existing
aggregate algorithm baseline frozen and compare the selector under matched proposal
and evaluation allocations, with explicit repeatability uncertainty. Do not claim
learning gain from the tests or run the new selector on partial current-family feedback.

## Verification

Tests were written first and initially failed on the absent module. The raw-content
refusal test then exposed a permissive schema and was fixed before completion.
62 relevant unit/integration tests pass, including the existing measured-feedback
adapter, balanced non-extreme frontier members, ties, deterministic order/usage,
capacity edge cases, reliability, mixed domains, invalid numeric/config values,
create-only archive roundtrip and refusal to rewrite. New module statement coverage
is66/66 (100percent). Engineering-base check passes. These are synthetic/model-free
proofs, not end-to-end GPU learning results. Existing remaining-b2 READ source pins
were reverified unchanged after the addition.
