# Cell B1r launch runbook: the request-identical replicate of the exemplar-supply cell

Preregistration:
[`../2026-09-19-slurp-b1-replicate-v1-preregistration.md`](../2026-09-19-slurp-b1-replicate-v1-preregistration.md).
Protocol: [`protocol-registered-v1.json`](protocol-registered-v1.json).
Analysis recipe: [`analysis-recipe-v1.json`](analysis-recipe-v1.json).

Registered before contact by the B1r registration agent, worktree
`/home/chao/saea-worktrees/fable-b1r`, branch `fable/b1r`, base commit `0989edb1`, under **owner
decision 37 of 2026-09-19**. Zero model, tokenizer, encoder, ASR, scorer and server contacts.

## 0. What kind of cell this is, in one paragraph

**Cell B1r changes nothing.** It is the request-identical replicate module M1's harness-admission
entry has been waiting for: the same roster, the same stores, the same role graph, the same prompts,
the same geometry, the same caps and the same session as the sealed cell B1 recovery arm
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`. The only thing that moves between
the two passes is **batch composition under greedy decoding**. It delivers two things: the
**replication verdict** on module M1 — the three clauses cell B1 passed, applied unchanged against
the same sealed anchor — and the **own null of the admitted configuration**, `h_SLU_M1` and
`h_intent_M1`, which owner decision 38 makes the margin regime for every later contrast involving an
exemplar-supplied arm. **Module M1 enters the SLURP default plan only if it replicates.**

## 1. What is registered here

- `configs/baseline/slurp-native-anchor-exemplars-k20-replicate-v1.json` — the arm baseline: cell
  B1's recovery baseline byte for byte in every model-facing key, plus this cell's own
  `native_contact_fit` identity, its own two speech-feature identity ids, its own
  `prepared_phase_supply` pin, its note, and the harness declaration
  `native_episode.finite_completion_policy = "deliver-latest-or-abstain"`.
- `configs/baseline/slurp-native-anchor-exemplars-k20-replicate-smoke-4-v1.json` — the four-row
  smoke baseline, the arm baseline plus bookkeeping at the 176-endpoint FIT ceiling.
- `configs/experiment/slurp-native-exemplars-k20-anchor-replicate-v1.json` — the 1,080-row arm,
  readiness `held`.
- `configs/experiment/slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1.json` — the four-row
  smoke, readiness `held`.
- `configs/campaign/slurp-native-exemplars-k20-anchor-replicate-v1.json` — the single-cell campaign
  plan, naming the arm and only the arm.
- this directory: the protocol, four plan pairs, the analysis recipe and this runbook.
- `tests/unit/test_b1_replicate_config.py` — the config and render-path proof.
- four exposure-ledger rows, `consumed = no`.

## 2. The one configuration change, stated honestly

There is **no factor**. Two things differ from cell B1's committed fragments and neither is a
factor:

1. **bookkeeping** — run, attempt and native-fit identities, the two provenance-only speech-feature
   identity strings, this cell's own prepared-supply pin, and free English;
2. **`native_episode.finite_completion_policy = "deliver-latest-or-abstain"`** — required of every
   live SLURP native cell by `scripts/checks/finite_completion_policy_check.py` (item E13). It
   renders **no request byte**; `docs/receipts/slurp-finite-completion-exposure-v1.json` proves zero
   finite completions on cell B1's own arm, so the comparator side is provably unaffected.

**`native_episode.tool_schema_rendering` is NOT armed.** Request identity with cell B1 requires the
anchor's **per-role** rendering. Cell B1r is a **per-role cell**, unaffected by efficiency cell
EFF-1's outcome; if EFF-1 is NEUTRAL and the constant rendering enters the default plan, this cell's
numbers stay the per-role numbers and the verdict says so.

## 3. Mint the receipt, then re-pin and flip

The coordinator mints `$DATA/coordination/slurp-b1-replicate-v1/root-admission-v1.json` with
decision id **`slurp-b1-replicate-admission-v1`** (already written by this registration in the shape
cells B0r, B4b, B5e, B8a, B8b and EFF-1 use), then re-pins and flips.

**Re-pin BOTH cells in one cycle.** Round 2 of the re-pin tool rewrites the protocol document's
SHA-256 inside *every* plan in this package, so re-pinning one cell alone leaves the other cell's
ledger `Plan SHA256` stale.

```bash
export REPO=<the clean detached worktree carrying this registration>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"
cd "$REPO"

