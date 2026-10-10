# One consumption module for the SLURP composed policy (design)

Author: design agent (Claude Opus 5.5) for the root coordinator (Fable 5.1), 2026-09-29. Docs only, model-free: no
code, no flight, no registration, no admission. Every number is a development number (owner decisions 28, 86) quoted
from the file named beside it.

**Owner directive (2026-09-29, translated from the owner's Chinese; the verbatim text is in the coordinator's brief and
is to be recorded in the decision registry as row 195's ruling):** "Decision 195: agreed [option B: the do-not-tag scope
rule enters the COMP-2 composed policy as a USE-layer deterministic node action, read only inside the composed arm's
DEV read]. I want you to finally unify these assembled components into ONE module (note: the module may call the model)
that carries them."

**Owner requirement added the same day (translated):** "Once the training-free RL achieves stable gains on SLURP, it
must transfer and extend to Audio2Tool, E21 (Earnings-21) and E22 (Earnings-22)." Section 2b answers it.

**Proposed id.** `saea-evidence-consumption-module-v1`, not `slurp-consumption-module-v1`. Every registered component
id in this study is `saea-<plane/role>-<name>-v<N>` and carrier-neutral where the mechanism is carrier-neutral
(`saea-obs-targeted-relisten-v1`, `rails/relisten.py:114`; `saea-deliver-normalise-v3`,
`rails/delivery_normalisers.py:69`; `saea-solver-cited-answer-v1`, `rails/solver_citation.py:63`). The carrier enters
as a `profile` (section 2b), never in the id. The file name of this note keeps the brief's wording. Paths below are
relative to `src/speech_aware_evidence_acquisition/` for code and to the repository root otherwise.

**Coordinator rulings.** The root coordinator's (Fable 5.1) answers to section 5's open questions, and its
acceptance of the proposed id and migration sequencing, are recorded in `## Coordinator rulings (Fable 5.1,
2026-09-29)` below section 5.

## 0. The problem in one paragraph

The SLURP policy that COMP-2 (owner decision 138) is meant to compose is spread today over config fragments
(`knowledge_stores.*.phase_supply`, `native_episode.*` blocks, `phase_material` templates), one phase-program file per
contact ceiling (`rails/controllers.py:1401-1741`: `-cited-v1`, `-pbranch3-l2-v1`, `-relisten-v1`, each "a separate
program id, never a flag on the base program", `:1712-1741`), same-flight branch blocks whose delivering branch may
carry no axis at all (`rails/supply_variants.py:1312-1314`, refusal 6), a shadow-only post-delivery stage
(`rails/relisten.py:223`, `:385-386`), and an offline edit that exists only as an analysis script
(`scripts/analysis/slurp_slu_consumption_headroom.py`). No single object answers "what is the policy", no single
switch turns a component off, and no current seam can put an admitted Perception presentation on the delivered path.

## 1. Component inventory

Status words: ADMITTED / NEUTRAL / RETIRED / HARMFUL are `docs/receipts/harness-admission.json` statuses; "retained",
"nominated", "flying", "held", "closed" are decision-registry dispositions
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, "registry" below). Layer: **L** = in the v2.0
lock (the base every composed read is compared against, decision 169); **C** = a post-lock COMP-2 candidate.

