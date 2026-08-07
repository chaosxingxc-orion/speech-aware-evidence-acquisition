# Carrier usage survey + mechanism map (2026-08-07)

Status: DRAFT EVIDENCE, model-free. This is the deliverable HANDOVER.md calls
"the most important missing piece": per-carrier performance trajectories
(floor → current best, each step attributed to a concrete mechanism), then
the three-bucket mechanism map. Owner framing rules applied: trajectories are
built from **papers that use the carrier**, the dataset's own introductory
baseline is only a *reference floor*; attribution is labeled by evidence
strength — `[ablation]` = supported by the paper's own ablation/controlled
comparison, `[weak]` = claimed without one. Sources: group-1 survey
(families A/C/E), group-2 survey (B/D/F), artifact hunt — all dated
2026-08-07 — plus the dataset content verification for scope. Numbers across
different papers on the same carrier are **not** on a shared footing unless
stated (different ASR front-ends, subsets, judges); trajectories are
per-paper deltas, not a single scale.

## Trajectory notation

`floor → step (mechanism, evidence label) → … | ceiling/bound` — WER falls,
everything else rises.

---

## Family A carriers

### earnings21-original / earnings22-original

- **Siskos et al. (EMNLP-Findings 2025)**, black-box ASR, E21: no-context WER
  35.9 → 31.1 CB-RAG / 31.8 CB-LLM (retrieved context injected into a
  contextual-ASR prompt) | oracle-context 29.7. Clean 4-condition
  dose-response — the strongest on-carrier `[ablation]` for
  evidence-supply-in-prompt anywhere in the program.
- **RECOVER (arXiv:2603.16411, preprint)**, E21 among 5 sets: 8–46% relative
  entity-WER reduction, up to +22pp entity recall (multi-hypothesis
  generation + deterministic entity-candidate retrieval + LLM correction
  under a verify gate) `[ablation]` per-dataset, but unreviewed preprint, no
  code.
- **FlexCTC/TurboBias (ASRU 2025)**: WER + bias-phrase recall gains from
  GPU-resident decoder phrase-boosting, bias lists literally sourced from E21
  `[ablation]` — mechanism unreachable (decoder-internal).

### conec

- **ConEC (LREC-COLING 2024)** floor: conventional-ASR aggregate WER 10.41
  no-bias, biasing conditions move it only within 10.29–10.66 `[weak
  aggregate — per-entity-class breakdown is where its signal lives]`;
  baselines in icefall (decoder-level, unreachable). Correction from the
  artifact hunt: official repo `huangruizhe/ConEC` exists (contexts +
  corrected transcripts; no LICENSE).
- No later papers found that improved on ConEC's task with any mechanism —
  trajectory has a floor and no steps.

**Buckets (A):**
1. *Shown + reachable:* context/evidence injection into the prompt (Siskos —
   on-carrier, dose-response); retrieval-grounded post-ASR entity correction
   (RECOVER — on-carrier, preprint caveat).
2. *Shown + unreachable:* decoder-level phrase boosting (FlexCTC/TurboBias,
   ConEC icefall baselines); trained contextual LMs/shallow fusion (ConEC
   baselines).
3. *Never tried on-carrier + reachable:* n-best/uncertainty prompting (shown
   off-carrier by WCN-ICL); self-cascade two-pass correction from the core's
   own sampled hypotheses; ICL exemplar retrieval; per-entity-class scoped
   evidence dosing (Siskos did dose-response on WER only).

---

## Family B carriers

### slurp

- Floor (Bastianelli 2020): pipeline Multi-ASR(WER 16.2)+HerMiT IC 76.68 /
  SLU-F1 69.53 → adapted 78.33/70.84 | gold-transcript NLU bound 84.84/78.19.
- Trained line: CTI (2021) 82.93/71.12 (ASR-BERT continuous-token interface
  training `[ablation]`) → SFT Qwen2-Audio (ICASSP 2026) 88.13/76.75
  (audio-LLM SFT; curriculum + small-speech-data ablations `[ablation]`) →
  UniverSLU (NAACL 2024) ~90.3 IC (multi-task instruction tuning of Whisper
  `[ablation]`, number search-attributed). All unreachable.
- Zero-shot slot-filling line (still trained): ZS-Whisper-SLU 50.0 SLU-F1 →
  QA-driven prefix-tuned Whisper (+40.7 abs `[ablation]`) → WHISMA 63.1/63.3
  (aligner+LoRA; ASR-auxiliary task ablation: without it 46.8 `[ablation]`) |
  supervised ref 69.9. All unreachable. **No prompt-only slot-filling number
  exists on SLURP at all.**
