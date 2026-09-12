# System optimization lifecycle: source-backed readiness audit

Date: September 12, 2026. Base: a00c34cb3d373a054158d25a2359c3708588bc79.
Scope: static source review only. No new model, scoring, reference-content read,
upstream execution, or active-runtime change. This note refines the earlier
2026 source audit; it does not register an optimization experiment.

## What the existing base already supports

Reuse the shared controller, phase programs, tool registries, flight runtime and
OpenJiuwen executor. The phase-tool bridge supports both fixed actions and a
bounded core-choice route with an allowed tool set and bound query state.
Do not describe the entire framework as a binary continue/stop controller merely
because the present phase Planner rule returns a boolean.

Immutable ExperienceSource, ValidationBinding and ExperienceRecord objects,
TRAIN-bound catalog admission, pinned runtime loading and source lineage already
exist. The runner retains complete states, transitions, actions and final response
identities. These are usable building blocks, not evidence of a complete
reward-driven update and evaluation loop.

## Semantics that must be preserved

- JudgeVerdict.score equals 1 for nothing to criticise. JudgeFlag supplies severity,
  location and reason, but no problem-confidence field. Severity and 1-score are
  not calibrated probabilities that an answer is wrong. The owner's requested
  trigger needs explicit problem-evidence semantics and a matched evaluation.
- Current corrective-memory applicability projects only six structural tags:
  prior response, knowledge and tool result, each present or absent. Semantic
  conflicts, confidence and reward-ranked selection are not implemented by merely
  declaring arbitrary tags in configuration. Add an outcome-free observable
  projection only when a named experiment requires it.
- The existing construction proposer requires gold-bearing targets. Do not reuse
  that payload unchanged for corrective-memory proposals. Use a narrow shared
  variant with legal trajectories and scalar/count feedback, with the same frozen
  core acting in a separately registered non-answering role.
- The corrective-memory tool manifest declares ORG, while the phase-tool event
  bridge emits USE for every non-speech tool. Its wrapper does not emit a separate
  axis event. Preserve both the event axis and tool-manifest identity in future
  offline credit assignment. Do not infer component contribution from the event
  prefix alone or silently rewrite historical traces. Resolve the distinction
  between memory organization and guidance consumption before using this credit.

## Minimum missing lifecycle

1. Bind each finalized TRAIN trajectory to its first complete official score.
   Preserve sample/partition, ordered actions, final response, scorer receipt,
   native score vector and frozen reward-rule identity in one immutable reward
   link. Verify the links before mapping them into ExperienceSource hashes.
2. Propose corrections from an allowlisted, gold-free projection. Store provisional
   and rejected records outside the admitted runtime catalog.
3. Evaluate candidate versions on a predeclared disjoint selection cohort.
   Selection use is optimization, not independent final evaluation.
4. Apply a frozen admission rule and emit ValidationBinding. Freeze the resulting
   immutable memory/policy version before evaluation; do not update within it.
5. Preserve version/supersession history and complete saves, harms and strata.
   Only validated reusable corrections become memory; raw TRAIN examples remain
   source data or task knowledge, not automatically experience.

The principal new interfaces are a canonical reward-link verifier, the legal
proposal projection and the update/admission driver. Do not build a second
execution framework. Runtime confidence and richer applicability are separate
component work, not prerequisites for the first fixed speech-evidence pair.

## Native rewards

SLURP pooled micro F1 uses aggregate word/character TP, FP and FN; row-mean F1 is
a different objective. Retain the native count vector through optimization.
Audio2Tool uses its registered official exact-match and parameter metrics.
E21 uses native WER and PERSON quality, with insertions reported separately under
the owner's prospective priority. No latency or monetary penalty enters reward.

A possible optimization-only decomposition illustrates the distinction. Let a
complete parent cohort have N0=2*TP0, D0=2*TP0+FP0+FN0 and F0=N0/D0.
For a candidate cohort define each row's utility u_i=delta_N_i-F0*delta_D_i.
When D0 and D1 are positive, F1-F0=sum(u_i)/D1 exactly. Handle the scorer's
zero-denominator convention explicitly. Per-row normalization can change these
weights; always validate the complete frozen policy with native aggregate F1.
This derivation is not an implemented reward or an admitted rollout. Never
oracle-select the best evaluated candidate per row and report it as one policy.

## Upstream qualifications

TF-GRPO snapshot 7612f860a2314c015573adc742f82157b0d66a6f has grouped external-reward
rollouts and does not need logits. Ground-truth reflection is enabled by default,
but the CLI explicitly converts the string False to false. Disable that route and
adapt the lifecycle instead of claiming an unchanged reproduction. Its updater
applies experience edits without our disjoint admission gate.

SkillOpt snapshot 79124b37e9a6371e13b753f8bcd7adb1e493ade1 has separate optimizer and
target roles that can share one model/backend. Normal selection gating is enabled.
Slow updates are optional and disabled by default; if enabled without selection
gating, the inspected route force-injects guidance. This qualifies the earlier
audit's wording: the ungated route is not always active. The saved snapshot omits
reflection adapter internals, so reference exposure there is unknown, not proven.

Keep adapted TF-GRPO as the engineering baseline. Treat the audited 2026 methods
as later alternatives after useful system actions are established. Static review
of seven methods is complete; their task reproduction and our optimization loop
are not. The current Audio2Tool flight and next fixed SLURP speech-evidence pair
remain the immediate execution priority.

Source bindings: 2026-09-12-system-optimization-lifecycle-audit-v1.json.
