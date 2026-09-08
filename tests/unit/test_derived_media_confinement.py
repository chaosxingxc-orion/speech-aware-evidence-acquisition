"""Derived-media confinement (2026-09-07 defect repair).

Every cross-carrier derived-media population -- the ``@ts2`` silence-tail
variants, the 16 kHz input-rate variants, the ESB utterance cuts -- writes its
files under ``<data_root>/derived/<variant>/`` and names them from its own
dataset fragment, which also carries the hash-pinned D1 media supplement that
vouches for them. ``core.model._enforce_payload_binding`` confined every
payload to the CARRIER root alone, so each such row was refused ("escapes its
confined root") the moment a real request was built -- while the preflights and
the zero-socket wire checks passed, because neither ever builds a payload.

The repair adds ``core.base.PayloadBindingContext.derived_media_roots``,
populated only from the fragment's declared derived-subdir keys, and accepts a
relpath confined under the carrier root OR under one of those roots -- always
AFTER the I4 exact-relpath check, so the set of files a payload may name is
still exactly one: the file this run's verified split names for that sample id.

The four cases the repair must hold, in this file's order:

(a) a carrier-root row still passes, and a decoy under the carrier root still
    fails exactly as before;
(b) a derived row passes only when its fragment declares the root AND the
    relpath equals the verified one;
(c) a derived relpath whose fragment declares no derived root fails;
(d) a declared root outside ``derived/`` or outside ``data_root`` is refused at
    binding construction.
"""

import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import (
    CoreError,
    PayloadBindingContext,
    declared_derived_media_roots,
)
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter, FrozenCoreError
from speech_aware_evidence_acquisition.core.tracing import TraceSink

REPO_ROOT = Path(__file__).resolve().parents[2]

CARRIER_RELPATH = "datasets/earnings21-22/earnings22/media/5000001.mp3"
DERIVED_SUBDIR = "derived/e22-esb-utterances/dev1500-tail2s-v1"
DERIVED_RELPATH = f"{DERIVED_SUBDIR}/5000001@ts2.mp3"


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        return None


def _plan(**overrides):
    base = dict(
        run_id="SAEA-E-000-derived",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings22-original",
        split_role="dev",
        split_identity_hash="a" * 64,
        planned_model_calls=3,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=250,
        protocol_hash="b" * 64,
        attempt_id="attempt-0001",
    )
    base.update(overrides)
    return ExecutionPlan(**base)


def _payload(media_relpath=CARRIER_RELPATH, **overrides):
    payload = {
        "request_id": "req-1",
        "carrier_lock_key": "earnings22-original",
        "sample_id": "5000001",
        "speech_ref": "earnings22-original/5000001",
        "media_relpath": media_relpath,
        "audio_seconds": 100.0,
        "sample_rate_hz": 16000,
        "task_instruction": "Transcribe the speech verbatim.",
        "history": [],
        "decoding_params": {"temperature": 0, "seed": 20260803},
    }
    payload.update(overrides)
    return payload


def _fake_transport(request_bytes):
    assert isinstance(request_bytes, bytes)
    return json.dumps(
        {"text": "hello world", "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
    ).encode()


def _materialize(tmp_path, *relpaths):
    """A real data root with real bytes at each relpath: the adapter resolves
    strict=True, so confinement can only be exercised against files that
    actually exist.

    The carrier root is always created, even for a run whose media is entirely
    derived. Every confinement root must itself resolve -- an unavailable root
    is a hard refusal, never quietly skipped in favour of the next one -- which
    matches production, where a carrier's pinned asset directory always exists.
    """

    data_root = tmp_path / "data"
    (data_root / "datasets" / "earnings21-22" / "earnings22").mkdir(parents=True)
    for relpath in relpaths:
        path = data_root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake-mp3-bytes-" + relpath.encode())
    return data_root


def _binding(data_root, *, media_relpath, derived_media_roots=()):
    return PayloadBindingContext(
        carrier_lock_key="earnings22-original",
        allowed_sample_ids=frozenset({"5000001"}),
        sample_facts={"5000001": (100.0, 16000)},
        data_root=data_root,
        carrier_root=data_root / "datasets" / "earnings21-22" / "earnings22",
        media_relpaths={"5000001": media_relpath},
        derived_media_roots=tuple(derived_media_roots),
    ).validate()


def _adapter(tmp_path, binding):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-derived")
    return FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=_plan(),
        arm="bare-core",
        transport=_fake_transport,
        sink=sink,
        binding=binding,
    )


