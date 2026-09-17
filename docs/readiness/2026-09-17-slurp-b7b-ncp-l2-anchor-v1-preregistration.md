# Cell B7b on cell B7a: the Node Context Policy at level L2, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B7b registration agent, worktree
`/home/chao/saea-worktrees/fable-b7b`, branch `fable/b7b`, base commit `b4cb9ae9`. Authority:
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` (sections 3 level L2, 4, 6 -- the
E8b paragraph -- 7, 8, 9, 11 and 15), `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`
section 3 (module M5) and section 5, and the owner decisions 12-17 of 2026-09-17 recorded in
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. Engineering: item **E8b**, the L2
mechanism. This document grants no model contact; both cells stay readiness `held`, and **B7b may not
open at all until cell B7a has sealed and its verdict is ADMITTED or NEUTRAL.**

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried, and no worker, campaign,
smoke or FIT was run.

## 1. Question

Does adding **one context-cleaning model contact at the single boundary L1 provably cannot structure
today** raise pooled official SLU micro F1 on TRAIN Fold A over cell B7a, without harming intent, at
+20 % contacts?

The boundary is `planner:review-finding`. On the sealed anchor **0 of 2,167 Reviewer outputs parse**
under the repository's registered findings parser, so B7a renders that boundary FALLBACK-RAW on 100 %
of rows -- the header plus the Reviewer's own bytes in an `UNPARSED` block. It is also the boundary
feeding the node that consumes 25.0 % of the run's prompt budget to emit a median of two tokens. L2
asks the frozen core itself to restate that commentary as bounded, schema-validated issues before the
Planner reads it.

## 2. Arms

| role | identity |
| --- | --- |
| B7b | `SAEA-SLURP-NATIVE-NCP-L2-REVIEW-CLEAN-ANCHOR-TRAIN-FOLD-A-V1` / `attempt-slurp-native-ncp-l2-review-clean-anchor-train-fold-a-generation-v1`, cell `slurp-native-ncp-l2-review-clean-anchor-train-fold-a-v1`, composed `3b238087723534381b05854ae6ae519348c1d66c4c3e8f2fd2f109591d94df8d`, protocol `a0193790dfc2267c2e9442940d7cb14916ecad0369eb306eb945d2e62602d096` |
| B7b smoke | `SAEA-SLURP-NATIVE-NCP-L2-REVIEW-CLEAN-ANCHOR-SMOKE-4-V1` / `attempt-slurp-native-ncp-l2-review-clean-anchor-smoke-4-generation-v1`, cell `slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1`, composed `5f2d24355bd8f052b84ffd25424e6bb5ad112675cd386b33e222f6efb0dc4a1b`, protocol `b0bbf8acb0c1aa2ae7c05b3c4b385fce91d3bba0e0d8e03730a7f6fbeea48456` |
| comparator, primary | **the sealed bytes of cell B7a**, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1`. **NOT YET FLOWN.** Its score artifact and run manifest digests are `PENDING_B7A_SEAL` in every plan and in the analysis recipe; the coordinator fills them from the B7a verdict before the paired read, and **B7b does not open unless that verdict is ADMITTED or NEUTRAL** |
| comparator, secondary | sealed bytes of the released TRAIN A direct anchor `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`, score SHA-256 `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38`, run manifest `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e`, official pooled SLU-F1 33.89 / intent 73.70 / scenario 82.69 / action 75.09 / span 21.10 |
| context column only | sealed bytes of the dual-store anchor `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`, score SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, official pooled SLU-F1 48.53 / intent 77.96. It is B7a's comparator, reported so the B7a-plus-B7b column can be read against the pre-policy base; **it is not this cell's decision comparator** |

No comparator is ever re-flown or re-scored. Both arms share the roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json` (SHA-256
`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never
spawn). The four-row smoke uses the four already-exposed TRAIN A engineering rows (split identity
`4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`).

**No twin is registered.** A derangement control over the cleaned block would be a second cell with
its own registration and, by the program's twin rule, could fly only on a positive B7b CI95.

