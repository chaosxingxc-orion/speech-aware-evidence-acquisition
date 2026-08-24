# E108 zero-copy flight — aborted at post-run metrics

## Outcome

The first flight of the E108 scientific cell on the resident zero-copy decoder
**completed every model contact and then failed to finalize**. All 338 contacts
were made, all 108 trajectories reached a final decision, and the trace,
trace manifest, and decisions file were written. The driver then refused to mint
the flight receipt because the GPU sample timeline was empty, so there is no
`flight-receipt.json` and the attempt is not finalized.

The refusal is fail-closed and was honoured: no gate was relaxed, no retry was
attempted, and no second attempt was flown. The exposure row is one-shot and
stays `consumed = no` — nothing semantic was read.

## The refusal, verbatim

```
File ".../core/driver/speech_native.py", line 12249, in _cli_speech_native_profile
    saturated_gpu = profile_server_slot_event_gpu_metrics(
File ".../core/driver/speech_native.py", line 7732, in profile_server_slot_event_gpu_metrics
    raise SpeechNativeProfileError("request GPU sample timeline is unavailable")
speech_aware_evidence_acquisition.core.driver.speech_native.SpeechNativeProfileError:
request GPU sample timeline is unavailable
```

`core.resources.GpuSampler.start()` performs one synchronous `nvidia-smi` poll
and returns *without starting its sampling thread* if that poll fails.
`summary()` then reports `NOT_AVAILABLE` with an empty `request_gpu_samples`
list, and `profile_server_slot_event_gpu_metrics` refuses rather than mint a
receipt with no GPU timeline. The failure is in telemetry acquisition, not in
the experiment: it is raised after the last contact, while assembling numbers
that the 2026-08-23 rulings §2.1 already made descriptive rather than gating.

Notably the same function's **slot-event lifecycle check passed first**: it
verified `launch_count == release_count == actual_contact_count == 338` with no
task straddling the window boundary, and only then reached the GPU-sample line.

## What the execution actually did

| Mechanical conjunct | Result |
| --- | --- |
| Final decisions | 108 / 108 |
| Split samples contacted | 108 / 108 distinct ids, 108 distinct query packets |
| Contacts | 338 (request = response = cost = 338 records) |
| Exact speech carriage | 338 / 338 requests, exactly one `role: query` part each |
| `query_source` | `speech_features` on all 338 — no transcript or text query |
| Speech packet hash present | 338 / 338 |
| mmproj | never loaded; process audit reports `mmproj_hit_count = 0` across live argv, open files, and process maps |
| OOM / host-spill / runaway markers | 0 / 0 / 0 |
| Native slot events | balanced, 884 launches = 884 releases service-wide; 338 attributable to this flight |
| Calls | 338 against a registered ceiling of 600 |
| Metered audio | 939.881 s against a registered ceiling of 1800 s |
| Resident service | PID 607 continuously resident, receipt `33639d3d…` unchanged, healthy after the flight |
| Attempt finalized | **NO** — no flight receipt |
| GPU telemetry | **UNAVAILABLE** — the refusal cause |

Token totals: 519,914 prompt and 8,390 completion tokens over 17,007.2 s of
summed request latency; wall clock 1,198 s (17:59:18Z → 18:19:16Z).

## Eligibility

**Not eligible for a semantic read.** Every label-blind execution conjunct
holds, but the attempt never finalized, so no hash-chained flight receipt exists
for a reader to bind to. Any semantic read needs a finalized attempt *and* its
own registered exposure row; neither exists.

## Descriptive serving numbers

Mostly unavailable: GPU median/P10, slot occupancy, throughput, and the
prompt-evaluation ratio are all produced by the receipt stage that refused.
Operator observations during the flight recorded 97–100% GPU utilization at
600–1200 MHz SM clock. Under §2.1 these numbers do not gate scientific
admission, so their loss is a telemetry gap, not a scientific one.

## Boundary respected

