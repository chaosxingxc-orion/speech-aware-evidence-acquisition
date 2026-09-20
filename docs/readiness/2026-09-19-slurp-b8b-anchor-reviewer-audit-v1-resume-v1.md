# Cell B8b-anchor: the one root-diagnosed recovery, as a RESUME-RECOVERY, registered before contact

Status: **REGISTERED BEFORE CONTACT.** Author: the cell B8b-anchor resume-recovery registration
agent, detached worktree `/home/chao/saea-worktrees/fable-b8ba-resume`, branch `fable/b8ba-resume`,
base commit `8032c7a4` (which carries harness item E22, merged at `6ecacc1b`).

This note is the **addendum** to
[`2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-preregistration.md`](2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-preregistration.md),
whose bytes the sealed root decision `slurp-b8b-anchor-reviewer-audit-admission-v1` pinned and which
is therefore **not edited**. Everything that document says about the question, the one factor, the
comparator, the margins, the metrics, the resampling, the decision rule, the mandatory tables, the
cost reporting and what is not claimed stands unchanged. Its failure rule allows *at most one
root-diagnosed recovery re-registration per run*. **This is it**, taken in the **resume-recovery**
form owner decision 22 of 2026-09-18 requires.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer, server and
paid-API contacts**. The resident service was never started, stopped or queried; nothing under
`runs/`, `attempts/` or `prepared/` was written, moved or renamed (the aborted attempt's trace,
attempt record, flight receipts and fit-receipt directory were read, read-only); `locks/flight.lock`
was never held; no scheduled task was touched; `prepare-supply` was not run; and
`docs/exposure-ledger.md` was not edited. No utterance text, filler or gold is printed or persisted
anywhere in this package.

## 1. What happened

Run `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1`, attempt
`attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1`, flown from the worktree
`/home/chao/saea-worktrees/fable-b8ba-flight` at study commit
`c905ddf01dbb6e9c2e62cf154a413add3bf0c506`, **ABORTED at 2026-09-19T22:15Z** after **2,016**
generation contacts and **5,481.64550000003** repeated speech seconds. The recorded failure is,
verbatim from
`attempts/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1/attempt-…-generation-v1.json`:

```
generation failed during run_phases or seal: NativeEpisodeError: review node did not return an answer
```

The mechanism, in one sentence: **with the Reviewer slot-audit attachment armed, the Reviewer's
ReAct loop spent all three of its iterations calling `saea-tool-task-contract-v1` without producing
an answer on 2 of 410 visits, and `reproduction.ojw.native_episode._ApplyRole` refused the pinned
framework's exhaustion literal because the harness had no disposition for ReAct exhaustion.**

The campaign log `/home/chao/b8ba-campaign-20260919T205944Z.log` (read-only; 55,674 lines),
re-counted by this registration:

| fact | evidence |
| --- | ---: |
| generation contacts | 2,016 `[LLM] >>> request` lines |
| Reviewer visits opened | 410 at `ReAct iteration 1/3` |
| Reviewer visits at iteration 2 | 409 |
| **Reviewer visits that reached `3/3`** | **2** |
| tool calls in the whole arm | 413 `Executing tool` lines, **413 of 413** `saea-tool-task-contract-v1 with args: {}` — one tool, one empty argument object, no variation |
| `workflow_execute_error` events | 5: at 14:28:58, 14:31:06 and 14:40:31 (the **E13** class, `finish_reason` `length`, all three rows **retained** by the armed `finite_completion_policy`) and at 15:13:24 and 15:15:46 (the **new** class, `review node did not return an answer`, both at node `reviewer_1_state`) |
| the comparator never reaches `3/3` | cell B1r's arm log `/home/chao/b1r-campaign-20260919T164911Z.log`: **1,092** visits at `1/3`, **0** at `3/3` |

**It was not the roster, the prompt, the knowledge, the retrieval, the budget, the geometry, the
scoring or the question.** The flight worktree was clean at `c905ddf0`; the request bytes already
transmitted were the registered ones; the prepared Perception artifact verified `identity_ok` at
preflight; the prompt budget decided **ALLOW** on all four phases; and three *earlier* length-capped
Reviewer completions in the very same flight were retained by the armed `finite_completion_policy`
— the same class of repair, one item earlier. The fix is **item E22** (the ReAct-exhaustion
disposition, not the Earnings-22 carrier),
[`docs/superpowers/specs/2026-09-19-e22-react-exhaustion-design.md`](../superpowers/specs/2026-09-19-e22-react-exhaustion-design.md),
merged on master at `6ecacc1b`, whose gate
`scripts/checks/finite_completion_policy_check.py` now demands **both** failure-mode keys of every
live, unflown native cell.

