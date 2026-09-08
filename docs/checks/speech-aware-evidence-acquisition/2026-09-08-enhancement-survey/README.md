# Enhancement-as-an-observe-mode survey — receipt

Row `SAEA-MF-ENHANCEMENT-SURVEY-V1`, profile `model-free-check`, owner Decision 12-H of
2026-09-08. Note: `docs/readiness/2026-09-08-enhancement-observe-mode-survey-v1.md`.
Runner: `scripts/run_enhancement_survey.py`.

**Zero model, GPU, tokenizer, embedder, retriever, network and paid-API contacts; zero audio
seconds delivered to any service; no enhancement model downloaded, installed, loaded or run.**
No byte was written under any dataset or derived-media root.

## Files

| file | what it holds |
|---|---|
| `summary.json` | every figure this read produced, machine-readable |
| `a2t-frozen400-acoustics.csv` | the 400 frozen Audio2Tool discovery wavs, one row each: sample rate, duration, peak dBFS, active share, floor dBFS, speech-to-floor margin |
| `slurp-channel-acoustics.csv` | the 766 DEV-1000 utterances whose recording session carries BOTH channel files, one row each, with the headset and far-field figures side by side |
| `e21-slice-acoustics.csv` | the seeded 132-slice sample (3 per call, seed 20260908) of the sealed Earnings-21 90-second obs-slices |

## Reproducing

From the study checkout, in WSL2 with `~/.venvs/speechrl` active:

```bash
PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= \
  python scripts/run_enhancement_survey.py --write
```

Pass `--umbrella-lock <path>` (or set `SAEA_UMBRELLA_LOCK`) when the checkout is a git worktree
parked outside the registered `<umbrella>/studies/<study>/` layout, where the lock locator cannot
find `docs/datasets.lock.json` on its own. The receipt carries no timestamp, so two back-to-back
writes reproduce the same `MANIFEST.sha256`.

## The one statistic that is not a standard quantity

`speech_floor_margin_db` is the median level of the frames the committed 20 ms energy gate calls
active, minus the 10th-percentile frame level of the same clip, at
`analysis.e22_clip_boundary`'s own `FRAME_MS=20` / `PEAK_DROP_DB=30` / `ABSOLUTE_FLOOR_DBFS=-55`.
It is a crude ranking device, **not an SNR**: no carrier in this study ships a clean reference
rendition of the same audio, so a true SNR cannot be computed for any of them. Every figure
derived from the gate inherits its crudeness, exactly as the clip-boundary audit says.

## Identity anchors that had to pass before any split was believed

* SLURP: the sealed comparator's own published numbers, recomputed from its sealed bytes —
  intent 71.40 unprojected, 73.10 under `slurp-legal-label-projection-v2`, SLU-F1 35.80.
  `identity_check_passed: true` in `summary.json`.
* Audio2Tool: every per-tier figure is READ from the three official-population verdict
  summaries, never recomputed; the media half re-verifies each wav header's sample rate against
  `data.audio2tool.load_media_rows`' own measurement before using it.
