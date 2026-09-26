# Resource and prefix amendment before the first real training batch

## Owner direction and precedence

The owner confirmed updates after each sampling batch, then required explicit
VRAM/token analysis before fixing the batch size, at least 10 GiB available
for Windows, consistent prefixes during sampling, and adequate output space.

Retain the cadence decision. Supersede the 32-input size assumption in the
[earlier decision](2026-09-26-slurp-system-batch-cadence-owner-decision-v1.md).
Its 54 updates and 216 construction-score jobs are historical draft arithmetic,
not the new schedule. Neither the batch size nor the new serving geometry has
been admitted. The 32-record runtime memory limit is a different bound; it is
not 32 simultaneous inputs and must also satisfy the actual token limit.

## Read-only evidence

Read the [operational audit](../receipts/continuation/2026-09-26-system-resource-history-audit-v1.json).
Root read only usage, cache, finish, service and resource metadata. No isolated
control quality, answers or scores were inspected.

The inherited service uses prepared speech features, no mmproj, Q8_0 K/V,
four 24576-token slots (98304 total), a 2048-token batch and 512-token
microbatch. Its CPU prompt cache is disabled. Keep these as the comparison
reference; do not silently edit or restart the closed source session.

Across 514 monitor samples from 21:38:56 to 23:16:39 UTC on September 25:

- GPU memory used was 22988 MiB in every sample, about 22.45 GiB.
- Windows available memory ranged from 15.97 to 21.81 GiB, last 18.35 GiB.
- WSL available memory ranged from 36.16 to 40.71 GiB.
- No recorded Windows sample crossed 10 GiB. The final sample preceded the
  failure by about 20 seconds; unobserved peaks are not excluded.

The 10 GiB value is an owner engineering reserve, not a universal Windows
reboot threshold. CUDA illegal access and the later 0x116 event do not prove
an out-of-memory root cause. Continue diagnosis without making dump access a
substitute for the measured resource work.

The completed control's maximum prompt sizes were 3811 (Perception), 14264
(Solver), 14362 (Reviewer), and 14408 (Planner). Every request reserved 512
output tokens. One of 1011 Reviewer responses reached that limit. Expanded
smoke's returned Solver requests reached 15353 input tokens, with four
contacts lacking returned usage. None of these observations proves the new
memory-bearing or semantic requests fit.

## Separate the four capacities

1. An update batch counts distinct training inputs before one policy update.
2. Replica count is four complete independent executions per input; it is
   not four permanently resident copies of the model or every trajectory KV.
3. In-flight slots bound simultaneous model requests. The native executor
   obtains one slot and serializes each trajectory's contacts; the next
   node is not launched concurrently with its own predecessor.
4. Context and prefill microbatch sizes determine separate KV and working
   memory demands. Merely reducing the update batch does not shrink an
   already allocated server KV cache.

Trajectory and feedback records are persisted outside GPU memory. However,
the semantic batch synthesis consumes all eligible group operations plus
the current memory pool in one request. Its context grows with update-batch
size, so an arbitrary batch size is still unsafe even with low concurrency.
Do not concatenate all full actor traces into one batch synthesis request;
retain the established per-trajectory summary/comparison/group/batch stages,
without dropping source evidence or substituting a lossy host summary.

## Prospective resource admission

Use a two-slot, 24576-tokens-per-slot decoder-only configuration as the first
resource-sizing candidate, subject to actual fit and a registered bounded
proof. Do not launch it from this amendment. Keeping per-request context and
reducing total context to 49152 addresses KV allocation directly.

The pinned GGUF has 48 layers, four KV heads, and 128-dimensional keys/values.
With the local 34-byte-per-32-value Q8_0 layout, ordinary full K/V tensor
payload is about 4896 MiB at total context 98304 and 2448 MiB at 49152.
The approximately 2448 MiB reduction is an analytical estimate, not a
measurement of total VRAM, temporary CUDA buffers, or backend reliability.

