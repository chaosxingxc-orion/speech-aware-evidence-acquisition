# Training-free acquisition memory — preregistration

Date: 2026-09-01. Status: **REGISTERED BEFORE DISCOVERY REWARD REPLAY**. Execution profile:
`model-free-check`. Experiment contract:
`configs/experiment/slurp-training-free-acquisition-memory-v1.json`.

## Decision and correction to the earlier route

The 360-memory / 140-holdout expansion is not admissible. E108 failed six of eight information-
support conjuncts, and its consumed verdict explicitly prohibits spending that expansion. This
experiment does not relax that gate. It moves training-free control to the fixed environment created
by the locked BLEND baseline.

The controller optimizes one decision only: for a trajectory that the locked baseline already plans
to dispatch, should the loop spend the evidence contact (`ACQUIRE`) or stop with the same frozen
core's direct response (`STOP`)? It never widens dispatch. This directly addresses the adverse prior
from the delta override, which was perfect on exposed data and harmful out of sample.

## Method

The method is a non-parametric state-action-return memory. Its state contains nine bounded,
runtime-visible quantities available before the evidence contact: two retrieval cosines, their
margin, two fused-score quantities, admitted-facet load, selected-value load, selected-target load,
and whether the direct response parsed. Gold, correctness, the evidence response, sample identity,
speaker identity, transcripts, and future turns are forbidden state fields.

Every memory row is a fully observed decision point: the sealed trajectory contains its own direct
and evidence responses, so both actions can be scored without imputing a counterfactual. The default
is `ACQUIRE`. `STOP` is permitted only when at least `k` neighbors fall inside a fixed radius and all
have non-positive observed acquisition advantage. The finite grid is `k ∈ {1,3,5,7}` and radius
`∈ {0.05,0.10,0.15,0.20,0.25,0.30}`.

## Two-stage read boundary

Stage 1 reads only the already-exposed DEV-100 round-4 cell. Whole utterance groups are assigned
deterministically to a 70% tuning memory and a 30% internal support gate. Candidate selection
requires at least two saved contacts and zero harmful stops under leave-one-utterance-group-out
replay. Ties resolve by maximum contacts saved, larger `k`, then smaller radius. The independent
support gate requires zero harmful stops and at least `max(2, ceil(10% × gate_n))` stops.

Stage 1 writes a self-hashed policy artifact. Stage 2 is a separate command and refuses to open
DEV-500-NEW400 unless the artifact says the support gate passed. The artifact must be committed
before Stage 2 starts. There is no combined fit-and-evaluate command.

Stage 2 excludes every baseline-dispatched NEW400 trajectory whose utterance group occurs in the
discovery memory. This prevents repeated recordings of one utterance from becoming a hidden
memorization path. The parent 400-sample surface may be read only because it was already lawfully
opened by the registered DEV-500 read; this experiment opens no new gold surface.

## Fixed evaluation and stopping rules

The primary reward is `scenario_action_exact` from the repository scorer. Extraction is reported
separately as macro exact slot-F1, micro exact slot-F1, and official micro SLU-F1. The control-plane
account reports evidence contacts saved, total core contacts, STOP coverage, and helpful/harmful/
neutral STOPs. Paired uncertainty uses 10,000 bootstrap replicates with seed 20260807.

The holdout promotion gate is conjunctive:

1. at least 100 utterance-unseen baseline-dispatched holdout trajectories;
2. zero harmful stops;
3. primary score does not decrease;
4. the paired 90% CI lower bound is non-negative; and
5. at least 10% of eligible evidence contacts are saved.

If discovery support fails, NEW400 rewards remain unread. If the holdout gate fails, this controller
branch is recorded as falsified and the locked baseline remains unchanged. If it passes, the result
is a retrospective Stage-2 training-free control-plane contribution on already-exposed devel data,
not a test, confirmatory, generality, or Stage-3 claim.

## Hard boundaries

Zero model, embedding, tokenizer, HTTP, or socket contacts are authorized. The in-process offline
guard is armed before any experiment input is opened. DEV-1000-NEW500, FINAL60, SLURP test, and all
future turns stay untouched. The frozen policy and knowledge snapshot are read-only. No task-trained
model and no second answering model are introduced; both selectable answers remain outputs of the
same frozen core.
