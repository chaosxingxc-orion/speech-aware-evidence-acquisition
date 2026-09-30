# Stage-3 re-plan v4: system-level optimisation, model-initiated tools, and the next rounds (2026-09-30)

Author: Fable 5.1 (root coordinator; planning, decomposition, review); written down by the records agent. Supersedes
`docs/readiness/2026-09-29-slurp-stage3-replan-v3.md` (kept in place as the record). Inputs: the 2026-09-29 / 30 result
notes under `docs/results/` named beside each number, the consumption-module design
`docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` (sections 2c, 2d), the E5 design and its addendum
`docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md`, the direction note
`docs/readiness/2026-09-29-research-direction-system-level-v1.md`, and owner decisions 195-206 (registry
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`). Every number is a development number (decisions 28,
86) quoted from the file named beside it; nothing here authorises a flight, a flip or an admission.

## 1. What the survey and the instrument settle

1. **The research direction changed (rows 205, 206).** Owner, 2026-09-29: 「我们调整下课题方向，0906的时候还是聚焦在如何用好主模型，现在调整为如何搭建系统并进行系统级优化」
   -- "We adjust the research direction: on 09-06 the focus was still how to use the main model well; now it is how to
   build the system and optimise at system level." And: 「工具应该是模型主动发起调用，而不是系统默认调用，否则就会陷入到自证陷阱，为什么不是ASR+LLM的组合来完成任务，而得用omni agent system！」
   -- "Tools should be invoked by the model on its own initiative, not called by the system by default; otherwise we fall
   into the self-proof trap -- why would the task not be done by an ASR + LLM combination, and why would it need an omni
   agent system!" Consequences: the object optimised is the model's control decisions through the control plane (what
   to supply, what to present, when to consult a tool); a pinned, logged tool is a system component (the 2026-09-06 "no
   transcript tokens" ruling is superseded in scope, row 201); every tool is an OFFER at one node, receipted as
   `tool_decision {offered, called, args_hash, result_hash, used_in_answer}` and read as call rate, decision precision /
   recall against an offline oracle, and conversion (module design section 2d); deterministic form normalisers (the
   delivered-row normaliser, the scope rule) are the one flagged class of system-default step. Transcripts still never
   enter the intent decision (DEV-1000 intent -0.90 [-1.68, -0.09] with transcripts in the prompt). The immutable
   research boundary of the study `CLAUDE.md` does not change.
2. **The instrument, as measured.** Cross-flight designs cost 2.5 pp at n = 1,080
   (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`). Same-flight floors per metric (decision
   190): intent 0.65 pp, SLU-F1 1.49 pp at n = 1,080 (`docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md`).
   Phase-2 Perception branches add a presence measurement: twin present bar 1.06 on P-SV-1 and 1.02 on P-SV-2 (their read
   notes). DEV-2000-ADDED own null h_intent 1.1520 (decision 169); A2's guard h_SLU 1.2525.
3. **Reads since v3.**

