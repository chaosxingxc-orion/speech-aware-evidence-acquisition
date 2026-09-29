# Handoff to ChatGPT — the Stage-3 entry point from the Fable 5.1 side

Last refreshed: 2026-09-29T16:04:34Z · maintainer: Fable 5.1 (root coordinator; this refresh written by the
records and read agent) · HEAD at writing `c0067e0e` on `master` (plus this refresh commit), tree clean.
**Since 15:04Z (records agent):** **Owner decisions 198/199 recorded** (registry rows at `f26e3cdb`). **198: COMP-1
NOT ADMITTED** (intent +4.26 [+2.41, +6.11], SLU-F1 -2.24 [-3.97, -0.47], HARMFUL branch). Cause named by the
attribution `docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md` (branch `fable/comp1slu`, not yet merged):
the Solver cited-answer contract, +102 false positives on the 414 zero-gold rows; the unwrap and the supply are
cleared. Owner adopted option B ("可以", "OK"): **COMP-1b** = AGREE + centroid boundary key WITHOUT the citation
contract, TRAIN Fold A vs the same in-chain A/A, declared intent +4.26, SLU guard -1.2485, registered and held on
`fable/comp1b` (cell `slurp-native-stage3-comp1b-fold-a-v1`), flipped/queued after the P-SV flips; then **A2 =
COMP-1b on DEV-2000-ADDED**. The citation contract leaves the COMP-2 component list (it may return only as its own
single-factor cell with an entity-emission limit). GPU order: G5 -> COMP-1b -> P-SV-2 / P-SV-3 -> A2. **199 (owner
directive): empty is legal** -- a slot may be none and knowledge retrieval may return nothing; supply abstention and
the answer-side "no entities" option become first-class, receipted outcomes (never padded to k); the module design
gains section 2c "Empty is legal" (`c0067e0e`: `supply_abstain: {rule, threshold, pinned table}`, inventory row 19,
model-free migration step 6a / AT-M5; all-off arms keep fixed-k bytes); the offline supply-abstention headroom
analysis is dispatched on `fable/emptysupply`; B4 (offline net -0.19) is re-examined under 199, not closed.
**P-SV-1 seal-only** (decision 197): registered and countersigned (`a842f670`), flipped to ready at `e42e87f3`, but the
flip was refused on the parent-package residue -- the cell is ready-unconverged at `e42e87f3`; the fix is on
`fable/repinresume2`. **P-SV-2's re-pin and P-SV-3's flip are queued behind that fix.** **G5 is flying.**
**Since 14:45Z (records and read agent):** the consumption-module design spec with coordinator rulings R1-R5 is merged
(`d51063b4`, `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md`, decisions 195/196). **COMP-1
seal-only COMPLETED**: attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only` FINALIZED at
`fd8a01fe` (manifest 14:42:12Z, 1,080 rows = 471 + 609 kept, 0 flown, 0 new contacts, scored once; run-cumulative
4,441 contacts), READ row seal-only clause countersigned `cf38bec3`, **read landed** (`99c5b004`,
`docs/results/2026-09-29-slurp-comp1-fold-a-read.md`, DESCRIPTIVE): vs the in-chain A/A intent 81.85 -> 86.11,
**+4.26 pp [+2.41, +6.11]** (declared 3.23, bar 2.5), official SLU-F1 64.21 -> 61.97, **-2.24 pp [-3.97, -0.47]**
(entity FP 497 -> 611; audio -41.04, general -17.46); newly delivered rows convert 38 / 78 (declared 56 / 125). The
numbers fall in the rule's **HARMFUL branch on the SLU-F1 guard**; the coordinator's verdict clause is pending. The
registered read driver refuses a seal-only arm (no generation manifest, no `phases.json`); the gating contrast ran on
the same driver bytes over a mirror data root (disclosed in the note). **G5 is flying** (campaign started 14:46:23Z,
smoke then arm, `fd8a01fe`). **P-SV-3** registration in progress on `fable/psv3` (boundary-depth column, present
primary). **P-SV-1 seal-only** (owner decision 197 GO) waits for the I7v receipt fix on `fable/psvsealfix`.
**P-SV-1 ABORTED AT SEAL** (`SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1`, flight commit `b9af3e58`): all 1,080 rows flew
(8,709 calls, run_phases complete), then the seal refused at 14:19:36Z on invariant **I7v** (`BundleError`: a
perception-branch receipt's `candidate_intent_ids` must be a non-empty ordered list of distinct non-empty strings).
Recovery is **seal-only after the receipt fix, no re-fly, no re-pin of the flown attempt** -- owner decision 197 GO;
the I7v fix is on `fable/psvsealfix`. Lock reconciled and STOP filed:
receipt `coordination/slurp-stage3-psv1-fold-b-v1/flight-lock-reconciliation-20260929T143300Z.json`
(`lease_reconcile_psv1.sh`, `0b50d47e`). **P-SV-2 is held back** (same validator) until the fix lands and it is
re-pinned; `SAEA-Queue-PSV` is not restarted.
**GPU queue now:** `SAEA-Queue-SEALONLY` (COMP-1 seal-only + G5 at `fd8a01fe`, P-SV wait removed, restarted 14:39Z,
seal-only step DONE ~14:44Z, G5 smoke/arm flying) -> `SAEA-Queue-E4SEAL` (E4-1 seal-only at `0b50d47e`, waits for `SEALONLY-COMP1 DONE` /
`filler hold removed`) -> filler. **Owner decisions 189-196 are recorded** (registry
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`; 189-194 at `70b2054e`, 195/196 at `da979818`):
189 option A (COMP-1 seal-only completion), 190 per-metric same-flight floors, 191 rule-card slot-convention line
CLOSED, 192 W5 held and a 1.5 pp offline bar for any SLU mechanism, 193 P-SV GO, 194 E4-1 seal-only completion GO,
**195 option B** (the do-not-tag scope rule is a USE-layer deterministic node action inside the COMP-2 composed
policy, and the assembled consumption components become ONE module that may itself call the model), **196** (owner
directive: the module must be carrier-agnostic, transferable to Audio2Tool, Earnings-21 and Earnings-22 once SLURP
gains are stable). The module design is merged (`d51063b4`, rulings R1-R5).
**Merged today by the records agent:** `fable/floor190` (merge `c2f1be08`; decision 190: `stage3_effect_floor_check.py`
floors per metric, intent 0.65 / SLU 1.49 at n = 1,080, shadow-relisten on SLU only, `primary_metric_key` required from
2026-09-30; `accept.py`, the four registration writers and tests; 1,072 worktree tests passed) and `fable/w5offline`
(merge `949d77d1`; `docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md`: no SLU mechanism at >= 1.5 pp at
a measured conversion, best composition about 1.28; W5 expected 0.15, line closed by the coordinator; consumption
214 / 407, 107 of 229 undetermined items had the gold value supplied; 16 worktree tests passed). Under decision 190
inner-loop run 1's k = 10 nomination (+0.48) lapses; run 1 nominates nothing. The floor check now FAILs on one blocker,
the comp1dev placeholder `expected_effect_pp` (A2's declaration can now be made: the COMP-1 Fold A read landed at `99c5b004`), with 17 advisories (W4-SV
`primary-metric-key-missing` and 16 missing declarations).
**COMP-1 seal-only completion + G5** (decision 189): countersigned `b3984358`, receipt
`coordination/slurp-stage3-comp1-fold-a-v1/root-admission-sealonly-v1.json` (sha256 `8a203ffd...`), flipped with G5
at flight commit **`fd8a01fe`**, queued as **`SAEA-Queue-SEALONLY`** (zero model contacts; replay proof
1,080 / 0 / 0; restarted 14:39Z without the P-SV wait). **E4-1 seal-only completion** (decision 194): countersigned
`b3984358`, receipt `coordination/slurp-stage3-relisten-fold-a-v1/root-admission-sealonly-v1.json` (sha256
`43d83158...`), the coordinator's column gate pre-declared on the READ row (replace-only >= 29 % net conversion of the
106 items; drop column >= 49.5 net false positives removed); the parent-config residue fix is merged (`0ef6d98c`,
`fable/repinresume`), the flip converged in one pass at **`0b50d47e`** (`/home/chao/e4seal-flight-commit.txt`;
registration gate PASS), queued as **`SAEA-Queue-E4SEAL`** behind COMP-1 seal-only + G5.
**Lines closed:** W4 / W4-SV rule-card slot conventions (191; results-ledger clauses added), W5 (192, coordinator; the
owner may reopen). **Re-plan v3:** `docs/readiness/2026-09-29-slurp-stage3-replan-v3.md` (supersedes v2; rounds
P-SV -> COMP-1 seal-only + G5 -> E4-1 seal-only -> COMP-1 / G5 read -> A2 on DEV-2000-ADDED -> P-SV reads -> composed
Perception policy -> milestone test read on the owner's go; the boundary-recall gap, 83 off-list rows with 49 in the
boundary block, is the named blank for 95). **Engineering item:** the registration gate treats seal-only cells as
historical and their decision receipts are checked only by the flip scripts; the gate should check them directly.
SLURP only on the GPU (decision 187). RANKVIS stays **INERT** and REV-TFRL-1 **NOT ADMITTED**.
**Isolation:** every chain flies from the `fable-batch-flight` worktree at its own flight commit, never from
master. Never re-flip a queued cell on master without updating its flight-commit file and the queue script's
hard-coded commits. **Hazard:** any `core.flight.cli` process alive between chain steps makes the running
driver STOP itself -- run no `cli check` while a queue is live.
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

