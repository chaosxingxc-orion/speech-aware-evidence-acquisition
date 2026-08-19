# P-TRAP registered one-shot read — archive (2026-08-19)

The single sanctioned read of the flown P-TRAP self-percept trap probe
(`SAEA-PROBE-ptrap-120`). The pinned offline read suite ran **exactly once**, exit 0; the
exposure row flips to consumed in the same commit, and the suite is idempotence-guarded
against a second run into this directory (a pre-existing `verdict.json` refuses the read
before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-ptrap-120/attempt-20260819T155046Z-98efbd` |
| Attempt status | `COMPLETED` (error `None`) |
| Rows scored | 120 = V1 self-percept 60 + V2 cross-percept 60; 120 distinct (arm, sample_id) pairs |
| Suite | `scripts/ptrap_read.py` → `speech_aware_evidence_acquisition.analysis.ptrap_read` (coordinator-reviewed before the read) |
| Read at study HEAD | `26ef46e`, clean tree |
| Pre-read gate | `pytest tests/unit/test_ptrap_read.py` **31 passed**; flight-archive `MANIFEST.sha256` verified (27/27 OK); ledger row `consumed = no` |
| Registration | `docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md` (§1–§5 design, §6 CI-gating and reachability amendment) |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-19-ptrap-flight/` |
| Verdict document | `docs/readiness/2026-08-19-ptrap-verdict.md` |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory (every attempt-dir file mtime 11:50–11:54 predates the 12:39 read; post-read
fingerprint `49a2c9a8ccec1ecb01b0ec24b2e4fd7e98b6c91a06fd098d8375a37edcefa191`). No GPU, no
model contact, no installs. `PYTHONDONTWRITEBYTECODE=1` throughout.

## Outcome

**OVERALL: ACOUSTIC-MEDIATED** (the §6 CI-gated evaluator, authoritative). Reachability was
published first and PASSED: with the run's own K distribution `{0:28, 1:18, 2:11, 3:3}` the
common denominator is **32**, max attainable rate diff **1.0000** and raw diff **32**, against
floors of +0.10 and 6 — both branches were live. Result: capture(V1) = **29/32 = 0.9062**,
capture(V2) = **0/32 = 0.0000**, rate diff **+0.9062**, raw diff **+29**, σ̂ = **0.0519**,
90 % CI **[+0.8125, +0.9688]** (N = 10,000, seed 20260807) — CI lower bound far above 0.
KEY-ONLY-MATCHING not met on both its point and CI readings. Guardrails: SLU-F1 V1 **0.5003**
(−0.0958 vs the cited consumed A3 0.5961) against V2 **0.5907** (−0.0054); induced
substitutions V1 **11** / V2 **3** (8 vs 0 on the usable 32); parse rate 1.0000 and empty rate
0.0000 on both arms; `recheck_mismatch_count` **0**; no harness defects.

**Carry with every citation**: 28 of 60 samples flew at K = 0 and are excluded from the
denominator — 5 because A0 emitted no wrong value, **23 because the fail-closed gold
zero-overlap check removed every candidate**. The usable 32 are therefore enriched for genuine
misperception, so 0.9062 is an upper-leaning estimate of a population rate. The verdict itself
survives the most adverse reweighting: scoring all 60 with zero capture assumed on every
excluded sample still gives +0.4833 / +29, clearing both floors.

## Contents

- `verdict.json` — machine-readable report (`saea-ptrap-read-v1`): capture counts and rates,
  the reachability statement, the point and CI-gated verdicts with every clause detail, the
  paired cluster bootstrap, the per-sample table, the SLU-F1/induced-substitution/parse
  guardrails, the excluded sample ids, and the harness-defect list.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

Scope: discovery-tier, n = 60 SLURP devel (32 usable), single run, same-distribution. SLURP
audio CC BY-NC 4.0 carried on every number. No test split was touched.
