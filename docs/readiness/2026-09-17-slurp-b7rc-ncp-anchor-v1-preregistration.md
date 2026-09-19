# Cells B7r and B7c on cell B7a's configuration: the Reviewer output contract and the tool-observation rewrite, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B7r/B7c registration agent, worktree
`/home/chao/saea-worktrees/fable-b7rc`, branch `fable/b7rc`, base commit `b4cb9ae9`, registration
commit `8b6b0c0b`. Authority:
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` sections 3-6, 11 and 15
(coordinator resolutions 2 and 3), owner decisions **12, 15 and 17 of 2026-09-17**
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`), the evidence base
`docs/results/2026-09-17-slurp-node-context-audit-v1.md`, and the B7a package
`docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md` (registered at
`2c39a957`). This document grants no model contact; all four cells stay readiness `held` until the
coordinator flips them.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried, and no worker, campaign,
smoke or FIT was run.

## 1. Questions

Both cells are one-factor steps **on top of cell B7a** — the Node Context Policy at level L1,
`structured` on the eight model-output boundaries, tool-observation `raw`, no producer format.

**B7r.** Cell B7a leaves the Reviewer prose, so the `planner:review-finding` and
`solver:review-finding` boundaries render their **FALLBACK-RAW** block on 100 % of rows: 2,167 of
2,167 sealed anchor Reviewer outputs fail the repository's own registered findings parser. Does
structuring what the Reviewer **generates** — binding the registered response format
`saea-review-findings-v1` to the review-finding producer, so those two boundaries can render
findings where the output parses — raise pooled official SLU micro F1 on TRAIN Fold A without
harming intent?

**B7c.** The audit measured 13,634,712 characters of one duplication: a replayed task-contract tool
observation echoes a contract the receiving request's own system message already carries verbatim
and in full. Does replacing that echo with a reference — the `structured` level on the four
`<role>:tool-observation` boundaries, which the policy applies only when the contract is provably a
substring of that request's system message — raise pooled official SLU micro F1 without harming
intent?

## 2. Arms

| role | identity |
| --- | --- |
| B7r | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-TRAIN-FOLD-A-V1` / `attempt-slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-generation-v1`, cell `slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1`, composed `6f4305068a65de7a591fcdc08e7182ebfdafec43ff0efa240afbb23784119cf1`, protocol `ea40fd649a62313d4dcaa038925c15e994a14173010b501f165e7b387d8cd076` |
| B7r smoke | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-SMOKE-4-V1` / `attempt-slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-generation-v1`, cell `slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1`, composed `bf8da2447697ce7ed7d89f4e70d47fb24335848a801c3cd36c569e9de37e1276`, protocol `1511e4e529b874c336750b0401902ed698d0696065835d7e100e764a8e59e9f1` |
| B7c | `SAEA-SLURP-NATIVE-NCP-L1-TOOL-OBS-ANCHOR-TRAIN-FOLD-A-V1` / `attempt-slurp-native-ncp-l1-tool-obs-anchor-train-fold-a-generation-v1`, cell `slurp-native-ncp-l1-tool-obs-anchor-train-fold-a-v1`, composed `5c0466b89f8675086825cbb7ea255d94f146b91ead4e373a66e5792c30fa817a`, protocol `bfb4ddcf1a0d5c50d25d086a989627dbed810a2c3e8274760103e04fece2084c` |
| B7c smoke | `SAEA-SLURP-NATIVE-NCP-L1-TOOL-OBS-ANCHOR-SMOKE-4-V1` / `attempt-slurp-native-ncp-l1-tool-obs-anchor-smoke-4-generation-v1`, cell `slurp-native-ncp-l1-tool-obs-anchor-smoke-4-v1`, composed `46e3dd74c39b13deda4953bb7e09f04f25efa0dbcf9ae2c489afe1500780ae79`, protocol `bfa9dc7a4cf68b6d83e5df1774e50cdaf765ef94e09c2e6591403d5aaff05292` |
| comparator, primary | **cell B7a's sealed bytes**, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1`, composed `208e5dba419a8d20b2b83667d700620a77c639303ca08b439b1154d7eb204542`, protocol `f90dd1b2d370795ff438bc53db593057cef98a3bf4336e3d62f905d7b5ed735d`. **B7a has not flown.** Its score artifact and run manifest SHA-256 are `PENDING_B7A_SEAL` in both analysis recipes and are filled in from B7a's own seal. **Both cells fly only after B7a seals and is read not HARMFUL.** |
| comparator, secondary | sealed bytes of the released TRAIN A direct anchor `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`, score SHA-256 `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38`, run manifest `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e`, official pooled SLU-F1 33.89 / intent 73.70 / scenario 82.69 / action 75.09 / span 21.10 |

