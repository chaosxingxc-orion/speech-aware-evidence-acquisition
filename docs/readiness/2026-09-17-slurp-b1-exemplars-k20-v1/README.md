# Cell B1 launch runbook: speech-keyed exemplar supply to the Solver

Everything the coordinator needs to fly cell B1, its twin and its four-row smoke is in this directory
and in the committed configs — **except one production fix that this preparation deliberately did not
make.** Read section 0 before anything else. Preregistration:
[`../2026-09-17-slurp-b1-exemplars-k20-v1-preregistration.md`](../2026-09-17-slurp-b1-exemplars-k20-v1-preregistration.md).

The preparation agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**, never
started, stopped or queried the resident service, and never touched cell B0 or its pinned worktree
while B0 was in flight.

## 0. The blocking gate

`rails.knowledge_stores.build_knowledge_store_supply` refuses this configuration:

```
candidate, explicit, and scoped supply cannot overlap on phase(s) ['solver']
```

`slot-contracts` serves the Solver through `candidate_supply` (the base) while `train-exemplars`
serves it through `phase_supply` (module M1). The per-store collision guard in
`build_knowledge_store_supply` tests each store's explicit specs against the *global* candidate specs
and refuses the overlap, so the router cannot even be constructed — `check`, `prepare-supply`, the
smoke and both campaigns all fail at the same frame.

**It is inherited from E3, not introduced here.** Commit `cfdf08fb` added `plain_later_phase_specs`
and extended `automatic_for_phase` to compose a later-phase plain `phase_supply` alongside
`context_supply` and `candidate_supply`, and its own module comment names *"this program's anchor:
`slot-contracts` candidate_supply.solver plus the new `train-exemplars` phase_supply.solver"* as the
case it fixes — but it left the older guard and its test
(`tests/unit/test_knowledge_stores_e3_exemplar_supply.py`) covers only the `context_supply` pairing.
A throwaway experiment fragment on the **anchor** policy pointing at the committed
`configs/baseline/slurp-native-dual-store-train-fold-a-exemplars-k20-v1.json` raises the identical
refusal at the identical frame, so the committed k20, k20-twin and k12 fragments are all affected.

A second defect: those three committed E3 fragments pin the exemplar knowledge receipt with
`"root": "repo"`, and `core.preparation.verify_source_receipts` accepts only `repository` and `data`.
The three B1 fragments here use `repository`.

**Diagnosed sufficient change, verified in a throwaway tree and NOT applied to this repository.**
Narrowing the guard to first-phase explicit specs:

```python
collisions = ({phase for phase in specs if phase == first_phase} | scoped_phases).intersection(candidate_specs)
```

