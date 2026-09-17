# Cell B1 on the sealed anchor base: the one root-diagnosed recovery, registered before contact

Status: **REGISTERED BEFORE CONTACT.** Author: the B1 recovery registration agent, worktree
`/home/chao/saea-worktrees/fable-b1-recovery`, branch `fable/b1-recovery`, base commit `cfbb5f8b`
(the merge that carries the E3c fix `f2595f4c`).

This note is the **addendum** to
[`2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md`](2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md),
whose bytes are pinned by the sealed root decision `slurp-b1-exemplars-k20-anchor-admission-v1` and
are therefore **not edited**. Everything the preregistration says about the question, the arms, the
metrics, the resampling, the decision rule, the containment proof, the prompt fit and what is not
claimed stands unchanged. Section 11 of that document allows *at most one root-diagnosed recovery
re-registration per run*. This is it.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried; no run directory was
modified; cell B4b's flight was not touched.

## 1. What happened

Run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2`, attempt
`attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-v2`, flight commit `ecc6ecea`,
**ABORTED at 2026-09-17T09:52:35Z** on the first row whose Planner routed `REVISE`. The recorded
failure is, verbatim from
`attempts/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2/attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-v2.json`:

```
generation failed during run_phases or seal: NativeEpisodeError: native episode node failed:
[100054] component 'solver_1_input' execute 'invoke' error, reason='phase supply selected values
already visible in this trajectory: ['train-exemplars::value:12925', ... 20 ids ...]; a
FusionDecision must exclude QueryState.retrieved_value_ids (rails.kb_policy's own fuser does)',
workflow='749cbc8893344ecd843dfe919c7341e0'
```

The mechanism, in one sentence: a prepared phase supply is a pure function of (phase, sample), so
when the Planner routed `REVISE` and the Solver was entered a **second** time the same twenty
`train-exemplars` values came back, they were already in `QueryState.retrieved_value_ids` from the
first Solver visit, and `rails.controllers.EvidenceAgentController._acquired_ids` refused the
decision by name.

**Why the smoke did not catch it.** The four-row smoke
(`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-V2`, sealed at study commit `0dbd0d1d`) ran
perception 1 / solver 1 / reviewer 2 / planner 1 on every row and **all four rows routed ACCEPT**.
The anchor's own revisions are rare — five executed revisions in 1,080 rows — and the failure needs
exactly one of them. A four-row ACCEPT-only smoke cannot reach the path.

## 2. What was spent, and what is preserved

| item | value |
| --- | --- |
| attempt state | `ABORTED` |
| generation calls | 420 |
| repeated speech seconds | 911.865938 |
| complete rows | 84 (5 contacts each: perception 1, solver 1, reviewer 2, planner 1, all `ACCEPT`) |
| request-fit receipts | 420 under `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-FIT-V2/` (1,680 FIT endpoints) |
| trace | `runs/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2/attempt-…-generation-v2/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2.trace.jsonl`, 2,350 records: 420 `MODEL_REQUEST`, 420 `MODEL_RESPONSE`, 420 `MODEL_WIRE_RESPONSE`, 420 `COST`, 670 `USE` |
| flight receipts | `…/flight-receipts.json`, receipts hash `18f5547ce897e226f4f22ac6fe3bb63c5c55377f902b351eb10e4691b0ff6bbd` |
| flight lock | preserved and then reconciled by root, receipt `coordination/slurp-b1-exemplars-k20-anchor-v2/flight-lock-reconciliation-20260917T100537Z.json` |
| score | none. No official scoring job ran and **no partial quality read was taken or is permitted** |

Everything above is **read-only**. Nothing under the run directory was modified by this
registration. The two exposure rows
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2` and
`…-TRAIN-FOLD-A-FIT-V2` are now `consumed = yes` and carry the abort, the root cause and the
recovery run ids in their notes. **Neither run id nor either attempt id is ever reused.**

## 3. The fix, and its proofs

`rails.controllers.restrict_repeat_visit_supply`, commit `f2595f4c`, merged `cfbb5f8b`. A phase this
trajectory has already answered — proved by its own sealed `state_kind="phase:<name>"` artifact —
has its decision restricted to the values not yet in `QueryState.retrieved_value_ids` (exactly what
`rails.kb_policy`'s own fuser does before it ever builds a decision). A filtered `FusionDecision` is
built, never filtered ids alone, so `_validate_agent_knowledge_decision` still sees
`new_value_ids == fusion_decision.selected_value_ids`; a revisit that acquires nothing returns
`None` and the wave seals an ordinary `organize` step. The supplied values still reach the revisited
request, because every post-Perception request renders from the accumulated `QueryState`.

Two invariants keep it repeat-visit-only: the **first** visit of every phase returns the caller's own
object (so its transition, its `new_value_ids` and its rendered request bytes are unchanged, and
`_acquired_ids` keeps its original purpose on a genuinely new acquisition), and facet exposure is
decided from the decision **as given**, so a value-only supply whose values are all visible yields
`None` rather than promoting its facets into a `knowledge_role="key"` block the first visit never
carried.

**Proof 1 — the committed tests.** `tests/unit/test_phase_supply_repeat_visit.py`, model-free, four
tests, all passing on this branch:

| node id | what it pins |
| --- | --- |
| `::test_revise_route_re_enters_the_supplied_solver_without_reacquiring` | the B1 abort route completes; one acquire transition; the twenty values render exactly once on the second Solver request; no key block |
| `::test_first_visit_supplied_request_bytes_and_transitions_are_unchanged` | the supplied first-visit request digests (`perception/1 a097af24…`, `solver/1 febb3f0f…`, `reviewer/1 d8bd4328…`, `planner/1 a0f7f955…`) and five transition digests, captured from the **pre-change** tree (master `93bbb3ad`) |
| `::test_anchor_without_phase_supply_renders_identically` | the no-supply anchor shape: seven request digests and eight transition digests, also pinned pre-change |
| `::test_first_visit_of_another_phase_still_refuses_an_already_visible_value` | the original `_acquired_ids` refusal still fires on a genuinely new acquisition |

**Proof 2 — the REVISE path on real ids.** Receipt
`coordination/slurp-b1-exemplars-k20-anchor-recovery-v2/revise-path-proof-v1.json`. Five REVISE
episodes through the **real** OpenJiuwen role graph (`openjiuwen-workflow-v1`), the real
`rails.runner.run_speech_native_agent_loop` and the real request gate over the shared fake transport
— zero model, tokenizer, encoder, scorer and server contacts:

- scenario **A**: the exact twenty `train-exemplars` value ids the aborted attempt's own failure
  record names;
- scenarios **B** (four): the per-row selections of the **real prepared smoke supply artifact**
  `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-RECOVERY-V2/phase-supply-v1.json`.

In every one: the Planner routes `REVISE` then `ACCEPT`, the role visits are
`perception, solver, review, planner, solver, review, planner`, the supply is consulted on **both**
Solver entries, exactly **one** acquire transition is emitted, every supplied value renders exactly
once on **both** Solver requests, no `[key …]` block appears on either, and the final `QueryState`
holds the supply's value ids exactly once each. Value **content** is synthetic in this proof; only
the value **ids** are real, and no utterance text or gold enters it.

All five scenarios pass. On the pre-fix tree this route is exactly what died.

## 4. Why nothing else changes

The failure is a **runner/controller** defect on a re-entered phase. It is not a roster, prompt,
knowledge, retrieval, budget, geometry or scoring defect, and it gives no information about the
question cell B1 asks. So:

- **no roster or split change.** Same 1,080-row TRAIN Fold A roster, same
  `SLURP-EVO-FOLD-A-V2`, same split identity
  `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, same ordered ids. The 84 rows
  the aborted attempt completed are **not** filtered out and **not** reused — the recovery flies the
  whole roster from row one, as one complete manifest.
- **no prompt, role-graph or instruction change.** Reviewer 3 / planner 1 / solver 1 /
  perception 1, `max_revisions` 1, policy `phase-native-candidates-review-revise-v1`, the same six
  composed instruction texts, the same `phase_tools` Reviewer task-contract authority.
- **no knowledge or retrieval change.** The same three stores with the same pinned release and
  snapshot hashes; the same `train-exemplars` plain top-k = 20 over the same 9,354-facet pool,
  keyed by the same sealed Fold A speech vectors.
- **no cap change.** 11,880 generation contacts, 47,520 FIT endpoints, 33,930 repeated speech
  seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete
  score (smoke 44 / 176 / 117 s / 1.0 GPU-h / 24 tool calls, zero scoring jobs). These are the
  aborted arm's own registered ceilings, unchanged, and they remain bounds rather than targets.
- **no geometry or session change.** The same resident session
  `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, 24,576-token slot, four slots.
- **no decision-rule change.** The TRAIN A own-null margins (SLU micro 1.1218, intent 1.0051) and
  the read-once rule are exactly as preregistered.

What *does* change is bookkeeping only: new run and attempt ids, this package's own
`native_contact_fit` identity, its own two speech-feature identity ids (provenance only), and its own
prepared-supply pin.

**Budget accounting.** The 420 calls and 911.865938 repeated speech seconds the aborted attempt
durably spent are charged to the **closed** run id, not to the recovery run. The recovery run's own
plan covers its own worst case at the unchanged program ceiling.

## 5. The recovery cells

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-exemplars-k20-anchor-train-fold-a-recovery-v2`, run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`, attempt `attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2` |
| arm FIT | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-FIT-RECOVERY-V2` / `attempt-slurp-native-exemplars-k20-anchor-train-fold-a-fit-recovery-v2`, 47,520 endpoints |
| smoke cell | experiment and cell `slurp-native-exemplars-k20-anchor-smoke-4-recovery-v2`, run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-RECOVERY-V2`, attempt `attempt-slurp-native-exemplars-k20-anchor-smoke-4-generation-recovery-v2` |
| smoke FIT | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-FIT-RECOVERY-V2` / `attempt-slurp-native-exemplars-k20-anchor-smoke-4-fit-recovery-v2`, 176 endpoints |
| baselines | `configs/baseline/slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2.json`, `configs/baseline/slurp-native-anchor-exemplars-k20-smoke-4-recovery-v2.json` |
| experiments | `configs/experiment/slurp-native-exemplars-k20-anchor-train-fold-a-recovery-v2.json`, `configs/experiment/slurp-native-exemplars-k20-anchor-smoke-4-recovery-v2.json` |
| campaign plan | `configs/campaign/slurp-native-exemplars-k20-anchor-train-fold-a-recovery-v2.json` |
| composed / protocol (arm) | `114b791752e160ed0f409fedf12d034b3cc05a8789b4423d1700cc6cb7df000c` / `c66d507d1ae03c081d04a72dda7b5be28c29d7d5d22e4f196c38e5912211da2d` |
| composed / protocol (smoke) | `d0876577fb59f17e473b28d0a2ac93c6a983e72a1c2e3b918f84f00c9dcf3900` / `60442419416f8d02aea230dd496ed398e8f316ca5c046e402854bf144aaccede` |
| prepared supply (arm) | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2/phase-supply-v2.json`, SHA-256 `4892dbe8173f480a77dd48f34171eba78bfd029a530efa6b095db4f744b00a00` |
| prepared supply (smoke) | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-RECOVERY-V2/phase-supply-v1.json`, SHA-256 `26a4f0167b91d3a1776f56e966fc18d9f0a1d05f8f603e22a1374ff08d003078` |
| plans | `docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1/` — four prospective and four `-registered` plans, the recovery protocol document and the recovery analysis recipe |
| readiness | both cells `held` with the `preparation` requirement pinned; the coordinator adds the `decision` requirement and flips with `scripts/flights/repin_cell.py` |

The two baseline fragments are the v2 baselines **unchanged** except `what_this_is`, the
`native_contact_fit` run and attempt identity (caps unchanged: 47,520 and 176), the two
speech-feature identity ids, and the prepared-supply pin. The two experiment fragments are the
pre-flip (`343e3b59`) v2 experiments unchanged except the cell, run, attempt, experiment and
fragment-kind ids, the preparation pin, the readiness reason and the failure/purpose prose.

**The prepared Perception supply is byte-identical to the sealed anchor's.** `prepare-supply` was
re-run model-free at 4 workers on this commit for both cells and each artifact's Perception `output`
reproduces the sealed anchor's exactly: `output_sha256`
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` on **1,080 of 1,080** rows for the
arm, and `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` on **4 of 4** rows for
the smoke. The same `compose`/`protocol_hash` command run on the sealed anchor's own fragments
returns the anchor's registered protocol hash
`2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c`, so the method is verified.
Receipt: `coordination/slurp-b1-exemplars-k20-anchor-recovery-v2/prepared-supply-and-hashes-v1.json`.

**The twin is untouched.** `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2` keeps its
own unflown v2 registration, `consumed = no`, readiness `held`. It never contacted the model, so
nothing about it needs re-registering; it will fly **on this fixed code** and only after the arm's
paired read shows a positive CI95 against the base (owner decision 8 of 2026-09-17).

## 6. The request envelope: what moves, and what cannot

Receipt `coordination/slurp-b1-exemplars-k20-anchor-recovery-v2/request-envelope-comparison-v1.json`.

The aborted attempt's trace holds **420 sealed `MODEL_REQUEST` payloads** — 84 rows × five contacts,
every one a **first visit** of its phase (`perception` 84, `solver` 84, `reviewer` 168 across two
visits, `planner` 84). They are the exact bytes the aborted arm sent, and they are the reference the
recovery arm is compared against:

1. **Config diff.** The recovery configuration differs from the aborted one only in
   `what_this_is`, `native_contact_fit.{run_id,attempt_id}`, the two `speech_feature_*_id` values,
   `prepared_phase_supply`, and the experiment fragment's own cell/run/attempt/readiness
   bookkeeping. Every model-facing key — `policy`, `native_episode`, `phase_material`, `phase_tools`,
   `knowledge_stores`, `task_instruction_template`, `serving_slot_tokens`, the packets — is
   byte-identical.
2. **None of those strings is in any request.** Every one of the 420 sealed payloads is searched, on
   every field, for the aborted run id, the aborted attempt id, both aborted speech-feature ids, the
   two recovery run ids, the recovery attempt ids and both recovery speech-feature ids. The receipt
   records the result per row and per phase.
3. **The payload's own `key_representation_id` and `matcher_policy_id` are program-derived, not
   config-derived.** They read `phase-native-candidates-review-revise-v1:<phase>` and
   `phase-native-candidates-review-revise-v1`, so the baseline's speech-feature identity ids — the
   one pair this registration deliberately makes unique — do not reach a request byte at all.
4. **Per-row per-phase digests are pinned.** For each of the 420 payloads the receipt records a
   SHA-256 over the whole payload minus `request_id` and the `evidence_provenance` message relpaths
   that are derived from it (`rails-message/flight-NNNN/i`, a per-flight sequence number). The
   recovery flight must reproduce these digests on every row and phase.
5. **The whole-roster render agrees.** `core.flight.cli check`'s pre-flight prompt budget renders the
   widest request each phase produces across all 1,080 rows and hashes it (`payload_sha256`). The
   recovery cell's four per-phase digests are compared against the aborted attempt's own sealed
   pre-flight receipt.

**Measured.** 57 composed-config keys are byte-identical and ten differ, all bookkeeping: the five
baseline keys named above and the experiment fragment's own `cells`, `experiment_id`,
`fragment_kind`, `failure_policy` and `purpose`. All twelve identity strings — both run ids, both
attempt ids and both speech-feature ids of each registration — return **0 hits across all 420 sealed
payloads**, on every field, on every row and phase. The whole-roster pre-flight render is
**byte-identical on all four phases**: `perception 2576cb36…`, `reviewer 164d4327…`,
`planner 5150f014…`, `solver 7ad717e2…`, each equal to the aborted attempt's own sealed pre-flight
`payload_sha256`, with the same required-window token counts (19,184 / 19,047 / 18,987 / 21,012) and
ALLOW on every phase.

**The honest limit:** the recovery arm has not flown, so its own realized post-Perception requests
cannot be re-derived model-free — they depend on the frozen core's answers, and greedy decoding at
`temperature 0` is not bitwise reproducible across batch compositions. What is proved here is that no
configuration byte that reaches a request moved and that the whole-roster render is identical per
phase; what is pinned is the per-row per-phase table the recovery flight is checked against.

## 7. Launch

Exactly the v2 runbook (`2026-09-17-slurp-b1-exemplars-k20-anchor-v2/README.md` sections 2–7), with
the recovery names. Flip the **smoke first**, commit, fly it, then re-pin and flip the arm.

```bash
export REPO=<the clean detached worktree carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"

$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-exemplars-k20-anchor-smoke-4-recovery-v2 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1 \
  --preregistration docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1.md \
  --decision coordination/slurp-b1-exemplars-k20-anchor-v2/root-admission-v1.json \
  --decision-id slurp-b1-exemplars-k20-anchor-admission-v1 \
  --set-ready
```

Then the same command with `--experiment slurp-native-exemplars-k20-anchor-train-fold-a-recovery-v2`
once the smoke seals. The arm then runs through
`configs/campaign/slurp-native-exemplars-k20-anchor-train-fold-a-recovery-v2.json`.

The re-pin tool rewrites this note, the recovery plan directory and the four recovery ledger notes;
it does **not** touch the v2 package, whose plan files and preregistration keep their sealed hashes,
and it refuses if any target exposure row is already `consumed = yes`.

## 8. Failure rule, restated

This registration **is** the one root-diagnosed recovery the preregistration allows for cell B1. A
second failure closes this flight: no third registration, no replay, no row filtering, and the fix
must be proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke
stops the recovery on the same terms.

## 9. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b1-exemplars-k20-anchor-recovery-v2/`, outside the
repository so no receipt can dirty the tree the manifest reads at finalize.

| receipt | SHA-256 | what it proves |
| --- | --- | --- |
| `prepared-supply-and-hashes-v1.json` | `eb2e9b3f66eab78fba75631d40b765231f1448d838d9dfa7d72e1a76371feecd` | the two prepared artifacts pinned, their Perception `output` identical to the sealed anchor's on 1,080 / 1,080 and 4 / 4, the composed and protocol hashes, the implementation-pin comparison against the aborted arm's own artifact, and the anchor method check (the same command on the anchor's fragments returns `2527b527…`) |
| `prepare-supply-…-train-fold-a-recovery-v2-v1.json` | `076594e50abd4a29df5adf5f498ddb6c38f0d3e0f1c374c70a9f95cf6f0cf0fa` | the raw model-free `prepare-supply` receipt for the arm |
| `prepare-supply-…-smoke-4-recovery-v2-v1.json` | `6c18e4c7ced8c8b4064427c75527f324e12f7ecd9dc801877315841e6c495a82` | the raw model-free `prepare-supply` receipt for the smoke |
| `revise-path-proof-v1.json` | `078dd94ff6b79f02a9bdd5ef104b7be847c42a9ca908d099bfc03a0d4ad38e5c` | five real-id REVISE episodes through the real role graph, all passing; the four E3c test node ids and their pinned pre-change request and transition digests |
| `request-envelope-comparison-v1.json` | `5ee60cdf5395f7aea63a98e128381391b65eda5e37a9ab275f504d8012d907bb` | the composed-config diff (57 keys identical, 10 bookkeeping keys differ), the 420-payload identity search (0 hits on all twelve strings), the per-row per-phase model-facing payload digests, and the whole-roster pre-flight render comparison (identical on all four phases) |
| `check-…-smoke-4-recovery-v2-v1.json` | `b0229f77cd934fd1e11693fda10eab4d8fd8dc0dbaccd05427619278f408ee79` | runtime `check` at study commit `49002dbc`: config `2f1c299a…`, 4 samples, readiness `held`, `generation_authorized false`, prompt budget ALLOW on all four phases (Solver 21,012 required, margin 3,564) |
| `check-…-train-fold-a-recovery-v2-v1.json` | `8b79424619e6de4fb68527579f08278a4e517a0e46467ddce51cd9116f01e8f5` | runtime `check` at study commit `49002dbc`: config `b15374a9…`, 1,080 samples, readiness `held`, `generation_authorized false`, prompt budget ALLOW on all four phases |
| `ledger-parse-v1.json` | `2ab007e5b0eda92b280ae53abf6be49b554c1e5673802314e170d71bad465e62` | `contracts._parse_ledger_tables` sees each of the four new rows exactly once at `consumed = no`, the two aborted rows exactly once at `consumed = yes`, and the twin row still once at `consumed = no` |
| `plan-hashes-v1.txt` | see the file | the SHA-256 of this note, of every document in the recovery readiness directory and of the five config fragments |

`core.flight.cli wire-check` remains unavailable for any native-episode cell, for the reason the v2
package records: `FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is
not the real shared speech renderer. The request-envelope comparison stands in its place.

## 10. What is NOT claimed

- Nothing about task quality. The aborted attempt's 84 complete rows were never scored and never
  read, and no partial read is permitted.
- The four-row smoke re-proves **form** on the fixed commit and nothing else; it cannot reach the
  REVISE path.
- The fix is proved for a re-entered phase's supply decision. It says nothing about whether exemplar
  supply helps — that is what the recovery flight measures, under the unchanged preregistered rule.
- No claim that the recovery run's realized requests equal the aborted run's: greedy decoding at
  `temperature 0` is not bitwise reproducible across batch compositions, so trajectories may differ
  row by row. What is pinned is the configuration and the request-construction surface.
