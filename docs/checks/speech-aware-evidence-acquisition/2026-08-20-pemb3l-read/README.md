# P-EMB-3L registered one-shot read — archive (2026-08-20)

The single sanctioned read of the flown P-EMB-3L local embedding construction sweep
(`SAEA-PROBE-pemb3l-234`). The pinned offline read suite ran **exactly once**, exit 0; the exposure
row flips to consumed in the same commit, and the suite is idempotence-guarded against a second run
into this directory.

## What was read

| | |
|---|---|
| Sweep | 234/234 embedding contacts across two attempts on one plan (`attempt-20260820T062543Z-e91099` = L1+L2, `attempt-20260820T065009Z-1361ad` = L3) |
| Attempt status | `COMPLETED` (`error: null`), durable state `FINALIZED` |
| Vectors read | `derived/embeddings/SAEA-PROBE-pemb3l-234/<arm>/manifest.json` for all three arms — 78 entries each (60 audio + 18 text), all dim 2048, 78 distinct vector sha256 per arm |
| Suite | `scripts/pemb3l_read.py` → `speech_aware_evidence_acquisition.analysis.pemb3l_read` (built and coordinator-reviewed before the read, flown unmodified) |
| Read at study HEAD | `063c056`, clean tree |
| Pre-read gate | `pytest tests/unit/test_pemb3l_read.py` **24 passed**; flight-archive `MANIFEST.sha256` verified (47/47 OK); ledger row `consumed = no` |
| Registration | `docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md` (§3 thresholds, §6 pre-read instrument amendment) |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3l-flight/` |
| Verdict document | `docs/readiness/2026-08-20-pemb3l-verdict.md` |

Model-free and read-only: the suite never opens a model session, never mutates an attempt directory
or a vector manifest, and consumes only the derived per-arm vector manifests plus scoring-side-only
gold. No GPU, no model contact, no installs. `PYTHONDONTWRITEBYTECODE=1` throughout.

## Outcome

**OVERALL: LOCAL-EXHAUSTED** — *every training-free embedding construction this build can express
fails identically; the external dedicated-embedder path becomes the routing tier's representation
instrument*.

| arm | pooling | prefix | accuracy | labels ever predicted |
|---|---|---|---|---|
| L1 last-bare | `last` | none | **3 / 60 = 0.0500** | 5 / 18 (`general` 29, `play` 26) |
| L2 last-instruct | `last` | GritLM-style | **3 / 60 = 0.0500** | 2 / 18 (`qa` 56, `datetime` 4) |
| L3 mean-instruct | `mean` | GritLM-style | **3 / 60 = 0.0500** | 2 / 18 (`datetime` 38, `qa` 22) |

LOCAL-SPACE-EXISTS (any arm ≥ 0.30) not met — short by **0.2500** (15 samples). LOCAL-EXHAUSTED
(every arm ≤ 0.15) met on all three, clearing by **0.1000**. INCONCLUSIVE-EMB3L not reached.
L3-vs-cited-mean-bare common-mode delta **+0.0000**.

**Carry with every citation.** (1) All three arms sit **below uniform chance** (0.0556) and below
the best constant predictor (0.1333), against 0.7833–0.8167 for closed-set decode routing on the
identical 60 samples. (2) Every arm scores **below the expectation of re-pairing its own prediction
vector at random** (4.300 / 4.867 / 3.733 expected vs 3 observed) — no detectable audio-content
signal in any argmax. (3) **The instruct prefix made the collapse worse**, narrowing the reachable
label set from 5 to 2; `calendar`, the modal gold class, is never predicted by any arm. (4) Geometry:
L1 mean cosine **+0.0377**, L2 **+0.0042**, L3 **−0.1846** with only **1 of 60** positive winners.
(5) **§6.2(c) structural check CONFIRMED at 60/60** — L1's audio vectors are byte-identical to the
consumed P-EMB-1's, so `--pooling` is inert on this build's audio side and the "mean vs last" audio
contrast was never tested; L1 is in fact a **bit-exact replay** of P-EMB-1 (60/60 identical predicted
labels and top-1 cosine floats). (6) The verdict is scoped per §6.3 to the constructions this build
can actually express.

## Contents

- `verdict.json` — machine-readable report (`saea-pemb3l-read-v1`): per-arm accuracy, verdict and
  detail, per-arm confusion tables, attractor structure, the 60-row `predictions` table per arm
  (sample_id, gold, predicted, top-1 cosine, correctness), and the L3-vs-cited delta.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `README.md` — this file.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

Scope: discovery-tier, n = 60 SLURP devel, 18 labels, three arms, single run per arm,
same-distribution. Two arms share an audio side; one arm replays a consumed probe. SLURP audio
CC BY-NC 4.0 carried. Gold scenarios scoring-side only; no test split was touched.
