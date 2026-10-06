"""Keep pinned historical metadata corrections narrow and fail closed."""
import hashlib
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/checks"))
import stage3_algorithm_label_check as gate

STEM = "slurp-stage3-synthetic-capacity"


def fixture(tmp_path, monkeypatch, mutate=None):
    fragment = tmp_path / "configs/experiment" / (STEM + ".json")
    fragment.parent.mkdir(parents=True)
    original = {"id": "system-text-black-box-v1", "operators_used": [], "note": "Capacity only."}
    document = {"experiment_id": "STAGE3-CAPACITY", "stage3_algorithm": original}
    fragment.write_text(json.dumps(document))
    digest = hashlib.sha256(fragment.read_bytes()).hexdigest()
    receipt = tmp_path / "docs/correction.json"
    receipt.parent.mkdir()
    value = {"schema": "saea-historical-algorithm-metadata-correction-v1", "authority": "owner227", "status": "decided", "scope": "historical-metadata-only", "runtime_admission": False, "corrections": {STEM: {"fragment_sha256": digest, "original_label": original, "corrected_label": {"id": "none", "operators_used": [], "note": "Tokenizer capacity exercises no learning operator."}}}}
    if mutate:
        mutate(value)
    receipt.write_text(json.dumps(value))
    monkeypatch.setattr(gate, "METADATA_CORRECTIONS", {STEM: {"fragment_sha256": digest, "receipt_relpath": "docs/correction.json", "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest()}}, raising=False)
    return fragment, receipt


def test_exact_correction_preserves_original_bytes(tmp_path, monkeypatch):
    fragment, receipt = fixture(tmp_path, monkeypatch)
    before = fragment.read_bytes()
    data = gate.evaluate(tmp_path)
    assert data["passed"], data["violations"]
    row = data["stage3_cells"][0]
    assert row["algorithm_id"] == "none"
    assert row["source"] == "hash-pinned-metadata-correction"
    assert row["metadata_correction"]["receipt_relpath"] == "docs/correction.json"
    assert row["metadata_correction"]["original_label"]["id"] == "system-text-black-box-v1"
    assert fragment.read_bytes() == before


@pytest.mark.parametrize("failure", ["fragment", "receipt", "missing"])
def test_changed_or_missing_evidence_refused(tmp_path, monkeypatch, failure):
    fragment, receipt = fixture(tmp_path, monkeypatch)
    if failure == "fragment":
        fragment.write_text(fragment.read_text() + " ")
    elif failure == "receipt":
        receipt.write_text(receipt.read_text() + " ")
    else:
        receipt.unlink()
    data = gate.evaluate(tmp_path)
    assert not data["passed"]
    assert data["violations"][0]["kind"] == "invalid-metadata-correction"


@pytest.mark.parametrize("mutate", [
    lambda v: v.update(authority="unknown"),
    lambda v: v.update(scope="runtime"),
    lambda v: v.update(runtime_admission=True),
    lambda v: v.update(status="pending"),
    lambda v: v["corrections"][STEM].update(original_label={}),
    lambda v: v["corrections"][STEM].update(fragment_sha256="wrong"),
])
def test_correction_cannot_expand_scope(tmp_path, monkeypatch, mutate):
    fixture(tmp_path, monkeypatch, mutate)
    data = gate.evaluate(tmp_path)
    assert not data["passed"]
    assert data["violations"][0]["kind"] == "invalid-metadata-correction"


def test_corrected_label_still_uses_registry_validation(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch, lambda v: v["corrections"][STEM]["corrected_label"].update(id="unknown"))
    data = gate.evaluate(tmp_path)
    assert not data["passed"]
    assert data["violations"][0]["kind"] == "invalid-label"


def test_other_invalid_fragment_is_not_exempted(tmp_path, monkeypatch):
    fragment, receipt = fixture(tmp_path, monkeypatch)
    other = fragment.with_name("other-stage3-capacity.json")
    other.write_bytes(fragment.read_bytes())
    data = gate.evaluate(tmp_path)
    assert not data["passed"]
    assert [v["cell"] for v in data["violations"]] == ["other-stage3-capacity"]


def test_non_object_fragment_is_reported_without_crashing(tmp_path):
    p = tmp_path / "configs/experiment/bad-stage3.json"
    p.parent.mkdir(parents=True)
    p.write_text("[]")
    data = gate.evaluate(tmp_path)
    assert not data["passed"]
    assert data["violations"][0]["kind"] == "missing-label"


def test_cli_discloses_historical_correction(tmp_path, monkeypatch, capsys):
    fixture(tmp_path, monkeypatch)
    assert gate.main(["--repo-root", str(tmp_path)]) == 0
    assert "hash-pinned historical correction" in capsys.readouterr().out
