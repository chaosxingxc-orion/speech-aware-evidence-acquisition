# Cell B4b-rep launch runbook: the request-identical replicate of cell B4b

Everything the coordinator needs to fly cell B4b-rep is in this directory and in the committed
configs. **Two steps remain: the re-pin (section 2) and the full campaign (section 4).** No smoke is
registered — section 5 says why, and the preregistration says it in full. Preregistration:
[`../2026-09-17-slurp-b4b-replicate-v2-preregistration.md`](../2026-09-17-slurp-b4b-replicate-v2-preregistration.md).

The registration agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**,
never started, stopped or queried the resident service, touched no run directory, and modified no
other worktree.

## 0. Why this cell exists

Module M4b (the date/time slot-contract revision, slot store v2) is **ADMITTED** on one pass
(`docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md`), and its entry in
`docs/receipts/harness-admission.json` carries `provisional.state = "UNMET"` with the requirement
"replicate on the same roster before the default plan carries the v2 pins". **Owner decision 13 of
2026-09-17** chose the request-identical replicate branch of that requirement and **decision 15** put
it in the GPU order: B1 recovery → B1 twin → B2 v3 → B7a → **B4b replicate** → B4a → B4c. This is that
cell. It does two things at once: it re-applies cell B4b's own three clauses to a second realisation,
and it measures the **own null of the admitted configuration** — the thing cell B4b had to borrow from
the review-off cell B0r.

## 1. What is registered

| item | value |
| --- | --- |
| cell | experiment and cell `slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2`, run `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2`, attempt `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2` |
| FIT | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-REPLICATE-V2` / `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-fit-replicate-v2`, 47,520 endpoints, inside the same campaign |
| smoke | **none**, deliberately — section 5 |
| campaign plan | `configs/campaign/slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2.json` |
| composed config / protocol | `658c568f335b77ed0612348cc4a79b7dbfa1fee5354deafb999af117f290dbe1` / `b8143a5d9511591cf55da817cc3648c6a644cae309a7c4cf51041fcb035243b2` |
| prepared phase supply | `prepared/SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2/phase-supply-v2.json`, SHA-256 `06e52a88b856e4d60b7d4ed9cda99490d61e5acdb26105e77722489abfe29150`, output SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| budgets | 11,880 generation calls, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score — cell B4b's own ceilings, unchanged |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | `held`, carrying the preparation requirement only; **the coordinator mints the decision receipt and flips it with the tool of section 2** |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-slot-store-v2-train-fold-a-replicate-v2",
            "slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

**The method is verified twice on this tree.** Run the same command on cell B4b's own fragments
(`slurp-native-anchor-slot-store-v2-train-fold-a-v2` / `slurp-native-slot-store-v2-anchor-train-fold-a-v2`)
and it returns `8d207b33fa7643b7e5acc4ccbd03354fe9c09df09563544c4879c4bb97ee6a4d` /
`567a87ad234bb4f17c4735f94219a82b05b25a19d81fdf1ee32bb93b6eda346a` — exactly the values the B4b
preregistration registers and the B4b verdict records as flown. Run it on
`slurp-native-dual-store-train-fold-a-anchor-v1` as both baseline and experiment and it returns the
sealed anchor's registered `d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

**These hashes describe the fragments exactly as committed**: readiness `held`, the preparation
requirement pinned, `prepared_phase_supply` pinned. `compose` hashes the whole merged fragment set, so
flipping readiness and adding the decision requirement each change the composed hash and therefore
the protocol hash. **Do not do that by hand — use the re-pin tool of section 2.**

## 2. The launch step: `core.flight.repin`

