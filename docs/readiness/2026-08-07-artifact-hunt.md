# GitHub artifact hunt — all candidate lines, groups 1+2 (2026-08-07)

Status: DRAFT EVIDENCE, model-free (GitHub API reads + web fetches only).
Purpose (HANDOVER.md item 4): for every candidate line, does an open-source
implementation exist — official or third-party — plus any reproduction
report. Framing rule 6 is applied as three separate columns that must never
be conflated: **(a)** an artifact exists; **(b)** it reproduces the published
number; **(c)** it runs under our boundary. "confirmed-none" means a targeted
search (repo search and/or code search for the arXiv ID) returned zero
matches today; "not-re-searched" means group 1's finding was left standing.

## Corrections to group 1

Two group-1 "NONE found" assertions are **overturned** by this hunt:

1. **ConEC**: official repo exists — `huangruizhe/ConEC` (first author's
   account, created 2024-01, README @ `88440713d8b80dc4f19b225f6480237e78c379de`).
   Contents: per-call context materials (slides/press-release PDFs, extracted
   biasing lists, participant names) and corrected Earnings-21/22
   transcripts + wer_tags; baselines are stated to live in the icefall
   toolkit (decoder-level contextualization — still out of boundary). **No
   LICENSE file in the repo** — data-license unstated. This is very likely
   the upstream of our on-disk `conec` carrier (identity question for the
   owner/lock, not decided here).
2. **CMT-LLM**: official repo exists — `JiajunHe1025/CMT-LLM` (README @
   `1cfdbe236ffb33a28bf039cfc5b785ee5e1724a3`), with decode + finetune
   scripts (WavLM/Whisper encoder + Vicuna-7B, trained projector). Boundary
   verdict unchanged (NOT_READY — parameter training); artifact status (a)
   flips to yes. No LICENSE observed in README; not further verified.

Re-check requested by group 1: **PlanRAG-Audio remains unreleased** — zero
matching repositories today despite ACL Findings 2026 acceptance. Worth
re-checking again near the conference date.

## Matrix — group 1 lines (families A, C, E)

| line | (a) artifact exists | (b) reproduces published number | (c) runs under boundary | notes |
|---|---|---|---|---|
| ConEC | **YES (corrected)** — `huangruizhe/ConEC`, data+contexts; baselines via icefall | no reproduction report found | data yes / method baselines no (decoder-level) | no LICENSE file |
| RECOVER (arXiv:2603.16411) | NO — confirmed-none (zero GitHub references to the arXiv ID) | n/a | method would be boundary-compatible if reimplemented | reimplementation-from-paper is the only path |
| Siskos et al. (arXiv:2509.19567) | NO — confirmed-none | n/a | method boundary-compatible if reimplemented | same |
| FlexCTC / TurboBias | YES — NeMo merged PRs (not-re-searched) | no independent report found | NO (decoder-internal) | Apache-2.0 |
| Raghuvanshi et al. 2019 | NO (not-re-searched) | n/a | reimplementable | algorithm description only |
| DeRAGEC | YES — `solee0022/deragec` (inference + filtering scripts) | no reproduction report; repo ships outputs but no independent verification | **legally blocked: no LICENSE file** (all-rights-reserved default) — confirmed by root listing | 8 stars, no forks of substance |
| Pusateri et al. (arXiv:2409.06062) | NO (not-re-searched) | n/a | reimplementable | — |
| SLUE-SQA-5 official baseline | toolkit YES, **SQA code NO — re-confirmed** (`slue_toolkit/eval` contains ner/nel/da/sentiment/wer only) | n/a | official pipeline out of boundary anyway (trained DeBERTa extractor) | MIT toolkit |
| Spoken-SQuAD original | dataset repo only (not-re-searched) | n/a | no baseline code ever released | — |
| Su & Fung 2020 | NO (not-re-searched) | n/a | trained head anyway | literature ceiling F1 77.67 |
| HeySQuAD | YES — `yijingjoanna/HeySQuAD`, official only; no third-party (confirmed today) | fine-tuning command, no frozen-inference repro | training pipeline out of boundary | MIT |
| SpeechDPR / SpeechRAG | NO — confirmed-none (targeted repo search) | n/a | trained retrievers anyway | — |
| AudioBench harness | YES — `AudioLLMs/AudioBench` @ `85dcdb88c4…` (group 1 pin stands) | leaderboard numbers are self-published; no third-party reproduction report | YES (direct-prompting protocol) | CC-NC-variant code license caveat stands |
| QMSum / ZeroSCROLLS / HMNet / MeetingQA / MeeQA / MS-AMI | YES — commits pinned in group 1 | no boundary-compatible reproduction reports found | as classified in group 1 | — |
| PlanRAG-Audio | **NO — re-checked today, still none** | n/a | would be the closest architectural match if released | ACL Findings 2026 accepted |
| CMT-LLM | **YES (corrected)** — `JiajunHe1025/CMT-LLM` | no reproduction report | NO (trained projector) | license not observed |

