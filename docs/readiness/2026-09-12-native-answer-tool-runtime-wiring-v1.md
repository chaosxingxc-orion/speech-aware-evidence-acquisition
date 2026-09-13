# Native answer-or-tool runtime wiring v1

This successor adds opt-in runtime custody for the registered `native-answer-or-tool-v1` phase program. The shared dispatcher remains the authority for parsing a model-selected native action. The runtime supplies dispatcher-owned internal tool schemas to `FrozenCoreClient`; it does not reuse Audio2Tool business schemas. Every accepted action is counted through `FrozenCoreClient.record_tool_call(count=1)`. A cold live ASR cache miss is separately debited, before source audio is opened or Whisper is loaded, against its own registered speech-tool `ExecutionPlan`. A warm cache hit retains the action count and adds no speech-tool contact.

The experiment config shape is:

```json
{
  "live_speech_observations": {
    "inventory": {"relpath": "<DATA-relative backend inventory>", "sha256": "<sha256>"},
    "protocol": {"relpath": "<DATA-relative decode protocol>", "sha256": "<sha256>"},
    "execution_plan": {"relpath": "<repository-relative registered plan>", "sha256": "<sha256>"},
    "output_relpath": "prepared/<tool-run-id>/<tool-attempt-id>/live"
  },
  "live_phase_fit_audio_seconds_cap": 6170
}
```

The runtime derives source bindings from the answering roster and validated packet promotion receipt. It stores their aggregate hash in the live-tool receipt. The tool plan must match the main carrier, split role and split identity; its ledger row must remain unconsumed at preflight. The provider is constructed without opening audio, loading Whisper or creating a service. Its backend stays lazy until a selected cold action. Seal closes the provider and finalizes an opened speech-tool attempt with a create-only receipt. Abort closes it and preserves an aborted attempt with the main failure reason.

`live_phase_fit_audio_seconds_cap` is optional and leaves historical configurations unchanged. When present, it replaces the generation plan's speech-audio reservation only for the separate live request-fit plan. This prevents a fit registration from inheriting an unrelated generation audio cap.

The dependency environments are not interchangeable. Package metadata on 2026-09-12 shows `/home/chao/.venvs/speechrl` has Torch 2.9.1 and SoundFile 0.14.0 but no `openai-whisper`; `/home/chao/.venvs/saea-whisper-vad` has `openai-whisper` 20250625 and Torch 2.8.0 but no SoundFile distribution. A real flight must use a registered environment that contains both the live provider's source reader and the pinned Whisper package. No package was installed and no module, checkpoint, audio or model was loaded for this check.
