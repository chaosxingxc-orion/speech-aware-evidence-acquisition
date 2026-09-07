# Earnings-22 short-clip encoding audit — what our path does to a short clip

**OUR SERVING PATH GLUES A BLOCK OF CONSTANT, NON-SILENT FEATURES TO THE END OF ALMOST EVERY
CLIP, AND CHARGES THE MODEL 13 AUDIO TOKENS FOR IT. THE PUBLISHED PATH MASKS THAT BLOCK AWAY.**
`mtmd_audio_preprocessor_qwen3a` rounds the mel spectrogram up to a whole number of 100-frame
blocks with the literal float `0.0` and the encoder graph emits 13 tokens per block whether the
block is speech or padding; the HF `Qwen3OmniMoeProcessor` path records each block's true length
and keeps only `ceil(length/8)` of its post-CNN positions. On the 1,500-row dev subset that is
**9,740 of the 139,282 audio tokens we send (6.99 %) computed from 75,330 frames — 753.3 seconds —
of padding**, and **1,498 of the 1,500 clips carry one**. On the full 6,038-row dev10 population it
is 39,378 of 550,992 tokens (7.15 %) over 3,044.4 s of padding on 6,032 of 6,038 clips.

**The effect is a SHORT-CLIP effect by construction, because the padded block is a fixed ≤ 0.99 s
and the clip is not.** Padding-derived tokens are **42.2 %** of what we send on sub-second clips,
25.0 % on 1–2 s, 13.8 % on 2–4 s, 8.2 % on 4–8 s, 4.5 % on 8–16 s and **2.5 %** at 16 s and above —
the same ordering as the arm A WER by duration (74.0 / 42.1 / 27.2 / 20.2 / 13.2 / 9.5 points,
usage-cells verdict §4.4). The worst single clip in the population sends **10 of its 13 audio
tokens** out of padding.

**And the padding is not silence.** The pad is `0.0` in the ALREADY-NORMALIZED mel space, where the
whisper normalization `v -> (max(v, max-8)+4)/4` puts a clip's own floor at a median of **−0.7152**
and its peak at **+1.2848**. Digital silence appended to the same clips lands exactly on that floor
(median −0.7152, identical to 6 decimals). `0.0` sits 0.72 units above it on a scale whose whole
span is 2.0, and **66.4 % of the real mel bins in a clip are BELOW it**. For up to 0.99 s after the
last word, the encoder is handed a flat band across all 128 mel bins that is louder than two thirds
of the clip's own speech — not room tone, not a stop, and not anything the training distribution
contains.

**The arithmetic is proved, not asserted.** The transcription of the llama.cpp front end reproduces
**all 6,038 sealed `prompt_tokens` records of arm A with a single 49-token text envelope** — one
distinct envelope across the whole flight, which is only possible if this audit's audio-token
formula is the server's own.

**What this does NOT say.** It does not say the padding causes the 7-point boundary insertion mass;
it says our path carries a short-clip encoding artifact of exactly the shape the hypothesis
predicted, and it prices it. **No fixed 30-second window is applied on our path** — the classic
Whisper 30-s pad is present in the code and is not on this branch — so that half of the hypothesis
is answered NO. Three preregistered probes turn the rest into a measurement
(`docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md`); none is flown here.

