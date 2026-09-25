# Finite action policy: pre-action state and full-system return

Owner scope clarification: this is a restricted single-action comparator.
The main Stage-3 objective is complete system policy optimization, as specified
in 2026-09-25-stage3-system-trajectory-optimization.md. A full-system terminal
reward does not by itself broaden the action space beyond Solver supply.
Preserve this baseline, but do not report it as sufficient coverage of system RL.


Status: root design continuation; no model-contact authorization in this note.
VAR-2 is closed after its sole recovery failed and supplies no matched-prefix
result. The action set and contact identities will be registered after F10
closes, using the available ordinary full-system VAR-1 evidence. This note makes the approved algorithm operational without changing
the frozen answering model or reopening the closed semantic-delta campaign.

## Research question

Can a frozen policy learned from construction trajectories select evidence
supply better than the strongest single fixed supply configuration? A global
win by every candidate action is unnecessary: a useful policy may exploit
different actions in different states. However, all actions must be executable,
have bounded requests and complete-system evidence, and preserve the same
knowledge-source exclusions. A local Solver advantage is not a system return.

The first action inventory is default20, examples10, examples30 and
intent-diversified supply, subject to root admission from the completed
VAR-1/VAR-2 evidence. F10 is a global representation choice, not an additional
action dimension in the first policy. Do not multiply this small action space
by candidate width, prompts, model settings or reviewer changes.

## Decision timing and state audit

The choice occurs after the initial Perception output is normalized and before
the first Solver request is built. Compute agreement against a deterministic
default20 supply preview under that same query state, before an action can
alter the supplied examples. The preview uses existing frozen vectors and
released knowledge labels only. It does not use the current sample's gold
intent, transcript, final answer, reviewer outcome or eventual revision count.

Keep the existing agreement bin boundaries from slurp_var1_variant_read.py;
freeze their exact values in the execution configuration. An empty preview
has its own state. Candidate count, predicted scenario and input duration are
diagnostics initially; do not tune new thresholds after reading returns.

An important audit finding: slurp_plan_bad_case_bank.load_plan_runtime
collects the union of new_value_ids across all waves. Consequently,
build_states' exemplar agreement based on that aggregate is episode-visible,
but is not guaranteed visible before the first Solver action. Preserve that
historical analysis as descriptive. Never directly train or deploy a policy
from its aggregate supplied list.

The runtime receipt must bind the first Perception state hash, the preview
query hash, ordered preview ids, state bin, action probabilities, sampled
action, policy hash and decision sequence. Assert that all state events
precede the selected action. Altering later waves in a test must leave the
initial state and action unchanged. Keep normalized candidate order stable.

## Episode and sampling semantics

Choose one supply action per episode and retain it through revisions. Run
the ordinary Solver, Reviewer and Planner through the shared OpenJiuwen
executor, with the existing finite completion rules. Each revision uses the
same action's own cumulative evidence; no side branch inherits a different
action's critique or answer. Only the delivered full episode is scored.

First construction round: uniformly randomized eligible actions with a
pre-registered seed and near-balanced counts. Log actual assignment
probabilities, including the allocation scheme. Do not relabel deterministic
quota assignments as independent uniform sampling.

Second construction round: freeze the updated policy for the entire round.
With probability 0.8 choose the current preferred action; with probability
0.2 draw uniformly from all eligible actions. Thus the preferred action has
probability 0.8 + 0.2/K, and each other action 0.2/K. Break value ties with a
pre-registered stable action order. Update only after complete scoring.

The state must remain action-independent: use the same default preview to
define agreement for all actions. Sparse state-action cells (fewer than20
observations) fall back to that action's global estimate. Never inspect
evaluation annotations to choose a fallback.

## Feedback and value update

Use the already frozen VAR-1 PLAN F0 and official word/character counts:

u = 2 TP - F0 (2 TP + FP + FN).

Store raw counts, intent correctness, format/fallback state and source hashes
alongside utility. Correctly empty outputs and hallucinated empty-target
entities must receive different feedback. Utility is in count units; do not
label it a percentage improvement or pass it to a boolean success API.

The first policy uses cumulative arithmetic means of observed full-system
returns, by state-action and globally, updated at round boundaries. Preserve
counts and sums and make updates idempotent by sealed trajectory identity.
A repeated or conflicting trajectory cannot silently update memory twice.
The knowledge store remains unchanged; memory stores state/action evidence,
counts, estimates and provenance.

This is a contextual bandit with complete-system returns, a MemRL-inspired
adaptation. It is not faithful reproduction of MemRL or a multi-step RL claim.
Do not optimize the reward formula after observing evaluation results.
Positive aggregate utility and ranking among two improved policies are
different questions; official pooled F1 remains the primary evaluation.

