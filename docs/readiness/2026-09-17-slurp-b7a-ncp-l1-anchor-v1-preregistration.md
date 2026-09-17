# Cell B7a on the sealed anchor: the Node Context Policy at level L1, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B7a registration agent, worktree
`/home/chao/saea-worktrees/fable-b7a`, branch `fable/b7a`, base commit `ff668547` (the merge of
engineering item E8a). Authority:
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` (sections 3-6 and 8-11, and the
E8a paragraph of section 6), `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`
section 3 (module M5) and section 5, the evidence base
`docs/results/2026-09-17-slurp-node-context-audit-v1.md`, and the coordinator resolutions of
2026-09-17 recorded in section 3 below. This document grants no model contact; both cells stay
readiness `held` until the coordinator flips them.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried, and no worker, campaign,
smoke or FIT was run.

## 1. Question

Does replacing the raw hand-off of upstream model text at every declared node boundary with a
parsed, normalised, hash-pinned per-node rendering -- the Node Context Policy at level L1
`structured`, zero extra contacts -- raise pooled official SLU micro F1 on TRAIN Fold A without
harming intent?

The audit fixes what the cell is answering against. In the sealed anchor there is exactly one
node-boundary admission test (`bool(output.strip())`) and one rendering template
(`[agent state {state_id} kind={state_kind}] {content}`) applied to the upstream model's own bytes.
Seven Solver drafts that do not parse as the task answer were passed verbatim to the Reviewer and
the Planner and accepted by all seven Planners; 2,167 of 2,167 Reviewer outputs fail the
repository's own registered findings parser; the Planner spends 25.0 % of the run's prompt budget to
emit a median of two tokens.

## 2. Arms

| role | identity |
| --- | --- |
| B7a | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1` / `attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-v1`, cell `slurp-native-ncp-l1-anchor-train-fold-a-v1`, composed `c46ce941af01d5bf98f9f04a9a8a2bb10b7108a74bd54850f814f42674d7a032`, protocol `f67eb9bc5e9ff23ff3b0cdcd9efa338163feaa732a1e9ff3e94cd7f2619ddded` |
| B7a smoke | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V1` / `attempt-slurp-native-ncp-l1-anchor-smoke-4-generation-v1`, cell `slurp-native-ncp-l1-anchor-smoke-4-v1`, composed `0fbb9f0001f8d11fbd8459b0a7dfd55f85833f75e4db38895bf1b028f095a8a2`, protocol `deeeba71ceb627efaaeaf46ace94e4eeefebeed5876eb98ae826ca712a814f1b` |
| comparator, primary | sealed bytes of `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`, score SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152`, official aggregate pooled SLU-F1 48.53 / intent 77.96 / scenario 84.81 / action 79.26 / span 29.50 |
| comparator, secondary | sealed bytes of the released TRAIN A direct anchor `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`, score SHA-256 `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38`, run manifest `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e`, official aggregate pooled SLU-F1 33.89 / intent 73.70 / scenario 82.69 / action 75.09 / span 21.10 |

Neither comparator is ever re-flown or re-scored. Both arms share the roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json` (SHA-256
`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never
spawn). The four-row smoke uses the four already-exposed TRAIN A engineering rows (split identity
`4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`).

The L1 derangement twin of design section 10 is **not registered here**: by the program's twin rule
it flies only if B7a shows a positive CI95 against the anchor.

## 3. The one factor, and the four things it deliberately is not

The moved key is `native_episode.context_policy`, the third and last key of the closed `episode`
switch-class allowlist (`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`). Its OFF arm is the key's
absence, which is exactly the sealed anchor fragment.

**ON, as this cell declares it** (coordinator resolution, Fable 5.1, 2026-09-17):

- `level: "structured"`, `policy_id: "typed-slurp-node-context-v1"`;
- `params`: `max_candidates` 3, `projection_policy`
  `bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1`, the closed
  `draft_response_schema` (the same contract `rails.role_context` already validates), and
  `legal_entity_types` = the 55 SLURP ontology entity types **exactly as this fragment's own
  `task_instruction_fill` `slurp-label-inventory` renders them** into the system message every role
  already reads (see section 5);
