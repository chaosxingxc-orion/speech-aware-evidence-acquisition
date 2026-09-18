# Cell B5e on the sealed anchor base: the one root-diagnosed recovery, registered before contact

Status: **REGISTERED BEFORE CONTACT.** Author: the B5e recovery registration agent, main checkout
`studies/speech-aware-evidence-acquisition`, branch `master`, base commit `835ecf10`.

This note is the **addendum** to
[`2026-09-18-slurp-b5e-combination-v1-preregistration.md`](2026-09-18-slurp-b5e-combination-v1-preregistration.md),
whose bytes are pinned by the sealed root decision `slurp-b5e-combination-admission-v1` and are
therefore **not edited**, and to its one amendment
[`2026-09-18-slurp-b5e-combination-v1-amendment-decision-23.md`](2026-09-18-slurp-b5e-combination-v1-amendment-decision-23.md),
which replaced clause 1 of section 7 under owner decision 23 (**the bar reads the OFFICIAL
unprojected SLURP `evaluate.py` number**) before any B5e number existed. Everything those two
documents say about the question, the arms, the metrics, the resampling, the decision rule, the
containment proof, the prompt fit and what is not claimed stands unchanged. Section 7 and section 11
of the preregistration allow *at most one root-diagnosed recovery re-registration per run*. **This is
it.**

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried; no run directory was written
(the aborted attempt's trace and receipts were read, read-only); `locks/flight.lock` was never held;
no scheduled task was touched.

## 1. What happened

Run `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1`, attempt
`attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-v1`, launched
**2026-09-18T14:35Z** as the Windows Scheduled Task `SAEA-Campaign-B5e` from the flight worktree at
study commit `325d67c6`, **ABORTED at 2026-09-18T14:40:20Z**. The recorded failure is, verbatim from
`attempts/SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1/attempt-…-generation-v1.json`:

```
generation failed during run_phases or seal: NativeEpisodeError: native episode node failed:
[100054] component 'solver_0_role' execute 'invoke' error, reason='llama.cpp prompt-audit
request failed: [Errno 32] Broken pipe', workflow='129a57816cea4c8e924969721ebe6c7f'
```

The campaign also saw `Remote end closed connection without response`. The mechanism, in one
sentence: **the task-owned resident llama-server died mid-request because all three SAEA scheduled
tasks stopped the instant the coordinator changed the power scheme with `powercfg`** —
`schtasks`-created tasks carry the default stop-on-battery condition, which the power-scheme change
tripped.

**It was not the harness, the config, the model or the host.** Host memory was 45.6 GB free; there
was no OOM; there was no harness error and no configuration error; the request bytes that had already
been transmitted were the registered ones. An earlier launch of 2026-09-18T03:32Z died with the
machine shutdown of 03:36Z **before opening any attempt** and therefore carries no exposure.

**The fix is outside this repository.** The three scheduled tasks were re-registered with the battery
and idle conditions disabled and no execution time limit, and the resident session was restarted
under the same session id with unchanged identity fields. Nothing in this repository changed, so
there is no code fix to prove and no test to add for one.

## 2. What was spent, and what is preserved

| item | value |
| --- | --- |
| attempt state | `ABORTED` |
| generation calls | 25 |
| repeated speech seconds | 63.72893749999999 |
| complete rows | 5 (a further 3 rows were in flight when the server died) |
| sealed `MODEL_REQUEST` payloads | 25 across 8 rows — perception 8, solver 5, reviewer 8, planner 4 |
| request-fit receipts | 25 under `prepared/SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-V1/`, every request fitting |
| trace | `runs/SAEA-…-TRAIN-FOLD-A-V1/attempt-…-generation-v1/SAEA-…-TRAIN-FOLD-A-V1.trace.jsonl`, 133 records: 25 `MODEL_REQUEST`, 24 `MODEL_RESPONSE`, 24 `MODEL_WIRE_RESPONSE`, 24 `COST`, 36 `USE` |
| flight lock | preserved and then reconciled by root: `coordination/slurp-b5e-combination-v1/flight-lock-preserved-20260918T144332Z.json` (SHA-256 `cc46fadcb7d6f7ea9d054d442feeda1d22394823182ac0619bd0622d298f79c9`) and `…/flight-lock-reconciliation-20260918T144332Z.json` (SHA-256 `b63d00003824aa7ab5138d912bd9993bb71eafb800ec409fa08def59d6283c81`) |
| score | none. No official scoring job ran and **no partial quality read was taken or is permitted** |

Everything above is **read-only**. Nothing under the run directory was modified by this registration.
The two exposure rows `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1` and
`…-TRAIN-FOLD-A-FIT-V1` are `consumed = yes` and carry the abort, the root cause and this recovery's
run ids in their notes. **Neither run id nor either attempt id is ever reused.**

The four-row form smoke `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-V1` had
already **sealed with a structural PASS** at study commit `878dd5c6` (20 calls, five contacts per row,
ACCEPT on 4/4 rows, both stores present in every phase record, 20/20 request fits with a minimum
margin of 9,562 tokens). Its rows are closed and it is not re-flown.

## 3. Why nothing in the science changes

The failure is an **infrastructure** failure of the machine that hosted the flight, caused by the
coordinator's own `powercfg` change. It is not a roster, prompt, knowledge, retrieval, budget,
geometry or scoring defect, and it gives no information about the question cell B5e asks. So:

- **no roster or split change.** Same 1,080-row TRAIN Fold A roster, same `SLURP-EVO-FOLD-A-V2`, same
  split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, same ordered ids.
  The 5 rows the aborted attempt completed are **not** filtered out and **not** reused — the recovery
  flies the whole roster from row one, as one complete manifest.
- **no module change.** `knowledge_stores` is byte-identical to the aborted arm's: M1's
  `train-exemplars` block is byte-for-byte cell B1's recovery-arm block (release `171aa4a8…`,
  snapshot `4c498dc0…`, plain top-k = 20, `saea-fuse-supplyfilter-v1` at m = c = top_l = 20, tau 0.0)
  and M4b's `slot-contracts` pair is byte-for-byte cell B4b's (release `f8e42d4f…`, snapshot
  `d5992bd1…`).
