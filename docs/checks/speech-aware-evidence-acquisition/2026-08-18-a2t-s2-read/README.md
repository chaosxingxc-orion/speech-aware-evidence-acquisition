# P-A2T Stage-2 supply-probe registered one-shot read — archive (2026-08-18)

The single sanctioned read of the flown P-A2T Stage-2 supply probe. The pinned offline read suite
ran **exactly once**; the exposure row `SAEA-PROBE-a2t-s2-120` flipped to consumed in the same
commit, and the suite is idempotence-guarded against a second run into this directory (a
pre-existing `verdict.json` refuses the read before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944` |
| Attempt status | `COMPLETED` (`request_failures: []`, `arms: ["S1p","S2","S4","N0r"]`) |
| Rows scored | 400 = S1p 120 + S2 120 + S4 120 + N0r 40 |
| Sample set | the frozen 120-sample Stage-2 headroom list (`saea-a2t-a0-headroom-v1`) |
| Split identity | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` |
| Suite | `scripts/a2t_s2_read.py` -> `speech_aware_evidence_acquisition.analysis.a2t_s2_read` (`b062ca9`) |
| Pre-read gate | `pytest tests/unit/test_a2t_s2_read.py` 31 passed, clean tree at `b062ca9` |
| Registration | `docs/readiness/2026-08-18-pa2t-stage2-preregistration-REGISTERED.md` |
| Flight archive | `ab23d83` (flight machinery `0b91f14`, config `15bee10`) |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory. No GPU, no model contact, no installs.

## Contents

- `verdict.json` — machine-readable report (`saea-a2t-s2-read-v1`): per-arm and per-tier
  EM-conversion / tool-selection-retention / slot P-R-F1 / empty-call / parse-failure /
  induced-substitution aggregates, plus every branch clause with its own verdict and detail text.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

## Outcome

**Branch: COPY-TRAP** (+ DOSE point, secondary). Evaluated in the registered order — VOID not met
(N0r EM-flip 0/40, comparator stable on the EM axis), COPY-TRAP MET, SCHEMA-ONLY / SUPPLY-CONVERTS /
INERT not met.

Headline numbers: S1' conversion **0.1333 (16/120)** against **34** induced substitutions; S2
**0.0917 (11/120)** against the same **34**; S4 **0.0000** with retention 0.0000 and 111/120
well-formed abstentions; N0r **0.0000 (0/40)**, noise floor **0.0250**, conversion floor 0.0500. 0
harness defects, 0 registry parse warnings.

The full reading — per-arm and per-tier tables, the empty-call decomposition, the comparator-
stability finding on the selection axis, why the S4 arm cannot answer the knowledge-vs-schema
question, the DOSE point, the L5 interpretation, and the limitations — is in
**`docs/readiness/2026-08-18-a2t-s2-verdict.md`**; that document, not this README, is the verdict of
record.
