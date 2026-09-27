"""The ``test-full`` preprocessing roster: registered, and refused today.

Owner decisions 99 (2026-09-22) and 107 (2026-09-23): the ONE complete official
SLURP test-split read happens at the end of Stage 3, and its preparations are
registered NOW and built ahead of time so the read waits on nothing. Preparation
1 of 3 is the featcache packet promotion, which
``scripts/slurp_evo_fold_preprocess.py`` drives.

The whole point of this module is the refusal. The roster is registered, its
plan numbers are measured rather than guessed, and every mode of the driver --
``--preflight-only`` and ``--promote-only`` included, neither of which builds a
``contracts.ExecutionPlan`` -- refuses it BEFORE the data root is opened, because
the committed owner-allowance receipt says ``pending-owner``. Nothing here
contacts a model, an encoder, a sidecar or a network, and no media file is read:
the refusal is proved by monkeypatching ``roster_samples`` to a landmine and
watching it never go off.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "slurp_evo_fold_preprocess.py"

# The script's own module-level guards require these before it can even be
# imported -- the pattern tests/unit/test_e33_preprocess_rosters.py already uses.
_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (
        ":" + _existing_pythonpath if _existing_pythonpath else ""
    )
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

_SPEC = importlib.util.spec_from_file_location("slurp_evo_fold_preprocess_test_full", SCRIPT)
assert _SPEC and _SPEC.loader
module = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = module
_SPEC.loader.exec_module(module)

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    FINAL_REPORT_SPLIT_ROLE,
    ExecutionScopeError,
)

ROSTER_KEY = "test-full"
RUN_ID = "SAEA-SN-TEST-FULL-PREPROCESS"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-test-full-13078-v1.json"
ALLOWANCE_RELPATH = "docs/receipts/owner/2026-09-23-slurp-test-split-allowance-v1.json"
RECORDINGS = 13078
UTTERANCES = 2974


@pytest.fixture()
def composed():
    spec = module.PREPROCESS_ROSTERS[ROSTER_KEY]
    return module.compose(
        module.REPO,
        module.MODEL_FRAGMENT,
        spec.dataset_fragment,
        module.BASELINE_FRAGMENT,
        spec.experiment_fragment,
    )


def test_the_roster_is_appended_at_the_end_of_the_table() -> None:
    """Appended, never inserted: the order is the registration order."""

    keys = list(module.PREPROCESS_ROSTERS)
    # ``test-sample-3010`` (owner decisions 151 and 156, 2026-09-27) was appended
    # after this roster; everything up to and including this roster is unmoved.
    assert keys == [
        "fold-a",
        "fold-b",
        "dev2000-added",
        "stage3-construction-r01",
        "stage3-construction-r01-recovery",
        "devel-remainder",
        "devel-remainder-np8-equivalence-4",
        ROSTER_KEY,
        "test-sample-3010",
    ]
    # The union receipt still covers the two TRAIN folds only.
    assert module.FOLD_ROSTER_KEYS == ("fold-a", "fold-b")


def test_the_roster_spec_is_exactly_what_was_registered() -> None:
    spec = module.PREPROCESS_ROSTERS[ROSTER_KEY]
    assert spec.run_id == RUN_ID
    assert spec.dataset_fragment == "slurp-speech-native-test-full"
    assert spec.experiment_fragment == "slurp-test-full-preprocess"
    assert spec.sample_id_prefix == "slurp:test:"
    assert spec.split_role == FINAL_REPORT_SPLIT_ROLE == "final-report"
    assert spec.promotion_receipt_name == "TEST-FULL-promotion.json"
    assert spec.default_attempt_id == "attempt-packets-test-full-v1"
    assert (spec.plan_calls, spec.plan_speech_seconds, spec.plan_gpu_hours) == (
        13078,
        36912,
        1.0,
    )


def test_no_other_roster_moved_or_grew_an_allowance() -> None:
    """A Stage-2 roster that declared an allowance would be refused by
    ``ExecutionPlan.validate``; none does, and none changed its role."""

    # The test SAMPLE roster is final-report by design and pins its OWN
    # allowance; tests/unit/test_slurp_test_sample_preparations.py covers it.
    final_report = {ROSTER_KEY, "test-sample-3010"}
    roles = {
        key: spec.split_role
        for key, spec in module.PREPROCESS_ROSTERS.items()
        if key not in final_report
    }
    assert set(roles.values()) == {"discovery", "dev"}
    for key, spec in module.PREPROCESS_ROSTERS.items():
        if key in final_report:
            continue
        values = module.compose(
            module.REPO,
            module.MODEL_FRAGMENT,
            spec.dataset_fragment,
            module.BASELINE_FRAGMENT,
            spec.experiment_fragment,
        ).values
        assert values.get("owner_allowance") is None


def test_the_plan_numbers_are_measured_from_the_committed_artifacts(composed) -> None:
    """calls = the roster's row count; speech seconds = ceil(measured audio)."""

    spec = module.PREPROCESS_ROSTERS[ROSTER_KEY]
    values = composed.values
    assert int(values["count"]) == len(values["items"]) == RECORDINGS
    assert spec.plan_calls == RECORDINGS
    measured = float(values["audio_seconds_total"])
    assert measured == 36911.9388125
    assert spec.plan_speech_seconds == math.ceil(measured) == 36912
    # 1.0 declared, 0.0 actually consumed: the sidecar runs -ngl 0
    # --no-mmproj-offload and leaves the GPU to the resident serving session.
    assert spec.plan_gpu_hours == 1.0

    roster = json.loads((REPO / ROSTER_RELPATH).read_text(encoding="utf-8"))
    assert len(roster["items"]) == RECORDINGS
    assert values["split_identity_hash"] == roster["split_identity_hash"]
    assert values["split_role"] == roster["split_role"] == FINAL_REPORT_SPLIT_ROLE
    assert (
        len({str(item["sample_id"]).rsplit(":", 1)[0] for item in roster["items"]})
        == UTTERANCES
    )


