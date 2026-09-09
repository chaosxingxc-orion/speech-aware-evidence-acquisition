# Root-owned coordinate-fit lifecycle

`core.flight.cli coordinate-fit` is the shared entry point for a cold full-roster tokenizer fit. It selects a declared cell with the existing `prompt-fit` execution stage, acquires the root-owned `GenerationLease`, and calls the existing `fit_phase_runtime` through its attach callback.

The fit performs contact-free CPU request materialization first. Only after the attach callback is reached may the coordinator start the existing `scripts/serving_session.sh start` wrapper. The coordinator waits for one identity-matching resident session, starts the existing ten-second `scripts/serving_monitor.py sample`, and attaches through `attach_worker_session`. It never duplicates serving arguments, starts a second wrapper, restarts a failed wrapper, or stops a wrapper it did not start.

When the output artifact already exists, the coordinator uses the existing warm path in `fit_phase_runtime`: artifact inputs are verified without acquiring a lease, starting a service, starting a monitor, or making endpoint contacts. After a cold success, the coordinator releases the fit lease and keeps its started serving wrapper in the foreground until root uses the existing serving stop path. A cold fit failure prints a lifecycle event and leaves the lease metadata and any started wrapper for root reconciliation; it does not replay or kill them.

Lifecycle events are fsynced to `$SPEECHRL_DATA_DIR/coordination/<session-id>.coordinate-fit.jsonl`; each event carries UTC and monotonic timestamps plus run, attempt, and session identity. The monitor process is recorded in a persistent ownership receipt and is reused only while its recorded PID is alive. Standard output receives only compact progress events and the final structured result; prompts, token payloads, and raw speech are never printed.

Root acceptance: the combined coordinator/campaign/queue/preparation suite passes87 tests.
The root tightened a false-positive monitor validation test: a valid command binding now
precedes the invalid-PID cases, exposing and fixing acceptance of boolean, zero and negative
PIDs. The coordinator-to-real-fitter test uses a real lease and immutable artifact writer,
with only model endpoints and transport replaced by test doubles. No live contacts occurred.
