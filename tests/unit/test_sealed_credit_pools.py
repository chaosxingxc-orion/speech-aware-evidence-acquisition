"""Pool manifest validation on synthetic repositories (no real utterances)."""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.sealed_credit import pools as pl


def _manifest(**overrides):
    base = {
        "schema": pl.SCHEMA,
        "tuning_roster": ["TUNE-A"],
        "read_rosters": {"same-flight-supply-variant": "READ-B"},
        "pools": [
            {"label": "p1", "run_id": "RUN-1", "kind": "single-sample-arm",
             "roster": "TUNE-A", "use": "tuning", "scorer": "slurp-slu-official-train"},
        ],
    }
    base.update(overrides)
    return base


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _receipt(repo, roster_id, disjointness_proof=None):
    payload = {"schema": "saea-roster-receipt-v1", "roster_id": roster_id}
    if disjointness_proof is not None:
        payload["disjointness_proof"] = disjointness_proof
    _write(repo / "docs" / "receipts" / "rosters" / f"{roster_id.lower()}.json", payload)


def _flight_registration_stub(repo):
    """A minimal flight_registration_check.py so pools.py's import_path resolves
    without pulling in the real (much heavier) gate module."""

    (repo / "scripts" / "checks").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "checks" / "flight_registration_check.py").write_text(
        (
            "import re\n"
            "ROSTER_RECEIPTS_DIR = __import__('pathlib').Path('docs/receipts/rosters')\n"
            "_NORMALIZE_KEY = re.compile(r'[^a-z0-9]')\n"
            "_SHARED_WITH_KEY = re.compile(r'^shared_with_(.*?)_(?:recordings|utterances)$')\n"
            "NO_TUNING_ROSTER = 'none'\n"
        ) + _SOURCE,
        encoding="utf-8",
    )


# The exact functions pools.py calls, copied verbatim from
# scripts/checks/flight_registration_check.py so this stub behaves identically to
# the real gate for the finite cases these tests exercise.
_SOURCE = '''
import json
from pathlib import Path
from typing import Any

def _roster_ids(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _is_no_tuning(value):
    ids = _roster_ids(value)
    return len(ids) == 1 and ids[0].strip().lower() == NO_TUNING_ROSTER


def _normalize_roster_key(value):
    return _NORMALIZE_KEY.sub("", value.lower())


_ROSTER_RECEIPT_INDEX_CACHE: dict = {}


def _roster_receipt_index(repo_root):
    key = str(repo_root)
    cached = _ROSTER_RECEIPT_INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    directory = Path(repo_root) / ROSTER_RECEIPTS_DIR
    by_filename = {}
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(document, dict):
                by_filename[path.stem.strip().lower()] = document
    index = dict(by_filename)
    for document in by_filename.values():
        roster_id_field = str(document.get("roster_id", "")).strip().lower()
        if roster_id_field:
            index.setdefault(roster_id_field, document)
    _ROSTER_RECEIPT_INDEX_CACHE[key] = index
    return index


def _load_roster_receipt(repo_root, roster_id):
    slug = roster_id.strip().lower()
    if not slug:
        return None
    return _roster_receipt_index(repo_root).get(slug)


def _extract_shared_count(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        counts = [v for k, v in value.items() if k in ("shared_recordings", "shared_utterances")
                  and isinstance(v, (int, float)) and not isinstance(v, bool)]
        if counts:
            return int(max(counts))
    return None


def _disjointness_count(receipt, other_roster_id):
    proof = receipt.get("disjointness_proof")
    if not isinstance(proof, dict):
        return None
    target = _normalize_roster_key(other_roster_id)
    if not target:
        return None
    best = None
    for key, value in proof.items():
        key_norm = _normalize_roster_key(str(key))
        matched = key_norm == target
        if not matched:
            fenced = _SHARED_WITH_KEY.match(key_norm)
            if fenced:
                slug = fenced.group(1)
                matched = bool(slug) and (slug in target or target in slug)
        if not matched:
            continue
        count = _extract_shared_count(value)
        if count is not None:
            best = count if best is None else max(best, count)
    return best


def _roster_overlap(repo_root, tuning_id, read_id):
    counts = []
    for this_id, other_id in ((tuning_id, read_id), (read_id, tuning_id)):
        receipt = _load_roster_receipt(repo_root, this_id)
        if receipt is None:
            continue
        count = _disjointness_count(receipt, other_id)
        if count is not None:
            counts.append(count)
    return max(counts) if counts else None
'''


@pytest.fixture()
def repo(tmp_path):
    _flight_registration_stub(tmp_path)
    return tmp_path


def test_load_manifest_valid(tmp_path):
    path = tmp_path / "pools.json"
    _write(path, _manifest())
    manifest = pl.load_manifest(path)
    assert manifest["schema"] == pl.SCHEMA
    assert len(manifest["pools"]) == 1