| # | component | where it lives today | status | layer, plane, node | model contacts | measured or declared effect (source) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | v2.0 lock base ("PLAN" = the default plan flown as one arm) | `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`; program `configs/policy/phase-native-candidates-review-revise-v1.json` (`max_contacts` 11) | LOCKED (`docs/results/2026-09-22-slurp-v2-lock-v1.md`) | L, all planes; Perception -> Solver -> Reviewer -> Planner -> deliver | the program's own, ceiling 11 | SLU-F1 63.6304, intent 82.2222; PLANr 63.8048 / 82.50 (same record, section 1) |
| 2 | M1 speech-keyed exemplar supply (cell B1) | `knowledge_stores.train-exemplars` (`phase_supply.solver`, k 20) in the default plan `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json` | ADMITTED, replication MET (harness receipt) | L, SUPPLY -> Solver | none (sealed speech-query vectors) | +12.61 pp SLU vs the anchor; vs the derangement twin +7.83 [+5.85, ...] (`docs/results/2026-09-18-slurp-b1-twin-verdict.md`) |
| 3 | M4b slot store v2 (cell B4b) | `knowledge_stores.slot-contracts` re-pin (release/snapshot v2) | ADMITTED, replication MET (harness receipt, `stores` re-pin form) | L, ORG -> Solver candidate supply | none | SLU +2.55 pp, CI95 LB +1.13 (`docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md`) |
| 4 | delivered-row normaliser M3 `saea-deliver-normalise-v3` (COMP-1 uses its cited twin `saea-deliver-cited-answer-normalise-v3-v1`) | `native_episode.deliver_normaliser`; `rails/delivery_normalisers.py:90`, `:401-411`; applied at `rails/runner.py:5483-5500` | ADMITTED (harness receipt) | L, USE, deliver node | none | +1.53 pp SLU on B1 (`docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md`); ledger: intent +1.94 [+1.20, +2.78], SLU +1.22 [+0.80, +1.66] (`docs/results/2026-09-28-slurp-node-information-gain-ledger.md:242`, `:246`) |
| 5 | review loop (Reviewer x3 + Planner + at most one revision) | `native_episode.review_loop` "on"; the four-phase program | NEUTRAL (harness receipt); REV-TFRL-1 NOT ADMITTED, B5 deferred (decision 188) | L, USE; Reviewer, Planner | up to 5 of the 11 | nets -1 / +1 rows; SLU -0.19 [-1.30, +0.93] after R (ledger `:43`, `:70`) |
| 6 | Reviewer task-contract toolkit withdrawn | `phase_tools` absent in the default plan | RETIRED (harness receipt; the plan carries the OFF arm) | L, Reviewer | reduces contacts | -69 % prefilled tokens per row, 0.418x GPU-h (harness receipt default-plan entry) |
| 7 | AGREE: exemplar-vote agreement in the Perception boundary rank (`w_agree` 1.0, k 60, fuse 8-1-8) | `knowledge_stores.intent-boundaries.phase_supply.perception.{rank_weights.w_agree, k, agreement_source}` in `configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json` | retained as COMP-1's first component, PENDING REPLICATION (decision 161; A2, decision 169) | C, SUPPLY -> Perception first-phase seed | none at flight (agreement table from sealed recalls) | intent +3.33 [+1.57, +5.09], SLU +1.85 [+0.23, +3.47] vs in-chain A/A (decision 161) |
| 8 | centroid boundary key | `...perception.facet_source` = `SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1` in `configs/baseline/slurp-native-stage3-comp1-fold-a-baseline-v1.json` | in COMP-1 (decision 152) | C, ORG -> Perception seed | none | part of COMP-1's declared 3.23 (re-plan v3, R2) |
| 9 | Solver citation contract `saea-solver-cited-answer-v1` | `phase_material.solver.{instruction_template, response_format_id}`, program `-cited-v1`, cited normaliser | COMP-1 no-harm item (decision 152) | C, USE, Solver response contract | none (+134 instruction tokens per Solver contact, decision 152) | no gain claimed; its credit table is the inner loop's reward signal (decision 152) |
| 10 | G5 Reviewer instruction repair | `phase_material.reviewer.instruction_template` = `..._g5_v1.txt` (`configs/baseline/slurp-native-stage3-g5-fold-a-baseline-v1.json`) | queued behind P-SV with COMP-1 seal-only (decisions 153, 189) | C, Reviewer | none extra | no-harm item; unread |
| 11 | P-SV-1 top-2 contrast presentation `top2-contrast-v1` | branch `b-top2contrast` in `configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1.json`; `rails/perception_presentations.py:89`, `:142`; pair table v2 (ruling O7) | FLYING (decision 193) | C, SUPPLY presentation -> Perception | as a level-2 branch +2 per row; on the delivered path 0 extra | ceiling 3.89 pp from 42 rank-2 rows (decision 184); unread |
| 12 | P-SV-2 forced three-candidate list (`min_candidates` 3) | branch `b-list3` in `configs/baseline/slurp-native-stage3-psv2-fold-b-baseline-v1.json` | FLYING (decision 193) | C, Perception response contract | as a branch +2 per row; delivered 0 extra | primary `present` (gold-on-list), ruling O4; unread |
| 13 | rank-visible presentation `rank-visible-v1` | `rails/perception_presentations.py:74`, `:141` | probe DESCRIPTIVE, treated as INERT: m = 19 of 119 vs a no-op 15.9 (`docs/results/2026-09-29-slurp-rankvis-probe-fold-a-119-read.md`) | not a component | -- | -- |
| 14 | E4-1 core-native targeted re-listen: replace-only and replace + drop-when-unheard columns | `native_episode.relisten` (`configs/baseline/slurp-native-stage3-relisten-fold-a-baseline-v1.json`), policy `saea-obs-targeted-relisten-v1` (`rails/relisten.py:114`, `:342`), stage `rails/runner.py:4401`, called at `:5517` | flew 1,080 rows, aborted at the seal; seal-only completion GO (decision 194), flip refused on the parent-config residue (re-plan v3, R3) | C, OBS post-delivery verification (shadow) | blind + confirm per entity, at most 3 entities: +6 to the ceiling (`rails/relisten.py:209-219`, `:470`) | declared 0.0, claim `nominated` (E4 spec section 8 item 7); gates: replace-only >= 29 % net of 106 items, drop >= 49.5 net false positives (decision 194) |
| 15 | do-not-tag scope rule (drop a delivered entity whose phrase occurs in >= 5 pool exemplars and is untagged in >= 80 % of them) | offline only: `scripts/analysis/slurp_slu_consumption_headroom.py` | decision 195 = B by the owner's directive above: a USE-layer deterministic node action inside COMP-2, read only inside the composed arm's DEV read | C, USE, deliver node | none | +1.04 [+0.53, +1.57] pp SLU, replicate +0.93 [+0.46, +1.42] (`docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md:94`) |
| 16 | E3 progressive slot loading (slot-types node, then full cards for chosen types) | `docs/superpowers/specs/2026-09-28-e3-progressive-slot-loading-design.md` only | designed, not built (re-plan v3, R9) | C, ORG/USE; new `slot-types` node before the Solver | +1 (ceiling 12, E3 spec section 3) | none measured |
| 17 | finite-completion / ReAct-exhaustion declarations | `native_episode.finite_completion_policy`, `react_exhaustion_policy` | NEUTRAL (harness receipt), mandatory (`scripts/checks/finite_completion_policy_check.py`) | L, harness | none | never fired (harness receipt) |
| 18 | dispatcher slot fill | `rails/dispatch_slot_fill.py` | PENDING, request-bytes-identical run-level module (harness receipt) | scheduling, not a component | none | throughput only |
| 19 | supply abstention (decision 199): `supply_abstain: {rule, threshold, pinned table}` per supply node; empty supply and empty entity list are valid (section 2c) | this design only | designed, offline analysis pending (branch fable/emptysupply) | C, SUPPLY/USE; every supply node the module owns, plus the Solver "no entities" option | none | none measured; B4 offline net -0.19 re-examined under it |

Closed or barred, never components: W-SV-1 (inert), W4 / W4-SV and every slot-convention card (decision 191), W5
(decision 192), W3a contrast cards (phase-2 spec ruling O5), and the HARMFUL modules of the harness receipt (silence
tail, logprob judge, NCP L1, B4a fallback, constant tool schema, knowledge index). NEUTRAL-not-in-plan modules
(grouped Solver sampling M2, Reviewer audit, Reviewer primitives) stay out unless a later decided entry moves them.

## 2. Module contract

### 2.1 Where it lives and what it may not be

- One class, `EvidenceConsumptionModule`, in a new file `rails/consumption_module.py`, registered into a new closed
  `core.base` registry `CONSUMPTION_MODULES` (same shape as `PERCEPTION_PRESENTATIONS`, `core/base.py:783-794`, checked
  at registration). The file joins `CANONICAL_REGISTRY_FILES` (`scripts/checks/engineering_base_check.py:79`).
- It is **not** a controller: it defines neither `initial_contact` nor `advance`, which is what the ratchet rule
  detects (`engineering_base_check.py:547-560`). It is **not** a `TaskAdapter` subclass (`:532-545`). No file under
  `rails/probes/` (`:519-529`).
- It never talks to the core itself. Every contact goes through the existing path: `FlightRuntime._dispatch_phase_program`
  (`core/flight/runtime.py:7108`) builds a `NativeEpisodeRunBinding` (`rails/native_episode_config.py:847`) that
  `_invoke_native_role_episode` (`rails/runner.py:2266`) runs on the OpenJiuwen ReActAgent path (`runner.py:2277`,
  `runtime.py:7640`), with the shared `EvidenceAgentController` (`rails/controllers.py:640`) walking the phase program.
  Post-delivery contacts use the existing metered sibling `_dispatch_relisten_contact` (`runner.py:4285`): same ceiling
  check, same `FrozenCoreClient` budget, own trace buffer. **Same harness for every arm** holds because the module is a
  policy that the one harness executes; it adds no execution path.

### 2.2 What the module owns

The module is a **policy compiler plus four node hooks**. At config load it compiles its `components` list into the
blocks the runtime already consumes; at run time it supplies the few decisions no block can express today.

