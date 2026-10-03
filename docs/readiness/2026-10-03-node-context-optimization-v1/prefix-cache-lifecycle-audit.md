# Prefix-cache lifecycle audit of the deployed speech server

## Scope and observed identity

Inspect the running server and its pinned local source at llama.cpp commit `04ccc72a2207347ca76161b93fd9d846dd0a8675`. The executable reports that build; the live /proc/942/exe SHA-256 is `d0b42ace8d8e02dc772a0e4a1e1667068b3ad799b1ca4c98c741cf89d58404f2`, matching the registered serving identity. The server has four 24576-token slots and uses decoder-only prepared speech features.

Actual arguments enable `--cache-prompt`, disable RAM backup with `--cache-ram 0`, disable idle-slot backup with `--no-cache-idle-slots`, and disable automatic similarity selection with `--slot-prompt-similarity 0`. There is no `--slot-save-path`. These settings were observed, not changed. Keep the current frozen engineering and learning jobs unchanged and the SLURP heartbeat paused.

## What is recomputed

The live-slot path computes the longest common prefix between the selected slot's old token/media sequence and the new request. It keeps that prefix, removes the divergent suffix, and evaluates the remaining input. Multimodal comparisons include media chunk identity and length; equal placeholder token values alone do not establish reuse. A complete token match can still require evaluating one final token for logits. SWA/hybrid checkpoint gaps can force more recomputation, but that is a separate mechanism.

A completed request normally releases the slot for scheduling without clearing its cached prompt. Stable role names or call order alone do not guarantee reuse: the exact rendered prefix must match, that slot must still hold it, and any earlier speech/evidence change makes the subsequent identical role instruction a different causal context. This is why placing independent stable role instructions before variable sample content is a prospective optimization factor, not a requirement that every role share one instruction.

The already qualified four-member scheduling panel measured 203944/204554 evaluated input tokens for its two trajectory repeats and 949857/920950 for role-affinity repeats. The latter sum is about4.58 times the former. These counters measure evaluated input, which includes necessary new input as well as recomputation; they do not label every token as avoidably recomputed. Reuse was about83% versus26%. No additional task quality or optimizer export is made by this audit. See the [qualified descriptive node measurements](../../results/2026-10-03-prefix-node-timing-descriptive-read.md).

Read `usage.prompt_tokens_details.cached_tokens` or `timings.cache_n` for reused input, and `timings.prompt_n` for actually evaluated input. In this pinned source, top-level `tokens_cached` is final slot residency, not reused-input count, despite the less precise README description. Keep the existing reader's distinction.

## Three distinct storage mechanisms

| Layer | Save/replacement behavior | Load behavior | Current state |
| --- | --- | --- | --- |
| Live slot KV | Keep matched prefix; discard divergent suffix. Unified-KV allocation pressure may purge an idle slot. | Reuse the selected slot's longest common prefix during ordinary completion. | Enabled |
| RAM prompt-state backup | Clone token/media metadata and serialize model sequence state. Suppress contained duplicates; remove superseded shorter entries. Enforce size/token bounds by removing oldest stored entries, retaining at least one. | Search for a better cached state, restore it into the selected slot, then remove that RAM entry. | Disabled |
| Disk slot snapshot | Explicit save endpoint serializes a slot state to a configured directory. The driver would manage filenames and retention. | Explicit restore endpoint loads into an idle slot; requests arriving while busy are deferred. | Not enabled; speech compatibility defect identified below |

RAM loading is not a general best-LCP trie. The current implementation rejects entries preserving less than25% of their saved prompt and requires strictly better preservation fraction and request similarity than the slot's resident state. Its capacity removal is oldest-entry order, not the live-slot LRU selection rule. Its configured RAM size is not a strict process-memory cap: allocation occurs before trimming and at least one entry is retained. Enforce the independent Windows resource floor as well.

For task slot selection, an explicit `id_slot` wins. Without one, similarity selection can choose an idle matching slot; otherwise the server chooses an idle least-recently-used slot. Automatic RAM save/load is conditional on that selection path. With the present explicit slot requests and similarity=0, `update_cache` stays false. Merely setting a positive RAM size would therefore not make the current requests perform save/load. Idle-slot backup is another trigger; it must not be enabled blindly because it can clear idle GPU slots when unified KV is used.

## Operational evidence and limits

