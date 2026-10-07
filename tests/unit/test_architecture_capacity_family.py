"""Complete manual architecture capacity qualification, using synthetic evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_context_structural_entry import (
    qualify_architecture_capacity_family,
)


def example():
    root = Path(__file__).resolve().parents[2]
    relpath = "configs/experiments/slurp-simple-consumption-architecture-n20-v1.json"
    raw = (root / relpath).read_bytes()
    population = json.loads(raw)
    pin = {"relpath": relpath, "sha256": hashlib.sha256(raw).hexdigest()}
    source = "a" * 40
    members, receipts, terminals, graph_hashes, policies = [], {}, {}, {}, {}
    for identity in population["architecture"]["members"]:
        label = identity["member_id"]
        roster = next(c["sample_ids"] for c in population["cohorts"]
                      if c["cohort_id"] == identity["cohort_id"])
        policies[label] = (root / identity["execution_config"]["relpath"]).read_bytes()
        episode = json.loads(policies[label])["native_episode"]
        off = identity["active_roles"] == ["perception", "solver"]
        tool = episode.get("solver_tool_access") == "bounded-slot-lookup-v1"
        profile = "review-off-v1" if off else "legacy-four-path-v1"
        member = {"label": label, "member_id": label, "population_cohort": identity["cohort_id"],
                  "execution_config": deepcopy(identity["execution_config"]),
                  "execution_identity_sha256": content_hash(identity),
                  "model_per_trajectory": identity["model_per_trajectory"],
                  "rehearsal_profile": profile, "run_id": "run-" + label,
                  "attempt_id": "attempt-" + label, "contact_cap": 500,
                  "composed_config_hash": content_hash({"fit": label}),
                  "experiment_population": deepcopy(pin), "expected_rows": len(roster), "graph_rows": 4,
                  "graph_sample_ids": list(roster[:4])}
        members.append(member)
        graph_hashes[label] = content_hash({"graph": label})
        output = {"schema": "saea-native-graph-capacity-v1", "every_request_fits": True,
                  "generation_contacts": 0, "scientific_results_read": False, "contacts": 120,
                  "selected_slots": [[900, "slot-one", "value-one"], [800, "slot-two", "value-two"]],
                  "maximum_speech_tokens_over_roster": 1000,
                  "rows": [], "proofs": []}
        inputs = {"schema": "saea-native-graph-capacity-input-v1", "source_commit": source,
                  "config_hash": member["composed_config_hash"], "graph_config_hash": graph_hashes[label],
                  "roster": list(roster), "output_reserve": 512, "structural_reserve": 2048}
        if off:
            inputs["rehearsal_profile"] = output["rehearsal_profile"] = profile
            inputs["registered_contact_cap"] = member["contact_cap"]
            inputs["endpoint_budget"] = {"profile": profile, "graph_rows": 4,
                "supply_modes": 2 if tool else 1, "captured_requests": 22 if tool else 8,
                "ranking_tokenizer_endpoints": 100, "padding_tokenizer_endpoints": 60 if tool else 18,
                "request_measurement_endpoints": 66 if tool else 24, "contact_cap": 227 if tool else 143}
            output["endpoint_budget"] = deepcopy(inputs["endpoint_budget"])
        modes = ["new-acquisition", "wide-automatic-supply"] if not off or tool else ["wide-automatic-supply"]
        counts = [4, 5, 5, 8] if not off else ([2, 3, 3, 3] if tool else [2] * 4)
        for mode in modes:
            proof = {"mode": mode, "terminal_rows": 4, "synthetic_completions": sum(counts),
                     "requests_sha256": content_hash([label, mode]),
                     "candidate_intents": ["synthetic-one", "synthetic-two", "synthetic-three"],
                     "synthetic_response_tokens": {r: 400 for r in
                        (["perception", "solver"] if off else ["perception", "reviewer", "solver"])}}
            if off:
                if tool:
                    proof["synthetic_response_tokens"]["solver_tool_call"] = 400
                proof.update(synthetic_tool_calls=2 if tool else 0,
                             post_tool_final_requests=3 if tool else 0,
                             accepted_final_request_sha256={s: content_hash([label, mode, s]) for s in roster[:4]})
            output["proofs"].append(proof)
            index = 0
            for sample, count in zip(roster[:4], counts, strict=True):
                for _ in range(count):
                    output["rows"].append({"mode": mode, "sample_id": sample,
                        "captured_request_index": index, "fits": True, "maximum_completion_tokens": 512,
                        "additional_structural_reserve_tokens": 2048, "slot_tokens": 24576,
                        "margin_after_structural_reserve": 100, "margin_tokens": 2148,
                        "request_body_sha256": content_hash([label, mode, index]), "media_count": 1,
                        "speech_tokens": 1000, "text_tokens": 20914, "special_tokens": 2,
                        "required_tokens": 22428, "fit_multiple": 1.0})
                    index += 1
        receipts[label] = {"contact_class": "tokenizer", "inputs": inputs,
                           "output": output, "output_sha256": content_hash(output)}
        terminals[label] = {"exit_code": 0, "generation_contacts": 0, "scorer_contacts": 0,
            "members": [{"label": label, "run_id": member["run_id"], "attempt_id": member["attempt_id"],
                         "exit_code": 0, "lease_exit_code": 0}]}
    source_check = {"source_commit": source, "experiment_population": deepcopy(pin), "exit_code": 0,
                    "generation_contacts": 0, "tokenizer_contacts": 0, "scorer_contacts": 0}
    registration = {"schema": "saea-architecture-capacity-entry-v1", "status": "ROOT-ADMITTED",
        "experiment_population": deepcopy(pin), "worker": "synthetic-frozen-worker", "worker_commit": source,
        "source_check_sha256": content_hash(source_check), "sampling": deepcopy(population["sampling"]),
        "execution": deepcopy(population["execution"]), "members": members,
        "budget": {"generation_contacts": 0, "scorer_contacts": 0,
                   "tokenizer_endpoint_caps": {m["label"]: m["contact_cap"] for m in members},
                   "tokenizer_endpoints_total": sum(m["contact_cap"] for m in members)}}
    finished = {"exit_code": 0, "generation_contacts": 0, "scorer_contacts": 0, "failure": None,
        "members": [{"label": m["label"], "run_id": m["run_id"], "attempt_id": m["attempt_id"],
                     "exit_code": 0, "observer_exit_code": 0} for m in members]}
    return dict(population=population, population_pin=pin, registration=registration,
                original_registration=deepcopy(registration), finished=finished, windows_exit={"exit_code": 0},
                receipts=receipts, member_terminals=terminals, graph_config_hashes=graph_hashes,
                policy_config_bytes=policies, source_check=source_check,
                output_reserve=512, structural_reserve=2048, slot_tokens=24576)


def rehash(args):
    for receipt in args["receipts"].values():
        receipt["output_sha256"] = content_hash(receipt["output"])


def test_complete_family_preserves_controls_source_and_no_admission():
    args = example()
    before = deepcopy(args)
    result = qualify_architecture_capacity_family(**args)
    assert args == before
    assert result["schema"] == "saea-architecture-capacity-family-review-v1"
    assert [m["label"] for m in result["members"]] == ["seed", "seed-aa", "review-off", "solver-lookup"]
    assert [m["member_role"] for m in result["members"]] == ["control", "control", "candidate", "candidate"]
    assert [m["measured_requests"] for m in result["members"]] == [44, 44, 8, 22]
    assert [m["model_per_trajectory"] for m in result["members"]] == [13, 13, 2, 3]
    assert result["tokenizer_endpoints"] == 480
    assert result["runtime_admission"] is False and result["root_review_required"] is True
    assert result["generation_contacts"] == result["scorer_contacts"] == 0
    for field, source in (("registration_sha256", "registration"), ("finished_sha256", "finished"),
                          ("windows_exit_sha256", "windows_exit"), ("capacity_receipts_sha256", "receipts"),
                          ("member_terminals_sha256", "member_terminals"), ("source_check_sha256", "source_check")):
        assert result[field] == content_hash(args[source])
    result["members"][0]["execution_config"]["sha256"] = "changed"
    assert args == before


@pytest.mark.parametrize("field", ["receipts", "member_terminals", "graph_config_hashes", "policy_config_bytes"])
@pytest.mark.parametrize("label", ["seed", "seed-aa", "review-off", "solver-lookup"])
def test_every_member_is_required(field, label):
    args = example()
    del args[field][label]
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda a: a["registration"]["members"].reverse(),
    lambda a: a["registration"]["members"].pop(0),
    lambda a: a["registration"].update(status="HELD"),
    lambda a: a["registration"].update(schema="saea-configured-partitioned-capacity-entry-v1"),
    lambda a: a["registration"]["members"][0].update(execution_config=a["registration"]["members"][2]["execution_config"]),
    lambda a: a["registration"]["members"][0].update(execution_identity_sha256="b" * 64),
    lambda a: a["registration"]["members"][2].update(model_per_trajectory=13),
    lambda a: a["registration"]["members"][2].update(rehearsal_profile="legacy-four-path-v1"),
    lambda a: a["registration"]["members"][0].update(contact_cap=True),
    lambda a: a["registration"]["members"][0].update(expected_rows=4),
    lambda a: a["registration"]["members"][0].update(graph_rows=3),
    lambda a: a["registration"]["members"][0].update(run_id="run-seed-aa"),
    lambda a: a["registration"]["members"][0].update(population_cohort="other"),
    lambda a: a["registration"]["budget"].update(tokenizer_endpoints_total=1),
    lambda a: a["registration"]["sampling"].update(seed=1),
    lambda a: a["registration"]["execution"].update(slot_count=1),
])
def test_even_consistently_rewritten_registration_cannot_override_population(change):
    args = example()
    change(args)
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda a: a["registration"].update(worker="different-worker"),
    lambda a: a["finished"].update(exit_code=1),
    lambda a: a["windows_exit"].update(exit_code=False),
    lambda a: a["finished"].update(failure="partial"),
    lambda a: a["finished"].update(generation_contacts=True),
    lambda a: a["finished"]["members"].reverse(),
    lambda a: a["finished"]["members"][0].update(observer_exit_code=1),
    lambda a: a["finished"]["members"][0].update(attempt_id="other"),
    lambda a: a["member_terminals"]["seed"].update(exit_code=1),
    lambda a: a["member_terminals"]["seed"]["members"][0].update(lease_exit_code=1),
    lambda a: a["member_terminals"]["seed"]["members"].clear(),
    lambda a: a["policy_config_bytes"].update(seed=b"{}"),
    lambda a: a["source_check"].update(source_commit="b" * 40),
    lambda a: a["source_check"].update(exit_code=1),
    lambda a: a["source_check"].update(tokenizer_contacts=1),
    lambda a: a["source_check"].update(experiment_population={}),
    lambda a: a["receipts"]["seed"]["inputs"].update(source_commit="b" * 40),
    lambda a: a["receipts"]["seed"]["inputs"].update(config_hash="b" * 64),
    lambda a: a["receipts"]["seed"]["inputs"].update(graph_config_hash="b" * 64),
    lambda a: a["receipts"]["seed"]["inputs"]["roster"].reverse(),
    lambda a: a["receipts"]["review-off"]["inputs"].pop("rehearsal_profile"),
    lambda a: a["receipts"]["solver-lookup"]["output"].update(rehearsal_profile="legacy-four-path-v1"),
    lambda a: a["receipts"]["seed"]["output"].update(contacts=501),
    lambda a: a["receipts"]["seed"]["output"].update(scorer_contacts=True),
    lambda a: a["receipts"]["seed"]["output"].update(scientific_results_read=True),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(maximum_completion_tokens=511),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(margin_after_structural_reserve=-1),
    lambda a: a["receipts"]["seed"]["output"]["proofs"].pop(),
    lambda a: a["receipts"]["seed"]["output"]["proofs"][0].update(synthetic_completions=21),
    lambda a: a["receipts"]["review-off"]["output"]["rows"].pop(),
    lambda a: a["receipts"]["solver-lookup"]["output"]["proofs"][0].update(synthetic_tool_calls=1),
    lambda a: a["receipts"]["solver-lookup"]["output"]["proofs"][0].update(post_tool_final_requests=2),
    lambda a: a["receipts"]["review-off"]["output"]["proofs"][0]["accepted_final_request_sha256"].popitem(),
    lambda a: a["receipts"]["seed"]["output"]["proofs"][0].update(requests_sha256="bad"),
    lambda a: a["receipts"]["seed"]["output"]["proofs"][0].update(candidate_intents=["same"] * 3),
    lambda a: a["receipts"]["seed"]["output"]["proofs"][0]["synthetic_response_tokens"].update(solver=513),
    lambda a: a["receipts"]["seed"]["output"]["rows"][1].update(captured_request_index=0),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(sample_id="slurp:train:unknown"),
    lambda a: a.update(receipts=None),
])
def test_incomplete_crossbound_or_malformed_evidence_refuses(change):
    args = example()
    change(args)
    if args["receipts"] is not None:
        rehash(args)
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("key,value", [
    ("profile", "legacy-four-path-v1"), ("graph_rows", True), ("supply_modes", 1),
    ("captured_requests", 8), ("ranking_tokenizer_endpoints", -1),
    ("padding_tokenizer_endpoints", 61), ("request_measurement_endpoints", 65),
    ("contact_cap", 228), ("extra", 0),
])
def test_consistently_corrupted_endpoint_budget_refuses(key, value):
    args = example()
    record = args["receipts"]["solver-lookup"]
    record["inputs"]["endpoint_budget"][key] = value
    record["output"]["endpoint_budget"] = deepcopy(record["inputs"]["endpoint_budget"])
    rehash(args)
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda r: r["inputs"].pop("endpoint_budget"),
    lambda r: r["inputs"].update(registered_contact_cap=501),
    lambda r: r["output"]["endpoint_budget"].update(contact_cap=500),
    lambda r: r["output"].update(contacts=228),
])
def test_missing_crossbound_or_exceeded_endpoint_budget_refuses(change):
    args = example()
    change(args["receipts"]["solver-lookup"])
    rehash(args)
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda a: a["receipts"]["seed"]["output"].pop("selected_slots"),
    lambda a: a["receipts"]["seed"]["output"]["selected_slots"].pop(),
    lambda a: a["receipts"]["seed"]["output"].update(maximum_speech_tokens_over_roster=999),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].pop("request_body_sha256"),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(text_tokens=10),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(required_tokens=10),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(margin_tokens=100),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(margin_after_structural_reserve=10),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(fit_multiple=True),
    lambda a: a["receipts"]["seed"]["output"]["rows"][0].update(media_count=2),
])
def test_incomplete_or_inconsistent_measurement_refuses(change):
    args = example()
    change(args)
    rehash(args)
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda a: a["source_check"].update(exit_code=1),
    lambda a: a["source_check"].update(source_commit="b" * 40),
    lambda a: a["source_check"].update(tokenizer_contacts=1),
    lambda a: a["source_check"].update(experiment_population={}),
])
def test_rehashed_unsuccessful_or_wrong_source_check_is_still_rejected(change):
    args = example()
    change(args)
    args["registration"]["source_check_sha256"] = content_hash(args["source_check"])
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("field", ["population", "composed", "graph"])
def test_consistently_bound_malformed_pin_or_config_hash_refuses(field):
    args = example()
    if field == "population":
        args["population_pin"]["sha256"] = "malformed"
        args["registration"]["experiment_population"] = deepcopy(args["population_pin"])
        args["source_check"]["experiment_population"] = deepcopy(args["population_pin"])
        args["registration"]["source_check_sha256"] = content_hash(args["source_check"])
        for member in args["registration"]["members"]:
            member["experiment_population"] = deepcopy(args["population_pin"])
    elif field == "composed":
        args["registration"]["members"][0]["composed_config_hash"] = ""
        args["receipts"]["seed"]["inputs"]["config_hash"] = ""
    else:
        args["graph_config_hashes"]["seed"] = ""
        args["receipts"]["seed"]["inputs"]["graph_config_hash"] = ""
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


def interleave_captures(args, branch_order):
    """Preserve every per-sample request while varying parallel completion order."""
    for member in args["registration"]["members"]:
        output = args["receipts"][member["label"]]["output"]
        reordered = []
        for proof in output["proofs"]:
            queues = [[r for r in output["rows"] if r["mode"] == proof["mode"] and r["sample_id"] == sample]
                      for sample in member["graph_sample_ids"]]
            captured = []
            while any(queues):
                for index in branch_order:
                    if queues[index]:
                        captured.append(queues[index].pop(0))
            for index, row in enumerate(captured):
                row["captured_request_index"] = index
            reordered.extend(captured)
        output["rows"] = reordered
    rehash(args)


@pytest.mark.parametrize("branch_order", [(0, 1, 2, 3), (3, 1, 0, 2)])
def test_interleaved_requests_use_registered_branch_order_not_first_capture(branch_order):
    args = example()
    interleave_captures(args, branch_order)
    before = deepcopy(args)
    result = qualify_architecture_capacity_family(**args)
    assert [m["measured_requests"] for m in result["members"]] == [44, 44, 8, 22]
    assert args == before and result["runtime_admission"] is False


@pytest.mark.parametrize("label", ["seed", "review-off", "solver-lookup"])
def test_interleaved_wrong_per_sample_count_refuses_even_with_complete_total(label):
    args = example()
    interleave_captures(args, (3, 1, 0, 2))
    output = args["receipts"][label]["output"]
    rows = output["rows"]
    rows[0]["sample_id"] = rows[1]["sample_id"]
    rehash(args)
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("change", [
    lambda m: m.pop("graph_sample_ids"),
    lambda m: m["graph_sample_ids"].pop(),
    lambda m: m["graph_sample_ids"].reverse(),
    lambda m: m["graph_sample_ids"].__setitem__(0, m["graph_sample_ids"][1]),
    lambda m: m["graph_sample_ids"].__setitem__(0, "slurp:train:unknown"),
])
def test_missing_malformed_or_wrong_branch_roster_refuses(change):
    args = example()
    change(args["registration"]["members"][0])
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


def runtime_order_example():
    args = example()
    for member in args["registration"]["members"]:
        label = member["label"]
        runtime = list(args["receipts"][label]["inputs"]["roster"])
        runtime[0], runtime[1] = runtime[1], runtime[0]
        graph = list(member["graph_sample_ids"])
        graph[0], graph[1] = graph[1], graph[0]
        member.update(runtime_sample_ids=runtime, runtime_graph_sample_ids=graph)
        args["receipts"][label]["inputs"]["roster"] = list(runtime)
        remap = dict(zip(member["graph_sample_ids"], graph, strict=True))
        for row in args["receipts"][label]["output"]["rows"]:
            row["sample_id"] = remap[row["sample_id"]]
    args["source_check"]["members"] = [
        {**deepcopy(m), "graph_config_hash": args["graph_config_hashes"][m["label"]]}
        for m in args["registration"]["members"]]
    args["registration"]["source_check_sha256"] = content_hash(args["source_check"])
    args["original_registration"] = deepcopy(args["registration"])
    rehash(args)
    return args


def test_explicit_runtime_order_preserves_configured_membership_and_accepts_real_branch_order():
    args = runtime_order_example()
    result = qualify_architecture_capacity_family(**args)
    for registered, qualified in zip(args["registration"]["members"], result["members"], strict=True):
        assert qualified["runtime_sample_ids"] == registered["runtime_sample_ids"]
        assert qualified["runtime_graph_sample_ids"] == registered["runtime_graph_sample_ids"]
        assert qualified["graph_sample_ids"] == registered["graph_sample_ids"]


@pytest.mark.parametrize("field", ["runtime_sample_ids", "runtime_graph_sample_ids"])
@pytest.mark.parametrize("defect", ["duplicate", "omitted", "foreign", "tampered_order", "missing"])
def test_explicit_runtime_order_refuses_invalid_or_unbound_rosters(field, defect):
    args = runtime_order_example()
    member = args["registration"]["members"][0]
    if defect == "duplicate":
        member[field][0] = member[field][1]
    elif defect == "omitted":
        member[field].pop()
    elif defect == "foreign":
        member[field][0] = "foreign-sample"
    elif defect == "tampered_order":
        member[field][0], member[field][1] = member[field][1], member[field][0]
    else:
        del member[field]
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("defect", ["missing", "repeated", "reordered", "equal_count_permutation"])
def test_frozen_production_runtime_order_binding_cannot_be_spoofed(defect):
    args = runtime_order_example()
    checked = args["source_check"]["members"]
    if defect == "missing":
        checked.pop()
    elif defect == "repeated":
        checked[1] = deepcopy(checked[0])
    elif defect == "reordered":
        checked.reverse()
    else:
        ids = checked[-1]["runtime_graph_sample_ids"]
        ids[1], ids[2] = ids[2], ids[1]
    args["registration"]["source_check_sha256"] = content_hash(args["source_check"])
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)


def test_source_only_runtime_binding_cannot_downgrade_to_legacy():
    args = runtime_order_example()
    for member in args["registration"]["members"]:
        del member["runtime_sample_ids"], member["runtime_graph_sample_ids"]
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError, match="runtime order"):
        qualify_architecture_capacity_family(**args)


@pytest.mark.parametrize("field", ["run_id", "attempt_id", "composed_config_hash", "graph_config_hash", "graph_sample_ids"])
def test_runtime_order_source_check_binds_exact_member_custody(field):
    args = runtime_order_example()
    checked = args["source_check"]["members"][0]
    checked[field] = list(reversed(checked[field])) if field == "graph_sample_ids" else "different-source-member"
    args["registration"]["source_check_sha256"] = content_hash(args["source_check"])
    args["original_registration"] = deepcopy(args["registration"])
    with pytest.raises(ValueError):
        qualify_architecture_capacity_family(**args)