def _fragment(**overrides):
    """A composed-config shape carrying a SLURP-spelled derived declaration."""

    values = {
        "derived_media_subdir": DERIVED_SUBDIR,
        "d1_media_supplement": "receipts/artifacts/d1-e22-esb-dev1500-tail2s.json",
        "d1_media_supplement_sha256": "6" * 64,
    }
    values.update(overrides)
    return values


# ---------------------------------------------------------------------------
# (a) The carrier-root path is untouched.
# ---------------------------------------------------------------------------


def test_carrier_root_row_still_passes(tmp_path):
    data_root = _materialize(tmp_path, CARRIER_RELPATH)
    binding = _binding(data_root, media_relpath=CARRIER_RELPATH)
    assert binding.derived_media_roots == ()
    response = _adapter(tmp_path, binding).request(_payload())
    assert response.text == "hello world"


def test_decoy_under_the_carrier_root_still_fails(tmp_path):
    """The IMPORTANT A decoy: a file that IS confinement-legal under the
    carrier root but is not the one the verified split names. Unchanged by the
    repair -- it is refused by the I4 exact-relpath check, which still runs
    first."""

    decoy = "datasets/earnings21-22/earnings22/media/decoy.mp3"
    data_root = _materialize(tmp_path, CARRIER_RELPATH, decoy)
    binding = _binding(data_root, media_relpath=CARRIER_RELPATH)
    with pytest.raises(FrozenCoreError, match="I4 exact media-relpath binding"):
        _adapter(tmp_path, binding).request(_payload(media_relpath=decoy))


def test_a_declared_derived_root_does_not_legalize_a_carrier_root_decoy(tmp_path):
    """The widening must not reopen the decoy hole: with a derived root
    declared, a decoy under the CARRIER root is refused exactly as before."""

    decoy = "datasets/earnings21-22/earnings22/media/decoy.mp3"
    data_root = _materialize(tmp_path, DERIVED_RELPATH, decoy)
    binding = _binding(
        data_root,
        media_relpath=DERIVED_RELPATH,
        derived_media_roots=(data_root / DERIVED_SUBDIR,),
    )
    with pytest.raises(FrozenCoreError, match="I4 exact media-relpath binding"):
        _adapter(tmp_path, binding).request(_payload(media_relpath=decoy))


# ---------------------------------------------------------------------------
# (b) A derived row passes only with the declared root AND the verified relpath.
# ---------------------------------------------------------------------------


def test_derived_row_passes_when_the_root_is_declared(tmp_path):
    data_root = _materialize(tmp_path, DERIVED_RELPATH)
    binding = _binding(
        data_root,
        media_relpath=DERIVED_RELPATH,
        derived_media_roots=(data_root / DERIVED_SUBDIR,),
    )
    response = _adapter(tmp_path, binding).request(_payload(media_relpath=DERIVED_RELPATH))
    assert response.text == "hello world"


def test_decoy_inside_the_declared_derived_root_is_refused(tmp_path):
    """Only the verified relpath, never merely "some file under the declared
    derived root" -- the same rule the carrier root has always had."""

    decoy = f"{DERIVED_SUBDIR}/decoy@ts2.mp3"
    data_root = _materialize(tmp_path, DERIVED_RELPATH, decoy)
    binding = _binding(
        data_root,
        media_relpath=DERIVED_RELPATH,
        derived_media_roots=(data_root / DERIVED_SUBDIR,),
    )
    with pytest.raises(FrozenCoreError, match="I4 exact media-relpath binding"):
        _adapter(tmp_path, binding).request(_payload(media_relpath=decoy))


def test_a_declared_root_does_not_legalize_a_different_derived_variant(tmp_path):
    """Declaring one variant's root never legalizes a sibling variant's."""

    sibling = "derived/e22-esb-utterances/dev1500-pad30s-v1/5000001@pad.mp3"
    data_root = _materialize(tmp_path, DERIVED_RELPATH, sibling)
    binding = _binding(
        data_root,
        media_relpath=sibling,
        derived_media_roots=(data_root / DERIVED_SUBDIR,),
    )
    with pytest.raises(FrozenCoreError, match="escapes its confined root"):
        _adapter(tmp_path, binding).request(_payload(media_relpath=sibling))


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink required")
def test_symlink_out_of_a_declared_derived_root_is_refused(tmp_path):
    """Confinement still resolves symlinks: a link inside the declared derived
    root pointing outside the data root is refused even though its leaf
    exists."""

    data_root = _materialize(tmp_path, DERIVED_RELPATH)
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"outside-bytes")
    link_relpath = f"{DERIVED_SUBDIR}/linked@ts2.mp3"
    (data_root / link_relpath).symlink_to(outside)
    binding = _binding(
        data_root,
        media_relpath=link_relpath,
        derived_media_roots=(data_root / DERIVED_SUBDIR,),
    )
    with pytest.raises(FrozenCoreError, match="escapes its confined root"):
        _adapter(tmp_path, binding).request(_payload(media_relpath=link_relpath))