- **no prompt, role-graph or instruction change.** Perception 1 / solver 1 / reviewer 3 / planner 1,
  `max_revisions` 1, policy `phase-native-candidates-review-revise-v1`, the same composed instruction
  texts, the same `phase_tools` Reviewer task-contract authority.
- **no cap change.** 11,880 generation contacts, 47,520 FIT endpoints, 33,930 repeated speech seconds,
  12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score, zero
  ASR / encoder / paid-API calls. These are the aborted arm's own registered ceilings, unchanged, and
  they remain bounds rather than targets.
- **no geometry or session change.** The same resident session
  `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, 24,576-token slot, four slots.
- **no decision-rule change.** The TRAIN A own-null margins (h_SLU 1.1218, h_intent 1.0051), the
  read-once rule, the comparators, the estimators, the seed (20260915) and the draws (10,000) are
  exactly as preregistered, with clause 1 as the 2026-09-18 decision-23 amendment states it — the bar
  on the **official unprojected** number.
- **no containment or prompt-fit change.** The B1 containment result still carries (no instruction
  text moves), and the registered static upper bound stays **17,983** required tokens, margin 6,593
  against the 24,576-token slot (receipt `coordination/slurp-b5e-combination-v1/prompt-fit-v1.json`,
  SHA-256 `544903713390aad0a58986d528e71a9f100a87d63f25329230c11286198c0c5b`).

What *does* change is bookkeeping only: new run and attempt ids, this package's own
`native_contact_fit` identity, its own two speech-feature identity ids (provenance only), its own
prepared-supply pin, and the free-English notes.

**Budget accounting.** The 25 calls and 63.72893749999999 repeated speech seconds the aborted attempt
durably spent are charged to the **closed** run id
`SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1` and its `consumed = yes`
rows, not to the recovery run. The recovery run's own plan covers its own full worst case — 1,080
rows times the exact 11-contact program ceiling is 11,880 — and because the failure rule allows this
run no second attempt, the run-cumulative enforcement across every attempt of this run id is satisfied
by the single full re-fly.

## 4. The recovery cell

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1`, run `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1`, attempt `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1` |
| arm FIT | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-RECOVERY-V1` / `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-fit-recovery-v1`, 47,520 endpoints |
| baseline | `configs/baseline/slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-train-fold-a-recovery-v1.json` |
| experiment | `configs/experiment/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1.json` |
| campaign plan | `configs/campaign/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1.json` |
| composed / protocol | `50ae44a67e1d6e897e266f9ebadb4eead62df091d4f4fbc72b9a8100b1f28ae1` / `b5d14e1fe060ee9f2b7ccc6d174b4e16cd82b5b07a9d9850808d2656ecfee4c0` |
| prepared supply | `prepared/SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1/phase-supply-v1.json`, SHA-256 `5bfc6bcdeda7438ca01725072267fe53086ffdb6395d813b3a6c897be4bfef0a`, **output** SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| plans | `docs/readiness/2026-09-18-slurp-b5e-combination-v1-recovery-v1/` — the generation and FIT plan pairs, the recovery protocol document, the recovery analysis recipe and the runbook |
| readiness | `held` with the `preparation` requirement pinned and **no decision requirement**; the coordinator adds the `decision` requirement and flips with `scripts/flights/repin_cell.py` |
| decision | id `slurp-b5e-combination-recovery-admission-v1`, receipt `coordination/slurp-b5e-combination-v1/root-admission-recovery-v1.json` — **the coordinator mints it**; this package deliberately does not |
| supersedes | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1` and `…-FIT-V1`, both closed and never reused |

