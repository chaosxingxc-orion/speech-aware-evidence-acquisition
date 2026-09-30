# Stage-3 re-plan v5: COMP-1b admitted on DEV, the milestone read, and the rounds after it (2026-09-30)

> **Superseded by v6** (`docs/readiness/2026-09-30-slurp-stage3-replan-v6.md`, after owner decisions 207-209 of 2026-09-30); kept in place as the record.

Author: Fable 5.1 (root coordinator; planning, decomposition, review); written down by the records agent. Supersedes
`docs/readiness/2026-09-30-slurp-stage3-replan-v4.md` (kept in place as the record). Inputs: the result notes under
`docs/results/` named beside each number, the consumption-module design
`docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md`, the Solver intent-decision design
`docs/superpowers/specs/2026-09-30-solver-intent-decision-mechanism-design.md` (ruling R5), the E5 design
`docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md`, and owner decisions 195-209 (registry
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`). Every number is a development number (decisions 28,
86) quoted from the file named beside it; nothing here authorises a flight, a flip or an admission.

## 1. What the survey and the instrument settle

1. **Direction (rows 205, 206), unchanged since v4.** The owner moved the research object from "how to use the main
   model well" to "how to build the system and optimise it at system level", and ruled that tools are invoked by the
   model on its own initiative, never called by the system by default (otherwise the work falls into the self-proof
   trap of an ASR + LLM pipeline). The verbatim owner text and its English rendering stand in rows 205 and 206. So:
   every tool is an OFFER at one node, receipted as `tool_decision {offered, called, args_hash, result_hash,
   used_in_answer}`; deterministic form normalisers are the one flagged class of system-default step; transcripts never
   enter the intent decision.
2. **The instrument, as measured.** Cross-flight designs cost 2.5 pp at n = 1,080
   (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`). Same-flight floors (decision 190): intent
   0.65 pp, SLU-F1 1.49 pp at n = 1,080 (`docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md`). Phase-2
   Perception presence: twin bars 1.06 (P-SV-1), 1.02 (P-SV-2), 1.0185 (P-SV-3). DEV-2000-ADDED own null h_intent 1.1520
   (decision 169); A2's floor 2.5981 and SLU guard h 1.2525; the COMP-2 Q2 bar 1.5485.
3. **Reads since v4.**

| cell / read | numbers | verdict | source (`docs/results/`) |
| --- | --- | --- | --- |
| P-SV-3 (Perception boundary depth 8 -> 12, Fold B) | presence -1.39 [-2.31, -0.56] vs twin bar 1.0185; level-2 intent 0.00, SLU-F1 +0.01 | NOT NOMINATED, branch-local harm on presence; depth line CLOSED | `2026-09-30-slurp-psv3-fold-b-branch-read.md` |
| **A2 (COMP-1b on DEV-2000-ADDED, n = 1,000)** | intent 76.90 -> 81.50, **+4.60 [+2.58, +6.73]**; SLU-F1 **+0.53 [-1.04, +2.09]**; zero-gold emitting 153 -> 140 | **REPLICATED and ADMITTED on the development roster**; first dev-admitted composed arm; meets decision 202's condition | `2026-09-30-slurp-a2-comp1b-dev2000-read.md` |
| COMP-2 scope-rule stage column on A2 | SLU-F1 +0.49 [-0.01, +1.00]; A/A replicate +0.73 [+0.25, +1.23]; Fold A rehearsal +1.35 shrank | FAILS Q2; COMP-2 = COMP-1b alone; scope rule stays a registered no-harm deliver stage | `2026-09-30-slurp-comp2-stage-column-dev2000-read.md` |
| E4-1 (core-native re-listen, shadow columns; carried) | replace-only SLU-F1 -4.11 [-5.41, -2.88] | SHADOW HARM; route moved to E5 | `2026-09-29-slurp-e4-relisten-fold-a-column-read.md` |
| G5 (Reviewer instruction repair; carried) | intent +0.09, SLU-F1 -0.38; narration 1,088 -> 0; GPU-h 1.68 -> 1.60 | no-harm efficiency item; in lock v2.1 | `2026-09-29-slurp-g5-fold-a-read.md`, `2026-09-30-slurp-v2-1-lock-v1.md` |
| Inner-loop run 2 (model-free; carried) | only AGREE + centroid (= COMP-1b) clears its floor; scope rule +1.76 upper bound | nothing new registered; the upper bound did not survive DEV (row above) | `2026-09-29-slurp-sealed-credit-inner-loop-run-2.md` |

