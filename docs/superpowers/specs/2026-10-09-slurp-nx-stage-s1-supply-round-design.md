# NX Stage S round S1: knowledge SUPPLY at the Solver node (design)

Author: Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1), 2026-10-09, branch
`fable/nx-stage-s-design` (base master `57fe863ee`). Status: DESIGN, model-free. No model, server, tokenizer, encoder,
embedder, scorer, GPU or network contact was made, and nothing was written under the data root. Inputs are aggregate
tables only: counts, rates, pp, slot-type names, ids and hashes. No utterance text, transcript, gold value, filler or
model output was read into this note.

Authority: NX programme `docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md` (C0, C2, C3, F1 "Stage S",
F2), owner decisions 192 (1.5 pp predicted at a measured conversion before an SLU mechanism registers), 199 (empty is
legal; retrieval may return empty), 190 (same-flight floors SLU 1.49 / intent 0.65 at n = 1,080), 191 (rule-card
slot-convention line CLOSED in every design), 228-234 (NX base and cadence). Nothing here registers a cell, authorises
a flight or admits a component.

**Answer first.** At the Solver node, six supply arms can be declared over the same `QueryState`: five reuse the
existing knob tails and release swap, and one needs a model-free, TRAIN-only release. **None of them reaches 1.5 pp
at a measured conversion.** The best arm's prediction at measured conversions is **+0.20 pp** (`s1-n1i-k10`). Its
upper bound at the M1 printing analogue is +0.85 pp. Every earlier supply read at this node is null or closed: k 30,
k 10, the diversity cap, F10, W4, W5 and the score-threshold abstention rules (section 2). Section 7 sets out what the
owner would have to accept to fly the round. A further gap: on the review-off module base, a supply column cannot be
declared without one model-free engineering change, because the module compiler admits only template columns
(section 1.3).

---

## 1. Solver-node supply axes

### 1.1 What the Solver reads on the NX base

The base is the review-off COMP-1b module graph on lock v2.1 (`configs/baseline/slurp-native-stage3-nx-r1-i2-solver-
fold-b-baseline-v1.json`, program `phase-native-module-v1-c8`; module components `agree-vote-seed` and
`centroid-boundary-key` ON, every other component OFF; `supply-abstain` and `e3-progressive-slots` are catalogue
entries with no compiled state, `rails/consumption_module.py` `COMPONENT_CATALOGUE`). The Solver phase reads two
stores. The third store (`intent-boundaries`) is a first-phase Perception supply seeded into the row's one initial
`QueryState`, so a Solver arm cannot vary it (`parse_supply_variant_knob` refusal: "names the program's FIRST phase").

