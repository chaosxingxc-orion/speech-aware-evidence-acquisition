# Same-flight instrument, phase 2: Perception-phase variants (design)

Author: design agent (Claude Opus 5.5), 2026-09-28, branch `fable/svphase2`. Status: DESIGN, no code. Extends
`docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md` (phase 1, rulings Q1-Q6,
release-swap amendment) and inherits every phase-1 rule it does not name. No model, server or GPU contact.

## 0. Why, and why phase 1 refuses it

The node ledger (`docs/results/2026-09-28-slurp-node-information-gain-ledger.md`, TRAIN Fold A, AGREE) finds
only two intent nodes with gain: Perception's re-ranking of the boundary block (+7.04 pp [+5.00, +9.07]) and
the delivery normaliser (+1.94 pp). The Solver adds +0.00 [-1.20, +1.20] and follows Perception's rank 1
(97.57 % correct at rank 1, 26.98 % at rank 2, 12.0 % at rank 3). Of 153 wrong rows, gold is at rank 2 on
42, rank 3 on 20, off the list on 83 (49 of them in the block). Intent mechanisms must change what
Perception sees or how it ranks, and cross-flight reads cannot resolve effects under about 2.5 pp.

Phase 1 refuses such a variant by name (`rails/supply_variants.py::parse_supply_variant_knob`):

> "supply-variant override {text!r} names the program's FIRST phase {first_phase_id!r}, whose selection is
> computed before the flight and seeded into each row's one initial QueryState; it cannot differ between two
> arms of the same row"

(This is refusal 7 in the current `parse_supply_variants` docstring, which is authoritative; an earlier draft of the phase-1 spec numbered it refusal 8.)
It exists for two reasons. **Mechanics:** phase-1 arms are resolved in `rails/runner.py::settle`
(2489-2522) against the preceding node's staged context and rendered over a view that swaps that node's own
acquired ids. The first phase has no preceding advance (`core/flight/runtime.py::_resolve_phase_supply`,
9316); its selection is a pre-flight seed (`_phase_supply_seeds`, 8244, or the prepared
`prepared_phase_supply`) handed to the runner as `bootstrap_value_ids` (runtime.py:6796), so there is no
per-arm selection to render. **Estimand:** a Perception variant changes the note Solver, Reviewer and
Planner all read, so a Solver-local column cannot carry it (Q1). `rank_weights` (holding `w_agree`),
`facet_source` and `query_source` are not knob tails either.

## 1. The object: an episode-level fork at Perception

Per row, K **Perception branches** over one audio packet: **A** delivers (last, override-free, the cell's
own request) and continues through Solver/Reviewer/Planner exactly as today; **T** (`replicate_of: "A"`)
repeats A's request byte for byte in the same batch; **B..** (at most 6) run Perception **only**, their
notes sealed as columns. Admitted axes, a closed set, one factor per non-A branch:

- *boundary supply knob:* `knowledge_stores.<store>.phase_supply.<first phase>.{k, fuse_coverage.m|c|top_l,
  rank_weights.w_cos|w_prior|w_agree}`;
- *release swap:* phase 1's `release_swap` over declared `alternates`;
- *presentation:* `presentation_id` from a new closed `core.base` registry `PERCEPTION_PRESENTATIONS`
  (`top2-contrast-v1`, `rank-visible-v1`);
- *response contract:* `min_candidates` of `slurp-intent-hypotheses-v1` (1..`max_candidates`).

Nothing else is addressable (model, decoding, geometry, task contract, program, tools; Perception holds none).

**Two levels** (the cell declares one):

- **Level 1, note only.** One Perception contact per non-A branch; the column is the note.
- **Level 2, note + one Solver contact.** At the Solver's first visit each non-A branch gets ONE Solver
  contact whose history carries that branch's note instead of A's, whose boundary ids are the branch's, and
  whose slot-contract `candidate_supply` (`candidate_state_phase: perception`) is re-resolved from the
  branch note; the speech-keyed `train-exemplars` supply is unchanged. The column is an answer the official
  scorer reads. A's column is A's own first Solver answer.

