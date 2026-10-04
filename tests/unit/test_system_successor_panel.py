"""Prospective six-member panels preserve all spent slots and blind isolation."""

import copy
import json

import pytest

from speech_aware_evidence_acquisition.rails import system_search_stage as stage
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_optimization_stage import fixture, measurement_profile
from test_system_search_allocations import write_pin


def setup(tmp_path, rows=20):
    return fixture(tmp_path, rows, profile=measurement_profile(), successor=True)


def freeze(f, rows=20):
    archive, repo, data, protocol, members, review, _, authority = f
    return stage.freeze_optimization_panel(
        archive,
        protocol=protocol,
        round_index=4,
        rows=rows,
        member_bindings=members,
        root_review=review,
        repo_root=repo,
        data_root=data,
        evaluation_authority=authority,
    )


@pytest.mark.parametrize("rows", [20, 50, 100, 200])
def test_successor_freeze_accounts_for_four_allocations_and_exact_six(tmp_path, rows):
    f = setup(tmp_path, rows)
    archive, _, data, protocol, members, _, _, _ = f
    before = {str(p): p.read_bytes() for p in archive.root.rglob("*") if p.is_file()}
    result = freeze(f, rows)
    reg = result["registration"]
    assert reg["schema"] == "saea-successor-system-panel-registration-v1"
    assert set(reg["expected_members"]) == set(members) - {
        "L-candidate-1",
        "B-candidate-1",
    }
    assert set(reg["allocations"]) == {
        "L-candidate-1",
        "L-candidate-2",
        "B-candidate-1",
        "B-candidate-2",
    }
    assert set(reg["exclusions"]) == {"L-candidate-1", "B-candidate-1"}
    assert reg["trajectory_cap"] == 6 * rows and reg["official_score_jobs_cap"] == 6
    assert (
        reg["measurement_profile"]
        == result["recipe"]["measurement_profile"]
        == protocol["measurement_profile"]
    )
    assert reg["runtime_admission"] == "separate-required"
    assert all(
        __import__("pathlib").Path(p).read_bytes() == raw for p, raw in before.items()
    )
    assert not data.exists()


@pytest.mark.parametrize(
    "fault",
    [
        "400",
        "missing-parent",
        "missing-slot",
        "bad-owner",
        "changed-authority",
        "valid-excluded",
        "invalid-compiled",
        "invalid-run",
        "admitted-run",
        "wrong-parent",
        "unmetered-valid",
    ],
)
def test_successor_freeze_refuses_illegal_subsets_and_dispositions(tmp_path, fault):
    f = setup(tmp_path)
    archive, repo, data, protocol, members, _, _, authority = f
    rows = 20
    if fault == "400":
        rows = 400
    elif fault == "missing-parent":
        members.pop("L-parent-aa")
    elif fault == "missing-slot":
        members.pop("B-candidate-1")
    elif fault == "bad-owner":
        (repo / protocol["allocation_extension"]["owner"]["relpath"]).write_text("{}")
    elif fault == "changed-authority":
        (repo / authority["relpath"]).write_text("{}")
    elif fault == "valid-excluded":
        path = archive.root / "imports/L-4-1.json"
        record = json.loads(path.read_text())
        record["status"] = "provisional"
        path.write_text(json.dumps(record))
    elif fault == "invalid-compiled":
        archive._write("compilations/L-4-1.json", {})
    elif fault in {"invalid-run", "admitted-run"}:
        (
            data
            / "attempts"
            / members["L-candidate-1" if fault == "invalid-run" else "L-parent"][
                "run_id"
            ]
        ).mkdir(parents=True)
    elif fault == "wrong-parent":
        members["B-parent-aa"]["bundle_id"] = "a" * 64
    else:
        path = archive.root / "responses/B-4-2.json"
        record = json.loads(path.read_text())
        record["input_tokens"] = None
        path.write_text(json.dumps(record))
    with pytest.raises((PolicyError, KeyError)):
        freeze(f, rows)
    assert not (archive.root / "panels").exists()


