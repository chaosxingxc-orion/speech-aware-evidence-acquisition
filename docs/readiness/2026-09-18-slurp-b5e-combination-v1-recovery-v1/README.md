# Cell B5e recovery launch runbook: the one root-diagnosed recovery of the combination arm

Everything the coordinator needs to re-fly cell B5e is in this directory and in the committed
configs. **Three steps remain: mint the decision receipt (section 2), re-pin and flip the arm, then
run the campaign.** There is **no smoke step** — section 4 says why.

Preregistration:
[`../2026-09-18-slurp-b5e-combination-v1-preregistration.md`](../2026-09-18-slurp-b5e-combination-v1-preregistration.md),
whose bar clause is amended by
[`../2026-09-18-slurp-b5e-combination-v1-amendment-decision-23.md`](../2026-09-18-slurp-b5e-combination-v1-amendment-decision-23.md).
Recovery note:
[`../2026-09-18-slurp-b5e-combination-v1-recovery-v1.md`](../2026-09-18-slurp-b5e-combination-v1-recovery-v1.md).

The recovery registration agent made **zero model, tokenizer, encoder, ASR, scorer and server
contacts**, never started, stopped or queried the resident service, wrote no run directory, touched
no scheduled task and did not hold `locks/flight.lock`. The only writes outside the repository are
the model-free `prepare-supply` artifact for this cell's own run id and five receipts under
`coordination/slurp-b5e-combination-v1/`.

## 0. Why this package exists

Run `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1`, attempt
`attempt-…-generation-v1`, launched 2026-09-18T14:35Z as the Windows Scheduled Task
`SAEA-Campaign-B5e` from the flight worktree at study commit `325d67c6`, **ABORTED at
2026-09-18T14:40:20Z** after **25 contacts (5 complete rows)** and **63.72893749999999** repeated
speech seconds. The task-owned resident server died mid-request; the root cause is infrastructure
and coordinator-caused: all three SAEA scheduled tasks carried the default stop-on-battery
condition and stopped when the coordinator changed the power scheme with `powercfg`. Code,
configuration and request bytes are unchanged. The tasks are now re-registered with the battery and
idle conditions disabled and no execution time limit.

This is the **one** root-diagnosed recovery re-registration the preregistration allows for cell
B5e. A second failure closes the cell.

## 1. What is registered

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1`, run `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1`, attempt `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1` |
| arm FIT | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-RECOVERY-V1` / `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-fit-recovery-v1`, 47,520 endpoints, inside the same campaign |
| baseline | `configs/baseline/slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-train-fold-a-recovery-v1.json` |
| experiment | `configs/experiment/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1.json` |
| campaign plan | `configs/campaign/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1.json` |
| composed / protocol | `50ae44a67e1d6e897e266f9ebadb4eead62df091d4f4fbc72b9a8100b1f28ae1` / `b5d14e1fe060ee9f2b7ccc6d174b4e16cd82b5b07a9d9850808d2656ecfee4c0` |
| prepared supply | `prepared/SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1/phase-supply-v1.json`, SHA-256 `5bfc6bcdeda7438ca01725072267fe53086ffdb6395d813b3a6c897be4bfef0a`, **output** SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| budgets | 11,880 generation calls, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score — **the aborted arm's own ceilings, unchanged** |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | `held` with the `preparation` requirement pinned and **no decision requirement**; the coordinator mints the receipt and flips with the tool of section 2 |
| supersedes | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1` and its FIT row — closed, `consumed = yes`, **never reused** |

Protocol hashes were computed the way the precedent computes them, model-free:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-train-fold-a-recovery-v1",
            "slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

**The method is verified four ways on this tree**, and all four match sealed registered values
(receipt `recovery-prepared-supply-and-hashes-v1.json`): the sealed anchor's
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`, the anchor recovery's
`2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c`, cell B1's recovery arm
`c66d507d1ae03c081d04a72dda7b5be28c29d7d5d22e4f196c38e5912211da2d` and cell B4b's
`567a87ad234bb4f17c4735f94219a82b05b25a19d81fdf1ee32bb93b6eda346a`.

