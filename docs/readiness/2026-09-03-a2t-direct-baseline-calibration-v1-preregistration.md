# Audio2Tool direct-baseline calibration, v1 preregistration (DRAFT, not yet registered)

Status: **DRAFT. Owner GO, a prompt-fit receipt, packet promotion, and an exposure-ledger row are
all still required before any contact.** Part D step 1 of the 2026-09-03 recovery plan; the
owner-approved rules are summarized in the study `CLAUDE.md` section "Engineering base and
experiment rules".

## 1. Why this flight exists

The paper (arXiv:2604.22821, Table 3) reports for the same frozen core Qwen3-Omni-30B:

| Tier | Paper tool acc | Paper EM | Repo A0 tool acc | Repo A0 EM (v1) | Repo A0 EM (v2) |
|---|---:|---:|---:|---:|---:|
| 1 direct | 92.4 | 92.4 | 58.0 | 12.0 | 40.0 |
| 2 parametric | 84.6 | 15.6 | 72.0 | 38.0 | 44.0 |
| 3 multi-intent | 74.7 | 28.6 | 62.0 | 4.0 | 14.0 |
| 4 implicit | 33.4 | 11.3 | 30.0 | 24.0 | 24.0 |
| 5 needle | 90.6 | 36.0 | 54.0 | 30.0 | 38.0 |
| 6 correction | 81.5 | 24.8 | 64.0 | 40.0 | 40.0 |
| 7 conversation | 54.6 | 16.3 | 60.0 | 44.0 | 44.0 |
| 8 intent blending | 41.7 | 12.4 | 34.0 | 2.0 | 6.0 |

The 2026-08-07 reproduction plan's P1 gate (per-tier |delta| <= 5 pp against this row; a bad miss
stops mechanism work until the pipeline is fixed) was missed by 34 pp on Tier 1 tool accuracy and
bypassed. The zero-contact scorer study of 2026-09-03 (`SAEA-A2T-MF-SCORER-V2-ZERO-CONTACT-STUDY`)
showed that scorer semantics explain part of the exact-match gap (Tier 1 EM 12 -> 40 under
`a2t-scorer-v2`) but none of the tool-selection gap: 142 of the 303 A0 exact-match failures are
wrong tool sets, 20 of 50 on Tier 1. The remaining gap therefore sits in the request protocol, and
two protocol facts have never been varied:

- **Output contract.** Every direct baseline pasted about 13k tokens of raw registry JSON into the
  system message and demanded a bare JSON array. The pinned llama-server runs with `--jinja` enabled
  and the GGUF chat template renders OpenAI-format `tools` natively (`<tools>` / `<tool_call>`); the
  repo never sent a `tools` field. Slices D1a/D1b (commits 00bb3fff, 064d1f73) added the D2-legal
  arms `bare-core-native-tools` and `speech-feature-query-native-tools`, the schema renderer
  (`data.audio2tool_tools.render_openai_tools`, 152/152 tools; every parameter carries a registry
  default, so no tool has a required parameter), and the transport pass-through that canonicalizes
  `message.tool_calls` back into the scorer's JSON array.
- **Audio path.** A0 (2026-08-18) flew raw audio through the mmproj on build 5d9dfcb58 with the D2
  arm `fixed-legal-context` (zero supply); every September direct M0 flew mmproj-free speech-feature
  packets on build 04ccc72a with the `speech-feature-query` arm. The two baselines therefore differ in
  audio path, build and arm, not only in roster.

## 2. Population

The frozen Audio2Tool discovery split, 400 items = 8 tiers x 50, seed 20260807, receipt
`docs/receipts/probe-samples/r1-audio2tool-sample.json`, split identity hash
`e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c`, split role `discovery`,
already exposed by A0 (row `SAEA-BASE-a2t-a0-400`). Total audio 2,159.688 s; longest item 35.714 s.
Test and confirmatory surfaces stay closed. Equal-tier reporting is the estimand; the natural
construction mixture (direct 12.27 %, parametric 20.64 %, ..., intent blending 5.59 %) is reported
as a reweighting beside it.

