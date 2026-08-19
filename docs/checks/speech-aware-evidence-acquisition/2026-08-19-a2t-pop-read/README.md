# V4 whole-population regression arm registered one-shot read — archive (2026-08-19)

The single sanctioned read of the flown whole-population regression arm
(`SAEA-PROBE-a2t-pop-194`). The pinned offline read suite ran **exactly once**, exit 0; the
exposure row flips to consumed in the same commit, and the suite is idempotence-guarded against a
second run into this directory (a pre-existing `verdict.json` refuses the read before any work
happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-pop-194/attempt-20260819T162625Z-b3257c` |
| Attempt status | `COMPLETED` (error `None`) |
| Rows scored | 194 = R0 97 + R1 97; 194 distinct (arm, sample_id) pairs |
| Suite | `python -m speech_aware_evidence_acquisition.analysis.a2t_pop_read` (coordinator-reviewed before the read) |
| Read at study HEAD | `b5b7f7c`, clean tree |
| Pre-read gate | `pytest tests/unit/test_a2t_pop_read.py` **29 passed**; flight-archive `MANIFEST.sha256` verified (22/22 OK); ledger row `consumed = no` |
| Registration | `docs/readiness/2026-08-19-a2t-pop-preregistration-REGISTERED.md` |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-19-a2t-pop-flight/` |
| Verdict document | `docs/readiness/2026-08-19-a2t-pop-verdict.md` (carries the five-probe synthesis appendix) |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory (fingerprint `252c8cbd10ccdc906b7654b708df618c8ccd5793ba1eb3b45ac4a59e50cda582` identical
before and after). No GPU, no model contact, no installs. `PYTHONDONTWRITEBYTECODE=1` throughout.

## Outcome

**OVERALL: REGRESSION-COSTLY.** The mandatory R0-stability statement was published first and is
perfect: the zero-supply re-fly, byte-identical to A0's own request, returned **0/97 EM
regressions**, retention 1.0000, slot F1 1.0000, empty and parse-failure rates 0.0000 — this
population's first EM-stability measurement, so every R1 regression is supply-attributable and σ̂
below is between-sample variance alone.

R1 (B1-form values-stripped self-supplied row, **replacing** the 152-row registry) regressed
**36/97 = 0.3711**. **Δreg = +36**, σ̂ = **4.7616**, 90 % CI **[+28, +44]** (N = 10,000, seed
20260807). REGRESSION-SAFE fails on both conjuncts (Δreg exceeds the ≤2 ceiling by 34; CI upper +44
exceeds the ≤5 ceiling by 39); REGRESSION-COSTLY clears its ≥6 floor by **+30**, and the CI's
lower bound alone clears it by +22.

**Induced substitutions are 0 on both arms** against the full-152-row-registry default-value
yardstick (`registry_defaults_parse_warnings` empty) — a genuine empirical zero, so the 36
regressions are **not** value injections. Decomposition: 7 samples lost tool selection (empty /
unparseable; the empty-call rate, parse-failure rate and retention loss all equal 7/97), and **29
of the 90 samples that kept the correct tool still failed EM on arguments**. Damage concentrates
where arguments matter: tier5_needle 9/15, tier7_multiturn 10/22, tier2_parametric 7/19, while
tier1_direct (0/6) and tier3_multi_intent (0/2) are untouched.

**Whole-population signed account** (published as the measured magnitude of the negative term; the
registration attached the *citable net account* to the SAFE branch, which did not fire): cited
conversions **+[8,10]/120** on the disjoint headroom set (+8/120 for the matched B1 rendering)
against **−36/97** measured here gives **−26 to −28 EM samples** over the **217** ids where an
EM-signed rule is defined. **183 of the frozen 400 are excluded** — EM cannot regress there and no
gold-free supply-row rule exists for them — which is 45.75 % of the split and must be disclosed on
every citation. Applied blindly, the clean form breaks 3.6–4.5 answers for every one it fixes.
Unlike the C2 conversions-vs-injections ratio, this is a legitimate signed sum: one unit, one
frozen scorer, disjoint populations partitioning the defined set.

## Contents

- `verdict.json` — machine-readable report (`saea-a2t-pop-read-v1`): per-arm and per-tier
  aggregates, the reachability/R0-stability statement, the paired bootstrap, and both verdict
  clauses with detail.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

Scope: discovery-tier, n = 97, single run, one carrier, the EM-regression-eligible population only.
Audio2Tool CC BY-NC 4.0 carried. No test split was touched.
