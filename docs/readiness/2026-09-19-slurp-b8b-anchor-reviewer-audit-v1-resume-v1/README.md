# Cell B8b-anchor resume-recovery launch runbook

The registration note is
[`../2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-resume-v1.md`](../2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-resume-v1.md).
The sealed preregistration it addends is
[`../2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-preregistration.md`](../2026-09-19-slurp-b8b-anchor-reviewer-audit-v1-preregistration.md)
and is **never edited**; neither is the aborted registration's package
[`../2026-09-19-slurp-b8b-anchor-reviewer-audit-v1/`](../2026-09-19-slurp-b8b-anchor-reviewer-audit-v1/),
whose plan files keep their sealed hashes.

This directory holds:

| file | what it is |
| --- | --- |
| `README.md` | this runbook |
| `generation-plan-v1.json`, `generation-plan-registered-v1.json` | the registered generation `ExecutionPlan` (identical bytes; the ledger cites the `-registered-` copy) |
| `fit-plan-v1.json`, `fit-plan-registered-v1.json` | the registered native contact-fit `ExecutionPlan` |
| `protocol-registered-v1.json` | the resume protocol document: the aborted arm's protocol plus the resume facts and the one declared repair |
| `analysis-recipe-v1.json` | the paired-read recipe, unchanged except the run/attempt identities and the resume reading rule |

Everything in this package was produced with **zero model, tokenizer, encoder, ASR, scorer, server
and paid-API contacts**.

## 0. Why this package exists

Run `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` aborted at 2026-09-19T22:15Z after
**2,016** contacts on a harness defect with a named component: with the Reviewer slot-audit
attachment armed, 2 of 410 Reviewer visits spent all three ReAct iterations calling
`saea-tool-task-contract-v1` without producing an answer, and
`reproduction.ojw.native_episode._ApplyRole` raised `NativeEpisodeError` because the harness had no
disposition for ReAct exhaustion. Item **E22** gives it one
(`native_episode.react_exhaustion_policy = "continue-without-answer"`, merged at `6ecacc1b`); that
key is the single declared repair and renders no request byte. Owner decision 22 of 2026-09-18 makes
the one root-diagnosed recovery of such a flight a **resume-recovery**: 378 complete rows are kept
without selection, 702 rows are flown under the **same run id** and a new attempt id, and the merged
1,080-row manifest is scored once. Harness item E10 implements it.

## 1. What is registered