## 3. Cells (Factor A output contract x Factor D audio path), all on build 04ccc72a, Q4_K_M

| Cell | D2 arm | Audio path | Prompt | Model fragment | Geometry |
|---|---|---|---|---|---|
| A0' legacy x raw | `bare-core` | raw audio, mmproj loaded | the Audio2Tool adapter's legacy instruction (`rails/adapters/audio2tool.py::_INSTRUCTION_TEMPLATE`, byte-identical to what A0 sent; 13,236 measured registry tokens; `configs/probes/r1_audio2tool_direct.txt` is its source text) | new raw-audio Q4_K_M fragment on build 04ccc72a (inference receipt with mmproj; `-c 49152 -np 4` as A0) | A0's |
| A1 native x raw | `bare-core-native-tools` | raw audio, mmproj loaded | `configs/probes/r1_audio2tool_direct_native_tools.txt` plus `tools` | same as A0' | A0's |
| P0 legacy x packets | `speech-feature-query` | mmproj-free packets | the same adapter legacy instruction | `configs/model/q4km-mmproj-free-speech-native-np2-a2t-max1024.json` | section 8.1: `-c 65536 -np 2` |
| P1 native x packets | `speech-feature-query-native-tools` | mmproj-free packets | native tools | same as P0 | section 8.1 |

Shared: temperature 0, seed 20260803, `max_tokens` 1024, `id_slot` per-sample, one contact per item,
no evidence, no OBS, the `direct-only` phase program of `rails.controllers.EvidenceAgentController`
through `core.flight.FlightRuntime` (slice C4c) and the OpenJiuwen executor for every cell. A0 is not
reused as a cell because its build (5d9dfcb58) and arm differ; it stays the historical anchor.

Factor B (scorer) costs zero contacts: every cell is scored with both `a2t-toolcall` (v1) and
`a2t-toolcall-v2` through `core.scoring_batch`, one job per complete manifest. Factor C
(quantization, Q8_0) is deferred to a follow-up preregistration and flies only on 100 rows if A and D
leave a Tier 1 gap; the umbrella lock records Q4-vs-Q8 transcript WER 1.50 % and a 4.17x slowdown,
so its prior is low and its cost high.

## 4. Pre-contact prerequisites (each is its own model-free receipt)

1. **Packet promotion** for the 400 items from the legacy encoder cache into a
   `SpeechFeaturePacketV1` root (`/home/chao/feat-cache/a2t-calibration-q4km-packets-04ccc72a`);
   promotion fails closed on cache misses, in which case the CPU sidecar preprocessing runs first
   under its own `SAEA-SN-*-PREPROCESS` row (8 workers while any campaign flies, 20 otherwise).
2. **Raw-audio inference receipt** for build 04ccc72a with the bf16 mmproj loaded
   (`e0.generate runtime --role inference`), since the current receipts are mmproj-free or preprocess.
3. **Prompt fit** for the two native-tools cells: the exact request is rendered through the pinned
   template (`/apply-template` on the resident server or the tokenizer audit) and measured before any
   contact; every one of the 400 requests must fit its slot with the 8,192-token reserve.
4. **Exposure-ledger row** `SAEA-A2T-DIRECT-CALIBRATION-V1` (profile `baseline-reproduction`, split
   role `discovery`, the hash above, consumed `no`) registered before takeoff; one-shot attempt
   semantics; at most one recovery re-registration.

## 5. Budget (ExecutionPlan)