**The composed and protocol hashes above are the pre-flip values** of the four fragments exactly as
committed: readiness `held`, the `preparation` requirement pinned, `prepared_phase_supply` pinned, no
`decision` requirement. `compose()` hashes the complete merged fragment set, so adding the decision
requirement and flipping readiness each change both. The re-pin tool recomputes them and rewrites
every document that quotes them; nobody edits them by hand.

**The prepared Perception supply does not move.** `prepare-supply` was re-run model-free at **one
worker** on this commit for the recovery cell, and its `output` is byte-identical to the aborted arm's
own artifact and to the sealed anchor's, cell B1's and cell B4b's: `output_sha256`
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` on **1,080 of 1,080** rows. The
same `compose` / `protocol_hash` command run on four sealed registrations returns their registered
protocol hashes — the anchor's `d1c61c09…`, the anchor recovery's `2527b527…`, cell B1's
`c66d507d…` and cell B4b's `567a87ad…` — so the method is verified. Receipt:
`coordination/slurp-b5e-combination-v1/recovery-prepared-supply-and-hashes-v1.json`.

## 5. The request envelope: what moves, and what cannot

Receipt `coordination/slurp-b5e-combination-v1/recovery-request-envelope-comparison-v1.json`,
SHA-256 `4ec576839d1d0cc56526cf0bf0408ac50169c415c07b59a9c7eedfb29c12d5e7`.

1. **Config diff, on the COMPOSED values.** The recovery configuration differs from the aborted one in
   **11 of 67** composed keys and **none of them is model-facing**: `native_contact_fit`,
   `prepared_phase_supply`, `speech_feature_key_representation_id`,
   `speech_feature_matcher_policy_id` and `what_this_is` from the baseline fragment, and `cells`,
   `experiment_id`, `failure_policy`, `fragment_kind`, `generation_budget` (its free-English
   `definition` only; the cap 11,880 and the target are unchanged) and `purpose` from the experiment
   fragment. The other **56** — `knowledge_stores`, `policy`, `native_episode`, `phase_material`,
   `phase_tools`, `preparation_source_receipts`, `scorers`, `serving_slot_tokens`, `serving_slots`,
   the speech packet promotion receipt, every instruction template, the roster and the population —
   are byte-identical. The committed proof is `tests/unit/test_b5e_combination_recovery_config.py`.
2. **None of those strings is in any request.** All **25** sealed `MODEL_REQUEST` payloads of the
   aborted attempt are searched, on every field, for **twelve** identity strings: the aborted run,
   attempt, FIT run and FIT attempt ids and both aborted speech-feature ids, and the same six for the
   recovery. The result is **0 hits on every one of the twelve**, on every row and phase.
3. **The payload's own `key_representation_id` and `matcher_policy_id` are program-derived, not
   config-derived.** Every one of the 25 payloads carries `matcher_policy_id`
   `phase-native-candidates-review-revise-v1` and a `key_representation_id` of the form
   `phase-native-candidates-review-revise-v1:<phase>`, so the baseline's speech-feature identity ids —
   the one pair this registration deliberately makes unique — do not reach a request byte at all.
4. **Per-contact digests are pinned.** For each of the 25 payloads the receipt records a SHA-256 over
   the whole payload minus `request_id` and the `evidence_provenance` message relpaths derived from
   it, alongside the sealed `payload_sha256` the flight itself wrote. That is the table the recovery
   flight's own first contacts can be checked against.

**The honest limit:** the recovery arm has not flown, so its own realized post-Perception requests
cannot be re-derived model-free — they depend on the frozen core's answers, and greedy decoding at
`temperature 0` is not bitwise reproducible across batch compositions, so trajectories may differ row
by row. What is proved here is that no configuration byte that reaches a request moved.

`core.flight.cli wire-check` remains unavailable for any native-episode cell, for the reason the B5e
package records: `FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is
not the real shared speech renderer. The composed-key diff and this identity search stand in its
place.

