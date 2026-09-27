"""A restarted resident session keeps prior manifest-bound receipt bytes available."""
import hashlib

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.artifacts import _verify_artifact
from speech_aware_evidence_acquisition.core.session import (
    ModelFileRef, SessionError, SessionReceipt, write_session_receipt,
)
from speech_aware_evidence_acquisition.core.session.receipt import (
    archived_session_receipt_path, resolve_pinned_session_receipt,
    store_session_receipt_bytes,
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
        archive.chmod(0o600)
        archive.write_bytes(b"tampered")
    with pytest.raises(BundleError):
        _verify_artifact({"path": str(path), "sha256": digest}, "session receipt")


def test_archive_collision_refuses_replacement_without_changing_resident(tmp_path):
    path = tmp_path / "session.json"
    write_session_receipt(path, _receipt(101))
    old = path.read_bytes()
    digest = hashlib.sha256(old).hexdigest()
    archive = archived_session_receipt_path(path, digest)
    archive.chmod(0o600)
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


def test_every_written_receipt_enters_the_store_before_it_goes_resident(tmp_path):
    path = tmp_path / "session.json"
    write_session_receipt(path, _receipt(101))
    first = path.read_bytes()
    archive = archived_session_receipt_path(path, hashlib.sha256(first).hexdigest())
    assert archive.read_bytes() == first
    assert not archive.stat().st_mode & 0o222  # read-only: never overwritten in place
    write_session_receipt(path, _receipt(101))  # identical bytes: idempotent, no collision
    assert sorted(entry.name for entry in archive.parent.iterdir()) == [archive.name]


def test_store_is_append_only_and_content_addressed(tmp_path):
    path = tmp_path / "session.json"
    stored = store_session_receipt_bytes(path, b"exact bytes")
    assert stored.name == hashlib.sha256(b"exact bytes").hexdigest() + ".json"
    assert store_session_receipt_bytes(path, b"exact bytes") == stored
    stored.chmod(0o600)
    stored.write_bytes(b"other bytes")
    with pytest.raises(SessionError, match="collision or tampering"):
        store_session_receipt_bytes(path, b"exact bytes")
    assert stored.read_bytes() == b"other bytes"


def test_legacy_resident_receipt_is_archived_when_replaced(tmp_path):
    # A receipt written before the store existed is only resident; a restart
    # of the same session id must keep its exact bytes resolvable by hash.
    path = tmp_path / "session.json"
    legacy = b'{"legacy": true}'
    path.write_bytes(legacy)
    digest = hashlib.sha256(legacy).hexdigest()
    write_session_receipt(path, _receipt(202))
    assert resolve_pinned_session_receipt(path, digest) == legacy


def test_unresolvable_pin_names_both_locations(tmp_path):
    path = tmp_path / "session.json"
    write_session_receipt(path, _receipt(101))
    lost = "d" * 64
    with pytest.raises(BundleError, match="resolves nowhere") as caught:
        _verify_artifact({"path": str(path), "sha256": lost}, "session receipt")
    assert str(archived_session_receipt_path(path, lost)) in str(caught.value)
