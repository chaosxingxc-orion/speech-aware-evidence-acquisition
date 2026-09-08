# The §8 item 5 smoke of `SAEA-E21-FULL44-TAIL2S-V1` — one call, thirteen windows

Exposure row `SAEA-E21-FULL44-TAIL2S-SMOKE-V1`, registered and committed at study commit
`81f2b1e9` **before the first contact**. Attempt `attempt-20260907T230846Z-e2f699`, manifest
`COMPLETED`, `study_repo_dirt` empty.

**This receipt decides nothing and carries no metric.** A smoke roster's outputs are never
contrasted, reported or quoted, here or anywhere; the cell's numbers come from
`SAEA-E21-FULL44-TAIL2S-V1` alone. The attempt was finalized so its lifecycle closes rather than
sitting `OPENED` forever behind a `COMPLETED` manifest — the same shape the KC-E1 wire check's
smoke roster took — and finalize necessarily scores; **those scores are recorded and never read.**
No number appears in this receipt, and none may be derived from that run.

---

## What it had to prove, and what it did not

`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` §8.1 item 1 states the
job exactly: *"What the smoke still has to prove is the RUNTIME path -- that the emitted slice bytes
reach the server and that its four slice SHA-256s equal the committed `@ts2` entries for those
windows, checked before any score file is opened. What it no longer has to discover is whether the
knob produces the right bytes at all: that is already proved offline, with zero contacts, on all
1,593 windows."*

So this smoke is a **wire test of the delivered media**, not a measurement.

## Measured, not assumed: there is no four-window call

§7 priced this smoke at **4 windows / 8 contacts / 400 speech-audio seconds**. That figure assumed a
call short enough to yield four fixed 90-second windows, and **no call in the frozen 44 does**. The
window counts, computed from the committed `@ts2` supplement's own 1,593 ids, run from **13** to
**64**:

| shortest calls | windows | cut seconds |
|---|---:|---:|
| **4386541** | **13** | **1,097.100** |
| 4387332 | 15 | 1,310.160 |
| 4392809 | 16 | 1,438.008 |
| 4384683 | 17 | 1,476.744 |

The smoke therefore flew the single shortest call, `4386541`, at 13 windows and 1,123.100 delivered
seconds, under its own exposure row registering the **measured** ceilings (20 calls / 1,400
speech-audio seconds / 0.05 GPU hours) with the correction recorded in the row, in
`docs/receipts/probe-samples/e21-full44-tail2s-smoke-1-sample.json` and here. §7's GPU-hour ceiling
of 0.05 is unchanged and was not approached: the smoke realized **0.0080**.

The roster is frozen by the receipt above: the rule is *sort the 44 by window count ascending,
tie-broken by `sample_id`, take one* — deterministic, not a seeded draw. Call `4386541` is already
inside the sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` population and was named by the KC-E1 wire
check as one of its four shortest construction calls, so no new speech surface is opened.

## The media falsifier — 13 of 13

§4.4: *"each row's delivered audio seconds must equal its sealed row's plus exactly 2.0, and each
row's media SHA-256 must equal the committed D1 supplement's entry for that `@ts2` id. Zero
disagreeing rows, or the cell is void and no score is read."*

| check | result |
|---|---|
| windows checked | **13 of 13** |
| slice SHA-256 equal to the committed `@ts2` entry | **13 of 13** |
| delivered byte count equal to the committed entry | **13 of 13** |
| delivered seconds = cut seconds + exactly 2.0 | **13 of 13** |
| `preprocess` declares `tail-silence-2s` | **13 of 13** |
| `audio_seconds` still equals the CUT span (the tail moved no window) | **13 of 13** |
| `pre_sha256` equal to the SEALED comparator's own cut for that window | **13 of 13** |
| window spans equal to the sealed comparator's | **13 of 13** |
| disagreeing rows | **0** |

`falsifier.json` carries every row. The `pre_sha256` chain is the part that could not be checked
offline: it proves the bytes the flight actually sent are the sealed comparator's own 90-second cut
with 32,000 zero samples appended, and nothing else.

## Cost and serving

| | realized | ceiling |
|---|---:|---:|
| model calls | **13** | 20 |
| speech-audio seconds (metered cut span) | **1,097.100** | 1,400 |
| delivered speech-audio seconds | 1,123.100 | — |
| GPU hours | **0.0080** | 0.05 |
| paid API spend | 0 | 0 |

**Attached, never started, never stopped.** `saea-driver run --session-receipt` reached the
coordinator's resident session `e21-np6-c36864-20260907b` through `core.session.attach_session`;
geometry `-c 36864 -np 6`, 6 slots of 6,144 tokens, port 8080, fragment
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, bf16 mmproj resident, raw audio, no feature cache.
Temperature 0, seed 20260803, `max_tokens` 1024, `obs_batch_slices` 8. Run wall 68 s.
`saturated_slice_count` 0, `skipped_slice_count` 0.

Composed config hash `64e3df5175c9a5a8f48a39f23bcaa5b10e90422b46c431fc79588e37de73c437`, protocol
hash `6a57165d8a1c2114de7cf6337de6351cf1c41c4ca7518e4c5b9d3cb065aa25b8`, split identity
`ea8022dfcba86d57498b42630147b6b0f516e476f3a30428b5a62a6ad8bf8ecc`.

## Files

| file | what |
|---|---|
| `falsifier.json` | every one of the 13 windows: emitted SHA-256, byte count, delivered seconds, `pre_sha256` chain, span, saturation |
| `flight-receipt.json` | identity, plan, serving, cost, throughput, saturation and every artifact's SHA-256 |