- `boundaries`: the **eight model-output boundaries** of design section 3 at `structured` --
  `solver:candidate-hypothesis`, `reviewer:candidate-hypothesis`, `reviewer:current-draft`,
  `planner:current-draft`, `solver:current-draft`, `planner:review-finding`,
  `solver:review-finding`, `solver:plan-action` -- each with `on_parse_failure: "raw"` except
  `solver:plan-action`, which declares `"refuse"` exactly where the harness already refuses an
  unregistered action token; and the **four tool-observation boundaries** declared `"raw"`.

Each structured boundary renders through its committed, hash-pinned template under
`configs/probes/ncp_slurp_*.txt`; six distinct template files serve the eight boundaries.

**Four things this cell is not**, each a separate later one-factor cell:

1. **No Reviewer producer response format.** The Reviewer stays prose, so the
   `planner:review-finding` and `solver:review-finding` boundaries render their **FALLBACK-RAW**
   block on every row -- the header plus the source content in a labelled `UNPARSED` section. That
   is the honest description of what the Planner is given, and it is measured in section 4: 100 %
   of rows. Giving the Reviewer a `response_format_id` is cell **B7r**.
2. **No tool-observation rewrite.** The duplicated task-contract reference line of design section 6
   is cell **B7c**; here all four tool-observation boundaries are declared `raw` and the Reviewer's
   live tool chain and every later replay of it keep the anchor's bytes.
3. **No cleaning contact.** Level L2 (`cleaned`) is E8b, refused at load time with `E8b not
   implemented`; it is cell **B7b**, and it flies only if B7a is ADMITTED or NEUTRAL.
4. **No knowledge, supply, store, roster, geometry, instruction-template or scorer change.** Both
   knowledge stores stay at v1 with their release/snapshot pins and their supply geometry; the
   review loop stays on (`max_revisions` 1, reviewer `max_iterations` 3, program ceiling 11
   contacts); the Reviewer-only task-contract tool authority, Solver-only answer authority, the
   three-candidate contract and every instruction template are the anchor's.

Held identical against the sealed anchor: the roster and split, the model fragment and resident
geometry, the promoted EVO-FOLDS-V2 speech packets, both knowledge stores, the full native episode,
every instruction template, and the scorers. The cell carries its own `native_contact_fit` identity,
its own speech-feature identity strings (provenance only, never model-visible) and its own prepared
phase supply, none of which is a channel the model can see. Fold B is absent.

### 3.1 What actually changes in the request, proved contact by contact

Receipt: `SPEECHRL_DATA_DIR/coordination/slurp-b7a-ncp-l1-anchor-v1/request-channel-proof-v1.json`
(SHA-256 `52638c76e5f5ee1558575d325702afd479bbb5fc78a499a5463b27e85168af50`).

All **5,417** of the sealed anchor's `MODEL_REQUEST` payloads were read from the run's own trace,
read-only. For each one, its exposed agent-state list was rebuilt as `AgentStateArtifact` values
from the sealed history, the registered policy's own `compile(...)` was applied with that contact's
own sealed inputs -- role kind, phase ids, sample id, the control envelope's
`local_tool_result_ids`, the speech packet id plus every `supplied_evidence` id, the system message,
the contact's own `Native episode limits` block and the episode's action set -- and both the sealed
and the rewritten history were rendered through the production renderer
`core.model.transport._speech_history_texts`. **Zero rows failed and zero contacts were unmatched.**

*Perception.* **1080 of 1080 Perception requests are byte-identical**: a Perception contact carries
no agent state at all, so the policy has nothing to transform.

*Solver, Reviewer and Planner.* They differ only in the agent-state parts the policy rewrites:

