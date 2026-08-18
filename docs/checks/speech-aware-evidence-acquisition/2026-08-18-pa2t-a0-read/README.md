# P-A2T Stage-1 A0 registered one-shot read — archive (2026-08-18)

The single sanctioned read of the flown P-A2T Stage-1 A0 zero-supply baseline. The pinned offline
read suite ran **exactly once**; the exposure row `SAEA-BASE-a2t-a0-400` flipped to consumed in the
same commit, and the suite is idempotence-guarded against a second run into this directory (a
pre-existing `verdict.json` refuses the read before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-BASE-a2t-a0-400/attempt-20260818T055500Z-res315` |
| Attempt status | `COMPLETED` (error `None`, `request_failures: []`) |
| Rows scored | 400 = 8 tiers x 50, frozen Audio2Tool discovery split, seed 20260807 |
| Split identity | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` |
| Suite | `scripts/a2t_read.py` -> `speech_aware_evidence_acquisition.analysis.a2t_read` (`ae4d71d`) |
| Pre-read gate | `pytest tests/unit/test_a2t_read.py` 18 passed, clean tree at `ae4d71d` |
| Restructure basis | `docs/readiness/2026-08-17-pa2t-preregistration-draft.md` section 8 item 4 |
| Binding table | `configs/probes/g0-binding/pa2t-binding.json` |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory. No GPU, no model contact, no installs.

## Contents

- `verdict.json` — machine-readable report (`saea-a2t-a0-read-v1`): overall and per-tier
  tool-accuracy / exact-match / gap / empty-tool-call counts, the headroom sample ids, and the
  recheck results.
- `headroom.json` — standalone Stage-2 headroom list (`saea-a2t-a0-headroom-v1`), 120 sample ids
  meeting `tool_accuracy == 1.0 AND exact_match == 0.0`; seeds the Stage-2 supply-probe
  registration.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

## Outcome

**Overall: tool-acc 0.5425, EM 0.2425, gap +0.3000 on n=400** (217 tool-correct, 97 exact, 120
headroom). This replaces the retired, unsourced 84.6% / 15.6% premise. 0 recheck mismatches, 0
harness defects, empty tool-call rate 41/400.

The full reading — the per-tier 8x50 table, the empty-tool-call decomposition, the Stage-2 headroom
distribution, the L5 supply-benefit interpretation, and the limitations — is in
**`docs/readiness/2026-08-18-pa2t-a0-verdict.md`**; that document, not this README, is the verdict
of record.
