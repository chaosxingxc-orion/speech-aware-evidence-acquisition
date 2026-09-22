# Stage 3 on the locked SLURP base: training-free RL over the knowledge content and the context-engineering dimensions (design draft)

Author: the coordinator (Fable 5.1). Date: 2026-09-21. Status: DECIDED 2026-09-22 (owner decisions 80-83 and the owner's Stage-3 goal); it opens after base lock v3
(the Stage-2 seal path PLAN / PLANr / B9a-rec / B6 is complete). Owner mandate: decisions 29 (one test
read after Stage 3), 34-35 (DEV-2000), 38 (own-null margins), 42-43 (base lock v3 before Stage 3), 70 (index content
by best discriminability through training-free RL, value retrieval, context-engineering dimensions), 72 (index line
closed), 73 ((b) the offline Pareto reading first, then (a) semantic advantage with additive store deltas), 74 (measure
the verifier first), 75 (frontier tables on every verdict), 76/76a (other carriers: generalisation proofs and one
direct-versus-system comparison), 77 (GPU only through the scheduled-task queue). Survey:
`wiki/survey/workbench/training-free-rl-2026-09-21/README.md` (umbrella).

## 1. What Stage 3 optimises, and what it never touches

The policy is the frozen Qwen3-Omni core behind the API boundary; no weight, no decoding parameter of the core, no
template byte of the task instruction moves. What moves is what the harness writes into the context between rows --
the **knowledge content** and the **context-engineering dimensions** of the locked base:

| dimension | today (locked base) | Stage-3 action |
| --- | --- | --- |
| exemplar selection (SUPPLY) | speech-keyed k = 20 neighbours, fuse `saea-fuse-supplyfilter-v1` m = c = top_l = 20 | per-state k and diversification; which exemplars a state may see (additive allow / deny deltas with provenance) |
| store text (ORG) | slot-contracts v2, intent-boundaries v1, scenario hints | additive, provenance-tagged deltas to store entries (a line added to a card is an item with its own id; never a rewrite) |
| hints (USE) | none in the plan (B8c not flown) | `solver_hints` items selected per state |
| review budget | Reviewer x3, Planner x1, one revision | per-stratum iteration counts fixed by the verifier measurement (decision 74) |
| grouped sampling | N = 1 in the plan | N per stratum where the verifier's selection precision justifies it (decision 74) |
| acquisition | kind (a), budget 1 / 0 (if B9a admits it) | which findings trigger a re-query (the acquisition policy's own deltas) |
| index / rendering | closed at decision 52's defaults (72) | NOT a hand-authored variant; if the search ever selects a compressed form it must beat the full text on the frontier |

Never touched: the core, the official scorer, the roster identities, the six-node graph itself (structure search is
out of scope: survey section 6), the test split (read once, at the end: decision 29), Fold B before its single
evaluation read.

## 2. The loop (survey family 1 with GEPA's reflect-on-the-trace; owner decision 73 (a))

```
for iteration t = 1 .. T (T fixed before the first search cell; T = 3 proposed):
  1. STATE:   for every row of the CONSTRUCTION roster: the sealed Perception state (candidate intents), the supply
              the base would render (exemplar ids, card ids), the stratum (scenario), the per-row cost so far
  2. ROLLOUT: N Solver samples per row through the E2 grouped sampler (registered commit policy kept; every sample
              custodied) on the construction roster -- gold is legal here (the 2026-09-13 construction exclusion:
              no TRAIN A / TRAIN B / DEV-1000 / DEV-2000 utterance)
  3. SCORE:   per-row official SLU-F1 and intent of every sample (the official scorer on COPIES, once per manifest)
  4. ADVANTAGE (semantic): for rows where the group disagrees, the best and worst samples are shown to the frozen
              core with the row's supply and the core states, in words, what distinguished them (Training-Free GRPO's
              group relative semantic advantage; the request is a registered contact, custodied like any other)
  5. CURATE:  the statements become CANDIDATE DELTAS -- typed items with provenance (row ids, sample ids, the
              statement, the target store and entry) -- deduplicated against the store; ACE's grow-and-refine rule:
              deltas are appended, never a whole-view rewrite (brevity bias and context collapse are the failure modes
              the IDX read exhibited)
  6. SELECT:  the candidate delta set is scored offline where possible (counterfactual replay on sealed traces) and
              otherwise by a bounded validation rollout on a held construction sub-roster; selection keeps the
              per-stratum Pareto frontier (effect x prefilled tokens), not the best average (GEPA)
  7. RELEASE: the selected deltas are a new pinned store version; the base plus that version is ONE cell (readiness
              package, ledger rows, decision receipt, re-pin, queue) read on TRAIN A against the locked plan at the
              plan's own null (PLANr), with a derangement twin of the delta set as the form control
```

Stopping: the frontier stops moving on TRAIN A by more than the own null on two consecutive iterations, or T is
reached. Then ONE read on Fold B (the fresh roster; decision 29's "first evaluation read on Fold B") of the base
versus the base plus the final store version, then base lock v3 is amended and the single test read follows.

## 3. Rewards, controls, margins

- Reward for selection: per-row official SLU-F1 (primary) with intent as a guard, minus a prefill-token cost term
  whose weight is fixed before the search from the frontier's slope (decision 75); per-stratum harm flags (decision
  17) are constraints, not terms.
- Controls per released version: (i) the locked plan (no deltas); (ii) the derangement twin of the delta set (the same
  bytes attached to the wrong entries); (iii) a length-matched random-provenance delta set when the twin is not
  length-matched (the IDX lesson: the content term is an upper bound otherwise).
- Margins: the plan's own null (PLANr); a version is ADMITTED only with the SLU CI95 lower bound above zero against the
  plan and both guards non-inferior; NEUTRAL versions never enter the base.
- Reads by script (decision 58): the stage drivers of the IDX / IDXT reads generalise to `plan_cell_read.py`.

## 4. The prelude (zero GPU; decisions 73 (b), 74, 75)

Before the first search cell, two scripted analyses on sealed data:
1. the SLURP module frontier (`scripts/analysis/slurp_module_frontier.py`): the effect x cost frontier of every decided
   module, pooled and per scenario; dominated modules are pruning candidates for the base lock;
2. the verifier measurement (`scripts/analysis/slurp_verifier_measurement.py`): the Reviewer / Planner selection
   precision against official correctness, and coverage versus selection on the sealed B2 v3 rollouts; the numbers fix
   N per stratum and the Reviewer iteration count of the locked base (a verifier below the noise floor makes extra
   samples cost-only).

## 5. Budget and schedule

Per iteration: the construction-roster rollouts (about 800 rows x N = 5 at 4 contacts per row -> about 3-4 GPU-h at the
tool-free base's throughput), the advantage contacts (one per disagreeing row, about 0.3 GPU-h), the validation
sub-roster, and one TRAIN A cell plus its twin (about 2.7 GPU-h). Three iterations: about 20 GPU-h, all through the
scheduled-task queue (decision 77), with the reads and the curation in CPU time between steps.

## 6. Owner decisions (taken 2026-09-22) and the Stage-3 goal

The owner's goal (2026-09-22, translated): "the basic engineering base is set by the field's open-source training-free RL
techniques; the research then optimises and improves those capabilities; Stage 3 must end with an observable positive
gain." So Stage 3 has two layers: (A) a FAITHFUL base loop assembled from the surveyed open-source mechanics -- Training-Free
GRPO's group-relative semantic advantage, GEPA's reflect-on-the-trace proposal with Pareto selection, ACE's grow-and-refine
delta store -- flown as one registered cell family on the locked plan and read against the sealed PLAN arm at the plan's own
null (h_SLU 1.2485 / h_intent 0.9943); (B) the program's improvements on top of (A) (E36b findings-keyed acquisition with a
discriminability rule, E37 primitive Reviewer verdicts, per-scenario frontier selection), each a one-factor cell against the
(A) base. The exit condition is a CI95-proven official SLU-F1 gain on TRAIN A that replicates on Fold B.

80. N = 5 rollouts per state ("N = 5, start with that"); T = 3 iterations as proposed.
81. The rollout roster: about 800 construction rows drawn with a semantic-diversity rule over the sealed content embeddings
    (farthest-point coverage so semantically distant utterances are represented), never a TRAIN A / TRAIN B / DEV-1000 /
    DEV-2000 utterance; the draw is a registered model-free preparation with its own receipt.
82. The semantic-advantage contact may see the construction row's gold; its output enters only provenance-tagged store
    deltas, never an evaluated row.
83. Selection keeps the per-scenario effect x prefilled-token frontier ("find the frontier per scenario"); the cost weight is
    read from the frontier slope of the sealed cells.

Order of the first cells: E37 (a measurable Reviewer) -> the decision-85 pruning cells -> the (A) base loop, iteration 1 ->
E36b on the (A) base -> iterations 2-3.

### 6a. Superseded: the questions as drafted

80. T (proposed 3) and N (proposed 5, subject to decision 74's measurement).
81. The construction roster for rollouts: the 2026-09-13 construction pool (about 9,354 utterances after exclusions)
    sampled to about 800 rows, or the whole pool in one pass.
82. Whether the semantic-advantage contact is allowed to see the construction row's gold (the proposer arm may see
    construction gold under the three-dimension program; decision 2026-09-05) or only the score-ordered samples.
83. The cost-term weight (from the frontier slope) and the per-stratum frontier rule for selection.

## 7. Not claimed, not done here

No prompt-population methods (survey section 2: cost model), no structure search (section 6), no reward-guided decoding
(logits are not exposed), no learning inside an episode (section 5); no Earnings or Audio2Tool optimisation (decision
76: generalisation proofs only). Nothing here authorises a contact; every contact of Stage 3 is a registered cell.
