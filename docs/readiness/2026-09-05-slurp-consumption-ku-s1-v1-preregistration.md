# SLURP consumption cells KU-S1c and KU-S1 — preregistration (2026-09-05)

Program: `docs/readiness/2026-09-05-three-dimension-experiment-program.md`, section 4b (knowledge
consumption). Profile: `bounded-discovery-probe`. Carrier: SLURP. Comparator: the sealed closed-list
direct baseline `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`. Two cells are registered here.

**Status.**

| cell | status | run id |
|---|---|---|
| **KU-S1c** (`phase-draft-revise-v1`, no knowledge, the equal-contact control) | **REGISTERED — flies** | `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` |
| **KU-S1** (BLEND-CL: `phase-direct-evidence-alpha-blend-v1` with `KbFacetProvider` top-5 supply) | **REFUSED BEFORE REGISTRATION** — section 6 | none; no fragment, no exposure row, no attempt |

KU-S1 is refused on a measured, structural blocker in the shared harness, not on a judgment call and
not by relaxing anything. Section 6 carries the measurement, the exact refusing lines and the exact
component that has to change. The KC-S1 verdict's deviation 1 said in writing that "KU-S1 actually
consumes facets and cannot take this way out; it needs its own ruling" — this is that ruling, and it
is that the cell cannot fly on the current base.

## 1. Owner decision in force

The aligned one-contact direct cells are the comparators for every mechanism (owner, 2026-09-05).
The 2026-08-23 alpha-blend two-contact form is re-established as **one consumption cell** against the
closed-list baseline, and stays a consumption reference **only if ADMITTED on the unexposed NEW500**.
KU-S1c is its equal-contact, no-knowledge control. Neither cell draws a new roster and neither adds
exposure: both fly the same 1,000 devel rows the sealed 2026-08-25 lock campaign and the 2026-09-05
closed-list baseline already read.

## 2. The comparator, fixed in advance

`SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, attempt `attempt-20260905T060424Z-2c5596`, run manifest
sha256 `f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c`. Official `evaluate.py`
(pinned commit `8eb16545762be97ace75334109d73824217311f1`, `--average micro`): scenario **81.00**,
action **73.90**, intent (scen_act) **71.40**, entities strict 21.91, Word-F1 33.69, Char-F1 38.20,
SLU-F1 **35.80**; 1,000 gold / 1,000 predicted / 0 skipped / 3 unparsed. One contact per row.

Reported beside it, never as comparators: the sealed DEV-1000 BLEND cell (83.90 / 77.60 / **75.70** /
**41.69**), the sealed DEV-1000 M0 arm (70.00 / 61.50 / 53.60 / 36.90), KC-S1b (81.00 / 73.90 / 71.40
/ 44.35), and the published brackets — Google/SF-ID weakest pipeline intent 72.06 / SLU-F1 64.02 and
Multi-SLURP/HerMiT intent 78.33 / SLU-F1 70.84, both the official **test** split and a natural
mixture. This is a scenario-stratified **dev** roster and no published prompt-only SLU-F1 computed
with this script exists for any audio LLM, so no like-for-like target is available and none is
claimed.

## 3. KU-S1c — the cell that flies

| item | value |
|---|---|
| run id | `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` |
| fragments | `configs/experiment/slurp-consumption-ku-s1c-v1.json`, `configs/baseline/slurp-phase-draft-revise-v1.json`, `configs/policy/phase-draft-revise-v1.json`, `configs/model/q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64.json`, `configs/dataset/slurp-speech-native-dev1000.json` |
| program | `phase-draft-revise-v1`: phase `draft` (knowledge `none`), phase `revise` (knowledge `none`), `max_contacts` 2, stop rule `always-run-full-program` |
| realized contacts | **exactly 2 per row, every row.** `rails.phase_runner.run_program` runs each phase as one blocking whole-roster `max_contacts=1` call, so no row can exit after one contact. Reported from the `run_phases` receipt, not assumed |
| system message | byte-identical to the comparator's: `probes/slurp_direct_closed_list.txt` through the `slurp-label-inventory` fill, 7,583 chars, sha256 `4073f79e…37db`, asserted before takeoff as the sealed M0 instruction (`cef52789…86b8`, 5,747 chars) plus a pure 1,836-char suffix |
| control turn, phase 1 | `probes/slurp_phase_direct.txt`, 262 chars, sha256 `d02f194c…f9d50`, **reused unchanged** from the MF-5 wiring cell |
| control turn, phase 2 | `probes/slurp_phase_revise.txt`, 477 chars, sha256 `236d1ee5…c518`, plus this sample's own phase-1 answer appended under the fixed `Prior phase response` prefix (`predecessor_binding: "append-sealed-state"`) |
| ontology in the control turn | **none.** Both directives defer to "the task contract already given in the system message above" and name no scenario, no action, no entity type and no example filler. This is the KC-S1 leakage finding applied by construction (section 6.4) |
| knowledge | none retrieved, none supplied, none rendered. The snapshot `slurp-kb-size-full-label-prior-speaker` (sha256 `07f94807…fa65`, 349 facets + 11,514 values = 11,863 protected payloads) is bound with empty bootstrap ids solely because `rails.runner.run_speech_native_agent_loop` requires one; what the binding buys is the leakage rule |
| geometry | the `SlurpAdapter` defaults, 8 slots x 8,192 slot tokens, `max_tokens` 64 — i.e. `-np 8 -c 65536`, **the comparator's own geometry**. No override; unlike KC-S1b this cell carries no per-sample block and needs no wider slot |
| decoding | greedy, temperature 0, seed 20260803, per-sample slot affinity; frozen Qwen3-Omni-30B-A3B-Instruct GGUF Q4_K_M on llama.cpp featcache build `04ccc72a`, mmproj-free over the registered DEV-1000 promotion receipt's packets |
| scorers | `["slurp-slu-official", "slurp-slu", "cost"]`, one scoring job per complete manifest through `core.scoring_batch`, never sharded |
| response shape | a full SLU object (scenario, action, entities) on both phases — the same shape the comparator sealed — so the whole official table comes from the sealed rows with **no projection anywhere** |
| tool / embedding contacts | 0 / 0 |

**What the cell is for.** It is the equal-contact reference every two-contact SLURP cell's delta is
stated net of (the program's contact-accounting rule). On its own it answers one question the slot
cells could not: KC-S1a held intent **identical by construction** (it was forbidden to revise the
sealed intent), so nothing in this study yet measures whether a second look at the same audio, with
the same information and no new knowledge, moves the **intent** layer at all. KU-S1c measures exactly
that, on every layer of the official table.

## 4. Roster, populations and exposure

The whole frozen DEV-1000 runtime view, id for id, split identity hash
`8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`, receipt
`docs/receipts/probe-samples/DEV-1000.json`. No new draw, no new exposure. Inherited exposure: the
DEV-100 campaign rounds 0–5, K-WIDEN K1, A4, the DEV-500 confirmatory campaign, the DEV-1000 baseline
lock, `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, `SAEA-SLURP-KC-S1A-…` and `SAEA-SLURP-KC-S1B-…`.

| population | n | receipt | role |
|---|---|---|---|
| DEV-1000-NEW500 (unexposed at the lock tier) | 500 | `docs/receipts/probe-samples/DEV-1000-NEW500.json` | the decision population for any cell this control serves; reported first |
| DEV-1000 (pooled) | 1000 | `docs/receipts/probe-samples/DEV-1000.json` | reported |
| DEV-500 (prior-exposed) | 500 | `docs/receipts/probe-samples/DEV-500.json` | reported separately, never pooled into a decision |

Gold never enters the flight process: samples are built label-free from the runtime view and the
adapter's `gold()` refuses outright. Gold opens once, scoring-side, at the single registered read.
The held-out test split is never named, loaded or scored.

## 5. Analysis and decision rule (frozen before the read)