def test_legacy_freezer_still_refuses_invalid_slots(tmp_path):
    f = setup(tmp_path)
    with pytest.raises(PolicyError):
        stage.freeze_optimization_panel(
            f[0],
            protocol=f[3],
            round_index=4,
            rows=20,
            member_bindings=f[4],
            root_review=f[5],
            repo_root=f[1],
            data_root=f[2],
        )


def read_setup(tmp_path, rows=20):
    from speech_aware_evidence_acquisition.analysis import system_text_panel as panel
    from test_system_text_update_read import fixture as update_fixture
    from test_system_search_measurement import timing

    f = setup(tmp_path / "freeze", rows)
    _, repo, _, protocol, _, _, pool, ep = f
    frozen = freeze(f, rows)
    reg, recipe = frozen["registration"], frozen["recipe"]
    plan = json.loads(
        (repo / protocol["optimization_panel"]["plan"]["relpath"]).read_text()
    )
    evaluation = json.loads((repo / ep["relpath"]).read_text())
    supp = {
        "owner_decision": plan["owner"],
        "proposal_protocol": write_pin(repo, "protocol.json", protocol),
        "evaluation_authority": ep,
        "growth_owner_decision": evaluation["growth_owner_decision"],
        "learning_owner_decision": evaluation["learning_owner_decision"],
    }
    recipe["successor_panel_scope"] = write_pin(
        repo,
        "source-scope.json",
        {"schema": "saea-successor-panel-source-scope-v1", **supp},
    )
    owner = json.loads((repo / plan["owner"]["relpath"]).read_text())
    kwargs = panel.load_scope(reg, owner, supp, repo_root=repo, recipe=recipe)
    _, reference, old_recipe, _ = update_fixture(tmp_path / "synthetic")
    d = reference.as_json()
    ids = pool[:rows]
    admitted = set(reg["member_bindings"])
    d["feedback"]["groups"] = d["feedback"]["groups"][:rows]
    for sid, group in zip(ids, d["feedback"]["groups"], strict=True):
        group["sample_id"] = sid
        group["members"] = [
            m for m in group["members"] if m["candidate_id"] in admitted
        ]
    d["feedback"]["candidate_ids"] = sorted(admitted)
    d["feedback"]["sources"] = [
        s for s in d["feedback"]["sources"] if s["candidate_id"] in admitted
    ]
    for s in d["feedback"]["sources"]:
        s.update(
            {
                k: reg["member_bindings"][s["candidate_id"]][k]
                for k in ("run_id", "attempt_id", "config_hash")
            }
        )
    d["summaries"] = {c: d["summaries"][c] for c in admitted}
    for summary in d["summaries"].values():
        summary.update(
            slu_f1=0.9,
            intent=0.8,
            model_calls=6 * rows,
            reliable_completion_rate=1.0,
            sample_timing=timing(ids),
            timing_session_sha256="a" * 64,
        )
    authority = {"read_run_id": reg["read_id"], "ledger_row_sha256": "b" * 64}
    d.update(
        schema=panel.SCHEMA,
        family_id=reg["family_id"],
        read_authority=authority,
        registration_sha256=reg["registration_sha256"],
        measurement_profile=measurement_profile(),
        successor_custody={k: reg[k] for k in ("allocations", "exclusions")},
        successor_bindings=copy.deepcopy(reg["member_bindings"]),
        panel_scope=panel.scope_record(
            reg, owner, kwargs["growth"], evaluation=kwargs["evaluation"]
        ),
    )
    return f, recipe, reg, supp, owner, kwargs, reference, d, old_recipe