| store | route at the Solver | release / snapshot (relpath) | selection knobs as locked | declared `alternates` |
| --- | --- | --- | --- | --- |
| `train-exemplars` | `phase_supply.solver` | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/{release,snapshot}.json` (snapshot `4c498dc0...`) | `k` 20; `fuse_policy` `saea-fuse-supplyfilter-v1` with `fuse_coverage` m 20 / c 20 / top_l 20; `rank_policy` `saea-rank-wcos-prior-agree-v1` (w_cos 1, w_prior 0, w_agree 0); `tau` 0; content dimension; speech query vectors of the row (Fold B pin `573a8a37...`); facet vectors `vectors/slurp-kus3/facet-vectors.jsonl` | none |
| `slot-contracts` | `candidate_supply.solver` | `knowledge/slurp/semantic/slot-contracts-v2/{release,snapshot}.json` | `max_candidates` 3; `max_total_values` 28; `max_values_per_candidate` 16; projection `bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1` | none in the NX base. `slot-contracts-w4-v1` was declared only in the W4-SV cell and is closed (decision 191). |

Fit frame of the NX base (template frame, `fit-measure-v1.json` of R1-i2): slot 24,576 tokens, completion ceiling 512,
`max_supplied_items` 55, `tokens_per_supplied_item` 235, `base_prompt_tokens` 2,000. Measured supplied items per row
on the COMP-1b Fold A pool are mean 41.6, with quartile cuts 39 / 42 / 45 (exchange-rate note section 6). Fixed at the
first Solver contact: 8 boundary items, 1-25 slot cards, and 20 exemplars.

**What the exemplar knobs mean (verified in code).** Each exemplar value's `task_target` is the utterance's intent
(`rails/knowledge_build.py:1163`, `task_target=row.intent`). `_fuse_supply_filter` (`rails/kb_policy.py:1047`) admits
the top `m` recalled facets, groups their values by `task_target`, keeps the `top_l` best-scoring intents, and takes
at most `c` values per intent. As a result, **`fuse_coverage.c` is already a per-intent exemplar cap and `top_l` an
intent-count cap.** A per-intent cap therefore needs no preparation. VAR-1's EX-DIV arm was `k` 20 / m 20 / c 4 /
top_l 20 (`configs/baseline/slurp-native-stage3-var1-ex-div-r01c-baseline-v1.json`).

### 1.2 Axes available without new runtime code (E42 knob tails and the release swap)

`rails/supply_variants.py::SUPPLY_VARIANT_KNOB_TAILS` admits exactly the following knobs:
`phase_supply.<phase>.{k, fuse_coverage.m, fuse_coverage.c, fuse_coverage.top_l}` and
`candidate_supply.<phase>.max_candidates`. Values must be positive integers, so an arm cannot set `k` 0. A
`release_swap` may repoint ONE store to an alternate that the base declares.

| axis | path | admissible range at the Solver | prior reads at this node (development numbers) |
| --- | --- | --- | --- |
| exemplar count | `train-exemplars.phase_supply.solver.k` (+ m / c / top_l) | any positive int within the fit | k 30: W-SV-1 same-flight, Fold A, **-0.46 [-1.85, +1.12]** vs twin +0.37: "exemplar-k line closed at k 30 on this roster" (`docs/results/2026-09-29-slurp-wsv1-fold-a-column-read.md`). k 10: VAR-1 EX-K10 minus PLANR **+0.07** pooled, point only, cross-flight, R01C 625 (`docs/results/2026-09-25-slurp-var1-complete-evidence.md` item 1); inner-loop intent +0.48 [-1.12, +2.24] |
| per-intent cap / intent count | `fuse_coverage.c`, `fuse_coverage.top_l` (with `k`, `m`) | positive ints | EX-DIV (c 4, 10.29 exemplars mean) **+0.17 [-1.50, +1.88]** vs PLAN, confounded with count (VAR-1 note item 2) |
| slot-card candidates | `slot-contracts.candidate_supply.solver.max_candidates` | 1 or 2 only (lowering; `CandidateSemanticSupplySpec` refuses > 3 under the fixed projection, instrument design Q5) | none flown at the Solver |
| exemplar release | `release_swap` on `train-exemplars` | only an alternate the base declares | F10 empty-contract release **CLOSED** (`docs/results/2026-09-25-slurp-f10-complete-verdict.md`: +0.34 [-1.42, +2.29]; "do not replicate this variant") |
| slot-card release | `release_swap` on `slot-contracts` | only an alternate the base declares | W4 / W4-SV rule cards **CLOSED** (decision 191) |

The following are NOT Solver-node axes and stay out of Stage S at the Solver. Key source (K6p), agreement weight and
contrast cards are first-phase Perception axes (P-SV-4 read NOT NOMINATED, master `57fe863ee`). `rank_weights`,
`query_source`, `facet_source`, `max_total_values` and `max_values_per_candidate` are not knob tails. The second W5
exemplar route is a new store id, held and closed under decision 192 unless the owner reopens it.

### 1.3 What needs work before any S1 cell can register

1. **E-S1 (engineering, model-free, needed for EVERY arm): a supply column on the module base.**
   `parse_consumption_module_block` refuses every non-template column under `review_loop: off` ("review-off profile
   does not support branch columns"). `verify_declared_module` requires the declared policy blocks to equal the
   compiled ones. A hand-written `roles.solver.supply_variants` block or a store `alternates` field is therefore
   refused on the NX base. Changes needed:
   - add a column kind `supply` (`{column_id, kind: "supply", node: "solver", overrides?, release_swap?,
     max_supplied_items}`) and a `supply_frame` (`{twin, fit_estimate, delivering_max_supplied_items}`), compiled to
     `native_episode.roles.solver.supply_variants` with `arm_visits: "first"`, the twin `aa` and the delivering arm
     `lock` last;
   - add the ceiling term K - 1 and the family id `phase-native-module-v1-c<ceiling>`;
   - pass declared alternates through to `knowledge_stores.<store>.alternates`;
   - refuse a supply column next to template or branch columns (one fan-out mechanism per episode, as the loader
     already refuses `template_variants` next to `supply_variants`);
   - change no runtime file. The E42 runtime, the release-swap route, receipt schema v3 and I7v are already merged
     (`rails/supply_variants.py` docstring; instrument design section 2).
2. **E-S2 (engineering, model-free): the node-local reader.** `scripts/analysis/slurp_nx_solver_column_read.py`
   reads `saea-supply-variant-arms-v4` template columns only ("this reader reads template columns only"). Extend it to
   v3 supply columns, keeping the same primary (`exact_set_normalised`) and secondaries. Also add per-arm supply
   statistics: supplied-item count, the entity-free share of the exemplars and the value-in-supply class E1 / E2 / E3
   / none per error item, all from the arm's sealed `supplied_value_ids`. Check that
   `scripts/analysis/slurp_nx_postproc_v4_apply.py` takes supply-arm columns from the same render
   (`stage3_rollout_score.py --mode supply-variants`), because W-SV-1 already scored supply columns that way.
3. **P-N1 (model-free preparation, one arm family): a TRAIN-only exemplar release** (section 2, arm `s1-n1i`).

---

## 2. The S1 arms (K = 8: six candidates, the twin `aa`, the delivering `lock` last)

**Residual counts.** Each count is cited from a file; no new number is introduced.
- **[A]** COMP-1b Fold A, first Solver answer (`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` sections
  3 and 6). SPURIOUS 264, of which 100 are E1 copied (type, value) pairs, 5 E2, 27 E3 and 132 none. MISSING 188, of
  which 103 are E1, 1 E2, 14 E3 and 70 none. WRONG-TYPE 54 (E1 14, E2 4). Empty-gold false fill 161 of 414 rows.
- **[B]** NX R1 Fold B `lock` column, normalised (node-local v2 `tables.md`, read-only). 1,080 rows, 392 of them
  empty-gold. False fill 34.44 % of 392 (135 rows, arithmetic). Gold 944: exact 498, missing 202, wrong 244;
  predicted 982, spurious 240. Official pooled SLU-F1 62.13; `aa` twin +0.57 [-0.10, +1.27]; v4g(lock) 63.69
  (+1.55 [+0.81, +2.33]).

**Measured conversions used.** M1 printing conversion 0.2471. N1 at θ 0.6 on COMP-1b Fold A: 128 rows gated
(122 zero-gold / 6 gold), 24 spurious removed, 3 exact lost, oracle +0.55, +0.13 at M1 (taxonomy refresh S5 table);
on AGREE, oracle +0.68 [+0.28, +1.10] and +0.17 at M1. The R1 c3 explicit empty decision moved false fill -15.82 pp
[-19.64, -12.24] and non-empty exact -1.74 pp at the template level. W5 newly printed 10 items, worth +0.15 pp. VAR-1
and W-SV-1 are cited in section 1.2. Exchange rates (Fold A): +0.056 per raw-exact row, +0.033 per emptied false-fill
row, +0.029 per SPURIOUS removed, +0.062 per MISSING recovered, +0.091 per wrong entity repaired.

**How predictions are formed.** A "measured" prediction is a measured analogue of the same axis. A "bound" is the
named residual x 0.2471 (M1) x the class exchange rate. The bound assumes that un-printing or newly printing a value
converts at M1's printing rate, with zero harm. That is an analogue, not a measurement, and it is reported only as a
ceiling.

| arm | declaration (supply only; template unvaried) | targeted residual (count) | mechanism hypothesis | prediction at a measured conversion | bound (M1 analogue, harm not netted) | harm channel and guard |
| --- | --- | --- | --- | --- | --- | --- |
| `s1-k10` | knob tails: `train-exemplars...k` 10, `fuse_coverage` m 10 / c 10 / top_l 10 | SPURIOUS copied pairs E1 100 / 264 [A]; false fill 161 / 414 [A], 135 / 392 [B] | fewer printed slot-bearing pairs mean fewer exemplar slots copied onto utterances that do not carry them (exchange note reading 2) | **+0.07 pp** (VAR-1 EX-K10 minus PLANR, point, cross-flight; about +1 raw-exact row at 0.056) | 100 x 0.2471 x 0.029 = **+0.72 pp** (about 25 entities removed) | MISSING E1 103 [A] lose their print when the printing exemplar ranked 11-20 (preparation P2 counts them); intent +0.48 [-1.12, +2.24] in the inner loop |
| `s1-pure` | knob tails: k 60, m 60, c 20, **top_l 1** | MISSING with value NOT in supply: 70 / 188 [A] (152 of 189 MISSING sit on intent-right rows, taxonomy S2 table) | up to 20 exemplars of the single best-matching intent print more of that intent's slot values (date, order_type, transport_type lead MISSING [A], [B]); empty is legal when the intent has fewer than 20 in the top 60 (rule 199) | **+0.15 pp** (W5 analogue: a speech-keyed slot-exemplar route newly printed 10 items, 0.15 pp) | 70 not-in-supply items fully printed at M1 = **+1.04 pp** (taxonomy S2: 1.04 on COMP-1b Fold A) | SPURIOUS copies of same-intent slots; intent guard: Solver rank-2 saves 18 / 69 [A] may depend on other intents' exemplars |
| `s1-icap5` | knob tails: k 40, m 40, **c 5, top_l 4** | WRONG-TYPE 54 [A], of which 18 have the value printed (E1 14 + E2 4); same-intent repeated copies within SPURIOUS E1 100 | count held at at most 20 exemplars but at most 5 per intent across the 4 best intents: a slot-type inventory per plausible intent without one intent's repeated pairs | **+0.17 pp** (EX-DIV analogue; count-confounded, which this arm removes) | 18 x 0.2471 x 0.091 = **+0.41 pp** | M1 conversions on same-intent E1 items that drop out above the cap of 5 (P2) |
| `s1-cards1` | knob tail: `slot-contracts.candidate_supply.solver.max_candidates` 1 | SPURIOUS E3 27 / 264 [A] (23 / 245 on DEV) | slot cards of non-rank-1 candidates name values that the Solver tags spuriously; one card set means one slot inventory | none measured at this node | 27 x 0.2471 x 0.029 = **+0.19 pp** (oracle 27 x 0.029 = 0.78) | MISSING E3 14 [A]; **intent guard at risk**: the rank-2 conversions (18 / 69 Fold A) may use the rank-2 card |
| `s1-n1i` | release swap `train-exemplars` -> alternate `size-pool-annotated-exemplars-n1-intent-v1` (P-N1) | empty-gold false fill 161 / 414 [A], 135 / 392 [B] | N1 as a static supply signal: for intents whose pool entity-free share is at least 0.6, only entity-free exemplars stay. Rows that recall those intents see an entity-free share near 1. Inside zero-gold rows a higher share goes with less emission (AUC 0.345, abstention note 2.1) | **+0.13 pp** (N1 at M1 on COMP-1b Fold A; about 4 emptied rows at 0.033) | N1 oracle **+0.55 pp** (128 rows gated, 24 spurious, 3 exact lost) | the slot-bearing minority rows of those intents lose same-intent slot exemplars (M1 loss). Overlap with v4g `ee10` is small: after the Wilson guard only `qa_maths` fires (v4g lock record section 4) |
| `s1-n1i-k10` | the release swap of `s1-n1i` **plus** the knobs of `s1-k10` (disjoint, admitted together) | all zero-gold SPURIOUS: 185 entities on 161 rows [A] | the static none signal and fewer printed pairs remove the two supply shapes of false fill together | **+0.20 pp** (0.07 + 0.13; additive by assumption, at most that on shared rows) | 0.72 + 0.13 = **+0.85 pp** | both arms' channels |
| `aa` | `replicate_of: lock`, no override | the within-flight null; R1 i1 twin +0.57 [-0.10, +1.27] | -- | -- | -- | -- |
| `lock` | delivering, LAST, no override: the locked supply above | -- | -- | -- | -- | -- |

**Why not other arms.**
- k 30 is closed by the W-SV-1 read.
- The F10 empty-contract release, the W4 card release and the second W5 route are closed (F10 verdict, decision 191,
  decision 192 recommendation 1).
- Score-threshold supply abstention reads 0.00 cross-fitted in every family (abstention note 3.2), so no arm uses a
  cosine floor.
- An extreme low-count arm (k 1) would only re-measure module M1's admitted gain in reverse, which is a known harm.

**Declared round effect.** The best arm at a measured conversion is **`s1-n1i-k10`, +0.20 pp official pooled SLU-F1**.
That is 0.13 x the 1.49 pp floor and far below decision 192's 1.5 pp. Even the M1-analogue ceilings stay below the
bar: the best single arm is `s1-pure` at +1.04 pp and the composite is +0.85 pp. **The round does not meet decision
192.** Section 7 sets out the owner's options.

**Estimand warning (R1 lesson 3).** Per-row SLU-F1 scores every empty-gold row as 0 whatever the arm answers. It is
therefore blind to the false-fill mass that four of the six arms target. Pooled micro SLU-F1 is the only estimand;
per-row numbers are reported but never quoted as an effect.

---

## 3. Which Solver template the round runs on

The supply is varied and the template is fixed, because the loader refuses `template_variants` next to
`supply_variants` on one node. The delivering template is the one in the module lock that the S1 block names:

- **Now:** lock **v2.1** (`slurp_module_hooks.CURRENT_LOCK`), Solver template
  `probes/slurp_native_role_solver_v2.txt` (`18bff5c5...`).
- **If R1-i2 NOMINATES an arm and its Fold A two-arm confirmation passes:** the R1 lock lands as module lock layer
  `v2.2` (lock v2.1 plus that Solver template pin; a new entry in `lock_versions` with its tests). S1's module block
  then changes in ONE line, `"lock": "v2.1"` -> `"lock": "v2.2"`, and the writer derives everything else.
- The S1 family constants file carries `S1_LOCK = "v2.1"` as its only template-bearing line.
- If the i2 pick is an empty-decision template (i2-c1 / i2-c3), the false-fill residual shrinks before S1 flies. In
  that case preparation P1 must be re-run on the i2 pick's Fold B column, and the `s1-n1i*` predictions re-derived
  from it before registration.
- The deliver normaliser stays `saea-deliver-normalise-v3` until the separately registered hook step moves the SLURP
  profile to v4g (v4g lock record section 5). v4g is read offline as a column, exactly as in R1.

---

## 4. The read (one READ row, after the seal, root countersigned before any column score exists)

1. **Node-local v2 reader** (E-S2): paired vs `lock`, whole-utterance cluster bootstrap, 10,000 draws, seed 20260915,
   CI95.
   - Primary: `exact_set_normalised`.
   - Secondaries: empty-gold false fill, non-empty exact, parse validity, per-slot-type counts.
   - Supply statistics: supplied items, exemplar entity-free share, E1 / E2 / E3 / none per class, and copied-pair
     counts per arm.
   - Diagnostic only; gates nothing.
2. **Official per-arm columns.**
   - Scoring: `stage3_rollout_score.py --mode supply-variants`, `slurp-slu-official-train`, eight complete column jobs,
     never sharded.
   - Contrasts: `aa-vs-lock` and `<arm>-vs-lock` through `stage3_paired_read.py`, row bootstrap, cluster key
     `sample_id`.
   - **Nomination rule (iteration-2 rule, unchanged).** X is NOMINATED iff all three hold:
     - (a) the official pooled SLU-F1 delta X minus `lock` has a CI95 lower bound > 0;
     - (b) that delta exceeds the `aa` delta of the same flight;
     - (c) the rows whose official intent correctness differs from `lock` number at most 7 (0.65 pp at 1,080).
   - HARM iff the CI95 upper bound < 0. Ties go to the larger delta, then the smaller supply.
   - Equal-scenario weighting (18 x 60) is reported beside the natural mixture and never gates.
3. **Offline v4g columns** (`slurp_nx_postproc_v4_apply.py --apply v4g`; 0 GPU):
   - `v4g(X) - X` for every arm;
   - `v4g(X) - v4g(lock)`, which is arithmetic on levels and descriptive;
   - this is the composition check that R1 c3 needed. An empty-signal arm whose official gain disappears under v4g
     duplicates `ee10` / `scope`, and the read says so.
   - Proposed for the coordinator to rule (not gating as drafted): a NOMINATED arm proceeds to Fold A only if
     `v4g(X) - v4g(lock)` is also positive at the point.

Claim ceiling `nominated` (instrument design Q6); development numbers only (decisions 28, 86). The per-stratum table
(scenario, empty-gold vs non-empty) is part of every verdict.

---

## 5. Exposure

- **Select on TRAIN Fold B** (`SLURP-EVO-FOLD-B-V2`, split identity `4407794c...`). Prior exposure carried: R1 i1,
  R1 i2, P-SV-4 and the earlier Fold B phase-2 cells. The roster is reused, so the winner's-curse caveat of R1-i2
  applies.
- **Confirm once on TRAIN Fold A**, as a two-arm column (the pick, `aa`, `lock`; K = 3) on the same base at the Fold A
  pins of the COMP-1b Fold A cell. One attempt; no re-selection on Fold A.
- **What a TRAIN-built release MAY see.**
  - Only the released construction pool of `size-pool-annotated-exemplars`: 9,354 values, which already excludes
    every utterance with a recording in TRAIN Fold A, TRAIN Fold B or DEV-1000.
  - Of that pool, only its metadata: each value's `task_target` (intent) and its entity count, which is entity-free or
    not (2,949 of 9,354 are entity-free, `scripts/build_slurp_train_exemplars_with_empty_store.py` docstring).
  - The selection rule's one parameter: θ = 0.6, fixed here from the N1 note (its cross-fit did not confirm θ, so θ
    is declared, never tuned on a read).
- **What it MAY NOT see.**
  - Any Fold A, Fold B, DEV or test row, or any gold label of those rosters.
  - Any sealed output, trace or score of any flight, and any per-row retrieval result of an evaluation roster.
  - This or any NX read.
  - The release is a pure SELECTION, with every surviving facet and value byte-identical to the parent's, like
    `build_slurp_stage3_r01_excluded_exemplar_store.py`. The pinned facet-vector file stays a superset, so no
    re-encoding is needed.
- **Predictions (P2, P3)** read the Fold B selection roster's sealed R1 `lock` column (and DEV-2000-ADDED A2), never
  Fold A, which is held for the confirmation. Arm values are fixed in this note before those numbers exist.

---

## 6. Registration skeleton and preparation checklist (for a Sonnet engineering agent)

### 6.1 Identities (cloned from the R1 family; `scripts/flights/nx/` gains a round parameter `s1`)

| item | value |
| --- | --- |
| cell / experiment | `slurp-native-stage3-nx-s1-supply-fold-b-v1` / `SAEA-SLURP-STAGE3-NX-S1-SUPPLY-FOLD-B-V1` |
| arm run / attempt | `SAEA-SLURP-STAGE3-NX-S1-SUPPLY-FOLD-B-V1` / `attempt-slurp-native-stage3-nx-s1-supply-fold-b-generation-v1` |
| FIT run / attempt | `SAEA-SLURP-STAGE3-NX-S1-SUPPLY-FOLD-B-FIT-V1` / `attempt-slurp-native-stage3-nx-s1-supply-fold-b-fit-v1` |
| smoke run / FIT | `SAEA-SLURP-STAGE3-NX-S1-SUPPLY-FOLD-B-SMOKE-4-V1` / `...-SMOKE-4-FIT-V1` (first attempts) |
| READ run | `SAEA-SLURP-STAGE3-NX-S1-SUPPLY-FOLD-B-COLUMN-READ-V1` |
| decision id / receipt | `slurp-nx-s1-supply-fold-b-admission-v1` / `coordination/slurp-nx-s1-supply-fold-b-v1/root-admission-v1.json` |
| package | `docs/readiness/2026-10-??-slurp-nx-s1-supply-fold-b-v1/` + `-preregistration.md` |
| Fold A confirmation (only after a NOMINATED read) | `slurp-native-stage3-nx-s1-supply-fold-a-confirm-v1`, K = 3, ceiling 4 |
| `stage3_algorithm` | `none` (an instrument cell) |
| `stage3_measurement` | design `same-flight-supply-variant`, `primary_metric_key` `slu`, `nomination_rule` `official-column`, intent guard 7 rows, in-chain A/A = `aa`, tuning roster `SLURP-EVO-FOLD-A-V2` is NOT used for tuning (arm values fixed here), read roster `SLURP-EVO-FOLD-B-V2`, floors SLU 1.49 / intent 0.65; `expected_effect_pp` and `claims_benefit` per section 7 |

### 6.2 Budgets (by analogy with R1; arithmetic from the R1-i2 package section 4)

| budget | arm | smoke (4 rows) |
| --- | --- | --- |
| contacts per row | 1 Perception + 8 Solver arms = 9 | 9 |
| program | `phase-native-module-v1-c9` (ceiling 2 + (8 - 1) = 9; the family covers c2-c24) | same |
| generation / native task-contract calls (run-cumulative) | 1,080 x 9 = **9,720** | 4 x 9 = **36** |
| FIT `contact_cap` (STRUCTURAL: rows x max_contacts x (max_speech_packets + 3), never scaled) | 1,080 x 9 x 4 = **38,880** | 4 x 9 x 4 = **144** |
| speech audio seconds (run-cumulative) | ceil(3,154.797 x 9) = **28,394** | ceil(4-row audio x 9), computed by the writer (i2: 82 at x 8) |
| `variant_cost` | +7 Solver contacts per row; +7 x 3,154.797 = +22,083.58 speech seconds per flight | -- |
| planned GPU-h (a ceiling) | **4.0** (R1 i1 flew 8 contacts per row in 2 h 16 m 54 s; x 9/8 is about 2.6 h) | 1.0 |
| official scoring jobs | 8 column jobs + the sealed delivered score | -- |

Every arm's `max_supplied_items` is at most the lock's 55 by construction: every candidate supplies at most 20
exemplars. `fit_estimate` must still be MEASURED by `native_contact_fit` at ceiling 9 (no placeholders; VAR-2 lesson).

### 6.3 Checklist (in order; each item model-free unless marked)

1. [ ] Worktree from WSL. First action: `git -C <master> status --porcelain`, which must be empty. No concurrent merge
   and flip; never `git add -A`.
2. [ ] **E-S1**: module `supply` column kind + `supply_frame` + `alternates` passthrough, as in 1.3.1.
   - Unit tests: compile byte-identity of the all-off block, the ceiling term, refusals next to template or branch
     columns, delivering arm last with no override, the twin carrying no release swap.
   - Gates: `engineering_base_check.py`, `stage3_effect_floor_check.py`, `flight_registration_check.py`,
     `finite_completion_policy_check.py`, `stage3_algorithm_label_check.py`.
   - Merging busts prepared-artifact identities, so re-pin at the coordinator's named point (loop-form
     `repin_cell.py`).
3. [ ] **E-S2**: reader v3-supply support and per-arm supply statistics, as in 1.3.2; fake-run tests; the v4g apply
   driver accepts supply columns.
4. [ ] **P1** (after the running flight seals). Re-run `scripts/analysis/slurp_nx_exchange_rates.py` for the review-off
   base on the R1 Fold B `lock` column, plus `v4g(lock)`, under a new analysis id (never inside a registered run
   dir). Outputs: the class x supply cube [B], false-fill rows, and the node rate on this base. The exchange note
   section 8 requires this before its rates are cited for another base.
5. [ ] **P2**: rank, repetition and intent split, counts only, from the Fold B `lock` sealed `supplied_value_ids` and
   the pool's metadata. For each E1 copied SPURIOUS pair and each E1-printed exact or MISSING item, record:
   - the rank of its printing exemplar(s);
   - the number of printing exemplars;
   - whether a printing exemplar's intent equals the delivered intent.

   This fills the `s1-k10` and `s1-icap5` predictions.
6. [ ] **P3**: offline re-retrieval of every arm at zero encoder contacts (pinned query and facet vectors, the
   registered ranker and fuser, as `analysis/fusion_form_offline_gate.py` does), on Fold B and A2. Per arm, record:
   - supplied items per row (max and mean, which feed the fit);
   - the exemplar entity-free share per row and the rows crossing 0.6 (the N1 signal);
   - newly printed and un-printed gold pairs by class.

   Replace the analogue predictions in section 2 by these counts x the measured conversions, and record both.
7. [ ] **P-N1**: build `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-n1-intent-v1/{snapshot,
   release}.json`.
   - Selection: keep every entity-free value; drop the slot-bearing values of each intent whose pool entity-free share
     is at least 0.6.
   - Parameters: θ = 0.6, and no other parameter.
   - Receipt (counts only): intents selected, values kept and dropped, and parent hashes.
   - Assert the subset of the parent and that the facet-vector file is a superset, then `--check` byte reproduction.
   - Profile `model-free-check`; a tool-contact ledger row.
8. [ ] Measure fit (`nx_r1_fit_measure.py`-style for ceiling 9). Then the registration writer: baseline, experiment and
   campaign fragments (+ smoke-4), protocol, generation and FIT plans, `registered-facts-v1.json`,
   `analysis-recipe-v1.json` (the three families of section 4), root-admission draft, preregistration with the
   section-2 predictions and the section-7 declaration.
9. [ ] Exposure-ledger DRAFT rows: arm, arm FIT, smoke, smoke FIT and READ. None is countersigned by the agent.
10. [ ] Offline proof: four-row dry run, in which the delivering arm's request is byte-identical to an unarmed run at
    ceiling 9 (I7) and each release-swap arm resolves exactly its alternate (I7v, receipt v3). Then
    `flight_registration_check.py --cell` for both cells and the five gates. Hand-off entry in both handoff files.
11. [ ] Coordinator only: decide the template line (section 3, after the i2 read), countersign, mint, flip and queue
    through the batch driver. One recovery at most; the FIT cap stays structural.

---

## 7. Decision 192 and what the owner would have to accept

The round's best measured-conversion prediction is **+0.20 pp**, against a floor of 1.49 and a bar of 1.5.
`stage3_effect_floor_check.py` refuses a benefit-claiming cell whose expected effect sits under its design's floor, and
decision 192 forbids registering an SLU mechanism below 1.5 pp predicted. Three honest options:

1. **Fly S1 as a measurement cell, `claims_benefit: false`.** The gate admits this form. It needs an explicit owner
   ruling that decision 192 does not block a cell that claims nothing.
   - Product: six same-flight, n = 1,080, measured supply conversions on the NX base. Today these are analogues from
     other bases (VAR-1 cross-flight on R01C, W-SV-1 on the review-on graph).
   - Cost: about 2.6 GPU-h and one read.
   - Consequence: no arm can be nominated from it. An arm that reads CI-LB > 0 anyway would need a fresh claiming cell,
     the Fold A two-arm confirmation.
   - It counts as one Stage S round under the plateau rule.
2. **Close Stage S at the Solver now, with no admissible candidate under decision 192,** and move to Stage J (R5).
   - Basis: k 30, k 10, the diversity cap, F10, W4, W5 and the score-threshold abstention are each null or closed
     (section 1.2).
   - The largest measured lever on the empty-gold mass is the template-level empty decision (R1 c3, false fill
     -15.82 pp). That lever belongs to Stage U and to v4g's `ee10`, not to supply.
3. **Open a code-level supply mechanism** (a per-row N1 "none" signal rendered into the supply, or new knob tails for
   `max_total_values` / `max_values_per_candidate`). This leaves the "no new code" envelope and needs its own
   decision-192 headroom read first. The on-file ceiling of the per-row N1 gate is oracle +0.55 / +0.13 at M1 on
   COMP-1b Fold A, which is also below the bar.

The analysis agent's reading, which is not a verdict: the on-file evidence points to option 2. Option 1 is the
cheapest way to replace six analogue numbers with measured ones if the owner wants the supply map recorded before
Stage J. The coordinator decides; this note registers nothing.

## 8. Sources

`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`;
`docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md`;
`docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md`;
`src/speech_aware_evidence_acquisition/rails/supply_variants.py` (docstring, `SUPPLY_VARIANT_KNOB_TAILS`,
`parse_supply_variant_knob`); `rails/consumption_module.py` (`parse_consumption_module_block`,
`verify_declared_module`); `rails/kb_policy.py::_fuse_supply_filter`; `rails/knowledge_build.py:1163`;
`rails/adapters/slurp_module_hooks.py`;
`configs/baseline/slurp-native-stage3-nx-r1-i2-solver-fold-b-baseline-v1.json`, `...-wsv1-fold-a-baseline-v1.json`,
`...-w4sv-fold-a-baseline-v1.json`, `...-var1-ex-div-r01c-baseline-v1.json`;
`docs/readiness/2026-10-09-slurp-nx-r1-i2-solver-fold-b-v1/README.md`;
`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`;
`docs/results/2026-10-09-slurp-nx-r1-solver-fold-b-column-read.md` (and
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1/node-local-v2/tables.md`, read-only);
`docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md`;
`docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md`;
`docs/results/2026-09-29-slurp-supply-abstention-headroom-offline.md`;
`docs/results/2026-09-30-slurp-s1-slu-error-taxonomy-refresh.md`;
`docs/results/2026-09-29-slurp-wsv1-fold-a-column-read.md`; `docs/results/2026-09-25-slurp-var1-complete-evidence.md`;
`docs/results/2026-09-29-slurp-sealed-credit-inner-loop-run-1.md`; `docs/results/2026-09-25-slurp-f10-complete-verdict.md`;
`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`; `scripts/checks/stage3_effect_floor_check.py`;
decision registry rows 190-192 and 199 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`).
