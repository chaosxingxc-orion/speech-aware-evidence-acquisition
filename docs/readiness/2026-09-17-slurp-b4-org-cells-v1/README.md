# Cells B4a, B4b and B4c launch runbook: the ORG knowledge cells

Everything the coordinator needs to fly the three ORG cells and their two four-row smokes is in
this directory and in the committed configs. Preregistration:
[`../2026-09-17-slurp-b4-org-cells-v1-preregistration.md`](../2026-09-17-slurp-b4-org-cells-v1-preregistration.md).

The preparation agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**,
never started, stopped or queried the resident service, and ran no worker, campaign, smoke or FIT.

## 0. The gate before anything else

**Nothing here flies before the cell B0 verdict is recorded.** Cell B0 is both the base these
cells extend and their primary comparator. If B0 is **HARMFUL**, re-base all three cells on the
sealed anchor first — new baseline fragments, new prepared supplies, and every composed hash,
protocol hash, plan hash and ledger note in this package recomputed. The spec's Phase B table is
the authority. If B0 is NEUTRAL or better, this package flies as registered, in the spec's order:
B4a, then B4b, and B4c only if B4a admits.

## 1. What is registered

| item | value |
| --- | --- |
| B4a cell | experiment and cell `slurp-native-fallback-quirky-intent-v2-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-fallback-quirky-intent-v2-train-fold-a-generation-v1` |
| B4a FIT | `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-fallback-quirky-intent-v2-train-fold-a-fit-v1`, 8,640 endpoints, inside the same campaign |
| B4a smoke | experiment and cell `slurp-native-fallback-quirky-intent-v2-smoke-4-v1`, run `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-SMOKE-4-V1`, attempt `attempt-slurp-native-fallback-quirky-intent-v2-smoke-4-generation-v1` |
| B4a smoke FIT | `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-SMOKE-4-FIT-V1` / `attempt-slurp-native-fallback-quirky-intent-v2-smoke-4-fit-v1`, 32 endpoints |
| B4b cell | experiment and cell `slurp-native-slot-store-v2-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-SLOT-STORE-V2-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-slot-store-v2-train-fold-a-generation-v1` |
| B4b FIT | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-slot-store-v2-train-fold-a-fit-v1`, 8,640 endpoints |
| B4b smoke | experiment and cell `slurp-native-slot-store-v2-smoke-4-v1`, run `SAEA-SLURP-NATIVE-SLOT-STORE-V2-SMOKE-4-V1`, attempt `attempt-slurp-native-slot-store-v2-smoke-4-generation-v1` |
| B4b smoke FIT | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-SMOKE-4-FIT-V1` / `attempt-slurp-native-slot-store-v2-smoke-4-fit-v1`, 32 endpoints |
| B4c cell | experiment and cell `slurp-native-intent-store-v2-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-INTENT-STORE-V2-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-intent-store-v2-train-fold-a-generation-v1` |
| B4c FIT | `SAEA-SLURP-NATIVE-INTENT-STORE-V2-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-intent-store-v2-train-fold-a-fit-v1`, 8,640 endpoints |
| B4c smoke | **none** — it shares B4a's store, Perception geometry and prepared-supply inputs, so B4a's smoke evidence is reusable |
| campaign plans | `configs/campaign/slurp-native-fallback-quirky-intent-v2-train-fold-a-v1.json`, `…/slurp-native-slot-store-v2-train-fold-a-v1.json`, `…/slurp-native-intent-store-v2-train-fold-a-v1.json` |
| composed / protocol (B4a) | `814df815488d08c9bd625434eb93323b25ce1e015314342d376f230b4da2457e` / `a2c7ddf9fe18bb819a9ecaf8e743972a0591f394b268a56af501d09678a3318b` |
| composed / protocol (B4a smoke) | `eeef90e6e8ffdb6d44f802b096d31eb38d60a848a97ee884477edc16cedb56b5` / `0192634ef738f82c96d698998692a814585e36636e8306642858953280bd629c` |
| composed / protocol (B4b) | `9e677170e47f01c3f6eeeae359afde683eef07b7a9cf45a2cdaedecb40c6588a` / `e0e7ad859389bfff488a912fcc617c51db57784e757799cc06cce366d4e952e3` |
| composed / protocol (B4b smoke) | `d0f44d8cebe9f73980a6d0ecaae4a7bad6da6a8315f95680c7f68496d4a8257b` / `0088be970c2fdfa3e30189a4e7d77e277557a7966ef89d8fe7ac53e228a4915f` |
| composed / protocol (B4c) | `f9635063a5bf745119ab59bc3fd2b84733ae5c3d55de30bec9f564091d5cbab4` / `ed934dcff2d7a6b5d8ae9e6c950324656ab1f1e7aba9d313a2c6be46463ab428` |
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
            "slurp-native-review-off-fallback-quirky-intent-v2-train-fold-a-v1",
            "slurp-native-fallback-quirky-intent-v2-train-fold-a-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with each other baseline/experiment pair reproduces that cell's pair; the two
