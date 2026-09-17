# Cell B7a launch runbook: the Node Context Policy at level L1 on the sealed anchor

Everything the coordinator needs to fly cell B7a and its four-row smoke is in this directory and in
the committed configs. Preregistration:
[`../2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md`](../2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md).

The registration agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**,
never started, stopped or queried the resident service, and ran no worker, campaign, smoke or FIT.

## 0. What this cell is

Module **M5** of `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 3, cell
**B7a** of `docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 11, on the
**sealed dual-store anchor**. One key moves: `native_episode.context_policy`, from absent (the
anchor) to the `structured` block on the eight model-output boundaries, with the four
tool-observation boundaries declared `raw` and **no** Reviewer producer response format.

Three sibling cells are deliberately NOT in it, and none of them is registered here: **B7r** (give
the Reviewer a response format), **B7c** (rewrite the duplicated task-contract tool observation) and
**B7b** (level L2, one cleaning contact, which flies only if B7a is ADMITTED or NEUTRAL). The L1
derangement twin flies only on a positive CI95.

## 1. What is registered

| item | value |
| --- | --- |
| B7a cell | experiment and cell `slurp-native-ncp-l1-anchor-train-fold-a-v1`, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1`, attempt `attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-v1` |
| B7a FIT | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-ncp-l1-anchor-train-fold-a-fit-v1`, 47,520 endpoints, inside the same campaign |
| B7a smoke | experiment and cell `slurp-native-ncp-l1-anchor-smoke-4-v1`, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V1`, attempt `attempt-slurp-native-ncp-l1-anchor-smoke-4-generation-v1` |
| B7a smoke FIT | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-ncp-l1-anchor-smoke-4-fit-v1`, 176 endpoints |
| baselines | `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v1.json`, `configs/baseline/slurp-native-anchor-ncp-l1-smoke-4-v1.json` |
| campaign plan | `configs/campaign/slurp-native-ncp-l1-anchor-train-fold-a-v1.json` |
| composed / protocol (B7a) | `c46ce941af01d5bf98f9f04a9a8a2bb10b7108a74bd54850f814f42674d7a032` / `f67eb9bc5e9ff23ff3b0cdcd9efa338163feaa732a1e9ff3e94cd7f2619ddded` |
| composed / protocol (B7a smoke) | `0fbb9f0001f8d11fbd8459b0a7dfd55f85833f75e4db38895bf1b028f095a8a2` / `deeeba71ceb627efaaeaf46ace94e4eeefebeed5876eb98ae826ca712a814f1b` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | both cells are `held` with the preparation requirement pinned; the coordinator appends the decision requirement and flips |
| budgets | full: 11,880 generation / 47,520 FIT / 33,930 repeated speech seconds / 12.0 GPU-h / 6,480 task-contract calls / 1 official score. Smoke: 44 / 176 / 117 / 1.0 / 24 / 0 |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-ncp-l1-train-fold-a-v1",
            "slurp-native-ncp-l1-anchor-train-fold-a-v1")
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
plan file, the protocol document and the exposure-ledger notes of this package's run ids -- then
runs `core.flight.cli check` for both cells and asserts the runtime-derived hashes agree. Every step
is model-free.

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
  --experiment slurp-native-ncp-l1-anchor-smoke-4-v1 \
    --cell slurp-native-ncp-l1-anchor-smoke-4-v1 \
  --experiment slurp-native-ncp-l1-anchor-train-fold-a-v1 \
    --cell slurp-native-ncp-l1-anchor-train-fold-a-v1 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1 \
  --preregistration docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md \
  --package-name slurp-b7a-ncp-l1-anchor-v1 \
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

1. One experiment in flight: the previous cell is sealed and its verdict written before this one
   opens.
2. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree. **Fly from a
   clean detached worktree pinned at the admitted commit.** No receipt from this preparation lives
   inside the repository.
