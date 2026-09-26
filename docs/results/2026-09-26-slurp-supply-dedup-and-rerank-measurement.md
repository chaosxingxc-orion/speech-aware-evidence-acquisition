# SLURP supply: dedup and re-rank measurement (2026-09-26)

Owner question (2026-09-26): the recall stage returns several results; a context-engineering stage
should deduplicate and re-rank them before the next node, and what crosses the boundary should be
the deduplicated VALUE, not the matched KEY, because several different keys can hit the same value.
This note measures whether that duplication exists on the flown path and what a dedup-then-rerank
stage would free. Measurement only: no mechanism is designed, no cell is registered, nothing is
flown.

**Method.** Model-free and local. Reproducer:
`scripts/analysis/slurp_supply_dedup_measurement.py`, byte-identical across two consecutive runs
(report sha256 `cad374aeffdcba3c7fb1556cbd9b8a023b3c34876e7fe10a04be9af70e6fe855`; the report
carries no timestamp, so the two passes match exactly). Sources, all read-only: seven sealed run
traces and their `flight-receipts.json` under `$SPEECHRL_DATA_DIR/runs/`, the three released store
snapshots, and the arms' `configs/baseline/` fragments. Tokens come from the local
`llama-tokenize` binary at `/home/chao/llama.cpp/build/bin/llama-tokenize` loading the pinned
`models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf` vocab in a
local process (302 invocations, 4 workers) — no server, no port, no GPU, no encoder, no scorer,
zero model contacts. Tools: `llama-tokenize`, `git`, `python` reads of sealed JSON, all local.
Scope: 7 arms, 4,375 fusion decisions, 4,604 slot-route selection audits, 20,850 node contacts,
697,170 supplied items.

## 1. Which path ranks, which path cuts, which path dedups

There are **two different kinds of key** in this system, and they behave oppositely.

**Route A — retrieval keys (facets), for `intent-boundaries` at Perception and `train-exemplars` at
the Solver.** `KbFacetProvider.candidates` ranks FACETS, never values
(`rails/knowledge_provider.py:600`, ranker resolved at `:564`, truncation to `k` at `:648`); `k`
reaches recall as `top_k_per_dimension` (`rails/phase_supply.py:1215`, policy default at `:13`,
registry resolution at `:509`). Then `rails/kb_policy.py:713`
`top_m_ids = tuple(candidate.facet_id for candidate in rank_result.candidates[: knobs.m])` —
admitted facets at `:723`, already-visible values excluded at `:725`, and only at `:768`
`selected_value_ids=tuple(sorted(set(selected_value_ids)))`. The associated-values fuser is the same
order: `seen = set(visible)` at `:834`, key cut at `:835`. **The coordinator's reading is confirmed
for route A: the budget cut falls on keys before any value-level dedup**, so the chain is coarse
retrieval → cut on keys → dedup on values → supply.

**Route B — intent-candidate keys, for `slot-contracts` at the Solver.**
`select_candidate_semantic_values` (`rails/knowledge_provider.py:1341`) walks the candidates
round-robin, and when a candidate's next value is already selected it records
`{"reason": "shared-value-already-selected"}` and **`continue`s to that candidate's next value
without consuming a budget slot** (`:1368-1372`). Here the order is already coarse retrieval →
dedup → cut, exactly what the owner prescribes.

**Composite merge.** Both Solver routes merge through `rails/knowledge_stores.py`:
`_composite_context_rank` re-sorts all keys by `(-score, facet_id)` (`:1792`, sort key at `:1808`),
and `_composite_context_fuse` deduplicates the KEY list with `dict.fromkeys(...)` (`:1825`) while
concatenating the VALUE lists with no dedup at all (`:1837`) — the inversion again, harmless only
because the two stores use disjoint id namespaces.