smokes use split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`. The
method is verified on this tree: run it on
`slurp-native-dual-store-train-fold-a-anchor-v1` as both baseline and experiment and it returns the
anchor's registered `d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

**These hashes describe the fragments exactly as committed at `c622334e`**: readiness `held`, the
preparation requirement pinned, `prepared_phase_supply` pinned. `compose` hashes the whole merged
four-fragment document, so flipping readiness and adding the decision requirement each change the
composed hash and therefore the protocol hash. Recompute and re-pin this package and the ten
exposure-ledger notes before launch, exactly as cells B0 and B1 did. `core.flight.cli check`
confirmed at `c622334e` that the runtime-derived hashes equal the registered ones for all five
cells.

## 2. Pre-launch checklist

1. Section 0 is closed: the cell B0 verdict exists, and if it was HARMFUL the re-basing is done.
2. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a
   COMPLETED manifest reads `study_commit` at finalize, so the checkout stays clean for the whole
   run. **Fly from a detached worktree pinned at the admitted commit**, because the main checkout
   carries untracked leftovers (`_tmp_slurp_gap_extract.py`, `integration_native_finite.py`,
   `wsl$/`) that would fail both gates. No receipt from this preparation lives inside the
   repository.
3. No flight process is running and no `locks/flight.lock` is held in the data root. One
   experiment in flight: seal each cell before opening the next.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
5. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
6. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
7. Fill the two `PENDING_B0_FINALIZE` digests (cell B0's score artifact and run manifest SHA-256)
   into `protocol-registered-v1.json` and the three analysis recipes.
8. Append the root decision requirement to each cell's `readiness.requirements`, then flip
   `readiness.state` from `held` to `ready` — the smoke first, its full cell only after the smoke
   seals. Commit each edit, because step 2 must still hold at launch, and recompute the hashes
   after each edit.

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

## 3. Step one: the four-row smoke (B4a, then later B4b)

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-fallback-quirky-intent-v2-smoke-4-v1 \
  --cell slurp-native-fallback-quirky-intent-v2-smoke-4-v1 \
  --owner root-slurp-native-fallback-quirky-intent-v2-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-fallback-quirky-intent-v2-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-fallback-quirky-intent-v2-smoke-4-v1 \
  --cell slurp-native-fallback-quirky-intent-v2-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-fallback-quirky-intent-v2-smoke-4-v1.worker-lease.json"
```

For cell B4b, substitute `slurp-native-slot-store-v2-smoke-4-v1` everywhere.

Expected: about 1 to 2 minutes of wall clock, 8 generation contacts, 32 FIT endpoints, about 21.2
repeated speech seconds, no scorer. Accept only if all of these hold:

- exactly 8 contacts, 2 per row, and no Reviewer or Planner contact in the trace;
- the episode receipt carries `review_loop_disposition = skipped_by_configuration` on every row;
- **B4a only**: on the rows where Perception omitted it, the Solver's candidate list carries
  `general_quirky` with `source = "fallback"` and the fixed distinction text, appended last and
  displacing no model candidate; the selection audit records `candidate_ids_without_fallback`;
- **B4a only**: the Perception knowledge block shows the revised intent-card text on the one smoke
  row whose sealed selection contains a revised card, and is byte-identical to cell B0's on the
  other three;
- **B4b only**: the Perception request is byte-identical to cell B0's smoke request on all four
  rows, and the Solver's slot cards show the revised text;
- one `*.request-fit.json` per realized contact under
  `$DATA/prepared/<FIT run id>/<fit attempt id>/`, every one with `every_request_fits = true`;
- the worker prints a seal and the tree is still clean.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops that cell until the fix is proven on this same four-row roster.

## 4. Step two: the campaigns

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-fallback-quirky-intent-v2-train-fold-a-v1.json" \
  --owner root-slurp-native-fallback-quirky-intent-v2-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

Then, after B4a seals and only after it:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-slot-store-v2-train-fold-a-v1.json" \
  --owner root-slurp-native-slot-store-v2-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

And cell B4c only if B4a admits:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-intent-store-v2-train-fold-a-v1.json" \
  --owner root-slurp-native-intent-store-v2-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

Each campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation, seals the manifest and schedules the single official score at
finalize through `core.scoring_batch`. Do not run `coordinate-fit`: the native gate fits every
request itself, and a standalone fit would double-charge the FIT row.

Expected per cell: 2,160 contacts at 2 per row and 6,169.06 repeated speech seconds against
ceilings of 2,160 and 6,170 — **the same contact count as cell B0**, because these modules add
prompt volume, not contacts. Cell B0's own measured generation cost at this geometry is the
reference; the registered fit-inclusive ceiling is 2.0 GPU hours per cell. Budget roughly 1.5 to 2
hours of wall clock for generation plus about 3 minutes of official scoring, per cell. Nothing
else may occupy the GPU while one flies, and CPU work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for each lease window from that file;
they are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means
a CPU-only step, not a hang.

## 5. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the
   official score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` into that cell's analysis recipe and run the
   paired read exactly as the recipe pins it: `analysis.null_calibration_cli.rows_for` to read
   both sealed score registries, `analysis.null_calibration.pooled_f1` for the pooled micro F1
   statistics, `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the
   bootstrap, whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner.
   Write `analysis/SAEA-SLURP-<CELL>-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}`.
3. Compute the cell's mandatory diagnostics from the preregistration section 4 — for B4b the
   per-type date/time FN/FP table and the six widened types; for B4a and B4c the `general`
   scenario intent, coverage with and without the fallback, the number of rows where the fallback
   was appended and the share of those where `general_quirky` was delivered, and the
   `general_quirky` → `qa_*` confusion count.
4. Apply the decision rule from the preregistration section 6 unchanged — **B4a's primary is the
   intent gain with pooled SLU non-inferior within 1.18 pp; B4b's and B4c's primary is pooled SLU
   with intent non-inferior within 0.92 pp**. Publish
   `docs/results/2026-09-17-slurp-<cell>-verdict.md` with the headline table (cell B0, arm, delta,
   the anchor as a secondary column), the saves/harms/ties table, the full 18-scenario table in
   both weightings, the diagnostics table and the cost table.
5. Close that cell's exposure rows: set `consumed` to `yes` and append the actual calls, actual
   repeated speech seconds, measured GPU hours, the sealed score and manifest SHA-256 values, and
   the verdict.
6. On ADMITTED, add the harness-admission entry for the module under the `stores` switch class and
   add it to the default plan. On NEUTRAL it enters the plan only if it lowers cost — neither cell
   does, so NEUTRAL means not adopted. On HARMFUL it never arms a default plan.
7. **An admitted B4a does not attribute the gain to the fallback hypothesis.** Cell B4c and the
   per-row selection audit are what separate the store revision from the fallback; run B4c before
   claiming either half.

## 6. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b4-org-cells-v1/` (index `INDEX-v1.json`):

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `check-b4a-full-v1.json` | `8363c1e3e31ad18c5e21c6463416ce4ca885f1f42f2ccd3522a800c1555d43cf` | `core.flight.cli check` passes for cell B4a: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase, runtime hashes equal to the registered ones |
| `check-b4a-smoke-v1.json` | `d5027de47b1fce45945744e56d55f21df3e40f92c4f6bf14d09408a85c289a1a` | the same for the B4a four-row smoke |
| `check-b4b-full-v1.json` | `65e14965e8542dd9ddeb43375b5be68ceb9074f33db56af1efa57ceb1cb75bba` | the same for cell B4b |
| `check-b4b-smoke-v1.json` | `f13a2c687cbac56f2bd4cbf5d541aa37403d5170f5e909e2ec4e09a6f9185460` | the same for the B4b four-row smoke |
| `check-b4c-full-v1.json` | `e5d2605cce4ed517bce7458469dcc86c87501dfc3782a2bcbec5d359c6f37430` | the same for cell B4c |
| `phase-supply-vs-base-v1.json` | `f439fc1045e1850522a8776eb6266222cd6a71102503ec46d09927697a09b764` | all five prepared Perception artifacts carry a byte-identical `output` block to cell B0's and the sealed anchor's |
| `request-channel-proof-v1.json` | `977b00c769c71da728b66d27486fc9a9a7cac34fac799d5e2dcbc88c0a91f71b` | the row-for-row request-channel proof: Perception selection and text, and the exhaustive store-version invariance of the Solver's slot selection |
| `request-envelope-comparison-v1.json` | `236f1c5fd6a2e17934e68589a63ec304e09b749b9b932144cc64cd89b5428873` | the worst-case budget envelope grows by a constant amount on every row and every phase |
| `request-envelope-digests-v1.json` | `ae93e09a7bbead9510ecb96c03af80b46c6425786e11bb13cdb64c9bbe4c03ad` | the per-row, per-phase envelope digests behind that claim |
| `fallback-supply-covariate-v1.json` | `3506b63434b6dc059f58b5b2e1f399d5e638cde7c37cb9d87ed8070955a10076` | cell B4a's named covariate: `general_quirky` binds 16 of 54 cards and the appended fallback adds a median of 7 values within the 16/28 caps |
| `solver-knowledge-ceiling-v1.json` | `8a7b0c86e0ee2b62d9add580d13bbabbb003bd0ef3a46566af841421671f4672` | the reachable Solver knowledge ceiling over every legal candidate set, and its delta per cell |
| `prompt-fit-v1.json` | `f9292b31d4519c2b14b3c7885e7296127151ae0ec83cdff843cbbd0e24823236` | the prompt-fit statement against the 24,576-token slot, decision ALLOW |
| `containment-v1.json` | `39ac50e37ebb0c2656049b3cd88587db18e7e8f842810c8468018fb0ce4b540c` | 0 containment collisions, verbatim and casefolded, for all four bound snapshots against all five control turns |
| `composed-hashes-v1.json` | `c9e3e1a43c9844f9aa75cbfdc9efb5a400cf38af9c9222294b36dba1fc2617bd` | the composed and protocol hashes, the anchor method check, and the cell-versus-B0 composed-key diff |
| `plan-hashes-v1.txt` | `29fd135b3089550ce0e8c679b2f5a8a1855ff5ec713112e639fb40429a909da5` | the SHA-256 of every plan, protocol and recipe document in this directory |
| `ledger-parse-v1.json` | `986789123f575fa9c4883e501703c86afad97e328be8d00cf85ef35b85eba135` | `contracts._parse_ledger_tables` sees all ten rows exactly once, each `consumed = no` |
| `wire-check-smoke-v1.stderr.txt` | `c0db5657a42f90a7011ea6c751ce416409e0ffaa0b3994e219fb54e60a6a0fec` | why no cell declares the `wire-check` stage |