## 3. The one factor, and the five things it deliberately is not

The moved key is the **sub-block** `native_episode.context_policy.boundaries["planner:review-finding"]`,
inside the third episode-class switch key (`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`). Its OFF
arm is cell B7a's own entry.

**OFF (cell B7a):**

```json
{"level": "structured", "template": "probes/ncp_slurp_review_finding_v1.txt", "on_parse_failure": "raw"}
```

**ON (cell B7b):**

```json
{"level": "cleaned", "template": "probes/ncp_slurp_review_finding_v1.txt", "on_parse_failure": "raw",
 "cleaning": {"phase_id": "context_clean_review",
              "instruction_template": "probes/ncp_slurp_cleaning_review_v1.txt",
              "response_format_id": "ncp-review-issues-v1",
              "on_invalid": "fallback-l1"}}
```

Nothing else in the policy document moves: the default `level` stays `structured`, the `policy_id`
stays `typed-slurp-node-context-v1`, the whole `params` block -- `max_candidates` 3, the projection
policy, the closed `draft_response_schema`, the 55 `legal_entity_types` -- is B7a's byte for byte, and
so are the other seven model-output boundaries and the four declared `raw` tool-observation
boundaries. Receipt: `composed-hashes-v1.json`, whose versus-B7a composed-key diff reports
`boundary_entries_that_differ = ["planner:review-finding"]`.

**Five things this cell is not:**

1. **Not more than one cleaned boundary.** Design section 7 tabulates `+ reviewer:current-draft`
   (ceiling 15, +40 %) and all four model boundaries (ceiling 19, +80 %); owner decision 12 of
   2026-09-17 confirms one. Each would be its own cell.
2. **Not a Reviewer producer contract.** The Reviewer stays prose; giving it a `response_format_id`
   is cell **B7r**, which flies before this one.
3. **Not a tool-observation rewrite.** The duplicated task-contract reference line is cell **B7c**,
   which also flies before this one.
4. **Not a retry.** One cleaning attempt per consumer contact per boundary; on any validation failure
   the boundary renders B7a's own L1 block and the receipt records `validation: "rejected"` with the
   reason. That is the program's one-shot attempt semantics.
5. **Not a knowledge, supply, store, roster, geometry, instruction-template or scorer change.** Both
   knowledge stores stay at v1 with their release/snapshot pins and their supply geometry; the review
   loop stays on (`max_revisions` 1, reviewer `max_iterations` 3); the Reviewer-only task-contract
   tool authority, the Solver-only answer authority, the three-candidate contract and every
   instruction template are B7a's. Fold B is absent.

The cell carries its own `native_contact_fit` identity and caps, its own speech-feature identity
strings (provenance only, never model-visible) and its own prepared phase supply. None of those is a
channel the model can see.

### 3.1 What the cleaning contact is, mechanically (E8b as built)

- it runs **inside the consumer contact's own worker**, from `speech_binding`, on the Planner's
  already-held slot, before the Planner's own request is dispatched -- which is what makes "the same
  resident session and geometry" true rather than intended. It composes through a second
  `MeteredNativeSpeechRequest`, the same class, the same `prepare`, the same `FrozenCoreClient`;
- it **settles nothing**: it never reaches `capture_completion` and never seals a phase state;
- it is a **declared contact, not a program phase**: `cleaning.phase_id` is its own identity and
  namespace and is refused if it collides with a program phase name;
- it declares **`knowledge: "none"`**, enforced by the runner: every knowledge and evidence part of
  the consumer's user turn is dropped, the system contract and the speech packet stay, and the
  agent-state history is empty;
- **at most ONE per consumer contact per boundary**: the policy cleans the LAST review state in that
  contact's exposed history -- the review the Planner is deciding about -- and renders the earlier ones
  at L1 with `validation: "skipped"`;
- its output is validated against the closed schema of design section 4 plus two rules
  `validate_cleaning_document` adds: a `problem` may not be blank, and **the response may not
  introduce content** -- every content token of an accepted output is either one of the schema's own
  fixed words or occurs, case-folded, in the L1 material that contact was handed;
