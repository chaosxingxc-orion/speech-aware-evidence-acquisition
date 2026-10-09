# NX post-processing v4g: registration and the apply driver (v1)

Date: 2026-10-09. Branch `fable/nx-v4g`. Model-free: no model, server, tokenizer, encoder, embedder, GPU, network or
paid-API contact. One registered-scorer run per derived column copy (section 5). No cell, fragment, lock or config is
touched; Fold B and any run that does not yet exist were not read.

## 1. What v4g is

`saea-deliver-normalise-v4g` (version `1`, rule id `slurp-use-projection-v4g`, class
`rails.delivery_normalisers.SlurpProjectionV4GuardedDeliveryNormaliser`, a subclass of the v4 class) is
`saea-deliver-normalise-v4` with two TRAIN-only guards, the guarded set of
`docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md`. The stage order is unchanged
(`fx-article`, `fx-oclock`, `scope`, `ti1`, `ee10`) and v4 itself is untouched (`guards` is `None` for v4; its id,
version, rule id and receipt are byte-identical to before).

| Guard | Rule in v4 | Rule in v4g | Pinned constants |
|---|---|---|---|
| ti-expressible | ti1 drops an entity whose slot type is in < 1 % of the delivered intent's pool exemplars | ti1 fires only on an intent with >= 100 pool exemplars (below that, "< 1 %" is not distinguishable from "never seen") | `V4G_GUARDS.ti1_min_exemplars = round(1 / V4_TI_MIN_SHARE) = 100` |
| ee-wilson | ee10 empties a row whose intent's pool entity-carrying rate is < 0.10 | ee10 fires only when the Wilson score 95 % UPPER bound of that rate is < 0.10 | `ee_wilson_max_upper = 0.10`, `ee_wilson_z = 1.959963984540054` |

The constants live in code (`V4G_GUARDS`, `V4G_WILSON_Z`) and are echoed in every row receipt under `guards`
(`{"ti-expressible": {"ti1_min_pool_exemplars": 100}, "ee-wilson": {"max_upper_bound": 0.1, "z": 1.959963984540054,
"interval": "wilson-score-upper"}}`), beside `stats_tables`, `stats_sha256` and `table_sha256`. A change to a guard
constant bumps `DELIVER_NORMALISE_V4G_VERSION`. The registered id resolves in `core.base.DELIVERY_NORMALISERS` beside
v4; `tests/unit/test_deliver_normaliser_v4g.py::test_v4g_is_registered_but_armed_by_no_config_fragment_or_lock` asserts
that no file under `configs/` names it.

## 2. Table pins (no new table)

The Wilson bound needs each intent's pool exemplar count and entity-carrying count. The pinned
`intent-entity-rate-v1.json` already carries both (`intent_n`, `intent_with_entities`; they are what v4's
`entity_rate` divides), so NO `-v2` table was built, the builder was not re-run for writing, and the v1 tables are
untouched. v4g loads the same four tables as v4, by hash:

| Table | sha256 |
|---|---|
| `article-strip-v1.json` | `db42bf10a08ae9ccc51c656fd5cbbf8a636ee88a12b4c37100b5d69cf4d51b79` |
| `oclock-v1.json` | `36779d582b0da541f55b90d3dcfc55ef7d3cfd6c4e3dfbec402daec5226399c7` |
| `type-by-intent-v1.json` | `41a57d45bc434a3e42f3950590985d86f8598c38fdd8aba443d161c57059329d` |
| `intent-entity-rate-v1.json` | `bd43804dd23868d2e4d6531f2ff305c1b0fd7a3a96cef4afaa28ab63793fac59` |

Loaded statistics digest `01e6a019c91f52bcd2941f593cfec9e8db120543334d46b9e643c29e4023f223`. Registration receipt:
`docs/receipts/knowledge/slurp-v4g-registration-v1.json` (`stats_tables`, `guards`, `new_tables: []`, `armed_by: []`);
a unit test asserts it agrees with the code constants.

## 3. A2 reproduction (sealed pool `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1`, 1,000 rows, 913 utterance clusters)

Both columns are produced by the registered ids through the shared replay row, then scored by the registered scorer
`slurp-slu-official` on a derived copy (port/official identity check passed; scorer pooled SLU-F1 equals
the in-process arithmetic to 1e-6). Paired delta vs the sealed delivered column (SLU-F1 65.9327), whole-utterance
cluster bootstrap, 10,000 draws, seed 20260915. Intent delta 0.0 for both.

