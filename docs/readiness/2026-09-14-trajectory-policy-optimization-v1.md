# Trajectory sampling and training-free control-policy optimization

Date: 2026-09-14.
Status: prospective algorithm specification; no new contact authorization.

**Later owner sequencing instruction:** first establish a stable-benefit agent
base and useful optimization workspace. Follow
[the current base-first plan](2026-09-14-stable-agent-base-first-v1.md).
Defer implementation of this document's sampling contract, factor abstraction
and update operators until that base is established. Preserve this proposal for
later review; it is not current execution priority.
Authority: owner clarification that reproducible trajectory sampling and algorithmic
optimization, rather than root/GPT-6 system edits, must define training-free research.

This specification supersedes the execution order and algorithm interpretation in
[the first rule-cycle plan](2026-09-14-training-free-system-rule-cycle-v1.md).
Preserve that earlier plan as an engineering proposal and historical record.
The currently admitted bounded-evidence recovery keeps its exact frozen source,
configuration, budget and one-recovery boundary.

## Separate three objects

1. Direct frozen-model performance.
2. A fixed multimodal agent base with knowledge, legal tools and role transitions.
3. The same base after a registered algorithm updates its external policy.

Root-authored prompt changes, bug fixes, tool integration and qualitative error
analysis belong to object 2. They do not establish object 3 or algorithm novelty.
A root model must not supply sample solutions, hand-written corrective rules,
preferred actions or checkpoint selection inside a reported optimization run.
Root designs and reviews the protocol and implementation; the frozen study core,
deterministic reward bridge and specified update operator execute the algorithm.

Keep the 95% candidate-coverage target alongside whole-task optimization.
Do not require it before optimizing. Do not use coverage as the only reward:
coverage, conditional intent selection and slot grounding can move differently.

## Correct the previous trajectory interpretation

The completed TRAIN A anchor and the bounded-evidence successor are trajectories
from different system policies. Their eventual complete paired comparison can
identify system changes and supply diagnostic support. It is not an on-policy
GRPO rollout group. They must not be relabeled as independent samples of one
policy or credited as an algorithm update.

Likewise, repeating a deterministic request with identical sampling settings
does not establish useful exploration. Generated explanations are not measured
action advantages. Cross-case rule consolidation alone is an artifact facility,
not the primary algorithm or a demonstrated learning loop.

## Reproduce a meaningful algorithm baseline first

Adapt 2025 Training-Free GRPO through the shared controller and executor:
freeze a policy version, generate multiple actual trajectories per optimization
input, score complete sources, contrast within-input outcomes with the same
frozen core, update a versioned experience policy, and repeat the registered
iteration schedule. Use a planned group size of four and at least two update
rounds as the initial design; exact execution plans remain to be admitted.

The baseline's update may be textual. Automatic, reward-conditioned experience
revision with grouped sampling is different from a researcher editing prompts.
Do not replace the published semantic update with a numerical formula and call
it an exact reproduction. Record our score-only, single-frozen-core adaptation:
upstream defaults that expose ground-truth answers to reflection are excluded.

The official preview branch now declares itself deprecated and points to the
main-branch Agent Practice implementation. Preserve the previously audited
historical commit as the reproducibility reference. Pin and inspect any newer
implementation before choosing it; do not silently change the baseline source.

