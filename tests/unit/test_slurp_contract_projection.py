from __future__ import annotations

from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.base import INSTRUCTION_FILLS
from speech_aware_evidence_acquisition.core.flight.runtime import phase_program_system_text
from speech_aware_evidence_acquisition.core.instructions import resolve_task_instruction
from speech_aware_evidence_acquisition.data.lock import REPO_ROOT, load_lock
from speech_aware_evidence_acquisition.data.slurp import (
    load_slurp_ontology,
    render_slurp_label_inventory,
)
from speech_aware_evidence_acquisition.data.slurp_contract_cache import (
    SLURP_LABEL_INVENTORY_FILL,
    SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY,
    load_cached_slurp_label_inventory,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import _INSTRUCTION, SlurpSample
from speech_aware_evidence_acquisition.rails.adapters.runtime_view import RuntimeViewError
from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime import (
    RuntimeSlurpAdapter,
    build_runtime_adapter,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.runner import _agent_messages
from speech_aware_evidence_acquisition.rails.tool_wrappers.phase_knowledge import (
    read_task_contract,
)


FILL_NAME = SLURP_LABEL_INVENTORY_FILL
TEMPLATE_RELPATH = "probes/slurp_direct_closed_list.txt"


def _sample() -> SlurpSample:
    return SlurpSample(
        sample_id="slurp:devel:one:audio",
        audio_ref=AudioRef(path="one.wav", sha256="a" * 64),
        audio_seconds=1.0,
        utterance_id="one",
        media_relpath="one.wav",
        scenario="",
        action="",
        intent="",
        entities=(),
    )


def test_registered_projection_fill_is_the_complete_no_filler_inventory(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    rendered = load_cached_slurp_label_inventory(lock, slurp_world.data_root)

    assert FILL_NAME in INSTRUCTION_FILLS.names()
    assert INSTRUCTION_FILLS.resolve(FILL_NAME) is load_cached_slurp_label_inventory
    assert rendered == render_slurp_label_inventory(ontology)
    for scenario, actions in ontology.actions_by_scenario.items():
        assert f"{scenario}: {', '.join(actions)}" in rendered
    for entity_type, fillers in ontology.entity_types.items():
        assert entity_type in rendered
        assert all(filler not in rendered for filler in fillers)




def test_runtime_adapter_default_keeps_the_legacy_contract_bytes(slurp_world):
    from speech_aware_evidence_acquisition.data.slurp_contract_cache import (
        load_cached_slurp_contract,
    )

    lock = load_lock(slurp_world.lock_path)
    sample = _sample()
    adapter = RuntimeSlurpAdapter(
        lock,
        slurp_world.data_root,
        repo_root=REPO_ROOT,
        split_id="devel",
        samples=(sample,),
        instruction_text=_INSTRUCTION,
    )

    assert adapter.build_task_contract(sample, None) == load_cached_slurp_contract(
        lock, slurp_world.data_root
    )


def test_projection_fill_and_runtime_contract_render_identical_bytes(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    instruction = resolve_task_instruction(
        {
            "task_instruction_template": TEMPLATE_RELPATH,
            "task_instruction_fill": FILL_NAME,
        },
        REPO_ROOT,
        lock,
        slurp_world.data_root,
    )
    adapter = RuntimeSlurpAdapter(
        lock,
        slurp_world.data_root,
        repo_root=REPO_ROOT,
        split_id="devel",
        samples=(_sample(),),
        instruction_text=instruction,
        task_contract_view=SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY,
    )
    contract = adapter.build_task_contract(_sample(), None)

    assert instruction == f"{_INSTRUCTION}\n\nTask contract:\n{contract}"


def test_projection_is_shared_by_request_tool_and_fit_paths(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    contract = load_cached_slurp_label_inventory(lock, slurp_world.data_root)
    instruction = resolve_task_instruction(
        {
            "task_instruction_template": TEMPLATE_RELPATH,
            "task_instruction_fill": FILL_NAME,
        },
        REPO_ROOT,
        lock,
        slurp_world.data_root,
    )
    sample = _sample()
    adapter = RuntimeSlurpAdapter(
        lock,
        slurp_world.data_root,
        repo_root=REPO_ROOT,
        split_id="devel",
        samples=(sample,),
        instruction_text=instruction,
        task_contract_view=SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY,
    )
    query = QueryState(
        query_id="query",
        query_sample_id=sample.sample_id,
        speech_packet_id="packet",
        speech_packet_sha256="b" * 64,
        use_split_identity_hash="c" * 64,
    )
    messages = _agent_messages(
        adapter=adapter,
        sample=sample,
        task_contract=adapter.build_task_contract(sample, None),
        snapshot=SimpleNamespace(facets=(), values=()),
        snapshot_sha256="d" * 64,
        query_state=query,
    )
    tool = read_task_contract(SimpleNamespace(task_contract=contract))

    assert messages[0]["content"] == instruction
    assert phase_program_system_text(adapter, sample) == instruction
    assert tool.result == {"task_contract": contract}
    assert "jazz" not in instruction


def test_projection_refuses_instruction_that_does_not_contain_its_contract(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    with pytest.raises(RuntimeViewError, match="must contain.*label inventory"):
        RuntimeSlurpAdapter(
            lock,
            slurp_world.data_root,
            repo_root=REPO_ROOT,
            split_id="devel",
            samples=(_sample(),),
            instruction_text=_INSTRUCTION,
            task_contract_view=SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY,
        )


def test_unknown_projection_refuses_before_instruction_or_roster_loading(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("runtime loading must not begin for an unknown view")

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.adapters.slurp_runtime."
        "resolve_active_task_instruction",
        forbidden,
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.adapters.slurp_runtime.roster_samples",
        forbidden,
    )
    with pytest.raises(RuntimeViewError, match="unsupported.*view"):
        build_runtime_adapter(
            {"slurp_task_contract_view": "invented-view"},
            {},
            REPO_ROOT,
            REPO_ROOT,
            dataset_fragment="unused",
        )


@pytest.mark.parametrize(
    "values",
    [
        {
            "slurp_task_contract_view": SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY,
            "task_instruction_fill": "slurp-label-inventory",
            "task_instruction_template_active": True,
        },
        {
            "task_instruction_fill": FILL_NAME,
            "task_instruction_template_active": True,
        },
    ],
)
def test_mismatched_projection_fill_and_view_refuse_before_roster_loading(
    values, monkeypatch
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("mismatched projection must fail before runtime loading")

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.adapters.slurp_runtime."
        "resolve_active_task_instruction",
        forbidden,
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.adapters.slurp_runtime.roster_samples",
        forbidden,
    )
    with pytest.raises(RuntimeViewError, match="must be selected together"):
        build_runtime_adapter(
            values, {}, REPO_ROOT, REPO_ROOT, dataset_fragment="unused"
        )


def test_projected_view_refuses_literal_instruction_source_before_roster_loading(
    monkeypatch,
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("literal projection must fail before runtime loading")

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.adapters.slurp_runtime."
        "resolve_active_task_instruction",
        forbidden,
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.adapters.slurp_runtime.roster_samples",
        forbidden,
    )
    values = {
        "slurp_task_contract_view": SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY,
        "task_instruction_fill": FILL_NAME,
        "task_instruction_template_active": True,
        "task_instruction": "arbitrary literal containing an inventory substring",
    }
    with pytest.raises(RuntimeViewError, match="active registered.*no literal"):
        build_runtime_adapter(
            values, {}, REPO_ROOT, REPO_ROOT, dataset_fragment="unused"
        )


