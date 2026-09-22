# Item E36b: the kind (a) knowledge re-query must SEARCH the released stores by the Reviewer's findings (design)

Author: the coordinator (Fable 5.1). Date: 2026-09-22. Status: DESIGN, awaiting the owner's decision after the B9a-rec read.
Provenance: the B9a-rec acquisition read (`analysis/SAEA-SLURP-PLAN-ACQUISITION-B9A-RECOVERY-PAIRED-ANALYSIS-V1/acquisition-read.json`,
sha256 63548923...) and a read of `core/flight/runtime.py` `_acquisition_requery_binding` (item E36, fef4341e) and
`rails/runner.py` (the `acquisition_requery` closure).

## 1. The finding

Cell B9a-rec flew the Acquisition node live for the first time: 18 of 1,080 rows routed `ACQUIRE` (then `ACCEPT`), every
acquisition receipt is well formed (kind `knowledge-requery`, 0 contacts, 5 to 8 state filters), and **every one of the 18
acquired zero items** (`item_count` 0, `provenance_ids` empty, a constant 335-character empty-evidence note). The 18 rows'
official per-row outcomes are identical to the sealed PLAN arm's (18 ties on intent, slot-F1 and SLU-F1). The node is
instantiated but inert; the arm's contrast against PLAN is greedy drift only.

## 2. The root cause, by name

`FlightRuntime._acquisition_requery_binding` (E36) implements the re-query as: re-run the Solver phase's own prepared
`supply_for_phase(solver_phase, context)`, then drop `exclude_value_ids` and keep only values matching the state tokens.
`rails/runner.py` passes `phase_id = config.role("solver").phase_id` and `exclude_value_ids = request.supplied_value_ids`.
A prepared phase supply is a pure function of (phase, sample) (the 2026-09-17 B1 abort analysis), so the re-run returns the
SAME selected ids the Solver already holds, and the exclusion removes all of them: **the intersection is empty by
construction, on every row, whatever the findings say.** The E36 wire proof did not catch it because it substituted a
real-store candidate sample for the live rank/fuse decision (its own stated caveat).

Kind (a) as designed (E18: "a model-free re-query of the released stores keyed by the Reviewer's findings") needs a
retrieval over the store that the row has NOT yet seen, keyed by the findings -- not a filter over the already-supplied
selection.

## 3. The repair (E36b)

`_acquisition_requery_binding` searches the bound composite snapshot (every value of the released stores the plan binds:
slot-contracts v2, intent-boundaries, train-exemplars) for values NOT in `exclude_value_ids` whose content or associated
facet ids contain at least one state token (the same `_matches_filters` predicate), ranks by the number of distinct
tokens hit (ties by value id, deterministic), and returns at most `k` items (`k` = 5 proposed, a config key
`native_episode.acquisition.budget.max_items_per_acquisition`, OFF form = absent = today's behaviour so the flown B9a-rec
bytes stay reproducible). Zero contacts, zero network, bytes only from the hash-verified snapshot. When no value matches,
the acquisition stays empty and legal (as today).

Proofs before any flight: (1) unit tests on a synthetic snapshot: hits ranked by token count, exclusions honoured, cap
honoured, empty when nothing matches, determinism; (2) the E32 ACQUIRE -> ACCEPT wire proof with the production binding
returning a non-empty item set; (3) a model-free replay on the 18 sealed B9a-rec `ACQUIRE` rows: their recorded state
filters against the real composite snapshot, reporting items found per row (the number that decides whether a flight is
worth its 1.7 GPU hours); (4) the unarmed request-bytes test stays green.

## 4. The cell (B9a v2), if the owner admits it

One factor on the locked plan: the acquisition block with `max_items_per_acquisition` armed (the kind (a) semantics
corrected). Read against the sealed PLAN arm at the plan's own null (1.2485 / 0.9943), with the acquisition read (routes,
items, provenance, saves / harms on the acquired rows) and the frontier row. Predecessor B9a-rec is root-caused to a named
component (the iteration rule), so a new mechanism cell is admissible. Expected: still at most 18 to 40 rows routed
(the Planner's ACQUIRE rate), so the pooled effect is bounded by about 2 % of rows; the acquisition read, not the pooled
number, is the decision-relevant output.

## 5. Not claimed

Nothing about kinds (b) / (c); nothing about the Planner's routing rate (an instruction question, decision 84's cell
territory); no flight is authorised by this note.
