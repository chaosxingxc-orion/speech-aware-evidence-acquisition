# Cell B8b launch runbook: the Reviewer slot-audit context block

Everything the coordinator needs for cell B8b is in this directory and in the committed configs.
**Six steps remain: mint the decision receipt (section 2), re-pin and flip, commit, fly the four-row
smoke, fly the 1,080-row arm, then run the paired read.** Preregistration:
[`../2026-09-19-slurp-b8b-reviewer-audit-v1-preregistration.md`](../2026-09-19-slurp-b8b-reviewer-audit-v1-preregistration.md).

The registration agent made **zero model, tokenizer, encoder, ASR, scorer, server and paid-API
contacts**, never started, stopped or queried the resident service, **never read or wrote a run
directory**, never touched a flight lock, and did not touch any flight in progress.

## 0. The order constraint — read this first

Owner decision 27 puts cell B8b after cell B7r; owner decision 15 forbids flying on a HARMFUL
predecessor's base. Concretely:

1. **The four-row smoke opens only after cell B7r's own four-row smoke has sealed.** The two form
   smokes are never in flight together, and criterion 4 below compares against B7r's sealed smoke
   bytes, which must therefore exist.
2. **The 1,080-row arm opens only after cell B7r's arm has sealed AND been read NOT HARMFUL**, and
   after this cell's own smoke has sealed.

One experiment in flight at a time.

## 1. What is registered

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1` |
| arm run / attempt | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` / `attempt-slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-generation-v1` |
| arm FIT | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-fit-v1`, 47,520 endpoints, inside the same campaign |
| arm composed / protocol | `c8599381f789c332597bbfc8008e64943fd7c3c3cd64c3abf49c4860ead58c6b` / `4997c665acc71869843dd31f0c920ceaacc18384d21db92cf809c57617f3cbae` |
| arm campaign plan | `configs/campaign/slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1.json` (one cell) |
| smoke cell | experiment and cell `slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1` |
| smoke run / attempt | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1` / `attempt-slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-generation-v1r` |
| smoke FIT | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-fit-v1`, 176 endpoints, inside the same worker |
| smoke composed / protocol | `097e94c094459dcbf14b0ae01067b418124bd334acbe2047f34ac870bc909139` / `6673658fb37f7e562bd31976a869b51e4365ba26332a09262024144fd2035a83` |
| baselines | `configs/baseline/slurp-native-anchor-ncp-l1-reviewer-audit-{train-fold-a,smoke-4}-v1.json` |
| experiments | `configs/experiment/slurp-native-ncp-l1-reviewer-audit-anchor-{train-fold-a,smoke-4}-v1.json` |
| prepared supply (inherited pins, to be rebuilt by the re-pin tool) | arm `prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v2.json`, SHA-256 `391177e18797854db0f41648a4de23a3ff100288e653032bb4c2dae09d8d44cd`, **output** `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`; smoke `prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1/phase-supply-v2.json`, SHA-256 `7c9d1e17d2637e18378225ff768e929badbf5c82cbe9a19b7ffbf4e52cb1c1f9`, **output** `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` |
| budgets (arm) | 11,880 generation contacts, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, **1 official complete score** |
| budgets (smoke) | 44 generation contacts, 176 FIT endpoints, 117 repeated speech seconds, 1.0 fit-inclusive GPU hour, 24 native task-contract calls, **zero scoring jobs** |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | both cells `held`, with the inherited `preparation` requirement and **no decision requirement** |
| comparator | cell B7r's sealed bytes (primary, `PENDING_B7R_SEAL`); cell B7a's (secondary, `PENDING_B7A_SEAL`); the sealed dual-store anchor and the released direct anchor as context |

**The one factor** is the episode-class key `native_episode.reviewer_audit`. **One further key**,
`native_episode.finite_completion_policy = "deliver-latest-or-abstain"`, is declared beside it as a
harness-robustness measure after cell B7a's recovery arm aborted at 1,451 contacts on a capped
Reviewer completion; it renders no request byte and is not a factor — see preregistration section
3.1, and note the mandatory `finite_completion` row-count diagnostic it brings with it.

Protocol hashes were computed the way the precedent computes them, model-free:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-ncp-l1-reviewer-audit-train-fold-a-v1",
            "slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

(For the smoke, swap in the two `smoke-4` fragment names and the split identity
`4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`.)

**The method is verified against sealed registered values on this tree.** The same two calls
reproduce cell B7r's own registered composed
`c17c661c0514951ec1ad5ec683f1e236ce269b9eceedf4bf376a9cf87fe03eeb` / protocol
`2d3b2a864a9528b2c69f58e58ff195b69bb8811538b880418dec8175c4e30257` and its smoke's
`c4306c4c7d9f36446715a32daa360455cc7e4f0b94e18b22a638107851c886c4` /
`28af23a50b1dcf1f8f8469c39f377d657a8810c7aeefa9d94ed5bffd2f50ed29`.

**These hashes describe the fragments exactly as committed** — readiness `held`, the inherited
preparation requirement, **no decision requirement**. Re-pinning, adding the decision requirement
and flipping readiness each change them. **Do not do that by hand — use the tool of section 2.**

## 2. The launch step: `core.flight.repin`

Shell prelude for every command below:

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
`$DATA/coordination/slurp-b8b-reviewer-audit-v1/root-admission-v1.json` in the same shape cells B0r,
B4b, B4b-rep, B5e and B8a use, with decision id **`slurp-b8b-reviewer-audit-admission-v1`**.

**Re-pin BOTH cells in one cycle.** Round 2 of the re-pin tool rewrites the protocol document's
SHA-256 inside *every* plan in this package, so re-pinning one cell alone leaves the other cell's
ledger `Plan SHA256` stale. Pass both pairs:

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
    --cell slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
  --experiment slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1 \
    --cell slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1 \
  --readiness-dir docs/readiness/2026-09-19-slurp-b8b-reviewer-audit-v1 \
  --preregistration docs/readiness/2026-09-19-slurp-b8b-reviewer-audit-v1-preregistration.md \
  --package-name slurp-b8b-reviewer-audit-v1 \
  --decision coordination/slurp-b8b-reviewer-audit-v1/root-admission-v1.json \
  --decision-id slurp-b8b-reviewer-audit-admission-v1 \
  --set-ready
```

