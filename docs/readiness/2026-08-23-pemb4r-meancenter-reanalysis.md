# P-EMB-4R per-modality mean-centering re-analysis (2026-08-23)

Work item: `docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md` section 5, CPU queue,
final entry — "per-modality mean-centering re-analysis of the landed P-EMB-4R vectors (model-free;
settles whether the 0.13–0.28 audio cosine is a modality-cone artifact)". Survey grounding:
`docs/readiness/2026-08-23-cross-modal-retrieval-survey.md` items 17 (modality gap: Mind the Gap,
I0T standardization, mean-shift calibration) and 28 (audio-text embedding granularity), plus
synthesis point (b).

Implementation: `src/speech_aware_evidence_acquisition/analysis/pemb4r_meancenter_reanalysis.py`,
SHA-256 `64e6c396df680348530165bdc364301606e2a91a5dce928a85835aad753d54ea`. Run against the working
tree at study commit `418ec68`; a parallel session advanced HEAD during this session (`26c4eeac`,
`d228de28`), with documentation-only changes under `docs/`, so no input to this analysis moved.

## Legality frame

This is a **descriptive re-analysis of CONSUMED artifacts**. The seven-arm P-EMB-4R vector sets
were written by flight attempt `attempt-20260820T181837Z-3e6c8f` (2026-08-20) and consumed by the
one-shot read of 2026-08-21
(`docs/checks/speech-aware-evidence-acquisition/2026-08-21-pemb4r-read/`). This work made **zero
model contacts**: no server was started, no embedding was regenerated, no cache or run bundle was
touched, and nothing was written into the embedding namespace. Gold scenario labels were used
**scoring-side only, offline**, from the same source the consumed read used. The results below are
**design inputs for knowledge-base construction**. They carry **no verdict clause** and **cannot
revise the consumed P-EMB-4R verdict**, which stands exactly as landed.

## 1. Inputs and integrity

| Item | Bound value |
|---|---|
| Probe | `SAEA-PROBE-pemb4r-4100`, flight attempt `attempt-20260820T181837Z-3e6c8f` |
| Query sets | 7 arms × 60 SLURP devel queries, loaded through `pemb4r_flight.load_query_vectors` (per-file SHA-256 verified) |
| Key banks | 4 models × 900 SLURP train utterances, `pemb4r_flight.load_bank_vectors` (per-file SHA-256 verified) |
| Retrieval plan | canonical document SHA-256 `7150c6b3410de4cc883da7f5ef0798dd80e4beaf253037594e99ff8cf5cea768` — **matches** the registered value |
| Gold source | `analysis.pemb_read.gold_scenarios_for_run_a` (devel split + `configs/probes/g0-binding/pslu-sample-devel-n60.json`), byte-compared against the landed `verdict.json` per-sample gold — identical |
| Scoring conventions | reused verbatim: `pemb4r_flight.build_arm_retrieval` (cosine, descending, ties by ascending bank id) and `analysis.pemb4r_read.build_arm_report` (K=5 majority vote, ties by highest mean cosine, recall@k over the ranked non-deduplicated label sequence) |
| Model/GPU contact | none |

The vectorised scorer used for the corrected variants was validated against
`build_arm_retrieval`'s own per-pair output on every sample of every arm before any corrected
number was produced: **0 disagreements** in top-K bank ids, top-K labels, or cosines (tolerance
1e-12).

Incidental measurement: **every landed vector is already unit-length** (raw norm 1.0000 ± 0.0000
for all 4,020 query and bank vectors). Centering on the mean of the raw vectors and centering on
the mean of the L2-normalised vectors are therefore the same operation here, and the two variants
below are bit-identical — the choice carries no risk in this data.

## 2. Reproduction of the landed read (correct-loading proof)

Recomputed from the vectors on disk, compared field-by-field against
`2026-08-21-pemb4r-read/verdict.json` at tolerance 1e-12, including every per-sample K=5 vote
label and every per-sample gold label.

