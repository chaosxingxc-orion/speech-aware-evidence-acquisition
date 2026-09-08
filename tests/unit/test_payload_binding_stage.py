"""``rails.core_client.payload_binding_stage`` -- the shared payload-binding
stage every wire check now runs between its request half and its seal half.

Follow-up closed here (``docs/readiness/2026-09-07-derived-media-
confinement-v1.md`` section 5): no model-free gate in this repository had
ever built a payload, which is why two preflights and a zero-socket wire
check all passed on a population whose payloads could not actually bind.
This stage builds a REAL ``core.base.PayloadBindingContext`` through the same
``build_payload_binding`` the driver itself uses -- over the real carrier
root, never a per-script ``carrier_root_resolver`` swap -- and drives the
production ``core.model.binding._enforce_payload_binding`` against a
synthetic payload for at least the first and last roster row.

Zero sockets, zero servers, zero model contacts throughout.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import AudioRef
from speech_aware_evidence_acquisition.rails.core_client import (
    PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT,
    FrozenCoreClientError,
    payload_binding_stage,
)

CARRIER_LOCK_KEY = "slurp-devel-fake"
FIXED_SAMPLE_RATE_HZ = 16000


@dataclass(frozen=True)
class _FakeSample:
    """Minimal ``rails.task_adapter.TaskSample`` duck type: exactly the three
    fields ``build_payload_binding`` reads (sample_id / audio_ref.path /
    audio_seconds), nothing else."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


def _fixed_sample_rate(_path: Path) -> int:
    """Never reads a real audio header -- this stage's own file-existence
    requirement (confinement resolves ``strict=True``) is exercised with
    placeholder bytes, and a real ``soundfile`` probe would refuse them."""

    return FIXED_SAMPLE_RATE_HZ


def _materialize(tmp_path: Path, carrier_subdir: str, *relpaths: str) -> Path:
    """A real data root with real (placeholder) bytes at each relpath --
    confinement resolves ``strict=True``, so it can only be exercised against
    files that actually exist."""

    data_root = tmp_path / "data"
    (data_root / carrier_subdir).mkdir(parents=True)
    for relpath in relpaths:
        path = data_root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake-audio-bytes-" + relpath.encode())
    return data_root


def _sample(sample_id: str, relpath: str, seconds: float = 12.0) -> _FakeSample:
    return _FakeSample(
        sample_id=sample_id,
        audio_ref=AudioRef(path=relpath, sha256="a" * 64),
        audio_seconds=seconds,
    )


def test_carrier_rooted_cell_binds(tmp_path: Path) -> None:
    carrier_subdir = "datasets/slurp"
    relpath = f"{carrier_subdir}/audio-1.flac"
    data_root = _materialize(tmp_path, carrier_subdir, relpath)
    samples = (_sample("s1", relpath),)

    result = payload_binding_stage(
        dataset_fragment="slurp-carrier-rooted-fixture",
        carrier_lock_key=CARRIER_LOCK_KEY,
        samples=samples,
        data_root=data_root,
        carrier_root=data_root / carrier_subdir,
        sample_rate_prober=_fixed_sample_rate,
    )

    assert result.bound is True
    assert result.failures == {}
    assert result.rows_checked == ("s1",)
    assert result.rows_total == 1
    assert result.sockets_opened == 0
    assert result.model_contacts == 0
    receipt = result.as_receipt()
    assert receipt["bound"] is True
    assert receipt["checked_every_row"] is True


def test_declared_derived_cell_binds(tmp_path: Path) -> None:
    carrier_subdir = "datasets/slurp"
    derived_subdir = "derived/slurp-dev1000-tail2s-v1"
    relpath = f"{derived_subdir}/audio-1@ts2.flac"
    data_root = _materialize(tmp_path, carrier_subdir, relpath)
    (data_root / derived_subdir).mkdir(parents=True, exist_ok=True)
    samples = (_sample("s1@ts2", relpath),)

    result = payload_binding_stage(
        dataset_fragment="slurp-derived-tail2s-fixture",
        carrier_lock_key=CARRIER_LOCK_KEY,
        samples=samples,
        data_root=data_root,
        carrier_root=data_root / carrier_subdir,
        derived_media_roots=(data_root / derived_subdir,),
        sample_rate_prober=_fixed_sample_rate,
    )

    assert result.bound is True
    assert result.failures == {}
    assert result.derived_media_roots == (data_root / derived_subdir,)


