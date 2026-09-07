# Audio2Tool input-rate audit — what actually converts 24 kHz to 16 kHz, and what it costs

**AUDIO2TOOL IS THE ONLY CARRIER IN THIS STUDY WHOSE AUDIO IS RESAMPLED BY llama.cpp, AND THE
RESAMPLER THAT DOES IT IS THE ONE MINIAUDIO ITSELF LABELS "FASTEST, LOWEST QUALITY".** Every
Audio2Tool release wav is 24 kHz mono; the Qwen3-Omni front end hard-codes 16 kHz; nothing in this
study converts between them. The study base64s the sealed bytes verbatim and the conversion happens
inside `ma_decoder`, as **two-tap linear interpolation preceded by a 4th-order Butterworth low-pass
at 8 kHz** — measured here at **−2.07 dB at 7 kHz and −3.02 dB at 7.5 kHz in the passband**, and
passing an 8.1 kHz input tone back into the speech band at only **5.65 dB below its input level**.
The study's own decoder, `librosa` `soxr_hq`, is flat to 7.5 kHz and puts nothing above 8 kHz back.
The two also disagree on length: llama.cpp emits `floor(2n/3)` output samples and drops up to
**41.7 µs**; librosa emits `ceil(2n/3)` and drops nothing.

Row `SAEA-A2T-MF-INPUT-RATE-AUDIT-V1` (`model-free-check`). **Zero model, tokenizer, embedder,
retriever, scorer, network and GPU contacts; zero audio seconds delivered to any service; zero
llama.cpp targets built, zero llama.cpp binaries executed and zero files written under the llama.cpp
checkout.** **No dataset byte of any kind was opened** — every sample measured here is a synthetic
tone the runner generated — and the offline guard recorded zero outbound connection attempts. The
row is landed in the same commit as its receipts rather than ahead of them, and that is stated
rather than dressed up: there was no contact to pre-register.

Receipt: `docs/checks/speech-aware-evidence-acquisition/2026-09-07-a2t-input-rate-audit/`
(`summary.json`, `tone-response.csv`, `MANIFEST.sha256`; the receipt carries no timestamp, so two
back-to-back writes reproduce the same `MANIFEST.sha256`). Runner
`scripts/run_a2t_input_rate_audit.py`, tests `tests/unit/test_a2t_input_rate_audit.py`.

**Sources.** `llama.cpp-featcache` detached and clean at build commit
`04ccc72a2207347ca76161b93fd9d846dd0a8675` — the commit `docs/receipts/runtime-q4km-featcache-04ccc72a.json`
pins and the one every sealed Audio2Tool arm was served from. Six files are cited below and all six
are re-hashed by the runner before a line number is trusted:

| file | sha256 |
|---|---|
| `vendor/miniaudio/miniaudio.h` | `ac7af4de748b7e26b777f37e01cee313a308a7296a3eb080e2906b320cc55c89` |
| `tools/mtmd/mtmd-helper.cpp` | `cb0bb84a55640be49a2ec5f2d6b95c97afa7775eaffc0d1ebe1e79dfb68f4064` |
| `tools/mtmd/mtmd.cpp` | `8accbc17efb1b301e7b02fff5522376e95990f477ad4f4f0f389eceb3c2b3109` |
| `tools/mtmd/clip.cpp` | `c7eaf112c2e067d3552af04f00fbe6cbcb6145cedf0f0f4a9040662760b87308` |
| `tools/server/server-common.cpp` | `7d86566ac735e2c0e7a3d78719b49fdb8383786fd142c8b4df9dd303ba1f6e96` |
| `tools/server/server-context.cpp` | `e235949a10bfa9284b8d79c735b638569e3db533e0eee8da2f3e474ca2701248` |

---

## 1. The path, layer by layer

Every line is a citation, not a paraphrase.