| Arm | vote K=5 landed | vote K=5 recomputed | r@1 | r@3 | r@5 | per-sample vote diffs | Reproduced |
|---|---:|---:|---:|---:|---:|---:|:--:|
| a-lco3 | 9/60 = 0.1500 | 9/60 = 0.1500 | 0.1833 | 0.3000 | 0.3000 | 0 | yes |
| a-lco7 | 7/60 = 0.1167 | 7/60 = 0.1167 | 0.1167 | 0.1500 | 0.2000 | 0 | yes |
| a-glap | 19/60 = 0.3167 | 19/60 = 0.3167 | 0.3167 | 0.5167 | 0.5667 | 0 | yes |
| t-lco3 | 33/60 = 0.5500 | 33/60 = 0.5500 | 0.5167 | 0.7000 | 0.7833 | 0 | yes |
| t-lco7 | 34/60 = 0.5667 | 34/60 = 0.5667 | 0.6333 | 0.7333 | 0.8667 | 0 | yes |
| t-glap | 13/60 = 0.2167 | 13/60 = 0.2167 | 0.2500 | 0.4333 | 0.5167 | 0 | yes |
| t-qw | 52/60 = 0.8667 | 52/60 = 0.8667 | 0.8500 | 0.9167 | 0.9333 | 0 | yes |

Recall columns are identical landed-vs-recomputed and are shown once. **Reproduction: PASS on all
seven arms, all fields, zero per-sample differences.**

## 3. Correction A — per-modality mean-centering

Per arm: subtract the query-side mean over that arm's own 60 query vectors from every query;
subtract the key-side mean over that model's own 900 bank vectors from every key; re-L2-normalise;
re-score with the unchanged ranking and voting conventions.

| Arm | kind | vote K=5 before | vote K=5 after | Δ vote | r@5 before | r@5 after | Δ r@5 |
|---|---|---:|---:|---:|---:|---:|---:|
| **a-lco3** | audio | 0.1500 (9/60) | **0.5000 (30/60)** | **+0.3500** | 0.3000 | **0.7500** | **+0.4500** |
| **a-lco7** | audio | 0.1167 (7/60) | 0.2833 (17/60) | +0.1667 | 0.2000 | 0.5000 | +0.3000 |
| **a-glap** | audio | 0.3167 (19/60) | 0.2333 (14/60) | **−0.0833** | 0.5667 | 0.6000 | +0.0333 |
| t-lco3 | text | 0.5500 (33/60) | 0.7333 (44/60) | +0.1833 | 0.7833 | 0.8667 | +0.0833 |
| t-lco7 | text | 0.5667 (34/60) | 0.7500 (45/60) | +0.1833 | 0.8667 | 0.9167 | +0.0500 |
| t-glap | text | 0.2167 (13/60) | 0.5167 (31/60) | +0.3000 | 0.5167 | 0.8000 | +0.2833 |
| t-qw | text | 0.8667 (52/60) | 0.8333 (50/60) | −0.0333 | 0.9333 | 0.9167 | −0.0167 |

Recall@1 / recall@3 after centering: a-lco3 0.4667 / 0.6500; a-lco7 0.2167 / 0.4500; a-glap
0.2667 / 0.5167; t-lco3 0.7333 / 0.8167; t-lco7 0.7000 / 0.8833; t-glap 0.5167 / 0.7167; t-qw
0.8167 / 0.8833. The `meancenter-rawmean` sensitivity variant reproduces this table exactly (see
section 1).

**Is this a transductive read of the evaluation batch? No, on the query side.** For `n` unit rows
with centroid `mu`, the leave-one-out centroid for row `i` is `(n·mu − x_i)/(n−1)`, so
`x_i − mu_LOO = (n/(n−1))·(x_i − mu)` — a positive scalar multiple, hence identical after
re-L2-normalisation and identical in every cosine and every ranking. The re-analysis checks this
identity numerically on all seven real matrices: **equivalent on every arm**. Query-side centering
is a per-encoder, per-modality constant offset estimable once, offline, from any audio pool. The
key-side mean is computed purely from the 900 TRAIN bank vectors and never touches a query.

## 4. Correction B — score standardisation

**Per-query z-scoring is ranking-invariant, as expected.** Standardising a single query's own 900
scores is `(s − mu)/sigma` with `sigma > 0` — a strictly increasing affine map, which cannot
reorder that query's candidates. Verified empirically: the argsort of the standardised scores
equals the argsort of the raw scores on **all seven arms**. The informative axis is therefore the
other one.

