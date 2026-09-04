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
| A0' legacy x raw | `bare-core` | raw audio, mmproj loaded | `configs/probes/r1_audio2tool_direct.txt` (13k-token registry text) | new raw-audio Q4_K_M fragment on build 04ccc72a (inference receipt with mmproj; `-c 49152 -np 4` as A0) | A0's |
| A1 native x raw | `bare-core-native-tools` | raw audio, mmproj loaded | `configs/probes/r1_audio2tool_direct_native_tools.txt` plus `tools` | same as A0' | A0's |
| P0 legacy x packets | `speech-feature-query` | mmproj-free packets | legacy registry text | `configs/model/q4km-mmproj-free-speech-native-np2-a2t-max1024.json` | section 8.1: `-c 65536 -np 2` |
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
