# Cell ROLL-2 -- the offline four-row dry run

Run model-free twice. First at study commit `e0a8d20d` from worktree
`/home/chao/saea-worktrees/fable-roll2`, branch `fable/roll2`, before the readiness flip; then RE-RUN on
`master` at `88eee136` after the flip re-pinned this cell's fragments, because the re-pin changes the
composed bytes and a dry run that quotes a superseded hash is not evidence about what will fly. Every
number below is the RE-RUN's, and the two runs agree on all three proofs. By
`scripts/flights/batch/roll2_dry_run.py` over the REGISTERED four-row smoke
cell `slurp-native-stage3-roll-2-fold-a-smoke-4-v1` composed from its committed fragments. **Verdict: `ok = true` -- all three proofs
hold.**

**Contacts: zero.** No model, tool, tokenizer, encoder, scorer, server, GPU, network, gate,
transport, client, attempt or serving-session contact of any kind. Only the four role answers are
canned, exactly as a fake frozen core would answer; every other object -- the composed config, the
episode loader, the phase program, the knowledge router, the phase supply, the packet binding, the
roster -- is the production one.

## Proof 1 -- FORM: the composed episode IS cell ROLL-1's grouped-Solver form

| key | expected (cell ROLL-1's form) | measured | agrees |
|---|---|---|---|
| `policy` | `phase-native-candidates-review-revise-samples5-v1` | `phase-native-candidates-review-revise-samples5-v1` | yes |
| program `max_contacts` | 19 | 19 | yes |
| loader graph ceiling | 19 | 19 | yes |
| Solver `samples` | 5 | 5 | yes |
| Solver `twin` | none | `null` | yes |
| Solver `temperature` | 0.7 | 0.7 | yes |
| Solver `seed_offset` | 0 | 0 | yes |
| commit policy | `saea-commit-plurality-support-v1` | `saea-commit-plurality-support-v1` | yes |
| commit `min_support` | 3 | 3 | yes |
| commit `similarity_threshold` | 0.8 | 0.8 | yes |
| `max_revisions` | 1 | 1 | yes |
| review loop | on | on | yes |
| roles (perception / solver / reviewer / planner) | 1 / 1 / 3 / 1 | 1 / 1 / 3 / 1 | yes |

`form.agrees = true`, no disagreements. Composed config hash of the smoke cell
`dc6f8e55bd35b330767479d2e3ceba3b7a0bbb164db29a037d823b2d4d9be9f2`.

Two absences are part of the form and were measured, not assumed:

- `native_episode.deliver_normaliser` is **absent (`null`)** -- a grouped Solver forbids a deliver-normaliser
  node. The sealed lock arm PLAN carries `saea-deliver-normalise-v3`; ROLL-2 does not, because
  ROLL-2 is cell ROLL-1's form on the lock roster and not the lock arm with a Solver group bolted
  on. This is a registered difference from the lock arm, stated before contact.
- `prepared_phase_supply` carried **no committed pin** before the flip, exactly as item E16 requires, so the
  readiness flip minted this cell's OWN first-phase supply under its own run id. The re-run measured it
  PRESENT at `f6ab4280f0c25bbdba1b6a4565bbef17c3c8563092fc90ab626a7ddce025781a`, which is the artefact
  the smoke will actually read; `--allow-output-change` must never be passed.

## Proof 2 -- IDENTITY: the five samples are one request drawn five times

`rails.runner._solver_fragment_seed('phase-native-candidates-review-revise-samples5-v1')` = **1249110493**, so the five seeds are
`1249110493`, `1249110494`, `1249110495`, `1249110496`, `1249110497`. The base decoding params are ``{"id_slot": "per-sample", "max_tokens": 512, "seed": 20260913, "temperature": 0}``; each sample's composed params are the same object
with `temperature` set to the declared 0.7 and `seed` set to `fragment_seed + seed_offset +
sample_index`, e.g. sample 0 ``{"id_slot": "per-sample", "max_tokens": 512, "seed": 1249110493, "temperature": 0.7}``.

- fields that differ across the five samples: **`seed`**
- every temperature is the declared 0.7: **true**
- all five seeds distinct: **true**

That is the property the sealed pool's later offline reads depend on: five independent draws of ONE
request, not five different requests.

## Proof 3 -- WALK: every smoke row walks the Fold A graph and delivers

Canned candidate intents, read off the composed runtime's own registered legal intent list (nothing
here invents a label): `alarm_query`, `alarm_remove`, `alarm_set`.

| row (Fold A sample id) | walked | delivered | supplied items: perception / solver / reviewer / planner |
| --- | --- | --- | --- |
| `slurp:train:000007:audio--1504197557` | perception -> solver -> reviewer -> planner | solver | 0 / 31 / 0 / 0 |
| `slurp:train:000009:audio-1497557594-headset` | perception -> solver -> reviewer -> planner | solver | 0 / 31 / 0 / 0 |
| `slurp:train:000015:audio-1488524781` | perception -> solver -> reviewer -> planner | solver | 0 / 31 / 0 / 0 |
| `slurp:train:000023:audio-1490956038` | perception -> solver -> reviewer -> planner | solver | 0 / 31 / 0 / 0 |

Every row walks `perception -> solver -> reviewer -> planner` and delivers. The FOLD A knowledge
artifacts resolve at every node boundary -- the re-pointed intent-boundary segment vectors, the
re-pointed content vectors, the parent `size-pool-annotated-exemplars` store and the EVO-FOLDS-V2
speech packets -- so a missing Fold A vector line or an unresolvable packet would have raised here.

**On the supply counts.** `supplied_items_per_node` counts `node.supplied_value_ids`, which is the
knowledge-provider supply resolved at the node boundary; the Perception candidate fill arrives by a
different path and is not counted in this field. It reads 0 at Perception and 31 at the Solver here,
and it reads **exactly the same** on the already-flown ROLL-AA smoke on R01C at this same commit:

| ROLL-AA smoke row (R01C, already flown) | perception / solver / reviewer / planner |
| --- | --- |
| `slurp:train:000049:audio-1434542455` | 0 / 31 / 0 / 0 |
| `slurp:train:000051:audio-1434531302-headset` | 0 / 31 / 0 / 0 |
| `slurp:train:000234:audio-1499688528` | 0 / 31 / 0 / 0 |
| `slurp:train:000260:audio-1488549919` | 0 / 31 / 0 / 0 |

So the shape is the harness's, not a defect of the Fold A re-point. Four rows cannot decide whether
a route is inert in any case: these counts are INFORMATION, never a verdict.

## What the verdict is

ok means: the composed episode IS cell ROLL-1's registered grouped-Solver form (proof 1), the five Solver samples are one request drawn five times at the declared temperature (proof 2), and every smoke row walks the whole graph and delivers with the FOLD A knowledge artifacts resolving at every node boundary (proof 3). The supply counts are INFORMATION: four rows cannot decide whether a route is inert.
