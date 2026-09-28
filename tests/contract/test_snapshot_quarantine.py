"""Contract 6: the W1 snapshot stays quarantined -- never imported, never on sys.path."""

import hashlib
import re
import sys
from pathlib import Path

import speech_aware_evidence_acquisition

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
SNAPSHOT = REPO_ROOT / "reference" / "w1-snapshot"


def test_package_resolves_from_src_not_reference():
    package_file = Path(speech_aware_evidence_acquisition.__file__).resolve()
    assert SRC_ROOT.resolve() in package_file.parents
    assert SNAPSHOT.resolve() not in package_file.parents


def test_no_source_module_touches_the_snapshot_or_sys_path():
    """No production module may mention the quarantine directory, import the
    ``reference`` package, or push a path naming the quarantine onto
    ``sys.path``. ``sys.path`` manipulation for an unrelated, legitimate
    purpose (e.g. resolving a pinned external source checkout named in a
    dataset lock) is not itself forbidden -- only a ``sys.path`` call whose
    argument names the quarantine is."""
    literal_forbidden = re.compile(
        r"w1[-_]snapshot|^\s*(?:from|import)\s+reference\b",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    quarantine_sys_path = re.compile(
        r"sys\.path\.(?:insert|append)\([^)]*\breference\b[^)]*\)",
        flags=re.IGNORECASE,
    )
    offenders = []
    for module in sorted(SRC_ROOT.rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        if literal_forbidden.search(text) or quarantine_sys_path.search(text):
            offenders.append(str(module.relative_to(REPO_ROOT)))
    assert offenders == [], f"production source must not reach into the quarantine: {offenders}"


def test_snapshot_is_not_importable_as_a_package():
    assert not (SNAPSHOT / "__init__.py").exists()
    assert not (REPO_ROOT / "reference" / "__init__.py").exists()
    assert "reference" not in sys.modules
    for entry in sys.path:
        resolved = Path(entry).resolve() if entry else Path.cwd().resolve()
        assert resolved != SNAPSHOT.resolve(), "the quarantine directory must never be on sys.path"


def test_snapshot_files_match_the_registered_manifest():
    listed = {}
    for line in (SNAPSHOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split("*", 1)
            listed[name.strip()] = digest.strip().lower()
    on_disk = {
        str(path.relative_to(SNAPSHOT)).replace("\\", "/")
        for path in SNAPSHOT.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "SNAPSHOT.md"}
    }
    assert on_disk == set(listed), "snapshot payload drifted from SHA256SUMS"
    assert len(listed) == 13, "the rescued snapshot is exactly thirteen files"
    for name, recorded in listed.items():
        actual = hashlib.sha256((SNAPSHOT / name).read_bytes()).hexdigest()
        assert actual == recorded, f"quarantined file content drifted: {name}"
