# Readiness package: SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1 (cell CELL-2)

Status: **HELD**. This package registers the engineering for iteration 2 of Stage-3 S3-6 -- the locked
v2.0 plan plus the RETAINED 200-value `stage3-deltas` store -- and authorises no flight, no readiness flip
and no admission entry. Source spec:
`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section S3-6. Governing decision:
owner decision 83. Diff plan:
`docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/iteration-2-plan-v1.md`. The registration note is
`docs/readiness/2026-09-24-slurp-stage3-delta-cell-r02-v1-preregistration.md`.

Stage-3 algorithm (owner decision 101): **`tfgrpo-semantic-advantage-v1`**, operators `update` +
`context_application`, at iteration 2 -- the retention step IS the update operator, and the per-node supply
is the context application. Declared as `stage3_algorithm` in both experiment fragments and checked by
`scripts/checks/stage3_algorithm_label_check.py`.

## What this cell is

CELL-1 with `knowledge_stores.stage3-deltas` re-pointed from `stage3-deltas-v1r` (379 values) to
`stage3-deltas-v2` (200 values), and the twin arm from `stage3-deltas-twin-v1r` to
`stage3-deltas-twin-v2`. **Nothing else moves**: the locked v2.0 PLAN fragment, the four routes and their
caps (Perception unconditional 4, Solver 8, Reviewer 4, Planner 4), `finite_completion_policy`
`deliver-latest-or-abstain`, `react_exhaustion_policy` `continue-without-answer`, `context_fit_policy`
`compact-or-abstain`, the deliver normaliser `saea-deliver-normalise-v3`, the review loop, the
`tfgrpo-semantic-advantage-v1` label, the population (TRAIN Fold A, 1,080 rows, split identity
`61b0f062...`), the caps, the session and the comparator (the sealed PLAN arm at the plan's own null,
h_SLU 1.2485 / h_intent 0.9943).

## The version-2 release (2026-09-24, model-free)

Run step by step from this worktree as the runbook's steps **B / C / W / D / E / R** at
`DELTA_VERSION_TAG=v2 DELTA_FROM_VERSION_TAG=v1r DELTA_ITERATION=2
DELTA_PREDECESSOR=$PREPARED/authored-stage3-deltas-v1r.json
DELTA_RETIRE_VALUE_IDS=$PREPARED/retention-v2.json`. The runbook's step **F** was NOT run: it re-points
CELL-1's sealed fragments, and CELL-2 owns its own.

Step B re-curated the two v2 documents that the retention pass had already built, and reproduced them
**byte for byte**, which is what the release registration's `authored_source` pin requires:

| artifact | sha256 | reproduced |
| --- | --- | --- |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/authored-stage3-deltas-v2.json` | `94c38b35ca4d6b45...` | yes |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/source-stage3-deltas-v2.json` | `e1afc2d86bb27510...` | yes |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/authored-stage3-deltas-twin-v2.json` | `b5fd2caa1b344fe7...` | yes |
| `prepared/SAEA-SLURP-STAGE3-DELTAS-V1/source-stage3-deltas-twin-v2.json` | `08767f3c0b1a8e1a...` | yes |

Released, and the pins the fragments carry:

| | release.json (file digest) | snapshot CONTENT hash | snapshot.json file digest |
| --- | --- | --- | --- |
| `knowledge/slurp/semantic/stage3-deltas-v2/` | `b81df5c5175e45e68933d4875c110fd46bea933283631d2c428187c480fc31f0` | `44a804184cf83a08e85831d40bae942af1e71ed4365b485d833f9a03807ef150` | `f960bc84b920e370...` |
| `knowledge/slurp/semantic/stage3-deltas-twin-v2/` | `b18b141f67dae4b413391d22dd787a3b85480d2b4fab24db0848e547e7aa1a9a` | `131809122d23ccdaac86c9a9426c5e045a9544fc3059c1b46f80a3365151d614` | `cf8f6037a0aad34e...` |

