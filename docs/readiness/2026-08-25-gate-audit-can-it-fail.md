# GATE AUDIT — CAN IT FAIL? Every gate a landed conclusion rests on, mutated

Date: 2026-08-25. Status: **DIAGNOSIS — computed, ZERO CONTACTS, 0 outbound connection attempts
against zero targets.** Row `SAEA-SN-MF-GATE-AUDIT-CAN-IT-FAIL` (registered `fc278296`, BEFORE any
computation). Receipt
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-gate-audit/gate-audit-report.json`
(sha256 `c850ace8e025071658201c3bc57f39741b8282f230fc0614f9dae9957516f8f3`), which carries every
mutation, its expected and observed outcome, and the raw measurements each battery produced.

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 HTTP or socket
requests, 0 audio seconds, 0.0 GPU hours, 0 new dependencies.**
`analysis.dev100_reviewer_audit.arm_offline_guard()` was armed before the first input was opened in
every one of the thirteen processes this audit ran, and every process that reached its own report
line recorded **0 outbound connection attempts against zero targets**. The resident np8
llama-server (pid 38623, port 8090) was not contacted, probed, reconfigured or stopped.

**This row DIAGNOSES. It changes no knob and repairs nothing.** Every mutation below was temporary
and reverted; the working tree was verified clean before and after. A fix to anything found here is
a separately registered step.

---

## 1. The one-line answer

**Of the 43 gates in scope, 23 FIRE, 10 CANNOT FAIL, 9 are NARROWER THAN THEIR CLAIM, and 1 is
UNTESTED.** The hard evidence chain the landed conclusions actually stand on — the SHA-256 pins on
every sealed input, the arm cross-checks, the population algebra, the exposure pre-registration
cross-check, the execution-scope guard, the two knowledge-binding assertions, the replay fidelity
gate five reads quote as their stop condition, and both landed decision rules (the DEV-1000 LOCK
CONDITION and the DEV-500 claim condition) — **all fire, in both directions, on every mutation
constructed for them.** No landed number changes.

What does not fire is a second tier of gates that are *reassuring rather than load-bearing*, and the
recurring shape is the one the intent-coverage case already named: **a denominator, roster or window
that the code immediately upstream has already made trivially satisfiable.**

The four findings that were not already on record are:

1. **The A2T coverage report has the same self-fulfilling shape as the SLURP one, across six
   metrics rather than one, and its `tool_coverage` denominator additionally misses a real gap:**
   152 registry tools, 151 in the construction pool, `tool_coverage` = 1.0.
2. **Both KB-BUILD decontamination gates cannot fail on the landed path.** SLURP's TRAIN id
   universe and its forbidden roster are disjoint by namespace (measured intersection: 0 of
   50,628 × 21,768); A2T's construction pool is the set difference the gate then checks (measured
   intersection: 0 of 22,951 × 800).
3. **The decode-rate sentinel tolerates up to 3 of 8 arbitrarily slow contacts** before its rolling
   median crosses the abort bar, and **the byte-compare canary's cross-attempt leg is not a stop
   condition** — a divergence is logged as a caveat and the arm flies.
4. **The damage-channel analysis publishes two gates and enforces one.** Its readiness document
   says "*Both gates pass with zero mismatches*"; forcing `winner_gate_passed` to `False` lets
   `analyse()` run to completion and publish `winner_gate_passed: false` in its own report, while
   forcing `supply_gate_passed` to `False` raises and voids the analysis. Both were in fact 100/100
   on the landed data, so nothing is wrong — but only one of the two is fail-closed.

---

## 2. Method — mutation, not reading

For each gate: construct an input (or, where the gate is a threshold, a statistic) that SHOULD make
it fail, run it, and record whether it actually failed. A gate that was only read is recorded
UNTESTED, never as passing. **140 mutations and controls were recorded across thirteen offline
processes; 112 are live and 28 are marked superseded in the receipt** — a superseded row is one
whose mutation raised for a reason other than the gate (a malformed constructor call) or was masked
by an earlier clause (a budget mutation against a `consumed = yes` row), and each names the battery
that replaced it. The live tally is **69 FIRES, 20 controls that correctly did not fire, and 23
DID-NOT-FIRE**. Where a live mutation was impractical (a gate that only exists mid-flight) the
smallest faithful reproduction was built and is labelled **REPRODUCTION** in the table below rather
than passed off as the live gate.

Classification, exactly one per gate:

- **FIRES** — a mutation in its declared domain made it fail, as designed.
- **CANNOT FAIL** — no mutation in its declared domain can make it fail: a constant, a
  self-fulfilling denominator, a dominated branch, or a domain that excludes the failure it names.
- **NARROWER THAN ITS CLAIM** — it fires on some of what it claims to protect but not all.
- **UNTESTED** — no mutation could be constructed; what would be needed is stated.

Mutations were made to **inputs and to in-memory pins**, never to sealed bytes on `E:` and never to
a committed artifact. The three sealed attempt stores, the pinned snapshots and every committed
receipt are byte-unchanged.

---

## 3. The table

### 3.1 Knowledge builders — the coverage and decontamination figures in `docs/receipts/knowledge/*.json`

| # | Gate | Mutation run | Observed | Class |
|---|---|---|---|---|
| 1 | SLURP KB-BUILD decontamination (`knowledge_build.build_knowledge_snapshot`: `selected_sample_ids & forbidden`) | (a) build the landed full-size snapshot against the roster loaded from disk; (b) inject one real selected TRAIN id into the roster; (c) measure the intersection of the whole TRAIN id universe with the real roster | (a) clean, `slurp-kb-distmodel-76e61b0666162aa7`; (b) **RAISES**, so the mechanism is live; (c) **0** — 50,628 `slurp:train:*` ids vs 21,768 `slurp:devel:*`/test ids | **CANNOT FAIL** |
| 2 | A2T KB-BUILD decontamination (`knowledge_build_a2t`, same shape) | same three, over the real partition (`items_construction` = 22,951, forbidden = 800) | (a) clean; (b) **RAISES**; (c) **0** — `propose_partition` built the construction pool by removing exactly the eval and exposed blocks one line earlier | **CANNOT FAIL** |
| 3 | A2T decontamination empty-roster clause | pass `forbidden_sample_ids=frozenset()` | **RAISES** ("refusing to build with an EMPTY decontamination roster") | **FIRES** |
| 4 | `decontamination.verdict` in both build receipts | read the two receipt writers | the string `"clean"` is a Python literal in `scripts/build_knowledge_snapshot.py:153` and `scripts/build_a2t_knowledge_snapshot.py:217`; it has no other reachable value | **CANNOT FAIL** |
| 5 | SLURP `intent_coverage`, `scenario_coverage`, `action_coverage`, `entity_type_coverage`, `long_tail_coverage.*` | sweep `datastore_size` ∈ {1, 60, 100, 1000, full} × `seed` ∈ {20260823, 1, 7} | **1.0 in every one of the ten cells.** At `datastore_size=1` the stratified sampler still returns 90 utterances covering all 60 intents; the size argument is a floor, not a cap | **CANNOT FAIL** |
| 6 | A2T `tool_coverage`, `tier_coverage`, `category_coverage`, `argument_key_coverage`, `argument_pattern_family_coverage`, `long_tail_coverage.*` | sweep `datastore_size` ∈ {100, 1000, 5000, full} | **1.0 in every cell** | **CANNOT FAIL** |
| 7 | A2T `tool_coverage` denominator vs the task target space | compare the denominator (construction-pool tools) with the frozen tool registry the core may call | registry **152**, pool **151**; `getLockStatus` is modelled by no facet while `tool_coverage` reads 1.0 | **NARROWER THAN ITS CLAIM** |
| 8 | SLURP `intent_coverage` denominator vs the task target space | compare TRAIN row intents with the DEVEL label space the study is scored on | TRAIN **60**, DEVEL **59**, DEVEL-not-in-TRAIN = **∅**; the denominator is a strict superset today, so the wrong denominator is currently harmless | **NARROWER THAN ITS CLAIM** |
| 9 | SLURP `cluster_coverage_proxy`, `kl_selected_given_train_over_intent` | same sweep as #5 | **vary**: 0.0195 → 1.0 and 0.0 → 0.00304. These two metrics are informative | **FIRES** |

### 3.2 Fail-closed assertions in `contracts/` and `rails/`

| # | Gate | Mutation run | Observed | Class |
|---|---|---|---|---|
| 10 | `contracts.plan.assert_execution_scope` | `'paper-scale-confirmatory'`; `'PAPER-SCALE-CONFIRMATORY'`; `'large-scale-evaluation'`; `''` | **RAISES on all four** | **FIRES** |
| 11 | `ExecutionPlan.validate` split-role clause | `split_role='confirmatory'`; `'test'` | **RAISES on both** | **FIRES** |
| 12 | `ExecutionPlan.validate` identifier clause | `run_id='../escape'`; `planned_model_calls=0` | **RAISES on both** | **FIRES** |
| 13 | `ExecutionPlan.validate` budget MAGNITUDE | `planned_model_calls=10⁹`, `planned_gpu_hours=1e9`, `planned_speech_audio_seconds=10¹²` | **accepted** — the slice-wide caps were retired by the 2026-08-06 owner amendment, so magnitude is no longer a refusal reason here | **CANNOT FAIL** (by design) |
| 14 | `gate_exposure._require_exposure_preregistration` per-row `registered ≥ planned` | +1 on each of calls / audio-seconds / gpu-hours against the unconsumed row `SAEA-DEV100-RETAIN-OVERRIDE` (300 / 900 / 0.4); and the exact-budget boundary | **RAISES on all three**; the exact-budget plan is accepted (`≥`, as specified) | **FIRES** |
| 15 | ... profile / split-identity / carrier / unregistered-run / consumed clauses | five separate mutations | **RAISES on all five** | **FIRES** |
| 16 | `gate_exposure._resolve_carrier_dataset_entry` | carrier = the model lock key `qwen3-omni-30b-a3b-instruct-gguf`; carrier = the general-audio asset `fsd50k` | **RAISES on both** | **FIRES** |
| 17 | `rails.knowledge.assert_knowledge_use_binding` | query id inside the TRAIN roster; foreign `RankResult.snapshot_sha256`; value outside the snapshot; supporting facet absent from the `RankResult` | **RAISES on all four** | **FIRES** |
| 18 | `assert_knowledge_use_binding` caller-supplied `snapshot_sha256` passthrough | a CONSISTENT lie: `'c'*64` in the `RankResult`, the `FusionDecision` and the passthrough argument, with the real snapshot unrelated | **NO RAISE** — the docstring states the passthrough is format-checked, never recomputed. Not reachable on the live path: `run_speech_native_agent_loop` computes `snapshot.content_hash()` itself and threads it down | **NARROWER THAN ITS CLAIM** |
| 19 | `rails.knowledge.assert_agent_step_binding` | successor `loop_step=5`; swapped `speech_packet_sha256`; value outside the snapshot; prior query id inside the TRAIN roster; an already-visible value claimed as new SUPPLY | **RAISES on all five** | **FIRES** |
| 20 | CONTROL-text payload guard `rails.runner._assert_agent_control_excludes_knowledge_payloads` | nine mutations, listed in §4 | **fires on 2 of 9**: the verbatim payload and the case-folded payload. It misses a one-character edit, whitespace reflow, a newline split, the `task_target` string, payloads under 8 characters, and the payload relocated to `purpose`, `key_representation_id` or `decoding_params` | **NARROWER THAN ITS CLAIM** |
| 21 | `assert_prior_scores_are_probabilities` (construction) and `KnowledgeSnapshot.frozen_json` (write) | `prior_score=4.1`; `prior_score=-0.01`; re-freeze a loaded historical snapshot carrying 4.1 | **RAISES on all three** | **FIRES** |
| 22 | `KnowledgeSnapshot.from_frozen_json` prior-score range (load) and `ValueBundle.validate` | load / validate a value carrying `prior_score=4.1` | **NO RAISE** — accepted, `RuntimeWarning` emitted, violation recorded as `(('v1', 4.1),)`. Deliberate and documented: refusing historical bytes would break every landed replay | **CANNOT FAIL** (by design) |
| 23 | `core.split_receipt.verify_receipt_document` | drop one id leaving `count` declared; replace an `identity_hash` with `0*64`; insert a foreign-carrier id; insert a DEV id into the CONFIRMATORY split with `count` AND `identity_hash` correctly recomputed so every earlier clause passes | **RAISES on all four**, the last one naming the same-carrier disjointness violation | **FIRES** |

### 3.3 Campaign launcher flight guards

| # | Gate | Mutation run | Observed | Class |
|---|---|---|---|---|
| 24 | `SidecarCoResidencyGuard`, sidecar-handle leg (A2T G1 attempt 4) | ARMED, the launcher's own handle reports live | **RAISES `CoResidencyViolation`** | **FIRES** |
| 25 | `SidecarCoResidencyGuard`, embedder-port leg | ARMED, handle dead but the port probes reachable | **RAISES** | **FIRES** |
| 26 | `SidecarCoResidencyGuard` TCP probe leg (`_port_reachable`) under an OS error | inject `OSError(EACCES)` into `socket.create_connection` (no socket opened) | **returns `reachable=False`** — `except OSError: return False` reports an UNDETERMINABLE port as CLEAR. The leg fails OPEN; leg 1 is unaffected | **NARROWER THAN ITS CLAIM** |
| 27 | `SidecarCoResidencyGuard` unarmed / disarmed windows | both legs hot while unarmed, and again while disarmed for the offline bridge | **NO RAISE in either window** — declared behaviour (`if not self._armed: return`); the bridge is exactly the window in which the sidecar is supposed to be up | **CANNOT FAIL** (by design) |
| 28 | `DecodeRateSentinel` abort | 8 of 8 contacts at 5,137 ms/token (the attempt-2 state) | **RAISES `DecodeRateSentinelTrip`** at rolling median 5,137 | **FIRES** |
| 29 | `DecodeRateSentinel` median blind spot | 1, 2, 3 and 4 of 8 contacts at 1,000,000 ms/token, the rest at 30 | **does not trip at 1, 2 or 3 of 8**; trips at 4 of 8. Up to three arbitrarily slow contacts per window are invisible | **NARROWER THAN ITS CLAIM** |
| 30 | Decode-speed canary threshold — **REPRODUCTION** of the live clause over the launcher's own constants | worst rate 997 ms/token; worst rate exactly 300.0 (strict `<`); one timing row for two contacts | **RAISES on all three**; 45 ms/token passes | **FIRES** |
| 31 | Byte-compare canary, CROSS-ATTEMPT leg | read the live branch taken when the canary responses differ from the attempt-1 M0 hashes | **not a stop**: the branch logs, re-runs the pair once, records `decode_divergence` as a caveat and flies. Only a WITHIN-build divergence raises `CanaryFail` | **NARROWER THAN ITS CLAIM** |
| 32 | Byte-compare canary, WITHIN-BUILD leg | — | no mutation could be constructed offline: it compares two live decode passes on the same binary, which requires a model contact this row may not take | **UNTESTED** |

### 3.4 Landed reads — pins, cross-checks and pre-registered decision rules

| # | Gate | Mutation run | Observed | Class |
|---|---|---|---|---|
| 33 | `dev1000_lock_read` sealed-input SHA-256 pins | replace, one at a time, the M0 `outputs_sha256`, `report_sha256`, `mechanical_sha256` and the DEV-1000 receipt file hash with `0*64`; change `expected_samples` 1000→999; change the receipt `run_identity_hash`; change `n_items` 1000→999 | **RAISES on all seven** | **FIRES** |
| 34 | `dev1000_lock_read.load_arm` mechanical cross-check | increment `two_contact_trajectories_dispatched`, then `one_contact_trajectories_retained_primary`, in the committed report as it is parsed | **RAISES on both** ("dispatched count disagrees with the committed report") | **FIRES** |
| 35 | `dev1000_lock_read` A4-lesson empty-intersection guard | enumerate every `(dev500, dev1000)` shape the line can be reached with: disjoint, empty-dev500, nested | the disjoint shape (what A4 actually produced) is caught by the **subset check on the preceding line**, so the A4 line is never reached; the only shape that trips the A4 line is an EMPTY DEV-500, which the `n_items = 500` assertion upstream already excludes | **CANNOT FAIL** |
| 36 | **DEV-1000 LOCK CONDITION** | run the live read three times with the PRIMARY bootstrap's `ci90_low_pp` forced to +5.000, −1.000 and +9.999 pp | **LOCKED → CONFIRMED-BUT-SHRUNKEN, NOT-CONFIRMED, CONFIRMED-BUT-SHRUNKEN**; `lock_condition_met=False` in all three. The unmutated re-read reproduces the landed verdict exactly: LOCKED, +20.20 pp, CI90 [+17.20, +23.40] | **FIRES** |
| 37 | LOCK CONDITION, wrong-direction and null | feed the rule a null effect and a −40 pp regression on 500 synthetic paired samples | **NOT-CONFIRMED in both** | **FIRES** |
| 38 | **DEV-500 claim condition** (`ci90_excludes_zero`) | feed it a −40 pp regression | **NOT MET**, CI90 [−43.60, −36.40]. The field is *named* `ci90_excludes_zero` but computes `ci_low > 0`, i.e. one-sided positive — which is the safe direction for a claim, though the name is not literally true | **FIRES** |
| 39 | `cross_carrier_ceiling_decomposition.fidelity_gate` — the stop condition the A2T gold-absence diagnosis, the cross-carrier decomposition, the query-key degeneracy read, the oracle-query bound and the prior-score repair all quote | four mutations of a faithful synthetic replay: a dispatched trajectory's replayed supply selects a different value; a retained trajectory is flipped to dispatched; a direct-label recovery flag is flipped; a retained trajectory carries a non-null flown supply | **`gate_passed=False` on all four**, each naming the offending sample id; the faithful control reports 3/3, 3/3, 3/3. Every one of the five consumers raises on `not gate_passed` | **FIRES** |
| 40 | `dev100_damage_channel_analysis.supply_gate_passed` | force `fidelity_report` to report `supply_gate_passed = False` and run the live `analyse()` | **RAISES `AnalysisError`** ("supply replay does not reproduce the flown SUPPLY trace; the analysis is void") | **FIRES** |
| 41 | `dev100_damage_channel_analysis.winner_gate_passed` | force `fidelity_report` to report `winner_gate_passed = False` and run the live `analyse()` | **`analyse()` COMPLETED** and published `{"supply_gate_passed": true, "winner_gate_passed": false}`. No consumer reads it: `analyse()` checks only `supply_gate_passed`. The unmutated control reports 100/100 on both | **CANNOT FAIL** (as a stop condition) |

### 3.5 Pre-registered falsifiers quoted in landed readiness documents

| # | Falsifier | How it was assessed | Class |
|---|---|---|---|
| 42 | The K1 key-plane falsifier — *"if hybrid ranking does not raise recall@5, key representation is not the lever either"* | not mutated; established from the landed documents. It **did not fire** (recall@5 rose +1.8 pp) and the recommendation is still DO NOT FLY for three reasons the falsifier did not name — recall@1 falls 4.6 pp, the conversion anchors price the trade badly, and the supply-level projection is negative on all four populations. Already recorded in `docs/readiness/2026-08-25-key-construction-agenda-plan.md` §6 | **NARROWER THAN ITS CLAIM** (already on record) |
| 43 | The δ ≥ 0.14 retain-override's registered property — *"zero loss by construction"* | not mutated; established from the landed lock verdict §3. The property held on **every population it was fit on** (DEV-100 r4/r5, DEV-500 NEW400, A4) and failed the first time it met unexposed data (3 fires, 0 recovered, 3 damaged). A property verified only on its own fit data cannot fail there | **NARROWER THAN ITS CLAIM** (already on record; the ladder's unexposed tier is what caught it) |

---

## 4. The CONTROL-text payload guard, in full

The guard is one line: `if any(material in plan.instruction.casefold() for material in
protected_material)`, where `protected_material` is every facet representation and every value
content of the frozen snapshot, casefolded and stripped, **filtered to items of at least 8
characters**. Nine mutations against a snapshot whose one value content is
`"Choose the dim-light route when the requested operation reduces brightness."`:

| mutation | fires? |
|---|---|
| instruction embeds the full value content verbatim | **yes** |
| instruction embeds a facet representation verbatim | **yes** |
| instruction embeds the value content in UPPER CASE | **yes** (the guard casefolds) |
| instruction embeds the value content with one trailing character deleted | no |
| instruction embeds the value content with internal spaces doubled | no |
| instruction embeds the value content split by a newline at the midpoint | no |
| instruction embeds the value content with every space replaced by a newline | no |
| instruction embeds only the value's `task_target` (`hue_lightdim`, 12 characters) | no |
| the value content is `"dim"` (3 characters) and the instruction embeds it verbatim | no — the 8-character filter drops it from `protected_material` entirely |
| the payload is placed in `AgentContactPlan.purpose` / `.key_representation_id` / `.decoding_params` instead of `.instruction` | no — the guard reads `plan.instruction` only |

The last row is the least alarming of the set: `decoding_params` is allowlisted at the adapter
(`core.model.request_types.ALLOWED_DECODING_KEYS`) and `purpose` / `key_representation_id` are
request metadata, not prompt text, so relocating a payload there does not currently reach the model.
The `response_format` key IS allowlisted and does carry a JSON schema to the server, which is a text
channel the guard does not inspect; no landed flight uses it to carry knowledge.

---

## 5. Ranked — the non-FIRES findings, by how much landed work depends on them

Ordered by exposure, most first. **Be clear about what "exposure" means here: an uninformative gate
does not by itself make a conclusion wrong.** Where a landed number is unaffected, that is stated.

### Rank 1 — the two KB-BUILD decontamination gates (#1, #2). CANNOT FAIL.

**What rests on them.** The clean-decontamination verdict is quoted as the leakage protection for
the whole knowledge plane: `slurp-kb-size-full.json` (`checked_sample_count` 50,628,
`verdict: clean`) backs the pinned SLURP snapshot `e27b2745…a51b57` that every DEV-100 / DEV-500 /
DEV-1000 flight retrieved from, and `a2t-kb-size-full.json` (22,951, `verdict: clean`) backs the
pinned A2T snapshot the whole G1 campaign retrieved from. The DEV-1000 lock verdict cites the SLURP
receipt by name in §4.

**How exposed.** **Low, and the reason matters.** The gates cannot fire because the property they
check is enforced *structurally*, one step earlier, by something stronger: SLURP ids are
split-namespaced (`slurp:train:*` vs `slurp:devel:*`), and the A2T construction pool is literally
`pool − eval − exposed`. So the no-leakage property is TRUE; it is the *check* that is
uninformative, not the conclusion. The residual risk is narrow but real: these gates are the only
thing that would catch a future build pointed at a merged corpus, or a DEV-ladder receipt that ever
pinned a train-prefixed id — and today they would not catch either, because they would still be
comparing disjoint namespaces. Neither is a repair this row may make.

### Rank 2 — the A2T coverage report's six metrics and its `tool_coverage` denominator (#6, #7). CANNOT FAIL / NARROWER.

**What rests on them.** `docs/readiness/2026-08-25-a2t-generality-campaign-plan.md` §3.2–3.3 uses
the coverage block as the evidence that the A2T KB models the tool space before the G1 flight was
authorized; the G0 receipt publishes `tool_coverage` 1.0 alongside `registry_tools` 152.

**How exposed.** **Low on the landed numbers, higher as a forward-looking instrument.** The one
uncovered registry tool, `getLockStatus`, is the receipt's own `registry_tools_never_gold` entry —
no gold trajectory targets it, so nothing in the landed G1 read depends on it being modelled. But
the metric would read 1.0 in exactly the same way if ten gold-bearing tools were missing, because
its denominator is the pool it was drawn from rather than the registry the core may call. This is
the SLURP intent-coverage defect, on the other carrier, across six metrics instead of one, and it
was not previously on record.

### Rank 3 — the damage-channel analysis's winner-label gate (#41). CANNOT FAIL as a stop condition.

**What rests on it.** `docs/readiness/2026-08-24-dev100-damage-channel-analysis.md` §2 states that
the replay reproduces, for 100/100 samples, both the round-2 SUPPLY channel's `selected_value_ids`
and the flown `winner_label`, and concludes: "*Both gates pass with zero mismatches, so every number
below is arithmetic over the flown trajectories rather than a model of them.*" Everything downstream
in that document — the 11-sample damage dissection, the knob counterfactuals, and through them the
δ retain-override that the DEV-1000 lock later falsified out of sample — inherits that claim.

**How exposed.** **Nil on the landed numbers, real as a discipline gap.** The unmutated re-run
confirms `winner_label_matches = 100` of 100, so the document's factual claim is true. But the
sentence "both gates pass" implies two fail-closed gates and there is only one: `analyse()` raises
on `supply_gate_passed` and never reads `winner_gate_passed`. A future run in which the winner
replay drifted would publish `winner_gate_passed: false` inside its own report and continue to
completion, and a reader who trusted the "both gates" phrasing would not go looking. This is the
same defect class as the others in this list — a guard that is reported rather than enforced — and
it is the one whose repair would be smallest.

### Rank 4 — the decode-rate sentinel's median blind spot (#29). NARROWER.

**What rests on it.** The DEV-1000 lock preregistration §4 and the DEV-500 preregistration both list
the sentinel among the preflight protections that make the flight's timing trustworthy; the lock
campaign flew 3,009 worst-case contacts under it.

**How exposed.** **Low for the landed flights, moderate for future ones.** The failure the sentinel
exists to catch — the attempt-2 co-residency state, in which *every* contact degraded to ~1,000
ms/token — is exactly the sustained kind it does trip on, and it did its job. What it cannot see is
an intermittent degradation touching up to 3 of every 8 contacts, which is the more likely shape of
a contended GPU. No landed conclusion depends on the absence of such a degradation, because decode
latency does not change a decode's content.

### Rank 5 — the byte-compare canary's cross-attempt leg (#31). NARROWER.

**What rests on it.** The DEV-1000 preregistration §4 lists the canary as "<300 ms/token +
byte-compare", which reads as two stop conditions.

**How exposed.** **Nil for the landed lock, and the narrowness is deliberate.** The lock flight ran
the BASE `llama.cpp-featcache` binary while the attempt-1 hashes came from a different build, so a
cross-attempt divergence is *expected* and treating it as a stop would have been wrong. The
within-build determinism check, which IS a stop, is the one that carries the continuity claim. The
preregistration's phrasing is what overstates it, not the code.

### Rank 6 — the CONTROL-text payload guard (#20). NARROWER.

**What rests on it.** It is the machine enforcement of the charter clause that CONTROL text must not
carry knowledge that ought to arrive through traced SUPPLY. It is on the live path — the runner
calls it on every contact wave of both `_run_agent_trajectory` and `_run_agent_openjiuwen`.

**How exposed.** **Nil in practice, because the instruction text in every landed flight is a fixed
template that no code derives from the snapshot.** The guard is a defence against a future
controller that composes instructions from retrieved material, and against that it is weak: any
one-character edit or whitespace reflow defeats it, and a `task_target` label — the exact quantity
the SLURP task predicts — is short enough to slip through the 8-character filter on some snapshots.
It is a tripwire for an honest mistake, not a barrier against a determined one, and it should be
described that way.

### Rank 7 — the A4-lesson empty-intersection guard (#35). CANNOT FAIL.

**What rests on it.** It is named in `dev1000_lock_read.load_populations` as the guard against the
recorded A4 failure (partitioning on the carrier-prefixed `key` rather than the `id`, which yields a
silently empty intersection).

**How exposed.** **Nil.** The A4 failure mode IS caught — by the subset check on the line above it,
and again by the `derived != new500` set-difference check, the disjointness check and the union
check below it. The named guard is dead only because it is dominated. The lock population is proved
four ways over; nothing rests on the dead line.

### Rank 8 — `ExecutionPlan.validate` budget magnitude (#13), the prior-score load side (#22), the co-residency disarm window (#27), `decontamination.verdict` (#4). CANNOT FAIL, all by design.

Three of these are documented deliberate decisions with recorded rationale (retired budget caps,
readable historical snapshots, the offline bridge). The fourth, `decontamination.verdict`, is a
literal string in a receipt writer: it is not wrong, it simply carries no information beyond "the
builder did not raise", and a reader who treats it as a computed verdict is reading more into it
than is there.

### Rank 9 — `assert_knowledge_use_binding`'s hash passthrough (#18). NARROWER.

**How exposed.** **Nil on the live path.** `run_speech_native_agent_loop` computes
`knowledge_snapshot.content_hash()` itself and threads that value down; no caller supplies an
unrelated hash. The narrowness is a property of the function's contract, not of any flight.

---

## 6. What this audit did NOT cover, and what it could not construct

- **Scope, stated so a deviation is visible.** Only gates, metrics, invariants and pre-registered
  verdicts that a LANDED CONCLUSION relies on. A sweep of every assertion in the codebase was
  explicitly not attempted. In particular: the E0 closure and scoring-freeze gates, the media and
  evidence identity gates, the runtime/GGUF byte gates, the trace-sink and attempt-store machinery,
  and every gate belonging to the retired earnings-carrier rounds were left alone except for
  `core.split_receipt.verify_receipt_document`, which campaign documents name directly.
- **#32, the byte-compare canary's within-build leg, is UNTESTED.** Making it fail requires two live
  decode passes on the same binary returning different bytes — a model contact this row may not
  take. What would be needed: a launcher dry-run harness that injects a scripted second response,
  which does not exist and which this row may not build.
- **Two falsifiers (#42, #43) were assessed from landed documents rather than by mutation**, because
  what makes them narrow is their wording against an outcome that has already been observed, not a
  code path. Both are labelled as such in the table.
- **The A2T snapshot rebuilt during this audit is `a2t-kb-toolshaped-961e088609b6f1bc`, not the
  landed `a2t-kb-toolshaped-9eb5f4bf186a0285`**, because the audit passed `seed=20260807` (the
  partition seed) where the build script passes `BUILD_SEED=20260825`. The partition itself
  reproduced exactly (`items_construction` 22,951, matching the landed `partition_report`), so the
  decontamination finding is unaffected; the coverage sweep is over the same construction pool. No
  snapshot was written to disk.
- **No claim is made that the FIRES gates are complete.** A gate that fires on the mutations
  constructed here may still be narrower than its claim along an axis nobody thought to mutate. The
  table records what was tested, not what is safe.

---

## 7. Disclosures

The SLURP intent-coverage finding (#5, #8) is a **restatement and strengthening** of
`docs/readiness/2026-08-25-slurp-intent-coverage-check.md`, which established that the metric is 1.0
with probability one at the landed configuration; the measured addition here is that it is 1.0 at
*every* configuration the builder accepts, down to `datastore_size=1`. The prior-score range
contract (#21, #22) is the one landed by
`docs/readiness/2026-08-25-prior-score-semantics-repair.md`; this audit confirms both of its sides
behave as that document specifies. Findings #42 and #43 are already on record and are carried here
only so the table is complete.

Every mutation was reverted. `git status --porcelain` was empty before the audit began and is empty
after it; the only tracked change this row lands is this document, its receipt, and the
exposure-ledger row and its execution-facts append.
