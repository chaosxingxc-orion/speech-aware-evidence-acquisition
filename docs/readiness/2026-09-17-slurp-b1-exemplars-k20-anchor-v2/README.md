# Cell B1 launch runbook (anchor base): speech-keyed exemplar supply to the Solver

Everything the coordinator needs to fly cell B1, its twin and its four-row smoke is in this directory
and in the committed configs. Preregistration:
[`../2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md`](../2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md).

This package **supersedes** `docs/readiness/2026-09-17-slurp-b1-exemplars-k20-v1/`, which registered
the same cell on the review-off base. The 2026-09-17 re-decision of module M0 under the TRAIN A own
null returned HARMFUL, so the Reviewer/Planner loop is retained and this cell builds on the sealed
dual-store anchor. The v1 package was never flown; its six exposure rows stay `consumed = no` and
carry supersession notes, and none of its run or attempt ids may be reused.

The re-base agent made **zero model, tokenizer, encoder, ASR, scorer and server contacts**, and never
started, stopped or queried the resident service.

## 1. What is registered

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-exemplars-k20-anchor-train-fold-a-v2`, run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2`, attempt `attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-v2` |
| arm FIT | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-FIT-V2` / `attempt-slurp-native-exemplars-k20-anchor-train-fold-a-fit-v2`, 47,520 endpoints, inside the same campaign |
| twin cell | experiment and cell `slurp-native-exemplars-k20-anchor-twin-train-fold-a-v2`, run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2`, attempt `attempt-slurp-native-exemplars-k20-anchor-twin-train-fold-a-generation-v2` |
| twin FIT | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-FIT-V2` / `attempt-slurp-native-exemplars-k20-anchor-twin-train-fold-a-fit-v2`, 47,520 endpoints |
| smoke cell | experiment and cell `slurp-native-exemplars-k20-anchor-smoke-4-v2`, run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-V2`, attempt `attempt-slurp-native-exemplars-k20-anchor-smoke-4-generation-v2` |
| smoke FIT | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-FIT-V2` / `attempt-slurp-native-exemplars-k20-anchor-smoke-4-fit-v2`, 176 endpoints |
| campaign plans | `configs/campaign/slurp-native-exemplars-k20-anchor-train-fold-a-v2.json`, `configs/campaign/slurp-native-exemplars-k20-anchor-twin-train-fold-a-v2.json` |
| composed / protocol (arm) | `c5bbdc2e1273a8de76b602b450f2da8c1c9092b703208739353b0b09e02fb67f` / `b251f59a41a4e7cbcf6aae328c07148c4dda2dd0c557fd9576e2f26b10ab49f6` |
| composed / protocol (twin) | `25daa5afb334a899091c6481a9febb33660743bfe96286c8d89903339b788d5c` / `4abd62bb6da4888095b57c843e59bb045a74bfb6fcce6b73ae3a4435f9207b2c` |
| composed / protocol (smoke) | `cfaca2b20af9e08499769a232615d62f779e4777293b4089714fe28d464b7b00` / `c31ac32fd609a2a17313b8fe9767528ccbeb1138ca24ecbcfa5b85cd811da335` |
| prepared supply (arm) | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2/phase-supply-v1.json`, SHA-256 `dbd6afbd146ad87aec8e8ad5441ee0c4f35681fbadf8fb4a76943d8c44d3bf97` |
| prepared supply (twin) | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2/phase-supply-v2.json`, SHA-256 `8a33d05022dcdc3fbda16d696e595e37efadabf52461181597668cc23fd02fa7` |
| prepared supply (smoke) | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-V2/phase-supply-v1.json`, SHA-256 `76186c55253f3bf535b0496fc783686c83b352c7badbec7a9f01febc4c107aa7` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | all three cells are `held` with the `preparation` requirement pinned; the coordinator adds the `decision` requirement and flips the state with the re-pin tool |

Protocol hashes were computed the way the precedent computes them:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" \
  /home/chao/.venvs/speechrl/bin/python -B -c '