@pytest.mark.parametrize("rows", [20, 50, 100, 200])
def test_successor_complete_projection_and_measured_retention(tmp_path, rows):
    from speech_aware_evidence_acquisition.analysis import system_text_panel as panel
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        exploratory_selection,
    )

    f, recipe, reg, _, owner, kwargs, reference, d, _ = read_setup(tmp_path, rows)
    panel.validate_registration(recipe, reg, owner, d["read_authority"], **kwargs)
    evidence = panel.CompletePanelEvidence(canonical(d))
    own = evidence.learning_projection(
        amendment=kwargs["evaluation"]["learning"], reference=reference
    )
    projected = own.as_json()
    assert set(projected["summaries"]) == {"L-parent", "L-parent-aa", "L-candidate-2"}
    assert "B-" not in canonical(projected)
    assert len(projected["feedback"]["groups"]) == rows
    assert set(projected["successor_custody"]["allocations"]) == {
        "L-candidate-1",
        "L-candidate-2",
    }
    assert (
        projected["panel_scope"]["root_custody_sha256"]
        == d["panel_scope"]["root_custody_sha256"]
    )
    parent = f[0].load_policy(reg["member_bindings"]["L-parent"]["bundle_id"]).as_json()
    binding = {
        "parent_id": reg["member_bindings"]["L-parent"]["bundle_id"],
        "complementary_ids": [],
        "next_round": 5,
    }
    selected = exploratory_selection(
        own, registration=reg, binding=binding, protocol=f[3], parents=[parent]
    )
    assert set(selected["member_bindings"]) == set(projected["summaries"])
    measured = selected["measurements"] + selected["repeated_measurements"]
    assert {r["candidate_id"] for r in measured} == {"L-parent", "L-candidate-2"}
    assert selected["same_chain_aa"]["candidate_id"] == "L-parent-aa"


@pytest.mark.parametrize(
    "fault",
    [
        "summary",
        "source",
        "trajectory",
        "custody",
        "learning-owner",
        "timing",
        "session",
    ],
)
def test_successor_learning_and_retention_refuse_incomplete_or_mixed_evidence(
    tmp_path, fault
):
    from speech_aware_evidence_acquisition.analysis import system_text_panel as panel
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        exploratory_selection,
    )

    f, _, reg, _, _, kwargs, reference, d, _ = read_setup(tmp_path)
    amendment = copy.deepcopy(kwargs["evaluation"]["learning"])
    if fault == "summary":
        d["summaries"].pop("B-parent")
    elif fault == "source":
        d["feedback"]["sources"].pop()
    elif fault == "trajectory":
        d["feedback"]["groups"][0]["members"].pop()
    elif fault == "custody":
        d["successor_custody"]["allocations"]["B-candidate-1"]["status"] = "no-change"
    elif fault == "learning-owner":
        amendment["recipient_branch"] = "B"
    elif fault == "timing":
        d["summaries"]["L-candidate-2"].pop("sample_timing")
    else:
        d["summaries"]["L-parent-aa"]["timing_session_sha256"] = "b" * 64
    with pytest.raises(PolicyError):
        own = panel.CompletePanelEvidence(canonical(d)).learning_projection(
            amendment=amendment, reference=reference
        )
        parent = (
            f[0].load_policy(reg["member_bindings"]["L-parent"]["bundle_id"]).as_json()
        )
        exploratory_selection(
            own,
            registration=reg,
            binding={
                "parent_id": reg["member_bindings"]["L-parent"]["bundle_id"],
                "complementary_ids": [],
                "next_round": 5,
            },
            protocol=f[3],
            parents=[parent],
        )


@pytest.mark.parametrize(
    "fault", ["scope-pin", "growth-pin", "learning-pin", "profile", "excluded-compile"]
)
def test_successor_load_and_read_definition_refuse_scope_mutations(tmp_path, fault):
    from speech_aware_evidence_acquisition.analysis import system_text_panel as panel

    f, recipe, reg, supp, owner, _, _, d, _ = read_setup(tmp_path)
    if fault == "scope-pin":
        recipe["successor_panel_scope"]["sha256"] = "0" * 64
    elif fault == "growth-pin":
        supp["growth_owner_decision"] = supp["evaluation_authority"]
    elif fault == "learning-pin":
        supp["learning_owner_decision"] = supp["growth_owner_decision"]
    elif fault == "profile":
        recipe["measurement_profile"]["queue_depth"] = 8
    else:
        reg["allocations"]["L-candidate-1"]["compilation_sha256"] = "a" * 64
        reg["registration_sha256"] = content_hash(
            {k: v for k, v in reg.items() if k != "registration_sha256"}
        )
    with pytest.raises(PolicyError):
        kwargs = panel.load_scope(reg, owner, supp, repo_root=f[1], recipe=recipe)
        panel.validate_registration(recipe, reg, owner, d["read_authority"], **kwargs)


