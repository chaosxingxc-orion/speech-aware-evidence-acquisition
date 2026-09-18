# Cell B2 v3 four-row smoke: the one root-diagnosed recovery, registered before contact

Status: **REGISTERED BEFORE CONTACT.** Author: the cell B2 v3 smoke recovery registration agent,
worktree `/home/chao/saea-worktrees/fable-b2-recovery`, branch `fable/b2-recovery`, base commit
`0292dcfe` (which carries the E2d fix `f3a77fb0`, merged `5492c2af`).

This note is the **addendum** to
[`2026-09-17-slurp-b2-samples5-anchor-v3-preregistration.md`](2026-09-17-slurp-b2-samples5-anchor-v3-preregistration.md),
whose bytes are pinned by the sealed root decision `slurp-b2-samples5-anchor-v3-admission-v1` and
are therefore **not edited**. Everything that preregistration says about the question, the arms, the
one moved factor, the commit policy and its thresholds, the metrics, the resampling, the decision
rule, the prompt fit and what is not claimed stands unchanged. Its section 10 allows *at most one
root-diagnosed recovery re-registration*. This is it.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried; the GPU was never touched;
no run directory was modified; and cell B7a's flight, which held the flight lock throughout, was not
touched.

## 1. What happened

Run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3`, attempt
`attempt-slurp-native-samples5-anchor-smoke-4-generation-v3`, flight commit `858ae4ea`, **generated
every one of its 36 registered contacts on all four rows and then failed AT THE SEAL.** This is not
a generation failure: every contact was made, metered and traced, and every request was fitted.

The bundle verifier refused the first row, `slurp:train:000007:audio--1504197557`, with invariant
**I7**:

```
text does not match its recorded response_text_sha256 -- the text was mutated after the model
response was recorded (I7)
```

The mechanism, in one sentence: under E2b/E2c a grouped Solver visit makes five metered contacts and
delivers the registered commit policy's **aggregate** of the five structured answers, so the
delivered text is a deterministic function of the five raw sample texts and equals none of them in
general — while the pre-E2d runner bound the row's `response_text_sha256` to the **last raw
sample's** text hash. I7's reading, "the delivered text IS one recorded model response's bytes", is
right for a samples-1 row and stays exactly as it is; a grouped row needed its own custody form.

**Why nothing earlier caught it.** Every model-free proof the v3 package carries is a proof about
**requests** — the row-for-row envelope comparison, the fake-model rendered proof, the prompt-fit
statement — and about the *receipt* the runner writes. The seal path is the one surface none of them
exercised: `core.flight.cli wire-check` is unavailable for any native-episode cell (see the v3
README section 8), and the grouped-Solver unit tests pinned the role-result contract and the
`solver_group` custody, not the outputs row the bundle verifier then reads. The four-row smoke was
the first place a grouped row ever reached `verify_bundle`, and it stopped there — which is exactly
what a form smoke is for.

The worker process died at the seal and therefore never reached its own attempt settle path, so the
attempt file was left at `OPENED` with its durable actuals intact.

## 2. What was spent, what is preserved, and how the attempt was reconciled

| item | value |
| --- | --- |
| attempt state before | `OPENED` (the worker died at the seal) |
| attempt state after | `ABORTED`, with `actual` and `reserved` preserved unchanged |
| generation calls | 36 |
| repeated speech seconds | 95.36006250000004 |
| rows generated | 4 of 4, at nine contacts each (1 Perception, 5 Solver samples, 2 Reviewer, 1 Planner) |
| request-fit receipts | 36 under `prepared/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-FIT-V3/` (144 FIT endpoints) |
| trace | `runs/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3/attempt-…-generation-v3/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3.trace.jsonl`, SHA-256 `13f9edf4fabdf1c557522e7c23e2a2d08c840bd9f7a26ae652011be8c739bc38`: 36 `MODEL_REQUEST`, 36 `MODEL_RESPONSE`, 36 `MODEL_WIRE_RESPONSE`, 36 `COST`, 56 `USE`, 4 `ORG`, 4 `SUPPLY` |
| outputs | `…outputs.jsonl`, SHA-256 `008e17d42edc5036da494f008f1f6260072268b8fda9bd4aa0037c4ee6185502`, four rows each carrying `native_episode_receipt` and `solver_group` |
| flight receipts | `…/flight-receipts.json`, receipts hash `4564db08a27ad6a9fbb5ae3bf166a3be723ee807b922cc250b155b65f8402fd6` |
| tool calls | 4 Reviewer task-contract calls, against the 24 ceiling |
| score | none. No official scoring job ran and **no partial quality read was taken or is permitted** |

Everything above is **read-only forever**. Nothing under the run directory was modified by this
registration.

**The run manifest reads `status: COMPLETED` and that is not evidence that the run sealed.** That
manifest is written by the seal path *before* the bundle verifier runs; it carries `scores: null` and
`failure_reason: null` because the process died before either could be filled. It is preserved
exactly as written.

**The attempt was reconciled by root through the repository's own API, never by hand.**
`core.attempts.store.AttemptStore.abort_if_opened(run_id, attempt_id, reason=…)` moved it
`OPENED → ABORTED` and wrote a durable `failure_reason` naming I7, the E2d fix and the reconciliation
receipt; `actual` (36 calls, 95.36006250000004 s) and `reserved` (76 calls, 202 s) are byte-identical
to what the flight persisted. The receipt is
`coordination/slurp-b2-samples5-anchor-v3/attempt-reconciliation-smoke-v1.json`
(schema `saea-attempt-reconciliation-v1`), which records the attempt and its actuals, the seal
failure line verbatim, the E2d fix, the E2d read-only proof on these sealed bytes, the SHA-256 of
every preserved run-directory file, and `reconciled_by: root (Fable 5.1 coordinator)`.

The two exposure rows `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3` and
`…-SMOKE-4-FIT-V3` are now `consumed = yes` and carry the abort, the root cause and the recovery run
ids in their notes. **Neither run id nor either attempt id is ever reused.** The 36 calls and
95.36006250000004 repeated speech seconds are charged to those closed rows and are **not** re-charged
to the recovery run, whose own plan covers only its own worst case at the unchanged ceiling.

## 3. The fix, and its proofs

**E2d**, commit `f3a77fb0`, merged `5492c2af`, invariant **I7g**. Two changes, both confined to
grouped rows; a samples-1 row is byte-identical to before.

*The runner.* `reproduction.ojw.native_group_solver` records `solver_group.commit_params` — the
exact parameters the policy was applied with, beside its already-recorded id, because a sealed bundle
carries `config_hash` and fragment names and never the composed configuration, so without them no
post-seal reader can re-run the commit. `core.flight.runtime._canonical_output_rows` binds a grouped
row's `response_text_sha256` to the **delivered** bytes, the same move the projection-v3 delivery
branch beside it already makes. Nothing is lost: the raw transport envelope hash stays in
`response_sha256`, and every raw sample's own request and response hashes stay in
`solver_group.samples[i].contacts[j]`. `rails.native_episode_receipt` validates the new field.

*The verifier.* `core.bundle.outputs` adds **I7g** for a row carrying a `solver_group` receipt only:
every sample's recorded `response_text_sha256` must be the trace's own `MODEL_RESPONSE` bytes for
that contact (request hash and envelope hash bound the same way) and the row's own request/response
identity must be that group's **last** sample contact; `solver_group.commit_policy_id` must resolve
in `core.base.COMMIT_POLICIES` and reproduce itself over the same recorded votes; and re-running it
over the row's own recorded samples through `analysis.native_commit_replay` — the same code the
offline sensitivity table runs — must reproduce the delivered bytes byte for byte. A grouped row
whose text differs is refused naming I7g and the first differing character offset, never the text
itself. A receipt recording no `commit_params` is refused. **I7 itself is unchanged** and still binds
every row's `text` to its own `response_text_sha256`, grouped rows included; the outputs-to-trace
binding drops only the comparisons a grouped row cannot satisfy and replaces them with the stronger
per-sample binding.

**Proof 1 — the committed tests**, model-free, fake data, zero model contact:

| node | what it pins |
| --- | --- |
| `tests/unit/test_bundle_grouped_commit.py` (10 cases) | the legitimate flow; a mutated delivered text (I7g); a stale row hash (I7); a sample hash that does not match the trace; a missing sample trace record; an unregistered policy; a missing `commit_params`; a forged transport identity; the pre-E2d row shape; and the untouched single-sample path |
| `tests/unit/test_flight_native_episode_dispatch.py::test_grouped_solver_seals_a_row_the_bundle_verifier_accepts` | **the seal path itself**: one real grouped dispatch through `FlightRuntime` whose sealed row hashes the delivered bytes, records `commit_params`, keeps its group's last contact as its transport identity, verifies against that run's own trace, and is refused with I7g once forged |
| `tests/unit/test_native_episode_runner_grouped_solver.py` | unchanged, and still passing: a samples-1 row is byte-identical to before |

**Proof 2 — the failed smoke's own real bytes, read only.** The E2d agent ran `verify_bundle` over
them without opening anything for writing. It **still refuses** them, and for the stated reason:
those rows were written by the pre-E2d runner, so their `response_text_sha256` is the last raw
sample's hash and their receipts carry no `commit_params`. But the custody underneath is sound — the
per-sample trace binding passes on **4 of 4** rows, and the commit recomputation at `min_support` 3 /
char-F1 0.8 (parameters taken out of band from the cell's own baseline fragment, which is exactly the
gap `commit_params` closes) reproduces **all four delivered texts byte for byte**. That is why cell
B2 v3 re-flies its four-row smoke under the fixed runner and **no sealed byte is edited**.

## 4. Why nothing else changes

The failure is a **seal-path custody** defect. It is not a roster, prompt, knowledge, retrieval,
sampling, commit-policy, budget, geometry or scoring defect, and it gives no information whatsoever
about the question cell B2 asks. So:

- **no roster or split change.** The same four already-exposed TRAIN A engineering rows, the same
  split `SLURP-EVO-FOLD-A-V2`, the same split identity
  `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`, the same ordered ids. The four
  rows the failed attempt generated are neither filtered out nor reused: the recovery flies all four
  from row one.
- **no change to the one moved factor.** `native_episode.roles.solver` still declares `samples` 5,
  `decoding_overrides` {temperature 0.7, seed_offset 0} and `commit` {policy
  `saea-commit-plurality-support-v1`, `min_support` 3, `similarity_threshold` 0.8}; the five seeds
  are still `1249110493 … 1249110497`.
- **no prompt, role-graph or instruction change.** Policy
  `phase-native-candidates-review-revise-samples5-v1` with `max_contacts` **19**, reviewer 3 /
  planner 1 / solver 1 / perception 1, `max_revisions` 1, exhaustion policy
  `deliver-latest-solver`, the same six composed instruction texts, the same `phase_tools` Reviewer
  `saea-tool-task-contract-v1` authority.
- **no knowledge or supply change.** Both stores with the same pinned release and snapshot hashes,
  the same four-candidate supply contract, the same promoted speech packets and promotion receipt.
- **no cap change.** 76 generation contacts, 304 FIT endpoints, 202 repeated speech seconds, 1.0
  fit-inclusive GPU hours, 24 Reviewer task-contract calls, zero scoring jobs. These are the v3
  smoke's own registered ceilings, unchanged, and they remain bounds rather than targets.
- **no geometry or session change.** The same resident session
  `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, 24,576-token slot, four slots.
