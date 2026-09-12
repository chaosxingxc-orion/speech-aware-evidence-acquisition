# Local batched speech observation preparation

Status: shared producer implemented and tested; real dataset ASR is not yet registered or executed.

## Shared execution path

Use core.flight.cli prepare-speech-observation-sources to export the exact configured roster and source/feature packet bindings. The operation reads existing metadata and cached packet identities; it does not decode audio, tokenize requests, start a service or generate an answer.

Use core.speech_preparation_runtime for registered neural preparation. The speech-observation protocol resolves the verified local Whisper inventory, the pinned source inventory, an ExecutionPlan, a protocol hash and a preregistered exposure row. It shares custody, generation-lease ownership, attempt accounting, events and monitoring with the existing preparation runtime. No experiment-specific server or launcher is added.

Batch only missing unique artifacts. Lock paths in canonical order, validate warm identities, and write every cold start marker before invoking the producer. Record each source clip and its duration in the attempt before model load or forward. Native Whisper batches share one loaded model. Do not use concurrent decode calls against shared decoder hooks. Preserve successful artifacts, charged exposure and start markers after an interruption; do not silently replay.

Validate checkpoint bytes, official source/assets and exact package versions before loading the backend. Load the absolute local checkpoint path. Do not accept a runtime prompt, hotword list, reference transcript or alternative answer source. The current backend accepts complete English utterances up to 30 seconds. It pads waveform before mel extraction, uses bounded deterministic decoding, and preserves raw diagnostics. Empty, suppressed or saturated outputs become explicit non-answering fallbacks.

Seal a catalog with source/span/packet identities, decoding and checkpoint pins, producer execution-plan identity, persisted contact totals and a finalized attempt receipt. The already integrated speech-observation tool validates this catalog and supplies typed OBS evidence beside the original speech. The frozen Solver retains final answer authority. Valid warm reuse makes zero new neural contacts and retains the original producer cost.

## Verified preparation

The shared source exporter completed on the retained SLURP DEV1000 roster: 1,000 source bindings, 2,884.7936875 seconds in total, and a longest utterance of 12.032 seconds. All source durations fit the full-utterance backend limit. This is metadata preparation, not a claim that Whisper has transcribed the roster.

The artifact is DATA/prepared/SAEA-SLURP-SPEECH-OBSERVATION-SOURCES-V1/sources.json, SHA-256 435d64b9e4fd341d9db6f8e574d5eda08007f48c432dda55b09bc0b2ab318782. Reuse it through its binding rather than exporting a new roster.

Whisper large-v3 is stored locally, with an isolated GPU runtime and an official-source inventory. The shared entry point imports with CUDA hidden and offline environment flags. Full checkpoint content was verified during acquisition; the import receipt reuses that pin and explicitly does not claim a second hash. The runtime revalidates the full checkpoint before any future model load.

## Validation and limits

The WSL validation passed 402 tests: 391 shared regression and end-to-end fake-transport tests plus 11 text-preparation regression tests. Combined statement coverage of the four producer/preparation modules is 84 percent. Ruff, the engineering-base check and whitespace checks passed. Read the exact source hashes and log pins in 2026-09-12-speech-observation-producer-validation-v1.json.

Tests cover warm zero-contact reuse, batch deduplication, concurrency protection, debit-before-contact ordering, producer-to-consumer binding, failed or late finalization events, original exception preservation, source/plan/ledger mismatch, duration rounding, native mel padding and decoding saturation. No new dataset ASR forward or GPU tool model load occurred.

The active Audio2Tool source remains frozen at 22b56d706e2f5601dc79f58a8fad2bb6a9629f51. Finish its admitted comparison before the next neural tool experiment. A free generation lease does not itself establish that another resident has released GPU memory; root must explicitly manage the service boundary.

## Next scientific use

Preserve the retained SLURP compact-frame plan and solve stages and append the same bounded revision stage to both arms. Supply cached Whisper observations only to the treatment, between solve and revise. Keep original speech, legal answer space, knowledge content, selected IDs/order, model phases and output cap matched. Verify actual state propagation and full request capacity before registration; do not replace existing knowledge with the ASR tool merely to fit an old tool slot.

First establish whether the additional evidence helps the native task. Only then test a Reviewer problem-trigger policy against a matched random selection. This document grants no model contact or effectiveness conclusion.