| part | owns | compiles to / hooks into (existing seam) | new seam needed |
| --- | --- | --- | --- |
| (a) Perception evidence policy | supply seed (boundary k, `rank_weights`, `agreement_source`, `facet_source`), presentation (`PERCEPTION_PRESENTATIONS` id + pinned table), response contract (`min_candidates`) | `knowledge_stores.intent-boundaries.phase_supply.perception` -> `_phase_supply_seeds` (`runtime.py:9079`); presentations via `rails/perception_presentations.py` | **delivered-path presentation and contract.** Today only a B branch may carry `presentation_id` / `min_candidates`; A carries none (`supply_variants.py:1312-1314`). The module becomes the one place that sets them for the delivering path; A stays "the cell's own request", which now includes the module's admitted Perception policy. |
| (b) Solver consumption policy | candidate supply (`candidate_state_phase: perception`), slot views (slot-contracts store pins), exemplar supply (train-exemplars), response contract (citation), E3 staging when built | `knowledge_stores.{slot-contracts,train-exemplars}`, `phase_material.solver`, program choice | E3's `slot-types` role (E3 spec section 3); nothing else |
| (c) post-delivery verification | relisten targeting, contacts, acceptance, delivery mode | `native_episode.relisten` -> `run_relisten_stage` (`runner.py:4401`, `:5517`) | a `delivery: live` mode beside `shadow` (`relisten.py:223`, `:385`), armed only after E4-1's column read nominates (E4 spec section 4: "Promotion means binding in delivery") |
| (d) deterministic USE steps | delivered-row normaliser; scope rule | `native_episode.deliver_normaliser` -> `DELIVERY_NORMALISERS` (`core/base.py:727`) | the scope rule as a registered delivery-normaliser **stage** with a pinned pool-statistics table (the cited normaliser already chains stages, `delivery_normalisers.py:353-398`) |

Order inside the episode is fixed and declared: Perception (a) -> Solver (b) -> Reviewer/Planner (as the lock) ->
deliver normaliser -> scope stage (d) -> relisten (c) -> seal. The scope stage runs before relisten so relisten targets
only entities that survive delivery, matching E4's rule that it reads "the normalised values that would be scored"
(E4 spec section 1).

### 2.3 Inputs

1. The row's sealed speech packet (the packet the flight already binds; no transcript state, owner direction
   2026-09-06).
2. Knowledge stores by pin only: `intent-boundaries` (release, facets, agreement table), `slot-contracts` v2,
   `train-exemplars`, the contrast-pair table v2, and the scope-rule table (new: phrase -> pool count, untagged share,
   built model-free from the same TRAIN pool that excludes every read roster; decision 186's rule applies: a table built
   from Fold B rollouts is never read on Fold B).
3. One config block, `native_episode.consumption_module` (section 3.1).

### 2.4 Model contacts it may make

Only these, all through the paths in 2.1, all counted into the program ceiling and the plan budget:

| contact | node | per row | switch |
| --- | --- | --- | --- |
| Perception (delivered) | Perception | 1 (as today) | always |
| Perception branch columns | Perception | +1 per non-A branch (level 1), +2 at level 2 (`supply_variants.py:1178`) | `columns` |
| Solver, Reviewer, Planner, revision | as the lock | as today (ceiling 11) | lock layer |
| slot-types | new E3 node | +1 | E3 component |
| relisten blind / confirm | OBS | <= 2 x `max_slots_per_row` (3) | relisten component |

No second answering model, no tool-level verifier (the Whisper comparison needs its own owner row, decision 180).

### 2.5 Receipts

One receipt per node action, reusing the schemas that exist:

- Perception branches: `saea-perception-branch-arms-v1` (`rails/native_episode_receipt.py:1555`);
- supply variants: `saea-supply-variant-arms-v3` (`:1236`);
- citations: `saea-solver-citations-v1` (`rails/solver_citation.py:67`);
- deliver normaliser: `saea-deliver-normaliser-v1` (`rails/delivery_normalisers.py:64`), whose `stages` list gains the
  scope stage's sub-receipt (rule id, table sha256, dropped entity indices, input/output sha256);
- relisten: `saea-relisten-v1` (`rails/relisten.py:117`), gaining `delivery` (`shadow` | `live`).

One new header receipt per row, `saea-consumption-module-v1`: module id and version, profile, the compiled
component list with each entry's admitting record and state, the config-block sha256, and the list of node-action
receipt pointers above. It carries no content of its own, so replay (`core/flight/resume.py`) re-derives it from the
node receipts.

### 2.6 Identity

- The module's config block is inside the composed config and therefore inside `config_sha256`; like the branch block
  (`runtime.py:379-411`), it is also bound explicitly into prepared-artifact identity as a `consumption_module` axis.
- Implementation hashes: `rails/consumption_module.py` and each component implementation file it resolves join the
  `implementation` map beside `kb_policy`, `knowledge_provider`, `phase_supply` and `runtime` (`runtime.py:8360-8366`).
- **The branch-seed lesson applies to every pin the module writes:** a `prepared_seed`-style pin is the receipt of an
  artifact prepared FROM the identity, never an input to it, and is excluded exactly as
  `without_branch_seed_receipts` excludes it (`runtime.py:398-404`); binding it made the identity circular (2026-09-29
  P-SV-1 smoke re-pin, same docstring). This covers prepared seeds, the scope-rule table's own output receipt and any
  compiled-block cache.

## 2b. Carrier independence

### 2b.1 Split

**Carrier-agnostic (the module):** the node policy -- the Perception evidence policy (supply seed, presentation,
response contract), the Solver consumption policy, post-delivery verification by core-native re-listen, deterministic
USE steps -- plus receipts (2.5), identity (2.6), composition and columns (section 3), and the tuning/read machinery it
is read with: the sealed-credit inner loop (`SEALED_CREDIT_SYSTEM_POLICY_V1`, `core/stage3_algorithms.py:310`) and the
same-flight instrument (`rails/supply_variants.py`, branches and supply variants).

**Carrier-specific (existing extension points only, CLAUDE.md "one base, thin derivations"):** the `data.carriers`
descriptor (`data/carriers.py:358`, `:407`, `:453`, `:482`), one `rails/adapters/` TaskAdapter per carrier
(registrations `rails/adapters/slurp_runtime.py:226`, `audio2tool_runtime.py:260`, `earnings_runtime.py:180`), the scorer
registration (`core/scorers.py:230` `a2t-toolcall`, `:500` `entity-wer`, `:766` `slurp-slu-official`, `:1056`
`asr-wer-whisper`), knowledge stores and views, and config fragments. The module reaches carrier facts only through
adapter hooks: the existing `candidate_inventory` / `candidate_contract_provider` / `extract_consumption`
(`rails/task_adapter.py:246-292`) plus four new, defaulted hooks -- `decision_candidates(rendered supply)` (the
decision-unit ids a presentation contrasts), `max_decision_candidates()`, `delivered_units(text)` (the units relisten
and the scope stage address) and `default_deliver_normaliser()`. A default of `None` means "component has no analogue
on this carrier", and the module refuses to arm such a component there.

