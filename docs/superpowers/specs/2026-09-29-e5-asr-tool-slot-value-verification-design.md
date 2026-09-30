# E5: frozen tool-level ASR for slot-value verification (design)

Date 2026-09-29. Carrier SLURP first (decision 187), transfer shape for Audio2Tool and Earnings
(decision 196). Status: **design only**. Nothing is registered or flown, and this document grants
no contact of any kind. It was written model-free: no model, tool, encoder, GPU, network or
paid-API contact. No utterance text, transcript, gold value or model output is quoted. Only
counts, rates, pp, ids, paths and hashes appear.

Authority chain:

- owner decision 180: "if the core is not natively effective at extracting some information, call
  an ASR tool to verify". The sequence is core-native re-listen first, Whisper after the E4 read.
- The E4 read has landed. E4-1's core-native blind + forced-choice re-listen is **SHADOW HARM**:
  replace-only SLU-F1 -4.11 [-5.41, -2.88]. 63 of the 122 accepted replacements turned EXACT values
  into BOUNDARY values, and only 7 repaired an item to EXACT
  (`docs/results/2026-09-29-slurp-e4-relisten-fold-a-column-read.md` sections 3-5).
- Decision 201 (proposed, pending the owner) opens the frozen tool-level ASR route (E5) for slot
  VALUE verification, offline-first. This spec is the design that decision would act on.

Charter clause (study `CLAUDE.md`, Research boundary): "A frozen tool-level retriever/judge is
allowed only when pinned and logged; final answer authority stays with the frozen core."

**Carried-forward direction that 201 must supersede explicitly.** The owner ruling of 2026-09-06
said there should be no transcript tokens anywhere in the system, and a weak core should be
answered by swapping the core. The E4 design already names this condition for any Whisper twin:
"an owner row that revises the 2026-09-06 direction for this twin"
(`docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md` section 5, item 1).
Decision 201 must be that row. It must also name the scope it revises: transcript text as
post-delivery verification evidence for entity values only. It must not revise supply to
Perception or Solver.

## 1. Inventory: what exists, and what is pinned

### 1.1 ASR and speech-tool assets

