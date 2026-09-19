# SLURP v2 base program: design

Author: Fable 5.1, root coordinator. Date: 2026-09-16 (owner approval), recorded 2026-09-17 UTC.
Authority: `docs/superpowers/plans/experiment-handoff/OWNER-FABLE-TAKEOVER-2026-09-16.md` and
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. This spec admits no model
contact; each cell registers its own ExecutionPlan, exposure row and readiness before contact.

## 1. Goal and acceptance bar

Raise the SLURP agent from the retained dual-store base (official pooled SLU-F1 48.53 / intent
77.96 on TRAIN A; 50.30 / 75.6 on DEV1000) to an acceptable base: **SLU-F1 >= 64 and intent
>= 78, replicated on the same roster** (owner decision 1). Lock that system as "SLURP base v2"
and only then open Stage 3 (training-free optimisation of its exposed decisions).

Owner decision 28 (2026-09-19): the bar above is a DEVELOPMENT bar on a roster drawn from the training data
that the program has optimised on; the published baselines it was derived from are test-set numbers and are
never compared with it, and no conclusion read on TRAIN A, Fold B or DEV-1000 extends to the test split. The
comparison with published systems happens once, on the test split, after Stage 3 (training-free RL,
Pareto-optimal policies); until then the program optimises freely on train and dev.

## 2. Diagnosis the design answers

| Fact (sealed evidence) | Consequence |
| --- | --- |
| Reviewer x2 + Planner = 60 % of contacts, 0 intent saves, 1 harm per 1,000 rows; Planner ACCEPTs 1,075/1,080 | The review loop is removed unless the ablation shows harm; its budget is re-spent |
| Entity loss: FN 31.5 % (date omission 84/138), FP 28.8 % (184/414 empty-gold rows emit entities), filler distance 35 % (time representation), type swap 4.7 %; recall ceiling 78 | Slots need convention transfer (exemplars), FP suppression (aggregation, support filter) and two contract fixes |
| Coverage 86.8 %, driven by own-card retrieval; Perception over all 60 cards also 87.7 %; `general` scenario coverage 43 %, intent 36.7 % | Coverage needs a supplement that preserves the model's hypotheses (neighbour intents) and a fallback for `general_quirky` |
| Far-field beats headset; fixed Whisper null; owner no-transcript rule | No ASR or re-listen tools |
| Byte-identical greedy prompts flip 28 % of outputs and 5 % of intents | Sampling plus deterministic aggregation has headroom and yields same-state trajectory groups |

## 3. Modules (each one config key, admitted one at a time)

| Id | Module | Axis | Config switch (harness-admission class) | Twin / control |
| --- | --- | --- | --- | --- |
| M0 | Review-off native episode | USE | `run`: `native_episode.max_revisions 0` + reviewer/planner `max_iterations 0` (policy `phase-native-candidates-solve-v1`) | sealed anchor |
| M1 | Exemplar-grounded Solver | SUPPLY | `knowledge_views`: `phase_supply.solver` = annotated TRAIN exemplars keyed by sealed speech vectors | within-scenario derangement of the speech vectors (token-matched) |
| M2 | Sample-and-aggregate commit | USE | `judges`: `roles.solver.samples N` + `decoding_overrides` + commit policy `saea-commit-plurality-support-v1` | N greedy repeats aggregated identically |
| M3 | USE projection v3 (label rule R_action then legal-label v2; filler normalisation P2: case, whitespace, punctuation, meridiem, numeric words; NO support filter, rejected by A1) | USE | scorer `slurp-slu-official-projected-v3[-train]` and the runtime judge of the same rule | unprojected; official, symmetric-normalised and rung numbers always reported together |
| M4a | `general_quirky` fallback candidate + qa/general contrast card | ORG | `knowledge_views`: Perception fill `fallback_candidate` + store version | base without it |
| M4b | Date/time slot-contract revision | ORG | `knowledge_views`: slot store version pin | base store |
| M5 | Node Context Policy, L1 `structured` (E8a, 2026-09-17) and L2 `cleaned` (E8b, 2026-09-17) | USE | `episode`: `native_episode.context_policy` (OFF = absent / `"raw"` / raw at every boundary) | the anchor; L1 derangement twin only on a positive CI95; L2's comparator is B7a's sealed bytes |

Boundary for M1: exemplar text and gold annotations come only from the construction pool
(TRAIN minus every utterance with a recording in TRAIN A, TRAIN B or DEV-1000, the 2026-09-13
exclusion), reach the model only as typed content blocks, and never as instruction text. The
exact-text-neighbour rate is reported as a sensitivity subset; no gold-derived runtime mask.

Boundary for M2 (item E2c, 2026-09-17): **the committed answer is the reviewed draft; raw samples in
custody.** One grouped Solver visit takes ONE step and registers exactly ONE `phase:<solver>` agent
state, holding the commit policy's aggregated answer in the same wire form a samples-1 (anchor)
Solver state has, so the Reviewer and the Planner read one draft exactly as they do on the anchor and
the cell stays one-factor. The N raw samples stay in custody — each its own contact, trace and cost
record, all N in the visit's one `action_alternatives` wave, and their seeds, decoding parameters,
parse status and parsed answers in the sealed `solver_group` receipt that
`analysis.native_commit_replay` re-aggregates offline. A Planner `REVISE` re-samples the whole group
and re-commits; the contact-ceiling formula is unchanged.