| role | contacts | agent states | states rewritten | history char delta (min / median / mean / p95 / max) |
| --- | ---: | ---: | ---: | --- |
| perception | 1,080 | 0 | 0 | 0 / 0 / 0 / 0 / 0 |
| solver | 1,085 | 1,110 | 1,100 | -150 / **-30** / +25.65 / +105 / +704 |
| reviewer | 2,167 | 6,548 | 4,344 | +132 / **+299** / +322.05 / +439 / +602 |
| planner | 1,085 | 5,444 | 2,180 | +466 / **+774** / +780.23 / +813 / +1,576 |

Total rendered-history growth over the whole run is **+1,572,264 characters on 206,799,138 wire-text
characters, +0.76 %**. The Solver's median is **negative**: the candidate-hypothesis template is
more compact than the raw Perception JSON it replaces.

The states a role sees but the policy leaves raw are named in the receipt rows: **1,110**
`boundary-not-declared` (1,090 Planner readings of the Perception state, which the design's boundary
table deliberately does not declare, and 20 revising-Reviewer readings of a plan-action or an
earlier review state), **2,184** `native-tool-call-source` (the Reviewer's own tool-calling turn,
whose bytes the framework verifies against its source authority -- 1,092 of them read by the
Reviewer itself at an undeclared boundary and 1,092 by the Planner or the revising Solver at a
declared `review-finding` boundary) and **1,082** `live-tool-chain` (a Reviewer's own replayed
observation inside its framework contract).

*Per boundary, on the anchor's own sealed outputs:*

| boundary | rows | structured | parsed | malformed -> FALLBACK-RAW | raw rows | rendered char delta (min / median / max) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `B-CAND-SOL` | 1,085 | 1,085 | 1,085 | 0 | 0 | -150 / -30 / +188 |
| `B-CAND-REV` | 2,167 | 2,167 | 2,167 | 0 | 0 | -148 / -28 / +190 |
| `B-DRAFT-REV` | 2,177 | 2,177 | 2,163 | **14** | 0 | +215 / +290 / +338 |
| `B-DRAFT-PLAN` | 1,090 | 1,090 | 1,083 | **7** | 0 | +240 / +541 / +589 |
| `B-DRAFT-SOL` | 5 | 5 | 5 | 0 | 0 | +248 / +279 / +280 |
| `B-REVIEW-PLAN` | 2,177 | 1,090 | 0 | **1,090 (100 %)** | 1,087 | +226 / +227 / +235 |
| `B-REVIEW-SOL` | 10 | 5 | 0 | **5 (100 %)** | 5 | +225 / +226 / +233 |
| `B-PLAN-SOL` | 5 | 5 | 5 | 0 | 0 | +234 / +235 / +242 |
| `B-TOOL-REVIEWER` | 1,092 | 0 | n/a | n/a | 1,092 | 0 |
| `B-TOOL-PLANNER` | 1,087 | 0 | n/a | n/a | 1,087 | 0 |
| `B-TOOL-SOLVER` | 5 | 0 | n/a | n/a | 5 | 0 |
| undeclared `(planner, candidate-hypothesis)`, `(reviewer, review-finding)`, `(reviewer, plan-action)` | 2,202 | 0 | n/a | n/a | 2,202 | 0 |

The malformed counts are exactly the audit's: **the seven Solver drafts that do not parse** reach
the Planner once each (`B-DRAFT-PLAN` 7) and the Reviewer twice each (`B-DRAFT-REV` 14), and **every
Reviewer output fails the registered findings parser**, so `B-REVIEW-PLAN` and `B-REVIEW-SOL` render
FALLBACK-RAW on 100 % of their structured rows. On this base the review block therefore reads
`REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)` followed by the Reviewer's own bytes, on every
row -- **this cell does not structure the review; it declares and receipts what the review is.**

*What provably does not change.* The policy is a transform over the exposed agent-state list only:
it returns a tuple of the same length and the same order and never reads or returns the system
message, the `supplied_evidence` items, the speech packet parts, the tool schemas or the decoding
parameters. The checked consequences recorded in the receipt are:

