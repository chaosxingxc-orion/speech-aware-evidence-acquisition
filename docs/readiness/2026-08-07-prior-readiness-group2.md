# Model-free prior-readiness survey — group 2 of 2 (families B, D, F)

Status: DRAFT EVIDENCE — produced by a model-free web survey (search + fetch of
primary sources, plus GitHub API reads for artifact status; no model touch, no
downloads beyond reading pages). This document does **not** pick the R1
baseline; the owner picks from the ranked evidence here plus group 1
(`2026-08-07-prior-readiness-group1.md`, families A/C/E).

Contract basis: `wiki/experiments/speech-aware-evidence-acquisition/2026-08-04-owner-consolidated-execution-contract.md`
§2 (speech-only scope), §3 (OBS/ORG/SUPPLY/USE separation). Framing basis: the
owner rules recorded in `docs/readiness/HANDOVER.md` — scope judged by content,
reproduction target = papers that *use* the carriers, per-carrier performance
trajectories with ablation-supported mechanism attribution (those trajectories
live in `2026-08-07-carrier-mechanism-map.md`; this file holds the per-line
readiness classification). Template basis:
`docs/readiness/2026-08-05-prior-readiness-memo.md` (not edited).

## Boundary rubric

Identical to group 1 (see that file's rubric section): prompt + audio bytes to
a frozen HTTP chat-completions endpoint (Qwen3-Omni via llama.cpp
llama-server), text back; no logits/decoder access, no training of any
parameter (SFT/LoRA/adapter/prefix/projector all excluded), no second
answering LLM; pinned deterministic tool-level retriever/judge allowed if
logged; gold/reference material never enters runtime.
`RUNNABLE_R1_FULL` / `RUNNABLE_AS_ARM` / `NOT_READY(reason)` as in group 1.

A distinction that matters more in this group than in group 1 (owner framing
rule 6): for families B/D/F the runnable artifact is usually the **benchmark
harness** (the dataset's own evaluation protocol), not a method. "Runnable"
below therefore means the *published evaluation protocol* is executable under
our boundary; whether any *method* that beat the floor is reachable is
recorded per line and consolidated in the mechanism map.

---

## Family B — SLU (intent classification / slot filling)

On-disk carriers: `slurp` (real+synth sub-splits, audio CC-BY-NC-4.0),
`speech-massive` (12 locales, CC-BY-NC-SA-4.0), `minds14` (14 locales,
CC-BY-4.0). SLURP's official scorer is already on disk (`repos/slurp`
evaluation scripts); `speech-massive` has an official Apache-2.0 repo.

| line | family | axis | runnable revision | license | boundary compatibility | scorer alignment | carrier we already hold | not-runnable reason |
|---|---|---|---|---|---|---|---|---|
| **SLURP multitask pipeline baseline** — Bastianelli et al., EMNLP 2020 (arXiv:2011.13205) | B | OBS/USE | `pswietojanski/slurp` (on disk at `repos/slurp`, incl. official evaluation scripts) — data + scorer, not the HerMiT NLU model | text CC-BY-4.0, audio CC-BY-NC-4.0; scorer repo on disk | NOT_READY as method; scorer directly reusable | direct — intent acc + SLU-F1 are the family's canonical metrics; official scorer on disk | `slurp` (direct) | pipeline = trained Multi-ASR + trained HerMiT NLU head; reference floor only (owner rule 2): IC 76.68→78.33, SLU-F1 69.53→70.84, gold-text bound 84.84/78.19, ASR WER 16.2 |
| **AIR-Bench foundation: intent classification on SLURP** — Yang, Xu et al., ACL 2024 main (arXiv:2402.07729) | B | OBS/USE | `OFA-Sys/AIR-Bench` @ `983247666e2a25519b5c122810c2bcd91f26fd8d` (inference + scoring scripts); data distributed via a GitHub-issue link (weak channel) | Apache-2.0 (repo README) | **RUNNABLE_R1_FULL** | indirect-but-deterministic-capable — 1k single-choice items from SLURP; published protocol uses gpt-4-0125-preview as judge, but a fixed label set admits a deterministic scorer | `slurp` (direct — AIR-Bench draws from it) | — (published zero-shot numbers to calibrate against: cascade Whisper+GPT-4 87.7%, Qwen-Audio-Chat 77.8%, Qwen-Audio-Turbo 56.4%, SpeechGPT 45.8%, BLSP 46.6%, SALMONN 36.7%, PandaGPT 28.5%, NExT-GPT 25.6%) |
| **UniverSLU** — Arora et al., NAACL 2024 (arXiv:2310.02973) | B | OBS/USE | ESPnet-integrated release (exact path not re-verified this session) | ESPnet Apache-2.0 | NOT_READY | direct (intent acc ~90.3 on SLURP — search-attributed, primary table not re-fetched) | `slurp` (direct) | multi-task instruction fine-tuning of Whisper-medium — parameter training |
| **Fine-tuned LALM SLU** — arXiv:2509.15389, ICASSP 2026 | B | OBS/USE | NONE — no code released | UNKNOWN (no repo) | NOT_READY | direct — SLURP IC 88.13/SLU-F1 76.75; Speech-MASSIVE-FR 87.39/74.86 after SFT of Qwen2-Audio-7B-Instruct | `slurp`, `speech-massive` (both direct) | SFT of the audio-LLM; also no artifact |
| **WHISMA** — Li et al. (Toshiba Europe), arXiv:2408.16423 | B | OBS/USE | NONE for model code; Spoken-Alpaca + SLU-GLUE data via Google-Drive links only | UNKNOWN | NOT_READY | direct-ish — zero-shot SLURP slot-filling SLU-F1 63.1/63.3 vs ZS-Whisper-SLU 50.0, supervised ref 69.9 | `slurp` (direct) | trained modality aligner + LoRA on Llama-3-8B; no code |
| **QA-driven zero-shot SLU via Whisper prompting** — Li, Keizer, Doddipatla, Interspeech 2024 (arXiv:2406.15209) | B | OBS/USE | NONE — no code found | UNKNOWN | NOT_READY | direct-ish (SLURP SLU-F1, +40.7 abs over the zero-shot benchmark it defines) | `slurp` (direct) | prefix-tuning (trained soft prompts) + Whisper decoder-side integration — both outside a chat-completions boundary |
| **WCN-in-prompt in-context learning** — Amazon Alexa AI / UW / NTU, ICASSP 2024 (arXiv:2401.02921) | B | USE/SUPPLY | NONE — no code found | paper only | RUNNABLE_AS_ARM | indirect — evaluated on NMSQA (SQA F1/EM) and ATIS (intent acc), not on our carriers; mechanism is the point: 1-best F1 64.5 → WCN+1-shot 70.5 vs oracle 76.2 (closes 81% of the gap), zero training | none (ATIS/NMSQA not held); mechanism transfers to `slurp`-style tasks | as published needs ASR lattice→WCN (Emformer-RNNT+Kaldi) and GPT-3.5 as the answering LLM; under our boundary the frozen core must produce its own sampled n-best and answer itself — an analogous arm, not a reproduction |
| **Speech-MASSIVE baselines** — Lee et al., Interspeech 2024 (arXiv:2408.03900) | B | OBS/USE | `hlt-mt/Speech-MASSIVE` @ `c08453f622460f3eb3ccdcdf3b7b9a691c383eff` (official; Apache-2.0, Beomseok Lee 2024) | code Apache-2.0; data CC-BY-NC-SA-4.0 | NOT_READY as method; protocol/scorer reusable | direct — intent acc + slot micro-F1; note metric-definition mismatch vs SLU-F1 | `speech-massive` (direct) | all baselines are trained (cascaded Whisper+mT5 fine-tunes or E2E Whisper); "zero-shot" in the paper means cross-lingual transfer of a trained model, not prompting. Floor: cascaded X-lingual IC avg 69.10/slot 43.15 → full FT 83.04/61.21; gold-NLU bound 86.73 |
| **MINDS-14 baselines** — Gerz et al. 2021 (arXiv:2104.08524) | B | OBS/USE | NONE for baseline code; data via PolyAI/HF | data CC-BY-4.0 | NOT_READY | weak — accuracy over 3-fold random 60/40 splits, **no canonical split**; cross-paper comparability poor | `minds14` (direct) | trained MLP heads over frozen sentence encoders (+MT); no prompting baseline exists |
| **XTREME-S (minds14 subset)** — Conneau et al., Interspeech 2022 (arXiv:2203.10752) | B | OBS | XTREME-S HF benchmark scripts | Apache-2.0 | NOT_READY | weak (same split fragility) | `minds14` (direct) | fine-tuned w2v-BERT/mSLAM encoders |

**Family B narrative.** The family's floor papers and its entire
trained-method trajectory (CTI 82.93/71.12 → fine-tuned Qwen2-Audio
88.13/76.75 → UniverSLU ~90.3 IC on SLURP) are uniformly out of boundary —
every step is parameter training, and the two zero-shot-branded slot-filling
lines (WHISMA, QA-driven Whisper prompting) still train aligners or soft
prompts. What *is* fully runnable is the **AIR-Bench SLURP intent protocol**:
audio + fixed-choice prompt → text, published zero-shot numbers for eight
systems to sanity-check against, Apache-2.0 harness with a pinnable commit,
and a deterministic scorer possible because the label set is closed (the
published GPT-4-judge step is only needed for free-form answer alignment). It
is also the only Family B line that measured the **cascade-vs-direct
contrast** on our carrier (87.7 vs 77.8): the one ablation-supported mechanism
signal on SLURP reachable under our boundary. Slot filling — the metric the
SLURP scorer on disk is strongest for — has **no published zero-training
number at all**: the zero-shot SF trajectory (50.0 → 63.3 SLU-F1) is entirely
trained-adapter territory, and the supervised ceiling is 78.19 (gold text) /
76.75 (best SFT audio-LLM). A prompt-only SLURP slot-filling number would be
literally the first of its kind — that absence is itself structural-gap
evidence, but it also means Family B offers no independent method paper we
could reproduce under boundary; the reproducible object is the protocol plus
the reference floors. `speech-massive` and `minds14` inherit the same
picture with thinner literatures (and minds14 adds a no-canonical-split
comparability problem), so SLURP is the family's anchor carrier.

---

## Family D — speech agentic / tool calling

On-disk carriers: `audio2tool` (CC-BY-NC-4.0 per disk/lock; ~36.4k wav, 152
tools, 8 tiers), `voiceagentbench` (Krutrim Community License; en+6 Indic),
plus `full-duplex-bench-v3` (disfluent acted dialogues → tool calls; dataset
license unstated) as an adjacent on-disk carrier.

| line | family | axis | runnable revision | license | boundary compatibility | scorer alignment | carrier we already hold | not-runnable reason |
|---|---|---|---|---|---|---|---|---|
| **Audio2Tool introductory baselines** — Rivian & VW Group Technologies, arXiv:2604.22821 (submitted Interspeech 2026) | D | USE/SUPPLY | official repo `RamitPahwa/Audio2Tool` is a **placeholder** (LICENSE + 123-byte README @ `90396465b6b63461ef4525deb57c9cfa22846118`, no code); site `audio2tool.github.io`; "release contingent on acceptance"; dataset itself on HF (on disk) | dataset cc-by-nc-4.0 (disk/lock); paper page shows CC-BY-4.0 — contradiction flagged for owner; placeholder repo LICENSE ≈ Apache-2.0 | **RUNNABLE_R1_FULL** (protocol; scorer must be reimplemented from the paper's deterministic metric definitions — Tool Accuracy / Exact Match / Slot-F1 over on-disk `tool_call` ground truth) | direct — deterministic metrics, no judge | `audio2tool` (direct) | — (**the paper's own SpeechLM baselines include Qwen-3-Omni-30B — our exact frozen core: Tier1 92.4% → Tier3 74.7% → Tier8 41.7%.** The single strongest calibration anchor found in R0.1: published numbers for our own model on an on-disk carrier under a prompt-only protocol) |
| **VoiceAgentBench introductory baselines** — Krutrim AI Labs, arXiv:2510.07978 | D | USE/SUPPLY | `ola-krutrim/VoiceAgentBench` @ `d1efb7d4b71bed85534ce171460f8f2fb133a456` (full eval code) + HF dataset (on disk) | Krutrim Community License v1.0 (code and data): research use permitted, revocable, non-compete, India law — non-OSI, owner-flagged | **RUNNABLE_R1_FULL** (protocol), with judge caveat | direct-ish — Tool Selection / Tool-Call Structure / Parameter Filling; GPT-4o-mini used as semantic-variation judge (paid → must pin an open judge or restrict to deterministic components) | `voiceagentbench` (direct) | — (published anchors: pipelines Whisper+Llama3-70B EN-PF 60.64/Indic 39.21 vs SpeechLMs KimiAudio 57.57/28.21, Qwen2.5-Omni-7B 1.70/0.29 format collapse; ablations: one-shot prompting +10–17pp on complex tasks — a reachable mechanism; ASR errors ≥24pp Indic degradation) |
| **Full-Duplex-Bench-v3** — Lin, Chen, Chen, Lee (NTU/NVIDIA), arXiv:2604.04847 | D | OBS/USE | demo site only (`daniellin94144.github.io/FDB-v3-demo`); eval-code release not located this session | dataset license UNSTATED (disk finding stands); paper header CC-BY-SA-4.0 | RUNNABLE_AS_ARM | partial — Tool-Selection F1 + argument accuracy transfer; Pass@1/latency/turn-taking dimensions are full-duplex-only and do not apply to our non-duplex core | `full-duplex-bench-v3` (direct) | all six published systems are streaming/duplex products (GPT-Realtime 0.600 Pass@1 … cascaded Whisper→GPT-4o→TTS 0.450); our core cannot enter the duplex protocol — only the offline tool-call subset is scoreable. Key published mechanism reversal: on self-correction disfluencies the cascade collapses (0.176) vs native duplex (0.588) |
| **MIST** — Chen, Zhang, Peng, Yu, Jo (Columbia/SNU), arXiv:2605.06897 | D | SUPPLY/USE | release stated at `billyzhang24kobe.github.io/mist-smarthome` (not verified this session) | UNKNOWN | RUNNABLE_AS_ARM (mechanism evidence; carrier not held) | indirect — Execution Match / Exact Match on its own 10k-conversation smart-home dataset | none (own dataset) | not a held carrier; relevance is the mechanism datapoint: full-tool-schema-in-prompt, zero training, Qwen3-Omni 59.86% ExecMatch vs Gemini-2.5-Pro 79.53% — a second published prompt-only Qwen3-Omni anchor |

**Family D narrative.** This family inverts group 1's problem. Families A/C/E
had method papers with no artifacts; D has **benchmark harnesses whose
introductory baselines are themselves prompt-only runs of frozen models** —
the published protocol *is* our access mode, and Audio2Tool even publishes
numbers for our exact core (Qwen-3-Omni-30B) across all eight tiers, which no
other line in either group does. Both carriers' later-user literature is
empty (Audio2Tool April 2026, VoiceAgentBench October 2025; citing papers so
far are successor benchmarks, not methods), so the owner's "papers that got
BETTER numbers on this carrier" question currently has a null answer — the
trajectory has a floor and no steps. The reachable-mechanism evidence inside
the family is thin but concrete: VoiceAgentBench's own ablation shows
one-shot prompting is worth +10–17pp on complex tasks, and the
cascade-vs-direct contrast replicates here (pipelines ≥ SpeechLMs on both
carriers) with FDB-v3 providing the important counter-case (cascades collapse
on self-correction disfluency). Blockers to record honestly: Audio2Tool's
eval scripts are unreleased (deterministic metrics make reimplementation
low-risk, but it is still reimplementation, and the paper-vs-disk license
contradiction needs owner review); VoiceAgentBench's judge is a paid model
(substitutable) and its license is non-OSI and revocable. Reproducing the
Audio2Tool Qwen-3-Omni-30B row under our GGUF/llama.cpp runtime would
additionally measure quantization/runtime drift against their (presumably
HF/bf16) inference — that is exactly the pipeline-calibration content R1 was
meant to deliver, without importing any "did we understand the method"
confound.

---

## Family F — assistant omnibus

On-disk carriers: `voicebench` (Apache-2.0), `voiceassistant-eval` (MIT;
8/13 subtasks in-scope), `uro-bench` (MIT; 38/40 subtasks in-scope),
`big-bench-audio` (MIT).

| line | family | axis | runnable revision | license | boundary compatibility | scorer alignment | carrier we already hold | not-runnable reason |
|---|---|---|---|---|---|---|---|---|
| **VoiceBench** — Chen et al., TACL 2026 (arXiv:2410.17196) | F | OBS/USE | `MatthewCYM/VoiceBench` (active; pin at freeze) | Apache-2.0 | **RUNNABLE_R1_FULL** for the speech→text protocol | mixed by subset: gpt-4o-mini judge for alpacaeval/commoneval/wildvoice/sd-qa (paid → pin/replace); **deterministic tier exists** — openbookqa/mmsu are MCQ, ifeval/advbench/bbh rule-scored | `voicebench` (direct) | — (leaderboard anchors: top Nemotron-3-Nano-Omni 89.39; **cascade Whisper-v3+GPT-4o 87.80 at rank 4**; GPT-4o-Audio 86.75; Kimi-Audio 76.91; Qwen2-Audio 55.80; all entries are trained models or cascades — no inference-time method has ever been submitted) |
| **VoiceAssistant-Eval** — arXiv:2509.22651 | F | OBS/USE | `mathllm/VoiceAssistant-Eval` (code confirmed released: judge pipeline + scorers) | MIT | RUNNABLE_R1_FULL for in-scope listening/speaking content dimensions | notable — content judge is **gpt-oss-20b, an open, pinnable model** (precedent for our no-paid-API constraint); UTMOS/speaker-sim/TTS-consistency dimensions don't apply to a text-out core | `voiceassistant-eval` (direct; 8/13 subtasks in-scope per content verification) | — (anchors: GPT-4o-Audio listening 39.78/speaking 51.26; Qwen2.5-Omni 33.56/41.27; 20/22 models better at speaking than listening) |
| **URO-Bench** — Yan et al. (SJTU X-LANCE), arXiv:2502.17810 | F | OBS/USE | `Ruiqi-Yan/URO-Bench` @ `9e74bc04114b6aac3ebc4fe54633777b21136684` (full 4-step pipeline; HF data incl. 1k miniset) | MIT | RUNNABLE_R1_FULL for basic-track speech→text subsets (S2S/paralinguistic-generation legs N/A for a text-out core) | LLM-judge based (scoring adapted from VoiceBench → paid judge, pin/replace); ClothoEval-en/MuChoEval-en are out-of-scope non-speech (disk verdict) | `uro-bench` (direct) | — (anchors EN-basic: cascade Whisper+GPT-4o 89.33 > GPT-4o-Audio 87.48 > best open E2E SDM GLM-4-Voice 69.09 — a 20-point cascade-vs-native gap) |
| **Big Bench Audio** — Artificial Analysis (HF dataset + blog, Dec 2024) | F | USE | HF `ArtificialAnalysis/big_bench_audio`; **no official eval-harness repo exists** — protocol documented in the HF blog (Whisper-transcribe + Claude-3.5-Sonnet binary judge) | MIT | RUNNABLE_R1_FULL (speech-to-text config is exactly our mode; short fixed answers admit a deterministic or open-judge scorer) | direct-ish — binary correct/incorrect on 1k BBH items | `big-bench-audio` (direct) | — (anchors: GPT-4o text 92% vs GPT-4o-Realtime speech-to-speech 66% vs Whisper→GPT-4o pipeline ≈ text level; Gemini-2.5 Native-Audio-Thinking closed the gap to 92% in Oct 2025 — by training, not by any inference-time method) |
| **Trained SDM lines on these carriers** (GLM-4-Voice, Freeze-Omni, LLaMA-Omni, SLAM-Omni, Kimi-Audio, MiniCPM-o, Step-Audio…) | F | — | various official repos | various | NOT_READY | — | all four carriers | each "step up" on these leaderboards is a new trained model; none is a method applicable to a frozen core — structural-gap bucket in the mechanism map |

**Family F narrative.** All four carriers share one shape: the protocol is
direct prompting (literally our access mode), the harnesses are genuinely
open (two MIT, one Apache-2.0, one MIT dataset with a documented protocol),
and **every published performance step on every one of them comes from
training a new model** — across VoiceBench's full leaderboard history,
URO-Bench's tracks, VoiceAssistant-Eval's 22 systems, and Big Bench Audio's
timeline, not a single inference-time method (prompting strategy, retrieval,
self-correction, evidence supply) has ever been evaluated. Combined with the
same finding on Families B and D, this is the survey's strongest
structural-gap statement: the entire mechanism class this study proposes to
occupy is unrepresented on all seven omnibus/agentic carriers we hold. The
recurring published mechanism signal is again cascade-vs-native (Big Bench
Audio's 66→~92 is the cleanest, with an explicit protocol; URO-Bench +20pts;
VoiceBench rank-4), which under our boundary maps onto a *self-cascade* arm
(the frozen core transcribes, then answers from its own transcript) — a
reachable, ablation-precedented arm design. Judge dependency is the family's
main reproduction caveat: three of four carriers used paid judges
(gpt-4o-mini / GPT-4-class / Claude), so literal number reproduction is
blocked by the =0 paid-API budget; the boundary-clean options are the
deterministic subsets (VoiceBench MCQ/rule tier), the open-judge precedent
(VoiceAssistant-Eval's gpt-oss-20b), or a pinned local judge with a
divergence note. For a text-out core, the speaking/S2S quality dimensions
(UTMOS, speaker similarity) are out of protocol scope and must be declared
N/A rather than silently dropped.

---

## Cross-family summary (group 2)

| family | lines assessed | RUNNABLE_R1_FULL | RUNNABLE_AS_ARM | NOT_READY | closest line |
|---|---|---|---|---|---|
| B — SLU | 10 | 1 (AIR-Bench SLURP-IC protocol) | 1 (WCN-ICL mechanism) | 8 | AIR-Bench SLURP-IC — runnable harness + published zero-shot numbers + the only on-carrier cascade-vs-direct ablation; slot-filling has no zero-training prior at all |
| D — speech agentic | 4 | 2 (Audio2Tool protocol, VoiceAgentBench protocol) | 2 (FDB-v3 subset, MIST mechanism) | 0 | **Audio2Tool** — publishes our exact core's numbers (Qwen-3-Omni-30B, 8 tiers) under a prompt-only protocol with deterministic metrics; blockers: eval scripts unreleased, NC-license contradiction |
| F — omnibus | 5 | 4 (VoiceBench, VoiceAssistant-Eval, URO-Bench, Big Bench Audio protocols) | 0 | 1 (trained-SDM class) | VoiceBench deterministic tier (MCQ/rule subsets need no judge) + Big Bench Audio (cleanest cascade-vs-native ablation); VoiceAssistant-Eval contributes the open-judge precedent |

Verdict on the group-1 open finding ("no candidate ships a runnable artifact
that reproduces its published number"): for families B/D/F the finding
**splits**. Method papers: confirmed — still zero runnable method artifacts
(WHISMA, prefix-tuning SLU, WCN-ICL, MIST aside, ship no code or train
parameters). Benchmark harnesses: **refuted** — four-plus harnesses are
runnable under our boundary, publish the numbers they report, and one
(Audio2Tool) publishes numbers for our exact frozen core on an on-disk
carrier. Consequence for the R1 re-plan options sketched in HANDOVER.md:
option 2 (official scorer + our arm vs published numbers) is now concretely
enabled, and the Audio2Tool × Qwen-3-Omni-30B row upgrades it — reproducing a
published number with the same model under our GGUF runtime isolates
pipeline/quantization drift with no method-interpretation confound. The owner
decision should weigh this against options 1/3/4 with both groups in hand.
