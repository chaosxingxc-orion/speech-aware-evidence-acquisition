# P-SV-1 / P-SV-2: phase-2 same-flight Perception branches on TRAIN Fold B (owner decisions 184, 186, 188)

Spec: `docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-design.md` (rulings
O1-O6). Packages: `docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1/` and `...-psv2-fold-b-v1/`.

| file | role | who runs it |
|---|---|---|
| `psv_family.py` | shared identities, rosters, pins, ledger numbers | imported |
| `psv_fit_measure.py` | measures the Perception `fit_estimate` and branch bounds on the sealed AGREE arm (model-free) | registration agent |
| `derive_slurp_psv_cells.py` | derives both cells (arm + four-row smoke) from the AGREE fragments: Fold B re-target, program switch, branch block | registration agent |
| `write_slurp_psv_registration.py` | writes each readiness package and the DRAFT ledger rows; `--check-dir` folds a held `core.flight.cli check` | registration agent |
| `psv_mint_receipt.py psv1\|psv2` | mints a cell's root-admission receipt (refuses P-SV-1 while the contrast-pair pin is a placeholder) | root |
| `psv_flip.sh [psv1 psv2]` | loop-form flip of both cells (smoke, then arm), converging at ONE HEAD | root |
| `psv_repin_cell.sh` | per-cell environment for `scripts/flights/batch/repin_cell_generic.sh` | called by the flip |
| `batch_chain_psv.sh [psv1 psv2]` | flies P-SV-1 then P-SV-2 on slurp-np4 through the batch driver, A/A-free (the twin is the null) | root / queue |
| `psv_read.sh psv1\|psv2` | the branch read through `scripts/analysis/slurp_perception_branch_read.py` (refuses until it lands) | coordinator, after the seal and the READ row |
