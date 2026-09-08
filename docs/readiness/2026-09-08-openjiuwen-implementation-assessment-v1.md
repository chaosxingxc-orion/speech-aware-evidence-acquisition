# Assessment: can the existing openJiuwen implementation carry the four-agent loop? (2026-09-08, v1)

**Status: READ-ONLY REVIEW. No code changed, no model contacted, no commit.** Read in the worktree
`D:\chao_workspace\saea-worktrees\wt-agentsys` (branch `wt/agentsys`, HEAD `da88f404`); the installed
framework is `openjiuwen==0.1.16.post2` in `~/.venvs/speechrl`. Every path below is relative to
`src/speech_aware_evidence_acquisition/` unless it starts with `configs/`, `docs/`, `scripts/` or `tests/`.

Owner instruction being answered (2026-09-08): *we already have an openJiuwen-based implementation;
analyse whether the existing engineering solution is reasonable; do not build another one unless the
previous work is completely unreusable.*

**Verdict up front: the openJiuwen agent layer is reasonable and reusable — nothing is unreusable.**
It already carries three of the four agents and the loop that connects them; what is missing is a
Reviewer seam, a mutable observation inside a trajectory, and a tool layer — three additive changes
inside the existing bases (26–34 agent-hours), no new pipeline and no rebuild.

