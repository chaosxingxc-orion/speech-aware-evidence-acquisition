# System evolution: evidence, active memory and escape from local search traps

Status: RESEARCH_AND_PROSPECTIVE_DESIGN_ONLY. Prepared 2026-10-06.
Do not use this document as actor, GPU, source-exposure or result-read admission.
Keep the reserved Update6 capsule, original response and historical acceptance rules unchanged.
The owner requests algorithm-focused follow-up informed by SkillOpt and related methods.

## Current implementation, not an aspirational label

The current frozen-core policy is the complete set of node texts and supported assembly
settings. A rollout executes that entire system. Reward-conditioned proposal generation
and measured acceptance constitute a text-policy optimization attempt. Archive growth
alone is not a policy update or evidence of learning gain. Eviction is neither necessary
nor sufficient for learning.

The partitioned trial implementation computes the sum of registered per-input utilities
for the complete before/after populations and returns a strict increase flag
(`rails/system_context_partitioned_trial.py:152`). Rejected-history preparation preserves
the active parents. Update5 changed utility from -56.15925390968045 to -69.32902959938615
and was rejected. Update3 and Update4 were also rejected; current active parents remain
Update2. Preserve these decisions rather than retrospectively selecting a new winner.

The shared learner contains add/delete/modify/keep experience operations
(`rails/system_context_learning.py:528`), but its original TF packet explicitly says an
experience runtime renderer is not implemented; behavior must be materialized as legal
role-text edits. The aggregate Update6 wire binds empty experience operations. Do not
describe this current path as an implemented adaptive experience-memory algorithm.
It uses deterministic distinct policies, not the original same-policy stochastic
Training-Free GRPO. No policy gradient, action likelihood or KL is available.

The original baseline seams and earlier executions remain separate. Do not rename the
current aggregate search as an exact GEPA or TF-GRPO reproduction. A prospective hybrid
requires its own algorithm identity and comparison registration.

## Primary-source findings checked on 2026-10-06

These are selected relevant public implementations, not an exhaustive survey of all
latest self-improvement methods. Read-only source snapshots and SHA256s are bound in
sources.json. No third-party optimizer was installed or executed.