## 2. What was spent, and what is preserved

| item | value |
| --- | --- |
| attempt state | `ABORTED` |
| generation calls | 2,016 |
| repeated speech seconds | 5,481.64550000003 |
| trace | `runs/SAEA-…-TRAIN-FOLD-A-V1/attempt-…-generation-v1/SAEA-…-TRAIN-FOLD-A-V1.trace.jsonl`, 169,656,308 bytes, 13,282 records, SHA-256 `d495661dc7904eebb51818d4b35996a175de37af08d07ae56e904528fd6a84e3` |
| rows with requests | 380 |
| rows COMPLETE (terminal episode receipt, every response recorded) | **378** |
| rows INCOMPLETE | **2** |
| rows never started | 700 |
| request-fit receipts | 6,048 files under `prepared/SAEA-…-FIT-V1/attempt-…-fit-v1/`, every request fitting |
| retained `finite_completion` rows | 3 (item E13 did its job; a mandatory diagnostic of the read) |
| flight lock | preserved and then reconciled by the coordinator: `coordination/slurp-b8b-anchor-reviewer-audit-v1/flight-lock-preserved-20260919T223435Z.json` (SHA-256 `17860a27b974fb3b4403a11a12f693a01d071a2498f103f698d72605cc8815b9`) and `…/flight-lock-reconciliation-20260919T223435Z.json` (SHA-256 `48c9018185d73792de97e3882edb19e206a344b89982869f6b0486e0879cc41d`) |
| score | none. No official scoring job ran and **no partial quality read was taken or is permitted** |

Everything above is **read-only**. Nothing under `runs/`, `attempts/` or `prepared/` was modified by
this registration. The run's two exposure rows —
`SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` (ledger line 4832) and
`…-FIT-V1` (line 4833) — both read **`consumed = no`** and are left exactly as they are, because a
resume flies under the same run id and both the re-pin tool
(`core.flight.repin.assert_rows_available`) and the fit gate
(`FlightRuntime._require_exposure_row_unconsumed`) refuse a consumed row. **No new ledger row is
added**, the two four-row smoke rows (4830, 4831) stay closed at `consumed = yes`, and the run id
and the predecessor attempt id are never reused as this attempt's own identities.

## 3. The resume: mode A, what is kept and what is flown

Harness item E10 implements **mode A — trace replay plus seal-time merge** (`core.flight.resume`;
the four modes and the choice are compared in
[`docs/superpowers/specs/2026-09-18-resume-modes-comparison.md`](../superpowers/specs/2026-09-18-resume-modes-comparison.md),
owner decisions 22 and 24). The recovery cell declares, in its committed experiment fragment and
nowhere else — there is deliberately no command-line flag:

```json
"resume_from": {
  "attempt_id": "attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1",
  "trace_sha256": "d495661dc7904eebb51818d4b35996a175de37af08d07ae56e904528fd6a84e3"
}
```

`FlightRuntime.preflight` scans that trace **model-free, before any server exists**, and refuses if
the bytes do not hash to the declared value, if the predecessor flew a row outside this flight's
roster, or if every row is already complete. The scan, re-run by this registration on the bytes on
disk through
`core.flight.resume.read_predecessor_attempt(program_id="phase-native-candidates-review-revise-v1")`:

| quantity | value |
| --- | --- |
| trace SHA-256 re-hashed on disk | `d495661dc7904eebb51818d4b35996a175de37af08d07ae56e904528fd6a84e3` (matches the declaration) |
| trace bytes / records | 169,656,308 / 13,282 |
| contacts in the trace | 2,016 |
| rows with requests | 380 |
| **COMPLETE, kept without selection** | **378** |
| **INCOMPLETE, re-flown in full** | **2** |
| never started, flown | 700 |
| **rows this attempt flies** | **702** |
| roster | 1,080 (`SLURP-EVO-FOLD-A-V2`, split identity `61b0f062…`); rows flown outside the roster: 0 |
| sorted kept-sample-id SHA-256 | `19b8b9e059d8a67bd83b8d7c72f86dc3d319617ea6fb123d32340faa91cfaccf` |