**What crosses the boundary is already the value.** `_render_kb_supply_packet`
(`rails/knowledge_provider.py:502`) renders `query_state.retrieved_value_ids` as
`[value <value_id>] <body>` with `item_id=knowledge:<value_id>` and `evidence_id=value_id`
(`:515`, `:517`); `expose_facets` is `false` in every flown store and the sealed
`supply_final_visible_facet_ids` is length 0 in all 4,375 episodes. A value can never appear twice
by id: `QueryState.validate` calls `_require_unique_texts(self.retrieved_value_ids, ...)`
(`rails/knowledge.py:658-659`), the acquire union is a set union (`rails/kb_policy.py:1267`), and
`restrict_repeat_visit_supply` (`rails/controllers.py:1276`) withholds already-visible values on a
re-entered phase.

## 2. Per-node comparison — the four nodes are not alike

`SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1`, the k=20 lock geometry, 625 episodes, verified against the
sealed `use_waves` and `flight-receipts.json`, not only the config.

| | Perception | Solver | Reviewer | Planner |
|---|---|---|---|---|
| store supplying it | `intent-boundaries` | `train-exemplars` + `slot-contracts` | none | none |
| query signal | `query-vectors-speech-segments.jsonl` | `query-vectors-speech-content-v1.jsonl` (exemplars); Perception's own sealed state (slots) | — | — |
| key kind | retrieval facet | retrieval facet (exemplars); intent candidate (slots) | — | — |
| rank policy | `saea-rank-wcos-prior-agree-v1` | same (exemplars); `saea-ranked-candidate-round-robin-v1` (slots) | — | — |
| rank weights | `w_cos 1.0 / w_prior 0.0 / w_agree 0.0` | identical, both non-cosine weights zeroed | — | — |
| fuser | `saea-fuse-associated-values-v1` | `saea-fuse-supplyfilter-v1` (exemplars); `saea-candidate-semantic-passthrough-v1` (slots) | — | — |
| where the cut falls | on keys: `m 8 / c 1 / top_l 8` | on keys: `m 20 / c 20 / top_l 20` (exemplars); after dedup: `max_total_values 28 / per-candidate 16 / candidates 3` (slots) | — | — |
| dedup fires? | by `value_id`; 0 firings | exemplars 0 firings; **slots 3,906 firings in 657 audits** | n/a | n/a |
| contacts | 625 | 657 | 657 | 651 |
| items supplied (mean / min / max) | 7.97 / 1 / 8 | 40.14 / 24 / 51 | 40.14 / 24 / 51 | 40.14 / 24 / 51 |
| items by store | 4,982 intent-boundaries | 5,235 + 7,998 + 13,140 | identical to Solver | 5,187 + 7,925 + 13,020 |
| supply-block tokens (mean, 25 sampled episodes) | 1,091.4 | 7,240.2 | 7,240.2 | 7,195.3 |
| prompt tokens (mean, sealed COST) | 3,615.5 | 9,967.6 | 9,945.2 | 10,082.0 |

**Two of the four nodes retrieve nothing.** The Reviewer and the Planner have no store entry, no
query, no ranker and no fuser — and they still receive the Solver's complete 40-item block, because
every later request renders from the accumulated `QueryState` (`rails/runner.py:1295`; the
docstring at `rails/controllers.py:1288` says so outright). The acquisition settles once per
episode, at the Perception wave, delivering to the Solver: `settling_roles` is `perception: 625`
and 625/625 episodes carry exactly 1 acquire transition.

## 3. The duplicate rate, per role and per k

Duplicate `value_id` in a supplied block: **0 of 20,850 contacts** in all seven arms — machine
enforced, not luck.

Duplicate BODY under a distinct `value_id`, in the block as delivered:

| level | measured |
|---|---|
| contacts carrying a repeated body | 19 of 20,850 (0.091 %) |
| items that are a repeated body | 19 of 697,170 (0.0027 %) |
| ranked retrieval keys resolving to a body an earlier key delivered | 6 of ~152,000 |
| ranked retrieval keys resolving to a VALUE an earlier key delivered | **0** |

Normalised bodies (whitespace collapsed, case folded) add nothing: the same 19 items.