3. No flight process is running and no `locks/flight.lock` is held in the data root.
4. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`; the session id is
   `serving-slurp-native-candidate-five-train-a-np4-v1`.
5. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package
   closes the D3 gate.
6. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
7. Section 2's re-pin has run and its `check` assertions passed for both cells.

## 4. Step one: the four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l1-anchor-smoke-4-v1 \
  --owner root-slurp-native-ncp-l1-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-ncp-l1-anchor-smoke-4-v1.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-ncp-l1-anchor-smoke-4-v1 \
  --cell slurp-native-ncp-l1-anchor-smoke-4-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-ncp-l1-anchor-smoke-4-v1.worker-lease.json"
```

Expected: a few minutes of wall clock, about 20 generation contacts against the 44 ceiling, about 80
FIT endpoints against the 176 ceiling, about 53 repeated speech seconds, no scorer. **Accept only if
all of these hold:**

1. at most 11 contacts per row and 44 in total, with the Reviewer and Planner visits present -- this
   is the anchor's loop, not the review-off ablation;
2. the episode receipt carries well-formed `role_visits` and `planner_routes` on every row, and no
   row reports `skipped_by_configuration`;
3. **every post-Perception request carries the policy's rendered blocks**: the Solver's and
   Reviewer's `PERCEPTION CANDIDATES (n of at most 3, ...)`, the Reviewer's `DRAFT UNDER REVIEW
   (Solver, parsed|UNPARSED)`, the Planner's `DECISION BRIEF` and the revising Solver's `YOUR
   PREVIOUS ANSWER` / `PLANNER DECISION:` blocks. A Perception request carries none, and its bytes
   equal the anchor's for that row;
4. **`DECISION BRIEF` and `HARNESS CHECKS` both appear on the Planner**, the checks block listing
   `draft parses as the task answer schema`, `selected intent is one of the Perception candidates`
   and `every entity type is in the legal inventory`;
5. **the review block reads `REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)` on every row**, with
   the Reviewer's own bytes in the `UNPARSED REVIEW, VERBATIM:` section. This is the expected form on
   this base, not a defect: 0 of 2,167 anchor Reviewer outputs parse under the registered findings
   parser, so `FALLBACK-RAW` is the declared and receipted disposition (preregistration section 3.1);
6. the compact episode receipt carries `node_context_policy_compilations`, one record per contact,
   each with `schema: "saea-node-context-policy-compilation-v1"` and per-boundary rows with
   `schema: "saea-node-context-policy-v1"`; every `structured` row names its `template_id` and a
   `template_sha256` equal to the committed file's hash, and **every `raw` row's `rendered_sha256`
   equals its source's `content_sha256`**;
7. **one derived state per rewritten source state**: each record's `output_state_ids` has exactly the
   length and order of that contact's exposed history, every rewritten entry is a
   `node-context:<role>:<class>:<sample>:<sha>` id, and the run's own agent-state ledger still holds
   the raw model text (the policy never rewrites custody);
8. the four tool-observation boundaries emit `level: "raw"` rows only, with `raw_reason`
   `live-tool-chain` on the Reviewer's own chain, and the replayed `tool` message is byte-identical
   to the anchor's;
9. one `*.request-fit.json` per realized contact under `$DATA/prepared/<FIT run id>/<fit attempt
   id>/`, every one with `every_request_fits = true` and a margin no smaller than about 8,900 tokens;
10. the worker prints a seal and the tree is still clean.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops the cell until the fix is proven on this same four-row roster.

## 5. Step two: the campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-ncp-l1-anchor-train-fold-a-v1.json" \
  --owner root-slurp-native-ncp-l1-anchor-train-fold-a-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

The campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation, seals the manifest and schedules the single official score at
finalize through `core.scoring_batch`. Do not run `coordinate-fit`: the native gate fits every
request itself, and a standalone fit would double-charge the FIT row.

