# Cell RANKVIS: rank-ordered, rank-visible rendering, converted on AGREE's delivered-but-wrong rows

Registered before contact 2026-09-27 on branch `fable/consume` (owner decision 171). The cell is
**held**. Nothing here authorises a flight, a flip, a receipt or an admission entry; the exposure rows
are DRAFT, root countersignature pending.

**The finding this probe follows.** The mechanism synthesis
([`docs/results/2026-09-27-slurp-mechanism-synthesis.md`](../../results/2026-09-27-slurp-mechanism-synthesis.md),
section 5, rank 2) ranks "rank-ordered, rank-visible rendering of the delivered boundary and exemplar
blocks" second for the large-scale phase: the exemplars are the cosine top 20 on 1,080 of 1,080 rows but
render in lexicographic id order (Spearman between position and rank 0.007), AGREE's 35 saves on rows
delivered in both flights come from re-ordering the eight boundary entries, and after AGREE 89 Fold A rows
have the gold boundary delivered and the intent still wrong. The AGREE error-source read
([`docs/results/2026-09-27-slurp-agree-arm-error-sources.md`](../../results/2026-09-27-slurp-agree-arm-error-sources.md))
names the same mass by stage: CONSUMPTION-SOLVER-CHOICE 58 rows (5.37 pp) and PERCEPTION-DROP 36 (3.33 pp)
on its catch-all-first partition. The synthesis prescribes a conversion probe first (about 0.12 GPU-h),
and an arm only after it, with its expected effect declared from the probe (decision 139).

## 1. Today's order, and the one change

| block | fuser | order today (counted) | rank shown today |
| --- | --- | --- | --- |
| intent-boundaries (Perception, 8 entries) | `saea-fuse-associated-values-v1` | retrieval rank: the fuser traverses the ranked facets in order; the error-source replay reproduces the sealed block in order on 1,080 / 1,080 rows | no |
| train-exemplars (Solver, 20 entries) | `saea-fuse-supplyfilter-v1` | lexicographic value id: `rails.kb_policy._fuse_supply_filter` returns `tuple(sorted(set(selected_value_ids)))`; the sealed AGREE phases render the exemplar keys in lexicographic order on 1,080 / 1,080 rows (`roster-derivation-v1.json`, proof B) | no |

**The switch** is one new, optional `native_episode` key, absent from every committed config, so today's
behaviour is the default byte for byte:

```json
"knowledge_value_rendering": {
  "schema": "saea-knowledge-value-rendering-v1",
  "order": "retrieval-rank",
  "rank_visible": true,
  "stores": ["intent-boundaries", "train-exemplars"]
}
```

**The code change** (this branch; `rails/runner.py` and `rails/native_episode_config.py` only):

- `rails.native_episode_config.parse_knowledge_value_rendering` validates the block fail-closed (exact
  keys, schema, order, a bool `rank_visible`, distinct bound store ids; refuses a no-op block, a visible
  rank over the supplied order, and the key beside `knowledge_index`, `phase_tools` or a Solver
  supply-variant group) and `NativeEpisodeConfig.knowledge_value_rendering_json` carries it, default `None`.
- `rails.runner.order_supply_by_retrieval_rank`, called at the native episode's supply step only when the
  key is armed, re-orders each named store's `selected_value_ids` by the score of its best supporting facet
  (`rails.knowledge_index.value_retrieval_ranks`, the E21w arithmetic, unchanged), ties by value id, keeping
  the selected SET, the rank result, the supporting facets and every other store's positions.
- `rails.runner.rank_visible_value_renderer`, bound only when `rank_visible` is true, renders the same parts
  as the default path except that a value of a named store reads `[evidence <id>] retrieval rank <r>: <content>`,
  `r` its 1-based position inside that store's block. Under `retrieval-rank` that position IS the rank: the
  boundary seed already arrives in rank order and every later supply step is re-ordered before it is acquired.

The prepared-artifact identity modules (`rails.kb_policy`, `rails.knowledge_provider`, `rails.phase_supply`,
`rails.knowledge_stores`, `core.flight.runtime`) and the request-fit identity modules are **byte-unchanged**,
so merging this change does not move any ready cell's prepared supply identity (checked by grep of every
`_sha256_file(Path(<module>.__file__))` binding). Token cost: one short prefix per rendered value of the two
stores (28 per Solver request); no contact.