**These hashes describe the fragments exactly as committed**: readiness `held`, the `preparation`
requirement pinned, `prepared_phase_supply` pinned, **no `decision` requirement**. `compose` hashes
the whole merged fragment set, so adding the decision requirement and flipping readiness each change
the composed hash and therefore the protocol hash. **Do not do that by hand — use the re-pin tool of
section 2.**

The same command run against the **aborted** arm's fragments still returns
`220a5ac4381090071d3da31798496a4486de486525c591d2d39e63d4eb0beb9e` /
`d33b86abf7be171887262144ad3799e7ed79cde5f4dd3a2aaf42a0e71023b638`, the values its ledger rows
record as flown, which is the cross-check that the tree under this registration has not moved.

## 2. The launch step: `core.flight.repin`

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
`$DATA/coordination/slurp-b5e-combination-v1/root-admission-recovery-v1.json` in the same shape the
B5e admission receipt uses, with decision id **`slurp-b5e-combination-recovery-admission-v1`**.

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

`--preregistration` points at the **recovery note**, not at the sealed preregistration: the sealed
preregistration and the amendment keep the bytes the original decision receipt pinned and must not be
rewritten. The tool re-verifies the prepared artifact, applies the decision requirement, flips
readiness, recomputes both hashes, rewrites this README, the recovery note, both plan pairs, the
protocol document and the two recovery ledger notes, then runs `core.flight.cli check` and asserts
the runtime-derived hashes agree.

Drop `--set-ready` and the two `--decision` flags to re-pin only — for example after merging master,
before deciding to launch. **`--allow-output-change` must never be given here**: the whole two-factor
claim is that the Perception selection does not move, and the tool refusing a changed selection is
that claim's enforcement. If the prepared artifact's `output_sha256` stops being
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`, the merge changed the knowledge
channel — **stop and report**.

Commit the result before launching.

## 3. Pre-launch checklist

1. One experiment in flight. No other campaign is running.
2. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a COMPLETED
   manifest reads `study_commit` at finalize. **Fly from a clean detached worktree pinned at the
   admitted commit.** No receipt from this preparation lives inside the repository.
3. No flight process is running and **no `locks/flight.lock` is held in the data root** — the
   aborted attempt's lock was moved to
   `coordination/slurp-b5e-combination-v1/flight-lock-preserved-20260918T144332Z.json` and
   reconciled by `…/flight-lock-reconciliation-20260918T144332Z.json` (SHA-256
   `b63d00003824aa7ab5138d912bd9993bb71eafb800ec409fa08def59d6283c81`). Confirm it has not come back.
4. **The scheduled task that will carry this campaign has the battery and idle conditions disabled
   and no execution time limit.** This is the fix; verify it before launching, because it is the one
   condition that caused the abort. Verify with `schtasks /query /tn SAEA-Campaign-B5e /xml` and read
   `<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>`,
   `<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>`, `<IdleSettings>` disabled and
   `<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>`. **Do not change the power scheme with `powercfg`
   while a campaign is in flight.**
5. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`. Attach only, never spawn.
6. Decide the conditional comparator: if the B4b replicate's manifest is sealed **and officially
   scored before this cell's first contact**, fill its `scores_sha256` and `run_manifest_sha256` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json)'s `left_m4b_replicate_conditional` arm; if it
   is not, drop that arm and its contrast and say so in the verdict. It never gates.
7. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package closes
   the D3 gate.
8. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
9. Do **not** re-run `derived_media_confinement_check.py` from inside the checkout: it rewrites
   `docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
   dirty the tree the manifest reads at finalize.

A contact-free `check` can be re-run at any time on a clean tree:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1 \
  --cell slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1
```

`generation_authorized` is always `false`; the readiness state it reports is whatever the fragment
declares. Note that `check` reserves the attempt in the durable `AttemptStore`, which is why this
registration did not run it.

## 4. No smoke, and why

The four-row form smoke `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-V1`
already **sealed with a structural PASS** at study commit `878dd5c6` on this exact configuration: 20
calls, five contacts per row, ACCEPT on 4/4 rows, both stores present in every phase record, 20/20
request fits with a minimum margin of 9,562 tokens, clean seal. Its exposure rows are closed.

