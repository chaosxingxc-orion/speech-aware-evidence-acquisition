# Cell B0r launch runbook: the own-null replicate of cell B0

Everything the coordinator needs to fly cell B0r is in this directory and in the committed configs.
**One step remains: the full campaign.** No smoke is registered — section 5 says why, and the
preregistration says it in full. Preregistration:
[`../2026-09-17-slurp-b0-replicate-v1-preregistration.md`](../2026-09-17-slurp-b0-replicate-v1-preregistration.md).

The preparation agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts** and
never started, stopped or queried the resident service. No other worktree was modified.

## 1. What is registered

| item | value |
| --- | --- |
| cell | experiment and cell `slurp-native-review-off-train-fold-a-replicate-v1`, run `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1`, attempt `attempt-slurp-native-review-off-train-fold-a-replicate-generation-v1` |
| FIT | `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-FIT-V1` / `attempt-slurp-native-review-off-train-fold-a-replicate-fit-v1`, 8,640 endpoints, inside the same campaign |
| campaign plan | `configs/campaign/slurp-native-review-off-train-fold-a-replicate-v1.json` |
| composed config / protocol | `086b6387de1f5ef9afb4d86f7f90058c753f3fea78d9ed1ee3ea9ea960f3018a` / `6f1d8dc0120b5f87442ac0d48eb0ca63656603222326df13b159673fe05e7d48` |
| prepared phase supply | `prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1/phase-supply-v3.json`, SHA-256 `052acd26f790a4e1af04a0c0a10dcc86bfaede1f208819b11ec53097edb1fccf`, output SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| budgets | 2,160 generation calls, 8,640 FIT endpoints, 6,170 repeated speech seconds, 2.0 fit-inclusive GPU hours, one official complete score |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | `held`, carrying the preparation requirement only; **the coordinator adds the decision requirement and flips it** |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-dual-store-train-fold-a-review-off-replicate-v1",
            "slurp-native-review-off-train-fold-a-replicate-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The method is verified: run it on the anchor fragments and it returns the anchor's registered
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`, exactly as cell B0's own
registration package verified it.

**Cell B0's own `45fe779f` no longer reproduces from master's bytes**, and section 7 isolates the
single key that explains it. Read section 7 before reading anything else in this package as a
discrepancy.

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
6. Add the root decision requirement to
   `configs/experiment/slurp-native-review-off-train-fold-a-replicate-v1.json`
   (`cells[0].readiness.requirements`), flip `readiness.state` from `held` to `ready`, and commit
   the flip — because step 1 must still hold at launch. Then re-run `check` (section 3) and confirm
   the runtime-derived protocol hash still equals the registered one; **flipping readiness and
   adding a requirement both change the composed config hash**, so the plan documents, the two
   ledger notes and this table must be re-pinned in the same commit. Master has already moved past this
   branch's base, so do this as the single re-pin cycle of section 10, not twice.

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

## 3. The pre-flight check

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-review-off-train-fold-a-replicate-v1 \
  --cell slurp-native-review-off-train-fold-a-replicate-v1
```

Contact-free. It opens the gate, re-checks the exposure row, asserts a clean tree, confirms the
attempt is free, and assesses the prompt budget for every phase. `generation_authorized` is always
`false`; the readiness state it reports is whatever the fragment declares.

## 4. The full campaign — the only contact step

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-review-off-train-fold-a-replicate-v1.json" \
  --owner root-slurp-native-review-off-train-fold-a-replicate-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

The campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation, seals the manifest and schedules the single official score at
finalize through `core.scoring_batch`. Do not run `coordinate-fit`: the native gate fits every
request itself, and a standalone fit would double-charge the FIT row.

Expected, from cell B0's own realized figures: 2,160 contacts at 2 per row, 6,169.06 repeated
speech seconds, 8,640 FIT endpoints, about 1.05 GPU hours and about 3,950 s of generation wall
clock, plus about 165 s of official scoring. Ceilings are 2,160 / 6,170 / 8,640 / 2.0 and are
bounds, not targets. Nothing else may occupy the GPU while this flies, and CPU work runs at 8
workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for the lease window from that file;
they are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means
a CPU-only step, not a hang.