- **no decision-rule change.** The arm's decision rule, its own-null margins (SLU micro 1.1218,
  intent 1.0051) and the read-once rule are exactly as preregistered.

What *does* change is bookkeeping only: new run and attempt ids, this package's own
`native_contact_fit` identity, its own two speech-feature identity ids, and its own prepared-supply
pin.

**The one deviation worth naming.** The v3 smoke baseline deliberately carried the **arm's**
speech-feature key and matcher identity strings so that its four rows would render exactly the arm's
own requests. The recovery baseline takes its **own** pair instead, so the recovery flight's trace
carries its own provenance rather than the failed flight's. This cannot move a request byte: each
payload's own `key_representation_id` and `matcher_policy_id` are derived from the **phase program
id** (`phase-native-candidates-review-revise-samples5-v1`), not from the baseline, and the receipt of
section 6 proves that on all 36 sealed payloads.

## 5. The recovery cell

| item | value |
| --- | --- |
| cell | experiment and cell `slurp-native-samples5-anchor-smoke-4-recovery-v3` |
| generation | run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-RECOVERY-V3`, attempt `attempt-slurp-native-samples5-anchor-smoke-4-generation-recovery-v3`, 76-contact cap |
| FIT | run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-FIT-RECOVERY-V3`, attempt `attempt-slurp-native-samples5-anchor-smoke-4-fit-recovery-v3`, 304 endpoints (4 rows x 19 contacts x (1 packet + 3 endpoints)) |
| baseline | `configs/baseline/slurp-native-anchor-samples5-smoke-4-recovery-v3.json` |
| experiment | `configs/experiment/slurp-native-samples5-anchor-smoke-4-recovery-v3.json` |
| campaign plan | none. The smoke flies through the standalone `core.flight.cli worker`, exactly as the v3 smoke did |
| composed / protocol | `187cd0ecb6671bc74212e33ea3981b72a581e16295ac5e52b46fb396ae39b047` / `0e3a0d3eb94c3115d295f248bf8af6469e3a2b3d16693a072b3d1428dd643bc4` |
| prepared phase supply | `prepared/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-RECOVERY-V3/phase-supply-v1.json`, SHA-256 `a0721db12339d7931738e7ae414cfac8087b68f9a978353582ebf58e85f2448b`, `output` SHA-256 `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` — the sealed smoke artifact's own, on 4 of 4 rows |
| protocol document | the v3 package's own `docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3/protocol-registered-v1.json`, SHA-256 `93829f87b4c56e6ff7e976ac017547ee1a0bb847eac825004752716060e025c0`, **unchanged**: the recovery moves the seal path in the code, never the protocol |
| plans | `docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1/` — two prospective and two `-registered` plans |
| readiness | `held`, with the preparation requirement pinned; the coordinator adds the decision requirement and flips with `scripts/flights/repin_cell.py` |