All five `check` receipts were produced at commit `c622334e`, the registration commit that carries
every config, plan and ledger row these cells fly; the documentation commit that follows it changes
no config, no plan and no ledger row. Do not re-run `derived_media_confinement_check.py` from
inside the checkout without reverting its in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
dirty the tree the manifest reads at finalize.

Prompt fit against the 24,576-token slot. Model-free estimate over the widest request each phase
renders across the whole roster, decision ALLOW everywhere: B4a and B4c perception 19,551 required
window tokens (margin 5,025) and solver 19,594 (margin 4,982); B4b perception 19,990 (margin
4,586) and solver 20,033 (margin 4,543). Measured, from the anchor's sealed fit receipts for
exactly these two contacts: `perception:0` at most 4,270 tokens (minimum margin 20,306) and
`solver:0` at most 13,157 (minimum margin 11,419), 1,080 contacts each, all fitting; adding the
measured knowledge bytes under the repository's stated word proxy gives at most 19,353 tokens on
cell B4a's Solver, the tightest of the three, with 5,223 tokens of margin.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. The sealed anchor, cell
B0 and cell B1 declare the same stages for the same reason. The row-for-row request-channel proof
above is the contact-free substitute and is stronger per row.

## 7. If master moves before launch

The registered **protocol and plan hashes survive a merge**: they derive from the four config
fragments only. The **prepared phase-supply artifacts do not**. Their identity digest
(`core.preparation.artifact_inputs`) pins the SHA-256 of `rails.kb_policy`,
`rails.knowledge_provider`, `rails.phase_supply`, `rails.knowledge_stores` and
`core.flight.runtime`, so once any of those files changes, `_load_phase_supply_seed` raises
*prepared artifact identity mismatch* at dispatch.

