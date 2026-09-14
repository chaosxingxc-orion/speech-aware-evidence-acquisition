# Audio2Tool and Earnings-21 native-role transfer readiness

Date: September 14, 2026. Source checkout: `e023dd427a5ed28090605a353a0f123c0be1d3cf`.

## Scope

This is a source-only transfer audit for root prioritization. It reads committed code,
configuration and released decisions. It does not inspect an unreleased flight, task output,
reference content or raw media; invoke a model, tool, scorer, tokenizer, encoder or backend; admit
an experiment; or select the next scientific successor.

The target system is one shared episode: Perception forms task hypotheses; Solver produces the
task answer; Reviewer and Planner may request bounded evidence on demand; Planner either accepts
or asks Solver to revise; only Solver may deliver. The detailed Audio2Tool carrier and eight-form
requirements remain in [the September 13 audit](2026-09-13-a2t-native-role-reuse-audit-v1.md).
This note records only the transfer boundary that source now establishes.

## Shared capability and its limits

The registered `phase-native-review-revise-v1` program is a four-role, eleven-contact
`native-role-episode` program
(`configs/policy/phase-native-review-revise-v1.json`;
`rails.controllers.default_phase_program`). The graph in
`reproduction.ojw.native_episode.NativeEpisodeWorkflow._build` propagates role state and bounds
Solver-to-Reviewer-to-Planner revisions. `rails.runner._invoke_native_role_episode` uses the
shared OpenJiuwen request, history, fit, slot and trace custody. Its accepted delivery is pinned
to a Solver completion.

`rails.native_episode_config.load_native_episode_config` requires exactly Perception, Solver,
Reviewer and Planner. Only Reviewer and Planner may receive model-callable analytical tools, and
their phase must own the exact source authority. `rails.phase_tools` and
`core.flight.runtime.FlightRuntime._build_phase_tool_dispatcher` already expose task-contract,
named phase-knowledge, prepared-speech, live-speech and optional candidate-contract actions.
Candidate-contract lookup is optional. Audio2Tool currently needs no carrier provider unless root
later selects that mechanism; multi-action alternatives must not reuse SLURP's mutually exclusive
intent representation.

The graph implementation contains an optional acquisition node, but the public config schema
cannot declare it and the runner advertises only ACCEPT and REVISE to Planner. The working
on-demand form is therefore a Reviewer or Planner ReAct tool call followed by a bounded Solver
revision. A distinct Planner ACQUIRE transition is not configuration-reachable.

A second transport limit matters for transfer. In
`FlightRuntime._default_phase_program_binding`, every config-built phase program currently
requires an arm whose frozen fields include `speech_feature_parts`; raw-audio arms are refused
before contact because the shared agent loop binds an `input_speech_features` query to each
contact. This restriction is separate from each carrier adapter.

## Audio2Tool: configuration-first path

`rails.adapters.audio2tool_runtime.Audio2ToolRuntimeAdapter` accepts the shared phase program,
pins the runtime roster, task-contract source and serving geometry, and reserves whole-manifest
scoring. `rails.adapters.audio2tool.Audio2ToolAdapter.build_task_contract` supplies the legal
tool registry, while its answer contract and `rails.a2t_response_schema` can carry the Solver's
joint ordered tool names and arguments. No committed Audio2Tool flight has proved this four-role
path; the released September 13 audit explicitly distinguishes the older fixed plan/solve
“native system” from the role episode.

A minimal prospective composition can reuse existing source interfaces:

1. Select `phase-native-review-revise-v1`, an Audio2Tool speech-feature arm, the existing
   runtime adapter, and the same lawful media roster and output form in direct and system arms.
2. Give Perception the complete task contract and require its state to preserve all requested
   actions, order, active corrections, lawful dialogue context and spoken values. Do not coerce
   multiple actions into one Top-N intent list.
3. Let Solver alone emit the configured call-string or JSON-array contract. Freeze that choice;
   the active-instruction contract must not silently become the generic adapter default.
