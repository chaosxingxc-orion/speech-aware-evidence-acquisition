# Cells B4a, B4b and B4c launch runbook: the ORG knowledge cells on the sealed anchor

Everything the coordinator needs to fly the three ORG cells and their two four-row smokes is in this
directory and in the committed configs. Preregistration:
[`../2026-09-17-slurp-b4-org-cells-anchor-v2-preregistration.md`](../2026-09-17-slurp-b4-org-cells-anchor-v2-preregistration.md).

The re-base agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**, never
started, stopped or queried the resident service, and ran no worker, campaign, smoke or FIT.

## 0. What changed, and what it replaces

These three cells were first registered on the **cell B0 review-off base**
(`docs/readiness/2026-09-17-slurp-b4-org-cells-v1/`). On 2026-09-17 module M0 was re-decided
**HARMFUL** under the TRAIN A own null (owner decision 6), so the Reviewer/Planner loop stays in the
default plan and every later cell builds on the **sealed dual-store anchor**. This package is the
re-base. The v1 package is **superseded before contact**, never flew, and its ten exposure rows stay
`consumed = no` with a supersession note.

Two owner conditions bind the launch order: **B1 -> B2 -> B4b -> B4a -> B4c** (decision 8), and
**B4c flies only if B4a admits** (decision 9).

## 1. What is registered

| item | value |
| --- | --- |
| B4a cell | experiment and cell `slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-v2`, run `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-V2`, attempt `attempt-slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-generation-v2` |
| B4a FIT | `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-TRAIN-FOLD-A-FIT-V2` / `attempt-slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-fit-v2`, 47,520 endpoints, inside the same campaign |
| B4a smoke | experiment and cell `slurp-native-fallback-quirky-intent-v2-anchor-smoke-4-v2`, run `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-SMOKE-4-V2`, attempt `attempt-slurp-native-fallback-quirky-intent-v2-anchor-smoke-4-generation-v2r` |
| B4a smoke FIT | `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-ANCHOR-SMOKE-4-FIT-V2` / `attempt-slurp-native-fallback-quirky-intent-v2-anchor-smoke-4-fit-v2`, 176 endpoints |
| B4b cell | experiment and cell `slurp-native-slot-store-v2-anchor-train-fold-a-v2`, run `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2`, attempt `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-generation-v2` |
| B4b FIT | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-V2` / `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-fit-v2`, 47,520 endpoints |
| B4b smoke | experiment and cell `slurp-native-slot-store-v2-anchor-smoke-4-v2`, run `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2`, attempt `attempt-slurp-native-slot-store-v2-anchor-smoke-4-generation-v2` |
| B4b smoke FIT | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-FIT-V2` / `attempt-slurp-native-slot-store-v2-anchor-smoke-4-fit-v2`, 176 endpoints |
| B4c cell | experiment and cell `slurp-native-intent-store-v2-anchor-train-fold-a-v2`, run `SAEA-SLURP-NATIVE-INTENT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2`, attempt `attempt-slurp-native-intent-store-v2-anchor-train-fold-a-generation-v2` |
| B4c FIT | `SAEA-SLURP-NATIVE-INTENT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-V2` / `attempt-slurp-native-intent-store-v2-anchor-train-fold-a-fit-v2`, 47,520 endpoints |
| B4c smoke | **none** -- it shares B4a's store, Perception geometry and prepared-supply inputs, so B4a's smoke evidence is reusable |
| campaign plans | `configs/campaign/slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-v2.json`, `…/slurp-native-slot-store-v2-anchor-train-fold-a-v2.json`, `…/slurp-native-intent-store-v2-anchor-train-fold-a-v2.json` |
| composed / protocol (B4a) | `a07e895cf893bf2a8ba348449e949f3b0db18808d4435a3670ef49fa37f452d2` / `2577e3c90ab1ac7b90819926ae931fb008dc92f0aaaa26e44917dd55135702ee` |
| composed / protocol (B4a smoke) | `352a97fa4a2f79b80c558381a5483ecd73543a810e40733da5e3ba1498e34d27` / `e6828a497645f2ec469d22f9d5f05ab50f20bfebf600d1e49a0ba9fdf8f0a8d6` |
| composed / protocol (B4b) | `8d207b33fa7643b7e5acc4ccbd03354fe9c09df09563544c4879c4bb97ee6a4d` / `567a87ad234bb4f17c4735f94219a82b05b25a19d81fdf1ee32bb93b6eda346a` |
| composed / protocol (B4b smoke) | `c0572352a9b4758a61654f46d06812819da42d3c7cf9611b24a383882b279661` / `f13ba493375d75a524884f771a6c5d9b410425951b15cccf9d59d1fe76f3cd9c` |
| composed / protocol (B4c) | `bdbe70349eb324d43b270d05a344386bf5089894ea354fad88009c67774b0e3c` / `7bf967c3f914acc1fb1dd4a3366c863eb6ed1056ef3fec105f4a96efabb4ad9a` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | all five cells are `held` with the preparation requirement pinned; the coordinator appends the decision requirement and flips |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-fallback-quirky-intent-v2-train-fold-a-v2",
            "slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-v2")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with each other baseline/experiment pair reproduces that cell's pair; the two smokes
