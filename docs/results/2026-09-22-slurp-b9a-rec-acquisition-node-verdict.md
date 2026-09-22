# NON-INFERIORITY NOT PROVEN, NODE INERT -- cell B9a-rec: the Acquisition node (kind (a) knowledge re-query) as one factor on the locked default plan, SLURP TRAIN Fold A, 1,080 rows

**The preregistered rule names NEUTRAL / ADMITTED / HARMFUL, and this read reaches none of them.** The primary
guard (official pooled SLU-F1) is non-inferior at the plan's own null; the intent guard is NOT (its CI95 lower
bound -1.098 lies below -h_intent = -0.994 while the point estimate is exactly 0.00 with 13 saves and 13 harms).
There is no measured loss on either guard, so decision 25's HARMFUL does not apply; the status is
NON-INFERIORITY NOT PROVEN, by interval width alone. **The acquisition read explains why nothing could move:**
18 rows routed `ACQUIRE`, and every one of the 18 acquisitions returned zero items. The node fired and acquired
nothing; the arm is the locked plan plus greedy-decoding drift. The root cause is a named component (section 4):
the E36 binding re-runs the Solver's own prepared supply and then excludes exactly that supply.

Read 2026-09-22 by the coordinator, model-free: the stage driver `plan_cell_read.py` (the PLANr copy patched at
`_contact_index` for the zero-contact acquisition visit, sha256 `0c5bd1fdf6b5466a...`) with the per-cell registered
facts `registered-b9arec.json` (comparator PLAN; own null PLAN / PLANr), analysis root
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-PLAN-ACQUISITION-B9A-RECOVERY-PAIRED-ANALYSIS-V1/`; plus the acquisition read
`acquisition-read.json` (sha256 `63548923a974e667...`, its script `b9arec_acquisition_read.py`, sealed outputs and
sealed per-sample official scores only).

**Exposure.** Zero model, tokenizer, encoder, ASR, server, GPU, paid-API and network contacts; registered model-free
scorings over copies only; no sealed file opened for writing; no utterance text, transcript, gold or model output
printed. **Claim boundary.** Development numbers (decisions 28, 86), TRAIN Fold A, official `evaluate.py` at
8eb16545; no test, superiority, generalisation, component-causal or cross-carrier claim.

## 0. The arm

Run `SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-V1` (the one recovery of the aborted B9a arm, after item E36
bound the kind (a) re-query in the production runtime), FINALIZED at flight commit 942aab16, flown by the
SAEA-Batch-Chain-B9arec scheduled task: 1,080 rows, 4,420 contacts (4.09 per row; histogram 2: 11, 4: 1,032,
7: 37), 12,642 repeated speech seconds, 0 tool calls, one official complete score, 1.683 GPU hours. Four-row smoke
sealed first (16 contacts, no smoke row routed ACQUIRE).

## 1. Gating contrast, B9a-rec against the sealed PLAN arm (the plan's own null)

Paired whole-speaker bootstrap, 10,000 draws, seed 20260915, 125 clusters; margins h_SLU 1.2485 / h_intent
0.9943 (PLANr, reproduced to the registered digits by this read).

| guard | PLAN | B9a-rec | delta pp | CI90 | CI95 | saves / harms / ties | non-inferior at h |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| official pooled SLU-F1 (primary) | 63.6304 | 63.8888 | +0.2583 | [-0.944, +1.379] | **[-1.187, +1.603]** | per-row SLU 53 / 58 / 969 | yes (-1.187 > -1.2485) |
| intent (scenario_action) | 82.2222 | 82.2222 | **0.0000** | [-0.930, +0.895] | **[-1.098, +1.079]** | 13 / 13 / 1,054 (McNemar p 1.0) | **no** (-1.098 < -0.9943) |
| equal-scenario weighting | | | SLU +0.063, intent 0.000 | | | | |

Other official numbers: scenario 87.2222 (PLAN 87.3148), action 83.3333 (83.5185), span-F1 53.7513 (53.7755,
delta -0.02 [-1.80, +1.59]). Under projection-v3 the two arms read 63.8888 and 63.6304 (idempotent, both carry the
v3 node). No scenario loses beyond its band; zero decision-17 flags.

## 2. The acquisition read (the decision-relevant output)

| item | value |
| --- | --- |
| rows by Planner route | ACCEPT only 1,032; ACQUIRE -> ACCEPT 18; REVISE -> ACCEPT 17; REVISE -> REVISE 2; no route (E13 finite completion) 11 |
| acquisitions | 18, all kind `knowledge-requery`, 0 contacts each, 5 to 8 state-filter tokens each |
| **items acquired** | **0 in 18 of 18** (`item_count` 0, `provenance_ids` empty, a constant 335-character empty-evidence note) |
| official outcome on the 18 ACQUIRE rows vs PLAN | intent 66.67 vs 66.67, slot-F1 18.52 vs 18.52, SLU-F1 18.52 vs 18.52: **18 ties on every metric** |
| PLAN's own route on those 18 rows | ACCEPT 16, REVISE -> ACCEPT 2 |
| rows PLAN revised (38) overlapping the arm's ACQUIRE / REVISE rows | 2 / 5 |
| the 1,032 ACCEPT-only rows vs PLAN | intent -0.19 pp (11 saves / 13 harms), SLU-F1 -0.25 pp (51 / 54): greedy drift |

Source: `acquisition-read.json`. The acquired rows carry NO information about the mechanism: the re-query
returned nothing, so the Solver's revision after ACQUIRE saw the same context it had already answered from.

## 3. Lock comparison, frontier, structure, cost (reported)

- Against the provisional lock B5e + node (63.7757 / 81.8519): SLU +0.11 [-1.37, +1.60], intent +0.37 [-0.51, +1.24]
  (`lock-comparison.json` cd0837b0...).
- Frontier (decision 75): B9a-rec 63.89 / 82.22 at 8,445 prefilled tokens per row (PLAN 8,353; +92 from the
  advertised ACQUIRE action and the 18 acquisition renders) and 1.683 GPU hours per 1,080 (PLAN 1.758); on both Pareto
  planes by cost, identical in effect (`frontier.json` 2787ab9d...). Projected 13,078-row read: 20.4 GPU hours.
- Structure: E20 compaction 0 rows; finite-completion 11 (PLAN 10); planner_action_illegal 0 (PLAN 1); ReAct
  exhaustion 0; rows with at least one REVISE 19 (PLAN 38); one normaliser receipt per row; 0 tools arrays
  (`structural.json` b1bf2ea5..., `compaction.json` 8a5ebefa...).
- Cost: 6,566 s wall, 6,061 GPU-active seconds, 40.4 contacts per minute, prompt-cache hit share 0.753, 249,324
  completion tokens; run-cumulative 4,420 of 11,880 calls and 12,642 of 33,930 speech seconds (`efficiency.json`
  40c4afa9...).

## 4. Root cause, by name, and what follows

`core/flight/runtime.py` `_acquisition_requery_binding` (item E36) re-runs `supply_for_phase(solver_phase, context)`
-- a pure function of (phase, sample), so it returns the ids the Solver already holds -- and `rails/runner.py`
passes `exclude_value_ids = request.supplied_value_ids`, which removes exactly those ids; the state-token filter
then runs on an empty set. Empty by construction on every row. The E36 wire proof substituted a real-store candidate
sample for the live supply decision and so could not see it. Kind (a) as designed (E18: "keyed by the Reviewer's
findings") needs a search of the released stores for values the row has NOT seen; the repair is item E36b
(`docs/superpowers/specs/2026-09-22-e36b-findings-keyed-requery-design.md`), to be proven by a model-free replay on
these 18 rows' recorded state filters before any flight.

**Consequences.** (1) The Acquisition node is instantiated in the harness (six nodes flew end to end, receipts and
custody complete) but is NOT admitted into the locked plan on this evidence: the plan's `acquisition` key stays off,
and no harness-admission entry is written by this read (the entry form waits for a non-inert form). (2) B9a-rec is
root-caused to a named component, so a new mechanism cell (B9a v2, E36b) is admissible under the iteration rule; it
is the owner's call (decision 43 forbids a registered absence; decision 44 built the node as everyday inference).
(3) The intent non-inferiority failure is width, not loss: two request-identical-in-effect arms differ by 13 / 13
row flips, exactly the own-null width; it says nothing about the node.

## Artefacts

`score-contrasts.json` c47e562d..., `lock-comparison.json` cd0837b0..., `frontier.json` 2787ab9d...,
`efficiency.json` 40c4afa9..., `per-scenario-tables.json` b96f7ab2..., `structural.json` b1bf2ea5...,
`compaction.json` 8a5ebefa..., `acquisition-read.json` 63548923..., `README.md` 3510aac2..., `registered-b9arec.json`.
Package `docs/readiness/2026-09-22-slurp-plan-acquisition-b9a-recovery-v1/`; recovery note
`docs/readiness/2026-09-22-slurp-plan-acquisition-b9a-recovery-v1.md`.
