from __future__ import annotations

import hashlib
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.controllers import (
    HARD_VALIDITY_PROGRAM_ID,
    EvidenceAgentController,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g3_plain_english_flight import (
    G3_MATCHED_USE_PHASE,
    G3_M0_DIRECT_PHASE,
    G3_OBSERVATION_PHASE,
    G3_SHUFFLED_USE_PHASE,
    G3PilotAdapter,
    G3PilotFlightError,
    build_complete_arm_texts,
    build_packet_routes,
    emit_g3_use_rows,
    resolve_g3_runtime_media,
    run_g3_agent_phase,
    run_g3_m0_phase,
    select_shuffled_control_ids,
)


TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _runtime_fixture(tmp_path: Path):
    roster_items = []
    media_items = []
    bindings = {}
    for tier_index, tier in enumerate(TIERS):
        for offset in range(5):
            sample_id = f"{tier}:{tier_index * 10 + offset:06d}"
            original_relpath = f"datasets/audio2tool/{sample_id}.wav"
            runtime_relpath = (
                f"derived/g3/{sample_id}.wav"
                if tier == "tier7_multiturn"
                else original_relpath
            )
            payload = f"speech:{sample_id}".encode()
            path = tmp_path / runtime_relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            roster_items.append(
                {
                    "audio_sha256": _sha(payload) if tier != "tier7_multiturn" else "0" * 64,
                    "media_relpath": original_relpath,
                    "packet_id": sample_id.replace(":", "/"),
                    "sample_id": sample_id,
                    "tier": tier,
                }
            )
            media_item = {
                "audio_seconds": 1.5,
                "audio_sha256": _sha(payload),
                "media_relpath": runtime_relpath,
                "sample_id": sample_id,
                "tier": tier,
            }
            if tier == "tier7_multiturn":
                media_item["source_final_turn_media_relpath"] = original_relpath
            media_items.append(media_item)
            bindings[sample_id] = {
                "packet_id": (
                    f"g3_complete_dialogue/{tier}/{tier_index * 10 + offset:06d}"
                    if tier == "tier7_multiturn"
                    else sample_id.replace(":", "/")
                ),
                "sha256": _sha(f"packet:{sample_id}".encode()),
            }
    roster = {"count": 40, "items": roster_items, "split_name": "A2T-G3-PILOT-40"}
    media = {
        "count": 40,
        "items": media_items,
        "tier7_complete_dialogue_count": 5,
    }
    return roster, media, {"count": 40, "bindings": bindings}


def _summary(sample_ids, prefix: str, contacts: int = 1):
    return SimpleNamespace(
        agent_executor_id="openjiuwen-workflow-v1",
        results=tuple(
            SimpleNamespace(
                sample_id=sample_id,
                final_response_text=f"{prefix}:{sample_id}",
                contacts=tuple(object() for _ in range(contacts)),
            )
            for sample_id in sample_ids
        ),
    )


def test_runtime_media_resolves_exact_40_and_five_derived_dialogue_identities(
    tmp_path: Path,
) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)

    surface = resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)

    assert len(surface.samples) == len(surface.packet_bindings) == 40
    assert set(surface.tier_by_sample.values()) == set(TIERS)
    derived = [
        sample
        for sample in surface.samples
        if surface.tier_by_sample[sample.sample_id] == "tier7_multiturn"
    ]
    assert len(derived) == 5
    assert all(sample.media_relpath.startswith("derived/g3/") for sample in derived)
    assert all(
        surface.packet_bindings[sample.sample_id]["packet_id"].startswith(
            "g3_complete_dialogue/"
        )
        for sample in derived
    )
    assert {
        sample_id: media_identity
        for sample_id, media_identity in surface.media_identity_by_sample.items()
        if sample_id != media_identity
    } == {
        f"tier7_multiturn:{60 + offset:06d}": f"a2t-g3-dialogue:{60 + offset:06d}"
        for offset in range(5)
    }
    assert sum(
        sample_id == media_identity
        for sample_id, media_identity in surface.media_identity_by_sample.items()
    ) == 35


def test_runtime_media_rejects_byte_or_identity_drift(tmp_path: Path) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)
    media["items"][0]["audio_sha256"] = "f" * 64

    with pytest.raises(G3PilotFlightError, match="audio SHA-256"):
        resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)


