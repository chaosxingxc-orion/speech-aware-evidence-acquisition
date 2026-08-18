# P-SLU Stage-2 registered one-shot read — archive (2026-08-18)

The single sanctioned read of the flown P-SLU Stage-2 follow-up probe. The pinned offline read
suite ran **exactly once**; the exposure row `SAEA-PROBE-pslu-s2-183` flipped to consumed in the
same commit, and the suite is idempotence-guarded against a second run into this directory (a
pre-existing `verdict.json` refuses the read before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-s2-183/attempt-20260818T200339Z-80119a` |
| Attempt status | `COMPLETED` (error `None`) |
| Rows scored | 183 = F1 60 + A1r-phase1 60 + A1'r 60 + 3 silence-swap |
| Suite | `scripts/pslu_s2_read.py` -> `speech_aware_evidence_acquisition.analysis.pslu_s2_read` (study HEAD `5699ab8`) |
| Pre-read gate | `pytest tests/unit/test_pslu_s2_read.py` 22 passed, clean tree at `5699ab8`, flight-archive MANIFEST sha256-verified |
| Registration | `docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md` |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-18-pslu-s2-flight/` |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory. No GPU, no model contact, no installs. A0/A2/A3/A4 comparators are CITED from the
consumed parent read (`d8b71a5`), never re-flown.

## Contents

- `verdict.json` — machine-readable report (`saea-pslu-s2-read-v1`): per-arm aggregates,
  supplied-item audit, phase-1 mapping summary, silence-swap comparisons, recheck/harness-defect
  results, and every Q-A/Q-B/VOID clause with its own detail text.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

## Outcome

**Q-A: KNOWLEDGE-BEYOND-FORMAT** — the format-matched filler control gained nothing (F1 SLU-F1
0.1356, −0.0385 vs the cited A0; FORMAT-FLOOR-CONFIRMED missed its +0.1046 floor by 0.1431) while
the cited A3 sits +0.4605 above it (floor 0.10). **Q-B: SELF-SCOPING-WORKS** — non-fallback 60/60
(floor 50) and A1'r 0.6093 SLU-F1, gain +0.4352 vs the cited A0 (floor +0.2646). VOID not met
(0 of 3 silence-swap answers persisted, 0 recheck mismatches, 0 harness defects).

The full reading, every ingredient number, the phase-1 mapping detail, the L3 anchor restatement,
and the limitations are in **`docs/readiness/2026-08-18-pslu-s2-verdict.md`** — that document,
not this README, is the verdict of record.
