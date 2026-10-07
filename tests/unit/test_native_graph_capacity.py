"""Reachable-request capacity keeps legal responses and exact wire bodies."""
import json
import pytest
from speech_aware_evidence_acquisition.analysis.native_graph_capacity import (
    bounded_response_texts, measure_captured_requests,
    FreshAuditConnections,
)
from speech_aware_evidence_acquisition.rails.review_handoff import normalize_review_handoff


def test_bounded_response_texts_keep_three_candidates_and_valid_review():
    texts, counts = bounded_response_texts(lambda s: len(s.encode()) // 4 + 1,
        targets=["media_type", "device_type"], intents=["calendar_query", "calendar_set", "calendar_remove"])
    assert all(n <= 512 for n in counts.values())
    assert len(json.loads(texts["perception"])["candidates"]) == 3
    assert all(len(c["distinction"]) <= 128 for c in json.loads(texts["perception"])["candidates"])
    assert json.loads(normalize_review_handoff(texts["reviewer"]))["status"] == "valid"
    assert len(json.loads(texts["reviewer"])["findings"]) == 4
    assert texts["solver"].startswith("intent: calendar_query")


def test_capacity_measures_exact_body_and_reserves_once(monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation as p
    body = {"messages": [{"role": "user", "content": "real projected history"}], "max_tokens": 512}
    received = []
    def measure(client, actual, **kw):
        received.append((actual, kw))
        return {"required_tokens": 24000, "margin_tokens": 576, "fits": True,
                "maximum_completion_tokens": 512}
    monkeypatch.setattr(p, "measure_request", measure)
    rows = measure_captured_requests(None, [{"request": body, "sample_id": "s"}],
                                    media_marker="MEDIA", speech_max=195, reserve=2048)
    assert received[0][0] is body
    assert received[0][1]["speech_tokens"] == (195,)
    assert body["messages"] == [{"role": "user", "content": "real projected history"}]
    assert rows[0]["fits"] is False
    assert rows[0]["margin_after_structural_reserve"] == -1472
    with pytest.raises(ValueError, match="completion"):
        measure_captured_requests(None, [{"request": {**body, "max_tokens": 256}, "sample_id": "s"}],
                                  media_marker="MEDIA", speech_max=195)


def test_each_endpoint_uses_a_fresh_connection_and_never_retries_failure():
    made, closed = [], []
    class Client:
        def __init__(self):
            from types import SimpleNamespace
            self.local = SimpleNamespace(connection=SimpleNamespace(close=lambda: closed.append(self)))
            self.called = False
            made.append(self)
        def request_json(self, method, route, payload=None):
            assert not self.called
            self.called = True
            if route == "/failure":
                raise BrokenPipeError("synthetic closed socket")
            return {"ok": True}
    adapter = FreshAuditConnections(Client)
    assert adapter.request_json("POST", "/tokenize") == {"ok": True}
    assert adapter.request_json("POST", "/apply-template") == {"ok": True}
    with pytest.raises(BrokenPipeError):
        adapter.request_json("POST", "/failure")
    assert len(made) == len(closed) == 3


@pytest.mark.parametrize("capacity, graph", [
    (None, {"schema": "saea-native-prefix-slots-v1", "role_slots": {"solver": 1}}),
    ({"schema": "saea-native-prefix-slots-v1", "role_slots": {"solver": 1}}, None),
    ({"schema": "saea-native-prefix-slots-v1", "role_slots": {"solver": 1}},
     {"schema": "saea-native-prefix-slots-v1", "role_slots": {"solver": 2}}),
])
def test_capacity_refuses_different_prefix_routing_before_any_endpoint(capacity, graph, tmp_path):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.analysis.native_graph_capacity import fit_native_graph

    def runtime(binding):
        values = {} if binding is None else {"native_prefix_slots": binding}
        return SimpleNamespace(preparation_context=lambda: {"values": values, "sample_ids": list("abcd")})

    with pytest.raises(ValueError, match="Graph proof differs.*native_prefix_slots"):
        fit_native_graph(runtime(capacity), tmp_path / "absent.json", policy=None,
                         graph_factory=lambda: runtime(graph))
    assert not (tmp_path / "absent.json").exists()


@pytest.mark.parametrize("capacity, graph", [
    (None, "before-speech-v1"), ("before-speech-v1", None),
])
def test_capacity_refuses_a_graph_with_different_context_layout(capacity, graph, tmp_path):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.analysis.native_graph_capacity import fit_native_graph

    def runtime(placement):
        values = {} if placement is None else {"native_role_query_placement": placement}
        return SimpleNamespace(preparation_context=lambda: {"values": values, "sample_ids": list("abcd")})

    with pytest.raises(ValueError, match="Graph proof differs.*native_role_query_placement"):
        fit_native_graph(runtime(capacity), tmp_path / "absent.json", policy=None,
                         graph_factory=lambda: runtime(graph))
    assert not (tmp_path / "absent.json").exists()


def test_capacity_scratch_names_separate_equal_leaf_directories(tmp_path):
    from speech_aware_evidence_acquisition.analysis.native_graph_capacity import capacity_rehearsal_outputs
    data = tmp_path / "data"
    first = data / "coordination" / "initial" / "counterexample-check" / "fit.json"
    second = data / "coordination" / "gepa" / "counterexample-check" / "fit.json"
    a = capacity_rehearsal_outputs(data, first)
    b = capacity_rehearsal_outputs(data, second)
    assert set(a) == {"new-acquisition", "wide-automatic-supply"}
    assert set(a.values()).isdisjoint(b.values())
    assert all(p.is_relative_to(data / "wire-check") for p in a.values())
    assert capacity_rehearsal_outputs(data, first.parent / "." / first.name) == a
    assert not data.exists()


@pytest.mark.parametrize("mode", ["new-acquisition", "wide-automatic-supply"])
def test_capacity_scratch_refuses_existing_proof_before_authorization(tmp_path, monkeypatch, mode):
    from types import SimpleNamespace
    import speech_aware_evidence_acquisition.analysis.native_graph_capacity as cap
    import speech_aware_evidence_acquisition.analysis.native_episode_dry_run as dry
    import speech_aware_evidence_acquisition.core.bundle.git_commit as gc
    import speech_aware_evidence_acquisition.core.preparation as prep
    data = tmp_path / "data"
    output = data / "coordination" / "fresh" / "fit.json"
    scratch = cap.capacity_rehearsal_outputs(data, output)
    scratch[mode].mkdir(parents=True)
    sentinel = scratch[mode] / "immutable"
    sentinel.write_text("preserve")
    context = {"values": {}, "sample_ids": list("abcd"), "data_root": data}
    runtime = SimpleNamespace(preparation_context=lambda: context, _data_root=data,
        _repo_root=tmp_path, _composed=SimpleNamespace(config_hash="synthetic"),
        verify_prepared_artifacts=lambda: (),
        authorize_preparation_contacts=lambda **kw: pytest.fail("authorized contacts"))
    monkeypatch.setattr(dry, "compose_dry_run", lambda *a, **kw: None)
    monkeypatch.setattr(gc, "require_clean_study_repo", lambda *a: "a" * 40)
    monkeypatch.setattr(prep, "prepare_artifact", lambda path, **kw: kw["producer"]())
    with pytest.raises(ValueError, match="Capacity rehearsal output already exists"):
        cap.fit_native_graph(runtime, output, policy=None, graph_factory=lambda: runtime)
    assert sentinel.read_text() == "preserve"
    assert not output.exists()