### 2b.2 Mapping table

| component | SLURP form | Audio2Tool form (tool = intent analogue, parameters = slot analogue) | Earnings-21 / -22 form |
| --- | --- | --- | --- |
| decision-node supply seed (AGREE, centroid key) | intent-boundary seed with exemplar vote | tool shortlist; A-C1 do-no-harm candidate formation, A-C1b goal-to-function recall (`docs/results/2026-09-27-a2t-earnings-gap-diagnosis.md:214-215`); the vote needs the A2T exemplar store (decision 157, not built) | **no analogue** (transcription has no closed decision label) |
| exemplar supply (M1) | train-exemplars k 20 | the A2T exemplar store (decision 157), not built | E-C2 speech-keyed entity retrieval from the full context (gap diagnosis `:364`), not flown |
| slot/argument knowledge (M4b) | slot-contracts v2 | tool/parameter cards; A-C3 value grounding (`:217`) | ConEC roster + brief (KC-E1f's supply) |
| presentation (top-2 contrast) | `top2-contrast-v1` | A-C2 twin-discriminating selection, 234 near-name twins (`:216`); ORG-1's grouping was HARMFUL, -3.225 pp (`docs/results/2026-09-27-a2t-org-1-reread-against-h-a2t.md`) | **no analogue** |
| response contract (forced-k) | `min_candidates` 3 | shortlist size of the tool proposal | **no analogue** |
| Solver consumption / USE repair | citation contract; E3 | A-C4 argument omission / default semantics (`:218`) | E-C1 roster-grounded entity repair (KC-E1f), ADMITTED and REPLICATED, PERSON +3.634 [+2.590, +4.690] (`docs/readiness/2026-09-08-e21-kc-e1f-replication-v1-verdict.md:95`) |
| post-delivery re-listen | E4-1 per delivered entity | parameter-value re-listen for hearing-origin value errors inside A-C3 (no measured share yet) | E-C3 targeted numeric re-listen (gap diagnosis `:365`) |
| deterministic scope / convention step | do-not-tag scope rule | an argument-omission rule would need its own offline read (A-C4); none today | E-C4 numeric format convention (`:366`), small |
| delivered-row normaliser | `saea-deliver-normalise-v3` | **none registered** (`rails/delivery_normalisers.py:401-411`) | `saea-deliver-earnings-text-v1` (same lines) |
| Reviewer / Planner | NEUTRAL loop | the same program family (`configs/policy/phase-audio2tool-native-candidates-review-revise-v1.json`) | E-C6 entity-targeted review (`:368`) |
| standard scorer | official `evaluate.py` | `a2t-toolcall` calibrated to arXiv:2604.22821 Table 3 (CLAUDE.md) | ConEC entity-WER mirror + numeric accuracy; Whisper-normalised WER |
| own null | DEV-2000-ADDED h_intent 1.1520 (decision 169); same-flight floors intent 0.65 / SLU 1.49 (decision 190) | h_A2T 1.625 tool accuracy, parameter-F1 margin 2.23 from the same-chain direct A/A (decision 167) | E21: WER 0.058, PERSON 0.250, ORG 0.356, numeric 0.157 (`docs/results/2026-09-27-verdict-reclassification.md:98`); E22: **none measured** |
| queued items | COMP-2 | A2T-ORG-1 closed; A-C1 then A-C3 (re-plan v2 row C2, `docs/readiness/2026-09-27-slurp-stage3-replan-v2.md:49`) | E41 sub10 (E-C0) -> E-C1 into the plan -> E-C2 -> E-C3 (re-plan v2 row C3, `:50`); E22: E-C7 clip boundary; no external sources (E-C8) |

Earnings-22 has a carrier descriptor (`data/carriers.py:407`) and loader support (`rails/adapters/earnings.py:36`) but
no registered runtime TaskAdapter (only `earnings21-original`, `earnings_runtime.py:180`); that registration is a
transfer precondition, not module work.

### 2b.3 Transfer protocol

1. Same module id on every carrier; one adapter (hooks of 2b.1) and one config block per carrier; **no carrier branch
   in the module code** (a test greps the module file for carrier lock keys and fails on any).
2. The module's carrier-agnostic tests run against a fake adapter and a recording fake server (precedent:
   `scripts/analysis/slotfill_fake_server_harness.py`, `tests/unit/test_perception_branch_acceptance.py`).
3. **Admission gate per carrier:** the module-bare arm (every component off, section 3.2) flown as an in-chain A/A on
   the carrier's own roster before any component is turned on; its half-widths are that carrier's module null. E22
   gets its first own null this way.
4. A component turns on per carrier only through its own read on that carrier (row 139's rule; no transfer by
   assumption), and only after SLURP's lock (decision 187 keeps the GPU on SLURP until the owner reopens the others).

### 2b.4 Carrier knobs the SLURP work hard-coded (migration items, behind the adapter)

| knob | where | move to |
| --- | --- | --- |
| SLURP intent-boundary id shape `<store>::intent-boundary:<intent_id>` read by `branch_supplied_intent_ids` | `rails/perception_presentations.py:155-190` | `decision_candidates` hook |
| `DEFAULT_MAX_SLURP_CANDIDATES` = 3 as the `min_candidates` ceiling | `rails/candidate_semantic_supply.py:53`, used at `rails/native_episode_config.py:1439`, `:1470` | `max_decision_candidates` hook |
| relisten's unit extraction via `parse_slu_response` and the SLURP templates / schemas | `rails/runner.py:4418-4421`; `rails/relisten.py:120-126`, `:843-844` | `delivered_units` hook + per-carrier template ids in the config block |
| the SLURP projection normaliser as the default deliver node | `rails/delivery_normalisers.py:90`, `:401` | `default_deliver_normaliser` hook |

The adapter line budget is 260 per file (`engineering_base_check.py:71`); `rails/adapters/audio2tool_runtime.py` is
already at 260, so the hooks go into one new per-carrier file beside the runtime adapter (precedent
`rails/adapters/slurp_runtime_material.py`), each under the budget.

## 2c. Empty is legal (owner decision 199, 2026-09-29)

