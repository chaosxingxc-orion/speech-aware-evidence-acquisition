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

### 2026-09-04, Phase 2c (smoke attempt 1: refused before any contact)

The registered 16-call smoke did NOT fly. The raw-geometry group
(`A0prime-legacy-raw`, `A1-native-raw`) was dispatched through `FlightQueue` and both cells
refused inside `run_phases`, at client construction, **before a single model contact**. The packet
group was not attempted. `SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1` stays `consumed = no`.

- **Spend: zero.** Both attempts recorded `calls 0 / audio_seconds 0.0` and produced no
  `outputs.jsonl`, no trace and no manifest. Both are now durably `ABORTED` with the reason
  recorded, rather than left `OPENED`.
- **The gate and the geometry were fine.** Preflight passed for both cells against the new
  smoke fragment (config composition, receipt-bound 4-row split, ExecutionPlan, frozen-core gate,
  exposure-row cross-check, clean tree, attempt reservation, prompt budget), and the raw server
  came up and was stopped cleanly -- ports 8080/8090 free and 0 MiB GPU afterwards, which is the
  Phase-2a `stop_serving()`/`shutdown()` fix working on a failure path.
- **Root cause.** `rails.core_client.FrozenCoreClient` accepted only four D2 field sets, every one
  of which carries `supplied_evidence`/`evidence_provenance`, because the bridge was written for
  `fixed-legal-context` -- the arm A0 itself flew, sending two empty evidence lists for its
  zero-supply requests. `bare-core` and `bare-core-native-tools` declare no evidence fields at all,
  and `core.model.adapter.FrozenCoreAdapter.request` enforces
  `set(payload) == ARM_VISIBLE_FIELDS[arm]` EXACTLY, so those two empty lists are an allowlist
  violation for them rather than a harmless extra. Both raw cells of this factorial were therefore
  unreachable from the moment they were written, and slice D1a's `bare-core-native-tools` arm had
  never been constructible at all. Nothing in preflight can see this: the client is built in
  `run_phases`.
- **Fix.** `_ACCEPTED_ARM_FIELD_SETS` now also admits the evidence-free field set and that set plus
  `tool_schemas`; `complete()` omits exactly the two evidence keys for an arm whose own declared
  fields lack them, and refuses loudly if such an arm is handed prompt-level supply text it could
  not record. The branch reads the arm's declared fields, never an arm-name list -- the discipline
  `core.policies.FixedPolicy.run_sample` already documents. `fixed-retrieval`,
  `exemplar-context` and `fixed-legal-context-replay` remain refused, so nothing was over-widened.
  Five new tests cover acceptance, payload shape, byte-identity against `fixed-legal-context` minus
  the evidence fields, the supply-text refusal, and the three still-unsupported arms; one
  pre-existing test that used `bare-core` as its "unsupported arm" exemplar now uses
  `fixed-retrieval`, with its assertion unchanged.
- The smoke can be re-flown as soon as this fix is committed; it needs no re-registration, since
  its row is untouched and unspent.

### 2026-09-04, Phase 2c attempt 2: two more harness defects, still zero contacts

The smoke was re-run after the client fix and refused again, at the NEXT link in the same chain.
Spend is still zero on every attempt; `SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1` remains `consumed = no`
and all four attempts to date are durably `ABORTED` with `calls 0 / audio_seconds 0.0`.

- **Defect: the attempt was opened twice.** `FlightRuntime.preflight` called
  `AttemptStore.open_attempt`, and `core.model.adapter.FrozenCoreAdapter` -- "the ONLY model request
  path" by its own module docstring, and the opener that `AttemptStore.abort_if_opened` itself names
  -- opens the SAME pair when `run_phases` builds the client. A `(run_id, attempt_id)` pair is a
  one-time key, so every flight through this harness died at client construction with "already
  reserved or opened ... a retry must mint a fresh attempt_id", AFTER preflight had reported
  success. The handle preflight kept was never read by anything. Fixed: preflight now CHECKS
  availability (refusing an attempt id whose file already exists, which keeps the fail-early intent)
  and leaves the reservation to the adapter.
