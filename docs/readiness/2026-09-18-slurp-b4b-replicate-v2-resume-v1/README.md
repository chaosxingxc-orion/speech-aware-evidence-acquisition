# Cell B4b-rep resume-recovery launch runbook

The registration note is
[`../2026-09-18-slurp-b4b-replicate-v2-resume-v1.md`](../2026-09-18-slurp-b4b-replicate-v2-resume-v1.md).
The sealed preregistration it addends is
[`../2026-09-17-slurp-b4b-replicate-v2-preregistration.md`](../2026-09-17-slurp-b4b-replicate-v2-preregistration.md)
and is **never edited**.

This directory holds:

| file | what it is |
| --- | --- |
| `README.md` | this runbook |
| `generation-plan-v1.json`, `generation-plan-registered-v1.json` | the registered generation `ExecutionPlan` (identical bytes; the ledger cites the `-registered-` copy) |
| `fit-plan-v1.json`, `fit-plan-registered-v1.json` | the registered native contact-fit `ExecutionPlan` |
| `protocol-registered-v1.json` | the resume protocol document: the aborted arm's protocol plus the resume facts |
| `analysis-recipe-v1.json` | the paired-read recipe, unchanged except the arm this cell seals and the resume reading rule |

Everything in this package was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**.

## 0. Why this package exists

Run `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2` aborted at
2026-09-18T02:40:20Z after 2,922 contacts when the inherited resident llama-server died with the
session that owned it. Infrastructure failure; code, configuration and request bytes unchanged. Owner
decision 22 of 2026-09-18 makes the one root-diagnosed recovery of such a flight a
**resume-recovery**: 580 complete rows are kept without selection, 500 rows are flown under the
**same run id** and a new attempt id, the manifest declares its predecessor and the complete 1,080-row
manifest is scored once. Harness item E10 (merged at `f79eaf79`) implements it; **this is its first
use**.

## 1. What is registered

| item | value |
| --- | --- |
| experiment / cell | `slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume` |
| run id | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2` — **unchanged; this is what a resume is** |
| generation attempt | `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2-resume2` |
| fit run / attempt | `SAEA-…-FIT-REPLICATE-V2` (unchanged) / `attempt-…-fit-replicate-v2-resume` |
| `resume_from` | `{"attempt_id": "attempt-…-replicate-generation-v2", "trace_sha256": "ad7a78c7…"}` |
| baseline | `configs/baseline/slurp-native-anchor-slot-store-v2-train-fold-a-replicate-v2-resume.json` |
| experiment | `configs/experiment/slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume.json` |
| campaign plan | `configs/campaign/slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume.json` |
| composed / protocol (pre-flip) | `a2d986c893923e25472e0ec775ebf3ffce905cb4edb1935c44efab13b40a7950` / `df67e8e1192aefa3a9ff7292625b7fa6bfbaa754aa4bcb2737466b4eb435ef0c` |
| readiness | `held`, `preparation` requirement only; the coordinator pins the decision receipt and flips |
| decision | `slurp-b4b-replicate-resume-admission-v1`, receipt `coordination/slurp-b4b-replicate-v2/root-admission-resume-v1.json` — **the coordinator mints it** |
| rows kept / flown | 580 / 500 (496 never started, 4 partial) |
| budget | run-cumulative: 2,922 spent + 5,500 worst case = 8,422 ≤ 11,880 |

Model, dataset, roster, split identity, both knowledge stores, the policy, the native episode, every
instruction template, the scorers, the resident geometry and both speech-feature identity strings are
the aborted arm's, byte for byte. The committed proof is
`tests/unit/test_b4b_replicate_resume_config.py`.

## 2. The launch step: `core.flight.repin`

Shell prelude used by every command below:

```bash
export REPO=<the clean checkout or detached worktree carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"
cd "$REPO"
```

**The coordinator mints the decision receipt first** — this package deliberately does not, because a
registration agent has no admission authority. Write it to
`$DATA/coordination/slurp-b4b-replicate-v2/root-admission-resume-v1.json` in the same shape
`root-admission-v1.json` uses, with decision id **`slurp-b4b-replicate-resume-admission-v1`**.

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

`--preregistration` points at the **resume note**, not at the sealed preregistration, whose bytes the
original decision receipt pinned. The tool re-verifies the prepared artifact, applies the decision
requirement, flips readiness, recomputes both hashes, rewrites this README, the resume note, both
plan pairs, the protocol document and the reopened generation ledger row's notes, then runs
`core.flight.cli check` and asserts the runtime-derived hashes agree.

**Expect the prepared artifact to be rebuilt.** `core.preparation.artifact_inputs` binds the composed
values including the cell and attempt identities, so the inherited `phase-supply-v2.json` pin will
not verify against this cell's digest. The tool detects that, rebuilds model-free into
`prepared/SAEA-…-REPLICATE-V2/phase-supply-v3.json`, asserts the new `output` equals the old one and
re-pins it. **`--allow-output-change` must never be given here**: if the prepared artifact's
`output_sha256` stops being `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`, the
knowledge channel moved and the resume is no longer a resume — **stop and report**.

Commit the result before launching.

## 3. Pre-launch checklist

1. **The ledger precondition, which is specific to a resume.** Both exposure rows of this run must
   read `consumed = no`:
   `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2` and
   `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-REPLICATE-V2`. This registration reopened
   both; confirm nothing has closed them again.
   `core.flight.repin.assert_rows_available` refuses the re-pin on the generation row and
   `FlightRuntime._require_exposure_row_unconsumed` refuses the flight on either. Grep both ids in
   `docs/exposure-ledger.md` and read the `consumed` column.
2. One experiment in flight. No other campaign is running. In particular the B5e recovery campaign
   must have finished.
3. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a COMPLETED
   manifest reads `study_commit` at finalize. Fly from a clean tree pinned at the admitted commit. No
   receipt from this preparation lives inside the repository.
4. **The predecessor attempt's directory is untouched and its trace still hashes to the declared
   value.** The resume refuses otherwise, before any contact — which is the point — but check it
   first so the refusal is not the first you hear of it:
   ```bash
   sha256sum "$DATA/runs/SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2/attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2/SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2.trace.jsonl"
   # ad7a78c77c26b8c7255e31fa897678b23609c9578933425b679594831e17c897
   ```
   Never write, move, rename or compress anything under that attempt directory.
5. No flight process is running and **no `locks/flight.lock` is held in the data root** — the aborted
   attempt's lock was moved to
   `coordination/slurp-b4b-replicate-v2/flight-lock-preserved-20260918T032333Z.json` and reconciled
   by `…/flight-lock-reconciliation-20260918T032333Z.json` (SHA-256
   `bc3874ae43ec05fb5655bf345f54c92b62575c28e0bc388b176664648ecc5a8d`). Confirm it has not come back.
6. **The campaign runs as a Windows Scheduled Task owned by the machine, not by a chat session.**
   That is the fix for the failure that caused this recovery: the previous flight died with the
   session that owned its server. Register the task with the battery and idle conditions disabled and
   no execution time limit — verify with `schtasks /query /tn <task> /xml` and read
   `<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>`,
   `<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>`, `<IdleSettings>` disabled and
   `<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>`. Do not run `powercfg` while a campaign is in
   flight, and confirm `pgrep` shows the serving wrapper alive before launching.
7. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`. Attach only, never spawn.
8. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package closes
   the D3 gate.
9. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
10. Do **not** re-run `derived_media_confinement_check.py` from inside the checkout: it rewrites
    `docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
    dirty the tree the manifest reads at finalize.

A contact-free `check` can be re-run at any time on a clean tree:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume \
  --cell slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume
```

Its preflight receipt carries a `resume` block: the predecessor trace path and SHA-256, the
kept/flown/partial/unstarted counts, `worst_case_contacts` (5,500), the four partial sample ids and
the recorded reason each is being re-flown. **Read those counts before launching**: kept 580, flown
500, partial 4, unstarted 496, roster 1,080. `generation_authorized` is always `false`. Note that
`check` reserves the attempt in the durable `AttemptStore`, which is why this registration did not
run it — a second `check` after the re-pin's own must therefore use a fresh attempt id, so do not run
it twice.

## 4. No smoke, and why

None is registered and none is needed. Cell B4b's four-row smoke
`SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2` sealed the structural form of this episode; the
preregistration proved the rendered request byte-identical to cell B4b's on all 1,080 rows and four
phases before any contact; and **the aborted attempt itself realized that form 2,922 times on this
roster**, with a request-fit receipt for every contact, all fitting. The failure was not a form
failure. The new surface is the harness resume path, and that is covered by E10's own committed tests
(the real native episode graph flown twice against a fake model — uninterrupted and
aborted-then-resumed — with kept rows compared byte for byte, six refused manifest tamperings, and a
read-only contract test over this very attempt), plus
`tests/unit/test_b4b_replicate_resume_config.py` for this registration.

## 5. The campaign — the only contact step

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume.json" \
  --owner root-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2-resume \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

There is **no resume flag**: `resume_from` is read from the committed experiment fragment, because
which rows a run keeps is registered, not typed at launch.

