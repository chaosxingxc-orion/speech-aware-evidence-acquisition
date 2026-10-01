"""Prospective update membership; synthetic proposals, no model or result reads."""

import copy
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import (
    SystemSearchArchive,
    proposal_input,
    proposal_sources,
)
from speech_aware_evidence_acquisition.rails.system_search_protocol import (
    build_protocol,
    stage_for,
    require_stage_feedback,
)
from speech_aware_evidence_acquisition.rails.system_search_stage import (
    freeze_update_stage,
    validate_stage_registration,
)
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    SystemTextPolicyBundle,
    TextPolicyUpdateProposal,
    apply_text_proposal,
    canonical,
)
from test_system_search_protocol import rosters
from test_system_text_policy import seed_document


def fixture(tmp_path, invalid=("L-candidate-2",)):
    archive = SystemSearchArchive(tmp_path / "archive")
    seed = SystemTextPolicyBundle.from_json(seed_document())
    archive.store_policy(seed)
    protocol = build_protocol(rosters())
    protocol.update(
        seed_bundle={"bundle_id": seed.bundle_id}, proposer_exact_version="GPT6-fixture"
    )
    members = {
        cid: {
            "bundle_id": seed.bundle_id,
            "run_id": "RUN-" + cid,
            "config_hash": content_hash(cid),
        }
        for cid in stage_for(protocol, "update-1")["member_slots"]
    }
    feedback = CompleteSystemFeedback(
        canonical(
            {
                "summaries": {"seed": {}, "seed-aa": {}},
                "reference": {"sample_ids": []},
                "feedback": {"groups": []},
            }
        )
    )
    for branch in ("L", "B"):
        for slot in (1, 2):
            cid = f"{branch}-candidate-{slot}"
            packet = proposal_input(
                branch=branch,
                round_index=1,
                slot=slot,
                seed=seed,
                parent=seed,
                model_version="GPT6-fixture",
                session_id=cid,
                input_token_cap=32768,
                output_token_cap=4096,
                feedback=feedback if branch == "L" else None,
            )
            packet["protocol_sha256"] = content_hash(protocol)
            packet["input_sha256"] = content_hash(
                {k: v for k, v in packet.items() if k != "input_sha256"}
            )
            archive.store_input(packet)
            doc = {
                "schema": "saea-text-policy-update-proposal-v1",
                "branch": branch,
                "round": 1,
                "slot": slot,
                "parent_ids": [seed.bundle_id],
                "changes": {},
                "rationale": "Preserve the starting system.",
                "hypotheses": [],
                "evidence": [],
            }
            receipt = {
                "raw_response": "invalid synthetic response"
                if cid in invalid
                else json.dumps(doc),
                "session_id": cid,
                "model_version": "GPT6-fixture",
                "input_sha256": packet["input_sha256"],
                "input_tokens": 100,
                "output_tokens": 100,
            }
            if isinstance(invalid, dict) and cid in invalid:
                receipt["raw_response"] = json.dumps(doc)
                invalid[cid](receipt, doc)
            result = archive.import_response(
                branch=branch, round_index=1, slot=slot, receipt=receipt
            )
            if result["status"] == "invalid":
                members[cid]["bundle_id"] = None
                members[cid]["config_hash"] = None
            else:
                record = json.loads(
                    (archive.root / f"proposals/{branch}-1-{slot}.json").read_text()
                )
                bundle = apply_text_proposal(
                    TextPolicyUpdateProposal.from_json(doc),
                    parents=[seed],
                    added_sources=proposal_sources(packet, record),
                )
                archive.store_policy(bundle)
                archive.record_compilation(
                    branch=branch,
                    round_index=1,
                    slot=slot,
                    bundle=bundle,
                    configuration={"synthetic": cid},
                )
                members[cid]["bundle_id"] = bundle.bundle_id
    return archive, protocol, members, tmp_path / "data"


def freeze(archive, protocol, members, data):
    return freeze_update_stage(
        archive,
        protocol=protocol,
        round_index=1,
        member_bindings=members,
        data_root=data,
    )