`decisions.jsonl` was never parsed — only its lines were counted. The
`MODEL_RESPONSE` channel of the trace was never opened. No prediction, label,
correctness, action reward, or response meaning was read.

## Suggested follow-on (not performed here)

The run data is complete and hash-stable: 338 request/response/cost records, 108
decisions, and the server log window are all on disk. A receipt could be rebuilt
from these persisted artifacts **with zero new model contact**, which would
finalize the attempt without spending the split again. That is a model-free
repair plus a driver change (making an unavailable GPU timeline a recorded
`NOT_AVAILABLE` rather than a hard refusal, consistent with §2.1 decoupling),
and it needs its own authorization — it is deliberately not done here.


## Addendum 2026-08-23 — finalized from disk (supersedes the sections above)

Everything above describes the attempt as it stood before finalization and is
kept verbatim as the abort record. The owner then decided Option B of
`docs/readiness/2026-08-23-e108-attempt-finalization-adjudication.md` §5:
registered model-free finalization. Under the new exposure row
`SAEA-SN-MF-EVIDENCE-E108-ZCOPY-FINALIZE-FROM-DISK`, committed before the
rebuild ran, the missing receipt was rebuilt from this attempt's durable records
by `saea-driver speech-native-finalize-from-disk` with **zero service contacts
of any kind**.

| Fact | Value |
| --- | --- |
| `flight-receipt.json` | written; sha256 `14be9f413ae0e7c760f8c45cd39b9a0b4d1cf4989b98581c84385144288a503a` |
| Data-derived content hash | `d5ef0aae01032d44cfbdfecfe74b86b344fa7f3558252f81e9e415609a05516c` |
| Attempt record | `OPENED` → `FINALIZED` |
| Final decisions | 108 / 108 |
| Contacts | 338 (request = response = cost = 338) |
| Exact speech carriage | 338 / 338 valid, 0 invalid |
| Native slot events in the window | 338 launches = 338 releases, none straddling |
| Failure markers | 0 OOM / 0 host-spill / 0 runaway / 0 request failures / 0 completion issues |
| GPU telemetry | `NOT_AVAILABLE` with an explicit `gpu_telemetry_defect` |
| Service contacts made by the rebuild | 0 |

The rebuild is deterministic over its data-derived fields: a read-only rebuild
run immediately beforehand produced the same content hash under two different
rebuild timestamps, and the written receipt carries that hash. `rebuilt_at` is
recorded in the `finalization` block and excluded from the content hash, since
no other receipt field has ever carried a timestamp.

The interrupted flight never persisted its server-log byte window, so the window
was re-derived as the trailing span holding exactly the traced 338 slot
launches, and then admitted by the driver's own fail-closed lifecycle checks
rather than trusted. The window independently contains exactly 338 prompt-eval
records, one per contact.

Zero-contact proof: the resident service's log is byte-identical across the
rebuild (1,117,739 bytes, last modified at the flight's own final slot release,
14:19:16), and its session receipt still hashes to `33639d3d…`. PID 607 was
never spoken to. The finalize path constructs no transport, client, session, or
socket at all, asserted by unit tests both statically over its bytecode and at
runtime with every contact primitive disabled.

Label blindness held throughout: decision rows were counted by a byte-level
counter that never decodes a line, and `MODEL_RESPONSE` records were counted by
channel without their payloads being touched (token accounting came from the
`COST` channel instead). Three live-flight fields that only in-memory decision
outcomes could supply — `parse_failure_count`, `response_text_sha256`, and
`profile.query_mapping_sha256` — are recorded `NOT_AVAILABLE` with a note rather
than reconstructed by reading what this rebuild must not read.

**Mechanical eligibility: PASSED.** See
`mechanical-eligibility-after-finalization.json`. This is mechanical eligibility
only. The frozen in-fragment reader (`m11-information-support-gate-v1` plus the
OOF evaluator) is a separate one-shot read that needs its own registered
exposure row after coordinator review, per adjudication §5.5. No prediction,
label, correctness, action reward, or response meaning has been read.
