# E21 window feature serving audit

Date: 2026-09-10  
Scope: pinned local runtime and configuration audit  
Owner control: `OWNER-FEATURE-SERVING-007`  
Contact status: no model, encoder, scorer, tokenizer, or service contact was made

## Conclusion

The repository has two plausible ways to keep mmproj parameters out of GPU memory after exact E21 windows are encoded ahead of a run:

1. Preserve the current raw `input_audio` request and prompt semantics, use a fresh current-build feature cache, and keep the projector in CPU memory with `--no-mmproj-offload`.
2. Promote the fresh window features into formal packets and use the existing decoder-only `input_speech_features` transport with an inference-role server that injects `--no-mmproj`.

The first option is the smaller bridge. The pinned cache patch has no cache-read-only or fail-on-miss switch, so it needs complete-roster and per-request cache validation. The second gives a stronger process boundary, but current packet binding is one packet per top-level sample and cannot address the many E21 windows under each call.

The owner conditionally prefers the smaller raw-cache route only if an explicit tested refusal-before-encoding boundary can be qualified; preflight validation alone is insufficient. Formal window packets remain the fallback, and no mode is ready or selected. The V2 successors select neither one, carry no executable replacement model fragment, and remain blocked on exact window preprocessing, current-build identity, request fit, and no-GPU-mmproj service qualification. Their scientific rosters, budgets, generation and delivery group counts, scoring rules, selection rules, and decision definitions remain those of their V1 parents.

## Current E21 path

All four fit/generation declarations in the accepted two-generation DR parent in `configs/experiment/e21-dr-shared-two-generation-v1.json` and all LOOP fit and generation cells in `configs/experiment/e21-loop-shared-two-plan-v1.json` bind `configs/model/q4km-e21-buf90-mmproj-gpu-04ccc72a-np6.json`.

That fragment declares `-c 36864`, `-np 6`, and `-ngl 999`. It omits `--no-mmproj-offload` and `LLAMA_MTMD_FEAT_CACHE_DIR`. Its own basis records GPU-resident bf16 mmproj, online encoding for every window, and deliberate non-use of the older cross-build cache. V2 retains this name only as `superseded_model_fragment`; it is not a fallback.

## Four distinct operations

| Operation | Existing path | Meaning |
| --- | --- | --- |
| CPU PCM preprocessing | `reproduction/obs_audio.py::encode_slice`; `reproduction/obs_loop.py::materialize_fixed_windows`; OpenJiuwen `reproduction/ojw/components.py::FeedBuffer` | Cuts, writes, hashes, and registers exact WAV windows. With no transforms or tail silence it is byte-identical to the historical writer. It creates no model features. |
| CPU mmproj encoding | `configs/model/q4km-preprocess-featcache-cpu-sidecar.json`; preprocess role in `core/session/lifecycle.py` | `-ngl 0 --no-mmproj-offload` places decoder and projector in host memory while a receipt-bound service fills a cache. This is a registered model contact. |
| GPU offline encoding | The preprocess role with a separately qualified GPU-offload identity | Temporarily uses GPU mmproj to fill a fresh cache, then stops before inference. Permission remains an owner decision. |
| Packet-only decoder inference | Inference role in `core/session/lifecycle.py`; `core/model/speech_features.py`; packet branch in `core/model/transport.py`; `rails/core_client.py` | Injects `--no-mmproj`, rejects mmproj arguments and legacy-cache environment, excludes mmproj from session `model_files`, validates packet and decoder hashes, and sends `input_speech_features`. |

Raw cached serving with `--no-mmproj-offload` is distinct from packet inference. It preserves the E21 wire and prompt shape and keeps mmproj out of GPU memory, but loads the projector in CPU memory and retains online encoding capability.

## Exact windows can be prepared ahead

`encode_slice` is the single byte-producing primitive used by plain and OpenJiuwen OBS. `materialize_fixed_windows` computes exact frame bounds and registers a `SliceRecord` with parent hash, times, duration, rate, byte count, media hash, transforms, and pre-transform hash.

The accepted DR parent fixes two generation groups, four correlated delivery derivatives, and its complete 90-second roster before contact. LOOP fixes its selected re-listen spans in sealed plans before contact. Both can be cut and hashed before preprocessing starts. Ahead-of-run materialization must reuse the existing frame rounding, `encode_slice`, and `SliceRecord` rules so every cache or packet audio hash names the exact historical request bytes.

Today the fixed-window path cuts windows inside generation before that sample's first request, and OpenJiuwen `FeedBuffer` cuts one immediately before dispatch. Ahead-of-run encoding requires moving the same deterministic operation before the separate encode pass.

## Smaller raw-cache bridge

The pinned patch `docs/patches/2026-08-11-mtmd-feature-cache.diff` stores chunks by media id and ordinal. `core/model/speech_features.py::legacy_audio_feature_cache_key` derives the media id as FNV-1a over exact encoded media bytes. Cache files carry token count and decoder embedding dimension followed by float32 features.