def test_successor_duplicate_candidate_retains_parent_measurement_representative(
    tmp_path,
):
    from speech_aware_evidence_acquisition.analysis import system_text_panel as panel
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        exploratory_selection,
    )

    f, _, reg, _, owner, kwargs, reference, d, _ = read_setup(tmp_path)
    reg["member_bindings"]["L-candidate-2"]["bundle_id"] = reg["member_bindings"][
        "L-parent"
    ]["bundle_id"]
    reg["registration_sha256"] = content_hash(
        {k: v for k, v in reg.items() if k != "registration_sha256"}
    )
    d.update(
        registration_sha256=reg["registration_sha256"],
        successor_bindings=copy.deepcopy(reg["member_bindings"]),
        panel_scope=panel.scope_record(
            reg, owner, kwargs["growth"], evaluation=kwargs["evaluation"]
        ),
    )
    own = panel.CompletePanelEvidence(canonical(d)).learning_projection(
        amendment=kwargs["evaluation"]["learning"], reference=reference
    )
    parent = f[0].load_policy(reg["member_bindings"]["L-parent"]["bundle_id"]).as_json()
    selected = exploratory_selection(
        own,
        registration=reg,
        binding={
            "parent_id": reg["member_bindings"]["L-parent"]["bundle_id"],
            "complementary_ids": [],
            "next_round": 5,
        },
        protocol=f[3],
        parents=[parent],
    )
    assert [r["candidate_id"] for r in selected["measurements"]] == ["L-parent"]
    assert [r["candidate_id"] for r in selected["repeated_measurements"]] == [
        "L-candidate-2"
    ]


@pytest.mark.parametrize("field", ["bundle_id", "attempt_id"])
def test_successor_packet_rejects_tampered_selection_after_qualified_projection(
    tmp_path, field
):
    from speech_aware_evidence_acquisition.analysis import system_text_panel as panel
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        exploratory_selection,
        require_exploratory_packet,
    )

    f, _, reg, _, _, kwargs, reference, d, _ = read_setup(tmp_path)
    own = panel.CompletePanelEvidence(canonical(d)).learning_projection(
        amendment=kwargs["evaluation"]["learning"], reference=reference
    )
    parent = f[0].load_policy(reg["member_bindings"]["L-parent"]["bundle_id"]).as_json()
    selection = exploratory_selection(
        own,
        registration=reg,
        binding={
            "parent_id": reg["member_bindings"]["L-parent"]["bundle_id"],
            "complementary_ids": [],
            "next_round": 5,
        },
        protocol=f[3],
        parents=[parent],
    )
    selection["member_bindings"]["L-candidate-2"][field] = (
        "a" * 64 if field == "bundle_id" else "another-attempt"
    )
    selection["selection_sha256"] = content_hash(
        {k: v for k, v in selection.items() if k != "selection_sha256"}
    )
    with pytest.raises(PolicyError, match="qualified own member bindings"):
        require_exploratory_packet(
            {"feedback": own.as_json(), "selection": selection}, protocol=f[3]
        )


