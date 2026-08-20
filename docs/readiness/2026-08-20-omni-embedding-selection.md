# Dedicated speech↔text embedding model — selection ticket (P-EMB-3)

Date: 2026-08-20. Status: **SELECTION TICKET — recommendation only.** No install, no download, no
model run, no tool contact was performed to produce this document. It discharges the
"selection ticket pending" cell added to `docs/readiness/2026-08-19-scheme-scoreboard.md` at
`833b6c9` and the "selection survey in flight" reference in
`docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md` §3.

**Primary recommendation: `LCO-Embedding/LCO-Embedding-Omni-3B-2605`** (Apache-2.0, ungated,
9.4 GB, dim 2048).
**Fallbacks, in order: `jinaai/jina-embeddings-v5-omni-small-retrieval` → `facebook/SONAR`
(`sonar_speech_encoder_eng` + `text_sonar_basic_encoder`) → `nvidia/omni-embed-nemotron-3b`.**
**Rejected on published evidence: the entire CLAP family.**

---

## 1. Requirements recap

### 1.1 Why an external instrument is on the table at all

P-EMB-1 (`EMB-WEAK`, 3/60, below the 1/18 = 0.0556 chance rate, permutation P = 0.8774) and
P-EMB-2 (`EMB-CLOSED`, 2/183 top-1, top-5 *below* chance, **400/400 winning cosines negative**,
15 of 152 tools ever predicted) established that the frozen generation core's mean-pooled
mmproj states do not form a shared audio/text semantic space
(`docs/readiness/2026-08-19-pemb2-verdict.md` §3, §5.1 rows 3–4). The surviving explanation
named there is mechanical: *a generative decoder with no contrastive objective does not place
mean-pooled audio and mean-pooled text in a shared space.*

The owner correction of 2026-08-20 (`833b6c9`) scoped that refutation: it covers **generation-core
pooled states only**. It never tested an embedding model **trained** for cross-modal semantic
alignment. This ticket selects that instrument.

### 1.2 The task the instrument must serve

The two registered P-EMB constructions, re-run unchanged on the dedicated space:

| construction | audio side | text side | candidates | comparator |
|---|---|---|---|---|
| **P-EMB-1 surface** (the smoke) | frozen 60 SLURP devel clips, split identity hash `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` | 18 canonical scenario labels, bare strings | 18 | chance 0.0556; cited local mean-bare 0.0500; closed-set decode router 0.7833–0.8167 |
| **P-EMB-2 surface** (only if the smoke passes) | 400 frozen Audio2Tool discovery clips | 152 shipped tool registry rows (`data.audio2tool.render_registry_row`, `strip_defaults=False`) | 152 | chance 0.0066; cited local 0.0109 on the 183 |

Operationally this is **utterance-level zero-shot cosine matching of a speech embedding against a
small set of short text descriptions**. That is a specific evaluation protocol and it is *not* the
protocol most audio-embedding literature reports (see §2.2) — this is the single most important
constraint on how published numbers may be read.

### 1.3 Hard constraints

- **Charter.** The instrument enters under the study charter's one permitted opening: *"A frozen
  tool-level retriever/judge is allowed only when pinned and logged; final answer authority stays
  with the frozen core."* It is a **retriever**, never an answerer. See §7 for the governance
  question this raises.
- **Zero training.** Inference only; no fine-tuning, no adapters, no probes fitted on our data.
- **Pinnable.** A repo revision SHA plus per-file hashes, resolvable offline thereafter.
- **Local + offline.** Runs on RTX 5090 (sm_120), WSL2 Ubuntu-24.04, torch cu128.
- **Isolated venv.** Never `~/.venvs/speechrl`. (Prior incident on record: an editable install in a
  clone repointed the shared venv.)
- **llama.cpp is NOT a constraint here.** That pin binds the frozen *core*. A tool-level retriever
  is a transformers/sentence-transformers process in its own environment.
- **Speech semantics, not acoustics.** The charter's research boundary is human speech and its
  linguistic content. An instrument whose audio side scores environmental sound events is
  out-of-boundary as well as useless for this task.

---

## 2. Evidence base and its limits

### 2.1 Method