**The real problem is not the openJiuwen layer; it is that only part of the study flies through it.**
Three run drivers, three executor names, four spellings of the executor key, 70 configs on a
`policy: "fixed"` path that never reaches the graph at all, and all of Earnings outside it. The owner's
2026-09-08 addendum — standardize on `rails`, one harness reused across tasks — is therefore a
*consolidation* task (register, port, dispose: §6, changes #7–#9), not a rebuild task. The repo's own
ratchet baseline already enumerates every offender.

---

## 0. What exists, in one paragraph

There are **two** openJiuwen graphs, both built on `LoopGroup` + `AdvancedLoopComponent` +
`FuncCondition` over the framework's Pregel engine, and both reached only through a lazy import seam
so `openjiuwen` never enters `pyproject.toml`:

1. **The obs graph** (`reproduction/ojw/runner.py:105-165`) —
   `start → AdvancedLoopComponent(LoopGroup[feed → asr → boundary → accept], FuncCondition(state.should_continue)) → end`.
   Policy id `obs-agent-loop-ojw` (`reproduction/ojw/__init__.py:37`), registered in the one policy
   registry (`core/policies.py:630`), driven by `core.driver.run_experiment`.
2. **The speech-native agent graph** (`reproduction/ojw/runner.py:297-354`) —
   `agent_start → AdvancedLoopComponent(LoopGroup[prepare_agent_wave → agent_contact_0..N → aggregate_agent_wave], FuncCondition(should_continue)) → agent_end`.
   Executor id `openjiuwen-workflow-v1`, driven by `rails.runner.run_speech_native_agent_loop`
   (`rails/runner.py:1895`, dispatch at `:2089`, body at `:1382`), which is what
   `rails.phase_runner` (`rails/phase_runner.py:81`, `DEFAULT_AGENT_EXECUTOR_ID = "openjiuwen-workflow-v1"`)
   and `core.flight.FlightRuntime._dispatch_phase_program` (`core/flight/runtime.py:3089`) call.

The single-door red line holds in both: `FrozenCoreASR` (`reproduction/ojw/components.py:188`) and
`ExecuteAgentContact` (`components.py:506` → `rails/runner.py:1537 invoke_contact` →
`core_client.complete`) are the only model doors, and no framework LLM client is imported anywhere
(`grep openjiuwen` over `src/` returns only workflow/session/graph/tool-free imports in
`reproduction/ojw/components.py:55-58` and `runner.py:42-58`).

---

## 1. Map: the four agents and the three mode tables against the code

### 1.1 Agents

| design agent | status | what implements it | citation |
|---|---|---|---|
| **Planner** | **PARTIAL** — a fixed, config-declared plan; no runtime decision, no per-episode call budget enforced by a planner | `PhaseProgram` / `PhaseSpec` (a frozen ordered phase list loaded from `configs/policy/phase-*.json`), plus `ObsLoopConfig.from_values` for the obs side | `rails/controllers.py:176-291`, `:295 load_phase_program`, `configs/policy/phase-*.json` (6 programs), `reproduction/obs_loop.py:642-890` |
| | ceiling: `PhaseProgram.max_contacts` is validated as `int >= len(phases)`; `run_speech_native_agent_loop(max_contacts=…)` enforces it per trajectory in `schedule_wave` | | `rails/controllers.py:221,241-249`, `rails/runner.py:1436-1440` |
| | the only *dynamic* planner decision that exists: `stop_policy` under `stop_rule="stop-policy-optional-early-exit"` | | `rails/controllers.py:154-158` (`PHASE_PROGRAM_STOP_RULES`), `:588-594` |
| **Observer** | **PARTIAL — split across two harnesses that do not meet.** Everything real (unit plan, tail, VAD, selective re-listen) lives on the **plain** `obs-agent-loop` family; the ojw agent graph sees one immutable speech packet | plain: `reproduction/obs_loop.py` (`_slice_parallel_pass:981`, unit plan `:797-841`, tail-silence `:689-698`, `OBS_TAIL_FRAME_V1:121`); ojw obs graph: `FeedBuffer` (`components.py:115`); ojw agent graph: nothing — the observation is `QueryState.speech_packet_id/sha256` fixed for the whole trajectory | see §2.3 |
| **Solver** | **PRESENT** | `FrozenCoreASR` on the obs graph; `ExecuteAgentContact` + `rails/runner.py:invoke_contact` on the agent graph; `EvidenceAgentController._dispatch` builds the per-phase contact | `components.py:188`, `:506`; `rails/runner.py:1537-1571`; `rails/controllers.py:508-543` |
| **Reviewer** | **ABSENT as a loop participant.** Judges exist as *offline* instruments and as *post-response* rules; none of them runs as a graph node, and no controller emits the `verify` transition the vocabulary already defines | judges: `core/repair_alignment.py` (substitution-only), `core/flag_sources.py` (roster-band), `core/replay_signals.py`, `core/span_surgery.py`, `reproduction/slurp_official_eval.py` projection; the transition kind `"verify"` is defined and validated but has **no producer** | `rails/knowledge.py:41-51` (`AGENT_ACTION_KINDS` includes `"verify"`), `:1024` (`verify must use at least one previously supplied value`); grep for `action_kind="verify"` across `rails/` + `core/` → 0 hits |

The Reviewer's *shape* is nonetheless already expressible: `EvidenceAgentController.advance`
(`rails/controllers.py:552-716`) is exactly a "score the response, then decide loop or commit" hook —
it seals the response as an `AgentStateArtifact`, consults `stop_policy`, resolves a supply, and emits
either a `stop` transition (`:673-691`) or an `acquire`/`organize` transition plus the next contact
(`:645-716`). A Reviewer is a callable injected beside `stop_policy`/`supply_for_phase`, not a new class.

### 1.2 Observe modes

| design entry | status | implementation | citation |
|---|---|---|---|
| fixed 90-s windows | PRESENT (plain + ojw obs graph) | `ObsLoopConfig.buffer_seconds`; `FeedBuffer` cuts from clock-derived `window_frames` | `reproduction/obs_loop.py:642-660`; `reproduction/ojw/components.py:115-187` |
| speaker-turn units (diarization) | PRESENT on the **plain policy only**; the ojw executor **refuses** it by name | `obs_unit_plan` + `obs_unit_plan_sha256`, `_load_unit_plan`, `PlannedUnit`; ojw refusal | `reproduction/obs_loop.py:436-600, :797-841`; refusal at `reproduction/ojw/policy.py:135-143` |
| silence tail | PRESENT on the plain policy; the ojw obs graph shares the same `encode_slice` so the bytes match | `obs_slice_tail_silence_seconds` → `obs_audio.append_tail_silence` / `tail_silence_samples` | `reproduction/obs_loop.py:689-698`; `reproduction/obs_audio.py:196-253`; equivalence scenario `tail-silence` in `tests/unit/test_obs_loop_ojw.py` |
| 16 kHz standardisation | PRESENT | `SLICE_SAMPLE_RATE_HZ`, `decode_parent_pcm`, `rms_normalize` | `reproduction/obs_loop.py` (`SLICE_SAMPLE_RATE_HZ`), `reproduction/obs_audio.py:173` |
| ESB clips through the slice path | PRESENT | `reproduction/esb_reference.py`, `core/model/slices.py` registry | `reproduction/esb_reference.py` |
| enhancement for noisy input | **ABSENT** (design says "named, not built") | — | — |
| selective re-listen of flagged spans | PRESENT on `obs-replay-loop` **only**, never on any openJiuwen path | LOCATE + RETRIEVE + REPLAY sections; `core.span_surgery.align_words`/`cut_span` re-cut with `replay_context_s` context, registered through the same `SliceRegistry` | `reproduction/replay_loop.py:1-9` (policy summary), `:134-160` (LOCATE), `:151-200` (RETRIEVE/REPLAY); policy id at `:366`; registered `core/policies.py:645` |

**Diarization is a read-time artifact reader, not a runnable tool row in this repo.**
`reproduction/diarization.py:14-24` states it "deliberately registers nothing in a `core.base`
registry … it is a read-time stratification input". The pinned Sortformer v2 payloads live in the
umbrella lock (`docs/datasets.lock.json` `meeting-minutes-tools`), consumed by the separate
meeting-minutes paper topic, not by this repo's loop.

### 1.3 Knowledge views

| design entry | status | implementation | citation |
|---|---|---|---|
| class lists / brief | PRESENT | `EVIDENCE_SOURCES` entries `conec-class-lists`, `conec-names`, `conec-bias-list`, `e22-metadata-brief`, … | `core/evidence.py:1328-1347` |
| TRAIN slot schema per intent | PRESENT | `PHASE_STATE_FILLS` `_slurp_intent_slot_schema_state_fill` | `rails/phase_material.py:140,206,246` |
| KB facets | PRESENT | `KnowledgeProvider` subclass `KbFacetProvider`, registered `kb-facet-v1` | `rails/knowledge_provider.py:508`, `:1089` |
| slot fillers | PRESENT | KU-S3 path: `phase-slots-given-intent-supplied-v1` + `phase_supply` | `configs/policy/phase-slots-given-intent-supplied-v1.json`; `rails/phase_supply.py:1-45` |
| derived-candidates bank | PRESENT | `EVIDENCE_SOURCES["derived-candidates"]`, `core/candidate_materializer.py` | `core/evidence.py:1331` |
| dense centroids | PRESENT (beyond the design table) | `DenseCentroidProvider`, registered `dense-centroid-v1` | `rails/knowledge_provider.py:665`, `:1091` |
| ConEC context view | PRESENT | `ConecContextProvider`, registered `conec-context-v1` | `rails/knowledge_provider.py:861`, `:1093` |
| same-speaker exemplar index (MF-8) | **ABSENT** (design says "named, not built"); the *bank* plumbing exists (`core/exemplars.py`, `SampleContext.exemplar_bank`) | | `core/exemplars.py`; `reproduction/replay_loop.py` REPLAY tier-2 |
| device inventory / legal-intent state | **ABSENT** | | — |
| speaker roles from diarization + brief | PARTIAL — `speaker_roster_mapping` exists but refuses to invent names and is not wired to any loop | | `reproduction/diarization.py:36-46` |

Knowledge views are supplied to the loop **only as traced `QueryState` entries**, never as prompt
text — this is the E6 rule and it is enforced: `_agent_messages` renders visible facets/values as typed
content blocks with `evidence_id`/`source_uri`/`knowledge_role` (`rails/runner.py:1085-1113`), and the
phase instruction is byte-identical supplied or not (`rails/controllers.py:60-77`, `:589-597`).

### 1.4 Judges

| design entry | status | implementation | citation |
|---|---|---|---|
| legal-label projection | PRESENT, but as a **scorer** (post-hoc), not a loop judge | `SCORERS["slurp-slu-projected-v2"]` etc. | `core/scorers.py:749-750` |
| schema conformance | PRESENT as *constrained decoding*, not as a judge | `RESPONSE_FORMATS["select-response-v1"]`, `["fill-response-v1"]`; `PhaseSpec.response_format_id` | `rails/controllers.py:1043-1045`, `:180` |
| substitution-only delivery rule | PRESENT as a registered **response postprocessor**, wired only into the plain `obs-repair-loop` window hook | `RESPONSE_POSTPROCESSORS["e21-entity-repair-substitutions-v1"]` | `core/base.py:110`, `core/policies.py:661-663`, `core/repair_alignment.py:1-40`, consumer `reproduction/repair_loop.py:208` |
| numeric-format checks | PRESENT as a scorer | `SCORERS["numeric-value-accuracy-v1"]` | `core/scorers.py:1183` |
| brief-name near-miss detector | PRESENT as a **flag source** on the replay policy (`roster-band`), not as a registered judge | `core.flag_sources.roster_band_flags` | `core/flag_sources.py:1-40`; consumer `reproduction/replay_loop.py:90-110` |
| decode-confidence signals from the trace | PRESENT on the replay policy (`replay_flag_source: "logprob"`) | `core.replay_signals.flag_spans`, `slice_logprob_stats` | `reproduction/replay_loop.py:56-80` |
| acoustic re-check through a pinned embedder | PARTIAL — `rails/embedding_client.py`, `rails/local_encoder_client.py` exist; no judge uses them | | `rails/embedding_client.py`, `rails/local_encoder_client.py` |
| core-as-critic phase | **ABSENT** (design defers it to owner confirmation) | | — |

**There is no judge registry.** Judges are spread across `SCORERS` (post-hoc, explicitly forbidden
inside the loop), `RESPONSE_POSTPROCESSORS` (one entry, plain-policy only) and plain functions in
`core/flag_sources.py` / `core/replay_signals.py` / `core/span_surgery.py` reachable only from
`reproduction/replay_loop.py`.

### 1.5 Which carriers run through the openJiuwen executor today

There are **three** run entry points (`core/driver/cli.py:903 run`, `:1114 speech-native-profile`,
`:1276 flight`) and **three** executor names. "The openJiuwen executor" names two unrelated
integrations, and a third executor is neither of them.

Distinct `"policy"` values across `configs/baseline` + `configs/experiment` (226 + 170 files):
`fixed` **70**, `obs-agent-loop` **40**, `phase-slots-given-intent-v1` **18**, `obs-replay-loop` **17**,
`obs-agent-loop-ojw` **13**, `obs-repair-loop` **4**, `phase-slots-given-intent-supplied-v1` **3**,
`phase-direct-only-v1` **2**, plus ~19 one-off carrier-specific ids (see §6.3).

| carrier / cell family | entry point | executor | citation |
|---|---|---|---|
| **Audio2Tool** AgentLoop family (g3–g8, select-then-fill, semantic, cascades, self-consistency, factor-top1) | `flight` → `FlightRuntime._dispatch_phase_program` → `phase_runner` → `run_speech_native_agent_loop`, or a `rails/probes/*_flight.py` launcher | **`openjiuwen-workflow-v1`**, declared explicitly (23 baselines + 4 experiments) | `configs/baseline/a2t-g5-exhaustive-family-agentloop.json:12`, `a2t-phase-select-then-fill-v1.json:8`, `a2t-semantic-agentloop-top16.json:5`; `rails/probes/a2t_select_fill_agentloop.py:50`, `a2t_semantic_agentloop.py:44`, `a2t_self_consistency_flight.py:39`, `a2t_self_transcript_cascade_flight.py:31`, `a2t_contract_preserving_cascade_flight.py:41` |
| **SLURP** KB alpha-blend campaign/lock family | `flight` / launcher | **`openjiuwen-workflow-v1`**, declared explicitly | `configs/baseline/slurp-dev{100,500,1000}-kb-alpha-blend.json:15`; `configs/experiment/slurp-dev1000-baseline-lock-v1.json:95`, `slurp-dev500-confirmatory-campaign-v1.json:62` |
| **SLURP** phase-program cells (KC-S1b, KU-S3, MF-5 direct-only, evolved slot schema) | `flight` → `_dispatch_phase_program` → `run_program` / `run_continuous_program` | **`openjiuwen-workflow-v1` by runner default, with no config key at all** | `rails/phase_runner.py:81`; `configs/baseline/slurp-phase-direct-only-v1.json` and `slurp-phase-slots-given-intent-v1.json:3` declare no executor |
| **SLURP** `speech-native-*` M-series (32 baselines, all `policy: "fixed"`) | `speech-native-profile` → `core/driver/speech_native.py` | **`legacy-contact-dag-v1`** — a third executor, taken by default because none of the 32 fragments sets the key | `core/driver/speech_native.py:11795-11805` (`values.get("speech_native_agent_executor_id", "legacy-contact-dag-v1")`), `:13099-13101` |
| **Earnings-21** wave-1 substrate + R4 context-dose ladder (13 baselines) | `run` → `POLICIES.resolve` | **openJiuwen, but the *obs* graph**, not the agent graph | `configs/baseline/{a1a-fixed-window,a2a-buffer90,a3a-loudnorm,bare-core,bias-phrases,fixed-legal-context,mismatched-evidence}-ojw.json:3`; `configs/experiment/wave1-substrate.json:4`, `r4-context-dose.json:4` |
| **Earnings-21** everything since (KC-E1, KC-E1f, OBS-E1, the replay/repair ladder, the 44-call direct baseline) | `run` → `POLICIES.resolve` | **none** — plain Python (`obs-agent-loop` 40, `obs-replay-loop` 17, `obs-repair-loop` 4) | `core/driver/run.py:530-541, :721, :755`; `core/policies.py:615,645,679` |
| **Earnings-22** (19 configs) | `flight` | **none** — `policy: "fixed"` throughout, zero agent loop | `configs/experiment/e22-dev-encoding-bx-v1.json:39` |

So: **the openJiuwen *agent* graph is an Audio2Tool + SLURP-subset construct.** Earnings never enters
it. The openJiuwen *obs* graph is Earnings-only, is used by 13 configs that all predate 2026-08-11, and
expresses no agent loop beyond feed→asr→boundary→accept. A large SLURP family and all of Earnings-22
run on neither.

Two config-level defects worth naming, both found by the sweep:

* `configs/baseline/a2t-direct-packets.json` declares `"policy": "fixed"` (line 3) **and**
  `"speech_native_agent_executor_id": "openjiuwen-workflow-v1"` (line 8). `"fixed"` never reaches the
  AgentLoop dispatcher (`core/flight/runtime.py:3300-3305`), so the executor key is inert — a config
  that reads as if it flies the agent graph and does not. Same in `a2t-direct-packets-native-tools.json:8`.
* The executor key has **four** spellings in `configs/`: `speech_native_agent_executor_id` (21),
  `agent_executor_id` (7), `executor_id` (3), `agent_executor` (1). `reference-trajectory-v1` appears
  **zero** times in `configs/` — it is chosen only by calling code.

The plain-Python reference has **two distinct residual roles**, and they are not the same thing:

* `reproduction.obs_loop.ObsAgentLoopPolicy` — the **reference fixture** for the obs graph
  (`docs/readiness/2026-08-08-openjiuwen-adoption.md:40-42`), and simultaneously the **only** executor
  that implements the unit plan and the window hook, so it is also the production path for OBS-E1 and
  KC-E1f. It is no longer only a fixture.
* `agent_executor_id="reference-trajectory-v1"` — a dependency-free equivalence oracle, hard-restricted
  to `execution_profile == "model-free-check"` and refused with the real `FrozenCoreClient`
  (`rails/runner.py:1988-1997`).

A third, non-openJiuwen path also exists and is worth naming because CLAUDE.md's "same harness" rule
targets it: `policy: "fixed"` in a baseline fragment dispatches through
`FlightRuntime._dispatch_fixed_policy` (`core/flight/runtime.py:3012-3085`) into
`rails.runner.run_rails_experiment` — a plain `for sample: for arm:` loop
(`rails/runner.py:857-885`) — or into `_dispatch_concurrent` / `_run_speech_feature_direct`. That is
the reason the owner rule says the direct baseline must be the `direct-only` **phase program**: only
the phase-program dispatch reaches the openJiuwen executor.

---

## 2. Loop: does the existing graph already express Plan → Observe → Solve → Review → Commit?

### 2.1 Yes for Plan → Solve → (decide) → Commit

The speech-native graph's one wave is literally that cycle:

```
FuncCondition(should_continue = state.final_outcome is None)      rails/runner.py:1743
  PrepareAgentWave      -> rails/runner.py:1531 prepare_workflow_wave -> publish_workflow_state
  ExecuteAgentContact_i -> rails/runner.py:1537 invoke_contact -> core_client.complete
  AggregateAgentWave    -> rails/runner.py:1579 aggregate_wave -> controller.advance(...)
                                                              -> transition + next contact, or stop
```

`aggregate_wave` (`rails/runner.py:1579-1727`) is the review-and-decide seat: it verifies the response
hash, calls `controller.advance`, validates the knowledge decision
(`_validate_agent_knowledge_decision`, `assert_agent_step_binding`, `_validate_new_agent_states`),
records the wave, and then either seals `final_outcome` (Commit) or schedules the next wave. The
loop-max guard is `max_contacts`, checked in `schedule_wave` (`rails/runner.py:1436-1440`).

`AgentContactBatch` (`rails/runner.py:144`) plus `branch_count = max_contacts` in
`build_speech_agent_workflow` (`reproduction/ojw/runner.py:307-339`) means a wave may fan out to N
parallel contacts and fan in deterministically — so a "propose k candidates, then judge" wave is
already expressible without any graph change.

### 2.2 Where a Reviewer node and a Planner condition attach without a new pipeline

Three attachment points, all inside existing signatures:

1. **Reviewer as an injected callable on the controller.** `EvidenceAgentController.__init__` already
   takes `material_for_phase`, `supply_for_phase`, `stop_policy` (`rails/controllers.py:467-497`). A
   fourth keyword — `review_for_phase(phase_name, context, response_text) -> ReviewResult` — called at
   the top of `advance` (`:552`) before the stop decision, would produce (a) the flags, (b) the
   `verify` transition (`AGENT_ACTION_KINDS` already admits it, `rails/knowledge.py:47`), and (c) the
   loop-or-commit decision that today is `is_last or stop_policy`. No graph node, no new class, no
   change to `rails/runner.py`.
2. **Reviewer as a graph node**, if a separate trace record per judgement is wanted: add one
   `WorkflowComponent` beside `AggregateAgentWave` in `build_speech_agent_workflow`
   (`reproduction/ojw/runner.py:307-339`) and one `add_connection`. The `LoopGroup` already supports it
   (`aggregate_agent_wave` is added the same way). This is ~20 lines and does not touch the outer
   `Workflow`/`AdvancedLoopComponent`.
3. **Planner condition.** `FuncCondition(should_continue)` is already a Python callable per state
   (`reproduction/ojw/runner.py:432`, `rails/runner.py:1743`). A planner that stops on budget, on a
   clean review, or on convergence is a change to that callable plus the controller's `advance`, not to
   the framework.

### 2.3 Is `acquire` the Acquire step? Partly.

`acquire` is the **knowledge**-acquire step, not the **observation**-acquire step. It is emitted in
`EvidenceAgentController.advance` when `supply_for_phase` returns a `PhaseSupply`
(`rails/controllers.py:654-660`), carries a hash-bound `RankResult`/`FusionDecision`, and grows the
successor `QueryState.retrieved_value_ids` / `visible_facet_ids`. It cannot re-listen.

**The blocking invariant, cited exactly.** `assert_agent_step_binding` refuses any step that changes
the observation:

```
rails/knowledge.py:1151-1166
    stable_query_fields = (
        "query_sample_id", "speech_packet_id", "speech_packet_sha256",
        "use_split_identity_hash", "use_partition_role", "query_source",
    )
    ... raise RailsError(
        "AgentStepTransition must keep the same original speech packet and "
        "DEV query binding across every step")
```

and `QueryState.validate` pins `query_source == "speech_features"` with the message "agent state or
generated text cannot replace the original speech query" (`rails/knowledge.py:608-615`).

That invariant exists for a good reason (the standing owner rule that the query is speech, never
agent text) and it is **not** an obstacle in principle: a selective re-listen supplies a *derived span
of the same parent media*, which is exactly the object `core.model.SliceRegistry` already chains and
`core.span_surgery.cut_span` already produces for `obs-replay-loop`. The change is to relax
`speech_packet_id`/`speech_packet_sha256` from "identical" to "identical, or a registered derivation
of the trajectory's parent media with a derivation record", keeping `query_sample_id`,
`use_split_identity_hash`, `use_partition_role` and `query_source` immutable. `_agent_messages`
already rebuilds the speech content block from `query_state.speech_packet_id/sha256` on every wave
(`rails/runner.py:1085-1094`), so nothing downstream needs to change.

### 2.4 Per-episode core-call budget

**Yes, three of them, at three scopes — but none of them is a Planner decision.**

* per trajectory: `max_contacts`, enforced in `schedule_wave` (`rails/runner.py:1436-1440`) and
  declared by `PhaseProgram.max_contacts` (`rails/controllers.py:221`, validated `>= len(phases)` at
  `:241-249`).
* per run: `ExecutionPlan.planned_model_calls` / `planned_speech_audio_seconds`
  (`contracts/plan.py:110`), metered by the adapter, cumulative across attempts.
* per prompt: `rails.context_budget.assess_context_budget` (`rails/context_budget.py:1-40`), a pure
  fail-closed accounting rail with `ALLOW` / `COMPACT_REQUIRED` / `REFUSE`.

What does **not** exist is a planner that *spends* a budget adaptively — decides "this row gets one
call, that row gets three". `max_contacts` is a ceiling declared before the flight, identical for
every row.

---

## 3. Tools: what is registered, and what a tool manifest would cost

### 3.1 Nothing is registered as a framework tool. Zero.

`grep -rn "LocalFunction|ToolManager|tool_manager|foundation.tool|foundation/tool|intent_toolkits|Toolkit"`
over `src/`, `tests/` and `scripts/` returns **no hits**. The only occurrences of `LocalFunction` and
`intent_toolkits` anywhere in the repo are in the design note itself
(`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md:146,151,157`).

The adoption memo's rebuild plan did say "DSP functions registered as framework local tools"
(`docs/readiness/2026-08-08-openjiuwen-adoption.md:47-49`), but the rebuild notes record the owner
**reversing** that the same day, and the reversal is the reason nothing is registered:

> `docs/readiness/2026-08-08-ojw-rebuild-notes.md:57`
> "DSP + slice rail | **NOT framework constructs, by design**: `reproduction/obs_audio.py` functions
> and `core/model/slices.py` registry are BELOW the framework layer and are called as plain functions
> (owner ruling: the framework tool base is reserved for the phase-2 model-invoked re-ask arm;
> wrapping pipeline DSP as tools would change semantics to model-decided invocation)"

The same ruling is restated in `reproduction/ojw/components.py:11-16`.

**This matters for the change list**: registering DSP as `LocalFunction` is not a gap to close blindly —
it was a deliberate decision, on the ground that a framework tool is *model-invoked*. The 2026-09-08
design's tool layer is a different object: a **system-invoked** catalog the *Planner* reads, not a
tool list the core is offered. That distinction has to be stated in the change, or the new tool layer
re-litigates a closed ruling.

### 3.2 What the framework offers, verified in the installed package

`~/.venvs/speechrl/lib/python3.12/site-packages/openjiuwen/core/foundation/tool/__init__.py` exports
`Tool`, `ToolCard`, `LocalFunction`, `Input`, `Output`, the `@tool` decorator, plus `MCPTool` /
`RestfulApi` (which must stay uninstantiated — paid API 0). The `@tool` decorator
(`.../tool/tool.py:30-40`) accepts `name`, `description`, `input_params` (dict schema or pydantic
model), `card`, `auto_extract`, `stateless`.

`ToolCard` (`.../tool/base.py:20-51`) already carries most of the design's manifest fields:

| design manifest field | `ToolCard` field | note |
|---|---|---|
| id, name, description | `BaseCard.id` / `.name` / `.description` | inherited |
| typed inputs/outputs | `input_params: Dict \| Type[BaseModel]` | present |
| side effects (bytes changed → derivation record) | `idempotent: bool` (defaults `False`, "secure-by-default") | close, not identical — a derivation-record flag would go in `properties` |
| cost class (CPU/GPU/contacts) | — | goes in `properties: Dict[str, Any]` |
| axis (OBS/ORG/SUPPLY/USE), scope (general/carrier), ledger row type, pinned hash | — | all go in `properties` |
| concurrency | `parallel_safe: bool` | present, and useful given the dispatcher work |

So a manifest does **not** need a new dataclass: `ToolCard.properties` is a free-form dict and the
study's own repository-side identity discipline (a `core.base.Registry` id + a config-pinned sha256)
is the same shape everything else here uses.

`core/controller/modules/intent_toolkits.py` exists in the installed package
(`.../openjiuwen/core/controller/modules/intent_toolkits.py`) — it is real, and this repo uses none of
the `core/controller` line at all.

### 3.3 How a tool would be added today

There is no tool seam, so the honest answer is: it would be added as a **plain function** called from
a component or a policy, exactly as `obs_audio.encode_slice` is called from
`FeedBuffer` (`reproduction/ojw/components.py:62-68`) and from `obs_loop._slice_parallel_pass`. The
repo's actual extension seam is the `core.base.Registry` family (`core/base.py:51-110`: `CARRIERS`,
`EVIDENCE_SOURCES`, `TRANSPORTS`, `POLICIES`, `SCORERS`, `MAX_TOKENS_POLICIES`, `INSTRUCTION_FILLS`,
`KNOWLEDGE_BUILDERS/RANKERS/FUSERS`, `AGENT_CONTROLLERS`, `KNOWLEDGE_PROVIDERS`, `RESPONSE_FORMATS`,
`RESPONSE_POSTPROCESSORS`), whose population sites are pinned by
`scripts/checks/engineering_base_check.py:72-95`. A `TOOLS` registry belongs in that list, and
`engineering_base_check.py`'s `CANONICAL_REGISTRY_FILES` tuple would gain one entry.

