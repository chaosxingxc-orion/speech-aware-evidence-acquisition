"""Owner220 diagnostics never become optimizer feedback or partial reads."""

import copy
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.reward_links import RewardProjection, SLURP_NATIVE_FIELDS

from speech_aware_evidence_acquisition.analysis import system_text_pilot as pilot
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)
from test_system_text_update_read import fixture as update_fixture


def fixture(tmp_path):
    _, feedback, recipe, roster = update_fixture(tmp_path)
    d = feedback.as_json()
    ids = [g["sample_id"] for g in d["feedback"]["groups"][:20]]
    d["feedback"]["groups"] = d["feedback"]["groups"][:20]
    d["family_id"] = pilot.FAMILY
    d["schema"] = pilot.SCHEMA
    bindings = recipe["system_search_evaluation"]["member_bindings"]
    members = {cid: b["run_id"] for cid, b in bindings.items()}
    for cid, b in bindings.items():
        b["attempt_id"] = "attempt-" + cid
    for source in d["feedback"]["sources"]:
        source["attempt_id"] = bindings[source["candidate_id"]]["attempt_id"]
    for cid, summary in d["summaries"].items():
        summary.update(
            slu_f1=1.0 if cid.endswith("candidate-1") else 0.9,
            intent=0.8,
            model_calls=120,
            tool_calls=0,
        )
    for g in d["feedback"]["groups"]:
        for m in g["members"]:
            m["native_counts"].update(slot_f1_exact_fp=0, slot_f1_exact_fn=0)
    recipe = {
        "family_id": pilot.FAMILY,
        "expected_members": members,
        "required_rows_per_member": 20,
        "sample_ids": ids,
        "run_ids": {"read": pilot.READ_ID},
    }
    registration = {
        "schema": "saea-small-system-pilot-registration-v1",
        "family_id": pilot.FAMILY,
        "expected_members": members,
        "member_bindings": bindings,
        "rows_per_member": 20,
        "trajectory_cap": 160,
        "official_score_jobs_cap": 8,
        "new_proposal_opportunities": 0,
        "owner_decisions": [219, 220],
        "read_id": pilot.READ_ID,
    }
    registration["registration_sha256"] = content_hash(registration)
    owner = {
        "decision_id": 220,
        "status": "approved",
        "budget": {
            "members": 8,
            "rows_per_member": 20,
            "system_trajectories": 160,
            "new_proposals": 0,
        },
    }
    authority = {"read_run_id": pilot.READ_ID, "ledger_row_sha256": "a" * 64}
    d["read_authority"] = authority
    roster = {sid: roster[sid] for sid in ids}
    for i, row in enumerate(roster.values()):
        row["stratum"] = "a" if i < 10 else "b"
    supplement = {
        "resampling": {
            "bootstrap_draws": 20,
            "confidence": 0.95,
            "seed": 20261001,
            "unit": "paired utterance; keep all recording variants together",
        }
    }
    return d, recipe, registration, owner, authority, roster, supplement


def test_pilot_keeps_all_twenty_own_aa_unknown_cost_and_no_learning(tmp_path):
    d, recipe, registration, owner, authority, roster, supplement = fixture(tmp_path)
    pilot.validate_pilot_registration(recipe, registration, owner, authority)
    evidence = pilot.CompleteSystemPilotEvidence(canonical(d))
    report = pilot.analyze_pilot(
        evidence,
        recipe=recipe,
        registration=registration,
        roster=roster,
        supplement=supplement,
    )
    assert report["sample_count"] == 20 and report["cluster_count"] == 10
    assert report["status"] == "EXPLORATORY-PILOT-NO-ADOPTION"
    assert report["official_summaries"]["L-parent"]["slu_f1"] == 0.9
    assert report["execution"]["L-parent"]["completion_tokens"] is None
    assert len(report["per_stratum"]) == 2
    assert (
        report["branches"]["L"]["comparisons"]["same-request-null"]["slu_f1"][
            "point_estimate"
        ]
        == 0
    )
    assert report["optimizer_feedback_allowed"] is False
    assert not hasattr(evidence, "learning_view")
    with pytest.raises(PolicyError, match="pilot"):
        CompleteSystemFeedback(canonical(d)).learning_view(["L-parent", "L-parent-aa"])


