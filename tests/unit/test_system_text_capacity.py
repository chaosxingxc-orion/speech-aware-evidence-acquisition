"""The capacity rehearsal is nongenerative and preserves full output reserves."""
from speech_aware_evidence_acquisition.analysis.system_text_capacity import stress_body
import json
from types import SimpleNamespace
import pytest


def test_stress_body_covers_tool_result_history_and_revision_without_truncation():
    messages = [{"role": "system", "content": "Task contract"},
                {"role": "user", "content": [{"type": "text", "text": "Speech placeholder"}]}]
    body = stress_body(messages, [{"type": "function", "function": {"name": "lookup"}}],
                       ["longest value", "second value"], 13, 512)
    assert body["messages"][:2] == messages
    assert len([m for m in body["messages"] if m["role"] == "assistant"]) == 13
    assert body["max_tokens"] == 512
    assert body["messages"][-2]["role"] == "tool"
    assert "longest value" in body["messages"][-2]["content"]
    assert "second value" in body["messages"][-2]["content"]
    assert body["tools"][0]["function"]["name"] == "lookup"
    assert messages[1]["content"][0]["text"] == "Speech placeholder"


@pytest.mark.parametrize("low_padding,wide", [(False, False), (True, False), (False, True)])
def test_fit_uses_lease_and_journals_before_counting(tmp_path, monkeypatch, low_padding, wide):
    from speech_aware_evidence_acquisition.analysis.system_text_capacity import fit_stress
    import speech_aware_evidence_acquisition.core.driver.speech_native as driver
    import speech_aware_evidence_acquisition.core.preparation_fit as pf
    import speech_aware_evidence_acquisition.core.session.resource_guard as resources
    import speech_aware_evidence_acquisition.rails.controllers as controllers
    import speech_aware_evidence_acquisition.rails.phase_tools as phase_tools
    import speech_aware_evidence_acquisition.core.bundle.git_commit as git_commit
    monkeypatch.setattr(git_commit, "require_clean_study_repo", lambda _: "d" * 40)
    touched = []
    snapshot = SimpleNamespace(values=[SimpleNamespace(value_id=str(i), content="z" * i) for i in (10, 80, 40)],
                               content_hash=lambda: "a" * 64)
    binding = SimpleNamespace(store=lambda _: SimpleNamespace(snapshot=snapshot), composite_snapshot=snapshot,
                              model_evidence_block=lambda _, **kw: {"text": kw["content"]})
    context = {"values": {"policy": "test", "speech_feature_root": str(tmp_path)}, "sample_ids": ["s1"],
               "data_root": tmp_path, "runtime_root": tmp_path, "run_id": "fit", "attempt_id": "a",
               "required_identity": {}, "runtime_receipt": {}}
    runtime = SimpleNamespace(_repo_root=tmp_path, preparation_context=lambda: context, _samples=["s1"],
        _phase_prompt_payloads=lambda *a: {"planner": json.dumps([{"role": "user", "content": "text"}]).encode()},
        _knowledge_store_binding=binding, _composed=SimpleNamespace(config_hash="b" * 64),
        authorize_preparation_contacts=lambda **kw: touched.append("authorized"),
        speech_packet_bindings=lambda: {"s1": {"packet_id": "p1", "sha256": "c" * 64}})
    class Client:
        def request_json(self, method, path, payload=None):
            assert touched and "lease" in touched
            assert (tmp_path / "fit.json.contacts.jsonl").read_text().strip()
            if path == "/props": return {"media_marker": "MEDIA"}
            if path == "/apply-template": return {"prompt": "boundMEDIA"}
            text = payload["content"]
            count = (1 if low_padding else 512) if text.startswith(" evidence") else len(text)
            if wide and text == "bound": count = 24576
            return {"tokens": [0] * count}
    monkeypatch.setattr(driver, "_LoopbackPromptAuditClient", lambda **kw: Client())
    monkeypatch.setattr(controllers, "default_phase_program", lambda _: None)
    def dispatcher(*a, **kw):
        with pytest.raises(ValueError, match="never execute"):
            kw["tool_contact"]()
        return SimpleNamespace(native_tool_schemas=lambda: [])
    monkeypatch.setattr(phase_tools, "build_phase_tools", dispatcher)
    monkeypatch.setattr(resources, "resource_limits", lambda _: None)
    packet_counter = pf.packet_token_counts
    def counts(payload, **kw):
        return packet_counter(payload, **kw, loader=lambda *a, **k: [SimpleNamespace(chunks=[SimpleNamespace(n_tokens=10)])])
    monkeypatch.setattr(pf, "packet_token_counts", counts)
    session = SimpleNamespace(host="127.0.0.1", port=1, model_files=[SimpleNamespace(path="decoder", sha256="c" * 64)])
    attach = lambda **kw: (tmp_path, {}, session)
    policy = SimpleNamespace(assert_lease=lambda *a, **kw: touched.append("lease"))
    path = tmp_path / "fit.json"
    if low_padding:
        with pytest.raises(ValueError, match="padding"):
            fit_stress(runtime, path, policy=policy, contact_cap=20, attach=attach)
        assert not path.exists()
    else:
        fit_stress(runtime, path, policy=policy, contact_cap=20, attach=attach)
        d = json.loads(path.read_text())["output"]
        assert d["selected_value_tokens"] == [80, 40]
        assert d["every_request_fits"] is (not wide)
        assert d["generation_contacts"] == 0
        assert d["rows"][0]["maximum_completion_tokens"] == 512
    assert touched[0] == "authorized"
