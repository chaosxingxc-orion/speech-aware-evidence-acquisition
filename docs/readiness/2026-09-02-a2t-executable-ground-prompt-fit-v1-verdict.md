# A2T Executable Ground Prompt Fit V1 Verdict

## Decision

The tokenizer-only capacity gate passes. The complete executable handbook fits both the direct and
bounded one-state AgentLoop envelopes with a large positive margin. Permit only model-free freezing
of a fresh block-disjoint approximately-104 roster and separately preregistered packet preprocessing
and ground qualification. This result does not show that the frozen core understands the handbook
or reaches the 90% floor.

## Capacity result

The complete 54,881-byte handbook renders to 12,557 text tokens in the direct envelope. Adding the
455-token measured speech reserve and two special tokens produces a 13,014-token prompt; with the
1,024-token completion allowance it requires 14,038 tokens in one 32,768-token slot.

The AgentLoop envelope renders to 12,572 text tokens with the preregistered one-character Agent-state
wrapper. Adding 455 speech tokens, two special tokens, and the separate conservative 1,024-token
observation-body allowance produces a 14,053-token prompt. With the 1,024-token completion allowance,
the worst envelope requires 15,077 tokens and leaves **17,691 tokens of margin**. The runtime
observation contract remains at most 160 words and 1,024 printable ASCII characters, with no silent
truncation.

Result SHA-256:
`627e0efb01595eb45751a448fcc2b9029ce35f38f73810107506226f86a55c63`.

## Identity and contact audit

Before service startup, the runner re-hashed the pinned llama.cpp binary and 43 receipt-listed
runtime-library files, then re-hashed the 18,557,053,952-byte decoder GGUF to
`0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d`. The live service matched
llama.cpp commit `04ccc72a2207347ca76161b93fd9d846dd0a8675`, the frozen chat template, and 32,768 tokens per
slot.

The only request contacts were one local `/props`, two local `/apply-template`, and four local
`/tokenize` calls. There were zero completion-endpoint calls, prompt-bearing decoder evaluations,
generated tokens, audio decodes, retriever or embedding contacts, paid API calls, external-network
contacts, gold reads, and test reads. The server's standard startup log records one automatic empty
warm-up before it accepted requests; this carried no prompt, generated no token, and is not a task
model contact. The receipt-bound process was stopped after measurement, and port 8090 is closed.

External session / stop / server-log SHA-256 values are respectively
`f069feb9264155a2da7195ce8ddc1d38f6e9c9096cfb20c37358581547edcdcb`,
`8bc5035c0bb4c551ece33c006ca63d15fea5ca8361cd2a92ba03e54b73f85a52`, and
`1e0a0d9fcb3ef73ea930e1a1f655fe9a5d809ea043f97c741b121aa8972dd3bc`.

## Consequence

The next experiment must freeze an approximately-104 roster from the proposed block-disjoint
evaluation parent without reading utterance text, expected calls, gold, prior outputs, or scores.
Its promoted speech packets must independently measure at most 455 tokens; otherwise this receipt
cannot be inherited. Ground qualification must compare the same complete handbook in a direct
single-call path and a same-core OBS -> USE AgentLoop path, then apply the already-frozen exact
at least 0.90, tool at least 0.95, slot micro F1 at least 0.90, and parse at least 0.99 gates, with
exact 0.95 as the target.

Candidate pruning and training-free control remain suspended until that qualification passes. No
approximately-1,000 expansion, baseline change, test access, Stage-3 claim, or paper-scale work is
authorized.

## Engineering scope

Later scoring remains one unchanged official single-process operation per complete manifest, with
independent complete manifests eligible for outer parallel execution. Dataset sharding and
shard-score averaging remain forbidden. Network jitter, packet loss, latency injection, and retry
stress remain outside the engineering baseline.