def test_invalid_proposal_consumes_its_slot_before_fixed_whole_family_freeze(tmp_path):
    archive, protocol, members, data = fixture(tmp_path)
    frozen = freeze(archive, protocol, members, data)
    assert set(frozen["expected_members"]) == set(members) - {"L-candidate-2"}
    assert frozen["trajectory_cap"] == 2800 and frozen["official_score_jobs_cap"] == 7
    assert frozen["proposal_opportunities_consumed"] == 4
    assert set(frozen["exclusions"]) == {"L-candidate-2"}
    assert frozen["runtime_admission"] == "separate-required"
    assert frozen["evaluation"]["member_bindings"]["L-parent"] == members["L-parent"]
    validate_stage_registration(frozen, protocol=protocol)
    with pytest.raises(PolicyError, match="exists|consumed"):
        freeze(archive, protocol, members, data)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-slot",
        "omit-aa",
        "drop-valid",
        "revive-invalid",
        "wrong-bundle",
        "wrong-parent",
        "changed-input",
        "changed-response",
        "no-compilation",
        "unadmitted-proposer",
        "prior-run",
        "excluded-run",
        "false-invalid",
    ],
)
def test_freeze_refuses_unqualified_or_post_contact_changes(tmp_path, fault):
    archive, protocol, members, data = fixture(tmp_path)
    if fault == "missing-slot":
        (archive.root / "imports/B-1-2.json").unlink()
    elif fault == "omit-aa":
        members.pop("L-parent-aa")
    elif fault == "drop-valid":
        members["B-candidate-1"].update(bundle_id=None, config_hash=None)
    elif fault == "revive-invalid":
        members["L-candidate-2"].update(members["L-parent"])
    elif fault == "wrong-bundle":
        members["L-candidate-1"]["bundle_id"] = members["L-parent"]["bundle_id"]
    elif fault == "wrong-parent":
        members["L-parent"]["bundle_id"] = members["L-candidate-1"]["bundle_id"]
    elif fault == "changed-input":
        p = archive.root / "inputs/L-1-2.json"
        d = json.loads(p.read_text())
        d["session_id"] = "tampered"
        p.write_text(json.dumps(d))
    elif fault == "changed-response":
        p = archive.root / "responses/L-1-2.json"
        d = json.loads(p.read_text())
        d["raw_response"] = "tampered"
        p.write_text(json.dumps(d))
    elif fault == "no-compilation":
        (archive.root / "compilations/L-1-1.json").unlink()
    elif fault == "false-invalid":
        p = archive.root / "imports/B-1-1.json"
        d = json.loads(p.read_text())
        d["status"] = "invalid"
        p.write_text(json.dumps(d))
        members["B-candidate-1"].update(bundle_id=None, config_hash=None)
        (archive.root / "compilations/B-1-1.json").unlink()
    elif fault == "unadmitted-proposer":
        protocol["proposer_exact_version"] = None
    elif fault in {"prior-run", "excluded-run"}:
        cid = "L-parent" if fault == "prior-run" else "L-candidate-2"
        (data / "runs" / members[cid]["run_id"]).mkdir(parents=True)
    with pytest.raises((PolicyError, FileNotFoundError)):
        freeze(archive, protocol, members, data)
    assert not (archive.root / "stages/update-1.json").exists()


@pytest.mark.parametrize(
    "excluded",
    [(), ("L-candidate-1", "L-candidate-2", "B-candidate-1", "B-candidate-2")],
)
def test_zero_or_all_invalid_candidates_retain_both_parent_aa_pairs(tmp_path, excluded):
    archive, protocol, members, data = fixture(tmp_path, excluded)
    frozen = freeze(archive, protocol, members, data)
    assert frozen["trajectory_cap"] == 400 * (8 - len(excluded))
    assert {"L-parent", "L-parent-aa", "B-parent", "B-parent-aa"} <= set(
        frozen["expected_members"]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "input-budget",
        "output-budget",
        "session",
        "unknown-field",
        "foreign-parent",
        "wrong-slot",
    ],
)
def test_exclusions_reverify_objective_import_faults(tmp_path, fault):
    def mutate(receipt, proposal):
        if fault == "input-budget":
            receipt["input_tokens"] = 32769
        elif fault == "output-budget":
            receipt["output_tokens"] = 4097
        elif fault == "session":
            receipt["session_id"] = "wrong-session"
        elif fault == "unknown-field":
            receipt["unregistered"] = True
        else:
            if fault == "foreign-parent":
                proposal["parent_ids"] = ["f" * 64]
            elif fault == "wrong-slot":
                proposal["slot"] = 1
            receipt["raw_response"] = json.dumps(proposal)

    archive, protocol, members, data = fixture(tmp_path, {"L-candidate-2": mutate})
    result = freeze(archive, protocol, members, data)
    assert set(result["exclusions"]) == {"L-candidate-2"}


