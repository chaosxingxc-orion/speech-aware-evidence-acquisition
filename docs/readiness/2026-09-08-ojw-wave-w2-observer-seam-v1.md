# WAVE W2 — the observation invariant, and the Observer seam (2026-09-08)

Items **#3** and **#4** of the ordered change list in
`2026-09-08-openjiuwen-implementation-assessment-v1.md`, plus the assessment's drift **#1**.
Branch `wt/ojw-w2` from `979a730e`. **Model-free: zero model, GPU, tool, network and dataset
contacts.** No config, no registry, no `core/base.py` entry, no controller class, no flight.

| commit | change |
|---|---|
| `5988c2b1` | `rails/knowledge.py`: a REGISTERED derivation of the original speech packet is admitted |
| `4e25b78f` | new `rails/observe.py` + `rails/runner.py`: the Observer seam |
| `c315a606` | `reproduction/ojw/*`: the obs executor cuts a unit plan instead of refusing it |

Gates: `ruff check` clean on every file this wave touched;
`python scripts/checks/engineering_base_check.py` **PASS**; the obs-loop, ojw, rails-runner,
knowledge, replay and unit-plan suites — **439 passed, 1 skipped**
(`test_agent_observe_seam`, `test_agent_relisten_binding`, `test_rails_runner`, `test_rails_packets`,
`test_obs_loop_ojw`, `test_obs_loop_ojw_absent`, `test_obs_loop_policy`, `test_replay_loop`,
`test_obs_unit_plan`, `test_knowledge_build`, `test_knowledge_build_common`,
`test_knowledge_provider`, `test_obs_loop_integration`; the one skip is the pre-existing
data-backed OBS-E1 falsifier, which skips without `$SPEECHRL_DATA_DIR`).

---

## 1. The invariant's new wording

### 1.1 What it said

`rails.knowledge.assert_agent_step_binding` listed `speech_packet_id` and `speech_packet_sha256`
among the fields a step may not change, so the observation was frozen for a whole trajectory:

> `AgentStepTransition must keep the same original speech packet and DEV query binding across
> every step`

That rule exists for a reason the study does not intend to weaken — the DEV query is this sample's
own speech and can never become agent text (`QueryState.validate`) — but as written it also made a
**selective re-listen** unexpressible: listening again, more closely, to a span of the *same* call
is not a new query, and the agent graph had no way to say so (assessment §2.3).

### 1.2 What it says now

The packet may **advance within a trajectory, and only to a registered derivation of the packet the
trajectory started from**. Formally, one step is admitted when either

* the successor carries the prior step's exact packet — the historical case, every sealed run's
  case, and the case in which a derivation record would be a lie and is refused; or
* the transition carries a `SpeechPacketDerivation` whose **parent is the trajectory's ORIGINAL
  packet**, whose `derivation_kind` is drawn from a closed list, and whose output is **exactly** the
  successor's packet.

```
SPEECH_PACKET_DERIVATION_KINDS = {"recut-span", "enhanced-copy", "reencoded-unit"}
```

Every entry is a transform of the *same media* that adds no content: a narrower span of it, a
pinned enhancement of it, or the same audio re-encoded. There is no entry for anything that would
introduce audio the original media does not contain, so such a step cannot be *spelled*, let alone
admitted. `derivation_params_hash` is the canonical hash of the parameters that governed the
transform, so two derivations claiming the same output from different parameters cannot both
verify — the discipline `core.evidence_derivation.canonical_params_hash` already applies to derived
evidence text.

Anything else refuses **word for word as before**: an unregistered packet swap still raises the
sentence quoted in §1.1, which is what every existing test that matches on it still sees.

### 1.3 Four design choices worth stating

**The origin travels with the caller, not with the state.** `assert_agent_step_binding` gained one
optional keyword, `origin_speech_packet: tuple[str, str] | None`. `None` — every caller written
before today — means "the prior step's own packet", i.e. exactly the old rule. `rails.runner`
passes the trajectory's *initial* packet. The alternative, an origin field on `QueryState`, was
rejected: every controller builds its successor state by copying the prior packet
(`rails/controllers.py:661`, `rails/kb_policy.py:965`, …), so an origin field would have had to be
propagated by each of them, and any controller that forgot would silently re-root the trajectory on
its own last cut. `QueryState` is therefore **unchanged**, and a second re-listen still chains to
the original media rather than to the first cut.

