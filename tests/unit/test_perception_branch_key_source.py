"""The ``key_source`` Perception-branch axis (2026-09-30; docs/results/2026-09-30-slurp-
retrieval-key-recall-offline.md): parse and refusals, the receipt (schema v3) and its
validator, the runtime's branch router swap (fail closed at seed preparation) and the
branch-seed identity. Model-free throughout: synthetic stores, one-dimensional vectors.
"""

from __future__ import annotations

import copy
import hashlib
import json
import types
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
    _perception_branches_identity,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2,
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA,
    PerceptionBranchError,
    parse_perception_branches,
    perception_branch_receipt,
    perception_branch_record,
)

from test_knowledge_stores import _first_phase_config

STORE = "intent-boundaries"
FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 512,
    "base_prompt_tokens": 4000,
    "tokens_per_supplied_item": 100,
}
SHA = "a" * 64


def _source(relpath="prepared/K/key-v1.jsonl", sha256="b" * 64, signal="text: a centred key"):
    return {
        "kind": "sealed-vectors", "relpath": relpath, "sha256": sha256,
        "tool_contact_ledger_row": "SYNTHETIC-NO-CONTACT", "embedded_signal": signal,
    }


def _key_source(**swapped):
    block = {"store_id": STORE, "facet_source": None, "query_source": None, "agreement_source": None}
    block.update(swapped)
    return block


def _b_key(branch_id="B", key_source=None, max_supplied_items=8):
    return {
        "branch_id": branch_id, "max_supplied_items": max_supplied_items,
        "key_source": key_source if key_source is not None else _key_source(facet_source=_source()),
    }


def _t(**extra):
    return {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8, **extra}


def _a(**extra):
    return {"branch_id": "A", "deliver": True, "max_supplied_items": 8, **extra}


def _parse(branches, *, first_phase_id="perception", level=1, declared_stores=(STORE,)):
    return parse_perception_branches(
        {"level": level, "fit_estimate": dict(FIT), "branches": branches},
        first_phase_id=first_phase_id, declared_stores=declared_stores,
    )


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


def test_a_key_source_branch_parses_as_one_axis_category():
    query = _source(relpath="prepared/Q/q.jsonl", sha256="c" * 64, signal="speech: centred speech query")
    ks = _key_source(facet_source=_source(), query_source=query)
    group = _parse([_b_key(key_source=ks), _t(), _a()])
    branch = group.branch("B")
    assert branch.key_source.store_id == STORE
    assert sorted(branch.key_source.swapped()) == ["facet_source", "query_source"]
    assert branch.key_source.agreement_source is None
    assert branch.as_json()["key_source"]["facet_source"]["relpath"] == "prepared/K/key-v1.jsonl"
    assert group.branch("A").key_source is None and group.branch("T").key_source is None


@pytest.mark.parametrize("target", ["A", "T"])
def test_key_source_on_a_or_its_twin_is_refused(target):
    ks = _key_source(facet_source=_source())
    branches = [_b_key(), _t(**({"key_source": ks} if target == "T" else {})),
                _a(**({"key_source": ks} if target == "A" else {}))]
    with pytest.raises(PerceptionBranchError, match="no axis"):
        _parse(branches)


def test_a_key_source_that_swaps_zero_fields_is_refused():
    with pytest.raises(PerceptionBranchError, match="swaps zero retrieval-key pins"):
        _parse([_b_key(key_source=_key_source()), _t(), _a()])


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda ks: ks.pop("agreement_source"), "exactly"),
        (lambda ks: ks.update(extra=1), "exactly"),
        (lambda ks: ks.update(store_id=""), "store_id"),
        (lambda ks: ks.update(store_id="not-declared"), "not a store this configuration declares"),
        (lambda ks: ks["facet_source"].update(sha256="XYZ"), "SHA-256"),
        (lambda ks: ks["facet_source"].pop("kind"), "must be null or exactly"),
        (lambda ks: ks["facet_source"].update(relpath=""), "must be null or exactly"),
        (lambda ks: ks.update(query_source="prepared/q.jsonl"), "must be null or exactly"),
    ],
)
def test_a_malformed_key_source_is_refused(mutate, match):
    ks = _key_source(facet_source=_source())
    mutate(ks)
    with pytest.raises(PerceptionBranchError, match=match):
        _parse([_b_key(key_source=ks), _t(), _a()])


def test_key_source_beside_another_axis_is_two_factors():
    row = _b_key()
    row["min_candidates"] = 3
    with pytest.raises(PerceptionBranchError, match="exactly one axis category"):
        _parse([row, _t(), _a()])


def test_two_b_branches_with_the_same_key_source_are_refused():
    with pytest.raises(PerceptionBranchError, match="same axis"):
        _parse([_b_key("B1"), _b_key("B2"), _t(), _a()])


def test_two_b_branches_with_different_key_pins_parse():
    group = _parse([
        _b_key("B1"),
        _b_key("B2", key_source=_key_source(facet_source=_source(sha256="d" * 64))),
        _t(), _a(),
    ])
    assert group.branch("B1").key_source != group.branch("B2").key_source


