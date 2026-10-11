"""E-T2 proof obligations (design spec 2026-10-11, sections 4.1-4.5 and 9 step 4):
the ACE reflector material, the strict delta parser, the DETERMINISTIC curator,
the token-parity helper and the ``ace-playbook`` store releases, on synthetic
fixtures only. No model, server, tokenizer service or dataset is contacted.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails import knowledge_build as _registrations  # noqa: F401
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
from speech_aware_evidence_acquisition.rails.proposer import ngram_digests
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_stage3_delta_snapshot_v2,
)
from speech_aware_evidence_acquisition.rails.stage3_delta_supply import (
    DeltaCandidate,
    node_target_of_task_target,
    select_stage3_delta_values,
)
from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace
from speech_aware_evidence_acquisition.rails.tfrl_ace_material import AceMaterialError

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_slurp_stage3_delta_store.py"
_spec = importlib.util.spec_from_file_location("_ace_test_delta_store_script", SCRIPT_PATH)
_script = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _script
_spec.loader.exec_module(_script)  # type: ignore[union-attr]

SHA = "1" * 64
LEGAL = ("general_quirky", "iot_hue_lightoff", "iot_hue_lighton", "qa_factoid")
CONSTANTS = ace.with_measured_lock_p99(1000)


def _delta(op="add", text="Prefer the closed intent list.", target="", section="strategy",
           scenarios=("all",), slots=(), rationale="table t1 shows loss"):
    return {
        "op": op, "target_id": target, "section": section,
        "scope": {"scenarios": list(scenarios), "slot_types": list(slots)},
        "text": text, "rationale": rationale,
    }


def _item(text, *, iteration=1, helpful=0, harmful=0, scoped=0, scenarios=("all",), slots=(),
          section="strategy"):
    return {
        "item_id": ace.item_id_for(text, iteration),
        "section": section,
        "scope": {"scenarios": list(scenarios), "slot_types": list(slots)},
        "text": text,
        "helpful": helpful, "harmful": harmful, "scoped_rows": scoped,
        "created_iteration": iteration,
        "provenance": [{"iteration": iteration, "op": "add", "delta_id": "d:" + "0" * 12}],
    }


def _playbook(*items, iteration=1):
    return ace.seal_playbook(
        {"schema": ace.PLAYBOOK_SCHEMA, "iteration": iteration, "items": list(items), "curation": None}
    )


def _credit(rows, iteration=1):
    return {"schema": ace.CREDIT_SCHEMA, "playbook_iteration": iteration, "rows": rows}


def _row(i, lock, ace_value, scenarios=("iot",), slots=("device",)):
    return {
        "row_digest": hashlib.sha256(f"row-{i}".encode()).hexdigest(),
        "scenarios": list(scenarios), "slot_types": list(slots),
        "lock": lock, "ace": ace_value,
    }


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------


def test_constants_hash_is_stable_and_t_cap_follows_the_formula() -> None:
    assert ace.constants_hash(ace.ACE_CONSTANTS) == ace.constants_hash(copy.deepcopy(ace.ACE_CONSTANTS))
    assert len(ace.constants_hash(ace.ACE_CONSTANTS)) == 64
    # A = 8 items x 235 tokens (spec 4.3)
    assert ace.ACE_CONSTANTS["allowance_tokens"] == 8 * 235 == 1880
    assert ace.resolve_t_cap(CONSTANTS) == 1000 + 1880
    changed = dict(ace.ACE_CONSTANTS, dedup_jaccard=0.7)
    assert ace.constants_hash(changed) != ace.constants_hash(ace.ACE_CONSTANTS)


def test_constants_refuse_unknown_missing_and_unmeasured() -> None:
    with pytest.raises(AceMaterialError, match="unknown keys"):
        ace.validate_constants(dict(ace.ACE_CONSTANTS, surprise=1))
    broken = dict(ace.ACE_CONSTANTS)
    del broken["dedup_jaccard"]
    with pytest.raises(AceMaterialError, match="missing keys"):
        ace.validate_constants(broken)
    with pytest.raises(AceMaterialError, match="lock_p99_supplied_tokens"):
        ace.resolve_t_cap(ace.ACE_CONSTANTS)


# ---------------------------------------------------------------------------
# the delta schema and the strict parser
# ---------------------------------------------------------------------------


def test_parser_accepts_a_legal_payload_and_normalises() -> None:
    payload = {"deltas": [
        _delta(text="  Use   the closed list.  ", scenarios=("qa", "iot"), slots=("zeta", "alpha")),
        _delta(op="modify", target="ace:i1:" + "a" * 12, text="Rewrite."),
        _delta(op="delete", target="ace:i1:" + "b" * 12, text=""),
    ]}
    parsed = ace.parse_reflector_response(payload)
    assert parsed[0]["text"] == "Use the closed list."
    assert parsed[0]["scope"] == {"scenarios": ["iot", "qa"], "slot_types": ["alpha", "zeta"]}
    assert [d["op"] for d in parsed] == ["add", "modify", "delete"]


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda p: p.update(extra=1), "exactly 'deltas'"),
        (lambda p: p.update(deltas="x"), "must be a list"),
        (lambda p: p["deltas"][0].update(helpful=3), "exactly op"),
        (lambda p: p["deltas"][0].update(op="rewrite"), "op must be one of"),
        (lambda p: p["deltas"][0].update(section="advice"), "section must be one of"),
        (lambda p: p["deltas"][0].update(target_id="ace:i1:" + "a" * 12), "carries no target_id"),
        (lambda p: p["deltas"][0].update(text=""), "needs text"),
        (lambda p: p["deltas"][0].update(text="caf\u00e9"), "printable ASCII"),
        (lambda p: p["deltas"][0].update(text="x" * 401), "exceeds 400"),
        (lambda p: p["deltas"][0].update(rationale="y" * 201), "exceeds 200"),
        (lambda p: p["deltas"][0]["scope"].update(scenarios=["all", "iot"]), "stand alone"),
        (lambda p: p["deltas"][0]["scope"].update(scenarios=[]), "1-18"),
        (lambda p: p["deltas"][0]["scope"].update(scenarios=["IoT"]), "malformed name"),
        (lambda p: p["deltas"][0]["scope"].update(extra=[]), "exactly scenarios"),
        (lambda p: p["deltas"][0].update(target_id="not-an-id"), "malformed"),
    ],
)
def test_parser_refuses_everything_else(mutate, message) -> None:
    payload = {"deltas": [_delta()]}
    mutate(payload)
    with pytest.raises(AceMaterialError, match=message):
        ace.parse_reflector_response(payload)


def test_parser_refuses_cross_field_violations_and_counts() -> None:
    with pytest.raises(AceMaterialError, match="modify needs a target_id"):
        ace.parse_reflector_response({"deltas": [_delta(op="modify")]})
    with pytest.raises(AceMaterialError, match="delete needs a target_id"):
        ace.parse_reflector_response({"deltas": [_delta(op="delete", text="")]})
    with pytest.raises(AceMaterialError, match="delete carries no text"):
        ace.parse_reflector_response(
            {"deltas": [_delta(op="delete", target="ace:i1:" + "a" * 12, text="why")]}
        )
    four_adds = {"deltas": [_delta(text=f"Note number {i}.") for i in range(4)]}
    with pytest.raises(AceMaterialError, match="too many add deltas"):
        ace.parse_reflector_response(four_adds)
    seven = {"deltas": [_delta(op="delete", target="ace:i1:" + f"{i:012x}", text="") for i in range(7)]}
    with pytest.raises(AceMaterialError, match="too many deltas"):
        ace.parse_reflector_response(seven)
    with pytest.raises(AceMaterialError, match="must be an object"):
        ace.parse_reflector_response([])  # type: ignore[arg-type]


def test_wire_schema_matches_the_parser_and_has_no_numeric_field() -> None:
    schema = ace.DELTA_ITEMS_SCHEMA
    item = schema["properties"]["deltas"]["items"]
    assert set(item["required"]) == {"op", "target_id", "section", "scope", "text", "rationale"}
    assert item["additionalProperties"] is False
    assert item["properties"]["text"]["maxLength"] == 400
    assert item["properties"]["op"]["enum"] == ["add", "modify", "delete"]
    blob = json.dumps(schema)
    assert '"integer"' not in blob and '"number"' not in blob
    fmt = ace.response_format()
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "saea-ace-delta-items-v1"


# ---------------------------------------------------------------------------
# material and the reflector request
# ---------------------------------------------------------------------------


def _material(**changes):
    document = {
        "schema": ace.MATERIAL_SCHEMA, "iteration": 1, "scenario": "iot",
        "source": {"column_arm": "lock", "run_id": "SAEA-TEST-RUN", "credit_receipt_sha256": SHA},
        "n_rows": 60,
        "credit_tables": [{
            "table_id": "slot-type-loss", "title": "Official loss by slot type",
            "columns": ["slot_type", "rows", "mean_loss"],
            "rows": [["device", 20, 0.1234], ["time", 12, None]],
        }],
        "item_counters": [],
    }
    document.update(changes)
    return ace.seal_material(document)


def _write_json(path: Path, document) -> Path:
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_request_is_text_only_and_deterministic(tmp_path) -> None:
    item = _item("Prefer the closed intent list.")
    material = _material(item_counters=[
        {"item_id": item["item_id"], "helpful": 3, "harmful": 1, "scoped_rows": 9}
    ])
    mpath = _write_json(tmp_path / "material.json", material)
    ppath = tmp_path / "playbook.json"
    ace.write_playbook(ppath, _playbook(item))
    first = ace.render_reflector_request(mpath, ppath, 2880)
    second = ace.render_reflector_request(mpath, ppath, 2880)
    assert first == second
    assert first["request_sha256"] == second["request_sha256"]
    assert [m["role"] for m in first["messages"]] == ["user"]
    content = first["messages"][0]["content"]
    assert isinstance(content, str) and "{{" not in content
    assert "audio" not in json.dumps(first["messages"]).lower().replace("spoken", "")
    assert item["item_id"] in content and "slot-type-loss" in content
    assert "0.1234" in content and "2880" in content
    assert first["response_format"]["json_schema"]["name"] == "saea-ace-delta-items-v1"
    assert first["material_sha256"] == material["material_sha256"]
    assert first["instruction_relpath"] == "configs/probes/tfrl/ace-reflector-v1.txt"
    assert first["max_tokens"] == 1024 and first["temperature"] == 0
    # the instruction artefact is English ASCII and pinned by sha256
    raw = (REPO_ROOT / ace.INSTRUCTION_RELPATH).read_bytes()
    raw.decode("ascii")
    assert first["instruction_sha256"] == hashlib.sha256(raw).hexdigest()


def test_request_with_an_empty_playbook_says_so(tmp_path) -> None:
    mpath = _write_json(tmp_path / "m.json", _material())
    ppath = tmp_path / "p.json"
    ace.write_playbook(ppath, ace.empty_playbook())
    request = ace.render_reflector_request(mpath, ppath, 100)
    assert "(the playbook is empty)" in request["messages"][0]["content"]


@pytest.mark.parametrize("key", ["text", "transcript", "gold", "value_text", "utterance", "sample_id"])
def test_material_refuses_forbidden_keys_at_any_depth(tmp_path, key) -> None:
    top = _material()
    top[key] = "hello"
    with pytest.raises(AceMaterialError, match="forbidden key"):
        ace.validate_material(top)
    nested = copy.deepcopy(_material())
    nested["credit_tables"][0][key] = "hello"
    with pytest.raises(AceMaterialError, match="forbidden key"):
        ace.validate_material(nested)
    nested2 = copy.deepcopy(_material())
    nested2["source"][key] = "hello"
    with pytest.raises(AceMaterialError, match="forbidden key"):
        ace.validate_material(nested2)


def test_material_refuses_free_text_cells_identifiers_and_a_bad_hash() -> None:
    sentence = _material(credit_tables=[{
        "table_id": "t", "title": "x", "columns": ["a"],
        "rows": [["set an alarm for seven in the morning please"]],
    }])
    with pytest.raises(AceMaterialError, match="4 words|closed-vocabulary"):
        ace.validate_material(sentence)
    ident = _material(credit_tables=[{
        "table_id": "t", "title": "x", "columns": ["a"], "rows": [["slurp:devel:001234"]],
    }])
    with pytest.raises(AceMaterialError, match="closed-vocabulary|sample identifier"):
        ace.validate_material(ident)
    digits = _material(credit_tables=[{
        "table_id": "t", "title": "x", "columns": ["a"], "rows": [["id 123456"]],
    }])
    with pytest.raises(AceMaterialError, match="sample identifier"):
        ace.validate_material(digits)
    tampered = _material()
    tampered["n_rows"] = 61
    with pytest.raises(AceMaterialError, match="material_sha256 differs"):
        ace.validate_material(tampered)
    nonascii = _material(credit_tables=[{
        "table_id": "t", "title": "caf\u00e9", "columns": ["a"], "rows": [],
    }])
    with pytest.raises(AceMaterialError, match="title is malformed"):
        ace.validate_material(nonascii)


def test_request_refuses_a_tampered_playbook(tmp_path) -> None:
    mpath = _write_json(tmp_path / "m.json", _material())
    doc = dict(_playbook(_item("Some note here.")))
    doc["iteration"] = 9
    ppath = _write_json(tmp_path / "p.json", doc)
    with pytest.raises(AceMaterialError, match="content_hash differs"):
        ace.render_reflector_request(mpath, ppath, 100)


# ---------------------------------------------------------------------------
# counters by script (I-OBJ)
# ---------------------------------------------------------------------------


def test_counters_are_computed_from_credit_not_claims() -> None:
    iot = _item("Keep device names short.", scenarios=("iot",))
    qa = _item("Answer factoid questions directly.", scenarios=("qa",))
    rows = (
        [_row(i, 0.5, 0.8) for i in range(4)]          # helpful
        + [_row(10 + i, 0.5, 0.2) for i in range(2)]   # harmful
        + [_row(20, 0.5, 0.5)]                         # tie
        + [_row(30, 0.1, 0.9, scenarios=("qa",))]      # only the qa item
    )
    updates = ace.compute_counter_updates([iot, qa], _credit(rows))
    assert updates[iot["item_id"]] == {"helpful": 4, "harmful": 2, "scoped_rows": 7}
    assert updates[qa["item_id"]] == {"helpful": 1, "harmful": 0, "scoped_rows": 1}


def test_slot_type_scope_narrows_the_counters() -> None:
    item = _item("Dates need a month.", scenarios=("all",), slots=("date",))
    rows = [_row(1, 0.2, 0.9, slots=("date",)), _row(2, 0.2, 0.9, slots=("device",))]
    assert ace.compute_counter_updates([item], _credit(rows))[item["item_id"]]["scoped_rows"] == 1


def test_credit_refuses_bad_values_and_duplicate_rows() -> None:
    with pytest.raises(AceMaterialError, match="in \\[0, 1\\]"):
        ace.validate_credit(_credit([_row(1, 0.5, 1.5)]))
    row = _row(1, 0.5, 0.6)
    with pytest.raises(AceMaterialError, match="repeats"):
        ace.validate_credit(_credit([row, dict(row)]))
    bad = dict(_row(1, 0.5, 0.6), text="hi")
    with pytest.raises(AceMaterialError, match="forbidden key"):
        ace.validate_credit(_credit([bad]))


# ---------------------------------------------------------------------------
# curate
# ---------------------------------------------------------------------------


def test_curate_is_deterministic() -> None:
    playbook = _playbook(_item("Prefer the closed intent list."), iteration=1)
    deltas = ace.parse_reflector_response({"deltas": [
        _delta(text="Spell numbers as digits."),
        _delta(text="Never invent a slot value.", section="pitfall"),
    ]})
    credit = _credit([_row(i, 0.4, 0.6) for i in range(5)])
    first = ace.curate(playbook, deltas, credit, CONSTANTS)
    second = ace.curate(copy.deepcopy(playbook), copy.deepcopy(deltas), copy.deepcopy(credit), dict(CONSTANTS))
    assert first == second
    assert first["content_hash"] == second["content_hash"]
    assert first["iteration"] == 2
    ace.validate_playbook(first)
    assert first["curation"]["constants_sha256"] == ace.constants_hash(CONSTANTS)
    assert first["curation"]["applied"] == {"add": 2, "modify": 0, "delete": 0}


def test_curate_grows_with_provenance_and_zero_counters() -> None:
    result = ace.curate(ace.empty_playbook(), ace.parse_reflector_response({"deltas": [_delta()]}), None, CONSTANTS)
    (item,) = result["items"]
    assert item["helpful"] == item["harmful"] == item["scoped_rows"] == 0
    assert item["created_iteration"] == 1
    assert item["item_id"] == ace.item_id_for(item["text"], 1)
    assert item["provenance"][0]["iteration"] == 1 and item["provenance"][0]["op"] == "add"
    assert item["provenance"][0]["delta_id"].startswith("d:")


def test_curate_applies_counters_then_keeps_existing_items_verbatim() -> None:
    old = _item("Keep device names short.", scenarios=("iot",))
    credit = _credit([_row(i, 0.3, 0.7) for i in range(3)], iteration=1)
    result = ace.curate(_playbook(old), [], credit, CONSTANTS)
    (kept,) = result["items"]
    assert (kept["helpful"], kept["harmful"], kept["scoped_rows"]) == (3, 0, 3)
    assert kept["text"] == old["text"] and kept["item_id"] == old["item_id"]
    assert result["curation"]["counter_updates"][old["item_id"]]["helpful"] == 3


def test_curate_modify_resets_counters_and_records_the_replaced_id() -> None:
    old = _item("Keep device names short.", helpful=4, harmful=1, scoped=6)
    deltas = ace.parse_reflector_response({"deltas": [
        _delta(op="modify", target=old["item_id"], text="Keep device names to one word."),
    ]})
    result = ace.curate(_playbook(old), deltas, None, CONSTANTS)
    (new,) = result["items"]
    assert new["item_id"] != old["item_id"]
    assert (new["helpful"], new["harmful"], new["scoped_rows"]) == (0, 0, 0)
    assert new["created_iteration"] == 2
    assert new["provenance"][-1]["replaces"] == old["item_id"]
    assert result["curation"]["replaced"] == {old["item_id"]: new["item_id"]}


def test_curate_delete_and_unknown_targets_are_counted_not_raised() -> None:
    old = _item("Keep device names short.")
    deltas = ace.parse_reflector_response({"deltas": [
        _delta(op="delete", target=old["item_id"], text=""),
        _delta(op="delete", target="ace:i7:" + "c" * 12, text=""),
        _delta(op="modify", target="ace:i7:" + "d" * 12, text="Phantom."),
    ]})
    result = ace.curate(_playbook(old), deltas, None, CONSTANTS)
    assert result["items"] == []
    assert result["curation"]["deleted"] == [old["item_id"]]
    assert result["curation"]["refused"]["unknown_target"] == 2


def test_curate_dedups_exact_and_near_and_merges_scope_and_provenance() -> None:
    base = _item("Always answer with entities from the closed list only.", scenarios=("iot",))
    deltas = ace.parse_reflector_response({"deltas": [
        _delta(text="ALWAYS answer  with entities from the CLOSED list only.", scenarios=("qa",)),
        _delta(text="Always answer with entities from the closed list only please.", scenarios=("music",)),
        _delta(text="Use ISO dates when a date slot is present.", scenarios=("calendar",)),
    ]})
    result = ace.curate(_playbook(base), deltas, None, CONSTANTS)
    texts = sorted(item["text"] for item in result["items"])
    assert texts == sorted([base["text"], "Use ISO dates when a date slot is present."])
    survivor = next(i for i in result["items"] if i["item_id"] == base["item_id"])
    assert survivor["scope"]["scenarios"] == ["iot", "music", "qa"]
    assert [e["op"] for e in survivor["provenance"]].count("merge") == 2
    dedup = result["curation"]["dedup"]
    assert dedup["exact"] == 1 and dedup["near"] == 1 and len(dedup["merges"]) == 2


def test_curate_dedup_threshold_is_the_pinned_constant() -> None:
    base = _item("alpha beta gamma delta epsilon")
    near = "alpha beta gamma delta zeta"   # Jaccard 4/6 = 0.667
    deltas = ace.parse_reflector_response({"deltas": [_delta(text=near)]})
    assert len(ace.curate(_playbook(base), deltas, None, CONSTANTS)["items"]) == 2
    loose = dict(CONSTANTS, dedup_jaccard=0.6)
    assert len(ace.curate(_playbook(base), deltas, None, loose)["items"]) == 1


def test_curate_prunes_by_script_computed_counters_over_enough_rows() -> None:
    bad = _item("Guess the slot value when unsure.", scenarios=("iot",))
    good = _item("Prefer the closed intent list.", scenarios=("iot",))
    other = _item("Use ISO dates.", scenarios=("qa",))
    rows = [_row(i, 0.8, 0.2) for i in range(12)]   # every iot row worse under ace
    # make the good item look good: it shares the scope, so give it prior credit
    good = dict(good, helpful=30, scoped_rows=30)
    result = ace.curate(_playbook(bad, good, other), [], _credit(rows), CONSTANTS)
    ids = {item["item_id"] for item in result["items"]}
    # bad: harmful 12, helpful 0, rows 12 -> pruned; good: 30 vs 12 -> net +18, kept; other untouched
    assert bad["item_id"] not in ids
    assert good["item_id"] in ids and other["item_id"] in ids
    assert result["curation"]["pruned"] == [bad["item_id"]]


def test_curate_does_not_prune_before_enough_scoped_rows() -> None:
    bad = _item("Guess the slot value when unsure.", scenarios=("iot",))
    rows = [_row(i, 0.8, 0.2) for i in range(9)]    # harm margin met, rows < 10
    result = ace.curate(_playbook(bad), [], _credit(rows), CONSTANTS)
    assert [i["item_id"] for i in result["items"]] == [bad["item_id"]]
    assert result["curation"]["pruned"] == []


def test_curate_enforces_t_cap_with_a_deterministic_drop_order() -> None:
    a = _item("Item A advice text.", iteration=1, helpful=5)                # net +5
    b = _item("Item B advice text.", iteration=1, helpful=2, harmful=1)     # net +1, older
    c = _item("Item C advice text.", iteration=2, helpful=1)                # net +1, newer
    d = _item("Item D advice text.", iteration=1, harmful=2)                # net -2
    pb = _playbook(a, b, c, d, iteration=2)
    ranked = [i["item_id"] for i in ace.rank_items(pb["items"])]
    assert ranked == [a["item_id"], b["item_id"], c["item_id"], d["item_id"]]
    lines = [ace.item_line(i) for i in ace.rank_items(pb["items"])]
    cap_for_two = ace.proxy_token_count(ace._render_lines(lines[:2]))
    constants = dict(ace.with_measured_lock_p99(0), allowance_tokens=cap_for_two)
    result = ace.curate(pb, [], None, constants)
    assert [i["item_id"] for i in result["items"]] == ranked[:2]
    assert result["curation"]["dropped_by_cap"] == ranked[2:]
    assert result["curation"]["t_cap"] == cap_for_two
    assert result["curation"]["rendered_tokens"] <= cap_for_two
    # a custom counter changes the count, and is named in the report
    def per_line(text):
        return text.count("\n") * 100

    per_line.counter_id = "test-lines"
    short = ace.curate(pb, [], None, dict(ace.with_measured_lock_p99(0), allowance_tokens=200), token_counter=per_line)
    assert len(short["items"]) == 2 and short["curation"]["token_counter_id"] == "test-lines"


def test_curate_refuses_decontamination_violations() -> None:
    sentence = "turn on the kitchen light please now"
    digests = ngram_digests([sentence])
    deltas = ace.parse_reflector_response({"deltas": [
        _delta(text="Remember turn on the kitchen light please now always."),
        _delta(text="Item slurp:devel:001234 is hard."),
        _delta(text="Plain general advice."),
    ]})
    result = ace.curate(ace.empty_playbook(), deltas, None, CONSTANTS, evaluation_ngram_digests=digests)
    assert [i["text"] for i in result["items"]] == ["Plain general advice."]
    refused = result["curation"]["refused"]
    assert refused["evaluation_ngram"] == 1 and refused["sample_identifier"] == 1


def test_curate_refuses_a_credit_for_another_playbook_and_unparsed_deltas() -> None:
    pb = _playbook(_item("A note."), iteration=3)
    with pytest.raises(AceMaterialError, match="credit playbook_iteration"):
        ace.curate(pb, [], _credit([_row(1, 0.1, 0.2)], iteration=2), CONSTANTS)
    with pytest.raises(AceMaterialError, match="exactly op"):
        ace.curate(pb, [{"op": "add"}], None, CONSTANTS)
    with pytest.raises(AceMaterialError, match="lock_p99_supplied_tokens"):
        ace.curate(pb, [], None, dict(ace.ACE_CONSTANTS))


# ---------------------------------------------------------------------------
# rendering, parity
# ---------------------------------------------------------------------------


def test_empty_playbook_renders_empty_supply() -> None:
    assert ace.render_playbook_supply(ace.empty_playbook(), 1000) == ""
    assert ace.count_playbook_tokens(ace.empty_playbook()) == 0


def test_render_is_rank_ordered_and_prefix_truncated() -> None:
    a = _item("First advice.", helpful=3)
    b = _item("Second advice.", helpful=1)
    pb = _playbook(b, a)
    full = ace.render_playbook_supply(pb, 10_000)
    assert full == "Playbook notes:\n- [strategy] First advice.\n- [strategy] Second advice."
    one = ace.proxy_token_count("Playbook notes:\n- [strategy] First advice.")
    assert ace.render_playbook_supply(pb, one) == "Playbook notes:\n- [strategy] First advice."
    assert ace.render_playbook_supply(pb, 0) == ""


def test_tokenize_counter_wraps_an_injected_requester() -> None:
    calls = []

    def request_json(method, path, body):
        calls.append((method, path, body))
        return {"tokens": list(range(len(body["content"].split())))}

    counter = ace.make_tokenize_counter(request_json)
    assert counter("a b c") == 3 and counter("") == 0
    assert calls == [("POST", "/tokenize", {"content": "a b c", "add_special": False, "parse_special": True})]
    assert counter.counter_id == "serving-tokenize-v1"
    with pytest.raises(AceMaterialError, match="no token list"):
        ace.make_tokenize_counter(lambda *a: {})("x")


def test_parity_helper_gates_non_twin_arms_on_t_cap() -> None:
    lock = [100] * 98 + [900, 1000]            # nearest-rank p99 = 900
    assert ace.percentile99(lock) == 900
    report = ace.token_parity_report({
        "lock": lock, "aa": lock, "typ": [900] * 100, "ace": [2780] * 100,
    })
    assert report["lock_p99_supplied_tokens"] == 900
    assert report["t_cap"] == 900 + 1880
    assert report["arms"]["ace"]["within"] and report["arms"]["typ"]["within"]
    assert report["arms"]["lock"]["over_rows"] == 0
    assert report["parity_ok"] is True
    over = ace.token_parity_report({"lock": lock, "ace": [2781] * 5, "aa": [9999]})
    assert over["arms"]["ace"]["over_rows"] == 5 and over["parity_ok"] is False
    assert over["arms"]["aa"]["gated"] is False   # the twin is reported, not gated
    with pytest.raises(AceMaterialError, match="needs the 'lock' arm"):
        ace.token_parity_report({"ace": [1]})


# ---------------------------------------------------------------------------
# the ace-playbook release (same authored form as the delta stores)
# ---------------------------------------------------------------------------


def _write_pin(path: Path, document) -> dict[str, str]:
    raw = canonical_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"relpath": path.name, "sha256": hashlib.sha256(raw).hexdigest()}


def _roster(ids, *, roster_id, roster_role="construction"):
    return {
        "schema": "saea-roster-receipt-v1", "roster_id": roster_id, "carrier_lock_key": "slurp",
        "split_role": "discovery", "roster_role": roster_role,
        "items": [{"sample_id": s, "stratum": "synthetic"} for s in ids],
        "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
    }


def _release(tmp_path, playbook, *, with_registration=False):
    data_root = tmp_path / "data"
    receipt = ace.build_playbook_release(
        playbook, data_root=data_root, carrier_sample_ids=("row-a", "row-b"),
        legal_intent_ids=LEGAL, source_split_identity_hash=SHA,
    )
    return data_root, receipt


def _snapshot(rows):
    spec = AuthoredSemanticKnowledgeSpec(
        carrier_lock_key="slurp", source_split_identity_hash=SHA,
        permitted_source_sample_ids=("row-a", "row-b", "row-c"),
    )
    return build_stage3_delta_snapshot_v2(spec, rows=rows)


def _solver_slice(snapshot, facets):
    deltas = [
        DeltaCandidate(
            value_id=v.value_id, associated_facet_ids=tuple(v.associated_facet_ids),
            prior_score=v.prior_score, node_target=node_target_of_task_target(v.task_target),
        )
        for v in snapshot.values
    ]
    return select_stage3_delta_values(facets, deltas, cap=50, node_target="solver")


def test_empty_i0_release_is_buildable_and_renders_an_empty_supply(tmp_path) -> None:
    playbook = ace.empty_playbook()
    data_root, receipt = _release(tmp_path, playbook)
    assert receipt["empty"] is True and receipt["row_count"] == 1
    source = json.loads((data_root / receipt["source"]["relpath"]).read_text())
    snapshot = _snapshot(source["rows"])                  # the compiler accepts it: non-empty
    assert len(snapshot.values) == 1
    # ...and the Solver route (node-filtered) selects nothing, for ANY candidate set
    assert _solver_slice(snapshot, LEGAL) == ()
    assert _solver_slice(snapshot, [ace.ANCHOR_FACET_ID]) == ()
    assert ace.render_playbook_supply(playbook, 5000) == ""


def test_release_has_the_delta_store_authored_and_source_format(tmp_path) -> None:
    items = [
        _item("Prefer the closed intent list.", helpful=4),
        _item("Dates need a month and a day.", scenarios=("calendar", "iot"), slots=("date",), iteration=2),
    ]
    playbook = _playbook(*items, iteration=2)
    data_root, receipt = _release(tmp_path, playbook)
    authored = json.loads((data_root / receipt["authored"]["relpath"]).read_text())
    assert authored["schema"] == "saea-stage3-authored-deltas-v2" and authored["iteration"] == 2
    # the existing wrapper builder produces the very same envelope
    expected = _script.build_authored_source_document(authored, source_split_identity_hash=SHA)
    written = json.loads((data_root / receipt["source"]["relpath"]).read_text())
    assert written == expected
    assert written["builder_policy_id"] == "saea-authored-stage3-deltas-v2"
    # every row carries exactly the v2 authored keys and validates under the script
    for row in written["rows"]:
        _script._validate_authored_row(row, field="row", required=_script._AUTHORED_ROW_KEYS_V2)
    # bytes are canonical: a rebuild reproduces the digests
    again = ace.build_playbook_release(
        playbook, data_root=tmp_path / "data2", carrier_sample_ids=("row-b", "row-a"),
        legal_intent_ids=LEGAL, source_split_identity_hash=SHA,
    )
    assert again["source"]["sha256"] == receipt["source"]["sha256"]
    assert again["authored"]["sha256"] == receipt["authored"]["sha256"]


def test_release_routes_by_scope_and_orders_like_the_playbook(tmp_path) -> None:
    top = _item("Top advice for every scenario.", helpful=9)
    mid = _item("Lights need a device name.", scenarios=("iot",), helpful=2)
    low = _item("Quiz answers should be short.", scenarios=("qa",), harmful=1)
    playbook = _playbook(low, mid, top, iteration=1)
    data_root, receipt = _release(tmp_path, playbook)
    source = json.loads((data_root / receipt["source"]["relpath"]).read_text())
    snapshot = _snapshot(source["rows"])
    by_value = {v.value_id: v for v in snapshot.values}
    # all items go to the Solver node; value ids follow the item digest
    assert {node_target_of_task_target(v.task_target) for v in snapshot.values} == {"solver"}
    iot_only = _solver_slice(snapshot, ["iot_hue_lightoff"])
    contents = [by_value[v].content for v in iot_only]
    assert contents == [ace.item_line(top), ace.item_line(mid)]          # rank order, qa item not routed
    anything = _solver_slice(snapshot, ["general_quirky"])
    assert [by_value[v].content for v in anything] == [ace.item_line(top)]  # global item only
    qa = _solver_slice(snapshot, ["qa_factoid"])
    assert [by_value[v].content for v in qa] == [ace.item_line(top), ace.item_line(low)]
    assert [by_value[v].content for v in _solver_slice(snapshot, LEGAL)] == [
        ace.item_line(i) for i in ace.rank_items(playbook["items"])
    ]


def test_release_round_trips_through_the_existing_store_loader(tmp_path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    playbook = _playbook(_item("Prefer the closed intent list.", helpful=2), iteration=1)
    ids = ("row-a", "row-b", "row-c")
    support_identity = split_identity_hash(prefixed("slurp", ids))
    binding = {
        "construction_scope": _write_pin(repo_root / "scope.json", _roster(ids, roster_id="scope")),
        "permitted_roster": _write_pin(repo_root / "permitted.json", _roster(ids, roster_id="permitted")),
        "forbidden_rosters": [_write_pin(
            repo_root / "forbidden.json",
            _roster(("forbidden-1",), roster_id="forbidden", roster_role="evaluation"),
        )],
    }
    data_root = tmp_path / "data"
    registration_path = repo_root / "registration.json"
    receipt = ace.build_playbook_release(
        playbook, data_root=data_root, carrier_sample_ids=("row-a", "row-b"),
        legal_intent_ids=LEGAL, source_split_identity_hash=support_identity,
        registration_binding=binding, registration_path=registration_path,
    )
    assert receipt["registration"]["output_namespace"] == "knowledge/slurp/semantic/ace-playbook-i1"
    result = prepare_semantic_knowledge_store(registration_path, repo_root=repo_root, data_root=data_root)
    assert result["cache"] == "cold"
    completion = result["completion"]
    loaded = load_knowledge_store_binding(
        {"knowledge_stores": {"ace-playbook": {
            "store_role": "stage3-deltas",
            "snapshot": completion["snapshot"], "release": completion["release"],
        }}},
        data_root=data_root,
    )
    snapshot = loaded.snapshot_for("ace-playbook")
    assert snapshot.builder_policy_id == "saea-authored-stage3-deltas-v2"
    assert [v.content for v in snapshot.values] == [ace.item_line(playbook["items"][0])]
    assert snapshot.source_sample_ids == ("row-a", "row-b")


def test_the_empty_i0_release_also_compiles_through_the_preparer(tmp_path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ids = ("row-a", "row-b", "row-c")
    support_identity = split_identity_hash(prefixed("slurp", ids))
    binding = {
        "construction_scope": _write_pin(repo_root / "scope.json", _roster(ids, roster_id="scope")),
        "permitted_roster": _write_pin(repo_root / "permitted.json", _roster(ids, roster_id="permitted")),
        "forbidden_rosters": [_write_pin(
            repo_root / "forbidden.json",
            _roster(("forbidden-1",), roster_id="forbidden", roster_role="evaluation"),
        )],
    }
    registration_path = repo_root / "registration-i0.json"
    ace.build_playbook_release(
        ace.empty_playbook(), data_root=tmp_path / "data", carrier_sample_ids=("row-a",),
        legal_intent_ids=LEGAL, source_split_identity_hash=support_identity,
        registration_binding=binding, registration_path=registration_path,
    )
    result = prepare_semantic_knowledge_store(registration_path, repo_root=repo_root, data_root=tmp_path / "data")
    assert result["completion"]["release"]["relpath"].startswith("knowledge/slurp/semantic/ace-playbook-i0/")


def test_release_refuses_bad_inputs(tmp_path) -> None:
    pb = _playbook(_item("A note."), iteration=1)
    with pytest.raises(AceMaterialError, match="64-hex"):
        ace.build_playbook_release(pb, data_root=tmp_path, carrier_sample_ids=("a",),
                                   legal_intent_ids=LEGAL, source_split_identity_hash="x")
    with pytest.raises(AceMaterialError, match="carrier_sample_ids"):
        ace.build_playbook_release(pb, data_root=tmp_path, carrier_sample_ids=(),
                                   legal_intent_ids=LEGAL, source_split_identity_hash=SHA)
    narrow = _playbook(_item("Weather note.", scenarios=("weather",)), iteration=1)
    with pytest.raises(AceMaterialError, match="no legal intent facet"):
        ace.build_playbook_release(narrow, data_root=tmp_path, carrier_sample_ids=("a",),
                                   legal_intent_ids=LEGAL, source_split_identity_hash=SHA)
    with pytest.raises(AceMaterialError, match="registration_path is required"):
        ace.build_playbook_release(pb, data_root=tmp_path, carrier_sample_ids=("a",),
                                   legal_intent_ids=LEGAL, source_split_identity_hash=SHA,
                                   registration_binding={"construction_scope": {}, "permitted_roster": {},
                                                         "forbidden_rosters": []})


def test_curate_then_release_end_to_end(tmp_path) -> None:
    """i0 -> reflector deltas -> i1 -> credit -> i2, releasing each state."""

    i0 = ace.empty_playbook()
    deltas = ace.parse_reflector_response({"deltas": [
        _delta(text="Prefer the closed intent list."),
        _delta(text="Never guess a slot value.", section="pitfall", scenarios=("iot",)),
    ]})
    i1 = ace.curate(i0, deltas, None, CONSTANTS)
    assert len(i1["items"]) == 2
    credit = _credit([_row(n, 0.2, 0.8) for n in range(10)], iteration=1)
    i2 = ace.curate(i1, [], credit, CONSTANTS)
    assert all(item["helpful"] > 0 for item in i2["items"] if item["scope"]["scenarios"] == ["iot"])
    for playbook in (i0, i1, i2):
        _, receipt = _release(tmp_path / f"i{playbook['iteration']}", playbook)
        assert receipt["iteration"] == playbook["iteration"]


def test_release_rows_carry_a_rank_ordered_prior_score_inside_the_unit_interval() -> None:
    """The snapshot refuses a prior_score outside [0, 1]; the rows rank by ``(total - rank) / total`` (strictly decreasing, top item 1.0)."""

    items = [_item(f"Advice number {n}.", helpful=20 - n) for n in range(18)]
    rows = ace.playbook_release_rows(_playbook(*items), carrier_sample_ids=["slurp:train:000001:audio-1"], legal_intent_ids=("iot_hue_lightoff",))
    scores = [row["prior_score"] for row in rows]
    assert len(scores) == 18 and scores[0] == 1.0 and scores[-1] == 1 / 18
    assert all(0.0 < s <= 1.0 for s in scores) and scores == sorted(scores, reverse=True) and len(set(scores)) == 18
    assert [row["content"] for row in rows][0].endswith("Advice number 0.")


# ---------------------------------------------------------------------------
# item ids inside a rendered prompt (loop iteration 2 render failure)
# ---------------------------------------------------------------------------


def test_request_renders_an_item_id_whose_hex_holds_a_six_digit_run(tmp_path) -> None:
    item = _item("Prefer the closed intent list.")
    item["item_id"] = "ace:i1:727456a71a6d"  # 6-digit run, bounded by ':' and a hex letter
    mpath = _write_json(tmp_path / "m.json", _material())
    ppath = tmp_path / "p.json"
    ace.write_playbook(ppath, _playbook(item))
    request = ace.render_reflector_request(mpath, ppath, 100)
    assert item["item_id"] in request["messages"][0]["content"]


@pytest.mark.parametrize(
    "leak",
    [
        "tier3_multi_intent:000412",
        "slurp:train:000930:audio-1497264490-headset",
        "slurp:devel:001234",
        "a bare run 123456 here",
        "ace:i1:727456a71a6d123456",  # digits beyond the 12-hex handle are not masked
        "x123456 ace:i1:ab12",  # malformed handle is not masked
    ],
)
def test_prompt_detector_still_refuses_every_real_identifier_form(leak) -> None:
    assert ace._prompt_carries_sample_identifier(f"item ace:i1:727456a71a6d says {leak}")


def test_prompt_detector_masks_only_well_formed_item_ids() -> None:
    assert not ace._prompt_carries_sample_identifier("ace:i1:727456a71a6d and ace:i12:892982dbf632")
    assert not ace._prompt_carries_sample_identifier("intent alarm_set slot time 2 rows 14")


def test_i1_reflector_prompts_reproduce_from_pinned_inputs() -> None:
    """The fix touches only the check; the flown i1 prompts must be byte-identical."""

    import os

    root = os.environ.get("SPEECHRL_DATA_DIR")
    cfg = REPO_ROOT / "configs/baseline/slurp-native-stage3-tfrl-ace-reflector-i1-baseline-v1.json"
    if not root or not cfg.is_file():
        pytest.skip("data root or i1 config absent")
    block = json.loads(cfg.read_text(encoding="utf-8"))["tfrl_ace_reflector"]
    playbook = Path(root) / block["playbook"]["relpath"]
    if not playbook.is_file():
        pytest.skip("i1 playbook absent")
    rows = []
    for carrier in block["carriers"]:
        material = Path(root) / carrier["material"]["relpath"]
        if not material.is_file():
            pytest.skip("i1 material absent")
        request = ace.render_reflector_request(material, playbook, block["token_cap"])
        rows.append((carrier["scenario"], request["prompt_sha256"], request["request_sha256"]))
    assert len(rows) == 18
    assert hashlib.sha256(json.dumps(rows).encode()).hexdigest() == (
        "6b6a5d76d2d2b05ca8f38d40d4b44daa36efd892b9c53786ae6636e6dfc37d67"
    )
