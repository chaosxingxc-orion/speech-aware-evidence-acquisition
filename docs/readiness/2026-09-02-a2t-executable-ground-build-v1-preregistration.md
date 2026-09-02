# A2T Executable Ground Build V1 Preregistration

## Purpose

Build one task-wide Audio2Tool handbook before any new model or tokenizer contact. This is the first
knowledge-expansion rung opened by the task-ground audit. It does not test performance and cannot
qualify the ground by itself.

## Frozen construction boundary

Use the already-landed `saea-a2t-block-partition-v1` proposal at seed `20260807`: 12,601
construction units are block-disjoint from the frozen exposed 400 and the proposed unexposed
400-item evaluation tier. The evaluation split identity remains
`4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90`.

Pinned inputs:

- partition proposal SHA-256
  `3bbf77a328c2983fb6299bcfe34a975624fee330a9325614dc1f84a7338678a1`;
- frozen registry SHA-256
  `7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4`.

The offline connection guard must be armed before either input is opened. The run may read the
governed construction manifests and registry locally. It may not contact a model, tokenizer,
embedding tool, retriever, network service, audio decoder, or GPU.

## Frozen rendering rule

The handbook is one query-independent object replacing the raw registry, not appended to it. It
contains:

1. global rules for tool selection, multi-call decomposition, corrections, implicit requests,
   needle content, exact JSON, and exact spelling;
2. a mandatory value-provenance rule: copy values only from speech or its same-core observation,
   never from the handbook and never from a default;
3. one contrast group for each registry `(domain, category)` with every sibling tool named;
4. exactly one entry per registry tool containing its description, signature, constraints, the
   intersection of required argument keys, the remaining optional keys, and every observed
   argument-key-set family for that tool.

It renders no construction utterance, sample identity, argument value, call exemplar, prior, or
registry default. The one registry-only tool remains present and follows its signature.

## Static gates

The build stops unless all conditions hold:

- registry tools = 152 and construction tools = 151;
- argument-pattern families = 354 and argument keys = 85;
- the handbook is ASCII English;
- no full non-empty registry default literal occurs in the handbook;
- rendered invocation texts = 0 and rendered argument values = 0;
- UTF-8 size is at most 65,536 bytes;
- construction samples intersect neither the exposed roster nor proposed evaluation roster;
- a second deterministic build is byte-identical.

The 65,536-byte cap is a build-size guard, not a tokenizer claim. A passing build opens only a
separately preregistered local-tokenizer prompt-fit check. No model contact or ground qualification
flight is authorized until prompt fit and the fresh approximately-104 roster are independently
frozen.

## Engineering scope

The later evaluation will retain complete-manifest outer parallel scoring around the unchanged
official single-process scorer. Network jitter, packet loss, latency injection, and retry stress
remain outside the engineering baseline.
