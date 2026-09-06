# SLURP legal-label projection v2, promoting an action-named scenario (2026-09-06)

Row id `SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-V2-V1`, profile `model-free-check`.
**Zero model, GPU, tool, embedding and network contacts.** Verdict:
`docs/readiness/2026-09-06-slurp-legal-label-projection-v2-verdict.md`.
Preregistration:
`docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md`.

## Headline

**RE-LOCKED.** The SLURP direct comparator is the sealed closed-list arm **plus**
`slurp-legal-label-projection-v2`, scored through the registered
`slurp-slu-official-projected-v2`.

| arm | intent unprojected | intent v1 | **intent v2** | SLU-F1 (all three) | changed | via promote | landing on gold |
|---|---|---|---|---|---|---|---|
| **CLOSED-LIST** | 71.40 | 71.60 | **73.10** | 35.80 | 39 | **19** | **17** (v1: 2) |
| KU-S1c (revise) | 72.90 | 73.10 | **74.00** | 35.92 | 37 | 13 | 11 (v1: 2) |
| KU-S1c (draft) | 72.60 | 72.70 | **73.50** | 35.51 | 35 | 11 | 9 (v1: 1) |
| KC-S1a (as sealed) | 15.20 | 15.30 | **15.40** | 35.75 | 8 | 2 | 2 (v1: 1) |
| KC-S1b (as sealed) | 32.10 | 32.30 | **33.80** | 44.35 | 38 | 19 | 17 (v1: 2) |

Every preregistered lock condition is met in **both** contrasts. Intent **+1.50 pp** over the
locked v1 comparator (15 saves, 0 harms, CI90 [+1.0, +2.1]) and **+1.70 pp** over the raw
sealed labels (17 saves, 0 harms, CI90 [+1.1, +2.3]), non-negative on OLD500 and NEW500 in
both, and **zero intent harms in every one of the 18 gold-scenario strata, in both**. Scenario
81.00 → **82.60**, the column v1 never moved. Action 73.30 → **74.60**, back above the
unprojected 73.90. Every entity-side number is identical to the last decimal across all three
views on every arm.

**Two caveats the verdict states as loudly as the result.** The whole intent gain is **one
stratum** — `recommendation`, 46.67 → 71.67 on 60 rows, with 17 of 18 strata flat against v1 —
and the **multi-owner half of the tie-break never fires** on this roster, so it is exercised
only by unit tests.

## Files

| file | what it is |
|---|---|
| `read.py` | the archived, byte-identical copy of the exact script that produced `read.json`. The live path is `scripts/slurp_legal_label_projection_v2_read.py`, and that is the one to run: the script resolves the repository from its own location, so the copy reproduces the bytes but not the invocation. Scoring-side only, zero contacts |
| `read.json` | schema `saea-slurp-legal-label-projection-v2-read-v1`: the full read — official blocks for all fifteen scored sets, per-branch projection accounting and the complete `from -> to` map split by branch, three paired contrasts with per-stratum tables over three populations, both weightings, the residual after v2 and the KC-S1b fallback analysis |
| `result-summary.json` | schema `saea-slurp-legal-label-projection-v2-result-summary-v1`: the machine-readable verdict, assembled from `read.json` alone |
| `build_result_summary.py` | that assembler; reads nothing but `read.json` |
| `MANIFEST.sha256` | SHA-256 of every file in this directory |

## How each number was produced

Each of the four sealed arms with a run manifest was scored **three times over its complete
1,000-row manifest through `core.scoring_batch`, one job per manifest, `include_per_sample=True`,
never sharded**:

* `slurp-slu-official` — UNPROJECTED, the identity anchor;
* `slurp-slu-official-projected` — `slurp-legal-label-projection-v1`, the LOCKED comparator;
* `slurp-slu-official-projected-v2` — the successor rule under test.

Both projected jobs need a manifest that declares their scorer, and `core.bundle.verify_bundle`
confines every artifact path a manifest names to the manifest's own directory. So **two derived
manifests** were written beside each sealed one, differing from it **only in the `scorers`
list**; their sha256 is in `read.json` under `manifests`. No sealed byte was altered, and the
sealed manifest is re-verified from its own bytes by the unprojected job in the same batch.

The **KU-S1c draft phase has no manifest of its own** — a phase is not a run — so it was scored
through the same registered scorer functions over the same complete 1,000 rows, exactly as its
own 2026-09-05 read and v1's read did. That deviation was registered in advance
(preregistration section 3).

Reproduce:

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src
D=docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-legal-label-projection-v2
python -B scripts/slurp_legal_label_projection_v2_read.py --out $D/read.json \
  --score-dir $SPEECHRL_DATA_DIR/runs/SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-V2-V1/score-batch
python -B $D/build_result_summary.py
```

Add `--reuse-score-dir` to re-read an existing batch instead of respawning the official
evaluator; the batch is deterministic, so that changes no number. Score-batch artifacts (twelve
job results, their stderr logs and the batch summary) live under
`$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-V2-V1/score-batch/` and never
enter Git.

## Identity anchors that had to pass before any number was trusted

1. **Every published number reproduces, and the read FAILS CLOSED if it does not.** All ten
   published sets — seven official metrics × five arms × the unprojected and v1 views — are
   hard-coded in `read.py` and matched exactly: the closed-list verdict's own table and v1's.
   The v2 column is the only column here that has never been published before.
2. The **official-vs-port identity check passed on all fifteen scored sets** (absolute
   difference ≤ 1.1e-16).
3. The entity-side invariant holds **row by row on every arm and every view**: not one of the
   15,000 arm-rows moved on `slot_f1_exact_f1`, `slu_f1_f1`, `slu_f1_word_f1` or
   `slu_f1_char_f1`.
4. No emitted label is illegal after either projection (`residual_illegal_targets` 0 on every
   arm and both rules), re-derived from the emitted labels rather than asserted.
5. The OLD500 / NEW500 partition reconstructs from its receipts at 500 + 500 with no overlap,
   and every arm covers the same 1,000 sample ids in all three views.
6. **Zero devel gold intents lie outside the 60 TRAIN pairs**, which is why intent and scenario
   harms are structurally zero — the property both preregistrations stated in advance.

## Boundaries

Devel only; the held-out `test` split is never named, loaded or scored. Gold opens once,
scoring-side, through the registered official scorer with `allow_heldout=False`. **No SLURP
devel sentence text is read anywhere in this work** — not into a receipt, a document, a table
cell or a log line. The pinned official `evaluate.py` at commit `8eb1654…311f1` in
`~/.venvs/slurp-official-eval` is used, never modified. No published verdict is reopened,
restated or re-scored: KC-S1b stays admitted on its own sealed numbers, KU-S1c stays reported
on its own, and v1 stays a registered, resolvable scorer whose verdict stands as published.
The re-lock is prospective.
