# Items #8 and #9 — the Earnings obs path on the openJiuwen graph, and Earnings on `FlightRuntime` (2026-09-08, v1)

Owner **Decision 12-F** (2026-09-08): *PORT the Earnings-21 obs path onto the openJiuwen graph, then
move Earnings onto `FlightRuntime` and retire the legacy contact executor.* Items **#8** and **#9**
of the ordered change list in
`docs/readiness/2026-09-08-openjiuwen-implementation-assessment-v1.md` §5.2.

**Model-free: zero model, GPU, tool, network and dataset contacts.** No flight, no server, no
scoring. Branch `wt/ojw-r89` from `5e4a6cf8` (merge wave 6).

| commit | change |
|---|---|
| `8dc195b3` | the `window_hook` seam reaches the openJiuwen obs graph (drift #2, closed) |
| `2365d983` | the cross-call obs pipeline reaches the openJiuwen graph (drift #5, closed) |
| `53b88881` | Earnings flies through `FlightRuntime`, on the one obs harness |
| `59407346` | no speech-native cell may default into the legacy contact DAG |

Gates: `ruff` clean on every file touched; `python scripts/checks/engineering_base_check.py` **PASS**;
the obs-loop, ojw, ojw-absent, pipeline, policy, unit-plan, repair, replay, integration, driver,
driver-smoke, flight-runtime, rails-runner, rails-phase-runner, speech-native-retirement and
speech-native-finalize suites — **584 passed, 1 skipped** (the one skip is the pre-existing
data-backed OBS-E1 falsifier, which skips without `$SPEECHRL_DATA_DIR`), and
`TestEquivalence` **13 passed**.

Two pre-existing failures were seen and are NOT this wave's: `tests/unit/
test_build_a2t_g6_family_sweep.py` fails to collect under the shared venv's verl `scripts` package
shadowing (recorded in the operator notes, untouched here), and
`TestSpeechAgentWorkflowScheduling::test_framework_timeout_waits_for_the_contact_worker_to_settle`
— a 0.02-second framework-timeout race on the speech AGENT graph, which this wave does not touch —
flaked twice under a loaded full-suite run and passed three times in isolation and in the final run.

---

## 1. The seam (#8, first half)

### 1.1 What was open

Drift #2 of the assessment, restated by W2 §4 as *priced but not attempted*: the `window_hook`
KC-E1f needs is consumed only by `_slice_parallel_pass`, the plain policy's **parallel** cutter
(`obs_batch_slices > 1`); the openJiuwen executor is a **sequential** cutter and had no hook site at
all. So the one mechanism that turns a second pass into a repair pass could not ride the graph.

### 1.2 What it is now

One seam, three sites, and the same two legs at every one of them:

* `instruction(iteration, record, default) -> str` — the rendered `task_instruction` for THAT
  window's request. Everything else about the request (arm, evidence, decoding params, slice) is
  untouched, so a per-window instruction rides exactly where `OBS_TAIL_FRAME_V1` already rides.
* `accept(iteration, record, transcript, saturated, skipped) -> (delivered_text, extra_obs_fields)`
  — what the run actually stitches, plus the fields that say why. Called for **every** window,
  saturated and skipped ones included, because "what this window contributes" is precisely the
  decision such a policy exists to make.

| site | file | leg 1 | leg 2 |
|---|---|---|---|
| plain, slice-parallel cutter | `reproduction/obs_loop.py::_slice_parallel_pass` | had it since 2026-09-07 | had it since 2026-09-07 |
| plain, **sequential** cutter | `reproduction/obs_loop.py::run_sample` | **new** | **new** |
| openJiuwen graph | `reproduction/ojw/components.py` | **new**, `FrozenCoreASR.invoke` | **new**, `AcceptAdvance.invoke` |

Three design points worth stating rather than discovering later.

**The hook is resolved once per sample, ABOVE the dispatch decision.** `run_sample` used to call
`self._window_hook(...)` inside the `if cfg.batch_slices > 1:` branch's argument list. It is now
resolved before that branch, and both cutters run it — so which cutter runs is a **throughput**
choice and never a semantic one. That is also what makes the plain sequential path a byte-exact
reference trajectory for the graph.

**The hook rides the FULLY rendered instruction.** After the boundary template, after the
conditioned tail. That is the only placement all three sites can share, and under the
fixed-boundary/zero-tail legality every hook consumer declares, all three hand the hook exactly
`ctx.task_instruction` — so one seam is one string everywhere.

**The delivery leg is handed the ACCEPTED span, not the raw response.** On the two sequential sites
the hook sees what the window *would* contribute; the parallel pass hands it the stripped
transcript. Under fixed boundaries with `is_final` or `boundary_mode == "fixed"` those are the same
string (`accepted = transcript`, `dropped = ""`), which is exactly the regime `obs-repair-loop`
requires — so the three are one seam, not three.

**The `SliceRecord` is read from driver-side state.** `ObsSampleState.slice_record_for(iteration)`
joins `unit_for` for the same reason W2 gave for the unit plan: a `SliceRecord` is a run object,
the framework's `${node.field}` channel carries only the JSON `slice_spec`, and the framework's
state merge deletes `None`-valued keys. The accessor asserts `record.iteration == iteration` rather
than trusting append order, because a hook that repaired the wrong window would be a silent defect.

### 1.3 The ojw sibling

`obs-repair-loop-ojw` joins `obs-repair-loop` in the one registry (`core/policies.py`). It is two
overridden methods over `ObsAgentLoopOjwPolicy`, and both policies resolve their hook through the
same module-level `reproduction.repair_loop.build_repair_window_hook` and their legality through
the same `assert_repair_config`. **No repair logic lives in either class**, so a repair pass cannot
mean one thing on one harness and another on the next.

The old `obs_batch_slices > 1` refusal is retired. Its message said *"the sequential path does not
run the hook that supplies each window its own predecessor"*, which stopped being true in this
change; the three refusals that actually matter (fixed boundary, zero tail, zero trim — the
independence the predecessor binding rests on) are unchanged.

---

## 2. The equivalence table

`tests/unit/test_obs_loop_ojw.py::TestEquivalence::test_ojw_reproduces_the_plain_policy`, over the
shared `_World` harness, asserting for every scenario: **accepted spans** (re-derived per side from
that side's own OBS records through the frozen pure functions), **every request payload**,
**derivation-record bytes**, **written slice bytes**, the whole **`SampleOutcome`**, and the
**complete trace-record sequence**.

| # | scenario | since | what it moves |
|---|---|---|---|
| 1 | `model-tails` | 2026-08-08 | model boundaries + a 4000-char conditioning tail (payload equality pins the span sequence directly) |
| 2 | `vad-trim` | 2026-08-08 | a long non-speech head, trimmed |
| 3 | `fixed-ablation` | 2026-08-08 | fixed boundaries, no tail |
| 4 | `evidence-arm` | 2026-08-08 | `fixed-legal-context` + a ConEC item |
| 5 | `rms-norm` | 2026-08-08 | a declared preprocess transform |
| 6 | `tail-silence` | 2026-09-07 | 2.0 s of digital silence appended to the delivered bytes |
| 7 | `fallback-boundary` | 2026-08-08 | an unparseable boundary response |
| 8 | `retry-flaky` | 2026-08-08 | one timeout, one successful retry under a fresh id |
| 9 | `retry-exhausted-skip` | 2026-08-09 | a slice whose retry also fails: skipped, counted, not aborted |
| 10 | `unit-plan` | 2026-09-08 (W2) | three speaker-turn units of unequal length instead of the clock |
| **11** | **`window-hook`** | **this change** | **both hook legs over three fixed windows** |
| **12** | **`window-hook-skip`** | **this change** | **the hook over a window the core never answered (empty string, `skipped=True`)** |

Beside the table, and pinned separately because equivalence over a hooked scenario is a strong
statement only if the hook really ran on the graph (two executors that both ignored it would agree
just as loudly), `TestWindowHook` asserts on the **ojw side alone**:

| claim | test |
|---|---|
| the default hook is `None` on both executors | `test_the_default_hook_is_none_on_both_executors` |
| every window's request carries the hook's instruction; the stitch is the hook's delivered text and never the raw response; the hook's fields reach every OBS record | `test_the_graph_renders_and_delivers_through_the_hook` |
| `obs-repair-loop-ojw` resolves in the registry, is the ojw policy plus two methods, and shares ONE hook builder with the plain repair policy | `test_the_repair_sibling_registers_and_shares_one_hook_builder` |
| the sibling refuses a config with no sealed predecessor, before any audio is cut | `test_the_repair_sibling_refuses_a_config_with_no_predecessor` |

Still green and unchanged: `TestDeterminism::test_determinism_five_runs`,
`TestBatchExecution`, `TestSingleDoor`, `TestSaturation`, `TestWorkflowTimeout`,
`TestSpeechAgentWorkflowScheduling`, and the D2 gate suite `test_obs_loop_ojw_absent.py`.

---

## 3. The pipeline property (#8, second half)

### 3.1 What was ported, and how

The 2026-09-08 obs-pipeline fix (`docs/readiness/2026-09-08-e21-obs-pipeline-v1.md`) measured that
**every idle GPU second of the sealed 44-call attempt was a call boundary** — 828.4 s of 829, mean
gap 19.26 s over 43 boundaries. It bought that back with two halves of one mechanism, and the port
**reuses both halves rather than growing parallel components inside the graph**:

| half | plain path | ported path |
|---|---|---|
| **PREFETCH** — the next call's decode/cut runs while this call's windows are answered | `core.driver.run_experiment`'s pipelined branch: `obs_prefetch_depth` samples of lookahead, each on its own worker with its own `TraceBuffer`, flushed in split-id order | **the same branch.** `_obs_pipeline` now admits `obs-agent-loop-ojw` and `obs-repair-loop-ojw`; the ojw policy's `_prepare_state` (decode + VAD) is what runs off the critical path |
| **SLOT-SATURATING DISPATCH** — the slots stay occupied across a boundary | `_slice_parallel_pass` acquires one `ObsDispatcher` slot **per request** | `runner.execute_obs_workflow` holds one `ObsDispatcher` slot **per SAMPLE**, acquired after the cut, released when the sample settles |

The per-sample hold is the better shape on this executor, not a compromise: the graph sends one
request at a time per sample, so "samples holding a slot" and "requests in flight" are the same
number, and the held integer is `id_slot="per-sample"` affinity in its **strongest** form — every
window of one call lands on one llama-server slot. The plain policy's pipelined path can only
resolve that sentinel per request, because one sample there spans the whole pool.

### 3.2 Legality, all fail-closed

| rule | where | why |
|---|---|---|
| the ojw executors are exempt from `obs_prefetch_depth > 0 requires obs_batch_slices > 1` | `ObsLoopConfig.from_values` | **not** because their cutter is parallel — it is strictly sequential — but because every loop-carried value of a sample lives in that sample's own `ObsSampleState` and its own workflow session, so two samples share no cursor at any boundary mode |
| `obs_batch_samples` must be 1 | `from_values` and `_obs_pipeline` | the graph's own batch executor already owns sample-level concurrency and its own slot pool; two schedulers would multiply the in-flight count |
| a run dispatcher reaching `execute_obs_batch` is refused outright | `reproduction/ojw/runner.py` | a silently ignored dispatcher looks exactly like a working one |
| on the ojw executors the dispatch width must be `>= depth + 1` | `_obs_pipeline` | the in-flight ceiling IS `depth + 1`; a narrower pool would serialize exactly the samples the prefetch just cut, and a pipeline that cannot pipeline is a defect worth refusing rather than measuring |

### 3.3 The proof, and what the port does NOT carry

Six tests over the driver's own synthetic three-call world (3 calls × 2 windows = 6 windows):

| claim | test |
|---|---|
| depth 0 is byte-identical to declaring nothing at all (same trace lines modulo the COST stopwatch, same outputs bytes) | `test_depth_zero_is_byte_identical_to_declaring_nothing` |
| **depth 1 sends the SAME set of request payload hashes, emits the SAME per-sample OBS records and writes the SAME outputs bytes as depth 0** — while two different calls are genuinely in flight at once | `test_depth_one_sends_the_same_payload_set_and_overlaps_two_calls` |
| the pool never exceeds its width, never hands one `id_slot` to two live requests, and **every window of a call carries that call's one slot integer** | `test_a_call_holds_one_slot_for_its_whole_life` |
| the graph needs no slice width; the plain sequential cutter still does | `test_the_graph_needs_no_slice_width_but_the_plain_cutter_does` |
| two schedulers never compose, at either layer | `test_two_schedulers_never_compose` |
| a width narrower than the lookahead is refused | `test_the_driver_refuses_a_width_narrower_than_the_lookahead` |

**What the port does not carry, stated rather than discovered later: intra-sample slice
parallelism.** `_slice_parallel_pass` puts `obs_batch_slices` windows of ONE call in flight; the
graph puts one. So on the ojw path the run's in-flight ceiling is `obs_prefetch_depth + 1`, and
`obs_batch_slices` declares the run's dispatch **width** rather than a per-sample fan-out.

Measured on the real sealed geometry (`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6` +
`e21-buf90-tail2s-scored7` + `e21-full44-tail2s-v1`, composed model-free):

```
serving_geometry: {"slots": 6, "slot_tokens": 6144, "max_tokens": 1024}
resolve_dispatch_width = max(obs_batch_slices 8, slots 6) = 8

policy obs-agent-loop-ojw, depth 0 -> 1 request in flight   (no dispatcher built)
policy obs-agent-loop-ojw, depth 1 -> 2 requests in flight
policy obs-agent-loop-ojw, depth 5 -> 6 requests in flight   <- saturates the SERVER's 6 slots
policy obs-agent-loop-ojw, depth 7 -> 8 requests in flight   <- saturates the declared width
policy obs-agent-loop-ojw, depth 9 -> REFUSED (width 8 < 10)
```

**So a ported Earnings-21 flight that wants the sealed comparator's occupancy declares
`obs_prefetch_depth: 5`, not `obs_batch_slices: 8`.** At depth 0 the ported path would run one
request at a time against a 6-slot server — roughly a fifth of the sealed attempt's 4.664 mean busy
slots — which is why the migration rule in §6 makes the depth an explicit part of the smoke rather
than something a flight discovers on the card.

---

## 4. The `FlightRuntime` path (#9, first half)

Earnings was the one carrier outside the harness: plain Python through
`core.driver.run.run_experiment`, its own receipt shape, its own driver. `run_phases` now dispatches
an obs policy through `_dispatch_obs_policy`, and the stage chain is the same one SLURP and
Audio2Tool fly:

```
preflight   compose 4 fragments -> split identity -> ExecutionPlan -> gate ->
            exposure-row re-check -> clean-tree assertion -> prompt budget
preprocess  the adapter's preprocess_plan through the packet-promotion seam
            (inert for a raw-audio Earnings arm)
serve       attach to the resident always-on session (E7); spawn only as fallback
run_phases  -> _dispatch_obs_policy -> core.driver.run_experiment  == the obs cut plan,
            the slice registry, the single FrozenCoreAdapter, the prefetch pipeline
seal        the driver's own outputs rows + manifest + verify + finalize
score       once through core.scoring_batch, never sharded
```

**It delegates; it does not reimplement.** The obs driver stays the one obs harness — it resolves
this run's evidence through `core.evidence` and proves its D1 identity and derivation chain, builds
the per-run `SliceRegistry` the adapter enforces slice binding against, constructs the single
`FrozenCoreAdapter` that reserves this attempt, emits the per-sample OBS/ORG/SUPPLY preamble, runs
the prefetch pipeline, writes `<run_id>.outputs.jsonl` in the bundle contract's own field set and
closes its trace sink. A second copy of any of that inside `FlightRuntime` would be the parallel
harness the owner's 2026-09-03 rule forbids, and would make an Earnings number produced here
incomparable with the sealed Earnings numbers produced there. The runner rides an injected
`obs_runner` seam defaulting to the real `run_experiment`, exactly as `rails_runner` and
`phase_runner` do for theirs.

Four consequences, each deliberate and each pinned:

| consequence | why | test |
|---|---|---|
| **no `FrozenCoreClient` is built** | that client is the rails `messages` shim over the same adapter the obs driver constructs; building one would open this attempt twice | `test_run_phases_routes_every_obs_policy_through_the_obs_driver` (client factory called 0 times) |
| **`seal` reads the driver's `RunResult`** (arm, trace manifest hash, measured cost) instead of closing a client that does not exist | ditto | `test_seal_writes_the_obs_drivers_own_rows_and_reads_its_run_result` |
| **the sealed rows are the driver's rows, unmodified** | those three hashes are STITCH descriptors over a sample's per-window requests and responses; no client timing exists (or could) for a multi-window stitch, and a second opinion about a stitched hypothesis' identity is what this stage must not have | same test (`sealed == the driver's rows`) |
| **`id_slot="per-sample"` reaches the driver UNRESOLVED** | `_decoding_params` collapses it to slot 0 because the phase harness dispatches one contact at a time; the obs executors resolve it per sample from the run's dispatch pool, which is what per-sample affinity means. The receipt says so rather than claiming a resolution that did not happen | `test_the_sentinel_reaches_the_obs_driver_unresolved` |

Two further adjustments the path needed:

* **The prompt budget estimates a WINDOW, not a whole call.** An Earnings call is 40–75 minutes and
  never reaches the core as one request; estimating the call would refuse every legal Earnings
  flight on a ceiling no request of it approaches. The speech term is the configured
  `obs_buffer_seconds` plus its declared `obs_slice_tail_silence_seconds`
  (`test_the_prompt_budget_estimates_a_window_not_a_whole_call`).
* **The throughput line is MEASURED, not estimated.** The obs driver's cost block carries the run's
  real `calls_used`, `completion_tokens_total` and `latency_seconds_total`, so `tokens_per_second`
  is the actual completion rate rather than the contact-rate-times-ceiling upper bound the phase
  path settles for. The receipt also carries the driver's own saturated/skipped slice aggregates,
  so a closure reports holes beside quality.

**The E21 fragments compose through it** (model-free, `core.config.compose`, this branch):

| model | dataset | baseline | experiment | policy | in the obs branch | `config_hash` |
|---|---|---|---|---|---|---|
| `q4km-e21-buf90-mmproj-gpu-04ccc72a-np6` | `earnings21-discovery` | `e21-buf90-zero-locked-scored4` | `e21-full44-direct-baseline-v1` | `obs-agent-loop` | yes | `e4b133d1df56…` |
| ″ | ″ | `e21-buf90-tail2s-scored7` | `e21-full44-tail2s-v1` | `obs-agent-loop` | yes | `3d28fb5abfe2…` |
| ″ | ″ | `e21-units-obse1-scored7` | `e21-obs-e1-speaker-turn-units-v1` | `obs-agent-loop` | yes | `4e5549ee9eed…` |
| ″ | `earnings21-discovery-conec-names` | `e21-kc-e1-brief-whole-prompt` | `e21-kc-e1-brief-44-v1` | `obs-agent-loop` | yes | `3ac6d4360101…` |

All four resolve `policy` into `FlightRuntime._obs_policy_names()`
(`obs-agent-loop`, `obs-repair-loop`, `obs-agent-loop-ojw`, `obs-repair-loop-ojw`) and their
composed hashes are unchanged by this branch — no Earnings fragment was edited.

### 4.1 What this branch does NOT prove, and why

The brief asked for a dry run on the four shortest calls' **sealed slices** reproducing the sealed
comparator's requests byte for byte. That is not done here, and the substitute is named rather than
implied. What is proven offline is the **chain**:

1. the sealed comparator's requests are the plain policy's requests — same code, unedited;
2. the ojw executor reproduces the plain policy byte for byte over 12 scenarios (§2), including
   both new hook scenarios;
3. depth 1 sends the same payload SET as depth 0 on the ojw path (§3.3);
4. `FlightRuntime`'s Earnings dispatch hands the obs driver **this flight's own** composed config,
   `ExecutionPlan`, gate, lock, data root, run dir and transport, and seals the driver's rows
   unmodified (`test_the_obs_driver_receives_this_flights_own_objects` asserts object identity, not
   similarity).

What the chain does not close is the real media: the equivalence scenarios run synthetic PCM through
a monkeypatched decode. **Closing it on real Earnings-21 audio is the 13-window smoke in §6**, which
is a flight-agent step and is named there.

---

## 5. The executor retirement (#9, second half)

Assessment §5.4 item 3: *name the executor explicitly, in one spelling.* Thirty-two speech-native
baselines reached `legacy-contact-dag-v1` by **declaring nothing at all**, so not one of them could
state which harness produced its number.

**The silent default is now a refusal.** One resolver,
`core.driver.speech_native.resolve_speech_native_agent_executor_id`, serves both call sites — the
profile flight (`_cli_speech_native_profile`) and finalize-from-disk — so the two can never disagree
about what a cell declared, and a fragment that names no executor is refused before any packet is
promoted and before any contact is spent. finalize-from-disk accepts both spellings rather than
pinning the legacy one: it contacts nothing, and refusing a fragment that has since named its
executor would strand exactly the attempts this retirement moves.

**All 32 fragments now name it, and every one names `legacy-contact-dag-v1`.** That is measured, not
assumed. The openJiuwen speech-native executor is an M1/M2 one-or-two-contact vertical slice
(`speech_native.py`: predictions result mode, `matcher_policy_id ∈ {M1, M2}`, `contact_ceiling ==
{M1: 1, M2: 2}`), and the eligible set over these 32 is **empty** — they are M0/M3/M5–M11 with
ceilings 1–20. Re-pointing them would **refuse** them, not port them, and would change what a
sealed cell measures. `test_no_speech_native_baseline_composes_into_the_openjiuwen_executor_today`
computes that set and asserts it is empty, so the claim re-checks itself.

**The retirement list** (all 32, each now carrying `speech_native_agent_executor_id:
"legacy-contact-dag-v1"` and its own `speech_native_agent_executor_basis`):

```
speech-native-engineering-adaptive-m11-k3-v4-contact.json
speech-native-engineering-adaptive-m11-k3-v4-task-affine-speech-prefix.json
speech-native-engineering-m11-prefix-probe-dual-v2.json
speech-native-engineering-m11-prefix-probe-speech-query-v2.json
speech-native-evidence-e108-information-complete-m11.json
speech-native-packet-equivalence-04ccc72a.json
speech-native-packet-equivalence.json
speech-native-preprocess.json
speech-native-profile.json
speech-native-science-effect-c108-m0-schema-v4.json
speech-native-science-effect-c108-m0.json
speech-native-science-effect-c108-m6-k3-v3-contact.json
speech-native-science-effect-c108-m7-k3-v3-contact.json
speech-native-science-effect-c108-m8-k3-v4-contact.json
speech-native-science-factor-d108-m9-k4-v4-contact.json
speech-native-science-gate-c36-m0.json
speech-native-science-gate-c36-m6-k3-v3-contact.json
speech-native-science-m2.json
speech-native-science-m3-k3-v3-contact-reverse.json
speech-native-science-m3-k3-v3-contact-rotate7.json
speech-native-science-m3-k3-v3-contact.json
speech-native-science-m3-k3-v3.json
speech-native-science-m3-k3.json
speech-native-science-m3-k5-v3.json
speech-native-science-m3-k5.json
speech-native-science-m5-k3-v3-contact.json
speech-native-science-m6-k3-v3-contact.json
speech-native-science-reverse.json
speech-native-science-rotate7.json
speech-native-science-x108-m5-k3-v3-contact-q8.json
speech-native-science-x108-m5-k3-v3-contact.json
speech-native-science.json
```

**Deviation from the brief, stated plainly.** The brief said every config that silently defaulted
"must name `openjiuwen-workflow-v1` explicitly". None can, today, for the reason measured above.
What is delivered instead is the ratchet: the legacy executor can no longer be reached by accident,
its remaining users are a `grep` and a test, and that list can only shrink. Shrinking it is
per-carrier phase-program work — `configs/baseline/slurp-phase-direct-only-v1.json` already
demonstrates it for the simplest of them — and is not something a config edit can do.

**Hash movement, deliberate.** The 32 fragments' `config_hash` moves by exactly one declared key
plus its basis string. Their sealed receipts are **not** re-run and are unaffected: a sealed
manifest pins the composition it flew. Any future re-fly of one of these cells is a new protocol
hash and its own exposure row, which is the correct reading of a cell that has changed what it
declares about its own harness.

The retirement's own ledger is `tests/unit/test_speech_native_executor_retirement.py`: the baseline
set is the 32 the assessment counted, every one names a legal executor, the remaining legacy users
are enumerated, none is ojw-eligible today, and the resolver refuses both an absent key and an
unknown third harness.

---

## 6. The flight-side migration rule

**The next Earnings-21 flight — the KC-E1f replication or the whole-loop cell — flies on the plain
path unless and until the smoke below passes.** Nothing in this branch flips a fragment: every
committed Earnings fragment still declares `policy: "obs-agent-loop"` and
`obs_prefetch_depth` is absent (0) everywhere.

### The smoke, named as a flight-agent step

**`SAEA-E21-MF-OJW-PORT-SMOKE-V1` — a 13-window smoke on the resident session.**

| | |
|---|---|
| who | the flight agent, not this wave |
| when | before the first Earnings-21 flight on the ported path |
| roster | the shortest Earnings-21 call that yields ≥ 13 windows at `obs_buffer_seconds 90`, or the first 13 windows of it |
| arms | one cell twice: `policy: "obs-agent-loop"` (the current path) and `policy: "obs-agent-loop-ojw"` (the ported path), every other key byte-identical |
| serving | attach to the resident session (E7); never spawn |
| pass | the two arms' per-window **request payload sha256 sets are equal**, their **slice bytes** are equal, their **derivation records** are equal, and both arms' OBS records agree field for field |
| also required | the ported arm declares `obs_prefetch_depth: 5` on the sealed `np6` geometry (§3.3) and its receipt's `dispatch.max_in_flight`/slot occupancy show it actually pipelined; a depth-0 ported arm is a throughput regression, not a port |
| exposure | its own pre-registered row; the smoke spends real contacts and is not model-free |

Only after that receipt does an Earnings fragment declare the ojw policy. Two further rules for
whoever writes that fragment:

1. **A depth change is a protocol change.** `obs_prefetch_depth` moves the fragment's hash, the
   composed `config_hash`, the `protocol_hash` and therefore the exposure row — deliberately. A cell
   may not change depth mid-campaign, and any comparison spanning a depth change is read against
   `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s band (greedy decoding is not bitwise reproducible across
   batch compositions, and the pipeline changes batch composition by construction).
2. **The `FlightRuntime` envelope and the executor are separate decisions.** An Earnings cell may
   move onto `FlightRuntime` while keeping `policy: "obs-agent-loop"` — that is the §4 path and it
   changes no request byte, only which harness runs preflight/serve/seal/score around the same obs
   driver. Moving the *executor* is the §3 decision and is what the smoke gates.

---

## 7. Drift status after this wave

| # | drift (assessment §4) | status |
|---|---|---|
| 1 | unit plan refused by name on the ojw obs path | **CLOSED** (W2, 2026-09-08) |
| 2 | `window_hook` absent on the ojw path | **CLOSED** (§1) |
| 3 | flagged spans / selective re-listen | **structural half closed** (W2); the ojw *obs* graph still has no replay policy, and by the assessment's own argument should not grow one — the agent graph expresses the mechanism more generally |
| 4 | tail knob | not drifted; untouched |
| 5 | prefetch + slot-saturating dispatcher | **CLOSED** (§3), with the intra-sample gap stated and quantified |
| 6 | `policy: "fixed"` bypasses openJiuwen (70 configs) | untouched; a preregistration concern |
| 7 | `run_program` vs `run_continuous_program` | untouched |

## 8. Claim surface

Nothing here is a quality claim, a superiority claim, or a Stage-3 activity. It is an engineering
port with an equivalence proof, a throughput property whose limit is stated, a harness consolidation
that deletes no capability, and a fail-closed retirement that changes what no sealed cell measures.
It authorizes no contact, no server, no scoring, and no change to any Earnings fragment.