The baseline fragment is the v3 smoke baseline **unchanged** except `what_this_is`, the
`native_contact_fit` run and attempt identity (the 304-endpoint cap is unchanged), the two
speech-feature identity ids, and the prepared-supply pin. The experiment fragment is the v3 smoke
experiment unchanged except the cell, run, attempt, experiment and fragment-kind ids, the preparation
pin, the readiness state and reason, and the failure-policy and purpose prose.

**The prepared Perception supply is byte-identical to the sealed smoke artifact's.**
`prepare-supply` was re-run model-free on this commit at one worker and its Perception `output` block
reproduces `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` on **4 of 4** rows,
`output_sha256` included; only the file digest moves, because the artifact carries its own cell
identity. The same `compose`/`protocol_hash` command run on the **anchor's** own fragments on this
branch returns the anchor's registered protocol hash
`2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c`, so the method is verified; and
recomposing the **v3 smoke's** own fragments returns its registered
`d631960a…` / `63034f02…` exactly, so nothing in the tree moved them either.

**The arm and the twin are untouched and stay `held`.**
`SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V3` and
`SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-V3` keep their own unflown v3
registrations at `consumed = no`. Neither has contacted the model, so nothing about them needs
re-registering — but **both must be re-pinned with `scripts/flights/repin_cell.py` on the fixed
commit before launch**, because the runner they will fly on now writes the E2d grouped-row form
(`solver_group.commit_params`, and a `response_text_sha256` bound to the delivered bytes). The re-pin
re-verifies the prepared artifact, re-derives the composed and protocol hashes and re-runs `check`.
The arm launches only after this recovery smoke seals cleanly; the twin still launches only after the
arm shows a positive CI95 against the base (owner decision 8 of 2026-09-17).