If the coordinator prefers to flip only the smoke first, that is legitimate — but **re-pin the arm
again (without `--set-ready`) before the arm launches**, for the reason above.

**Expect a rebuild, and expect it to prove something.** Both baselines inherit cell B7r's prepared
artifacts. The prepared artifact's identity digest pins the cell's whole composed configuration, and
this cell's differs from B7r's by its two declared keys (arm
`757dfc5b…` → `7799e57a…`; smoke `e3d880e1…` → `fcd664ae…`, both measured model-free in the
registration, with the B7r values reproducing the ones stored inside B7r's own artifacts). So
`core.preparation.load_artifact` will refuse the inherited artifact for this cell and the tool will
derive a fresh one into `prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-{TRAIN-FOLD-A,SMOKE-4}-V1/`.
`_compare_artifact_output` then **refuses the rebuild unless the new Perception selection is
byte-identical to the inherited one** (`ba5e1faa…` on 1,080 of 1,080 rows; `512583ec…` on 4 of 4).
That refusal is the model-free proof that neither declared key moves a knowledge-selection byte.

> **`--allow-output-change` must never be passed here.** If an output SHA-256 stops matching, a
> merge changed the knowledge channel — **stop and report.**

### 2.1 A known refusal, and how to get past it without weakening anything

**Read this before the first re-pin.** These two cells inherit *cell B7r's own* prepared artifacts,
so a rebuild changes both the pinned `relpath` and the pinned `sha256` — and
`core.flight.repin.assert_no_residue` then scans the whole of `docs/` and `configs/` for those two
old strings and **refuses**, because **cell B7r's own committed fragments legitimately still carry
them**. The refusal is correct behaviour hitting a case it was not written for; it is not a defect in
this package, and it was found in this registration rather than at launch.

Exactly which files it will name (the B8b files themselves are rewritten before the check runs, so
they drop out):

| cell | old values that will still be found | in |
| --- | --- | --- |
| arm | `prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v2.json`, `391177e18797854db0f41648a4de23a3ff100288e653032bb4c2dae09d8d44cd` | `configs/baseline/slurp-native-anchor-ncp-l1-reviewer-format-train-fold-a-v1.json`, `configs/experiment/slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1.json` |
| smoke | `prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1/phase-supply-v2.json`, `7c9d1e17d2637e18378225ff768e929badbf5c82cbe9a19b7ffbf4e52cb1c1f9` | `configs/baseline/slurp-native-anchor-ncp-l1-reviewer-format-smoke-4-v1.json`, `configs/experiment/slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1.json` |

**Preferred remedy — the shape every earlier cell used, including B8a.** At the launch commit, build
each cell's *own* prepared artifact with the model-free `prepare-supply` step first, assert its
Perception output by hand, then pin it, then run the re-pin tool — which now finds the pin valid,
rebuilds nothing, and adds nothing to the residue set:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-supply \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1
# then, before pinning it, assert the Perception output has NOT moved:
$PY -B -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["output_sha256"])' \
  "$DATA/prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1/phase-supply-v2.json"