# ---------------------------------------------------------------------------
# (c) A derived relpath with no declared root fails -- the reproduced defect.
# ---------------------------------------------------------------------------


def test_derived_relpath_without_a_declared_root_is_refused(tmp_path):
    """The 2026-09-07 failure reproduced: the verified split's own relpath, the
    real file present, and still refused, because nothing declared the root."""

    data_root = _materialize(tmp_path, DERIVED_RELPATH)
    binding = _binding(data_root, media_relpath=DERIVED_RELPATH)
    with pytest.raises(FrozenCoreError, match="escapes its confined root"):
        _adapter(tmp_path, binding).request(_payload(media_relpath=DERIVED_RELPATH))


# ---------------------------------------------------------------------------
# (d) An illegal declared root refuses at binding construction.
# ---------------------------------------------------------------------------


def test_declared_root_outside_derived_is_refused_at_construction(tmp_path):
    data_root = _materialize(tmp_path, CARRIER_RELPATH)
    with pytest.raises(CoreError, match="derived media root"):
        _binding(
            data_root,
            media_relpath=CARRIER_RELPATH,
            derived_media_roots=(data_root / "datasets" / "earnings21-22",),
        )


def test_declared_root_outside_data_root_is_refused_at_construction(tmp_path):
    data_root = _materialize(tmp_path, CARRIER_RELPATH)
    with pytest.raises(CoreError, match="beneath data_root"):
        _binding(
            data_root,
            media_relpath=CARRIER_RELPATH,
            derived_media_roots=(tmp_path / "derived" / "elsewhere-v1",),
        )


def test_the_bare_derived_directory_is_not_a_legal_root(tmp_path):
    """``<data_root>/derived`` itself would legalize EVERY variant at once; a
    root must name one variant directory."""

    data_root = _materialize(tmp_path, CARRIER_RELPATH)
    with pytest.raises(CoreError, match="derived media root"):
        _binding(
            data_root,
            media_relpath=CARRIER_RELPATH,
            derived_media_roots=(data_root / "derived",),
        )


def test_declared_roots_must_be_paths(tmp_path):
    data_root = _materialize(tmp_path, CARRIER_RELPATH)
    with pytest.raises(CoreError, match="must contain Path objects"):
        _binding(
            data_root,
            media_relpath=CARRIER_RELPATH,
            derived_media_roots=(str(data_root / DERIVED_SUBDIR),),
        )


# ---------------------------------------------------------------------------
# The fragment reader: what may become a declared root at all.
# ---------------------------------------------------------------------------


def test_a_fragment_without_a_derived_key_declares_nothing():
    assert declared_derived_media_roots({"carrier_lock_key": "slurp"}, Path("/data")) == ()


@pytest.mark.parametrize(
    "subdir_key,path_key,digest_key",
    [
        ("derived_media_subdir", "d1_media_supplement", "d1_media_supplement_sha256"),
        (
            "a2t_calibration_derived_subdir",
            "a2t_calibration_d1_media_supplement",
            "a2t_calibration_d1_media_supplement_sha256",
        ),
        ("e22_esb_derived_subdir", "d1_media_supplement", "d1_media_supplement_sha256"),
    ],
)
def test_each_carrier_key_spelling_is_read(subdir_key, path_key, digest_key):
    values = {
        subdir_key: DERIVED_SUBDIR,
        path_key: "receipts/artifacts/d1-x.json",
        digest_key: "7" * 64,
    }
    assert declared_derived_media_roots(values, Path("/data")) == (
        Path("/data") / DERIVED_SUBDIR,
    )


def test_a_derived_root_without_a_d1_media_supplement_is_refused():
    values = {"derived_media_subdir": DERIVED_SUBDIR}
    with pytest.raises(CoreError, match="no D1 media supplement"):
        declared_derived_media_roots(values, Path("/data"))


