# Cell B7a on the sealed anchor: the one root-diagnosed recovery, registered before contact

Status: **REGISTERED BEFORE CONTACT.** Author: the B7a recovery registration agent, worktree
`/home/chao/saea-worktrees/fable-b7a-recovery`, branch `fable/b7a-recovery`, base commit `5bbd54a2`
(the merge that carries the E8c fix `2af5955a`).

This note is the **addendum** to
[`2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md`](2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md),
whose bytes are pinned by the sealed root decision `slurp-b7a-ncp-l1-anchor-admission-v1` and are
therefore **not edited**. Everything that document says about the question, the arms, the one moved
factor, the metrics, the resampling, the decision rule, the prompt fit and what is not claimed
stands unchanged. Section 10 of that document allows *at most one root-diagnosed recovery
re-registration* per run. This is it.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried; no run directory was
modified; cell B1's flying twin was not touched.

## 1. What happened

Run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1`, attempt
`attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-v1`, flight commit `00483f61`,
**ABORTED at about 21:00 UTC on 2026-09-17**. The recorded failure is, verbatim from
`attempts/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1/attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-v1.json`:

```
generation failed during run_phases or seal: NativeEpisodeError: Planner output names no
registered action
```

The mechanism, in one sentence: the flight's Planner emitted a token that was not one of the three
registered actions, `reproduction.ojw.native_episode._planner_action` had no designed behaviour for
it, and the exception it raised propagated out of the episode and killed the campaign.

**The two odd outputs, by length and hash only.** Their bytes are never reproduced, here or in any
receipt. Of the attempt's **665** Planner responses, **663** were exactly `ACCEPT` (615) or `REVISE`
(48). The remaining two were:

| # | characters | SHA-256 of the whole response | what it is |
| --- | --- | --- | --- |
| 1 | 6 | `ec947170824a09f8b502f402ac3ef7eb02b6a4096b54a190836b79d5155e0ed2` | a six-character control token outside the configured action set; it is the token the E8c commit message names |
| 2 | 80 | `0db1d699388e290aeb5ddf7c114d3f90120d70de829ee5a85f0748f7112080e8` | an 80-character response opening on a non-alphabetic character |

Each fell on the **final Planner visit of its own row**, and those are exactly the two rows of the
618 contacted that never sealed.

**Why it was undesigned rather than mis-designed.** The sealed dual-store anchor's own **1,085**
Planner contacts produced an illegal token **zero** times, and neither did cell B0, cell B0r or the
B7a four-row smoke. There was no observation to design against. That makes this a harness
robustness defect, not a finding about the Node Context Policy under test.

**Why the smoke did not catch it.** The four-row smoke
(`SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V1`, sealed at study commit `ea84dcd5`) produced six
Planner responses across its four rows -- three rows `ACCEPT` at five contacts and one row `REVISE`
then `ACCEPT` at nine -- and every one named a registered action. It even exercised the REVISE
route. A four-row roster on which the Planner routes only registered actions cannot reach the
illegal-action path, at any revision depth.

## 2. What was spent, and what is preserved

| item | value |
| --- | --- |
| attempt state | `ABORTED`, with `actual` preserved |
| generation calls | 3,278 |
| repeated speech seconds | 8,973.150063 |
| rows contacted | 618 (616 sealed; the two that carried an illegal action did not) |
| contacts by role | perception 616, solver 661, reviewer 1,322, planner 661, plus 18 on the two rows that did not seal |
| request-fit receipts | 3,278 under `prepared/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-FIT-V1/attempt-slurp-native-ncp-l1-anchor-train-fold-a-fit-v1/` |
| trace | `runs/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1/attempt-…-generation-v1/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1.trace.jsonl`, 21,596 records: 3,278 `MODEL_REQUEST`, 3,278 `MODEL_RESPONSE`, 3,278 `MODEL_WIRE_RESPONSE`, 3,278 `COST`, 5,224 `USE`, 3,260 `ORG` |
| flight lock | preserved and then reconciled by root, receipt `coordination/slurp-b7a-ncp-l1-anchor-v1/flight-lock-reconciliation-20260917T203304Z.json` (preserved copy `flight-lock-preserved-20260917T203304Z.json`) |
| score | none. No official scoring job ran and **no partial quality read was taken or is permitted** |

Everything above is **read-only**. Nothing under the run directory was modified by this
registration. The two exposure rows
`SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1` and `…-TRAIN-FOLD-A-FIT-V1` are now
`consumed = yes` and carry the abort, the root cause and the recovery run ids in their notes. The
two smoke rows were already closed by the smoke itself. **No run id and no attempt id is ever
reused.**

## 3. The fix, and its proofs

`reproduction.ojw.native_episode._planner_action`, commit `2af5955a`, merged `5bbd54a2` (engineering
item E8c). Instead of raising, it returns the reserved routing value `PLANNER_ACTION_ILLEGAL` --
for a token outside the configured action set, and under `json-action-v1` for every output the
strict single-key parse refuses -- and the episode graph maps that value to the **same explicit-accept
component an `ACCEPT` takes**.

The row is **RETAINED**, which is the program's standing rule for a malformed row: it delivers its
committed draft unchanged, contacts no further role, spends no revision, and counts toward every
budget it consumed. Its `planner_routes` entry gains `"legal": false`, `"disposition":
"planner_action_illegal"`, `"action_sha256"` over the whole token and `"action_chars"`, with
`"action"` cut to the first 32 characters; the receipt gains a `planner_action_illegal` mark
carrying the count and that sha256. An illegal route also clears any earlier visit's
`planner_control`, so the raw-source custody check can never bind the wrong route. **An illegal
Planner action is a row disposition, never a flight failure.**

**Proof 1 -- the committed tests.** Both pass on this branch:

| node id | what it pins |
| --- | --- |
| `tests/unit/test_ojw_native_episode.py::test_malformed_planner_action_seals_the_row_instead_of_failing_the_flight` | the disposition itself, the 32-character truncation on the 80-character shape, a legal route's byte identity beside an illegal one, the `json-action-v1` cases and the reserved value |
| `tests/unit/test_flight_native_episode_dispatch.py::test_an_illegal_planner_token_seals_its_row_and_the_campaign_continues` | a real two-row dispatch: the campaign runs both rows with its contact accounting intact, the bundle verifier accepts the sealed row, and the registered SLURP official scorer scores it exactly like the accepted row beside it |

E8c also pins that the anchor's own byte identity does not move
(`test_node_context_policy_runner.py`'s `ANCHOR_REQUEST_SHA256`, `ANCHOR_TRANSITION_SHA256` and
`ANCHOR_FRAGMENT_SHA256`, and `test_native_episode_runner_grouped_solver.py`), and that a route the
episode really took as `ACCEPT` or `REVISE` records exactly its three pre-E8c keys.

**Proof 2 -- the illegal-action path on this recovery's own four-row smoke roster.** Receipt
`coordination/slurp-b7a-ncp-l1-anchor-recovery-v1/illegal-action-proof-v1.json`. Four dispatches
through the **real** OpenJiuwen role graph, the real `FlightRuntime._dispatch_phase_program` and the
real request gate over the shared fake transport -- zero model, tokenizer, encoder, scorer and
server contacts. The row ids are the **real** four rows of
`prepared/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1/phase-supply-v1.json`; the shared
`_World` fixture publishes two media samples per dispatch, so the four scenarios cover all four rows
between them:

| scenario | rows | Planner outputs | result |
| --- | --- | --- | --- |
| A | smoke rows 1-2 | both `ACCEPT` | 0 illegal rows; the routes carry exactly their three pre-E8c keys |
| B | smoke rows 1-2 | row 2 the real six-character token | 1 retained row, disposition `planner_action_illegal`, the dispatch seals both rows |
| C | smoke rows 3-4 | row 3 an 80-character shape | 1 retained row, same disposition, both rows seal |
| D | smoke rows 3-4 | one odd shape per row | 2 retained rows, both sealed, the dispatch never raises |

In every scenario the dispatch returns every row, the contact count equals the transport's own
request count (8 per dispatch), each illegal row's `final_response_text` is its committed draft
unchanged, and no illegal row spends a revision. On the pre-E8c tree scenarios B, C and D are
exactly what died. Only the row **ids** are real in this proof: drafts are synthetic, no utterance
text and no gold enters it, the six-character token is the real control token, and the 80-character
shape is a **synthetic** string of the same length as the sealed one, whose own bytes are never
reproduced.

## 4. Why nothing else changes

The failure is a **harness** defect on an undesigned Planner output. It is not a roster, prompt,
knowledge, retrieval, context-policy, budget, geometry or scoring defect, and it gives no
information about the question cell B7a asks. So:

- **no roster or split change.** Same 1,080-row TRAIN Fold A roster, same `SLURP-EVO-FOLD-A-V2`,
  same split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, same
  ordered ids. The 618 rows the aborted attempt contacted are **not** filtered out and **not**
  reused -- the recovery flies the whole roster from row one, as one complete manifest.
- **no context-policy change.** `native_episode.context_policy` is the same `structured` block on
  the same eight model-output boundaries, `on_parse_failure` `raw` everywhere except
  `solver:plan-action` (`refuse`), the same four tool-observation boundaries declared `raw`, the
  same six committed templates at the same hashes, and still no producer response format. The
  `solver:plan-action` FALLBACK-REFUSE boundary is untouched: it renders into a **re-entered**
  Solver, which happens only after a `REVISE`, and an illegal output terminates its row at the
  Planner.
- **no prompt or role-graph change.** Reviewer 3 / planner 1 / solver 1 / perception 1,
  `max_revisions` 1, policy `phase-native-candidates-review-revise-v1`, program ceiling 11 contacts,
  the same Reviewer-only task-contract tool authority and Solver-only answer authority.
- **no knowledge or retrieval change.** The same two stores at v1 with the same release and snapshot
  hashes, the same supply geometry, and the same sealed Fold A speech query vectors.
- **no cap change.** 11,880 generation contacts, 47,520 FIT endpoints, 33,930 repeated speech
  seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete
  score (smoke 44 / 176 / 117 s / 1.0 GPU-h / 24 tool calls, zero scoring jobs). These are the
  aborted arm's own registered ceilings, unchanged, and they remain bounds rather than targets.
- **no geometry or session change.** The same resident session
  `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, 24,576-token slot, four slots.
