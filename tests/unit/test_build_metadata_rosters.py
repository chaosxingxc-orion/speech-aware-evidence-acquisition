"""Unit tests for ``scripts/build_metadata_rosters.py`` (PRE Track A).

The filtering rule under test was spot-checked directly against the two
already-committed reference manifests (p1-metadata-v1/v2) and the real
``speaker-metadata.csv`` before this script was written: ``"Operator"`` is
a literal metadata value (kept), and ``^Speaker \\d+$`` is the only
excluded pattern -- see the script's own module docstring for the full
citation trail. These tests pin that corrected rule with synthetic CSVs;
no real data dependency."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_metadata_rosters.py"

CARRIER = "earnings21-original"
FILE_METADATA_HEADER = (
    "file_id,audio_length,sample_rate,company_name,financial_quarter,sector,"
    "speaker_switches,unique_speakers,curator_id"
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("build_metadata_rosters", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _World:
    def __init__(
        self,
        tmp_path: Path,
        companies: dict[str, str],
        speakers: dict[str, list[str]],
    ) -> None:
        self.data_root = tmp_path / "data"
        self.carrier_dir = self.data_root / "datasets" / "earnings21-22" / "earnings21"
        self.carrier_dir.mkdir(parents=True)
        self.lock_path = tmp_path / "lock.json"

        file_metadata = self.carrier_dir / "earnings21-file-metadata.csv"
        rows = [FILE_METADATA_HEADER]
        for sample_id, company in companies.items():
            rows.append(f"{sample_id},100.0,16000,{company},Q1 2020,Industrial,10,3,curator-1")
        file_metadata.write_text("\n".join(rows) + "\n", encoding="utf-8")
        self.file_metadata_path = file_metadata

        speaker_metadata = self.carrier_dir / "speaker-metadata.csv"
        with speaker_metadata.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["file_id", "speaker_id", "speaker_name"])
            for sample_id, names in speakers.items():
                for index, name in enumerate(names):
                    writer.writerow([sample_id, index, name])
        self.speaker_metadata_path = speaker_metadata

        self.lock_path.write_text(
            json.dumps(
                {
                    "datasets": [
                        {
                            "name": CARRIER,
                            "local_subdir": "datasets/earnings21-22/earnings21",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def load_lock(self):
        return json.loads(self.lock_path.read_text(encoding="utf-8"))

    def write_ids_file(self, path: Path, ids: list[str]) -> None:
        path.write_text(json.dumps({"items": [{"id": i} for i in ids]}), encoding="utf-8")


# ---------------------------------------------------------------------------
# build_roster: the pure filtering/dedup/sort function
# ---------------------------------------------------------------------------


def test_operator_is_kept_speaker_n_pattern_is_dropped(script):
    roster = script.build_roster(
        "Culp Inc", ["Operator", "Dru Anderson", "Speaker 1", "Speaker 12"]
    )
    assert roster == ["Culp Inc", "Dru Anderson", "Operator"]


def test_case_insensitive_dedupe_keeps_first_seen_casing(script):
    roster = script.build_roster("Acme Corp", ["steve", "Steve", "STEVE"])
    assert roster == ["Acme Corp", "steve"]


def test_typos_and_honorifics_preserved_verbatim(script):
    roster = script.build_roster(
        "Pheonix New Media Ltd", ["Dr. Todd Brady", "Mr. Joshua Reed", "Micheal Frenz"]
    )
    assert roster == ["Dr. Todd Brady", "Micheal Frenz", "Mr. Joshua Reed", "Pheonix New Media Ltd"]


def test_speaker_n_only_matches_the_exact_pattern(script):
    # "Speaker Nine" and "Speaker 1a" are real-shaped names, not the
    # placeholder pattern -- only digits-only suffixes are dropped.
    roster = script.build_roster("Acme Corp", ["Speaker Nine", "Speaker 1a", "Speaker 7"])
    assert roster == ["Acme Corp", "Speaker 1a", "Speaker Nine"]


def test_company_name_alone_yields_a_singleton_roster(script):
    assert script.build_roster("Solo Corp", []) == ["Solo Corp"]


# ---------------------------------------------------------------------------
# build_rosters: full CSV-reading pipeline
# ---------------------------------------------------------------------------


def test_build_rosters_reads_real_csv_shape_and_hashes_sources(tmp_path, script):
    world = _World(
        tmp_path,
        companies={"4330115": "Culp Inc", "4365024": "Nextar Media Group"},
        speakers={
            "4330115": ["Operator", "Dru Anderson", "Iv Culp"],
            "4365024": ["Aaron Watts", "Speaker 1"],
        },
    )
    rosters, sources = script.build_rosters(
        data_root=world.data_root,
        lock=world.load_lock(),
        carrier_lock_key=CARRIER,
        ids=["4330115", "4365024"],
    )
    assert rosters["4330115"] == ["Culp Inc", "Dru Anderson", "Iv Culp", "Operator"]
    assert rosters["4365024"] == ["Aaron Watts", "Nextar Media Group"]
    assert sources["file_metadata"]["relpath"] == (
        "datasets/earnings21-22/earnings21/earnings21-file-metadata.csv"
    )
    assert sources["file_metadata"]["sha256"] == _sha256_file(world.file_metadata_path)
    assert sources["speaker_metadata"]["relpath"] == (
        "datasets/earnings21-22/earnings21/speaker-metadata.csv"
    )
    assert sources["speaker_metadata"]["sha256"] == _sha256_file(world.speaker_metadata_path)


def test_missing_sample_id_raises_roster_error(tmp_path, script):
    world = _World(tmp_path, companies={"4330115": "Culp Inc"}, speakers={})
    with pytest.raises(script.RosterError, match="4999999"):
        script.build_rosters(
            data_root=world.data_root,
            lock=world.load_lock(),
            carrier_lock_key=CARRIER,
            ids=["4330115", "4999999"],
        )


def test_call_with_no_speaker_rows_yields_company_only_roster(tmp_path, script):
    world = _World(tmp_path, companies={"4389907": "Pheonix New Media Ltd"}, speakers={})
    rosters, _sources = script.build_rosters(
        data_root=world.data_root,
        lock=world.load_lock(),
        carrier_lock_key=CARRIER,
        ids=["4389907"],
    )
    assert rosters["4389907"] == ["Pheonix New Media Ltd"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_dry_run_writes_nothing(tmp_path, script, capsys):
    world = _World(
        tmp_path,
        companies={"4330115": "Culp Inc"},
        speakers={"4330115": ["Operator", "Dru Anderson"]},
    )
    ids_file = tmp_path / "ids.json"
    world.write_ids_file(ids_file, ["4330115"])
    out_dir = world.data_root / "derived" / "evidence-candidates" / "dry-run-check"

    exit_code = script.main(
        [
            "--out-id",
            "dry-run-check",
            "--ids-file",
            str(ids_file),
            "--carrier-lock-key",
            CARRIER,
            "--data-root",
            str(world.data_root),
            "--lock-path",
            str(world.lock_path),
            "--dry-run",
        ]
    )
    assert exit_code == 0
    assert not out_dir.exists()
    captured = capsys.readouterr()
    assert "Operator" in captured.out


def test_cli_writes_candidates_and_manifest(tmp_path, script):
    world = _World(
        tmp_path,
        companies={"4330115": "Culp Inc", "4365024": "Nextar Media Group"},
        speakers={
            "4330115": ["Operator", "Dru Anderson", "Iv Culp"],
            "4365024": ["Aaron Watts", "Speaker 1"],
        },
    )
    ids_file = tmp_path / "ids.json"
    world.write_ids_file(ids_file, ["4330115", "4365024"])

    exit_code = script.main(
        [
            "--out-id",
            "test-roster-v3",
            "--ids-file",
            str(ids_file),
            "--carrier-lock-key",
            CARRIER,
            "--data-root",
            str(world.data_root),
            "--lock-path",
            str(world.lock_path),
        ]
    )
    assert exit_code == 0

    out_dir = world.data_root / "derived" / "evidence-candidates" / "test-roster-v3"
    candidates = (out_dir / "4330115.candidates.txt").read_text(encoding="utf-8")
    assert candidates == "Culp Inc\nDru Anderson\nIv Culp\nOperator\n"

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "saea-metadata-roster-v1"
    assert manifest["rule_version"] == "metadata-roster-rule-v1"
    assert manifest["materialization_id"] == "test-roster-v3"
    assert manifest["per_sample"]["4330115"]["count"] == 4
    assert manifest["per_sample"]["4330115"]["terms"] == [
        "Culp Inc",
        "Dru Anderson",
        "Iv Culp",
        "Operator",
    ]
    assert manifest["sources"]["file_metadata"]["sha256"] == _sha256_file(
        world.file_metadata_path
    )
