"""Manual N20 contracts use real configuration and synthetic pinned evidence."""

from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import (
    _canonical_hash,
    compose,
    protocol_hash,
)
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.preparation import (
    SCHEMA,
    digest,
    artifact_inputs,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails import (
    architecture_natural_registration as admission,
)
import test_architecture_natural_registration as natural_fixture
from test_architecture_natural_registration import (
    fixture as capacity_fixture,
    ROOT,
    LABELS,
    write,
)


def implementation():
    paths = {"runtime": "core/flight/runtime.py"}
    paths.update(
        {
            "speech_aware_evidence_acquisition.rails." + name: "rails/" + name + ".py"
            for name in (
                "kb_policy",
                "knowledge_provider",
                "knowledge_stores",
                "phase_supply",
            )
        }
    )
    return {
        name: hashlib.sha256(
            (ROOT / "src/speech_aware_evidence_acquisition" / path).read_bytes()
        ).hexdigest()
        for name, path in paths.items()
    }


def supply(data, name, values):
    document = dict(
        schema=SCHEMA,
        kind="phase-supply",
        contact_class="model-free",
        inputs=artifact_inputs(
            config=values,
            split_identity_hash=values["population"]["split_identity_hash"],
            sources={
                "implementation": implementation(),
                "packets": {sid: {} for sid in values["populations"][0]["ids"]},
            },
        ),
        output={},
        output_sha256=digest({}),
    )
    return write(data, name, document)


def fixture(tmp_path, monkeypatch, label="seed"):
    prior_pins = {}
    for name in LABELS:
        stem = f"slurp-native-stage3-simple-consumption-{name}-n20-v2"
        (c,) = load_campaign_cells(ROOT, stem)
        c = c.document
        values = compose(
            ROOT,
            c["model_fragment"],
            c["dataset_fragment"],
            c["baseline_fragment"],
            stem,
        ).values
        prior_pins[name] = supply(tmp_path, f"capacity/{name}-source.json", values)
    original_example = natural_fixture.example

    def example():
        result = original_example()
        for member in result["registration"]["members"]:
            member["prepared_artifact_verification"] = {
                "capacity": {"prepared_pin": prior_pins[member["label"]]}
            }
        return result

    monkeypatch.setattr(natural_fixture, "example", example)
    base = capacity_fixture(tmp_path, label)
    capacity = base["registered_plans"][0]["capacity_prerequisite"]
    population_pin = base["values"]["experiment_population"]
    members, reads, accounting, compositions = [], [], [], {}
    source = "a" * 40
    for name in LABELS:
        stem = f"slurp-native-stage3-simple-consumption-{name}-engineering-smoke-4-v4"
        (c,) = load_campaign_cells(ROOT, stem)
        cell = c.document
        original = compose(
            ROOT,
            cell["model_fragment"],
            cell["dataset_fragment"],
            cell["baseline_fragment"],
            stem,
        )
        values = deepcopy(original.values)
        values["prepared_phase_supply"] = supply(
            tmp_path, f"natural/{name}/supply.json", values
        )
        config_hash = _canonical_hash(values)
        compositions[stem] = SimpleNamespace(values=values, config_hash=config_hash)
        run, attempt = cell["run_id"], cell["attempt_id"]
        roster = deepcopy(values["populations"][0]["ids"])
        fit = values["native_contact_fit"]
        contacts = 4
        member = dict(
            label=name,
            experiment=stem,
            run_id=run,
            attempt_id=attempt,
            fit_run_id=fit["run_id"],
            config_hash=config_hash,
            configured_sample_ids=roster,
            runtime_sample_ids=roster,
            policy_binding=cell["system_text_policy_binding"],
            prepared_phase_supply=values["prepared_phase_supply"],
            rows=4,
            model_contacts=contacts,
        )
        expected_natural = ExecutionPlan(
            **values["execution_plan"],
            run_id=run,
            attempt_id=attempt,
            carrier_lock_key="slurp",
            split_identity_hash=values["population"]["split_identity_hash"],
            protocol_hash=protocol_hash(
                config_hash, values["arm"], values["population"]["split_identity_hash"]
            ),
        ).validate()
        expected_fit = replace(
            expected_natural,
            run_id=fit["run_id"],
            attempt_id=fit["attempt_id"],
            planned_model_calls=fit["contact_cap"],
        )
        manifest = dict(
            schema="saea-run-manifest-v1",
            status="COMPLETED",
            run_id=run,
            study_commit=source,
            study_repo_dirt=[],
            config={"config_hash": config_hash},
            plan=asdict(expected_natural),
            scores=None,
        )
        member["manifest"] = write(tmp_path, f"natural/{name}/manifest.json", manifest)
        member["attempt"] = write(
            tmp_path,
            f"natural/{name}/attempt.json",
            dict(
                state="OPENED",
                run_id=run,
                attempt_id=attempt,
                actual={"calls": contacts},
            ),
        )
        member["inspection"] = write(
            tmp_path,
            f"natural/{name}/inspection.json",
            dict(
                pass_=True,
                **{"pass": True},
                bundle_verified=True,
                fails=[],
                dirt=[],
                study_commit=source,
                manifest_status="COMPLETED",
                run_id=run,
                attempt_id=attempt,
                rows=4,
                distinct=4,
                actual={"calls": contacts},
                **{"sha256_run-manifest": member["manifest"]["sha256"]},
            ),
        )
        member["guard_finished"] = write(
            tmp_path,
            f"natural/{name}/guard.json",
            dict(
                schema="saea-flight-process-memory-guard-v1",
                status="completed",
                exit_code=0,
                worker_returncode=0,
                identity=dict(
                    run_id=run,
                    attempt_id=attempt,
                    study_head=source,
                    repo_root="/frozen/natural",
                ),
            ),
        )
        records = []
        for index in range(contacts):
            journal = [
                {"contact": index * 4 + i + 1, "method": "POST", "route": "/tokenize"}
                for i in range(4)
            ]
            output = dict(
                every_request_fits=True,
                capacity_scope="actual-variable-trajectory-contact",
                generation_contacts=0,
                agent_contact_id=f"contact-{index}",
                contacts=4,
                cumulative_contacts=(index + 1) * 4,
                contact_counts={"POST /tokenize": 4},
            )
            artifact = dict(
                schema=SCHEMA,
                kind="request-fit",
                contact_class="tokenizer",
                inputs={
                    "fit_plan": asdict(expected_fit),
                    "native_contact": {"agent_contact_id": f"contact-{index}"},
                },
                output=output,
                output_sha256=digest(output),
            )
            pin = write(tmp_path, f"natural/{name}/fit-{index}.json", artifact)
            raw = b"".join(json.dumps(row).encode() + b"\n" for row in journal)
            (tmp_path / (pin["relpath"] + ".contacts.jsonl")).write_bytes(raw)
            records.append(
                {
                    **pin,
                    "journal_sha256": hashlib.sha256(raw).hexdigest(),
                    "actual_endpoints": 4,
                }
            )
        accounting.append(
            dict(
                run_id=fit["run_id"],
                actual_request_receipts=contacts,
                actual_endpoints=contacts * 4,
                records=records,
            )
        )
        flight = write(
            tmp_path,
            f"natural/{name}/flight.json",
            {"run_id": run, "attempt_id": attempt},
        )
        report = {
            k: deepcopy(member[k])
            for k in (
                "label",
                "run_id",
                "attempt_id",
                "config_hash",
                "configured_sample_ids",
                "runtime_sample_ids",
                "model_contacts",
            )
        }
        report.update(
            schema="saea-natural-architecture-structural-report-v1",
            passed=True,
            bundle_verified=True,
            all_contacts_joined=True,
            all_original_fits_verified=True,
            terminal_policy_verified=True,
            source_commit=source,
            official_score_jobs=0,
            scientific_feedback=False,
            learner_export=False,
            rows=[
                dict(sample_id=sid, terminal_policy_verified=True, contacts=1)
                for sid in roster
            ],
            reviewer_applicable=name in ("seed", "seed-aa"),
            flight_receipts=flight,
            actual_fit_receipts=contacts,
            actual_fit_endpoints=contacts * 4,
            fit_receipts=[{k: r[k] for k in ("relpath", "sha256")} for r in records],
        )
        member["structural_report"] = write(
            tmp_path, f"natural/{name}/report.json", report
        )
        members.append(member)
        reads.append(
            {
                k: member[k]
                for k in ("label", "run_id", "attempt_id", "manifest", "guard_finished")
            }
        )
    account_pin = write(
        tmp_path,
        "natural/accounting.json",
        dict(schema="saea-native-actual-fit-accounting-v1", members=accounting),
    )
    for member in members:
        member["actual_fit_accounting"] = account_pin
    natural_admission = write(
        tmp_path,
        "natural/admission.json",
        dict(
            schema="saea-campaign-decision-v1",
            status="decided",
            owner_decisions=[227],
            next_panel_authorized=False,
            learning="HELD",
            capacity_prerequisite=capacity,
            eligible_run_ids=[
                rid
                for member in members
                for rid in (member["run_id"], member["fit_run_id"])
            ],
        ),
    )
    read_pin = write(
        tmp_path,
        "natural/read.json",
        dict(
            schema="saea-architecture-natural-family-root-read-v1",
            status="ROOT COUNTERSIGNED STRUCTURAL READ",
            passed=True,
            registration=natural_admission,
            experiment_population=population_pin,
            source_commit=source,
            frozen_worker="/frozen/natural",
            member_labels=list(LABELS),
            official_score_jobs=0,
            scientific_feedback=False,
            learner_export=False,
            members=reads,
            actual_fit_accounting=account_pin,
        ),
    )
    qualification = dict(
        schema="saea-architecture-natural-family-qualification-v1",
        status="QUALIFIED_STRUCTURAL_ONLY",
        passed=True,
        registration=natural_admission,
        experiment_population=population_pin,
        source_commit=source,
        frozen_worker="/frozen/natural",
        root_read_receipt=read_pin,
        members=members,
        official_score_jobs=0,
        scientific_feedback=False,
        learner_export=False,
        next_panel_admitted=False,
    )
    natural = {
        "registration": natural_admission,
        "qualification": write(tmp_path, "natural/qualification.json", qualification),
    }
    stem = f"slurp-native-stage3-simple-consumption-{label}-n20-v2"
    (c,) = load_campaign_cells(ROOT, stem)
    cell = c.document
    config = compose(
        ROOT,
        cell["model_fragment"],
        cell["dataset_fragment"],
        cell["baseline_fragment"],
        stem,
    )
    values = deepcopy(config.values)
    values["prepared_phase_supply"] = supply(tmp_path, "n20/supply.json", values)
    config_hash = _canonical_hash(values)
    roster = values["populations"][0]["ids"]
    receipt = dict(
        member_id=label,
        experiment=stem,
        run_id=cell["run_id"],
        attempt_id=cell["attempt_id"],
        config_hash=config_hash,
        configured_sample_ids=roster,
        runtime_sample_ids=deepcopy(roster),
        prepared_phase_supply=values["prepared_phase_supply"],
        contacts=0,
        output_equal=True,
        warm_verified=True,
        runtime_admission=False,
        prepared_source_commit="c" * 40,
        source_policy=json.loads((ROOT / population_pin["relpath"]).read_bytes())[
            "architecture"
        ]["members"][list(LABELS).index(label)]["execution_config"],
        output_sha256=digest({}),
        source_prepared_phase_supply=prior_pins[label],
    )
    # Redirect this one synthetic repo receipt to scratch; the real pin reader
    # still verifies its raw bytes. Other repo/source/config reads are unchanged.
    receipt_pin = write(tmp_path, "repo-preparation.json", receipt)
    original_read = admission._read_pin

    def read(p, root):
        if (
            isinstance(p, dict)
            and p.get("relpath") == "repo-preparation.json"
            and Path(root) == ROOT
        ):
            return original_read(p, tmp_path)
        return original_read(p, root)

    monkeypatch.setattr(admission, "_read_pin", read)
    # Independently persisted fresh N20 configuration: never alias later caller
    # mutations of values, the cell or its proposed execution identities.
    compositions[stem] = SimpleNamespace(
        values=deepcopy(values), config_hash=config_hash
    )
    original_compose = admission.compose
    monkeypatch.setattr(
        admission,
        "compose",
        lambda root, model, dataset, baseline, experiment: (
            compositions.get(experiment)
            or original_compose(root, model, dataset, baseline, experiment)
        ),
    )
    split = split_identity_hash(prefixed("slurp", roster))
    expected = ExecutionPlan(
        **values["execution_plan"],
        run_id=cell["run_id"],
        attempt_id=cell["attempt_id"],
        carrier_lock_key="slurp",
        split_identity_hash=split,
        protocol_hash=protocol_hash(config_hash, values["arm"], split),
    ).validate()
    plans = []
    draft_root = (
        ROOT / "docs/readiness/2026-10-07-slurp-simple-consumption-n20-preparation-v3"
    )
    for role in ("generation", "fit"):
        plan = json.loads(
            (draft_root / f"{label}-{role}-plan-draft-v1.json").read_bytes()
        )
        spec = values["native_contact_fit"]
        execution = (
            expected
            if role == "generation"
            else replace(
                expected,
                run_id=spec["run_id"],
                attempt_id=spec["attempt_id"],
                planned_model_calls=spec["contact_cap"],
            )
        )
        plan.update(
            status="ROOT COUNTERSIGNED BEFORE CONTACT",
            architecture_proof="manual-architecture-n20-v1",
            composed_config_hash=config_hash,
            execution_plan=asdict(execution),
            prepared_phase_supply=values["prepared_phase_supply"],
            capacity_prerequisite=capacity,
            natural_prerequisite=natural,
            preparation_receipt=receipt_pin,
            runtime_sample_ids=deepcopy(receipt["runtime_sample_ids"]),
        )
        plans.append(plan)
    eligible = []
    for name in LABELS:
        (nc,) = load_campaign_cells(
            ROOT, f"slurp-native-stage3-simple-consumption-{name}-n20-v2"
        )
        nd = nc.document
        nv = compose(
            ROOT,
            nd["model_fragment"],
            nd["dataset_fragment"],
            nd["baseline_fragment"],
            nd["cell_id"],
        ).values
        eligible.extend([nd["run_id"], nv["native_contact_fit"]["run_id"]])
    decision = write(
        tmp_path,
        "n20/admission.json",
        dict(
            schema="saea-campaign-decision-v1",
            status="decided",
            owner_decisions=[227],
            learner_export=False,
            source_preparation_commit="c" * 40,
            experiment_population=population_pin,
            capacity_prerequisite=capacity,
            natural_prerequisite=natural,
            eligible_run_ids=eligible,
        ),
    )
    for plan in plans:
        plan["decision_receipt"] = decision
    return dict(
        values=values,
        cell=cell,
        registered_plans=plans,
        repo_root=ROOT,
        data_root=tmp_path,
    )


def invoke(args):
    return admission.require_architecture_n20_registration(**args)


@pytest.mark.parametrize(
    "label,generation,fit",
    [
        ("seed", 260, 1040),
        ("seed-aa", 260, 1040),
        ("review-off", 40, 160),
        ("solver-lookup", 60, 240),
    ],
)
def test_exact_full_family_admits_only_the_configured_pair(
    tmp_path, monkeypatch, label, generation, fit
):
    result = invoke(fixture(tmp_path, monkeypatch, label))
    assert result["generation_cap"] == generation and result["fit_cap"] == fit
    assert len(result["sample_ids"]) == len(result["runtime_sample_ids"]) == 20
    assert result["runtime_admission"] is False and result["read_authorized"] is False


def test_natural_four_row_pair_cannot_enter_n20(tmp_path):
    with pytest.raises(ValueError, match="N20"):
        invoke(capacity_fixture(tmp_path))


def rehash(args, relative, mutate):
    """Mutate evidence and refresh every enclosing raw pin, not just its digest."""
    root = args["data_root"]
    path = root / relative
    document = json.loads(path.read_bytes())
    mutate(document)
    path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")

    def refresh(value):
        if isinstance(value, dict):
            if (
                "relpath" in value
                and "sha256" in value
                and (root / value["relpath"]).is_file()
            ):
                value["sha256"] = hashlib.sha256(
                    (root / value["relpath"]).read_bytes()
                ).hexdigest()
            for child in value.values():
                refresh(child)
        elif isinstance(value, list):
            for child in value:
                refresh(child)

    for _ in range(8):
        for path in root.rglob("*.json"):
            document = json.loads(path.read_bytes())
            refresh(document)
            path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    for plan in args["registered_plans"]:
        refresh(plan)


@pytest.mark.parametrize(
    "relative,mutate",
    [
        ("natural/qualification.json", lambda d: d["members"].pop()),
        (
            "natural/qualification.json",
            lambda d: d["members"].append(deepcopy(d["members"][0])),
        ),
        ("natural/qualification.json", lambda d: d["members"].reverse()),
        ("natural/qualification.json", lambda d: d.update(status="PENDING")),
        ("natural/qualification.json", lambda d: d.update(source_commit="b" * 40)),
        (
            "natural/qualification.json",
            lambda d: d["members"][0]["runtime_sample_ids"].reverse(),
        ),
        (
            "natural/qualification.json",
            lambda d: d["members"][0]["runtime_sample_ids"].append(
                d["members"][0]["runtime_sample_ids"][0]
            ),
        ),
        (
            "natural/qualification.json",
            lambda d: d["members"][0]["policy_binding"].update(bundle_id="f" * 64),
        ),
        (
            "natural/qualification.json",
            lambda d: d["members"][0].update(model_contacts=5),
        ),
        ("natural/admission.json", lambda d: d.update(status="draft")),
        ("natural/admission.json", lambda d: d["eligible_run_ids"].pop()),
        ("natural/read.json", lambda d: d.update(status="UNSIGNED")),
        ("natural/read.json", lambda d: d.update(scientific_feedback=True)),
        ("natural/seed/guard.json", lambda d: d.update(exit_code=125)),
        (
            "natural/seed/guard.json",
            lambda d: d["identity"].update(study_head="c" * 40),
        ),
        ("natural/seed/inspection.json", lambda d: d.update(bundle_verified=False)),
        ("natural/seed/manifest.json", lambda d: d.update(study_repo_dirt=["dirty"])),
        ("natural/seed/attempt.json", lambda d: d["actual"].update(calls=99)),
        (
            "natural/seed/report.json",
            lambda d: d.update(all_original_fits_verified=False),
        ),
        (
            "natural/accounting.json",
            lambda d: d["members"][0]["records"].append(
                deepcopy(d["members"][0]["records"][0])
            ),
        ),
        ("n20/admission.json", lambda d: d.update(status="draft")),
        ("n20/admission.json", lambda d: d.update(owner_decisions=[])),
        ("n20/admission.json", lambda d: d["eligible_run_ids"].pop()),
        ("repo-preparation.json", lambda d: d.update(config_hash="e" * 64)),
        ("repo-preparation.json", lambda d: d["runtime_sample_ids"].reverse()),
        (
            "repo-preparation.json",
            lambda d: d["runtime_sample_ids"].append(d["runtime_sample_ids"][0]),
        ),
        (
            "n20/supply.json",
            lambda d: d["inputs"]["sources"]["implementation"].update(runtime="e" * 64),
        ),
    ],
)
def test_rehashed_chain_cannot_admit_invalid_evidence(
    tmp_path, monkeypatch, relative, mutate
):
    args = fixture(tmp_path, monkeypatch)
    rehash(args, relative, mutate)
    with pytest.raises((ValueError, KeyError)):
        invoke(args)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda a: a["registered_plans"].pop(),
        lambda a: a["registered_plans"].append(deepcopy(a["registered_plans"][0])),
        lambda a: a["registered_plans"][0].update(
            architecture_proof="natural-four-row-v1"
        ),
        lambda a: a["registered_plans"][0].update(status="DRAFT_HELD_NOT_REGISTERED"),
        lambda a: a["registered_plans"][0]["execution_plan"].update(
            planned_model_calls=261
        ),
        lambda a: a["registered_plans"][0]["runtime_sample_ids"].reverse(),
        lambda a: a["registered_plans"][0]["configured_sample_ids"].reverse(),
        lambda a: a["registered_plans"][0].update(official_score_jobs=0),
        lambda a: a["values"]["family_budget"].update(generation_calls_cap=261),
    ],
)
def test_pair_binding_refuses_missing_duplicate_unsigned_or_drifted_plans(
    tmp_path, monkeypatch, mutation
):
    args = fixture(tmp_path, monkeypatch)
    mutation(args)
    with pytest.raises(ValueError):
        invoke(args)