**Depth 1, deliberately.** A derivation whose parent is the previous re-listen's own cut is
refused. Derivation-of-a-derivation would put each cut one step further from the media with no
single record still naming the original.

**The record and the action kind are one object.** `relisten` joins `AGENT_ACTION_KINDS`. A
derivation may ride only a `relisten`; a `relisten` must carry one; and a `relisten` may claim no
knowledge use and no new agent state. So `action_kind` **alone** tells a trace reader whether the
observation moved — the property that makes the OBS axis separately auditable.

**Identity only.** `rails/knowledge.py` still reads no bytes and no filesystem. The byte chain
stays the separate, unchanged `core.model.slices.SliceRegistry` rail, which independently
re-measures the parent media and the written cut; `rails/observe.py` is what wires the two
together. This mirrors the E22 clip precedent exactly: a runtime slice is admitted through a
derivation record chained to the parent media, never through a self-computed hash.

### 1.4 Byte identity

The new transition field serializes **only when present**, so every transition this repository has
already sealed keeps its exact JSON and its exact content hash.
`test_a_step_without_a_derivation_keeps_its_exact_json_and_hash` rebuilds the historical document
independently of the dataclass and compares both the mapping and the digest.

---

## 2. The seam

`run_speech_native_agent_loop` gained one optional keyword, `observe_step: ObserveStep | None`.
Between the wave that just settled and the wave about to be prepared:

```
AggregateAgentWave -> controller.advance -> next_query_state, next_contact
                   -> [Observer]  flags(sample, wave) -> cut + register -> relisten transition
                                  -> re-bind next_contact to the observed QueryState
                   -> schedule_wave -> PrepareAgentWave -> ExecuteAgentContact ...
```

* **Flags.** `{sample_id, spans: [{start, end, reason}]}`, exactly the shape W1 will emit as
  `REVIEW` records, read today from a fixture through `rails.observe.fixture_flag_source`. Both
  reach the step through one `FlagSource = Callable[[str, int], ReviewFlags | None]` callable, so
  when W1's records land nothing else moves.
* **The cut.** `SliceReCutter` is `obs-replay-loop`'s own mechanism, not a second copy of it:
  `core.span_surgery.cut_span` writes the flagged span widened by the configured context margin
  (the margin is folded into the bounds and `pad_s` is `0.0`, exactly as
  `reproduction/replay_loop.py::_cut_replay_window` does), the run's `SliceRegistry` chains the
  written file to the sample's registered parent media and re-measures both, and only then does an
  injected `encode_packet` turn the chained `SliceRecord` into the speech-feature packet the agent
  loop actually sends. Encoding is the one step that needs the preprocessing encoder, so it is
  **injected** — which is also what keeps the whole seam runnable model-free.
* **The dispatch.** The controller's own next contact is re-bound (`_rebind_contact`): only
  `query_state_sha256` moves. The contact id, purpose, instruction, key representation, matcher
  policy and decoding params stay what the controller authored, branch by branch for a fan-out
  wave. The Observer changes **what** the next contact listens to, never **what it is asked**.
* **The cost.** A re-listen spends no model contact, so it is bounded by the Observer's own
  `max_relistens_per_sample` and never by `max_contacts`.
* **The record.** One `OBS` trace record per re-listen —
  `<sample>/agent-loop/relisten0000` — carrying the flagged span, the reason, the margin, the cut
  bounds, the whole parent/derived packet chain, the params hash and the cutter's provenance. Under
  the openJiuwen executor its buffer is keyed below the wave's branch 0, so the merged trace reads
  "observe, then contact".

### 2.1 Fail-closed

Every one of these raises `ObserveError`; none is a silently skipped step, because a skipped step
would make two runs of the same config differ with nothing in the trace to say why.

| condition | refusal |
|---|---|
| a flagged span outside its own media | `flagged span [...] lies outside sample ... 's own media` |
| a sample with no verified media in the run's loader facts | `no verified media` |
| a cutter that produced no derived packet | `produced no derived packet` |
| a context margin that is not a finite non-negative number | `ObserveConfig.context_margin_seconds` |
| more flagged spans than `max_relistens_per_sample` | `max_relistens_per_sample` |
| a flag source answering a different sample | `flag source answered sample` |
| a malformed / duplicated flag fixture entry | `start/end/reason`, `unknown keys`, `twice` |
| a cut whose sample is not in the verified split | `SliceRegistry`: `not in the verified split` |

