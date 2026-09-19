# SLURP context efficiency: consolidated Pareto proposal v1 (owner decision 50)

Author: Fable 5.1 (coordinator). Date: 2026-09-19. Development numbers only (decision 28): every score
is official SLURP `evaluate.py` on TRAIN Fold A (1,080 rows, 125 speakers) or on its sealed comparator;
nothing here is a test claim. This document registers nothing, arms nothing and makes no contact; it
consolidates five sealed analyses into one ranked proposal and names the decisions it needs.

## 0. What this document consolidates, and what it decides

Owner decision 50 (2026-09-19): *what* a node reads is a design decision of the agent system and is
never changed to save tokens; *how* it reads is optimised under model efficiency, official
effectiveness at own-null margins, and inference cost; every rendering form is one one-factor cell on
the effect-cost Pareto front, admitted only NEUTRAL-or-better; no mechanical efficiency; the analyses
are consolidated before the next efficiency cell is registered. Inputs, all sealed on master:

| analysis | owner decision | document |
| --- | --- | --- |
| throughput root cause | 41 | `docs/results/2026-09-19-slurp-throughput-root-cause-v1.md` |
| serving geometry and graceful degradation | 45 | `docs/results/2026-09-19-slurp-serving-geometry-and-degradation-v1.md` |
| M1 exemplar compression, the neighbour vote, staged use | 46, 47, 49 | `docs/results/2026-09-19-slurp-m1-exemplar-compression-analysis-v1.md` (sections 13-16 reconcile it with the index design) |
| knowledge index and index-based context assembly | 48 | `docs/superpowers/specs/2026-09-19-knowledge-index-and-context-assembly-design.md` |
| efficiency cell EFF-1 (E17 constant tool rendering), read HARMFUL | 41 | `docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md` |

It decides four things: the per-node *reads* invariant (section 1), the measured front (section 2),
the ranked candidate forms with the control each needs (section 3), the consolidated answers to the
index design's thirteen questions (section 4), and the registration order (section 5). Section 7
lists the owner decisions it needs.

## 1. The invariant: what each node reads (design), and what may be optimised (rendering)

Node names are the base lock's (`agent-base-lock-v2-draft`, six mandatory nodes, decision 43). The
*reads* column is the index design's per-node assembly table (section 4.2) and is proposed here as
the **design column of base lock v3**; under decision 50 it changes only by owner decision. The
*rendering knobs* column is what efficiency cells are allowed to move.