| Quantity | Value |
|---|---:|
| Planned model calls | 1,600 (4 cells x 400) + 8 canaries = 1,608; ceiling 1,700 |
| Planned speech audio | 4 x 2,159.688 s = 8,638.75 s; ceiling 9,000 s |
| Planned GPU hours | 6.0 (A0's resumed attempt ran 85 raw-audio calls in 1,895 s at -np 4; packets are faster) |
| Paid API spend | 0 |

## 6. Analysis and acceptance (fixed before takeoff)

- Per cell: overall and per-tier tool accuracy (ordered and multiset), exact match (v1 and v2), slot
  F1, parse rate, prompt tokens, latency, with the paper row beside every tier (rendered by
  `analysis.paired.render_markdown`).
- Main effects and interaction on the paired 400: A (native minus legacy) within each audio path, D
  (packets minus raw) within each contract; tier-stratified paired bootstrap CI90, 10,000 replicates,
  seed 20260903; saves/harms/ties and the exact sign test.
- **Acceptance of the calibration:** at least one cell reaches per-tier tool-accuracy |delta| <= 5 pp
  against the paper row on Tiers 1, 2, 5 and 6 (the tiers the paper reports above 80 %) with the tier
  rank order preserved. That cell becomes the direct baseline for every later mechanism experiment
  and fills the umbrella `published-baselines.md` row.
- **If no cell passes:** the miss is itself the finding; report which factor moved tool accuracy and
  by how much, and stop mechanism work until the owner decides (Factor C, prompt-template variants,
  or a protocol clarification request to the paper's authors).
- Nothing here is a superiority, generality or Stage-3 claim; the population is exposed discovery
  data; no knob is tuned on it.

## 7. What this preregistration does not authorize

No test contact, no mechanism arm, no Q8_0 flight, no fresh roster, no training-free policy fit, no
edit to the locked SLURP cell. It authorizes exactly the four direct cells above on the frozen 400,
after the four prerequisites are receipted and the owner's GO is recorded in this file.

## 8. Owner GO recorded 2026-09-03; execution log

The owner gave GO for this calibration flight on 2026-09-03 (recorded by the lead). The flight runs
in three phases with a hard stop between each; the study tree must be committed at every phase
boundary because `FlightRuntime.preflight` and the bundle sealer both refuse a dirty tree.

### 2026-09-04, Phase 1 (model-free preparation, zero contacts)

- Built the flight roster `docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-calibration-400-roster/flight-roster-receipt.json`
  (SHA-256 `6f352ea583d0bb91f77aad62e07bdad4d3210d066440fbfaee8e2af504853fe7`) with the new
  `scripts/build_a2t_calibration_400_roster.py`. Nothing was drawn: the roster re-expresses the
  frozen 400 parent receipt in the flight-roster schema and adds `media_relpath`, `audio_seconds`
  and `audio_sha256`. 400 rows, 50 per tier, 2,159.688 s, longest item 35.714 s.
- Verified the roster reproduces the parent split identity hash
  `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` under the parent's own key
  convention, and recorded the second, different hash the same 400 samples produce under the
  `FlightRuntime` carrier-prefixed convention,
  `11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b`. Section 2's hash is the
  former; a `FlightRuntime` exposure row must carry the latter.
- **Section 4 item 1 is amended in one respect and the packet root is renamed.** The D1 media
  supplement this campaign's dataset fragment was to declare cannot exist: all 400 sample ids are
  already inside the parent D1 identity closure, and `contracts.gate_media_identity` refuses any
  supplement that duplicates a base D1 sample. Media identity is therefore verified against the
  parent D1 manifest directly and no supplement is created. The packet root is
  `/home/chao/feat-cache/a2t-calibration-400-packets-04ccc72a` (section 4 named
  `a2t-calibration-q4km-packets-04ccc72a`; the roster's own name is used instead so the directory
  matches the roster and the model fragment).
- Landed the config fragments: dataset `audio2tool-calibration-400`; experiments
  `a2t-calibration-400-preprocess` and `a2t-direct-calibration-400-v1`; baselines
  `a2t-direct-calibration`, `a2t-direct-native-tools-calibration`, `a2t-direct-packets`,
  `a2t-direct-packets-native-tools`; models `q4km-featcache-a2t-calibration-04ccc72a` (raw audio,
  `-c 49152 -np 3`, 16,384 tokens per slot) and
  `q4km-mmproj-free-speech-native-a2t-calibration-max1024` (packets, `-c 65535 -np 3`, 21,845
  tokens per slot). Section 3's raw-audio geometry is therefore `-np 3`, not A0's `-np 4`: at
  `-np 4` a slot holds 12,288 tokens and cannot carry the 13,236-token registry request at all.
- Added the `--calibration-400` profile to `scripts/a2t_g1_preprocess.py` and ran its two
  contact-free modes. `--emit-identity` reports config hash
  `e2dc87187a8833050daddbcf72eccb0886c56ff9a89f7d43a81b44f2096a65a4`; `--preflight-only` PASSED and
  measured 312 of 400 rows already warm in the current-build legacy cache, 0 of 400 packet
  manifests present and no promotion receipt.
- Added `scripts/flights/run_calibration_cell.py`, one generic entry that reads the four cells from
  this experiment fragment's own `cells` array and binds the seams `saea-driver flight` leaves
  unbound (packet promoter, speech-feature client bindings, tool-schema resolver, the packet direct
  arm, and the session start that preserves the model fragment's full `server_args`).
- Registered three exposure rows: `SAEA-SN-A2T-CALIBRATION-400-PREPROCESS` (400 calls, 2,300 s,
  0.3 GPU-h), `SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1` (16 calls, 100 s, 0.2 GPU-h) and
  `SAEA-A2T-DIRECT-CALIBRATION-V1` (1,608 calls, 9,000 s, 6.0 GPU-h), all `consumed = no`.
- `--dry-run` preflight for all four cells passed config composition, receipt-bound split load,
  ExecutionPlan validation, the frozen-core gate and the exposure-row cross-check, and then
  correctly refused on the uncommitted Phase-1 tree. The prompt-budget arithmetic was reproduced
  outside the gate: every cell is ALLOW, with worst-case required windows of 15,453 tokens
  (legacy contract, heuristic count) and 1,659 tokens (native contract, whose tool schemas travel
  in the request's `tools` field and are therefore not counted by the pre-flight estimate at all).
- Section 4 item 3 is consequently load-bearing: the exact prompt-fit receipt for the two
  native-tools cells must be measured through the pinned template before takeoff, because the
  rendered `tools` block is invisible to the pre-flight estimator, and the raw-audio slot's
  margin at `-np 3` is 1,608 tokens against the measured 13,236-token legacy envelope.

### 2026-09-04, Phase 2a (harness repair, zero contacts)

Owner decision on the Phase-1 blockers: the four seams `saea-driver flight` left unbound are
defects in the shared harness, not something a launcher may paper over, so they were fixed as
config-driven defaults in `core/flight/runtime.py` and the flights entry shrank to adapter wiring.
No server or sidecar was started.

- **`serve` no longer discards the model fragment's `server_args`.** It now merges them
  (`merge_server_args`), overriding only `-np`/`-c` from the adapter geometry. Before this, the
  stage passed those two flags and nothing else, so `-ngl 999` never reached llama-server and every
  cell of this flight would have been served on the CPU. `serve` also now passes the runtime
  receipt's own `role` (an mmproj-free inference receipt declares `inference`, which is what makes
  `start_session` inject `--no-mmproj`) and the fragment's `model_materialization_root`; both were
  previously ignored, so a packet cell would have been served WITH the mmproj and from the wrong
  model root.
- **The client factory now supplies `speech_feature_root` and `speech_packet_bindings`** for any
  arm whose D2 field set carries `speech_feature_parts`, read from the model fragment and from the
  registered promotion receipt (whose `feature_root` must agree with the fragment, and which must
  cover every sample). `rails.core_client.FrozenCoreClient` refuses to be constructed for such an
  arm without them, so both packet cells previously died at client construction.
- **The default tool-schema resolver** resolves a baseline fragment's `tool_schema_fill` through
  `core.policies.TOOL_SCHEMA_FILLS`, the same registry the non-flight path uses; both native cells
  previously refused because the seam defaulted to `None`. Verified against the real fragments:
  152 tool schemas resolve for A1 and P1.
- **The default packet promoter** binds
  `core.model.speech_features.materialize_legacy_cached_speech_feature_packets` to the registered
  promotion receipt (its own `feature_root`, `legacy_cache_dir`, encoder receipt hash and
  decoder/mmproj hashes), and refuses any promoted packet whose SHA-256 that receipt does not pin.
  A raw-audio arm promotes nothing and records why.
- **`run_phases` now carries the packet audio path itself** as the fixed-policy branch for
  speech-feature arms: one contact per sample with exactly one `input_speech_features` query
  descriptor. `rails.runner.run_rails_experiment` cannot express it (it always calls `complete()`
  under the audio invariant), which is why no packet cell could previously fly. Same single
  contact, same adapter instruction, same post-hoc scoring; no extra phase and no evidence.
- 16 new unit tests cover each default and the packet branch with fakes;
  `pytest tests/unit/test_flight_runtime.py` is 40 passed. The engineering-base gate stays PASS.
- Section 3's raw-audio cells serve from the data root (the fragment declares no
  `model_materialization_root`), so their 18.5 GB GGUF loads over drvfs rather than from ext4;
  the packet cells load from `/home/chao`. Both roots hold the pinned bytes.
- GPU power state checked ahead of Phase 2b: `enforced.power.limit` reads 100.00 W (not the 35 W
  Quiet-mode cap), memory 0 of 24,463 MiB used.
- One pre-existing red test repaired in passing:
  `tests/unit/test_engineering_base_check.py::test_regex_extraction_agrees_with_package_import`
  compared a scan of all six canonical registry files against an import list that omitted
  `rails/controllers.py`, so the four `phase-*-v1` AGENT_CONTROLLERS ids commit `a80eef79` made
  visible to the scan had no import-side counterpart. The missing import was added; the check
  itself was always PASS.

### 2026-09-04, Phase 2b (preprocessing, prompt fit, geometry decision)

- **mmproj copy not required.** `/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/`
  already held `mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf` at exactly the receipt's
  `f0dfe825fb692d426362b1ac79678fc08daa4758f7151526cad110515f122883`, so the raw-audio cells' new
  `model_materialization_root` resolves on ext4 with no byte copied. Verified by `sha256sum` before
  any server started.
- **GPU power state** checked at mission start and again immediately before serving:
  `enforced.power.limit` 100.00 W, max SM clock 3,090 MHz, 0 MiB used, ports 8080/8090 free. Not the
  35 W Quiet-mode cap.
- **Preprocessing (`SAEA-SN-A2T-CALIBRATION-400-PREPROCESS`) completed.** 400 encode contacts, 0
  failures, 2,159.688 referenced speech-audio seconds, 721.5 s wall (690.4 s in-request), then 400
  of 400 packets promoted in about 9 s at 20 workers. Report SHA-256
  `b30ed122a33f88e246503267a73711f5c5ac0eca14c8c383db5090e9b96e280a`; promotion receipt SHA-256
  `2b848b86a4228452d8965f4542005e3d28d3370243b3353dfd34c10cac2f8b92`. The GPU decoder on 8090 was
  unreachable before and after. Row flipped to consumed=yes.
- **Measured packet speech tokens: min 13, median 65, p90 143, p95 169, max 468** -- materially
  below the 514 the registered geometry assumed from 35.714 s x 14.4 tokens/s. Every later window
  figure in this log uses the measured 468, not the assumption.
- **Prompt fit (`SAEA-A2T-DIRECT-CALIBRATION-PROMPT-FIT-V1`, prerequisite 3) completed with zero
  generated tokens** -- 1 `GET /props`, 2 `POST /apply-template`, 4 `POST /tokenize`, no completion
  endpoint. Receipt `docs/checks/speech-aware-evidence-acquisition/
  2026-09-04-a2t-direct-calibration-400-v1/prompt-fit/prompt-fit.json` SHA-256
  `d867d858ec3a0a7c2a10758dc2edb61a51eaec80b1c7abec19b4753daf6888d5`.

| envelope | text tokens | worst required window | A0'/A1 slot 24,576 | P0/P1 slot 22,016 |
|---|---:|---:|---:|---:|
| legacy registry text | 13,236 | 14,730 | margin 9,846 | margin 7,286 |
| native `tools` list (152) | 13,914 | 15,408 | margin 9,168 | margin 6,608 |

- **The native contract is LARGER than the legacy one, by 678 tokens.** Section 1 framed the native
  path as replacing 13k tokens of pasted registry text; the pinned template in fact renders the same
  registry back at 13,914 tokens. Factor A is therefore a contract-shape comparison at matched
  prompt volume, not a prompt-shrinking one -- and any later reading of A that attributes a gain to
  "less context" is unsupported by this measurement.
- **Section 8 raw-geometry rule applied: -np 3 -> -np 2.** A1's worst request needs 15,408 tokens,
  above the 14,800 threshold, and left only 976 tokens of margin in a 16,384-token slot. The raw
  fragment `configs/model/q4km-featcache-a2t-calibration-04ccc72a.json` now serves `-c 49152 -np 2`
  (24,576 tokens per slot). All four cells fit with at least 6,608 tokens of margin.
- **Serving-geometry defect found and fixed: llama-server rounds each slot's `n_ctx` up to a
  multiple of 512.** The packet fragment's `-c 65535 -np 3` was served back by `GET /props` as
  22,016 tokens per slot, not the declared 21,845, so the fragment, the adapter geometry and the
  live server disagreed. The fragment now declares the post-rounding numbers (`-c 66048 -np 3`,
  22,016 per slot) and the measurement refuses only when the live slot is SMALLER than declared.
- **Runtime defect found and fixed: `serve()` had no counterpart.** A flight started an 18.5 GB
  llama-server and never stopped it, so a second serving geometry could not obtain VRAM and the
  process orphaned the server on exit. `FlightRuntime.stop_serving()` (seam `session_stopper`,
  default `core.session.stop_session`) now stops only a server this flight itself started -- never a
  reused one -- and `FlightQueue` stops the resident server on a genuine geometry change and from
  `shutdown()`, tracking the owning flight separately from the most recent user.
- **The 16-call smoke is registered and wired but NOT yet flown.** Two blockers were found and
  both are now closed in configuration: (1) the smoke borrowed the flight fragment, whose
  `execution_profile` is `baseline-reproduction`, so the gate refused it against its own
  `bounded-discovery-probe` exposure row -- a new fragment
  `configs/experiment/a2t-direct-calibration-400-smoke-v1.json` now carries the smoke's own profile,
  its own 4-calls-per-cell plan and the same four cells; (2) with that fixed the gate PASSES and
  preflight advances to `require_clean_study_repo`, which refuses this phase's own working tree.
  The smoke therefore needs one commit of the Phase-2b artifacts before it can run; nothing else
  stands in its way. Command after the commit, one geometry group at a time:
  `python scripts/flights/run_calibration_cell.py --experiment a2t-direct-calibration-400-smoke-v1
  --cells A0prime-legacy-raw,A1-native-raw --sample-ids <the four ids> --run`, then the same for
  `P0-legacy-packets,P1-native-packets`.
- No llama-server is left resident: ports 8080 and 8090 are free and the GPU reports 0 MiB used.