The owner ruled that a slot may be none and that knowledge retrieval may return nothing (registry row 199); the module
makes both first-class outcomes. The supply policy of every node the module owns (exemplar supply, boundary supply,
slot views) returns an ordered list that MAY be empty; nothing pads it back up to k. The decision to return empty is a
registered, receipted policy, `supply_abstain: {rule, threshold, pinned table}`, applied to the retrieval scores of
that node, never a silent cap or a truncation hidden inside a store. Every abstention writes a receipt row (node, rule,
threshold, the scores it saw, the empty delivery), so an empty supply is as auditable as a full one. The Perception and
Solver contracts state in their instruction bytes that an empty supply is valid input and that an empty entity list
is a valid answer; the Solver contract carries an explicit "no entities" option instead of forcing emission, which is
the failure the COMP-1 citation contract showed (+102 false positives on the 414 zero-gold rows of Fold A). The read
design counts abstentions per node and reads `present`, intent and SLU-F1 on the abstained rows separately from the
supplied rows, beside the pooled table. The all-off arms keep today's fixed-k behaviour (no `supply_abstain` block),
so the module-all-off A/A request bytes are unchanged and AT-M0 to AT-M4 still hold. Carrier independence follows
section 2b: the abstain rule and its receipt live in the module, while the score it thresholds comes from the carrier
adapter (retrieval similarity, vote share, or a carrier-defined relevance). The threshold is fitted model-free on
construction data only (the offline headroom analysis on branch fable/emptysupply) and pinned before any flight; B4
(explicit empty-entity decision, offline net -0.19) is re-examined under this rule rather than closed.

## 3. Composition rule

### 3.1 The config block

```json
"native_episode": {
  "consumption_module": {
    "module_id": "saea-evidence-consumption-module-v1",
    "profile": "slurp",
    "components": [
      {"component_id": "agree-vote-seed", "state": "on",
       "admitted_by": "registry row 161", "record": "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json",
       "params": {"w_agree": 1.0, "k": 60, "agreement_source": {"relpath": "...", "sha256": "..."}}},
      {"component_id": "scope-rule", "state": "on", "admitted_by": "registry row 195",
       "record": "docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md",
       "params": {"min_pool_occurrences": 5, "untagged_share": 0.8, "table": {"relpath": "...", "sha256": "..."}}},
      {"component_id": "relisten", "state": "shadow", "admitted_by": "registry row 185", "...": "..."}
    ],
    "columns": []
  }
}
```

### 3.2 Entry, states and switch-off

- **Entry.** A component may be listed with `state: on` only if its `admitted_by` names a registry row or harness
  receipt entry whose disposition is ADMITTED / NEUTRAL-in-plan, retained, or `nominated` by its own read; the loader
  resolves `record` to an existing file and refuses otherwise, before any contact. Decision 138 stands: no component is
  added on top of an unresolved conflict; a composed read that fails to improve is a conflict diagnosis, and its
  per-class attribution table names the pair.
- **States.** `on` (delivered path), `off`, `shadow` (post-delivery columns only; relisten today), `column` (only as a
  same-flight branch, 3.3).
- **Layers.** Components carry the layer of section 1. `lock` compiles rows 1-6 and 17; with every C component off the
  module compiles **byte-for-byte to the PLAN lock** -- the in-chain A/A comparator of decision 169. `bare` (every
  component off, lock layer included) compiles to the carrier's direct baseline through the same harness; it is the
  transfer gate of 2b.3 and the "direct baseline = module with every component off" of the brief.
- **One key.** The harness receipt gains one entry for the module under a new switch class `module` (a sibling of the
  `episode` class, `rails/config_tables.py:510-524`), whose key is `native_episode.consumption_module`, whose OFF arm is
  the lock-layer block, and whose falsifier for the OFF arm is the request-bytes-identical proof of section 4 (the
  `run`-class precedent). Each component's own admission stays in its own entry or registry row; the module entry
  records only the composition.
- **Ablation.** Leave-one-out and add-one reads flip one component's `state`; the loader refuses a pair of arms that
  differ in more than one component (the one-factor rule of the phase-2 spec, section 1).

### 3.3 Same-flight columns inside the module

`columns` replaces hand-written branch blocks. Each column is `{column_id, toggle: <one component_id>, to: on|off,
level: 1|2}`. The module compiles `columns` into `native_episode.roles.perception.branches` for Perception components
(A = the module's delivered policy, T = its twin, one B per column, refusals 1-18 of `supply_variants.py:1303-1339`
still applied) and into shadow columns for post-delivery components (relisten's two columns, rendered by
`bind_shadow_entities`, `relisten.py:925`). The contact ceiling is computed from the columns
(`perception_branch_ceiling`, `supply_variants.py:1178`; `relisten_extra_ceiling`, `relisten.py:470`). Consequence: the
P-SV question "top-2 contrast vs AGREE as flown" becomes one column toggling `top2-contrast` on over a module whose A
carries it off, and after admission the same component flips to `on` with no new program fragment.

## 4. Migration plan