import sys; sys.path.insert(0, "'"$REPO"'/src")
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
c = compose("'"$REPO"'",
            "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "slurp-speech-native-evo-fold-a-1080",
            "slurp-native-anchor-exemplars-k20-train-fold-a-v2",
            "slurp-native-exemplars-k20-anchor-train-fold-a-v2")
print(c.config_hash)
print(protocol_hash(c.config_hash, c.values["arm"],
      "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"))'
```

The same command with the twin fragment pair reproduces the twin pair, and with the two smoke
fragment names plus split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb`
the smoke pair. The method is verified: run it on the anchor's own fragments
(`slurp-native-dual-store-train-fold-a-anchor-recovery-v1` twice) and it returns the sealed anchor's
registered protocol hash `2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c`.

**These hashes describe the fragments exactly as committed: readiness `held`, the `preparation`
requirement pinned, no `decision` requirement.** `compose` hashes the whole merged four-fragment
document, so adding the decision requirement and flipping readiness each change the composed hash and
therefore the protocol hash. That is what the re-pin tool in section 2 is for: it recomputes and
rewrites every dependent hash in this package and in the six exposure-ledger notes, then runs `check`
and asserts the runtime-derived hashes agree.

## 2. Launch step one: the re-pin tool

`scripts/flights/repin_cell.py` is the single launch step. It re-runs the model-free `prepare-supply`
only if the pinned artifact would mismatch, pins the root decision receipt, flips `readiness.state` to
`ready`, recomputes the composed and protocol hashes, rewrites this package and the ledger notes in
dependency order, and runs `core.flight.cli check` for every cell, refusing if the runtime-derived
hashes disagree.

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
  --experiment slurp-native-exemplars-k20-anchor-smoke-4-v2 \
  --experiment slurp-native-exemplars-k20-anchor-train-fold-a-v2 \
  --experiment slurp-native-exemplars-k20-anchor-twin-train-fold-a-v2 \
  --readiness-dir docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2 \
  --preregistration docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md \
  --decision coordination/slurp-b1-exemplars-k20-anchor-v2/<root-decision>.json \
  --decision-id <DECISION-ID> \
  --set-ready
```

Flip the **smoke first** (one `--experiment` for the smoke cell), commit, fly the smoke, and only then
re-pin and flip the two full cells: a COMPLETED manifest reads `study_commit` at finalize and refuses
a dirty tree, so every flip is its own commit. The tool refuses outright if the tree carries tracked
modifications outside the files it rewrites, or if any target exposure row is already `consumed = yes`.

Then, in order:

1. `git -C "$REPO" status --porcelain` is empty and the re-pin is committed;
2. `core.flight.cli check` receipts for the flipped cells are recorded under
   `$DATA/coordination/slurp-b1-exemplars-k20-anchor-v2/` (the tool writes them itself);
3. the smoke lease and worker (section 4);
4. the arm campaign from a detached worktree pinned at the admitted commit (section 5);
5. the twin campaign **only after** the arm's paired read shows a positive CI95 against the base
   (section 6).

## 3. Pre-launch checklist

1. `git -C "$REPO" status --porcelain` is empty. `check` itself refuses a dirty tree, and a COMPLETED
   manifest reads `study_commit` at finalize. **Flights run from a detached worktree pinned at the
   admitted commit**; no receipt from this preparation lives inside the repository.
2. No flight process is running and no `locks/flight.lock` is held in the data root. One experiment in
   flight.
3. The resident session identity matches:
   `jq -r .identity.props_identity "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json"`
   reports `slot_n_ctx 24576` and `total_slots 4`.
4. `export PYTHONDONTWRITEBYTECODE=1` in every shell; bytecode under the frozen scoring package closes
   the D3 gate.
5. `export PYTHONPATH="$REPO/src"` as armour; never `pip install` in a worktree.
6. Do **not** re-run `derived_media_confinement_check.py` from inside the checkout without reverting
   its in-repo receipt afterwards: it rewrites
   `docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/` and would
   dirty the tree the manifest reads at finalize.

## 4. The four-row smoke

Issue the attach-only worker lease in its own root-owned terminal and keep it open:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli \
  --stage worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-exemplars-k20-anchor-smoke-4-v2 \
  --cell slurp-native-exemplars-k20-anchor-smoke-4-v2 \
  --owner root-slurp-native-exemplars-k20-anchor-smoke-4-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --token-output coordination/slurp-native-exemplars-k20-anchor-smoke-4-v2.worker-lease.json
```