# ---------------------------------------------------------------------------
# receipt (schema v3) and validator
# ---------------------------------------------------------------------------


def _records(group, level=1):
    out = []
    for index, branch in enumerate(group.branches):
        kwargs = dict(
            branch=branch, branch_index=index, contact_id=f"c{index}",
            request_sha256=SHA, response_text_sha256="c" * 64, note_sha256="d" * 64,
            note_parse_status="ok", candidate_intent_ids=("intent_a",),
            supplied_value_ids=("v1", "v2"),
        )
        if level == 2:
            kwargs.update(solver_contact_id=f"sc{index}", solver_request_sha256="e" * 64,
                          solver_response_text_sha256="f" * 64, candidate_supply_value_ids=("v1",))
        out.append(perception_branch_record(**kwargs))
    return out


def _validate(receipt, group, level=1):
    validate_perception_branch_receipt(
        receipt, branch_ids=group.branch_ids, delivered_branch_id="A", twin_branch_id="T",
        phase_id="perception", level=level,
    )


@pytest.mark.parametrize("level", [1, 2])
def test_the_receipt_carries_the_swapped_pins_and_validates(level):
    group = _parse([_b_key(), _t(), _a()], level=level)
    receipt = perception_branch_receipt(group=group, phase_id="perception", records=_records(group, level))
    assert receipt["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA == "saea-perception-branch-arms-v3"
    rows = {row["branch_id"]: row for row in receipt["branches"]}
    assert rows["B"]["key_source"] == {
        "store_id": STORE, "facet_source": {"relpath": "prepared/K/key-v1.jsonl", "sha256": "b" * 64},
        "query_source": None, "agreement_source": None,
    }
    assert rows["A"]["key_source"] is None and rows["T"]["key_source"] is None
    _validate(receipt, group, level)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda rows: rows[2].update(key_source=copy.deepcopy(rows[0]["key_source"])), "must declare no axis"),
        (lambda rows: rows[1].update(key_source=copy.deepcopy(rows[0]["key_source"])), "must declare no axis"),
        (lambda rows: rows[0].update(key_source=None), "exactly one axis category"),
        (lambda rows: rows[0]["key_source"].update(facet_source=None), "swaps no retrieval-key pin"),
        (lambda rows: rows[0]["key_source"]["facet_source"].update(sha256="nothex"), "64-hex"),
        (lambda rows: rows[0]["key_source"].pop("store_id"), "exactly"),
        (lambda rows: rows[0].pop("key_source"), "invalid shape"),
    ],
)
def test_the_validator_refuses_a_malformed_key_source_row(mutate, match):
    group = _parse([_b_key(), _t(), _a()])
    receipt = perception_branch_receipt(group=group, phase_id="perception", records=_records(group))
    mutate(receipt["branches"])
    with pytest.raises(ValueError, match=match):
        _validate(receipt, group)


def test_a_v2_receipt_without_key_source_still_validates():
    knob_b = {"branch_id": "B", "max_supplied_items": 8,
              "overrides": {f"knowledge_stores.{STORE}.phase_supply.perception.k": 8}}
    group = _parse([knob_b, _t(), _a()])
    receipt = perception_branch_receipt(group=group, phase_id="perception", records=_records(group))
    receipt["schema"] = PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2
    for row in receipt["branches"]:
        row.pop("key_source")
    _validate(receipt, group)
    # ... and a v2 row that DOES carry key_source is an invalid v2 shape.
    receipt["branches"][0]["key_source"] = None
    with pytest.raises(ValueError, match="invalid shape"):
        _validate(receipt, group)


# ---------------------------------------------------------------------------
# runtime: the branch's own router with the swapped pin; identity
# ---------------------------------------------------------------------------


def _fake_runtime(config, *, data_root):
    runtime = SimpleNamespace(
        _composed=SimpleNamespace(values=config),
        _data_root=data_root,
        _knowledge_store_binding=load_knowledge_store_binding(config, data_root=data_root),
        _knowledge_store_router_options={},
    )
    runtime._supply_action_router = types.MethodType(FlightRuntime._supply_action_router, runtime)
    runtime._apply_key_source = types.MethodType(FlightRuntime._apply_key_source, runtime)
    return runtime


def _write_facets(tmp_path, relpath, facet_id, vector):
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"id": facet_id, "vectors": {"operation": vector}}) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _runtime_group(key_source):
    return parse_perception_branches(
        {"level": 1, "fit_estimate": dict(FIT), "branches": [
            {"branch_id": "B", "max_supplied_items": 8, "key_source": key_source}, _t(), _a()]},
        first_phase_id="direct", declared_stores=(STORE, "slot-contracts"),
    )


def _expected():
    return {"s1": ("intent-boundaries::value:dim-light", "slot-contracts::value:dim-light")}