4. Give Reviewer and Planner separately named evidence authorities. The discrimination store
   explains when a tool or operation applies. The argument/explanatory store carries schema
   meaning, required and conditional fields, and lawful grounding. Existing
   `knowledge_stores`/`knowledge_store_ids` routing can express the separation.
5. Bound role iterations, revision count, tool allowlists and contact fit through the existing
   native config and phase material tables.

This path preserves the eight task forms named by the September 13 audit: direct, parametric,
multiple-intent, implicit, embedded, correction, multiple-turn and blended requests. Complete
dialogue still needs the already identified pinned dialogue materialization and equal input
between arms. That is carrier configuration/source preparation, not a reason to add another
controller. The existing single-store `a2t-native-system-knowledge-v1` config is historical
fixed plan/solve evidence and does not prove this composition.

The frozen core input for this configuration path is a prepared speech-feature packet because of
the shared phase-program restriction above. Raw Audio2Tool through the resident projection model
is supported elsewhere by direct arms, but it is not a config-built native episode today. The
live speech-observation tool is also not a general substitute:
`rails.live_speech_observation._validate_arguments` accepts only `full-utterance` ASR, and
`_validate_source_binding` caps the hash-pinned raw source at 30 seconds. Some Audio2Tool
populations include longer utterances. A roster-specific duration proof or a new scoped-source
contract would be required before selecting that tool; knowledge/task-contract tools do not need
it.

Audio2Tool execution readiness and optimization readiness differ. The task-native scorer
`a2t-toolcall-official` is registered in `core.scorers` and the runtime sends complete
manifests through `core.scoring_batch`; `a2t-toolcall-v2` supplies the existing ordered-tool
diagnostic. However, `rails.reward_links._NATIVE_PROJECTIONS` has no Audio2Tool scorer
projection, and `rails.group_relative_feedback._native_quality` has no Audio2Tool branch.
Source-verified group-relative optimization therefore cannot consume Audio2Tool outcomes until
root chooses and registers the task-native per-sample sufficient statistics and vector
interpretation. This note does not invent either.

## Earnings-21: reuse the admitted packet route

Both input paths exist, but they describe different source histories.

The finalized September 8 direct/null/KC-E1f family used `arm: fixed-legal-context` with fixed
90-second windows and `q4km-e21-buf90-mmproj-gpu-04ccc72a-*`. The experiment config
`configs/experiment/e21-kc-e1f-repair-44-v1.json` says “raw audio through the bf16 mmproj on the
GPU; no feature cache”; its model fragment omits `LLAMA_MTMD_FEAT_CACHE_DIR`. The released
September 8 verdicts bind that raw-audio execution.

The most recent finalized E21 system result in this checkout is instead the released
[September 11 offline decision](2026-09-11-e21-offline-system-result.md). Its direct and repair
stages used `speech-feature-query`,
`e21-full44-direct-ojw-feature-packets-np4-v1` /
`e21-offline-kc-e1f-new-direct-packets-np4-v1`, and
`q4km-e21-full90-packets-cddb000c-np4-v1`: validated full-window packets with a decoder-only
resident service. That fixed two-stage system was finalized but was not admitted, and its released
note explicitly says it does not prove live Reviewer/Planner selection. Packet-backed proof,
dialogue-refresh and loop configs are thus real source capability, and the September 11 pair is
real finalized execution.

The initial transfer audit incorrectly treated the continuation plan's raw-audio requirement as
current. Root corrected that interpretation before transfer implementation or contact. The
[owner feature-serving amendment](../superpowers/plans/experiment-handoff/OWNER-FEATURE-SERVING-007.md)
explicitly supersedes G5 GPU-resident mmproj. The subsequently admitted
[September 10 packet successor](2026-09-10-e21-dr-window-packets.md) abandons the stopped strict
raw-cache qualification and uses formal exact-window packets. Its
[root generation admission](2026-09-10-e21-dr-packets-root-generation-admission.md) records the
source and capacity qualification. The later on-demand-tool direction retains decoder-only
core serving while reserving semantic speech tools for live Reviewer/Planner decisions.