The survey ran on 2026-08-20. **The session's WebSearch budget (200/200) was exhausted before the
first query**, so the survey was conducted entirely through WebFetch against structured
endpoints: the Hugging Face model API (`/api/models?search=`, `/api/models/<id>`,
`/api/models/<id>/tree/main`), raw model cards and configs, the arXiv listing API, and arXiv
abstract/HTML pages. This is a *narrower* instrument than keyword search: it enumerates well
by repo-name substring but cannot find a model whose name contains none of the probed strings.
Probed name-spaces: `sonar`, `omni embedding`, `omni-embed`, `speech embedding`, `gme`, `clap`.

**Second-hand-read caveat.** WebFetch answers a prompt against a page using a small summarizing
model. Every number below is a *summarizer's read* of the source, not a direct byte-level
extraction. The MAEB Table 2 extraction in §2.3 in particular showed an internal inconsistency
(the Borda-count rank column is not monotonic in the Overall column — which the paper's stated
Borda methodology may legitimately explain, or which may be an extraction artifact). **No number
in this ticket may be quoted in a verdict document without re-verification against the source
PDF.** The *qualitative* separations in §2.3 are large enough (4–5×) to survive plausible
extraction error, and they agree with the papers' own prose findings, which is why the
recommendation rests on them.

### 2.2 The protocol that matters

MAEB (`arXiv:2602.16008`, *Massive Audio Embedding Benchmark*, El Assadi et al., 2026-02-17,
30 tasks, 100+ languages, 50+ models, integrated into MTEB) separates two categories that are
routinely conflated:

- **Classification** — *"A logistic regression is trained on audio embeddings to predict
  labels … with 8 examples per class."* A few-shot linear probe. **This is not our setting.**
  Our probe fits nothing.
- **Zero-shot Classification** — *"Audio embeddings are directly matched to class labels
  converted to text prompts (e.g. 'This is a sound of dog bark') without training a
  classifier."* **This is exactly our setting.**
- **Retrieval** — cross-modal audio↔text (CommonVoice, FLEURS: speech against its transcript).
  Closest published analogue for our tool-row matching, though it is transcript-identity
  retrieval rather than label abstraction.

Consequence: a model's headline "classification" score is largely irrelevant to us, and the
columns that predict P-EMB-3 are **zero-shot classification** and **cross-modal retrieval**.

A second consequence is a genuine evidence gap that must be stated: MAEB's zero-shot tasks are
`ESC50_Zeroshot`, `RavdessZeroshot`, `SpeechCommandsZeroshot v0.01/v0.02`, `UrbanSound8kZeroshot` —
environmental sound, emotion, and isolated keyword spotting. **No public benchmark reports
zero-shot utterance→intent-label matching**, our exact task. MInDS-14 (multilingual intent from
speech) exists in MAEB but sits in the *probe* category. So **no candidate has direct published
evidence for the P-EMB-3 task**; the selection is made on the nearest two proxies plus mechanism.

### 2.3 The decisive published separation

MAEB Table 2, as extracted (see the caveat in §2.1). Columns are percentages.

| model | Overall | Classification (probe) | **Zero-shot** | Clustering | **Retrieval** |
|---|---|---|---|---|---|
| **LCO-Embedding-Omni-7B** | 52.2 | 67.3 | **64.5** | 1.7 | **50.3** |
| **LCO-Embedding-Omni-3B** | 50.7 | 66.7 | **62.2** | 1.3 | **50.3** |
| Qwen2-Audio-7B | 33.7 | 56.9 | 12.4 | 12.7 | 1.6 |
| larger_clap_general | 32.2 | 51.9 | 14.9 | 6.6 | 9.8 |
| larger_clap_music_and_speech | 31.9 | 52.1 | 13.2 | 7.7 | 9.3 |
| clap-htsat-fused | 30.7 | 52.0 | 13.2 | 22.7 | 9.2 |
| clap-htsat-unfused | 30.0 | 52.6 | 11.3 | 12.5 | 8.8 |
| msclap-2023 | 31.1 | 53.6 | 12.6 | 15.2 | 9.4 |
| wav2clip | 25.5 | 53.6 | 10.8 | 6.0 | 1.0 |
| Whisper-large-v3 (encoder) | 42.1 | 52.5 | — | 3.4 | — |
| ast-finetuned-audioset | 44.2 | 51.2 | — | 6.9 | — |

`jina-embeddings-v5-omni-small` is not in MAEB Table 2 (it postdates the benchmark); its own paper
(`arXiv:2605.08384`, Table 3) self-reports on MAEB: **aggregate 50.77**, retrieval/reranking 53.56,
classification/zero-shot 55.89, text-matching 62.40, clustering 5.99.

