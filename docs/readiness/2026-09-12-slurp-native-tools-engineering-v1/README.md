# Native speech tool engineering proof

Run one four-row TRAIN construction proof through the shared FlightRuntime, EvidenceAgentController and OpenJiuwen executor. Reuse the root-owned decoder-only np4 resident service and prepared Qwen speech packets. The main model emits a native tool call; a selected live speech tool loads the pinned CPU Whisper backend only after custody and source verification; the actual transcript returns as typed observation evidence for the main model to use in its final task answer.

The phase program allows up to two selected actions followed by a final answer, and permits earlier plain answers. The engineering prompt explicitly requests one corroborating transcript to exercise the call branch. This verifies interactive execution only; it does not demonstrate a useful autonomous trigger, an optimized policy, or task improvement. A model that never calls ASR leaves live-call proof unestablished; do not silently execute ASR or rerun the flight to obtain a preferred trace.

The fixed TRAIN-A reward-source attempt remains separately held and ABORTED with zero contacts. This proof has a distinct preregistration and does not recover that attempt.

## Bounds and preparation

Use four ordered source rows, 10.5955625 seconds in total, from the existing TRAIN-A construction roster. The source remains historically exposed. Bind full local Whisper runtime inventory through the shared verifier: checkpoint bytes and hash, source and tokenizer asset hashes, and dependency versions. The compact projection is an implementation input, not a substitute for full inventory verification.

Maximum Qwen generation is 12 contacts and 32 speech seconds. Maximum actual phase-fit contacts is 39, with 32 speech seconds. These Qwen GPU and audio ceilings cover the same fit-inclusive flight and must not be added as physical usage. Maximum selected internal invocations is eight; maximum cold CPU ASR is four sources and 11 speech seconds. Warm selected ASR reuse is an internal invocation with zero extra ASR forward. The historical ExecutionPlan schema requires a positive GPU ceiling for CPU tool plans; record actual ASR GPU usage as zero and do not infer GPU ASR authority.

## Validation and reading

The merged integration tests use the real client, adapter, dispatcher, live provider and OpenJiuwen with fake model/ASR transports. They verify direct stopping with zero tool work, actual result supply into successor requests, multiple selected evidence types, warm-cache accounting, duplicate-evidence handling and malformed-call recovery. A wire check uses the real four-row configuration but refuses any native tool execution. Neither is a live quality result.

Before live contact, bind the clean source commit and exact resident identity in a separate root launch receipt. Run actual capacity checks on every active wave's prepared request bytes. Seal the complete final manifest before reading semantic outputs. Run the complete native TRAIN scorer once; retain per-sample counts and engineering-only interpretation. Record actual tool/answer/fit counts and a source-bound observation-to-successor-request check. Preserve failure evidence and do not automatically restart a service or replay a selected tool.
