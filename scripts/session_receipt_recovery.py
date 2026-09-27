#!/usr/bin/env python3
"""Recover a pinned resident session receipt byte-exactly, or report it lost.

Owner decision 163 (track ENGINEERING, 2026-09-27). Before commit 46e03f3d
(2026-09-24) ``write_session_receipt`` replaced ``serving/<session-id>/
session-receipt.json`` in place when a serving task restarted the SAME session
id, so a sealed bundle that pinned the earlier receipt ``{path, sha256}`` could
no longer be verified: the bytes were overwritten, never archived.

Every field of a resident receipt is still recorded elsewhere, except one:

* ``pid``, ``started_at`` and the serving identity (argv, binary, model files,
  host, port, role, server environment keys) are copied into every
  ``*.session-attach-receipt.json`` a flight writes beside its bundle;
* ``startup_stdout_sha256`` is the sha256 of the first bytes the server
  printed. ``server.log`` is opened in append mode and receives every one of
  those bytes in order, so the startup capture is a PREFIX of the session's
  own section of ``server.log`` no longer than ``DEFAULT_STARTUP_MAX_BYTES``.

This tool renders the candidate receipt with the package's own serializer
(``SessionReceipt.as_json`` + the ``write_session_receipt`` encoding) for every
prefix length of every section, and accepts a candidate ONLY when the sha256
of the rendered bytes equals the manifest's pin. A sha256 match is the proof;
nothing is ever written on a near miss. Where a stop record names the
session's canonical receipt hash, that independent match is reported too.

Default: dry run (report only). ``--write`` stores each PROVEN receipt into the
content-addressed store beside the pinned path
(``core.session.receipt.store_session_receipt_bytes``: exclusive create,
read-only, idempotent), which is exactly where ``verify_bundle`` resolves a
pinned hash. The resident file is never touched; no sealed byte is rewritten.

Zero model, tokenizer, encoder, scorer and network contacts.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    DEFAULT_STARTUP_MAX_BYTES,
    ModelFileRef,
    SessionError,
    SessionReceipt,
)
from speech_aware_evidence_acquisition.core.session.receipt import (  # noqa: E402
    SESSION_RECEIPT_SCHEMA,
    SESSION_RECEIPT_SCHEMA_V2,
    archived_session_receipt_path,
    resolve_pinned_session_receipt,
    store_session_receipt_bytes,
)

SECTION_MARKER = b" I log_info: verbosity"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_sha(document: dict) -> str:
    return _sha(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def render(receipt: SessionReceipt) -> bytes:
    """The exact bytes ``write_session_receipt`` writes for ``receipt``."""
    return json.dumps(receipt.as_json(), ensure_ascii=False, sort_keys=True, indent=2).encode(
        "utf-8"
    )


def log_sections(log: bytes) -> list[int]:
    """Byte offsets where a llama-server process began writing ``server.log``."""
    starts = {0}
    index = 0
    while True:
        found = log.find(SECTION_MARKER, index + 1)
        if found < 0:
            return sorted(starts)
        starts.add(log.rfind(b"\n", 0, found) + 1)
        index = found


def unresolved_pins(runs_root: Path) -> dict[tuple[str, str], list[Path]]:
    """``{(pinned path, sha256): [manifest, ...]}`` for pins that resolve nowhere."""
    missing: dict[tuple[str, str], list[Path]] = {}
    for manifest in sorted(runs_root.rglob("*.run-manifest.json")):
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        pin = document.get("session_receipt") if isinstance(document, dict) else None
        if not isinstance(pin, dict):
            continue
        path, digest = pin.get("path"), pin.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            continue
        try:
            resolve_pinned_session_receipt(Path(path), digest)
        except SessionError:
            missing.setdefault((path, digest), []).append(manifest)
    return missing


def attach_candidates(pinned_path: str, manifests: list[Path]) -> list[dict]:
    """Distinct (pid, started_at, identity) records naming ``pinned_path``."""
    seen: dict[str, dict] = {}
    for manifest in manifests:
        for attach in sorted(manifest.parent.glob("*.session-attach-receipt.json")):
            try:
                document = json.loads(attach.read_text(encoding="utf-8"))
                if document.get("session_receipt_path") != pinned_path:
                    continue
                candidate = {
                    "pid": document["serving_session_pid"],
                    "started_at": document["serving_session_started_at"],
                    "session_id": document["session_id"],
                    "identity": document["identity"],
                    "attach_receipt": str(attach),
                }
            except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
                continue
            key = json.dumps({k: v for k, v in candidate.items() if k != "attach_receipt"},
                             sort_keys=True)
            seen.setdefault(key, candidate)
    return list(seen.values())


def _receipt_for(candidate: dict, *, pinned_path: str, startup_sha256: str) -> SessionReceipt:
    identity = candidate["identity"]
    role = identity["session_role"]
    return SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA if role == "legacy" else SESSION_RECEIPT_SCHEMA_V2,
        study="speech-aware-evidence-acquisition",
        session_id=candidate["session_id"],
        binary_path=identity["binary_path"],
        binary_sha256=identity["binary_sha256"],
        argv=tuple(identity["server_argv"]),
        pid=candidate["pid"],
        host=identity["host"],
        port=identity["port"],
        model_files=tuple(
            ModelFileRef(path=entry["path"], sha256=entry["sha256"])
            for entry in identity["model_files"]
        ),
        started_at=candidate["started_at"],
        startup_stdout_sha256=startup_sha256,
        server_log_path=str(Path(pinned_path).parent / "server.log"),
        role=role,
        server_env_keys=(
            tuple(sorted(identity.get("server_env") or {})) if role != "legacy" else ()
        ),
    )


def recover(pinned_path: str, digest: str, manifests: list[Path]) -> dict:
    """Search for the pinned bytes; return a report entry (``raw`` on success)."""
    entry: dict = {
        "pinned_path": pinned_path,
        "sha256": digest,
        "bundles": [str(path) for path in manifests],
    }
    log_path = Path(pinned_path).parent / "server.log"
    try:
        log = log_path.read_bytes()
    except OSError as error:
        entry.update(status="LOST", evidence=f"no server.log to search: {error}")
        return entry
    sections = log_sections(log)
    candidates = attach_candidates(pinned_path, manifests)
    for candidate in candidates:
        for start in sections:
            digest_state = hashlib.sha256()
            limit = min(DEFAULT_STARTUP_MAX_BYTES, len(log) - start)
            for length in range(0, limit + 1):
                if length:
                    digest_state.update(log[start + length - 1 : start + length])
                try:
                    receipt = _receipt_for(
                        candidate,
                        pinned_path=pinned_path,
                        startup_sha256=digest_state.copy().hexdigest(),
                    )
                    raw = render(receipt)
                except (KeyError, TypeError, SessionError):
                    break
                if _sha(raw) != digest:
                    continue
                canonical = _canonical_sha(receipt.as_json())
                corroboration = []
                for stop in glob.glob(str(Path(pinned_path).parent / "**" / "session-stop.json"),
                                      recursive=True):
                    try:
                        stop_receipt = json.loads(Path(stop).read_text(encoding="utf-8")).get(
                            "stop_receipt"
                        )
                    except (OSError, ValueError, AttributeError):
                        continue
                    if (
                        isinstance(stop_receipt, dict)
                        and stop_receipt.get("session_receipt_sha256") == canonical
                    ):
                        corroboration.append(stop)
                entry.update(
                    status="RECOVERED",
                    raw=raw,
                    evidence={
                        "server_log": str(log_path),
                        "section_offset": start,
                        "startup_bytes": length,
                        "attach_receipt": candidate["attach_receipt"],
                        "pid": candidate["pid"],
                        "started_at": candidate["started_at"],
                        "canonical_sha256": canonical,
                        "stop_records_naming_canonical_sha256": corroboration,
                    },
                )
                return entry
    entry.update(
        status="LOST",
        evidence=(
            f"no rendering over {len(candidates)} attach record(s) x {len(sections)} "
            f"server.log section(s) x prefixes <= {DEFAULT_STARTUP_MAX_BYTES} bytes hashes "
            "to the pin; content hashes of the bundle remain intact"
        ),
    )
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--data-root",
        default=os.environ.get("SPEECHRL_DATA_DIR"),
        help="data root holding runs/ and serving/ (default: $SPEECHRL_DATA_DIR)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="store every PROVEN receipt into the content-addressed store (default: dry run)",
    )
    parser.add_argument("--json", type=Path, help="write the report as JSON to this path")
    args = parser.parse_args(argv)
    if not args.data_root or not (Path(args.data_root) / "runs").is_dir():
        print(f"session receipt recovery: no runs/ under data root {args.data_root!r}")
        return 2
    report = []
    for (pinned_path, digest), manifests in sorted(
        unresolved_pins(Path(args.data_root) / "runs").items()
    ):
        entry = recover(pinned_path, digest, manifests)
        raw = entry.pop("raw", None)
        if raw is not None and args.write:
            if _sha(raw) != digest:  # pragma: no cover - recover() already proved it
                raise SystemExit("refusing to store bytes whose sha256 differs from the pin")
            stored = store_session_receipt_bytes(Path(pinned_path), raw)
            entry["stored_at"] = str(stored)
            assert stored == archived_session_receipt_path(Path(pinned_path), digest)
        report.append(entry)
        evidence = entry["evidence"]
        where = (
            f"server.log@{evidence['section_offset']}+{evidence['startup_bytes']}, pid "
            f"{evidence['pid']}, stop-record corroboration "
            f"{len(evidence['stop_records_naming_canonical_sha256'])}"
            if isinstance(evidence, dict)
            else evidence
        )
        print(
            f"{entry['status']:<9} {digest[:12]} {len(manifests):>3} bundle(s) "
            f"{Path(pinned_path).parent.name}: {where}"
            + (f" -> stored {entry['stored_at']}" if "stored_at" in entry else "")
        )
    if not report:
        print("session receipt recovery: every pinned session receipt resolves")
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if any(entry["status"] == "LOST" for entry in report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