The campaign scans the predecessor trace at preflight (model-free, before the server is touched),
narrows the dispatch roster to the 500 rows that are not COMPLETE, fits each realized native request
inside generation, merges the 580 replayed rows with the 500 live ones at the seal through the one
`_canonical_output_rows` stage, writes the `predecessor_attempt` block into the manifest, and
schedules the single official score of the complete 1,080-row manifest at finalize through
`core.scoring_batch`. **Do not run `coordinate-fit`**: the native gate fits every request itself, and
a standalone fit would double-charge the FIT row.

Expected: about **2,500 contacts** (500 rows at cell B4b's realized 5.006 per row), about **7,500
repeated speech seconds**, about **10,000 FIT endpoints**, about **1.6 GPU hours** and about 1.8
hours of generation wall clock, plus about 6 minutes of official scoring on the full 1,080 rows.
Ceilings are run-cumulative and are bounds, not targets: 11,880 generation calls for the whole run
(2,922 already spent), 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU
hours, 6,480 native task-contract calls. Nothing else may occupy the GPU while this flies.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy, utilisation and parked fraction for the lease window
from that file; they are mandatory verdict fields. A `0 %` utilisation reading with the model still
resident means a CPU-only step, not a hang.

**If the flight fails again**, cell B4b-rep closes. No third registration, no second resume, no row
filtering: preserve everything, reconcile the lock, and report.

## 6. Post-flight

1. The manifest must be COMPLETED with exactly **1,080** ordered outputs and a `predecessor_attempt`
   block declaring trace SHA-256 `ad7a78c7…`, kept-ids SHA-256
   `45e9eeb3a80c2b448cd7eb3922de4c000e22c2f188448c786de6f0a076916049` and counts
   `{kept: 580, flown: 500, partial: 4}`. `core.bundle.verify_bundle` must pass invariant **I7r**:
   every kept row held against the predecessor trace byte for byte, every flown row against this
   attempt's own, no sample in both.
2. **One** official score of the complete manifest through `core.scoring_batch`, never sharded, never
   re-run. Fill its `scores_sha256` and `run_manifest_sha256` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json)'s `right_replicate` arm.
3. Run the paired read exactly as [`analysis-recipe-v1.json`](analysis-recipe-v1.json) pins it. The
   **STOP condition of the preregistration applies first**: the recomputed `(B4b − anchor)` contrast
   must reproduce `+1.1294` and `−0.7117` to the digit and both comparators must reproduce their
   registered aggregates, or the read stops.
4. **Never split the read on kept versus flown rows.** That partition is an arrival-order fact, not a
   property of the rows, and it is not a preregistered stratum.
5. Report the cost fields section 7 of the preregistration lists, and say explicitly, in the verdict,
   **which rows were resumed rather than re-flown** and what the run-cumulative contact total was
   (predecessor + this attempt).
6. Verdict: `docs/results/2026-09-17-slurp-b4b-replication-v2-verdict.md`, beside the first-pass
   verdict `docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md`, which stays on record
   unchanged.
7. Close both reopened exposure rows at the merged seal with the realized actuals, appending rather
   than replacing their existing text.

## 7. Deviations the coordinator should know about

1. **A sibling baseline fragment exists.** The brief asked for the aborted cell's own baseline
   fragment. The runtime forbids it: `native_contact_fit` lives in the baseline, a fresh FIT
   **attempt** id is mandatory (section 4.1 of the note — all four partial rows already have
   `perception:0` and `solver:0` request-fit receipts under the predecessor fit attempt, and the fit
   gate refuses an existing receipt path), and `core.config.compose` refuses a key defined by two
   fragments, so the field cannot be overridden from the experiment fragment. Editing the aborted
   arm's baseline in place would retroactively move a closed registration's composed hash. The
   sibling differs in exactly `native_contact_fit.attempt_id` and `what_this_is`.
2. **The FIT run id and both exposure rows are reused, not replaced.** The fit receipt root is
   namespaced by run *and* attempt, so a fresh attempt id alone clears the collision, and the run's
   accounting stays on its existing two rows — which is why this package adds no ledger row.
3. **The two speech-feature identity strings are HELD**, unlike in the B5e recovery and unlike cell
   B4b-rep's own choice against cell B4b. A resume must not move them: they ride the audited payload
   as ORG/CONTROL provenance and the 580 kept rows already carry the predecessor's values.
4. **`prepare-supply` was not run by this registration.** A 1,080-row campaign was occupying the GPU
   and the host, and the re-pin cycle does the same model-free work once, with the
   output-equality assertion attached. The inherited pin is therefore expected to mismatch; section 2
   says what the tool does about it.
5. **No `core.flight.cli check` receipt for this cell.** It reserves the attempt id; a registration
   agent is not entitled to spend one. The hashes were computed through the same
   `compose()` / `protocol_hash()` functions `check` uses, and the method was verified against two
   sealed registered values.