## Evaluation and scientific interpretation

Freeze the policy and switch exploration off before evaluation on the already
authorized exposed regression roster. Compare it with both locked default
and the strongest eligible fixed action selected on construction data.
Keep roster, serving geometry and complete execution program matched, and
register selection and repeat rules before execution. Repeated construction
rows estimate optimization behavior, not transfer or generalization.

Report all actions' counts, propensity distribution, per-state support,
fallback frequency, action changes between rounds, official pooled F1,
intent, empty FP, nonempty FN/FP, strata and resource use. Separate improvement
over the default from improvement over the strongest fixed action. If only
the former holds, report a configuration benefit without an adaptive-policy
advantage. If neither holds, retain the negative result and identify whether
the state, action effects or noisy return prevents useful selection.

A stable-gain claim requires a registered matched replication; discovery
selection alone cannot establish it. Fresh DEV6570 and test13078 remain
closed. No threshold or fresh roster is opened to manufacture significance.

## Required scholarly comparisons after this baseline

Use the pinned source audit in training-free-rl-baseline-fidelity.md.
A same-space MemRL-style comparator must explicitly bind its fixed-alpha
update, memory retrieval and credit rule. An adapted TF-GRPO comparator must
execute grouped full trajectories, feedback, bounded experience updates,
and another execution round; one reflection is insufficient.

The finite-policy baseline is the smallest actual sampling-feedback-update-
evaluation cycle. It supplies a controlled optimization space for those
algorithm comparisons, not a replacement for them. Review root conclusions
before expanding to multi-step Reviewer/Planner decisions or other datasets.


## Implementation boundary and next integration

Reuse FlightRuntime._resolve_phase_supply and the ordinary
NativeEpisodeRunBinding.supply_for_phase callback. The shared runner invokes
that callback with the just-sealed Perception state before the first Solver
request. Choose the action there once, then retain it by episode identity.
Do not enter the closed supply_variants grouped-Solver branch.

Reuse each action's existing named-knowledge-store router and the same
composite knowledge identity. A fixed default20 preview establishes the
state; selected-action routing establishes the actual supplied evidence.
Both need separate receipts so an inspected preview is never reported as
model-exposed evidence. Validate preview query/state hashes and reject any
first decision that already contains Solver/Reviewer/Planner output.
The absence of a policy configuration must preserve existing requests.

The numeric library, pinned snapshot and schedule loader, pre-action state
receipt, episode-held action router and ordinary OpenJiuwen graph proof are now
implemented. See 2026-09-25-finite-policy-runtime-integration.md and the corresponding
implementation receipt. This is model-free engineering evidence; the algorithm
registry remains planned until a registered formal cell executes.

The shared full-system official-feedback reader now verifies complete sealed
sources, finalized score custody, exact populations and pooled counts. See
2026-09-25-stage3-system-trajectory-optimization.md. Remaining restricted-baseline
work is its policy-decision credit join (including episodes ending before the
action), immutable round-update entry point, complete-horizon request capacity and
formal admission. Numeric dataclass validity alone is not artifact-seal proof.
This restricted comparator does not replace the full-system optimization plan.

Round1 uses balanced sampling without replacement in fixed roster order.
Choose the remainder-action allocation reproducibly before the round, then
record the registered seed, quotas, roster order and per-decision random draw.
Report the actual conditional probability vector remaining_count/remaining_total,
including zero probabilities at the end of the schedule. Do not pass this
allocation through the independent epsilon-greedy probability formula.
Round2 uses the declared 80/20 epsilon-greedy rule with the prior snapshot
frozen throughout; evaluation uses zero exploration.

## Statistical limits to diagnose, not silently repair

With625 trajectories and four actions, round1 provides about156 observations
per action before splitting into five agreement states. Rare state-action
cells may stay below20 observations; report that frequency and the resulting
global fallback. Do not promise a detectable small improvement from these
counts or replace the registered thresholds after seeing results.

During adaptive round2, different actions may be sampled under different
state mixtures. Their unweighted global means can therefore reflect both
action quality and the states where they were selected. Preserve the approved
cumulative-mean estimator for this baseline, retain exact propensities and
state occupancy, and report the limitation. Importance-weighted or
state-standardized estimators would be separately registered algorithm
comparators, not an invisible repair after an unfavorable evaluation.

The design does not require every action to outperform the default globally.
It requires lawful complete-system execution and evidence sufficient to test
conditional usefulness. Admission must consider the EX-DIV harm signal and
the weak separation between K10/K30 and PLANR; no action is promoted merely
because its single point estimate is largest.
