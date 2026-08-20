# P-FEW registered one-shot read — archive (2026-08-19)

The single sanctioned read of the flown P-FEW routing few-shot form probe (`SAEA-PROBE-pfew-180`).
The pinned offline read suite ran **exactly once**, exit 0; the exposure row flips to consumed in
the same commit, and the suite is idempotence-guarded against a second run into this directory (a
pre-existing `verdict.json` refuses the read before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pfew-180/attempt-20260819T233312Z-480fed` |
| Attempt status | `COMPLETED` (error `None`) |
| Rows scored | 180 = FS-NONE 60 + FS-BAL 60 + FS-SKEW 60; 180 distinct (arm, sample_id) pairs |
| Suite | `scripts/pfew_read.py` → `speech_aware_evidence_acquisition.analysis.pfew_read` (coordinator-reviewed before the read) |
| Read at study HEAD | `47eb2c1`, clean tree |
| Pre-read gate | `pytest tests/unit/test_pfew_read.py` **27 passed**; flight-archive `MANIFEST.sha256` verified (27/27 OK); ledger row `consumed = no` |
| Registration | `docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md` |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-19-pfew-flight/` |
| Verdict document | `docs/readiness/2026-08-19-pfew-verdict.md` |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory (every attempt-dir file mtime 19:33–19:39 predates the 20:39 read; post-read fingerprint
`8968b37b6ed34042210fd2ff1146bc40c592946602439250eff095916a0c1b27`). No GPU, no model contact, no
installs. `PYTHONDONTWRITEBYTECODE=1` throughout; zero `__pycache__`/`*.pyc` under the frozen
scoring package after the read.

## Outcome

**OVERALL: INCONCLUSIVE-FEW.** Reachability was published first and PASSED on both contrasts:
acc(FS-NONE) = **0.8167**, so the BAL−NONE branch had max attainable diff **+0.1833** against the
+0.10 FS-HELPS floor (headroom **+0.0833** — the ceiling case did not fire, but only by two
samples), and the NONE−SKEW branch had max attainable **+0.8167** against the +0.15 floor.

Accuracies: FS-NONE **49/60 = 0.8167**, FS-BAL **49/60 = 0.8167**, FS-SKEW **45/60 = 0.7500**.
BAL−NONE = **+0.0000**, σ̂ 0.0411, 90 % CI **[−0.0667, +0.0667]** (N = 10,000, seed 20260807).
NONE−SKEW = **+0.0667**, σ̂ 0.0323, 90 % CI **[+0.0167, +0.1167]**. FS-HELPS not met (short by
0.1000 = 6 samples). FS-INERT met on the point estimate (an exact zero) but **not** CI-gated — the
CI overhangs the ±0.05 band by 0.0167 per edge, one sample of resolution. BIAS-SENSITIVE not met on
either conjunct: degradation +0.0667 vs floor +0.15, capture 0.0339 vs floor 0.25. Mapping outcomes
`{exact: 60}` on all three arms, 180/180 non-fallback. `harness_defect_reasons` empty.

**Carry with every citation.** (1) The skew label is the **global** seeded label `audio` (drawn with
zero gold input, as the boundary requires); 1 of 60 samples has gold == `audio` and is excluded, so
the capture denominator is **59**. (2) Both counted captures are rows the **zero-demo** arm already
answered `audio` on — **incremental capture attributable to the skewed demos is 0/59**, and the
skew-label predicted marginal is unchanged at 3 → 3 → 3 across FS-NONE / FS-BAL / FS-SKEW. (3) The
FS-BAL tie is a wash, not stillness: the arms differ on 6 of 60 labels, 3 gains and 3 losses. (4) The
in-session FS-NONE comparator reads **49/60** where the cited A1′r phase-1 read **47/60** on the same
samples with a byte-identical prompt and unchanged decode config — cross-session reproduction on this
instrument is **±2 samples (±0.0333)**, larger than the primary contrast itself.

## Contents

- `verdict.json` — machine-readable report (`saea-pfew-read-v1`): per-arm accuracies, mapping-outcome
  counts, the reachability statement, the point and CI-gated verdicts with every clause detail, both
  paired bootstraps, the skew-capture accounting with its exclusion count, the 60-row three-arm
  `per_sample` table, and the harness-defect list.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed (carries the full
  per-sample table).
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

Scope: discovery-tier, n = 60 SLURP devel, single run per arm, same-distribution, K = 4 only, one
seeded skew label. SLURP audio CC BY-NC 4.0 carried on every number. Gold labels scoring-side only;
no test split was touched.