Row `SAEA-E22-MF-SHORT-CLIP-ENCODING-AUDIT-V1` (`model-free-check`). **Zero model, tokenizer,
embedder, retriever, scorer, network and GPU contacts; zero audio seconds delivered to any service;
zero llama.cpp processes started and zero llama.cpp sources modified**, and the offline guard
recorded zero outbound connection attempts. The row is landed in the same commit as its receipts
rather than ahead of them, and that is stated rather than dressed up: there was no contact to
pre-register, and the only sealed values it opened are `usage.prompt_tokens` integers on a dev
population three earlier rows had already read.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-short-clip-encoding-audit/`
(`MANIFEST.sha256`; `summary.json` sha256 `e6f765ae…`, `per-clip-table.csv` `34b77b8c…`; the
receipt carries no timestamp, so two back-to-back writes reproduce the same `MANIFEST.sha256`).
Module
`analysis/e22_short_clip_encoding.py`, runner `scripts/run_e22_short_clip_encoding_audit.py`, tests
`tests/unit/test_e22_short_clip_encoding.py` (11, every expectation derived by hand from the pinned
sources).

**Population: DEV ONLY.** The 6,038 ESB train-split utterances of the ten registered Earnings-22
dev subset10 calls and the 1,500-row `E22-DEV-ESB-1500-V1` subset of them. **The six ESB test calls
were not opened** (`test_split_read: false`): no test reference, output, segment row or derived clip
is read or reachable. No reference sentence and no hypothesis text was read at all — the only sealed
values opened are `usage.prompt_tokens` integers.

---

## 1. The path, layer by layer

Every line below is a citation, not a paraphrase. Sources: `llama.cpp-featcache` at build commit
`04ccc72a2207347ca76161b93fd9d846dd0a8675` (the commit
`docs/receipts/runtime-q4km-featcache-04ccc72a.json` pins and the one every sealed E22 dev arm was
served from; the checkout is detached at it and clean), read-only, never modified, never rebuilt,
never executed by this row.

| layer | file | what it does |
|---|---|---|
| the wire | `core/model/transport.py:295` | `base64.b64encode(media.read_bytes())` into an `input_audio` part with `format: "wav"`. **The study sends the sealed WAV bytes verbatim** — no resample, no trim, no normalization, no re-encode. |
| decode | `tools/mtmd/mtmd-helper.cpp:461` | miniaudio `ma_decoder_config_init(ma_format_f32, 1, target_sampler_rate)` at `mtmd_get_audio_sample_rate` = 16 kHz. Our clips are already 16 kHz mono int16, so this is a format cast, not a resample. |
| dispatch | `tools/mtmd/mtmd.cpp:684-686` | the mmproj declares `PROJECTOR_TYPE_QWEN3A` (`clip-impl.h:347`, `:401`), so the preprocessor is `mtmd_audio_preprocessor_qwen3a` and the markers are `<\|audio_start\|>` / `<\|audio_end\|>`. |
| hparams | `tools/mtmd/clip.cpp:1534-1556` | **hard-coded, not read from the GGUF**: `audio_sample_rate 16000`, `audio_n_fft 400`, `audio_window_len 400`, `audio_hop_len 160`. `n_mel_bins` is the one GGUF-sourced value (`clip.cpp:1200`, `clip.audio.num_mel_bins`; 128 for this model). `audio_chunk_len = 30` is set here **and never read by this preprocessor**. |
| framing | `tools/mtmd/mtmd-audio.cpp:653-667` | reflection pad of `n_fft/2 = 200` samples at each end, index for index the same as `torch.stft(center=True, pad_mode="reflect")`. |
| spectrogram | `tools/mtmd/mtmd-audio.cpp:669-681` | `log_mel_spectrogram` with `no_padding = true` and `use_natural_log = false`, then the whisper normalization `v -> (max(v, max-8)+4)/4` over the **whole clip**. |
| frame count | `tools/mtmd/mtmd-audio.cpp:687-690` | `n_eff = min(mel_full.n_len, n_samples/hop + 1)`. The clamp is inert: `log_mel_spectrogram` (`:443`) returns `(n_samples_padded - 400)/160 + 1 = n_samples/160 + 1` frames, the same number. |
| **the padding** | `tools/mtmd/mtmd-audio.cpp:706-727` | windows of `window_size = 800` frames; each window's effective length is rounded UP to a multiple of `chunk_size = 100` and `out.data.assign(n_mel * n_padded, 0.0f)` fills the remainder with **literal zeros**. `out.n_len_org` records the true length. |
| chunking | `tools/mtmd/mtmd.cpp:1300-1333` | **each window becomes its own `MTMD_INPUT_CHUNK_TYPE_AUDIO` chunk** — a separate encoder invocation, with no attention across windows. |
| tokens | `tools/mtmd/clip.cpp:3398-3403` | `n_patches = (img->nx() / 100) * 13` — 13 tokens per 100-frame block, **padded blocks included**. |
| the graph | `tools/mtmd/models/qwen3a.cpp:11-24, 63-70` | views the padded `[n_frames, n_mel]` tensor as `n_frames/100` chunks, asserts `n_frames % 100 == 0`, adds a per-chunk positional embedding that **resets 0..12 in every chunk**, and runs `build_vit` over all of them. **`n_len_org` is never read: there is no mask.** |

### 1.1 The three things this rules OUT

* **No fixed 30-second window.** The 30-second `stage_1_pad` lives in `log_mel_spectrogram`'s
  `else` branch (`mtmd-audio.cpp:399-407`) and `no_padding = true` skips it. `audio_chunk_len = 30`
  is only ever read by `mtmd_audio_preprocessor_whisper`, which Qwen3-Omni does not use.
* **No short-audio zero-fill.** `mtmd_audio_preprocessor_whisper` pads any input shorter than
  `sample_rate * (audio_chunk_len + 1)` = 31 s out to that length (`mtmd-audio.cpp:556-565`).
  Qwen3-Omni never enters that function, so a 0.22 s clip is *not* inflated to 31 s.
* **No re-encode, resample or trim anywhere between the WAV on disk and the mel.** The clips are
  16 kHz mono int16 by construction; miniaudio's target rate equals the file's.

---

## 2. A 3-second clip, and a 33-second clip

Both walkthroughs are in `summary.json`; both are reproduced by
`tests/unit/test_e22_short_clip_encoding.py` from hand arithmetic.

### 2.1 3.000 s — 48,000 samples

| step | value |
|---|---|
| reflection pad | 200 samples each end → 48,400 |
| mel frames, ours | `48000 // 160 + 1` = **301** |
| mel frames, published | `48000 // 160` = **300** |
| windows | one (`301 < 800`) |
| block rounding | `ceil(301/100) = 4` blocks → 400 frames |
| **zero-pad frames** | **99** (0.99 s), value **0.0** |
| the tail block | 1 real frame + 99 zeros, and it is charged 13 tokens |
| audio tokens, ours | 4 × 13 = **52** |
| audio tokens, published | 13 × 3 + `ceil(0/8)` = **39** |
| difference | **+13, a quarter of everything we send** |

