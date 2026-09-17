# Cell B7b launch runbook: the Node Context Policy at level L2 on the cell B7a base

Everything the coordinator needs to fly cell B7b and its four-row smoke is in this directory and in
the committed configs. Preregistration:
[`../2026-09-17-slurp-b7b-ncp-l2-anchor-v1-preregistration.md`](../2026-09-17-slurp-b7b-ncp-l2-anchor-v1-preregistration.md).

The registration agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**,
never started, stopped or queried the resident service, and ran no worker, campaign, smoke or FIT.

## 0. What this cell is, and the gate in front of it

Module **M5** of `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 3, cell
**B7b** of `docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 11, on the
**cell B7a** base. One sub-block moves:
`native_episode.context_policy.boundaries["planner:review-finding"]`, from B7a's `structured` entry
to the `cleaned` entry with its four-field cleaning block. Everything else in the policy document,
and everything else in the composed config, is B7a's.

**B7b does not open until cell B7a has sealed and its verdict is ADMITTED or NEUTRAL.** A HARMFUL
B7a closes this cell unflown -- the design says so in the same paragraph as the rule. Owner decision
15 of 2026-09-17 also puts **B7r** and **B7c** before it, each flying only if its predecessor is not
HARMFUL. Before launch the coordinator must:

1. confirm the B7a verdict is ADMITTED or NEUTRAL;
2. fill B7a's sealed `scores_sha256` and `run_manifest_sha256` into `b7b-analysis-recipe-v1.json`
   (both are `PENDING_B7A_SEAL` today) and into `protocol-registered-v1.json`;
3. decide whether owner decision 14's TRAIN sibling of the symmetric scorer has been registered; if
   it has, the verdict reads it and preregistration deviation 2 is withdrawn.

## 1. What is registered

| item | value |
| --- | --- |
| B7b cell | experiment and cell `slurp-native-ncp-l2-review-clean-anchor-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-NCP-L2-REVIEW-CLEAN-ANCHOR-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-ncp-l2-review-clean-anchor-train-fold-a-generation-v1` |
| B7b FIT | `SAEA-SLURP-NATIVE-NCP-L2-REVIEW-CLEAN-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-ncp-l2-review-clean-anchor-train-fold-a-fit-v1`, 56,160 endpoints, inside the same campaign |
| B7b smoke | experiment and cell `slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1`, run `SAEA-SLURP-NATIVE-NCP-L2-REVIEW-CLEAN-ANCHOR-SMOKE-4-V1`, attempt `attempt-slurp-native-ncp-l2-review-clean-anchor-smoke-4-generation-v1` |
| B7b smoke FIT | `SAEA-SLURP-NATIVE-NCP-L2-REVIEW-CLEAN-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-ncp-l2-review-clean-anchor-smoke-4-fit-v1`, 208 endpoints |
| baselines | `configs/baseline/slurp-native-anchor-ncp-l2-review-clean-train-fold-a-v1.json`, `configs/baseline/slurp-native-anchor-ncp-l2-review-clean-smoke-4-v1.json` |
| campaign plan | `configs/campaign/slurp-native-ncp-l2-review-clean-anchor-train-fold-a-v1.json` |
| policy fragment | `configs/policy/phase-native-candidates-review-revise-clean1-v1.json` (**new**, `max_contacts` 13; see section 9 deviation 1) |
| composed / protocol (B7b) | `3b238087723534381b05854ae6ae519348c1d66c4c3e8f2fd2f109591d94df8d` / `a0193790dfc2267c2e9442940d7cb14916ecad0369eb306eb945d2e62602d096` |
| composed / protocol (B7b smoke) | `5f2d24355bd8f052b84ffd25424e6bb5ad112675cd386b33e222f6efb0dc4a1b` / `b0bbf8acb0c1aa2ae7c05b3c4b385fce91d3bba0e0d8e03730a7f6fbeea48456` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | both cells are `held` with the preparation requirement pinned; the coordinator appends the decision requirement and flips |
| budgets | full: 14,040 generation / 56,160 FIT / 40,099 repeated speech seconds / 12.0 GPU-h / 6,480 task-contract calls / 1 official score. Smoke: 52 / 208 / 138 / 1.0 / 24 / 0 |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-ncp-l2-review-clean-train-fold-a-v1",
            "slurp-native-ncp-l2-review-clean-anchor-train-fold-a-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with the smoke baseline/experiment pair reproduces the smoke pair under split
identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`. The method is verified
on this tree: run it on `slurp-native-dual-store-train-fold-a-anchor-v1` as both baseline and
experiment and it returns the anchor's registered
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

**These hashes describe the fragments exactly as committed at the registration commit**: readiness
`held`, the preparation requirement pinned, `prepared_phase_supply` pinned. `compose` hashes the
whole merged fragment set, so flipping readiness and adding the decision requirement each change the
composed hash and therefore the protocol hash. **Do not do that by hand -- use the re-pin tool of
section 2.**

## 2. The launch step: `core.flight.repin`

`scripts/flights/repin_cell.py` is the reviewed, tested entry point
(`speech_aware_evidence_acquisition.core.flight.repin`). It re-runs the model-free `prepare-supply`
step only when the prepared artifact would actually mismatch, re-pins the new artifact into the
baseline fragment and the experiment's preparation readiness requirement, optionally applies a
decision requirement and flips `readiness.state` to `ready`, recomputes the composed and protocol
hashes, rewrites every dependent hash in dependency order -- this README, the preregistration, every
plan file, the protocol document and the exposure-ledger notes of this package's run ids -- then runs
`core.flight.cli check` for both cells and asserts the runtime-derived hashes agree. Every step is
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
  --experiment slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1 \
    --cell slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1 \
  --experiment slurp-native-ncp-l2-review-clean-anchor-train-fold-a-v1 \
    --cell slurp-native-ncp-l2-review-clean-anchor-train-fold-a-v1 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b7b-ncp-l2-anchor-v1 \
  --preregistration docs/readiness/2026-09-17-slurp-b7b-ncp-l2-anchor-v1-preregistration.md \
  --package-name slurp-b7b-ncp-l2-anchor-v1 \
  --decision coordination/<the root admission receipt relpath> \
  --decision-id <the admission decision id> \
  --set-ready
```

Drop `--set-ready` (and the two `--decision` flags) to re-pin only -- for example after merging
master, before deciding to launch. The tool refuses a prepared artifact whose selection changed
unless `--allow-output-change` is given; **it must never be given here**, because part of the
one-factor claim is that the Perception selection does not move. Commit the result before launching:
a COMPLETED manifest reads `study_commit` at finalize and refuses a dirty tree.

## 3. Pre-launch checklist

1. **Cell B7a has sealed and its verdict is ADMITTED or NEUTRAL**, and B7r and B7c are not HARMFUL
   (owner decision 15). The B7a digests are filled into the analysis recipe.
2. One experiment in flight: the previous cell is sealed and its verdict written before this one
   opens.
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
8. Section 2's re-pin has run and its `check` assertions passed for both cells.

## 4. Step one: the four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1 \
  --owner root-slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-ncp-l2-review-clean-anchor-smoke-4-v1.worker-lease.json"