- Prompt-only line (IC only): AIR-Bench 1k subset — direct audio-LLMs 25.6 →
  77.8 (model identity, no mechanism) vs cascade Whisper+GPT-4 87.7
  (transcript mediation, same items — controlled comparison `[ablation]`).

### speech-massive

- Floor (Interspeech 2024): cascaded Whisper+mT5, cross-lingual "zero-shot"
  IC avg 69.10/slot 43.15 → few-shot 72.45/49.78 → full FT 83.04/61.21 (all
  trained; mechanism = target-language supervision dose `[ablation]`) | gold
  bound 86.73. E2E FR 85.87.
- SFT Qwen2-Audio (ICASSP 2026) FR 87.39 IC / 74.86 SLU-F1 (metric definition
  differs from slot-micro-F1 — not directly comparable to 61.21).
- No prompt-only line exists on this carrier.

### minds14

- Floor (Gerz 2021): LaBSE+MT+trained-MLP 91.3–95.9 avg acc over 3-fold
  random splits — **no canonical split; cross-paper comparability poor**.
- XTREME-S: fine-tuned speech encoders; mSLAM-TLM +1.3 over speech-only
  `[ablation]`. MAEB (2026): embedding-probe only (Qwen2-Audio 25.51 vs
  Whisper-medium 48.30 — representation quality, not task prompting).
- No prompt-only line exists on this carrier.

**Buckets (B):**
1. *Shown + reachable:* transcript self-mediation for IC (AIR-Bench cascade
   contrast, on-carrier); closed-label-set-in-prompt protocol (AIR-Bench
   construction).
2. *Shown + unreachable:* every training mechanism above (E2E/SFT/multi-task
   instruction tuning/aligners/prefix-tuning/contrastive robustness lines).
3. *Never tried + reachable:* prompt-only slot filling (first-of-its-kind
   territory on SLURP); schema/ontology-in-prompt supply (MIST precedent,
   off-carrier); ICL exemplar retrieval from train split; n-best/WCN
   prompting; self-correction second pass; multilingual prompt-only IC on
   speech-massive/minds14 (entirely unpopulated).

---

## Family C carriers

### slue-sqa-5

- Floor (SLUE Phase-2, ACL 2023): trained pipeline (ASR + DeBERTa
  span-extractor fine-tuned on transcripts), frame-F1 metric; SQA baseline
  code never released (re-confirmed).
- SpeechDPR (ICASSP 2024): trained speech-passage bi-encoder; Top-20
  retrieval accuracy gates downstream frame-F1 `[ablation]` — the family's
  explicit SUPPLY-sensitivity evidence; unreachable (trained retriever).
- AudioBench (NAACL 2025): direct-prompting judge protocol over
  `slue_p2_sqa5_test`; published audio-LLM rows; runnable (group-1 R1-full
  line) — but protocol always supplies the full document (SUPPLY-insensitive
  by construction).

### spoken-squad

- Floor (Interspeech 2018): trained span predictors; ceiling Su & Fung 2020
  F1 77.67 (fine-tuned contextualized QA head). Both unreachable, no code.
- SpeechRAG (ICASSP 2025): trained speech retriever; claims direct speech
  retrieval "does not degrade" vs text `[weak from accessible excerpts]`;
  unreachable.
- AudioBench `spoken_squad_test` direct-prompting rows: runnable, published.

### heysquad

- Floor/best (arXiv:2304.13689): fine-tuned RoBERTa extractors; the paper's
  useful mechanism finding is human-vs-machine-transcription QA degradation
  `[ablation]` — an OBS-quality dose signal. Unreachable as method; no
  frozen-inference baseline published; not in AudioBench.

**Buckets (C):**
1. *Shown + reachable:* direct-prompting QA protocol (AudioBench, two of
   three carriers, published rows to calibrate against).
2. *Shown + unreachable:* trained retrievers (SpeechDPR/SpeechRAG — the only
   lines with demonstrated SUPPLY sensitivity), trained span extractors
   (SLUE/HeySQuAD/Su&Fung).
3. *Never tried + reachable:* SUPPLY perturbation under prompting (chunking /
   ordering / retrieval-quality ladders with EM/F1 scoring — the family's
   central tension in group 1: every SUPPLY-sensitive line is unreachable,
   every reachable line is SUPPLY-insensitive; a prompting-based SUPPLY
   ladder on spoken-squad/heysquad would be first-of-its-kind);
   self-cascade; n-best prompting; timestamp-anchored answer localization
   under prompting (slue-sqa-5's word2time layer is unused by any
   prompt-only work).

---

## Family D carriers

### audio2tool