def test_runtime_media_fails_closed_on_malformed_identity_surfaces(tmp_path: Path) -> None:
    base = _runtime_fixture(tmp_path)

    def refuses(mutate) -> None:
        roster, media, bindings = copy.deepcopy(base)
        mutate(roster, media, bindings)
        with pytest.raises(G3PilotFlightError):
            resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)

    mutations = (
        lambda roster, _media, _bindings: roster.clear(),
        lambda roster, _media, _bindings: roster.update(count=39),
        lambda roster, _media, _bindings: roster["items"].__setitem__(0, None),
        lambda _roster, media, _bindings: media["items"][0].update(audio_sha256="bad"),
        lambda roster, _media, _bindings: roster["items"][1].update(
            sample_id=roster["items"][0]["sample_id"]
        ),
        lambda _roster, media, _bindings: media["items"][0].update(
            media_relpath=str((tmp_path / "absolute.wav").resolve())
        ),
        lambda _roster, media, _bindings: media["items"][0].update(
            media_relpath="missing.wav"
        ),
        lambda _roster, _media, bindings: bindings.update(count=39),
        lambda _roster, _media, bindings: bindings["bindings"].pop(
            next(iter(bindings["bindings"]))
        ),
        lambda _roster, media, _bindings: media.update(
            tier7_complete_dialogue_count=4
        ),
        lambda _roster, media, _bindings: media["items"][0].update(tier="wrong"),
        lambda _roster, media, _bindings: media["items"][0].update(audio_seconds=0),
        lambda _roster, media, _bindings: next(
            item for item in media["items"] if item["tier"] == "tier7_multiturn"
        ).update(source_final_turn_media_relpath="wrong.wav"),
        lambda _roster, _media, bindings: bindings["bindings"].__setitem__(
            next(iter(bindings["bindings"])), None
        ),
        lambda _roster, _media, bindings: next(
            value
            for sample_id, value in bindings["bindings"].items()
            if sample_id.startswith("tier7_multiturn:")
        ).update(packet_id="wrong/dialogue"),
    )
    for mutate in mutations:
        refuses(mutate)


def test_identity_only_shuffled_subset_is_fixed_at_two_per_tier(tmp_path: Path) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)
    surface = resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)

    selected = select_shuffled_control_ids(surface.tier_by_sample)
    reordered = select_shuffled_control_ids(dict(reversed(tuple(surface.tier_by_sample.items()))))

    assert selected == reordered
    assert len(selected) == 16
    assert {
        tier: sum(surface.tier_by_sample[sample_id] == tier for sample_id in selected)
        for tier in TIERS
    } == {tier: 2 for tier in TIERS}


def test_observation_routes_use_bounded_text_without_a_tier_hint() -> None:
    sample_ids = ("tier1_direct:000001", "tier3_multi_intent:000002")
    observations = _summary(sample_ids, "turn on lights and play music")
    calls = []

    def retrieve(text, corpus, **kwargs):
        calls.append((text, corpus, kwargs))
        return SimpleNamespace(
            matched_packet=f"matched {text}", shuffled_packet=f"shuffled {text}"
        )

    routes = build_packet_routes(
        observations,
        corpus=object(),
        retriever=retrieve,
        detailed_tool_limit=32,
    )

    assert set(routes) == set(sample_ids)
    assert all(call[2]["detailed_tool_limit"] == 32 for call in calls)
    assert all("tier_hint" not in call[2] for call in calls)


def test_role_labeled_dialogue_observation_is_retrieved_without_a_tier_hint() -> None:
    sample_id = "tier7_multiturn:000318"
    observations = SimpleNamespace(
        results=(
            SimpleNamespace(
                sample_id=sample_id,
                final_response_text=(
                    "User: turn on the light\nAssistant: done\nUser: also play music"
                ),
            ),
        )
    )
    calls = []

    def retrieve(text, corpus, **kwargs):
        calls.append((text, kwargs))
        return SimpleNamespace(matched_packet="matched", shuffled_packet="shuffled")

    routes = build_packet_routes(
        observations,
        corpus=object(),
        dialogue_sample_ids=(sample_id,),
        retriever=retrieve,
    )

    assert set(routes) == {sample_id}
    assert calls[0][0].startswith("User:")
    assert "tier_hint" not in calls[0][1]