- it carries its own trace buffer, its own ordinary `native-role-contact` USE record, its own
  `AgentContactPlan` (checked against the knowledge-payload rule), the episode's evidence pins and
  the run's budget id, and it **increments `scheduled_contacts`**. It is not appended to the
  episode's `contacts`/`waves` ledger, whose invariant is one wave per QueryState transition.

Two committed templates are pinned, not one:
`configs/probes/ncp_slurp_cleaning_review_v1.txt` is the **instruction** the cleaner reads, and
`configs/probes/ncp_slurp_cleaned_review_v1.txt` is how an **accepted** output is rendered into the
Planner's context. Both are ordinary node-context templates, validated at load time and hash-pinned
in every receipt beside the boundary's L1 template.

### 3.2 The contact-ceiling arithmetic (design section 7), verified with the loader

`rails/native_episode_config.py` computes

```
ceiling = perception.max_iterations
        + (max_revisions + 1) * ( sum over the other roles of role.max_iterations * (samples if solver else 1)
                                  + sum over cleaned boundaries of consumer.max_iterations )
        + max_refreshes * perception.max_iterations
```

On this role graph (`perception 1, reviewer 3, planner 1, solver 1, samples 1, max_revisions 1,
max_refreshes 0`):

- cell B7a: `1 + (1 + 1) * (3 + 1 + 1) + 0 = 11`;
- cell B7b: `1 + (1 + 1) * (3 + 1 + 1 + 1) + 0 = 13`.

The loader then **asserts** `program.max_contacts == ceiling` and raises `program contact ceiling must
equal the bounded native graph ceiling` otherwise. That assertion was exercised on this tree against
the anchor's own `phase-native-candidates-review-revise-v1` (max_contacts 11) and it **refused the
cell**. The cell therefore binds a new program id,
`phase-native-candidates-review-revise-clean1-v1` -- the same four phases, the same purposes, the same
`knowledge` declarations, the same Perception `response_format_id` and the same `stop_rule`, with
`max_contacts` 13. See deviation 1.

Per row this is **6 contacts expected** (the anchor's realized 5.016 plus one cleaning contact per
Planner contact) against a **13-contact worst case**, that is **+20.0 % contacts** over B7a, which is
exactly what design section 7 budgets.

### 3.3 The request channel: what is shown and what is not

Receipts: `request-channel-statement-v1.json` (SHA-256
`0b0fa7e3da7062441a1b188ad52fb91ec746a50b951fdd5e2ec32515c373c684`) and
`cleaning-request-render-v1.json` (SHA-256
`36712746173bcd9e4601f490199cd13d94a7858c802a0ea520cf842439bad802`).

B7a could prove its channel **contact by contact**, because L1 is a deterministic transform and the
sealed anchor's own 5,417 requests could be replayed through it. **L2 cannot be proved that way**:
the cleaned block is the output of a model contact that has not happened, and the comparator arm has
not flown, so there are no sealed B7a requests to replay. What this package registers instead is a
statement in three provable parts and one explicit list of unknowns.

*Proved from the composed configs.* Only the one boundary entry moves, plus the policy fragment
carrying the raised ceiling and this cell's own bookkeeping identities.

*Proved through the production render path over the fake-model harness* (the same
`MeteredNativeSpeechRequest` composition and the same `LlamaServerTransport.render_request` the
flight uses, over the scripted fake transport, on an episode carrying the four smoke-row sample ids):

| statement | measured |
| --- | --- |
| one cleaning contact per Planner contact | 8 Planner contacts, 8 cleaning contacts, exactly one each |
| the cleaning request carries the committed instruction template | true on 8 of 8 |
| the cleaning request carries **no evidence block** | true on 8 of 8 |
| the cleaning request carries **no agent-state history** | 0 agent-state parts, 0 node-context parts, on 8 of 8 |
| cleaning request volume | 855 / 856 / 863 wire characters; 165 proxy tokens at `TOKEN_PROXY_FACTOR` 1.3 |
| the Planner's own request | +103 wire characters, +22 proxy tokens |
| every other shared request | 24 of 24 non-Planner requests are byte-identical once `remaining_model_contacts` is normalised away; **0** differ for any other reason |

