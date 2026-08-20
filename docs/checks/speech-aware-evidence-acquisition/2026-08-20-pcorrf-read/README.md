# P-CORR-F registered one-shot read — archive (2026-08-20)

The single sanctioned read of the flown P-CORR-F percept-keyed type-corrective supply probe
(`SAEA-PROBE-pcorrf-240`). The pinned offline read suite ran **exactly once**, exit 0; the exposure
row flips to consumed in the same commit, and the suite is idempotence-guarded against a second run
into this directory (a pre-existing `verdict.json` refuses the read before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pcorrf-240/attempt-20260820T151845Z-88b2a5` |
| Attempt status | `COMPLETED` (error `None`) |
| Rows scored | 240 = W1 60 + W2 60 + W3 60 + W4 60; 240 distinct (arm, sample_id) pairs |
| Suite | `speech_aware_evidence_acquisition.analysis.pcorrf_read` (coordinator-reviewed before the read), run **exactly as shipped** |
| Read at study HEAD | `a407d03`, clean tree |
| Pre-read gates | `pytest tests/unit/test_pcorrf_read.py tests/unit/test_pcorrf_flight.py` **110 passed**; flight-archive `MANIFEST.sha256` verified (**34/34 OK**); ledger row `consumed = no`; pcorrf modules byte-identical to their reviewed state at `5c3e0fa` |
| Registration | `docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md` (§3 verdicts, §4 legality, §5 comparators, §8 pre-read GPU-accounting adjudication) |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-20-pcorrf-flight/` |
| Verdict document | `docs/readiness/2026-08-20-pcorrf-verdict.md` |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory — the pre-read and post-read attempt fingerprints are identical
(`35c64313fc0abe147132576292aecbd22bdab91d81a64970bbb477d2d95cdb20`). No GPU, no model contact, no
installs. `PYTHONDONTWRITEBYTECODE=1` throughout.

## Outcome

**Q-1 mechanism: CORRECTIVE-PERCEPT. Q-2 dose efficiency: DOSE-INSUFFICIENT. W4: descriptive.**

Reachability was published first, led by the denominator correction the flight receipt required:
20 of 60 samples fly at K = 0 with **byte-identical W1/W2 prompts (verified 20/20)**, so the
mechanism denominator is **40, not 60**. Max attainable recovery W1 37/89, W2 0/89, W3 37/89,
W4 39/89. Positive control: W3's zero-supply slice scores 0.1609 against the cited bare-core A0
0.1741, inside the ±0.013 drift bound.

Q-1 registered full-60: Δ₁ = **+0.0508**, 90% CI **[+0.0098, +0.0968]**, σ̂ 0.0265 (N = 10,000,
seed 20260807) → **CORRECTIVE-PERCEPT**. Restricted to the 40 K > 0 samples: Δ₁ = **+0.0753**,
CI **[+0.0179, +0.1411]** — same branch, larger effect where the mechanism can act.
Q-2 registered full-60: Δ₂ = **−0.1625** vs the pinned A3 0.5961 → **DOSE-INSUFFICIENT**; restricted
to K > 0, Δ₂ = **−0.0380**, so the deficit is the 33% zero-supply blind spot, not a weak dose.
Arm SLU-F1: W1 **0.6588**, W2 0.6080, W3 0.4336, W4 0.6366.

**The percept gate is the headline.** Capture of supplied corrective entries: W1 self-percept
**96.7%** (59/61) versus W2 cross-percept **0.0%** (0/61); W3 100.0%; and inside a single W4 prompt,
percept-keyed L1 **95.1%** versus retrieval-widened L2b **11.9%**. P-TRAP with the sign flipped, as
pre-declared.

**Dual measurement (mandatory).** Recovery/contamination: W1 53/12, W2 46/0, W3 27/14, W4 48/18. On
the 40 mechanism-usable samples the marginal effect of the corrective layer over its dose-matched
control is **+7 gold slots recovered against +12 spurious values emitted** — the gain is real and so
is the cost. W1's supplied set is 47 gold-valued and 14 non-gold; **12 of those 14 non-gold entries
were emitted (85.7%)**, so the core applies no correctness filter of its own. Guardrails: parse rate
1.0000, empty rate 0.0000 and copy rate 0.0000 on all four arms; induced substitutions 3/2/2/3; no
harness defects.

## Two disclosures carried out of this read

1. **The byte-identical-resend floor is not 0.0000 on this stack.** The 20 K = 0 samples are a free
   in-flight measurement: at temperature 0, seed 20260803, `-np 4`, **6 of 20 byte-identical prompt
   pairs returned different responses** (aggregate |ΔF1| on that slice 0.0072). Verdict headroom is
   about an order of magnitude, so nothing here changes, but successor registrations must stop citing
   0.0000 as this stack's floor.
2. **Reachability denominator display defect (verdict-neutral).** `verdict.json` renders the
   fractions as `n/8352` rather than `n/89`, because `analysis.pslu_read.load_gold_by_sample_id`
   ignores its `sample_ids` filter and returns the whole devel gold map (8690 keys). Numerators are
   correct (they iterate the 60 flown rows), and this is the only aggregate over that map in the
   read, so no verdict, bootstrap, recovery or contamination number moves. The suite was **not**
   patched; the corrected fractions are stated in the verdict document.

Full numbers, the recovery-versus-contamination balance sheet, what this decides for the filling
tier and the supply law, and the P-CORR-R design implications are in
`docs/readiness/2026-08-20-pcorrf-verdict.md`.

## Files

| File | What it is |
|---|---|
| `README.md` | this archive note |
| `verdict.json` | the suite's own machine-readable output (verdicts, bootstraps, dual measurement, reachability, guardrails) |
| `report.txt` | the suite's rendered report, verbatim |
| `MANIFEST.sha256` | sha256 over every file above |