- **no decision-rule change.** Primary pooled official SLU micro F1, intent non-inferior within
  1.0051 pp (the TRAIN A own-null half-width from cell B0r), the scenario null band, projection v3
  agreeing in sign, and the rule that a NEUTRAL L1 still enters the SLURP default plan.

What *does* change is bookkeeping only: new run and attempt ids, this package's own
`native_contact_fit` identity, its own two speech-feature identity ids (provenance only), and its
own prepared-supply pin.

**Budget accounting.** The 3,278 calls and 8,973.150063 repeated speech seconds the aborted attempt
durably spent are charged to the **closed** run id, not to the recovery run. The recovery run's own
plan covers its own worst case at the unchanged program ceiling.

## 5. The recovery cells

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-ncp-l1-anchor-train-fold-a-recovery-v1`, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1`, attempt `attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-recovery-v1` |
| arm FIT | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-FIT-RECOVERY-V1` / `attempt-slurp-native-ncp-l1-anchor-train-fold-a-fit-recovery-v1`, 47,520 endpoints |
| smoke cell | experiment and cell `slurp-native-ncp-l1-anchor-smoke-4-recovery-v1`, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1`, attempt `attempt-slurp-native-ncp-l1-anchor-smoke-4-generation-recovery-v1` |
| smoke FIT | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-FIT-RECOVERY-V1` / `attempt-slurp-native-ncp-l1-anchor-smoke-4-fit-recovery-v1`, 176 endpoints |
| baselines | `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-recovery-v1.json`, `configs/baseline/slurp-native-anchor-ncp-l1-smoke-4-recovery-v1.json` |
| experiments | `configs/experiment/slurp-native-ncp-l1-anchor-train-fold-a-recovery-v1.json`, `configs/experiment/slurp-native-ncp-l1-anchor-smoke-4-recovery-v1.json` |
| campaign plan | `configs/campaign/slurp-native-ncp-l1-anchor-train-fold-a-recovery-v1.json` |
| composed / protocol (arm) | `55c658cf3191edf4cd45df0396abe2fd4eaf6cac05ca18c27a9b982bda03406e` / `938990b7dba691fc656eaa30e1ef67848a7fcc812ec9f2eba0ec584ce1400ad8` |
| composed / protocol (smoke) | `097d1b9d445b4a959c2654cf6fb45fd8d2f6e81b29873cd5d7f54a95a01e10d3` / `4585fd4dc66618a9448667fd202d67a12d9426098140f4e153a8ea22da094bb0` |
| prepared supply (arm) | `prepared/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1/phase-supply-v2.json`, SHA-256 `115e76498232450a83c5c70bf8ee33eac232138e44596ca9691fe37725fb4926` |
| prepared supply (smoke) | `prepared/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1/phase-supply-v1.json`, SHA-256 `a3a07acdc44eb082717684376209624f72e960189ba77e0676c81b49422ca270` |
| plans | `docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-recovery-v1/` -- four prospective and four `-registered` plans, the recovery protocol document and the recovery analysis recipe |
| readiness | both cells `held` with the `preparation` requirement pinned; the coordinator adds the `decision` requirement and flips with `scripts/flights/repin_cell.py` |

The two baseline fragments are the v1 baselines **unchanged** except `what_this_is`, the
`native_contact_fit` run and attempt identity (caps unchanged: 47,520 and 176), the two
speech-feature identity ids, and the prepared-supply pin -- seven leaf keys, and nothing else. The
two experiment fragments are the **pre-flip** (`2c39a957`) v1 experiments unchanged except the cell,
run, attempt, experiment and fragment-kind ids, the baseline fragment name, the preparation pin, the
readiness reason and the failure/purpose prose.

**The prepared Perception supply is byte-identical to the sealed anchor's.** `prepare-supply` was
re-run model-free at 4 workers on this commit for both cells and each artifact's Perception `output`
block reproduces the sealed anchor preparation's exactly: `output_sha256`
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` on **1,080 of 1,080** rows for
the arm, and `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` on **4 of 4** rows
for the smoke, each row's selection equal to the reference's own row. Both blocks are also
byte-identical to the **aborted v1 registration's own artifacts**; the only inputs that move are
`inputs.config_sha256` (this recovery's own identity ids) and one entry of
`inputs.sources.implementation`, `runtime`, because E8c edits `rails/runner.py`. Every retrieval
input -- `supply_spec`, `packets`, `snapshot`, `source_audio_bindings`, `frozen_source_receipts` --
and the split identity are unchanged, and so are the `kb_policy`, `knowledge_provider` and
`knowledge_stores` module hashes. The same `compose`/`protocol_hash` command run on the sealed
anchor's own fragments returns the anchor's registered protocol hash
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`, so the method is verified.
Receipt: `coordination/slurp-b7a-ncp-l1-anchor-recovery-v1/prepared-supply-and-hashes-v1.json`.

**The v1 package's own contact-free evidence still stands and is not re-derived.** The
request-channel proof over all 5,417 sealed anchor requests, the prompt-fit bound and the
containment proof (`coordination/slurp-b7a-ncp-l1-anchor-v1/`) describe the *policy*, which this
recovery does not touch; E8c changes no rendered request byte.

**The sibling cells are untouched.** B7b (L2), B7r and B7c keep their own unflown registrations,
`consumed = no`, readiness `held`. None of them contacted the model. B7b still flies only if B7a is
read ADMITTED or NEUTRAL, and B7r and B7c still open only after B7a seals and is read not HARMFUL.
The L1 derangement twin is still unregistered and still flies only on a positive CI95.

## 6. The request envelope: what moves, and what cannot

Receipt `coordination/slurp-b7a-ncp-l1-anchor-recovery-v1/request-envelope-comparison-v1.json`.

The aborted attempt's trace holds **3,278 sealed `MODEL_REQUEST` payloads** over 618 rows
(perception 616, solver 661, reviewer 1,322, planner 661, plus 18 on the two rows that did not
seal). They are the exact bytes the aborted arm sent, and they are the reference the recovery arm is
compared against:

1. **Config diff.** Of the 66 composed keys, **56 are byte-identical** and ten differ. All ten are
   bookkeeping: the five baseline keys named in section 5 (`what_this_is`, `native_contact_fit`,
   both `speech_feature_*_id`, `prepared_phase_supply`) and the experiment fragment's own `cells`,
   `experiment_id`, `fragment_kind`, `failure_policy` and `purpose`. Every model-facing key --
   `policy`, `native_episode` (the context policy included), `phase_material`, `phase_tools`,
   `knowledge_stores`, `task_instruction_template`, `task_instruction_fill`,
   `task_instruction_template_active`, `serving_slot_tokens`, `serving_slots`, `arm`,
   `evidence_source`, `evidence_mismatch`, `scorers` and both speech-packet promotion keys -- is
   **byte-identical**. (The aborted fragment is compared as it stands at HEAD, in its post-flip
   form, so its readiness bookkeeping is expected in the differing list.)
2. **None of those strings is in any request.** Every one of the 3,278 sealed payloads is
   serialised to canonical JSON -- every field, `task_instruction`, `history`, `supplied_evidence`,
   `evidence_provenance`, `speech_feature_parts` and `decoding_params` included -- and searched for
   the aborted run id, the aborted FIT run id, both aborted attempt ids, both aborted
   speech-feature ids, and the same six strings of this recovery. **All twelve return 0 hits across
   all 3,278 payloads.**
3. **The payload's own `key_representation_id` and `matcher_policy_id` are program-derived, not
   config-derived.** On **3,278 of 3,278** payloads they read
   `phase-native-candidates-review-revise-v1:<phase>` and
   `phase-native-candidates-review-revise-v1` -- the **policy** id, not the baseline's. So the
   speech-feature identity ids this registration deliberately makes unique do not reach a request
   byte at all.
4. **Per-row per-phase digests are pinned.** For each of the 3,278 payloads the companion receipt
   `request-envelope-per-row-digests-v1.json` records a SHA-256 over the whole payload minus
   `request_id` and with the `evidence_provenance` relpaths that are derived from it
   (`rails-message/flight-NNNN/i`, a per-flight sequence number) normalised. The recovery flight
   must reproduce these digests on every row and phase it covers.
5. **The whole-roster render agrees.** `core.flight.cli check`'s pre-flight prompt budget renders
   the widest request each phase produces across all 1,080 rows and hashes it (`payload_sha256`).
   On the clean tree at commit `45abba9e` the recovery arm's four per-phase entries are **byte-
   identical** to the aborted registration's own sealed pre-flight receipt -- not only the digest
   but the whole entry, decision, breakdown and margin: `perception 2576cb36…`,
   `reviewer 164d4327…`, `planner 5150f014…`, `solver 3308edb1…`, with
   required-window token counts 19184 / 19047 / 18987 / 19227 and ALLOW on every phase. The
   four-row smoke agrees on every phase too. Receipt `preflight-render-comparison-v1.json`.

**The honest limit:** the recovery arm has not flown, so its own realized post-Perception requests
cannot be re-derived model-free -- they depend on the frozen core's answers, and greedy decoding at
`temperature 0` is not bitwise reproducible across batch compositions. Trajectories may therefore
differ row by row, and the recovery is expected to meet illegal Planner actions of its own. What is
proved here is that no configuration byte that reaches a request moved; what is pinned is the
per-row per-phase table the recovery flight is checked against.

## 7. Launch

Exactly the v1 runbook (`2026-09-17-slurp-b7a-ncp-l1-anchor-v1/README.md` sections 2-7), with the
recovery names. Flip the **smoke first**, commit, fly it, then re-pin and flip the arm.

```bash
export REPO=<the clean detached worktree carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"
cd "$REPO"

$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-anchor-smoke-4-recovery-v1 \
    --cell slurp-native-ncp-l1-anchor-smoke-4-recovery-v1 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-recovery-v1 \
  --preregistration docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-recovery-v1.md \
  --package-name slurp-b7a-ncp-l1-anchor-recovery-v1 \
  --decision coordination/<the root recovery-admission receipt relpath> \
  --decision-id <the recovery admission decision id> \
  --set-ready
```

Then the same command with `--experiment slurp-native-ncp-l1-anchor-train-fold-a-recovery-v1 --cell
slurp-native-ncp-l1-anchor-train-fold-a-recovery-v1` once the smoke seals. The smoke runs through
the standalone worker of the v1 runbook's section 4; the arm then runs through
`configs/campaign/slurp-native-ncp-l1-anchor-train-fold-a-recovery-v1.json`, exactly as section 5
describes.

The re-pin tool rewrites **every file under `--readiness-dir`**, this note and the four recovery
ledger notes; it does **not** touch the v1 package, whose plan files and preregistration keep their
sealed hashes, and it refuses if any target exposure row is already `consumed = yes`. Never pass
`--allow-output-change`: part of the one-factor claim is that the Perception selection does not
move.

Post-flight is the v1 runbook's section 6 unchanged, **plus one mandatory diagnostic**: see
section 8.

## 8. Failure rule and verdict obligation

This registration **is** the one root-diagnosed recovery the preregistration allows for cell B7a. A
second failure closes this flight: no third registration, no replay, no row filtering, and the fix
must be proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke
stops the recovery on the same terms.

**The verdict must report the flight's own `planner_action_illegal` count as a diagnostic**, beside
the node-context receipt table: the number of rows that carried the disposition, their sample ids,
and their action character counts and sha256 values. Those rows are **retained** in every metric --
they delivered a committed draft and are scored like any other row -- and are never dropped from the
paired read. A high count is a finding about the Planner's output contract on this base, and it is
reported, not repaired inside this cell; repairing it would be a new registration.

## 9. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b7a-ncp-l1-anchor-recovery-v1/`, outside the
repository so no receipt can dirty the tree the manifest reads at finalize.

| receipt | SHA-256 | what it proves |
| --- | --- | --- |
| `prepared-supply-and-hashes-v1.json` | `bcdf794adc12bf690c7fe52013c97a93a86b4670339ad92e5cfa0d462938dbe4` | the two prepared artifacts pinned, their Perception `output` identical to the sealed anchor's on 1,080 / 1,080 and 4 / 4, the composed and protocol hashes, the implementation-pin comparison against the aborted arm's own artifact, and the anchor method check (the same command on the anchor's fragments returns `d1c61c09…`) |
| `prepare-supply-train-fold-a-recovery-v1-v1.json` | `78b1ade2d2005f3ff8762bf10bde0383a8ce8d0221084a7fa79f67af729ba0ed` | the raw model-free `prepare-supply` receipt for the arm |
| `prepare-supply-smoke-4-recovery-v1-v1.json` | `5f8d7cea1e96d83d06c9d5444c73c94c1ce9af4abf36c2df05f5dca5372118f3` | the raw model-free `prepare-supply` receipt for the smoke |
| `illegal-action-proof-v1.json` | `cdd9f64149f890bd49ca3dcbe507f274526e8ec37a2ab7904486437b76fd3459` | four dispatches on the real smoke row ids through the real role graph, all passing; the two committed E8c test node ids |
| `request-envelope-comparison-v1.json` | `1813e2b961858f8b63f70c2147a15d089796b1f2c2cd06e966aa2ae873b24841` | the composed-config diff (56 keys identical, 10 bookkeeping keys differ, every model-facing key identical), the 3,278-payload identity search (0 hits on all twelve strings), and the program-derived identity check (3,278 of 3,278) |
| `request-envelope-per-row-digests-v1.json` | `a59993550cd49ce43c702368503ad55a3b4ee555aee9f0ad35d82b8d87ae6479` | the per-row per-phase model-facing payload digests the recovery flight is checked against |
| `check-train-fold-a-recovery-v1-v1.json` | `18423f5207d21def61eaf69ff34530a700b30822440ba4047b0dd5e4a48bdf09` | runtime `check` on the clean tree: gate, exposure row, attempt free, readiness `held`, `generation_authorized false`, prompt budget ALLOW on every phase, runtime hashes equal to the registered ones |
| `check-smoke-4-recovery-v1-v1.json` | `6f0c6d4378b43da56810ba176dc2917fc93814ecc27dc439fe616c27ec13ffab` | the same for the four-row smoke |
| `ledger-parse-v1.json` | `1cb0732081304ebe7aee42761b8fa80fe8a6c9667fa81178f3e5950591bbb858` | `contracts._parse_ledger_tables` sees each of the four new rows exactly once at `consumed = no`, and the two aborted arm rows exactly once at `consumed = yes` |
| `preflight-render-comparison-v1.json` | `f077aa8ec605015ed19fe7c72bd307bf52762bb4f95a18a086e48ff20efc1b48` | the whole-roster pre-flight render of both recovery cells, entry for entry identical to the aborted registration's own sealed receipts on all four phases |
| `INDEX-v1.json` | see the file | the index of this directory, naming every receipt above with its size and SHA-256 |
| `plan-hashes-v1.txt` | see the file | the SHA-256 of this note, of every document in the recovery readiness directory and of the five config fragments |

`core.flight.cli wire-check` remains unavailable for any native-episode cell, for the reason the v1
package records: `FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is
not the real shared speech renderer. The request-envelope comparison stands in its place.

## 10. What is NOT claimed

- Nothing about task quality. The aborted attempt's 618 contacted rows were never scored and never
  read, and no partial read is permitted.
- The four-row smoke re-proves **form** on the fixed commit and nothing else; it cannot reach the
  illegal-action path.
- The fix is proved for an illegal Planner action. It says nothing about whether the Node Context
  Policy at level L1 helps -- that is what the recovery flight measures, under the unchanged
  preregistered rule.
- No claim about *why* the Planner emitted an illegal token on two rows, nor that the recovery will
  meet none. The count is a diagnostic to report, not a hypothesis this cell tests.
- No claim that the recovery run's realized requests equal the aborted run's: greedy decoding at
  `temperature 0` is not bitwise reproducible across batch compositions. What is pinned is the
  configuration and the request-construction surface.

## Outcome of the recovery smoke (2026-09-18, coordinator)

`SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1` flew at 2026-09-18T00:58Z through the
standalone worker attached to the resident session, at study commit `d1cb9d4d` (the E8c-fixed
code). Actuals: 20 calls, 52.98 audio seconds, 4 task-contract tool calls, 20/20 request fits
(minimum margin 10,303 tokens); manifest COMPLETED with the seal stage present. Every row shows the
five nominal contacts (Perception 1, Solver 1, Reviewer 2, Planner 1 ACCEPT, no revision) and a
receipt carrying `node_context_policy_compilations` per contact (`context_policy_config_sha256`,
`perception_response_format_sha256`, `template_sha256s`). The Solver request carries the L1
node-context block, each Reviewer request four, and the Planner brief carries the REVIEW OF THE
CURRENT DRAFT, DECISION BRIEF and HARNESS CHECKS blocks with both Reviewer outputs in their UNPARSED
L1 state (the Reviewer response format is cell B7r's factor). No illegal Planner action occurred on
the four rows, so the E8c retained-row path was not exercised in flight; its proof remains the
fake-model test landed with item E8c. **Structural PASS; no quality read.** The arm re-pins before
its launch and, under owner decision 19 of 2026-09-18, flies after cell B5e.
