# Cells B7r and B7c launch runbook: the Reviewer output contract and the tool-observation rewrite

Everything the coordinator needs to fly cells **B7r** and **B7c** and their four-row smokes is in
this directory and in the committed configs. Preregistration:
[`../2026-09-17-slurp-b7rc-ncp-anchor-v1-preregistration.md`](../2026-09-17-slurp-b7rc-ncp-anchor-v1-preregistration.md).

The registration agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**,
never started, stopped or queried the resident service, and ran no worker, campaign, smoke or FIT.

## 0. What these cells are

Two **one-factor steps on top of cell B7a** (`configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v1.json`,
the Node Context Policy at level L1 on the sealed dual-store anchor). Design section 15 resolutions 2
and 3; owner decisions 12, 15 and 17 of 2026-09-17.

- **B7r** declares the review-finding PRODUCER response format `saea-review-findings-v1`, so the
  `planner:review-finding` and `solver:review-finding` boundaries can render structured findings
  instead of the FALLBACK-RAW block on the rows whose Reviewer output parses. Because a phase's output
  contract has exactly one authority, `phase_material.reviewer` declares the same id and the phase
  program id moves to `phase-native-candidates-review-revise-findings-v1` (preregistration deviation
  1). The Reviewer keeps its own prose instruction template and its task-contract tool authority.
- **B7c** moves the four `<role>:tool-observation` boundaries from `raw` to `structured` through
  `probes/ncp_slurp_tool_observation_v1.txt`, so a REPLAYED task-contract observation is rendered as a
  reference instead of echoing the 5,424-character contract the request's own system message already
  carries.

**Cell B7a has not flown.** It is the primary comparator for both cells, and **neither cell opens
before B7a seals and is read not HARMFUL** (owner decision 15 of 2026-09-17: ... -> B7a -> B4b
replicate -> B4a -> B4c only if B4a admits -> **B7r -> B7c** -> B7b -> B5). **B7b (level L2) is not
registered here.**

## 1. What is registered

| item | value |
| --- | --- |
| B7r cell | experiment and cell `slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-generation-v1` |
| B7r FIT | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-fit-v1`, 47,520 endpoints, inside the same campaign |
| B7r smoke | experiment and cell `slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1`, run `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-SMOKE-4-V1`, attempt `attempt-slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-generation-v1` |
| B7r smoke FIT | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-fit-v1`, 176 endpoints |
| B7c cell | experiment and cell `slurp-native-ncp-l1-tool-obs-anchor-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-NCP-L1-TOOL-OBS-ANCHOR-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-ncp-l1-tool-obs-anchor-train-fold-a-generation-v1` |
| B7c FIT | `SAEA-SLURP-NATIVE-NCP-L1-TOOL-OBS-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-ncp-l1-tool-obs-anchor-train-fold-a-fit-v1`, 47,520 endpoints, inside the same campaign |
| B7c smoke | experiment and cell `slurp-native-ncp-l1-tool-obs-anchor-smoke-4-v1`, run `SAEA-SLURP-NATIVE-NCP-L1-TOOL-OBS-ANCHOR-SMOKE-4-V1`, attempt `attempt-slurp-native-ncp-l1-tool-obs-anchor-smoke-4-generation-v1` |
| B7c smoke FIT | `SAEA-SLURP-NATIVE-NCP-L1-TOOL-OBS-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-ncp-l1-tool-obs-anchor-smoke-4-fit-v1`, 176 endpoints |
| baselines | `configs/baseline/slurp-native-anchor-ncp-l1-{reviewer-format,tool-obs}-{train-fold-a,smoke-4}-v1.json` |
| phase program (B7r only) | `configs/policy/phase-native-candidates-review-revise-findings-v1.json`, registered in `rails.controllers` and shaped in `tests/unit/test_rails_controllers.py::_EXPECTED_PROGRAM_SHAPES` |
| campaign plans | `configs/campaign/slurp-native-ncp-l1-{reviewer-format,tool-obs}-anchor-train-fold-a-v1.json` |
| composed / protocol (B7r) | `6f4305068a65de7a591fcdc08e7182ebfdafec43ff0efa240afbb23784119cf1` / `ea40fd649a62313d4dcaa038925c15e994a14173010b501f165e7b387d8cd076` |
| composed / protocol (B7r smoke) | `bf8da2447697ce7ed7d89f4e70d47fb24335848a801c3cd36c569e9de37e1276` / `1511e4e529b874c336750b0401902ed698d0696065835d7e100e764a8e59e9f1` |
| composed / protocol (B7c) | `5c0466b89f8675086825cbb7ea255d94f146b91ead4e373a66e5792c30fa817a` / `bfb4ddcf1a0d5c50d25d086a989627dbed810a2c3e8274760103e04fece2084c` |
| composed / protocol (B7c smoke) | `46e3dd74c39b13deda4953bb7e09f04f25efa0dbcf9ae2c489afe1500780ae79` / `bfa9dc7a4cf68b6d83e5df1774e50cdaf765ef94e09c2e6591403d5aaff05292` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | all four cells are `held` with the preparation requirement pinned; the coordinator appends the decision requirement and flips |
| budgets (per cell) | full: 11,880 generation / 47,520 FIT / 33,930 repeated speech seconds / 12.0 GPU-h / 6,480 task-contract calls / 1 official score. Smoke: 44 / 176 / 117 / 1.0 / 24 / 0 |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-ncp-l1-reviewer-format-train-fold-a-v1",
            "slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with each other baseline/experiment pair reproduces that pair; the smokes use split
identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`. The method is verified on
this tree twice: it reproduces cell B7a's registered
`f90dd1b2d370795ff438bc53db593057cef98a3bf4336e3d62f905d7b5ed735d` and the sealed anchor's
`d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

**These hashes describe the fragments exactly as committed at the registration commit `8b6b0c0b`**:
readiness `held`, the preparation requirement pinned, `prepared_phase_supply` pinned. `compose` hashes
the whole merged fragment set, so flipping readiness and adding the decision requirement each change
the composed hash and therefore the protocol hash. **Do not do that by hand — use the re-pin tool of
section 2.**

## 2. The launch step: `core.flight.repin`

`scripts/flights/repin_cell.py` is the reviewed, tested entry point
(`speech_aware_evidence_acquisition.core.flight.repin`). It re-runs the model-free `prepare-supply`
step only when the prepared artifact would actually mismatch, re-pins the new artifact into the
baseline fragment and the experiment's preparation readiness requirement, optionally applies a
decision requirement and flips `readiness.state` to `ready`, recomputes the composed and protocol
hashes, rewrites every dependent hash in dependency order — this README, the preregistration, every
plan file, the protocol document and the exposure-ledger notes of this package's run ids — then runs
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

Re-pin cell B7r and its smoke and flip them ready in one call:

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1 \
    --cell slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1 \
  --experiment slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1 \
    --cell slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b7rc-ncp-anchor-v1 \
  --preregistration docs/readiness/2026-09-17-slurp-b7rc-ncp-anchor-v1-preregistration.md \
  --package-name slurp-b7rc-ncp-anchor-v1 \
  --decision coordination/<the root admission receipt relpath> \
  --decision-id <the admission decision id> \
  --set-ready
```

and cell B7c and its smoke, separately and only when B7c's own turn comes:

```bash
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-tool-obs-anchor-smoke-4-v1 \
    --cell slurp-native-ncp-l1-tool-obs-anchor-smoke-4-v1 \
  --experiment slurp-native-ncp-l1-tool-obs-anchor-train-fold-a-v1 \
    --cell slurp-native-ncp-l1-tool-obs-anchor-train-fold-a-v1 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b7rc-ncp-anchor-v1 \
  --preregistration docs/readiness/2026-09-17-slurp-b7rc-ncp-anchor-v1-preregistration.md \
  --package-name slurp-b7rc-ncp-anchor-v1 \
  --decision coordination/<the root admission receipt relpath> \
  --decision-id <the admission decision id> \
  --set-ready
