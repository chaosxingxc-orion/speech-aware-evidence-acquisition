# Earnings-22 DEV ESB shape C, v1 preregistration

Status: **REGISTERED 2026-09-05**, on the owner directive of 2026-09-05 ("align the way the model is
USED"). One experiment, profile `baseline-reproduction`, **one new arm**, paired against the two
arms already sealed on the same roster, plus one 4-row smoke and one rendered-template proof.
Written before any model contact.

| Run id | Cell | Population | Fragments |
|---|---|---|---|
| `SAEA-E22-DEV-ESB-SHAPE-C-V1` | `E22-ESB-DEV-C` | the sealed A/B roster: 6,038 ESB `train` utterances of the ten Earnings-22 **dev** subset10 calls, 39,292.647 s (10.915 h) | dataset `earnings22-esb-dev-utterances-6038`, baseline `e22-esb-dev-shape-c`, model `q4km-e22-dev-esb-mmproj-gpu-04ccc72a-np8-c40960`, experiment `e22-dev-esb-shape-c-v1` |
| `SAEA-E22-DEV-ESB-SHAPE-C-SMOKE-V1` | `E22-ESB-DEV-SMOKE-4-C` | the same 4 rows the A/B smoke flew | dataset `earnings22-esb-dev-utterances-smoke4`, same baseline and model, experiment `e22-dev-esb-shape-c-smoke-v1` |
| `SAEA-E22-DEV-ESB-SHAPE-C-PROMPT-FIT-V1` | — | no population; one media stand-in | the rendered-template proof: `/props`, `/apply-template`, `/tokenize` only, **zero generated tokens** |

Predecessor: `docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-verdict.md`
(`SAEA-E22-DEV-ESB-PROMPT-A-V1` **17.565** and `SAEA-E22-DEV-ESB-PROMPT-B-V1` **18.394** corpus
Whisper-normalized WER over the same 6,038 utterances). That experiment supplies **everything**
except the factor under test: the roster, the derived media, the derived reference layer, the D1
media supplement, the scorers, the model fragment, the geometry, the harness, the entry point, the
prompt-fit route, the wire check, the smoke design, the analysis code — and both sealed arms to pair
against.

## 1. Why this experiment exists

The A/B falsified the prompt-**text** hypothesis in the direction nobody expected: the Qwen3-Omni
authors' own English ASR prompt scored **0.830 points worse** than this study's own instruction, and
the paired CI90 excluded zero on the wrong side (per-utterance delta −0.02741, CI90 [−0.0449,
−0.0133]; corpus delta −0.830, CI90 [−1.653, −0.172]; worse on eight of ten calls). Over-generation
survived both arms unchanged: insertions **62.0 %** and **63.0 %** of all errors, hypothesis
**1.086×** and **1.092×** the reference length, and a length ratio that rises monotonically as clips
shorten (1.045 → 1.158 on arm A, 1.043 → 1.207 on arm B).

The A/B verdict named the cheapest untested factor, and it is the **shape** of the request rather
than the text in it. The same model-card section that supplied arm B's wording — *Setting for
Evaluation*, pinned in
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-prompt-ab-v1/prompt-source/qwen3-omni-asr-prompt-source.json`
— also states:

> **"No `system prompt` should be set for any evaluation benchmark."**
>
> "The question or prompt should be input as user text. Unless otherwise specified by the benchmark,
> the text should come **after** multimodal data in the sequence."

Every Earnings flight this study has ever sent did the opposite: a system message carrying the
instruction, and a user message carrying nothing but the audio. Arms A and B held that shape fixed on
purpose, so exactly one factor differed between them; it was recorded there as deviation **G2** and
named as the second, unflown suspect.

There is a mechanism to expect, not merely an audit box to tick. A user-turn instruction that
**follows** the audio is the only form in which the model has heard the clip end before it is told
what to do. That bears directly on the one thing the A/B left unexplained — a model continuing past a
sentence boundary it cannot see.

## 2. Population and materials — nothing is re-derived

**Exactly the sealed A/B roster.** The same 6,038 utterances, the same derived WAV bytes, the same
derived reference layer, the same D1 media supplement, the same receipts, the same hashes. Nothing is
re-cut, re-drawn or re-hashed, and the dataset fragments are the *same files* the A/B arms composed:

| artifact | sha256 |
|---|---|
| roster receipt (`.../roster/flight-roster-receipt.json`) | `20437bcb…` (`ids_sha256` `dfa2ec01…`, `items_sha256` `37e45e51…`) |
| segment-table receipt | `2ff3aa88…` (extracted table `51257011…`, 6,038 rows) |
| reference-layer receipt | `e2030bde…` (layer `8da3a65d…`, 6,038 rows, 104,808 whitespace words) |
| D1 media supplement `docs/receipts/artifacts/d1-e22-esb-dev10-utterances.json` | `ad01c4ec…` |

Split identity hashes, unchanged from the A/B: flight `fc14c98b…`, smoke `5f0b843c…`.

**Split role.** These ten calls — 4453225, 4469088, 4470684, 4474506, 4479944, 4481952, 4482383,
4482613, 4483937, 4485192 — **are** this study's registered `earnings22-original` **dev** subset10
(`docs/receipts/splits.json`, split `dev`, count 10, identity `89b178d6…`). No owner allowance is
involved and none is claimed. **No confirmatory call is named, loaded, decoded, scored or read**, and
the six calibration-exposed ESB **test** calls of 2026-09-04 are not read again. The one clamped
utterance (`4481952-631`, end boundary clamped to the decoded parent) is inherited from the roster and
is named again in the verdict.

**Why the paired contrast is legitimate at all.** Arms A, B and C send the same media bytes for the
same 6,038 sample ids under the same build, the same quantization, the same audio path, the same
serving geometry and the same greedy decoding parameters. The three arms therefore differ in exactly
what this preregistration says they differ in, and every contrast is within-utterance.

## 3. The arm

**Arm C (the official usage shape).** Wire messages:

```json
[{"role": "user",
  "content": [{"type": "input_audio", "input_audio": {"data": "<the wav>", "format": "wav"}},
              {"type": "text", "text": "Transcribe the English audio into text."}]}]
```

against arms A and B's

```json
[{"role": "system", "content": "<the arm's instruction>"},
 {"role": "user", "content": [{"type": "input_audio", ...}]}]
```

The instruction **string** is byte-identical to arm B's (sha256
`8533f771edf09f036aa333ed9631e531e5a0c4493efa5f7b0f53fdcf751154d6`, 39 chars), so the A/B's finding
about the text carries over unchanged and the only thing that varies between B and C is **where that
string sits**. Everything else — roster, media, references, scorers, build `04ccc72a`, Q4_K_M decoder
`0751c279…`, bf16 mmproj `f0dfe825…` resident on the GPU, `-c 40960 -np 8` at 5,120 tokens per slot,
`GGML_CUDA_DISABLE_GRAPHS=1`, greedy `temperature: 0`, `max_tokens: 1024`, `id_slot: per-sample`, seed
20260803, `core.flight.FlightRuntime` entered through `scripts/flights/run_e22_esb_cell.py` — is
identical, and the **model fragment is the same file** arms A and B composed rather than a copy of it.

### 3.1 The seam, and why it is one key on the existing base

No existing seam could express "no system message". The Audio2Tool official-protocol work already
added the placement half — `user_turn_text` / `user_turn_audio_first` on the composed config, read by
`core.model.transport.LlamaServerTransport` — and this flight adds the other half as one more
request-shaping config key on the same class:

* `omit_system_message: true` (baseline fragment; travels in `config_hash` → `protocol_hash` like
  every other request-shaping key, and **defaults to false**, so every fragment that predates it
  renders byte-identical requests).

`rails.task_adapter.TaskAdapter.assemble_prompt` is **unchanged**: it still produces the internal
`[system, user]` pair that `rails.core_client._parse_rails_messages` parses into
`(task_instruction, media_relpath, supply_texts)`. Only the transport's rendering of the resulting
payload changes, because the transport is the one place the wire messages are built. No new module
under `rails/probes/`, no `TaskAdapter` subclass, no controller subclass, no new `launcher/`
directory — the owner's 2026-09-03 base rule, and `scripts/checks/engineering_base_check.py` passes.

**The seam is fail-closed, because its failure mode is silent.** Dropping the system message would
otherwise take `task_instruction` off the wire while the payload, the trace records, the config hash
and the protocol hash all still recorded it — the run would be measuring a prompt nobody wrote down.
The transport therefore refuses:

1. `omit_system_message` without a declared `user_turn_text`;
2. `omit_system_message` under any speech-feature prompt order (those own their message assembly);
3. a non-bool value;
4. any request whose payload `task_instruction` is not **byte-identical** to the configured
   `user_turn_text`;
5. any request carrying evidence or an exemplar bank — both travel in the system message under the
   evidence-first orders and would be silently dropped.

Tests: `tests/unit/test_llama_server_transport.py`, ten new cases including
`test_sealed_e22_arm_a_payload_is_byte_identical_without_the_seam` (the sealed arms' wire bytes,
pinned) and `test_transport_factory_defaults_omit_system_message_to_false`.

### 3.2 The rendered-template proof, before any generation

Arithmetic cannot see whether the pinned GGUF chat template really emits no system block. A template
that quietly injected a default system prompt when the request carries none would make this whole
experiment measure something other than what it claims. So `scripts/e22_dev_esb_prompt_fit.py` gains
a `--render` mode (the same script family, not a new one) that:

* captures the wire messages from the **real** `LlamaServerTransport`, resolved through the same
  `TRANSPORTS` registry entry and the same composed config the flight uses, driven with a real
  `core.policies.build_arm_payload` payload, with only its HTTP sender replaced — so what is rendered
  is what the flight sends, byte for byte;
* renders them through the pinned template with `POST /apply-template` and counts the rendered text
  around the single opaque media marker `GET /props` reports with `POST /tokenize`;
* **asserts**, for arm C: the wire roles are exactly `["user"]`, the rendered prompt contains no
  system block, the instruction appears verbatim, and every occurrence of it sits **after** the media
  marker;
* **asserts**, for arms A and B rendered through the identical route: they still show their system
  block. That control is what makes the absence meaningful.

`GET /props`, `POST /apply-template` and `POST /tokenize` decode nothing: **zero generated tokens**.
The server is spawned under a gate-checked `contracts.ExecutionPlan` bound to its own exposure row and
stopped with its own stop receipt.

## 4. Budget (ExecutionPlan, registered)

| | plan | registered ceiling | basis |
|---|---:|---:|---|
| model calls | 6,046 | 6,350 | 6,038 rows × 1 contact + 8 canaries; ceiling about 5 % above |
| speech audio seconds | 39,300 | 41,300 | 39,292.64675 for one pass; ceiling about 5 % above |
| GPU hours | 0.6 | 1.0 | arms A and B measured **0.4515** and **0.4596** GPU-h on exactly this roster and geometry; arm C's request is 26 tokens smaller than arm A's and the same size as arm B's, so 0.6 is about 1.3× the measurement and 1.0 about 2.2× |
| paid API spend | 0 | 0 | in force, unchanged |

| smoke | plan | registered ceiling | basis |
|---|---:|---:|---|
| model calls | 12 | 40 | 4 rows × 1 contact = 4 plus headroom |
| speech audio seconds | 120 | 240 | 96.959875 for one pass |
| GPU hours | 0.5 | 1.0 | essentially all of it model load |

| prompt-fit render | plan | registered ceiling | basis |
|---|---:|---:|---|
| model calls | 1 | 4 | nominal: nothing decodes |
| speech audio seconds | 1 | 4 | nominal: one media stand-in, never encoded for generation |
| GPU hours | 0.3 | 0.5 | essentially all of it model load |

`core/model/adapter.py` enforces `planned_model_calls` and `planned_speech_audio_seconds` **across all
attempts of a run id**. A partly spent dead attempt therefore cannot be re-run under the same run id;
the one permitted recovery takes a fresh run id and a fresh exposure row.

## 5. Protocol

* **Request**: one utterance per contact. No OBS loop, no windowing — an ESB utterance *is* the
  request. `policy: fixed`, `rails_arms: ["zero-supply"]`, `arm: bare-core`, `evidence_source: none`.
* **Prompt shape**: section 3, proved by section 3.2.
* **Decoding**: greedy (`temperature: 0`), `max_tokens: 1024`, `id_slot: per-sample`, seed 20260803
  (inert under greedy) — byte-identical to arms A and B. `max_tokens` is deliberately **not** changed:
  a different ceiling could truncate a rambling completion and silently move WER, which is precisely
  the quantity under study.
* **Model / serving / harness**: section 3, all inherited unchanged.

### 5.1 Window fit, before any contact

Unchanged from the A/B, because the roster and the geometry are unchanged: the encoder's exact
one-second window rule `n_tokens = 13 × ceil(audio_seconds)` gives the longest utterance
(`4470684-13`, 78.360000 s) **1,027** speech tokens; with the 49-token envelope bound, a 1,024-token
completion ceiling and 2 special tokens the worst request is **2,102** against a **5,120**-token slot
— margin 3,018, **×2.44**, **FITS**. Receipt: `prompt-fit/prompt-fit.json` (arm C column) and
`prompt-fit/prompt-fit-smoke4.json`, both at zero contacts of every kind.

49 is a strict upper bound for arm C: its instruction is shorter than the one measured at 49, and
removing the system message can only remove template scaffolding, never add any. The `--render`
receipt measures the exact figure and the smoke measures it again live.

### 5.2 Deviations, named

| # | deviation | why | expected effect |
|---|---|---|---|
| H1 | arm C sends **no** system message and puts the instruction in the user turn **after** the audio | this IS the factor under test; it is the model card's own evaluation protocol, and it is the A/B's deviation G2, named there as the second and unflown suspect | unknown, which is why it is measured; the mechanistic reason to expect an effect is that a post-audio instruction is the only form in which the model has heard the clip end before being told what to do |
| H2 | one new request-shaping config key (`omit_system_message`) in `core.model.transport` | no existing seam could express "no system message" | none on any sealed cell: the key defaults to false and a regression test pins the sealed A/B wire bytes |
| H3 | the population is the ten dev calls, not the published ESB test subset | the confirmatory read of the six ESB test calls is spent; dev is the split this study may optimize on | no number here is an alignment verdict |
| H4 | `merge_compounds` is not applied | this study's Whisper-normalizer scorer does not implement it | identical in all three arms, so it cancels in every contrast |
| H5 | the rendered-template proof spawns a server under its own run id | only the live template can prove the shape | zero generated tokens; it decodes nothing and scores nothing |

## 6. Scoring, analysis and the decision rule

One job, one complete manifest, through `core.scoring_batch` — never sharded, never averaged across
shards.

* **Paper-facing number**: `asr-wer-esb-whisper` **corpus** WER — total S+D+I over total reference
  words, Whisper `EnglishTextNormalizer` on both sides, whitespace tokenization.
* Reported beside it: the mean of per-utterance Whisper-normalized WER; the frozen `saea-scoring-v1`
  corpus and mean; substitutions/deletions/insertions and reference words; the hypothesis-to-reference
  length ratio and the insertion share of errors; and `cost`.
* **Paired per-utterance contrasts, C minus A and C minus B**, through
  `analysis.paired.paired_contrast`: saves / harms / ties, the exact two-sided sign test, and **10,000
  replicates stratified by source call (10 strata), seed 20260903, CI90**. The metric passed to
  `analysis.paired` is **negated** per-utterance WER, so `delta = right − left` is **positive when arm
  C is better** and `saves` counts utterances arm C improves; the raw WER delta is reported beside it.
* Mandatory slices in the verdict: the per-call table for all ten calls under both normalizers for
  **all three** arms; natural-mixture (corpus) and equal-call weightings side by side; the
  insertion/deletion/substitution split and the length ratio per arm; **the length ratio by duration
  bucket**, which is the A/B verdict's own diagnostic and the quantity the decision rule reads; the
  rendered-template proof; and `4481952-631`, the one clamped utterance, named.

### Decision rule, preregistered

1. **If** arm C's pooled corpus Whisper-normalized WER is lower than arm A's **AND** the CI90 lower
   bound on the paired C-minus-A delta is above 0 (negated-WER convention, so "above 0" means arm C
   genuinely lower) **AND** the hypothesis-to-reference length ratio falls toward 1.0, **then** the
   official usage shape becomes this study's ASR request shape for cleaned-reference protocols, and
   the verdict **recommends to the owner** a second and final read of the six ESB test calls under
   shape C. **The owner decides; this flight never flies it.**
2. **Otherwise** the shape is **excluded** as an explanation and the remaining suspects are named for
   the owner *without being flown*: (a) **context-free clipping** — one sentence-length clip with no
   context and no way to know where it ends, the deviation the A/B verdict already implicated through
   a length ratio that rises monotonically as clips shorten; (b) **decoding length control** tied to
   clip duration; (c) **quantization** (Q4_K_M, deviation D2 of the sealed test flight).
3. **In every case** the verdict states whether arm C's dev corpus WER would sit inside the 3-point
   band of the published 9.79 (and of the cross-read 12.3) **as an indication only**. These ten calls
   are not the test subset, no published number covers them, and no alignment verdict is issued here.

The "length ratio falls toward 1.0" clause is read off the same diagnostic the A/B verdict published
— the pooled hypothesis/reference word ratio (arm A 1.0861, arm B 1.0919) — and is satisfied when arm
C's pooled ratio is strictly below arm A's. The per-duration-bucket table is reported in every case,
whichever way the rule falls.

## 7. Sequence and invariants

fragments + seam + tests → this preregistration → **exposure rows before any contact** → arithmetic
prompt fit (zero contacts of every kind) → rendered-template proof (zero generated tokens) → wire
check on a clean committed tree → 4-row smoke with its own exposure row → go/no-go → flight →
`core.scoring_batch` → verdict `docs/readiness/2026-09-05-e22-dev-esb-shape-c-v1-verdict.md` +
`result-summary.json` → every exposure row closed COMPLETED with hashes.

Invariants: `pytest` green apart from the documented pre-existing failures (6 failed / 6,371 passed /
10 skipped and one collection error at `794efac6`, all of them predating this flight — see section 8);
`python scripts/checks/engineering_base_check.py` passes; the tree clean and committed before the wire
check, before the smoke and before the flight, and until finalize; receipts written outside the tree
until the run has FINALIZED, which is what the A/B flight learned when receipts written straight into
`docs/checks/` made the tree dirty for the next cell's scoring gate; `PYTHONDONTWRITEBYTECODE=1`; no
`pip install`, no venv change, no rebuild or checkout of `/home/chao/llama.cpp-featcache` (detached at
`04ccc72a`), no ffmpeg, no fstalign; **no read of any confirmatory call, and no second read of the six
calibration-exposed ESB test calls**; GPU idle and `enforced.power.limit` at 100.00 W before takeoff;
references never enter the request path; `FrozenCoreGate` and `ARM_VISIBLE_FIELDS` decide legality and
causes get fixed, not gates.

**Recovery.** At most one recovery re-registration, with a fresh run id and a fresh exposure row (the
budget is metered cumulatively across attempts of a run id). If a second attempt also fails, the flight
stops under the owner's own rule and the fix is proven on a 4-row dry run before anything else flies.

## 8. Pre-existing test failures, recorded before any change

Measured on the clean tree at `794efac6` before a line of this flight's code was written, with
`PYTHONPATH=$PWD:$PWD/src` and `--continue-on-collection-errors`: **6 failed, 6,371 passed, 10
skipped, 1 collection error** in 164.55 s.

* `tests/unit/test_build_a2t_g6_family_sweep.py` — collection error. `scripts/` in this repository is
  a namespace package and the shared venv's verl 0.8.0 installs a *regular* top-level `scripts`
  package, which wins the import regardless of `sys.path` order. Environmental, and not this flight's
  to fix.
* `tests/unit/test_bundle.py::test_cli_score_manifest_mode_is_verified_and_authoritative`
* `tests/unit/test_engineering_base_check.py::test_regex_extraction_agrees_with_package_import`
* `tests/unit/test_pemb3m_flight.py` (2) and `tests/unit/test_pemb4r_flight.py` (2) — the pinned
  binding-config SHA-256 against the real umbrella lock.

This flight must not add to that list.

### Not authorized by this preregistration

No read of any confirmatory call. **No second read of the six calibration-exposed ESB test calls —
including the one this verdict may recommend, which only the owner may authorize.** No fourth arm. No
few-shot. No post-processing of any hypothesis. No Q8_0 cell. No mechanism arm. No test tuning, no
paper-scale work, no superiority or generality claim.

---

## Phase log

### 2026-09-05, Phase 1 — seam, fragments, registration

Nothing was re-derived: the roster, the derived media, the reference layer, the D1 supplement and both
dataset fragments are the sealed A/B artifacts, reused by name and by hash.

The one code change is `omit_system_message` on `core.model.transport.LlamaServerTransport` plus its
factory key, with the five fail-closed refusals of section 3.1 and ten new tests. The whole
transport-test module passes (78 passed, 1 skipped) and
`python scripts/checks/engineering_base_check.py` reports PASS.

Arithmetic window fit re-run for arm C on both rosters at zero contacts of every kind: worst request
**2,102** tokens against a 5,120-token slot, **×2.44**, FITS; the sealed test flight's 4,096-token slot
still would not.

### 2026-09-05, Phase 2 — the rendered-template proof

Commit `aa8dac6b` (registration), then `a402f628` (one fix, below). Run
`SAEA-E22-DEV-ESB-SHAPE-C-PROMPT-FIT-V1`. All three arms rendered through the pinned GGUF chat
template on the live server at **zero generated tokens** — one `GET /props`, three `POST
/apply-template`, six `POST /tokenize`, no `/completion` call of any kind. All four assertions of
section 3.2 held: arm C's wire roles are exactly `["user"]`, its rendered prompt contains **no
system block**, its instruction appears verbatim **after** the media marker, and arms A and B
still show their system block. Rendered text tokens 47 / 21 / **16**; against the sealed A/B
smoke's measured 49 and 23 envelopes (`add_special: false` here, so the flight's two special
tokens sit on top), the arm-C prediction is **18**.

One defect of my own, caught by reading the artifact rather than by a test: the first receipt
recorded `build_commit: ""`, because the pinned runtime receipt keeps that value at
`llama_cpp.build_commit` and the code read a non-existent top-level key. Fixed at `a402f628`;
the render was re-run and reproduced the first attempt's token counts and all four assertions
exactly. Both attempts are recorded.

### 2026-09-05, Phase 3 — wire check

Commit `a402f628`, clean tree, receipts written outside the tree. Both arm-C cells driven
through `core.flight.runtime`'s `WireCheckGate` and `WireCheckTransport`: the real compose, the
real adapter and its roster-bound samples, the real payload binding and allowlist, the real
`FrozenCoreAdapter` accounting, the real manifest builder, the real bundle verifier and both ESB
scorers. Smoke cell **4 of 4**, flight cell **6,038 of 6,038**, `seal_and_score` **OK** on both.
Zero model contacts, zero servers, zero sockets. The tree was still clean afterwards, which is
the lesson the A/B flight paid for.

### 2026-09-05, Phase 4 — the smoke, and the go/no-go

Row `SAEA-E22-DEV-ESB-SHAPE-C-SMOKE-V1`, attempt `attempt-20260905T094034Z-fa6e61`, **COMPLETED
and FINALIZED, 4 of 4**, 96.96 speech seconds, 2.4 s of dispatch after a 10.0 s model load.

All four registered reads affirmative. **GO.** Every row returned a non-empty completion under
the no-system-message shape; the text envelope measured **exactly 18 tokens on all four
requests**, precisely the render's 16 + 2; the worst request 1,045 + 1,024 = 2,069 against a
5,120-token slot; both ESB scorers returned per-sample rows through `core.scoring_batch` with
`verified: true`.

One observation recorded **before the flight launched**, and not a stop condition because four
rows are not a result and the smoke's WER figures enter no verdict: on the longest row
(`4470684-13`, 78.36 s, 32-word reference) arm C returned the single word `yet.` where arms A and
B both returned a full transcript. The flight has since put it in proportion — collapses of that
severity occur on 47 rows of 6,038, the same count as arm A.

### 2026-09-05, Phase 5 — the flight, the analysis and the verdict

Run `SAEA-E22-DEV-ESB-SHAPE-C-V1`, attempt `attempt-20260905T094322Z-2174df`, **COMPLETED and
FINALIZED, 6,038 of 6,038**, one attempt, no recovery, no CUDA fault, no out-of-memory, no
skipped contact. 1,652.1 s of dispatch plus 11.1 s of startup = **0.4620 GPU-h** against a
registered 1.0 and a planned 0.6; 39,292.647 speech seconds of a registered 41,300.

The window fit held live to the token: largest prompt **1,045** = `13 × ceil(78.36) = 1,027`
speech tokens plus the 18-token envelope, and arm C's prompt-token total is exactly
`6,038 × 5` below arm B's — the five tokens of system-block scaffolding the template no longer
writes, on every row.

`scripts/e22_dev_esb_prompt_ab_analysis.py` was generalized from two arms to N
(`--arm NAME=run_id,run_dir,receipt`, `--contrast RIGHT-LEFT`) and **re-run on the sealed A/B
inputs before being trusted with a third arm**, reproducing that verdict to the last digit.

**Result: the shape is EXCLUDED.** Corpus WER 17.8896 against arm A's 17.5648 (+0.325), while
the length ratio fell 1.0861 → 1.0398 and insertions fell 11,270 → 9,094 — paid for with
deletions 2,370 → 4,975. Two of the rule's three conditions hold; the governing one does not. No
second test read is recommended to the owner. Verdict:
`docs/readiness/2026-09-05-e22-dev-esb-shape-c-v1-verdict.md`.
