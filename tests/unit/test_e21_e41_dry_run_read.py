"""Tests for scripts/analysis/e21_e41_dry_run_read.py (item E41 four-row
dry-run READ driver).

The driver is a plain script (not a package module), imported here by file
path -- the same ``importlib`` idiom the driver itself uses to reuse
``e21_e41_perception_note_trace_read.py``. Every scenario below runs on a
fully synthetic sealed run under a temp data root; none of these tests reads
or writes anything under ``$SPEECHRL_DATA_DIR`` or the real
``docs/exposure-ledger.md``, and none makes a model, server, encoder,
scorer, or network contact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO / "scripts" / "analysis" / "e21_e41_dry_run_read.py"

_LEDGER_COLUMNS = [
    "date", "run/experiment id", "execution profile", "scope", "model/tool",
    "speech carrier + split", "split role", "split identity hash", "consumed",
    "calls", "speech audio seconds", "gpu hours", "inherited exposure", "artifacts", "notes",
]


def _load_driver():
    spec = importlib.util.spec_from_file_location("e21_e41_dry_run_read_under_test", DRIVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DRIVER = _load_driver()

RUN_ID = "SAEA-TEST-E41-DRYRUN-V1"
ATTEMPT = "attempt-test-e41-dryrun-v1"
READ_RUN_ID = "SAEA-TEST-E41-DRYRUN-V1-READ-V1"
SAMPLE_ID = "4320211"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Fixture builders: a synthetic repo root (ledger only) and a synthetic
# sealed run (manifest + trace + outputs) under a temp data root.
# ---------------------------------------------------------------------------


def _write_ledger(tmp_path: Path, read_run_id: str, *, countersigned: bool) -> Path:
    notes = "root countersigned c0ffee00" if countersigned else "DRAFT, root countersignature pending"
    header = "| " + " | ".join(_LEDGER_COLUMNS) + " |"
    separator = "| " + " | ".join(["---"] * len(_LEDGER_COLUMNS)) + " |"
    row_cells = [
        "2026-09-27", read_run_id, "model-free-check", "test", "none", "none",
        "none", "none", "no", "0", "0", "0", "none", "none", notes,
    ]
    row = "| " + " | ".join(row_cells) + " |"
    repo_root = tmp_path / "repo"
    (repo_root / "docs").mkdir(parents=True)
    (repo_root / "docs" / "exposure-ledger.md").write_text(
        "# Exposure ledger\n\n" + header + "\n" + separator + "\n" + row + "\n", encoding="utf-8",
    )
    return repo_root


def _write_recipe(tmp_path: Path, read_run_id: str) -> Path:
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps({
        "recipe_id": "e21-native-window-e41-dry-run-receipts-read-v1-TEST",
        "read_run_id": read_run_id,
    }), encoding="utf-8")
    return path


def _contact(flight_id: str, role: str, text: str, finish_reason: str, max_tokens: int,
             completion_tokens: int, *, sample_id: str = SAMPLE_ID, packet: str | None = None):
    request_sha256 = _sha(f"{flight_id}-request")
    response_sha256 = _sha(f"{flight_id}-response")
    response_text_sha256 = _sha(text)
    agent_contact_id = _sha(f"{flight_id}-agent")
    records = [
        {"record_id": f"{flight_id}/request", "channel": "MODEL_REQUEST", "payload": {
            "payload": {
                "decoding_params": {"max_tokens": max_tokens},
                "speech_packet_sha256": packet, "history": [],
                "sample_id": sample_id, "request_id": flight_id,
            },
            "payload_sha256": request_sha256,
        }},
        {"record_id": f"{flight_id}/response", "channel": "MODEL_RESPONSE", "payload": {
            "text": text,
            "usage": {"completion_tokens": completion_tokens, "prompt_tokens": 10,
                      "total_tokens": completion_tokens + 10},
            "response_sha256": response_sha256, "response_text_sha256": response_text_sha256,
        }},
        {"record_id": f"{flight_id}/wire-response", "channel": "MODEL_WIRE_RESPONSE", "payload": {
            "finish_reason": finish_reason, "request_id": flight_id, "sample_id": sample_id,
            "response_sha256": response_sha256,
        }},
        {"record_id": f"{flight_id}/native-role-contact", "channel": "USE", "payload": {
            "use_role_id": role, "use_agent_contact_id": agent_contact_id,
            "use_request_sha256": request_sha256, "use_response_sha256": response_sha256,
            "use_response_text_sha256": response_text_sha256,
        }},
    ]
    contact_receipt = {
        "agent_contact_id": agent_contact_id, "request_id": flight_id,
        "request_sha256": request_sha256, "response_sha256": response_sha256,
        "response_text_sha256": response_text_sha256,
    }
    return records, contact_receipt, response_text_sha256


def _window(index: int, perception_text: str, perception_finish_reason: str, *,
            solver_text: str = "Solver delivered answer.", perception_max_tokens: int = 640,
            perception_completion_tokens: int = 50):
    perception_flight = f"flight-{index:04d}0"
    solver_flight = f"flight-{index:04d}1"
    perception_records, _perception_contact, _ = _contact(
        perception_flight, "perception", perception_text, perception_finish_reason,
        perception_max_tokens, perception_completion_tokens, packet=f"packet-{index}",
    )
    solver_records, solver_contact, solver_text_sha256 = _contact(
        solver_flight, "solver", solver_text, "stop", 256, 40,
    )
    episode = {
        "role_visits": [
            {"role_id": "perception", "stage": "perception", "execution_receipt": {
                "contacts": [_perception_contact], "final_contact": _perception_contact,
            }},
            {"role_id": "solver", "stage": "solver", "execution_receipt": {
                "contacts": [solver_contact], "final_contact": solver_contact,
            }},
        ],
        "planner_routes": [],
        "accepted_solver_receipt": {"contacts": [solver_contact], "final_contact": solver_contact},
        "deliver_normaliser": {
            "normaliser_id": "saea-deliver-earnings-text-v1", "applied": False, "changed": False,
        },
    }
    episode_record = {
        "record_id": f"unit-w{index:04d}/{SAMPLE_ID}/phase-native-review-revise-acquire-v1/native-episode",
        "channel": "USE", "payload": {"use_native_episode": episode},
    }
    records = perception_records + solver_records + [episode_record]
    execution_unit_id = f"{SAMPLE_ID}#w{index:04d}"
    output_source = {
        "execution_unit_id": execution_unit_id, "request_id": solver_flight,
        "delivery_text_sha256": solver_text_sha256,
    }
    return records, output_source


def _write_sealed_run(data_root: Path, run_id: str, attempt: str, *, perception_texts: list[str],
                       perception_finish_reasons: list[str], calls_used: int = 8,
                       audio_seconds_used: int = 360) -> Path:
    assert len(perception_texts) == len(perception_finish_reasons)
    all_records: list[dict] = []
    sources: list[dict] = []
    for index, (text, finish_reason) in enumerate(zip(perception_texts, perception_finish_reasons), start=1):
        records, source = _window(index, text, finish_reason)
        all_records += records
        sources.append(source)

    directory = data_root / "runs" / run_id / attempt
    directory.mkdir(parents=True, exist_ok=True)
    trace_path = directory / f"{run_id}.trace.jsonl"
    with trace_path.open("w", encoding="utf-8") as handle:
        for record in all_records:
            handle.write(json.dumps(record) + "\n")
    outputs_row = {"sample_id": SAMPLE_ID, "execution_unit_delivery": {"sources": sources}}
    (directory / f"{run_id}.outputs.jsonl").write_text(json.dumps(outputs_row) + "\n", encoding="utf-8")
    manifest = {
        "schema": "saea-run-manifest-v1", "run_id": run_id, "status": "COMPLETED",
        "study_commit": "0" * 40, "config": {"config_hash": "c" * 64}, "protocol_hash": "p" * 64,
        "split": {"name": "test", "role": "discovery", "count": 1, "ids": [SAMPLE_ID],
                  "identity_hash": "i" * 64, "carrier_lock_key": "earnings21-original"},
        "plan": {"execution_profile": "bounded-discovery-probe", "planned_model_calls": 44,
                 "planned_gpu_hours": 0.5, "planned_speech_audio_seconds": 3960},
        "cost": {"calls_used": calls_used, "audio_seconds_used": audio_seconds_used,
                 "completion_tokens_total": 100, "prompt_tokens_total": 1000,
                 "latency_seconds_total": 1.0, "tool_calls": 0},
    }
    (directory / f"{run_id}.run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def _run_driver(monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["e21_e41_dry_run_read.py"] + argv)
    return DRIVER.main()


# ---------------------------------------------------------------------------
# 1. The countersign refusal.
# ---------------------------------------------------------------------------


def test_countersign_refusal_exits_before_opening_the_trace(tmp_path, monkeypatch, capsys):
    repo_root = _write_ledger(tmp_path, READ_RUN_ID, countersigned=False)
    recipe_path = _write_recipe(tmp_path, READ_RUN_ID)
    data_root = tmp_path / "data"  # deliberately no sealed run written under here

    exit_code = _run_driver(monkeypatch, [
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--run-id", RUN_ID, "--attempt", ATTEMPT, "--recipe", str(recipe_path), "--dry-run",
    ])
    captured = capsys.readouterr()

    assert exit_code == 3
    assert "REFUSED" in captured.err
    assert "not countersigned" in captured.err
    # Nothing was ever written: the manifest/trace were never opened.
    assert not data_root.exists()


def test_countersign_refusal_when_the_read_row_is_entirely_absent(tmp_path, monkeypatch, capsys):
    repo_root = _write_ledger(tmp_path, "SAEA-SOME-OTHER-READ-V1", countersigned=True)
    recipe_path = _write_recipe(tmp_path, READ_RUN_ID)
    data_root = tmp_path / "data"

    exit_code = _run_driver(monkeypatch, [
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--run-id", RUN_ID, "--attempt", ATTEMPT, "--recipe", str(recipe_path), "--dry-run",
    ])
    captured = capsys.readouterr()

    assert exit_code == 3
    assert "no exposure-ledger row named" in captured.err


# ---------------------------------------------------------------------------
# 2. --dry-run validates and prints counts only; it writes nothing.
# ---------------------------------------------------------------------------


def test_dry_run_prints_counts_and_writes_nothing(tmp_path, monkeypatch, capsys):
    repo_root = _write_ledger(tmp_path, READ_RUN_ID, countersigned=True)
    recipe_path = _write_recipe(tmp_path, READ_RUN_ID)
    data_root = tmp_path / "data"
    _write_sealed_run(data_root, RUN_ID, ATTEMPT,
                       perception_texts=["1. NAME near 1 s: Alpha or Beta"] * 4,
                       perception_finish_reasons=["stop"] * 4)
    analysis_root = tmp_path / "analysis-out"

    exit_code = _run_driver(monkeypatch, [
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--run-id", RUN_ID, "--attempt", ATTEMPT, "--recipe", str(recipe_path),
        "--analysis-root", str(analysis_root), "--dry-run",
    ])
    captured = capsys.readouterr()

    assert exit_code == 0
    summary = json.loads(captured.out)
    assert summary["mode"].startswith("dry-run")
    assert summary["counts"]["episodes"] == 4
    assert summary["counts"]["contacts"] == 8  # 4 perception + 4 solver
    assert summary["counts"]["outputs_rows"] == 1
    assert not analysis_root.exists()  # dry-run writes nothing


# ---------------------------------------------------------------------------
# 3. R3 pass: zero Perception/Reviewer truncations.
# ---------------------------------------------------------------------------


def test_r3_pass_when_no_perception_contact_is_length_truncated(tmp_path, monkeypatch):
    repo_root = _write_ledger(tmp_path, READ_RUN_ID, countersigned=True)
    recipe_path = _write_recipe(tmp_path, READ_RUN_ID)
    data_root = tmp_path / "data"
    perception_texts = [f"1. NAME near {index} s: Alpha or Beta" for index in range(1, 5)]
    _write_sealed_run(data_root, RUN_ID, ATTEMPT, perception_texts=perception_texts,
                       perception_finish_reasons=["stop"] * 4)
    analysis_root = tmp_path / "analysis-out"

    exit_code = _run_driver(monkeypatch, [
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--run-id", RUN_ID, "--attempt", ATTEMPT, "--recipe", str(recipe_path),
        "--analysis-root", str(analysis_root),
    ])
    assert exit_code == 0

    document = json.loads((analysis_root / "read.json").read_text(encoding="utf-8"))
    assert document["assertions"]["R3"]["pass"] is True
    assert document["assertions"]["R3"]["perception"]["truncated"] == 0
    assert document["assertions"]["R3"]["perception"]["contacts"] == 4
    assert document["assertions"]["R1"]["pass"] is True
    assert document["assertions"]["R2"]["pass"] is True
    assert document["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# 4. R3 fail: one Perception contact is length-truncated.
# ---------------------------------------------------------------------------


def test_r3_fail_reports_the_truncated_notes_structure(tmp_path, monkeypatch):
    repo_root = _write_ledger(tmp_path, READ_RUN_ID, countersigned=True)
    recipe_path = _write_recipe(tmp_path, READ_RUN_ID)
    data_root = tmp_path / "data"
    truncated_note = "\n".join(f"line {index} carries filler words to build length" for index in range(1, 9))
    perception_texts = [
        "1. NAME near 1 s: Alpha or Beta",
        "2. NAME near 2 s: Gamma or Delta",
        "3. NAME near 3 s: Epsilon or Zeta",
        truncated_note,
    ]
    finish_reasons = ["stop", "stop", "stop", "length"]
    _write_sealed_run(data_root, RUN_ID, ATTEMPT, perception_texts=perception_texts,
                       perception_finish_reasons=finish_reasons)
    analysis_root = tmp_path / "analysis-out"

    exit_code = _run_driver(monkeypatch, [
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--run-id", RUN_ID, "--attempt", ATTEMPT, "--recipe", str(recipe_path),
        "--analysis-root", str(analysis_root),
    ])
    assert exit_code == 0

    document = json.loads((analysis_root / "read.json").read_text(encoding="utf-8"))
    assert document["assertions"]["R3"]["pass"] is False
    assert document["assertions"]["R3"]["perception"]["truncated"] == 1
    assert document["assertions"]["R3"]["perception"]["contacts"] == 4
    assert document["verdict"] == "FAIL"
    structure = document["assertions"]["R3"]["perception"]["truncated_note_structure"]
    assert len(structure) == 1
    assert structure[0]["lines"] == 8
    # The structure is reported (recipe R3: "the truncated note's structure
    # (lines, words per line, repetition share) reported"); the text is not.
    assert "repeat_share_6gram" in structure[0]
    rendered = json.dumps(document)
    assert truncated_note not in rendered
    assert "line 1 carries filler words" not in rendered


# ---------------------------------------------------------------------------
# 5. No fixture text ever reaches read.json / read.md.
# ---------------------------------------------------------------------------


def test_no_fixture_text_appears_in_read_json_or_read_md(tmp_path, monkeypatch):
    repo_root = _write_ledger(tmp_path, READ_RUN_ID, countersigned=True)
    recipe_path = _write_recipe(tmp_path, READ_RUN_ID)
    data_root = tmp_path / "data"
    marker = "NONCE-3f9b1c-DO-NOT-LEAK"
    perception_texts = [
        f"1. NAME near 1 s: {marker}-Alpha or {marker}-Beta",
        "2. NAME near 2 s: Gamma or Delta",
        "3. NAME near 3 s: Epsilon or Zeta",
        "\n".join(f"{marker}-line-{index} filler words padding out this note" for index in range(1, 9)),
    ]
    finish_reasons = ["stop", "stop", "stop", "length"]
    solver_marker = f"{marker}-SOLVER-DELIVERED-TEXT"
    directory = data_root / "runs" / RUN_ID / ATTEMPT
    _write_sealed_run(data_root, RUN_ID, ATTEMPT, perception_texts=perception_texts,
                       perception_finish_reasons=finish_reasons)
    # Overwrite one solver response with a distinctive marker so a leak of
    # the ANSWERING node's text (not just Perception's) would also be caught.
    trace_path = directory / f"{RUN_ID}.trace.jsonl"
    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line]
    for record in records:
        if record["record_id"] == "flight-00011/response":
            record["payload"]["text"] = solver_marker
    trace_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    analysis_root = tmp_path / "analysis-out"
    exit_code = _run_driver(monkeypatch, [
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--run-id", RUN_ID, "--attempt", ATTEMPT, "--recipe", str(recipe_path),
        "--analysis-root", str(analysis_root),
    ])
    assert exit_code == 0

    read_json_text = (analysis_root / "read.json").read_text(encoding="utf-8")
    read_md_text = (analysis_root / "read.md").read_text(encoding="utf-8")
    for leaked_candidate in (marker, solver_marker, *perception_texts):
        assert leaked_candidate not in read_json_text
        assert leaked_candidate not in read_md_text