**Per-key standardisation across the 60 queries** (hubness / mean-shift calibration): subtract
each key's own mean similarity over the query batch (`key-mean-shift`), optionally also dividing
by that key's own standard deviation (`key-zscore`).

| Arm | raw | key-mean-shift | key-zscore | meancenter + key-mean-shift |
|---|---:|---:|---:|---:|
| a-lco3 | 0.1500 | 0.3833 (23/60) | 0.3833 (23/60) | **0.5167 (31/60)** |
| a-lco7 | 0.1167 | 0.2167 (13/60) | 0.2000 (12/60) | 0.2833 (17/60) |
| a-glap | 0.3167 | 0.2500 (15/60) | 0.2167 (13/60) | 0.2333 (14/60) |
| t-lco3 | 0.5500 | 0.6833 (41/60) | 0.6833 (41/60) | 0.7000 (42/60) |
| t-lco7 | 0.5667 | 0.7000 (42/60) | 0.7167 (43/60) | 0.7500 (45/60) |
| t-glap | 0.2167 | 0.6000 (36/60) | 0.5333 (32/60) | 0.4667 (28/60) |
| t-qw | 0.8667 | 0.8500 (51/60) | 0.8167 (49/60) | 0.8333 (50/60) |

Values are vote accuracy at K=5. Recall@5 under `key-mean-shift`: a-lco3 0.6667, a-lco7 0.4167,
a-glap 0.6333, t-lco3 0.8667, t-lco7 0.8333, t-glap 0.8500, t-qw 0.9500.

Unlike Correction A, both key-standardisation variants **are** batch-dependent: they read all 60
queries to score any one of them. They are reported here as score-geometry diagnostics. A
deployable form would estimate the per-key statistic from a train-side query pool, never from the
evaluation set.

## 5. Cone geometry (cone-offset magnitudes)

Unit-sphere centroids. `||mu||` is the cone-offset magnitude: 0 = isotropic, 1 = a degenerate ray.
`mean pair` is the mean of the full 60 × 900 cosine matrix.

| Arm | kind | ‖mu_q‖ | ‖mu_k‖ | cos(mu_q, mu_k) | ‖mu_q − mu_k‖ | mean pair raw | mean pair centred | mean top-1 cos raw → centred |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| a-lco3 | audio | **0.9435** | 0.7539 | **0.0740** | 1.1633 | 0.0526 | −0.0001 | 0.1700 → 0.1592 |
| a-lco7 | audio | **0.8906** | 0.6963 | **0.1052** | 1.0713 | 0.0653 | −0.0000 | 0.2753 → 0.1507 |
| a-glap | audio | 0.7110 | 0.7793 | **−0.1036** | 1.1080 | −0.0574 | −0.0001 | 0.1280 → 0.3814 |
| t-lco3 | text | 0.7750 | 0.7539 | 0.5949 | 0.6884 | 0.3476 | 0.0013 | 0.6709 → 0.4298 |
| t-lco7 | text | 0.6437 | 0.6963 | 0.6449 | 0.5666 | 0.2890 | 0.0005 | 0.5964 → 0.4183 |
| t-glap | text | 0.9143 | 0.7793 | 0.8916 | 0.4155 | 0.6352 | 0.0008 | 0.8901 → 0.4501 |
| t-qw | text | 0.6331 | 0.6564 | **0.9770** | 0.1402 | 0.4060 | 0.0001 | 0.7580 → 0.5966 |

Audio↔text separation of the same model's own query centroids, and the gap to the matched text
control:

| Model | audio arm vs its text control, raw | after centering | gap movement |
|---|---:|---:|---:|
| lco3 | 0.1500 vs 0.5500 (−0.4000) | 0.5000 vs 0.7333 (−0.2333) | **narrows 0.1667** |
| lco7 | 0.1167 vs 0.5667 (−0.4500) | 0.2833 vs 0.7500 (−0.4667) | widens 0.0167 |
| glap | 0.3167 vs 0.2167 (**+0.1000**) | 0.2333 vs 0.5167 (−0.2833) | **widens 0.3833** |

## 6. Interpretation and design consequence

1. The cone is real and large on the omni-native side: the LCO audio query sets occupy an
   extremely narrow cone (‖mu_q‖ = 0.94 and 0.89 on 2048-d and 3584-d spaces) that is nearly
   orthogonal to the text key cone (cos(mu_q, mu_k) = 0.074 and 0.105, mean pair cosine 0.053 and
   0.065). Item 17's prediction holds for these two encoders.
