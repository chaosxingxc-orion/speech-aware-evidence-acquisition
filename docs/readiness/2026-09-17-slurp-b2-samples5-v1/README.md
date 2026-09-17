# Cell B2 launch runbook: sample-and-aggregate commit, N = 5 at T = 0.7

Everything the coordinator needs to fly cell B2, its greedy-repeat twin and its four-row smoke is
in this directory and in the committed configs. Three steps remain: add the root decision
requirement, flip readiness, fly the smoke, then the arm, then the twin. Preregistration:
[`../2026-09-17-slurp-b2-samples5-v1-preregistration.md`](../2026-09-17-slurp-b2-samples5-v1-preregistration.md).

The preparation agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**,
never started, stopped or queried the resident service, and never touched cell B0 or its pinned
worktree while B0 was in flight.

There is **no blocking gate in this package**: `check` and `prepare-supply` were actually run for
all three cells on this branch and both pass. There is one blocking decision outside it — **cell B0
closed HARMFUL** (`docs/results/2026-09-17-slurp-b0-review-off-verdict.md`, master `ccd2bc88`,
landed while this package was being prepared), and its registered own-null replicate and
re-decision rule settle whether cell B2's base is cell B0 or the sealed anchor. Nothing here may
launch before that. See section 2 step 3 and section 11.

## 1. What is registered

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-samples5-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-SAMPLES5-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-samples5-train-fold-a-generation-v1` |
| arm FIT | `SAEA-SLURP-NATIVE-SAMPLES5-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-samples5-train-fold-a-fit-v1`, 25,920 endpoints, inside the same campaign |
| twin cell | experiment and cell `slurp-native-samples5-greedy-twin-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-SAMPLES5-GREEDY-TWIN-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-samples5-greedy-twin-train-fold-a-generation-v1` |
| twin FIT | `SAEA-SLURP-NATIVE-SAMPLES5-GREEDY-TWIN-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-samples5-greedy-twin-train-fold-a-fit-v1`, 25,920 endpoints |
| smoke cell | experiment and cell `slurp-native-samples5-smoke-4-v1`, run `SAEA-SLURP-NATIVE-SAMPLES5-SMOKE-4-V1`, attempt `attempt-slurp-native-samples5-smoke-4-generation-v1` |
| smoke FIT | `SAEA-SLURP-NATIVE-SAMPLES5-SMOKE-4-FIT-V1` / `attempt-slurp-native-samples5-smoke-4-fit-v1`, 96 endpoints |
| campaign plans | `configs/campaign/slurp-native-samples5-train-fold-a-v1.json`, `configs/campaign/slurp-native-samples5-greedy-twin-train-fold-a-v1.json` |
| composed / protocol (arm) | `5261d4c4a572cefe65cc2162c48be673f695e0e2f288b34e9ce8b753b5cf7111` / `8b28f552ffb55f2be0deecf290b3e5aab5f287f9b911573bccac0a1d610972b1` |
| composed / protocol (twin) | `9abb4936406a59a4a59ef1292b9fb1e316f1dfdc8c9888cbd586004fd963acf1` / `e9f8a31e30e75307bf55b23634be27c3e3474699c4d7a9d506105178bfbf70f9` |
| composed / protocol (smoke) | `41b35f8fd5c55cd5eaee5751321f8c7c601f3ee4eec1677cfa81e9656a0bcfbc` / `48c2e685c675dd3a2150cb6c176e6298bedd3053acb283c4f826e5b1a6383b2d` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | all three cells are `held` with the **preparation requirement already pinned**; the coordinator adds the decision requirement and flips |
| registration commit | `fd882ca8`, on branch `fable/b2-prep`, based on master `6c5c9ab7` |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-review-off-samples5-train-fold-a-v1",
            "slurp-native-samples5-train-fold-a-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with the twin fragment pair reproduces the twin pair, and with the two smoke
fragment names plus split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`
the smoke pair. The method is verified twice: run it on the anchor fragments and it returns the
anchor's registered `d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`, and
`core.flight.cli check` independently re-derives each registered protocol hash at runtime (section
6). See `composed-hashes-v1.json`.