```

Expected: a few minutes of wall clock, about 24 generation contacts against the 52 ceiling, about 96
FIT endpoints against the 208 ceiling, about 64 repeated speech seconds, no scorer.

**Accept only if all of these hold:**

1. **exactly one cleaning contact precedes each Planner contact**, and no other extra contact appears:
   the realized cleaning-contact count equals the realized Planner-contact count;
2. **the cleaning request carries no evidence block** and **carries the committed instruction template
   bytes** of `configs/probes/ncp_slurp_cleaning_review_v1.txt` -- the request is the system contract
   plus the speech packet plus that template plus the L1 material, and nothing else; its agent-state
   history is empty;
3. **the `saea-node-context-policy-v1` receipt rows at `planner:review-finding` carry a
   `cleaning_contact` block** with contact id, request id, request and response digests,
   `response_format_id: "ncp-review-issues-v1"`, the schema hash, the three committed template hashes,
   and **`validation` set to `accepted`, `rejected` or `skipped` with `rejected_reason` filled on
   every rejection**;
4. **the Planner's review block reads the CLEANED render where validation accepted and cell B7a's own
   L1 render where it rejected** -- `REVIEW OF THE CURRENT DRAFT (Reviewer, restated as structured
   issues by one cleaning contact)` in the first case and
   `REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)` with the verbatim block in the second. Both
   outcomes are admissible on this base; a rejection is not a defect, it is the declared fallback;
5. **no row exceeds 13 contacts** and no row exceeds 52 in total, with the Reviewer and Planner visits
   present -- this is B7a's loop plus the cleaner, not the review-off ablation;
6. **a `*.request-fit.json` exists for every realized contact**, the cleaning contacts included, under
   `$DATA/prepared/<FIT run id>/<fit attempt id>/`, every one with `every_request_fits = true`;
7. the episode receipt carries well-formed `role_visits` and `planner_routes` on every row, and no row
   reports `skipped_by_configuration`;
8. **every boundary other than `planner:review-finding` reproduces cell B7a's own receipt rows** on
   these four rows: the same boundaries, the same levels, the same template ids, and every `raw` row's
   `rendered_sha256` equal to its source's `content_sha256`;
9. **one derived state per rewritten source state**: each record's `output_state_ids` has exactly the
   length and order of that contact's exposed history, and the run's own agent-state ledger still
   holds the raw model text (the policy never rewrites custody);
10. the worker prints a seal and the tree is still clean.

Structural inspection only: no answer, reference or quality interpretation. **Report the smoke's own
validation-rejection rate** -- it is the first reading of the field preregistration section 8 makes
mandatory, and a smoke in which every cleaning output is rejected is a signal worth stopping on even
though it is not a quality result. Release the lease. A failure stops the cell until the fix is proven
on this same four-row roster.

The registration's own contact-free pin of the cleaning request is
`$DATA/coordination/slurp-b7b-ncp-l2-anchor-v1/cleaning-request-render-v1.json`: it carries the same
four sample ids, the committed template hashes, the per-row request digests from the fake-model
harness, 855-863 wire characters and 165 proxy tokens. Compare the smoke's request shape against it --
not its digests, which the harness's own system contract and speech packets make different by
construction.

## 5. Step two: the campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-ncp-l2-review-clean-anchor-train-fold-a-v1.json" \
  --owner root-slurp-native-ncp-l2-review-clean-anchor-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

The campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation -- the cleaning contacts included, because a cleaning contact composes
through the same `MeteredNativeSpeechRequest` path -- seals the manifest and schedules the single
official score at finalize through `core.scoring_batch`. Do not run `coordinate-fit`: the native gate
fits every request itself, and a standalone fit would double-charge the FIT row.

Expected, from the anchor's own measured cost at this geometry plus one cleaning contact per Planner
contact: about **6,500 contacts** (about 6.0 per row, +20.0 %) against the 14,040 ceiling, about
18,500 repeated speech seconds against the 40,099 ceiling, about **4.0-4.3 GPU hours** against the
12.0 ceiling, and roughly 1.3 hours of wall clock plus about 3 minutes of official scoring. Nothing
else may occupy the GPU while it flies, and CPU work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for the lease window from that file; they
are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means a
CPU-only step, not a hang.

## 6. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the official
   score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` for **both** arms into `b7b-analysis-recipe-v1.json`
   -- this cell's own, and cell B7a's, which are `PENDING_B7A_SEAL` until B7a seals -- and run the
   paired read exactly as the recipe pins it: `analysis.null_calibration_cli.rows_for` to read both
   sealed score registries, `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B7B-NCP-L2-ANCHOR-V1-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}`.
3. Run the projection-v3 reading over a COPY of the arm's sealed outputs with
   `slurp-slu-official-projected-v3-train` and report it beside every official number. Read the
   symmetric-normalised scorer **only if** owner decision 14's TRAIN sibling has been registered;
   otherwise the honest statement stays "not evaluable on TRAIN" (preregistration section 6,
   deviation 2).
4. Compute the mandatory diagnostics of preregistration section 4. Above all:
   - **the validation-rejection rate** (preregistration section 8): accepted / rejected / skipped
     counts, the `rejected_reason` histogram, the rate as a percentage of realized cleaning contacts,
     and the same split per scenario. **A verdict without this field is incomplete.**
   - **net harmed rows per scenario, flagging any scenario with five or more** (owner decision 17);
   - realized cleaning contacts against realized Planner contacts, and contacts per row against B7a's
     5.016;
   - the `saea-node-context-policy-v1` aggregate per boundary, with **every boundary except
     `planner:review-finding` reproducing cell B7a's own aggregate**. A disagreement is a defect in
     the cell, not a new finding.