def test_the_composed_view_is_label_free_and_all_test_split(composed) -> None:
    values = composed.values
    assert values["experiment_id"] == RUN_ID
    assert values["execution_profile"] == "bounded-discovery-probe"
    allowed = {
        "sample_id",
        "media_relpath",
        "audio_sha256",
        "audio_seconds",
        "sample_rate_hz",
        "packet_id",
    }
    for item in values["items"]:
        assert set(item) == allowed
        assert str(item["sample_id"]).startswith("slurp:test:")
        assert item["packet_id"] == str(item["sample_id"]).replace(":", "/")


def test_the_fragment_pins_the_committed_allowance_bytes(composed) -> None:
    allowance = composed.values["owner_allowance"]
    assert set(allowance) == {"path", "sha256"}
    assert allowance["path"] == ALLOWANCE_RELPATH
    raw = (REPO / ALLOWANCE_RELPATH).read_bytes()
    assert allowance["sha256"] == hashlib.sha256(raw).hexdigest()
    document = json.loads(raw.decode("utf-8"))
    assert document["status"] == "pending-owner"
    assert RUN_ID in document["permitted_run_ids"]
    assert RUN_ID in document["preparation_run_ids"]
    assert document["split"]["split_identity_hash"] == composed.values["split_identity_hash"]


def _landmined(monkeypatch, tmp_path):
    """Every mode of ``main`` must refuse before it reads one media file."""

    def never(*args, **kwargs):  # pragma: no cover -- the point is it never runs
        raise AssertionError(
            "roster_samples was reached: the final-report roster opened the data "
            "root while the owner allowance is still pending"
        )

    monkeypatch.setattr(module, "roster_samples", never)
    monkeypatch.setattr(module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(module, "umbrella_lock_path", lambda *a, **k: tmp_path / "lock.json")
    monkeypatch.setattr(module, "load_lock", lambda path: {})


@pytest.mark.parametrize(
    "argv",
    [
        ["--roster", ROSTER_KEY, "--preflight-only"],
        ["--roster", ROSTER_KEY, "--run"],
        ["--roster", ROSTER_KEY, "--promote-only", "--attempt-id", "attempt-x-v1"],
    ],
)
def test_every_mode_is_refused_today_before_any_media_is_read(
    monkeypatch, tmp_path, argv
) -> None:
    _landmined(monkeypatch, tmp_path)
    with pytest.raises(ExecutionScopeError) as error:
        module.main(argv)
    message = str(error.value)
    assert "status is 'pending-owner', not 'authorised'" in message
    assert ALLOWANCE_RELPATH in message


def test_a_byte_drifted_allowance_is_refused_too(monkeypatch, tmp_path) -> None:
    """Flipping the receipt's status breaks the pin, on purpose.

    The owner's ruling therefore forces a visible, countersigned re-pin of this
    fragment rather than silently unlocking an already-registered plan.
    """

    _landmined(monkeypatch, tmp_path)
    spec = module.PREPROCESS_ROSTERS[ROSTER_KEY]
    real_compose = module.compose

    def drifted(*args, **kwargs):
        composed = real_compose(*args, **kwargs)
        values = dict(composed.values)
        values["owner_allowance"] = {
            "path": ALLOWANCE_RELPATH,
            "sha256": "0" * 64,
        }
        return type(composed)(
            values=values, config_hash=composed.config_hash, fragments=composed.fragments
        )

    monkeypatch.setattr(module, "compose", drifted)
    with pytest.raises(ExecutionScopeError) as error:
        module.main(["--roster", ROSTER_KEY, "--preflight-only"])
    assert "not the pinned" in str(error.value)
    assert spec.run_id == RUN_ID


def test_the_other_rosters_still_reach_their_own_preflight(monkeypatch, tmp_path) -> None:
    """The refusal is scoped to the final-report role and nothing else.

    A Stage-2 roster walks straight past the new guard and lands in
    ``roster_samples`` -- which is the landmine here, so its AssertionError is
    the proof that the guard did not fire.
    """

    _landmined(monkeypatch, tmp_path)
    with pytest.raises(AssertionError, match="roster_samples was reached"):
        module.main(["--roster", "dev2000-added", "--preflight-only"])
