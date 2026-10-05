# K8B memory observer diagnosis

The original branch10 guard stopped after81 model contacts when its Windows
physical-memory observer returned ValueError. It retained no specific rejected
field. The last valid reading was26.1081GiB; no valid reading breached8GiB.
Keep the original failure, STOP, worker and incomplete family unread.

The prospective observer now records bounded numeric failure diagnostics:
cross-clock freshness, roundtrip deadline, response identity/type, memory range,
observer process identity, JSON/transport framing. Do not log raw responses,
nonces or free-form exception contents. The guard retains these diagnostics.
All old stop conditions, timing limits and memory floors remain unchanged.
No reconnect, retry, cached reading, VM-memory fallback or service change is added.

The initial observer-only reproduction completed150 reads successfully. Windows
and WSL wall-clock offsets varied. This does not establish the old failure
cause, prove generation stability or justify weakening freshness checks.

`probe-config.json` declares180 observations at5-second intervals and8-second
transport timeout. Run `scripts/checks/windows_memory_observer_probe.py` with
the config file, exact SHA-256
`7a2bd73e19d9484fa8e06ef1d4c47177ccddca629487d5b99af4547177530677`
and a fresh output directory. It owns only its own memory observer, records
each observation, stops at the first failure and never dispatches an experiment.
The started receipt records the live PID; verify that handle before interpreting
an incomplete observation file. No GPU heartbeat is required for this CPU-only
probe.

Tests pass94; branch-aware coverage is95% for the observer and93% for the owned
process guard. See
`docs/receipts/continuation/2026-10-05-k8b-observer-diagnostics-prepared.json`.
Root227 permits this bounded diagnosis. Recovery remains a separate recorded
disposition after source-bound evidence and structural verification. Preserve
the configured population lifecycle and all original template identities.
