# A2T Executable Ground Prompt Fit V1 Preregistration

## Purpose

Prove, before any qualification model contact, that the complete executable handbook can be sent
to the frozen core with original speech and a bounded same-core English observation. This is a
tokenizer-only engineering gate. It measures capacity, not comprehension or task performance.

Experiment id: `SAEA-A2T-MF-EXECUTABLE-GROUND-PROMPT-FIT-V1`.

## Pinned inputs and service

The check reads the externally materialized handbook at
`knowledge/audio2tool/executable-ground-v1/handbook.txt` and refuses unless its SHA-256 is
`58ba08f3cebbe390156506653051d54aa37796822f49f5b851fd6eba4818fbc8`. Its in-repository build
receipt must hash to `505645b3cdef553ac847a5b248936182160d7b38aaaac84a076b9137c8e40e34`.

The serving fragment is
`configs/model/q4km-mmproj-free-speech-native-np2-a2t-max1024.json`, SHA-256
`82a23ed8bf71ff3cb290cea7d1f8e4cb35b281965a085bf8ab6d59406d650532`. It binds a 65,536-token
context split across two slots, a 1,024-token completion allowance, prompt order
`speech-query-prefix-v2`, and runtime receipt `docs/receipts/runtime-q4km-mmproj-free.json`,
SHA-256 `b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77`. The receipt pins
llama.cpp commit `04ccc72a2207347ca76161b93fd9d846dd0a8675` and decoder GGUF SHA-256
`0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d`.

The local service may already be resident on `127.0.0.1:8090`. If it is absent, a launcher may
start exactly the receipt-pinned service, verify all receipt-listed bytes before startup, make only
the contacts below, and stop only the process it started. Startup may load weights but may not run a
decoder evaluation. The live service must report 32,768 context tokens per slot and chat-template
SHA-256 `45777d2e798aae1d1ce6844e69edcb23fc0c710009554711c78efab9044da2c8`.

## Frozen envelopes

The handbook is the complete system message; it is not appended to the old registry contract and
may not be shortened, reordered, selected, or compressed after token counts are seen.

1. `ground-direct`: one query speech-feature marker and no Agent state.
2. `ground-agent-observed`: the same system message and query marker followed by exactly one
   `_speech_history_texts` `agent_state` wrapper. The measured wrapper carries the one-character
   placeholder `A`; the capacity calculation then adds a separate conservative allowance of 1,024
   tokens for the future observation body.

The later runtime parser is thereby frozen to accept only one-line printable ASCII English with at
most 160 whitespace-delimited words and at most 1,024 ASCII characters. The 1,024-token allowance
is conservative for a byte-level tokenizer because it is added on top of the already measured
one-character wrapper. Any observation outside either bound is unavailable and cannot be silently
truncated.

Both envelopes add the CPV2-measured worst speech-feature reserve of 455 tokens and two special
tokens. The future fresh roster must independently prove every promoted packet is at most 455
speech-feature tokens before inheriting this receipt. A larger packet stops qualification and
requires a separately preregistered prompt-fit successor with the newly measured maximum.

## Contacts and gates

Permitted local tokenizer contacts are exactly one `GET /props`, two `POST /apply-template`, and at
most four `POST /tokenize` requests. No completion endpoint may be called. Decoder evaluations,
generated tokens, speech decoding, audio seconds, paid API spend, retriever/embedding contact,
gold, reference transcript, score, test annotation, and network service contact are all zero.
Loopback socket calls are tokenizer contacts and are recorded as such; network-jitter testing is
out of scope.

The check passes only if:

- every pinned source and live tokenizer identity matches;
- the rendered prompt contains exactly one media marker;
- both text envelopes are measured through the live chat template;
- the worst envelope plus the 455 speech reserve, two special tokens, the 1,024 observation-token
  allowance where applicable, and the 1,024 completion allowance fits one 32,768-token slot with a
  strictly positive margin;
- the receipt records zero decoder evaluations and zero generated tokens.

Any failure closes V1 without modifying the handbook. Passing authorizes only model-free freezing
of a fresh block-disjoint approximately-104 roster and the separately preregistered preprocessing
and ground-qualification implementation. It does not authorize a model flight by itself, candidate
pruning, training-free policy fitting, approximately-1,000 scale, baseline change, test access,
Stage-3 work, or a superiority claim.

## Later scoring and engineering scope

The qualification experiment will keep the official scorer unchanged and single-process for each
complete manifest. Independent complete manifests may run concurrently through outer workers;
dataset sharding and shard-score averaging are forbidden. Network jitter, packet loss, latency
injection, and retry stress are not part of this engineering baseline.