```

Drop `--set-ready` (and the two `--decision` flags) to re-pin only — for example after merging master,
before deciding to launch. The tool refuses a prepared artifact whose selection changed unless
`--allow-output-change` is given; **it must never be given here**, because part of the one-factor
claim is that the Perception selection does not move. Commit the result before launching: a COMPLETED
manifest reads `study_commit` at finalize and refuses a dirty tree.

Because the two cells share one `--readiness-dir` and one `--package-name`, run the two invocations
**one at a time**, commit between them, and expect the second to rewrite this README's and the
preregistration's hash tables for its own pair only.

## 3. Pre-launch checklist

1. **Cell B7a has sealed and its verdict is written, and it is not HARMFUL.** Neither cell opens
   otherwise. Fill B7a's sealed `scores_sha256` and `run_manifest_sha256` into
   `b7r-analysis-recipe-v1.json` and `b7c-analysis-recipe-v1.json`, which carry `PENDING_B7A_SEAL`.
2. One experiment in flight: the previous cell is sealed and its verdict written before this one
   opens. B7r precedes B7c.
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
8. Section 2's re-pin has run for the cell about to fly and its `check` assertions passed for both its
   cells.

## 4. Step one: the four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open (shown for B7r;
substitute the B7c ids for B7c):

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1 \
  --owner root-slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1.worker-lease.json"
```

Expected: a few minutes of wall clock, about 20 generation contacts against the 44 ceiling, about 80
FIT endpoints against the 176 ceiling, about 53 repeated speech seconds, no scorer.

### 4.1 Shared acceptance (both smokes)

1. at most 11 contacts per row and 44 in total, with the Reviewer and Planner visits present — this is
   cell B7a's loop, not the review-off ablation;
2. the episode receipt carries well-formed `role_visits` and `planner_routes` on every row, and no row
   reports `skipped_by_configuration`;