Three separations carry the decision:

1. **LCO-Embedding-Omni beats every CLAP variant by ~5× on zero-shot (62–65 vs 11–15) and ~5× on
   cross-modal retrieval (50.3 vs 8.8–9.8).** Those are the two columns that match P-EMB-3.
2. **CLAP is at chance on speech intent.** The paper states directly: CLAP variants *"score below
   15% across all languages on MInDS-14, near random chance for intent classification."*
3. **The paper's structural finding is the mechanism we care about**: *"contrastive audio-text
   models excel at environmental sound tasks but underperform on multilingual speech, while
   speech-pretrained models show inverse patterns"* — models *"excelling on acoustic understanding
   often perform poorly on linguistic tasks, and vice versa."* Speech-LLM-derived contrastive
   embedders (LCO) are the family that sits on the linguistic side while still having a text tower.

---

## 3. Candidate matrix

Sizes are repo bytes from the HF tree API. "Speech vs general audio" is the orientation of the
**audio side**.

| # | candidate | HF repo + revision | license / gating | size on disk · dim | speech vs general audio | published evidence nearest our task | pinnability | integration cost | fit for P-EMB-3 |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **LCO-Embedding-Omni-3B-2605** | `LCO-Embedding/LCO-Embedding-Omni-3B-2605` @ `5f6b5329da5141367da30e06a9826d1322d6c9b2` | **apache-2.0**, ungated | **9.40 GB** bf16 (2 shards) · **2048** | Qwen2.5-Omni audio tower (32-layer, d=1280, Whisper-large-v3 lineage) + **contrastive retrieval training** → linguistic side | family: zero-shot **62.2**, retrieval **50.3** (MAEB, Oct-2025 3B); 2605 claims *"substantial improvements on all 4 modalities"* | ✅ commit SHA + per-file hashes; ungated | **low** — `SentenceTransformer(...)`; authors publish the exact export stack: torch **2.10.0+cu128**, transformers **5.6.0**, sentence-transformers **5.4.0** | **best** — trained *for asymmetric retrieval*, which is what audio-query → text-row matching is |
| 2 | jina-embeddings-v5-omni-small-retrieval | `jinaai/jina-embeddings-v5-omni-small-retrieval` (+ base `…-omni-small` @ `87f7a45d1ae0265843f8569c47fb53847cb193c3`) | **cc-by-nc-4.0**, ungated, `region:eu` | **3.13 GB** single safetensors · **1024** | Qwen2.5-Omni audio encoder (Whisper-large-v3 adapted), **frozen**; only a projection trained (GELATO: 0.35 % of weights). Audio training mix: music 55.0 %, environmental 25.5 %, **English speech 14.2 %**, multilingual speech 3.1 % | MAEB aggregate **50.77** (self-reported) — parity with LCO-3B at 1/3 the parameters | ✅ SHA; ungated | **medium** — `trust_remote_code` (`custom_st.py`, `modeling_qwen3vl_audio.py`) | good; the best size/quality ratio, but its audio alignment budget went mostly to non-speech |
| 3 | SONAR (speech ENG + text) | `facebook/SONAR` (text `sonar_text_encoder.pt`, 3.06 GB) **+ `spenc.eng.pt` from `dl.fbaipublicfiles.com/SONAR/`** | **cc-by-nc-4.0**, ungated | text 3.06 GB; ENG speech encoder size **unpublished** (sibling `v3ap`/`v5ap` encoders are 8.60 GB each) · **1024** | **purely speech-linguistic** — w2v-BERT 600M init, teacher-student MSE against the *transcript's* sentence embedding; ENG trained on CommonVoice-12 + MuST-C + VoxPopuli + LibriSpeech | English speech↔text xsim *"saturates to zero error rate on FLEURS"*; the paper's own framing is that xsim is too easy at this point | ⚠️ **weakest** — the English encoder is **not on HF**; it is a bare URL on `dl.fbaipublicfiles.com` with no revision and no published hash. We would have to self-hash on first fetch. | **medium-high** — `sonar-space` 0.5.0 → `fairseq2>=0.5.2` + `fairseq2n` native ext (Linux-only; WSL2 OK; prebuilt wheels do cover **cu128**) | **strong on mechanism, weak on protocol** — it is a symmetric *sentence-translation* space, never retrieval-tuned. A 5.4 s utterance embeds near its transcript; matching that to a bare one-word label like `alarm` is exactly the short-vs-long asymmetry a translation space is not built for — the same asymmetry that P-EMB-2 tried and failed to fix from the text side |
| 4 | omni-embed-nemotron-3b | `nvidia/omni-embed-nemotron-3b` @ `865db1bb57e369a85357cf114cbd6b3c5322d19d` | `license: other` — **NVIDIA OneWay Noncommercial + Qwen Research License**; research use permitted; ungated | **9.43 GB** · **2048** | same base as #1 (Qwen2.5-Omni-3B Thinker), different contrastive recipe | audio numbers are **video-soundtrack retrieval**: LPM audio-only nDCG@10 0.8238, FineVideo audio-only 0.5407 — not speech-semantic | ✅ SHA | **medium-high** — pins `transformers==4.51.3` *from a specific GitHub branch*, which conflicts with #1's stack and would need its own venv | useful **control** (same base, different objective) more than a primary |
| 5 | LCO-Embedding-Omni-7B | `LCO-Embedding/LCO-Embedding-Omni-7B` @ `108f6f1a5de3b2eedd1d1c7b7005aaca6ed3802c` | apache-2.0, ungated | **17.88 GB** · 3584 (7B) | as #1 | **MAEB rank 1**: zero-shot **64.5**, retrieval **50.3** | ✅ SHA | low (same stack) | best raw numbers; +2.3 zero-shot over the 3B for +8.5 GB. Escalation target if the 3B lands `INCONCLUSIVE` |
| 6 | Tevatron/OmniEmbed-v0.1 | `Tevatron/OmniEmbed-v0.1` | **MIT** (cleanest license found), ungated | Qwen2.5-Omni-7B base | Whisper-lineage audio tower | audio evidence is **AudioCaps R@1 34.0** — audio *captioning*, i.e. sound-event description, not spoken content | ✅ | low | deprioritized: its only audio number is a general-audio task |
| 7 | BidirLM-Omni-2.5B-Embedding | `BidirLM/BidirLM-Omni-2.5B-Embedding` | apache-2.0, ungated | 2.5B · 2048 | Qwen3 base, audio accepted as raw arrays @16 kHz | cites "MAEB (beta)" without published per-task numbers | ✅ | medium — requires **cuDNN > 9.20.0**, an extra environment constraint | thin evidence; hold |
| **✗** | **CLAP family** — `laion/clap-htsat-unfused`, `laion/clap-htsat-fused`, `laion/larger_clap_general`, `laion/larger_clap_music_and_speech`, `microsoft/msclap` | apache-2.0, ungated | small (~0.6–1.6 GB) | **general audio events + music.** LAION-CLAP trains on LAION-Audio-630K, *"633,526 audio-text pairs"* of sound-event captions. Even the variant literally named `music_and_speech` scores 13.2 zero-shot. | **zero-shot 10.8–14.9, retrieval 8.8–9.8; below 15 % on MInDS-14 intent, "near random chance"** | ✅ | trivial | **REJECT.** Stated plainly, as the brief asked: the CLAP audio side is general-audio-event/music oriented, and the one published number on speech intent classification is at chance. Adopting it would reproduce P-EMB-1/2's attractor collapse with a different set of attractors. |
| ✗ | GME family | `Alibaba-NLP/gme-Qwen2-VL-{2B,7B}-Instruct` | apache-2.0 | — | **no audio modality at all** (Qwen2-VL: text + image + video) | — | — | — | **not applicable** — checked because the brief named "GME audio"; no audio variant exists |

