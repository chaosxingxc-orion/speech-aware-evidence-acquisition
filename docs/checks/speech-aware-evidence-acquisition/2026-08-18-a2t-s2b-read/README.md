# P-A2T Stage-2b follow-up registered one-shot read — archive (2026-08-18)

The single sanctioned read of the flown P-A2T Stage-2b follow-up probe. The pinned offline read suite
ran **exactly once**; the exposure row `SAEA-PROBE-a2t-s2b-120` flipped to consumed in the same
commit, and the suite is idempotence-guarded against a second run into this directory (a pre-existing
`verdict.json` refuses the read before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2b-120/attempt-20260818T153859Z-8da515` |
| Attempt status | `COMPLETED` (`error: null`, `request_failures: []`, `arms: ["B1","B2"]`) |
| Rows scored | 240 = B1 120 + B2 120 |
| Sample set | the frozen 120-sample Stage-2 headroom list (`saea-a2t-a0-headroom-v1`) — the SAME ids Stage-2 flew |
| Split identity | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` |
| Reused Stage-2 arm plan | `runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944/SAEA-PROBE-a2t-s2-120.arm-plan.json` (verbatim; per-row `supplied_tool` cross-check proved it) |
| Suite | `scripts/a2t_s2b_read.py` -> `speech_aware_evidence_acquisition.analysis.a2t_s2b_read` (`d85a025`) |
| Pre-read gate | `pytest tests/unit/test_a2t_s2b_read.py` 21 passed, clean tree at `8380a81` |
| Registration | `docs/readiness/2026-08-18-pa2t-stage2b-preregistration-REGISTERED.md` |
| Flight archive | `8380a81` (flight machinery `5fdb919`, registration `3e91312`) |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory. No GPU, no model contact, no installs.

## Contents

- `verdict.json` — machine-readable report (`saea-a2t-s2b-read-v1`): per-arm and per-tier
  EM-conversion / tool-selection-retention / slot P-R-F1 / empty-call / parse-failure /
  induced-substitution aggregates, plus every Q-A and Q-B clause with its own verdict and detail
  text, and the independently-evaluated MISLEAD overlay.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

## Outcome

Two **independent** questions, each with its own mechanical verdict (no exclusive branch lattice):

- **Q-A — corruption-channel localization: CONFIRMED-CUT.** B1 (`argument_defaults` stripped) induced
  **2** substitutions against a ceiling of 5, and converted **0.0667 (8/120)** against a floor of
  8/120. NOT-DEFAULTS refuted (2 vs a floor of 20). Against Stage-2's S1' — same ids, same supply
  form, values included — injection falls **34 -> 2** while conversion falls 16 -> 8.
- **Q-B — schema vs knowledge: INCONCLUSIVE-B.** B2 (full 152-row registry + highlighted deranged
  row, correct tool present) converted **0.0083 (1/120)**, below both the 0.0500 SCHEMA-CONTRIBUTES
  floor and the cited 0.0250 noise floor, with **0** induced substitutions — but retention
  **0.8250** missed KNOWLEDGE-TIED's 85% clause, so the conjunction failed.
- **MISLEAD overlay: not met.** B2 retention 0.8250 >= the 0.80 ceiling; the highlighted wrong row
  did not clearly drag selection.

0 harness defects, 0 registry `argument_defaults` parse warnings. Both floors are **cited** from
Stage-2's own N0r arm (EM 0/40; 12.5% selection band), not re-measured — this probe flew no noise arm.

The full reading — per-arm and per-tier tables, the empty-call decomposition, the Q-A trade-off
analysis, why the content half of Q-B is answered decisively while only the retention guardrail is
undetermined, what Stage-2 and Stage-2b jointly establish about the signed-supply law, and the
limitations — is in **`docs/readiness/2026-08-18-a2t-s2b-verdict.md`**; that document, not this
README, is the verdict of record.