def _plan():
    binding = {"speech_packet_bindings": {"s1": {"packet_id": "speech/s1", "sha256": "a" * 64}}}
    return default_phase_program("phase-direct-only-supplied-v1"), binding, SimpleNamespace(split_identity_hash="b" * 64)


def _swap_facets(tmp_path, config, vector, relpath="prepared/KEY/facets.jsonl"):
    own = config["knowledge_stores"][STORE]["phase_supply"]["direct"]["facet_source"]
    facet_id = json.loads((tmp_path / own["relpath"]).read_text(encoding="utf-8"))["id"]
    sha = _write_facets(tmp_path, relpath, facet_id, vector)
    return _key_source(facet_source={**own, "relpath": relpath, "sha256": sha})


def test_the_swapped_key_reaches_the_branch_router_and_only_the_branch(tmp_path):
    config, _ = _first_phase_config(tmp_path)
    before = copy.deepcopy(config)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program, binding, plan = _plan()
    # An anti-aligned key: the query's cosine to it is -1, so the branch's own router
    # admits no facet from this store; A and T keep the flight's own seed (AT-P1/P2).
    group = _runtime_group(_swap_facets(tmp_path, config, [-1.0]))
    seeds, receipts = FlightRuntime._perception_branch_seeds(runtime, program, binding, group, _expected(), plan)
    assert seeds["A"] == seeds["T"] == _expected()
    assert seeds["B"]["s1"] == ("slot-contracts::value:dim-light",)
    assert config == before  # the swap lives in the branch router's own copy only
    # An aligned copy of the same key reproduces A's seed: the swap itself changes nothing else.
    same = _runtime_group(_swap_facets(tmp_path, config, [1.0], relpath="prepared/KEY2/facets.jsonl"))
    seeds2, _ = FlightRuntime._perception_branch_seeds(runtime, program, binding, same, _expected(), plan)
    assert seeds2["B"] == _expected()
    by_id = {row["branch_id"]: row["identity_sha256"] for row in receipts}
    assert by_id["A"] == by_id["T"] != by_id["B"]


def test_the_branch_identity_is_sensitive_to_the_pin_and_blind_to_a_and_t(tmp_path):
    config, _ = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program, binding, plan = _plan()
    one = _runtime_group(_swap_facets(tmp_path, config, [1.0], relpath="prepared/K1/facets.jsonl"))
    two = _runtime_group(_swap_facets(tmp_path, config, [0.5], relpath="prepared/K2/facets.jsonl"))
    _, r1 = FlightRuntime._perception_branch_seeds(runtime, program, binding, one, _expected(), plan)
    _, r2 = FlightRuntime._perception_branch_seeds(runtime, program, binding, two, _expected(), plan)
    i1 = {row["branch_id"]: row["identity_sha256"] for row in r1}
    i2 = {row["branch_id"]: row["identity_sha256"] for row in r2}
    assert i1["B"] != i2["B"]
    assert i1["A"] == i2["A"] and i1["T"] == i2["T"]
    # The config-level identity binds the whole declared block, key_source included.
    block = {"level": 1, "fit_estimate": dict(FIT), "branches": [{"branch_id": "B", "key_source": _key_source(
        facet_source=_source())}]}
    other = copy.deepcopy(block)
    other["branches"][0]["key_source"]["facet_source"]["sha256"] = "e" * 64
    ident = _perception_branches_identity({"roles": {"perception": {"branches": block}}})
    assert ident != _perception_branches_identity({"roles": {"perception": {"branches": other}}})
    assert ident["branches"][0]["key_source"]["facet_source"]["sha256"] == "b" * 64


def test_a_missing_swapped_file_fails_closed_at_seed_preparation(tmp_path):
    config, _ = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program, binding, plan = _plan()
    own = config["knowledge_stores"][STORE]["phase_supply"]["direct"]["facet_source"]
    group = _runtime_group(_key_source(facet_source={**own, "relpath": "prepared/NONE/facets.jsonl"}))
    with pytest.raises(FlightRuntimeError, match="key_source facet_source file .* missing"):
        FlightRuntime._perception_branch_seeds(runtime, program, binding, group, _expected(), plan)


def test_a_sha_mismatch_fails_closed_at_seed_preparation(tmp_path):
    config, _ = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program, binding, plan = _plan()
    ks = _swap_facets(tmp_path, config, [1.0])
    ks["facet_source"]["sha256"] = "f" * 64
    with pytest.raises(FlightRuntimeError, match="does not hash to its pinned sha256"):
        FlightRuntime._perception_branch_seeds(runtime, program, binding, _runtime_group(ks), _expected(), plan)


def test_a_swap_of_an_undeclared_pin_is_refused(tmp_path):
    config, _ = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program, binding, plan = _plan()
    ks = _key_source(agreement_source={**_source(), "kind": "sealed-agreement"})
    with pytest.raises(FlightRuntimeError, match="never adds one"):
        FlightRuntime._perception_branch_seeds(runtime, program, binding, _runtime_group(ks), _expected(), plan)
