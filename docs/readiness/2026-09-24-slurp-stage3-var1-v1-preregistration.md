# VAR-1: the first construction-variant rollout of the locked v2.0 plan — preregistration

Status: **HELD**, registered before contact, model-free. Nothing was flown, flipped, scored or
minted: zero model, tokenizer, encoder, scorer, server, GPU and network contacts.

Family: `SAEA-SLURP-STAGE3-VAR1-*` — six 625-row cells on the SLURP-STAGE3-CONSTRUCTION-R01C
construction roster plus one four-row form smoke. Package:
`docs/readiness/2026-09-24-slurp-stage3-var1-v1/`. Protocol:
`docs/readiness/2026-09-24-slurp-stage3-var1-v1/protocol-registered-v1.json`.

Authority: the owner directive of 2026-09-24 — *training-free RL gains come from rolling out
VARIATIONS of prompts, data and content construction over an optimisation space, scored per
variant, with the winners encoded into demonstrations, constraints and selection rules; never from
running a simple algorithm mechanically and declaring a conclusion* — recorded in
`docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md` sections 5–7 as routes **F3**
(exemplar-construction variants) and **F4** (Perception coverage). Owner decisions 17, 25, 28, 29,
58, 75, 79, 86, 99, 101, 102, 107, 108, 111, 112, 113 and 114.

---

## 1. Why this family exists

The Stage-3 semantic-delta line is closed (owner decision 111). Its post-mortem, in section 5 of
the handoff, is that the rollouts varied **only Solver decoding under one fixed context**, so the
"advantage" learned from them ranked decoding noise and did not transfer out of fold (CELL-3:
−1.44 SLU on a fresh roster, twin +0.38, arm minus twin −1.82 — the store's *content* was the
harm). The directive that replaced it is to vary the **construction** instead: what is retrieved,
how much of it, how it is grouped, how many candidates the contract admits.

VAR-1 is that, in its smallest honest form. Every cell is the **locked v2.0 plan** with **one
existing config knob moved**. No new module, no new store, no new provider, no new policy id, no
new rails file, no code change. The family's product is a **table**: per-row paired deltas, a gold
per-scenario table, entity false positives and negatives by slot type, Perception coverage, and the
**group-relative advantage of each variant per runtime-observable state** — the quantity a
training-free RL policy would actually be learned from.

## 2. The cells

| cell | run id | change against the locked plan | rows |
| --- | --- | --- | ---: |
| **VAR1-PLAN** | `SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1` | none (the locked plan re-pointed at R01C) | 625 |
| **VAR1-PLANR** | `SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1` | request-identical replicate — the roster's own null | 625 |
| **VAR1-EX-K10** | `SAEA-SLURP-STAGE3-VAR1-EX-K10-R01C-V1` | exemplars `k` 20 → 10, `fuse_coverage` 10/10/10 | 625 |
| **VAR1-EX-K30** | `SAEA-SLURP-STAGE3-VAR1-EX-K30-R01C-V1` | exemplars `k` 20 → 30, `fuse_coverage` 30/30/30 | 625 |
| **VAR1-EX-DIV** | `SAEA-SLURP-STAGE3-VAR1-EX-DIV-R01C-V1` | exemplars `k` 20, `fuse_coverage.c` 20 → 4 | 625 |
| **VAR1-PER-K16C5** | `SAEA-SLURP-STAGE3-VAR1-PER-K16C5-R01C-V1` | Perception `k` 8 → 16, `fuse_coverage` 1/16/16, candidate bound 3 → 5 | 625 |
| smoke | `SAEA-SLURP-STAGE3-VAR1-SMOKE-4-V1` | the VAR1-PER-K16C5 form on the first four R01C rows | 4 |

Each carries a fit sibling `…-FIT-V1`. **FOURTEEN flight run ids** (seven cells × generation + fit);
two further ids are model-free-check READS and are never flown. The decision receipt
`coordination/slurp-stage3-var1-v1/root-admission-v1.json` (decision id
`slurp-stage3-var1-admission-v1`) lists the fourteen.