After merging master into the flight branch, and before flipping readiness, re-pin all five
supplies:

```bash
for CELL in slurp-native-fallback-quirky-intent-v2-smoke-4-v1 \
            slurp-native-fallback-quirky-intent-v2-train-fold-a-v1 \
            slurp-native-slot-store-v2-smoke-4-v1 \
            slurp-native-slot-store-v2-train-fold-a-v1 \
            slurp-native-intent-store-v2-train-fold-a-v1; do
  case "$CELL" in
    slurp-native-fallback-quirky-intent-v2-smoke-4-v1)      RUN=SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-SMOKE-4-V1 ;;
    slurp-native-fallback-quirky-intent-v2-train-fold-a-v1) RUN=SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-TRAIN-FOLD-A-V1 ;;
    slurp-native-slot-store-v2-smoke-4-v1)                  RUN=SAEA-SLURP-NATIVE-SLOT-STORE-V2-SMOKE-4-V1 ;;
    slurp-native-slot-store-v2-train-fold-a-v1)             RUN=SAEA-SLURP-NATIVE-SLOT-STORE-V2-TRAIN-FOLD-A-V1 ;;
    *)                                                      RUN=SAEA-SLURP-NATIVE-INTENT-STORE-V2-TRAIN-FOLD-A-V1 ;;
  esac
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-supply \
    --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
    --experiment "$CELL" --cell "$CELL" --workers 8 \
    --output "$DATA/prepared/$RUN/phase-supply-v2.json"
  sha256sum "$DATA/prepared/$RUN/phase-supply-v2.json"
done
```

`prepare-supply` refuses to run while `prepared_phase_supply` names a file that does not exist, so
remove that key transiently, prepare, then pin. Then, in order:

1. write the new relpath and SHA-256 into `prepared_phase_supply` of the five baseline fragments
   and into `cells[0].readiness.requirements` of the five experiment fragments;
