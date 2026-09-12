"""Cell KU-S3 (2026-09-07): the SLURP slot stage with speech-keyed neighbour
fillers supplied as traced typed content, and its form twin.

What is pinned here is what makes the cell a one-factor contrast against the
sealed KC-S1b rows, plus the two ``core.flight.runtime`` seam repairs the
preparation needed. Zero model, GPU, network and embedding contacts; synthetic
vectors and a synthetic snapshot only.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import phase_supply as ps
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINES = _REPO_ROOT / "configs" / "baseline"
_SHA_C = "c" * 64

_SPEECH = json.loads(
    (_BASELINES / "slurp-phase-slots-supplied-fillers-speech-v1.json").read_text("utf-8")
)
_TWIN = json.loads(
    (_BASELINES / "slurp-phase-slots-supplied-fillers-twin-v1.json").read_text("utf-8")
)
_STATE = json.loads(
    (_BASELINES / "slurp-phase-slots-supplied-fillers-speech-state-v1.json").read_text(
        "utf-8"
    )
)
_KC_S1B = json.loads(
    (_BASELINES / "slurp-phase-slots-given-intent-schema-v1.json").read_text("utf-8")
)


# ---------------------------------------------------------------------------
# The program, and what the fragments declare
# ---------------------------------------------------------------------------


def test_the_supplied_program_is_kc_s1b_s_program_with_one_word_changed():
    """Two program ids rather than a flag on one: a phase's ``knowledge``
    value rides the config hash, so KC-S1b and KU-S3 must never resolve to
    the same program object."""

    plain = rc.default_phase_program("phase-slots-given-intent-v1")
    supplied = rc.default_phase_program("phase-slots-given-intent-supplied-v1")
    assert plain.phase_names() == supplied.phase_names() == ("slots",)
    assert plain.max_contacts == supplied.max_contacts == 1
    assert plain.phases[0].knowledge == "none"
    assert supplied.phases[0].knowledge == "supplied"
    assert plain.phases[0].purpose == supplied.phases[0].purpose
    assert supplied.program_id in rc.registered_program_ids()


@pytest.mark.parametrize("fragment", [_SPEECH, _TWIN, _STATE])
def test_each_ku_s3_fragment_resolves_to_a_top_5_supply_spec(fragment):
    program = rc.default_phase_program(fragment["policy"])
    specs = ps.load_phase_supply_specs(fragment, program)
    spec = specs["slots"]
    assert spec.provider == "kb-facet-v1"
    assert spec.k == 5
    assert spec.dimensions == ("content",)
    assert spec.expose_facets is False
    assert spec.alpha is None
    # The locked BLEND knobs do NOT transfer: at tau 0.65 no cross-modal
    # candidate is admitted at all (preregistration section 3).
    assert spec.tau == 0.0
    knobs = spec.fuse_knobs()
    assert (knobs.m, knobs.c, knobs.top_l) == (5, 5, 5)
    weights = spec.rank_weights_or_none()
    assert (weights.w_cos, weights.w_prior, weights.w_agree) == (1.0, 0.0, 0.0)


@pytest.mark.parametrize(
    "fragment,modality",
    [(_SPEECH, "speech"), (_TWIN, "speech"), (_STATE, "speech+state")],
)
def test_each_query_source_declares_its_modality_and_the_twin_says_whose_speech(
    fragment, modality
):
    source = fragment["phase_supply"]["slots"]["query_source"]
    assert ps.query_signal_modality(source, field="q") == modality
    FlightRuntime._assert_phase_supply_is_legal_for(
        SimpleNamespace(_composed=SimpleNamespace(values=fragment)), fragment["policy"]
    )
    if fragment is _TWIN:
        # The twin's vectors ARE speech vectors -- of another recording. The
        # modality token is honest; the prose has to say whose.
        assert "ANOTHER row" in source["embedded_signal"]


def test_the_key_side_is_unconstrained_and_says_so():
    facet = _SPEECH["phase_supply"]["slots"]["facet_source"]
    assert facet["embedded_signal"].startswith("text:")
    with pytest.raises(ps.PhaseSupplyError):
        ps.assert_query_signal_declares_speech(facet["embedded_signal"], field="f")


# ---------------------------------------------------------------------------
# One factor, three ways
# ---------------------------------------------------------------------------


_IDENTITY_KEYS = {
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
}
_NOTE_PREFIXES = ("what_", "why_", "the_one_", "how_", "predecessor_is_", "knowledge_is_")


def _substantive(fragment):
    """The fragment minus its free-English note blocks and the two identity
    ids every arm must own uniquely."""

    return {
        key: value
        for key, value in fragment.items()
        if key not in _IDENTITY_KEYS and not key.startswith(_NOTE_PREFIXES)
    }


def test_the_twin_differs_from_the_speech_arm_only_in_the_query_source():
    left, right = _substantive(_SPEECH), _substantive(_TWIN)
    differing = {key for key in set(left) | set(right) if left.get(key) != right.get(key)}
    assert differing == {"phase_supply"}
    a = _SPEECH["phase_supply"]["slots"]
    b = _TWIN["phase_supply"]["slots"]
    assert {k: v for k, v in a.items() if k != "query_source"} == {
        k: v for k, v in b.items() if k != "query_source"
    }
    assert a["query_source"]["relpath"] != b["query_source"]["relpath"]
    assert a["query_source"]["sha256"] != b["query_source"]["sha256"]
    # Same producing contact row: the twin embeds nothing new, it permutes.
    assert (
        a["query_source"]["tool_contact_ledger_row"]
        == b["query_source"]["tool_contact_ledger_row"]
    )


def test_the_state_key_differs_from_the_speech_arm_only_in_the_query_source():
    left, right = _substantive(_SPEECH), _substantive(_STATE)
    differing = {key for key in set(left) | set(right) if left.get(key) != right.get(key)}
    assert differing == {"phase_supply"}


def test_ku_s3_is_kc_s1b_plus_supply_and_nothing_else():
    """The scientific claim as an assertion: against the sealed KC-S1b rows
    the only things that move are the supply, the program id that lets a
    phase receive it, and the snapshot view that lets the leakage rule
    tolerate a bound content dimension."""

    left, right = _substantive(_KC_S1B), _substantive(_SPEECH)
    differing = {key for key in set(left) | set(right) if left.get(key) != right.get(key)}
    assert differing == {
        "phase_supply",
        "policy",
        "knowledge_snapshot_relpath",
        "knowledge_snapshot_sha256",
    }
    # The instruction path -- template, fill, sealed predecessor, geometry --
    # is byte-identical, which is what makes the contrast one-factor.
    assert _SPEECH["phase_material"] == _KC_S1B["phase_material"]
    assert _SPEECH["task_instruction_template"] == _KC_S1B["task_instruction_template"]
    assert _SPEECH["task_instruction_fill"] == _KC_S1B["task_instruction_fill"]
    assert _SPEECH["serving_slots"] == _KC_S1B["serving_slots"] == 4
    assert _SPEECH["serving_slot_tokens"] == _KC_S1B["serving_slot_tokens"] == 16384
    assert _SPEECH["scorers"] == _KC_S1B["scorers"]


def test_the_predecessor_binding_does_not_project():
    """The comparator's own blocks were chosen from UNPROJECTED bytes, so an
    arm that projected would beat it partly by better block selection."""

    material = _SPEECH["phase_material"]["slots"]
    assert material["predecessor_binding"] == "sealed-manifest"
    assert material["state_fill"] == "slurp-intent-slot-schema-for-state"
    assert "fill_params" not in material


# ---------------------------------------------------------------------------
# The two seam repairs (2026-09-07)
# ---------------------------------------------------------------------------


def _snapshot():
    facets = (
        KeyFacet(
            facet_id="facet:content:u1",
            dimension="content",
            representation='TRAIN utterance u1 (slot-filler retrieval key): "lights off"',
            representation_kind="text",
            source_sample_ids=("train:u1",),
        ).validate(),
    )
    values = (
        ValueBundle(
            value_id="value:u1",
            content="Slot type=filler pairs observed in TRAIN utterance u1: device_type=lights.",
            associated_facet_ids=("facet:content:u1",),
            source_sample_ids=("train:u1",),
            provenance_refs=("utterance:u1",),
            task_target="iot_hue_lightoff",
            prior_score=0.5,
        ).validate(),
    )
    return KnowledgeSnapshot(
        snapshot_id="kus3-test",
        source_split_identity_hash=_SHA_C,
        source_sample_ids=("train:u1",),
        builder_policy_id="saea-kb-distmodel-v1",
        facets=facets,
        values=values,
    ).validate()


def _write_vectors(path: Path, rows) -> str:
    import hashlib

    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        json.dumps({"id": entry_id, "vectors": vectors}) + "\n" for entry_id, vectors in rows
    )
    path.write_text(body, encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _specs(tmp_path, provider="kb-facet-v1"):
    program = rc.default_phase_program("phase-slots-given-intent-supplied-v1")
    query_sha = _write_vectors(
        tmp_path / "v" / "q.jsonl", [("dev:s1", {"content": [1.0, 0.0]})]
    )
    facet_sha = _write_vectors(
        tmp_path / "v" / "f.jsonl", [("facet:content:u1", {"content": [1.0, 0.0]})]
    )
    values = {
        "phase_supply": {
            "slots": {
                "provider": provider,
                "rank_policy": "saea-rank-wcos-prior-agree-v1",
                "fuse_policy": "saea-fuse-supplyfilter-v1",
                "k": 5,
                "tau": 0.0,
                "dimensions": ["content"],
                "rank_weights": {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0},
                "fuse_coverage": {"m": 5, "c": 5, "top_l": 5},
                "expose_facets": False,
                "query_source": {
                    "kind": ps.SEALED_VECTORS_KIND,
                    "relpath": "v/q.jsonl",
                    "sha256": query_sha,
                    "tool_contact_ledger_row": "TEST-EMB-KUS3",
                    "embedded_signal": "speech: the test's own synthetic speech vectors",
                },
                "facet_source": {
                    "kind": ps.SEALED_VECTORS_KIND,
                    "relpath": "v/f.jsonl",
                    "sha256": facet_sha,
                    "tool_contact_ledger_row": "TEST-EMB-KUS3",
                    "embedded_signal": "text: the test's own synthetic TRAIN key vectors",
                },
            }
        }
    }
    return program, ps.load_phase_supply_specs(values, program), values


def _resolve_stub(values, tmp_path, providers=None):
    return SimpleNamespace(
        _composed=SimpleNamespace(values=values),
        _data_root=tmp_path,
        _phase_supply_providers=providers,
        _phase_supply_receipt=None,
    )


def test_a_supplied_first_phase_needs_no_injected_provider_for_kb_facet_v1(tmp_path):
    """The repair. ``build_supply_for_phase`` CONSTRUCTS 'kb-facet-v1' from
    the frozen snapshot and publishes its factory, which is exactly what the
    pre-flight seed reads -- so refusing the first phase for it forced the
    launcher script the owner's engineering rules forbid."""

    program, _specs_map, values = _specs(tmp_path)
    snapshot = _snapshot()
    stub = _resolve_stub(values, tmp_path)
    supply_for_phase, resolved = FlightRuntime._resolve_phase_supply(
        stub, program, snapshot
    )
    assert set(resolved) == {"slots"}
    assert "slots" in supply_for_phase.provider_factories
    # A seeded phase never answers the runtime callable.
    assert supply_for_phase("slots", None) is None


