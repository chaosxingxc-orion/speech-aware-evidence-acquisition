# Provenance — vendored OpenAI Whisper text normalizer

Vendored verbatim from https://github.com/openai/whisper at pinned upstream tag `v20240930`,
upstream paths `whisper/normalizers/{__init__.py,basic.py,english.py,english.json}` and the
repository root `LICENSE`. License: MIT (Copyright (c) 2022 OpenAI; full text in `LICENSE`
alongside this file).

Recorded on 2026-09-03. No byte of any file below was modified in the copy from upstream into
this directory; `english.py`'s relative import of `.basic` and its `os.path.join(os.path.dirname(
__file__), "english.json")` lookup are preserved unchanged and resolve correctly because all four
files stay together in this same package directory.

Per-file SHA-256 (upstream bytes, re-verified against these vendored copies by
`tests/unit/test_whisper_normalizer_vendored.py`):

| File | SHA-256 |
| --- | --- |
| `__init__.py` | `f18fcdce4caee7f2e80e4c01ab0457d3a080a872a29489542c6d23c4b0bba572` |
| `basic.py` | `ad567b3a0e1d03ccc0c35fc746fd6830c35290fe4ed7674eb61ce157ba3d380d` |
| `english.py` | `2898e4672aeefc9f44cb4de38c115cdf286f5b35ae321433467a7674ce8841d0` |
| `english.json` | `6607f948be9824d2e1b2fa2223cd94c06c45afa4e05ea0e3d5e1f2bdffde2465` |
| `LICENSE` | `b5d65a59060e68c4ff940e1eddfa6f94b2d68fdf58ed7f4dd57721c997e35e9d` |

## Why vendored, not a dependency

This package is used only as the field-standard text normalizer for reporting Earnings-21/22 WER
in the convention most published ASR papers on these corpora use, alongside — never in place of —
this study's own frozen `saea-scoring-v1` stack (`scoring/normalize.py`, E0 D3 freeze). Vendoring a
small, pinned, read-only copy keeps that reporting reproducible without adding an `openai-whisper`
package dependency (which pulls in torch/ffmpeg/audio-model code this study never runs) and without
letting the comparison drift if upstream changes its normalization rules. `regex` and
`more_itertools`, the two third-party imports `basic.py`/`english.py` make, are already study
dependencies.

## Boundary

This directory is read-only, upstream-authored code: it is never edited in place, and this
study's own runtime/scoring logic never modifies it. `reproduction/asr_wer_whisper.py` is the only
consumer, importing `EnglishTextNormalizer` from this package's `__init__.py` exactly as upstream
exports it.
