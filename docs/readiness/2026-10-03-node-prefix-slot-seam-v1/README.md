# Optional node-prefix slot scheduling seam

## Implemented scope

Extend the existing `execute_speech_agent_workflows` entry point with optional `prefix_slot_bindings`, mapping opaque, versioned prefix-family names to distinct in-range slot IDs. An opted-in native invoker supplies `prefix_family` on every existing `run_contact` call. This is a shared executor capability, not a new model client, controller or carrier framework.

The executor copies the mapping before execution. Each prefix family serializes all its contacts across samples on its declared slot. Different families run concurrently, and a single trajectory still serializes its own contacts. The routing key never enters model context or alters callback request bytes. The caller must bind the key to the exact policy/template/tool-schema identity; a node label alone is not proof that token prefixes match.

Queued cancellation never submits a contact. Cancellation after submission, including repeated cancellation and a later worker exception, retains the family lock until the actual synchronous worker settles. Local CPU tool work holds no prefix slot. Missing/unknown families, duplicate slot assignments, noninteger or out-of-range IDs and legacy invokers fail before the corresponding contact.

With `prefix_slot_bindings=None`, the existing trajectory-affinity branch and its request behavior remain unchanged. No current FlightRuntime configuration enables the new seam. No frozen experiment, geometry, serving/cache parameter, read allowance or queue is modified.

## Verification

The new interface tests failed for the absent keyword before implementation. The completed suite passes177 tests through the actual installed OpenJiuwen executor and synthetic frozen-core callbacks, including native SLURP episodes, Audio2Tool native episodes, Earnings native branches and the Earnings22 consumption profile. Shared executor statement coverage is98%. Scoped lint and the engineering base check pass.

The tests verify fixed routing across changing samples and role transitions, exclusive slot ownership, cross-family parallelism, queued/in-flight cancellation, exceptions, copied bindings and local-tool interoperability. They do not measure llama.cpp cache hits, output quality or real carrier execution. Existing third-party deprecation warnings remain unchanged.

## Remaining work before a real flight

1. Bind the optional mapping through the shared FlightRuntime execution envelope and pin it in dispatch metadata, with an explicit reachable-role/prefix registry. Keep it outside text-policy search and preserve the default request path.
2. Pre-register a small cache/structural proof, including the same requests under baseline trajectory affinity, actual maximum legal request capacity and full output reserves. Freeze the worker before contact.
3. Verify live cached-input/processed-input measurements, complete delivery custody, queued time and wall-clock throughput. Only then decide whether to couple this scheduling factor to separately optimized node text.

Slot affinity does not prove retention, cache-hit rate, speedup, unchanged numeric outputs or task benefit. Current four-slot geometry stays fixed. The SLURP heartbeat remains paused; independent resource telemetry continues. Owner227 permits reviewed bounded engineering before8x400, which still requires a human decision. Other carrier holds remain.