- **no evidence block changes**: every `supplied_evidence` item is outside the transform, and no
  boundary's rendering reads one;
- **no speech part changes**: the speech packet and its SHA-256 are outside the transform;
- **no system message changes**: `task_instruction` is an INPUT to the tool-observation renderer and
  is never rewritten -- and on this cell that renderer never runs, because all four tool-observation
  boundaries are `raw`;
- **every non-agent-state history part is byte-identical**: 5,417 of 5,417 control envelopes;
- **every tool-observation state is byte-identical**: 0 of 2,184 changed;
- **every `raw` row's `rendered_sha256` equals its source's `content_sha256`**, asserted on every one
  of the 5,478 raw rows (13,102 boundary rows in total: 7,624 structured, 5,478 raw).

## 4. Metrics

**Primary: official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded. **Guard: intent (joint scenario+action) accuracy.**

Secondaries: intent accuracy, scenario accuracy, action accuracy, official pooled span F1, per-row
mean official SLU-F1, per-row mean exact slot F1, and the saves/harms/ties table with the exact
two-sided McNemar p. **Projection v3 is reported beside every official number** (owner decision 7 of
2026-09-17); the anchor's v3 reading is SLU 51.99 / intent 79.35 / scenario 85.46 / action 80.65 /
span 40.30, and the released direct anchor's is 34.31 / 75.37 / 84.17 / 75.93 / 23.24.

Mandatory diagnostics:

- the flight's own `saea-node-context-policy-v1` receipt aggregate per boundary -- rows, parsed,
  malformed, fallback applied, median rendered chars -- against the contact-free expectation of
  section 3.1;
- rewritten states per role against the contact-free expectation (solver 1,100 of 1,110; reviewer
  4,344 of 6,548; planner 2,180 of 5,444; perception 0 of 0);
- the seven malformed Solver drafts of the audit: whether the Planner's `HARNESS CHECKS` block
  changed their outcome, reported as a count, never as a claim;
- the per-scenario intent table over all 18 scenarios, natural mixture and equal weighting;
- the per-contact prompt-token delta from the cell's own sealed native contact-fit receipts.

`delta = arm minus the sealed anchor`, in percentage points; a negative delta means the arm is worse.

## 5. `legal_entity_types` carries no new information

The `HARNESS CHECKS` block of `probes/ncp_slurp_planner_brief_v1.txt` reports whether every entity
type in the draft is in the legal inventory, so the policy's `params` must carry that inventory. It
is derived **from the committed inventory this fragment already uses**, never from data rows and
never from gold: `core.base.INSTRUCTION_FILLS["slurp-label-inventory"]` is the anchor's own
`task_instruction_fill`, and its rendered line

```
Entity types (55 in total; every "type" must be exactly one of these): alarm_type, app_name, ...
```

is a **substring of the system message of all 5,417 sealed anchor contacts** (checked in the
request-channel proof: 5,417 of 5,417). The 55 types are recorded in the fragment in the fill's own
sorted order. The policy therefore renders no label the anchor's own system prompt did not already
carry on every contact.

## 6. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence. Sensitivity:
paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries the
per-scenario table over all 18 scenarios in both the natural-mixture and the equal-scenario
weighting, the equal-scenario delta reported beside the natural-mixture point estimate and never
replacing it. Speaker clusters come from the released roster metadata (125 speakers, 18 scenarios of
60 rows, 523 headset and 557 far-field rows).

## 7. Decision rule (fixed before contact)

Null half-widths are the **TRAIN A own null measured by cell B0r** on this exact roster and
geometry: **h_SLU = 1.1218 pp**, **h_intent = 1.0051 pp** at CI95 (0.9420 / 0.8505 at CI90).

**The B7a decision rule, quoted verbatim from
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 11:**

