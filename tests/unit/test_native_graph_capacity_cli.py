"""The separate capacity launcher forwards the exact registered endpoint cap."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cli():
    spec = importlib.util.spec_from_file_location("capacity_cli", ROOT / "scripts/native_graph_capacity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("cap", [None, 297])
@pytest.mark.parametrize("profile", [None, "review-off-v1"])
def test_native_capacity_forwards_cap_without_a_generation_path(cli, monkeypatch, tmp_path, cap, profile):
    data = tmp_path / "data"
    data.mkdir()
    token = tmp_path / "lease.json"
    token.write_text(json.dumps({"token": "synthetic"}))
    output = data / "fit.json"
    args = []
    for key, value in {"repo-root": tmp_path, "data-root": data, "runtime-root": tmp_path,
        "lock-path": tmp_path / "lock", "experiment": "capacity", "graph-experiment": "graph",
        "output": output, "lease-token-file": token, "expected-session-id": "session"}.items():
        args.extend(["--" + key, str(value)])
    if cap is not None:
        args.extend(["--contact-cap", str(cap)])
    if profile is not None:
        args.extend(["--profile", profile])
    cell = SimpleNamespace(document={"model_fragment": "model", "dataset_fragment": "dataset",
        "baseline_fragment": "baseline"}, run_id="RUN-FIT-V1", attempt_id="attempt",
        assert_mode=lambda mode: None)
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *a: [cell])
    monkeypatch.setattr(cli, "declared_readiness", lambda *a: SimpleNamespace(state="ready"))
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *a, **k: object())
    monkeypatch.setattr(cli, "WorkerExecutionPolicy", lambda *a: SimpleNamespace(assert_lease=lambda *a, **k: None))
    captured = []
    def fit(runtime, path, **kwargs):
        captured.append(kwargs["contact_cap"])
        assert kwargs.get("profile") == profile
        assert kwargs["graph_factory"]() is not None
        path.write_text(json.dumps({"output": {"every_request_fits": True}}))
        return {"status": "synthetic"}
    monkeypatch.setattr(cli, "fit_native_graph", fit)
    cli.main(args)
    assert captured == [2048 if cap is None else cap]


@pytest.mark.parametrize("cap", ["0", "-1", "bad"])
def test_invalid_endpoint_cap_refuses_before_runtime(cli, monkeypatch, cap):
    args = []
    for key in ("repo-root", "data-root", "runtime-root", "lock-path", "experiment", "output",
                "lease-token-file", "expected-session-id", "graph-experiment"):
        args.extend(["--" + key, "unused"])
    args.extend(["--contact-cap", cap])
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *a: pytest.fail("runtime touched"))
    with pytest.raises(SystemExit):
        cli.main(args)


def test_held_capacity_refuses_before_runtime_or_contacts(cli, monkeypatch):
    args = []
    for key in ("repo-root", "data-root", "runtime-root", "lock-path", "experiment", "output",
                "lease-token-file", "expected-session-id", "graph-experiment"):
        args.extend(["--" + key, "unused"])
    args.extend(["--contact-cap", "297"])
    cell = SimpleNamespace(assert_mode=lambda mode: None)
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *a: [cell])
    monkeypatch.setattr(cli, "declared_readiness", lambda *a: SimpleNamespace(state="held"))
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *a, **k: pytest.fail("runtime touched"))
    monkeypatch.setattr(cli, "fit_native_graph", lambda *a, **k: pytest.fail("contact attempted"))
    with pytest.raises(ValueError, match="not admitted"):
        cli.main(args)
