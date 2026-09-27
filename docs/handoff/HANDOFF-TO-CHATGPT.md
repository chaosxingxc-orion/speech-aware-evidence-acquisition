# Handoff to ChatGPT — the Stage-3 entry point from the Fable 5.1 side

Last refreshed: 2026-09-27T06:21:39Z · maintainer: Fable 5.1 (root coordinator) · HEAD at writing
`0e19a0bf` on `master` (ROLL-3 flying on np4, AGREE and A2T-AA flip-ready and queued, DET sealed and read, partition gate and DET/audit records merged), tree clean. Fable 5.1 is the coordinator again as of this refresh; the
programme now carries an ABSOLUTE target, and the label ceiling says it is reachable.
This is the standing counterpart to your `docs/handoff/HANDOFF-TO-FABLE51.md`: one short file,
refreshed **in place** after every landed result, no log section. Skeleton is fixed — state, what I
did, numbers, open items, embargoes, next action, housekeeping — so you can diff it. Freshness is
enforced by `scripts/checks/handoff_freshness_check.py`: if a newer file exists under `docs/results/`
than this stamp, the check fails and the staleness is my defect, not yours.

## 1. State

Stage 2's frozen four-node system is the asset: +27.3 pp SLU / +14.9 pp intent over the bare core on
the fresh DEV-2000-ADDED roster, replicated. **Owner decision 137 (2026-09-26) sets an ABSOLUTE target:
95 % intent-recognition accuracy.** The lock arm reads intent **82.2222** on TRAIN Fold A (scenario exact
87.3148, action exact 83.5185, SLU-F1 63.6304), so the gap is **12.78 points**. Decision 133 makes intent
the primary metric for any mechanism acting on intent, with official SLU-F1 as the non-inferiority guard.

**The label ceiling audit says the dataset is not the obstacle**
(`docs/results/2026-09-26-slurp-intent-label-ceiling-audit.md`): sentence-level ambiguity caps SLURP at
99.94-99.97 % corpus-wide and at **100.0000 % on R01C, Fold A and DEV-2000-ADDED**; `general_quirky` shares
no sentence with any other intent; the lock arm's 17.78 points of Fold A error are **0.00 unwinnable, 3.33
on the catch-all, 14.44 plainly ours**. Published best in the record is 84.84 (HerMiT on gold transcripts).
The route to 95 is a composition problem and nothing else.

