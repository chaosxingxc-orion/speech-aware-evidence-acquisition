# Model-free dataset content verification — 15 datasets + reference (2026-08-07)

**Status: no dataset content was copied into this repository and no model was
touched.** All evidence below comes from reading local file bytes (directory
listings, file-extension histograms, WAV/FLAC header reads via
`soundfile.info` — header only, no PCM decode — and Parquet row-group
metadata) inside `SPEECHRL_DATA_DIR` in WSL2, plus each dataset's own
`README.md`/`LICENSE*` on disk and the corresponding entry in
`docs/datasets.lock.json`. Only short illustrative strings (a transcript, an
intent label, a tool-call schema) are quoted below — no bulk content, no
audio bytes, no images. `docs/datasets.lock.json` was not modified.

Rule applied throughout: **scope is judged by audio/task content actually
observed on disk, never by dataset name.**

## Summary table

| dataset | local_subdir | audio nature | task shape | scale on disk | license (lock + on-disk) | scope verdict |
|---|---|---|---|---|---|---|
| slurp | `repos/slurp/scripts/audio` (+`repos/slurp/dataset`) | **mixed**: `slurp_real/` human-recorded (headset+far-field) + `slurp_synth/` synthetic TTS augmentation, split apart in the manifests (`train.jsonl`/`devel.jsonl`/`test.jsonl` = real; `train_synthetic.jsonl` = synth) | intent classification + slot filling (`intent`, `action`, `entities` spans, BIO-style `sentence_annotation`) | 141,652 `.flac` files; corrected est. **~112h** (2.85s avg × true count, not the capped sample count) | text CC-BY-4.0, **audio CC BY-NC-4.0** — NEW flag, not previously called out | IN_SCOPE_SPEECH (flag: NC audio license; synthetic sub-split present) |
| speech-massive | `datasets/speech-massive` | human-recorded, crowdsourced with full speaker demographics (age/sex/ethnicity/nationality/first-language) per utterance | intent classification + BIO slot filling (MASSIVE schema), 12 non-English locales | 48,804 unique utterances (`all/` = sum of the 12 per-locale dirs, confirmed equal); ~52.0h (3.84s avg @48kHz) | **cc-by-nc-sa-4.0** (owner-flagged NC) | IN_SCOPE_SPEECH |
| minds14 | `datasets/minds14` | human-recorded, 8kHz telephony-quality (call-center style) | intent classification (14 classes) + transcript + English translation | 8,168 unique utterances (`all/`=sum of 14 locale dirs, confirmed equal); ~19.7h corrected (8.67s avg @8kHz; naive double-counted estimate was 39.3h) | cc-by-4.0 (open, confirmed via README) | IN_SCOPE_SPEECH |
| spoken-squad | `datasets/spoken-squad` | **TTS-synthesized** reading of SQuAD/Wikipedia passages (classic Spoken-SQuAD construction) | extractive QA: audio `context` (passage) + text `instruction` (question) → text `answer` span | 5,351 rows; ~69.1h (46.46s avg @16kHz) | lock `source.license: null` (unstated in lock); README states **CC-BY-SA-4.0** | IN_SCOPE_SPEECH (TTS, closed-book — no external evidence relevant) |
| heysquad | `datasets/heysquad` | **human-recorded** spoken questions (crowd-sourced); the passage (`context`) stays TEXT, not audio | spoken question → extract text span from a co-provided text passage | 76,148 rows (train 71,990 + val 4,158); ~107.7h (5.09s avg @16kHz) | cc-by-4.0 (explicit in lock + README) | IN_SCOPE_SPEECH (human, closed-book — evidence is co-located text, not external) |
| audio2tool | `datasets/audio2tool` | **mixed real+cloned**: speaker sourcing sampled across `generation_results.csv` = voxpopuli (real EU-Parliament speech), yodas (real YouTube speech), 3dspeaker (real speaker corpus) ≈61%, vs. `ecapa` (speaker-embedding voice-cloning ⇒ synthetic) ≈39% | spoken smart-home/car/wearable command → structured `tool_call` (e.g. `setLighting()`), across 8 escalating tiers: direct, parametric, multi_intent, implicit, **needle** (distractor context), **correction**, multi_turn, **intent_blending** | 36,419 `.wav` files across 152 registered tools (3 domains: smart_car 86, smart_home 53, wearables 13); corrected est. **~36.5h** (3.61s avg, capped sample corrected against true file count) | **cc-by-nc-4.0** (owner-flagged NC, confirmed) | IN_SCOPE_SPEECH — closest task-shape analog to SUPPLY/USE found (no external world-knowledge lookup, but "needle"/"correction"/"intent_blending" tiers mirror evidence-extraction-under-noise) |
| voiceagentbench | `datasets/voiceagentbench` | audio source **not explicitly stated**; no per-speaker demographics (unlike the confirmed-human corpora above), duration values are uniform/clean — consistent with but not confirmed as TTS | spoken query → structured tool/function call: `single_tool`, `single_tool_retrieval`, `parallel_tool`, `seqdep_tool`, `multi_turn` (chat-history-accumulated), `safety` (refusal) | 7,434 `.wav` files across en/hi/bn/ta/te/ml/mr; ~18.6h (9.00s avg) | **Krutrim Community License** ("other") — free for research/personal/education; commercial use >1M MAU needs a separate agreement — FLAG as non-standard/restricted | IN_SCOPE_SPEECH (audio provenance unconfirmed); strong SUPPLY/USE tool-call analog |
| voicebench | `datasets/voicebench` | **TTS-synthesized**, explicit Google WaveNet voice IDs (`en_AU_Wavenet_A`, etc.); one whole subset (`alpacaeval_speaker`) systematically varies speed/pitch per synthetic voice | audio prompt → open-ended free-text response, scored via LLM-judge (no fixed reference answer field beyond the prompt) | 11 subtasks (advbench, alpacaeval, alpacaeval_full, alpacaeval_speaker×9 voices, bbh, commoneval, ifeval, **mmsu** [12 knowledge domains: law/history/chemistry/physics/…], mtbench, **openbookqa**, **sd-qa** [11 English-variety splits], wildvoice); e.g. advbench alone = 520 rows, ~0.7h | apache-2.0 (confirmed) | IN_SCOPE_SPEECH (TTS); `mmsu`/`openbookqa`/`sd-qa` subtasks are genuinely knowledge-dependent — external evidence plausibly helps there |
| voiceassistant-eval | `datasets/voiceassistant-eval` | **MIXED at subtask level** — see notes | 13 subtasks under `listening/`, `speaking/`, `viewing/` | 13 parquet files, 8.8GB; rows ≈600–920/subtask (spot-checked: listening_general 799, listening_music 600, listening_sound 394, listening_speech 899, speaking_assistant 836, speaking_safety 920, viewing_multi_discipline 900) | mit (confirmed) | **MIXED** — see per-subtask verdict below |
| uro-bench | `datasets/uro-bench` | **MIXED**: 2/40 subtasks are non-speech (ClothoEval-en ← ClothoAQA environmental-sound QA; MuChoEval-en ← MuChoMusic music QA, per README acknowledgment section); remaining ~38 subtasks are **TTS-synthesized** spoken versions of existing TEXT NLP benchmarks (AlpacaEval, TruthfulQA, OpenbookQA, GSM8k, SQuAD-zh, MT-Bench-101, WildChat, LCSTS, Gaokao, HSK5, STORAL, APE-210k, Claude-Instruct; UnderEmotion-en ← RAVDESS actor recordings) | varies by subtask: open QA, extractive QA, math, summarization, repeat-after-me, tongue-twisters (SRT), emotion/style generation, code-switching, safety | 40 parquet files (6.1GB) + 2 raw zip archives (4.7GB+560MB, likely redundant jsonl+audio form); sample counts: AlpacaEval 199, TruthfulEval 470, Repeat 252 (~0.3h), SRT-en 43, SpeakerAware-en 55×3-turn dialogues | mit (confirmed) | **MIXED** — ClothoEval-en/MuChoEval-en OUT_OF_SCOPE_NON_SPEECH; rest IN_SCOPE_SPEECH (TTS, EN+ZH), mostly closed-book |
| omni-deepsearch | `datasets/omni-deepsearch` | audio-content taxonomy explicit in `task_category` (`<retrieval_modality>/<audio_content_code>`): BIO/ENV/MUSIC/SPEECH each 120/640 (single+image+trace splits), plus multi/2WAY(80)+3WAY(53)+4WAY(27)=160 cross-modal items | multi-hop **external web/encyclopedia search chain** seeded by an audio clue, e.g. identify a speaker/animal/sound → chase 3-5 unrelated facts → answer grounded in an external image | 906 `.wav` files (avg 16.4s, ~4.1h); 640 total items | lock: "upstream card unspecified" — **UNSTATED**, no local LICENSE file found | **OUT_OF_SCOPE by content** (see note) despite closest task-*shape* match to the study's evidence-acquisition thesis of anything examined |
| tau2-bench | `datasets/tau2-bench` | **no audio of any kind on disk** — pure text/JSON | agentic tool-use over airline/retail/telecom/mock domain DBs; policy-constrained multi-turn evaluation, text only | 36 files, 25MB, all `.json`/`.md`/`.py`/`.toml`; **zero** `.wav`/`.mp3` | README: Apache License 2.0 (not in main lock entry) | **OUT_OF_SCOPE_NON_SPEECH** — critical: lock's `factor_family: "spoken-agent"` / note "voice tool-use agent data" does not match the local bytes, which contain no audio at all |
| big-bench-audio | `datasets/big-bench-audio` | **TTS-synthesized**, 23 synthetic voices from the Artificial Analysis TTS Arena | spoken logic/reasoning puzzle → short text `official_answer` (formal_fallacies/navigate/object_counting/web_of_lies, 250 each) | 1,000 `.mp3` files; ~5.4h (19.4s avg) | mit (confirmed both lock + README) | IN_SCOPE_SPEECH (TTS); self-contained puzzles, no external-evidence relevance |
| full-duplex-bench-v3 | `datasets/full-duplex-bench-v3` | **human-acted, scripted-disfluent** speech — `acting_notes` direct voice actors (e.g. "Say the order ID clearly, one character at a time"), `disfluency_features` field for scripted "uh/um" fillers | acted spoken dialogue (with disfluency) → generate `expected_tool_calls` (structured function calls); also carries `state_rollback_test`/`latency_profile` for turn-taking eval | 100 dialogues (`ecommerce_support` 29, `finance_billing` 25, `housing_location` 26, `travel_identity` 20) × difficulty (easy 36/medium 34/hard 30); 100 `.wav`, ~1.3h (47.18s avg, 16–48kHz mono/stereo mixed) | **no license field anywhere** — not in the lock entry, no local LICENSE file; sourced via a Google-Drive zip (unusual channel) | IN_SCOPE_SPEECH (human-acted); no external-knowledge need, but a strong disfluency-robust tool-call analog; **license UNSTATED — flag for owner** |
| slue-sqa-5 (reference) | `datasets/slue-sqa-5` | **TTS-synthesized** (both question and document audio; `Lavf`/ffmpeg encoder tag in RIFF headers confirms machine-generated audio, consistent with the SLUE toolkit's synthesis pipeline) | spoken question over a spoken document → extract text-span answer, with word-level (`word2time`) and second-level (`start_second`/`end_second`) localization inside the document audio | 118GB/301 parquet files (per existing lock verification); confirmed structure matches the lock's COMPLETE record | mixed CC-BY-SA-4.0 + Apache-2.0 (lock, confirmed) | IN_SCOPE_SPEECH — already the best-characterized entry; closed-book (document audio is self-contained), no external retrieval needed |

## Per-subtask verdicts for the two confirmed-MIXED benchmarks

**voiceassistant-eval** (`datasets/voiceassistant-eval`):
- OUT_OF_SCOPE_NON_SPEECH: `listening_general` (rows sampled ask about music rhythm/tempo, not speech), `listening_music`, `listening_sound` (rows sampled: "metallic noise… silverware clinking", "sound's implication of a possible emergency" — pure acoustic-scene/sound-event QA)
- OUT_OF_SCOPE (vision-dependent): `viewing_multi_discipline` — every row carries both an image (67KB sample) and an audio narration (1.5MB sample) of an exam question (e.g. a cost-accounting table); the audio narrates but cannot answer alone, the image is load-bearing
- Borderline IN_SCOPE (paralinguistic, not spoken-content): `listening_speech` — sampled task is "identify whether the voice sounds like a man or a woman," i.e., a voice-timbre judgment, not ASR/entity/spoken-QA content
- IN_SCOPE_SPEECH (genuine spoken-language-content tasks): `speaking_assistant`, `speaking_emotion`, `speaking_instruction_following`, `speaking_multi_round`, `speaking_reasoning`, `speaking_robustness`, `speaking_roleplay`, `speaking_safety` — all are spoken user query → text/speech assistant response

**uro-bench** (`datasets/uro-bench`):
- OUT_OF_SCOPE_NON_SPEECH: `ClothoEval-en` (adapted from ClothoAQA — environmental sound clips, e.g. sample question "Is water being poured?" over a clip named `Mug in sink.wav`), `MuChoEval-en` (adapted from MuChoMusic — music-instrument/genre QA)
- IN_SCOPE_SPEECH (all TTS-synthesized, not human speech): the remaining ~38 subtasks (AlpacaEval/-zh, APE-zh, Claude-zh, CodeSwitching-en/-zh, CommonEval, GaokaoEval, GenEmotion-en/-zh, GenStyle-en/-zh, Gsm8kEval, HSK5-zh, LCSTS-zh, MLC/MLC-zh/MLCpro-en/-zh, MtBenchEval-en, Multilingual, OpenbookQA-zh, Repeat/-zh, SQuAD-zh, SRT-en/-zh, Safety-en/-zh, SpeakerAware-en/-zh, StoralEval, Summary, TruthfulEval, UnderEmotion-en/-zh, Wildchat-zh, WildchatEval)

## Note on omni-deepsearch's scope verdict

Even its `SPEECH`-tagged items (120/640, 18.75%) do not qualify under this
study's boundary ("only human speech and its linguistic content: ASR,
entities, contextual biasing, spoken QA, meeting-speech understanding").
Sampled `SPEECH` items ask the model to **identify a speaker by voice
timbre**, then chase 3–5 unrelated encyclopedic/geographic facts, often
finishing on a **web image** — e.g.:

> `"Listen to the audio to identify the second speaker. In their youth, this
> individual received private education at multiple institutions. The very
> first headmaster of one of these institutions shares their name with a
> person who, in 2025, authored an official event report…"`

This is paralinguistic speaker-ID plus general web multi-hop search, not the
linguistic *content* of speech. BIO/ENV/MUSIC (360/640, 56%) are explicit
non-speech audio (animal vocalizations, ambient sound, music); `multi/*`
(160/640, 25%) combine several modalities per item, not cleanly speech
either. Net: **no subtask of omni-deepsearch cleanly qualifies as
IN_SCOPE_SPEECH by content**, even though the multi-hop
external-evidence-chaining *task shape* is the closest structural mirror of
this study's SUPPLY thesis of anything examined here.

## Scope verdicts (compact)

- IN_SCOPE_SPEECH: slurp, speech-massive, minds14, spoken-squad, heysquad,
  audio2tool, voiceagentbench, voicebench, big-bench-audio,
  full-duplex-bench-v3, slue-sqa-5 (reference)
- MIXED: voiceassistant-eval (8/13 subtasks in-scope), uro-bench (38/40
  subtasks in-scope)
- OUT_OF_SCOPE_NON_SPEECH: tau2-bench (no audio at all), omni-deepsearch (no
  subtask cleanly qualifies by content, despite task-shape relevance)

## License flags requiring owner attention

- **slurp**: audio is **CC BY-NC-4.0** (text portion is CC-BY-4.0) — this NC
  restriction was not previously flagged for slurp (only speech-massive and
  audio2tool were called out in the task brief); confirmed via
  `repos/slurp/LICENSE.txt` on disk.
- **audio2tool**: cc-by-nc-4.0, confirmed (already flagged).
- **speech-massive**: cc-by-nc-sa-4.0, confirmed (already flagged).
- **voiceagentbench**: Krutrim Community License — not NC by name, but
  non-standard: free for research/personal/educational use; commercial use
  requires a separate agreement once >1M monthly active users. Flag as
  restricted/non-OSI.
- **full-duplex-bench-v3**: no license stated anywhere (lock entry has no
  `license` key; no local LICENSE file; source is an unauthenticated
  Google-Drive zip) — needs an owner/source follow-up before any scoring use.
- **omni-deepsearch**: lock says "upstream card unspecified" — confirmed
  unstated, no local LICENSE file either.
- **spoken-squad**: lock's `source.license` is `null`; README states
  CC-BY-SA-4.0 — lock could be tightened to match, but this is an
  owner/lock-maintenance decision, not made here.
- **tau2-bench**: no `license` field in the lock's dataset entry; local
  README states Apache License 2.0.
- **uro-bench**: no `license` field in the lock's dataset entry; local
  README front-matter states MIT (confirmed on disk).

## Reference/label layers observed (governs whether a scorer adapter is possible)

- **slurp**: `intent`, `action`, `entities` (span+type), `sentence_annotation`
  (inline BIO-like slot markup), per-recording `wer`/`ent_wer`/`status` — rich
  enough for intent-F1, slot-F1, and entity-level scoring.
- **speech-massive / minds14**: `intent_str`/`intent_class` + BIO `labels` per
  token — same MASSIVE-family schema, scorer-ready.
- **spoken-squad / heysquad / slue-sqa-5**: SQuAD-style `answers`
  (`answer_start`+`text`) or (`answer`, `start_second`, `end_second`) spans —
  scorer-ready extractive-QA schema; slue-sqa-5 additionally has word-level
  `word2time` alignment.
- **audio2tool / voiceagentbench / full-duplex-bench-v3**: structured
  `tool_call`/`expected_tool_call(s)` with function name + argument dict —
  directly diffable against a model's function-call output; audio2tool's
  ground truth was itself LLM-generated (`source_endpoint:
  databricks-claude-opus-4-5`), a provenance point worth noting for claim
  limits.
- **voicebench / big-bench-audio / omni-deepsearch**: big-bench-audio has a
  short fixed `official_answer` per item (scorer-ready); voicebench mostly
  has only the source `prompt` text (open-ended, needs an LLM-judge, no fixed
  reference); omni-deepsearch has a free-text `answer` plus a `golden_path`
  hop-chain (useful for diagnosing partial credit on the search chain, not a
  simple string-match scorer).
- **tau2-bench**: `evaluation_criteria` (`actions`, `communicate_info`,
  `nl_assertions`) per task — a rich but text-only agent-eval schema; not
  applicable here since there is no audio to attach it to.

## Scale caveat

Duration estimates use header-only `soundfile.info()` reads (RIFF/FLAC
header parse, no PCM decode) on a random sample, extrapolated by file count.
For `slurp` (141,652 `.flac`) and `audio2tool` (36,419 `.wav`) the file
count exceeds the 20,000-file exploration cap used for the file *listing*;
the hour estimates above are corrected to use the true total file count, not
the capped sample-pool size. For `minds14`, the per-locale directories are a
re-partition of the same rows already counted in `all/` (verified equal via
exact Parquet row-group counts: 8,168 = 8,168) — the reported scale uses the
deduplicated count.