3. every post-Perception request carries the policy's rendered blocks: the Solver's and Reviewer's
   `PERCEPTION CANDIDATES (n of at most 3, ...)`, the Reviewer's `DRAFT UNDER REVIEW (Solver,
   parsed|UNPARSED)`, the Planner's `DECISION BRIEF` with its `HARNESS CHECKS` block, and the revising
   Solver's `YOUR PREVIOUS ANSWER` / `PLANNER DECISION:` blocks. A Perception request carries none;
4. the compact episode receipt carries `node_context_policy_compilations`, one record per contact,
   each with `schema: "saea-node-context-policy-compilation-v1"` and per-boundary rows with
   `schema: "saea-node-context-policy-v1"`; every `structured` row names its `template_id` and a
   `template_sha256` equal to the committed file's hash, and every `raw` row's `rendered_sha256`
   equals its source's `content_sha256`;
5. one derived state per rewritten source state: each record's `output_state_ids` has exactly the
   length and order of that contact's exposed history, and the run's own agent-state ledger still
   holds the raw model text;
6. one `*.request-fit.json` per realized contact under `$DATA/prepared/<FIT run id>/<fit attempt
   id>/`, every one with `every_request_fits = true` and a margin no smaller than about 8,900 tokens
   (B7r) or 9,100 tokens (B7c);
7. the worker prints a seal and the tree is still clean.

### 4.2 B7r acceptance, in addition

8. **the Reviewer's output parses under `rails.review_findings.parse_review_findings`** on the smoke
   rows: every reporting-turn completion is read through that parser and the result recorded as
   parsed or rejected, **with the rejection rate written into the smoke note**. On cell B7a's base the
   rate was 2,167 of 2,167 REJECTED; anything short of a large drop here is the finding, not a
   formality (design section 15 point 6: the rejection rate is read at B7r's smoke);
9. **the Planner's review block reads `REVIEW OF THE CURRENT DRAFT (Reviewer, parsed)` with a
   `verdict:` and an `issues:` list where the Reviewer's output parses, and `(Reviewer, UNPARSED)`
   with the `UNPARSED REVIEW, VERBATIM:` section where it does not.** Both forms are legal; the
   per-row split is the measurement;
10. **the Reviewer still issues its task-contract tool call.** `decoding_params.response_format`
    applies to every turn of the role, and the Reviewer's first turn is required by its instruction to
    call the task-contract tool (preregistration open decision 2). Count native task-contract calls
    and compare with cell B7a's rate on the same four rows. **If the Reviewer stops calling its tool,
    the cell has moved two things: stop, and re-register rather than reinterpret.**

### 4.3 B7c acceptance, in addition

8. **no replayed tool observation carries the task contract's own text.** On every `tool` message the
   Planner or the revising Solver replays, the 5,424-character contract is absent and the
   `result.task_contract` field holds the reference block `The task contract returned by
   saea-tool-task-contract-v1, verbatim and in full, is the system message of this request. It is
   referenced here instead of repeated.` (161 characters), with `result_sha256` recomputed over it;
9. **each rewritten row carries the reference block and nothing else changes**: its receipt row is
   `level: "structured"`, `parse_status: "parsed"`, `template_id:
   "probes/ncp_slurp_tool_observation_v1.txt"`, and `derived_fields` reporting
   `source_contract_chars: 5424` and `reference_chars: 161`;
10. **the Reviewer's own live chain is untouched**: its tool-observation rows are `level: "raw"` with
    `raw_reason: "live-tool-chain"` and bytes identical to cell B7a's for the same row. On 1,080 rows
    the expectation is 1,102 rewritten and 1,082 raw; on four rows expect roughly four rewritten
    Planner replays and four raw Reviewer chains.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops that cell until the fix is proven on this same four-row roster.

## 5. Step two: the campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1.json" \
  --owner root-slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

(and the `tool-obs` campaign plan for B7c, in its own turn.) The campaign acquires its own
`GenerationLease` against the resident session, fits each realized native request inside generation,
seals the manifest and schedules the single official score at finalize through `core.scoring_batch`.
Do not run `coordinate-fit`: the native gate fits every request itself, and a standalone fit would
double-charge the FIT row.

Expected, from cell B7a's own cost at this geometry: about 5,400 contacts (5.016 per row) against the
11,880 ceiling, about 15,460 repeated speech seconds against the 33,930 ceiling, about 3.4 GPU hours
against the 12.0 ceiling, and roughly 1 hour of wall clock plus about 3 minutes of official scoring.
Neither cell adds a contact. B7c **removes** prompt volume: 6,648,366 characters, about -3.19 % of the
run's wire text. Nothing else may occupy the GPU while a cell flies, and CPU work runs at 8 workers.

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
2. Fill `scores_sha256` and `run_manifest_sha256` into that cell's analysis recipe — **both the
   arm's own and cell B7a's `PENDING_B7A_SEAL` fields** — and run the paired read exactly as the
   recipe pins it: `analysis.null_calibration_cli.rows_for` to read both sealed score registries,
   `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`, 10,000
   draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write the
   recipe's `analysis_root`.
3. Run the projection-v3 reading over a COPY of the arm's sealed outputs with
   `slurp-slu-official-projected-v3-train` and report it beside every official number. Read the
   symmetric-normalised companion **with the TRAIN sibling of `slurp-slu-f1-normalized-v1` if one is
   registered by then** (owner decision 14 of 2026-09-17); otherwise record the clause as not
   evaluable and use projection v3 as the agreement reading (preregistration deviation 2). Never force
   `slurp-slu-f1-normalized-v1` itself onto the TRAIN roster.
4. Compute the mandatory diagnostics of preregistration section 4, above all the flight's own
   `saea-node-context-policy-v1` aggregate per boundary against this package's contact-free
   expectation: for **B7r**, 13,102 of 13,102 boundary rows unchanged in form from B7a's apart from
   the review-finding rows, plus the findings rejection rate and the native task-contract call count;
   for **B7c**, 1,102 rewritten and 1,082 `live-tool-chain` tool-observation rows, -6,033 rendered
   characters each and -6,648,366 over the run, with 0 of 7,624 model-output boundary rows changed. A
   disagreement between the flight's receipts and this expectation is a defect in the cell, not a new
   finding.
5. Apply the decision rule of preregistration section 6 unchanged — primary pooled official SLU micro
   F1 against **cell B7a** with intent non-inferior within 1.0051 pp, the scenario null band, the
   symmetric or projection-v3 sign agreement — and publish the recipe's `verdict_document` with the
   headline table (cell B7a, arm, delta, the released direct anchor as a secondary column), the
   projection-v3 table beside it, the saves/harms/ties table, the full 18-scenario table in both
   weightings, **the net-harmed-rows-per-scenario table with any scenario of five or more flagged**
   (owner decision 17 of 2026-09-17), the node-context receipt table and the cost table.
6. Close that cell's four exposure rows: set `consumed` to `yes` and append the actual calls, actual
   repeated speech seconds, measured GPU hours, the sealed score and manifest SHA-256 values, and the
   verdict.
7. **NEUTRAL enters the plan for B7c only.** Design section 15 resolution 5: a NEUTRAL B7r/B7c enters
   the SLURP default plan only if it lowers cost. B7c does (a measured -6,648,366 characters);
   **B7r does not**. ADMITTED enters on its measured gain either way. HARMFUL never arms a default
   plan, and then the next cell in the queue order does not fly on that base.

## 7. Harness-admission expectations (write them from the verdicts, not from here)

When each verdict is sealed, that module's entry in `docs/receipts/harness-admission.json` must
satisfy the gate `scripts/checks/harness_admission_check.py` with exactly this switch shape. **Both
modules are the same `episode`-class key `native_episode.context_policy`** — cell B7a's admission
entry moves the key from absent to the L1 block, B7r moves its `producers` sub-block and B7c its four
tool-observation boundaries — so each entry's `switch.on` / `switch.off` pair must name the sub-block
that moved, and the OFF arm of each is **cell B7a's block**, not the key's absence.

**B7r**

| field | value |
| --- | --- |
| `module` | `node context policy review-finding producer format (saea-review-findings-v1 on the Reviewer phase; consumer boundaries unchanged)` |
| `carrier` | `slurp` |
| `switch.table` | `episode` |
| `switch.key` | `native_episode.context_policy` — **the switch is the `producers` sub-block**, so record cell B7a's whole block as OFF and B7a's block plus `producers` as ON; the entry's prose must say that the sub-block is what moved, because the key itself is shared with B7a's own entry |
| `switch.on` | the `structured` block exactly as `configs/baseline/slurp-native-anchor-ncp-l1-reviewer-format-train-fold-a-v1.json` declares it, `producers` included |
| `switch.off` | the `structured` block exactly as `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v1.json` declares it (no `producers`) |
| `switch.proof` | `tests/unit/test_node_context_policy_runner.py::test_a_declared_producer_format_must_match_the_producing_phase` |
| `status` | `ADMITTED`, `NEUTRAL` or `HARMFUL` from the verdict |
| `comparator.on_arm` / `off_arms` | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-TRAIN-FOLD-A-V1` / `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1` |
| default plan | an ADMITTED entry enters `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`; a **NEUTRAL entry must be barred from every default plan**, because B7r lowers no cost (design section 15 resolution 5) |

