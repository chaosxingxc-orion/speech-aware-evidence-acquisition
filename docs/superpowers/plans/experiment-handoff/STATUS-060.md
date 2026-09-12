# STATUS-060: Local speech producer committed and recovery continues

Snapshot UTC: 2026-09-12T15:55:08.968529+00:00.

## Local tools and shared producer

Root committed the shared local batched speech producer at 94537c0e0beb0653a1fc61b1b59910c99556f9f4. It uses the existing preparation runtime, execution plan, lease, accounting, event monitor, catalog consumer and FlightRuntime entry point. Warm validated catalogs cause zero new neural contacts; failed attempts preserve their original exposure and partial evidence. No new experiment-specific controller, launcher or service was introduced.

The WSL validation passed 402 tests with 84 percent combined statement coverage across the four preparation/producer modules. Ruff, engineering-base and whitespace checks passed. Exact code and log pins are in docs/readiness/2026-09-12-speech-observation-producer-validation-v1.json.

The shared model-free SLURP source exporter completed: 1,000 bindings, 2,884.7936875 speech seconds, longest source 12.032 seconds. Its DATA artifact is prepared/SAEA-SLURP-SPEECH-OBSERVATION-SOURCES-V1/sources.json, SHA-256 435d64b9e4fd341d9db6f8e574d5eda08007f48c432dda55b09bc0b2ab318782. No source audio decode, real ASR forward, GPU tool load or new Qwen experiment generation occurred during this work.

Whisper, Silero and MMS weights are local and CPU loading was verified during acquisition. Sortformer weights are local but model loading remains untested. FFmpeg and CMUdict are available. WhisperX is source-only; pyannote community-1 payload remains unavailable under current access. Read docs/readiness/2026-09-12-local-speech-tools-status-v2.md for exact levels and local receipt paths. Do not equate local loading with native task benefit.

## Active GPU experiment

Keep the recovery source frozen at 22b56d706e2f5601dc79f58a8fad2bb6a9629f51. Root revalidated campaign PID 2179 / exec 22617, resident PID 620 / exec 51845, and monitor PID 678 / exec 78284. The resident is decoder-only, no-mmproj, total context 98304, three 32768-token slots on port 8090.

- DIRECT: FINALIZED, 4000 charged generation calls.
- STAGE-CONTROL: FINALIZED, 8000 charged generation calls.
- KNOWLEDGE: OPENED, 1142 charged generation calls.

At 2026-09-12T15:55:06.550917+00:00, the existing monitor reported utilization 81.0 percent, 2 of 3 slots busy, and 88.36 watts. Preserve measured load/fit/sealing gaps and reported clock values; utilization alone does not establish unconstrained hardware throughput.

The operational snapshot is DATA coordination/speech-observation-producer-and-recovery-status-v1.json, SHA-256 13a38a8bc9d95ebf724a6db228fc689a0ffe7596a862a1ffc4122cb17a57a24f. It supersedes STATUS-059 for execution status only. No task-quality results were opened.

## Next work

Finish the three admitted recovery arms and once-only full scoring. Keep quality reads closed until all recovery manifests seal or root records a terminal hold. Then preregister and run the frozen finalized-bundle saved-score analysis from the existing analysis worktree. Do not rescore or authorize a second recovery.

Prepare a matched SLURP comparison that preserves compact-frame plan and solve behavior and adds the same bounded revision stage to both arms. Supply finalized Whisper OBS only to the treatment between solve and revise. Verify state propagation, knowledge IDs/order, source retention and actual request capacity. Register finite real preparation and generation budgets before contact.

Root assigns an exclusive Whisper GPU preparation window after scientific admission, then returns to the decoder-only core service for the matched arms. The first registered batch measures throughput without extra trial contacts. The research goal remains active; no tool effectiveness or training-free optimization result is claimed.