## Matrix — group 2 lines (families B, D, F)

| line | (a) artifact exists | (b) reproduces published number | (c) runs under boundary | notes |
|---|---|---|---|---|
| SLURP official scorer | YES — on disk (`repos/slurp`) | scorer is the official metric implementation | YES (post-hoc scorer) | audio CC-BY-NC-4.0 |
| AIR-Bench | YES — `OFA-Sys/AIR-Bench` @ `983247666e2a25519b5c122810c2bcd91f26fd8d`, Apache-2.0 | publishes its own leaderboard numbers; judge pinned in README as gpt-4-0125-preview (paid) | YES for direct-prompting rows; deterministic scorer possible for closed label sets | data download via GitHub-issue link — weak distribution channel |
| UniverSLU | ESPnet-integrated (not deeply verified) | — | NO (fine-tuned) | — |
| Fine-tuned LALM SLU (2509.15389) | NO code | n/a | NO (SFT) | — |
| WHISMA | model code NO; SLU-GLUE/Spoken-Alpaca data via Google Drive | n/a | NO (trained aligner+LoRA) | — |
| QA-driven Whisper SLU (2406.15209) | NO code — confirmed-none | n/a | NO (prefix-tuning) | — |
| WCN-ICL (2401.02921) | NO code — confirmed-none | n/a | mechanism reachable as arm | — |
| Speech-MASSIVE | YES — `hlt-mt/Speech-MASSIVE` @ `c08453f622460f3eb3ccdcdf3b7b9a691c383eff`, Apache-2.0 | official baselines, self-published | protocol/scorer yes; methods no (trained) | data CC-BY-NC-SA-4.0 |
| MINDS-14 (Gerz baselines) | baseline code NO; data via PolyAI/HF | n/a | NO (trained MLPs); no canonical split | — |
| Audio2Tool | **placeholder only** — `RamitPahwa/Audio2Tool` = LICENSE (~Apache-2.0 text) + 123-byte README @ `90396465b6b63461ef4525deb57c9cfa22846118`; site repo exists; dataset on HF/disk | published numbers not independently reproduced; **eval scripts unreleased** — scorer must be reimplemented from the paper's deterministic metric definitions | YES (prompt-only protocol; our core literally among the published baselines) | paper-vs-disk license contradiction (CC-BY-4.0 vs CC-BY-NC-4.0) — owner flag |
| VoiceAgentBench | YES — `ola-krutrim/VoiceAgentBench` @ `d1efb7d4b71bed85534ce171460f8f2fb133a456` (full eval code) + HF dataset | self-published numbers | YES except GPT-4o-mini judge (paid → pin/replace) | Krutrim Community License v1.0: research OK, revocable, non-compete, India law |
| Full-Duplex-Bench-v3 | demo site only; eval code not located | n/a | partial (offline tool-call subset only) | dataset license unstated |
| MIST | release stated on project site (not verified) | n/a | mechanism reachable | — |
| VoiceBench | YES — `MatthewCYM/VoiceBench`, Apache-2.0, TACL 2026 | self-published leaderboard; no third-party reproduction report | YES; deterministic MCQ/rule tier needs no judge | pin at freeze |
| VoiceAssistant-Eval | YES — `mathllm/VoiceAssistant-Eval` (judge pipeline confirmed in repo), MIT | self-published | YES for in-scope subtasks; **open judge (gpt-oss-20b)** — the only paid-API-free judge precedent found | — |
| URO-Bench | YES — `Ruiqi-Yan/URO-Bench` @ `9e74bc04114b6aac3ebc4fe54633777b21136684`, MIT; HF data + 1k miniset | self-published leaderboard incl. cascade references | YES for basic-track speech→text subsets; judge pin/replace | 2025-08-03 data reconstruction — disk copy predates/postdates to be checked at freeze |
| Big Bench Audio | dataset YES (HF, MIT); **official eval-harness repo does not exist** — protocol lives in the HF blog post | Artificial Analysis' numbers not independently reproduced | YES (speech-to-text config; replace Claude judge with pinned open judge) | — |

## Reproduction reports — global finding

**Zero third-party reproduction reports were found for any candidate line in
either group.** The closest existing structures are the self-published,
submission-accepting leaderboards (AIR-Bench, VoiceBench, URO-Bench), which
verify nothing independently. The practical consequence, combined with the
group-2 survey verdict: under this study's boundary, "reproduce a prior" can
only mean (i) re-running a benchmark harness's prompt-only protocol against
its published numbers — available for B/D/F, including one same-model row
(Audio2Tool × Qwen-3-Omni-30B) — or (ii) reimplementing a method from its
paper with no artifact to check against — the only path available for every
method line in groups 1 and 2.