4. **Ceiling, recall and decision findings (all offline, zero contacts).**
   - **Structural ceiling** (`2026-09-30-slurp-intent-ceiling-under-current-components.md`): Fold A on-list recall
     92.1 %, so a perfect Solver on today's list reaches about 92-93 %; 95 % needs on-list recall near 97 % AND rank-2/3
     conversion near 50 % (today 29.5 %). DEV level: A2 81.50 % vs A/A 76.90 %; Fold A COMP-1b 85.65 %.
   - **Perception levers CLOSED** (`2026-09-30-slurp-perception-block-depth-and-recall-offline.md`): depth fails in
     both directions and the P-SV-1 Solver contrast was an artefact.
   - **Recall key** (`2026-09-30-slurp-retrieval-key-recall-offline.md`): no pinned-vector key adds more than +0.4 pp
     presence; the one lever is RANK -- K6p (centred centroid + agreement) lifts gold to block rank 1 on +22 / +26 net
     rows, about **+1.1 pp** intent predicted on both folds, with a selection disclosure (P-SV-4, row 208).
   - **Solver-node blank CLOSED under the current evidence kinds** (ruling R5;
     `2026-09-30-slurp-solver-decision-oracle-offline.md`,
     `2026-09-30-slurp-reviewer-revision-decision-instrument-offline.md`): the decision is readable (AUC about 0.78),
     but REVISE precision is 0.122 pooled and conversion 0.159, under the R2 bars 0.33 / 0.30.
5. **Closed lines** (do not re-fly): everything closed in v4, plus Perception boundary depth (P-SV-3), the scope rule
   as its own COMP-2 claim, and a Solver-side revision mechanism on the current evidence kinds (R5).

## 2. The rounds

One resident geometry at a time; SLURP only on the card until the SLURP lock (decision 187). No if-then on unread
results (decision 139); admission rule unchanged (decision 138).

| # | round | reads against | status / precondition |
| --- | --- | --- | --- |
| R1 | Milestone test-sample read (`SLURP-TEST-SAMPLE-3010-V1`; MILESTONE-01 = COMP-1b, expectation re-declared 4.6) | comparator MILESTONE-00-PLAN | decision 202 condition met; needs 207 (allowance v2 FIT ids) and sample preparations 2/3 finished; one shot, no re-fly, no re-read |
| R2 | P-SV-4: K6p key-source Perception column, TRAIN Fold B, intent primary, declared +1.1 pp vs floor 0.65 | twin present null, floors of 190 | registered HELD; needs 208; a NOMINATED read needs replication on DEV-2000-ADDED before `key-source:k6p` enters the module |
| R3 | E5-1: model-free decision oracle over the E5-0 Whisper pass (base rate b, upper bound) | -- | running (E5-0 DONE 06:23Z) |
| R4 | E5-2: the `verify_span(entity_index)` offer at the Solver's slot-value step | three-part gate (row 206, proposed) | only if E5-1's oracle justifies it and the owner confirms the gate |
| R5 | Module step 6: COMP-1b as the first module block (`agree-vote-seed` + `centroid-boundary-key`); harness `module` switch; the all-off arm is the lock layer and the A/A | AT-M0 to AT-M5 byte proofs | the component list is now named by the A2 verdict |
| R6 | Lock v2.1 (v2.0 + G5 Reviewer template) becomes base and A/A for cells registered after the module step | -- | decision 204 |
| R7 | Inner-loop run 3 on the new pools (P-SV-1/2/3, A2, the scope column, E5-1 oracle, P-SV-4 if flown) | floors of 190 | after R3 (and R2 if ruled) |
| R8 | Carrier transfer of the module (Audio2Tool, Earnings-21, Earnings-22), module-all-off A/A first on each roster | per carrier | once SLURP is closed under decision 209 (decision 196) |