2. Removing the two constant offsets converts a large part of that deficit into retrieval:
   a-lco3 moves 9/60 → 30/60 (vote K=5 0.1500 → 0.5000) and recall@5 0.3000 → 0.7500; a-lco7
   moves 7/60 → 17/60 with recall@5 0.2000 → 0.5000. The reported 0.13–0.28 audio cosine was
   substantially a cone artifact, not only an information deficit.
3. GLAP behaves oppositely. As a contrastively pre-aligned audio-text model its audio query cone
   is looser (0.711) but *anti*-aligned with its key cone (cos = −0.104, mean pair cosine
   −0.0574); centering raises its mean top-1 cosine 0.1280 → 0.3814 while *lowering* accuracy
   19/60 → 14/60. Its own text control gains instead (13/60 → 31/60), so the a-glap ↔ t-glap gap
   does not close — it opens by 0.38. The named illustrative bar (a-glap ≥ 0.50) is **not met**.
4. The 0.50 bar is met, exactly, by a different audio arm: a-lco3 at 0.5000, rising to 0.5167 when
   the per-key hubness shift is composed on top. That arm carries the flight's
   `POOLING-OVERRIDE-PRESENT` stack scope, so it is a stack-level observation about this serving
   configuration, never a model-level property.
5. Even so, no corrected audio arm reaches any corrected text arm: best audio 0.5167 vs t-lco3
   0.7333, t-lco7 0.7500, t-qw 0.8333, and far below the cited direct-speech FS-NONE reference
   0.8167. Text keys remain the stronger retrieval dimension by a wide margin after both
   corrections are applied to both sides.
6. Correction A is legally deployable as written: query-side centering is leave-one-out identical
   (section 3) and key-side centering reads TRAIN only. Correction B is not, in its measured form,
   and must be re-specified against a train-side query pool before any runtime use.
7. **Design consequence for the KB build.** The primary sequencing is unchanged: KB-BUILD v1
   proceeds **text-key-first**. But audio-Q does not stay fully parked — audio keys re-enter as a
   *secondary, centering-mandatory* dimension in the multi-dimensional K design, with per-modality
   centering treated as a required preprocessing step of any audio-key dimension rather than an
   optional tweak, and with the encoder choice reopened (the omni-native LCO encoders, not GLAP,
   are the ones the correction rescues).
8. Corollary for the survey's synthesis point (b): "apply per-modality mean-centering before
   accepting any audio cosine as a ceiling" is confirmed on this data and should be a standing
   precondition for any future audio-embedding measurement in this study.

## 7. How to reproduce

```bash
# WSL2 Ubuntu-24.04
source ~/.venvs/speechrl/bin/activate
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=<repo>/src
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
python -m speech_aware_evidence_acquisition.analysis.pemb4r_meancenter_reanalysis \
    --output-dir <scratch-dir> --repo-root <repo> --embeddings-root "$SPEECHRL_DATA_DIR"
```

Runtime is roughly 90 s on CPU. The command exits non-zero if the landed read fails to reproduce
or if the vectorised scorer disagrees with `build_arm_retrieval`, so a green exit is itself the
integrity assertion. Output artifacts (`meancenter-reanalysis.json`, `report.txt`) are written to
the caller's directory and are intentionally not committed.

## 8. Incidental defect found (not repaired here)

At study commits `418ec68` and `26c4eeac` the package carries a pre-existing import cycle:
`rails/__init__` → `rails.consumption` → `core.retrieval` → `core/__init__` → `core.driver.cli` →
`rails.probes.pslu_flight` → `rails.adapters.slurp` → `rails.consumption` (partially
initialised) → `ImportError`. It was introduced by commit `8f51e95d` ("Refactor speech-native loops
onto openJiuwen"). Consequences observed: `scripts/pemb4r_read.py` no longer imports, and
`tests/unit/test_pemb4r_read.py` fails at collection. Both failures reproduce with this
re-analysis module absent from the tree, so the defect is independent of this work. This
re-analysis routes around it by reaching `core` before `rails`; repairing the cycle belongs to a
task with authority over `rails`/`core`.