## 6. No smoke, and why

**No new four-row smoke is registered.** The form is already proved twice on this exact
configuration:

- the four-row smoke `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-V1` sealed with
  a structural PASS at study commit `878dd5c6`, with both stores present in every phase record and
  20/20 request fits; and
- the aborted arm itself realized the same form on the **full** roster — 25 sealed contacts across 8
  rows, 25 request-fit receipts, every request fitting — before the server died.

The failure was not a form failure, and the recovery changes nothing a smoke could test. Registering a
new smoke would spend contacts to re-prove a proved form. A failure of the recovery flight is still
governed by the preregistration's own rule: the cell closes and the fix must be proven on a four-row
dry run before another mechanism is admitted.

## 7. Launch

The runbook is `2026-09-18-slurp-b5e-combination-v1-recovery-v1/README.md`, sections 2, 3 and 5.
Campaigns are launched as **Windows Scheduled Tasks**; the task that carries this campaign must have
the battery and idle conditions disabled and no execution time limit, and `powercfg` must not be run
against the machine while a campaign is in flight. That is the fix, and verifying it is item 4 of the
pre-launch checklist.

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1 \
    --cell slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1 \
  --readiness-dir docs/readiness/2026-09-18-slurp-b5e-combination-v1-recovery-v1 \
  --preregistration docs/readiness/2026-09-18-slurp-b5e-combination-v1-recovery-v1.md \
  --package-name slurp-b5e-combination-v1 \
  --decision coordination/slurp-b5e-combination-v1/root-admission-recovery-v1.json \
  --decision-id slurp-b5e-combination-recovery-admission-v1 \
  --set-ready