def test_complete_feedback_uses_only_prospectively_frozen_membership(tmp_path):
    archive, protocol, members, data = fixture(tmp_path)
    registration = freeze(archive, protocol, members, data)
    value = {
        "summaries": {cid: {} for cid in registration["expected_members"]},
        "feedback": {
            "groups": [
                {"sample_id": sid}
                for sid in stage_for(protocol, "update-1")["sample_ids"]
            ]
        },
        "read_authority": {"stage_registration": registration},
    }
    feedback = SimpleNamespace(as_json=lambda: value)
    require_stage_feedback(protocol, "update-1", feedback)
    value["summaries"].pop("L-candidate-1")
    with pytest.raises(PolicyError, match="complete preceding family"):
        require_stage_feedback(protocol, "update-1", feedback)
    value["summaries"] = {cid: {} for cid in registration["expected_members"]}
    value["read_authority"] = {}
    with pytest.raises(PolicyError):
        require_stage_feedback(protocol, "update-1", feedback)


@pytest.mark.parametrize(
    "fault", ["protocol", "roster", "budget", "aa", "disposition", "run"]
)
def test_registration_revalidation_refuses_a_rehashed_bad_manifest(tmp_path, fault):
    archive, protocol, members, data = fixture(tmp_path)
    d = freeze(archive, protocol, members, data)
    if fault == "protocol":
        d["protocol_sha256"] = "f" * 64
    elif fault == "roster":
        d["roster_sha256"] = "f" * 64
    elif fault == "budget":
        d["trajectory_cap"] += 400
    elif fault == "aa":
        d["expected_members"].pop("L-parent-aa")
    elif fault == "disposition":
        d["exclusions"]["L-candidate-2"]["status"] = "failed-after-contact"
    else:
        d["evaluation"]["member_bindings"]["L-parent"]["run_id"] = "DIFFERENT-RUN"
    d["registration_sha256"] = content_hash(
        {k: v for k, v in d.items() if k != "registration_sha256"}
    )
    with pytest.raises(PolicyError):
        validate_stage_registration(d, protocol=protocol)


def test_cli_freezes_membership_but_never_admits_runtime(tmp_path, capsys):
    from test_system_text_search_cli import cli, write

    archive, protocol, members, data = fixture(tmp_path)
    args = [
        "--archive",
        str(archive.root),
        "freeze-update",
        "--round",
        "1",
        "--protocol",
        write(tmp_path / "protocol.json", protocol),
        "--member-bindings",
        write(tmp_path / "bindings.json", members),
        "--data-root",
        str(data),
    ]
    cli.main(args)
    assert '"members": 7' in capsys.readouterr().out
    assert not data.exists()
    saved = cli.read(archive.root / "stages/update-1.json")
    assert saved["runtime_admission"] == "separate-required"
    assert (
        saved["evaluation"]["member_bindings"]["B-parent-aa"]["bundle_id"]
        == protocol["seed_bundle"]["bundle_id"]
    )


