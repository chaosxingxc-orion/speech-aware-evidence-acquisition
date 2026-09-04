"""Vendored Audio2Tool official evaluation code, pinned and unmodified.

Upstream: https://github.com/audio2tool/Audio2Tool
License: MIT, Copyright (c) 2026 Audio2Tool Authors (LICENSE at the pinned
commit). This package redistributes two upstream artifacts under that
license; the notice above travels with them.

Pinned commit: ``b9d5383ca30945fbafb965a04bea40117e1e8a82``
Clone receipt: ``docs/receipts/environments/audio2tool-official-code.json``

Contents:

* :mod:`.metrics` -- ``audio_benchmark/evaluation/metrics.py`` copied
  BYTE-FOR-BYTE (git blob SHA-1
  ``d98277bcf69795c9a0ae54e538c170abfd8c51ca``). Never edit it:
  ``tests/unit/test_audio2tool_official_scorer.py`` recomputes that blob
  hash from the bytes on disk and fails on any drift, which is the whole
  point of vendoring rather than reimplementing.
* :mod:`.parse` -- ``BaseAudioModel.parse_tool_call`` from
  ``audio_benchmark/models/base.py`` (git blob SHA-1
  ``977ce0cdde41b44b35ee2e6f43808d4eb16fec96``) as a module-level function,
  dedented one level with the bound ``self`` removed and nothing else
  changed. The same test re-applies that derivation against the local clone.

Why this package exists: the repository's paper-facing Audio2Tool number
must be the published benchmark's own metric, computed by the published
code, not by a reimplementation of its description. Everything specific to
THIS repository (reading a sealed outputs JSONL, resolving frozen-receipt
gold, per-tier aggregation) lives in
``reproduction.a2t_scorer.score_audio2tool_outputs_official``, outside this
package, so nothing here ever has to be edited.

Deliberately OUTSIDE the E0 D3 frozen scoring package
(``scoring/``), exactly like ``reproduction.toolcall_scoring``: this is
reproduction machinery pinned to a third party's release, not one of this
study's own frozen scoring primitives.
"""

from __future__ import annotations

AUDIO2TOOL_OFFICIAL_COMMIT = "b9d5383ca30945fbafb965a04bea40117e1e8a82"
AUDIO2TOOL_OFFICIAL_METRICS_BLOB_SHA1 = "d98277bcf69795c9a0ae54e538c170abfd8c51ca"
AUDIO2TOOL_OFFICIAL_BASE_BLOB_SHA1 = "977ce0cdde41b44b35ee2e6f43808d4eb16fec96"
AUDIO2TOOL_OFFICIAL_SCORER_VERSION = "a2t-scorer-official-b9d5383c"

__all__ = [
    "AUDIO2TOOL_OFFICIAL_BASE_BLOB_SHA1",
    "AUDIO2TOOL_OFFICIAL_COMMIT",
    "AUDIO2TOOL_OFFICIAL_METRICS_BLOB_SHA1",
    "AUDIO2TOOL_OFFICIAL_SCORER_VERSION",
]