The two partial rows, by id, each for the same recorded reason — *the episode emitted no terminal
receipt*:

- `slurp:train:004389:audio-1502113264`
- `slurp:train:004534:audio-1498647066-headset`

**These are exactly the two exhausted visits' rows.** They are re-flown in full; if a Reviewer visit
exhausts again under greedy decoding, the armed policy retains the row with a `react_exhaustion`
visit disposition instead of closing the flight, and the count is reported in the read.

**Completeness is the episode's own terminal receipt, never a contact count.** The replay classifies
delivery with the same validator the seal uses
(`rails.native_episode_receipt.validate_native_episode_delivery_receipt`, in its documented
post-seal reader mode) and checks every contact the receipt names against the recorded request and
response digests.

**No selection is possible anywhere in this path.** The kept set is exactly the predecessor's
COMPLETE rows and the flown set is exactly the rest of the registered roster; `core.flight.resume`
raises rather than honour any other partition. The seal renders kept and flown rows through the one
`_canonical_output_rows` stage, so a kept row is byte-identical to the row the aborted attempt would
have sealed; the manifest declares `predecessor_attempt` (trace SHA-256, the sorted kept ids and
their hash, the kept/flown/partial counts); `core.bundle.verify_bundle` holds every kept row against
the predecessor trace byte for byte under invariant **I7r**; and the complete 1,080-row manifest is
scored **once**.

## 4. Why nothing in the science changes

The failure is a harness defect with a named component, on a disposition the runtime simply did not
have. It is not a roster, prompt, knowledge, retrieval, budget, geometry or scoring defect, and it
gives no information about the question cell B8b-anchor asks. So:

- **no roster or split change.** The same 1,080-row TRAIN Fold A roster, the same
  `SLURP-EVO-FOLD-A-V2`, the same split identity
  `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, the same ordered ids. Fold B,
  DEV-1000 and the test split are absent and untouched.
- **no module, prompt, role-graph, geometry or cap change.** The one factor
  `native_episode.reviewer_audit` with the released view `slot-audit-v1` and its three registered
  thresholds, both knowledge stores at `intent-boundaries-v1` and `slot-contracts-v1`, the arm
  `speech-feature-query-native-tools`, the policy `phase-native-candidates-review-revise-v1`, the
  full native episode with the review loop on (`max_revisions` 1, reviewer `max_iterations` 3,
  program ceiling 11 contacts), every instruction template, the `phase_tools` block, the scorers,
  the model fragment (temperature 0, seed 20260913, `max_tokens` 512), the promoted EVO-FOLDS-V2
  packets and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` are
  byte-identical to the aborted arm's.
- **the two WAVE R7 speech-feature identity strings are HELD**, not minted fresh. A *resume* must
  not move them: they ride the audited payload as ORG/CONTROL provenance and the 378 kept rows
  already carry the aborted attempt's values.
- **no decision-rule change.** The margins (B0r's own null, h_SLU **1.1218** / h_intent
  **1.0051**, owner decision 38), the HARMFUL-by-measured-loss rule (Method B, owner decision 25),
  the ADMITTED conjunction, the resampling, the CI levels and the mandatory tables are exactly as
  preregistered.
- **no comparator change.** The sealed dual-store anchor
  `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` (official pooled SLU-F1 48.53363,
  intent 77.96296, n = 1,080) is the comparator. It is sealed bytes; it is never re-flown or
  re-scored.

What *does* change is the fresh cell and attempt identities, the `resume_from` declaration, the
native-fit **attempt** id, the free-English fields (`purpose`, `failure_policy`,
`generation_budget.definition`, `population.decision_population`, `readiness.reason`,
`what_this_is`) — and **one declared repair**, below. The committed proof is
`tests/unit/test_b8b_anchor_reviewer_audit_resume_config.py`.

### 4.1 The one declared repair: `react_exhaustion_policy`

`native_episode.react_exhaustion_policy = "continue-without-answer"` (item E22). It is declared
beside the `finite_completion_policy` the arm already carried, and it is the **only** behavioural
change of this recovery.

