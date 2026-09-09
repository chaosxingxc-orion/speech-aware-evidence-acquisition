# LP-2 label-token logprob judge — the DESIGN read — `SAEA-SLURP-MF-LP2-DESIGN-V1`

**Zero contacts of every kind.** No model, GPU, server, socket, tokenizer, tool,
embedder, retriever or network; no waveform is decoded and no MP3 is opened, so the
pinned absence of `ffmpeg` is preserved. Five already-sealed files are read and
nothing else.

**Every number here is a DESIGN READ and none of them is a result.** The judge's
threshold is the value that flags 86 of *these* 1,000 rows, so this page measures a
rule against the data that chose it. The decision lives in
`docs/readiness/2026-09-09-slurp-label-token-logprob-judge-lp2-v1-preregistration.md`,
which sends it to a fresh replicate of the same cell read under the frozen rule.

Runner: `label_token_design_read.py` (in this directory). Machine-readable half:
`design-read.json`. Judge: `core.judges.SlurpIntentTokenLogprobJudge`, registered as
`slurp-intent-token-logprob-flag-v1` version `1.0.0`.

## The frozen thresholds

| statistic | frozen floor | rows it flags | basis |
|---|---:|---:|---|
| `intent_mean_token_logprob` **(chosen)** | `-0.2675283079346116` | 86 | the 86-flag cutoff on the predecessor arm |
| `intent_min_token_logprob` | `-0.5693119168281555` | 86 | the 86-flag cutoff on the predecessor arm |

A row is flagged when its statistic is **at or below** the floor: boundary ties are
included, because a threshold cannot split identical evidence.

## The design read, against this arm's own official intent errors

265 of 1000 rows carry an intent error.

| flag | flagged | caught | precision % | recall % |
|---|---:|---:|---:|---:|
| `intent_mean_token_logprob` at its frozen floor | 86 | 65 | 75.58 | 24.53 |
| `intent_min_token_logprob` at its frozen floor | 86 | 62 | 72.09 | 23.40 |
| legality judge (free, recomputed on this arm) | 42 | 28 | 66.67 | 10.57 |
| union: mean-statistic flag + legality judge | 111 | 80 | 72.07 | 30.19 |
| the predecessor's whole-answer minimum, 86 flags | 86 | 44 | 51.16 | 16.60 |

## What the fresh pass has to beat

AUROC for intent error, speaker-cluster bootstrap, 10,000 replicates, seed 20260909, CI90 over 124 clusters:

| statistic | AUROC | CI90 |
|---|---:|---|
| `intent_mean_token_logprob` | 0.8497 | [0.8261, 0.8724] |
| `intent_min_token_logprob` | 0.8446 | [0.8210, 0.8676] |

## The two proofs this read owes

1. **One alignment, not two.** The judge's label-token locator and the predecessor
   read's are compared on all 1000
   rows for both statistics and agree exactly, to the last bit, with
   0 disagreements. The read
   refuses rather than reporting a number if they ever differ.
2. **The threshold is re-derived, not trusted.** Both frozen floors are recomputed
   from the sealed rows as the 86-flag cutoff and asserted equal to the constants
   the judge ships; the registered judge's own flag set is then asserted equal to
   the set that cutoff selects.

## Files

| file | what it holds |
|---|---|
| `label_token_design_read.py` | the runner, zero contacts |
| `design-read.json` | every number above, plus both whole precision-recall curves |
| `MANIFEST.sha256` | this directory's byte manifest |

## Reproducing

```bash
source ~/.venvs/speechrl/bin/activate
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$REPO/src
export CUDA_VISIBLE_DEVICES=
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
cd $REPO && python docs/checks/speech-aware-evidence-acquisition/\
2026-09-09-lp2-label-token-logprob-design/label_token_design_read.py --write
```

The receipt carries no timestamp, so two consecutive writes reproduce the same
`MANIFEST.sha256`.