> ADMITTED iff the primary official SLU CI95 lower bound is > 0 against the anchor, intent is
> non-inferior at the own null margin 1.0051 pp, the symmetric-normalised scorer agrees in sign, and
> no scenario loses intent beyond the null band. NEUTRAL iff both primary metrics are non-inferior
> within the own null margins (SLU 1.1218, intent 1.0051); a NEUTRAL L1 still enters the SLURP
> default plan, because it removes a named defect class at no measured cost -- the seven malformed
> drafts that reached the Planner unflagged and the 2,167 unstructured reviews now carry a declared,
> receipted disposition. HARMFUL otherwise, and then L2 is not flown.

Operationalised, with nothing added and one clause recorded as unevaluable:

- **primary**: the CI95 lower bound of the pooled official SLU micro F1 delta against the sealed
  anchor is greater than 0;
- **intent guard**: non-inferior at 1.0051 pp (its CI95 lower bound above -1.0051);
- **scenario harm**: a scenario loses intent beyond the null band when the CI95 upper bound of that
  scenario's own paired intent delta is below zero. Roster-level scenario and action margins stay
  diagnostics for the per-scenario table, exactly as cell B0 registered them, not gates;
- **the symmetric-normalised clause is NOT EVALUABLE on this roster.**
  `slurp-slu-f1-normalized-v1` resolves gold from the SLURP `devel` split and refuses TRAIN sample
  ids, exactly as cell B0r recorded. Following the B4 anchor package, the clause is replaced by the
  **projection-v3 agreement clause** -- `slurp-slu-official-projected-v3-train` must agree in sign
  with the unprojected primary -- and this substitution is recorded as deviation 1 of section 12
  rather than silently dropped. The coordinator may instead register a TRAIN sibling of the
  symmetric scorer before launch;
- **NEUTRAL enters the default plan.** This is the one place B7a differs from every other cell of
  this program, and it is the design's own fixed consequence, not this registration's addition;
- **HARMFUL** otherwise, and then B7b (L2) is not flown.

No repeat-to-pass: the verdict is read once, from the single official score of the complete
manifest.

## 8. Cost reporting (mandatory in every verdict)

- actual generation contacts, against the anchor's realized 5,417 (5.016 per row) and the registered
  ceiling of 11 per row, 11,880 per cell;
- contacts per row against the anchor's 5.016 -- **this module adds prompt volume, not contacts**:
  L1 is a deterministic, zero-contact transform;
- actual repeated speech seconds, against the anchor's realized 15,459.76 and the registered ceiling
  11 x 3,084.528 = 33,929.8, registered as 33,930;