@pytest.mark.parametrize("complete", [True, False])
def test_existing_named_checker_routes_only_the_complete_n20_pair(
    tmp_path, monkeypatch, complete
):
    from test_flight_registration_check import gate

    args = fixture(tmp_path, monkeypatch)
    cell, values = args["cell"], args["values"]
    package = tmp_path / "packages" / "n20"
    monkeypatch.setattr(gate, "READINESS", package.parent)
    for plan in args["registered_plans"][: 2 if complete else 1]:
        write(package, plan["plan_role"] + "-plan-registered-v1.json", plan)
    # The effective synthetic composition mirrors persisted source fixtures;
    # only the operational envelope pin differs from the untouched real config.
    import speech_aware_evidence_acquisition.core.config as config_module

    original_compose = config_module.compose

    def compose_fixture(root, model, dataset, baseline, experiment):
        if experiment == cell["cell_id"]:
            return SimpleNamespace(values=values, config_hash=_canonical_hash(values))
        return original_compose(root, model, dataset, baseline, experiment)

    monkeypatch.setattr(config_module, "compose", compose_fixture)
    baseline = json.loads(
        (ROOT / "configs/baseline" / (cell["baseline_fragment"] + ".json")).read_bytes()
    )
    baseline["prepared_phase_supply"] = values["prepared_phase_supply"]
    fragment = json.loads(
        (ROOT / "configs/experiment" / (cell["cell_id"] + ".json")).read_bytes()
    )
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
        "n20",
        {},
        cell=cell,
        fragment=fragment,
        data_root=tmp_path,
    )
    assert bool(report.findings) is not complete
    if not complete:
        assert any(f.kind == "population-config-binding" for f in report.findings)


