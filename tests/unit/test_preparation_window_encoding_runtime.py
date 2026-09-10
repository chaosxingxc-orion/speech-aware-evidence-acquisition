"""Synthetic attachment and pre-contact checks for configured window encoding."""

from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_window_encoding import (
    prepare_window_feature_encoding,
)


def test_absent_encoder_config_refuses_before_authorization(tmp_path):
    calls = []
    runtime = SimpleNamespace(
        preparation_context=lambda: {"values": {}},
        authorize_preparation_client=lambda **kw: calls.append(kw),
    )
    with pytest.raises(PreparationError, match="window_feature_preparation"):
        prepare_window_feature_encoding(
            runtime, tmp_path / "output.json", policy=object()
        )
    assert calls == []


def test_non_preprocess_runtime_refuses_before_any_attachment(tmp_path):
    runtime = SimpleNamespace(
        preparation_context=lambda: {
            "values": {
                "decoding_params": {"max_tokens": 1},
                "window_feature_preparation": {
                    "inventory_relpath": "input.json",
                    "inventory_sha256": "a" * 64,
                    "source_run_id": "source-run",
                    "expected_n_embd": 4,
                    "instruction": "Observe the speech.",
                },
            },
            "runtime_receipt": {"role": "inference"},
        }
    )
    with pytest.raises(PreparationError, match="preprocess"):
        prepare_window_feature_encoding(
            runtime, tmp_path / "output.json", policy=object()
        )


def _world(tmp_path):
    import json
    from test_preparation_runtime import _world as runtime_world
    from test_preparation_feature_cache import _batch
    from speech_aware_evidence_acquisition.core.preparation_runtime import (
        verify_feature_encoder_runtime,
    )
    from speech_aware_evidence_acquisition.core.preparation_windows import (
        prepare_window_feature_inventory,
    )
    from speech_aware_evidence_acquisition.core.session import load_runtime_receipt
    from speech_aware_evidence_acquisition.core.session.serving import (
        serving_session_dir,
        SESSION_RECEIPT_NAME,
    )

    repo, runtime_root, data, _, receipt, receipt_path = runtime_world(tmp_path)
    values = {
        "runtime_receipt": "receipts/preprocess.json",
        "model_materialization_root": str(data),
        "transport": "llama-server",
        "arm": "bare-core",
        "decoding_params": {"temperature": 0, "max_tokens": 1},
    }
    identity = verify_feature_encoder_runtime(
        repo_root=repo,
        data_root=data,
        runtime_root=runtime_root,
        values={
            **values,
            "feature_encoder_runtime_receipt": "receipts/preprocess.json",
        },
        generation_receipt=receipt,
        receipt_loader=load_runtime_receipt,
    ).encoder_identity
    batch = _batch(data, run="source-run")
    artifact = data / "inventory.json"
    prepared = prepare_window_feature_inventory(
        artifact,
        batches={"source-run": batch},
        data_root=data,
        encoder_identity=identity,
    )
    cache = tmp_path / "cache"
    cache.mkdir()
    values["server_env"] = {"LLAMA_MTMD_FEAT_CACHE_DIR": str(cache)}
    values["window_feature_preparation"] = {
        "inventory_relpath": "inventory.json",
        "inventory_sha256": prepared["sha256"],
        "source_run_id": "source-run",
        "expected_n_embd": 4,
        "instruction": "Observe the complete speech signal. Respond with OK.",
    }
    plan = SimpleNamespace(planned_model_calls=1)
    context = dict(
        values=values,
        runtime_receipt=receipt,
        data_root=data,
        repo_root=repo,
        runtime_root=runtime_root,
        execution_plan=plan,
        sample_ids=["sample-1"],
        run_id="encoding-run",
        attempt_id="attempt",
        required_identity={"role": "preprocess"},
    )
    events = []
    binding = SimpleNamespace(
        allowed_sample_ids={"sample-1"},
        media_relpaths={"sample-1": batch.source_bindings[0]["parent_media_relpath"]},
        sample_facts={"sample-1": (100, 16000)},
    )

    def authorize(**kw):
        events.append("gate")
        assert kw == {"contact_cap": 1}
        return plan, object()

    runtime = SimpleNamespace(
        preparation_context=lambda: context,
        authorize_preparation_client=authorize,
        frozen_core_client_kwargs=lambda **kw: {
            **kw,
            "binding": binding,
            "run_dir": data / "run",
            "arm": "bare-core",
        },
    )
    policy = SimpleNamespace(
        expected_session_id="cpu-session",
        assert_lease=lambda *_a, **_k: events.append("lease"),
    )
    directory = serving_session_dir(data, "cpu-session")
    directory.mkdir(parents=True)
    (directory / SESSION_RECEIPT_NAME).write_text(
        json.dumps({"synthetic": "verified by injected attacher"})
    )

    def attach(**kw):
        events.append("attach")
        return (
            directory,
            {"session_id": "cpu-session"},
            SimpleNamespace(role="preprocess"),
        )

    def transport(*_a, **_k):
        events.append("transport")
        return lambda _: b""

    clients = []
    from test_preparation_encoding import Client
    from test_preparation_feature_cache import _write_chunk

    class ProducingClient(Client):
        def __init__(self, **kw):
            super().__init__()
            clients.append(self)
            events.append("client")
            assert kw["slice_registry"].__class__.__name__ == "SliceRegistry"

        def complete(self, *args, **kw):
            value = super().complete(*args, **kw)
            source = batch.source_bindings[0]
            _write_chunk(cache, (data / source["media_relpath"]).read_bytes())
            return value

    options = dict(
        policy=policy,
        attach=attach,
        transport_factory=transport,
        client_factory=ProducingClient,
    )
    return runtime, options, context, events, clients, tmp_path / "encoding.json"


