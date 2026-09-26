# Single-slot profile for whole-system semantic stages

Status: HELD. No service switch or generation is authorized by this document
alone. This follows the compact-view capacity verdict: all16 requests physically
fit a24576-token slot, but one needs21528 input tokens and leaves only998 after
its full2048 output allowance. Retain the registered3072-token reserve.

Use q4km-mmproj-free-system-np1-ctx48k-resource-guard-v1: one49152-token slot,
total49152 context. The actor profile remains two24576-token slots. The model,
decoder-only runtime, weights, feature root, Q8_0 K/V and prefill batch2048 /
microbatch512 stay as in the observed actor configuration. Slot count changes
from2 to1. Total analytical KV payload remains2448 MiB; total GPU peak also
depends on compute workspace, graphs and request length and must be observed.
Do not infer stability solely from unchanged KV capacity.

For semantic stages, input + full output allowance +2 special tokens +3072
reserve must fit49152. Summary/comparison/group-operation output2048 leaves
44030 input tokens. A prospective8192-token batch-synthesis output leaves37886
input tokens. Only real predecessor artifacts and resident-tokenizer receipts
admit these stages. The current longest summary would leave25574 margin after
its output and special tokens if tokenization is unchanged; that arithmetic
does not replace a new-service fit receipt.

Run one semantic request at a time. Keep the actual same role prompt/prefix
and source content for the entire registered set. Never change the policy
mid-batch. Sequential summary requests can reuse the shared fixed prefix, but
record returned cache statistics rather than promising a measured speedup.

The root must register the new service identity and cells, complete a planned
owned-service handoff, rebind independent Windows serving/monitor tasks, and
fit all16 exact requests before summary generation. Retain startup32 GiB,
admission12 GiB and stop10 GiB Windows availability; GPU admission2048 MiB
and stop1024 MiB free. Missing/stale observation refuses contact. Generation
must run independently in WSL, with no automatic restart or retry.

Restore the actor's independently validated two-slot geometry at its next
registered boundary. One learning batch still contains four inputs and four
complete trajectories per input, with a frozen policy until the actual
summary/comparison/update artifacts seal. This schedule is a first update-cycle
proof, not an effectiveness claim or a final32-input baseline.
