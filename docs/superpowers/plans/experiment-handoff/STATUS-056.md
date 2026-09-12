# STATUS-056: Local speech tools acquired and loaded

Snapshot UTC: 2026-09-12T07:03:55.972151+00:00.

## Active generation and immediate operational concern

DIRECT is FINALIZED with 4,000 charged generation contacts. STAGE-CONTROL is FINALIZED with 8,000. KNOWLEDGE is OPENED with 3,313 of 8,000 target contacts. These are accounting facts, not task-quality findings. Keep campaign session 71462, resident owner session 2098 and ten-second monitor session 88815. Active source remains frozen at cbc53ac0c36bed94fdb50c3b069a74569d935720. All three complete manifests must seal before semantic score or task-result reads.

Read-only hardware inspection found battery power, a 60 W enforced software power cap and 232 MHz SM clocks despite roughly 90 percent GPU utilization. At this snapshot the battery reported 21 percent remaining, PowerOnline=false and Discharging=true. Root asked the owner to connect external power. Recheck fresh power state promptly; do not interpret high utilization as unrestricted throughput. No hardware settings, service geometry or campaign parameters were changed. Preserve the hardware observation with cost interpretation.

## Completed local acquisition

The authoritative successor is docs/readiness/2026-09-12-local-speech-tool-readiness-complete-v1.json, SHA256 1a10bf17d648786d819ebdae335e80a532d741b387a60cce2ed501b8edaddead. The earlier partial readiness and acquisition records remain immutable.

Whisper large-v3 is fully local: 3,087,371,615 bytes, official SHA256 e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb. The downloader exited successfully; root independently verified the full file. The separately recorded single CPU model construction passed after host-free RAM recovered above 14 GiB. The model was released and the validation process exited; no audio or forward pass occurred.

Silero VAD ONNX and MMS_FA CPU construction checks passed. FFmpeg/ffprobe local launchers work. CMUdict pronunciation source is pinned. Existing Sortformer checkpoints and runtime are hash-verified; no new activation occurred. Optional WhisperX source is pinned, not installed. Optional pyannote Community-1 payload is still gated by official account access; its public source/card is available and the existing Sortformer path remains usable.

The isolated GPU-capable Whisper environment is /home/chao/.venvs/saea-whisper-gpu. It reuses pinned installed dependencies through read-only paths and imports official Whisper20250625 with torch2.9.1+cu128. Forty dependency distributions resolve with no missing/incompatible requirements. Import validation prohibited CUDA availability calls, weight loads and GPU allocations. This is package readiness, not GPU load or task-effectiveness validation.

## Shared implementation and analysis preparation

The shared core.preparation API now supports contact_class=speech-tool. Commit c6c8220245af0308582233a1cc295e6317d4f2cf preserves durable one-shot start markers, source/config binding, concurrent producer exclusion and warm reuse without producer calls. Historical encoder bytes remain unchanged. Agent verification passed 287 related tests and 88 percent module coverage; root independently passed 39 core tests. See docs/readiness/2026-09-12-speech-tool-preparation-validation.json. This storage capability does not authorize ASR inference or provide the pending OBS phase-tool action.

Outcome-free A2T metadata is complete under DATA/prepared/SAEA-A2T-NATIVE-SYSTEM-ANALYSIS-METADATA-V1/. Metadata SHA256 f4eeb0f5c548b15ab65e8137d134ee4b17bcebfa402eb71dcda6aa64198a5c70; receipt SHA256 48dfa94b3c0ba3c6d3e66fc9eafbe5645b2e475c4755533e58fe73c08e8e0367. Root independently checked 4,000 exact sample IDs, eight 500-row tiers, 2,792 smart_home / 857 wearables / 351 smart_car, and 2,097 query-index clusters. There are 677 cross-tier clusters. The metadata also retains legacy aliases but the frozen recipe uses query_idx, tier and domain directly.

## Next actions

1. Recheck external power and fresh attempt/monitor metadata. The current experiment remains active; no automatic restart or replay is allowed.
2. When all three complete manifests seal, preregister semantic result reading and instantiate the frozen analysis recipe from the first finalized score attachments. Use score_source=finalized-bundle; do not invoke the official scorer again. Analysis source remains /home/chao/saea-worktrees/a2t-native-analysis-v1 at 5f79d399.
3. Close the system-versus-direct and knowledge-versus-matched-stage-control decisions under the unchanged rule. Preserve exposed-roster and metric limitations.
4. Prepare the matched SLURP speech-evidence comparison through the shared OBS/controller path. Separate evidence availability, targeted selection and evidence-use benefit. Acquired tool assets alone do not establish any of these.
5. Keep the research goal active. E22 test remains closed. No new experiment GPU contact is admitted by this readiness update.

The completed implementation and documents are ready for a local fast-forward merge to master. No remote push is claimed.