def test_flat_dialogue_observation_is_ascii_normalized_and_reported() -> None:
    sample_id = "tier7_multiturn:001590"
    observations = SimpleNamespace(
        results=(
            SimpleNamespace(
                sample_id=sample_id,
                final_response_text="Set it to 72\N{DEGREE SIGN}\N{EM DASH}don\N{RIGHT SINGLE QUOTATION MARK}t stop.",
            ),
        )
    )
    calls = []
    representation_flags = {}

    def retrieve(text, corpus, **kwargs):
        calls.append((text, kwargs))
        return SimpleNamespace(matched_packet="matched", shuffled_packet="shuffled")

    routes = build_packet_routes(
        observations,
        corpus=object(),
        dialogue_sample_ids=(sample_id,),
        representation_flags=representation_flags,
        retriever=retrieve,
    )

    assert set(routes) == {sample_id}
    assert calls[0][0] == "Set it to 72 degrees - don't stop."
    assert calls[0][0].isascii()
    assert representation_flags == {
        sample_id: {
            "role_labels_missing": True,
            "normalized_non_ascii": True,
        }
    }


def test_adapter_keeps_observation_task_blind_and_use_packet_sample_local(
    tmp_path: Path,
) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)
    surface = resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)
    sample = surface.samples[0]

    obs_adapter = G3PilotAdapter(surface.samples, phase=G3_OBSERVATION_PHASE)
    obs_contract = obs_adapter.build_task_contract(sample, object())
    assert "Transcribe the English speech verbatim" in obs_contract
    assert "Available tools" not in obs_contract
    assert "exactToolName" not in obs_contract
    assert sample.sample_id not in obs_contract

    dialogue_sample = next(
        item
        for item in surface.samples
        if surface.tier_by_sample[item.sample_id] == "tier7_multiturn"
    )
    dialogue_adapter = G3PilotAdapter(
        surface.samples,
        phase=G3_OBSERVATION_PHASE,
        dialogue_sample_ids=surface.derived_dialogue_sample_ids,
    )
    dialogue_contract = dialogue_adapter.build_task_contract(dialogue_sample, object())
    assert "alternating user and assistant" in dialogue_contract
    assert "explicit role labels" in dialogue_contract

    use_adapter = G3PilotAdapter(
        surface.samples,
        phase=G3_MATCHED_USE_PHASE,
        observation_by_sample={item.sample_id: f"observation {item.sample_id}" for item in surface.samples},
        packet_by_sample={item.sample_id: f"packet {item.sample_id}" for item in surface.samples},
    )
    contract = use_adapter.build_task_contract(sample, object())
    prompt = use_adapter.assemble_prompt(sample, None)
    assert f"observation {sample.sample_id}" in contract
    assert f"packet {sample.sample_id}" in contract
    assert prompt[1]["content"][0]["media_relpath"] == sample.media_relpath
    assert use_adapter.score(sample, "[]") == {"scoring_deferred": True}
    assert use_adapter.extract_consumption(sample, None, "[]").records == ()


def test_adapter_rejects_phase_surface_leakage_and_wrong_split(tmp_path: Path) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)
    surface = resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)
    sample = surface.samples[0]

    with pytest.raises(G3PilotFlightError, match="unknown G3 phase"):
        G3PilotAdapter(surface.samples, phase="unknown")
    with pytest.raises(G3PilotFlightError, match="nonempty and unique"):
        G3PilotAdapter((), phase=G3_OBSERVATION_PHASE)
    with pytest.raises(G3PilotFlightError, match="legacy registry"):
        G3PilotAdapter(surface.samples, phase=G3_M0_DIRECT_PHASE)
    with pytest.raises(G3PilotFlightError, match="M0 cannot"):
        G3PilotAdapter(
            surface.samples,
            phase=G3_M0_DIRECT_PHASE,
            registry_contract="registry",
            observation_by_sample={sample.sample_id: "leak"},
        )
    with pytest.raises(G3PilotFlightError, match="task blind"):
        G3PilotAdapter(
            surface.samples,
            phase=G3_OBSERVATION_PHASE,
            registry_contract="registry",
        )
    with pytest.raises(G3PilotFlightError, match="one observation"):
        G3PilotAdapter(surface.samples, phase=G3_MATCHED_USE_PHASE)
    with pytest.raises(G3PilotFlightError, match="outside the phase"):
        G3PilotAdapter(
            surface.samples,
            phase=G3_OBSERVATION_PHASE,
            dialogue_sample_ids=("unknown",),
        )
    adapter = G3PilotAdapter(surface.samples, phase=G3_OBSERVATION_PHASE)
    with pytest.raises(G3PilotFlightError, match="serves only"):
        adapter.load_split("wrong")
    with pytest.raises(G3PilotFlightError, match="second supply"):
        adapter.assemble_prompt(sample, object())