@pytest.mark.parametrize("role", ["generation", "fit"])
@pytest.mark.parametrize("change_run", [True, False])
def test_consistently_rebound_unlisted_pair_identity_is_refused(
    tmp_path, monkeypatch, role, change_run
):
    args = fixture(tmp_path, monkeypatch)
    values, cell = args["values"], args["cell"]
    if role == "generation":
        if change_run:
            cell["run_id"] = "UNLISTED-N20-GENERATION-SYNTHETIC"
        cell["attempt_id"] = "unlisted-generation-attempt"
    else:
        if change_run:
            values["native_contact_fit"]["run_id"] = "UNLISTED-N20-FIT-SYNTHETIC"
        values["native_contact_fit"]["attempt_id"] = "unlisted-fit-attempt"
        supply_path = tmp_path / values["prepared_phase_supply"]["relpath"]
        prepared = json.loads(supply_path.read_bytes())
        prepared["inputs"] = artifact_inputs(
            config=values,
            split_identity_hash=values["population"]["split_identity_hash"],
            sources=prepared["inputs"]["sources"],
        )
        values["prepared_phase_supply"] = write(
            tmp_path, values["prepared_phase_supply"]["relpath"], prepared
        )
    config_hash = _canonical_hash(values)
    split = values["population"]["split_identity_hash"]
    generation = ExecutionPlan(
        **values["execution_plan"],
        run_id=cell["run_id"],
        attempt_id=cell["attempt_id"],
        carrier_lock_key="slurp",
        split_identity_hash=split,
        protocol_hash=protocol_hash(config_hash, values["arm"], split),
    ).validate()
    fit = values["native_contact_fit"]
    for document in args["registered_plans"]:
        bound = (
            generation
            if document["plan_role"] == "generation"
            else replace(
                generation,
                run_id=fit["run_id"],
                attempt_id=fit["attempt_id"],
                planned_model_calls=fit["contact_cap"],
            )
        )
        document.update(
            composed_config_hash=config_hash,
            execution_plan=asdict(bound),
            run_id=bound.run_id,
            attempt_id=bound.attempt_id,
            prepared_phase_supply=deepcopy(values["prepared_phase_supply"]),
        )
    rehash(
        args,
        "repo-preparation.json",
        lambda receipt: receipt.update(
            run_id=cell["run_id"],
            attempt_id=cell["attempt_id"],
            config_hash=config_hash,
            prepared_phase_supply=deepcopy(values["prepared_phase_supply"]),
        ),
    )
    with pytest.raises(ValueError, match="N20 root.*identity"):
        invoke(args)