The static render therefore differs from B7a's **in the epilogue's contact counts and nothing else**:
the episode appends its bounded limits, including `remaining_model_contacts`, to every instruction,
and the ceiling moving from 11 to 13 shifts that number for every contact of every row. The
model-free `core.flight.cli check` estimate moves accordingly and by no more: perception
19,184 -> 19,186, reviewer 19,047 -> 19,049, planner 18,987 -> 18,988, solver 19,227 -> 19,228 tokens,
all `ALLOW`.

**The harness caveat is part of the statement.** The harness supplies its own system contract, its
own synthetic speech packets and its own scripted Reviewer text, and its role graph is
perception 1 / solver 1 / reviewer 2 / planner 1 (ceiling 9 at L1, 11 at L2). The pin is of the
cleaning request's **shape, committed bytes and token volume**, not of the flight's own per-row
digests. The four smoke-row sample ids are carried so the smoke can be compared against these rows
key for key.

The measured Planner delta is **positive only because the harness's scripted review is short**. On
the anchor's own prose reviews -- p95 439 and max 1,759 characters (design section 8) -- a bounded
five-issue cleaned block is usually *smaller* than the FALLBACK-RAW block it replaces, which is why
design section 8 says L2 reduces the consumer's slice. The prompt-fit bound uses +103 characters as a
conservative upper bound, never as an expectation.

*Not knowable model-free, and not claimed to be:* which rows the cleaning output is accepted on and
which it is rejected on (the **validation-rejection rate**, section 8); the per-row bytes of the
cleaned block and therefore of the Planner request; realized contacts, repeated speech seconds, GPU
hours and prompt tokens; and cell B7a's own sealed digests.

**One consequence stated plainly.** B7b's requests are **not** byte-identical to B7a's outside the
cleaned boundary. The design says so in its own E8b paragraph, and this registration does not pretend
otherwise: an admitted B7b attributes nothing to the cleaned block alone, because the shifted contact
counter moves with it. Holding the ceiling fixed would isolate the boundary -- which is what
`tests/unit/test_node_context_policy_l2_runner.py::test_l2_changes_only_the_declared_boundarys_consumer`
measures -- but a fixed ceiling would refuse the extra contact at dispatch and is therefore not a
flyable arm.

## 4. Metrics

**Primary: official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded. **Guard: intent (joint scenario+action) accuracy.**

Secondaries: intent accuracy, scenario accuracy, action accuracy, official pooled span F1, per-row
mean official SLU-F1, per-row mean exact slot F1, and the saves/harms/ties table with the exact
two-sided McNemar p. **Projection v3 (`slurp-slu-official-projected-v3-train`) is reported beside
every official number** (owner decision 7 of 2026-09-17).

Mandatory diagnostics:

- **the validation-rejection rate** -- section 8, a mandatory verdict field;
- **net harmed rows per scenario, flagging any scenario with five or more** (owner decision 17 of
  2026-09-17);
- realized cleaning contacts against realized Planner contacts, which the design bounds at one per
  consumer contact per boundary, with earlier review states rendered at L1 and marked
  `validation: "skipped"`;
- the flight's own `saea-node-context-policy-v1` aggregate per boundary; **every boundary except
  `planner:review-finding` must reproduce cell B7a's own aggregate**, and a disagreement is a defect
  in the cell, not a new finding;
- the per-contact prompt-token delta against cell B7a's own sealed native contact-fit receipts, split
  into the Planner's own delta and the cleaning contact's new requests;
- contacts per row against B7a's realized 5.016 and the +20.0 % design expectation;
- the per-scenario intent table over all 18 scenarios, natural mixture and equal weighting.

