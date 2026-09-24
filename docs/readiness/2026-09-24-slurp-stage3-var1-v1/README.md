# Readiness package: VAR-1 — the first construction-variant rollout of the locked v2.0 plan

Status: **HELD**. This package registers the engineering for **VAR-1**: six 625-row cells on the
SLURP-STAGE3-CONSTRUCTION-R01C construction roster plus one four-row form smoke. It authorises no
flight, no readiness flip and no admission entry. Every cell in it is `held`.

Authority: the owner directive of 2026-09-24 — *training-free RL gains come from rolling out
VARIATIONS of prompts, data and content construction over an optimisation space, scored per variant,
with the winners encoded into demonstrations, constraints and selection rules* — recorded in
`docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md` sections 5–7 as routes **F3** and
**F4**. Governing decisions: 17, 25, 28, 29, 58, 75, 79, 86, 99, 101, 102, 107, 108, 111, 112, 113,
114. The registration note is
`docs/readiness/2026-09-24-slurp-stage3-var1-v1-preregistration.md`.

Stage-3 algorithm (owner decision 101): **`shared-rollout`**, operators `rollout` + `scoring`,
checked by `scripts/checks/stage3_algorithm_label_check.py`. That is the honest label. VAR-1 runs the
algorithm-neutral rollout substrate once per construction variant; the policy is learned **offline**,
by group-relative advantage over variants per runtime-observable state. No credit-assignment, update,
selection or context-application operator runs inside any cell.

## What this family is

Six cells. Each is the **locked v2.0 default plan**
(`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`) with **one existing config knob
moved**, on one roster, read paired by row. No new module, no new store, no new provider, no new
policy id, no new rails file, no code change.

| cell | run id | change against the locked plan | rows |
| --- | --- | --- | ---: |
| **VAR1-PLAN** | `SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1` | none — the comparator | 625 |
| **VAR1-PLANR** | `…-VAR1-PLANR-R01C-V1` | request-identical replicate — the roster's own null | 625 |
| **VAR1-EX-K10** | `…-VAR1-EX-K10-R01C-V1` | exemplars `k` 20 → 10, coverage 10/10/10 | 625 |
| **VAR1-EX-K30** | `…-VAR1-EX-K30-R01C-V1` | exemplars `k` 20 → 30, coverage 30/30/30 | 625 |
| **VAR1-EX-DIV** | `…-VAR1-EX-DIV-R01C-V1` | exemplars `k` 20, coverage `c` 20 → 4 | 625 |
| **VAR1-PER-K16C5** | `…-VAR1-PER-K16C5-R01C-V1` | Perception `k` 8 → 16, coverage 1/16/16, candidate bound 3 → 5 | 625 |
| smoke | `SAEA-SLURP-STAGE3-VAR1-SMOKE-4-V1` | the PER-K16C5 form on the first four R01C rows | 4 |

Each has its fit identity `…-FIT-V1`. **FOURTEEN flight run ids** (seven cells × generation + fit).
Two further ids are model-free-check READS and are never flown —
`SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1` and `SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1`. The coordinator's
decision receipt `coordination/slurp-stage3-var1-v1/root-admission-v1.json` (decision id
`slurp-stage3-var1-admission-v1`) lists the fourteen.

Composed and protocol hashes of all fourteen: `protocol-registered-v1.json`, `cells` and
`fit_only_cells`. A generation cell and its fit sibling share a composed hash by construction — a
cell id and an attempt id are not part of a composed config.

| cell | composed config | protocol |
| --- | --- | --- |
| VAR1-PLAN | `029dbb74e49c…` | `004a32be92e9…` |
| VAR1-PLANR | `2bb848172c3b…` | `86bd0a22216a…` |
| VAR1-EX-K10 | `d27a2d7304e8…` | `92ed2735773a…` |
| VAR1-EX-K30 | `9a68f50a8707…` | `096228b2fc71…` |
| VAR1-EX-DIV | `606016d2b345…` | `866d14b670b9…` |
| VAR1-PER-K16C5 | `5a16192c2fbe…` | `952d4b886891…` |
| smoke | `7ad58b95a96c…` | `bc0d1f7c9f03…` |

## Why a construction-variant rollout, and why now

The Stage-3 semantic-delta line is closed (owner decision 111). Its post-mortem is that the rollouts
varied **only Solver decoding under one fixed context**, so the advantage learned from them ranked
decoding noise: CELL-3 read −1.44 SLU on a fresh roster while its derangement twin read +0.38, which
says the *content* of a Fold-A-selected store was the harm. The directive that replaced it is to
vary the **construction** — what is retrieved, how much of it, how it is grouped, how many candidates
the contract admits — and to learn the policy from the variants' own per-row advantage.