```

Then the campaign, over
`configs/campaign/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1.json`.

The re-pin tool rewrites this note, the recovery plan directory and the two recovery ledger notes; it
does **not** touch the preregistration, the amendment or the aborted registration's package, whose
plan files keep their sealed hashes, and it refuses if either target exposure row is already
`consumed = yes`.

## 8. Failure rule, restated, and the E10 conversion clause

This registration **is** the one root-diagnosed recovery the preregistration allows for cell B5e. A
second failure closes this cell: no third registration, no replay, no row filtering, and the fix must
be proven on a four-row dry run before another mechanism is admitted.

**Why this is a full re-fly rather than a resume.** Owner decision 22 of 2026-09-18 requires every
future experiment to support checkpoint resume, but its implementation item **E10 is not merged**.
Resuming would recover 25 contacts out of an 11,880-contact ceiling — about 0.5 % of the expected
spend — so it does not pay here.

**E10 conversion clause.** If item E10 lands **before** this recovery flies, the coordinator **may**
convert this registration to a resume-recovery under owner decision 22 instead of a full re-fly. The
conversion changes no question, roster, factor, comparator, decision rule, metric or cap, and it is
not a second recovery. It must re-check the run-cumulative budget, because a resumed attempt and its
predecessor share one run id, and it must state in the verdict which rows were resumed rather than
re-flown.

## 9. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b5e-combination-v1/`, outside the repository so no
receipt can dirty the tree the manifest reads at finalize.

| receipt | what it proves |
| --- | --- |
| `recovery-prepared-supply-and-hashes-v1.json` | the rebuilt prepared artifact and its pin; its `output` byte-identical to the aborted arm's, the sealed anchor's, cell B1's and cell B4b's; the recovery composed and protocol hashes; the composed-key diff against the aborted arm (56 identical / 11 differing, none model-facing); the four-way method verification against sealed registered values |
| `recovery-prepare-supply-v1.json` | the raw model-free `prepare-supply` receipt, `contact_class = model-free`, one worker |
| `recovery-request-envelope-comparison-v1.json` | the twelve-string identity search across the aborted attempt's 25 sealed `MODEL_REQUEST` payloads (0 hits), the program-derived id proof, and the per-contact model-facing digests |
| `recovery-ledger-parse-v1.json` | `contracts._parse_ledger_tables` sees each of the two new rows exactly once at `consumed = no` and the four rows of the aborted registration exactly once at `consumed = yes` |
| `recovery-plan-hashes-v1.txt` | the SHA-256 of this note, of every document in the recovery readiness directory and of the three config fragments |
| `flight-lock-reconciliation-20260918T144332Z.json` | root's quiescence proof: owner pid dead, 0 slots processing, attempt `ABORTED` at 25 calls and 63.72893749999999 s, `flight.lock` moved to the preserved copy |
| `prompt-fit-v1.json` | the aborted registration's prompt-fit receipt, unchanged and still authoritative: static bound 17,983 required tokens, margin 6,593 |

**No `core.flight.cli check` receipt is on file, and that is deliberate.** `FlightRuntime.preflight`
asserts a clean study tree and reserves the attempt in the durable `AttemptStore`; a registration
agent that has not committed can neither pass the first nor is entitled to the second. The composed
and protocol hashes were computed directly through `core.config.compose` / `core.config.protocol_hash`
— the same two functions `check` itself uses — and the method was verified four ways against sealed,
registered values. The coordinator's re-pin cycle runs `check` on the clean registration commit and
**asserts the runtime-derived hashes equal the ones it has just written**; if they differ by one
character, the launch stops.

## 10. What is NOT claimed

- **Nothing about task quality.** The aborted attempt's 25 complete contacts were never scored and
  never read, and no partial read is permitted.
- **No claim that the recovery run's realized requests equal the aborted run's.** Greedy decoding at
  `temperature 0` is not bitwise reproducible across batch compositions. What is pinned is the
  configuration and the request-construction surface.
- **No re-litigation of the cell's own claims.** Everything the preregistration and the decision-23
  amendment say — the bar on the official unprojected number, the combination clause against the
  sealed B1 arm, the HARMFUL trigger, the additivity diagnostic, the STOP condition, and the whole
  "what is NOT claimed" list of section 12 — stands unchanged and is not restated here.
- **No claim that the infrastructure fix is proved by this package.** It is a scheduled-task and
  power-scheme change on the host, verified by the pre-launch checklist rather than by a test in this
  repository.
- **Meeting the bar on this pass is still not "replicated".** B5er is what replication means here.
