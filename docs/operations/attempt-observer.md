# Attempt observer

Use `scripts/watch_attempt.py` to observe one already-dispatched campaign from local metadata. Root owns campaign dispatch, the serving process, scoring handoff, and every operational or scientific decision. The observer has no restart, retry, scoring, service-control, or scheduling authority.

The script binds the campaign PID at startup using its process start ticks and command hash. It validates plain run and attempt identifiers and derives the authoritative ledger path itself:

```text
<data-root>/attempts/<run-id>/<attempt-id>.json
```

It does not accept an arbitrary attempt-ledger path. A missing ledger before attempt creation produces one waiting event while the bound PID remains live. An existing ledger must have schema `saea-attempt-v1`, exact run and attempt identities, a recognized state, and finite nonnegative call and audio debits. Invalid metadata terminates the observer with an error event.

Run the observer locally with a 60-second interval:

```bash
PYTHONDONTWRITEBYTECODE=1 python -B scripts/watch_attempt.py \
  --pid <campaign-pid> \
  --data-root <speechrl-data-root> \
  --run-id <run-id> \
  --attempt-id <attempt-id> \
  --output-dir <observer-output-directory> \
  --interval 60
```

Local polling makes zero model calls. It emits only material summaries: initial waiting, state changes, first progress, a single ten-minute unchanged-call stall, resumed progress, terminal attempt state, invalid metadata, process termination, or PID identity loss. An optional explicit manifest path may add strictly identity-bound manifest status; it does not change attempt-ledger authority.

Delegate the local script session to a smaller ChatGPT observer subagent and forward only these material-event summaries. Root must not periodically scan campaign logs or request unchanged progress summaries. The child owns waiting on the script output; local polling must not invoke a model per interval. It must not read partial task quality, raw answers, transcripts, labels, references, or scores. Root receives each summary and makes the decision. The observer never retries a campaign, restarts a service, or turns this script into a scheduler.

`FINALIZED` means generation finalization only. It does not establish that official scoring completed. On `FINALIZED`, the observer hands the campaign to the scoring owner; root must not infer score completion from the attempt state.
