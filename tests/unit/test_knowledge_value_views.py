from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.model import LlamaServerTransport
from speech_aware_evidence_acquisition.core.session import (
    ModelFileRef,
    SESSION_RECEIPT_SCHEMA_V2,
    SessionReceipt,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (
    SpeechFeatureChunkData,
    load_speech_feature_packets,
    materialize_speech_feature_packet,
)
from speech_aware_evidence_acquisition.rails.core_client import (
    _parse_speech_feature_messages,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.knowledge_value_views import (
    KnowledgeValueRenderer,
    KnowledgeViewError,
    assemble_knowledge_values,
    load_prepared_knowledge_view_catalog,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(*, partition: str = "train") -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="train-knowledge",
        source_split_identity_hash="1" * 64,
        source_sample_ids=("train-1", "train-2"),
        builder_policy_id="train-knowledge-builder-v1",
        facets=(
            KeyFacet("facet-1", "content", "text", "first knowledge key", ("train-1",)),
            KeyFacet(
                "facet-2", "content", "text", "second knowledge key", ("train-2",)
            ),
        ),
        values=(
            ValueBundle(
                "value-1",
                "first historical value text",
                ("facet-1",),
                ("train-1",),
                ("train://train-1",),
            ),
            ValueBundle(
                "value-2",
                "second historical value text",
                ("facet-2",),
                ("train-2",),
                ("train://train-2",),
            ),
        ),
        source_partition_role=partition,
    ).validate()


def _packet(feature_root: Path, index: int):
    return materialize_speech_feature_packet(
        feature_root=feature_root,
        packet_id=f"slurp/train-knowledge/{index}",
        audio_sha256=hashlib.sha256(f"synthetic speech {index}".encode()).hexdigest(),
        encoder_receipt_sha256="e" * 64,
        decoder_gguf_sha256="d" * 64,
        mmproj_sha256="a" * 64,
        position_mode="mrope_1d",
        causal_attention=True,
        chunks=(
            SpeechFeatureChunkData(
                n_tokens=2,
                n_pos=2,
                n_embd=4,
                feature_bytes=struct.pack("<8f", *(index + n for n in range(8))),
                position_bytes=struct.pack("<8i", 0, 1, 0, 1, 0, 1, 0, 1),
            ),
        ),
    )


def _world(tmp_path: Path, *, episode_count: int = 2):
    snapshot = _snapshot()
    feature_root = tmp_path / "features"
    packets = [_packet(feature_root, index) for index in (1, 2)]
    document = {
        "schema": "saea-train-knowledge-view-catalog-v1",
        "snapshot_sha256": snapshot.content_hash(),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "source_partition_role": "train",
        "decoder_gguf_sha256": "d" * 64,
        "mmproj_sha256": "a" * 64,
        "episodes": [
            {
                "episode_id": f"episode-{index}",
                "value_id": f"value-{index}",
                "source_sample_id": f"train-{index}",
                "audio_sha256": packets[index - 1].audio_sha256,
                "packet_id": packets[index - 1].packet_id,
                "packet_sha256": packets[index - 1].packet_sha256,
                "encoder_receipt_sha256": packets[index - 1].encoder_receipt_sha256,
            }
            for index in range(1, episode_count + 1)
        ],
    }
    manifest = tmp_path / "catalog.json"
    manifest.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
    return snapshot, feature_root, packets, manifest, document


def _load(snapshot, feature_root, manifest):
    return load_prepared_knowledge_view_catalog(
        manifest,
        expected_sha256=_sha256(manifest),
        feature_root=feature_root,
        snapshot=snapshot,
        expected_decoder_gguf_sha256="d" * 64,
        expected_mmproj_sha256="a" * 64,
    )


def test_text_view_matches_historical_rendering_and_preserves_snapshot(tmp_path):
    snapshot, root, _packets, manifest, _document = _world(tmp_path)
    before = snapshot.as_json()
    assert len(assemble_knowledge_values(snapshot, ("value-1",))) == 1
    digest = snapshot.content_hash()
    catalog = _load(snapshot, root, manifest)
    assert assemble_knowledge_values(
        snapshot, ("value-2", "value-1")
    ) == catalog.assemble(("value-2", "value-1"), view="text", snapshot=snapshot)

    assert catalog.assemble(("value-2", "value-1"), view="text", snapshot=snapshot) == (
        {
            "type": "text",
            "text": "second historical value text",
            "evidence_id": "value-2",
            "source_uri": f"knowledge-snapshot://{digest}/value-2",
            "knowledge_role": "value",
        },
        {
            "type": "text",
            "text": "first historical value text",
            "evidence_id": "value-1",
            "source_uri": f"knowledge-snapshot://{digest}/value-1",
            "knowledge_role": "value",
        },
    )
    assert catalog.assemble((), view="paired", snapshot=snapshot) == ()
    assert snapshot.as_json() == before
    assert snapshot.content_hash() == digest


def test_prepared_renderer_hashes_and_indexes_snapshot_only_once(tmp_path, monkeypatch):
    snapshot, root, _packets, manifest, _document = _world(tmp_path)
    catalog = _load(snapshot, root, manifest)
    original = KnowledgeSnapshot.content_hash
    calls = 0

    def counted(instance):
        nonlocal calls
        calls += 1
        return original(instance)

    monkeypatch.setattr(KnowledgeSnapshot, "content_hash", counted)
    renderer = KnowledgeValueRenderer(snapshot, catalog)
    assert calls == 1
    assert len(renderer.assemble(("value-1",), view="paired")) == 2
    assert len(renderer.assemble(("value-2",), view="text")) == 1
    assert calls == 1


def test_speech_and_paired_views_keep_order_and_fit_core_client_grammar(tmp_path):
    snapshot, root, packets, manifest, _document = _world(tmp_path)
    catalog = _load(snapshot, root, manifest)

    speech = catalog.assemble(("value-2", "value-1"), view="speech", snapshot=snapshot)
    assert [part["speech_features"]["packet_id"] for part in speech] == [
        packets[1].packet_id,
        packets[0].packet_id,
    ]
    assert all(part["speech_features"]["role"] == "key" for part in speech)

    paired = catalog.assemble(("value-2", "value-1"), view="paired", snapshot=snapshot)
    assert [part["type"] for part in paired] == [
        "text",
        "input_speech_features",
        "text",
        "input_speech_features",
    ]
    assert paired[0]["evidence_id"] == "value-2"
    assert paired[2]["evidence_id"] == "value-1"

    query = {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": packets[0].packet_id,
            "sha256": packets[0].packet_sha256,
            "role": "query",
        },
    }
    _instruction, text_parts, descriptors = _parse_speech_feature_messages(
        (
            {"role": "system", "content": "Solve the spoken command."},
            {"role": "user", "content": [query, *paired]},
        )
    )
    assert [part["evidence_id"] for part in text_parts] == ["value-2", "value-1"]
    assert [part["role"] for part in descriptors] == ["query", "key", "key"]
    assert [
        (text["evidence_id"], descriptor["packet_id"])
        for text, descriptor in zip(text_parts, descriptors[1:], strict=True)
    ] == [
        ("value-2", packets[1].packet_id),
        ("value-1", packets[0].packet_id),
    ]


def test_paired_views_retain_value_packet_alignment_through_client_and_renderer(
    tmp_path, monkeypatch
):
    from test_rails_frozen_core_client import (
        _World as ClientWorld,
        _client,
        _speech_feature_world,
    )

    world = ClientWorld(tmp_path)
    feature_root, query_packet, query_bindings = _speech_feature_world(world, tmp_path)
    snapshot = _snapshot()
    knowledge_packets = [_packet(feature_root, index) for index in (1, 2)]
    document = {
        "schema": "saea-train-knowledge-view-catalog-v1",
        "snapshot_sha256": snapshot.content_hash(),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "source_partition_role": "train",
        "decoder_gguf_sha256": "d" * 64,
        "mmproj_sha256": "a" * 64,
        "episodes": [
            {
                "episode_id": f"episode-{index}",
                "value_id": f"value-{index}",
                "source_sample_id": f"train-{index}",
                "audio_sha256": packet.audio_sha256,
                "packet_id": packet.packet_id,
                "packet_sha256": packet.packet_sha256,
                "encoder_receipt_sha256": packet.encoder_receipt_sha256,
            }
            for index, packet in enumerate(knowledge_packets, start=1)
        ],
    }
    manifest = tmp_path / "full-client-catalog.json"
    manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
    catalog = _load(snapshot, feature_root, manifest)
    from dataclasses import replace
    from test_rails_controllers import _context, _query_state, _phase_supply
    from test_phase_planner import _material
    from speech_aware_evidence_acquisition.rails.controllers import (
        EvidenceAgentController,
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.phase_tools import (
        build_phase_tools,
        PHASE_KNOWLEDGE_TOOL,
    )

    query_state = replace(
        _query_state(sample_id="s1"),
        speech_packet_id=query_packet.packet_id,
        speech_packet_sha256=query_packet.packet_sha256,
    )
    context = replace(
        _context(query_state),
        knowledge_snapshot_sha256=snapshot.content_hash(),
        catalog_facet_ids=("facet-1", "facet-2"),
        catalog_value_ids=("value-1", "value-2"),
    )
    program = default_phase_program("phase-task-tools-then-solve-v1")
    dispatcher = build_phase_tools(
        {
            "phase_tools": {
                "plan": {
                    "mode": "fixed",
                    "allowed_tools": [PHASE_KNOWLEDGE_TOOL],
                    "knowledge_views": ["paired"],
                    "fixed_action": {
                        "tool_id": PHASE_KNOWLEDGE_TOOL,
                        "arguments": {"view": "paired"},
                    },
                }
            }
        },
        program,
        snapshot=snapshot,
        knowledge_catalog=catalog,
        supply_for_phase=lambda _phase, ctx: _phase_supply(
            ctx,
            value_ids=("value-2", "value-1"),
            facet_ids=("facet-2", "facet-1"),
        ),
    )
    controller = EvidenceAgentController(
        program=program,
        material_for_phase=_material,
        tools_for_phase=dispatcher,
    )
    first_contact = controller.initial_contact(context)
    advance = controller.advance(context, first_contact, "Prepare task evidence.")
    result_state = json.loads(advance.new_agent_states[-1].content)
    assert result_state["result"]["speech_evidence_order"] == [
        {
            "value_id": f"value-{index}",
            "packet_id": knowledge_packets[index - 1].packet_id,
            "packet_sha256": knowledge_packets[index - 1].packet_sha256,
        }
        for index in (2, 1)
    ]
    assert dispatcher.receipt()["completed"] == 1
    paired = dispatcher.render_values(
        snapshot,
        advance.next_query_state,
        advance.new_agent_states,
    )

    session = SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA_V2,
        study=STUDY_SLUG,
        session_id="knowledge-render-test",
        binary_path="llama.cpp/build/bin/llama-server",
        binary_sha256="b" * 64,
        argv=(
            "llama.cpp/build/bin/llama-server",
            "--host",
            "127.0.0.1",
            "--port",
            "49199",
            "--no-mmproj",
        ),
        pid=1,
        host="127.0.0.1",
        port=49199,
        model_files=(ModelFileRef(path="models/decoder.gguf", sha256="d" * 64),),
        started_at="2026-09-11T00:00:00+00:00",
        startup_stdout_sha256="0" * 64,
        role="inference",
    )
    monkeypatch.setattr(
        LlamaServerTransport, "_assert_session_still_valid", lambda self: None
    )
    llama = LlamaServerTransport(
        "http://127.0.0.1:49199",
        world.data_root,
        session,
        {"unused_because_liveness_is_synthetic": True},
        tmp_path,
        prompt_order="knowledge-speech-state-v2",
        feature_root=feature_root,
        post=lambda _url, _body: pytest.fail("render-only test must not POST"),
    )
    rendered_bodies = []

    def render_only(request_bytes):
        rendered_bodies.append(llama.render_request(request_bytes))
        return json.dumps(
            {"text": "ok", "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
        ).encode()

    client, _gate, _transport = _client(
        world,
        tmp_path,
        transport=render_only,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=query_bindings,
    )
    query = {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": query_packet.packet_id,
            "sha256": query_packet.packet_sha256,
            "role": "query",
        },
    }
    result = client.complete(
        (
            {"role": "system", "content": "Use the selected knowledge."},
            {"role": "user", "content": [query, *paired]},
        ),
        speech_feature_sample_id="s1",
        key_representation_id="train-knowledge-view-v1",
        matcher_policy_id="knowledge-selection-v1",
    )

    assert result == "ok"
    assert len(rendered_bodies) == 1
    boundary_payload = json.loads(
        next(world.run_dir.glob("*.trace.jsonl")).read_text().splitlines()[0]
    )
    assert boundary_payload["payload"]["payload_sha256"]
    recorded = boundary_payload["payload"]["payload"]
    assert recorded["speech_feature_parts"] == [
        {
            "packet_id": query_packet.packet_id,
            "sha256": query_packet.packet_sha256,
            "role": "query",
        },
        {
            "packet_id": knowledge_packets[1].packet_id,
            "sha256": knowledge_packets[1].packet_sha256,
            "role": "key",
        },
        {
            "packet_id": knowledge_packets[0].packet_id,
            "sha256": knowledge_packets[0].packet_sha256,
            "role": "key",
        },
    ]
    assert [item["evidence_id"] for item in recorded["supplied_evidence"]] == [
        "value-2",
        "value-1",
    ]
    content = rendered_bodies[0]["messages"][1]["content"]
    packet_parts = [
        part["speech_features"]
        for part in content
        if part["type"] == "input_speech_features"
    ]
    text_parts = [part["text"] for part in content if part["type"] == "text"]
    assert [part["packet_id"] for part in packet_parts] == [
        knowledge_packets[1].packet_id,
        knowledge_packets[0].packet_id,
        query_packet.packet_id,
    ]
    assert [part["role"] for part in packet_parts] == ["key", "key", "query"]
    assert text_parts == [
        "[evidence value-2] second historical value text",
        "[evidence value-1] first historical value text",
    ]
    assert list(
        zip(
            ("value-2", "value-1"),
            [part["packet_id"] for part in packet_parts[:2]],
            strict=True,
        )
    ) == [
        ("value-2", knowledge_packets[1].packet_id),
        ("value-1", knowledge_packets[0].packet_id),
    ]


def test_loader_refuses_non_train_snapshot(tmp_path):
    _snapshot0, root, _packets, manifest, document = _world(tmp_path)
    snapshot = _snapshot(partition="external-governed")
    document["snapshot_sha256"] = snapshot.content_hash()
    document["source_partition_role"] = "external-governed"
    manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
    with pytest.raises(KnowledgeViewError, match="TRAIN"):
        _load(snapshot, root, manifest)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("snapshot_sha256", "0" * 64, "snapshot"),
        ("source_split_identity_hash", "0" * 64, "split identity"),
        ("decoder_gguf_sha256", "0" * 64, "decoder"),
        ("mmproj_sha256", "0" * 64, "mmproj"),
    ],
)
def test_loader_refuses_top_identity_mismatch(tmp_path, field, value, match):
    snapshot, root, _packets, manifest, document = _world(tmp_path)
    document[field] = value
    manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
    with pytest.raises(KnowledgeViewError, match=match):
        _load(snapshot, root, manifest)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("value_id", "foreign", "value"),
        ("source_sample_id", "train-2", "source sample"),
        ("audio_sha256", "0" * 64, "audio"),
        ("packet_sha256", "0" * 64, "packet"),
        ("encoder_receipt_sha256", "0" * 64, "encoder"),
    ],
)
def test_loader_refuses_episode_or_packet_mismatch(tmp_path, field, value, match):
    snapshot, root, _packets, manifest, document = _world(tmp_path)
    document["episodes"][0][field] = value
    manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
    with pytest.raises(KnowledgeViewError, match=match):
        _load(snapshot, root, manifest)


