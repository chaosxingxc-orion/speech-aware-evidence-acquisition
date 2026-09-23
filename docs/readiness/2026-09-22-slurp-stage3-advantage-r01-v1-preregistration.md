# Cell ADV-1: the Stage-3 SYSTEM-level semantic-advantage contact on the disagreeing ROLL-1 rows: preregistration

Registered 2026-09-23 by the ADV-1 registration agent (worktree `/home/chao/saea-worktrees/fable-adv1reg`,
branch `fable/adv1reg`) at study commit `c2754ff1`, per
`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` sections S3-4 and S3-4s and
`docs/superpowers/specs/2026-09-21-slurp-stage3-training-free-rl-design.md` section 2 step 4. Before any contact.
READINESS HELD: this registration authorises no flight, no readiness flip, no decision receipt, no exposure-row
countersignature and no contact (see section 7).

## 1. Why this cell exists

Cell ROLL-1 sealed 625 construction rows with five custodied Solver samples each. S3-3 scored those samples on copies
and found **225 of the 625 rows disagreeing** (best-minus-worst official SLU-F1 > 0 within the row's N=5 group). A
disagreeing row is a row where the system could have done better with the material it already had. ADV-1 asks the
frozen core, once per such row, *what distinguished the better rollout from the worse one, and which node should do
something differently* — the group-relative semantic advantage operator of Training-Free GRPO (arXiv:2510.08191),
amended by owner decision 106 from a Solver-only reading to a **SYSTEM-level** one over perception / solver /
reviewer / planner.

## 2. The factor and the arm

There is no factor against a comparator: this is a **construction contact**, not an arm of the locked v2.0 plan. What
is fixed and registered is the contact **form**.

| item | value |
| --- | --- |
| arm | `construction-advantage-text` (a construction-visible arm; D2 field set = bare-core's ten identity/text fields plus `construction_targets`) |
| program | `phase-stage3-advantage-v2` (`configs/policy/phase-stage3-advantage-v2.json`: one phase `advantage`, `max_contacts` **1**, `stop_rule` `always-run-full-program`) |
| system template | `probes/slurp_stage3_advantage_system_v2.txt` |
| per-row template | `probes/slurp_stage3_advantage_v2.txt` |
| response format | `stage3-advantage-statement-v2` |
| parser | `rails.stage3_advantage.parse_advantage_statements_v2` |
| evidence source / scorers | `none` / `["cost"]` |
| modality | **TEXT ONLY** — `core.model.transport` forces `text_only` for this arm under the D2 freeze; no audio part and no speech-feature packet is ever opened |
| model fragment | `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1`, byte-identical to cell PLAN's and ROLL-1's |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1` (resident; attach only, never spawn or stop) |
| contacts per row | ceiling **1** (the program's own `max_contacts`), so cap = target |
| comparator | **none** (section 5) |
| smoke | the first four disagreeing rows, structural acceptance (section 4) |
| runs | `SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1` / `-FIT-V1`; smoke `-SMOKE-4-V1` / `-SMOKE-4-FIT-V1` |
| Stage-3 algorithm (decision 101) | `tfgrpo-semantic-advantage-v1`, operator `credit_assignment` |

## 3. What the contact sees, and what it answers

Rendered into the phase instruction **only**, by a caller-supplied
`core.flight.FlightRuntime.bind_phase_program_material` override built from
`rails.stage3_advantage.build_advantage_instruction_for_row_v2` over S3-3's `pairs.json` trajectory block and S3-2's
sealed rollout outputs. None of it is ever written to a receipt (proved by `tests/unit/test_stage3_advantage.py`):

1. the **Perception candidate list**, in the order the Perception node proposed it (first-occurrence distinct ids,
   with the raw count);
2. **ANSWER A** (the best sample) and **ANSWER B** (the worst sample) of this row's N=5 ROLL-1 group — custodied model
   outputs;
3. the **DELIVERED** answer with the Reviewer's verdict labels (re-derived from the sealed Reviewer response by
   `rails.review_primitives.parse_review_primitive`) and the Planner's route (action labels, revision count, delivery
   kind);
4. the row's **own construction gold**, carried by `construction_targets` — the same field and the same discipline
   `construction-proposer-text` uses (owner decision 82). Never another row's gold, never a reference transcript,
   never a future turn.

The answer is **one to three four-line blocks**:

```
NODE: <one of: perception | solver | reviewer | planner>
DELTA-KIND: <one of: intent-boundary | slot-contract | exemplar-note | perception-hint | reviewer-criterion | planner-rule>
TARGET: <the scenario_action or slot type this statement is about>
STATEMENT: <one sentence, at most 40 words>
```

The vocabularies are `rails.stage3_advantage.LEGAL_DELTA_NODES` (four) and `LEGAL_DELTA_KINDS_V2` (six: v1's three
plus one per newly addressable node, spec section S3-4s), and the committed template
`configs/probes/slurp_stage3_advantage_v2.txt` states the same six. `MAX_ADVANTAGE_BLOCKS` is 3.

An illegal block is **retained and marked**, never dropped by the parser and never repaired; S3-5's curation drops it
and this cell counts it by the parser's own reason strings (`illegal node: ...`, `illegal delta-kind: ...`,
`missing keys: ...`, `empty target`, `empty statement`, `statement exceeds 40 words (M)`,
`block i is past the 3-block form`, `no NODE/DELTA-KIND/TARGET/STATEMENT block was found`,
`response text is not a string`). A fourth and later block is likewise retained and marked, never silently dropped.

## 4. Decision rule (structural only)

This cell carries **no gating decision rule and no effectiveness claim**. The effect of the curated deltas is read at
**CELL-1**, against the plan's own null, with its own registration. Acceptance here is five structural items, each
reported with its denominator:

1. **parse rate** — contacts whose response yields at least one LEGAL block;
2. **node distribution** — legal blocks per `NODE` value, as a table (so a contact form that can only ever blame one
   node is visible before 225 rows are spent);
3. **illegal-block count** by the parser's own reason strings (illegal node, illegal delta-kind, missing keys, empty
   target, empty statement, statement exceeds 40 words, past the 3-block form, no block found, non-string response);
4. **blocks per row** — the one-to-three distribution;
5. a **clean seal** with row accounting in = out.

No threshold is pre-registered on any of the five, because a low parse rate or a degenerate node distribution is a
FORM defect that stops the arm and is root-caused, not a measured result. The four-row smoke's acceptance is the same
five items on 4 rows; **a failed smoke stops cell ADV-1 and the 225-row arm does not open.**

## 5. Comparators: none

ADV-1 answers no evaluated row, produces no answer any scorer reads, and its only output is an artifact (a set of
advantage statements) that S3-5 curates into the node-targeted `stage3-deltas-v1` store. Comparing this cell to
anything would be comparing an artifact to an answer. The registered protocol states it machine-readably:
`"comparator": null`, with that reason.

## 6. Budgets

| quantity | arm | smoke |
| --- | --- | --- |
| rows | 225 | 4 |
| per-row ceiling | 1 | 1 |
| `planned_model_calls` / `generation_calls_cap` | **225** = 225 x 1 | **4** = 4 x 1 |
| `fit_endpoint_calls_cap` | **675** = 225 x (0 speech packets + 3 endpoints) | **12** = 4 x (0 + 3) |
| `planned_speech_audio_seconds` / `repeated_speech_audio_seconds_cap` | 0 | 0 |
| `planned_gpu_hours` / `gpu_hours_fit_inclusive` | 1.0 | 1.0 |
| `native_task_contract_calls_cap` | 0 | 0 |
| `official_complete_scoring_jobs` | 0 | 0 |

**Why 225 and not the 625 this fragment was registered with.** The earlier registration carried 625 (one contact per
R01C row) explicitly as *"the registered CEILING that stands until S3-3's pairs.json names the disagreeing rows,
never a target"*, with an expected 213 from the S3-3 dry run's 0.3398 disagreement-pair rate. `pairs.json` has now
named them: 225, a measured rate of 0.36. Nothing pinned the 625 — no exposure-ledger row, no registered plan and no
decision receipt for this cell existed before this package — so the ceiling is re-registered at the exact population.
`generation_budget.target` becomes 225 as well: a one-contact-per-row program has no gap between its ceiling and its
expected volume, and cap = target is not a claim that all 225 will succeed.

**Why the fit ceiling is a reserve.** `configs/baseline/slurp-native-stage3-advantage-baseline-v1.json` declares
**neither** `native_contact_fit` (that path belongs to a `native_episode` cell, and this is a one-phase phase program)
**nor** `live_phase_fit` with `whole_roster_wave_barrier` (the pair
`core.preparation_fit.validate_live_phase_fit_config` requires). No fit gate is built at dispatch, so both FIT run ids
are expected to be charged **zero**; they are registered so that any endpoint spend under this cell's fit identity
lands against a row written before the result was read. If root ever registers a `live_phase_fit` block,
`core.preparation_fit.build_live_phase_fit_gate` requires `contact_cap` to **equal** `len(phases) * (1 + 3 * rows)`
exactly — 676 for the arm and 13 for the smoke, each **one more** than the ceiling registered here, because that
formula charges one extra whole-roster barrier contact per phase. The ceiling would have to be re-registered first;
this package does not attempt it. `coordinate-fit` must **not** be run.

Budgets are run-cumulative across every attempt of a run id; ceilings are bounds, never targets.

## 7. What this registration does NOT authorise (readiness held)

`readiness.state` is `"held"` on all four cells. No decision id is minted, no `scripts/flights/repin_cell.py
--set-ready` has run, no exposure row is countersigned (all four read `consumed = no` and carry
`REGISTERED BEFORE CONTACT (draft, root countersignature pending)`), and neither cell is on the batch queue. No model,
tokenizer, encoder, ASR, scorer, server, network or paid-API contact was made by this registration.

**No decision requirement is registered in either fragment on purpose** (the ROLL-1 precedent):
`core.flight.repin._upsert_decision_requirement` inserts it at the flip, and a placeholder entry without an
`expected_decision_id` would be left beside it and refuse the campaign at load
(`core.flight.campaign.declared_readiness`).

**No prepared phase supply is pinned**, and none is owed: `phase-stage3-advantage-v2`'s single phase declares
`knowledge: none` and the baseline declares `evidence_source: none`, so there is no supplied first phase to prepare
and `core.flight.repin` reports *"program has no supplied first phase to prepare"*. The only readiness requirement
either cell carries is S3-3's `pairs.json`, already satisfied and pinned by hash.

## 8. Boundary

`construction-advantage-text` makes this row's own construction gold visible to the frozen core, so
`contracts.gate_exposure._require_construction_role_for_visible_targets` refuses the touch unless the **flying cell's
own** `split_identity_hash` is that of a committed `roster_role='construction'` roster of carrier `slurp` and the
split role is `discovery`. Both populations therefore carry a committed receipt of their own — the gate knows nothing
about parent rosters and would refuse a four-row subset of one:

| population | receipt | rows | split identity |
| --- | --- | --- | --- |
| arm | `docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json` | 225 | `7c603857503faacbc40999d0dd939202ac141ba50aac3fb5e3594542931c46d7` |
| smoke | `docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-smoke-4-v1.json` | 4 | `8cbdb0acece69a74145685ab1b6452d494ac86a82b6b18b260cec66d36264762` |

Both are **pure selections with zero contacts** (the `SLURP-EVO-S1-PROPOSER-R01` precedent), written by
`scripts/flights/batch/adv1_prepare_steps.py` (`roster` and `smoke-roster`); the smoke's four rows are the first four
items of the arm's receipt in that receipt's own order (ascending `sample_id`) — no quality-based selection, no score
read, no separate draw.

**Nothing reaches an evaluated row.** TRAIN Fold A, TRAIN Fold B, DEV-1000, DEV-2000, DEV-2000-ADDED and the test
split stay untouched and unread; the S3-1 draw excluded all six by construction (owner decision 81) and R01C further
removed the 175 knowledge-source rows. The 225 rows are a strict subset of the 625 ROLL-1 already flew, so this cell
opens **no new speech identity** — and, being text-only, opens no speech at all. What is new is the *visibility* of
those 225 rows' own gold, which owner decision 82 authorises for a construction-role roster.

## 9. The S3-3 facts this cell is built on

Read model-free from `pairs.json`'s own trajectory block (`saea-stage3-rollout-pairs-v2`) — ids, labels, counts and
hashes only:

- **225 of 625** construction rows disagree (rate 0.36; the S3-3 dry run predicted 0.3398,
  `docs/readiness/2026-09-22-slurp-stage3-rollout-r01-v1/s3-3-dry-run-receipt-v1.json`).
- The **gold intent is among the Perception candidates on 194 of the 225**. On the other 31 no Solver choice could
  have recovered it, so Perception is the responsible node by construction — which is exactly the kind of attribution
  the SYSTEM-level v2 block form exists to elicit.
- **Zero truncated nodes** in the sealed rollout: no contact hit the 512-token output cap, so no best/worst pair is an
  artefact of truncation.

## 10. Known gap (diagnostics only)

`pairs.json`'s per-row `delivered_below_best` flag is **vacuous in this seal** and must not be read as a rate. The
sealed ROLL-1 run carries the delivered answer's own official score under the scorer id `slurp-slu-official-train`
(the campaign's one complete official score at finalize), while S3-3 scored the five custodied samples offline under
`slurp-slu-official-projected-v3-train`. `delivered_below_best` compares the delivered score to the best *sample*
score, so it compares two different scorer ids, and where the delivered score is absent under the projected-v3 id the
flag falls back to its own absent/False reading rather than a measurement.

It is rendered into no instruction, feeds no decision rule and appears in no verdict table. **The best/worst pair
itself is unaffected**: both of its sides are sample scores under the same projected-v3 id, and that pair is what the
advantage contact is shown. Closing the gap means re-scoring the delivered path under the projected-v3 id in a
separate model-free act; this package does not attempt it.

## 11. What is registered

Package `docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1/`:

| file | what |
| --- | --- |
| `README.md` | the pre-existing runbook and S3-4s amendment record |
| `fill-after-roll1-seal.json` | the fill map, now fully applied |
| `protocol-registered-v1.json` | the registered protocol (form, population, decision rule, accounting, fit, boundary, S3-3 facts, known gap) |
| `generation-plan-registered-v1.json` | arm generation plan, cell `slurp-native-stage3-advantage-r01-v1` |
| `fit-plan-registered-v1.json` | arm fit plan (registration reserve), cell `slurp-native-stage3-advantage-r01-fit-v1` |
| `smoke-generation-plan-registered-v1.json` | smoke generation plan, cell `slurp-native-stage3-advantage-r01-smoke-4-v1` |
| `smoke-fit-plan-registered-v1.json` | smoke fit plan (registration reserve), cell `slurp-native-stage3-advantage-r01-smoke-4-fit-v1` |

plus the campaign plan `configs/campaign/slurp-native-stage3-advantage-r01-v1.json` (arm only; a smoke is a standalone
worker, the ROLL-1 precedent), the four config fragments, the two roster receipts, four unconsumed exposure-ledger
rows, and the runbooks `scripts/flights/batch/adv1_repin_smoke.sh`, `adv1_repin_arm.sh`, `adv1_flip_both.sh`,
`batch_chain_adv1.sh`.

The package deliberately carries **no** un-suffixed `*-plan-v1.json` twins. In the ROLL-1 package those were
byte-identical duplicates of the `-registered-v1.json` plans that nothing reads: `core.flight.repin` globs
`readiness_dir/*.json`, `scripts/flights/batch/repin_loop_generic.sh` reads only
`<smoke-generation|generation>-plan-registered-v1.json`, and the exposure-ledger `artifacts` column points only at the
registered plans. Two files that must stay in sync and prove nothing are a defect surface, not evidence.

## 12. Registered hashes

| run id | cell | plan | composed config | protocol hash | split identity |
| --- | --- | --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1` | `...-r01-v1` | `generation-plan-registered-v1.json` | `9a4f061c5e3f9e52512a9369b4240cdc9b10460be7e62d6b12db3752e07ca055` | `67779678aa0ee76764b94829c51a208fd251f6e9b4aa9dd5ddcd9f40f3c1f154` | `7c603857503faacbc40999d0dd939202ac141ba50aac3fb5e3594542931c46d7` |
| `SAEA-SLURP-STAGE3-ADVANTAGE-R01-FIT-V1` | `...-r01-fit-v1` | `fit-plan-registered-v1.json` | same | same | same |
| `SAEA-SLURP-STAGE3-ADVANTAGE-R01-SMOKE-4-V1` | `...-r01-smoke-4-v1` | `smoke-generation-plan-registered-v1.json` | `3dd482a3c8e87c8ef1157a3cdc0172d0a5a2e7b6531d9c06d5ddc8062276d384` | `1c5598f6d9fe870a45bd68a8d2c333dd61dcdb4cff7807f9fbb7b5423d76d3ef` | `8cbdb0acece69a74145685ab1b6452d494ac86a82b6b18b260cec66d36264762` |
| `SAEA-SLURP-STAGE3-ADVANTAGE-R01-SMOKE-4-FIT-V1` | `...-r01-smoke-4-fit-v1` | `smoke-fit-plan-registered-v1.json` | same | same | same |

Protocol document `protocol-registered-v1.json` sha256 `239bb27e86731dc19de11adeac104bb43deb7bff3120246a4ce705aaf109be00`. S3-3's `pairs.json`
(`analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1/pairs.json`, schema `saea-stage3-rollout-pairs-v2`) sha256
`d66cd80104e2ec9161057a8e4f587dac981e701f347c2fce3c5dce40cba6ef80`.

**Every one of these hashes moves at the readiness flip** (the flip edits the readiness block, which `compose()`
hashes), and `scripts/flights/repin_cell.py` rewrites the plans, this note, the README and the four ledger rows in
dependency order.

## 13. Blocking defect to repair BEFORE the flip

`core.flight.cli check` **refuses all four cells today**, so the readiness flip would refuse too
(`scripts/flights/repin_cell.py` runs `check` and asserts the runtime-derived hashes agree). Exit code 1 on each,
with:

```
CoreError: task_instruction_template requires task_instruction_fill naming a registered instruction fill
```

raised from `rails.adapters.slurp_runtime.build_runtime_adapter` line 203, which computes
`instruction = resolve_active_task_instruction(...) or resolve_task_instruction(...)`.

**Why.** `configs/baseline/slurp-native-stage3-advantage-baseline-v1.json` declares
`task_instruction_template: "probes/slurp_stage3_advantage_system_v2.txt"` with `task_instruction_fill: null`.
`core.instructions.resolve_task_instruction` accepts exactly two spellings: a **literal** `task_instruction`, or a
template **plus** a registered fill **plus** a single `{tool_schemas}` placeholder in the template. The system v2
probe is a static system message with no placeholder and the fragment names no fill, so neither spelling is
satisfied and the refusal is unconditional. `resolve_active_task_instruction` returns `None` first (no literal, no
`task_instruction_template_active`), which is why the `or` falls through to the refusing resolver rather than to the
adapter's own hard-coded text.

**Provenance.** Pre-existing in the committed arm registration at study commit `c2754ff1`
(`git show c2754ff1:configs/baseline/slurp-native-stage3-advantage-baseline-v1.json` carries the same two keys). The
2026-09-23 registration agent did not modify that file. The smoke baseline inherits the keys **deliberately**: the
smoke must fly the arm's form key for key, and a smoke that proved a different system message would prove nothing.

**The two supported repairs.**

- **(a) literal** — replace `task_instruction_template` / `task_instruction_fill` with a literal `task_instruction`
  carrying the system v2 probe's exact text, keeping the probe relpath and sha256 beside it as provenance.
  Byte-identical wire text to what the registration intended; no code change; the probe stays committed and pinned in
  `configs/probes/manifest.json` but stops being the thing that is read.
- **(b) fill** — register an instruction fill in `core.base.INSTRUCTION_FILLS`, add the single `{tool_schemas}`
  placeholder to the system v2 probe, re-pin the probe in `configs/probes/manifest.json`, and name the fill in
  `task_instruction_fill`. Keeps the probe as the read artifact but changes committed probe bytes and adds code.

Choosing between them decides what the frozen core sees as its system message and whether committed probe bytes move,
so it is a registration decision for root, not a mechanical repair, and this package does not make it. Both fragments
are left byte-consistent with each other so the chosen repair can be applied to both in one edit. Applying it
re-composes both config hashes — which the re-pin cycle rewrites anyway.

### 13a. Second blocking defect, found at the first launch and repaired (2026-09-23)

The section 13 defect was repaired and both cells were flipped to ready. The smoke then **refused at
its first contact, before any model call was spent**, on a second, independent defect. The attempt
`attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-generation` was opened and carries **zero
contacts**.

```
FrozenCoreError: speech feature request query_source must be 'speech_features'
```

raised from `core/model/transport.py` `render_request_with_receipt`.

**Why.** The composed model fragment
`q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` declares
`prompt_order: speech-query-prefix-v2` -- it is the **resident** np4 serving geometry. ADV-1's
dispatch is the text-only construction path
(`core.flight.runtime._run_construction_proposer` -> `rails.core_client` ->
`core.policies.build_arm_payload`), whose D2-frozen payload is the rendered instruction as the system
message, an **empty** user content list, `construction_targets`, and **none** of the five
speech-feature fields. The renderer had no branch for that pair. A new fragment could not have fixed
it: `prompt_order` is inside the **compared** session identity (`model_fragment_sha256` hashes the
whole fragment; `core.session.serving.SERVING_IDENTITY_FIELDS`), so a fragment declaring a text
prompt order cannot attach to the resident session.

**Repaired in the renderer.** A dedicated text-only construction branch: under a speech prompt order,
a construction-visible payload renders exactly as `evidence-first-system-v2` renders it (system
instruction, empty user content, zero audio parts, zero speech packets), with a render receipt
carrying `text_only_construction: true` and the reason. A construction-visible payload that also
carries a speech-feature field, a media part or a non-empty `history` is refused by name; every other
payload under a speech order keeps its refusals in the same order. Covered by
`tests/unit/test_llama_server_transport.py`, including an end-to-end test that renders the payloads
`FlightRuntime.wire_check` actually builds for this arm under the flown fragment's own
`prompt_order`. Nothing about the contact form, the population, the templates, the response format,
the caps or the decision rule moves.

## 14. The coordinator's sequence

On the main checkout, after merging `fable/adv1reg` **and after repairing section 13**. Nothing below was performed by
the registering agent.

**1. Mint the decision receipt** (`scripts/flights/batch/mint_decision_receipt.py`, from the sealed ROLL-1 receipt),
WSL, from the study root:

```
python scripts/flights/batch/mint_decision_receipt.py \
  --from stage3-rollout-r01 --from-tag STAGE3-ROLLOUT-R01 --from-date 2026-09-22 \
  --name stage3-advantage-r01 --tag STAGE3-ADVANTAGE-R01 --date 2026-09-22 \
  --expected-contacts 225 --expected-gpu-hours 1.0 \
  --replace 'SAEA-SLURP-STAGE3-ROLLOUT-R01-=SAEA-SLURP-STAGE3-ADVANTAGE-R01-' \
  --replace 'attempt-slurp-native-stage3-advantage-r01-smoke-4-generation-recovery-v1=attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-generation' \
  --replace 'attempt-slurp-native-stage3-advantage-r01-smoke-4-generation-v1=attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-generation' \
  --replace 'attempt-slurp-native-stage3-advantage-r01-smoke-4-fit-v1=attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-fit' \
  --replace 'attempt-slurp-native-stage3-advantage-r01-generation-v1=attempt-slurp-native-stage3-advantage-r01-v1-generation' \
  --replace 'attempt-slurp-native-stage3-advantage-r01-fit-v1=attempt-slurp-native-stage3-advantage-r01-v1-fit' \
  --replace 'slurp-native-stage3-rollout-smoke-4-baseline-v1=slurp-native-stage3-advantage-smoke-4-baseline-v1' \
  --replace 'slurp-native-stage3-rollout-baseline-v1=slurp-native-stage3-advantage-baseline-v1' \
  --replace 'f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515=7c603857503faacbc40999d0dd939202ac141ba50aac3fb5e3594542931c46d7' \
  --replace 'e9dcea536028d17737b999c65267e47645ca7b3f6f9c4f57622961cf29363ed5=8cbdb0acece69a74145685ab1b6452d494ac86a82b6b18b260cec66d36264762' \
  --decision "<one sentence: what is admitted>" \
  --authority "<owner decisions 82 / 101 / 106; spec S3-4 and S3-4s>" \
  --claim-boundary "<structural only; no effectiveness claim; the effect is read at CELL-1>"
```

The `--replace` pairs are applied in order, after the tool's own five id substitutions. The first is needed because
the ROLL-1 run ids carry no `NATIVE` infix; the five `attempt-` pairs are needed because ADV-1 names its attempts
`attempt-<cell-id>-<role>` where ROLL-1 names them `attempt-<cell>-<role>-v1`; the two baseline pairs are needed
because those fragment names carry no `-r01-` segment; the two hash pairs rewrite ROLL-1's split identities to
ADV-1's. The tool re-hashes every referenced repository file automatically. **Check after minting** that
`eligible_run_ids` names exactly the four ADV-1 run ids, that no `stage3-rollout` / `ROLLOUT` / `f56bc386` /
`e9dcea53` substring survives, and that the decision id is `slurp-stage3-advantage-r01-admission-v1`.

**2. Flip smoke, then arm** — one cycle, on the clean tree:

```
bash scripts/flights/batch/adv1_flip_both.sh
```

which drives `repin_loop_generic.sh` over `adv1_repin_smoke.sh` and then `adv1_repin_arm.sh`. Each pass re-pins with
`scripts/flights/repin_cell.py --set-ready`, commits, and re-runs until the freshly composed hashes and the registered
documents agree.

**3. Chain the flight** (smoke first, then the arm), through the batch driver only (decision 77):

```
bash scripts/flights/batch/batch_chain_adv1.sh
```

Expected rows 4 then 225, one contact per row, ceiling 1, tool-free, session
`serving-slurp-native-candidate-five-train-a-np4-v1`. The arm opens only after the smoke seals.

**4. Countersign** the four exposure-ledger rows as the flights consume them. Do not countersign before contact.

### 14a. Recovery re-registration after the refused first launch (2026-09-23)

The sequence above was executed through step 3 and the smoke's first launch was **refused before
contact** (section 13a). This is the **one** root-diagnosed recovery re-registration the failure rule
allows for this flight.

**Changed, and only this:** the smoke GENERATION cell's attempt id becomes

```
attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-generation-recovery
```

in `configs/experiment/slurp-native-stage3-advantage-r01-smoke-4-v1.json` and as `smoke_attempt_id`
in `scripts/flights/batch/batch_chain_adv1.sh`.

**Unchanged:** the smoke fit attempt id
(`attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-fit`), both arm attempt ids
(`attempt-slurp-native-stage3-advantage-r01-v1-generation` / `-fit`), all four run ids, the
population, both roster receipts, the two templates, the response format, every cap and the decision
rule. The refused attempt is left in place as the record of the refused launch; budgets are
**run-cumulative** across every attempt of a run id, so its zero contacts count against the same
4-contact ceiling.

**Coordinator:** re-run step 2 (`bash scripts/flights/batch/adv1_flip_both.sh`) so the re-pin rewrites
the registered smoke documents and the ledger row to the recovery attempt id and to the freshly
composed hashes, then step 3. The readiness states and the registered plan hashes were NOT edited by
hand.
