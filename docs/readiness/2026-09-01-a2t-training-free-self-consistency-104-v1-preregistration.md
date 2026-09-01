# Audio2Tool training-free self-consistency v1 — prospective 104-sample preregistration

Date: 2026-09-01. Status: **SCIENTIFIC DESIGN REGISTERED; NO NEW MODEL CONTACT
AUTHORIZED YET**. Experiment: `SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1`. Machine contract:
`configs/experiment/a2t-training-free-self-consistency-104-v1.json`.

## Why this is the next admissible variable

Signed-supply memory v1 and registry-semantic memory v2 exhausted the static 217-row return
surface. Their structural and semantic states were live, but every supported positive cell mixed
saves with harms. The v2 terminal rule forbids another threshold or categorical split of those
same returns. This successor changes the information available at runtime: it obtains one new
same-core direct observation before deciding whether stripped registry evidence is worth another
contact.

The cohort is the already-exposed `A2T-G1-104` discovery set: 13 samples per tier, receipt SHA-256
`b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db`. It opens no new sample,
G2, FINAL60, test annotation, or future turn. Its old M0 answers are frozen at SHA-256
`dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467`. Previous G1 work already
reported that one historical direct re-flight was byte-identical on 93 of 104 samples. That
aggregate motivates a liveness expectation; the historical re-flight is not substituted for the
new observation and its per-sample outcomes are not used by this experiment.

## Frozen AgentLoop

The task runs through `openjiuwen-workflow-v1` and the same receipt-pinned frozen Qwen3-Omni core.
No parameter changes, task-trained model, second answering model, transcript fallback, logprob
route, or embedding contact is allowed. Every new request carries the exact original speech-feature
packet.

The loop has two prospective phases. `REOBSERVE_DIRECT` replays the byte-identical M0 messages once
for all 104 samples and seals the responses. `SUPPLY_UNION_STRIPPED` then parses M0 and the new
observation with the frozen scorer parser, takes the registry-resolved union of predicted tool
names, renders those registry rows in registry order, removes only `argument_defaults`, and makes
one evidence contact per sample. If neither observation resolves a registry tool, supply is
unavailable. The final policy action is either `STOP_M0`, which returns the original M0 answer, or
`SUPPLY_UNION_STRIPPED`, which returns the evidence response. The observation never silently
replaces the answer.

The union renderer is order- and duplicate-invariant and may read no gold, expected arguments,
reference text, sample identity, tier, reward, or future response. This makes the supplied row a
deterministic function of deployment-visible state.

## New state and training-free reward memory

The coarse state contains paired parse status and the relation between the two predicted tool
multisets: exact, overlap, disjoint, or unresolved. The detailed state adds call-count agreement,
per-tool argument-key-signature agreement, and per-tool argument-value agreement. Tool names,
domain/category labels, literal argument values, transcript text, sample/group identity, tier,
gold, correctness, reward, and the evidence response are forbidden features.

Five whole-`query_idx` folds at seed 20260901 keep related renderings together. The controller is a
hierarchical exact-cell non-parametric action-return memory: consult the most-specific other-fold
detailed cell and then the coarse cell; supply only when support is at least four, observed saves
are at least two, and observed harms are zero. Otherwise stop. Reward is the official exact-match
difference between the evidence response and frozen M0. Tool accuracy, slot micro-F1, and contact
cost are reported but cannot replace exact match as the selection target. There is no
counterfactual imputation and no parameter training.

## Pass, failure, and scale

Promotion is conjunctive. The cross-fitted policy must exercise both actions; supply 5–52 samples;
save at least three exact matches; harm at most one; gain at least two exact matches; have a
strictly positive grouped CI90 lower bound; keep tool-accuracy net gain nonnegative; be nonnegative
in every fold and positive in at least two; avoid at least 80% of always-supply harms while
retaining at least 50% of its saves; and demonstrate at least two live state classes with at least
ten samples outside the dominant class.

Failure closes same-core direct self-consistency as the next Audio2Tool targeting signal and makes
no further contact. Success freezes exactly one controller for a separately preregistered
actual-policy support run on the remaining exposed discovery cohort. It cannot revise the baseline,
open G2, or support a superiority, confirmatory, generality, or Stage-3 claim. Only a stable
prospective support gain may propose a later scale transition.

## Evaluation efficiency and integrity

Both complete 104-row contact arms seal before gold opens. Each arm is one indivisible official
scorer job. The two official scorer processes then run concurrently through
`scripts/evaluate_parallel.sh --workers 2`. No dataset shard is scored independently and no shard
metrics are averaged. The receipt records batch wall time, each job's elapsed time, result hashes,
and the explicit whole-manifest boundary.

The plan allows 208 main contacts plus four canary and one resend contacts, at most 1,200 metered
speech-audio seconds and 0.5 GPU-hours, with zero paid API, embedding, or tokenizer spend. These are
run-local fail-closed ceilings, not a revival of the retired program-wide numeric limits.

This document registers the scientific design only. Before any core contact, the implementation,
tests, structured `contracts.ExecutionPlan`, protocol hash, exposure binding, packet and runtime
receipts, prompt-fit proof, renderer-identity proof, scorer manifests, and two-job score table must
be committed and the working tree must be clean.
