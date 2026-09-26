# Resource-receipt publication defect in memory batch002

The seventh actor stopped during Reviewer dispatch because opening the resource
snapshot raised FileNotFoundError. The complete final traceback retains this
cause; the earlier operational checkpoint had only the wrapped error.
The six completed actors scored once. The eighth actor never started.
No task answers or quality have been read.

The resource guard publishes a new snapshot through a temporary file followed
by os.replace. On this WSL Windows-mounted data directory, concurrent readers
can observe the destination as missing during replacement. The shared real
publisher/reader functions reproduced421 such failures during a six-second
stress run; a native WSL directory had none. This is a stress reproduction,
not an estimate of normal incidence.

Only missing-path reopening is bounded: five opens, at most40ms total sleep.
Permission errors, malformed content and permanently absent snapshots fail
closed. A successfully reopened snapshot must still pass service identity,
policy identity, observation age, actual memory floors and latched decisions.
Transport is invoked at most once, with unchanged request bytes. Recovered
filesystem reads are logged. No stale receipt cache is used.

The same stress run after repair recorded166 recovered read events and zero
failed admissions on the Windows mount; the native control remained clean.
42guard tests pass, including original-request single dispatch, continued
rejection of stale/wrong/low-memory/corrupt receipts, bounded permanent absence
and no wait for other errors. Module coverage is93%.18memory regression tests
and all nine repository offline gates also pass.

The evidence supports a named operational recovery of the missing matched pair.
It says nothing about memory quality or training-free learning gain.
Keep earlier three complete pairs and their scores; use fresh identities for
both members of pair4, with all scientific settings retained. Exclude the
aborted partial actor from complete trajectories, retain its costs, and allow
no second recovery. The fixed guard does not change resident model geometry,
candidate/slot knowledge, decoding or the provisional memory.

Receipts:
- docs/receipts/continuation/2026-09-26-system-memory-batch002-resource-repair-proof.json
- docs/receipts/continuation/2026-09-26-system-memory-batch002-recovery1-validation.json
- docs/readiness/2026-09-26-system-memory-batch002-recovery1-v1/protocol.json