@pytest.mark.parametrize(
    "fault",
    [
        "owner",
        "family",
        "rows",
        "duplicate",
        "test",
        "missing",
        "hash",
        "aa",
        "read",
        "budget",
        "identity",
    ],
)
def test_wrong_pilot_authority_refuses_before_results(tmp_path, monkeypatch, fault):
    d, recipe, registration, owner, authority, _, _ = fixture(tmp_path)
    if fault == "owner":
        owner["status"] = "pending"
    elif fault == "family":
        recipe["family_id"] = "update-2"
    elif fault == "rows":
        recipe["required_rows_per_member"] = 400
    elif fault == "duplicate":
        recipe["sample_ids"][0] = recipe["sample_ids"][1]
    elif fault == "test":
        recipe["sample_ids"][0] = "slurp:test:1"
    elif fault == "missing":
        recipe["expected_members"].pop("B-candidate-2")
    elif fault == "hash":
        registration["registration_sha256"] = "f" * 64
    elif fault == "aa":
        registration["member_bindings"]["L-parent-aa"]["bundle_id"] = "changed"
    elif fault == "read":
        authority["read_run_id"] = "OTHER-READ"
    elif fault == "budget":
        registration["new_proposal_opportunities"] = 1
    elif fault == "identity":
        registration["member_bindings"]["L-parent"]["run_id"] = "other"
    monkeypatch.setattr(
        pilot, "preflight_family", lambda *a: pytest.fail("results reached")
    )
    with pytest.raises(PolicyError):
        pilot.read_pilot_evidence(
            [],
            recipe=recipe,
            registration=registration,
            owner=owner,
            authority=authority,
        )


@pytest.mark.parametrize(
    "fault", ["duplicate", "missing", "counts", "source", "cost", "schema"]
)
def test_bad_measurement_cannot_be_described(tmp_path, fault):
    d, recipe, registration, _, _, roster, supplement = fixture(tmp_path)
    if fault == "duplicate":
        d["feedback"]["groups"][-1] = d["feedback"]["groups"][0]
    elif fault == "missing":
        d["feedback"]["groups"][0]["members"].pop()
    elif fault == "counts":
        d["summaries"]["L-parent"]["slu_f1"] = 0.7
    elif fault == "source":
        d["feedback"]["sources"][0]["config_hash"] = "wrong"
    elif fault == "cost":
        d["feedback"]["groups"][0]["members"][0]["execution"]["tool_calls"] = -1
    elif fault == "schema":
        d["schema"] = "saea-complete-system-feedback-v1"
    with pytest.raises((PolicyError, ValueError)):
        pilot.analyze_pilot(
            pilot.CompleteSystemPilotEvidence(canonical(d)),
            recipe=recipe,
            registration=registration,
            roster=roster,
            supplement=supplement,
        )