| Reference | Verified mechanism | Applicable idea and fidelity limit |
| --- | --- | --- |
| [SkillOpt training loop](https://github.com/microsoft/SkillOpt/blob/32deaeb50f92fc2f3a225bbf67d3eb3a604ce8b6/skillopt/engine/trainer.py) | The trainer supports edit-budget selection, selection evaluation, rejected-edit/failure buffers and optional prior-epoch meta-skill context. Its gate can be disabled, so strict acceptance is a configuration choice rather than an unconditional property. | Bound semantic edit scope and learn from rejected changes. Retain full independent node templates; do not import a small universal token cap or mistake edit counts for gradients. Our repeatedly exposed N20 panel is not SkillOpt's held-out selection setup. |
| [Training-Free GRPO](https://arxiv.org/abs/2510.08191) and [experience updater](https://github.com/TencentCloudADP/youtu-agent/blob/c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d/utu/practice/experience_updater.py) | Group-relative semantic reflection updates external experience. The inspected updater applies ADD/UPDATE/DELETE plans. | A maintained experience state should influence subsequent policy construction. Preserve aggregate-only input here; do not restore expensive per-case semantic summaries or claim identical reproduction. Metadata deletion alone has no behavioral effect. |
| [GEPA candidate selectors](https://github.com/gepa-ai/gepa/blob/fb1ed589fd83372caef499cffc2c73173d3b096b/src/gepa/strategies/candidate_selector.py) | The implementation provides Pareto, current-best and epsilon-greedy selectors, with reproducible RNG support. Pareto selection delegates to a task-front mapping. | Select among complementary parents instead of one scalar winner. Original task-wise Pareto coverage differs from quality-cost non-dominance. Backend selection and actor evidence must have separately declared schemas and custody. |
| [ACE playbook utilities](https://github.com/ace-agent/ace/blob/82709de050e1db6e6ef2f07bcb0393560b94992a/playbook_utils.py) | The inspected utility updates helpful/harmful counters and applies ADD operations. UPDATE/MERGE/DELETE are listed as future operations in this function. | Borrow stable experience identities and incremental changes, but do not assume every operation described at project level is implemented in this path. Reflector tags are not experimentally identified causal effects. Do not import domain knowledge or raw cases into our learner. |
| [DGM outer loop](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/DGM_outer.py) and [paper](https://arxiv.org/abs/2505.22954) | The default archive mode keeps generated variants; parent-selection options include score and descendant-count weighting, allowing exploration from more than the latest best variant. | Preserve potentially useful historical starting points. Borrow bounded parent exploration only; arbitrary self-modifying code and unbounded search are outside this experiment's scope. |

SkillOpt-Sleep additionally documents offline consolidation with a validation gate and
separate optimizer-facing feedback. Treat it as an engineering reference, not a reason
to harvest conversations or replay task data. See its [official documentation](https://github.com/microsoft/SkillOpt/blob/32deaeb50f92fc2f3a225bbf67d3eb3a604ce8b6/docs/sleep/README.md).

No cited method guarantees escape from local optima on this task. No public benchmark
gain transfers to SLURP without our own complete-system evidence.

## Failure modes to distinguish before changing the algorithm

1. Proposal collapse: different words encode the same decision rule. Inspect declared
   mechanisms and observed aggregate behavior, not lexical distance alone.
2. Parent lock-in: repeated rejected whole populations retain the same parent set.
   A useful individual branch can be masked by regressions elsewhere.
3. Excessive local edits: a narrow neighborhood cannot express a joint Solver/Reviewer
   contract change. Conversely, uncontrolled rewrites can erase useful behavior.
4. Experience lock-in: one noisy N20 result becomes a universal prohibition or success rule.
5. Measurement ambiguity: unchanged requests can differ in observed outputs. Repeated
   failure does not establish a mathematical local optimum or identify its cause.
6. Optimization-set overfitting: exploring more templates on the same inputs can improve
   selection estimates without improving task capability beyond that pool.

The Astra prompt addresses mechanism-level proposal diversity. It does not implement
parent selection, experience retirement, acceptance reform or a proof of learning.

## Proposed state and update contract

Maintain three distinct objects in the existing archive rather than a second framework:

- Immutable evidence archive H: complete T*K aggregate candidate records, all originals,
  lineage, actual costs and private source custody. Never delete exposure or failed attempts.
- Bounded active search set P: eligible parent policy identities with measurement-domain
  keys, observed quality/reliability/cost, lineage and exploration-use counts.
- Versioned optimizer experience E: abstract template/assembly hypotheses, supporting and
  contradictory aggregate record IDs, applicability, current status and declared next test.

Keep exactly K experimental records per complete observed population and T*K historical
records in actor input as the owner requested. E is derived shared optimizer metadata,
not extra sample records or a substitute that silently drops historical records.
Bound E and P through config. Record their truncation/retirement decisions. Runtime
receives only the compiled chosen policy, not all history or an answer cache.

Use experience statuses hypothesis, provisionally-supported, contradicted and retired.
An untested sentence is a hypothesis. Do not auto-promote based on an LLM's confidence.
Retire a rule from active guidance only under a prospective evidence/conflict/capacity
rule; keep its original text and evidence in H. Repeated correlated observations on the
same N20 inputs do not count as independent replications.

The intended update is:
  complete qualified K-record feedback -> E update + P selection -> configured K proposals
  -> legal compilation and capacity/structural proof -> fresh complete-system evaluation
  -> root review -> next E/P version.
Every admitted proposal remains spent, including duplicates, invalid and no-change cases.

## Proposed exploration policy

Allocate the configured K proposal slots across local improvement, complementary-parent
recombination and a distinct-mechanism exploration path. Require a nonzero exploration
allocation when K permits it; define deterministic small-K fallback and rounding in config.
Do not hardcode K, proportions, patience, edit budgets, archive size or retirement limits.

Maintain separate search admission and formal adoption. A reliable but lower-scoring
historical system may receive a bounded exploration opportunity as a stepping stone; it
does not replace the formal incumbent. New combinations must still run complete native
trajectories and respect all interface and fixed-knowledge constraints.

Choose comparable non-dominated candidates using declared official quality, intent,
reliability and measured cost. Keep a separate bounded behavior-diversity exploration
set so that intermediate process statistics do not become an arbitrary weighted reward.
Do not merge scores from different batches/cohorts into one frontier. Historical parents
from different measurement domains need prospective common-roster evaluation before a
joint quality frontier; preserve the cost of that evaluation explicitly.

Use small/local and broader joint edits within the same finite proposal allocation.
A stagnation trigger may redistribute *future* registered slots or change eligible
parents. It never creates replacement proposals, raises temperature, extends budgets,
or retries failed work. Each larger edit still preserves all native output contracts.

## Diagnostics that can test the hypothesis

Business outcomes come first: official pooled SLU-F1, intent protection and reliable
completion. Report process detection, false alarms, eligible repair/damage counts,
knowledge visibility/support diagnostics and normalization burden with denominators,
missingness and intervals. A correct alarm on an erroneous sample alone does not prove
correct criticism; a visible knowledge item does not prove semantic use.

For search, report exact duplicate/no-change/invalid rate, parent concentration,
declared mechanism coverage, observed process-profile diversity, candidate acceptance,
incumbent progress and the proportion of explored branches with uncertain outcomes.
Behavior-profile distance is descriptive; unequal denominators or missing data must
not create artificial novelty. Improvement yield per actual evaluation/model-call
budget complements absolute gain. Unknown proposer tokens stay unknown.

Measure end-to-end sample latency, first-sample and remaining-sample means separately.
Latency is one process/cost dimension, never the sole proxy for learning or quality.
Do not calculate proposal efficiency from serving request totals.

## Prospective experimental sequence

1. Finish the already admitted Update6 proposal and its normal compilation/review path.
   Preserve its existing feedback, empty experience operations and acceptance rule.
2. Use complete qualified results to finalize one new selector/experience protocol.
   Keep the current aggregate method as a frozen baseline, and retain separately named
   original TF-GRPO/GEPA baselines with explicit aggregate adaptations where applicable.
3. Test an explicit small algorithm contrast at N20 with equal configured proposal and
   complete-system evaluation allocations. Start with one main mechanism change rather
   than simultaneously claiming gains from every imported feature. No required node
   component ablations or independent component-benefit prerequisites are introduced.
4. If claiming feedback-specific benefit, include a prospectively isolated no-feedback
   or feedback-ablation comparison. Equal candidate counts alone do not prove equal
   computation. Do not reuse this root chat as a blind proposer.
5. Compare incumbent quality, improvement yield and maintained behavioral diversity;
   include all spent failures and null updates. Optional experience/selector ablations
   should answer an unresolved algorithm question, not become routine GPU overhead.
6. Review progression inside the same fixed400 pool using the existing staged authority.
   Keep optimization exposure explicit; more template trials are not independent
   validation. Obtain human review before8x400 or an equivalent split campaign.

This document is an algorithm roadmap, not an admission of any new algorithm contact,
budget, candidate, dataset, model, carrier or GPU run. Shared runtime/adapter/provider/
controller, official scorer and Omni answer authority remain the execution foundation.


## Latest meta-optimizer references and implementation limits

Primary pages and source files were rechecked on 2026-10-06. This is a targeted
continuation of the existing survey, not an exhaustive latest-method ranking.
See meta-source-audit.json for the additional immutable source pins. No external
optimizer code was executed and no research model contact was made.

- [SePO paper](https://arxiv.org/abs/2606.04465), submitted 2026-06-03, optimizes the
  prompt-generating agent's own system prompt, then uses that evolved optimizer on
  target tasks. Its archive preserves possible stepping stones. The inspected
  [official repository](https://github.com/taowangcheng/SePO/tree/83083782a9487ef61962d933fc72abbe95f9fa76)
  contains README/assets and states that code release preparation is in progress.
  Treat its algorithm as a paper reference, not a runnable reproduced baseline.
- [HyperAgents paper](https://arxiv.org/abs/2603.19461), submitted 2026-03-19, makes
  both the task agent and its modification procedure editable. The inspected
  [parent selector](https://github.com/facebookresearch/HyperAgents/blob/59a68f672dfb92c74aeb7e61535d776fb36e172d/select_next_parent.py)
  filters eligible evaluated parents and computes score/child-count metadata, but
  actually returns uniform random.choice over eligible parents. Do not describe
  this implementation as score-weighted or descendant-count-weighted selection.
  Its executable code evolution exceeds our template-only scope; borrow only the
  distinction between optimizing task behavior and optimizing the proposal rule.
- [SkillOpt's current official overview](https://github.com/microsoft/SkillOpt)
  describes bounded edits, rejected-edit memory and held-out acceptance in the
  default paper-style path. Its 2026-07-02 v0.2.0 notes separate experimental
  controls from conservative CLI defaults. Keep our earlier pinned code audit;
  do not equate a project headline with a mandatory behavior of every code path.
- [GEPA's official overview](https://github.com/gepa-ai/gepa) supports broader text
  artifact optimization and diagnostic side information. Our aggregate-only
  representation is an explicit adaptation: it does not reproduce its default
  full-trajectory reflection or task-instance Pareto coverage.

Our inference: the Astra-authored diversity prompt is a candidate meta-policy,
not evidence that the meta-policy learned. Credit a meta-policy only after its
resulting candidate systems are evaluated under matched search/evaluation budgets.
Freeze the proposal rule during a search comparison. In a later registered
comparison, vary that rule while holding parent selection, model, data, feedback
representation and actual allowance accounting comparable. Include both the
meta-optimization cost and the cost of evaluating its generated task policies.
Do not approve a generator because its prose appears more diverse.

## Sequential algorithm questions and stagnation diagnostics

Keep the first prospective comparison focused on fixed-parent versus bounded
multi-parent search. Test revisable experience and meta-prompt evolution later if
this leaves an unresolved question. Do not silently change current configs or
old whole-population acceptance. These are research priorities, not extra runs.

Use three observable distinctions when progress stalls:

1. Proposal collapse: exact duplicates, no-change rate, parent concentration,
   declared mechanism coverage, and observed process-profile similarity.
2. Evaluation ambiguity: same-policy A/A variation, paired uncertainty, sample
   denominators, and unresolved runtime reproducibility. Weakly separated scores
   do not establish a local optimum.
3. Search stagnation: no qualified business improvement over a prospectively
   configured complete-round window, after accounting for uncertainty and cost.
   Respond by reallocating existing future slots to eligible historical parents,
   recombination or broader joint edits. Do not silently add contacts or slots.

Mechanism tags can include evidence-preserving Solver behavior, selective Reviewer
criticism, revision restraint, and explicit handoff ownership. These tags describe
hypotheses; aggregate behavior and complete-system scores test them. Lexical
novelty or higher alarm rates alone are not progress. A high-risk exploration
candidate can be a search parent under bounded rules without becoming deployed.

Retain the owner's exact K-record aggregate input per evaluated population and
all historical population records. A bounded active parent/experience state can
coexist with immutable history. Store corroborating and contradicting record IDs
for experience; retire guidance from active use without deleting evidence.
Do not expose concrete examples, task knowledge, source inventories, gold or raw
trajectories to the learner as a shortcut to reproducing another paper.

For every subsequent algorithm comparison, report official task quality and
intent/reliability first, detection/false-alarm/repair/damage statistics second,
then measured latency and total search cost. Separate best observed search score
from qualified adopted performance. Any repeated pool remains optimization data;
small-panel improvements and behavior diversity do not prove generalization or
escape from all local optima. A feedback-free control remains necessary for the
later feedback-specific learning claim; two feedback-aware selectors test search
strategy, not that claim.
