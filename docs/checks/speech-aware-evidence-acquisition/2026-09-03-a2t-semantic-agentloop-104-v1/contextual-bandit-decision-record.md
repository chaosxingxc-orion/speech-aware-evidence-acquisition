# Deferred contextual-bandit decision record

Date: 2026-09-03

## Decision

Do not fit or deploy a contextual-bandit policy in this discovery analysis.
The future 104-row semantic AgentLoop flight may only produce the sealed,
post-seal evidence needed to decide whether a separately preregistered policy
study is warranted.

## Required later controller boundary

If an owner authorizes a later policy study, use the pinned upstream
`vowpalwabbit==9.11.2` `cb_explore_adf` controller. Do not substitute a
repository-owned learner. The later record must bind the context hash, action
set hash, selected action, logged propensity, observed reward, trajectory hash,
split identity hash, controller version, and policy configuration before any
fit.

## Gate interpretation

The current report must show complete manifests, verified whole-manifest
scores, matched-versus-M0 Agent gain, matched-versus-shuffled causal evidence
gain, and retrieval/action-set ceilings. It must not turn network jitter,
retries, repair, resend, or transport timing into a scientific result.

Passing this discovery review opens only a new owner-approved preregistration;
it does not authorize training-free reinforcement learning, confirmation,
approximately-100 or approximately-1,000 campaigns, Stage-3 work, or paper
claims. A score greater than 0.90 is not a baseline admission gate and belongs
only to a later post-training-free-RL decision if separately authorized.