### 2a. What the knobs mean

`rails/kb_policy.py` is the authority, and the variants are named for what it actually does:

* **`saea-fuse-supplyfilter-v1`** (train-exemplars → Solver). `m` is the top-*m* ranked-facet window
  the cosine threshold is applied inside; the admitted values are grouped by their `task_target` —
  for this store an SLURP intent id, 59 distinct over 8,554 values — `top_l` bounds how many
  **targets** are served, and `c` bounds how many values **per served target**. Each exemplar value
  associates with exactly one content facet, so at `k = m = c = top_l = 20` the route is *twenty in,
  twenty out*. `k` 20 → 10 or 30 therefore moves the demonstration count directly; `c` 20 → 4 caps
  the supply at **four demonstrations per intent**, which shrinks the block on an
  intent-concentrated neighbourhood and leaves a diverse one untouched. That is why EX-DIV's supply
  size is **data-dependent** and its realised distribution is a registered deliverable, not an
  assumption.
* **`saea-fuse-associated-values-v1`** (intent-boundaries → Perception). The first *m* ranked facets
  are admitted, traversed in rank order taking at most `c` new values per facet, stopping at `top_l`
  values overall. The released store has 60 facets and 60 values, one card per intent, so `c = 1`
  with `m = top_l = k` gives exactly *k* intent cards. Its cards average **702 characters** (max
  895), so `k` 8 → 16 is the single largest text change in the family.

### 2b. The one required companion, declared and not hidden

`rails.candidate_semantic_supply` refuses a candidate bound above three under the literal-3
`bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1` projection. VAR1-PER-K16C5 therefore
also declares
`configurable-bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1`, a policy already
registered in `rails/slurp_intent_hypotheses.py`. The projection itself does **not** change — first
occurrence in the model's own order, distinct on `intent_id` — only its declared input bound moves
from a literal 3 to the configured `max_candidates` within the legal intent inventory. The bound is
moved at **both** sites that must agree (`phase_material.perception.fill_params.max_candidates` and
`knowledge_stores.slot-contracts.candidate_supply.solver.max_candidates`), because a Perception
contract that can emit five candidates and a Solver route that reads three is a config defect the
harness refuses at build time. `max_total_values` 28 and `max_values_per_candidate` 16 are **not**
moved: the same 28-value budget is spread round-robin over five candidates instead of three, so the
Solver's candidate block does not grow.

### 2c. The algorithm label

Every cell declares `stage3_algorithm.id = "shared-rollout"` with `operators_used = ["rollout",
"scoring"]` (`core.base.STAGE3_ALGORITHMS`, owner decision 101; gate
`scripts/checks/stage3_algorithm_label_check.py`). That is the honest label: VAR-1 runs the
algorithm-neutral rollout substrate once per construction variant, and the policy is learned
**offline**, by group-relative advantage over variants per runtime-observable state. No
credit-assignment, update, selection or context-application operator runs inside any cell.

## 3. The venue, and the two mandatory deviations

`SLURP-STAGE3-CONSTRUCTION-R01C` (`docs/receipts/rosters/slurp-stage3-construction-r01c.json`,
sha256 `e8abc65b…`): 625 TRAIN recordings, 18 scenario strata of 26–42, 625 distinct utterance ids,
67 headset / 558 far-field, 2,726.847188 s of audio, `roster_role: construction`, `split_role:
discovery`, split identity `f56bc386…`. Its receipt proves zero shared recordings and zero shared
utterances with TRAIN Fold A, TRAIN Fold B, DEV-1000 and DEV-2000-ADDED.

Two things follow, and neither is a variant:

1. **The re-pointing.** The two `query_source` pins, `preparation_source_receipts`, the packet
   promotion receipt and its sha256 are cell ROLL-1's, key for key. The R01C query-vector files are
   pure id SELECTIONS of the sealed R01 parents: every kept line is the parent's own line bytes.