**These hashes describe the fragments exactly as committed at `fd882ca8`**: readiness `held`, the
preparation requirement pinned, `prepared_phase_supply` pinned. `compose` hashes the whole merged
four-fragment document, so the coordinator's readiness flip changes the composed hash and therefore
the protocol hash. Recompute and re-pin before launch (section 7).

## 2. Pre-launch checklist

1. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a
   COMPLETED manifest reads `study_commit` at finalize, so the checkout stays clean for the whole
   run. **Flights run from a detached worktree pinned at the admitted commit**, because the main
   checkout carries untracked leftovers (`_tmp_slurp_gap_extract.py`, `integration_native_finite.py`,
   `wsl$/`) that would fail both gates. No receipt from this preparation lives inside the
   repository.
2. No flight process is running and no `locks/flight.lock` is held in the data root. Cell B0 must be
   finalized and its verdict published: one experiment in flight.
3. **Cell B0 closed HARMFUL while this package was being prepared — settle the base first.**
   Master moved from `6c5c9ab7` (this branch's base) to `ccd2bc88`,
   `docs/results/2026-09-17-slurp-b0-review-off-verdict.md`: HARMFUL by the preregistered intent
   clause, a width failure with a nil point estimate (pooled SLU +0.13, CI95 [-1.15, +1.45]; intent
   -0.37, CI95 [-1.53, +0.82]), with a same-roster own-null replicate and a re-decision rule
   registered in `docs/readiness/2026-09-17-slurp-b0-replicate-v1-preregistration.md`. The spec's
   Phase B table says later cells then build on the sealed anchor, but the re-decision may restore
   B0 as the base. **Do not launch until that re-decision lands.** If the base becomes the anchor,
   re-base both full cells and the smoke on it — the baseline fragments become anchor-based, the
   review-off role graph goes back to `max_revisions 1` / reviewer 3 / planner 1, the policy
   fragment becomes a review-revise program whose `max_contacts` equals its own grouped ceiling
   (`1 + 2*(3 + 1 + 1*5) = 19` for `max_revisions 1`), the contact and FIT budgets are recomputed,
   and every hash in this package is recomputed. That is a new registration, not an edit.
   Nothing else in this package depends on the merge: `ccd2bc88` touches only
   `docs/exposure-ledger.md`, cell B0's own analysis recipe and the results ledger — none of the
   five modules the prepared phase-supply artifact's identity digest pins — so the prepared supplies
   and every composed and protocol hash here survive it unchanged.
4. Fill the two `PENDING_B0_FINALIZE` digests into `protocol-registered-v1.json` and
   `analysis-recipe-v1.json`. Cell B0 has finalized, so they are known: score artifact
   `51f37e6c5a78751f2d000ac370cff6f0fff18745cd18d1fc81a2cd145ce960ae`, run manifest
   `8b6f3f783f1933c4009c46cdc01472e240c547a496f7553c07e5efe301cdfe32` (outputs
   `108d6851c5cc5347e5b626354a99ea370f65d321c16396a914274e90c2678e65`, 1,080 scored rows, 1,071
   parsed). They are left as placeholders here only because B0 finalized after this package was
   written and filling them re-pins the protocol document, the six plan documents that cite its
   SHA-256 and the six ledger notes — work that the base re-decision of step 3 may moot.
5. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
6. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
7. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
8. Add the root decision requirement to `cells[0].readiness.requirements` of all three experiment
   fragments (a `decision` entry naming the admission receipt under the data root), then flip
   `readiness.state` from `held` to `ready` in `configs/experiment/slurp-native-samples5-smoke-4-v1.json`
   first, and in the two full experiment fragments only after the smoke seals. Commit each change,
   because step 1 must still hold at launch, and recompute the hashes after each one (section 7).

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

## 3. Step one: the four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-smoke-4-v1 \
  --cell slurp-native-samples5-smoke-4-v1 \
  --owner root-slurp-native-samples5-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-samples5-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-smoke-4-v1 \
  --cell slurp-native-samples5-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-samples5-smoke-4-v1.worker-lease.json"
```

Expected: about 3 to 6 minutes of wall clock, 24 generation contacts, 96 FIT endpoints, about 63.6
repeated speech seconds, no scorer. Accept only if all seven hold:

- exactly **24 contacts, 6 per row** — one Perception and five Solver samples — and no Reviewer or
  Planner contact in the trace;
- the episode receipt carries `review_loop_disposition = skipped_by_configuration` on every row;
- every outputs row carries a top-level `solver_group` sibling of `native_episode_receipt` with
  **all five raw samples**, `sample_index` 0 to 4 ascending, five **distinct** seeds
  (`1597380463 … 1597380467`) and `temperature 0.7` on each
  (`rails.native_episode_receipt.validate_solver_group_receipt` enforces the shape at seal, so a
  missing sample stops the worker rather than producing a row);
- the delivered `final_response_text` **equals the commit policy's own output**: replay each row
  offline with `analysis.native_commit_replay.replay_row` at `min_support 3`,
  `similarity_threshold 0.8` and confirm the replayed answer is byte-identical to the delivered one
  on all four rows;
- the `solver_group.delivered` block carries the intent support count, the member sample indices and
  the tie-break index, and each delivered entity its own support and member indices;
- one `*.request-fit.json` per realized contact — **24 receipts, not 8** — under
  `$DATA/prepared/SAEA-SLURP-NATIVE-SAMPLES5-SMOKE-4-FIT-V1/attempt-slurp-native-samples5-smoke-4-fit-v1/`,
  every one with `every_request_fits = true` and the Solver requirement below 24,576 (the registered
  upper bound is 13,157);
- the worker prints a seal and the tree is still clean.

Read the serving monitor for this window as well: the smoke is the **first visible evidence** of
whether the five same-prefix sibling requests reuse the cached prompt prefix on one slot. Record the
per-contact latency of sample 0 against samples 1 to 4. If samples 1 to 4 cost the same prefill as
sample 0, the 5.0 GPU-hour ceiling of the full cell is optimistic and the coordinator should
re-price before launching the arm.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops cell B2 until the fix is proven on this same four-row roster.

## 4. Step two: the arm campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-samples5-train-fold-a-v1.json" \
  --owner root-slurp-native-samples5-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

## 5. Step three: the twin campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-samples5-greedy-twin-train-fold-a-v1.json" \
  --owner root-slurp-native-samples5-greedy-twin-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

One cell in flight at a time: seal the arm before launching the twin. Each campaign acquires its own
`GenerationLease` against the resident session, fits each realized native request — all five Solver
samples separately — inside generation, seals the manifest and schedules the single official score
at finalize through `core.scoring_batch`. Do not run `coordinate-fit`: the native gate fits every
request itself, and a standalone fit would double-charge the FIT row.

Expected per arm: **6,480 contacts at 6 per row** and 18,507.17 repeated speech seconds against
ceilings of 6,480 and 18,508. Cell B0's own measured two-contact cost is the reference. The
registered fit-inclusive ceiling is 5.0 GPU hours per arm and rests on the prompt-cache assumption
of section 8 of the preregistration: if the five siblings reuse the prefill, the cost is close to
cell B0's plus four decodes per row; if they do not, pessimistic linear scaling is 3x cell B0's
generation cost, about 4.2 GPU hours. Budget roughly 4 to 6 hours of wall clock for generation plus
about 3 minutes of official scoring, per arm. Nothing else may occupy the GPU while either flies,
and CPU work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for each lease window from that file;
they are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means a
CPU-only step, not a hang.

## 6. Post-flight

1. Confirm each manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows each carrying
   its `solver_group`, and each official score ran exactly once. Record the score artifact SHA-256
   and the run manifest SHA-256 for both arms.
2. Fill `scores_sha256` and `run_manifest_sha256` for all four arms into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that
   recipe pins it: `analysis.null_calibration_cli.rows_for` to read the sealed score registries,
   `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B2-SAMPLES5-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}` with all
   four contrasts of the recipe.
3. Compute the preregistered agreement diagnostics: the intent support-count distribution, entities
   kept and dropped by the support filter by slot type, the malformed-sample count, the rows whose
   delivered answer differs from sample 0, and the arm-versus-twin per-row sample disagreement rate.
4. Produce the **report-only** sensitivity table with `analysis/native_commit_replay.py` over the
   sealed `solver_group` rows at `s` in {2, 3, 4}, char-F1 0.8. It is never a gate and no threshold
   may be chosen from it after the fact.
5. Apply the decision rule from the preregistration section 7 unchanged. Publish
   `docs/results/2026-09-17-slurp-b2-samples5-verdict.md` with the headline table (base, arm, twin,
   both deltas, anchor column), the saves/harms/ties table against base and twin, the full
   18-scenario table in both weightings, the agreement diagnostics table, the report-only
   sensitivity table and the cost table including measured GPU hours and prompt-cache behaviour.
6. Close the six exposure rows: set `consumed` to `yes` for all six run ids and append to each note
   the actual calls, actual repeated speech seconds, measured GPU hours, the sealed score and
   manifest SHA-256 values, and the verdict.
7. On ADMITTED, add the harness-admission entry for M2 under the `episode` switch class
   (`switch.table` `"episode"`, `switch.key` `native_episode.roles.solver`, `switch.off` the
   historical Solver role — `rails.config_tables.is_episode_null_arm` accepts `null`, or a role with
   `samples` 1 and no `decoding_overrides`/`commit` — and a `switch.proof` test that composes both
   arms), and add the grouped Solver to the default plan. On NEUTRAL it enters the plan only if it
   lowers cost, which at 6 contacts per row against 2 it does not; on HARMFUL it never arms a
   default plan.

## 7. Re-pinning after a readiness flip or a master merge

The composed hash covers the whole merged four-fragment document, so **adding the decision
requirement and flipping readiness both change it**, and with it the protocol hash. The prepared
phase-supply artifact is separate: its identity digest (`core.preparation.artifact_inputs`) pins the
SHA-256 of `rails.kb_policy`, `rails.knowledge_provider`, `rails.phase_supply`,
`rails.knowledge_stores` and `core.flight.runtime`, so once any of those files changes,
`_load_phase_supply_seed` raises *prepared artifact identity mismatch* at dispatch. `readiness` is
stripped by `artifact_inputs` and `prepared_phase_supply` is in `core.preparation._RECEIPT_KEYS`, so
neither a flip nor the pin itself invalidates the artifact.

After any readiness edit, and after merging master if it touches one of those five modules:

```bash
for CELL in slurp-native-samples5-smoke-4-v1 \
            slurp-native-samples5-train-fold-a-v1 \
            slurp-native-samples5-greedy-twin-train-fold-a-v1; do
  case "$CELL" in
    *smoke*) RUN=SAEA-SLURP-NATIVE-SAMPLES5-SMOKE-4-V1 ;;
    *twin*)  RUN=SAEA-SLURP-NATIVE-SAMPLES5-GREEDY-TWIN-TRAIN-FOLD-A-V1 ;;
    *)       RUN=SAEA-SLURP-NATIVE-SAMPLES5-TRAIN-FOLD-A-V1 ;;
  esac
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-supply \
    --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
    --experiment "$CELL" --cell "$CELL" --workers 8 \
    --output "$DATA/prepared/$RUN/phase-supply-v2.json"
  sha256sum "$DATA/prepared/$RUN/phase-supply-v2.json"