**The slot route is where the duplication actually is**, and it is already absorbed. Over all seven
arms, the sealed selection audits record **83,821 mapped key-slots collapsing to 56,014 supplied
values, a ratio of 1.4964, with 27,807 `shared-value-already-selected` drops = 33.2 % of mapped
slots**. Per arm the ratio is 1.474 to 1.565. In PLAN, 11,904 mapped slots → 7,998 values, 3,906
drops; 12.17 slot values per row as flown against 17.75 with the dedup condition removed.

Per k on the exemplar axis (per acquisition, 625 each):

| k | ranked exemplar keys | keys surviving the cut | exemplar values delivered | Solver items | distinct bodies | Solver block tokens |
|---|---|---|---|---|---|---|
| 10 | 10.00 | 10.00 | 10.00 | 30.13 | 30.13 | 6,898.6 |
| 20 (PLANR) | 20.00 | 20.00 | 20.00 | 40.02 | 40.01 | 7,271.3 |
| 30 | 30.00 | 30.00 | 30.00 | 50.07 | 50.07 | 7,520.0 |
| 20, `c 4` (DIV) | 20.00 | 10.29 | 10.29 | 30.33 | 30.33 | 6,617.3 |

Raising `k` from 10 to 30 delivers exactly 10 → 30 distinct exemplar bodies; duplicate absorption is
0.0016 items per acquisition. **VAR1's +0.07 / +0.09 pp null is not a duplicate artefact — the extra
budget bought 20 genuinely new exemplar bodies per row and moved nothing.** The only arm where the
cut discards ranked keys is DIV, and there it is the per-target `c 4` coverage knob, not
duplication, that drops 9.71 of 20 keys.

## 4. Does re-ranking after dedup change the top of the list?

**No.** Collapsing repeated bodies changes the top-5 distinct-value SET in 0 of 4,375 acquisitions
and the top-10 SET in 0 of 4,375. With `w_prior` and `w_agree` both pinned to 0.0 in every flown
store the ranker is pure cosine, so removing a member cannot reorder the survivors — and at
19 duplicated items in 697,170 there is almost nothing to remove.

One measured observation about the top of the list that is *not* about dedup: the composite rank
sorts keys from both Solver routes by raw score, and the two routes score on different scales (the
candidate route emits ordinal scores `n, n-1, …`; the exemplar route emits cosines). In PLANR the
composite top-5 is 3,065 slot-contract keys against 60 exemplar keys (98.1 %) and the top-10 is
5,711 against 539 (91.4 %). Every arm is within one point of that.

## 5. Keys versus values — the fan-in direction, measured both ways

**Retrieval facet → value is a strict bijection** in all three released stores, so on route A there
is nothing to collapse:

| store | snapshot sha256 (prefix) | facets | values | keys per value | values per key | exact body duplicate groups |
|---|---|---|---|---|---|---|
| `train-exemplars` (`size-pool-annotated-exemplars-minus-r01`) | `6eaa03ae` | 8,554 | 8,554 | 1 for all 8,554 | 1 for all 8,554 | 5 groups, 10 values (0.117 %) |
| `intent-boundaries-v1` | `5520b844` | 60 | 60 | 1 for all 60 | 1 for all 60 | 0 |
| `slot-contracts-v2` | `d5992bd1` | 54 | 54 | 1 for all 54 | 1 for all 54 | 0 |

Keys after the cut equal values delivered in 4,375 of 4,375 fusion decisions — 0 collapses, 0
fan-outs. The ROLL-2 dry-run reading of "20 keys → 31 supplied values" is a composition artefact,
not fan-out: the 31 is the union across stores (8 inherited `intent-boundaries` + `slot-contracts` +
20 `train-exemplars`) while the 20 counted only exemplar keys. Per store the ratio is 1.000.

**Intent candidate → slot-contract value is heavy many-to-many**, which is exactly the owner's
model. Over PLAN's 657 audits: within one row, 4,947 of the row's distinct slot values were reached
by 1 candidate, 2,196 by 2 and 855 by 3 — **38.1 % of each row's slot values are hit by two or
three different keys**. Across the arm the index fan-in is far larger: of the 54 slot values ever
mapped, 14 are reached by exactly 1 intent candidate, and the tail runs 11, 15, 17, 19, 21, 23, 24,
27, 34 and **40 candidates for a single value**. The PER-K16C5 arm, which raises `max_candidates` to
5, pushes the within-row fan-in to 4 and 5 candidates per value (155 and 51 occurrences) and the
mapped/selected ratio to 1.565. So both directions the coordinator asked about coexist: bijection on
the retrieval-facet route, strong fan-in on the intent-candidate route.