## 5. No smoke, deliberately

Cell B0's package flew a four-row smoke first. This one does not, for a reason that is itself
pre-contact evidence: **the request bytes of this cell are cell B0's own**, byte-identical on
1,080/1,080 rows and all four declared phases (section 6, and preregistration section 3.1), and
B0's smoke `SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1` already sealed the structural form of exactly
this episode: 8 contacts, 2 per row, no Reviewer or Planner contact,
`review_loop_disposition = skipped_by_configuration` on every row, one `*.request-fit.json` per
realized contact with `every_request_fits = true`. Re-flying it would spend contacts to re-learn a
recorded fact, and would put four of this roster's rows through a second batch composition before
the measurement this cell exists to make.

The structural assertions still hold at the campaign's own seal, and the coordinator checks them
there: exactly 2,160 contacts, no Reviewer or Planner contact in the trace,
`review_loop_disposition = skipped_by_configuration` on every row, and 8,640 fit receipts all
carrying `every_request_fits = true`.

## 6. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b0-replicate-v1/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `prepare-supply-v1.json` | `cbd9016d89ca217d0170c465e41691b250c14baef8119135a215022147f0e8bf` | the model-free supply preparation receipt for this cell, `contact_class = model-free` |
| `phase-supply-vs-b0-and-anchor-v1.json` | `1647ea99113bd2e56763ae70012a1904eac084f410e76e9117eb3b5e1621d401` | the rebuilt Perception supply selects the identical values as cell B0 and as the sealed anchor on every one of the 1,080 rows; all three artifacts share the output digest `ba5e1faa...` |
| `composed-hashes-v1.json` | `8c9c30ab630f13999cde6de878c268dcf12a42b87498242350542a87c53d4c15` | the composed and protocol hashes, the method verification against the anchor's registered `d1c61c09`, and the exact B0-versus-B0r composed-key diff |
| `request-envelope-comparison-v1.json` | `b4f742c42eced2c87ab5d21ca05e0748822ce86ec4b26d71bcb1faa52f0f5167` | on 1,080/1,080 rows and all four phases the rendered request is byte-identical to cell B0's — including the `[agent control ...]` marker — in all three pairings, with a rendered byte delta of exactly 0 |
| `request-envelope-digests-b0r-v1.json` | `62c74b0548c1481b6c29790d502c951ba751c26a5934fa8dfb5e1474f80ca539` | the per-row, per-phase envelope digests of this cell |
| `request-envelope-digests-b0-master-v1.json` | `8f66c84235aeac0c4079cd99443378ebd46019dd58134ca6341171dd480e8395` | the same for cell B0 as committed on this master |
| `request-envelope-digests-b0-asflown-v1.json` | `b1b8ba98ca257fd9cc5fe813f9d8ae158bbff42ecbe984afcf2bcc0156131534` | the same for cell B0 **as flown**, rendered from the `5d0d694d` worktree, which reproduces B0's registered `45fe779f` / `c445394b` |
| `plan-hashes-v1.txt` | `05d47505b9e709c995915bca406444a1301d0f5fec7891de4f731ed5d18bc079` | the SHA-256 of every plan and protocol document in this directory |
| `ledger-parse-v1.json` | `0dde3f137b40f46973e4c34546d5b0eadf576608a9301b9449aa1896c54574c9` | `contracts._parse_ledger_tables` sees both rows exactly once, each `consumed = no` |
| `check-v1.json` | `df09ac5be6557781ef2030377189207039abbc0a4070ca1d8f67786fa1c75858` | `core.flight.cli check` passes: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase |

The `check` receipt was produced at commit `43ede91c33e349eaba9e982c5a012300a5c7288f`, the registration commit that carries
every config, plan and ledger row this cell flies; the documentation commit that follows it changes
no config, no plan and no ledger row.

Do not re-run `derived_media_confinement_check.py` from inside the checkout without reverting its
in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
dirty the tree the manifest reads at finalize.

