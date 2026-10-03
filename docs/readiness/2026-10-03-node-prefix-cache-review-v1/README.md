# Node-specific prefix caching: source review

Recorded: 2026-10-03. Scope: source inspection and engineering design, with zero new inference, tokenizer or scorer contacts. No serving configuration, scheduling policy or frozen experiment was changed.

## Decision

Allow different nodes to have different stable instruction prefixes. Prefix equality across every role is not a correctness requirement of llama.cpp. Treat the current shared-prefix layout as one performance design, and evaluate role-specific cache affinity separately before relying on it.

Stable request content alone does not guarantee cache retention. A reusable prefix must match the cached token/media sequence on the selected slot, the slot must retain that sequence, and the full request plus output reserve must fit. Do not claim measured acceleration from this inspection.

The owner requested pausing the SLURP 30-minute background inspection until a later large-scale experiment. Automation `slurp` was updated to `PAUSED` and the app confirmed the state. This does not stop the independent Windows-owned serving, execution, official scoring or 10-second resource recorder. Root delegated next-stage GPU preparation to one explicitly requested sub-agent; no cache change is included in that already prepared round6 sequence.

## Verified deployed implementation

The live process resolved to `/home/chao/llama.cpp-featcache/build/bin/llama-server`. Its version reports `04ccc72a2`; the clean source checkout is commit `04ccc72a2207347ca76161b93fd9d846dd0a8675`.

Observed arguments include:
- `--no-mmproj -c 98304 -np 4`: four 24,576-token slots.
- `--cache-prompt`: same-slot common-prefix reuse enabled.
- `--cache-ram 0`: serialized host-memory prompt cache disabled.
- `--no-cache-idle-slots`: automatic idle-slot snapshot path disabled.
- `--slot-prompt-similarity 0`: similarity-based slot selection disabled.
- No `--cache-reuse` or `--kv-unified`; their inspected defaults are respectively zero and false.

Do not confuse the startup log's "prompt cache is disabled" (host-memory pool) with disabled same-slot KV prefix reuse.

## Request lifecycle and retention

Local source references, relative to the deployed llama.cpp checkout:
- `tools/server/server-context.cpp:1756`: explicit `id_slot` selects a slot; otherwise optional longest-common-prefix similarity and then idle-slot LRU choose one. A busy explicit slot defers its request at line2576. Explicit IDs wrap modulo slot count at line1731, so the client must validate real slot IDs and must not use hashing as a reservation mechanism.
- `tools/server/server-context.cpp:3334`: cache-enabled prompt preparation computes the common prefix with that selected slot. It retains that prefix, removes the divergent suffix and evaluates the new suffix (lines3532-3567). A completely matching request still evaluates at least one token for logits.
- `tools/server/server-common.cpp:480`: ordinary tokens match exactly; media chunks additionally match by identity and token count. Semantic similarity is not a cache match.
- `tools/server/server-task.cpp:1623`: the optional RAM pool stores serialized sequence states. It removes redundant entries, selects a better prefix under explicit retention/similarity criteria and discards oldest retained entries when size/token limits are exceeded (line1753). It is not currently enabled.
- `tools/server/server-context.cpp:1871`: unified-KV pressure can purge idle slots; this inspected path is inapplicable to the present non-unified configuration.
- `tools/server/server-context.cpp:3024`: reaching the context boundary may shift/discard context where supported. Capacity admission must preserve the complete output reserve rather than count on context shifting.
- `tools/server/server-context.cpp:3344`: optional chunk-shifting cache reuse is a separate feature, default-off and disallowed for requests carrying multimodal chunks. Do not treat it as arbitrary exact KV composition.

On one slot, requests `C + Solver + x`, `C + Reviewer + y`, then `C + Solver + z` retain at most the common part C across these switches. The first Solver branch is not simultaneously retained merely because the later Solver request is stable. This is suffix replacement, not necessarily RAM capacity eviction.

With separately reserved slots, Solver and Reviewer can each retain their own different prefix. A request must still provide its complete intended context; a saved cache is computation reuse, not hidden task memory.

## Current application behavior

`src/speech_aware_evidence_acquisition/reproduction/ojw/runner.py:424` and its `primary_slot/run_contact` implementation pin a trajectory from its first contact through completion. Different roles in that trajectory share the slot. The optional local-tool path can release and reacquire it; a future cache policy must account for that path.

`core/model/transport.py:216` and `speech-query-prefix-v2` place stable speech/knowledge content before mutable evidence and role/control history. Current role text can already differ in that suffix. `tool_schema_rendering=constant` avoids template-prefix changes when roles switch. These are efficiency choices for trajectory-owned slots, not a general rule that nodes must share their reasoning instructions.

The prepared speech-feature files cache a different stage from decoder KV. Keeping a speech packet on disk does not retain all attention states produced after a particular preceding text prefix.

## Candidate engineering designs

1. Preserve trajectory affinity and the shared speech/evidence prefix, while optimizing role-specific suffix text. This already supports different role policies with minimal scheduling change.
2. Add an opt-in node/prefix-family slot allocator. Pin each slot to a role-policy/template/tool-schema fingerprint; serialize requests per slot; track request dependencies, cancellation and release. Keep allocation metadata outside model text. Match the actual serialized prefix, not a node name alone.
3. If the active family working set exceeds available slots, explicitly choose recomputation or a bounded, verified save/restore tier. The existing file save/restore API is explicit I/O, not an automatic disk-backed prefix dictionary. Host RAM caching would be a separately measured serving change, not a free solution.

A four-slot role pool may preserve four static role prefixes, but cannot preserve every role-by-sample full history for multiple concurrent samples. For example, three roles across four live samples create up to twelve distinct full-context working states. A role pool preserves its static prefix while changing the sample-dependent suffix; it can lose useful cross-role reuse of the same speech/evidence and can create queue bottlenecks. Do not increase slots without rechecking per-slot context, KV memory and resource floors.

A prefix preceding the same speech packet changes the decoder state of the later packet when the prefix changes. Reuse of a later matching text/audio block under a different preceding prefix is not ordinary exact prefix reuse.

## Prospective verification

First inspect serialized request identities and test the allocator without model contacts. Then separately register a small structural/cache proof on the same allowed pool before any performance comparison:
- Distinct node A and B prefixes remain routed to their intended slots; returning to A retains the expected common prefix.
- Changing one prefix version recomputes from its first changed token; unchanged node caches remain independent.
- No two live requests own the same slot; queued/cancelled work cannot release an in-flight slot prematurely.
- Full legal context and output reserves fit; no hidden history or new runtime knowledge/gold is introduced.

Compare unchanged requests under current trajectory affinity and proposed node affinity before coupling the scheduling change to new text policies. Record cold/warm state, actual cached input tokens, processed prompt tokens, prefill time, first-token latency, queue delay, full-trajectory time, GPU/host memory and completion. Use `usage.prompt_tokens_details.cached_tokens` / prompt-cache timing counters for reused input; the legacy `tokens_cached` response field is the final slot token count in this build (`server-context.cpp:2326`) and must not be substituted for reuse.

Evaluate text changes as complete-system candidates with the registered A/A and quality/cost protocol. Cache and batch changes need not be bitwise neutral. No benefit, adoption or L-over-B learning claim follows from a better cache-hit rate. Owner227 authorizes bounded reviewed engineering; return to the human before8x400.

## Upstream references

- [Server API and cache arguments](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Host-memory prompt cache design](https://github.com/ggml-org/llama.cpp/pull/16391)

Upstream documents corroborate the broad model. The deployed fork and its exact code above govern this system; do not assume later upstream changes are already installed.
