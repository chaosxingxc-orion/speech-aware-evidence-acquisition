# SLURP agent base lock v1 — DRAFT for owner review

Author: Claude Fable 5.1, root coordinator. Date: 2026-09-19. Tree: `fable/base-lock` at
`9418c69c`. Status: **DRAFT. Nothing here is locked, admitted, decided or authorised.**
Authority: owner decision 33 of 2026-09-19 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`,
section "Owner decisions 29-35"): *"First lock the agent engineering base, and the context between
every node and the optimisable space, including the knowledge-construction method and content; only
then discuss the training-free RL framework."*

Machine-readable companion: `docs/receipts/slurp-agent-base-lock-v1-draft.json` — the same node
graph, **12 boundaries**, **9 knowledge stores** plus **5 vector pins**, **72 knobs**, **15 findings**
and **10 owner questions**, with a `derived_from` list of **83 file paths and their sha256 at
`9418c69c`**, so a later gate can compare a tree against whatever the owner approves.

Zero contacts: no model, tool, scorer, tokenizer or encoder was reached while this draft was written,
and no code, config, knowledge store, receipt or ledger row was changed.

---

## 1. Purpose and status

### 1.1 What this document is

Decision 33 blocks the Stage-3 (training-free RL) specification behind one deliverable: a written
statement of **what the agent actually is today**, precise enough that a later optimiser has a named
action space instead of a codebase. This draft is that statement. It describes four things and
proposes a status for each:

1. the **node graph as flown** — which nodes exist, in what order, under what ceilings, with what
   routing and what failure dispositions (section 2);
2. the **context contract per boundary** — for every `(consumer role, semantic class)` pair, what
   the consumer reads, from which producer, at which level, through which template, and what happens
   when the upstream does not parse (section 3);
3. every **knowledge store** — its identity, its content, how it was constructed, which exclusion
   rule keeps evaluated rows out of it, and which boundary consumes it (section 4);
4. the **optimisable space per node** — every knob, its current value, its admissible range, its
   cost, the evidence that has moved it, and whether the lock should freeze it or leave it open
   (section 5).

### 1.2 What "lock" will mean once approved

The owner approves a lock; the lock then has teeth. This draft proposes the following meaning, and
asks the owner to confirm or amend it (question Q8, section 6.2).

**Frozen by the lock** — changing any of these requires a new owner decision, not an implementer's
judgement:

| Frozen object | Where it lives |
| --- | --- |
| The four-role episode graph and its routing (Perception → Solver → Reviewer → Planner, one revision, ACCEPT / REVISE / terminal delivery) | `reproduction/ojw/native_episode.py`; `configs/policy/phase-native-candidates-review-revise-v1.json` |
| The closed `episode` switch allowlist and every key's OFF semantics | `rails/config_tables.py` `EPISODE_LEVEL_SWITCH_KEYS`, `is_episode_null_arm` |
| The twelve boundary ids, their parsers, their renderer keys and their default templates | `rails/node_context_policy.py` `SLURP_BOUNDARY_IDS`, `PARSER_IDS`, `RENDERER_KEYS`, `SLURP_BOUNDARY_TEMPLATES` |
| The default plan's armed module list | `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`; `docs/receipts/harness-admission.json` `default_plans[1]` |
| Every knowledge store's release/snapshot pin and its construction rule | section 4; `docs/receipts/knowledge/*.json` |
| The construction-pool exclusion (TRAIN minus Fold A, Fold B and DEV-1000; 9,354 retained utterances; split identity `67e53fb5…`) | `scripts/build_slurp_slot_audit_view.py`, `scripts/build_slurp_scenario_hints_view.py`, `scripts/build_slurp_exemplar_pool_assets.py` |
| The serving geometry and decoding block | `configs/model/q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1.json` |
| The scoring contract: one official `slurp-slu-official-train` score per complete manifest through `core.scoring_batch` | program spec section 5 |

**Left open for Stage 3** — the action space a training-free optimiser may search, subject to its own
preregistration, without reopening the lock: every knob marked `OPEN` in section 5. In short: the
exemplar policy (`k`, fusion, rank weights, `tau`), the candidate-union caps, the sampling and
aggregation block, the per-boundary NCP level, and the per-node context composition. Nothing in that
set changes a node's identity; each changes only how much of what kind of material a node is handed.

**Neither frozen nor open** — knobs marked `UNEXPLORED`: admissible by the loader, never flown, with
no evidence. They are not part of the Stage-3 action space until a cell or the owner puts them there.

### 1.3 Scope

SLURP only. Earnings-21/22 and Audio2Tool share the same harness (`rails.controllers.EvidenceAgentController`
+ `core.flight.FlightRuntime`) and the same policy object, but no carrier inherits another's verdicts,
and this draft proposes nothing for them.

---

## 2. The node graph as flown

### 2.1 Program and roles

The flown program is `configs/policy/phase-native-candidates-review-revise-v1.json`
(`stop_rule: native-role-episode`, `max_contacts: 11`). Its four phases are `perception`, `reviewer`,
`planner`, `solver`; the *episode* order is Perception → Solver → Reviewer → Planner. Every phase
declares `knowledge: "supplied"`, `barrier: false`.

| Role | Phase id | `max_iterations` | `history_scope` | Response format | Tools | Instruction template |
| --- | --- | ---: | --- | --- | --- | --- |
| Perception | `perception` | 1 | `full` | `slurp-intent-hypotheses-v1` | none | `probes/slurp_native_role_perception_v3.txt` |
| Solver | `solver` | 1 | `full` | none (free text under the task contract) | none | `probes/slurp_native_role_solver_v2.txt` |
| Reviewer | `reviewer` | 3 | `full` | none (prose) | `saea-tool-task-contract-v1` | `probes/slurp_native_role_reviewer_v1.txt` |
| Planner | `planner` | 1 | `full` | none (`exact-text` action) | none | `probes/slurp_native_role_planner_v1.txt` |
| Delivery normaliser | not a phase | — | — | — | — | `saea-deliver-normalise-v3` |

The shared task contract is `probes/slurp_native_role_context_v3.txt` with fill
`slurp-label-inventory` (the closed 60-intent / 54-type inventory), rendered into every role's system
message.

**The delivery normaliser is a node, not a role.** It makes no contact, registers no agent state and
routes no episode step. `rails/runner.py:2778-2793` applies it exactly once per row, after the
Planner's ACCEPT (or after the terminal delivery of the last revision), after every guard that binds
the accepted answer to its source response, and before that answer becomes the delivered text. An
abstention is never normalised.

### 2.2 The phase program and the contact ceiling

`rails/native_episode_config.py:759-770` fixes the ceiling and refuses a program whose
`max_contacts` disagrees with it:

```
ceiling = perception.max_iterations
        + (max_revisions + 1) * ( solver.max_iterations * solver.samples
                                  + reviewer.max_iterations
                                  + planner.max_iterations
                                  + cleaning_contacts_per_revision )
        + max_candidate_refreshes * perception.max_iterations
```

| Configuration | per-revision sum | Ceiling | Program fragment |
| --- | ---: | ---: | --- |
| Default plan / anchor | 1 + 3 + 1 = 5 | **11** | `phase-native-candidates-review-revise-v1` |
| Reviewer response format (B7r, B8b) | 5 | 11 | `phase-native-candidates-review-revise-findings-v1` |
| Review loop off (M0, HARMFUL) | 1 | 2 | `phase-native-candidates-solve-v1` |
| Grouped Solver, 5 samples (M2, NEUTRAL) | 5 + 3 + 1 = 9 | 19 | `phase-native-candidates-review-revise-samples5-v1` |
| One cleaned boundary (B7b, L2) | 5 + 1 = 6 | 13 | `phase-native-candidates-review-revise-clean1-v1` |

Measured on the sealed anchor: **5.0157 contacts per row**, 1,080 rows, about 3.4 GPU hours.

### 2.3 Routing

The Planner's output is matched **byte for byte** against the registered action set
(`reproduction/ojw/native_episode.py:255-300`). Under the flown `planner_output_format: "exact-text"`
the legal set is `{ACCEPT, REVISE, ACQUIRE}` (`native_episode.py:352-358`).

| Action | Route at revision 0 | Route at the terminal revision (`revision == max_revisions`) |
| --- | --- | --- |
| `ACCEPT` | `_Accept` → end; the committed draft is delivered | same |
| `REVISE` | `_AdvanceRevision` → Solver re-entered | `_TerminalDelivery` (`exhaustion_policy: deliver-latest-solver`): latest draft delivered, `terminal_disposition.reason = "revision_limit"`, `planner_accepted: false` |
| `ACQUIRE` | `_Exhausted("episode has no configured analytical acquisition role")` — **raises, aborting the flight** (no acquisition node is ever built for SLURP) | `_TerminalDelivery`, exactly as `REVISE` |
| anything else | `PLANNER_ACTION_ILLEGAL` → the same `_Accept` component (E8c) | same |

The prompt advertises only the actions the episode can take: `rails/runner.py:2044-2047` sets
`available_planner_actions = [ACCEPT] + ([REVISE] if revision_index < max_revisions else [])`.
`ACQUIRE` is never advertised. It is nonetheless legal at the parser and unroutable at revision 0 —
see finding **I-1** (section 6.1).

### 2.4 Dispositions

| Disposition | Trigger | Effect on the row | Receipt |
| --- | --- | --- | --- |
| `planner_action_illegal` (E8c) | Planner output names no registered action, or (under `json-action-v1`) defeats the strict single-key parse | Row sealed through the explicit-accept path: committed draft delivered unchanged, no further contact, no revision spent, row scored normally | `planner_routes[i]` gains `legal: false`, `disposition`, `action_sha256` over the whole token, `action_chars`, `action` truncated to 32 characters; `native_episode_receipt.planner_action_illegal` carries the count |
| `finite_completion` (E13) | A valid source-bound completion the core ended before authoritative delivery (`finish_reason` `length` or `content_filter`) | With `finite_completion_policy: "deliver-latest-or-abstain"` (the default plan) the row is retained: latest delivery-eligible Solver draft, or an abstention. With `"raise"` (the parser default) the flight aborts | `terminal_disposition.reason = "finite_completion"` naming the interrupted role |
| `revision_limit` | `REVISE` or `ACQUIRE` at the terminal revision under `deliver-latest-solver` | Latest draft delivered, `planner_accepted: false` | `terminal_solver_receipt`, `terminal_disposition` |
| abstention | no delivery-eligible Solver draft | empty delivered text, derived identity record, never normalised | `abstention_receipt` |

A cell verdict must read the `planner_action_illegal` count: rows sealed that way answered without a
Planner decision, so a cell whose count is not ~0 reports on a different population than its
comparator.

### 2.5 The fit gate

`native_contact_fit` (`core/preparation_fit.py:873-930`) is the pre-contact dry run every native cell
carries: `{run_id, attempt_id, contact_cap, max_speech_packets}`. The default plan declares
`contact_cap: 47520`, `max_speech_packets: 1`. It is mutually exclusive with `live_phase_fit`,
`prepared_request_fit`, `prompt_fit_receipt` and the whole-roster wave barrier, and it requires the
`native-role-episode` stop rule. It produces `native_contact_fit_receipts` in the dispatch record —
the prompt-fit proof the program's section 5 requires before contact.

### 2.6 Serving geometry

| Property | Value |
| --- | --- |
| Fragment | `configs/model/q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1.json` |
| Model lock | `qwen3-omni-30b-a3b-instruct-gguf-q4km`, llama-server at `127.0.0.1:8080`, timeout 420 s |
| Server args | `-c 98304 -np 4 -b 2048 -ub 512 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --cache-prompt --cache-ram 0 --no-cache-idle-slots --slot-prompt-similarity 0` |
| Slots | `serving_slots: 4`, `serving_slot_tokens: 24576`, `id_slot: per-sample` |
| Decoding | `temperature 0`, `seed 20260913`, `max_tokens 512` |
| Speech | `speech_feature_root /home/chao/feat-cache/slurp-q4km-packets-04ccc72a`; promotion receipt sha256 `4f048f47…` |
| Attachment | Flights **attach** the one resident serving session under the data root and never spawn or stop it (`core/flight/runtime.py:3869-3960`); a resident session serving another geometry is a refusal |
| Headroom | Largest observed prompt 14,868 tokens (planner#1) = 60.5 % occupancy; 9,708 tokens of headroom at the worst observed contact |

---

## 3. The context contract per boundary

### 3.1 What a boundary is

A boundary is the pair `(consumer_role_kind, semantic_class)` — the kind of upstream material, not
the producer's contact, because the same output means different things to different consumers. There
are **twelve** (`rails/node_context_policy.py:181-194`): eight model-text boundaries and four
tool-observation boundaries.

The policy is a **per-state transform**, never a re-selection: it keeps every state of the already
selected history, in order, and replaces only the content of states whose boundary is declared at a
non-`raw` level. That is what makes L0's byte identity true by construction.

Levels: **L0 `raw`** (today's pass-through, `[agent state {state_id} kind={state_kind}] {content}`);
**L1 `structured`** (deterministic parse → declared malformed rule → hash-pinned template, zero
contacts); **L2 `cleaned`** (L1 plus one extra metered contact at a declared boundary, schema-validated,
falling back to L1 on any failure, one attempt, no retry).

### 3.2 The boundary table

**Today's default plan declares no `native_episode.context_policy` key at all, so every boundary below
is at L0.** The L1 column is what cell B7a v2 registers
(`configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v2.json`, next in the GPU queue under owner
decision 27) and what the later L1-family cells build on.

| Boundary id | Consumer · semantic class | Producer | Reads | L1 template | Parser | On parse failure | Cell / status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `B-CAND-SOL` | solver · candidate-hypothesis | Perception | The bounded intent hypotheses (≤3, id + distinction ≤128 chars) | `probes/ncp_slurp_candidate_hypothesis_v1.txt` | `rails.slurp_intent_hypotheses.project_bounded_slurp_intent_hypotheses` | `raw` | B7a v2 — registered, not flown |
| `B-CAND-REV` | reviewer · candidate-hypothesis | Perception | the same list | same template | same | `raw` | B7a v2 — registered |
| `B-DRAFT-REV` | reviewer · current-draft | Solver | scenario, action, intent, entity type=filler pairs, candidate-membership flag | `probes/ncp_slurp_current_draft_reviewer_v1.txt` | `reproduction.slurp_scoring.parse_slu_response` | `raw` | B7a v2 — registered. **Carries the B8b slot-audit block as an appended addition** |
| `B-DRAFT-PLAN` | planner · current-draft | Solver | the draft fields plus the deterministic `HARNESS CHECKS` block (parses / intent among candidates / entity types legal) | `probes/ncp_slurp_planner_brief_v1.txt` | same | `raw` | B7a v2 — registered (owner decision 12(2) put the checks block in B7a) |
| `B-DRAFT-SOL` | solver · current-draft | Solver, previous visit | the revising Solver's own previous answer, with revision index | `probes/ncp_slurp_current_draft_solver_v1.txt` | same | `raw` | B7a v2 — registered. **First instance of L1 is E2c**: a grouped Solver visit seals one committed draft, not N raw samples |
| `B-REVIEW-PLAN` | planner · review-finding | Reviewer | verdict, issues, cited evidence availability | `probes/ncp_slurp_review_finding_v1.txt` | `rails.review_findings.parse_review_findings` | `raw` | B7a v2 at L1; **the only boundary cell B7b declares `cleaned`** |
| `B-REVIEW-SOL` | solver · review-finding | Reviewer | the same review | same template | same | `raw` | B7a v2 — registered |
| `B-PLAN-SOL` | solver · plan-action | Planner | the Planner's action token, revisions remaining, actions still available | `probes/ncp_slurp_plan_action_v1.txt` | `rails.node_context_policy.parse_plan_action` | **`refuse`** | B7a v2 — registered; reachable only after a `REVISE`, so effectively unreachable since E8c |
| `B-TOOL-PERCEPTION` | perception · tool-observation | the role's own tool chain | replayed task-contract observation | `probes/ncp_slurp_tool_observation_v1.txt` | `rails.node_context_policy.parse_tool_observation` | `raw` | **B7c** — held, `raw` in B7a v2 |
| `B-TOOL-SOLVER` | solver · tool-observation | same | same | same | same | `raw` | B7c — held |
| `B-TOOL-REVIEWER` | reviewer · tool-observation | `saea-tool-task-contract-v1` | a live tool chain is left verbatim (`raw_reason: "live-tool-chain"`) | same | same | `raw` | B7c — held |
| `B-TOOL-PLANNER` | planner · tool-observation | same | a later role's **replay** may be rendered by reference, and only when the contract is provably a substring of that request's own system message | same | same | `raw` | B7c — held |

Today, at L0, exactly one admission test runs at every boundary — `bool(output.strip())` — and one
template. The audit measured the consequence: 7 Solver drafts that do not parse as the task answer
reached the Reviewer and the Planner verbatim and were accepted by all seven Planners, and 2,167 of
2,167 Reviewer outputs fail the repository's own registered findings parser.

### 3.3 Supply paths that are not boundaries

Three channels put material into a node's request without being node-context boundaries. They are
supply, not hand-off, and the policy object never touches them.

| Path | Consumer | Config key | Form | Status |
| --- | --- | --- | --- | --- |
| Perception candidate supply | Perception | `knowledge_stores.intent-boundaries.phase_supply.perception` | `kb-facet-v1` retrieval over the intent-boundary store, keyed by the row's own sealed speech vector; result becomes the phase's supplied evidence block | **In the default plan** |
| Solver candidate semantic supply | Solver | `knowledge_stores.slot-contracts.candidate_supply.solver` | the slot-contract values attached to the Perception candidates the Solver is choosing between, round-robin ranked, capped | **In the default plan** |
| Solver exemplar supply (M1) | Solver | `knowledge_stores.train-exemplars.phase_supply.solver` | top-20 annotated TRAIN exemplars, keyed by the row's own sealed speech vector, delivered as typed content | ADMITTED, **replication obligation UNMET**, not in the default plan |
| Reviewer slot audit (B8b) | Reviewer | `native_episode.reviewer_audit` | an **addition** appended after the `B-DRAFT-REV` L1 block, one newline between them | held |
| Solver scenario hints (B8c) | Solver | `native_episode.solver_hints` | an **addition** appended after the `B-CAND-SOL` L1 candidate list | built, **no committed arm** |
| Delivery normaliser (M3) | delivery | `native_episode.deliver_normaliser` | rewrites the accepted answer before it becomes delivered text | **In the default plan** |

On a repeat Solver visit after a `REVISE`, `rails.controllers.restrict_repeat_visit_supply`
(`controllers.py:1276-1355`) restricts the prepared supply to what the trajectory does not already
hold and emits no acquire transition when that is nothing; the values still reach the revisited
request through the accumulated `QueryState`, and every first visit stays byte-identical (E3c).

### 3.4 What no node may read

This is the research boundary, machine-enforced where possible, and it is part of what the lock fixes.

- **No gold of an evaluated row**, anywhere, at any node, at any level. Every B8-family block is
  authored from construction data alone; a rule that only exists because it was fitted to the
  evaluated rows' gold stays a diagnostic ceiling (which is why A3's own confusion pairs are *not*
  what B8c's table contains).
- **No transcript and no ASR state.** Owner ruling of 2026-09-06: retrieval queries carry speech or
  speech+state, never text (`rails/phase_supply.py:185-188`, `QUERY_SIGNAL_MODALITIES`, enforced as
  the first token of `embedded_signal`).
- **No future turn**, no reference transcript, no other evaluated row's content.
- **No second answering model.** The frozen core holds final answer authority; a cleaning contact
  (L2) may only select, label and compress what L1 handed it, and `validate_cleaning_document`
  refuses any content token that is neither one of the schema's fixed words nor present, case-folded,
  in the L1 material.
- **The Reviewer seat is criticism-only** (owner decision 11-C): `core.base.JudgeRegistry` refuses at
  the door anything that could return replacement text. That is why the delivery normaliser lives in
  `DELIVERY_NORMALISERS` and can never be a judge.
- **No knowledge or evidence block is touched by the policy at any level** — only `agent_state`
  entries. The speech packet, the system message and `supplied_evidence` are outside its reach.

---

## 4. Knowledge stores

### 4.1 The construction pool and its exclusion rule

Every store authored for this program draws from the **governed SLURP TRAIN split minus every
utterance with a recording in TRAIN Fold A, Fold B or DEV-1000** — the 2026-09-13 exclusion.
Retained: **9,354 utterances**; excluded: **2,160**; split identity hash
`67e53fb5f712c40b21b8b54b74e867e6da209f057c68cd40dd987aaa99b19875`. The three excluded rosters are
pinned by file hash inside each build receipt:
`docs/receipts/rosters/slurp-evo-fold-a-v2.json` (`1fe7908c…`, 1,080),
`docs/receipts/rosters/slurp-evo-fold-b-v2.json` (`47b89b9e…`, 1,080),
`docs/receipts/probe-samples/DEV-1000.json` (`653c7556…`, 0 TRAIN utterances).
The builders re-check the rule at build time (`refuse_evaluated_rows`) and refuse a pool of any other
size or identity.

The two **authored** stores (intent boundaries, slot contracts) use an older, narrower permitted
roster of their own (`intent-support-construction-roster.json`, `slot-support-construction-roster.json`)
with the same three forbidden rosters; their builder raises when the used sources intersect the
forbidden set or differ from the permitted set.

### 4.2 Store table

| Store id · version | Root | Content (a record) | Counts | Builder | Consumer boundary | Status | Release / snapshot pin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `intent-boundaries-v1` | data | a value = one intent's boundary card (`content`, `associated_facet_ids`, `source_sample_ids`); a facet = one `intent-boundary` text key | 60 values, 60 facets, 2,037 source recordings; 5,740 content words | `rails.semantic_knowledge_build.build_intent_boundary_snapshot` via `saea-driver prepare-semantic-knowledge` | Perception `phase_supply` | **in the default plan** | release `2e51c14b…`, snapshot (content) `5520b844…`, completion `ebd60aca…` |
| `intent-boundaries-v2` | data | same shape, re-authored cards | 60 / 60 / 2,037 | same builder, registration v3 | Perception `phase_supply` | **held** — cells B4a (with the fallback) and B4c (alone, only if B4a admits) | release `31eb595b…`, snapshot `8a27424a…` |
| `intent-boundaries-factored-v1` | data | same shape plus one shared-guidance value | **61** values, 60 facets | `build_factored_intent_boundary_snapshot` | none today | superseded / unused | release `1aa06765…`, snapshot `2f51a962…` |
| `slot-contracts-v1` | data | a value = one entity type's contract card | 54 / 54 / 3,162; 11,647 content words | `build_slot_contract_snapshot` | Solver `candidate_supply` | **superseded** by v2 in the default plan | release `8a29c48b…`, snapshot `11c246e4…` |
| `slot-contracts-v2` | data | same shape; eight revised date/time cards authored from construction data only | 54 / 54 / 3,162 | same builder, registration v2 | Solver `candidate_supply` | **ADMITTED and REPLICATED** (module M4b); in the default plan | release `f8e42d4f…`, snapshot `d5992bd1…` |
| `train-exemplars` = `size-pool-annotated-exemplars` | data | a value = one construction utterance rendered as an annotated exemplar (`content`, `task_target` = intent, `prior_score`); facet dimension `content` | **9,354** values, 9,354 facets, 37,407 source ids | `scripts/build_slurp_exemplar_pool_assets.py` (seed 20260823) | Solver `phase_supply` (M1) | **ADMITTED, provisional UNMET**; not in the default plan | release `171aa4a8…`, snapshot (content) `4c498dc0…` |
| `slot-audit-v1` | **repo** | per intent: every entity type attested with it and that type's row share, the share of its rows carrying no entity, plus two verbatim `date`/`time` convention statements. Counts and shares only — no filler, no sentence, no utterance id, no recording | 60 intents, 54 distinct types, 402 listed type rows, 2 conventions, over 9,354 construction utterances | `scripts/build_slurp_slot_audit_view.py` | Reviewer `B-DRAFT-REV` addition (B8b) | **held** | release `eaa2dd0d…`, snapshot `0cc3f96c…` (raw file bytes) |
| `scenario-hints-v1` | data | per intent: its construction neighbours (id, leakage share, counts) and the top cue words distinguishing it from each. Construction counts, leakage rates and words — no utterance id, no sentence, no filler | 60 intents, 44 with ≥1 neighbour, 81 neighbour pairs, 231 cue rows, 130 distinct cue words | `scripts/build_slurp_scenario_hints_view.py` | Solver `B-CAND-SOL` addition (B8c) | **built, unregistered** — no committed arm at `9418c69c` | release `44716de6…`, snapshot `079b2bf4…`, completion `e8024fe4…` |
| `saea-slurp-intent-candidates-v1` | data | intent-candidate values over the full governed TRAIN split | 60 / 60, **50,628** source ids | `scripts/slurp_kus4_prep.py` | none today | **unused; built without the 2026-09-13 exclusion** — see finding I-8 | no `release.json`, no `completion.json` |

### 4.3 Vector pins

Retrieval keys and queries are sealed files, read and hashed at binding time, never recomputed.

| Pin | Rows | sha256 | Used by |
| --- | ---: | --- | --- |
| `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl` | 60 | `76e8d16a…` | Perception facet (key) side |
| `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl` | 1,080 | `e7a5b226…` | Perception query (speech) side |
| `vectors/slurp-kus3/facet-vectors.jsonl` | 11,514, dim 2048 | `5dfe7523…` | exemplar facet side; scenario-hints neighbour measurement |
| `vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl` | 1,080 | `d0f06ed2…` | M1 exemplar query side |
| `vectors/slurp-exemplars-twin/query-vectors-speech-segments-deranged-v1.jsonl` | 1,080 | `92e7f72e…` | the B1 derangement twin (Sattolo, seed 20260917, 0 fixed points, `gold_read: false`) |

The embedding pass itself is spent and sealed (ledger row `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1`);
no builder and no runtime path re-encodes. `rails/phase_supply.py` names `embedding-server` as a kind
and **refuses** it, so an in-flight encoder contact is a named refusal rather than a generic one.

### 4.4 What changing a store costs

| Change | Cost |
| --- | --- |
| Re-pin an existing store to a new release/snapshot (e.g. slot contracts v1 → v2) | A `stores`-class re-pin arm (`switch.form: "repin"`, moving only `release` and `snapshot`); a one-factor cell on the sealed anchor; the harness-admission entry plus a replication obligation. This is exactly what B4b cost: two flights, about 4.6 GPU hours |
| Add a new store block (e.g. `train-exemplars`) | A `stores`-class arm whose OFF is the key's absence, a prepared-artifact rebuild over the **whole** roster (E10b), a new `prepared_phase_supply` pin, a wire check, a four-row smoke, a prompt-fit receipt, and a twin when the mechanism could be explained by presence alone |
| Change a retrieval knob (`k`, fusion, rank weights, `tau`) | The prepared artifact's identity changes, so the artifact is rebuilt and re-verified by `core.flight.repin`; the cell is a new arm even though no store byte moved |
| Rebuild a construction view (slot audit, scenario hints) | Model-free; the builder's own `--check` must reproduce the released bytes from the pool; the build receipt under `docs/receipts/knowledge/` and the config pins must be updated together; a repo-committed view additionally moves a git blob hash |

---

## 5. The optimisable space per node

Legend for the proposed status: **FREEZE** — the lock fixes this value; **OPEN** — admissible Stage-3
action space; **UNEXPLORED** — loader-admissible, never flown, no evidence, not in the action space
until the owner puts it there.

Reference points used in the "best arm" column: the sealed anchor
`SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` reads official pooled SLU-F1 **48.53**
/ intent **77.96**; the best measured combination is B5e (M1 + M4b) at **62.34 / 80.09** official, or
**63.78 / 81.85** when the admitted delivery node is applied. The development bar is SLU ≥ 64 and
intent ≥ 78, replicated (owner decisions 1, 23, 28 — a development bar, never compared with a
published test-set number).

### 5.1 Perception

| Knob | Default plan | Best arm | Type / admissible | Cost | Evidence | Proposed |
| --- | --- | --- | --- | --- | --- | --- |
| `roles.perception.max_iterations` | 1 | 1 | int ≥ 1 | +1 contact/row per unit | never varied | FREEZE |
| `phase_supply.perception.k` | 8 | 8 | int ≥ 1 | prompt tokens only | never varied | OPEN |
| `phase_supply.perception.fuse_policy` | `saea-fuse-associated-values-v1` | same | registry id | — | never varied | OPEN |
| `fuse_coverage {c, m, top_l}` | `{1, 8, 8}` | same | ints | prompt tokens | never varied | OPEN |
| `rank_policy` / `rank_weights` | `saea-rank-wcos-prior-agree-v1`, `{w_cos 1.0, w_prior 0.0, w_agree 0.0}` | same | registry id; three floats | none | never varied | OPEN |
| `tau` | 0.0 | same | float | none | never varied | OPEN |
| `query_source` modality | `speech` | same | `speech` \| `speech+state` | re-encode (refused: vectors are sealed) | owner ruling 2026-09-06 | FREEZE (`speech+state` needs its own sealed vectors and a cell) |
| `fill_params.max_candidates` | 3 | 3 | int, > 3 refused for SLURP (`candidate_semantic_supply.py:171`) | candidate-union size, Solver prompt | the five-candidate arm read `NOT_ADVANCED` (2026-09-16) | FREEZE at 3 |
| `fill_params.min_candidates` | 1 | 1 | int | — | never varied | UNEXPLORED |
| `fill_params.max_distinction_chars` | 128 | 128 | int | prompt tokens | never varied | UNEXPLORED |
| `fill_params.max_evidence_refs` / `max_unresolved_fields` | 0 / 0 | same | int | — | never varied | FREEZE |
| `fill_params.fallback_candidates` | absent | `["general_quirky"]` | ≤ `MAX_FALLBACK_CANDIDATES` unique legal ids; SLURP-only | appended when absent, never displacing a model candidate | **cell B4a, registered, not flown** | OPEN (pending B4a) |
| `knowledge_stores.intent-boundaries` pins | v1 | v2 in B4a/B4c | `{release, snapshot}` re-pin | re-pin + cell | B4c flies only if B4a admits (owner decision 9) | OPEN (pending) |

### 5.2 Solver

| Knob | Default plan | Best arm | Type / admissible | Cost | Evidence | Proposed |
| --- | --- | --- | --- | --- | --- | --- |
| `roles.solver.max_iterations` | 1 | 1 | int ≥ 1 | +1 contact/row per unit, multiplied by `samples` | never varied | FREEZE |
| `roles.solver.samples` | 1 | 1 | int 1–8; ≥2 requires `decoding_overrides` **and** `commit` | N = 5 costs 1.81× contacts, ceiling 11 → 19 | **B2 v3 NEUTRAL** (+0.06 SLU [-1.46, +1.60], intent +0.83 [-0.30, +1.88]); enters no plan because it does not lower cost | OPEN for Stage 3 (grouped rollouts are the sampler a training-free method needs), never as a default |
| `decoding_overrides.temperature` | n/a | 0.7 | float in (0, 2]; 0 only for an explicit `twin: "greedy-repeat"` | none per contact | B2 v3 | OPEN |
| `decoding_overrides.seed_offset` | n/a | 0 | int ≥ 0; seed = `fragment_seed + seed_offset + sample_index` | none | B2 v3 | OPEN |
| `commit.policy` | n/a | `saea-commit-plurality-support-v1` | must resolve in `core.base.COMMIT_POLICIES` | none | B2 v3 | OPEN |
| `commit.min_support` | n/a | 3 | int 1..samples | none | preregistered s = 3 of 5; an offline sensitivity table over s ∈ {2,3,4} exists and was never used for a verdict | OPEN |
| `commit.similarity_threshold` | n/a | 0.8 | float in (0, 1] | none | preregistered | OPEN |
| `candidate_supply.solver.max_candidates` | 3 | 3 | int ≤ 3 for SLURP | Solver prompt | tied to Perception's cap | FREEZE at 3 |
| `candidate_supply.solver.max_values_per_candidate` | 16 | 16 | positive int | Solver prompt | never varied | OPEN |
| `candidate_supply.solver.max_total_values` | 28 | 28 | positive int ≤ candidates × per-candidate | Solver prompt | never varied | OPEN |
| `candidate_supply.solver.projection_policy` | `bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1` | same | registry id | — | never varied | FREEZE |
| `candidate_supply.solver.rank_policy` / `fuse_policy` | `saea-ranked-candidate-round-robin-v1` / `saea-candidate-semantic-passthrough-v1` | same | registry ids | — | never varied | OPEN |
| `phase_supply.solver.k` (exemplars) | absent | **20** | int ≥ 1 | +7.37 % prompt tokens, +8 contacts | A2 chose 20 over {5, 8, 12}; **B1 ADMITTED** +12.61 [+10.54, +14.60] vs anchor, +7.83 [+5.85, +9.75] vs the derangement twin | OPEN — the single largest lever measured |
| `phase_supply.solver.fuse_policy` / `fuse_coverage` | absent | `saea-fuse-supplyfilter-v1`, `{c 20, m 20, top_l 20}` | registry id; ints | prompt tokens | B1 | OPEN |
| `phase_supply.solver.rank_weights` | absent | `{w_cos 1.0, w_prior 0.0, w_agree 0.0}` | three floats | none | B1; A2 found no memorisation channel (exact-text-neighbour rate reported) | OPEN |
| `phase_supply.solver.tau` | absent | 0.0 | float | none | B1 | OPEN |
| `native_episode.solver_hints.max_neighbours` | absent | — | int 1..3 (may only narrow the released table) | 578–1,608 characters (≈145–402 tokens); zero contacts | **B8c built, unregistered** | UNEXPLORED |
| `native_episode.solver_hints.max_cues` | absent | — | int 1..3 | same | B8c | UNEXPLORED |
| Instruction template | `probes/slurp_native_role_solver_v2.txt` | same | committed probe file | prompt tokens | never varied as a cell | FREEZE |

### 5.3 Reviewer

| Knob | Default plan | Best arm | Type / admissible | Cost | Evidence | Proposed |
| --- | --- | --- | --- | --- | --- | --- |
| `roles.reviewer.max_iterations` | 3 | 3 | int ≥ 1, or 0 only with planner 0 and `max_revisions` 0 | 3 of the 11 ceiling | Reviewer ×2 + Planner = 60 % of contacts, 0 intent saves, 1 harm per 1,000 rows; **M0 (loop off) HARMFUL** under the own null | FREEZE (the loop stays; owner decision 6) |
| `roles.reviewer.history_scope` | `full` | `full` | `full` \| `latest-solver-and-local-tools` (Reviewer only) | fewer prompt tokens | refuses to combine with `role_context` or a non-raw `context_policy` (`native_episode_config.py:552` and `:587`) | UNEXPLORED — and mutually exclusive with the NCP |
| `phase_material.reviewer.response_format_id` | `null` (prose) | `saea-review-findings-v1` | registered format id | none | 0 of 2,167 anchor Reviewer outputs parse under the registered findings parser; **cell B7r registered, not flown** | OPEN (pending B7r) |
| `phase_tools.reviewer.allowed_tools` | `["saea-tool-task-contract-v1"]` | same | tool ids; Reviewer and Planner only | the replayed contract echo is ~5,424 characters | B7c (tool-observation rewrite) held | OPEN |
| `native_episode.reviewer_audit.view` | absent | `slot-audit-v1` | the registered view id only | 687–787 characters (≈170–200 tokens); **zero contacts**, ceiling unmoved | **B8b held**; requires `reviewer:current-draft` at `structured` | UNEXPLORED |
| `…reviewer_audit.thresholds.empty_draft_min_entity_row_share` | — | 0.5 | float in [0, 1] | none | default; never varied | UNEXPLORED |
| `…reviewer_audit.thresholds.missing_common_min_row_share` | — | 0.5 | float in [0, 1] | none | default | UNEXPLORED |
| `…reviewer_audit.thresholds.profile_min_row_share` | — | 0.05 | float in [0, 1]; bounds what the profile lists, gates no flag | prompt length | default | UNEXPLORED |
| Instruction template | `probes/slurp_native_role_reviewer_v1.txt` | `…_findings_v1.txt` under B7r | committed probe file | prompt tokens | B7r | OPEN (pending B7r) |

### 5.4 Planner

| Knob | Default plan | Best arm | Type / admissible | Cost | Evidence | Proposed |
| --- | --- | --- | --- | --- | --- | --- |
| `roles.planner.max_iterations` | 1 | 1 | int ≥ 1 (0 only with reviewer 0 and revisions 0) | 1 of the 11 ceiling | Planner ACCEPTs 1,075/1,080 and spends 25.0 % of the prompt budget to emit a median of two tokens | FREEZE |
| `native_episode.max_revisions` | 1 | 1 | int ≥ 0; a refresh allowance must be ≤ it | (revisions+1) multiplies the per-revision sum | never varied except by M0 | FREEZE |
| `planner_output_format` | `exact-text` | `exact-text` | `exact-text` \| `json-action-v1` (the latter requires the registered Planner phase format) | none | never flown on SLURP | UNEXPLORED |
| `actions {accept, revise, acquire}` | `ACCEPT` / `REVISE` / `ACQUIRE` | same | three distinct non-empty strings, never the reserved illegal token | none | — | FREEZE (but see finding I-1) |
| `candidate_refresh {action, max_refreshes}` | absent | — | distinct action; 1 ≤ refreshes ≤ `max_revisions`; requires `candidate_state_selection: "latest"` | +`max_refreshes` × Perception contacts | a refresh fragment exists and has not flown on this base | UNEXPLORED |
| `exhaustion_policy` | `deliver-latest-solver` | same | `raise` \| `deliver-latest-solver` | none | retains the row at the revision limit | FREEZE |
| Planner brief `HARNESS CHECKS` block | absent (L0) | present at L1 | part of `ncp_slurp_planner_brief_v1.txt` | ≈ +110–170 tokens | owner decision 12(2) put it inside B7a rather than in its own cell | OPEN (pending B7a) |
| Instruction template | `probes/slurp_native_role_planner_v1.txt` (193 bytes) | same | committed probe file | prompt tokens | never varied | FREEZE |

### 5.5 Node context policy (cross-node)

| Knob | Default plan | Registered arm | Type / admissible | Cost | Evidence | Proposed |
| --- | --- | --- | --- | --- | --- | --- |
| `native_episode.context_policy` presence | **absent** (L0) | declared | absent \| `"raw"` \| object | absent composes to the pre-key config hash | **B7a v2 registered, not flown**; B7a v1 closed without a result after two aborts | OPEN |
| `context_policy.level` | — | `structured` | `raw` \| `structured` (a bare `"cleaned"` default is refused) | — | — | OPEN |
| `context_policy.policy_id` | — | `typed-slurp-node-context-v1` | string | — | — | FREEZE |
| per-boundary `level` (×12) | — | `structured` ×8, `raw` ×4 (tool-observation) | `raw` \| `structured` \| `cleaned` | L1 ≈ +400–600 characters worst case; `cleaned` adds `(max_revisions+1) × consumer.max_iterations` contacts | B7a (8 boundaries), B7c (the 4 tool ones), B7b (`planner:review-finding` cleaned) | OPEN — **this is the per-node composition surface owner decision 31 names** |
| per-boundary `on_parse_failure` | — | `raw` everywhere except `refuse` at `solver:plan-action` | `raw` \| `omit` \| `refuse` | — | `omit` would delete the review from the Planner's context on 100 % of rows, which B0 already measured as harmful; it is implementable and **not admitted for any SLURP boundary** without its own cell | FREEZE at `raw` / `refuse` |
| per-boundary `template` | — | the committed `probes/ncp_slurp_*.txt` defaults | must match the boundary's renderer key; hash-pinned in every receipt | prompt tokens | — | FREEZE (the template set), OPEN (which boundaries use one) |
| `cleaning.phase_id` | — | `context_clean_review` | string, never a program phase name | identity only | B7b held | UNEXPLORED |
| `cleaning.response_format_id` | — | `ncp-review-issues-v1` | resolves in `core.base.RESPONSE_FORMATS` | — | B7b held | UNEXPLORED |
| `cleaning.on_invalid` | — | `fallback-l1` | the only admissible value | — | one attempt, no retry | FREEZE |
| `producers.<class>.response_format_id` | — | `saea-review-findings-v1` for `review-finding` | must equal the producer phase's declared format | — | B7r | OPEN (pending B7r) |

### 5.6 Delivery, failure mode and serving

| Knob | Default plan | Type / admissible | Cost | Evidence | Proposed |
| --- | --- | --- | --- | --- | --- |
| `native_episode.deliver_normaliser` | `{"normaliser": "saea-deliver-normalise-v3"}` | absent, or a registered `DELIVERY_NORMALISERS` id declared for this carrier; refused beside the run-level `slurp_projection_v3_delivery` key and beside a grouped Solver | **zero contacts**, zero request bytes | **ADMITTED** (module M3, cell B8a): anchor +3.46 [+2.78, +4.18], B1 +1.53 [+1.05, +2.03], intent up on every base, 0 rows harmed; 103 of 1,080 rows changed | FREEZE armed |
| `native_episode.finite_completion_policy` | `deliver-latest-or-abstain` | `raise` \| `deliver-latest-or-abstain` | zero request bytes | **NEUTRAL**; no sealed SLURP native contact ever met a finite completion, and the B7a v1 recovery died because the key was absent | FREEZE armed, and **require it in every new fragment** (finding I-3) |
| `native_episode.review_loop` | `"on"` | `"on"` \| `"off"`; validated against the three loop leaves, renders no request byte | none | **NEUTRAL** (the marker); the loop itself is retained because M0 is HARMFUL | FREEZE |
| `serving_slots` / `serving_slot_tokens` | 4 / 24576 | ints matching the resident geometry | the geometry a flight may attach to | 9,708 tokens of headroom at the worst observed contact | FREEZE |
| `decoding_params.max_tokens` | 512 | int | output length; a 512-token Reviewer completion is what E13 retains | the max512 geometry is the program's own | FREEZE |
| `decoding_params.temperature` / `seed` | 0 / 20260913 | float / int | none | greedy is not bitwise reproducible across batch compositions; comparators are sealed bytes, never re-flown | FREEZE |
| `obs_prefetch_depth` (run class) | absent | absent \| int | +17 % throughput at depth 1 on Earnings | NEUTRAL on E21; depth ≥2 unreceipted; never flown on SLURP | UNEXPLORED |
| `scorers` | `["slurp-slu-official-train", "cost"]` | registry ids | one score per complete manifest | owner decision 23: the official unprojected number is the bar | FREEZE |

### 5.7 Summary of the proposed action space

The companion JSON enumerates **72 knobs** across nine nodes (Solver 21, Perception 15, node
context policy 10, Reviewer 9, Planner 7, serving 5, episode 2, run 2, delivery 1). Their proposed
partition is **30 OPEN / 28 FREEZE / 14 UNEXPLORED**.

**OPEN (the Stage-3 action space, 30 knobs):** Perception `k`, fuse policy, fuse coverage, rank
policy, rank weights, `tau`, `fallback_candidates` and the intent-store pin; Solver `samples`,
temperature, `seed_offset`, commit policy, `min_support`, `similarity_threshold`,
`max_values_per_candidate`, `max_total_values`, candidate rank and fuse policy, exemplar `k`, exemplar
fuse policy, exemplar fuse coverage, exemplar rank weights and exemplar `tau`; Reviewer response
format, tool exposure and instruction template; the NCP presence, its default level, the per-boundary
level map and the producer response format.

**FREEZE (28 knobs and objects):** the role set and every `max_iterations`; `max_revisions`; the
action triple; `exhaustion_policy`; the Perception, Solver and Planner instruction templates that have
never been a cell; the candidate cap of 3; the projection policy; the query modality; the
parse-failure rules; the template set; the policy id; the cleaning fallback rule; the two zero-evidence
Perception caps (`max_evidence_refs`, `max_unresolved_fields`); the delivery node armed; the
finite-completion policy armed; the review-loop marker; the serving geometry (slots, slot tokens); the
decoding block (`max_tokens`, temperature, seed); and the scorer list.

**UNEXPLORED (14 knobs):** `min_candidates`, `max_distinction_chars`, Reviewer `history_scope`, the
`reviewer_audit` view and its three thresholds, the two `solver_hints` bounds,
`planner_output_format`, `candidate_refresh`, the two `cleaning` identity fields, and
`obs_prefetch_depth`.

---

## 6. Inconsistencies found, and the questions the owner must answer

### 6.1 Inconsistencies between the specs, the configs and the code

**I-1 — `ACQUIRE` is a legal Planner action with no route at revision 0, and it aborts the flight.**
`reproduction/ojw/native_episode.py:352-358` puts `self._actions.acquire` in the legal set under
`exact-text` (the flown format), so an `ACQUIRE` token is *not* the E8c illegal disposition. No
acquisition node is ever built for SLURP (`rails/runner.py` never sets `NativeEpisodeNodes.acquisition`),
so `native_episode.py:947-958` routes `ACQUIRE` at a non-terminal revision to
`_Exhausted("episode has no configured analytical acquisition role")`, and `_Exhausted.invoke`
(`native_episode.py:455-463`) **raises**, taking the campaign with it — precisely the failure class
E8c was written to remove. At the terminal revision the same token routes to `_TerminalDelivery` and
the row is retained. The prompt never advertises `ACQUIRE` (`rails/runner.py:2044-2047`) and the
sealed anchor's 1,085 Planner responses never produced it, but neither did they ever produce `REJECT`
before B7a v1 died on one.
**Status: fixed by E15 (commit 6d9ef288); see section 17 of `docs/superpowers/specs/2026-09-17-node-context-policy-design.md`.**

**I-2 — the L2 fragment is not one factor against its own comparator.**
`configs/baseline/slurp-native-anchor-ncp-l2-review-clean-train-fold-a-v1.json` differs from its
declared base `…ncp-l1-train-fold-a-v2.json` in **two** episode keys, not one: the cleaning block at
`planner:review-finding`, and the **absence** of `native_episode.finite_completion_policy`, which the
L1 v2 fragment carries as `deliver-latest-or-abstain`. The design (section 11) says B7b's "whole
config difference from B7a is that one boundary entry".

**I-3 — the forward queue's fragments disagree about the finite-completion key.** Of the registered or
held SLURP fragments, `ncp-l1-*-v2`, `ncp-l1-reviewer-format-*`, `ncp-l1-reviewer-audit-*`,
`ncp-l1-tool-obs-*`, `fallback-quirky-intent-v2-*` and `intent-store-v2-*` carry
`finite_completion_policy: "deliver-latest-or-abstain"`; `ncp-l2-review-clean-*` (both arms) does not.
The key is the NEUTRAL retention rule whose absence killed the B7a v1 recovery at 1,451 contacts.

**I-4 — `EPISODE_LEVEL_SWITCH_KEYS` has seven members and its docstring says three.**
`rails/config_tables.py:287-290`: "The closed allowlist of `episode`-class switch keys. **All three**
are dotted paths … admitting **a fourth** is a code change with a test". The frozenset at
`config_tables.py:361-369` holds seven. `is_episode_null_arm`'s docstring
(`config_tables.py:1195`) repeats it: "because **the three** today mean different things". The
program spec repeats the same staleness at `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md:205`
("the fourth **and last**") and `:308` ("the FIFTH **and last**").

**I-5 — `NativeEpisodeConfig.context_policy_json` contradicts the loader that fills it.** The field
comment (`rails/native_episode_config.py:277-282`) says it is "the canonical text of a
`native_episode.context_policy` whose effective level is NOT raw. An absent key, the literal `"raw"`
and an all-raw object are ONE thing here — `None`". The loader
(`native_episode_config.py:578-580`) assigns it for **any** declared `context_policy`, including an
all-raw one — deliberately, because NCP design note E8a(4) makes a declared all-raw arm emit
`level: "raw"` receipt rows. `is_episode_null_arm`'s docstring (`config_tables.py:1204`) carries
the same wrong claim: "an all-raw declaration reaches the runtime as no policy at all". The behaviour
is right; two docstrings describe the opposite.

**I-6 — the program spec's module table names the wrong switch classes.**
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md:35-40` assigns M0 to `run`, M1 to
`knowledge_views`, M2 to `judges`, and M4a/M4b to `knowledge_views`. The receipt
`docs/receipts/harness-admission.json` registers them as `episode`
(`native_episode.review_loop`), `stores` (`knowledge_stores.train-exemplars`), `episode`
(`native_episode.roles.solver`) and `stores` (`knowledge_stores.slot-contracts`, `form: "repin"`)
respectively — and `config_tables.py` explains why a store can never be a `knowledge_views` entry.
The spec's own Phase B outcome line (`:411`) already states the correct class for M2.

**I-7 — the spec spells the fallback key in the singular.** Spec lines 39 and 401 write
`fallback_candidate`; the config key is `fallback_candidates` (plural), in both
`phase_material.perception.fill_params` and `knowledge_stores.<store>.candidate_supply.<phase>`.

**I-8 — one store on disk was built without the 2026-09-13 exclusion.**
`knowledge/slurp/saea-slurp-intent-candidates-v1` (data root) carries
`source_split_identity_hash 6a6677e9…` and 50,628 source sample ids — the full governed TRAIN split,
with no Fold A / Fold B / DEV-1000 exclusion — and has neither a `release.json` nor a
`completion.json` nor a file under `docs/receipts/knowledge/`. It is consumed by no current config.

**I-9 — the release-pins file is stale as a coverage document.**
`docs/readiness/2026-09-13-slurp-semantic-store-release-pins-v1.json` pins exactly two stores
(`intent-boundaries-v1`, `slot-contracts-v1`). Eight further stores and every vector pin exist on disk
and are pinned only inside per-cell configs and per-store receipts, never in one place.

**I-10 — two incompatible `snapshot_sha256` conventions.** For the authored family
(`intent-boundaries-*`, `slot-contracts-*`, `size-pool-annotated-exemplars`)
`release.json.snapshot_sha256` is the **canonical content hash** of the snapshot object, and the raw
file byte hash lives in `completion.json.snapshot_file_sha256`. For the view family
(`slot-audit-v1`, `scenario-hints-v1`) it is the **raw file byte hash**. A gate that hashes
`snapshot.json` bytes and compares against `release.json.snapshot_sha256` passes for the views and
fails for all four authored stores. (The companion JSON records both values where they differ.)

**I-11 — the default plan's `preparation_source_receipts` still pin slot contracts v1.** The plan
re-pins `knowledge_stores.slot-contracts` to v2 but its `preparation_source_receipts` list still names
`knowledge/slurp/semantic/slot-contracts-v1/release.json` and `…/completion.json`. This is arguably
correct provenance — the prepared artifact was prepared under v1, and slot contracts feed
`candidate_supply`, not the prepared phase supply — but it reads as a stale pin and no note says which.

**I-12 — the default plan arms four modules and its receipt names three.**
`docs/receipts/harness-admission.json` `default_plans[1].modules` lists the review loop, slot store v2
and the delivery node; the fragment also arms `native_episode.finite_completion_policy`, which appears
only in the free-text `default_plans_note`. The gate verifies arming from the fragment, so it passes;
the prose is what is short.

**I-13 — two design statements were superseded and not amended.** NCP design section 11 (`:597`)
requires "projection v3 applied to every official number", which owner decision 23 revised (the
official unprojected number is what the bar reads; v3 is a diagnostic). Program spec `:427` still
records decision 7's reading of v3 as "the fixed post-processing of every official number". Program
spec `:38` still places M3 in the scorer, which E11/B8a moved into the agent.

**I-14 — the NCP design's boundary table lists nine rows for twelve boundaries.** Design section 3
writes the tool-observation boundary once as `B-TOOL-*`; the code
(`node_context_policy.py:181-194`) enumerates four of them, and cell B7c's fragment moves all four.

**I-15 — a builder docstring names an output file that does not exist.**
`scripts/build_slurp_exemplar_pool_assets.py` documents the exemplar query vectors as
`query-vectors-speech-segments-content-v1.jsonl`; the constant and the file on disk are
`query-vectors-speech-content-v1.jsonl` (`d0f06ed2…`).

### 6.2 Questions the owner must answer to approve the lock

**Q1 (I-1, blocking).** Should `ACQUIRE` be removed from the SLURP action triple, or should an
unrouted-but-registered action be sealed like an illegal one instead of raising? The lock should not
freeze a graph that still contains one token capable of killing a 3.4-GPU-hour flight. Recommendation:
treat a registered action with no route exactly as E8c treats an unregistered one, and keep the triple
(the schema requires three distinct actions).

**Q2 (I-2, I-3, blocking for B7b).** Is `native_episode.finite_completion_policy: "deliver-latest-or-abstain"`
mandatory in every fragment registered from now on? If yes, the L2 fragments must be re-pinned before
B7b flies, and B7b's comparator statement must say whether the key's presence is part of the contrast.

**Q3 (decision 31).** Section 5 proposes the per-node map the owner's composition rule asks for:
Perception = candidate supply + intent store + fallback; Solver = exemplars + scenario hints +
sampling/commit; Reviewer = response format + slot audit + tools; Planner = brief composition;
delivery = the normaliser; NCP = every boundary. Two modules compete for the Solver boundary
(exemplar supply M1 and the B8c hints, both typed content at `B-CAND-SOL`/`phase_supply`) and two for
the Reviewer (the B7r format and the B8b audit). Does the owner accept this map as the B5b node map,
and should the competing pairs fly as paired placement cells rather than be stacked?

**Q4 (module M1).** M1 is the largest measured effect (+12.61 pp) and its `provisional.state` is
**UNMET**: the named replication route was the B5e/B5er pair, B5e did not separate M1 from B1 and
B5er was not registered. Does the lock (a) carry M1 as admitted-but-unreplicated and exclude it from
the default plan until B5b replicates it, or (b) authorise a request-identical B1 replicate (about
3.7 GPU hours) before the lock closes?

**Q5 (margins).** Three margin regimes are in force: the retired imported DEV-1000 half-widths, B0r's
own null (SLU 1.1218 / intent 1.0051, measured on the review-**off** configuration) and B4b-rep's own
null (SLU 1.3222 / intent 1.0682, the only one measured on an admitted configuration). Does the lock
fix the rule "a configuration's own request-identical replicate supplies the margins for contrasts
involving it, and B0r's are the fallback"?

**Q6 (I-8).** Should `saea-slurp-intent-candidates-v1` be deleted, re-built under the 2026-09-13
exclusion, or recorded as a quarantined artifact that no config may reference? It is the only store on
disk built on the unexcluded TRAIN split.

**Q7 (I-9, I-10).** Should the lock supersede
`docs/readiness/2026-09-13-slurp-semantic-store-release-pins-v1.json` with one pins document covering
all ten stores and every vector, recording for each which hash convention its `snapshot_sha256`
follows?

**Q8 (section 1.2).** Does the owner accept the FREEZE / OPEN / UNEXPLORED partition of section 5.7 as
the definition of the Stage-3 action space — in particular that grouped Solver sampling stays OPEN as
the rollout mechanism a training-free method needs, although B2 v3 read NEUTRAL as a standalone module?

**Q9 (scope of the freeze).** Does the lock freeze the three never-varied instruction templates
(Perception v3, Solver v2, Planner v1) and the shared task contract v3, or are prompt texts part of the
optimisable space? They are the largest untouched surface in the system and no cell has ever moved one.

**Q10 (the lock's own gate).** Should `docs/receipts/slurp-agent-base-lock-v1-draft.json`, once
approved, become a checked receipt — a `scripts/checks/agent_base_lock_check.py` that compares the tree
against the approved graph, boundaries, stores and knob statuses — or stay a document? Recommendation:
a gate, because a prose lock that nothing enforces is what sections 6.1's fifteen findings are made of.

---

## 7. What this draft does not do

- It proposes **no Stage-3 framework**: no state, no action, no reward, no update rule, no rollout
  design. Decision 33 orders the lock first, and the framework is the conversation that follows the
  owner's approval of this document.
- It **registers no cell**, writes no preregistration, opens no exposure row, composes no
  `contracts.ExecutionPlan` and makes no model, tool, scorer, tokenizer or encoder contact.
- It **changes no code, no config, no knowledge store, no receipt and no ledger row.** The only files
  it adds are this draft and its machine-readable companion.
- It **decides nothing.** Every FREEZE / OPEN / UNEXPLORED value in section 5 is a proposal; every
  finding in section 6.1 is reported, not repaired; every question in section 6.2 is open.
- It **makes no claim** about task quality. Every number quoted is read from a sealed verdict and is a
  **development** number on TRAIN Fold A or DEV-1000, drawn from the training data, on a roster this
  program has optimised against. Owner decision 28 forbids comparing any of them with a published
  test-set baseline, and this draft does not.
