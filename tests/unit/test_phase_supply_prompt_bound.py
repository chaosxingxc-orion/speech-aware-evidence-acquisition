"""E6 deliverable 4: the prompt estimate sees a supplied phase's TRACED
blocks.

A supplied phase's knowledge never touches its instruction, but it is still
part of the request. An estimate that counted only the instruction would
under-count exactly the cell it exists for -- the same defect KC-S1's
per-sample ``state_fill`` produced (about 7,500 tokens short). These tests
pin the two halves of the fix: ``render_phase_prompt_envelopes`` renders the
blocks, and ``FlightRuntime._phase_supply_prompt_bound`` produces a true
UPPER BOUND on them without loading a vector file.

No model, GPU, network or embedding contact.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    phase_envelope_sha256,
    render_phase_prompt_envelopes,
)
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.phase_material import (
    PhaseMaterialError,
    PhaseMaterialSpec,
    render_phase_envelope,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def _specs():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    return program, {
        phase.name: PhaseMaterialSpec(
            phase=phase.name,
            purpose=phase.purpose,
            instruction_template="probes/x.txt",
            predecessor_binding="none",
        ).validate()
        for phase in program.phases
    }


def _envelopes(supply_blocks_by_phase=None):
    program, specs = _specs()
    return render_phase_prompt_envelopes(
        program_id=program.program_id,
        phase_names=program.phase_names(),
        specs=specs,
        static_text_by_phase={
            "direct": "static directive for direct",
            "evidence": "static directive for evidence",
        },
        system_text="fake system message",
        prompt_order="speech-query-prefix-v2",
        packet_descriptor={"packet_id": "s1", "sha256": _SHA_A},
        sample_id="s1",
        supply_blocks_by_phase=supply_blocks_by_phase,
        completion_token_ceiling=64,
    )


def test_omitting_supply_blocks_renders_byte_identically_to_before_e6():
    """A pinned prompt-fit receipt measured before this parameter existed
    still verifies."""

    assert _envelopes() == _envelopes({})
    assert _envelopes(None) == _envelopes({"direct": (), "evidence": ()})


def test_supplied_blocks_enter_the_estimated_envelope():
    blocks = (
        ("[evidence value:u1] a long enough evidence payload for u1", "value"),
        ("[evidence value:u2] a long enough evidence payload for u2", "value"),
    )
    plain = _envelopes()
    supplied = _envelopes({"evidence": blocks})

    # The unsupplied phase is untouched; the supplied one grows by exactly
    # the block texts.
    assert supplied["direct"] == plain["direct"]
    assert phase_envelope_sha256(supplied["evidence"]) != phase_envelope_sha256(
        plain["evidence"]
    )
    rendered = json.dumps(list(supplied["evidence"]), ensure_ascii=False)
    for text, _role in blocks:
        assert text in rendered
    # And the instruction itself is unchanged -- the whole point of the
    # traced channel.
    plain_size = len(json.dumps(list(plain["evidence"]), ensure_ascii=False))
    supplied_size = len(rendered)
    assert supplied_size > plain_size


def test_render_phase_envelope_refuses_an_untyped_supply_block():
    with pytest.raises(PhaseMaterialError, match="roles must be"):
        render_phase_envelope(
            "system",
            "instruction",
            prompt_order="speech-query-prefix-v2",
            packet_descriptor={"packet_id": "s1", "sha256": _SHA_A},
            contact_id="c1",
            supply_blocks=(("[evidence v1] text", "smuggled"),),
        )


def _snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="prompt-bound-test-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:t1",),
        builder_policy_id="test-builder-v1",
        facets=tuple(
            KeyFacet(
                facet_id=f"facet:content:{index}",
                dimension="content",
                representation_kind="text",
                representation="k" * (10 + index),
                source_sample_ids=("train:t1",),
            )
            for index in range(6)
        ),
        values=tuple(
            ValueBundle(
                value_id=f"value:{index}",
                content="v" * (10 + index),
                associated_facet_ids=(f"facet:content:{index}",),
                source_sample_ids=("train:t1",),
                provenance_refs=("train:t1",),
                task_target=f"t{index}",
            )
            for index in range(6)
        ),
    ).validate()


def _bound(expose_facets: bool):
    """``FlightRuntime._phase_supply_prompt_bound`` on a stub carrying only
    the two things it reads: the composed baseline values and the frozen
    snapshot. Called unbound so the test needs no repo, no data root and no
    preflight."""

    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    snapshot = _snapshot()
    stub = SimpleNamespace(
        _composed=SimpleNamespace(
            values={
                "phase_supply": {
                    "evidence": {
                        "provider": "kb-facet-v1",
                        "rank_policy": "saea-rank-wcos-prior-agree-v1",
                        "fuse_policy": "saea-fuse-supplyfilter-v1",
                        "k": 3,
                        "tau": 0.65,
                        "dimensions": ["content"],
                        "expose_facets": expose_facets,
                        "fuse_coverage": {"m": 2, "c": 2, "top_l": 3},
                        "query_source": {
                            "kind": "sealed-vectors",
                            "relpath": "v/q.jsonl",
                            "sha256": _SHA_A,
                            "tool_contact_ledger_row": "TEST-EMB-0001",
                            "embedded_signal": "speech: synthetic",
                        },
                    }
                }
            }
        ),
        _load_knowledge_snapshot=lambda: snapshot,
    )
    return FlightRuntime._phase_supply_prompt_bound(stub, program)


def test_prompt_bound_takes_the_k_longest_values_as_a_true_ceiling():
    bound = _bound(expose_facets=False)
    assert set(bound) == {"evidence"}
    blocks = bound["evidence"]
    assert len(blocks) == 3
    assert all(role == "value" for _text, role in blocks)
    # The three LONGEST values, longest first -- no per-sample decision can
    # select more than k, and none can select a longer one.
    assert [text for text, _role in blocks] == [
        f"[evidence value:{index}] {'v' * (10 + index)}" for index in (5, 4, 3)
    ]


def test_prompt_bound_adds_the_m_longest_facets_for_a_facet_exposing_phase():
    blocks = _bound(expose_facets=True)["evidence"]
    keys = [text for text, role in blocks if role == "key"]
    values = [text for text, role in blocks if role == "value"]
    assert len(keys) == 2  # fuse_coverage.m
    assert len(values) == 3  # k
    assert keys == [
        f"[evidence key:facet:content:{index}] {'k' * (10 + index)}"
        for index in (5, 4)
    ]


def test_prompt_bound_is_empty_for_a_cell_that_supplies_nothing():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    stub = SimpleNamespace(
        _composed=SimpleNamespace(values={}),
        _load_knowledge_snapshot=lambda: pytest.fail(
            "an unsupplied cell must not load the snapshot for a prompt bound"
        ),
    )
    assert FlightRuntime._phase_supply_prompt_bound(stub, program) == {}