done
```

`prepare-supply` refuses to run while `prepared_phase_supply` names a file that does not exist, so
write a **new** version name (`phase-supply-v2.json`) rather than overwriting the pinned v1, then, in
order:

1. write the new relpath and SHA-256 into `prepared_phase_supply` of the three baseline fragments
   and into the `preparation` entry of `cells[0].readiness.requirements` of the three experiment
   fragments;
2. confirm the new artifacts still select what the base selected: the `output` of each full cell's
   artifact must equal the `output` of
   `prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1/phase-supply-v2.json` on all 1,080 rows,
   and the smoke's that of
   `prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1/phase-supply-v2.json` on its 4 (both held at
   `fd882ca8`, `output_sha256` included, and so did the anchor's own
   `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-PREPARE-V1-R2/phase-supply.json`);
3. recompute the composed and protocol hashes with the command in section 1;
4. rewrite the documents in this directory with the new hashes, and the six exposure-ledger notes
   with the new plan SHA-256 values and protocol hashes;
5. re-run `core.flight.cli check` for the three cells and confirm the runtime-derived protocol hash
   equals the registered one again.

Nothing else in this package depends on a merge: the protocol and plan hashes derive from the four
config fragments alone.

## 8. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b2-samples5-v1/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `check-arm-v1.json` | `4be79d8ecb0d11d1c155c5c5a91cd530489dc65bac7a36fd66fd0b7ce58d5d1b` | `core.flight.cli check` passes for the arm: preflight, gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase, and the runtime-derived protocol hash equals the registered `8b28f552…` |
| `check-twin-v1.json` | `962fb9726531bf0aaccf2217abb2dc6e1f7b1c3cc6025d08a2ba7c6d23dfa9e6` | the same for the twin, runtime protocol `e9f8a31e…` |
| `check-smoke-v1.json` | `46d09ad81bcef7866f27e5bfc9285d978c1d64e1491a71c9c2e07fbff02ed02b` | the same for the four-row smoke, runtime protocol `48c2e685…`, 4 samples |
| `request-envelope-comparison-v1.json` | `26b003ab94522f58b2974abbd18152f6854f5b6d3050c9cea5a53a3a4b25e58f` | on 1080/1080 rows and all four phases the rendered request differs from cell B0's only by the 9-byte phase-program id inside the `[agent control …]` marker, for the arm and the twin alike, 0 rows differing otherwise; and the five sibling Solver requests differ from each other only by `seed`, from cell B0's only by `seed` and `temperature` |
| `request-envelope-digests-v1.json` | `d5e6b6948a13601fabfdc726b60c53af753211c9ab336a3dd2d729fa0ad43260` | the per-row, per-phase envelope digests for cell B0, the arm and the twin behind that claim |
| `phase-supply-vs-b0-and-anchor-v1.json` | `c88c8bcbd1b1d2d870a05e2be55fbefb6fb13d9f42d6d6e1846fce4c150f736a` | the rebuilt Perception supply selects the identical facets and values as cell B0's and the anchor's on all 1,080 rows (4/4 for the smoke), `output_sha256` equal |
| `prompt-fit-statement-v1.json` | `30ecab38810e88b1471811fd91b98893557f357336481e8ef4882fbbcbcd289f` | measured prompt fit for exactly B2's two role visits from the anchor's 5,417 sealed fit receipts: `solver:0` at most 13,157 tokens (margin 11,419), `perception:0` at most 4,270 (margin 20,306) |
| `composed-hashes-v1.json` | `c2c953211fdb9506be783131fa22f56a934a21c7111777bee5dac6a83941c5cf` | the composed and protocol hashes for all three cells, the anchor method check, and the cell-B0-versus-arm composed-key diff |
| `plan-hashes-v1.txt` | `a676b6510728e4c322b726ffe165e5607613e8288e22c4fef5775782b6164415` | the SHA-256 of every registered document in this directory (this README excepted, since it cites the file), plus the preregistration, the exposure ledger and every config fragment |
| `ledger-parse-v1.json` | `2dca65aae15ed378387a0488eebde90edab788653398315ee49d8bc9b99f82bc` | `contracts._parse_ledger_tables` sees all six rows exactly once, each `consumed = no`, 860 rows and 860 distinct run ids parsed in total |
| `prepare-supply-arm-v1.json` | `8a08777a86f15f65df0eced216897b1646a003c9de7c07fa4630d3b196349b6c` | the model-free supply preparation receipt for the arm (`contact_class: model-free`, 9.95 s at 8 workers) |
| `prepare-supply-twin-v1.json` | `4cd429e26e2704ff866e06fed4ffd069bb71b6bfd3d738a512dc8da2fe479e2b` | the same for the twin (6.71 s) |
| `prepare-supply-smoke-v1.json` | `464b6656df248929e7f4d045feda4f704da7c5feb74730fbc16842963d3ae95a` | the same for the smoke (11.30 s) |
| `wire-check-smoke-v1.stderr.txt` | `b9cc6d2123be9868ca33cb1a825c0d92d494178a39fce8f68dda35bca548a082` | why no cell declares the `wire-check` stage: `cell … does not permit execution stage wire-check` |

Prompt fit against the 24,576-token slot. Model-free estimate from `core.flight.cli check` over the
widest request each phase renders across the whole roster: Perception 19,184 required window tokens
(operational margin 5,392), Reviewer 19,048 (5,528), Planner 18,987 (5,589), Solver 19,227 (5,349);
decision ALLOW for every phase. That estimate unions every candidate envelope and is deliberately
conservative. Measured, from the anchor's sealed fit receipts for exactly the two visits this cell
renders: `perception:0` at most 4,270 tokens (minimum margin 20,306) and `solver:0` at most 13,157
tokens (minimum margin 11,419), 1,080 contacts each, all fitting.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double (cell B0's own
`wire-check-smoke-v2.stderr.txt` records that refusal verbatim). These three cells therefore do not
declare the stage at all, so the CLI refuses earlier, at the cell's `allowed_execution_stages`
policy. The row-for-row envelope comparison above is the contact-free substitute and is stronger per
row.

Do not re-run `derived_media_confinement_check.py` from inside the checkout without reverting its
in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
dirty the tree the manifest reads at finalize.

## 9. Gates run on this branch

`scripts/checks/engineering_base_check.py` PASS; `scripts/checks/results_ledger_check.py` PASS
(53 rows, 66 run ids registered and closed, 142 cited paths present, 38 pre-existing findings
reported, none introduced here); `scripts/checks/harness_admission_check.py` PASS (4 modules, 3
barred from every default plan, 1 default plan — M2 has no entry yet and must not have one before a
verdict).

## 10. Deviations the coordinator should know about

1. **The E2b fragments were behind master in three ways, and are brought into line here.** The
   committed `configs/baseline/slurp-native-dual-store-train-fold-a-review-off-samples5-v1.json` and
   its greedy twin (a) omit the anchor's `phase_tools` block, which
   `FlightRuntime.frozen_core_client_kwargs` needs as the schema source for the
   `speech-feature-query-native-tools` arm (the empty-tuple escape hatch covers only
   `raw-speech-agent-native-tools`), so the fragment could not build a client at all; (b) omit the
   E6 `native_episode.review_loop "off"` marker that cell B0's baseline carries; and (c) still pin
   `prepared_phase_supply` to the anchor's
   `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-PREPARE-V1-R2/phase-supply.json`, which cannot
   load under this composed config. Apart from those three and the run identities, they are
   byte-identical to the review-off baseline; the diff is recorded in `composed-hashes-v1.json`. The
   three new baselines restore the `phase_tools` block verbatim (inert: the review-off graph builds
   no Reviewer node, so the declared task-contract authority is unreachable, and keeping it holds the
   tool block of every request identical to cell B0's), carry `review_loop "off"`, and pin their own
   freshly prepared supply. **The E2b fragments themselves are left untouched**; they are the
   engineering item's own artifacts and no cell points at them.
2. **Experiment and run names drop `review-off`; baseline names keep it.** The run ids are the ones
   the coordinator specified (`SAEA-SLURP-NATIVE-SAMPLES5-…`) and the experiment fragments follow
   them; the baseline fragment names keep `review-off` to record which base they extend. This is
   cell B1's convention.
3. **A separate smoke baseline fragment exists.** `native_contact_fit` carries the FIT run identity
   and the endpoint ceiling, which `build_native_contact_fit_gate` requires to equal
   `rows * max_contacts * (packets + 3)`. Sharing the arm's fragment would have charged smoke
   contacts to the arm's FIT row. The smoke baseline deliberately **shares the arm's speech-feature
   key and matcher identity**, exactly as cell B0's smoke shares cell B0's, so the four smoke rows
   render the arm's own requests byte for byte.
4. **The registered envelope difference is 9 bytes, not 0.** The coordinator's brief expected the
   Perception request to be byte-identical to cell B0's. It cannot be: the `[agent control …]`
   marker carries the phase-program id, and the grouped cell needs its own policy fragment because
   `max_contacts` must equal the graph ceiling. The difference is exactly the substitution
   `phase-native-candidates-solve-v1` -> `phase-native-candidates-solve-samples5-v1` on every phase
   of every row, with zero rows differing otherwise — the same shape and the same cause as cell B0's
   own 8-byte difference from the anchor. Two further dispatch-time differences are recorded in
   preregistration section 3: the episode-limits epilogue's `remaining_model_contacts` reads 5
   instead of 1, and the real `agent_contact_id` carries the per-sample invocation index
   `solver:0 … solver:4`.
5. **The 5.0 GPU-hour ceiling rests on an unproven prompt-cache assumption.** See preregistration
   section 8 and the smoke instructions in section 3 above. The measured GPU hours are a mandatory
   verdict field.
6. **Readiness carries the preparation requirement but not the decision requirement.** The
   coordinator adds the decision entry and flips, and re-pins the hashes afterwards (section 7).
7. **Registered hashes are pre-flip.** Section 1.
8. **No production code was changed and nothing was merged into master.** This branch is
   `fable/b2-prep` at `fd882ca8`, based on master `6c5c9ab7`.

## 11. Open decisions for the coordinator

1. **The base.** Cell B0 is HARMFUL as read once; its registered own-null replicate and
   re-decision rule are what settle whether cell B2 sits on B0 or on the sealed anchor. This package
   is registered on B0, which is where the spec's order (B0 -> B1 -> B2) puts it and what the
   coordinator's brief specified. Re-basing on the anchor is a new registration, not an edit:
   see checklist step 3.
2. Whether to re-price the 5.0 GPU-hour ceiling after reading the smoke's prompt-cache behaviour,
   before launching the arm. Re-pricing the ceiling upward is a plan change and needs a new
   registration; re-pricing it downward does not.
3. Whether the twin flies immediately after the arm or after the arm's paired read. The
   preregistration requires both before the verdict, and one cell in flight at a time; the order
   inside that constraint is the coordinator's.


## 12. Superseded before contact (2026-09-17)

**This package is superseded and must not be flown.** Cell B0 (module M0, the review loop off) was
re-decided **HARMFUL** under the TRAIN A own null — the first-pass verdict
`docs/results/2026-09-17-slurp-b0-review-off-verdict.md` and the B0r own-null re-decision read
`analysis/SAEA-SLURP-B0-REPLICATE-PAIRED-ANALYSIS-V1/README.md`, under owner decision 6 of
2026-09-17 — so cell B2 builds on the sealed dual-store anchor, not on cell B0. The replacement
registration is
[`../2026-09-17-slurp-b2-samples5-anchor-v2-preregistration.md`](../2026-09-17-slurp-b2-samples5-anchor-v2-preregistration.md)
with its runbook [`../2026-09-17-slurp-b2-samples5-anchor-v2/README.md`](../2026-09-17-slurp-b2-samples5-anchor-v2/README.md).

The three cells registered here never flew. Their six exposure rows stay `consumed = no` and each
now carries a supersession note. The configs, plans and protocol of this package are left in place
unchanged as the audit record of what was registered on the review-off base; nothing in it is
edited, and the open decision 1 of section 11 above is answered by the re-decision.
