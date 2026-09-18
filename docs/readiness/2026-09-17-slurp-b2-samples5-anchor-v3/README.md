# Cell B2 launch runbook (v3, after E2c): sample-and-aggregate commit on the sealed anchor, N = 5 at T = 0.7

Everything the coordinator needs to fly cell B2, its greedy-repeat twin and its four-row smoke is in
this directory and in the committed configs. **Three steps remain: re-pin with the decision
requirement and the readiness flip, fly the smoke, then the arm, then (only on a positive arm CI95)
the twin.** Preregistration:
[`../2026-09-17-slurp-b2-samples5-anchor-v3-preregistration.md`](../2026-09-17-slurp-b2-samples5-anchor-v3-preregistration.md).

The v3 registration agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**,
never started, stopped or queried the resident service, never touched the campaign in flight, and
never touched another worktree.

**This package replaces the v2 package**
(`docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v2/`), which is superseded before contact. The
v2 registration predates **E2c** (merged at `59db0f9b`) and had to register "the Reviewer and the
Planner read the five raw Solver samples" as a second, unmeasured difference beside the one factor
under test. E2c makes a grouped Solver visit register exactly one `kind=phase:solver` state, the
committed answer, so the Reviewer and the Planner read one draft exactly as on the anchor. The v2
cells never flew, their six exposure rows keep `consumed = no`, and the v2 README and each of the six
notes carry a supersession line. **Do not fly the v2 cells.**

> **STOP — the four-row smoke of this package failed AT THE SEAL on 2026-09-17 and its two exposure
> rows are closed.** `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3` generated all 36 of its contacts
> and was then refused by the bundle verifier on invariant **I7**; the fix is **E2d** (commit
> `f3a77fb0`, merged `5492c2af`, invariant I7g) and the smoke is re-registered as
> `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-RECOVERY-V3`. **Do not fly the smoke cell named in
> section 1**; fly the recovery cell instead, and re-pin the arm and the twin on the fixed commit
> before either launches. See section 12 below and
> [`../2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1.md`](../2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1.md).

