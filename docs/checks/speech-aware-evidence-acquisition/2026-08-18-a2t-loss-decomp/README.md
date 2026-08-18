# P-A2T selection-loss decomposition -- registered model-free re-read

Schema: `saea-a2t-loss-decomp-read-v1`. Registered design: `docs/readiness/2026-08-18-a2t-loss-decomp-preregistration-REGISTERED.md`. Exposure row: `SAEA-CHECK-a2t-loss-decomp`.

Re-reads three ALREADY-CONSUMED attempts (Stage-2, Stage-2b, Stage-2c) with a NEW, narrower instrument (`analysis.a2t_loss_decomp` + this CLI) over the SAME archived `outputs.jsonl` files, hash-verified against their MANIFESTs before reading. The original one-shot reads remain consumed and their own verdicts untouched.

## Attempt dirs

- S2:  `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944`
- S2b: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-a2t-s2b-120/attempt-20260818T153859Z-8da515`
- S2c: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-a2t-s2c-120/attempt-20260818T175018Z-0d3363`
- arm plan (reused verbatim): `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944/SAEA-PROBE-a2t-s2-120.arm-plan.json`
- split identity hash: `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c`

## B2 verdict

**DRIFT-CONFIRMED** -- 3/21 of B2's losses are DRAGGED-TO-SUPPLIED.

## Files

- `verdict.json` -- machine-readable report
- `report.txt` -- human-rendered report (per-arm class tables, per-sample detail rows, the B2 verdict, the N0r reference shape, the integrity section)
- `MANIFEST.sha256` -- hashes of every file in this directory
