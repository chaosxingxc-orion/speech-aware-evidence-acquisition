# Event-driven experiment monitoring

Owner direction, 2026-09-14: delegate routine progress reading to a smaller
ChatGPT observer. Keep planning, decisions and review with the root agent.

## Responsibilities

- Run the local metadata watcher in WSL. Poll explicit attempt and process
  metadata every 60 seconds; make no model request during local polling.
- Let a smaller ChatGPT observer own the watcher tool session. Read concise
  event metadata, not full logs, answer text or unreleased scores.
- Forward first progress, phase changes, completion, failure, lost observation,
  one sustained-stall event and resumption after that stall. Suppress unchanged
  status. Do not send a root message for every local poll.
- Include event time, run/attempt identity, process identity, observed state,
  charged contacts, evidence path and any decision needed.
- Let root inspect source evidence when a meaningful event requires judgment.
  Keep service control, scientific admission, result release and dispatch with
  root. Do not restart, replay, score or expand a flight from the observer.

## Launch and lifetime

Provide the observer exact run ID, attempt ID, campaign PID, attempt path,
watcher path/hash, a fresh output directory and a manifest path when available.
The observer must launch the watcher itself and retain its own tool handle.
Do not rely on transferring an opaque root-owned tool session.

The forwarding guarantee is session-scoped. An exited observer does not keep
watching and there is no unattended wakeup transport. Start and bind an observer
with each actual campaign; do not poll a closed flight. Mechanical polling
uses no model calls, but observer reading and summarization still use tokens.

## Verified implementation

Use DATA/coordination/bounded_campaign_watcher.py.
SHA256: 2048decf61d6500836b2a9a115fe146af8f9748515bd7da9f2ee63f7b6d13a6c.

An isolated synthetic process/metadata proof demonstrated that the observer
can own the watcher session, receive an event and forward a labeled summary
to root. The helper and watcher exited cleanly. The proof made zero research,
model-service or GPU contacts and read no real task output.

Proof: DATA/coordination/monitor-observer-delivery-proof-v1/proof-receipt-v1.md.
SHA256: b7c4667c4f796917dd88c3818b61d8c61d5af8c32987c50bec5001a19cd174ea.

Operational handoff: DATA/coordination/
slurp-native-candidate-refresh-tools-train-fold-a-recovery-v1/observer-handoff-v1.md.
SHA256: 83a1da45d712af4191a7f0c34e38e3dbb1b9c6e173c9e2a872fb21044fcc6c52.

Current flight state is in STATUS-101.md. The prospective bounded-evidence
campaign has a session-bound observer attached. Read its material events and
current process evidence; never poll either closed predecessor.
