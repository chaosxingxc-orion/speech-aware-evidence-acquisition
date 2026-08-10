# Serving configuration: decision and the measurements behind it (2026-08-09)

Closes the open question of whether to move the audio encoder (`mmproj`) to CPU
and raise the parallel slot count, versus keeping everything on GPU at four
slots.

**Decision: keep `-c 49152 -np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0` with the
encoder on GPU, unchanged for all of SAEA-E-002 and Wave 1.**

## What was measured

| configuration | GPU utilisation | throughput | note |
|---|---|---|---|
| encoder on GPU, `-np 4` | 99–100 % sustained | **13.1 s/slice** (live, first 13 slices); **11.6 s/slice** over a 581-slice run | 23.4 GB of 24.5 GB resident |
| encoder on CPU, `-np 4` | **median 0 %** | not run to completion | the GPU starved waiting on CPU-side audio encoding |
| CPU encode in isolation | — | ~1.6× slower than GPU encode | the encoder itself is not badly CPU-bound |

At 11.6–13.1 s/slice a ten-sample Earnings-21 arm (~610 slices) costs **≈2 h**,
so a three-arm paired experiment is **≈6–7 h** including per-arm model loads.

## Why the producer–consumer idea did not pay off here, and what would change that

The appeal of moving the encoder to CPU was overlapping audio encoding with GPU
decoding — a genuine producer–consumer pipeline. The measurement says that at
four slots it does the opposite: the GPU sits idle at a **median 0 %**
utilisation, because four concurrent samples cannot keep the decoder fed while
each one waits on a CPU encode.

That is a result about **four slots**, not about the idea. Since CPU encode is
only ~1.6× slower than GPU encode, enough concurrent slots would in principle
hide the encode latency entirely, and would buy back the VRAM the encoder
occupies. It was not tested at a higher slot count, and doing so costs GPU hours
that Wave 1 needs more. The question is parked, not answered.

An earlier endorsement of the CPU-encoder configuration in this study's working
notes was **based on a comparison that was not like-for-like** (an 88-request
mixed workload against an 8-request worst-case one) and should not be relied on;
the table above supersedes it.

## The constraint that makes this moot mid-experiment anyway

Serving arguments are part of the composed config and therefore of the run's
config hash, and encoder placement can perturb numerics (CPU and GPU float paths
are not bit-identical). A paired experiment is only readable if every arm shares
one config hash, so the serving configuration **cannot** change between the arms
of SAEA-E-002 regardless of which is faster. Any revisit happens at a clean
experiment boundary, never inside one.

## Open: decode is ~10× slower than this hardware should give (2026-08-10)

The server log — persisted for the first time this run — shows the split
between prefill and generation, and generation is the problem:

```
prompt eval time =  9964.35 ms /  4691 tokens   (470.78 tokens per second)
       eval time = 61354.67 ms /   209 tokens   (  3.41 tokens per second)
      total time = 71319.02 ms
```

Three consecutive requests give 3.41 / 3.07 / 4.40 tokens per second of
generation per slot. Across the completed no-evidence arm the aggregate is
114,345 completion tokens in 118 minutes ≈ **16 tokens per second total**, for a
30B-A3B MoE (3B active) at Q4_K_M on a 5090. The prefill:decode ratio is about
**138:1**, where 10–30:1 is normal — prefill is healthy, decode is not.

This also settles a question the arm times raised: the evidence arm's 2.4×
slower slices are **not** a prompt-cache miss. The cache is live
(`cache state: 8 prompts, 2043.232 MiB`); evidence simply raises prefill from
~1k to ~4.7k tokens, and prefill is the cheap half.

Leading suspect is `-ctk q8_0 -ctv q8_0`: quantised KV must be dequantised on
every decoded token, and it can push flash attention onto a slower path. Those
flags exist to fit a 49,152-token context on a 24 GB card, so any change trades
against the context sizing above and must be measured, not assumed.

Worth doing properly, because a 2–5× decode speedup would compress every
remaining arm in the study from hours to a fraction. Requires an idle GPU; do
not touch it mid-sequence, and note that serving args are inside the config
hash, so any change lands at a clean experiment boundary.

## Sizing rationale for the current values, for the record

- `-c 49152` with `-np 4` gives **12,288 tokens per slot**. The worst request in
  this study is a ConEC-evidence arm at ≈11.8 k tokens (that material tokenises
  at 2.19 bytes/token), so 12,288 is the minimum viable, not a comfortable
  margin.
- `-ctk q8_0 -ctv q8_0` is what keeps that context on the GPU at all: it left a
  1,057 MiB margin that held at +0 MiB across an 88-request test. An earlier
  `-c 32768` configuration left ~500 MB free and the server lost its CUDA
  context mid-run.
- `-ngl 999` disables llama.cpp's own device-memory fitting. That is deliberate
  (everything must be resident), but it is also why a competing CUDA context is
  so damaging: spilled allocations are never migrated back, so throughput stays
  degraded after the competitor exits. Hence the standing rule that no
  CUDA-capable process may run beside a live experiment, enforced in
  `scripts/run_arm_sequence.sh`.
- `max_tokens: 1024` bounds a degenerate slice. Uncapped, decoding runs until
  the 12,288-token slot fills, which outlasts the request ceiling; see the
  exposure ledger's fourth-stop entry and its correction.