5. Apply the decision rule of preregistration section 6 unchanged -- primary pooled official SLU micro
   F1 against **cell B7a**, intent non-inferior within 1.0051 pp, the scenario null band, projection
   v3 agreeing in sign -- and publish
   `docs/results/2026-09-17-slurp-b7b-ncp-l2-anchor-v1-verdict.md` with the headline table (B7a, B7b,
   delta, the dual-store anchor and the released direct anchor as context columns), the projection-v3
   table beside it, the saves/harms/ties table, the full 18-scenario table in both weightings with the
   net-harmed-rows column, the node-context receipt table including the cleaning block, and the cost
   table.
6. Close the four exposure rows: set `consumed` to `yes` and append the actual calls, actual repeated
   speech seconds, measured GPU hours, the sealed score and manifest SHA-256 values, the
   validation-rejection rate and the verdict.
7. **Remember that NEUTRAL does NOT enter the plan here.** Unlike B7a, a NEUTRAL B7b stays out of the
   SLURP default plan, because it costs +20 % contacts for no measured gain. Only ADMITTED arms it.

## 7. Harness-admission expectation (write it from the verdict, not from here)

When the verdict is sealed, the module's entry in `docs/receipts/harness-admission.json` must satisfy
the gate `scripts/checks/harness_admission_check.py` with exactly this switch shape:

| field | value |
| --- | --- |
| `module` | `node context policy L2 (one context-cleaning contact declared at planner:review-finding; L1 fallback on any validation failure)` |
| `carrier` | `slurp` |
| `switch.table` | `episode` |
| `switch.key` | `native_episode.context_policy` |
| `switch.on` | the B7a policy block with its `planner:review-finding` entry at `level: "cleaned"` and the four-field `cleaning` sub-block, exactly as `configs/baseline/slurp-native-anchor-ncp-l2-review-clean-train-fold-a-v1.json` declares it |
| `switch.off` | the same block with that entry at `level: "structured"`, exactly as `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v1.json` declares it -- that is, **cell B7a is the OFF arm**, not the key's absence |
| `switch.proof` | `tests/unit/test_node_context_policy_l2_runner.py::test_the_l2_policy_document_is_the_cell_b7b_config_surface` (the whole config difference is one boundary entry) and `::test_l2_changes_only_the_declared_boundarys_consumer` |
| `status` | `ADMITTED`, `NEUTRAL` or `HARMFUL` from the verdict |
| `comparator.on_arm` / `off_arms` | this cell's run id / cell B7a's run id |

The switch class is **episode** and the moved key is the same third episode-class key B7a moves; what
distinguishes the two entries is the **cleaning sub-block**, which is the ON arm here. Note the
consequence for the gate's rule 2 -- every ADMITTED or NEUTRAL entry must appear in at least one
default plan for its carrier: **only an ADMITTED B7b may be added to
`configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`.** A NEUTRAL B7b is
barred from every default plan by the design's own rule, so its entry must be recorded the way the
gate records a barred module. That default-plan edit and the admission entry are **not** part of this
registration and must not be written before the verdict.

