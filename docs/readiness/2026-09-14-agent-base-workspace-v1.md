# Agent base acceptance and observable workspace

Date: 2026-09-14.
Status: engineering acceptance plan; algorithm design remains deferred.
Authority: the latest owner instruction, recorded in
[the base-first plan](2026-09-14-stable-agent-base-first-v1.md).

## Acceptance before algorithm design

Establish complete agent behavior, reproducible native task benefit and observable
room for improvement. Require all three before calling the base ready for later
training-free optimization.

Use the existing Perception, Solver, Reviewer and Planner graph through the shared
controller and OpenJiuwen executor. Keep direct inference on that same harness.
Keep intent-boundary knowledge separate from slot-contract knowledge. Keep local
speech tools callable during an episode, with Solver retaining answer authority.

The released max512 dual-store base has one favorable exploratory pair:
NEW500 pooled official SLU micro F1 increased from 36.1437 to 50.4479, with a
paired speaker-cluster difference interval of [11.2445, 17.5009] percentage
points. This is not yet same-setting reproducibility. The fresh DEV1000 paired
replication is prepared and independently reviewed but held for root admission
at the active flight boundary. Preserve its original quality rule and full
roster; do not average an unfavorable replication away.

The active bounded-evidence TRAIN recovery is a different system. It adds
capabilities, but the older base's benefit does not establish their benefit.
Finish or close the recovery under its existing contract, then use its complete
released source and sole official score to select the next engineering step.
Do not read partial quality or admit another recovery after its second failure.

## Implemented behaviors and information flow

| Node or boundary | Useful base | Active enhanced recovery | Evidence needed after complete release |
| --- | --- | --- | --- |
| Perception | Consume up to eight speech-retrieved intent-boundary values; form one to three actual intent hypotheses. | Support one bounded candidate refresh and explicit unresolved fields. | Initial and delivered-stage candidate coverage, missed labels, lost/recovered candidates and actual widths. |
| Solver | Consume candidate-associated explanatory slot values and jointly choose intent and entities. | Consume latest candidate additions after refresh while retaining prior visible evidence. | Correctness conditional on coverage, exact intent-plus-entities, slot errors and delivery-stage identity. |
| Reviewer | Access the task-contract tool. The original prompt instructs its use. | Choose among task-contract lookup, candidate-contract lookup and live speech observation; reserve a final tool-free report. | Actual calls, returned evidence, rejection/failure, subsequent review and full-task outcome. |
| Planner | Accept or request one bounded Solver revision. | Also request one candidate refresh before Solver revision. | Actual route, remaining bounds, accepted delivery versus exhaustion, and whether useful evidence preceded revision. |
| Tool propagation | Return tool output to the calling Reviewer and commit it into episode state. | Use the same path for all three tools. Later Planner, refreshed Perception and revised Solver consume committed states. | Source-bound request/result identity and later visibility. Visibility alone is not causal use. |
| Final delivery | Only an eligible Solver completion can answer. | A validated finite length/content-filter stop may retain an earlier Solver or produce an explicit abstention. | Include every sample, finite stop, retained answer and abstention. Preserve fatal source/integrity failures as failures. |

The active configuration grants tool authority to Reviewer only; Planner chooses
routes. The framework can scope analytical tools to Reviewer or Planner, but
that general capability must not be described as a Planner tool call observed
in this experiment. A declared ACQUIRE action is not an available configured
acquisition node; selective evidence currently enters through Reviewer tools.
Do not claim an extra action simply because its name appears in a schema.

Root verified the source paths for tool-call binding, state commitment, role
visibility, legal Planner actions, Solver-only delivery and finite completion.
The bounded independent inventory is retained at
DATA/coordination/slurp-dual-store-base-replication-v1/base-workspace-inventory-v1.md,
SHA-256 3426845cf97e76f0c3108f155c9ad261d79f5de144f8b140c64c64402af6fbdf.
It compares method source 6307a3ab30c93a6be35114deb5f701e6e444292f with active
recovery source f2c90cb2a4ab98713e319202f6f95a98765f1e76.
No unreleased task trace or partial score was read for this inventory.

## Use results to limit further engineering

Separate three SLURP problems: gold missing from the candidates; wrong selection
despite coverage; and wrong entities despite correct intent. Candidate coverage
of at least 95 percent remains a priority, not a gate that prevents other
whole-system improvements. Keep full-cohort quality as the selection criterion.

Do not require each tool to improve independently or add tools merely to widen
the menu. Add or revise a capability only when complete diagnostics identify
the missing evidence or failed information flow it can address. A useful
workspace records both improvements and regressions; it does not manufacture
causal credit from an observational trace.

Carry the stable shared graph to Audio2Tool and E21 with their own knowledge
organization and native scoring. Audio2Tool requires multi-action and argument
semantics; E21 requires window-to-call integration and ASR/entity semantics.
Neither transfer should inherit SLURP intent labels or a SLURP benefit claim.
Keep E22 and held-out Fold B under their existing access restrictions.

## Deferred algorithm boundary

No trajectory-sampling or reward-driven policy-update stage executes in either
configuration. Treat manual system changes as engineering. After a useful,
reproducible base is selected, define algorithm factors, sampling, the policy
space and its update rule from the behaviors and failure opportunities actually
observed here. Do not create those algorithm abstractions as prerequisites for
the present base validation.
