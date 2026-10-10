# SLURP consumption module, step 7 (2026-10-09): delivery normaliser v4g as the lock-layer default

Model-free. Code and tests only: no model, server, GPU, FIT, flip, re-pin, flight or data-root contact. Authority: the
lock record `docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md` section 5 ("a separate registered step before
R5") and the NX programme row R5. Development numbers only (owner decisions 28 and 86); this note claims nothing.

## 1. What changed

- **Mechanism: a new lock id, `v2.2`** (the module's existing lock-version mechanism, migration step 6 / decision 204:
  a block's `lock` key resolved through `CarrierHooks.lock_versions`). `v2.2` = the `v2.1` layer with exactly one leaf
  moved: `native_episode.deliver_normaliser.normaliser` `saea-deliver-normalise-v3` -> `saea-deliver-normalise-v4g`
  (version `1`; guards `ti-expressible` 100 and `ee-wilson` 0.10 / z 1.959963984540054; tables loaded by hash by
  `rails/delivery_normalisers.py`). The lock-layer component record is `delivery-normaliser`, state `on (lock)`, record =
  the lock note (`slurp_module_lock_v2_2.LOCK_V2_2_COMPONENT_STATES`).
- **Opt-in by lock id.** A block naming no `lock`, `v2.0` or `v2.1` compiles to the same bytes as before (v3).
  At step 7, `CURRENT_LOCK` stayed `v2.1`: moving it changes what `harness_admission_check` requires of every module
  OFF arm and what `derive_slurp_module_*` scripts emit, which is a registration decision, not this step.
  **Update 2026-10-10 (owner decision 249): `CURRENT_LOCK` is now `v2.2`** (`slurp_module_hooks.CURRENT_LOCK =
  slurp_module_lock_v2_2.LOCK_V2_2`; R5 read NEUTRAL = an efficiency result with no harm, and the v4g delivered gain is
  locked). A block's `lock` key still selects the layer; no committed config relies on the default (all 1,070 SLURP
  `consumption_module` blocks name `v2.1` or `v2.2`), so no registered cell compiles differently. What `CURRENT_LOCK`
  governs: the OFF arm of the harness `module` class (rule 8), and the lock the `derive_slurp_module_comp1bdev_cells.py`
  and `derive_slurp_nx_r1_cells.py` writers emit for NEW derivations. The registered PENDING `module` entry in
  `docs/receipts/harness-admission.json` stays on `v2.1` (its cell flew there) and carries
  `switch.lock_superseded_by: "v2.2"`; the gate accepts that marker only on a PENDING entry naming the CURRENT lock.
- **New hook** `CarrierHooks.lock_deliver_normalisers` (`{lock: callable -> normaliser id}`): the compiler checks the
  layer's deliver leaf against the lock's own normaliser (v3 for v2.0/v2.1/no lock; v4g for v2.2), still fail-closed.
  `default_deliver_normaliser()` is unchanged (v3). Other carriers leave the hook `None`.
- **Composition limits under v2.2.** The `scope-rule` stage has no registered composition with v4g, and the
  `solver-citation-contract` component would overwrite the leaf with the cited-v3 normaliser; the compiler refuses both
  on a lock whose normaliser is not the carrier's default ("no registered composition"). The COMP-1b-style composed
  cells (citation contract) therefore stay on v2.1.
- Files: `rails/adapters/slurp_module_lock_v2_2.py` (new; constants, per-lock default, layer builder),
  `rails/adapters/slurp_module_hooks.py` (wires v2.2; kept at 260 lines, the adapter line budget),
  `rails/consumption_module.py` (the hook and the per-lock check), tests `tests/unit/test_consumption_module_step7.py`
  and the carrier-transfer hook table.

## 2. Proofs

- Composed config hashes of the three registered module / NX cells (arm and smoke), before and after: identical
  (pinned in `test_consumption_module_step7.py::COMPOSED_HASHES_BEFORE`). Cells: `slurp-native-stage3-module-comp1b-dev2000-added-v1`
  (HELD), `slurp-native-stage3-nx-r1-solver-fold-b-v1`, `slurp-native-stage3-nx-r1-i2-solver-fold-b-v1`. They name
  `lock: v2.1` and v3 literally in their baseline fragments, so they are unaffected.
- `scripts/analysis/module_equivalence_proof.py --at all` (includes `a2t0`, `e210`, the M-series and AT-M6): output
  byte-identical before and after; `ok: true` for the Audio2Tool and Earnings 21 / 22 all-off proofs.
- Unaffected: every cell registered or flown on v2.0 / v2.1 (A2, G5, P-SV, COMP-1b, R1, R1 iteration 2); the
  Audio2Tool, Earnings 21 and Earnings 22 carrier hooks.

## 3. What the R5 composed cell must declare

1. `consumption_module.lock = "v2.2"` in the block, and its in-chain module-all-off A/A on the same lock (a composed
   read never mixes normalisers: a cell reads against an A/A on its own normaliser).
2. (Resolved 2026-10-10, decision 249: `CURRENT_LOCK` is `v2.2`.) The harness `module` class OFF arm and
   `harness_admission_check` require the OFF arm to name the carrier's CURRENT lock, so an R5 `module`-class entry now
   names `v2.2` and needs a falsifier cell that carries the v2.2 bytes (none is registered today: R5/R6 are review-off).
3. No `scope-rule` or `solver-citation-contract` component on that block (refused on v2.2; compose them offline as
   columns, or register a composition first).
4. A baseline fragment whose `native_episode.deliver_normaliser.normaliser` is `saea-deliver-normalise-v4g` (the
   compiled v2.2 layer, proven by `module_equivalence_proof.py` for the new cell) and the usual re-proof of AT-M0 on
   the new request/delivery bytes.
