# Cell B4b-rep: the one root-diagnosed recovery, as a RESUME-RECOVERY, registered before contact

Status: **REGISTERED BEFORE CONTACT.** Author: the B4b replicate resume-recovery registration agent,
main checkout `studies/speech-aware-evidence-acquisition`, branch `master`, base commit `7effe819`
(which carries harness item E10, merged at `f79eaf79`).

This note is the **addendum** to
[`2026-09-17-slurp-b4b-replicate-v2-preregistration.md`](2026-09-17-slurp-b4b-replicate-v2-preregistration.md),
whose bytes are pinned by the sealed root decision `slurp-b4b-replicate-admission-v1` and are
therefore **not edited**. Everything that document says about the question, the arms, the single
factor, the metrics, the resampling, the STOP condition, the decision rule, the cost reporting, the
prompt fit and what is not claimed stands unchanged. Section 10 of the preregistration allows *at
most one root-diagnosed recovery re-registration per run*. **This is it**, taken in the
**resume-recovery** form owner decision 22 of 2026-09-18 requires. It is the **first use of harness
item E10**.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried; the 1,080-row campaign
flying from its pinned worktree was never touched; no run directory, attempt record or prepared
artifact was written, moved or renamed (the aborted attempt's trace, attempt record and fit receipts
were read, read-only); `locks/flight.lock` was never held; no scheduled task was touched.

## 1. What happened

Run `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2`, attempt
`attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2`, flown from the
worktree at study commit `2fdede26`, **ABORTED at 2026-09-18T02:40:20Z** after **2,922** generation
contacts and **7,895.544875000081** repeated speech seconds. The recorded failure is, verbatim from
`attempts/SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2/attempt-…-replicate-generation-v2.json`:

```
generation failed during run_phases or seal: NativeEpisodeError: native episode node failed:
[100054] component 'reviewer_0_role' execute 'invoke' error, reason='Remote end closed connection
without response', workflow='5024c2ed5a7b4686a1db2cd9f61c9787'
```

The mechanism, in one sentence: **the inherited resident llama-server and its serving wrapper died
with the ChatGPT session that owned them** (owner-confirmed; the stop receipt reads `ALREADY_EXITED`,
there was no OOM and no host memory pressure), and the next Reviewer contact found a closed socket.

**It was not the harness, the config, the model, the roster or the host.** There was no harness error
and no configuration error; the request bytes already transmitted were the registered ones; the
flight worktree was clean at `2fdede26`. This is exactly the class of failure a resume-recovery
applies to: **an infrastructure failure with code and request bytes unchanged.** The fix is outside
this repository and is already in force — the serving wrapper, the monitor and every campaign now run
as Windows Scheduled Tasks owned by the machine rather than by a chat session (owner decision 24),
and the coordinator's own session owns the wrapper it starts.

## 2. What was spent, and what is preserved

| item | value |
| --- | --- |
| attempt state | `ABORTED` |
| generation calls | 2,922 |
| repeated speech seconds | 7,895.544875000081 |
| trace | `runs/SAEA-…-REPLICATE-V2/attempt-…-replicate-generation-v2/SAEA-…-REPLICATE-V2.trace.jsonl`, 202,733,292 bytes, 16,338 records, SHA-256 `ad7a78c77c26b8c7255e31fa897678b23609c9578933425b679594831e17c897` |
| rows with requests | 584 |
| rows COMPLETE (terminal episode receipt, every response recorded) | **580** |
| rows INCOMPLETE | **4** |
| rows never started | 496 |
| request-fit receipts | 8,766 files under `prepared/SAEA-…-FIT-REPLICATE-V2/attempt-…-fit-replicate-v2/`, every request fitting |
| flight lock | preserved and then reconciled by root: `coordination/slurp-b4b-replicate-v2/flight-lock-preserved-20260918T032333Z.json` (SHA-256 `7a4c99efddc972d22a9b139b7c947e1619e3656b4e9c90e8d0f120b6ef2f5399`) and `…/flight-lock-reconciliation-20260918T032333Z.json` (SHA-256 `bc3874ae43ec05fb5655bf345f54c92b62575c28e0bc388b176664648ecc5a8d`) |
| score | none. No official scoring job ran and **no partial quality read was taken or is permitted** |