@pytest.mark.parametrize("round_index", [2, 3])
@pytest.mark.parametrize("changed_selection", [False, True])
def test_later_round_freeze_binds_the_preceding_learning_retention(
    tmp_path, round_index, changed_selection
):
    from test_system_search_selection import selection_fixture, retain

    archive, protocol, feedback, evaluation = selection_fixture(
        tmp_path, f"update-{round_index - 1}"
    )
    selection = retain(archive, protocol, feedback, evaluation)
    seed = archive.load_policy(protocol["seed_bundle"]["bundle_id"])
    learned = archive.load_policy(selection["active_ids"][0])
    members = {}
    for branch in ("L", "B"):
        parent = learned if branch == "L" else seed
        for suffix in ("parent", "parent-aa"):
            cid = f"{branch}-{suffix}"
            members[cid] = {
                "bundle_id": parent.bundle_id,
                "run_id": "NEXT-" + cid,
                "config_hash": content_hash(cid),
            }
        for slot in (1, 2):
            cid = f"{branch}-candidate-{slot}"
            packet = proposal_input(
                branch=branch,
                round_index=round_index,
                slot=slot,
                seed=seed,
                parent=parent,
                model_version=protocol["proposer_exact_version"],
                session_id=f"round-{round_index}-{cid}",
                input_token_cap=32768,
                output_token_cap=4096,
                feedback=feedback.learning_view(
                    [c for c in feedback.as_json()["summaries"] if c.startswith("L-")]
                )
                if branch == "L"
                else None,
            )
            if branch == "L":
                packet["selection"] = selection
            packet["protocol_sha256"] = content_hash(protocol)
            packet["input_sha256"] = content_hash(
                {k: v for k, v in packet.items() if k != "input_sha256"}
            )
            archive.store_input(packet)
            doc = {
                "schema": "saea-text-policy-update-proposal-v1",
                "branch": branch,
                "round": round_index,
                "slot": slot,
                "parent_ids": [parent.bundle_id],
                "changes": {},
                "rationale": "Keep this branch's frozen parent.",
                "hypotheses": [],
                "evidence": [],
            }
            response = {
                "raw_response": json.dumps(doc),
                "session_id": packet["session_id"],
                "model_version": packet["model_version"],
                "input_sha256": packet["input_sha256"],
                "input_tokens": 100,
                "output_tokens": 100,
            }
            imported = archive.import_response(
                branch=branch, round_index=round_index, slot=slot, receipt=response
            )
            assert imported["status"] == "no-change"
            record = json.loads(
                (
                    archive.root / f"proposals/{branch}-{round_index}-{slot}.json"
                ).read_text()
            )
            bundle = apply_text_proposal(
                TextPolicyUpdateProposal.from_json(doc),
                parents=[parent],
                added_sources=proposal_sources(packet, record),
            )
            archive.store_policy(bundle)
            archive.record_compilation(
                branch=branch,
                round_index=round_index,
                slot=slot,
                bundle=bundle,
                configuration={"synthetic": cid},
            )
            members[cid] = {
                "bundle_id": bundle.bundle_id,
                "run_id": "NEXT-" + cid,
                "config_hash": content_hash(cid),
            }
    if changed_selection:
        path = archive.root / f"retentions/update-{round_index - 1}/L.json"
        value = json.loads(path.read_text())
        value["active_ids"].reverse()
        path.write_text(json.dumps(value))
        with pytest.raises(PolicyError, match="retention"):
            freeze_update_stage(
                archive,
                protocol=protocol,
                round_index=round_index,
                member_bindings=members,
                data_root=tmp_path / "data",
            )
        assert not (archive.root / f"stages/update-{round_index}.json").exists()
    else:
        frozen = freeze_update_stage(
            archive,
            protocol=protocol,
            round_index=round_index,
            member_bindings=members,
            data_root=tmp_path / "data",
        )
        assert frozen["trajectory_cap"] == 3200
        assert (
            frozen["evaluation"]["member_bindings"]["L-parent"]["bundle_id"]
            == learned.bundle_id
        )
        assert (
            frozen["evaluation"]["member_bindings"]["B-parent"]["bundle_id"]
            == seed.bundle_id
        )


@pytest.mark.parametrize("fault", ["reused-session", "mixed-model"])
def test_freeze_rechecks_sequence_wide_proposer_identity(tmp_path, fault):
    archive, protocol, members, data = fixture(tmp_path)
    prior = copy.deepcopy(archive.history()[0])
    prior.update(branch="L", round=2, slot=1)
    if fault == "mixed-model":
        prior["receipt"].update(
            model_version="another-model", session_id="another-session"
        )
    archive._write("proposals/L-2-1.json", prior)
    with pytest.raises(PolicyError, match="invalid response cannot activate"):
        freeze(archive, protocol, members, data)
    assert not (archive.root / "stages/update-1.json").exists()


