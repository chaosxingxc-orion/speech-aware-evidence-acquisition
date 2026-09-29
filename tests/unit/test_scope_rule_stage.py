"""Evidence-consumption module, migration step 3: the do-not-tag scope-rule deliver stage.

Owner decision 195 = B; design docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md
sections 2.2 (d), 2.5 and 4 (step 3); coordinator ruling R5. Model-free: the table here is a fake
pool's, and the data root is never read.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis", _REPO / "scripts" / "checks"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import fold  # noqa: E402
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    DELIVERY_NORMALISERS, DeliveryNormaliserError,
)
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails import controllers as rc  # noqa: E402
from speech_aware_evidence_acquisition.rails import delivery_normalisers as dn  # noqa: E402
from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (  # noqa: E402
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.solver_citation import (  # noqa: E402
    CITED_ANSWER_NORMALISER_IDS,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    legal_intent_inventory, parse_slu_response,
)


def _load(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HR = _load(_REPO / "scripts/analysis/slurp_slu_consumption_headroom.py", "slurp_slu_consumption_headroom")
TB = _load(_REPO / "scripts/build_slurp_scope_rule_table.py", "build_slurp_scope_rule_table")

INVENTORY = legal_intent_inventory({"alarm": ("set", "query"), "calendar": ("set", "query")})


def _ex(utterance: str, *fillers: str) -> tuple[list[str], list[list[str]]]:
    return fold(utterance).split(), [fold(f).split() for f in fillers]


#: A fake pool. "tomorrow": 6 exemplars, tagged in 1 (untagged 0.833 -> dropped); "the morning":
#: 5 exemplars, tagged in 2 (untagged 0.6 -> kept); "jazz": 4 exemplars (below the floor -> kept);
#: "wake me up": 5 exemplars, never tagged (dropped).
FAKE_POOL = [
    _ex("set an alarm for tomorrow", "tomorrow"),
    _ex("what is on tomorrow"), _ex("tomorrow is fine"), _ex("remind me tomorrow"),
    _ex("tomorrow please"), _ex("is it cold tomorrow"),
    _ex("the morning news", "the morning"), _ex("in the morning", "the morning"),
    _ex("the morning show"), _ex("all the morning"), _ex("the morning after"),
    _ex("play jazz"), _ex("jazz now"), _ex("some jazz"), _ex("more jazz"),
    _ex("wake me up at six"), _ex("please wake me up"), _ex("wake me up now"),
    _ex("do not wake me up"), _ex("wake me up later"),
]


def _fake_table() -> dn.ScopeRuleTable:
    rows = TB.table_rows(FAKE_POOL)
    document = {"schema": dn.SCOPE_RULE_TABLE_SCHEMA, "min_pool_occurrences_floor": TB.MIN_POOL_OCCURRENCES_FLOOR,
                "rows": dict(sorted(rows.items()))}
    return dn.ScopeRuleTable.from_bytes(TB.table_bytes(document), expected_sha256=None)


@pytest.fixture(autouse=True)
def _no_data_root(monkeypatch):
    table = _fake_table()
    monkeypatch.setattr(dn, "_DEFAULT_SCOPE_RULE_TABLE", [table])
    monkeypatch.setattr(v3, "_default_legal_intent_inventory", lambda: INVENTORY)


def _answer(entities, scenario="alarm", action="set") -> str:
    return json.dumps({"scenario": scenario, "action": action,
                       "entities": [{"type": t, "filler": f} for t, f in entities]},
                      ensure_ascii=False, sort_keys=True)


ROWS = {
    "r1": [("date", "tomorrow"), ("timeofday", "the morning")],
    "r2": [("music_genre", "jazz")],
    "r3": [("event_name", "Wake me up!"), ("date", "Tomorrow")],
    "r4": [],
    "r5": [("time", "six")],
}


def _offline(entities) -> set[int]:
    occ, tagged = HR.scope_counts(FAKE_POOL)
    out = set()
    for index, (_type, filler) in enumerate(entities):
        n, u = HR.untagged_share(tuple(fold(filler).split()), occ, tagged)
        if n >= HR.SCOPE_MIN_OCC and u is not None and u >= 0.8:
            out.add(index)
    return out


# ---------------------------------------------------------------------------
# The stage reproduces the offline rule's row set exactly.
# ---------------------------------------------------------------------------


def test_the_stage_reproduces_the_offline_rules_row_set_exactly():
    stage = DELIVERY_NORMALISERS.resolve(dn.DELIVER_SCOPE_RULE_V1)
    offline, staged = {}, {}
    for sid, entities in ROWS.items():
        if hits := _offline(entities):
            offline[sid] = hits
        result = stage(_answer(entities))
        if dropped := set(result.receipt["dropped_entity_indices"]):
            staged[sid] = dropped
            _s, _a, kept, parsed = parse_slu_response(result.text)
            assert parsed and [(e.type, e.filler) for e in kept] == [
                pair for i, pair in enumerate(entities) if i not in dropped
            ]
    assert offline == staged == {"r1": {0}, "r3": {0, 1}}


def test_the_table_carries_the_offline_counts_and_floor():
    table = _fake_table()
    assert table.rows["tomorrow"] == (6, 1)
    assert table.rows["the morning"] == (5, 2)
    assert "jazz" not in table.rows  # below the occurrence floor
    assert table.rows["wake me up"] == (5, 0)


def test_a_row_the_rule_leaves_alone_is_delivered_verbatim():
    text = '{"action":"set","entities":[{"type":"music_genre","filler":"jazz"}],"scenario":"alarm"}'
    result = DELIVERY_NORMALISERS.resolve(dn.DELIVER_SCOPE_RULE_V1)(text)
    assert result.text == text and not result.changed
    assert result.receipt["dropped_entity_indices"] == [] and result.receipt["applied"] is True


def test_an_unparsed_answer_is_delivered_verbatim_with_a_reason():
    result = DELIVERY_NORMALISERS.resolve(dn.DELIVER_SCOPE_RULE_V1)("not json")
    assert result.text == "not json" and not result.changed
    assert result.receipt["applied"] is False and result.receipt["reason"] == "unparsed"
    dn.validate_scope_rule_receipt(dict(result.receipt))


# ---------------------------------------------------------------------------
# Receipt validation.
# ---------------------------------------------------------------------------


def test_the_sub_receipt_binds_the_table_and_thresholds_and_no_text():
    text = _answer(ROWS["r1"])
    receipt = dict(DELIVERY_NORMALISERS.resolve(dn.DELIVER_SCOPE_RULE_V1)(text).receipt)
    assert dn.validate_scope_rule_receipt(receipt) is receipt
    assert receipt["table_sha256"] == _fake_table().sha256
    assert receipt["min_pool_occurrences"] == 5 and receipt["untagged_share"] == 0.8
    assert receipt["input_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert "tomorrow" not in json.dumps(receipt)
    for mutate, message in (
        (lambda r: r.update(extra=1), "carries exactly"),
        (lambda r: r.update(untagged_share=0.5), "untagged_share"),
        (lambda r: r.update(table_sha256="x"), "64-hex"),
        (lambda r: r.update(dropped_entity_indices=[1, 0]), "sorted"),
        (lambda r: r.update(changed=False), "changed must hold"),
    ):
        broken = copy.deepcopy(receipt)
        mutate(broken)
        with pytest.raises(DeliveryNormaliserError, match=message):
            dn.validate_scope_rule_receipt(broken)


def test_a_table_that_is_not_the_pinned_bytes_is_refused():
    data = TB.table_bytes({"schema": dn.SCOPE_RULE_TABLE_SCHEMA, "min_pool_occurrences_floor": 5, "rows": {}})
    with pytest.raises(DeliveryNormaliserError, match="not the pinned"):
        dn.ScopeRuleTable.from_bytes(data, expected_sha256=dn.SCOPE_RULE_TABLE_SHA256)
    with pytest.raises(DeliveryNormaliserError, match="schema"):
        dn.ScopeRuleTable.from_bytes(b'{"schema":"other"}', expected_sha256=None)
    with pytest.raises(DeliveryNormaliserError, match="floor"):
        dn.scope_rule_drops(["tomorrow"], _fake_table(), min_pool_occurrences=4)


def test_the_composed_normaliser_runs_v3_then_the_stage_with_both_sub_receipts():
    text = _answer([("date", "Tomorrow."), ("time", "six")])
    base = DELIVERY_NORMALISERS.resolve(dn.DELIVER_NORMALISE_V3)(text)
    composed = DELIVERY_NORMALISERS.resolve(dn.DELIVER_NORMALISE_V3_SCOPE_RULE_V1)(text)
    stage = DELIVERY_NORMALISERS.resolve(dn.DELIVER_SCOPE_RULE_V1)(base.text)
    assert composed.text == stage.text and composed.changed
    receipt = composed.receipt
    assert receipt["normaliser_id"] == dn.DELIVER_NORMALISE_V3_SCOPE_RULE_V1
    assert [s["normaliser_id"] for s in receipt["stages"]] == [dn.DELIVER_NORMALISE_V3, dn.DELIVER_SCOPE_RULE_V1]
    dn.validate_scope_rule_receipt(dict(receipt["stages"][-1]))
    assert receipt["input_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert receipt["output_sha256"] == hashlib.sha256(composed.text.encode()).hexdigest()
    assert receipt["entities_dropped"] == 1
    # replay form (the bundle's I7n): the id alone re-derives the bytes
    again = DELIVERY_NORMALISERS.resolve(receipt["normaliser_id"])(text)
    assert again.text == composed.text


def test_the_cited_composition_is_a_citation_unwrapping_normaliser():
    assert dn.DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1 in CITED_ANSWER_NORMALISER_IDS
    composed = DELIVERY_NORMALISERS.resolve(dn.DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1)
    assert composed.carrier_lock_key == "slurp"
    assert dn.SCOPE_RULE_COMPOSITIONS == {
        dn.DELIVER_NORMALISE_V3: dn.DELIVER_NORMALISE_V3_SCOPE_RULE_V1,
        dn.DELIVER_CITED_ANSWER_NORMALISE_V3_V1: dn.DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1,
    }


# ---------------------------------------------------------------------------
# The module component: with and without the stage differ only in the stage.
# ---------------------------------------------------------------------------

NORMALISER_LEAF = "native_episode.deliver_normaliser.normaliser"


def test_the_module_with_the_stage_and_without_differ_only_in_the_stage():
    hooks = carrier_module_hooks()
    for armed in ((), (cm.AGREE_VOTE_SEED,), (cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY)):
        without = cm.compile_module(proof.module_block(armed), hooks)
        with_stage = cm.compile_module(proof.module_block((*armed, cm.SCOPE_RULE)), hooks)
        assert cm.differing_paths(without.values(), with_stage.values()) == [NORMALISER_LEAF]
        assert with_stage.values()["native_episode"]["deliver_normaliser"]["normaliser"] == (
            dn.DELIVER_NORMALISE_V3_SCOPE_RULE_V1
        )
        assert (with_stage.program_id, with_stage.program_ceiling) == (without.program_id, without.program_ceiling)


def test_the_stage_composes_after_the_citation_contracts_normaliser():
    composed = cm.compile_module(
        proof.module_block((cm.SOLVER_CITATION_CONTRACT, cm.SCOPE_RULE)), carrier_module_hooks(),
    )
    assert composed.values()["native_episode"]["deliver_normaliser"]["normaliser"] == (
        dn.DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1
    )
    assert composed.program_id == "phase-native-candidates-review-revise-cited-v1"
    assert NORMALISER_LEAF in composed.written_paths


def test_scope_rule_params_must_equal_the_registered_pins():
    block = proof.module_block((cm.SCOPE_RULE,))
    entry = next(c for c in block["components"] if c["component_id"] == cm.SCOPE_RULE)
    entry["params"]["untagged_share"] = 0.5
    with pytest.raises(cm.ConsumptionModuleConfigError, match="registered stage's pins"):
        cm.compile_module(block, carrier_module_hooks())
    entry["params"]["untagged_share"] = 0.8
    entry["params"]["table"] = {"relpath": dn.SCOPE_RULE_TABLE_RELPATH, "sha256": "0" * 64}
    with pytest.raises(cm.ConsumptionModuleConfigError, match="registered stage's pins"):
        cm.compile_module(block, carrier_module_hooks())


def test_a_carrier_without_the_stage_refuses_to_arm_it():
    hooks = carrier_module_hooks()
    bare = cm.CarrierHooks(profile="slurp", lock_layer=hooks.lock_layer, flown_programs=hooks.flown_programs)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="deliver_stages"):
        cm.compile_module(proof.module_block((cm.SCOPE_RULE,)), bare)


def test_the_loader_accepts_the_composed_stage_config_and_refuses_the_undeclared_one():
    cell = json.loads((_REPO / "configs/experiment/slurp-native-default-plan-lock-v1.json").read_text(
        encoding="utf-8"))["cells"][0]
    lock = dict(compose(_REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"],
                        "slurp-native-default-plan-lock-v1").values)
    composed = cm.compile_module(proof.module_block((cm.SCOPE_RULE,)), carrier_module_hooks())
    values = composed.apply_to(copy.deepcopy(lock))
    values["native_episode"]["consumption_module"] = proof.module_block((cm.SCOPE_RULE,))
    program = rc.default_phase_program(values["policy"])
    parsed = load_native_episode_config(values, program)
    baseline = load_native_episode_config(copy.deepcopy(lock), program)
    assert parsed.deliver_normaliser_id == dn.DELIVER_NORMALISE_V3_SCOPE_RULE_V1
    assert baseline.deliver_normaliser_id == dn.DELIVER_NORMALISE_V3
    assert parsed.roles == baseline.roles and parsed.max_contacts == baseline.max_contacts
    # the block declares the stage, the config's own deliver node does not -> refused
    values["native_episode"]["deliver_normaliser"]["normaliser"] = dn.DELIVER_NORMALISE_V3
    with pytest.raises(ValueError, match="consumption_module is invalid.*differ"):
        load_native_episode_config(values, program)
