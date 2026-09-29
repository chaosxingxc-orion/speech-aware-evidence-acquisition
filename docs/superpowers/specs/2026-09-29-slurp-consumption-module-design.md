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

## 6. What this design does not decide

- No component's admission, and not the step-7 component list: that follows the R3, R4 and R6 reads.
- No flight, flip, registration, exposure-ledger row or test-sample contact.
- Not E3's build go, the Reviewer B5 round (decision 188), the Whisper comparison (decision 180), or the
  boundary-recall blank (83 off-list rows, 49 in the block; ledger `:244`).
- Not any Audio2Tool or Earnings cell: section 2b is the transfer shape only; decision 187 keeps the GPU on SLURP.
- Not a change to the lock: the lock layer compiles to the existing PLAN bytes and is proven so, not re-decided.