**Cost per row** (K counts A and T; audio is re-sent per contact; planning figure 2.86 speech-s per contact,
the wave A/A's 12,557.168 s / 4,393):

| level | extra contacts | extra audio | K = 3, 1,080 rows |
| --- | --- | --- | --- |
| 1 | K - 1 | (K - 1) x row audio | +2,160 contacts, about +6,180 s |
| 2 | 2 (K - 1) | 2 (K - 1) x row audio | +4,320 contacts, about +12,360 s |

GPU time is measured on the fit pass, never extrapolated (reference: 1.7417 GPU-h per 4,393 contacts).

## 2. What the column read measures

- **Level 1 (the ledger's metric).** Per branch: gold's rank in the note (1/2/3/absent), `top1`, `present`,
  list size. Gold enters only offline. Primary: paired per-row `top1` difference B - A; null T - A; bar
  |T - A| + its half-width (phase-1 law). `present` and mean rank are reported, never gating.
- **Level 2.** Each column goes through the delivered row's normaliser and projection and is scored once per
  complete column (`score_complete_derived_copy`). Primary official intent accuracy; guard SLU-F1;
  conversion P(correct | gold rank r in the branch note) against the ledger's 97.57 / 26.98 / 12.0 %.
- **Delivered guard.** Branches never change the delivered row: A's requests equal a branch-free flight's
  byte for byte, so delivered intent and SLU are identical by construction at the request level (responses
  are not bitwise guaranteed; greedy is not reproducible across slots). Reported, never contrasted.
- **Resampling** by row (`sample_id`), 10,000 draws (Q4); utterance level reported beside.
- **Claim ceiling** `nominated` (Q6). Level 1 nominates only into level 2; level 2 nominates the composed
  policy into a full-system cross-flight read against an in-chain A/A.
- **Sensitivity (estimate).** One row is 0.0926 pp. With about 20 T/A discordant rows the half-width is
  about 1.96 x sqrt(20) / 1080 = 0.81 pp; with 50-60 discordant B/A rows an effect near 1.2-1.5 pp is
  readable, below the cross-flight floor. The first read measures the real twin discordance.

## 3. Runtime contract

**Fork point: `rails/runner.py::_invoke_native_role_episode`, node loop 3750-3860.** Today its
`if/elif/else` (3829-3860) wraps only the Solver (`elif role.supply_variants is not None:` at 3843 builds
`SupplyVariantRoleNode`). Phase 2 adds `elif role.role_kind == "perception" and role.branches is not None:`
building `PerceptionBranchRoleNode` (`reproduction/ojw/native_supply_variants.py`), the structural twin: K
sequential `inner.invoke_direct(query)` calls, A last. The graph is unchanged (`native_episode.py:1670`
still adds one `perception` stage); `build_native_episode` validation (2043) admits the wrapper.

**Branch seeds.** At assembly, before any contact, `core/flight/runtime.py` builds one router per branch
with `_supply_action_router(program, branch_id, knobs, release_swap=...)` and computes its first-phase seed
through the same `bootstrap_first_phase` path `_phase_supply_seeds` uses. Each non-A, non-T branch pins its
seed as its own prepared artifact (`roles.perception.branches.arms[i].prepared_seed {relpath, sha256}`,
identity covering its axes and implementation hashes). A's seed is the cell's own `prepared_phase_supply`,
and A's independently built router must reproduce it on every row (phase 1's non-circular delivering-arm
check, moved to the seed). T takes A's seed. The `rank_weights.*` tail is admitted only on this branch route.

**Messages and settle.** `perception_branch_messages`, beside `supply_variant_messages` (runner.py:2263): A
and T take `base_messages(ctx)` unchanged; any other branch renders over a `QueryState` view whose
`retrieved_value_ids` are its seed, with its presentation and contract applied (rendering only: no
transition, wave, state or hash edge reads it). The K contacts form one `AgentContactBatch`
(`action_alternatives`) on the initial `query_state_sha256`; only A's completion registers the Perception
state, and a new assertion refuses downstream state bound to any other branch.

**Level 2.** The Solver's first visit fans out one contact per non-A branch, A last, reusing
`run_supply_variant_arms` with arms mapped one-to-one to branches and `arm_visits` forced `"first"`;
revisits contact A alone. Phase-1 Solver `supply_variants` are refused beside branches (one factor).

**Receipt** `saea-perception-branch-arms-v1` under `perception_branches`: `level`, `branch_visits:
"first"`, `visit_index: 0`; per branch `branch_id`, `deliver`, `replicate_of`, `resolved_knobs`,
`release_swap`, `presentation_id`, `min_candidates`, `supplied_value_ids` (rendered order), `supplied_count`,
`contact_id`, `request_sha256`, `response_text_sha256`, `note_sha256`, `note_parse_status`,
`candidate_intent_ids` (ordered: each candidate's rank); at level 2 also `solver_contact_id`,
`solver_request_sha256`, `solver_response_text_sha256`, `candidate_supply_value_ids`. The branch id reaches
the trace only through the role custody document, so T's wire bytes equal A's.

**I7v, Perception path** (`core/bundle/outputs.py::_verify_supply_variant_trace_binding`, same invariant
id): the Perception visit carries exactly K contacts in declared order, each bound to its trace pair; A's
`note_sha256` equals the sealed Perception state's hash; every later request history carries A's note hash
and no other; at level 2 the first Solver visit carries K contacts in branch order. Row identity still binds
to the final delivering Solver contact; I7 and I7n are unchanged.

**Budget.** Ceiling `base + (K - 1)` (level 1) or `base + 2 (K - 1)` (level 2): 13 or 15 for
`phase-native-candidates-review-revise-v1` (11) at K = 3, each its own program id
(`native_episode_config.py:1876` asserts equality). `planned_model_calls >= rows x ceiling`, audio likewise,
run-cumulative; `variant_cost.{extra_contacts_per_row, extra_audio_seconds}` checked against the branch
list and level.

**Fit gate.** The flown Perception envelope is 19,449 tokens in a 24,576-token slot. Every branch prompt,
presentation included, is measured on the cell's own `native_contact_fit` pass at the new ceiling; a branch
over the live slot minus the registered reserve is refused before any contact.

**Branch visits.** Perception has one visit per row here (`max_iterations` 1, no refresh); the fan-out is at
visit 0 only, and any `perception_refresh_*` stage contacts A alone. There is no `"every"`.

**Refused.** A non-A branch delivering or registering state; Reviewer/Planner seeing any non-A note, block
or answer; any merge or vote over branches (phase-1 section 6); branches beside `samples >= 2`,
`solver_group`, Solver `supply_variants`, `knowledge_value_rendering` (its arm-group refusal exists,
`native_episode_config.py:1878-1883`), `finite_supply_policy`, or an acquisition policy that re-enters
Perception; axes on A or T; two branches with identical axes.

## 4. Isolation

- **TRAIN only.** Seeds, swaps and presentations come from released, hash-pinned TRAIN-derived stores;
  agreement tables stay self-excluded by utterance identity, as in AGREE.
- **Rosters.** Branch values are chosen on a tuning roster; the nominating read uses a disjoint one. Fold A
  produced the ledger that motivates both first cells, so Fold A is their **tuning** roster and cannot
  nominate. Both rosters exclude every knowledge-source id (exemplar pool, card `source_support`, agreement
  pool, contrast-pair pool): the R01/R01C lesson.
- **A/A = twin** (Q3). The within-flight Perception null is unmeasured; the ledger's cross-flight P top-1
  difference, +0.28 [-0.56, +1.20], is context only.
- **Registration.** `measurement_design: "same-flight-perception-variant"` with `tuning_roster`,
  `read_roster`, `aa_arm_id`, `variant_cost`, `level`, `claim: "nominated"`; phase 1's gate findings plus
  `branch-level-missing` and `branch-seed-unpinned`. *(Coordinator note, 2026-09-28, merge set C
  implementation: this sentence originally spelled the design value `"same-flight-perception-branch"`.
  `scripts/checks/stage3_effect_floor_check.py` and `scripts/checks/flight_registration_check.py` register
  it as `"same-flight-perception-variant"`, and the P-SV-1/P-SV-2 packages already fly under that spelling
  on branch `fable/psv`; this section is amended to match rather than the other way around, so the spec and
  the gates name one value. Do not rename anything in the checks or their tests to match this document's
  earlier spelling.)*

## 5. Changes and merge set C

Identity-bound files **[IB]**: `core/flight/runtime.py`, `rails/kb_policy.py`, `rails/phase_supply.py`,
`rails/knowledge_stores.py`, `rails/knowledge_provider.py`. **`kb_policy.py` is not expected to change:**
`rank_weights` is already a per-spec field (`rails/phase_supply.py:549-617`), so a branch router is a
values-copy override; if that proves false the change is flagged and joins this set. Set C lands at a
coordinator-named re-pin point with a loop-form `repin_cell.py` pass. Order:

1. *Read side and gates (not IB).* `stage3_effect_floor_check.py` and `flight_registration_check.py`
   (design value, fields, findings); `scripts/analysis/slurp_perception_branch_read.py` (level 1; imports
   the ledger driver's functions unchanged and refuses unless branch A reproduces the ledger's P-node
   counts); `stage3_rollout_score.py` (level-2 columns); `stage3_paired_read.py` (`column` = branch id,
   same-parent refusal, `nominated` ceiling).
2. *Parser and receipt.* `rails/supply_variants.py` (one base: `PerceptionBranchGroup`,
   `parse_perception_branches`, schema); `rails/native_episode_receipt.py` (validator).
3. *Config.* `rails/native_episode_config.py`: `roles.perception.branches`, refusals, ceiling term.
4. *Runtime [IB].* `core/flight/runtime.py`: branch routers and seeds, live A-seed check, branch-route
   `rank_weights` tail, `sources["perception_branches"]` in `_phase_seed_inputs`.
5. *Runner and nodes.* `rails/runner.py` (messages, settle, assertion, level-2 fan-out);
   `reproduction/ojw/native_supply_variants.py` (`PerceptionBranchRoleNode`);
   `reproduction/ojw/native_episode.py` (validation).
6. *Presentations.* `PERCEPTION_PRESENTATIONS` in `core/base.py`; `rank-visible-v1` wraps
   `rank_visible_value_renderer` (runner.py:1426); `top2-contrast-v1` renders one block for the branch's
   rank-1/rank-2 pair from a pinned contrast-pair table built model-free by
   `scripts/build_slurp_intent_contrast_pairs.py` (W3a's word-gap method, R01-excluded TRAIN pool, receipt).
7. *Bundle.* `core/bundle/outputs.py`: the I7v Perception path.
8. *Fragments.* `configs/policy/phase-native-candidates-review-revise-pbranch3-l1-v1.json` (13) and
   `-pbranch3-l2-v1` (15), registered in `rails/controllers.py`; existing configs byte-identical.

Acceptance tests (unit, fake core): **AT-P1** A's Perception request equals the branch-free request;
**AT-P2** T's wire bytes equal A's; **AT-P3** mutating any non-A note leaves every Reviewer, Planner and
A-Solver request byte-identical; **AT-P4** ceiling and budget at both levels; **AT-P5** a fake sealed run
passes `verify_bundle`, column render, stub scoring and the column paired read; **AT-P6** A's router
reproduces the prepared seed and a tampered seed is refused; **AT-P7** A's level-2 column equals the sealed
first Solver visit after the normaliser; **AT-P8** a column package never emits `admitted`.

Gates after each step: `pytest`, `engineering_base_check.py`, `stage3_effect_floor_check.py`,
`flight_registration_check.py`, `stage3_algorithm_label_check.py`, `finite_completion_policy_check.py`.
Then (coordinator) dry run, fit pass at the new ceiling, four-row smoke.

## 6. First cells

**P-SV-1: agreement term vs top-2 contrast** (level 2, K = 3, ceiling 15). A = the AGREE Perception supply
as flown (`w_agree` 1.0, `k` 60, m/c/top_l 8/1/8); B = same ids plus `top2-contrast-v1`; T = twin.
Target: rows with gold at Perception rank 2, 63 overall (5.83 pp level-1 `top1` ceiling), 42 of them
delivered wrong (3.89 pp delivered-intent ceiling). Risk: the 907 rank-1 rows; the B->P edge already
worsened 29, and W3a (contrast lines on every card) read -0.56 [-1.67, +0.56] cross-flight. P-SV-1 tests
the narrower pair-only form; it needs about 15 net promotions (about a third of the 42) to clear an
estimated 1.2-1.5 pp bar. An optional branch C (`w_agree` 0.0, K = 4) reads the agreement term itself.

**P-SV-2: rank order vs wider shortlist** (level 1, K = 3, ceiling 13). A = today's block, which is
**already rank-ordered** (rendered order equals the ranker order on 1080/1080 rows, ledger section 0) but
shows no rank numbers (`knowledge_value_rendering` is not armed in AGREE); B = `min_candidates: 3`; T = twin.
B changes only the 270 rows with lists of one (35) or two (235). The presence ceiling is the 49 wrong rows
with gold in the block but off the list (4.54 pp); at the 12.0 % rank-3 conversion the delivered-intent
ceiling is about 6 rows (about 0.5 pp), below sensitivity. P-SV-2 is a presence and conversion measurement
with `present` as its declared primary, not an intent claim. An optional branch C (`rank-visible-v1`) adds
rank numerals.

## 7. Open questions

- **O1.** May a level-1 `top1` effect nominate straight into the full-system read? Default: level 2 first.
- **O2.** No held-out TRAIN roster has an agreement table and speech query vectors (the agreement artifact
  is Fold A only). Is Fold B the read roster, with its artifacts minted first?
- **O3.** Presentation and response-contract axes change request text and grammar, not supply. Are they
  instrument axes through a closed registry, or cross-flight only?
- **O4.** Should P-SV-2 declare `present` as primary (proposed), since intent is out of reach by
  construction?
- **O5.** When a pair has too few pool utterances, should `top2-contrast-v1` render nothing (proposed,
  receipted) or fall back to the W3a card line?
- **O6.** If twin discordance is large (about 20 rows or more), is a second twin worth one more contact per
  row?

## 8. Coordinator rulings (Fable 5.1, 2026-09-28)

- **O1.** A level-1 result nominates only into a level-2 read of the same candidate pair; only a
  level-2 result (the branch Solver conversion, section 2) nominates the composed policy for the
  full-system cross-flight read against an in-chain A/A. Section 2's claim-ceiling sentence already
  assumed this ordering; it is now the ruling, not a default. P-SV-2 (level 1) cannot itself clear the
  full-system gate: a level-1 `top1` or `present` gain that survives resampling reopens a level-2 cell
  on the same pair before any nomination beyond it.

- **O2.** The read roster for the first phase-2 cells is TRAIN **Fold B**; Fold A produced the node
  ledger that shaped both first cells and stays their **tuning** roster (section 4, unchanged). Fold B
  carries neither an agreement table nor speech-query vector files today, so section 4's open question
  is resolved this way, not by reading Fold A twice. Both artifacts are minted **model-free** wherever
  the underlying vectors are already released (the same embedding/index bytes AGREE consumes, re-keyed
  to Fold B's utterance ids); only a residual that needs a fresh encode is a registered tool contact
  (logged in `docs/exposure-ledger.md` before its result is read), and that contact runs **inside** a
  long flight window already open for another purpose -- never as a standalone sidecar while serving
  must restart (memory: serving session death, 2026-09-18). Minting Fold B's artifacts is a
  precondition of `read_roster` for both first cells, not a parallel or optional task.

- **O3.** Yes. `presentation_id` (`PERCEPTION_PRESENTATIONS`) and the response-contract's
  `min_candidates` are instrument axes through the two closed registries section 1 already names,
  exactly like a boundary-supply knob or a release swap. Section 1's axis list is confirmative, not
  exploratory: no cell may vary rendering or response format outside those two closed registries, and
  no cell may treat them as cross-flight-only.

- **O4.** Confirmed. P-SV-2 declares `present` (gold-on-list) as its `stage3_measurement` primary
  metric; official intent accuracy is reported beside it, never gating, per section 6's framing.
  `claim` stays `"nominated"` at both levels (phase 1, Q6).

- **O5.** No fallback. When a candidate pair's pool support is under the registered floor,
  `top2-contrast-v1` renders nothing for that row -- the branch's note carries no contrast block, and
  `min_candidates` still applies to whatever the boundary supply itself returns. It never falls back to
  W3a's closed contrast-card line (which read -0.56 [-1.67, +0.56] cross-flight and is not reopened by
  this instrument). The renderer receipts which rows rendered nothing and why
  (`presentation_skip_reason: "insufficient-pool-support"`).

- **O6.** No second twin. One A/A per row is the within-flight null at both levels; a second twin would
  add a contact per row to re-measure discordance the first twin already measures. Phase 1's Q3 ruling
  (one twin per same-flight read) extends here unchanged.

- **O7.** The nearest-rival contrast-pair table (one pair per intent, its single nearest rival by
  centroid cosine) covered only 415 of P-SV-1's 1,078 `b-top2contrast` rows (38.5%; `scripts/analysis/
  slurp_contrast_pair_coverage.py`), because the branch renders a block only when a row's OWN
  rank-1/rank-2 candidate pair is a key in the table, and 662 rows named a pair the nearest-rival
  selection never built. The table is now every unordered pair of distinct SLURP intents whose pool
  support meets the registered floor (`min_pair_pool_support` 5, unchanged), built by the SAME
  word-gap method over the SAME R01-excluded, Fold-A- and Fold-B-excluded TRAIN pool, roster-agnostic:
  pairs are never selected from any roster's seeds, only from the full released intent set. O5 stands
  unchanged -- a pair under the floor still renders nothing, and the runtime receipt still reports
  `presentation_skip_reason` per row. Coverage against the same P-SV-1 seed rises to 1,035 of 1,078
  rows (96.0%); the residual 42 rows land on the 2 pairs the floor still skips
  (`cooking_query`/`cooking_recipe`, `iot_hue_lightoff`/`iot_hue_lighton`) -- the identical 2 of 60
  pairs the nearest-rival table also skipped for insufficient pool support.

## 9. Seal-time validation lesson (coordinator, 2026-09-29)

**What happened.** P-SV-1 flew all 1,080 rows (8,709 calls) and aborted at seal (I7v): the runner sealed each
branch note's intent list verbatim, and 61 notes over 49 rows listed one intent twice (a-agree 21,
b-top2contrast 17, t-twin 23; no empty or malformed note). The validator required distinct ids. Receipt schema
`saea-perception-branch-arms-v2` now records a degenerate list as a measured outcome: `candidate_intent_ids`
keeps the parsed order with duplicates collapsed (first occurrence), `candidate_intent_ids_raw_count` records
the listed count, and `note_parse_status` is one of `ok` / `duplicates-collapsed` / `empty` / `malformed` (the
last two carry an empty list; the `("unparsed",)` sentinel is retired). `min_candidates_met` is computed on the
collapsed list, so a padded `[x, x, y]` does not meet a bound of 3. Section 2's `present` metric (ruling O4)
reads `empty` and `malformed` as gold-absent. v1 receipts keep their original rule. The same investigation
found that the level-2 fold dropped each branch's presentation outcome (every P-SV-1 `b-top2contrast` row sealed
None/None, which contradicts ruling O5's per-row `presentation_skip_reason`). It would also have refused every
row of a level-2 `min_candidates` branch (P-SV-2 `b-list3`). Both are fixed, and a seal-only replay rebuilds
the whole block from the trace.

**The pattern.** This is the third whole-run abort at seal in one day caused by a rare row class hitting a
validator that only the seal ran: COMP-1 (citation ids), E4-1 (a finite delivery followed by relisten
contacts), and P-SV-1 (a repeated intent). Each time, every row had flown and the delivered answers were sound,
but one row class discarded the whole run until a seal-only recovery.

**Proposal (not implemented here).**

1. *Per-row receipt validation at row completion.* Run the row-level receipt validators (I7, I7n, I7v, I7l,
   I7g and the delivery receipt) as soon as each row seals its episode receipt, not only in `verify_bundle`.
2. *Per-row quarantine instead of a whole-run abort.* A row that fails gets `row_status: "receipt-invalid"`
   and a reason class. Its delivered answer and custody are kept, and it is excluded from every column read.
   Each read reports the quarantined count per class beside its n. The seal still fails closed on
   run-level invariants (roster, manifest, trace hash, duplicate rows) and when quarantined rows exceed a
   registered ceiling (proposed: 1% of the roster), so a systematic defect still stops the flight.
3. *Smoke rosters by class, not by count.* A four-row smoke proves only the classes it happens to draw.
   Before a smoke is accepted, its roster must include at least one row of each delivery kind (accepted
   first visit, revisit, finite-completion, abstention) and each branch outcome class the receipt can
   record (`ok`, `duplicates-collapsed`, `empty`, `malformed`, a rendered presentation block, and each skip
   reason). Classes the model does not produce on real rows are covered by a fake-transport live test
   instead (as `tests/unit/test_perception_branch_degenerate_lists.py` now does).
