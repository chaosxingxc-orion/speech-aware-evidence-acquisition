# E21 full44 direct then KC-E1f next-window readiness

## Intended offline system

The bounded successor is a two-stage, full-roster offline pipeline. Stage 1 runs the existing direct transcription instruction over all 44 frozen Earnings-21 discovery calls and all 1,593 fixed 90-second windows. Stage 2 applies the existing KC-E1f brief repair to those same windows, using the newly generated stage-1 window responses as its predecessor. The final system output is stage 2. Its reported cost must include both stages.

This is not a LOOP replacement. It performs no judge selection and does not reuse the LOOP slice plans. It is also not a continuous in-request loop: the complete stage-1 parent seals before the content-free predecessor binding is created and stage 2 is composed.

## Material already ready without a model

The authoritative source-window inventory is `analysis/SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1/window-inventory.json`, file SHA-256 `7b12a5c32654855701c48b57152ab1643e0c776b9a7a3853fda009a6ac78face`. It is a `saea-prepared-artifact-v1` wrapper of kind `exact-window-feature-inventory-v1`; its canonical output is schema `saea-window-feature-inventory-v1`, output SHA-256 `09a154a65b83171920b834e706558e75f1a661593cea1ef2ecf1f5503982573d`, and source-window identity `f569c77f6e22315f57268b1688b3b70e0b1e037de3284d5d198fbec269e115d4`. The single named batch covers 44 calls, 1,593 unique request keys and audio hashes, and 141,345.8526875 selected seconds. Every row binds sample id, zero-based iteration, start/end/audio seconds, sample rate, source WAV SHA/size, parent media path/SHA/size, preprocessing, payload SHA, and encoding-key SHA. The exact 1,593 full-window sources therefore have complete current-build preparation. The final cache audit is `analysis/SAEA-E21-DR-FULL-WINDOW-GPU-ENCODING-V1/window-feature-cache-audit.json`, SHA-256 `cc59a1dee59908c7fae25500b9ab40383b4aa9f9ef00a2946ba7c544b60180a8`. Final preparation provenance is `analysis/SAEA-E21-DR-FULL-WINDOW-GPU-ENCODING-V1/window-feature-preparation-provenance.json`, SHA-256 `72d097e3b153baccb75b4e6e221bc83a1ac60d36dd194c39822993db684ed757`.

The cache audit, preparation provenance, and packet artifact all bind the canonical inventory output SHA-256 `09a154a65b83171920b834e706558e75f1a661593cea1ef2ecf1f5503982573d`; the packet artifact additionally binds the inventory file SHA-256 above. The promoted packet artifact is `analysis/SAEA-E21-DR-FULL-WINDOW-GPU-ENCODING-V1/window-feature-packets.json`, SHA-256 `9aba4ff0d9a78dc66afcdf73f35bea0e7e6919e8448211f383f95219833a5115`, with packet root `/home/chao/feat-packets/e21-cddb000c-dr-full-gpu-v1`. It covers all 1,593 requests and requires no new encoding. The shared loader verifies its artifact hash, decoder and encoder identities, packet descriptors, and every regenerated `SliceRecord` source identity before a packet enters a request.

The new direct baseline fragment is independently composable through the current `obs-agent-loop-ojw` path, `phase-direct-only-v1`, and the full-window packet artifact. Before a GPU window, model-free work can compose it and verify the complete source/packet roster. Materializing the registered runtime request identities and running the synthetic shared wire check remain held until root supplies the exact execution plan and attempt identity. The ConEC class-list evidence source and KC-E1f response postprocessor are already registered. No reference, scorer, tokenizer, encoder, or answering model is needed for those checks.

Actual request capacity is not model-free. Both the direct request and the longer brief-plus-draft repair request need separately registered formal-packet fits on the chosen runtime before generation admission.

## Matching serving geometry

The current validated E21 packet geometry is the decoder-only cddb000c runtime at `-c 36864 -np 4`: four 9,216-token slots, `max_tokens=1024`, temperature zero, seed 20260803, `speech-query-prefix-v2`, q8 KV, flash attention, and `GGML_CUDA_DISABLE_GRAPHS=1`. It loads no projector. The existing LOOP model fragment proves this geometry against LOOP packets; the new thin model fragment keeps that geometry and points `LLAMA_SPEECH_FEATURE_ROOT` at the already completed full-window packet root. It does not claim that the KC-E1f request fits 9,216 tokens; the actual fit remains a prerequisite.