## 1. What is registered

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-samples5-anchor-train-fold-a-v3`, run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V3`, attempt `attempt-slurp-native-samples5-anchor-train-fold-a-generation-v3` |
| arm FIT | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-FIT-V3` / `attempt-slurp-native-samples5-anchor-train-fold-a-fit-v3`, 82,080 endpoints, inside the same campaign |
| twin cell | experiment and cell `slurp-native-samples5-anchor-greedy-twin-train-fold-a-v3`, run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-V3`, attempt `attempt-slurp-native-samples5-anchor-greedy-twin-train-fold-a-generation-v3` |
| twin FIT | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-FIT-V3` / `attempt-slurp-native-samples5-anchor-greedy-twin-train-fold-a-fit-v3`, 82,080 endpoints |
| smoke cell | experiment and cell `slurp-native-samples5-anchor-smoke-4-v3`, run `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3`, attempt `attempt-slurp-native-samples5-anchor-smoke-4-generation-v3` |
| smoke FIT | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-FIT-V3` / `attempt-slurp-native-samples5-anchor-smoke-4-fit-v3`, 304 endpoints |
| campaign plans | `configs/campaign/slurp-native-samples5-anchor-train-fold-a-v3.json`, `configs/campaign/slurp-native-samples5-anchor-greedy-twin-train-fold-a-v3.json` |
| policy fragment | `configs/policy/phase-native-candidates-review-revise-samples5-v1.json`, `max_contacts` **19** — unchanged from the v2 package, and not re-registered here |
| composed / protocol (arm) | `9688e0c9e6e93e30d200469b6ecafd28f865a37f0b0a3d694a879f7749f426a3` / `4e5acfad5219ef6920b881dec240ead02d06f53aaf91895e92674579f0ee0a3e` |
| composed / protocol (twin) | `65c9a220f3bced4f523b5c531a8a577c539dd10db4b4b7d439c73edc9a91cc9b` / `0066dd067b27aadf25c8ba3b0e03cbffb78a9d47b3be0be66f4a9f37861430df` |
| composed / protocol (smoke) | `d631960a736c34b0e9a1dd85bf9cdb7370feb7ec2410260a7fcadcf3737b2142` / `63034f02c67c2fe3b0dde2cab8762df68500ec1ce545ab6f321562ec58324553` |
| protocol document | `protocol-registered-v1.json`, SHA-256 `348ab17d10d49f943745a43c8065660f87d171ccc0bf1398d739ba77c2af0cfd` |
| prepared phase supply (arm) | `prepared/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V3/phase-supply-v2.json`, SHA-256 `f686a1cd3801e04b6ac2fde52edd2b25509cd073a48d9624074239873ea5616d`, output `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` — the anchor's own |
| prepared phase supply (twin) | `prepared/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-V3/phase-supply-v1.json`, SHA-256 `43854c81092c49ce99db6f099f775380023beaced3bb11c47500da1411157ff5` |
| prepared phase supply (smoke) | `prepared/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3/phase-supply-v2.json`, SHA-256 `b9db585a7d6b32c592fdc8d01730c77cab53998f037eeb58523b974646efff2e`, output `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` |
| budgets per full arm | 20,520 generation calls, 82,080 FIT endpoints, 58,607 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 Reviewer tool calls, one official complete score |
| budgets, smoke | 76 generation calls, 304 FIT endpoints, 202 repeated speech seconds, 1.0 GPU hours, 24 tool calls, no scoring |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | all three cells are `held` with the **preparation requirement already pinned**; the coordinator adds the decision requirement and flips |
| registration commit | `502d3516` (the package) plus this receipt-pinning commit, on branch `fable/b2-v3`, based on master `36874ed4` (which carries E2c, merged `59db0f9b`); `check` ran against the clean tree at `502d3516` |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-samples5-train-fold-a-v3",
            "slurp-native-samples5-anchor-train-fold-a-v3")
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
  --experiment slurp-native-samples5-anchor-smoke-4-v3 \
  --experiment slurp-native-samples5-anchor-train-fold-a-v3 \
  --experiment slurp-native-samples5-anchor-greedy-twin-train-fold-a-v3 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3 \
  --preregistration docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-preregistration.md \
  --decision coordination/slurp-b2-samples5-anchor-v3/admission-v1.json \
  --decision-id <the admission decision id> \
  --set-ready \
  --python "$PY"
```

It refuses a dirty tree, refuses if any of the six ledger rows is missing or already consumed, and
refuses if the package does not currently carry the hashes it is about to replace. Commit the
result in one commit before launching, because step 3 below must still see a clean tree.

If the owner wants the smoke sealed before the two full cells are armed, run the tool once with
only `--experiment slurp-native-samples5-anchor-smoke-4-v3 --set-ready`, and again for the two full
cells after the smoke seals. Each invocation is its own commit.

## 3. Pre-launch checklist

1. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a
   COMPLETED manifest reads `study_commit` at finalize, so the checkout stays clean for the whole
   run. No receipt from this preparation lives inside the repository.
2. No flight process is running and no `locks/flight.lock` is held in the data root: one experiment
   in flight. (A B4b campaign held the lock while this package was registered; that flight owns the
   GPU until it seals.)
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
  --experiment slurp-native-samples5-anchor-smoke-4-v3 \
  --cell slurp-native-samples5-anchor-smoke-4-v3 \
  --owner root-slurp-native-samples5-anchor-smoke-4-v3 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-samples5-anchor-smoke-4-v3.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-samples5-anchor-smoke-4-v3 \
  --cell slurp-native-samples5-anchor-smoke-4-v3 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-samples5-anchor-smoke-4-v3.worker-lease.json"
```