Then, from the same checkout, run the standalone worker:

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-exemplars-k20-anchor-smoke-4-v2 \
  --cell slurp-native-exemplars-k20-anchor-smoke-4-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 \
  --lease-token-file "$DATA/coordination/slurp-native-exemplars-k20-anchor-smoke-4-v2.worker-lease.json"
```

Expected: a few minutes of wall clock, about 20 generation contacts (5 per row on the anchor's own
trajectory statistics; 44 is the ceiling), up to 176 FIT endpoints, about 53 repeated speech seconds
at 5 contacts per row, no scorer. Accept only if all five hold:

- the trace carries Perception, Solver, Reviewer and Planner contacts — this base runs the review
  loop, unlike the superseded v1 registration;
- no row exceeds 11 contacts and the FIT row is not overrun;
- the Solver request carries the `train-exemplars::…` typed content blocks, twenty per row, and the
  Solver instruction body is byte-identical to the anchor's;
- one `*.request-fit.json` per realized contact under
  `$DATA/prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-FIT-V2/attempt-slurp-native-exemplars-k20-anchor-smoke-4-fit-v2/`,
  every one with `every_request_fits = true` and every required-token count below 24,576 (the
  registered upper bound is 16,465);
- the worker prints a seal and the tree is still clean.

Structural inspection only: no answer, reference or quality interpretation. Release the lease. A
failure stops cell B1 until the fix is proven on this same four-row roster.

## 5. The arm campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-exemplars-k20-anchor-train-fold-a-v2.json" \
  --owner root-slurp-native-exemplars-k20-anchor-train-fold-a-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

The campaign acquires its own `GenerationLease` against the resident session, fits each realized
native request inside generation, seals the manifest and schedules the single official score at
finalize through `core.scoring_batch`. Do not run `coordinate-fit`: the native gate fits every request
itself, and a standalone fit would double-charge the FIT row.

Expected: about 5,400 contacts near 5.0 per row and about 15,460 repeated speech seconds, against
ceilings of 11,880 and 33,930. The anchor's own measured generation cost at this geometry is the
reference (5,417 contacts, 3.388 GPU hours, 88.7 % mean utilisation); the exemplar block adds prompt
tokens, not contacts, so the arm should land near the anchor's cost plus the prefill of at most 1,083
extra tokens per supplied contact. Budget roughly 3.5 to 4 hours of wall clock for generation plus
about 3 minutes of official scoring. Nothing else may occupy the GPU while it flies, and CPU work runs
at 8 workers.

Watch, in a second terminal:

```bash
tail -f "$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl"
```

Read GPU hours, mean latency, slot occupancy and duty cycle for each lease window from that file; they
are mandatory verdict fields. A `0 %` utilisation reading with the model still resident means a
CPU-only step, not a hang.

## 6. The twin campaign

```bash
$PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
  --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --campaign-plan "$REPO/configs/campaign/slurp-native-exemplars-k20-anchor-twin-train-fold-a-v2.json" \
  --owner root-slurp-native-exemplars-k20-anchor-twin-train-fold-a-v2 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1
