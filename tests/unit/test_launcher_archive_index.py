"""WAVE R7 Group B: the archived launcher directories, and the gate that keeps
new ones out.

`docs/archive/launchers/2026-09-08/INDEX.md` records three orphan launcher
directories moved out of `docs/checks/`, byte for byte, with their sha256 and
their origin path. These tests pin that record: the bytes are what the index
says, the origin receipts survive without their launcher, nothing archived has
reappeared under `docs/checks/`, and the ratchet baseline agrees with the tree.
"""

import hashlib
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = REPO_ROOT / "docs/archive/launchers/2026-09-08"
INDEX = ARCHIVE / "INDEX.md"
CHECKS = REPO_ROOT / "docs/checks"
BASELINE = REPO_ROOT / "scripts/checks/engineering_base_baseline.json"

#: (archived relative path, sha256, origin path) exactly as INDEX.md records.
ARCHIVED = (
    (
        "2026-08-24-dev500-confirmatory/launch_dev500_confirmatory.py",
        "8049422875bd6833a6074a7c43afdd6fb9a87332737b6e6c0ea51a8c387fab5d",
        "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev500-confirmatory/launcher/launch_dev500_confirmatory.py",
    ),
    (
        "2026-09-01-a2t-factor-top1-104-v1/launch_a2t_factor_top1.py",
        "73f5c5a2be8515cfb9ab0ea4a211ef334ba81aeaad8413e5fad1c39f0bb1aeb4",
        "docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-factor-top1-104-v1/launcher/launch_a2t_factor_top1.py",
    ),
    (
        "2026-09-01-a2t-self-consistency-104-v1/launch_a2t_self_consistency.py",
        "816dc902695f76ff056eb17a234a492242c6496330d8a3f65bbd9aee5d503bb9",
        "docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-self-consistency-104-v1/launcher/launch_a2t_self_consistency.py",
    ),
)


def test_the_index_exists_and_names_every_archived_file():
    text = INDEX.read_text(encoding="utf-8")
    for relpath, digest, origin in ARCHIVED:
        assert relpath in text
        assert digest in text
        assert origin in text


def test_every_archived_file_is_present_at_the_recorded_sha256():
    for relpath, digest, _origin in ARCHIVED:
        path = ARCHIVE / relpath
        assert path.is_file(), f"missing archived launcher {relpath}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == digest, f"{relpath}: {actual} != recorded {digest}"


def test_the_origin_receipt_survives_and_no_longer_carries_a_launcher_dir():
    for _relpath, _digest, origin in ARCHIVED:
        origin_path = REPO_ROOT / origin
        assert not origin_path.exists(), f"{origin} is back under docs/checks"
        launcher_dir = origin_path.parent
        assert not launcher_dir.exists(), f"{launcher_dir} is back"
        receipt = launcher_dir.parent
        assert receipt.is_dir(), f"origin receipt {receipt} disappeared"
        sealed = [p for p in receipt.iterdir() if p.is_file()]
        assert sealed, f"origin receipt {receipt} has no sealed artifact left"


def test_the_ratchet_baseline_agrees_with_the_tree():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    listed = set(baseline["rules"]["launcher_dirs"])
    on_disk = {
        p.relative_to(REPO_ROOT).as_posix()
        for p in CHECKS.rglob("launcher")
        if p.is_dir()
    }
    # Ratchet semantics: the tree may be a SUBSET of the baseline (disposal is
    # in progress); a directory on disk that the baseline does not list is
    # regrowth and fails the gate.
    assert on_disk <= listed
    assert len(listed) == 42
    for _relpath, _digest, origin in ARCHIVED:
        assert Path(origin).parent.as_posix() not in listed


def test_the_index_disposition_table_covers_all_45_original_directories():
    text = INDEX.read_text(encoding="utf-8")
    rows = re.findall(r"^\| `(20\d\d-\d\d-\d\d-[^`]+)` \| \d+ \|", text, re.MULTILINE)
    assert len(rows) == 45, f"disposition table lists {len(rows)} directories, not 45"
    assert len(set(rows)) == 45