## 6. The request envelope: what moves, and what cannot

Receipt `coordination/slurp-b2-samples5-anchor-v3/recovery-request-envelope-comparison-v1.json`.

The failed attempt's trace holds **36 sealed `MODEL_REQUEST` payloads** — the exact bytes that flight
sent, four rows of nine contacts each. They are the reference the recovery cell is compared against.

1. **Config diff.** Of the 66 composed keys, **56 are byte-identical** and **10 differ**, all
   bookkeeping: `what_this_is`, `native_contact_fit`, `speech_feature_key_representation_id`,
   `speech_feature_matcher_policy_id` and `prepared_phase_supply` from the baseline, and `cells`,
   `experiment_id`, `fragment_kind`, `failure_policy` and `purpose` from the experiment. Every
   model-facing key — `policy`, `native_episode`, `phase_material`, `phase_tools`,
   `knowledge_stores`, `task_instruction_template`, `task_instruction_fill`, `serving_slot_tokens`,
   `serving_slots`, the speech-packet promotion receipt and its hash — is byte-identical.
2. **None of those strings is in any request.** All 36 payloads were scanned on **every field, every
   object key and every string value at every depth** for sixteen needles: both registrations' two
   run ids, two attempt ids and two speech-feature ids (twelve identity strings), plus both
   prepared-supply relpaths and both prepared-supply digests. **Every one returns 0 hits.**
3. **The payload's own `key_representation_id` and `matcher_policy_id` are program-derived.** On all
   36 contacts they read `phase-native-candidates-review-revise-samples5-v1:<phase>` and
   `phase-native-candidates-review-revise-samples5-v1`, so the one pair of baseline keys this
   registration deliberately makes unique does not reach a request byte at all.
