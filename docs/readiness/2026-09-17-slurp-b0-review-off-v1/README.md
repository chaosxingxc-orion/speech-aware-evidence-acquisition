# Cell B0 launch runbook: the review-loop-off ablation

Everything the coordinator needs to fly cell B0 is in this directory and in the committed configs.
Only two steps remain: the four-row smoke, then the full campaign. Preregistration:
[`../2026-09-17-slurp-b0-review-off-v1-preregistration.md`](../2026-09-17-slurp-b0-review-off-v1-preregistration.md).

The preparation agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts** and
never started, stopped or queried the resident service.

## 1. What is registered

| item | value |
| --- | --- |
| full cell | experiment and cell `slurp-native-review-off-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-review-off-train-fold-a-generation-v1` |
| full FIT | `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-review-off-train-fold-a-fit-v1`, 8,640 endpoints, inside the same campaign |
| smoke cell | experiment and cell `slurp-native-review-off-smoke-4-v1`, run `SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1`, attempt `attempt-slurp-native-review-off-smoke-4-generation-v1` |
| smoke FIT | `SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-FIT-V1` / `attempt-slurp-native-review-off-smoke-4-fit-v1`, 32 endpoints |
| campaign plan | `configs/campaign/slurp-native-review-off-train-fold-a-v1.json` |
| composed config / protocol (full) | `45fe779f75694774a5e8f313a6682da5f70531c6e810554b6cd1a06c734400d1` / `c445394b3c5560e07d4b1bf22b520297514456f88ca50d7293bb265f6090a7e6` |
| composed config / protocol (smoke) | `d241dd7e76608184f9db83153008f9dbf4a5cb9f3e555c0bdf750923f2e43ed5` / `b3a751293e64abf36dece4b51f1161c75f2c23f89937c1b63cc5137238e4bc8d` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | both cells are `held`; the coordinator flips them |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-dual-store-train-fold-a-review-off-v1",
            "slurp-native-review-off-train-fold-a-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with the two smoke fragment names and split identity
`4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` reproduces the smoke pair. The
method is verified: run it on the anchor fragments and it returns the anchor's registered
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

## 2. Pre-launch checklist

1. `git -C "$REPO" status --porcelain` is empty. A COMPLETED manifest reads `study_commit` at
   finalize and refuses a dirty tree, so the checkout stays clean for the whole run. No receipt
   from this preparation lives inside the repository.
2. No flight process is running and no `locks/flight.lock` is held in the data root.
3. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
4. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
5. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
6. Flip `readiness.state` from `held` to `ready` in
   `configs/experiment/slurp-native-review-off-smoke-4-v1.json` first, and in
   `configs/experiment/slurp-native-review-off-train-fold-a-v1.json` only after the smoke seals.
   Commit each flip, because step 1 must still hold at launch.

Shell prelude used by every command below:

```bash
export REPO=<the clean checkout carrying this registration>
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
  --experiment slurp-native-review-off-smoke-4-v1 \
  --cell slurp-native-review-off-smoke-4-v1 \
  --owner root-slurp-native-review-off-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-review-off-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-review-off-smoke-4-v1 \
  --cell slurp-native-review-off-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-review-off-smoke-4-v1.worker-lease.json"
```

Expected: about 1 to 2 minutes of wall clock, 8 generation contacts, 32 FIT endpoints, about 21.2
repeated speech seconds, no scorer. Accept only if all four hold:

- exactly 8 contacts, 2 per row, and no Reviewer or Planner contact in the trace;
- the episode receipt carries `review_loop_disposition = skipped_by_configuration` on every row;
- one `*.request-fit.json` per realized contact under
  `$DATA/prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-FIT-V1/attempt-slurp-native-review-off-smoke-4-fit-v1/`,
  every one with `every_request_fits = true`;
- the worker prints a seal and the tree is still clean.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops cell B0 until the fix is proven on this same four-row roster.

## 4. Step two: the full campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-review-off-train-fold-a-v1.json" \
  --owner root-slurp-native-review-off-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

The campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation, seals the manifest and schedules the single official score at
finalize through `core.scoring_batch`. Do not run `coordinate-fit`: the native gate fits every
request itself, and a standalone fit would double-charge the FIT row.