| asset | location | size | pinned? | how | used before on SLURP? |
| --- | --- | ---: | --- | --- | --- |
| Whisper large-v3, openai-whisper `.pt` checkpoint | `/home/chao/speech-tools/whisper-vad/models/whisper/large-v3.pt` | 3,087,371,615 B | **yes, study-level** | sha256 `e5b1a55b…1dadb` plus all 18 source/asset files, in `docs/readiness/2026-09-12-whisper-runtime-inventory-v1.json`. Successor inventory v2 covers the patched batched-beam source `openai_whisper-20250625-saea-beam-batch-v1` (`$DATA/prepared/SAEA-SLURP-NATIVE-SYSTEM-LIVE-SPEECH-PREPARE-V1/full-runtime-inventory-v2.json`, sha256 `e5e6d376…0427`). Patch: `docs/readiness/2026-09-12-slurp-whisper-recovery-v1/whisper-batched-beam.patch` | **yes** (section 1.3) |
| Whisper large-v3, HF transformers safetensors | `$DATA/models/whisper-large-v3` | 2.9 GB (11 files, 3,091,519,764 B) | **yes, umbrella lock** | `docs/datasets.lock.json` `models[]` entry `whisper-large-v3`: revision `06f233fe06e710322aca913c1bc4249a0d71fce1`, `model.safetensors` sha256 `a8e94b85…fd95`, profile `speech-aware-tools`, lifecycle AUXILIARY. CPU load smoke only: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-whisper-acquisition/README.md` | no. It was acquired for the Earnings-22 self-run anchor, which has not run |
| Whisper runtimes | venvs `~/.venvs/saea-whisper-gpu` (CUDA) and `~/.venvs/saea-whisper-vad` (CPU) | -- | **yes** | package versions in the runtime inventory (openai-whisper 20250625, torch 2.9.1, triton 3.5.1). Readiness: `docs/readiness/2026-09-12-local-speech-tool-readiness-complete-v1.json` | yes |
| MMS_FA forced aligner (torchaudio) | `$DATA/models/speech-tools/torch-hub` | 1.2 GB | yes, lock `mms-fa-torchaudio`, `model.pt` sha256 `20ef1296…c680` | CC-BY-NC-4.0, research only. Zero forwards so far. The lock note says the first runtime drive needs a tool-smoke ledger row | no. It is the candidate word-timing aligner for E5's span hook (section 4) |
| SenseVoice-small | `$DATA/models/sensevoice-small` | 894 MB | **no**: lock `asset_catalog` says `UNRESOLVED_LOCAL_SOURCE` / `UNRESOLVED_LOCAL_REVISION`, lifecycle LOCAL_CANDIDATE | -- | no |
| Voxtral-Mini-3B GGUF | `$DATA/models/voxtral-mini-3b-2507-gguf` | 99 MB on disk | **no**: not in the lock | the Q4_K_M file is 102,847,006 B and the mmproj is 126,836 B, so the holding looks incomplete for a 3B model and is not usable as found | no |
| LCO-Embedding-Omni-3B GGUF | `$DATA/models/lco-embedding-omni-3b-gguf` | 5.9 GB | yes, lock (Q8_0 `53a9898b…6d887`, mmproj `765beb61…a13a`) | an encode-only representation comparator. **Not an ASR tool**: it produces vectors, not text | not as ASR |
| whisper.cpp / faster-whisper builds | -- | -- | **absent** | no build or venv found under `/home/chao` | -- |

### 1.2 Existing Whisper plumbing in the study repo (reuse; do not rebuild)

- **Backend.** `src/speech_aware_evidence_acquisition/core/speech_observation_backend.py`
  (`LocalWhisperBackend`) does bounded local decoding with the following limits:
  - utterances of 30 s or less at 16 kHz;
  - `device` is either `cpu` with `fp16=false`, or exactly one `cuda:N`;
  - `cpu_thread_limits` apply on CPU only;
  - the backend refuses concurrent or truncated requests.
- **Prepared-evidence producer.** `core/speech_preparation_runtime.py` and
  `core/preparation_speech_observations.py` implement the producer. Each per-row artifact is
  `saea-prepared-artifact-v1` with `contact_class: "speech-tool"`. Beside it sits a
  `*.speech-tool-started.json` marker written before the forward. The catalog schema is
  `saea-prepared-speech-observation-catalog-v1`. Each catalog pins:
  - `checkpoint_receipt`, the runtime inventory;
  - `decoding_config_sha256`;
  - the execution plan;
  - the exposure-ledger row by `relpath`, `row_id` and `sha256`;
  - `protocol_sha256`;
  - `use_split_identity_hash`;
  - one row per source, carrying the source-audio relpath and sha256, the packet id and sha256,
    the span, and the artifact and output sha256.
- **Consumer and tool rows.**
  - `rails/speech_observation.py` (`load_speech_observation_catalog`) validates every pin above and
    refuses a `contact_class` other than `speech-tool`.
  - The catalog tool is `saea-tool-prepared-speech-observation-v1` (`rails/tools.py:1539`,
    `cost_class="cpu"`, `axis="OBS"`, `ledger_row_type="tool-contact"`). The on-demand forms are
    `saea-tool-live-speech-observation-v1` and `saea-tool-live-speech-span-v1` (`:1561`, `:1595`,
    backed by `rails/live_speech_observation.py`).
- **Catalog gate.** `scripts/checks/tool_catalog_check.py` enforces four things:
  1. every manifest re-validates, including the 64-hex pin and the rule "a `contact` cost class
     needs a ledger row";
  2. the pin equals the sha256 of the wrapped function's source;
  3. no wrapper imports a framework LLM, MCP or REST tool;
  4. every registration goes through `build_tool_entry`.
- **Audio hand-off today.**
  - E4's `rails/relisten.py` does **not** cut audio. It re-sends the **same packet** (about 2.9 s,
    no derived media; E4 spec section 0).
  - The only byte-changing tool is `saea-tool-slice-encode-v1`, which emits a
    `saea-slice-derivation-v1` record (`rails/tool_wrappers/slice_encode.py`).
  - Derived media must live under `$SPEECHRL_DATA_DIR/derived/<variant>/` with a declared root
    and a hash-pinned D1 supplement. `scripts/checks/derived_media_confinement_check.py` proves the
    binding, and proves that a no-declaration payload, a decoy file and a foreign declaration are
    each refused.
  - SLURP E5 needs **no derived media**: Whisper reads the original full-utterance FLAC, which is
    the same source the packet binds.
- **Whisper-normalised scoring.** The `asr-wer-whisper` and `entity-wer` scorers beside
  `saea-scoring-v1` (Earnings-21 corpus WER 8.200 under `EnglishTextNormalizer`;
  `docs/results/stage2-results-ledger.md:124-131`) are **scoring-side only**. E5 must not reuse the
  Whisper normaliser as its runtime canonicaliser, because it rewrites number words to digits in
  the direction opposite to SLURP's written convention. Section 2.2 names the canonicaliser to
  use instead.
- **E22 encoding-pad finding.** This concerns only the llama.cpp mtmd front end of the **core**
  (Qwen3-A mel pad). The Whisper path does not use it, so the finding does not transfer to E5.

### 1.3 Prior Whisper exposure to inherit (never re-counted as new)

| row | split | contacts | device | what it was |
| --- | --- | ---: | --- | --- |
| `SAEA-SLURP-WHISPER-OBSERVATIONS-V1` + `-RECOVERY-V1` | DEV-1000 (`8580d199…`) | 8 aborted + 1,000 | GPU `cuda`, fp16, batch 8, beam 5, `sample_len` 224 | the full-utterance catalog `slurp-dev1000-whisper-large-v3-full-utterance-recovery-v1` |
| `SAEA-SLURP-SPEECH-OBSERVATION-WHISPER-TRANSPORT-RECOVERY-V1` vs `-CONTROL-V1` | DEV-1000 | 3,000 core contacts each | -- | **fixed transcript supply** to plan/solve/revise: EFFECTIVENESS_NOT_ESTABLISHED. NEW500 SLU micro +0.83 [-1.10, +2.83]; DEV-1000 intent -0.90 [-1.68, -0.09] (`docs/readiness/2026-09-12-slurp-fixed-whisper-result-v1.md`) |
| `SAEA-SLURP-NATIVE-CANDIDATE-REFRESH-TOOLS-TRAIN-FOLD-A-ASR(-RECOVERY)-V1`, `SAEA-SLURP-NATIVE-BOUNDED-EVIDENCE-TRAIN-FOLD-A(-RECOVERY)-ASR-V1` | **TRAIN Fold A** (`61b0f062…`) | 1 + 9 + 11 + 66 = 87 artifacts. The unique-row union is at most 87 and is computed by E5-0 step 1 | CPU fp32, beam 5, 1 worker × 4 threads | Reviewer-selected live ASR. The artifacts sit under `$DATA/prepared/<run>/` |

Two consequences follow:

- Fold A is **not** Whisper-naive. E5-0's ledger row inherits these 87 decodes.
- The only full-roster SLURP Whisper result is the fixed-supply one, and it was intent-negative.
  E5 therefore keeps the transcript **away from intent** by construction (section 2.3).

## 2. The mechanism, staged

### 2.1 E5-0: one pinned ASR pass (tool contact, no core contact)

**What.** One `speech-tool` contact per row over the TRAIN Fold A roster:

- 1,080 rows, split hash `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`;
- source export `SAEA-SLURP-TRAIN-A-LIVE-SPEECH-SOURCES-PREPARE-V1`, already landed;
- 3,085 speech s in the Fold A ASR plans, **about 2.86 s per row, not 4 s**.

A second pass covers TRAIN Fold B (1,080 rows) for tuning. Fold A is the read roster, and Fold B
is the only roster on which rule parameters may be chosen (section 2.2).

**Producer.** The existing `core.speech_preparation_runtime` entry writes a new catalog. The
protocol is the recovery DEV-1000 GPU protocol, byte for byte in its decode fields:

- `batch_size` 8, `beam_size` 5;
- `device` `cuda`, `fp16` true;
- `language` `en`, `task` `transcribe`, `temperature` 0;
- `sample_len` 224, `without_timestamps` true;
- `no_speech_threshold` 0.6, `logprob_threshold` -1.0.

Timestamps stay off. Word timing, if a later stage needs it, comes from MMS_FA (section 4) and is
never produced by this pass. The output is:

- `$DATA/prepared/SAEA-SLURP-ASR-TOOL-PASS-V1/<attempt>/catalog.json` plus per-row artifacts;
- catalog id `slurp-train-fold-a-whisper-large-v3-full-utterance-v1`, with a Fold B sibling;
- never in Git, and never printed.

**Ledger row, written before any result is read.** Row `SAEA-SLURP-ASR-TOOL-PASS-V1`:

- profile `bounded-discovery-probe`, split role discovery (TRAIN);
- `planned_model_calls` 1,080 and `planned_speech_audio_seconds` 3,085;
- `planned_gpu_hours` 0.25;
- tool kind `asr`, contact class `speech-tool`.

The brief said "contact class `asr`". The existing loader accepts only `speech-tool`
(`rails/speech_observation.py:545`). Keep `speech-tool` as the class and record `asr` as the tool
kind in the row text. Inherited exposure: the 87 Fold A decodes of section 1.3. The Fold B row is
`SAEA-SLURP-ASR-TOOL-PASS-FOLD-B-V1`, a separate row.

**Receipt.** `docs/readiness/2026-09-29-slurp-asr-tool-pass-v1/` holds:

- the runtime inventory, checkpoint `.pt` sha256 `e5b1a55b…` and patched-source file hashes;
- `decoding_config_sha256`;
- the build: openai-whisper 20250625 with the `saea-beam-batch-v1` patch, plus the venv package
  pins;
- the study commit of the producer checkout;
- the `ExecutionPlan` pin;
- the source-roster sha256.

The catalog carries every pin and is the receipt the consumer validates.

**Where it runs.** On the **GPU inside the serving-restart gap**. The 12-h restart rule
(`docs/handoff/HANDOFF-TO-CHATGPT.md:56-59`) already stops the resident llama-server between
chains when no flight is alive. The order is:

1. The chain ends and the restart rule fires.
2. Stop the server and check the lease.
3. Run the E5-0 Fold A pass, then the Fold B pass.
4. Start the server on the same geometry and log `READY`.

The GPU does not run Whisper while the core is resident. The CPU is the fallback (section 5).

### 2.2 E5-1: offline oracle (model-free after E5-0)

**Inputs, all sealed.**

- The AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, with its node-ledger sets.
- E4-1's delivered column and its two shadow columns (the 63 EXACT -> BOUNDARY items).
- COMP-1b once sealed. It is flying now and is not yet readable.
- The wave A/A arm `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`, used as the replicate.
- The E5-0 catalog.

Gold enters **only on the scoring side**, through the governed TRAIN loader
(`data.slurp.load_slurp_split`) and `analysis.sealed_credit.entity_states.entity_items`, exactly as
the headroom read did.

**Canonicaliser (runtime side, gold-free).**

- `rails/relisten.canonical_value` and `fold_number_words`: fold both the transcript and the
  delivered value.
- Word-bounded containment, meaning the folded delivered value occurs as a contiguous token run in
  the folded transcript.
- Near-containment: token edit distance of at most 1 on runs of 3 or more tokens. This is reported
  separately.

**Item sets and per-set questions.** Each set is reported per entity type with a paired-cluster
bootstrap. The cluster is `sample_id`, 10,000 draws, seed 20260807, and the report gives CI95.

| set | size, source | question | what it predicts |
| --- | --- | --- | --- |
| hearing-visible 71 ∪ re-listen-addressable 35 | 106 items on 104 rows (headroom `§2`) | Q1: gold span ⊂ transcript? Q2: delivered wrong value ⊂ transcript? | Q1 bounds replace/repair. Q2 = "a transcript check would **not** reject it" |
| E4-1's EXACT -> BOUNDARY failures | 63 items (E4 read `§4`) | Q3: delivered EXACT value ⊂ transcript? | the check's protection: a high rate means E5 would have **kept** these items where E4 broke them |
| audio-only undetermined (E5 class) | 82 items (62 not MISSING, 20 MISSING; headroom `§3`) | Q1, Q2 | the hearing target no supply route reaches |
| every delivered entity on AGREE | 534 EXACT + all non-EXACT + 253 SPURIOUS | Q4: flag rate of the check on EXACT items, which is the false-reject cost. Q5: flag rate on SPURIOUS items | the net of a drop rule |
| all 941 gold entities on Fold A | -- | Q6: Whisper span recall per type | the ceiling on everything above |

**Three deterministic rules.** Each rule is scored as a column with the official in-process
arithmetic, then with the `slurp-slu-official-train` subprocess, once per complete column. A
delivered value is "consistent" if it passes the canonicaliser containment test.

- **R-FLAG.** No change to delivery. The column equals the delivered column. The rule counts only
  flags, which are the triggers for E5-2b.
- **R-DROP.** Drop an inconsistent entity. This is the transcript analogue of E4's drop column,
  aimed at the 179 not-in-note SPURIOUS items.
- **R-SWAP (span-preserving).** Replace an inconsistent value with the transcript n-gram that
  meets all three conditions below. If no n-gram qualifies, keep the delivered value.
  1. It has minimum token edit distance to the delivered value.
  2. It has **the same token count** as the delivered value.
  3. Its similarity is at least θ.

  The same-token-count constraint answers E4-1's failure: E4 lost on span extent (63 EXACT ->
  BOUNDARY), not on hearing. A replacement must therefore never widen or narrow the span.

θ and the near-containment option are tuned on **Fold B only**. On Fold A they are fixed before
the first Fold A column is scored, with two pre-set values, θ 0.6 and 0.8, both reported. The
deterministic scope rule at 0.8 / 5 occurrences (+1.04, replicate +0.93; headroom `§2`) is also
composed with each rule. It is reported both alone and composed, because it touches a disjoint
failure mass.

**FORMAT risk.** Whisper writes digits and punctuation, while SLURP gold follows its own written
convention. R-SWAP substitutes transcript tokens, so the E5-1 table must report the transitions
into FORMAT and BOUNDARY separately. R-SWAP's replacement text is re-rendered through the fold
before delivery.

**Thresholds E5-1 must show.** They are fixed here, before E5-0 exists. They come from the
headroom conversion table: 1.5 pp needs 49.5 net FP removed, or 24.8 FN recovered, or 16.5 of
each. 2.5 pp needs 81.3, or 41.6, or 27.5.

1. **Precondition (tool quality).**
   - Q6: Whisper span recall of at least 0.80 over the 941 gold entities.
   - Q3: at least 0.85 of the 63 E4 failures kept as EXACT.

   If either fails, stop. A transcript that does not contain the gold cannot verify it.
2. **E5-2a gate: a deterministic USE step, with no flight needed to read it.** One of R-DROP or
   R-SWAP, alone or composed with the scope rule, must show all three of the following:
   - an official SLU-F1 delta of at least **+1.49 pp** on AGREE, with CI95 lower bound > 0;
   - the same sign and at least +1.0 pp on the wave A/A arm, which is the replicate;
   - an EXACT loss of at most 1 per 5 net items gained.

   The rule adds no decode noise, so the bar is the same-flight contrast half-width at
   n = 1,080 (1.49, decision 190). Section 5 of the headroom note left open whether a
   deterministic deliver-side edit should instead use its own bootstrap interval. See Q2 in
   section 6.
3. **E5-2b gate: one core contact.**
   - Let Oflag be the flagged-set oracle: the pp gained if every flagged entity were resolved
     correctly.
   - The expected gain is Oflag × the measured conversion 0.457 (CONV probe, 32 of 70).
   - That product must be at least 1.49 pp, which means Oflag ≥ 3.26 pp.
   - On a cross-flight form (a delivery change upstream of the seal), the bar is 2.5 pp, which
     means Oflag ≥ 5.47 pp.
   - E4-1's measured net conversion for a core-native forced choice was 2.83 %. So E5-2b is
     registered only if E5-2a falls short **and** Oflag clears the bar.

E5-1's outputs go to `$DATA/analysis/SAEA-SLURP-ASR-SLOT-VERIFY-ORACLE-V1/` (`report.json`,
`tables.md`, `content-sha256.json`). The driver is a new
`scripts/analysis/slurp_asr_slot_verify_oracle.py`. It reuses the headroom driver's `derive_arm`,
`slot_ledger` and `boot_f1` unchanged, and asserts their published counts.

### 2.3 E5-2: the module (post-delivery verification)

**Position.** The module sits after ACCEPT and after the deliver normaliser, which is E4's node
position. It covers entities only and never reopens intent. Intent is identical by construction,
and the read tests this with 0 rows differing. The transcript is never shown to Perception, the
Planner or the Solver. This keeps the fixed-supply intent harm of 2026-09-12 structurally out.

- **E5-2a (deterministic USE step, zero core contacts).** This is the winning rule from E5-1,
  applied to the transcript catalog through `saea-tool-prepared-speech-observation-v1`.
  - It is first read as a **shadow column on an already-sealed arm**, which needs no flight.
  - It is then bound in delivery on the next queued cell. That makes it a knob contrast against
    that cell's own delivered column, read under decision 190's same-flight bar.
  - The per-entity receipt `saea-asr-verify-v1` carries `consistent` (bool), `rule`, `action`
    (keep / drop / swap) and hashes only (value sha256, transcript artifact sha256). It never
    carries value or transcript bytes. This is the E4 receipt discipline.
- **E5-2b (one forced-choice core contact, conditional).** This fires only on a flagged entity,
  meaning the delivered value `c` is inconsistent and the span-preserving transcript n-gram `t`
  exists.
  - The contact is `{packet audio, decided intent, slot type, A/B = (c, t) in sha256(sample_id,
    slot_type) order, "neither"}`. This is E4's `slurp-relisten-confirm-v1` format, and E4's
    blind contact is removed. There is **one contact per flagged entity, not two**.
  - Accept `t` only on the core's choice. The core keeps answer authority, and the tool only
    proposes.
  - This is read as a same-flight shadow column exactly like E4-1. It uses the
    `same-flight-shadow-relisten` floor design, 1.49 × sqrt(1080 / rows), in
    `scripts/checks/stage3_effect_floor_check.py`, with `expected_effect_pp` taken from E5-1's
    Oflag × 0.457.
  - The pre-declared gate is SLU-F1 delta ≥ +1.49 with CI95 lower bound > 0, **and** net
    conversion over the flagged set ≥ 0.457 × 0.9. The 0.9 factor is a 10 % allowance for the
    analogue.
  - Contacts are about the flag count × 1. E5-1's Q4 + Q5 predict this count before registration.

## 3. Boundary and authority

1. **The tool never answers.** Whisper output is OBS evidence. The deterministic check (E5-2a) or
   the frozen core (E5-2b) consumes it. No second answering model is involved, and the final
   entity list is the core's delivered list after a deterministic edit, or after the core's own
   choice.
2. **Transcripts are runtime evidence, and gold is not.** The E5-0 transcript is produced from
   audio alone, with no labels, no reference transcript and no future turns. SLURP's reference
   transcript and gold entities are read only by the E5-1 oracle and the official scorer, on the
   scoring side, through the governed TRAIN loader.
3. **Confinement.** Whisper reads only the source FLAC whose relpath and sha256 are bound in the
   catalog row. These are the packet's own source bindings, and `_confined` refuses paths outside
   the data root. No derived media is created on SLURP. If a later carrier needs cut spans
   (Earnings, section 4), they go through `saea-tool-slice-encode-v1` and a declared
   `derived/<variant>/` root proven by `derived_media_confinement_check.py`.
4. **How the receipt proves no gold entered.**
   - Each artifact's `inputs` block has a fixed shape: source audio relpath and sha256, packet id
     and sha256, span, split hash, config sha256, plan, ledger row and protocol. The loader's
     `_exact_mapping` refuses any extra key, so a label field cannot ride along.
   - `decoding_config_sha256` pins a decode config that has no prompt or `initial_prompt` field.
     Whisper is therefore not conditioned on text, and in particular not on SLURP's reference.
   - The producer imports no SLURP label loader. This is proven by an AST check added to
     `tool_catalog_check.py`'s wrapper scan: `speech_preparation_runtime` must not import
     `data.slurp` label functions.
   - The E5-2 receipt stores hashes, not values.
5. **Charter pins.** Final authority stays with the frozen core. The tool is pinned (section 2.1
   receipt) and logged (ledger rows before contact, and before any result is read). Paid API
   spend is 0. The run is local only.

## 4. Carrier transfer (decision 196; shape only, no GPU before the SLURP lock, decision 187)

| carrier | E5-0 target | E5-1 unit | E5-2 hook | adapter work |
| --- | --- | --- | --- | --- |
| Audio2Tool | full-utterance transcript per item (A2T clips are short, so the same producer applies) | each delivered **argument value** in the tool-call JSON; string arguments only (enums and numerics are graded by `a2t-toolcall`) | `rails/adapters/audio2tool.py`: an `entity_values(delivered)` view over `arguments`, plus a re-render after R-DROP/R-SWAP | a value-view function; the scorer stays `a2t-toolcall` |
| Earnings-21/22 | 90-s windows exceed Whisper's 30-s limit (`MAX_AUDIO_SECONDS`). Use MMS_FA word timings on the core's own delivered text to cut ±1.5 s `recut-span` slices around each entity or numeric, through `saea-tool-slice-encode-v1` and a declared derived root | ConEC entity items and **numerics** (E-C3; numeric-value accuracy baseline 90.73 %) | `rails/adapters/earnings.py` (`Earnings21Adapter`): an entity/numeric extractor over the window transcript; the check compares folded numerics | the span-cut derivation plus the MMS_FA tool-smoke row (lock note). Scoring already exists (`entity-wer`, `asr-wer-whisper`) |

Earnings is the natural second carrier, because the whole output is a transcript there. On
Earnings, E5 is a numeric/entity **verifier**, not a second transcriber. It is not a WER mechanism:
the owner ruled 2026-09-06 that WER is not the task metric.

## 5. Cost and schedule

| stage | device | estimate | basis |
| --- | --- | --- | --- |
| E5-0 Fold A | GPU (RTX 5090), batch 8, beam 5, fp16 | **about 5 min of decode plus about 2-3 min of model load and prefetch, so about 10 min wall and 0.15 GPU-h** | DEV-1000: 1,000 rows and 2,884.8 speech s decoded in 277 s (artifact mtimes, recovery attempt). Fold A has 3,085 s |
| E5-0 Fold B | same | about 10 min | same |
| E5-0 Fold A, CPU fallback | CPU fp32, beam 5, 1 worker × 4 threads | **about 4.4 h** (1,080 × 14.8 s) | measured 14.1-14.5 s median per utterance on 86 live Fold A decodes while the core was serving (started-marker to artifact mtime) |
| E5-1 | CPU, model-free | about 10 min | the headroom driver's 7 min is dominated by the TRAIN loader |
| E5-2a shadow read | CPU | about 10 min, plus one official column scoring per rule | -- |
| E5-2b | GPU, inside a queued cell | about the flag count × 1 contact at about 2.9 s audio | only if gated |

**Schedule.** Use GPU E5-0 inside the next 12-h serving restart gap, after the current chain
(COMP-1b -> P-SV-1 seal-only -> P-SV-2 -> P-SV-3) has no flight alive. It costs about 20 min of
core downtime for both folds, and no flight is interrupted.

The CPU fallback avoids the GPU entirely but has two hazards:

- The ~4.4 h × 1 worker run holds about 6-7 GB of host RAM, fp32 large-v3. That RAM counts
  against the 12 GB host-free start guard, which refuses an np4 restart while a CPU sidecar holds
  memory.
- More workers would shorten the run but multiply that host-memory hazard.

The GPU gap is the recommended slot.

**Decision requested (201).**

- **A:** open E5-0 (the Fold A and Fold B passes in the restart gap), then E5-1 offline, with the
  thresholds of section 2.2 fixed now. E5-2a/E5-2b are registered only if E5-1 clears its gate.
- **B:** close the ASR route. The E4 line then ends at SHADOW HARM, and the hearing mass
  (106 + 82 items) stays unaddressed.

The recommendation is **A**. It costs about 0.3 GPU-h and has no core contact until E5-1 has
shown the number.

## 6. Open questions for the coordinator

1. **Direction revision.** Should decision 201 explicitly supersede the 2026-09-06
   no-transcript-tokens ruling, scoped to post-delivery entity verification? That ruling is still
   the standing memory of owner intent.
2. **Bar for a deterministic edit.** Should E5-2a use the 1.49 pp same-flight contrast bar, its
   own bootstrap CI, or the pool null of 1.547? The headroom note's recommendation 3 left the
   same question open for the scope rule, and it should be decided once for both.
3. **Which Whisper file is "the pinned tool".** The first option is the study-pinned openai-whisper
   `.pt`, which has working plumbing and SLURP precedent but is not in the umbrella lock. The
   second is the lock-registered HF safetensors, which has no SLURP plumbing. The recommendation
   is the `.pt`, together with an umbrella lock entry for it before E5-0.
4. **Restart-gap scheduling.** Should the queue driver own E5-0 as a chain step at the next
   restart (stop -> E5-0 A+B -> start), or should the coordinator run it by hand under the lease?
5. **COMP-1b.** Should E5-1 wait for COMP-1b's seal, so that one read covers AGREE, the wave A/A
   and COMP-1b? Or should it read AGREE, the A/A and E4-1 now and append COMP-1b afterwards?

## Coordinator rulings (Fable 5.1, 2026-09-29)

- **Q1 (2026-09-06 "no transcript tokens" ruling).** Decision 201 is put to the owner as a LIMITED exception: ASR transcripts are used only for post-delivery ENTITY-VALUE checks (E5-1 offline, E5-2a deterministic, E5-2b one forced-choice contact after delivery); they never enter the intent decision, the Perception or Solver prompts, or any retrieval key. The DEV-1000 result (intent -0.90 [-1.68, -0.09] with transcripts in the prompt) is the reason the exception is this narrow.
- **Q2 (bar for a deterministic edit).** On a single sealed pool the edit is judged by its own paired row-bootstrap CI95 excluding zero AND its point estimate clearing the same-flight SLU floor (1.49 pp at n = 1,080); the A/A replicate must show the same sign at >= 1.0 pp. The 1.547 pool null applies only to multi-sample pools (decision 179). This rule applies to E5-2a and to the scope rule alike.
- **Q3 (pinned tool).** The study-pinned `.pt` with the existing plumbing; an umbrella `docs/datasets.lock.json` entry is added before E5-0 runs, so the lock stays the single source of dataset/model identity.
- **Q4 (how E5-0 runs).** As a queue chain step at the 12-h serving restart, scripted and receipted through the batch driver's lease, never by hand.
- **Q5 (E5-1 timing).** E5-1 reads AGREE, the A/A and E4-1 as soon as E5-0's transcripts exist; COMP-1b is added when sealed. Nothing here admits anything; decision 201 gates E5-0.

## Addendum: runtime form is model-initiated (owner directive, 2026-09-29)

**Owner directive (2026-09-29; translated from the owner's Chinese, verbatim text in
`docs/readiness/2026-09-29-research-direction-system-level-v1.md`).** "Tools should be invoked by the model on its own
initiative, not called by the system by default; otherwise we fall into the self-proof trap -- why would the task not
be done by an ASR + LLM combination, and why would it need an omni agent system!" The module-level rule is section 2d
of `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md`; this addendum applies it to E5 and
supersedes section 2.3 where they disagree.

**What E5-0 and E5-1 become.** Both are instruments and oracles only. E5-0 produces the pinned transcript catalog that
the tool will read; it is a tool pass over audio, not a runtime step, and nothing it produces reaches a core request
by itself. E5-1 bounds what a perfect call would yield and defines the **decision oracle**: the set of delivered
entities where a call would have helped (delivered value wrong, gold span contained in the transcript: Q1 true and Q2
false), its complement where a call can only cost (delivered value EXACT; Q3 and Q4 give the false-reject rate), and
its base rate `b` = oracle-positive entities over delivered entities on the read roster. Section 2.2's thresholds keep
their role as the precondition (Q6 >= 0.80, Q3 >= 0.85) and as the upper bound; they no longer gate a runtime rule.

**E5-2a is WITHDRAWN as a runtime candidate.** A transcript check applied by the system to every delivered entity is
exactly the "ASR + LLM" form the owner barred. Its R-FLAG / R-DROP / R-SWAP columns survive only offline, as the
oracle's upper bound: the best any decision policy over the same tool could do. E5-2b's forced-choice contact is
likewise not registered in its system-triggered form; its format (A/B in sha256 order plus "neither") is not reused.

**E5-2 is the tool offer at the Solver's slot-value step** (`tool-offer:asr-slot-value`, inventory row 20 of the
module design). One tool is offered, and only there:

- **Chosen signature: `verify_span(entity_index: int)`**, where `entity_index` indexes the entity list of the Solver's
  own draft in the same episode (the cited-answer draft). It returns the span-preserving transcript n-gram for that
  entity from the pinned E5-0 catalog -- the same-token-count nearest match under the section 2.2 canonicaliser, which
  is the entity's window on SLURP, where E5-0 carries no timestamps -- or an empty result when none qualifies (empty is
  legal, decision 199). It never returns the whole transcript.
- **Rejected: `transcribe_segment(t0, t1)`.** It is the wider tool and therefore the less safe one. Its argument space
  is open (two real numbers that the core cannot ground, because the core sees no timeline); its output is arbitrary
  transcript text, including the intent-bearing words that the 2026-09-12 fixed-supply result showed to hurt intent
  (DEV-1000 intent -0.90 [-1.68, -0.09]); it needs a live decode per call and derived media per range; and its
  decision oracle is undefined, because "a call would have helped" has no closed unit. `verify_span` has a closed
  argument space (0 .. n-1 of the model's own draft), a bounded output (one span or empty), a deterministic answer
  read from a pinned catalog (a `speech-tool` catalog read through `saea-tool-prepared-speech-observation-v1`, no live
  decode on SLURP), an `args_hash` that is enumerable, and an oracle that is defined per entity. On Earnings the same
  signature resolves the window through MMS_FA timings (section 4); the argument space does not widen.
- **Schema budget.** One function, one integer parameter, a description of at most two sentences; rendered only in
  the Solver's request at that step (per-role rendering, never constant: EFF-1).
- **Receipt.** `tool_decision: {offered, called, args_hash, result_hash, used_in_answer}` per row, plus the
  `saea-asr-verify-v1` hash-only sub-receipt per returned span (value sha256, transcript artifact sha256; never value
  or transcript bytes).

**Pre-declared gate (three parts, all required; fixed now, before E5-0 exists).**

1. **Call rate within a declared band:** calls per offered row in [max(0.01, 0.5 b), min(0.50, 4 b)], with `b` the
   oracle base rate measured by E5-1 and frozen before the flight. Below the band the offer is inert; above it the
   model is calling by reflex, which is the system-default form by another name.
2. **Decision precision above the oracle's base rate by a margin:** precision (calls on oracle-positive entities over
   calls) >= b + 0.10 absolute and >= 2 b, with a paired-cluster bootstrap CI95 (cluster `sample_id`, 10,000 draws,
   seed 20260807) whose lower bound exceeds b. Recall is reported beside it and not gated.
3. **Conversion clears the floor, and the column does no harm:** the SLU-F1 delta carried by the called rows (the
   arm's delivered column against its no-offer comparator, which differ only on called rows), expressed over the whole
   read roster, is >= +1.49 pp (the same-flight SLU floor at n = 1,080, decision 190) with CI95 lower bound > 0; and
   the arm's whole-column SLU-F1 does not breach the guard (no measured loss: the CI95 upper bound is not below zero)
   while intent differs on 0 rows.

**Read form.** An offer changes the Solver's request bytes (the `tools` array is rendered), so it cannot be a shadow of
the delivered request. If the module's same-flight columns (module design 3.3) reach the Solver node by the time E5-2
is registered, the read is a same-flight **column** (the offered Solver contact as a branch beside the delivered,
unoffered one) under the 1.49 pp bar above; otherwise it is a **cross-flight** read against the in-chain A/A with the
2.5 pp bar at n = 1,080 in place of 1.49 in part 3. Either way the `stage3_measurement` block declares the design, and
`expected_effect_pp` is the E5-1 upper bound times the measured decision precision times the conversion, never the
upper bound alone.

**Unchanged boundary.** Transcripts never enter the intent decision: `verify_span` is not offered to Perception, the
Planner or the Reviewer, its result is scoped to the entity it was called for, the read requires 0 intent rows
differing, and no transcript byte becomes a retrieval key. Gold stays scoring-side only (section 3, item 2).

*Merge note (2026-09-29): the preparation addendum below was written on `fable/e5prep` concurrently with the master addendum above. Both record the same owner directive. Where they differ on the E5-2 runtime form (signature, gate, read form), the addendum above and module design section 2d govern; the preparation addendum records what E5-0 and E5-1 register and compute.*

## Preparation addendum (2026-09-29): the owner supplement to decision 201 -- tools are called by the model

Owner, 2026-09-29, translated to English (First principle 1; the original-language message is the
addressable source in the coordinator's brief of 2026-09-29 to the E5 preparation agent): "A tool should
be invoked by the model on its own initiative, not called by the system by default; otherwise we fall into a
self-proof trap -- why use an omni agent system at all, rather than an ASR + LLM combination, to do the task!"

This addendum supersedes every sentence above that treats a system-applied transcript check as a runtime
step. The sections it changes:

**A1. E5-0 and E5-1 are instruments.** The transcript pass (section 2.1) and the offline read (section 2.2)
are INSTRUMENTS / ORACLES. They bound what a perfect tool call could yield and measure the decision the
model would have to learn. They are registered as such
(`docs/readiness/2026-09-29-slurp-asr-tool-pass-v1/README.md`; rows `SAEA-SLURP-ASR-TOOL-PASS-V1`,
`SAEA-SLURP-ASR-TOOL-PASS-FOLD-B-V1`, `SAEA-SLURP-E5-TRANSCRIPT-CONSISTENCY-READ-V1`).

**A2. No system-applied check is a runtime candidate.** E5-2a (section 2.3: "the winning rule from E5-1 ...
bound in delivery on the next queued cell") is withdrawn as a runtime form. R-FLAG, R-DROP and R-SWAP stay
in E5-1 only, as the ORACLE UPPER BOUND of a system-applied check; the section 2.2 "E5-2a gate" is read as
that bound, and clearing it nominates the E5-2 design below, never a delivery edit. The E5-2b wording
(section 2.3) that the tool "only proposes" and fires "only on a flagged entity" is replaced by A3: the flag
is no longer a system trigger.

**A3. The runtime form, E5-2: the core is OFFERED a pinned ASR tool and DECIDES whether to call it.** The
tool is exposed through the existing native tool-calling path (the featcache llama-server runs with `--jinja`;
the tool catalog's `saea-tool-live-speech-observation-v1` / `saea-tool-live-speech-span-v1` rows and
`rails/live_speech_observation.py` are the plumbing to reuse). Two measured lessons bound the offer:

- EFF-1: constant tool schemas rendered to about 13.9k prompt tokens and were HARMFUL; the Reviewer tool was
  retired after B1-notool read NEUTRAL. The offer must therefore be cheap -- one small schema, not the
  catalog -- and scoped to the **Solver's slot-value step** (never Perception, never the intent decision).
- The call returns OBS evidence for the entity the core names; the core keeps answer authority and may
  ignore it. Transcripts never enter the intent decision or a retrieval key (decision 201's limited
  exception, coordinator ruling Q1).

The E5-2 read measures three things: the **call rate**; the **precision of the decision** against the E5-1
tool-call decision oracle (a call on a row the oracle marks helpful is a correct call; the oracle's signal
AUCs say which model-visible signals the decision should follow); and the **conversion** (the share of
called entities that end EXACT, and the SLU-F1 delta under the same-flight bar of decision 190). No code for
E5-2 is written until E5-1 has read; it needs its own design, registration and rows.

**A4. What E5-1 adds for A3.** The E5-1 driver (`scripts/analysis/e5_transcript_consistency_read.py`)
carries a TOOL-CALL DECISION ORACLE: per row, whether a verifying call WOULD have helped (a delivered value
the transcript does not contain while the matched gold span is contained), the count of such rows and
entities (MISSING gold spans the transcript contains are counted separately), the flag precision, and one
AUC per model-visible signal: the core's own Perception candidate-list length, `note_parse_status`, the
delivered entity count and types, E4-1's blind / forced-choice disagreement, and the entity-free exemplar
share (the supply-abstention trigger). This is what the model must learn to act on.