Tests: `tests/unit/test_knowledge_value_rendering.py` (the OFF arm re-asserts the pre-change request digests
of `test_phase_supply_repeat_visit`; eleven parser refusals; the order and renderer functions; two real
native episodes, armed with and without the visible rank) and `tests/unit/test_rankvis_config.py` (the
baseline differs from AGREE's by the one key plus bookkeeping; the key parses through the real loader;
roster, split identity and held state).

## 2. The roster

119 ids, split identity `8af458d8cfc91cb705a4891fa39245bac87c4f3b46f1931d7989bb553f78aaac`
([`roster-derivation-v1.json`](roster-derivation-v1.json), by `scripts/analysis/slurp_rankvis_probe_roster.py`):
every AGREE Fold A row whose intent is wrong while the gold boundary entry sits in the delivered eight --
CONSUMPTION-PERCEPTION-DROP 49, CONSUMPTION-SOLVER-CHOICE 69 (catch-all rows included) and the one UNPARSED
row whose gold entry was delivered. The error-source driver is imported byte-unchanged and its partition
reproduces the committed note exactly (primary 1 / 33 / 25 / 36 / 58, stage 1 / 34 / 49 / 69). The
synthesis's **89** is the pre-declared subset whose in-chain A/A answer was also wrong: 40 not delivered in
the A/A + 49 delivered in both, reproduced exactly. The other 30 are AGREE's own harms with gold still
delivered. **Selected using gold, offline**: a conditional rate on a TRAIN roster and nothing else; no
pooled or roster-level claim, and the probe cannot see harm on rows AGREE answers correctly.

**The no-op expectation.** A request-identical re-flight flips wrong rows to correct by noise: in the three
null pairs of the error-source read a wrong row with gold at position 1 re-flew correct in 12 of 31 cases,
at 2-8 in 20 of 226. On this roster (18 rows at position 1, 101 at 2-8) that is **15.9 expected no-op
conversions** (11.5 on the 89-row subset). The probe's `m` is read against this, never against zero.

## 3. Measurement and label

**`stage3_measurement`** (canonical copy in [`registered-facts-v1.json`](registered-facts-v1.json)):
`form-proof`, 119 rows, `claims_benefit` false, `expected_effect_pp` 0.0. Under the instrument's rule 5 a
batch under 200 rows is a form proof, never evidence of benefit. **Re-declaration rule, stated and not
applied:** the later 1,080-row arm with an in-chain A/A declares `(m - 15.9) x 0.0926` pp intent accuracy;
it clears the 2.5 pp bar only if `m >= 43`. The arm is **not** registered now.

**`stage3_algorithm`**: `none` -- a one-key rendering change measured on a gold-selected subset; no
rollout, scoring, credit, update or store evolution.

## 4. Budgets (CONV's arithmetic)

1,309 generation contacts (119 x 11), 5,236 FIT endpoints (x 4), 714 native task-contract calls
(119 x 6), 3,420 repeated speech seconds (ceil(310.89 x 11)), 1.5 GPU-h ceiling, one official complete
score. Expected about 598 contacts and about 0.41 GPU-h at the sealed arm's rate.

## 5. What root does next (not done here)

1. Review and merge `fable/consume` (the runner change is inert until a config arms it).
2. Countersign the three DRAFT exposure rows (`SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1`, its FIT identity,
   and the model-free roster derivation `SAEA-SLURP-MF-RANKVIS-ROSTER-DERIVATION-V1`).
3. Write the read driver and its recipe in KPROBE's shape (`scripts/analysis/slurp_kprobe_read.py`): the
   comparator is the sealed AGREE arm; the **rendering gate** refuses the read unless the flown Solver
   requests carry the rank labels and the exemplar order equals the recomputed rank order on every row;
   Wilson and Clopper-Pearson CI95; four-way transition split; the 89-row sub-read; the no-op expectation
   beside `m`.
4. Mint the admission receipt, flip with `scripts/flights/repin_cell.py --set-ready` (which mints this
   cell's own first-phase supply; `--allow-output-change` is never passed), queue behind the np4 session.

**Not authorised by this package.** No flight, no contact, no re-flight of AGREE, no Fold B / DEV / test
read, no second factor, no store rebuild, no re-pin of committed configs, no pooled claim, no admission.

| file | holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1-preregistration.md` | the preregistration and its `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact and the CANONICAL `stage3_measurement` |
| `roster-derivation-v1.json` | the 119 ids, proofs A and B, the 89-row subset, the no-op expectation |