# must print 512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733
# (arm: ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f)
```

Then set `prepared_phase_supply` in the baseline and the `preparation` requirement's `relpath` /
`sha256` in the experiment to that artifact's own path and hash, and run section 2's command. **That
hand-run output assertion replaces `_compare_artifact_output`, which does not run when the tool has
nothing to rebuild — do not skip it.** If the printed hash is not the one above, a merge changed the
knowledge channel: **stop and report.**

**Fallback, if the tool is run first anyway.** The refusal is raised *after* the fragments, the
package files and the ledger have already been rewritten with the new pins, so the tree is left
consistent and **a second invocation of the same command completes**: it finds the pin valid,
rebuilds nothing and adds nothing to the residue set. Verify the pins and the `output_sha256` above
by hand before trusting it, and never reach for `--allow-output-change`.

Drop `--set-ready` and the two `--decision` flags to re-pin only, for example after merging master.
The tool recomputes the composed and protocol hashes and rewrites this README, the preregistration,
the four plan pairs, the protocol document and the exposure-ledger notes for the package's run ids,
then runs `core.flight.cli check` for every cell and asserts the runtime-derived hashes agree.
**Commit the result before launching**: a COMPLETED manifest reads `study_commit` at finalize and
refuses a dirty tree.

## 3. Pre-launch checklist

1. The order constraint of section 0 is satisfied. One experiment in flight.
2. `git -C "$REPO" status --porcelain` is empty. **Fly from a clean detached worktree pinned at the
   admitted commit.** No receipt from this preparation lives inside the repository.
3. No other flight process is running and no `locks/flight.lock` is held in the data root.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`. **Attach only, never spawn or stop.**
5. If a flight is launched as a Windows Scheduled Task (owner decision 24), register the task with
   the **battery and idle conditions disabled and no execution time limit** — `schtasks /query /tn
   <task> /xml` must show `<DisallowStartIfOnBatteries>false</…>`,
   `<StopIfGoingOnBatteries>false</…>` and `<ExecutionTimeLimit>PT0S</…>` — and keep `powercfg` away
   from the machine for the duration.
6. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
7. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
8. Do **not** run `scripts/checks/derived_media_confinement_check.py` from inside the checkout: it
   rewrites `docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and
   would dirty the tree the manifest reads at finalize.

A contact-free `check` can be re-run at any time on a clean tree (the re-pin tool runs it for you):

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1
```

## 4. The four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
  --owner root-slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1.worker-lease.json"
