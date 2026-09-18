# Cell B5e launch runbook: the early combination of modules M1 and M4b

Everything the coordinator needs to fly cell B5e and its four-row smoke is in this directory and in
the committed configs. **Four steps remain: mint the decision receipt (section 2), re-pin and flip the
smoke, fly the smoke, then re-pin and flip the arm and run the campaign.** Preregistration:
[`../2026-09-18-slurp-b5e-combination-v1-preregistration.md`](../2026-09-18-slurp-b5e-combination-v1-preregistration.md).

The registration agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**, never
started, stopped or queried the resident service, read and wrote no run directory, and did not touch
the B4b replicate flight that was in progress.

## 0. Why this cell exists

Two modules are admitted on the sealed dual-store anchor base and no cell has ever run them together:
**M1**, speech-keyed annotated TRAIN exemplars supplied to the Solver (cell B1, ADMITTED 2026-09-18
under owner decision 18 branch A), and **M4b**, the date/time slot-contract revision (cell B4b,
ADMITTED 2026-09-17, provisional until replicated). **Owner decision 19 of 2026-09-18** put their
combination in front of the rest of the queue because the arithmetic reaches the bar: v3-projected
**62.67 + 2.06 = 64.73** against a bar of 64.00, with intent already 3.76 points clear. Owner decision
21 put the B4b replicate immediately before it.

That arithmetic is an extrapolation. **This cell measures the combination once and reads it once.**

## 1. What is registered

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-v1` |
| arm FIT | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-fit-v1`, 47,520 endpoints, inside the same campaign |
| smoke cell | experiment and cell `slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1`, run `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-V1`, attempt `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-generation-v1` |
| smoke FIT | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-fit-v1`, 176 endpoints |
| baselines | `configs/baseline/slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-train-fold-a-v1.json`, `configs/baseline/slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-smoke-4-v1.json` |
| experiments | `configs/experiment/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1.json`, `configs/experiment/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1.json` |
| campaign plan | `configs/campaign/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1.json` |
| composed / protocol (arm) | `220a5ac4381090071d3da31798496a4486de486525c591d2d39e63d4eb0beb9e` / `d33b86abf7be171887262144ad3799e7ed79cde5f4dd3a2aaf42a0e71023b638` |
| composed / protocol (smoke) | `9c5d3c4beec5f5c120a2593a5eaa648c5e76d78d138f3f506508b195f7e45c9f` / `c5cbfa6ae93319bb25531087040dfaa741713b2eefb67c7c30be2fe25e99d61b` |
| prepared supply (arm) | `prepared/SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v1.json`, SHA-256 `eabae1321fbe49a7962efb54b130982d192040937d17c7c13c23cf0568223728`, **output** SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| prepared supply (smoke) | `prepared/SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-V1/phase-supply-v1.json`, SHA-256 `6126432fff193fb1b7d63150f40dcff95a1c47ff8ff1ebf6e175e818e138d413`, **output** SHA-256 `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` |
| budgets (arm) | 11,880 generation calls, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score — **cell B1's own ceilings, unchanged** |
| budgets (smoke) | 44 / 176 / 117 s / 1.0 GPU-h / 24 tool calls, zero scoring jobs — **cell B1's recovery smoke's own, unchanged** |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | both cells `held` with the `preparation` requirement pinned and **no decision requirement**; the coordinator mints the receipt and flips with the tool of section 2 |

Protocol hashes were computed the way the precedent computes them, model-free:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-train-fold-a-v1",
            "slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with the two smoke fragment names and split identity
`4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` reproduces the smoke pair.

**The method is verified four ways on this tree**, and all four match sealed registered values
(receipt `composed-hashes-v1.json`):

| fragments | protocol hash | matches |
| --- | --- | --- |
| `slurp-native-dual-store-train-fold-a-anchor-v1` as both baseline and experiment | `d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d` | the sealed anchor's registered value |
| `slurp-native-dual-store-train-fold-a-anchor-recovery-v1` as both | `2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c` | the anchor recovery's registered value |
| cell B1's recovery arm pair | `c66d507d1ae03c081d04a72dda7b5be28c29d7d5d22e4f196c38e5912211da2d` (composed `114b7917…`) | the values its note registers and its verdict records as flown |
| cell B4b's pair | `567a87ad234bb4f17c4735f94219a82b05b25a19d81fdf1ee32bb93b6eda346a` (composed `8d207b33…`) | the values its preregistration registers and its verdict records as flown |

**These hashes describe the fragments exactly as committed**: readiness `held`, the `preparation`
requirement pinned, `prepared_phase_supply` pinned, **no `decision` requirement**. `compose` hashes the
whole merged fragment set, so adding the decision requirement and flipping readiness each change the
composed hash and therefore the protocol hash. **Do not do that by hand — use the re-pin tool of
section 2.**

## 2. The launch step: `core.flight.repin`

`scripts/flights/repin_cell.py` is the reviewed, tested entry point
(`speech_aware_evidence_acquisition.core.flight.repin`). It re-runs the model-free `prepare-supply`
step only when the prepared artifact would actually mismatch, re-pins the new artifact into the
baseline fragment and the experiment's preparation readiness requirement, applies the decision
requirement, flips `readiness.state` to `ready`, recomputes the composed and protocol hashes, rewrites
every dependent hash in dependency order — this README, the preregistration, all four plan pairs, the
protocol document and the four exposure-ledger notes — then runs `core.flight.cli check` and asserts
the runtime-derived hashes agree. Every step is model-free.

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
`$DATA/coordination/slurp-b5e-combination-v1/root-admission-v1.json` in the same shape cells B0r, B4b
and B4b-rep use, with decision id **`slurp-b5e-combination-admission-v1`**.

**Flip the smoke first**, commit, fly it, and only then re-pin and flip the arm: a COMPLETED manifest
reads `study_commit` at finalize and refuses a dirty tree, so every flip is its own commit.

```bash
# step 1: the four-row smoke
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1 \
    --cell slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1 \
  --readiness-dir docs/readiness/2026-09-18-slurp-b5e-combination-v1 \
  --preregistration docs/readiness/2026-09-18-slurp-b5e-combination-v1-preregistration.md \
  --package-name slurp-b5e-combination-v1 \
  --decision coordination/slurp-b5e-combination-v1/root-admission-v1.json \
  --decision-id slurp-b5e-combination-admission-v1 \
  --set-ready