- **Defect: the slot-affinity sentinel was never resolved.** All four model fragments declare
  `decoding_params.id_slot = "per-sample"`. That is a sentinel, not a value: the batch executor that
  owns slot allocation resolves it to an allocated llama-server slot integer
  (`reproduction.ojw.runner.SLOT_AFFINITY_SENTINEL`, and `core.policies`' fixed-batch policy does
  the same from a free-slot queue). `FlightRuntime` passed it through verbatim and
  `FrozenCoreAdapter.request` refuses it, so no cell could have made a single contact. Fixed:
  `_decoding_params()` resolves the sentinel to slot 0 -- this harness dispatches exactly one
  contact at a time, so there is never more than one in-flight request to allocate for, and pinning
  one slot is also the best case for the thing slot affinity exists to buy (every request of a
  direct baseline shares the same multi-thousand-token instruction prefix). A future concurrent
  dispatcher must resolve it per in-flight worker instead; the constant and that requirement are
  documented at the definition. The resolution is recorded in the `run_phases` receipt.
- **Both defects were found without spending a registered call.** The second one was caught by a
  throwaway wire check that drives the REAL `FrozenCoreClient`, the REAL adapter, the REAL payload
  binding and the REAL promoted packets for all four cells against a FAKE transport -- no server, no
  GPU, no model. That check now passes for every cell: 4 contacts each, payload key set exactly
  equal to the arm's own `ARM_VISIBLE_FIELDS` entry, 152 tool schemas present for both native cells,
  `id_slot` resolved to 0, and the packet cells' real packet bytes loaded and hash-verified against
  the promotion receipt. A third refusal in the same chain is therefore unlikely, though sealing and
  official scoring remain unexercised against real bytes until the smoke actually flies.

### 2026-09-04, Phase 2d: the wiring proof becomes a committed mode

Three defects in a row (client arm refusal, double-opened attempt, unresolved slot sentinel) were
each found only by burning a server start on the registered smoke, and none was visible to
preflight. That loop is now closed with a contact-free proof that runs on the working tree.

- **`FlightRuntime.wire_check()`** drives a flight's entire request path against two doubles and
  nothing else. Real: the composed fragments, the adapter and its samples, the payload binding, the
  tool-schema resolution, the promoted speech-feature packets (loaded and hash-verified), the arm's
  own dispatch, and the whole `FrozenCoreClient`/`FrozenCoreAdapter` stack including its payload
  allowlist and attempt accounting. Fake: only `WireCheckGate` and `WireCheckTransport`, which never
  opens a socket. It asserts, per request, that the payload key set equals
  `ARM_VISIBLE_FIELDS[arm]` exactly, that `tool_schemas` is present for native arms and absent
  otherwise, and that `id_slot` is an integer -- the three checks the three landed defects would
  each have failed.
- It is generic, so any carrier flying through `FlightRuntime` gets it. `preflight` was factored so
  the check reuses exactly the same fragment/adapter/split resolution without opening the gate or
  asserting a clean tree -- the latter would make the check unusable precisely when it matters, on
  the tree carrying the fix under test. The fixed-policy dispatch was likewise factored so the check
  drives the same code a real flight does.
