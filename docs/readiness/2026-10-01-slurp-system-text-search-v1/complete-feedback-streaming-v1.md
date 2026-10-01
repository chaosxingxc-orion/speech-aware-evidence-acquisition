# Complete feedback at measured trace volume

Recorded by ChatGPT root on 2026-10-01 under owner214/215. This is an offline
engineering correction. It changes no scientific policy, model budget, frozen
worker, queue, serving geometry, score job or read allowance.

## Two concrete integration defects

The initial CONTROL2 seed trace is 262,916,398 bytes. Root obtained this size
from filesystem metadata without reading task answers or quality. The original
proposer capsule's 128 MiB artifact limit would reject that complete trace.
Increasing a memory limit would not address growing multi-round history.

The complete-system cost reader also expected a request ID inside each model
response payload. The production adapter instead binds the response through
its `<request_id>/response` record ID. Valid recorded token usage was therefore
reported as unavailable. Production-shaped synthetic records reproduce this
defect and verify the correction.

## Implemented behavior

The existing capsule now supports create-only, disk-backed storage. It streams
every registered artifact into 262,144-character UTF-8 chunks, preserving all
bytes, including line endings and punctuation. The full source hash and byte
count must match before the capsule is returned. Every supplied page rechecks
its chunk hashes and file custody. No case selection or truncation occurs.

`proposal-capsule` uses this storage under the existing external archive's
`capsule-material/<branch>/<allocation>/` directory. The model still receives
the identical artifact IDs and character-page interface; storage paths and
chunk indexes never enter its context. Complete earlier learning inputs are
expanded recursively through their typed pins. Blind inputs retain their
existing feedback refusal. Insufficient disk space, altered or linked chunks,
invalid UTF-8 and unregistered artifacts fail closed. Partial failed caches are
preserved and cannot be overwritten by another invocation.

Small in-memory callers retain the existing limits. These are packaging limits,
not proposal token allowances. Disk storage does not change the registered
input/output/contact limits or authorize a live provider.

The cost reader streams terminal and trace records after verifying their pins.
It joins model responses by the production record identity, tolerates record
ordering, rejects duplicate terminal/request/response identities and retains
compact usage indexes instead of answer bodies. Failed model contacts count;
missing usage remains unknown. Tool attempts, results, failures and rejections
are reported separately from unique recorded invocations. None is interpreted
as causal credit for a role.

The shared bundle/reward-link verification path is unchanged and may still load
full artifacts. The memory proof below measures capsule packaging, not the
entire feedback pipeline. Complete-family qualification and the exact root
READ countersignature remain prerequisites for real feedback export.

## Evidence

The related `test_system*.py` selection passes 569 tests. Capsule and feedback
reader statement coverage each round to 99%. The suite includes real loopback
transport fixtures, but makes zero external model or research proposal calls.
An initial test command used an unavailable pytest coverage plugin and ran no
tests; the preserved corrected run uses the installed coverage runner.

A separate 260 MiB synthetic artifact was copied into 1,040 chunks and fully
reconstructed to its original SHA-256. Four boundary pages matched the source.
Measured Python traced memory peaked at 1,876,836 bytes during packaging. The
proof used no real task result and made zero model contacts. It is an engineering
measurement, not task efficacy or end-to-end resident-memory evidence.

Seven broader checks pass, with existing advisories. The two previously
reported frozen native-capacity algorithm annotations remain unchanged and
unwaived. Source hashes, test reports, the synthetic proof, operational metadata
and gate logs are pinned in the
[continuation receipt](../../receipts/continuation/2026-10-01-system-text-feedback-streaming.json).

At the recorded operational checkpoint, seed is FINALIZED with a verified seal,
400 rows and one successful official score job. A/A is still OPENED. The
finalize-scoring path attaches saved scores; the existing saved-score receipt
adapter can derive the reader's envelope after the whole-family READ gate
without another scoring job. No quality value was read for this correction.

Exact proposer/provider admission, the pending owner budget decision and
complete initial feedback still precede live L/B proposals. The independent
milestone remains outside the optimizer. All other research holds remain in force.