use split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`. The method is
verified on this tree: run it on `slurp-native-dual-store-train-fold-a-anchor-v1` as both baseline and
experiment and it returns the anchor's registered
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

**These hashes describe the fragments exactly as committed at `d4965c5e`**: readiness `held`, the
preparation requirement pinned, `prepared_phase_supply` pinned. `compose` hashes the whole merged
fragment set, so flipping readiness and adding the decision requirement each change the composed hash
and therefore the protocol hash. **Do not do that by hand -- use the re-pin tool of section 2.**

## 2. The launch step: `core.flight.repin`

`scripts/flights/repin_cell.py` is the reviewed, tested entry point
(`speech_aware_evidence_acquisition.core.flight.repin`). It re-runs the model-free `prepare-supply`
step only when the prepared artifact would actually mismatch, re-pins the new artifact into the
baseline fragment and the experiment's preparation readiness requirement, optionally applies a
decision requirement and flips `readiness.state` to `ready`, recomputes the composed and protocol
hashes, rewrites every dependent hash in dependency order -- this README, the preregistration, every
plan file, the protocol document and the exposure-ledger notes of the package's run ids -- then runs
`core.flight.cli check` for every cell and asserts the runtime-derived hashes agree. Every step is
model-free.

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

Re-pin the whole package and flip it ready in one call:

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-fallback-quirky-intent-v2-anchor-smoke-4-v2 \
    --cell slurp-native-fallback-quirky-intent-v2-anchor-smoke-4-v2 \
  --experiment slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-v2 \
    --cell slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-v2 \
  --experiment slurp-native-slot-store-v2-anchor-smoke-4-v2 \
    --cell slurp-native-slot-store-v2-anchor-smoke-4-v2 \
  --experiment slurp-native-slot-store-v2-anchor-train-fold-a-v2 \
    --cell slurp-native-slot-store-v2-anchor-train-fold-a-v2 \
  --experiment slurp-native-intent-store-v2-anchor-train-fold-a-v2 \
    --cell slurp-native-intent-store-v2-anchor-train-fold-a-v2 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2 \
  --preregistration docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2-preregistration.md \
  --package-name slurp-b4-org-cells-anchor-v2 \
  --decision coordination/<the root admission receipt relpath> \
  --decision-id <the admission decision id> \
  --set-ready
```

Drop `--set-ready` (and the two `--decision` flags) to re-pin only -- for example after merging
master, before deciding to launch. The tool refuses a prepared artifact whose selection changed
unless `--allow-output-change` is given; **it must never be given here**, because the whole
one-factor claim is that the Perception selection does not move. Commit the result before launching:
a COMPLETED manifest reads `study_commit` at finalize and refuses a dirty tree.

## 3. Pre-launch checklist

1. Owner decision 8's order is respected: B1 and B2 are sealed, then B4b, then B4a. **B4c must not
   fly unless B4a is ADMITTED** (decision 9).
2. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree. **Fly from a
   clean detached worktree pinned at the admitted commit.** No receipt from this preparation lives
   inside the repository.
3. No flight process is running and no `locks/flight.lock` is held in the data root. One experiment
   in flight: seal each cell before opening the next.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
5. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package closes
   the D3 gate.
6. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
7. Section 2's re-pin has run and its `check` assertions passed for all five cells.