- Everything is written under a `WIRECHECK-` run id that is unique per invocation (attempt budget is
  run-cumulative, so a fixed id let the first cell exhaust the second's), under
  `<data root>/wire-check/`, never the `runs/` tree, and the attempt it opens is aborted before
  returning. No exposure row references such a run id and none should.
- **Sealing and official scoring are exercised in the same mode**: the check seals a manifest from
  the fake responses and runs the registered scorers over it. A dirty study tree refuses a COMPLETED
  manifest by design, which is RECORDED as `seal_and_score: REFUSED` rather than raised, so the
  client half still reports. On a clean tree the same command exercises manifest, verify and the
  three scorers for real. Any score it produces is computed over a canned response and measures
  nothing.
- `scripts/flights/run_calibration_cell.py --wire-check` runs it for every requested cell and writes
  one receipt to `docs/checks/speech-aware-evidence-acquisition/
  2026-09-04-a2t-direct-calibration-400-v1/wire-check/wire-check.json`.

Result for all four calibration cells, zero model contacts and zero servers started:

| cell | arm | contacts | payload keys = ARM_VISIBLE_FIELDS | tool_schemas | id_slot | packets verified |
|---|---|---:|---|---:|---:|---:|
| A0'-legacy-raw | `bare-core` | 4 | yes (10) | 0 | 0 | 0 |
| A1-native-raw | `bare-core-native-tools` | 4 | yes (11) | 152 | 0 | 0 |
| P0-legacy-packets | `speech-feature-query` | 4 | yes (18) | 0 | 0 | 4 |
| P1-native-packets | `speech-feature-query-native-tools` | 4 | yes (19) | 152 | 0 | 4 |

The payload-to-wire-body step (`tool_schemas` -> `tools`) belongs to
`core.model.transport.LlamaServerTransport` and is covered by that transport's own committed tests;
this check asserts at the transport seam, where the payload is what crosses. The only link now
untested against real bytes is the server itself.

### 2026-09-04, Phase 2e: the wire check pays for itself -- defect 6, found for free

Running `--wire-check` on the CLEAN tree got past the git guard and immediately refused at the
sealing link, for all four cells:

    BundleError: outputs line 1 lacks required fields ['admitted', 'carrier_lock_key',
    'request_id', 'request_sha256', 'response_sha256', 'response_text_sha256', 'text']

- **Defect: `seal()` wrote outputs rows the bundle contract refuses.**
  `core.bundle.outputs._REQUIRED_OUTPUTS_FIELDS` is a hash-bound audit contract -- `request_id`,
  `sample_id`, `carrier_lock_key`, `arm`, `text`, `admitted` and three identity hashes -- and
  `verify_bundle` additionally binds each row's `carrier_lock_key`/`arm` to the manifest and
  re-derives `response_text_sha256` from the row's own `text`. `FlightRuntime.seal()` wrote its own
  loose diagnostic dict instead (`messages`/`metrics`/`consumption`), so a sealed rails flight could
  never verify. **On the real smoke this would have refused at seal time, after all 16 contacts had
  been spent**; on the 400-row flight, after 1,608.
- **Root cause underneath it**: the three hashes only ever existed on `core.model.CoreResponse`,
  which `rails.core_client.FrozenCoreClient.complete` discarded -- it returns `response.text` alone.
  Nothing on the rails path could have written a verifiable row.
- **Fix, in two parts.** `RequestTiming` now carries `request_sha256`, `response_sha256` and
  `response_text_sha256` (defaulted to `None`, so every existing construction site is untouched),
  populated from the adapter's own `CoreResponse`; and a new
  `FlightRuntime._canonical_output_rows()` builds exactly the contract's nine fields from those
  per-request records, one row per sample, failing closed when a sample has no record or a record
  lacks its hashes. Both `seal()` and the wire check's own sealing step write through it, so they
  can never drift apart. Four new tests assert the row set against the real
  `_REQUIRED_OUTPUTS_FIELDS`, the text-to-hash binding, and both refusals.
- This is the third harness defect that would have cost a full campaign to discover, and the first
  one caught before spending anything. The wire check has now paid for itself.

Receipts under `docs/checks/speech-aware-evidence-acquisition/
2026-09-04-a2t-direct-calibration-400-v1/wire-check/`: `wire-check.json` is the dirty-tree run that
proved the client path for all four cells; `wire-check-clean.json` is the clean-tree run that found
this defect, re-issued after the fix and therefore again recording `seal_and_score: REFUSED` -- this
time for the ordinary dirty-tree reason, since the fix itself dirties `src/`. The client half is
unchanged and green in both: 4 contacts per cell, payload key set equal to `ARM_VISIBLE_FIELDS[arm]`,
152 tool schemas on both native cells, `id_slot` 0, and 4 packets hash-verified on both packet cells.
One more `--wire-check` on the next clean tree closes the seal and scoring links for real.

The registered 16-call smoke was NOT run in this phase: the standing rule is to stop for a commit
once a refusal is diagnosed and fixed. `SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1` remains
`consumed = no` with all 16 calls unspent.

### 2026-09-04, Phase 2f: defect 7, and a false green in the wire check itself

The clean-tree wire check reported `seal_and_score: OK` for all four cells -- and it was WRONG.
Reading the receipt rather than the status line showed every scoring job had failed.

- **Defect 7: `seal()` named the outputs artifact `outputs.jsonl`, not `<run_id>.outputs.jsonl`.**
  The `cost` scorer locates a run's manifest by the shared run_id stem
  (`core.scorers._manifest_path_for_outputs`, the same convention
  `core.bundle.build_manifest` uses for `<run_id>.run-manifest.json`) and refuses any other name:
  "cost scorer requires an outputs artifact named '<run_id>.outputs.jsonl'". The manifest built and
  verified; only the official scoring step failed -- which on the real smoke would have landed after
  all 16 contacts were spent, and on the 400-row flight after 1,608. Fixed in both `seal()` and the
  wire check's own sealing step.
- **Defect 8, in the wire check itself: a failed score batch was reported green.**
  `core.scoring_batch.run_score_batch` reports per-job outcomes in its RESULT dict and does not
  raise, so the wire check's "no exception means OK" was a false green that hid defect 7 behind an
  OK line. `seal_and_score` is now green only when every job succeeded; otherwise it reports
  `SCORING_FAILED` with each job's error, return code and stderr log. The fake score batch in the
  unit tests was made faithful to the real success shape so this can never silently regress.
- This is the failure mode a wiring proof is most exposed to: a check that reports what it hoped
  rather than what happened is worse than no check. It was caught by reading the receipt the check
  itself wrote, which is the reason the receipt records the full batch result and not just a verdict.

Status of the links: contact-free client path green for all four cells (4 contacts each, payload key
set equal to `ARM_VISIBLE_FIELDS[arm]`, 152 tool schemas on both native cells, `id_slot` 0, 4 packets
hash-verified on both packet cells); manifest build and `verify_bundle` green; official scoring NOT
yet observed green -- the naming fix landed after the last clean tree, so the next `--wire-check` on
a clean tree is the first that can honestly report it.

Receipts under `docs/checks/speech-aware-evidence-acquisition/
2026-09-04-a2t-direct-calibration-400-v1/wire-check/`: `wire-check-clean-2.json` is the run that
reported the false green (kept deliberately -- it is the evidence for defect 8, and its embedded
`score_result` shows `succeeded: 0, failed: 1` under a status line that said OK).

The registered 16-call smoke was NOT run in this phase; the standing rule is to stop for a commit
once a refusal is diagnosed and fixed. `SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1` remains
`consumed = no` with all 16 calls unspent.

### 2026-09-04, Phase 2g: first real contacts, and defect 9 at the finalizer

The wire check was truthfully green for all four cells this time (every scorer job succeeded), so
the smoke launched on the still-clean tree. **Cell A0' made the campaign's first four real model
contacts** and then died in `seal()`, at the one link the wire check did not cover.

- **A0'-legacy-raw actually flew**: 4 of 4 contacts, 16.948 speech-audio seconds, 53,199 prompt
  tokens, 120 completion tokens, 6.538 s of in-request latency, 4 admitted outputs rows with real
  model text, a COMPLETED manifest and a verified trace. The server came up and was stopped
  cleanly. A1 never started, because the queue raised on A0's seal.
- **Defect 9: `seal()` called `finalize_bundle` with no ledger cells.**
  `core.tracking.ledger_row_for_bundle` requires the complete 21-column ledger surface;
  `core.tracking.bundle_ledger_cells` derives only nine of them and says so -- the other twelve are
  "human judgment or external-index facts this module has no basis to invent", i.e. the caller's.
  `seal()` supplied none, so finalize refused with "ledger row must have exactly the columns ...".
  Fixed: `FlightRuntime.CALLER_LEDGER_COLUMNS` names those twelve, `_default_ledger_cells(plan)`
  derives the honest ones from the flight's own composed identity and marks the four judgment
  columns `pending post-run analysis` (a run seals before its verdict exists; inventing one would be
  worse than saying so), `seal(ledger_cells=...)` lets a caller override any of them, and a missing
  column now refuses in the harness with a clear message instead of deep inside tracking.
- **The wire check's own gap, closed.** It exercised the manifest builder, the verifier and the
  scorers but NOT the finalizer, which is why defect 9 survived a green wire check. It now validates
  the same complete ledger surface through an injectable `ledger_validator` seam (default
  `core.tracking.ledger_row_for_bundle`), in validate-only mode -- the real finalizer would settle
  the very attempt the check is about to abort.
- Four new tests: the ledger surface is validated with every caller-owned column present, `seal()`
  refuses a missing column, the judgment columns carry the pending marker, and the finalizer doubles
  in both test files now assert the same contract rather than ignoring the argument.

**Budget position, which constrains the recovery.** The registered row allows 16 calls and 4 are
now durably spent, leaving exactly 12 -- exactly the three remaining cells. The recovery is
therefore NOT a re-run: A0's bundle is sealed, COMPLETED and its attempt still OPENED, so once
defect 9 is committed it can be finalized and scored with ZERO further contacts, and only A1, P0 and
P1 need to fly (12 calls). That lands the smoke at exactly 16 with no re-registration. Re-running
A0' instead would need 20 calls against a 16-call row and must not be attempted.

`SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1` therefore stays `consumed = no` for now, with 4 of its 16
calls spent and one attempt OPENED pending that zero-contact finalize.

### 2026-09-04, Phase 2h: A0' recovered with zero contacts; defect 11 stops A1 before its first

- **A0'-legacy-raw is FINALIZED, at zero additional cost.** Its already-sealed bundle was finalized
  and scored through `core.bundle.finalize_bundle` with exactly the ledger cells
  `FlightRuntime.seal()` now builds; the attempt settled from OPENED to FINALIZED and all three
  registered scorers (`a2t-toolcall`, `a2t-toolcall-v2`, `cost`) are present in its scores artifact.
  No model was contacted. The four calls it had already spent are the only ones this cell will ever
  cost -- it was never re-run.
- **Defect 11: the smoke fragment's execution plan was sized per cell, but budget is enforced
  RUN-cumulatively.** `core.model.adapter.FrozenCoreAdapter` re-reads every prior attempt's durable
  actuals for the run id on every request and refuses when prior spend plus this attempt exceeds
  `planned_model_calls`. All four cells are attempts of ONE run id, so the fragment's per-cell plan
  of 4 was already exhausted by A0's 4: A1 refused at its first request, "allows 4 calls (4 already
  spent by other attempts on this run)", **before spending anything**. Fixed in
  `configs/experiment/a2t-direct-calibration-400-smoke-v1.json`: the plan is now the whole smoke
  (16 calls, 68 speech-audio seconds, 0.2 GPU hours), which is also exactly what the exposure row
  registers. Two tests now assert that both the smoke and the 400-row flight plans cover
  cells x rows, so this class cannot regress silently.