```

Owner decision 8 of 2026-09-17: **the twin flies only after the arm's paired read shows a positive
CI95 against the base.** Seal and read the arm first; one cell in flight at a time.

## 7. Post-flight

1. Confirm each manifest is `COMPLETED`, the outputs are the exact ordered 1,080 rows and each official
   score ran exactly once. Record the score artifact SHA-256 and the run manifest SHA-256 for both arms.
2. Fill `scores_sha256` and `run_manifest_sha256` for the two new arms into
   [`analysis-recipe-v1.json`](analysis-recipe-v1.json) and run the paired read exactly as that recipe
   pins it: `analysis.null_calibration_cli.rows_for` to read the sealed score registries,
   `analysis.null_calibration.pooled_f1` for the pooled micro F1 statistics,
   `analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` for the bootstrap,
   whole-speaker clusters from
   `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`, 10,000
   draws, seed 20260915, CI95 and CI90. `analysis.score_compare_cli` is not the runner. Write
   `analysis/SAEA-SLURP-B1-EXEMPLARS-K20-ANCHOR-PAIRED-ANALYSIS-V2/{score-contrasts.json,README.md}`
   with all four contrasts of the recipe.
3. Compute the four mandatory diagnostics: realized candidate-union coverage against A2's 0.9722, the
   Solver escape-to-neighbour-intent rate, the exemplar token volume actually rendered, and the
   revision counts and review-loop dispositions against the anchor's own.
4. Report projection v3 beside every official number (owner decision 7), over a COPY of each arm's
   sealed outputs, with the symmetric-normalised view where one exists.
5. Apply the decision rule from the preregistration section 7 unchanged, on the **unprojected**
   numbers, at the TRAIN A own-null margins (SLU 1.1218, intent 1.0051). Publish
   `docs/results/2026-09-17-slurp-b1-exemplars-k20-anchor-verdict.md` with the headline table (anchor,
   arm, twin, both deltas), the saves/harms/ties table against anchor and twin, the full 18-scenario
   table in both weightings, the diagnostics table and the cost table.
6. Close the six exposure rows: set `consumed` to `yes` for all six run ids and append to each note the
   actual calls, actual repeated speech seconds, measured GPU hours, the sealed score and manifest
   SHA-256 values, and the verdict.
7. On ADMITTED, add the harness-admission entry for M1 under the `stores` switch class
   (`switch.key = knowledge_stores.train-exemplars`, `switch.off = null`, and a `switch.proof` test
   that composes the two committed fragments) and add the store to the default plan. On NEUTRAL it
   enters the plan only if it lowers cost; on HARMFUL it never arms a default plan.

## 8. Pre-contact evidence, outside the repository

All under `$DATA/coordination/slurp-b1-exemplars-k20-anchor-v2/`:

| file | SHA-256 | what it proves |
| --- | --- | --- |
| `prepared-supply-and-hashes-v1.json` | `ea98af7cdbb91fa297a2a4f496e00f808d111572c756f21f22970b6002c1de49` | the three prepared artifacts pinned, their Perception `output` identical to the anchor's on 1,080 / 1,080 (smoke 4 / 4), the composed and protocol hashes, the eleven-contact ceiling, and the anchor method check |
| `request-envelope-comparison-v1.json` | `3fa91d10c6be62b335d81b4ee8f81e9b442efe21cbd9c9e44f786e69a1359263` | Perception / Reviewer / Planner byte-identical to the anchor on 1,080 / 1,080; Solver equal after removing exactly the twenty `train-exemplars` blocks on 1,080 / 1,080; no run id, attempt id or speech-feature identity id in any request byte |
| `request-envelope-digests-v1.json` | `d2022c908bab77f1549119cb8fc01a310d5e9f6e51328b2cb8e5978b28831999` | the per-row per-phase envelope digests for anchor, arm, twin and smoke |
| `prompt-fit-v1.json` | `8b72aa67b9c0ebcf52379442f8e9dc0d62a2d8dfac91faae9af1618bd8632916` | the anchor's per-role-visit sealed maxima over 5,417 fit receipts (widest `planner:1` 15,382; widest Reviewer `reviewer:3` 15,374) and the 16,465-token upper bound, margin 8,111 |
| `exemplar-prompt-fit-v1.json` | `fa2060af0621a920a590825749ec692cf9cbf75d1d41111965717742c79e10c6` | the k = 20 block distribution (max 4,332 chars / 1,083 proxy tokens), provider-verified on 5 rows per k |
| `containment-v1.json` | `48389b8d656545380efdfd9df269f47c391bf910ef4ae735325f8204c714dff8` | 0 collisions between the 9,354 rendered exemplar values and all six composed instruction texts, Reviewer and Planner included |
| `ledger-parse-v1.json` | `f4b162c60b6cd560d4510dee3731186eec3c405f7abb5d6ee30e26a047bc053d` | all six new rows seen exactly once at `consumed = no`; all six superseded v1 rows annotated and still `consumed = no` |
| `plan-hashes-v1.txt` | see the file | the SHA-256 of every document in this directory |
| `check-slurp-native-exemplars-k20-anchor-smoke-4-v2-v1.json` | `4b0ecc8a402d002fd9d9be0215b028b026b6881652883eeabd0d894ef059090e` | runtime `check` at study commit `343e3b59`: config `049ea7c4…`, protocol `74f4a464…`, 4 samples, readiness `held`, `generation_authorized false`, prompt budget ALLOW on all four phases |
| `check-slurp-native-exemplars-k20-anchor-train-fold-a-v2-v1.json` | `295f60380d8dcde3eb23b8c8f073c99c888232a57eae15fde64f2b145834061e` | runtime `check`: config `db1f5e02…`, protocol `63d62d74…`, 1,080 samples, readiness `held`, prompt budget ALLOW on all four phases |
| `check-slurp-native-exemplars-k20-anchor-twin-train-fold-a-v2-v1.json` | `d0a48baeb37fe781e602e4e17049ad23faaf2ca9426e9f2f3336ddd619fed86d` | runtime `check`: config `f9b9d45e…`, protocol `1bcfc79f…`, 1,080 samples, readiness `held`, prompt budget ALLOW on all four phases |

`core.flight.cli wire-check` is unavailable for any native-episode cell, as it was for the anchor, B0
and B0r: `FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the
real shared speech renderer, and `wire_check` installs a text transport double. The request-envelope
comparison stands in its place.