Expected, from the anchor's own measured cost at this geometry: about 5,400 contacts (5.016 per row)
against the 11,880 ceiling, about 15,460 repeated speech seconds against the 33,930 ceiling, about
3.4 GPU hours against the 12.0 ceiling, and roughly 1 hour of wall clock plus about 3 minutes of
official scoring. This module adds prompt volume, not contacts: the measured bound is +0.76 % of the
run's wire text and at most +165 proxy tokens on any one contact. Nothing else may occupy the GPU
while it flies, and CPU work runs at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for the lease window from that file;
they are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means a
CPU-only step, not a hang.

## 6. Post-flight

1. Confirm the manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and the official
   score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256.
2. Fill `scores_sha256` and `run_manifest_sha256` into `b7a-analysis-recipe-v1.json` and run the
   paired read exactly as the recipe pins it: `analysis.null_calibration_cli.rows_for` to read both
   sealed score registries, `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
   10,000 draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B7A-NCP-L1-ANCHOR-V1-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}`.
3. Run the projection-v3 reading over a COPY of the arm's sealed outputs with
   `slurp-slu-official-projected-v3-train` and report it beside every official number. The
   symmetric-normalised scorer has no TRAIN sibling and must not be forced onto this roster
   (preregistration section 7, deviation 1).
4. Compute the mandatory diagnostics of preregistration section 4 -- above all the flight's own
   `saea-node-context-policy-v1` aggregate per boundary against this package's contact-free
   expectation (7 malformed drafts at `planner:current-draft`, 14 at `reviewer:current-draft`, 100 %
   malformed at `planner:review-finding` and `solver:review-finding`, 0 tool-observation states
   changed) and the rewritten-state counts per role (solver 1,100 of 1,110; reviewer 4,344 of 6,548;
   planner 2,180 of 5,444; perception 0 of 0). A disagreement between the flight's receipts and this
   expectation is a defect in the cell, not a new finding.
5. Apply the decision rule of preregistration section 7 unchanged -- primary pooled official SLU
   micro F1 with intent non-inferior within 1.0051 pp, the scenario null band, projection v3 agreeing
   in sign -- and publish
   `docs/results/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-verdict.md` with the headline table (anchor,
   arm, delta, the released direct anchor as a secondary column), the projection-v3 table beside it,
   the saves/harms/ties table, the full 18-scenario table in both weightings, the node-context
   receipt table and the cost table.
6. Close the four exposure rows: set `consumed` to `yes` and append the actual calls, actual repeated
   speech seconds, measured GPU hours, the sealed score and manifest SHA-256 values, and the verdict.
7. **Remember that NEUTRAL enters the plan here.** The design fixes that a NEUTRAL L1 still enters
   the SLURP default plan, because it removes a named defect class at no measured cost. ADMITTED
   likewise. HARMFUL never arms a default plan, and then B7b (L2) is not flown.

## 7. Harness-admission expectation (write it from the verdict, not from here)

When the verdict is sealed, the module's entry in `docs/receipts/harness-admission.json` must satisfy
the gate `scripts/checks/harness_admission_check.py` with exactly this switch shape:

| field | value |
| --- | --- |
| `module` | `node context policy L1 (structured on the eight model-output boundaries; tool-observation raw; no producer response format)` |
| `carrier` | `slurp` |
| `switch.table` | `episode` |
| `switch.key` | `native_episode.context_policy` |
| `switch.on` | the `structured` block exactly as `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v1.json` declares it |
| `switch.off` | absent, or the literal `"raw"`, or `raw` at every boundary (`rails.config_tables.is_episode_null_arm`) |
| `switch.proof` | `tests/unit/test_config_table_module_switches.py::test_node_context_policy_is_one_episode_class_key` |
| `status` | `ADMITTED`, `NEUTRAL` or `HARMFUL` from the verdict |
| `comparator.on_arm` / `off_arms` | this cell's run id / the sealed anchor recovery run id |

