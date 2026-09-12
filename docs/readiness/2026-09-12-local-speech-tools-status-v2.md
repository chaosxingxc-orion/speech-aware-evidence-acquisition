# Local speech tool inventory and use order

Snapshot: 2026-09-12. Root rechecked the local WSL artifact inventory and acquisition receipts. Store tools under /home/chao/speech-tools and load their pinned local paths. Downloads and load checks are distinct from registered task inference.

| Tool | Local artifacts | Verified readiness | Remaining use requirement |
| --- | --- | --- | --- |
| Official Whisper large-v3 | Full checkpoint, official 20250625 source, isolated CPU and GPU environments | Checkpoint acquisition hash, dependency imports, CPU model construction and weight load; shared GPU entry-point import with CUDA hidden | Run registered batch ASR, then test native task quality through the shared evidence consumer |
| Silero VAD 6.2.1 | ONNX checkpoint, package and source | CPU ONNX session construction | Register input/forward and task-specific threshold use; preserve the original speech |
| MMS forced alignment | Existing 1.26 GB checkpoint reused through a local symlink | Dependency imports, CPU construction and checkpoint load | Register alignment against a legal hypothesis; alignment is not proof that a word was spoken |
| Sortformer v2 | NeMo and GGUF Q8_0 weights, pinned local runtime | File identity and availability | Model load and forward remain untested; activate only in its admitted service window |
| FFmpeg and ffprobe | User-local executables and dependency closure | Versions, dependency resolution, crop mapping and stream inspection | Reuse through the shared source/span and derivative recording interfaces |
| CMUdict | Pinned English pronunciation dictionary, 135,166 entries | Format and count validation | Register pronunciation lookup before runtime tool consumption |
| WhisperX | Pinned v3.8.6 source checkout | Source acquisition only | Use an isolated compatible environment if selected; do not treat the same Whisper weights as independent ASR evidence |
| pyannote community-1 | Public metadata and pyannote-audio source | Existing access returned HTTP 401 | Weight payload remains absent; owner account access is needed if this optional backend is selected |

No real dataset neural forward was performed by this acquisition or producer validation. Do not label download completion, CPU loading or synthetic integration tests as effectiveness evidence.

## Authoritative local receipts

- Whisper and Silero: /home/chao/speech-tools/whisper-vad/receipts/acquisition-complete-v1.json.
- Whisper CPU load: /home/chao/speech-tools/whisper-vad/receipts/whisper-cpu-load-v1.json.
- Whisper GPU environment: /home/chao/speech-tools/whisper-vad/receipts/gpu-runtime-dependencies-v1.json and gpu-runtime-import-v1.json.
- Alignment, diarization and optional backend gaps: /home/chao/speech-tools/alignment-diarization/receipts/acquisition-v1.json.
- pyannote remote metadata: /home/chao/speech-tools/alignment-diarization/receipts/pyannote-community-1-remote-metadata.json.
- Media tools: /home/chao/speech-tools/ffmpeg/receipt.json and package-inventory.json.
- Pronunciation dictionary: /home/chao/speech-tools/phonetic-lexicon/receipt.json.

The repository inventory and import bindings for the new Whisper producer are 2026-09-12-whisper-runtime-inventory-v1.json and 2026-09-12-whisper-runtime-import-readiness-v1.json. Read 2026-09-12-speech-observation-producer-v1.md for shared execution and validation.

## Use order

Finish the running Audio2Tool recovery and its frozen scientific analysis. Prepare the matched SLURP tool comparison in parallel. Then root assigns an exclusive GPU window to batch the complete bound short-utterance roster with one loaded Whisper instance. Cache the finalized outputs and return to the decoder-only Qwen service. Experimental arms consume the local cache; they do not start auxiliary servers independently.

Preserve the existing compact-frame plan and solve stages. Add the same bounded revision stage to both arms and give Whisper evidence only to the treatment. This tests additional evidence separately from the extra opportunity to revise. Keep the original audio and final Solver authority.

After closing this comparison, use VAD, alignment, conflict localization or speaker turns only to address a named failure component. Favor the already downloaded MMS and Sortformer capabilities before adding another runtime. Keep the optional pyannote access issue outside the critical path.

Training-free system optimization can later choose investigation, tool, span, evidence representation and continuation using native task reward. It requires useful actions and faithful evidence accounting first; tool acquisition alone does not establish an optimization result.