Everything above is **read-only**. Nothing under `runs/`, `attempts/` or `prepared/` was modified by
this registration. The run's two exposure rows —
`SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2` and
`…-FIT-REPLICATE-V2` — were closed at `consumed = yes` on 2026-09-18 with the abort actuals and are
**REOPENED to `consumed = no` by this registration**, because a resume flies under the same run id
and both the re-pin tool (`core.flight.repin.assert_rows_available`) and the fit gate
(`FlightRuntime._require_exposure_row_unconsumed`) refuse a consumed row. Their existing text is
untouched; one sentence is appended to each. **No new ledger row is added, and the run id and the
predecessor attempt id are never reused as this attempt's own identities.**

## 3. The resume: mode A, what is kept and what is flown

Harness item E10 implements **mode A — trace replay plus seal-time merge**
(`core.flight.resume`; the four modes and the choice are compared in
`docs/superpowers/specs/2026-09-18-resume-modes-comparison.md`, owner decision 24). The recovery cell
declares, in its committed experiment fragment and nowhere else — there is deliberately no
command-line flag:

```json
"resume_from": {
  "attempt_id": "attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2",
  "trace_sha256": "ad7a78c77c26b8c7255e31fa897678b23609c9578933425b679594831e17c897"
}
```

`FlightRuntime.preflight` scans that trace **model-free, before any server exists**, and refuses if
the bytes do not hash to the declared value, if the predecessor flew a row outside this flight's
roster, or if every row is already complete. The scan of 2026-09-18, re-run by this registration on
the bytes on disk, reports:

| quantity | value |
| --- | --- |
| trace SHA-256 re-hashed on disk | `ad7a78c77c26b8c7255e31fa897678b23609c9578933425b679594831e17c897` (matches the declaration) |
| contacts in the trace | 2,922 |
| rows with requests | 584 |
| **COMPLETE, kept without selection** | **580** |
| **INCOMPLETE, re-flown in full** | **4** |
| never started, flown | 496 |
| **rows this attempt flies** | **500** |
| roster | 1,080 |
| sorted kept-sample-id SHA-256 | `45e9eeb3a80c2b448cd7eb3922de4c000e22c2f188448c786de6f0a076916049` |

The four partial rows, by id, each for the same recorded reason — *the episode emitted no terminal
receipt*:

- `slurp:train:008363:audio-1502300356-headset`
- `slurp:train:008450:audio-1490199694`
- `slurp:train:008472:audio-1499690693`
- `slurp:train:008505:audio-1490195977`

**Completeness is the episode's own terminal receipt, never a contact count.** A request-count read
alone would report 577 complete and 7 partial; three short rows finished their episode in fewer than
five contacts. The replay classifies delivery with the same validator the seal uses
(`rails.native_episode_receipt.validate_native_episode_delivery_receipt`, in its documented post-seal
reader mode) and checks every contact the receipt names against the recorded request and response
digests.

**No selection is possible anywhere in this path.** The kept set is exactly the predecessor's
COMPLETE rows and the flown set is exactly the rest of the registered roster; `core.flight.resume`
raises rather than honour any other partition. The seal renders kept and flown rows through the one
`_canonical_output_rows` stage, so a kept row is byte-identical to the row the aborted attempt would
have sealed; the manifest declares `predecessor_attempt` (trace SHA-256, the sorted kept ids and
their hash, the kept/flown/partial counts); `core.bundle.verify_bundle` holds every kept row against
the predecessor trace byte for byte under invariant **I7r**; and the complete 1,080-row manifest is
scored **once**.