Every step before step 7 is model-free. One experiment in flight stays the rule; code lands in a worktree and merges
only at a deliberate re-pin point (decision 172's precedent), with the `__pycache__` purge and two-pass re-pin
convergence.

1. **Registry and key (no behaviour).** `CONSUMPTION_MODULES` in `core/base.py`; `native_episode.consumption_module`
   on the allowlist; `engineering_base_check.py` learns `module_id` -> `CONSUMPTION_MODULES` (NESTED_ID_KEYS,
   `:151-173`) and the new canonical file. Checks: `engineering_base_check`, `harness_admission_check`.
2. **Compiler only.** `EvidenceConsumptionModule.compile(block) -> composed native_episode / knowledge_stores /
   phase_material / program id`, with no runtime change. **AT-M0:** lock layer only = the PLAN lock request bytes on a
   sealed pool. **AT-M1 (the brief's equivalence proof):** the module with the AGREE component alone renders
   byte-identical requests to `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` on its sealed pool, content fields compared per
   decision 167's amended identity rule (slot id and request id excluded). **AT-M2:** AGREE + centroid + citation = the
   COMP-1 bytes; the P-SV-1 column = the flown `b-top2contrast` branch bytes; the relisten shadow block = the E4-1 trace.
   All on a recording fake server.
3. **Deterministic USE stage.** The scope rule as a registered delivery-normaliser stage with its pinned table (built
   model-free by a script under `scripts/`, receipted); **AT-M3:** applied to the sealed AGREE and wave-A/A outputs it
   reproduces the offline +1.04 / +0.93 row set exactly.
4. **Delivered-path Perception policy.** Lift refusal 6 for the module-owned A only (the module sets the delivering
   Perception's presentation and contract; a hand-written branch block still may not). **AT-M4:** the module with
   `top2-contrast` on renders, as its delivered Perception request, the bytes the P-SV-1 B branch flew.
5. **Carrier hooks.** Section 2b.4 moves behind the adapter; SLURP bytes unchanged (AT-M0 to AT-M4 re-run).
6. **Re-express the live cells as module blocks (config only)** for new registrations; flown cells keep their bytes
   and records. Checks that must pass: `harness_admission_check`, `engineering_base_check`,
   `flight_registration_check`, `stage3_effect_floor_check` (with `primary_metric_key` declared, decision 190),
   `finite_completion_policy_check`, `stage3_algorithm_label_check`, plus `cli check` and the handoff freshness stamp.
   **Step 6 status (2026-09-30, branch `fable/module6`): DONE, model-free, nothing flown.**
   - *Harness class (ruling R2).* The ninth switch class `module` (`rails/config_tables.py`:
     `MODULE_SWITCH_CLASS`, one key `native_episode.consumption_module`). Its OFF arm is the all-off block
     naming the carrier's CURRENT lock (v2.1 at step 6; v2.2 since owner decision 249, 2026-10-10, with a
     PENDING entry allowed to stay on its registered lock via `switch.lock_superseded_by`);
     `scripts/checks/harness_admission_check.py` rule 8 recomputes the
     licence (falsifier kind `compiles-to-lock`): it compiles the OFF arm, compares it with the named lock
     version's blocks, requires each named cell to carry those blocks on its own roster, and compiles the ON
     arm. `docs/receipts/harness-admission.json` carries one PENDING `module` entry (OFF = lock v2.1 all-off,
     ON = COMP-1b).
   - *Lock versions (decision 204).* A block may declare `lock: v2.1`; the SLURP hooks build v2.1 as the v2.0
     layer with only the Reviewer template moved to the G5 bytes (both templates re-hashed). A block with no
     `lock` key still compiles to v2.0, so A2 and every queued v2.0 cell stay provable. AT-M0 targets v2.1
     (cell G5's flown hashes) and keeps the v2.0 case beside it.
   - *Roster pins.* `CarrierHooks.roster_pin_paths` (the sealed per-roster query vectors) are cell identity,
     never policy: `apply_to` and the loader keep the target's own. A module cell can therefore sit on a roster
     other than the lock's.
   - *First module cell.* `slurp-native-stage3-module-comp1b-dev2000-added-v1`, with its smoke and its in-chain
     A/A `slurp-native-stage3-module-comp1b-aa-dev2000-added-v1` (the module OFF arm on v2.1). Package:
     `docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1/`, all HELD. The AT-M6 proof
     (`module_equivalence_proof.py --at m6`): the arm's policy blocks equal cell A2's flown bytes except
     `phase_material.reviewer.instruction_template`, and the A/A equals the lock-v2.1 blocks. The cell need not
     fly if the byte proof suffices; the coordinator decides.
   - *What remains after step 6.* (a) Delivered-path Perception axes (ruling R3): these arm only once a
     component is nominated and a composed read has carried it. `DELIVERED_PATH_ADMISSIONS` is still empty.
     (b) Re-listen `live` delivery (ruling R4): this needs its own later read. (c) Carrier hook files for
     Audio2Tool and Earnings (`rails/adapters/<profile>_module_hooks.py`), plus Earnings-22's runtime
     TaskAdapter registration (section 2b.2) -- DONE 2026-09-30, see "Carrier transfer status" below. (d) Step 6a,
     supply abstention. (e) Step 7, the first composed read.
   - *Carrier transfer status (2026-09-30, branch `fable/carrierhooks`; owner decision 196, direction 205;
     model-free, nothing flown, decision 187 still bars every Audio2Tool and Earnings flight).*
     - *Profiles.* `core.base.CONSUMPTION_MODULE_PROFILES` maps each profile to its carrier lock keys
       (`slurp` -> `slurp`, `audio2tool` -> `audio2tool`, `earnings` -> `earnings21-original`); the module file
       still names no carrier. `earnings22-original` maps to no profile: it has no baseline and no own null.
     - *Hook files.* `rails/adapters/audio2tool_module_hooks.py` implements `decision_candidates` (the first two
       distinct tool names of the A2T Perception state's `candidate_tools`, or of tool-card value ids),
       `max_decision_candidates` (`max_candidates_per_action` 4), `delivered_units` (parameter values per action,
       through the repository scorer's parser), `tool_offer_units` (string parameter values, section 2d) and
       `carrier_components` (the exemplar-vote seed: not built; A2T-ORG-1: closed HARMFUL); `None`:
       `decision_supply_path`, `default_deliver_normaliser` (none registered), `deliver_stages`,
       `perception_branch_frame`, `flown_branch_programs`, `delivered_path_admissions`, `lock_versions`,
       `current_lock`. `rails/adapters/earnings_module_hooks.py` implements `delivered_units` (numeric values, the
       `numeric-value-accuracy-v1` unit, plus ConEC-term entity mentions when the caller passes the call's context
       terms), `tool_offer_units` (numeric values, E-C3), `default_deliver_normaliser`
       (`saea-deliver-earnings-text-v1`, the registered FORM step; the Whisper normaliser is scorer-side only) and
       `carrier_components` (`kc-e1f-repair-supply`, "admitted on E21 (replicated PERSON +3.634)", the
       Solver-repair analogue, never armable here); `None`: every decision / contrast / forced-candidate member
       (no closed decision label), `deliver_stages`, `perception_branch_frame`, `flown_branch_programs`,
       `delivered_path_admissions`, `lock_versions`, `current_lock`. Two defaulted `CarrierHooks` members were
       added (`tool_offer_units`, `carrier_components`) and a generic `DeliveredUnit`.
     - *Direct layers.* Neither carrier has a locked system, so each hook file's `lock_layer` is a DIRECT layer
       (`policy` + `phase_material` of `a2t-native-system-direct-v1` / `e21-native-window-direct-full44-v1`,
       section 3.2 "bare"). The compiler accepts a direct layer only with every component off and no column;
       anything armed there is refused, and any component whose hook is `None` is refused on a system layer too.
     - *All-off arms (the 2b.3 admission gate), HELD.* `a2t-native-stage3-module-alloff-v1` (+ smoke) on the
       paired 400 and `earnings21-native-stage3-module-alloff-v1` (+ smoke) on the full 44-call discovery roster;
       packages `docs/readiness/2026-09-30-{a2t,earnings21}-native-stage3-module-alloff-v1/`, DRAFT ledger rows,
       `stage3_measurement` form-proof with `claims_benefit: false`. Each declares its all-off block in the
       experiment fragment (`consumption_module_declaration`; a direct program carries no `native_episode`). Byte
       proofs `module_equivalence_proof.py --at a2t0 e210`: the block compiles to the direct baseline's policy
       blocks with no differing leaf, each cell rebuilds to its own composed hash, and each differs from its
       direct parent (A2T-AA pass A / smoke; the E21 full44 / four-row direct cells) by no policy leaf.
     - *Earnings-22.* `rails/adapters/earnings22_runtime.py`, a thin derivation of the Earnings-21 runtime adapter
       (carrier and whole `dev` split only), registered in the shared factory; scoring reuses `asr-wer-whisper`.
     - *What remains per carrier.* Audio2Tool: its all-off arm is request-identical to A2T-AA, so its module null
       is h_A2T 1.625 by construction; next are component candidates (A-C1 do-no-harm candidate formation / the
       exemplar-vote seed once the decision-157 store exists, then A-C3 value grounding) and a system lock to
       compile them onto. Earnings-21: the module null on the native-window form is unmeasured (the measured E21
       null is on the buf90 form) until an in-chain A/A of the all-off arm seals; component candidates are E-C1
       (KC-E1f, admitted, needs an Earnings system lock) then E-C2 / E-C3. Earnings-22: no own null, no baseline
       fragment (its direct program needs prepared execution units that do not exist), so no cell on it may claim
       a benefit. For every carrier: no component-on cell and no composed read before the SLURP lock, when the
       owner reopens the carrier (decision 187).
6a. **Supply abstention, model-free (decision 199, section 2c).** Register the `supply_abstain` block and its receipt
   rows; pin the threshold table fitted offline on construction data (branch fable/emptysupply); add the explicit
   "no entities" option to the Solver contract as a component-owned template. **AT-M5:** with the block absent the
   module renders the AT-M0 to AT-M4 bytes unchanged; with it present, on a sealed pool and a recording fake server,
   every abstained node delivers an empty list with a receipt row and no node is padded to k.
7. **First composed read (first model contact of the module).** DEV-2000-ADDED: the module with its C components as
   decided by the reads R4 (COMP-1/G5), R6 (P-SV) and R3 (E4-1) plus the scope rule (decision 195 = B), against the
   module-all-off (lock layer) in-chain A/A; bar: cross-flight 2.5 pp at n = 1,080 (instrument note
   `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`), DEV-2000-ADDED own null h_intent 1.1520
   (decision 169); intent primary unless the component list makes SLU the declared primary; per-stratum tables; expected
   effect composed from measured m values only (decision 139). It is re-plan v3's R7.
8. **Milestone.** The test-sample read (`SLURP-TEST-SAMPLE-3010-V1`, decision 151) on the owner's go after a
   dev-admitted composed arm is reported in conversation.

## 5. Open questions for the coordinator

1. **Program id vs contact ceiling.** The rule "two program ids must never resolve to the same object when their
   contact ceilings differ" (`controllers.py:1712-1741`) forces one program file per ceiling. Should the module register
   a program family keyed by its computed ceiling (e.g. `phase-native-ecm-v1-c21`), one committed file per used
   ceiling with a test that the file's `max_contacts` equals the module's computed ceiling, or keep choosing among
   hand-registered programs?
2. **Harness form.** A new `module` switch class whose OFF arm is the lock layer (not the key's absence), licensed by
   the request-bytes-identical AT-M0, or the existing `episode` class with a null arm of "absent" plus a separate
   lock-layer proof?
3. **Refusal 6.** Is lifting "A carries no axis" for the module-owned delivered policy acceptable to the instrument's
   reading of A and T (T still replicates A byte for byte), or should an admitted Perception component instead move A's
   bytes through the lock layer at a re-pin point?
4. **Relisten in the composed read.** If E4-1 nominates a column, does the step-7 read carry relisten `live` (its own
   promotion, E4 spec section 4) or keep it `shadow` inside the composed flight and promote it in a later read?
5. **Scope-rule table roster.** The table is built from TRAIN minus Fold A; for DEV-2000-ADDED it is roster-clean, but
   should it also exclude Fold B now that Fold B is rollout-exposed (decision 186)?

## Coordinator rulings (Fable 5.1, 2026-09-29)

- **R1 (program id vs contact ceiling).** Yes: the module compiles a program FAMILY, one registered program id per
  computed ceiling (`phase-native-module-v1-c<ceiling>`), emitted by the compiler and registered through one family
  registration in `rails/controllers.py`; the one-id-one-ceiling rule stays intact and no program fragment is written
  by hand.
- **R2 (harness form).** A new `module` switch class whose OFF arm compiles byte-for-byte to the v2.0 lock (licensed
  by AT-M0). The lock is the null arm of every composed read; the "everything off, lock included" setting is used
  only as the per-carrier admission gate (section 2b).
- **R3 (delivering branch).** Admitted Perception components enter through the module's own delivered policy: branch
  A may carry a presentation and a candidate count once that component's column read has NOMINATED and the composed
  DEV read has carried it. The lock itself is not re-pinned for this; a lock revision (v2.x) happens only when the
  owner locks a composed arm.
- **R4 (re-listen in the composed read).** The first composed read keeps re-listen in `shadow` (its two shadow
  columns are read for free inside the same flight); `live` is armed only in a later composed read that changes
  nothing else (one change per read, decision 164's rule).
- **R5 (scope-rule table roster).** Build the scope-rule table from TRAIN minus Fold A, minus Fold B
  (rollout-exposed, decision 186) and minus R01/R01C, exactly the contrast-pair table's exclusions; re-derive the
  offline +1.04 / +0.93 estimate on that table before AT-M3, and register the table with a receipt like
  `SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V2`.
- **Id.** `saea-evidence-consumption-module-v1` is accepted; the carrier enters as `profile`.
- **Sequencing.** Steps 1-5 of the migration are model-free and may start now in a worktree; step 6 onward waits for
  the P-SV-1/P-SV-2 and E4-1 reads, which name the first composed component list. Owner decisions 195 and 196 are the
  authority; the design admits nothing.

## 6. What this design does not decide

- No component's admission, and not the step-7 component list: that follows the R3, R4 and R6 reads.
- No flight, flip, registration, exposure-ledger row or test-sample contact.
- Not E3's build go, the Reviewer B5 round (decision 188), the Whisper comparison (decision 180), or the
  boundary-recall blank (83 off-list rows, 49 in the block; ledger `:244`).
- Not any Audio2Tool or Earnings cell: section 2b is the transfer shape only; decision 187 keeps the GPU on SLURP.
- Not a change to the lock: the lock layer compiles to the existing PLAN bytes and is proven so, not re-decided.

## 2d. Tool use is a model decision (owner directives, 2026-09-29)

**Owner directives (2026-09-29; translated from the owner's Chinese, verbatim text in
`docs/readiness/2026-09-29-research-direction-system-level-v1.md`).** (1) "We are adjusting the research direction: on
09-06 the focus was still on how to make good use of the main model; it now becomes how to build the system and
optimise it at system level." (2) "Tools should be invoked by the model on its own initiative, not called by the
system by default; otherwise we fall into the self-proof trap -- why would the task not be done by an ASR + LLM
combination, and why would it need an omni agent system!"

The module OFFERS tools; it never calls a tool on the model's behalf, and no module part may turn a tool output into
delivered content without a model decision in between. A tool offer is a component like any other in section 1, with
the states `on` (offered on the delivered path), `off` (not rendered at all) and `column` (offered only in a
same-flight column, 3.3); `shadow` is not a legal state for an offer, because an offer that the model cannot see is not
an offer. An offer is scoped to ONE node: the first one, `tool-offer:asr-slot-value`, is rendered only at the Solver's
slot-value step, which is owner decision 180's thesis in its model-initiated form -- if the core cannot extract a value
natively, it may call ASR to verify it. The offer is rendered through the existing native tool-calling path
(llama-server with `--jinja`, the `phase_tools` block of `rails/native_episode_config.py:1316`, `tool_choice` set to
`auto` only where tools are named, `rails/runner.py:3536`) and its wrapper is registered in the `rails/tools.py`
catalog through `build_tool_entry` (`:357`), so `tool_catalog_check.py` pins it like every other tool. The offer must
be minimal, because this study has already measured what a heavy offer costs: rendering a tool schema constantly into
every role (EFF-1) made the Solver answer with a tool-call-shaped string on 145 of 1,092 contacts and was HARMFUL,
SLU-F1 -4.39 [-6.69, -2.17] (`docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md`); the Reviewer's
task-contract tool was RETIRED (`docs/receipts/harness-admission.json`); and a full native tool catalog renders to
13,914 tokens (`docs/readiness/2026-09-04-a2t-direct-baseline-calibration-v1-verdict.md:140`). So an offer is one
tool, a short schema with a closed argument space, present only at its node and absent from every other role's
request. Each model call through an offer costs one more core contact inside the same ReAct episode, counted into the
program ceiling like any other contact of section 2.4, which this section extends: the "no tool-level verifier" line
of 2.4 holds for system-applied verification and is superseded for model-initiated offers once owner rows 201 and 206
stand.

The model's decision is receipted per row and per offered node as
`tool_decision: {offered, called, args_hash, result_hash, used_in_answer}`, where `used_in_answer` is computed
deterministically after delivery (the delivered value at the called index differs from the pre-call draft value, or
matches the returned span under the E5 canonicaliser) and never read from the model's own claim. The read of any tool
offer measures three things separately and never pools them: the **call rate** (calls over offered rows), the
**decision precision and recall** against the offline DECISION ORACLE (the rows where a call would have helped, which
for the ASR offer is E5-1's set of delivered values that are wrong while the transcript holds the gold span), and the
**conversion** (delivered values changed from wrong to correct, net of correct values changed to wrong). The
sealed-credit inner loop (`SEALED_CREDIT_SYSTEM_POLICY_V1`) credits the DECISION node -- when to call -- before it
credits the tool's quality, which is the offer-level echo of the Reviewer rule "reach before quality": a perfect tool
that the model never calls at the right rows is worth nothing, and a tool's quality is only readable on rows the
decision reached.

Deterministic FORM normalisers -- the delivered-row normaliser (row 4) and the do-not-tag scope rule (row 15; its
bar under registry row 203 as the coordinator numbers it) -- are not tools and stay system steps. They are flagged here
as the ONE class of system-default action the module takes, and the reason is stated so the class cannot grow: they
change the FORM of what the core already delivered (projection, casing, scope of tagging), never the EVIDENCE the
answer rests on, so they cannot turn the system into "a fixed front end plus an LLM". Anything that adds evidence the
core did not choose to consult -- a transcript, an alignment, a retrieval result -- is an offer or it is nothing. The
all-off arm offers no tool at all, so its request bytes are the AT-M0 lock bytes unchanged and every A/A comparator of
section 3.2 stays valid.

| verification route | who decides to verify | what the receipt records | what the read measures | what the oracle is |
| --- | --- | --- | --- | --- |
| core-native targeted re-listen v1 (E4-1, `saea-obs-targeted-relisten-v1`) -- CLOSED at SHADOW HARM (replace-only SLU-F1 -4.11 [-5.41, -2.88]) | the system (the stage fired on every delivered entity, at most 3 per row) -- the default-applied pattern this section bars | `saea-relisten-v1`: per-entity blind / confirm contacts, accepted replacement, value hashes | replace-only and replace + drop shadow columns vs the delivered column | the headroom hearing-visible 71 + re-listen-addressable 35 items |
| E5-2a system-applied transcript check in delivery -- WITHDRAWN as a runtime candidate | the system (a rule applied to every delivered entity) | none at runtime; offline only | R-FLAG / R-DROP / R-SWAP columns on sealed arms (E5-1) | itself: kept only as the UPPER BOUND on what a perfect decision to call could yield |
| E5-2 ASR tool offer `tool-offer:asr-slot-value` (one tool, `verify_span(entity_index)`, E5 spec addendum) | the model, at the Solver's slot-value step | `tool_decision {offered, called, args_hash, result_hash, used_in_answer}` per row, plus `saea-asr-verify-v1` hashes for each returned span | call rate; decision precision / recall; conversion on called rows; whole-column SLU-F1 guard; intent rows differing = 0 | the E5-1 DECISION ORACLE: delivered value wrong and gold span contained in the pinned transcript (Q1 and not Q2) |
| future MMS_FA aligner tool (word timing for a named value) | the model, at one declared node | the same `tool_decision` shape plus the alignment artifact hash and the tool-smoke ledger row | same three measures | an offline oracle built from MMS_FA timings on sealed arms before the offer is registered |
| future speech-embedder tool (LCO-Embedding-Omni; speech-keyed lookup the model requests) | the model, at one declared node | the same `tool_decision` shape plus the query-vector and result-list hashes | same three measures, plus retrieval hit rate on called rows | an offline oracle of rows where the requested lookup returns the gold unit (decision 199's empty result stays legal) |

**Inventory addition (section 1).**

| # | component | where it lives today | status | layer, plane, node | model contacts | measured or declared effect (source) |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | `tool-offer:asr-slot-value`: one model-initiated ASR tool, `verify_span(entity_index)`, offered only at the Solver's slot-value step; returns the pinned E5-0 transcript span for that entity or an empty result | `docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md` (addendum) and this section only | designed; E5-0/E5-1 oracles pending | C, OBS evidence offered to USE; Solver slot-value step only | +1 core contact per call (the tool round-trip inside the Solver's ReAct episode); 0 when not called; the tool itself is a `speech-tool` catalog read, no live decode | none measured; upper bound = E5-1's oracle, gate in the E5 addendum |

**Carrier mapping addition (section 2b.2).**

| component | SLURP form | Audio2Tool form (tool = intent analogue, parameters = slot analogue) | Earnings-21 / -22 form |
| --- | --- | --- | --- |
| model-initiated ASR tool offer (`tool-offer:asr-slot-value`) | `verify_span(entity_index)` at the Solver's slot-value step; span from the full-utterance E5-0 catalog | the same offer at the parameter-filling step, indexed over the draft call's string **parameter values** (enums and numerics stay with `a2t-toolcall`'s own grading); the A2T clip transcript from the same producer | the same offer at the entity / numeric step, indexed over the draft's **numeric and entity values** (E-C3's targets); span cut through MMS_FA timings and `saea-tool-slice-encode-v1` under a declared derived root, because 90-s windows exceed Whisper's 30-s limit |
