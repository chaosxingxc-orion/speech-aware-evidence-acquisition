"""Stage-3 item S3-1: the SLURP-STAGE3-CONSTRUCTION-R01 preparation registrations.

Two model-free registrations are covered here:

* the ``stage3-construction-r01`` roster of the generalized SLURP packet
  preprocessing driver ``scripts/slurp_evo_fold_preprocess.py``
  (``SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS``, the ENCODE + PROMOTE
  preparation cell ROLL-1's ``speech_packet_promotion_receipt`` placeholder
  waits for); and
* the roster-identity fallback of
  ``scripts/build_speech_query_source_inventory.py``, which the
  ``SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1`` protocol's
  ``sources`` inventory is built with.

Zero model / encoder / tokenizer / network / GPU contact and no audio read:
every assertion reads committed config fragments through ``core.config.compose``
or exercises a pure function against synthetic dictionaries.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (":" + _existing_pythonpath if _existing_pythonpath else "")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


preprocess = _load("slurp_evo_fold_preprocess_s3", "scripts/slurp_evo_fold_preprocess.py")
inventory = _load("build_speech_query_source_inventory_s3", "scripts/build_speech_query_source_inventory.py")


# ---------------------------------------------------------------------------
# The ENCODE + PROMOTE roster registration.
# ---------------------------------------------------------------------------


def test_stage3_roster_carries_the_train_prefix_discovery_role_and_own_run_id() -> None:
    spec = preprocess.PREPROCESS_ROSTERS["stage3-construction-r01"]
    assert spec.run_id == "SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS"
    assert spec.dataset_fragment == "slurp-speech-native-stage3-construction-r01"
    assert spec.experiment_fragment == "slurp-stage3-construction-r01-preprocess"
    assert spec.sample_id_prefix == "slurp:train:"
    assert spec.split_role == "discovery"
    assert spec.promotion_receipt_name == "STAGE3-CONSTRUCTION-R01-promotion.json"
    assert spec.default_attempt_id == "attempt-packets-stage3-construction-r01-v1"
    assert (spec.plan_calls, spec.plan_speech_seconds, spec.plan_gpu_hours) == (800, 3492, 1.0)


def test_stage3_roster_is_not_part_of_the_two_fold_union_receipt() -> None:
    assert "stage3-construction-r01" not in preprocess.FOLD_ROSTER_KEYS


def test_stage3_roster_promotion_receipt_resolves_under_the_resident_packet_root() -> None:
    spec = preprocess.PREPROCESS_ROSTERS["stage3-construction-r01"]
    resolved = preprocess._resolve_promotion_receipt(
        {}, spec, preprocess.DEFAULT_FEATURE_ROOT, "stage3-construction-r01"
    )
    assert resolved == preprocess.DEFAULT_FEATURE_ROOT / "STAGE3-CONSTRUCTION-R01-promotion.json"


def test_stage3_composed_config_names_the_run_id_and_carries_800_train_rows() -> None:
    spec = preprocess.PREPROCESS_ROSTERS["stage3-construction-r01"]
    values = preprocess.compose(
        preprocess.REPO, preprocess.MODEL_FRAGMENT, spec.dataset_fragment,
        preprocess.BASELINE_FRAGMENT, spec.experiment_fragment,
    ).values
    assert str(values["experiment_id"]) == spec.run_id
    assert values.get("split_role") == spec.split_role
    assert values.get("execution_profile") == "bounded-discovery-probe"
    assert int(values["count"]) == 800
    items = values["items"]
    assert len(items) == 800
    assert all(str(item["sample_id"]).startswith("slurp:train:") for item in items)
    # The declared ceiling covers the roster: one contact per row, and the
    # whole roster's audio seconds rounded up.
    assert spec.plan_calls == len(items)
    assert spec.plan_speech_seconds >= float(values["audio_seconds_total"])


def test_stage3_roster_rejects_a_devel_row_prefix() -> None:
    spec = preprocess.PREPROCESS_ROSTERS["stage3-construction-r01"]
    view = {
        "schema": "saea-speech-native-runtime-view-v1",
        "count": 1,
        "items": [{"sample_id": "slurp:devel:000001:audio-1", "media_relpath": "x", "audio_sha256": "0" * 64, "audio_seconds": 1.0}],
    }
    with pytest.raises(SystemExit):
        preprocess.roster_samples(view, Path("/nonexistent"), 1, spec.sample_id_prefix, "stage3-construction-r01")


# ---------------------------------------------------------------------------
# The roster-identity fallback of the speech-query source inventory builder.
# ---------------------------------------------------------------------------


def test_inventory_reads_the_id_extra_when_the_roster_receipt_declares_one() -> None:
    receipt = {"items": [{"sample_id": "slurp:devel:1:a", "id": "slurp:devel:1:a"},
                         {"sample_id": "slurp:devel:2:b", "id": "slurp:devel:2:b"}]}
    assert inventory.roster_sample_ids(receipt) == {"slurp:devel:1:a", "slurp:devel:2:b"}


def test_inventory_falls_back_to_sample_id_for_a_receipt_without_an_id_extra() -> None:
    # The SLURP-STAGE3-CONSTRUCTION-R01 shape: freeze_roster identity plus the
    # farthest-point draw extras, and no 'id'.
    receipt = {
        "items": [
            {"sample_id": "slurp:train:1:a", "stratum": "alarm", "draw_rank": 0, "min_cosine_to_selected": 0.5},
            {"sample_id": "slurp:train:2:b", "stratum": "audio", "draw_rank": 1, "min_cosine_to_selected": 0.4},
        ]
    }
    assert inventory.roster_sample_ids(receipt) == {"slurp:train:1:a", "slurp:train:2:b"}


def test_inventory_refuses_a_receipt_row_with_no_sample_identity_at_all() -> None:
    with pytest.raises(SystemExit):
        inventory.roster_sample_ids({"items": [{"stratum": "alarm"}]})


def test_inventory_refuses_an_empty_sample_identity() -> None:
    with pytest.raises(SystemExit):
        inventory.roster_sample_ids({"items": [{"sample_id": ""}]})


def test_the_committed_stage3_roster_receipt_needs_the_fallback() -> None:
    """Regression anchor: the committed R01 receipt carries no 'id' extra, so
    the pre-fallback builder raised KeyError before reading a single byte."""

    import json

    receipt = json.loads(
        (REPO / "docs" / "receipts" / "rosters" / "slurp-stage3-construction-r01.json").read_text(encoding="utf-8")
    )
    assert receipt["roster_id"] == "SLURP-STAGE3-CONSTRUCTION-R01"
    assert all("id" not in item for item in receipt["items"])
    assert len(inventory.roster_sample_ids(receipt)) == 800
