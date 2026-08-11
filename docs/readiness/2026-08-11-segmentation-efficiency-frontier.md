# Segmentation strategies vs efficiency: the measured frontier, and the probe ladder that settles it (2026-08-11)

Owner directive: consolidate the segmentation/efficiency discussion into one
systematic comparison so later validation runs are chosen mechanically instead
of argued case by case. Everything quantitative below is measured in this
study; predictions are labelled as predictions and each carries the probe that
falsifies it. Efficiency is the contract's third axis (calls, tokens, latency,
GPU, processed speech seconds) with **wall clock as the binding unit** — this
study pays no per-token API cost, but it does pay GPU hours. Tonight's
determinism result adds a second binding axis nobody planned for:
**reproducibility is a segmentation property too** (§2).

## 1. The measured constants everything below is built from

| quantity | value | source |
|---|---|---|
| audio prompt cost | 12.87 tok per audio-second | cost model, n=614, R²=0.891 (2026-08-09) |
| per-call prompt intercept | 228 tok (system + instruction + rolling tail) | same fit |
| latency at the 60 s protocol | ≈ 0.678 × audio_seconds at 4-way; no significant fixed term **in the 13–60 s range** | same fit |
| output rate | ≈ 2.55 completion tok per audio-second (~153/slice) | bench fd7ba3 |
| audio encode (GPU) | 3.32 s per 60 s slice (n=622, p10 3.17 / p90 3.46); **linearity below 60 s unmeasured** | 2026-08-10 ledger |
| decode vs context | 13.07 tok/s per slot at 816-tok context; 6.31 at ~1,233 (4-way); 3.07–4.40 at ~4,700 — **points taken under different concurrency, curve is confounded** | server logs 72179f / fd7ba3, IC-001 memo |
| prefill | ~194 tok/s at ~900-tok prompts (4-way); ~470 tok/s at ~4,700 | bench / matched logs |
| stitch deletions | 86 % of all deletions (10,693 words, r=0.847) are made at overlap-dedup seams | deletion-mass memo (2026-08-09) |
| boundary overrun | 1,648 s advanced past untranscribed by the model-declared boundary | same |
| current overlap factor | 1.207× (612 calls over 30,408 s) | cost model |
| locked-config wall | 10.8 s wall per 60 s slice at 4-way = 5.5× real time; WER 0.2359 on fast-e21-sub3 | serving verdict (2026-08-10) |
| **run-to-run noise, same config hash** | **three runs of the identical configuration: mean WER 0.2359 / 0.2680 / 0.2604 (band 3.2 pp); per-sample range up to 13.6 pp with orderings inverting; slice counts 126/124/126; 114/129 slice responses diverge, first at slice 3** | fd7ba3 / 54a5e7 / E-002F-nocontext dfc630 (2026-08-11) |
| **per-call wall-clock floor** | **≈4.3 s** (two-point fit with slice10: latency ≈ 0.40×audio + 4.3 s at 4-way) — invisible in the 13–60 s fit range, dominant below it | slice10 probe f8292e (2026-08-11) |
| **per-call output intercept** | **~18 completion tok** (boundary-report format): slice10 slices emit 42.8 tok where the transcript needs ~25 | same |
| evidence block (SUPPLY arms) | 1,850 tok median / 5,835 worst per call, re-prefilled EVERY call — measured zero prompt-cache hits | 72179f log analysis (2026-08-11) |
| prompt-cache machinery | exact-prefix KV reuse present and on by default in the pinned build; media chunks hash-match; misses are caused by slot churn at 4×4 saturation | source audit of fdbd6abee (2026-08-11) |
| pause structure | a ≥1 s pause every 12–55 s in 9/10 discovery files; 4366522 is energy-VAD-blind (7 dB dynamic range) | cost-model memo §VAD |

The wall-clock identity per request, at fixed serving config:

```
latency ≈ encode(W) + prompt_tokens/prefill_rate + output_tokens/decode_rate(context) + floor
prompt_tokens = 12.87·W + 228 (+ evidence)
```

with three quantities still unmeasured: `floor` (HTTP/slot/scheduling/boundary
parse per call), `encode(W)` below 60 s, and `decode_rate(context)` at fixed
concurrency. Those three are exactly what the slice10 probe reads.

## 2. The noise mechanism, and why segmentation owns part of it

Two runs of the byte-identical configuration (same config hash `dc67f633…`,
same seed, temperature 0) produced different transcripts on every sample and
different slice counts. Mechanism, consistent with the C-config divergence in
the serving bench: **batch composition varies with request-arrival timing**,
matmul accumulation order changes, near-tie logits flip a token; then — and
this is the segmentation-owned part — **a flipped token near a boundary moves
the model-declared cut, which shifts the audio bytes of every later slice**.
One numeric flicker becomes a diverging cascade (126 vs 124 calls proves the
cascade, not just the flicker).

Consequences:

- Single-run paired deltas below ~±3 pp (3-sample mean) / ~±10 pp
  (per-sample) are **unreadable** at the current protocol. Tonight's E-002F
  fast set is registered with exactly that proviso.
