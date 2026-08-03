"""Contract 6: the W1 snapshot stays quarantined -- never imported, never on sys.path."""

import re
import sys
from pathlib import Path

import audio_aware_evidence_acquisition

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
SNAPSHOT = REPO_ROOT / "reference" / "w1-snapshot"


def test_package_resolves_from_src_not_reference():
    package_file = Path(audio_aware_evidence_acquisition.__file__).resolve()
    assert SRC_ROOT.resolve() in package_file.parents
    assert SNAPSHOT.resolve() not in package_file.parents


def test_no_source_module_touches_the_snapshot_or_sys_path():
    forbidden = re.compile(
        r"w1[-_]snapshot|sys\.path|^\s*(?:from|import)\s+reference\b",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    offenders = []
    for module in sorted(SRC_ROOT.rglob("*.py")):
        if forbidden.search(module.read_text(encoding="utf-8")):
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
    listed = set()
    for line in (SNAPSHOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            listed.add(line.split("*", 1)[1].strip())
    on_disk = {
        str(path.relative_to(SNAPSHOT)).replace("\\", "/")
        for path in SNAPSHOT.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "SNAPSHOT.md"}
    }
    assert on_disk == listed, "snapshot payload drifted from SHA256SUMS"
    assert len(listed) == 13, "the rescued snapshot is exactly thirteen files"