Prompt fit against the 24,576-token slot, model-free, over the widest request each phase renders
across the whole roster: Perception 19,182 required window tokens (operational margin 5,394),
Solver 19,225 (5,351), Reviewer 19,045 (5,531), Planner 18,985 (5,591); decision ALLOW everywhere.
These are cell B0's own numbers to the token. Measured, from the anchor's sealed fit receipts for
exactly these two contacts: `perception:0` at most 4,270 tokens (minimum margin 20,306) and
`solver:0` at most 13,157 tokens (minimum margin 11,419), 1,080 contacts each, all fitting.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. Cell B0 and the sealed
anchor declare the same four stages for the same reason. The row-for-row envelope comparison above
is the contact-free substitute and is stronger per row.

## 7. Cell B0's `45fe779f` does not reproduce on master — isolated

Commit `ad04a26c` (merged as `dd83963e`), landed **after** cell B0 flew at `5d0d694d`, added one
key to B0's baseline fragment: `native_episode.review_loop: "off"`, part of the harness-admission
switch classes. That single key moves B0's composed config hash from `45fe779f` to `821d6839` and
its protocol hash from `c445394b` to `b71400cb`. Nothing else in B0's four fragments changed, and
its experiment fragment did not change at all: reverting only that key to its `5d0d694d` bytes
reproduces `45fe779f` and `c445394b` on this master, to the digit.

The marker is inert by construction. Its own commit message calls it "a checked redundant
declaration": `rails.native_episode_config.load_native_episode_config` derives
`review_loop_enabled` from the three authoritative leaves (`max_revisions`,
`roles.reviewer.max_iterations`, `roles.planner.max_iterations`) and **refuses** a marker that
disagrees with them. Section 6's third envelope pairing is the empirical proof: cell B0 rendered
from the `5d0d694d` worktree and cell B0 rendered on this master produce byte-identical requests on
1,080/1,080 rows in all four phases.

Cell B0r inherits the marker, which is the right choice: it keeps the replicate on the current
harness convention and on the switch class M0's admission entry will point at, while changing no
byte the core sees.

## 8. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the
   official score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` for `b0r_replicate` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that
   recipe pins it: `analysis.null_calibration_cli.rows_for` to read all three sealed score
   registries, `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner.
   Write `analysis/SAEA-SLURP-B0-REPLICATE-OWN-NULL-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}`.
3. **Stop if the recomputed `(B0 minus anchor)` contrast does not reproduce the first pass's CI95
   lower bounds `-1.150048` (pooled SLU) and `-1.527335` (intent) to the digit.** The same sealed
   bytes under the same estimator and seed cannot give two answers.
4. Apply the decision rule from the preregistration section 6 unchanged. Publish
   `docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md` with the own-null table, the
   clause table, the saves/harms/ties table, the full 18-scenario table in both weightings, the
   row-identity diagnostic and the cost table. The first-pass verdict
   `docs/results/2026-09-17-slurp-b0-review-off-verdict.md` stays on record beside it, as the
   KC-E1f v1/v2 pair does.
5. Close the two exposure rows: set `consumed` to `yes` for
   `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1` and
   `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-FIT-V1`, and append to each note the actual
   calls, actual repeated speech seconds, measured GPU hours, the sealed score and manifest SHA-256
   values, and the re-decision verdict.
6. On NEUTRAL, add the harness-admission entry for M0, drop the review loop from the default plan,
   and let cells B1, B2, B4a and B4b build on B0. On HARMFUL, later cells build on the sealed
   anchor and the loop stays.

## 9. Deviations the coordinator should know about

1. **No smoke.** Section 5. The request bytes are B0's, proved row for row; B0's own smoke is the
   structural receipt this cell cites.
2. **A separate baseline fragment exists.** `native_contact_fit` carries the FIT run identity and
   the endpoint ceiling, so sharing cell B0's fragment would have charged this cell's contacts to
   B0's FIT row. Only three keys differ from B0's baseline: the two fit identities and the
   prepared-supply pin (plus the `what_this_is` prose).
