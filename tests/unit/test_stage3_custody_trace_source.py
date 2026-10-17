"""The ONE trace a row's contacts were sealed in (``_custody_trace_source``).

NX-T R1 rec2 (2026-10-17): request ids are attempt-scoped and repeat across attempts, so a
KEPT row of a resume completion must resolve its contacts in its predecessor's trace even
when the bundle's own trace carries the same request id for a different sample.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "stage3_custody_trace_source", ROOT / "scripts/analysis/stage3_rollout_score.py",
)
score = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(score)

OWN = {"flight-0026/request": {"payload_sha256": "own-req"}, "flight-0026/response": {"text": "own"}}
KEPT = {"flight-0026/request": {"payload_sha256": "kept-req"}, "flight-0026/response": {"text": "kept"}}
BUNDLE = SimpleNamespace(trace_records=OWN)


def test_a_kept_row_resolves_in_its_predecessor_trace_even_when_the_bundle_repeats_the_request_id():
    source = score._custody_trace_source(BUNDLE, {"kept-row": KEPT}, "kept-row")
    assert source is KEPT
    assert source["flight-0026/response"]["text"] == "kept"


def test_a_flown_row_resolves_in_the_bundle_s_own_trace():
    assert score._custody_trace_source(BUNDLE, {"kept-row": KEPT}, "flown-row") is OWN


def test_without_predecessors_every_row_resolves_in_the_bundle_s_own_trace():
    assert score._custody_trace_source(BUNDLE, None, "any") is OWN
    assert score._custody_trace_source(BUNDLE, {}, "any") is OWN
