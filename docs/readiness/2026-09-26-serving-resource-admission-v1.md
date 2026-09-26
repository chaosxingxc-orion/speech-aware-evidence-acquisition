# Shared resource admission before system training

This completes the runtime guard requested by the
[resource amendment](2026-09-26-slurp-system-resource-and-prefix-amendment-v1.md).
It is engineering admission, not a training result or GPU launch registration.

## Implementation

The model fragment may opt into serving_resource_limits. The resident service
owner checks actual Windows memory before loading, samples Windows/GPU memory
after loading and throughout its existing foreground ownership loop, and writes
resource-history.jsonl plus an atomic resource-state.json. The snapshot binds
session ID, PID, start epoch and the complete policy hash. It does not depend
on the scientific heartbeat, network or assistant.

The registered transport wrapper checks this receipt immediately before every
actual send. Runtime and independently prepared tokenizer paths check it before
each endpoint. Rendering remains pure and request bytes/prefix order remain
unchanged. Guarded profiles cannot use FlightRuntime's fallback server spawn:
they require the coordinator-owned resident service that runs the observer.

Pressure closes admissions for the service lifetime. A later good reading
does not silently resume a partial flight. The hard floor, an unavailable
measurement, or an observer failure ends the owned service through the
existing stop_session identity checks, preserving its failure receipt. No
automatic service, attempt or scorer restart is introduced.

The [candidate model](../../configs/model/q4km-mmproj-free-system-np2-ctx24k-resource-guard-v1.json)
has two 24576-token slots, total 49152, prepared speech, no mmproj, the same
Q8_0 KV and prefill settings, and the following limits:

| Condition | Bound | Behavior |
| --- | ---: | --- |
| Windows available before loading | 32 GiB | Refuse loading below it or without a reading |
| Windows available during operation | 12 GiB | Latch new admissions closed below it |
| Windows hard reserve | 10 GiB | Stop the owned service below it |
| GPU free memory for admission | 2048 MiB | Latch new admissions closed below it |
| GPU hard reserve | 1024 MiB | Stop the owned service below it |
| Observation age | 15 seconds maximum | Refuse stale/future/mismatched receipts |

The 32 GiB startup threshold is loading headroom, not 32 training inputs.
GPU thresholds are prospective engineering reserves, not measured optimal
limits. The existing WSL cap and power/driver settings were not changed.

The shared batch prelaunch no longer runs gpu_warm.sh or gpu_ramp_test.sh
beside the resident model. Warmup and throughput measurements must use the
new family's registered model work. Historical scripts remain addressable.

## Verification and limits

[Validation receipt](../receipts/continuation/2026-09-26-serving-resource-guard-validation-v1.json):
337 related regressions, Ruff, shell syntax and all nine offline gates passed.
The focused guard module has 90.91% combined statement/branch coverage.
Tests execute the shared generation, tokenizer and service-owner connections
with substituted hardware and model transport. They verify no downstream
POST on refusal, correct process ownership on the stop seam, and no fallback
spawn without a resident coordinator.

A real read-only idle check found Windows available 46.81 GiB and GPU used
0 MiB/free 24137 MiB. No model process was alive. The hardware read took
3.43 seconds; the service loop also sleeps one second, so this is not a
one-Hz or instantaneous guard. A sampled monitor cannot guarantee protection
from every allocation/fault between samples. Loading and real flight peak
memory still require the registered proof. Windows commit and WSL swap
counters are not added here.

The old source worker, STOP and closed candidate recovery remain unchanged.
No GPU model/tokenizer/encoder/scorer work occurred during this change.

## Next execution work

The candidate is a model fragment, not an executable experiment. Existing
held actor baselines still declare four slots and cannot be used unchanged.
Derive matching two-slot experiment geometry when forming the concrete batch
cells. Preserve per-role prefix identity and reserve complete output plus
headroom for every actual actor, summary, comparison and batch-update request.

The inherited max512 in the model fragment is an actor template only.
Semantic limits, update batch size (four/eight under evaluation), complete
source/dependency bindings and new exposure/ExecutionPlans remain to be
frozen. Do not silently reduce output space or evidence to force a fit.
The next acceptance is a real registered complete batch/update/reexecution
cycle, followed by frozen full-roster evaluation and matched replication.
