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
    "partition,role,scorer",
    [
        ("devel", "dev", "slurp-slu-official-train"),
        ("test", "dev", "slurp-slu-official-train"),
        ("train", "dev", "slurp-slu-official-train"),
        ("devel", "discovery", "slurp-slu-official-train"),
        ("devel", "dev", "slurp-slu-official-test"),
    ],
)
def test_dev_cohort_uses_only_registered_devel_inputs_without_changing_policy(
    case, partition, role, scorer
):
    base, binding, protocol, repo, data, receipt = case
    view = json.loads((repo / "view.json").read_text())
    ids = [
        row["sample_id"].replace(":train:", f":{partition}:") for row in view["items"]
    ]
    view["items"] = [{"sample_id": s} for s in ids]
    view["split_role"] = role
    base["scorers"] = [scorer, "cost"]
    view.pop("runtime_view_sha256")
    view["runtime_view_sha256"] = content_hash(view)
    binding.update(stage="dev", runtime_view=save(repo, "dev-view.json", view))
    protocol["stages"] = [
        {"stage": "dev", "sample_ids": ids, "roster_sha256": content_hash(ids)}
    ]
    bootstrap = json.loads((repo / "bootstrap.json").read_text())
    for name, phase in (
        ("train-exemplars", "solver"),
        ("intent-boundaries", "perception"),
    ):
        query = bootstrap["knowledge_stores"][name]["phase_supply"][phase][
            "query_source"
        ]
        query.update(save(data, f"dev-{name}.jsonl", [{"id": s} for s in ids], True))
    binding["bootstrap_baseline"] = save(repo, "dev-bootstrap.json", bootstrap)
    receipt["derived_from"]["vote_spec"]["query_source"] = copy.deepcopy(
        bootstrap["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"][
            "query_source"
        ]
    )
    agreement = [
        json.loads(line) for line in (data / "agreement.jsonl").read_text().splitlines()
    ]
    for row, identity in zip(agreement, ids, strict=True):
        row["id"] = identity
    receipt["artifact"].update(save(data, "dev-agreement.jsonl", agreement, True))
    binding["agreement_receipt"] = save(data, "dev-receipt.json", receipt)
    kwargs = dict(
        protocol=protocol,
        stage="dev",
        repo_root=repo,
        data_root=data,
        module_repo_root=ROOT,
    )
    before = copy.deepcopy(base)
    if partition != "devel" or role != "dev" or scorer != "slurp-slu-official-train":
        with pytest.raises(PolicyError, match="cohort|scoring"):
            bind_system_text_cohort(base, binding, **kwargs)
        return
    from test_system_text_policy import seed_document
    from speech_aware_evidence_acquisition.rails.system_text_policy import (
        SystemTextPolicyBundle,
        compile_system_text_policy,
    )

    document = seed_document()
    document["seed_config_sha256"] = content_hash(base)
    document["role_text"] = {
        r: (
            ROOT / "configs" / base["phase_material"][r]["instruction_template"]
        ).read_text()
        for r in ("solver", "reviewer", "planner")
    }
    bundle = SystemTextPolicyBundle.from_json(document)
    # Real shared compiler and real cohort binding; synthetic query/artifact bytes.
    compiled = compile_system_text_policy(
        base, bundle, repo_root=ROOT, output_root=repo / "worker"
    )
    result = bind_system_text_cohort(compiled, binding, **kwargs)
    replica = bind_system_text_cohort(
        compile_system_text_policy(
            base, bundle, repo_root=ROOT, output_root=repo / "worker"
        ),
        binding,
        **kwargs,
    )
    assert result == replica
    assert base == before
    for key in ("policy", "phase_material", "phase_tools", "serving_slot_tokens"):
        assert result[key] == compiled[key]
    assert result["scorers"] == ["slurp-slu-official", "cost"]
    assert (
        result["knowledge_stores"]["slot-contracts"]
        == base["knowledge_stores"]["slot-contracts"]
    )
    assert "prepared_phase_supply" not in result and "native_contact_fit" not in result


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