`scripts/flights/repin_cell.py` is the reviewed, tested entry point
(`speech_aware_evidence_acquisition.core.flight.repin`). It re-runs the model-free `prepare-supply`
step only when the prepared artifact would actually mismatch, re-pins the new artifact into the
baseline fragment and the experiment's preparation readiness requirement, applies the decision
requirement, flips `readiness.state` to `ready`, recomputes the composed and protocol hashes, rewrites
every dependent hash in dependency order — this README, the preregistration, both plan pairs, the
protocol document and the two exposure-ledger notes — then runs `core.flight.cli check` and asserts
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
registration agent has no admission authority. Write it under
`$DATA/coordination/slurp-b4b-replicate-v2/root-admission-v1.json` in the same shape cells B0r and B4b
use, with its own decision id (the suggested id is `slurp-b4b-replicate-admission-v1`). Then re-pin
and flip in one call:

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2 \
    --cell slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b4b-replicate-v2 \
  --preregistration docs/readiness/2026-09-17-slurp-b4b-replicate-v2-preregistration.md \
  --package-name slurp-b4b-replicate-v2 \
  --decision coordination/slurp-b4b-replicate-v2/root-admission-v1.json \
  --decision-id slurp-b4b-replicate-admission-v1 \
  --set-ready
```

Drop `--set-ready` and the two `--decision` flags to re-pin only — for example after merging master,
before deciding to launch. **`--allow-output-change` must never be given here**: the whole
one-factor claim is that the Perception selection does not move, and the tool refusing a changed
selection is that claim's enforcement. If the prepared artifact's `output_sha256` stops being
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`, the merge changed the knowledge
channel, this is no longer a replicate — **stop and report**.

Commit the result before launching: a COMPLETED manifest reads `study_commit` at finalize and refuses
a dirty tree.

## 3. Pre-launch checklist

1. Owner decision 15's order is respected: B7a is sealed before this cell opens, and B4a follows it.
   One experiment in flight.
2. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree. **Fly from a
   clean detached worktree pinned at the admitted commit.** No receipt from this preparation lives
   inside the repository.
3. No flight process is running and no `locks/flight.lock` is held in the data root.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
5. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package closes
   the D3 gate.
6. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
7. Section 2's re-pin has run, its `check` assertions passed, and its result is committed.

A contact-free `check` can be re-run at any time:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli check \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2 \
  --cell slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2