Both runnable release registrations (`stage3-deltas-v2-release-registration.json` sha256 `9ad980f0...`,
`stage3-deltas-twin-v2-release-registration.json` sha256 `548f6640...`) were re-materialised from their
committed templates and came back **identical to the committed bytes**; they stay in the CELL-1 package,
because the preparer records a registration by its repo-relative path and the released `release.json` binds
exactly that path. Release pins, including the reach block:
`coordination/slurp-stage3-delta-cell-r02-v1/stage3-deltas-v2-release-pins.json`. Fill values (never typed
by hand): `coordination/slurp-stage3-delta-cell-r02-v1/cell2-fill-values-v2.json`.

### The store, in counts (model-free, no statement text)

| | v1r (CELL-1 flew it) | v2 (CELL-2) |
| --- | ---: | ---: |
| values | 379 | **200** |
| perception / solver / reviewer / planner | 119 / 151 / 95 / 14 | **80 / 76 / 40 / 4** |
| delta kinds | slot-contract 147, intent-boundary 117, reviewer-criterion 95, planner-rule 13, exemplar-note 5, perception-hint 2 | slot-contract 75, intent-boundary 79, reviewer-criterion 40, planner-rule 4, exemplar-note 2 |
| distinct facets / facet entries | 39 / 402 | **26 / 219** |
| facets per row | 357 x 1, 21 x 2, 1 x 3 | 182 x 1, 17 x 2, 1 x 3 |
| source sample ids | 223 | **136** |
| statement characters | 31,840 | **16,743** |
| authored token count (twin holds it) | 5,740 | **3,001** |
| twin value fixed points | 16 of 379 | 13 of 200 |
| worst-case supplied chars per node (P/S/R/Pl) | 485 / 938 / 423 / 381 | 476 / 850 / 416 / 269 |

Retention: 200 kept, 179 retired; 201 of 379 decided by the SCENARIO rule (83 kept) and 178 by the
frontier-slope tie rule (117 kept); tie threshold 0.0 pp, unreached policy `keep`; the 179 retired ids are
also kept as **dedup tombstones** so the same statements cannot re-enter from the same ADV-1 advantage
outputs (the curation report records `retirement.applied_value_ids` 179 and `curation.retired_suppressed`
182).

### Supply reach (model-free, step R)

200 of 200 values are reachable by a registered candidate intent on **every** node, arm and twin:
perception 80 (22 intents), solver 76 (20), reviewer 40 (15), planner 4 (4); twin identical except solver
19 and planner 3 distinct intents. The intent vocabulary is the 60 registered SLURP candidate intents of
`prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/catalog.json`.

**The Perception slice does not move.** The unconditional route takes the top 4 perception values by
`prior_score` descending, `value_id` ascending; all four of CELL-1's seeds are kept and retirement only
removes rows, so version 2's top 4 is the SAME four value ids. CELL-2 therefore tests the three
candidate-bound routes and nothing else.

## The offline four-row dry run (zero contacts)

`scripts/flights/batch/cell2_dry_run.py` composes the registered CELL-2 smoke cell from the committed
fragments over the REAL released version-2 stores and walks it node by node with
`analysis.native_episode_dry_run`: all four rows on the Perception candidate ids the flight itself produced,
a REVISE revisit, and a duplicate-candidate row. Delta items supplied per node, with the same walk over
CELL-1's v1r store as the control:

| row | arm v2 S / R / P | arm v1r S / R / P | twin v2 S / R / P | twin v1r S / R / P |
| --- | --- | --- | --- | --- |
| `slurp:train:000007:audio--1504197557` | 0 / 1 / 0 | 1 / 3 / 1 | 1 / 0 / 0 | 0 / 4 / 1 |
| `slurp:train:000009:audio-1497557594-headset` | 0 / 0 / 0 | 4 / 0 / 0 | 0 / 0 / 0 | 3 / 1 / 0 |
| `slurp:train:000015:audio-1488524781` | 0 / 1 / 0 | 0 / 2 / 1 | 1 / 0 / 0 | 0 / 3 / 0 |
| `slurp:train:000023:audio-1490956038` | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