E2d (2026-09-17): **a grouped row's delivered text is custody, re-derived at seal.** Cell B2 v3's
four-row smoke generated every contact and then failed AT THE SEAL. The delivered `text` of a grouped
Solver row is the commit policy's aggregate over the N raw sample texts and equals none of them,
while the bundle's I7 invariant reads a row's `response_text_sha256` as "the delivered text IS one
recorded model response's bytes" — and the pre-E2d runner bound that field to the LAST RAW sample's
text hash. Two changes close it, both confined to grouped rows. (1) The runner:
`reproduction.ojw.native_group_solver` now records `solver_group.commit_params`, the exact parameters
the policy was applied with, beside its already-recorded id; and
`core.flight.runtime._canonical_output_rows` binds a grouped row's `response_text_sha256` to the
DELIVERED bytes. Nothing is lost — the raw transport envelope hash stays in `response_sha256`, and
every raw sample's own request/response hashes stay in `solver_group.samples[i].contacts[j]`. A
samples-1 row is byte-identical to before (pinned in
`tests/unit/test_native_episode_runner_grouped_solver.py`). (2) The verifier: `core.bundle.outputs`
adds invariant **I7g** for a row carrying a `solver_group` receipt — every sample's recorded
`response_text_sha256` must be the trace's own MODEL_RESPONSE bytes for that contact, the named
commit policy must resolve in `core.base.COMMIT_POLICIES` and reproduce itself, re-running it over
the row's own recorded samples through `analysis.native_commit_replay` (the same code the offline
sensitivity table runs) must reproduce the delivered bytes byte for byte, and the row's
request/response identity must be that group's LAST sample contact. I7 itself is untouched and still
binds every row's `text` to its own `response_text_sha256`, grouped rows included; a grouped row
whose delivered text differs from the recomputation is refused naming I7g and the first differing
character offset, never the text. A grouped receipt recording no `commit_params` is refused: a bundle
carries no composed configuration, so without them the delivered text cannot be re-derived from the
bundle alone. That is also why the smoke's own sealed bytes, written by the pre-E2d runner, do not
verify — their samples bind to the trace and their commit recomputation reproduces all four delivered
texts exactly, but the row form is the old one, so cell B2 v3 re-flies its four-row smoke under the
fixed runner rather than any sealed byte being edited.

E8a (2026-09-17, owner directive of 2026-09-17 on node context): **M5, the Node Context Policy**, one
declared handling policy per node boundary, where a boundary is the pair
`(consumer_role_kind, semantic_class)`. Axis USE. Config switch: `episode` class, third and last key
of the closed allowlist, `native_episode.context_policy`. OFF arm: level L0 — the key absent, the
literal `"raw"`, or an object that is `raw` at every boundary — which renders request bytes identical
to the pre-key baseline (pinned in `tests/unit/test_node_context_policy_runner.py`). ON arm: level L1
`structured`, a deterministic zero-contact parse → declared malformed rule → committed hash-pinned
template under `configs/probes/ncp_slurp_*.txt`. Twin: the L1 derangement control of the design's
section 10, which flies only if the cell shows a positive CI95. Level L2 (`cleaned`, one extra
context-cleaning contact) is E8b and is refused at load time until it lands. The existing optional
`native_episode.role_context` block is folded under the new key — its `policy_id`/`params` pair IS
the structured level's implementation — and a fragment carrying both is refused. Design and cells
(B7a, B7b): `docs/superpowers/specs/2026-09-17-node-context-policy-design.md`; evidence base:
`docs/results/2026-09-17-slurp-node-context-audit-v1.md`. E8a is the engineering only: no cell, no
config commit, no exposure row and no model contact are authorised by it.

