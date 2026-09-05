# Audio2Tool Q8_0 quantization probe, v1 — verdict

Run `SAEA-A2T-Q8-QUANTIZATION-PROBE-V1`, flown 2026-09-05 on the frozen 400-item Audio2Tool
discovery split (`A2T-CALIBRATION-400`, flight split identity hash
`11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b`), one cell `C-q8-official-raw`,
attempt `attempt-20260905T111245Z-cq8officialraw`, study commit `3be56ddc`, manifest SHA-256
`880171d4cfa47759b71ab6277af7c2a66b8a21949cdb6bef2b766b85e88a6eb2`.

Preregistration: `docs/readiness/2026-09-04-a2t-q8-quantization-probe-v1-preregistration.md`
(owner decision 2026-09-04: "GO as the closing model-usage check; no author query").
Full numbers:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-q8-quantization-probe-400-v1/result-summary.json`
(SHA-256 `3025bf00ae8ddb340e38c793b6fdf6b37e02b3b0cd9ae013b905bcbfbebbdce4`).
Paper-facing scorer: `a2t-toolcall-official` — the pinned release's own `metrics.py`, git blob
`d98277bcf69795c9a0ae54e538c170abfd8c51ca`, commit `b9d5383ca30945fbafb965a04bea40117e1e8a82`.

## Verdict: QUANTIZATION-EXCLUDED. And Tier 1 did not move by a single row.

On the four acceptance tiers the preregistered rule reads, C-q8 minus R-official-raw is
**+0.50 pp of tool accuracy, 4 saves / 3 harms / 193 ties, sign test p = 1.0000, tier-stratified
paired bootstrap CI90 [−1.50, +2.50] pp**. The interval contains zero, so the preregistered outcome
is **QUANTIZATION-EXCLUDED** (section 6): the residual gap between this study's Audio2Tool numbers
and the paper's is not the decoder quantization.

The sharpest single fact is smaller than the interval. **Tier 1 is 60.0 % on Q4_K_M and 60.0 % on
Q8_0 — zero saves, zero harms, all fifty rows landing on the same side.** The one tier that carries
the whole unexplained gap (−32.4 pp against the published 92.4) is the one tier the decoder
quantization does not touch at all. The same is true of `wearables`: 95 rows, 72.63 % both ways,
zero discordant pairs.

## What was varied, and what was held

One factor. The decoder GGUF is the umbrella lock's Q8_0 file
(`qwen3-omni-30b-a3b-instruct-gguf`, 32,484,494,336 bytes, SHA-256 `8a50e5a7d29ae6a2…`) instead of
the Q4_K_M requant. Everything else was held, and each hold is a receipt rather than an assertion:

- **The audio encoder is the same file.** The Q8 runtime receipt records the mmproj SHA-256
  `f0dfe825fb692d426362b1ac79678fc08daa4758f7151526cad110515f122883`, identical to the Q4 kit's.
- **The prompt is the same bytes.** llama-server mints a fresh media-marker nonce per session, so a
  rendered prompt can never re-hash across servers. Re-rendering the Q8 prompt with the sealed Q4
  session's own marker substituted hashes to
  `430c075bbb923d487ca959dc86ca7d7ade6372660001abab0223bdabcb53f231` — exactly the sealed
  R-official-raw `rendered_prompt_sha256`. Same chat template hash, same 16,143-character system
  message, same 3,581 text tokens.
- **The flight corroborates it independently.** Prompt tokens over 400 calls: **1,464,049 on both
  flights**, to the digit.
- **The audio never re-entered the encoder.** The cell read the feature-cache directory the sealed
  Q4 cell filled. It held 5,617 entries before the flight and 5,617 after, and the server log
  carries zero `encoding` lines.
- **The serving geometry is the same**: `-c 49152 -np 3`, 16,384 tokens per slot, `-fa on`,
  `-ctk/-ctv q8_0`, greedy, `max_tokens` 256, seed 20260803.

The one genuine consequence of the swap is weight placement, and it is forced: 30.3 GiB cannot be
resident on a 24,463 MiB card. `--n-cpu-moe 24` is the preregistered VRAM fit rule's own answer,
fixed model-free with zero generated tokens before takeoff.

## Per tier, official scorer, n = 50 per tier

Tool accuracy (%), paired on the same rows.

| tier | Q4_K_M | Q8_0 | Q8 − Q4 | saves | harms | ties | paper | Q8 − paper | CI90 (Q8) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| tier1_direct | 60.0 | **60.0** | **0.0** | 0 | 0 | 50 | 92.4 | −32.4 | [48.4, 70.6] |
| tier2_parametric | 74.0 | 76.0 | +2.0 | 1 | 0 | 49 | 84.6 | −8.6 | [64.9, 84.4] |
| tier3_multi_intent | 72.0 | 76.0 | +4.0 | 3 | 1 | 46 | 74.7 | +1.3 | [64.9, 84.4] |
| tier4_implicit | 28.0 | 30.0 | +2.0 | 3 | 2 | 45 | 33.4 | −3.4 | [20.6, 41.5] |
| tier5_needle | 78.0 | 76.0 | −2.0 | 1 | 2 | 47 | 90.6 | −14.6 | [64.9, 84.4] |
| tier6_correction | 84.0 | 86.0 | +2.0 | 2 | 1 | 47 | 81.5 | +4.5 | [76.1, 92.2] |
| tier7_multiturn | 58.0 | **58.0** | **0.0** | 0 | 0 | 50 | 54.6 | +3.4 | [46.4, 68.8] |
| tier8_intent_blending | 34.0 | **44.0** | **+10.0** | 6 | 1 | 43 | 41.7 | +2.3 | [33.1, 55.6] |
| **overall, n = 400** | **61.00** | **63.25** | **+2.25** | 16 | 7 | 377 | — | — | [59.2, 67.1] |

Pooled over all eight tiers the effect is real but small: **+2.25 pp, sign test p = 0.0931,
tier-stratified CI90 [+0.25, +4.25] pp**. Two thirds of it is one tier: tier 8 contributes +10.0 pp
on 6 saves against 1 harm. Under the extended `a2t-toolcall-v2` the same contrast is +2.50 pp
ordered (CI90 [+0.75, +4.50], p = 0.0525) and +3.00 pp multiset (CI90 [+1.00, +5.00], p = 0.0227).

**The decision block is narrower and it is null.** Restricted to tiers 1, 2, 5 and 6 — the four the
acceptance rule reads — there are 4 saves and 3 harms in 200 rows, delta +0.50 pp, CI90
[−1.50, +2.50].

### The other official metrics

| metric | Q4_K_M | Q8_0 | delta |
|---|---:|---:|---:|
| tool accuracy | 61.00 | 63.25 | +2.25 |
| exact match | 20.25 | 20.50 | +0.25 |
| parameter F1 (macro) | 31.65 | 31.36 | −0.28 |
| parameter F1 (micro) | 27.39 | 26.96 | −0.43 |
| parse rate | 99.75 | **100.00** | +0.25 |
| rows naming > 1 call | 52 | 66 | +14 |
| summed absolute per-tier gap to the paper | 77.3 pp | **70.5 pp** | −6.8 pp |

Paired, exact match is +0.25 pp (9 saves / 8 harms / 383 ties, p = 1.0000, CI90 [−1.50, +2.00]) and
parameter F1 is **−0.28 pp** (13 saves / 15 harms, p = 0.8506, CI90 [−1.97, +1.42]). The better
decoder picks the tool slightly more often and fills its arguments very slightly worse; neither
argument metric is separable from noise. The single tier-4 row that failed to produce a call-shaped
span on Q4_K_M parses on Q8_0, which is the whole of the parse-rate move.

## Per domain

The three official-population verdicts of 2026-09-04 all found `smart_home` to be the weak
stratum, so the probe reports the domain slice beside the tier slice. Tool accuracy (%), paired.

| domain | n | Q4_K_M | Q8_0 | Q8 − Q4 | saves | harms | ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| `wearables` | 95 | 72.63 | **72.63** | **0.00** | 0 | 0 | 95 |
| `smart_car` | 36 | 72.22 | 77.78 | +5.56 | 3 | 1 | 32 |
| `smart_home` | 269 | 55.39 | 57.99 | +2.60 | 13 | 6 | 250 |
| natural mixture | 400 | 61.00 | 63.25 | +2.25 | 16 | 7 | 377 |
| equal-domain | 400 | 66.75 | 69.47 | +2.72 | — | — | — |

Domain-stratified paired bootstrap on tool accuracy: delta +2.25 pp, CI90 [+0.50, +4.25],
p = 0.0931 — the same pooled figure the tier stratification gives, as it must.

**`wearables` is the reading that matters.** It is the domain the tier-1 official-population flight
found sitting *on* the published number (93.41 % at n = 91), and across 95 rows here the Q8_0
decoder does not change one of them. Where this runtime already matches the paper, quantization is
worth nothing; the +2.6 pp it buys on `smart_home` is the same small general lift the pooled figure
shows, not a repair of the stratum that is 36 pp low.

## C-q8 against the paper

Under the official-protocol replication preregistration's own definitions — PASS iff every
acceptance tier is within 5 pp with the rank order preserved, CONSISTENT-WITHIN-NOISE iff the paper
value sits inside every acceptance tier's Wilson CI90 — **C-q8 is FAIL**, exactly as R-official-raw
was. Tiers 1, 2 and 5 are outside 5 pp *and* outside their CI90. The rank order is not preserved:

- ours: tier6 > tier2 ≈ tier3 ≈ tier5 > tier1 > tier7 > tier8 > tier4
- paper: tier1 > tier5 > tier2 > tier6 > tier3 > tier7 > tier8 > tier4

Fraction of each tier's Q4-to-paper gap that the Q8_0 decoder closes: tier 1 **0 %**, tier 2 19 %,
tier 4 37 %, tier 5 **−16 %** (it moves away), tier 3 and tier 8 pass the paper row outright, and
tiers 6 and 7 were already above it. The summed absolute gap falls from 77.3 pp to 70.5 pp, and
essentially all of the remainder is tiers 1, 5 and 2.

## Throughput and memory

| quantity | R-official-raw (Q4_K_M) | C-q8-official-raw (Q8_0) |
|---|---:|---:|
| decoder bytes | 18,557,053,952 | 32,484,494,336 |
| weight placement | fully resident, `-ngl 999` | `-ngl 999` + `--n-cpu-moe 24` |
| GPU memory in use | resident core | **21,930 MiB** of 24,463, 2,208 MiB free |
| server host RSS | — | **20,646 MiB**, of 49,783 MiB available |
| model load | 10.0 s | 16.0 s |
| contacts | 400 of 408 planned, 450 registered | 400 of 408 planned, 450 registered |
| speech audio | 2,159.688 s of 2,300 | 2,159.688 s of 2,300 |
| prompt tokens (total) | 1,464,049 | **1,464,049** |
| completion tokens (total) | 6,523 | 7,019 |
| mean latency per call | 0.782 s | **6.141 s** |
| generation wall at 3 slots | — | 953.4 s (0.265 h) |
| contacts per second | — | 0.4195 |
| GPU hours used | 1.0 registered | **≈ 0.29** of 4.0 registered |
| GPU `enforced.power.limit` | 100.00 W | 100.00 W before and after |

**Q8_0 with 24 layers of experts in host RAM costs 7.85x the per-call latency of the resident
Q4_K_M core** — not the 4.17x of the August whole-model-offload note, and not the 32x the 4-row
smoke projected. The smoke's figure was an artefact of a cold page cache: its four calls paid to
fault 14 GiB of CPU-resident expert tensors in from ext4. Steady state over 400 calls is 6.141 s.
The whole flight, preflight hashing and model load included, took 17.4 minutes.

## Caveats, recorded rather than tuned away

1. **Placement is a numerical-implementation detail, not a protocol factor.** CPU and CUDA kernels
   accumulate in different orders, so a rare greedy tie can flip. The preregistration said this in
   advance and it stays a caveat. It cuts *against* over-reading the +2.25 pp, not for it.
2. **The mmproj headroom was never tested.** llama.cpp estimates the audio encoder's worst-case
   compute buffer at 2,940 MiB against the 2,228 MiB this placement leaves free. Every one of the
   400 rows was a feature-cache hit (5,617 entries before and after, zero `encoding` lines), so no
   encode ran. A future Q8 cell on uncached audio must re-derive the placement.
3. **The GPU's enforced power limit wobbled 96.8–98.3 W around its 100.00 W nominal during
   generation**, with no throttle reason active (`clocks_throttle_reasons.active` 0x0, SW Power Cap
   and HW Slowdown both Not Active, 57 °C) and 100.00 W recorded before and after. This is laptop
   dynamic-boost arbitration, not the Quiet-mode 35 W collapse the standing operating note warns
   about, and it cannot have bound a workload drawing ~21 W at 4–12 % GPU utilisation because 24 of
   48 MoE layers were running on the CPU.
4. **n = 50 per tier.** The per-tier deltas in the table above each rest on between 0 and 7
   discordant pairs. Only the pooled figures are worth reading as effects.

## What this changes

The owner's 2026-09-04 framing was that the alignment axes that matter are the prompt, the way the
model is used, and the scoring script. The scoring script has been the release's own since
2026-09-04. The prompt has been the release's own, proved byte-identical, since the same day. This
flight closes the last controllable "model usage" suspect: **the decoder quantization is worth
+2.25 pp pooled, 0.0 pp on tier 1, and 0.0 pp on the domain that already matches the paper.**

What remains unexplained, in the order this flight would now rank it:

1. **The audio front-end.** The prompt-fit receipt proves the rendered *text* is the published
   text. Nothing proves that llama.cpp's mtmd audio path produces the same speech representation
   the HF processor hands the model. It is now the largest named difference left between this
   runtime and the paper's, and it is the one difference the whole tier-1 anomaly is consistent
   with: a tool-selection failure concentrated in one domain, unaffected by prompt, whitespace,
   roster or quantization.
2. **The published tier-1 row itself.** The paper reports 92.4 for both tool accuracy *and* exact
   match on tier 1 — identical figures on one tier and nowhere else — which requires a run that
   emitted no unsolicited argument on any tier-1 row while choosing the right tool 92.4 % of the
   time. Five separately sealed cells have now failed to reproduce either half: `A0prime-legacy-raw`,
   `R-official-raw`, `T1-official-pop-500`, `W-official-raw-yaml` and `C-q8-official-raw`. The owner has ruled the
   authors will not be asked.

Suspects now closed by measurement: the reconstruction (−5.50 pp, 2026-09-04), the system-prompt
whitespace variant (+1.00 pp, p = 0.5034), the roster (+5.6 pp at n = 500), and the decoder
quantization (+0.50 pp on the acceptance tiers, CI90 containing zero).

## What this authorizes

Nothing new. The population is exposed discovery data and no knob was tuned on it. This is not a
superiority, generality or Stage-3 claim.

**Q8_0 does not become the operating core by this document.** The probe records the cost so the
owner can decide: 7.85x the per-call latency, 21,930 MiB of VRAM and 20,646 MiB of host RAM, in
exchange for +2.25 pp of pooled tool accuracy and nothing at all on the tier that carries the gap.
On that trade the Q4_K_M core remains this study's frozen core, as the owner's 2026-09-04 ruling
already had it, and every later Audio2Tool table can now carry the measured per-tier Q8 bound
beside the paper's bf16 row instead of an assumption.

Mechanism work stays stopped.
