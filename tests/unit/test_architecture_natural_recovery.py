"""Natural plan pairs after one honest capacity recovery; synthetic records only."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_context_structural_entry import (
    architecture_capacity_recovery_binding,
    qualify_architecture_capacity_recovery,
)
from test_architecture_capacity_recovery import fixture as recovery_fixture
from test_architecture_natural_registration import (
    LABELS,
    ROOT,
    fixture as natural_fixture,
    invoke,
    write,
)

SCHEMA = "saea-architecture-recovered-capacity-prerequisite-v1"


def absolute(root, pin):
    return {"path": str(root / pin["relpath"]), "sha256": pin["sha256"]}


def fixture(tmp_path, label="solver-lookup"):
    natural = natural_fixture(tmp_path, label)
    a, old, decision, compatible = recovery_fixture()
    pin = natural["values"]["experiment_population"]
    a["population"] = json.loads((ROOT / pin["relpath"]).read_bytes())
    a["population_pin"] = deepcopy(pin)
    original = json.loads((tmp_path / "capacity/registration-v1.json").read_bytes())
    old["registration"] = original
    old["source_check"] = json.loads(
        (tmp_path / "capacity/frozen-check.json").read_bytes()
    )
    new = a["recovery"]
    for member in original["members"]:
        label = member["label"]
        member["capacity"] = "original-capacity-" + label
        a["graph_config_hashes"]["original"][label] = member["graph_config_hash"]
        a["policy_config_bytes"][label] = (
            ROOT / member["execution_config"]["relpath"]
        ).read_bytes()
        if label in old["receipts"]:
            old["receipts"][label]["inputs"]["graph_config_hash"] = member[
                "graph_config_hash"
            ]
    member = dict(
        deepcopy(original["members"][-1]),
        run_id="new-solver-run",
        attempt_id="new-solver-attempt",
        capacity="new-solver-capacity",
        composed_config_hash="e" * 64,
    )
    new["registration"] = dict(
        deepcopy(original),
        schema="saea-architecture-capacity-recovery-entry-v1",
        worker="new-frozen-worker",
        worker_commit="b" * 40,
        new_receipt_root=str(tmp_path / "recovery"),
        members=[member],
        budget=deepcopy(new["registration"]["budget"]),
    )
    new["source_check"] = dict(
        deepcopy(old["source_check"]), commit="b" * 40, source_commit="b" * 40
    )
    new["receipts"]["solver-lookup"]["inputs"].update(
        graph_config_hash=member["graph_config_hash"],
        config_hash=member["composed_config_hash"],
    )
    a["graph_config_hashes"]["recovery"] = {
        "solver-lookup": member["graph_config_hash"]
    }
    for row in (
        new["finished"]["members"][0],
        new["member_terminals"]["solver-lookup"]["members"][0],
    ):
        row.update(run_id=member["run_id"], attempt_id=member["attempt_id"])
    decision["experiment_population"] = compatible["experiment_population"] = deepcopy(
        pin
    )
    compatible["unchanged_members"] = {
        m["label"]: {
            k: deepcopy(m[k])
            for k in (
                "execution_identity_sha256",
                "graph_config_hash",
                "graph_sample_ids",
                "model_per_trajectory",
            )
        }
        for m in original["members"][:3]
    }
    case = dict(
        natural=natural,
        arguments=a,
        original=old,
        decision=decision,
        compatible=compatible,
        root=tmp_path,
    )
    seal(case, recompute=True)
    return case


def seal(case, *, recompute=False):
    """Write synthetic records and their independent pins, without runtime calls."""
    root, a, old = case["root"], case["arguments"], case["original"]
    new, decision, compatible = a["recovery"], case["decision"], case["compatible"]

    def save(rel, doc):
        return absolute(root, write(root, rel, doc))

    def records(envelope):
        reg = envelope["registration"]
        entry = Path(reg["new_receipt_root"]).relative_to(root).as_posix()
        source_pin = save(entry + "/frozen-check.json", envelope["source_check"])
        reg["frozen_preflight_receipts"] = [source_pin]
        reg["source_check_sha256"] = content_hash(envelope["source_check"])
        envelope["original_registration"] = deepcopy(reg)
        envelope["pins"] = {
            key: save(entry + "/" + name, envelope[key])
            for key, name in (
                ("registration", "registration-v1.json"),
                ("finished", "capacity-finished.json"),
                ("windows_exit", "capacity-task-exit.json"),
            )
        }
        for label, value in envelope["member_terminals"].items():
            save(entry + "/" + label + "-capacity-finished.json", value)
        for label, value in envelope["receipts"].items():
            save(entry + "/" + label + "/request-fit-v1.json", value)

    records(old)
    reg = new["registration"]
    a["original_evidence_pin"] = save("capacity/original-evidence.json", old)
    a["original_evidence_bytes"] = Path(a["original_evidence_pin"]["path"]).read_bytes()
    reg["original_evidence"] = a["original_evidence_pin"]
    for key in ("registration", "finished", "windows_exit"):
        reg["original_" + key] = old["pins"][key]
    compatible["source_commits"] = dict(
        original=old["registration"]["worker_commit"], recovery=reg["worker_commit"]
    )
    a["source_compatibility_pin"] = save(
        "recovery/source-compatibility.json", compatible
    )
    a["source_compatibility_bytes"] = Path(
        a["source_compatibility_pin"]["path"]
    ).read_bytes()
    reg["source_compatibility"] = a["source_compatibility_pin"]
    failed = root / "capacity/failed-contacts.jsonl"
    failed.write_bytes(a["failed_contacts_bytes"])
    a["failed_contacts_pin"] = dict(
        path=str(failed), sha256=hashlib.sha256(failed.read_bytes()).hexdigest()
    )
    decision.update(
        original_evidence_sha256=content_hash(old),
        original_registration_sha256=content_hash(old["registration"]),
        recovery_binding_sha256=content_hash(
            architecture_capacity_recovery_binding(reg)
        ),
        source_compatibility=a["source_compatibility_pin"],
        failed_contacts=a["failed_contacts_pin"],
    )
    a["root_disposition_pin"] = save("recovery/root-disposition.json", decision)
    a["root_disposition_bytes"] = Path(a["root_disposition_pin"]["path"]).read_bytes()
    reg["root_recovery_disposition"] = a["root_disposition_pin"]
    records(new)
    recovery_pin = save("recovery/recovery-evidence.json", new)
    if recompute:
        case["result"] = qualify_architecture_capacity_recovery(**a)
    qualification = dict(
        schema="saea-simple-consumption-capacity-recovery-root-qualification-v1",
        result=case["result"],
        runtime_admission=False,
        read_authorized=False,
    )
    pins = dict(
        original_evidence=a["original_evidence_pin"],
        recovery_evidence=recovery_pin,
        root_disposition=a["root_disposition_pin"],
        source_compatibility=a["source_compatibility_pin"],
        failed_contacts=a["failed_contacts_pin"],
        qualification=save("recovery/capacity-qualified-v1.json", qualification),
    )
    prerequisite = dict(
        schema=SCHEMA,
        **{
            key: {
                "relpath": Path(p["path"]).relative_to(root).as_posix(),
                "sha256": p["sha256"],
            }
            for key, p in pins.items()
        },
    )
    for plan in case["natural"]["registered_plans"]:
        plan["capacity_prerequisite"] = deepcopy(prerequisite)


@pytest.mark.parametrize(
    "label,source,generation,fit",
    [
        ("seed", "original", 52, 208),
        ("seed-aa", "original", 52, 208),
        ("review-off", "original", 8, 32),
        ("solver-lookup", "recovery", 12, 48),
    ],
)
def test_recovered_prerequisite_keeps_real_member_sources_and_paired_caps(
    tmp_path, label, source, generation, fit
):
    case = fixture(tmp_path, label)
    before = deepcopy(case)
    result = invoke(case["natural"])
    registration = (
        case["original"] if source == "original" else case["arguments"]["recovery"]
    )["registration"]
    assert result["capacity_registration_sha256"] == content_hash(registration)
    assert result["capacity_source_commit"] == registration["worker_commit"]
    assert result["generation_cap"] == generation and result["fit_cap"] == fit
    assert result["capacity_source"] == source and result["capacity_source_exits"] == [
        1,
        0,
    ]
    assert result["failed_attempt_tokenizer_endpoints"] == 143
    assert result["runtime_admission"] is False and result["read_authorized"] is False
    assert case == before


@pytest.mark.parametrize(
    "field",
    [
        "original_evidence",
        "recovery_evidence",
        "root_disposition",
        "source_compatibility",
        "failed_contacts",
        "qualification",
    ],
)
def test_each_recovery_prerequisite_is_required_and_raw_hash_bound(tmp_path, field):
    case = fixture(tmp_path)
    pin = case["natural"]["registered_plans"][0]["capacity_prerequisite"][field]
    with (tmp_path / pin["relpath"]).open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ValueError):
        invoke(case["natural"])


@pytest.mark.parametrize(
    "fault",
    [
        "original_success",
        "partial",
        "missing_aa",
        "wrong_receipt_source",
        "wrong_lease",
        "changed_graph",
        "changed_policy",
        "source_failed",
        "source_commit",
        "missing_disposition",
        "missing_fit",
        "wrong_fit_cap",
        "no_schema",
        "unknown_schema",
        "extra_prerequisite",
        "wrong_result",
    ],
)
def test_recovered_natural_prerequisite_refuses_partial_fabricated_or_crossbound_evidence(
    tmp_path, fault
):
    case = fixture(tmp_path)
    old, new = case["original"], case["arguments"]["recovery"]
    if fault == "original_success":
        old["finished"].update(exit_code=0, failure=None)
        old["windows_exit"]["exit_code"] = 0
    elif fault == "partial":
        new["finished"]["members"] = []
    elif fault == "missing_aa":
        del old["receipts"]["seed-aa"]
    elif fault == "wrong_receipt_source":
        new["receipts"]["solver-lookup"]["inputs"]["source_commit"] = "c" * 40
    elif fault == "wrong_lease":
        new["member_terminals"]["solver-lookup"]["members"][0]["lease_exit_code"] = 1
    elif fault == "changed_graph":
        old["registration"]["members"][0]["graph_config_hash"] = "c" * 64
    elif fault == "changed_policy":
        old["registration"]["members"][0]["execution_config"]["sha256"] = "c" * 64
    elif fault == "source_failed":
        new["source_check"]["passed"] = False
    elif fault == "source_commit":
        new["source_check"]["commit"] = "c" * 40
    elif fault == "wrong_result":
        case["result"]["spent_tokenizer_endpoints"] += 1
    seal(case)
    plans = case["natural"]["registered_plans"]
    if fault == "missing_fit":
        plans.pop()
    elif fault == "wrong_fit_cap":
        plans[1]["execution_plan"]["planned_model_calls"] += 1
    else:
        for plan in plans:
            p = plan["capacity_prerequisite"]
            if fault == "missing_disposition":
                del p["root_disposition"]
            elif fault == "no_schema":
                del p["schema"]
            elif fault == "unknown_schema":
                p["schema"] = "future"
            elif fault == "extra_prerequisite":
                p["extra"] = {}
    with pytest.raises((ValueError, KeyError)):
        invoke(case["natural"])


@pytest.mark.parametrize("fault", ["hash", "roster", "policy"])
@pytest.mark.parametrize("label", LABELS)
def test_every_capacity_graph_is_independently_composed_before_natural_admission(
    tmp_path, monkeypatch, label, fault
):
    from speech_aware_evidence_acquisition.rails import (
        architecture_natural_registration as binding,
    )

    case = fixture(tmp_path)
    original = binding.compose

    def changed(*parts):
        config = original(*parts)
        if (
            parts[-1]
            == f"slurp-native-stage3-simple-consumption-{label}-engineering-graph-v2"
        ):
            if fault == "hash":
                return replace(config, config_hash="c" * 64)
            values = deepcopy(config.values)
            if fault == "roster":
                values["populations"][0]["ids"].reverse()
            else:
                values["native_episode"] = {}
            return replace(config, values=values)
        return config

    monkeypatch.setattr(binding, "compose", changed)
    with pytest.raises(ValueError):
        invoke(case["natural"])


@pytest.mark.parametrize(
    "rel",
    [
        "capacity/registration-v1.json",
        "capacity/capacity-task-exit.json",
        "capacity/seed-aa-capacity-finished.json",
        "capacity/seed/request-fit-v1.json",
        "recovery/frozen-check.json",
        "recovery/solver-lookup/request-fit-v1.json",
    ],
)
def test_raw_envelopes_cannot_replace_independently_read_operational_files(
    tmp_path, rel
):
    case = fixture(tmp_path)
    (tmp_path / rel).write_text("{}", encoding="utf-8")
    with pytest.raises((ValueError, KeyError)):
        invoke(case["natural"])


def test_recovered_path_does_not_contact_a_service_or_mutate_evidence(
    tmp_path, monkeypatch
):
    import subprocess

    case = fixture(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def refuse(*args, **kwargs):
        raise AssertionError("natural registration attempted a subprocess")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)
    assert invoke(case["natural"])["runtime_admission"] is False
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "fault",
    [
        "no_data_root",
        "outside_entry",
        "malformed_record_pin",
        "outside_record",
        "relative_record",
        "wrong_record_path",
        "changed_original_copy",
        "outside_source",
        "qualification_schema",
        "qualification_admission",
        "qualification_read",
        "qualification_path",
    ],
)
def test_recovery_file_custody_and_qualification_scope_fail_closed(tmp_path, fault):
    case = fixture(tmp_path)
    natural = case["natural"]
    p = natural["registered_plans"][0]["capacity_prerequisite"]
    key = "qualification" if fault.startswith("qualification") else "recovery_evidence"
    doc = json.loads((tmp_path / p[key]["relpath"]).read_bytes())
    if fault == "no_data_root":
        natural["data_root"] = None
    elif fault == "outside_entry":
        doc["registration"]["new_receipt_root"] = str(tmp_path.parent)
    elif fault == "malformed_record_pin":
        doc["pins"]["registration"]["extra"] = 0
    elif fault == "outside_record":
        doc["pins"]["registration"]["path"] = str(tmp_path.parent / "foreign.json")
    elif fault == "relative_record":
        doc["pins"]["registration"]["path"] = "registration-v1.json"
    elif fault == "wrong_record_path":
        doc["pins"]["registration"]["path"] = str(tmp_path / "foreign.json")
    elif fault == "changed_original_copy":
        doc["original_registration"]["worker_commit"] = "c" * 40
    elif fault == "outside_source":
        doc["registration"]["frozen_preflight_receipts"][0]["path"] = str(
            tmp_path / "foreign-source.json"
        )
        doc["original_registration"] = deepcopy(doc["registration"])
        path = (
            Path(doc["pins"]["registration"]["path"]).relative_to(tmp_path).as_posix()
        )
        doc["pins"]["registration"] = absolute(
            tmp_path, write(tmp_path, path, doc["registration"])
        )
    elif fault == "qualification_schema":
        doc["schema"] = "foreign"
    elif fault == "qualification_admission":
        doc["runtime_admission"] = True
    elif fault == "qualification_read":
        doc["read_authorized"] = True
    path = (
        "other-qualified.json" if fault == "qualification_path" else p[key]["relpath"]
    )
    replacement = write(tmp_path, path, doc)
    for plan in natural["registered_plans"]:
        plan["capacity_prerequisite"][key] = deepcopy(replacement)
    with pytest.raises(ValueError):
        invoke(natural)


@pytest.mark.parametrize("label", LABELS)
def test_shared_flight_gate_accepts_only_the_complete_recovered_natural_pair(
    tmp_path, monkeypatch, label
):
    from test_flight_registration_check import gate

    args = fixture(tmp_path, label)["natural"]
    cell, values = args["cell"], args["values"]
    directory = tmp_path / "packages" / "recovered-natural"
    monkeypatch.setattr(gate, "READINESS", directory.parent)
    for plan in args["registered_plans"]:
        write(directory, plan["plan_role"] + "-plan-registered-v1.json", plan)
    baseline = json.loads(
        (ROOT / "configs/baseline" / (cell["baseline_fragment"] + ".json")).read_bytes()
    )
    fragment = json.loads(
        (ROOT / "configs/experiment" / (cell["cell_id"] + ".json")).read_bytes()
    )

    def check():
        report = gate.CellReport(
            experiment=cell["cell_id"],
            cell_id=cell["cell_id"],
            run_id=cell["run_id"],
            state="held",
            named=True,
        )
        report.run_ids = {
            "generation": cell["run_id"],
            "native_contact_fit": values["native_contact_fit"]["run_id"],
        }
        gate._check_registered_supply_binding(
            report,
            baseline,
            gate.PackageIndex(ROOT),
            "recovered-natural",
            {},
            cell=cell,
            fragment=fragment,
            data_root=tmp_path,
        )
        return report

    assert not check().findings
    (directory / "fit-plan-registered-v1.json").unlink()
    assert any(f.kind == "population-config-binding" for f in check().findings)