The patch has no read-only or fail-on-miss setting. `LLAMA_MTMD_FEAT_CACHE_VALIDATE` is not one: it disables cache loading, invokes the encoder, compares results, and may overwrite the cache. Missing or invalid entries fall through to online encoding. A cached-feature decode failure also falls back to encoding.

Minimum bridge:

1. Build a fresh cache for the exact complete cell-specific window roster under the intended current build. The historical cache is forbidden.
2. Write a SHA-pinned manifest binding each `SliceRecord`, audio SHA-256, FNV key, contiguous chunk filenames and hashes, token count, dimension, runtime receipt, preprocess session and stop receipts, decoder hash, and mmproj hash.
3. Add a shared preflight validator proving complete roster equality, audio-to-key derivation, contiguous ordinals from zero, valid headers and byte lengths, common dimension, and manifest hashes.
4. Run the same validation for the exact window before every dispatch. Refuse missing, changed, or invalid entries before sending the raw request.
5. Qualify a resident fragment with the fresh cache and `--no-mmproj-offload`; verify live GPU placement while preserving raw request, arm, and prompt order.
6. Keep the cache immutable during serving and record per-request cache-hit evidence. A strict internal guarantee would require a separately reviewed fail-on-miss patch; the pinned runtime provides no such switch.

This mode avoids a new packet arm or per-window packet transport, but still needs shared receipt and validation code. Counting directory entries is insufficient.

## Formal packet bridge

`core/session/lifecycle.py::_model_file_argv` requires receipt-pinned mmproj for `preprocess`; for `inference` it emits the decoder and injects `--no-mmproj`. `build_server_command` rejects inference mmproj arguments and `LLAMA_MTMD_FEAT_CACHE_DIR`.

`SpeechFeaturePacketV1` binds packet id, audio hash, encoder receipt, decoder and mmproj hashes, position and attention modes, dimensions, chunk hashes, and packet manifest. Promotion accepts only warm entries and refuses a missing ordinal zero. The strict promotion loader also binds dataset runtime view and preprocessing session, stop, and runtime receipts. Transport checks `query_source=speech_features`, `mmproj_loaded=false`, descriptors, decoder identity, and exactly one query packet.

Exact E21 gaps:

1. `FlightRuntime.speech_packet_bindings()` and `validate_speech_packet_set()` bind one packet to each parent sample and parent audio. E21 needs many packets per parent call.
2. `FlightRuntime._builtin_packet_promoter()` promotes `sample.media_relpath`, not windows. The Earnings adapter declares `raw-speech-windows` and 20 workers but exposes no pre-serve window roster.
3. `reproduction/obs_loop.py::window_request_factory` and OpenJiuwen `FrozenCoreASR` produce raw slice payloads with no packet descriptors.
4. DR's `bare-core` and LOOP's `fixed-legal-context` arms carry no packet fields; packet selection derives from `ARM_VISIBLE_FIELDS`.
5. E21 uses `evidence-first-system-v3`; packet transport accepts separate registered prompt orders. Exact packet rendering and fit are required.
6. FlightRuntime's local promotion loader only shape-checks, while `core/driver/run.py::_speech_feature_queries` uses the strict SHA- and runtime-view-bound loader. A shared window path must use the strict loader.

Minimum packet changes are a shared packet-per-slice binding and validator, a pre-serve exact-window promoter, and one packet-aware window payload helper used by both OBS executors. Payloads must retain parent sample identity while binding exact slice path, duration, rate, packet hash, representation and matcher ids, and `mmproj_loaded=false`.

## Common gates

- `FlightRuntime` hashes composed config, D2 arm, and split identity into the protocol. The selected mode and receipts must be composed before exposure registration.
- Preprocessing is a separate contact with its own plan, exposure row, runtime identity, session and stop receipts, and complete-roster receipt.
- The inference identity is qualified only after preprocessing stops. No V2 field claims a resident service is qualified.
- Request fit must use the selected representation. Raw fit does not qualify packets; packet fit does not prove raw serving used cache hits.
- Removing mmproj from GPU memory may permit more slots, but context, KV, feature inputs, activations, and largest request determine safe geometry. V2 selects none.

## Held successors

- `configs/experiment/e21-dr-shared-two-generation-v2.json`
- `configs/experiment/e21-loop-shared-two-plan-v2.json`

Each cell has `model_fragment: null`, retains the prior name under `superseded_model_fragment`, selects neither allowed mode, and leaves replacement model, cache manifest, promotion receipt, and fit receipt null. Each records `gpu_mmproj_allowed: false`, `runtime_identity_qualified: false`, and `contact_authorized: false`.

## Root decisions

- Select raw precomputed cache with CPU projector or formal packets with decoder-only inference.
- Decide whether offline preprocessing may temporarily use GPU mmproj.
- For raw cache, decide whether immutable cache plus validation and hit evidence is sufficient or a new fail-on-miss patch is required.
- For packets, select the packet-per-window id and receipt shape and packet prompt rendering.
- Select geometry only after exact fit and no-GPU-mmproj memory qualification.