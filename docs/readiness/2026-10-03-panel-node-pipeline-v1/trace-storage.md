# Pending trace storage and node-stage memory observations

Authority: the direct node-stage/cache clarification within owner227. Keep independent node contexts, all four active-node slots, fixed groups and the global model-stage barrier. Keep learning HELD and the slurp heartbeat PAUSED. The human boundary remains8x400.

## Actual retention and scope

The runtime already carries speech-feature packet descriptors and local file paths. It does not retain one feature-byte array per pending job. The real contact builds its request and the FrozenCoreClient consumes/removes its prepared request before dispatch. Actual-request FIT still runs at that contact. None of those operations is KV warmup.

Before this change, TraceBuffer deep-copied all trace payloads in memory until each owner's complete runtime window ended. A full node-stage panel keeps many workflows pending, making those duplicate request/response/history records a separate retention source. The opt-in store now writes these copies to local append-only intermediate files. Per-buffer indexes retain only offset, encoded length and SHA-256; merging buffers in deterministic sample/contact order moves references without reading or duplicating payloads. Final trace replay streams one record at a time through the original TraceSink. The store preserves canonical trace bytes, eager boundary validation and one-shot flush behavior. It does not become a runtime answer store, an optimizer input, a result manifest or a recovery mechanism.

Independent run identities get independent fresh spool files. Files and the writer-close receipt remain after success or failure. They live under the owned data root, outside the repository. A missing/changed record, disk write failure or registered storage bound stops execution; nothing silently regenerates or overwrites it. The writer stays open through the original final runtime-trace append and closes after all owner traces have flushed. Failure preservation also closes it after active execution settles.

The default configuration remains unchanged. A future node-pipeline registration may explicitly add:

```json
{
  "trace_spool": {
    "schema": "saea-native-trace-spool-v1",
    "max_record_bytes": 1048576,
    "max_total_bytes": 67108864
  }
}
```

These are synthetic-test example bounds, not admitted real-flight capacities. Register real bounds from maximum legal request/response evidence. Keep the complete outer native_node_pipeline declaration and original preparation identity rules. Do not alter prior frozen configurations or envelopes.

## Measurement and limits

Writer receipts report encoded bytes, record/read counts, largest written/read record and cumulative read/write wall time. Node preparation/contact timing events additionally carry current and peak Linux process RSS, process identity and observation time when disk storage is enabled. A process observation covers all owners in that process; it cannot be attributed to one sample or experiment. Missing observations are unknown, never zero. The ordinary Windows process supervisor and8GiB running/12.5GiB startup guards remain authoritative.

The stored trace payload copies retain zero payload bytes between operations, but indexes, live workflow histories, material objects, prepared strings, transient serialization/read buffers and other process objects still consume memory. The record/file bounds are not a total resident-memory cap. No workflow state is deleted, truncated or re-created to improve memory statistics. The public records inspection property can materialize all pending records; the runtime uses streaming iteration instead.

Spooling does not save or restore KV, prevent prefix mismatch, prove a cache hit, or make160 model contexts resident. Writes during execution lie on the original sample/panel path. Final canonical trace replay occurs after the runtime window; retain its read/write counters and generation-stage wall time separately rather than silently counting it as measured sample latency. Review both costs jointly with cache/recomputation and business quality. No speedup is inferred from synthetic execution. A larger stage can improve throughput while delaying early samples; preserve that distinction.

## Verification and next work

New unit checks exercise exact-byte trace replay, reference-only merges, mutation safety, independent owners, concurrent writes, streaming reads, size refusals, corruption/missing evidence, I/O failure and process-memory unavailable cases. Native integration checks compare unchanged requests/terminal answers through revision paths, preserve failure traces, and execute eight independent20-job runtime dispatches with separate clients/budgets/traces and160-request node stages. These use scripted model transports only.

After the final regression evidence is recorded, retain deterministic registered member order as the baseline within-node order. Declare any compatible-prefix grouping prospectively from actual request identity rather than node labels. Finish real maximum-request capacity and a separately registered integrated structural proof before a complete8x20 latency/quality panel. Preserve exact server-slot/token joins and first/later-group timing. Do not activate the learning search, cache save/restore or another carrier from this engineering change.

The [final source and evidence receipt](../../receipts/continuation/2026-10-03-node-panel-trace-storage-engineering.json) records574 passing selected tests,99.08% storage/98.40% shared-tracing statement coverage and passing lint/base/harness gates. The earlier lifecycle test failure was corrected before admission. An old timing-count assertion also failed identically on unchanged base; its corrected test explicitly preserves both existing timing records. No real model, tokenizer or scorer contacts occurred.
