# Segmentation: what a call actually costs, and where the granularity should go (2026-08-09)

Prompted by the owner's proposal to replace the fixed 60 s window with
sentence-level segmentation, feeding text history as context, on the
expectation that inference cost would drop and accuracy might rise. Measured
against the 614 calls of the first completed SAEA-E-002 arm.

## The per-call cost model

Least squares over all 614 calls, whose slice durations range 13–60 s:

```
prompt_tokens = 12.87 × audio_seconds + 228        (R² = 0.891)
latency_seconds ≈ 0.678 × audio_seconds            (at 4-way concurrency)
```

Audio costs **12.87 prompt tokens per second**. The **228-token intercept is a
per-CALL fixed overhead** — system prompt, task instruction, and the rolling
text tail — and it is multiplied by the number of calls, not by the audio.

Projected onto the same 30,408 s of unique audio:

| segmentation | calls | prompt tokens | vs current |
|---|---|---|---|
| current: 60 s windows, 1.20× overlap | 612 | 609,493 | 1.00× |
| 30 s, no overlap | 1,014 | 622,856 | 1.02× |
| 10 s, no overlap | 3,041 | 1,085,740 | 1.78× |
| **5 s sentence-ish, no overlap** | 6,082 | 1,780,068 | **2.92×** |
| **90 s, no overlap** | 338 | 468,561 | **0.77×** |

