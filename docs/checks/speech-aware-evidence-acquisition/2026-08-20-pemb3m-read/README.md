# P-EMB-3M registered one-shot read — archive (2026-08-20)

The single sanctioned read of the flown P-EMB-3M dedicated-embedder multi-model routing comparison
(`SAEA-PROBE-pemb3m-388`). The pinned offline read suite ran **exactly once**, exit 0; the exposure
row flips to consumed in the same commit, and the suite is idempotence-guarded against a second run
into this directory.

## What was read

| | |
|---|---|
| Sweep | 234/234 scored embedding contacts across the three flyable arms, finalized attempt `attempt-20260820T112943Z-410bdb` (241 calls incl. 7 gate contacts) |
| Attempt status | durable state `FINALIZED` |
| Vectors read | `derived/embeddings/SAEA-PROBE-pemb3m-388/<arm>/manifest.json` for M1 (dim 2048, 78 entries), M2 (dim 1024, 78) and M4 (dim 1024, 78 + 2 jitter). M3 has no manifest — never flown |
| Suite | `speech_aware_evidence_acquisition.analysis.pemb3m_read` (built and coordinator-reviewed before the read, flown UNMODIFIED) |
| Read at study HEAD | `8695525`, clean tree |
| Pre-read gate | `pytest tests/unit/test_pemb3m_read.py tests/unit/test_pemb3m_flight.py` **106 passed**; flight-archive `MANIFEST.sha256` verified **32/32 OK**; ledger row `consumed = no` |
| Registration | `docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md` (§4 verdict rules, §6 discipline) |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3m-flight/` |
| Verdict document | `docs/readiness/2026-08-20-pemb3m-verdict.md` |

Model-free and read-only: the suite never opens a model session, never mutates an attempt directory
or a vector manifest, and consumes only the derived per-arm vector manifests plus scoring-side-only
gold. No GPU, no model contact, no installs. `PYTHONDONTWRITEBYTECODE=1` throughout.

## Two report pairs, and which one governs

The shipped suite ships **no `__main__` guard and no `scripts/pemb3m_read.py` wrapper** (every
sibling read has one), so it was invoked as `main(["--output-dir", <this dir>])` from a scratchpad
driver against `PYTHONPATH=<repo>/src`. The suite source was not modified.

The shipped `main()` **hardcodes `pooling_override_present=False`**, labels any arm whose manifest is
missing `DROPPED-DEPS`, and supplies no jitter pair. The flight's actual gate outcomes are the
opposite on two of those three points. Rather than edit the pinned suite, the read was performed
twice over the same inputs:

| files | inputs | M1 label |
|---|---|---|
| `verdict.json` + `report.txt` | the shipped `main()` **exactly as shipped** | `EMB-WEAK` |
| `verdict-flight-facts.json` + `report-flight-facts.txt` | the SAME shipped pure functions (`build_pemb3m_sweep_report`) driven with the flight's real gate outcomes — `pooling_override_present=True`, M3 `DROPPED-RUNTIME-ERROR`, M4 jitter pair supplied | **`EMB-WEAK-SCOPED`** |

**`verdict-flight-facts.json` is the governing artifact**, because registration §4 makes the scoped
name fire exactly when gate (a) recorded `POOLING-OVERRIDE-PRESENT` — which it did. Every accuracy,
confusion table, attractor structure, cross-arm agreement and cosine profile is **identical** between
the two files; they differ only in the M1 verdict string, the M3 status label, and the presence of
the jitter evaluation. The hardcoded `False` is an instrument defect recorded here for audit, not a
finding.

## Outcome

**OVERALL: EMB-WEAK-SCOPED + CASCADE-ROUTES** — the dedicated AUDIO embedder fails on this stack
(scoped, not a model-level refutation), while the TEXT-ONLY cascade reaches the routing tier.

| arm | model | accuracy | labels ever predicted | mean top-1 cosine | verdict |
|---|---|---|---|---|---|
| M1 PRIMARY | `lco-embedding-omni-3b-gguf` | **3 / 60 = 0.0500** | 5 / 18 (`recommendation` 36) | +0.0707 | **EMB-WEAK-SCOPED** |
| M2 CONTROL (audio-TYPE) | `glap` | **8 / 60 = 0.1333** | 16 / 18 (`iot` 11) | +0.0223 | control, no clause |
| M3 CONTROL (speaking-STYLE) | `clsp` | **not flown** | — | — | **DROPPED-RUNTIME-ERROR** |
| M4 CASCADE | T0 transcript → `qwen3-embedding-0.6b-gguf` | **45 / 60 = 0.7500** | 17 / 18 (`play` 10) | **+0.6030** | **CASCADE-ROUTES** |

**CONTROL-ANOMALY: NOT FIRED** — max(M2,M3) = 0.1333 vs max(M1,M4) = 0.7500, floor 0.30; both
conditions fail. **Evaluated against GLAP alone**: M3 never flew, so the speaking-STYLE confound went
untested and this must be cited with that scope.

**Carry with every citation.** (1) M4's 0.7500 sits **2 samples below A1′r (0.7833) and 4 below
FS-NONE (0.8167)**, and **+40.683 above the expectation of re-pairing its own predictions at
random**. (2) M4's argmax is jitter-robust: the repeat pair clears the declared ≥ 0.9999 tolerance
(0.9999006) but its **argmax is NOT stable** — on a semantically null synthetic string whose own
top-1/top-2 margin is 0.000485; under the adversarial 2δ bound (δ = 0.014097) at most 5 correct
scored predictions could flip, leaving **40/60 = 0.6667, still above the 0.65 floor**. (3) M1
reproduces the attractor pathology (60 % of mass on `recommendation`, `calendar` never predicted,
60/60 near-orthogonal positive cosines in a 0.0401–0.1077 band, median top-1/top-2 margin 0.00737)
and sits **below uniform chance** and below its own shuffle expectation (3 observed vs 3.283).
(4) M2 GLAP is the secondary finding: 0.1333 with **16/18 labels** reachable and **+4.750 above its
own shuffle expectation** — the first audio-side arm in the program to beat that baseline, though it
is a control and far under the 0.30 floor. (5) Cross-arm agreement is near-nil (M1↔M2 1/60,
M1↔M4 3/60, M2↔M4 11/60); only 2 samples M4 misses are recovered by either audio arm.

## Contents

- `verdict.json` — machine-readable report (`saea-pemb3m-read-v1`) from the shipped `main()` exactly
  as shipped: per-arm accuracy, verdict and detail, per-arm confusion tables, attractor structure,
  the 60-row `predictions` table per arm (sample_id, gold, predicted, top-1 cosine, correctness),
  cross-arm agreement and cosine-sign profiles.
- `report.txt` — that run's rendered human-readable report, verbatim as printed.
- `verdict-flight-facts.json` — **the governing report**: the same schema and the same numbers, with
  the flight's real gate outcomes applied (scoped M1 name, `DROPPED-RUNTIME-ERROR`, jitter
  evaluation) plus a `flight_facts_applied` block recording exactly what differed and why.
- `report-flight-facts.txt` — its rendered report.
- `README.md` — this file.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

Scope: discovery-tier, n = 60 SLURP devel, 18 labels, three flown arms, single run per arm,
same-distribution. One control never flew. SLURP audio CC BY-NC 4.0 carried. Gold scenarios
scoring-side only; no test split was touched.