Expected: 2,160 contacts at 2 per row and 6,169.06 repeated speech seconds against ceilings of
2,160 and 6,170. On the anchor's np4 geometry, 5,417 contacts cost about 3.46 GPU hours, so 2,160
contacts should land near 1.4 GPU hours of generation; the registered fit-inclusive ceiling is 2.0.
Budget roughly 1.5 to 2 hours of wall clock for generation plus about 3 minutes of official
scoring. Nothing else may occupy the GPU while this flies, and CPU work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for the lease window from that file;
they are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means
a CPU-only step, not a hang.

## 5. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the
   official score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that
   recipe pins it: `analysis.null_calibration_cli.rows_for` to read both sealed score registries,
   `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner.
   Write `analysis/SAEA-SLURP-B0-REVIEW-OFF-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}`.
3. Apply the decision rule from the preregistration section 6 unchanged. Publish
   `docs/results/2026-09-17-slurp-b0-review-off-verdict.md` with the headline table, the
   saves/harms/ties table, the full 18-scenario table in both weightings, and the cost table.
4. Close the four exposure rows: set `consumed` to `yes` for
   `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1`,
   `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-FIT-V1`,
   `SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1` and `SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-FIT-V1`,
   and append to each note the actual calls, actual repeated speech seconds, measured GPU hours,
   the sealed score and manifest SHA-256 values, and the verdict.
5. On NEUTRAL or better, add the harness-admission entry for M0 and drop the review loop from the
   default plan, then open cell B1 on top of B0. On HARMFUL, later cells build on the sealed
   anchor and the loop stays.

## 6. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b0-review-off-v1/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `check-full-v1.json` | `b9865b75695a34f40674041e7116d1da399c4755eb15b597ab679ba9365d4308` | `core.flight.cli check` passes for the full cell: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase |
| `check-smoke-v1.json` | `d23fe385702cbc4c41c61172fce0f7a4f284c563733fa41d16ed9841f788c332` | the same for the four-row smoke |
| `request-envelope-comparison-v1.json` | `344200f727d0d112bf59bbb5aac80763df36bdd8e8de0cb8f52870c0a208bd14` | on 1080/1080 rows and all four phases the rendered request differs from the anchor's only by the phase-program id inside the `[agent control ...]` marker, 8 bytes |
| `request-envelope-digests-v1.json` | `74274883d45e91ea6dfa329866e937dd6b26587aa0740da804a34edb8d5362f8` | the per-row, per-phase envelope digests behind that claim |
| `phase-supply-vs-anchor-v1.json` | `aa7e2171b9a6aa75173ffe9ca3961ea0e528080f2722c089e3561b2b336ec288` | the rebuilt Perception supply selects the identical facets and values as the anchor on every row |
| `anchor-fit-token-stats-v1.json` | `1eb2352b947942fe0414f124a7c4abc37a54daf36a309ef9e4fc23b309e44b67` | measured prompt fit for exactly B0's two roles from the anchor's 5,417 sealed fit receipts |
| `composed-hashes-v1.json` | `ee8bcda4c110354151e672f04b37547543eeaa9d15774a8f0c44b2db56fac3d6` | the composed and protocol hashes, and the anchor-versus-B0 composed-key diff |
| `plan-hashes-v1.txt` | `64fba18d2cccee0122e3fed71d669ec955c438e07403a1be8ef64c4ee5ff2544` | the SHA-256 of every plan document in this directory |
| `ledger-parse-v1.json` | `8d7b344a60a32b7a99a512a72ba7285d4e0338619a58f7075a07f4ab13dbb969` | `contracts._parse_ledger_tables` sees all four rows exactly once, each `consumed = no` |
| `prepare-supply-full-v1.json` | `5b4abe41b51e866ee9684cddcec543ce267ca2aa247d27e23b64772e0b14bd77` | the model-free supply preparation receipt for the full cell |
| `prepare-supply-smoke-v1.json` | `14e7aafc00a5a56666b2e1101b5e984ddaa7b295ef64db7f13163a1fa2a3d5d8` | the same for the smoke |
| `wire-check-smoke-v2.stderr.txt` | `db3849fd2c87040e1130e6eaa42a79046625fba3aad02468d8776c46eaead0c9` | why neither cell declares the `wire-check` stage |

Both `check` receipts were produced at commit `d04d389e`, the registration commit that carries every config, plan and ledger row this cell flies; the documentation commit that follows it changes no config, no plan and no ledger row. Do not re-run `derived_media_confinement_check.py` from inside the checkout without reverting its in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would dirty the tree the manifest reads at finalize.

Prompt fit against the 24,576-token slot. Model-free estimate over the widest request each phase
renders across the whole roster: Perception 19,182 required window tokens (margin 5,394), Solver
19,225 (margin 5,351), decision ALLOW. Measured, from the anchor's sealed fit receipts for exactly
these two contacts: `perception:0` at most 4,270 tokens (minimum margin 20,306) and `solver:0` at
most 13,157 tokens (minimum margin 11,419), 1,080 contacts each, all fitting.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. The sealed anchor cell
declares the same four stages for the same reason. The row-for-row envelope comparison above is
the contact-free substitute and is stronger per row.

## 7. If master moves before launch (it already has)

This branch is based on `fe140d4f`. While it was being prepared, another session merged E5b, A1,
E5a and E3 onto master (`93060eb6`), and that merge touches
`src/speech_aware_evidence_acquisition/rails/knowledge_provider.py` and
`rails/knowledge_stores.py`.

The registered **protocol and plan hashes survive a merge**: they are derived from the four config
fragments only. The **prepared phase-supply artifact does not**. Its identity digest
(`core.preparation.artifact_inputs`) pins the SHA-256 of `rails.kb_policy`,
`rails.knowledge_provider`, `rails.phase_supply`, `rails.knowledge_stores` and
`core.flight.runtime`, so once any of those files changes, `_load_phase_supply_seed` raises
*prepared artifact identity mismatch* at dispatch.

After merging master into this branch, and before flipping readiness, re-pin both supplies:

```bash
for CELL in slurp-native-review-off-smoke-4-v1 slurp-native-review-off-train-fold-a-v1; do
  case "$CELL" in
    *smoke*) RUN=SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1 ;;
    *)       RUN=SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1 ;;
  esac
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-supply     --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK"     --experiment "$CELL" --cell "$CELL" --workers 8     --output "$DATA/prepared/$RUN/phase-supply-v2.json"
  sha256sum "$DATA/prepared/$RUN/phase-supply-v2.json"
