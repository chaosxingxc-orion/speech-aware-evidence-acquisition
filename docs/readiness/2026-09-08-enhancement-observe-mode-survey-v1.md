# Speech enhancement as an observe mode: does the data support it, and what could we deploy

**Status: SURVEY, model-free, NO CELL REGISTERED, nothing authorized.** Owner Decision 12-H of
2026-09-08 ("for speech enhancement as an observe mode, first check whether the datasets and tasks
support it, and survey the latest, strongest locally deployable enhancement models; no experiment
before that"). Row `SAEA-MF-ENHANCEMENT-SURVEY-V1`, profile `model-free-check`. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-enhancement-survey/`
(`summary.json`, three per-row CSVs, `MANIFEST.sha256`). Runner:
`scripts/run_enhancement_survey.py`.

**Zero model, GPU, tokenizer, embedder, retriever, network and paid-API contacts; zero audio
seconds delivered to any service; no enhancement model downloaded, installed, loaded or run.**
Section 3 of this note was written **with no network access at all**: every claim about an external
model or paper is labelled *from training knowledge, to verify*, carries the name and the date I
believe it appeared, and gives a range or "not recalled" instead of a number I cannot stand behind.

---

## 0. The answer, before the evidence

1. **The testbed the design note names does not exist.** Section 7 of
   `docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md` puts enhancement in the
   Observer's tool table with "testbed = the Audio2Tool noisy tier". **Audio2Tool has no noisy
   tier.** It ships eight tiers, all clean-recorded synthesis over open speaker corpora, with no
   additive noise, no SNR field, and no `{clean, noisy}` variant of anything. The tier that reads
   as "noisy" — `tier8_intent_blending` — is not noise: it is a **second intelligible utterance
   carrying a competing tool intent that the model is required to ignore**. Removing it is target
   selection, not denoising, and the corpus ships no isolated foreground rendition to enhance
   towards or to score against.
2. **The one carrier that does support the question is SLURP, and it answers it against
   enhancement.** A SLURP real recording session writes two files under one recording id — a
   close-talk `-headset.flac` and a far-field `.flac` of the same utterance by the same speaker —
   and the sealed DEV-1000 roster already mixes them, 522 far-field to 478 headset, chosen at
   random per utterance. The acoustic gap between the two
   channels is enormous: **26.6 dB of noise floor and 24.1 dB of speech-to-floor margin at the
   median**. The task gap is **0.09 pp of intent** (CI90 [−5.20, +5.29]) and **2.54 pp of SLU-F1**
   (CI90 [−2.45, +7.45]) on the 766 utterances where the channel assignment was a coin flip.
   A perfect enhancer — one that turned every far-field row into its own headset twin — would buy
   at most **+0.05 pp of intent and +1.33 pp of SLU-F1** on the whole roster, both with intervals
   that contain zero.
3. **Nothing is pinned and nothing is local.** The umbrella lock holds nine model entries and not
   one is an enhancer; `SPEECHRL_DATA_DIR/models/` holds 29 directories and not one is an enhancer.
   A bring-up is therefore a download, an install, a hash pin, a derivation record and a byte
   check — real cost, against a measured ceiling of roughly one SLU-F1 point whose interval
   contains zero.

**The recommendation this note ends on: do not bring an enhancer up for score.** If the owner
wants one anyway, section 3.3 names exactly two, ranked, with the verification steps, and section 4
prices the cell — including the falsifier that would catch the failure mode that actually worries
me, which is not that enhancement fails to help but that it **hurts the frozen core's encoder on
audio that needed nothing done to it**.

---

## 1. Task support, from sealed data

Every figure in this section is either read from a committed receipt or computed by the runner from
sealed bytes. The acoustic statistic is one number and it is crude on purpose:

> **speech-to-floor margin** = the median level of the frames `analysis.e22_clip_boundary`'s
> committed 20 ms energy gate calls active, minus the 10th-percentile frame level of the same clip,
> at that module's own `FRAME_MS=20` / `PEAK_DROP_DB=30` / `ABSOLUTE_FLOOR_DBFS=-55`.

It is **not an SNR**. A true SNR needs a clean reference of the same audio and **no carrier in this
study has one** — which is itself half the finding. The margin ranks conditions: speech well above
a quiet floor scores high, a far-field room or a competing talker filling the gaps scores low.

### 1.1 Audio2Tool — no clean/noisy pair exists, and the one degraded tier is already aligned

**How the corpus was built, per its own card** (`<asset root>/datasets/audio2tool/README.md`,
v1.0, CC-BY-NC-4.0, Rivian & Volkswagen Technologies): 16,843 queries across `smart_home`,
`wearables` and `smart_car`, voiced by TTS conditioned on reference speech from VoxPopuli,
3D-Speaker, ECAPA and YODAS. **The card describes no noise addition of any kind.** There is no
noise type, no SNR column, no room impulse response, no `clean`/`noisy` split, and no per-item
condition field. The only degradation the card documents is tier 8's construction: "`path` points
at a single `mixed.wav` that contains a foreground utterance overlapped with a background one",
with the background's own `background_tool_id` / `background_tool_call` / `background_query`
recorded because the model must **ignore** it.

**Two corpus facts the read establishes and the card gets wrong or leaves out.**

* **All 400 frozen-discovery wavs are 24 kHz**, measured from their own headers through
  `data.audio2tool.load_media_rows`. The card says "All audio is **16 kHz** mono WAV". The card is
  wrong, the 2026-09-07 input-rate audit was right, and llama.cpp's miniaudio linear resampler is
  what converts them (`docs/readiness/2026-09-07-a2t-input-rate-audit-v1.md`).
* Tier 8 is the **longest single-file tier after tier 5** — median 6.20 s against 2.04 s on tier 1
  — because it carries two utterances at once.

**The sealed task numbers, official scorer `a2t-toolcall-official`, n = 500 per tier**
(read from the three official-population verdicts of 2026-09-04, never recomputed):

| tier | ours | CI90 | paper | outcome | `smart_home` | `wearables` | wearables − smart_home |
|---|---:|---|---:|---|---:|---:|---:|
| `tier1_direct` | 65.60 | [62.03, 69.00] | 92.4 | FAIL | 55.71 | 93.41 | **37.70** |
| `tier2_parametric` | 79.60 | [76.48, 82.40] | 84.6 | FAIL | 74.59 | 95.37 | 20.78 |
| `tier3_multi_intent` | 65.00 | [61.42, 68.42] | 74.7 | FAIL | 59.51 | 79.12 | 19.61 |
| `tier4_implicit` | 28.20 | [25.01, 31.62] | 33.4 | FAIL | 21.60 | 55.56 | 33.96 |
| `tier5_needle` | 80.80 | [77.74, 83.53] | 90.6 | FAIL | 75.00 | 96.70 | 21.70 |
| `tier6_correction` | 75.80 | [72.52, 78.81] | 81.5 | FAIL | 70.11 | 93.41 | 23.30 |
| `tier7_multiturn` | 49.40 | [45.74, 53.07] | 54.6 | FAIL | 42.63 | 77.38 | 34.75 |
| **`tier8_intent_blending`** | **46.80** | [43.16, 50.48] | **41.7** | **ALIGNED** | 29.74 | 58.77 | **29.02** |

**The acoustic signature, frozen 400, 50 rows per tier** (medians; full per-row table in the
receipt's `a2t-frozen400-acoustics.csv`):

| tier | median s | peak dBFS | active share | floor dBFS | **margin dB** | share below −55 dBFS |
|---|---:|---:|---:|---:|---:|---:|
| `tier1_direct` | 2.04 | −13.85 | 0.745 | −60.12 | **31.41** | 0.155 |
| `tier2_parametric` | 3.12 | −14.90 | 0.807 | −53.25 | 26.45 | 0.093 |
| `tier3_multi_intent` | 4.88 | −13.67 | 0.833 | −50.30 | 22.93 | 0.069 |
| `tier4_implicit` | 2.52 | −16.09 | 0.829 | −52.01 | 26.19 | 0.080 |
| `tier5_needle` | 11.16 | −14.24 | 0.830 | −55.54 | 26.47 | 0.104 |
| `tier6_correction` | 5.05 | −12.15 | 0.800 | −54.38 | 28.36 | 0.095 |
| `tier7_multiturn` | 4.48 | −17.59 | 0.781 | −57.56 | 27.71 | 0.131 |
| **`tier8_intent_blending`** | 6.20 | −12.31 | **0.912** | **−42.60** | **17.80** | **0.017** |

Tier 8 is measurably the degraded one and it is degraded in exactly the way a second talker
degrades a signal: the **floor rises 8–18 dB**, the margin **collapses to 17.8 dB**, the active
share climbs to 0.912 and the share of frames below the absolute floor falls to 0.017 — the gaps
between the foreground's words are filled by the background's words rather than by silence.

**And that is precisely why a denoiser cannot help here.** What fills the gaps is intelligible
speech carrying a competing tool intent. A single-channel denoiser has no cue for which of two
talkers is the target; a separator would emit two streams and the loop would still have to choose,
which is the task itself, not a preprocessing step for it.

**The decisive number is the last column of the task table.** The device-domain gap —
`wearables` minus `smart_home` tool accuracy — is **19.6 to 37.7 pp on every one of the seven clean
tiers**, with a median of 23.3, and tier 8's is **29.0**, sitting in the middle of that range. The
same failure that costs 37.7 pp on tier 1, where there is no background talker at all, costs 29.0
pp on tier 8. **The dominant error axis on Audio2Tool is device-domain disambiguation across a
152-tool registry with three near-duplicate capability sets** (named in the calibration verdict's
addendum A4), not the acoustic condition.

**Headroom and ceiling.** Tier 8 is 500 of the 4,000 flown union rows (12.5 %). Since no isolated
foreground rendition exists, *"the degraded rows scored as if clean"* **cannot be computed on this
corpus** — only bounded. The bound: scoring **every** tier-8 row perfectly would add **6.65 pp** to
the union's natural-mixture accuracy. That is arithmetic, not a target, and it is not reachable:
tier 8 is the single tier this repository has ever landed ALIGNED, **5.1 points above** the
published row.

### 1.2 SLURP — the only real clean/degraded pair in the study, and it says no

**The structure.** A SLURP real recording session writes two files under one recording id:
`audio-<id>-headset.flac`, the close-talk headset channel, and `audio-<id>.flac`, the far-field
channel. The governed metadata lists both as `recordings[]` of the **same** `slurp_id` — same
sentence, same speaker session — and both are 16 kHz mono FLAC. That is a genuine paired
clean/degraded design and it is the only one in the locked carrier set.

**One property of the pair, measured rather than assumed, because it constrains what can be done
with it.** The two files are **not frame aligned**: the absolute difference in their durations has
a median of **0.06 s**, p90 **0.46 s** and a maximum of **3.52 s**; only 27.4 % of pairs agree to
within 20 ms and 67.6 % to within 100 ms. They are separately trimmed renditions of one utterance,
not two views of one byte-aligned capture window. **A study can therefore pair them by utterance
and never by sample** — which is enough for a paired task-score contrast, and not enough to use the
headset file as a supervised enhancement target. Whether the far-field channel was captured
simultaneously or separately is a corpus-design fact I could not check offline; *to verify*.

**What the roster already does with it.** DEV-1000's own selection rule resolves one recording per
selected utterance with `random.Random(f'{seed}:{scenario}:{utterance_id}')` over that utterance's
id-sorted recordings. So the flown roster is **522 far-field and 478 headset**, and on the subset
where both files exist the channel is a **randomized assignment**, not a confound the analyst
chose. 766 of the 1,000 utterances have both (390 flown far-field, 376 flown headset); 234 sessions
carry only one channel (132 flown far-field, 102 flown headset) and are excluded from the
randomized contrast.

**The acoustic gap, both files of all 766 utterances** (medians, then [p10, p90]):

| statistic | headset | far-field | headset − far-field |
|---|---:|---:|---|
| peak dBFS | −10.85 | −9.94 | −1.11 [−3.50, +1.25] |
| **floor dBFS** | **−61.51** | **−32.53** | **−26.62 [−66.11, −12.38]** |
| active share | 0.71 | **1.00** | −0.24 [−0.44, −0.08] |
| **speech-to-floor margin dB** | **36.23** | **8.81** | **+24.08 [+9.65, +67.60]** |

The far-field channel's median active share is **exactly 1.000**: under a peak−30 dB gate, *every*
20 ms frame is active, which is what a room whose noise floor sits within 30 dB of the talker looks
like. By any acoustic reading these are two very different conditions, and the far-field one is
squarely the kind of input an enhancer is built for.

**The task gap, sealed comparator `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, scored through the
locked `slurp-slu-official-projected-v2`.** The read first reproduces the comparator's own
published figures from its sealed bytes — **intent 71.40 unprojected, 73.10 projected-v2, SLU-F1
35.80** — and only then splits them (`identity_check_passed: true`).

| population | channel | n | intent (v2) | intent (raw) | SLU-F1 |
|---|---|---:|---:|---:|---:|
| all 1,000 | far-field | 522 | 73.56 | 72.41 | 35.47 |
| all 1,000 | headset | 478 | 72.59 | 70.29 | 36.16 |
| all 1,000 | pooled | 1000 | **73.10** | **71.40** | **35.80** |
| twin available | far-field | 390 | 73.85 | 72.31 | 33.45 |
| twin available | headset | 376 | 73.94 | 72.34 | 35.99 |
| twin available | pooled | 766 | 73.89 | 72.32 | 34.75 |

**far-field minus headset**, unpaired percentile bootstrap, 10,000 replicates, seed 20260908,
CI90 — reported as a *headroom observation*, never as an admission contrast, because the two
channels carry different utterances:

| population | intent (v2) | intent (raw) | SLU-F1 |
|---|---|---|---|
| all 1,000 | +0.97 [−3.63, +5.59] | +2.12 [−2.53, +6.88] | −0.69 [−4.94, +3.72] |
| **twin available (randomized)** | **−0.09 [−5.29, +5.20]** | −0.03 [−5.30, +5.43] | **−2.54 [−7.45, +2.45]** |

**Read it plainly.** A 26.6 dB difference in noise floor and a 24.1 dB difference in speech-to-floor
margin move intent accuracy by **0.09 points in the headset's favour** and SLU-F1 by **2.54 points
in the headset's favour**, and both intervals contain zero. On the full roster the intent
difference even points the *other* way. The frozen core is, on this evidence, close to indifferent
to the SLURP channel.

**The ceiling, priced.** A perfect enhancer that turned every far-field row into its own headset
twin would buy, on the whole DEV-1000 roster, at most
**52.2 % × 0.09 = +0.05 pp of intent** and **52.2 % × 2.54 = +1.33 pp of SLU-F1**, with the
upper CI90 bound of the SLU-F1 half at **+3.89 pp**. And it is worth naming what the roster can
actually resolve: the CI half-width on the randomized contrast is about **±5 pp**, so a real effect
smaller than that is invisible at DEV-1000 no matter how good the enhancer is.

**One corroborating signal this read deliberately did not open.** The governed SLURP metadata
carries, per recording, the corpus authors' own quality-control fields `wer`, `ent_wer` and
`status`. If far-field recordings carry systematically higher `wer` there, it would say the channel
IS harder for a conventional recognizer while being ~free for this frozen core's SLU — a sharper
version of the finding above. `data.slurp` deliberately does not expose those fields, so reading
them means adding a registered reader; that is a named next step, not something to reach past the
loader for.

**One caveat that is mine to state and not to hide.** The channel contrast is between different
utterances. Randomized assignment makes it unbiased in expectation, but a *paired* answer is
available and cheap in principle — the 766 twins are already on disk and were never flown. Section
4 turns that into the cell design that would actually settle it, if the owner wants it settled.

### 1.3 Earnings-21 and Earnings-22 — no clean counterpart exists at all

**Sample rates**, from the carriers' own metadata through `data.loader.load_earnings21` /
`load_earnings22`:

| carrier | files | hours | 8 k | 11.025 k | 16 k | 22.05 k | 24 k | 32 k | 44.1 k | 48 k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `earnings21-original` | 44 | 39.26 | — | 5 | 6 | 5 | 21 | — | 7 | — |
| `earnings22-original` | 125 | 118.89 | 1 | 5 | 29 | 17 | 64 | 1 | 7 | 1 |

**"Telephone-band" does not describe these carriers.** Exactly **one of 169 files is 8 kHz**; ten
are 11.025 kHz; the modal rate is 24 kHz and 15 files are 44.1 kHz or above. What the table shows
is **heterogeneity**, and heterogeneity is a resampling and bandwidth question — already owned by
the input-rate work and by `reproduction.obs_loop.decode_parent_pcm`'s `librosa soxr_hq` path — not
a denoising one.

**Acoustics, Earnings-21**, seeded 132-slice sample (3 per call over the 44 discovery calls,
seed 20260908) of the **sealed** 90-second obs-slices of `SAEA-E21-FULL44-DIRECT-BASELINE-V2`:
peak dBFS median −10.77 [p10 −20.77, p90 −4.32]; active share median 0.669; floor dBFS median
−62.18; **speech-to-floor margin median 35.81 dB [p10 22.59, p90 47.38]**. That is a margin as
large as SLURP's *headset* channel. These are conference-call recordings of prepared corporate
speech, not noisy field audio. (The margin's long upper tail is an artefact of digital-silence
frames inside some slices — floor values down to −240 dBFS — so the median and p10 are the
informative statistics, not the max.)

**Acoustics, Earnings-22 ESB clips**, from the committed per-clip table of the 2026-09-06
clip-boundary audit, 6,038 DEV-10 clips: peak dBFS median −15.46 [p10 −27.44, p90 −9.25]; active
share median 0.759 [p10 0.477, p90 0.924]; leading silence median 0.04 s; trailing silence median
0.00 s. That table carries no per-clip floor, so no margin is computed for it and none is invented.

**And the finding that already settled what "noise" means on Earnings-22 is not acoustic at all.**
The 2026-09-06 semantic error scan found that **47.6 % of the E22 error mass is clip-boundary
bleed** — a neighbour's *speech*, admitted by the cut, whose named fix is boundary-exact clips
(the B2a probe). The 2026-09-07 short-clip encoding audit found the second candidate root cause in
llama.cpp's mel padding, also not acoustic. **Both of Earnings-22's measured damage channels are
segmentation and encoding, and a denoiser addresses neither.**

**Ceiling: none computable.** Neither Earnings carrier ships a second channel or a clean rendition
of the same audio, so there is no clean-versus-degraded contrast and no "scored as if clean"
ceiling on either.

### 1.4 The headroom table

| carrier | degraded condition | clean counterpart? | share | measured task gap | ceiling for a perfect enhancer | verdict |
|---|---|---|---:|---|---|---|
| **Audio2Tool** | `tier8_intent_blending`: a competing intelligible utterance mixed into the same wav | **No.** One `mixed.wav` per item; no isolated foreground rendition | 500 / 4,000 = 12.5 % | not computable — no clean rows to contrast | **not computable**; unreachable arithmetic bound +6.65 pp on the union | **NO TARGET.** The degradation is competing speech, not noise; tier 8 is the one ALIGNED tier (46.80 vs 41.7); its device-domain gap (29.0 pp) is mid-range among the seven clean tiers (19.6–37.7) |
| **SLURP** | far-field channel against its own simultaneous headset twin | **Yes** — a true paired design, 766 of 1,000 DEV utterances | 522 / 1,000 = 52.2 % | intent −0.09 pp [−5.29, +5.20]; SLU-F1 −2.54 pp [−7.45, +2.45] on the randomized 766 | **+0.05 pp intent, +1.33 pp SLU-F1** (upper CI90 +3.89) | **TARGET EXISTS BUT IS ~ZERO.** A 26.6 dB floor gap buys ≤ 1 SLU-F1 point, interval contains zero; roster resolution is ±5 pp |
| **Earnings-21** | none identifiable | **No.** Single channel, no clean rendition | — | — | **not computable** | **NO TARGET.** Margin 35.8 dB, as clean as SLURP headset; the open damage channels are entity naming and unit segmentation |
| **Earnings-22 / ESB clips** | none acoustic | **No.** | — | — | **not computable** | **NO TARGET.** 47.6 % of error mass is clip-boundary bleed (a cut, fixed by boundary-exact clips); the other named candidate is mel padding |

---

## 2. What is on this machine today

**Nothing.** Read by the runner, not asserted:

* The umbrella lock's `models` section holds **nine** entries — `qwen3-omni-30b-a3b-instruct-gguf`,
  `qwen3-omni-30b-a3b-instruct-gguf-q4km`, `nemotron3-nano-omni-nvfp4`, `omni-embed-nemotron-3b`,
  `mms-fa-torchaudio`, `spkrec-ecapa-voxceleb`, `diar-sortformer-4spk-v2`,
  `qwen3-embedding-0.6b-gguf`, `whisper-large-v3`. **Zero** match any enhancement, denoising,
  dereverberation or separation marker.
* `SPEECHRL_DATA_DIR/models/` holds **29** directories (omni cores, embedders, speaker and emotion
  encoders, a diarizer, Whisper, speech tools). **Zero** match.
* The only "noise" strings anywhere in the lock belong to Spoken-SQuAD's *ASR-noise* framing and to
  a THCHS-30 `test-noise.tgz` archive. Neither is a locked carrier and both are out of scope.

**What the shared WSL venv already has**, which matters for what a bring-up would cost:
`torch 2.9.1+cu128`, `torchaudio 2.9.1+cu128`, `speechbrain 1.1.0`, `transformers 5.12.1`,
`huggingface_hub 1.20.1`, `numpy 2.2.6`, `soundfile 0.14.0`, `librosa 0.11.0`, `scipy 1.17.1`.
**`onnxruntime` is absent. `ffmpeg` is absent and is pinned absent** — every `buf90` slice in this
study was cut through the librosa fallback and installing ffmpeg would change bytes and cold the
26 GB feature cache. **Any candidate whose audio I/O needs ffmpeg is disqualified as written and
must be driven through `soundfile` instead.**

---

## 3. Candidate enhancers — from training knowledge, with no network

**Read this section as testimony, not as a citation list.** I had no network access. Every row is
what I recall, with a confidence label; nothing here has been verified against a page, a repository
or a weight file, and no number appears that I cannot bound honestly. A future agent with network
access must verify every cell before any of it is pinned.

### 3.1 The table

Columns: **Y** = year I believe it appeared; **SR** = native sample rate; **RT** = real-time capable
on CPU; **venv** = whether it runs in this rig's WSL venv with no *system* package added (a pip
install into an isolated venv is still required and is never done by an agent in the shared one);
**ASR effect** = what I recall about its effect downstream; **Conf** = my confidence in the row.

| model / family | Y | license | size | SR | RT | framework | venv | known ASR/SLU effect | Conf |
|---|---:|---|---|---|---|---|---|---|---|
| **DeepFilterNet 2 / 3** (Schröter et al.) | 2022 / 2023 | permissive, I believe MIT or Apache-2.0 — **to verify** | very small, low single-digit millions of parameters | 48 k full-band | **yes**, designed for it | PyTorch + a Rust core (`libdf`); ONNX export exists | pip install into an isolated venv; **`onnxruntime` absent** so the torch path is the one available | mixed: helps at low SNR, **often neutral-to-harmful on already-clean speech** — to verify | **HIGH** on existence and character; MEDIUM on license/size |
| **`denoiser` / Demucs-for-speech** (Défossez et al., "Real Time Speech Enhancement in the Waveform Domain") | 2020 | MIT — to verify | small causal U-Net (DNS48/64, master64) | 16 k | yes | PyTorch | isolated venv; audio I/O must be forced through `soundfile`, **not** ffmpeg | the paper's own framing is perceptual; artefact-driven ASR degradation is the standard caveat — to verify | **HIGH** on existence; MEDIUM on details |
| **htdemucs / Hybrid Transformer Demucs** (Meta) | ICASSP 2023 | MIT — to verify | tens of millions | 44.1 k | no (offline) | PyTorch | isolated venv; ffmpeg-dependent as usually packaged | **music source separation, not speech enhancement**; recorded in the umbrella archive as a *separation* tool in a related agentic pipeline | **HIGH** that it exists and is separation |
| **SpeechBrain `metricgan-plus-voicebank`** (Fu et al., MetricGAN+) | 2021 | Apache-2.0 — to verify | small | 16 k | near | PyTorch via `speechbrain` | **`speechbrain 1.1.0` is already installed**; needs only a weights download | optimizes PESQ directly; **PESQ gains are known not to transfer to WER** — to verify | **HIGH** on existence; MEDIUM on numbers |
| **SpeechBrain `sepformer-*` (wsj0-2mix / WHAM! / WHAMR!)** (Subakan et al.) | 2021 | Apache-2.0 — to verify | ~26 M, transformer, heavy | 8 k / 16 k variants | no | PyTorch via `speechbrain` | as above | **separation, not denoising**; emits N streams and needs a selection rule the loop does not have | **HIGH** |
| **NVIDIA CleanUNet / CleanUNet 2** (Kong et al.) | ICASSP 2022 / ~2023 | NVIDIA source-code licence, **non-commercial terms likely** — to verify | tens of millions | 16 k | no | PyTorch | isolated venv | not recalled | MEDIUM |
| **NSNet2 and the DNS-Challenge baselines** (Microsoft) | 2020–2021 | MIT — to verify | tiny | 16 k | yes | ONNX | **needs `onnxruntime`, which is absent** | baseline-grade; superseded | MEDIUM |
| **FullSubNet / FullSubNet+** | 2021 / 2022 | open, licence not recalled | ~5–10 M | 16 k | near | PyTorch | isolated venv | not recalled | MEDIUM |
| **GTCRN** | ICASSP 2024 | MIT — to verify | ultra-light, I recall ~30–50 k parameters | 16 k | yes | PyTorch / ONNX | isolated venv | not recalled | MEDIUM |
| **MP-SENet** (magnitude–phase, Lu et al.) | 2023 | open, licence not recalled | tens of millions | 16 k | no | PyTorch | isolated venv | strong on VoiceBank+DEMAND perceptual metrics; downstream ASR not recalled | MEDIUM |
| **SEMamba** (state-space enhancement) | 2024 | open — to verify | tens of millions | 16 k | no | PyTorch (Mamba kernels) | isolated venv; **custom CUDA kernels are a real bring-up risk** | not recalled | MEDIUM-LOW |
| **SGMSE / SGMSE+ / StoRM** (Richter, Welker, Lemercier, Lay, Gerkmann) | TASLP 2023 | open, I believe MIT — to verify | tens of millions | 16 k | **no**, diffusion, many reverse steps | PyTorch | isolated venv; **GPU-bound, and the GPU is contested** | **generative**: strong on dereverberation, and generative enhancers are the ones most likely to *hallucinate* phonetic content | MEDIUM |
| **ClearerVoice-Studio** (Alibaba: FRCRN, MossFormer2-SE-48K, super-resolution) | ~2024–2025 | Apache-2.0 — to verify | tens of millions | 16 k / 48 k | no | PyTorch + ModelScope/HF | isolated venv; extra SDK dependencies | not recalled | MEDIUM |
| **VoiceFixer**, **Resemble Enhance** | 2021–2023 | open — to verify | tens of millions | 44.1 k | no | PyTorch | isolated venv | **restoration/generative — known to alter content**; wrong tool where transcript fidelity is scored | MEDIUM |
| **Miipher / Miipher-2** (Google) | 2024 / 2025 | **weights not released, to my recollection** | — | — | — | — | **not deployable locally** | — | LOW-MEDIUM |
| 2025–2026 successors | — | — | — | — | — | — | — | — | **I cannot name a 2025–2026 speech-enhancement model with the confidence this table requires.** I recall a shift toward flow-matching and generative unified enhancement (names like *AnyEnhance*, *FlowSE*, Schrödinger-bridge enhancement) but not their numbers, licences or weight availability. Treat the frontier as **unsurveyed** until a networked agent checks it |

**Already local: none.** Expected, and confirmed by measurement in section 2.

### 3.2 The downstream risk is the headline, not a footnote

This is the part of the survey I hold with the most confidence, and it argues against the whole
idea on this data:

* **Single-channel enhancement front-ends routinely HURT ASR** when the recognizer was trained on
  multi-condition (i.e. unenhanced) audio. The mechanism is *processing artefacts*: the enhanced
  signal is out of the recognizer's training distribution in a way the noisy signal is not. I recall
  the CHiME-series experience and, specifically, **Iwamoto et al., "How bad are artifacts?:
  Analyzing the impact of speech enhancement errors on ASR" (Interspeech 2022)**, which decomposes
  the enhanced signal into target / residual-noise / artefact components and attributes the ASR
  degradation mainly to the **artefact** term. *From training knowledge, to verify; I do not recall
  its WER figures and will not invent them.*
* The corollary in the ESPnet-SE / joint-training literature is that enhancement helps downstream
  **when the front end and the recognizer are trained or fine-tuned together**. This study cannot
  do that: the core is frozen and reached across an API-shaped boundary, and zero-parameter training
  is a charter invariant. **We are structurally in the regime where enhancement is known to be
  risky.** *To verify.*
* For **Whisper-family and omni encoders** specifically, I recall reports from roughly 2023–2024
  that denoiser front ends (DeepFilterNet, Demucs-family) give little or no WER gain and can worsen
  it at moderate SNR, helping only at genuinely low SNR. *To verify; I do not recall the papers'
  identifiers.*
* **Generative restorers are worse for this purpose than discriminative denoisers**, because they
  can synthesise plausible phonetic content that was never spoken. On tasks scored by transcript or
  by slot filler, that is a wrong-answer generator.

**Applied here:** section 1 says the far-field SLURP rows lose at most ~1 SLU-F1 point to their
channel, and section 3.2 says an enhancer's artefacts are a plausible several-point cost on rows
that needed nothing. **The expected sign of this intervention on this data is negative.**

### 3.3 The two to bring up, if any — ranked, with the exact verification steps

**Rank 0 — the honest recommendation: bring up none for score.** The measured ceiling does not pay
for a pinned dependency, a derivation record, a media build and a flight.

If the owner overrides that, exactly two, in this order:

**(1) DeepFilterNet 3 — the low-risk discriminative denoiser.** Smallest, fastest, CPU-only,
permissively licensed, purpose-built for real-time single-channel noise suppression with light
dereverberation, and the least likely of the list to invent content. Use it on the **SLURP
far-field channel**, which is the only condition in the study it is the right tool for.

**Its one structural problem, named now rather than discovered later: it is a 48 kHz full-band
model and SLURP is 16 kHz.** Running it means 16 k → 48 k → enhance → 48 k → 16 k, so **two
resampling passes ride along with the enhancement** and the cell would no longer be moving one
factor. Three ways out, in order of preference: (a) add a **resample-only control** — the same
round trip with the enhancer switched off — as a third twin, which isolates the resampling from
the enhancement and is cheap (section 4.3); (b) use a **16 kHz-native** denoiser instead, for which
the candidates I would name are `denoiser`'s DNS64/master64 or **GTCRN**, both 16 kHz by
construction, at the cost of taking a weaker model; (c) drop the mode. Option (a) is the one I
would take, because it keeps the strongest candidate and prices the confound instead of hiding it.
The same problem does not arise on Audio2Tool for the opposite reason — its release wavs are
24 kHz and are already being resampled inside llama.cpp by the lowest-quality path (section 1.1),
which makes any enhancement there a **two-resampler interaction** nobody has measured.

**(2) SpeechBrain `sepformer-whamr16k` (or `sepformer-wham16k-enhancement`) — diagnostic only.**
Justified solely because `speechbrain 1.1.0` is **already in the venv**, so the bring-up is a
weights download and nothing else. It is a **separator**, and on Audio2Tool tier 8 it would emit two
streams with no cue for which one is the foreground — so it can serve as a *diagnostic* of how much
of tier 8's loss is recoverable in principle (e.g. by scoring both streams and taking the oracle
best), never as an observe mode. **An oracle-best read is a ceiling measurement and must be
labelled one; it is not a mechanism.**

**Verification steps a future agent must run, in order, before either is used for anything:**

1. **Licence and provenance, on the record.** Fetch the repository and the model card; record the
   licence text verbatim, the upstream commit, and the release tag. **Non-commercial terms are a
   blocker to name explicitly** rather than to discover later.
2. **Isolated environment.** Create a **new** venv (`~/.venvs/saea-enhance`), never the shared
   `speechrl` one — an install into the shared venv has repointed it before, and the launch scripts
   carry `PYTHONPATH=$REPO/src` armour precisely because of that. Record `pip freeze`.
3. **Hash pin.** SHA-256 every weight file and every config; add an umbrella lock entry with
   `local_subdir`, revision and per-file hashes, exactly as the charter's frozen tool-level clause
   requires ("a tool is admitted only pinned and logged"). Land a runtime receipt naming the
   library version and the weight hashes.
4. **Determinism.** Run the enhancer twice over the same four inputs with the same seed and assert
   **byte-identical** outputs. A non-deterministic enhancer cannot leave a reproducible derivation
   record and must be refused at this step.
5. **The 4-row byte check.** Take four SLURP DEV-1000 far-field rows. Enhance them. Assert: the
   output is 16 kHz mono PCM_16 with the **same sample count** as the input (no trim, no pad, no
   resample); the derivation record's `pre_sha256` chains to the sealed input's hash; the
   `post_sha256` matches the emitted bytes; `audio_seconds` is unchanged; the media stays inside the
   derived-media confinement the 2026-09-07 note fixed. **Any length change is a defect, not a
   feature** — it would move every downstream frame and confound the cell.
6. **The pass-through twin, and the resample-only twin.** Run the same path with the enhancer
   replaced by the identity transform and assert the emitted bytes equal the sealed input bytes
   exactly. Then, for any enhancer whose native rate is not the carrier's, run the **round trip
   with the enhancer switched off** (16 k → its rate → 16 k) and keep those bytes as a second
   control. The first proves the plumbing changes nothing; the second separates the resampling from
   the enhancement, which is the only way a 48 kHz model can be a single-factor change on a 16 kHz
   carrier.
7. **The clean-side falsifier first** (section 4.5). Do not spend the degraded-side contacts until
   the clean-side one has been read.

---

## 4. The admission design, priced — NOT preregistered

Written so the owner can price the decision. **Nothing in this section is registered, and no cell
here is authorized.** It follows the module admission gate of section 8 of the design note: one
config key, never a second code path; module ON versus module OFF on the same roster; the carrier's
own null; ADMITTED / NEUTRAL / HARMFUL.

### 4.1 One entry in the observe-mode table, nothing else

The mode is one row of the Observer's `observe` table and one registered tool, reached the way the
tail and the 16 kHz media already are — an offline **media build** that emits a derived variant of
a sealed roster, not a runtime call inside the loop:

* one `LocalFunction`-shaped tool row: id, pinned weight hashes, typed input/output, side effect
  `bytes changed -> derivation record required`, cost class CPU, axis **OBS**, scope general;
* one config key on the observe-mode table (`obs_enhance: none | deepfilternet3-v1`), resolving in
  a `core.base` registry, as the engineering base check requires;
* **no new module under `rails/probes/`, no `TaskAdapter` subclass, no `launcher/` directory** —
  the same base, one thin entry.

### 4.2 The derivation record

Per row, and identical in shape to the `@ts2` and `@16k` supplements: sealed source `sha256`,
emitted `sha256`, byte count, sample count, sample rate, the enhancer's lock key and weight hashes,
the library version, the seed, and `audio_seconds` **unchanged**. The variant id follows the
existing convention (`<sample_id>@dfn3`). The build is registered as its own model-free media row
before the first byte is written, exactly as `SAEA-SN-MF-*-MEDIA-V1` rows are.

### 4.3 The twin

**Two twins, and both are needed:**

* **the score twin** — the sealed un-enhanced rows, already flown, which is what the delta is taken
  against;
* **the form twin** — a byte-identical **pass-through "enhancer"** that runs the entire derivation
  path (decode, identity transform, re-encode, hash, record) and emits bytes equal to the sealed
  input. It costs one media build and no contacts, and it is what proves that any delta belongs to
  the enhancement and not to the plumbing. If the pass-through's emitted bytes are **not** identical
  to the sealed input, the media path itself is the confound and the cell stops there;
* **the resample-only twin, whenever the enhancer's native rate is not the carrier's** — the same
  round trip with the enhancer switched off. A 48 kHz model on a 16 kHz carrier otherwise moves two
  factors at once (section 3.3). This one **does** need contacts if it is to be scored: a scored
  resample-only arm is a full manifest. Price it in, or pick a rate-matched enhancer.

### 4.4 The first cell, priced

Written as the design note asks — Audio2Tool noisy tier, official scorer, imported null — **and
then corrected**, because section 1.1 shows that testbed is the wrong one.

**As asked (Audio2Tool tier 8):**

| item | value |
|---|---|
| roster | the flown `tier8_intent_blending` official population, **n = 500** (never the n = 50 frozen-400 stratum: its Wilson CI90 half-width is ~10 pp, which cannot resolve anything) |
| arms | (a) `tier8` un-enhanced and (b) `tier8@enh`, plus the pass-through form twin as a media check. Arm (a) has to be **re-flown rather than taken from the sealed `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1` rows**, for the same reason as the SLURP cell below: those rows were decoded inside a 1,500-row manifest and this runtime's greedy decode is not bitwise reproducible across batch compositions |
| contacts | **1,000** = two complete 500-row manifests; **+4** for the dry run. Taking arm (a) from the seal instead would cost 500 and put replicate noise on the arm axis; that trade is available but must be declared in the verdict |
| audio | ~6,600 s of speech (tier 8 median 6.20 s × 1,000, plus headroom) |
| scorer | `a2t-toolcall-official` — the pinned release's own `metrics.py`, one job over the complete manifest through `core.scoring_batch`, never sharded |
| null | **imported, and the verdict must say so.** Audio2Tool has no measured same-request null. Per the 2026-09-07 convention: the tier's own **Wilson CI90 at n = 500** is the harm floor — for 46.80 at n = 500 that is **[43.16, 50.48]**, a half-width of **~3.7 pp** — and for any paired overall delta the margin is zero plus the Earnings-22 null half-width, **declared imported, not measured** |
| decision | ADMITTED only if the delta's CI90 is disjoint from that interval **upward**; NEUTRAL if inside; HARMFUL if disjoint downward |
| what it can prove | **almost nothing.** Tier 8 is already ALIGNED at +5.1 above the published row, its degradation is a competing intelligible utterance rather than noise, and a denoiser has no target-selection cue. A separator would need an oracle stream choice, which is a ceiling read and not a mode |

**As it should be (SLURP far-field), and this is the cell I would actually price:**

| item | value |
|---|---|
| roster | the **766 DEV-1000 utterances that have both channel files**, using the **far-field member of each pair**, whether or not it is the member the comparator flew |
| the point | it makes the contrast **paired on the utterance**: same speaker, same words, one recording id. That is the design SLURP hands us free and that DEV-1000 currently spends on a random channel draw. It is a pairing by utterance, not by sample (the two files are not frame aligned, section 1.2) |
| arms | (a) far-field un-enhanced, (b) far-field enhanced, (c) **headset — the ceiling arm**. Arm (c) is what makes the read interpretable: it measures how much of the gap enhancement recovers **of a gap we have already measured to be ~0** |
| contacts | **2,298** = three complete 766-row manifests, plus a 4-row dry run. The tempting saving is illusory: of the 766 pairs the comparator already sealed 390 far-field and 376 headset members, so "only" 766 + 766 rows are strictly missing — but those sealed rows were flown in a **different batch composition**, and this runtime's greedy decode is not bitwise reproducible across batch compositions (`SAEA-E21-FULL44-NULL-REPLICATE-V1`: 66 % of 1,593 windows emitted different bytes on an identical re-flight). Mixing sealed and fresh rows inside one arm would put that variability on the arm axis. **Fly each arm whole** |
| audio | ~2.7 s median per row × 2,298 ≈ 6,200 s |
| scorer | the locked `slurp-slu-official-projected-v2` through `core.scoring_batch`, one job per complete manifest |
| statistics | paired, cluster-bootstrapped over the utterance, CI90 — a real paired contrast at n = 766, which is above the n ≥ 400 floor |
| null | SLURP has **no measured same-request null either**. This cell should be preceded by, or paired with, a SLURP own-null replicate in the shape of `SAEA-E21-FULL44-NULL-REPLICATE-V1`; without it the margin is imported and must be declared so |
| honest expected outcome | **NEUTRAL.** Arm (c) minus arm (a) IS the ceiling, and the randomized estimate of it is already **+0.09 pp intent [−5.20, +5.29] and +2.54 pp SLU-F1 [−2.45, +7.45]**, both containing zero. Arm (b) can only land inside that, and the artefact risk of section 3.2 makes a *negative* result the most likely single outcome |

**The cheapest thing that would change my mind:** arms (a) and (c) alone — the **paired**
headset-versus-far-field ceiling at n = 766, 1,532 contacts, **no enhancer, no download, no
derivation record, no new dependency, no new roster and no new gold**. It is the paired version of
the section 1.2 estimate. If a paired contrast at n = 766 turned out to be several points and
separable from zero, enhancement would suddenly have a target and this note would need revisiting;
if it lands where the randomized estimate puts it, the question is closed on the study's own data
rather than on an argument. **That, not an enhancer bring-up, is the correct next step if the owner
wants this settled rather than shelved.**

### 4.5 The risk that enhancement harms the encoder, and its falsifier

**The risk, stated precisely.** The frozen core's audio front end was trained on unenhanced audio.
An enhancer's residual artefacts — spectral holes, musical noise, over-suppressed fricatives, phase
damage — are a distribution the encoder has never seen, and section 3.2's literature says that is
the dominant cause of enhancement-induced ASR degradation. There is a second, study-specific edge:
Audio2Tool's wavs already pass through llama.cpp's *lowest-quality* linear resampler with a 4th-order
Butterworth at 8 kHz and audible aliasing above it (the 2026-09-07 audit). **Enhancement artefacts
would be resampled by that filter, and the two interact in a way nobody has measured.**

**The falsifier, and it is cheap and comes first.** Run the enhancer on rows that have **nothing to
remove** and see whether the score survives.

> **Clean-side falsifier.** Enhance the **478 DEV-1000 rows the comparator actually flew on the
> headset channel** — the cleanest audio in the study, margin 36.2 dB — and score them against
> their own sealed un-enhanced selves, paired row by row, cluster-bootstrapped over the utterance,
> CI90, through the locked `slurp-slu-official-projected-v2`. These 478 rows need no new roster and
> no gap-filling: every one of them already has a sealed score under the identical request.
>
> * If the CI90 of (enhanced-headset − sealed-headset) is **disjoint from zero downward**, the
>   artefact hypothesis is **confirmed**: the enhancer damages this core on audio that needed
>   nothing. **The mode is refused outright, whatever it does on degraded rows**, because an
>   observe mode is selected by a Planner rule that will sometimes fire on clean input.
> * If it is **inside the imported null margin**, the artefact risk is not demonstrated at this
>   power, and the degraded-side cell may proceed — with that stated as an unmeasured risk, not as
>   a clearance.
> * If it is **disjoint upward**, something is wrong with the experiment, not right with the
>   enhancer: an enhancer that improves already-clean close-talk speech is measuring a confound
>   (a level change, a length change, a resample) and the byte check of step 5 must be re-run.
>
> Cost: **478 contacts**, one media build, no new roster, no new gold. It is strictly cheaper than
> the degraded-side cell and it can kill the mode before that cell is paid for. **Run it first.**
>
> One honest limit on it: it inherits the same imported-null problem as everything else on SLURP —
> a same-request replicate here would move some rows even with the enhancer switched off, so
> "disjoint from zero" should read "disjoint from SLURP's own measured null" the moment that null
> exists, and until then the margin is imported and the verdict must say so.

A second, free falsifier for the plumbing: the pass-through twin of section 4.3. If the identity
transform's bytes are not identical to the sealed input, no enhancement number from that path means
anything.

---

## 5. What this note does and does not do

**It does:** answer owner Decision 12-H's first half with sealed measurements — the carriers'
noise and channel structure, the measured headroom, and the ceiling wherever one is computable;
answer its second half with an explicitly unverified, network-free survey; and price the design so
the decision can be made on cost rather than on hope.

**It does not:** register a cell, preregister anything, authorize a download, admit a tool, create
a derivation record, or claim a result. It scores nothing new, it changes no sealed number, and it
contacts nothing. The two recommendations of section 3.3 are **candidates for the owner to accept
or reject**, not a plan in motion.

**And it does not settle the frontier.** I could not reach the network. The 2025–2026 speech
enhancement literature is, from this note's point of view, **unsurveyed**: if the owner wants the
candidate table to be authoritative rather than indicative, that is a networked task and should be
run as one before any weight is pinned.
