# Audio2Tool official-protocol replication, v1 — preregistration

Run `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, profile `baseline-reproduction`, one cell
(`R-official-raw`) on the frozen 400-item Audio2Tool discovery split. Written before any model
contact of this run.

Experiment fragment: `configs/experiment/a2t-official-protocol-replication-400-v1.json`.
Predecessor: `docs/readiness/2026-09-04-a2t-direct-baseline-calibration-v1-verdict.md`.

## 1. Why this flight exists

The 2026-09-04 calibration flight `SAEA-A2T-DIRECT-CALIBRATION-V1` flew four cells x 400 rows and
missed the paper on every tier — Tier 1 tool accuracy 64.0 against the published 92.4. It varied the
output contract (legacy registry text versus a native OpenAI `tools` list) and the audio path (raw
audio versus mmproj-free packets), found Factor A significant and negative, Factor D null, and
concluded that at most 8.75 pp of a 28–42 pp Tier-1 gap is explained by either.

Both of its output contracts were **this repository's reconstruction of an unreleased protocol**.
`configs/probes/README.md` recorded that as a fidelity caveat from the start and named the remedy:
"If their release later shows different prompts, R1 re-runs under the released ones with a new
manifest entry." The release appeared on 2026-09-03. This flight is that re-run: the request, the
decoding ceiling, the output parse and every metric come from the published code, so a residual gap
can no longer be attributed to a reconstructed prompt.

An earlier reading of the release — that the per-item `functions` and `instruction` fields scope the
candidate tool set per utterance — was **wrong and was withdrawn before any model contact**; its code
sits unused on side branch `staged/a2t-item-functions-cell` (`c6cecbfa`) and is not reused here. The
official code ignores both fields.

### The published row (arXiv:2604.22821 Table 3, Qwen3-Omni-30B)

| tier | tool accuracy | exact match |
|---|---:|---:|
| tier1_direct | 92.4 | 92.4 |
| tier2_parametric | 84.6 | 15.6 |
| tier3_multi_intent | 74.7 | 28.6 |
| tier4_implicit | 33.4 | 11.3 |
| tier5_needle | 90.6 | 36.0 |
| tier6_correction | 81.5 | 24.8 |
| tier7_multiturn | 54.6 | 16.3 |
| tier8_intent_blending | 41.7 | 12.4 |

## 2. The protocol, quoted from the pinned code

Source: `https://github.com/audio2tool/Audio2Tool`, MIT, commit
`b9d5383ca30945fbafb965a04bea40117e1e8a82`. Clone receipt with every git blob SHA-1 verified in the
clone: `docs/receipts/environments/audio2tool-official-code.json`. The two artifacts this repository
vendors are `reproduction/audio2tool_official/metrics.py` (byte-for-byte, blob
`d98277bcf69795c9a0ae54e538c170abfd8c51ca`) and `parse.py` (`BaseAudioModel.parse_tool_call` from
`models/base.py`, blob `977ce0cdde41b44b35ee2e6f43808d4eb16fec96`).

Adapter mirrored: `models/qwen3_omni.py` (blob `7f5f50e91a814620f040fcd11d9a5f77760db5d9`), the
deterministic HuggingFace one. Tool rendering: `utils/tools_schema.py` (blob
`ef108a9f9c2aad42b9f4a38e369d5f88cb24d5f5`). Metric aggregation: `evaluation/evaluator.py` (blob
`84c629f87550daf9e6f8c4aeb600bd0187d3b20b`). Dataset shape: `datasets/release_dataset.py` (blob
`ff9b3e22096b6bd0254e32ba3ef08e1d74c11474`) and `datasets/base.py` (blob
`4bddda1885f3c789f705acb43ff4580462918abb`). Config defaults: `utils/config.py` (blob
`3af612351b289c3d94b4fa48afba6ff87a92689a`) and `configs/example_config.yaml` (blob
`4f57feae0216192141b909b051185cdc2eb4b793`).

