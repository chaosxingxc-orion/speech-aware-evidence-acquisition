"""Synthetic parent-flight/replay parity and fail-closed provenance tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import test_e21_repair_loop as fixtures


from speech_aware_evidence_acquisition.core.bundle import BundleError, verify_bundle


@pytest.fixture(autouse=True)
def _drop_synthetic_registrations():
    """The synthetic delivery rules and scorers these tests register into the process-global
    ``core.base.RESPONSE_POSTPROCESSORS`` / ``SCORERS`` (every such id starts ``synthetic-``) are removed after
    each test, so no later module -- test_engineering_base_check's registry/source agreement -- sees them."""

    from speech_aware_evidence_acquisition.core.base import RESPONSE_POSTPROCESSORS, SCORERS

    before = {id(registry): set(registry._entries) for registry in (RESPONSE_POSTPROCESSORS, SCORERS)}
    yield
    for registry in (RESPONSE_POSTPROCESSORS, SCORERS):
        for name in set(registry._entries) - before[id(registry)]:
            if name.startswith("synthetic-"):
                registry._entries.pop(name, None)
from speech_aware_evidence_acquisition.core.bundle.delivery import build_delivery_bundle
from speech_aware_evidence_acquisition.core.config import compose

repair_repo = fixtures.repair_repo

FREE = "e21-free-refresh-delivery-v1"
CONSTRAINED = "e21-entity-repair-substitutions-v1"


@pytest.fixture
def generation(synthetic_world, tmp_path, repair_repo, monkeypatch):
    def run(*, policy="obs-repair-loop", transport=None, declared_deliveries=True, **overrides):
        _, repo, digest = repair_repo
        values = dict(fixtures._composed(digest, policy=policy, **overrides).values)
        experiment = {
            "experiment_id": values.pop("experiment_id"),
            "cells": [
                {
                    "cell_id": "generation",
                    "model_fragment": "m",
                    "dataset_fragment": "d",
                    "baseline_fragment": "b",
                }
            ],
            "delivery_derivatives": [
                {
                    "cell_id": "constrained",
                    "parent_cell_id": "generation",
                    "response_postprocessor": CONSTRAINED,
                    "response_postprocessor_params": {"max_substituted_fraction": 0.25},
                },
                {
                    "cell_id": "free",
                    "parent_cell_id": "generation",
                    "response_postprocessor": FREE,
                    "response_postprocessor_params": {},
                },
            ],
        }
        if not declared_deliveries:
            experiment.pop("delivery_derivatives")
        for kind, name, document in (
            ("model", "m", {}),
            ("dataset", "d", {}),
            ("baseline", "b", values),
            ("experiment", "e", experiment),
        ):
            path = repo / "configs" / kind / f"{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(document), encoding="utf-8")
        fixtures._git(repo, "add", "configs")
        fixtures._git(repo, "commit", "-q", "-m", "predeclare both delivery rules")
        composed = compose(repo, "m", "d", "b", "e")
        monkeypatch.setattr(fixtures, "_composed", lambda *_args, **_kw: composed)
        if transport is None:
            transport = fixtures._transport_factory(
                lambda text: "  " + text.replace("Ponton", "Pontone") + " "
            )
        parent, _ = fixtures._run(synthetic_world, tmp_path, repair_repo, transport)
        kwargs = dict(
            parent_manifest=parent,
            repo_root=repo,
            experiment_path=repo / "configs/experiment/e.json",
            data_root=synthetic_world.data_root,
        )
        return parent, kwargs

    return run


def _build(tmp_path, kwargs, cell="constrained"):
    return build_delivery_bundle(
        **kwargs, derivative_cell_id=cell, output_dir=tmp_path / f"derived-{cell}"
    )