| layer | file:line | what it does |
|---|---|---|
| the wire | `core/model/transport.py:295` | `data_b64 = base64.b64encode(media.read_bytes())` into an `input_audio` part whose `format` is the file suffix. **The study sends the sealed 24 kHz bytes verbatim** — no resample, no trim, no normalization, no re-encode. |
| request parse | `tools/server/server-common.cpp:1347-1356` | `type == "input_audio"` → `handle_media(out_files, url, opt.media_path, false)`. The comment is explicit: *"don't need to validate `format`, it's redundant"* — the declared format is never used. |
| base64 | `tools/server/server-common.cpp:1241-1247` | `auto decoded_data = base64_decode(url); ... out_files.push_back(decoded_data);` — the container bytes are pushed **untouched**. |
| handoff | `tools/server/server-common.cpp:704` | `mtmd_helper_bitmap_init_from_buf(mctx, file.data(), file.size(), is_placeholder)`. Nothing between the wire and miniaudio inspects, reformats or resamples. |
| sniff | `tools/mtmd/mtmd-helper.cpp:514`, `:523-531` | `is_audio_file(...)` → `decode_audio_from_buf(buf, len, mtmd_get_audio_sample_rate(ctx), pcmf32)`. |
| target rate | `tools/mtmd/mtmd.cpp:1692-1697` → `tools/mtmd/clip.cpp:1536`, `:1552` | `mtmd_get_audio_sample_rate` returns `clip_get_hparams(ctx->ctx_a)->audio_sample_rate`; for `PROJECTOR_TYPE_QWEN3A` that is **hard-coded `16000`**, not read from the GGUF. |
| **the decoder** | `tools/mtmd/mtmd-helper.cpp:461-467` | `ma_decoder_config_init(ma_format_f32, 1, target_sampler_rate)` then `ma_decoder_init_memory(...)`. **miniaudio 0.11.25** (`vendor/miniaudio/miniaudio.h:3750`), vendored and — see §4 — unmodified by the fork. For a 16 kHz file this is a format cast; **for a 24 kHz file it is a resample.** |
| **the resampler** | `vendor/miniaudio/miniaudio.h:62890` | `config.resampling = ma_resampler_config_init(..., ma_resample_algorithm_linear)`. mtmd never overrides `decoder_config.resampling`, so the stock linear resampler runs. |
| its own label | `vendor/miniaudio/miniaudio.h:5403` | `ma_resample_algorithm_linear = 0, /* Fastest, lowest quality. Optional low-pass filtering. Default. */` |
| its filter | `:12233`, `:4284`, `:53979` | `MA_DEFAULT_RESAMPLER_LPF_ORDER` is **4**, clamped to `MA_MAX_FILTER_ORDER` = 8; `ma_resampler_config_init` sets `config.linear.lpfOrder = ma_min(4, 8)`. |
| what that filter is | `:3203`, `:3003-3010` | `ma_lpf` is a *"High order low-pass filter (Butterworth)"*; the documentation states the low-pass runs **before** downsampling and its cutoff *"defaults to half the sample rate of the lowest of the input and output sample rates"*. |
| the cutoff, for 24→16 | `:53096-53099`, `:53106-53109` | the rates are first reduced by their GCF (8000), so 24000/16000 becomes **3/2**; then `lpfSampleRate = max(3,2) = 3` and `lpfCutoff = min(3,2) × 0.5 = 1.0`. Normalized back, that is a Butterworth at **8 kHz running on the 24 kHz stream**. |
| the interpolation | `:5346-5368`, `:53126-53127` | the state carries `x0` (*"the previous input frame"*) and `x1` (*"the next input frame"*) — **two-tap linear** — advanced by a fixed-point step `inAdvanceInt = 3/2 = 1`, `inAdvanceFrac = 3 % 2 = 1`, i.e. **1.5 input frames per output frame**. |

### 1.1 Audio2Tool is the only carrier this applies to

| carrier | what goes on the wire | what miniaudio does |
|---|---|---|
| Earnings-21 buf90 windows | 16 kHz mono WAV slices cut at runtime by `reproduction.obs_loop` | format cast |
| Earnings-22 ESB utterances | 16 kHz mono WAV | format cast |
| SLURP DEV-1000 | 16 kHz mono PCM_16 FLAC (and in the sealed comparator, encoder packets, which bypass the decoder entirely) | format cast |
| **Audio2Tool** | **24 kHz mono WAV** | **resample** |

The reason the other three are already at 16 kHz is that **this study converts them itself**:
`reproduction/obs_loop.py:481-537` (`decode_parent_pcm`) decodes every Earnings parent with
`librosa.load(str(path), sr=16000, mono=True)` and quantizes with
`clip(rint(float32 × 32767), −32768, 32767)`, preferring `ffmpeg` when present — and `ffmpeg` is
deliberately absent on this machine, so the librosa branch is the one that has always run.
`analysis/slurp_mf7b_vectors.py:166-188` (`read_audio_wav_bytes`) uses the same rule for SLURP. So the
study already has one pinned decode-and-resample path; Audio2Tool is simply the one carrier that has
never been put through it.

---

## 2. Truncation: llama.cpp floors, we ceil

`decode_audio_from_buf` asks the decoder how long the output is and then reads **exactly** that many
frames, once:

`tools/mtmd/mtmd-helper.cpp:472-481`
```cpp
    result = ma_decoder_get_length_in_pcm_frames(&decoder, &frame_count);
    ...
    pcmf32_mono.resize(frame_count);
    result = ma_decoder_read_pcm_frames(&decoder, pcmf32_mono.data(), frame_count, &frames_read);
```