1. **Tools.** The adapter loads the WHOLE `tools_registry.csv` (our copy: 152 rows; columns
   `tool_id,domain,category,tool_name,signature,description,argument_defaults,argument_constraints`,
   with no `deprecated` column, so upstream's deprecation filter drops nothing) and renders it with
   `format_tools_compact`: sorted by `tool_name` under plain Python string ordering, one line each,
   exactly `- {signature}: {description}`, joined by `\n`. Nothing else from the registry — no
   defaults, no constraints, no domain, no category. It **ignores** the per-call `tools` argument,
   the per-item `functions` field and the per-item `instruction` field.
2. **System message.** Exactly `f"{system_prompt}\n\n## Available Tools:\n{tool_lines}"`, where
   `system_prompt` is the adapter's hard-coded single-line default:
   `You are an AI assistant that converts voice commands into tool calls. Listen to the audio and determine which tool should be called. Output ONLY the tool call in the format: tool_name(param1=value1, param2=value2). If no parameters are mentioned, output: tool_name().`
   (sha256 `1c52cd2ebca6e4737b706ccc231b01f008d35276a2153000d74ec9500018258a`).
3. **User message.** Content parts in this order: the audio, then the text
   `Convert this voice command to a tool call.`
4. **Template.** `processor.apply_chat_template(conversation, add_generation_prompt=True,
   tokenize=False, enable_thinking=False)`; no native `tools=`; talker disabled; bf16; librosa
   16 kHz mono; `use_audio_in_video=False`.
5. **Decoding.** `max_new_tokens=256`, `do_sample=False` (greedy), seed 42.
6. **Parse** (`BaseAudioModel.parse_tool_call`): `re.search(r'(\w+)\s*\((.*?)\)', raw_output)`, FIRST
   match only, giving `tool_name` and `params` from
   `re.finditer(r"(\w+)\s*=\s*['\"]?([^,'\"]+)['\"]?", params_str)` with values `.strip()`; fallback
   to the first whitespace token ending in `()`; else `tool_name` `""`. The HF adapter never fills
   `all_tool_calls`, so a multi-call response is judged on its FIRST parsed call.
7. **Metrics** (`evaluation/metrics.py`, `evaluator.py`):
   `tool_correct = normalize_tool_name(pred) == normalize_tool_name(gold.tool_name)` (strip
   `\(.*\)`, strip, lowercase) against the PRIMARY gold tool; `compute_parameter_accuracy` after
   `normalize_parameters` (keys lowercased/stripped; `None` -> `""`; bool -> `"true"`/`"false"`;
   int/float -> `str(v)`; else `str(v).strip().lower()`); `exact_match = tool_correct and` parameter
   exact (no missing, no extra, no wrong value); parameter precision/recall/F1 per sample, then a
   plain mean over samples. That mean is a **macro** average even though the paper's prose says
   "micro"; both are reported and both are labelled. `compute_multi_tool_metrics` (unordered set
   match) runs only when gold carries `additional_tool_calls` or the prediction has more than one
   tool, and `all_expected_tools = [tool_name] + additional_tool_calls`.
8. **Population.** `speakers_per_query 1` / `max_speakers_per_query 1` — the first successful speaker
   per `query_idx`, every query of each tier. Tier 7 rows are fed as ONE audio file with no history
   and no context in the prompt.
9. **The other official adapter.** `models/qwen3_omni_vllm.py` (blob
   `feec338d97760bcc3e70fe69b5d7f8f915b42c06`) differs: its own system prompt ("You are a voice
   command executor …"), an `Available tools:` block plus the same format sentence, temperature 0.3
   and top_p 0.95. This flight mirrors the deterministic HF adapter; the vLLM variant is recorded
   here as the other official variant and is **not flown**.

### What is measured before takeoff

`configs/probes/r1_audio2tool_official.txt` plus the registered `audio2tool-registry-compact` fill
compose the system message. Model-free verification already done: the composed message is
byte-identical to what the release's own `format_tools_compact` builds over the same CSV — 16,143
characters, sha256 `be7f31a2e8c7e6dd6a2db8673a54da26051cf2c3914218532521385175ffd8bd`. The prompt-fit
receipt re-asserts this against the clone and against the live rendered prompt.

## 3. The cell

| Cell | D2 arm | Audio path | System message | User turn | Model fragment |
|---|---|---|---|---|---|
| `R-official-raw` | `bare-core` | raw audio, bf16 mmproj loaded | the release's own, section 2 items 1–2 | audio, then the fixed sentence | `q4km-featcache-a2t-official-04ccc72a` |

Shared: temperature 0, seed 20260803, `max_tokens` 256, `id_slot` per-sample, one contact per item,
no evidence, no OBS, the `direct-only` phase program of `rails.controllers.EvidenceAgentController`
through `core.flight.FlightRuntime` and the OpenJiuwen executor — the same harness every calibration
cell flew, which is what makes the paired contrast against `A0prime-legacy-raw` a contrast in the
request protocol alone.

## 4. Deviations, recorded rather than fixed

Each of these is a difference from the published setup that this repository cannot remove, and none
of them is a design choice made in place of the protocol.

1. **Quantization and runtime.** Q4_K_M GGUF served by llama.cpp build `04ccc72a` instead of the
   release's bf16 HuggingFace checkpoint. The umbrella lock records Q4-vs-Q8 transcript WER of
   1.50 % and a 4.17x slowdown for Q8; Q8 is not flown here.
2. **Chat template.** The GGUF chat template under `--jinja`, not the HF `Qwen3OmniMoeProcessor`
   template. The prompt-fit route proves what that template actually renders, including that the
   system message appears verbatim in the rendered prompt.
3. **Audio path.** Raw audio through the bf16 mmproj — the closest available analogue of the HF
   audio input. The mmproj-free packet path is **not** flown here. The calibration measured Factor D
   as null (+1.0 pp legacy, −2.0 pp native, both CI90s straddling zero), so nothing is expected to
   turn on this.
4. **Roster.** The frozen 400 (50 per tier, mixed speakers, 374 distinct `query_idx`, already
   exposed) instead of the release's first-successful-speaker-per-`query_idx` over every query of
   every tier. This is the single largest population difference: it is a stratified subsample with
   duplicate `query_idx` values, not the full per-tier census.
5. **Tier 7.** The roster binds one audio per row, and `data.audio2tool._entry_media` selects the
   **final user turn's** wav from `chat_history`. The release also feeds one audio file with no
   history; which turn its own loader picks is not established here, so this is recorded as a
   possible difference rather than a match.
6. **Gold shape.** `data.audio2tool.load_official_gold` reproduces the release loader's
   `QuerySample`: primary `tool_name`, **verbatim** `extracted_params`, verbatim
   `additional_tool_calls`. This is deliberately NOT `a2t-gold-v1`, which JSON-coerces values and can
   take primary arguments from the `expected_tool_call` call string; scoring the official metric
   against `a2t-gold-v1` would score a different gold.
7. **Seed.** 20260803, not the release's 42. Inert: under greedy decoding a seed selects nothing.
8. **Temperature.** 0, the greedy equivalent of `do_sample=false`; the release's nominal
   `temperature: 1.0` is inert under greedy decoding.
9. **System-prompt whitespace variant.** `configs/example_config.yaml` carries the same four
   sentences as a YAML block scalar — newline-separated, with a trailing newline (sha256
   `aa2e344ee52c59019b938926f37498e0dc9c80bd01f6521eba5c3d81309a491d`) — and `run_benchmark.py`
   passes it to the adapter when a config is used, which means a config-driven official run would
   send the newline variant while the adapter's own default is the single-space one. The two differ
   ONLY in whitespace. This flight sends the in-code default. **This is the one remaining protocol
   ambiguity that could still be resolved differently**, and it is named here so a later reading of
   the verdict can weigh it.
10. **Serving geometry.** `-np`/`-c` are re-derived from the prompt-fit measurement (section 6) and
    have no counterpart in the release, which runs one request at a time on HF.

## 5. Budget (ExecutionPlan)

| Quantity | Value |
|---|---:|
| Planned model calls | 400 items x 1 contact + 8 canaries = 408; registered ceiling 450 |
| Planned speech audio | 2,159.688 s, rounded to the integer the plan contract requires; registered ceiling 2,300 s |
| Planned GPU hours | 1.0 |
| Paid API spend | 0 |

Budget is cumulative across every attempt of the run id. One-shot attempt semantics; at most one
recovery re-registration; a second failure stops the flight and the fix is proven on a 4-row dry run.

## 6. Pre-contact prerequisites

1. **Official-code receipt** — `docs/receipts/environments/audio2tool-official-code.json`, every blob
   SHA verified in the clone. DONE (commit `a4aeee3e`).
2. **Vendored scorer** — `a2t-toolcall-official` registered, with the vendored `metrics.py` blob hash
   asserted from the bytes on disk and the vendored parse re-derived from the clone. DONE
   (commit `a4aeee3e`).
3. **Prompt fit** — the exact request rendered through the pinned template on the resident server and
   measured, with its own exposure row, before any generation. Every one of the 400 requests must fit
   its slot with the 8,192-token reserve the 2026-09-03 preregistration set, and the rendered system
   text must equal the release's own. The measurement then fixes `-np`/`-c`: pick the largest slot
   count whose per-slot window still clears `worst required + 8,192`, with `slots x slot_tokens`
   equal to `-c` and `slot_tokens` a multiple of 512 so llama-server's own rounding cannot make the
   live slot disagree with the declared one.
4. **Exposure rows** — `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-PROMPT-FIT-V1`,
   `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-SMOKE-V1` and
   `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, each registered with `consumed = no` before the
   contact it authorizes.
5. **Wire check and smoke** — `FlightRuntime.wire_check` on a clean committed tree (zero contacts),
   then a 4-row smoke on the same four rows the calibration smoke used
   (`tier1_direct:000045`, `tier2_parametric:000045`, `tier5_needle:000060`, `tier6_correction:000008`).
6. **GPU power** — `nvidia-smi -q -d POWER` must report `enforced.power.limit` 100.00 W, as the
   calibration held. A lower cap stops the flight (the Legion SmartFanMode note).

## 7. Decision rule — three outcomes

Evaluated on the four tiers the paper reports above 80 %: `tier1_direct`, `tier2_parametric`,
`tier5_needle`, `tier6_correction`. The number is the **official** scorer's per-tier tool accuracy
(`a2t-toolcall-official`, the vendored `metrics.compute_tool_accuracy` against the primary gold tool).

- **PASS** — per-tier |delta| <= 5 pp against the paper row on all four tiers, AND the tier rank
  order preserved across all eight tiers.
- **CONSISTENT-WITHIN-NOISE** — not PASS, but the paper's value lies inside the tier's CI90 on all
  four tiers. The interval is the Wilson score interval for a binomial proportion at n = 50, reported
  per tier.
- **FAIL** — neither.

**Power.** n = 50 per tier gives a binomial standard error of 4–7 pp across the accuracy range the
paper reports (7.1 pp at p = 0.5, 3.7 pp at p = 0.9). PASS at this n is therefore a strong result:
the tolerance is smaller than the noise, so passing it on four tiers at once is unlikely by chance.
CONSISTENT-WITHIN-NOISE is weak evidence — it says only that 50 rows cannot distinguish this cell
from the paper — and the response to it is a larger roster drawn the release's own way
(first successful speaker per `query_idx`, every query of every tier), which is an **owner decision,
not this flight's**. FAIL means the published protocol, faithfully mirrored, does not reproduce the
published row on this runtime, and the deviations in section 4 become the candidate explanations.

Reported beside the decision, none of them part of it: the same per-tier table under
`a2t-toolcall-v2` ordered accuracy; official exact match and parameter F1 (macro and micro) per tier;
parse rate; the number of rows whose response named more than one call; and the paired contrast
against the sealed calibration cell `A0prime-legacy-raw`
(`attempt-20260904T081627Z-a0primelegacyraw`), with the official scorer applied to both through a
zero-contact re-score, so the effect of the request protocol alone is visible on the same 400 rows.

## 8. Claim surface

Nothing here is a superiority, generality or Stage-3 claim. The population is exposed discovery data
and no knob is tuned on it. Not authorized: any test contact, any mechanism arm, a Q8_0 flight, a
fresh roster, a training-free policy fit, or any edit to the locked SLURP cell.

## 9. Execution log

Filled in as the flight proceeds; every entry is written before the step it describes is read.

### 2026-09-04, Phase 1 — model-free preparation (zero contacts)

- Cloned the official code to `$SPEECHRL_DATA_DIR/repos/audio2tool` at commit `b9d5383c…` and
  verified all ten pinned blob SHAs with `git rev-parse <commit>:<path>` in the clone; wrote
  `docs/receipts/environments/audio2tool-official-code.json`. Commit `a4aeee3e`.
- Vendored `metrics.py` byte-for-byte (its committed git blob in THIS repository is
  `d98277bcf69795c9a0ae54e538c170abfd8c51ca`, the upstream blob itself) and
  `BaseAudioModel.parse_tool_call` as `parse.py`; registered `a2t-toolcall-official` with
  `data.audio2tool.load_official_gold` supplying the release's own `QuerySample` gold shape.
  13 unit tests, including the blob-hash assertion and the clone re-derivation. Commit `a4aeee3e`.
- Landed the request side: the `audio2tool-registry-compact` fill (byte-identical to the release's
  `format_tools_compact` over the real 152-row CSV), the frozen template
  `configs/probes/r1_audio2tool_official.txt` as a NEW probe-manifest entry
  `R1-audio2tool-official-protocol`, the `user_turn_text` / `user_turn_audio_first` transport seam
  (default off, with a regression test pinning the legacy calibration cell's exact wire bytes), and
  the four fragments. Commit `46ce43b5`.
- Full test suite: 6,259 passed, 6 failed — exactly the known pre-existing set (2 x `test_pemb3m`,
  2 x `test_pemb4r`, `test_bundle` CLI, and one full-suite-only registry-pollution failure in
  `test_engineering_base_check` that passes in isolation), plus the known
  `test_build_a2t_g6_family_sweep` collection error from the verl `scripts` shadow.
  `scripts/checks/engineering_base_check.py`: PASS.

### 2026-09-04, Phase 2 — prompt fit (zero generated tokens)

Row `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-PROMPT-FIT-V1`, registered before the server was
touched. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-official-protocol-replication-400-v1/prompt-fit/prompt-fit.json`
(SHA-256 `3aa8a34d5816a5360bc20b80675dc28ac97a0b8da7872115b1547612864fe1ac`). One `GET /props`, one
`POST /apply-template`, two `POST /tokenize`, zero generations.

- **Fidelity.** The rendered system message equals the pinned release's own, byte for byte:
  16,143 characters, SHA-256 `be7f31a2e8c7e6dd6a2db8673a54da26051cf2c3914218532521385175ffd8bd`
  from this repository's template + fill AND from the clone's own
  `format_tools_compact(load_tools_from_csv(...))`. It appears verbatim inside the prompt the pinned
  GGUF chat template rendered, and so does the user-turn sentence after the audio part.
- **Envelope.** 3,581 text tokens. The reconstruction the calibration flew was **3.7x larger** than
  the protocol it was reconstructing: 13,236 tokens for the legacy registry text, 13,914 for the
  native `tools` list. Worst required window over all 400 requests: 4,307 tokens
  (3,581 + 468 speech + 256 completion + 2 special), against the calibration's 14,730 / 15,408.
- **Geometry.** Section 6 item 3's rule fixes `-c 49152 / -np 3`, 16,384 tokens per slot, worst
  margin 12,077. `-np 4` at the same total context gives 12,288 per slot and a margin of 7,981 —
  211 tokens short of the 8,192 reserve — and is refused. `GET /props` reported exactly 16,384, so
  no rounding disagreement exists. This is one MORE slot than the calibration's raw cells could
  serve. `configs/model/q4km-featcache-a2t-official-04ccc72a.json` now carries these measured
  numbers in its `serving_geometry_basis`.

### 2026-09-04, Phase 3 — wire check and smoke

- `FlightRuntime.wire_check` on the clean committed tree `408a7f40`: 400 contacts through the real
  client, adapter, payload binding and sealer against the fake gate and transport, zero sockets
  opened. `payload_keys` equals `ARM_VISIBLE_FIELDS["bare-core"]` exactly — the user-turn text is
  transport-level request shape bound by `config_hash`, not a payload field, so the D2 allowlist is
  untouched by the seam. Dispatch used 3 slots. `seal_and_score` OK with all four registered
  scorers through `core.scoring_batch` as one whole-manifest job.
- Smoke row `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-SMOKE-V1`, its own fragment
  (`a2t-official-protocol-replication-400-smoke-v1`, `bounded-discovery-probe`, 12-call plan
  because attempt budget is run-cumulative). 4 of 4 contacts, FINALIZED, manifest SHA-256
  `c8c204e47ed7b48c0bceec49797bd20d606a29b7138136223844bc2fa4ca4b43`.
- **The smoke's one finding, which changed how the flight is read:** under the published protocol
  the model answers with CALL STRINGS, which is exactly what that prompt asks for and which
  `a2t-toolcall` / `a2t-toolcall-v2` cannot parse at all — they expect the reconstructed JSON-array
  contract. All four rows parse-failed under v1/v2 and all four parsed under the official scorer.
  The v1/v2 columns of this flight are therefore a format mismatch, not a model result. Recorded in
  the smoke's exposure row before the flight was launched.

### 2026-09-04, Phase 4 — the flight

Row `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`. 400 of 450 registered calls (408 planned),
2,159.688 of 2,300 registered speech-audio seconds, one attempt, FINALIZED, no recovery
re-registration, GPU held 100.00 W. Verdict:
`docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-verdict.md`. **FAIL** on the
section-7 rule; the substantive findings — a genuine +5.50 pp protocol effect on tool selection and
a Tier-1 result that moves the wrong way — are in that document.
