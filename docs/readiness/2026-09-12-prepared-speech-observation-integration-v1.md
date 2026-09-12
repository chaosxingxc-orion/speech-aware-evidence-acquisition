# Prepared speech observation integration v1

Status: shared source-bound cache consumption and model-free wire integration are implemented. No dataset ASR inference or task-quality evaluation is authorized or reported here.

## Runtime contract

The integration adds the configured system-invoked tool `saea-tool-prepared-speech-observation-v1` to the existing `rails.tools` catalog. Its manifest declares axis `OBS`, CPU consumption, and ledger row type `tool-contact`. CPU describes the cached read performed during the task trajectory. `tool-contact` preserves the exposure record of the earlier neural preparation; it does not claim that cache consumption makes another neural call.

`rails.speech_observation.load_speech_observation_catalog` loads one data-root-confined, hash-pinned catalog before flight execution. The loader accepts only canonical POSIX relative paths and an exact roster. Each observation is bound to:

- the use split, sample, cached speech-feature packet ID and packet SHA-256;
- the original audio relative path, SHA-256 and duration;
- `full-utterance`, starting at `0.0` and ending at that exact duration;
- a repository-pinned checkpoint receipt and decoding-configuration hash;
- the producer run, attempt, pinned `ExecutionPlan`, protocol and unique exposure-ledger row;
- the prepared artifact and output hashes; and
- one explicit status: `ok`, `empty`, `timeout` or `unsupported`.

The producer attempt must use the existing `saea-attempt-v1` state machine, be `FINALIZED`, and name the catalog itself in its `finalization` binding with kind `speech-observation-catalog`. Its actual calls and audio duration must equal the catalog accounting, remain within its reservation and execution plan, and cover every catalog row and every full utterance. The loader uses `core.preparation.load_artifact` and requires `contact_class: speech-tool`. It reads no audio and cannot invoke a decoder.

The following fragment illustrates the configuration. Values inside angle brackets are placeholders, and every path is relative to the root named in the placeholder.

```json
{
  "prepared_speech_observations": {
    "relpath": "<DATA_ROOT_RELATIVE_CATALOG_PATH>",
    "sha256": "<CATALOG_SHA256>"
  },
  "phase_tools": {
    "draft": {
      "mode": "fixed",
      "allowed_tools": ["saea-tool-prepared-speech-observation-v1"],
      "fixed_action": {
        "tool_id": "saea-tool-prepared-speech-observation-v1",
        "arguments": {
          "span": "full-utterance",
          "representation": "asr-transcript",
          "distinction": "Check the spoken number."
        }
      }
    }
  }
}
```

The catalog has this exact top-level shape. Repository-relative pins identify the checkpoint receipt, execution-plan envelope and exposure ledger. Observation artifact paths are data-root-relative.

```json
{
  "schema": "saea-prepared-speech-observation-catalog-v1",
  "catalog_id": "<CATALOG_ID>",
  "use_split_identity_hash": "<SPLIT_SHA256>",
  "checkpoint_receipt": {
    "relpath": "<REPOSITORY_RELATIVE_CHECKPOINT_RECEIPT>",
    "sha256": "<CHECKPOINT_RECEIPT_SHA256>"
  },
  "decoding_config_sha256": "<DECODING_CONFIG_SHA256>",
  "producer": {
    "run_id": "<PREPARATION_RUN_ID>",
    "attempt_id": "<PREPARATION_ATTEMPT_ID>",
    "execution_plan": {
      "relpath": "<REPOSITORY_RELATIVE_EXECUTION_PLAN>",
      "sha256": "<EXECUTION_PLAN_SHA256>"
    },
    "protocol_sha256": "<PROTOCOL_SHA256>",
    "ledger_row": {
      "relpath": "docs/exposure-ledger.md",
      "sha256": "<EXPOSURE_LEDGER_SHA256>",
      "row_id": "<PREPARATION_RUN_ID>"
    },
    "contacts": {"calls": 1, "audio_seconds": 2.5}
  },
  "observations": [
    {
      "sample_id": "example-sample",
      "speech_packet_id": "example-packet",
      "speech_packet_sha256": "<PACKET_SHA256>",
      "source_audio_relpath": "<SOURCE_AUDIO_RELPATH>",
      "source_audio_sha256": "<SOURCE_AUDIO_SHA256>",
      "source_audio_duration_seconds": 2.5,
      "span": {"kind": "full-utterance", "start_seconds": 0.0, "end_seconds": 2.5},
      "artifact_relpath": "<DATA_ROOT_RELATIVE_ARTIFACT_PATH>",
      "artifact_sha256": "<ARTIFACT_SHA256>",
      "output_sha256": "<OUTPUT_SHA256>"
    }
  ]
}
```

## Phase and wire behavior

The action accepts only `span: full-utterance`, `representation: asr-transcript`, and a non-empty `distinction` of at most 512 characters. Write the distinction in English. A catalog declaration and its phase action must appear together. Fixed selection is the first interpretable policy; the existing core-choice mode may select the same bounded action, but this integration does not claim that Reviewer confidence thresholds are calibrated or active.

`PhaseToolDispatcher` selects the observation against the current `QueryState`, records its lineage on the OBS trace, and seals a `tool-result` state without copying the transcript into that state. Its shared `render_values` path reselects the source-bound cache and emits the transcript once as a typed text block. The original `input_speech_features` query remains first in the request, so the next Solver receives the original speech and the independent observation together. Duplicate references to the same artifact SHA-256 do not duplicate its transcript. Empty, timeout and unsupported outcomes render an explicit non-answering status instead of fabricated transcription.

The normal `EvidenceAgentController`, `FlightRuntime`, OpenJiuwen executor and request builder remain the execution path. The wire check compares every `prepared-speech-observation://` block with the sample's finalized cached selection and reports observation-block counts separately from knowledge blocks. The final response still comes from the Solver contact; neither the cached transcript, the phase action nor its status has answering authority.

Omitting `prepared_speech_observations`, setting it to `null`, or setting it to `{}` returns no catalog. A phase action without a catalog and a catalog without its phase action both fail before contact. Configurations that declare neither retain the historical path and receipt behavior.

## Readiness boundary

Local speech-tool acquisition has separately pinned the relevant checkpoints and runtime sources. Whisper large-v3 CPU model construction has passed with zero forward calls, and CUDA-build dependencies and official source imports have been checked without a GPU model load or forward. Those acquisition and loading facts do not constitute this integration's evidence.

This integration has exercised only synthetic, model-free prepared artifacts and request wiring. A real Whisper producer, a registered dataset ASR preparation contact, its finalized catalog and any task-facing result remain pending. Version 1 covers cached feature-packet tasks with full short utterances. It does not admit arbitrary Earnings21 slices, targeted timestamps without validated alignment, diarization, or a live Whisper service.

## Root verification

The final WSL regression run passed 426 tests, including the existing FlightRuntime and shared phase/request suites. The new observation module and wrapper together have 84% statement coverage. The complete fake-transport OpenJiuwen test proves actual successor-request supply, original speech retention, transcript deduplication, final Solver authority, opt-out request parity and transport-side tamper rejection. No dataset, ASR, GPU or paid API contacts occurred in these checks. Validation details and source file hashes are recorded in 2026-09-12-prepared-speech-observation-validation-v1.json.