VAR-1 is the smallest honest version of that. It also targets named bad classes from the handoff's
section 6:

| variant | bad class it aims at | headroom cited |
| --- | --- | --- |
| EX-K10 / EX-K30 | entity FN (~31.5 %, `date` omission dominant), same-type filler distance (35 %) | demonstration count is the M1 lever that produced the convention transfer |
| EX-DIV | entity FP (~28.8 %; 184 of 414 empty-gold rows emit) | intent-diversified neighbourhoods change what conventions are copied |
| PER-K16C5 | intent by candidate coverage (own card supplied → 96.5 % covered, absent → 17.3 %) | the largest single documented coverage gap in the plan |

## What the knobs mean

`rails/kb_policy.py` is the authority, and the variants are named for what it does.

* **`saea-fuse-supplyfilter-v1`** (train-exemplars → Solver): `m` is the top-*m* ranked-facet window;
  admitted values are grouped by `task_target` (an SLURP intent id, 59 distinct over 8,554 values);
  `top_l` bounds how many **targets** are served and `c` how many values **per target**. Each
  exemplar value has exactly one content facet, so at `k = m = c = top_l` the route is *k in, k out*.
  `c` 20 → 4 therefore caps the supply at four demonstrations **per intent**.
* **`saea-fuse-associated-values-v1`** (intent-boundaries → Perception): the first *m* facets are
  admitted, traversed in rank order taking at most `c` new values per facet, stopping at `top_l`
  overall. The store has 60 facets and 60 values — one card per intent — so `c = 1` with
  `m = top_l = k` gives exactly *k* cards. Those cards average 702 characters, so `k` 8 → 16 is the
  family's single largest text change.

**One required companion, declared and not hidden.** `rails.candidate_semantic_supply` refuses a
candidate bound above three under the literal-3 bounded first-occurrence projection, so
VAR1-PER-K16C5 also declares the already-registered
`configurable-bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1`. The projection itself is
unchanged — first occurrence in the model's own order, distinct on `intent_id` — only its declared
input bound moves. The bound is moved at **both** agreeing sites (the Perception fill contract and
the slot-contracts candidate supply); `max_total_values` 28 and `max_values_per_candidate` 16 are
**not** moved.

## The venue, and the two mandatory deviations

`SLURP-STAGE3-CONSTRUCTION-R01C`: 625 TRAIN recordings, 18 scenario strata of 26–42, 625 distinct
utterance ids, 67 headset / 558 far-field, 2,726.847188 s of audio, `roster_role: construction`,
`split_role: discovery`, split identity `f56bc386…`. Zero shared recordings and zero shared
utterances with TRAIN Fold A, TRAIN Fold B, DEV-1000 and DEV-2000-ADDED.

Two things follow, and neither is a variant: the **R01C re-pointing** cell ROLL-1 already proved
(query-vector pins, preparation receipts, packet promotion receipt), and the **MINUS-R01 exemplar
store** — the parent pool contains R01's own utterances and a construction roster may never retrieve
itself (coordinator decision 102).

**R01C's roster receipt carries a per-item stratum**, so a **gold per-scenario table is derivable
offline** here. That is the one thing this venue gives that DEV-2000-ADDED withheld.

**VAR1-PLAN is flown, not imported.** No plan-form arm has ever been sealed on R01C: ROLL-1 flew the
five-sample grouped-Solver policy, not the locked single-sample plan, and greedy decoding is not
bit-reproducible across batch compositions. The locked plan's TRAIN Fold A (63.63 / 82.22) and
DEV-2000-ADDED (65.40 / 76.60) numbers are context and are never this family's comparator.

## The roster's own null flies second, and the margins are not known here

`h_SLU` and `h_intent` are the CI95 half-widths **VAR1-PLAN against VAR1-PLANR** produces on this
roster, with the same estimator, clustering (`utterance_id`; 625 distinct, so the cluster is the
row), seed 20260915 and 10,000 draws as every variant contrast. The own-null read
`SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1` is completed and **sealed before any variant contrast stage is
read**, and the margins are never adjusted afterwards. The TRAIN Fold A margins (1.2485 / 0.9943) and
DEV-2000-ADDED margins (1.2525 / 1.1520) are recorded in `registered-facts-v1.json` as **context
only**: a margin is a property of a roster, never of a mechanism.

## The decision rule: a table, not a verdict