## Fixed live-draft binding rule

Before stage 1 starts, freeze the rule rather than its unknowable output hash:

1. Accept only the declared stage-1 run and attempt on the exact full44 roster, packet artifact, direct instruction, and fixed-window protocol.
2. After the parent is complete, verify its manifest, outputs and trace hashes. Recover every terminal window from the trace and require those windows to rebuild all 44 sealed outputs byte for byte.
3. Require exactly 1,593 unique windows, their declared source bounds and identities, and the recorded saturation/skip closure. Select every row in stitch order; inspect no response content or quality statistic to make the selection.
4. Persist the response-bearing snapshot under `SPEECHRL_DATA_DIR`. Publish a content-free binding receipt carrying the new run/attempt, source hashes, roster counts, artifact hash, and canonical `(window_id, text_sha256)` chain.
5. Create a stage-2 baseline successor that preserves KC-E1f's brief source, cap 12, repair frame, instruction, substitution-only delivery parameters, fixed-window protocol and scorers. Replace its historical `predecessor_snapshot` only with the new receipt path and SHA-256, and add the current OJW/formal-packet fields.
6. Hash and register that concrete stage-2 composition before tokenizer fit or generation and before reading any quality outcome from stage 1.

The existing `PredecessorSnapshot` reader and KC-E1f repair hook already enforce the downstream window/source binding. No new controller is required for this batch-barrier design.

## Small shared-interface gap

The existing producer `scripts/build_e21_predecessor_snapshot.py` is tied to `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, its attempt, exposure row, and historical prompt/completion token totals. It accepts run and attempt arguments but still refuses a valid new parent when those hard-coded totals differ. The minimal missing shared seam is a model-free predecessor snapshot builder parameterized by an already verified complete parent and explicit expected roster/source identity, retaining the current stitch-rebuild proof and receipt schema. It should return the receipt reference needed to compose the stage-2 successor.

`FlightQueue` cannot construct stage 2 before that receipt exists: it accepts prebuilt `FlightRuntime` objects and its dependency state changes only after a flight seals or scores. The bounded route is two queue/campaign invocations against the same admitted resident geometry, with the model-free binding and concrete stage-2 composition between them. Adding live multi-phase behavior to the window controller is unnecessary for this offline design.

The current live window controller remains single-phase and correctly refuses `phase-draft-revise-v1`. That limitation matters only if the owner later asks for an in-request two-contact window loop; this readiness plan does not.

## Held artifacts

- `configs/model/q4km-e21-full90-packets-cddb000c-np4-v1.json`: full-window packet root on the validated np4 decoder-only geometry.
- `configs/baseline/e21-full44-direct-ojw-feature-packets-np4-v1.json`: direct stage through the current shared OpenJiuwen executor.
- `configs/experiment/e21-full44-direct-then-kc-e1f-packets-np4-held-v1.json`: fixed two-stage binding rule and held cells. The repair cell intentionally names a pending baseline, so campaign loading fails closed until the newly generated predecessor receipt exists.

No exposure, fit, generation, scoring, comparison, or claim is admitted here. Root owns the scientific comparator, ceilings, concrete attempt identities, stage-2 successor, and every contact decision.

## Existing shared entry points

- `core.flight.factory.build_flight_runtime` composes the four fragments and binds the Earnings adapter.
- `core.flight.runtime.FlightRuntime._dispatch_obs_policy` delegates both stages to `core.driver.run.run_experiment`; the registered OJW policies remain the only window executor.
- `core.driver.run.load_window_packet_binding` loads the prepared artifact once and confines it to `SPEECHRL_DATA_DIR`. `reproduction.window_controller.ControllerWindowHook` resolves each actual `SliceRecord` through that binding.
- `analysis.e21_window_pairing.stitched_windows_from_trace` and `assert_stitch_reproduces_outputs` are the existing recovery and completeness proof used by the predecessor producer.
- `core.predecessor_snapshot.load_predecessor_binding` is the existing stage-2 reader. `reproduction.repair_loop` uses it to align the declared predecessor window with the current repair request and applies the registered KC-E1f delivery rule.
- `core.flight.queue.FlightQueue` reuses matching serving profiles, but it cannot defer construction of a downstream runtime until an upstream receipt exists.