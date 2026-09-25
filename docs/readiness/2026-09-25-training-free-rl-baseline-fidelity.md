# Training-free RL baseline fidelity and SLURP adaptation

Status: source-audited design, not an executed algorithm comparison.
Keep the current order: qualify actions, validate complete-system returns,
then sample, update and re-execute. Do not reopen the closed semantic-delta
application campaign through a renamed prompt experiment.

## Frozen external references

Read-only upstream code was downloaded outside the repository. Exact file
hashes are recorded in
docs/receipts/continuation/2026-09-25-training-free-upstream-source-pins.json.
No upstream code or package enters the study runtime in this step.

- MemRL: MemTensor/MemRL, commit
  c1b322ca43de36ddf64c6712f89d0095bfc35ce0 (2026-07-17).
- Training-Free GRPO: TencentCloudADP/youtu-agent, commit
  c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d (2026-03-21).
  This is the pinned implementation of the earlier method, not a claim that
  Training-Free GRPO originated in 2026.

## Findings from implementation, not just the abstract

MemRL's Q updater applies
Q <- (1-alpha) Q + alpha (reward + gamma max_next_Q).
The inspected config defaults to alpha=0.3 and gamma=0; a Q floor is optional.
It changes memory metadata and preserves the memory retrieval key.
[Source](https://github.com/MemTensor/MemRL/blob/c1b322ca43de36ddf64c6712f89d0095bfc35ce0/memrl/service/value_driven.py)

The inspected service exposes more than one retrieval path. Its local
retrieve_query ranks by a mixture of normalized similarity and Q, then uses
epsilon-greedy selection; the LifelongAgentBench runner calls that path.
Do not label every code path a faithful implementation of the paper's
two-stage retrieval description. Its batch update_values maps truthy
success values to success_reward, otherwise failure_reward, and assigns
that outcome to every retrieved memory in the trajectory.
[Service](https://github.com/MemTensor/MemRL/blob/c1b322ca43de36ddf64c6712f89d0095bfc35ce0/memrl/service/memory_service.py),
[runner](https://github.com/MemTensor/MemRL/blob/c1b322ca43de36ddf64c6712f89d0095bfc35ce0/memrl/run/llb_rl_runner.py)

Training-Free GRPO iterates rollout batches, experience updates and scheduled
evaluation. Its experience updater summarizes trajectories, derives semantic
group advantages, then consolidates experience updates. A single reflection
or a manually edited prompt does not reproduce that loop.
[Loop](https://github.com/TencentCloudADP/youtu-agent/blob/c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d/utu/practice/training_free_grpo.py),
[updater](https://github.com/TencentCloudADP/youtu-agent/blob/c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d/utu/practice/experience_updater.py)

## Consequences for this study

These are root inferences from the inspected implementations and SLURP results.

1. Do not feed a fractional SLU score or signed utility to a success-boolean
   update API: almost every nonzero number, including a negative number,
   is truthy. Preserve the declared continuous feedback and record that
   adaptation; keep intent correctness as a separate protected outcome.
2. Crediting every retrieved memory with the same terminal outcome does not
   identify which evidence helped. VAR-2 supplies matched-prefix action
   evidence, but its side branches still lack independent downstream
   Reviewer/Planner trajectories. Only complete-system trials can supply
   the return for a deployed action-selection policy.
3. Memory values should represent supported conditional action experience
   (state, action, outcome, count, provenance), not a copy of the training
   corpus. Knowledge continues to hold released task semantics and examples.
4. Keep runtime selection independent of online external APIs. Use frozen,
   already-prepared speech representations and observed pre-action state;
   update external values only from complete construction rounds.
5. A fixed-action search can improve the system without demonstrating an RL
   benefit. Compare the frozen learned selector with both the locked default
   and the best eligible fixed action under matched evaluation conditions.

## Baseline ladder and labels

| Baseline | Updated object | Required cycle | Scientific label |
| --- | --- | --- | --- |
| Locked system | Nothing | Repeated complete evaluation | System comparator |
| Best fixed eligible action | One construction configuration | Complete fixed-action validation | Configuration-search comparator |
| First finite policy | State-action cumulative mean values | Balanced round, score, update, 80/20 round, score, freeze | Contextual bandit with complete-system return; MemRL-inspired adaptation |
| Faithful MemRL-style memory policy | Per-memory values plus pinned retrieval/credit rule | Sample, attribute, update, retrieve again, frozen evaluation | Adapted MemRL baseline, with every deviation enumerated |
| Training-Free GRPO comparator | Bounded experience/policy context | Grouped sampling, feedback, semantic update, re-execution | Adapted TF-GRPO only when the full loop is actually executed |

The approved first finite policy deliberately uses cumulative means instead of
the upstream fixed alpha. It is not full MemRL replication and cannot by itself
complete the scholarly-baseline objective. A same-space algorithm comparison
must be registered after useful actions and return semantics are established.
The closed historical delta results remain evidence about that application,
not evidence that all TF-GRPO or GEPA implementations fail.

## Feedback limitation to keep visible

The frozen-baseline utility is u=2TP-F0(2TP+FP+FN), using official combined
word/character counts. With a positive denominator, positive summed utility
implies pooled F1 above F0. It does not guarantee the same ordering between
two improved policies when their denominators differ. Therefore utility is
the optimization signal; official pooled F1, intent and error decomposition
remain the evaluation criteria. The zero-denominator convention remains
explicit. No reward formula is tuned after observing validation results.

## Still required

Qualify action availability and behavior; execute complete-system exploration
rounds with logged action probabilities and frozen policies; verify that the
state exists before the action; freeze policy and provenance; evaluate against
the strongest fixed action; replicate before claiming stable gains. Keep new
DEV and test access closed under the existing data boundary.