With that one line, `core.flight.cli prepare-supply` completed model-free for all three B1 cells at
`--workers 8` in 18 to 21 seconds each, and the rebuilt Perception artifacts reproduced the sealed
cell B0 artifact `output` and the sealed anchor artifact `output` **exactly on 1080/1080 rows** (and
the smoke against B0's own smoke artifact on its 4 rows). Still unproven, and owed by the engineering
item: that `_compose_supplies` accepts the candidate supply alongside the exemplar supply at dispatch.

It is not applied here because it is a production change that owes its own reviewed engineering item
and test, and because `rails.knowledge_stores` is one of the five module files whose SHA-256 the
prepared phase-supply artifact identity pins — an artifact prepared against an unreviewed patch is
invalid the moment that patch is reshaped in review.

**Unblocking sequence, in order:**

1. Land a reviewed engineering item that narrows the guard and adds the missing test (a composition
   of `candidate_supply` and a later-phase plain `phase_supply` on one phase).
2. Correct `"root": "repo"` to `"root": "repository"` in the three committed E3 fragments.
3. `prepare-supply` the three B1 cells (section 7 below).
4. Confirm the arm artifact `output` equals the sealed cell B0 artifact `output` on 1080/1080 rows.
5. Pin `prepared_phase_supply` in the three baselines and the `preparation` readiness requirement in
   the three experiment fragments.
6. Recompute the composed and protocol hashes (section 1) and re-pin this package and the six
   exposure-ledger notes.
7. Run `check` for the three cells and record the receipts under the coordination root.
8. Only then flip readiness and fly the smoke.

Receipt: `$DATA/coordination/slurp-b1-exemplars-k20-v1/store-router-blocker-v1.json`, with raw
refusals in `store-router-blocker-v1.log`.

## 1. What is registered

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-exemplars-k20-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-exemplars-k20-train-fold-a-generation-v1` |
| arm FIT | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-exemplars-k20-train-fold-a-fit-v1`, 8,640 endpoints, inside the same campaign |
| twin cell | experiment and cell `slurp-native-exemplars-k20-twin-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-TWIN-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-exemplars-k20-twin-train-fold-a-generation-v1` |
| twin FIT | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-TWIN-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-exemplars-k20-twin-train-fold-a-fit-v1`, 8,640 endpoints |
| smoke cell | experiment and cell `slurp-native-exemplars-k20-smoke-4-v1`, run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-SMOKE-4-V1`, attempt `attempt-slurp-native-exemplars-k20-smoke-4-generation-v1` |
| smoke FIT | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-SMOKE-4-FIT-V1` / `attempt-slurp-native-exemplars-k20-smoke-4-fit-v1`, 32 endpoints |
| campaign plans | `configs/campaign/slurp-native-exemplars-k20-train-fold-a-v1.json`, `configs/campaign/slurp-native-exemplars-k20-twin-train-fold-a-v1.json` |
| composed / protocol (arm) | `39ce13ecae402b31bbd062acb459534b17bf2c57b0041f723304bdd720bdc7f7` / `2ccd722e0319a2daf831bfc01a00aa2cf993ec97a5d7545e9493a97a54cd91c3` |
| composed / protocol (twin) | `94df17ed9d6379f5f0152cad750182b7c95b7b07c9ee89f00c817a85567c7a32` / `4735f4b7949c6b2e587d97e5d4df2050b43a1e0ee466689021bf2b435a84bb4d` |
| composed / protocol (smoke) | `e967065c01ec49146bd3d923b3297e28af742698290100c8693fafce97f4dd51` / `80673120409682e019c7fe303ca2de85bfe9911a8abd8ab609490fd1ad37e1a2` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | all three cells are `held` with an empty requirement list; the coordinator adds the decision requirement, adds the preparation requirement after step 3 of section 0, and flips |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-review-off-exemplars-k20-train-fold-a-v1",
            "slurp-native-exemplars-k20-train-fold-a-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with the twin fragment pair reproduces the twin pair, and with the two smoke
fragment names plus split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`
the smoke pair. The method is verified: run it on the anchor fragments and it returns the anchor's
registered `d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

**These hashes describe the fragments exactly as committed: readiness `held`, requirements empty,
`prepared_phase_supply` absent.** `compose` hashes the whole merged four-fragment document, so pinning
the prepared supply, adding the preparation requirement and flipping readiness each change the
composed hash and therefore the protocol hash. Recompute and re-pin before launch. The same mechanism
explains why cell B0's registered `45fe779f…` no longer reproduces on master at `02f2f0af` (the later
E6 merge added `native_episode.review_loop` to its baseline); B0 flies from a worktree pinned at
`5d0d694d`, where its registered hashes hold, so its flight is unaffected. See
`composed-hashes-v1.json` for all of it, including B0's held-state hashes
`29128fdc…` / `990c7b23…` which its own `check-full-v2.json` reports.

## 2. Pre-launch checklist

1. Section 0 is closed. Nothing below runs until it is.
2. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a COMPLETED
   manifest reads `study_commit` at finalize, so the checkout stays clean for the whole run. **Flights
   run from a detached worktree pinned at the admitted commit**, because the main checkout carries
   untracked leftovers (`_tmp_slurp_gap_extract.py`, `integration_native_finite.py`, `wsl$/`) that
   would fail both gates. No receipt from this preparation lives inside the repository.
3. No flight process is running and no `locks/flight.lock` is held in the data root. Cell B0 must be
   finalized: one experiment in flight.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
5. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package closes
   the D3 gate.
6. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
7. **If cell B0 was HARMFUL**, re-base both full cells on the sealed anchor before going further: the
   baseline fragments become anchor-based, and every hash in this package is recomputed. The spec's
   Phase B table is the authority.
8. Fill the two `PENDING_B0_FINALIZE` digests (cell B0's score artifact and run manifest SHA-256) into
   `protocol-registered-v1.json` and `analysis-recipe-v1.json`.
9. Flip `readiness.state` from `held` to `ready` in `configs/experiment/slurp-native-exemplars-k20-smoke-4-v1.json`
   first, and in the two full experiment fragments only after the smoke seals. Commit each flip,
   because step 2 must still hold at launch, and recompute the hashes after each flip.

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
  --experiment slurp-native-exemplars-k20-smoke-4-v1 \
  --cell slurp-native-exemplars-k20-smoke-4-v1 \
  --owner root-slurp-native-exemplars-k20-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-exemplars-k20-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-exemplars-k20-smoke-4-v1 \
  --cell slurp-native-exemplars-k20-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-exemplars-k20-smoke-4-v1.worker-lease.json"
```

Expected: about 1 to 2 minutes of wall clock, 8 generation contacts, 32 FIT endpoints, about 21.2
repeated speech seconds, no scorer. Accept only if all five hold:

- exactly 8 contacts, 2 per row, and no Reviewer or Planner contact in the trace;
- the episode receipt carries `review_loop_disposition = skipped_by_configuration` on every row;
- the Solver request carries the `train-exemplars::…` typed content blocks, twenty per row, and the
  Solver instruction body is unchanged from cell B0's;
- one `*.request-fit.json` per realized contact under
  `$DATA/prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-SMOKE-4-FIT-V1/attempt-slurp-native-exemplars-k20-smoke-4-fit-v1/`,
  every one with `every_request_fits = true` and the Solver requirement below 24,576 (the registered
  upper bound is 14,240);
- the worker prints a seal and the tree is still clean.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops cell B1 until the fix is proven on this same four-row roster.

## 4. Step two: the arm campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-exemplars-k20-train-fold-a-v1.json" \
  --owner root-slurp-native-exemplars-k20-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

## 5. Step three: the twin campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-exemplars-k20-twin-train-fold-a-v1.json" \
  --owner root-slurp-native-exemplars-k20-twin-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

One cell in flight at a time: seal the arm before launching the twin. Each campaign acquires its own
`GenerationLease` against the resident session, fits each realized native request inside generation,
seals the manifest and schedules the single official score at finalize through `core.scoring_batch`.
Do not run `coordinate-fit`: the native gate fits every request itself, and a standalone fit would
double-charge the FIT row.

Expected per arm: 2,160 contacts at 2 per row and 6,169.06 repeated speech seconds against ceilings of
2,160 and 6,170. Cell B0's own measured generation cost at this geometry is the reference; the
registered fit-inclusive ceiling is 2.0 GPU hours per arm and the exemplar block adds prompt tokens,
not contacts, so the arm should land near B0's cost plus the prefill of at most 1,083 extra tokens per
Solver contact. Budget roughly 1.5 to 2 hours of wall clock for generation plus about 3 minutes of
official scoring, per arm. Nothing else may occupy the GPU while either flies, and CPU work runs at 8
workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for each lease window from that file; they
are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means a
CPU-only step, not a hang.

## 6. Post-flight

1. Confirm each manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and each official
   score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256 for both arms.
2. Fill `scores_sha256` and `run_manifest_sha256` for all four arms into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that recipe
   pins it: `analysis.null_calibration_cli.rows_for` to read the sealed score registries,
   `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`, 10,000
   draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B1-EXEMPLARS-K20-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}` with all
   four contrasts of the recipe.
3. Compute the three mandatory diagnostics: realized candidate-union coverage against A2's 0.9722,
   the Solver escape-to-neighbour-intent rate, and the exemplar token volume actually rendered.
4. Apply the decision rule from the preregistration section 7 unchanged. Publish
   `docs/results/2026-09-17-slurp-b1-exemplars-k20-verdict.md` with the headline table (base, arm,
   twin, both deltas), the saves/harms/ties table against base and twin, the full 18-scenario table in
   both weightings, the diagnostics table and the cost table.
5. Close the six exposure rows: set `consumed` to `yes` for all six run ids and append to each note the
   actual calls, actual repeated speech seconds, measured GPU hours, the sealed score and manifest
   SHA-256 values, and the verdict.
6. On ADMITTED, add the harness-admission entry for M1 under the `stores` switch class
   (`switch.key = knowledge_stores.train-exemplars`, `switch.off = null`, and a `switch.proof` test
   that composes the two committed fragments) and add the store to the default plan. On NEUTRAL it
   enters the plan only if it lowers cost; on HARMFUL it never arms a default plan.

## 7. Preparing the phase supply (step 3 of section 0)

Once the guard is closed, and before flipping readiness:

```bash
for CELL in slurp-native-exemplars-k20-smoke-4-v1 \
            slurp-native-exemplars-k20-train-fold-a-v1 \
            slurp-native-exemplars-k20-twin-train-fold-a-v1; do
  case "$CELL" in
    *smoke*) RUN=SAEA-SLURP-NATIVE-EXEMPLARS-K20-SMOKE-4-V1 ;;
    *twin*)  RUN=SAEA-SLURP-NATIVE-EXEMPLARS-K20-TWIN-TRAIN-FOLD-A-V1 ;;
    *)       RUN=SAEA-SLURP-NATIVE-EXEMPLARS-K20-TRAIN-FOLD-A-V1 ;;
  esac
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-supply \
    --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
    --experiment "$CELL" --cell "$CELL" --workers 8 \
    --output "$DATA/prepared/$RUN/phase-supply-v1.json"
  sha256sum "$DATA/prepared/$RUN/phase-supply-v1.json"
