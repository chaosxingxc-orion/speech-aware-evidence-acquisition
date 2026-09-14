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
from types import MappingProxyType, SimpleNamespace

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


def _named_candidate_bound(
    *, mode="provide", ordinary=False, malformed=False, native=True, refreshes=0
):
    from speech_aware_evidence_acquisition.rails.controllers import (
        PhaseProgram,
        PhaseSpec,
    )
    from speech_aware_evidence_acquisition.rails.knowledge_stores import (
        KnowledgeStore,
        KnowledgeStoreBinding,
    )

    if native:
        registered = rc.default_phase_program(
            "phase-audio2tool-native-candidates-review-revise-v1"
        )
        revisions = max(1, refreshes)
        max_contacts = 1 + (revisions + 1) * 3 + refreshes
        program = PhaseProgram(
            program_id="synthetic-native-candidate-bound-v1",
            phases=registered.phases,
            max_contacts=max_contacts,
            stop_rule="native-role-episode",
        ).validate()
    else:
        program = PhaseProgram(
            program_id="synthetic-linear-candidate-bound-v1",
            phases=(
                PhaseSpec("perception", "propose", "supplied", None, False),
                PhaseSpec("solver", "solve", "supplied", None, False),
                PhaseSpec("review", "review", "supplied", None, False),
            ),
            max_contacts=3,
            stop_rule="always-run-full-program",
        ).validate()

    parameter = _snapshot()
    candidate = {
        "provider": "audio2tool-candidate-semantic-v1",
        "rank_policy": "saea-ranked-candidate-round-robin-v1",
        "fuse_policy": "saea-candidate-semantic-passthrough-v1",
        "candidate_state_phase": "perception",
        "compact_source_phase": "perception",
        "max_actions": 2,
        "max_candidates_per_action": 2,
        "max_values_per_candidate": 1,
        "max_total_values": 2,
        "supply_mode": mode,
    }
    if malformed:
        candidate["max_total_values"] = 5
    if refreshes:
        candidate["candidate_state_selection"] = "latest"
    pin = MappingProxyType({"relpath": "unused.json", "sha256": _SHA_A})
    stores = {
        "parameter-meaning": KnowledgeStore(
            "parameter-meaning",
            "parameter-meaning",
            parameter,
            pin,
            pin,
            pin,
            MappingProxyType({}),
            MappingProxyType({"solver": candidate}),
        )
    }
    if ordinary:
        activation = parameter
        stores["tool-activation"] = KnowledgeStore(
            "tool-activation",
            "tool-activation",
            activation,
            pin,
            pin,
            pin,
            MappingProxyType(
                {
                    "perception": {
                        "provider": "kb-facet-v1",
                        "rank_policy": "saea-rank-wcos-prior-agree-v1",
                        "fuse_policy": "saea-fuse-supplyfilter-v1",
                        "k": 1,
                        "tau": 0.0,
                        "dimensions": ["content"],
                        "expose_facets": False,
                        "query_source": {
                            "kind": "sealed-vectors",
                            "relpath": "unused.jsonl",
                            "sha256": _SHA_A,
                            "tool_contact_ledger_row": "SYNTHETIC-BOUND",
                            "embedded_signal": "speech: synthetic bound",
                        },
                    }
                }
            ),
            MappingProxyType({}),
        )
    stores = MappingProxyType(dict(sorted(stores.items())))
    binding = KnowledgeStoreBinding(stores, parameter, _SHA_B)
    values = {"knowledge_stores": {}}
    if native:
        values["native_episode"] = {
            "schema": "saea-native-episode-config-v1",
            "episode_id": "synthetic-native-candidate-bound-v1",
            "max_revisions": revisions,
            "actions": {
                "accept": "ACCEPT",
                "revise": "REVISE",
                "acquire": "ACQUIRE",
            },
            "roles": {
                kind: {"phase_id": kind, "max_iterations": 1}
                for kind in ("perception", "solver", "reviewer", "planner")
            },
        }
        if refreshes:
            values["native_episode"]["candidate_refresh"] = {
                "action": "REFRESH_CANDIDATES",
                "max_refreshes": refreshes,
            }
    stub = SimpleNamespace(
        _composed=SimpleNamespace(values=values),
        _knowledge_store_binding=binding,
        _load_knowledge_snapshot=lambda: parameter,
    )
    return FlightRuntime._phase_supply_prompt_bound(stub, program)