---

## 4. Recommendation

### 4.1 Primary — `LCO-Embedding/LCO-Embedding-Omni-3B-2605`

Five reasons, in order of weight:

1. **It is the only family with strong published numbers on both columns that match our protocol.**
   Zero-shot 62.2 and cross-modal retrieval 50.3, against 11–15 and 8.8–9.8 for every CLAP variant
   and 12.4 / 1.6 for Qwen2-Audio-7B. Our task is zero-shot text-label matching; this is the
   measurement that predicts it.
2. **It is the clean scientific ablation of our own negative.** Its base is a Qwen2.5-Omni
   *thinker* — the same architectural family as our frozen Qwen3-Omni core, same Whisper-lineage
   audio tower — with **one** difference: a contrastive refinement stage. P-EMB-1/2 concluded the
   failure was "no contrastive objective, therefore no shared space." Running the identical
   construction on the identical architecture *plus* a contrastive objective converts that
   conclusion from an inference into a measured contrast. No other candidate isolates the variable
   this cleanly.
3. **Apache-2.0, ungated.** The cleanest license in the top tier. SLURP and Audio2Tool already
   force CC BY-NC 4.0 onto every audio-derived number; choosing an NC *model* on top would add a
   second NC carry for no benefit. (jina and SONAR are both CC BY-NC 4.0.)
