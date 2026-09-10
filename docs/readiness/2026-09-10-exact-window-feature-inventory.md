# Exact-window feature inventory seam

Date: 2026-09-10  
Owner control: `OWNER-FEATURE-SERVING-007`  
Status: model-free engineering seam; no encoding or generation authorization

`core.preparation_windows.build_window_feature_inventory` now accepts named
`WindowRequestBatch` objects from the existing shared window materializer. It
does not cut a second set of windows. For every request it binds the batch name,
request key, payload hash, parent sample, normalized slice provenance, exact
slice bytes, and exact parent bytes under the confined data root. The numeric
request-key suffix must equal the source record's zero-based iteration plus
one. Payload audio_seconds and sample_rate_hz must equal the corresponding
source record facts. It refuses a path escape, a payload/source mismatch,
duplicate request keys within an arm, changed bytes, changed hashes, and files
that change while the inventory is built.

The duration comparison intentionally follows the existing SliceRecord and
runtime payload-binding contract. audio_seconds describes the verified cut
span. A declared transform may change the written WAV duration, such as by
adding tail silence, without changing that cut-span fact; the inventory does
not replace it with a duration inferred from the transformed carrier.

One inventory carries one explicit encoder identity: runtime-receipt SHA-256,
llama.cpp build commit, decoder GGUF SHA-256, and mmproj SHA-256. Identical
slice bytes in different arms or run-owned paths share one encoding input only
under that identity. Each original request remains listed separately, so
deduplication does not erase arm or request provenance.

`prepare_window_feature_inventory` stores the result through the shared
immutable preparation-artifact writer with contact class `model-free`. The
artifact state is `inputs-verified-features-not-materialized`. It records no
feature path, feature hash, cache hit, packet, or serving qualification.

## Remaining integration

An admitted preprocessing implementation must consume the inventory's unique
audio inputs, record its encoder contact separately, and bind produced feature
hashes back to every encoding key. For the raw-cache route, cache chunks must
be validated through the existing strict routines in
`core.model.speech_features`; do not add another cache-header parser. The
resident raw-audio path still needs a tested refusal before encoding on every
miss or invalid entry. For the packet route, FlightRuntime still needs the
previously identified packet-per-window binding and request parity proof.

Neither route may be promoted until complete output coverage, immutable cache
or packet receipts, preprocessing stop evidence, request fit, and a qualified
resident service identity are present. Serving geometry and CPU/GPU encoder
placement remain owner decisions.
