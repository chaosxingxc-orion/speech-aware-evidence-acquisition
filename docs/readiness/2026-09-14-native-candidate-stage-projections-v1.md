# Native TRAIN C0/C1 candidate-stage projections

Status: optional shared offline implementation with synthetic verification.
This document registers no source read, model contact, scorer invocation, GPU
use, experiment configuration, proposal input, optimizer choice, or scientific
decision.

## Opt-in contract

The existing `saea-native-train-stage-diagnostic-config-v1` configuration and
singleton Perception reader remain unchanged when `candidate_stage_projection`
is absent. A successor sidecar is selected only by this exact additional block:

```json
{
  "candidate_stage_projection": {
    "schema": "saea-native-candidate-stage-projection-config-v1",
    "policy_id": "first-perception-and-last-before-delivered-solver-v1",
    "candidate_projection_policy": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
  }
}
```

The successor output schema is
`saea-native-train-candidate-stage-diagnostics-v2`. It uses the existing native
source, reference, legal candidate inventory, reward-link, complete official
score, cohort, and preparation verifiers. It retains the derived document hash
in preparation inputs, so changed verified output cannot reuse stale bytes.

## Stage custody

C0 is the first actual Perception role visit. C1 is the last actual Perception
role visit before the Solver visit whose execution receipt is the delivered
final answer receipt. Without a refresh, C0 and C1 are the same verified stage
and `refresh_executed` is false. Candidate states are never unioned, inferred
from the final answer, or ordered by state ID or raw state-list position.

Each selected stage joins the ordered native role-visit receipt to its final
contact, serialized contact plan, query-state hash, sealed Perception state,
request and response trace records, and the bounded legal candidate parser.
Refreshed requests may retain prior request history, but their current control
envelope must be unique and last. The legacy singleton reader keeps its strict
one-row history validation.

The persisted stage custody contains visit index, state/contact/request IDs,
request, response, response-text, query-state, state, and candidate-set hashes,
and candidate width. Candidate IDs and reference intent strings stay internal
to the offline membership comparison and are not persisted.

## Numeric output

The sidecar reports initial and pre-final candidate coverage, recovered, lost,
stable-covered, and stable-uncovered membership, plus whole-roster final intent
accuracy. It reports conditional final accuracy for the C0-covered set, the
C1-covered set, and the common-covered set. Correct final answers outside C1
have their own ratio. Every ratio has an explicit numerator and denominator;
a zero denominator yields a null value rather than a conditional failure.

These are descriptive diagnostics for realized TRAIN trajectories. They do not
alter final-task reward vectors, assign causal credit to Reviewer or Solver,
construct counterfactuals, enter runtime or proposal model context, update a
policy, or authorize evaluation on another fold.

## Synthetic verification boundary

Tests exercise a refreshed native trajectory through the existing OpenJiuwen
episode harness with a fake transport, including exact C0/C1 selection and
missing, corrupt, or reordered custody. A zero-refresh trajectory proves C0 and
C1 identity. Additional synthetic tests cover covered-to-uncovered and
uncovered-to-covered transitions, stable cohorts, whole-roster and conditional
denominators, correct answers outside C1, absence of reference strings, the
opt-in preparation route, legacy preparation behavior, and warm-cache refusal
after a derived document changes. No real source, result, reference, scorer,
service, model, or GPU is contacted by these tests.
