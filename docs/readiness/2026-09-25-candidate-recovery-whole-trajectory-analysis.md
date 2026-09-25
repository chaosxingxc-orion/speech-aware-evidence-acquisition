# Candidate recovery: whole-trajectory analysis and optimization unit

## Scope and live boundary

The owner requires system-level optimization. A candidate-coverage improvement,
a better Solver branch, or a favorable review score is not a system-policy gain.
The unit of observation is the complete executed trajectory, and the primary
comparison remains the pre-registered official terminal task score.

The registered control/expanded pair is running in the independent WSL queue.
Worker source stays frozen at 9f6a949f445e4fb308789eb0786a1a25c3fb8f69.
This change extends shared offline analysis only. It changes no request,
configuration, roster, budget, threshold, serving geometry or execution order.
No current arm answers, partial quality scores or new evaluation labels were read.

## Preserve the causal chain without overstating causality

The score-free system trajectory export now carries the source-bound candidate
proposal, selected example identities and target labels, original Perception
binding, and every downstream proposal-contact receipt. It reuses the runtime
custody validator to join the actual request evidence, response, and ORG record.
Phase and output records must agree. Legacy trajectories without this feature
retain their previous export fields and fingerprint.

The shared SLURP attribution entry joins this export to the sealed source and
the existing official terminal feedback. It reports:

- Whether the proposal was reached, merely prepared without a response, or
  supplied in a completed model contact. Preparation alone proves neither
  dispatch nor model use.
- Original versus proposed candidate coverage, including the full registered
  population and explicit unavailable rows. Added candidates never become a
  hard answer-space filter.
- Whether the first Solver, last Solver and delivered answer select an original
  candidate, an added candidate or a label outside the proposal. Unavailable
  Solver outputs and malformed responses remain distinct.
- Revision reach, retained task repairs, repairs lost at delivery, new task harms,
  terminal intent correctness and task exactness within coverage groups.
- Actual proposal-contact counts by role, per-scenario counts, and the existing
  whole-population natural/equal-scenario diagnostics, input volumes, tool
  events, finite outcomes and official pooled terminal verdict.

Coverage groups use offline gold and cannot become runtime policy states.
Example support counts are not calibrated confidence. Evidence present in a
request does not prove semantic use. A label selected from the added set does
not by itself show that expansion caused a repair. Within-trajectory changes
are descriptive; the matched complete-system comparison establishes whether
the registered fixed policy helps. Strict intermediate exactness does not
replace official word/character pooled SLU-F1.

## Subsequent training-free optimization

Use coordinated continuation policies as actions. A policy may jointly define
candidate/evidence supply, the information supplied to independent review,
Planner routing conditions and bounded revision behavior. Preserve the final
answer authority of Solver and the frozen core. Do not compose locally winning
components and assume their gains will add.

Sample complete continuations from comparable pre-action observable states.
Record state identity and timing, selected policy, its probability, all actual
role/tool contacts, intermediate transitions, terminal output and official
feedback. Include action-not-reached, abstention and finite-failure episodes;
exclude no failed trajectory merely because it lacks an intermediate score.

Update only after the construction round has completed and been scored.
Assign terminal system feedback to the sampled continuation. Intermediate
coverage, disagreement and repair statistics diagnose interaction failures;
they do not substitute for terminal reward or establish per-node causal credit.
Where policies interact, measure their joint complete continuation rather than
summing isolated node effects. A multi-step learner later requires actual
logged sequential choices and downstream returns; the first finite
continuation selector remains a contextual bandit.

Evaluate a frozen updated policy by executing the complete system again and
comparing it with both the locked system and the strongest eligible fixed
policy. A single episode-start state can at most learn a fixed choice; it
cannot establish adaptive selection benefit. No learned RL update or stable
learning gain has occurred in the current fixed-policy pair.

## Completion and next decision

After both full manifests and their single official scoring jobs seal, bind
the exact sources and use the shared feedback and trajectory entry points.
Apply the existing primary gate and intent protection before interpreting
subgroups. A promising fixed policy requires matched replication; a local
coverage gain with no terminal benefit is not a promotion.

The present implementation does not authorize another flight, reopen a closed
line, admit a policy-learning action, or change the purpose of DEV6570/test13078.
No new owner decision is required to finish the current registered pair.

## Verification

82 related tests and all nine repository offline gates pass in WSL. Tests
exercise the real shared graph with deterministic synthetic model responses,
all four role truncations, missing/changed proposal custody, lost repairs,
outside-candidate answers, malformed responses and complete population
retention. The legacy no-proposal trajectory fingerprint remains pinned and
unchanged. The offline entry rejects feedback with a different proposal or
receipt hash. No research model or official scorer was invoked by these tests.

See docs/receipts/continuation/2026-09-25-candidate-recovery-whole-trajectory-analysis.json.
