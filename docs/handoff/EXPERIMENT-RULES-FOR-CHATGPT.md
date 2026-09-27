# Experiment rules for the ChatGPT side

Written 2026-09-27 under owner decision 166 ("state our experiment rules explicitly to him in the handoff
document"). Binding for every cell either side registers from 2026-09-27. Where this file and the owner-decision
registry (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`) disagree, the registry wins; the
measurement instrument (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`) is binding for every
Stage-3 claim. The re-read of past verdicts under these rules, yours and the coordinator's, is
`docs/results/2026-09-27-verdict-reclassification.md`: most of your session's results stand (11 of 12 items KEEP),
and the coordinator's own record carries 8 of the 11 items that had to be adjusted.

Each rule gives the rule, the gate that enforces it (or says plainly that none does), and the incident that
produced it. A gate on a branch that is not merged yet is named with its branch.

## A. Measurement

**A1. Fly an in-chain A/A for every cross-flight design.** A cell that compares two flights also flies a
request-identical replicate of its comparator in the same chain, and reads its arm against that replicate.
Never read an arm against an older sealed comparator alone.
Gate: `scripts/checks/stage3_effect_floor_check.py` refuses the design `cross-flight-no-replicate` and requires
`replicate_run_id` for `cross-flight-with-in-chain-replicate`.
Incident: VAR-1's PLAN and PLANR are request-identical and differ by +1.87 pp SLU, CI95 [+0.41, +3.36], while
intent moves -1.28 pp. Your VAR-1 read found this: K10 and K30 were +1.94 / +1.95 over PLAN and +0.07 / +0.09 over
PLANR. The coordinator's B0, B7a v2, B4a v2 and CELL-3 were read HARMFUL on effects inside that band and are now
re-read as not distinguishable from flight variance.

**A2. Know the floor before you register, and declare it.** Every Stage-3 cell carries a top-level
`stage3_measurement` block (`measurement_design`, `expected_effect_pp`, `rows`, `primary_metric`,
`claims_benefit`, and `replicate_run_id` or `admission` / `harm_margin_pp` where they apply). The floors:

| design | n | CI95 half-width (SLU) | offset it carries |
| --- | ---: | ---: | --- |
| offline read over one sealed sample pool | 625 | 0.67 | none |
| two passes inside one flight | 200 | 0.735 (intent 0.000) | none |
| cross-flight A/A, R01C | 625 | 1.474 (intent 1.760) | +1.87 measured |
| cross-flight A/A, TRAIN Fold A | 1,080 | 1.2485 (intent 0.9943) | +0.17 measured |
| cross-flight A/A, DEV-2000-ADDED | 1,000 | 1.2525 (intent 1.1520) | -0.25 measured |

A cross-flight gain is admitted only when its CI95 lower bound is above zero AND the delta exceeds the in-chain
replicate's measured offset plus that offset's half-width: about 3 pp at n = 625 and 2.5 pp at n = 1,080 (rule 3
of the instrument). Two identical flights of the locked plan disagree on intent on 27-33 of 1,080 rows, about 15
saves and 15 harms for a no-op arm; judge saves and harms against that.
Gate: `scripts/checks/stage3_effect_floor_check.py` refuses a cell whose `expected_effect_pp` is under its design's
floor (blocking for cells registered from 2026-09-27).
Incident: nine Stage-3 mechanism families flew before this law and none could have seen an effect of the size it
produced (instrument section 1).

**A3. Prefer, in this order: an offline read over a sealed pool, a same-flight paired design, a cross-flight
design with its A/A.** Any selection, commit, projection, verification, re-ranking or scoring rule is read
offline over already-sealed samples first, at zero GPU. The same-flight `supply_variants` path needs an owner
re-authorisation, and `core/bundle/outputs.py` must learn `supply_variants` before any interleaved number is
reported.
Gate: the floor check ranks the designs by floor; no gate forces the order.
Incident: VERIFY-1 (yours) and the aggregation read are the only Stage-3 reads that cleared their own design's
floor, and both were read over sealed samples. VAR-2 closed without a number after its sole recovery hit the
cumulative supply bound.

**A4. Treat a batch under 200 rows as a form proof.** It proves the path runs; it never supports a benefit, a
harm or a policy update. Terminal feedback on 4-16 trajectories is not readable.
Gate: `stage3_effect_floor_check.py` (`MIN_BENEFIT_ROWS = 200`; `claims_benefit` must be false below it).
Incident: memory batch002 (4 inputs x 4 trajectories); its one-draw 59.78 -> 53.53 cannot be read either way. You
recorded it without an efficacy claim, which is correct.

**A5. Never decide on a stratum.** Report the per-stratum table beside every verdict, in both weightings (natural
mixture and equal stratum), and decide on the pooled number only. A 60-row scenario stratum has a bar near
9.7 pp; the DEV-1000 byte-identical re-flight moved per-scenario intent by -5.13 to +5.41 with nothing changed.
Gate: the study guide's reporting rule ("every verdict carries the per-stratum table"); the standard paired read
driver `scripts/analysis/stage3_paired_read.py` (branch `fable/launchgate`) emits both weightings. No gate refuses
a stratum-based decision.
Incident: owner decision 110 was built on CELL-2's per-scenario "content gains" (+7 to +15 pp), and the cell it
designed read -1.44 inside its own replicate's band; the silence tail was barred as HARMFUL because 5 of 18
scenarios lost.

**A6. Call a result HARMFUL only on a measured loss beyond the floor.** A non-inferiority test that fails because
the interval is wide reads NEUTRAL with "non-inferiority not proven". An engineering-base item is admitted on
no harm and is never reported as a gain (owner decision 127): declare `admission: no-harm` with a `harm_margin_pp`
no tighter than its design's sampling half-width.
Gate: owner decision 25 (method B) for combination cells; `stage3_effect_floor_check.py` enforces the no-harm
declaration shape. No gate reads a verdict's status word.
Incident: B0, B0r, B7a v2 and B4a v2 were recorded HARMFUL with every point estimate between -0.70 and +0.74 pp.

**A7. Use the carrier's own null; never import a margin; never use a point-estimate guard.** A "not worse" guard
is a non-inferiority test whose margin is the half-width of the carrier's own same-request null. A point estimate
below zero is not a failed guard, and an effect inside the own null is not an admission.
Gate: the results ledger's family rule (owner, 2026-09-08); not machine-enforced.
Incident: the SLURP silence tail failed an imported 0.60 pp scenario margin (SLURP's own is 0.8255); the Codex
session refused G6, the Earnings-21 offline system and the Audio2Tool role base on point guards (scenario -0.2;
+5 insertions of 10,336; tool accuracy), and admitted an Earnings-21 refresh whose WER gain (0.0056 pp) was a tenth
of the own null (0.058). Audio2Tool still has no own null: A2T-AA (decision 144) supplies it.

**A8. Pick the primary metric by what the mechanism acts on.** A mechanism that acts on intent reads intent
accuracy as primary and official SLU-F1 as the non-inferiority guard (owner decision 133). Otherwise decision 115's
rule holds: official SLU-F1 primary with its CI95 lower bound above zero, intent non-inferior at the own null,
replicated on a fresh roster, one test read.
Gate: `primary_metric` in the `stage3_measurement` block (reported, not enforced).
Incident: the AGREE arm was re-declared on intent before it flew (decisions 133 and 143) because official SLU-F1 is
entity-only.

## B. Registration and custody

**B1. Register before contact, and record every contact before reading its result.** The exposure-ledger row must
match the `ExecutionPlan` field by field (profile, split role, split identity hash, budgets) and read
`consumed = no`.
Gate: `contracts.gate_exposure._require_exposure_preregistration` and `contracts.assert_execution_scope` refuse at
runtime, fail-closed.
Incident: VERIFY-1's first run registered the live-phase fit count as its generation ceiling and opened no
attempt; it needed one named recovery.

**B2. Countersign every flight row and register the READ row before launch.** A draft row never authorises
contact; the analysis recipe declares its READ run id and that id has its own ledger row before the flight.
Gate: `scripts/checks/flight_registration_check.py` (branch `fable/launchgate`), run by the batch driver's
`prelaunch` step for every queue step.
Incident: ROLL-3's flight rows flew while still marked draft; the READ rows of AGREE, KPROBE and ROLL-3 were
registered after the seal.

**B3. Take no disposition on an unread result.** Do not pre-commit "if the number is X, do Y" (owner decision
139). The number is read, then discussed, then ruled on as a numbered decision.
Gate: none; the registry is the record.
Incident: a fallback for the AGREE arm was pre-committed on the CONV probe's count before it was read (decision
139); decision 32 had pre-committed the closure of the L1 family on B7a v2's verdict.

**B4. One recovery per flight.** A second failure stops the flight; the fix is proven on a four-row dry run;
never splice, partially score, or rename a retry as a new experiment.
Gate: the study guide's iteration rule and the runtime's one-recovery semantics.
Incident: VAR-2 (closed without a number after its sole recovery; you followed this rule) and the typed-context
package (closed after its second failure).

**B5. Keep construction on TRAIN and never on the roster you read.** No gold of an evaluation roster (TRAIN Fold A,
DEV-2000-ADDED, the test sample) enters construction, tuning or the choice of a setting; a roster used to choose a
setting is not the roster that reads it.
Gates: `contracts.gate_exposure._require_construction_role_for_visible_targets` (gold crosses to the core only on
a construction roster); the BUILD/USE guard in `rails/knowledge_provider.py` (a store whose sources overlap the
use roster is refused); `contracts.gate_exposure._require_final_report_disjointness` for the test rosters. Nothing
checks an offline diagnostic that reads gold to pick a weight.
Incident: the first construction roster R01 contained 175 utterances that were sources of the authored stores
(decision 102, replaced by R01C); AGREE's weight grid was chosen by a diagnostic over Fold A gold and then read on
Fold A, so its replication on DEV-2000-ADDED is owed (decision 161); CELL-3's gate was chosen on Fold A, so it was
read on DEV (decision 110).

**B6. Read the test split once, and not before a fresh-roster gain exists.** Decisions 99, 107, 108, 115, 141,
151 and 156 govern the test sample and its preparations.
Gates: the final-report gates in `contracts/gate_exposure.py` (disjointness, attempt budget, isolation).
Incident: none; keep it that way.

**B7. Declare the native-episode policies and the algorithm label.** Every live native cell declares
`native_episode.finite_completion_policy = "deliver-latest-or-abstain"` and
`native_episode.react_exhaustion_policy = "continue-without-answer"`; every Stage-3 cell carries a
`stage3_algorithm` label that resolves in `core.base.STAGE3_ALGORITHMS` (decision 101). One base, thin
derivations; the direct baseline runs through the same controller and runtime.
Gates: `finite_completion_policy_check.py`, `stage3_algorithm_label_check.py`, `engineering_base_check.py`.
Incident: B7a lost 1,451 contacts and B8b-anchor 2,016 to the parser defaults.

## C. Serving and the GPU

**C1. Swap the serving geometry only with the one swap tool, one swap at a time.** Never run the WSL half and the
Windows scheduled-task half of a switch separately, and never run two switches in parallel.
Gate: `scripts/flights/batch/serving_swap.sh`: a lock, precise flight detection, a
host-memory pre-check before anything is stopped, and restore of the previous geometry on failure.
Incident: on 2026-09-27 the two halves of a switch were run separately, and one ran while the other refused.

**C2. Start the serving geometry before any CPU sidecar; run sidecars only inside long resident flights** (owner
decision 162).
Gate: the swap tool's pending marker refuses sidecar launches for the duration of a swap (`serving_lib.sh`).
Incident: with a resident sidecar holding host memory, 11.7 GB and 10.1 GB free failed two serving restarts after
the running geometry had already been stopped; about 130 GPU minutes of 2026-09-27 were lost this way.

**C3. Fly GPU cells only through the scheduled batch driver, and stop only what you started.** Every GPU flight is
launched by the Windows scheduled tasks (serving, monitor, batch driver) from the queue file, never from an
interactive session (owner decision 77). Never kill processes by an unscoped pattern; stop the recorded session
through `scripts/serving_session.sh`.
Gate: `scripts/flights/batch/batch_driver.sh` with its `prelaunch` gate.
Incident: 2026-09-22, a serving entry's unscoped `pgrep -f 'llama-server --host'` reaper killed the CPU-only R01
preprocess sidecar during a geometry switch (72 encode contacts succeeded, 728 failed, and the run failed).

**C4. Leave the host settings alone.** No power, driver, TDR or WSL-cap change as a throughput measure (owner
decision 117, recorded from your session).
Gate: none.

## D. Repository and records

**D1. One agent per worktree.** Work in your own worktree under `/home/chao/saea-worktrees/`, commit on your own
branch, and let the coordinator merge serially; never merge into master while a flight is running there.
Gate: none beyond the dirty-tree refusal below.
Incident: 2026-09-17 (the B1 smoke), two processes sourcing an env script that created the flight worktree on demand raced one checkout, and the worker read the half-populated tree as staged deletions.

**D2. Never `git add -A` and never `git stash`.** Add explicit paths; write multi-line commit messages to a file
and commit with `-F`.
Gate: none.
Incident: 2026-09-05, two agents in different worktrees stashed and popped from the one stash stack every worktree
shares and swapped each other's changes.

**D3. Leave the tree clean when you stop.** Commit or remove your work; untracked files count as dirt.
Gate: `core.flight.cli check` refuses a dirty tree, and a COMPLETED manifest reads `study_commit` at finalize.
Incident: your per-group knowledge-proposal work was left uncommitted in the shared tree on 2026-09-26 and had to be
landed unchanged (`15c13a00`) before a flight could check.

**D4. Write English.** Every document, comment and record is English; translate any non-English source before it
enters a model context and keep the source addressable.
Gate: none in this repository (the study guide's first principles; the umbrella's
`scripts/checks/ai_context_surface_check.py` covers the umbrella surface).

**D5. The owner-decision registry is the single source of rulings.** Record every owner ruling as a numbered row
of `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, the owner's words plus an English
translation; a design note may quote a row and never replaces it.
Gate: none.
Incident: rulings of 2026-09-25 and 2026-09-26 were recorded only in design notes and were re-entered as rows
115-125 (`2e6274eb`).

**D6. Record every result in the results ledger, both halves, and refresh the handoff in place.** A verdict or
read lands with its row in `docs/results/stage2-results-ledger.md` and `.json`; the handoff file is rewritten in
place after every landed result.
Gates: `scripts/checks/results_ledger_check.py`, `scripts/checks/handoff_freshness_check.py`.
Incident: the machine-readable ledger stopped at 2026-09-09 while Stage 3 ran (its Stage-3 rows were added on
2026-09-26), and five cells of 2026-09-25 (VAR-1, VAR-2, VERIFY-1, F10, the evidence path) had to be closed in the
records afterwards (`a88798c2`).

## E. Standing boundaries

The study guide's research boundary is unchanged: human speech only; the frozen core reached only across the
service boundary; zero parameter training; no second answering model; gold, reference transcripts and future turns
never enter runtime; zero paid API spend; paper-scale work belongs to a separately admitted paper repository.
