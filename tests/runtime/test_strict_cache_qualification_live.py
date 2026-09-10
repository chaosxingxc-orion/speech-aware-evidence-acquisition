"""Explicitly registered, attach-only strict-cache service qualification.

Ordinary pytest runs skip this module. The root supplies a committed experiment
and a live worker capability only during the isolated qualification session.
No server is started, stopped, retried, or used for scientific answering here.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.configured_transport import (
    build_configured_transport,
)
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.core.flight.lease import WorkerExecutionPolicy
from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.slices import (
    SliceRegistry,
)
from speech_aware_evidence_acquisition.core.preparation import (
    canonical_bytes,
    digest as canonical_digest,
    load_artifact,
)
from speech_aware_evidence_acquisition.core.preparation_encoding import (
    DEFAULT_INSTRUCTION,
    _slice as window_source_slice,
    window_encoding_sources,
)
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WINDOW_FEATURE_INVENTORY_KIND,
)
from speech_aware_evidence_acquisition.core.session.worker import (
    LeaseCheckedTransport,
    attach_worker_session,
)
from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient

pytestmark = pytest.mark.skipif(
    os.environ.get("SAEA_RUN_REGISTERED_CACHE_QUALIFICATION") != "1",
    reason="requires a registered root-owned isolated runtime qualification",
)


def _file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_registered_strict_cache_service():
    repo = Path(os.environ["SAEA_QUALIFICATION_REPO"]).resolve()
    data = Path(os.environ["SPEECHRL_DATA_DIR"]).resolve()
    name = os.environ["SAEA_QUALIFICATION_EXPERIMENT"]
    experiment_path = repo / "configs" / "experiment" / (name + ".json")
    assert experiment_path.parent == repo / "configs" / "experiment"
    experiment = json.loads(experiment_path.read_bytes())
    cells = experiment["cells"]
    assert len(cells) == 1
    cell = cells[0]
    assert cell["readiness"]["state"] == "ready"
    config = compose(
        repo,
        cell["model_fragment"],
        cell["dataset_fragment"],
        cell["baseline_fragment"],
        name,
    ).values
    spec = config["runtime_cache_qualification"]
    assert spec["cases"] == ["hit", "missing", "malformed", "decode-failure"]
    assert config["decoding_params"]["max_tokens"] == 1
    assert config["task_instruction"] == DEFAULT_INSTRUCTION
    assert "prepared_window_feature_cache" not in config
    assert config["server_env"]["LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT"] == "1"
    assert "--no-mmproj-offload" in config["server_args"]
    assert _file_hash(spec["fault_library"]["path"]) == spec["fault_library"]["sha256"]
    assert config["server_env"]["LD_PRELOAD"] == spec["fault_library"]["path"]
    trigger = Path(config["server_env"]["SAEA_CACHE_DECODE_FAULT_TRIGGER"])
    assert trigger.is_absolute() and trigger.is_relative_to(data / "coordination")
    assert not trigger.exists()

    inventory_path = data / spec["inventory"]["relpath"]
    wrapper = json.loads(inventory_path.read_bytes())
    inventory = load_artifact(
        inventory_path,
        expected_sha256=spec["inventory"]["sha256"],
        kind=WINDOW_FEATURE_INVENTORY_KIND,
        inputs=wrapper["inputs"],
    )
    sources = sorted(
        window_encoding_sources(inventory).values(),
        key=lambda source: (source["sample_id"], source["iteration"]),
    )
    assert len(sources) == 4
    assert [source["sha256"] for source in sources] == spec["ordered_audio_sha256"]
    for source in sources:
        assert _file_hash(data / source["media_relpath"]) == source["sha256"]
        assert (
            _file_hash(data / source["parent_media_relpath"]) == source["parent_sha256"]
        )
    cache = Path(config["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"]).resolve()
    assert cache == Path(spec["isolated_cache"]).resolve()
    assert cache != Path(spec["original_cache"]).resolve()
    fixture = json.loads((data / spec["fixture_receipt"]["relpath"]).read_bytes())
    assert (
        _file_hash(data / spec["fixture_receipt"]["relpath"])
        == spec["fixture_receipt"]["sha256"]
    )
    assert fixture["ordered_audio_sha256"] == spec["ordered_audio_sha256"]
    assert fixture["cache_root"] == str(cache)
    expected_cache = fixture["isolated_files"]
    assert {p.name: _file_hash(p) for p in cache.glob("*.feat")} == expected_cache
    original_files = fixture["original_files"]
    for path, digest in original_files.items():
        assert _file_hash(path) == digest

    token = json.loads(Path(os.environ["SAEA_QUALIFICATION_LEASE_FILE"]).read_bytes())
    assert (
        token["run_id"] == cell["run_id"] and token["attempt_id"] == cell["attempt_id"]
    )
    policy = WorkerExecutionPolicy(
        expected_session_id=experiment["service_session_id"],
        lease_token=token["token"],
    )
    runtime = build_flight_runtime(
        repo,
        data,
        model=cell["model_fragment"],
        dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"],
        experiment=name,
        run_id=cell["run_id"],
        attempt_id=cell["attempt_id"],
        runtime_root=Path("/home/chao"),
        lock_path=Path(os.environ["SAEA_DATASET_LOCK"]),
        execution_policy=policy,
    )
    context = runtime.preparation_context()
    assert set(context["sample_ids"]) == {source["sample_id"] for source in sources}
    assert context["execution_plan"].planned_model_calls == 4
    plan, gate = runtime.authorize_preparation_client(contact_cap=4)

    def guard():
        policy.assert_lease(data, run_id=cell["run_id"], attempt_id=cell["attempt_id"])

    guard()
    session_dir, document, session = attach_worker_session(
        policy=policy,
        data_root=data,
        run_id=cell["run_id"],
        attempt_id=cell["attempt_id"],
        required_identity=context["required_identity"],
        runtime_receipt=context["runtime_receipt"],
        runtime_root=Path("/home/chao"),
    )
    assert document["session_id"] == experiment["service_session_id"]
    transport = build_configured_transport(
        config,
        data,
        session=session,
        repo_root=repo,
        runtime_receipt=context["runtime_receipt"],
        runtime_root=Path("/home/chao"),
    )
    kwargs = runtime.frozen_core_client_kwargs(
        plan=plan,
        gate=gate,
        transport=LeaseCheckedTransport(transport, guard),
    )
    binding = kwargs["binding"]
    registry = SliceRegistry(
        data_root=data,
        run_id=spec["source_run_id"],
        parent_facts={
            sample_id: (
                binding.media_relpaths[sample_id],
                binding.sample_facts[sample_id][0],
            )
            for sample_id in binding.allowed_sample_ids
        },
    )
    fit_pin = spec["actual_request_fit"]
    fit_path = data / fit_pin["relpath"]
    fit_wrapper = json.loads(fit_path.read_bytes())
    fit = load_artifact(
        fit_path,
        expected_sha256=fit_pin["sha256"],
        kind="request-fit",
        inputs=fit_wrapper["inputs"],
    )
    assert fit_wrapper["contact_class"] == "tokenizer"
    assert fit["session_id"] == document["session_id"]
    assert fit["session_identity_sha256"] == canonical_digest(context["required_identity"])
    assert fit["sample_count"] == 4 and fit["every_request_fits"] is True
    assert fit["contacts"] == 5 and fit["generation_contacts"] == 0
    fit_hashes = []
    for row in fit["rows"]:
        assert row["maximum_completion_tokens"] == 1
        assert row["slot_tokens"] == context["geometry"]["slot_tokens"]
        assert row["fit_multiple"] == 2.0
        assert row["fits"] is True and row["margin_tokens"] >= 0
        assert row["measurement"] == "resident-multimodal-input-tokens"
        fit_hashes.append(row["request_body_sha256"])
    assert len(fit_hashes) == len(set(fit_hashes)) == 4

    client = FrozenCoreClient(**kwargs, slice_registry=registry)
    output = data / experiment["output_relpath"]
    output.parent.mkdir(parents=True, exist_ok=True)
    assert not output.exists()
    journal = output.with_name(output.name + ".events.jsonl")
    assert not journal.exists()
    server_log = Path(session_dir) / "server.log"
    start_offset = server_log.stat().st_size
    outcomes = []
    closed = None
    try:
        prepared = []
        request_hashes = []
        for source in sources:
            client.register_slice(window_source_slice(source))
            request = client.prepare_request(
                (
                    {"role": "system", "content": DEFAULT_INSTRUCTION},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "media_relpath": source["media_relpath"],
                            }
                        ],
                    },
                ),
                decoding_params=dict(config["decoding_params"]),
            )
            prepared.append(request)
            request_hashes.append(
                canonical_digest(transport.render_request(request.payload_bytes))
            )
        assert sorted(request_hashes) == sorted(fit_hashes)
        with journal.open("x") as events:
            for case, request, request_hash in zip(
                spec["cases"], prepared, request_hashes, strict=True
            ):
                guard()
                if case == "decode-failure":
                    with trigger.open("xb") as marker:
                        marker.write(
                            b"Inject one registered embedded decode failure.\n"
                        )
                before = server_log.stat().st_size
                error = None
                try:
                    client.complete_prepared(request)
                except FrozenCoreError as caught:
                    error = str(caught)
                segment = server_log.read_bytes()[before:]
                row = {
                    "case": case,
                    "request_body_sha256": request_hash,
                    "request_id": client.last_attempted_request_id,
                    "success": error is None,
                    "server_log_sha256": hashlib.sha256(segment).hexdigest(),
                    "error_sha256": None
                    if error is None
                    else hashlib.sha256(error.encode()).hexdigest(),
                }
                outcomes.append(row)
                events.write(json.dumps(row) + "\n")
                events.flush()
                os.fsync(events.fileno())
                if case == "hit":
                    assert error is None and b"mtmd feat-cache HIT" in segment
                else:
                    assert error is not None and "server returned HTTP" in error
                    expected = (
                        b"feat-cache required hit decode failed"
                        if case == "decode-failure"
                        else b"feat-cache required hit missing or invalid"
                    )
                    assert expected in segment
                    if case == "decode-failure":
                        assert b"SAEA_INJECTED_EMBEDDED_DECODE_FAILURE" in segment
                assert b"encoding mtmd batch" not in segment
                assert b"falling back to encode" not in segment
        closed = client.close()
        assert closed["cost"]["calls_used"] == 4
        assert len(client.timings) == 1
        assert {p.name: _file_hash(p) for p in cache.glob("*.feat")} == expected_cache
        for path, digest in original_files.items():
            assert _file_hash(path) == digest
        log_bytes = server_log.read_bytes()[start_offset:]
        assert log_bytes.count(b"SAEA_INJECTED_EMBEDDED_DECODE_FAILURE") == 1
        result = {
            "schema": "saea-strict-cache-runtime-qualification-v1",
            "state": "passed",
            "run_id": cell["run_id"],
            "attempt_id": cell["attempt_id"],
            "session_id": document["session_id"],
            "cases": outcomes,
            "actual_request_fit": fit_pin,
            "cost": closed["cost"],
            "trace_manifest_hash": closed["trace_manifest_hash"],
            "server_log_start_offset": start_offset,
            "server_log_segment_sha256": hashlib.sha256(log_bytes).hexdigest(),
            "limits": "Isolated fault-injected runtime proof only; no scientific answer or score.",
        }
        with output.open("xb") as stream:
            stream.write(canonical_bytes(result))
    finally:
        if closed is None:
            client.close()