done
```

`prepare-supply` refuses to run while `prepared_phase_supply` names a file that does not exist, which
is why the committed baselines omit the key: prepare first, then pin. The key is in
`core.preparation._RECEIPT_KEYS`, so adding it afterwards does **not** invalidate the artifact
identity; neither does the readiness flip, because `artifact_inputs` strips each cell's `readiness`.
Both do change the composed config hash.

Then, in order:

1. write the new relpath and SHA-256 into `prepared_phase_supply` of the three baseline fragments, and
   into `cells[0].readiness.requirements` of the three experiment fragments as a `preparation` entry;
2. confirm the new artifacts still select what the base selected: the `output` of the arm cell's
   artifact must equal the `output` of
   `prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1/phase-supply-v2.json` on all 1,080 rows (it
   did in the throwaway diagnostic tree, and it also equals the anchor's own
   `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-PREPARE-V1-R2/phase-supply.json` output), and the
   smoke's against `prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1/phase-supply-v2.json` on its 4;
3. recompute the composed and protocol hashes with the command in section 1 — re-pinning changes the
   composed config hash, because `compose` hashes the whole merged fragment set;
4. rewrite the fourteen documents in this directory with the new hashes, and the six exposure-ledger
   notes with the new plan SHA-256 values and protocol hashes;
5. re-run `core.flight.cli check` for the three cells and confirm the runtime-derived protocol hash
   equals the registered one again.

The artifact identity digest pins the SHA-256 of `rails.kb_policy`, `rails.knowledge_provider`,
`rails.phase_supply`, `rails.knowledge_stores` and `core.flight.runtime`. The engineering item that
closes section 0 changes `rails.knowledge_stores`, so the preparation must happen **after** it lands,
not before.

## 8. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b1-exemplars-k20-v1/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `store-router-blocker-v1.json` | `a4a215493b5a43a7dd869b10b2cd38de390d43ce11f87ba34889a0c361e9a27e` | the blocking gate, its inheritance from E3, the diagnosed sufficient change, and what the engineering item still owes |
| `store-router-blocker-v1.log` | — | the raw refusal for each of the three B1 cells |
| `composed-hashes-v1.json` | `86b7e9637bc6f3b634c3c52f1b869d359cdbe380e303ba4b2d32bbd90b48f236` | the composed and protocol hashes for all three cells, the anchor method check, and the explained cell B0 hash drift on master |
| `containment-v1.json` | — | 0 collisions between the 9,354 rendered exemplar values and every composed instruction text; no no-example projection needed |
| `exemplar-prompt-fit-v1.json` | — | the k = 20 and k = 12 exemplar block size distributions, cross-checked against the real provider on 5 rows per k |
| `twin-derangement-proof-v1.json` | — | 0 fixed points on 1,080 rows, recomputed from the sealed vector files alone, with the one-row bijection shortfall recorded |
| `plan-hashes-v1.txt` | — | the SHA-256 of every plan document in this directory |
| `ledger-parse-v1.json` | — | `contracts._parse_ledger_tables` sees all six rows exactly once, each `consumed = no`, 854 rows parsed in total |

Prompt fit against the 24,576-token slot: measured base `solver:0` at most 13,157 tokens from the
anchor's 5,417 sealed fit receipts, plus at most 1,083 exemplar-block proxy tokens, gives a strict
upper bound of 14,240 required tokens and a margin of at least 10,336. k = 12 remains the registered
fallback and is not needed.

Blocked and therefore absent: `check` receipts for the three cells, `prepare-supply` receipts against
this repository, the `prepared_phase_supply` pins and the preparation readiness requirements, and the
request-envelope comparison against cell B0's rendered requests. `core.flight.cli wire-check` is
unavailable for any native-episode cell: `FlightRuntime._dispatch_phase_program` refuses a native
episode whose transport is not the real shared speech renderer, and `wire_check` installs a text
transport double — the sealed anchor and cell B0 declare the same stages for the same reason. Do not
re-run `derived_media_confinement_check.py` from inside the checkout without reverting its in-repo
receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would dirty
the tree the manifest reads at finalize.

## 9. Deviations the coordinator should know about

1. **The cell is blocked and three deliverables are missing.** Section 0. The `check` receipts,
   `prepare-supply` receipts, the `prepared_phase_supply` pins, the preparation readiness requirements
   and the request-envelope comparison could not be produced. Everything else is final.
2. **No production code was changed.** The guard fix was diagnosed and verified in a throwaway tree
   (`/home/chao/saea-worktrees/b1-guard-diagnostic`, deleted after use) and deliberately left to its
   own reviewed engineering item, because `rails.knowledge_stores` is inside the prepared artifact's
   identity digest and because cell B0 was in flight.
3. **`phase_tools` kept.** The arm `speech-feature-query-native-tools` declares `tool_schemas` and
   `FlightRuntime.frozen_core_client_kwargs` has no schema source without `phase_tools`, so the
   review-off block is carried verbatim and inert, exactly as cell B0's README section 8 deviation 1
   requires. It also keeps the tool block of every request identical to B0's.
4. **`"root": "repository"`, not `"repo"`.** The E3 fragments' source-receipt root name is invalid;
   corrected in the three B1 fragments and still open in the three committed E3 fragments.
5. **Separate smoke baseline fragment.** `native_contact_fit` carries the FIT run identity and the
   endpoint ceiling, which `build_native_contact_fit_gate` requires to equal
   `rows * max_contacts * (packets + 3)`. Sharing the arm's fragment would have charged smoke contacts
   to the arm's FIT row.
6. **Experiment and run names drop `review-off`; baseline names keep it.** The run ids are the ones the
   coordinator specified (`SAEA-SLURP-NATIVE-EXEMPLARS-K20-…`) and the experiment fragments follow
   them; the baseline fragment names keep `review-off` to record which base they extend.
7. **The twin is not a strict permutation.** 0 fixed points, but one source vector serves two rows and
   one serves none — the arithmetic consequence of the provenance's declared `cross_group_rows: 1`.
   Recorded, not smoothed over.
8. **No `wire-check` stage** on any cell, for the reason in section 8.
9. **Registered hashes are pre-pin.** Section 1. The coordinator recomputes after pinning the supply
   and flipping readiness, exactly as B0 did.
## 10. Superseded before contact

**This package was never flown and is superseded by
[`../2026-09-17-slurp-b1-exemplars-k20-anchor-v2/README.md`](../2026-09-17-slurp-b1-exemplars-k20-anchor-v2/README.md)**
(preregistration
[`../2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md`](../2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md)),
which registers the same cell on the sealed dual-store anchor.

Reason: the 2026-09-17 re-decision of module M0 under the TRAIN A own null (owner decision 6; the
B0r read, `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B0-REPLICATE-PAIRED-ANALYSIS-V1/README.md`)
returned **HARMFUL** -- the intent clause fails on both passes and the SLU clause fails once by
0.028 pp -- so the Reviewer/Planner review loop is retained and every later cell of the program
builds on the anchor, not on the review-off base. That is exactly the re-base this package's own
section 2 step 7 and its preregistration section 2 instructed.

The six exposure rows of this package stay `consumed = no`, each annotated as superseded before
contact; none of its run or attempt ids may ever be reused. The blocking gate of section 0 was
closed independently by engineering item E3b (commit `d8d8844b`, merge `29bca551`) and the package's
supplies were completed by `scripts/flights/repin_cell.py`, so nothing here is left open on
technical grounds -- only on the base it was built against.