It **renders no request byte.** `rails.runner` reads it once into the core `NativeEpisodeSpec`; it
is not a prompt, a tool, a template or a routing change. It fires **only on a visit that would
otherwise abort the flight**: the exhausted Reviewer visit ends with an empty finding
(`state["review"] == ""`, the state the graph would hold if the Reviewer had reviewed and found
nothing — never the framework's sentence, which a committed test asserts never reaches any rendered
request), custody of its contacts is kept in `role_visits` with their full execution receipts, the
Planner routes normally, **nothing is retried**, no extra contact is spent, and a
`react_exhaustion` record is sealed into the episode receipt. Its scope is
`REACT_EXHAUSTION_STAGES == {"review"}` and nothing else: Solver, Planner and Perception keep their
pre-E22 raise.

On a row whose roles all answer, arming the key composes **byte-identical requests and identical
receipts** on both arms — E22's own falsifier test. On the aborted attempt's own evidence, the
Reviewer reached iteration `3/3` on **2 of 410** visits; the comparator reached it on **0 of 1,092**.
The asymmetry is therefore **measured, not assumed**, exactly as the arm's `finite_completion_policy`
asymmetry already is, and `react_exhaustion_rows` / `react_exhaustion_visits` are mandatory
diagnostics of the read. Retaining a row whose Reviewer found nothing is **not** evidence that the
row is as good as one whose Reviewer reviewed; that is stated in section 10 and in the protocol.

**At the flight commit `c905ddf0` the key was absent**, and therefore at the module default
`"raise"`. Item E22 armed it on this cell's flown-arm baseline on master at `97e90a9b`. So the
resume baseline differs from the **bytes the aborted attempt actually flew** in exactly three
leaves — `native_episode.react_exhaustion_policy`, `native_contact_fit.attempt_id` and
`what_this_is` — and from the same baseline **as it stands on master** in exactly two.

### 4.2 The one runtime-forced identity: a fresh native-fit ATTEMPT

`native_contact_fit.attempt_id` moves to
`attempt-slurp-native-reviewer-audit-anchor-train-fold-a-fit-v1-resume`. The **FIT run id does not
move**, and neither does `contact_cap`.

This is required by the runtime, not chosen. `core.preparation_fit.build_native_contact_fit_gate`
writes one request-fit receipt per realized contact to
`prepared/<fit run>/<fit attempt>/<sha256 of {sample_id, agent_contact_id}>.request-fit.json` and
**refuses a path that already exists**. `agent_contact_id` is the deterministic
`<program>:<phase>:<iteration>:<sample id>`, so a re-flown partial row re-mints the exact contact
ids it used before, and the predecessor fit attempt already holds **6,048** receipts — the two
partial rows' among them, verified read-only on disk by this registration. Re-flying them under that
attempt would refuse at the first contact and abort the whole flight. The fit root is namespaced by
run **and** attempt, so a fresh attempt id under the unchanged fit run id is the minimum change that
clears it, and it keeps the run's exposure accounting on its existing two ledger rows rather than
opening a third.

`contact_cap` stays **47,520** = 1,080 registered rows × 11 contacts × (1 speech packet + 3
endpoints). The gate derives the required cap from the whole registered roster, not from the flown
subset, and refuses any other value.

Because `native_contact_fit` lives in the baseline fragment and `core.config.compose` refuses a key
defined by two fragments, this one field forces a sibling **baseline fragment**,
`configs/baseline/slurp-native-anchor-reviewer-audit-train-fold-a-v1-resume.json`. Editing the
aborted arm's own baseline in place was rejected: it would retroactively move a closed
registration's composed hash.

## 5. Budget: run-cumulative, and the arithmetic

A resumed attempt and its predecessor **share one run id**, so exposure accounting is run-cumulative
across attempts — `core.attempts.AttemptStore.prior_actual_usage` sums the actual calls and audio
seconds of every attempt file under the run id and the gate holds that sum against
`planned_model_calls` (invariants I3/I6).

| term | value |
| --- | ---: |
| predecessor attempt, durably spent | 2,016 |
| this attempt's worst case: 702 flown rows × 11 contacts (the program ceiling) | 7,722 |
| **run-cumulative worst case** | **9,738** |
| registered `planned_model_calls` (unchanged) | 11,880 |
| headroom | 2,142 |

`FlightRuntime.preflight` reports the same 7,722 as `resume.worst_case_contacts`, beside the
kept/flown/partial counts and the per-row reasons, and it reports it rather than reconciling it: the
number the plan declares is the owner's, not the stage's. Every other ceiling is the aborted arm's,
unchanged and still a bound rather than a target: 47,520 FIT endpoints, 33,930 repeated speech
seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete
score, zero ASR, encoder and paid-API calls.