4. **Lowest integration cost, and the pin is published for us.** `config_sentence_transformers.json`
   in the repo records the authors' exact export stack — torch `2.10.0+cu128`,
   transformers `5.6.0`, sentence-transformers `5.4.0`, `similarity_fn_name: cosine`. **cu128 is our
   stack**; sm_120 is covered. Usage is a `SentenceTransformer.encode()` call over file paths.
5. **Sized right.** 9.40 GB bf16 → roughly 11–13 GB peak VRAM on 5.4 s clips; comfortable on a
   32 GB 5090, and — unlike the local probes — **it does not contend with the frozen core's
   llama-server for the same weights**, because it is a separate process holding separate weights.
   It still should not fly concurrently with a generation campaign; see §6.

**Two risks to carry.** (a) The `-2605` checkpoint is *not* the checkpoint MAEB scored; MAEB scored
the October-2025 `LCO-Embedding-Omni-3B`. The May-2026 card claims improvement on all four
modalities but publishes no MAEB delta. Mitigation: this is why P-EMB-3 is a smoke first (§6), and
why `LCO-Embedding-Omni-3B` (Oct-2025, the actually-scored checkpoint) is named as an in-family
fallback. (b) It carries a **default prompt** — the Qwen system persona string — in
`config_sentence_transformers.json`. Since P-EMB-1's binding decision was *no instruct prefix on
either side*, the prompt handling is a construction variable that must be frozen explicitly and
hashed, not inherited by accident.

### 4.2 Fallback ladder

1. **`jinaai/jina-embeddings-v5-omni-small-retrieval`** — if VRAM, disk, or the transformers-5.x
   stack becomes a problem. 3.13 GB, MAEB 50.77 at parity with LCO-3B. Costs: CC BY-NC 4.0,
   `trust_remote_code`, and an audio alignment budget that was only 14.2 % English speech with a
   *frozen* audio encoder — the paper itself flags audio-encoder adaptation as future work.
2. **`facebook/SONAR`** — if both omni embedders fail and the diagnosis is "the audio side isn't
   really speech-semantic." SONAR is the purest speech↔text sentence space available and its
   English speech-text retrieval is saturated-good. Take it knowing that its weakness is on the
   *protocol* (symmetric translation space vs. our short-label asymmetry) and on *pinning* (the
   English encoder has no HF revision — self-hash required).
3. **`LCO-Embedding/LCO-Embedding-Omni-7B`** — escalation inside the primary family if the 3B lands
   `INCONCLUSIVE` rather than clearly negative. +2.3 zero-shot, same stack, +8.5 GB.
4. **`nvidia/omni-embed-nemotron-3b`** — as a *control*, not a primary: identical base to the
   primary, different contrastive recipe, so a disagreement between them is informative about
   recipe sensitivity. Held back because of the `transformers==4.51.3`-from-a-branch pin and the
   noncommercial license.

### 4.3 Explicit rejection

**CLAP (LAION-CLAP and MS-CLAP) is rejected, and the brief's suspicion is confirmed: its audio
side is general-audio-event and music oriented, not speech-semantic.** LAION-CLAP's training set is
633,526 sound-event/caption pairs; MAEB puts every CLAP variant at 10.8–14.9 zero-shot and
8.8–9.8 cross-modal retrieval, and below 15 % — *"near random chance"* — on MInDS-14 speech intent.
The variant explicitly named `larger_clap_music_and_speech` scores 13.2 zero-shot, which is the
cleanest available demonstration that the "speech" in that name does not mean spoken *content*.
Adopting CLAP would buy a second attractor-collapse verdict, not a shared space.

---

## 5. Isolated-venv install plan

**No step below has been executed.** Both steps require the authorizations in §7 first.

### 5.1 Environment — new, isolated, never `~/.venvs/speechrl`

