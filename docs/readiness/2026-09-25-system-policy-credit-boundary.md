# Whole-policy trajectory custody and candidate terminal credit

Status: offline source/feedback integration. No algorithm cell is activated.
This continues the complete-episode selector described in
2026-09-25-system-episode-policy-integration.md. The active fixed evidence-path
control/tools family remains on its unchanged frozen checkout.

## The scientific limit of the first comparator

The current selector has one episode-start state. Under a stationary task
distribution, a randomized mixture of fixed complete policies cannot have a
higher expected additive utility than the best member. Exploration can identify
a good fixed policy; it does not demonstrate per-input adaptation.

Do not present this comparator as the final system optimizer or as stable
training-free RL improvement over the best fixed policy. The broader research
goal still requires informative state available before the chosen action, or a
declared multistep policy/experience update, followed by complete system
reexecution and matched evaluation. Full terminal feedback is necessary but
does not itself make a single-state controller adaptive.

The useful distinction is between an actual complete-policy choice and a tool
action. A chosen policy receives the outcome of its whole episode, including
cases in which it never invokes its optional tool. That does not manufacture
an executed tool action or assign a terminal reward independently to every node.

## What is now checked

The shared trajectory exporter joins each new whole-policy decision across:

- The pre-role ORG trace record.
- The original initial query and speech packet.
- All realized request positions in the verified raw trace.
- The phase's native receipt and final delivered-output receipt.

Missing, duplicated, orphaned, late, altered or future-state choices are refused.
Decision records are indexed once per source. Historical sources acquire no new
fields or synthetic probabilities. Their exported hashes remain governed by
their original contents.

The record parser validates the exact schema and fingerprint. The same frozen
schedule/definition builder used at execution reconstructs the expected
allocation during feedback validation; it neither resamples nor emits a new
decision. Changed draws, probabilities, action definitions or schedule identity
cannot be relabeled as the original choice.

The complete official-feedback reader now retains these source-bound choices
beside the full terminal trajectory. It requires every row when the feature is
present. Official counts and labels stay out of actor context.

## Candidate update entry

analysis.system_policy_credit.candidate_update_from_source calls the existing
complete native/official source verifier before constructing TerminalFeedback
for the shared update_complete_round implementation. It joins all ordered
samples, decision fingerprints, terminal output hashes, official TP/FP/FN,
intent, format and fallback status. It preserves the original frozen F0 and
does not substitute per-row F1 or a binary success flag.

This is an offline update using decisions from the frozen collection policy.
It validates their declared allocation and uses the existing cumulative-mean
action-value rule. No importance-weighted off-policy estimator is claimed.

Evaluation-mode policy objects are rejected before any feedback read.
Historical allocation, incomplete rounds, nested optimized supply decisions,
source mismatches and repeated/conflicting trajectory credit are refused.
The input snapshot is immutable; recomputing a candidate from the same source
does not append credit to it. The output records its parent snapshot and exact
source hashes.

The returned receipt explicitly sets runtime_application_authorized to false.
The policy object still contains caller-supplied resolved bindings. This entry
does not prove that those action assets were admitted, that every selected
per-row configuration passed seal verification, or that a future flight is
registered. It must not be used to bypass those remaining steps.

## Validation and source boundary

Tests cover actual OpenJiuwen trace ordering using fake model transport, native
trajectory custody, complete official-feedback export, source-reader invocation,
candidate credit, evaluation refusal, empty-entity false positives, retained
finite fallback, and unchanged frozen snapshots. Counts used for the new credit
tests are explicitly synthetic; no research trajectory was retroactively
assigned a policy probability and no real policy update was produced.

The existing native source verifier still proves the current fixed system
sources. Before enabling selected per-row configurations, extend that authority
to the admitted action catalog. The candidate credit join does not replace it.

## Next work

1. Finish and interpret the complete evidence-path pair under its existing
   prospective rule; do not read partial outcomes or enlarge its queue.
2. Admit useful complete policy actions, with source-pinned configuration assets
   and explicit limits on which fields may differ.
3. Complete the shared FlightRuntime loader and per-row native seal validation
   for those assets, then register the first algorithm flight.
4. Use the one-state selector only as a best-fixed-policy learning comparator.
   Define contextual or multistep states at their real decision boundaries;
   Perception output cannot enter a pre-Perception choice.
5. Complete the scholarly baseline's declared update/reexecution mechanism on
   the same system space. This bandit code does not reproduce TF-GRPO, MemRL
   or GEPA by name.

The owner need not decide anything new for this bounded offline continuation.
Fresh DEV and test remain closed; no closed application line is reopened.

Validation receipt: docs/receipts/continuation/2026-09-25-system-policy-credit-engineering.json.
The focused suite passed 90 tests. After indexing trace decisions once per
source, the affected trajectory/feedback suite passed 39 tests (overlapping).
Engineering-base and Stage-3 algorithm-label gates passed. This work does not
resolve the previously recorded unrelated ROLL-AA fixture expectations and
does not claim a clean full-repository test suite.
