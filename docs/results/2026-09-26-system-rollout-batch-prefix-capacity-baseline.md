# Whole-system rollout batch, prefix and capacity baseline

## Owner decision and scope

Keep 32-input update batches unfrozen. Complete the first learning loop with
four TRAIN inputs, four independent whole-system trajectories per input, and
at most two concurrent actor episodes. Update only after the sampling batch
has sealed and its official terminal feedback has been joined. This choice
is an engineering construction scale, not an effectiveness sample size.

Separate four quantities: inputs per policy update, trajectories per input,
simultaneous requests, and the token length of each request. The product of
the first two is work volume; it is not the number of GPU-resident KV contexts.
Therefore 32 inputs do not by themselves imply a GPU crash. They increase
aggregation work and may increase a synthesis request unless explicitly bounded.

## Measured actor execution

All 16 first-batch episodes finalized. The four complete manifests each have
one official score. Their 67 requests reached a maximum prompt of 10810 tokens
and a maximum completion of 274 tokens. Output caps were 512 for most roles
and 1024 for Reviewer; all 67 stopped normally, none hit the cap.

Across 889 resource observations, GPU used peaked at 20432 MiB, GPU free
reached a minimum of 3706 MiB, and actual Windows available memory remained
at least 26.321 GiB. This establishes observed short-batch operation only;
sampling cannot rule out brief peaks or prove future stability.

Read the complete resource audit and prefix audit in ../receipts/continuation/.
The service is decoder-only, no-mmproj, using verified prepared speech
features. Total context is 49152 with Q8_0 K/V and two 24576-token actor slots.
Prefill token batch 2048 and microbatch 512 are separate from the four-input
learning batch and the two-request concurrency limit.

## Complete-trajectory summary capacity

The original representation repeated nested internal context: a single
trajectory required 57386 to 99721 input tokens. Reducing the number of
training inputs would not fix that individual request. The versioned compact
wire view preserves the exact model-visible requests, raw responses, actual
tool events, transitions and final delivery, with reversible shared JSON
references. Original immutable records remain addressable.

All 16 compact requests were measured through the actual renderer/tokenizer.
The longest has 21528 input tokens. With 2048 output and two special tokens,
a 24576-token slot leaves only 998 tokens, below the registered 3072-token
operational reserve. Generation on that geometry was refused.

The summary service assigns the same total 49152 context to one slot.
All 16 requests have unchanged individual token counts; the minimum remaining
margin is 25574 after output and special tokens. Analytical KV payload stays
2448 MiB. One-slot idle GPU used was 20434 MiB, but long-prefill generation
must still be observed. A tokenizer fit is not a measured peak-memory proof.

Keep output space explicit for each later comparison, proposal and synthesis
stage. Do not squeeze output caps to make an oversized prompt fit. Fit those
real source-bound requests after they exist; do not treat summary fit as
authorization for every later stage.

## Prefix and policy consistency

Within one input, role and policy version, keep common message bytes,
knowledge serialization and speech prefix stable across replicas. Put random
seeds in decoding parameters, not prompt text. Put varying observations and
own trajectory histories after the shared portion. Different roles and
different inputs need not have identical entire prompts.

The audit found 16 comparable role/visit groups with identical first messages
and four Perception groups with identical complete messages. Positive cache
reuse appeared in 65 of 67 responses; this is not a controlled speedup estimate.
Never replace a trajectory's dynamic history to manufacture a cache hit.

Freeze memory, policy and prompt-prefix version for the entire sampling batch.
If a prefix or memory update is accepted, apply it uniformly to all replicas
of the next batch and bind its version in the trajectory. Cached prefixes
improve throughput; they do not supply a memory-safety guarantee.

## Host and GPU protection

Keep the independent Windows-owned WSL service and monitor running without
network or ChatGPT-credit dependency. Sample GPU allocation, host memory,
slot occupancy and throughput every ten seconds; join request token counts
from the actual request/response records.

The current guard requires 32 GiB Windows available before service startup,
closes new-contact admission below 12 GiB Windows available or 2048 MiB GPU
free, and stops the owned service below 10 GiB Windows or 1024 MiB GPU free.
Unavailable or stale resource state fails closed and a stop remains latched.
Do not automatically retry an experiment after a pressure or service fault.
A sampled guard cannot guarantee that Windows always retains the floor during
a sudden external allocation, so preserve operating headroom above 10 GiB.

## Immediate execution status

The first summary launch held before all model contact because its root
decision receipt omitted the required schema. The service remained healthy.
The named v2 successor corrects only this binding and uses fresh run IDs;
it preserves the service, request contents, output reserve and research
question. No second recovery is allowed.

After summaries seal, root verifies their source bindings and performs the
system-level analysis. Proceed through comparison and batch memory update
before the next prepared four-input batch. No learned improvement or stable
training-free RL gain is established by this resource diagnostic.