- A segmentation without model-declared boundaries (S1/S2 below) removes the
  cascade: slice audio becomes run-invariant, and divergence shrinks to
  per-slice token flips that do not propagate. The interleaved policy (S4)
  has no cuts at all. **Reproducibility ranks segmentation strategies in the
  same order that seam-count does** — a second, independent argument for the
  same frontier direction.
- For confirmatory-grade paired reads there is also a serving-side option:
  single-slot serving (`-np 1`, batch-of-one is composition-invariant),
  estimated ~1.7× wall at the 60 s protocol (single-slot decode ~13 tok/s at
  ~1k context vs 6.31 shared). Owner decision for the full R4, not tonight's.

## 3. The strategies, side by side

Per hour of unique audio, bare-core arm, locked serving config A, 4-way.
"Seams" are places where two independently decoded texts meet — the measured
dominant WER mechanism. "Noise exposure" is the §2 cascade surface. Reference
row = S0.

| | strategy | calls | prompt tok | per-req context | seams (type) | noise exposure | predicted wall | status |
|---|---|---|---|---|---|---|---|---|
| S0 | **60 s buffer, model boundary, 1.2× overlap** (current) | 72 | 72.0 k (1.00×) | ~1,000 | 72 overlap-dedup | boundary cascade (measured ±3.2 pp) | **658 s (measured)** | locked baseline |
| S1 | 60 s fixed window, no overlap (`a1a-fixed-window-ojw`, exists) | 60 | 60.0 k (0.83×) | ~1,000 | 60 hard cuts | per-slice flips only, no cascade | ~550 s | E-004 A-1a arm, designed |
| S2 | pause-packed 60–90 s, no overlap (recommended shape, 2026-08-09) | 40–60 | 55–60 k (0.77–0.83×) | 1,000–1,400 | 40–60 pause-aligned | no cascade (cuts are signal-derived, run-invariant) | ~520–610 s | needs packer + per-file VAD threshold |
| S3 | 10 s buffer, 1.2× overlap (`a2a-buffer10-ojw`) | 432 | 154 k (**measured 2.11×**) | ~357 (measured 352) | **432 overlap-dedup** | cascade ×6 boundary decisions | **MEASURED: 1.75× SLOWER (42 vs 24 min) and WER 0.5337 (+27 pp)** | **DEAD — both kill-rules fired** |
| S4 | interleaved listen-and-spell, step S window W (IC-001) | 3600/S | 12.87·W/S per s + cached history | history + 12.87·W | none (continue-the-text) | no cuts; history content still noise-carrying | unknown; compaction-bound | design after P1–P3 |
| S5 | S0 + per-sample `id_slot` cache affinity | 72 | 72.0 k charged, stable prefix prefilled once | ~1,000 | 72 overlap-dedup | **reduces timing variance** (less prefill contention) — may shrink the cascade trigger | bare-core −5–10 %; **evidence arms −20–30 %** | bench proposal to owner |

What the table settles on measurement alone:

- **Token accounting always worsens with finer slicing** (the 228-tok
  intercept is per call): S3 pays 2.14×. On tokens alone S2 wins at 0.77×.
- **The seam count is the WER exposure.** S3 multiplies the mechanism behind
  86 % of deletions by 6. S1/S2 delete the dedup seam entirely; their
  hard/pause cuts carry an unmeasured but strictly gentler risk (A-1a
  measures the hard-cut case; a pause cut is gentler still).
- **S3's wall-clock case rests on two unmeasured quantities at once**: the
  decode-vs-context gain at fixed concurrency AND a per-call floor small
  enough not to eat it 432 times an hour. The 0.678·audio latency fit never
  saw a slice under 13 s — extrapolating it to 10 s is the kind of assumption
  this study refuses to run science on. Hence the probe.
- **S4 is the only strategy that removes both measured error mechanisms AND
  the noise cascade by construction** — its cost is governed by `W/S` (audio
  re-encode) and history length in the KV at decode, which is why compaction
  is a prerequisite, not a refinement.
- **S5 is orthogonal to all of the above**: no protocol semantics change,
  only who pays prefill. It is the only lever that specifically helps the
  evidence arms, whose per-call evidence block dwarfs the intercept and whose
  decode sits in the slow-context zone under every slicing.

## 4. The probe ladder (each rung ~25–40 min on fast-e21-sub3 unless noted)

| rung | probe | what it kills | status |
|---|---|---|---|
| P0 | determinism repeat (54a5e7 vs fd7ba3) | the run-to-run noise floor | **DONE: non-deterministic; 3-run band 3.2 pp mean, 13.6 pp per-sample** |
| P1 | `SAEA-BENCH-slice10-q4km` (S3) | decode-vs-context at fixed concurrency; per-call floor; encode(10 s); stitch×6 WER prediction | **DONE: both kill-rules fired — 42 min (1.75× slower), WER 0.5337 (+27 pp); floor ≈4.3 s/call; token model verified (2.11× vs 2.14× predicted)** |
| P2 | id_slot affinity bench (S5, matched-style arm) | cache-hit wall saving on evidence arms; batch-composition numerics effect (may also REDUCE noise) | proposal due to owner after the fast set |
| P3 | A-1a fixed-window contrast (S1) | hard-cut WER vs model-boundary WER; the 0.83× no-overlap gain; **cascade-free determinism check for free** (fixed windows ⇒ run-invariant slice audio) | designed inside E-004 wave1 |
| P4 | pause-packed prototype (S2) | pause-cut WER; packer feasibility incl. the VAD-blind file (webrtc fallback) | needs packer implementation; go/no-go after P1+P3 |
| P5 | interleaved W/S prototype (S4) | the step-size frontier with P1's floor and P2's cache constants plugged in | IC-001; design after P1–P4 |

