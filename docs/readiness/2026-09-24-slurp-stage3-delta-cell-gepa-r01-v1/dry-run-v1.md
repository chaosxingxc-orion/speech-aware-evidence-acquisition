# CELL-1-GEPA: the offline four-row native-episode dry run (zero contacts)

Model-free by construction: **zero** model, tool, network, GPU, gate, transport, client, attempt,
tokenizer, encoder, scorer and serving-session contacts. Driver
`scripts/flights/batch/gepacell_dry_run.py`; walker
`speech_aware_evidence_acquisition.analysis.native_episode_dry_run`. The REAL registered smoke cells
are composed from the committed fragments over the REAL released GEPA stores and walked node by
node; only the four role answers are canned, exactly as a fake frozen core would answer. No
utterance text, no gold label and no delta statement text is read, printed or persisted -- value
ids, node names and counts only.

Item 5 of `docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/cell-1-gepa-diff-plan-v1.md`: the walk
covers **every** row of the smoke roster with the candidate ids a real trace recorded, and includes
a REVISE walk.

| | arm | twin |
| --- | --- | --- |
| cell | `slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1` | `slurp-native-stage3-delta-cell-gepa-r01-smoke-4-twin-v1` |
| release pinned | `knowledge/slurp/semantic/stage3-deltas-gepa-v1/release.json` | `knowledge/slurp/semantic/stage3-deltas-gepa-twin-v1/release.json` |
| release sha256 | `53c1267169b5269bc850f75527b2c8086fd681126f9180ac4a0df9410b61fcfa` | `fb2dad3082848f1ff794401f2ea1d9b0d53e33b0f7a459592b44364cce196fb3` |
| snapshot content hash | `560d84e7e6364de5ce09635f586660d22b9a103734c51dbd64e6182599fb935c` | `f19671d381f82ffb07f7d186b93c45adfe129bcf934e62011abdec1744123ffe` |
| verdict | **PASS** (`ok: true`) | **PASS** (`ok: true`) |

## 1. The ACCEPT walk, every row of the roster

Delta items supplied per candidate-bound node. The Perception route is **seeded** into the initial
`QueryState` before the walk (4 unconditional values, the same four value ids as CELL-1's and
CELL-2's -- measured, not assumed), so it is never a node-boundary supply here and reads 0 in this
table.

| row | arm S | arm R | arm Pl | twin S | twin R | twin Pl |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `slurp:train:000007:audio--1504197557` | 8 | 4 | 4 | 8 | 4 | 4 |
| `slurp:train:000009:audio-1497557594-headset` | 1 | 4 | 4 | 4 | 3 | 2 |
| `slurp:train:000015:audio-1488524781` | 5 | 4 | 4 | 5 | 4 | 2 |
| `slurp:train:000023:audio-1490956038` | 0 | 0 | 0 | 0 | 0 | 0 |

Every row on both forms walked the whole graph `perception -> solver -> reviewer -> planner` and
delivered from the Solver's sealed draft.

Totals over the four rows -- **the registered structural rule for the smoke: the flight's realised
counts must EQUAL these**:

| | perception | solver | reviewer | planner |
| --- | ---: | ---: | ---: | ---: |
| arm items | 0 | 14 | 12 | 12 |
| arm rows supplied | 0 | 3 | 3 | 3 |
| twin items | 0 | 17 | 11 | 8 |
| twin rows supplied | 0 | 3 | 3 | 3 |

Two facts this table registers before contact:

1. **The arm and the twin do not match per node.** The derangement moves each row's whole
   attachment tuple, so a candidate-bound route selects a different slice; only the store's total
   authored token count (7,345) is held. The read reports realised supplied items and tokens for
   both arms separately and assumes no identity between them.
2. **Row `slurp:train:000023:audio-1490956038` declines all three candidate-bound routes on both forms.** Its
   Perception candidates are `iot_hue_lightdim` / `iot_hue_lighton` / `iot_hue_lightoff`, which
   reach no value in the store (the released reach block covers `iot_hue_lightchange`,
   `iot_hue_lightup` and `iot_wemo_off`). Each declined route is receipted with its reason. Four
   rows cannot decide whether a route is inert at population level -- the 1,080-row arm's own
   delta-consumption table does (the B9a-rec check) -- so this is reported, never failed.

## 2. The REVISE walk (row `slurp:train:000007:audio--1504197557`)

Node order `perception, solver, reviewer, planner, solver, reviewer, planner`; the Planner answers
`REVISE` on its first visit and `ACCEPT` on its second.

| form | perception#1 | solver#1 | reviewer#1 | planner#1 | solver#2 | reviewer#2 | planner#2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arm | 0 | 8 | 4 | 4 | 1 | 4 | 4 |
| twin | 0 | 8 | 4 | 4 | 4 | 4 | 0 |

**Duplicate acquisitions: arm 0, twin 0.** Distinct delta value ids over the
whole episode: arm 25, twin 24.

THE REGISTERED INVARIANT IS DISJOINTNESS, NOT EMPTINESS, and that is a deliberate correction of the
rule the CELL-2 driver carried. A candidate-bound route excludes what the accumulated `QueryState`
already holds and then fills its cap from what is left, so at a 448-value store a revisited node
acquires a SECOND, DISJOINT slice instead of nothing; at CELL-2's 200-value store there was no
second slice to find, and "acquires nothing" and "acquires nothing it already holds" could not be
told apart there. The failure mode that matters is unchanged and is what this walk tests:
`QueryState` refuses a duplicate `retrieved_value_id`,
`EvidenceAgentController._acquired_ids` refuses the decision and the trajectory dies (the
2026-09-17 cell B1 abort). Both forms acquire **zero** duplicates, so that mode cannot fire.

The consequence for cost is registered here and measured on the flight: a REVISED row carries more
delta text than an accepted one. The plan's `context_fit_policy` is `compact-or-abstain` and the
E20 compaction count is a mandatory diagnostic of the read.

## 3. The DUPLICATE-candidate walk (row `slurp:train:000007:audio--1504197557`, n=3 distinct=1)

The shape that aborted the CELL-1 arm after 304 metered contacts. Both forms walk the whole graph
instead of raising, with 3 candidate projections receipted.

| form | perception | solver | reviewer | planner |
| --- | ---: | ---: | ---: | ---: |
| arm | 0 | 5 | 4 | 4 |
| twin | 0 | 5 | 4 | 2 |

## 4. What this proves, and what it does not

PROVES: every row of the smoke roster walks the whole role graph and delivers on both forms; no
revisit re-acquires a held value; a duplicate-candidate Perception answer walks; every declined
route is receipted; the per-node counts above are the smoke's acceptance rule.

DOES NOT PROVE: any effectiveness claim, any population-level statement about whether a route
serves, or the prompt-fit bound (that is `core.flight.cli check`'s `_assess_prompt_budget` in the
coordinator's own clean-tree cycle, and the authority in flight is
`core.preparation_fit.build_native_contact_fit_gate`).

The driver also accepts `--experiment` so the same walk can be taken over a CELL-1 or CELL-2 smoke
fragment as the version-1r / version-2 control of the same rows.
