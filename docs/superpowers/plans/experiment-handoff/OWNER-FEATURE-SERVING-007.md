# Owner feature preparation and resident serving amendment

Date: 2026-09-10 UTC. Decision ID: OWNER-FEATURE-SERVING-007.

## Owner direction

Prepare speech features ahead of experimental generation. Keep mmproj parameters out of GPU memory in the resident inference service so the memory can support useful request concurrency and context. This direction supersedes the continuation plan's G5 assumption that mmproj remains GPU-resident during raw-audio generation. Preserve completed experiments and their exact serving identities.

## Verified current state

The completed recovered KU-S3 trio used `slurp-g1-max256-recovery-np4-20260909-root`, frozen source `05b0f05ea87b52314845c3466d8f5a547551356f`. Its session receipt includes explicit `--no-mmproj`, role `inference`, only the decoder GGUF in `model_files`, and the speech-feature-root environment binding. It used four slots, 65,536 total context tokens, batch 2,048, microbatch 512, and a request output ceiling of 256. Its feature input was already prepared. The speech-arm full-roster capacity receipt measured a maximum requirement of 10,457 tokens including the 256-token completion reserve (16,384 per slot minus 5,927 minimum margin). At the same 65,536 total context, eight slots would provide only 8,192 tokens each, so simply doubling slot count would fail that measured request. This is a context constraint despite mmproj already being absent. The service is stopped; the current device query reports 0 MiB used and 0% utilization. Do not restart this completed flight.

The held G2 N/twin model already uses decoder-only speech packets, eight slots and 65,536 total context tokens. Preserve the registered 64-token N intent-output ceiling; the owner's 256-token amendment applies to KU-S3 slot generation. Recheck actual requests and packet coverage before admission.

The held E21 DR/LOOP V1 fragments still point to `q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, which explicitly places mmproj on the GPU and disables the historical feature cache. Do not dispatch these fragments unchanged after this amendment. Create source-bound successors after the exact-window feature preparation, transport and encoder identity are verified. Compare the smaller raw-input/fresh-cache/CPU-projector path with the formal per-window packet path; do not require a packet migration if the smaller path can satisfy the checks. Preserve all V1 fragments as historical planning records.

## Required implementation and acceptance

1. Separate PCM decoding and slicing from neural encoder output preparation. A ready audio file alone is not a ready speech-feature packet.
2. Materialize exact audio bytes for all fixed DR windows and the actual selected LOOP slices through the same shared observation code used at runtime. Deduplicate identical inputs across arms. Bind source audio, slice boundaries, encoder weights, runtime build, preprocessing configuration and output hashes. Reject missing, mismatched or concurrently overwritten features.
3. Prepare and validate the complete feature inventory before loading the decoder for a generation window. Use the existing shared preparation/cache/packet mechanisms; extend the carrier boundary only where needed. Record encoding contacts separately from generation. Do not use an old cache merely because it exists.
4. Use an inference session that cannot load mmproj at all when packet input is supported. `--no-mmproj-offload` only keeps an attached projector on the CPU; it is not equivalent to a decoder-only process and cannot by itself prove zero runtime encoding. Refuse cache misses during generation.
5. Check feature/request parity before migrating E21 from raw-audio wire input to feature packets. Keep the same speech content, actual slice and associated text range. The raw-input/fresh-cache/CPU-projector path can retain the current prompt layout; it still needs complete current-build cache validation and a defensible miss refusal boundary. CPU/GPU encoder arithmetic and runtime builds may differ; do not assume byte identity or silently pool the successor with an older serving path. Register any necessary engineering proof before contact.
6. Measure actual maximum requests with the complete output reserve and the required memory margin. Choose one serving geometry per comparison group. Distinguish parallel slots, prompt batch size and microbatch size; do not increase them solely from nominal free memory.
7. Keep one root-owned inference service and one generating experiment. Do not add an independently launched CPU sidecar during an SLURP campaign. The existing no-overlap rule remains in force.

## Root engineering preference

Prefer the smaller raw-audio bridge for E21: precompute a fresh, current-build exact-window cache and keep the projector in CPU memory with `--no-mmproj-offload`. Preserve the historical audio wire and prompt layout. Do not treat a preflight check alone as proof that the server cannot encode: the pinned 04ccc72a cache implementation falls through to encoding on misses, invalid entries and cached-decode failure, and its VALIDATE mode deliberately re-encodes. Require an explicit, tested refusal boundary before unintended encoding, with immutable source-bound cache artifacts and observed hit evidence. A minimal shared serving-runtime guard may need its own reviewed build and runtime receipt. Keep the formal per-window packet route as the alternative if this boundary cannot be qualified. Neither route is ready to run today. This engineering preference does not authorize extra generation or relax scientific matching.

## Offline encoder placement clarification

A clarification is pending: whether this direction excludes GPU mmproj only during resident generation, or also during the separate preparation window. The working interpretation retains the previously accepted, separately registered exclusive GPU encoding window followed by complete encoder unload. CPU-only preparation remains an available alternative. No new encoding contact is authorized or performed by this document; wait for the applicable input before a placement-dependent dispatch.

## Efficiency accounting

The stopped G1 monitor reports 3,041.55 seconds observed, 1,621.46 active and 1,420.09 parked (46.69%). Its sampled request delta is a lower bound, not the completed 3,000-generation count. mmproj was already absent, so investigate avoidable request validation and handoff waiting as well as memory capacity. Keep the GPU off while no scientifically and technically ready task exists.
