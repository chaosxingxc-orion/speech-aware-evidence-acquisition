# Whole-system terminal reward: objective audit and prospective comparator

Status: root-owned mathematical analysis using synthetic terminal count tables.
No current experiment answer, score, annotation or research trajectory was read.
The registered candidate-recovery pair and its verdict are unchanged.

## Finding 1: improvement over a reference does not imply correct policy ranking

For the existing construction feedback, let N=2TP and D=2TP+FP+FN. Then

u(F0) = N - F0 D = D (F - F0), for D > 0.

Positive aggregate utility proves pooled F1 above the frozen reference. It does
not order two improved policies solely by F1, because their denominators differ.
This is not a bug in the shared arithmetic and does not invalidate the existing
baseline. The limited ranking guarantee was already recorded; this audit makes
it concrete with an admissible equal-target-count example.

The following are synthetic complete-system totals. F0=0.60 is illustrative;
it is not the study's frozen baseline. Both policies have TP+FN=10 and identical
intent correctness.

| Complete policy | TP | FP | FN | Pooled F1 | Utility at 0.60 |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 5 | 0 | 5 | 66.6667% | 1.0 |
| B | 10 | 11 | 0 | 64.5161% | 1.4 |

Maximizing the frozen utility selects B, although A has higher terminal F1.
This proves a possible objective mismatch, not that a real learned policy has
already made this mistake. No research learning update has yet been executed.

## Finding 2: optimize population quality jointly across states

The same two actions can also show why maximizing each state's own F1 is
insufficient. Give the preceding state half the population weight. Give the
other half two possible terminal outcomes (TP,FP,FN)=(0,0,2) or (0,1,2).
Both actions have the same reference count within each state.

Choosing A in the first state and the lower-FP action in the second produces
pooled F1=10/17, about 58.82%. Choosing B in the first state instead produces
20/33, about 60.61%, despite B's lower local-state F1. The population numerator
and denominator couple the decisions. State occupancy must be fixed from
permitted pre-action observations, not retrospectively chosen from outcomes.

The optimization unit is a policy over complete continuations, with final
official counts. Intermediate node improvements and independently maximized
component metrics cannot supply this objective.

## Finding 3: standardized group advantages can erase important magnitude

A second synthetic example exercises the existing complete-rollout grouper
directly. Three inputs have reference counts 1,1,10. Complete policy A misses
the first two and correctly extracts all ten on the third. Complete policy B
correctly extracts the first two and misses all ten on the third. Intent and
format are identical.

| Complete policy | Pooled F1 | Summed raw utility at 0.60 | Mean within-input standardized advantage |
| --- | ---: | ---: | ---: |
| A | 90.91% | 6.8 | -1/3 |
| B | 28.57% | -4.4 | +1/3 |

A hypothetical rule that maximizes the mean standardized advantage chooses B.
The current grouping reader is diagnostic and preserves raw counts/utility;
it does not implement that policy rule. The pinned TF-GRPO updater uses semantic
comparisons, not this numeric averaging rule. Do not call this a demonstrated
upstream defect or a measured TF-GRPO loss.

For a future semantic update, retain full count changes, population weights and
counterevidence. A summary such as "wins on two of three inputs" discards the
system-level objective. Per-input normalization is not automatically an
aggregate-task objective.

## Candidate comparator: ratio-aware complete-policy improvement

A separately registered comparator could retain state/action estimates of
terminal TP,FP,FN, and optimize their pooled ratio. For fixed estimates and
state weights, iterate:

1. At reference q, choose a complete action in each state that maximizes
   expected 2TP - q(2TP+FP+FN).
2. Compute N and D for that complete population policy.
3. Set q=N/D and repeat until the maximum residual is zero.
4. Freeze the resulting policy before a new full-system evaluation.

This is an application of classical fractional programming, not a new
optimization theorem or a claimed novel RL algorithm.
[Primary reference: Dinkelbach, 1967](https://pubsonline.informs.org/doi/10.1287/mnsc.13.7.492).

The audit uses exact rational arithmetic and known synthetic counts. Across
192 generated finite state/action tables, it matches the exhaustive optimum in
each table (1696 candidate policies in total). This checks the mathematical implementation,
not finite-data learning, generalization or statistical power. The observed
mismatch frequency in those invented tables is not an estimate for SLURP.

Empty-target rows remain in population totals; false-positive counts affect
the objective. The fractional proof requires a positive pooled denominator
for every eligible policy. An all-empty population with a zero denominator
is explicitly rejected by this prototype, not treated as a convergence
certificate or perfect task performance.

## Requirements before any research algorithm flight

Keep the approved frozen-F0 cumulative-mean baseline intact. Do not change its
reward, historical utility, group advantages or acceptance threshold. A
ratio-aware rule must have a new declared algorithm/configuration identity.

The prospective same-space comparison must address the following:

- Use the same eligible complete-system actions, observed pre-action states,
  frozen model/service, roster and terminal official feedback. The ratio rule
  must not receive extra knowledge, tools or reference-answer context.
- Estimate count vectors from complete exploration trajectories and preserve
  sampling probabilities and action-not-reached outcomes. The exact-count
  synthetic optimizer does not solve noisy estimation or missing support.
- Account for changing state occupancy, sparse cells and adaptive allocation.
  Naive global fallback can mix different state distributions; selecting on
  noisy estimates can overfit. Do not claim an unbiased off-policy estimator
  or confidence guarantee that has not been implemented and registered.
- Preserve the original intent protection and failure reporting. The synthetic
  examples hold intent equal; no constrained intent-quality optimizer has
  been proven here.
- Freeze policy during a collection/evaluation round. Updating the numerical
  reference inside an offline optimizer is distinct from changing a live
  runtime policy or using validation outcomes for updates.
- Reexecute complete trajectories, compare with the strongest eligible fixed
  policy and the frozen-F0 learning baseline, and replicate before claiming
  stable benefit. A fit to construction counts alone is insufficient.
- For TF-GRPO-style semantic updates, retain the declared full summary,
  group comparison, experience consolidation and reexecution cycle. This
  numerical comparator does not replace that scholarly baseline.

This objective-specific design should not be transferred blindly to other
carriers. Metrics with an action-independent denominator, such as accuracy
on a fixed roster or WER on a fixed reference population, require a different
analysis of their reward and error decomposition.

## Reproduction and current scope

Run scripts/analysis/audit_system_ratio_objective.py with --output pointing to
a new file. It uses the shared official-count utility, pooled metric and
complete-system grouping helpers. It does not load datasets, invoke the
official scorer, call a model, register a flight or activate a runtime selector.

The result is /home/chao/system-ratio-objective-audit-v1.json with SHA-256
69eeade8a38226234383198578577f18cbf1c931e4869370190d3fead28e88ae.
Validation and source hashes are recorded in the companion continuation receipt.

Validation: 42 related tests and all nine offline repository checks passed in
WSL. Receipt: docs/receipts/continuation/2026-09-25-system-terminal-ratio-objective-audit.json.