---

## 4. Drift: where the plain policy and the openJiuwen executor have diverged

The 2026-08-08 red line was byte equivalence between the two obs executors. The equivalence tests
still pass (see §4.5), but the *feature sets* have separated, always in the same direction: **new obs
mechanisms land on the plain policy and are refused, ignored, or absent on the ojw path.**

| # | drift | plain policy | ojw executor | citation |
|---|---|---|---|---|
| 1 | **unit plan (OBS-E1 speaker-turn units)** | implemented at both cut sites | **refused by name, fail-closed** — "this executor's `window_frames` is clock-derived", so a plan would be silently ignored | `reproduction/obs_loop.py:797-841`; refusal `reproduction/ojw/policy.py:129-143`; test `tests/unit/test_obs_unit_plan.py:573-589` |
| 2 | **`window_hook` (KC-E1f substitution-only revise)** | added 2026-09-07 as the one seam a second pass needs; `obs-repair-loop` overrides only `_window_hook` | **absent** — `FrozenCoreASR.invoke` renders the instruction with no hook and `AcceptAdvance` has no delivery override; `grep window_hook reproduction/ojw/` → 0 hits | `reproduction/obs_loop.py:984, :1010-1034, :1135-1136, :1209-1210, :1391, :1747`; `reproduction/repair_loop.py:208`; `reproduction/ojw/components.py:188-305` |
| 3 | **flagged spans / selective re-listen (`obs-replay-loop`)** | full SCORE → LOCATE → RETRIEVE → REPLAY → ACCEPT policy, calling `_slice_parallel_pass` for pass 1 | **absent**; and the ojw *agent* graph structurally cannot re-listen (§2.3) | `reproduction/replay_loop.py:1-200`, policy id `:366`, registered `core/policies.py:645` |
| 4 | **tail knob** | `obs_slice_tail_silence_seconds` → `append_tail_silence` inside `encode_slice` | **shared, not drifted** — both executors call the same `obs_audio.encode_slice`, and `tail-silence` is one of the 9 equivalence scenarios | `reproduction/obs_loop.py:689-698, :1076, :1442`; `reproduction/ojw/components.py:62-68` |
| 5 | **prefetch + slot-saturating dispatcher (`wt/obspipe`)** | new `ObsDispatcher` + a pipelined branch in `core.driver.run_experiment` | **explicitly excluded, twice**: the driver refuses `obs_prefetch_depth > 0` for any policy other than `obs-agent-loop`, and the config refuses it unless `obs_batch_samples == 1` because "the sample-batch executor already owns sample-level concurrency" | read from the `wt/obspipe` uncommitted diff at ~09:00 on 2026-09-08: `core/driver/run.py` (+188) guard "is only defined for policy … but this run declares"; `reproduction/obs_loop.py` (+275) guard "requires obs_batch_samples 1"; design note `docs/readiness/2026-09-08-e21-obs-pipeline-v1.md:150-158` (still present) |

