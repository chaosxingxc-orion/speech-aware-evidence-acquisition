# Efficiency cell EFF-1: constant native tool-schema rendering, preregistration

Status: **PREREGISTERED BEFORE CONTACT. BOTH CELLS `held`.** Author: the EFF-1 registration agent,
worktree `/home/chao/saea-worktrees/fable-eff1`, branch `fable/eff1`, base commit `6851acdc`
(item E17 merged at `d6fade1e`). Authority: **owner decision 41 of 2026-09-19** (the throughput root
cause, and the coordinator's 12 GPU-hour target for the test read); **owner decision 38** (margins —
a configuration's own replicate, with cell B0r's own null as the registered fallback); **owner
decision 30** (efficiency cells do not count toward the headroom trigger); **owner decision 28**
(development numbers); **owner decision 25** (HARMFUL requires a measured loss); **owner decision
23** (the official, unprojected number decides); **owner decision 22** (the resume-recovery clause
every new registration carries); **owner decision 17** (net harmed rows per scenario); **owner
decisions 7 and 14** (projection v3 and the TRAIN symmetric sibling reported beside every official
number). All in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`.

Engineering: `docs/superpowers/specs/2026-09-19-e17-constant-tool-rendering-design.md` (item E17,
which ships the mechanism and registers **no** cell). Measured motivation:
`docs/results/2026-09-19-slurp-throughput-root-cause-v1.md` (lever **L1**) and
`docs/receipts/slurp-throughput-root-cause-v1.json`.

This document grants no model contact. Both cells it registers stay readiness `held` until the
coordinator mints the root decision receipt and flips them with `scripts/flights/repin_cell.py`.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer, server and
paid-API contacts**. The resident service was never started, stopped or queried. `SPEECHRL_DATA_DIR`
was read read-only, apart from the two prepared artifacts this cell's own model-free `prepare-supply`
wrote under its own run ids. No utterance text, filler or gold is printed or persisted anywhere in
this package.

## 1. Why this cell exists, and what kind of cell it is

**This is an EFFICIENCY cell. Its purpose is throughput and its admission rule is NEUTRAL.**

The throughput root-cause report measured that the SLURP flights are **prefill-bound**: across four
sealed native runs the wall clock is predicted by the count of prompt tokens llama.cpp actually had
to evaluate, at **488 to 536 seconds per million prefilled tokens** — a spread of about 5 % — while
the same wall clock predicted from contacts varies by 30 % and from generated tokens by 20 %. The
machine's aggregate prefill rate is already at its single-stream ceiling, so what makes a flight slow
is **how many tokens the row presents for evaluation**.

The dominant cause of that count is not prompt size. It is **prefix-cache breakage**, and it has one
named source:

1. `task_instruction` is **byte-identical across all four roles** — one distinct SHA-256 over every
   request of every sealed native run. The instruction is not what changes.
2. The **Reviewer is the only role that carries a native `tool_schemas` entry**.
3. The Qwen3-Omni chat template renders the `tools` array **inside the system message**.
4. `decoding_params.id_slot` is `per-sample`, so one row owns one slot for its whole trajectory and
   its five contacts run in the order perception, solver, reviewer, reviewer, planner.

Together: the tools block **toggles on at contact 3 and off at contact 5**, each toggle changes the
token stream about 2,220 tokens in, and that invalidates the whole KV prefix behind it — including
the speech packet, re-decoded on **100 %** of first-Reviewer and Planner contacts. Measured on the
B4b replicate:

| position | role | tools | prompt (med) | prefilled (med) | cached | packet re-decoded | prefilled / row | share |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | perception | 0 | 3,597 | 1,373 | 61.8 % | 100 % | 1,374 | 5.2 % |
| 1 | solver | 0 | 9,960 | 6,591 | 36.1 % | 0 % | 6,258 | 23.9 % |
| 2 | reviewer #1 | **1** | 10,062 | **7,843** | 23.6 % | **100 %** | **7,505** | **28.7 %** |
| 3 | reviewer #2 | 1 | 11,813 | 1,757 | 83.5 % | 1.4 % | 1,859 | 7.1 % |
| 4 | planner | **0** | 11,805 | **9,586** | 19.8 % | **100 %** | **9,109** | **34.8 %** |

Positions 2 and 4 carry **63.5 % of all prefill work**, and position 3 — the *same role* as position
2, with a *longer* prompt — costs a quarter of it. Nothing about the Reviewer or the Planner is
intrinsically expensive; their neighbours' tools shape is.

Item E17 built the switch. This package decides it.

> **Order matters and it is part of the registration.** The report's ranking note is explicit: the
> Planner looks like the single biggest line item, but four fifths of its cost is this toggle.
> **L1 must be evaluated before L2 (drop the Planner) and before L3 (shrink the evidence block)**,
> or L2 will be credited with L1's gain.

## 2. The question

> Does holding the native tool-schema rendering constant across the five role contacts of a row
> reduce prefilled prompt tokens per row and GPU hours per 1,080 rows on the sealed dual-store anchor
> base, **without moving the official number**?

The first half is what the cell **measures**. The second half is what it must **pass**.

## 3. The one factor

**The factor.** Exactly one composed key moves against the sealed anchor's baseline:
`native_episode.tool_schema_rendering`, `"per-role"` → `"constant"`. `"per-role"` is the key's
**absence**, which *is* the anchor's configuration; `rails.config_tables.is_episode_null_arm` reads
an explicit `"per-role"` identically.

Armed, every role contact of a row renders the **same** `tools` array: the union of the tool schemas
any role of the episode may call, in one fixed order (`NativeEpisodeConfig.constant_tool_names`).
For this episode the Reviewer is the only tool-bearing role, so **the union is its own ordered
array** — which is why the Reviewer's request bytes do not move at all, and perception, solver and
planner gain exactly one key.

### 3.1 Rendering is not authority

The key changes **what is rendered**, never **what may be called**:

* each role's `tool_names` is unchanged, and `tool_choice` is still derived from `tool_names` alone —
  a role with no authority still sends `tool_choice: "none"`;
* the framework still advertises that role no ability (`NativeRoleNode` builds it with no `abilities`
  and no `tool_allowed`), so the agent cannot dispatch one;
* if the core emits a call anyway, `_RoleAuthorityRail._assert_allowed` still raises `AbortError`
  with a `PermissionError` cause, the framework hands the role the "outside role authority" tool
  result, and the episode continues.

The loader is fail-closed: `"constant"` is refused when **no** role holds tool authority (it would be
a second spelling of `"per-role"`, and two spellings of one thing is how a cell acquires two
identities) and when two tool-bearing roles declare **different** ordered `tool_names` (the native
tool-authority custody path re-derives a request's schema array from the names the model actually
called and compares its digest to that request's own `tool_schemas_sha256`, which only holds while a
caller's rendered array is exactly its own authority).

### 3.2 It moves request bytes, on three of five contacts, by design

That is why the key is an **episode**-class switch and why **no `request-bytes-identical` falsifier
can exist for it**. `config_hash` and `protocol_hash` move. Nothing else does: no change to
knowledge, roster, split, serving geometry, scorers, contact count, or any role's authority.

Held identical: `knowledge_stores`, `phase_material`, `phase_tools`, `policy`
(`phase-native-candidates-review-revise-v1`, bounded ceiling 11), `scorers`
(`slurp-slu-official-train`, `cost`), `task_instruction_template`
(`probes/slurp_native_role_context_v3.txt`) and its fill, `serving_slot_tokens` 24,576,
`serving_slots` 4, the promoted EVO-FOLDS-V2 packets, the roster, the split, and the Perception
supply reproduced byte for byte. The bookkeeping that must differ is four fields: the FIT run and
attempt ids, the two provenance-only speech-feature ids, and the free-English `what_this_is` note —
plus `prepared_phase_supply`, which is this cell's own (section 5).

### 3.3 `native_episode.finite_completion_policy` — a harness declaration, not a factor

Both EFF-1 baselines declare `finite_completion_policy: "deliver-latest-or-abstain"`. It is
**required** of every live, unflown SLURP native cell by
`scripts/checks/finite_completion_policy_check.py` (item E13), after cell B7a's recovery arm lost
1,451 charged contacts to the module default `"raise"`.

**It renders no request byte.** `rails.runner` reads it once into the core `NativeEpisodeSpec`; it
reaches no template, instruction, evidence block, agent state or decoding parameter. It is not a
member of `EPISODE_LEVEL_SWITCH_KEYS` and claims no module admission.

**And here, uniquely, its asymmetry is closed rather than merely declared.** On every earlier cell
this key created an asymmetry against a comparator that flew under `"raise"`: a sealed comparator
implies it met no finite completion, so any treated row with that disposition is a row the comparator
could not have produced. For EFF-1 the comparator **is** the sealed anchor, and
`docs/receipts/slurp-finite-completion-exposure-v1.json` is the registered exposure receipt proving
**zero finite completions on the anchor**. The count of such rows on this arm remains a mandatory
diagnostic (section 7), the expected count is zero, and the comparator side is provably unaffected.

## 4. Arms, comparator and order

| role | identity |
| --- | --- |
| **arm** | `SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-V1` / `attempt-slurp-native-tool-constant-anchor-train-fold-a-generation-v1`, cell `slurp-native-tool-constant-anchor-train-fold-a-v1`, composed `02b13593d920d6dd93977cf608da8812cb86ddaae3a1222b0287fe50f7507602`, protocol `dc357b14d608d1fd19ea1a879c3fde59809e0af01a0726c2131eabd513af54ab` |
| **arm FIT** | `SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-tool-constant-anchor-train-fold-a-fit-v1`, 47,520 endpoints, inside the same campaign |
| **smoke** | `SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-SMOKE-4-V1` / `attempt-slurp-native-tool-constant-anchor-smoke-4-generation-v1`, cell `slurp-native-tool-constant-anchor-smoke-4-v1`, composed `a007c30b35856a411afcf921d62a618a2a853ec4f044e38f108d2440ed42fc01`, protocol `67746f3211e5e62f330fd2f658c0a60673506725d847b9f1ce166ce989d17fcc` |
| **smoke FIT** | `SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-tool-constant-anchor-smoke-4-fit-v1`, 176 endpoints, inside the same worker |
| **comparator, the only one that gates** | the **sealed dual-store anchor**, run `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`, attempt `attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1`. Scores `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, outputs `d87d71e8fa0fe93b45d5c6817ba125b016d8d91f44a14309171dd0f3a64270d8`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152`; official **48.53 / 77.96**. **Never re-flown, never re-scored, never opened for writing.** |
| **efficiency reference, not an arm** | the **B4b replicate**'s per-position prefill profile, measured in the throughput report's sections 3.1 / 5.2 / 5.3 |

**Hash provenance, stated plainly.** The comparator's three artifact hashes were **re-derived in this
registration** by hashing the sealed files read-only, and its cost block, protocol hash and study
commit were read from its own sealed run manifest:

* `calls_used` **5,417** (5.016 per row), `audio_seconds_used` **15,459.764875**,
  `prompt_tokens_total` **45,998,267** (42,591 per row), `completion_tokens_total` **255,153**,
  `tool_calls` **1,082**, `latency_seconds_total` **46,114.747**;
* `protocol_hash` `2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c`,
  `study_commit` `826a77c7`, `status` `COMPLETED`;
* **3.388 GPU hours**, from the anchor's own exposure-ledger row.

The two official aggregates (48.53 / 77.96) are **carried verbatim** from the registered B8b package
and must be re-verified from the sealed score artifact at read time.

> **One honest gap, declared before contact.** The anchor attempt has **no `flight-receipts.json`**,
> so the comparator's slot occupancy, utilisation, wall seconds and per-position prefill split are
> **not on file**. The per-position reference is therefore the **B4b replicate**, which is a
> different configuration on the same geometry. Every per-position table in the verdict must label
> that column as a **reference**, never as an anchor measurement. The anchor's own realized cost
> block above is a measurement and is the comparator for contacts, audio seconds, prompt tokens and
> GPU hours.

**Order.** The four-row smoke opens when the GPU is free and no other form smoke is in flight. The
1,080-row arm opens only after this cell's own smoke has sealed and its acceptance list passes. One
experiment in flight at a time. **No twin is registered**: there is no gain to control for.

### 4.1 Which side of the rendering switch a later cell sits on

The B8a package required every later cell to say which side of the delivery node it sits on. This
cell inherits that obligation and creates its own:

* **Both sides of this contrast are per-role today.** The comparator is the sealed anchor, which
  rendered per-role, and the arm differs from it by exactly this key.
* **If EFF-1 reads NEUTRAL, `native_episode.tool_schema_rendering: "constant"` enters the SLURP
  default plan, and every later cell and the test read adopt it.** From that moment a cell registered
  against a **sealed per-role arm** is registered against a comparator that is no longer the default,
  and **its package must say so**, exactly as this one says it. Measuring a later mechanism on a
  per-role base after the key is admitted is a **new cell** with its own registration, not an edit of
  an existing one.

## 5. The prepared Perception supply — this cell's own, and the rebuild proved something

EFF-1 owes **no new knowledge**: the key is a rendering switch and moves no supply, no retrieval and
no evidence block. But it registers its **own** prepared artifacts rather than inheriting the
anchor's, for two operational reasons:

1. `core.preparation.artifact_inputs` binds the cell's **whole composed configuration** *and* the
   implementation modules' own digests (item E16). An inherited pin cannot verify for a cell whose
   episode block differs — it would be rebuilt at the flip.
2. `core.flight.repin.assert_no_residue` scans all of `docs/` and `configs/` for an inherited pin's
   old strings and **refuses**, because the donor's own committed fragments legitimately still carry
   them. Building each cell's own artifact first means the re-pin tool finds the pin valid, rebuilds
   nothing, and adds nothing to the residue set.

Both were built in this registration with the model-free `core.flight.cli prepare-supply` step, under
each cell's own run id, with zero model, tokenizer, encoder, scorer and server contacts:

| cell | prepared artifact | SHA-256 | Perception `output` SHA-256 | prepared identity `config_sha256` |
| --- | --- | --- | --- | --- |
| arm | `prepared/SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v1.json` | `84b8ea643bdb9e5a47a9bb5dd39d1101fcaae3cde22116739464fdd6799c7659` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` (1,080 of 1,080 rows — **the sealed anchor preparation's own output**) | `83156991a8d589bd55d92eb52f37304102e25ef8b972768e1a037931716b0768` |
| smoke | `prepared/SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-SMOKE-4-V1/phase-supply-v1.json` | `b46ce333c2636bbe94d067b40f976cd0ba80723096187bd60d1a2bfb7c1a844a` | `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` (4 of 4 rows — the four-row reference every form smoke of this roster shares) | `a115b6758af1b1c336c9f36acf955820977a4908b846e159c9d641c03954873f` |

**The output assertion is the proof, and it was made by hand.** `_compare_artifact_output` does not
run when the tool has nothing to rebuild, so both outputs were asserted directly against the sealed
anchor preparation's own `output_sha256` (`ba5e1faa…`, read read-only from
`prepared/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-PREPARE-V1-R2/phase-supply.json`) and
against the shared four-row reference. **Both matched exactly** — the model-free proof that neither
declared key moves a knowledge-selection byte. Each pin was then re-verified by re-running
`prepare-supply` with the pin in place, which took the warm branch and returned the same digest
without invoking the producer.