def test_configured_encoder_attaches_after_gate_and_reuses_without_contact(tmp_path):
    runtime, options, context, events, clients, output = _world(tmp_path)
    result = prepare_window_feature_encoding(runtime, output, **options)
    assert result["cache"] == "cold" and len(clients) == 1 and clients[0].closed == 1
    assert events.index("gate") < events.index("attach") < events.index("client")
    assert events.count("lease") >= 2
    events.clear()
    runtime.authorize_preparation_client = lambda **_: pytest.fail(
        "warm encoding must not reopen a gate/client"
    )
    assert (
        prepare_window_feature_encoding(runtime, output, **options)["cache"] == "warm"
    )
    assert events == [] and len(clients) == 1


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-roster",
        "wrong-prefix",
        "wrong-budget",
        "validation-mode",
        "wrong-parent",
        "wrong-inventory-hash",
    ],
)
def test_configured_input_faults_refuse_before_gate_or_attachment(tmp_path, fault):
    runtime, options, context, events, clients, output = _world(tmp_path)
    if fault == "wrong-roster":
        context["sample_ids"] = ["different"]
    elif fault == "wrong-prefix":
        context["values"]["window_feature_preparation"]["source_run_id"] = "different"
    elif fault == "wrong-budget":
        context["execution_plan"].planned_model_calls = 2
    elif fault == "validation-mode":
        context["values"]["server_env"]["LLAMA_MTMD_FEAT_CACHE_VALIDATE"] = "0"
    elif fault == "wrong-inventory-hash":
        context["values"]["window_feature_preparation"]["inventory_sha256"] = "0" * 64
    else:
        (context["data_root"] / "datasets/e21/sample-1.wav").write_bytes(
            b"changed parent"
        )
    with pytest.raises(PreparationError):
        prepare_window_feature_encoding(runtime, output, **options)
    assert events == [] and clients == [] and not output.exists()


def test_missing_resident_session_never_constructs_encoder_client(tmp_path):
    runtime, options, _context, events, clients, output = _world(tmp_path)

    def absent(**_kw):
        raise PreparationError("required resident session absent")

    options["attach"] = absent
    with pytest.raises(PreparationError, match="resident session absent"):
        prepare_window_feature_encoding(runtime, output, **options)
    assert events == ["gate", "lease"] and clients == []


@pytest.mark.parametrize("parameters", [{"max_tokens": 2}, {"max_tokens": True}, {}])
def test_invalid_encoding_parameters_refuse_before_opening_attempt(
    tmp_path, parameters
):
    runtime, options, context, events, clients, output = _world(tmp_path)
    context["values"]["decoding_params"] = parameters
    with pytest.raises(PreparationError, match="max_tokens"):
        prepare_window_feature_encoding(runtime, output, **options)
    assert events == [] and clients == []


def test_interrupted_encoding_refuses_without_leaving_client_open(tmp_path):
    runtime, options, _context, _events, clients, output = _world(tmp_path)
    output.with_name(output.name + ".encoder-started.json").write_text("{}")
    with pytest.raises(PreparationError, match="new registered attempt"):
        prepare_window_feature_encoding(runtime, output, **options)
    assert len(clients) == 1 and clients[0].closed == 1
