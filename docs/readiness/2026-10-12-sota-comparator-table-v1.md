# SOTA comparator table v1 (owner decision 273 A): SLURP, Audio2Tool, Earnings-21, Earnings-22

Written 2026-10-12 by Claude Opus 5.5 (survey agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/sota-comparator-table`. This is a survey record. It is model-free: no model, server, encoder, scorer or GPU was
contacted, and nothing was written under the data root. Web access was used only to read published papers, model
cards and vendor pages. Machine-readable twin: `docs/readiness/2026-10-12-sota-comparator-table-v1.json`
(62 entries, schema `saea-sota-comparator-table-v1`).

**What this record is not.** It makes no SOTA claim. The owner's goal ("reach or exceed industry SOTA on several
tasks", 2026-10-09) needs this table before any such claim. Every study number below is quoted from a sealed read
and is development evidence under owner decisions 28 and 86, not a test claim. The study files are cited, not
altered.

## 0. How to read the table

- **Training regime**, one of: *fine-tuned on the task data*; *instruction-tuned general model zero-shot*;
  *training-free control of a frozen model* (ours); *cascade ASR+LLM*; plus, for ASR, *general-purpose ASR not
  trained on the task data*, and *oracle upper bound* (gold-transcript input or post-hoc substitution).
- **Claim classes** the owner can choose from: **A**, against direct-call baselines of the same frozen core (paired,
  same harness); **B**, against published training-free, zero-shot or prompt-only systems; **C**, against published
  fine-tuned SOTA.
- **Status.** VERIFIED: I read the number in the primary source (the paper's table, the model card, or the paper
  that reports it) on 2026-10-12. **UNVERIFIED**: I could not confirm it from a primary source in this pass; the
  reason is given. STUDY-OWN: quoted from the cited study file. Two hosts were unreachable from this machine
  (huggingface.co, and intermittently arxiv.org), so every Open ASR Leaderboard per-dataset value is UNVERIFIED.
- **Our core** throughout: Qwen3-Omni-30B-A3B-Instruct, Q4_K_M GGUF on llama.cpp, bf16 mmproj, behind an API-shaped
  boundary, zero parameter updates (the Thinking variant appears once, in the TRAIN Fold B bare-core read).
- Umbrella literature ids reused: `OMR-ARXIV-2604.22821` (Audio2Tool, `wiki/survey/registry/official-metadata-receipts-v1.jsonl`)
  and `aclanthology:2024.lrec-main.328` (ConEC, `proposal-citation-verification-2026-08-16-papers.jsonl`). No other
  paper below has an umbrella registry record yet. The umbrella living page
  `wiki/experiments/speech-aware-evidence-acquisition/published-baselines.md` already holds most Earnings and
  Audio2Tool rows; this record re-checks them against the primary sources and adds the SLURP fine-tuned and
  speech-LLM lines.

## 1. Headline per task

| task | metric (official scorer) | best published, class C (fine-tuned) | best published, class B (zero-shot / prompt-only / training-free) | ours (best on file) | class A (vs the same core, direct) |
| --- | --- | --- | --- | --- | --- |
| SLURP | intent acc / SLU-F1, `evaluate.py` | UniverSLU-14 **90.3 / 79.5** (NAACL 2024); TCPGen 88.9 / **79.5**; NeMo Conformer 90.14 / 82.27 UNVERIFIED (split not stated) | intent only: ChatGPT 0-shot on gold text **79.25**; ASR -> ChatGPT 10-shot 72.89. **No zero-shot audio-LLM SLU-F1 with the official script exists** | composed v2.2 + v4g, 3,010-row test sample: **82.36 / 66.65** (post-stratified) | DEV-2000-ADDED v2.0 plan vs bare: **+14.9 intent / +27.3 SLU-F1** (paired); Fold B lock vs bare Instruct +10.00 / +30.85 (cross-flight) |
| Audio2Tool | tool acc / exact match, official `metrics.py` | **none published** (every Table 3 row is zero-shot) | same core Qwen3-Omni-30B: tool **69.19** (8-tier mean), EM 20.71 (tiers 2-8); best EM tiers 2-8: Whisper v3 + Gemma 27B **26.79** | direct 62.03 tool / 18.86 EM(2-8); dual-store system 58.43 / **24.37** (not adopted) | system vs direct: tool -3.60, exact +4.05 [+2.96, +5.17] (paired; guard failed) |
| Earnings-21 | corpus WER, Whisper normaliser; ConEC PERSON entity WER | ConEC zipformer + real context (segmented): WER 10.29, PERSON 39.8 | Whisper large-v2 **9.7** (whole file); whisper-large-v3 9.71 UNVERIFIED; ConEC Whisper large (segmented) 7.98 / PERSON **28.9** | bare core **8.200**; KC-E1f PERSON **18.75** (replicated 18.86) at WER 8.154 | KC-E1f vs bare: PERSON -3.74 pp [CI90 2.65, 4.86], replicated |
| Earnings-22 (ESB short-form test) | corpus WER, Whisper normaliser | NeMo fine-tuned Qwen3-Omni 8.89 UNVERIFIED | Nemotron 3 Nano Omni **9.66**; same core 9.79 UNVERIFIED / **12.3** (Nemotron Table 8) | bare 15.94; with the 2-s silence tail **9.24** (second and last test read) | tail vs bare -6.70 [CI90 -7.04, -6.38] on the same rows (an OBS media convention) |

The short version: on **SLURP intent** our sampled-test number sits above every published prompt-only line and every
trained pipeline of the dataset paper, and about 6 to 8 pp under the fine-tuned speech models. On **SLURP SLU-F1** we
are 4.19 pp under the dataset paper's best trained pipeline and 10 to 13 pp under fine-tuned SOTA, and no
zero-shot comparator exists. On **Audio2Tool**, which has no fine-tuned lines, we are 7 pp under the paper's own
number for the same core on tool accuracy. The dual-store system is above that number on exact match over tiers
2-8 and below the best cascade. On **Earnings-21** the bare core already beats every verified zero-shot whole-file
WER, and KC-E1f beats the published PERSON rows except the oracle. On **Earnings-22** only the tail-convention read
reaches the same-model published band.

## 2. SLURP

### 2.1 Published lines

| system | regime | split | intent % | SLU-F1 % | source | status |
| --- | --- | --- | ---: | ---: | --- | --- |
| Gold transcripts + HerMiT | fine-tuned NLU, **oracle text** | test 13,078 | 84.84 | 78.19 | arXiv:2011.13205 T7-8 | VERIFIED |
| Multi-SLURP ASR + HerMiT | fine-tuned pipeline | test | 78.33 | 70.84 | arXiv:2011.13205 T7-8 | VERIFIED |
| Google ASR + SF-ID | fine-tuned NLU on commercial ASR | test | 72.06 | 64.02 | arXiv:2011.13205 T7-8 | VERIFIED |
| CTI (Seo et al., ICASSP 2022) | fine-tuned E2E | test | 82.93 | 71.12 | arXiv:2104.07253 T2 | VERIFIED |
| HuBERT-large, partially fine-tuned (Wang et al.) | fine-tuned E2E | official test | 89.38 | 78.43 ("SF F1") | arXiv:2111.02735 | VERIFIED values; metric identity with SLU-F1 UNVERIFIED |
| E2E SLU + TCPGen + SPB (Sun et al., ICASSP 2023) | fine-tuned E2E | official test | 88.9 | 79.5 | arXiv:2210.16554 T2 | VERIFIED |
| UniverSLU-14, task specifier (NAACL 2024) | fine-tuned Whisper multi-task | test | **90.3** | **79.5** | arXiv:2310.02973 T3-4 | VERIFIED |
| UniverSLU-3 (Table 6) | fine-tuned Whisper multi-task | test | 90.4 | 80.4 | arXiv:2310.02973 T6 | UNVERIFIED (row label lost in PDF text) |
| LauraGPT (as reported by UniverSLU) | multi-task trained speech LLM | test | 87.87 | 73.45 | arXiv:2310.02973 T4 | VERIFIED (reported by others) |
| SFT Qwen2-Audio-7B-Instruct, 100 % speech | fine-tuned speech LLM | test 13,078 | 88.13 | 76.75 | arXiv:2509.15389 T2 | VERIFIED |
| same paper, text-only fine-tune scored on speech / oracle text | fine-tuned | test | 83.60 / 91.29 | 72.07 / 85.93 | arXiv:2509.15389 T2 | VERIFIED |
| NeMo `slu_conformer_transformer_large_slurp` (127M, real + synthetic train) | fine-tuned E2E | **not stated** | 90.14 | 82.27 | NGC model card | **UNVERIFIED** (split not stated; 82.27 vs 76.89 column assignment inferred) |
| ChatGPT, 0-shot prompt | zero-shot, **oracle text**, 60 intents | test | 79.25 | -- | arXiv:2305.13512 T1 | VERIFIED |
| ASR -> ChatGPT, 10-shot (20-shot 73.96) | cascade ASR+LLM, few-shot | test | 72.89 | -- | arXiv:2305.13512 T5 | VERIFIED |
| ChatGPT slot filling, 10-30 shot | prompt-only, oracle text | test | -- | slot F1 12.03-13.35 (not SLU-F1) | arXiv:2305.13512 T4 | UNVERIFIED (Table 4 not re-read) |
| SALMONN (activation-tuned) | instruction-tuned, task untrained | SLURP probe | -- | slot-value accuracy 0.41 (cascade reference 0.46) | arXiv:2310.13289 T3(b) | VERIFIED; different metric |
| WHISMA + MR | SLU fine-tuned speech LLM, unseen slot types | held-out slot split | -- | 63.3 on unseen slots | arXiv:2408.16423 T3 | VERIFIED; not the standard protocol |

Checked and absent: the Qwen3-Omni technical report (arXiv:2509.17765) reports no SLURP, Earnings or Audio2Tool
number (its only function-calling benchmark is BFCL-v3). The Qwen2.5-Omni report (arXiv:2503.20215) could not be
fully downloaded, so its absence of a SLURP row is UNVERIFIED. The repo's earlier note that Qwen2.5-Omni scores 75.5
on AIR-Bench's 4-way multiple-choice SLURP probe is a different task and metric and is not used here.

### 2.2 Our numbers

| our row | population | intent % | SLU-F1 % | source |
| --- | --- | ---: | ---: | --- |
| composed v2.2 + v4g (review-off COMP-1b), 2.00 contacts per row | signed test **sample**, 3,010 recordings / 682 prompts / 58 of 59 intents, post-stratified natural mixture (raw 83.16 / 66.30; span-F1 raw 58.38; scenario 87.97, action 85.71 raw per-row) | **82.36** | **66.65** | `docs/results/2026-10-10-slurp-milestone-successor2-composed-test-sample-read.md` |
| COMP-1b (successor 1) | same sample | 82.82 | 64.98 | same, section 3.1 |
| PLAN v2.0 (successor 1) | same sample | 77.02 | 64.18 | same |
| composed (NX R5) | DEV-2000-ADDED, 1,000 devel recordings | not printed | 67.18 | `docs/results/2026-10-10-slurp-nx-r5-composed-dev2000-added-read.md` |
| bare core -> v2.0 plan (paired) | DEV-2000-ADDED | 61.7 -> 76.6 | 38.09 -> 65.40 | `docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md` |
| bare Instruct / bare Thinking / lock v2.2 + v4g (Instruct) | TRAIN Fold B, n 1,080 | 72.41 / 76.76 / 82.41 | 33.49 / 45.39 / 64.34 | `docs/results/2026-10-12-slurp-266e-thinking-vs-instruct-bare-core-read.md` |

### 2.3 Comparability

The apples-to-apples claim for a training-free control plane around the frozen Q4_K_M core is narrow:

1. **Population.** Every published row is the full official test split (13,078 recordings). Ours is a one-shot
   3,010-row sample with 58 of 59 intents, post-stratified to the population intent shares. It has CIs on deltas
   only, not on levels. A full-split read would need a new owner allowance.
2. **Metric.** We run the unmodified official `evaluate.py`, so intent (scenario_action) accuracy and SLU-F1 are the
   same definitions as SLURP Tables 7-8, TCPGen, UniverSLU and the Qwen2-Audio SFT paper. The ChatGPT rows use a
   60-intent closed list on text; SALMONN and the ChatGPT slot rows use other metrics.
3. **Input.** The gold-HerMiT, ChatGPT 0-shot and SFT-oracle rows read oracle transcripts. They are upper bounds,
   not peers.
4. **Regime.** No published zero-shot audio model reports official-script SLURP SLU-F1. The 2026-09-04 audit
   (`docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md` section 2.1) reached the same finding, and
   this pass did not change it. Our row would be the first of its kind, which also means class B has no SLU-F1
   target.
5. **Knowledge.** Our system reads TRAIN-derived knowledge (exemplars, slot stores, a vote table) at run time. That
   is training-free but not data-free. A class-B claim must say so, because the ChatGPT rows used at most 30
   in-context examples.

### 2.4 Gaps by claim class (ours = composed, test sample, post-stratified)

| class | comparator | intent gap pp | SLU-F1 gap pp |
| --- | --- | ---: | ---: |
| A | v2.0 plan vs bare core, DEV-2000-ADDED, paired | +14.9 [+11.8, +18.0] | +27.3 [+24.0, +30.5] |
| A | composed vs PLAN on the test sample, paired (context comparator) | +5.34 [+3.67, +6.97] | +2.46 [+0.88, +3.96] |
| A | lock vs bare Instruct, Fold B, cross-flight arithmetic | +10.00 | +30.85 |
| B | ChatGPT 0-shot, oracle text | +3.11 | no counterpart |
| B | ASR -> ChatGPT 10-shot | +9.47 | no counterpart |
| C | Google / SF-ID (weakest trained pipeline) | +10.30 | +2.63 |
| C | Multi-SLURP / HerMiT (dataset paper's best audio) | +4.03 | **-4.19** |
| C | CTI | -0.57 | -4.47 |
| C | SFT Qwen2-Audio-7B | -5.77 | -10.10 |
| C | TCPGen | -6.54 | -12.85 |
| C | UniverSLU-14 (best verified) | **-7.94** | **-12.85** |
| C | NeMo Conformer (UNVERIFIED split) | -7.78 | -15.62 |
| oracle | gold transcripts + HerMiT | -2.48 | -11.54 |

A defensible SLURP sentence today would be class A, plus class C against the dataset paper's pipelines on intent
only, carried with every caveat above. "SOTA" in the usual sense (class C, fine-tuned E2E) is 8 pp away on intent
and 13 pp away on SLU-F1. As every headroom note on file says, the remaining distance is entities.

## 3. Audio2Tool (arXiv:2604.22821, umbrella id `OMR-ARXIV-2604.22821`)

### 3.1 Published lines (Table 3, read in full from the v2 PDF)

Every row is **zero-shot** ("We evaluate zero-shot tool calling"). The paper reports no fine-tuned system, so
**class C is empty**. Groups: SpeechLMs on audio; Whisper v3 -> text LLM cascades; and an **oracle** block (Qwen3
1.7B/4B/8B, Gemma 3 12B) where "Whisper transcripts are replaced with ground-truth queries", with tier 8 not
evaluated. Tier-1 EM is printed equal to Acc. The means are computed here from the per-tier values.

| system | regime | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | tool mean (8) | EM mean (T2-8) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Qwen-3-Omni-30B (same core)** | zero-shot SpeechLM | 92.4 | 84.6 | 74.7 | 33.4 | 90.6 | 81.5 | 54.6 | 41.7 | **69.19** | 20.71 |
| Whisper v3 + Gemma 27B | cascade | 87.9 | 78.9 | 62.8 | 26.3 | 82.7 | 77.1 | 56.2 | 50.5 | 65.30 | **26.79** |
| Qwen-2.5-Omni-7B | zero-shot SpeechLM | 79.5 | 80.6 | 50.2 | 22.4 | 74.1 | 68.3 | 48.2 | 36.5 | 57.48 | 25.21 |
| Whisper v3 + Gemma 12B | cascade | 80.3 | 75.2 | 50.4 | 18.9 | 69.1 | 64.2 | 44.9 | 46.5 | 56.19 | 22.44 |
| Kimi-7B | zero-shot SpeechLM | 75.4 | 75.6 | 46.5 | 20.5 | 70.6 | 65.3 | 45.7 | 37.8 | 54.67 | 23.51 |
| Step-Audio2-7B | zero-shot SpeechLM | 77.9 | 76.5 | 41.4 | 15.1 | 64.4 | 58.2 | 40.8 | 34.2 | 51.06 | 20.80 |
| Audio-Flamingo-8B | zero-shot SpeechLM | 64.5 | 75.3 | 40.6 | 7.9 | 58.9 | 44.6 | 34.5 | 30.4 | 44.59 | 16.61 |
| Qwen3 8B, oracle text | oracle | 85.6 | 77.1 | 61.3 | 26.8 | 80.5 | 75.2 | 55.4 | -- | 65.99 (T1-7) | -- |

Per-tier EM and slot F1 for all 14 rows (including the smaller cascades) are in the JSON. The cells are tool
accuracy. Qwen-3-Omni-30B EM by tier: 92.4 / 15.6 / 28.6 / 11.3 / 36.0 / 24.8 / 16.3 / 12.4.

### 3.2 Our numbers (union-4000 official population, 500 per tier, official primary-call scorer)

| our row | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | tool pooled | EM pooled | EM mean T2-8 | source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| direct call (native-role) tool / EM | 67.2 / 16.0 | 78.4 / 28.2 | 67.6 / 20.4 | 29.0 / 6.4 | 80.4 / 21.8 | 76.0 / 24.0 | 49.0 / 10.6 | 48.6 / 20.6 | 62.03 | 18.50 | 18.86 | `docs/results/2026-09-27-a2t-earnings-gap-diagnosis.md` A1 |
| dual-store system tool / EM | 61.4 / 9.8 | 75.8 / 35.2 | 64.8 / 27.4 | 24.4 / 9.8 | 74.4 / 27.8 | 72.8 / 29.0 | 45.4 / 12.4 | 48.4 / 29.0 | 58.43 | 22.55 | 24.37 | same |
| official-protocol replication (tool) | 65.6 | 79.6 | 65.0 | 28.2 | 80.8 | 75.8 | 49.4 | 46.8 | 61.40 | -- | -- | 2026-09-04 official-population result summaries |

### 3.3 Comparability

- **Same task, same core, different serving path.** The paper ran Qwen3-Omni-30B through its released code (bf16
  transformers). Ours is Q4_K_M on llama.cpp. The study replicated the released prompt string for string and scores
  with the vendored official `metrics.py`, yet the replication was **NOT ACCEPTED** as a calibration: tier 1 is
  65.6 against 92.4, and only 1 of 8 tiers aligns in the natural mixture (7 of 8 equal-domain). Any class-B
  sentence must carry the unreproduced tier-1 gap. Quantization was excluded as the cause (Q8 +2.25 overall, 0.0 on
  tier 1).
- **Metric drift.** The paper's Tool Accuracy is an ordered tool-name sequence match, and its EM requires all
  tools and arguments. The official code path we vendor reads only the first parsed call against the primary gold
  tool (`docs/checks/.../2026-09-04-a2t-tier258-official-population-v1/result-summary.json`,
  `scorer_rule_differences`). Our tier-1 EM collapses because argument-free gold calls are failed by an extra
  `deviceId` key (389 of 495 extra-key rows). Per-tier n is not printed in the paper.
- **Speech.** The benchmark is synthetic TTS speech.

### 3.4 Gaps by claim class

| class | comparator | tool acc gap pp | EM gap pp (T2-8 mean) |
| --- | --- | ---: | ---: |
| A | dual-store system vs direct, paired, union-4000 | -3.60 | +4.05 pooled (+5.51 on T2-8 means) |
| B | Qwen-3-Omni-30B published, our **direct** | **-7.16** (-7.79 for the official-protocol cell) | -1.85 |
| B | Qwen-3-Omni-30B published, our **system** | -10.77 | **+3.66** |
| B | Whisper v3 + Gemma 27B (best published EM), our system | -6.88 | -2.42 |
| C | none published | -- | -- |

Per tier, our direct call beats the published same-core tool accuracy only on tier 8 (48.6 vs 41.7). The
dual-store system's EM beats it on tiers 2, 6 and 8. Nothing here supports a SOTA sentence on Audio2Tool. The
nearest honest sentence is class B on exact match over tiers 2-8, for a module that the ledger records as
PRIMARY_GAIN_TOOL_GUARD_FAILED_NOT_ADOPTED.

## 4. Earnings-21 (+ ConEC, umbrella id `aclanthology:2024.lrec-main.328`)

### 4.1 Published lines

| system | regime | protocol | WER % | PERSON entity WER % | source | status |
| --- | --- | --- | ---: | ---: | --- | --- |
| Whisper large-v2 (medium.en 10.2, small.en 10.8, base.en 12.5, tiny.en 17.0) | general ASR, zero-shot | all 44, long-form, Whisper normaliser | **9.7** | -- | arXiv:2212.04356 App. D.4 | VERIFIED |
| openai/whisper-large-v3 | general ASR | Open ASR Leaderboard long-form | 9.71 | -- | leaderboard | **UNVERIFIED** (huggingface.co unreachable; study transcription of 2026-09-04) |
| TRADE (FastConformer FT+LCA+GT 13.84 beside it) | trained speech LLM | long-form, no external segmentation | 9.75 | -- | arXiv:2606.08486 T2 | VERIFIED |
| ConEC row 8, Whisper large, no biasing | general ASR | all 44, **sentence-segmented**, fstalign | 7.98 | 28.9 | ConEC T2 | VERIFIED |
| ConEC row 4, zipformer + real ConEC context | in-domain trained AM + context biasing | segmented | 10.29 | 39.8 | ConEC T2 | VERIFIED |
| ConEC row 1, zipformer, no biasing | in-domain trained AM (SPGISpeech) | segmented | 10.41 | 45.9 | ConEC T2 | VERIFIED |
| ConEC row 5, oracle substitution | oracle upper bound | segmented | 9.69 | 13.0 | ConEC T2 | VERIFIED |
| Earnings-21 paper (Rev ESPNet 11.3, Rev Kaldi 13.2, Microsoft 15.8, Speechmatics 16.0, Amazon 17.0, Google 17.8) | commercial / in-house ASR | fstalign family | 11.3 best | -- | arXiv:2104.11348 T2 | VERIFIED; different metric family |

The Open ASR Leaderboard paper (arXiv:2510.06961 Table 5) prints only long-form averages across its long-form sets
(best open model Cohere Labs Transcribe 9.73, best closed ElevenLabs Scribe v2 7.32, whisper-large-v3 11.2), not an
Earnings-21 column. The per-dataset leaderboard leader on Earnings-21 is therefore **UNVERIFIED and unknown** to this
record.

### 4.2 Our numbers and comparability

| our row | WER % | PERSON % | source |
| --- | ---: | ---: | --- |
| bare core, all 44 calls, 1,593 fixed 90-s windows (numeric-value accuracy 90.73) | **8.200** | 22.49 | `docs/readiness/2026-09-04-e21-full44-direct-baseline-v1-verdict.md`; `docs/readiness/2026-09-06-earnings-agentic-metric-baseline-v1.md` |
| KC-E1f, the ConEC brief as a second-pass entity repair (ADMITTED under own-null margins, REPLICATED) | 8.154 | **18.75** (replicate 18.86) | `docs/results/stage2-results-ledger.md` E21-KC-E1F rows |
| silence tail (NOT ADMITTED) / speaker-turn units OBS-E1 (REJECTED) | 7.271 / 7.151 | 23.17 / 24.58 | umbrella `published-baselines.md`, 2026-09-08 rows |

The WER rows share the Whisper normaliser with the Whisper paper and the leaderboard, but four caveats remain:

- Our whole-file 90-s windows are not ConEC's sentence segmentation, which is worth about 2.3 points on Whisper
  large's own numbers.
- We do not apply the leaderboard's `merge_compounds`, which can only work against us.
- Our entity metric is a mirror of fstalign `RecordTagWer` (`official_tool_run: false`), not the official tool.
- Whisper's own decoding heuristics move this set by about 1.1 points.

The study's six-node FlightRuntime system arm has not been admitted for Earnings (E35 harm as flown, root-caused).
KC-E1f is outside every default plan until its switch form is flown.

### 4.3 Gaps by claim class

| class | comparator | WER gap pp (ours minus theirs; negative = better) | PERSON gap pp |
| --- | --- | ---: | ---: |
| A | KC-E1f vs bare core, paired, 44 call clusters | -0.045 (inside its own null, withdrawn) | **-3.74 [CI90 -4.86, -2.65]**, replicated |
| B | Whisper large-v2, whole file | **-1.50** (bare core) | -- |
| B | whisper-large-v3, leaderboard (UNVERIFIED) | -1.51 | -- |
| B | ConEC Whisper large, segmented (not comparable on WER) | +0.22 | -6.4 (bare) / **-10.15** (KC-E1f) |
| C | ConEC zipformer + real context biasing (segmented) | -2.09 (not comparable) | -21.05 (KC-E1f) |
| oracle | ConEC oracle substitution | -- | +5.75 (KC-E1f) |

Earnings-21 is the strongest class-B position on file. The bare core is 1.5 points under every verified zero-shot
whole-file WER, and KC-E1f's PERSON entity WER is 10 points under the published Whisper-large row, with the
segmentation and scorer-mirror caveats attached. It is not a SOTA statement against the leaderboard, whose per-dataset
leader was not obtainable.

## 5. Earnings-22

Note: the study `CLAUDE.md` locks the carriers to Earnings21+ConEC, SLURP and Audio2Tool. Earnings-22 enters through
the owner goal of 2026-10-09 (the base must run on E22). Its two test reads are spent.

### 5.1 Published lines and ours

| system | regime | population | WER % | source | status |
| --- | --- | --- | ---: | --- | --- |
| Nemotron 3 Nano Omni (30B-A3B) | zero-shot omni LLM | Open ASR LB English, Earnings22 | **9.66** | arXiv:2604.24954 T8 | VERIFIED (multi-column layout) |
| Qwen3-Omni-30B-A3B (same core) | zero-shot | same | 12.3 | arXiv:2604.24954 T8 | VERIFIED |
| Qwen3-Omni-30B-A3B-Instruct (same core), greedy, N 2,741 | zero-shot | ESB test subset | 9.79 | NVIDIA NeMo AutoModel documentation | **UNVERIFIED** (current page did not show the row) |
| same, NeMo fine-tuned | fine-tuned on Earnings22 among others | ESB test subset | 8.89 | same | **UNVERIFIED** |
| Phi-4-multimodal-instruct / Voxtral-Mini-3B / Parakeet-TDT-0.6B-v3 / whisper-large-v3 / Canary-1B-v2 | general ASR / speech LLM | Open ASR LB Earnings22 | 10.50 / 10.65 / 11.19 / 11.29 / 11.79 | arXiv:2509.14128 T5 | VERIFIED (reported by NVIDIA) |
| Qwen3-ASR-1.7B (9.73), distil-large-v3.5 (10.83), whisper-large-v3 (11.59), base.en (15.09) | ASR | leaderboard snapshot 2026-09-04 | -- | study preregistration | **UNVERIFIED** |
| full 125-file long-form: TRADE 10.88, Whisper large-v2 12.6, Canary-1B-v2 parallel chunks 13.93 | trained ASR | long-form full corpus | -- | arXiv:2606.08486 T2; arXiv:2212.04356 D.4 | VERIFIED; different population |
| **ours: bare core** | direct call | ESB test, 2,735 of 2,741 utterances | 15.94 | `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-verdict.md` | STUDY-OWN |
| **ours: bare core + 2-s silence tail** (agentic error rate 1.76 -> 1.59) | direct call + OBS convention | same rows | **9.24** | `docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-verdict.md` | STUDY-OWN |

### 5.2 Comparability and gaps

The ESB clips overlap their neighbours (the released arrays carry the same overlap), and our bare core continues
into the next utterance from a sub-second onset. The silence tail removes that continuation. It is a model-usage
convention that **published systems did not use**, so 9.24 is not a like-for-like reproduction. Our clips are
librosa 16 kHz mono cuts from the locked MP3s, not the released arrays. The two vendor reports of the same model
differ by 2.5 points.

| class | comparator | gap pp (ours minus theirs) |
| --- | --- | ---: |
| A | tail vs bare, same 2,735 rows, paired | -6.70 [CI90 -7.04, -6.38] |
| B | same core, Nemotron Table 8 (12.3) | -3.06 (tail) / +3.64 (bare) |
| B | same core, NeMo doc (9.79, UNVERIFIED) | -0.55 (tail) / +6.15 (bare) |
| B | Nemotron 3 Nano Omni (9.66) | -0.42 (tail) |
| C | NeMo fine-tuned Qwen3-Omni (8.89, UNVERIFIED) | +0.35 (tail) |

The leaderboard's per-dataset Earnings22 leader was not obtainable (UNVERIFIED). The owner has also ruled WER not to
be an agentic task (2026-09-06), and no published counterpart to the agentic error rate exists.

## 6. UNVERIFIED items (all)

1. Open ASR Leaderboard per-dataset values: whisper-large-v3 Earnings-21 long-form 9.71; the 2026-09-04 Earnings22
   snapshot (whisper-large-v3 11.59, Qwen3-ASR-1.7B 9.73, distil-large-v3.5 10.83, Qwen3-ASR-0.6B 10.78,
   whisper-large-v3-turbo 11.07, base.en 15.09); and the per-dataset leaders on Earnings-21 and Earnings22. Cause:
   huggingface.co unreachable from this machine.
2. Qwen3-Omni-30B-A3B-Instruct Earnings22 9.79 zero-shot and 8.89 NeMo fine-tuned (vendor documentation; the current
   page did not show the row).
3. NeMo SLURP Conformer-Transformer-Large 90.14 / 82.27: split not stated; SLU-F1 column inferred.
4. UniverSLU Table 6 rows (90.4 / 80.4 and the 89.6 / 79.7 prior SOTA): row labels lost in PDF text extraction.
5. Wang et al. HuBERT "SF F1": not confirmed to be the official SLU-F1.
6. ChatGPT slot-filling F1 12.03-13.35 (He and Garner Table 4 not re-read).
7. The Qwen2.5-Omni report's absence of SLURP / Earnings / Audio2Tool rows (partial download).
8. Model sizes marked "per paper, not re-read" in the JSON (UniverSLU, WHISMA, TRADE).

Everything else in this record was read in the primary source on 2026-10-12 or is a study-own number with its file
cited.

## 7. What the owner can choose (no recommendation implied beyond the arithmetic)

- **Class A** is available and paired on SLURP (DEV-2000-ADDED, +14.9 intent / +27.3 SLU-F1) and on Earnings-21
  (PERSON -3.74 replicated). On Audio2Tool it is a trade (exact +4.05, tool -3.60).
- **Class B** is defensible today on Earnings-21 WER (bare core under every verified zero-shot whole-file row), on
  Earnings-21 PERSON (with the segmentation and mirror caveats), and on SLURP intent against prompt-only text
  systems. SLURP SLU-F1 has no class-B target. On Audio2Tool it holds only on exact match over tiers 2-8, against
  the same core's published row.
- **Class C** is not reached on any task. The nearest is SLURP intent against the dataset paper's trained pipelines
  (+4.03 over HerMiT). Fine-tuned SLURP SOTA is 8 pp (intent) and 13 pp (SLU-F1) away. Audio2Tool has no class-C
  line.
