# Iteration 2 of the stage3-deltas store: the CELL-2 DIFF PLAN

Status: **DIFF PLAN ONLY**. Nothing here registers a cell, flips a readiness state, mints a
decision receipt, releases a store, or fills a fragment. It states what version 2 of the
`stage3-deltas` store is, what a second cell over it would cost, and what the coordinator runs
if and when it decides to go ahead. The twin read decides that, not this note.

Source spec: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section
S3-6. Governing decision: owner decision 83
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`) -- "the per-scenario effect
x prefilled-token frontier decides which deltas survive". Read discipline: owner decision 28
(TRAIN A / Fold B / DEV numbers are development numbers, never test claims).

## 1. Why there is an iteration 2

CELL-1 (the locked v2.0 plan plus `stage3-deltas-v1r`, 379 node-targeted deltas) read on TRAIN
Fold A against the sealed PLAN arm:

| quantity | CELL-1 | comparator (PLAN) | delta | CI95 |
| --- | ---: | ---: | ---: | --- |
| official SLU-F1 | 63.1502 | 63.6304 | -0.48 | [-2.18, +1.24] |
| official intent | 81.4815 | 82.2222 | -0.74 | [-2.17, +0.57] |
| prefilled tokens / row | 9,264.9 | 8,353.2 | +911.6 | -- |
| GPU-h / 1,080 rows | 1.8021 | 1.7579 | +2.5 % | -- |

Non-inferiority was not proven and there is no gain, while the arm sits off both the
prefilled-token and the GPU-hour frontier. Decision 83 does not ask for the store to be thrown
away on that reading; it asks for it to be PRUNED by the per-scenario effect, with the frontier
slope as the cost weight.

## 2. What version 2 changes

Exactly one thing: WHICH rows are in the store. No schema, no builder policy, no facet rule, no
route, no cap, no cell shape and no population moves.

| | v1r | v2 |
| --- | ---: | ---: |
| values | 379 | 200 |
| perception (unconditional route) | 119 | 80 |
| solver (candidate-bound, cap 8) | 151 | 76 |
| reviewer (candidate-bound, cap 4) | 95 | 40 |
| planner (candidate-bound, cap 4) | 14 | 4 |
| distinct facet ids | 39 | 26 |
| facet entries | 402 | 219 |
| statement characters, whole store | 31,840 | 16,743 |
| twin token count (parent = twin, by construction) | 5,740 | 3,001 |

Retention (`scripts/build_slurp_stage3_delta_retention.py`, decision 83 as preregistered):
179 values retired, 200 kept. 201 of the 379 were decided by the SCENARIO rule (83 kept, 118
retired) and 178 by the frontier-slope tie rule (117 kept, 61 retired). The per-scenario band is
DERIVED -- the registered own-null table carries no per-scenario half-width -- as
`max(|PLANr - PLAN per-scenario pooled SLU delta|, 1.2485 pp)`, the floor being the registered
pooled own-null SLU-F1 micro CI95 half-width. Seven scenarios are harmed beyond their band
(alarm, general, iot, music, news, play, social), three gain beyond it (datetime,
recommendation, transport) and eight sit inside it. The full derivation, the per-scenario table
and the per-value decisions are in
`docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/iteration-2-retention-v1.md` and
`$SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-STAGE3-DELTAS-V1/retention-v2.json`.

Append-only is amended exactly as decision 83 prescribes: the retired rows are dropped from
version 2's set AND kept as dedup tombstones, because version 2 is curated from the same ADV-1
advantage outputs and would otherwise re-propose every retired statement under an iteration-2
`value_id`. The curation report records `retirement.applied_value_ids` (179) and
`curation.retired_suppressed` (182 candidate blocks). `--schema-version 1` and every released
store are unaffected: re-running the v1r command line on the patched curator reproduces
`authored-stage3-deltas-v1r.json`, `source-stage3-deltas-v1r.json` and
`authored-stage3-deltas-twin-v1r.json` byte for byte.

### Artifacts already built (data root, never in Git)

| artifact | sha256 |
| --- | --- |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/retention-v2.json` | `00b1596a3ca1461f` |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/authored-stage3-deltas-v2.json` | `94c38b35ca4d6b45` |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/source-stage3-deltas-v2.json` | `e1afc2d86bb27510` |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/authored-stage3-deltas-twin-v2.json` | `b5fd2caa1b344fe7` |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/source-stage3-deltas-twin-v2.json` | `08767f3c0b1a8e1a` |

