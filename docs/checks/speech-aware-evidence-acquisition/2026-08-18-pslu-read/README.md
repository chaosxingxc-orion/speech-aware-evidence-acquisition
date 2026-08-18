# P-SLU registered one-shot read — archive (2026-08-18)

The single sanctioned read of the flown P-SLU probe. The pinned offline read suite ran **exactly
once**; the exposure row `SAEA-PROBE-pslu-n60` flipped to consumed in the same commit, and the
suite is idempotence-guarded against a second run into this directory (a pre-existing
`verdict.json` refuses the read before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T010218Z-4c97cb` |
| Attempt status | `COMPLETED` (error `None`) |
| Rows scored | 363 = 6 arms x 60 samples + 3 silence-swap |
| Suite | `scripts/pslu_read.py` -> `speech_aware_evidence_acquisition.analysis.pslu_read` (`9eccfff`, fixtures `e5547ed`) |
| Pre-read gate | `pytest tests/unit/test_pslu_read.py` 15 passed, clean tree at `e5547ed` |
| Registration | `docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md` |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-17-pslu-flight/2026-08-18-attempt4-flight-execution.md` |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory. No GPU, no model contact, no installs.

## Contents

- `verdict.json` — machine-readable report (`saea-pslu-read-v1`): per-arm aggregates, silence-swap
  comparisons, recheck/harness-defect results, and every branch clause with its own detail text.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

## Outcome

**OVERALL: UNRESOLVED — no branch rule fired.** VOID not met (0 of 3 silence-swap answers
persisted, 0 recheck mismatches, 0 harness defects); SUPPLY-CONVERTS not met on its A4 clause
(+0.1346 against a +0.01 ceiling); COPY-TRAP not met (A4 short of the half-gain threshold by
0.0062); DOSE-CONFIRM not met and directionally contradicted; INERT not met.

The full reading, every ingredient number, the void-as-flown status of the A1' arm, and the
limitations are in **`docs/readiness/2026-08-18-pslu-verdict.md`** — that document, not this
README, is the verdict of record.