> **State caveat on drift #5.** The two modified source files and `tests/unit/test_obs_pipeline.py`
> were present in `wt/obspipe` when read and had disappeared from `git status` about 40 minutes later,
> with the branch still at `839a73e5` and nothing committed to `master`. Only the readiness note, the
> receipt directory and `scripts/obs_pipeline_dry_run.py` remain untracked there. This review never
> wrote to that tree (read-only `git diff` / `sed -n` / `grep` only), so the change came from whichever
> session owns that branch. The exclusion quoted above is therefore a design decision recorded in the
> note, and the code implementing it is not in any tree right now — worth confirming with that session
> before drift #5 is acted on.

Two further structural drifts, not on the obs axis:

| # | drift | note | citation |
|---|---|---|---|
| 6 | **`policy: "fixed"` bypasses openJiuwen entirely — 70 configs** | `FlightRuntime._dispatch_fixed_policy` calls `run_rails_experiment` (a serial `for sample: for arm:` loop), `_dispatch_concurrent`, or `_run_speech_feature_direct`; only `policy: phase-*` reaches `run_speech_native_agent_loop`. The repo states the consequence itself: `slurp-direct-closed-list.json` (fixed) and `slurp-phase-direct-only-v1.json` (phase program) differ by one control turn, and **"its numbers are therefore NOT interchangeable with the sealed closed-list baseline's"** | `core/flight/runtime.py:3012-3085`, `:3266-3312`; `rails/runner.py:798-891`; `configs/baseline/slurp-phase-direct-only-v1.json` key `the_one_difference_from_slurp_direct_closed_list` |
| 7 | **`run_program` breaks a multi-phase program into N whole-roster single-contact calls**, so a phase controller never reaches its own `advance` unless `run_continuous_program` is chosen | `rails/phase_runner.py:9-49` (barrier realisation), `core/flight/runtime.py:3127-3137` (`continuous = bool(set(supply_specs) - {first phase})`) |

