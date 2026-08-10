# Positioning and the ablation ladder (owner directives, 2026-08-09)

Three owner directives this session fix the study's competitive frame and its
experimental method. Recorded here because everything downstream (which arms
exist, what counts as success, what we may claim) follows from them.

## 1. Fair comparison: use Earnings-21, and score the published systems ourselves

Earnings-21 is on disk in full (44 calls = the entire published corpus), and
the release ships **each evaluated system's own hypothesis transcripts**
(`output/{amazon,google,microsoft,rev,speechmatics,kaldi_org}`) in the same
`.nlp` format as the references. So the fairest available comparison is not
"our number vs their paper number" but **their transcripts and ours scored by
the same frozen scorer on the same calls**.

Measured (10-call R4 mini sample, frozen `normalize_text_v1` + alignment):
Amazon 15.70 · Google 16.36 · Speechmatics 17.07 · Microsoft 17.95, against
paper values 17.0 / 17.8 / 16.0 / 15.8 — agreement within **±1.3–2.2 pp**.

Consequences:
- The **target band on this sample+metric is 15.70–17.95 % WER.**
- Our E-21 numbers may be placed beside published ones with a stated ±2 pp
  tooling allowance (previously we could only claim an ordinal relation).
- The R4 `no-context` arm doubles as our comparable single-task ASR baseline;
  E-001's 26.70 % is on Earnings-**22** (harder, accented) and is NOT the
  number to compare against this band.

## 2. What we are actually competing on

Single-task ASR SOTA is the **reference frame, not the claim**. A frozen omni
core driven by an inference-time control plane will not out-transcribe systems
built and tuned solely for transcription — and it does not need to. The claim
is:

> One frozen core plus one agentic control plane reaches usable performance
> across transcription, entity fidelity, spoken QA and tool calling on the
> same substrate, and evidence supply systematically improves them — with zero
> parameter training.

So every task carries two numbers: **distance to the best single-task baseline**
(honesty about the gap) and **the arm-to-arm delta our mechanisms produce**
(the contribution). The second is where the science lives; the first keeps us
from over-claiming.

## 3. The current agent system is the ablation baseline

The obs-agent-loop as it stands today — model-guided segmentation, energy-VAD
snapping, bounded advance, rolling tail conditioning, bounded per-slice retry,
sample-level batching — is **A0, the baseline to ablate against**, not a
finished system. Every capability is added as its own arm, each independently
pre-registered, each with a measurable end-to-end delta:

| rung | added element | axis | status |
|---|---|---|---|
| A0 | segmentation + VAD + tail conditioning (today) | OBS | running (E-001 done, R4 in flight) |
| A1 | external evidence supply (matched / mismatched ConEC materials) | SUPPLY | R4 arms, in flight |
| A2 | multimodal knowledge base (retrieval over an indexed evidence store rather than a fixed injected block; local generative embedding model as a pinned tool) | ORG+SUPPLY | designed, not built |
| A3 | denoise-and-relisten tool calling (acoustic-badness trigger → pinned denoiser → re-ask → deterministic keep rule) | OBS+USE | designed, not built |
| A4 | confusable-set injection and correction re-ask (phonetic keying + self-detected cross-slice inconsistency) | ORG+USE | designed, not built |
| A5 | condition-aware routing between direct and mediated paths | construct 4 | designed, not built |

Rules for the ladder: one element per arm; every arm pre-registers its
success criterion before it runs; a rung that does not move the metric is
reported as a null, not quietly dropped; and the A0 baseline is re-run
whenever the substrate changes so deltas are always same-substrate.

### 3b. Amendment (owner, 2026-08-10): for long audio the policy IS the carrier

The ladder above treats the segmentation substrate (A0) and knowledge supply
(A1–A2) as independent rungs. That holds for short-utterance carriers. **It does
not hold for long audio**, where the systematic answer is end-to-end agent
optimisation, and where knowledge, memory and skills do not enter *alongside*
the policy — they enter **through** it.

Under the interleaved listening-and-spelling policy (IC-001) the four constructs
stop being separate rungs and become parts of one loop:

| construct | in the loop | what it was in A0 |
|---|---|---|
| OBS | commit step + left context + right lookahead | a fixed 60 s window |
| ORG | the compacted carried memory | a 400-character rolling tail |
| SUPPLY | what is placed in the next step's prompt | one static evidence block, identical on every slice |
| USE | the decode | the decode |

Two consequences the ladder has to absorb:

**1. Evidence becomes dynamic rather than static.** In A0 the ConEC block is
prepended identically to all ~60 slices of a call. In the loop it can be
re-selected per step against what is currently being heard. That turns A1 from
"does context help" into "does *this* context help *now*", which is a different
and harder question — and the one worth asking.

**2. Memory and knowledge merge, and the merge is self-supplied.** The entity
glossary the loop keeps for continuity — speaker names, tickers, product names,
recurring figures, all extracted from what the system has *already transcribed* —
is simultaneously ORG (memory) and SUPPLY (a bias list). It is derived from the
system's own output, never from gold, so it carries **no leakage exposure at
all**, and it targets proper names, which is where this domain's errors
concentrate. It is the training-free, incrementally-built analogue of contextual
biasing, and it needs no external evidence source to exist.

The revised long-audio ladder, therefore, is not A0→A1→A2 but:

| rung | added element | falsified by |
|---|---|---|
| L0 | A0 as it stands — the floor every rung below must beat | — |
| L1 | interleaved policy, verbatim tail only, no compaction | no reduction in deletion share below 60.6 % at matched audio-token budget |
| L2 | + memory compaction (tail / glossary / discourse state) | compaction loses to a plain verbatim tail at equal token budget |
| L3 | + **self-supplied** glossary fed forward as a bias list | no entity-class WER gain over L2 |
| L4 | + external evidence, selected per step rather than prepended once | no gain over L3, i.e. external context adds nothing the system could not supply itself |
| L5 | + tools (denoise-and-relisten, forced alignment where timing is needed) | no gain on the low-yield tail specifically |

**L4 is the sharpest experiment in the ladder**: if a self-supplied glossary
matches externally supplied context, then the study's evidence-acquisition
premise needs restating for this carrier — and that is a result worth having
either way.

The A0-substrate probes already in flight (R4 dose, B-2a form) are **not
superseded** by this. They measure the floor and they answer "does knowledge
help at all, and in what form", which L3/L4 need as a reference point. A ladder
without a measured floor cannot attribute its gains.

## 4. Sampling discipline (owner directive, same session)

Validation work samples — it does not run full corpora. A firm rough answer
that lets the next decision proceed is the goal; full-corpus runs are reserved
for results we intend to publish. The published-system calibration above used
10 calls rather than 44 for exactly this reason, and became *more* rigorous as
a result (same sample as our own arms).
