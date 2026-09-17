# Cell B2 launch runbook: sample-and-aggregate commit on the sealed anchor, N = 5 at T = 0.7

Everything the coordinator needs to fly cell B2, its greedy-repeat twin and its four-row smoke is in
this directory and in the committed configs. **Three steps remain: re-pin with the decision
requirement and the readiness flip, fly the smoke, then the arm, then (only on a positive arm CI95)
the twin.** Preregistration:
[`../2026-09-17-slurp-b2-samples5-anchor-v2-preregistration.md`](../2026-09-17-slurp-b2-samples5-anchor-v2-preregistration.md).

The re-base agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**, never
started, stopped or queried the resident service, and never touched another worktree.

**This package replaces the review-off-based v1 package**
(`docs/readiness/2026-09-17-slurp-b2-samples5-v1/`), which is superseded before contact: cell B0 was
re-decided HARMFUL under the TRAIN A own null (owner decision 6 of 2026-09-17), so cell B2 sits on
the sealed dual-store **anchor**. The v1 cells never flew, their six exposure rows keep
`consumed = no`, and the v1 README and each of the six notes carry a supersession line. Do not fly
the v1 cells.

## 1. What is registered

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-samples5-anchor-train-fold-a-v2`, run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V2`, attempt `attempt-slurp-native-samples5-anchor-train-fold-a-generation-v2` |
| arm FIT | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-FIT-V2` / `attempt-slurp-native-samples5-anchor-train-fold-a-fit-v2`, 82,080 endpoints, inside the same campaign |
| twin cell | experiment and cell `slurp-native-samples5-anchor-greedy-twin-train-fold-a-v2`, run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-V2`, attempt `attempt-slurp-native-samples5-anchor-greedy-twin-train-fold-a-generation-v2` |
| twin FIT | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-FIT-V2` / `attempt-slurp-native-samples5-anchor-greedy-twin-train-fold-a-fit-v2`, 82,080 endpoints |
| smoke cell | experiment and cell `slurp-native-samples5-anchor-smoke-4-v2`, run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V2`, attempt `attempt-slurp-native-samples5-anchor-smoke-4-generation-v2` |
| smoke FIT | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-FIT-V2` / `attempt-slurp-native-samples5-anchor-smoke-4-fit-v2`, 304 endpoints |
| campaign plans | `configs/campaign/slurp-native-samples5-anchor-train-fold-a-v2.json`, `configs/campaign/slurp-native-samples5-anchor-greedy-twin-train-fold-a-v2.json` |
| policy fragment | `configs/policy/phase-native-candidates-review-revise-samples5-v1.json`, `max_contacts` **19** |
| composed / protocol (arm) | `e7af643d1d6c171ad895171e29d2ca6b28aa463261d389e2f008c879a487c004` / `dfd1cde52a4943a7f1dc7f824acaad8c2766cb176e2d1ce7a937b92a33bd696f` |
| composed / protocol (twin) | `48191ef49f1ff0a97aba070c46a39d35f9cbd9d29f4d5032e2459673516c0203` / `281be9bbb4425988e8eb2d9c9151be9c3165dacf4a67c3e3fc594a35dfafae01` |
| composed / protocol (smoke) | `1276d8af11ed5aaf45bdad1a28819d0496980fb84a542f9ad0ec5cdbe35280f7` / `771378958b5093ccb8b9fbc7b364259b67052d6535acd1ba039bf48bc5edbc75` |
| prepared phase supply (arm) | `prepared/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V2/phase-supply-v1.json`, output SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` — the anchor's own |
| budgets per full arm | 20,520 generation calls, 82,080 FIT endpoints, 58,607 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 Reviewer tool calls, one official complete score |
| budgets, smoke | 76 generation calls, 304 FIT endpoints, 202 repeated speech seconds, 1.0 GPU hours, 24 tool calls, no scoring |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | all three cells are `held` with the **preparation requirement already pinned**; the coordinator adds the decision requirement and flips |
| registration commit | ``a379d444` (the package) plus this receipt-pinning commit; `check` ran against the clean tree at `a379d444``, on branch `fable/b2-anchor-prep`, based on master `bd04f4b9` |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-samples5-train-fold-a-v2",
            "slurp-native-samples5-anchor-train-fold-a-v2")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with the twin fragment pair reproduces the twin pair, and with the two smoke