### 2.2 33.000 s — 528,000 samples

| step | value |
|---|---|
| mel frames, ours / published | **3,301** / 3,300 |
| windows | **five**: 800, 800, 800, 800, 101 effective frames |
| padded to | 800, 800, 800, 800, **200** |
| zero-pad frames | 99, all in the last window |
| audio tokens per window | 104, 104, 104, 104, **26** |
| audio tokens, ours / published | **442** / 429 |
| difference | +13 — 2.9 % of the clip |

A 33-second clip is **five independent encoder invocations with no attention between them**, not
one 30-second window. That is a property of `n_window_infer = 800` and it is shared with the
published path (`modeling_qwen3_omni_moe.py:725`, `n_window_ratio = n_window_infer // (n_window*2)`),
so it is not a divergence — it is stated here only because "any fixed 30-s window" was the question.

### 2.3 The general rule

With `L = n_samples // 160` (the published frame count) and `r = L % 100`:

```
ours      = 13 * (L // 100 + 1)                 audio tokens
published = 13 * (L // 100) + ceil(r / 8)       audio tokens
extra     = 13 - ceil(r/8)                      in 0 .. 13
zero pad  = 99 - r frames  (0 when r == 99)     in 0 .. 99
```

`extra` is 13 exactly when the clip's duration is a whole number of seconds and 0 only when
`r >= 97`. The mean over the dev1500 is **6.49 tokens and 50.2 pad frames per clip**.

### 2.4 A correction to the study's own speech-token rule