- **Defect 12: the single-cell CLI path never stopped its server.** `FlightQueue.shutdown()` stops
  the resident server on the queue path; the single-cell path had no counterpart, so any stage
  raising after `serve()` left an 18.5 GB llama-server resident (and orphaned at process exit) --
  precisely what prevents the next serving geometry from starting. The six stages are now wrapped in
  try/finally with `stop_serving()`. (The A1 refusal happened to leave nothing behind -- ports
  8080/8090 free, GPU 0 MiB, no llama-server process -- but that was luck, not design.)

**Budget position after this phase**: 4 of the registered 16 calls are durably spent, all by A0's
single FINALIZED attempt (16.948 speech-audio seconds of the registered 100). Every other attempt on
this run id is ABORTED with zero actuals. The remaining 12 calls are exactly the three remaining
cells (A1, P0, P1) at 4 each. With the corrected 16-call plan those three can now fly under the same
registration, landing the smoke at exactly 16 with no re-registration and no re-run.

`SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1` stays `consumed = no` until the remaining three cells land.

### 2026-09-04, Phase 2i: the smoke is complete -- 16 of 16 calls, all four cells sealed and scored

`SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1` is `consumed = yes`. Every one of the four cell
configurations ran end to end, sealed a verifiable manifest, finalized and scored with all three
registered scorers. Spend landed at **exactly 16 of 16 registered calls** and 67.792 of 100
registered speech-audio seconds; every attempt on the row is durably FINALIZED or ABORTED and no
llama-server was left resident.

