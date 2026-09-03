# Open-source training-free control adoption for Audio2Tool

## Decision

Adopt `vowpalwabbit==9.11.2` as the primary open-source policy-learning asset
for the Audio2Tool external control plane. Keep `mabwiser==2.7.4` as a
lightweight macro-router ablation only. Do not build a repository-specific RL
algorithm.

The term *training-free* refers to the frozen Qwen3-Omni answering core: no
core weights, adapters, task-trained speech model, or second answering LLM are
introduced. Vowpal Wabbit does learn an external control policy from discovery
rewards. Describe the system precisely as a **parameter-frozen core with a
learned external control policy**, rather than as a system with no learning of
any kind.

This decision changes the controller implementation path. It does not promote
G7, authorize new model contact, open test data, or establish an effectiveness
claim.

## Production implementation boundary

The active TFRL production path is the thin adapter in
`analysis/training_free_vw_control.py`. Local code may validate and render ADF
examples, call the pinned upstream workspace's `learn` and `predict` methods,
and save, load, and hash upstream policy artifacts. It must not implement a
study-owned learner, value update, reward-memory rule, or learned action-scoring
algorithm. Mechanically sampling the upstream probability vector with a logged
external random draw remains adapter work; the probabilities and their updates
remain owned by Vowpal Wabbit.

The repository's earlier handwritten memory controllers, including the
`training_free_*_memory.py` modules, are historical discovery records and are
explicitly excluded from this active path. Keep those files intact for audit
and reproducibility, but do not import, wrap, extend, or select them from a
production Vowpal Wabbit launcher. Their prior results remain evidence about
the experiments that produced them; they are not the adopted TFRL learner.

## Why Vowpal Wabbit is the primary asset

Vowpal Wabbit provides the capabilities the AgentLoop needs without adding
another answering model:

- contextual-bandit learning over context, action, chosen-action probability,
  and terminal cost;
- action-dependent features through `cb_explore_adf`, including action sets
  that change between decisions;
- standard exploration policies and propensity-aware logs;
- IPS and doubly robust estimators for properly randomized logged feedback;
- an established BSD-3-Clause implementation with Python bindings.