The runtime `check` confirms the registered identities on this commit: each cell's runtime-derived
composed config hash and protocol hash equal the values in section 1, `scientific_readiness` is
`held` and `generation_authorized` is `false`. Its pre-flight prompt budget (the conservative
whole-roster estimate, not the per-request fit) returns ALLOW on all four phases, with the Solver at
21,012 required window tokens and an operational margin of 3,564; the anchor's own Solver estimate at
this geometry is about 19,225, so the exemplar supply costs roughly 1,790 estimate tokens. The exact
per-request authority remains the `native_contact_fit` gate.

## 9. Deviations the coordinator should know about

1. **Budgets are the anchor's, not B0's.** This base runs the full review loop, so the registered
   ceilings are the anchor's own (11,880 generation, 47,520 FIT endpoints, 33,930 repeated speech
   seconds, 12.0 GPU hours, 6,480 task-contract calls) rather than the review-off cell's. They are the
   exact program maximum, not a target: about 5,400 contacts and 3.4 GPU hours is the expected spend.
   The smoke carries the proof4 envelope (44 / 176 / 117 s / 1.0 GPU-h / 24 tool calls).
2. **The supply bound under-counts the later Reviewer and Planner requests.**
   `render_phase_prompt_envelopes` accumulates supply in declaration order, so the pre-flight prompt
   budget does not add the exemplar block to the Reviewer/Planner requests that follow a Solver
   contact at dispatch. Quantified in the preregistration section 9: even the anchor's widest request
   plus a full exemplar block is 16,465 tokens against a 24,576-token slot. The `native_contact_fit`
   gate remains the exact per-request authority and would refuse a real overrun.
3. **`phase_tools` kept, and now reachable.** On the review-off base the Reviewer task-contract
   authority was declared but unreachable; on this base the Reviewer node is built, so the 6,480
   task-contract ceiling is a live ceiling and the ledger rows say so.
4. **The twin is not a strict permutation.** 0 fixed points on 1,080 rows, but one source vector serves
   two rows and one serves none — the arithmetic consequence of the provenance's declared
   `cross_group_rows: 1`. Recorded, not smoothed over.