## 4. Why nothing in the science changes

The failure is an infrastructure failure of the process that hosted the flight. It is not a roster,
prompt, knowledge, retrieval, budget, geometry or scoring defect, and it gives no information about
the question cell B4b-rep asks. So:

- **no roster or split change.** The same 1,080-row TRAIN Fold A roster, the same
  `SLURP-EVO-FOLD-A-V2`, the same split identity
  `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, the same ordered ids. Fold B is
  absent and untouched.
- **no module, prompt, role-graph, geometry or cap change.** Both knowledge stores at
  `intent-boundaries-v1` and `slot-contracts-v2` (release `f8e42d4f…` / snapshot `d5992bd1…`), the
  arm `speech-feature-query-native-tools`, the policy `phase-native-candidates-review-revise-v1`, the
  full native episode with the review loop on (`max_revisions` 1, reviewer `max_iterations` 3,
  program ceiling 11 contacts), the candidate contract, the Perception retrieval geometry, every
  instruction template, the `phase_tools` block, the scorers, the model fragment (temperature 0, seed
  20260913, `max_tokens` 512), the promoted EVO-FOLDS-V2 packets and the resident session
  `serving-slurp-native-candidate-five-train-a-np4-v1` are byte-identical to the aborted arm's.
- **the two WAVE R7 speech-feature identity strings are HELD**, not minted fresh. Cell B4b-rep minted
  its own against cell B4b (preregistration section 3.5); a *resume* must not, because those strings
  ride the audited payload as ORG/CONTROL provenance and the 580 kept rows already carry the aborted
  attempt's values. A merged manifest whose kept and flown rows disagreed about them would be
  internally inconsistent for no gain.
- **no decision-rule change.** The three clauses, the −1.0051 intent margin, the projection-v3 sign
  agreement, the own-null definition, the paired whole-speaker cluster bootstrap (10,000 draws, seed
  20260915), the CI levels, the STOP condition on reproducing `+1.1294` and `−0.7117`, and the
  mandatory tables are exactly as preregistered.
- **no comparator change.** The sealed dual-store anchor
  `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` is the clause leg, the sealed cell
  B4b arm `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2` is the own-null leg, and the
  released direct anchor `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1` is the secondary
  system-versus-direct column. All three are sealed bytes; none is re-flown or re-scored.

What *does* change is bookkeeping only, in **eight of the sixty-six composed keys**, and none of them
is model-facing: the cell and attempt identities and the `resume_from` declaration (`cells`), the
native-fit attempt id (`native_contact_fit`), the registration date (`date`), the fragment name
(`fragment_kind`), and four free-English fields (`purpose`, `failure_policy`, the
`generation_budget.definition`, and the baseline's `what_this_is`). The other **58** — including
`knowledge_stores`, `policy`, `native_episode`, `phase_material`, `phase_tools`,
`prepared_phase_supply`, `scorers`, both speech-feature identity strings, every instruction template,
`populations`, `population`, `split_id`, `family_budget`, `execution_plan` and `service_session` —
are byte-identical. The committed proof is `tests/unit/test_b4b_replicate_resume_config.py`.

### 4.1 The one runtime-forced identity: a fresh native-fit ATTEMPT

`native_contact_fit.attempt_id` moves to
`attempt-slurp-native-slot-store-v2-anchor-train-fold-a-fit-replicate-v2-resume2`. The **FIT run id
does not move**, and neither does `contact_cap`.

This is required by the runtime, not chosen. `core.preparation_fit.build_native_contact_fit_gate`
writes one request-fit receipt per realized contact to
`prepared/<fit run>/<fit attempt>/<sha256 of {sample_id, agent_contact_id}>.request-fit.json` and
**refuses a path that already exists** (`native contact fit identity already has contact or result
evidence`). `agent_contact_id` is the deterministic `<program>:<phase>:<iteration>:<sample id>`, so a
re-flown partial row re-mints the exact contact ids it used before. All four partial rows already
carry `perception:0` and `solver:0` receipts under the predecessor fit attempt — verified read-only
on disk by this registration — so re-flying them under that attempt would refuse at the first
contact and abort the whole flight. The fit root is namespaced by run **and** attempt, so a fresh
attempt id under the unchanged fit run id is the minimum change that clears it, and it keeps the
run's exposure accounting on its existing two ledger rows rather than opening a third.

`contact_cap` stays **47,520** = 1,080 registered rows × 11 contacts × (1 speech packet + 3
endpoints). The gate derives the required cap from the whole registered roster, not from the flown
subset, and refuses any other value.

Because `native_contact_fit` lives in the baseline fragment and `core.config.compose` refuses a key
defined by two fragments, this one field forces a sibling **baseline fragment**,
`configs/baseline/slurp-native-anchor-slot-store-v2-train-fold-a-replicate-v2-resume.json`. It is the
aborted arm's baseline byte for byte except that one key and its `what_this_is` prose. Editing the
aborted arm's own baseline in place was rejected: it would retroactively move the closed
registration's composed hash.

## 5. Budget: run-cumulative, and the arithmetic

A resumed attempt and its predecessor **share one run id**, so exposure accounting is run-cumulative
across attempts — `core.attempts.AttemptStore.prior_actual_usage` sums the actual calls and audio
seconds of every attempt file under the run id and the gate holds that sum against
`planned_model_calls` (invariants I3/I6).

| term | value |
| --- | ---: |
| predecessor attempt, durably spent | 2,922 |
| this attempt's worst case: 500 flown rows × 11 contacts (the program ceiling) | 5,500 |
| **run-cumulative worst case** | **8,422** |
| registered `planned_model_calls` (unchanged) | 11,880 |
| headroom | 3,458 |

`FlightRuntime.preflight` reports the same 5,500 as `resume.worst_case_contacts`, beside the
kept/flown/partial counts and the per-row reasons, and it reports it rather than reconciling it: the
number the plan declares is the owner's, not the stage's. Every other ceiling is the aborted arm's,
unchanged and still a bound rather than a target: 47,520 FIT endpoints, 33,930 repeated speech
seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score,
zero ASR, encoder and paid-API calls.

Expect the resume itself to realize about **2,500 contacts**, about **7,500 repeated speech seconds**
and about **1.6 GPU hours**: cell B4b realized 5,407 contacts on 1,080 rows (5.006 per row) in
12,796.8 s, and this attempt flies 500 of them. That is what the resume buys: **2,922 of the run's
roughly 5,400 contacts never have to be paid again**, and the ~3.5-GPU-hour re-fly becomes a
~1.6-GPU-hour completion.

## 6. No smoke, and why

**No four-row smoke is registered, and none is needed.** The form is proved three times over on this
exact configuration:

- cell B4b's own four-row smoke `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2` sealed the
  structural form of this episode (composed `c0572352…`, protocol `f13ba493…`, COMPLETED, 20
  contacts, 20 request fits, all fitting);
- the preregistration proved, row for row before any contact, that cell B4b-rep's rendered request is
  byte-identical to cell B4b's on all 1,080 rows and all four declared phases, in three pairings,
  with a rendered byte delta of exactly 0 and 0 identity-string hits in 12,960 scanned envelopes; and
- **the aborted attempt itself realized that form 2,922 times on this roster**, with 2,922
  request-fit receipts, every request fitting, before the server died. Those sealed contacts are the
  strongest form evidence this cell can have, and they are the very bytes the resume keeps.

The failure was not a form failure, and the resume changes nothing a smoke could test. What is new is
the *harness path*, and that is covered by E10's own committed tests, which fly the real native
episode graph twice against a fake model — uninterrupted, and aborted-then-resumed — and compare the
kept rows byte for byte, for a nominal episode, an episode with an executed revision, a partial row
and an unstarted row, plus six refused tamperings of the merged manifest and a read-only contract
test over **this** aborted attempt. Registering a smoke would spend contacts to re-prove a proved
form, and — worse — would put four rows of this roster through an extra batch composition before the
measurement this cell exists to make.

## 7. Failure rule, restated

This registration **is** the one root-diagnosed recovery re-registration the preregistration allows
for this run. A second failure **closes cell B4b-rep**: no third registration, no second resume, no
replay, no row filtering, no roster, role-graph, prompt, geometry or cap change, and the fix must be
proven on a four-row dry run before another mechanism is admitted. A partial manifest is never scored
and never read. One experiment in flight at a time.

Owner decision 22 also makes checkpoint resume a **standing rule**: every experiment registered from
now on must support it, and every new preregistration's failure rule carries the resume-recovery
clause — its one recovery is a `resume_from` resume when the abort was an infrastructure failure with
code and request bytes unchanged, and a full re-fly otherwise.

## 8. The recovery cell

| item | value |
| --- | --- |
| cell / experiment fragment | `slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume` |
| generation run / attempt | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2` (**unchanged**) / `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2-resume2` |
| native fit run / attempt | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-REPLICATE-V2` (**unchanged**) / `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-fit-replicate-v2-resume2` |
| model fragment | `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` (**unchanged**) |
| dataset fragment | `slurp-speech-native-evo-fold-a-1080` (**unchanged**) |
| baseline fragment | `slurp-native-anchor-slot-store-v2-train-fold-a-replicate-v2-resume` |
| campaign plan | `configs/campaign/slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume.json` |
| composed config / protocol | `a2d986c893923e25472e0ec775ebf3ffce905cb4edb1935c44efab13b40a7950` / `df67e8e1192aefa3a9ff7292625b7fa6bfbaa754aa4bcb2737466b4eb435ef0c` |
| prepared phase supply | inherited pin `prepared/SAEA-…-REPLICATE-V2/phase-supply-v2.json`, SHA-256 `ac501ceef5cd31047ec239843afdb3834f774c72c5f686d8786b90ede184da00`, **output** SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`; the re-pin cycle rebuilds it as `phase-supply-v3.json` (see below) |
| budgets | 11,880 generation calls (**run-cumulative**), 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score — cell B4b's own ceilings, unchanged |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| plans | `docs/readiness/2026-09-18-slurp-b4b-replicate-v2-resume-v1/` — the generation and FIT plan pairs, the resume protocol document, the analysis recipe and the runbook |
| readiness | `held` with the `preparation` requirement pinned and **no decision requirement**; the coordinator adds the `decision` requirement and flips with `scripts/flights/repin_cell.py` |
| decision | id `slurp-b4b-replicate-resume-admission-v1`, receipt `coordination/slurp-b4b-replicate-v2/root-admission-resume-v1.json` — **the coordinator mints it**; this package deliberately does not |
| supersedes | attempt `attempt-…-replicate-generation-v2` (ABORTED) and fit attempt `attempt-…-fit-replicate-v2`; the **run ids are kept**, because that is what a resume is |