- Floor (arXiv:2604.22821) — introductory prompt-only baselines, tiered:
  **Qwen-3-Omni-30B (our core): Tier1 92.4 → Tier3 multi-intent 74.7 → Tier8
  intent-blending 41.7** (Tool-Accuracy family, deterministic metrics);
  Whisper+Gemma-27B 87.9 → 50.5. Pipeline-vs-E2E: rough parity, both ~50% at
  Tier8 `[ablation]`. Noise: significant degradation across 3 noise types × 3
  SNRs `[ablation]`.
- No later papers. Trajectory = floor only. Eval scripts unreleased
  (placeholder repo); metrics reimplementable deterministically.

### voiceagentbench

- Floor (arXiv:2510.07978): pipelines Whisper+Llama3-70B EN
  parameter-filling 60.64 / Indic 39.21 > SpeechLMs (KimiAudio 57.57/28.21;
  Qwen2.5-Omni-7B 1.70/0.29 format collapse). Mechanism ablations —
  **one-shot prompting +10–17pp on complex tasks** `[ablation]` (a reachable,
  on-carrier prompting mechanism: the only one published in family D);
  refusal-prompt removal → 4× safety drop `[ablation]`; ASR errors ≥24pp
  Indic degradation `[ablation]`. Note: the dataset's `single_tool_retrieval`
  category builds tool-retrieval into the protocol itself — the retrieval
  policy is an open experimental surface.
- No later papers.

### full-duplex-bench-v3 (adjacent)

- Floor (arXiv:2604.04847): duplex products; GPT-Realtime Pass@1 0.600 …
  cascade Whisper→GPT-4o→TTS 0.450. Mechanism reversal: self-correction
  disfluencies — cascade 0.176 vs native 0.588 `[ablation]` — the program's
  clearest evidence that transcript mediation *loses* when disfluency
  semantics matter. Our core cannot enter the duplex protocol; offline
  tool-call subset scoreable.

**Buckets (D):**
1. *Shown + reachable:* direct prompting with full tool schema (both
   floors); one-shot exemplar prompting (VoiceAgentBench, on-carrier);
   self-cascade analog of the pipeline arms.
2. *Shown + unreachable:* agentic-trained LLM backends (VoiceAgentBench
   attributes pipeline superiority to them `[weak]`); native-duplex speech
   stacks (FDB-v3).