def test_m0_and_agent_phases_bind_fresh_openjiuwen_calls_and_contact_caps(
    tmp_path: Path,
) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)
    surface = resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)
    sample_ids = tuple(sample.sample_id for sample in surface.samples)
    adapter = G3PilotAdapter(
        surface.samples,
        phase=G3_MATCHED_USE_PHASE,
        observation_by_sample={sample_id: "turn on the light" for sample_id in sample_ids},
        packet_by_sample={sample_id: "plain English card packet" for sample_id in sample_ids},
    )
    direct_calls = []

    def direct_runner(**kwargs):
        direct_calls.append(kwargs)
        return _summary(sample_ids, "m0")

    m0 = run_g3_m0_phase(
        adapter=G3PilotAdapter(
            surface.samples,
            phase=G3_M0_DIRECT_PHASE,
            registry_contract="English registry contract",
        ),
        core_client=object(),
        speech_packet_bindings=surface.packet_bindings,
        slot_count=4,
        decoding_params={},
        direct_runner=direct_runner,
    )
    assert len(m0.results) == 40
    assert direct_calls[0]["split_id"] == "A2T-G3-PILOT-40"

    agent_calls = []

    def agent_runner(**kwargs):
        agent_calls.append(kwargs)
        controller = kwargs["controller_registry"].resolve(kwargs["controller_policy_id"])(
            sample_ids[0]
        )
        assert isinstance(controller, EvidenceAgentController)
        assert controller.program.program_id == HARD_VALIDITY_PROGRAM_ID
        return _summary(sample_ids, "use", contacts=2)

    summary = run_g3_agent_phase(
        phase=G3_MATCHED_USE_PHASE,
        data_root=tmp_path,
        plan=object(),
        adapter=adapter,
        core_client=object(),
        knowledge_snapshot=object(),
        speech_packet_bindings=surface.packet_bindings,
        trace_sink=object(),
        slot_count=4,
        queue_depth=8,
        decoding_params={},
        registry_rows=({"tool_name": "setLight", "signature": "setLight()"},),
        agent_runner=agent_runner,
    )
    assert len(summary.results) == 40
    assert agent_calls[0]["agent_executor_id"] == "openjiuwen-workflow-v1"
    assert agent_calls[0]["max_contacts"] == 2
    assert agent_calls[0]["controller_policy_id"] == HARD_VALIDITY_PROGRAM_ID
    assert agent_calls[0]["bootstrap_facet_ids"] == ()
    assert agent_calls[0]["bootstrap_value_ids"] == ()


def test_observation_phase_uses_256_or_768_tokens_from_media_identity(
    tmp_path: Path,
) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)
    surface = resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)
    sample_ids = tuple(sample.sample_id for sample in surface.samples)
    adapter = G3PilotAdapter(
        surface.samples,
        phase=G3_OBSERVATION_PHASE,
        dialogue_sample_ids=surface.derived_dialogue_sample_ids,
    )

    def agent_runner(**kwargs):
        factory = kwargs["controller_registry"].resolve(kwargs["controller_policy_id"])
        ordinary_id = next(
            sample_id
            for sample_id in sample_ids
            if sample_id not in surface.derived_dialogue_sample_ids
        )
        dialogue_id = surface.derived_dialogue_sample_ids[0]
        context = SimpleNamespace(
            query_state=SimpleNamespace(loop_step=0, content_hash=lambda: "a" * 64)
        )
        ordinary = factory(ordinary_id).initial_contact(context)
        dialogue = factory(dialogue_id).initial_contact(context)
        assert ordinary.decoding_params["max_tokens"] == 256
        assert dialogue.decoding_params["max_tokens"] == 768
        assert "alternating user and assistant" in dialogue.instruction
        return _summary(sample_ids, "observation")

    summary = run_g3_agent_phase(
        phase=G3_OBSERVATION_PHASE,
        data_root=tmp_path,
        plan=object(),
        adapter=adapter,
        core_client=object(),
        knowledge_snapshot=object(),
        speech_packet_bindings=surface.packet_bindings,
        trace_sink=object(),
        slot_count=4,
        queue_depth=8,
        decoding_params={},
        agent_runner=agent_runner,
    )

    assert len(summary.results) == 40