**The composed and protocol hashes above are the pre-flip values** of the four fragments exactly as
committed: readiness `held`, the `preparation` requirement pinned, `prepared_phase_supply` inherited,
no `decision` requirement. `compose()` hashes the complete merged fragment set, so adding the
decision requirement and flipping readiness each change both. The re-pin tool recomputes them and
rewrites every document that quotes them; nobody edits them by hand. The method was verified twice on
this checkout against sealed registered values: the same `compose()` / `protocol_hash()` call
reproduces the aborted arm's registered `658c568f…` / `b8143a5d…` and cell B4b's own registered
`8d207b33…` / `567a87ad…`.

**The prepared Perception supply does not move, but its FILE must be rebuilt.**
`core.preparation.artifact_inputs` binds the composed values — the cell and attempt identities
included — so the inherited pin will not verify against the resume cell's composed digest. That is
expected and is handled by the launch step: `core.flight.repin.ensure_artifact_pinned` detects
exactly that mismatch, rebuilds the artifact model-free into
`prepared/SAEA-…-REPLICATE-V2/phase-supply-v3.json`, **asserts its `output` equals the previous
artifact's**, and re-pins it in the same cycle. This registration deliberately does not run
`prepare-supply` itself: a 1,080-row campaign was in flight on the GPU and the re-pin cycle does the
same work, once, with the assertion attached. **`--allow-output-change` must never be given**: an
output that moved would mean the knowledge channel moved, and the resume would no longer be a resume.

