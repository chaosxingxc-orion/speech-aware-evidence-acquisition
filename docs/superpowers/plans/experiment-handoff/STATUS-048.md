# STATUS-048: complete-speech query GPU preparation active

Date: September 12, 2026 UTC. The broad multimodal-system goal remains active.

## Actual execution state

The idle no-mmproj SLURP answering service was stopped using its receipt-bound
stopper, with SIGTERM and no forced termination. Preserve the existing frozen
SLURP results and source; do not reopen role coverage.

The first Audio2Tool query preparation attempt ABORTED before its first neural
forward. Its guard exposed actual truncation at 32,768 audio samples in the
current processor. Four synthetic real-processor checks identified the cause;
four more verified the explicit audio-length remedy. All eight diagnostic
processor calls are registered; none loaded a neural model or used GPU.
Read [the named recovery](../../../readiness/2026-09-12-a2t-query-encoder-recovery.md).

The sole recovery is actively encoding under shared GenerationLease and
AttemptStore. Its frozen WSL source is
/home/chao/saea-worktrees/a2t-query-recovery-runtime-v1 at
4671c5b4cb2b766367bcb57353704a47c9572b6b. Observed process PID is 458;
revalidate it before control actions. The former service PID is historical.

At 2026-09-12T02:56:06.302272+00:00, 1608 of 4,020 registered contacts had
completed and 10 full 120-second actual speech spans had passed.
This is preparation progress, not a task-quality result. GPU use is active
but initial short-clip telemetry was 21-31 percent; do not claim full utilization.
Keep the registered batch-one recipe through this run. Measure load, processor,
forward, data-wait and artifact time before choosing later efficiency changes.

Active snapshot: DATA coordination/a2t-query-encoding-active-root-snapshot-v1.json,
SHA-256 69cebbe709aaf8de5ce3dba0bd3a80c306a54df5eb86933c81a7344cf69a4a89. Runtime config SHA-256:
4c71b5bc05e42a4646a91ff981b4f29ad5d0c6a79cc1e4cbf76f55acdaa63f86.
Any second failure stops this preparation flight; no automatic replay.

## Knowledge construction

The configured native-compatible compiler and snapshot export are implemented,
root-reviewed and actually materialized. They preserve all 152 tools, with 152
positive text facets and 152 complete supplied values, including 4 schema-only
tools. Public API shapes and construction-supported native forms are separately
labeled. Avoid guidance remains in values, outside the positive embedding key.

Corpus SHA-256:
1a4da985addf30f53b692b656d3907e15b60dd1a3c4da5c28a9cd2858bf5df82.
Snapshot file SHA-256:
6abf2ceacd2fb87242a5e9d15f4c468306feafe8e9bfe3e10fbb0be31800eb8e.
Compilation receipt SHA-256:
ee72a598fcedaeda24a2f072c41bd1cbebcbe9cb0ca8b4c530e47f69ab46b2b5.

A legacy aggregate example counter inherited 269 from an intermediate corpus;
the final rendered count is 190. Preserve that receipt and use the root
qualification, SHA-256
f1d947bf913a981dcae390910e51bda7f1cb44554a296d8cf70ac54e2ec4a63a.
The counter correction changes no model-facing corpus or snapshot bytes.
No runtime treatment or efficacy verdict follows from materialization.

## Next actions

Finish and seal the active full query attempt. Prepare and register the 152
matching text-key embeddings using the same pinned passage recipe. Bind shared
phase supply, then register actual-request fit and the full-system comparison.
Keep value-content component comparisons distinct from complete live-system
comparisons. Corrected and newly damaged native task outputs are the reward
evidence; retrieval similarity and larger values are not.

Read [the assembly note](../../../readiness/2026-09-12-a2t-native-value-and-query-assembly.md).
Current source review and 217-test integration checks passed before initial
dispatch; the remedy and current compiler paths passed 73 focused tests and the
engineering check. The recovery input protocol is immutable. No remote push,
new task-answering model, paid API experiment, or Stage-3 claim is introduced.