This explains — and corrects — the `13 * ceil(audio_seconds)` rule the model fragments have used
since 2026-09-04 to fit the serving geometry. The exact rule is `13 * (n_samples // 16000 + 1)`, and
the two agree on every duration EXCEPT an exact whole number of seconds, where `ceil` returns the
duration itself and the extra mel frame nevertheless opens one more block.

**Those durations are not rare here, because the published `start_ts`/`end_ts` are quantized.**
`n_samples % 160` takes only **17 distinct values** across the 6,038 dev clips, 2,109 of them zero,
and **87 clips (1.44 %) have an exactly whole-second duration** — 1.0, 3.0, 4.0, 5.0, 9.0, 13.0,
14.0 s and so on. **25 of them are in the 1,500-row subset.** On those rows the old rule understates
the speech tokens by 13.

Nothing flown was affected and no number moves: the geometry fit is driven by the LONGEST clip
(`4470684-13`, 78.36 s, not an integer), whose 1,027 speech tokens both rules agree on, and the
understatement is 13 tokens against the 3,018-token margin the `-c 40960 -np 8` geometry carries. It
is recorded because a fit rule that is wrong on 1.4 % of a population should be right, and because
the corrected rule is what §5 of the preregistration sizes the `pad-30s` cell with.

---

## 3. The published path, from the installed source

`transformers` 5.12.1 as installed in `~/.venvs/speechrl` (read there, never from the network).

* **The processor's own audio defaults** (`processing_qwen3_omni_moe.py:98-102`):
  `{"sampling_rate": 16000, "padding": True, "truncation": False}`. `padding=True` is
  `PaddingStrategy.LONGEST`, so a single clip is **not** padded to 30 s either; a batch is padded to
  its longest member and the pad is recorded in `feature_attention_mask`
  (`processing_qwen3_omni_moe.py:157`).
* **The frame count** (`feature_extraction_whisper.py:149-150`):
  `torch.stft(waveform, 400, 160, window=hann(400))` — `center=True`, `pad_mode="reflect"` by
  default, the same reflection our path re-implements — then `magnitudes = stft[..., :-1]`. **The
  last STFT frame is dropped**, which is the one frame our path keeps.
* **The normalization** (`:155-161`): `log10`, `max(x, max-8)`, `(x+4)/4` — identical to ours.
* **The tail block** (`modeling_qwen3_omni_moe.py:643-675, 678-694`): `chunk_and_pad_features`
  splits into 100-frame chunks and right-pads the last one, but keeps `chunk_lengths` = the TRUE
  lengths; `get_valid_indices` then keeps only
  `_get_feat_extract_output_lengths(chunk_length)` positions per chunk. That function
  (`processing_qwen3_omni_moe.py:107-115`) is `13 * (n // 100) + ceil((n % 100) / 8)`; the identity
  is asserted at import time in `analysis/e22_short_clip_encoding.py` rather than trusted.

So the two paths agree on the filterbank, the window, the hop, the reflection and the
normalization, and they disagree on exactly two things: **one mel frame, and what happens to the
remainder of the last 100-frame block.**

---

## 4. What it costs, measured

### 4.1 Both dev populations

| | dev10 (6,038) | dev1500 (1,500) |
|---|---:|---:|
| audio seconds | 39,292.647 | 9,948.983 |
| audio tokens, ours | **550,992** | **139,282** |
| audio tokens, published | 511,614 | 129,542 |
| **padding-derived tokens** | **39,378 (7.15 %)** | **9,740 (6.99 %)** |
| zero-pad frames | 304,441 | 75,330 |
| zero-pad seconds | **3,044.4** | **753.3** |
| clips carrying a pad block | 6,032 of 6,038 | 1,498 of 1,500 |
| clips paying nothing extra | 104 | 36 |
| mean extra tokens per clip | 6.522 | 6.493 |
| mean padding share of a clip's tokens | 12.33 % | 12.00 % |
| worst clip's padding share | **76.9 %** (`4469088-654`, 0.2199 s: 13 tokens ours, 3 published) | **76.9 %** (the same clip) |
| clips spanning more than one encoder window | 1,898 | 701 |

### 4.2 By duration, on the 1,500 (the finding)