def fixed_pool_case(case):
    """Reuse the owner's pinned400 inputs instead of creating new vote bytes."""
    from test_system_optimization import fixture as optimization_fixture

    base, binding, _, repo, data, receipt = case
    protocol, ids = optimization_fixture(repo)
    full = json.loads((repo / "view.json").read_text())
    full.update(split_role="discovery", split_identity_hash="4" * 64)
    full["runtime_view_sha256"] = content_hash(full)
    full_pin = save(repo, "view.json", full)
    owner_path = (
        "docs/receipts/owner/2026-10-02-decision224-fixed400-context-postcall.json"
    )
    owner = json.loads((repo / owner_path).read_text())
    owner["fixed_runtime_view"] = full_pin
    owner_pin = save(repo, owner_path, owner)
    plan = json.loads((repo / "plan.json").read_text())
    plan.update(owner=owner_pin, source_runtime_view=full_pin)
    protocol["optimization_panel"]["plan"] = save(repo, "plan.json", plan)
    protocol["stages"][0]["roster_sha256"] = content_hash(ids[:20])
    view = {
        "items": full["items"][:20],
        "count": 20,
        "split_role": "discovery",
        "split_identity_hash": "2" * 64,
    }
    view["runtime_view_sha256"] = content_hash(view)
    bootstrap = json.loads((repo / "bootstrap.json").read_text())
    for name, phase in (
        ("train-exemplars", "solver"),
        ("intent-boundaries", "perception"),
    ):
        query = bootstrap["knowledge_stores"][name]["phase_supply"][phase][
            "query_source"
        ]
        query.update(
            save(data, f"{name}-full400.jsonl", [{"id": sid} for sid in ids], True)
        )
    receipt["derived_from"]["split_identity_hash"] = full["split_identity_hash"]
    receipt["derived_from"]["vote_spec"]["query_source"] = copy.deepcopy(
        bootstrap["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"][
            "query_source"
        ]
    )
    row = json.loads((data / "agreement.jsonl").read_text().splitlines()[0])
    receipt["artifact"].update(
        save(
            data, "agreement-full400.jsonl", [{**row, "id": sid} for sid in ids], True
        ),
        rows=400,
    )
    binding.update(
        stage="update-3",
        runtime_view=save(repo, "prefix20.json", view),
        bootstrap_baseline=save(repo, "bootstrap-full400.json", bootstrap),
        agreement_receipt=save(data, "full400-receipt.json", receipt),
    )
    return base, binding, protocol, repo, data, receipt


def bind_prefix(case):
    base, binding, protocol, repo, data, _ = case
    return bind_system_text_cohort(
        base,
        binding,
        protocol=protocol,
        stage="update-3",
        repo_root=repo,
        data_root=data,
        module_repo_root=ROOT,
    )


def test_fixed_prefix_reuses_full_pool_agreement_without_rebuilding(case):
    c = fixed_pool_case(case)
    base, _, _, repo, data, _ = c
    before = {
        str(p): p.read_bytes()
        for root in (repo, data)
        for p in root.rglob("*")
        if p.is_file()
    }
    result = bind_prefix(c)
    agreement = result["knowledge_stores"]["intent-boundaries"]["phase_supply"][
        "perception"
    ]["agreement_source"]
    assert agreement["relpath"] == "agreement-full400.jsonl"
    assert result["phase_material"] == base["phase_material"]
    assert {
        str(p): p.read_bytes()
        for root in (repo, data)
        for p in root.rglob("*")
        if p.is_file()
    } == before
    pins = result["preparation_source_receipts"]
    assert any(
        p.get("relpath") == "plan.json" and p["root"] == "repository" for p in pins
    )