The upstream references are the
[contextual-bandit tutorial](https://vowpalwabbit.org/docs/vowpal_wabbit/python/latest/tutorials/python_Contextual_bandits_and_Vowpal_Wabbit.html),
[offline policy-evaluation tutorial](https://vowpalwabbit.org/tutorials/off_policy_evaluation.html),
and [source repository](https://github.com/VowpalWabbit/vowpal_wabbit).

MABWiser remains useful as an independent small-data ablation because it
provides linear and non-parametric contextual bandits with parallel fitting and
prediction. Its public API is centered on single-arm selection and does not
natively provide Vowpal Wabbit's action-dependent changing-action format or
propensity-first logging. Using it for the sequential AgentLoop would therefore
require more local policy machinery. The upstream references are the
[public API](https://fidelity.github.io/mabwiser/api.html) and
[source repository](https://github.com/fidelity/mabwiser).

Stable-Baselines3 DQN is out of scope for this phase because it would add a
separately trained neural Q-network and is poorly matched to the small logged
reward surface. DSPy/GEPA is not the primary control asset because it optimizes
prompts and normally adds reflection-model work rather than a bandit policy
over the registered AgentLoop actions.

## Compatibility result

An isolated compatibility probe used Python 3.12.3, matching the repository's
declared Python floor. It installed the exact Linux CPython 3.12 wheel for
`vowpalwabbit==9.11.2` and the universal wheel for `mabwiser==2.7.4`. Both
imports succeeded. A three-action `cb_explore_adf` prediction returned a valid
three-probability vector, and a two-arm MABWiser LinUCB fit/predict round trip
succeeded.

The repository adapter then made the estimator and the state-action interaction
explicit with `--cb_type dr --quadratic sa`. A real two-context/two-action
round trip trained on balanced logged feedback learned opposite actions for the
two contexts: the preferred-action probability was approximately 0.975 in each
context while the other action retained the configured 0.025 exploration mass.
This verifies contextual routing rather than a context-independent global arm
preference.

Neither package was added to the existing research environment by that probe.
The production integration must keep Vowpal Wabbit in a pinned optional extra,
record its exact version and configuration in every policy artifact, and keep
the base package importable without the compiled extension.

## Correct starting evidence

The same-row comparator for G7 is the frozen G1 M0 output filtered to G7's 16
sample identities. It scores 11/16 tool correct, 4/16 exact, and 0.500000 slot
micro-F1. G7 scores 7/16 tool correct, 3/16 exact, and 0.405797 slot micro-F1.
G7 has zero exact saves and one exact harm. The earlier 6/16 tool, 3/16 exact,
and 0.285714 slot-F1 M0 figure belongs to the different G6 roster and must not
be used for G7.

A gold-informed oracle choosing only between the existing M0 and G7 terminal
responses reaches 11/16 tool correct, 4/16 exact, and 0.514286 slot micro-F1.
Therefore controller optimization over only `STOP_M0` and `USE_G7` cannot
approach the post-training-free-RL target. The action set must improve before a
router can improve the system.

G7 remains valuable as the complete, runnable engineering baseline: 480/480
contacts completed, all 16 final responses parse, and the trace contains live
OBS/ORG/SUPPLY/USE state. It is not an accuracy-improving baseline.

## What existing traces can and cannot support

The paired M0/G7 terminal outputs provide complete rewards for two macro-actions
on 16 contexts. They are sufficient to compute the two-action oracle ceiling
and to falsify that action set. They are not sufficient to learn or evaluate a
sequential query policy.

Only one deterministic G7 trajectory was executed:

```text
OBS -> all 28 EVIDENCE families -> all-tool RESOLVE
```

No logged counterfactual reveals the value of skipping or reordering a family,
deepening OBS, narrowing the candidate sheet, verifying a value, backtracking,
or stopping early. The trace also has no action propensity. IPS, DR, or a
stage-level value estimate would therefore be invalid on the existing G7 trace.

## Bounded action-support experiment

The next model-contact experiment is an action-space reachability study, not a
policy-success claim. Keep G7 immutable and use a new identity-only fixed16
roster drawn from the untouched discovery/support remainder. Hold the shared
OBS and evidence collection fixed, and execute these complete policy branches
once per row:

1. `STOP_M0`: return the direct frozen-core answer.
2. `EXHAUSTIVE_G7`: use the current all-tool G7 resolution.
3. `SUPPORT_ONLY_RESOLVE`: mechanically remove unsupported candidates before
   the frozen core resolves.
4. `DECOMPOSED_SELECT_BIND_RESOLVE`: use the complete normalized status surface
   to select registered tools, bind values in a separate speech-carrying step,
   then let the frozen core author the official response.

Every branch must retain final-answer authority in the frozen core. The
controller may select evidence and procedure, but it may not synthesize the
answer. Gold remains closed until every branch output and trace is sealed.

This complete-branch screen gives a real per-row oracle. Stop expanding this
action set if the oracle remains below 15/16 exact or slot-F1 does not exceed
0.90: no policy learner can beat the actions it is allowed to choose. If the
oracle is reachable, use the same branch definitions to collect randomized,
propensity-logged discovery feedback for Vowpal Wabbit.

## Initial Vowpal Wabbit formulation

Start with macro-action routing. Do not claim sequential RL at this stage.

Deployment-visible context may include:

- OBS parse validity and bounded structural features;
- correction, multi-intent, and dialogue-history cues derived before scoring;
- completed-family and parser-coverage counts;
- support, contradiction, uncertainty, sibling-conflict, and candidate-width
  counts;
- typed-value coverage and unresolved-value counts;
- actual serialized prompt size, remaining context margin, contact count, and
  remaining contact budget.

It must exclude gold, reference transcripts, test annotations, sample identity,
tier identity, future turns, and scorer-derived values.

Each decision log must bind the ordered available actions, action-dependent
features, the complete probability vector, selected action, selected-action
propensity, policy/configuration hash, and pre-reward context hash. The official
terminal reward is joined only after sealing and scoring. Use binary exact match
as the primary reward; treat tool correctness, slot-F1, mechanical validity,
and contact cost as separately reported diagnostics or pre-registered
constraints so dense shaping cannot conceal a loss in exact match.

Fit and select policies only on discovery folds. Hash and freeze the chosen
policy before any disjoint validation. Never use test rows for feature,
hyperparameter, action, threshold, or prompt selection.

After the macro-action experiment demonstrates both action variation and
out-of-fold reward separation, a later successor may use `cb_explore_adf` at
each AgentLoop step. Consider CCB only after valid slot/sequential feedback has
been logged; do not infer it from the deterministic G7 trace.

## Scale progression and target

Use this sequence:

```text
correct M0 + runnable G7 baseline
  -> fixed16 action-reachability screen
  -> approximately 100 discovery examples with logged propensities
  -> freeze policy before disjoint validation
  -> approximately 1,000 examples only after stable paired gains
  -> larger confirmation only after the gains remain stable
```

The `>0.90` performance objective applies **after** the open-source
training-free control policy, not to admission of the engineering baseline.
Promotion requires an actual paired gain over direct M0, an actual paired gain
over the fixed AgentLoop baseline, evidence-use information gain rather than
format repair alone, and a positive contribution attributable to the frozen
external controller on data not used to select it.

## Execution notes carried forward

- Determine prompt fit from the actual serialized request at every loop step;
  do not reserve the context window from a fixed per-step estimate. The present
  service has a 32,768-token model context and a 24,576-token operational cap;
  G7's longest request remained below that cap, so context length was not its
  observed failure cause.
- Batch execution remains supported. Preserve sample-affine state and use the
  proven two-slot geometry until a separate throughput experiment justifies a
  change.
- Do not model network jitter as a baseline variable.
- Run the official scorer once per complete sealed manifest. Independent full
  manifests may be scheduled in parallel by an outer launcher; never shard one
  manifest and average partial scorer outputs.
