# First whole-system construction batch: resource and prefix envelope

Status: HELD. This is a concrete sizing/configuration packet, not an exposure
registration, a token-fit receipt, a GPU launch or a final algorithm baseline.
It implements the owner's resource-first amendment without reopening any
closed experiment. All new work was model-free in WSL Ubuntu-24.04.

## Separate the three sizes

An update batch contains four inputs. Each input receives four independently
sampled complete Perception/Solver/Reviewer/Planner trajectories. The resident
service admits at most two episodes concurrently, with serial role contacts
inside each episode. Sixteen trajectories are therefore a streamed workload,
not sixteen simultaneous KV allocations. Keep policy and memory frozen through
all four complete replica manifests and their one official score each.

The first batch is the first four entries in the already frozen R01C order,
without a new draw or an outcome-based selection. The roster and label-free
runtime view are new files; the originals remain unchanged. This is a
construction step and an execution proof, not a four-row effectiveness screen.
Later construction batch size and all full-roster comparisons remain pending.

Use the existing shared controller, FlightRuntime, OpenJiuwen executor,
per-role completion caps and request decoding overrides. No new runner or
private agent script is needed. Four held experiment cells and a matching
two-slot baseline now compose correctly; the inherited four-slot override is
not carried into them.

## GPU and host envelope

Use the prospective decoder-only prepared-feature profile: two slots of
24576 tokens, total 49152; no mmproj, Q8_0 K/V, unchanged prefill geometry.
Relative to the old four-slot total of 98304, the GGUF-based analytical KV
payload decreases from 4896 to 2448 MiB. This is a 2448 MiB payload saving,
not a measured total-VRAM or stability guarantee.

The historical four-slot recovery recorded 22988 MiB GPU usage across 514
samples and at least 15.97 GiB available Windows memory. The final approximately
20 seconds before failure were unobserved. These data show limited VRAM
headroom; they do not establish that an OOM caused the CUDA illegal access
or Windows 0x116. A 32-input update batch also does not by itself prove an OOM.

The implemented independent resident-owner guard requires 32 GiB Windows
available before loading. Below 12 GiB Windows available or 2048 MiB GPU free
it latches new admissions closed; below 10 GiB or 1024 MiB it stops its owned
service. Missing or stale observation also refuses contact. See
[resource admission](2026-09-26-serving-resource-admission-v1.md) for exact
sampling and protection limits. Leave Windows at least 10 GiB actual available
RAM; a WSL maximum or an in-process estimate is not a substitute.

## Output and complete input accounting

The shared 24576-token slot rule retains 3072 operational reserve tokens and
two special-token reserve tokens. The prospective admission inequality is:

rendered input + speech packet tokens + output allowance + 3072 + 2 <= 24576.

| Stage | Output allowance | Maximum rendered input plus speech |
| --- | ---: | ---: |
| Actor conservative fit | 1024 | 20478 |
| One complete trajectory summary | 2048 | 19454 |
| Four-summary comparison for one input | 2048 | 19454 |
| One input's operation proposals plus frozen memory | 2048 | 19454 |
| Whole-batch synthesis plus entire frozen memory | 8192 | 13310 |

Actor roles retain 512 for Perception, Solver and Planner; Reviewer receives
1024 because one historical Reviewer response reached 512. The new matched
actor/control family must use this same allocation. Old 512-token results
remain historical comparisons, not a same-configuration control.
The shared conservative native fit uses the 1024 ceiling for every contact.

The semantic limits above are prospective configuration targets. They are not
claims of measured sufficiency or already bound semantic ExecutionPlans.
Every actual dependent-stage request must be prepared from its sealed
predecessor, rendered by the shared builder and measured with the authorized
resident tokenizer before generation. Record input/output/cache tokens,
context margin, VRAM and actual Windows availability by session/contact time.

A complete trajectory summary can exceed the window even when every actor
request fitted: it carries multiple role contexts, responses and tool records.
Smaller minibatches do not solve that per-trajectory issue. Comparison requests
contain four summaries regardless of update batch size. Batch synthesis grows
with both the number of inputs and the memory pool. Do not conflate these
three capacity problems.

The preliminary pool cap is eight records, with diagnosis <=256 characters,
guidance <=640 characters and up to two limitations of <=192 characters each.
The atomic synthesis may propose at most eight operations. These are explicit
prospective compact-memory constraints, not evidence that eight is optimal.
Keep all eligible group operations and all existing records in the request.
Character bounds are preparation guards, not token conversion formulas.

At the 2048-token group-output ceiling, four inputs represent up to 8192
source output tokens before re-rendering and memory overhead; eight represent
up to 16384, already above the batch-synthesis input allowance of 13310 before
that overhead. Tokenization is not additive across JSON serialization, so this
comparison motivates testing four first; it does not certify that four fits.

If exact fit fails, do not silently shorten outputs, discard trajectories,
prune memory, or increase context. Preserve the attempted stage and identify
the failing representation. Explicitly redesign that representation before
a separately registered continuation. Retain capped or malformed responses;
no automatic retries or manufactured updates.

## Prefix identity and sampling

Within a batch, preserve exact role instruction bytes, knowledge release and
selection ordering, tool schema order and the frozen memory version. Change
only registered request decoding seeds for the four replicas, never inserting
replica IDs or seeds into a shared prompt prefix. Preserve the existing speech
query prefix renderer rather than introducing another rendering path.

Prefix identity is conditional on the same input, role and policy version.
Different speech inputs, roles or actually observed histories are legitimately
different. Keep each trajectory's own responses, tool results and current
draft; do not force them to match for cache reuse or share mutable KV state.
Common static policy bytes precede changing history wherever the existing
renderer permits. Do not reorder an already registered comparison mid-flight.

An accepted memory update changes the next batch's common memory version for
all replicas together. It never mutates one active trajectory. The initial
batch is tool-free; source-attested Reviewer memory activation for batch two
requires an explicit common actor transition. It cannot borrow a future source.

Configuration/prompt equality is not proof of cached-token reuse. Verify the
actual rendered prefix and returned cache metadata during the registered
fit/proof; record lost reuse after a local tool yields a model slot. Stable
prefixes reduce repeated prefill work, but do not remove the preallocated KV
capacity or justify enlarging the batch.

## Work and launch boundary

The first batch has at most 176 actor generations (16 episodes x 11 contacts),
16 summaries, four comparisons, four group-operation requests and one batch
synthesis: 201 generation contacts at the structural ceiling, often fewer.
This excludes tokenizer/fit calls and is not a registered execution budget.
Each of the four complete actor manifests is scored once; semantic artifacts
are sealed without an official task score.

Read the [machine-readable sizing packet](../../configs/analysis/slurp-system-first-batch-sizing-v1.json)
for source hashes and exact caps. The four cells permit check only. Preparation
receipts, actual capacity, exposure/ExecutionPlans, dependent-stage bindings,
retained source and the independent Windows-owned WSL launch must be completed
before contact. No current GPU, tokenizer, encoder or scoring work was started.
The existing queue, STOP, failed attempts and retained workers are unchanged.