Expect the resume itself to realize about **3,520 contacts** and about **2.4 GPU hours**: the sealed
anchor realized 5,417 contacts on 1,080 rows (5.016 per row) and this attempt flies 702 of them.
That is what the resume buys: **2,016 of the run's roughly 5,400 contacts never have to be paid
again.**

## 6. No smoke, and why

**No four-row smoke is registered, and none is needed.** The form is proved three times over on this
exact configuration:

- cell B8b-anchor's **own** four-row smoke `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1`
  sealed the structural form of this episode and its two exposure rows are closed;
- **the aborted attempt itself realized that form 2,016 times on this roster**, with 6,048
  request-fit receipts, every request fitting, an `ALLOW` prompt-budget decision on all four phases,
  and three length-capped Reviewer completions retained by the E13 policy. Those sealed contacts are
  the strongest form evidence this cell can have, and they are the very bytes the resume keeps;
- and the failure was not a form failure: the resume changes nothing a smoke could test.

What is new is the **harness path**, twice, and each is covered by its own committed tests. E10's
tests fly the real native episode graph against a fake model — uninterrupted, and
aborted-then-resumed — and compare the kept rows byte for byte for a nominal episode, an episode with
an executed revision, a partial row and an unstarted row, plus six refused tamperings of the merged
manifest. E22's 36 tests (`tests/unit/test_e22_react_exhaustion.py`) drive the **actual** runner with
a Reviewer that answers with a tool call on all three iterations: under `"raise"` they reproduce the
flown sentence verbatim, under the armed policy they get a retained row that delivers the Solver's
own draft, keeps all three Reviewer contacts in `role_visits`, seals the block, routes the Planner on
`ACCEPT` and spends exactly six contacts; they prove the framework's literal never reaches a rendered
request; and they prove byte-identical requests and identical receipts on both arms for a row whose
roles all answer. Registering a smoke would spend contacts to re-prove a proved form and would put
four rows of this roster through an extra batch composition before the measurement this cell exists
to make.

## 7. Failure rule, restated

This registration **is** the one root-diagnosed recovery re-registration the preregistration allows
for this run. A second failure **closes cell B8b-anchor**: no third registration, no second resume,
no replay, no row filtering, no roster, role-graph, prompt, geometry or cap change, and the fix must
be proven on a four-row dry run before another mechanism is admitted. A partial manifest is never
scored and never read. One experiment in flight at a time.

Owner decision 22 also makes checkpoint resume a **standing rule**: every experiment registered from
now on must support it, and every new preregistration's failure rule carries the resume-recovery
clause.

## 8. The recovery cell

