"""Synthetic tests for the ASR339 sidecar and the Fold B transcription instrument (no model, no data, no GPU)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SC = _load("scripts/flights/direct/asr_sidecar.py", "asr339_sidecar_under_test")
IN = _load("scripts/analysis/asr339/foldb_transcription.py", "asr339_instrument_under_test")


def _lock(tmp_path: Path, status: str = "COMPLETE") -> Path:
    entry = {"name": "qwen3-asr-0.6b-gguf", "kind": "model", "local_subdir": "models/x/asr06", "revision": "rev0",
             "status": status, "source": {"files": [
                 {"filename": "A-bf16.gguf", "size_bytes": 3, "sha256": "a" * 64},
                 {"filename": "mmproj-A-bf16.gguf", "size_bytes": 2, "sha256": "b" * 64}]}}
    path = tmp_path / "lock.json"
    path.write_text(json.dumps({"models": [entry], "other": 1}), encoding="utf-8")
    return path


def test_lock_resolution_roles_and_paths(tmp_path):
    assets = SC.resolve_assets("qwen3-asr-0.6b", _lock(tmp_path), tmp_path / "data")
    assert assets["files"]["model"]["path"] == str(tmp_path / "data" / "models/x/asr06" / "A-bf16.gguf")
    assert assets["files"]["mmproj"]["sha256"] == "b" * 64
    assert assets["revision"] == "rev0"


def test_lock_resolution_fails_closed(tmp_path):
    with pytest.raises(SC.SidecarError):
        SC.resolve_assets("qwen3-asr-9b", _lock(tmp_path), tmp_path)
    with pytest.raises(SC.SidecarError):
        SC.resolve_assets("qwen3-asr-1.7b", _lock(tmp_path), tmp_path)  # entry absent
    with pytest.raises(SC.SidecarError):
        SC.resolve_assets("qwen3-asr-0.6b", _lock(tmp_path, status="PARTIAL"), tmp_path)


def test_verify_assets_detects_size_and_hash(tmp_path):
    assets = SC.resolve_assets("qwen3-asr-0.6b", _lock(tmp_path), tmp_path)
    with pytest.raises(SC.SidecarError):
        SC.verify_assets(assets)  # files absent


def test_argv_is_reaper_safe_cpu_only(tmp_path):
    assets = SC.resolve_assets("qwen3-asr-0.6b", _lock(tmp_path), tmp_path)
    argv = SC.build_argv("/x/build/bin/llama-server", assets, 8190)
    joined = " ".join(argv)
    assert "llama-server --host" not in joined
    assert not SC.REAPER_PATTERN.search(joined)
    assert argv.index("--port") < argv.index("--host")
    assert argv[argv.index("-ngl") + 1] == "0" and "--no-mmproj-offload" in argv
    assert argv[argv.index("--mmproj") + 1].endswith("mmproj-A-bf16.gguf")
    with pytest.raises(SC.SidecarError):
        SC.build_argv("/x/llama-server", assets, 8080)


def test_server_env_hides_the_gpu():
    assert SC.server_env()["CUDA_VISIBLE_DEVICES"] == ""


def test_receipt_schema(tmp_path):
    assets = SC.resolve_assets("qwen3-asr-0.6b", _lock(tmp_path), tmp_path)
    argv = SC.build_argv("/x/llama-server", assets, 8190)
    r = SC.make_receipt("qwen3-asr-0.6b", assets, argv, 8190, 123, "/x/llama-server", "04ccc72a2")
    assert r["schema"] == SC.RECEIPT_SCHEMA and r["device"] == "cpu"
    for key in ("model_id", "lock_entry", "lock_revision", "build_commit", "port", "pid", "started_at", "argv"):
        assert key in r
    assert r["model"]["sha256"] == "a" * 64 and r["mmproj"]["sha256"] == "b" * 64
    json.dumps(r)


def test_parse_asr_output():
    assert IN.parse_asr_output("language English<asr_text>Hello there.") == ("ok", "Hello there.")
    assert IN.parse_asr_output("language English<asr_text>") == ("empty", "")
    assert IN.parse_asr_output("") == ("empty", "")
    assert IN.parse_asr_output("plain words") == ("ok", "plain words")


def test_wer_summary_arithmetic():
    canon = lambda s: s.lower().split()  # noqa: E731

    def edit(a, b):
        return sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))

    out = IN.wer_summary({"a": "one two three", "b": "four five"}, {"a": "one two three", "b": "four six"}, canon, edit)
    assert out["ref_tokens"] == 5 and out["edit_errors"] == 1 and out["canon_wer"] == 0.2
    assert out["sentence_exact_rate"] == 0.5


def test_catalog_and_rows_schema_roundtrip(tmp_path):
    rows = tmp_path / "transcripts.jsonl"
    rows.write_text(json.dumps({"schema": IN.SCHEMA_ROW, "sample_id": "slurp:train:000006:audio-1",
                                "status": "ok", "transcript": "t", "audio_sha256": "0" * 64, "audio_seconds": 1.0,
                                "asr_seconds": 0.5, "completion_tokens": 3, "prompt_tokens": 9}) + "\n")
    catalog = {"schema": IN.SCHEMA_CATALOG, "transcripts_sha256": IN.sha256_file(rows), "mode": "smoke"}
    (tmp_path / "catalog.json").write_bytes(IN.canonical_json(catalog))
    cat, loaded = IN.load_rows(tmp_path)
    assert cat["schema"] == IN.SCHEMA_CATALOG and loaded[0]["status"] == "ok"
    rows.write_text("tampered\n")
    with pytest.raises(IN.InstrumentError):
        IN.load_rows(tmp_path)


def test_full_pass_refused_without_ledger_row(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "exposure-ledger.md").write_text("no such row\n", encoding="utf-8")
    with pytest.raises(IN.InstrumentError):
        IN.check_ledger(tmp_path)
    (tmp_path / "docs" / "exposure-ledger.md").write_text(
        f"| {IN.LEDGER_ROW_ID} | consumed = no | root countersigned |\n", encoding="utf-8")
    IN.check_ledger(tmp_path)


def test_roster_is_the_fold_b_1080():
    doc, items = IN.roster_items(REPO_ROOT)
    assert len(items) == 1080 and doc["split_identity_hash"].startswith("4407794c")
    assert all(":train:" in i["sample_id"] for i in items)