`delta = cell B7b minus cell B7a`, in percentage points; a negative delta means the arm is worse. The
B7b-minus-anchor column is reported beside it as context and is never the decision.

## 5. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence. Sensitivity:
paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries the per-scenario
table over all 18 scenarios in both the natural-mixture and the equal-scenario weighting, the
equal-scenario delta reported beside the natural-mixture point estimate and never replacing it.
Speaker clusters come from the released roster metadata (125 speakers, 18 scenarios of 60 rows, 523
headset and 557 far-field rows).

## 6. Decision rule (fixed before contact)

Null half-widths are the **TRAIN A own null measured by cell B0r** on this exact roster and geometry:
**h_SLU = 1.1218 pp**, **h_intent = 1.0051 pp** at CI95 (0.9420 / 0.8505 at CI90).

**The B7b decision rule, quoted verbatim from
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 11:**

> **B7b decision rule:** ADMITTED iff primary SLU CI95 lower bound > 0 against **B7a** and intent
> non-inferior at 1.0051 pp, with the same scenario-harm and normalised-sign conditions; NEUTRAL if
> non-inferior within the null margins, in which case it does **not** enter the default plan, because
> it costs +20 % contacts for no measured gain; HARMFUL otherwise. B7b flies only if B7a is ADMITTED
> or NEUTRAL.

Operationalised, with nothing added and one clause recorded as unevaluable:

- **precondition**: cell B7a has sealed and its verdict is ADMITTED or NEUTRAL. A HARMFUL B7a closes
  this cell unflown, and the design says so in the same paragraph: "HARMFUL otherwise, and then L2 is
  not flown";
- **primary**: the CI95 lower bound of the pooled official SLU micro F1 delta **against cell B7a's
  sealed bytes** is greater than 0;
- **intent guard**: non-inferior at 1.0051 pp (its CI95 lower bound above -1.0051);
- **scenario harm**: a scenario loses intent beyond the null band when the CI95 upper bound of that
  scenario's own paired intent delta is below zero. Roster-level scenario and action margins stay
  diagnostics for the per-scenario table, exactly as cells B0 and B7a registered them, not gates;
- **the symmetric-normalised clause.** `slurp-slu-f1-normalized-v1` resolves gold from the SLURP
  `devel` split and refuses TRAIN sample ids. As of this registration commit `core.base.SCORERS`
  registers **no TRAIN sibling of it** -- the registered SLURP scorers are `slurp-slu`,
  `slurp-slu-f1-normalized-v1`, `slurp-slu-official`, `slurp-slu-official-aligned-v1`,
  `slurp-slu-official-projected{,-v2,-v2-train,-v3,-v3-train}`, `slurp-slu-official-train`,
  `slurp-slu-projected{,-v2,-v3}` and `slurp-slu-train`. **Owner decision 14 of 2026-09-17 orders
  such a sibling registered (model-free) and every sealed TRAIN A cell re-read offline.** If that
  TRAIN sibling exists at launch, the verdict reads it, reports it beside every official number and
  applies the design's own normalised-sign clause; **until then the clause is NOT EVALUABLE on this
  roster** and is replaced by the **projection-v3 agreement clause** --
  `slurp-slu-official-projected-v3-train` must agree in sign with the unprojected primary -- exactly
  as the B4 anchor package and cell B7a recorded it. Deviation 2;
- **NEUTRAL does NOT enter the default plan.** This is where B7b differs from B7a: a NEUTRAL L1 still
  enters the SLURP default plan because it removes a named defect class at no measured cost, while a
  NEUTRAL L2 costs **+20 % contacts** for no measured gain. The design fixes both, and neither is
  this registration's addition;
- **HARMFUL** otherwise, and then the cleaning boundary is not adopted and no further L2 boundary is
  proposed.

No repeat-to-pass: the verdict is read once, from the single official score of the complete manifest.

## 7. Cost reporting (mandatory in every verdict)

- actual generation contacts, against B7a's expected 5,417 and the registered ceiling of 13 per row,
  14,040 per cell;