| bucket | clips | audio tokens | padding-derived | share | arm A WER (usage-cells §4.4) |
|---|---:|---:|---:|---:|---:|
| [0, 1) s | 116 | 1,508 | 636 | **42.18 %** | 74.007 |
| [1, 2) s | 109 | 2,834 | 709 | **25.02 %** | 42.086 |
| [2, 4) s | 291 | 13,351 | 1,842 | 13.80 % | 27.221 |
| [4, 8) s | 488 | 39,988 | 3,276 | 8.19 % | 20.217 |
| [8, 16) s | 425 | 62,894 | 2,816 | 4.48 % | 13.160 |
| [16, ∞) s | 71 | 18,707 | 461 | **2.46 %** | 9.536 |

The two right-hand columns are monotone together across every bucket. That is an association on six
points and it is reported as one — it is not a causal claim and this row makes none.

### 4.3 Per call, on the 1,500

| call | clips | audio seconds | tokens, ours | tokens, published | padding-derived | zero-pad frames |
|---|---:|---:|---:|---:|---:|---:|
| `4453225` | 150 | 1,029.128 | 14,378 | 13,400 | 978 | 7,578 |
| `4469088` | 150 | 738.174 | 10,569 | 9,617 | 952 | 7,364 |
| `4470684` | 150 | 1,134.753 | 15,743 | 14,769 | 974 | 7,495 |
| `4474506` | 150 | 1,028.465 | 14,352 | 13,388 | 964 | 7,443 |
| `4479944` | 150 | 931.988 | 13,156 | 12,135 | 1,021 | 7,882 |
| `4481952` | 150 | 803.967 | 11,427 | 10,470 | 957 | 7,390 |
| `4482383` | 150 | 1,055.644 | 14,716 | 13,748 | 968 | 7,520 |
| `4482613` | 150 | 1,029.089 | 14,404 | 13,406 | 998 | 7,775 |
| `4483937` | 150 | 1,052.708 | 14,651 | 13,704 | 947 | 7,305 |
| `4485192` | 150 | 1,145.067 | 15,886 | 14,905 | 981 | 7,578 |

No call is an outlier; the artifact is a property of the front end, not of a recording.

---

## 5. The proof: 6,038 sealed `prompt_tokens`

A transcription of someone else's C++ is a claim, so it is checked against the flight's own
tokenizer. For arm A the instruction is byte-identical on every row, so

```
prompt_tokens  -  (this audit's audio-token formula)  =  a constant text envelope
```

must hold on every row or the formula is wrong. Over **all 6,038 sealed rows of
`SAEA-E22-DEV-ESB-PROMPT-A-V1` (attempt `attempt-20260905T073641Z-f977d1`) there is exactly ONE
distinct envelope: 49 tokens** — the same 49-token envelope the 2026-09-05 fragments recorded from
the smoke. `build_receipts` refuses to write anything if there is more than one.

Only `usage.prompt_tokens` was read. No hypothesis text, no score, no reference.

---

## 6. The pad value, measured against real clips

Sixty clips, six per call, drawn at seed 20260907 from the 1,500, run through the **published
path's own numpy kernel** (`WhisperFeatureExtractor._np_extract_fbank_features`, 128 mel bins,
n_fft 400, hop 160) so the comparison is not against our own re-implementation. 6,325,183 PCM
samples were read from the sealed WAVs; none was sent anywhere.

| quantity, in normalized mel units | min | median | mean | max |
|---|---:|---:|---:|---:|
| clamp floor of a clip (`(max−4)/4`) | −1.1027 | **−0.7152** | −0.7282 | −0.4929 |
| clip's feature maximum | 0.8974 | 1.2848 | 1.2718 | 1.5071 |
| mean of the final ten REAL frames | −0.5094 | −0.1382 | −0.1664 | 0.1619 |
| **2.0 s of appended digital silence** | −1.1027 | **−0.7152** | −0.7281 | −0.4929 |
| share of a clip's real bins below `0.0` | 0.3647 | **0.6650** | 0.6643 | 0.9258 |