3. *Never tried + reachable:* retrieval-augmented tool-schema supply
   (nothing beyond full-schema-in-prompt exists); ICL exemplar *retrieval*
   (only fixed one-shot tried); n-best/uncertainty prompting; re-ask /
   self-correction loops (FDB-v3 shows exactly where they're needed);
   evidence extraction under distractors (Audio2Tool's needle/correction/
   intent-blending tiers are unattacked by any method).

---

## Family E carrier

### ami-meeting-corpus

- QMSum line: trained summarizers (BART/HMNet…) → zero-shot LLM prompting
  (ZeroSCROLLS, reachable but gold-transcript caveat) — ROUGE metric
  documented as evidence-insensitive (MS-AMI authors: ROUGE/BERTScore
  "nearly identical across conditions" `[ablation]` — disqualifying for an
  evidence-acquisition calibration target).
- MeetingQA: fine-tuned extractive F1 57.3 | human 84.6; zero-shot not
  cleanly isolable. MeeQA: trained QA head, no license.
- CMT-LLM (Interspeech 2025): contextual multi-talker ASR, AMI SDM WER 32.9
  @1000 distractors (trained projector + biasing `[ablation]`); artifact-hunt
  correction: official code exists (`JiajunHe1025/CMT-LLM`), boundary verdict
  unchanged.
- PlanRAG-Audio (ACL Findings 2026): frozen audio-LLMs + deterministic
  non-trained retriever on AMI — architecturally the closest published
  design to this study; **still unreleased** (re-checked today).

**Buckets (E):**
1. *Shown + reachable:* zero-shot summarization prompting (metric-weak).
2. *Shown + unreachable:* trained summarizers/extractors; trained multi-talker
   contextual ASR.
3. *Never tried + reachable:* evidence-supplied meeting QA under prompting
   with span-sensitive scoring; entity-grounded meeting understanding;
   PlanRAG-Audio's own design point remains open until its release.

---

## Family F carriers

### voicebench / voiceassistant-eval / uro-bench / big-bench-audio

- Trajectories on all four are **model-training ladders**: VoiceBench Oct
  2024 → top 89.39 (Nemotron Nano Omni) with cascade Whisper+GPT-4o at 87.80
  (rank 4); URO-Bench cascade 89.33 vs best open E2E SDM 69.09 (EN basic);
  VoiceAssistant-Eval GPT-4o-Audio 39.78 listening / 51.26 speaking, 20/22
  models speak better than they listen; Big Bench Audio GPT-4o text 92 vs
  native speech 66 vs Whisper→GPT-4o pipeline ≈ text `[ablation — cleanest
  controlled mechanism comparison in the program]`, gap closed to 92 by
  Gemini-2.5 Native-Audio-Thinking (training, Oct 2025).
- **No inference-time method has ever been evaluated on any of the four.**

**Buckets (F):**
1. *Shown + reachable:* transcript self-mediation (BBA/URO-Bench/VoiceBench
   cascade rows — multi-carrier, consistently ≥ native for open models).
2. *Shown + unreachable:* every SDM/omni training step; reasoning-trained
   native audio.
3. *Never tried + reachable:* everything else — prompting strategies,
   retrieval/evidence supply, self-correction, uncertainty handling.

---

## Consolidated three-bucket map (cross-carrier)

**Bucket 1 — shown to work AND reachable (R1 calibration candidates):**

| mechanism | on-carrier evidence | strength |
|---|---|---|
| transcript self-mediation (cascade→self-cascade arm) | Big Bench Audio 66→~92; AIR-Bench SLURP 77.8→87.7; URO-Bench +20; VoiceBench rank-4; counter-case FDB-v3 self-corrections 0.588→0.176 | multiple independent controlled comparisons; strongest reachable signal in the program |
| context/evidence injection into prompt | Siskos on E21: 35.9→31.1 WER, oracle 29.7 (dose-response); MIST schema-in-prompt (off-carrier) | on-carrier ablation (A); single-paper |
| retrieval-grounded post-ASR entity correction | RECOVER on E21: 8–46% rel E-WER, +22pp recall | on-carrier ablation, but unreviewed preprint, no artifact |
| one-shot / few-shot exemplar prompting | VoiceAgentBench +10–17pp (on-carrier); WCN-ICL one-shot closes 81% of 1-best→oracle gap (off-carrier) | on-carrier ablation (D) |
| uncertainty/n-best-in-prompt | WCN-ICL (ATIS/NMSQA only) | off-carrier; as-arm only (no lattice from a chat endpoint — sampled n-best analog) |

**Bucket 2 — shown to work but unreachable (structural-gap evidence):**
decoder-level phrase boosting (FlexCTC/TurboBias, icefall-ConEC); every
SFT/instruction-tuning/aligner/prefix/projector line (UniverSLU, SFT-LALM,
WHISMA, QA-prefix, CTI, CMT-LLM, XTREME-S encoders, Speech-MASSIVE
baselines); trained retrievers/rerankers (SpeechDPR, SpeechRAG); trained
extractive heads (SLUE, HeySQuAD, Su&Fung, MeetingQA, MeeQA); trained
summarizers (HMNet, QMSum baselines); reasoning-trained native audio
(Gemini-2.5-NAT); native-duplex stacks (FDB-v3 systems). Notably, the only
lines with *demonstrated SUPPLY sensitivity* in family C (SpeechDPR,
SpeechRAG) sit in this bucket — the reachable/insensitive vs
sensitive/unreachable tension group 1 identified is confirmed program-wide.

**Bucket 3 — never tried on these carriers but reachable (contribution
space):** across all 17 in-scope carriers, **no published inference-time
evidence-acquisition method exists** — no retrieval-augmented supply under
prompting, no SUPPLY perturbation ladders, no n-best/uncertainty prompting on
any held carrier, no self-correction/re-ask loops, no exemplar-retrieval ICL,
no prompt-only SLURP slot filling, no prompt-only multilingual SLU. The
mechanism class this study targets (OBS/ORG/SUPPLY/USE control around a
frozen core) is unpopulated on every carrier we hold; the closest published
design (PlanRAG-Audio) is unreleased. Bucket 1 provides the calibration
anchors; bucket 3 is where any X-probe result would be un-preceded.

## Implication for the R1 re-plan (owner decision pending)

The map supports the group-2 verdict: R1-as-written ("closest-prior
reproduction") remains impossible for method lines (bucket-1 rows with
on-carrier ablations ship no artifacts), but benchmark-protocol reproduction
with published numbers is available on ≥6 carriers, including one same-model
row (Audio2Tool × Qwen-3-Omni-30B, tiered, deterministic metrics). A
defensible composite is HANDOVER option 2 (+3): protocol reproduction to
calibrate the pipeline against published same-model numbers, plus a
constructive degradation ladder to prove metric sensitivity — with bucket-1
mechanisms as the ablation-precedented arm designs for the X probes. Recorded
as evidence, not as a decision.
