# Cell B1-notool launch runbook: the Reviewer's task-contract tool withdrawn on the B1 base (repair form 0-B)

Preregistration: [`../2026-09-20-slurp-b1-notool-v1-preregistration.md`](../2026-09-20-slurp-b1-notool-v1-preregistration.md).
Owner decisions 55 (repair = 0-B, judged on effect), 56 (option a: the B1 base first), 57, 58.

## 0. What kind of cell this is, in one paragraph

One factor on the B1 base: the flown B1 fragment (module M1, the speech-keyed exemplar supply at k = 20 on the sealed
dual-store anchor; the request bytes of cell B1r) with the `phase_tools` mapping removed. The Reviewer no longer holds
`saea-tool-task-contract-v1`, whose observation is `context.task_contract` -- the contract already rendered verbatim in
every role's system message -- so **no role renders a tools array**, the per-slot prefix is constant by construction, and
the Reviewer's visit is one contact instead of a tool round trip (5 -> 4 contacts per row). EFF-1 showed the other way
of holding the array constant (rendering it to tool-free roles) halves GPU hours but corrupts the Solver's delivery shape;
this cell removes the array instead. It is read against the **sealed B1 arm** at **B1's own-null margins 1.2350 / 1.2212**
(cell B1r): NEUTRAL-or-better admits the withdrawal into the default plan and makes it the base of the knowledge-index
cell (decision 53); HARMFUL with a measured loss registers 0-A as the fallback. The efficiency read is mandatory.

## 1. What is registered here

- `configs/baseline/slurp-native-anchor-exemplars-k20-notool-v1.json` and `-smoke-4-v1.json`: the B1r baselines minus
  `phase_tools`, plus `native_episode.react_exhaustion_policy = "continue-without-answer"` (E22) beside the E13 key.
- `configs/experiment/slurp-native-exemplars-k20-notool-v1.json` (arm) and `-smoke-4-v1.json` (four-row smoke);
  `configs/campaign/slurp-native-exemplars-k20-notool-v1.json` (one cell per plan).
- This package: the generation / FIT plan pairs for the arm and the smoke, `protocol-registered-v1.json`,
  `analysis-recipe-v1.json`, this runbook. Four exposure-ledger rows (`consumed = no`).
- Model-free proof on file (2026-09-20, coordinator): the tool-free fragment loads through
  `load_native_episode_config` with the unchanged ceiling 11; `max_iterations = 1` for the Reviewer is refused by the
  program-ceiling rule, so it stays 3.

## 2. The one configuration change, stated honestly

`phase_tools` absent. Nothing else moves: stores, supply, roster, geometry, session, instruction template and fill,
`tool_schema_rendering` (absent), the review loop, the revision limit. Contacts per row 5 -> 4 because the Reviewer's
first contact is its answer. The native task-contract call ceiling is 0.

## 3. Mint the receipt, then re-pin and flip

The coordinator mints `coordination/slurp-b1-notool-v1/root-admission-v1.json` under the data root (decision id `slurp-b1-notool-admission-v1`, the shape cells B1r and EFF-1 use), then:

```bash
$PY -B scripts/flights/repin_cell.py --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment slurp-native-exemplars-k20-notool-smoke-4-v1 --cell slurp-native-exemplars-k20-notool-smoke-4-v1 \
  --readiness-dir docs/readiness/2026-09-20-slurp-b1-notool-v1 --package-name slurp-b1-notool-v1 \
  --preregistration docs/readiness/2026-09-20-slurp-b1-notool-v1-preregistration.md \
  --decision coordination/slurp-b1-notool-v1/root-admission-v1.json --decision-id slurp-b1-notool-admission-v1 --set-ready
# then the same with --experiment/--cell slurp-native-exemplars-k20-notool-v1
```

Run / commit / run until the tool is satisfied; the last flip commit is the flight commit; the flight worktree is
pinned there. The prepared Perception supply is rebuilt model-free by the re-pin cycle under this cell's run id and its
output asserted equal to B1r's; `--allow-output-change` is never given.

## 4. Pre-launch checklist

Both exposure rows of each run `consumed = no`; no `flight.lock`; no flight or lease process; the resident session
`serving-slurp-native-candidate-five-train-a-np4-v1` idle (4 slots, 0 busy); GPU ramp >= 30 TFLOP/s; the flight
worktree at the flip commit with a clean tracked tree.

## 5. The four-row smoke

Structural acceptance only: 4 of 4 rows delivered; 4 contacts per row (at most 9 with one revision); no request carries
a `tools` array and every `tool_choice` is `none`; 0 tool calls; every request fits; finite_completion and
react_exhaustion counted (0 expected); the first model-facing request of every smoke row byte-identical to cell B1r's
for the same row, the Reviewer request differing by exactly the absent tools array; no abort.

## 6. The arm

The campaign over the committed single-cell plan, as a Windows Scheduled Task from the pinned worktree; one official
complete score at finalize; ceilings run-cumulative (11,880 calls / 47,520 FIT endpoints / 33,930 s / 12.0 GPU-h).
First failure: stop and preserve; one root-diagnosed recovery re-registration at most.

## 7. The read

The recipe is the analysis: paired whole-speaker cluster bootstrap (10,000 draws, seed 20260915) against the sealed B1
arm; NEUTRAL / ADMITTED / HARMFUL exactly as `protocol-registered-v1.json` states; the decision-56 5 % clause; the
efficiency tables from the server.log join; the delivery-shape counts; per-scenario tables and the decision-17 flag.

## 8. Registered hashes (pre-flip)

Quoted in the plan files; recomputed by the re-pin tool at the flip.

## 9. What this package does not authorise

No flight before the receipt is minted and both cells are flipped; no contact of any kind by this registration; no
re-flying or re-scoring of any comparator; no anchor-base or plan-base withdrawal cell (decision 56 decides after the
read); no default-plan edit or harness-admission entry before the sealed verdict; no test-split, Fold B or DEV-1000 read.