That length is a rate conversion of the file's own length (`vendor/miniaudio/miniaudio.h:67656`,
`ma_calculate_frame_count_after_resampling`), whose body **floors** and then tries to add one frame
back (`:17476-17483`):

```c
    outputFrameCount = (frameCountIn * sampleRateOut) / sampleRateIn;
    preliminaryInputFrameCountFromFrac = (outputFrameCount * (sampleRateIn / sampleRateOut)) / sampleRateOut;
    preliminaryInputFrameCount         = (outputFrameCount * (sampleRateIn % sampleRateOut)) + preliminaryInputFrameCountFromFrac;
    if (preliminaryInputFrameCount <= frameCountIn) {
        outputFrameCount += 1;
    }
```

For `sampleRateIn = 24000`, `sampleRateOut = 16000` the `+1` branch is **dead**: `sampleRateIn %
sampleRateOut` is 8000, so `preliminaryInputFrameCount ≈ 8000 × outputFrameCount`, which exceeds
`frameCountIn ≈ 1.5 × outputFrameCount` for every clip longer than one frame. The output is therefore
**exactly `floor(2n/3)`**.

**Measured, on tones at every `n mod 3`** (`summary.json` → `length_probe`):

| input samples @24 k | `n mod 3` | source s | llama.cpp out | librosa out | llama.cpp s | dropped s |
|---:|---:|---:|---:|---:|---:|---:|
| 24,000 | 0 | 1.000000000 | 16,000 | 16,000 | 1.000000000 | 0 |
| 24,001 | 1 | 1.000041667 | 16,000 | 16,001 | 1.000000000 | **0.000041667** |
| 24,002 | 2 | 1.000083333 | 16,001 | 16,002 | 1.000062500 | 0.000020833 |
| 24,003 | 0 | 1.000125000 | 16,002 | 16,002 | 1.000125000 | 0 |
| 35,932 | 1 | 1.497166667 | 23,954 | 23,955 | 1.497125000 | 0.000041667 |
| 21,697 | 1 | 0.904041667 | 14,464 | 14,465 | 0.904000000 | 0.000041667 |

`llama.cpp = floor(2n/3)` on 9 of 9 probes; `librosa = ceil(2n/3)` on 9 of 9. **The worst loss is
41.7 µs**, two thirds of one 24 kHz sample period. It is recorded because it is a real difference
between the two arms and because it must not be mistaken for the effect under test; at 160 samples
per mel hop it cannot move a single mel frame.

**One latent hazard, not fired here.** `decode_audio_from_buf` sizes `pcmf32_mono` to `frame_count`
**before** the read and never shrinks it to `frames_read` (`:480-485`); the bitmap is then built from
`pcmf32.size()` (`:534`), not from `frames_read`. A short read that still returned `MA_SUCCESS` would
therefore append silence rather than shorten the clip. On **9 of 9** probes `frames_read ==
frame_count`, so this did not fire — it is written down so a future short-read regression is
recognized rather than rediscovered.

---

## 3. The two resamplers, measured on one instrument

Both decoders were run on the same synthetic tones: 1.0 s each at amplitude 0.5, synthesized at
24 kHz as mono int16 WAV, decoded to 16 kHz, 50 ms trimmed off each end, then the output energy split
into a ±25 Hz bin at the frequency the tone should land on and everything else. The miniaudio side is
a **standalone C harness that reproduces `decode_audio_from_buf`'s call sequence line for line**,
compiled in a temporary directory against the checkout's read-only vendored header; no llama.cpp
target was built and no binary from the checkout was run. Reference tone level **−9.031 dBFS**.

| input Hz | lands at | llama.cpp dBFS | at own freq | librosa dBFS | at own freq |
|---:|---:|---:|---:|---:|---:|
| 100 | 100 | −9.032 | 1.0000 | −9.031 | 1.0000 |
| 1,000 | 1,000 | −9.068 | 0.99998 | −9.031 | 1.0000 |
| 3,000 | 3,000 | −9.361 | 0.99844 | −9.031 | 1.0000 |
| 5,000 | 5,000 | −9.928 | 0.98690 | −9.031 | 1.0000 |
| 6,000 | 6,000 | **−10.334** | 0.97140 | −9.031 | 1.0000 |
| 7,000 | 7,000 | **−11.097** | 0.94416 | −9.031 | 1.0000 |
| 7,500 | 7,500 | **−12.048** | 0.92453 | −9.462 | 1.0000 |
| 7,900 | 7,900 | −13.553 | 0.90533 | −60.037 | 0.99990 |
| 8,000 | 8,000 | −12.779 | 1.0000 | −330.309 | — |
| **8,100** | **7,900** | **−14.683** | 0.89445 | −104.568 | 0.00599 |
| **8,500** | **7,500** | **−17.826** | 0.86993 | −99.340 | 0.17284 |
| **9,000** | **7,000** | **−23.280** | 0.83380 | −330.309 | — |
| **10,000** | **6,000** | −38.440 | 0.74260 | −330.309 | — |
| **11,000** | **5,000** | −63.326 | 0.62841 | −330.309 | — |
| 11,900 | 4,100 | −102.800 | 0.03855 | −103.319 | 0.05489 |

