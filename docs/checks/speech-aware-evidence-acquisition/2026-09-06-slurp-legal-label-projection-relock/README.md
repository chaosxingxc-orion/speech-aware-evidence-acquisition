# SLURP legal-label projection, re-locking the closed-list baseline (2026-09-06)

Row id `SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-RELOCK-V1`, profile `model-free-check`.
**Zero model, GPU, tool, embedding and network contacts.** Verdict:
`docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-verdict.md`.
Preregistration:
`docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md`.

## Headline

**RE-LOCKED.** The SLURP direct comparator is the sealed closed-list arm **plus** the
legal-label projection `slurp-legal-label-projection-v1`, scored through the registered
`slurp-slu-official-projected`.

| arm | intent unprojected | intent projected | SLU-F1 (both) | rows projected | impossible pairs |
|---|---|---|---|---|---|
| **CLOSED-LIST** | 71.40 | **71.60** | 35.80 | 39 | 3.90 % → 0.00 % |
| KU-S1c (revise) | 72.90 | 73.10 | 35.92 | 37 | 3.70 % → 0.00 % |
| KU-S1c (draft) | 72.60 | 72.70 | 35.51 | 35 | 3.50 % → 0.00 % |
| KC-S1a (as sealed) | 15.20 | 15.30 | 35.75 | 8 | 0.80 % → 0.00 % |
| KC-S1b (as sealed) | 32.10 | 32.30 | 44.35 | 38 | 3.80 % → 0.00 % |

Every preregistered lock condition is met: intent `+0.00` on OLD500, `+0.40` on NEW500,
`+0.20` pooled, and **zero intent harms in every one of the 18 gold-scenario strata**. Every
entity-side number is identical to the last decimal on every arm — the projection rewrites
`scenario`/`action` and nothing else.

**The gain is protocol alignment, not accuracy.** Only 2 of the 39 legalised closed-list rows
land on the gold intent, and the action column loses 0.60 pp. The residual is named and
priced: **19 of the 39 rows put a legal ACTION name in the scenario slot**, and promoting it
back to its owning scenario would have recovered **15** of them (about +1.5 pp intent). That is
a SUCCESSOR rule and needs its own preregistration before it can be locked.

## Files

| file | what it is |
|---|---|
| `read.py` | the archived, byte-identical copy of the exact script that produced `read.json`. The live path is `scripts/slurp_legal_label_projection_read.py`, and that is the one to run: the script resolves the repository from its own location, so the copy reproduces the bytes but not the invocation. Scoring-side only, zero contacts |
| `read.json` | schema `saea-slurp-legal-label-projection-relock-read-v1`: the full read — official blocks for all ten scored sets, projection accounting and the complete `from -> to` map, paired contrasts with per-stratum tables for three populations, both weightings, the residual diagnostic and the KC-S1b fallback analysis |
| `result-summary.json` | schema `saea-slurp-legal-label-projection-relock-result-summary-v1`: the machine-readable verdict, assembled from `read.json` alone |
| `build_result_summary.py` | that assembler; reads nothing but `read.json` |
| `MANIFEST.sha256` | SHA-256 of every file in this directory |

## How each number was produced

Each of the four sealed arms with a run manifest was scored **twice over its complete
1,000-row manifest through `core.scoring_batch`, one job per manifest, `include_per_sample=True`,
never sharded**:

* `slurp-slu-official` — the UNPROJECTED identity anchor;
* `slurp-slu-official-projected` — the same code path with the projection on.

The projected job needs a manifest that declares its scorer, and `core.bundle.verify_bundle`
confines every artifact path a manifest names to the manifest's own directory. So a **derived
manifest** was written beside each sealed one, differing from it **only in the `scorers` list**;
its sha256 is in `read.json` under `manifests`. No sealed byte was altered, and the sealed
manifest is re-verified from its own bytes by the unprojected job in the same batch.

The **KU-S1c draft phase has no manifest of its own** — a phase is not a run — so it was scored
through the same registered scorer functions over the same complete 1,000 rows, exactly as its
own 2026-09-05 read did. That deviation was registered in advance (preregistration section 3).

Reproduce:

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src
D=docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-legal-label-projection-relock
python -B scripts/slurp_legal_label_projection_read.py --out $D/read.json \
  --score-dir $SPEECHRL_DATA_DIR/runs/SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-RELOCK-V1/score-batch
python -B $D/build_result_summary.py
```

Add `--reuse-score-dir` to re-read an existing batch instead of respawning the official
evaluator; the batch is deterministic, so that changes no number.

Score-batch artifacts (eight job results, their stderr logs and the batch summary) live under
`$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-RELOCK-V1/score-batch/` and never
enter Git.

## Identity anchors that had to pass before any number was trusted

1. The **official-vs-port identity check passed on all ten scored sets** (absolute difference
   0.0, except KC-S1a's 5.6e-17).
2. The unprojected column of every arm **reproduces its own published verdict to the second
   decimal**: CLOSED-LIST 81.00 / 73.90 / 71.40 / 21.91 / 33.69 / 38.20 / 35.80; KU-S1c
   81.50 / 75.20 / 72.90 / 23.26 / 33.99 / 38.07 / 35.92; KU-S1c draft 72.60 intent, 35.51
   SLU-F1; KC-S1b entities-strict 31.37 and SLU-F1 44.35; KC-S1a 21.82 and 35.75.
3. The entity-side invariant holds **row by row on every arm**: not one of the 5,000
   arm-rows moved on `slot_f1_exact_f1`, `slu_f1_f1`, `slu_f1_word_f1` or `slu_f1_char_f1`.
4. No emitted label is illegal after projection (`residual_illegal_targets` 0 on every arm),
   re-derived from the emitted labels rather than asserted.
5. The OLD500 / NEW500 partition reconstructs from its receipts at 500 + 500 with no overlap,
   and every arm covers the same 1,000 sample ids.
6. **Zero devel gold intents lie outside the 60 TRAIN pairs**, which is why intent and scenario
   harms are structurally zero — the property the preregistration stated in advance.

## Boundaries

Devel only; the held-out `test` split is never named, loaded or scored. Gold opens once,
scoring-side, through the registered official scorer with `allow_heldout=False`. **No SLURP
devel sentence text is read anywhere in this work** — not into a receipt, a document, a table
cell or a log line. The pinned official `evaluate.py` at commit `8eb1654…311f1` in
`~/.venvs/slurp-official-eval` is used, never modified. No published verdict is reopened,
restated or re-scored: KC-S1b stays admitted on its own sealed numbers and KU-S1c stays
reported on its own. The re-lock is prospective.