def test_all_seals_precede_reward_reads_and_no_utility_is_exported(
    tmp_path, monkeypatch
):
    d, recipe, registration, owner, authority, _, _ = fixture(tmp_path)
    bindings, metadata = [], []
    for cid, b in registration["member_bindings"].items():
        roster = tmp_path / (cid + "-roster.json")
        roster.write_text(
            json.dumps({"items": [{"sample_id": s} for s in recipe["sample_ids"]]})
        )
        import hashlib

        bindings.append(
            {
                "candidate_id": cid,
                "config": {
                    "manifest": {"path": "/fake/" + cid},
                    "construction_roster": {
                        "path": str(roster),
                        "sha256": hashlib.sha256(roster.read_bytes()).hexdigest(),
                    },
                },
            }
        )
        metadata.append(
            (
                {
                    "run_id": b["run_id"],
                    "config": {"config_hash": b["config_hash"]},
                    "split": {"count": 20, "ids": recipe["sample_ids"]},
                    "attempt": {"attempt_id": b["attempt_id"]},
                },
                {},
            )
        )
    monkeypatch.setattr(pilot, "preflight_family", lambda *a: metadata)
    seen = []

    def verify(path):
        seen.append(str(path))
        return SimpleNamespace(attempt_state="FINALIZED")

    monkeypatch.setattr(pilot, "verify_bundle", verify)

    def group_read(_):
        assert len(seen) == 8
        result = copy.deepcopy(d["feedback"])
        result["carrier_lock_key"] = "slurp"
        return result

    monkeypatch.setattr(pilot, "build_group_relative_feedback", group_read)
    monkeypatch.setattr(
        pilot,
        "_official_family_rows",
        lambda *a: (
            {
                cid: {
                    g["sample_id"]: next(
                        m["execution"] for m in g["members"] if m["candidate_id"] == cid
                    )
                    for g in d["feedback"]["groups"]
                }
                for cid in recipe["expected_members"]
            },
            d["summaries"],
        ),
    )
    evidence = pilot.read_pilot_evidence(
        bindings,
        recipe=recipe,
        registration=registration,
        owner=owner,
        authority=authority,
    ).as_json()
    assert "reference" not in evidence
    for g in evidence["feedback"]["groups"]:
        for m in g["members"]:
            assert not {"utility", "relative_return", "quality"} & set(m)
    seen.clear()
    monkeypatch.setattr(
        pilot, "verify_bundle", lambda *a: SimpleNamespace(attempt_state="OPENED")
    )
    with pytest.raises(PolicyError, match="seal"):
        pilot.read_pilot_evidence(
            bindings,
            recipe=recipe,
            registration=registration,
            owner=owner,
            authority=authority,
        )


def test_cli_unsigned_read_refuses_before_opening_any_member(tmp_path, monkeypatch):
    import importlib.util

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "pilot_cli_test", root / "scripts/analysis/system_text_pilot_read.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    d, recipe, registration, owner, authority, roster, supplement = fixture(tmp_path)

    def refuse(*a, **k):
        raise PolicyError("READ row is not root countersigned")

    monkeypatch.setattr(cli.CLI, "require_read_registration", refuse)
    monkeypatch.setattr(
        cli, "load_documents", lambda *a: (recipe, registration, owner, supplement)
    )
    monkeypatch.setattr(
        cli, "source_bindings", lambda *a: pytest.fail("opened sources before READ")
    )
    output = tmp_path / "data/analysis/pilot"
    with pytest.raises(PolicyError, match="countersigned"):
        cli.run(
            recipe_pin={},
            supplement_pin={},
            repo_root=tmp_path,
            data_root=tmp_path / "data",
            output=output,
        )
    assert not output.exists()


