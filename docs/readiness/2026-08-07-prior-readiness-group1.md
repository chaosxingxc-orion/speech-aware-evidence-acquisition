# Model-free prior-readiness survey — group 1 of 2 (families A, C, E)

Status: DRAFT EVIDENCE — produced by a model-free web survey (search + fetch of
primary sources only; no model touch, no downloads beyond reading pages). This
document does **not** pick the R1 baseline; the owner picks from the ranked
evidence below (and from group 2, covering families B/D, once produced).

Contract basis: `wiki/experiments/speech-aware-evidence-acquisition/2026-08-04-owner-consolidated-execution-contract.md`
§2 (speech-only scope), §3 (OBS/ORG/SUPPLY/USE separation), §4 (data/baseline
binding — closest-prior candidates named there: ConEC/contextual ASR,
RECOVER-style 1-best correction, Siskos entity resolution, FlexCTC/TurboBias).
Template basis: `docs/readiness/2026-08-05-prior-readiness-memo.md` (not
edited by this document).

## Boundary rubric used to classify every row

We can only send a prompt + audio bytes to a frozen HTTP chat-completions
endpoint (Qwen3-Omni via llama.cpp llama-server) and read back text. We cannot
access logits/hidden-states/attention, manipulate the decoder/beam search, do
CTC-lattice rescoring, fine-tune/LoRA/adapter-train anything, or add a second
trained task head or a second answering LLM. A lightweight deterministic
tool-level retriever/reranker (not itself producing the final answer) is
allowed only if pinned and logged. Gold/reference transcripts, test
annotations and future dialogue turns never enter runtime.

- **RUNNABLE_R1_FULL** — the prior's full method is reproducible purely via
  prompts/audio/tool-calls against the frozen HTTP endpoint; no logit access
  or fine-tuning needed.
- **RUNNABLE_AS_ARM** — the prior's core mechanism needs something outside
  the boundary (trained rescorer/retriever/head, logit-level fusion), but an
  analogous evidence-supply/evidence-use strategy can still be built as one
  experimental arm scored via the frozen core. Not a full reproduction.
- **NOT_READY(reason)** — neither of the above; exact blocker stated.

Every fact below came from a primary source (paper abstract/PDF, official
repo) unless marked `UNKNOWN`/`NONE`, which are asserted rather than guessed.

---

## Family A — contextual ASR / entity correction / proper-noun biasing

On-disk carriers: `earnings21-original`, `earnings22-original`, `conec`
(core); `prism-public`, `rare5k-reconstruction`, `buzzword` (diagnostic).