## 9. Launch

The runbook is [`2026-09-18-slurp-b4b-replicate-v2-resume-v1/README.md`](2026-09-18-slurp-b4b-replicate-v2-resume-v1/README.md),
sections 2, 3 and 5. The ledger precondition is item 1 of its checklist: **both** exposure rows of
this run must read `consumed = no`.

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume \
    --cell slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume \
  --readiness-dir docs/readiness/2026-09-18-slurp-b4b-replicate-v2-resume-v1 \
  --preregistration docs/readiness/2026-09-18-slurp-b4b-replicate-v2-resume-v1.md \
  --package-name slurp-b4b-replicate-v2 \
  --decision coordination/slurp-b4b-replicate-v2/root-admission-resume-v1.json \
  --decision-id slurp-b4b-replicate-resume-admission-v1 \
  --set-ready
```

Then the campaign, over
`configs/campaign/slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume.json`, launched
as a Windows Scheduled Task with the battery and idle conditions disabled and no execution time
limit.

`--preregistration` points at **this note**, not at the sealed preregistration, whose bytes the
original decision receipt pinned and which must not be rewritten. The re-pin tool rewrites this note,
the resume plan directory and the two reopened ledger rows' notes; it does **not** touch the
preregistration or the aborted registration's package, whose plan files keep their sealed hashes, and
it refuses if the generation run's exposure row is still `consumed = yes`.

## 10. What is NOT claimed

- **Nothing about task quality.** The predecessor attempt's 2,922 contacts were never scored and
  never read; no partial read is permitted; the 580 rows it completed reach a number only through the
  one official score of the complete merged manifest.
- **No sub-population claim about kept versus flown rows.** Which rows the predecessor happened to
  finish before the server died is an arrival-order fact, not a property of the rows. Kept and flown
  rows are never separated, compared or reported as strata; the read is of one complete 1,080-row
  manifest, exactly as preregistered.
- **No claim that a resumed pass is a *cleaner* replicate than a re-flown one.** It is the same
  replicate: 580 rows keep the batch composition they were drawn under and 500 rows are drawn under a
  new one. The single factor the cell measures — batch composition under greedy decoding — is
  unchanged in kind, and this note makes no claim that it is unchanged in magnitude.
- **No re-litigation of the cell's own claims.** Everything the preregistration says — the three
  replication conjuncts, the own null of the admitted configuration as an *output*, the consequence
  clause, the mandatory tables, the symmetric-scorer clause and the whole section-11 list — stands
  unchanged and is not restated here.
- **No claim that the infrastructure fix is proved by this package.** It is a process-ownership and
  scheduled-task change on the host (owner decision 24), verified by the pre-launch checklist rather
  than by a test in this repository.
- **Meeting clause 1 on this pass is still not a paper claim.** A REPLICATED verdict admits the v2
  pins into the SLURP default plan; Stage-3 claims belong to a separately admitted paper repository.

## 11. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b4b-replicate-v2/`, outside the repository so no
receipt can dirty the tree the manifest reads at finalize.

