# Complete-system trajectory attribution: VAR-1 PLAN and PLANR

Status: post-hoc descriptive analysis, registered before this derived read.
All 625 R01C TRAIN construction utterances in each sealed arm are retained.
PLANR is the same-configuration repeat, not an independently sampled dataset.
No model, tokenizer, encoder, official scorer, server or network contact was added.

The new shared exporter verified both complete systems against their original
clean source commit 3ade29ffe2342ee65de47b6913990bd15fdcc24d, all request/response
and role identities, full terminal outputs, source flight/score custody, and the
complete official TRAIN per-sample counts. The attribution reader independently
verified the full source again and reproduced every delivered row's exact entity
TP/FP/FN and intent indicator from the governed offline labels.

## What the metric means

The intermediate diagnostic below is strict task exactness: the intent and
entire entity multiset must be correct. Entity type/filler equality is exact;
duplicates remain extra predictions. It is NOT official pooled SLU-F1, and a
24-25% strict full-answer rate must not be substituted for the official scores
58.5066% / 60.3755%. Intermediate outputs were not officially rescored.

First Solver to last Solver describes changes within an actual trajectory.
Last Solver to final delivery isolates the registered deterministic normalizer.
Neither is a counterfactual ablation of review: no claim is made that removing
the Reviewer would reproduce the original first Solver distribution.

## The observed trajectory

| Diagnostic, full 625-row population | PLAN | PLANR |
| --- | ---: | ---: |
| First Solver strictly incorrect | 481 | 478 |
| Rows with an actual subsequent Solver visit | 32 | 31 |
| Incorrect first drafts receiving that revision | 29 | 26 |
| Correct first drafts receiving that revision | 3 | 5 |
| Revision: fully repaired answers | 2 | 7 |
| Revision: newly incorrect answers | 2 | 4 |
| Revision repairs retained in final delivery | 2 / 2 | 7 / 7 |
| Delivery normalization: fully repaired answers | 9 | 9 |
| Delivery normalization: newly incorrect answers | 1 | 1 |
| First Solver to final: repairs / harms | 11 / 3 | 16 / 5 |
| Final strictly correct answers | 152 | 158 |
| Final wrong answers without a Solver revision | 444 | 444 |
| Final uncovered-intent errors without revision | 119 | 128 |
| Final covered-intent errors without revision | 50 | 52 |
| Empty-target false-positive rows without revision | 106 | 107 |
| Gold-empty rows, all | 191 | 191 |
| Gold-empty rows emitting entities, final | 114 | 115 |

Only 29/481 (6.03%) and 26/478 (5.44%) of initially wrong strict answers
received an actual revision. This is the reach of the executed repair path, not
the recall of an independently measured Reviewer classifier. Review may identify
a problem without causing the Planner to revise; the existing free-text outputs
do not justify silently inferring a typed issue label.

The owner's local-to-system concern is the correct optimization question, but
these data do not show successful complete repairs disappearing downstream:
all nine observed complete reasoning repairs survived delivery. The measured
bottleneck here is low repair reach, weak repair success, and new harms offsetting
repairs. More node calls alone have no demonstrated answer to that bottleneck.

The two runs share 133 strictly correct rows and 448 strictly wrong rows; 44 flip.
These are descriptive repeated-construction classes, not runtime features,
independent replications, significance tests, or evidence of fresh generalization.

## Actual information and instruction interfaces

| Request/source fact | PLAN | PLANR |
| --- | ---: | ---: |
| First Reviewer receives same evidence IDs as first Solver | 625 / 625 | 625 / 625 |
| First Reviewer receives same speech packet as first Solver | 625 / 625 | 625 / 625 |
| Reviewer model requests | 657 | 656 |
| Reviewer requests exposing a tool schema | 0 | 0 |
| Reviewer requests retaining mandatory task-contract call instruction | 657 | 656 |