> **`--allow-output-change` must never be passed.** If either output SHA-256 stops matching, a merge
> changed the knowledge channel — **stop and report.**

## 6. What this cell delivers — the efficiency read is the deliverable

All of it is read from the flight's own sealed receipts, trace and manifest and from the resident
session's `server.log` and `monitor.jsonl`, joined **per slot** exactly as the throughput report's
section 1.2 joins them: `decoding_params.id_slot` is `per-sample`, so one row owns one slot and the
per-slot request sequences match one for one. `prefilled` is the `prompt eval time` token count;
`cached` is prompt length minus prefilled.

| deliverable | comparator value | expected |
| --- | --- | --- |
| **prefilled tokens / row** | 26,197 (B4b **reference**) | ≈ 13,065 (−50.1 %) |
| **GPU hours / 1,080 rows** | **3.388** (the anchor's own) | ≈ 1.9 |
| **contacts / row** | **5.016** (the anchor's own) | unchanged |
| slot occupancy, utilisation, parked fraction | not on file for the anchor; B4b 0.881 / 90.1 % / 1.8 % | reported |
| per-position cache table (5 positions) | the report's section 5.3 table | positions 2 and 4 fall to ≈ 1,800 prefilled each; packet re-decode share ≈ 80 % → ≤ 25 % |
| `distinct_tool_schemas_sha256` | no block on the OFF arm | **1 on every row**; anything else refutes the mechanism |
| wall seconds / row | 12.79 (B4b reference) | ≈ 6.4 plus the decode floor |
| aggregate prefill / decode tok/s | 2,048 / 18.7 (B4b reference) | prefill unchanged; the flight moves toward the decode bound |

**One number is expected to get worse, and saying so here is the point.** Client-visible
**prompt tokens per row will RISE**, because perception, solver and planner each gain the tools
block. The anchor's measured value is 42,591 per row. Prompt volume is *not* the cost — the report's
section 3.3 shows B2 v3 running 1.71× B1's prompt volume for 0.92× its **prefilled** volume — and a
verdict that quoted the prompt-token rise as a regression would be reading the wrong number. The
per-contact delta at each of the three tool-free positions is registered as a measurement, stated as
an expected rise, and explicitly not a regression.

**Prefill join quality is itself reported.** The verdict states the share of contacts on which
`n_tokens - generated + 1` equals the client's `usage.prompt_tokens`. The report achieved 100.00 % on
five sealed runs. Below 100.00 %, the per-role figures are reported as **estimates**, not
measurements, and the verdict says so.

## 7. Metrics, the guard, and the mandatory diagnostics

**The admission guard: official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded, used as a **non-inferiority guard** and not as a gain.
**Second guard: intent (joint scenario+action) accuracy.**

Secondaries: intent, scenario and action accuracy, official pooled span F1, per-row mean official
SLU-F1, per-row mean exact slot F1, and saves / harms / ties with the exact two-sided McNemar p.
**Projection v3 (`slurp-slu-official-projected-v3-train`) and the TRAIN symmetric sibling
(`slurp-slu-f1-normalized-v1-train`) are reported beside every official number** (owner decisions 7
and 14); owner decision 23 keeps the **official, unprojected** number the one that decides.

Mandatory diagnostics:

1. **Finite-completion rows**: the count whose `terminal_disposition.reason` is `"finite_completion"`,
   the affected sample ids, the delivered-draft versus abstention split, and — only if the count is
   non-zero — the primary metric recomputed with those rows excluded **beside** the registered
   all-rows number, which stays the number the decision rule reads. **No row filtering.** Expected
   zero; the anchor side is provably zero.
2. **`planner_action_illegal`**: the flight's own count, the sample ids that carry it, and their
   action character counts and SHA-256 values — the form inherited from the B7a recovery note's
   section 8. Reported whether or not it is zero.
3. **First-request byte identity, stated honestly.** The first request of a row is the Perception
   request, and under this factor it is **NOT byte-identical** to the anchor's: the tools array is
   added to it. What **is** claimed, and what the smoke proves, is that (a) every **Reviewer** request
   is byte-identical to the anchor's request at the same position of the same sample id, and (b) the
   perception, solver and planner payloads differ from the anchor's in **exactly one key, `tools`**,
   with `tool_choice` still `"none"` — that is,
   `{k: v for k, v in on.items() if k != "tools"} == off`. A differing Reviewer request, or any other
   differing key on the three tool-free roles, is a **failure**. A differing solver or planner request
   whose upstream model response differs is **reported**, not silently excused: greedy decoding at
   temperature 0 is not bitwise reproducible across batch compositions.
4. **The constancy table** per row from the sealed receipt, with `authority_tool_names` beside
   `rendered_tool_names`.
5. **Native task-contract call count** against the anchor's realized **1,082**, plus the count of tool
   calls emitted by a role that holds **no** authority, per role. Expected zero. A refused call is not
   a flight failure — the rail refuses it and the episode continues — but it is the single most
   interesting behavioural consequence of showing three more roles the tool definitions, and it is
   reported.
6. **Per-scenario** intent and SLU over all 18 scenarios in **both** weightings, plus **net harmed
   rows per scenario**, any scenario of five or more flagged (owner decision 17) — a diagnostic the
   verdict must carry, not an additional gate.
7. **Row accounting**: 1,080 in, 1,080 out on both sides, no row dropped and no `sample_id` invented.
8. **Cost**: contacts, repeated speech seconds, FIT endpoints and GPU hours against the anchor's
   realized figures and against the ceilings.

**Resampling:** paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for the
decision clauses and CI90 for diagnostics, both as percentile pairs of the same retained replicate
sequence. Sensitivity: paired scenario-stratified row bootstrap, same draws and seed. Every table in
both the natural-mixture and the equal-scenario weighting. Both sides are decoded runs, so the paired
interval carries real decoding noise; the own-null margins are the calibration for exactly that, and
a **non-inferiority** read is the correct shape here precisely because the expected true effect is
zero.

`delta = EFF-1 minus the sealed anchor`, in percentage points; negative means the arm is worse.

### Decision rule, fixed here before any number is read

Own-null margins, the TRAIN A own null measured by cell B0r on this exact roster and geometry:
**h_SLU = 1.1218 pp**, **h_intent = 1.0051 pp** at CI95 (0.9420 / 0.8505 at CI90). Owner decision 38
makes a configuration's own replicate the first margin; this cell has no replicate, so B0r's own null
is the registered **fallback**.

> **HARMFUL is read first** (owner decision 25, Method B): only by a **measured loss** — a point
> estimate of official pooled SLU or of intent below **−h** (−1.1218 / −1.0051), or a CI95 **upper**
> bound below zero. An interval that straddles zero with the point estimate inside the margin is
> **not** harmful.
>
> **NEUTRAL — and NEUTRAL is what admits this cell — if and only if both guards are non-inferior**
> against the sealed anchor's score artifact:
> 1. the CI95 **lower** bound of the paired **official pooled SLU-F1** delta exceeds **−1.1218**; and
> 2. the CI95 **lower** bound of the paired **intent** delta exceeds **−1.0051**.
>
> **NON-INFERIORITY NOT PROVEN** if either interval is so wide that its CI95 lower bound falls below
> −h without a point estimate below −h. That is neither NEUTRAL nor HARMFUL: the key does not enter
> the default plan, and the remedy is the configuration's **own replicate** (owner decision 38's
> first clause), not a re-read of this one.
>
> **The scenario band is a diagnostic, not a gate.** A scenario loses intent beyond the null band
> when the CI95 upper bound of that scenario's own paired intent delta is below zero. Under owner
> decision 17 the verdict must carry and state it; a breach is reported as a breach and does not by
> itself convert a non-inferior read into HARMFUL, which requires a roster-level measured loss.
>
> **There is no ADMITTED-on-a-gain clause.** If the paired SLU delta's CI95 lower bound happens to
> exceed zero, that is **reported as a fact** and explicitly **not** claimed as an effect of the
> rendering key: the cell has no mechanism by which constant rendering should raise quality, and a
> positive interval on a one-shot read is not an admission.
>
> **Read exactly once.** No repeat-to-pass, no re-scoring, no second estimator, no re-weighting after
> seeing a number.

**The efficiency numbers are reported regardless**, including under HARMFUL. A cost measurement is
not contingent on a quality outcome.

**NEUTRAL and the default plan.** The SLURP v2 design's section 15 resolution 5 admits a NEUTRAL
switch into the default plan **only if it lowers cost**. This one does, measurably, which is the
whole point of the cell. **On NEUTRAL the key enters the SLURP default plan and every later cell and
the test read adopt it** — and the clause of section 4.1 binds from that moment. A HARMFUL EFF-1
enters no plan, the per-role rendering stays the default, and lever L2 must **not** then be credited
with L1's gain.

**An efficiency cell does not count toward owner decision 30's headroom trigger.** This cell consumes
a flight slot and a share of the GPU budget; it does not consume a headroom attempt, and a NEUTRAL
result here is not evidence about the bar. The verdict states this in those words.

**Not a bar attempt.** The verdict states the official pooled SLU the arm reaches as a **fact** beside
the anchor's 48.53 / 77.96, never as a claim, and "replicated on the same roster" is not claimed by
anything here.

> **STOP condition, before any table of this read is looked at.** (1) The sealed anchor comparator
> must reproduce its own registered official aggregates to the hundredth of a point, from its sealed
> score artifact, with its three artifact hashes re-verified by hashing the files. (2) Every row must
> be accounted for — 1,080 in, 1,080 out — on both sides. (3) The roster, split identity and scenario
> / speaker strata must be identical on both sides. (4) The sealed tool-schema-rendering receipt must
> report `distinct_tool_schemas_sha256 == 1` on every row. If any clause fails, the read stops and the
> discrepancy is reported before anything else happens.

## 8. Prompt fit

Slot **24,576** tokens; decision **ALLOW** for every phase of both cells.

The basis is the sealed anchor's own realized prompt distribution over this exact roster plus one
rendered `tools` array on the three tool-free roles. That array is the Reviewer's own, which the
anchor already rendered on 1,082 tool-bearing contacts without approaching the slot; adding it to
three shorter prompts cannot approach it either. The throughput report's section 4 records p99.9
prompt lengths of 15,045–15,756 and a maximum context used of 15,350–18,110 across four sealed native
runs, with **zero truncations**.

Item E17 also repaired a latent defect in exactly this gate:
`FlightRuntime._assess_prompt_budget` used to budget the preflight estimate against a fixed 32,768
whenever a fragment declared no `context_budget_limits` block — every committed SLURP fragment is
such a fragment and every one of them serves **24,576**-token slots. The gate now reads the live
per-slot limit from the adapter's own serving geometry. Nothing was ever harmed by the old behaviour,
but this cell flies under the repaired gate.

**The authority in flight is `core.preparation_fit.build_native_contact_fit_gate`**, which fits every
realized immutable request against the resident tokenizer before it is transmitted and **stops the
flight rather than truncating**. No static bound in this package replaces it.

## 9. Budgets and cost reporting

| | generation | FIT endpoints | speech seconds | GPU hours | task-contract calls | official scores |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **arm** | 11,880 | 47,520 | 33,930 | 12.0 | 6,480 | 1 |
| **smoke** | 44 | 176 | 117 | 1.0 | 24 | 0 |

ASR, encoder and paid-API calls are zero in both. 11,880 is the exact eleven-contact program maximum
(1,080 × 11), not an estimate and not a target; 47,520 is 11,880 × (1 speech packet + 3 endpoints);
the smoke is the same arithmetic on four rows. **The key adds no contact**: it changes what three of
the five contacts render, never how many there are. Ceilings are run-cumulative across every attempt
of a run id, and unused budget is never attempt authority.

**Expected cost.** The sealed anchor realized **5,417 contacts, 15,459.76 repeated speech seconds and
3.388 GPU hours**. This cell expects the **same** contact count and the **same** audio seconds at
roughly **half** the GPU hours (≈ 1.9). The 12-hour ceiling is the registered ceiling, not a forecast.

Every verdict reports: actual generation contacts against 5,417 and the ceiling; contacts per row;
actual repeated speech seconds against 15,459.764875; actual FIT endpoints; actual native
task-contract calls against 1,082; GPU hours read from the serving monitor over the lease window,
never a wall-clock guess; mean latency, slot occupancy and duty cycle; and the efficiency table of
section 6, which is the reason the cell exists.

## 10. The four-row smoke — structural and efficiency acceptance only

The smoke proves the mechanism reaches the **server**, not only the renderer. Accept only if all
eight hold:

1. **Delivery.** 4 of 4 rows delivered, five contacts per row, no row above the bounded ceiling of 11.
2. **Constancy.** The sealed receipt carries `tool_schema_rendering` on every row with `schema`
   `saea-native-tool-schema-rendering-v1`, `mode` `constant`, `rendered_tool_names`
   `["saea-tool-task-contract-v1"]`, one contact row per realized contact, `authority_tool_names` `[]`
   on perception / solver / planner against `["saea-tool-task-contract-v1"]` on the two Reviewer
   contacts, and **`distinct_tool_schemas_sha256 == 1` on every row**.
3. **The Reviewer bytes do not move.** Each Reviewer `MODEL_REQUEST` of each of the four rows is
   **byte-identical** (`request_sha256`) to the sealed anchor's request at the same position of the
   same sample id. **The anchor has no four-row smoke of its own** — it was flown once, directly, over
   the 1,080-row roster — so the comparison is against the anchor's own sealed trace under
   `runs/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/`, restricted to these four
   sample ids, which are members of that roster. That trace is **read-only**: never write to it, and
   read no answer, reference or quality field of it.
4. **The other roles differ only by `tools`.** For each perception, solver and planner request, the
   payload minus the `tools` key is byte-identical to the anchor's and `tool_choice` is still
   `"none"`. A differing **Perception** payload outside the `tools` key **is** a failure — it precedes
   every generation and nothing else can explain it.
5. **Fit and seal.** One `*.request-fit.json` per realized contact with `every_request_fits = true`
   and every required-token count below 24,576; the worker prints a seal; the manifest seals clean;
   the tree is still clean.
6. **The point of the smoke — the cache.** The server-reported cached-token share per position, read
   from the resident session's `server.log` joined to these contacts per slot, shows the
   **first-Reviewer and Planner contacts no longer re-prefilling the packet**: their cached share
   rises from the anchor-era 23.6 % and 19.8 % toward the same-tools handover's 83.5 %, and the
   speech-packet re-decode share at those two positions falls from 100 % toward 0. Four rows cannot
   establish a rate, so **no threshold gates the smoke on this number** — but a cached share that does
   **not** move at those two positions means the mechanism did not reach the server, and that **is** a
   failure.
7. **Finite completions.** Any row whose `terminal_disposition.reason` is `"finite_completion"` is
   **retained** and reported, never an error. Expected zero. What is **not** acceptable is an abort on
   `finish_reason` `"length"`: that would mean the declared policy did not reach the runtime.
8. **Authority.** Zero tool calls from perception, solver or planner is the expected result. A call
   refused by `_RoleAuthorityRail` is reported with its role and sample id and is **not** a failure —
   the rail is the designed behaviour — but it is recorded as the first observed behavioural
   consequence of showing a tool-free role the definitions.

No scorer, no answer, reference or quality interpretation, and no task-quality claim. **A structural
smoke result is never a quality result.**

## 11. Failure rule

The first failure stops the flight and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. **At most one
root-diagnosed recovery re-registration per flight**; a second failure closes that flight and the fix
must be proven on a four-row dry run before the key is proposed again. A failed four-row smoke stops
cell EFF-1 until the fix is proven on that same four-row roster. One experiment in flight at a time.

**Resume-recovery clause (owner decision 22 of 2026-09-18).** If an attempt dies of an
**infrastructure** failure with code and request bytes unchanged — never a harness or config defect —
the one allowed recovery may be a **resume-recovery** under item E10 instead of a re-fly: every
complete row of the aborted attempt is kept without selection, every partial or unstarted row is
flown under the same run id, and the merged manifest declares the predecessor attempt with its trace
hash, kept-row list and that list's hash. It changes no question, roster, factor, comparator, decision
rule or cap, and the run-cumulative budget must be re-checked because a resumed attempt and its
predecessor share one run id.

**One clause is specific to an efficiency cell.** A resumed efficiency read must additionally state
the **split of its GPU hours and prefilled tokens across attempts**, because a merged manifest's cost
is the sum of two lease windows; a per-row rate computed over the merged manifest alone would be
wrong.

A completion that hits the 512-token cap is **not** a failure in this cell: section 3.3's declared
policy retains the row and the count is a diagnostic.

## 12. What is NOT claimed

- **No effectiveness claim.** This cell asserts nothing about SLU F1, intent accuracy or any quality
  metric except that they do not fall. It is not expected to improve anything and cannot be admitted
  for improving anything.
- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster and every claim of this cell stops at it. Fold B, DEV-1000 and the test split stay
  untouched and unread.
- **No claim about other carriers.** The measurement is SLURP native, np4, ctx24k, `id_slot`
  per-sample. Earnings and Audio2Tool are not addressed, and a saving measured here is not a saving
  claimed there.
- **No claim that the Planner or the Reviewer is expensive.** Their neighbours' tools shape is. The
  report's levers L2 and L6 are separate, effectiveness-bearing questions and are not decided here.
- **No geometry claim.** np6 / np8 and `-ub` remain out of scope (report L8 and L5(b)). They become
  interesting only after the row stops being prefill-bound, which is a consequence this cell may
  **measure** but does not act on.
- **No claim that the predicted 50.1 % is the realized saving.** 50.1 % comes from character-level
  longest-common-prefix proxies plus llama.cpp's common-prefix rule. The realized token-level number
  is what this cell measures, and it may be smaller or larger.
- **No claim about what three more roles do with the tool definitions.** Showing a tool-free role the
  definitions inserts the template's tool paragraph into its system message and the model can react to
  it. That is exactly what the neutrality guard is for; the cell measures the outcome, it does not
  explain it.
- **Nothing about any in-flight cell.** Cells registered against the anchor or against a per-role base
  are unaffected by this registration, and no number here is evidence for or against any of them.
- **A structural smoke result is never a quality result**, and this is not a bar attempt.

## 13. Pre-contact evidence on file

In this readiness directory (`docs/readiness/2026-09-19-slurp-eff1-tool-constant-v1/`), all
model-free:

| file | what it carries | SHA-256 |
| --- | --- | --- |
| `README.md` | the launch runbook | (rewritten by the re-pin tool) |
| `protocol-registered-v1.json` | the frozen protocol | `6ef936762b024d812b4045db163dd0a3f6bd45c084af5e514cae6d6c1287b1cb` |
| `generation-plan-v1.json` / `-registered-v1.json` | the 1,080-row arm's plan | `04fd70c68b179b236b106ed9cf310d7b46b7cf671ca5572cf13791af6d015704` |
| `fit-plan-v1.json` / `-registered-v1.json` | the arm's native contact-fit plan | `82f72d71b270b627e8d3b0c15fc2bc43b575283e01696dd3d76481b9a4f1f354` |
| `smoke-generation-plan-v1.json` / `-registered-v1.json` | the four-row smoke's plan | `d241965ffece2d58aee659bb4e199e4f9341d706142413192a67daf1bf0f75af` |
| `smoke-fit-plan-v1.json` / `-registered-v1.json` | the smoke's FIT plan | `48a7ba70b1fe9dd8d447198be44c34f1615b2af92fb2344a1ebd3d9a2fe19f44` |
| `analysis-recipe-v1.json` | the paired read plus the efficiency tables | `9c7858476e500413fd733ddde333efef570170facd8641d8a2a4c54754bcc83c` |

Config fragments: `configs/baseline/slurp-native-anchor-tool-constant-train-fold-a-v1.json`,
`configs/baseline/slurp-native-anchor-tool-constant-smoke-4-v1.json`,
`configs/experiment/slurp-native-tool-constant-anchor-train-fold-a-v1.json`,
`configs/experiment/slurp-native-tool-constant-anchor-smoke-4-v1.json`,
`configs/campaign/slurp-native-tool-constant-anchor-train-fold-a-v1.json`.

**No `core.flight.cli check` receipt is on file, and that is deliberate.** `FlightRuntime.preflight`
asserts a clean study tree and reserves the attempt in the durable `AttemptStore`; a registration
agent that has not committed cannot run it without either failing on its own uncommitted files or
writing an attempt reservation it has no authority to make. The composed and protocol hashes were
computed directly through `core.config.compose` / `core.config.protocol_hash` — the same two functions
`check` itself uses — and **the method was verified on this tree**: composing cell B7a v2's own four
fragments reproduces its registered composed
`73a817ffda56b02501002685db0cd695516425644544fa040464efb17849d494` / protocol
`f5a6733f39952cfba2fc418d233c8acf1ff3a3758f16765737de47cc2fbceb31`, and its smoke's
`fbe7556e225a4f6ab53f466b09f3b8fcd1efba45404e55a566d0f081b16e8880` /
`1f3bdd15ece682b449d0706301a633af09a747f5ef38fa3b93aacc65ae0e52e5`.

**`core.flight.cli wire-check` remains unavailable** for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. The substitute is
`tests/unit/test_eff1_tool_constant_config.py` together with
`tests/unit/test_e17_constant_tool_rendering.py`, which run the real OpenJiuwen role graph, the real
`rails.runner` and the real `LlamaServerTransport.render_request` over the shared fake transport and
compare every rendered request with and without the key.

**These hashes describe the fragments exactly as committed**: readiness `held`, this cell's **own**
`preparation` requirement pinned, **no `decision` requirement**. `compose()` hashes the whole merged
fragment set, so adding the decision requirement and flipping readiness change the composed hash and
therefore the protocol hash. The re-pin tool does both in one cycle and rewrites every dependent hash;
nothing here is edited by hand.

## 14. What this package does not authorise

No readiness flip, no model contact, no default-plan edit and no harness-admission entry. The
admission entry for the module "constant native tool-schema rendering" is written from the sealed
verdict, never from this registration; the protocol document records the expected entry shape so the
coordinator can check it against the switch rule before writing it.