**A NEUTRAL entry still enters the SLURP default plan** for this module, by the design's own rule
(`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 11), so the gate's rule 2
-- every ADMITTED or NEUTRAL entry must appear in at least one default plan for its carrier -- is
satisfied by adding the key to
`configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`. That default-plan edit
and the admission entry are **not** part of this registration and must not be written before the
verdict.

## 8. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b7a-ncp-l1-anchor-v1/` (index `INDEX-v1.json`):

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `check-b7a-full-v1.json` | `47a06fa9615aa1abe080f939ec29e784fc7cdaf2a2af2bc79cb36ae5bc23a355` | `core.flight.cli check` passes for cell B7a: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase, runtime hashes equal to the registered ones |
| `check-b7a-smoke-v1.json` | `09dcd1a067dd0f233016c149964fa3af23a6f911b2059eb1d88e349f25ce13c1` | the same for the four-row smoke |
| `phase-supply-vs-anchor-v1.json` | `5f98a6125cd92b071dcd8748d8f93c53f4481e663bc812805b27765f42e5cbaf` | both prepared Perception artifacts carry an `output` block byte-identical to the sealed anchor preparation's (`ba5e1faa…`) on 1080/1080 rows and to the four-row reference (`512583ec…`) on 4/4, and each row's selection equals the anchor's own row |
| `request-channel-proof-v1.json` | `52638c76e5f5ee1558575d325702afd479bbb5fc78a499a5463b27e85168af50` | the contact-by-contact proof over all 5,417 sealed anchor requests: Perception byte-identical on 1080/1080; Solver, Reviewer and Planner differ only in the agent-state parts the policy rewrites; 0 tool-observation states changed; 5,417/5,417 control envelopes identical; every raw row's rendered hash equals its source's |
| `prompt-fit-v1.json` | `4e33b5fa00839bee31bc3918611ded2df64b60822495b7cff65e439b82881b14` | the per-contact bound against the 24,576-token slot, built on the anchor's 5,417 sealed fit receipts plus this cell's word delta; every bound fits, worst margin 8,983 tokens (planner) |
| `containment-v1.json` | `75722d6d01c92d669842150ef91a8eddfd84728301d9e64a9600b6051fdd9c1c` | 0 containment collisions, verbatim and casefolded, for both bound snapshots against the five control turns and the six node-context templates |
| `composed-hashes-v1.json` | `d2dcf4a14ca3bf67bb4231a733b5e5194095be115091accdc65bcab2e3b5aca5` | the composed and protocol hashes, the anchor method check, and the cell-versus-anchor composed-key diff (`native_episode` differs in `context_policy` and nothing else) |
| `plan-hashes-v1.json` | `e74261f000da4a758e55dc2c5cf5b0ea2d67e1f2747e3f68da2faff27bb2190b` | the SHA-256 of every config fragment, plan, protocol and recipe document in this package |
| `ledger-parse-v1.json` | `47c4b60087be75cc397435f48423abb63d21467f6ae8b8524c93793195dda72c` | `contracts._parse_ledger_tables` sees the four rows exactly once, each `consumed = no` |

Do not re-run `derived_media_confinement_check.py` from inside the checkout without reverting its
in-repo receipt afterwards: it rewrites
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
dirty the tree the manifest reads at finalize.

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. The sealed anchor, cell
B0, cell B1 and the B4 cells declare the same stages for the same reason. The request-channel proof
above is the contact-free substitute and is stronger per contact.

## 9. Deviations the coordinator should know about

1. **The symmetric-normalised clause of the design's verbatim decision rule is not evaluable on
   TRAIN** and is replaced by the projection-v3 agreement clause, exactly as the B4 anchor package
   did. Preregistration section 7.
2. **The Planner's `HARNESS CHECKS` block is included.** Design open question 2 leaves it to the
   owner; E8a merged it into `probes/ncp_slurp_planner_brief_v1.txt` and this cell flies that
   template. Splitting it out is a template change and a new registration.
3. **The four tool-observation boundaries are declared `raw`, not left undeclared**, so each emits a
   receipt row per contact and the byte-identity claim is checked rather than assumed.
4. **No Reviewer response format**, so the review block is UNPARSED on 100 % of rows by construction.
   Expect it in the smoke; it is not a defect.
5. **No `wire-check` stage**, for the reason in section 8.
6. **No twin is registered.** The L1 derangement control flies only on a positive CI95.
7. **Registered hashes are pre-flip.** Section 1; use the re-pin tool of section 2.

## Smoke record (2026-09-17, coordinator)

SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V1 sealed at study commit ea84dcd5: 24 contacts on four rows (three rows ACCEPT at 5 contacts, one row REVISE then ACCEPT at 9), 5 task-contract tool calls, 24 request-fit receipts all fitting (minimum margin 11,158). Every post-Perception request carried the policy's rendered blocks exactly as designed and one `saea-node-context-policy-v1` receipt row per contact; the revising Solver carried the YOUR PREVIOUS ANSWER and PLANNER DECISION blocks, so the REVISE path of the policy is exercised in flight. The arm was flipped at 00483f61 and flies under ready-first scheduling while B2 v3 waits for the E2d bundle-verifier fix.

## Arm ABORTED 2026-09-17, and its one recovery (coordinator)

`SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1` (flight commit `00483f61`) **ABORTED** at about
21:00 UTC on 2026-09-17, after 3,278 contacts over 618 rows and 8,973.150063 repeated speech
seconds, with `NativeEpisodeError: Planner output names no registered action`. Of its 665 Planner
responses 663 were exactly `ACCEPT` or `REVISE`; one was a six-character control token and one an
80-character response (lengths and sha256 values in the recovery note; the bytes are never
reproduced). `reproduction.ojw.native_episode._planner_action` had no designed behaviour for either
-- the sealed anchor's own 1,085 Planner contacts never produced one -- so it raised and the
exception killed the campaign. **No score ran and no partial quality read was taken or is
permitted.** The run directory is read-only evidence and the flight lock was reconciled by root
(`coordination/slurp-b7a-ncp-l1-anchor-v1/flight-lock-reconciliation-20260917T203304Z.json`). The
smoke above could not have caught it: all six of its Planner responses named a registered action.

The fix is **E8c** (commit `2af5955a`, merged `5bbd54a2`): an illegal Planner action is now a
**retained row disposition** `planner_action_illegal` -- draft delivered, loop stopped, count and
sha256 recorded -- never a flight failure.

The one root-diagnosed recovery the preregistration section 10 allows is registered separately and
**does not modify this package**, whose preregistration bytes stay pinned by the sealed root
decision:

- note [`../2026-09-17-slurp-b7a-ncp-l1-anchor-v1-recovery-v1.md`](../2026-09-17-slurp-b7a-ncp-l1-anchor-v1-recovery-v1.md)
- plans `../2026-09-17-slurp-b7a-ncp-l1-anchor-v1-recovery-v1/`
- runs `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` / `-FIT-RECOVERY-V1` and
  `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1` / `-FIT-RECOVERY-V1`
- configs `configs/baseline/slurp-native-anchor-ncp-l1-{train-fold-a,smoke-4}-recovery-v1.json`,
  the matching experiment fragments and
  `configs/campaign/slurp-native-ncp-l1-anchor-train-fold-a-recovery-v1.json`
- evidence `SPEECHRL_DATA_DIR/coordination/slurp-b7a-ncp-l1-anchor-recovery-v1/`

Nothing in this package's sections 0-9 changes: the question, the moved factor, the metrics, the
resampling, the decision rule, the acceptance list and the harness-admission switch shape are the
recovery's too. Two things are added to post-flight (section 6): the verdict must report the
flight's own `planner_action_illegal` count, sample ids and action lengths as a diagnostic, and
those rows are **retained** in every metric, never dropped from the paired read. A second failure
closes the flight.