5. **The normalised-scorer clause is not evaluable on TRAIN.** `slurp-slu-f1-normalized-v1` is bound to
   the `devel` split and refuses TRAIN sample ids. The clause is reported as not evaluable rather than
   dropped or replaced.
6. **Separate smoke baseline fragment.** `native_contact_fit` carries the FIT run identity and the
   endpoint ceiling, which must equal `rows * max_contacts * (packets + 3)`. Sharing the arm's fragment
   would have charged smoke contacts to the arm's FIT row.
7. **Baseline names say `anchor`; experiment and run names say `anchor` too.** Both halves of the v2
   package carry the base in the name so the superseded review-off package can never be confused with
   it in a log line.
8. **No `wire-check` stage** on any cell, for the reason in section 8.
9. **Registered hashes are pre-flip.** Section 1. The re-pin tool recomputes them when the decision
   requirement is pinned and readiness is flipped, exactly as B0, B0r and B4 did.
10. **Measured at the smoke (2026-09-17, run SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-V2,
   study commit 0dbd0d1d): the exemplar blocks reach every post-Perception request.** On all four
   rows the Perception request carries 0 blocks and the Solver, both Reviewer and the Planner
   requests each carry the same 20 distinct `train-exemplars::value:<id>` items (40 marker
   occurrences per request: each item names its id twice in the wire form), because the supply
   accumulates through the episode's QueryState at dispatch, exactly as deviation 2 anticipated and
   the static render could not show. The module's channel is therefore "exemplar supply declared on
   the Solver phase and visible to the Solver, Reviewer and Planner"; the Reviewer/Planner requests are
   NOT byte-identical to the anchor's at dispatch, only in the static render. Fit held on every
   contact (20 request-fit receipts, every_request_fits true, minimum margin 10,743 tokens). Every
   row ran perception 1 / solver 1 / reviewer 2 / planner 1 and routed ACCEPT; 20 contacts, 52.98
   repeated speech seconds, 4 task-contract tool calls, 170,939 prompt tokens. The verdict states
   this channel; the twin shares it exactly.

## 11. The arm aborted on the REVISE route; the one allowed recovery is registered

**2026-09-17T09:52:35Z.** The arm `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2` (flight
commit `ecc6ecea`, root decision `slurp-b1-exemplars-k20-anchor-admission-v1`) **ABORTED** on the
first row whose Planner routed `REVISE`. The re-entered Solver re-ran its prepared phase supply, the
decision re-selected the same twenty `train-exemplars` values, and
`rails.controllers.EvidenceAgentController._acquired_ids` refused them: *"phase supply selected
values already visible in this trajectory"* (`NativeEpisodeError` `[100054]`, component
`solver_1_input`). 84 rows were complete; **420 generation calls, 911.865938 repeated speech seconds
and 420 request-fit receipts** are durably spent, preserved read-only, and never scored. The
four-row smoke of section 9 item 10 could not have caught it: all four rows routed `ACCEPT`, and
deviation 2 of this README was about prompt volume, not about re-acquisition.

**The fix** is `rails.controllers.restrict_repeat_visit_supply` (commit `f2595f4c`, merged
`cfbb5f8b`, item E3c) with `tests/unit/test_phase_supply_repeat_visit.py`: a phase this trajectory
has already answered acquires only what its `QueryState` does not already hold, and every FIRST
visit is returned unchanged, request bytes and transition identities included.

**What this means for this package.**

1. The **preregistration is not edited** — its bytes are pinned by the sealed root decision. The
   addendum is
   [`../2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1.md`](../2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1.md),
   which carries the root cause, the spend, the fix and its proofs, the recovery cells and their
   launch commands. Section 11 of the preregistration allows exactly one root-diagnosed recovery
   re-registration per run; that note **is** it.
2. The arm's two exposure rows are closed (`consumed = yes`) with the abort, the root cause and the
   recovery run ids. Four new rows are registered at `consumed = no`:
   `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`, `…-TRAIN-FOLD-A-FIT-RECOVERY-V2`,
   `…-SMOKE-4-RECOVERY-V2` and `…-SMOKE-4-FIT-RECOVERY-V2`.