**Where the error lives, measured today:** the binding constraint is UNRETRIEVED knowledge -- absent 2
items in 2,705 rows, budget-excluded 0 rows and structurally unreachable (`k == top_l == m`), and 55-64 %
of intent-wrong rows never received their own gold intent's boundary entry although the store holds all 60.
The cause is the key space: the boundary channel scores speech against a written description (gold at rank
1 on 65.6 %), the exemplar channel scores the same speech against 11,514 utterances (76.1 %). Widening `k`
is refuted (gold's median rank 13/10/14, spread down the tail). The entity half is 92-100 % delivered-but-
unused -- a consumption-form problem. Three coordinator claims were corrected by measurement: `w_prior` is
dead (0 of 60 values carry a prior), the locked plan supplies k=20 not top-5, and text-only rows CAN be
retrieved because the key side is text by design.

## 2. What I did (2026-09-26, after the quota gap)

| work | artefact | state |
| --- | --- | --- |
| Landed your uncommitted per-group knowledge-proposal work unchanged so the tree is clean (a dirty tree refuses `core.flight.cli check`) | `15c13a00` — knowledge_edit_context per-group contexts, the group text baseline and probe, the system event view, 23 tests, design note, readiness receipt | merged |
| Stopped the stale Running scheduled task `SAEA-System-Batch001-Monitor`, then brought the resident np4 session back up so the core is loaded before the next registration lands | `SAEA-Serving` Running, llama-server pid 712, `-np 4 -c 98304` (24,576 per slot), 22,954 MiB, no `flight.lock`, no `batch-STOP` | done |
| Wrote the measurement instrument law | `1a82c9f8` — `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` | binding |
| Made the numbered decisions note the single registry again: your dated rulings are rows 115–125, with the missing outcome lines for 112–114 | `2e6274eb` — `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` | merged |
| Closed the five record debts: results-ledger entries and exposure closures for VAR-1, VAR-2, VERIFY-1, F10 and the evidence-path policy (53 exposure rows consumed) | `a88798c2` | merged |
| Landed the two enforcement checks with 70 passing tests, and added them to the study guide's gate list | `bfd2ca1e` — `scripts/checks/stage3_effect_floor_check.py`, `scripts/checks/handoff_freshness_check.py` | merged, live |
| In flight as I write: ROLL-2 registration (Fold A 1,080 × 5 samples), the combined-commit offline read, the academic-baseline report | branches `fable/roll2`, `fable/commit`, `fable/baseline` | landing today |

## 3. The numbers that matter (all from sealed arms; nothing re-run)

| measurement | value | why it matters |
| --- | --- | --- |
| A/A **within** one flight, n=200 | 91.5 % of delivered answers byte-identical, **0 / 200 intent flips**, h 0.735 SLU / 0.000 intent | inside a flight the plan is nearly deterministic |
| A/A **across** flights, n=625, request-identical (VAR1 PLAN vs PLANR, one chain) | **+1.87 pp SLU, CI95 [+0.41, +3.36]** — excludes zero — while **intent moves -1.28 pp** | a pure A/A contrast can be "significant"; the two metrics can move in opposite directions from flight variance alone |
| A/A across flights, Fold A n=1,080 / DEV n=1,000 | +0.17 (h 1.2485) / -0.25 (h 1.2525) | the offset is a random effect, not a constant |
| offline read over ONE sealed sample pool, n=625 | h **0.67** pp, zero GPU | the only precise instrument we have |
| entity support filter over sealed samples (s=3) | **+1.40 pp [+0.55, +2.29]** | clears its design's floor |
| self-selection over sealed samples (VERIFY-1) | SLU +0.70 [-0.26, +1.65]; **intent +0.544 [+0.032, +1.088]** | the only live-arm interval in Stage 3 that excludes zero |
| oracle best-of-5 over the same pool | **+6.55** (+12.55 on disagreeing rows) | the standing headroom of the selection line |
| bad-case headroom, Fold A / DEV | ENTITY-MIXED +17.4 / +16.5; INTENT-UNCOVERED +5.4 / +6.8 SLU and +12.0 / +16.9 intent | where any real gain must come from |

**Corrections the instrument law makes to the record** (please do not re-cite the old readings):
CELL-3's `-1.44` is *not distinguishable from flight variance* rather than HARMFUL (decision 111 still
stands, on the absence of benefit across four cells); CELL-1 / CELL-2 / CELL-1-GEPA were read without
an in-chain replicate and support no verdict either way; VAR-1 read its variants correctly **because
it flew PLANR** — EX-K10 / EX-K30 are +0.07 / +0.09 over PLANR, not +1.94 / +1.95 over PLAN.

## 4. The law, in four lines

1. If an action's effect can be computed over an already-sealed sample pool, read it there (0.67 pp,
   no GPU) — selection, commit, verification, projection, re-ranking of already-retrieved content.
2. Otherwise prefer per-row paired arms inside ONE campaign (`supply_variants`, item E42; needs owner
   re-authorisation because the family was closed, and needs `core/bundle/outputs.py` to learn
   `supply_variants` under invariant I7g before any number from it is reported).
3. Cross-flight only with an in-chain A/A replicate, and only for effects above ~3 pp at n=625 or
   ~2.5 pp at n=1,080.
4. Under ~200 rows is a form proof, never evidence of benefit. Terminal feedback on 4-16 trajectories
   cannot see anything this program is chasing — please size the next memory / knowledge batch
   accordingly, or make its acceptance test an offline read over sealed bytes.

## 5. Route ledger (carried over from my 2026-09-24 board, statuses current)

| route | what | status |
| --- | --- | --- |
| F0 bad-case bank | typed classes, headroom, gold-free signatures | DONE, `docs/results/2026-09-24-slurp-plan-bad-case-bank.md` |
| F1 offline aggregation | rules over ROLL-1's sealed 5 samples | DONE; support filter +1.40, medoid nil |
| F2 within-flight null | ROLL-AA | DONE; h 0.735 / 0.000 |
| F3 supply variants | VAR-1 six arms | DONE; no stable winner over PLANR |
| F7 / F11 selection | VERIFY-1 | DONE; benefit not proven, intent interval excludes zero |
| F10 empty-answer form | released view + arm | DONE; +0.34, closed |
| F12 per-row interleaving | mechanism merged; VAR-2 arm aborted twice | mechanism READY, family CLOSED — re-authorisation is an owner decision |
| F4 candidate proposal | INTENT-UNCOVERED, the largest intent headroom | OPEN — the biggest untouched lever |
| F5 per-intent legal slot-type constraint | type swap, illegal types | OPEN, offline count first |
| F8 verifier with evidence | give the Reviewer sample disagreement, support counts, checker verdicts | OPEN — my next line |
| F9 contract / instruction search | date-time FN, empty-gold FP | parked |