## 4. Step one: the four-row smoke (B4b first, then B4a)

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-slot-store-v2-anchor-smoke-4-v2 \
  --cell slurp-native-slot-store-v2-anchor-smoke-4-v2 \
  --owner root-slurp-native-slot-store-v2-anchor-smoke-4-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-slot-store-v2-anchor-smoke-4-v2.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-slot-store-v2-anchor-smoke-4-v2 \
  --cell slurp-native-slot-store-v2-anchor-smoke-4-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-slot-store-v2-anchor-smoke-4-v2.worker-lease.json"
```

For cell B4a, substitute `slurp-native-fallback-quirky-intent-v2-anchor-smoke-4-v2` everywhere.

Expected: a few minutes of wall clock, about 20 generation contacts against the 44 ceiling, about 80
FIT endpoints against the 176 ceiling, about 53 repeated speech seconds, no scorer. Accept only if all
of these hold:

- at most 11 contacts per row and 44 in total, with the Reviewer and Planner visits present -- this is
  the anchor's loop, not the review-off ablation;
- the episode receipt carries well-formed `role_visits` and `planner_routes` on every row, and no row
  reports `skipped_by_configuration`;
- **B4b only**: the Perception request is byte-identical to the anchor's on all four rows, and the
  Solver and Reviewer slot cards show the revised text;
- **B4a only**: on the rows where Perception omitted it, the selection audit records the appended
  `general_quirky` candidate with `source = "fallback"` and `candidate_ids_without_fallback`, and the
  Solver's slot cards include that candidate's cards. The fixed distinction text does **not** appear
  in any request on this base -- do not look for it there (preregistration section 3.2);
- **B4a only**: the Perception knowledge block shows the revised intent-card text on the smoke rows
  whose sealed selection contains a revised card, and is byte-identical to the anchor's on the others;
- one `*.request-fit.json` per realized contact under `$DATA/prepared/<FIT run id>/<fit attempt id>/`,
  every one with `every_request_fits = true`;
- the worker prints a seal and the tree is still clean.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops that cell until the fix is proven on this same four-row roster.

## 5. Step two: the campaigns

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-slot-store-v2-anchor-train-fold-a-v2.json" \
  --owner root-slurp-native-slot-store-v2-anchor-train-fold-a-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

Then, after B4b seals and only after it:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-v2.json" \
  --owner root-slurp-native-fallback-quirky-intent-v2-anchor-train-fold-a-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

And cell B4c **only if B4a admits**:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-intent-store-v2-anchor-train-fold-a-v2.json" \
  --owner root-slurp-native-intent-store-v2-anchor-train-fold-a-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

Each campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation, seals the manifest and schedules the single official score at
finalize through `core.scoring_batch`. Do not run `coordinate-fit`: the native gate fits every request
itself, and a standalone fit would double-charge the FIT row.

Expected per cell, from the anchor's own measured cost at this geometry: about 5,400 contacts
(5.016 per row) against the 11,880 ceiling, about 15,460 repeated speech seconds against the 33,930
ceiling, about 3.4 GPU hours against the 12.0 ceiling, and roughly 1 hour of wall clock plus about
3 minutes of official scoring. Nothing else may occupy the GPU while one flies, and CPU work runs at
8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for each lease window from that file; they
are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means a
CPU-only step, not a hang.

## 6. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the official
   score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` into that cell's analysis recipe and run the paired
   read exactly as the recipe pins it: `analysis.null_calibration_cli.rows_for` to read both sealed
   score registries, `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`, 10,000
   draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-<CELL>-ANCHOR-V2-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}`.
3. Run the projection-v3 reading over a COPY of the arm's sealed outputs with
   `slurp-slu-official-projected-v3-train` and report it beside every official number (owner decision
   7). The symmetric-normalised scorer has no TRAIN sibling and must not be forced onto this roster.
4. Compute the cell's mandatory diagnostics from the preregistration section 4 -- for B4b the per-type
   date/time FN/FP table and the six widened types; for B4a and B4c the `general` scenario intent,
   coverage with and without the fallback, the number of rows where the fallback was appended and the
   share of those where `general_quirky` was delivered, and the `general_quirky` → `qa_*` confusion
   count; for B4a additionally the realized per-row slot-card supply delta.
5. Apply the decision rule from the preregistration section 6 unchanged -- **B4a's primary is the
   intent gain with pooled SLU non-inferior within 1.1218 pp; B4b's and B4c's primary is pooled SLU
   with intent non-inferior within 1.0051 pp**. Publish
   `docs/results/2026-09-17-slurp-<cell>-anchor-v2-verdict.md` with the headline table (anchor, arm,
   delta, the released direct anchor as a secondary column), the projection-v3 table beside it, the
   saves/harms/ties table, the full 18-scenario table in both weightings, the diagnostics table and
   the cost table.
6. Close that cell's exposure rows: set `consumed` to `yes` and append the actual calls, actual
   repeated speech seconds, measured GPU hours, the sealed score and manifest SHA-256 values, and the
   verdict.
7. On ADMITTED, add the harness-admission entry for the module under the `stores` switch class and add
   it to the default plan. On NEUTRAL it enters the plan only if it lowers cost -- neither cell does,
   so NEUTRAL means not adopted. On HARMFUL it never arms a default plan.
8. **An admitted B4a does not attribute the gain to the fallback hypothesis.** Cell B4c and the per-row
   selection audit are what separate the store revision from the fallback; run B4c before claiming
   either half, and only if B4a admitted.

## 7. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b4-org-cells-anchor-v2/` (index `INDEX-v1.json`):

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `check-b4a-full-v1.json` | `8f8eee0f3e86e8ea21e3074bb15d032013311e849f97fd92854ff83f1f91eb71` | `core.flight.cli check` passes for cell B4a: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase, runtime hashes equal to the registered ones |
| `check-b4a-smoke-v1.json` | `76ac22aa48f415aeea34f85f2dbd2bdb6878878770abfddff6e89cd3e3bd812f` | the same for the B4a four-row smoke |
| `check-b4b-full-v1.json` | `e70cc33d1dba7f2a488385ee2d09f6186a071ae1d7d11d6f77912d5dbd15a9a4` | the same for cell B4b |
| `check-b4b-smoke-v1.json` | `3a64839230a43515446a17ee8808efe6b00b3194909def9dd189eae30d828a83` | the same for the B4b four-row smoke |
| `check-b4c-full-v1.json` | `793354748d93004c6ff6a48e502356e00590c2bba4bdd4cc82c52d4e16a26d6c` | the same for cell B4c |
| `phase-supply-vs-anchor-v1.json` | `ae0b10821f75491f7dec184daa820d11fe20fa039073b09c5421b00d369261f5` | all five prepared Perception artifacts carry a byte-identical `output` block to the sealed anchor preparation's, and each smoke matches the anchor's own four rows |
| `request-channel-proof-v1.json` | `3598de1aa75e73eadf8814f5e5889a0447806c348e2f5b1c41473d179cea3102` | the contact-by-contact request-channel proof over all 5,417 sealed anchor requests: every card re-derived from the released v1 snapshot, and the only difference each cell makes is its revised card texts |
| `fallback-supply-covariate-v1.json` | `f79017bf601e3568a95de80a74bce60030b930cab5f6a495b22c989ccb96fbec` | cell B4a's named covariate on the anchor's own realized candidate distribution: the fallback is appended on 1,063 of 1,080 rows, adds a median of 8 cards and displaces none, growing the Solver knowledge block by a mean of about 16 KB |
| `solver-knowledge-ceiling-v1.json` | `a913801b69393239c6f8e924dda2637a49e83ce2d8b33b777ceb2ceb320755aa` | the reachable Solver knowledge ceiling over all 34,220 legal candidate sets, its delta per cell, and 0 combinations whose slot selection moves with the store version |
| `prompt-fit-v1.json` | `68b42607aaa5d58454e0ba33a5eeb142281b6c48bec51561809e101cb7ef941f` | the per-contact prompt-fit bound against the 24,576-token slot, built on the anchor's 5,417 sealed fit receipts; every bound fits, worst margin 7,249 tokens (B4a planner) |
| `containment-v1.json` | `2c010d4271d385780254b28ba77cbaece3cf2cda32c2c5cbd9bd39a17e5e37df` | 0 containment collisions, verbatim and casefolded, for all four bound snapshots against all five control turns |
| `composed-hashes-v1.json` | `dfa1315e7a591de76e44d1971a83f86a99fb2aacc6615a18ac2f9c475048ff5f` | the composed and protocol hashes, the anchor method check, and the cell-versus-anchor composed-key diff |
| `plan-hashes-v1.txt` | `4a86970549756d399c8372b40d5e786b4d335526347f79f8bfb50a792f2cd0fa` | the SHA-256 of every config fragment, plan, protocol and recipe document in this package |
| `ledger-parse-v1.json` | `f37c8d65459234ebb7e3838ec617e5e8d04937dc0a76de703dcdb2734e2d83cc` | `contracts._parse_ledger_tables` sees the ten v2 rows exactly once with `consumed = no`, and the ten superseded v1 rows still unconsumed and annotated |

