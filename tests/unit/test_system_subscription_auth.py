"""Own-app secrets stay in the private pipe and never enter diagnostics."""
import hashlib
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.system_subscription_auth import SubscriptionBearer
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def adapter(tmp_path):
    script = tmp_path / "auth.mjs"
    script.write_text("synthetic adapter")
    return SubscriptionBearer(node="node.exe", script_windows="C:/auth.mjs", script_local=script,
                              script_sha256=hashlib.sha256(script.read_bytes()).hexdigest())


def test_private_pipe_omits_unrelated_environment(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    monkeypatch.setenv("CODEX_THREAD_ID", "must-not-inherit")
    def run(args, **kwargs):
        seen.append(kwargs)
        return SimpleNamespace(returncode=0, stdout=b"synthetic-own-token", stderr=b"")
    monkeypatch.setattr("subprocess.run", run)
    assert adapter(tmp_path)() == "synthetic-own-token"
    assert "OPENAI_API_KEY" not in seen[0]["env"]
    assert "CODEX_THREAD_ID" not in seen[0]["env"]
    assert seen[0]["env"]["SAEA_AUTH_INTERNAL_PIPE"] == "1"


def test_failed_auth_never_exposes_child_streams(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.run", lambda *a, **k: SimpleNamespace(
        returncode=1, stdout=b"secret-stdout", stderr=b"secret-stderr"))
    with pytest.raises(PolicyError) as error:
        adapter(tmp_path)()
    assert "secret" not in str(error.value)


def test_adapter_pin_precedes_process(tmp_path, monkeypatch):
    auth = adapter(tmp_path)
    auth.script_local.write_text("changed")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: pytest.fail("must not start"))
    with pytest.raises(PolicyError, match="changed"):
        auth()


def test_physical_own_app_directory_is_an_explicit_nonsecret_argument(tmp_path, monkeypatch):
    auth = adapter(tmp_path)
    auth.app_root_windows = "C:/registered/saea-system-proposer"
    seen = []
    def run(args, **kwargs):
        seen.append(args)
        return SimpleNamespace(returncode=0, stdout=b"synthetic-own-token", stderr=b"")
    monkeypatch.setattr("subprocess.run", run)
    assert auth() == "synthetic-own-token"
    assert seen == [["node.exe", "C:/auth.mjs", "credential-pipe", auth.app_root_windows]]