### 4.5 Equivalence tests that still pass

`tests/unit/test_obs_loop_ojw.py` (1,100 lines, module-level `pytest.importorskip("openjiuwen")` at
`:39-43`) pins, over the **same** `_World` harness the plain-policy suite uses
(`tests/unit/test_obs_loop_policy.py:129`, imported at `test_obs_loop_ojw.py:71-83`):

* `TestEquivalence.test_ojw_reproduces_the_plain_policy` (`:291-319`), parametrised over 9 scenarios
  (`model-tails`, `vad-trim`, `fixed-ablation`, `evidence-arm`, `rms-norm`, `tail-silence`,
  `fallback-boundary`, `retry-flaky`, `retry-exhausted-skip`), asserting equality of accepted spans,
  every request payload, derivation-record bytes, written slice bytes, the whole `SampleOutcome`, and
  the complete trace-record sequence;
* `TestDeterminism.test_determinism_five_runs` (`:336-353`) — 5 ojw runs fingerprint-identical to the
  plain reference;
* `TestBatchExecution.test_batch_of_two_matches_sequential_plain_per_sample` (`:645-707`);
* `TestSingleDoor.test_frozen_core_asr_requires_an_injected_callable` (`:357`);
* `TestWorkflowTimeout` (`:767-891`), `TestSpeechAgentWorkflowScheduling` (`:892-1099`) — slot
  affinity, cancellation settlement, bounded 100-workflow admission, first-fatal-stops-admission.

At the agent-loop layer, `tests/unit/test_rails_runner.py:1430-1476`
(`test_openjiuwen_agent_matches_the_reference_trajectory_semantics`) runs the same controller under
`reference-trajectory-v1` and `openjiuwen-workflow-v1` and asserts
`summaries[0].results[0].as_json() == summaries[1].results[0].as_json()`.

`tests/unit/test_obs_loop_ojw_absent.py` (203 lines) proves the D2 gate: the policy registers with
openjiuwen absent, the version pin fails closed, and `run_sample` refuses with the install hint.

**What the tests do NOT pin:** the drift items. Scenario list has no unit-plan case (that is covered
only by the *refusal* test), no `window_hook` case, no replay case. So equivalence is green precisely
because the diverged features are outside its scope.

---

## 5. Verdict and the minimal ordered change list

### 5.1 Verdict