def test_undeclared_derived_root_fails_the_stage(tmp_path: Path) -> None:
    """The exact 2026-09-07 defect, reproduced: a payload naming a real file
    under a real derived root that THIS binding was never told about must be
    refused, never silently admitted."""

    carrier_subdir = "datasets/slurp"
    derived_subdir = "derived/slurp-dev1000-tail2s-v1"
    relpath = f"{derived_subdir}/audio-1@ts2.flac"
    data_root = _materialize(tmp_path, carrier_subdir, relpath)
    samples = (_sample("s1@ts2", relpath),)

    result = payload_binding_stage(
        dataset_fragment="slurp-undeclared-root-fixture",
        carrier_lock_key=CARRIER_LOCK_KEY,
        samples=samples,
        data_root=data_root,
        carrier_root=data_root / carrier_subdir,
        # derived_media_roots deliberately omitted: the fragment declares
        # nothing, exactly the pre-repair binding.
        sample_rate_prober=_fixed_sample_rate,
    )

    assert result.bound is False
    assert set(result.failures) == {"s1@ts2"}
    assert "escapes its confined root" in result.failures["s1@ts2"]


def test_checks_every_row_when_cheap(tmp_path: Path) -> None:
    carrier_subdir = "datasets/slurp"
    relpaths = [f"{carrier_subdir}/audio-{i}.flac" for i in range(4)]
    data_root = _materialize(tmp_path, carrier_subdir, *relpaths)
    samples = tuple(_sample(f"s{i}", relpaths[i]) for i in range(4))
    assert len(samples) <= PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT

    result = payload_binding_stage(
        dataset_fragment="slurp-smoke4-fixture",
        carrier_lock_key=CARRIER_LOCK_KEY,
        samples=samples,
        data_root=data_root,
        carrier_root=data_root / carrier_subdir,
        sample_rate_prober=_fixed_sample_rate,
    )

    assert result.rows_checked == tuple(f"s{i}" for i in range(4))
    assert result.rows_total == 4
    assert result.as_receipt()["checked_every_row"] is True


def test_checks_only_first_and_last_row_when_not_cheap(tmp_path: Path) -> None:
    carrier_subdir = "datasets/slurp"
    count = PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT + 1
    relpaths = [f"{carrier_subdir}/audio-{i}.flac" for i in range(count)]
    data_root = _materialize(tmp_path, carrier_subdir, *relpaths)
    samples = tuple(_sample(f"s{i}", relpaths[i]) for i in range(count))

    result = payload_binding_stage(
        dataset_fragment="slurp-full-fixture",
        carrier_lock_key=CARRIER_LOCK_KEY,
        samples=samples,
        data_root=data_root,
        carrier_root=data_root / carrier_subdir,
        sample_rate_prober=_fixed_sample_rate,
    )

    assert result.rows_checked == ("s0", f"s{count - 1}")
    assert result.rows_total == count
    assert result.bound is True
    assert result.as_receipt()["checked_every_row"] is False


def test_empty_roster_refuses(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    (data_root / "datasets" / "slurp").mkdir(parents=True)
    with pytest.raises(FrozenCoreClientError):
        payload_binding_stage(
            dataset_fragment="slurp-empty-fixture",
            carrier_lock_key=CARRIER_LOCK_KEY,
            samples=(),
            data_root=data_root,
            carrier_root=data_root / "datasets" / "slurp",
            sample_rate_prober=_fixed_sample_rate,
        )


def test_never_opens_a_socket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero sockets, proved rather than assumed: ``socket.socket`` is replaced
    with something that raises the instant it is constructed, and the stage
    must still complete -- for both a binding cell and a refusing one."""

    def _poisoned_socket(*_args, **_kwargs):
        raise AssertionError("payload_binding_stage opened a socket")

    monkeypatch.setattr(socket, "socket", _poisoned_socket)

    carrier_subdir = "datasets/slurp"
    derived_subdir = "derived/slurp-dev1000-tail2s-v1"
    carrier_relpath = f"{carrier_subdir}/audio-1.flac"
    derived_relpath = f"{derived_subdir}/audio-2@ts2.flac"
    data_root = _materialize(tmp_path, carrier_subdir, carrier_relpath, derived_relpath)

    bound_result = payload_binding_stage(
        dataset_fragment="slurp-socket-fixture-binds",
        carrier_lock_key=CARRIER_LOCK_KEY,
        samples=(_sample("s1", carrier_relpath),),
        data_root=data_root,
        carrier_root=data_root / carrier_subdir,
        sample_rate_prober=_fixed_sample_rate,
    )
    assert bound_result.bound is True

    refused_result = payload_binding_stage(
        dataset_fragment="slurp-socket-fixture-refuses",
        carrier_lock_key=CARRIER_LOCK_KEY,
        samples=(_sample("s2@ts2", derived_relpath),),
        data_root=data_root,
        carrier_root=data_root / carrier_subdir,
        # derived_media_roots omitted on purpose: this row must refuse.
        sample_rate_prober=_fixed_sample_rate,
    )
    assert refused_result.bound is False
