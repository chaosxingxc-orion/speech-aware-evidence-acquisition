# Windows physical-memory observer causal freshness repair

Owner227 authorizes bounded offline observer engineering. This branch makes no model or scorer contact, dispatch, recovery, service change, cache operation, or campaign-control change. The frozen K8B worker remains immutable.

## Established defect and incident uncertainty

The old observer compared independent Windows and WSL wall clocks within one second. A nonce-matched response from a fresh physical-memory read could therefore fail solely because the clocks differed. Synthetic tests first reproduced rejection at offsets of plus and minus 24 hours. Earlier dedicated observations already showed offsets varying from approximately -0.7 to +0.5 seconds. This is a demonstrated acceptance defect, not proof that it caused the historical K8B stop: its rejected response was discarded and the precise ValueError cause remains unestablished. No physical-memory floor breach was observed in the incident.

## Freshness argument

Keep the owned persistent process, unpredictable per-request nonce, exact increasing sequence, stable positive Windows observer PID, bounded framing, and fail-closed latch. The pinned observer script reads the request before querying AvailablePhysicalMemory and TotalPhysicalMemory, then echoes that request identity. It never returns a cached measurement. A valid response is therefore causally after this request and before its receipt. The WSL monotonic roundtrip, including process startup, remains at most eight seconds and bounds the sample age without comparing wall clocks.

Measure the physical-memory query duration with Windows System.Diagnostics.Stopwatch. Require a finite nonnegative duration no greater than the measured WSL roundtrip plus one millisecond for timing serialization precision. This tolerance does not extend the WSL deadline. Windows sampled_at remains finite and is retained as diagnostic metadata; wall time grants no freshness permission. Guard event receipts retain freshness=request-causal-monotonic-v1 and sample_elapsed_ms. Missing timing data, wrong identities, impossible timing, malformed/oversized/unsolicited responses, and deadline exhaustion still fail closed without respawn or fallback.

Preserve the configured admission and running floors; the current owner policy is 20 GiB startup and 8 GiB running. No K value or experiment configuration changes occur here.

## Validation and remaining proof

Tests-first old implementation: 11 failed, 31 passed. Final observer/probe/flight/batch guard suites: 129 passed. Branch coverage: observer 95%, process guard 93%. Diff whitespace validation passes. These are CPU-only synthetic tests, including large independent clock offsets, invalid elapsed values, process identity, timeout, failure latching, owned cleanup, and propagation into guard receipts.

The root-owned original-source long probe was inspected read-only at 85/180 successful reads with no failures, no result yet, and matching PID44809/start ticks53338932. Its partial samples hash is a snapshot, not a completed seal. It remains untouched and is not validation of this new implementation. A separately authorized bounded physical-Windows probe of the committed repair is still required before a prospective campaign adopts it. It must use fresh output custody and capture source hashes. Campaign recovery, admission, and scientific qualification remain root decisions.
