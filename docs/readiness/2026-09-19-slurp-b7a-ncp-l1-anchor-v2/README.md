# Cell B7a v2 launch runbook: the Node Context Policy at level L1 on the sealed anchor

Status: **REGISTERED BEFORE CONTACT. BOTH CELLS `held`.** Author: the B7a v2 registration agent,
worktree `/home/chao/saea-worktrees/fable-b7a2`, branch `fable/b7a2`, base commit `25a7f325`.
Produced with **zero model, tokenizer, encoder, ASR, scorer and server contacts**.

Read first:
[`../2026-09-19-slurp-b7a-ncp-l1-anchor-v2-preregistration.md`](../2026-09-19-slurp-b7a-ncp-l1-anchor-v2-preregistration.md)
and the closure record [`../../results/2026-09-19-slurp-b7a-v1-closure.md`](../../results/2026-09-19-slurp-b7a-v1-closure.md).
The question, arms, metrics, resampling and decision rule are
[`../2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md`](../2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md)'s,
unchanged.

## 0. What is registered here

| file | what it is |
| --- | --- |
| `protocol-registered-v2.json` | the registered protocol: authority, base, comparators, the moved factor, the harness-robustness key, metrics, decision rules, budgets, the wire-check clause, the resume-recovery clause and the v1 closure |
| `b7a-generation-plan-v2.json` / `-registered-v2.json` | the arm's prospective and registered execution plan |
| `b7a-fit-plan-v2.json` / `-registered-v2.json` | the arm's FIT plan |
| `b7a-smoke-generation-plan-v2.json` / `-registered-v2.json` | the four-row smoke's plan |
| `b7a-smoke-fit-plan-v2.json` / `-registered-v2.json` | the four-row smoke's FIT plan |
| `b7a-analysis-recipe-v2.json` | the paired-analysis recipe the verdict runs |

Config fragments: `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v2.json`,
`configs/baseline/slurp-native-anchor-ncp-l1-smoke-4-v2.json`,
`configs/experiment/slurp-native-ncp-l1-anchor-train-fold-a-v2.json`,
`configs/experiment/slurp-native-ncp-l1-anchor-smoke-4-v2.json`,
`configs/campaign/slurp-native-ncp-l1-anchor-train-fold-a-v2.json`.

## 1. The one configuration change

`native_episode.finite_completion_policy: "deliver-latest-or-abstain"`, added to both v2 baselines.
It is a **harness-robustness key, not a factor**: it renders no request byte and only decides whether
a finite completion aborts the flight or retains the row. Everything a model can see is the v1
recovery's, byte-identical. See the preregistration, sections 2, 3 and 5.

## 2. Launch order

**Smoke first. The arm does not fly until the smoke seals and its request digests match.**

1. Re-pin and flip the **smoke**, using the v1 runbook's section 2 command with the v2 names:

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
  --experiment slurp-native-ncp-l1-anchor-smoke-4-v2 \
    --cell slurp-native-ncp-l1-anchor-smoke-4-v2 \
  --readiness-dir docs/readiness/2026-09-19-slurp-b7a-ncp-l1-anchor-v2 \
  --preregistration docs/readiness/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-preregistration.md \
  --package-name slurp-b7a-ncp-l1-anchor-v2 \
  --decision coordination/slurp-b7a-ncp-l1-anchor-v2/root-admission-v2.json \
  --decision-id slurp-b7a-ncp-l1-anchor-admission-v2 \
  --set-ready
