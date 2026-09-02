# Evaluation definition — Audio2Tool executable-ground qualification 104 v1

## Unit and population

The unit is one frozen Audio2Tool speech query. The population is exactly the 104 receipt rows in
`A2T-GROUND-QUAL-104`, with whole query blocks and 13 rows per tier.

## Arms

- `M0_REGISTRY_DIRECT`: one original-speech call with the complete registry.
- `G1_FULL_EXECUTABLE_GROUND`: one original-speech call with the complete executable handbook.
- `G1_RESEND_STABILITY`: one repeat for the prospectively frozen two-per-tier ground subset.

## Metrics and gates

Use the unchanged official `a2t-toolcall` scorer for the two complete 104-row manifests. Report exact
count/rate, tool count/rate, slot micro precision/recall/F1, parse count/rate, empty calls, and the
complete per-tier table. Compute the paired exact delta by whole query group with the frozen grouped
90% percentile interval: 10,000 bootstrap replicates, seed 20260902, NumPy linear quantiles at 0.05
and 0.95. Each replicate samples frozen `query_block` identities with replacement, includes every
paired row in each sampled block, and computes the sample-weighted mean ground-minus-M0 exact
delta. Parse resends with the same exact parser and compare call multisets plus
exact-correct outcomes on the fixed 16 pairs.

Basic pass is conjunctive: parse at least 103, exact at least 94, tool at least 99, slot F1 at least
0.90, exact and tool gains over M0 each at least 15, strictly positive paired grouped-CI90 lower
bound, resend parse 16, resend semantic-call agreement at least 15, and resend exact-outcome
agreement at least 15. Target pass additionally requires exact at least 99.

## Scoring execution

Execute exactly M0, then ground, then the 16 resends through one unchanged service session and three
distinct attempt ids derived in a hashed pre-contact flight plan. A partial failure seals available
trace/accounting, aborts opened attempts, stops the service, and ends the mission without recontact;
recovery requires a prospective amendment.

Seal every model response before opening gold. Run two complete-manifest official single-process
finalizers through two outer workers. Never shard a manifest or average shard scores. Do not include
network jitter or retry behavior in the engineering gate.

For each resend, canonicalize the complete traced source payload except `request_id` as sorted ASCII
JSON and bind its SHA-256 plus source slot. The intended resend must match that hash before contact;
the actual traced resend must match it again after contact. After both official finalizers settle,
semantic agreement requires both outputs to parse and scorer-v1 exact multiset equality when the
source calls are passed as expected and the resend calls as predicted. Exact-outcome agreement
compares the finalized source exact boolean with unchanged item scoring of the resend. A parsed
empty call is `parsed=true` with zero calls; parse failures are a separate count.

## Leakage and scope

Runtime cannot read gold, labels, reference transcripts, expected calls, scores, prior task outputs,
future turns, protected unexposed data, or test annotations. No result-dependent handbook change,
candidate pruning, policy fit, threshold search, sample exclusion, or approximately-1,000 expansion
is allowed in this row.