fragment names plus split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`
the smoke pair. **The method is verified**: run it on the anchor's own fragments
(`slurp-native-dual-store-train-fold-a-anchor-recovery-v1` for both baseline and experiment) and it
returns the anchor's sealed protocol hash
`2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c`, the value its own run manifest
carries. See `composed-hashes-v1.json`.

**These hashes describe the fragments exactly as committed**: readiness `held`, the preparation
requirement pinned, `prepared_phase_supply` pinned. `compose` hashes the whole merged four-fragment
document, so adding the decision requirement and flipping readiness both change the composed hash
and therefore the protocol hash. Section 2 is the one step that does both and re-pins everything.

## 2. The launch step: `scripts/flights/repin_cell.py`

This is the reviewed, tested tool for exactly this transition. It re-runs the model-free
`prepare-supply` **only if** the prepared artifact would otherwise mismatch, re-pins it into the
baseline fragment and the experiment's preparation requirement, applies the decision requirement,
flips `readiness.state` to `ready`, recomputes the composed and protocol hashes, rewrites every
dependent hash in this directory, the preregistration and the six exposure-ledger notes in
dependency order, and then runs `core.flight.cli check` for every cell and asserts the
runtime-derived hashes agree. Every step is model-free.

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

Write the root admission receipt under the data root first (the tool refuses a `--decision` whose
file is absent), then:

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-anchor-smoke-4-v2 \
  --experiment slurp-native-samples5-anchor-train-fold-a-v2 \
  --experiment slurp-native-samples5-anchor-greedy-twin-train-fold-a-v2 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v2 \
  --preregistration docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v2-preregistration.md \
  --decision coordination/slurp-b2-samples5-anchor-v2/admission-v1.json \
  --decision-id <the admission decision id> \
  --set-ready \
  --python "$PY"
```

It refuses a dirty tree, refuses if any of the six ledger rows is missing or already consumed, and
refuses if the package does not currently carry the hashes it is about to replace. Commit the
result in one commit before launching, because step 3 below must still see a clean tree.

If the owner wants the smoke sealed before the two full cells are armed, run the tool once with
only `--experiment slurp-native-samples5-anchor-smoke-4-v2 --set-ready`, and again for the two full
cells after the smoke seals. Each invocation is its own commit.

## 3. Pre-launch checklist

1. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a
   COMPLETED manifest reads `study_commit` at finalize, so the checkout stays clean for the whole
   run. No receipt from this preparation lives inside the repository.
2. No flight process is running and no `locks/flight.lock` is held in the data root: one experiment
   in flight.
3. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
4. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
5. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
6. Section 2 has run and its commit is in place.

## 4. Step one: the four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-anchor-smoke-4-v2 \
  --cell slurp-native-samples5-anchor-smoke-4-v2 \
  --owner root-slurp-native-samples5-anchor-smoke-4-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-samples5-anchor-smoke-4-v2.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-anchor-smoke-4-v2 \
  --cell slurp-native-samples5-anchor-smoke-4-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-samples5-anchor-smoke-4-v2.worker-lease.json"
