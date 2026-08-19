# P-KEY successor registered one-shot read — archive (2026-08-19)

The single sanctioned read of the flown P-KEY modality × supply factorial
(`SAEA-PROBE-pkey2-338`). The pinned offline read suite ran **exactly once**, exit 0; the
exposure row flips to consumed in the same commit, and the suite is idempotence-guarded
against a second run into this directory (a pre-existing `verdict.json` refuses the read
before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/attempt-20260819T111032Z-3109e8` |
| Attempt status | `COMPLETED` (error `None`) |
| Rows scored | 338 = T0 60 + AUD-NOSUP 60 + AUD-SUP 60 (+3 silence-swap) + TXT-NOSUP 60 + TXT-SUP 60 + TXT-NOSUP duplicate sub-block 35 |
| Suite | `scripts/pkey_read.py` → `speech_aware_evidence_acquisition.analysis.pkey_read` (built at `01583dc`, coordinator-reviewed) |
| Read at study HEAD | `dbe3503`, clean tree |
| Pre-read gate | `pytest tests/unit/test_pkey_read.py tests/unit/test_bootstrap.py` **69 passed**; flight-archive `MANIFEST.sha256` verified (30/30 OK); P-PHON cross-reference archive `MANIFEST.sha256` verified (3/3 OK) |
| Registration | `docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md` (§1–§7 design, §7 and §8 amendments) |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-19-pkey2-flight/` |
| Verdict document | `docs/readiness/2026-08-19-pkey2-verdict.md` |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory (pre-read and post-read directory fingerprints identical: `24e961b2…`). No GPU, no
model contact, no installs. `PYTHONDONTWRITEBYTECODE=1` throughout.

## Outcome

**OVERALL: INCONCLUSIVE-KEY** (CI-gated, the 2026-08-19 amendment's authoritative verdict).
Reachability PASSED first: max attainable |I| = 4/60 = **0.0667** ≥ the +0.06
SPEECH-TERM-PRESENT floor, so the affirmative branch was reachable and KEY-ONLY was legally
available as an affirmative negative. It did not fire: I = **+0.0463**, σ̂(I) = **0.0306**,
90 % CI **[−0.0033, +0.0970]** — the CI overhangs the equivalence band on the high side, and
the point estimate itself sits in the registered dead zone between the 0.03 KEY-ONLY ceiling
and the +0.06 SPEECH-TERM-PRESENT floor. VOID not met on all six clauses.

## Contents

- `verdict.json` — machine-readable report (`saea-pkey-read-v1`): per-arm aggregates, the
  reachability statement, the point and CI-gated interaction verdicts with every clause
  detail, the bootstrap, the duplicate-block floor, the converted-set difference, T0-vs-gold
  WER, silence-swap comparisons, and every VOID clause.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

Scope: discovery-tier, n = 60 SLURP devel, single run, same-distribution. SLURP audio
CC BY-NC 4.0 carried on every audio-derived number. No test split was touched.