Build prospective E21 native roles on this already admitted packet route, with source-bound
window preparation and actual request capacity for the new episode. Preserve historical raw
and packet experiments under their original identities. Do not require a shared raw-audio
phase-program retrofit to proceed. The raw-program refusal above remains a real limitation
only if a separately motivated raw transport is selected.

The runtime makes the distinction centrally:
`core.flight.runtime.arm_uses_speech_feature_packets` tests the arm's
`speech_feature_parts`; `FlightRuntime.uses_speech_feature_packets` selects the route; and
`_builtin_packet_promoter` records either `raw-audio-mmproj` or
`mmproj-free-window-speech-feature-packets`. The adapter's
`preprocess_plan() == {"kind": "raw-speech-windows", "workers": 20}` describes how Earnings
calls are divided into source windows. It does not assert which model transport consumes those
windows.

Earnings still cannot express the target window-level native episode by configuration today:

- `EarningsRuntimeAdapter.__init__` permits only `obs-agent-loop-ojw` and
  `obs-repair-loop-ojw`, then validates the window controller. It rejects the registered native
  role policy.
- The native episode operates on one prepared sample state; no shared interface nests it at the
  fixed-window unit and returns the final Solver transcript to the existing ordered whole-call
  stitch/delivery path.
- The on-demand live ASR tool accepts a full raw utterance of at most 30 seconds, while the proven
  E21 core unit is a 90-second window. It has no current-window/span binding with exact audio and
  frame custody. Cached packets cannot satisfy this raw-source tool.
- Existing ConEC supply is a fixed pre-meeting brief. A native episode would need separately named
  authorities for uncertainty/candidate discrimination (plausible names, organizations, numbers
  or spellings for the current window) and explanatory repair context (roster roles, canonical
  forms and numeric/semantic conventions). No intent taxonomy should be introduced for ASR.

The standard whole-manifest registrations already exist:
`asr-wer-whisper`, `conec-entity-wer-official`,
`numeric-value-accuracy-v1`, `semantic-high-impact-error-rate-v1` and `cost`.
The adapter correctly refuses per-item scoring.

Optimization has an additional exact gap. `rails.reward_links._NATIVE_PROJECTIONS` exposes
Earnings ASR sufficient counts through `asr-wer` and `asr-wer-whisper`, but it has no native
projection for the ConEC entity, numeric or semantic registrations.
`rails.group_relative_feedback._native_quality` validates
`wer/hits/substitutions/deletions/insertions` and then returns only
`{"negative_wer": -wer}`. The outer artifact preserves the raw counts, but its normalized
quality advantages contain only WER. It cannot produce the owner-required separate PERSON,
overall WER, non-entity, number and insertion feedback vector. The missing work is an explicit
source-bound multi-metric projection and a carrier-native vector mapping after root fixes its
semantics. Do not synthesize an entity evaluator or scalar cost penalty; group feedback already
sets `scalar_reward` and `cost_penalty` to null.

## Readiness matrix

| Boundary | Audio2Tool | Earnings-21 |
|---|---|---|
| Four-role execution | Source-capable by config on packet arm; carrier flight unproved | Needs adapter policy admission and window/stitch integration on the admitted packet route |
| Perception state | Full registry plus carried role state is sufficient initially | Needs current-window uncertainty/candidate state |
| On-demand evidence | Named knowledge/task tools work; live ASR needs roster duration proof | Needs named ConEC views and a window/span raw-source tool contract |
| Solver authority | Existing answer contract plus shared Solver-only delivery | Shared authority exists, but final window revision-to-stitch return is missing |
| Core audio | Config-built phase path requires packets; raw direct path exists separately | Historical raw and packet flights remain distinct; reuse admitted exact-window packets and decoder-only serving |
| Native scoring | Whole-manifest Audio2Tool scorer exists | Whole-manifest WER/entity/numeric/semantic scorers exist |
| Optimization feedback | No Audio2Tool reward projection or group-quality branch | ASR projection exists, but quality collapses to negative WER; required vector is absent |

This inventory licenses no implementation or contact. Root retains the choice of carrier,
capability and scientific order.