The aborted arm then realized the same form on the **full** roster: 25 sealed `MODEL_REQUEST`
payloads across 8 rows (perception 8, solver 5, reviewer 8, planner 4) with 25 request-fit receipts,
every one fitting, before the server died. The failure was not a form failure, and the recovery
changes nothing a smoke could test. Registering a new smoke would spend contacts to re-prove a
proved form.

## 5. The arm campaign — the only contact step

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1.json" \
  --owner root-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

Campaigns are launched as **Windows Scheduled Tasks**; register the task with the battery and idle
conditions disabled and no execution time limit (section 3 item 4) and keep `powercfg` away from the
machine for the duration.

The campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation, seals the manifest and schedules the single official score at
finalize through `core.scoring_batch`. **Do not run `coordinate-fit`**: the native gate fits every
request itself, and a standalone fit would double-charge the FIT row.

Expected, from the four sealed realisations on this geometry: about **5,430 contacts** at about 5.03
per row, about **15,500 repeated speech seconds**, about **21,700 FIT endpoints**, about **3.7 GPU
hours** and about 3.8 hours of generation wall clock, plus about 3 minutes of official scoring.
Ceilings are 11,880 / 47,520 / 33,930 / 12.0 / 6,480 and are bounds, not targets. Nothing else may
occupy the GPU while this flies, and CPU work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy, utilisation and parked fraction for the lease window
from that file; they are mandatory verdict fields. A `0 %` utilisation reading with the model still
resident means a CPU-only step, not a hang.

**If item E10 (resume-recovery, owner decision 22) is merged before this flies**, the coordinator may
convert this registration to a resume-recovery instead of a full re-fly. The conversion changes no
question, roster, factor, comparator, decision rule or cap; it must re-check the run-cumulative
budget, because a resumed attempt and its predecessor share one run id.

## 6. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b5e-combination-v1/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `recovery-prepared-supply-and-hashes-v1.json` | see `recovery-plan-hashes-v1.txt` | the rebuilt prepared artifact and its pin; its `output` byte-identical to the aborted arm's, the sealed anchor's, cell B1's and cell B4b's (`ba5e1faa…`); the recovery composed and protocol hashes; the composed-key diff against the aborted arm (56 identical / 11 differing, none model-facing); the four-way method verification |
| `recovery-prepare-supply-v1.json` | see `recovery-plan-hashes-v1.txt` | the raw model-free `prepare-supply` receipt, `contact_class = model-free`, one worker |
| `recovery-request-envelope-comparison-v1.json` | `4ec576839d1d0cc56526cf0bf0408ac50169c415c07b59a9c7eedfb29c12d5e7` | all twelve identity strings of both registrations searched across the aborted attempt's 25 sealed `MODEL_REQUEST` payloads: **0 hits**; the payload's own `key_representation_id` / `matcher_policy_id` are program-derived; the per-contact model-facing digests the recovery flight can be checked against |
| `recovery-ledger-parse-v1.json` | see `recovery-plan-hashes-v1.txt` | `contracts._parse_ledger_tables` sees each of the two new rows exactly once at `consumed = no` and the four B5e rows of the aborted registration exactly once at `consumed = yes` |
| `recovery-plan-hashes-v1.txt` | see the file | the SHA-256 of the recovery note, of every document in this directory and of the three config fragments |
| `flight-lock-reconciliation-20260918T144332Z.json` | `b63d00003824aa7ab5138d912bd9993bb71eafb800ec409fa08def59d6283c81` | the coordinator's quiescence proof: owner pid dead, 0 slots processing, attempt `ABORTED` at 25 calls, `flight.lock` moved to the preserved copy |
| `prompt-fit-v1.json` | `544903713390aad0a58986d528e71a9f100a87d63f25329230c11286198c0c5b` | the aborted registration's prompt-fit receipt, unchanged and still authoritative: registered static bound 17,983 required tokens, margin 6,593 against the 24,576-token slot |

