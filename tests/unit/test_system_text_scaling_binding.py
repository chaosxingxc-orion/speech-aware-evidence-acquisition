"""Use the same compiled policy on larger exact prefixes without new authority."""

import copy
import hashlib
import json
import shutil

import pytest

from speech_aware_evidence_acquisition.rails import system_text_scaling as scaling
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import (
    SystemSearchArchive,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    SystemTextPolicyBundle,
    compile_system_text_policy,
)
from test_system_text_cohort import case as case, fixed_pool_case, save, ROOT
from test_system_text_policy import seed_document
from test_system_search_allocations import fixture as allocations


def prepared(case, tmp_path, size):
    base, binding, protocol, repo, data, _ = fixed_pool_case(case)
    _, _, _, extension = allocations(tmp_path / "extension")
    extension["owner"] = save(
        repo,
        extension["owner"]["relpath"],
        {
            "decision_id": 223,
            "status": "approved",
            "stage_ladder": [20, 50, 100, 200, 400],
        },
    )
    protocol["allocation_extension"] = extension
    protocol["optimization_panel"]["stages"] = ["update-4"]
    protocol["stages"][0]["stage"] = "update-4"
    protocol["updates"] = 4
    binding["stage"] = "update-4"
    full = json.loads((repo / "view.json").read_text())
    # Supply the real runtime item shape, not task answers.
    for i, item in enumerate(full["items"]):
        item.update(
            audio_seconds=1.0,
            audio_sha256="a" * 64,
            media_relpath=f"audio/{i}.flac",
            packet_id=item["sample_id"],
            sample_rate_hz=16000,
        )
    full["runtime_view_sha256"] = content_hash(
        {k: v for k, v in full.items() if k != "runtime_view_sha256"}
    )
    full_pin = save(repo, "view.json", full)
    plan = json.loads((repo / "plan.json").read_text())
    owner = json.loads((repo / plan["owner"]["relpath"]).read_text())
    owner["fixed_runtime_view"] = full_pin
    plan["owner"] = save(repo, plan["owner"]["relpath"], owner)
    plan["source_runtime_view"] = full_pin
    protocol["optimization_panel"]["plan"] = save(repo, "plan.json", plan)
    view = copy.deepcopy(full)
    view.update(count=size, items=full["items"][:size], split_identity_hash="f" * 64)
    view["runtime_view_sha256"] = content_hash(
        {k: v for k, v in view.items() if k != "runtime_view_sha256"}
    )
    binding["runtime_view"] = save(repo, f"prefix{size}.json", view)
    d = seed_document()
    d["seed_config_sha256"] = content_hash(base)
    d["knowledge"] = {
        k: base["knowledge_stores"]["slot-contracts"][k]
        for k in ("snapshot", "release")
    }
    d["role_text"] = {
        r: (
            ROOT / "configs" / base["phase_material"][r]["instruction_template"]
        ).read_text()
        for r in ("solver", "reviewer", "planner")
    }
    d["cumulative_sources"].append(
        {
            "kind": "feedback",
            "sha256": "d" * 64,
            "sample_ids": [i["sample_id"] for i in full["items"][:20]],
        }
    )
    bundle = SystemTextPolicyBundle.from_json(d)
    archive = SystemSearchArchive(data / "search")
    archive.store_policy(bundle)
    policy_file = archive.root / "policies" / (bundle.bundle_id + ".json")
    policy_binding = {
        "schema": "saea-system-text-role-binding-v1",
        "bundle_id": bundle.bundle_id,
        "bundle": {
            "relpath": policy_file.relative_to(data).as_posix(),
            "sha256": hashlib.sha256(policy_file.read_bytes()).hexdigest(),
        },
    }
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (
        LOCK_BASELINE_FRAGMENT,
        LOCK_V2_0_REVIEWER_TEMPLATE,
        LOCK_V2_1_REVIEWER_TEMPLATE,
    )

    required = [
        "configs/baseline/" + LOCK_BASELINE_FRAGMENT + ".json",
        "configs/" + LOCK_V2_0_REVIEWER_TEMPLATE[0],
        "configs/" + LOCK_V2_1_REVIEWER_TEMPLATE[0],
    ]
    required += [
        c["record"]
        for c in base["native_episode"]["consumption_module"]["components"]
        if "record" in c
    ]
    for rel in required:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    compiled = compile_system_text_policy(
        base, bundle, repo_root=ROOT, output_root=repo
    )
    return compiled, policy_binding, protocol, binding, repo, data, bundle