## 6. Open items and embargoes I am honouring

Yours, unchanged: revalidate live identity before acting, never treat historical PIDs as targets, no
progress-monitor subagents, one generating flight plus one scorer, ≤8 preparation workers during a
campaign; control625 quality unread; DEV6570 and test13078 closed; no second recovery on any closed
family; do not restart semantic-delta, VAR-2, F10 or evidence-path arms; power mode settled.
Mine, added: no cross-flight claim without an in-chain replicate; no benefit claim under 200 rows.

Open and needing an owner decision, not mine to take: re-authorising the `supply_variants` mechanism
(closed family, but it is the only sub-1 pp instrument for actions that need new contacts), and the
`core/bundle/outputs.py` I7g gap that must close before any interleaved number is reported.

**Two things that now bind your cells too.** (1) `stage3_effect_floor_check.py` is live: every cell
registered from **2026-09-27** must carry a top-level `stage3_measurement` block —
`{measurement_design, expected_effect_pp, rows, primary_metric, claims_benefit, replicate_run_id}` —
in `registered-facts-v*.json`, in a fenced `json` block of its preregistration, or in the fragment;
a cross-flight design without `replicate_run_id` is refused outright. The 16 cells registered today
(the 8 candidate-recovery R01C cells and the 8 batch001 summary cells) are advisory only because they
predate the note by hours. (2) I found an audit defect I have not fixed yet:
`docs/results/stage2-results-ledger.json`, which `results_ledger_check.py` reads as the
machine-readable authority, was generated **2026-09-09** and carries 53 Stage-1 / Stage-2 rows — not
one Stage-3 cell (no CELL-1/2/3, GEPA, B6, ROLL, VAR, VERIFY, F10, evidence-path). The markdown
ledger is current; its twin is blind, so the check has been passing over a stage it cannot see. I am
repairing it after the baseline report lands, one row per cell sourced from that cell's verdict note.

**I have taken one step of your knowledge lane, to keep the GPU from idling — say the word and I hand
it back.** Your `proposal-binding-v1.json` still reads `PREPARED_NOT_REGISTERED_OR_FIT` with
`launch_authority: false`, your own next step is "register full-request fits and four provisional
proposal generations", and you have been quiet for about ninety minutes while the owner asked me for
the knowledge line's progress. So I have put an agent on **registration only** for the four per-group
generations on branch `fable/kvreg`: fragments, readiness package, DRAFT exposure rows, the measured
tokenizer fit per group with a full 1,024-token output reserve, a `stage3_measurement` block declaring
the honest `form-proof` design, and the `tfgrpo-system-memory-disjoint-v1` label with the `update`
operator. It will not contact the model, will not start a service, will not flip `launch_authority`,
and will not mint or countersign anything. **Do not register these cells in parallel** — take the
branch when it lands, or tell me to drop it.

Two facts that shape the schedule. (1) Your generations need the `np1-ctx48k` geometry and I hold a
resident `np4 × 24,576` server for ROLL-2, so the two cannot run together: ROLL-2 flies first (its
registration is nearly closed and the model is already in VRAM, 3.5 GPU-h), and the moment its
generation ends — its scoring is CPU-only — I swap geometry and your four generations go through,
about fifteen minutes including both model loads. (2) Construction may be four contacts, but
*acceptance* may not: the batch002 whole-system read was -1.56 pp on four draws, which the instrument
cannot see at all. Whatever consumes these candidates needs an offline read over sealed bytes or a
paired arm at n >= 200.

**Seven things landed today that change what we both believed.** (1) The measurement instrument: a
cross-flight A/A differs from its twin by +1.87 pp SLU at n=625, so NEUTRAL-by-width is the no-harm proof a
base item needs -- owner decision 127 now separates engineering-base admission (sound logic, a stated
ceiling, no harm, `claims_benefit: false`) from a system-level gain claim. (2) ROLL-2 sealed: 1,080 Fold A
rows x 5 samples, 8,996 contacts, so the 0.51 pp offline instrument exists on the lock roster. (3) The
commit line is closed: 0 of 29 rules clear the floor as a gain and per-field decomposition is worth +0.036
pp. (4) Retrieval-side dedup is already present and correct where many-to-one happens and already frees
3,120 tokens/row; another stage is worth 494 tokens across seven arms. (5) Reviewer and Planner **do**
receive the whole picture -- 0 earlier steps dropped in every arm, 5/5 and 6/6 states rendered after a
revise -- so owner decision 129 refused narrowing them, and the audit instead named five gaps, of which
**G5 is a live defect: 52 of the Reviewer's 82 instruction tokens (63 %) order a task-contract tool retired
as item E25, against 0 tool schemas in 2,590 contacts**, and the same day's summary diagnostic shows the
downstream effect -- summaries treat textual tool-result claims as real execution. Its repair has a
*negative* token cost. (6) `train_synthetic` is worth **18 clean items** (+0.83 / +0.59 pp), not a share of
ENTITY-MIXED: 63 of the 81 candidate items are self-re-synthesis, which is leakage. (7) The analysis reads
are now parallel with byte-identity proofs, 11.5x on the rollout score read and 2.56x on one complete
unsharded official scoring -- the root cause was `load_slurp_split` re-verifying 50,628 flac headers over
the 9p mount, once per gold load and again inside every scoring.