Expected: roughly 36 realized contacts (about 9 per row: one Perception, five Solver samples, two
Reviewer, one Planner) against the 76-contact ceiling, about 95 repeated speech seconds, no scorer,
around 10 to 20 minutes of wall clock. Accept only if all nine hold:

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
- **E2c, the new acceptance item:** each Solver visit leaves exactly **one** `kind=phase:solver`
  agent state, whose content is the committed answer, and the visit contributes exactly one
  `action_alternatives` wave naming all five contacts. A row with five `phase:solver` states per
  visit means the checkout predates E2c and the flight must stop;
- the delivered `final_response_text` **equals the commit policy's own output**: replay each row
  offline with `analysis.native_commit_replay.replay_row` at `min_support 3`,
  `similarity_threshold 0.8` and confirm the replayed answer is byte-identical to the delivered one
  on all four rows — and, under E2c, byte-identical to the registered `phase:solver` state of the
  delivered visit;
- the `solver_group.delivered` block carries the intent support count, the member sample indices and
  the tie-break index, and each delivered entity its own support and member indices;
- one `*.request-fit.json` per realized contact under
  `$DATA/prepared/SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-FIT-V3/attempt-slurp-native-samples5-anchor-smoke-4-fit-v3/`,
  every one with `every_request_fits = true` and every Reviewer and Planner request still inside the
  24,576-token slot — and, under E2c, at the anchor's own one-state volume rather than the v2
  package's projected four-extra-state growth;
- Reviewer task-contract tool calls are non-zero and at most 24;
- the worker prints a seal and the tree is still clean.

Read the serving monitor for this window as well: the smoke is the **first visible evidence** of
whether the five same-prefix sibling requests reuse the cached prompt prefix on one slot. Under E2c
the five siblings share the same `QueryState`, so their prompts are byte-identical but for `seed`.
Record the per-contact latency of sample 0 against samples 1 to 4. If samples 1 to 4 cost the same
prefill as sample 0, the arm's cost estimate should be re-priced before launch.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops cell B2 until the fix is proven on this same four-row roster.

## 5. Step two: the arm campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-samples5-anchor-train-fold-a-v3.json" \
  --owner root-slurp-native-samples5-anchor-train-fold-a-v3 \
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
  --campaign-plan "$REPO/configs/campaign/slurp-native-samples5-anchor-greedy-twin-train-fold-a-v3.json" \
  --owner root-slurp-native-samples5-anchor-greedy-twin-train-fold-a-v3 \
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
   `analysis/SAEA-SLURP-B2-SAMPLES5-ANCHOR-PAIRED-ANALYSIS-V3/{score-contrasts.json,README.md}`.
3. Run projection v3 (`slurp-slu-official-projected-v3-train`) over a **copy** of each arm's sealed
   outputs and report its numbers beside every official number (owner decision 7). Report the
   symmetric-normalised number as **not evaluable** — no symmetric TRAIN sibling scorer exists — and
   never substitute the DEV sibling's value. It never gates.
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