| cell | read | verdict | source |
| --- | --- | --- | --- |
| W-SV-1 (Solver exemplars k 30, same-flight) | SLU-F1 -0.46 [-1.85, +1.12] vs twin +0.37 | NOT NOMINATED, inert | `2026-09-29-slurp-wsv1-fold-a-column-read.md` |
| W4-SV (slot-convention release swap) | SLU-F1 -0.15 [-1.40, +1.11] vs twin +0.43 | NOT NOMINATED; slot-convention line CLOSED (191) | `2026-09-29-slurp-w4sv-fold-a-column-read.md` |
| COMP-1 (AGREE + centroid + citation contract) | intent +4.26 [+2.41, +6.11], SLU-F1 -2.24 [-3.97, -0.47] | HARMFUL on the SLU guard; NOT ADMITTED (198); cause: the Solver citation contract (+102 false positives on 414 zero-gold rows) | `2026-09-29-slurp-comp1-fold-a-read.md`, `2026-09-29-slurp-comp1-slu-harm-attribution.md` |
| COMP-1b (AGREE + centroid, no citation contract) | intent +3.80 [+1.94, +5.65], SLU-F1 -0.60 [-2.29, +1.07]; zero-gold emission 161 vs A/A 162 | **NOMINATED (intent)**, not admitted; A2 is the admission test | `2026-09-29-slurp-comp1b-fold-a-read.md` |
| E4-1 (core-native targeted re-listen, shadow columns) | replace-only SLU-F1 -4.11 [-5.41, -2.88]; replace + drop -3.59 [-5.08, -2.14] | SHADOW HARM; core-native re-listen CLOSED; route moves to E5 (201, 206) | `2026-09-29-slurp-e4-relisten-fold-a-column-read.md` |
| G5 (Reviewer instruction repair) | intent +0.09 [-1.02, +1.20], SLU-F1 -0.38 [-1.78, +1.04]; tool narration 1,088 -> 0; GPU-h 1.68 -> 1.60 | no-harm efficiency item; enters lock v2.1 (204) | `2026-09-29-slurp-g5-fold-a-read.md`, `2026-09-30-slurp-v2-1-lock-v1.md` |
| P-SV-1 (top-2 contrast note at Perception) | level-2 intent -0.19 [-0.56, +0.19]; present -1.85 [-2.96, -0.83]; rank-2 conversion 41.5 % vs 19.5 % | NOT NOMINATED; closed as a Perception component; rank-2 conversion kept as a Solver-side knob | `2026-09-29-slurp-psv1-fold-b-branch-read.md` |
| P-SV-2 (forced three-candidate list) | present +0.37 [-0.37, +1.20]; level-2 SLU-F1 +0.81 [+0.11, +1.66] beside | NOT NOMINATED on presence; `min_candidates = 3` kept as an inner-loop knob | `2026-09-30-slurp-psv2-fold-b-branch-read.md` |
| Inner-loop run 2 (model-free) | only AGREE + centroid (= COMP-1b) clears its floor; + scope rule SLU +1.76, + none hint +1.93 (upper bounds) | nothing new to register | `2026-09-29-slurp-sealed-credit-inner-loop-run-2.md` |

4. **The named blank for 95 is boundary recall.** Gold is off the Perception list on 83 of the 153 wrong AGREE rows, 49
   of them still in the boundary block (`docs/results/2026-09-28-slurp-node-information-gain-ledger.md`). P-SV-2 shows a
   longer note does not bring it back; P-SV-3 (boundary depth, `b-depth`: fuse_coverage m and top_l 8 -> 12) decides
   whether the gap is DEPTH or KEY. If depth does not move presence, the key side is the next mechanism, with an offline
   prediction over the floor before any cell.
