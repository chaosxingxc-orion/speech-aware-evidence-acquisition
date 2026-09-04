# A2T-CALIBRATION-400 flight roster (2026-09-04)

Receipt: `flight-roster-receipt.json`
(schema `saea-a2t-agentloop-flight-roster-receipt-v1`),
SHA-256 `6f352ea583d0bb91f77aad62e07bdad4d3210d066440fbfaee8e2af504853fe7`.

Built by `scripts/build_a2t_calibration_400_roster.py`. Zero model, network,
tokenizer, scorer and audio-decoding contact: the builder reads the parent
receipt's identifiers, the carrier's runtime media facts through
`data.audio2tool.load_audio2tool` (no gold, no expected calls, no task text)
and the WAV bytes for their SHA-256.

## Population

**Nothing was drawn.** This roster is the already-frozen Audio2Tool
discovery split, re-expressed in the flight-roster schema the September
Audio2Tool preprocessing launcher consumes:

| field | value |
|---|---|
| parent receipt | `docs/receipts/probe-samples/r1-audio2tool-sample.json` |
| parent receipt SHA-256 | `d99570a797744f7dc3db53bdb898611836ae2682a02e726b974d05734c6cbb2d` |
| parent seed | 20260807 |
| selection rule | the frozen 400 split, no draw |
| split name | `A2T-CALIBRATION-400` |
| split role | `discovery` (already exposed by A0, row `SAEA-BASE-a2t-a0-400`) |
| count | 400 (8 tiers x 50) |
| total audio | 2,159.688 s |

## Two identity hashes, deliberately both recorded

| field | value | convention |
|---|---|---|
| `split_identity_hash` | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` | SHA-256 over the LF-joined sorted parent `key` values (`audio2tool:<tier>:<id6>`) — the parent receipt's own convention, reproduced and asserted by the builder |
| `flight_split_identity_hash` | `11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b` | `data.splits.split_identity_hash(prefixed("audio2tool", sample_ids))` over `audio2tool/<tier>:<id6>` — the value `core.flight.FlightRuntime.preflight` computes at flight time |

Both hashes cover exactly the same 400 samples. They differ only in the
separator convention of the identifiers being hashed, so an exposure row
must carry whichever value the code path that builds its `ExecutionPlan`
will compute: the preprocessing launcher (which pins the receipt's own
`split_identity_hash`) uses `e1d751e6...`, and a `FlightRuntime` flight uses
`11091b38...`.

## Per-tier counts and audio

| tier | items | audio seconds | longest item (s) |
|---|---:|---:|---:|
| tier1_direct | 50 | 102.487 | 3.977 |
| tier2_parametric | 50 | 166.210 | 7.097 |
| tier3_multi_intent | 50 | 255.176 | 8.937 |
| tier4_implicit | 50 | 137.103 | 5.177 |
| tier5_needle | 50 | 546.210 | 14.697 |
| tier6_correction | 50 | 261.962 | 8.149 |
| tier7_multiturn | 50 | 358.371 | 35.714 |
| tier8_intent_blending | 50 | 332.169 | 15.417 |
| **total** | **400** | **2,159.688** | **35.714** |

Shortest item 0.617 s. The 35.714 s maximum is the speech-token sizing input
for every serving-geometry decision in this campaign
(35.714 s x 14.4 tokens/s = 514 speech tokens).

## No D1 media supplement, by design

`docs/receipts/artifacts/d1-a2t-calibration-400.json` was **not** created and
must not be. All 400 sample ids are already inside the parent D1 identity
closure (`docs/receipts/artifacts/d1-identity.json` carries exactly these 400
`audio2tool` media entries), and
`contracts.gate_media_identity` refuses any supplement that duplicates a base
D1 sample ("D1 media supplement duplicates base D1 sample"). The existing
builder `scripts/build_a2t_semantic_agentloop_d1_supplement.py` enforces the
same rule and refuses this roster for the same reason. Config fragments for
this campaign therefore declare no `d1_media_supplement` pair; media identity
is verified against the parent D1 manifest directly.

## Boundary

Gold, expected tool calls, task text, transcripts, annotations, model
outputs, scores, test data and future turns were never opened. This receipt
grants no contact authority.