All five `check` receipts were produced at commit `d4965c5e`, the registration commit that carries
every config, plan and ledger row these cells fly; the documentation commit that follows it changes no
config, no plan and no ledger row. Do not re-run `derived_media_confinement_check.py` from inside the
checkout without reverting its in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would dirty
the tree the manifest reads at finalize.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real shared
speech renderer, and `wire_check` installs a text transport double. The sealed anchor, cell B0 and cell
B1 declare the same stages for the same reason. The contact-by-contact request-channel proof above is
the contact-free substitute and is stronger per contact.

## 8. Deviations the coordinator should know about

1. **The base is the sealed anchor, not cell B0.** Comparators, margins and budgets all follow from
   that. Preregistration section 14 lists every consequence.
2. **Experiment and run names carry `anchor` and `v2`; baseline names carry `anchor` too.** The run ids
   are the ones the coordinator specified.
3. **Separate smoke baseline fragments.** `native_contact_fit` carries the FIT run identity and the
   endpoint ceiling, which `build_native_contact_fit_gate` requires to equal
   `rows * max_contacts * (packets + 3)`. Sharing a full cell's fragment would have charged smoke
   contacts to that cell's FIT row.
4. **Cell B4c has no smoke**, and flies only if B4a admits (owner decision 9).
5. **The third fallback declaration site is unreachable here.** `rails.role_context` declares the same
   option at its own consumption site, but the sealed anchor declares no `native_episode.role_context`
   block, so E5a's two declarations are the complete reachable set. Recorded rather than silently
   omitted.