| item | value |
| --- | --- |
| cell / experiment fragment | `slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume` |
| generation run / attempt | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` (**unchanged**) / `attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1-resume` |
| native fit run / attempt | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-FIT-V1` (**unchanged**) / `attempt-slurp-native-reviewer-audit-anchor-train-fold-a-fit-v1-resume` |
| model fragment | `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` (**unchanged**) |
| dataset fragment | `slurp-speech-native-evo-fold-a-1080` (**unchanged**) |
| baseline fragment | `slurp-native-anchor-reviewer-audit-train-fold-a-v1-resume` |
| campaign plan | `configs/campaign/slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume.json` |
| composed config / protocol | `1170659f0fcda16ee5f051b5be85fda869e2e986dc150a478dfc26bbcafe2ead` / `ffb4595b210aa3db754bb356f9573e9efc3830ab85c80d39ad4dea438ac325db` |
| prepared phase supply | inherited pin `prepared/SAEA-…-TRAIN-FOLD-A-V1/phase-supply-v1.json`, SHA-256 `4d3233fd71b2ffa2ffa2e7b1b50d944f238c0729203647460f26fe6986b1f82c`, **output** SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`; the re-pin cycle rebuilds it as the next `phase-supply-v*.json` under the same run id (see below) |
| rows kept / flown | 378 / 702 (700 never started, 2 partial) |
| budgets | 11,880 generation calls (**run-cumulative**), 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score — cell B8b-anchor's own ceilings, unchanged |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| plans | `docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-resume-v1/` — the generation and FIT plan pairs, the resume protocol document, the analysis recipe and the runbook |
| readiness | `held` with the `preparation` requirement pinned and **no decision requirement**; the coordinator adds the `decision` requirement and flips with `scripts/flights/repin_cell.py` |
| decision | id `slurp-b8b-anchor-reviewer-audit-resume-admission-v1`, receipt `coordination/slurp-b8b-anchor-reviewer-audit-v1/root-admission-resume-v1.json` — **the coordinator mints it**; this package deliberately does not |
| supersedes | attempt `attempt-…-generation-v1` (ABORTED) and fit attempt `attempt-…-fit-v1`; the **run ids are kept**, because that is what a resume is |

**The composed and protocol hashes above are the pre-flip values** of the four fragments exactly as
committed: readiness `held`, the `preparation` requirement pinned, `prepared_phase_supply`
inherited, no `decision` requirement. `compose()` hashes the complete merged fragment set, so adding
the decision requirement and flipping readiness each change both. The re-pin tool recomputes them
and rewrites every document that quotes them; nobody edits them by hand. **The method was verified
against a sealed registered value:** the same `compose()` / `protocol_hash()` calls reproduce the
aborted arm's registered `04592f9515a24cc3f34f57787202209d3391f04f363e4d863e1ce6c3cc6f0ae2` and
`8b339a25d25e6a53a1d7efff57ad46861f8ba0a84d7f29f2257919cf496b7e13` **from its fragments as they
stood at the flight commit `c905ddf0`** (git blob bytes, `git show c905ddf0:configs/…`, never the
working tree, where item E22 has since armed the third key). Those are also the values the aborted
attempt's own preflight receipt records.

**The prepared Perception supply does not move, but its FILE must be rebuilt.**
`core.preparation.artifact_inputs` binds the composed values — the cell and attempt identities
included — so the inherited pin will not verify against the resume cell's composed digest. That is
expected and is handled by the launch step: `core.flight.repin.ensure_artifact_pinned` detects
exactly that mismatch, rebuilds the artifact model-free into the next `phase-supply-v*.json` under
the same run id, **asserts its `output` equals the previous artifact's**, and re-pins it in the same
cycle. This registration deliberately does not run `prepare-supply` itself: the re-pin cycle does
the same work, once, with the assertion attached. **`--allow-output-change` must never be given**:
an output that moved would mean the knowledge channel moved, and the resume would no longer be a
resume.

## 9. Launch

The runbook is
[`2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-resume-v1/README.md`](2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-resume-v1/README.md),
sections 2, 3 and 5. The ledger precondition is item 1 of its checklist: **both** exposure rows of
this run must still read `consumed = no`.

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume \
    --cell slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume \
  --readiness-dir docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-resume-v1 \
  --preregistration docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-resume-v1.md \
  --package-name slurp-b8b-anchor-reviewer-audit-v1 \
  --decision coordination/slurp-b8b-anchor-reviewer-audit-v1/root-admission-resume-v1.json \
  --decision-id slurp-b8b-anchor-reviewer-audit-resume-admission-v1 \
  --set-ready
```

Then the campaign, over
`configs/campaign/slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume.json`, launched as a
Windows Scheduled Task with the battery and idle conditions disabled and no execution time limit.

`--preregistration` points at **this note**, not at the sealed preregistration, whose bytes the
original decision receipt pinned and which must not be rewritten. **One cell per package
invocation**: this package holds exactly one cell's plans, so the re-pin tool rewrites this note,
the resume plan directory and nothing of the aborted registration's package, whose plan files keep
their sealed hashes. It refuses if the generation run's exposure row is `consumed = yes`.

## 10. What is NOT claimed

- **Nothing about task quality from the predecessor.** Its 2,016 contacts were never scored and
  never read; no partial read is permitted; the 378 rows it completed reach a number only through
  the one official score of the complete merged 1,080-row manifest.
- **No sub-population claim about kept versus flown rows.** Which rows the predecessor happened to
  finish before the flight died is an arrival-order fact, not a property of the rows. Kept and flown
  rows are never separated, compared or reported as strata; the read is of one complete 1,080-row
  manifest, exactly as preregistered.
- **No claim that a resumed pass is a *cleaner* pass than a re-flown one.** 378 rows keep the batch
  composition they were drawn under and 702 rows are drawn under a new one; greedy decoding is not
  bitwise reproducible across batch compositions, and this note makes no claim that the effect of
  that is zero.