Evaluate small update batches, initially 4 or 8 inputs, using complete
actor and semantic input/output envelopes. Freeze one batch size, group
count and deterministic order before outcomes. Keep the tail. Retain four
complete trajectories per input; never launch all batch trajectories at
once. Do not treat these construction batches as statistical effectiveness
screens; final evaluation and replication still use full B1080.

For U declared construction batches, construction scoring uses 4*U complete
jobs and at most U memory updates. Actor episodes remain 6820. More frequent
updates also increase scoring/setup waits and exposure to memory drift;
choose capacity and cadence jointly rather than shrinking blindly.

Before new flight admission, use the shared service/request path to enforce:

- At least 10 GiB measured Windows available RAM throughout the run; begin
  draining new admissions at 12 GiB as a safety margin. Missing or stale
  host readings refuse new admission. WSL MemAvailable is a separate metric.
- Monitor Windows commit pressure, WSL memory/swap, and GPU used/free/total
  memory together. A 44 GiB WSL cap does not prove host headroom.
- Record resource samples independently of ChatGPT and join them to request
  start/end, role, slot, actual input, output reservation, generated/cached
  token counts, and resource high/low watermarks. Use a faster resource
  guard than the fifteen-minute scientific monitor.
- Remove the unattended requirement for separate torch matmul warmup while
  the model is resident. Existing gpu_warm/gpu_ramp scripts allocate another
  CUDA context and matrices; their contribution to this incident is unknown.
  Use the new flight's registered model work for warmup and throughput records.
- Fit actual requests including history, tool schemas/results and speech
  tokens. Require input + full output reserve + registered margin <= slot
  context. Fit again when new memory is materialized. A fit failure stops
  at a declared boundary; do not truncate evidence/output or replay the batch.
- Set actor and semantic output limits separately. In particular, a batch
  operation JSON cannot inherit the SLURP answer's 512-token limit by habit.
  Account for its complete permitted operation structure before generation.

These are admission requirements, not a claim that all guards are implemented.
Currently startup refuses below 12 GiB but fails open if the Windows reading
is absent; the runtime monitor only warns below 6 GiB. Close this concrete gap
in the existing shared path before starting the new family. No power, driver,
TDR, WSL cap or service setting was changed during this audit.

## Prefix and fair comparison

Preserve stable task contract, ordered knowledge, speech identity, memory
version and tool schema bytes for the same input/role across replicas.
Vary sampling seed in request parameters, never by injecting seed, run ID,
timestamps or replica prose into the model prefix. Keep changing rollout
history and node state in the suffix. Different generated histories must
remain different; do not reuse another trajectory's mutable KV state.

Keep the shared speech-query-prefix-v2 ordering and slot affinity where
possible. The native local-tool path releases its slot while CPU work runs,
so later reacquisition can reduce cache reuse. Measure that effect before
changing scheduling or claiming guaranteed prefix hits.

Existing completed control weighted cached/input token fractions are 61.75%
Perception, 58.35% Solver, 96.20% Reviewer and 96.53% Planner. These are token
fractions from returned cache metadata, not percentages of requests served
entirely from cache. Prefix reuse already works and should be preserved.

Freeze prompt/template and common prefix changes together across the matched
family at a run boundary. Memory is fixed within a training batch and changes
only after the sealed update. A new memory version naturally changes the
relevant prefix/suffix bytes; retain its hash and separate the cold prefix
cost from steady reuse. Evaluation policies differ only in their declared
memory contents/interface, with matched serving and output settings.

## Immediate sequence

Complete deterministic batch sizing and the shared runtime resource guard;
register the smaller serving geometry and complete output envelopes; then
perform the new family's bounded fit/form proof and first real batch. Do not
reopen the closed candidate comparison. Use existing prepared packets and
background WSL ownership. No extra unregistered performance experiment,
encoder contact, task scoring replay, or test/DEV6570 access is permitted.