**There is no `check` receipt, deliberately**, for the reason the aborted registration's package gave
and section 3 repeats: `FlightRuntime.preflight` asserts a clean study tree and reserves the attempt.
Section 2's re-pin runs `check` on the clean registration commit and refuses if the runtime-derived
hashes disagree with the ones it has just written.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer. The composed-key diff, the store-by-store equality proofs of
`composed-hashes-v1.json` and the 25-payload identity search stand in its place, and
`tests/unit/test_b5e_combination_recovery_config.py` pins the config half as a committed test.

## 7. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the official
   score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` for `right_b5e` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that recipe
   pins it: `analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast`, whole-speaker clusters
   from `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/{score-contrasts.json,per-scenario-tables.json,README.md}`.
3. **Stop if the STOP condition fails**: all four sealed comparators must reproduce their registered
   official and projection-v3 aggregates to the hundredth of a point, and the recomputed
   `(B1 minus anchor)` and `(B4b minus anchor)` contrasts must reproduce `+10.54` / `+0.74` and
   `+1.1294` / `-0.7117` CI95 lower bounds to the digit.
4. Apply the decision rule from the preregistration section 7 with **clause 1 as amended by owner
   decision 23**: the bar reads the **official unprojected** pooled SLU-F1 (>= 64.00) and official
   intent (>= 78.00), with the v3-projected and TRAIN symmetric numbers reported beside them and the
   verdict stating whether the v3 number would have cleared 64.00. **Clause 2** (the combination,
   gated on `(B5e minus B1)`, with `(B5e minus B4b)` reported and the additivity statement) and
   **clause 3** (the HARMFUL trigger) are unchanged. Publish
   `docs/results/2026-09-18-slurp-b5e-combination-verdict.md` with the headline table, every clause
   table, the saves/harms/ties table, the full 18-scenario table in **both** weightings for every
   contrast, owner decision 17's net harmed-rows-per-scenario diagnostic, the recomputed M1
   diagnostics, the recomputed B4b per-type slot decomposition, and the cost table. The verdict must
   name this run as the recovery and state that the aborted attempt's 25 contacts were never scored
   and never read.
5. Close the two exposure rows: set `consumed` to `yes` for
   `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` and its FIT
   row, and append to each note the actual calls, actual repeated speech seconds, measured GPU hours,
   the sealed score and manifest SHA-256 values, and the verdict.
6. **On MEETING THE BAR (clause 1)**: register **B5er**, the request-identical replicate, immediately
   — before any "SLURP base v2.0" lock is claimed. **On MISSING it**: the bar is **not** lowered
   (owner decision 20); decision 15's order resumes and B5b reads against the same bar. **On HARMFUL
   (clause 3)**: the v2 candidate falls back to B1 alone, B5er is **not** registered, and the owner is
   told.
7. **On a second failure**: the cell closes. No third registration, no replay, no row filtering; the
   fix must be proven on a four-row dry run before another mechanism is admitted.

## 8. Deviations the coordinator should know about

1. **No smoke cell.** Section 4. The aborted registration's smoke sealed and is closed; this package
   registers only the arm and its FIT row.
2. **`--preregistration` points at the recovery note.** The sealed preregistration and its amendment
   keep the bytes the original decision receipt pinned and are never rewritten by the re-pin tool.
3. **The speech-feature identity strings are fresh for this cell.** They are provenance only, and the
   25-payload search of section 6 proves directly that neither the aborted pair nor the recovery pair
   reaches a request byte.
4. **The prepared Perception supply was rebuilt at one worker**, model-free, and selects identically —
   same `output_sha256` as the aborted arm's, the sealed anchor's, cell B1's and cell B4b's on 1,080
   of 1,080 rows.
5. **`allowed_execution_stages` declares `worker` as well as `campaign`**, mirroring the aborted arm's
   fragment. This cell flies through `campaign`; the stage is declared for parity, not to authorize a
   standalone worker on the 1,080-row roster.
6. **`generation_budget.definition` is the eleventh bookkeeping key that moves.** Only its free-English
   text changed, to record the recovery's budget accounting; the cap (11,880) and the target are the
   aborted arm's.
7. **The registration commit does not flip readiness and does not fly anything.** Both are the
   coordinator's acts, and section 2 is the tool for the first.