def test_a_supplied_first_phase_with_another_provider_is_still_refused(tmp_path):
    program, _specs_map, values = _specs(tmp_path, provider="dense-centroid-v1")
    stub = _resolve_stub(values, tmp_path)
    with pytest.raises(FlightRuntimeError, match="bind_phase_supply_providers"):
        FlightRuntime._resolve_phase_supply(stub, program, _snapshot())


def test_the_seeded_selection_is_the_top_k_neighbours(tmp_path):
    program, specs_map, values = _specs(tmp_path)
    snapshot = _snapshot()
    stub = _resolve_stub(values, tmp_path)
    supply_for_phase, _resolved = FlightRuntime._resolve_phase_supply(
        stub, program, snapshot
    )
    provider = supply_for_phase.provider_factories["slots"]()
    facets, selected = ps.build_bootstrap_selection(
        specs_map["slots"],
        provider=provider,
        query_vectors_by_sample=supply_for_phase.query_tables["slots"],
        speech_packet_bindings={"dev:s1": {"packet_id": "speech/dev:s1", "sha256": _SHA_C}},
        split_identity_hash=_SHA_C,
    )
    assert selected == {"dev:s1": ("value:u1",)}
    assert facets == {}


def test_the_seed_uses_the_plan_driving_the_dispatch_not_self_plan(tmp_path):
    """The second repair. ``wire_check`` builds its own plan under its own
    run id and never sets ``self._plan``, so reading the attribute raised
    ``AttributeError: 'NoneType'`` and made the one cell shape that seeds a
    first phase impossible to wire-check."""

    program, specs_map, values = _specs(tmp_path)
    snapshot = _snapshot()
    stub = _resolve_stub(values, tmp_path)
    supply_for_phase, resolved = FlightRuntime._resolve_phase_supply(
        stub, program, snapshot
    )
    binding = {
        "supply_for_phase": supply_for_phase,
        "speech_packet_bindings": {
            "dev:s1": {"packet_id": "speech/dev:s1", "sha256": _SHA_C}
        },
    }
    seed_stub = SimpleNamespace(
        _plan=None, _composed=SimpleNamespace(values={}), _data_root=tmp_path
    )
    plan = SimpleNamespace(split_identity_hash=_SHA_C)
    facets, selected = FlightRuntime._phase_supply_seeds(
        seed_stub, program, binding, resolved, plan
    )
    assert selected == {"slots": {"dev:s1": ("value:u1",)}}
    assert facets == {}


