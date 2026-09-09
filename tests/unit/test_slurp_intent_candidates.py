"""Unit tests for the KU-S4N narrowing view (``rails.slurp_intent_candidates``)
and the provider that serves it.

Model-free: no model, no server, no vectors, no corpus. Every fixture below is
a synthetic label space; the REAL numbers live in the preparation receipt
``docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-kus4-prep/``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import (
    KNOWLEDGE_FUSERS,
    KNOWLEDGE_PROVIDERS,
    KNOWLEDGE_RANKERS,
)
from speech_aware_evidence_acquisition.rails import knowledge_provider as kp
from speech_aware_evidence_acquisition.rails import slurp_intent_candidates as sic
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge import QueryState

REPO_ROOT = Path(__file__).resolve().parents[2]

LEGAL = tuple(
    f"{scenario}_{action}"
    for scenario in ("alarm", "audio", "calendar", "email", "iot", "qa")
    for action in ("query", "set", "remove", "settings", "factoid", "volume")
)


def _snapshot() -> object:
    return sic.build_candidate_snapshot(
        legal_intents=LEGAL,
        train_sample_ids_by_intent={
            intent: (f"slurp:train:{index:06d}:audio-1", f"slurp:train:{index:06d}:audio-2")
            for index, intent in enumerate(sorted(LEGAL), start=1)
        },
        governed_train_relpath="datasets/slurp/metadata/train.jsonl",
    )


def _query_state(sample_id: str) -> QueryState:
    return QueryState(
        query_id=f"q:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id="slurp/devel/000011/audio-1",
        speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
    ).validate()


# --- the rule ---------------------------------------------------------------


def test_the_scenario_lead_comes_first_and_neighbours_fill_the_rest():
    offered = sic.compose_candidate_set(
        ("a_1", "a_2", "a_3", "a_4"),
        ("b_1", "a_2", "c_3", "d_4", "e_5", "f_6", "g_7"),
        8,
        scenario_lead=3,
    )
    assert offered == ("a_1", "a_2", "a_3", "b_1", "c_3", "d_4", "e_5", "f_6")
    assert len(set(offered)) == len(offered)


def test_k_is_a_cap_and_a_short_neighbour_list_yields_a_short_offer():
    offered = sic.compose_candidate_set(("a_1",), ("b_1", "b_1"), 8, scenario_lead=3)
    assert offered == ("a_1", "b_1")


def test_the_rule_matches_the_mf8_audits_own_function_byte_for_byte():
    """The audit priced the family; the flight-side module must be the same
    rule, not a similar one."""

    path = REPO_ROOT / "scripts" / "mf8_speech_to_knowledge_audit.py"
    spec = importlib.util.spec_from_file_location("saea_mf8_audit_for_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = (
        ((), ("a_1", "b_2"), 3, 0),
        (("a_1", "a_2", "a_3", "a_4"), ("b_1", "a_2"), 8, 3),
        (("a_1",), (), 5, 3),
        (("a_1", "a_2"), ("a_1", "c_3", "d_4", "e_5", "f_6", "g_7", "h_8", "i_9"), 8, 3),
    )
    for scenario, neighbours, k, lead in cases:
        assert sic.compose_candidate_set(
            scenario, neighbours, k, scenario_lead=lead
        ) == module.compose_candidates(scenario, neighbours, k, scenario_lead=lead)


def test_bad_k_and_bad_lead_refuse():
    with pytest.raises(sic.SlurpIntentCandidateError):
        sic.compose_candidate_set((), ("a_1",), 0)
    with pytest.raises(sic.SlurpIntentCandidateError):
        sic.compose_candidate_set((), ("a_1",), 3, scenario_lead=-1)


# --- the twin ---------------------------------------------------------------


def test_the_twin_matches_the_count_and_shares_nothing_with_the_arm():
    arm = ("alarm_query", "alarm_set", "qa_factoid")
    twin = sic.compose_twin_set(arm, LEGAL, sample_id="slurp:devel:000011:audio-1")
    assert len(twin) == len(arm)
    assert not set(twin) & set(arm)
    assert set(twin) <= set(LEGAL)


def test_the_twin_is_reproducible_from_the_seed_and_the_sample_id_alone():
    arm = ("alarm_query", "alarm_set", "qa_factoid")
    first = sic.compose_twin_set(arm, LEGAL, sample_id="slurp:devel:000011:audio-1")
    again = sic.compose_twin_set(arm, LEGAL, sample_id="slurp:devel:000011:audio-1")
    other = sic.compose_twin_set(arm, LEGAL, sample_id="slurp:devel:000053:audio-1")
    assert first == again
    assert first != other


def test_a_pool_too_small_for_the_arms_count_refuses():
    with pytest.raises(sic.SlurpIntentCandidateError):
        sic.compose_twin_set(("a_1", "a_2"), ("a_1", "a_2", "a_3"), sample_id="s")


# --- the blocks -------------------------------------------------------------


def test_a_block_names_its_intent_and_decomposes_it_at_the_first_underscore():
    assert sic.render_candidate_block("recommendation_events") == (
        "Candidate intent for the spoken command in this request: recommendation_events "
        '(scenario "recommendation", action "events").'
    )


def test_a_non_intent_string_refuses_rather_than_rendering_nonsense():
    for bad in ("alarm", "_set", "alarm_"):
        with pytest.raises(sic.SlurpIntentCandidateError):
            sic.render_candidate_block(bad)


def test_the_facet_key_is_not_a_bare_label_name():
    """The comparator's own closed label inventory names all sixty intents, so
    a bare-name facet would make ``rails.runner``'s containment fold refuse
    the very instruction this family holds byte-identical."""

    from speech_aware_evidence_acquisition.rails.runner import (
        _protected_knowledge_material,
    )

    snapshot = _snapshot()
    protected = _protected_knowledge_material(snapshot)
    assert protected
    assert all(material != intent for material in protected for intent in LEGAL)
    inventory_like = " ".join(sorted(LEGAL))
    assert not [material for material in protected if material in inventory_like]


# --- the snapshot -----------------------------------------------------------


def test_the_snapshot_carries_one_facet_and_one_value_per_legal_intent():
    snapshot = _snapshot()
    assert len(snapshot.facets) == len(set(LEGAL))
    assert len(snapshot.values) == len(set(LEGAL))
    assert {value.task_target for value in snapshot.values} == set(LEGAL)


def test_the_snapshot_refuses_a_devel_source_id():
    with pytest.raises(sic.SlurpIntentCandidateError):
        sic.build_candidate_snapshot(
            legal_intents=("alarm_set",),
            train_sample_ids_by_intent={"alarm_set": ("slurp:devel:000011:audio-1",)},
            governed_train_relpath="datasets/slurp/metadata/train.jsonl",
        )


def test_the_split_identity_is_derived_from_the_source_set_the_builder_uses():
    ids = ("slurp:train:000002:audio-1", "slurp:train:000001:audio-1")
    assert sic.train_split_identity_hash(ids) == hashlib.sha256(
        "\n".join(sorted(ids)).encode("utf-8")
    ).hexdigest()


# --- the bank ---------------------------------------------------------------


def _write_bank(tmp_path: Path, arm, twin, *, k=3) -> tuple[Path, str]:
    payload = sic.serialize_bank(
        sic.bank_rows(arm, twin, k=k, scenario_lead=sic.DEFAULT_SCENARIO_LEAD)
    )
    path = tmp_path / "bank.jsonl"
    path.write_text(payload, encoding="utf-8", newline="\n")
    return path, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_a_bank_round_trips_and_verifies_its_own_hash(tmp_path):
    arm = {"s1": ("alarm_query", "alarm_set", "qa_factoid")}
    twin = {"s1": ("email_query", "iot_set", "audio_volume")}
    path, digest = _write_bank(tmp_path, arm, twin)
    bank = sic.load_candidate_bank(path, expected_sha256=digest)
    assert bank.selection("candidates") == arm
    assert bank.selection("twin_candidates") == twin
    assert bank.k == 3


def test_a_bank_whose_bytes_moved_refuses(tmp_path):
    path, digest = _write_bank(
        tmp_path, {"s1": ("alarm_query",)}, {"s1": ("iot_set",)}, k=1
    )
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    path.write_text(
        path.read_text(encoding="utf-8").replace("alarm_query", "alarm_set"),
        encoding="utf-8",
    )
    with pytest.raises(sic.SlurpIntentCandidateError):
        sic.load_candidate_bank(path, expected_sha256=digest)


def test_a_twin_overlapping_its_own_arm_refuses(tmp_path):
    payload = sic.serialize_bank(
        sic.bank_rows(
            {"s1": ("alarm_query", "alarm_set")},
            {"s1": ("alarm_query", "iot_set")},
            k=2,
            scenario_lead=3,
        )
    )
    path = tmp_path / "bad.jsonl"
    path.write_text(payload, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    with pytest.raises(sic.SlurpIntentCandidateError):
        sic.load_candidate_bank(path, expected_sha256=digest)


def test_a_bank_without_its_schema_header_refuses(tmp_path):
    payload = json.dumps({"schema": "something-else"}) + "\n"
    path = tmp_path / "bad.jsonl"
    path.write_text(payload, encoding="utf-8", newline="\n")
    with pytest.raises(sic.SlurpIntentCandidateError):
        sic.load_candidate_bank(
            path, expected_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest()
        )


def test_an_unknown_selection_name_refuses(tmp_path):
    path, digest = _write_bank(
        tmp_path, {"s1": ("alarm_query",)}, {"s1": ("iot_set",)}, k=1
    )
    bank = sic.load_candidate_bank(path, expected_sha256=digest)
    with pytest.raises(sic.SlurpIntentCandidateError):
        bank.selection("gold")


# --- the provider -----------------------------------------------------------


def _provider(tmp_path, selection="candidates"):
    arm = {"s1": ("alarm_query", "alarm_set", "qa_factoid")}
    twin = {"s1": ("email_query", "iot_set", "audio_volume")}
    path, digest = _write_bank(tmp_path, arm, twin)
    bank = sic.load_candidate_bank(path, expected_sha256=digest)
    snapshot = _snapshot()
    provider = kp.SlurpIntentCandidateProvider(bank=bank, selection=selection)
    provider.adopt(
        snapshot,
        policy_id="frozen-snapshot:direct",
        source_ids=(),
        snapshot_sha256=snapshot.content_hash(),
    )
    return provider, snapshot


def test_the_provider_and_its_two_policy_ids_are_registered():
    assert "slurp-intent-candidates-v1" in KNOWLEDGE_PROVIDERS.names()
    assert kp.SLURP_INTENT_CANDIDATES_RANK_POLICY_ID in KNOWLEDGE_RANKERS.names()
    assert kp.SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID in KNOWLEDGE_FUSERS.names()


def test_the_two_policy_ids_resolve_and_refuse_to_be_constructed():
    for registry, name in (
        (KNOWLEDGE_RANKERS, kp.SLURP_INTENT_CANDIDATES_RANK_POLICY_ID),
        (KNOWLEDGE_FUSERS, kp.SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID),
    ):
        factory = registry.resolve(name)
        with pytest.raises(RailsError):
            factory(None)


def test_the_provider_serves_the_banks_order_and_nothing_else(tmp_path):
    provider, _snapshot_object = _provider(tmp_path)
    ranking = provider.candidates({"query_state": _query_state("s1")}, k=8)
    assert [entry.entry_id for entry in ranking.entries] == [
        sic.facet_id_for("alarm_query"),
        sic.facet_id_for("alarm_set"),
        sic.facet_id_for("qa_factoid"),
    ]
    decision = provider.fuse([ranking], k=8, policy_id=kp.SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID)
    assert list(decision.selected_value_ids) == [
        sic.value_id_for("alarm_query"),
        sic.value_id_for("alarm_set"),
        sic.value_id_for("qa_factoid"),
    ]
    assert provider.last_rank_result() is not None


def test_the_twin_selection_serves_the_twin_draw(tmp_path):
    provider, _ = _provider(tmp_path, selection="twin_candidates")
    ranking = provider.candidates({"query_state": _query_state("s1")}, k=8)
    assert [entry.entry_id for entry in ranking.entries] == [
        sic.facet_id_for("email_query"),
        sic.facet_id_for("iot_set"),
        sic.facet_id_for("audio_volume"),
    ]


def test_a_sample_the_bank_does_not_carry_yields_an_empty_ranking(tmp_path):
    provider, _ = _provider(tmp_path)
    ranking = provider.candidates({"query_state": _query_state("unknown")}, k=8)
    assert ranking.entries == ()


def test_the_provider_refuses_a_bank_that_was_never_hash_verified():
    with pytest.raises(RailsError):
        kp.SlurpIntentCandidateProvider(bank={"s1": ("alarm_set",)})


def test_the_provider_refuses_an_unknown_selection(tmp_path):
    arm = {"s1": ("alarm_query",)}
    twin = {"s1": ("iot_set",)}
    path, digest = _write_bank(tmp_path, arm, twin, k=1)
    bank = sic.load_candidate_bank(path, expected_sha256=digest)
    with pytest.raises(RailsError):
        kp.SlurpIntentCandidateProvider(bank=bank, selection="gold")


def test_the_provider_refuses_a_bank_the_snapshot_does_not_card(tmp_path):
    payload = sic.serialize_bank(
        sic.bank_rows({"s1": ("not_registered",)}, {"s1": ("alarm_set",)}, k=1, scenario_lead=3)
    )
    path = tmp_path / "bank.jsonl"
    path.write_text(payload, encoding="utf-8", newline="\n")
    bank = sic.load_candidate_bank(
        path, expected_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest()
    )
    snapshot = _snapshot()
    provider = kp.SlurpIntentCandidateProvider(bank=bank)
    provider.adopt(
        snapshot,
        policy_id="frozen-snapshot:direct",
        source_ids=(),
        snapshot_sha256=snapshot.content_hash(),
    )
    with pytest.raises(RailsError):
        provider.candidates({"query_state": _query_state("s1")}, k=8)


def test_the_provider_does_not_build():
    bank_free = pytest.raises(RailsError)
    with bank_free:
        kp.SlurpIntentCandidateProvider(bank=None)


def test_fuse_before_candidates_refuses(tmp_path):
    provider, _ = _provider(tmp_path)
    with pytest.raises(RailsError):
        provider.fuse([], k=8)


# --- the program ------------------------------------------------------------


def test_the_supplied_direct_program_is_registered_and_declares_supplied_knowledge():
    from speech_aware_evidence_acquisition.core.base import AGENT_CONTROLLERS
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

    assert "phase-direct-only-supplied-v1" in AGENT_CONTROLLERS.names()
    program = default_phase_program("phase-direct-only-supplied-v1")
    assert program.phase_names() == ("direct",)
    assert program.phases[0].knowledge == "supplied"
    unsupplied = default_phase_program("phase-direct-only-v1")
    assert unsupplied.phases[0].knowledge == "none"


def test_the_two_registered_fragments_differ_only_in_the_bank_selection_and_identity():
    arm = json.loads(
        (
            REPO_ROOT / "configs/baseline/slurp-phase-direct-candidates-kus4n-v1.json"
        ).read_text(encoding="utf-8")
    )
    twin = json.loads(
        (
            REPO_ROOT / "configs/baseline/slurp-phase-direct-candidates-kus4n-twin-v1.json"
        ).read_text(encoding="utf-8")
    )
    behavioural = {
        key
        for key in set(arm) | set(twin)
        if not key.startswith(("what_", "why_", "the_", "arm_basis", "instruction_basis"))
    }
    moved = sorted(key for key in behavioural if arm.get(key) != twin.get(key))
    assert moved == [
        "candidate_bank_selection",
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
    ]
    assert arm["candidate_bank_sha256"] == twin["candidate_bank_sha256"]
    assert arm["knowledge_snapshot_sha256"] == twin["knowledge_snapshot_sha256"]
    assert arm["policy"] == twin["policy"] == "phase-direct-only-supplied-v1"
    assert arm["phase_review"] == twin["phase_review"]