Rows in bold above 8 kHz are **aliases**: the input frequency is gone, and what appears in the output
is a different tone at the folded frequency. Three readings:

1. **Passband droop.** llama.cpp is **1.30 dB down at 6 kHz, 2.07 dB at 7 kHz and 3.02 dB at
   7.5 kHz** — the −3 dB point of a 4th-order Butterworth nominally at 8 kHz, pulled in further by
   the linear interpolator's own sinc-shaped droop. librosa is within **0.001 dB to 7 kHz** and
   0.43 dB at 7.5 kHz, then cuts.
2. **In-band distortion.** llama.cpp's share of output energy *at the tone's own frequency* falls to
   **0.9716 at 6 kHz and 0.9442 at 7 kHz** — 5.6 % of what comes out of a 7 kHz tone is not a 7 kHz
   tone. librosa stays at 1.0000. That is the two-tap interpolator, not the low-pass.
3. **Aliasing.** An 8.1 kHz input reappears at 7.9 kHz only **5.65 dB below its input level**; 9 kHz
   folds to 7 kHz 14.2 dB down and 10 kHz folds to 6 kHz 29.4 dB down. librosa's worst leak above
   8 kHz is **90.31 dB down**, and most of the band is annihilated outright.

**Neither is "correct" and the note says so.** The two disagree in the 7.5–8 kHz band in *both*
directions: llama.cpp keeps content there attenuated, librosa's `soxr_hq` transition sits between
7,500 Hz (−0.43 dB) and 7,900 Hz (−51.0 dB) and removes it. Standardizing with librosa therefore
trades a gentle roll plus alias for a sharp cut, and the trade is only worth making if the corpus has
energy in the bands where they differ.

---

## 4. The featcache fork adds nothing to this path

`git diff --name-only fdbd6abee 04ccc72a2` touches eight files —
`tests/CMakeLists.txt`, `tests/test-server-tokens.cpp`, `tools/mtmd/mtmd.cpp`, `tools/mtmd/mtmd.h`,
`tools/server/CMakeLists.txt`, `tools/server/server-common.cpp`, `tools/server/server-common.h`,
`tools/server/server-context.cpp`. **`vendor/miniaudio/miniaudio.h`, `tools/mtmd/mtmd-helper.cpp`,
`tools/mtmd/mtmd-audio.cpp` and `tools/mtmd/clip.cpp` are unmodified from upstream.** The fork's one
addition next to this path is the `input_speech_features` content type, which is a *bypass*: it
accepts a pre-computed feature packet instead of raw audio and never reaches miniaudio. So on the
packet path (SLURP DEV-1000) no decoder runs at all, and on the raw-audio path (Audio2Tool,
Earnings-21) the decoder is stock upstream miniaudio.

---

## 5. What this settles, and what it does not

**Settled.**

* The 24 → 16 kHz conversion of every Audio2Tool request is done by miniaudio's linear resampler with
  a 4th-order Butterworth at 8 kHz, inside llama.cpp, and the study has never had a say in it.
* Audio2Tool is the **only** carrier where that happens; the other three are converted by this
  study's own `librosa` `soxr_hq` path, or bypass the decoder entirely.
* The two resamplers' output lengths differ by at most one 16 kHz sample and llama.cpp loses at most
  41.7 µs of the tail. That is far too small to move a mel frame and cannot be the effect under test.
* Standardizing the input rate to 16 kHz with `librosa` before the wire is therefore a **real,
  single-factor change to what the encoder sees** — it is not a no-op and it is not cosmetic.

**Not settled, and deliberately not guessed here.**

* **Whether it matters on this corpus.** The differences live at 6–8 kHz and above. How much of the
  Audio2Tool frozen 400's energy is up there is a property of the corpus, not of the resampler, and
  it is measured under the media row `SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1`, not here.
* **Whether it helps.** Nothing in this note licenses any claim about tool accuracy. The cell that
  can is preregistered in
  `docs/readiness/2026-09-07-a2t-input-rate-standardization-v1-preregistration.md` and is not
  authorized.
* **Whether `soxr_hq` is the right target.** It is the study's *existing* pinned convention and that
  is the only reason it is the one proposed. A sharp cut at 7.6 kHz is a choice, and §3 records what
  it costs as well as what it buys.
* **Nothing about the mel front end.** The padding, block rounding and token accounting downstream of
  the decoder are the 2026-09-07 short-clip encoding audit's subject and are unchanged by anything
  here.