```bash
# WSL2 Ubuntu-24.04. Run from a scratchpad script file, not an inline wsl.exe string.
python3.12 -m venv ~/.venvs/saea-omniemb
source ~/.venvs/saea-omniemb/bin/activate
python -m pip install -U pip

# torch first, from the cu128 index, matching the checkpoint's published export stack
pip install --index-url https://download.pytorch.org/whl/cu128 \
    torch==2.10.0 torchaudio==2.10.0

pip install \
    "transformers==5.6.0" \
    "sentence-transformers[audio]==5.4.0" \
    "accelerate" "safetensors" "soundfile" "librosa==0.11.0" "numpy==2.2.6"
```

Guard rails, all mandatory:

- **Never `pip install -e` this study (or any repo) into this venv**, and never activate
  `~/.venvs/speechrl` in the same shell. Prior incident on record: an editable install in a clone
  repointed the shared venv.
- Export `PYTHONDONTWRITEBYTECODE=1` for every invocation — bytecode under a frozen scoring package
  fails the D3 gate.
- Pin `librosa`/`soundfile` to the versions already on record as the study's decoders. **Do not
  install ffmpeg**: its absence is pinned, and introducing it would change decoded bytes and cold
  the featcache.
- Emit `pip freeze > docs/receipts/<date>-omniemb-venv.txt` as the environment receipt.

### 5.2 Model download

```bash
export HF_HOME="$SPEECHRL_DATA_DIR/hf-cache"        # keep cache off the small ext4 root
export TARGET="$SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-2605"

hf download LCO-Embedding/LCO-Embedding-Omni-3B-2605 \
    --revision 5f6b5329da5141367da30e06a9826d1322d6c9b2 \
    --local-dir "$TARGET"

# receipt: per-file SHA-256 over the materialized directory
( cd "$TARGET" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) \
    > docs/checks/speech-aware-evidence-acquisition/<date>-omniemb-acquisition/MANIFEST.sha256
```

Expected footprint, from the HF tree API:

| file | bytes |
|---|---|
| `model-00001-of-00002.safetensors` | 4,994,841,696 |
| `model-00002-of-00002.safetensors` | 4,412,249,056 |
| `tokenizer.json` | 11,421,870 |
| `vocab.json` | 2,776,833 |
| `merges.txt` | 1,671,853 |
| `model.safetensors.index.json` | 116,180 |
| `spk_dict.pt` | 259,544 |
| configs + templates (10 files) | < 25 KB total |
| **total** | **≈ 9.40 GB** |

Fallback footprints for planning: jina retrieval 3.13 GB (single `model.safetensors`
3,118,864,032 B + `custom_st.py` + `modeling_qwen3vl_audio.py`); SONAR text 3.06 GB + ENG speech
encoder (size unpublished; budget 8.6 GB by analogy with the `v3ap`/`v5ap` siblings);
LCO-7B 17.88 GB; nemotron-3b 9.43 GB.

### 5.3 Registration before download

The download is only legitimate after an entry lands in umbrella `docs/datasets.lock.json` — the
single live source of model/dataset identity — following the existing model-entry shape:

```jsonc
{ "name": "lco-embedding-omni-3b-2605", "kind": "model",
  "local_subdir": "models/lco-embedding-omni-3b-2605",
  "source": { "kind": "hf", "id": "LCO-Embedding/LCO-Embedding-Omni-3B-2605" },
  "revision": "5f6b5329da5141367da30e06a9826d1322d6c9b2",
  "status": "COMPLETE", "size_bytes": <measured>, "files": <measured>,
  "factor_family": "model",
  "note": "tool-level retriever for P-EMB-3 under the charter retriever clause; Apache-2.0; NOT an answering model" }
```

That file is umbrella-owned, so the lock edit and this study's ticket are **two commits in two
repositories**. Acquisition itself is a `model-free-check` (download + hash, zero inference) and
gets its own ledger row.

---

## 6. Bounded P-EMB-3 smoke plan

**Separately registered before any contact.** This section is a *plan for a registration*, not a
registration, and authorizes nothing.

### 6.1 Gate — this plan does not start until P-EMB-3L reports

`SAEA-PROBE-pemb3l-234` (registered `18da9a9`, ledgered `eccf7f8`, `consumed = no`) sweeps the
remaining training-free constructions on the **local** core (last-bare / last-instruct /
mean-instruct). Per its §3, the external path opens only on **`LOCAL-EXHAUSTED`** (every arm
≤ 0.15). On `LOCAL-SPACE-EXISTS` (any arm ≥ 0.30) external adoption is **deferred** and this
ticket goes to the shelf. On `INCONCLUSIVE-EMB3L` the decision returns to the owner. **Fly P-EMB-3L
first.**