| receipt | what it proves |
| --- | --- |
| `root-admission-v1.json` (SHA-256 `75edd7591a9d79ad49aae339064eaaedbc6470caeb6424fd3ebd9fba2f9f0eeb`) | the sealed root decision `slurp-b4b-replicate-admission-v1` that admitted the aborted arm; the resume's own receipt `root-admission-resume-v1.json` is the coordinator's to mint |
| `flight-lock-preserved-20260918T032333Z.json` (SHA-256 `7a4c99efddc972d22a9b139b7c947e1619e3656b4e9c90e8d0f120b6ef2f5399`) | the aborted attempt's `flight.lock`, moved rather than deleted |
| `flight-lock-reconciliation-20260918T032333Z.json` (SHA-256 `bc3874ae43ec05fb5655bf345f54c92b62575c28e0bc388b176664648ecc5a8d`) | root's quiescence proof for the aborted flight |
| `request-envelope-comparison-v1.json` (SHA-256 `05b54c73efcab569652bb6877a836b619b533dcdfaeb57d643661a8f710bf88d`) | the aborted registration's own proof, still authoritative: byte-identical rendered requests on 1,080 rows × 4 phases in three pairings, 0 identity-string hits in 12,960 envelopes |
| `phase-supply-vs-b4b-and-anchor-v1.json` (SHA-256 `7733fdb895e834e9cb243bf67ec28bea4a2619de5a07c5203cddf0f3b128053c`) | the prepared supply selects what cell B4b and the sealed anchor selected on 1,080/1,080 rows, all three sharing the output digest `ba5e1faa…` |
| `composed-hashes-v1.json` (SHA-256 `7fdd6e2017123450a4ef1a5e038ac20fdbc6e7dee90808c4e45dce7d146cb376`) | the aborted registration's hash-method verification against cell B4b's and the anchor's registered values |
| `check-replicate-ready-v1.json` (SHA-256 `9f535a923640bfa10607dc7f0665247565d1548efaad3f6c85a56a160d12418b`) | the aborted arm's post-flip `core.flight.cli check` |