**B7c**

| field | value |
| --- | --- |
| `module` | `node context policy tool-observation rewrite (the four <role>:tool-observation boundaries at structured; replayed task contract rendered by reference)` |
| `carrier` | `slurp` |
| `switch.table` | `episode` |
| `switch.key` | `native_episode.context_policy` — **the switch is the four `<role>:tool-observation` boundaries**; record the prose the same way |
| `switch.on` | the `structured` block exactly as `configs/baseline/slurp-native-anchor-ncp-l1-tool-obs-train-fold-a-v1.json` declares it |
| `switch.off` | the `structured` block exactly as `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v1.json` declares it (tool-observation `raw`) |
| `switch.proof` | `tests/unit/test_node_context_policy.py` and `tests/unit/test_node_context_policy_runner.py` tool-observation cases (the reference rendering, the substring refusal and the `live-tool-chain` raw reason) |
| `status` | `ADMITTED`, `NEUTRAL` or `HARMFUL` from the verdict |
| `comparator.on_arm` / `off_arms` | `SAEA-SLURP-NATIVE-NCP-L1-TOOL-OBS-ANCHOR-TRAIN-FOLD-A-V1` / `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1` |
| default plan | an ADMITTED **or NEUTRAL** entry enters `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`, because B7c lowers cost |

The gate's rule 2 — every ADMITTED or NEUTRAL entry must appear in at least one default plan for its
carrier — is satisfied for B7c by adding the key to that default plan, and for a NEUTRAL B7r by
recording it **barred** from every default plan, the same way the gate already carries four barred
modules. **Those default-plan edits and the admission entries are not part of this registration and
must not be written before the verdicts.**

