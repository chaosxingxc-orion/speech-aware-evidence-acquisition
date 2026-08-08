# Reference-works triage + improvement/exploration directions (2026-08-07)

Status: PLANNING DOC (model-free). This refreshes every referenced work from
the R0.1 survey into three explicit classes — **planned for reproduction /
not worth reproducing / cannot be reproduced** — then distills each family's
improvement directions and the study's exploration directions. Execution
sequencing, sampling, and compliance design live in
`2026-08-07-r1-replan-reproduction-plan.md` (P0–P4, incl. the four-construct
abstraction frame and the sample-once manifest policy); the published-number
tables live in the umbrella wiki:
`wiki/experiments/speech-aware-evidence-acquisition/published-baselines.md`.
Owner decision points from the reproduction plan still gate all model
touches. "Reproduce" always means: sampled subsets, paired arms, claimed
improvement as direction + effect size — never full-scale reruns.

## 1. Planned reproductions (7 committed + 4 optional protocol anchors)

| # | work | what exactly we reproduce | plan step | carrier | sampled design | success criterion (pre-registered) |
|---|---|---|---|---|---|---|
| R1 | **Audio2Tool introductory baselines** (arXiv:2604.22821) | the published **same-model** row: Qwen-3-Omni-30B per-tier numbers (92.4/74.7/41.7 …) under their prompt-only protocol | **P1** | `audio2tool` | 50×8 tiers = 400 items | tier rank-order preserved; per-tier \|Δ\|≤5pp; miss = quantization/prompt-fidelity finding |
| R2 | **Big Bench Audio pipeline-vs-native** (Artificial Analysis 2024) | the claimed cascade advantage (text 92 / native 66 / pipeline ≈ text) as a **direction** on our core: direct audio answer vs self-cascade | **P2a** | `big-bench-audio` | 200/1000, 4-category stratified, paired 2 arms | cascade > direct, paired-significant |
| R3 | **AIR-Bench SLURP intent classification** (ACL 2024) | the published cascade-vs-direct gap (87.7 vs 77.8) as a direction on our core; plus our absolute position vs the 8 published rows | **P2a** | `slurp` (AIR-Bench 1k subset) | 200 items, paired 2 arms, deterministic label scorer | cascade > direct; absolute row recorded to baseline wiki |
| R4 | **Siskos et al. context discovery** (EMNLP-Findings 2025) | the dose-response **direction** (no-context → context → better-context, their 35.9→31.1→29.7 WER) with gold kept out of runtime: arms = no-context / matched ConEC materials / mismatched materials | **P2b** (merged with degradation ladder, HANDOVER option 3) | `conec` + `earnings21/22` (start: frozen dev subset10) | ~10 calls × windows × 3 arms | WER (+ per-entity-class WER) monotone in evidence quality |
| R5 | **VoiceAgentBench one-shot ablation** (arXiv:2510.07978) | the claimed +10–17pp one-shot gain on complex tasks | **P2c** | `voiceagentbench` | 150 EN complex items, paired 2 arms | positive paired delta; magnitude vs claimed range recorded |
| R6 | **RECOVER-style entity correction** (arXiv:2603.16411) | the claimed E-WER reduction *class* (8–46% rel) — labeled RECOVER-**style**: preprint, no artifact, real interpretation risk | **P2d-1** (conditional on P2a/P2b positive) | `earnings21` | 1-best vs retrieval-grounded correction pass | relative E-WER reduction > 0 with CI |
| R7 | **WCN-ICL uncertainty prompting** (ICASSP 2024) | the claimed 1-best→uncertainty-in-prompt gap closure (81% on NMSQA), transferred: sampled n-best analog (no lattice from a chat endpoint) | **P2d-2** (conditional) | `slurp` or `heysquad` | paired 2–3 arms | gap closure vs self-oracle > 0 |
| A1 | *AudioBench SQA rows* (NAACL 2025) | protocol rerun of `slue_p2_sqa5_test` / `spoken_squad_test` direct-prompting rows, judge replaced by pinned open judge | optional, post-P2 | `slue-sqa-5`, `spoken-squad` | sampled | fills our rows in the baseline wiki; SUPPLY-insensitive as published — protocol anchor only |
| A2 | *VoiceBench deterministic tier* (TACL 2026) | MCQ/rule-scored subsets only (openbookqa/mmsu/ifeval/advbench/bbh) — no judge needed | optional, post-P2 | `voicebench` | sampled per subset | our core's position vs leaderboard |
| A3 | *URO-Bench EN-basic* | official 1k **miniset** (a natural sampled unit), judge pinned/replaced | optional | `uro-bench` | miniset subset | position vs cascade 89.33 / GLM-4-Voice 69.09 |
| A4 | *VoiceAssistant-Eval in-scope subtasks* | content dimension only, with its own **open judge** (gpt-oss-20b) | optional | `voiceassistant-eval` | sampled, 8/13 in-scope subtasks | position vs published rows |

