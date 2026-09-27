#!/usr/bin/env python3
"""Gate: every sealed bundle's pinned session receipt still resolves by hash.

Owner decision 163 (track ENGINEERING, 2026-09-27). A run manifest pins the
resident serving receipt it ran against as ``session_receipt: {path, sha256}``.
Serving task entries restart the SAME session id, and before commit 46e03f3d
(2026-09-24) the restart replaced ``serving/<session-id>/session-receipt.json``
in place without keeping the prior bytes. On 2026-09-27 that left 59 sealed
bundles -- five E21 FlightRuntime bundles (E35 sub10 direct and system among
them) and 54 SLURP bundles of ``serving-slurp-native-candidate-five-train-a-
np4-v1`` -- refused by ``verify_bundle`` although every content hash they pin
was intact. ``scripts/session_receipt_recovery.py`` recovered all seven
distinct receipts byte-exactly; this gate keeps the property from decaying
silently again.

For every ``*.run-manifest.json`` under ``<data-root>/runs`` that pins a
session receipt, this resolves the pin exactly as ``verify_bundle`` does
(``core.session.receipt.resolve_pinned_session_receipt``: the resident file
when it still holds the pinned bytes, else the content-addressed store entry
``<path>.archive/<sha256>.json``, which must hash to its own name). It also
re-hashes every entry of every store directory it meets, so a tampered or
misnamed entry is reported even when no bundle pins it yet.

Report-only by default (exit 0). ``--strict`` exits 1 on any unresolvable pin
or any store entry whose bytes do not hash to its name. ``--full`` additionally
runs ``verify_bundle`` on every bundle whose receipt resolves and lists every
other refusal (informational; never changes the exit code). Without a data
root (``--data-root`` or ``$SPEECHRL_DATA_DIR``) holding ``runs/``, the gate
reports SKIP and exits 0. Read-only: nothing is ever written under the data
root. Zero model, tokenizer, encoder, scorer and network contacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _import_resolver():
    src = _REPO / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from speech_aware_evidence_acquisition.core.session import SessionError  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.session.receipt import (  # noqa: PLC0415
        resolve_pinned_session_receipt,
    )

    return SessionError, resolve_pinned_session_receipt


def _pins(runs_root: Path) -> list[dict]:
    pins = []
    for manifest in sorted(runs_root.rglob("*.run-manifest.json")):
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            pins.append({"manifest": str(manifest), "unreadable": str(error)})
            continue
        pin = document.get("session_receipt") if isinstance(document, dict) else None
        if pin is None:
            continue
        pins.append(
            {
                "manifest": str(manifest),
                "status": document.get("status"),
                "path": pin.get("path") if isinstance(pin, dict) else None,
                "sha256": pin.get("sha256") if isinstance(pin, dict) else None,
            }
        )
    return pins


def _store_findings(store_dirs: set[Path]) -> list[str]:
    findings = []
    for store in sorted(store_dirs):
        if not store.is_dir():
            continue
        for entry in sorted(store.iterdir()):
            try:
                actual = hashlib.sha256(entry.read_bytes()).hexdigest()
            except OSError as error:
                findings.append(f"{entry}: unreadable store entry: {error}")
                continue
            if entry.name != f"{actual}.json":
                findings.append(
                    f"{entry}: store entry bytes hash to {actual[:12]}..., not to its name"
                )
    return findings


def check(data_root: Path, *, full: bool = False) -> dict:
    session_error, resolve = _import_resolver()
    runs_root = data_root / "runs"
    report: dict = {"data_root": str(data_root), "bundles": 0, "by_session": {},
                    "unresolved": [], "unreadable": [], "store_findings": [],
                    "other_refusals": []}
    counts: Counter = Counter()
    store_dirs: set[Path] = set()
    serving = data_root / "serving"
    if serving.is_dir():
        store_dirs.update(path for path in serving.glob("*/*.archive") if path.is_dir())
    resolvable = []
    for pin in _pins(runs_root):
        if "unreadable" in pin:
            report["unreadable"].append(pin)
            continue
        report["bundles"] += 1
        path, digest = pin["path"], pin["sha256"]
        session = Path(path).parent.name if isinstance(path, str) else "(malformed pin)"
        if not isinstance(path, str) or not isinstance(digest, str):
            counts[(session, "unresolved")] += 1
            report["unresolved"].append({**pin, "reason": "malformed session_receipt pin"})
            continue
        store_dirs.add(Path(path).parent / f"{Path(path).name}.archive")
        try:
            raw = resolve(Path(path), digest)
        except session_error as error:
            counts[(session, "unresolved")] += 1
            report["unresolved"].append({**pin, "reason": str(error)})
            continue
        try:
            resident = Path(path).read_bytes() == raw
        except OSError:
            resident = False
        counts[(session, "resident" if resident else "store")] += 1
        resolvable.append(pin["manifest"])
    for (session, kind), count in sorted(counts.items()):
        report["by_session"].setdefault(session, {})[kind] = count
    report["store_findings"] = _store_findings(store_dirs)
    if full:
        from speech_aware_evidence_acquisition.core.bundle.verify import (  # noqa: PLC0415
            verify_bundle,
        )

        for manifest in resolvable:
            try:
                verify_bundle(Path(manifest))
            except Exception as error:  # informational: every refusal is listed
                report["other_refusals"].append(
                    {"manifest": manifest, "reason": f"{type(error).__name__}: {error}"[:500]}
                )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--data-root",
        default=os.environ.get("SPEECHRL_DATA_DIR"),
        help="data root holding runs/ and serving/ (default: $SPEECHRL_DATA_DIR)",
    )
    parser.add_argument("--strict", action="store_true", help="exit 1 on any finding")
    parser.add_argument(
        "--full", action="store_true", help="also run verify_bundle on every resolvable bundle"
    )
    parser.add_argument("--json", type=Path, help="write the report as JSON to this path")
    args = parser.parse_args(argv)
    if not args.data_root or not (Path(args.data_root) / "runs").is_dir():
        print(f"sealed_bundle_verify_check: SKIP (no runs/ under data root {args.data_root!r})")
        return 0
    report = check(Path(args.data_root), full=args.full)
    for session, kinds in sorted(report["by_session"].items()):
        detail = ", ".join(f"{kind} {count}" for kind, count in sorted(kinds.items()))
        print(f"  {session}: {detail}")
    for item in report["unresolved"]:
        print(f"UNRESOLVED {item['manifest']}: {item['reason']}")
    for item in report["unreadable"]:
        print(f"UNREADABLE {item['manifest']}: {item['unreadable']}")
    for finding in report["store_findings"]:
        print(f"STORE {finding}")
    for item in report["other_refusals"]:
        print(f"REFUSED (informational) {item['manifest']}: {item['reason']}")
    failures = len(report["unresolved"]) + len(report["store_findings"])
    print(
        f"sealed_bundle_verify_check: {report['bundles']} bundle(s) pin a session receipt; "
        f"{len(report['unresolved'])} unresolved, {len(report['store_findings'])} store "
        f"finding(s)" + (f", {len(report['other_refusals'])} other refusal(s)" if args.full else "")
        + (" [strict]" if args.strict else " [report-only]")
    )
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
