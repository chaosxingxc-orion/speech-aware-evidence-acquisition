# Four-window packet proof closure

This is a model-free closure check of the completed engineering proof SAEA-E21-CURRENT-EXECUTOR-FIRST-FOUR-FULL90-PACKET-PROOF-V2, attempt attempt-20260910-first-four-full90-packet-proof-v2. It records executor connectivity and bounded transport facts only. It does not score the one-call subset, inspect a reference or gold label, or support an effectiveness claim.

The authoritative generation manifest records study commit bb104ffd8c4533bd7f8ab8b10a37c038d8adde3c, configuration hash 0463c37ba507f476a29098a17d555a35ecb48e0c6b3eb2ced332eba78e0c67bf, protocol hash ee8711a2dd14b37c6d4d6659258a66e083836a49767281a58c5354981b5dcb27, and a completed discovery engineering subset containing only call 4320211.

The trace contains exactly four non-stitch model requests and four matching responses: req-0001-i0000 through req-0001-i0003. Each names the original source call, uses one query-role formal speech packet, has query_source speech_features, and records mmproj_loaded false. Their audio-source hashes, 90-second intervals, and predecessor delivery bindings match the four ordered fixed-window entries in the hash-pinned unit plan. The trace records no supplied evidence, retry, skip, or saturation. It records the shared phase-direct-only-v1 controller with saea-window-controller-context-v1 context and constrained substitution-splice delivery for every window. One stitch response and one sealed output row are present.

Measured authoritative cost is four calls, 360 speech seconds, 6,360 prompt tokens, and 1,098 completion tokens. Per-request prompt counts are 1,602, 1,585, 1,586, and 1,587. They equal the registered fit rows text plus speech counts: 419 plus 1,183; 402 plus 1,183; 403 plus 1,183; and 404 plus 1,183. Each completion is within the 1,024-token maximum. The fit separately reserves two special tokens and the maximum completion, producing required capacities 2,628, 2,611, 2,612, and 2,613 with margins 888, 922, 920, and 918. Request envelopes and request identifiers were not compared as wire hashes because the fit and generation carry different envelope identities.

The attached monitor reports requests_delta 2. That coarse monitor field is not the call authority; the sealed manifest and four COST trace records establish four actual calls. Per-request GPU seconds are NOT_AVAILABLE because the run path had no resource sampler. External serving telemetry remains separate from this closure check.

See `closure-receipt.json` for the content-free hash and count record.