For context only, never as either cell's comparator: the sealed dual-store anchor
`SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` (score SHA-256
`7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, SLU 48.53 / intent 77.96), which
is B7a's own base and the source of every contact-free measurement in section 3.

No comparator is ever re-flown or re-scored. All arms share the roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json` (SHA-256
`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never
spawn). Each four-row smoke uses the four already-exposed TRAIN A engineering rows (split identity
`4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`).

**No twin is registered.** A derangement or token-matched control for either cell flies only if that
cell shows a positive CI95 against B7a, by the program's twin rule.

## 3. The one factor of each cell, and the four things each deliberately is not

The moved key in both cells is `native_episode.context_policy`, the third key of the closed `episode`
switch-class allowlist (`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`). The OFF arm of each is
**cell B7a's configuration**, not the key's absence.

### 3.1 B7r: the review-finding producer format

**ON, as this cell declares it:**

- `native_episode.context_policy.producers = {"review-finding": {"response_format_id":
  "saea-review-findings-v1"}}` — the only sub-block that moves
  (`context_policy_key_diff_vs_b7a` = `["producers"]`);
- `phase_material.reviewer.response_format_id = "saea-review-findings-v1"`, because
  `rails.native_episode_config.load_native_episode_config` refuses a `producers` block whose declared
  format differs from the producing phase's;
- consequently the phase program id moves from `phase-native-candidates-review-revise-v1` to
  `phase-native-candidates-review-revise-findings-v1`: the **same four phases, the same purposes and
  `knowledge` values, the same episode shape and the same contact ceiling 11**, with only the
  Reviewer phase's `response_format_id` declared. `rails.phase_material.load_phase_material_specs`
  states the reason — *a phase's output contract has exactly one authority*. This is the mechanical
  carrier of the same factor and is recorded as **deviation 1**.

`saea-review-findings-v1` is `rails.review_findings`'s own registered contract, minus the
`uniqueItems` keyword constrained decoding does not express, so a response generated under it
satisfies `parse_review_findings` by construction and the parser stays the authority on the rules the
schema cannot state.

**Four things B7r is not.** (1) No tool-observation rewrite — the four tool-observation boundaries
stay `raw`; that is B7c. (2) No cleaning contact — level L2 is B7b. (3) **No Reviewer instruction
change**: the Reviewer keeps `probes/slurp_native_role_reviewer_v1.txt`, the anchor's prose
instruction that asks for one task-contract tool call and concise findings. Only the output
**contract** moves; swapping in `probes/slurp_native_role_reviewer_findings_v1.txt` would be a second
factor and is not done here. (4) No knowledge, supply, store, roster, geometry, boundary-template or
scorer change.

### 3.2 B7c: the tool-observation rewrite

**ON, as this cell declares it:** the four `<role>:tool-observation` boundaries at
`{"level": "structured", "template": "probes/ncp_slurp_tool_observation_v1.txt",
"on_parse_failure": "raw"}` — the only sub-block that moves
(`context_policy_key_diff_vs_b7a` = `["boundaries"]`).

`rails.node_context_policy.parse_tool_observation` refuses the rewrite unless the envelope is a
`task_contract` result **and** its contract is provably a substring of that request's own system
message, so the replacement removes a repetition and never a fact. A Reviewer's own live tool chain
keeps its bytes (`raw_reason: "live-tool-chain"`), as does the native tool-call source turn; the
rewrite is confined to REPLAYS, exactly as design section 6 point 3 states. The template carries no
`UNPARSED` block, so a parse failure hands the consumer the sealed state itself.

**Four things B7c is not.** (1) No producer response format — that is B7r. (2) No cleaning contact —
that is B7b. (3) No change to the eight model-output boundaries, their templates or their
`on_parse_failure` rules. (4) No knowledge, supply, store, roster, geometry, instruction-template or
scorer change.

### 3.3 What actually changes in the request, proved contact by contact

Receipt: `SPEECHRL_DATA_DIR/coordination/slurp-b7rc-ncp-anchor-v1/request-channel-proof-v1.json`
(SHA-256 `e0b5023a700ed7d6f2801588764c97c028d41dbf0d55f7f1b2768ebf78e25a09`).

All **5,417** sealed `MODEL_REQUEST` payloads of the dual-store anchor recovery run were read
read-only. For each one, its exposed agent-state list was rebuilt as `AgentStateArtifact` values, the
registered policy's own `compile(...)` was applied **twice** — once with **cell B7a's** bound policy
and once with the cell under test — with that contact's own sealed inputs (role kind, phase ids,
sample id, the control envelope's `local_tool_result_ids`, the speech packet id plus every
`supplied_evidence` id, the system message, the contact's own `Native episode limits` block and the
episode's action set), and **both** renderings were produced through the production renderer
`core.model.transport._speech_history_texts`. **Zero rows failed, zero contacts were unmatched, and
every contact matched its sealed native contact-fit receipt.**

**B7r against B7a's registered render.**

| quantity | value |
| --- | ---: |
| requests byte-identical to B7a's render | **5,417 of 5,417** |
| boundary rows identical | **13,102 of 13,102** |
| agent states differing | **0** |
| control envelopes identical | 5,417 of 5,417 |
| non-agent-state history parts identical | 5,417 of 5,417 |

Given the anchor's own upstream bytes the compiled render **does not move at all**. The static
differences are therefore exactly two, and both are quantified:

1. **A decoding parameter, not prompt text.** `rails.runner.speech_binding` writes the resolved
   format into `decoding_params.response_format`; it never enters `task_instruction`, the evidence
   blocks, the speech parts or the rendered history. The document is **898 characters** (SHA-256
   `4e2c339162937b0f2d4c98c13b5bde6474cb81a9cbcf36acd0e1d63aee3b8d29`) and rides the **2,167**
   Reviewer contacts.
2. **A provenance string.** `rails.runner` seals every phase state and control envelope under the
   program id, so in a **live** B7r flight each rendered agent-state id and control contact id
   carries `phase-native-candidates-review-revise-findings-v1` (49 characters) instead of
   `phase-native-candidates-review-revise-v1` (40): **+9 characters per occurrence**, a median of
   **4** and a maximum of **14** occurrences per contact, **26,120** occurrences over the run
   (**+235,080 characters**, +0.11 % of the run's wire text). A program id carries no task content,
   no knowledge and no gold.

**The third difference cannot be shown model-free and is not claimed to be small.** At dispatch the
Reviewer generates under a constrained JSON contract, so on the rows whose output parses the
`planner:review-finding` and `solver:review-finding` blocks render findings instead of the
FALLBACK-RAW block, and the Reviewer's own text changes. **No contact-free method can produce those
bytes.** The four-row smoke reads the rejection rate and the block form; the flight's own
`saea-node-context-policy-v1` receipts carry the rate on all 1,080 rows.

**B7c against B7a's registered render.**

| quantity | value |
| --- | ---: |
| requests byte-identical to B7a's render | 4,320 of 5,417 |
| requests differing | **1,097** |
| tool-observation rows total | 2,184 |
| rows rewritten (replays) | **1,102** |
| rows left `raw`, `raw_reason: live-tool-chain` | **1,082** |
| contract chars replaced per rewritten row | **5,424** |
| reference block chars per rewritten row | **161** |
| rendered delta per rewritten row | **-6,033** |
| rendered delta over the run | **-6,648,366** |
| rows where the contract was a substring of that request's own system message | **1,102 of 1,102** |
| control envelopes identical | 5,417 of 5,417 |
| non-agent-state history parts identical | 5,417 of 5,417 |
| model-output boundary rows changed | **0 of 7,624** |

Per rewritten row the policy replaces a **5,424-character** contract with a **161-character**
reference and re-serializes the envelope, so the rendered state shrinks by **6,033** characters —
larger than the raw 5,263-character difference because the contract's JSON-escaped form is longer
than its plain text. The delta is uniform: min = median = max = -6,033. Against B7a's own rendered
total (the anchor's 206,799,138 wire-text characters plus B7a's measured +1,572,264 = 208,371,402)
that is **-3.19 %**; against the sealed anchor it is **-2.45 %**.

Per role: planner 1,087 rows on 1,082 of 1,085 contacts (median history delta **-6,033**, minimum
-12,066 where the Planner holds two replays), reviewer 10 rows on 10 of 2,167 contacts, solver 5 rows
on 5 of 1,085 contacts, perception 0 of 1,080. The 1,082 rows the policy leaves alone are the
Reviewer's own live chain, and the 2,184 `native-tool-call-source` rows and 1,110
`boundary-not-declared` rows are unchanged from B7a's own counts.

*What provably does not change in either cell.* Both policies are transforms over the exposed
agent-state list only: they return a tuple of the same length and order and never read or return the
system message, the `supplied_evidence` items, the speech packet parts, the tool schemas or the
decoding parameters. `task_instruction` is an INPUT to the tool-observation renderer and is never
rewritten. Every non-agent-state history part is byte-identical on 5,417 of 5,417 contacts in both
cells.

## 4. Metrics

**Primary: official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded. **Guard: intent (joint scenario+action) accuracy.**

Secondaries: intent accuracy, scenario accuracy, action accuracy, official pooled span F1, per-row
mean official SLU-F1, per-row mean exact slot F1, and the saves/harms/ties table with the exact
two-sided McNemar p. **Projection v3 (`slurp-slu-official-projected-v3-train`) is reported beside
every official number** (owner decision 7 of 2026-09-17).

**The symmetric-normalised scorer.** Owner decision 14 of 2026-09-17 registers a TRAIN sibling of
`slurp-slu-f1-normalized-v1`, and a sibling is being registered in parallel with this package. The
rule is therefore conditional and fixed here: **if a registered TRAIN symmetric scorer is available
at read time, it supplies the symmetric-sign clause of section 6; else the clause is NOT EVALUABLE on
this roster, projection v3 is the agreement reading, and the substitution is recorded as deviation
2.** No sibling is forced onto the TRAIN roster.

Mandatory diagnostics:

- the flight's own `saea-node-context-policy-v1` receipt aggregate per boundary — rows, parsed,
  malformed, fallback applied, median rendered chars — against the contact-free expectation of
  section 3.3;
- **B7r:** the findings rejection rate under `rails.review_findings.parse_review_findings` against
  the sealed anchor's 2,167 of 2,167, and whether the Reviewer still issues its task-contract tool
  call under the constrained output contract (a count of native task-contract calls against B7a's);
- **B7c:** the realized wire-text reduction against this package's measured -6,648,366 characters,
  and the 1,102 rewritten / 1,082 `live-tool-chain` split;
- the per-scenario intent table over all 18 scenarios, natural mixture and equal weighting;
- **net harmed rows per scenario, with any scenario of five or more flagged** (owner decision 17 of
  2026-09-17). New in this package relative to B7a, and carried by every paired read from here on;
- the per-contact prompt-token delta from the cell's own sealed native contact-fit receipts.

`delta = arm minus cell B7a`, in percentage points; a negative delta means the arm is worse.

## 5. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence. Sensitivity:
paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries the per-scenario
table over all 18 scenarios in both the natural-mixture and the equal-scenario weighting, the
equal-scenario delta reported beside the natural-mixture point estimate and never replacing it, and
the net-harmed-rows-per-scenario table of section 4. Speaker clusters come from the released roster
metadata (125 speakers, 18 scenarios of 60 rows, 523 headset and 557 far-field rows).

## 6. Decision rule (fixed before contact)

Null half-widths are the **TRAIN A own null measured by cell B0r** on this exact roster and geometry:
**h_SLU = 1.1218 pp**, **h_intent = 1.0051 pp** at CI95 (0.9420 / 0.8505 at CI90).

Design section 11's B7a rule is adapted in exactly two declared ways — the comparator moves from the
sealed anchor to **cell B7a's sealed bytes**, and the NEUTRAL consequence is narrowed by design
section 15 resolution 5 — and in no other way:

> **ADMITTED** iff the primary official SLU CI95 lower bound is > 0 against **cell B7a**, intent is
> non-inferior at the own null margin 1.0051 pp, the symmetric-normalised scorer agrees in sign, and
> no scenario loses intent beyond the null band. **NEUTRAL** iff both primary metrics are
> non-inferior within the own null margins (SLU 1.1218, intent 1.0051). **HARMFUL** otherwise.

Operationalised, with nothing added:

- **primary**: the CI95 lower bound of the pooled official SLU micro F1 delta against cell B7a's
  sealed score artifact is greater than 0;
- **intent guard**: non-inferior at 1.0051 pp (its CI95 lower bound above -1.0051);
- **scenario harm**: a scenario loses intent beyond the null band when the CI95 upper bound of that
  scenario's own paired intent delta is below zero. Roster-level scenario and action margins stay
  diagnostics for the per-scenario table, not gates. **Net harmed rows per scenario is reported for
  every scenario and any scenario with five or more is flagged; the flag is a diagnostic the verdict
  must carry, not an additional gate** (owner decision 17 of 2026-09-17);
- **the symmetric-normalised clause** is evaluated with the TRAIN sibling of
  `slurp-slu-f1-normalized-v1` **if one is registered at read time**; otherwise it is NOT EVALUABLE,
  is replaced by the projection-v3 agreement clause (`slurp-slu-official-projected-v3-train` must
  agree in sign with the unprojected primary), and the substitution is recorded as deviation 2;
- **NEUTRAL and the default plan.** Design section 15 resolution 5 fixes that a NEUTRAL B7r/B7c/B7b
  enters the SLURP default plan **only if it lowers cost**. Applied here before contact:
  - **a NEUTRAL B7c ENTERS the default plan**: it removes a measured 6,648,366 characters of
    duplicated task contract (-3.19 % of the run's wire text, 1,102 rewritten replays) at no measured
    quality cost, and the reduction is proved contact by contact in section 3.3;
  - **a NEUTRAL B7r DOES NOT enter the default plan**: a constrained Reviewer output contract lowers
    no cost. It adds an 898-character decoding parameter on 2,167 contacts, it adds no contact and
    removes none, and its only cost argument would be a prompt reduction at the review-finding
    boundary that this registration does not predict and cannot measure without a contact. An
    ADMITTED B7r enters the plan on its measured gain, as any admitted module does;
- **HARMFUL** consequence: a HARMFUL cell does not enter the default plan, and its successor in the
  queue order B7a -> B7r -> B7c -> B7b does not fly on its base (owner decision 15 of 2026-09-17).

No repeat-to-pass: each verdict is read once, from the single official score of that cell's complete
manifest.

## 7. Cost reporting (mandatory in every verdict)

- actual generation contacts, against cell B7a's realized count and the registered ceiling of 11 per
  row, 11,880 per cell (the sealed anchor realized 5,417, 5.016 per row);
- contacts per row — **neither cell adds a contact**: B7r moves one declaration inside the same
  zero-contact policy and B7c moves four boundary levels;
- actual repeated speech seconds, against the anchor's realized 15,459.76 and the registered ceiling
  11 x 3,084.528 = 33,929.8, registered as 33,930;
- actual FIT endpoints, expected 4 per realized contact, ceiling 47,520;
- actual native task-contract tool calls, ceiling 6,480 — **for B7r this is also a diagnostic**, see
  section 4;
- GPU hours read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`) over
  the lease window, never a wall-clock guess, against the anchor's measured 3.388;
- mean latency, slot occupancy and duty cycle from the same monitor;
- the prompt-token delta against cell B7a, from the cell's own sealed native contact-fit receipts;
- **for B7c**: the realized wire-text reduction against this package's measured -6,648,366
  characters.

Registered ceilings, which are bounds and not targets, per cell: **11,880 generation calls, 47,520
FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native
task-contract calls**, one official complete scoring job, zero ASR, encoder and paid-API calls. Per
smoke: **44 generation calls, 176 FIT endpoints, 117 repeated speech seconds, 1.0 GPU hours, 24
task-contract calls**, zero scoring jobs. These are the anchor's and cell B7a's own ceilings,
unchanged.

## 8. Prompt fit

Receipt: `prompt-fit-v1.json` (SHA-256
`e2b341157699a8552a45797144cd530dd46a2d85a247f929eedd1bc1941f5e35`). Slot **24,576** tokens; decision
**ALLOW** for every phase of both cells.

The bound is the sealed dual-store anchor's own **5,417 native contact-fit receipts** — each realized
contact's own `required_tokens` — plus that same contact's measured node-context **word** delta
against the sealed L0 rendering under the repository's stated proxy
(`analysis.slurp_slot_vocabulary.TOKEN_PROXY_FACTOR` = 1.3). Every one of the 5,417 contacts was
matched to its fit receipt; none was unmatched.

| cell | phase | contacts | anchor max required | word delta (min / median / max) | max bound | min margin |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| B7r | perception | 1,080 | 4,270 | 0 / 0 / 0 | 4,270 | 20,306 |
| B7r | solver | 1,085 | 13,482 | -18 / +2 / +50 | 13,544 | 11,032 |
| B7r | reviewer | 2,167 | 15,374 | +8 / +32 / +68 | 15,447 | 9,129 |
| B7r | planner | 1,085 | 15,382 | +24 / +82 / +165 | 15,593 | **8,983** |
| B7c | perception | 1,080 | 4,270 | 0 / 0 / 0 | 4,270 | 20,306 |
| B7c | solver | 1,085 | 13,482 | -509 / +2 / +36 | 13,482 | 11,094 |
| B7c | reviewer | 2,167 | 15,374 | -500 / +32 / +68 | 15,374 | 9,202 |
| B7c | planner | 1,085 | 15,382 | -950 / -474 / +82 | 15,382 | **9,194** |

B7r's static bound is cell B7a's bound exactly, because the rendered history does not move; B7c's is
at or below B7a's on every contact, because the policy removes a bounded repetition and adds nothing.
**B7r's bound is a static bound, not a live one**: in a live flight the Reviewer generates under a
constrained contract, so the review block changes on the rows that parse. The findings rendering
replaces the FALLBACK-RAW block (header plus the Reviewer's verbatim bytes) with a bounded
header/verdict/issues/citations block whose size the registered schema caps (at most two findings,
rationale at most 240 characters, at most three evidence ids of at most 160 characters,
`remaining_uncertainty` at most 240 characters), so the live delta is bounded above by roughly 1,700
characters on a boundary whose B7a rendering already carries the whole review — inside the 8,983
tokens of margin by a wide factor. Each flight still fits every realized request itself through
`build_native_contact_fit_gate`, and the coordinator reads those receipts.

Independently, `core.flight.cli check` ran its own model-free budget over the widest request each
phase renders across the whole roster and returned **ALLOW for every phase of all four cells**: B7r
perception 19,186 required window tokens, reviewer 19,050, planner 18,989, solver 19,229 (smoke
19,186 / 19,049 / 18,988 / 19,228); B7c 19,184 / 19,047 / 18,987 / 19,227 (smoke 19,183 / 19,047 /
18,986 / 19,226). Every one carries an operational margin above 5,347 tokens. That estimate unions
every candidate envelope and is deliberately more conservative than the per-contact bound above; both
are recorded and neither replaces the other.

## 9. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration; a second failure closes that flight and the fix must be
proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke stops its
cell until the fix is proven on that same four-row roster. One experiment in flight at a time.

## 10. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed discovery
  roster.
- **Nothing about cell B7a's own verdict.** B7a has not flown; if B7a is HARMFUL neither cell flies,
  and no number in this document is evidence for or against B7a.
- **B7r claims nothing about what the Reviewer's constrained output SAYS**, only about what the loop
  does with a parseable one. Whether the constrained contract suppresses, preserves or degrades the
  Reviewer's own task-contract tool call is an open question read at the smoke (section 12, open
  decision 2), not a prediction.
- **B7c claims nothing about the removed duplication having been harmful.** It removes a measured
  repetition; whether that helps is exactly what the cell measures.
- No per-boundary attribution inside cell B7a, which moved eight boundaries together.
- Nothing about level L2 (B7b), Fold B, DEV-1000 or the test split; they stay unread.
- The audit's counts (2,167 unparsed reviews, 13,634,712 duplicated characters) bound what each cell
  can touch; they are never predicted gains.
- A structural smoke result is never a quality result.

## 11. Deviations recorded before contact

1. **B7r's factor is carried by a new phase-program id.**
   `rails.phase_material.load_phase_material_specs` refuses a `phase_material` response format that
   disagrees with the program's own PhaseSpec — *a phase's output contract has exactly one authority*
   — and `rails.native_episode_config` refuses a `producers` block that disagrees with the producing
   phase. Declaring the Reviewer format therefore requires
   `configs/policy/phase-native-candidates-review-revise-findings-v1.json` plus its registration in
   `rails.controllers._PROGRAM_CONFIG_FILENAMES` / `AGENT_CONTROLLERS` and its shape entry in
   `tests/unit/test_rails_controllers.py::_EXPECTED_PROGRAM_SHAPES`. The new program is the existing
   one with one field changed; its phases, purposes, `knowledge` values, `stop_rule` and
   `max_contacts` are identical, and the repository's own precedent for a program variant
   (`phase-native-candidates-solve-v1`, `-samples5-v1`, `phase-native-review-revise-json-v1`) is a
   new id and a new file, never a flag. The visible consequence is measured in section 3.3: +9
   provenance characters per rendered state id. **If the coordinator wants the factor carried some
   other way, that is a code change and a new registration, not an edit of this one.**
2. **The symmetric-normalised clause is conditional.** Section 4 and section 6. If no TRAIN sibling
   of `slurp-slu-f1-normalized-v1` is registered at read time the clause is not evaluable and
   projection v3 is the agreement reading, exactly as the B4 and B7a packages recorded it.
3. **No `wire-check` stage** on any of the four cells, exactly as the sealed anchor, cell B0, cell B1,
   the B4 cells and cell B7a declare none: `FlightRuntime._dispatch_phase_program` refuses a native
   episode whose transport is not the real shared speech renderer, and `wire_check` installs a text
   transport double. The contact-by-contact request-channel proof of section 3.3 is the contact-free
   substitute and is stronger per contact.
4. **B7r's request-channel proof is static.** It proves that the compiled render does not move given
   the anchor's own upstream bytes. It cannot prove what the Reviewer generates under the constrained
   contract; section 3.3 says so and the smoke reads it. This is a limit of the method, recorded
   rather than hidden.
5. **The four tool-observation boundaries stay DECLARED** in both cells — `raw` in B7r, `structured`
   in B7c — rather than left undeclared, so each emits one receipt row per contact and the
   byte-identity claim stays a checked statement.
6. **Registered hashes are pre-flip.** Section 12.
7. **The smoke reference artifact.** Neither cell's preparation has a four-row artifact of its own, so
   each smoke's `output` block is compared against the review-off four-row artifact AND, row by row,
   against the sealed anchor's own rows for the same four sample ids; both agree.

## 12. Open decisions for the coordinator

1. **Does the coordinator accept the new phase program as the carrier of B7r's factor?** Deviation 1.
   The alternative is a code change that lets `producers` declare the format without a program
   variant, which E8a did not build.
2. **Does the constrained output contract survive the Reviewer's tool-calling turn?**
   `rails.runner.speech_binding` writes `decoding_params.response_format` for **every** turn of the
   role, and the Reviewer's first turn is required by its instruction to call the task-contract tool.
   Whether llama.cpp's grammar and its `tools` rendering compose on that turn is **not knowable
   model-free** and is the first thing the four-row smoke must show. If the Reviewer stops calling
   its tool, the cell has moved two things and must be re-registered, not reinterpreted.
3. **Registered hashes are pre-flip.** Section 13.

## 13. Registered hashes are pre-flip

Every composed and protocol hash above is the value of the four config fragments **exactly as
committed at the registration commit** `8b6b0c0b`: readiness `held`, the preparation requirement
present, `prepared_phase_supply` pinned. `core.config.compose` hashes the whole merged four-fragment
document, so flipping readiness to `ready` and appending the coordinator's own decision requirement
each change the composed hash and therefore the protocol hash. Re-pin with `core.flight.repin` (the
runbook's section 2 gives the exact command) and re-pin this package and the eight exposure-ledger
notes before launch. The method was verified on this tree twice: composing cell B7a's own fragments
reproduces its registered protocol hash
`f90dd1b2d370795ff438bc53db593057cef98a3bf4336e3d62f905d7b5ed735d`, and composing
`slurp-native-dual-store-train-fold-a-anchor-v1` as both baseline and experiment reproduces the
sealed anchor's `d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

## 14. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b7rc-ncp-anchor-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads. Index: `INDEX-v1.json`.

| receipt | SHA-256 |
| --- | --- |
| `check-b7r-full-v1.json` | `eb2ad3db9980e6b068d7b17cb4172098fb21e51ad8a1e8681f8febb9d6fb8809` |
| `check-b7r-smoke-v1.json` | `7b6b150528ce07b10c1ede531d5ce42227f6799c63ab5267ce91ab7c1819f2a0` |
| `check-b7c-full-v1.json` | `1a3d1735be00d9055837527ecf240b40b1c119914bfd7237221a3b0c01ba7afb` |
| `check-b7c-smoke-v1.json` | `ea6bf383a0ef12cc24ec1458293e9d256015ccc6f6cff143c47a5075a6b347e7` |
| `phase-supply-vs-anchor-v1.json` | `46f09a5d9282c200f2b206062238f6f639613c6ca3812ac7d0afeb934cd21887` |
| `request-channel-proof-v1.json` | `e0b5023a700ed7d6f2801588764c97c028d41dbf0d55f7f1b2768ebf78e25a09` |
| `prompt-fit-v1.json` | `e2b341157699a8552a45797144cd530dd46a2d85a247f929eedd1bc1941f5e35` |
| `containment-v1.json` | `67b78676c847b0c37f9780b20d4cfc09a0a825f7b0fa0b6b62979d46b46014b0` |
| `composed-hashes-v1.json` | `eeb2f42e20a10197f280343fe40a5232f9266a69815527645c4f78d87ad36cf4` |
| `plan-hashes-v1.json` | `fc2fa742532ef59cbcc43ae7535fa170c360ebfb0e7bc0b7cc1491139e113dfa` |
| `ledger-parse-v1.json` | `06e84990fe0ed3b44a280c72e28da81ca8e4a1f72f98537bebc42502c3fd8f00` |

Prepared supply: all four cells' Perception artifacts carry an `output` block **byte-identical** to
the sealed anchor preparation's (`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`)
on **1080 of 1080** rows and to the four-row reference
(`512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733`) on **4 of 4**, and each row's
selection equals the anchor's own row. The Perception selection channel does not move in either cell.

Containment: **0 collisions**, verbatim and casefolded, between the protected material of both bound
snapshots (`intent-boundaries-v1` 120 items, `slot-contracts-v1` 108 items) and every one of the five
control turns the base sends **and** all seven committed node-context templates these cells render
(B7c renders `probes/ncp_slurp_tool_observation_v1.txt`, which B7a does not), under the runtime rule
`rails.runner._assert_agent_control_excludes_knowledge_payloads` at its floor of 8 characters.

Ledger: `contracts.ledger._parse_ledger_tables` sees all eight rows exactly once, each
`consumed = no`; 916 rows parsed in total.

All four `check` receipts were produced at the registration commit `8b6b0c0b` that carries every
config, plan and ledger row these cells fly, and each reports `study_commit` equal to it,
`generation_authorized` false, readiness `held`, and runtime-derived `config_hash` and
`protocol_hash` equal to the registered ones. The documentation commit that follows changes no
config, no plan and no ledger row, and `plan-hashes-v1.json` deliberately excludes this document and
the runbook for that reason.

## 15. What this package does not authorise

No readiness flip, no model contact, no default-plan edit and no harness-admission entry. The
admission entries for the modules "node context policy review-finding producer format" and "node
context policy tool-observation rewrite" are written from the sealed verdicts, never from this
registration; the runbook records the expected entry shapes so the coordinator can check them against
the switch rule before writing them. Neither cell opens before cell B7a seals and is read not
HARMFUL.
