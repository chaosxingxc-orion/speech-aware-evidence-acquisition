"""Reject partial or mismatched capacity families before structural registration."""
import copy
import pytest
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_context_structural_entry import qualify_capacity_family


def example(size=3):
    pin = {"relpath": "population.json", "sha256": "a" * 64}
    labels = [f"candidate-{i}" for i in range(size)]
    cfg = {"cohorts": [{"candidate_ids": labels, "sample_ids": ["s1", "s2"]}], "sampling": {"temperature": 0, "seed": 7}}
    members = [{"label": x, "run_id": "run-" + x, "attempt_id": "attempt-" + x, "contact_cap": 3, "composed_config_hash": "config-" + x, "experiment_population": pin} for x in labels]
    reg = {"status": "ROOT-ADMITTED", "experiment_population": pin, "worker_commit": "commit", "sampling": cfg["sampling"], "members": members, "budget": {"generation_contacts": 0, "scorer_contacts": 0, "tokenizer_endpoint_caps": {x: 3 for x in labels}, "tokenizer_endpoints_total": 3 * size}}
    exits = [{"label": m["label"], "run_id": m["run_id"], "attempt_id": m["attempt_id"], "exit_code": 0, "lease_exit_code": 0} for m in members]
    finished = {"exit_code": 0, "members": exits, "generation_contacts": 0, "scorer_contacts": 0}
    windows = {"exit_code": 0}
    receipts = {}
    for m in members:
        output = {"every_request_fits": True, "generation_contacts": 0, "scientific_results_read": False, "contacts": 3, "rows": [{"fits": True, "maximum_completion_tokens": 512, "additional_structural_reserve_tokens": 2048, "slot_tokens": 24576, "margin_after_structural_reserve": 100}]}
        receipts[m["label"]] = {"contact_class": "tokenizer", "inputs": {"source_commit": "commit", "config_hash": m["composed_config_hash"], "graph_config_hash": "graph-" + m["label"], "roster": ["s2", "s1"], "output_reserve": 512, "structural_reserve": 2048}, "output": output, "output_sha256": content_hash(output)}
    return cfg, pin, reg, finished, windows, receipts


def qualify(args):
    return qualify_capacity_family(*args, output_reserve=512, structural_reserve=2048, slot_tokens=24576, graph_config_hashes={m["label"]: "graph-" + m["label"] for m in args[2]["members"]})


@pytest.mark.parametrize("size", [1, 2, 5, 8])
def test_configured_sizes_preserved(size):
    result = qualify(example(size))
    assert len(result["members"]) == size
    assert result["tokenizer_endpoints"] == size * 3
    assert result["root_review_required"] is True
    assert result["runtime_admission"] is False


@pytest.mark.parametrize("mutation", [
    lambda a: a[2]["members"].reverse(),
    lambda a: a[3]["members"].pop(),
    lambda a: a[3]["members"].reverse(),
    lambda a: a[5].pop("candidate-0"),
    lambda a: a[5].update(extra=a[5]["candidate-0"]),
    lambda a: a[2].update(status="HELD"),
    lambda a: a[2].update(experiment_population={"sha256": "wrong"}),
    lambda a: a[2]["sampling"].update(seed=9),
    lambda a: a[2]["budget"].update(tokenizer_endpoints_total=1),
    lambda a: a[2]["budget"]["tokenizer_endpoint_caps"].update({"candidate-0": 8}),
    lambda a: a[2]["members"][0].update(contact_cap=True),
    lambda a: a[3].update(exit_code=1),
    lambda a: a[4].update(exit_code=1),
    lambda a: a[3].update(generation_contacts=1),
    lambda a: a[3].update(scorer_contacts=1),
    lambda a: a[3]["members"][0].update(lease_exit_code=1),
    lambda a: a[3]["members"][0].update(attempt_id="wrong"),
    lambda a: a[5]["candidate-0"].update(output_sha256="wrong"),
    lambda a: a[5]["candidate-0"]["inputs"].update(source_commit="wrong"),
    lambda a: a[5]["candidate-0"]["inputs"].update(config_hash="wrong"),
    lambda a: a[5]["candidate-0"]["inputs"].update(roster=["s1", "s1"]),
    lambda a: a[5]["candidate-0"]["inputs"].update(output_reserve=1),
    lambda a: a[5]["candidate-0"].update(contact_class="model"),
])
def test_reject_incomplete_or_mismatched_family(mutation):
    args = copy.deepcopy(example())
    # Keep fixture dictionaries independent, as persisted JSON documents are.
    args = tuple(copy.deepcopy(x) for x in args)
    mutation(args)
    with pytest.raises(ValueError):
        qualify(args)


@pytest.mark.parametrize("key,value", [("every_request_fits", False), ("generation_contacts", 1), ("scientific_results_read", True), ("contacts", 4), ("contacts", True), ("rows", [])])
def test_reject_rehashed_invalid_output(key, value):
    args = example()
    rec = args[5]["candidate-0"]
    rec["output"][key] = value
    rec["output_sha256"] = content_hash(rec["output"])
    with pytest.raises(ValueError): qualify(args)


@pytest.mark.parametrize("key,value", [("fits",False), ("maximum_completion_tokens",1), ("additional_structural_reserve_tokens",0), ("slot_tokens",100), ("margin_after_structural_reserve",-1), ("margin_after_structural_reserve",float("nan")), ("margin_after_structural_reserve",True)])
def test_reject_invalid_measured_row(key,value):
    args=example(); rec=args[5]["candidate-0"]
    rec["output"]["rows"][0][key]=value
    rec["output_sha256"]=content_hash(rec["output"])
    with pytest.raises(ValueError): qualify(args)


def test_no_input_mutation():
    args=example(); original=copy.deepcopy(args)
    qualify(args)
    assert args==original

@pytest.mark.parametrize("change", [
    lambda a: a[2].pop("worker_commit"),
    lambda a: a[0].update(cohorts=[]),
    lambda a: a[0]["cohorts"][0]["candidate_ids"].append("candidate-0"),
    lambda a: a[2]["members"][0].update(experiment_population={}),
    lambda a: a[3]["members"][0].update(exit_code=False),
    lambda a: a[3].update(generation_contacts=False),
    lambda a: a[5]["candidate-0"]["inputs"].update(graph_config_hash="other-graph"),
])
def test_reject_malformed_or_unbound_graph(change):
    args=tuple(copy.deepcopy(x) for x in example())
    change(args)
    with pytest.raises(ValueError): qualify(args)
