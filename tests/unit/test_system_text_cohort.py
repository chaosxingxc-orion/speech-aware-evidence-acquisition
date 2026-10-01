"""Bind an unchanged compiled policy to its exact registered input cohort."""

import copy
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.phase_supply import load_phase_supply_specs
from speech_aware_evidence_acquisition.rails.system_text_cohort import (
    bind_system_text_cohort,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError

ROOT = Path(__file__).resolve().parents[2]


def save(root, relative, document, lines=False):
    import hashlib

    p = root / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = (
        "\n".join(json.dumps(r) for r in document) if lines else json.dumps(document)
    ).encode()
    p.write_bytes(raw)
    return {"relpath": relative, "sha256": hashlib.sha256(raw).hexdigest()}


@pytest.fixture
def case(tmp_path):
    repo, data = tmp_path / "repo", tmp_path / "data"
    base = json.loads(
        (
            ROOT
            / "configs/baseline/slurp-native-stage3-system-text-initial-seed-v2.json"
        ).read_text()
    )
    bootstrap = copy.deepcopy(base)
    ids = ["slurp:train:100:r", "slurp:train:101:r"]
    view = {
        "count": 2,
        "split_role": "discovery",
        "split_identity_hash": "a" * 64,
        "items": [{"sample_id": s} for s in ids],
    }
    view["runtime_view_sha256"] = content_hash(view)
    for store, phase, kind in [
        ("intent-boundaries", "perception", "sealed-segment-vectors"),
        ("train-exemplars", "solver", "sealed-vectors"),
    ]:
        source = save(data, store + ".jsonl", [{"id": s} for s in ids], True)
        bootstrap["knowledge_stores"][store]["phase_supply"][phase]["query_source"] = {
            **source,
            "kind": kind,
            "tool_contact_ledger_row": "TRAIN-QUERY",
            "embedded_signal": "speech: Pinned query; no transcript or target.",
        }
    bootstrap["preparation_source_receipts"] = []
    receipt = {
        "schema": "saea-phase-agreement-receipt-v1",
        "artifact_id": "FIXTURE-AGREEMENT",
        "contacts": {"model": 0, "encoder": 0, "gpu": 0, "scorer": 0},
        "artifact": {
            **save(
                data,
                "agreement.jsonl",
                [
                    {
                        "schema": "saea-phase-agreement-v1",
                        "id": s,
                        "dimension": "agreement:exemplar-intent",
                        "scores": {"intent-boundary:fixture": 1.0},
                        "vote_total": 1,
                        "self_excluded": 0,
                    }
                    for s in ids
                ],
                True,
            ),
            "rows": 2,
            "dimension": "agreement:exemplar-intent",
        },
        "derived_from": {
            "split_identity_hash": view["split_identity_hash"],
            "vote_snapshot_sha256": base["knowledge_stores"]["train-exemplars"][
                "snapshot"
            ]["sha256"],
            "target_snapshot_sha256": base["knowledge_stores"]["intent-boundaries"][
                "snapshot"
            ]["sha256"],
            "vote_store": "train-exemplars",
            "vote_phase": "solver",
            "target_store": "intent-boundaries",
            "vote_spec": load_phase_supply_specs(
                {
                    "phase_supply": bootstrap["knowledge_stores"]["train-exemplars"][
                        "phase_supply"
                    ]
                },
                default_phase_program(base["policy"]),
            )["solver"].as_json(),
        },
    }
    binding = {
        "schema": "saea-system-text-cohort-binding-v1",
        "stage": "update-1",
        "runtime_view": save(repo, "view.json", view),
        "bootstrap_baseline": save(repo, "bootstrap.json", bootstrap),
        "agreement_receipt": save(data, "receipt.json", receipt),
    }
    protocol = {
        "stages": [
            {"stage": "update-1", "sample_ids": ids, "roster_sha256": content_hash(ids)}
        ]
    }
    return base, binding, protocol, repo, data, receipt


def bind(case):
    base, binding, protocol, repo, data, _ = case
    return bind_system_text_cohort(
        base,
        binding,
        protocol=protocol,
        stage="update-1",
        repo_root=repo,
        data_root=data,
        module_repo_root=ROOT,
    )


def test_only_input_bindings_change_and_old_runtime_identities_are_removed(case):
    base, binding, _, repo, _, _ = case
    before = copy.deepcopy(base)
    result = bind(case)
    assert base == before
    assert "native_contact_fit" not in result and "prepared_phase_supply" not in result
    for key in [
        "policy",
        "scorers",
        "phase_material",
        "phase_tools",
        "serving_slots",
        "serving_slot_tokens",
    ]:
        assert result[key] == base[key]
    for key in ["slot-contracts", "train-exemplars", "intent-boundaries"]:
        assert (
            result["knowledge_stores"][key]["snapshot"]
            == base["knowledge_stores"][key]["snapshot"]
        )
    for key, phase in [
        ("train-exemplars", "solver"),
        ("intent-boundaries", "perception"),
    ]:
        old = base["knowledge_stores"][key]["phase_supply"][phase]
        new = result["knowledge_stores"][key]["phase_supply"][phase]
        assert {
            k: v
            for k, v in old.items()
            if k not in ["query_source", "agreement_source"]
        } == {
            k: v
            for k, v in new.items()
            if k not in ["query_source", "agreement_source"]
        }
    comp = next(
        c
        for c in result["native_episode"]["consumption_module"]["components"]
        if c["component_id"] == "agree-vote-seed"
    )
    assert (
        comp["params"]["agreement_source"]
        == result["knowledge_stores"]["intent-boundaries"]["phase_supply"][
            "perception"
        ]["agreement_source"]
    )


def test_bootstrap_intent_ranker_is_not_copied_into_current_policy(case):
    base, binding, _, repo, _, _ = case
    bootstrap = json.loads((repo / "bootstrap.json").read_text())
    phase = bootstrap["knowledge_stores"]["intent-boundaries"]["phase_supply"][
        "perception"
    ]
    phase["k"] = 8
    phase["rank_weights"]["w_agree"] = 0.0
    binding["bootstrap_baseline"] = save(repo, "bootstrap.json", bootstrap)
    result = bind(case)
    actual = result["knowledge_stores"]["intent-boundaries"]["phase_supply"][
        "perception"
    ]
    original = base["knowledge_stores"]["intent-boundaries"]["phase_supply"][
        "perception"
    ]
    assert actual["k"] == original["k"]
    assert actual["rank_weights"] == original["rank_weights"]


@pytest.mark.parametrize(
    "mutation",
    [
        "stage",
        "roster",
        "pool",
        "vote",
        "partial",
        "contact",
        "query-missing",
        "query-hash",
    ],
)
def test_refuse_cross_cohort_or_changed_vote_inputs(case, mutation):
    base, binding, protocol, repo, data, receipt = case
    if mutation == "stage":
        binding["stage"] = "selection"
    elif mutation == "roster":
        protocol["stages"][0]["sample_ids"].reverse()
    elif mutation == "pool":
        receipt["derived_from"]["vote_snapshot_sha256"] = "0" * 64
    elif mutation == "vote":
        receipt["derived_from"]["vote_spec"]["k"] = 2
    elif mutation == "partial":
        receipt["artifact"]["rows"] = 1
    elif mutation == "contact":
        receipt["contacts"]["model"] = 1
    elif mutation == "query-missing":
        d = json.loads((repo / "bootstrap.json").read_text())
        d["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"][
            "query_source"
        ].update(save(data, "different.jsonl", [{"id": "slurp:train:100:r"}], True))
        binding["bootstrap_baseline"] = save(repo, "bootstrap.json", d)
        receipt["derived_from"]["vote_spec"]["query_source"] = d["knowledge_stores"][
            "train-exemplars"
        ]["phase_supply"]["solver"]["query_source"]
        binding["agreement_receipt"] = save(data, "receipt.json", receipt)
    else:
        (data / "train-exemplars.jsonl").write_text("changed")
    if mutation in ["pool", "vote", "partial", "contact"]:
        binding["agreement_receipt"] = save(data, "receipt.json", receipt)
    with pytest.raises((PolicyError, ValueError)):
        bind(case)


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong-vote-rows",
        "changed-vote-rule",
        "wrong-release",
        "non-train",
        "view-hash",
        "query-duplicate",
        "declared-module",
    ],
)
def test_refuse_validly_hashed_but_wrong_runtime_inputs(case, mutation):
    base, binding, protocol, repo, data, receipt = case
    if mutation == "wrong-vote-rows":
        rows = [
            json.loads(line)
            for line in (data / "agreement.jsonl").read_text().splitlines()
        ]
        rows[0]["id"] = "slurp:train:999:r"
        receipt["artifact"].update(save(data, "agreement.jsonl", rows, True))
        binding["agreement_receipt"] = save(data, "receipt.json", receipt)
    elif mutation == "changed-vote-rule":
        base["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]["k"] = 2
    elif mutation == "wrong-release":
        base["knowledge_stores"]["intent-boundaries"]["release"]["sha256"] = "0" * 64
    elif mutation in ["non-train", "view-hash"]:
        view = json.loads((repo / "view.json").read_text())
        view["items"][0]["sample_id"] = "slurp:test:100:r"
        if mutation == "non-train":
            protocol["stages"][0]["sample_ids"][0] = "slurp:test:100:r"
            protocol["stages"][0]["roster_sha256"] = content_hash(
                protocol["stages"][0]["sample_ids"]
            )
            view["runtime_view_sha256"] = content_hash(
                {k: v for k, v in view.items() if k != "runtime_view_sha256"}
            )
        binding["runtime_view"] = save(repo, "view.json", view)
    elif mutation == "query-duplicate":
        d = json.loads((repo / "bootstrap.json").read_text())
        d["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"][
            "query_source"
        ].update(
            save(
                data,
                "duplicate.jsonl",
                [{"id": s} for s in protocol["stages"][0]["sample_ids"]] * 2,
                True,
            )
        )
        binding["bootstrap_baseline"] = save(repo, "bootstrap.json", d)
    else:
        base["native_episode"]["consumption_module"]["components"] = [
            c
            for c in base["native_episode"]["consumption_module"]["components"]
            if c["component_id"] != "agree-vote-seed"
        ]
    with pytest.raises((PolicyError, ValueError)):
        bind(case)