def reader_bindings(tmp_path, reg):
    """Materialize synthetic official job metadata; never invoke a scorer."""
    bindings = []
    for cid, member in reg["member_bindings"].items():
        folder = tmp_path / member["attempt_id"]
        folder.mkdir(parents=True)
        manifest = folder / "manifest.json"
        manifest.write_text("{}")
        job = {
            "job_id": folder.name,
            "manifest": str(manifest),
            "status": "succeeded",
            "returncode": 0,
            "operation": "finalize",
        }
        (folder / "score-jobs.jsonl").write_text(json.dumps(job) + "\n")
        (folder / "score-batch").mkdir()
        (folder / "score-batch/batch-summary.json").write_text(
            json.dumps(
                {
                    "job_count": 1,
                    "succeeded": 1,
                    "failed": 0,
                    "include_per_sample": True,
                    "jobs": [job],
                }
            )
        )
        bindings.append(
            {
                "candidate_id": cid,
                "config": {
                    "manifest": {"path": str(manifest)},
                    "construction_roster": {},
                },
            }
        )
    return bindings


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "job-failed",
        "job-duplicate",
        "last-seal",
        "binding-omitted",
        "B-timing",
        "timing-session",
    ],
)
def test_successor_actual_reader_requires_six_jobs_seals_and_all_timing(
    tmp_path, monkeypatch, fault
):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.analysis import (
        system_text_panel as panel,
        system_text_pilot as pilot,
    )

    f, recipe, reg, _, owner, kwargs, _, d, _ = read_setup(tmp_path)
    bindings = reader_bindings(tmp_path / "terminal", reg)
    metadata = [
        (
            {
                "run_id": b["run_id"],
                "config": {"config_hash": b["config_hash"]},
                "attempt": {"attempt_id": b["attempt_id"]},
                "split": {"count": 20, "ids": recipe["sample_ids"]},
            },
            {},
        )
        for b in reg["member_bindings"].values()
    ]
    if fault == "job-failed":
        path = (
            __import__("pathlib")
            .Path(bindings[-1]["config"]["manifest"]["path"])
            .parent
            / "score-batch/batch-summary.json"
        )
        job = json.loads(path.read_text())
        job["failed"] = 1
        path.write_text(json.dumps(job))
    elif fault == "job-duplicate":
        path = (
            __import__("pathlib")
            .Path(bindings[-1]["config"]["manifest"]["path"])
            .parent
            / "score-jobs.jsonl"
        )
        path.write_text(path.read_text() * 2)
    elif fault == "binding-omitted":
        bindings.pop()
    elif fault == "B-timing":
        d["summaries"]["B-candidate-2"].pop("sample_timing")
    elif fault == "timing-session":
        d["summaries"]["B-parent"]["timing_session_sha256"] = "b" * 64

    # The reader itself must count bindings before any task-result hook.
    def preflight(b, _expected):
        if fault == "binding-omitted":
            pytest.fail("omitted bindings reached task-result preflight")
        return metadata

    monkeypatch.setattr(pilot, "preflight_family", preflight)
    monkeypatch.setattr(
        pilot,
        "_absolute_json",
        lambda *_: {"items": [{"sample_id": s} for s in recipe["sample_ids"]]},
    )
    events = []

    def verify(_):
        events.append("seal")
        return SimpleNamespace(
            attempt_state="OPENED"
            if fault == "last-seal" and len(events) == 6
            else "FINALIZED"
        )

    monkeypatch.setattr(pilot, "verify_bundle", verify)

    def grouped(_):
        assert events == ["seal"] * 6
        events.append("scores")
        return {**copy.deepcopy(d["feedback"]), "carrier_lock_key": "slurp"}

    monkeypatch.setattr(pilot, "build_group_relative_feedback", grouped)
    monkeypatch.setattr(
        pilot,
        "_official_family_rows",
        lambda *_a, **_k: (
            {c: {s: {} for s in recipe["sample_ids"]} for c in reg["member_bindings"]},
            d["summaries"],
        ),
    )

    def read():
        return panel.read_evidence(
            bindings,
            recipe=recipe,
            registration=reg,
            owner=owner,
            authority=d["read_authority"],
            **kwargs,
        )

    if fault:
        with pytest.raises(PolicyError):
            read()
        if fault in {"job-failed", "job-duplicate", "last-seal", "binding-omitted"}:
            assert "scores" not in events
    else:
        result = read().as_json()
        assert set(result["summaries"]) == set(reg["member_bindings"])
        assert result["successor_custody"] == {
            k: reg[k] for k in ("allocations", "exclusions")
        }
        assert events == ["seal"] * 6 + ["scores"]


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "scope-missing",
        "owner-changed",
        "protocol-changed",
        "exclusion-changed",
        "profile-conflict",
        "attempt-conflict",
    ],
)
def test_successor_actual_prelaunch_validates_scope_before_runtime(tmp_path, fault):
    from types import SimpleNamespace
    import hashlib
    import shutil
    from test_system_text_policy import ROOT
    from test_system_text_policy_binding import bound as bound_fixture
    from test_flight_registration_check import gate, _write
    from speech_aware_evidence_acquisition.rails.system_text_policy import (
        compile_system_text_policy,
    )

    f, recipe, reg, _, _, _, _, _, _ = read_setup(tmp_path / "successor")
    archive, repo, data, _, _, _, _, _ = f
    # Reuse the bound policy fixture's pinned baseline dependencies, then compile
    # the actual registered parent into the same shared runtime fragments.
    _, _, deps, _, baseline, _ = bound_fixture.__wrapped__(tmp_path / "deps")
    shutil.copytree(deps / "configs", repo / "configs", dirs_exist_ok=True)
    shutil.copytree(deps / "docs", repo / "docs", dirs_exist_ok=True)
    member = reg["member_bindings"]["L-parent"]
    policy = archive.load_policy(member["bundle_id"])
    compiled = compile_system_text_policy(
        baseline, policy, repo_root=ROOT, output_root=repo
    )
    compiled.update(
        system_search_measurement=measurement_profile(),
        serving_slots=4,
        serving_slot_tokens=24576,
        server_args=["-np", "4", "-c", "98304"],
        decoding_params={"max_tokens": 512},
    )
    raw = (archive.root / "policies" / (policy.bundle_id + ".json")).read_bytes()
    target = data / "search/policies" / (policy.bundle_id + ".json")
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)
    binding = {
        "schema": "saea-system-text-role-binding-v1",
        "bundle_id": policy.bundle_id,
        "bundle": {
            "relpath": target.relative_to(data).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    }
    cell = {
        "model_fragment": "synthetic",
        "dataset_fragment": "synthetic",
        "baseline_fragment": "synthetic",
        "attempt_id": member["attempt_id"],
        "system_text_policy_binding": binding,
    }
    if fault == "scope-missing":
        recipe.pop("successor_panel_scope")
    elif fault == "owner-changed":
        evaluation = json.loads(
            (repo / reg["evaluation_authority"]["relpath"]).read_text()
        )
        (repo / evaluation["owner227"]["relpath"]).write_text("{}")
    elif fault == "protocol-changed":
        (repo / "protocol.json").write_text("{}")
    elif fault == "exclusion-changed":
        reg["exclusions"].pop("B-candidate-1")
        reg["registration_sha256"] = content_hash(
            {k: v for k, v in reg.items() if k != "registration_sha256"}
        )
    elif fault == "profile-conflict":
        compiled["system_search_measurement"]["queue_depth"] = 8
    elif fault == "attempt-conflict":
        cell["attempt_id"] = "another-attempt"
    recipe["system_panel_registration"] = write_pin(repo, "registration.json", reg)
    for kind, doc in (
        ("model", {}),
        ("dataset", {}),
        ("baseline", compiled),
        ("experiment", {"cells": [cell]}),
    ):
        _write(repo / "configs" / kind / "synthetic.json", doc)
    report = SimpleNamespace(
        run_id=member["run_id"], experiment="synthetic", findings=[]
    )
    gate._check_system_text_binding(report, cell, compiled, recipe, repo, data)
    assert bool(report.findings) is (fault is not None), report.findings


@pytest.mark.parametrize("rows", [20, 50, 100, 200, 400])
def test_successor_cli_freezes_reviewed_definitions_and_refuses_400(
    tmp_path, capsys, rows
):
    from test_system_text_search_cli import cli, write

    f = setup(tmp_path)
    archive, repo, data, protocol, members, review, _, authority = f
    if rows in (50, 100, 200):
        f = setup(tmp_path / "larger", rows)
        archive, repo, data, protocol, members, review, _, authority = f
    args = [
        "--archive",
        str(archive.root),
        "freeze-successor-panel",
        "--round",
        "4",
        "--rows",
        str(rows),
        "--protocol",
        write(tmp_path / "cli-protocol.json", protocol),
        "--member-bindings",
        write(tmp_path / "cli-members.json", members),
        "--root-review",
        write(tmp_path / "cli-review.json", review),
        "--evaluation-authority",
        write(tmp_path / "cli-authority.json", authority),
        "--repo-root",
        str(repo),
        "--data-root",
        str(data),
    ]
    if rows == 400:
        with pytest.raises(SystemExit):
            cli.main(args)
        assert not (archive.root / "panels").exists()
    else:
        cli.main(args)
        result = json.loads(capsys.readouterr().out)
        assert result["members"] == 6 and result["trajectory_cap"] == rows * 6
        assert (
            result["runtime_admission"] == "separate-required"
            and result["contacts_added"] == 0
        )
