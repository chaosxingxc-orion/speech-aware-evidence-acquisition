# `stage3-deltas-v1` is superseded by `stage3-deltas-v1r`, before any flight

Written 2026-09-23 by the S3-5 revision agent (worktree `/home/chao/saea-worktrees/fable-s35r`,
branch `fable/s35r`, base master `d3eef48a`). Readiness stays **HELD**: this note supersedes a
released knowledge store, it does not authorize a flight, a readiness flip or an admission entry.
Zero model, tokenizer, encoder, scorer, server, GPU, network and paid-API contacts.

## Why

`stage3-deltas-v1` is **mostly unreachable**. The defect was found by the CELL-1 registration agent
(commit `6d1f30fc`) and registered there as an expectation rather than repaired; the coordinator
then ruled it a defect to fix before contact, because flying a cell on an inert supply is the
cell B9a-rec failure repeated on purpose (`b9a-rec inert acquisition`, 2026-09-22).

A candidate-bound route selects a value only when one of that value's `associated_facet_ids`
**equals** one of the row's Perception candidate **intent** ids
(`rails/knowledge_stores.py::_stage3_delta_local_supply` ->
`rails/stage3_delta_supply.py::select_stage3_delta_values`). S3-5's curator wrote
`associated_facet_ids = [TARGET]`, and for the 147 slot-contract rows `TARGET` is a **slot type**
(`place_name`, `device_name`, ...), which no Perception candidate list can ever name. A generic
target (`query`, `entities`) is unreachable for the same reason.

## The numbers, model-free

Measured by `scripts/flights/batch/adv1_to_deltas_steps.py reach` against the 60 registered SLURP
candidate intents of `prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/catalog.json`. The
step reproduces the v1 figures commit `6d1f30fc` registered by hand, exactly.

| node | route | values | reachable (v1) | reachable (v1r) |
| --- | --- | --- | --- | --- |
| `perception` | unconditional | 119 | 80 (66.8 %) -- **not a bound**, the route is unconditional | 119 (100 %) |
| `solver` | candidate-bound, cap 8 | 151 | **11 (7.3 %)** | **151 (100 %)** |
| `reviewer` | candidate-bound, cap 4 | 95 | 24 (25.3 %) | 95 (100 %) |
| `planner` | candidate-bound, cap 4 | 14 | 6 (42.9 %) | 14 (100 %) |
| total | | 379 | **121 (31.9 %)** | **379 (100 %)** |

Distinct intents covered: v1 solver 8, reviewer 13, planner 6, 29 overall; v1r solver 34,
reviewer 30, planner 14, perception 34, **39 overall** of the 60-intent vocabulary. The twin's
totals match its parent's on both versions (v1 121, v1r 379), so the form control is now supplied
at the same volume as the arm rather than at a different one -- which removes the twin
token-matching caveat commit `6d1f30fc` had to register (v1 arm solver 11 against twin solver 22).

## What changed, and what did not

**Only the facet rule.** `scripts/build_slurp_stage3_delta_store.py --facet-rule source-intent`
(the new default for schema v2) writes the ordered, de-duplicated union of

1. the construction **gold intent id** (`<scenario>_<action>`) of every source row the statement
   was drawn from (`--gold-intents`
   `coordination/slurp-stage3-advantage-r01-v1/r01c-gold-intents.json`, legal on the construction
   side under owner decision 82), and
2. the bare `TARGET` when `TARGET` is itself a legal intent id (`--intent-vocabulary`, the
   registered candidate catalog), so an intent-boundary row keeps its target intent as a facet.

A slot type never becomes a facet. This is a routing key over the **construction** population
only: the read population's gold never enters the store, any runtime path or any prompt, exactly as
`slot-contracts`, `intent-boundaries` and `train-exemplars` already carry TRAIN intent ids as facet
ids.

**Unchanged**: the statements themselves (same ADV-1 outputs, same parse, same six-token
containment rule with 3 blocks dropped), `task_target`, `node_target`, the `value_id` form
(`delta:<iteration>:<sha256(statement)[:12]>`), the append-only predecessor rule, the
exact-normalised and Jaccard dedup, `prior_score`, `source_sample_ids`, `provenance_refs`, the
release envelope, the registration shape, the four per-node routes and their caps, and the twin
seed 20260922.

**Counts unchanged**: 379 values; node targets perception 119 / solver 151 / reviewer 95 /
planner 14; delta kinds slot-contract 147 / intent-boundary 117 / reviewer-criterion 95 /
planner-rule 13 / exemplar-note 5 / perception-hint 2; 223 source sample ids; mean statement
84.0 characters, longest 126.

**Counts that moved**: distinct facets 97 -> **39** (every one of them now a legal intent id);
per-row facet counts 379 x 1 -> 357 x 1, 21 x 2, 1 x 3 (402 facet entries); 7 duplicate absorptions
now also merge facets, because a facet id records which intent the lesson was learned on.

`--facet-rule target-only` keeps the pre-v1r rule and is **proven** byte-identical: re-curating the
same sealed ADV-1 outputs under it reproduces `authored-stage3-deltas-v1.json`
(`3d2bc069...`) and `source-stage3-deltas-v1.json` (`c548b8df...`, the digest the v1 registration
pins) exactly.

## v1 was never consumed

No CELL-1 run exists. All eight CELL-1 exposure rows read `consumed = no` and carry
`REGISTERED BEFORE CONTACT (draft, root countersignature pending)`; `readiness.state` is `held` on
all six cells; no decision receipt was minted and no cell reached the batch queue. Superseding the
store therefore invalidates no evidence and rewrites no record.