```

```bash
# step 2, after the smoke seals and is inspected: the full cell
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1 \
    --cell slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1 \
  --readiness-dir docs/readiness/2026-09-18-slurp-b5e-combination-v1 \
  --preregistration docs/readiness/2026-09-18-slurp-b5e-combination-v1-preregistration.md \
  --package-name slurp-b5e-combination-v1 \
  --decision coordination/slurp-b5e-combination-v1/root-admission-v1.json \
  --decision-id slurp-b5e-combination-admission-v1 \
  --set-ready
```

Drop `--set-ready` and the two `--decision` flags to re-pin only — for example after merging master,
before deciding to launch. **`--allow-output-change` must never be given here**: the whole two-factor
claim is that the Perception selection does not move, and the tool refusing a changed selection is that
claim's enforcement. If either prepared artifact's `output_sha256` stops being
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` (arm) or
`512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` (smoke), the merge changed the
knowledge channel — **stop and report**.

Commit the result before launching.

## 3. Pre-launch checklist

1. Owner decision 21's order is respected: the **B4b replicate is sealed** before this cell opens. One
   experiment in flight.
2. Decide the conditional comparator: if the B4b replicate's manifest is sealed **and officially
   scored before this cell's first contact**, fill its `scores_sha256` and `run_manifest_sha256` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json)'s `left_m4b_replicate_conditional` arm; if it
   is not, drop that arm and its contrast and say so in the verdict. It never gates.
3. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree. **Fly from a
   clean detached worktree pinned at the admitted commit.** No receipt from this preparation lives
   inside the repository.
4. No flight process is running and no `locks/flight.lock` is held in the data root.
5. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
6. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package closes
   the D3 gate.
7. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
8. Do **not** re-run `derived_media_confinement_check.py` from inside the checkout: it rewrites
   `docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
   dirty the tree the manifest reads at finalize.

A contact-free `check` can be re-run at any time on a clean tree:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1 \
  --cell slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1
```

It opens the gate, re-checks the exposure row, asserts a clean tree, confirms the attempt is free and
assesses the prompt budget for every phase. `generation_authorized` is always `false`; the readiness
state it reports is whatever the fragment declares.

## 4. The four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1 \
  --cell slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1 \
  --owner root-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1 \
  --cell slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-v1.worker-lease.json"