2. **The MINUS-R01 exemplar store.** The parent `size-pool-annotated-exemplars` pool contains R01's
   own utterances, and a construction roster that retrieved itself would read its own answer. Every
   VAR-1 cell pins
   `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/` (coordinator
   decision 102), exactly as ROLL-1 does.

**R01C's roster receipt carries a per-item stratum.** That is the one thing this venue gives that
DEV-2000-ADDED withheld: a **gold per-scenario table is derivable offline**, from the receipt alone,
with no gold at runtime.

### 3a. Why VAR1-PLAN is flown and not imported

No plan-form arm has ever been sealed on R01C. Cell ROLL-1 flew
`phase-native-candidates-review-revise-samples5-v1` — the five-sample grouped-Solver policy with a
plurality-support commit — not the locked single-sample plan. The locked plan's sealed numbers are
TRAIN Fold A 63.63 / 82.22 and DEV-2000-ADDED 65.40 / 76.60, and neither is comparable to a 625-row
TRAIN construction subset. Greedy decoding is not bit-reproducible across batch compositions, so a
comparator from another roster would import a margin this family cannot measure. VAR1-PLAN is
therefore flown, once, and never re-flown.

## 4. Decision rule (fixed here)

**This family returns no admission verdict.** It is a construction-variant rollout on a
construction roster; its output is a table. No ADMITTED / NEUTRAL / HARMFUL label is attached to any
VAR-1 cell, no module is admitted, no store is released, nothing is locked, and the v2.0 lock is
untouched. The read driver writes status `DESCRIPTIVE` and the coordinator does not convert it.

For each variant *v*: `delta(v) = v − VAR1-PLAN` on the same 625 rows, paired by row, in percentage
points, for the official pooled SLU micro F1 (primary) and the intent (joint scenario+action)
accuracy (guard). Each delta is reported with CI90 and CI95 from a paired row-cluster bootstrap
(10,000 draws, seed 20260915, cluster key `utterance_id`), beside `h_SLU` and `h_intent` from the
own null. A variant is called **SEPARATED FROM THE NULL** when its CI95 excludes zero **and** its
point estimate lies outside ±h on that metric; anything else is **INSIDE THE NULL**. Those are
readings of a rollout, not admissions, and the words ADMITTED and HARMFUL are not used of a VAR-1
cell.

### 4a. The margins are NOT known at registration, and that is deliberate

`h_SLU` and `h_intent` are the CI95 half-widths **VAR1-PLAN against VAR1-PLANR** produces on **this**
roster, with the same estimator, clustering, seed and draws as every variant contrast. The order is
part of the registration: the own-null read `SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1` is completed and
its margin table **sealed before any variant contrast stage is read**, and the margins are never
adjusted after a variant's numbers are seen.

The TRAIN Fold A margins (`h_SLU` 1.2485 / `h_intent` 0.9943) and the DEV-2000-ADDED margins (1.2525
/ 1.1520) are recorded in `registered-facts-v1.json` as **context only** and are explicitly not this
family's bar. A margin is a property of a roster, never of a mechanism; R01C is a different roster of
a different size with a different scenario allocation, and at *n* = 625 the paired band is wider
than at *n* = 1,000.

### 4b. Primary deliverables, reported whatever the table says

1. the per-row **paired variant table** (four variants plus PLANR as the A/A control row);
2. the **margin table** from the own null, printed above it and dated before it;
3. the **gold per-scenario table** per variant, in both the natural-mixture and the equal-stratum
   weighting (owner decision 17);
4. **entity false positives and false negatives by slot TYPE** per variant, with the empty-gold-row
   emission rate;
5. **Perception coverage** per variant from the sealed Perception receipts — gold intent present in
   the row's own candidate list — with the candidate-count distribution;
6. the **group-relative advantage** of each variant per runtime-observable state (predicted majority
   candidate scenario, candidate count, channel, audio-duration band), with per-state *n*, never
   read as an effect below *n* = 20;
7. the **frontier row** per 625 rows (owner decision 75) and the cost table.