def test_candidate_only_store_bounds_longest_values_and_native_retained_history():
    bound = _named_candidate_bound()
    assert set(bound) == {"perception", "solver", "reviewer", "planner"}
    for blocks in bound.values():
        assert [text for text, role in blocks if role == "value"] == [
            f"[evidence parameter-meaning::value:{index}] "
            f"[knowledge store=parameter-meaning role=parameter-meaning] "
            f"{'v' * (10 + index)}"
            for index in (5, 4)
        ]

def test_native_refresh_bound_includes_disjoint_selections_up_to_snapshot_size():
    bound = _named_candidate_bound(refreshes=1)
    for blocks in bound.values():
        assert [text for text, role in blocks if role == "value"] == [
            f"[evidence parameter-meaning::value:{index}] "
            f"[knowledge store=parameter-meaning role=parameter-meaning] "
            f"{'v' * (10 + index)}"
            for index in (5, 4, 3, 2)
        ]

def test_linear_candidate_bound_starts_at_target_and_retains_into_later_phase():
    bound = _named_candidate_bound(native=False)
    assert "perception" not in bound
    assert bound["solver"] == bound["review"]

def test_ordinary_and_candidate_store_bounds_are_combined_without_replacement():
    bound = _named_candidate_bound(ordinary=True)
    for phase in ("perception", "solver", "reviewer", "planner"):
        text = "\n".join(block for block, _role in bound[phase])
        assert "tool-activation::value:5" in text
        assert "parameter-meaning::value:5" in text
        assert "parameter-meaning::value:4" in text

def test_withheld_candidate_supply_adds_no_prompt_bound():
    assert _named_candidate_bound(mode="withhold") == {}

def test_malformed_candidate_supply_is_rejected_by_the_shared_loader():
    from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (
        CandidateSemanticSupplyError,
    )

    with pytest.raises(CandidateSemanticSupplyError, match="max_total_values"):
        _named_candidate_bound(malformed=True)

def test_shared_slurp_program_supports_null_arm_without_direct_prompt_id_drift():
    """A config-only null arm keeps the direct model-visible program identity."""
    import copy
    from pathlib import Path

    from speech_aware_evidence_acquisition.rails.phase_material import (
        build_material_for_phase,
        load_phase_material_specs,
    )
    from speech_aware_evidence_acquisition.rails.phase_supply import load_phase_supply_specs

    root = Path(__file__).resolve().parents[2]
    baseline_root = root / "configs" / "baseline"
    control = json.loads(
        (baseline_root / "slurp-live-intent-slots-control-recovery-v1.json").read_text()
    )
    speech = json.loads(
        (baseline_root / "slurp-live-intent-slots-speech-v1.json").read_text()
    )
    null = copy.deepcopy(control)
    null["policy"] = speech["policy"]
    null["phase_supply"] = {}

    def program(values):
        raw = json.loads(
            (root / "configs" / "policy" / (values["policy"] + ".json")).read_text()
        )
        return rc.PhaseProgram(
            program_id=raw["program_id"],
            phases=tuple(rc.PhaseSpec(**phase) for phase in raw["phases"]),
            max_contacts=raw["max_contacts"],
            stop_rule=raw["stop_rule"],
        ).validate()

    shared = program(null)
    assert load_phase_supply_specs(null, shared) == {}
    absent = copy.deepcopy(null)
    del absent["phase_supply"]
    assert load_phase_supply_specs(absent, shared) == {}
    assert set(load_phase_supply_specs(speech, shared)) == {"slots"}
    assert control["phase_material"] == speech["phase_material"]

    def direct_envelope(values):
        configured = program(values)
        material = build_material_for_phase(
            load_phase_material_specs(values, configured),
            program_id=configured.program_id,
            static_text_by_phase={
                "direct": "Transcribe the speech and identify its scenario and action.",
                "slots": "Extract the stated slots.",
            },
            response_format_by_phase={},
            state_fill_by_phase={"slots": lambda content: "Synthetic slot schema."},
        )("direct", SimpleNamespace(sample_id="synthetic-config-proof"), {})
        return render_phase_envelope(
            "Use only supplied evidence.",
            material.instruction,
            prompt_order="speech-query-prefix-v2",
            packet_descriptor={
                "packet_id": "synthetic-config-proof",
                "sha256": _SHA_A,
            },
            contact_id=material.contact_id,
            supply_blocks=(),
        )

    assert direct_envelope(null) == direct_envelope(absent) == direct_envelope(speech)
    assert direct_envelope(control) != direct_envelope(speech)