- **No claim that retaining an exhausted Reviewer visit is neutral to quality.** The
  ReAct-exhaustion disposition is a failure-mode repair, not a mechanism. A row whose Reviewer found
  nothing is not thereby as good as one whose Reviewer reviewed; the counts are diagnostics and the
  asymmetry against the comparator (0 of 1,092 visits at `3/3`) is reported, never reconciled.
- **No second factor.** Item E22 adds no repeated-tool-call guard and no change to the Reviewer's
  prompt, tools, `max_iterations` or routing. A cell that wants the Reviewer to stop asking the same
  question is a different cell.
- **No re-litigation of the cell's own claims.** Everything the sealed preregistration says — the
  one factor, the comparator, the margins, the decision rule, the mandatory tables, the per-scenario
  diagnostics and the whole not-claimed list — stands unchanged and is not restated here. In
  particular: no superiority, generalization, paper-scale or held-out claim; TRAIN Fold A is an
  exposed discovery roster and every claim stops at it; Fold B, DEV-1000 and the test split stay
  untouched and unread; and under owner decision 28 these are development numbers, never comparable
  with a published TEST baseline.

## 11. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b8b-anchor-reviewer-audit-v1/`, outside the
repository so no receipt can dirty the tree the manifest reads at finalize.

| receipt | SHA-256 | what it proves |
| --- | --- | --- |
| `root-admission-v1.json` | `4891f994b8d499d79d2d8f2654b0e8325afca9eaa3758a86559b2c306da833a7` | the sealed root decision `slurp-b8b-anchor-reviewer-audit-admission-v1` that admitted the aborted arm; the resume's own receipt `root-admission-resume-v1.json` is the coordinator's to mint |
| `flight-lock-preserved-20260919T223435Z.json` | `17860a27b974fb3b4403a11a12f693a01d071a2498f103f698d72605cc8815b9` | the aborted attempt's `flight.lock`, moved rather than deleted |
| `flight-lock-reconciliation-20260919T223435Z.json` | `48c9018185d73792de97e3882edb19e206a344b89982869f6b0486e0879cc41d` | the coordinator's quiescence proof for the aborted flight: owner pid dead, 0 of 4 server slots processing, no flight or lease process, attempt `ABORTED` with 2,016 calls |
| `check-slurp-native-reviewer-audit-anchor-train-fold-a-v1-repin-20260919T125542Z.json` | `838f668fee9c767694b7870d22cfdfa62d20a8e5ee1920262f92509523211dae` | the aborted arm's own post-flip `core.flight.cli check` |
| `check-slurp-native-reviewer-audit-anchor-smoke-4-v1-repin-20260919T125311Z.json` | `0b80849376380f3693a77e573897e48e907b94dd155fcb82e691ca78c909a471` | the four-row smoke's post-flip `check` |

The trace itself is the resume's primary evidence and is pinned in the cell:
`runs/SAEA-…-TRAIN-FOLD-A-V1/attempt-…-generation-v1/SAEA-…-TRAIN-FOLD-A-V1.trace.jsonl`,
169,656,308 bytes, 13,282 records, SHA-256
`d495661dc7904eebb51818d4b35996a175de37af08d07ae56e904528fd6a84e3`, re-hashed and re-scanned on disk
by this registration. The aborted attempt's flight receipts
(`runs/…/attempt-…-generation-v1/flight-receipts.json`) carry its preflight `config_hash`
`04592f9515…`, `protocol_hash` `8b339a25…`, `sample_count` 1,080, `prepared_artifacts_ok` true and
the four `ALLOW` prompt-budget decisions.

**No `core.flight.cli check` receipt for the resume cell is on file, and that is deliberate.**
`FlightRuntime.preflight` asserts a clean study tree and reserves the attempt in the durable
`AttemptStore`; a registration agent that has not committed can neither pass the first nor is
entitled to the second. The composed and protocol hashes were computed directly through
`core.flight.repin.compute_cell_identity` — which composes exactly the four fragments the CLI
composes — and the method was verified against the aborted arm's sealed registered values. The
coordinator's re-pin cycle runs `check` on the clean registration commit and **asserts the
runtime-derived hashes equal the ones it has just written**; if they differ by one character, the
launch stops.
