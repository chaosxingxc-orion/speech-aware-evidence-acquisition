# P-PHON failure-class decomposition -- registered model-free re-read

Schema: `saea-pphon-decomp-read-v1`. Registered design: `docs/readiness/2026-08-18-pphon-preregistration-REGISTERED.md`. Exposure row: `SAEA-CHECK-pphon-decomp`.

Re-reads five ALREADY-CONSUMED attempts (pslu_read, pslu_s2_read, a2t_read, a2t_s2b_read, a2t_s2c_read) with a NEW, narrower instrument (`analysis.pphon_decomp` + this CLI) over the SAME archived `outputs.jsonl` files, hash-verified against their MANIFESTs before reading. The original one-shot reads remain consumed and their own verdicts untouched.

## Attempt dirs

- pslu (A0+A3): `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-pslu-n60/attempt-20260818T010218Z-4c97cb`
- pslu-s2 (A1'r): `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-pslu-s2-183/attempt-20260818T200339Z-80119a`
- a2t (A0): `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-BASE-a2t-a0-400/attempt-20260818T055500Z-res315`
- a2t-s2b (B1): `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-a2t-s2b-120/attempt-20260818T153859Z-8da515`
- a2t-s2c (C1/C2): `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-a2t-s2c-120/attempt-20260818T175018Z-0d3363`
- arm plan (reused verbatim): `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944/SAEA-PROBE-a2t-s2-120.arm-plan.json`

## SLURP-A3 verdict (primary)

**MIXED**

## A1'r concordance

**CONCORDANT** -- A3 (primary): overall='MIXED', speech_snap_present=False, format_dominant=False; A1'r (secondary): overall='MIXED', speech_snap_present=False, format_dominant=False

## Files

- `verdict.json` -- machine-readable report
- `report.txt` -- human-rendered report (per-class tables, verdicts, concordance, reconciliation, integrity section)
- `MANIFEST.sha256` -- hashes of every file in this directory