Deliverables 4–6 are why this family is worth flying at *n* = 625 at all: the cross-flight pooled
floor is about ±1.3 pp at *n* = 1,000 and wider here, and a dense per-class proxy is not subject to
that floor. Reading a coverage lever through a pooled score would be reading a 2 pp effect through a
1.3 pp instrument.

### 4c. Nothing selected here is a result

A variant that separates from the null on R01C is a **candidate**. The next step is a re-read of
that one variant on TRAIN Fold A against the sealed PLAN comparator at Fold A's own null, and then
on DEV-2000-ADDED at its own null. CELL-3 is the standing evidence for why: a store selected on Fold
A read −1.44 on a roster it had never touched. Selecting on construction rows and claiming on them
is the error this family is designed not to repeat.

## 5. Prompt fit

Not measured in tokens by this registration; no tokenizer was contacted.
`core.flight.cli check`'s `_assess_prompt_budget` is the measurement and it runs in the
coordinator's clean-tree cycle.

The rule (`rails/context_budget.py`): `required_window_tokens` = rendered text tokens + speech
tokens + the registered special-token reserve + the 512-token completion ceiling. **ALLOW** at or
below `slot − reserve` = 24,576 − 3,072 = **21,504**; **COMPACT_REQUIRED** at or below the slot
(24,576), which `core.flight.runtime` **records and proceeds on** under
`native_episode.context_fit_policy = compact-or-abstain` (harness item E20, owner decision 45);
**REFUSE** above the slot, which aborts.

What a store decides for a node does **not** travel in the rendered instruction — it reaches the
node as typed content blocks through the acquire transition, and every VAR-1 form's rendered
instruction is byte-for-byte the same length. So the quantity that actually moves is measured
directly in `dry-run-v1.md`: the **supplied content characters** per node per row, summed from the
released snapshots over the value ids the offline walk selected on the same four R01C rows. The
registered arithmetic and its conservative 2.5-characters-per-token conversion are in
`protocol-registered-v1.json` → `prompt_fit`; the conclusion is **COMPACT_REQUIRED at worst and
never REFUSE** on every phase of every cell.

**Fail-closed fallback, registered before contact.** If the coordinator's `check` reports `REFUSE`
(not `COMPACT_REQUIRED`) on VAR1-EX-K30's Solver, that cell **does not open**. It is re-registered
at `k = 26` with `fuse_coverage` 26/26/26, a **new** run id, a **new** generation attempt id and a
**new** `native_contact_fit.attempt_id`, and the `k = 30` identity is retired unused. The same rule
applies to VAR1-PER-K16C5 at `k = 12` with coverage 1/12/12. No other cell is touched, and no margin
or decision rule moves.

## 6. Budgets

Per 625-row cell: **6,875** generation calls (625 × 11, the locked plan's own per-row contact
ceiling from `configs/policy/phase-native-candidates-review-revise-v1.json` `max_contacts` 11,
resolved from the unchanged role graph perception 1 / solver 1 / reviewer 3 / planner 1 with
`max_revisions` 1 as 1 + 2 × (3 + 1 + 1)); **27,500** fit endpoint calls (6,875 × (1 speech packet +
3 endpoints)); **29,996** repeated speech audio seconds (2,726.847188 s × 11, rounded up); **8.0**
GPU hours; **0** native task-contract calls; **1** official complete scoring job.

Four-row smoke: **44** generation calls, **176** fit endpoint calls, **188** audio seconds, **1.0**
GPU hour, **0** scoring jobs.

