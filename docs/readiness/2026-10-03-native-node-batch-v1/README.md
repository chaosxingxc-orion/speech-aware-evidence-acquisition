# Bounded native node batches on the shared executor

Status: implemented and verified offline; no GPU or exposure admission. Owner227 and the direct2026-10-03 node-batching instruction authorize this engineering work. Keep independent node instructions and per-sample source-bound intermediates. The same TaskAdapter, controller, FlightRuntime, native role graph and OpenJiuwen session own business execution.

## Execution contract

An explicit `native_node_batch` block contains schema `saea-native-node-batch-v1`, a complete unique `node_order` and positive integer `batch_size`. The batch fits the admitted workflow queue; the ordinary flight queue remains four workflows per model slot (16 here). Absence preserves the historical execution route. Permanent role slots and model context-cleaning calls outside this scheduler are refused.

For one cohort, suspend each native episode at its next contact boundary. Select the current node while it still has ready work, otherwise the first ready node in the declared order. Use all available slots for that node, then wait for each sample's own post-call, tool and state transition before the next scheduling decision. Preserve CPU intermediate state until every sample finishes. Admit the next cohort only after the current one settles. Conditional early completion, tool-loop continuation and Planner-to-Solver revision remain decisions of each original graph. Nodes never consume another sample's answer.

This provides bounded node batches within one flight. It does not yet interleave separate experimental attempts. Joint cross-attempt scheduling needs its own prospective accounting/read-family design; no answer sharing, skipped independent generations or cross-branch feedback is admitted by this implementation.

Any failure stops queued contacts and future cohorts. Active synchronous workers settle before their slots are released. Repeated cancellation is drained, not treated as worker termination. Per-sample context variables are captured at enqueue and carried into the worker. Existing per-contact FIT, tool authorization, output reserves, accounting and Omni final authority remain in the ordinary callbacks.

## Measurement

Each scheduled callback emits source-addressable node timing with cohort, node, wave, slot, queue/start/finish monotonic boundaries and success/failure. Model and tool callbacks carry distinct `contact_kind`; CPU-offloaded tools retain their existing tool receipts. These diagnostic records do not enter any model context.

Existing sample admission-to-terminal timing includes all node barriers and cleanup. Batch start and pre-admission waiting remain available, so cohort-release-to-terminal time cannot be hidden by admitting later. Report complete-family official quality/reliability, all-sample latency, first/later cohorts, node queue/prefill/decode/post-call time, and throughput separately. Node timing begins at shared callback scheduling, which includes actual-request FIT; original transport metrics still isolate server prefill/decode. A slot's active task is not a GPU-utilization measurement.

## Verification

The targeted suite passes237 tests. New scheduler module statement coverage is93%, shared OpenJiuwen runner97%, and scheduler/configuration module99% (rounded). Tests cover all slots serving the same node, independent sample handoff, bounded cohorts, conditional completion/revision, tool continuation, context variables, queued/repeated active cancellation, source/FIT order, timing failure, native runtime receipts, and disabled-mode request/canonical-output equivalence. No neural/tool-service/GPU/official scorer contact occurs; the tests use synthetic callbacks and the existing native harness.

One older trace-equivalence test already failed on the unchanged cf89ae2f4 base because it compared monotonic times between runs. The source-pinned baseline reproduction is retained. Its correction removes only the three measured timing boundaries, preserving sample identity, status, scope and all business records. Existing timing tests continue to validate those boundaries. The first coverage invocation found no pytest-cov plugin; it was replaced by the already installed coverage runner, with no environment installation. All intermediate logs are preserved under `coordination/node-batch-engineering-owner227-v1`.

## Prospective small comparison

First register two new node-batch configurations with unchanged before-speech node inputs, one cohort of4 and one of16, on the SAME existing fixed400 pool. Perform exact capacity and four-row structural proof through the standard background driver before runtime comparison. Keep the currently prepared tool-display/Reviewer-history factors HELD so scheduling can be diagnosed first.

The proposed next complete20-input family contains original-layout trajectory, before-speech trajectory, before-speech node-batch4 and before-speech node-batch16, each with its own A/A (8x20,160 trajectories). Exact policies, supply envelopes, FIT identities, source freeze, registration, scoring identities and whole-family READ remain prerequisites. Preserve the same prepared audio/packets/queries/votes/knowledge and existing20-input prefix; do not rebuild task data. This is a prospective design, not dispatch admission.

Count any explicit future prefix warmup separately, including its time and model contacts. Existing warm artifact/FIT verification is not KV prefill; inherited KV does not establish a controlled cold/warm contrast. First inspect actual node waves and unchanged request bytes, then evaluate sample latency and business quality. Fewer prefix switches are an opportunity, not a proven end-to-end win. Do not claim no-harm, stable benefit or learning from the small panel. Root alone; no subagents; learning HELD, heartbeat PAUSED,8/12.5GiB floors,human before8x400.
