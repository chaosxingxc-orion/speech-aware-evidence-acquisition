"""E6: the ``phase_supply`` config seam --- spec loading and refusal, sealed
vector loading, the ``supply_for_phase`` binding it builds, and the
end-to-end proof that a supplied phase's knowledge travels the TRACED typed
content channel while its control-turn bytes stay identical.

No model, GPU, network or embedding contact anywhere in this file: every
vector is written by the test, every snapshot is synthetic, and the one
end-to-end run drives ``rails.phase_runner.run_continuous_program`` against
a fake core client.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import phase_supply as ps
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def _snapshot() -> KnowledgeSnapshot:
    """Two content facets with vectors, two label facets with prior mass, one
    value each -- the same shape ``rails.knowledge_build`` produces for
    SLURP, small enough to reason about by hand."""

    return KnowledgeSnapshot(
        snapshot_id="phase-supply-test-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:u1", "train:u2"),
        builder_policy_id="test-builder-v1",
        facets=(
            KeyFacet("facet:content:u1", "content", "text", "red apple", ("train:u1",)),
            KeyFacet("facet:content:u2", "content", "text", "green leaf", ("train:u2",)),
            KeyFacet("facet:label:red", "label", "text", "red", ("train:u1",)),
            KeyFacet("facet:label:green", "label", "text", "green", ("train:u2",)),
        ),
        values=(
            ValueBundle(
                value_id="value:u1",
                content="a long enough evidence payload for u1",
                associated_facet_ids=("facet:content:u1", "facet:label:red"),
                source_sample_ids=("train:u1",),
                provenance_refs=("sample:train:u1",),
                task_target="red",
                prior_score=0.7,
            ),
            ValueBundle(
                value_id="value:u2",
                content="a long enough evidence payload for u2",
                associated_facet_ids=("facet:content:u2", "facet:label:green"),
                source_sample_ids=("train:u2",),
                provenance_refs=("sample:train:u2",),
                task_target="green",
                prior_score=0.3,
            ),
        ),
    ).validate()


def _write_vectors(path, rows) -> str:
    import hashlib

    text = "".join(
        json.dumps({"id": entry_id, "vectors": vectors}, sort_keys=True) + "\n"
        for entry_id, vectors in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_segment_vectors(path, rows) -> str:
    import hashlib

    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source(relpath: str, sha256: str) -> dict[str, object]:
    return {
        "kind": ps.SEALED_VECTORS_KIND,
        "relpath": relpath,
        "sha256": sha256,
        "tool_contact_ledger_row": "TEST-EMB-0001",
        "embedded_signal": "speech: the test's own synthetic vectors",
    }


def _segment_source(relpath: str, sha256: str) -> dict[str, object]:
    source = _source(relpath, sha256)
    source["kind"] = ps.SEALED_SEGMENT_VECTORS_KIND
    return source


def _fragment(query_source, facet_source=None, **overrides) -> dict[str, object]:
    entry: dict[str, object] = {
        "provider": "kb-facet-v1",
        "rank_policy": "saea-rank-wcos-prior-agree-v1",
        "fuse_policy": "saea-fuse-supplyfilter-v1",
        "k": 5,
        "tau": 0.65,
        "dimensions": ["content"],
        "query_source": query_source,
    }
    if facet_source is not None:
        entry["facet_source"] = facet_source
    entry.update(overrides)
    return {"phase_supply": {"evidence": entry}}


def _program():
    return rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")


# ---------------------------------------------------------------------------
# spec loading and refusal
# ---------------------------------------------------------------------------


def test_absent_phase_supply_yields_no_specs():
    assert ps.load_phase_supply_specs({}, _program()) == {}
    assert ps.load_phase_supply_specs({"phase_supply": {}}, _program()) == {}


def test_load_phase_supply_specs_reads_the_declared_phase():
    specs = ps.load_phase_supply_specs(
        _fragment(_source("v/q.jsonl", _SHA_A)), _program()
    )
    assert set(specs) == {"evidence"}
    spec = specs["evidence"]
    assert spec.provider == "kb-facet-v1"
    assert spec.rank_policy == "saea-rank-wcos-prior-agree-v1"
    assert spec.fuse_policy == "saea-fuse-supplyfilter-v1"
    assert (spec.k, spec.tau, spec.dimensions) == (5, 0.65, ("content",))
    assert spec.fuse_knobs().tau == 0.65


# ---------------------------------------------------------------------------
# Owner rule, 2026-09-06: the retrieval QUERY must contain the speech signal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("modality", ["speech", "speech+state"])
def test_a_query_source_declaring_a_speech_modality_is_accepted(modality):
    source = _source("v/q.jsonl", _SHA_A)
    source["embedded_signal"] = f"{modality}: the row's own 90 s speech packet"
    specs = ps.load_phase_supply_specs(_fragment(source), _program())
    assert specs["evidence"].query_source["embedded_signal"].startswith(modality)
    assert (
        ps.query_signal_modality(
            specs["evidence"].query_source, field="phase_supply['evidence'].query_source"
        )
        == modality
    )


def test_a_text_only_query_source_is_refused_before_any_file_is_opened():
    """The honest description this seam accepted BEFORE the rule -- a
    response text embedding -- is exactly what is now refused."""

    source = _source("v/q.jsonl", _SHA_A)
    source["embedded_signal"] = (
        "the sealed one-contact CLOSED-LIST DEV-1000 response text of each row"
    )
    with pytest.raises(ps.PhaseSupplyError, match="must DECLARE the query signal"):
        ps.load_phase_supply_specs(_fragment(source), _program())


def test_a_modality_named_inside_the_prose_does_not_count_as_a_declaration():
    """The modality is the FIRST token, not a word somewhere in the prose:
    a declaration a reader could miss is not a declaration."""

    source = _source("v/q.jsonl", _SHA_A)
    source["embedded_signal"] = (
        "the draft answer text, which describes what the speech said"
    )
    with pytest.raises(ps.PhaseSupplyError, match="must DECLARE the query signal"):
        ps.load_phase_supply_specs(_fragment(source), _program())


def test_a_bare_modality_with_no_description_is_refused():
    source = _source("v/q.jsonl", _SHA_A)
    source["embedded_signal"] = "speech:   "
    with pytest.raises(ps.PhaseSupplyError, match="carries no description"):
        ps.load_phase_supply_specs(_fragment(source), _program())


def test_the_key_side_is_unconstrained_by_the_query_rule():
    """A facet (KEY) vector is knowledge text by construction; the rule is
    about what the QUERY carries."""

    facet = _source("v/f.jsonl", _SHA_B)
    facet["embedded_signal"] = "KeyFacet.representation of every content facet"
    specs = ps.load_phase_supply_specs(
        _fragment(_source("v/q.jsonl", _SHA_A), facet_source=facet), _program()
    )
    assert specs["evidence"].facet_source["embedded_signal"].startswith("KeyFacet")


def test_assert_phase_supply_queries_carry_speech_reads_a_raw_fragment():
    """The form ``core.flight.FlightRuntime`` calls in its own preflight,
    before the phase program is resolved."""

    ok = _fragment(_source("v/q.jsonl", _SHA_A))
    ps.assert_phase_supply_queries_carry_speech(ok)
    ps.assert_phase_supply_queries_carry_speech({})
    ps.assert_phase_supply_queries_carry_speech({"phase_supply": {}})

    bad = _fragment(_source("v/q.jsonl", _SHA_A))
    bad["phase_supply"]["evidence"]["query_source"]["embedded_signal"] = "plain text"
    with pytest.raises(ps.PhaseSupplyError, match="must DECLARE the query signal"):
        ps.assert_phase_supply_queries_carry_speech(bad)


def test_the_phase_supply_receipt_records_the_declared_modality():
    specs = ps.load_phase_supply_specs(
        _fragment(_source("v/q.jsonl", _SHA_A)), _program()
    )
    receipt = ps.phase_supply_receipt(specs, {"evidence": 3}, {"evidence": 2})
    assert receipt["schema"] == "saea-phase-supply-v2"
    assert receipt["query_signal_vocabulary"] == list(ps.QUERY_SIGNAL_MODALITIES)
    assert receipt["phases"][0]["query_signal_modality"] == "speech"


def test_phase_supply_for_a_phase_the_program_does_not_declare_is_refused():
    values = {"phase_supply": {"nope": {"provider": "kb-facet-v1"}}}
    with pytest.raises(ps.PhaseSupplyError, match="does not declare"):
        ps.load_phase_supply_specs(values, _program())


def test_phase_supply_on_a_phase_declaring_knowledge_none_is_refused():
    program = rc.default_phase_program("phase-draft-revise-v1")
    values = {"phase_supply": {"revise": {"provider": "kb-facet-v1"}}}
    with pytest.raises(ps.PhaseSupplyError, match="knowledge='none'"):
        ps.load_phase_supply_specs(values, program)


def test_unknown_phase_supply_key_is_refused():
    fragment = _fragment(_source("v/q.jsonl", _SHA_A))
    fragment["phase_supply"]["evidence"]["logit_bias"] = True
    with pytest.raises(ps.PhaseSupplyError, match="unknown key"):
        ps.load_phase_supply_specs(fragment, _program())


@pytest.mark.parametrize(
    "key, value, message",
    [
        ("provider", "no-such-provider", "KNOWLEDGE_PROVIDERS"),
        ("rank_policy", "no-such-ranker", "KNOWLEDGE_RANKERS"),
        ("fuse_policy", "no-such-fuser", "KNOWLEDGE_FUSERS"),
    ],
)
def test_unregistered_component_ids_are_refused(key, value, message):
    fragment = _fragment(_source("v/q.jsonl", _SHA_A))
    fragment["phase_supply"]["evidence"][key] = value
    with pytest.raises(ps.PhaseSupplyError, match=message):
        ps.load_phase_supply_specs(fragment, _program())


def test_an_embedding_server_query_source_is_declared_but_never_resolvable():
    fragment = _fragment({"kind": ps.EMBEDDING_SERVER_KIND})
    specs = ps.load_phase_supply_specs(fragment, _program())
    with pytest.raises(ps.PhaseSupplyError, match="not implemented"):
        ps.build_supply_for_phase(
            specs,
            snapshot=_snapshot(),
            snapshot_sha256=_snapshot().content_hash(),
            data_root=None,
        )


def test_an_absolute_query_source_relpath_is_refused():
    fragment = _fragment(_source("/etc/passwd", _SHA_A))
    with pytest.raises(ps.PhaseSupplyError, match="plain relative path"):
        ps.load_phase_supply_specs(fragment, _program())


# ---------------------------------------------------------------------------
# sealed vectors
# ---------------------------------------------------------------------------


def test_load_sealed_vectors_verifies_the_pinned_sha256(tmp_path):
    path = tmp_path / "q.jsonl"
    digest = _write_vectors(path, [("s1", {"content": [1.0, 0.0]})])
    table = ps.load_sealed_vectors(
        path, expected_sha256=digest, dimensions=("content",)
    )
    assert table == {"s1": {"content": (1.0, 0.0)}}
    with pytest.raises(ps.PhaseSupplyError, match="hashes to"):
        ps.load_sealed_vectors(path, expected_sha256=_SHA_A, dimensions=("content",))


def test_load_sealed_vectors_refuses_an_undeclared_dimension(tmp_path):
    path = tmp_path / "q.jsonl"
    digest = _write_vectors(path, [("s1", {"speaker": [1.0]})])
    with pytest.raises(ps.PhaseSupplyError, match="does not declare"):
        ps.load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))


def test_load_sealed_vectors_refuses_mixed_widths(tmp_path):
    path = tmp_path / "q.jsonl"
    digest = _write_vectors(
        path, [("s1", {"content": [1.0, 0.0]}), ("s2", {"content": [1.0]})]
    )
    with pytest.raises(ps.PhaseSupplyError, match="mixes widths"):
        ps.load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))


def test_load_sealed_vectors_refuses_a_duplicate_id(tmp_path):
    path = tmp_path / "q.jsonl"
    digest = _write_vectors(
        path, [("s1", {"content": [1.0]}), ("s1", {"content": [0.0]})]
    )
    with pytest.raises(ps.PhaseSupplyError, match="duplicate id"):
        ps.load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))


def test_load_sealed_segment_vectors_requires_exact_frame_coverage_and_hash(tmp_path):
    path = tmp_path / "q-segments.jsonl"
    digest = _write_segment_vectors(
        path,
        [{"id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 4,
          "source_sample_rate_hz": 16000,
          "segments": [
              {"id": "early", "start_frame": 0, "end_frame": 1,
               "vectors": {"content": [0.0, 1.0]}},
              {"id": "late", "start_frame": 2, "end_frame": 4,
               "vectors": {"content": [1.0, 0.0]}},
          ]}],
    )
    with pytest.raises(ps.PhaseSupplyError, match="coverage"):
        ps.load_sealed_segment_vectors(path, expected_sha256=digest, dimensions=("content",))
    with pytest.raises(ps.PhaseSupplyError, match="hashes to"):
        ps.load_sealed_segment_vectors(path, expected_sha256=_SHA_B, dimensions=("content",))


def test_load_sealed_segment_vectors_accepts_registered_120_second_overlap(tmp_path):
    """120-second windows, 8-second overlap, 112-second stride, tail complete."""

    path = tmp_path / "q-segments.jsonl"
    digest = _write_segment_vectors(
        path,
        [{
            "id": "dev:s1",
            "audio_sha256": _SHA_A,
            "source_frames": 3840000,
            "source_sample_rate_hz": 16000,
            "segments": [
                {"id": "000000000-0001920000", "start_frame": 0,
                 "end_frame": 1920000, "vectors": {"content": [1.0, 0.0]}},
                {"id": "0001792000-0003712000", "start_frame": 1792000,
                 "end_frame": 3712000, "vectors": {"content": [0.0, 1.0]}},
                {"id": "0003584000-0003840000", "start_frame": 3584000,
                 "end_frame": 3840000, "vectors": {"content": [1.0, 1.0]}},
            ],
        }],
    )
    table = ps.load_sealed_segment_vectors(
        path, expected_sha256=digest, dimensions=("content",)
    )
    assert len(table["dev:s1"].segments) == 3


@pytest.mark.parametrize(
    "second_range",
    [
        (0, 4),  # duplicate start
        (1, 3),  # contained
        (3, 2),  # reversed
    ],
)
def test_load_sealed_segment_vectors_refuses_nonextending_ranges(tmp_path, second_range):
    path = tmp_path / "q-segments.jsonl"
    start, end = second_range
    digest = _write_segment_vectors(
        path,
        [{
            "id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 4,
            "source_sample_rate_hz": 16000,
            "segments": [
                {"id": "first", "start_frame": 0, "end_frame": 4,
                 "vectors": {"content": [1.0, 0.0]}},
                {"id": "second", "start_frame": start, "end_frame": end,
                 "vectors": {"content": [0.0, 1.0]}},
            ],
        }],
    )
    with pytest.raises(ps.PhaseSupplyError, match="coverage"):
        ps.load_sealed_segment_vectors(
            path, expected_sha256=digest, dimensions=("content",)
        )


@pytest.mark.parametrize(
    "segments, message",
    [
        ([{"id": "same", "start_frame": 0, "end_frame": 1, "vectors": {"content": [1.0, 0.0]}},
          {"id": "same", "start_frame": 1, "end_frame": 2, "vectors": {"content": [1.0, 0.0]}}], "duplicate segment id"),
        ([{"id": "one", "start_frame": 0, "end_frame": 1, "vectors": {"content": [0.0, 0.0]}},
          {"id": "two", "start_frame": 1, "end_frame": 2, "vectors": {"content": [1.0, 0.0]}}], "nonzero"),
        ([{"id": "one", "start_frame": 0, "end_frame": 1, "vectors": {"content": [float("nan"), 0.0]}},
          {"id": "two", "start_frame": 1, "end_frame": 2, "vectors": {"content": [1.0, 0.0]}}], "finite"),
        ([{"id": "one", "start_frame": 0, "end_frame": 1, "vectors": {"content": [1.0, 0.0]}},
          {"id": "two", "start_frame": 1, "end_frame": 2, "vectors": {"content": [1.0]}}], "mixes widths"),
    ],
)
def test_load_sealed_segment_vectors_refuses_invalid_ids_and_vectors(tmp_path, segments, message):
    path = tmp_path / "q-segments.jsonl"
    digest = _write_segment_vectors(
        path, [{"id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 2,
                "source_sample_rate_hz": 16000, "segments": segments}],
    )
    with pytest.raises(ps.PhaseSupplyError, match=message):
        ps.load_sealed_segment_vectors(path, expected_sha256=digest, dimensions=("content",))


# ---------------------------------------------------------------------------
# the binding
# ---------------------------------------------------------------------------


def _built_binding(tmp_path, *, expose_facets=False):
    snapshot = _snapshot()
    query_digest = _write_vectors(
        tmp_path / "v" / "q.jsonl", [("dev:s1", {"content": [1.0, 0.0]})]
    )
    facet_digest = _write_vectors(
        tmp_path / "v" / "f.jsonl",
        [
            ("facet:content:u1", {"content": [1.0, 0.0]}),
            ("facet:content:u2", {"content": [0.0, 1.0]}),
        ],
    )
    fragment = _fragment(
        _source("v/q.jsonl", query_digest),
        _source("v/f.jsonl", facet_digest),
        expose_facets=expose_facets,
    )
    specs = ps.load_phase_supply_specs(fragment, _program())
    supply_for_phase = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
    )
    return snapshot, specs, supply_for_phase


def _context(
    snapshot,
    *,
    sample_id="dev:s1",
    query_source="speech_features",
    packet_id=None,
    packet_sha=_SHA_A,
):
    query_state = QueryState(
        query_id=f"run:{sample_id}:step0",
        query_sample_id=sample_id,
        speech_packet_id=packet_id or f"speech/{sample_id}",
        speech_packet_sha256=packet_sha,
        use_split_identity_hash=_SHA_A,
        query_source=query_source,
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256=snapshot.content_hash(),
        catalog_facet_ids=tuple(facet.facet_id for facet in snapshot.facets),
        catalog_value_ids=tuple(value.value_id for value in snapshot.values),
        query_state=query_state,
        task_contract="fake task contract",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )


def test_binding_returns_a_phase_supply_bound_to_the_contact_query_state(tmp_path):
    snapshot, _specs, supply_for_phase = _built_binding(tmp_path)
    context = _context(snapshot)
    supply = supply_for_phase("evidence", context)
    assert isinstance(supply, rc.PhaseSupply)
    supply.validate()
    assert supply.rank_result.query_state_sha256 == context.query_state.content_hash()
    assert supply.fusion_decision.query_state_sha256 == (
        context.query_state.content_hash()
    )
    assert supply.rank_result.snapshot_sha256 == snapshot.content_hash()
    # The query vector points at u1's content facet, so u1's value is the
    # one the fuser admits.
    assert "value:u1" in supply.fusion_decision.selected_value_ids


def test_binding_returns_none_for_an_undeclared_phase_and_an_unknown_sample(tmp_path):
    snapshot, _specs, supply_for_phase = _built_binding(tmp_path)
    assert supply_for_phase("direct", _context(snapshot)) is None
    assert supply_for_phase("evidence", _context(snapshot, sample_id="dev:absent")) is None


def test_segmented_query_recall_keeps_evidence_found_only_in_a_late_segment(tmp_path):
    snapshot = _snapshot()
    query_digest = _write_segment_vectors(
        tmp_path / "v" / "q.jsonl",
        [{"id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 4,
          "source_sample_rate_hz": 16000,
          "segments": [
              {"id": "early", "start_frame": 0, "end_frame": 2,
               "vectors": {"content": [0.0, 1.0]}},
              {"id": "late", "start_frame": 2, "end_frame": 4,
               "vectors": {"content": [1.0, 0.0]}},
          ]}],
    )
    facet_digest = _write_vectors(
        tmp_path / "v" / "f.jsonl",
        [("facet:content:u1", {"content": [1.0, 0.0]}),
         ("facet:content:u2", {"content": [0.0, 1.0]})],
    )
    specs = ps.load_phase_supply_specs(
        _fragment(_segment_source("v/q.jsonl", query_digest),
                  _source("v/f.jsonl", facet_digest), k=1), _program()
    )
    supply_for_phase = ps.build_supply_for_phase(
        specs, snapshot=snapshot, snapshot_sha256=snapshot.content_hash(), data_root=tmp_path
    )
    supply = supply_for_phase("evidence", _context(snapshot, query_source="speech_audio"))
    assert isinstance(supply, rc.PhaseSupply)
    assert supply.fusion_decision.selected_value_ids == ("value:u1",)
    assert type(supply_for_phase.provider_factories["evidence"]()).__name__ == "KbFacetProvider"


def test_segmented_queries_require_matching_raw_audio_and_speech_audio_source(tmp_path):
    snapshot = _snapshot()
    query_digest = _write_segment_vectors(
        tmp_path / "v" / "q.jsonl",
        [{"id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 2,
          "source_sample_rate_hz": 16000,
          "segments": [{"id": "whole", "start_frame": 0, "end_frame": 2,
                        "vectors": {"content": [1.0, 0.0]}}]}],
    )
    specs = ps.load_phase_supply_specs(
        _fragment(_segment_source("v/q.jsonl", query_digest)), _program()
    )
    supply_for_phase = ps.build_supply_for_phase(
        specs, snapshot=snapshot, snapshot_sha256=snapshot.content_hash(), data_root=tmp_path
    )
    with pytest.raises(ps.PhaseSupplyError, match="query_source='speech_audio'"):
        supply_for_phase("evidence", _context(snapshot))
    with pytest.raises(ps.PhaseSupplyError, match="audio_sha256"):
        supply_for_phase("evidence", _context(snapshot, query_source="speech_audio", packet_sha=_SHA_B))


def test_segmented_query_accepts_distinct_bound_source_and_packet_hashes(tmp_path):
    snapshot = _snapshot()
    query_digest = _write_segment_vectors(
        tmp_path / "v" / "q.jsonl",
        [{"id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 2,
          "source_sample_rate_hz": 16000,
          "segments": [{"id": "whole", "start_frame": 0, "end_frame": 2,
                        "vectors": {"content": [1.0, 0.0]}}]}],
    )
    facet_digest = _write_vectors(
        tmp_path / "v" / "f.jsonl",
        [("facet:content:u1", {"content": [1.0, 0.0]}),
         ("facet:content:u2", {"content": [0.0, 1.0]})],
    )
    specs = ps.load_phase_supply_specs(
        _fragment(
            _segment_source("v/q.jsonl", query_digest),
            _source("v/f.jsonl", facet_digest),
            tau=0.0,
        ),
        _program(),
    )
    source_bindings = {
        "dev:s1": {
            "packet_id": "speech/dev:s1",
            "packet_sha256": _SHA_B,
            "source_audio_sha256": _SHA_A,
        }
    }
    supply_for_phase = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
        source_audio_bindings=source_bindings,
    )

    supply = supply_for_phase(
        "evidence", _context(snapshot, packet_sha=_SHA_B)
    )
    assert isinstance(supply, rc.PhaseSupply)
    assert supply.fusion_decision.selected_value_ids == ("value:u1",)


@pytest.mark.parametrize(
    "binding_change, context_change, message",
    [
        ({"source_audio_sha256": _SHA_B}, {}, "source audio"),
        ({"packet_sha256": _SHA_A}, {}, "packet SHA"),
        ({"packet_id": "speech/other"}, {}, "packet id"),
        ({}, {"packet_sha": "c" * 64}, "packet SHA"),
        ({}, {"packet_id": "speech/other"}, "packet id"),
        ({}, {"sample_id": "dev:other"}, "source-audio binding"),
    ],
)
def test_segmented_query_refuses_source_packet_and_state_mismatches(
    tmp_path, binding_change, context_change, message
):
    snapshot = _snapshot()
    query_digest = _write_segment_vectors(
        tmp_path / "v" / "q.jsonl",
        [{"id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 2,
          "source_sample_rate_hz": 16000,
          "segments": [{"id": "whole", "start_frame": 0, "end_frame": 2,
                        "vectors": {"content": [1.0, 0.0]}}]}],
    )
    specs = ps.load_phase_supply_specs(
        _fragment(_segment_source("v/q.jsonl", query_digest), tau=0.0), _program()
    )
    binding = {
        "packet_id": "speech/dev:s1",
        "packet_sha256": _SHA_B,
        "source_audio_sha256": _SHA_A,
    }
    binding.update(binding_change)
    supply_for_phase = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
        source_audio_bindings={"dev:s1": binding},
    )
    context_kwargs = {"packet_sha": _SHA_B, **context_change}
    with pytest.raises(ps.PhaseSupplyError, match=message):
        supply_for_phase("evidence", _context(snapshot, **context_kwargs))


def test_a_non_kb_facet_provider_is_refused_without_an_injected_instance(tmp_path):
    query_digest = _write_vectors(
        tmp_path / "v" / "q.jsonl", [("dev:s1", {"content": [1.0]})]
    )
    fragment = _fragment(_source("v/q.jsonl", query_digest), provider="conec-context-v1")
    specs = ps.load_phase_supply_specs(fragment, _program())
    snapshot = _snapshot()
    with pytest.raises(ps.PhaseSupplyError, match="bind_phase_supply_providers"):
        ps.build_supply_for_phase(
            specs,
            snapshot=snapshot,
            snapshot_sha256=snapshot.content_hash(),
            data_root=tmp_path,
        )


def test_an_injected_provider_is_used_verbatim(tmp_path):
    """The seam KU-A1's ``dense-centroid-v1`` sketch needs: a provider this
    harness cannot construct from a KnowledgeSnapshot comes in built."""

    query_digest = _write_vectors(
        tmp_path / "v" / "q.jsonl", [("dev:s1", {"content": [1.0]})]
    )
    fragment = _fragment(_source("v/q.jsonl", query_digest), provider="dense-centroid-v1")
    specs = ps.load_phase_supply_specs(fragment, _program())
    snapshot = _snapshot()
    calls: list[str] = []

    class _FakeProvider:
        def candidates(self, query, *, k):
            calls.append("candidates")
            return "ranking"

        def fuse(self, rankings, *, k, policy_id):
            calls.append(f"fuse:{policy_id}")
            from speech_aware_evidence_acquisition.rails.knowledge import FusionDecision

            return FusionDecision(
                snapshot_sha256=snapshot.content_hash(),
                query_state_sha256=self.query_state_sha256,
                rank_result_sha256=self.rank_result.content_hash(),
                fusion_policy_id=policy_id,
                supporting_facet_ids=("facet:content:u1",),
                selected_value_ids=("value:u1",),
            ).validate()

        def last_rank_result(self):
            return self.rank_result

    from speech_aware_evidence_acquisition.rails.knowledge import (
        RankedFacet,
        RankResult,
    )

    provider = _FakeProvider()
    context = _context(snapshot)
    provider.query_state_sha256 = context.query_state.content_hash()
    provider.rank_result = RankResult(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=provider.query_state_sha256,
        ranking_policy_id="fake-rank-v1",
        candidates=(RankedFacet(facet_id="facet:content:u1", score=1.0),),
    ).validate()

    supply_for_phase = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
        provider_for_phase=lambda phase: provider,
    )
    supply = supply_for_phase("evidence", context)
    assert calls == ["candidates", "fuse:saea-fuse-supplyfilter-v1"]
    assert supply.fusion_decision.selected_value_ids == ("value:u1",)


def test_seeded_phases_never_answer_the_runtime_supply_callable(tmp_path):
    """A first phase's selection already rode the initial QueryState, so the
    runtime callable must stay silent for it."""

    snapshot = _snapshot()
    query_digest = _write_vectors(
        tmp_path / "v" / "q.jsonl", [("dev:s1", {"content": [1.0, 0.0]})]
    )
    facet_digest = _write_vectors(
        tmp_path / "v" / "f.jsonl", [("facet:content:u1", {"content": [1.0, 0.0]})]
    )
    fragment = _fragment(
        _source("v/q.jsonl", query_digest), _source("v/f.jsonl", facet_digest)
    )
    specs = ps.load_phase_supply_specs(fragment, _program())
    supply_for_phase = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
        seed_phases=("evidence",),
    )
    assert supply_for_phase("evidence", _context(snapshot)) is None


def test_build_bootstrap_selection_decides_before_the_flight(tmp_path):
    snapshot, specs, supply_for_phase = _built_binding(tmp_path)
    facets, values = ps.build_bootstrap_selection(
        specs["evidence"],
        provider=supply_for_phase.provider_factories["evidence"](),
        query_vectors_by_sample=supply_for_phase.query_tables["evidence"],
        speech_packet_bindings={
            "dev:s1": {"packet_id": "speech/dev:s1", "sha256": _SHA_A}
        },
        split_identity_hash=_SHA_A,
    )
    assert facets == {}
    assert values == {"dev:s1": ("value:u1",)}


def test_bootstrap_accepts_distinct_bound_source_and_packet_hashes(tmp_path):
    snapshot = _snapshot()
    query_digest = _write_segment_vectors(
        tmp_path / "v" / "q.jsonl",
        [{"id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 2,
          "source_sample_rate_hz": 16000,
          "segments": [{"id": "whole", "start_frame": 0, "end_frame": 2,
                        "vectors": {"content": [1.0, 0.0]}}]}],
    )
    facet_digest = _write_vectors(
        tmp_path / "v" / "f.jsonl",
        [("facet:content:u1", {"content": [1.0, 0.0]}),
         ("facet:content:u2", {"content": [0.0, 1.0]})],
    )
    specs = ps.load_phase_supply_specs(
        _fragment(
            _segment_source("v/q.jsonl", query_digest),
            _source("v/f.jsonl", facet_digest),
            tau=0.0,
        ),
        _program(),
    )
    source_bindings = {
        "dev:s1": {
            "packet_id": "speech/dev:s1",
            "packet_sha256": _SHA_B,
            "source_audio_sha256": _SHA_A,
        }
    }
    supply_for_phase = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
        source_audio_bindings=source_bindings,
    )
    facets, values = ps.build_bootstrap_selection(
        specs["evidence"],
        provider=supply_for_phase.provider_factories["evidence"](),
        query_vectors_by_sample=supply_for_phase.query_tables["evidence"],
        speech_packet_bindings={
            "dev:s1": {"packet_id": "speech/dev:s1", "sha256": _SHA_B}
        },
        source_audio_bindings=supply_for_phase.source_audio_bindings,
        split_identity_hash=_SHA_A,
    )
    assert facets == {}
    assert values == {"dev:s1": ("value:u1",)}


def test_phase_supply_receipt_never_carries_a_vector(tmp_path):
    _snapshot_obj, specs, supply_for_phase = _built_binding(tmp_path)
    receipt = ps.phase_supply_receipt(
        specs,
        supply_for_phase.query_vector_rows,
        supply_for_phase.facet_vector_rows,
    )
    assert receipt["schema"] == "saea-phase-supply-v2"
    (phase,) = receipt["phases"]
    assert phase["query_vector_rows"] == 1
    assert phase["facet_vector_rows"] == 2
    serialized = json.dumps(receipt)
    assert "1.0" not in serialized.replace('"k": 5', "")
    assert "evidence payload" not in serialized



def test_flight_runtime_injects_source_audio_binding_into_segmented_supply(tmp_path):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime

    snapshot = _snapshot()
    query_digest = _write_segment_vectors(
        tmp_path / "v" / "q.jsonl",
        [{"id": "dev:s1", "audio_sha256": _SHA_A, "source_frames": 2,
          "source_sample_rate_hz": 16000,
          "segments": [{"id": "whole", "start_frame": 0, "end_frame": 2,
                        "vectors": {"content": [1.0, 0.0]}}]}],
    )
    facet_digest = _write_vectors(
        tmp_path / "v" / "f.jsonl",
        [("facet:content:u1", {"content": [1.0, 0.0]}),
         ("facet:content:u2", {"content": [0.0, 1.0]})],
    )
    values = _fragment(
        _segment_source("v/q.jsonl", query_digest),
        _source("v/f.jsonl", facet_digest),
        tau=0.0,
    )
    source_bindings = {
        "dev:s1": {
            "packet_id": "speech/dev:s1",
            "packet_sha256": _SHA_B,
            "source_audio_sha256": _SHA_A,
        }
    }
    stub = SimpleNamespace(
        _composed=SimpleNamespace(values=values),
        _data_root=tmp_path,
        _phase_supply_providers=None,
        _phase_supply_receipt=None,
        source_audio_bindings=lambda: source_bindings,
        speech_packet_bindings=lambda: {
            "dev:s1": {"packet_id": "speech/dev:s1", "sha256": _SHA_B}
        },
        _prepare=lambda: (values, "test", "dev", _SHA_A),
    )

    supply_for_phase, specs = FlightRuntime._resolve_phase_supply(
        stub, _program(), snapshot
    )
    assert supply_for_phase.source_audio_bindings == source_bindings
    assert isinstance(
        supply_for_phase(
            "evidence", _context(snapshot, packet_sha=_SHA_B)
        ),
        rc.PhaseSupply,
    )
    assert set(specs) == {"evidence"}
