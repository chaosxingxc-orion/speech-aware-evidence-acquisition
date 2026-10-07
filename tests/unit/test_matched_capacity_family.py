"""Qualify complete operational evidence without changing original controls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_context_structural_entry import (
    qualify_matched_capacity_family,
)


def example(graph_rows=4):
    """Use real pinned config identities and synthetic operational evidence only."""
    root = Path(__file__).resolve().parents[2]
    populations, pins, members, receipts, terminals, graph_hashes = {}, [], [], {}, {}, {}
    for arm in ("fixed-parent", "multi-parent"):
        relpath = f"configs/experiments/slurp-system-context-algorithm-contrast-n20-{arm}-v1.json"
        raw = (root / relpath).read_bytes()
        config = json.loads(raw)
        populations[arm] = config
        pin = {"relpath": relpath, "sha256": hashlib.sha256(raw).hexdigest()}
        pins.append({"arm": arm, "pin": pin})
        for cohort in config["cohorts"]:
            roster = cohort["sample_ids"]
            for member_id in cohort["control_ids"] + cohort["candidate_ids"]:
                label = arm + "-" + member_id
                member = {"label": label, "run_id": "run-" + label, "attempt_id": "attempt-" + label,
                          "contact_cap": 297, "composed_config_hash": "config-" + label,
                          "experiment_population": deepcopy(pin), "expected_rows": len(roster),
                          "graph_rows": graph_rows, "plan": {"relpath": label + "-plan.json", "sha256": "c" * 64}}
                members.append(member)
                graph_hashes[label] = "graph-" + label
                output = {"every_request_fits": True, "generation_contacts": 0,
                          "scientific_results_read": False, "contacts": 120, "rows": [], "proofs": []}
                for mode in ("new-acquisition", "wide-automatic-supply"):
                    output["proofs"].append({"mode": mode, "terminal_rows": graph_rows})
                    for index, sample in enumerate(roster[:graph_rows]):
                        output["rows"].append({"mode": mode, "sample_id": sample, "captured_request_index": index,
                                               "fits": True, "maximum_completion_tokens": 512,
                                               "additional_structural_reserve_tokens": 2048,
                                               "slot_tokens": 24576, "margin_after_structural_reserve": 100})
                receipts[label] = {"contact_class": "tokenizer", "output": output, "output_sha256": content_hash(output),
                                   "inputs": {"source_commit": "frozen-source", "config_hash": member["composed_config_hash"],
                                              "graph_config_hash": graph_hashes[label], "roster": list(roster),
                                              "output_reserve": 512, "structural_reserve": 2048}}
                terminals[label] = {"exit_code": 0, "generation_contacts": 0, "scorer_contacts": 0,
                                    "members": [{"label": label, "run_id": member["run_id"], "attempt_id": member["attempt_id"],
                                                 "exit_code": 0, "lease_exit_code": 0}]}
    reg = {"schema": "saea-configured-partitioned-capacity-entry-v1", "status": "ROOT-ADMITTED",
           "experiment_populations": deepcopy(pins), "worker": "original-worker", "worker_commit": "frozen-source",
           "sampling": deepcopy(populations["fixed-parent"]["sampling"]), "members": members,
           "resource_policy": {"start_gib": 20, "floor_gib": 8}, "native_prefix_affinity": "OFF",
           "budget": {"generation_contacts": 0, "scorer_contacts": 0,
                      "tokenizer_endpoint_caps": {m["label"]: m["contact_cap"] for m in members},
                      "tokenizer_endpoints_total": sum(m["contact_cap"] for m in members)}}
    finished = {"exit_code": 0, "generation_contacts": 0, "scorer_contacts": 0, "failure": None,
                "members": [{"label": m["label"], "run_id": m["run_id"], "attempt_id": m["attempt_id"],
                             "exit_code": 0, "observer_exit_code": 0} for m in members]}
    return {"populations": populations, "population_pins": pins, "registration": reg,
            "original_registration": deepcopy(reg), "finished": finished, "windows_exit": {"exit_code": 0},
            "receipts": receipts, "member_terminals": terminals, "graph_config_hashes": graph_hashes,
            "output_reserve": 512, "structural_reserve": 2048, "slot_tokens": 24576}


def rehash(args, label="fixed-parent-seed"):
    record = args["receipts"][label]
    record["output_sha256"] = content_hash(record["output"])


@pytest.mark.parametrize("graph_rows", [3, 4])
def test_exact_whole_family_preserves_original_roles_and_evidence(graph_rows):
    args = example(graph_rows)
    before = deepcopy(args)
    result = qualify_matched_capacity_family(**args)
    assert args == before
    expected = [m["label"] for m in args["registration"]["members"]]
    assert [m["label"] for m in result["members"]] == expected
    assert len(result["members"]) == 20
    assert [m["label"] for m in result["members"] if m["member_role"] == "control"] == [
        "fixed-parent-seed", "fixed-parent-seed-aa", "multi-parent-seed", "multi-parent-seed-aa"]
    assert all("candidate_id" not in m for m in result["members"])
    assert result["tokenizer_endpoints"] == 2400
    assert result["generation_contacts"] == result["scorer_contacts"] == 0
    assert result["runtime_admission"] is False and result["root_review_required"] is True
    for key, source in (("registration_sha256", "registration"), ("finished_sha256", "finished"),
                        ("windows_exit_sha256", "windows_exit"), ("capacity_receipts_sha256", "receipts"),
                        ("member_terminals_sha256", "member_terminals")):
        assert result[key] == content_hash(args[source])
    for member in result["members"]:
        assert member["capacity_output_sha256"] == args["receipts"][member["label"]]["output_sha256"]
    result["experiment_populations"][0]["pin"]["sha256"] = "changed"
    assert args == before


@pytest.mark.parametrize("label", ["fixed-parent-seed", "fixed-parent-seed-aa", "multi-parent-seed", "multi-parent-seed-aa"])
def test_missing_control_cannot_qualify_even_with_consistently_trimmed_registration(label):
    args = example()
    for key in ("registration", "original_registration"):
        args[key]["members"] = [m for m in args[key]["members"] if m["label"] != label]
        args[key]["budget"]["tokenizer_endpoint_caps"].pop(label)
        args[key]["budget"]["tokenizer_endpoints_total"] -= 297
    args["finished"]["members"] = [m for m in args["finished"]["members"] if m["label"] != label]
    for key in ("receipts", "member_terminals", "graph_config_hashes"):
        args[key].pop(label)
    with pytest.raises(ValueError, match="Ordered matched capacity members"):
        qualify_matched_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda a: a["population_pins"].reverse(),
    lambda a: a["population_pins"].pop(),
    lambda a: a["populations"].update(extra=a["populations"]["fixed-parent"]),
    lambda a: a["registration"]["experiment_populations"].reverse(),
    lambda a: a["registration"]["members"][0].update(experiment_population=a["population_pins"][1]["pin"]),
    lambda a: a["registration"]["members"].reverse(),
    lambda a: a["registration"]["members"].append(a["registration"]["members"][0]),
    lambda a: a["registration"]["members"].pop(),
    lambda a: a["finished"]["members"].reverse(),
    lambda a: a["finished"]["members"].append(a["finished"]["members"][0]),
    lambda a: a["finished"]["members"].pop(),
    lambda a: a["receipts"].pop("multi-parent-seed"),
    lambda a: a["receipts"].update(extra=a["receipts"]["fixed-parent-seed"]),
    lambda a: a["member_terminals"].pop("fixed-parent-seed-aa"),
    lambda a: a["member_terminals"].update(extra=a["member_terminals"]["fixed-parent-seed"]),
    lambda a: a["graph_config_hashes"].update(extra="extra"),
    lambda a: a["graph_config_hashes"].pop("fixed-parent-seed"),
    lambda a: a["registration"].update(worker_commit="other-source"),
    lambda a: a["registration"].update(worker="other-worker"),
    lambda a: a["registration"].update(status="PENDING"),
    lambda a: a["registration"]["sampling"].update(seed=2),
    lambda a: a["registration"]["resource_policy"].update(start_gib=18),
    lambda a: a["registration"]["members"][0].update(run_id="replacement"),
    lambda a: a["registration"]["members"][0].update(attempt_id="replacement"),
    lambda a: a["registration"]["members"][0]["plan"].update(sha256="other-plan"),
    lambda a: a["registration"]["members"][0].update(contact_cap=1),
    lambda a: a["registration"]["members"][0].update(expected_rows=1),
    lambda a: a["registration"]["members"][0].update(graph_rows=2),
    lambda a: a["registration"]["budget"].update(tokenizer_endpoints_total=1),
    lambda a: a["registration"].update(extra="unregistered-data"),
    lambda a: a["finished"].update(exit_code=1),
    lambda a: a["windows_exit"].update(exit_code=1),
    lambda a: a["finished"].update(generation_contacts=1),
    lambda a: a["finished"].update(scorer_contacts=1),
    lambda a: a["finished"].update(failure={"message": "failed"}),
    lambda a: a["finished"]["members"][0].update(observer_exit_code=1),
    lambda a: a["finished"]["members"][0].update(run_id="other-run"),
    lambda a: a["finished"]["members"][0].update(attempt_id="other-attempt"),
    lambda a: a["member_terminals"]["fixed-parent-seed"].update(exit_code=1),
    lambda a: a["member_terminals"]["fixed-parent-seed"].update(generation_contacts=1),
    lambda a: a["member_terminals"]["fixed-parent-seed"].update(scorer_contacts=1),
    lambda a: a["member_terminals"]["fixed-parent-seed"]["members"].clear(),
    lambda a: a["member_terminals"]["fixed-parent-seed"]["members"].append({}),
    lambda a: a["member_terminals"]["fixed-parent-seed"]["members"][0].update(lease_exit_code=1),
    lambda a: a["member_terminals"]["fixed-parent-seed"]["members"][0].update(attempt_id="other"),
    lambda a: a["receipts"]["fixed-parent-seed"].update(output_sha256="invalid"),
    lambda a: a["receipts"]["fixed-parent-seed"].update(contact_class="generation"),
    lambda a: a["receipts"]["fixed-parent-seed"]["inputs"].update(source_commit="other-source"),
    lambda a: a["receipts"]["fixed-parent-seed"]["inputs"].update(config_hash="other-config"),
    lambda a: a["receipts"]["fixed-parent-seed"]["inputs"].update(graph_config_hash="other-graph"),
    lambda a: a["receipts"]["fixed-parent-seed"]["inputs"]["roster"].reverse(),
    lambda a: a["receipts"]["fixed-parent-seed"]["inputs"]["roster"].pop(),
    lambda a: a["receipts"]["fixed-parent-seed"]["inputs"].update(output_reserve=1),
    lambda a: a["receipts"]["fixed-parent-seed"]["inputs"].update(structural_reserve=1),
])
def test_fail_closed_on_changed_or_incomplete_family(change):
    args = example()
    change(args)
    with pytest.raises(ValueError):
        qualify_matched_capacity_family(**args)


@pytest.mark.parametrize("key,value", [("contacts", 298), ("contacts", True), ("contacts", 0),
                                      ("generation_contacts", 1), ("generation_contacts", False),
                                      ("scorer_contacts", 1), ("scorer_contacts", False),
                                      ("every_request_fits", False), ("scientific_results_read", True), ("rows", [])])
def test_invalid_rehashed_capacity_output(key, value):
    args = example()
    args["receipts"]["fixed-parent-seed"]["output"][key] = value
    rehash(args)
    with pytest.raises(ValueError):
        qualify_matched_capacity_family(**args)


@pytest.mark.parametrize("key,value", [("fits", False), ("maximum_completion_tokens", 1),
                                      ("additional_structural_reserve_tokens", 1), ("slot_tokens", 1),
                                      ("margin_after_structural_reserve", -1),
                                      ("margin_after_structural_reserve", float("nan")),
                                      ("margin_after_structural_reserve", True),
                                      ("sample_id", "outside-roster"), ("mode", "unexpected"),
                                      ("captured_request_index", 2), ("captured_request_index", False)])
def test_invalid_rehashed_measured_row(key, value):
    args = example()
    args["receipts"]["fixed-parent-seed"]["output"]["rows"][0][key] = value
    rehash(args)
    with pytest.raises(ValueError):
        qualify_matched_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda o: o["proofs"].pop(),
    lambda o: o["proofs"].reverse(),
    lambda o: o["proofs"][0].update(terminal_rows=3),
    lambda o: o["proofs"][0].update(terminal_rows=True),
    lambda o: o["rows"].reverse(),
    lambda o: o["rows"].pop(0),
    lambda o: o["rows"].append(o["rows"][0]),
    lambda o: o["rows"][0].update(sample_id=o["rows"][1]["sample_id"]),
    lambda o: o["rows"][4].update(sample_id="slurp:train:010065:audio-1501756518"),
])
def test_incomplete_or_extra_graph_proof(change):
    args = example()
    change(args["receipts"]["fixed-parent-seed"]["output"])
    rehash(args)
    with pytest.raises(ValueError):
        qualify_matched_capacity_family(**args)


@pytest.mark.parametrize("key,value", [("contact_cap", True), ("expected_rows", True), ("expected_rows", 19),
                                      ("graph_rows", True), ("graph_rows", 0), ("graph_rows", 21)])
def test_invalid_original_declared_counts(key, value):
    args = example()
    # A trusted anchor still has to satisfy the config and operational evidence.
    args["registration"]["members"][0][key] = value
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError):
        qualify_matched_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda a: a.update(population_pins=None),
    lambda a: a.update(finished=None),
    lambda a: a["registration"].pop("worker_commit"),
    lambda a: a["receipts"]["fixed-parent-seed"].update(output=None),
    lambda a: a["member_terminals"].update({"fixed-parent-seed": None}),
    lambda a: a["finished"]["members"][0].update(observer_exit_code=False),
    lambda a: a["windows_exit"].update(exit_code=False),
    lambda a: a["finished"].update(generation_contacts=False),
    lambda a: a["populations"]["fixed-parent"]["cohorts"][0]["control_ids"].pop(),
    lambda a: a["populations"]["multi-parent"]["execution"].update(slot_count=2),
])
def test_malformed_evidence_fails_closed(change):
    args = example()
    change(args)
    with pytest.raises(ValueError):
        qualify_matched_capacity_family(**args)


def test_swapped_member_pins_fail_even_in_the_original_anchor():
    args = example()
    args["registration"]["members"][0]["experiment_population"] = deepcopy(args["population_pins"][1]["pin"])
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError, match="Member population pin"):
        qualify_matched_capacity_family(**args)


def test_consistent_identity_replacement_cannot_rewrite_original_registration():
    args = example()
    label = "fixed-parent-seed"
    args["registration"]["members"][0]["run_id"] = "replacement"
    args["finished"]["members"][0]["run_id"] = "replacement"
    args["member_terminals"][label]["members"][0]["run_id"] = "replacement"
    with pytest.raises(ValueError, match="original complete registration"):
        qualify_matched_capacity_family(**args)