Both release registrations are materialised and committed BESIDE their templates:
`stage3-deltas-v2-release-registration.json` (namespace
`knowledge/slurp/semantic/stage3-deltas-v2`, registration id
`SAEA-SLURP-STAGE3-DELTAS-PREPARATION-V2`, 200 rows) and
`stage3-deltas-twin-v2-release-registration.json` (namespace
`knowledge/slurp/semantic/stage3-deltas-twin-v2`, 200 rows). **The stores are NOT released.**

## 3. What CELL-2 would be

CELL-2 is CELL-1 with `knowledge_stores.stage3-deltas` re-pointed from `stage3-deltas-v1r` to
`stage3-deltas-v2` (and the twin arm from `stage3-deltas-twin-v1r` to `stage3-deltas-twin-v2`).
Everything else is held: the locked v2.0 PLAN fragment, the four routes and their caps
(Perception 4 unconditional, Solver 8, Reviewer 4, Planner 4), `finite_completion_policy`
`deliver-latest-or-abstain`, `react_exhaustion_policy` `continue-without-answer`,
`context_fit_policy` `compact-or-abstain`, the deliver normaliser `saea-deliver-normalise-v3`,
the review loop, the `tfgrpo-semantic-advantage-v1` Stage-3 algorithm label, and the comparator
(the sealed PLAN arm at the plan's own null, h_SLU 1.2485 / h_intent 0.9943).

Population: unchanged TRAIN Fold A, 1,080 rows, `slurp-speech-native-evo-fold-a-1080`, split
identity `61b0f062...`. R01C remains the CONSTRUCTION roster only.

The six fragments CELL-1 uses, which CELL-2 would mirror:

- `configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json`
- `configs/experiment/slurp-native-stage3-delta-cell-smoke-4-v1.json`
- `configs/baseline/slurp-native-stage3-delta-cell-baseline-v1.json`
- `configs/baseline/slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json`
- `configs/baseline/slurp-native-stage3-delta-cell-twin-baseline-v1.json`
- `configs/baseline/slurp-native-stage3-delta-cell-twin-smoke-4-baseline-v1.json`

**CELL-2 needs its own run and attempt ids.** CELL-1's
(`SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1`, `...-TWIN-V1`, and the smoke identities) are sealed and
their exposure rows are consumed; the runbook's `repoint` step rewrites store pins in place and
is for a HELD cell, never for re-pointing a sealed identity onto new content. A derived cell
protects the registry id, carries its own policy program where a role budget changed, and
carries rescaled fit caps -- so CELL-2 is a sibling fragment set with `-v2` identities, not an
edit of the six files above.

## 4. What CELL-2 would cost

Per node, the share of CELL-1's supplied items whose value survives retention (an upper bound on
the reduction, because the Solver and Reviewer caps bind and refill from the remaining pool):

| node | route | cap | CELL-1 items | items whose value is kept | rows at full cap |
| --- | --- | ---: | ---: | ---: | ---: |
| perception | unconditional | 4 | 4,320 | 4,320 (100 %) | 1,080 / 1,080 |
| solver | candidate-bound | 8 | 6,386 | 3,597 (56.3 %) | 536 / 1,080 |
| reviewer | candidate-bound | 4 | 3,722 | 1,834 (49.3 %) | 727 / 1,080 |
| planner | candidate-bound | 4 | 807 | 267 (33.1 %) | 0 / 1,080 |

Two consequences worth stating before the flight rather than after it:

1. **Perception does not move.** The unconditional route is the top 4 perception values by
   `prior_score` descending, `value_id` ascending
   (`rails.stage3_delta_supply.select_unconditional_stage3_delta_values`). All four CELL-1 seeds
   are KEPT and retirement only removes rows, so the v2 top 4 is the same four value ids.
   CELL-2 therefore tests the three CANDIDATE-BOUND routes and nothing else.
2. **Planner nearly closes.** 4 of 14 planner values survive, over 4 distinct facets; the
   planner route was already the weakest (0.75 items per row, never at cap). If CELL-2 is read,
   the planner route's contribution should be reported separately rather than pooled, and an
   inert-route check (the B9a-rec failure mode) belongs in the preflight.

Cost expectation: strictly below CELL-1 on both axes -- fewer supplied items at three of four
nodes, no new contact, the same 4.22 contacts per row -- but NOT down to the PLAN row, because
Perception's 4 unconditional items per row and the binding Solver/Reviewer caps stay. A
defensible pre-registration is "no more than CELL-1's 9,264.9 prefilled tokens per row and no
more than its 1.8021 GPU-h per 1,080", with the realised number measured, not predicted.

## 5. Read discipline