```

Expected: a few minutes of wall clock, about **20 generation contacts** (5 per row; 44 is the ceiling),
up to 176 FIT endpoints, about 53 repeated speech seconds, no scorer. **Accept only if all five hold —
structural acceptance only:**

- the trace carries Perception, Solver, Reviewer and Planner contacts, five per row, and no row exceeds
  11 contacts;
- **the exemplar supply is acquired exactly once per row** (one acquire transition; this is the E3c
  repeat-visit invariant, and the four smoke rows are expected to route ACCEPT and never exercise it);
- the Solver request carries the twenty `train-exemplars::…` typed content blocks, and the **slot store
  v2 cards are present in the Solver evidence**;
- one `*.request-fit.json` per realized contact under
  `$DATA/prepared/SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-FIT-V1/attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-fit-v1/`,
  every one with `every_request_fits = true` and every required-token count below 24,576 (the
  registered static bound is **17,983**);
- the worker prints a seal and the tree is still clean.

No answer, reference or quality interpretation. Release the lease. A failure stops cell B5e until the
fix is proven on this same four-row roster.

## 5. The arm campaign — the only large contact step

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1.json" \
  --owner root-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

The campaign acquires its own `GenerationLease` against the resident session, fits each realized native
request inside generation, seals the manifest and schedules the single official score at finalize
through `core.scoring_batch`. **Do not run `coordinate-fit`**: the native gate fits every request
itself, and a standalone fit would double-charge the FIT row.

Expected, from the four sealed realisations on this geometry: about **5,430 contacts** at about 5.03
per row, about **15,500 repeated speech seconds**, about **21,700 FIT endpoints**, about **3.7 GPU
hours** and about 3.8 hours of generation wall clock, plus about 3 minutes of official scoring.
Ceilings are 11,880 / 47,520 / 33,930 / 12.0 / 6,480 and are bounds, not targets. Nothing else may
occupy the GPU while this flies, and CPU work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy, utilisation and parked fraction for the lease window from
that file; they are mandatory verdict fields. A `0 %` utilisation reading with the model still resident
means a CPU-only step, not a hang.

## 6. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b5e-combination-v1/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `prepared-supply-comparison-v1.json` | `9b6f8771aa4b92a95ac89a25c9eba8a4af5fea48766834de419698419645554d` | the two rebuilt prepared artifacts select the identical ordered value ids as the sealed anchor's own preparation, as cell B1's and as cell B4b's, on 1,080 / 1,080 and 4 / 4 rows; all of them share the output digests `ba5e1faa…` and `512583ec…` |
| `composed-hashes-v1.json` | `aff1f87819727b47836a7cc4a22097e86c9c5909ca9727290f585491af3a4734` | the composed and protocol hashes of both cells; the exact composed-key diffs against the anchor (48 identical / 19 differing), cell B1 (52 / 15) and cell B4b (51 / 16) with `knowledge_stores` the only model-facing difference in each; the store-by-store equality proofs; and the four-way method verification |
| `prompt-fit-v1.json` | `544903713390aad0a58986d528e71a9f100a87d63f25329230c11286198c0c5b` | the per-role-visit maxima over all 21,678 sealed contact-fit receipts on this base, the per-module increments, and the registered static bound 17,983 with margin 6,593 and its 17,834 cross-check |
| `prepare-supply-arm-v1.json` | see `plan-hashes-v1.txt` | the raw model-free `prepare-supply` receipt for the arm, `contact_class = model-free` |
| `prepare-supply-smoke-v1.json` | see `plan-hashes-v1.txt` | the same for the smoke |
| `plan-hashes-v1.txt` | see the file | the SHA-256 of the preregistration, of every document in this directory and of the five config fragments |

**There is no `check` receipt, deliberately.** `FlightRuntime.preflight` asserts a clean study tree and
reserves the attempt in the durable `AttemptStore`; a registration agent whose own files are not yet
committed can neither pass the first nor is entitled to the second. The composed and protocol hashes
were computed directly through `core.config.compose` / `core.config.protocol_hash` — the same two
functions `check` itself uses — and the method was verified four ways against sealed registered values
(section 1). **Section 2's re-pin runs `check` for each cell on the clean registration commit and
refuses if the runtime-derived hashes disagree with the ones it has just written.** That is the gate
this package defers to, not one it skips.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real shared
speech renderer, and `wire_check` installs a text transport double. The sealed anchor, B0, B0r, B1, B4b
and B4b-rep declare the same stages for the same reason. The composed-key diff and the store-by-store
equality proofs stand in its place, and `tests/unit/test_b5e_combination_config.py` pins them as a
committed test.

## 7. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the official
   score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` for `right_b5e` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that recipe
   pins it: `analysis.null_calibration_cli.rows_for` to read every sealed score registry,
   `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`, 10,000
   draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/{score-contrasts.json,per-scenario-tables.json,README.md}`.
3. **Stop if the STOP condition fails**: all four sealed comparators must reproduce their registered
   official and projection-v3 aggregates to the hundredth of a point, and the recomputed
   `(B1 minus anchor)` and `(B4b minus anchor)` contrasts must reproduce `+10.54` / `+0.74` and
   `+1.1294` / `-0.7117` CI95 lower bounds to the digit. The same sealed bytes under the same estimator
   and seed cannot give two answers.
4. Report projection v3 beside every official number (owner decision 7), over a COPY of the sealed
   outputs, with the symmetric `slurp-slu-f1-normalized-v1-train` view beside it.
5. Apply the decision rule from the preregistration section 7 unchanged: **clause 1** (the bar, read on
   the v3 numbers), **clause 2** (the combination, gated on `(B5e minus B1)`, with `(B5e minus B4b)`
   reported and the additivity statement), **clause 3** (the HARMFUL trigger). Publish
   `docs/results/2026-09-18-slurp-b5e-combination-verdict.md` with the headline table (anchor, B1, B4b,
   B5e, direct, and the replicate if it entered), every clause table, the saves/harms/ties table, the
   full 18-scenario table in **both** weightings for every contrast, owner decision 17's net
   harmed-rows-per-scenario diagnostic, the recomputed M1 diagnostics, the recomputed B4b per-type slot
   decomposition, and the cost table.
6. Close the four exposure rows: set `consumed` to `yes` for
   `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-V1`, its FIT row,
   `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1` and its FIT row, and
   append to each note the actual calls, actual repeated speech seconds, measured GPU hours, the sealed
   score and manifest SHA-256 values, and the verdict.
7. **On MEETING THE BAR (clause 1)**: register **B5er**, the request-identical replicate, immediately —
   before any "SLURP base v2.0" lock is claimed. Two passes lock the base (manifest hash, scorer id,
   module list) and B6 confirms on DEV1000 (owner decision 19). **On MISSING it**: the bar is **not**
   lowered (owner decision 20); decision 15's order resumes and B5b reads against the same bar.
   **On HARMFUL (clause 3)**: the v2 candidate falls back to B1 alone, B5er is **not** registered, and
   the owner is told.

## 8. Deviations the coordinator should know about

1. **No `check` receipt in this package.** Section 6 says why, and the re-pin cycle is the gate. This is
   the one place this package departs from the B1 and B4b-rep precedents, which were able to run `check`
   because the coordinator committed their registration first.
2. **A separate smoke baseline fragment exists.** `native_contact_fit` carries the FIT run identity and
   the endpoint ceiling, so sharing the arm's fragment would charge the smoke's contacts to the arm's
   FIT row. Only five keys differ from the arm's baseline: the two fit identities, the two
   speech-feature identity ids and the prepared-supply pin (plus the `what_this_is` prose).
3. **The speech-feature identity strings are fresh for this cell.** They are provenance only:
   `core.model.transport` validates and drops them, the payload's own `key_representation_id` and
   `matcher_policy_id` are program-derived (`phase-native-candidates-review-revise-v1:<phase>`), and fit
   receipts are namespaced by the FIT run and attempt id. The B4b-rep package proved on 12,960 rendered
   envelopes that these strings reach no request byte.
4. **The prepared Perception supply was rebuilt at one worker**, not four or eight: the B4b replicate
   campaign was in flight during this registration and the brief capped CPU use. The rebuild is
   model-free and selects identically — same output digests as the anchor's, cell B1's and cell B4b's.
5. **`allowed_execution_stages` on the arm declares `worker` as well as `campaign`**, mirroring cell
   B1's fragment. This cell flies through `campaign`; the stage is declared for parity, not to authorize
   a standalone worker on the 1,080-row roster.
6. **The registration commit does not flip readiness and does not fly anything.** Both are the
   coordinator's acts, and section 2 is the tool for the first.
7. **The conditional fifth comparator.** The B4b replicate enters the read only if it is sealed and
   scored before this cell's first contact (section 3 item 2). It is reported, never gating, and its
   absence is stated rather than quietly dropped.