| line | family | axis | runnable revision | license | boundary compatibility | scorer alignment | carrier we already hold | not-runnable reason |
|---|---|---|---|---|---|---|---|---|
| **ConEC** — Huang et al., "ConEC: Earnings Call Dataset with Real-world Contexts for Benchmarking Contextual Speech Recognition," LREC-COLING 2024 ([ACL Anthology](https://aclanthology.org/2024.lrec-main.328/)) | A | SUPPLY | NONE found — no code/data-release repo located for the corpus/baselines | paper CC BY 4.0 (ACL Anthology default); corpus license UNKNOWN | RUNNABLE_AS_ARM | moderate — reported WER + per-entity-class WER (PERSON/PRODUCT/ORG), close to but not identical to entity-PRF | `conec` (direct) | baselines (neural biasing / shallow-fusion contextual LM) need decoder-internal integration; only the real-context-materials task design is boundary-compatible as a prompt-injection arm |
| **RECOVER** — Kumar & Sachdeva, "RECOVER: Robust Entity Correction via agentic Orchestration of hypothesis Variants for Evidence-based Recovery," arXiv:2603.16411 (submitted for Interspeech 2026 review; confirmed live abstract) | A | USE | NONE — no GitHub repo found | CC0 (per arXiv listing) | RUNNABLE_R1_FULL | direct — entity-phrase WER (E-WER) + P/R/F1 per dataset; reports 8-46% relative E-WER reduction, up to +22pp recall | `earnings21-original` (direct — one of 5 eval sets) | — |
| **Siskos et al.** — "Retrieval Augmented Generation based context discovery for ASR," EMNLP 2025 Findings ([ACL Anthology](https://aclanthology.org/2025.findings-emnlp.768/), arXiv:2509.19567) | A | SUPPLY | NONE — no GitHub repo found | UNKNOWN for code; paper likely CC BY 4.0 (unconfirmed) | RUNNABLE_R1_FULL | direct-ish — WER only, no entity-specific metric, but a clean 4-condition dose-response (35.9%→31.1%→31.8%→29.7% no-context/CB-RAG/CB-LLM/oracle) | `earnings21-original` (direct — one of 3 eval sets) | — |
| **FlexCTC / TurboBias** — Grigoryan, Bataev, Karpov, Andrusenko, Lavrukhin, Ginsburg (NVIDIA), ASRU 2025 / arXiv:2508.07014, 2508.07315 | A | SUPPLY | NVIDIA/NeMo repo, PRs #14108 & #14277 (TurboBias) merged to `main`; FlexCTC toolkit stated open-source, exact path unconfirmed | Apache 2.0 (NeMo repo) | NOT_READY | direct-ish but inaccessible — WER + bias-phrase recall; bias list literally sourced from earnings21 `bias_lists/oracle_list.txt` | `earnings21-original` (bias-list source match; method itself not runnable) | requires GPU-resident beam-search / decoder-score-level phrase-boosting fusion inside CTC/transducer/AED decoding — no hook behind a frozen HTTP text API |
| **Entity resolution for noisy ASR transcripts** — Raghuvanshi et al., EMNLP-IJCNLP 2019 ([ACL Anthology](https://aclanthology.org/D19-3011/)) | A | USE | NONE — algorithm description only, no code | paper CC BY 4.0; no code | RUNNABLE_R1_FULL | indirect — reports "40.8% accuracy improvement" on a proprietary production-NLU metric, not WER/entity-F1 | none directly; `buzzword`/`rare5k-reconstruction` are conceptual analogs | — |
| **DeRAGEC** — Im, Lee, An, Kim, Ok, Lee, "Denoising Named Entity Candidates with Synthetic Rationale for ASR Error Correction," ACL 2025 Findings (arXiv:2506.07510, [repo](https://github.com/solee0022/deragec)) | A | USE | `solee0022/deragec` main branch (~19 commits); exact commit SHA/tag UNKNOWN | paper CC BY 4.0; repo license UNKNOWN (no LICENSE file surfaced) | RUNNABLE_R1_FULL | direct-ish — WER + NE hit ratio (entity-recall-like) | none directly (evaluated on CommonVoice + STOP); `buzzword`/`rare5k-reconstruction` conceptual analogs | — |
| **Retrieval Augmented Correction of Named Entity Speech Recognition Errors** — Pusateri, Walia, Kashi et al., ICASSP 2025 submission (arXiv:2409.06062) | A | SUPPLY | NONE — no GitHub URL found | paper CC BY 4.0; no code | RUNNABLE_R1_FULL | direct-ish — WER reduction on synthetic rare-entity test sets + STOP regression check | none directly; `buzzword`/`rare5k-reconstruction` conceptual analogs | — |

Note on the contract's "Siskos entity resolution" pointer: the only real,
findable ASR/entity paper by an author named Siskos is the EMNLP 2025
Findings RAG-context-discovery paper above; no separate "Siskos entity
resolution" paper distinct from this was located. Reported as the closest
real match rather than a guess.

**Family A narrative.** Under our boundary the two strongest candidates are
**RECOVER** and **Siskos et al.** — both are explicitly black-box, text/audio
I/O pipelines around a frozen ASR system, both report directly on
`earnings21-original` (a carrier we already hold), and neither needs logits,
decoder access, or fine-tuning. RECOVER is architecturally the closer match
to our OBS/SUPPLY/USE split (multi-hypothesis generation, deterministic
entity-candidate retrieval as a permitted tool-level step, LLM correction
under a verify/guardrail gate), but it is a fresh, not-yet-peer-reviewed
preprint with zero released code, so reproduction means reimplementing from
the method description with real interpretation risk. Siskos et al. is
peer-reviewed and gives a cleaner controlled comparison directly on
Earnings-21 whose WER moves substantially and monotonically with
context/evidence quality — exactly the sensitivity a calibration baseline
needs — but likewise ships no code, and its underlying "black-box contextual
ASR system" behavior would have to be approximated against Qwen3-Omni rather
than literally rerun. By contrast, ConEC's own reported aggregate WER barely
moves across biasing conditions (10.29-10.66% band around a 10.41% no-bias
baseline) — a real concern if aggregate WER rather than per-entity-class
breakdown were used as the signal — and FlexCTC/TurboBias, despite being the
best-licensed and most cleanly versioned code here, is flatly NOT_READY
because its phrase-boosting mechanism modifies token-level decode scores
inside CTC/transducer/AED beam search, which a frozen chat-completions
endpoint cannot expose. For either RECOVER or Siskos et al. to be a
defensible R1, we would need: a code release or a budget to reimplement the
algorithm exactly against the paper's own numbers as a match target;
confirmation that reimplementation needs nothing beyond prompt/audio I/O plus
a pinned deterministic tool-level retriever (true for both, per their own
black-box framing); and explicit acceptance that we are calibrating against a
preprint (RECOVER) or a paper with no released code (Siskos) rather than an
artifact-verified baseline.

---

## Family C — spoken question answering

On-disk carriers: `slue-sqa-5`, `spoken-squad`, `heysquad`, plus
`slue-toolkit`.

| line | family | axis | runnable revision | license | boundary compatibility | scorer alignment | carrier we already hold | not-runnable reason |
|---|---|---|---|---|---|---|---|---|
| **SLUE-SQA-5 official baseline** — Shon et al., "SLUE Phase-2," ACL 2023 ([ACL Anthology](https://aclanthology.org/2023.acl-long.496/), arXiv:2212.10525) | C | OBS/USE | Paper only. Baseline code NONE released: `asappresearch/slue-toolkit` (main, HEAD ~2026-06-15) ships ASR/NER/SA/NEL baselines but no SQA code despite the paper stating scripts "will be released" | slue-toolkit repo MIT; text/audio sourced from SQuAD (CC BY-SA 4.0), NQ/WebQuestions/TriviaQA/CuratedTREC (mixed CC); HF dataset-card license not independently re-verified | RUNNABLE_AS_ARM | frame-level F1 (time-interval span overlap), not text EM/F1 — indirect mapping | `slue-sqa-5` (direct) | official pipeline needs a DeBERTa span-extractor fine-tuned on ground-truth transcripts — a second trained task head, out of boundary; code never released |
| **Spoken-SQuAD original** — Lee, Wu, Wang, Lee, Lee, Interspeech 2018 (arXiv:1804.00320) | C | OBS/USE | `Chia-Hsuan-Lee/Spoken-SQuAD` (dataset/audio hosting only; no baseline model code shipped) | dataset CC-BY-SA-4.0; no code license (no code) | RUNNABLE_AS_ARM | EM/F1 on text spans — most direct QA-EM-F1 alignment of any line surveyed | `spoken-squad` (direct — origin dataset) | baseline is a trained gated self-matching-attention span predictor; code never released |
| **Su & Fung 2020** — best published Spoken-SQuAD F1, ICASSP 2020 (IEEE 9053979) | C | OBS/USE | Paper only; no author code repo found | no code released; paper IEEE copyright | RUNNABLE_AS_ARM | EM/F1 — direct; F1 77.67 is the literature ceiling on a carrier we hold | `spoken-squad` (direct) | fine-tuned contextualized-embedding extractive QA head; code never released |
| **HeySQuAD** — Wu, Rallabandi, Srinivasamurthy, Dakle, Gon, Raghavan, arXiv:2304.13689 (rev. 2024) | C | OBS/USE | `yijingjoanna/HeySQuAD` ships an HF-Trainer fine-tuning command, not a frozen inference baseline | repo MIT; dataset CC BY 4.0 | RUNNABLE_AS_ARM | EM/F1 — direct | `heysquad` (direct) | best config fine-tunes a RoBERTa-large extractive head on SQuAD+HeySQuAD transcripts; no frozen-core prompt-only variant published |
| **SpeechDPR** — Lin et al., ICASSP 2024, arXiv:2401.13463 | C | SUPPLY | Paper only; no code repo found | paper CC BY 4.0; no code | RUNNABLE_AS_ARM | Top-20 retrieval accuracy (direct SUPPLY signal) + downstream frame-F1 (indirect vs. our QA-EM-F1) on SLUE-SQA-5 | `slue-sqa-5` (direct — the open-domain retrieval setting SLUE-SQA-5 was built for) | needs a trained speech-passage bi-encoder retriever (a second trained model); code never released |
| **SpeechRAG** — Min, Mundnich, Lapastora, Soltanmohammadi, Ronanki, Han (AWS AI Labs + U. Michigan), ICASSP 2025, arXiv:2412.16500 | C | SUPPLY/ORG | Paper only; no code repo found | no code license (none released); paper license UNKNOWN from accessible excerpts | RUNNABLE_AS_ARM | paper states direct speech retrieval "does not degrade" vs. text baseline; exact metric UNKNOWN/indirect from accessible excerpts, but design is explicitly SUPPLY-sensitive | `spoken-squad` (direct — "SpokenSQuAD" is one of two eval sets; VoxPopuli, the other, is not held) | trained speech adapter/retriever required; code never released |
| **AudioBench direct-prompting harness** — Wang et al., NAACL 2025, arXiv:2406.16020 (incl. Qwen2-Audio-Instruct, Qwen-Audio-Chat, SALMONN-7B, WavLLM, MERaLiON-AudioLLM baselines) | C | OBS/USE | `AudioLLMs/AudioBench`, commit `85dcdb88c41e6ebb2bcb3ce19b15d061dfef9dba` on `main` (repo confirmed live; no tagged release) | code license: repo states a CC NonCommercial variant (exact sub-license unspecified); each dataset under its own HF license (`AudioLLMs/spoken_squad_test`, `AudioLLMs/slue_p2_sqa5_test`) not independently re-verified | **RUNNABLE_R1_FULL** | model-as-judge score (Llama-3-70B-Instruct/GPT-4o, 0-100), not EM/F1, but the most direct holistic proxy among all Family C lines | `slue-sqa-5` and `spoken-squad` both directly (`slue_p2_sqa5_test`, `spoken_squad_test`); `heysquad` not included | — |

**Family C narrative.** The **AudioBench direct-prompting harness** is the
only line where "reproduce the published baseline" and "run our own system
under the same protocol" are literally the same operation — audio + text
prompt to a chat-completions endpoint, text back, no logits, no fine-tuning,
no second answering LLM, exactly our access mode. It already targets two of
our three on-disk carriers and publishes numbers for several audio-LLMs we
can sanity-check against. Every other line needs a trained retriever,
adapter, or extractive-QA head outside our boundary — reproducible at best as
an analogous arm. The metric-sensitivity concern is real and structural: the
AudioBench SQA protocol always gives the full spoken document and never
perturbs retrieval/ordering/chunking, so its judge score measures OBS+USE
quality only and is by construction insensitive to SUPPLY manipulation —
using it unmodified as an R1 target would tell us nothing about whether
evidence acquisition matters. The lines that are explicitly SUPPLY-sensitive
(SpeechDPR's Top-20 retrieval accuracy directly gating downstream frame-F1;
SpeechRAG's explicit retrieval-vs-no-retrieval ablation) are exactly the ones
boundary-incompatible (trained retrievers, no code). This is Family C's
central tension. For AudioBench to be a defensible R1: (i) re-verify the HF
dataset-card licenses for the two eval sets against our no-redistribution
constraints (blocked this session); (ii) layer our own SUPPLY-perturbation
conditions on top of the same items/gold answers, using the judge only for
literal baseline replication and switching to EM/F1 against Spoken-SQuAD's
native ground-truth answers (SLUE-SQA-5's gold answers are frame/timestamp-
based and need an extra alignment step) for the SUPPLY-sensitive tier; (iii)
pin the exact judge model/prompt or substitute a deterministic scorer to
avoid a second LLM call; (iv) record the exact commit
(`85dcdb88c4…`) as the frozen baseline revision.

---

## Family E — meeting / long-form speech understanding

On-disk carrier: `ami-meeting-corpus`.

| line | family | axis | runnable revision | license | boundary compatibility | scorer alignment | carrier we already hold | not-runnable reason |
|---|---|---|---|---|---|---|---|---|
| **QMSum benchmark + original baselines** (Locate-then-Summarize, BART, HMNet-as-baseline) — Zhong et al., NAACL 2021 | E | SUPPLY/ORG | `Yale-LILY/QMSum` @ `83d7768c1f2b4dfeb091385d3dc7e239b8e5bb7e` | code MIT; 137/232 meetings are AMI transcripts (AMI upstream CC BY 4.0); QMSum's own query/summary annotation license not separately stated (2023 README commit removed research-usage-restriction text — re-check before use) | NOT_READY | ROUGE-1/2/L — weak surface-overlap proxy, not a direct WER/entity-PRF/QA-EM-F1 analogue | AMI (text transcripts, not raw audio) | original baselines require fine-tuning a seq2seq/extractive-span model; no zero-shot path in the original paper |
| **Zero-shot LLM prompting on QMSum** — via ZeroSCROLLS, Shaham et al., EMNLP 2023 | E | SUPPLY/USE | `tau-nlp/zero_scrolls` @ `c994676234c624ae32232eda9ee32b0329a37f04` | code MIT; AMI subset CC BY 4.0 (via QMSum) | RUNNABLE_R1_FULL for the core mechanism — but only if gold transcript is replaced with our own ASR output from AMI audio, since gold text may not enter runtime | ROUGE geometric mean — same weak-proxy caveat as above | AMI subset of QMSum — but original setup uses gold text; our reproduction must re-derive transcript from audio | — |
| **HMNet** (Hierarchical Meeting Summarization Network) — Zhu et al., EMNLP Findings 2020 | E | ORG | `microsoft/HMNet` @ `416966c63e3cb7a57dc59b4ce8fa76f11fd048be` (pretrained checkpoint + fine-tuning scripts) | license unclear/NOASSERTION on repo (no OSS license badge); AMI/ICSI split (Shang et al. 2018) license not restated | NOT_READY | ROUGE-1/2/L | AMI (canonical abstractive-summarization split) | is itself a 204M-parameter second trained answering model — disallowed by design regardless of the fine-tuning question |
| **MeetingQA** (extractive QA on meeting transcripts) — Prasad et al., ACL 2023 | E | USE | `adobe-research/meetingqa` @ `5e3d1fbf4fefb60790d2445ce6721085b274024b` | code+data CC BY-NC-SA 4.0 (non-commercial, ShareAlike) | RUNNABLE_AS_ARM | extractive F1 — best QA-EM/F1 alignment of any Family E line | AMI + ICSI transcripts directly | best-reported baseline is fine-tuned (F1 57.3 vs. human 84.6); zero-shot subset not cleanly separable from what could be verified |
| **MeeQA** (natural questions in meeting transcripts) — Apel et al., arXiv 2023 | E | USE | `reutapel/MeeQA` @ `7b9a6c43eef4e0830336862ffc19b48ff52615a6` | code: no LICENSE file (default all-rights-reserved); data mixed AMI+ICSI+other provenance | NOT_READY | span/token F1 + answerability P/R | AMI is one of several source corpora, not sole one | requires training a custom "Flat Hierarchical Loss" QA head; no license granted for reuse |
| **MS-AMI / personalized multi-source meeting summarization** — Kirstein et al., EMNLP 2024 Industry | E | SUPPLY/ORG | `FKIRSTE/emnlp2024-personalized-meeting-sum` @ `7b896a30d23ca0c5eb5a1acae9e49a3cd09be9a4` | code Apache-2.0; MS-AMI is adapted/augmented AMI (125 staged meetings), AMI's own CC BY 4.0 not explicitly restated | RUNNABLE_R1_FULL for the base zero-shot transcript-only summarization chain (GPT-4o/Gemini/Phi-3/Llama-3, no fine-tuning); full "personalized multi-source" variant needs OCR'd slides/notes, outside our audio-only OBS pipeline | primarily LLM-judge Likert score; authors explicitly report ROUGE/BERTScore "yield nearly identical scores across conditions, limiting interpretability" | AMI-derived text transcripts | — (base arm only) |
| **CMT-LLM** (Contextual Multi-Talker ASR with LLMs) — He et al., Interspeech 2025 | E | OBS | NONE — no code repo found | paper standard Interspeech copyright; AMI (IHM-Mix/SDM/MDM) CC BY 4.0 | NOT_READY | WER (AMI SDM: 32.9% at 1,000 distractors); biasing-list recall entity-like but not a standalone entity-PRF number | AMI SDM/IHM-Mix/MDM directly | requires training a projector/adapter between frozen speech encoder and frozen LLM — parameter training, forbidden even though base LLM stays frozen |
| **PlanRAG-Audio** — Someki, Huang, Arora, Cornell, Müller, Susanj, Swaminathan, Strimel, Liu, Watanabe (CMU/Amazon AGI), arXiv:2605.20414, **accepted ACL Findings 2026** (verified — later status than "preprint" assumed at initial search) | E | SUPPLY/OBS | NONE yet at survey time — code/data release tied to acceptance; not confirmed published as of this survey | paper CC BY 4.0; code/data license unset, unreleased | architecturally closest to our own OBS/ORG/SUPPLY/USE design (frozen audio-LLM backbones + a deliberately non-fine-tuned, deterministic keyword/SQL retriever) but classified NOT_READY today purely on availability | ROUGE-L for a self-built AMI summarization task (10-min windows) + DER for a self-built diarization task; neither is an established public benchmark scorable without the unreleased eval set | AMI directly (both sub-tasks) | code/eval data not released; re-check post-ACL-Findings-2026 publication for a release |
| **Interactive In-Meeting Speaker Correction with Human Feedback** — arXiv:2509.18377 (2025) | E | OBS | UNKNOWN — code availability could not be confirmed | UNKNOWN | NOT_READY | DER (diarization error rate) — not in our WER/entity-PRF/QA-EM-F1 set | AMI (evaluation) | core mechanism requires live human feedback at inference — incompatible with an autonomous pipeline, independent of the LLM component itself being used frozen |

**Family E narrative.** Nothing in this family is both fully reproducible
under our boundary and a strong, evidence-sensitive metric at once — the two
properties trade off. The most concretely reproducible line today is
zero-shot LLM prompting on QMSum's AMI subset (MIT-licensed code, no
fine-tuning), but its ROUGE metric is a documented weak proxy for
evidence-selection quality — independently confirmed by MS-AMI's own authors,
who report ROUGE/BERTScore "yield nearly identical scores across conditions,"
i.e. the metric barely moves even when their evidence-injection condition
changes, which is close to disqualifying for an evidence-acquisition
calibration target. The line with the best scorer alignment — MeetingQA's
extractive span-F1, directly mapping to our QA-EM/F1 axis and clearly
sensitive to whether the right span was found — cannot be faithfully
reproduced because its strongest reported baselines are fine-tuned
long-context extractors, and a pure zero-shot number could not be cleanly
isolated from what was retrieved. The architecturally closest published
design to our own axis separation is PlanRAG-Audio: frozen audio-LLM
backbones plus a deliberately non-trained deterministic retriever, evaluated
directly on AMI — now confirmed accepted to ACL Findings 2026, but not
runnable today because code and its self-built evaluation set are still
unreleased as of this survey (worth a follow-up check, since acceptance often
precedes a near-term code release). For this family to yield a defensible R1:
either (a) PlanRAG-Audio's code/data are released and its AMI eval becomes
independently scorable, which would make it the strongest match by far, or
(b) accept the QMSum/ZeroSCROLLS zero-shot route as R1 but explicitly pair
ROUGE with a second, more evidence-sensitive metric (entity-overlap or
LLM-judge) to compensate for ROUGE's documented insensitivity. Family E is
thin enough that it should be treated as a secondary/supplementary
calibration family rather than the study's primary R1 — every line found
needs either a trained/forbidden component, a human in the loop, or code that
does not yet exist.

---

## Cross-family summary (group 1 only — B/D not covered here)

| family | lines assessed | RUNNABLE_R1_FULL | RUNNABLE_AS_ARM | NOT_READY | closest line |
|---|---|---|---|---|---|
| A — contextual ASR / entity correction | 7 | 5 (RECOVER, Siskos et al., Raghuvanshi et al., DeRAGEC, Pusateri et al.) | 1 (ConEC) | 1 (FlexCTC/TurboBias) | RECOVER (arch. closest to OBS/SUPPLY/USE) vs. Siskos et al. (peer-reviewed, cleanest dose-response, on-carrier) — see narrative for the trade-off |
| C — spoken QA | 7 | 1 (AudioBench harness) | 6 | 0 | AudioBench direct-prompting harness — only line whose access mode literally matches ours; caveat: SUPPLY-insensitive as published |
| E — meeting/long-form | 8 | 2 (ZeroSCROLLS/QMSum zero-shot; MS-AMI base arm) | 1 (MeetingQA) | 5 | none fully defensible alone; ZeroSCROLLS/QMSum zero-shot is the practical fallback, PlanRAG-Audio the aspirational match pending a code release |

This document does not recommend a winner across families or within them
beyond what each narrative states. The owner decision should also weigh
group 2 (families B, D) before finalizing R1.
