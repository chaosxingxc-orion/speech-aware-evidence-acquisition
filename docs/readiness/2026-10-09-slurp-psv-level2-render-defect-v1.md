# Level-2 Perception-branch Solver render defect (P-SV-1 to P-SV-4), root cause and fix

Recorded 2026-10-09 by Claude Sonnet 5.5 (engineering agent) on the coordinator's brief, in the worktree
`fable/psv-level2-render-fix` (model-free: no model, server, GPU, encoder or tokenizer contact; read-only on the data
root). Source of the finding: `docs/results/2026-10-09-slurp-psv4-fold-b-branch-read.md` section 3a. Master at the start
of this work: `7d3062d74`, working tree clean.

## 1. The defect

A level-2 Perception-branch cell (`roles.perception.branches.level = 2`) gives every non-delivering branch its own
first-visit Solver contact, whose column is read against A's. The design (phase-2 design, section 3, "Level 2") says that
contact's history carries the branch's own note, and that its slot-contract `candidate_supply`
(`candidate_state_phase: perception`) is re-resolved from the branch note. In every level-2 cell flown so far the branch
Solver request was A's request: the branch Solver never saw its own note and never received the supply that note implies.
Every level-2 branch column (B and T) in P-SV-1 to P-SV-4 was therefore an A/A replicate of A's Solver request.

## 2. Root cause

All line numbers are `rails/runner.py` at master `7d3062d74`.

1. `perception_branch_solver_messages` (2978) rendered a non-A branch's messages with
   `base_messages(replace(ctx, agent_states=_perception_note_view(ctx.agent_states, note_text=...)))` (3027). In
   `base_messages` (2645) `agent_states` feeds only the optional `knowledge_value_renderer`; the default renderer reads
   nothing from it. The swapped note therefore changed no rendered byte.