**The encoder's pad is `0.0`.** Digital silence is `−0.7152`. They are 0.72 apart on a scale whose
entire span is exactly 2.0, and two thirds of a clip's real mel bins sit below the pad. So the block
the encoder is handed after the last word is neither silence nor the room the speaker was in: it is
a flat, moderately energetic band across all 128 mel bins, for up to 0.99 s, immediately after
speech that was itself already fading (mean of the last ten real frames: −0.138).

That is the mechanism the three probes are designed to separate, and it is why
**`tail-silence-2s` is the sharpest of them**: appending digital silence provably produces the clamp
floor on these exact clips, so it replaces the discontinuity with the thing the model was trained to
read as an ending — without removing the pad block itself, which stays the same 99 − r frames and
simply stops abutting the speech.

---

## 7. What this licenses, and what it does not

**Answered.** *Does our path pad or chunk short audio differently from the published one?* **Yes**,
and the difference is priced: one extra mel frame, up to 99 frames of a non-silent constant, and up
to 13 audio tokens per clip that the published path never spends — 7 % of everything we send on
these rows and 42 % of what we send on a sub-second clip.

**Answered NO.** *Is there a fixed 30-second window, or a short-audio inflation, on our path?* No.
Both exist in `mtmd-audio.cpp` and both belong to the whisper preprocessor Qwen3-Omni does not use.

**Not answered, and not answerable model-free.** *Does any of this move the 7.076 WER points of
boundary insertion the 2026-09-06 clip-boundary audit attributed to the overlapping cut, or the
8.278 points of boundary block on the 1,500?* Nothing here is paired against anything; no
hypothesis was read. The three cells of
`docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md` are the measurement, and
each needs its own owner decision and its own exposure row.

**The one probe this audit's own finding implies and this row does NOT build.** All three
preregistered variants move the *acoustic* tail and leave the pad block's size untouched — by
arithmetic, since appending 2.0 s (200 frames) or padding to 30.0 s both leave `r` where it was or
set it to 0. A **frame-exact** variant — trim or extend each clip so that `n_samples // 160 + 1` is
a multiple of 100, at a cost of at most 0.99 s per clip — is the only cheap intervention that
removes the padded block entirely, and it would separate "the encoder sees a discontinuity" from
"the encoder sees 13 tokens of nothing". It is named here, specified in §5 of the preregistration,
and deliberately not built: it needs its own owner decision, and trimming audio is a second factor
where extending it is not.

---

## 8. Limits

* **The published path is read from transformers 5.12.1 as installed here.** Whatever version
  NVIDIA NeMo AutoModel used for the 9.79 is not established by anything in this repository, and a
  different version could handle the tail block differently. The comparison is to *this* installed
  source, named as such.
* **The pad-value probe is 60 clips, not 1,500**, and it uses the HF numpy kernel rather than the
  llama.cpp one. The two agree on the filterbank design and the normalization by inspection, not by
  a numerical comparison — no llama.cpp binary was run, so no bit-level agreement is claimed. What
  is claimed is a distributional statement about where `0.0` sits, and 60 clips over ten calls is
  enough for that and is not enough for a per-clip statement.
* **The token arithmetic is exact; the WER association in §4.2 is six points.** The monotone
  agreement between padding share and arm A WER across duration buckets is confounded with the
  denominator effect the usage-cells verdict already named (a short clip has few reference words, so
  every error costs more). Nothing here disentangles them.
* **`n_mel_bins` was not read out of the GGUF.** It is the one hparam the code takes from the file
  (`clip.audio.num_mel_bins`), and 128 is taken from the model's published configuration rather than
  from a header read. Nothing in this audit's arithmetic depends on it: the frame, block, window and
  token counts are all independent of the mel-bin count.
* **This is dev only, and it is an encoding fact, not an alignment argument.** The 2026-09-06
  array-durations verdict made the boundary claim rule unconditional; nothing here lifts it, and no
  number in this document may be compared to the published 9.79 or 12.3.