```

It opens the gate, re-checks the exposure row, asserts a clean tree, confirms the attempt is free and
assesses the prompt budget for every phase. `generation_authorized` is always `false`; the readiness
state it reports is whatever the fragment declares.

## 4. The full campaign — the only contact step

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2.json" \
  --owner root-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

The campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation, seals the manifest and schedules the single official score at
finalize through `core.scoring_batch`. **Do not run `coordinate-fit`**: the native gate fits every
request itself, and a standalone fit would double-charge the FIT row.

Expected, from cell B4b's own realized figures: about 5,407 contacts at about 5.01 per row, about
15,433 repeated speech seconds, about 21,628 FIT endpoints, about 3.47 GPU hours and about 12,800 s of
generation wall clock, plus about 390 s of official scoring. Ceilings are 11,880 / 47,520 / 33,930 /
12.0 / 6,480 and are bounds, not targets. Nothing else may occupy the GPU while this flies, and CPU
work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy, utilisation and parked fraction for the lease window
from that file; they are mandatory verdict fields. A `0 %` utilisation reading with the model still
resident means a CPU-only step, not a hang.

## 5. No smoke, deliberately

Cell B4b's package flew a four-row smoke first. This one does not, for a reason that is itself
pre-contact evidence: **the request bytes of this cell are cell B4b's own**, byte-identical on
1,080/1,080 rows and all four declared phases (section 6, and preregistration section 3.1), and B4b's
own smoke `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2` already sealed the structural form of
exactly this episode: composed `c0572352…`, protocol `f13ba493…`, COMPLETED, 20 contacts, 52.98
repeated speech seconds, 4 task-contract calls, 20 fit receipts, all fitting. Re-flying it would spend
contacts to re-learn a recorded fact, and would put four rows of this roster through a second batch
composition before the measurement this cell exists to make.

The structural assertions still hold at the campaign's own seal, and the coordinator checks them
there: about 5,400 contacts within the 11,880 ceiling, the exact ordered 1,080 outputs, the
Reviewer/Planner loop present on the rows that trigger it, and one `*.request-fit.json` per realized
contact carrying `every_request_fits = true`.

## 6. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b4b-replicate-v2/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `prepare-supply-v1.json` | `f70f6e410dc4a7cc771ebbe772d2bc53158b26da90a74aca0a0f21219af7bb0d` | the model-free supply preparation receipt for this cell, `contact_class = model-free` |
| `phase-supply-vs-b4b-and-anchor-v1.json` | `7733fdb895e834e9cb243bf67ec28bea4a2619de5a07c5203cddf0f3b128053c` | the rebuilt Perception supply selects the identical ordered value ids as cell B4b and as the sealed anchor on every one of the 1,080 rows; all three artifacts share the output digest `ba5e1faa…` |
| `composed-hashes-v1.json` | `7fdd6e2017123450a4ef1a5e038ac20fdbc6e7dee90808c4e45dce7d146cb376` | the composed and protocol hashes, the method verification against cell B4b's registered `8d207b33` / `567a87ad` and the sealed anchor's registered `d1c61c09`, and the exact twelve-key composed diff against cell B4b |
| `request-envelope-comparison-v1.json` | `05b54c73efcab569652bb6877a836b619b533dcdfaeb57d643661a8f710bf88d` | on 1,080/1,080 rows and all four phases the rendered request is byte-identical to cell B4b's — including the `[agent control …]` marker — in all three pairings, with a rendered byte delta of exactly 0, and **0 identity-string hits in 12,960 scanned envelopes** |
| `request-envelope-digests-b4b-replicate-v1.json` | `de691c98346c1da8599b175e6d14694d94efd4be8f22aff11bb3ab78b0a9bdac` | the per-row, per-phase envelope digests of this cell |
| `request-envelope-digests-b4b-v1.json` | `914732378048f6153bdd9c86b173a10e41f582bbd19e9d159b7c7296decbcae6` | the same for cell B4b as committed on this master |
| `request-envelope-digests-b4b-asflown-v1.json` | `2b321b1907adaf35b49823d3c979f70de40e2d7d642609032bbcff73e2a49e12` | the same for cell B4b **as flown**, rendered from an export of commit `19ad05b4` with that commit's own code and config bytes, which reproduces B4b's registered composed hash `8d207b33` |
| `plan-hashes-v1.txt` | `87b27c920c3078d136f0f2b1f1db81c4754427b4ccb8c373a0d9ea65115d0cf8` | the SHA-256 of every plan, protocol and recipe document in this directory |
| `ledger-parse-v1.json` | `972b2586b6450abe80fdc39b7e233423cbdf823b1cde21132305875d4540fb30` | `contracts._parse_ledger_tables` sees both rows exactly once, each `consumed = no`, out of 910 rows parsed |
| `check-v1.json` | `f1311eeba91dd498e3a957c4fc24d04b20a6962d4c193f89ea1270b35b994c26` | `core.flight.cli check` passes: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase |

The `check` receipt was produced at commit `5bfe01ab7080a6ebcbd07b6d31aa8dc2c471db9b`, the
registration commit that carries every config, plan and ledger row this cell flies; `check` asserts a
clean study tree and therefore cannot run before that commit exists, and the documentation commit
that follows it changes no config, no plan and no ledger row. The receipt records
`config_hash 7462a00e…`, `protocol_hash bf24d265…`, `study_commit 5bfe01ab…`, `sample_count 1080`,
`scientific_readiness.state "held"`, `generation_authorized false`, and prompt-budget **ALLOW** on all
four phases at exactly the required-window tokens and margins registered above.

Prompt fit against the 24,576-token slot, model-free, over the widest request each phase renders
across the whole roster: perception 19,992 required window tokens (operational margin 4,584), reviewer
19,856 (4,720), planner 19,795 (4,781), solver 20,035 (4,541); decision ALLOW everywhere. These are
cell B4b's own numbers to the token. Measured, from B4b's own 5,407 sealed fit receipts for exactly
these requests: `every_request_fits = true`, minimum margin 8,242 tokens in the `reviewer` phase,
widest realized reviewer request 16,334 tokens.

Do not re-run `derived_media_confinement_check.py` from inside the checkout: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would dirty
the tree the manifest reads at finalize.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. Cell B4b, cell B0r and the
sealed anchor declare the same stages for the same reason. The row-for-row envelope comparison above
is the contact-free substitute and is stronger per row.

## 7. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the official
   score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` for `right_replicate` into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that
   recipe pins it: `analysis.null_calibration_cli.rows_for` to read all four sealed score registries,
   `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B4B-REPLICATE-OWN-NULL-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}`.