@pytest.mark.parametrize("measured", [False, True])
@pytest.mark.parametrize("size", [50, 100, 200])
def test_actual_policy_and_full400_artifacts_survive_prefix_binding(
    case, tmp_path, size, measured
):
    compiled, pb, protocol, binding, repo, data, bundle = prepared(case, tmp_path, size)
    if measured:
        from test_system_search_measurement import profile
        protocol["measurement_profile"] = profile()
    before = copy.deepcopy((compiled, pb, protocol, binding))
    files = {
        str(p): p.read_bytes()
        for root in (repo, data)
        for p in root.rglob("*")
        if p.is_file()
    }
    result = scaling.bind_scaling_policy(
        compiled,
        pb,
        source_protocol=protocol,
        cohort_binding=binding,
        size=size,
        repo_root=repo,
        data_root=data,
    )
    assert (compiled, pb, protocol, binding) == before
    actual = result["baseline"]
    assert actual.get("system_search_measurement") == protocol.get("measurement_profile")
    for key in (
        "phase_material",
        "phase_tools",
        "policy",
        "scorers",
        "serving_slots",
        "serving_slot_tokens",
    ):
        assert actual[key] == compiled[key]
    assert "prepared_phase_supply" not in actual and "native_contact_fit" not in actual
    assert (
        actual["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"][
            "agreement_source"
        ]["relpath"]
        == "agreement-full400.jsonl"
    )
    assert result["preparation"]["rows"] == size
    assert result["preparation"]["source_proposal_protocol_sha256"] == content_hash(
        protocol
    )
    assert result["preparation"]["bundle_id"] == bundle.bundle_id
    assert result["preparation"]["runtime_admission"] == "separate-required"
    assert result["preparation"]["contacts_added"] == 0
    assert len(protocol["stages"][0]["sample_ids"]) == 20
    assert {
        str(p): p.read_bytes()
        for root in (repo, data)
        for p in root.rglob("*")
        if p.is_file()
    } == files


@pytest.mark.parametrize(
    "fault",
    [
        "size",
        "no-scope",
        "different-prefix",
        "changed-media",
        "gold",
        "old-planner",
        "changed-role",
        "wrong-bundle",
        "source-stage",
        "pending-owner",
        "knowledge-overlap",
    ],
)
def test_prefix_binding_refuses_invalid_input_or_policy_before_preparation(
    case, tmp_path, fault
):
    c, pb, protocol, binding, repo, data, bundle = prepared(case, tmp_path, 50)
    size = 50
    if fault == "size":
        size = 51
    elif fault == "no-scope":
        protocol.pop("optimization_panel")
    elif fault == "source-stage":
        binding["stage"] = "update-5"
    elif fault == "old-planner":
        c["phase_material"]["planner"]["instruction_template"] = "probes/old.txt"
    elif fault == "changed-role":
        (
            repo / "configs" / c["phase_material"]["solver"]["instruction_template"]
        ).write_text("Deliver.")
    elif fault == "wrong-bundle":
        pb["bundle_id"] = "0" * 64
    elif fault == "pending-owner":
        ext = protocol["allocation_extension"]
        ext["owner"] = save(
            repo, ext["owner"]["relpath"], {"decision_id": 223, "status": "pending"}
        )
    elif fault == "knowledge-overlap":
        d = bundle.as_json()
        d["cumulative_sources"][0]["sample_ids"] = [
            protocol["stages"][0]["sample_ids"][0]
        ]
        replacement = SystemTextPolicyBundle.from_json(d)
        archive = SystemSearchArchive(data / "search")
        archive.store_policy(replacement)
        raw = archive.root / "policies" / (replacement.bundle_id + ".json")
        pb.update(
            bundle_id=replacement.bundle_id,
            bundle={
                "relpath": raw.relative_to(data).as_posix(),
                "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            },
        )
        c = compile_system_text_policy(
            case[0], replacement, repo_root=ROOT, output_root=repo
        )
    else:
        view = json.loads((repo / binding["runtime_view"]["relpath"]).read_text())
        if fault == "different-prefix":
            view["items"].reverse()
        elif fault == "changed-media":
            view["items"][0]["audio_sha256"] = "b" * 64
        else:
            view["items"][0]["gold"] = "forbidden"
        view["runtime_view_sha256"] = content_hash(
            {k: v for k, v in view.items() if k != "runtime_view_sha256"}
        )
        binding["runtime_view"] = save(repo, "changed-view.json", view)
    with pytest.raises((PolicyError, ValueError)):
        scaling.bind_scaling_policy(
            c,
            pb,
            source_protocol=protocol,
            cohort_binding=binding,
            size=size,
            repo_root=repo,
            data_root=data,
        )


@pytest.mark.parametrize("size", [50, 100, 200])
def test_cli_writes_create_only_preparation_and_preserves_proposal(
    case, tmp_path, capsys, size
):
    from test_system_text_search_cli import cli, write

    c, pb, protocol, binding, repo, data, bundle = prepared(case, tmp_path, size)
    output = tmp_path / "prepared.json"
    args = [
        "--archive",
        str(data / "search"),
        "bind-scaling-policy",
        "--size",
        str(size),
        "--repo-root",
        str(repo),
        "--data-root",
        str(data),
        "--output",
        str(output),
    ]
    for option, value in [
        ("compiled", c),
        ("policy-binding", pb),
        ("protocol", protocol),
        ("cohort-binding", binding),
    ]:
        args += ["--" + option, write(tmp_path / (option + ".json"), value)]
    snapshot = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    cli.main(args)
    receipt = json.loads(capsys.readouterr().out)
    result = json.loads(output.read_text())
    assert receipt == {
        "bundle_id": bundle.bundle_id,
        "rows": size,
        "contacts_added": 0,
        "runtime_admission": "separate-required",
        "preparation_sha256": content_hash(result["preparation"]),
    }
    assert result["preparation"]["source_proposal_protocol_sha256"] == content_hash(
        protocol
    )
    assert {
        str(p): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file() and p != output
    } == snapshot
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        cli.main(args)
    assert output.read_bytes() == before
    # A failed role check must leave no apparently usable preparation output.
    output.unlink()
    c["phase_material"]["planner"]["instruction_template"] = "probes/old.txt"
    write(tmp_path / "compiled.json", c)
    with pytest.raises(PolicyError):
        cli.main(args)
    assert not output.exists()