def test_the_supplied_values_never_reach_a_control_turn(tmp_path):
    """Containment, on the shape this cell sends: the value text is a
    paragraph and can never be a substring of an instruction, while the key
    descriptor quotes its utterance rather than being it."""

    from speech_aware_evidence_acquisition.rails.runner import (
        _protected_knowledge_material,
    )

    snapshot = _snapshot()
    protected = _protected_knowledge_material(snapshot)
    instruction = (
        "Extract the entities of the spoken command carried in this request.\n\n"
        '{"scenario": "iot", "action": "hue_lightoff"}\n\n'
        "For intent iot_hue_lightoff TRAIN uses: device_type (lights off, lamp)."
    )
    assert all(payload not in instruction.casefold() for payload in protected)
    # and the bare utterance, which the exemplar view WOULD have protected,
    # is free to appear
    assert "lights off" in instruction.casefold()


def test_a_query_state_carrying_the_seed_renders_typed_value_blocks():
    from speech_aware_evidence_acquisition.rails.knowledge_provider import (
        _render_kb_supply_packet,
    )

    snapshot = _snapshot()
    state = QueryState(
        query_id="q1",
        query_sample_id="dev:s1",
        speech_packet_id="speech/dev:s1",
        speech_packet_sha256=_SHA_C,
        use_split_identity_hash=_SHA_C,
        retrieved_value_ids=("value:u1",),
    ).validate()
    packet = _render_kb_supply_packet(snapshot, state)
    assert packet.dose.n_items == 1
    assert packet.items[0].evidence_id == "value:u1"
    assert packet.items[0].text.startswith("Slot type=filler pairs observed")
    assert "-> intent" not in packet.items[0].text
