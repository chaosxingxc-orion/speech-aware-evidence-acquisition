# SLURP intent-boundary passage-key encoding draft

**Status: DRAFT / NOT GPU ADMITTED.** This document prepares a prospective
text-encoder tool plan. It does not authorize a model, processor, tokenizer,
GPU, speech, scoring, service, or network contact. It does not create an
exposure-ledger row, a root admission, or a task-quality conclusion.

## Purpose and bounded source

Encode exactly 60 released TRAIN-derived `intent-boundary` text facets from
the frozen SLURP semantic snapshot into the existing MF-7b
Omni-Embed-Nemotron space. The output is a passage-key index for the matching
model-free query-axis alias. It is not an answer source and never reads a DEV
target, reference transcript, score, or outcome.

The immutable source inventory is
`DATA/coordination/slurp-intent-boundary-key-source-inventory-v1.json`, SHA-256
`4d771352cc3c945ffdff343673ed89e37b629b6826fa73b3492db40cb889ff6d`.
It contains only the sorted facet IDs, character counts, and text hashes. It
pins the following source identities:

| Source | SHA-256 |
| --- | --- |
| Snapshot file `DATA/knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json` | `4579079c949e7da71125047c8d57027a55f0b90c3fc6db5704ba3c9322e6afd3` |
| Snapshot semantic content | `5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe` |
| TRAIN source split | `f76a7d00172a29452e791b0ec292c08492b9ae48e5eb28f72f58afd7f34cb1df` |
| Facet roster (`slurp/<facet-id>`, sorted) | `2baa0bf8615723e3b69a43ce7ade8333f71e8402a1e4db8e9da995b67774a80c` |
| Encoder inventory | `1548387ba91209921fd747e9eff981027be618c618b732efe20ca7d43680bb31` |
| Historical MF-7b Nemotron receipt | `b6ac1576936f8e2936354063e59c3bd3577592bee0fdef8020d227a06aab053d` |
| Intent-boundary query-axis alias | `6f391f883129f88fd7f843a76de95a805c39f165b2938a7ae9e3bb92d5860967` |
| Query-axis alias receipt | `f83b5b002d0823de40ac3f52f9a839f83daedf4ecdbbf0606b85f1fc07bd01a8` |

The source inventory records 5,010 total facet characters and a longest
representation of 140 characters. These are model-free inventory facts; they
do not replace the runtime's 8,192-token bound.

## Pinned protocol and geometry

The draft protocol is
`configs/preparation/slurp-intent-boundary-key-encoding-protocol-v1.json`,
SHA-256 `d327a7a04ae61be35bdb05b0dddcd5b170fcdd5c649983eaa99b5f03a242a36f`.
It uses the existing `saea-text-facet-encoding-protocol-v1` branch of
`core.speech_preparation_runtime` with `facet_dimension` set to
`intent-boundary`. The shared runtime selects only text facets in that
dimension, includes the dimension in the cache and index identity, emits the
same vector key, and seals the dimension in its source binding.

The frozen local retrieval tool is Omni-Embed-Nemotron-3B under the MF-7b
receipt geometry: the shipped sentence template, literal `passage: ` prefix,
batch size one, bf16 with SDPA, mean pooling over the attention mask including
the prompt, L2 normalization, 2,048 dimensions, and an 8,192-token bound.
The inventory pins the local model directory, processor/tokenizer files,
modeling file, two weight shards, and required package versions before load.

The query axis is already a model-free alias with the exact same ordered IDs
and floats as its `content` source, relabeled to `intent-boundary`. This draft
does not re-encode, normalize, or otherwise alter query vectors.

## Proposed tool plan

```json
{
  "schema": "saea-text-encoder-plan-v1",
  "study": "speech-aware-evidence-acquisition",
  "run_id": "SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1",
  "attempt_id": "encode-v1",
  "execution_profile": "bounded-discovery-probe",
  "carrier_lock_key": "slurp",
  "split_role": "discovery",
  "split_identity_hash": "2baa0bf8615723e3b69a43ce7ade8333f71e8402a1e4db8e9da995b67774a80c",
  "planned_model_calls": 60,
  "planned_gpu_hours": 0.5,
  "planned_speech_audio_seconds": 0,
  "protocol_hash": "d327a7a04ae61be35bdb05b0dddcd5b170fcdd5c649983eaa99b5f03a242a36f"
}
```

This is a prospective operational ceiling: 60 text-encoder contacts, zero
audio seconds, and 0.5 GPU hours. The shared `ExecutionPlan` requires the
text-encoder schema to state exactly zero audio seconds. One passage uses one
forward. Cache hits consume no new encoder contacts. There is no retry,
restart, jitter, batch widening, second encoder, Qwen contact, or score.

On a future separately admitted attempt, the shared lifecycle must write only
these new DATA paths:

- `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl`
- `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/index.json`
- `prepared/slurp-intent-boundary-text-facet-cache-v1/`

## Required root steps before any execution

1. Review and register the protocol hash and proposed plan in a new immutable
   DATA registration/configuration. Bind the exact clean runtime checkout and
   the `slurp` dataset-lock entry.
2. Add the pre-contact exposure-ledger row with the same run ID, attempt ID,
   roster hash, 60 tool contacts, zero audio seconds, and 0.5 GPU-hour ceiling.
3. Obtain the required root/owner admission, acquire the shared lease, and run
   only `speech_preparation_runtime` from the registered frozen checkout.
4. Seal the per-facet cache artifacts, facet JSONL, index, attempt receipt,
   lease release, and readback through the existing shared loader. Preserve an
   abort receipt and spent-contact trace if any failure occurs.
5. Register the sealed passage index with the existing model-free
   intent-boundary query alias. Do not alter the snapshot, query alias, or
   active native recovery service.

The draft changes no runtime code or launcher and has no effect on the active
terminal recovery. A failure would stop and preserve the attempt; any recovery
would require a separately registered named cause.

## Root successor

Root registration now resides in docs/readiness/2026-09-13-slurp-intent-boundary-key-encoding-v1. Its launch state is HELD. This draft records the earlier inventory and is not a dispatch receipt. The protocol contact-policy text is superseded by the registered protocol hash; content and geometry are unchanged. Owner authorization for progressive system capabilities is already present; no additional permission request is implied by this draft.