| node | reads (design; fixed) | rendering knobs (optimisable, one per cell) | change proposed to today's reads (owner decision) |
| --- | --- | --- | --- |
| N1 Perception | the speech packet; the closed legal inventory (L0 intents grouped by scenario, L0 slots) | rendering of the inventory (grouping, id grammar) | none |
| N2 Solver | the speech packet; the Perception candidates; the contracts of the candidate intents and of their bound slot types; the speech-keyed exemplar neighbourhood (k = 20) | L1 line choice; expansion budgets `r` (exemplars) and `e` (slot cards); pointer grammar; ordering; store alias; hoisting of constant card sections | none: the Solver still reads every object it reads today, as index lines plus budgeted expansions |
| N3 Reviewer | the draft; the task contract (already verbatim in its system message); the contracts of the ids the draft cited; the slot-audit block (E12) | the same knobs as the Solver, on the cited ids | **two WHAT changes**: cited-only (today: the whole retrieved set), and **withdrawal of the task-contract tool**, whose observation is `context.task_contract`, the contract its system message already holds (section 3, form 0-B) |
| N4 Planner | the states (draft, findings, remaining budget); the id space (L0) | none beyond L0 rendering | **L0-only** (today: the whole episode, 25.0 % of the run's prompt budget and 34.8 % of its prefill, for a median 2-token verdict) |
| N5 Acquisition | speech + the drafted id + state filters (E18 kind a); tool actions (kind c) | item cap of the kind | none (built, unflown); under form 0-B it becomes the only node with tool actions, which is what decision 44 built it for |
| N6 Delivery | the delivered text; L0 | none | none |

The WHAT rows are design changes, not renderings, and are therefore not registered here as efficiency
cells: they are base-lock v3 decisions (section 7, D-A and D-E), each then flown as its own one-factor
cell with a NEUTRAL bar.

## 2. The measured effect-cost front today (TRAIN Fold A, official scorer)

| arm | official SLU / intent | with the normaliser node | contacts / row | GPU-h / 1,080 | prefilled tok / row | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| dual-store anchor (base) | 48.53 / 77.96 | -- | 5.016 | 3.388 | not joined (no flight receipts) | comparator |
| B4b slot store v2 | +1.54 (replicated) | -- | 5.01 | 3.465 | 26,197 | ADMITTED |
| B1 exemplars k = 20 | 61.14 / 80.19 | 62.67 / 81.76 | 5.02 | 3.680 | 25,933 | ADMITTED (B1r flying) |
| B5e = B1 + B4b | 62.34 / 80.09 | 63.78 / 81.85 | 5.01 | 3.871 | not joined | NEUTRAL vs B1; bar missed by 1.66 SLU |
| B7a v2 NCP L1 | 48.22 / 77.31 | -- | 5.20 | 3.781 (+11.6 %) | -- | HARMFUL |
| B4a v2 fallback candidate | 47.83 / 78.70 | -- | 5.01 | 4.721 (+39 %) | -- | HARMFUL |
| **EFF-1 = anchor + E17 constant tools** | **44.14 / 68.80** | -- | 4.90 | **1.843** | **10,127** (-61.3 %) | **HARMFUL** (delivery shape; zero delta on the 938 rows both arms parsed) |

Reading of the front. The effect frontier is B5e with the node (63.78 / 81.85) at 3.87 GPU-h. The
cost frontier is EFF-1 at 1.84 GPU-h, and EFF-1 proves the prefix-cache diagnosis (cached share
42.9 % -> 75.2 %, first-Reviewer prefill -96.9 %, Planner -80.8 %, 45.94 contacts per minute against
26.06) while failing on one component: rendering the Reviewer's tools array into the Solver's system
message made 145 of 1,092 Solver completions tool-call-shaped strings, delivered verbatim on 137 rows
that score zero. **The two frontiers have never been measured on one row**: the post-constant-prefix
cost of a row that also carries the exemplar block and slot store v2 is derived, not measured.

**Why the repair precedes the index cell.** Under per-role rendering the tools toggle re-decodes the
whole KV prefix at contacts 3 and 5 of every row. A 3,526-token index in the system message would then
be prefilled about twice per row (about 7,000 tokens) against the 4,784 + 645 the pointer discipline
saves: **the index cell is an efficiency loss without a constant prefix**, and the index design's loader
refusal 7 (the key refuses without constant rendering) already encodes that dependency.

## 3. Candidate forms, ranked on the front

Ranking key: prefill saved per row after a constant prefix (the EFF-1 row is 10,127 prefilled tokens),
the measured risk to the official number, and the control the form needs. "WHAT" marks a form that
changes what a node reads or may do and is therefore a design decision (section 1), not an efficiency
cell.

| rank | form | what it changes | prefill / contacts saved per row | expected effect | control / bar | proposal |
| ---: | --- | --- | ---: | --- | --- | --- |
| **0-B** | **withdraw the Reviewer's task-contract tool** (`phase_tools.reviewer` empty; no role renders a tools array; the prefix is constant by construction) | **WHAT**: the Reviewer loses an action whose observation is byte-for-byte the contract already in its system message; it reads nothing less | the whole EFF-1 saving (about 16,000 prefilled tokens) **plus** the tool round trip: 5 -> 4 contacts per row and L4's 895 tokens (the observation replay) | NEUTRAL expected: no role ever sees a tool schema, so the EFF-1 failure class cannot occur (the anchor's Solver, per-role, produced 0 of 1,085 tool-call strings) | one cell on the B1 base against the sealed B1 bytes at B1r's margins; NEUTRAL-or-better; the class is `toolkits` | **recommended repair** (owner D-E) |
| **0-A** | keep `tool_schema_rendering = "constant"` and add a per-role decode-time ban of the `<tool_call>` token on the tool-free roles (`decoding_params.logit_bias`, which the transport already passes through), plus a receipt counter of tool-call-shaped completions per role | HOW: prompt bytes identical to EFF-1; the Reviewer unchanged | the EFF-1 saving (GPU-h -45.6 %) | NEUTRAL expected on the 938-row evidence; the risk is a second surface form the ban does not cover, which the counter would show | one cell on the B1 base at B1r's margins; NEUTRAL-or-better; the token id read from the GGUF vocabulary with a receipt, no tokenizer contact | fallback if the owner keeps the Reviewer's tool |
| **1** | **index prefix + pointer block on the slot-contract cards, with three free riders** (hoist the two constant card sections 540 tok; most-relevant-first exemplar order 0 tok; store alias 105 tok) | HOW: the Solver's rendering of the same objects (constant L0 + L1 index cached once per slot at 13.1 tok/row, per-row pointers, budgeted L2 expansions) | ~4,784 + 645 (about 55 % of the post-repair row); 13,078-row read 13.4-21.5 h (co-bound range) | NEUTRAL expected; the risk is the index's own compression (90.6 % of card characters serve slot types no answer used) | **derangement twin required** (Q5; A2T ORG-1: form alone cost -3.23 pp); margins = B1's own null from B1r | **register after the repair** |
| 2 | Planner reads L0 only | WHAT | the remainder of the Planner's per-row replay (its prefill is already -80.8 % under a constant prefix) | unknown; the Planner emits 2 tokens | own-null NEUTRAL bar | base-lock v3 decision D-A, then its own cell |
| 3 | Reviewer reads the cited ids only | WHAT | small under a constant prefix (its evidence block is cached) | unknown | own-null NEUTRAL bar | base-lock v3 decision D-A, then its own cell |
| 4 | GPU power limit 100 W -> 175 W (host setting) | nothing in the repository; byte-neutral | none; machine rate +15-40 % modelled | none on outputs | Probe G0 receipt | owner checks Lenovo Vantage / Legion Space; no cell |
| 5 | `-ub 512 -> 1024` at np4 | serving flag, new session id | none; rate unknown | none on outputs | Probe G1 (~30 min) in a GPU gap | probe, no cell |
| 6 | np6 x 16,384 at q8_0 | serving geometry | none; +7.5 % modelled once the row is decode-bound | none on outputs; refused today by 188 tokens | Probe G2 after E20 (landed), after form 1 reads, after the test tail is bounded | held |
| 7 | exemplar rank top-12 + compact rendering (`M1-K12-1`) | the exemplar block's size | ~352 | -1.5 pp intent coverage / -4.2 pp filler recall (offline) | NEUTRAL bar | **not now**: dominated by rank 1, real coverage cost |
| 8 | neighbour vote (m = 5) + 2-3 few-shot lines (decision 49 form) | the exemplar block's content | ~599 | **-24 pp filler recall offline, predicted -5 to -6 pp SLU**; M1 works by raw-line convention transfer (86.4 % of new-correct fillers verbatim in the block) | an effectiveness hypothesis, not an efficiency one | **not as an efficiency cell** |
| 9 | Reviewer x2 -> x1 | iteration count | under form 0-B the second Reviewer contact is the tool round trip and disappears anyway | -- | -- | subsumed by 0-B |
| 10 | drop the Planner contact (L2) | node removal | ~1.8 h on the test read | changes the system | -- | refused by decision 43 (six mandatory nodes) |
| 11 | cap the card expansion without an index | the Solver's card set | 1,176-2,829 | -11.8 to -38.0 pp delivered-type cover | -- | dominated by rank 1 |
| -- | `context_fit_policy = "compact-or-abstain"` (E20, merged 7d696378) | a per-request disposition; fires on no TRAIN A row | 0 | none by construction on TRAIN A | harness declaration with a receipt | armed on every new cell as a declaration; prerequisite of form 6 and of the test read |

Why form 0-B is a design consolidation and not a token-saving hack: the tool's wrapper returns
`context.task_contract`, the object every role's instruction template already renders verbatim, so
the Reviewer reads exactly what it read before; the six-node design gives tool actions to N5
Acquisition (decision 44); and the withdrawal removes the one mechanism (a tools array on some roles
and not others) that both breaks the prefix cache and, when made constant, corrupts the Solver's
delivery shape. Its cost is that every later cell flies on a base that differs from the sealed
comparators in the Reviewer's toolkit, which is why it must be one NEUTRAL cell of its own before
anything is stacked on it.

Why rank 1 is not "mechanical" under decision 50: the Solver keeps every object it reads today; the
cell changes the granularity at which each object is rendered (index line versus full card) and adds
the pointer discipline the model can act on; its twin separates content from shape; it is read on the
official number at the comparator's own margins; and it is the only form that also unlocks the
geometry (np6 becomes admissible with about 1,516 tokens to spare).

## 4. Consolidated answers to the index design's thirteen questions

| q | recommendation | why |
| --- | --- | --- |
| Q1 | **one key** `native_episode.knowledge_index` arming prefix + pointers + budgets | an index-only arm is refused by the live-slot fit gate (18,987 vs 16,384); a pointer-only arm has no referent |
| Q2 | the pure-suffix instruction fill is **not** a contract change; the template file is untouched and the repository's own docstring names this form as what keeps a paired contrast legitimate | record the owner's ruling either way; if "contract change", the cell gets its own fill id and a `contract`-class switch |
| Q3 | intent L1 = `Activation boundary`; `Confusable exclusions` folded into edge entries | the distinction belongs to the pair |
| Q4 | slot L1 = `Admissible formats` | the delivery normaliser and the E12 `REPRESENTATION` flag key on it |
| Q5 | **twin required on the first cell** | A2T ORG-1: form alone cost -3.23 pp; the twin is ~1.15 GPU-h at the projected rate |
| Q6 | factoring **inside the index renderer**; `intent-boundaries-factored-v1` stays unused | one factor per cell; a store re-pin is a second factor |
| Q7 | citation **permitted, not required**; the citation rate is a structural read | a required citation changes the answer surface (a second factor) |
| Q8 | **`expansion_budget.slot_card = 4`** on the first cell (the cards of the slot types bound to the top candidate); `0` as a later one-factor point | protects the one admitted slot mechanism (B4b's revised date/time cards); the difference is 2.4 h on the test read |
| Q9 | order in section 5; the repair cell (0-B or 0-A) precedes the index cell; B8c is **not** registered before the index cell reads; B8b-anchor flies because it is ready and its object is E12's per-row audit, which the index re-bases later | the index is an efficiency loss without a constant prefix; B8b/B8c blocks are the objects the index renders once in the prefix |
| Q10 | **hold** every other carrier until the SLURP cell reads | Earnings and Audio2Tool are held by the owner anyway |
| Q11 | **yes**: already legal content, newly rendered, is a new exposure; own pre-registration row, one-shot semantics | the ledger records contact surfaces, not byte legality |
| Q12 | Planner L0-only is a **separate cell after a base-lock v3 decision** (section 1) | a WHAT change under decision 50 |
| Q13 | the geometry flip is **Probe G2**, separate, gated on E20 (landed) + the index cell's read + the test-tail bound | not part of the cell's claim |

Under form 0-B the index design's loader refusal 7 must accept "no role holds tool authority" as a
constant prefix, beside `tool_schema_rendering = "constant"`; that is a one-line change to item E21
(knowledge index) once the owner decides D-E.

## 5. Registration order and prerequisites

1. **B1r** (flying, `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1`): supplies B1's own-null
   margins (decision 38), the only legitimate margin for a B1-based comparator.
2. **B8b-anchor** (ready at c905ddf0; four-row smoke queued in the GPU gap after B1r, then the arm).
3. **The repair cell** on the B1 base (+ M4b, + M3) against the sealed B1 bytes at B1r's margins:
   0-B (withdraw the Reviewer's tool) on owner decision D-E, else 0-A. NEUTRAL-or-better; its sealed
   bytes become the base of every later SLURP cell. About 1.5-1.8 GPU-h.
4. **Item E21 engineering** (in progress on `fable/e21`, branched from the E20 merge): the index
   renderer, the assembly, the one key with every Q3/Q4/Q7/Q8 choice as a config value, the loader
   refusals, the model-free render proof, tests. No contact.
5. **Render proof** (index design 7.0) on 20 sealed B1 rows; a proof that fails any of its three
   properties stops the cell.
6. **Index cell** on the repair arm against its sealed bytes, then its **derangement twin**: two
   readiness packages (one cell per package), each with its own exposure row, ExecutionPlan,
   four-row smoke and prompt-fit receipt.
7. Then, per decision 50, the next efficiency cell is registered only after this one reads and the
   analyses are re-consolidated; B9a (staged acquisition, index design 7.3) is its natural successor.

## 6. What is not claimed

No test-split number. No claim that either repair is NEUTRAL before it is flown (0-B's expectation
rests on the anchor's zero tool-call strings under per-role rendering and on the wrapper's source; 0-A's
on the 938-row diagnostic). No claim that the index preserves what the full cards carry. No measured
cost for the B5e-shaped row under a constant prefix. No measured gain from the power cap. No
cross-carrier claim. No claim that any efficiency cell moves the dev bar (64 / 78): B5e with the node
reads 63.78 / 81.85 and an efficiency-NEUTRAL cell moves neither number.

## 7. Decisions requested from the owner

- **D-A.** Adopt section 1's *reads* column as the design column of base lock v3, including the
  Planner L0-only and Reviewer cited-only reads, each then flown as its own one-factor cell -- or keep
  today's reads and let the index change rendering only.
- **D-B.** The thirteen answers of section 4 as recommended, or name the deviations.
- **D-C.** Register the index cell and its twin as the next efficiency cell after the repair cell.
- **D-D.** Check the host GPU power limit in Lenovo Vantage / Legion Space (100 W enforced of 175 W);
  Probe G0 flies in the next GPU gap once the setting is known.
- **D-E.** The repair: withdraw the Reviewer's task-contract tool (0-B, recommended: the observation
  is the contract the Reviewer already holds; tool actions belong to N5 Acquisition) or keep the tool
  and ban the `<tool_call>` token on the tool-free roles at decode time (0-A).