The frozen Reviewer instruction says to call the available task-contract tool
exactly once, while the flown tool-free configuration exposes no such tool.
PLAN's count was also checked directly against non-state instruction entries in
the sealed request history. This is an actual instruction/capability mismatch,
not merely a stale template on disk. It does not quantify its task-quality effect.

The same evidence IDs and speech do not prove that both roles reason identically
or that the Reviewer adds no value. They do show that this arm supplies no new
external evidence through review or a tool. Runtime evidence *delivery* is
observable; semantic evidence *use* remains a separate question.

Do not automatically re-enable the old task-contract tool: the 2026-09-17 node
context audit found that its result repeats the already-present task contract.
A new tool or acquisition action must provide a named missing piece of evidence.

## Earlier evidence that constrains the next design

- R-PRIM on Fold A made 1,091 Reviewer visits parseable, but produced ACCEPT on
  98.4% of visits. Its registered wrong-row recall was 0.017. That is a different
  roster and measurement; do not pool it with the reach numbers above.
- B8b slot-audit context moved pooled SLU-F1 by +0.8698 pp with CI95 crossing zero.
  An audit block by itself is not an established system improvement.
- B7a context policy L1 did not qualify; its historical HARMFUL verdict and blocked
  L2 successor remain unchanged. Do not relaunch the same filtering as a renamed fix.
- B9a-rec acquired zero items on all 18 ACQUIRE rows because the production binding
  reran prepared Solver supply and excluded exactly that supply. A routed node
  without new evidence was not an effective acquisition experiment.
- VERIFY-1's current full answer-selector benefit remains unproven. This report
  authorizes neither more five-way sampling nor automatic selector deployment.

Sources: the corresponding committed verdicts under docs/results and the
2026-09-17-slurp-node-context-audit-v1.md structural audit. Their original
registrations, statuses and claim boundaries remain in force.

## Root decision and next system experiment boundary

Keep the four-node system and F10 running unchanged. Retain finite supply
selection only as a restricted algorithm comparator.

Prepare a small *complete policy* space whose interventions connect an identified
evidence deficit to an action and its downstream consumption:

1. Candidate recovery must deliver genuinely additional discriminating evidence
   and allow a corresponding candidate/state update before final selection.
   Detecting a missing candidate while still forcing the Solver to choose the old
   candidate set is an incomplete system action.
2. Entity repair must bind the disputed field to original speech and applicable
   slot meaning, positive and empty/counterexample evidence. The Reviewer reports
   the issue and supporting source IDs; the Planner chooses a scoped action;
   the Solver retains answer authority and consumes that evidence in its revision.
3. An observation tool is admitted only if its pinned local implementation supplies
   new relevant evidence on demand. An ASR hypothesis may help lexical ambiguity,
   but cannot by itself settle annotation-specific slot scope or empty-entity rules.
4. Normalize handoff into supported issue, evidence, unresolved question and repair
   target; do not mechanically add another free-text critique or revive old L1.
   Make instructions consistent with actual tool authority across the new group.

Before any such GPU family, prove the information change on the whole prepared
roster: new evidence survives duplicate exclusion, provenance is intact, no target
gold enters the actor state, and the next node can actually consume the result.
An empty acquisition is recorded as empty, never as successful information gain.

Sample full trajectories under a few coherent executable policies, preserve all
terminal outcomes, update external policy/memory only after complete feedback,
then execute the updated policy again. Compare against the locked system and
strongest fixed complete policy, with matched replication before stable-gain
claims. Novelty must be in a specified sampling/credit/update algorithm; manual
interface correction and this diagnostic are engineering/research preparation.

No new GPU family, closed-family reopening or learned policy is admitted by this
report. The next design must state how it differs from B7a, B8b, B9a and R-PRIM,
instead of repeating their already-measured interventions.

## All scenario strata

Entries are counts. R/H means strict complete-answer repairs/new harms.
The natural-mixture final strict task-exact rates are 24.32% and 25.28%;
equal-scenario rates are 25.4039% and 26.4894%. No confidence interval or efficacy
decision is assigned to these post-hoc diagnostics.

