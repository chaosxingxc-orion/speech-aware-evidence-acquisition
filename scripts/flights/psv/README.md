# P-SV-1 / P-SV-2 / P-SV-3 / P-SV-4: phase-2 same-flight Perception branches on TRAIN Fold B (owner decisions 184, 186, 188, 190)

Spec: `docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-design.md` (rulings
O1-O6). Packages: `docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1/`, `...-psv2-fold-b-v1/` and
`...-psv3-fold-b-v1/`. P-SV-3 (branch `fable/psv3`) is the boundary-supply-DEPTH axis (`fuse_coverage.m` and
`fuse_coverage.top_l` raised together, 8 -> 12, c unchanged): registered separately from P-SV-1/P-SV-2, held,
no flip, no receipt, no countersign.
P-SV-4 (branch `fable/keysource`, package `docs/readiness/2026-09-30-slurp-stage3-psv4-fold-b-v1/`) is the
`key_source` axis: B (`b-k6p`) re-keys the boundary retrieval with the K6p centred centroid key and the centred Fold B
speech queries (agreement unchanged), level 2, intent primary, `claims_benefit` true at 1.1 pp; branch bounds from
`fit-measure-v2.json` (the v1 file is untouched). Registered HELD: no flip, no receipt, no countersign.

| file | role | who runs it |
|---|---|---|
| `psv_family.py` | shared identities, rosters, pins, ledger numbers | imported |
| `psv_fit_measure.py` | measures the Perception `fit_estimate` and branch bounds on the sealed AGREE arm (model-free) | registration agent |
| `derive_slurp_psv_cells.py` | derives each cell (arm + four-row smoke) from the AGREE fragments: Fold B re-target, program switch, branch block; `--cells` scopes which cell(s) a run touches (default: every cell in `psv_family.CELLS`) | registration agent |
| `write_slurp_psv_registration.py` | writes each readiness package and the DRAFT ledger rows; `--check-dir` folds a held `core.flight.cli check`; `--cells` scopes which cell(s) (default `psv1,psv2`) | registration agent |
| `psv_mint_receipt.py psv1\|psv2\|psv3\|psv4` | mints a cell's root-admission receipt (refuses P-SV-1 while the contrast-pair pin is a placeholder) | root |
| `psv_flip.sh [psv1 psv2 psv3 psv4]` | loop-form flip of the named cells (smoke, then arm), converging at ONE HEAD (default: psv1 psv2, unchanged) | root |
| `psv_repin_cell.sh` | per-cell environment for `scripts/flights/batch/repin_cell_generic.sh` (`PSV_CELL` psv1\|psv2\|psv3\|psv4) | called by the flip |
| `batch_chain_psv.sh [psv1 psv2 psv3 psv4]` | flies the named cells on slurp-np4 through the batch driver, A/A-free (the twin is the null); default: psv1 then psv2, unchanged | root / queue |
| `psv_read.sh psv1\|psv2\|psv3\|psv4 [--rescore] [--dry-run]` | the recipe-driven branch read through `scripts/analysis/slurp_perception_branch_read.py` (attempt from the recipe: seal-only for P-SV-1; `--dry-run` counts only, no gold, no scorer) | coordinator, after the seal and the READ row |