3. **The speech-feature identity strings are held at B0's values.** Cell B2 mints its own pair
   because B2 changes the arm; a replicate that renamed them would not be a replicate. They are
   provenance only (`core.model.transport` validates and drops them; they never enter the rendered
   `messages`), and fit receipts are namespaced by the FIT run and attempt id, so holding them
   cannot collide.
4. **The prepared Perception supply was rebuilt.** `core.preparation.artifact_inputs` binds the
   composed values and the rails/core module digests, both of which moved since B0 flew. The
   rebuild is model-free and selects identically — same output digest as B0's and the anchor's.
5. **`allowed_execution_stages` still declares `worker`**, mirroring cell B0's fragment. This cell
   flies through `campaign`; the stage is declared for parity with B0, not to authorize a
   standalone worker.
6. **Cell B0's registered composed hash does not reproduce on master.** Section 7, isolated to one
   inert key, with the envelope proof beside it.

## 10. If master moves before launch (it already has)

This branch is based on `6c5c9ab7`. While it was being prepared, another session merged cell B2's
registration, the E3b store-router fix and cell B0's own first-pass verdict onto master
(`d62bfa8d`).

The registered **protocol and plan hashes survive that merge**: they derive from the four config
fragments only, and `core.config.compose`'s own change in that range
(`assert_preparation_source_receipts_are_well_formed`) is a pure load-time validator that adds
nothing to `_canonical_hash`'s input — this cell's `preparation_source_receipts` all pin
`"root": "data"` and already pass it. The **prepared phase-supply artifact does not survive it.**
Its identity digest (`core.preparation.artifact_inputs`) pins the SHA-256 of `rails.kb_policy`,
`rails.knowledge_provider`, `rails.phase_supply`, `rails.knowledge_stores` and
`core.flight.runtime`, and commit `d8d8844b` changes `rails/knowledge_stores.py`. Once it does,
`_load_phase_supply_seed` raises *prepared artifact identity mismatch* at dispatch.

So the readiness flip of section 2 item 6 and the master merge are **one re-pin cycle**, in this
order:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-supply \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-review-off-train-fold-a-replicate-v1 \
  --cell slurp-native-review-off-train-fold-a-replicate-v1 --workers 8 \
  --output "$DATA/prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1/phase-supply-v3.json"
sha256sum "$DATA/prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1/phase-supply-v3.json"
```

1. merge master into this branch;
2. re-run `prepare-supply` as above — **remove `prepared_phase_supply` from the baseline fragment
   first**, because `core.flight.runtime._phase_supply_seeds` short-circuits to
   `_load_phase_supply_seed` whenever that key is present and would re-verify the stale pin instead
   of rebuilding;
3. **confirm the new artifact still selects what cell B0 selected**: its `output_sha256` must still
   be `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`, the digest cell B0's
   artifact and the sealed anchor preparation both carry. If it moves, the merge changed the
   knowledge channel and this is no longer a replicate — **stop and report**;
4. write the new relpath and SHA-256 into `prepared_phase_supply` of
   `configs/baseline/slurp-native-dual-store-train-fold-a-review-off-replicate-v1.json` and into
   `cells[0].readiness.requirements[0]` of the experiment fragment;
5. add the root decision requirement and flip `readiness.state` to `ready`;
6. recompute the composed and protocol hashes with the command in section 1 — **re-pinning and the
   readiness flip both change the composed config hash**, because `compose` hashes the whole merged
   fragment set;
7. rewrite the hashes in this file, in the preregistration section 2, in the four plan documents and
   the protocol document, and in the two exposure-ledger notes;
8. re-run `check` and confirm the runtime-derived protocol hash equals the newly registered one;
9. re-run the envelope comparison against cell B0 as flown if any of the five identity-bearing
   modules changed how a request renders. `rails/knowledge_stores.py` is one of them, so on this
   particular merge, do re-run it: 1080/1080 rows must still be byte-identical.

Nothing else in this package depends on the merge.
