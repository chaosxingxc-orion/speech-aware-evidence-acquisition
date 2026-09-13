# Native answer-or-tool runtime wiring v1

This successor adds opt-in runtime custody for the registered `native-answer-or-tool-v1` phase program. The shared dispatcher remains the authority for parsing a model-selected native action. The runtime supplies dispatcher-owned internal tool schemas to `FrozenCoreClient`; it does not reuse Audio2Tool business schemas. Every accepted action is counted through `FrozenCoreClient.record_tool_call(count=1)`. A cold live ASR cache miss is separately debited, before source audio is opened or Whisper is loaded, against its own registered speech-tool `ExecutionPlan`. A warm cache hit retains the action count and adds no speech-tool contact.

The experiment config shape is:

```json
{
  "live_speech_observations": {
    "inventory": {"relpath": "<DATA-relative full runtime inventory>", "sha256": "<sha256>"},
    "protocol": {"relpath": "<DATA-relative decode protocol>", "sha256": "<sha256>"},
    "execution_plan": {"relpath": "<repository-relative registered plan>", "sha256": "<sha256>"},
    "output_relpath": "prepared/<tool-run-id>/<tool-attempt-id>/live"
  },
  "live_phase_fit_audio_seconds_cap": 6170
}
```

The runtime verifies the full inventory through the existing `verify_whisper_inventory` contract before serving: checkpoint size and SHA-256, every declared source and tokenizer asset, and the registered package versions. That verifier projects the compact backend inventory consumed by the lazy provider. The runtime also derives source bindings from the answering roster and validated packet promotion receipt and stores their aggregate hash in the live-tool receipt. The tool plan must match the main carrier, split role and split identity; its ledger row must remain unconsumed at preflight. The provider is constructed without opening audio, loading Whisper or creating a service. Its backend stays lazy until a selected cold action. Seal closes the provider and finalizes an opened speech-tool attempt with a create-only receipt. Abort closes it and preserves an aborted attempt with the main failure reason.

`live_phase_fit_audio_seconds_cap` is optional and leaves historical configurations unchanged. When present, it replaces the generation plan's speech-audio reservation only for the separate live request-fit plan. This prevents a fit registration from inheriting an unrelated generation audio cap.

The production environment is `/home/chao/.venvs/speechrl`; the separate `/home/chao/.venvs/saea-whisper-vad` environment is not used by this experiment. `core.speech_observation_backend._load_whisper_stack` prepends the backend inventory's pinned `whisper_source_path` before importing Whisper, so the production environment does not require an installed `openai-whisper` distribution. An import-only check on 2026-09-12 prepended `/home/chao/speech-tools/whisper-vad/sources/openai_whisper-20250625-saea-beam-batch-v1` and resolved `whisper`, `whisper.audio` and `whisper.tokenizer` from that exact source tree. The production environment carries Torch 2.9.1, torchaudio 2.9.1, SoundFile 0.14.0, tiktoken 0.13.0, numba 0.61.2, llvmlite 0.44.0, NumPy 2.2.6, more-itertools 11.1.0 and Triton 3.5.1. No checkpoint, audio or model was loaded for this check.