E8b (2026-09-17): **M5 gains its level L2, `cleaned`.** A boundary declared
`{"level": "cleaned", "cleaning": {...}}` performs L1 first and then makes ONE additional contact to
the same frozen core, on the consumer contact's own pinned slot, in the same resident session and
serving geometry, composed by the same `MeteredNativeSpeechRequest` path every role contact uses — so
it is metered, budget-gated, exposure-bound, traced and costed identically and is refused past
`config.max_contacts`. Its declared phase carries `knowledge: "none"` (its request has no evidence
block and no agent-state history), its own registered `response_format_id`
(`ncp-review-issues-v1`), and an instruction that is exactly the committed, hash-pinned template
`configs/probes/ncp_slurp_cleaning_review_v1.txt` plus the L1 material — never the task, never the
answer schema, never a request for a new judgment. Its answer is validated against the design's
closed schema and against the rule that a cleaning contact may not introduce content; on ANY failure
the boundary falls back to its L1 rendering and the receipt records `validation: "rejected"` with the
reason, one attempt and no retry. At most one cleaning contact is made per consumer contact per
boundary (the LAST state of that boundary in the contact's exposed history), which is what makes the
ceiling exact: the contact ceiling gains `(max_revisions + 1) × consumer_role.max_iterations` per
cleaned boundary, taking the anchor's 11 to 13 for the one boundary cell B7b declares. Cell B7b's
whole config difference from B7a is that one boundary entry. E8b, like E8a, is engineering only.

E3c (2026-09-17, cell B1 abort): when the Planner routes REVISE the Solver is re-entered and the
prepared M1 supply returns the same twenty values, so `rails.controllers.restrict_repeat_visit_supply`
restricts a repeat visit to what the trajectory does not already hold and emits no acquire
transition when that is nothing — the values still reach the revisited request through the
accumulated `QueryState`, and every first visit is byte-identical.

E8c (2026-09-17, cell B7a abort): **harness robustness — a malformed Planner output is a retained
row, never a flight failure.** The B7a L1 arm aborted at 618 of 1,080 rows and 3,278 contacts
because one Planner response was `REJECT` and one was an 80-character sentence instead of `ACCEPT`
or `REVISE`. Every module in this section shares the one harness, so this applies to every cell: a
Planner output that names no registered action (and, under `json-action-v1`, any output the strict
single-key parse refuses) now ends its own row through the same explicit-accept seal an `ACCEPT`
takes — the committed draft delivered unchanged, no further contact, no revision spent — and is
reported as a row-level disposition, with `"legal": false` and
`"disposition": "planner_action_illegal"` on the route, the token cut to 32 characters, its sha256
beside it, and a `planner_action_illegal` count on the row's `native_episode_receipt`. The row
counts toward every budget it consumed and is scored by the standard scorer like any other row. A
cell verdict must read that count: rows sealed this way answered without a Planner decision, and a
cell whose count is not ~0 is reporting on a different population than its comparator. See
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 6 for the mechanism and
the proofs.

E10 (2026-09-18): **resume-recovery of an aborted attempt.** Owner decision 22 makes this a
standing program rule: every experiment registered from now on must support checkpoint resume. A
resume-recovery is a recovery re-registration (one per flight, root-diagnosed) that applies ONLY
when the code and the request bytes are unchanged — an infrastructure failure, never a harness or
config defect. Under that precondition every COMPLETE row of the aborted attempt is kept, without
selection; every partial or unstarted row is flown by the recovery attempt under the SAME run id
and its own new attempt id; the merged manifest declares the predecessor attempt (trace sha256, the
sorted kept sample ids and their hash, the kept/flown/partial counts) and scores once; and the
bundle verifies every kept row against the predecessor trace, byte for byte. It is a capability of
the shared campaign path, not of one cell: a recovery cell declares `resume_from`
(`{"attempt_id", "trace_sha256"}`) in its committed experiment fragment, `FlightRuntime.preflight`
scans that attempt's trace model-free and fixes the flown roster before any contact,
`_dispatch_phase_program` narrows the roster to the rows that are not COMPLETE, and the seal merges
the predecessor's replayed rows with this attempt's live ones through the one
`_canonical_output_rows` stage (`core.flight.resume`; `core.bundle.outputs` invariant I7r).
Completeness is decided by the episode's own terminal receipt in the trace, never by counting
contacts. Exposure accounting stays run-cumulative across attempts: the recovery plan's worst case
must cover the remaining rows plus the partial ones. The sibling note
`docs/superpowers/specs/2026-09-18-resume-modes-comparison.md` records why this mode was chosen
over incremental checkpoints, chunked sub-attempts and streaming appends (owner decision 24).

E10b (2026-09-18): the narrowing applies to what is DISPATCHED, never to what is VERIFIED — a
prepared artifact (`prepared/<run>/phase-supply-v<N>.json` and its recall twin) is produced, and
re-verified by `core.flight.repin`, over the cell's WHOLE roster, so its identity is computed
from the full-roster packet map (`FlightRuntime._identity_binding`) and the loaded selections are
restricted to the flown rows afterwards; the first resume-recovery flight aborted in `run_phases`
with zero contacts on `PreparationError("prepared artifact identity mismatch")` because the
narrowed 500-row map was compared against a 1,080-row artifact, and the audited list of every
other narrowed-binding consumer lives in that method's docstring.

E10c (2026-09-18): the flown roster also reaches `rails.runner` explicitly — the loop derives its
roster from `adapter.load_split(split_id)`, so narrowing only the packet map left the two
disagreeing and a recovery refused with `speech_packet_bindings must materialize every query sample
exactly once`; `_dispatch_phase_program` now passes the flown ids as `flown_sample_ids` (optional,
absent for every ordinary flight, honoured by `rails.phase_runner.run_continuous_program` and
`rails.runner.run_speech_native_agent_loop`), which restricts the split in its own order, refuses a
flown id the split does not carry, and derives `planned_ceiling` from the flown rows alone, while
the adapter, the prepared-artifact identity and the merged seal keep the cell's whole roster.


E11 (2026-09-18, owner directive 26): **the delivery-time normaliser node.** Owner directive 26
rules that this program's offline analyses belong INSIDE agent nodes rather than only in reports,
and owner decision 23 makes the bar and every final evaluation the OFFICIAL, unprojected
`slurp-slu-official-train` number. Together they move module M3 out of the scorer. Projection v3
(label rule `R_action`, then the registered legal-label projection v2, then filler normalisation
P2 -- case, whitespace, punctuation, meridiem, numeric words, no support filter) has lived since E4
as scorer-side post-processing (`slurp-slu-official-projected-v3[-train]`, cell B3); it lifts cell
B1 from 61.14 to 62.67 and cell B5e from 62.34 to 63.78 official-equivalent pooled SLU on TRAIN A,
and the official scorer credits none of it while it lives there. E11 applies the SAME rule inside
the episode, so the official scorer reads an answer the system itself delivered.

*What it is.* One registry-resolved entry, `saea-deliver-normalise-v3`, in the NEW
`core.base.DELIVERY_NORMALISERS` registry, implemented by calling
`rails.slurp_projection_v3.apply_slurp_projection_v3_delivery` -- the same two functions the v3
scorer applies -- never a second implementation. It is pure and deterministic, needs no gold, no
roster and no model contact, and declares the one carrier it is defined for. It is NOT a
`core.base.JUDGES` entry and cannot be one: owner Decision 11-C makes the Reviewer seat
criticism-only and `core.base.JudgeRegistry` refuses at the door anything that could return
replacement text, while this node's whole job is to rewrite the delivered answer. The registry it
does live in is the seam `COMMIT_POLICIES` already is -- a registered, deterministic function whose
output IS delivered bytes, resolved by id from one config key and re-derivable offline from
custody -- and it checks its own door the way `JudgeRegistry` checks that one.

*The switch.* One `episode`-class key, `native_episode.deliver_normaliser`, the fourth and last of
that class's closed allowlist, armed as `{"normaliser": "saea-deliver-normalise-v3"}`. Its OFF arm
is the key's absence: a delivery node is either absent or armed. `rails.runner` applies it exactly
once per row, after the Planner ACCEPTs (or after the terminal delivery of the last revision),
after every guard that binds the accepted answer to its actual source response, and before that
answer becomes the delivered text; an abstention is never normalised. The loader validates it
fail-closed before any contact: an unregistered rule, a rule declared for another carrier, the E4
run-level key `slurp_projection_v3_delivery` declared beside it (two spellings of one rule), and
the grouped-Solver combination (`roles.solver.samples >= 2`, whose delivered text is already the
COMMIT policy's aggregate) are each refused by name. Harness-admission entry form: `switch.table`
`"episode"`, `switch.key` `"native_episode.deliver_normaliser"`, `switch.off` `null`, `switch.on`
`{"normaliser": "saea-deliver-normalise-v3"}`, `switch.proof`
`tests/unit/test_config_table_module_switches.py::test_deliver_normaliser_is_one_episode_class_key`.
It is an `episode` entry rather than a `run` one because it is a node of the episode declared
beside the roles it runs after, and rather than a `judges` TABLE entry because that table wraps a
phase's `phase_review` block, i.e. the criticism-only Reviewer seat.

*One factor, down to the byte.* The node makes no contact, so every MODEL_REQUEST byte is identical
with and without it (pinned end to end in
`tests/unit/test_native_episode_runner_deliver_normaliser.py`, which runs the real episode twice
through the shared fake transport and compares all four rendered requests). It also delivers the
accepted answer VERBATIM whenever the rule repairs neither a label nor a filler, rather than
re-rendering it in canonical JSON: on the sealed B1 arm the re-render alone would have changed
1,076 of 1,080 rows against 24 repaired labels and 82 repaired filler rows, which is a difference no
verdict could read. With the suppression the ON arm differs from its comparator on 103 rows, and
`changed` means "the rule repaired this row".

*Custody.* The bundle's I7 binds a row's delivered text to a recorded model response, and a
normalised row's delivered text is not those bytes. I7 is untouched. Following the E2d precedent
exactly, such a row is held to the new invariant **I7n**: the trace's own MODEL_RESPONSE bytes for
the row's request id must be the rule's recorded input, the named rule must resolve in
`core.base.DELIVERY_NORMALISERS` and be deterministic, and re-running it over those bytes must
reproduce the delivered bytes byte for byte; a row carrying both a `solver_group` and a
`deliver_normaliser` receipt is refused; a refusal names the invariant and the first differing
character offset, never the text. The seal (`core.flight.runtime._canonical_output_rows`) binds a
normalised row's `response_text_sha256` to the DELIVERED bytes, exactly as it does for a grouped
row, and checks the receipt's input digest against the accepted contact's own recorded response
text. The per-row receipt is `native_episode_receipt.deliver_normaliser`: schema, rule id, version,
`rule_id`, carrier, `applied`, `changed`, `rendering_suppressed`, `input_sha256`, `output_sha256`,
`labels_changed`, `label_branch`, `fillers_changed`. Ordinary rows are unchanged in every respect.

*The reading rule.* Because the node is deterministic and zero-contact, its admission can be read
MODEL-FREE from sealed arms. `analysis.deliver_normaliser_replay` (function and CLI, the delivery
sibling of `analysis.native_commit_replay`) re-applies the registered rule to a sealed
`outputs.jsonl` under a fresh output directory, never opening the input for writing, and reports
`model_calls: 0` beside the changed-row counts. On the sealed B1 recovery arm it reports 1,080 rows,
103 changed, 24 label repairs, 82 filler-repaired rows (90 entities), 4 unparsed rows left
byte-identical. Stronger still, and what the tests actually assert: on every one of those 1,080 rows
the prediction triple parsed back out of the node's delivered text is byte-identical to the triple
the v3 SCORER builds from the same row, so the official number of the in-agent cell IS the
v3-projected number of the sealed arm -- identically, not to two decimal places -- and no scorer run
or gold read is needed to establish it. What the flight still owes is therefore only the proof that
the node executed IN the agent: a four-row smoke on the armed fragment, showing the receipt present,
the request bytes unchanged against the comparator's, and the delivered bytes equal to the replay's
for those four rows. Config fragments for both arms of cell B8a are committed with readiness `held`
(`configs/baseline/slurp-native-dual-store-train-fold-a-anchor-deliver-normalise-v3-v1.json` and
`configs/baseline/slurp-native-anchor-exemplars-k20-deliver-normalise-v3-train-fold-a-v1.json`,
with the matching `configs/experiment/slurp-native-b8a-deliver-normalise-v3-*.json`); E11 is
engineering only and authorises no owner decision, no preregistration, no exposure row and no
contact.

*One gap recorded, not closed.* The E4 SEAL-time form of this rule (run key
`slurp_projection_v3_delivery`, `core.flight.runtime._canonical_output_rows`) rewrites `text` and
`response_text_sha256` on an ordinary row while `core.bundle.outputs` still binds both to the trace
record, so a cell flown with that key would be refused at bundle verification. Both fragments that
declare it are `held` and it has never flown. E11 does not change that path; a cell that wants it
must either close it the way I7n closes the node's or use the node instead.


E12 (2026-09-19, owner directive 26): **the Reviewer slot-audit context block.** E11 is the
directive's WRITE-side instance -- an analysis placed as a transform of what the episode delivers.
E12 is its READ-side instance: the A3 coverage / slot-loss audits placed as declared context at the
Reviewer boundary, so the node that is supposed to criticise a draft finally has something
deterministic to criticise it against. The evidence it comes from is
`docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md` T5/T6 (81 of 135 gold-`date` rows
emit no date at all; 46 of 72 `time` rows emit a non-exact filler) and
`docs/results/2026-09-14-slurp-train-a-entity-loss-attribution-v1.md` (184 of the 414 empty-gold
rows emit an entity anyway). Today the Reviewer is handed the draft and nothing else, and cell B7r
only fixes the shape of what it WRITES.

*What it is.* Two pieces. First, a released construction view,
`knowledge/slurp/semantic/slot-audit-v1/` (`release.json` + `snapshot.json`, the same two-file
pinned form the other SLURP semantic stores use, built by
`scripts/build_slurp_slot_audit_view.py`): per intent, every entity type attested with it in the
construction pool and the share of that intent's construction rows carrying it, the share of its
rows carrying no entity at all, and the `date` / `time` representation conventions quoted verbatim
from the released slot store v2 card. 60 intents, 54 entity types, 9,354 construction utterances --
the governed TRAIN split minus every utterance with a recording in TRAIN Fold A, Fold B or DEV-1000
(the 2026-09-13 exclusion), the SAME pool `scripts/build_slurp_exemplar_pool_assets.py` pins for
module M1. It is committed rather than kept under `SPEECHRL_DATA_DIR` because it carries counts and
shares only -- no filler, no sentence, no utterance id, no recording -- so its pin is a git blob
hash an auditor can check offline. Second, `rails.slot_audit` plus one committed template
(`configs/probes/ncp_slurp_slot_audit_reviewer_v1.txt`) render that table, for the draft under
review, as a block APPENDED after the `reviewer:current-draft` L1 rendering, carrying the intent's
expected slot profile and four flags the HARNESS computes, never the model:

| Flag | Fires when |
| --- | --- |
| `TYPE-UNSEEN` | a draft entity type is not attested with this intent anywhere in the construction pool |
| `EMPTY-DRAFT` | the draft declares no entity while at least `empty_draft_min_entity_row_share` (0.5) of this intent's construction rows carry one |
| `MISSING-COMMON` | a type above `missing_common_min_row_share` (0.5) of this intent's construction rows is absent from the draft (`date` and `time` are named like any other type) |
| `REPRESENTATION` | a `date` or `time` filler breaks the released spoken-form convention -- `saea-spoken-form-v1`: no ASCII digit, no colon, no slash |

*The switch.* One `episode`-class key, `native_episode.reviewer_audit`, the FIFTH and last of that
class's closed allowlist, armed as `{"view": "slot-audit-v1", "release": {...}, "snapshot": {...},
"thresholds": {...}}`. Its OFF arm is the key's absence: a context block is either absent or
rendered. The loader validates it fail-closed before any contact -- another carrier, another view
id, a pin outside `knowledge/slurp/semantic/`, an unknown threshold, a threshold outside `[0, 1]`,
and a `reviewer:current-draft` boundary that is not at level `structured` are each refused by name
-- and the binding then reads both pinned files, hashes them against their pins and cross-checks
the release against the snapshot before the first request is composed. Harness-admission entry
form: `switch.table` `"episode"`, `switch.key` `"native_episode.reviewer_audit"`, `switch.off`
`null`, `switch.on` the armed object, `switch.proof`
`tests/unit/test_config_table_module_switches.py::test_reviewer_audit_is_one_episode_class_key`.
It is an `episode` entry rather than a `run` one because it MOVES REQUEST BYTES at one boundary by
design, so no `request-bytes-identical` falsifier can exist for it; rather than a
`knowledge_views` TABLE entry because it is not a phase's material or supply, performs no
retrieval and adds no evidence block; and it is a second key rather than a field of
`native_episode.context_policy` because a cell that moves the audit must stay distinguishable from
a cell that moves the policy.

*One factor, down to the byte.* The block is an ADDITION, never a rewrite: the L1 draft block above
it is produced by the same code and the same template as on the base, and the audit follows it after
one newline. `tests/unit/test_native_episode_runner_reviewer_audit.py` runs the real episode twice
through the shared fake transport and shows that with the block armed exactly the three Reviewer
contacts move and every Perception, Solver and Planner contact renders byte-identical bytes. The
block makes no contact of any kind, so the bounded ceiling stays 11 and every budget stays cell
B7r's; a malformed draft renders no block at all and records `applied: false` with its reason.
Measured size on the released table: 687-787 characters, roughly 170-200 tokens, against the 9,708
tokens of headroom the NCP design measured at the worst observed contact.

*Receipts.* The boundary's own `saea-node-context-policy-v1` row gains a `slot_audit` block
(`saea-reviewer-slot-audit-v1`): the view id, the release and snapshot sha256s, the table's content
hash, the template id and hash, the thresholds, `applied` / `reason`, the intent and whether the
table carries it, the rendered block's sha256 and character count, the count of each of the four
flags, and the flag list itself -- each flag naming a TYPE and its counts, never a filler. The
compilation record's `template_sha256s` gains the three assets the block was composed from. A row
of any other boundary keeps exactly its pre-E12 fields and its pre-E12 digest.

*Config fragments.* Both arms of cell B8b are committed with readiness `held`:
`configs/baseline/slurp-native-anchor-ncp-l1-reviewer-audit-{train-fold-a,smoke-4}-v1.json` with
the matching `configs/experiment/slurp-native-ncp-l1-reviewer-audit-anchor-{train-fold-a,smoke-4}-v1.json`,
on cell B7r's base, its roster, its budgets and its prepared Perception supply reused byte for byte.
E12 is engineering only: it authorises no owner decision, no preregistration, no exposure row and no
contact, and cell B8b flies only after B7r seals and is not HARMFUL.

## 4. Phases

**Phase 0 (done or in progress, zero contacts):** takeover receipt, owner decision record,
coordination phase `fable_directed_execution`, owner-decisions note, this spec, TRAIN A
direct-anchor release (`docs/results/2026-09-17-slurp-train-a-direct-anchor-release.md`).

**Phase A (CPU, zero model contacts; parallel agents):**

- A1 USE projection audit (DONE 2026-09-17, `docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md`: P2 +3.46 / +3.73 pp official with no scenario harm, about three quarters of it case alignment that the symmetric scorer scores at zero; support filter REJECTED; illegal-label rule R_action +1.39 pp intent) on the sealed TRAIN A anchor and DEV1000 replication outputs:
  support filter (type never under the delivered intent in the 402 TRAIN bindings; variant < 1 %
  of that intent's mentions), spoken-form normalisation for time (digits to words, am/pm),
  scored with the official scorer on projected copies; decision rule fixed: >= +1.0 pp SLU on
  TRAIN A, DEV1000 same sign, no scenario harm beyond the null margin, normalised scorer same
  sign -> M3 admitted.
- A2 exemplar-retrieval headroom (DONE 2026-09-17, `docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md`: plain k=20 union coverage 0.972, type recall 0.960, filler recall 0.566, no memorisation channel): sealed Fold A speech vectors
  (`vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl`,
  encoder identity verified against the Nemotron `query:` protocol) against the construction-pool
  subset of `vectors/slurp-kus3/facet-vectors.jsonl`; k in {5, 8, 12, 20}: gold intent among
  neighbour intents, union coverage with sealed Perception candidates, gold filler and slot-type
  recall, echo versus the sealed draft, exact-text-neighbour rate, token cost. Decision: the
  (k, c/m/top_l) maximising union coverage and filler recall under +600 Solver tokens; if
  filler+type recall < 50 % at k <= 12 and union coverage < 92 %, M1 is downgraded and reported.
- A3 coverage confusion audit (DONE 2026-09-17, `docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md`; FIX-3 illegal-id repair joins M3): pair tables for the 143 missing and 95 covered-wrong rows,
  scenario-level recall, share of the 100 persistent misses recovered by A2 neighbours.
- A4 cost pricing from the maximum-five receipts (3.46 GPU-h / 5,417 contacts).
- Engineering E1-E5 (worktrees off master, one agent per item, no installs, PYTHONPATH armour,
  `PYTHONDONTWRITEBYTECODE=1`, base check and targeted tests before merge):
  - E1: `rails/native_episode_config.py` accepts reviewer/planner `max_iterations 0` with
    `max_revisions 0` (ceiling `1 + 1*(0+0+1) = 2`); `reproduction/ojw/native_episode.py`
    delivers the initial Solver output; policy fragment `phase-native-candidates-solve-v1`;
    prompts byte-identical to the anchor; harness-admission switch registered.
  - E2: `roles.solver.samples N` and per-phase `decoding_overrides {temperature, seed_offset}`
    composed into `decoding_params` in `reproduction/ojw/native_request.py` (session identity
    unchanged); all N raw responses kept in the episode receipt; commit policy
    `saea-commit-plurality-support-v1` in `core.base` (intent plurality, greedy tie-break; entity
    pairs at support >= s of N with same-type char-F1 >= 0.8 clustering; medoid filler); an
    offline re-aggregation CLI over sealed samples; tests.
  - E3: KB view `annotated-exemplars` (utterance | intent | type=filler pairs; facet ids
    unchanged so sealed key vectors bind); `phase_supply.solver` through the E6 `acquire`
    transition, key = the sealed speech vector, plain top-k with k = 20 (A2 decision of
    2026-09-17; k = 12 if the prompt-fit receipt refuses 20); no intent diversification
    (`saea-fuse-associated-values-v1` groups per facet and equals plain top-k here);
    containment preflight with the no-example task-contract projection if needed; twin =
    derangement of the query vectors within the sealed anchor's delivered scenario (gold-free,
    token-matched by construction); prompt-fit estimate; tests.
  - E4: `score_slurp_outputs_official_projected_v3[_train]` in `core/scorers.py` mirroring v2's
    registration pattern (label rule R_action, then the v2 fallback; filler normalisation P2 with
    its four rungs; no support filter), plus the runtime commit judge form of the same function;
    tests proving scorer and judge agree byte-for-byte on sealed rows and that v3 reproduces the
    A1 numbers (TRAIN A 51.995 / 79.352, DEV1000 agent 54.031 / 76.5-76.6 as A1 records).
  - E5: Perception fill option `fallback_candidate: general_quirky` (appended when absent, never
    displacing model candidates) and a qa_factoid/general_quirky contrast card; date and time
    slot-contract revisions from construction data only, as a new pinned slot store version.

**Phase B (GPU, one cell in flight, TRAIN A 1,080):**

| Cell | Module | Base | Control | Contacts/row | GPU-h |
| --- | --- | --- | --- | ---: | ---: |
| B0 | M0 | anchor minus review loop | sealed anchor | 2 | ~1.4 |
| B1 | M1, plain top-20 speech-keyed exemplars | anchor (B0 harmful) | derangement twin + anchor | 5 | ~3.4 | ADMITTED 2026-09-18 (twin read, decision 18 branch A): SLU +12.61 [+10.54, +14.60] vs anchor, +7.83 [+5.85, +9.75] vs twin; twin alone +4.77 with nil intent; intent +2.22, v3 62.67 |
| B2 | M2, N=5, T=0.7 | anchor (B0 harmful) | 5 greedy repeats aggregated identically + anchor | 10 | ~5-6 | NEUTRAL 2026-09-19: SLU +0.06 [-1.46, +1.60], intent +0.83 [-0.30, +1.88]; FP suppressed, omissions up; twin not due; M2 enters no plan (switch class episode, key native_episode.roles.solver). |
| B3 | M3 (A1-decided: R_action + v2 labels, P2 fillers; +3.5 SLU official, about +0.2 symmetric, +1.4 intent) | scorer-side | unprojected | 0 | 0 | B8a (2026-09-19, directive 26): M3 as the delivery-time node saea-deliver-normalise-v3, model-free read ADMITTED (anchor +3.46 [+2.78, +4.18], B1 +1.53 [+1.05, +2.03] official; intent up, zero rows harmed), smoke structural PASS; default plan carries the node |
| B4a | M4a | anchor | anchor | 5 | ~3.4 | B4a v2 (2026-09-19): HARMFUL by the registered rule (intent +0.74 [-0.30, +1.75], SLU -0.70 [-2.29, +0.89]); the fallback was appended on 1,052 rows and chosen on none; +39 % GPU hours; B4c closed (decision 9) |
| B4b | M4b | anchor | anchor | 5 | ~3.4 | ADMITTED 2026-09-17: SLU +2.55 [+1.13, +3.98], intent +0.56, v3 +2.06; REPLICATED 2026-09-19 (resume-recovery flight): SLU +1.54 [+0.30, +2.93], intent +0.65, v3 +0.85; own null h_SLU 1.32 / h_intent 1.07; obligation MET, default plan pins v2 |
| B7a v2 | NCP L1 (E8a-E8c; owner directive 2026-09-17) | anchor | anchor | 5.2 | 3.8 | B7a v2 (2026-09-19): HARMFUL by the registered rule (SLU -0.31 [-1.81, +1.12], intent -0.65 [-2.18, +0.87]; interval width, not measured loss); costs +11.6 % GPU hours for no gain; decision 32: B7r/B7c closed, B8b re-based |
| B5 | admitted set ("v2 candidate") | -- | anchor, released direct | 6-7 | ~4-5 | B5e (early combination M1+M4b, recovery flight, 2026-09-18): official 62.34 / 80.09, BAR NOT MET (SLU -1.66); vs B1 +1.20 [-0.11, +2.48], intent -0.09 [-1.51, +1.38]; combination HARMFUL by clause 3 (interval width); decision 20 path. |
| B5r | replication of B5 | -- | B5 | 6-7 | ~4-5 |
| B6 | DEV1000 confirmation | -- | sealed DEV1000 direct 35.68 / agent 50.30 | 6-7 | ~4 |

Order (owner decision 8, 2026-09-17): B0 -> B0r (own-null re-decision) -> B1 -> B2 -> B4b -> B4a -> B4c only if B4a admits -> B5 -> B5r -> B6; a twin flies only after its arm shows a positive CI95 against the base. B3 (projection v3)

Order update (owner decisions 12-17, 2026-09-17): B1 recovery -> B1 twin only on a positive arm CI95 -> B2 v3 -> B7a -> B4b replicate -> B4a -> B4c only if B4a admits -> B7r -> B7c -> B7b -> B5 -> B5r -> B6; every paired read reports net harmed rows per scenario and flags five or more; a TRAIN sibling of the symmetric scorer is registered and every sealed TRAIN A cell re-read offline.

Bar metric (owner decision 23, 2026-09-18): the bar and every final evaluation read the OFFICIAL, unprojected SLURP `evaluate.py` number (`slurp-slu-official-train`), aligned with the community-standard protocol; projection v3 and the TRAIN symmetric view are diagnostics reported beside every official number, never the number a bar or a rule reads. Gains are never assumed additive: a combination cell is read from its own measured score, and additivity (the combination's delta against the sum of the single-module deltas) is a reported diagnostic only. Owner decision 24 (2026-09-18): the serving wrapper, its monitor and every campaign run as Windows Scheduled Tasks with the battery and idle conditions disabled (they survive Claude Code restarts; a machine shutdown still kills them, which is what the resume-recovery of E10 and decision 22 cover); AC sleep and hibernate are set to never during the program.

Order update (owner decisions 18-21, 2026-09-18, bar-first): B1 twin closure -> the pending four-row smokes (B2 v3 recovery, B7a recovery) in GPU gaps -> B4b replicate -> B5e (early combination of M1 or M1p with M4b, the B5 form restricted to the modules admitted so far) -> on meeting the bar, B5er replicate -> lock "SLURP base v2.0" -> B6 DEV1000 -> B2 v3 -> B7a -> B4a -> B4c only if B4a admits -> B7r -> B7c -> B7b as "v2.1" admissions on the locked base. If B5e misses the bar, the decisions 12-17 order resumes and B5b (all admitted modules) reads against the unchanged bar before any owner re-decision. Twin contingency (decision 18): a twin that ties B1 while beating the anchor makes B1 NOT ADMITTED under the registered rule and registers the twin's sealed bytes as the arm of module M1p (delivered-scenario annotated-exemplar presence), replicated by the combination flights. Record: docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md.

Outcome 2026-09-17 (B0 and B0r flown): module M0 is HARMFUL under the TRAIN A own null (docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md); the review loop is retained and recorded NEUTRAL in the harness-admission table with the SLURP default plan configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json; cells B1, B2 and B4 re-register on the anchor as v2 packages (the review-off v1 packages are superseded before contact). Every later cell carries the anchor's nominal 5 contacts per row (B2: 10) at about 3.4 GPU hours (B2: about 5 to 6). The measured own null of this roster and geometry, half-widths pooled SLU 1.1218 pp and intent 1.0051 pp, replaces the imported DEV1000 margins in every later TRAIN A rule. B3 (projection v3) is adopted as the fixed post-processing of every official number (owner decision 7), reported beside the symmetric-normalised number.

Decision rules, fixed before each flight and copied into its preregistration:

- B0 NEUTRAL if SLU and intent are non-inferior within the null margins (intent 0.92, SLU micro
  1.18); then the loop leaves the default plan. If HARMFUL, later cells build on the anchor.
  Outcome: HARMFUL on the first pass (imported margin) and HARMFUL on the own-null re-decision;
  later cells build on the anchor.
- B1, B2, B4 ADMITTED if primary SLU CI95 lower bound > 0 against the base and (B1) the twin,
  intent non-inferior at the null margin, normalised scorer agreeing in sign, and no scenario
  losing intent beyond the null band. Otherwise NEUTRAL (enters the plan only if it lowers cost)
  or HARMFUL.
- B2 thresholds preregistered: s = 3 of 5, char-F1 >= 0.8; the sealed samples license an offline
  sensitivity table (s in {2,3,4}), reported and never used for the verdict.
- B5/B5r/B6: SLU >= 64 and intent >= 78 on TRAIN A twice and on DEV1000 -> lock v2. If B5 lands
  at 56-63, report per-module contributions and return to the owner with the three options
  (second round inside one preregistered grid, lower bar, core-swap study). No repeat-to-pass.

**Phase C (after the lock):** Stage 3 training-free optimisation: state = sealed candidates +
exemplar set + draft structure + sample agreement; actions = exemplar policy, aggregation
thresholds, candidate union; grouped rollouts from the M2 sampler; reward = per-row official SLU
proxy on TRAIN A; update = the adapted Training-Free GRPO experience operator; controls = fixed
agent and unchanged-policy grouped sampling; first read on Fold B. Own spec later.

## 5. Fixed protocol (every cell)

Shared harness (`EvidenceAgentController`, `FlightRuntime`, OpenJiuwen native episode); roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json`; resident session geometry of
`configs/model/q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1.json`
(attach, never spawn); primary `slurp-slu-official-train`, one score per complete manifest through
`core.scoring_batch`, with the symmetric-normalised sibling
`slurp-slu-f1-normalized-v1-train` (owner decision 14 of 2026-09-17; same implementation, same
TRAIN gold resolution, gold and prediction normalised alike) reported beside every official
TRAIN number as owner decision 7 requires; paired whole-speaker bootstrap, 10,000 draws, seed 20260915, CI95 for
advancement, CI90 for diagnostics, natural-mixture and equal-scenario tables; comparators are
sealed bytes, never re-flown controls; preregistration + ledger row + ExecutionPlan
(`bounded-discovery-probe`, discovery role) before the first contact; contact-free wire check and
a 4-row smoke for each new module form; first failure stops a cell, one recovery
re-registration at most; harness-admission entry per module; default plan = admitted or neutral
modules only; no transcript tokens, no second answering model, no gold in runtime.
Every new preregistration's failure rule carries the resume-recovery clause (section 3, E10; owner
decision 22): its one recovery re-registration is a `resume_from` resume when the abort was an
infrastructure failure with code and request bytes unchanged, and a full re-fly otherwise.