A read-only string-count scan covered the current session log's first45804212 bytes, SHA-256 `53619705e4c924f76b08af464c5c68aa4f616194cf3e26a05f43c9e994a969b8`,434673 lines, at2026-10-03T12:17:11.967255Z. It observed47543 explicit-slot selections and zero logged RAM saves, loads, evictions or idle saves; zero KV allocation-failure/purge, context-shift, forced-full-reprocess or checkpoint-restore events. Only operational counts were exposed. The log covers the whole session, not one exact experiment. Absence of these events does not prove the cause of every cache miss; ordinary LCP truncation is not fully observable at the current log level. Existing sealed response counters remain the per-request evidence.

## Do not call disk save on current speech slots

The custom `process_speech_feature_prompt` constructs `server_tokens(..., true)` and media placeholders even on a decoder-only server. The disk action guard checks only whether the mmproj context exists; this server has no mmproj context. The save handler subsequently calls `server_tokens::get_tokens()`, which asserts `!has_mtmd`. Thus enabling the route and saving a populated speech-feature slot can reach an assertion. This is a static source finding, not an observed live crash, and no action endpoint was called.

Disk restore also reconstructs a flat token vector rather than the media-position map. A complete speech-slot snapshot needs explicit media metadata serialization/validation and a matching restore path. RAM `server_tokens::clone` already preserves that metadata, so its representation is a more promising candidate for a bounded proof; successful end-to-end restoration is not yet demonstrated.

## Prospective driver policy

1. Keep normal live-slot reuse as the first choice. Track exact prefix identity, requested/served slot where observable, cached/evaluated tokens, prefill/decode/client times and episode wall time. Do not treat role ID as cache identity or force one physical slot per role.
2. At the next independent serving boundary, evaluate bounded RAM backup only after proving the trigger path with explicit-slot routing. Preserve the current four-slot geometry and full output reserve, measure save/load time and bytes, and retain8GiB running/12.5GiB startup protection. Do not enable unbounded RAM or idle-slot clearing by default.
3. Consider disk storage as a cold tier. First prove pure-text invariant-prefix snapshots or implement media-aware serialization in an isolated source version. Never save a populated speech slot through the incompatible current endpoint. A stable text prefix may be restored into a selected idle slot before appending sample speech; validate the exact rendered token boundary.
4. Key entries by pinned model/build/KV configuration, template and complete prefix identity, policy version, and media identities/positions when present. Preserve raw responses and answer custody. Do not transplant a suffix KV state behind a different causal prefix.
5. Before changing a slot, hold scheduler ownership across the save/restore-and-next-request transaction. A GET-idle check alone races with concurrent work. Restore only when measured avoided prefill exceeds amortized save, lookup, load/transfer and scheduling delay; otherwise use ordinary recomputation.
6. Run a separately registered structural cache proof for exact repeat, shared-prefix/different-suffix, switch-away-and-return, and supported snapshot restoration. Then compare the same complete requests and roster with cache policy as the sole changed factor. Test context-layout changes as a declared policy factor, and do not ascribe their quality effects to cache alone. Count warmup/tokenizer/model contacts and all storage/transfer costs.
7. Preserve L/B isolation, spent proposal allocations, whole-family reading and owner227's human boundary before8x400. This audit does not modify queues, service options, frozen sources or experiment permissions.

## Source map

Pinned local source under `/home/chao/llama.cpp-featcache`:

- `tools/server/server-context.cpp:1756`: selection and automatic RAM update.
- `tools/server/server-context.cpp:1871`: idle-slot KV-pressure purge.
- `tools/server/server-context.cpp:2601`: idle-slot backup.
- `tools/server/server-context.cpp:2712`: disk save/restore task handlers.
- `tools/server/server-context.cpp:3334`: LCP, optional chunk reuse, checkpoint fallback and suffix truncation.
- `tools/server/server-context.cpp:4685`: slot-save-path action gate.
- `tools/server/server-task.cpp:1623`: RAM allocation, matching, loading and oldest-entry removal.
- `tools/server/server-common.cpp:415`: text-only token accessor assertion.
- `tools/server/server-common.cpp:480`: token/media LCP.
- `tools/server/server-common.cpp:560`: media-preserving RAM clone.
- `tools/server/server-common.cpp:996`: supplied speech-feature construction.

The [official server API documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) documents cache options and slot save/restore/erase endpoints. Resolve deployed behavior against the pinned local implementation, especially the custom speech-feature path and counter semantics.