| item | value |
| --- | --- |
| experiment / cell | `slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume` |
| run id | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` — **unchanged; this is what a resume is** |
| generation attempt | `attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1-resume` |
| fit run / attempt | `SAEA-…-FIT-V1` (unchanged) / `attempt-…-fit-v1-resume` |
| `resume_from` | `{"attempt_id": "attempt-…-generation-v1", "trace_sha256": "d495661d…"}` |
| baseline | `configs/baseline/slurp-native-anchor-reviewer-audit-train-fold-a-v1-resume.json` |
| experiment | `configs/experiment/slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume.json` |
| campaign plan | `configs/campaign/slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume.json` |
| composed / protocol (pre-flip) | `1170659f0fcda16ee5f051b5be85fda869e2e986dc150a478dfc26bbcafe2ead` / `ffb4595b210aa3db754bb356f9573e9efc3830ab85c80d39ad4dea438ac325db` |
| readiness | `held`, `preparation` requirement only; the coordinator pins the decision receipt and flips |
| decision | `slurp-b8b-anchor-reviewer-audit-resume-admission-v1`, receipt `coordination/slurp-b8b-anchor-reviewer-audit-v1/root-admission-resume-v1.json` — **the coordinator mints it** |
| rows kept / flown | 378 / 702 (700 never started, 2 partial) |
| budget | run-cumulative: 2,016 spent + 7,722 worst case = 9,738 ≤ 11,880 |

The model, dataset, roster, split identity, both knowledge stores, the policy, the whole native
episode including the one factor `native_episode.reviewer_audit`, every instruction template,
`phase_tools`, the scorers, the resident geometry and both speech-feature identity strings are the
aborted arm's, byte for byte. The only behavioural change is the declared
`react_exhaustion_policy`. The committed proof is
`tests/unit/test_b8b_anchor_reviewer_audit_resume_config.py`.

## 2. The launch step: `scripts/flights/repin_cell.py`

Shell prelude used by every command below:

```bash
export REPO=<the clean detached worktree carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"
cd "$REPO"
```

**The coordinator mints the decision receipt first** — this package deliberately does not, because a
registration agent has no admission authority. Write it to
`$DATA/coordination/slurp-b8b-anchor-reviewer-audit-v1/root-admission-resume-v1.json` in the same
shape `root-admission-v1.json` uses, with decision id
**`slurp-b8b-anchor-reviewer-audit-resume-admission-v1`**.

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

`--preregistration` points at the **resume note**, not at the sealed preregistration. The tool
re-verifies the prepared artifact, applies the decision requirement, flips readiness, recomputes both
hashes, rewrites this README, the resume note, both plan pairs, the protocol document and the
analysis recipe, then runs `core.flight.cli check` and asserts the runtime-derived hashes agree.
**One cell per package invocation**: this package holds exactly one cell's plans, so nothing of the
aborted registration is rewritten.

**Expect the prepared artifact to be rebuilt.** `core.preparation.artifact_inputs` binds the composed
values including the cell and attempt identities, so the inherited `phase-supply-v1.json` pin will
not verify against this cell's digest. The tool detects that, rebuilds model-free into the next
`phase-supply-v*.json` under the same run id, asserts the new `output` equals the old one and re-pins
it. **`--allow-output-change` must never be given here**: if the prepared artifact's `output_sha256`
stops being `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`, the knowledge
channel moved and the resume is no longer a resume — **stop and report**.

Commit the result before launching.

## 3. Pre-launch checklist

1. **The ledger precondition, which is specific to a resume.** Both exposure rows of this run must
   read `consumed = no`: `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` (ledger line
   4832) and `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-FIT-V1` (line 4833). They read
   `no` as this package is registered and this registration did not touch them; confirm nothing has
   closed them since. `core.flight.repin.assert_rows_available` refuses the re-pin on the generation
   row and `FlightRuntime._require_exposure_row_unconsumed` refuses the flight on either.
2. One experiment in flight. No other campaign is running.
3. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a
   COMPLETED manifest reads `study_commit` at finalize. Fly from a clean detached worktree pinned at
   the admitted commit. No receipt from this preparation lives inside the repository.
4. **The predecessor attempt's directory is untouched and its trace still hashes to the declared
   value.** The resume refuses otherwise, before any contact — which is the point — but check it
   first so the refusal is not the first you hear of it:
   ```bash
   sha256sum "$DATA/runs/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1/attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1.trace.jsonl"
   # d495661dc7904eebb51818d4b35996a175de37af08d07ae56e904528fd6a84e3
   ```
   Never write, move, rename or compress anything under that attempt directory, and never delete a
   request-fit receipt under `prepared/SAEA-…-FIT-V1/attempt-…-fit-v1/`.
5. No flight process is running and **no `locks/flight.lock` is held in the data root** — the aborted
   attempt's lock was moved to
   `coordination/slurp-b8b-anchor-reviewer-audit-v1/flight-lock-preserved-20260919T223435Z.json` and
   reconciled by `…/flight-lock-reconciliation-20260919T223435Z.json` (SHA-256
   `48c9018185d73792de97e3882edb19e206a344b89982869f6b0486e0879cc41d`). Confirm it has not come back.
6. **The campaign runs as a Windows Scheduled Task owned by the machine, not by a chat session**,
   with the battery and idle conditions disabled and no execution time limit — verify with
   `schtasks /query /tn <task> /xml` and read
   `<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>`,
   `<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>`, `<IdleSettings>` disabled and
   `<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>`. Do not run `powercfg` while a campaign is in
   flight, and confirm the serving wrapper is alive before launching.
7. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`. Attach only, never spawn or stop.
8. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
9. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
10. Do **not** re-run `derived_media_confinement_check.py` from inside the checkout: it rewrites
    `docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
    dirty the tree the manifest reads at finalize.
11. The **prompt-budget blocker of the aborted package's section 2.1 is cleared** and recorded as
    cleared: the operational reserve is the live slot's one eighth (3,072 of 24,576), and the aborted
    attempt's own preflight receipt records `ALLOW` on all four phases. The resume adds no prompt
    byte, so the same four `ALLOW` decisions are expected.

A contact-free `check` can be re-run at any time on a clean tree:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume \
  --cell slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume
```

Its preflight receipt carries a `resume` block: the predecessor trace path and SHA-256, the
kept/flown/partial/unstarted counts, `worst_case_contacts` (7,722), the two partial sample ids and
the recorded reason each is being re-flown. **Read those counts before launching**: kept 378, flown
702, partial 2, unstarted 700, roster 1,080. `generation_authorized` is always `false`. Note that
`check` reserves the attempt in the durable `AttemptStore`, which is why this registration did not
run it — a second `check` after the re-pin's own would need a fresh attempt id, so do not run it
twice.

## 4. No smoke, and why

None is registered and none is needed. Cell B8b-anchor's own four-row smoke
`SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1` sealed the structural form of this episode and
is closed; **the aborted attempt itself realized that form 2,016 times on this roster**, with 6,048
request-fit receipts all fitting, `ALLOW` on all four phases and three length-capped Reviewer
completions retained by the E13 policy. The failure was not a form failure. The new surface is the
harness path — E10's resume and E22's disposition — and both are covered by their own committed
tests, plus `tests/unit/test_b8b_anchor_reviewer_audit_resume_config.py` for this registration.