- CELL-2 is a **second look on the same TRAIN Fold A rows** that produced the retention rule. It
  is not an independent confirmation of anything: the rows that chose which deltas to keep are
  the rows the keeping is then scored on. Its verdict is a development number under owner
  decision 28.
- Any effectiveness claim needs the **replicate on a fresh roster** first -- Fold B or DEV --
  and the per-stratum table beside the pooled number, per the 2026-09-03 owner reporting rule.
- The **twin arm is not optional.** `stage3-deltas-twin-v2` exists so that a v2 gain can be
  separated from a form effect (a smaller store is also a shorter prompt, and IDX already showed
  this study a pure form loss of -7.37 SLU). A CELL-2 arm read without its twin proves nothing
  about content.
- One experiment in flight; a new mechanism is admitted only after its predecessor is replicated
  or root-caused. CELL-2 is the root-cause follow-through of CELL-1, not a new mechanism.
- The band used here is DERIVED from one replicate pass. It is a decision rule for pruning, not
  a measured per-scenario null: a per-scenario band with a real interval would need more than
  one PLAN replicate, and no claim in this note or in CELL-2's verdict may treat it as one.

## 6. The exact commands, when the coordinator decides to go ahead

Everything below is run from a worktree of this repository in WSL2 `Ubuntu-24.04`, with
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=$REPO:$REPO/src`,
`SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data` and
`PY=/home/chao/.venvs/speechrl/bin/python`.

### 6.1 Re-derive the retention document (optional; it is already built and pinned)

```bash
$PY -B scripts/build_slurp_stage3_delta_retention.py \
  --authored "$PREPARED/authored-stage3-deltas-v1r.json" \
  --cell-per-scenario "$DATA/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R01-PAIRED-ANALYSIS-V1/per-scenario-tables.json" \
  --own-null-per-scenario "$DATA/analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-REPLICATE-PAIRED-ANALYSIS-V1/per-scenario-tables.json" \
  --delta-consumption "$DATA/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R01-PAIRED-ANALYSIS-V1/delta-consumption.json" \
  --registered-facts docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/registered-facts-v1.json \
  --out-json "$PREPARED/retention-v2.json" \
  --out-markdown docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/iteration-2-retention-v1.md
```

`--tie-threshold-pp` (default `0.0`) and `--unreached-policy` (default `keep`) are the two
parameters of the rule; changing either changes the retained set and must be stated in the
verdict.

### 6.2 Release both v2 stores

One command -- the runbook drives curation, twin, wrap, both registrations, both releases and
the reach expectation:

```bash
REPO=$REPO DELTAS_DRY=0 \
DELTA_VERSION_TAG=v2 DELTA_FROM_VERSION_TAG=v1r \
DELTA_ITERATION=2 \
DELTA_PREDECESSOR="$PREPARED/authored-stage3-deltas-v1r.json" \
DELTA_RETIRE_VALUE_IDS="$PREPARED/retention-v2.json" \
bash scripts/flights/batch/adv1_to_deltas.sh
```

Step B re-curates the two v2 documents already built above, so their digests must come back
unchanged; if they do not, the release fails closed on the registration's `authored_source` pin
rather than releasing different content. Step F re-points fragment store pins from `v1r` to
`v2` -- **skip it for CELL-1's sealed fragments** and apply it only to CELL-2's own copies.

### 6.3 Fill CELL-2

1. Derive CELL-2's six fragments from CELL-1's (new experiment ids, new run ids, new attempt
   ids, own policy program and rescaled fit caps if any role budget moved).
2. Point their `knowledge_stores.stage3-deltas` pins at the released v2 namespaces:

   ```bash
   $PY -B scripts/flights/batch/adv1_to_deltas_steps.py \
     --repo-root "$REPO" --data-root "$DATA" cell1-values \
     --version-tag v2 --values-out "$COORD/cell1-fill-values-v2.json"
   $PY -B scripts/flights/batch/adv1_to_deltas_steps.py \
     --repo-root "$REPO" --data-root "$DATA" repoint \
     --values "$COORD/cell1-fill-values-v2.json" \
     --version-tag v2 --from-version-tag v1r
   ```

   (`$COORD` = `$DATA/coordination/slurp-stage3-delta-cell-r01-v1`. The snapshot value is the
   snapshot's CONTENT hash, never the `snapshot.json` file digest.)
3. Re-pin the cell (`scripts/flights/repin_cell.py`), run the offline gates, land the smoke
   before the arm, and only then queue the arm and its twin through the batch driver
   (decision 77: flights only through the scheduled driver).