3. The **recovery package lives in its own directory**,
   `docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1/` (recovery protocol
   document, recovery analysis recipe, four prospective and four `-registered` plans), so **every
   file of this v2 directory keeps the bytes and hashes the sealed decision and the closed ledger
   rows quote**. Launch with `--readiness-dir` pointing at the recovery directory.
4. The sections of this README that describe the *science* — the store, the twin, the metrics, the
   containment proof, the prompt fit, the analysis recipe and the post-flight procedure — are
   unchanged and remain in force. Only the names change: the recovery cells are
   `slurp-native-exemplars-k20-anchor-{train-fold-a,smoke-4}-recovery-v2` on baselines
   `slurp-native-anchor-exemplars-k20-{train-fold-a,smoke-4}-recovery-v2`, through campaign plan
   `configs/campaign/slurp-native-exemplars-k20-anchor-train-fold-a-recovery-v2.json`.
5. **The twin cell stays registered exactly as it is** —
   `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2`, unflown, `consumed = no`, readiness
   `held`, its v2 baseline, experiment and campaign fragments untouched. It never contacted the
   model, so nothing about it needs re-registering. **It flies on the fixed code** (`cfbb5f8b` or
   later), and still only after the arm's paired read shows a positive CI95 against the base (owner
   decision 8 of 2026-09-17).
6. The smoke re-proof on the fixed commit (`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-RECOVERY-V2`)
   is a **structural form re-proof only**. It cannot reach the REVISE path — the same four rows
   routed `ACCEPT` at study commit `0dbd0d1d` — and the registration says so in its own
   `what_this_is`, in its `failure_policy` and in its ledger note. The REVISE path is proved
   model-free instead, by the four E3c tests and by
   `coordination/slurp-b1-exemplars-k20-anchor-recovery-v2/revise-path-proof-v1.json` (five episodes
   through the real role graph over the aborted attempt's own twenty value ids and the four real
   prepared smoke selections).

Recovery identities, composed and protocol hashes as committed (readiness `held`, preparation
requirement pinned, no decision requirement yet):

| cell | composed config | protocol | prepared supply SHA-256 |
| --- | --- | --- | --- |
| `…-train-fold-a-recovery-v2` | `(pre-flip; the flipped value is in the recovery package)` | `(pre-flip; the flipped value is in the recovery package)` | `ae9feef8152da8333d3b8bc992037d5776bd3a32c225c9105d879d3398925595` |
| `…-smoke-4-recovery-v2` | `d0876577fb59f17e473b28d0a2ac93c6a983e72a1c2e3b918f84f00c9dcf3900` | `60442419416f8d02aea230dd496ed398e8f316ca5c046e402854bf144aaccede` | `26a4f0167b91d3a1776f56e966fc18d9f0a1d05f8f603e22a1374ff08d003078` |

Both prepared artifacts reproduce the sealed anchor's Perception `output` byte-for-byte:
`ba5e1faa…` on 1,080 / 1,080 and `512583ec…` on 4 / 4. Pre-contact receipts live under
`$DATA/coordination/slurp-b1-exemplars-k20-anchor-recovery-v2/` and are listed with their SHA-256 in
section 9 of the recovery note; the runtime `check` for both cells returns readiness `held`,
`generation_authorized false` and prompt budget ALLOW on all four phases, and the whole-roster
pre-flight render is byte-identical to the aborted attempt's own on every phase
(`request-envelope-comparison-v1.json`, `5ee60cdf5395f7aea63a98e128381391b65eda5e37a9ab275f504d8012d907bb`).

Hash note (coordinator, 2026-09-17): the recovery smoke was flipped ready at study commit d26b2789 by the re-pin tool; its composed/protocol hashes above are the flipped values (d0876577… / 60442419…). The recovery arm's hashes above are pre-flip and move when it is flipped; the recovery package `docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1/` is the authority for the registered values.