### 6.2 The smoke — `SAEA-PROBE-pemb3-78`

Re-run the **P-EMB-1 surface verbatim** on the dedicated space: the frozen 60 SLURP devel clips
(split identity hash `fc9de436…5ee5`, the same subset already consumed by P-SLU/P-KEY/P-EMB-1 — no
new sample identity) + the 18 canonical scenario labels as bare strings = **78 embedding contacts,
zero generation**. Prediction: argmax cosine. L2-normalize both sides so cosine = dot. Gold
scenarios scoring-side only.

Held constant against P-EMB-1 so the comparison is clean: same 60 samples, same 18 label strings,
same argmax-cosine matcher, same manifest and hashing discipline, same pinned read suite
(`analysis/pemb_read.py`, extended by one evaluator, coordinator-reviewed **before** the read).
Changed: **only the embedding model**. The audio decoder stays librosa/soundfile.

**Construction, frozen and hashed at registration** (this is the one place the primary's default
prompt must be handled deliberately):

- Pooling: the checkpoint's own sentence-transformers pooling module — not re-derived by us.
- Prompt: the repo's default prompt is the Qwen system persona. Register **one** arm as the
  baseline with prompt handling explicitly declared (either the shipped default applied
  common-mode to both sides, or suppressed on both sides), the exact strings frozen with SHA-256.
  Do not let the default apply asymmetrically. A second prompt arm is a *later* probe, not part
  of this smoke.
- dtype bf16, `device=cuda`, deterministic ordering, vectors written to the data root with a
  hashed manifest; no vectors in Git.

### 6.3 Cost

≤ 90 embedding contacts; ≤ 400 metered audio-seconds; **≈ 5 minutes GPU** (≈ 1 min weight load
from the data root + ≈ 1–2 min for 78 encodes); ≤ 0.2 GPU-h ceiling. It must take a GPU gap, not
contend with a generation campaign — a long mixed CPU-encode + GPU-decode campaign is what sticks
this GPU's P-state at 232 MHz. Check `clocks.sm` before and after.

### 6.4 Verdicts (to be registered; chance = 1/18 = 0.0556)

Calibrated against the arc's existing comparators — cited local mean-bare **0.0500** and the
closed-set decode router **0.7833–0.8167**:

- **ALIGNED-SPACE-EXISTS**: accuracy **≥ 0.50**. A dedicated aligned space does what the
  generation core's pooled states cannot. Advances to the P-EMB-2 surface (400 A2T clips × 152
  registry rows) under a *separate* registration.
- **ALIGNED-WEAK**: accuracy **≤ 0.15**. Even a purpose-trained aligned space does not route this
  task; the embedding channel closes for good and the routing tier stays decode-based, now on
  three independent instruments rather than two.