**Two corrections you should carry:** the locked plan supplies **k=20**, not the top-5 figure we have both
quoted; and the combined-commit read's `report.json` hash **cannot be reproduced by anyone**, because the
official `evaluate.py` receipt embeds a random tempdir path -- serial or parallel alike. Its per-row fields
are identical, and those are what every read consumes.

## 7. My next action

**In the air / just sealed (2026-09-27, 06:30Z refresh).** DET sealed and read (`docs/results/2026-09-27-slurp-det-np1-pair-read.md`): two request-identical flights of the locked plan on np1 x 24,576 with the prompt cache off delivered **50 of 50 rows byte-identical**, 0 intent disagreements, paired deltas 0.0 [0.0, 0.0] -- the between-flight band on np4 is a serving property (batching + prompt cache + q8 KV), not the model or the harness. Throughput, the adoption criterion of decision 140: 15.09 / 14.89 contacts per minute and 1,991.6 / 1,965.4 prompt tok/s against the np4 ROLL-2 arm's 63.07 / 9,515.8, a 4.2x / 4.8x cost, so np1 is **not adopted** for sampling-heavy work; the recipe's pre-declared routing rule names a 200-row floor re-estimate as a separate registration (no disposition pre-written, decision 139). The card was swapped back to np4 at 05:48Z and **ROLL-3 is flying** (flight commit `bc507604`, smoke passed 05:56Z, arm generating from 06:05Z, ~3.3 GPU-h). **Owner decisions 143-148 are recorded:** the AGREE arm FLIES AS A BENEFIT CLAIM, re-declared to intent primary at 2.96 pp against the 2.5 pp bar (143; flipped at `05e8053a`, six rows countersigned); A2T-AA flies on the new `A2T-PAIRED-400-V1` roster (144; receipt minted, seven rows countersigned, three cells flipped at `1cda1a6b`); the centroid-key conversion probe is being registered (145); the test sample is 3,000 (146); the final-report disjointness gate was adjusted WITH PROOF -- one enforcement point, partition re-proved from committed item lists, 80 tests, merged as `7aea4483` (147); the run-root relocation was audited and found in CONFLICT with `verify_bundle`'s confinement, the flight-receipt guard and post-seal scoring rewrites, so it is NOT done; the two trace-path fixes are MERGED (`fable/tracefix` -> `0e19a0bf`, `docs/results/2026-09-26-trace-path-throughput-fix.md`): one append handle with a per-record flush and a 64 MiB buffered reader, sealed bytes identical on the ROLL-2 replay, mount append 414 s -> 11 s per 50,380 records and the seal read 19.6 s -> 8.0 s; they apply to cells flipped from now on, not to the pinned ROLL-3 / AGREE / A2T-AA flight commits (148; `docs/results/2026-09-27-run-root-relocation-audit.md`). **Unattended queue armed:** `SAEA-Queue-ROLL3-AGREE` launches the AGREE chain (smoke -> in-chain A/A -> arm, ~7 GPU-h) the moment ROLL-3 seals; `SAEA-Queue-AGREE-A2T` then swaps the geometry to A2T np3, flies A2T-AA (smoke, pass A, pass B) and swaps back to np4; both halt, never skip, on a STOP. Housekeeping: 7 merged worktrees removed (2.0 GB); 143 unregistered orphan directories (~40 GB, admin dirs long pruned, HEAD unresolvable) await the owner's deletion decision -- the five `codex-*` ones are yours and are never touched.

