# Stage-3 fast-validation board (living document)

Owner directive 2026-09-24: analyse and summarise the technical routes that can be validated
QUICKLY, validate them fast, and refresh this board whenever a new experiment result lands.
Maintainer: the root coordinator (Fable 5.1). Every entry names its target bad class, its expected
information per GPU-hour, its read protocol and its current status. Numbers are development
numbers (decisions 28 / 86). Comparators are sealed; the own-null margins are Fold A h_SLU 1.2485 /
h_intent 0.9943 and DEV-2000-ADDED h_SLU 1.2525 / h_intent 1.1520.

Refresh log (newest first):

- 2026-09-24 18:30 UTC -- board created after owner decisions 111-114; CELL-3 arm read, twin
  flying; two zero-contact reads in flight (bad-case bank, offline sample aggregation).

## A. Ranking rule

A route is admitted to the board when it (1) names the bad class it moves, (2) has a recoverable
upper bound >= 2 pp pooled SLU or >= 2 pp intent on the target roster (the measurement floor is
about +-1.3 pp pooled at n = 1,000 across flights), (3) can be read within one day, and (4) costs
<= 4 GPU-hours before its first read. Routes are ordered by expected information per GPU-hour;
zero-GPU reads come first.

## B. The board

| # | route | target bad class | first read | GPU-h to first read | status | result |
| --- | --- | --- | --- | ---: | --- | --- |
| F0 | **Bad-case bank** of the locked plan (typed, counted, runtime-observable signatures, stable-wrong vs flipping, headroom per class) on Fold A and DEV-2000-ADDED | all | zero-contact script over sealed arms | 0 | RUNNING (branch `fable/badcases`) | pending |
| F1 | **Offline sample aggregation** over ROLL-1's five sealed samples (R0 single, R1 medoid, R2 intent-plurality medoid, R3 support-filtered s = 2/3/4, oracle best-of-5), with the deterministic-checker filter (legal intent, intent -> legal slot types) | greedy diffuseness (225 / 625 rows disagree); entity FP | zero-contact script over sealed samples + per-sample official scores | 0 | RUNNING (branch `fable/agg`) | pending; gate for AGG-1 is >= +1.5 pp SLU vs single with an I7-compatible rule |
| F2 | **A/A within-flight null**: the identical PLAN prompt twice inside one flight on 200 R01C rows (paired per row) | measurement floor | paired per-row delta distribution | ~0.4 | READY TO REGISTER | the within-flight paired half-width decides whether variant rollouts can be read at n = 200 |
| F3 | **ROLL-2-VARIANTS**: K = 4 exemplar-construction variants per row on R01C (k in {5, 8, 12}; selection speech-neighbour / candidate-intent-aligned / slot-type-matched with empty-entity share; raw-line vs structured rendering) + the A/A control, one flight, Solver only, dense rewards (entity F1 by type, FP mass) | entity FN (date) and FP (empty-gold rows), same-type filler distance | group-relative advantage per variant per state (predicted scenario, candidate margin, channel) | ~1.5 | DESIGN (needs F0 headroom + F2 null) | -- |
| F4 | **Perception coverage rollout**: 4 candidate-construction variants (K, neighbour-intent union, general fallback position, card order), one Perception contact per row per variant on Fold A; reward = gold-in-candidates coverage (dense, 0/1 per row) | intent by candidate coverage (own card absent -> 17.3 % covered) | coverage per variant per state; the plan's intent is retrieval-driven | ~1 | DESIGN | -- |
| F5 | **Per-intent legal slot-type constraint** at the delivery node (llama.cpp json_schema / grammar): offline first (count illegal-type and type-swap mass on sealed arms), then a four-row form smoke and a Fold A cell | type swap (4.7 %), illegal types, part of FP | offline mass count; then admission rule | 0 then ~2 | DESIGN | -- |
| F6 | **Bootstrapped demonstrations**: the core's own gold-verified rollout outputs (from ROLL-1 / ROLL-2) rendered as exemplars in the model's own output format, retrieved by speech key, replacing or adding to TRAIN gold exemplars (DSPy-style bootstrap; ExpeL-style successful trajectories) | conventions, entity FN / FP | inside F3 as a source variant | (in F3) | DESIGN | -- |
| F7 | **AGG-1** inference-time selection cell: adaptive N (N = 5 only when the first two samples disagree) + deterministic verifier + medoid commit; Fold A vs PLAN, then DEV | greedy diffuseness | admission rule at own null | ~3.5 (+3.5 DEV) | GATED by F1 | -- |
| F8 | **Reviewer with evidence**: the Reviewer sees the sample disagreement, per-entity support counts and checker results instead of one draft | review loop inert (ACCEPT 98.4 %) | inside F7's form (a variant of the commit node) | (in F7) | DESIGN | -- |
| F9 | **Contract / instruction search** (GEPA-style on the task contract: date / time serialisation, "no entity" rule, per-type convention line), selected on DEV-remainder rows, validated on Fold A / B | date / time FN, empty-gold FP | small-batch paired search, then a cell | ~2 | LATER (after F3 / F5 show where the contract matters) | -- |

Closed routes (do not reopen): the semantic-delta APPLICATION line (gating / pruning / re-ranking
over the v1r / v2 / gepa stores) -- owner decision 111; the `general`-targeted mechanism (form
cost, upper bound 0.56 pp intent) -- diagnostic 2026-09-24; entity-FP suppression by filtering
deltas (<= 0.12 pp) -- diagnostic 2026-09-24.

## C. What each route must report

1. The target class and the recoverable mass from F0 (upper bound), so the reader can see the
   share of the bound the route recovered.
2. The paired delta with CI95 against the sealed comparator (or, for rollouts, the per-row paired
   variant table with the A/A control beside it).
3. The per-scenario table (gold scenarios on TRAIN; predicted-majority scenarios on DEV) and the
   per-channel split.
4. Cost: contacts per row, GPU-h per 1,000 rows, prefilled tokens per row.
5. The algorithm label (decision 101) and the operator(s) the route exercises.

## D. Results appended as they land

(Each entry: date, route id, roster, headline numbers, verdict, link to the read.)

- 2026-09-24 -- CELL-3 (closed line, for reference): DEV-2000-ADDED, SLU -1.44 [-2.88, -0.05],
  intent 0.00 [-1.01, +1.00]; HARMFUL by rule; loss diagnostic: noise +-2 pp on 355-row splits,
  store part -0.35, perfect gate ~PLAN (`docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md`).