def test_load_manifest_missing_key(tmp_path):
    path = tmp_path / "pools.json"
    bad = _manifest()
    del bad["read_rosters"]
    _write(path, bad)
    with pytest.raises(pl.PoolManifestError):
        pl.load_manifest(path)


def test_load_manifest_bad_kind(tmp_path):
    path = tmp_path / "pools.json"
    bad = _manifest()
    bad["pools"][0]["kind"] = "not-a-kind"
    _write(path, bad)
    with pytest.raises(pl.PoolManifestError):
        pl.load_manifest(path)


def test_grouped_pool_requires_samples_per_row(tmp_path):
    path = tmp_path / "pools.json"
    bad = _manifest()
    bad["pools"][0]["kind"] = "grouped-multi-sample"
    _write(path, bad)
    with pytest.raises(pl.PoolManifestError):
        pl.load_manifest(path)


def test_roster_findings_missing_receipt(repo):
    manifest = _manifest()
    findings = pl.roster_findings(manifest, repo)
    codes = {f["code"] for f in findings}
    assert "missing-roster-receipt" in codes
    assert all(f["severity"] == "blocking" for f in findings if f["code"] == "missing-roster-receipt")


def test_roster_findings_disjoint_receipts_pass(repo):
    _receipt(repo, "TUNE-A", {"read-b": {"shared_recordings": 0, "shared_utterances": 0}})
    _receipt(repo, "READ-B")
    manifest = _manifest()
    findings = pl.roster_findings(manifest, repo)
    assert not any(f["code"] == "tuning-read-overlap" for f in findings)
    assert not any(f["code"] == "missing-roster-receipt" for f in findings)


def test_roster_findings_overlap_blocks(repo):
    _receipt(repo, "TUNE-A", {"read-b": {"shared_recordings": 5, "shared_utterances": 2}})
    _receipt(repo, "READ-B")
    manifest = _manifest()
    findings = pl.roster_findings(manifest, repo)
    overlap = [f for f in findings if f["code"] == "tuning-read-overlap"]
    assert overlap and overlap[0]["severity"] == "blocking"
    with pytest.raises(pl.PoolManifestError):
        pl.validate_manifest(manifest, repo)


def test_roster_findings_identical_tuning_and_read_roster(repo):
    _receipt(repo, "TUNE-A")
    manifest = _manifest(read_rosters={"same-flight-supply-variant": "TUNE-A"})
    findings = pl.roster_findings(manifest, repo)
    assert any(f["code"] == "tuning-read-overlap" for f in findings)


def test_dev_as_tuning_pool_refused(repo):
    _receipt(repo, "TUNE-A", {"read-b": {"shared_recordings": 0, "shared_utterances": 0}})
    _receipt(repo, "READ-B")
    manifest = _manifest()
    manifest["pools"][0]["roster"] = "READ-B"  # a tuning-use pool sitting on the read roster
    findings = pl.roster_findings(manifest, repo)
    assert any(f["code"] == "read-roster-as-tuning" for f in findings)


def test_pools_by_use_and_pool_by_label():
    manifest = _manifest()
    assert [p["label"] for p in pl.pools_by_use(manifest, "tuning")] == ["p1"]
    assert pl.pool_by_label(manifest, "p1")["run_id"] == "RUN-1"
    with pytest.raises(pl.PoolManifestError):
        pl.pool_by_label(manifest, "missing")


def test_attempt_dir_resolves_single_attempt(tmp_path):
    run_dir = tmp_path / "runs" / "RUN-1" / "attempt-a"
    run_dir.mkdir(parents=True)
    (run_dir / "RUN-1.phases.json").write_text("{}", encoding="utf-8")
    resolved = pl.attempt_dir(tmp_path, "RUN-1")
    assert resolved == run_dir


def test_attempt_dir_refuses_ambiguous(tmp_path):
    for name in ("attempt-a", "attempt-b"):
        run_dir = tmp_path / "runs" / "RUN-1" / name
        run_dir.mkdir(parents=True)
        (run_dir / "RUN-1.phases.json").write_text("{}", encoding="utf-8")
    with pytest.raises(pl.PoolManifestError):
        pl.attempt_dir(tmp_path, "RUN-1")


def test_seal_only_pool_may_name_its_phases_attempt(tmp_path):
    pools = [{"label": "p1", "run_id": "RUN-1", "kind": "single-sample-arm", "roster": "TUNE-A",
              "use": "tuning", "scorer": "slurp-slu-official-train",
              "attempt": "attempt-x-seal-only", "phases_attempt": "attempt-x"}]
    path = tmp_path / "m.json"
    _write(path, _manifest(pools=pools))
    manifest = pl.load_manifest(path)
    assert manifest["pools"][0]["phases_attempt"] == "attempt-x"