@pytest.fixture
def phase_generation(synthetic_world, tmp_path, repair_repo, generation):
    """A real verified two-phase parent with hash-bound trace artifacts."""
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import canonical
    from speech_aware_evidence_acquisition.core.base import RESPONSE_POSTPROCESSORS
    from speech_aware_evidence_acquisition.core.config import protocol_hash
    from speech_aware_evidence_acquisition.contracts import TraceRecord
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
    from speech_aware_evidence_acquisition.core.repair_alignment import RepairOutcome
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

    seed_parent_path, seed_kwargs = generation()
    _, repo, digest = repair_repo
    values = dict(fixtures._composed(digest).values)
    values.pop("experiment_id", None)
    for key in ("predecessor_snapshot", "predecessor_binding_receipt"):
        values.pop(key, None)
    values["policy"] = "phase-draft-revise-v1"
    values["decoding_params"] = {"temperature": 0, "max_tokens": 64}
    rule_id = f"synthetic-phase-pair-{tmp_path.name}"

    def rule_factory():
        def join(predecessor, response):
            text = f"{predecessor} || {response}"
            return RepairOutcome(
                text=text,
                refused=False,
                refusal_reason=None,
                substitutions=(),
                rejected={},
                predecessor_tokens=len(predecessor.split()),
                response_tokens=len(response.split()),
                anchor_tokens=0,
                substituted_tokens=0,
                delivery="synthetic-phase-pair",
                text_changed=True,
            )

        return join

    RESPONSE_POSTPROCESSORS.register(rule_id, rule_factory)
    program_sha256 = hashlib.sha256(
        canonical(default_phase_program("phase-draft-revise-v1").as_json())
    ).hexdigest()
    experiment = {
        "experiment_id": "synthetic-phase-delivery",
        "cells": [
            {
                "cell_id": "generation",
                "model_fragment": "m",
                "dataset_fragment": "d",
                "baseline_fragment": "b",
            }
        ],
        "delivery_derivatives": [
            {
                "cell_id": "paired",
                "parent_cell_id": "generation",
                "response_postprocessor": rule_id,
                "response_postprocessor_params": {},
                "source_selector": {
                    "schema": "saea-phase-response-pair-v1",
                    "program_id": "phase-draft-revise-v1",
                    "program_sha256": program_sha256,
                    "predecessor_phase": "draft",
                    "response_phase": "revise",
                },
            }
        ],
    }
    values.pop("delivery_derivatives", None)
    values.pop("cells", None)
    for kind, name, document in (
        ("model", "m", {}),
        ("dataset", "d", {}),
        ("baseline", "b", values),
        ("experiment", "e", experiment),
    ):
        path = repo / "configs" / kind / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8")
    fixtures._git(repo, "add", "configs")
    fixtures._git(repo, "commit", "-q", "-m", "declare synthetic phase delivery")
    composed = compose(repo, "m", "d", "b", "e")

    records, output_rows = {}, []
    for index, sample_id in enumerate(("phase-s1", "phase-s2"), start=1):
        phase_sources = {}
        for phase, text in (("draft", f" draft {index} "), ("revise", f" revised {index} ")):
            request_id = f"opaque-client-{index}-{phase}"
            control_text = f"Run {phase}."
            payload = {
                "request_id": request_id,
                "sample_id": sample_id,
                "decoding_params": {"temperature": 0, "max_tokens": 64},
                "history": [
                    {
                        "turn": 1,
                        "role": "control",
                        "contact_id": f"phase-draft-revise-v1:{phase}:{sample_id}",
                        "content": control_text,
                        "content_sha256": hashlib.sha256(control_text.encode()).hexdigest(),
                    }
                ],
            }
            request = {
                "arm": "synthetic-arm",
                "payload": payload,
                "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest(),
            }
            response = {
                "response_sha256": hashlib.sha256(
                    f"wire:{sample_id}:{phase}".encode()
                ).hexdigest(),
                "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "text": text,
                "usage": {"completion_tokens": 2},
            }
            records[f"{request_id}/request"] = request
            records[f"{request_id}/response"] = response
            phase_sources[phase] = (request_id, request, response, text)
        request_id, request, response, text = phase_sources["revise"]
        output_rows.append(
            {
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": "earnings21-original",
                "arm": "synthetic-arm",
                "text": text,
                "admitted": True,
                "request_sha256": request["payload_sha256"],
                "response_sha256": response["response_sha256"],
                "response_text_sha256": response["response_text_sha256"],
            }
        )
    parent_path = seed_parent_path
    parent_manifest = json.loads(parent_path.read_text(encoding="utf-8"))
    run_dir = parent_path.parent
    run_id = parent_manifest["run_id"]
    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    trace_path = run_dir / f"{run_id}.trace.jsonl"
    trace_manifest_path = run_dir / f"{run_id}.trace-manifest.json"
    outputs_path.write_bytes(b"".join(canonical(row) + b"\n" for row in output_rows))
    trace_documents = []
    trace_hashes = {}
    for record_id, payload in records.items():
        channel = "MODEL_REQUEST" if record_id.endswith("/request") else "MODEL_RESPONSE"
        trace_record = TraceRecord(channel=channel, record_id=record_id, payload=payload)
        trace_documents.append(trace_record.serialize().encode("utf-8") + b"\n")
        trace_hashes[record_id] = trace_record.content_hash()
    trace_path.write_bytes(b"".join(trace_documents))
    trace_manifest_path.write_bytes(canonical({"records": trace_hashes}) + b"\n")
    split_ids = ["phase-s1", "phase-s2"]
    carrier = parent_manifest["split"]["carrier_lock_key"]
    identity = split_identity_hash(prefixed(carrier, split_ids))
    arm = "synthetic-arm"
    parent_manifest["study_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    parent_manifest["arm"] = arm
    parent_manifest["config"] = {
        "fragments": {"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
        "config_hash": composed.config_hash,
    }
    parent_manifest["split"].update(ids=split_ids, count=2, identity_hash=identity)
    parent_manifest["plan"]["split_identity_hash"] = identity
    parent_manifest["protocol_hash"] = protocol_hash(composed.config_hash, arm, identity)
    parent_manifest["plan"]["protocol_hash"] = parent_manifest["protocol_hash"]
    parent_manifest["cost"] = {"calls_used": 4}
    for field, path in (
        ("outputs", outputs_path),
        ("raw_trace", trace_path),
        ("trace_manifest", trace_manifest_path),
    ):
        parent_manifest[field] = {
            "path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    parent_path.write_bytes(canonical(parent_manifest) + b"\n")
    parent = verify_bundle(parent_path)
    return parent, {
        "parent_manifest": parent_path,
        "repo_root": repo,
        "experiment_path": repo / "configs/experiment/e.json",
        "data_root": seed_kwargs["data_root"],
    }


def test_phase_pair_selects_namespaced_trace_sources_and_verifies_deterministically(
    phase_generation, tmp_path
):
    parent, kwargs = phase_generation
    before = parent.manifest_path.read_bytes()
    manifest = build_delivery_bundle(
        **kwargs, derivative_cell_id="paired", output_dir=tmp_path / "phase-derived"
    )
    derived = verify_bundle(manifest)

    assert [row["text"] for row in derived.outputs_rows] == [
        "draft 1 || revised 1",
        "draft 2 || revised 2",
    ]
    assert len(derived.manifest["phase_sources"]) == 2
    assert all(
        source["predecessor_contact_id"].endswith(source["sample_id"])
        and source["response_contact_id"].endswith(source["sample_id"])
        and source["predecessor_max_tokens"] == 64
        and source["response_max_tokens"] == 64
        and source["predecessor_saturated"] is False
        and source["response_saturated"] is False
        for source in derived.manifest["phase_sources"]
    )
    assert "predecessor_receipt" not in derived.manifest
    assert parent.manifest_path.read_bytes() == before
    assert verify_bundle(manifest).manifest == derived.manifest


@pytest.mark.parametrize("delivery_rule", ["synthetic", "slurp"])
def test_flight_runtime_phase_parent_replays_through_declared_derivative(
    tmp_path, monkeypatch, delivery_rule
):
    """The real shared phase runner seals the parent consumed by delivery.

    The SLURP case uses synthetic JSON responses to prove the registered
    delivery rule's shared wiring and diagnostics, not a SLURP corpus run.
    """
    import socket

    import test_flight_runtime as flight_fixtures
    import test_rails_runner as runner_fixtures

    from speech_aware_evidence_acquisition.core.bundle import (
        build_manifest,
        verify_bundle as verify_real_bundle,
    )
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import canonical
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.core_client import (
        FrozenCoreClient,
        build_payload_binding,
    )
    from speech_aware_evidence_acquisition.rails.phase_runner import run_program

    run_id = "SAEA-TEST-PHASE-DELIVERY"
    repo_root, data_root = flight_fixtures._phase_packet_repo(tmp_path, run_id)
    program = default_phase_program("phase-draft-revise-v1")
    program_sha256 = hashlib.sha256(canonical(program.as_json())).hexdigest()
    rule_id = (
        "slurp-intent-slots-delivery-v1"
        if delivery_rule == "slurp"
        else f"synthetic-live-phase-pair-{tmp_path.name}"
    )

    from speech_aware_evidence_acquisition.core.base import RESPONSE_POSTPROCESSORS, SCORERS
    from speech_aware_evidence_acquisition.core.repair_alignment import RepairOutcome

    def rule_factory():
        def join(predecessor, response):
            text = f"{predecessor} || {response}"
            return RepairOutcome(
                text=text,
                refused=False,
                refusal_reason=None,
                substitutions=(),
                rejected={},
                predecessor_tokens=len(predecessor.split()),
                response_tokens=len(response.split()),
                anchor_tokens=0,
                substituted_tokens=0,
                delivery="synthetic-live-phase-pair",
                text_changed=True,
            )

        return join

    if delivery_rule == "synthetic":
        RESPONSE_POSTPROCESSORS.register(rule_id, rule_factory)
    scored_rows = []

    def synthetic_delivery_scorer(outputs_path, lock, root):
        rows = [
            json.loads(line)
            for line in Path(outputs_path).read_text(encoding="utf-8").splitlines()
        ]
        scored_rows.append(rows)
        return {
            "aggregate": {"samples": len(rows)},
            "per_sample": [{"sample_id": row["sample_id"]} for row in rows],
        }

    scorer_names = [
        f"synthetic-delivery-score-a-{tmp_path.name}",
        f"synthetic-delivery-score-b-{tmp_path.name}",
    ]
    for scorer_name in scorer_names:
        SCORERS.register(scorer_name, synthetic_delivery_scorer)
    baseline_path = repo_root / "configs/baseline/b.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["decoding_params"] = {"temperature": 0, "max_tokens": 7}
    baseline["scorers"] = scorer_names
    snapshot = runner_fixtures._knowledge_snapshot()
    snapshot_path = data_root / "knowledge/synthetic-phase-snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot.frozen_json()), encoding="utf-8")
    baseline["knowledge_snapshot_relpath"] = str(snapshot_path.relative_to(data_root))
    baseline["knowledge_snapshot_sha256"] = snapshot.content_hash()
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    experiment_path = repo_root / "configs/experiment/e.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    experiment.update(
        {
            "cells": [
                {
                    "cell_id": "generation",
                    "model_fragment": "m",
                    "dataset_fragment": "d",
                    "baseline_fragment": "b",
                }
            ],
            "delivery_derivatives": [
                {
                    "cell_id": "paired",
                    "parent_cell_id": "generation",
                    "response_postprocessor": rule_id,
                    "response_postprocessor_params": {},
                    "source_selector": {
                        "schema": "saea-phase-response-pair-v1",
                        "program_id": program.program_id,
                        "program_sha256": program_sha256,
                        "predecessor_phase": "draft",
                        "response_phase": "revise",
                    },
                }
            ],
        }
    )
    experiment_path.write_text(json.dumps(experiment), encoding="utf-8")
    flight_fixtures._git(repo_root, "add", "configs")
    flight_fixtures._git(repo_root, "commit", "-q", "-m", "declare phase delivery")

    # The real payload binding probes WAV headers. These tiny files are only
    # synthetic carrier bytes and never leave the fake transport boundary.
    import wave
    import struct

    from speech_aware_evidence_acquisition.core.model import (
        SpeechFeatureChunkData,
        materialize_speech_feature_packet,
    )

    packets = []
    for sample_id in ("s1", "s2"):
        audio_path = data_root / f"{sample_id}.wav"
        with wave.open(str(audio_path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16000)
            stream.writeframes(b"\0\0" * 160)
        packets.append(
            materialize_speech_feature_packet(
                feature_root=tmp_path / flight_fixtures._PROMOTION_DIR,
                packet_id=sample_id,
                audio_sha256=hashlib.sha256(audio_path.read_bytes()).hexdigest(),
                encoder_receipt_sha256="e" * 64,
                decoder_gguf_sha256="d" * 64,
                mmproj_sha256="f" * 64,
                position_mode="mrope_1d",
                causal_attention=True,
                chunks=(
                    SpeechFeatureChunkData(
                        n_tokens=2,
                        n_pos=2,
                        n_embd=4,
                        feature_bytes=struct.pack("<8f", *range(8)),
                        position_bytes=struct.pack(
                            "<8i", 0, 1, 0, 1, 0, 1, 0, 1
                        ),
                    ),
                ),
            )
        )
    promotion_path = tmp_path / "promotion.json"
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    promotion["packets"] = [
        {
            "packet_id": packet.packet_id,
            "packet_sha256": packet.packet_sha256,
            "decoder_gguf_sha256": "d" * 64,
            "mmproj_sha256": "f" * 64,
        }
        for packet in packets
    ]
    promotion_path.write_text(json.dumps(promotion), encoding="utf-8")

    sent_payloads = []

    def transport(request_bytes):
        payload = json.loads(request_bytes.decode("utf-8"))
        sent_payloads.append(payload)
        contact_id = payload["history"][-1]["contact_id"]
        phase = contact_id.split(":")[-2]
        if delivery_rule == "slurp":
            text = json.dumps(
                (
                    {"scenario": "weather", "action": "query", "entities": []}
                    if phase == "draft"
                    else {
                        "scenario": "ignored-slot-label",
                        "entities": [
                            {"type": "location", "filler": payload["sample_id"]}
                        ],
                    }
                )
            )
        else:
            text = f"{phase}-{payload['sample_id']}"
        return json.dumps(
            {"text": text, "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
        ).encode("utf-8")

    def transport_factory(*args, **kwargs):
        return transport

    def forbid_socket(*args, **kwargs):
        raise AssertionError("the synthetic phase flight must not open a socket")

    def forbid_finalizer(*args, **kwargs):
        raise AssertionError("a phase-delivery parent must defer finalization")

    monkeypatch.setattr(socket, "create_connection", forbid_socket)
    monkeypatch.setattr(socket.socket, "connect", forbid_socket)
    runtime = flight_fixtures._make_runtime(
        tmp_path,
        run_id=run_id,
        attempt_id="attempt-phase-delivery",
        repo_root=repo_root,
        happy_path=True,
        phase_runner=run_program,
        client_factory=FrozenCoreClient,
        payload_binding_factory=build_payload_binding,
        carrier_root_resolver=lambda lock, carrier, root: Path(root),
        transport_factory=transport_factory,
        manifest_builder=build_manifest,
        bundle_verifier=verify_real_bundle,
        bundle_finalizer=forbid_finalizer,
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()

    phase_receipt = runtime.run_phases()
    seal = runtime.seal()
    parent_path = Path(seal["manifest_path"])
    parent = verify_real_bundle(parent_path)
    assert seal["delivery_required"] is True
    assert seal["declared_delivery_cells"] == ["paired"]
    assert parent.manifest["required_phase_deliveries"] == [
        experiment["delivery_derivatives"][0]
    ]
    parent_files = {
        path: path.read_bytes()
        for path in (
            parent_path,
            Path(parent.manifest["outputs"]["path"]),
            Path(parent.manifest["raw_trace"]["path"]),
            Path(parent.manifest["trace_manifest"]["path"]),
        )
    }
    from speech_aware_evidence_acquisition.core import scorers

    def forbid_parent_scoring_entry(*args, **kwargs):
        raise AssertionError("required delivery must refuse before the scoring gate")

    monkeypatch.setattr(
        scorers, "_assert_scoring_entry_gate", forbid_parent_scoring_entry
    )
    raw_parent_manifest = parent_path.read_bytes()
    manifest_document = json.loads(raw_parent_manifest)

    # Removing only the additive marker cannot bypass the declaration in the
    # exact experiment blob recorded by study_commit.
    no_marker = dict(manifest_document)
    no_marker.pop("required_phase_deliveries")
    parent_path.write_text(json.dumps(no_marker), encoding="utf-8")
    try:
        unmarked_parent = verify_real_bundle(parent_path)
        with pytest.raises(scorers.ScoringPhaseError, match="deliver"):
            scorers.score_bundle(unmarked_parent, {}, data_root, repo_root=repo_root)
    finally:
        parent_path.write_bytes(raw_parent_manifest)

    # The current working fragment is not an authority over the recorded Git
    # blob. Removing its declaration as well still leaves the parent blocked.
    raw_experiment = experiment_path.read_bytes()
    current_experiment = json.loads(raw_experiment)
    current_experiment.pop("delivery_derivatives")
    experiment_path.write_text(json.dumps(current_experiment), encoding="utf-8")
    parent_path.write_text(json.dumps(no_marker), encoding="utf-8")
    try:
        unmarked_parent = verify_real_bundle(parent_path)
        with pytest.raises(scorers.ScoringPhaseError, match="deliver"):
            scorers.score_bundle(unmarked_parent, {}, data_root, repo_root=repo_root)
    finally:
        experiment_path.write_bytes(raw_experiment)
        parent_path.write_bytes(raw_parent_manifest)

    forged_marker = dict(manifest_document)
    forged_marker["required_phase_deliveries"] = []
    parent_path.write_text(json.dumps(forged_marker), encoding="utf-8")
    try:
        forged_parent = verify_real_bundle(parent_path)
        with pytest.raises(scorers.ScoringPhaseError, match="deliver"):
            scorers.score_bundle(forged_parent, {}, data_root, repo_root=repo_root)
    finally:
        parent_path.write_bytes(raw_parent_manifest)

    contacts_before_derivative = len(sent_payloads)
    derivative_path = build_delivery_bundle(
        parent_manifest=parent_path,
        repo_root=repo_root,
        experiment_path=experiment_path,
        data_root=data_root,
        derivative_cell_id="paired",
        output_dir=tmp_path / "live-phase-derived",
    )
    derivative = verify_real_bundle(derivative_path)

    with pytest.raises(scorers.ScoringPhaseError, match="deliver"):
        scorers.score_bundle(parent, {}, data_root, repo_root=repo_root)
    monkeypatch.setattr(scorers, "_assert_scoring_entry_gate", lambda *args: None)
    scores = scorers.score_bundle(derivative, {}, data_root, repo_root=repo_root)

    assert phase_receipt["contact_count"] == 4
    assert len(sent_payloads) == contacts_before_derivative == 4
    revise_payloads = [
        payload
        for payload in sent_payloads
        if ":revise:" in payload["history"][-1]["contact_id"]
    ]
    if delivery_rule == "slurp":
        assert all(
            '"scenario": "weather"' in payload["history"][-1]["content"]
            for payload in revise_payloads
        )
        assert [json.loads(row["text"]) for row in derivative.outputs_rows] == [
            {
                "scenario": "weather",
                "action": "query",
                "entities": [{"type": "location", "filler": sample_id}],
            }
            for sample_id in ("s1", "s2")
        ]
        assert [
            source["delivery_diagnostics"]
            for source in derivative.manifest["phase_sources"]
        ] == [
            {
                "rows": 1,
                "arm_response_unparsed": 0,
                "arm_response_carried_scenario_or_action": 1,
                "closed_list_unparsed": 0,
            },
            {
                "rows": 1,
                "arm_response_unparsed": 0,
                "arm_response_carried_scenario_or_action": 1,
                "closed_list_unparsed": 0,
            },
        ]
    else:
        assert all(
            f"draft-{payload['sample_id']}" in payload["history"][-1]["content"]
            for payload in revise_payloads
        )
        assert [row["text"] for row in derivative.outputs_rows] == [
            "draft-s1 || revise-s1",
            "draft-s2 || revise-s2",
        ]
    assert derivative.manifest["cost"]["additional_model_contacts"] == 0
    assert list(scores) == scorer_names
    assert scores[scorer_names[0]] == scores[scorer_names[1]]
    assert scores[scorer_names[0]]["aggregate"] == {"samples": 2}
    assert len(scored_rows) == 1
    assert [row["sample_id"] for row in scored_rows[0]] == ["s1", "s2"]
    assert scored_rows[0] == [dict(row) for row in derivative.outputs_rows]
    assert all(
        source["predecessor_max_tokens"] == 7
        and source["response_max_tokens"] == 7
        and source["predecessor_saturated"] is False
        and source["response_saturated"] is False
        for source in derivative.manifest["phase_sources"]
    )
    assert all(path.read_bytes() == raw for path, raw in parent_files.items())


def test_legacy_non_phase_delivery_parent_remains_raw_scoreable(generation):
    from speech_aware_evidence_acquisition.core.bundle.delivery import (
        assert_raw_parent_scoreable,
    )

    parent_path, kwargs = generation()
    parent = verify_bundle(parent_path)
    assert "required_phase_deliveries" not in parent.manifest
    assert_raw_parent_scoreable(parent, kwargs["repo_root"])


def _selected_phase_request(records, phase, sample_id="phase-s1"):
    return next(
        record
        for key, record in records.items()
        if key.endswith("/request")
        and record["payload"]["history"][-1]["contact_id"].endswith(
            f":{phase}:{sample_id}"
        )
    )


def _rehash_request(request):
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import canonical

    request["payload_sha256"] = hashlib.sha256(canonical(request["payload"])).hexdigest()


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("draft", " || revised 1"),
        ("revise", "draft 1 || "),
    ],
)
def test_phase_pair_uses_each_actual_stage_cap_and_quarantines_saturation(
    phase_generation, phase, expected
):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import replay_delivery

    parent, kwargs = phase_generation
    values = dict(compose(kwargs["repo_root"], "m", "d", "b", "e").values)
    values["decoding_params"] = {"temperature": 0, "max_tokens": 999}
    records = json.loads(json.dumps(parent.trace_records))
    request = _selected_phase_request(records, phase)
    request["payload"]["decoding_params"]["max_tokens"] = 2
    _rehash_request(request)
    outputs = [dict(row) for row in parent.outputs_rows]
    if phase == "revise":
        outputs[0]["request_sha256"] = request["payload_sha256"]
    rows, sources = replay_delivery(
        replace(parent, outputs_rows=tuple(outputs), trace_records=records),
        None,
        values["delivery_derivatives"][0],
        values,
    )
    assert rows[0]["text"] == expected
    source = sources[0]
    assert source[f"{'predecessor' if phase == 'draft' else 'response'}_max_tokens"] == 2
    assert source[f"{'predecessor' if phase == 'draft' else 'response'}_saturated"] is True


def test_phase_pair_allows_request_without_cap_and_records_no_saturation(phase_generation):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import replay_delivery

    parent, kwargs = phase_generation
    values = compose(kwargs["repo_root"], "m", "d", "b", "e").values
    records = json.loads(json.dumps(parent.trace_records))
    request = _selected_phase_request(records, "draft")
    del request["payload"]["decoding_params"]["max_tokens"]
    _rehash_request(request)
    rows, sources = replay_delivery(
        replace(parent, trace_records=records),
        None,
        values["delivery_derivatives"][0],
        values,
    )
    assert rows[0]["text"] == "draft 1 || revised 1"
    assert sources[0]["predecessor_max_tokens"] is None
    assert sources[0]["predecessor_saturated"] is False


@pytest.mark.parametrize("cap", [True, 0, -1, 2.5, "64"])
def test_phase_pair_refuses_invalid_actual_stage_cap(phase_generation, cap):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import replay_delivery

    parent, kwargs = phase_generation
    values = compose(kwargs["repo_root"], "m", "d", "b", "e").values
    records = json.loads(json.dumps(parent.trace_records))
    request = _selected_phase_request(records, "draft")
    request["payload"]["decoding_params"]["max_tokens"] = cap
    _rehash_request(request)
    with pytest.raises(BundleError, match="actual max_tokens"):
        replay_delivery(
            replace(parent, trace_records=records),
            None,
            values["delivery_derivatives"][0],
            values,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "foreign-phase",
        "request-hash",
        "control-hash",
        "response-hash",
        "wire-hash",
        "terminal-output",
    ],
)
def test_phase_pair_refuses_incomplete_foreign_or_tampered_sources(
    phase_generation, tmp_path, mutation
):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import replay_delivery

    parent, kwargs = phase_generation
    values = compose(kwargs["repo_root"], "m", "d", "b", "e").values
    declaration = values["delivery_derivatives"][0]
    records = json.loads(json.dumps(parent.trace_records))
    outputs = [dict(row) for row in parent.outputs_rows]
    request_key = next(
        key
        for key, record in records.items()
        if key.endswith("/request")
        and record["payload"]["history"][-1]["contact_id"].endswith(":draft:phase-s1")
    )
    request_id = records[request_key]["payload"]["request_id"]
    if mutation == "missing":
        del records[request_key]
    elif mutation == "duplicate":
        duplicate = json.loads(json.dumps(records[request_key]))
        duplicate["payload"]["request_id"] += "-duplicate"
        duplicate["payload_sha256"] = hashlib.sha256(
            json.dumps(duplicate["payload"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        records[f"{duplicate['payload']['request_id']}/request"] = duplicate
    elif mutation == "foreign-phase":
        records[request_key]["payload"]["history"][-1]["contact_id"] = (
            "foreign-program:draft:phase-s1"
        )
    elif mutation == "request-hash":
        records[request_key]["payload_sha256"] = "0" * 64
    elif mutation == "control-hash":
        records[request_key]["payload"]["history"][-1]["content_sha256"] = "0" * 64
        records[request_key]["payload_sha256"] = hashlib.sha256(
            json.dumps(records[request_key]["payload"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    elif mutation == "response-hash":
        records[f"{request_id}/response"]["response_text_sha256"] = "0" * 64
    elif mutation == "wire-hash":
        records[f"{request_id}/response"]["response_sha256"] = "not-a-sha256"
    else:
        outputs[0]["text"] = "tampered terminal raw output"
    with pytest.raises(BundleError):
        replay_delivery(
            replace(parent, outputs_rows=tuple(outputs), trace_records=records),
            None,
            declaration,
            values,
        )


@pytest.mark.parametrize(
    "selector_update",
    [
        {"schema": "wrong"},
        {"program_id": "phase-direct-only-v1"},
        {"program_sha256": "0" * 64},
        {"predecessor_phase": "missing"},
        {"predecessor_phase": "revise", "response_phase": "draft"},
        {"predecessor_phase": "draft", "response_phase": "draft"},
    ],
)
def test_phase_pair_selector_must_match_registered_parent_program(
    phase_generation, selector_update
):
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import replay_delivery

    parent, kwargs = phase_generation
    values = compose(kwargs["repo_root"], "m", "d", "b", "e").values
    declaration = json.loads(json.dumps(values["delivery_derivatives"][0]))
    declaration["source_selector"].update(selector_update)
    with pytest.raises(BundleError):
        replay_delivery(parent, None, declaration, values)


def test_phase_pair_selector_requires_program_structure_pin(phase_generation):
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import replay_delivery

    parent, kwargs = phase_generation
    values = compose(kwargs["repo_root"], "m", "d", "b", "e").values
    declaration = json.loads(json.dumps(values["delivery_derivatives"][0]))
    del declaration["source_selector"]["program_sha256"]
    with pytest.raises(BundleError):
        replay_delivery(parent, None, declaration, values)


def test_phase_pair_manifest_source_provenance_is_recomputed(
    phase_generation, tmp_path
):
    _, kwargs = phase_generation
    manifest = build_delivery_bundle(
        **kwargs, derivative_cell_id="paired", output_dir=tmp_path / "phase-tamper"
    )
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["phase_sources"][0]["predecessor_text_sha256"] = "0" * 64
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(BundleError, match="recomputation"):
        verify_bundle(manifest)


@pytest.mark.parametrize("policy", ["obs-repair-loop", "obs-repair-loop-ojw"])
def test_live_and_replay_share_identical_window_delivery(generation, tmp_path, policy):
    parent, kwargs = generation(policy=policy)
    parent_before = parent.read_bytes()
    derived = verify_bundle(_build(tmp_path, kwargs))
    original = verify_bundle(parent)
    assert [row["text"] for row in derived.outputs_rows] == [
        row["text"] for row in original.outputs_rows
    ]
    assert len(derived.manifest["windows"]) == 6
    assert derived.trace_records == original.trace_records
    assert derived.manifest["cost"]["calls_used"] == 0
    assert derived.manifest["cost"]["parent_generation_cost"]["calls_used"] == 6
    assert parent.read_bytes() == parent_before
    assert all("response_sha256" not in row for row in derived.outputs_rows)


def test_free_rule_can_replay_shared_response_without_new_contact(generation, tmp_path):
    parent, kwargs = generation(
        transport=fixtures._transport_factory(lambda text: text + " added words")
    )
    original = verify_bundle(parent)
    constrained = verify_bundle(_build(tmp_path, kwargs))
    free = verify_bundle(_build(tmp_path, kwargs, "free"))
    assert [row["text"] for row in constrained.outputs_rows] == [
        row["text"] for row in original.outputs_rows
    ]
    assert all(row["text"].count("added words") == 2 for row in free.outputs_rows)
    assert free.manifest["parent"]["sha256"] == constrained.manifest["parent"]["sha256"]


@pytest.mark.parametrize("failure", ["retry", "skip", "saturated"])
def test_terminal_identity_and_fallback_include_every_window(
    generation, tmp_path, failure
):
    def transport(raw):
        payload = json.loads(raw)
        rid = payload["request_id"]
        first = "-i0000" in rid
        if first and (
            failure == "skip" or (failure == "retry" and not rid.endswith("-r1"))
        ):
            raise TimeoutError("synthetic retry")
        return json.dumps(
            {
                "text": "  "
                + fixtures._predecessor_of(payload).replace("Ponton", "Pontone")
                + " ",
                "usage": {
                    "completion_tokens": 10 if first and failure == "saturated" else 1
                },
            }
        ).encode()

    parent, kwargs = generation(
        transport=transport,
        obs_slice_retry_max=1,
        decoding_params={"temperature": 0, "max_tokens": 10},
    )
    original = verify_bundle(parent)
    derived = verify_bundle(_build(tmp_path, kwargs))
    assert [r["text"] for r in derived.outputs_rows] == [
        r["text"] for r in original.outputs_rows
    ]
    assert len(derived.manifest["windows"]) == 6
    first_windows = [w for w in derived.manifest["windows"] if w["window_index"] == 1]
    for window in first_windows:
        assert window["terminal_request_id"].endswith("-r1") == (failure != "saturated")
        assert window["skipped"] == (failure == "skip")
        if failure in ("skip", "saturated"):
            assert window["normalized_input_sha256"] == hashlib.sha256(b"").hexdigest()
            assert window["delivered_text_sha256"] == window["predecessor_text_sha256"]
        if failure == "skip":
            assert window["response_record_sha256"] is None


@pytest.mark.parametrize(
    "field", ["parent", "rule_sources", "windows", "outputs", "cost", "scorers"]
)
def test_verifier_refuses_provenance_or_output_tampering(generation, tmp_path, field):
    _, kwargs = generation()
    path = _build(tmp_path, kwargs)
    document = json.loads(path.read_text())
    if field in ("parent", "outputs"):
        document[field]["sha256"] = "0" * 64
    elif field == "rule_sources":
        document[field]["core/delivery.py"] = "0" * 64
    elif field == "windows":
        document[field][0]["terminal_request_id"] += "-r99"
    elif field == "cost":
        document[field]["calls_used"] = 6
    else:
        document[field] = ["cost"]
    path.write_text(json.dumps(document))
    with pytest.raises(BundleError):
        verify_bundle(path)


def test_declared_rule_must_precede_generation_and_output_directory_is_new(
    generation, tmp_path
):
    _, kwargs = generation()
    _build(tmp_path, kwargs)
    with pytest.raises(BundleError, match="exist"):
        _build(tmp_path, kwargs)
    experiment = kwargs["experiment_path"]
    document = json.loads(experiment.read_text())
    document["delivery_derivatives"][0]["response_postprocessor_params"] = {}
    experiment.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="config"):
        build_delivery_bundle(
            **kwargs, derivative_cell_id="constrained", output_dir=tmp_path / "late"
        )


def test_registered_scorers_receive_one_complete_derived_manifest(
    generation, tmp_path, monkeypatch, synthetic_world
):
    from speech_aware_evidence_acquisition.core import scorers
    from speech_aware_evidence_acquisition.core.scoring_batch import load_score_jobs

    _, kwargs = generation(scorers=["asr-wer", "cost"])
    path = _build(tmp_path, kwargs)
    bundle = verify_bundle(path)
    gate_calls = []
    monkeypatch.setattr(
        scorers, "_assert_scoring_entry_gate", lambda *args: gate_calls.append(args)
    )
    from speech_aware_evidence_acquisition.data.lock import load_lock

    lock = load_lock(synthetic_world.lock_path)
    result = scorers.score_bundle(
        bundle, lock, kwargs["data_root"], repo_root=kwargs["repo_root"]
    )
    assert len(gate_calls) == 1
    assert len(result["asr-wer"]["per_sample"]) == 3
    assert result["cost"]["aggregate"]["calls_used"] == 0
    assert result["cost"]["aggregate"]["parent_generation_cost"]["calls_used"] == 6
    jobs = tmp_path / "score-jobs.jsonl"
    jobs.write_text(json.dumps({"job_id": "derived", "manifest": str(path)}) + "\n")
    assert load_score_jobs(jobs)[0].manifest == path


def test_derived_artifact_cannot_finalize_or_change_parent_attempt(
    generation, tmp_path
):
    from speech_aware_evidence_acquisition.core.bundle import finalize_bundle

    parent, kwargs = generation()
    path = _build(tmp_path, kwargs)
    parent_doc = json.loads(parent.read_text())
    attempt = Path(parent_doc["attempt"]["state_path"])
    before = attempt.read_bytes()
    with pytest.raises(BundleError, match="derivative.*finalize|finalize.*derivative"):
        finalize_bundle(path, {}, kwargs["data_root"], repo_root=kwargs["repo_root"])
    assert attempt.read_bytes() == before


def test_recomputed_outer_output_hash_cannot_hide_modified_delivery(
    generation, tmp_path
):
    _, kwargs = generation()
    path = _build(tmp_path, kwargs)
    document = json.loads(path.read_text())
    outputs = Path(document["outputs"]["path"])
    rows = [json.loads(line) for line in outputs.read_text().splitlines()]
    rows[0]["text"] = "invented delivery"
    raw = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for row in rows
    )
    outputs.write_bytes(raw)
    document["outputs"]["sha256"] = document["outputs_sha256"] = hashlib.sha256(
        raw
    ).hexdigest()
    path.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="recomputation|replay"):
        verify_bundle(path)


def _attach_synthetic_scores(parent, document):
    from speech_aware_evidence_acquisition.core.bundle.manifest import _attach_scores

    scores = parent.parent / "synthetic.scores.json"
    scores.write_text(json.dumps(document))
    _attach_scores(parent, scores)
    return scores


def test_identical_view_reuses_complete_source_scores_without_rescoring(
    generation, tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core import scorers

    parent, kwargs = generation(scorers=["asr-wer", "cost"])
    expected = {
        "asr-wer": {
            "aggregate": {"samples": 3},
            "per_sample": [
                {"sample_id": sample_id, "wer": 0.123} for sample_id in fixtures.E21_IDS
            ],
        },
        "cost": {"aggregate": {"calls_used": 6}, "per_sample": []},
    }
    _attach_synthetic_scores(parent, expected)
    derived = verify_bundle(_build(tmp_path, kwargs))
    assert (
        derived.manifest["score_reuse"]["source_run_id"]
        == verify_bundle(parent).manifest["run_id"]
    )
    monkeypatch.setattr(scorers, "_assert_scoring_entry_gate", lambda *args: None)

    def forbid(*args):
        pytest.fail("identical source scores must not invoke a scorer again")

    monkeypatch.setattr(scorers.SCORERS, "resolve", forbid)
    result = scorers.score_bundle(
        derived, {}, kwargs["data_root"], repo_root=kwargs["repo_root"]
    )
    assert result["asr-wer"] == expected["asr-wer"]
    assert result["cost"]["aggregate"]["calls_used"] == 0


def test_changed_free_output_does_not_reuse_source_scores(generation, tmp_path):
    parent, kwargs = generation(
        transport=fixtures._transport_factory(lambda text: text + " added words")
    )
    _attach_synthetic_scores(parent, {"asr-wer": {"aggregate": {}, "per_sample": []}})
    free = verify_bundle(_build(tmp_path, kwargs, "free"))
    assert free.manifest["score_reuse"] is None


@pytest.mark.parametrize(
    "scores",
    [
        {"asr-wer": {"aggregate": {}}},
        {"asr-wer": {"aggregate": {}, "per_sample": [{"sample_id": "wrong"}]}},
        {"other-scorer": {"aggregate": {}, "per_sample": []}},
    ],
)
def test_score_reuse_refuses_incomplete_or_unpaired_source_scores(
    generation, tmp_path, monkeypatch, scores
):
    from speech_aware_evidence_acquisition.core import scorers

    parent, kwargs = generation()
    _attach_synthetic_scores(parent, scores)
    bundle = verify_bundle(_build(tmp_path, kwargs))
    monkeypatch.setattr(scorers, "_assert_scoring_entry_gate", lambda *args: None)
    with pytest.raises(scorers.ScoringPhaseError, match="reus"):
        scorers.score_bundle(
            bundle, {}, kwargs["data_root"], repo_root=kwargs["repo_root"]
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-window",
        "duplicate-window",
        "predecessor",
        "bounds",
        "request-hash",
        "response-hash",
        "saturation",
        "fabricated-skip",
        "retry",
        "stitch-order",
        "selective",
    ],
)
def test_replay_cross_checks_terminal_evidence_even_after_outer_trace_verification(
    generation, tmp_path, mutation
):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import (
        replay_delivery,
    )
    from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
        load_predecessor_binding,
    )

    parent_path, kwargs = generation()
    parent = verify_bundle(parent_path)
    values = compose(kwargs["repo_root"], "m", "d", "b", "e").values
    snapshot = load_predecessor_binding(
        kwargs["repo_root"] / "docs" / fixtures.BINDING_RELPATH, kwargs["data_root"]
    )
    records = json.loads(json.dumps(parent.trace_records))
    rid = next(
        rid[:-4]
        for rid in records
        if rid.endswith("/obs") and records[rid].get("obs_repair")
    )
    obs = records[f"{rid}/obs"]
    if mutation == "missing-window":
        del records[f"{rid}/obs"]
    elif mutation == "duplicate-window":
        records[f"{rid}-r1/obs"] = dict(obs)
    elif mutation == "predecessor":
        obs["obs_repair_predecessor_text_sha256"] = "0" * 64
    elif mutation == "bounds":
        obs["obs_window_end_seconds"] += 1
    elif mutation == "request-hash":
        records[f"{rid}/request"]["payload_sha256"] = "0" * 64
    elif mutation == "response-hash":
        records[f"{rid}/response"]["text"] += " corrupt"
    elif mutation == "saturation":
        obs["obs_saturated"] = True
    elif mutation == "fabricated-skip":
        obs["obs_skipped"] = True
    elif mutation == "retry":
        obs["obs_retry_of"] = "wrong"
    elif mutation == "stitch-order":
        root = parent.outputs_rows[0]["request_id"]
        records[f"{root}/request"]["stitched_request_ids"].reverse()
    else:
        obs["obs_relisten"] = True
    with pytest.raises(BundleError):
        replay_delivery(
            replace(parent, trace_records=records),
            snapshot,
            values["delivery_derivatives"][0],
            values,
        )


def test_parent_score_tamper_and_output_path_escape_are_refused(generation, tmp_path):
    parent, kwargs = generation()
    scores = _attach_synthetic_scores(
        parent, {"asr-wer": {"aggregate": {}, "per_sample": []}}
    )
    path = _build(tmp_path, kwargs)
    document = json.loads(path.read_text())
    original = scores.read_bytes()
    scores.write_bytes(b"{}")
    with pytest.raises(BundleError, match="hash"):
        verify_bundle(path)
    scores.write_bytes(original)
    outside = tmp_path / "outside.outputs.jsonl"
    outside.write_bytes(Path(document["outputs"]["path"]).read_bytes())
    document["outputs"]["path"] = str(outside)
    path.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="directory"):
        verify_bundle(path)


def test_derivative_cannot_be_used_as_generation_parent(generation, tmp_path):
    _, kwargs = generation()
    derivative = _build(tmp_path, kwargs)
    kwargs["parent_manifest"] = derivative
    with pytest.raises(BundleError, match="ordinary generation"):
        build_delivery_bundle(
            **kwargs, derivative_cell_id="free", output_dir=tmp_path / "recursive"
        )


def test_unregistered_cell_and_repository_output_refuse_before_writes(
    generation, tmp_path
):
    _, kwargs = generation()
    with pytest.raises(BundleError, match="uniquely declared"):
        build_delivery_bundle(
            **kwargs, derivative_cell_id="unknown", output_dir=tmp_path / "unknown"
        )
    assert not (tmp_path / "unknown").exists()
    with pytest.raises(BundleError, match="outside repository"):
        build_delivery_bundle(
            **kwargs,
            derivative_cell_id="free",
            output_dir=kwargs["repo_root"] / "derived",
        )


def test_current_controller_generation_replays_without_replacing_its_trace(
    generation, tmp_path
):
    parent, kwargs = generation(
        policy="obs-repair-loop-ojw", obs_controller_program="phase-direct-only-v1"
    )
    original = verify_bundle(parent)
    assert (
        sum(rid.endswith("/window-controller") for rid in original.trace_records) == 6
    )
    derived = verify_bundle(_build(tmp_path, kwargs))
    assert derived.trace_records == original.trace_records
    assert [row["text"] for row in derived.outputs_rows] == [
        row["text"] for row in original.outputs_rows
    ]