def cli_fixture(tmp_path, monkeypatch, fixture_factory=None):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pilot_cli_operator",
        Path(__file__).resolve().parents[2]
        / "scripts/analysis/system_text_pilot_read.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    d, recipe, registration, owner, authority, roster, supplement = (
        fixture_factory or fixture
    )(tmp_path)
    repo, data = tmp_path / "repo", tmp_path / "data"
    repo.mkdir()

    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return cli.pin(path)

    def rp(name, value):
        result = save(repo / name, value)
        return {"relpath": name, "sha256": result["sha256"]}

    recipe["analysis_roster"] = rp("roster.json", {"items": list(roster.values())})
    recipe["pilot_registration"] = rp("registration.json", registration)
    recipe_pin = rp("recipe.json", recipe)
    supplement.update(
        schema="saea-pilot-analysis-supplement-v1",
        recipe=recipe_pin,
        owner_decision=rp("owner.json", owner),
        stratum_metadata=rp("strata.json", {"items": list(roster.values())}),
        projection=RewardProjection(
            "synthetic-official-counts-v1", "slurp-slu-official-train",
            ("port_micro.slu_f1", "port_micro.intent_accuracy"), SLURP_NATIVE_FIELDS,
        ).as_json(),
    )
    supplement_pin = rp("supplement.json", supplement)
    manifests = {}
    for cid, b in registration["member_bindings"].items():
        directory = data / "runs" / b["run_id"] / b["attempt_id"]
        manifest_path = directory / "run-manifest.json"
        state = directory / "attempt.json"
        save(
            state,
            {
                "state": "FINALIZED",
                "run_id": b["run_id"],
                "attempt_id": b["attempt_id"],
            },
        )
        manifest = {
            "status": "COMPLETED",
            "run_id": b["run_id"],
            "plan": {"split_role": "discovery"},
            "config": {"config_hash": b["config_hash"]},
            "split": {"count": 20, "ids": recipe["sample_ids"]},
            "attempt": {"state_path": str(state), "attempt_id": b["attempt_id"]},
        }
        save(manifest_path, manifest)
        manifests[str(manifest_path)] = manifest
        job = {"manifest": str(manifest_path), "job_id": b["attempt_id"]}
        save(directory / "score-jobs.jsonl", job)
        save(
            directory / "score-batch/batch-summary.json",
            {
                "job_count": 1,
                "succeeded": 1,
                "failed": 0,
                "include_per_sample": True,
                "jobs": [
                    {
                        **job,
                        "status": "succeeded",
                        "returncode": 0,
                        "operation": "finalize",
                    }
                ],
            },
        )
    calls = {"verify": [], "reuse": [], "artifacts": []}
    monkeypatch.setattr(cli.CLI, "require_read_registration", lambda *a, **k: authority)

    def verify(path):
        calls["verify"].append(str(path))
        return SimpleNamespace(attempt_state="FINALIZED", manifest=manifests[str(path)])

    monkeypatch.setattr(cli, "verify_bundle", verify)

    def reuse(path, *, job_id, verified_bundle):
        assert len(calls["verify"]) == len(registration["member_bindings"])
        calls["reuse"].append(job_id)
        pin = save(path / "receipt.json", {"job_id": job_id})
        return SimpleNamespace(
            path=Path(pin["path"]), sha256=pin["sha256"], cell_id=job_id
        )

    monkeypatch.setattr(cli, "write_complete_saved_score_receipt", reuse)

    def artifact(config, path):
        from speech_aware_evidence_acquisition.rails.reward_links import RewardProjection
        RewardProjection.from_json(config["projection"])
        calls["artifacts"].append(config)
        save(path, {"stub": True})

    monkeypatch.setattr(cli, "build_reward_link_artifact", artifact)
    monkeypatch.setattr(
        cli,
        "read_pilot_evidence",
        lambda *a, **k: pilot.CompleteSystemPilotEvidence(canonical(d)),
    )
    return cli, repo, data, recipe_pin, supplement_pin, calls, d


def test_cli_retains_all_sources_create_only_and_no_scorer(tmp_path, monkeypatch):
    cli, repo, data, recipe_pin, supplement_pin, calls, d = cli_fixture(
        tmp_path, monkeypatch
    )
    output = data / "analysis/pilot"
    report = cli.run(
        recipe_pin=recipe_pin,
        supplement_pin=supplement_pin,
        repo_root=repo,
        data_root=data,
        output=output,
    )
    assert len(calls["reuse"]) == len(calls["artifacts"]) == 8
    assert (
        report["sample_count"] == 20 and report["optimizer_feedback_allowed"] is False
    )
    assert len(json.loads((output / "family.json").read_text())["bindings"]) == 8
    assert (output / "README.md").is_file() and (output / "evidence.json").is_file()
    with pytest.raises(PolicyError, match="fresh directory"):
        cli.run(
            recipe_pin=recipe_pin,
            supplement_pin=supplement_pin,
            repo_root=repo,
            data_root=data,
            output=output,
        )


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "failed",
        "job",
        "manifest",
        "config",
        "split",
        "roster",
        "strata",
        "supplement",
        "owner",
        "outside",
        "seal",
    ],
)
def test_cli_refuses_before_any_derivative_or_task_read(tmp_path, monkeypatch, fault):
    cli, repo, data, recipe_pin, supplement_pin, calls, d = cli_fixture(
        tmp_path, monkeypatch
    )
    output = data / "analysis/pilot"
    directory = next((data / "runs").iterdir())
    directory = next(directory.iterdir())
    if fault == "missing":
        (directory / "score-jobs.jsonl").unlink()
    elif fault in {"failed", "job"}:
        p = directory / "score-batch/batch-summary.json"
        value = json.loads(p.read_text())
        if fault == "failed":
            value["failed"] = 1
        else:
            value["jobs"][0]["job_id"] = "wrong"
        p.write_text(json.dumps(value))
    elif fault in {"manifest", "config", "split"}:
        p = directory / "run-manifest.json"
        value = json.loads(p.read_text())
        if fault == "manifest":
            value["status"] = "ABORTED"
        elif fault == "config":
            value["config"]["config_hash"] = "wrong"
        else:
            value["split"]["ids"].pop()
        p.write_text(json.dumps(value))
    elif fault in {"roster", "strata", "supplement", "owner"}:
        (repo / (fault + ".json")).write_text("{}")
    elif fault == "outside":
        output = data / "system-text-search/pilot"
    elif fault == "seal":
        monkeypatch.setattr(
            cli, "verify_bundle", lambda *a: SimpleNamespace(attempt_state="OPENED")
        )
    with pytest.raises((PolicyError, OSError)):
        cli.run(
            recipe_pin=recipe_pin,
            supplement_pin=supplement_pin,
            repo_root=repo,
            data_root=data,
            output=output,
        )
    assert not calls["reuse"] and not calls["artifacts"] and not output.exists()