`None` — no observation — is returned in exactly two cases: the Reviewer flagged nothing for this
`(sample, wave)`, or every flag it raised has already been re-listened to.

### 2.2 Where the code lives, and why a new module

`rails/observe.py` is new. It is **not** under `rails/probes/`, adds no controller class, no
`TaskAdapter` subclass, no `docs/checks/*/launcher/` directory and **no `core.base` registry**, so
`engineering_base_check.py` passes unchanged and nothing in `core/base.py` — W1's file — had to
move. It owns the flag contract, the guards and the identity bridge; it owns no loop. The loop
stays in `rails/runner.py`, which builds the successor state, proves the transition and emits the
record — and calls the same helper from **both** executors, so the `reference-trajectory-v1`
equivalence oracle keeps covering the seam rather than being bypassed by it.

---

## 3. The equivalence proof

**Default absent = today's graph.** `observe_step=None` — the default, and the `observe: null` arm
of §5's table — takes no step, emits no record, moves no byte.

| claim | test |
|---|---|
| an absent Observer and a silent Reviewer produce the same result JSON, the same trace record sequence and the same speech packet on every request | `test_an_absent_observer_and_a_silent_reviewer_produce_the_same_graph` |
| an absent Observer emits no `OBS` record, no `relisten` transition, and never moves the packet | `test_an_absent_observer_emits_no_obs_record_and_no_relisten_transition` |
| the two executors agree on the whole result JSON with the Observer **active** | `test_both_executors_agree_with_the_observer_active` |
| the two executors agree with the Observer present and the Reviewer silent | `test_both_executors_agree_when_the_reviewer_is_silent` |
| the pre-existing agent-loop result-JSON equivalence | `test_rails_runner.py::test_openjiuwen_agent_matches_the_reference_trajectory_semantics` — green |
| the 9 (now 10) obs-loop equivalence scenarios | `test_obs_loop_ojw.py::TestEquivalence` — green |
| a flagged span really is re-listened to: the derived packet reaches the next wave's request, the margin widened `[4.0, 5.0)` to `[2.5, 6.5)`, and the trajectory still spent 2 contacts | `test_a_flagged_span_becomes_a_registered_relisten_the_next_wave_listens_to` |
| the byte chain is real: a synthetic WAV through `cut_span` and a real `SliceRegistry`, re-measured after the write | `TestSliceReCutter` |