```

   The inherited `prepared_phase_supply` pins name the closed v1 recovery's artifacts and will **not**
   verify against the v2 composed digests. That is expected: `ensure_artifact_pinned` rebuilds each
   artifact under `prepared/<v2 run id>/` and asserts its `output` block equals the inherited one's.
   **Never pass `--allow-output-change`.** Commit the re-pin before launching: a COMPLETED manifest
   reads `study_commit` at finalize and refuses a dirty tree.

2. Pre-launch checklist: the v1 runbook's section 3, unchanged.
3. Fly the smoke through the standalone worker: the v1 runbook's section 4, with
   `--experiment slurp-native-ncp-l1-anchor-smoke-4-v2 --cell slurp-native-ncp-l1-anchor-smoke-4-v2`.
4. Then the same re-pin command with `--experiment slurp-native-ncp-l1-anchor-train-fold-a-v2 --cell
   slurp-native-ncp-l1-anchor-train-fold-a-v2`, and fly the arm through
   `configs/campaign/slurp-native-ncp-l1-anchor-train-fold-a-v2.json` exactly as the v1 runbook's
   section 5 describes.

## 3. Smoke acceptance: the v1 list, plus one

Accept the smoke only if the v1 runbook's section 4 acceptance list (items 1-10) holds **and**:

11. **Every `MODEL_REQUEST` digest equals the sealed v1 recovery smoke's.** Compare each
    `request_sha256` of `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V2` with the corresponding record of
    `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1`, whose trace is under
    `$DATA/runs/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1/`. That trace is **read-only**:
    never write to it, and read no answer, reference or quality field of it. The comparison covers
    the four rows' Perception and Solver requests and every Reviewer and Planner request on a row
    that took the same trajectory. A request whose predecessor response differs is **reported**, not
    silently excused: greedy decoding at `temperature 0` is not bitwise reproducible across batch
    compositions. This is the in-flight proof that `finite_completion_policy` renders no request
    byte; the wire-check stage is unavailable for a native-episode cell.

A four-row roster cannot by itself reach the finite-completion path. That path is proved by the
harness's own committed tests, not by this smoke.

## 4. Post-flight

The v1 runbook's section 6, unchanged, **plus two mandatory diagnostics** in the verdict:

- the flight's own `planner_action_illegal` count, the sample ids that carry it, and their action
  character counts and SHA-256 values (inherited from the v1 recovery note's section 8); and
- the flight's own **finite-completion** count and breakdown -- the `finite_stops` block
  `analysis.native_episode_diagnostics` emits (`count`, `solver_delivery_count`, `by_finish_reason`,
  `by_role`, `by_stage`) plus the sample ids that carry `terminal_disposition.reason ==
  "finite_completion"`, and separately the count of rows that delivered an **abstention** because no
  Solver had completed when the truncation happened.

Rows with either disposition are **RETAINED** in every metric -- they delivered what the policy says
they deliver -- and are **never** dropped from the paired read. A high count is a finding about the
role's output contract or output length on this base; it is reported, not repaired inside this cell.

## 5. Registered hashes (pre-flip)

| item | value |
| --- | --- |
| arm composed / protocol | `73a817ffda56b02501002685db0cd695516425644544fa040464efb17849d494` / `f5a6733f39952cfba2fc418d233c8acf1ff3a3758f16765737de47cc2fbceb31` |
| smoke composed / protocol | `fbe7556e225a4f6ab53f466b09f3b8fcd1efba45404e55a566d0f081b16e8880` / `1f3bdd15ece682b449d0706301a633af09a747f5ef38fa3b93aacc65ae0e52e5` |
| `protocol-registered-v2.json` | `c2239f5857aa12b40d8a36e7ccbb547e41a75ce66a5f0dcad6e99753fcc68cbb` |
| `b7a-generation-plan-registered-v2.json` | `f6ff30b626d7c59f8360b97967d44a287dbc767fdd9f516b80fe2a4e15abf356` |
| `b7a-fit-plan-registered-v2.json` | `2da8e07384dcb137fb76049584a66d4fa1e579c09e47a4845ee632d177d3d625` |
| `b7a-smoke-generation-plan-registered-v2.json` | `bafacfddeb3c6dc9a6ba171692688269ac5cbeb0a86a3d483711a41e5f0e14c2` |
| `b7a-smoke-fit-plan-registered-v2.json` | `5906dad62382a41c10f19902e741e013c5ee6cf8caf3ae7e61146ca822201f44` |
| `b7a-analysis-recipe-v2.json` | `b7803c0a5d95cb8fdf8da76923e505a811c783cc187e17eb6c6aec9fb396aff9` |

These are the values of the five v2 config fragments and of the files in this directory **exactly as
committed**: readiness `held`, the inherited preparation requirement present, no decision
requirement. `scripts/flights/repin_cell.py` rewrites every one of them in dependency order at the
flip; never edit one by hand.

## 6. Root decision receipt

`SPEECHRL_DATA_DIR/coordination/slurp-b7a-ncp-l1-anchor-v2/root-admission-v2.json`, decision id
`slurp-b7a-ncp-l1-anchor-admission-v2`, status `decided`, coordinator Fable5.1, eligible run ids the
four v2 ids. It lives outside the repository so no receipt can dirty the tree the manifest reads at
finalize.

## 7. What this package does not authorise

No readiness flip, no model contact, no `prepare-supply` run, no re-pin, no default-plan edit and no
harness-admission entry. The admission entry for the module "node context policy L1" is written from
the sealed verdict, never from a registration.