def test_owner222_projects_every_learning_case_without_blind_or_formal_admission(
    tmp_path,
):
    d, recipe, registration, _, _, _, _ = fixture(tmp_path)
    _, reference, _, _ = update_fixture(tmp_path)
    amendment = {
        "decision_id": 222,
        "status": "approved",
        "family_id": pilot.FAMILY,
        "allow_learning_feedback": True,
        "recipient_branch": "L",
        "complete_family_required": True,
        "formal_adoption": False,
    }
    evidence = pilot.CompleteSystemPilotEvidence(canonical(d))
    projected = evidence.learning_projection(
        amendment=amendment, reference=reference
    ).as_json()
    assert projected["schema"] == "saea-exploratory-system-feedback-v1"
    assert projected["formal_adoption"] is False
    assert set(projected["summaries"]) == {
        c for c in pilot.MEMBERS if c.startswith("L-")
    }
    assert len(projected["feedback"]["groups"]) == 20
    assert len(projected["feedback"]["sources"]) == 4
    assert all(len(g["members"]) == 4 for g in projected["feedback"]["groups"])
    assert all(
        "utility" in m and "relative_return" in m
        for g in projected["feedback"]["groups"]
        for m in g["members"]
    )
    assert all("B-" not in json.dumps(g) for g in projected["feedback"]["groups"])
    assert projected["reference"] == reference.as_json()["reference"]
    assert projected["read_gate_family_sha256"] == content_hash(d)
    from speech_aware_evidence_acquisition.rails.system_search_protocol import (
        require_stage_feedback,
    )

    protocol = {
        "stages": [
            {
                "stage": pilot.FAMILY,
                "sample_ids": recipe["sample_ids"],
                "member_slots": list(projected["summaries"]),
            }
        ]
    }
    with pytest.raises(PolicyError, match="formal"):
        require_stage_feedback(
            protocol, pilot.FAMILY, CompleteSystemFeedback(canonical(projected))
        )
    for key, wrong in [
        ("status", "pending"),
        ("allow_learning_feedback", False),
        ("family_id", "other"),
        ("recipient_branch", "B"),
        ("formal_adoption", True),
    ]:
        with pytest.raises(PolicyError):
            evidence.learning_projection(
                amendment={**amendment, key: wrong}, reference=reference
            )