**Current best arm, pending replication.** AGREE (the boundary agreement term) reads intent 82.50 -> **85.83**, +3.33 [+1.57, +5.09] against its in-chain A/A, with SLU +1.85 [+0.23, +3.47] on TRAIN Fold A. That leaves 9.17 points to 95. Under decision 166 it is KEEP-PROVISIONAL because the roster was reused for selection and for reading. COMP-1 composes AGREE + the centroid key + the citation contract; its arm **ABORTED** at 1,913 calls on the citation contract (section 2), so it is unread; the recovery is RESUME (decision 175; `-REC` superseded unflown), whose attempt 1 died on a server CUDA abort, whose attempt 2 STOPped on a fit-identity refusal, and whose attempt 3 flew every row but failed at the seal on the replayed rows (header); decision 189 ruled option A, the seal-only completion is queued behind P-SV -- still unread. A2 (COMP-1 on DEV-2000-ADDED) settles AGREE's classification and gates every wave item into COMP-2 (row 138); its per-class attribution is now fixed model-free, and its declaration formula waits for the COMP-1 Fold A read.

## 2. What landed (2026-09-27 evening to 2026-09-29)

| work | artefact | state |
| --- | --- | --- |
| A2T-ORG-1 re-read against h_A2T 1.625 (decisions 166, 167, 173): official tool accuracy -3.225 [-4.30, -2.13] at n = 4,000, 2.0x h_A2T | `docs/results/2026-09-27-a2t-org-1-reread-against-h-a2t.md`, ledger annotated in both halves | **KEEP** (secondary-loss claim KEEP-PROVISIONAL) |
| Test fixes: the A2T comparator-rows companion is recognised, the sys.path quarantine scan is narrowed, and the Perception-state parser is excluded from renderer catalogue coverage | merge of `fable/testfix` | merged |
| COMP-1 on DEV-2000-ADDED (A2): arm, in-chain A/A of the PLAN lock's bytes, four-row smoke; own null h 1.1520 intent / 1.2525 SLU | `docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1/` | registered, **HELD**. `expected_effect_pp` is the placeholder `TO-BE-DECLARED-BY-COORDINATOR-FROM-THE-COMP-1-FOLD-A-READ` until the Fold A arm is read (row 139), so `stage3_effect_floor_check.py` refuses this one cell by design |
| The knowledge wave's shared in-chain A/A `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` | `docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1/` | registered; proven **IDENTICAL** to the AGREE arm's bytes |
| W3 re-derived and re-registered as **W3a alone** (intent contrast cards; the per-intent exemplar cap dropped under decision 164's one-change rule) | `docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/` (same run ids, rewritten in place) | registered, held |
| W5 slot-side retrieval, with its offline estimate | `docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1/`, `docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md` | registered, **HELD** (outcome of 170) |
| B1 / B3 / B4 (decision 171): `native_episode.knowledge_value_rendering` behind a config key (off by default); RANKVIS probe on the 119 Fold A rows AGREE got wrong (held); CATCHALL offline rule; EMPTYENT offline null + rule | merge of `fable/consume` | registered |
| **COMP-1 + G5 chain STOP**, 2026-09-28T03:28:18Z at `cb628f59`: COMP-1 smoke COMPLETED (16 calls); shared A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` COMPLETED (4,435 calls); the COMP-1 arm ABORTED after 1,913 calls on the Solver cited-answer contract refusal "intent citations must be unique non-blank ids"; G5 never started | `docs/results/2026-09-28-slurp-comp1-g5-chain-stop.md` | nothing read; recovery staged (next rows). The wave was launched fresh after the STOP, not chained onto it |
| **COMP-1 abort root cause and fixes** (merged): the root cause is a repeated Solver intent citation id tripping the cited-answer contract ("intent citations must be unique non-blank ids"). Fixes: a repeated citation id is collapsed instead of aborting the arm; a seal-refused stop becomes a per-row abstain; the resume replay now skips the context-fit and cited-answer annotation blocks (with a COMP-1 resume byte-identity proof) | merges of `fable/comp1rec` / `fable/comp1res`; `docs/results/2026-09-28-slurp-comp1-g5-chain-stop.md` section 5 | merged. The aborted arm is closed (consumed = yes) |
| **COMP-1 recovery**: variant 1 resume (owner decision 22) vs variant 2 `-REC` (full 1,080-row re-fly, fresh run id, shared in-chain A/A not re-flown). **Owner ruling open; default `-REC`**, chosen by the coordinator | `-REC` smoke + arm flipped ready, flight commit `472474bf`; receipt `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-rec-v1.json` | `-REC` + G5 queued in `SAEA-Queue-AFTER-REVTFRL`; the resume variant stays HELD. `cli check` on the `-REC` arm: ready, `prepared_artifacts_ok: true` (cfg `67063b2c`, proto `7edf51c1`) |
| **B3 CATCHALL offline read** (decision 171): Fold A intent -0.185 [-0.778, +0.370] vs floor 0.5097; DEV +0.320 [-0.280, +0.920] vs 0.5299 | `docs/results/2026-09-28-slurp-catchall-offline-read.md` | **INERT** (coordinator). No arm. The K5 catch-all class (3.06 pp) stays open and needs evidence from outside the vote (the B1 rank-visible / contrastive family) |
| **B4 EMPTYENT offline read**: SLU-F1 +0.256 [+0.067, +0.445], intent 0.000; the pool's own sample-vs-sample null is 1.547 pp SLU / 0.810 intent | `docs/results/2026-09-28-slurp-empty-entity-offline-read.md` | **INERT-BY-INSTRUMENT** (coordinator): real but tiny, about 17 % of the null; no arm. **Instrument finding:** a multi-sample pool's offline null on DEV-2000-ADDED is 2.3x the 0.67 pp one-pool floor, so offline rule designs on multi-sample pools have little room. FP-only share 16.2 % by the scorer's per-row definition, not 10.8 % |
| **A2 DEV attribution table** fixed model-free before contact (decision 138): 109 newly delivered rows on DEV-2000-ADDED vs 78 on Fold A | `docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1/attribution-classes-v1.json` (merge of `fable/comp1devattr`) | merged; A2 still HELD. Its `expected_effect_pp` declaration formula is pending the COMP-1 Fold A read |
| **E41 four-row dry run**: R1, R2, R3 PASS (Perception truncated 0 / 4), form proof, no effect claimed | `docs/results/2026-09-28-e21-e41-four-row-dry-run-read.md` (merge of `fable/e41read`) | read |
| **E41 sub10 admitted and flipped** (owner decision 158): the draft's `dry_run_read` antecedent filled with the committed read and its blob sha256; the two sub10 exposure rows countersigned; receipt `coordination/e21-native-window-e41-v1/root-admission-sub10-v1.json` minted; the sub10 READ row `SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1-READ-V1` registered, countersigned and declared in its recipe (the pre-launch gate required it) | flip `f1485535`; flight commit `bf6db903` in `/home/chao/e41-sub10-flight-commit.txt` | `cli check` ready + `prepared_artifacts_ok: true` (cfg `e5fd6a77`, proto `bcfbe518`, re-checked after today's merges). **Not launched**: queued in `SAEA-Queue-AFTER-REVTFRL` after `-REC` + G5 |
| **ROLL-2 Fold A pool read** (DESCRIPTIVE): delivered 62.716 SLU / 80.185 intent as sealed; per-sample SLU 60.24-63.26, intent 81.76-82.78; oracle best-of-5 68.514 / any-sample-correct 83.241 as upper bounds; one intent across five samples on 93.5 % of rows | `docs/results/2026-09-28-slurp-roll-2-fold-a-pool-read.md` | read. **B3 is unblocked** (its primary pool input now exists); sampling cannot move intent, mirroring ROLL-3 |
| **B1 read driver + gate**: the RANKVIS probe read driver, its gate verifying rendering from the sealed request records, the dry-run replay honouring `knowledge_value_rendering` | merge of `fable/consume` (`ada7a4cb`) | merged; the probe itself stays held |
| **Same-flight supply-variant instrument, merge set A** (decision 172): design note plus the model-free read side (paired roster read, rollout score, citation credit, registration gate) | merge of `fable/svinst` (`2cef09ec`) | merged; touches no identity file (W1 `cli check` unchanged: same config and protocol hash, ready, `prepared_artifacts_ok: true`). **Set B waits for its named re-pin point** |
| **W1 card selection read** against the shared wave A/A (TRAIN Fold A, n = 1,080): intent +0.19 [-0.74, +1.11], official SLU-F1 +0.53 [-0.85, +1.93]; both no-harm clauses hold (margins 0.9943 / 1.2485); -3,379.5 prompt tokens per row, -8.0 % GPU-h, Solver -1,125 tokens per contact (registered -1,186); instrument reading (A/A vs the AGREE arm it re-flies) intent -0.19 / SLU -1.00, inside the between-flight band | `docs/results/2026-09-28-slurp-w1-fold-a-read.md` (merge `01b98eef`, verdict `af29c70c`) | **NEUTRAL (no-harm holds; retained as an enabler)** (coordinator). The saving is the room W3a and W4 need; W1 folds into COMP-2 only after AGREE replicates on DEV-2000-ADDED (decisions 138 / 161 / 169) |
| **W3a intent contrast cards read** against the shared wave A/A (TRAIN Fold A, n = 1,080): intent -0.56 [-1.67, +0.56] (15 saves / 21 harms, p 0.405), official SLU-F1 +0.32 [-1.39, +2.02]; the intent no-harm clause does not hold (-1.67 below -0.9943) and no harm clause is met; the K1 ceiling (+6.94 pp oracle) did not convert in card form; -1,378.6 prompt tokens per row, -0.126 GPU-h per 1,080 rows (noted, not a reason to retain) | `docs/results/2026-09-28-slurp-w3a-fold-a-read.md` (merge of `fable/wavereads`, `25826028`; verdict `9d8ba00d`) | **NOT ADMITTED** (coordinator: neutral by width; the card form of K1 is closed; contrast evidence continues only at the decision node -- RANKVIS and the Reviewer top-2 contrast of decision 165's second round; does not enter COMP-2) |
| **RANKVIS** (B1 rank-visible probe, 119 Fold A rows AGREE got wrong): registration completed, exposure rows countersigned, flipped ready | flip `b0c6c608` (flight commit in `/home/chao/rankvis-flight-commit.txt`) | flown and read: **INERT** (row below) |
| **Same-flight supply-variant instrument, merge set B** (decision 172) | merge of `fable/svinst` (`0f17a5e1`) | merged on master; queued flights are unaffected because they fly at their own flight commits |
| Tool-gap fixes: the repin residue scan is scoped to the cell, the flip scripts carry the current trailer; config tests made flip-state agnostic | merges of `fable/repinfix2` (`da541f92`) and `fable/cfgtests` (`18f1ae2e`) | merged; both gaps from the `-REC` staging are closed |
| **W4 slot conventions read** against the shared wave A/A (TRAIN Fold A, n = 1,080): official SLU-F1 (primary) +0.79 [-0.56, +2.12], intent guard -0.09 [-1.02, +0.83] (13 saves / 14 harms); the SLU no-harm margin (1.2485) holds but the result sits below the M4b analogue's lower end (1.3285) and far below the 2.5 pp cross-flight floor; the intent guard misses its margin (0.9943) by 0.024 pp, under one row's step (0.0926), so the cell is in the residual branch; entity classes SPURIOUS -29, BOUNDARY -12, MISSING +14, WRONG-TYPE -4 (FP 506 -> 461); cost +3,529 prompt tokens per row, +1,207.8 per Solver contact (registered +724.5), +0.1643 GPU-h per 1,080 rows | `docs/results/2026-09-28-slurp-w4-fold-a-read.md` (read `d28f098d`, verdict `06810352`) | **NOT ADMITTED (neutral by width)** (coordinator); does not enter COMP-2, not an enabler. **Re-registered as the first real cell of the same-flight supply-variant instrument's phase 1** (decision 172; spec `docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md`): Solver-local columns with an in-flight twin arm; base = the AGREE arm bytes; arm A = the AGREE Solver supply; arm B = the W4 conventions; twin = a replicate of A; `arm_visits: "first"`; claim `"nominated"` only. Its plausible effect (about 0.8 pp SLU) is the size that design reads (about 0.7 pp at n = 200) and the cross-flight design cannot |
| Coordinator ratification of the two model-free W4 rows `SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1` and `SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1`, countersigned beyond the admission list | exposure ledger | ratified |
| **Owner decisions 175-180** (~13:20Z and ~14:00Z) | `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` rows 175-180 | 175 RESUME (decision 22 amended for post-fix resumes; byte-identity proof 481/481; `-REC` superseded unflown; resume flip pending `fable/repinresume`); 176 DONE (`kb_policy` `FILE_DIGESTS` re-pinned, `cfd34bf5`, merge `87189a82`); 177 DONE (receipt v2, `3d02f68f`, merge `03c94d72`; v1 kept immutable); 178 K1-as-cards closed, contrast only at the decision node; 179 offline rule designs on multi-sample pools discontinued, sub-floor reads go to the same-flight instrument (first cells W-SV-1 and W4-SV, both held); 180 consumption thesis adopted with measured caveats, core-native re-listen first, Whisper only after E4 reads, extension experiments E1-E6 |
| **E1: SLURP node information-gain ledger** (model-free, TRAIN Fold A, AGREE arm + its same-bytes replicate). Intent: boundary block -> Perception +7.04 [+5.00, +9.07] pp; Perception -> Solver 0.00 [-1.20, +1.20]; Reviewer/Planner net -1 row; deliver normaliser +1.94. Conversion by Perception rank 97.6 / 27.0 / 12.0 %; of 153 wrong rows gold is at rank 2 on 42 (3.89 pp), rank 3 on 20, off the list on 83 (49 in the block, 34 outside). Slots: SLU-F1 63.89 -> 63.94 -> 65.16; only FORMAT moves after the Solver (normaliser +1.22 [+0.80, +1.66]); of 407 delivered errors 107 consumption origin, 71 visible hearing/span, 229 undetermined; 35 of 142 BOUNDARY + NEAR + FORMAT re-listen addressable; SPURIOUS 253 | `docs/results/2026-09-28-slurp-node-information-gain-ledger.md` (merge `1bf2877d`; coordinator reading section 5, `8e843055`) | **DESCRIPTIVE.** Coordinator reading: Perception's shortlist decides intent, so the contrast action must reach it (same-flight instrument **phase 2** is now the priority engineering item; RANKVIS stays queued as a cheap Solver-side test, bounded by the rank-2/3 conversion); E6's first instance: the Solver (intent) and the Reviewer/Planner (intent and slots) show no measurable gain |
| **E3 progressive slot loading design** (type first, then the chosen type's closed vocabulary) | `docs/superpowers/specs/2026-09-28-e3-progressive-slot-loading-design.md` (merge `17361233`) | merged, model-free. Supported by 34 of 41 closed-type misses being Solver omissions; flies **after E4** as a cross-flight no-harm enabler |
| **E4 core-native targeted re-listen design** (blind re-listen of each delivered slot keyed by intent + type, then a forced-choice confirm) | `docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md` (merge `73aae18f`; rulings section 8, `b12810a5` / `88897512`) | merged with coordinator rulings: NOT shelved (hearing share 17-74 %); two shadow columns from the same contacts, (a) replace-only and (b) replace + drop-when-both-contacts-say-unheard (aimed at the 253 SPURIOUS); the confirm contact does not see Perception's candidates; missing-slot probe left to E3; shadow on Fold A first; host = the AGREE arm bytes; expected effect 0.0 nominated, bar = the twin/shadow null; SLU-F1 primary, intent identical by construction. Not registered |
| **Owner decisions 181-188** (2026-09-28 ~23:30Z to 2026-09-29 ~00:05Z) | `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` rows 181-188 and their outcomes | 181 COMP-1 resume STOP -> option A, but the diagnosis found a server CUDA abort (infrastructure), so the outcome is a direct retry under decision 22 (resume attempt 2, same run, `resume_from` the aborted attempt); 182 idle watchdog authorised (merged, registered paused); 183 card order RANKVIS -> W-SV-1 -> W4-SV -> sub10 -> filler; 184 P-SV-1 / P-SV-2 (phase-2 Perception variants, TRAIN Fold B, `nominated`) registered after merge set C; 185 E4 v1 implemented after set C with a 4-row dry run; 186 Fold B is ROLLOUT-exposed, a phase-2 cell built from Fold B rollouts may not be read on Fold B; 187 **SLURP only on the GPU** (sub10 deferred, its cell stays ready at `bf6db903`; A2T and Earnings fly nothing; model-free work continues everywhere); 188 B5 deferred, P-SV first |
| **Server CUDA abort** (decision 181 outcome): resume attempt 1 loaded, replayed and passed prelaunch; 3 s after its first Perception wave the resident llama-server aborted on `CUDA error: the function failed to launch on the GPU` (`ggml_cuda_op_mul_mat_cublas`; an earlier `illegal memory access` abort in the same 14.6 h server log); 4 calls / 10.6 s audio spent; the 471 kept rows untouched | decisions file, outcome of 181 | retried as **resume attempt 2** at `c24824a4` (flip `27c2b372`, G5 re-converged `c24824a4`), queue `SAEA-Queue-RESUME2`: resume + G5 -> W-SV-1 / W4-SV when flipped -> release `pre-sub10.hold` -> the filler (SLURP only, row 187). **Attempt 2 STOPped at 00:20:43Z** on `native contact fit identity already has contact or result evidence` (header); the watchdog's uptime-restart rule (12 h) is the standing answer to the server-age finding |
| **RANKVIS read** (B1 rank-visible probe, 119 Fold A rows AGREE got wrong): m = 19 / 119 (Wilson [10.47, 23.59] %) against the no-op 15.9 (+0.29 pp net; m >= 43 net needed cross-flight, >= 20 same-flight); gold at boundary position 1 converted 14 / 18 (no-op 6.97), positions 2-8 only 5 / 101 | `docs/results/2026-09-29-slurp-rankvis-probe-fold-a-119-read.md` (merge `6f3c2974`, verdict `0d9e03e5`) | **INERT (form proof; the B1 arm is not registered)** (coordinator). Rank labels make the Solver follow the presented rank 1 -- consistent with the node-gain ledger (Solver follows Perception's rank 1 on 97.6 %); the contrast route continues at Perception (P-SV-1 / P-SV-2). The driver's two path repairs are accepted |
| **REV-TFRL-1 read** (contrastive Reviewer form vs its in-chain A/A, TRAIN Fold A, n = 1,080): intent -0.46 [-1.57, +0.65], official SLU-F1 -0.55 [-1.79, +0.69]; both no-harm clauses fail, no harm clause met; the +0.80 declaration lies above the CI; REVISE reach 3.32 % -> 30.57 % of visits but intent repairs / breaks 14 / 15 and entity 34 / 16; +0.42 GPU-h per 1,080 rows | `docs/results/2026-09-28-slurp-revtfrl-1-fold-a-read.md` (merge `46fd19d8`, verdict `0d9e03e5`) | **NOT ADMITTED (neutral by width with a measured cost)** (coordinator; decision 188): reach was achieved, judgment was not; B5 deferred behind P-SV-1 / P-SV-2; row 165's route stays open |
| **W-SV-1 and W4-SV** (the first two same-flight supply-variant cells, decision 179) | merges of `fable/wsv1` and `fable/w4sv2` (`c30d03d5`), `fable/w4svproof` (`9907a7d3`); `docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1/`, `docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1/` | W-SV-1 countersigned (`92ce4c39`), flown at `1c1e19ce` under `SAEA-Queue-WSV1`, **sealed and read** (row below). W4-SV countersigned (`f2cf343a`), receipt minted, flipped (`4f203ea9`) and **flying** (`SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1`), then the filler |
| **COMP-1 resume attempt 3** (after the fit-identity STOP of attempt 2; the resume fix proven first on a four-row dry run, flip `8fd87fca`) | the flight's own manifests; diagnosis on `fable/sealcheck` | **ABORTED at the seal**: all 609 remaining rows flew (2,476 calls), then the seal refused the 471 replayed rows because the deliver normaliser's output hash does not match the replayed `final_response_text`. Unread. Root cause `core/flight/resume.py::_classify` (raw recorded response instead of the normaliser's output for kept rows), fixed on `fable/sealcheck` `d619e1c5`; the offline seal-replay checker reproduces 471/471 under the old code and 0/1,080 under the fix (decision 181 addendum, `06cdabb7`). Attempt 2's STOP was a coordinator-side registration error (attempt 1's FIT id reused; 48 calls). **Owner decision 189 pending**: A, seal-only completion (recommended), or B, resume from attempt 3 |
| **Seal fix + offline checker** | merge of `fable/sealcheck` (`3ca7bfca`; fix `d619e1c5`); `docs/results/2026-09-29-slurp-comp1-resume3-seal-abort-diagnosis.md` | merged. `replay_seal_consistency.py` over the original attempt (471 rows) and attempt 3 (609 rows): 0 of 1,080 failing under the fix |
| **Resume prelaunch replay gate** (coordinator ruling after the attempt 3 abort) | merge of `fable/resumegate` (`6473df27`; `World` fixture conflict resolved by keeping both master's `perception_branches` and the branch's `resume_from` / `resume_replay_proof`) | merged. `resume_prelaunch_gate_check.py` runs the offline full-trace replay for any step whose config declares `resume_from`; new finding `resume-replay-unproven`. The `--include-held` blocking set is unchanged (9 cells) |
| **Set C: same-flight instrument phase 2** (Perception branches; decision 184) | merge of `fable/svphase2` (`57d464ad`; conflict in `scripts/checks/flight_registration_check.py` resolved by the coordinator's ruling: the new perception-branch registration check is added, and the roster-split check keeps master's condition `report.named or report.consumed_by is None`) | merged. The perception-branch check reports `branch-seed-unpinned` on the held P-SV cells (advisory while held); the blocking set of `flight_registration_check.py --include-held` is unchanged (9 cells) |
| **P-SV-1 / P-SV-2** (phase-2 Perception variants, TRAIN Fold B, decision 184) | merge of `fable/psv` (`4e5a9a7e`); `docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1/`, `...-psv2-fold-b-v1/` | branch seeds merged (`d158d4ee`, `d81b8ad4`; worktree tests 126 / 128 passed; `--include-held` blocking set unchanged, 9 cells); eight flight rows countersigned (`a9d8bf8a`), 1,078 / 1,080 seed coverage disclosed; P-SV-2 receipt minted; **NOT flipped**. The B-axis wiring has landed (merge `038de276`, header) and P-SV-1 is re-pinned to the all-pairs v2 contrast-pair table (ruling O7; 1,035 / 1,078 B-row coverage); both cells still need re-derivation, re-pin, P-SV-1 mint and flip. P-SV-1's contrast-pair table is pinned (`3ee765f3`): `prepared/SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V1/table-v1.json` sha256 `19bf2487...`, receipt `docs/receipts/knowledge/slurp-perception-contrast-pairs-v1.json` sha256 `4af9e874...`, 48 pairs written / 2 skipped of 50. No flip before the branch seeds are prepared and pinned |
| **Filler c01 / c02 sealed-pool read** (TRAIN Fold B, 180 rows each, five Solver samples at T 0.7) | `docs/results/2026-09-29-slurp-filler-fold-b-c01-c02-pool-read.md` (merge `62d4a2f3`) | **DESCRIPTIVE.** Mean-sample intent / SLU-F1 80.56 / 65.87 (c01) and 82.89 / 62.36 (c02); oracle any-sample intent / best-of-5 SLU-F1 81.11 / 71.93 and 84.44 / 69.71; one intent across all five samples on 96.1 % / 94.4 % of rows; median micro SLU half-width 3.32 / 3.36 at n = 180. Sampling headroom sits in slot content (+6.1 to +7.3 SLU over the mean sample), not intent (at most +1.56) |
| **Seal-only completion capability** (option A of decision 189) | merge of `fable/sealonly` (`e5146944`; worktree merge of master `7f1951fa`, clean) | merged. Multi-predecessor `resume_from`, `core.flight.cli seal-only`, I7r per-sample binding; `replay_seal_consistency.py` pins the predecessors and checks the real COMP-1 pair at 1,080 rows / 0 failing / 0 sealed twice; 246 targeted tests pass. `runtime.py` changed, so HELD cells re-pin at their flip. The `--include-held` blocking set is unchanged (9 cells). The COMP-1 seal-only completion cell is registered **HELD** (row below) |
| **E4 v1** (core-native targeted re-listen, decision 185) | merge of `fable/e4v1` (`84a62499`; worktree merge of master clean) | merged. Node wired, receipt persisted, `--mode relisten` scoring; the budget-accounting fix included. Carries the supply-router test fix (`87146390`; 128 passed across the finite-supply binding, release-alternates and supply-variant interleaving tests) |
| **E4-1** (the core-native targeted re-listen, shadow delivery on TRAIN Fold A) | merge of `fable/e4cell` (`29e89a5c`; worktree ledger conflict resolved by keeping master's rows and appending the five E4-1 DRAFT rows, no shared run ids) | countersigned (`f989bc5f`), **flipped** (flight commit `e9777e18`) and queued as `SAEA-Queue-E4` after W4-SV; a 4-row dry run precedes the arm |
| **COMP-1 seal-only completion** (option A of decision 189) | merge of `fable/comp1seal` (`ad0f0d8e`; worktree merge of master clean) | registered **HELD** pending owner decision 189. `resume_from` = the original attempt (471 kept rows) + attempt 3 (609 rows); replay proof 1,080 rows / 0 failing / 0 sealed twice; `cli seal-only` refuses held cells and scores after the seal. The `--include-held` blocking set is unchanged (9 cells) |
| **E4-1 seal fix and seal-only completion** (decision 194 pending) | merge `109538e8` of `fable/e4sealfix` (fix `b286d8974`; worktree merge of master clean, 1,196 targeted tests pass); registration `9c9ee145` | fix merged. Seal-only cell `slurp-native-stage3-relisten-fold-a-v1-resume` registered **HELD** (`docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1/`): `resume_from` = the aborted attempt (1,080 kept rows), zero contacts. Replay proof 1,080 / 0 failing / 0 sealed twice. The registration gate treats the cell as historical (run directory exists), so it reports no finding. Flip / chain / mint: `scripts/flights/e4/e4_sealonly_flip.sh`, `batch_chain_e4_sealonly.sh`, `e4_sealonly_mint_receipt.py` (not run) |
| **Idle watchdog** (decision 182): one tick every 5 min; never launches onto a STOP (except a proven server-death STOP), respects hold files, ready-chain list `scripts/flights/batch/ready_chains.json` (`allowed_carriers: [slurp]`), server-death and 12 h uptime restart | merge `bdaa66b4`; `saea_task.ps1` repetition fix `8d36213f` (PS 5.1 refused `-RepetitionDuration MaxValue`) | Windows task `SAEA-Watchdog` registered and **PAUSED** by `/home/chao/saea-queue/watchdog.hold` (the coordinator removes it). First ticks 00:20:58Z / 00:21:59Z: "busy, exiting quietly" (stale flight lock + parked queue script); nothing launched |
| **W-SV-1 column read** (same-flight supply variant, Solver train-exemplars k 30, TRAIN Fold A, n = 1,080; READ row `SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1`): twin null SLU-F1 +0.37 [-0.14, +0.92] (half-width 0.53), intent 0.00 (identical on all 1,080 rows); b-exk30 vs a-base SLU-F1 -0.46 [-1.85, +1.12], intent +0.37 [-0.09, +0.93] (6 saves / 2 harms) | `docs/results/2026-09-29-slurp-wsv1-fold-a-column-read.md` (merge of `fable/wsv1read` `3a6cb9cb`, with the `wsv1_read.sh` module-registration and `stage3_paired_read` column-arm fixes; verdict `aaa9b573`) | **NOT NOMINATED (inert)** (coordinator); instrument: intent null 0.00, SLU null hw 0.53. The exemplar-k line is closed at k 30 on this roster; nothing is admitted or closed for the composed policy (claim ceiling nominated, phase-1 ruling Q6). Development number (decision 28) |
| **W4-SV column read** (same-flight supply variant, release swap to `slot-contracts-w4-v1`, TRAIN Fold A, n = 1,080; READ row `SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1`): twin null SLU-F1 +0.43 [-0.19, +1.04], intent +0.09 [-0.19, +0.46] (3 discordant rows); b-w4 vs a-agree SLU-F1 -0.15 [-1.40, +1.11], intent +0.19 [-0.46, +0.83]; contrast half-widths SLU 1.25 / intent 0.65 | `docs/results/2026-09-29-slurp-w4sv-fold-a-column-read.md` (merge of `fable/w4svread` `c2ebffe4`; verdict `5dfc7791`) | **NOT NOMINATED (width)** (coordinator): not resolvable at n = 1,080; rule-card conventions line closed for same-flight reads (reopens only cross-flight on DEV-2000-ADDED or larger behind a TRAIN above-floor mechanism); SLU main line stays W5 (decision 170, held). Decision 190 anchors amended to intent 0.65 / SLU 1.49. Outstanding: the per-type TP/FP/FN table over the 19 changed cards (model-free, descriptive). Development number (decisions 28/86) |
| **Sealed-credit inner loop run 1** | `docs/results/2026-09-29-slurp-sealed-credit-inner-loop-run-1.md` (merge `f52af202`) | Sealed-credit inner loop run 1 landed (model-free, DESCRIPTIVE): mechanical rule nominates `phase_supply.k = 10` (+0.48 pp intent predicted, CI95 crosses zero, folds -0.33 / +1.24); registration held pending the coordinator's floor re-calibration ruling (owner decision 190 proposed: same-flight floor from the measured contrast half-widths, amended after W4-SV to intent 0.65 / SLU 1.49, not the twin null 0.3163). |
| **Same-flight floor re-calibration** (model-free impact note) | `docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md` (merge `67a6acad`) | Proposed owner decision 190: per-metric same-flight anchors from W-SV-1's contrast, intent 0.5093 / SLU 1.4866 at n = 1,080 (vs the provisional 0.3163), **amended after W4-SV to the larger of the two measurements, intent 0.65 / SLU 1.49**; no queued cell is refused; W4-SV (0.79) is underpowered on SLU; the inner-loop run-1 nomination (`phase_supply.k = 10`, +0.48 pp) no longer clears. The FLOOR_TABLE diff is text only, not applied. |
| **COMP-1 Fold A paired read** (seal-only arm, decision 189-A; READ row `SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1`, n = 1,080 vs the in-chain A/A): intent +4.26 [+2.41, +6.11] (76 / 30), official SLU-F1 -2.24 [-3.97, -0.47]; entity FP 497 -> 611; newly delivered 38 / 78 convert (newly-by-both 30 / 47) | `docs/results/2026-09-29-slurp-comp1-fold-a-read.md` (merge `99c5b004`; countersign `cf38bec3`) | DESCRIPTIVE; HARMFUL branch on the SLU-F1 guard, intent clears its declared 3.23; coordinator verdict pending |
| **Consumption-module design** (decisions 195/196) with coordinator rulings R1-R5 | `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` (merge `d51063b4`) | merged; docs only |

### What the wave taught

No knowledge-form item moved the numbers at the cross-flight floor: W1 (card selection), W3a (intent
contrast cards) and W4 (slot conventions) all read within width against the shared in-chain A/A. Only W1
saved cost (-3,379.5 prompt tokens per row, -8.0 % GPU-h); W3a's saving came with a negative intent point
estimate and W4 cost more than registered. This is consistent with
`docs/results/2026-09-27-slurp-mechanism-synthesis.md` section 2.1: gains need row-matched content at the
deciding node, not a new form of the same content. Effects of W4's size (about 0.8 pp) go to the same-flight
supply-variant instrument, not to another cross-flight cell.

Before set B merged, `core.flight.cli check` on the E41 sub10 cell and the `-REC` arm read `ready` with `prepared_artifacts_ok: true` and unchanged hashes. After set B, `-REC` and RANKVIS read `prepared_artifacts_ok: false` on master by design (the isolation fact above); they stay ready at their flight commits. No `cli check` runs while the queue is live.

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

**Owner rulings received (decisions 175-199, 2026-09-28 / 29).** None open; 197-199 are listed below.

1. 175: COMP-1 recovers by RESUME; `-REC` superseded unflown; the resume is the flight's one recovery.
2. 176: `kb_policy` digest lock re-pinned (`cfd34bf5`).
3. 177: successor receipt `A2T-CANONICAL-FAMILY-SECONDARY-FIXED8-v2.json` issued (`3d02f68f`); v1 untouched.
4. 178: K1-as-cards closed; contrast evidence only at the decision node. After E1, the deciding node for intent is Perception's shortlist.
5. 179: offline rule designs on multi-sample pools discontinued; W-SV-1 and W4-SV are registered on master and held.
6. 180: core-native re-listen first; Whisper waits for E4's read; E1-E6 adopted. E1 has landed; E3 and E4 are designed and merged.
7. 181: option A ruled; the diagnosis found a server CUDA abort, so the outcome is a direct retry under decision 22 (attempt 2 at `c24824a4`), which then STOPped on the fit-identity refusal.
8. 182: idle watchdog authorised; merged `bdaa66b4`; task `SAEA-Watchdog` registered paused by `watchdog.hold`.
9. 183: card order RANKVIS -> W-SV-1 -> W4-SV -> sub10 -> filler (sub10 then deferred by 187).
10. 184: P-SV-1 / P-SV-2 registered after merge set C; set C and `fable/psv` are merged, both cells held, P-SV-1's contrast-pair table pinned.
11. 185: E4 v1 is the next engineering item after set C, with a 4-row dry run before its flight.
12. 186: Fold B is ROLLOUT-exposed while it is the phase-2 read roster.
13. 187: SLURP only on the GPU; E41 sub10 deferred (ready at `bf6db903`, disabled in the watchdog list).
14. 188: REV-TFRL-1 NOT ADMITTED; B5 deferred behind P-SV-1 / P-SV-2; row 165's route open.
15. 189: option A; COMP-1 seal-only completion countersigned (`b3984358`), flipped with G5 at `fd8a01fe`, queued as `SAEA-Queue-SEALONLY` (restarted 14:39Z without the P-SV wait); seal-only COMPLETED ~14:44Z, read landed `99c5b004`; G5 flying.
16. 190: same-flight floors per metric, intent 0.65 / SLU 1.49 at n = 1,080; merged `c2f1be08`; inner-loop run 1 nominates nothing.
17. 191: rule-card slot-convention line CLOSED; no re-fly in any design.
18. 192: W5 held; >= 1.5 pp offline prediction required for any SLU mechanism; the headroom note (merged `949d77d1`) finds none; W5 line closed by the coordinator.
19. 193: P-SV GO; flipped `b9af3e58`; P-SV-1 flew all rows and ABORTED at seal on I7v (14:19:36Z); P-SV-2 held back until the receipt fix and its re-pin (header). Decision 197 GO (P-SV-1 seal-only recovery), waiting for the I7v fix on `fable/psvsealfix`.
20. 194: E4-1 seal-only completion GO; countersigned `b3984358`, receipt minted, column gate pre-declared; residue fix merged `0ef6d98c`; flipped at `0b50d47e`, queued as `SAEA-Queue-E4SEAL`.
21. 195: option B (USE-layer node action inside COMP-2; one consumption module that may call the model), recorded `da979818`.
22. 196: owner directive, carrier-agnostic consumption module (Audio2Tool, Earnings-21, Earnings-22 after stable SLURP gains), recorded `da979818`; design merged `d51063b4` (rulings R1-R5).
23. 197: P-SV-1 seal-only completion GO; registered and countersigned `a842f670`, flipped to ready `e42e87f3`; the flip was refused on the parent-package residue (cell ready-unconverged), fix on `fable/repinresume2`.
24. 198: COMP-1 NOT ADMITTED (HARMFUL on the SLU-F1 guard; cause: the Solver citation contract); option B -- COMP-1b (AGREE + centroid key, no citation contract) held on `fable/comp1b`, then A2 = COMP-1b on DEV-2000-ADDED; recorded `f26e3cdb`.
25. 199: owner directive, empty supply and none slots are first-class outcomes; recorded `f26e3cdb`; module design section 2c `c0067e0e`; offline analysis on `fable/emptysupply`.

**Pending branches (not merged):** `fable/repinresume2` (the parent-package residue fix for the P-SV-1 seal-only flip); `fable/comp1slu` (COMP-1 SLU harm attribution); `fable/comp1b` (COMP-1b registration, held); `fable/emptysupply` (supply-abstention offline analysis, dispatched); `fable/psv3` (P-SV-3 registration, boundary-depth column). `fable/psvsealfix` is merged (`0177f83f`). `fable/moduledesign` is merged (`d51063b4`), `fable/comp1read` is merged (`99c5b004`). `fable/repinresume` is merged (`0ef6d98c`). `fable/floor190` (merge `c2f1be08`) and `fable/w5offline` (merge `949d77d1`) are merged today, after `fable/e4sealfix` (merge `109538e8`), `fable/psvrepinfix` (merge `4b1283e0`) and the earlier set. **Pending engineering:** the residue fix (`fable/repinresume2`), then P-SV-1's seal-only flip convergence (decision 197), P-SV-2's re-pin and P-SV-3's flip; the registration gate's direct check of seal-only decision receipts (header). Queue order: `SAEA-Queue-SEALONLY` (COMP-1 seal-only + G5, `fd8a01fe`) -> `SAEA-Queue-E4SEAL` (E4-1 seal-only, `0b50d47e`) -> filler; `SAEA-Queue-PSV` stays halted.

**Remaining test failures:** the tests that call a bare `python`, which is not on the WSL PATH (environment, not code). The supply-router test failure found during E4 v1 (a bare `object()` double refusing the bolted-on binding) is fixed (`87146390`).

**Offline reads closed today:** B3 CATCHALL **INERT**; B4 EMPTYENT **INERT-BY-INSTRUMENT** (size any offline rule on a multi-sample pool against the 1.547 pp null, not 0.67).

**Wave state (decision 164, one change from the AGREE bytes each, one shared A/A):**

| cell | state |
| --- | --- |
| Shared A/A | Registered and proven IDENTICAL to AGREE. |
| W1 | Card selection. Sealed and read: **NEUTRAL (no-harm holds; retained as an enabler).** |
| W2 | Stopped offline. |
| W3 | W3a alone. Sealed and read: **NOT ADMITTED (neutral by width; the card form of K1 is closed).** |
| W4 | Slot conventions. Sealed and read: **NOT ADMITTED (neutral by width)**; re-registered as the first cell of the same-flight supply-variant instrument's phase 1. |
| W5 | Held (outcome of 170). |

The wave (W1, W3a, W4 on the shared A/A) flew at `5f8b4c9d`, launched fresh after the COMP-1 + G5 STOP, and is complete: all four arms are sealed and read. REV-TFRL-1 flew in the same queue and is read: **NOT ADMITTED (neutral by width with a measured cost)**.

**Same-flight supply-variant instrument (decision 172).** Merge set A (`2cef09ec`) and merge set B (`0f17a5e1`) are both on master. Set B touches identity-bound implementation files; the queued flights fly at their own flight commits and are not affected. VAR-2 as a mechanism stays closed. Its first real phase-1 cells are W-SV-1 and W4-SV (arm A = the AGREE Solver supply, arm B = the W4 conventions, twin = a replicate of A, `arm_visits: "first"`, claim `"nominated"`): W-SV-1 is sealed and read (b-exk30 NOT NOMINATED, inert; intent null 0.00, SLU null hw 0.53), and W4-SV is sealed and read (b-w4 NOT NOMINATED, width; intent null +0.09; the rule-card conventions line is closed for same-flight reads). Phase 2 (Perception variants) is set C plus P-SV-1 / P-SV-2: re-derived with the v2 table pin (`ec9e1b65`), P-SV-1 minted, the first flip cycle refused on a branch-seed re-pin identity mismatch (fix on `fable/psvrepinfix`); both cells held.

## 7. My next action

1. COMP-1 is NOT ADMITTED (decision 198; cause the citation contract): merge `fable/comp1slu`, then flip and queue COMP-1b (`fable/comp1b`) after the P-SV flips; A2 = COMP-1b on DEV-2000-ADDED follows its read. G5 is flying (`SAEA-Queue-SEALONLY`, `fd8a01fe`); read it against the shared A/A when sealed.
2. E4-1 seal-only runs next (`SAEA-Queue-E4SEAL`, `0b50d47e`); read the columns against the pre-declared gate; then the filler runs inline. SLURP only (187).
3. P-SV-1: land the parent-package residue fix (`fable/repinresume2`), converge the decision-197 seal-only flip (no re-fly); then re-pin P-SV-2 and flip P-SV-3 (`fable/psv3`); read under the decision-190 floors.
4. Build the one consumption module from the merged design (195/196, `d51063b4`; section 2c for decision 199, supply abstention, pending the `fable/emptysupply` analysis); remove `/home/chao/saea-queue/watchdog.hold` once `ready_chains.json` names the next ready chain.
5. Declare A2's `expected_effect_pp` from the COMP-1b read (A2 = COMP-1b on DEV-2000-ADDED, decision 198) by its formula (row 139), then flip and queue A2.

## 8. Housekeeping we share

WSL2 `Ubuntu-24.04`, `/home/chao/.venvs/speechrl/bin/python`, English documents, one generating flight
plus one scorer, merge finished work into master promptly, keep both entry points short and current.
When you land a result, my freshness check will fail until I refresh this file — that is the intended
signal, not a conflict.