| Scenario | n | PLAN revised | PLAN revision R/H | PLAN delivery R/H | PLAN final exact | PLANR revised | PLANR revision R/H | PLANR delivery R/H | PLANR final exact |
| --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- | ---: |
| alarm | 26 | 1 | 0/0 | 0/0 | 13 | 3 | 0/1 | 0/0 | 11 |
| audio | 30 | 0 | 0/0 | 0/0 | 14 | 2 | 1/1 | 0/0 | 17 |
| calendar | 42 | 3 | 0/0 | 1/0 | 6 | 1 | 0/0 | 1/0 | 6 |
| cooking | 31 | 1 | 0/0 | 0/0 | 10 | 1 | 0/0 | 0/0 | 11 |
| datetime | 39 | 3 | 0/0 | 3/1 | 9 | 0 | 0/0 | 3/1 | 10 |
| email | 33 | 1 | 0/1 | 0/0 | 7 | 3 | 1/0 | 0/0 | 8 |
| general | 42 | 7 | 1/0 | 0/0 | 5 | 3 | 0/0 | 0/0 | 2 |
| iot | 33 | 1 | 0/0 | 0/0 | 9 | 3 | 1/1 | 0/0 | 10 |
| lists | 37 | 4 | 1/0 | 0/0 | 15 | 2 | 1/1 | 0/0 | 13 |
| music | 27 | 2 | 0/1 | 2/0 | 9 | 1 | 0/0 | 1/0 | 12 |
| news | 36 | 1 | 0/0 | 0/0 | 6 | 4 | 1/0 | 0/0 | 7 |
| play | 37 | 1 | 0/0 | 2/0 | 5 | 1 | 0/0 | 3/0 | 6 |
| qa | 38 | 4 | 0/0 | 0/0 | 6 | 4 | 2/0 | 0/0 | 8 |
| recommendation | 29 | 2 | 0/0 | 0/0 | 8 | 1 | 0/0 | 0/0 | 6 |
| social | 35 | 0 | 0/0 | 0/0 | 8 | 0 | 0/0 | 0/0 | 7 |
| takeaway | 37 | 0 | 0/0 | 0/0 | 7 | 1 | 0/0 | 0/0 | 8 |
| transport | 32 | 1 | 0/0 | 1/0 | 7 | 1 | 0/0 | 1/0 | 8 |
| weather | 41 | 0 | 0/0 | 0/0 | 8 | 0 | 0/0 | 0/0 | 8 |

## Reproduction and source artifacts

Registration: docs/readiness/2026-09-25-stage3-system-trajectory-read-v1.json.
Shared engine: analysis.slurp_system_attribution. Entry:
scripts/analysis/slurp_system_trajectory_read.py. Read the two complete original
sources from a clean checkout at 3ade29ffe2342ee65de47b6913990bd15fdcc24d;
the entry itself runs from the current analysis checkout with explicit PYTHONPATH.
No editable install or active-flight modification is needed.

External directory:
$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-SYSTEM-TRAJECTORY-READ-V1/

| File | Raw SHA-256 |
| --- | --- |
| plan-system-feedback.json | 80d53a8f4728bccf4b932ffc1ae8a2e98ae05eb1f73acd343f1d60f0835537f1 |
| planr-system-feedback.json | 2fcbe5e92771c752ef5fb986736a1089644a884cb315e27d5be5137487ef8f0b |
| attribution.json | 494ae8788e41d741960e7bf5b5bce30dc37fd742cb04361c8de2f210da9a3db5 |
| cross-node-summary.json | cfb44d1fd6a77ccb3476cb64d1df1459531ebc572630897e9e67b0865ed3bb44 |

The last file is the pure cross_node_summary projection of attribution.json,
carrying that source pin. Reports contain IDs, labels, counts, booleans and hashes,
not raw answer, transcript, utterance or entity filler text.
