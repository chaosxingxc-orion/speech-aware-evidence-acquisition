"""The structural CLI forwards the explicit bound P/S rehearsal profile."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_review_off_capacity import values, payload


@pytest.mark.parametrize("lookup", [False, True])
def test_structural_cli_selects_review_off_responder_without_contact(tmp_path, monkeypatch, lookup):
    spec = importlib.util.spec_from_file_location("rehearsal_cli", Path(__file__).resolve().parents[2] / "scripts/native_graph_rehearsal.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    directory = tmp_path / "configs/experiment"
    directory.mkdir(parents=True)
    (directory / "graph.json").write_text(json.dumps({"cells": [{"model_fragment": "model", "dataset_fragment": "dataset",
        "baseline_fragment": "policy", "run_id": "run", "attempt_id": "attempt"}]}))
    context = {"sample_ids": list("abcd"), "values": values(lookup)}
    runtime = SimpleNamespace(preparation_context=lambda: context)
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *a, **kw: runtime)
    calls = []
    def rehearse(actual, **kw):
        assert actual is runtime and kw["profile"] == "review-off-v1"
        responder = kw["respond"]
        first = responder(payload("d", "solver"))
        assert bool(first.get("tool_calls")) is lookup
        if lookup:
            assert responder(payload("d", "solver"))["content"].startswith("intent:")
        calls.append(True)
        return dict(schema="synthetic", terminal_rows=4, synthetic_completions=11 if lookup else 8,
                    synthetic_tool_calls=2 if lookup else 0, generation_contacts=0, tokenizer_contacts=0,
                    capacity_verified=False)
    monkeypatch.setattr(cli, "rehearse_native_graph", rehearse)
    args = ["rehearsal"]
    for key, value in {"repo-root": tmp_path, "data-root": tmp_path, "runtime-root": tmp_path,
                       "lock-path": tmp_path / "lock", "experiment": "graph", "session": tmp_path / "session",
                       "output": tmp_path / "output", "profile": "review-off-v1"}.items():
        args.extend(["--" + key, str(value)])
    args.extend(["--targets", "person", "place"])
    monkeypatch.setattr("sys.argv", args)
    cli.main()
    assert calls == [True]
