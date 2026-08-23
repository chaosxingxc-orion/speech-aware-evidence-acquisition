# E108 zero-copy prompt-fit audit (`speech-query-prefix-v2`)

## Decision

Every reachable K1/M11 prompt envelope of the information-complete E108 cell
fits one 4,096-token slot of the resident zero-copy service under the
`speech-query-prefix-v2` serving layout, with 1,623 tokens of margin left after
the 64-token completion reserve. The audit authorizes no model contact, no
semantic reading, and no larger run.

## Bound identities

- Resident session receipt SHA-256:
  `33639d3d4a74db48fead435cb7c7548beb58437a79cba64f5312b100b8fe9698`
  (`SAEA-SN-Q4KM-NP16-HOT-PREFIX-ZCOPY-20260823T111700Z`, PID 607,
  llama.cpp build b11-8e381e39c singleton-zero-copy)
- Decoder SHA-256:
  `0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d`
- Packet-promotion receipt SHA-256:
  `4aafd75ab86734159e39d8dedfc3ec12346d75d683119984c7b1aece761c1555`
- Knowledge binding SHA-256:
  `a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe`
- Decision-graph SHA-256 (`slurp-signature-complete-decision-graph-v5`):
  `58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc`
- Composed config hash:
  `48c5ccaea9dadbf4240239ac90283f0eb72758281c84b193f7fb457d943eafd4`
- Audit artifact SHA-256:
  `c2ee949a58c368dc3e3c4b3541f64ad845158771d90ca66327b955de30c46b4f`

## Method

Pre-registered as `SAEA-SN-MF-EVIDENCE-E108-ZCOPY-PROMPT-FIT` before it ran. The
existing `saea-driver speech-native-prompt-audit` entry point enumerated every
reachable canonical-order request through the production M11 constructor:

- one primary request;
- one complete-key retrieval request;
- 4,896 ranked top-three candidate-action permutations (`18P3`); and
- 220 directed, order-controlled boundary requests (`55 * 2 * 2`).

All 108 promoted speech packets were validated in parallel with 16 workers. The
audit attached read-only to the already-resident decoder-only service and used
only `/props`, `/apply-template`, and `/tokenize`. It mirrored the production
media-marker split, added the longest validated speech-feature sequence, and
reserved two possible special tokens. It never called a completion route,
evaluated the decoder, sampled a token, or read semantic output.

## Result

| Quantity | Value |
| --- | ---: |
| Prompt envelopes | 5,118 |
| Maximum text prompt | 2,290 tokens |
| Maximum speech feature | 117 tokens |
| Conservative prompt upper bound | 2,409 tokens |
| Completion reserve | 64 tokens |
| Context per slot | 4,096 tokens |
| Remaining margin | 1,623 tokens |

The worst envelope is `boundary:B001:K003:ba`. Tokenizer accounting is one
`GET /props`, 5,118 `POST /apply-template`, and 10,236 `POST /tokenize`
requests, with zero decoder evaluations and zero generated tokens. The server
remained mmproj-free and continuously resident; the session receipt hash was
identical before and after attachment.

## Difference from the 2026-08-22 canonical-order audit

Same graph, same binding, same packets, same envelope set. Only the transport
layout differs: `speech-query-prefix-v2` puts the speech query first and holds
mutable Agent state as an ordered suffix, which splits the text into more
tokenizer segments and costs 68 tokens at the worst envelope (2,341 -> 2,409).
The margin stays large, so the layout ruling of 2026-08-23 carries into the
E108 scientific cell without relaxing the slot geometry.

## Runtime rail

Formal M11 inference on this cell must present this exact receipt together with
the resident session receipt. The driver recomputes every reachable
prompt-envelope hash and fails before model contact if the graph, cards, prompt
construction, packet promotion, decoder, session, context geometry, completion
ceiling, or receipt bytes differ. A server restart requires a new
tokenizer-only audit.
