# Cell ROLL-3 -- the offline four-row dry run and the pre-mint check

**This is the PRE-FLIP run.** It was run model-free at study commit `de730eab` (the commit that
landed the fragments, the package and the four draft exposure rows) from worktree
`/home/chao/saea-worktrees/fable-roll3`, branch `fable/roll3`, by
`scripts/flights/batch/roll3_dry_run.py` over the REGISTERED four-row smoke cell
`slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1` composed from its committed fragments.
**Verdict: `ok = true` -- all three proofs hold.** The readiness flip re-pins this cell's own
prepared phase supply into the baseline, which moves the composed bytes, so **the coordinator re-runs
this dry run at the flipped bytes** and rewrites the one hash line below (it is quoted exactly once in
this note, so the re-run's rewrite is one edit); the pre-flip record is not evidence about what will
fly, only that the registered form composes and walks.

**Contacts: zero.** No model, tool, tokenizer, encoder, scorer, server, GPU, network, gate,
transport, client, attempt or serving-session contact of any kind. Only the four role answers are
canned, exactly as a fake frozen core would answer; every other object -- the composed config, the
episode loader, the phase program, the knowledge router, the phase supply, the packet binding, the
roster -- is the production one. The resident flight on port 8080 was neither started, stopped nor
probed.

## Proof 1 -- FORM: the composed episode IS cell ROLL-2's grouped-Solver form

| key | expected (cell ROLL-2's form, itself cell ROLL-1's) | measured | agrees |
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

`form.agrees = true`, no disagreements. Composed config hash of the smoke cell at the pre-flip bytes:
`5e91c6f83983da147e8d9931cbf74599499c95c6da2d9064fdfabfdafed89786` (the only place this note quotes it).

Two absences are part of the form and were measured, not assumed:

- `native_episode.deliver_normaliser` is **absent (`null`)** -- a grouped Solver forbids a deliver-normaliser
  node. The sealed DEV-2000-ADDED plan arm carries `saea-deliver-normalise-v3`; ROLL-3 does not,
  because ROLL-3 is cell ROLL-2's form on the evaluation roster and not the plan arm with a Solver
  group bolted on. This is a registered difference from the plan arm, stated before contact.
- `prepared_phase_supply` is **`ABSENT (minted at the flip, item E16)`**: the cell carries no committed pin, so the readiness flip
  mints its own under its own run id and `--allow-output-change` must never be passed. The post-flip
  re-run will measure it PRESENT and should say so.

## Proof 2 -- IDENTITY: the five samples are one request drawn five times

`rails.runner._solver_fragment_seed('phase-native-candidates-review-revise-samples5-v1')` = **1249110493**, so the five seeds are
`1249110493`, `1249110494`, `1249110495`, `1249110496`, `1249110497`. The base decoding params are ``{"id_slot": "per-sample", "max_tokens": 512, "seed": 20260913, "temperature": 0}``; each sample's composed params are the same object
with `temperature` set to the declared 0.7 and `seed` set to `fragment_seed + seed_offset +
sample_index`, e.g. sample 0 ``{"id_slot": "per-sample", "max_tokens": 512, "seed": 1249110493, "temperature": 0.7}``.

- fields that differ across the five samples: **`seed`**
- every temperature is the declared 0.7: **true**
- all five seeds distinct: **true**

That is the property the sealed pool's later offline reads depend on: five independent draws of ONE
request, not five different requests. The seeds are the program's, not the roster's, so they are the
same five cell ROLL-2 flew on TRAIN Fold A.

## Proof 3 -- WALK: every smoke row walks the DEV-2000-ADDED graph and delivers

Canned candidate intents, read off the composed runtime's own registered legal intent list (nothing
here invents a label): `alarm_query`, `alarm_remove`, `alarm_set`.

| row (DEV-2000-ADDED sample id) | walked | delivered | supplied items: perception / solver / reviewer / planner |
| --- | --- | --- | --- |
| `slurp:devel:000017:audio-1501773854-headset` | perception -> solver -> reviewer -> planner | solver | 0 / 31 / 0 / 0 |
| `slurp:devel:000024:audio-1490195864-headset` | perception -> solver -> reviewer -> planner | solver | 0 / 31 / 0 / 0 |
| `slurp:devel:000026:audio-1502216425-headset` | perception -> solver -> reviewer -> planner | solver | 0 / 31 / 0 / 0 |
| `slurp:devel:000026:audio-1502301875` | perception -> solver -> reviewer -> planner | solver | 0 / 31 / 0 / 0 |

Every row walks `perception -> solver -> reviewer -> planner` and delivers. The DEV-2000-ADDED
knowledge artifacts resolve at every node boundary -- the re-pointed intent-boundary segment vectors
(`vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl`), the re-pointed content vectors
(`vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl`), the parent
`size-pool-annotated-exemplars` store and the DEV-2000-ADDED speech packets -- so a missing
DEV-2000-ADDED vector line or an unresolvable packet would have raised here. The third and fourth
rows are the roster's own two recordings of one utterance and each walks and delivers on its own.

**On the supply counts.** `supplied_items_per_node` counts `node.supplied_value_ids`, which is the
knowledge-provider supply resolved at the node boundary; the Perception candidate fill arrives by a
different path and is not counted in this field. It reads 0 at Perception and 31 at the Solver on
every row here, exactly as it read on cell ROLL-2's Fold A smoke rows and on the flown ROLL-AA smoke
on R01C (both 0 / 31 / 0 / 0 on every row), so the shape is the harness's, not a property of the
DEV-2000-ADDED re-point. Four rows cannot decide whether a route is inert in any case: these counts
are INFORMATION, never a verdict.

## The pre-mint `check`, both cells

Run on the same clean tree at `de730eab`, immediately after the draft rows landed (the exposure gate
inside preflight matches each plan against its row), with
`python -B -m speech_aware_evidence_acquisition.core.flight.cli check --repo-root <worktree> --data-root <data> --runtime-root /home/chao --lock-path <umbrella datasets.lock.json> --experiment <cell> --cell <cell>`.
Both exited 0 with `blockers` absent and `generation_authorized: false`.

| cell | readiness | sample_count | runtime `config_hash` / `protocol_hash` equal the registered values | prompt budget |
|---|---|---|---|---|
| `slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1` | `held` (root admission receipt not yet minted) | 4 | yes (both, against `registered-facts-v1.json` `cells.smoke`) | ALLOW, margin 1,511 tokens over the 3,072 reserve in the 24,576 slot |
| `slurp-native-stage3-roll-3-dev2000-added-v1` | `held` (root admission receipt not yet minted) | 1000 | yes (both, against `registered-facts-v1.json` `cells.arm`) | ALLOW, margin 1,511 tokens over the 3,072 reserve in the 24,576 slot |

`prepared_artifacts` is empty on both, as item E16 requires before the flip. The check touched the
runtime root read-only and left the worktree clean (`git status --short` empty afterwards). It is
recorded here, not re-stamped into the plan files, so the ledger's Plan SHA256 values stay true.

## What the verdict is

ok means: the composed episode IS cell ROLL-2's registered grouped-Solver form (proof 1), the five Solver samples are one request drawn five times at the declared temperature (proof 2), and every smoke row walks the whole graph and delivers with the DEV-2000-ADDED knowledge artifacts resolving at every node boundary (proof 3). The supply counts are INFORMATION: four rows cannot decide whether a route is inert.

Re-run at the flipped bytes after the smoke flip (the coordinator, 2026-09-27, zero contacts): ok = true, form.agrees = true; the composed hash above is the flipped one.