def test_learning_projection_uses_existing_proposer_capsule_and_exposure_accounting(
    tmp_path,
):
    from test_system_proposer_capsule import fixture as capsule_fixture
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import (
        ProposerCapsule,
    )
    from speech_aware_evidence_acquisition.rails.system_search_archive import (
        proposal_input,
        proposal_sources,
    )
    from speech_aware_evidence_acquisition.rails.system_text_policy import (
        SystemTextPolicyBundle,
    )

    d, recipe, registration, _, _, _, _ = fixture(tmp_path)
    _, reference, _, _ = update_fixture(tmp_path)
    amendment = {
        "decision_id": 222,
        "status": "approved",
        "family_id": pilot.FAMILY,
        "allow_learning_feedback": True,
        "recipient_branch": "L",
        "complete_family_required": True,
        "formal_adoption": False,
    }
    feedback = pilot.CompleteSystemPilotEvidence(canonical(d)).learning_projection(
        amendment=amendment, reference=reference
    )
    packet, roots = capsule_fixture(tmp_path)
    seed = SystemTextPolicyBundle.from_json(packet["parent_policy"])
    packet = proposal_input(
        branch="L",
        round_index=3,
        slot=1,
        seed=seed,
        parent=seed,
        feedback=feedback,
        model_version="gpt-6-astra",
        session_id="fresh-owner222",
        input_token_cap=32768,
        output_token_cap=4096,
    )
    from speech_aware_evidence_acquisition.rails.system_optimization import exploratory_selection
    protocol = {"exploratory_learning": {"relpath": "binding.json", "sha256": "b" * 64}}
    for member in registration["member_bindings"].values():
        member["bundle_id"] = seed.bundle_id
    packet["protocol_sha256"] = content_hash(protocol)
    packet["selection"] = exploratory_selection(feedback, registration=registration,
        binding={"next_round": 3, "parent_id": seed.bundle_id, "complementary_ids": []},
        protocol=protocol, parents=[seed.as_json()])
    packet["input_sha256"] = content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    assert capsule.as_json()["packet"]["branch"] == "L"
    assert "B-parent" not in json.dumps(packet) and "B-candidate" not in json.dumps(
        packet
    )
    # The source tracker must preserve all pilot input exposure, not just improved cases.
    sources = proposal_sources(packet, {"status": "no-change", "proposal": None})
    exposed = set().union(*(set(s["sample_ids"]) for s in sources))
    assert set(recipe["sample_ids"]) <= exposed
    with pytest.raises(PolicyError, match="blind"):
        proposal_input(
            branch="B",
            round_index=3,
            slot=1,
            seed=seed,
            parent=seed,
            feedback=feedback,
            model_version="gpt-6-astra",
            session_id="fresh-blind",
            input_token_cap=32768,
            output_token_cap=4096,
        )


def test_cli_owner222_learning_export_reverifies_reference_and_is_branch_isolated(
    tmp_path, monkeypatch
):
    cli, repo, data, recipe_pin, supplement_pin, calls, d = cli_fixture(
        tmp_path, monkeypatch
    )
    _, reference, _, _ = update_fixture(tmp_path)
    amendment = {
        "decision_id": 222,
        "status": "approved",
        "family_id": pilot.FAMILY,
        "allow_learning_feedback": True,
        "recipient_branch": "L",
        "complete_family_required": True,
        "formal_adoption": False,
    }
    p = repo / "amendment.json"
    p.write_text(json.dumps(amendment))
    amendment_pin = {"relpath": p.name, "sha256": cli.pin(p)["sha256"]}
    seen = []

    def read_reference(path, **kwargs):
        seen.append(path)
        return reference

    monkeypatch.setattr(cli.CLI, "read_family", read_reference)
    ref_path = tmp_path / "original-qualified-initial-family.json"
    output = data / "analysis/pilot-learning"
    report = cli.run(
        recipe_pin=recipe_pin,
        supplement_pin=supplement_pin,
        repo_root=repo,
        data_root=data,
        output=output,
        learning_amendment_pin=amendment_pin,
        reference_family_path=ref_path,
    )
    assert seen == [ref_path]
    learning = json.loads((output / "learning-feedback.json").read_text())
    assert len(learning["feedback"]["groups"]) == 20
    assert all(cid.startswith("L-") for cid in learning["summaries"])
    assert report["learning_projection"]["owner_decision"] == amendment_pin
    assert (
        report["optimizer_feedback_allowed"] is False
    )  # Full root report is not proposer input.
    with pytest.raises(PolicyError, match="both owner222"):
        cli.run(
            recipe_pin=recipe_pin,
            supplement_pin=supplement_pin,
            repo_root=repo,
            data_root=data,
            output=data / "analysis/missing-reference",
            learning_amendment_pin=amendment_pin,
        )
