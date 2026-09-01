# Training-free query memory v2 — preregistration

Date: 2026-09-01. Status: **REGISTERED BEFORE V2 DISCOVERY REPLAY**. Experiment:
`SAEA-SN-MF-TFRL-QUERY-MEMORY-V2`.

## Why v2 exists

V1 failed its discovery support gate. On the 26-item tuning side, one-neighbor scalar memory saved
12 contacts but lost four correct answers; three-neighbor memory saved ten but lost three; five- and
seven-neighbor rules removed the harm only by saving no contacts. Every radius from 0.05 through
0.30 was identical at fixed `k`. NEW400 stayed unread.

V2 changes one variable: state representation. The nine scalar retrieval/fusion/load values are
replaced by the exact direct-answer query vector already used by the locked retriever. This is the
information-bearing state the knowledge plane acts on and requires no new model or tool contact.

## Frozen controller and grid

The policy remains a non-parametric state-action-return memory. For a baseline-dispatched trajectory,
rank memory rows by query-vector cosine after excluding the trajectory's whole utterance group.
`STOP` is allowed only when the top `k` rows all clear the minimum cosine and all have observed
acquisition advantage at or below zero. Every other state defaults to `ACQUIRE`.

The finite grid is `k ∈ {1,3,5,7}` and minimum cosine
`∈ {0.50,0.60,0.70,0.80,0.90,0.95,0.99,0.999999}`. Tune candidates require at least two stops and
zero harmful stops. Selection maximizes contacts saved, then prefers larger `k`, then larger minimum
cosine. The separate 30% discovery support gate requires zero harmful stops and at least
`max(2, ceil(10% × gate_n))` stops.

## Boundaries unchanged from v1

DEV-100 round 4 is the only discovery source. The exact 70/30 whole-utterance assignment uses seed
20260901, matching v1. A self-hashed v2 policy must pass and be committed before the separate holdout
command can open DEV-500-NEW400. A failed support gate leaves NEW400 unread. Repeated utterance
groups are excluded from holdout evaluation.

The holdout gate remains conjunctive: at least 100 eligible dispatched trajectories, zero harmful
stops, non-decreasing `scenario_action_exact`, paired CI90 lower bound at least zero, and at least 10%
evidence-contact savings. Extraction and contact metrics remain mandatory secondaries.

The baseline policy, knowledge snapshot, dispatch set, actions, reward, scorer, uncertainty,
utterance isolation, and claim boundary do not change. V2 never widens dispatch or imputes an
unlogged response. It introduces no parameter training and no second answering model.

## Hard stop

Zero model, embedding, tokenizer, HTTP, socket, audio, or GPU contact is authorized. DEV-1000-
NEW500, FINAL60, SLURP test, and future turns remain untouched. No v1 threshold is relaxed, and no
sample expansion occurs unless v2 first produces a zero-harm discovery gain.