2. confirm the new artifacts still select what the base selected: the `output` block of every full
   cell's artifact must equal
   `prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1/phase-supply-v2.json`'s on all 1,080
   rows, and each smoke's against
   `prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1/phase-supply-v2.json` on its 4 — the
   `output_sha256` values to reproduce are `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`
   and `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733`;
3. recompute the composed and protocol hashes with the command in section 1 — **re-pinning changes
   the composed config hash**, because `compose` hashes the whole merged fragment set;
4. rewrite the documents in this directory with the new hashes, and the ten exposure-ledger notes
   with the new plan SHA-256 values and protocol hashes;
5. re-run `core.flight.cli check` for the five cells and confirm the runtime-derived protocol hash
   equals the registered one again.

Nothing else in this package depends on the merge.

## 8. Deviations the coordinator should know about

1. **`phase_tools` kept.** The arm `speech-feature-query-native-tools` declares `tool_schemas` and
   `FlightRuntime.frozen_core_client_kwargs` has no schema source without `phase_tools`, so the
   review-off block is carried verbatim and inert, exactly as cell B0's README section 8 deviation
   1 requires. It also keeps the tool block of every request identical to B0's.
2. **Experiment and run names drop `review-off`; baseline names keep it.** The run ids are the ones
   the coordinator specified and the experiment fragments follow them; the baseline fragment names
   keep `review-off` to record which base they extend. This is the cell B1 convention.
3. **Separate smoke baseline fragments.** `native_contact_fit` carries the FIT run identity and the
   endpoint ceiling, which `build_native_contact_fit_gate` requires to equal
   `rows * max_contacts * (packets + 3)`. Sharing a full cell's fragment would have charged smoke
   contacts to that cell's FIT row.
4. **Cell B4c has no smoke.** By the coordinator's instruction, and because its store, Perception
   geometry and prepared-supply inputs are cell B4a's. If the coordinator would rather not reuse
   B4a's smoke evidence, B4c needs its own smoke baseline fragment, experiment fragment and two
   ledger rows before it flies.
5. **The third fallback declaration site is unreachable here.** `rails.role_context` declares the
   same option at its own consumption site, but the review-off base declares no
   `native_episode.role_context` block, so E5a's two declarations are the complete reachable set.
   Recorded rather than silently omitted.
6. **The prompt-budget envelope is not a request.** `render_phase_prompt_envelopes` size-ranks the
   worst-case cards, so the v2 revisions change which cards enter that worst case. The per-row
   proof lives in `request-channel-proof-v1.json`, not in the envelope comparison. See
   preregistration section 3.1.
7. **Cell B4a moves two channels.** The fallback hypothesis and the intent store revision travel
   together, and the fallback also enlarges the Solver's slot-card supply (median +7 values). The
   verdict must carry the covariate and must not attribute a gain to either half without cell B4c.
8. **No `wire-check` stage** on any cell, for the reason in section 6.
9. **Registered hashes are pre-flip.** Section 1. The coordinator recomputes after appending the
   decision requirement and flipping readiness, exactly as B0 and B1 did.

## 9. Postscript: master moved while this package was being prepared

This registration is based on `6c5c9ab7`. While it was being prepared, master advanced to
`2b960418` and two facts landed that the coordinator needs before launching anything here.

**1. The cell B0 verdict exists, and it is HARMFUL -- on width, not on a loss.**
`docs/results/2026-09-17-slurp-b0-review-off-verdict.md` records
`SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1` as **HARMFUL by the preregistered intent clause**:
pooled SLU +0.13 [-1.15, +1.45], intent -0.37 [-1.53, +0.82]. The intent CI95 lower bound of -1.53
sits below the -0.92 null margin, so the rule fires -- but the point estimate is nil and every
saves/harms table is a tie (intent 22 / 26 / 1,032, p = 0.67). The verdict itself calls it *a width
failure with a nil point estimate* and registers a same-roster own-null replicate, cell B0r, with a
re-decision rule (`docs/readiness/2026-09-17-slurp-b0-replicate-v1-preregistration.md`). B0's sealed
digests are score `51f37e6c5a78751f2d000ac370cff6f0fff18745cd18d1fc81a2cd145ce960ae` and run
manifest `8b6f3f783f1933c4009c46cdc01472e240c547a496f7553c07e5efe301cdfe32`; those are the two
`PENDING_B0_FINALIZE` values the checklist asks for.

