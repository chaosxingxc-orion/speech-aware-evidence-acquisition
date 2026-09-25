"""A restarted resident session keeps prior manifest-bound receipt bytes available."""
from dataclasses import replace
import hashlib

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.artifacts import _verify_artifact
from speech_aware_evidence_acquisition.core.session import (
    ModelFileRef, SessionError, SessionReceipt, write_session_receipt,
)
from speech_aware_evidence_acquisition.core.session.receipt import (
    archived_session_receipt_path,
)


def _receipt(pid):
    return SessionReceipt(
        schema="saea-session-receipt-v1", study=STUDY_SLUG,
        session_id="SAEA-SESSION-ARCHIVE-TEST", binary_path="llama-server",
        binary_sha256="a" * 64, argv=("llama-server",), pid=pid,
        host="127.0.0.1", port=8080,
        model_files=(ModelFileRef("model.gguf", "b" * 64),),
        started_at="2026-09-25T00:00:00Z", startup_stdout_sha256="c" * 64,
    )


def test_restart_archives_exact_old_bytes_and_bundle_can_resolve_them(tmp_path):
    path = tmp_path / "session.json"
    write_session_receipt(path, _receipt(101))
    old = path.read_bytes()
    digest = hashlib.sha256(old).hexdigest()
    write_session_receipt(path, _receipt(202))

    archive = archived_session_receipt_path(path, digest)
    assert archive.read_bytes() == old
    assert path.read_bytes() != old
    assert _verify_artifact({"path": str(path), "sha256": digest}, "session receipt") == old
    path.unlink()
    assert _verify_artifact({"path": str(path), "sha256": digest}, "session receipt") == old
    write_session_receipt(path, _receipt(202))
    assert _verify_artifact(
        {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
        "session receipt",
    ) == path.read_bytes()


@pytest.mark.parametrize("damage", ["missing", "tampered"])
def test_missing_or_tampered_archive_refused(tmp_path, damage):
    path = tmp_path / "session.json"
    write_session_receipt(path, _receipt(101))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    write_session_receipt(path, _receipt(202))
    archive = archived_session_receipt_path(path, digest)
    if damage == "missing":
        archive.unlink()
    else:
        archive.write_bytes(b"tampered")
    with pytest.raises(BundleError):
        _verify_artifact({"path": str(path), "sha256": digest}, "session receipt")


def test_archive_collision_refuses_replacement_without_changing_resident(tmp_path):
    path = tmp_path / "session.json"
    write_session_receipt(path, _receipt(101))
    old = path.read_bytes()
    digest = hashlib.sha256(old).hexdigest()
    archive = archived_session_receipt_path(path, digest)
    archive.parent.mkdir()
    archive.write_bytes(b"collision")
    with pytest.raises(SessionError):
        write_session_receipt(path, _receipt(202))
    assert path.read_bytes() == old
    assert archive.read_bytes() == b"collision"
    assert not list(tmp_path.glob("session.json.tmp-*"))


def test_non_session_artifacts_never_use_receipt_archive(tmp_path):
    path = tmp_path / "session.json"
    write_session_receipt(path, _receipt(101))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    write_session_receipt(path, _receipt(202))
    for label in ("outputs", "raw trace", "trace manifest"):
        with pytest.raises(BundleError):
            _verify_artifact({"path": str(path), "sha256": digest}, label)