Expected, never a target: about **4.1 contacts per row** (cell PLAN measured 4.0963 on TRAIN Fold A,
cell B6's plan arm 4.071 on DEV-2000-ADDED), so about **2,563** contacts and about **1.05** GPU
hours per cell, and roughly **6.5** GPU hours for the whole family. **No VAR-1 knob adds a contact**:
every one of them changes how much text an already-scheduled request carries. Ceilings are bounds,
never targets; unused budget is not attempt authority; a plan budget is run-cumulative per run id.

## 7. Boundary

* TRAIN Fold A, TRAIN Fold B, DEV-1000, DEV-2000-ADDED and the test split stay untouched and unread.
* No gold label, reference transcript, delivered answer or future turn enters runtime. Every knob is
  a retrieval budget or a candidate bound read from the row's own speech vector and its own sealed
  Perception state.
* R01C is the clean subset (175 knowledge-source recordings removed, coordinator decision 102) and
  the exemplar store is the MINUS-R01 release, so no row can retrieve its own utterance. The roster
  receipt's own `knowledge_source_guard` asserts the empty intersection the runner recomputes before
  it dispatches a row.
* No packet is promoted, nothing is encoded and no new speech identity is opened.
* Paid API spend stays 0. No tools array is rendered on any role; the native task-contract ceiling is
  0.

## 8. Registered hashes

`protocol-registered-v1.json` → `cells` and `fit_only_cells` carry the composed config hash and the
protocol hash of all fourteen identities, computed live by `core.config.compose` and
`core.config.protocol_hash` over the fragments the generator itself wrote. The generation cell and
its fit sibling share a composed hash by construction: a cell id and an attempt id are not part of a
composed config.

`registered-facts-v1.json` carries every number this registration asserts before contact — the knob
table, the roster facts, the store facts (8,554 exemplar values over 59 task targets, mean content
69.9 characters, p95 117, max 200; 60 intent cards, mean 702.2 characters, max 895), the pins, the
bad-case targets and the offline dry-run measurements — so a later read is checked against bytes
rather than memory. Every data-root pin was re-hashed against the bytes on disk by the generator at
generation time, not typed.

## 9. What is registered, and what this registration does NOT authorise

Registered: seven baseline fragments, seven experiment fragments, six single-cell campaign plans,
the readiness package (fourteen plan documents, the protocol, the registered facts, the analysis
recipe, the dry-run record, the README), this note, sixteen unconsumed DRAFT exposure rows, the
runbooks `var1_repin_{smoke,plan,planr,exk10,exk30,exdiv,perk16c5}.sh`, `var1_flip_all.sh`,
`batch_chain_var1.sh`, `var1_read.sh`, `var1_dry_run.py`, the generator
`scripts/flights/derive_slurp_var1_cells.py` and the proof test
`tests/unit/test_slurp_var1_registration.py`.

Not authorised by it: any readiness flip; any model, tokenizer, encoder, scorer, server, GPU or
network contact; `core.flight.cli check`; any measured prompt-fit claim; any read of the test split,
TRAIN Fold A, TRAIN Fold B, DEV-1000 or DEV-2000-ADDED; any paper-scale work; any change to the
locked v2.0 plan fragment; any adjustment of the margins after a variant contrast is read; and any
new knob after the first variant's numbers are seen — a VAR-2 family is a new registration.

### 9a. Why only one smoke

The four-row smoke flies the **VAR1-PER-K16C5** form, because it is the only VAR-1 form whose
**contract shape** changes: five Perception candidates instead of three, the configurable
first-occurrence projection, sixteen intent cards instead of eight. VAR1-PLAN and VAR1-PLANR are the
locked plan's own sealed form. VAR1-EX-K10, VAR1-EX-K30 and VAR1-EX-DIV change a retrieval budget on
a route whose contract, instruction bytes and response format are untouched — there is no structural
question a four-row flight would answer that the offline dry run has not already walked over the
real released store. The smoke's population is the **first four rows of R01C in the roster's own
order**, a pure positional selection with zero contacts and no label, score or gold input; split
identity `e9dcea536028d17737b999c65267e47645ca7b3f6f9c4f57622961cf29363ed5`, 17.034938 s of audio.

### 9b. The read driver, recorded as an open item rather than worked around

`scripts/analysis/slurp_paired_roster_read.py` is roster-generic and produces, on this roster with
`--scorer-id slurp-slu-official-train`, the pooled paired contrast, the per-channel table, the
structural counts and the efficiency block. It does **not** produce the per-scenario table (it
hard-codes "NOT AVAILABLE" for its own roster and takes no `--stratum-key`), the entity
FP/FN-by-slot-type decomposition, the Perception coverage or the group-relative advantage table.
`scripts/analysis/plan_cell_read.py` is bound to TRAIN Fold A's roster metadata and a TRAIN-only
comparator and cannot read this cell either.

Teaching the roster-generic driver a `--stratum-key` flag, or writing
`scripts/analysis/slurp_var1_variant_read.py`, is a **separate engineering change with its own tests
and its own review** — not something a registration agent does, and never something done beside a
live flight. It is registered as `VAR1-OPEN-1` and `VAR1-OPEN-2` in the protocol's `open_items` and
**must land before the variant reads**.

## 10. The coordinator's sequence

0. Clear `locks/flight.lock` if an earlier campaign left one. Confirm the tree carries no untracked
   files: they count as dirt for `core.flight.cli check`.
1. Mint `coordination/slurp-stage3-var1-v1/root-admission-v1.json` (decision id
   `slurp-stage3-var1-admission-v1`) with `scripts/flights/batch/mint_decision_receipt.py`, then
   rewrite its `eligible_run_ids` to the **fourteen** run ids of section 2 and its budget caps to
   section 6's. Without that rewrite `core.flight.campaign.declared_readiness` refuses every cell
   but the first ("run … is not eligible in decision receipt").
2. `bash scripts/flights/batch/var1_flip_all.sh` — seven re-pin cycles in order: smoke, PLAN, PLANR,
   EX-K10, EX-K30, EX-DIV, PER-K16C5. Each mints that cell's OWN `prepared_phase_supply` under its
   own run id (harness item E16) and inserts the matching `preparation` requirement.
   **`--allow-output-change` must never be passed.** VAR1-PLANR's prepared artifact **must**
   reproduce VAR1-PLAN's exactly, and so must VAR1-EX-K10's, VAR1-EX-K30's and VAR1-EX-DIV's — those
   three knobs live on the SOLVER route and the prepared artifact seeds PERCEPTION only. Only
   VAR1-PER-K16C5 and the smoke may legitimately differ. A different value anywhere else means the
   knowledge channel moved: stop and report.
3. `bash scripts/flights/batch/batch_chain_var1.sh` — six steps through the SAEA-Batch-Driver
   scheduled task (owner decision 77): PLAN, PLANR, EX-K10, EX-K30, EX-DIV, then PER-K16C5 with its
   four-row smoke ahead of it. One experiment in flight at a time; a failure in any step stops the
   chain and the remaining variants do not open. The chain reads the flight commit from
   `/home/chao/var1-flight-commit.txt`.
4. `bash scripts/flights/batch/var1_read.sh own-null` — the margin table, sealed before anything else
   is read.
5. Land the VAR-1 read driver of section 9b, with its tests, on a clean tree and **not** beside a
   flight.
6. `bash scripts/flights/batch/var1_read.sh variant <cell>` for each of EX-K10, EX-K30, EX-DIV,
   PER-K16C5 and PLANR, then the per-scenario, entity, coverage and advantage tables.
7. The read document `docs/results/<date>-slurp-stage3-var1-construction-variant-read.md`, carrying
   the seven deliverables of section 4b and stating plainly that variants were chosen on
   construction rows and that any winner must be re-read on TRAIN Fold A and DEV-2000-ADDED before
   it is a claim.

## 11. The lessons this package carries forward

1. **A recovery needs two new identities.** The fit gate binds the baseline's
   `native_contact_fit.attempt_id` and refuses one that already carries evidence. Every
   `failure_policy` here says a recovery re-registration needs a new generation attempt id **and** a
   new fit attempt id.
2. **A margin is a property of a roster, not of a mechanism.** Hence VAR1-PLANR.
3. **`check` does not walk the episode.** The offline dry run over the real released stores, on all
   seven forms, is a precondition of the smoke.
4. **A sealed identity is never re-pointed.** VAR-1 is a sibling fragment set; the locked plan's and
   ROLL-1's fragments are untouched.
5. **Selection venue is not claim venue.** CELL-3 selected on Fold A and lost on a fresh roster.
   R01C is a construction roster and nothing selected on it is a result.