def test_a_prose_supplement_without_a_digest_is_refused():
    """Several sealed fragments carry the supplement key as prose explaining
    why they need none; a declared derived root may never ride on that."""

    values = {
        "a2t_calibration_derived_subdir": DERIVED_SUBDIR,
        "a2t_calibration_d1_media_supplement": "none, by design. All 400 ids are in D1.",
    }
    with pytest.raises(CoreError, match="no D1 media supplement"):
        declared_derived_media_roots(values, Path("/data"))


def test_a_supplement_with_a_malformed_digest_is_refused():
    values = _fragment(d1_media_supplement_sha256="not-a-digest")
    with pytest.raises(CoreError, match="lowercase 64-hex"):
        declared_derived_media_roots(values, Path("/data"))


@pytest.mark.parametrize(
    "subdir",
    [
        "datasets/slurp/slurp_real",
        "/derived/x-v1",
        "derived",
        "derived/../datasets",
        "derived\\x-v1",
        "",
    ],
)
def test_an_illegal_declared_subdir_is_refused(subdir):
    with pytest.raises(CoreError):
        declared_derived_media_roots(_fragment(derived_media_subdir=subdir), Path("/data"))


# ---------------------------------------------------------------------------
# The rails builder threads the roots into the context it constructs.
# ---------------------------------------------------------------------------


def test_build_payload_binding_carries_the_declared_roots(tmp_path):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.rails.core_client import build_payload_binding

    data_root = _materialize(tmp_path, DERIVED_RELPATH)
    sample = SimpleNamespace(
        sample_id="5000001",
        audio_ref=SimpleNamespace(path=DERIVED_RELPATH),
        audio_seconds=100.0,
    )
    binding = build_payload_binding(
        carrier_lock_key="earnings22-original",
        samples=[sample],
        data_root=data_root,
        carrier_root=data_root / "datasets" / "earnings21-22" / "earnings22",
        derived_media_roots=declared_derived_media_roots(
            _fragment(derived_media_subdir=DERIVED_SUBDIR), data_root
        ),
        sample_rate_prober=lambda _path: 16000,
    )
    assert binding.derived_media_roots == (data_root / DERIVED_SUBDIR,)
    assert _adapter(tmp_path, binding).request(
        _payload(media_relpath=DERIVED_RELPATH)
    ).text == "hello world"


def test_build_payload_binding_defaults_to_no_declared_roots(tmp_path):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.rails.core_client import build_payload_binding

    data_root = _materialize(tmp_path, CARRIER_RELPATH)
    sample = SimpleNamespace(
        sample_id="5000001",
        audio_ref=SimpleNamespace(path=CARRIER_RELPATH),
        audio_seconds=100.0,
    )
    binding = build_payload_binding(
        carrier_lock_key="earnings22-original",
        samples=[sample],
        data_root=data_root,
        carrier_root=data_root / "datasets" / "earnings21-22" / "earnings22",
        sample_rate_prober=lambda _path: 16000,
    )
    assert binding.derived_media_roots == ()


# ---------------------------------------------------------------------------
# The real fragments this repair exists for.
# ---------------------------------------------------------------------------


def _real_fragment(name):
    path = REPO_ROOT / "configs" / "dataset" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name,expected",
    [
        ("slurp-speech-native-dev1000-tail2s", "derived/slurp-dev1000-tail2s-v1"),
        ("audio2tool-calibration-400-tail2s", "derived/a2t-calibration-400-tail2s-v1"),
        ("audio2tool-calibration-400-16k", "derived/a2t-calibration-400-16k-v1"),
        (
            "audio2tool-calibration-400-16k-tail2s",
            "derived/a2t-calibration-400-16k-tail2s-v1",
        ),
    ],
)
def test_the_real_derived_fragments_declare_their_root(name, expected):
    roots = declared_derived_media_roots(_real_fragment(name), Path("/data"))
    assert roots == (Path("/data") / expected,)


def test_the_comparator_fragment_declares_no_derived_root():
    values = _real_fragment("slurp-speech-native-dev1000")
    assert declared_derived_media_roots(values, Path("/data")) == ()


def test_every_shipped_fragment_with_a_derived_key_still_resolves():
    """Regression fence: the reader is fail-closed, so a fragment that used to
    fly must not start refusing at binding construction."""

    declared = 0
    for path in sorted((REPO_ROOT / "configs" / "dataset").glob("*.json")):
        values = json.loads(path.read_text(encoding="utf-8"))
        if declared_derived_media_roots(values, Path("/data")):
            declared += 1
    assert declared >= 20