All under `$DATA/coordination/slurp-b2-samples5-anchor-v3/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `request-envelope-comparison-v1.json` | `cb1453ab837f93c129e8d61836e6910ea53a044ab5aace9c44860e3d7ba291b8` | on 1080/1080 rows and all four phases the rendered request differs from the ANCHOR's only by the phase-program id inside the `[agent control …]` marker, for the arm and the twin alike, **0 rows differing otherwise**; and the five sibling Solver requests differ from each other only by `seed`, from the anchor's only by `seed` and `temperature` (twin: only `seed`) |
| `request-envelope-digests-v1.json` | `cd443a157b2c5245f3178005fd10c9ea3a47bbc76780b010e926ed8656fed82c` | the per-row, per-phase envelope digests for the anchor, the arm and the twin behind that claim |
| `e2c-rendered-proof-v1.json` | `71a07bcd2cd2a475eb38db3375fbbc11e3bdc4dd22b0a53b505eecf684383092` | the fake-model rendered proof over the four smoke sample ids: 15 contacts per row inside the 19 ceiling, two Solver visits of five contacts, two `action_alternatives` waves each naming five contacts with one shared `QueryState`, exactly **one** `kind=phase:solver` state per visit carrying the committed answer, the first-round Reviewer and Planner requests carrying exactly one such state and no raw sample, the second-round Reviewer carrying exactly two (both committed), the delivered answer equal to the commit, and a rendered-text volume within **one character** of an anchor-shaped episode scripted with the same answer |
| `e2c-rendered-proof-driver.py` | `4c880acb0b2d17efba58e697a34fa7d3553fba7bce7a410a97c285663d877f0c` | the driver that produced it: a pytest module run against `tests/unit` on `PYTHONPATH`, driving the shared `_ActualEpisodeHarness` fake transport; kept outside the repository so no receipt can dirty the tree |
| `phase-supply-vs-anchor-v1.json` | `8c69e6bc1d09853a0a3429db23312b6a575e31293a8e8d4354ca8b0ba5a409a2` | the rebuilt Perception supply selects identically to the anchor's on all 1,080 rows (4/4 for the smoke against the sealed smoke artifact), `output_sha256` equal: `ba5e1faa…` and `512583ec…` |
| `prompt-fit-statement-v1.json` | `38a57bc6865decbbed55f8281859260d546f2d4a8e88d0f6e3e5a470d95f639e` | measured prompt fit for the four role visits this cell renders, from the anchor's 5,417 sealed fit receipts; tightest margin 9,194 tokens (`planner:1`) applied **directly** under E2c's one-state form, with a conservative 2,560-token content bound leaving 7,146 |
| `composed-hashes-v1.json` | `1111c2c038bc8def66e01ac703158c0038ef07106d6ed250142f87c47f91fd0c` | the composed and protocol hashes for all three cells, plus the anchor method check that returns the anchor's sealed `2527b527…` |
| `plan-index-v1.json` | `af1befc89b8b7220c4bf33df9a77985f8967c400f36092c62df67650fee098cd` | the SHA-256 of the protocol document and of all six registered plan documents, with their attempt ids and caps |
| `ledger-parse-v1.json` | `6f66224dec526ff3ff9f447b71d9ccdd6f468ab0572fe96d0b465a9049b5b014` | `contracts._parse_ledger_tables` sees all six new v3 rows and all six superseded v2 rows exactly once, each `consumed = no`; 900 rows and 900 distinct run ids parsed in total, 0 duplicates |
| `prepare-supply-arm-v1.json` | `46c11199f2a805fcb4dd8f731abc5f0f6d8ffb9b48a16283073cbff8031bade2` | the model-free supply preparation receipt for the arm |
| `prepare-supply-twin-v1.json` | `2ef4e94ce6c8b50b7ec311b7a9495c8b516ded7eb69d3f06706d6436430b842c` | the same for the twin |
| `prepare-supply-smoke-v1.json` | `d8ab5d804d8e41d925f9aabd005c5b701d22290cfcf9b6dd025072113f6218a8` | the same for the smoke |
| `check-arm-v1.json` | `10b0663b4f9a738d60cd150db7ca9e761b9e6d0715f27d35d1de592337bd4f71` | `core.flight.cli check` passes for the arm: preflight, gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase, and the runtime-derived protocol hash equals the registered one |
| `check-twin-v1.json` | `a64e0eb0afa4d90a2e15686d615cb66ff7a193f71361e45e8af6a325bbcd2a87` | the same for the twin |
| `check-smoke-v1.json` | `76d0642c827177a25cbd82fe0ab376ca2af9776ee81dffeffaf6281c1435d82f` | the same for the four-row smoke |

Model-free prompt-budget estimate from `core.flight.cli check` over the widest request each phase
renders across the whole roster is recorded in the three `check` receipts. That estimate unions
every candidate envelope and is deliberately conservative; the measured per-visit bound from the
anchor's own sealed receipts is in the preregistration section 9.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. These three cells
therefore do not declare the stage at all, so the CLI refuses earlier, at the cell's
`allowed_execution_stages` policy. The row-for-row envelope comparison above is the contact-free
substitute and is stronger per row, and the fake-model rendered proof covers what the envelope
renderer cannot: what a real episode's later roles actually receive.

Do not re-run `derived_media_confinement_check.py` from inside the checkout without reverting its
in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
dirty the tree the manifest reads at finalize.

## 9. Gates run on this branch

`scripts/checks/engineering_base_check.py` PASS; `scripts/checks/results_ledger_check.py` PASS;
`scripts/checks/harness_admission_check.py` PASS (5 modules, 3 barred from every default plan;
M2 still has no entry and must not have one before a verdict). `core.flight.cli check` PASS for
all three cells at study commit `502d3516`, each re-deriving its registered protocol hash at
runtime and reporting `ALLOW` for every phase (operational margins 5,347 to 5,588 tokens on the
conservative union estimate, readiness `held`, `generation_authorized` false). Targeted tests:
`tests/unit/test_native_episode_runner_grouped_solver.py`, `tests/unit/test_native_group_solver.py`,
`tests/unit/test_native_request_grouped_solver.py`, `tests/unit/test_commit_policies.py`,
`tests/unit/test_native_episode_config.py` and `tests/unit/test_rails_controllers.py`. `ruff check`
clean on every touched Python file. Exact counts are in the registration commit message.

## 10. Deviations the coordinator should know about

1. **The v2 open decision is closed by E2c, not by this package.** The v2 runbook's first open
   decision asked whether the Reviewer should read the five raw samples or one committed draft.
   E2c decided it in the harness: the committed answer IS the draft. This package registers the cell
   on that harness and withdraws the v2 "registered known behaviour" section. No configuration
   choice here depends on the answer.
2. **New run ids, new hashes, same experiment.** The base, the roster, the one moved factor, the
   commit thresholds, the comparators, the decision rule, the budgets and the twin trigger are the
   v2 registration's, unchanged. Only the harness beneath them moved, so the cell is re-registered
   rather than amended: the composed document changed, so every composed and protocol hash changed,
   and reusing the v2 run ids would have made the sealed bytes ambiguous.
3. **The policy fragment is untouched.** `phase-native-candidates-review-revise-samples5-v1` and its
   `rails/controllers.py` registration were landed by the v2 package and are reused as-is; this
   registration adds no source change at all.
4. **The prompt-fit growth term is withdrawn, not re-estimated.** The v2 package carried "four extra
   `phase:solver` states, under 2,304 extra tokens, residual 6,890". Under E2c there are no extra
   states; the anchor's measured maxima apply directly, and the only content term is the one
   committed state, conservatively bounded at 2,560 tokens with 7,146 tokens of residual margin.
5. **The smoke acceptance list gained one item**: exactly one `kind=phase:solver` state per Solver
   visit, carrying the committed answer. It is the cheapest live check that the flying checkout
   actually carries E2c.
6. **The fake-model proof runs on two harness batches, not one.** The shared `_ActualEpisodeHarness`
   synthetic world carries two rows, so the four smoke sample ids are covered in two batches of two.
   The property proved is per-episode and does not depend on the roster.
7. **Registered hashes are pre-flip.** Section 1, and section 2 is the one step that changes them.
8. **The 12.0 GPU-hour ceiling is the anchor's own, not a fresh estimate.** The anchor realized
   3.388 GPU hours; a contact-proportional estimate for this cell is about 6.1. See the
   preregistration section 8.
9. **A campaign was in flight during this registration** (`locks/flight.lock` held by the B4b slot
   store v2 arm). Nothing here touched the GPU, the resident service or any run directory; CPU work
   was capped at four workers.
10. **Other anchor packages are being prepared in parallel.** The exposure ledger will conflict
    textually when those branches merge; merge them serially and re-run `results_ledger_check.py`
    after each.
11. **Master moved while this package was being registered.** The base is `36874ed4`; by the time
    the gates finished, master carried `cfbb5f8b` (E3c, a re-entered phase acquires only what its
    trajectory lacks) and `716c5e27` (the node-context audit and the Node Context Policy design).
    Neither changes anything registered here: `core.config.compose` hashes the four **config**
    fragments and nothing else, so no source merge can move a composed or protocol hash, and E3c
    touches `rails/controllers.py` and `rails/runner.py`, neither of which the prepared artifact's
    identity digest pins (`rails.kb_policy`, `rails.knowledge_provider`, `rails.phase_supply`,
    `rails.knowledge_stores`, `core.flight.runtime`). E3c does change what a **re-entered** phase
    acquires, which this cell reaches on any `REVISE` round, so after merging, run section 2's
    `repin_cell.py` — it re-verifies the prepared artifact, re-derives every hash and re-runs
    `check` — and read the smoke's second Solver visit before launching the arm.

## 11. Open decisions for the coordinator

1. Whether to re-price the arm's cost after reading the smoke's prompt-cache behaviour. Re-pricing
   the 12.0-hour ceiling upward is a plan change and needs a new registration; downward does not.
   E2c makes the five siblings share one `QueryState`, which should help prefix reuse, but the
   server's `--no-cache-idle-slots` and `--slot-prompt-similarity 0` still make it unproven.
2. Whether the smoke's readiness is flipped separately from the two full cells (section 2 gives
   both forms).
3. Whether "the Reviewer reviews the sample set" is worth registering as its own later cell now that
   E2c has removed it from B2. It is a different mechanism, not a variant of this one, and nothing
   in this package presumes an answer.

## 12. The four-row smoke failed at the seal (2026-09-17), and the one registered recovery

`SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3` / `attempt-…-generation-v3` flew at study commit
`858ae4ea` under root decision `slurp-b2-samples5-anchor-v3-admission-v1`. It **generated every one
of its 36 registered contacts on all four rows** — 95.360063 repeated speech seconds, 36 request-fit
receipts, 4 Reviewer tool calls — and then **failed AT THE SEAL**. `core.bundle.outputs` refused row
`slurp:train:000007:audio--1504197557` with invariant **I7**: "text does not match its recorded
`response_text_sha256` — the text was mutated after the model response was recorded (I7)". A grouped
Solver row's delivered text is the registered commit policy's aggregate over the five raw samples and
equals none of them, while the pre-E2d runner bound the row's `response_text_sha256` to the **last
raw sample's** text hash.

None of this package's model-free proofs could have caught it: all of them are proofs about
*requests* (the envelope comparison, the fake-model rendered proof, the prompt-fit statement) or
about the *receipt* the runner writes. `wire-check` is unavailable for a native-episode cell, so the
four-row smoke was the first place a grouped row ever reached `verify_bundle` — which is exactly what
a form smoke is for.

**What happened to the attempt and the rows.** The worker died at the seal and never settled its
attempt, so it was left at `OPENED`. Root reconciled it to `ABORTED` through the repository's own
`core.attempts.store.AttemptStore.abort_if_opened`, with `actual` (36 calls, 95.36006250000004 s) and
`reserved` preserved unchanged; receipt
`coordination/slurp-b2-samples5-anchor-v3/attempt-reconciliation-smoke-v1.json`. The two smoke
exposure rows are now `consumed = yes`, the run directory is read-only evidence, no scorer ran and no
partial quality read was taken or is permitted. The run manifest reads `status: COMPLETED` only
because that manifest is written before the verifier runs; it is not evidence that the run sealed.

**The fix.** E2d (commit `f3a77fb0`, merged `5492c2af`) gives a grouped row its own sanctioned
custody form: the runner records `solver_group.commit_params` and binds a grouped row's
`response_text_sha256` to the DELIVERED bytes, and invariant **I7g** binds every raw sample to the
trace's own `MODEL_RESPONSE` bytes, resolves the commit policy in `core.base.COMMIT_POLICIES` and
re-derives the delivered bytes through `analysis.native_commit_replay`. I7 is unchanged and a
samples-1 row is byte-identical to before. Validated read-only on the failed smoke's own bytes:
`verify_bundle` still refuses them (pre-E2d row form, no `commit_params`), while the per-sample trace
binding passes on 4 of 4 rows and the commit recomputation reproduces all four delivered texts byte
for byte. No sealed byte was edited.

**The recovery.** `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-RECOVERY-V3` (generation) and
`SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-FIT-RECOVERY-V3` (native contact fit), cell
`slurp-native-samples5-anchor-smoke-4-recovery-v3`, composed
`2e806bfb003f5f0bbf73ff62fe8d5ac02d21bedb2832cb91c3c80f269f949b5a` / protocol
`eb1d172324d0ecbd2b784c5c51fe5067c82d770cbc63d051c8a1249b7005b1b0`, readiness `held`, plans under
`docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1/`, statement
[`../2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1.md`](../2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1.md).
**This is the one root-diagnosed recovery the preregistration section 10 allows for cell B2; a second
failure closes the cell.** Nothing about the question, the roster, the one moved factor, the commit
thresholds, the comparators, the decision rule, the budgets or the twin trigger moves — only the
E2d seal-path fix in the code the cell flies on, plus this package's own bookkeeping identities. The
caps stay the v3 smoke's own (76 / 304 / 202 s / 1.0 GPU-h / 24 tool calls, zero scoring), and the 36
calls and 95.360063 speech seconds the failed attempt spent stay charged to the closed run ids.

**What changes for the coordinator in sections 2 to 7 of this runbook.**

1. Section 2's re-pin runs for `--experiment slurp-native-samples5-anchor-smoke-4-recovery-v3` with
   `--readiness-dir docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1` and
   `--preregistration docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3-recovery-v1.md`. The same
   root decision receipt and decision id apply.
2. Section 4's worker runs on the recovery cell and its own lease token file. Its nine acceptance
   items all stand, **plus one that is the point of this recovery**: the worker prints a seal, which
   means the bundle verifier accepted every grouped row under I7g — and each row's `solver_group`
   carries the new `commit_params` block beside `commit_policy_id`.
3. Sections 5 and 6 are unchanged, **but the arm and the twin must be re-pinned with
   `scripts/flights/repin_cell.py` on the fixed commit before either launches**, because their runner
   now writes the E2d grouped-row form. Both stay `held` at `consumed = no`; the arm launches only
   after this recovery smoke seals, and the twin still only after a positive arm CI95.
4. Section 8's evidence table is joined by the recovery receipts, listed in section 9 of the recovery
   note.

**Runtime `check` on the recovery cell**, at study commit `18605e50`: config `2e806bfb…`, protocol `eb1d1723…` re-derived at runtime and equal to the registered value, 4 samples, readiness `held`, `generation_authorized false`, prompt budget `ALLOW` on all four phases (operational margins 5,348 to 5,588 tokens on the conservative union estimate). Receipt `coordination/slurp-b2-samples5-anchor-v3/recovery-check-smoke-v1.json`, SHA-256 `bb59f041c693a1d35e90b4a0b8e4029df30cbb42beb1aabf11861f4c50685fa1`.

**Deviation 12, added to section 10.** The v3 smoke baseline deliberately shared the **arm's**
speech-feature key and matcher identity strings. The recovery baseline takes its **own** pair, so the
recovery flight's trace carries its own provenance. This cannot move a request byte: each payload's
`key_representation_id` and `matcher_policy_id` are derived from the phase program id, not from the
baseline, and
`coordination/slurp-b2-samples5-anchor-v3/recovery-request-envelope-comparison-v1.json` proves it on
all 36 sealed payloads, alongside a sixteen-needle identity search that returns 0 hits on every field.