done
```

Then, in order:

1. write the new relpath and SHA-256 into `prepared_phase_supply` of
   `configs/baseline/slurp-native-dual-store-train-fold-a-review-off-v1.json` and
   `configs/baseline/slurp-native-review-off-smoke-4-v1.json`, and into
   `cells[0].readiness.requirements[0]` of both experiment fragments;
2. confirm the new artifacts still select what the anchor selected: the `output` of the full cell's
   artifact must equal the `output` of
   `prepared/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-PREPARE-V1-R2/phase-supply.json`
   (it did at `fe140d4f`, on all 1,080 rows);
3. recompute the composed and protocol hashes with the command in section 1 -- **re-pinning changes
   the composed config hash**, because `compose` hashes the whole merged fragment set;
4. rewrite the nine documents in this directory with the new hashes, and the four exposure-ledger
   notes with the new plan SHA-256 values and protocol hash;
5. re-run `core.flight.cli check` for both cells and confirm the runtime-derived protocol hash
   equals the registered one again.

Nothing else in this package depends on the merge.

## 8. Deviations the coordinator should know about

1. **`phase_tools` restored.** The E1 fragment as merged removed the anchor's `phase_tools` block.
   The arm `speech-feature-query-native-tools` declares `tool_schemas`, and
   `FlightRuntime.frozen_core_client_kwargs` has no schema source for it once `phase_tools` is
   absent (the empty-tuple escape hatch covers only `raw-speech-agent-native-tools`), so the
   fragment could not build a client at all. The anchor block is restored verbatim; it is inert,
   because the review-off graph builds no Reviewer node, and keeping it also holds the tool block
   of every request identical to the anchor's.
2. **The FIT run identity moved.** The E1 fragment named its FIT run
   `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-REVIEW-OFF-FIT-V1`; it is now
   `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-FIT-V1`, matching this cell's registered run ids.
3. **A separate smoke baseline fragment exists.** `native_contact_fit` carries the FIT run identity
   and the endpoint ceiling, which `build_native_contact_fit_gate` requires to equal
   `rows * max_contacts * (packets + 3)`. Sharing the full cell's fragment would have charged smoke
   contacts to the full cell's FIT row.
4. **No `wire-check` stage** on either cell, for the reason in section 6.
5. **The prepared Perception supply was rebuilt.** The anchor's artifact binds the anchor's composed
   config and cannot load under this one; the rebuild is model-free and selects identically.