`analysis.paired.paired_contrast`, delta = arm minus comparator on per-sample official scores,
stratified bootstrap **N = 10,000**, strata = the gold scenario, **seed 20260903**, **CI90**, exact
sign test. Metrics: intent (scen_act), scenario, action, per-sample slot F1 (exact type+filler),
per-sample SLU-F1, slot precision, slot recall. Both weightings reported: natural mixture and
equal-stratum. Per-stratum table with the published column beside it. Realized contacts per row and
**gain per extra contact** for every two-contact arm.

* **KU-S1c is REPORTED, NEVER DECIDED.** It carries no admission gate of its own; the program's own
  words. Its numbers are the equal-contact reference, and every later two-contact SLURP cell states
  its delta net of it.
* **KU-S1, had it flown**, would have been **ADMITTED** iff its intent CI90 lower bound is above 0
  against the closed-list baseline on NEW500 **and** its delta net of KU-S1c keeps a lower bound
  above 0; **NULL** if either includes 0 — in which case the direct form stays the reference and
  retrieval on SLURP is re-scoped to slots with KC-S1b as the base; **HARMFUL** if the upper bound is
  below 0. This rule is registered and stays on the books unchanged for the day the enabler in
  section 6.5 lands. **It is not applied to anything in this flight**: an unflown cell is neither
  ADMITTED nor NULL nor HARMFUL, it is unread, and no statement about alpha-blend's value under the
  closed-list instruction may be drawn from this flight in either direction.

## 6. KU-S1 — refused before registration, with the measurement

Analysis receipt: `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-consumption-ku-s1-v1/containment-analysis.json`.
Zero model, GPU, tool, embedding, network, audio and gold contacts; it reads two frozen snapshots, the
two committed control-turn templates and the sealed closed-list outputs, and nothing else.

### 6.1 What the cell needed