6. **The fallback's fixed distinction text reaches no request on this base.** Its entire
   request-visible effect is the extra slot cards. Preregistration section 3.2 corrects the v1 wording.
7. **Cell B4a moves two channels**, and the second one is large: a median of 8 extra slot cards and
   about 16 KB per contact on the anchor's own rows. The verdict must carry the covariate and must not
   attribute a gain to either half without cell B4c.
8. **Projection v3 is the agreement scorer**, because the symmetric-normalised scorer has no TRAIN
   sibling. The coordinator may register one before launch if a symmetric reading is wanted.
9. **The scenario null band is defined in the preregistration**, which v1 left open.
10. **No `wire-check` stage** on any cell, for the reason in section 7.
11. **Registered hashes are pre-flip.** Section 1; use the re-pin tool of section 2.

## 9. Smoke record (2026-09-17, coordinator)

Cell B4b's four-row smoke SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2 sealed at study commit
bc65ef84: 20 contacts, every row perception 1 / solver 1 / reviewer 2 / planner 1 routed ACCEPT, 4
task-contract tool calls, 20 request-fit receipts all fitting (minimum margin 11,094). Against the
anchor's sealed requests for the same four rows, the Perception evidence content is identical on every
item and the Solver, Reviewer and Planner evidence differs only on the revised slot cards (1 to 4
items per row: time, date, media_type); `request_id`, `evidence_provenance` and each item's
`source_uri` differ as bookkeeping, and the history differs only where the core's own Perception
output differs (greedy nondeterminism). Two operational facts recorded before the arm flew: the
B4b lease was first refused by the flight lock the aborted B1 campaign preserved by design, reconciled
by root after proving quiescence (receipt under
`$SPEECHRL_DATA_DIR/coordination/slurp-b1-exemplars-k20-anchor-v2/flight-lock-reconciliation-*.json`);
and the smoke ran while the GPU stayed in its idle power state (about 7 W, 43 s per contact), which
a non-model matmul ramp preflight now guards before every campaign launch (about 54 TFLOP/s and
92 W when healthy). B4b flew before the B1 recovery under ready-first GPU scheduling.