The v1r columns reproduce the CELL-1 package's own recorded table exactly. Every walk completes the whole
graph on every row, arm and twin, and delivers from the Solver's sealed draft; the REVISE revisit visits
Solver, Reviewer and Planner a second time and acquires nothing; the duplicate-candidate row (n=3,
distinct=1 -- the shape that aborted the CELL-1 arm) walks, with 3 candidate projections receipted; each
declined route is receipted with its reason.

**These zeros are a property of the four rows, not of the store.** Their candidate intents are
`audio_volume_*`, `play_*` and `iot_hue_*`, which is where the retention cut hardest (iot kept 0 of 19,
play 1 of 25, audio 1 of 3), while the reach measurement says every value is reachable on every node and
CELL-1's own consumption table shows all four routes serving over 1,080 rows. The preregistration therefore
amends the SMOKE's acceptance rule -- the realised per-node counts must EQUAL the table above -- and leaves
the "routes actually serve" evidence to the arm's delta-consumption table, without widening a cap,
redrawing the smoke population or touching the store. Section 4a of the preregistration states this in
full, together with the Planner-slice inert-route risk (4 of 14 values survive).

## The proofs on the committed tree

- `core.flight.cli check` exits **0 on all eight cells** (arm, twin, both arm-side fit identities, the
  generation smoke, the twin smoke and both smoke fit identities), with `prepared_artifacts_ok: true` (no
  pin yet: the flip mints each cell's own), readiness `held`, `generation_authorized` false and no blocker.
  Composed config and protocol hashes are in the preregistration, section 8.
- Prompt fit, measured by the same check: perception 19,992 (+1,512), reviewer 19,856 (+1,648), planner
  19,795 (+1,709), **solver 21,821 (COMPACT_REQUIRED by 317)** against the 24,576-token live slot less its
  3,072 reserve -- identical to CELL-1's, because the bound is driven by the per-node caps and the longest
  statement (126 characters at both versions), which the retention does not move.
- Offline gates: `engineering_base_check.py`, `harness_admission_check.py`, `results_ledger_check.py`,
  `tool_catalog_check.py`, `experiment_handoff_check.py`, `finite_completion_policy_check.py`,
  `stage3_algorithm_label_check.py` and `derived_media_confinement_check.py` all exit 0 on this tree.

## What is registered here

Eight plan documents (`{,twin-}{generation,fit}-plan-registered-v1.json` and their smoke siblings),
`protocol-registered-v1.json`, `registered-facts-v1.json` and `analysis-recipe-v1.json` in this directory;
outside it, the preregistration note, the six config fragments, the two campaign plans, eight unconsumed
DRAFT exposure rows and the runbooks `cell2_repin_{smoke,twin_smoke,arm,twin}.sh`, `cell2_flip_all.sh`,
`batch_chain_cell2.sh`, `cell2_read.sh` and `cell2_dry_run.py`.

## The lessons this package carries forward from CELL-1

1. **A recovery needs two new identities.** CELL-1 lost two relaunches (zero contacts each) because the fit
   gate binds the BASELINE's `native_contact_fit.attempt_id` and refuses an identity that already carries
   evidence. Both fragments' `failure_policy` now say a recovery re-registration needs a new generation
   attempt id AND a new fit attempt id.
2. **A sealed identity is never re-pointed.** The release runbook's fill stage rewrites store pins in
   place, which is right for a held cell and wrong for a consumed one; CELL-2 is a sibling fragment set and
   the fill stage was not run.
3. **`check` does not walk the episode.** Three CELL-1 launches died at node boundaries that `check` cannot
   see. The four-row offline dry run over the real released stores, on the candidates the flight actually
   produced, with a REVISE revisit and a duplicate-candidate row, is a precondition of the smoke here.
4. **An aborted campaign leaves `locks/flight.lock`.** Clear it before the next launch.
5. **The snapshot pin is the CONTENT hash**, never the `snapshot.json` file digest; both were read out of
   the released documents by `adv1_to_deltas_steps.py cell1-values`, not typed.