**Reasonable. Keep it.** The openJiuwen adoption is disciplined (single door held, D2 gate held,
version pinned and fail-closed, byte-equivalence proven and still green, framework constructs composed
rather than subclassed per the owner's own ruling), and the four-agent loop is a *superset* of what the
graph already runs — Plan/Solve/Commit are there, Acquire is there for knowledge, and the two gaps
(a Reviewer seat and a mutable observation) are additive changes inside existing signatures.
Nothing named in the design requires a component that the existing bases cannot carry.

### 5.2 The minimal set of changes, ordered

Each is scoped to existing files; none creates a new pipeline, a `rails/probes/` module, a
`TaskAdapter` subclass, or a `docs/checks/*/launcher/` directory.

| # | change | files | effort |
|---|---|---|---|
| **1** | **Reviewer seam on the controller.** Add `review_for_phase(phase_name, context, response_text) -> ReviewResult \| None` as a fourth injected callable beside `stop_policy`; call it at the top of `advance` before the stop decision; let a `ReviewResult` carry `flags`, `verdict ∈ {commit, revise, acquire, relisten}` and the ids it used, and emit `action_kind="verify"` when it consumed supplied values (the kind and its validation already exist). Config seam: one `phase_review` key parsed like `phase_supply`, resolving ids in a new `core.base.JUDGES` registry. | `rails/controllers.py` (+~120), new `rails/phase_review.py` (~200, mirroring `rails/phase_supply.py`), `core/base.py` (+1 registry), `core/flight/runtime.py` `_dispatch_phase_program` (+~30), `scripts/checks/engineering_base_check.py` `CANONICAL_REGISTRY_FILES` (+1) | **6–8 h** |
| **2** | **Register the judges that already exist.** Wrap `core.repair_alignment.entity_repair_substitutions_v1`, `core.flag_sources.roster_band_flags`, `core.replay_signals.flag_spans`/`slice_logprob_stats`, the SLURP legal-label projection and the numeric-format check as `JUDGES` entries with a uniform `(response, context) -> ReviewResult` shape. No new logic — these are adapters over frozen functions, which is what makes their precision/recall measurable model-free on sealed outputs (design §4). | `core/policies.py` (canonical registration site, +~60), thin wrappers in `core/judges.py` (~180) | **4–5 h** |
| **3** | **Relax the observation invariant to admit a registered derivation.** Change `stable_query_fields` so `speech_packet_id`/`speech_packet_sha256` may advance to a `SliceRegistry`-chained derivation of the trajectory's parent media, carrying the derivation record on the transition; keep `query_sample_id`, `use_split_identity_hash`, `use_partition_role`, `query_source` immutable. Add `action_kind="relisten"` (or reuse `verify` + a target ref) and the successor-`QueryState` accounting. `_agent_messages` needs no change. | `rails/knowledge.py:1151-1166` and `AGENT_ACTION_KINDS` (+~80), `rails/runner.py` `_validate_agent_knowledge_decision` (+~30), tests | **5–7 h** |
| **4** | **Observer seam on the controller**, consuming #3: `observe_for_phase(next_phase, context, review) -> ObservationSupply \| None`, which cuts the flagged span with context through `core.span_surgery.cut_span` + `core.model.SliceRegistry` (both already exist and are already used by `obs-replay-loop`) and returns the derived packet id/sha. This is what turns `obs-replay-loop`'s proven mechanism into a loop step instead of a second policy. | `rails/controllers.py` (+~90), `rails/phase_review.py` (+~60) | **5–6 h** |
| **5** | **Tool catalog + manifest**, as a *system-invoked* catalog the Planner reads — explicitly not the model-invoked tool base the 2026-08-08 ruling reserved. New `core.base.TOOLS` registry; `rails/tools.py` mapping each entry to a framework `LocalFunction` via `@tool(...)` with `ToolCard.properties` carrying `{pinned_sha256, axis, scope, cost_class, side_effects, ledger_row_type}`; the first eight wrappers named in the design (`obs_audio.encode_slice`+tail+resample, the unit planner, the diarization artifact reader, the legality projection, `repair_alignment`, the flagged-span detector, speech-keyed retrieval, the prompt-fit tokenizer). One equivalence test per wrapper: wrapped output == direct output, byte for byte. Keep it behind the D2 lazy seam so the suite still passes with openjiuwen absent. | new `rails/tools.py` (~350), `core/base.py` (+1), `scripts/checks/engineering_base_check.py` (+1), `tests/unit/test_rails_tools.py` (~250) | **6–8 h** |
| **6** | **Config tables with a null arm** (§7), so a module ablation is one key. Introduce `observe: {...}`, `judges: [...]`, `toolkits: {...}` as composed-config objects beside the existing `phase_material` / `phase_supply`; make every entry nullable and make `null`/`[]` byte-identical to today; relax `PhaseSpec.knowledge` to admit `"optional"` so supply on/off stops requiring a second program id. Every id keeps resolving in a `core.base` registry, so `engineering_base_check.py` still reads them from source. | `core/config.py`, `rails/phase_material.py`, `rails/phase_supply.py`, new `rails/phase_review.py` + `rails/tools.py` (from #1/#5), `rails/controllers.py` (`PHASE_KNOWLEDGE_KINDS`, `configs/policy/phase-*.json`), `core/flight/runtime.py` | **5–7 h** |
| **7** | **Standardize on `rails`: registration + disposal, no rewrite.** (a) Register the 36 unregistered `configs/` ids (`engineering_base_baseline.json::unregistered_config_values`) by pointing `POLICIES`/`EVIDENCE_SOURCES` entries at the probe functions that already implement them; (b) re-shape `rails/a2t_hard_validity.py::HardValidityRepairController` and `rails/kb_policy.py::KbAlphaBlendController` onto the `judges` / `stop_policy` seams; (c) delete the 45 `docs/checks/*/launcher/` directories whose controllers are now expressible in config (14 copies of `RuntimeEmbeddedBlendController` alone); (d) shrink the ratchet baseline as each group clears. | `core/policies.py`, `core/evidence.py`, `rails/a2t_hard_validity.py`, `rails/kb_policy.py`, `docs/checks/*/launcher/` (deletions), `scripts/checks/engineering_base_baseline.json` | **10–14 h**, disposal-paced |
| **8** *(decision, then work)* | **Close the obs-executor drift** by having one Earnings executor, not two. Cheapest correct form: freeze or retire the ojw **obs** graph (`obs-agent-loop-ojw`, 13 configs, none since 2026-08-11) and keep the plain policy until #1–#6 let Earnings run as a phase program on the agent graph — because the plain policy is the *production* path for OBS-E1 and KC-E1f and the ojw obs graph adds nothing the agent graph will not do better. Alternative (more work, no measured benefit today): implement `unit_plan` and `window_hook` in `FeedBuffer`/`FrozenCoreASR`. **Decide, do not drift.** | `reproduction/ojw/policy.py`, `components.py`, `core/policies.py`, `configs/` | **3–4 h to freeze; ~12 h to port** |
| **9** *(after 6–8)* | **Move Earnings onto `FlightRuntime`** so all three carriers share one driver, one receipt shape and one executor; retire `core/driver/speech_native.py`'s `legacy-contact-dag-v1` path by re-expressing its 32 SLURP baselines as phase programs, as `configs/baseline/slurp-phase-direct-only-v1.json` already demonstrates for the simplest. This is the actual content of "one harness, reused across tasks". | `core/driver/run.py`, `core/flight/runtime.py`, `configs/baseline/*`, `configs/experiment/*` | **14–20 h**, and it should be split per carrier |

Total for #1–#5 (the four-agent loop and the tool layer): **26–34 agent-hours**.
Adding #6 (one-key ablations): **31–41 h**. Adding #7–#8 (standardization + drift closure):
**44–59 h**. #9 is the endgame, separately scoped.

**Order matters and is not negotiable at two points.** #3 must precede #4 (the Observer seam is
unusable while the observation is frozen), and #1–#2 must precede #6 (there is nothing to put in a
`judges` table until judges are registered). Everything else can interleave.