- Otherwise **INCONCLUSIVE-EMB3**: report per-label confusion, the attractor structure (how many
  of 18 labels are ever predicted — the diagnostic that exposed both prior collapses), and the
  winning-cosine distribution (P-EMB-2's `400/400 negative` is the signature to check against).
  Escalation on INCONCLUSIVE: the 7B, *not* a prompt sweep.

Mandatory reported diagnostics either way, because they are what made the P-EMB-1/2 negatives
interpretable rather than merely disappointing: distinct labels ever predicted, most-predicted
label share, winning-cosine min/mean/median/max and the count of positive cosines, and a
permutation test on the prediction vector (N = 100,000, seed 20260807, matching the prior reads).

### 6.5 Discipline

One-shot read. Exposure row `SAEA-PROBE-pemb3-78` appended at registration with `consumed = no`,
**before** any result is read. Tool contacts are ledgered exactly as frozen-core contacts are.
Clean tree for the run's whole duration (a dirty tree kills manifest finalize).
`PYTHONDONTWRITEBYTECODE=1` throughout. Gold labels scoring-side only, never runtime.
SLURP CC BY-NC 4.0 carried on every number. No test split.

---

## 7. Blockers and open governance questions

1. **Sequencing blocker (hard).** P-EMB-3L must fly and return `LOCAL-EXHAUSTED` first. This
   ticket is a recommendation held in reserve behind that gate.
2. **Charter question for the owner (the one real one).** The charter states *"zero-parameter
   training; no task-trained model; no second answering LLM"* and separately permits *"a frozen
   tool-level retriever/judge … when pinned and logged."* A pinned public embedding model is not
   trained on our task and never answers — it enters under the retriever clause. But
   `LCO-Embedding-Omni-3B-2605` is *derived from a generative thinker and retains the capacity to
   generate*. Two things follow: the owner should confirm the retriever-clause reading in writing,
   and the integration must **structurally forbid generation** — the wrapper exposes `encode()`
   only, never `generate()`, and that should be a machine check, not a convention.
3. **Asset-lock dependency.** The umbrella `docs/datasets.lock.json` entry (§5.3) is a
   cross-repository change and must land before download.
4. **Evidence-quality caveat (§2.1).** Every number here is a summarizer's read of a web page.
   Before any of it is cited in a verdict, re-verify against the source PDFs — especially MAEB
   Table 2, whose rank column did not reconcile with its overall column in the extraction.
5. **The genuine evidence gap (§2.2).** No public benchmark measures zero-shot utterance→intent
   matching. Every candidate is selected on proxies (zero-shot sound/keyword classification;
   speech-transcript retrieval) plus mechanism. **P-EMB-3 is therefore a real experiment with a
   real chance of `ALIGNED-WEAK`**, and it should be registered with that expectation rather than
   as a formality confirming a better instrument.
6. **Checkpoint-vs-benchmark mismatch.** MAEB scored the Oct-2025 `LCO-Embedding-Omni-3B`; the
   recommendation is the May-2026 `-2605` refresh. If exact evidence-to-artifact correspondence is
   preferred over claimed improvement, pin the Oct-2025 checkpoint instead — that is a defensible
   owner-level swap and both are Apache-2.0.

---

## 8. Sources

- MAEB: Massive Audio Embedding Benchmark — https://arxiv.org/abs/2602.16008 ,
  https://arxiv.org/html/2602.16008v1
- SONAR: Sentence-Level Multimodal and Language-Agnostic Representations —
  https://arxiv.org/abs/2308.11466 , https://arxiv.org/html/2308.11466v1
- SONAR code, asset cards, install — https://github.com/facebookresearch/SONAR ,
  https://raw.githubusercontent.com/facebookresearch/SONAR/main/sonar/cards/sonar_speech_encoder.yaml ,
  https://pypi.org/pypi/sonar-space/json
- fairseq2 support matrix (torch/cu128/Python/OS) —
  https://raw.githubusercontent.com/facebookresearch/fairseq2/main/README.md
- SONAR weights + license + file sizes — https://huggingface.co/facebook/SONAR ,
  https://huggingface.co/api/models/facebook/SONAR/tree/main
- SONAR text encoder transformers port (dim 1024, CC BY-NC 4.0) —
  https://huggingface.co/cointegrated/SONAR_200_text_encoder
- LCO-Embedding — https://huggingface.co/LCO-Embedding/LCO-Embedding-Omni-3B-2605 ,
  https://huggingface.co/LCO-Embedding/LCO-Embedding-Omni-3B-2605/raw/main/config.json ,
  https://huggingface.co/LCO-Embedding/LCO-Embedding-Omni-3B-2605/raw/main/config_sentence_transformers.json ,
  https://huggingface.co/LCO-Embedding/LCO-Embedding-Omni-7B , https://arxiv.org/abs/2510.11693
- jina-embeddings-v5-omni (GELATO) — https://huggingface.co/jinaai/jina-embeddings-v5-omni-small ,
  https://arxiv.org/abs/2605.08384 , https://arxiv.org/html/2605.08384v1 ,
  https://huggingface.co/api/models/jinaai/jina-embeddings-v5-omni-small-retrieval/tree/main
- NVIDIA omni-embed-nemotron-3b — https://huggingface.co/nvidia/omni-embed-nemotron-3b
- Tevatron OmniEmbed — https://huggingface.co/Tevatron/OmniEmbed-v0.1
- BidirLM-Omni-2.5B-Embedding — https://huggingface.co/BidirLM/BidirLM-Omni-2.5B-Embedding
- LAION-CLAP — https://huggingface.co/laion/clap-htsat-unfused
- GME (audio-free, checked and excluded) —
  https://huggingface.co/Alibaba-NLP/gme-Qwen2-VL-2B-Instruct