@pytest.mark.parametrize(
    "fault",
    [
        "no-scope",
        "other-pool",
        "missing-row",
        "duplicate-row",
        "wrong-prefix",
        "wrong-identity",
    ],
)
def test_prefix_reuse_never_admits_arbitrary_supersets(case, fault):
    c = fixed_pool_case(case)
    _, binding, protocol, repo, data, receipt = c
    if fault == "no-scope":
        protocol.pop("optimization_panel")
    elif fault == "wrong-prefix":
        view = json.loads((repo / "prefix20.json").read_text())
        view["items"].reverse()
        view["runtime_view_sha256"] = content_hash(
            {k: v for k, v in view.items() if k != "runtime_view_sha256"}
        )
        binding["runtime_view"] = save(repo, "prefix20.json", view)
        protocol["stages"][0].update(
            sample_ids=[r["sample_id"] for r in view["items"]],
            roster_sha256=content_hash([r["sample_id"] for r in view["items"]]),
        )
    elif fault == "wrong-identity":
        receipt["derived_from"]["split_identity_hash"] = "f" * 64
        binding["agreement_receipt"] = save(data, "full400-receipt.json", receipt)
    else:
        rows = [
            json.loads(line)
            for line in (data / "agreement-full400.jsonl").read_text().splitlines()
        ]
        if fault == "other-pool":
            rows[-1]["id"] = "slurp:train:999999:audio"
        elif fault == "missing-row":
            rows.pop()
        else:
            rows[-1] = rows[-2]
        receipt["artifact"].update(save(data, "agreement-full400.jsonl", rows, True))
        binding["agreement_receipt"] = save(data, "full400-receipt.json", receipt)
    from speech_aware_evidence_acquisition.rails.phase_supply import PhaseSupplyError

    with pytest.raises((PolicyError, PhaseSupplyError)):
        bind_prefix(c)


@pytest.mark.parametrize("fault", [None, "no-extension", "no-panel", "wrong-round", "pending-owner"])
def test_extra_round_cohort_requires_exact_owner_and_fixed_pool(case, tmp_path, fault):
    from test_system_search_allocations import fixture as allocation_fixture
    base, binding, protocol, repo, data, _ = fixed_pool_case(case)
    _, owner_repo, _, extension = allocation_fixture(tmp_path / "extension")
    owner = json.loads((owner_repo / extension["owner"]["relpath"]).read_text())
    if fault == "pending-owner":
        owner["status"] = "pending"
    extension["owner"] = save(repo, extension["owner"]["relpath"], owner)
    protocol["allocation_extension"] = extension
    protocol["optimization_panel"]["stages"] = ["update-4"]
    protocol["stages"][0]["stage"] = "update-4"
    binding["stage"] = "update-4"
    if fault == "no-extension":
        del protocol["allocation_extension"]
    elif fault == "no-panel":
        del protocol["optimization_panel"]
    elif fault == "wrong-round":
        binding["stage"] = "update-5"
    def run():
        return bind_system_text_cohort(base, binding, protocol=protocol, stage=binding["stage"],
            repo_root=repo, data_root=data, module_repo_root=ROOT)
    if fault:
        with pytest.raises(PolicyError):
            run()
    else:
        result = run()
        assert result["phase_material"] == base["phase_material"]
        assert result["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["agreement_source"]["relpath"] == "agreement-full400.jsonl"


def test_measured_protocol_reaches_compiled_runtime_without_policy_change(case):
    from test_system_search_measurement import profile
    base, _, protocol, *_ = case
    legacy = bind(case)
    base_before = copy.deepcopy(base)
    protocol["measurement_profile"] = profile()
    result = bind(case)
    assert result["system_search_measurement"] == profile()
    assert {k: v for k, v in result.items() if k != "system_search_measurement"} == legacy
    assert base == base_before
    result["system_search_measurement"]["queue_depth"] = 12
    assert protocol["measurement_profile"] == profile()


@pytest.mark.parametrize("fault", ["null", "slots", "queue", "conflict", "unregistered", "geometry"])
def test_measured_cohort_refuses_undeclared_or_incompatible_schedule(case, fault):
    from test_system_search_measurement import profile
    base, _, protocol, *_ = case
    protocol["measurement_profile"] = profile()
    if fault == "null":
        protocol["measurement_profile"] = None
    elif fault == "slots":
        protocol["measurement_profile"]["slot_count"] = 8
    elif fault == "queue":
        protocol["measurement_profile"]["queue_depth"] = 2
    elif fault == "conflict":
        base["system_search_measurement"] = {**profile(), "queue_depth": 16}
    elif fault == "geometry":
        del base["serving_slots"]
    else:
        del protocol["measurement_profile"]
        base["system_search_measurement"] = profile()
    with pytest.raises(PolicyError):
        bind(case)


def test_matching_registered_measurement_is_idempotent(case):
    from test_system_search_measurement import profile
    base, _, protocol, *_ = case
    base["system_search_measurement"] = profile()
    protocol["measurement_profile"] = profile()
    assert bind(case)["system_search_measurement"] == profile()