- actual FIT endpoints, expected 4 per realized contact, ceiling 47,520;
- actual native task-contract tool calls, ceiling 6,480;
- GPU hours read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`)
  over the lease window, never a wall-clock guess, against the anchor's measured 3.388;
- mean latency, slot occupancy and duty cycle from the same monitor;
- the prompt-token delta against the anchor, from the cell's own sealed native contact-fit receipts.

Registered ceilings, which are bounds and not targets: **11,880 generation calls, 47,520 FIT
endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract
calls**, one official complete scoring job, zero ASR, encoder and paid-API calls. Per smoke: **44
generation calls, 176 FIT endpoints, 117 repeated speech seconds, 1.0 GPU hours, 24 task-contract
calls**, zero scoring jobs.

## 9. Prompt fit

Receipt: `prompt-fit-v1.json` (SHA-256 `4e33b5fa00839bee31bc3918611ded2df64b60822495b7cff65e439b82881b14`). Slot **24,576** tokens;
decision **ALLOW** for every phase.

The bound is the anchor's own **5,417 sealed native contact-fit receipts** -- each realized
contact's own `required_tokens` -- plus that same contact's measured node-context **word** delta
under the repository's stated proxy (`analysis.slurp_slot_vocabulary.TOKEN_PROXY_FACTOR` = 1.3).
Every one of the 5,417 contacts was matched to its fit receipt; none was unmatched.

| phase | contacts | anchor max required | word delta (min / median / max) | max bound | min margin |
| --- | ---: | ---: | --- | ---: | ---: |
| perception | 1,080 | 4,270 | 0 / 0 / 0 | 4,270 | **20,306** |
| solver | 1,085 | 13,482 | -18 / +2 / +50 | 13,544 | **11,032** |
| reviewer | 2,167 | 15,374 | +8 / +32 / +68 | 15,447 | **9,129** |
| planner | 1,085 | 15,382 | +24 / +82 / +165 | 15,593 | **8,983** |

Every bound fits on every one of the 5,417 contacts, with at least **8,983 tokens of margin**. This
is a bound, not a measurement on the flight tokenizer: each flight fits every realized request
itself through `build_native_contact_fit_gate`, and the coordinator reads those receipts.

Independently, `core.flight.cli check` ran its own model-free budget over the widest request each
phase renders across the whole roster and returned **ALLOW for every phase of both cells**: full
cell perception 19,184 required window tokens, reviewer 19,047, planner 18,987, solver 19,227
(smoke 19,183 / 19,047 / 18,986 / 19,226), each with an operational margin above 5,300 tokens. That
estimate unions every candidate envelope and is deliberately more conservative than the per-contact
bound above; both are recorded and neither replaces the other.

## 10. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration; a second failure closes that flight and the fix must be
proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke stops the
cell until the fix is proven on that same four-row roster. One experiment in flight at a time.

## 11. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed
  discovery roster.
- **No per-boundary attribution.** Eight boundaries move together in this cell; an admitted B7a says
  nothing about which boundary paid, and the design registers no per-boundary decomposition cell.
- Nothing about the Reviewer's output contract (B7r), the duplicated task-contract tool message
  (B7c) or a cleaning contact (B7b). On this base the review block is rendered UNPARSED on 100 % of
  rows, and that is a description, not a repair.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- Nothing about whether the template *language* is better in general; this cell measures one frozen
  core's behaviour on one roster under one retrieval geometry.
- The audit's counts (7 malformed drafts, 2,167 unparsed reviews) bound what a declared disposition
  can touch; they are never predicted gains.
- A structural smoke result is never a quality result.
- Nothing about the knowledge channel: the same ~32,010 characters of evidence are re-sent on four
  to five contacts per row in both arms, and the design keeps that out of scope.

## 12. Deviations recorded before contact

1. **The symmetric-normalised clause of the verbatim rule is not evaluable on TRAIN** and is
   replaced by the projection-v3 agreement clause, exactly as the B4 anchor package recorded it.
   Section 7.
2. **No `wire-check` stage** on either cell, exactly as the sealed anchor, cell B0, cell B1 and the
   B4 cells declare none: `FlightRuntime._dispatch_phase_program` refuses a native episode whose
   transport is not the real shared speech renderer, and `wire_check` installs a text transport
   double. The contact-by-contact request-channel proof of section 3.1 is the contact-free
   substitute and is stronger per contact, because it reads the real requests the anchor actually
   sent.
3. **The Planner's `HARNESS CHECKS` block is included**, which design open question 2 leaves to the
   owner. It is deterministic, computed only from material the Planner already receives, contains no
   gold, and is part of the committed `probes/ncp_slurp_planner_brief_v1.txt` template E8a merged.
   If the coordinator wants it split into its own cell, that is a template change and a new
   registration, not an edit of this one.
4. **The four tool-observation boundaries are DECLARED `raw`** rather than left undeclared. A
   declared raw boundary renders identical bytes and still emits one `level: "raw"` receipt row per
   contact, which is what turns the byte-identity claim into a checked statement (design section 6,
   point 4).
5. **`legal_entity_types` is carried in the fragment.** It is the anchor's own rendered inventory
   (section 5), not a second source; a future carrier could read it from the bound schema instead,
   and that would be a code change with its own test.
6. **Registered hashes are pre-flip.** Section 13.
7. **The smoke reference artifact.** The sealed anchor preparation has no four-row artifact of its
   own, so the smoke's `output` block is compared against the review-off four-row artifact AND, row
   by row, against the anchor's own rows for the same four sample ids; both agree.

## 13. Registered hashes are pre-flip

Every composed and protocol hash above is the value of the four config fragments **exactly as
committed at the registration commit**: readiness `held`, the preparation requirement present,
`prepared_phase_supply` pinned. `core.config.compose` hashes the whole merged four-fragment
document, so flipping readiness to `ready` and appending the coordinator's own decision requirement
each change the composed hash and therefore the protocol hash. Re-pin with `core.flight.repin` (the
runbook's section 2 gives the exact command) and re-pin this package and the four exposure-ledger
notes before launch. The method was verified on this tree: composing
`slurp-native-dual-store-train-fold-a-anchor-v1` as both baseline and experiment reproduces the
sealed anchor's own registered protocol hash
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

## 14. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b7a-ncp-l1-anchor-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads. Index: `INDEX-v1.json`.

| receipt | SHA-256 |
| --- | --- |
| `check-b7a-full-v1.json` | `47a06fa9615aa1abe080f939ec29e784fc7cdaf2a2af2bc79cb36ae5bc23a355` |
| `check-b7a-smoke-v1.json` | `09dcd1a067dd0f233016c149964fa3af23a6f911b2059eb1d88e349f25ce13c1` |
| `phase-supply-vs-anchor-v1.json` | `5f98a6125cd92b071dcd8748d8f93c53f4481e663bc812805b27765f42e5cbaf` |
| `request-channel-proof-v1.json` | `52638c76e5f5ee1558575d325702afd479bbb5fc78a499a5463b27e85168af50` |
| `prompt-fit-v1.json` | `4e33b5fa00839bee31bc3918611ded2df64b60822495b7cff65e439b82881b14` |
| `containment-v1.json` | `75722d6d01c92d669842150ef91a8eddfd84728301d9e64a9600b6051fdd9c1c` |
| `composed-hashes-v1.json` | `d2dcf4a14ca3bf67bb4231a733b5e5194095be115091accdc65bcab2e3b5aca5` |
| `plan-hashes-v1.json` | `e74261f000da4a758e55dc2c5cf5b0ea2d67e1f2747e3f68da2faff27bb2190b` |
| `ledger-parse-v1.json` | `47c4b60087be75cc397435f48423abb63d21467f6ae8b8524c93793195dda72c` |

Prepared supply: both cells' Perception artifacts carry an `output` block **byte-identical** to the
sealed anchor preparation's (`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`) on
**1080 of 1080** rows and to the four-row reference
(`512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733`) on **4 of 4**, and each row's
selection equals the anchor's own row. The Perception selection channel does not move.

Containment: **0 collisions**, verbatim and casefolded, between the protected material of both bound
snapshots (`intent-boundaries-v1` 120 items, `slot-contracts-v1` 108 items) and every one of the
five control turns the base sends **and** every one of the six committed node-context templates this
cell renders, under the runtime rule
`rails.runner._assert_agent_control_excludes_knowledge_payloads` at its floor of 8 characters.

Ledger: `contracts._parse_ledger_tables` sees all four rows exactly once, each `consumed = no`;
908 rows parsed in total.

Both `check` receipts were produced at the registration commit that carries every config, plan and
ledger row these cells fly, and both report `study_commit` equal to it, `generation_authorized`
false, readiness `held`, and runtime-derived `config_hash` and `protocol_hash` equal to the
registered ones. The documentation commit that follows changes no config, no plan and no ledger
row, and `plan-hashes-v1.json` deliberately excludes this document and the runbook for that reason.

## 15. What this package does not authorise

No readiness flip, no model contact, no default-plan edit and no harness-admission entry. The
admission entry for the module "node context policy L1" is written from the sealed verdict, never
from this registration; the runbook records the expected entry shape so the coordinator can check it
against the switch rule before writing it.