## 6. Verification

Gates: `scripts/checks/engineering_base_check.py`, `harness_admission_check.py`,
`results_ledger_check.py`, `tool_catalog_check.py`, `derived_media_confinement_check.py`,
`experiment_handoff_check.py`; targeted `pytest` per engineering item; WSL-marked runtime tests
where applicable. Per cell: wire-check receipt showing the request differs from the base only in
the module's channel, smoke receipt, prompt-fit receipt, hashes bound before contact, official
score once, paired analysis with the fixed seed, per-scenario tables, admission entry, ledger row.
Program: B5r inside the null band of B5 on every metric; B6 agrees in sign with B5.

## 7. Roles, cadence, budget

Fable designs, preregisters, decides and reports. Opus agents babysit flights and run the A1-A4
reads. Sonnet agents implement E1-E5 in worktrees, one item per agent. Merges land serially on
master between flights; HEAD never moves while a cell flies; CPU work runs at 8 workers during a
flight and 20 idle. Budget about 25-30 GPU-h, three to four weeks wall clock.

## 8. Out of scope

ASR or transcript states, core swap, E21/Audio2Tool flights, N/K sweeps, reuse of any ABORTED
attempt, the four-row slot-view proof, paper-scale claims, Fold B or test reads before the lock.

## Owner decisions 29-35 (2026-09-19)

Recorded in docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md. Consequences for this program: the
v2.0 lock fires on 64 / 78 replicated OR on three consecutive NEUTRAL / HARMFUL one-factor cells (30); B5b is
composed per node, never by stacking modules on one node, with competing placements flown as paired cells (31);
an L1 HARMFUL read closes B7r / B7c and re-bases B8b (32); an agent base lock document (node graph, per-boundary
context contract, knowledge stores and their construction, optimisable space per node) precedes any Stage-3
framework analysis (33); B6 reads on DEV-2000 (34); the one-shot test-split protocol is drafted now and frozen at
the lock (29).