## 8. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b7rc-ncp-anchor-v1/` (index `INDEX-v1.json`):

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `check-b7r-full-v1.json` | `eb2ad3db9980e6b068d7b17cb4172098fb21e51ad8a1e8681f8febb9d6fb8809` | `core.flight.cli check` passes for cell B7r: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase, runtime hashes equal to the registered ones, `study_commit` `8b6b0c0b` |
| `check-b7r-smoke-v1.json` | `7b6b150528ce07b10c1ede531d5ce42227f6799c63ab5267ce91ab7c1819f2a0` | the same for B7r's four-row smoke |
| `check-b7c-full-v1.json` | `1a3d1735be00d9055837527ecf240b40b1c119914bfd7237221a3b0c01ba7afb` | the same for cell B7c |
| `check-b7c-smoke-v1.json` | `ea6bf383a0ef12cc24ec1458293e9d256015ccc6f6cff143c47a5075a6b347e7` | the same for B7c's four-row smoke |
| `phase-supply-vs-anchor-v1.json` | `46f09a5d9282c200f2b206062238f6f639613c6ca3812ac7d0afeb934cd21887` | all four prepared Perception artifacts carry an `output` block byte-identical to the sealed anchor preparation's (`ba5e1faa…`) on 1080/1080 rows and to the four-row reference (`512583ec…`) on 4/4, and each row's selection equals the anchor's own row |
| `request-channel-proof-v1.json` | `e0b5023a700ed7d6f2801588764c97c028d41dbf0d55f7f1b2768ebf78e25a09` | the contact-by-contact proof over all 5,417 sealed anchor requests against cell B7a's own render: B7r byte-identical on 5,417/5,417 contacts and 13,102/13,102 boundary rows; B7c rewrites 1,102 of 2,184 tool-observation rows at -6,033 characters each (-6,648,366 total), leaves 1,082 `live-tool-chain` raw, and changes 0 of 7,624 model-output boundary rows; 5,417/5,417 control envelopes identical in both |
| `prompt-fit-v1.json` | `e2b341157699a8552a45797144cd530dd46a2d85a247f929eedd1bc1941f5e35` | the per-contact bound against the 24,576-token slot: ALLOW for both cells, worst margin 8,983 tokens (B7r planner) and 9,194 (B7c planner) |
| `containment-v1.json` | `67b78676c847b0c37f9780b20d4cfc09a0a825f7b0fa0b6b62979d46b46014b0` | 0 containment collisions, verbatim and casefolded, for both bound snapshots against the five control turns and all seven node-context templates |
| `composed-hashes-v1.json` | `eeb2f42e20a10197f280343fe40a5232f9266a69815527645c4f78d87ad36cf4` | the composed and protocol hashes, the B7a and anchor method checks, and the per-cell composed-key diff against B7a (`native_episode` differs in `context_policy` only; inside it, `producers` for B7r and `boundaries` for B7c) |
| `plan-hashes-v1.json` | `fc2fa742532ef59cbcc43ae7535fa170c360ebfb0e7bc0b7cc1491139e113dfa` | the SHA-256 of every config fragment, plan, protocol and recipe document in this package, plus the B7r phase-program fragment |
| `ledger-parse-v1.json` | `06e84990fe0ed3b44a280c72e28da81ca8e4a1f72f98537bebc42502c3fd8f00` | `contracts.ledger._parse_ledger_tables` sees the eight rows exactly once, each `consumed = no`, out of 916 rows |

Do not re-run `derived_media_confinement_check.py` from inside the checkout without reverting its
in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would dirty
the tree the manifest reads at finalize.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. The sealed anchor, cell B0,
cell B1, the B4 cells and cell B7a declare the same stages for the same reason. The request-channel
proof above is the contact-free substitute and is stronger per contact.

## 9. Deviations and open decisions the coordinator should know about

1. **B7r's factor is carried by a new phase-program id**,
   `phase-native-candidates-review-revise-findings-v1`, because a phase's output contract has exactly
   one authority. Preregistration deviation 1 and open decision 1. The program is the existing one
   with one field changed; the visible consequence is +9 provenance characters per rendered state id,
   measured in preregistration section 3.3.
2. **The symmetric-normalised clause is conditional** on a registered TRAIN sibling existing at read
   time. Preregistration deviation 2 and section 6.
3. **B7r's request-channel proof is static.** It proves the compiled render does not move given the
   anchor's own upstream bytes; it cannot prove what the Reviewer generates under the constrained
   contract. Preregistration deviation 4.
4. **Open: does the constrained output contract survive the Reviewer's tool-calling turn?**
   `decoding_params.response_format` applies to every turn of the role. This is section 4.2 item 10
   and preregistration open decision 2 — the first thing B7r's smoke must show.
5. **No `wire-check` stage**, for the reason in section 8.
6. **No twin is registered** for either cell; a control flies only on a positive CI95.
7. **Registered hashes are pre-flip.** Section 1; use the re-pin tool of section 2.
8. **B7b (level L2) is not registered here** and is unaffected by this package.