def recipe_fixture(tmp_path):
    from test_system_text_search_cli import read_fixture

    archive, protocol, members, data = fixture(tmp_path)
    registration = freeze(archive, protocol, members, data)
    spec, ledger, path = read_fixture(tmp_path)
    spec.update(family_id="update-1", expected_members=registration["expected_members"])
    recipe = {
        "read_run_id": "FIXTURE-READ",
        "family_id": "update-1",
        "expected_members": registration["expected_members"],
        "system_search_stage": registration,
        "system_search_evaluation": registration["evaluation"],
    }
    path.write_text(json.dumps(recipe))
    import hashlib

    spec["read_registration"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return archive, protocol, registration, spec, path


def test_signed_recipe_carries_frozen_membership_into_complete_reader(
    tmp_path, monkeypatch
):
    from test_system_text_search_cli import cli, write

    archive, protocol, registration, spec, path = recipe_fixture(tmp_path)
    value = {
        "family_id": "update-1",
        "summaries": {cid: {} for cid in registration["expected_members"]},
        "feedback": {
            "groups": [
                {"sample_id": sid}
                for sid in stage_for(protocol, "update-1")["sample_ids"]
            ]
        },
    }
    calls = []

    def complete(*a, **k):
        calls.append(k)
        return CompleteSystemFeedback(canonical(value))

    monkeypatch.setattr(cli.CompleteSystemFeedback, "from_family", complete)
    feedback = cli.read_family(
        write(tmp_path / "family.json", spec), repo_root=tmp_path
    )
    require_stage_feedback(protocol, "update-1", feedback)
    assert calls[0]["expected_members"] == registration["expected_members"]
    assert feedback.as_json()["read_authority"]["stage_registration"] == registration


def test_read_rejects_recipe_membership_edit_before_any_result_source(
    tmp_path, monkeypatch
):
    import hashlib
    from test_system_text_search_cli import cli, write

    archive, protocol, registration, spec, path = recipe_fixture(tmp_path)
    recipe = json.loads(path.read_text())
    recipe["expected_members"].pop("L-candidate-1")
    spec["expected_members"] = recipe["expected_members"]
    path.write_text(json.dumps(recipe))
    spec["read_registration"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    spec["reference_family"] = str(tmp_path / "DO-NOT-OPEN.json")
    monkeypatch.setattr(
        cli.CompleteSystemFeedback,
        "from_family",
        lambda *a, **k: pytest.fail("opened a score source"),
    )
    with pytest.raises(PolicyError, match="frozen stage"):
        cli.read_family(write(tmp_path / "family.json", spec), repo_root=tmp_path)


def test_learning_projection_and_retention_do_not_expose_blind_stage_dispositions(
    tmp_path,
):
    from test_system_search_selection import selection_fixture

    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    d = feedback.as_json()
    # An opaque fixture proves projection does not preserve any hidden fields.
    d["read_authority"]["stage_registration"] = {"B-candidate-1": "private disposition"}
    projected = CompleteSystemFeedback(canonical(d)).learning_view(
        [c for c in d["summaries"] if c.startswith("L-")]
    )
    authority = projected.as_json()["read_authority"]
    assert "stage_registration" not in authority
    assert authority["stage_registration_sha256"] == content_hash(
        d["read_authority"]["stage_registration"]
    )
    assert "private disposition" not in canonical(projected.as_json())
    # Use a real valid reduced registration for the retention path.
    a, p, m, data = fixture(tmp_path / "reduced")
    registered = freeze(a, p, m, data)
    d["summaries"] = {
        cid: d["summaries"][cid] for cid in registered["expected_members"]
    }
    d["feedback"]["sources"] = [
        s for s in d["feedback"]["sources"] if s["candidate_id"] in d["summaries"]
    ]
    registered["evaluation"]["member_bindings"] = {
        cid: evaluation["member_bindings"][cid] for cid in d["summaries"]
    }
    registered["planned_runs"] = {
        cid: "RUN-" + cid for cid in registered["planned_runs"]
    }
    registered["expected_members"] = {cid: "RUN-" + cid for cid in d["summaries"]}
    registered["protocol_sha256"] = content_hash(protocol)
    registered["evaluation"]["protocol_sha256"] = content_hash(protocol)
    registered["registration_sha256"] = content_hash(
        {k: v for k, v in registered.items() if k != "registration_sha256"}
    )
    d["read_authority"]["stage_registration"] = registered
    record = archive.retain_feedback(
        protocol=protocol,
        stage_name="update-1",
        feedback=CompleteSystemFeedback(canonical(d)),
        evaluation=registered["evaluation"],
        branch="L",
        selected_ids=[evaluation["member_bindings"]["L-candidate-1"]["bundle_id"]],
    )
    assert "stage_registration" not in record["read_authority"]
    assert "B-candidate-1" not in canonical(record)