def test_partial_catalog_keeps_text_compatible_but_refuses_speech_and_paired(tmp_path):
    snapshot, root, _packets, manifest, _document = _world(tmp_path, episode_count=1)
    catalog = _load(snapshot, root, manifest)
    assert (
        len(catalog.assemble(("value-1", "value-2"), view="text", snapshot=snapshot))
        == 2
    )
    for view in ("speech", "paired"):
        with pytest.raises(KnowledgeViewError, match="not prepared"):
            catalog.assemble(("value-1", "value-2"), view=view, snapshot=snapshot)


def test_selection_refuses_duplicate_unknown_and_invalid_view(tmp_path):
    snapshot, root, _packets, manifest, _document = _world(tmp_path)
    catalog = _load(snapshot, root, manifest)
    with pytest.raises(KnowledgeViewError, match="unique"):
        catalog.assemble(("value-1", "value-1"), view="text", snapshot=snapshot)
    with pytest.raises(KnowledgeViewError, match="outside"):
        catalog.assemble(("foreign",), view="text", snapshot=snapshot)
    with pytest.raises(KnowledgeViewError, match="view"):
        catalog.assemble(("value-1",), view="video", snapshot=snapshot)


def test_manifest_pin_and_exact_schema_are_enforced(tmp_path):
    snapshot, root, _packets, manifest, document = _world(tmp_path)
    with pytest.raises(KnowledgeViewError, match="manifest SHA"):
        load_prepared_knowledge_view_catalog(
            manifest,
            expected_sha256="0" * 64,
            feature_root=root,
            snapshot=snapshot,
            expected_decoder_gguf_sha256="d" * 64,
            expected_mmproj_sha256="a" * 64,
        )
    document["unbound"] = True
    manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
    with pytest.raises(KnowledgeViewError, match="exact keys"):
        _load(snapshot, root, manifest)


def test_request_time_packet_guard_still_refuses_changed_feature_bytes(tmp_path):
    snapshot, root, packets, manifest, _document = _world(tmp_path)
    catalog = _load(snapshot, root, manifest)
    block = catalog.assemble(("value-1",), view="speech", snapshot=snapshot)[0]
    feature_path = root / packets[0].packet_id / packets[0].chunks[0].feature_relpath
    feature_path.write_bytes(b"changed after catalog load")
    with pytest.raises(FrozenCoreError, match="feature bytes"):
        load_speech_feature_packets(
            root,
            (
                {
                    "packet_id": block["speech_features"]["packet_id"],
                    "sha256": block["speech_features"]["sha256"],
                },
            ),
            workers=1,
            expected_decoder_gguf_sha256="d" * 64,
        )


def test_catalog_bindings_are_immutable(tmp_path):
    snapshot, root, _packets, manifest, _document = _world(tmp_path)
    catalog = _load(snapshot, root, manifest)
    with pytest.raises(FrozenInstanceError):
        catalog.snapshot_sha256 = "0" * 64
    with pytest.raises(FrozenInstanceError):
        catalog.episodes[0].value_id = "changed"
