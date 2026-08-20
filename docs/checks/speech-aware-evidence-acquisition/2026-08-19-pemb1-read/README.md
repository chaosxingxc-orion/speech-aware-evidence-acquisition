# P-EMB-1 registered one-shot read — archive (2026-08-19)

The single sanctioned read of the flown P-EMB-1 embedding scenario-routing probe
(`SAEA-PROBE-pemb1-78`, Run A of the two-run P-EMB registration). The pinned offline read suite ran
**exactly once**, exit 0; the exposure row flips to consumed in the same commit, and the suite is
idempotence-guarded against a second run into this directory.

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb1-78/attempt-20260819T235907Z-49567c` |
| Attempt status | `COMPLETED` (error `None`), durable state `FINALIZED` |
| Vectors read | `derived/embeddings/SAEA-PROBE-pemb1-78/manifest.json` — 78 entries (60 audio + 18 text), all dim 2048, 78 distinct vector sha256 |
| Suite | `scripts/pemb_read.py run-a` → `speech_aware_evidence_acquisition.analysis.pemb_read` (coordinator-reviewed before the read) |
| Read at study HEAD | `162cca3`, clean tree |
| Pre-read gate | `pytest tests/unit/test_pemb_read.py` **41 passed**; flight-archive `MANIFEST.sha256` verified (30/30 OK); ledger row `consumed = no` |
| Registration | `docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md` §2 (Run A) |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-19-pemb1-flight/` |
| Verdict document | `docs/readiness/2026-08-19-pemb1-verdict.md` |

Model-free and read-only: the suite never opens a model session, never mutates the attempt
directory, and consumes only the derived vector manifest (every attempt-dir and
`derived/embeddings/SAEA-PROBE-pemb1-78/` file mtime is 20:02 and predates the 20:53 read; post-read
attempt fingerprint `744947017a004d46f631cf01e6c8d6165ab5096bb225be27207f82d8348c2839`). No GPU, no
model contact, no installs. `PYTHONDONTWRITEBYTECODE=1` throughout.

## Outcome

**OVERALL: EMB-WEAK** — *bare cross-modal matching does not form a usable shared space on this core;
the routing tier stays decode-based*. Argmax-cosine accuracy **3 / 60 = 0.0500** over 18 canonical
scenario labels. EMB-ROUTES (≥ 0.65) not met, short by **0.6000** (36 samples); EMB-WEAK (≤ 0.30)
met, clearing by **0.2500**; INCONCLUSIVE-EMB1 not reached.

**Comparators, same 60 samples, same frozen core**: A1′r closed-set decode routing **0.7833**
(cited); P-FEW FS-NONE closed-set decode routing **0.8167** (in-session, consumed same day); A0
free-form decode **≈ 0.10** (cited); uniform chance over 18 labels **0.0556**; best constant
predictor (always `calendar`) **0.1333**. **At 0.0500 the embedding router is below all of them,
including chance.**

**Carry with every citation.** (1) The failure is a **collapse, not misrouting**: only **5 of 18**
labels were ever predicted, and `general` (29) + `play` (26) absorb **55 of 60** samples (91.7 %);
thirteen labels — including the modal gold class `calendar` — were never predicted at all. (2) The
three correct predictions sit inside the two attractors and are fully explained by the prediction
marginal: re-pairing the same 60 predicted labels at random expects **4.30** hits (more than the 3
observed), and a permutation test (N = 100,000, seed 20260807) gives **P(hits ≥ 3) = 0.8774**. There
is **no detectable audio-content signal in the argmax**. (3) The geometry agrees: with L2-normalized
vectors the winning cosine has max **0.0808**, mean **0.0377**, median **0.0366**, one **negative**
winner, and **42 of 60** below 0.05 — the nearest label is essentially orthogonal to the audio in
every case. (4) This is a negative on **one construction** (mean pooling, bare label strings, no
instruct prefix, no contrastive objective in the core), not on embedding routing as a family; any
redesign is a fresh registration and may not re-cut these spent vectors.

## Contents

- `verdict.json` — machine-readable report (`saea-pemb1-read-v1`): accuracy, verdict and detail, the
  full confusion table, and the 60-row `predictions` table (sample_id, gold, predicted, top-1 cosine,
  correctness).
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

Scope: discovery-tier, n = 60 SLURP devel, 18 labels, single run, same-distribution, one pooling
mode, one text rendering. SLURP audio CC BY-NC 4.0 carried. Gold scenarios scoring-side only; no
test split was touched.