**What that means for these three cells.** Section 0's re-basing clause is now live but not yet
settled: the base decision belongs to the B0r re-decision, not to the raw HARMFUL label. Do not
re-base reflexively. If the re-decision leaves cell B0 usable as the base, this package flies
exactly as registered. If it does not, rebuild the five baseline fragments on the sealed anchor,
re-prepare all five phase supplies, and recompute every composed hash, protocol hash, plan hash and
ledger note here -- the preparation is otherwise unaffected, because the moved ORG channels are
identical on either base.

**2. The registered hashes survive the merge; the prepared supplies do not.** Master's
`6c5c9ab7..2b960418` range touches `src/.../core/config.py` and `src/.../rails/knowledge_stores.py`
(the E3b candidate-and-phase-supply router fix that unblocks cell B1). Verified on this tree by
composing these five fragments against **master's** `core.config`: all five composed hashes and all
five protocol hashes reproduce unchanged, and master's new
`assert_preparation_source_receipts_are_well_formed` accepts every one of the five fragments (they
inherit the review-off base's `"root": "data"` pins, not the `"root": "repo"` spelling that check
was written to catch). But `rails.knowledge_stores` is one of the five module files whose SHA-256
the prepared phase-supply artifact identity pins, so **all five prepared supplies must be
re-prepared and re-pinned after the merge**: section 7 is a requirement here, not a contingency.
The `output` blocks to reproduce are `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`
(full cells) and `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` (smokes).

Nothing else in this package depends on the merge, and the five `check` receipts still describe the
configs, plans and ledger rows exactly as committed at `c622334e`.

## 10. Superseded before contact

**This package is SUPERSEDED BEFORE CONTACT, on 2026-09-17, and must not be flown.** It never flew:
all ten of its exposure-ledger rows stay `consumed = no`, and each now carries a supersession note.

Section 0's re-basing clause fired. Module M0 (the review loop off) was re-decided **HARMFUL** under
the TRAIN A own null measured by the replicate cell B0r -- h_SLU 1.1218 pp and h_intent 1.0051 pp at
CI95, with the intent clause failing on both passes (owner decision 6 of 2026-09-17). The
Reviewer/Planner loop therefore stays in the default plan, cell B0 is not a usable base, and all
three ORG cells were rebuilt on the sealed dual-store anchor
`configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json`.

The successor package is:

- preregistration `docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2-preregistration.md`;
- runbook `docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2/README.md`;
- five baseline fragments `configs/baseline/slurp-native-anchor-*-v2.json`, five experiment fragments
  `configs/experiment/slurp-native-*-anchor-*-v2.json`, three campaign plans
  `configs/campaign/slurp-native-*-anchor-train-fold-a-v2.json`;
- ten new exposure rows, all `consumed = no`;
- pre-contact evidence under
  `SPEECHRL_DATA_DIR/coordination/slurp-b4-org-cells-anchor-v2/`.

The moved ORG channels, the questions, the metrics, the diagnostics and the claim boundary are
identical on either base. What changed is the base, the comparators (the sealed anchor primary, the
released direct anchor secondary), the margins (the TRAIN A own null rather than the imported DEV-1000
margins), the budgets (eleven contacts per row), and every composed, protocol, plan and ledger hash.
The successor's section 14 lists every deviation, including two corrections to this document: the
appended fallback's fixed distinction text reaches no request, and its realized slot-card supply delta
is far larger than this document's reachable-ceiling framing suggested.

Nothing in this directory is edited otherwise; it stays on file as the superseded record.
