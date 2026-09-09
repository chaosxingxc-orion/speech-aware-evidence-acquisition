"""``rails.core_client.media_identity_stage`` -- the wire checks' third stage.

A cell is wire-ready only if it BINDS **and** is IDENTITY-CLOSED. Payload
confinement (``payload_binding_stage``) reads the carrier-prefixed derived-root
declaration; media identity reads the plain D1 supplement pair. Six Audio2Tool
fragments carried only the first, so every wire check was green while the
identity gate saw no supplement at all and the first real request refused
every roster id (2026-09-09, ``docs/readiness/
2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md``).

Model-free, zero sockets, zero servers, zero model contacts. **No gold label,
reference transcript, tool name, sealed output or score is read.**
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts.gate_media_identity import (
    _no_d1_media_identity,
)
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.core_client import media_identity_stage

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = REPO_ROOT / "docs" / "receipts"
CARRIER = "audio2tool"
SUPPLEMENT = "receipts/artifacts/d1-a2t-calibration-400-16k.json"

pytestmark = pytest.mark.skipif(
    not (RECEIPTS / "e0-closure.json").is_file(),
    reason="E0 closure receipts not landed in this checkout",
)


@dataclass(frozen=True)
class _AudioRef:
    path: str


@dataclass(frozen=True)
class _Sample:
    """The three fields ``rails.task_adapter.TaskSample`` exposes and the two
    stages actually read -- the same duck typing ``build_payload_binding``
    already documents."""

    sample_id: str
    audio_ref: _AudioRef
    audio_seconds: float


def _values(dataset: str = "audio2tool-calibration-400-16k-smoke4"):
    """The composed config of the ``@16k`` 4-row smoke cell, exactly as
    ``scripts/flights/run_calibration_cell.py::build_runtime`` composes it."""

    experiment = "a2t-official-protocol-16k-400-smoke-v1"
    document = json.loads(
        (REPO_ROOT / "configs" / "experiment" / f"{experiment}.json").read_text(
            encoding="utf-8"
        )
    )
    cell = next(
        item
        for item in document["cells"]
        if str(item["cell_id"]) == "R-official-16k-smoke-4"
    )
    return compose(
        REPO_ROOT,
        str(cell["model_fragment"]),
        dataset,
        str(cell["baseline_fragment"]),
        experiment,
    ).values


def _roster_ids() -> list[str]:
    document = json.loads(
        (REPO_ROOT / "configs/experiment/a2t-official-protocol-16k-400-smoke-v1.json")
        .read_text(encoding="utf-8")
    )
    return [str(sample_id) for sample_id in document["populations"][0]["ids"]]


def _supplement_entry(sample_id: str) -> dict:
    document = json.loads(
        (REPO_ROOT / "docs" / SUPPLEMENT).read_text(encoding="utf-8")
    )
    return next(entry for entry in document["manifest"] if entry["id"] == sample_id)


def test_an_identity_closed_cell_passes(tmp_path: Path) -> None:
    """Every roster id of the ``@16k`` smoke cell is inside D1's closure.

    The data root is a tmp path and ``samples`` is empty on purpose: this half
    of the stage opens no media file, so a 400- or 1,000-row roster costs
    nothing and the assertion is about the DECLARATION, not about whatever
    bytes happen to sit on this machine.
    """

    result = media_identity_stage(
        dataset_fragment="audio2tool-calibration-400-16k-smoke4",
        carrier_lock_key=CARRIER,
        values=_values(),
        repo_root=REPO_ROOT,
        data_root=tmp_path,
        runtime_root=tmp_path,
        roster_sample_ids=_roster_ids(),
        samples=(),
    )
    assert result.identity_closed is True
    assert result.refusal is None
    assert result.d1_media_supplement == SUPPLEMENT
    assert result.roster_ids_checked == 4
    # 400 sealed base-D1 audio2tool entries plus the 400 the supplement adds.
    assert result.closure_ids == 800
    assert result.model_contacts == 0 and result.sockets_opened == 0
    assert result.as_receipt()["identity_closed"] is True


@pytest.mark.skipif(
    os.environ.get("SPEECHRL_DATA_DIR") is None,
    reason="the byte half needs the controlled data root",
)
def test_an_identity_closed_cell_passes_on_real_media_bytes() -> None:
    """The expensive half, on ONE real row: the live file re-measures to the
    size and SHA-256 the D1 supplement recorded for
    ``tier1_direct:000045@16k`` -- the id the 2026-09-09 flight died on."""

    data_root = Path(os.environ["SPEECHRL_DATA_DIR"])
    entry = _supplement_entry("tier1_direct:000045@16k")
    if not (data_root / entry["media_relpath"]).is_file():
        pytest.skip("the @16k derived media is not materialized on this machine")
    result = media_identity_stage(
        dataset_fragment="audio2tool-calibration-400-16k-smoke4",
        carrier_lock_key=CARRIER,
        values=_values(),
        repo_root=REPO_ROOT,
        data_root=data_root,
        runtime_root=data_root,
        roster_sample_ids=_roster_ids(),
        samples=(
            _Sample(
                sample_id=str(entry["id"]),
                audio_ref=_AudioRef(str(entry["media_relpath"])),
                audio_seconds=float(entry["audio_seconds"]),
            ),
        ),
    )
    assert result.identity_closed is True, result.refusal
    assert result.rows_verified == ("tier1_direct:000045@16k",)


def test_a_supplement_blind_cell_fails_with_the_gates_own_sentence(
    tmp_path: Path,
) -> None:
    """The state the prefixed-only declaration produced: the gate is handed no
    supplement, and the stage reports the gate's OWN refusal sentence -- the
    exact line a flight would die on -- rather than a paraphrase."""

    values = dict(_values())
    del values["d1_media_supplement"]
    del values["d1_media_supplement_sha256"]
    del values["a2t_calibration_d1_media_supplement"]
    del values["a2t_calibration_d1_media_supplement_sha256"]
    result = media_identity_stage(
        dataset_fragment="audio2tool-calibration-400-16k-smoke4",
        carrier_lock_key=CARRIER,
        values=values,
        repo_root=REPO_ROOT,
        data_root=tmp_path,
        runtime_root=tmp_path,
        roster_sample_ids=_roster_ids(),
        samples=(),
    )
    assert result.identity_closed is False
    assert result.d1_media_supplement is None
    assert result.refusal == _no_d1_media_identity(_roster_ids()[0], CARRIER)


def test_a_prefixed_only_cell_fails_the_stage(tmp_path: Path) -> None:
    """A cell whose supplement is declared ONLY under the carrier-prefixed key
    is refused -- by ``core.config`` now, before a gate is even built -- and
    the stage REPORTS that refusal instead of exploding, so one bad cell never
    hides the state of the others in a wire-check receipt."""

    values = dict(_values())
    del values["d1_media_supplement"]
    del values["d1_media_supplement_sha256"]
    assert "a2t_calibration_d1_media_supplement_sha256" in values
    result = media_identity_stage(
        dataset_fragment="audio2tool-calibration-400-16k-smoke4",
        carrier_lock_key=CARRIER,
        values=values,
        repo_root=REPO_ROOT,
        data_root=tmp_path,
        runtime_root=tmp_path,
        roster_sample_ids=_roster_ids(),
        samples=(),
    )
    assert result.identity_closed is False
    assert result.d1_media_supplement is None
    assert "a2t_calibration_d1_media_supplement" in str(result.refusal)
    assert "identity closure" in str(result.refusal)


def test_a_foreign_id_on_an_otherwise_closed_cell_fails_the_stage(
    tmp_path: Path,
) -> None:
    """The roster half is checked over EVERY id, not just the loaded rows: one
    id outside the closure refuses the whole cell."""

    result = media_identity_stage(
        dataset_fragment="audio2tool-calibration-400-16k-smoke4",
        carrier_lock_key=CARRIER,
        values=_values(),
        repo_root=REPO_ROOT,
        data_root=tmp_path,
        runtime_root=tmp_path,
        roster_sample_ids=[*_roster_ids(), "tier1_direct:000045@forged"],
        samples=(),
    )
    assert result.identity_closed is False
    assert result.refusal == _no_d1_media_identity(
        "tier1_direct:000045@forged", CARRIER
    )