3. **Stop if the recomputed `(B4b minus anchor)` contrast does not reproduce the first pass's CI95
   lower bounds `+1.1294` (pooled SLU) and `-0.7117` (intent) to the digit**, or if either comparator
   fails to reproduce its registered official and projection-v3 aggregates. The same sealed bytes
   under the same estimator and seed cannot give two answers.
4. Apply the decision rule from the preregistration section 6 unchanged. Publish
   `docs/results/2026-09-17-slurp-b4b-replication-v2-verdict.md` with the clause table, the own-null
   table (h_SLU_M4b and h_intent_M4b beside B0r's 1.1218 / 1.0051), the saves/harms/ties table, the
   full 18-scenario table in both weightings for both contrasts, the owner-decision-17 net-harmed-rows
   diagnostic, the per-type slot decomposition recomputed on this cell's own outputs, and the cost
   table. The first-pass verdict `docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md` stays on
   record beside it.
5. Close the two exposure rows: set `consumed` to `yes` for
   `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2` and
   `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-REPLICATE-V2`, and append to each note the
   actual calls, actual repeated speech seconds, measured GPU hours, the sealed score and manifest
   SHA-256 values, and the replication verdict.
6. **On REPLICATED**: add a SECOND harness-admission entry recording the replication, leave the first
   entry standing, set the M4b entry's `provisional.state` to `MET`, and let the SLURP default plan
   carry the `slot-contracts-v2` release `f8e42d4f…` and snapshot `d5992bd1…` pins. **Otherwise**: the
   entry stays provisional with its obligation UNMET, the default plan keeps the v1 pins, and the
   owner is told. **No third pass either way.**

## 8. Deviations the coordinator should know about

1. **No smoke.** Section 5. The request bytes are B4b's, proved row for row; B4b's own smoke is the
   structural receipt this cell cites.
2. **A separate baseline fragment exists.** `native_contact_fit` carries the FIT run identity and the
   endpoint ceiling, so sharing cell B4b's fragment would have charged this cell's contacts to B4b's
   FIT row. Only five keys differ from B4b's baseline: the two fit identities, the two speech-feature
   identity strings and the prepared-supply pin (plus the `what_this_is` prose).
3. **The speech-feature identity strings are FRESH here, where cell B0r held its predecessor's.**
   Preregistration section 3.5 reconciles the two: the strings appear in none of the 12,960 rendered
   envelopes scanned, `core.model.transport` validates and drops them, and fit receipts are namespaced
   by the FIT run and attempt id, so neither choice can change a request byte. Minting them is the
   stricter provenance choice and costs nothing the core can see.
4. **The FIT run id reads `…-FIT-REPLICATE-V2`, not `…-REPLICATE-FIT-V2`.** It extends cell B4b's own
   `…-TRAIN-FOLD-A-FIT-V2` with the replicate marker in the position the registration brief named;
   cell B0r used the other order. Nothing depends on the order, but grep for the literal id above.
5. **The prepared Perception supply was rebuilt.** `core.preparation.artifact_inputs` binds the
   composed values and the rails/core module digests; the run ids necessarily moved and
   `core.flight.runtime` moved since B4b flew. The rebuild is model-free and selects identically —
   same output digest as B4b's and the anchor's.
6. **`allowed_execution_stages` still declares `worker`**, mirroring cell B4b's fragment. This cell
   flies through `campaign`; the stage is declared for parity, not to authorize a standalone worker.
7. **The registration commit does not flip readiness and does not merge to master.** Both are the
   coordinator's acts, and section 2 is the tool for the first.