4. **Per-contact digests are pinned.** For each of the 36 payloads the receipt records a SHA-256 over
   the whole payload minus `request_id` and the `evidence_provenance` relpaths derived from it
   (`rails-message/flight-NNNN/i`, a per-flight sequence number), beside the sealed
   `payload_sha256`, the `sample_id`, the seed, the temperature and the resolved `id_slot`. All 36
   digests are distinct, as they must be.
5. **E2d cannot move a request byte.** Every site it changed runs *after* the response has been
   received (`core/bundle/outputs.py`, the verifier; `core/flight/runtime.py`'s
   `_canonical_output_rows`, at seal time) or writes a receipt field the request never carries
   (`reproduction/ojw/native_group_solver.py`'s `commit_params`,
   `rails/native_episode_receipt.py`'s validation of it). Request composition, the phase prompt
   envelope renderer, the episode-limits epilogue, decoding-parameter composition, the phase supply
   and the controllers are all untouched by E2d.

**The honest limit:** the recovery smoke has not flown, so its own realized post-Perception requests
cannot be re-derived model-free — they depend on the frozen core's answers, and five sampled Solver
draws at temperature 0.7 are not bitwise reproducible across batch compositions, so trajectories may
legitimately differ row by row. What is **proved** is that no configuration byte that reaches a
request moved and that no identity this registration renamed is visible to the model; what is
**pinned** is the per-contact table the recovery flight is checked against. The four Perception
requests are the model-free part and must match exactly.

## 7. Launch

Exactly the v3 runbook
([`2026-09-17-slurp-b2-samples5-anchor-v3/README.md`](2026-09-17-slurp-b2-samples5-anchor-v3/README.md)
sections 3–4 and 7), with the recovery names, and its **nine acceptance items plus one**: a **clean
seal through the bundle verifier**, and a `solver_group` carrying `commit_params`.

```bash
export REPO=<the clean checkout carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"
cd "$REPO"

$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-anchor-smoke-4-recovery-v3 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1 \
  --preregistration docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1.md \
  --decision coordination/slurp-b2-samples5-anchor-v3/root-admission-v1.json \
  --decision-id slurp-b2-samples5-anchor-v3-admission-v1 \
  --set-ready \
  --python "$PY"
```

Commit that in one commit, then take the attach-only worker lease and run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-anchor-smoke-4-recovery-v3 \
  --cell slurp-native-samples5-anchor-smoke-4-recovery-v3 \
  --owner root-slurp-native-samples5-anchor-smoke-4-recovery-v3 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-samples5-anchor-smoke-4-recovery-v3.worker-lease.json

$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-anchor-smoke-4-recovery-v3 \
  --cell slurp-native-samples5-anchor-smoke-4-recovery-v3 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-samples5-anchor-smoke-4-recovery-v3.worker-lease.json"
```

Then re-pin the arm (`--experiment slurp-native-samples5-anchor-train-fold-a-v3`) and, only on a
positive arm CI95, the twin. Expected: about 36 realized contacts against the 76 ceiling, about 95
repeated speech seconds, no scorer, roughly 10 to 20 minutes of wall clock. Read the serving monitor
for this window: the smoke is still the first visible evidence of whether the five same-prefix
sibling requests reuse the cached prompt prefix, and the arm's 12.0 GPU-hour ceiling should be
re-priced from it before launch.

## 8. Failure rule, restated

This registration **is** the one root-diagnosed recovery the v3 preregistration section 10 allows for
cell B2. **A second failure closes the cell**: no third registration, no replay, no row filtering,
no roster, role-graph, prompt, geometry or cap change, no change to `samples`, `temperature`,
`seed_offset`, `min_support` or `similarity_threshold`, and the fix must be proven on a four-row dry
run before another mechanism is admitted.

## 9. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b2-samples5-anchor-v3/`, outside the repository so no
receipt can dirty the tree the manifest reads at finalize.

| receipt | SHA-256 | what it proves |
| --- | --- | --- |
| `attempt-reconciliation-smoke-v1.json` | `8ee8c140e420fd065231c149417a765a4a310a1aa3f464f00a9f1742844859fc` | the failed attempt, its actuals, the seal failure line verbatim, the E2d fix and its read-only proof on these sealed bytes, the SHA-256 of every preserved run-directory file, and the `OPENED → ABORTED` reconciliation by root |
| `recovery-prepare-supply-smoke-v1.json` | `7d0b4502603ebde57b5736fcd53c165c8f5fc5b1a885d1d1609fda3d9e24fb26` | the raw model-free `prepare-supply` receipt for the recovery smoke |
| `recovery-prepared-supply-and-hashes-v1.json` | `64c6334e09495e7c4aa16853bffcaaec2b817864193393e66ab1969fe585a0b8` | the prepared artifact pinned, its Perception `output` identical to the sealed smoke artifact's on 4 of 4, the composed and protocol hashes, the v3-smoke recomposition check and the anchor method check (the same command on the anchor's fragments returns `2527b527…`) |
| `recovery-composed-keys-v1.json` | `e0a2683202ec53a2bbeb01c9d92f99a485cd01ccc71f1ec39cbc1a2c85669a52` | the composed-config key partition behind the 56/10 claim |
| `recovery-request-envelope-comparison-v1.json` | `73de4b78bcd8d3d57306c2bbfa745e5af4b9cadec72e75b91b2b22a2523b0358` | the config diff, the sixteen-needle identity search over all 36 sealed payloads (0 hits on every field), the program-derived `key_representation_id`/`matcher_policy_id` on every contact, the per-contact model-facing payload digests, and the statement that E2d touches no request byte |
| `recovery-check-smoke-v1.json` | `bb59f041c693a1d35e90b4a0b8e4029df30cbb42beb1aabf11861f4c50685fa1` | runtime `core.flight.cli check` at study commit `18605e50`: preflight, gate, exposure row, clean tree, attempt free, readiness `held`, `generation_authorized false`, prompt budget `ALLOW` on every phase (operational margins 5,390 perception / 5,527 reviewer / 5,588 planner / 5,348 solver tokens), and the runtime-derived protocol hash equal to the registered one |
| `recovery-ledger-parse-v1.json` | `90cea5012f6da39a0b2fb4c6df0d65fae07bc3408bc9ed4d2e00e6e774d75647` | `contracts.ledger._parse_ledger_tables` sees both new rows exactly once at `consumed = no`, both failed smoke rows exactly once at `consumed = yes`, and the arm and twin rows still once each at `consumed = no`; 924 rows and 924 distinct run ids, 0 duplicates |
| `recovery-plan-hashes-v1.txt` | see the file | the SHA-256 of this note, of every document in the recovery readiness directory, and of the two recovery config fragments |