`phase-direct-evidence-alpha-blend-v1` (direct, then evidence) through the shared
`core.flight.FlightRuntime`, with `KbFacetProvider` supplying the top 5 facets per row from the frozen
TRAIN snapshot `slurp-kb-size-full` (all four dimensions — **the BLEND lock's own substrate**), ranker
`saea-rank-wcos-prior-agree-v1`, fuser `saea-fuse-supplyfilter-v1`, knobs alpha 0.45 / tau 0.65 / k 5,
and the closed-list instruction in place of M0's in both phases.

### 6.2 The base has no seam that can supply it

`core/flight/runtime.py:2501` — `_default_phase_program_binding`, the config-native path every phase
cell uses, returns `"supply_for_phase": None`, unconditionally. A phase program flown from config
alone can never supply knowledge; there is no `configs/` key that resolves a `KnowledgeProvider`, and
`supply_for_phase` has no caller anywhere in `src/` or `scripts/`. The only alternative is the
launcher-side `bind_phase_program_material(supply_for_phase=...)` override — and section 6.3 shows it
does not help.

### 6.3 The containment rule refuses the supply itself, on 100 % of rows

`rails/controllers.py:405–412` — `EvidenceAgentController._dispatch` folds a `SupplyPacket` into the
phase's own text: `instruction = f"{instruction}\n\nSupplied evidence:\n{supply.prompt_block}"`.
`rails/runner.py:355` — `_assert_agent_control_excludes_knowledge_payloads(contact, protected_material)`
reads exactly `plan.instruction`, and is called on every contact of both dispatch paths
(`runner.py:1198`, `runner.py:1384`). `protected_material` is every facet representation and every
value content of the bound snapshot whose stripped length is at least 8 characters
(`runner.py:334`). A `KbFacetProvider.materialize` packet is rendered from `KnowledgeValue.content`
**verbatim** (`knowledge_provider.py::_render_kb_supply_packet` / `runner.py::_supply_for_state`).

Measured, on `slurp-kb-size-full`:

| quantity | value |
|---|---|
| protected payloads | **23,267** (11,753 facet representations + 11,514 value contents at ≥ 8 chars) |
| values at or over 8 characters | **11,514 of 11,514 — 100 %** |
| a top-5 supply block | 3,224 characters carrying **19** distinct protected payloads |
| control turns refused | **every dispatched row, without exception** |

Every supplied value is, by construction, a payload the rule forbids on the control turn. This is not
a tunable rate: it is 100 %, and it is 100 % under any snapshot, because supply *is* protected
material. Relaxing the rule was the only way through, and the brief forbids it — correctly: the rule
exists to stop control text bypassing traced supply, which is exactly what folding a fused evidence
packet into a phase instruction does.

### 6.4 The substrate the cell needs also refuses 7.8 % of its own phase-2 control turns

Independently of the supply, the content dimension `KbFacetProvider` retrieves over carries one facet
per TRAIN utterance, and SLURP has one- and two-word utterances. Measured on the exact bytes phase 2
would send — the committed `revise` directive plus a sealed closed-list response appended under the
`Prior phase response` prefix, all 1,000 rows:

| bound snapshot | dimensions | protected payloads | phase-2 control turns refused | static directives refused |
|---|---|---|---|---|
| `slurp-kb-size-full` (`e27b2745…a51b57`) | content, label, prior, speaker | 23,267 | **78 of 1,000 (7.8 %)** | 0 of 2 |
| `slurp-kb-size-full-label-prior-speaker` (`07f94807…9ffa65`) | label, prior, speaker | 11,863 | **0 of 1,000** | 0 of 2 |

The 78 offending payloads: `calendar` 57, `shopping` 7, `politics` 4, `change song` 2,
`next episode` 2, `to do list` 2, `clothing` 1, `donald trump` 1, `jane doe` 1, `new york time` 1.
Every colliding sample id is listed in the receipt. This replicates the KC-S1 deviation-1 measurement
on this cell's own bytes: binding `size-full` here would have killed the flight mid-roster on about
one row in thirteen, after part of the budget was gone. KU-S1c takes the way out KC-S1a/b took
(drop the content dimension, which `KnowledgeBuildSpec.validate` explicitly allows); **KU-S1 cannot**,
because the content dimension is what it retrieves over.

### 6.5 The one legal channel, and the enabler that would open it

Traced supply already exists and already works: `rails/runner.py::_agent_messages` renders every
facet named by `QueryState.visible_facet_ids` and every value named by
`QueryState.retrieved_value_ids` as typed `text` content blocks in the **user** message, each carrying
`evidence_id`, `source_uri` and `knowledge_role`, and `rails.knowledge.assert_knowledge_use_binding`
validates the `RankResult`/`FusionDecision` that put them there. The containment rule does not read
that channel, precisely because that channel is traced.

`EvidenceAgentController` cannot reach it: every transition it emits is `action_kind="organize"` with
empty `new_value_ids`, and it never advances `retrieved_value_ids`
(`rails/controllers.py:495–520`). The one controller that does reach it is
`rails.kb_policy.KbAlphaBlendController` — and `FlightRuntime.run_phases` cannot dispatch it, because
`policy` is either `"fixed"` or a phase-program id resolved through
`rails.controllers.default_phase_program`. Reviving the pre-`FlightRuntime` launcher that flew the
sealed lock is not an option either: that is exactly the path the 2026-09-04 scoring-alignment audit
found sealing no run manifest, and the owner's "same harness for every arm" rule forbids it.

**The fix, recorded and not done here** (a new enabler, its own tests, its own registration): give
`EvidenceAgentController` a supply path that emits an `acquire` transition with its `RankResult` and
`FusionDecision` and advances the successor `QueryState`'s `retrieved_value_ids`, so a `SupplyPacket`
travels the typed-content channel instead of the instruction; and add the config seam that lets
`_default_phase_program_binding` build a real `supply_for_phase` from a `core.base`-registered
provider id. Until that lands, **no knowledge-supplying phase cell can fly on this base** — that is
KU-S1, KU-S2 and KU-A1 as well, not KU-S1 alone, and it is the single highest-value engineering item
the consumption dimension has.

### 6.6 What this refusal does and does not claim

It claims nothing about alpha-blend. It does not say retrieval fails on SLURP, does not say the
closed-list instruction defeats it, and does not convert to a NULL. The cell is **unread**. The
program's fixed points are unchanged: the sealed BLEND arm stays a reference, not a comparator, and
the one-contact closed-list direct arm stays the SLURP comparator.

## 7. Budget and ceilings

Run-cumulative across every attempt of each run id, enforced by `core.model.adapter` against a fresh
sibling read of durable attempt actuals. At most **one** recovery re-registration per run id; a
second failure stops the flight and the fix is proven on a 4-row dry run.

| run id | calls (registered ceiling) | speech seconds (ceiling) | GPU-h (ceiling) | tool | embedding | paid |
|---|---|---|---|---|---|---|
| `SAEA-SLURP-KU-S1C-PROMPT-FIT-V1` | 0 generated (4) | 0 (60) | ~0.05 (0.3) | 0 | 0 | 0 |
| `SAEA-SLURP-KU-S1C-SMOKE-4-V1` | 8 (24) | 30.022 (120) | ~0.05 (0.3) | 0 | 0 | 0 |
| `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` | 2,000 + 8 canaries (2,100) | 5,769.5874 (6,000) | ~0.3 (1.0) | 0 | 0 | 0 |
| KU-S1 | **not registered — 0** | 0 | 0 | 0 | 0 | 0 |

The roster's own audio is 2,884.7937 s and KU-S1c makes two passes over it. Paid API spend is 0 and
stays 0.

## 8. Takeoff sequence and the gates each step must pass

1. **Containment analysis** (model-free, zero contacts) — section 6; must show 0 static control-turn
   collisions and 0 phase-2 control-turn collisions under the bound snapshot. **Done, both zero.**
2. **Exposure rows written** for every run id above, before any contact.
3. **`pytest` green** except the documented pre-existing failures, `python scripts/checks/engineering_base_check.py` PASS, ruff clean.
4. **Dry run** (`--dry-run`): preflight only, no server, no contact.
5. **Wire check** (`--wire-check`) on a clean committed tree: the whole request path against a fake
   gate and a fake transport, zero sockets and zero model contacts; the seal-and-score step must not
   be REFUSED.
6. **Prompt fit**, zero generated tokens, through the resident server's `/apply-template` +
   `/tokenize`: both phases, all 1,000 rows, worst envelope reported against the 8,192-token slot.
   A negative margin STOPS the mission. `FlightRuntime`'s own pre-flight budget estimator does not
   count these prompts (KC-S1 deviation 3: `_phase_prompt_payloads` pads the predecessor state with
   a fixed 256 characters and `rails.context_budget`'s `PER_SLOT_LIMIT_TOKENS` is 32,768 rather than
   the physical `-c / -np`), so its ALLOW is not evidence for this cell.
7. **4-row smoke** on the four DEV-1000 rows the fragment itself names, against the section-8 gate in
   `configs/experiment/slurp-consumption-ku-s1c-smoke-4-v1.json`. Its eight responses are a wiring
   proof and enter no verdict.
8. **Flight**, one attempt, one seal.
9. **`core.scoring_batch`**, one job per complete manifest, never sharded, with the official-vs-port
   identity check.
10. **One registered read**, then the verdict
    `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-verdict.md` and its `result-summary.json`.

## 9. What this authorizes, and what it forbids

Authorizes: the KU-S1c flight above and its single read. Forbids, as always: any test contact, any
superiority claim, any generalization claim, any Stage-3 or paper-scale activity, any knob change or
re-fly on the strength of a number, and any statement about KU-S1's mechanism drawn from a cell that
was never flown. Under the claim ladder nothing here reaches even rung 1, because KU-S1c has no
admission gate: it is a control, and its value is that later cells can be stated net of it.