## 8. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b7b-ncp-l2-anchor-v1/` (index `INDEX-v1.json`):

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `check-b7b-full-v1.json` | `02ddb70366d476c9c22f8ecc4457559cbd067e48fed6f94093f46c485eb1f0d9` | `core.flight.cli check` passes for cell B7b: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase, runtime hashes equal to the registered ones, readiness `held`, `generation_authorized` false |
| `check-b7b-smoke-v1.json` | `aa1cbbd19bc6d4bc41d1a42b21397d62fc63bd54888d4d3656f0ec06dc138943` | the same for the four-row smoke |
| `composed-hashes-v1.json` | `5f9a1522b7fd0528e10fc8a2fc7cc3fb20ed888129cd7182ae68d5999814b036` | the composed and protocol hashes, the anchor method check, the contact-ceiling arithmetic and the versus-B7a composed-key diff (`boundary_entries_that_differ = ["planner:review-finding"]`) |
| `phase-supply-vs-anchor-v1.json` | `0112d6c6764af99d1bf29b09b9baf21f7ee672ac62c986e35002cbf0f1935950` | both prepared Perception artifacts carry an `output` block byte-identical to the sealed anchor preparation's (`ba5e1faa...`) on 1080/1080 rows and to the four-row reference (`512583ec...`) on 4/4, and each row's selection equals the anchor's own row |
| `cleaning-request-render-v1.json` | `36712746173bcd9e4601f490199cd13d94a7858c802a0ea520cf842439bad802` | the cleaning request rendered through the production path over the fake-model harness on the four smoke-row sample ids: one per Planner contact (8/8), the committed template present, no evidence block, no agent-state history, 855-863 wire characters, 165 proxy tokens, the Planner's own request +103 characters, and every other shared request identical once `remaining_model_contacts` is normalised away |
| `request-channel-statement-v1.json` | `0b0fa7e3da7062441a1b188ad52fb91ec746a50b951fdd5e2ec32515c373c684` | the three-part statement and the explicit list of what cannot be shown model-free |
| `prompt-fit-v1.json` | `cdb5bf176d43d9364e589606758bbddec90a7c90758c31802815f7f9769c49c1` | the per-contact bound against the 24,576-token slot: worst margin 8,961 tokens (planner), cleaning contact bounded at 2,733 tokens, margin 21,843 |
| `containment-v1.json` | `48084ebbb8ffd58842d8266af54005a21263d62358b11df3af9bafe38a2e5138` | 0 containment collisions, verbatim and casefolded, for both bound snapshots against the five control turns and the **eight** node-context templates, the two E8b templates included |
| `plan-hashes-v1.json` | `71f24cb819bd227e3854c70fef8a383b266bac03564a02574a4c8ccd2ccc636c` | the SHA-256 of every config fragment, plan, protocol and recipe document in this package |
| `ledger-parse-v1.json` | `6c563430fb76b41d9b5cda373fe815f72edadb4813f05d69694f73178db91ce0` | `contracts._parse_ledger_tables` sees the four rows exactly once, each `consumed = no`; 912 rows parsed |

Do not re-run `derived_media_confinement_check.py` from inside the checkout without reverting its
in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would dirty
the tree the manifest reads at finalize.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. The sealed anchor, cells
B0, B1, the B4 cells and cell B7a declare the same stages for the same reason. The request-channel
statement plus the fake-model render above is the contact-free substitute.

## 9. Deviations the coordinator should know about

1. **A new policy fragment was needed, against the registration brief.** The brief expected the
   ceiling to move through `native_episode_config` alone. It does compute 13 -- and then asserts
   `program.max_contacts == ceiling` and **refuses** the anchor's 11-contact fragment.
   `program.max_contacts` comes from `configs/policy/<policy>.json`, and no committed fragment with
   these four phases declares 13. This registration therefore adds
   `configs/policy/phase-native-candidates-review-revise-clean1-v1.json` and registers its id in
   `rails/controllers.py` and `tests/unit/test_rails_controllers.py`, following the
   `phase-native-candidates-review-revise-samples5-v1` precedent exactly. **This is a code change on
   branch `fable/b7b` and must be merged before the cell composes anywhere else.** Preregistration
   deviation 1.
2. **No contact-by-contact request-channel proof is possible for L2**, because the moved bytes are a
   model output and the comparator has not flown. Section 8 registers a statement plus a fake-model
   render instead, and preregistration deviation 3 records that this is weaker than B7a's evidence.
3. **B7b's requests are not byte-identical to B7a's outside the cleaned boundary**: the ceiling moving
   11 -> 13 shifts `remaining_model_contacts` on every contact of every row. Measured: 24 of 24
   non-Planner shared requests differ only in that number, and 0 differ for any other reason.
4. **The symmetric-normalised clause is not evaluable on TRAIN** unless owner decision 14's TRAIN
   sibling has been registered; until then the projection-v3 agreement clause replaces it.
   Preregistration deviation 2.
5. **The primary comparator has not flown.** Every B7a digest in this package is
   `PENDING_B7A_SEAL`, and the cell is gated on B7a's verdict.
6. **No twin is registered.** A derangement control over the cleaned block would be a second cell and,
   by the twin rule, could fly only on a positive B7b CI95.
7. **Registered hashes are pre-flip.** Section 1; use the re-pin tool of section 2.