The trace itself is the resume's primary evidence and is pinned in the cell:
`runs/SAEA-…-REPLICATE-V2/attempt-…-replicate-generation-v2/SAEA-…-REPLICATE-V2.trace.jsonl`,
202,733,292 bytes, SHA-256 `ad7a78c77c26b8c7255e31fa897678b23609c9578933425b679594831e17c897`,
re-hashed on disk by this registration.

**No `core.flight.cli check` receipt for the resume cell is on file, and that is deliberate.**
`FlightRuntime.preflight` asserts a clean study tree and reserves the attempt in the durable
`AttemptStore`; a registration agent that has not committed can neither pass the first nor is
entitled to the second. The composed and protocol hashes were computed directly through
`core.config.compose` / `core.config.protocol_hash` — the same two functions `check` itself uses —
and the method was verified twice against sealed, registered values. The coordinator's re-pin cycle
runs `check` on the clean registration commit and **asserts the runtime-derived hashes equal the ones
it has just written**; if they differ by one character, the launch stops.

## Second attempt id (2026-09-18, coordinator)

The first resume attempt, `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2-resume`, passed preflight (resume block: kept 580, flown 500,
partial 4, unstarted 496, worst case 5,500 contacts), preprocess and serve, and aborted in
`run_phases` with ZERO contacts on `PreparationError: prepared artifact identity mismatch`: the
phase-supply artifact identity embeds the full-roster packet map and E10 narrowed the map to the
flown rows before the identity was computed. Fixed by E10b (identities over the whole roster,
selections restricted after the load) and E10c (the runner takes an explicit `flown_sample_ids`
roster; `planned_ceiling` = 500 x 11), merged at `b6f1b045` with a fake-model test that drives the
real dispatch path. The zero-contact attempt consumed nothing; its flight lock was reconciled with a
quiescence receipt under `coordination/slurp-b4b-replicate-v2/`. This package now registers the
second attempt ids `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2-resume2` and `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-fit-replicate-v2-resume2`; everything else is unchanged. The
run-cumulative budget stays 2,922 + 5,500 = 8,422 within 11,880.