```

Expected: roughly 36 realized contacts (about 9 per row: one Perception, five Solver samples, two
Reviewer, one Planner) against the 76-contact ceiling, about 95 repeated speech seconds, no scorer,
around 10 to 20 minutes of wall clock. Accept only if all eight hold:

- **no row exceeds 19 contacts**, and the Reviewer and the Planner are both present in the trace —
  this is the review-loop-ON base, not cell B0's two-contact shape;
- every outputs row's `native_episode_receipt.role_visits` reads
  `perception, solver, review, planner` (plus a second `solver, review, planner` on any row the
  Planner routed `REVISE`), and `planner_routes` records the action per visit;
- every outputs row carries a top-level `solver_group` sibling of `native_episode_receipt` with
  **all five raw samples** of the DELIVERED Solver visit, `sample_index` 0 to 4 ascending, five
  **distinct** seeds (`1249110493 … 1249110497`) and `temperature 0.7` on each
  (`rails.native_episode_receipt.validate_solver_group_receipt` enforces the shape at seal, so a
  missing sample stops the worker rather than producing a row);
- the delivered `final_response_text` **equals the commit policy's own output**: replay each row
  offline with `analysis.native_commit_replay.replay_row` at `min_support 3`,
  `similarity_threshold 0.8` and confirm the replayed answer is byte-identical to the delivered one
  on all four rows;
- the `solver_group.delivered` block carries the intent support count, the member sample indices and
  the tie-break index, and each delivered entity its own support and member indices;
- one `*.request-fit.json` per realized contact under
  `$DATA/prepared/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-FIT-V2/attempt-slurp-native-samples5-anchor-smoke-4-fit-v2/`,
  every one with `every_request_fits = true` and every Reviewer and Planner request still inside the
  24,576-token slot — this is where the four extra `phase:solver` agent states (preregistration
  section 3, item 4) first show up in a real request, bounded at under 2,304 extra tokens;
- Reviewer task-contract tool calls are non-zero and at most 24;
- the worker prints a seal and the tree is still clean.

Read the serving monitor for this window as well: the smoke is the **first visible evidence** of
whether the five same-prefix sibling requests reuse the cached prompt prefix on one slot. Record the
per-contact latency of sample 0 against samples 1 to 4. If samples 1 to 4 cost the same prefill as
sample 0, the arm's cost estimate should be re-priced before launch.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops cell B2 until the fix is proven on this same four-row roster.

## 5. Step two: the arm campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-samples5-anchor-train-fold-a-v2.json" \
  --owner root-slurp-native-samples5-anchor-train-fold-a-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

Expected: about **9.0 contacts per row**, roughly 9,800 contacts, against the exact 20,520 ceiling;
about 27,800 repeated speech seconds against the 58,607 cap; roughly 6 GPU hours against the 12.0
ceiling. The sealed anchor's own measured cost — 5,417 contacts, 15,459.76 speech seconds, 3.388
GPU hours, 88.7 % mean utilisation — is the reference. Budget roughly 6 to 10 hours of wall clock
for generation plus about 3 minutes of official scoring. Nothing else may occupy the GPU while it
flies, and CPU work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for each lease window from that file;
they are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means a
CPU-only step, not a hang.

Do not run `coordinate-fit`: the native gate fits every request itself, and a standalone fit would
double-charge the FIT row.

## 6. Step three: the twin campaign — only on a positive arm CI95

Owner decision 8 of 2026-09-17: **a cell's twin flies only after its arm shows a positive CI95
against the base.** Read the arm against the sealed anchor first (section 7 step 2). If the CI95
lower bound of the pooled SLU delta is not above zero, the cell closes without the twin and the
arm-versus-twin clause is reported as not reached.

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-samples5-anchor-greedy-twin-train-fold-a-v2.json" \
  --owner root-slurp-native-samples5-anchor-greedy-twin-train-fold-a-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

One cell in flight at a time: the arm seals before the twin launches.

## 7. Post-flight

1. Confirm each manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows each carrying
   its `solver_group`, and each official score ran exactly once. Record the score artifact SHA-256
   and the run manifest SHA-256 for both arms.
2. Fill `scores_sha256` and `run_manifest_sha256` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that
   recipe pins it: `analysis.null_calibration_cli.rows_for` to read the sealed score registries,
   `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B2-SAMPLES5-ANCHOR-PAIRED-ANALYSIS-V2/{score-contrasts.json,README.md}`.
3. Run projection v3 (`slurp-slu-official-projected-v3-train`) over a **copy** of each arm's sealed
   outputs and report its numbers beside every official number, with the symmetric-normalised
   number (owner decision 7). It never gates.
4. Compute the preregistered agreement diagnostics, including the revision counts and the Reviewer
   tool-call count against the anchor's 1,082.
5. Produce the **report-only** sensitivity table with `analysis/native_commit_replay.py` over the
   sealed `solver_group` rows at `s` in {2, 3, 4}, char-F1 0.8. It is never a gate and no threshold
   may be chosen from it after the fact.
6. Apply the decision rule from the preregistration section 7 unchanged, at the TRAIN A own-null
   margins (SLU micro 1.1218, intent 1.0051). Publish
   `docs/results/2026-09-17-slurp-b2-samples5-anchor-verdict.md` with the headline table (anchor,
   arm, twin, both deltas, direct column, projection-v3 column), the saves/harms/ties table, the
   full 18-scenario table in both weightings, the agreement diagnostics table, the report-only
   sensitivity table and the cost table including measured GPU hours and prompt-cache behaviour.
7. Close the six exposure rows: set `consumed` to `yes` and append the actual calls, actual repeated
   speech seconds, measured GPU hours, the sealed score and manifest SHA-256 values, and the
   verdict.
8. On ADMITTED, add the harness-admission entry for M2 under the `episode` switch class
   (`switch.table` `"episode"`, `switch.key` `native_episode.roles.solver`, `switch.off` the
   historical Solver role — `rails.config_tables.is_episode_null_arm` accepts `null`, or a role with
   `samples` 1 and no `decoding_overrides`/`commit` — and a `switch.proof` test that composes both
   arms), and add the grouped Solver to the default plan. On NEUTRAL it enters the plan only if it
   lowers cost, which it does not; on HARMFUL it never arms a default plan.

## 8. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b2-samples5-anchor-v2/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `request-envelope-comparison-v1.json` | `e8d6e1b5425edaa23245a1c332a7dd7b3c89f2729bebc0c016d7d58ef5325b5e` | on 1080/1080 rows and all four phases the rendered request differs from the ANCHOR's only by the phase-program id inside the `[agent control …]` marker, for the arm and the twin alike, **0 rows differing otherwise**; and the five sibling Solver requests differ from each other only by `seed`, from the anchor's only by `seed` and `temperature` (twin: only `seed`) |
| `request-envelope-digests-v1.json` | `79032accb2bbefed18fed9783294f32943873c5393fd546d7dd55b1c6d9f195b` | the per-row, per-phase envelope digests for the anchor, the arm and the twin behind that claim |
| `phase-supply-vs-anchor-v1.json` | `68e1b12c15a3dda42ac83f04d6ff5bccccfaf9fc6e5bbf3ae92cb54d9c29d428` | the rebuilt Perception supply selects identically to the anchor's on all 1,080 rows (4/4 for the smoke against both sealed smoke artifacts), `output_sha256` equal: `ba5e1faa…` and `512583ec…` |
| `prompt-fit-statement-v1.json` | `6086dd1abb750d7c08985a5f42da275434bcd88c079c3bbb8d4b116f71ec9ad5` | measured prompt fit for the four role visits this cell renders, from the anchor's 5,417 sealed fit receipts; tightest margin 9,194 tokens (`planner:1`), worst-case growth under 2,304 tokens, residual 6,890 |
| `composed-hashes-v1.json` | `8c1667e6cbecd50d7c5c67a5b3df5afff9393d5b3b116cc5feb2edf69c207372` | the composed and protocol hashes for all three cells, plus the anchor method check that returns the anchor's sealed `2527b527…` |
| `plan-index-v1.json` | `eb3c164f830c75bdafeada981f77f05f38d8a48fb431c58d471ccb2a6f982ae6` | the SHA-256 of the protocol document and of all six registered plan documents, with their attempt ids and caps |
| `ledger-parse-v1.json` | `74fe8a150407aa8ffdc19a5232c5d4aa2c2a7c7654ec6a8ae7687b742f598150` | `contracts._parse_ledger_tables` sees all six new rows and all six superseded v1 rows exactly once, each `consumed = no`; 878 rows and 878 distinct run ids parsed in total, 0 duplicates |
| `prepare-supply-arm-v1.json` | `b513ff4f2fddccf93182e92ce990e525e1d96358d2d1203d85aa50dd9da1f245` | the model-free supply preparation receipt for the arm |
| `prepare-supply-twin-v1.json` | `11cd278643c471d59632b8815e417dd6a3d0756ce763b16721b7415d9bf1d2ea` | the same for the twin |
| `prepare-supply-smoke-v1.json` | `619e9b6f8c9f71d82948241fac95988870386775986427d1301fdcdbb750ae55` | the same for the smoke |
| `check-arm-v1.json` | `0ade13185c917d3b304d9a92509672e4a6c5f1c69df836dfe06833263f0724d9` | `core.flight.cli check` passes for the arm: preflight, gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase, and the runtime-derived protocol hash equals the registered one |
| `check-twin-v1.json` | `9efd11e99a7ab5b4d9a17498c0079bb8dad04743850dc13b42074c60f534cf31` | the same for the twin |
| `check-smoke-v1.json` | `48298499e0b34cc888e09341a987b8e025a5bc072c97998d2062120e64168074` | the same for the four-row smoke |

Model-free prompt-budget estimate from `core.flight.cli check` over the widest request each phase
renders across the whole roster is recorded in the three `check` receipts. That estimate unions
every candidate envelope and is deliberately conservative; the measured per-visit bound from the
anchor's own sealed receipts is in the preregistration section 9.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. These three cells
therefore do not declare the stage at all, so the CLI refuses earlier, at the cell's
`allowed_execution_stages` policy. The row-for-row envelope comparison above is the contact-free
substitute and is stronger per row.

Do not re-run `derived_media_confinement_check.py` from inside the checkout without reverting its
in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
dirty the tree the manifest reads at finalize.

## 9. Gates run on this branch

`scripts/checks/engineering_base_check.py` PASS; `scripts/checks/results_ledger_check.py` PASS
(53 rows, 66 run ids registered and closed, 143 cited paths present, 40 pre-existing findings
reported, none introduced here); `scripts/checks/harness_admission_check.py` PASS (4 modules, 3
barred from every default plan, 1 default plan). `core.flight.cli check` PASS for all three cells,
each re-deriving its registered protocol hash at runtime and reporting `ALLOW` for every phase
(operational margins 5,347 to 5,588 tokens on the conservative union estimate). M2 has no
harness-admission entry yet and must not have one before a verdict. Targeted tests:
`tests/unit/test_rails_controllers.py`, `tests/unit/test_native_episode_config.py`,
`tests/unit/test_native_group_solver.py`, `tests/unit/test_native_request_grouped_solver.py`,
`tests/unit/test_commit_policies.py` and
`tests/unit/test_native_episode_runner_grouped_solver.py`.

## 10. Deviations the coordinator should know about

1. **The Reviewer and the Planner read all five raw Solver samples, not the committed answer.** The
   brief asked this to be confirmed; it is **false** as implemented, and the new test
   `test_grouped_solver_revise_resamples_and_the_reviewer_reads_every_raw_sample` records the real
   behaviour by rendering the actual Reviewer and Planner requests. Agent states are registered per
   contact, so the commit policy governs the delivered answer only. Registered as known request
   difference 4 in the preregistration, bounded in prompt-fit terms, and left unrepaired: changing
   it is a production change that owes its own engineering item. **This is the first open decision
   for the coordinator.**
2. **A pre-existing test break was repaired.** `tests/unit/test_rails_controllers.py::test_registered_program_ids_match_the_shipped_configs`
   failed on master `bd04f4b9`: `phase-native-candidates-solve-samples5-v1` was registered in
   `rails/controllers.py` by the merged v1 package but never added to `_EXPECTED_PROGRAM_SHAPES`.
   Both it and the new program id are now present.
3. **Two budget numbers in the brief were corrected upward.** Repeated speech seconds 58,606 became
   **58,607** (`ceil(19 x 3,084.5284375) = 58,606.04` rounds up, and the anchor's own 33,930 for 11
   contacts is the same `ceil` convention), and the smoke's 117 s became **202** s
   (`ceil(19 x 10.5955625)`; the four-row roster is 10.5955625 s per pass, from cell B0's sealed
   smoke manifest). Registering a ceiling below the theoretical maximum would fail closed at the
   worst possible moment.
4. **The 12.0 GPU-hour ceiling is the anchor's own, not a fresh estimate.** The anchor realized
   3.388 GPU hours; a contact-proportional estimate for this cell is about 6.1. See the
   preregistration section 8.
5. **`native_episode.review_loop "on"` was added** to the three baselines. The anchor carries no
   marker. It is the optional, validated E6 declaration and is refused the moment it disagrees with
   the three role leaves, so it cannot change behaviour; it makes the ON/OFF pair legible beside
   cell B0's `"off"`.
6. **Registered hashes are pre-flip.** Section 1, and section 2 is the one step that changes them.
7. **No production behaviour was changed.** The only source edits are the new policy fragment, its
   registration in `rails/controllers.py`, and tests.
8. **Other anchor re-base packages are being prepared in parallel** (B1 and B4 prepared artifacts
   for `…-ANCHOR-…-V2` run ids already exist under `$DATA/prepared/`). The exposure ledger will
   conflict textually when those branches merge; merge them serially and re-run
   `results_ledger_check.py` after each.

## 11. Open decisions for the coordinator

1. **The Reviewer/Planner input.** Do they review the five raw samples (as registered), or should a
   production change make them review the one committed draft? The registered cell answers the
   question the spec asks — does sampling plus aggregation raise SLU-F1 — under the first reading,
   and the twin shares the property exactly, so the contrast is clean either way. But "the Reviewer
   reviews a draft" is a different mechanism from "the Reviewer reviews a sample set", and the
   owner may want the second registered as its own cell rather than folded in silently.
2. Whether to re-price the arm's cost after reading the smoke's prompt-cache behaviour. Re-pricing
   the 12.0-hour ceiling upward is a plan change and needs a new registration; downward does not.
3. Whether the smoke's readiness is flipped separately from the two full cells (section 2 gives
   both forms).
## 12. Superseded before contact (2026-09-17, after E2c)

**This package is superseded and must not be flown.** It was registered before **E2c** (merged at
`59db0f9b`), when agent states were registered per *contact*, so a grouped Solver visit left five
separate `kind=phase:solver` states and the Reviewer and the Planner read the five raw samples
rather than the one committed answer. Section 10 deviation 1 and section 11 open decision 1 above
record that as a known, unrepaired difference: the cell moved two things at once.

E2c repaired it in the harness. A grouped Solver visit now takes one step and registers exactly one
`kind=phase:solver` state, carrying the commit policy's aggregate, in the same wire form a samples-1
(anchor) Solver state has, so the Reviewer and the Planner read one draft exactly as they do on the
anchor; the five raw samples stay in custody in their own contacts, the visit's one
`action_alternatives` wave and the sealed `solver_group` receipt; and a Planner `REVISE` re-samples
the whole group and re-commits. Cell B2 is therefore a one-factor cell again, and it is
re-registered on new run ids and new hashes.

The replacement registration is
[`../2026-09-17-slurp-b2-samples5-anchor-v3-preregistration.md`](../2026-09-17-slurp-b2-samples5-anchor-v3-preregistration.md)
with its runbook
[`../2026-09-17-slurp-b2-samples5-anchor-v3/README.md`](../2026-09-17-slurp-b2-samples5-anchor-v3/README.md).

The three cells registered here never flew. Their six exposure rows stay `consumed = no` and each
now carries a supersession note. The configs, plans and protocol of this package are left in place
unchanged as the audit record of what was registered before E2c; nothing in it is edited, and open
decision 1 of section 11 above is answered by E2c rather than by a configuration choice.
