# Exact M11-v5 prompt-fit audit

## Decision

The complete v5 knowledge graph fits the resident 16-slot llama.cpp profile. The
audit does not authorize a model contact or waive the separately failed GPU P10
admission gate.

## Bound identities

- Resident session receipt SHA-256:
  `bfe06fa0df23f51094ce1ebfcec185523e406fee025a5203390b1e454e611da8`
- Decoder SHA-256:
  `0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d`
- Packet-promotion receipt SHA-256:
  `4aafd75ab86734159e39d8dedfc3ec12346d75d683119984c7b1aece761c1555`
- Knowledge binding SHA-256:
  `a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe`
- Decision-graph SHA-256:
  `58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc`
- Audit artifact SHA-256:
  `a5931ccd3c9e02150496d0475829e926becc02ed83322d45f4121dd00ee2a289`

## Method

The existing `saea-driver` contact-batched M11 constructor enumerated every
reachable canonical-order request before inference:

- one primary request;
- one complete-key retrieval request;
- 4,896 ranked top-three candidate-action permutations (`18P3`); and
- 220 directed, order-controlled boundary requests (`55 * 2 * 2`).

The audit validated all 108 promoted speech packets in parallel. It attached
read-only to the already-resident decoder-only service and used only `/props`,
`/apply-template`, and `/tokenize`. It mirrored the production media-marker
split, added the longest validated speech-feature sequence, and reserved two
possible special tokens. It did not call a completion route, evaluate the
decoder, sample a token, or read semantic output.

## Result

| Quantity | Value |
| --- | ---: |
| Prompt envelopes | 5,118 |
| Maximum text prompt | 2,222 tokens |
| Maximum speech feature | 117 tokens |
| Conservative prompt upper bound | 2,341 tokens |
| Completion reserve | 64 tokens |
| Context per slot | 4,096 tokens |
| Remaining margin | 1,691 tokens |

The worst envelope is `boundary:B001:K003:ba`. The tokenizer accounting is one
`GET /props`, 5,118 `POST /apply-template`, and 10,236 `POST /tokenize`
requests, with zero decoder evaluations and zero generated tokens. The server
remained mmproj-free and continuously resident.

## Runtime rail

Formal M11 inference must now present this exact receipt and the resident
session receipt. The driver recomputes every reachable prompt-envelope hash and
fails before model contact if the graph, cards, prompt construction, packet
promotion, decoder, session, context geometry, completion ceiling, or receipt
bytes differ. A server restart requires a new tokenizer-only audit.
