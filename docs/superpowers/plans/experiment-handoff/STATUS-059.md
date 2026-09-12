# STATUS-059: Local speech evidence is integrated; recovery continues

Snapshot UTC: 2026-09-12T15:09:17.701995+00:00.

## Shared implementation completed

Root reviewed and committed the prepared speech observation integration at 99e3e5eb85e38e2debc328cfdc66fc6a32bfa0b4. The existing tool catalog, phase dispatcher, EvidenceAgentController, FlightRuntime, OpenJiuwen executor and request builder carry a source-bound finalized ASR observation beside the original speech. The transcript is supplied once; sealed tool state keeps a reference. The Solver retains answer authority. Cache consumption records OBS provenance and zero new neural contacts while retaining original producer exposure and cost.

The exact source/audio/packet/span, checkpoint, decoding configuration, producer ExecutionPlan, exposure row, attempt finalization and output hashes are validated before use. Empty, timeout and unsupported results produce explicit non-answering fallbacks. A configured action and catalog must appear together. Absent/null configuration preserves the historical request path.

The final WSL run passed 426 tests; the new modules have 84% statement coverage. Ruff, engineering-base, tool-catalog and diff checks passed. Actual fake-transport wire tests cover source-bound OBS, original speech retention, transcript deduplication, Solver authority, historical parity and transport tamper refusal. No new dataset ASR, GPU tool load, neural forward or paid API contact occurred. See docs/readiness/2026-09-12-prepared-speech-observation-validation-v1.json and docs/readiness/2026-09-12-prepared-speech-observation-integration-v1.md.

## Active GPU recovery

The active source remains clean at 22b56d706e2f5601dc79f58a8fad2bb6a9629f51. Preserve campaign PID 2179 / root exec 22617, resident PID 620 / root exec 51845, and monitor PID 678 / root exec 78284. Port 8090 remains decoder-only, no-mmproj, context 98304, three 32768-token slots.

DIRECT: FINALIZED, 4000 charged generation calls.
STAGE-CONTROL: OPENED, 2451 charged generation calls.
KNOWLEDGE: NOT_OPENED, 0 charged generation calls.

At 2026-09-12T15:09:16.232449+00:00, the monitor observed GPU utilization 89.0% and 3 of 3 busy slots. These are operational measurements, not task-quality results. DIRECT sealing and the successor fit included observed idle samples; preserve those intervals honestly rather than counting all resident time as useful generation.

The durable snapshot is DATA coordination/speech-observation-integration-and-recovery-status-v1.json, SHA-256 be2edebe827a192c6dde1e48e903ef8f6029c47c5358a3d8e0d54bc2079d8b9b. It supersedes STATUS-058 for execution status only. Do not rewrite the original interrupted attempts or the local acquisition receipts.

## Next action

Finish the three recovery arms and their once-only full scoring. Keep quality reads closed until all three manifests seal or root records a terminal hold. Then register and run the frozen saved-score analysis from /home/chao/saea-worktrees/a2t-native-analysis-v1 using finalized-bundle score sources and the sealed 4000-row metadata. Do not rescore or create a second recovery after another failure.

The speech cache consumer is complete. A real shared Whisper preparation producer, a registered dataset ASR contact and native task effectiveness evidence are still pending. Prepare the matched SLURP tool-evidence comparison under the recorded scientific dependency; do not confuse local loading or synthetic integration tests with task benefit. E22 test stays closed.

The research goal remains active.