**GPU risk, stated plainly.** After the E5 gap (E5-0 done; sample preparations 2/3 finishing) the filler family is
exhausted: no registered, ready cell remains that does not wait on an owner ruling. Unless 207 or 208 is ruled, the card
idles after the sample preparations end. R1 needs 207; R2 needs 208; R4 needs E5-1 and the gate; R5 is engineering plus
model-free proofs first.

## 3. Training-free RL: shortfalls and changes

| shortfall (measured) | change | instantiated by |
| --- | --- | --- |
| Perception presentation and depth do not move recall (P-SV-1, P-SV-2, P-SV-3) | Stop Perception knobs; the only remaining recall lever is the key's RANK (K6p), read same-flight then replicated on DEV | R2 |
| Same evidence kind cannot fix rank-2/3: REVISE precision 0.122, conversion 0.159 (R5) | Credit the DECISION node; a Solver-side mechanism needs a NEW evidence kind (row 209 option B), not another pass over the same supply | R5 ruling; row 209 |
| Forced emission harms (citation contract +102 FP on zero-gold rows) | Empty is legal (decision 199): supply abstention and answer-side none are first-class outcomes; A2 shows zero-gold emission falling (153 -> 140) | R5 step 6a (AT-M5) |
| System-applied verification is the "ASR + LLM" form (206); E4-1 harmed SLU | Tools are model-initiated offers, read on reach (call rate, decision precision vs b) before quality | R3, R4 |
| Inner-loop upper bounds overstate DEV effects (scope rule +1.76 predicted, +0.49 read) | Treat inner-loop predictions as upper bounds; register only above the floor and read on DEV before composing | R7 |

## 4. Coordinator checkpoints (script-run, not prose)

- Every launch: `flight_registration_check.py`, `cli check`, `stage3_effect_floor_check.py`,
  `finite_completion_policy_check.py`, `stage3_algorithm_label_check.py`, and the handoff freshness stamp.
- Before R1's flip: 207 ruled and the FIT ids in the allowance; sample preparations 2/3 DONE with receipts; the
  preflip gate at zero refusals; the per-scenario table and the attribution-class table owed by the A2 recipe are
  produced (`comp1dev_attribution_classes.py` re-run, id-list hashes reproduced).
- Before R1's first contact: the coordinator's report of the dev-admitted arm is with the owner (decision 151's gate);
  each run id one attempt.
- Before R2 flips: 208 ruled; the K6p artifact proof rows closed; claim ceiling `nominated`.
- Before R4 registers: E5-1's b frozen; the offer is one function with one integer parameter rendered only in the
  Solver's request; `tool_catalog_check.py` pins the wrapper.
- Before R5: AT-M0 to AT-M4 hold on master; the lock layer moves to v2.1 only in that step.

## 5. Decisions the owner is asked for

1. **207**: test-sample allowance v2 -- add exactly the two zero-contact FIT ids (MILESTONE-00-PLAN-FIT, MILESTONE-01-FIT)
   to the decision-151 allowance, all other terms unchanged. Gates R1.
2. **The E5-2 gate** (row 206, proposed): call rate within [max(0.01, 0.5b), min(0.50, 4b)]; decision precision
   >= b + 0.10 and >= 2b with CI95 lower bound above b; conversion >= +1.49 pp on the called rows with CI95 lower bound
   > 0, a whole-column SLU-F1 guard and 0 intent rows differing (2.5 pp if cross-flight).
3. **208**: fly P-SV-4 (K6p Perception column on Fold B) under the accepted selection disclosure. Gates R2 and keeps
   the card busy.
4. **209**: the structural ceiling -- A accept about 90 % dev intent as this design's SLURP ceiling; B open a new
   evidence kind for intent; C both (close SLURP at the measured ceiling, carry the module to Audio2Tool/Earnings under
   196, explore B offline). With the DEV numbers (A2 81.50 % vs A/A 76.90 %; Fold A 85.65 %), the coordinator
   recommends **C**.
