# Who decides where to cut: model-declared boundaries are the wrong mechanism (2026-08-10)

Owner asked whether an external VAD is even needed, or whether the omni model
could be given the segmentation task directly — hand it audio, have it return
semantic segment boundaries — which would remove the preprocessing dependency
entirely. Literature survey, no runs.

**Answer: the semantic half of that idea is supported; the timing half is not,
and our current design already depends on the timing half.**

## The evidence lands on our exact model

Retkowski et al., *Beyond Transcripts: A Renewed Perspective on Audio
Chaptering* (Feb 2026, [arXiv:2602.08979](https://arxiv.org/abs/2602.08979))
evaluates **Qwen3-Omni-30B-A3B-Instruct** — the model this study serves — on
predicting chapter boundaries in audio:

| | |
|---|---|
| median timestamp deviation from ground truth | **11.8 s** |
| mean deviation | 22.0 s |
| predictions within a 10 s tolerance | **43 %** |
| F1, model emits the timestamp directly | 12.52 |
| F1, same model's boundary decision taken in TEXT space and located by forced alignment | **43.84** |

Their conclusion is the useful one: **"the bottleneck is temporal grounding
rather than segmentation ability."** The model can tell you *where* the content
turns; it cannot reliably tell you *when* that was as a number.

Corroboration that this is general, not a Qwen quirk:

- **BLAB** ([arXiv:2505.03054](https://arxiv.org/abs/2505.03054)), 51-minute
  average clips: Gemini 2.0 Flash scores ~3 % F1 on word localisation, and
  degrades further with duration.
- The **Qwen team's own answer** to needing accurate long-audio timestamps was
  not a better prompt — they trained a separate 0.6B **Qwen3-ForcedAligner**
  ([arXiv:2601.21337](https://arxiv.org/abs/2601.21337)), citing "sharp
  degradation in timestamp accuracy on long utterances" from direct emission.
  A same-lab admission that the frozen omni model is not the tool for this job.
- Qwen3-Omni's own model card does not list timestamp output as a supported
  capability at all.

## Why this matters here and now: it names our own bug

Our loop asks the model for `BOUNDARY_SECONDS: NN` and **advances on that
number**. A median timestamp error of ~12 s is already larger than our entire
overlap window (~12 s, being 20 % of a 60 s buffer). The measured consequence is
already on record: 1,648 s of audio advanced past and never transcribed
(`2026-08-09-deletion-mass-is-made-at-the-stitch.md`).

This is textbook Whisper long-form drift. Whisper transcribes a 30 s window,
reads its own predicted end-timestamp, shifts the window there, and repeats
([Whisper paper §3.8](https://cdn.openai.com/papers/whisper.pdf)) — structurally
identical to our design, and its documented pathologies are ours: timestamp
drift compounding window to window, repetition loops under greedy decoding, and
hallucination on non-speech (**40.3 % of pure non-speech inputs produce
hallucinated text**, [arXiv:2501.11378](https://arxiv.org/pdf/2501.11378)).

**Honest limit on this evidence:** every number above is measured at whole-file
scale (30–51 min), not at our ~60 s chunk granularity, and no published work
prompts an omni model chunk-by-chunk for internal boundaries and reports ASR
quality. That experiment does not appear to exist. But the failure mechanism
identified — numeric emission being unreliable *independently* of semantic
understanding — is not obviously a long-context artifact that disappears at
60 s, and the median error already exceeds our overlap. Extrapolating optimism
downward would run against the only evidence there is.

## What the field converged on

WhisperX ([arXiv:2303.00747](https://arxiv.org/abs/2303.00747)) decouples three
jobs that we currently ask one model to do at once:

1. **where to cut** — an external VAD, so chunk edges land on real acoustic gaps;
2. **what was said** — the recognizer;
3. **precise timing** — a separate lightweight forced-alignment pass.

Measured against Whisper's self-reported timestamps on Switchboard: 93.2 % /
65.4 % precision/recall versus 85.4 % / 62.8 %. The chaptering paper arrives at
the same decoupling independently for omni-LLMs.

## VAD options, judged for our case

Every tool below produces **acoustic** speech/non-speech boundaries only. None
produce semantic ones off the shelf.

| tool | licence | cost | fit for our two problems (46 dB noise-floor spread; one file at ~7 dB range) |
|---|---|---|---|
| **Silero VAD** | MIT | 2 MB, <1 ms/chunk on one CPU thread | Neural spectral features, so the decision is *relative* rather than absolute-level — structurally the right answer to both. Tunable down to 100 ms silences, far finer than the 0.3–1.0 s structure we measured. TPR ≈ 87.7 % at 5 % FPR. **Recommended primary.** |
| SpeechBrain `vad-crdnn-libriparty` | Apache-2.0 (toolkit) | CRDNN, needs the full SpeechBrain/PyTorch stack | Trained on **LibriParty** — simulated indoor cocktail-party scenes, a materially different domain from limited-dynamic-range conference audio. No evaluation found on compressed/broadcast speech. Domain risk is real and unverified either way. |
| pyannote.audio segmentation-3.0 | MIT toolkit / CC-BY-4.0 weights | heavier neural | Richer (VAD + overlap + speaker turns) and same relative-feature argument. **Gated on Hugging Face** — a token and a usage-data prompt, which is registration friction worth flagging against this study's exposure discipline. |
| WebRTC VAD | BSD | negligible | TPR ≈ 50 % at 5 % FPR — a 1999-era GMM on raw features with no learned level invariance. Keep only as a zero-dependency fallback; our config already allows it. |
| TEN VAD (2025) | Apache-2.0 **plus an anti-compete rider** | lightweight C + ONNX | Credible Silero challenger on vendor benchmarks; no independent replication found. Licence rider needs reading before adoption. |

For the pathological file specifically, the literature's answers are (a) use a
neural VAD rather than an energy threshold — which is a mechanism-level fix for
exactly this class, though no source tested audio matching our profile; (b)
pitch/periodicity VAD (**rVAD**, zero-frequency filtering), since a limiter
crushes amplitude but not voicing periodicity; and (c) **not** loudness
normalisation, which retargets level across programmes and cannot restore
dynamic range already compressed out of a file.

## Semantic segmentation does exist — but not for a frozen core

E2E Segmenter (Google, Interspeech 2022; 8.5 % relative WER improvement over a
VAD baseline on long-form YouTube), Semantic VAD (Interspeech 2023; 53.3 %
latency reduction at no CER cost), and bidirectional-LM semantic segmentation
all place the segmenter **inside** the recognizer, jointly trained. None is a
library you can put in front of a frozen, API-only model. There is no
plug-and-play semantic segmenter compatible with this study's constraints.

## What we should change

1. **Stop advancing on the model's declared boundary.** That is the mechanism
   the evidence indicts and the one our own overrun measurement caught.
2. **Cut with a neural VAD** (Silero first), non-overlapping, packed to a
   60–90 s target — which the pause measurement showed is feasible for 9 of 10
   samples — with a hard-cap fallback cut for the file that has no silence.
3. **Keep the model's semantic judgment, in text space.** Asking "is this a
   complete thought / where does the topic turn" is what it is good at; asking
   "at what second" is what it is bad at.
4. **Add a degeneracy gate before accepting a chunk and advancing**, copying
   Whisper's compression-ratio / average-logprob fallback ladder. Our low-yield
   tail (13.4 % of slices under 2.0 words per second of audio) is exactly the
   population such a gate exists to catch.

Items 1–2 remove the overrun mechanism and the overlap-dedup mechanism at once;
item 4 addresses the tail. Each becomes an arm rather than an assumption.
