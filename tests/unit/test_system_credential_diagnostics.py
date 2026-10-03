"""Credential failure categories never expose callback or child secrets."""
from types import SimpleNamespace
import subprocess
import pytest
from test_system_subscription_auth import adapter
from speech_aware_evidence_acquisition.rails.system_subscription_auth import safe_credential_failure
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError, content_hash
from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesHTTP


@pytest.mark.parametrize("failure,code", [
    (subprocess.TimeoutExpired(["secret-command"], 90, output=b"secret"), "pipe-timeout"),
    (OSError("secret-path"), "pipe-os-error"),
    (subprocess.SubprocessError("secret-child"), "pipe-execution-error"),
    (SimpleNamespace(returncode=7, stdout=b"secret", stderr=b"secret"), "pipe-exit-nonzero"),
    (SimpleNamespace(returncode=0, stdout=b"\xff", stderr=b"secret"), "pipe-response-non-ascii"),
    (SimpleNamespace(returncode=0, stdout=b"secret token", stderr=b"secret"), "pipe-response-invalid"),
])
def test_typed_credential_error_uses_allowlisted_category(tmp_path, monkeypatch, failure, code):
    def run(*args, **kwargs):
        if isinstance(failure, Exception):
            raise failure
        return failure
    monkeypatch.setattr("subprocess.run", run)
    with pytest.raises(PolicyError) as error:
        adapter(tmp_path)()
    report = safe_credential_failure(error.value)
    assert report == {"category": code, "phase": "before-http-post", "http_post_entered": False}
    assert "secret" not in str(error.value) + str(report)


def test_pin_and_unreadable_adapter_have_distinct_safe_categories(tmp_path):
    auth = adapter(tmp_path)
    auth.script_local.write_text("changed")
    with pytest.raises(PolicyError) as error:
        auth()
    assert safe_credential_failure(error.value)["category"] == "adapter-pin-mismatch"
    auth.script_local.unlink()
    with pytest.raises(PolicyError) as error:
        auth()
    assert safe_credential_failure(error.value)["category"] == "adapter-unreadable"


def test_http_failure_keeps_safe_category_and_never_posts(tmp_path, monkeypatch):
    auth = adapter(tmp_path)
    monkeypatch.setattr("subprocess.run", lambda *a, **k: SimpleNamespace(returncode=7, stdout=b"secret", stderr=b"secret"))
    class Connection:
        def __init__(self, *a, **k): pass
        def request(self, *a, **k): pytest.fail("no HTTP POST is allowed")
        def close(self): pass
    monkeypatch.setattr("http.client.HTTPSConnection", Connection)
    endpoint = "https://api.openai.com/v1/responses"
    admission = {"status": "admitted", "endpoint": endpoint, "paid_api_spend": 0,
                 "provider_profile": "responses-v1", "output_cap_enforcement": "provider-hard-limit",
                 "budget_profile": "provider-hard-limit", "protocol_sha256": "a" * 64,
                 "model_version": "fixture"}
    admission["sha256"] = content_hash(admission)
    client = ResponsesHTTP(endpoint, bearer=auth, admission=admission)
    with pytest.raises(PolicyError, match="registered credential unavailable") as error:
        list(client.events({"model": "fixture"}))
    assert safe_credential_failure(error.value)["category"] == "pipe-exit-nonzero"
    assert "secret" not in str(error.value)
    assert safe_credential_failure(PolicyError("secret callback text"))["category"] == "callback-unclassified"


@pytest.mark.parametrize("known", [False, True])
def test_failed_reservation_keeps_unknown_usage_and_only_safe_diagnostics(tmp_path, known):
    import json
    from speech_aware_evidence_acquisition.rails.system_subscription_auth import CredentialFailure
    from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesProposer
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
    from test_system_proposer_capsule import fixture
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    class Client:
        admission = None
        last_response_metadata = None
        def events(self, request, *, raw_sink=None):
            error = CredentialFailure("pipe-timeout") if known else RuntimeError("secret callback text")
            safe = safe_credential_failure(error)
            raise CredentialFailure(safe["category"], transport=True) from None
            yield
    reservations = []
    audit = tmp_path / "audit"
    transport = ResponsesProposer(capsule, Client(), audit_dir=audit,
        input_counter=lambda request: 100, before_contact=reservations.append, contact_cap=4)
    with pytest.raises(PolicyError, match="registered credential unavailable"):
        transport(capsule.request())
    result = json.loads((audit / "outcome.json").read_text())
    assert len(reservations) == result["attempted_contacts"] == result["unmetered_contacts"] == 1
    assert result["usage_complete"] is False and result["retry_permitted"] is False
    assert result["credential_failure"]["category"] == ("pipe-timeout" if known else "callback-unclassified")
    assert result["credential_failure"]["http_post_entered"] is False
    assert "secret" not in (audit / "outcome.json").read_text()
    assert not (audit / "contact-001/usage.json").exists()
    assert (audit / "contact-001/response.sse").read_bytes() == b""


def test_foreign_or_changed_diagnostic_cannot_export_arbitrary_text():
    from speech_aware_evidence_acquisition.rails.system_subscription_auth import CredentialFailure
    error = CredentialFailure("pipe-timeout")
    error.category = "secret"
    assert safe_credential_failure(error)["category"] == "callback-unclassified"