def test_shuffled_phase_is_only_16_and_composites_stay_scorer_compatible(
    tmp_path: Path,
) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)
    surface = resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)
    sample_ids = tuple(sample.sample_id for sample in surface.samples)
    shuffled_ids = select_shuffled_control_ids(surface.tier_by_sample)
    m0 = _summary(sample_ids, "m0")
    matched = _summary(sample_ids, "matched")
    shuffled = _summary(shuffled_ids, "shuffled")

    arms = build_complete_arm_texts(
        m0_summary=m0,
        matched_summary=matched,
        shuffled_summary=shuffled,
        shuffled_ids=shuffled_ids,
    )

    assert len(arms.m0) == len(arms.matched) == len(arms.shuffled) == 40
    assert all(arms.shuffled[sample_id].startswith("shuffled:") for sample_id in shuffled_ids)
    assert all(
        arms.shuffled[sample_id] == arms.matched[sample_id]
        for sample_id in set(sample_ids) - set(shuffled_ids)
    )
    assert set(vars(matched.results[0])) >= {
        "sample_id",
        "final_response_text",
        "contacts",
    }


def test_shuffled_use_runner_accepts_only_the_fixed_16_row_subset(tmp_path: Path) -> None:
    roster, media, bindings = _runtime_fixture(tmp_path)
    surface = resolve_g3_runtime_media(roster, media, bindings, data_root=tmp_path)
    selected = select_shuffled_control_ids(surface.tier_by_sample)
    selected_samples = tuple(
        sample for sample in surface.samples if sample.sample_id in set(selected)
    )
    selected_bindings = {
        sample_id: surface.packet_bindings[sample_id] for sample_id in selected
    }
    adapter = G3PilotAdapter(
        selected_samples,
        phase=G3_SHUFFLED_USE_PHASE,
        observation_by_sample={sample_id: "turn on the light" for sample_id in selected},
        packet_by_sample={sample_id: "shuffled English cards" for sample_id in selected},
    )

    summary = run_g3_agent_phase(
        phase=G3_SHUFFLED_USE_PHASE,
        data_root=tmp_path,
        plan=object(),
        adapter=adapter,
        core_client=object(),
        knowledge_snapshot=object(),
        speech_packet_bindings=selected_bindings,
        trace_sink=object(),
        slot_count=4,
        queue_depth=8,
        decoding_params={},
        registry_rows=({"tool_name": "setLight", "signature": "setLight()"},),
        agent_runner=lambda **_kwargs: _summary(selected, "shuffled", contacts=1),
    )

    assert len(summary.results) == 16


def test_use_composites_delegate_to_existing_scorer_row_shape() -> None:
    calls = []

    def emitter(**kwargs):
        calls.append(kwargs)
        return (
            {
                "request_id": "composite-1",
                "sample_id": "tier1_direct:000001",
                "carrier_lock_key": "audio2tool",
                "arm": "speech-feature-query",
                "text": "[]",
                "admitted": True,
            },
        )

    rows = emit_g3_use_rows(
        texts={"tier1_direct:000001": "[]"},
        source_by_id={"tier1_direct:000001": {"phase": "matched"}},
        sink=object(),
        phase=G3_MATCHED_USE_PHASE,
        emitter=emitter,
    )

    assert calls[0]["variant"] == "matched"
    assert set(rows[0]) >= {
        "request_id",
        "sample_id",
        "carrier_lock_key",
        "arm",
        "text",
        "admitted",
    }
