# Training-free route memory v3 — preregistration

Date: 2026-09-01. Status: **REGISTERED BEFORE V3 ROUTE-STATE REPLAY**. Experiment:
`SAEA-SN-MF-TFRL-ROUTE-MEMORY-V3`.

## Why v3 exists

V2 improved the safety frontier but failed its fixed support-coverage gate. Its selected one-neighbor
rule at cosine 0.95 saved three of 26 tuning contacts and one of 11 support contacts with no lost
answers. The support fold required two stops. At cosine 0.90 the rule gained one more tuning stop but
lost one correct answer; at 0.99 it stopped nowhere. NEW400 remained unread.

Query similarity can join trajectories whose evidence conflicts with their direct answer in
different ways. V3 adds that conflict topology as one runtime-visible route class. No result field,
gold field, reference transcript, evidence response, sample identity, speaker identity, or future
turn enters the state.

## Frozen route-conditioned controller

Before the evidence response is requested, the locked loop has both the parsed direct answer target
and the ordered fused evidence targets. Their relation is mapped exactly to one of five classes:

1. direct target unresolved;
2. direct target absent from the fused route;
3. direct target ranked first but still dispatched;
4. direct target is the fused runner-up; or
5. direct target is at rank three or lower.

For a baseline-dispatched trajectory, memory is first restricted to the same route class and to
different utterance groups. It is then ranked by the existing query-vector cosine. `STOP` is allowed
only when all top `k` neighbors clear the minimum cosine and all have observed
ACQUIRE-minus-STOP primary return at or below zero. Every other state defaults to `ACQUIRE`.

The grid remains the v2 grid: `k ∈ {1,3,5,7}` and minimum cosine
`∈ {0.50,0.60,0.70,0.80,0.90,0.95,0.99,0.999999}`. The locked v2 rule (`k=1`, cosine 0.95,
without route conditioning) is reported as a non-selectable comparator.

## Honest use of the adaptive DEV-100 surface

V1 and v2 exposed the former DEV-100 support fold. V3 therefore treats all 37 dispatched
trajectories as exploratory. It does not rename any subset as fresh support. Whole utterance groups
are assigned deterministically to five balanced folds with seed 20260902. Each trajectory is
evaluated only against memory in the other four folds.

A candidate clears the exploratory stability screen only if it has zero harmful stops in aggregate,
stops on at least `ceil(10% × 37) = 4` decisions, and stops at least once in at least three of the
five folds. Selection maximizes contacts saved, then prefers larger `k`, then larger minimum cosine.
These conditions authorize only freezing the controller for a genuinely untouched holdout read;
they are not independent validation and cannot support a superiority claim.

## Holdout and hard stop

A self-hashed v3 policy must pass the exploratory screen and be committed before a separate command
can open DEV-500-NEW400. Repeated utterance groups are excluded. The holdout gate remains
conjunctive: at least 100 eligible dispatched trajectories, zero harmful stops, non-decreasing
`scenario_action_exact`, paired CI90 lower bound at least zero, and at least 10% evidence-contact
savings. Extraction and contact metrics remain mandatory secondaries.

Zero model, embedding, tokenizer, HTTP, socket, audio, or GPU contact is authorized. The baseline
policy, knowledge bytes, scorer, action space, reward, default action, and no-imputation rule do not
change. DEV-1000-NEW500, FINAL60, SLURP test, and future turns remain untouched. A failed stability
screen leaves NEW400 closed, and no gate may be relaxed after reading the result.