- **realized cleaning contacts against realized Planner contacts**, and contacts per row against
  B7a's 5.016 -- this module adds contacts, not only prompt volume;
- actual repeated speech seconds, against the registered ceiling 13 x 3,084.5284375 = 40,099
  (the anchor realized 15,459.76 at 5.016 contacts per row);
- actual FIT endpoints, expected 4 per realized contact, ceiling 56,160;
- actual native task-contract tool calls, ceiling 6,480;
- GPU hours read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`) over
  the lease window, never a wall-clock guess, against the design's 4.0-4.3 expectation and the 12.0
  ceiling;
- mean latency, slot occupancy and duty cycle from the same monitor;
- the prompt-token delta against cell B7a, from this cell's own sealed native contact-fit receipts.

Registered ceilings, which are bounds and not targets: **14,040 generation calls, 56,160 FIT
endpoints, 40,099 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract
calls**, one official complete scoring job, zero ASR, encoder and paid-API calls. Per smoke: **52
generation calls, 208 FIT endpoints, 138 repeated speech seconds, 1.0 GPU hours, 24 task-contract
calls**, zero scoring jobs.

## 8. The validation-rejection rate is a mandatory verdict field

Every `saea-node-context-policy-v1` row at a cleaned boundary carries a `cleaning_contact` block with
`validation` (`accepted`, `rejected` or `skipped`) and `rejected_reason`. The verdict **must** report:

- the accepted / rejected / skipped counts, absolutely and as a percentage of realized cleaning
  contacts;
- the `rejected_reason` histogram, naming the two rules `validate_cleaning_document` adds beyond the
  schema (a blank `problem`; a content token that is neither one of the schema's own fixed words nor
  present, case-folded, in the L1 material);
- the same split per scenario.

A verdict without this field is incomplete, whatever the primary metric says. The reason is direct: a
high rejection rate means the Planner mostly read B7a's own L1 render, so a null result would be a
statement about the *fallback*, not about cleaning; a low rejection rate with a null result is a
statement about cleaning itself. The two are different findings and the rate is what separates them.

## 9. Prompt fit

Receipt: `prompt-fit-v1.json` (SHA-256
`cdb5bf176d43d9364e589606758bbddec90a7c90758c31802815f7f9769c49c1`). Slot **24,576** tokens; decision
**ALLOW**.

Two contact-free bounds.

*(a) Existing contacts.* Only the Planner's own request changes at all, by the cleaned block replacing
the L1 review block; its measured wire delta is added to cell B7a's own per-phase maximum required
tokens. Every other role's request is unchanged except for the `remaining_model_contacts` counter.

| phase | B7a max required | B7b delta | B7b bound | margin |
| --- | ---: | ---: | ---: | ---: |
| perception | 4,270 | 0 | 4,270 | 20,306 |
| solver | 13,544 | 0 | 13,544 | 11,032 |
| reviewer | 15,447 | 0 | 15,447 | 9,129 |
| planner | 15,593 | **+22** | 15,615 | **8,961** |

*(b) The new contact.* The cleaning request is a new request shape. Measured through the production
render path over the fake-model harness: **165 proxy tokens / 863 wire characters**. Adding the
cell's own 8,118-character system contract (2,111 proxy tokens) and the material term -- the
Reviewer's own output, bounded at the anchor's measured max 1,759 characters (457 proxy tokens) --
gives a bound of **2,733 tokens, margin 21,843**, inside the design's own 2,400-2,700 estimate.

Worst margin anywhere: **8,961 tokens** (planner). Independently, `core.flight.cli check` ran its own
model-free budget over the widest request each phase renders across the whole roster and returned
**ALLOW for every phase of both cells**: full cell perception 19,186, reviewer 19,049, planner 18,988,
solver 19,228 required window tokens (smoke 19,185 / 19,049 / 18,988 / 19,228), each with an
operational margin above 5,300 tokens. That estimate does **not** include the cleaning contact, which
is not a program phase; bound (b) covers it. Every flight also fits each realized request itself
through `build_native_contact_fit_gate`, the cleaning contacts included.

## 10. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration; a second failure closes that flight and the fix must be
proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke stops the
cell until the fix is proven on that same four-row roster. One experiment in flight at a time.

## 11. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed discovery
  roster.
- **No attribution inside the arm.** A structured review block and a shifted
  `remaining_model_contacts` move together, and no decomposition cell is registered.
- Nothing about the other eleven boundaries, the Reviewer's output contract (B7r) or the
  tool-observation rewrite (B7c).
- Nothing about a second, third or fourth cleaned boundary, whose ceilings design section 7 already
  tabulates.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- Nothing about whether the cleaning *template language* is better in general; this cell measures one
  frozen core's behaviour on one roster under one retrieval geometry.
- The audit's counts (2,167 unparsed reviews) bound what a cleaning contact can touch; they are never
  predicted gains.
- A structural smoke result is never a quality result.
- Nothing about the knowledge channel: the same ~32,010 characters of evidence are re-sent on four to
  five contacts per row in both arms, and the design keeps that out of scope. The cleaning contact
  itself sends none of it.

## 12. Deviations recorded before contact

1. **A new policy fragment WAS needed, against the registration brief's expectation.** The brief
   stated that the ceiling moves through `native_episode_config` alone and that no new policy
   fragment is required. Verified with the loader on this tree: `load_native_episode_config` does
   compute 13, and then **asserts `program.max_contacts == ceiling` and refuses** the anchor's
   11-contact `phase-native-candidates-review-revise-v1`. `program.max_contacts` is read from
   `configs/policy/<policy>.json` by `rails.controllers.load_phase_program`; no committed fragment
   with these four phases declares 13 (the existing ones declare 11, 12 and 19). This registration
   therefore adds `configs/policy/phase-native-candidates-review-revise-clean1-v1.json` and registers
   its id in `rails/controllers.py` (`_PROGRAM_CONFIG_FILENAMES` plus a literal
   `register_phase_programs_v1` entry, as `scripts/checks/engineering_base_check.py` requires) and in
   `tests/unit/test_rails_controllers.py`'s expected program shapes. The fragment is
   `phase-native-candidates-review-revise-v1` with `max_contacts` 13 and nothing else changed. The
   precedent is exact: `phase-native-candidates-review-revise-samples5-v1` was added the same way for
   cell B2, under the comment "two program ids must never resolve to the same object when their
   contact ceilings differ". **This is a code change and the coordinator should see it**: it is on
   branch `fable/b7b` and must be merged before the cell composes anywhere else.
2. **The symmetric-normalised clause is not evaluable on TRAIN** and is replaced by the projection-v3
   agreement clause, unless the TRAIN sibling that owner decision 14 orders is registered before
   launch. Section 6.
3. **No contact-by-contact request-channel proof, and none is possible.** B7a's proof replayed the
   sealed anchor's own requests through a deterministic transform; L2's moved bytes are a model
   output and the comparator has not flown. Section 3.3 registers a three-part statement and an
   explicit list of unknowns instead. This is weaker than B7a's evidence and is recorded as such.
4. **No `wire-check` stage**, exactly as the sealed anchor, cells B0, B1, the B4 cells and cell B7a
   declare none: `FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is
   not the real shared speech renderer, and `wire_check` installs a text transport double.