(The model reproduces the arm's measured 611,164 prompt tokens to within 0.3 %.)

**Finer segmentation costs more, not less.** At 5 s a call pays 228 tokens of
overhead to carry 64 tokens of audio — 78 % overhead. And because text history
is part of that per-call overhead, *enriching* the context makes the penalty at
fine granularity worse, not better.

The cost win runs the other way: **fewer, longer, non-overlapping** calls.

## Why the segmentation should change anyway

The accuracy argument for leaving fixed windows is much stronger than the cost
argument, and it comes from the deletion analysis
(`2026-08-09-deletion-mass-is-made-at-the-stitch.md`):

- the dominant error mechanism — 10,693 excess-removed words, 86 % of all
  deletions, r = 0.847 per sample — is the **stitch dedup**, and the stitch
  dedup exists **only because consecutive slices overlap**;
- the secondary mechanism — 1,648 s advanced past untranscribed — exists only
  because the loop takes a **model-declared boundary** on trust.

A non-overlapping, pause-aligned segmentation removes both **by construction**:
nothing to dedup, and no boundary for the model to declare.

## The dependency asymmetry, and why it changes what the table above *means*

Raised by the owner: the two dependencies a speech decoder needs are not the
same kind. **Acoustic dependency is short-range** — the signal that
disambiguates a phoneme is local. **Discourse dependency is long-range** — who
is speaking, which company, which quarter, what number was quoted two minutes
ago. And decoding the audio *needs* that long-range textual context.

The current design conflates them: **one 60 s window serves both roles**, while
the text carried across slices is a fixed 400-character tail (~100 tokens). The
ratio is backwards relative to where the information sits.

The two also have opposite cost structures, which the table above measures in
the wrong unit to expose:

- **Audio is a hard linear cost.** 12.87 prompt tokens per second, re-encoded
  every call, and the latency fit is `0.678 × audio_seconds` with **no
  significant fixed term** — so audio seconds are what actually buys wall clock.
- **Text history is an append-only stable prefix.** It is exactly the case
  llama-server's prompt cache exists for, and this repo already orders content
  evidence-text-first / audio-last for prefix-cache friendliness. Token
  accounting charges it in full on every call; wall clock may not.

If that holds, "short audio window + long text history" is expensive in tokens
and nearly free in time — and the architectural direction is right while the
cost table's *implication* is wrong. The token table stands as measured; what it
cannot settle is which unit binds.

**Cheap decisive test, minutes not hours:** hold the audio fixed, vary only the
text-prefix length, and see whether latency tracks it. Run it the moment the GPU
frees. Until then, do not spend an arm on the assumption either way.

**What this study cannot currently learn:** 604 of the 614 slices are exactly
60 s, so there is no variation in audio-window length to regress against
quality. A-2a (30/60/90 s) is the arm that supplies it, and under this framing
its purpose sharpens — it measures **how short the audio window can get before
accuracy falls**, i.e. the effective range of the short-range acoustic
dependency. It should be paired with a text-history sweep (400 / 1600 / 4000
chars) so the two windows are ablated separately rather than as one knob.

## Recommended shape

**VAD-packed, non-overlapping, still long: cut only at a pause, pack
consecutive speech up to a 60–90 s target.** That keeps the cheap end of the
cost curve (0.77–1.00×), deletes the study's two measured deletion mechanisms,
and retains the text-history conditioning that is already in place
(`obs_condition_tail_chars: 400` — the proposal's second half is implemented).

## The precondition nobody has measured yet

Pause-aligned cutting needs pauses, and **the VAD as configured finds none**.
With `obs_vad_trim_min_seconds: 5.0`, across all 614 slices of a completed arm
the energy VAD produced **1 trim totalling 0 s**. Earnings calls are continuous
professional speech; there are essentially no 5-second silences. Inter-sentence
pauses in this register run 0.3–0.5 s, and that distribution has not been
measured on this carrier.

### Measured (2026-08-10, model-free, first 600 s of each discovery sample)

Per-file adaptive threshold — halfway between that file's own 5th and 95th
percentile frame energy, minus 6 dB — on 20 ms frames:

| sample | floor p05 dB | silence | pauses ≥0.3 s | ≥1.0 s | a ≥1 s cut every |
|---|---|---|---|---|---|
| 4330115 | −79.6 | 18.3 % | 108 | 21 | 28.6 s |
| 4365024 | −73.9 | 13.3 % | 68 | 18 | 33.3 s |
| 4365948 | −63.1 | 19.7 % | 129 | 33 | 18.2 s |
| 4366429 | −65.6 | 32.5 % | 144 | 49 | 12.2 s |
| **4366522** | **−33.2** | **0.0 %** | **0** | **0** | **never** |
| 4384964 | −60.5 | 28.6 % | 151 | 25 | 24.0 s |
| 4385072 | −74.2 | 27.2 % | 173 | 20 | 30.0 s |
| 4387383 | −48.3 | 12.4 % | 62 | 11 | 54.5 s |
| 4389907 | −55.0 | 25.6 % | 197 | 21 | 28.6 s |
| 4397829 | −66.3 | 23.5 % | 148 | 43 | 14.0 s |

**Pause-aligned packing at a 60–90 s target is feasible for 9 of 10 samples**
— a ≥1 s pause arrives every 12–55 s, comfortably inside the target.

Two things fall out that the plan has to absorb:

1. **The noise floor spans 46.4 dB across files** (−79.6 to −33.2). No fixed
   absolute threshold can serve this corpus; the threshold must be derived
   per file. This is part of why the shipped `obs_vad: energy` configuration
   finds nothing.
2. **4366522 has no detectable silence at any threshold** — its whole dynamic
   range is about 7 dB (p05 −33.2, p95 −25.8), i.e. heavily compressed or
   limited audio. Energy VAD is blind on it by construction. It needs the
   spectral VAD (`obs_vad: webrtc`, already an allowed value) or a hard-cap
   fallback cut, and a packer without that fallback would run one sample as a
   single unbounded chunk.

Correction to the note above: the VAD is not inert in the signal, only at the
**configured 5 s trim** — pauses of that length are genuinely rare (11 in 2,158 s
on the most pause-rich file). The usable structure lives at 0.3–1.0 s.

Consequence for the advance-overrun estimate in
`2026-08-09-deletion-mass-is-made-at-the-stitch.md`: that measure divides word
count by a flat 2.54 w/s over the slice's **raw** duration, so a slice that is
30 % silence looks like under-transcription when it is not. Silence density
varies 0–32 % across these files, which is very likely why the overrun measure
correlated at −0.131 with deletions. **It should be recomputed against
silence-corrected speech duration before being used for anything.** The stitch
measure is unaffected — it compares raw production to final output, never to
duration.

(One file emits a libmpg123 `part2_3_length too large` frame error on decode;
harmless here, but it is the same message that appears in the driver logs.)

Scope note: this concerns the VAD **trim**. The boundary **snap**
(`obs_silence_snap_seconds: 2.0`) is a separate mechanism and is not measured
here.

## Immediate consequence for E-004

The ladder's A-3a arm toggles `obs_vad_trim_min_seconds` between 5.0 and 0.
Since the trim fires once in 614 slices, **that contrast is empty** — the two
arms would be the same run at different config hashes, and it would burn an
hour to learn nothing. Either re-point the arm at a threshold where the trim
actually fires, or drop it and spend the hour on the segmentation question,
which the evidence says matters far more.
