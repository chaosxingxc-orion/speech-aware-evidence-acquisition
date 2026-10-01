"""Evidence-consumption module, migration step 5: carrier hooks (owner decision 196; design 2b).

The SLURP hard-codings of the carrier-agnostic rails live behind SLURP's ``CarrierHooks``; SLURP
bytes are unchanged (the AT proofs, the relisten and P-SV suites, and the equivalence script), and a
second, fake carrier arms the SAME module through its own, different hooks. Model-free.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails import perception_presentations as pp  # noqa: E402
from speech_aware_evidence_acquisition.rails import runner  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_hooks as sh  # noqa: E402
from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (  # noqa: E402
    DEFAULT_MAX_SLURP_CANDIDATES,
)
from speech_aware_evidence_acquisition.rails.relisten import (  # noqa: E402
    RelistenConfig, parse_relisten, replay_relisten_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import parse_perception_branches  # noqa: E402

IDS = (
    "intent-boundaries::intent-boundary:shared-guidance",
    "intent-boundaries::intent-boundary:alarm_set",
    "train-exemplars::value:17",
    "intent-boundaries::intent-boundary:alarm_set",
    "intent-boundaries::intent-boundary:alarm_query",
    "intent-boundaries::intent-boundary:calendar_set",
)


# ---------------------------------------------------------------------------
# SLURP's hooks carry exactly what the rails used to spell.
# ---------------------------------------------------------------------------


def test_slurp_hooks_resolve_by_carrier_lock_key_and_others_have_none():
    hooks = cm.carrier_hooks_for_lock_key("slurp")
    assert hooks is not None and hooks.profile == "slurp"
    # 2026-09-30 (carrier transfer): Earnings-21 and Audio2Tool have hook files; a lock key
    # reaches its profile through core.base.CONSUMPTION_MODULE_PROFILES.
    assert cm.carrier_hooks_for_lock_key("earnings21-original").profile == "earnings"
    assert cm.carrier_hooks_for_lock_key("earnings22-original").profile == "earnings22"
    assert cm.carrier_hooks_for_lock_key(None) is None
    assert hooks.decision_candidates is sh.slurp_decision_candidates
    assert hooks.delivered_units is sh.slurp_delivered_units
    assert hooks.max_decision_candidates() == DEFAULT_MAX_SLURP_CANDIDATES == 3
    assert hooks.default_deliver_normaliser() == "saea-deliver-normalise-v3"


def test_decision_candidates_is_the_former_presentation_helper_byte_for_byte():
    assert sh.slurp_decision_candidates(IDS) == ("alarm_set", "alarm_query")
    assert pp.branch_supplied_intent_ids(IDS) == sh.slurp_decision_candidates(IDS)
    assert sh.slurp_decision_candidates(()) == ()


def test_delivered_units_is_parse_slu_response():
    text = json.dumps({"scenario": "alarm", "action": "set",
                       "entities": [{"type": "time", "filler": "six"}]})
    label, units, parsed = sh.slurp_delivered_units(text)
    assert parsed and label == "alarm_set" and [(u.type, u.filler) for u in units] == [("time", "six")]
    assert sh.slurp_delivered_units("not json") == (None, (), False)


def test_the_runner_uses_the_hooks_and_keeps_the_slurp_bytes_by_default():
    class _Branch:
        branch_id = "b"
        min_candidates = 3
        presentation_id = None

    default = runner._perception_branch_min_candidates_sentence(_Branch())
    hooked = runner._perception_branch_min_candidates_sentence(_Branch(), max_candidates=3)
    assert default == hooked and "at most 3 candidates" in default["text"]
    other = runner._perception_branch_min_candidates_sentence(_Branch(), max_candidates=5)
    assert "at most 5 candidates" in other["text"]


def test_the_loader_takes_the_min_candidates_ceiling_from_the_carrier():
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        _carrier_max_decision_candidates, _carrier_profile,
    )

    assert _carrier_max_decision_candidates({"carrier_lock_key": "slurp"}) == 3
    assert _carrier_profile({"carrier_lock_key": "slurp"}) == "slurp"
    assert _carrier_max_decision_candidates({"carrier_lock_key": "earnings21-original"}) == 0
    assert _carrier_profile({"carrier_lock_key": "earnings21-original"}) == "earnings"
    assert _carrier_max_decision_candidates({"carrier_lock_key": "audio2tool"}) == 4
    assert _carrier_max_decision_candidates({"carrier_lock_key": "earnings22-original"}) == 0
    assert _carrier_profile({"carrier_lock_key": "earnings22-original"}) == "earnings22"
    assert _carrier_profile({}) is None


def test_relisten_replay_takes_the_carriers_delivered_units():
    config = parse_relisten(copy.deepcopy(proof.component_entries()[cm.RELISTEN]["params"]))
    assert isinstance(config, RelistenConfig)
    calls = []

    def units(text):
        calls.append(text)
        return None, (), False

    receipt = replay_relisten_receipt(sample_id="s", delivered_text="x", contacts=[], config=config,
                                      delivered_units=units)
    default = replay_relisten_receipt(sample_id="s", delivered_text="x", contacts=[], config=config)
    assert calls == ["x"] and receipt == default


def test_the_module_file_still_names_no_carrier():
    text = (_REPO / "src/speech_aware_evidence_acquisition/rails/consumption_module.py").read_text(
        encoding="utf-8").lower()
    for token in ("slurp", "audio2tool", "a2t", "earnings", "intent-boundar", "conec"):
        assert token not in text, token


def test_the_slurp_equivalence_proofs_are_unchanged_by_the_migration():
    for at in ("m0", "m1", "m2", "extra", "m4"):
        assert proof.run_case(at)["ok"], at


# ---------------------------------------------------------------------------
# A second carrier arms the SAME module with different hooks.
# ---------------------------------------------------------------------------


def _fake_hooks() -> cm.CarrierHooks:
    slurp = sh.carrier_module_hooks()
    layer = copy.deepcopy(dict(slurp.lock_layer()))
    stores = layer["knowledge_stores"]
    stores["tool-shortlist"] = stores.pop("intent-boundaries")  # a different decision-node store
    layer["native_episode"]["deliver_normaliser"] = {"normaliser": "fake-deliver-v1"}
    return cm.CarrierHooks(
        profile="fakecarrier",
        lock_layer=lambda: layer,
        decision_supply_path=("knowledge_stores", "tool-shortlist", "phase_supply", "perception"),
        flown_programs={(11, None): "phase-native-candidates-review-revise-v1"},
        decision_candidates=lambda ids: tuple(i.rsplit(":", 1)[-1] for i in ids)[:2],
        max_decision_candidates=lambda: 5,
        delivered_units=lambda text: (None, (), False),
        default_deliver_normaliser=lambda: "fake-deliver-v1",
        deliver_stages={cm.SCOPE_RULE: {
            "compositions": {"fake-deliver-v1": "fake-deliver-v1-scope"},
            "params": {"min_pool_occurrences": 7, "untagged_share": 0.9,
                       "table": {"relpath": "prepared/FAKE/table.json", "sha256": "1" * 64}},
        }},
        perception_branch_frame={
            "block_path": ("native_episode", "roles", "perception", "branches"),
            "delivering_branch_id": "a-direct", "twin_branch_id": "t-copy",
            "max_supplied_items": 8,
            "fit_estimate": {"base_prompt_tokens": 1000, "completion_ceiling": 256,
                             "slot_tokens": 16384, "tokens_per_supplied_item": 100},
        },
        flown_branch_programs={},
        delivered_path_admissions={},
    )


def _fake_block() -> dict:
    block = proof.psv_column_block("configs/baseline/slurp-native-stage3-psv2-fold-b-baseline-v1.json")
    block["profile"] = "fakecarrier"
    block["components"] = [
        {**c, "params": {"min_candidates": 4, "max_supplied_items": 8}}
        if c["component_id"] == cm.FORCED_CANDIDATE_LIST else c
        for c in block["components"]
    ]
    scope = copy.deepcopy(proof.component_entries()[cm.SCOPE_RULE])
    scope["params"] = copy.deepcopy(_fake_hooks().deliver_stages[cm.SCOPE_RULE]["params"])
    block["components"] = [scope if c["component_id"] == cm.SCOPE_RULE else c for c in block["components"]]
    block["columns"][0]["column_id"] = "b-list4"
    return block


def test_a_second_carrier_arms_the_same_module_through_its_own_hooks():
    composed = cm.compile_module(_fake_block(), _fake_hooks())
    values = composed.values()
    assert composed.module_id == cm.CONSUMPTION_MODULE_ID and composed.profile == "fakecarrier"
    seed = values["knowledge_stores"]["tool-shortlist"]["phase_supply"]["perception"]
    assert seed["rank_weights"]["w_agree"] == 1.0 and "agreement_source" in seed
    assert "intent-boundaries" not in values["knowledge_stores"]
    assert values["native_episode"]["deliver_normaliser"]["normaliser"] == "fake-deliver-v1-scope"
    block = values["native_episode"]["roles"]["perception"]["branches"]
    assert [b["branch_id"] for b in block["branches"]] == ["b-list4", "t-copy", "a-direct"]
    group = parse_perception_branches(block, first_phase_id="perception", max_candidates_ceiling=5)
    assert group.branch("b-list4").min_candidates == 4
    # level 2, K = 3 over the lock's 11: ceiling 15, no flown branched program -> the family id
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c15", 15)
    receipt = cm.module_header_receipt(composed)
    assert cm.validate_module_header_receipt(receipt)["profile"] == "fakecarrier"


def test_the_same_block_is_refused_where_the_carrier_pins_differ():
    block = _fake_block()
    block["profile"] = "slurp"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="registered stage's pins"):
        cm.compile_module(block, sh.carrier_module_hooks())
    with pytest.raises(cm.ConsumptionModuleConfigError, match="default deliver normaliser"):
        fake = _fake_hooks()
        cm.compile_module(_fake_block(), cm.CarrierHooks(**{
            **{f: getattr(fake, f) for f in cm.CarrierHooks.__dataclass_fields__},
            "default_deliver_normaliser": lambda: "another-v1",
        }))
