# SLURP closed-list direct baseline — preregistration (2026-09-05)

Run id: `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`. Profile: `baseline-reproduction`.
Smoke run id: `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-SMOKE-V1`, same profile, four rows.
Machine-readable contract: `configs/experiment/slurp-dev1000-closed-list-direct-v1.json`.
Authority: the owner directive of 2026-09-04 ("align the basic results first; the axes
that matter are the prompt, the way the model is used, and the scoring script"), the
2026-09-04 scoring-alignment audit `docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md`
section 2.2 ("a closed-label-list arm, to match He & Garner's 60-way classification
protocol"), and the engineering rules in the study `CLAUDE.md` section "Engineering base
and experiment rules (owner, 2026-09-03)".

Status: **REGISTERED — flies after the four-row smoke lands, the exposure row is
written, and the tree is clean and committed.**

## 1. The premise correction this preregistration carries

The directive that opened this mission states that the sealed DEV-1000 M0 prompt "offers
NO label inventory", citing `rails/adapters/slurp.py::_INSTRUCTION`. The audit's own
caveat 4 says the same. **Both are wrong about the flown arm**, and the correction is
load-bearing for what this experiment measures.

`_INSTRUCTION` is half the system message. `rails/runner.py::_agent_messages` appends
`"\n\nTask contract:\n" + SlurpAdapter.build_task_contract(...)`, which is
`render_slurp_ontology(load_slurp_ontology(...))`. All 1,000 sealed `MODEL_REQUEST`
records of `attempt-20260825T053342Z-dev1000m0` carry one identical 5,747-character
instruction (sha256 `cef527896e9beef5774305e01dc29192fc2d5ca89fba5143e82f0b91a7cb86b8`)
whose contract half enumerates **18 scenarios, 46 actions and 55 entity types** with 263
example fillers.

What it never carried is the **pairing**: two flat lists imply 18 x 46 = 828 intents
where only **60** `(scenario, action)` pairs occur in `train`. `SlurpOntology` had no
field for the pairing, so no consumer could have rendered it.

The model-free receipt `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-closed-list-headroom/`
(row `SAEA-SLURP-MF-CLOSED-LIST-HEADROOM-V1`, zero contacts, no gold) measures the
consequence on the sealed predictions themselves:

| arm | scenario outside the 18 | action outside the 46 | pair not in train | entity type outside the 55 |
|---|---|---|---|---|
| DEV-1000 M0 | 8.60 % | 6.90 % | **32.20 %** | 0.28 % of 718 mentions |
| DEV-1000 BLEND | 0.20 % | 0.20 % | **2.10 %** | 0.00 % of 693 |

M0's intent error is 46.40 points; the impossible-pair class is 32.20 of them, about
69 %. This satisfies the owner's "no expansion without visible gains" rule
(`docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md` section 7.3) with
evidence from already-exposed data, and it makes the flown arm **M0's prompt plus the
missing pairing**, not "M0's prompt plus an inventory it never had".

## 2. The arm (one arm, one contact per sample)

Everything below is the sealed DEV-1000 M0 arm's own setting unless the row says
CHANGED.

| axis | value | same as sealed M0? |
|---|---|---|
| population | DEV-1000, all 1,000 devel rows, receipt `docs/receipts/probe-samples/DEV-1000.json`, load-split identity `8580d199…3c84`, receipt integrity `9fb44e33…243b` | same, id-for-id |
| runtime view | `configs/dataset/slurp-speech-native-dev1000.json`, view sha256 `e148dbbc…0e87` | same |
| arm | `speech-feature-query` | same |
| audio path | mmproj-free decode over pre-materialized encoder packets, promotion receipt `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-1000-promotion.json` sha256 `2accbdc5…6a8fe6` | same |
| model | frozen Qwen3-Omni-30B-A3B-Instruct GGUF Q4_K_M, llama.cpp featcache build `04ccc72a` | same |
| geometry | `-np 8`, `-c 65536` (8 slots x 8,192 slot tokens) | same |
| decoding | greedy, `temperature 0`, `seed 20260803`, `max_tokens 64`, per-sample slot affinity | same |
| contacts | 1 per sample, no evidence, no knowledge, no second contact | same |
| **instruction** | the sealed M0 instruction **plus** a 1,836-character closed label inventory | **CHANGED — the only change** |
| harness | `core.flight.FlightRuntime`, `policy: "fixed"` | CHANGED (mechanical) |
| scoring | `slurp-slu-official`, `slurp-slu`, `cost` declared in the manifest, run once over the complete manifest through `core.scoring_batch` | CHANGED (mechanical) |

The two mechanical changes are the durable fix for defect 2 of the 2026-09-04 audit: the
August SLURP flights predate `FlightRuntime.seal` and left no `*.run-manifest.json`, and
their rows carry `final_response_text` where every registered scorer reads `text`. This
is the first SLURP cell flown through `FlightRuntime`; its seal writes the canonical
rows and a real run manifest, so `core.scoring_batch` applies to this carrier without a
key-rename projection.

### 2.1 The prompt, exactly

Resolved through the config, never hard-coded: `configs/baseline/slurp-direct-closed-list.json`
declares `task_instruction_template: "probes/slurp_direct_closed_list.txt"`,
`task_instruction_fill: "slurp-label-inventory"` and
`task_instruction_template_active: true`; the flight script resolves it through
`core.instructions.resolve_active_task_instruction` and hands it to a roster-bound
adapter, because `FlightRuntime` reads its system message from
`adapter.instruction(sample)` and has no config seam of its own.

* template `configs/probes/slurp_direct_closed_list.txt`, 337 bytes, sha256
  `9f2017c1b9a5cbf561a3437377ea4777d418ed19a7607f05e471f71a51dc0413`, pinned in
  `configs/probes/manifest.json` under probe `SLURP-DEV1000-CLOSED-LIST-DIRECT`. Its
  fixed half is `_INSTRUCTION` verbatim plus the same `"Task contract:"` header
  `rails/runner.py` appends.
* fill `slurp-label-inventory` = `data.slurp.render_slurp_closed_label_inventory`,
  registered in `core/instructions.py` beside the two Audio2Tool fills. It renders the
  **unchanged** `render_slurp_ontology` document, one blank line, then
  `render_slurp_label_inventory`.
* rendered instruction: 7,583 characters, sha256
  `4073f79ef25c4796b0a46cb2ac7f5d4982c83084982b87ddd8a70504090d37db`.
* added suffix: 1,836 characters, sha256
  `46ee018e1bd2392c0e3654ddeacf4b7f32209da2a0c00cd7e658afe50ca0dda3`.

The suffix is a header sentence, one line per scenario listing the actions legal under
it (18 lines, 60 pairs), and one line listing the 55 entity types. It carries **no
example fillers, no exemplars, no evidence, no retrieval and no knowledge plane**: this
is the zero-shot direct baseline every mechanism must beat.

`scripts/flights/run_slurp_closed_list_cell.py` refuses to fly unless the first 5,747
characters of the resolved instruction hash to the sealed M0 value and the instruction
is strictly longer — so a prompt rewrite can never be mistaken for a prompt extension.

### 2.2 Why the example fillers stay

M0's contract already carried 263 example filler strings. Rendering the inventory as a
replacement (compact lists only) would have deleted them and changed two things at once.
The registered arm is therefore purely additive, and the 3-point band and the paired
contrast measure the pairing alone.

### 2.3 Gold discipline

The flight process never loads a SLURP gold label. Samples are built from the runtime
view (media identity only); `SlurpSample`'s SLU fields are empty, the adapter's `gold()`
refuses outright, and `score()` is a reference-free stub whose output the seal discards.
`split_id` is `DEV-1000`; `allow_heldout` is never passed; the official scorer refuses
any row whose id names `slurp:test:`. Gold opens once, scoring-side, after the seal.

## 3. Budget and ceilings (row `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`)

`planned_model_calls` 1,050 (1,000 contacts plus margin); `planned_speech_audio_seconds`
3,000 (the roster's own 2,884.7936875 rounded up); `planned_gpu_hours` 1.0. Tool
contacts 0, embedding contacts 0, paid API spend 0. Plan cells are RUN-CUMULATIVE across
every attempt of the run id. One-shot semantics: at most one recovery re-registration,
and a second failure stops the flight.

Smoke row `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-SMOKE-V1`: 12 planned calls, 60 speech
seconds, 0.3 GPU-h, over the four DEV-1000 ids named in
`configs/experiment/slurp-dev1000-closed-list-direct-smoke-v1.json` itself. Its numbers
are a wiring proof and are never reported as a result.

## 4. Exposure

**No new exposure.** These are the same 1,000 `devel` rows the sealed lock arms already
flew, at the same identity hash. The DEV-500 / DEV-1000-NEW500 partition is preserved
for reporting only and is never used to select at flight time. The held-out `test` split
is not named, loaded or scored anywhere in this campaign.

## 5. The read (frozen in advance)

One attempt, one seal, one registered read. Reported whatever the outcome:

1. The full official `evaluate.py` table, micro: scenario / action / intent (scen_act) /
   entities strict / Word-F1 / Char-F1 / SLU-F1, plus n gold, **n predicted**, skipped,
   and unparsed rows. Because `evaluate.py` pairs with `if gold_id in pred_examples`, an
   unanswered gold row never touches TP/FP/FN; the unanswered-counted-wrong variant is
   reported explicitly, equal to the official number only when skipped is zero.
2. The same table for the sealed M0 comparator and the locked BLEND arm, side by side.
3. A paired per-sample contrast against the sealed M0 rows (`analysis.paired`): saves,
   harms, ties, exact sign test, CI90 — on the same 1,000, and separately on the
   unexposed DEV-1000-NEW500.
4. Distance to each published bracket, with the within-3-points rule applied and the
   caveats carried: Google/SF-ID 72.06 intent / 64.02 SLU-F1; Multi-SLURP/HerMiT 78.33 /
   70.84; Gold/HerMiT 84.84 intent; ChatGPT prompt-only on oracle transcripts 79.25
   intent (60 intents listed in the prompt) with a 12.03–13.35 slot F1 that is **not**
   this script's SLU-F1 block. Every published row is the official **test** split and a
   natural mixture; this arm is a scenario-stratified **devel** roster. No like-for-like
   prompt-only official-script SLU-F1 exists for any audio LLM.
5. The post-flight repeat of the headroom read: the impossible-pair rate of the new arm
   beside M0's 32.20 % and BLEND's 2.10 %, which says whether the prompt change did the
   thing it was designed to do independently of whether accuracy moved.
6. How much of BLEND's +22.10 pp intent margin over M0 survives against this arm.

### Decision rule

**The closed-list arm becomes the study's SLURP direct baseline regardless of outcome**,
because it is the protocol-aligned one. There is no pass/fail gate on the headline. Three
named readings follow mechanically from the numbers:

* if the arm lands within 3 points of a published bracket or better, that bracket is
  recorded as aligned for a prompt-only frozen core on devel, with the split caveat;
* if intent rises materially and SLU-F1 does not, the He & Garner asymmetry (intent
  classification survives prompting, slot filling does not) is confirmed on audio input
  and becomes the named target for the evidence-acquisition control plane;
* if BLEND's margin over this arm is small, the locked knowledge cell's SLURP gain is
  restated as substantially a label-inventory effect, and the knowledge plane's claim on
  this carrier is re-scoped accordingly.

No knob is changed and no arm is re-flown on the strength of the number.

## 6. Sequence

1. code, configs, template, probe-manifest entry and tests committed on a clean tree;
2. exposure row for the smoke; `--dry-run` (preflight, then abort; zero contacts);
   `--wire-check` (whole request path, fake gate and transport, zero sockets); four-row
   smoke; smoke row closed;
3. this preregistration committed;
4. exposure row `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` written **before any
   contact**;
5. prompt-fit receipt (tokenizer only, zero tokens generated) at `-np 8`;
6. wire check on the clean committed tree;
7. flight; seal; `core.scoring_batch`;
8. verdict `docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md`
   plus `result-summary.json`; ledger rows closed COMPLETED with hashes; a note appended
   to the 2026-09-04 alignment audit.

GPU preflight before takeoff: enforced power limit >= 95 W (recent flights held 100.00 W)
and an idle card.

## 7. Scope

This registration authorizes the flight, its mechanical landing and its official
scoring. It makes **no** test claim, **no** superiority claim, **no** generalization
claim and **no** Stage-3 claim. The carrier set stays Earnings-21+ConEC, SLURP and
Audio2Tool.