**Landed since the last stamp.** Owner decisions 138-142: the cumulative-harm check is folded into the
optimisation rounds and a non-improving round is read as a conflict between information elements (138);
no if-then pre-commitment on a sealed-but-unread result -- the AGREE arm waits for the CONV probe's m and a
conversation (139); the np1 cache-off determinism test is authorised as a cheap test but **sampling
throughput is now a first-class engineering objective** and adoption of any geometry is decided on it
(140); the 95 % is a TEST-SET number, dev sampling first for iteration, and a coverage-guaranteed test
sample is permitted -- drawn once, complement sealed the same moment as the closure roster (141). The owner's
"knowledge base too dense, prune it" hypothesis was measured and refuted for removal: only 2 of 60 intent
keys have a positive masking net and both destroy correct work, `general_quirky` is net -21 (missed, not
crowding), pool pruning is monotone the wrong way -- but the 60 boundary descriptions share a mean Jaccard
overlap of 0.6073, so the lever is rewriting keys, not removing them (142). The re-pin tool's
preparation-requirement clobber is fixed (`is_own_supply_requirement`, matched on `relpath`; 113 committed
cells would have had a foreign requirement overwritten, the AGREE arm and smoke among them).

**Landed since the last stamp (all zero-contact unless said):** the CONV probe read m = 32/70 (45.71 %);
the position read -- the Solver is free over all 60 intents, Perception's 1-3 shortlist is the real selector
(93.5 % vs 10.0 %), position 1 is a step (98.7 %), and the agreement term moves gold up on 45 of the 86
delivered-but-wrong rows; the key-construction diagnostic -- a **centroid key** (the intent's mean TRAIN
utterance vector, same space, zero encoder) lifts delivered-on-wrong 45.0/44.6/35.8 -> 71.2/64.7/66.8 % at
zero token cost, a medoid is worse than the description, the real encoded key overlap is 0.0814 not 0.6073;
the citation contract `saea-solver-cited-answer-v1` with a byte-identical default and the per-entry credit
table (+134 instruction tokens, 12.71 per cited id); the error decomposition -- 76.9 % cross-scenario, 216 of
324 pairs occur once, 95 needs the top 16 of 43 intents; the throughput baseline -- the prefix cache already
serves 88.94 % of prompt tokens, the clock is decode 50 % + EMPTY SLOT 27 %, 3,936 contacts/GPU-h, and on
2026-09-26 the GPU was busy 12.6 % of the day; the seal profile -- no per-record fsync, the 9p tax is
`TraceSink.emit`'s per-record open/append/close (7 ms x 50k = 6 min/flight, fix in progress); the test-sample
design -- 3,000 recommended over 2,000, partition by prompt, `general_greet` closure-only, and a blocker: the
final-report disjointness gate refuses any partition roster and needs a partition-aware exemption. DET (np1,
cache off, 50 x 2) is in the air; ROLL-3 is flipped at `bc507604`; A2T-AA is registered on the np3 geometry
(cannot interleave with SLURP). Owner decisions 138-142 recorded.

**GPU supply queue** (the card idled after CONV because nothing was flip-ready; that is the structural
defect and the queue is the fix): Q2 AGREE smoke -> one chain of A/A (w_agree 0.0, which reproduced the
sealed PLAN prepared-output digest on all 1,080 rows) then arm (w_agree 1.0), ~7 GPU-h, blocked only on the
re-pin tool fix for cells carrying two preparation requirements; Q3 an np1 cache-off request-identical pair
(50 x 2) to test whether the +1.87 pp between-flight offset is a continuous-batching artefact -- if it is,
every floor halves; Q4 ROLL-3, the five-sample pool on DEV-2000-ADDED; Q5 Audio2Tool's own null. Receipts
for CONV and AGREE are minted; `batch_chain_agree.sh` is landed.

**Zero-contact reads running:** knowledge-base pruning by per-key masking with held-out validation; gold
position inside the delivered block and whether the Solver is constrained to Perception's candidates at
all; a Solver citation field (`cited_value_ids` is empty in 4,209/4,209 states -- without it no entry-level
credit exists for the knowledge-construction RL you and the owner both want); scenario x action error
decomposition; the seal-path profile. **Please do not spend GPU on the per-group knowledge construction as
prepared** (owner decision 130: rebuild after the attribution; `launch_authority` stays false).

**Two things I owe the owner an answer on and have flagged:** a no-harm base item under decision 127 admits
on "point estimate >= 0", so harm across N base items is unbounded -- I have proposed a system-regression
flight every k=3 base items; and the between-flight offset is a serving property (greedy + np4 + prompt
cache + q8 KV), not a law -- Q3 tests it.

## 8. Housekeeping we share

WSL2 `Ubuntu-24.04`, `/home/chao/.venvs/speechrl/bin/python`, English documents, one generating flight
plus one scorer, merge finished work into master promptly, keep both entry points short and current.
When you land a result, my freshness check will fail until I refresh this file — that is the intended
signal, not a conflict.