$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1 \
    --cell slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1 \
  --experiment slurp-native-exemplars-k20-anchor-replicate-v1 \
    --cell slurp-native-exemplars-k20-anchor-replicate-v1 \
  --readiness-dir docs/readiness/2026-09-19-slurp-b1-replicate-v1 \
  --preregistration docs/readiness/2026-09-19-slurp-b1-replicate-v1-preregistration.md \
  --package-name slurp-b1-replicate-v1 \
  --decision coordination/slurp-b1-replicate-v1/root-admission-v1.json \
  --decision-id slurp-b1-replicate-admission-v1 \
  --set-ready
```

> **Memory rule, and it applies here.** `repin_cell.py` rewrites every plan in a readiness package.
> This package contains exactly one cell family (smoke + arm), which is the shape that rule asks
> for; there is no sibling cell in it whose closed plan could be rewritten.

**No rebuild is expected, and that is the point.** Both baselines already pin **this cell's own**
prepared artifacts, built in this registration with the model-free `prepare-supply` step under each
cell's own run id:

| cell | prepared artifact | SHA-256 | Perception `output` SHA-256 |
| --- | --- | --- | --- |
| arm | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1/phase-supply-v1.json` | `7f2c82d982df64641b3b0c7b2a06650a6fd2248e8450fa8ee7778f568b0326ef` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| smoke | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-SMOKE-4-V1/phase-supply-v1.json` | `78aa0622394f37287878116beab4b229dd2c5afbb28b08d8210e798e21ed0f83` | `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` |

`core.flight.repin.ensure_artifact_pinned` will find both pins **valid**, rebuild nothing, and add
nothing to `assert_no_residue`'s scan — which is exactly why this package did not inherit cell B1's
pins (item E16). Both Perception `output` blocks were asserted **by hand** in the registration
against the sealed cell B1 preparation's own output — `ba5e1faa…` on 1,080 of 1,080 rows and
`512583ec…` on 4 of 4 — and both matched exactly. That hand assertion replaces
`_compare_artifact_output`, which does not run when there is nothing to rebuild.

> **`--allow-output-change` must never be passed.** If either output SHA-256 stops matching, a merge
> changed the knowledge channel — **stop and report.** This would no longer be a replicate.

**Commit the re-pin before launching**: a COMPLETED manifest reads `study_commit` at finalize and
refuses a dirty tree.

Drop `--set-ready` and the two `--decision` flags to re-pin only, for example after merging master.

## 4. Pre-launch checklist

1. One experiment in flight. The arm does not open before this cell's own four-row smoke seals.
2. `git -C "$REPO" status --porcelain` is empty. **Fly from a clean detached worktree pinned at the
   admitted commit.** No receipt from this preparation lives inside the repository.
3. No other flight process is running and no `locks/flight.lock` is held in the data root.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`. **Attach only, never spawn or stop.** A geometry
   change would end the request identity this cell exists to hold.
5. If a flight is launched as a Windows Scheduled Task (owner decision 24), register the task with
   the **battery and idle conditions disabled and no execution time limit**, and keep `powercfg`
   away from the machine for the duration.
6. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
7. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
8. Do **not** run `scripts/checks/derived_media_confinement_check.py` from inside the checkout: it
   rewrites a receipt directory and would dirty the tree the manifest reads at finalize.
9. Both exposure rows of the cell you are about to launch read `consumed = no`.

A contact-free `check` can be re-run at any time on a clean tree (the re-pin tool runs it for you):

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1 \
  --cell slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1
