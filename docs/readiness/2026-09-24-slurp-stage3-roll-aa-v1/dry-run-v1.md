# Cell ROLL-AA: offline dry run over the four smoke rows

Driver: `scripts/flights/batch/rollaa_dry_run.py`, run 2026-09-24 in worktree
`/home/chao/saea-worktrees/fable-aanull` (branch `fable/aanull`) at study commit `95951add`
plus this registration's own uncommitted tree.

**Contacts: zero of every kind** -- no model, tool, network, GPU, gate, transport, client, attempt
or serving-session contact, and no audio sample decoded. The REAL registered smoke cell is
composed from the committed fragments and walked node by node by
`speech_aware_evidence_acquisition.analysis.native_episode_dry_run`; only the four role answers are
canned, exactly as a fake frozen core would answer.

**Result: `ok = true`.** All three proofs hold.

## Proof 1 -- FORM: the composed episode is the registered A/A form

Composed config hash `0decf326679336d94a74c9e4fb4a999a9cefe0ff7278bba9dd4ecd3377fd322e` (the smoke
cell). Expected and measured agree on every key, with no disagreements:

| key | value |
| --- | --- |
| `policy` | `phase-native-candidates-review-revise-samples2-v1` |
| `program.max_contacts` | 13 |
| bounded graph ceiling (`rails.native_episode_config`) | 13 |
| `roles.solver.samples` | 2 |
| `roles.solver.twin` | `greedy-repeat` |
| `roles.solver.decoding_overrides.temperature` | 0.0 |
| `roles.solver.decoding_overrides.seed_offset` | 0 |
| `roles.solver.commit` | `saea-commit-plurality-support-v1`, `min_support` 2, `similarity_threshold` 0.8 |
| `max_revisions` | 1 |
| `review_loop` | `on` |
| role iterations | perception 1, solver 1, reviewer 3, planner 1 |

The program's declared ceiling and the loader's own graph ceiling both resolve to 13; the loader
refuses by name when they disagree, so this is a checked equality, not a coincidence.

## Proof 2 -- IDENTITY: the two samples are one request up to an inert seed

Built by the production `reproduction.ojw.native_request.compose_solver_sample_decoding_params`
with the real `rails.runner._solver_fragment_seed("phase-native-candidates-review-revise-samples2-v1")`
= **2080141211**, over the composed base `{id_slot: per-sample, max_tokens: 512, seed: 20260913,
temperature: 0}`:

| sample | composed request decoding params |
| --- | --- |
| 0 | `{id_slot: per-sample, max_tokens: 512, seed: 2080141211, temperature: 0.0}` |
| 1 | `{id_slot: per-sample, max_tokens: 512, seed: 2080141212, temperature: 0.0}` |

`fields_that_differ = ["seed"]`; `both_temperatures_zero = true`.

The two seeds differ **by construction** -- `seed = fragment_seed + seed_offset + sample_index`, and
the grouped sampler offers no way to make them equal; `rails.native_episode_receipt
.validate_solver_group_receipt` additionally *requires* distinct pinned seeds. At temperature 0
llama.cpp decodes greedily and does not consult the seed, which is exactly why
`rails.native_episode_config` admits temperature 0 only under the explicit `twin: "greedy-repeat"`
marker and calls those seeds *"recorded custody, never a source of diversity at temperature 0."*

## Proof 3 -- WALK: every smoke row walks the whole graph and delivers

Canned Perception candidates, read off the composed runtime's own registered legal-intent list:
`alarm_query`, `alarm_remove`, `alarm_set`. Planner answers `ACCEPT` on its first visit.

| row | walked | delivered | supplied items per node |
| --- | --- | --- | --- |
| `slurp:train:000049:audio-1434542455` | perception -> solver -> reviewer -> planner | solver | perception 0, solver 31, reviewer 0, planner 0 |
| `slurp:train:000051:audio-1434531302-headset` | perception -> solver -> reviewer -> planner | solver | perception 0, solver 31, reviewer 0, planner 0 |
| `slurp:train:000234:audio-1499688528` | perception -> solver -> reviewer -> planner | solver | perception 0, solver 31, reviewer 0, planner 0 |
| `slurp:train:000260:audio-1488549919` | perception -> solver -> reviewer -> planner | solver | perception 0, solver 31, reviewer 0, planner 0 |

The 31 items at the Solver are the locked plan's own knowledge channel (the k = 20 exemplar slice
plus the slot-contract values), unchanged by this cell -- ROLL-AA touches the Solver's *sampling*,
not its supply. Perception's route is seeded before the walk rather than supplied at a node
boundary, so 0 there is the expected shape, and the Reviewer/Planner zeros are information, not a
verdict: four rows cannot decide whether a route is inert.

## What the dry run does not prove

It does not decode anything, so it cannot say whether the two greedy passes will actually produce
identical bytes -- measuring that residual is the entire point of the cell. It also walks a single
ACCEPT path; a `REVISE` round would open a second grouped Solver visit, and the read reports the
revision share so that case stays visible.