## 6. The budget — what dedup already frees, and what is left to free

Measured on the tokenizer, 25 deterministically strided rows per arm.

**Route B dedup, already in force.** Rendering the slot block from the flown selection versus the
same round-robin with only the dedup condition removed: PLAN flown 5,381.8 tokens (median 5,617)
against 8,502.2 without dedup (median 7,929) — **the existing dedup already frees 3,120.4 tokens per
row (median 2,784, max 6,983)**, about 31 % of the Solver's 9,968-token prompt. Every arm agrees:
2,880 (k10), 2,973 (DIV), 3,059 (k30), 3,403 (PLANR), 3,412 (ROLL-1), 3,481 (PER-K16C5).

**What a further dedup stage would free.** Body-level dedup inside a delivered block frees exactly
26 tokens in each of the 19 contacts it touches: 78 tokens per arm for PLAN, PLANR, k30 and
PER-K16C5, 182 for ROLL-1, 0 for k10 and DIV — **494 tokens across all seven arms, 20,850 contacts
and 697,170 supplied items**. Against PLAN's 7,240-token Solver block that is 0.36 % of one block
and 0.26 % of one prompt, in 1 contact of 657.

**The duplication that is large is between nodes, not inside a block.** In PLAN one episode sends
134.18 supply items across its node contacts while needing only 40.18 distinct bodies — a ratio of
**3.34** (median 3.20, min 2.19, max 6.25, n=625). On the tokenizer, over 25 sampled episodes:
22,479 supply-block tokens sent, 7,240 of them new, **15,239 retransmitted = 67.8 %**. Every arm
agrees: 68.2 % (k30), 68.3 % (k10), 69.5 % (DIV), 70.0 % (PLANR), 70.4 % (PER-K16C5), 86.8 %
(ROLL-1, five samples per row).

## Verdict

A dedup-then-rerank context-engineering stage is **(a) already effectively present** on the flown
path, on both of its routes and for the reason the owner gives. The slot-contract route is the one
where several different keys really do hit the same value — 38.1 % of a row's slot values are
reached by two or three intent candidates, and one value is reachable from 40 of them — and its
round-robin already collapses 83,821 mapped key-slots to 56,014 supplied values across the seven
arms, dropping 27,807 of them as `shared-value-already-selected` (33.2 %) and skipping each
duplicate without spending a budget slot, so on that route the order is already coarse retrieval →
dedup → cut. The retrieval-facet route cuts on keys before dedup, exactly as the coordinator read
(`rails/kb_policy.py:713`, `:835`; and the composite merge dedups keys while concatenating values at
`rails/knowledge_stores.py:1825`/`:1837`), but that inversion costs nothing measurable because all
three released stores are strict 1-key-to-1-value bijections: 0 of ~152,000 ranked keys resolved to
a value an earlier key had already delivered. Quoted from the freed budget and the top-5 changes
rather than asserted, the ceiling of adding a further dedup stage is **494 freed tokens across
20,850 contacts and 697,170 supplied items — 26 tokens in each of 19 contacts, 0.26 % of one
affected prompt — with 0 of 4,375 top-5 set changes and 0 of 4,375 top-10 set changes**, against the
**3,120 tokens per row the dedup already in force frees**. So the hypothesis is right about the
mechanism and the mechanism is already built; the headroom left in it is three orders of magnitude
smaller than what it already delivers, and it is not the explanation for VAR1, whose k=10/20/30 arms
received exactly 10, 20 and 30 distinct exemplar bodies. The duplication still on the table is one
level up: 67.8 % of the supply-block tokens an episode sends are re-renders of bodies an earlier
node already received, and the Reviewer and the Planner each receive the full 40-item, ~7,240-token
block while retrieving nothing of their own.