**D2 gate.** `rails/observe.py` imports no openjiuwen and no heavy dependency at module level
(`soundfile`/`numpy` stay inside `core.span_surgery`'s own function-local imports), so the suite
still passes with openjiuwen absent — `test_obs_loop_ojw_absent.py` green.

**One caveat, stated rather than discovered later.** A controller that hardcodes `loop_step` — only
`rails/a2t_hard_validity.py` does (`loop_step=1` at `:609`, `== 0` / `== 1` guards at `:556`,
`:581`, `:639`) — cannot run under an Observer, because an inserted step increments `loop_step`.
Every other controller derives it from `context.query_state.loop_step + 1` and is unaffected. The
Observer is opt-in and is not configured for Audio2Tool, so nothing in flight is touched; a future
`observe` row on an A2T program would have to re-express that controller's step guards first.

---

## 4. Drift status

| # | drift (assessment §4) | status after W2 |
|---|---|---|
| 1 | **unit plan** refused by name on the ojw obs path | **CLOSED.** The port was what the assessment guessed it might be — passing the already-cut units through the same graph. `ObsSampleState` gained `plan_units` and a plan-aware `window_frames` (an exhausted plan becomes the degenerate window the loop already exits on, which is the plain policy's other `break`); `FeedBuffer` took the plain policy's own `is_final` form; `AcceptAdvance` emits the plain policy's own `_unit_trace_fields`; `_prepare_state` substitutes `units_for`, `len(units) + 8` and the plan boundary mode. **No unit-plan logic is reimplemented** — every decision is still made by a function `reproduction.obs_loop` owns, so the refusals travel with it (a roster call the plan does not cover still stops the ojw path with the identical message, before the parent is decoded). `should_continue` now calls `window_frames` instead of repeating its arithmetic, which its own docstring already claimed. Proof is byte-level: `unit-plan` joined the equivalence suite (three units of unequal length, so a clock-derived cutter on either side would deliver different media), asserting equal accepted spans, request payloads, derivation-record bytes, written slice bytes, outcome and the complete trace sequence. |
| 2 | **`window_hook`** (KC-E1f substitution-only revise) absent on the ojw path | **OPEN, priced.** The hook is consumed only by `_slice_parallel_pass`, the plain policy's *parallel* cutter (`obs_batch_slices > 1`); the ojw executor is the *sequential* cutter, which has no hook site at all. Closing it needs (a) a hook seam threaded through `FrozenCoreASR.invoke`'s instruction rendering and `AcceptAdvance`'s delivery, (b) an ojw sibling for `obs-repair-loop`'s `_window_hook` override, and (c) a repair scenario in the equivalence suite. That is a different shape from drift #1 — a new seam rather than a plan-vs-clock substitution — and it should be taken only if the ojw obs graph is kept at all (assessment change #8 proposes freezing it). Not attempted here; W2 changed nothing about it. |
| 3 | **flagged spans / selective re-listen** absent, and the ojw *agent* graph structurally unable to re-listen | **STRUCTURAL HALF CLOSED.** The agent graph can now re-listen: change #3 admits the derived packet and change #4 wires the step. What remains is the ojw *obs* graph, which still has no replay policy — and the assessment's own point is that it should not grow one, because the agent graph now expresses the mechanism more generally. |
| 4 | tail knob | not drifted (shared `encode_slice`); untouched. |
| 5 | prefetch + slot-saturating dispatcher | untouched by W2. The assessment's state caveat still stands: confirm with the session owning `wt/obspipe`. |
| 6 | `policy: "fixed"` bypasses openJiuwen (70 configs) | untouched; a preregistration concern, not a W2 one. |
| 7 | `run_program` vs `run_continuous_program` | untouched. |

---

## 5. What W4 needs: the `observe` config table, with a null arm

W2 deliberately stops at the seam. It adds **no config key and no registry entry**, because both
`core/config.py` and `core/base.py` belong to sibling waves. What W4 has to add is one composed
config object beside `phase_material` / `phase_supply`, whose **null arm is the absence of an
`ObserveStep` entirely**:

```jsonc
"observe": null            // the default: today's graph, byte for byte
```

```jsonc
"observe": {
  "flag_source": "<JUDGES/REVIEW id, or a fixture relpath + sha256 pin>",
  "context_margin_seconds": 1.5,     // finite, >= 0
  "max_relistens_per_sample": 2,     // positive integer
  "derivation_kind": "recut-span"    // one of recut-span | enhanced-copy | reencoded-unit
}
```

Construction, in `core/flight/runtime.py`'s phase-program dispatch:

```python
observe_step = None if row is None else ObserveStep(
    config=ObserveConfig(
        context_margin_seconds=row["context_margin_seconds"],
        max_relistens_per_sample=row["max_relistens_per_sample"],
        derivation_kind=row.get("derivation_kind", "recut-span"),
    ),
    flag_source=<W1 REVIEW records, or fixture_flag_source(pinned document)>,
    cutter=SliceReCutter(
        registry=<the run's SliceRegistry>,
        data_root=data_root,
        encode_packet=<the preprocessing encoder: SliceRecord -> (packet_id, sha256)>,
    ),
    media_facts=<the SAME {sample_id: (media_relpath, seconds)} the SliceRegistry was built from>,
)
run_speech_native_agent_loop(..., observe_step=observe_step)
```

Four notes for that wave:

1. **`media_facts` must be the loader's own mapping**, not a second copy — the out-of-media guard
   reads the verified duration, and two independently drifting copies of it would be exactly the
   defect the guard exists to catch.
2. **`encode_packet` is the only piece W2 could not write model-free.** It is the preprocessing
   encoder (decoder + mmproj) producing a `SpeechFeaturePacketV1` from the chained cut; a re-listen
   therefore costs one packet encode, which the preregistration must price alongside the contacts.
3. **`SliceReCutter(iteration_base=...)`** offsets the slice iteration numbers. The agent loop cuts
   no obs windows, so `0` is correct there; a program that also runs an obs policy in the same run
   must offset past that policy's iterations.
4. **Ablation is one key.** `observe: null` versus the same row with a margin is a paired arm on one
   roster, and the null arm is provably today's graph (§3), which is what makes the comparison a
   module-admission test rather than a rebuild.
