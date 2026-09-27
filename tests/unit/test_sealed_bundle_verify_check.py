"""The sealed-bundle session-receipt gate and the byte-exact receipt recovery.

``scripts/checks/sealed_bundle_verify_check.py`` resolves every run
manifest's pinned ``session_receipt`` exactly as ``verify_bundle`` does;
``scripts/session_receipt_recovery.py`` re-renders an overwritten resident
receipt from its attach record and ``server.log`` and stores it ONLY when the
rendered bytes hash to the pin. Both run here on a miniature data root in a
temporary directory: zero model, server, network and ``SPEECHRL_DATA_DIR``
contacts.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _path in (_REPO / "scripts" / "checks", _REPO / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import sealed_bundle_verify_check as gate  # noqa: E402
import session_receipt_recovery as recovery  # noqa: E402

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG  # noqa: E402
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    ModelFileRef,
    SessionReceipt,
)
from speech_aware_evidence_acquisition.core.session.receipt import (  # noqa: E402
    archived_session_receipt_path,
)

SESSION_ID = "serving-synthetic-np4-v1"
SECTION_ONE = b"0.00.001 I log_info: verbosity = 3\n0.00.002 I device_info:\n0.01.000 I ready\n"
SECTION_TWO = b"0.00.001 I log_info: verbosity = 3\n0.00.003 I second start\n"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _identity() -> dict:
    return {
        "binary_path": "llama/bin/llama-server",
        "binary_sha256": "a" * 64,
        "host": "127.0.0.1",
        "port": 8080,
        "model_files": [{"path": "models/core.gguf", "sha256": "b" * 64}],
        "server_argv": ["/root/llama/bin/llama-server", "--no-mmproj", "-np", "4"],
        "server_env": {"GGML_CUDA_DISABLE_GRAPHS": "1"},
        "session_role": "inference",
    }


def _receipt(session_dir: Path, *, pid: int, started_at: str, startup: bytes) -> bytes:
    identity = _identity()
    receipt = SessionReceipt(
        schema="saea-session-receipt-v2", study=STUDY_SLUG, session_id=SESSION_ID,
        binary_path=identity["binary_path"], binary_sha256=identity["binary_sha256"],
        argv=tuple(identity["server_argv"]), pid=pid, host="127.0.0.1", port=8080,
        model_files=(ModelFileRef("models/core.gguf", "b" * 64),),
        started_at=started_at, startup_stdout_sha256=_sha(startup),
        server_log_path=str(session_dir / "server.log"), role="inference",
        server_env_keys=("GGML_CUDA_DISABLE_GRAPHS",),
    ).validate()
    return recovery.render(receipt)


def _bundle(root: Path, run_id: str, pin_path: Path, pin_sha: str, *, pid=None, started_at=None):
    attempt = root / "runs" / run_id / "attempt-1"
    attempt.mkdir(parents=True)
    manifest = attempt / f"{run_id}.run-manifest.json"
    manifest.write_text(json.dumps({
        "schema": "saea-run-manifest-v1", "status": "COMPLETED",
        "session_receipt": {"path": str(pin_path), "sha256": pin_sha},
    }), encoding="utf-8")
    if pid is not None:
        (attempt / f"{run_id}-attempt-1.session-attach-receipt.json").write_text(json.dumps({
            "schema": "saea-session-attach-receipt-v1", "session_id": SESSION_ID,
            "session_receipt_path": str(pin_path), "serving_session_pid": pid,
            "serving_session_started_at": started_at, "identity": _identity(),
        }), encoding="utf-8")
    return manifest


@pytest.fixture()
def overwritten(tmp_path):
    """A session id restarted before the store existed: the first receipt's
    bytes were replaced in place and never archived."""
    session_dir = tmp_path / "serving" / SESSION_ID
    session_dir.mkdir(parents=True)
    (session_dir / "server.log").write_bytes(SECTION_ONE + SECTION_TWO)
    first = _receipt(session_dir, pid=101, started_at="2026-09-22T13:21:47.116552+00:00",
                     startup=SECTION_ONE[:58])
    second = _receipt(session_dir, pid=202, started_at="2026-09-23T03:58:54.638853+00:00",
                      startup=SECTION_TWO)
    resident = session_dir / "session-receipt.json"
    resident.write_bytes(second)
    _bundle(tmp_path, "SAEA-SYNTHETIC-OLD-V1", resident, _sha(first), pid=101,
            started_at="2026-09-22T13:21:47.116552+00:00")
    _bundle(tmp_path, "SAEA-SYNTHETIC-NEW-V1", resident, _sha(second))
    return tmp_path, resident, first


def test_gate_reports_an_unresolvable_pin_and_blocks_only_when_strict(overwritten, capsys):
    root, resident, first = overwritten
    assert gate.main(["--data-root", str(root)]) == 0
    assert gate.main(["--data-root", str(root), "--strict"]) == 1
    output = capsys.readouterr().out
    assert "UNRESOLVED" in output and "resolves nowhere" in output
    report = gate.check(root)
    assert report["bundles"] == 2
    assert report["by_session"][SESSION_ID] == {"resident": 1, "unresolved": 1}


def test_recovery_proves_bytes_by_hash_then_stores_them(overwritten, capsys):
    root, resident, first = overwritten
    store = archived_session_receipt_path(resident, _sha(first))
    assert recovery.main(["--data-root", str(root)]) == 0  # dry run
    assert "RECOVERED" in capsys.readouterr().out
    assert not store.exists()
    assert recovery.main(["--data-root", str(root), "--write"]) == 0
    assert store.read_bytes() == first
    assert resident.read_bytes() != first  # the resident file is never touched
    assert gate.main(["--data-root", str(root), "--strict"]) == 0
    assert gate.check(root)["by_session"][SESSION_ID] == {"resident": 1, "store": 1}


def test_recovery_never_writes_bytes_that_do_not_hash_to_the_pin(overwritten, capsys):
    root, resident, _ = overwritten
    lost = _sha(b"a receipt no attach record and no log section can render")
    _bundle(root, "SAEA-SYNTHETIC-LOST-V1", resident, lost, pid=303,
            started_at="2026-09-24T00:00:00+00:00")
    assert recovery.main(["--data-root", str(root), "--write"]) == 1
    assert "LOST" in capsys.readouterr().out
    assert not archived_session_receipt_path(resident, lost).exists()


def test_gate_flags_a_store_entry_that_does_not_hash_to_its_name(overwritten):
    root, resident, first = overwritten
    recovery.main(["--data-root", str(root), "--write"])
    entry = archived_session_receipt_path(resident, _sha(first))
    entry.chmod(0o600)
    entry.write_bytes(b"tampered")
    report = gate.check(root)
    assert report["store_findings"] and "not to its name" in report["store_findings"][0]
    assert gate.main(["--data-root", str(root), "--strict"]) == 1


def test_gate_skips_without_a_data_root(tmp_path, capsys):
    assert gate.main(["--data-root", str(tmp_path / "absent"), "--strict"]) == 0
    assert "SKIP" in capsys.readouterr().out