5. **The fake-model harness is not the cell.** Its system contract, speech packets, scripted Reviewer
   text and role graph are its own; it pins the cleaning request's shape, committed bytes and token
   volume, not the flight's per-row digests. Section 3.3.
6. **The primary comparator's digests are `PENDING_B7A_SEAL`.** They cannot be filled before B7a
   flies, and the cell cannot open before B7a's verdict is read.
7. **Registered hashes are pre-flip.** Section 13.
8. **The smoke reference artifact.** The B7a preparation has no four-row artifact of its own, so the
   smoke's `output` block is compared against the review-off four-row artifact and, row by row,
   against the anchor's own rows for the same four sample ids; both agree.

## 13. Registered hashes are pre-flip

Every composed and protocol hash above is the value of the five config fragments **exactly as
committed at the registration commit**: readiness `held`, the preparation requirement present,
`prepared_phase_supply` pinned, no decision requirement. `core.config.compose` hashes the whole merged
document, so flipping readiness to `ready` and appending the coordinator's own decision requirement
each change the composed hash and therefore the protocol hash. Re-pin with `core.flight.repin`
(`scripts/flights/repin_cell.py`; the runbook's section 2 gives the exact command) and re-pin this
package and the four exposure-ledger notes before launch. The method was verified on this tree:
composing `slurp-native-dual-store-train-fold-a-anchor-v1` as both baseline and experiment reproduces
the sealed anchor's own registered protocol hash
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

## 14. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b7b-ncp-l2-anchor-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads. Index: `INDEX-v1.json`.

| receipt | SHA-256 |
| --- | --- |
| `check-b7b-full-v1.json` | `02ddb70366d476c9c22f8ecc4457559cbd067e48fed6f94093f46c485eb1f0d9` |
| `check-b7b-smoke-v1.json` | `aa1cbbd19bc6d4bc41d1a42b21397d62fc63bd54888d4d3656f0ec06dc138943` |
| `cleaning-request-render-v1.json` | `36712746173bcd9e4601f490199cd13d94a7858c802a0ea520cf842439bad802` |
| `composed-hashes-v1.json` | `5f9a1522b7fd0528e10fc8a2fc7cc3fb20ed888129cd7182ae68d5999814b036` |
| `containment-v1.json` | `48084ebbb8ffd58842d8266af54005a21263d62358b11df3af9bafe38a2e5138` |
| `ledger-parse-v1.json` | `6c563430fb76b41d9b5cda373fe815f72edadb4813f05d69694f73178db91ce0` |
| `phase-supply-vs-anchor-v1.json` | `0112d6c6764af99d1bf29b09b9baf21f7ee672ac62c986e35002cbf0f1935950` |
| `plan-hashes-v1.json` | `71f24cb819bd227e3854c70fef8a383b266bac03564a02574a4c8ccd2ccc636c` |
| `prompt-fit-v1.json` | `cdb5bf176d43d9364e589606758bbddec90a7c90758c31802815f7f9769c49c1` |
| `request-channel-statement-v1.json` | `0b0fa7e3da7062441a1b188ad52fb91ec746a50b951fdd5e2ec32515c373c684` |

Prepared supply: both cells' Perception artifacts carry an `output` block **byte-identical** to the
sealed anchor preparation's (`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`) on
**1080 of 1080** rows and to the four-row reference
(`512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733`) on **4 of 4**, and each row's
selection equals the anchor's own row. The Perception selection channel does not move.

Containment: **0 collisions**, verbatim and casefolded, between the protected material of both bound
snapshots and every one of the five control turns the base sends **and** every one of the **eight**
committed node-context templates this cell renders -- the two E8b templates included -- under the
runtime rule `rails.runner._assert_agent_control_excludes_knowledge_payloads` at its floor of 8
characters.

Ledger: `contracts._parse_ledger_tables` sees all four rows exactly once, each `consumed = no`; 912
rows parsed in total.

Both `check` receipts were produced at the registration commit that carries every config, plan and
ledger row these cells fly, and both report `readiness held`, `generation_authorized false`, and
runtime-derived `config_hash` and `protocol_hash` equal to the registered ones. The documentation
commit that follows changes no config, no plan and no ledger row, and `plan-hashes-v1.json`
deliberately excludes this document and the runbook for that reason.

## 15. What this package does not authorise

No readiness flip, no model contact, no default-plan edit, no harness-admission entry, no twin
registration, and **no launch before cell B7a has sealed with an ADMITTED or NEUTRAL verdict**. The
admission entry for the module "node context policy L2" is written from the sealed verdict, never
from this registration; the runbook records the expected entry shape so the coordinator can check it
against the switch rule before writing it. Branch `fable/b7b` is not merged into `master` by this
agent.