Decision rules, pre-stated so the reading is mechanical:

- P1 WER degrades ≥3 pp → 10 s granularity is dead for scientific arms in ANY
  overlapping design; short steps survive only inside S4 (seamless) designs.
  **FIRED (+26.6 pp above the 3-run noise band).**
- P1 net wall ≥ 22.8 min (the S0 fast-split reference) → the per-call floor
  dominates; fine granularity is dead on efficiency grounds too, and the
  efficiency direction is locked to S1/S2 (fewer, longer calls) + S5 (cache).
  **FIRED (40.6 min net; floor ≈4.3 s/call, ~28 of the 42 minutes).**
- P1 net wall materially < 22.8 min AND WER holds → the decode-context effect
  is real and large; S4's design proceeds with priority, because it is the
  only way to keep short contexts without paying seams. **DID NOT FIRE — any
  S4 design must beat the 4.3 s floor per step, which at 1 s steps would be
  ~13× real time of pure overhead; steps below ~20 s are not viable on this
  serving stack without amortising the floor.**
- P2 saves ≥15 % on the matched-style arm → propose id_slot into the locked
  config via a re-lock bench before the full R4 re-run (two of its three arms
  carry evidence). Transcript A/B is part of that bench either way.
- P3 fixed-window WER ≥ model-boundary WER → the boundary machinery is not
  earning its cost; S2 inherits (pause-packing replaces the model boundary),
  and the noise cascade goes with it.
- Noise floor for the full R4 (owner decision, informed by P3): more samples,
  repeated runs, or `-np 1` deterministic serving at ~1.7× wall.

## 5. The config-lock protocol (owner directive 2026-08-11, standing)

Configuration decisions are locked on SMALL runs, never on campaigns:

1. **Venue**: fast-e21-sub3 for anything whose readout is wall clock,
   prefill sizes, or WER-equivalence-vs-noise-band (~25–40 min per
   configuration); the raw single-slice probe pattern (memory-strategy
   precedent, outside the driver) for pure serving-throughput questions
   (~minutes). Lightweight means a SMALL SLICE OF THE REAL WORKLOAD —
   60 s slices, real ConEC evidence sizes, 4-way concurrency — never a
   different-domain small corpus, whose prompt shape would lock the wrong
   configuration.
2. **Form**: registered bench namespace, pre-stated falsifiable predictions,
   mechanical adoption rules, ~1 GPU-h budget per decision.
3. **Throughput readings need n=3 single runs** (wall noise ~3%). **Quality
   readings at small n can only check equivalence against the measured
   noise band** — never small effects. Scientific claims stay on n=10+
   under a noise treatment; short-utterance carriers escape the floor
   entirely.
4. Anything that changes request bytes or output semantics enters through a
   fragment/config-hash change plus a bench — never a silent code default.

Applied so far: serving A/B/C, slice10, idslot, cacheorder, decode
attribution — six locked decisions in ~6 GPU-hours total.

## 6. Decode attribution (2026-08-11, SAEA-BENCH-decode-q4km)

M1 VRAM-spill and M2 quantized-KV-kernel are REFUTED (p50 6.59 / 6.73 vs
reference 6.74 tok/s per slot); M3 shows badly sublinear batched-MoE
scaling (aggregate ~13.1 / ~19.5 / ~27.0 tok/s at 1/2/4 slots). Single-slot
13 tok/s is 5–10× below the realistic band for a 3B-active MoE at Q4_K_M on
this card: **the deficit is intrinsic to the pinned llama.cpp build's MoE
decode path, compounded by WSL2 per-launch overhead. Next lever: the
version-upgrade bench (rebuild → receipt v2 rebind → transcript A/B →
re-lock), gated on owner authorization. vLLM is ruled out by owner
judgment.**

## 7. What this buys the full R4 re-run

The full set (three arms × 44 samples, two arms evidence-carrying) is the
next large spend — ~5 h under S0 today. The ladder can legally change that
only through re-lock benches, but the plausible end-state — S1/S2-shaped
observation (0.77–0.83× audio), S5 cache affinity for the evidence arms
(−20–30 % on two of three arms), cascade-free segmentation for reproducible
paired reads — puts **~3.5 h with a lower noise floor and lower seam-driven
deletion mass** within reach: cheaper, cleaner, and more reproducible at
once. The ladder's total probe cost is ~2 GPU-hours; it pays for itself
inside the first full-split campaign it shapes.