```

## 5. The four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open, then run the
standalone worker against `--experiment slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1
--cell slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1`. `coordinate-fit` is **not** run; the
FIT gate fits each realized request inside the same worker.

Acceptance list, all structural, none scored:

1. 4 of 4 rows delivered, manifest `COMPLETED`, a clean seal;
2. the eleven-contact anchor role graph resolved, five contacts realized per nominal row;
3. the `train-exemplars` typed content blocks present in the Solver request, store-prefixed
   `train-exemplars::…`, twenty values in and twenty out;
4. one native contact fit receipt per realized contact, `every_request_fits = true`;
5. any retained `finite_completion` row **reported with its sample id and its delivered/abstained
   state**, never treated as an error and never filtered;
6. per-role authority refusals reported (expected zero);
7. no `planner_action_illegal`.

A failed smoke stops cell B1r and the arm does not open.

## 6. The arm

After the smoke seals, launch the campaign over
`configs/campaign/slurp-native-exemplars-k20-anchor-replicate-v1.json` as a Windows Scheduled Task
with the battery and idle conditions disabled and no execution time limit. The campaign acquires its
own `GenerationLease` against the resident session and schedules the one official score at finalize.
`coordinate-fit` must **not** be run.

Expect about **5,425 generation contacts** (5.023 per row), about **15,495 repeated speech seconds**
and about **3.7 GPU hours** — cell B1's own realized cost — against ceilings of 11,880 contacts,
47,520 FIT endpoints, 33,930 speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native
task-contract calls and one complete official score. Ceilings are bounds, never targets.

## 7. The read

Nothing is read until the complete sealed manifest, the exact ordered 1,080 outputs, the native
phase summary and the single successful complete official TRAIN score all exist, **and the STOP
condition passes**: the recomputed `(B1 − anchor)` contrast must reproduce **+10.54** (pooled SLU)
and **+0.74** (intent) as CI95 lower bounds to the two decimals the verdict publishes, and both
comparators must reproduce their registered aggregates.

Then, once, following [`analysis-recipe-v1.json`](analysis-recipe-v1.json):

- **clause contrast** `(B1r − anchor)`: (1a) CI95 lower bound of official pooled SLU-F1 above zero;
  (1b) intent CI95 lower bound above −1.0051; (1c) projection v3 agreeing in sign;
- **own-null contrast** `(B1r − B1)`: the CI95 half-widths `h_SLU_M1` and `h_intent_M1` — **outputs**,
  reported beside B0r's 1.1218 / 1.0051 and B4b-rep's 1.3222 / 1.0682;
- the TRAIN symmetric number and the projection-v3 number beside every official number;
- the 18-scenario table in both weightings, and owner decision 17's net-harmed-rows count with any
  scenario at five or more flagged, **for both contrasts**;
- the mandatory diagnostics of the protocol document, including the **first-request byte identity
  against cell B1 on every row** and the **per-row exemplar-block identity**;
- the full cost block against cell B1's realized figures.

Verdict document: `docs/results/2026-09-19-slurp-b1-replicate-verdict.md`. The verdict word is
**REPLICATED** or **NOT REPLICATED**.

**On REPLICATED**: the M1 provisional obligation is **MET** — a second harness-admission entry
records the replication, the first entry stays, and the SLURP default plan **carries the exemplar
supply**, meaning the whole `knowledge_stores.train-exemplars` block the M1 entry's `switch.on`
records (release `171aa4a8…`, snapshot `4c498dc0…`, `phase_supply.solver` at k = 20 with
`saea-fuse-supplyfilter-v1` m = c = top_l = 20, `saea-rank-wcos-prior-agree-v1` w_cos = 1,
`tau` 0.0, `store_role` `train-exemplars`).

**On NOT REPLICATED**: module M1 stays **out** of the SLURP default plan, its entry stays
provisional with the obligation `UNMET`, and **the owner is told**. No third pass either way.

## 8. Registered hashes (pre-flip)

| cell | composed config | protocol |
| --- | --- | --- |
| arm `slurp-native-exemplars-k20-anchor-replicate-v1` | `130a72f658a3d30d549d06745db4ef7cd1bacafbb9dc378f81be2246fe776150` | `9c17b1723917f8ea67b8b454967d4ef15e8cd7b6fbb45d149e60a537723a1cd7` |
| smoke `slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1` | `188ac3fc02b1b66cda23c2a88ed1b0791284698f59f5611044ab387a38076d68` | `47a32c78a98698789b2ccd9e9377194b30f54f10edf2e40bb5693283a58b2714` |

These are the values of the five fragments **exactly as committed** — readiness `held`, this cell's
own `preparation` requirement pinned, **no** `decision` requirement. Re-pinning, adding the decision
requirement and flipping readiness each change them; the tool recomputes and rewrites them.

**Method verified on this tree against sealed, registered values**: the same `core.config.compose` /
`core.config.protocol_hash` call reproduces cell B1's own registered
`114b791752e160ed0f409fedf12d034b3cc05a8789b4423d1700cc6cb7df000c` /
`c66d507d1ae03c081d04a72dda7b5be28c29d7d5d22e4f196c38e5912211da2d`.

## 9. What this package does not authorise

- any arm flight before this cell's own four-row smoke seals and its acceptance list passes;
- any model, tokenizer, encoder, ASR, scorer, server or paid-API contact from the registration
  itself;
- re-flying or re-scoring either sealed comparator, or opening its run directory for writing;
- `--allow-output-change` on the re-pin tool;
- `coordinate-fit`;
- any default-plan edit or harness-admission entry before the sealed verdict;
- any geometry, roster, prompt, store, k, fuse-policy or rank-weight change — every one of them
  would end the request identity this cell exists to hold;
- arming `native_episode.tool_schema_rendering` on this cell;
- a third pass of this configuration, whichever way clause 1 falls.