2. The note is delivered to the Solver as the exposed HISTORY (the request's `agent_state`), and that was composed later,
   in `speech_binding`, from the row's own `ctx`, not from the view: `select_native_role_history(...,
   states=ctx.agent_states, ...)` (3733 to 3735), the role-context compiler (`states=ctx.agent_states`, 3748) and the
   candidate-proposal call (`binding.candidate_proposal_for_context(ctx)`, 3820). `ctx` carries A's sealed Perception
   state, so every branch contact was handed A's note.
3. The candidate supply was never re-resolved. The docstring of `perception_branch_solver_messages` claimed "the Solver's
   own candidate construction is a pure function of the `phase:<perception>` state this view replaces, so it re-resolves
   on its own". That is false: the supply is resolved once per row, in `settle` (3284,
   `binding.supply_for_phase(next_phase, staged)`), against A's staged context, and lands in
   `ctx.query_state.retrieved_value_ids`, which every branch contact reads. Level 2 had no per-branch supply resolver at
   all (the supply-variant arm route has `supply_variant_for_phase`; level 2 had no counterpart).
4. The only level-2 live proof (`tests/unit/test_perception_branch_live.py::test_at_p7_level2_solver_fanout_...`) states
   that it does not assert B's rendered content, and its history helper scanned text parts that the history never
   carries, so a B column equal to A's passed.

### Confirmation on the sealed bytes (read-only; counts only)

Per row, `native_episode_receipt.perception_branches.branches[*]` of each sealed `outputs.jsonl` (1,080 level-2 rows per
cell), treatment branch vs A:

| cell, branch | note differs from A | candidate-intent list differs | rendered `candidate_supply_value_ids` equal to A | ... of which on rows whose list differs |
| --- | ---: | ---: | ---: | ---: |
| P-SV-4 `b-k6p` | 1,009 | 713 | **1,080 / 1,080** | 713 / 713 |
| P-SV-4 `t-twin` | 679 | 231 | 1,080 / 1,080 | 231 / 231 |
| P-SV-1 `b-top2contrast` (seal-only attempt) | 1,041 | 674 | 1,080 / 1,080 | 674 / 674 |
| P-SV-1 `b-top2contrast` (first attempt) | 1,041 | 686 | 1,080 / 1,080 | 686 / 686 |
| P-SV-2 `b-list3` | 920 | 465 | 1,080 / 1,080 | 465 / 465 |
| P-SV-3 `b-depth` | 973 | 455 | 1,080 / 1,080 | 455 / 455 |

The first-visit Solver `prompt_tokens` equal to A's on 1,080 / 1,080 rows in P-SV-4 for both branches (the P-SV-4 read
note, section 3a). P-SV-1's level-2 primary (intent -0.19 pp [-0.56, +0.19]) is numerically the same as P-SV-4's: two
cells whose branch notes differ but whose Solver requests are both A's request draw the same A/A noise.

## 3. What stands and what is struck

Stands (level 1, the registered presence gates; the branch Perception contact did render its own supply and key, proven
by the level-1 receipts and the live tests):

- P-SV-1: level-1 `top1` -1.67 pp [-2.96, -0.37] and `present` -1.85 pp [-2.96, -0.83] (the top2-contrast note lowers
  presence).
- P-SV-2: gold-on-list +0.37 pp [-0.37, +1.20] against a twin present bar of 1.02 pp.
- P-SV-3: gold-on-list -1.39 pp [-2.31, -0.56] (depth 8 to 12 lowers presence).
- P-SV-4: the level-1 K6p reading (block-rank lift +15 rows at block rank 1; note `top1` -0.09 pp) and the NOT NOMINATED
  closure of K6p, which the P-SV-4 note already rests on level 1.

Struck (every level-2 side reading, because the branch Solver column was A's request):

- P-SV-1: the level-2 primary (intent -0.19 pp [-0.56, +0.19] against a twin bar of 0.42 pp), and the level-2 SLU-F1.
- P-SV-2: the level-2 intent 0.00 and the observed `min_candidates = 3` SLU-F1 +0.81 pp [+0.11, +1.66]. That knob has
  NOT been shown to help; it was an A/A replicate.
- P-SV-3: the level-2 intent 0.00 and SLU-F1 +0.01 pp [-0.42, +0.44], and "the Solver still answers absent gold on 9 of
  105 rows".
- P-SV-4: the level-2 primary (intent -0.19 pp [-0.56, +0.19] against a twin bar of 0.23 pp; the NOT NOMINATED word is
  mechanically correct and uninformative) and the twin null derived from the level-2 columns.

The level-2 columns of P-SV-1 to P-SV-4 must not be cited as evidence about any branch mechanism. No level-2
Perception-branch cell has measured a branch Solver conversion; the first valid one is a future cell flown from a commit
that contains this fix.

## 4. The fix

Branch `fable/psv-level2-render-fix` (not merged; merging and the repin of any queued level-2 cell are the coordinator's):

- `rails/runner.py`: one function, `_perception_branch_solver_view(ctx, request)`, defines the context a non-A,
  non-twin branch Solver contact renders from: the sealed Perception state's content is the branch's own note, and
  `retrieved_value_ids` carry the branch's own Solver-phase supply. A and the twin get `ctx` back unchanged, so their
  request is the unbranched construction by construction (I7). The messages, the exposed history, the role-context
  compiler and the node-context compiler all read this view; the row's custody context (`state.current_context`, the
  sealed states, `final_query_state`) is untouched, so only the rendering moves.
- `settle` resolves each non-A, non-twin branch's Solver-phase supply at the first Solver visit, against the same staged
  context the row's ordinary supply step uses except that the sealed Perception state carries that branch's note, through
  a new flight-owned resolver (`binding.perception_branch_solver_supply`). The branch's value ids replace A's node
  contribution through `arm_supplied_value_ids`, exactly as a supply-variant arm's do.
- `core/flight/runtime.py`: `_perception_branch_solver_supply_binding` builds one independent knowledge-store router per
  non-A, non-twin branch over the same released, pinned stores, with no knob override (a shared router would refuse the
  second note's selection as "changed within one query").
- Pre-contact refusals: a level-2 group beside a Solver supply with no resolver, a resolver with no level-2 group, and a
  candidate proposal beside level 2 (a branch's proposal would have to be re-derived from its note; not built).
- Fail-closed seal guard (`rails/runner.py`, final receipt assembly): every Solver contact of a level-2 episode records a
  contact-id-free digest of its composed messages plus exposed history. At seal, a non-twin branch whose own Perception
  note differs from A's and whose digest equals A's is refused by name ("replicated branch A's rendered request although
  its own Perception note differs from A's (the 2026-10-09 level-2 render defect ...)"), and a twin whose digest differs
  from A's is refused. A branch that sees a different note but whose role-context compiler reduces it to A's rendering
  would also be refused; that is deliberate, since such a column carries no branch information.
- Not changed: the delivering column, level 1, supply-variant arms and template arms. The `config` hash is unchanged
  (no new config key), but the implementation identity changed, so any queued level-2 cell's prepared artifacts that bind
  runner or runtime implementation hashes must be re-pinned from the merged commit.

## 5. The test

`tests/unit/test_perception_branch_level2_render.py` (model-free; the `_ActualEpisodeHarness` fake transport through the
production graph, two rows because the shared fake world holds two; Perception notes and the Solver-phase supply are
pure functions of each other, B's note differs from A's, T's equals A's):

1. B's Solver request carries B's note and the supply that note implies, and no trace of A's note; A's carries A's; T's
   equals A's on every AT2 field and on the sealed-state history; the receipt records B, T, A candidate supply
   `[Y], [X], [X]`; custody (final query state, sealed Perception state) stays A's.
2. The delivering column equals the unbranched plan request (supplied evidence, decoding, sealed-state history) from a
   control run with no branch group.
3. The seal guard: with the defect reproduced (history read from A's note, supply resolved from A's note) the row is
   refused with the guard's message.

Run against the pre-fix `runner.py`, test 1 fails (B's Solver history carries A's note), so the test would have caught the
defect. Existing supply-variant, template-variant, perception-branch, native-episode and stage-3 supply tests are
unchanged and pass (804 tests selected by name, 0 failures).