## 5. The campaign — the only contact step

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume.json" \
  --owner root-slurp-native-reviewer-audit-anchor-train-fold-a-v1-resume \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

There is **no resume flag**: `resume_from` is read from the committed experiment fragment, because
which rows a run keeps is registered, not typed at launch.

The campaign scans the predecessor trace at preflight (model-free, before the server is touched),
narrows the dispatch roster to the 702 rows that are not COMPLETE, fits each realized native request
inside generation, merges the 378 replayed rows with the 702 live ones at the seal through the one
`_canonical_output_rows` stage, writes the `predecessor_attempt` block into the manifest, and
schedules the single official score of the complete 1,080-row manifest at finalize through
`core.scoring_batch`. **Do not run `coordinate-fit`**: the native gate fits every request itself, and
a standalone fit would double-charge the FIT row.

Expected: about **3,520 contacts** (702 rows at the sealed anchor's realized 5.016 per row), about
**2.4 GPU hours**, and about 14,100 FIT endpoints, plus the official scoring pass on the full 1,080
rows. Ceilings are run-cumulative and are bounds, not targets: 11,880 generation calls for the whole
run (2,016 already spent), 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive
GPU hours, 6,480 native task-contract calls. Nothing else may occupy the GPU while this flies.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy, utilisation and parked fraction for the lease window
from that file; they are mandatory verdict fields. A `0 %` utilisation reading with the model still
resident means a CPU-only step, not a hang.

**If the flight fails again**, cell B8b-anchor closes. No third registration, no second resume, no
row filtering: preserve everything, reconcile the lock, and report.

## 6. Post-flight

1. The manifest must be COMPLETED with exactly **1,080** ordered outputs and a `predecessor_attempt`
   block declaring trace SHA-256 `d495661d…`, kept-ids SHA-256
   `19b8b9e059d8a67bd83b8d7c72f86dc3d319617ea6fb123d32340faa91cfaccf` and counts
   `{kept: 378, flown: 702, partial: 2}`. `core.bundle.verify_bundle` must pass invariant **I7r**:
   every kept row held against the predecessor trace byte for byte, every flown row against this
   attempt's own, no sample in both.
2. **One** official score of the complete manifest through `core.scoring_batch`, never sharded, never
   re-run.
3. Run the paired read exactly as [`analysis-recipe-v1.json`](analysis-recipe-v1.json) pins it,
   against the sealed anchor's score artifact, under the decision rule of section 6 of the sealed
   preregistration.
4. **Never split the read on kept versus flown rows.** That partition is an arrival-order fact, not a
   property of the rows, and it is not a preregistered stratum.
5. Report the mandatory diagnostics, including **`react_exhaustion_rows` and
   `react_exhaustion_visits`** and the count of `finite_completion` rows, and say explicitly, in the
   verdict, **which rows were resumed rather than re-flown** and what the run-cumulative contact
   total was (predecessor 2,016 + this attempt).
6. Verdict: `docs/results/2026-09-19-slurp-b8b-anchor-reviewer-audit-verdict.md`.
7. Close both exposure rows at the merged seal with the realized actuals, appending rather than
   replacing their existing text, and run `engineering_base_check`, `harness_admission_check`,
   `results_ledger_check`, `finite_completion_policy_check` and `tool_catalog_check`.

## 7. Deviations the coordinator should know about

1. **A sibling baseline fragment exists.** The runtime requires it: `native_contact_fit` lives in the
   baseline, a fresh FIT **attempt** id is mandatory (the predecessor fit attempt already holds 6,048
   receipts, the two partial rows' among them, and the fit gate refuses an existing receipt path),
   and `core.config.compose` refuses a key defined by two fragments. Editing the aborted arm's
   baseline in place would retroactively move a closed registration's composed hash. The sibling
   differs from the aborted baseline **as it stands on master** in exactly
   `native_contact_fit.attempt_id` and `what_this_is`, and from the baseline the aborted attempt
   **actually flew** (study commit `c905ddf0`) in those two plus
   `native_episode.react_exhaustion_policy`, which item E22 armed on master at `97e90a9b`.
2. **The FIT run id and both exposure rows are reused, not replaced**, so this package adds no ledger
   row and does not edit `docs/exposure-ledger.md` at all.
3. **The two speech-feature identity strings are HELD.** A resume must not move them: they ride the
   audited payload as ORG/CONTROL provenance and the 378 kept rows already carry the predecessor's
   values.
4. **`prepare-supply` was not run by this registration.** The inherited pin is therefore expected to
   mismatch; section 2 says what the tool does about it.
5. **No `core.flight.cli check` receipt for this cell.** It reserves the attempt id; a registration
   agent is not entitled to spend one. The hashes were computed through
   `core.flight.repin.compute_cell_identity`, and the method was verified by reproducing the aborted
   arm's sealed registered `04592f95…` / `8b339a25…` from its fragments **at the flight commit
   `c905ddf0`**, where `react_exhaustion_policy` was still absent.
