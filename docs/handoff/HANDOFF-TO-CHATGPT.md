# Handoff to ChatGPT — the Stage-3 entry point from the Fable 5.1 side

Last refreshed: 2026-09-28T04:53:17Z · maintainer: Fable 5.1 (root coordinator; this refresh written by the
merge and records agent, Claude Opus 5.5) · HEAD at writing `e4742aea` on `master`, tree clean. **GPU flying:**
the knowledge wave (W1, W3a, W4 on the shared in-chain A/A) and then REV-TFRL-1, from their own flight
worktree at `5f8b4c9d`, through the batch driver under queue task `SAEA-Queue-WAVE-REVTFRL` (log
`/home/chao/queue-wave-revtfrl.out`; status lines only: 03:50:52Z queue start; the COMP-1 + G5 STOP recorded
as already terminal, "launching the wave fresh after it ..., not chained onto it"; 03:50:52Z launching the
knowledge wave at 5f8b4c9d (steps w1 w3 w4); chain `batch_chain_wave.sh` start. The driver's status stream
shows the W1 smoke passed at 03:52:17Z and the W1 step's arm started at 03:52:27Z). Master commits do not
touch that flight. **COMP-1 + G5 STOPPED** at 03:28:18Z (section 2).
This is the standing counterpart to your `docs/handoff/HANDOFF-TO-FABLE51.md`: one short file,
refreshed **in place** after every landed result, no log section. Skeleton is fixed — state, what I
did, numbers, open items, embargoes, next action, housekeeping — so you can diff it. Freshness is
enforced by `scripts/checks/handoff_freshness_check.py`: if a newer file exists under `docs/results/`
than this stamp, the check fails and the staleness is my defect, not yours.

## 0. Read this first: the experiment rules (owner decision 166)

The owner asked me to state our experiment rules to you explicitly. They are in [`docs/handoff/EXPERIMENT-RULES-FOR-CHATGPT.md`](EXPERIMENT-RULES-FOR-CHATGPT.md). Each rule is in the imperative, with the gate that enforces it and the incident that motivated it. Your earlier work was re-read against the corrected instrument (`docs/results/2026-09-27-verdict-reclassification.md`). Of your 2026-09-25/26 items, 11 are KEEP and 1 is KEEP-PROVISIONAL (F10's mechanism counts), and none was adjusted. Your VAR-1 re-read against PLANr became rule 3. Nothing was overturned wholesale.

**The plan now in force is the re-plan v2** (`docs/readiness/2026-09-27-slurp-stage3-replan-v2.md`). The owner accepted all six items as recommended ("Decisions 1-6: all agreed; execute as recommended"), recorded as owner decisions 169-174 in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`:

- 169: A2, the COMP-1 replication on DEV-2000-ADDED, flies right after COMP-1 + G5 and before wave 1.
- 170: W5, slot-side retrieval, is registered as the fifth wave cell.
- 171: the B1 rank-visible conversion probe, the B3 catch-all offline design and the B4 empty-entity offline design are registered model-free.
- 172: the same-flight supply-variant instrument is authorised as an engineering-base item.
- 173: A2T-ORG-1 is re-read against h_A2T now; A-C1 comes after the SLURP lock.
- 174: Earnings E-C1 comes after E41 sub10 passes its form gates.

**Outcome of decision 170 (2026-09-28 00:20Z):** W5 stays registered and **HELD, not flown**. Its offline estimate is 0.14 pp SLU (ceiling 0.548), under the 1.2485 floor, and all 414 rows without gold slots would receive nine exemplars (`docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md`). The SLU main line is re-pointed at USE, not delivery:

- W4 conventions read no-harm;
- B4, an explicit empty-entity decision;
- slot-side contrastive consumption at the Solver, in B1's family.

The +17.4 figure is an oracle and does not measure delivery headroom.

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

**Current best arm, pending replication.** AGREE (the boundary agreement term) reads intent 82.50 -> **85.83**, +3.33 [+1.57, +5.09] against its in-chain A/A, with SLU +1.85 [+0.23, +3.47] on TRAIN Fold A. That leaves 9.17 points to 95. Under decision 166 it is KEEP-PROVISIONAL because the roster was reused for selection and for reading. COMP-1 composes AGREE + the centroid key + the citation contract; its arm **ABORTED** at 1,913 calls on the citation contract (section 2), so it is unread and in recovery. A2 (COMP-1 on DEV-2000-ADDED) settles AGREE's classification and gates every wave item into COMP-2 (row 138); it waits for the COMP-1 recovery.

## 2. What landed (2026-09-27 evening to 2026-09-28)

| work | artefact | state |
| --- | --- | --- |
| A2T-ORG-1 re-read against h_A2T 1.625 (decisions 166, 167, 173): official tool accuracy -3.225 [-4.30, -2.13] at n = 4,000, 2.0x h_A2T | `docs/results/2026-09-27-a2t-org-1-reread-against-h-a2t.md`, ledger annotated in both halves | **KEEP** (secondary-loss claim KEEP-PROVISIONAL) |
| Test fixes: the A2T comparator-rows companion is recognised, the sys.path quarantine scan is narrowed, and the Perception-state parser is excluded from renderer catalogue coverage | merge of `fable/testfix` | merged |
| COMP-1 on DEV-2000-ADDED (A2): arm, in-chain A/A of the PLAN lock's bytes, four-row smoke; own null h 1.1520 intent / 1.2525 SLU | `docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1/` | registered, **HELD**. `expected_effect_pp` is the placeholder `TO-BE-DECLARED-BY-COORDINATOR-FROM-THE-COMP-1-FOLD-A-READ` until the Fold A arm is read (row 139), so `stage3_effect_floor_check.py` refuses this one cell by design |
| The knowledge wave's shared in-chain A/A `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` | `docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1/` | registered; proven **IDENTICAL** to the AGREE arm's bytes |
| W3 re-derived and re-registered as **W3a alone** (intent contrast cards; the per-intent exemplar cap dropped under decision 164's one-change rule) | `docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/` (same run ids, rewritten in place) | registered, held |
| W5 slot-side retrieval, with its offline estimate | `docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1/`, `docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md` | registered, **HELD** (outcome of 170) |
| B1 / B3 / B4 (decision 171): `native_episode.knowledge_value_rendering` behind a config key (off by default); RANKVIS probe on the 119 Fold A rows AGREE got wrong (held); CATCHALL offline rule; EMPTYENT offline null + rule | merge of `fable/consume` | registered |
| **COMP-1 + G5 chain STOP**, 2026-09-28T03:28:18Z at `cb628f59`: COMP-1 smoke COMPLETED (16 calls); shared A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` COMPLETED (4,435 calls); the COMP-1 arm ABORTED after 1,913 calls on the Solver cited-answer contract refusal "intent citations must be unique non-blank ids"; G5 never started | `docs/results/2026-09-28-slurp-comp1-g5-chain-stop.md` | nothing read. Diagnosis and the ONE recovery re-registration are in progress on branch `fable/comp1rec`; the wave was launched fresh after the STOP, not chained onto it |
| **E41 four-row dry run**: R1, R2, R3 PASS (Perception truncated 0 / 4), form proof, no effect claimed | `docs/results/2026-09-28-e21-e41-four-row-dry-run-read.md` (merge of `fable/e41read`) | read |
| **E41 sub10 admitted and flipped** (owner decision 158): the draft's `dry_run_read` antecedent filled with the committed read and its blob sha256; the two sub10 exposure rows countersigned; receipt `coordination/e21-native-window-e41-v1/root-admission-sub10-v1.json` minted; the sub10 READ row `SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1-READ-V1` registered, countersigned and declared in its recipe (the pre-launch gate required it) | flip `f1485535`; flight commit `bf6db903` in `/home/chao/e41-sub10-flight-commit.txt` | `cli check` ready + `prepared_artifacts_ok: true`; `flight_registration_check.py` PASS for the cell. **Not launched**: E21 geometry, queued after REV-TFRL-1 |
| **ROLL-2 Fold A pool read** (DESCRIPTIVE): delivered 62.716 SLU / 80.185 intent as sealed; per-sample SLU 60.24-63.26, intent 81.76-82.78; oracle best-of-5 68.514 / any-sample-correct 83.241 as upper bounds; one intent across five samples on 93.5 % of rows | `docs/results/2026-09-28-slurp-roll-2-fold-a-pool-read.md` | read. **B3 is unblocked** (its primary pool input now exists); sampling cannot move intent, mirroring ROLL-3 |
| **B1 read driver + gate**: the RANKVIS probe read driver, its gate verifying rendering from the sealed request records, the dry-run replay honouring `knowledge_value_rendering` | merge of `fable/consume` (`ada7a4cb`) | merged; the probe itself stays held |
| **Same-flight supply-variant instrument, merge set A** (decision 172): design note plus the model-free read side (paired roster read, rollout score, citation credit, registration gate) | merge of `fable/svinst` (`2cef09ec`) | merged; touches no identity file (W1 `cli check` unchanged: same config and protocol hash, ready, `prepared_artifacts_ok: true`). **Set B waits for its named re-pin point** |
| Coordinator ratification of the two model-free W4 rows `SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1` and `SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1`, countersigned beyond the admission list | exposure ledger | ratified |

After the merge that carries the config key, `core.flight.cli check` on the ready COMP-1 arm still reads `ready` with `prepared_artifacts_ok: true`. The flying cells' prepared-artifact identity did not move.

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

Yours, unchanged:

- Revalidate live identity before acting, and never treat historical PIDs as targets.
- Run no progress-monitor subagents.
- Run one generating flight plus one scorer, with ≤8 preparation workers during a campaign.
- control625 quality stays unread; DEV6570 and test13078 stay closed.
- Run no second recovery on any closed family.
- Do not restart the semantic-delta, VAR-2, F10 or evidence-path arms.
- Power mode is settled.

Mine: make no cross-flight claim without an in-chain replicate and no benefit claim under 200 rows. Every cell registered from 2026-09-27 carries a `stage3_measurement` block, and `stage3_effect_floor_check.py` enforces it.

**Waiting on the owner, not mine to take.** Two test defects are still open after the `fable/testfix` merge (`pytest -q`: 17,393 passed, 2 failed):

1. The `kb_policy` digest lock: `test_stage2a_synthesis_verification.py` pins a `FILE_DIGESTS` value for `rails/kb_policy.py`, and the live sha256 drifted from it across the W1-W3 merge wave. Re-pinning needs an owner-authorised equivalence proof.
2. A wrong sha256 inside the committed receipt `docs/receipts/a2t/A2T-CANONICAL-FAMILY-SECONDARY-FIXED8.json`, on its `A2T-G6-FAMILY-SWEEP-FIXED16.json` exclusion entry. The receipt was already wrong when it was authored, and the error is not a CRLF artefact. The receipt is hash-pinned evidence, so it gets a superseding receipt or an owner ruling, never an in-place edit.

**Wave state (decision 164, one change from the AGREE bytes each, one shared A/A):**

| cell | state |
| --- | --- |
| Shared A/A | Registered and proven IDENTICAL to AGREE. |
| W1 | Card selection. |
| W2 | Stopped offline. |
| W3 | W3a alone. |
| W4 | Slot conventions, no-harm. Its base is AGREE. |
| W5 | Held (outcome of 170). |

The wave (W1, W3a, W4 on the shared A/A) is flying now at `5f8b4c9d`, launched fresh after the COMP-1 + G5 STOP; REV-TFRL-1 follows it in the same queue.

**Same-flight supply-variant instrument (decision 172).** The design note and merge set A are on master (merge `2cef09ec`); set A touches no identity file. Set B touches identity-bound implementation files and merges only at its named re-pin point. VAR-2 as a mechanism stays closed.

## 7. My next action

1. Let the running queue finish (the wave W1, W3a, W4 on its shared A/A, then REV-TFRL-1), then read each with the standard paired read. W5 stays held.
2. Land the COMP-1 recovery from `fable/comp1rec` (one re-registration at most; a second failure stops the flight and the fix is proven on a 4-row dry run), re-fly COMP-1 + G5, and read them against the sealed shared A/A.
3. From the COMP-1 Fold A read, declare `expected_effect_pp` for A2 (row 139), replacing the placeholder in both places the gate reads; then flip A2 (arm + A/A + smoke) and queue it.
4. Queue the E41 sub10 re-read (flight commit `bf6db903`) on the E21 geometry after REV-TFRL-1; Earnings E-C1 is registered only after sub10 passes its form gates (174). A-C1 on Audio2Tool waits for the SLURP lock (173).
5. Offline in parallel: B3 (CATCHALL) over the ROLL-2 pool once its row is countersigned; the B4 offline null, then its rule; the RANKVIS probe (0.1 GPU-h) when the card has a gap; merge set B of the supply-variant instrument at its re-pin point.

## 8. Housekeeping we share

WSL2 `Ubuntu-24.04`, `/home/chao/.venvs/speechrl/bin/python`, English documents, one generating flight
plus one scorer, merge finished work into master promptly, keep both entry points short and current.
When you land a result, my freshness check will fail until I refresh this file — that is the intended
signal, not a conflict.
