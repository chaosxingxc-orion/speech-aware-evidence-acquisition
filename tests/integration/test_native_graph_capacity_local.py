"""Opt-in full graph integration with a fake tokenizer; never a FIT certificate."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest


@pytest.mark.skipif(not os.environ.get("SAEA_NATIVE_CAPACITY_FAKE_OUTPUT"), reason="Requires local released DATA")
def test_capacity_integration_without_model_or_tokenizer_endpoints(monkeypatch):
    import speech_aware_evidence_acquisition.analysis.native_graph_capacity as cap
    import speech_aware_evidence_acquisition.core.preparation as prep
    import speech_aware_evidence_acquisition.core.bundle.git_commit as gc
    import speech_aware_evidence_acquisition.core.driver.speech_native as driver
    import speech_aware_evidence_acquisition.core.session.worker as worker
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
    from speech_aware_evidence_acquisition.core.session import attach_session
    repo = Path(__file__).resolve().parents[2]
    data = Path(os.environ["SAEA_NATIVE_REHEARSAL_DATA"])
    def build(experiment):
        cell = json.loads((repo / "configs/experiment" / (experiment + ".json")).read_text())["cells"][0]
        return build_flight_runtime(repo, data, model=cell["model_fragment"], dataset=cell["dataset_fragment"],
            baseline=cell["baseline_fragment"], experiment=experiment, run_id=cell["run_id"], attempt_id=cell["attempt_id"],
            runtime_root=Path("/home/chao"), lock_path=Path(os.environ["SAEA_NATIVE_REHEARSAL_LOCK"]), campaign_active=False)
    runtime = build(os.environ.get("SAEA_NATIVE_CAPACITY_EXPERIMENT", "slurp-native-stage3-system-text-capacity-control2-recovery1-v1"))
    monkeypatch.setattr(runtime, "authorize_preparation_contacts", lambda **kw: None)
    monkeypatch.setattr(gc, "require_clean_study_repo", lambda _: "a" * 40)
    session_path = Path(os.environ["SAEA_NATIVE_REHEARSAL_SESSION"])
    session = attach_session(session_path, runtime_receipt=runtime.preparation_context()["runtime_receipt"], runtime_root=Path("/home/chao"))
    monkeypatch.setattr(worker, "attach_worker_session", lambda **kw: (session_path.parent, {}, session))
    import speech_aware_evidence_acquisition.core.session.resource_guard as rg
    monkeypatch.setattr(rg, "resource_limits", lambda _: None)
    class FakeClient:
        def request_json(self, method, path, payload=None):
            if path == "/props":
                return {"media_marker": "MEDIA"}
            assert path == "/tokenize"
            return {"tokens": [0] * (len(payload["content"].encode()) // 4 + 1)}
    monkeypatch.setattr(driver, "_LoopbackPromptAuditClient", lambda **kw: FakeClient())
    monkeypatch.setattr(prep, "measure_request", lambda client, body, **kw: {
        "required_tokens": 100, "margin_tokens": 24476, "fits": True, "maximum_completion_tokens": body["max_tokens"]})
    output = Path(os.environ["SAEA_NATIVE_CAPACITY_FAKE_OUTPUT"])
    def fake_artifact(path, **kw):
        result = {"synthetic_tokenizer": True, "capacity_verified": False, "output": kw["producer"]()}
        path.write_text(json.dumps(result))
        return result
    monkeypatch.setattr(prep, "prepare_artifact", fake_artifact)
    with patch("socket.socket.connect", side_effect=AssertionError("No network")), patch("socket.socket.connect_ex", side_effect=AssertionError("No network")):
        cap.fit_native_graph(runtime, output, policy=SimpleNamespace(assert_lease=lambda *a, **kw: None),
            graph_factory=lambda: build(os.environ.get("SAEA_NATIVE_CAPACITY_GRAPH", "slurp-native-stage3-system-text-smoke-4-recovery1-v1")))
    result = json.loads(output.read_text())["output"]
    assert len(result["proofs"]) == 2
    assert all(p["terminal_rows"] == 4 and p["synthetic_completions"] == 22 for p in result["proofs"])
    assert len(result["rows"]) == 44
    assert result["generation_contacts"] == 0