## The v1 hashes, kept for the record

Nothing below is deleted or rewritten. The v1 namespaces, prepared documents and release
registrations stay exactly where they are; this note supersedes them in English, which is the
program's rule for an immutable record.

| artifact | v1 | v1r |
| --- | --- | --- |
| curated document | `3d2bc0693273a10bb727b354926ee2200675cda0000250ac5bff94a0945b2269` | `092dd386bb45e484eea0f2f075dc6570930dece59db674669367fa07a0a0773d` |
| release source (the pinned wrapper) | `c548b8df24fd19f617669e009b0973724d90dd0b2eecaa8ad8591bd2a3d6fce9` | `0041c4a6cd175a5ec50c6297e86383f1924f895c9a11cc480b5ee627d7bd34fc` |
| twin curated document | `01f5c7f35a7fb964127bfc5aa8f5f1aa9bddac7b8c22a8e486bcf9ce51b7aa33` | `a2b13c2168d256b7bd023d8b87c43b5832c66cef4a1b79813f87465c26c10813` |
| twin release source | `7bbd2b8447e90ce9ff78886ba02a88d6f909ea6016cef760e379903f7428d0c8` | `84c60ec34c0446c911ed37a0ec300b3f593349e115f2c194f24bfc8cf34134b4` |
| release registration | `f73b287a5ec3f7bf6f337c42b34d3e6fab9c25228f4763387daa0f1b3c99c482` | `954d102a4b991cf507f968c61376a2fe18dcba1ee40aa05823b69754a4eb4324` |
| twin release registration | `623e977482fe4aaf3b1d1bfb5971ff20b530443fa2c22344a3b285f2b5bada26` | `5efc5c8acdb35540012301b0f4a263c44c5ec5112ce05a886c472ed8f6ecc2a8` |
| `release.json` file digest (the release pin) | `ec9da3e2b8ed842a73c13ea51f58a1f077c787777da2edad82a8234729777338` | `02505ba2e548a008cc6c16ffda6f7b9bff505061863026a3d7e1396c26d6c2e0` |
| snapshot **content** hash (the snapshot pin) | `1d55f44122c741e0c17e5186cf6f17a3181a31bae0152dea95decd7a4b9fea10` | `e2552666ebe6dcd87e4239bfddb3a02d62e8965280b9f52c40acf9cbf4b2f27d` |
| `snapshot.json` file digest (pins neither) | `3a770de1ecb752c27aa00942db9f5de2d94e8cbd7029ec358a3736a8a6dc1de7` | `cf6f7fa639c4b1a0e7e7bad0bf071a8672352a25160544431966d7922250e071` |
| twin `release.json` file digest | `a58a370ce9275391c74ae582704ae04c45ad886f6274bff6edd0256c5448f015` | `7c0dc8979e8b9f1ae66105049168b310d5136c99983f99a98885d01e27d84219` |
| twin snapshot **content** hash | `d393bbbb7db698a881c160ce8a77aea68af9964ab68c10fe2b7c8781b472c5a4` | `5aee8d1df90430272d7eedbafb2ab4fe032178a7b681b692b8234ecb2e56fb98` |
| twin `snapshot.json` file digest | `95c3b2aac36d5e490a662e482808d1ae98b13c76f80eb1f820b0ee3abb57305a` | `b39b6b4c0d27161a6da9434f69821aeedac98ef49ab86d347fae6bd8155c67a4` |

Registration ids: `SAEA-SLURP-STAGE3-DELTAS-PREPARATION-V1R` and
`SAEA-SLURP-STAGE3-DELTAS-TWIN-PREPARATION-V1R`, beside the v1 pair. Namespaces
`knowledge/slurp/semantic/stage3-deltas-v1r/` and `stage3-deltas-twin-v1r/`. The release-pins
document, now carrying the reach block, is
`coordination/slurp-stage3-delta-cell-r01-v1/stage3-deltas-v1r-release-pins.json`; the fill values
are `.../cell1-fill-values-v1r.json`.

## The twin, restated

The candidate-bound group keeps the facet derangement and the unconditional group keeps the TARGET
derangement, but under `source-intent` a row may carry more than one facet, so **both move a row's
whole attachment as one unit** -- the entire `associated_facet_ids` tuple, and for the
unconditional group the donor's `TARGET` field together with the donor's whole tuple. A
permutation of whole tuples preserves the multiset, so the twin's token count (5,740 = the
parent's) and the per-row facet-count multiset are held exactly; both invariants are enforced in
`scripts/build_slurp_stage3_delta_twin.py` and proven in `tests/unit/test_stage3_delta_twin_v2.py`.
On a `target-only` document the donor's tuple *is* `[donor_target]`, so the v1 twin's bytes are
unaffected by the change.

**One caveat to carry into the verdict.** 16 of 379 rows landed on a facet set equal to their own
(`value_fixed_points`), against 0 in v1. That is arithmetic, not a defect: the v1r vocabulary is 39
distinct intents over 379 rows, so a positional derangement will sometimes hand a row an equal
attachment, and the builder refuses only a twin that moved nothing at all. The twin is a genuine
form control on 363 of 379 rows (95.8 %), and the delta-consumption read should say so rather than
claim a perfect derangement.

## What root must still do

1. Mint the admission decision receipt (`coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json`).
2. Flip readiness with `scripts/flights/batch/cell1_flip_all.sh`, which re-pins every hash in this
   package in dependency order.
3. Queue through `scripts/flights/batch/batch_chain_cell1.sh` (decision 77).

Nothing in this note performs any of the three.
