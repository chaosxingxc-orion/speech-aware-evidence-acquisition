# Item E36b: the kind (a) knowledge re-query must SEARCH the released stores by the Reviewer's findings (design)

Author: the coordinator (Fable 5.1). Date: 2026-09-22. Status: IMPLEMENTED 2026-09-22 (merged 289e4d51, decision 90: a Stage-3 cell). Rule as built: idf-weighted token search over the whole composite snapshot (`saea-requery-idf-v1`: min 4 chars, document-frequency share <= 0.05, visible tokens excluded, top k by score then value id); replay on the 18 sealed ACQUIRE rows: 18/18 get 5 items (store mix slot-contracts 45 / train-exemplars 42 / intent-boundaries 3; 22-697 candidates per row; median 4 tokens kept). B9a v2 cells are registered held (`configs/experiment/slurp-native-plan-acquisition-b9a-v2-v1.json`) for Stage 3.
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

## 6. Model-free replay on the 18 sealed ACQUIRE rows (2026-09-22, after the B9a-rec read)

Script `e36b_replay.py` (session scratchpad; zero contacts): the plan's three released stores loaded through the real
`load_knowledge_store_binding` (composite snapshot of 9,468 values: intent-boundaries 60, slot-contracts 54,
train-exemplars 9,354), each row's recorded 5 to 8 state-filter tokens, the crude E36 predicate (`token in content or
facet id`), the row's prepared-perception ids excluded (8 per row; the Solver's 20 exemplars are supplied from a
separate artifact and were not excluded here, so the counts are upper bounds).

| fact | value |
| --- | --- |
| rows with at least one non-visible matching value | 18 of 18 (with at least five: 18 of 18) |
| matching values per row | 58 to 9,460 (median about 2,300) |
| top-5 by token-hit count, by store (all rows) | slot-contracts 79, train-exemplars 7, intent-boundaries 4 |
| best token-hit count in a row's top 5 | 1 to 7 |

Reading: candidates exist on every row, so a findings-keyed search is not empty by construction -- but the E36
predicate has no discriminability: common tokens match thousands of values and the top of the list is the generic
slot-contract cards the Solver's context already covers by type. Before any B9a v2 flight the ranking needs a
discriminability rule (decision 70's language): weight tokens by rarity across the composite snapshot (an
inverse-frequency weight), drop tokens shorter than four characters or present in more than a fixed share of values,
and prefer values whose matched tokens are absent from the row's visible context. That rule is a value-retrieval
policy in Stage 3's action space (training-free RL over context-engineering dimensions), not a Stage-2 seal item.
Recommendation to the owner: keep the Acquisition node off the locked plan for the seal, close B9a on this evidence
(instantiated, inert, root-caused), and carry E36b into Stage 3 as the first acquisition-policy cell.