```

If the smoke runs as a Scheduled Task instead of an open terminal, the task's action is that same
`worker` command, with the lease issued first and its token file passed through; the task conditions
of section 3 item 5 apply unchanged.

Expected: a few minutes of wall clock, about **20 generation contacts** (5 per row; 44 is the
ceiling), up to 176 FIT endpoints, about 53 repeated speech seconds, **no scorer**.

### Accept only if all six hold — structural acceptance only

Preregistration section 9 is the authority; in short:

1. Perception, Solver, Reviewer and Planner contacts, about five per row plus revisions; no row
   exceeds 11.
2. **The `slot_audit` receipt on every Reviewer contact of 4 of 4 rows**, with `schema`
   `saea-reviewer-slot-audit-v1`, `view_id` `slot-audit-v1`, `release_sha256` `eaa2dd0d…`,
   `snapshot_sha256` `0cc3f96c…`, `table_content_hash` `d4cd4bf3…`, `template_id`
   `probes/ncp_slurp_slot_audit_reviewer_v1.txt`, `template_sha256` `88cc927d…`, the three declared
   thresholds and `flag_counts` carrying all four names including zeros. **At least one Reviewer
   contact of every row must carry `applied: true`**; an `applied: false` / `reason:
   "draft-unparsed"` contact is acceptable beside it.
3. The block is an **addition**: the last `block_chars` characters of the rendered
   `reviewer:current-draft` text hash to `block_sha256`, the text before them is the boundary's own
   L1 rendering, **no other boundary row carries a `slot_audit` block**, and the compilation record's
   `template_sha256s` carries the block's three assets.
4. The **Perception request** of each row is byte-identical to cell B7r's own sealed four-row smoke
   on 4 of 4 rows. (Solver/Planner requests may legitimately differ where their upstream responses
   do — greedy decoding is not bitwise reproducible across batch compositions.)
5. One `*.request-fit.json` per realized contact under
   `$DATA/prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-FIT-V1/attempt-slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-fit-v1/`,
   every one with `every_request_fits = true` and every required-token count below 24,576; the
   manifest seals clean and the tree is still clean.
6. Any row whose `terminal_disposition.reason` is `"finite_completion"` is **retained and reported**,
   not an error. An **abort** on `finish_reason` `length` is a failure: it would mean the declared
   `finite_completion_policy` did not reach the runtime.

Release the lease. A failure stops cell B8b until the fix is proven on this same four-row roster.

## 5. The 1,080-row arm

Only after the smoke seals **and** cell B7r's arm seals and is read **not HARMFUL**.

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --plan configs/campaign/slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1.json \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

The campaign acquires its own `GenerationLease` against the resident session and schedules the one
official score at finalize. Expected: about **5,420 contacts** (5.02 per row; 11,880 is the exact
program maximum), about **3.6 GPU hours**, one complete official score. `coordinate-fit` must **not**
be run, or the FIT row is double-charged.

## 6. The paired read

Pinned by [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and preregistration section 6. It is
model-free — it works from the two sealed score artifacts and the sealed per-row outputs — so it may
run in parallel with any GPU flight (owner decision 27).

Before any table is looked at, **assert the STOP condition**: cell B7r's sealed comparator reproduces
its own registered official aggregates to the hundredth, with the `PENDING_B7R_SEAL` hashes filled in
and verified by hashing the files; 1,080 rows in and out on both sides; identical roster, split
identity and strata. Then produce the contrasts, the per-scenario tables, owner decision 17's
net-harmed-rows diagnostic, and the slot-audit diagnostics of preregistration section 6 — including
**the count of rows whose `terminal_disposition.reason` is `"finite_completion"`**, with no row
filtering.

Read **once**. The decision rule is fixed in preregistration section 6 and is not edited after a
number is seen. Output root
`$DATA/analysis/SAEA-SLURP-B8B-REVIEWER-AUDIT-ANCHOR-V1-PAIRED-ANALYSIS-V1/`; verdict
`docs/results/2026-09-19-slurp-b8b-reviewer-audit-verdict.md`.

## 7. Post-read

- **If ADMITTED**: the coordinator writes the `docs/receipts/harness-admission.json` entry in the
  form the protocol document's `harness_admission_entry_form` fixes, and adds
  `native_episode.reviewer_audit` to
  `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`.
  `scripts/checks/harness_admission_check.py` is the oracle. From that moment every later official
  SLURP number this program reports is produced by a system that contains the block.
- **If NEUTRAL**: the admission entry is still written, but the module **does not** enter the default
  plan — design section 15 resolution 5 admits a NEUTRAL node-context cell to the plan only if it
  lowers cost, and this one adds context and removes nothing.
- **If HARMFUL**: no plan entry, and the successor in the queue does not fly on this base (owner
  decision 15). The record keeps the negative.
- Either way, run `python scripts/checks/harness_admission_check.py`,
  `python scripts/checks/results_ledger_check.py` and
  `python scripts/checks/engineering_base_check.py`, and close the four exposure-ledger rows.

## 8. Things the coordinator should know

- **The second declared key.** `native_episode.finite_completion_policy =
  "deliver-latest-or-abstain"` was added by the coordinator on 2026-09-19, before any hash here was
  pinned, after cell B7a's recovery arm aborted at 1,451 contacts on a Reviewer completion that hit
  the 512-token cap under the module default `"raise"`. It renders no request byte and claims no
  module admission. It does create one asymmetry — a sealed B7r comparator implies B7r met no finite
  completion at all — so the count of retained `finite_completion` rows is a mandatory diagnostic and
  the verdict reports the excluded-rows recomputation beside the registered number if the count is
  non-zero. Preregistration section 3.1.
- **Two tests were updated in the same change** because they pin the two baselines'
  contents: `tests/unit/test_b8b_reviewer_audit_config.py` and
  `tests/unit/test_config_table_module_switches.py::test_the_two_b8b_fragments_arm_the_block_and_nothing_else`.
- **No `check` receipt is on file** and that is deliberate — see preregistration section 12.
- **`core.flight.cli wire-check` remains unavailable** for any native-episode cell; the substitute is
  `tests/unit/test_native_episode_runner_reviewer_audit.py`.
- **The context comparators' hashes were carried, not re-derived.** A GPU campaign was flying and
  this registration touched no run directory. Re-verify them by hashing the files at read time.
- **Which side of the delivery node this contrast sits on.** Module M3 was ADMITTED on 2026-09-19
  (commit `a533f6dc`) and `native_episode.deliver_normaliser` is now in the SLURP default plan.
  **Both sides of this contrast are node-free** — neither cell B7r's baseline nor either B8b baseline
  declares the key — so the delta is clean, but neither arm is the current default plan and these
  official numbers are not directly comparable to a later node-carrying arm. Preregistration section
  4.