### 5.3 What is unreusable

**Nothing is unreusable.** No named component fails a named requirement.

Four things are *constrained* or *retirable* rather than unusable, and each is cited so the
constraint is not mistaken for a defect:

* `assert_agent_step_binding`'s frozen speech packet (`rails/knowledge.py:1151-1166`) blocks the
  selective re-listen **as written**. It is a deliberate rule, not an accident, and change #3 relaxes
  it in the one direction the design needs while keeping the rule that motivated it (the query is
  speech from this sample's own media, never agent text). Rebuilding the loop would not remove this
  rule — it would have to reimplement it.
* The ojw **obs** graph (`obs-agent-loop-ojw`, `reproduction/ojw/policy.py` + the four obs components):
  13 configs, none newer than the 2026-08-11 wave-1 ladder, frozen while three obs mechanisms landed on
  the plain policy, and duplicating a loop the agent graph expresses more generally. **Retirable, not
  unreusable** — change #8, and an owner decision, not a silent fix.
* `core/driver/speech_native.py` (13,427 lines) and its third executor `legacy-contact-dag-v1`
  (`:11795-11805`): a parallel harness with its own gate, attempt store and contact DAG, defaulted into
  by 32 SLURP baselines that never name it. **Retirable** once those baselines are re-expressed as
  phase programs (change #9); porting it as a "mode" is not sensible and not proposed.
* The 45 `docs/checks/*/launcher/` directories and their 33 out-of-base controller classes: **disposable,
  not portable.** 14 of them are copies of one class. The E1/E6 config seams were built to make them
  unnecessary (`core/flight/runtime.py:3107-3110`), which is why change #7 deletes rather than migrates.

### 5.4 Four things to state in the next preregistration

1. The design's tool layer is **system-invoked**, which is a different object from the model-invoked
   framework tool base the owner reserved on 2026-08-08
   (`docs/readiness/2026-08-08-ojw-rebuild-notes.md:57`). Say so, or the change re-opens a closed ruling.
2. `policy: "fixed"` does not fly the openJiuwen executor
   (`core/flight/runtime.py:3012-3085`). Any cell claiming "same harness for every arm" must declare
   `phase-direct-only-v1`, not `fixed` — and the repo already says the two are not interchangeable
   (`configs/baseline/slurp-phase-direct-only-v1.json`, key
   `the_one_difference_from_slurp_direct_closed_list`).
3. **Name the executor explicitly, in one spelling.** Today `openjiuwen-workflow-v1` is reached by
   four different config keys and, for the SLURP phase-program cells, by no key at all
   (`rails/phase_runner.py:81` default). A cell that does not name its executor cannot state which
   harness produced its number. Fold the four spellings into one key and make it required.
4. **Audit for inert executor keys** before takeoff: `a2t-direct-packets.json:3,8` declares
   `policy: "fixed"` beside `speech_native_agent_executor_id: "openjiuwen-workflow-v1"`, which reads as
   an agent-graph cell and is not one.

---

## 6. Reuse map: what lives outside the four bases, and what it costs to bring in

Owner addendum, 2026-09-08: *the harness must be standardized on `rails` and reused across tasks —
never one agent system per task.*

The repo already measures its own violations. `scripts/checks/engineering_base_check.py` runs in
ratchet mode against `scripts/checks/engineering_base_baseline.json`
(captured at commit `bd366feb1347e0b43a647598c23993fc2e0793a2`), whose five rules list, verbatim:
**8** `TaskAdapter` subclasses outside `rails/adapters/`, **33** controller classes outside
`rails/controllers.py`, **45** `docs/checks/*/launcher/` directories, **36** modules under
`rails/probes/`, and **36** `configs/` values that resolve in no `core.base` registry. That baseline
IS the reuse map; what follows groups it by what each group would cost.

### 6.1 Group A — carrier orchestration that can become a mode-table entry or an adapter method

| what lives outside the bases | file:line | becomes | rewrite? |
|---|---|---|---|
| **E21 obs loop** — the whole `obs-agent-loop` policy: fixed tiling, VAD trim, boundary tiers, tail, retry/skip, stitch | `reproduction/obs_loop.py:975` (`ObsAgentLoopPolicy`), registered `core/policies.py:615` | **an observe-mode table entry**, not a policy: the cut/encode/register primitives are already pure functions (`reproduction/obs_audio.py:63-420`, `core/model/slices.py`), and the loop around them is what `LoopGroup` already runs on the ojw obs graph | **No rewrite.** It needs the `QueryState` derivation relaxation (change #3) so a window is a derived observation of the parent, then one `Earnings` adapter method `observe_units(sample) -> tuple[SpanRef, ...]` on `TaskAdapter`. The policy's own body becomes the default mode. |
| **E21 replay loop** — SCORE→LOCATE→RETRIEVE→REPLAY→ACCEPT | `reproduction/replay_loop.py:366` (`OBS_REPLAY_LOOP_POLICY_NAME`), registered `core/policies.py:645` | **a judge entry + an observe-mode entry**: its SCORE stage is the Reviewer (change #1/#2), its LOCATE/REPLAY stage is the selective re-listen observe mode (change #4) | **No rewrite** — it already calls the shared `_slice_parallel_pass` for pass 1 rather than reimplementing it (`replay_loop.py:11-14`). |
| **E21 repair loop** — KC-E1f | `reproduction/repair_loop.py:77`, `:208` (`_window_hook`), registered `core/policies.py:679` | **a judge entry** (`e21-entity-repair-substitutions-v1` is already registered in `RESPONSE_POSTPROCESSORS`) plus the `phase-draft-revise-v1` program that already exists | **No rewrite** — the class is 1 overridden method over the base policy by construction (`repair_loop.py:8-17`). |
| **`rails/a2t_*.py`** — 19 modules (`a2t_canonical_family_ground`, `a2t_plain_english_cards`, `a2t_executable_semantic_cards`, `a2t_selected_tool_ground`, `a2t_response_schema`, `a2t_semantic_router`, `a2t_stage_state`, …) | `rails/a2t_canonical_family_ground.py:1` … `rails/a2t_structured_dialogue_state.py:1` | **task tools + knowledge views** in the design's own §7 sense. Their own docstrings say they are pure renderers: "reads no manifests, audio, evaluation fields, model output, scorer, or network service" (`a2t_construction_example_ground.py:1-6`), "performs no embedding, model, network, scorer, or file-system contact" (`a2t_semantic_router.py:1-6`) | **No rewrite.** They are already pure, hashable, side-effect-free functions — which is exactly a `LocalFunction`/`ToolCard` body. Register, do not rebuild. |
| **`rails/a2t_hard_validity.py::HardValidityRepairController`** | baseline `controller_classes_outside_controllers` entry; `rails/a2t_hard_validity.py` | **a judge**: its own docstring says "only deterministic, deployment-visible validity checks … deliberately excludes semantic confidence, reward, tier identity" (`a2t_hard_validity.py:1-7`) — that is a Reviewer, mis-shaped as a controller | **No rewrite**, one signature change to `(response, context) -> ReviewResult`. |
| **`rails/kb_policy.py::KbAlphaBlendController`** (`saea-kb-alpha-blend-v1`, used by 5 SLURP experiment configs) | registered `rails/kb_policy.py:98`, rankers/fusers at `:1132`, `:1134` | its α-blend "the direct label already wins, skip the evidence contact" shortcut is exactly the `stop_policy` seam `EvidenceAgentController` already exposes (`rails/controllers.py:37-43`) | **No rewrite; a port.** `phase-direct-evidence-alpha-blend-v1` was written for this shape and is already registered. |

### 6.2 Group B — the launcher tier, which is the real duplication

**45 `docs/checks/*/launcher/` directories** and **33 controller classes outside
`rails/controllers.py`**, of which **21 are copies of two classes** — `RuntimeEmbeddedBlendController`
appears in 14 separate launcher files (dev100 rounds 0–5 plus 6 attempt-N variants, dev500, dev1000,
a2t-g1 ×4, kwiden-k1, retain-override) and `DirectAdapter`/`DirectObservabilityController`/
`DirectDedupController` in the rest. These are not designs; they are copy-paste attempt scaffolds.

They can be deleted rather than ported: the E1/E6 config seams (`rails/phase_material.py`,
`rails/phase_supply.py`) were built specifically so a two-contact supplied cell is a config edit
(`core/flight/runtime.py:3107-3110` — "a phase program whose material IS expressible in the baseline
fragment binds itself here, so a two-contact cell is a config edit rather than a launcher script").
`bind_phase_program_material` (`core/flight/runtime.py:3735`) remains for anything genuinely
inexpressible. **No rewrite; disposal, at roughly 0.5 h per launcher family once #1–#5 land.**

### 6.3 Group C — the 36 unregistered config values, which are the standardization debt

Every Audio2Tool AgentLoop cell declares a `policy` and an `evidence_source` that resolve in **no**
`core.base` registry, e.g.
`configs/baseline/a2t-g5-exhaustive-family-agentloop.json::policy=saea-a2t-g5-plan-compile-execute-v1`
and `::evidence_source=closed-English-family-taxonomy-to-deterministic-full-unranked-family-contract-bundle`
(baseline rule `unregistered_config_values`, 36 entries). Each of those names is resolved by its own
probe module's constant instead. Registering them (a `POLICIES`/`EVIDENCE_SOURCES` entry pointing at
the existing probe function) is a one-line-per-name change and is what makes an A2T cell reachable
from `FlightRuntime` without its probe launcher. **No rewrite; registration.**

### 6.4 What genuinely cannot be a mode-table entry

Only two things, and neither is a rewrite candidate:

* `core/driver/speech_native.py` (13,427 lines) with its `legacy-contact-dag-v1` executor
  (`:11795-11805`). It is a parallel harness with its own gate, its own attempt store and its own
  contact DAG, used by 32 SLURP baselines. It is not portable as a mode; it is **retirable** once
  those 32 baselines are re-expressed as phase programs — which is what `slurp-phase-direct-only-v1`
  already demonstrates for the simplest of them.
* `core/driver/run.py`'s POLICIES dispatch (`:530-541`) versus `FlightRuntime.run_phases`
  (`:3266`). Two drivers, two receipt shapes. Standardizing means Earnings moves to `FlightRuntime`,
  which is change #6 below.

---

## 7. Where a per-module ON/OFF switch would sit, for a module-admission ablation

The design's discipline is "a cell moves one factor, and its twin is the same loop with that entry
replaced by its form control". That requires **module on vs module off to be one config key on one
harness**. Today it is one key for two of the seven modules and a *policy change* — a different code
path, therefore a different comparator — for the other five.

| module | switch today | is it one key? | where the switch should sit |
|---|---|---|---|
| **silence tail** | `obs_slice_tail_silence_seconds` (float, `0` = today's bytes) | **YES**, and it is already a clean form control: `0` is byte-identical to before the knob existed (`reproduction/obs_loop.py:689-698`) | keep; lift verbatim into the observe-mode table as `observe.tail_silence_seconds` |
| **unit plan (speaker-turn units)** | `obs_unit_plan` + `obs_unit_plan_sha256`, both `None` = off, and they must move together (`reproduction/obs_loop.py:797-806`) | **NO** — two keys, and the ojw executor refuses the pair outright (`reproduction/ojw/policy.py:135-143`), so on/off also changes executor | `observe.unit_plan: {path, sha256} \| null` as one object in the observe-mode table; the refusal disappears once the mode table is the only cutter |
| **legal-label projection** | the `scorers` list: `slurp-slu-projected-v2` vs `slurp-slu-official` (`core/scorers.py:705,749`) | **NO** — it is a *measurement* switch, not a loop switch. Flipping it changes what is scored, not what the system did | as a judge: `judges: ["slurp-legal-label-projection-v2"]` in the review table, with the scorer left alone. Only then is "projection on vs off" a system ablation instead of a metric change |
| **slot schema (TRAIN schema per intent)** | `phase_material.<phase>.state_fill` id resolving in `PHASE_STATE_FILLS` (`rails/phase_material.py:140,246,362`) | **NEARLY** — it is one key, but turning it off means dropping to a different `policy` (`phase-direct-only-v1`), which changes the contact count too | `knowledge_views: {slots: "slurp-train-slot-schema-v1" \| null}` — a view entry that renders to empty when null, so the phase and the contact count stay fixed |
| **repair post-processor (substitution-only delivery)** | `response_postprocessor` + `response_postprocessor_params` (`configs/baseline/e21-kc-e1f-brief-repair.json:12-17`), but read **only** by `obs-repair-loop` and declared REQUIRED there (`reproduction/repair_loop.py:96-102`) | **NO** — off means switching `policy` from `obs-repair-loop` to `obs-agent-loop`, i.e. a different harness | `judges: ["e21-entity-repair-substitutions-v1"]` with params; the rule is already a registered `RESPONSE_POSTPROCESSORS` entry (`core/policies.py:661`), so this is a consumer change, not a new rule |
| **retrieval provider (knowledge supply)** | `phase_supply.<phase>.{provider, rank_policy, fuse_policy, k, tau, query_source}` (`rails/phase_supply.py:11-30`); absent = off | **NO** — the phase must ALSO declare `knowledge: "supplied"`, which is baked into the program id, so on/off means swapping `phase-slots-given-intent-v1` ↔ `phase-slots-given-intent-supplied-v1`. The repo states the reason: *"Two program ids rather than a flag on one, because the phase's `knowledge` value rides the config hash and is part of what the cell IS"* (`rails/controllers.py:866-872`) | that reasoning is right about hashing and wrong about ergonomics. Keep `knowledge` on the `PhaseSpec` but let it be `"optional"`: one program id, and `phase_supply` present/absent is the switch. The config hash still moves, because `phase_supply` is in it |
| **window hook (per-window instruction + delivery)** | **no config key at all** — it is a `_window_hook` override on a policy subclass (`reproduction/obs_loop.py:1747` returns `None`; `reproduction/repair_loop.py:208` overrides it), selected by the `policy` value | **NO** | it is the Reviewer+Solver revise pair; once #1 and #2 land, `judges: [...]` + `phase-draft-revise-v1` is the switch, and no subclass is needed |

**The general rule this yields.** A module switch belongs in one of four config tables, all of which
already exist as objects and none of which currently has a null/off convention:

| table | key today | off convention needed |
|---|---|---|
| observe modes | (none — obs knobs are flat top-level keys on the `run` path only) | one `observe: {...}` object, every entry nullable |
| knowledge views | `phase_supply` (`rails/phase_supply.py`), `phase_material.*.state_fill` (`rails/phase_material.py`) | `null` renders to empty **without** changing the program id or the contact count |
| judges | (none) | `judges: []` is the off arm, and it must be the default so today's cells are byte-identical |
| tools | (none) | `toolkits: {...}` per task type; a tool absent from the toolkit is off |

`phase_material` and `phase_supply` already prove the pattern is workable and hashable; the work is to
extend it to `observe`, `judges` and `toolkits`, and to give all five a null arm. That is
**change #7 below** and it is what makes a module-admission ablation one key rather than one code path.