| Column | Rows edited | Delta SLU-F1 (pp) | CI95 | Registered scorer SLU-F1 | Column copy sha256 |
|---|---|---|---|---|---|
| `--apply v4` | 124 | +0.9771 | [+0.2116, +1.7443] | 66.9098 | `2104239a2aa51ee949036a20295f4754ca12793202dcda362374adf8758b14d6` (equals the R0.4 v4 column copy) |
| `--apply v4g` | 115 | +0.9761 | [+0.2453, +1.7120] | 66.9088 | `6e50951c3486a77c491da551b6b9cfeffa691b24c216eb2f1d734561601903f2` |

The v4g row equals the attribution note's `guards['ti-expressible + ee-wilson']` entry of the report pinned by hash
`f5e486a814a33398bce8969fac653b0488dae5bcc25e35f9ae9ba24411d950c0` (`delta_slu_pp` 0.9761, `ci95_slu_pp`
[0.2453, 1.712], `delta_span_pp` 2.0143, `left` 65.9327, `right` 66.9088). Byte for byte:
`test_the_registered_v4g_path_reproduces_the_attribution_notes_guarded_a2_column` (data-gated) renders, for every
row, the text of the attribution driver's own guarded recompute and compares it with the registered v4g output
(0 mismatches over 1,000 rows, 115 rows edited, every receipt carrying the pinned `stats_tables` and `guards`).

## 4. The apply driver

`scripts/analysis/slurp_nx_postproc_v4_apply.py` (a sibling of the search driver, which it imports for the gold
loader, the official count arithmetic and the bootstrap; it contains no rule logic).

```
cd /home/chao/saea-worktrees/fable-nx-v4g && source ~/.venvs/speechrl/bin/activate
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data PYTHONDONTWRITEBYTECODE=1
python -B scripts/analysis/slurp_nx_postproc_v4_apply.py --apply {v4,v4g} --pool <run id>/<attempt> [--column <arm id>]
```

* `--pool` is a sealed run under `$SPEECHRL_DATA_DIR/runs/` (aliases `a2`, `fold-a` also resolve). The scorer and
  split are read from the run's `scores.json` (exactly one SLURP scorer block, from an allow-list of devel/train
  scorers).
* Without `--column`: the delivered answers of the run, proved row by row against the sealed official per-sample
  fields before any edit. With `--column <arm id>`: the RAW first-visit Solver answer of that arm of a same-flight
  node-template group (E1 receipt `saea-supply-variant-arms-v4`), loaded through the E2 reader
  (`slurp_nx_solver_column_read.load_sealed_arm_texts` over a verified bundle). The registered normaliser then runs on
  the raw answer (v3 first, as in a delivery node), and the unmodified column is the raw arm answer; both copies are
  scored by the registered scorer. The `--column` path is covered by the shared code path only and has not been run:
  no sealed run carries a template group yet.
* Path: `DELIVERY_NORMALISERS.resolve(<registered id>)` through `analysis.deliver_normaliser_replay.replay_row`.
* Output under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1/apply-<v4|v4g>-<run id>[-<arm>]/`:
  `report.json` (ids, counts, pp, per-scenario table, scorer runs with the copy sha256 and the result sha256),
  the derived column copy (answer text, never in the repository). Reports are write-once.
* Refusals: scorer outside the devel/train allow-list (the test split); any row whose utterance is in the TRAIN
  Fold B roster; labels `select-a2`, `confirm-*` (the search driver's reports; the search driver's own
  `confirm-fold-a` write-once refusal is untouched); an existing report (identical bytes only with
  `--allow-rewrite-identical`); a normaliser that moves an intent label. Unit tests:
  `tests/unit/test_slurp_nx_postproc_v4_apply.py`.

## 5. Scorer runs recorded in the analysis root

Both A2 runs, in `apply-v4-SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1/` and `apply-v4g-...`, one registered-scorer run
each (copy hashes in section 3). No scorer run happened on any other pool.

## 6. What is NOT done

* No cell, fragment, lock or config names v4 or v4g; which cells use v4g is the owner's lock decision.
* No Fold B read and no read of any run that does not yet exist (the R1 delivering-arm confirmation of v4g is a later
  offline step through `--apply v4g --pool <R1 run>/<attempt>`).
* The `--column` mode is untested on a real sealed template run.
* Guard constants are not tuned: they are the attribution note's TRAIN-only values. The A2 selection pool is the
  pool the guards were chosen against, so the A2 numbers are descriptive, not a confirmation.