5. **Closed lines** (do not re-fly): everything closed in v3, plus the citation contract as a COMP-2 component (198; may
   return only as its own single-factor cell with an entity-emission limit), core-native replacement re-listen (E4-1),
   the Perception top-2 contrast note (P-SV-1), and the system-applied transcript check E5-2a as a runtime candidate
   (206; kept only as the oracle's upper bound).

## 2. The rounds

One resident geometry at a time; SLURP only on the card until the SLURP lock (decision 187); filler rollouts on Fold B
take every gap.

| # | round | reads against | status |
| --- | --- | --- | --- |
| R1 | P-SV-3: Perception boundary-depth branch, TRAIN Fold B, gold-on-list primary | twin present null, floors of 190 | flying at `c6e98e6b` since 23:25Z (decision 200) |
| R2 | A2: COMP-1b on DEV-2000-ADDED (arm + in-chain A/A), declared +3.80 intent, guard h_SLU 1.2525 -- the dev-admission test | in-chain A/A | queued as SAEA-Queue-A2 at `310110be`, after R1; v2.0 bytes |
| R3 | COMP-2 scope-rule stage column: `saea-deliver-scope-rule-v1` applied offline to A2's sealed delivered column (0 GPU) | A2's own delivered column | script prepared on fable/milestoneprep; after R2 seals (decision 203) |
| R4 | Milestone test-sample read (`SLURP-TEST-SAMPLE-3010-V1`, decision 151 allowance) | -- | GO once A2 reads NOMINATED or better (decision 202); package held on fable/milestoneprep; one-shot |
| R5 | E5-0 (one pinned Whisper pass, tool contact, no core contact) at a 12-h serving restart, then E5-1 (model-free decision oracle: base rate b, upper bound) | -- | prepared on fable/e5prep; instruments and oracles only (201) |
| R6 | E5-2: the tool offer `verify_span(entity_index)` at the Solver's slot-value step | same-flight column if module columns reach the Solver by then, else cross-flight vs in-chain A/A; three-part gate (row 206, proposed) | only if E5-1's oracle justifies it |
| R7 | Consumption-module step 6: COMP-1b as the first module block; a harness `module` switch whose OFF arm is the lock layer; delivered-path Perception axes rendered only when a component is nominated; 6a supply abstention (AT-M5) | AT-M0 to AT-M5 byte proofs | after R2's read names the component list |
| R8 | Lock v2.1 (v2.0 + G5 Reviewer template) becomes the base and A/A for cells registered after A2 seals; AT-M0 re-proven on v2.1 at the next module step | -- | decision 204; `docs/results/2026-09-30-slurp-v2-1-lock-v1.md` |
| R9 | Inner-loop run 3 on the new pools (P-SV-1/2/3 branches, A2, scope column, E5-1 oracle), with the knobs recorded today (Solver-side contrast, `min_candidates = 3`, none hint) | floors of 190 | after R2, R3 and R5 |
| R10 | Carrier transfer of the module (Audio2Tool, Earnings-21, Earnings-22): module-all-off A/A on each carrier's roster first | per carrier | after the SLURP lock (decisions 187, 196) |

No if-then on unread results (decision 139). Admission rule unchanged: an item enters a composed arm only after its
predecessor is replicated or root-caused (decision 138).

## 3. Training-free RL: shortfalls and changes

| shortfall (measured) | change | instantiated by |
| --- | --- | --- |
| Perception presentation knobs do not move recall: P-SV-1 lowers presence, P-SV-2 does not raise it | Stop presentation variants at Perception; test depth (P-SV-3), then the key side; move the contrast to the Solver where it converts | R1, R9 (Solver-side contrast knob) |
| A system-applied verifier is the "ASR + LLM" form (206); E4-1's forced system re-listen harmed SLU | Tools become offers; the inner loop credits the DECISION node (when to call) for tool calls before the tool's quality | R5, R6; `SEALED_CREDIT_SYSTEM_POLICY_V1` decision-node credit |
| Gate-shaped nodes (Reviewer, tool decisions) show no gain when reach is low | "Reach before quality": a gate-shaped node, including a tool decision, is read first on its reach (call rate in band, decision precision above base rate), then on conversion | the three-part E5-2 gate (row 206, proposed) |
| Forced emission harms: the citation contract added +102 false positives on 414 zero-gold rows | Empty is legal (decision 199): supply abstention and answer-side none are first-class outcomes, receipted, never padded | module section 2c, step 6a (AT-M5); none hint as an inner-loop knob |
| SLU mass is consumption, not supply | Deterministic form actions read as stage columns on sealed outputs where possible (0 GPU) | R3 (scope rule on A2) |
| The inner loop tunes only on the pools it has | Feed run 3 the P-SV branches, A2 and the E5-1 oracle | R9 |

## 4. Coordinator checkpoints (script-run, not prose)

- Every launch: `flight_registration_check.py`, `cli check`, the offline gates (`stage3_effect_floor_check.py` with
  `primary_metric_key`, `finite_completion_policy_check.py`, `stage3_algorithm_label_check.py`), and the handoff
  freshness stamp.
- Before R3: A2 sealed and its READ row countersigned; the scope-rule table receipt
  `docs/receipts/knowledge/slurp-scope-rule-table-v1.json` unchanged.
- Before R4's first contact: A2's coordinator verdict is NOMINATED or better and is reported to the owner (decision 151's
  gate); the package's run ids are one attempt each.
- Before R5: the umbrella `docs/datasets.lock.json` carries the pinned Whisper `.pt` entry (E5 ruling Q3), and E5-0 is a
  queue chain step at the 12-h restart under the driver lease (Q4), recorded in `docs/exposure-ledger.md` first.
- Before R6 registers: E5-1's b is frozen, the offer's schema is one function with one integer parameter rendered only
  in the Solver's request, and `tool_catalog_check.py` pins the wrapper.
- Before R7: AT-M0 to AT-M4 hold on master; the lock layer moves to v2.1 only in that step.

## 5. Decisions the owner is asked for

1. **Confirm the E5-2 gate numbers** (row 206, proposed by the coordinator): (1) call rate within
   [max(0.01, 0.5b), min(0.50, 4b)]; (2) decision precision >= b + 0.10 and >= 2b, CI95 lower bound above b; (3)
   conversion >= +1.49 pp whole-roster on the called rows with CI95 lower bound > 0, a whole-column SLU-F1 guard and 0
   intent rows differing (2.5 pp in place of 1.49 if the read is cross-flight).

Nothing else is open.