`core.flight.cli wire-check` remains unavailable for any native-episode cell, for the reason the v3
package records: `FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is
not the real shared speech renderer. The request-envelope comparison stands in its place — and it is
precisely the surface that was *not* the problem here, which section 1 states plainly.

## 10. What is NOT claimed

- Nothing about task quality. The failed attempt's four generated rows were never scored and never
  read, and no partial read is permitted.
- The four-row smoke re-proves **form** on the fixed commit and nothing else. A structural smoke
  result is never a quality result.
- No claim that the recovery flight's realized requests or trajectories equal the failed flight's:
  five sampled Solver draws at temperature 0.7 are not bitwise reproducible across batch
  compositions. What is pinned is the configuration, the request-construction surface and the
  per-contact digest table.
- The fix is proved for a grouped Solver row's seal-time custody. It says nothing about whether
  sampling and aggregation help — that is what the arm measures, under the unchanged preregistered
  rule.
- The prompt-cache assumption behind the arm's 12.0 GPU-hour ceiling is still stated, not proven.

## Outcome (2026-09-18, coordinator)

The recovery smoke `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-RECOVERY-V3` flew at 2026-09-18T00:42Z
through the standalone worker attached to the resident session, at study commit `fdad9af0` (the
ready package was re-pinned from `7c97b963`, which lacks the E8c fix, before contact; the re-pin tool
rewrote no hash: composed `187cd0ec...`, protocol `0e3a0d3e...` unchanged). Actuals: 36 calls, 95.36
audio seconds, 4 task-contract tool calls, 36/36 request fits (minimum margin 11,188 tokens). The
manifest reads COMPLETED with the seal stage present, so the E2d custody form is proved on the four
grouped rows; every row shows 9 contacts (Perception 1, Solver 5 samples at temperature 0.7 under the
five pinned seeds, Reviewer 2, Planner 1 ACCEPT) and a `solver_group` block carrying
`commit_params`, `commit_policy_id`, `delivered` and `samples`. **Structural PASS; no quality read.**
The arm re-pins before its launch and, under owner decision 19 of 2026-09-18, flies after cell B5e.
