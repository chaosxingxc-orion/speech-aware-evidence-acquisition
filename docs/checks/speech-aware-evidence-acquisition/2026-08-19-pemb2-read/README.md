# P-EMB-2 registered one-shot read — archive (2026-08-19)

The single sanctioned read of the flown P-EMB-2 embedding tool-routing probe
(`SAEA-PROBE-pemb2-552`, Run B of the two-run P-EMB registration). The pinned offline read suite ran
**exactly once**, exit 0; the exposure row flips to consumed in the same commit, and the suite is
idempotence-guarded against a second run into this directory.

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb2-552/attempt-20260820T002031Z-e816e2` |
| Attempt status | `COMPLETED` (error `None`), durable state `FINALIZED` |
| Vectors read | `derived/embeddings/SAEA-PROBE-pemb2-552/manifest.json` — 552 entries (400 audio + 152 tool registry rows), all dim 2048, 552 distinct vector sha256 |
| Partition source | the consumed A0 attempt, re-partitioned in-suite via `rails.probes.a2t_pop_flight.load_headroom_source` / `assert_split_identity_hash_pinned` and `analysis.a2t_read.score_row`, with the fail-closed 217/183 count check |
| Suite | `scripts/pemb_read.py run-b` → `speech_aware_evidence_acquisition.analysis.pemb_read` (coordinator-reviewed before the read) |
| Read at study HEAD | `6ebcaba`, clean tree |
| Pre-read gate | `pytest tests/unit/test_pemb_read.py` **41 passed**; flight-archive `MANIFEST.sha256` verified (36/36 OK); ledger row `consumed = no` |
| Registration | `docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md` §3 (Run B) |
| Flight archive | `docs/checks/speech-aware-evidence-acquisition/2026-08-19-pemb2-flight/` |
| Verdict document | `docs/readiness/2026-08-19-pemb2-verdict.md` (carries the arc's SYNTHESIS appendix) |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory (every attempt-dir and `derived/embeddings/SAEA-PROBE-pemb2-552/` file mtime is 20:23 and
predates the 21:26 read; post-read attempt fingerprint
`88bbdb86593092c8c2fae096072f27fc383b56c47df0ac7147bd3c6f577bb134`). No GPU, no model contact, no
installs. `PYTHONDONTWRITEBYTECODE=1` throughout.

**Landing-integrity note.** The CLI ran to completion (exit 0, bundle written 21:26) but the
supervising session was severed by a transient connection error mid-execution; the landing was
completed afterwards from the bundle that single execution had already written. **The read still
executed exactly once** — no second invocation was issued, the idempotence guard was never re-armed,
and both output files carry the 21:26 mtimes of that one execution.

## Outcome

**OVERALL: EMB-CLOSED** — top-1 accuracy on the 183 tool-wrong ids = **0.0109** ≤ 0.10.

**The 183 headline** (the population no supply form reaches; V4 excludes it from the signed supply
account, 45.75 % of the frozen 400): **2 recoveries / 183 = 0.0109** top-1, **5/183 = 0.0273**
top-5. EMB-OPENS-183 fails on **both** conjuncts — top-1 short by **0.2891** and recoveries short by
**53** (the observed count is 3.6 % of the registered floor of 55). EMB-CLOSED met, clearing its
ceiling by **0.0891** (a factor of 9.2). INCONCLUSIVE-EMB2 not reached. Chance baselines: uniform
chance over 152 rows expects **1.79** hits, random re-pairing of the same predicted vector expects
**0.99**, and a permutation test (N = 100,000, seed 20260807) gives **P(hits ≥ 2) = 0.2562**; the
top-5 figure is **below** its own uniform chance rate of 5/152 = 0.0329. **The 183 are not opened.**

**Non-degradation on the 217** (reported, no clause): **1/217 = 0.0046**, below the uniform chance
rate of 0.0066 (permutation P(hits ≥ 1) = 0.7358), against the decode router's 217/217 = 1.0000 by
construction. Whole-population: decode **217/400 = 0.5425** vs embedding **3/400 = 0.0075**.

**Carry with every citation.** (1) Predictions collapse to **15 of 152** tools; `stopCharging` alone
takes **151/400 (37.8 %)**, the top two take 53.3 % and the top five 85.8 %; **137 registry rows were
never the nearest neighbour of any clip**. (2) **Every one of the 400 winning cosines is negative**
(max −0.0494, mean −0.1253, median −0.1177, min −0.2541) — with L2-normalized vectors, the best of
152 candidate rows is anti-aligned with the audio on every sample. (3) All three top-1 hits in the
whole run land on collapse-attractor tools. (4) This carrier **removes Run A's strongest confound**:
the text side here is the full shipped registry row (name + description + parameter schema), an order
of magnitude richer than Run A's bare label, against clips averaging 5.4 s — and the result is worse,
not better, so length/form asymmetry is not the explanation and the absence of a contrastive
objective in the frozen core is.

## Contents

- `verdict.json` — machine-readable report (`saea-pemb2-read-v1`): the 183/217 partition sizes,
  recoveries, top-1/top-5 accuracies, verdict and detail, the confusion table over the 183, and the
  400-row `predictions` table (sample_id, partition, gold tool-name set, top-1 tool, top-1 cosine,
  top-5 list, top-1/top-5 correctness).
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

Scope: discovery-tier, n = 400 Audio2Tool discovery split, 152 registry rows, single run,
same-distribution, one pooling mode, one text rendering. The 183/217 partition is a property of one
consumed A0 attempt, not an established stable set. Audio2Tool CC BY-NC 4.0 carried. Gold tools
scoring-side only; no test split was touched.