**This family returns no admission verdict.** No ADMITTED / NEUTRAL / HARMFUL label is attached to
any VAR-1 cell, no module is admitted, no store is released, nothing is locked. A variant whose CI95
excludes zero **and** whose point estimate lies outside ±h is called **SEPARATED FROM THE NULL**;
anything else is **INSIDE THE NULL**.

Primary deliverables, reported whatever the table says: the per-row paired variant table; the
own-null margin table above it; the **gold per-scenario table** in both weightings; **entity FP / FN
by slot TYPE**; **Perception coverage** (gold intent in the row's own candidate list); the
**group-relative advantage of each variant per runtime-observable state** (predicted scenario,
candidate count, channel, duration band), with per-state *n* and never read below *n* = 20; the
frontier row per 625 rows.

**Nothing selected here is a result.** R01C is a construction roster. A variant that separates from
the null is a **candidate**, and the next step is a re-read of that one variant on TRAIN Fold A at
Fold A's own null and then on DEV-2000-ADDED at its own null. CELL-3 is the standing evidence for
why.

## The offline seven-form dry run

`dry-run-v1.md`. **All seven forms PASS, zero contacts, zero defects.** Every row of every form
walked `perception → solver → reviewer → planner` and delivered; every REVISE revisit acquired
nothing it already held; every duplicate-candidate row walked instead of raising.

Supplied items per row, measured over the four smoke rows against the real released stores:

| form | cards @ Perception | exemplars @ Solver | slot-contract values @ Solver |
| --- | ---: | ---: | ---: |
| VAR1-PLAN / PLANR | 8 | 20 | 11 |
| VAR1-EX-K10 | 8 | **10** | 11 |
| VAR1-EX-K30 | 8 | **30** | 11 |
| VAR1-EX-DIV | 8 | **7 / 15 / 8 / 16** (mean 11.5) | 11 |
| VAR1-PER-K16C5 / smoke | **16** | 20 | **12** |

Three registered readings: the `k` knobs are exact (*k* in, *k* out); **EX-DIV is data-dependent and
by a lot**, so it changes the demonstration **count** as well as its diversity and its contrast is
not a pure diversity contrast — the read must say so beside EX-K10, the count-only control at a
comparable mean; and the five-candidate bound is nearly free at the Solver (11 → 12 values) because
the 28-value budget is unmoved, so PER-K16C5 spends at Perception.

## Prompt fit

Not measured in tokens here; no tokenizer was contacted. Because a store's decision travels as typed
content blocks and not in the rendered instruction (every form's instruction is the same size), the
dry run measures **supplied content characters** per node per row. Widest-case differences against
VAR1-PLAN, at a deliberately pessimistic 2.5 characters per token: EX-K30 Solver **+1,334 chars ⇒
≤ 534 tokens**; PER-K16C5 Perception **+5,708 ⇒ ≤ 2,284**; PER-K16C5 Solver **+1,605 ⇒ ≤ 642**.
Against CELL-2's measured bounds (Solver 21,821, Perception 19,992 — both **with** a delta block
VAR-1 does not carry) the worst case is about 22,463 against the 24,576-token slot. **REFUSE is
arithmetically excluded; `COMPACT_REQUIRED` is the expectation** and is recorded and proceeded on
under `context_fit_policy: compact-or-abstain`. The fail-closed fallback — k = 26 for EX-K30, k = 12
for PER-K16C5, each with new run, generation and fit identities — is registered in the
preregistration, section 5.

## Budgets

Per 625-row cell: 6,875 generation calls (625 × 11), 27,500 fit endpoint calls, 29,996 repeated
speech audio seconds, 8.0 GPU hours, 0 native task-contract calls, 1 official complete scoring job.
Smoke: 44 / 176 / 188 / 1.0 / 0 / 0. Expected about 4.1 contacts per row (≈ 2,563 per cell) and about
1.05 GPU hours per cell, roughly 6.5 for the family — ESTIMATES, never targets. **No VAR-1 knob adds
a contact.**

## The proofs on the committed tree

* Offline gates, all exit 0: `engineering_base_check.py`, `harness_admission_check.py`,
  `results_ledger_check.py`, `tool_catalog_check.py`, `experiment_handoff_check.py`,
  `finite_completion_policy_check.py`, `stage3_algorithm_label_check.py`,
  `derived_media_confinement_check.py`.
* The composed and protocol hashes of all fourteen identities, computed offline by
  `core.config.compose` / `core.config.protocol_hash` by the generator itself, never typed:
  `protocol-registered-v1.json`.
* The offline seven-form dry run: `dry-run-v1.md`.
* `tests/unit/test_slurp_var1_registration.py`: every baseline equals the locked plan on every key
  except the R01C re-pointing, the per-cell identity bookkeeping and its own declared knobs; nothing
  but the knobs moves inside `knowledge_stores` and `phase_material`; VAR1-PLANR equals VAR1-PLAN on
  every key except the fit identity and the prose; a bound above three carries the configurable
  projection; every registered hash reproduces from `core.config.compose`.

**`core.flight.cli check` was NOT run** and no prompt-fit bound is claimed as measured. That check
needs the coordinator's clean-tree cycle against the minted receipt.

## What is registered here

In this directory: `protocol-registered-v1.json`, `registered-facts-v1.json`,
`analysis-recipe-v1.json`, `dry-run-v1.md` and fourteen plan documents
(`{plan,planr,exk10,exk30,exdiv,perk16c5,smoke}-{generation,fit}-plan-registered-v1.json`).

Outside it: the preregistration note, seven baseline fragments, seven experiment fragments, six
single-cell campaign plans, sixteen unconsumed DRAFT exposure rows, the generator
`scripts/flights/derive_slurp_var1_cells.py`, the proof test
`tests/unit/test_slurp_var1_registration.py`, and the runbooks
`var1_repin_{smoke,plan,planr,exk10,exk30,exdiv,perk16c5}.sh`, `var1_flip_all.sh`,
`batch_chain_var1.sh`, `var1_read.sh` and `var1_dry_run.py`.

## The order the coordinator flies

1. mint `coordination/slurp-stage3-var1-v1/root-admission-v1.json`, rewrite its `eligible_run_ids`
   to the fourteen and its budget caps to this family's;
2. `var1_flip_all.sh` — seven re-pin cycles (smoke, PLAN, PLANR, EX-K10, EX-K30, EX-DIV, PER-K16C5).
   **PLANR's, EX-K10's, EX-K30's and EX-DIV's prepared first-phase supply must reproduce PLAN's
   exactly** — those knobs live on the SOLVER route and the prepared artifact seeds PERCEPTION only.
   Only PER-K16C5 and the smoke may legitimately differ;
3. `batch_chain_var1.sh` — six steps: PLAN, PLANR, EX-K10, EX-K30, EX-DIV, then PER-K16C5 with its
   four-row smoke ahead of it. One experiment in flight at a time;
4. `var1_read.sh own-null` — the margin table, sealed before anything else is read;
5. land the VAR-1 read driver (open items `VAR1-OPEN-1` / `VAR1-OPEN-2`), with its tests, on a clean
   tree and **not** beside a flight;
6. `var1_read.sh variant <cell>` for each variant and for PLANR, then the per-scenario, entity,
   coverage and advantage tables;
7. the read document `docs/results/<date>-slurp-stage3-var1-construction-variant-read.md`.

## The open items, registered rather than worked around

* **`VAR1-OPEN-1`** — `scripts/analysis/slurp_paired_roster_read.py` produces the pooled paired
  contrast, the per-channel table, the structural counts and the efficiency block on this roster, and
  nothing else: it hard-codes "per-scenario NOT AVAILABLE" and takes no `--stratum-key`, so the gold
  per-scenario table — which **is** derivable on R01C — does not come out of it as committed.
  `scripts/analysis/plan_cell_read.py` is bound to TRAIN Fold A's roster metadata and a TRAIN-only
  comparator and cannot read these cells either.
* **`VAR1-OPEN-2`** — the entity FP/FN-by-slot-type decomposition, the Perception coverage read and
  the group-relative advantage table have no committed driver at all.
* **`VAR1-OPEN-3`** — the prompt-fit bound of EX-K30 and PER-K16C5 is not measured in tokens here.

VAR1-OPEN-1 and VAR1-OPEN-2 are a separate engineering change with their own tests and review, and
**must land before the variant reads** — never beside a live flight.

## The lessons this package carries forward

1. **A recovery needs two new identities** — a new generation attempt id **and** a new
   `native_contact_fit.attempt_id`.
2. **A margin is a property of a roster, not of a mechanism.** Hence VAR1-PLANR.
3. **`check` does not walk the episode.** The offline dry run over the real released stores, on all
   seven forms, is a precondition of the smoke.
4. **A sealed identity is never re-pointed.** The locked plan's and ROLL-1's fragments are untouched.
5. **Selection venue is not claim venue.** CELL-3 selected on Fold A and lost on a fresh roster.