| cell | arm | parse rate | tool acc v1 | tool acc v2 | exact match (v1/v2) | slot F1 (v1/v2) |
|---|---|---:|---:|---:|---:|---:|
| A0'-legacy-raw | `bare-core` | 4/4 | 0.75 | 0.75 | 0.00 / 0.00 | 0.143 / 0.182 |
| A1-native-raw | `bare-core-native-tools` | 3/4 | 0.25 | 0.25 | 0.00 / 0.00 | 0.000 / 0.000 |
| P0-legacy-packets | `speech-feature-query` | 4/4 | 0.75 | 0.75 | 0.00 / 0.00 | 0.154 / 0.200 |
| P1-native-packets | `speech-feature-query-native-tools` | 3/4 | 0.25 | 0.25 | 0.00 / 0.00 | 0.000 / 0.000 |

**These are four-row engineering numbers and enter no verdict.** They exist to prove transport,
sealing and scoring legality. The calibration's own numbers come only from the registered 400-row
flight.

**The native tool-calling contract did NOT come back as native tool calls.** Every cell's cost block
records `tool_calls: 0` and no trace record in any of the four bundles mentions a `tool_calls` field;
A1 and P1 answered in TEXT, and on the first sample the text is a refusal ("I'm sorry, but I can't
engage the lights as requested..."), which the scorer counts as an unparsed row -- hence 3/4 parse
rate and the 0.25 tool accuracy on both native cells. A1 and P1 produced byte-identical response
shapes to each other, so this is a property of the output contract, not of the audio path. Section 1
framed native `tools` as the promising half of Factor A; on four rows it is the WEAKER half, and the
400-row flight now has a specific hypothesis to test rather than an assumption to confirm.

Throughput, measured (A0's own run_phases receipt was lost with the finalizer failure; its cost
block survives):

| cell | wall | contacts/s | mean latency | slot occupancy | prompt tok | completion tok | completion tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| A0'-legacy-raw | -- | -- | 1.634 s | -- | 53,199 | 120 | 18.35 |
| A1-native-raw | 13.455 s | 0.297 | 2.831 s | 0.421 | 55,287 | 143 | 12.63 |
| P0-legacy-packets | 12.665 s | 0.316 | 2.607 s | 0.275 | 53,191 | 114 | 10.93 |
| P1-native-packets | 15.057 s | 0.266 | 3.202 s | 0.284 | 55,279 | 148 | 11.56 |

The native contract costs about 2,090 more prompt tokens per request than the legacy one, consistent
with the prompt-fit measurement (13,914 versus 13,236 text tokens).

Server argv actually used, per geometry, exactly as the fragments declare:

* raw (A0', A1): `-c 49152 -np 2 -fa on -ngl 999 -ctk q8_0 -ctv q8_0`, role `legacy`, model root
  `/home/chao`, 24,576 tokens per slot, ~11.6 s startup.
* packets (P0, P1): `-c 66048 -np 3 -b 2048 -ub 512 -fa on -ngl 999 -ctk q8_0 -ctv q8_0
  --cache-prompt --cache-ram 0 --no-cache-idle-slots --slot-prompt-similarity 0`, role `inference`,
  22,016 tokens per slot, ~10.1 s startup. P1 REUSED P0's resident server (`reused: true`,
  0 s startup), and the queue stopped it at shutdown.

`id_slot` resolved to 0 on every cell; the packet cells promoted and hash-verified 4 packets each and
ran the `direct-speech-feature-packets` dispatch; the raw cells promoted nothing and ran the rails
`direct` dispatch.

Contact-free wire-check receipt for this configuration:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-direct-calibration-400-v1/wire-check/
wire-check-clean-3.json` (SHA-256 f0a573ee3fc4802db865a9ab884469b245e646e5c39a76f8c84273f44cfe7c5c),
green on every link for all four cells with zero model contacts.

Prerequisites 1-4 of section 4 are now closed. The 1,608-call flight has NOT been started.

### 2026-09-04, Phase 3a: recording HOW a response arrived (zero contacts)

Reading the sealed native rows exposed an ambiguity the smoke could not settle. Three of the four
A1/P1 rows are canonical JSON arrays -- which is exactly what `core.model.transport` writes when
llama-server returned `message.tool_calls`, because it canonicalizes native calls into the same
`[{"name": ..., "arguments": {...}}]` text a free-text arm produces (that is what lets one scorer
serve both arms). The adapter parsed only `text`/`usage`/`logprobs` off the envelope and dropped
`tool_calls`, and the trace keeps text plus hashes, so after the fact nobody could tell a native
tool call from JSON the model authored as text. Factor A cannot be read without that distinction.

Closed at the one place that still knows, with no contact and no change to any audited artifact:

- `core.model.request_types.CoreResponse` gains `tool_calls: object = None` -- the RAW list off the
  envelope, still carrying the server's own `function.arguments` JSON string, never the canonical
  form. `None` means the envelope had no `tool_calls` key at all, i.e. the model answered as text.
- `core.model.adapter` reads it beside `logprobs`, in the one place the response envelope is
  parsed. Every existing constructor call keeps working; the response hashes are unchanged, and a
  test asserts that explicitly.
- `rails.core_client.RequestTiming` gains `native_tool_calls: int | None`, set from that raw list,
  and reports it in `as_json()`.
- `FlightRuntime.response_arrival_counts()` aggregates per cell -- rows with native tool calls, rows
  answered as text, total native calls -- into both the `run_phases` receipt and the wire-check
  receipt. An EMPTY tool_calls list counts as a native-arm response, not as text; only a missing key
  is text.
- The wire check's fake transport now imitates exactly one native envelope for a native arm and none
  for a text arm, and the check REFUSES when the accounting does not report precisely that. A count
  that reads the same either way would be worse than none, since the canonical text is identical.

**The sealed contracts are deliberately untouched**: no new outputs field, no trace schema change.
This is provenance for the run receipt only.

Verified contact-free against the real four cells: A0'/P0 report 0 native and 4 text rows, A1/P1
report 1 native and 3 text (matching what the fake transport emitted), 152 tool schemas on both
native arms, zero model contacts.

Phase 3b is the registered 1,608-call flight; `SAEA-A2T-DIRECT-CALIBRATION-V1` remains
`consumed = no`.

### 2026-09-04, Phase 3b-prep: concurrent dispatch against the loaded model (zero contacts)

The owner's standing rule is that GPU calls are batched in parallel against the loaded model; both
fixed-policy branches dispatched one contact at a time, so a 1,608-call flight would have run
strictly serially on a two- or three-slot server. `FlightRuntime` now dispatches concurrently.

- **A worker owns one slot for its whole life.** The pool has exactly `workers` threads and each
  takes one id_slot (`0..workers-1`) once from a free-slot queue and never returns it, so no two
  in-flight requests ever share a llama-server slot. For a one-contact policy that IS slot affinity:
  a sample makes exactly one request, so "a sample's requests share a slot" holds by construction.
- **At most `workers` requests in flight**, because the pool has that many threads. **Queue depth
  is deliberately not a knob** and is documented as such: with one contact per sample nothing queues
  behind a sample, so the only thing a deeper queue could add is more in-flight requests than slots,
  which is exactly what the slot pinning forbids.
- **No batching of samples into one prompt.** One contact per sample, unchanged; the arm under test
  is a one-contact direct baseline and merging prompts would change what is measured.
- **Deterministic order**: samples are handed out in split order and results collected back into it,
  so the sealed outputs rows never depend on completion timing.
- **Thread safety was verified, not assumed.** `rails.core_client.FrozenCoreClient` guards its
  request counter and timings with `_state_lock`, and `core.model.adapter.FrozenCoreAdapter` guards
  its budget check and metering with `_metering_lock` -- both already correct. `core.tracing.
  TraceSink.emit`, however, holds NO lock: it check-then-sets a dict and reopens the trace file per
  record. So each task emits into its own `core.tracing.TraceBuffer` (bound through the per-thread
  contextvar `set_current_trace_buffer`) and the parent flushes them one at a time, in sample order,
  through `flush_trace_buffer`, which serializes on the client's own lock -- the same pattern
  `core.policies.FixedPolicy.run_samples` already uses.
- **A failure aborts cleanly**: remaining work is cancelled and the first exception re-raised, but
  every buffer that did complete is flushed first, so the durable trace keeps what actually
  happened.
- **`workers=1` keeps the serial path**, and the serial raw path still goes through `rails_runner`
  itself, so a `workers=1` flight is byte-identical to the sealed smoke. Default is `workers =
  slots` from the geometry.
- The `run_phases` receipt now carries `dispatch` (workers, max_in_flight, slot_ids_used,
  contacts_per_sample, the queue-depth note), `serving_slots` and `occupancy_slots` beside
  `contacts_per_second` and `slot_occupancy`. **Occupancy is measured against the slots actually
  used**, not the server's slot count: a serial dispatch on a three-slot server occupies one slot,
  and reporting that as a third would understate the very thing the number is for.

Verified contact-free on all four cells through the real client and adapter: raw cells ran 2 workers
using slots [0, 1], packet cells 3 workers using slots [0, 1, 2], `max_in_flight == workers` on every
cell, 4 contacts each, one contact per sample, and the native-versus-text accounting unchanged
(A1/P1 report 1 native and 3 text as the fake transport emitted). Seven new tests pin peak in-flight
<= slots, one-slot-per-worker, sample-ordered results, clean abort with completed traces still
flushed, the `workers=1` serial route, a refused bad worker count, and the occupancy basis.

Phase 3b is the registered 1,608-call flight; `SAEA-A2T-DIRECT-CALIBRATION-V1` remains
`consumed = no`.

### 2026-09-04, Phase 3b: the registered flight flew; no cell passes

`SAEA-A2T-DIRECT-CALIBRATION-V1` is `consumed = yes`. All four cells flew 400 rows, sealed,
finalized and scored; 1,600 of 1,700 registered calls (1,608 planned), 8,638.752 of 9,000 registered
speech-audio seconds, four FINALIZED attempts, none aborted, no recovery re-registration used. The
GPU power limit held at 100.00 W with maximum SM clock 3,090 MHz for the whole flight.

**No cell meets the section 6 acceptance rule**, so section 6's own contingency applies and
mechanism work stays stopped. The full verdict is
`docs/readiness/2026-09-04-a2t-direct-baseline-calibration-v1-verdict.md`; the numbers are
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-direct-calibration-400-v1/result-summary.json`.

Headline: Factor A (the native tool-calling contract) is significant and NEGATIVE for tool accuracy
(-5.75 pp raw, p 0.040; -8.75 pp packets, p 0.0020; both CI90s exclude zero) while trading tiers --
it gains on tier5 and tier6 and collapses on tier3 and tier8. Factor D (mmproj-free packets versus
raw audio) is NULL on every metric, which is the first paired evidence at n=400 that the audio path
is not what separates the September packet-based mechanism runs from A0. Together the two factors
move tool accuracy by at most 8.75 pp against a tier1 gap of 28.4 to 42.4 pp, so the residual gap is
not the request protocol.

Two corrections to earlier readings, both from artifacts this flight produced: native tool calls
arrived on 347 of 400 A1 rows and 346 of 400 P1 rows, so the four-row smoke's "all text" reading was
an artefact of four rows; and the packet path is 56 % faster per contact than raw audio at the
legacy contract, which the smoke was too small to show.

Preregistration section 6 also asks for ORDERED as well as multiset tool accuracy. The registered
`a2t-toolcall` scorer compares tool-name multisets and has no ordered variant, so the ordered column
is reported as not computed rather than invented: adding a scoring rule after the flight would make
the paper-facing number something other than the dataset's standard scorer. That is a gap in this
preregistration, not in the flight.