### 1b. Training-free analog track (plan P3, T-series — owner alignment 2026-08-07)

Trained reference works whose *knowledge component* we re-design as a
training-free analog on the same carrier + scorer, positioned against the
published trained row (gap small → training wasn't load-bearing; gap large →
sharpened structural-gap evidence):

| id | trained reference | analog on carrier | published row it is positioned against |
|---|---|---|---|
| T1 | SpeechDPR | pinned lexical retrieval over core transcripts, bounded pool (`slue-sqa-5`) | Top-20 19.73 / frame-F1 0.558 (direction reference only — pool differs) |
| T2 | SpeechRAG | retrieval ladder closed-book/retrieved/oracle over core-transcribed passages (`spoken-squad`) | the "does not degrade" claim |
| T3 | ZS-Whisper-SLU → WHISMA line | prompt-only slot filling, official scorer (`slurp`) | 50.0 → 63.3 SLU-F1 (first zero-training number on the carrier) |
| T4 | FlexCTC/TurboBias | ConEC bias-lists injected at prompt level — folded into R4's entity-class extension (`conec`/`earnings21`) | mechanism analog only |

## 2. Not worth reproducing (deliberate skips — each with the reason)

| work | reason we skip it |
|---|---|
| ConEC's own biasing-condition experiment | its aggregate WER barely moves (10.29–10.66 around a 10.41 no-bias floor) — a calibration target that cannot show sensitivity; we reuse its **carrier, real context materials, and per-entity-class scoring** instead (they power R4) |
| Raghuvanshi et al. 2019 | metric is a proprietary production-NLU accuracy; no held carrier; mechanism superseded by the RECOVER-style class (R6) |
| DeRAGEC | repo has **no LICENSE** (all-rights-reserved default) — legally blocked; carriers are CommonVoice/STOP (not held); mechanism class already covered by R6 |
| Pusateri et al. | synthetic off-carrier rare-entity test sets, no code; mechanism folds into R6 |
| ZeroSCROLLS/QMSum zero-shot + MS-AMI base arm | runnable but the metric is documented insensitive to evidence quality (MS-AMI's own ablation: ROUGE/BERTScore "nearly identical across conditions") — fails the calibration purpose; keep only as a possible negative-control later |
| Gerz MINDS-14 baselines + XTREME-S minds14 | no canonical split (3-fold random 60/40) → cross-paper comparability is unrecoverable; task near-saturated (95.9) by trained MLPs; carrier stays diagnostic-only |
| MIST | not a held carrier; its mechanism datapoint (schema-in-prompt, Qwen3-Omni 59.86) is already absorbed as evidence |
| Full-Duplex-Bench-v3 full protocol | all six published systems are streaming/duplex products — our core cannot enter the protocol; the counter-case evidence (cascade 0.176 vs native 0.588 on self-corrections) is already extracted; offline tool-call subset remains a later option |
| HeySQuAD fine-tuned baselines | the transferable signal is its transcript-quality-dose ablation, which our own OBS arms produce natively; the fine-tune itself teaches us nothing |

## 3. Cannot reproduce (blocker stated; these stay as structural-gap / trajectory evidence)

| work | blocker |
|---|---|
| FlexCTC / TurboBias | decoder-internal score fusion — no hook behind a chat endpoint |
| UniverSLU; SFT-LALM SLU (2509.15389); CTI; Speech-MASSIVE baselines; XTREME-S encoders | parameter training (instruction-tuning / SFT / E2E); 2509.15389 also has no code |
| WHISMA; QA-driven Whisper prompting | trained aligner+LoRA / prefix-tuning + decoder access; no model code |
| SLUE-SQA-5 official; Spoken-SQuAD original; Su & Fung 2020; MeetingQA; MeeQA; QMSum trained baselines; HMNet | trained extractors/summarizers or second answering model; several with code never released (SLUE-SQA), no license (MeeQA), or unclear license (HMNet) |
| SpeechDPR; SpeechRAG | trained speech retrievers/adapters, no code — the family's only SUPPLY-sensitive lines, both unreachable (core tension, confirmed program-wide) |
| RECOVER / Siskos **literal** reproduction | no artifacts exist anywhere (GitHub zero-hit on both arXiv IDs); only the mechanism-delta transfer is possible — that *is* R4/R6 |
| CMT-LLM | trained projector (code exists, boundary verdict unchanged) |
| PlanRAG-Audio | code + self-built eval set unreleased (re-checked 2026-08-07); **standing re-check trigger** — if released, becomes the top Family E candidate |
| Interactive in-meeting speaker correction | live human feedback at inference |
| Trained SDM class (GLM-4-Voice, Freeze-Omni, Kimi-Audio, …) & reasoning-trained native audio (Gemini-2.5-NAT) | they are models/products, not methods; the closed ones aren't even weights-available |

Four of the lines above graduate into the P3 training-free analog track
rather than ending as gap records: T1 (SpeechDPR), T2 (SpeechRAG), T3 (the
zero-shot slot-filling line), T4 (FlexCTC/TurboBias, via R4's bias-list
extension) — designs in the reproduction plan §P3.

## 4. Improvement directions in the literature (what actually moved numbers, per family)

- **A (contextual ASR/entity):** three routes — (i) decoder-level biasing
  (FlexCTC/TurboBias; unreachable), (ii) evidence-into-prompt supply
  (Siskos; reachable, dose-response-proven), (iii) post-ASR
  retrieval-grounded correction (RECOVER/DeRAGEC/Pusateri; reachable
  class). ConEC's lesson: aggregate WER hides the effect — score
  per-entity-class.
- **B (SLU):** the entire published ladder is training (pipeline → E2E →
  instruction-tuned → SFT audio-LLM: 76.68 → ~90.3 IC). The only reachable
  published lever is transcript mediation (AIR-Bench cascade +9.9). Slot
  filling has **no zero-training number at all** — open floor.
- **C (spoken QA):** SUPPLY improvements come only from trained retrievers
  (SpeechDPR/SpeechRAG); USE improvements from trained extractors. The
  runnable AudioBench protocol is SUPPLY-insensitive by construction. The
  reachable-and-sensitive combination is unoccupied.
- **D (speech agentic):** floors only, no method papers yet. Published
  levers: pipeline-vs-E2E ≈ parity, one-shot prompting (+10–17pp — the
  family's only prompting ablation), full-schema-in-prompt. Complexity
  tiers (multi-intent/needle/correction/blending) are where everything
  collapses (92→42) and nothing has been tried.
- **E (meeting):** trained summarization plateaued on an
  evidence-insensitive metric; extractive QA needs trained heads;
  PlanRAG-Audio (frozen backbones + deterministic retriever) is the
  literature converging toward exactly our design point — still
  unreleased.
- **F (omnibus):** every step is a new trained model; cascade stays at or
  near the top throughout (87.8–89.3 band on VoiceBench; +20 on URO-Bench;
  BBA 66→92). No inference-time method has ever been submitted to any of
  the four.

## 5. Distilled exploration directions for this study (bucket-1 precedent × bucket-3 vacancy)

Ordered by evidence strength of the precedent; each maps to an axis and a
first probe. The plan's four-construct frame (agent construction / knowledge
construction / knowledge use / knowledge-utilization-driven agent
optimization) is the working vocabulary over these: directions 1 and 8 are
construct 1→4, directions 2–7 are constructs 2+3, and construct 4 is where
the fold-back (plan P4) aims the X probes:

1. **Self-cascade / transcript-mediation policies** (OBS→USE). Strongest
   multi-carrier precedent (BBA, AIR-Bench, URO-Bench, VoiceBench). Probe =
   R2/R3. Extension: *when* to mediate (see #8).
2. **Evidence dose/quality control in prompt** (SUPPLY). On-carrier
   dose-response precedent (Siskos). Probe = R4. Extension:
   entity-class-scoped dosing, budgeted evidence selection.
3. **Retrieval policy for tool schemas & context** (SUPPLY/ORG). Vacant on
   D carriers (only full-schema-in-prompt exists; VAB even ships a
   `single_tool_retrieval` category nobody has attacked). Probe grows out
   of R1+R5 carriers after P2.
4. **Uncertainty surfacing — sampled n-best/self-consistency in prompt**
   (OBS/USE). Off-carrier precedent (WCN-ICL 81% gap closure). Probe =
   R7.
5. **Retrieval-grounded self-correction loop** (USE). On-carrier preprint
   precedent (RECOVER). Probe = R6.
6. **Exemplar-retrieval ICL** (ORG). Fixed one-shot proven on-carrier
   (VAB +10–17pp); *retrieved* exemplars untried. Extension of R5.
7. **Prompt-only structured extraction (slot filling)** (USE).
   First-of-its-kind territory on SLURP (zero published zero-training
   numbers); official scorer on disk. Natural post-P2 probe.
8. **Condition-aware routing between direct and mediated paths** (OBS).
   The FDB-v3 reversal (cascade collapses on self-corrections, 0.176 vs
   0.588) plus the cascade advantage everywhere else implies the *choice*
   is input-dependent — a routing policy is itself an evidence-acquisition
   mechanism no paper has tried.

Directions 1–2 are the X-probe anchors (ablation-precedented, on-carrier);
3–8 are contribution space (bucket 3, unpopulated everywhere). All eight
stay inside prompt+audio→text; none require training, logits, or a second
answering LLM.

## 6. Wiki linkage

Published numbers per carrier + our to-be-filled rows:
`wiki/experiments/speech-aware-evidence-acquisition/published-baselines.md`
(umbrella). Update discipline: after each probe reads results (ledger row
first), fill the matching "ours" row in place, dated; the study repo's
receipts/MLflow remain the number authority — the wiki row carries only the
summary value + pointer.