Sources: [paper](https://arxiv.org/abs/2510.08191),
[official historical branch](https://github.com/TencentCloudADP/youtu-agent/tree/training_free_GRPO),
[existing pinned source audit](2026-09-11-training-free-rl-2026-source-audit.md).

## Research candidate: optimize the value of acquiring and using evidence

The scientific hypothesis is that a system should learn which evidence action
improves the eventual speech task in a particular observable state. A tool being
called, producing plausible text, or receiving Reviewer approval does not prove
information gain. Compare actual downstream outcomes and retain harmful uses.

Use the existing role graph. Perception consumes task knowledge and speech.
Reviewer and Planner expose finite, legal decisions. Solver retains answer
authority and consumes the resulting evidence. Do not add an answering model
or allow an external policy to select an intent using its reference label.

### State, actions, transitions and reward

Represent an episode as a sequence of source-bound states, actions, observations
and one final delivered answer. The state projection includes the role and phase,
current candidate distinctions, missing or contradictory field evidence, acquired
evidence identifiers, completed decisions, allowed context and remaining bounds.
Use only deployment-visible fields; preserve access to the original speech.

Actions remain role-scoped and preconditioned. Candidate action families include:

- Acquire a registered intent boundary or candidate-specific slot contract.
- Request local ASR for a named evidence gap.
- Refresh candidate perception after an actual new observation.
- Request Solver revision using specified evidence.
- Preserve a completed answer or stop.

These are design families, not claims that every family is currently exposed as
a selectable action. Bind each admitted action to an existing shared tool or
transition. Hide unavailable actions and retain the exact legal-action mask.
Perception and Solver do not acquire independent analytical tool authority.

For SLURP, optimize a prospectively fixed, sample-decomposable quality reward
derived from the official scorer's retained statistics. Keep full-task micro SLU
as the main reported metric and preserve its TP/FP/FN aggregation: mean sample F1
is not micro F1. Choose and register the optimization scalar and its relation to
the reported metric before outcome access; intent and slot components accompany
it. Do not invent a weighted reward after seeing a favorable result.

Candidate coverage and conditional selection are diagnostic components; any
intermediate shaping term must be separately registered and compared against
terminal-reward-only learning. Do not reward larger candidate sets by default.
For later E21 and Audio2Tool, use their own native task outcomes and explicit
scalarization, not the SLURP reward. Cost and latency remain descriptive.

### Genuine sampling and attribution

For each policy version and input, collect four genuine complete episodes with
registered distinct random streams. Record policy identity, prompt/tool/knowledge
identity, sampling parameters, source input and every selected action.
Exploration may vary legal control actions while keeping Solver decoding fixed.
For the TF-GRPO baseline, any stochastic role decoding is separately explicit.
The unoptimized exploration control uses the same sampling mechanism.

Within-input group advantage can center the complete return, optionally divide
by its standard deviation, and retain the raw return difference. All-tied groups
have zero advantage; low-variance numerical artifacts must not create preference.
Four rollouts are repeated measurements of one input, not four independent cases.

Initially use terminal-return Monte Carlo credit at actual decision states.
This supplies an algorithmic learning signal but does not isolate tool causality.
To study evidence action value, prospectively sample alternative legal actions
from the same immutable node-state prefix and execute their real continuations
under the same continuation policy and random-stream schedule. Record branch
assignment probabilities. Unexecuted branches have no measured reward.

Source-bound prefix reuse is optional infrastructure, not a prerequisite for the
first complete-rollout baseline. If safe node continuation is not implemented,
collect complete real episodes and limit attribution accordingly. Never produce
counterfactual trajectories by editing an old response or manifest. Shared
prefixes remain correlated; account for actual contacts once and logical reuse
separately. Do not use gold to choose which states receive branch expansion.

### Explicit external policy update

Maintain nonparametric state/action return statistics outside core weights.
For a fixed, admissible state representation, estimate action value from actual
sampled continuations. Keep support count, variability, harmful transitions,
policy/iteration identity and source links. Older-policy returns do not become
current on-policy values by pooling them without correction.

Use a finite external action distribution, not unverified decoder logits.
A prospective KL-regularized update has the form:

    A_t(s, a) = Q_hat_t(s, a) - sum_b pi_t(b | s) Q_hat_t(s, b)
    pi_next(a | s) proportional to pi_t(a | s) * exp(eta * A_t(s, a))

Normalize over the current legal mask. Exploration during collection mixes in a
registered distribution with nonzero support for eligible alternatives and logs
the resulting assignment probability. Unsupported or stale states retain the
base policy; missing support is not evidence that an action is poor.
Define state matching, support rules, step size and numerical stabilization in
configuration before collection. Do not tune these from Fold B.

This formula defines an external finite-action update, not a token-logit API,
neural policy training or a guaranteed global improvement. Empirical returns in
partially observed states are uncertain. Prove the numerical update separately
and evaluate the actual resulting agent. A model's verbal confidence is not a
calibrated action probability. If the frozen base exposes only a selected action,
a registered stochastic proposal/prior interface is needed; do not manufacture
its probability from answer-token likelihood.

JitRL motivates action-advantage policy adjustment, and MemRL motivates external
value updates. The pinned JitRL source audit distinguishes its paper formula from
the released probability-plus-advantage scoring path. Our proposed external
distribution must be labeled an adaptation and is not granted the paper's claims.
Do not reopen the closed log-probability probe.

Sources: [JitRL](https://arxiv.org/abs/2601.18510),
[official JitRL code](https://github.com/liushiliushi/JitRL),
[MemRL](https://arxiv.org/abs/2601.03192),
[official MemRL code](https://github.com/MemTensor/MemRL).

### Knowledge and memory remain distinct

Keep stable task contracts in the separate intent and slot knowledge stores.
The algorithm optimizes evidence selection and use before changing their content.
Keep raw training trajectories in the offline optimization archive; do not expose
them as a runtime training-example database.

If textual memory is used, the same frozen core automatically derives bounded
conditional lessons from measured trajectories. Preserve counterexamples and
uncertainty. A rule must state an observable condition, an action and expected
discriminating/explanatory evidence; it must not encode a case's reference answer.
Credit and selection come from the specified update/evaluation procedure.
Root reviews provenance and validity, not which wording should win.

Rule consolidation becomes an optional policy representation and TF-GRPO
baseline facility. Implement it when the algorithm needs it; do not make
open-ended rule engineering the prerequisite for starting trajectory sampling.

## Evaluation that separates compute, engineering and learning

Keep the direct model, fixed agent and optimized agent as separate reported rows.
Also retain an unchanged-policy sampling control at matched registered sampling
and inference settings. More rollouts with no update may improve selection or
merely expose oracle headroom; either way, it is not learning.

Report best-of-group using official rewards only as an offline oracle diagnostic.
Deployment selection may not access those rewards. If deploying multiple samples,
use a label-blind registered selection rule and compare with the same rule and
budget in the unoptimized arm. Also report a single deployed-episode comparison
where applicable, so an optimization effect is not conflated with more inference.

Perform update/checkpoint choices entirely within TRAIN A under a fixed schedule
and speaker-grouped inner evaluation. Selection data reused across iterations is
optimization data, not an independent test. Use pooled eligible cohorts for
effectiveness claims and preserve existing roster/stratum requirements.
Register the exact split/group construction and checkpoint acceptance rule before
additional contacts. Do not hand-select a favorable checkpoint.

Freeze the resulting policy before Fold B. Do not update from B references or use
B to select rules, hyperparameters or algorithm variants. Any comparison of the
TF-GRPO baseline and the research candidate must be registered before B is read,
with all arms reported and no post-read winner tuning. Any claim beyond exploratory
development still needs the inherited replication and qualification evidence.

## Execution order and actual gaps

1. Finish or close the already admitted bounded-evidence recovery according to its
   existing contract. It supplies engineering and trajectory evidence only.
2. Audit public rollout identity, distinct random streams, action probability
   logging, shared reward links and configured updater support. Implement the
   minimum shared gaps and prove them synthetically.
3. Admit a bounded same-policy grouped-rollout TF-GRPO adaptation on TRAIN A,
   with a fixed update schedule and complete-source scoring.
4. Implement and register the finite evidence-action value update. Reuse the
   same base, role authority, data handling, service and trajectory format.
5. Freeze candidates, then execute the untouched B comparison under fresh plans.
   Transfer the verified optimization interfaces to Audio2Tool and E21; specialize
   knowledge, legal action scopes and task rewards. No new E22 flight is implied.

Use one resident model service and one active experiment. Fill its available
slots with independent episodes within the admitted flight. Interleave CPU
preparation and complete scoring without bypassing model-contact custody.
An observed failure does not authorize another recovery or a renamed replacement.

## Source audit completed before implementation

Read-only audit used frozen source f2c90cb2 and root rechecked the decisive shared
interfaces. Existing decoding requests admit seed and temperature
(core/model/request_types.py:85); separate registered runs can reuse one policy
and roster with distinct seeds at one fixed temperature. Changing temperature
changes the stochastic policy. Existing build_group_relative_feedback joins
distinct complete runs on the same ordered cohort; it explicitly permits
different policies and therefore does not certify same-policy sampling.
The bundle verifier rejects duplicate sample IDs (core/bundle/outputs.py:201).

The minimum first extension is a shared rollout-family preparation contract that
expands a pinned policy/roster and ordered random-stream schedule into existing
run identities. Bind one common stochastic-policy identity separately from
individual seed-bearing request identities. Keep one output per input in each
run and join the complete runs through existing feedback readers. This avoids
rewriting the executor or bundle format just to start grouped sampling.

The current Planner records the returned legal action but no probability
(reproduction/ojw/native_episode.py:246-273). Reviewer free-form tool calls also
have no normalized categorical action distribution. The numerical policy
candidate therefore needs an actual finite decision interface and source-bound
decision receipt; raw token log probabilities do not fill that gap.

The native graph starts at _InitialState, and _RoleCheckpoint is invocation-local
custody (native_episode.py:126-160, 612-630). There is no public source-verified
branch-resume interface. Defer its implementation until the matched-prefix
attribution experiment is registered. Full-episode sampling can proceed first.

No audited interface or document change has added experimental contacts or
modified the active frozen recovery source.

## Claim boundary

A candidate algorithmic contribution is state-dependent estimation and use of
downstream task benefit for multimodal evidence actions, including harmful evidence
and the distinction between acquired evidence and evidence used by final Solver.
This is a hypothesis. A formula, memory artifact or engineering test does not
establish novelty or effectiveness. Establish those through implemented updates,
trajectory diversity/support diagnostics, matched controls and independent
evaluation. Keep prior manual improvements in the engineering baseline record.
