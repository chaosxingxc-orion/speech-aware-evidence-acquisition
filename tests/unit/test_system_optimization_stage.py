"""Freeze exact extra-round panels without dispatch or result access."""

import copy
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import system_search_stage as stage
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import (
    proposal_input,
    proposal_sources,
)
from speech_aware_evidence_acquisition.rails.system_search_allocations import (
    register_extension,
)
from speech_aware_evidence_acquisition.rails.system_optimization import (
    panel_identities,
    panel_member_run_id,
)
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    TextPolicyUpdateProposal,
    apply_text_proposal,
    canonical,
)
from test_system_search_allocations import fixture as allocation_fixture, write_pin
from test_system_optimization import fixture as pool_fixture, learning_fixture
from test_system_search_measurement import profile as measurement_profile


UNSET = object()


def fixture(tmp_path, rows=50, *, profile=UNSET, successor=False):
    if successor:
        from test_system_search_successor import setup
        from speech_aware_evidence_acquisition.rails.system_search_successor import register_successor
        old, archive, repo, seed, ext, _ = setup(tmp_path)
        ext["owner"] = write_pin(repo, ext["owner"]["relpath"], {
            "decision_id": 227, "status": "approved", "authorized_rows_per_member": [4, 20, 50, 100, 200],
        })
        register_successor(old, archive, ext, repo_root=repo)
    else:
        archive, repo, seed, ext = allocation_fixture(tmp_path)
    growth = write_pin(
        repo,
        "growth.json" if successor else ext["owner"]["relpath"],
        {
            "decision_id": 223,
            "status": "approved",
            "stage_ladder": [20, 50, 100, 200, 400],
        },
    )
    if not successor:
        ext["owner"] = growth
        register_extension(archive, ext, repo_root=repo)
    protocol, pool = pool_fixture(repo)
    protocol.update(
        updates=4,
        allocation_extension=ext,
        proposer_exact_version=ext["model_version"],
        seed_bundle={"bundle_id": seed.bundle_id},
        proposal_input_token_cap=ext["input_token_cap"],
        proposal_output_token_cap=ext["output_token_cap"],
    )
    protocol["optimization_panel"]["stages"] = ["update-4"]
    protocol["stages"][0]["stage"] = "update-4"
    if profile is not UNSET:
        protocol["measurement_profile"] = copy.deepcopy(profile)
    archive.store_policy(seed)
    _, learning = learning_fixture(tmp_path / "learning")
    if profile is not UNSET:
        learning["feedback"]["measurement_profile"] = copy.deepcopy(profile)
        learning["selection"]["measurement_profile"] = copy.deepcopy(profile)
        learning["selection"]["learning_feedback_sha256"] = content_hash(learning["feedback"])
    learning["selection"].update(
        next_round=4,
        active_ids=[seed.bundle_id],
        protocol_sha256=content_hash(protocol),
    )
    for member in learning["selection"]["member_bindings"].values():
        member["bundle_id"] = seed.bundle_id
    learning["selection"]["selection_sha256"] = content_hash(
        {k: v for k, v in learning["selection"].items() if k != "selection_sha256"}
    )
    members = {}
    for branch in ("L", "B"):
        for role in ("parent", "parent-aa", "candidate-1", "candidate-2"):
            cid = branch + "-" + role
            members[cid] = {
                "run_id": panel_member_run_id(4, rows, cid, successor=successor) if successor else panel_member_run_id(4, rows, cid),
                "attempt_id": "attempt-" + cid.lower() + f"-{rows}",
                "bundle_id": seed.bundle_id,
                "config_hash": content_hash(cid),
            }
        for slot in (1, 2):
            cid = f"{branch}-candidate-{slot}"
            packet = proposal_input(
                branch=branch,
                round_index=4,
                slot=slot,
                seed=seed,
                parent=seed,
                model_version=ext["model_version"],
                session_id=f"{branch}-4-{slot}",
                input_token_cap=ext["input_token_cap"],
                output_token_cap=ext["output_token_cap"],
                feedback=CompleteSystemFeedback(canonical(learning["feedback"]))
                if branch == "L"
                else None,
                allocation_extension=ext,
            )
            packet["protocol_sha256"] = content_hash(protocol)
            packet["optimization_scope"] = {
                "purpose": "reused-optimization-panel",
                "editable": ["role_text"],
                "plan_sha256": protocol["optimization_panel"]["plan"]["sha256"],
            }
            if branch == "L":
                packet["selection"] = copy.deepcopy(learning["selection"])
            packet["input_sha256"] = content_hash(
                {k: v for k, v in packet.items() if k != "input_sha256"}
            )
            archive.store_input(packet)
            doc = {
                "schema": "saea-text-policy-update-proposal-v1",
                "branch": branch,
                "round": 4,
                "slot": slot,
                "parent_ids": [seed.bundle_id],
                "changes": {}
                if slot == 1
                else {
                    "role_text": {
                        "solver": "Use grounded slots only. Deliver exact task JSON."
                    }
                },
                "rationale": "Preserve or repair task-shaped delivery.",
                "hypotheses": [],
                "evidence": [],
            }
            response = {
                "raw_response": "" if successor and slot == 1 else json.dumps(doc),
                "session_id": packet["session_id"],
                "model_version": ext["model_version"],
                "input_sha256": packet["input_sha256"],
                "input_tokens": None if successor and slot == 1 else 100,
                "output_tokens": None if successor and slot == 1 else 100,
            }
            archive.import_response(
                branch=branch, round_index=4, slot=slot, receipt=response
            )
            if successor and slot == 1:
                members[cid].update(bundle_id=None, config_hash=None)
                continue
            record = json.loads(
                (archive.root / f"proposals/{branch}-4-{slot}.json").read_text()
            )
            bundle = apply_text_proposal(
                TextPolicyUpdateProposal.from_json(doc, allocation_extension=ext),
                parents=[seed],
                added_sources=proposal_sources(packet, record),
            )
            archive.store_policy(bundle)
            archive.record_compilation(
                branch=branch,
                round_index=4,
                slot=slot,
                bundle=bundle,
                configuration={"source_prefix": 20, "candidate": cid},
            )
            members[cid]["bundle_id"] = bundle.bundle_id
    family, _ = panel_identities(4, rows, successor=True) if successor else panel_identities(4, rows)
    evaluation_pin = None
    if successor:
        learning_pin = write_pin(repo, "learning222.json", {
            "decision_id": 222, "status": "approved", "family_id": "pilot20-owner220",
            "allow_learning_feedback": True, "recipient_branch": "L", "complete_family_required": True,
            "formal_adoption": False,
        })
        evaluation_pin = write_pin(repo, "successor-evaluation.json", {
            "schema": "saea-owner227-successor-panel-evaluation-v1", "reviewer": "ChatGPT root",
            "status": "approved", "owner227": ext["owner"], "growth_owner_decision": growth,
            "learning_owner_decision": learning_pin, "proposal_protocol_sha256": content_hash(protocol),
            "proposal_round": 4, "pool_sample_ids_sha256": content_hash(pool),
            "admitted_members": sorted(set(members) - {"L-candidate-1", "B-candidate-1"}),
            "excluded_members": ["B-candidate-1", "L-candidate-1"], "progressive_sizes": [20, 50, 100, 200],
            "new_proposal_opportunities": 0, "automatic_expansion": False,
            "independent_validation": False, "formal_adoption": False,
        })
    review = {
        "schema": "saea-fixed400-panel-stage-review-v1",
        "reviewer": "ChatGPT root",
        "status": "completed",
        "family_id": family,
        "proposal_protocol_sha256": content_hash(protocol),
        "pool_sample_ids_sha256": content_hash(pool),
        "rows_per_member": rows,
        "member_bindings_sha256": content_hash(members),
        "prior_complete_read_ids": ["SAEA-SLURP-SYSTEM-TEXT-PILOT20-OWNER220-READ-V1"],
        "rationale": "Synthetic reviewed preparation; no runtime authority or quality claim.",
    }
    review_pin = write_pin(repo, "review.json", review)
    if successor:
        review["evaluation_authority"] = evaluation_pin
        review_pin = write_pin(repo, "review.json", review)
        return archive, repo, tmp_path / "data", protocol, members, review_pin, pool, evaluation_pin
    return archive, repo, tmp_path / "data", protocol, members, review_pin, pool


def freeze(f, rows=50):
    archive, repo, data, protocol, members, review, pool = f
    return stage.freeze_optimization_panel(
        archive,
        protocol=protocol,
        round_index=4,
        rows=rows,
        member_bindings=members,
        root_review=review,
        repo_root=repo,
        data_root=data,
    )


@pytest.mark.parametrize("rows", [20, 50, 100, 200, 400])
def test_freeze_complete_extra_round_keeps_spent_no_change_and_exact_panel(
    tmp_path, rows
):
    f = fixture(tmp_path, rows)
    archive, repo, data, protocol, members, review, pool = f
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    frozen = freeze(f, rows)
    reg = frozen["registration"]
    assert reg["rows_per_member"] == rows and reg["trajectory_cap"] == 8 * rows
    assert reg["member_bindings"] == members and reg["new_proposal_opportunities"] == 0
    assert reg["root_stage_review_receipt"] == review
    assert reg["allocations"]["L-candidate-1"]["status"] == "no-change"
    assert reg["allocations"]["B-candidate-2"]["status"] == "duplicate"
    assert reg["runtime_admission"] == "separate-required"
    assert "measurement_profile" not in reg
    assert "measurement_profile" not in frozen["recipe"]
    assert set(reg) == {
        "schema", "family_id", "proposal_round", "expected_members", "member_bindings",
        "rows_per_member", "trajectory_cap", "official_score_jobs_cap",
        "new_proposal_opportunities", "owner_decisions", "read_id", "root_stage_review",
        "root_stage_review_receipt", "independent_validation", "automatic_expansion",
        "scientific_role", "proposal_protocol_sha256", "pool_sample_ids_sha256",
        "prefix_sample_ids_sha256", "allocations", "retained_exposure",
        "runtime_admission", "registration_sha256",
    }
    assert set(frozen["recipe"]) == {
        "family_id", "expected_members", "sample_ids", "required_rows_per_member", "run_ids",
    }
    assert frozen["recipe"]["sample_ids"] == pool[:rows]
    assert all(Path(p).read_bytes() == raw for p, raw in before.items())
    assert not data.exists()
    with pytest.raises(PolicyError):
        freeze(f, rows)


def panel_authorities(repo, protocol):
    plan = json.loads((repo / protocol["optimization_panel"]["plan"]["relpath"]).read_text())
    owner = json.loads((repo / plan["owner"]["relpath"]).read_text())
    growth = json.loads((repo / protocol["allocation_extension"]["owner"]["relpath"]).read_text())
    return owner, growth


@pytest.mark.parametrize("rows", [20, 50, 100, 200, 400])
def test_actual_freezer_pins_measured_profile_in_registration_and_recipe(tmp_path, rows):
    from speech_aware_evidence_acquisition.analysis.system_text_panel import validate_definition

    f = fixture(tmp_path, rows, profile=measurement_profile())
    archive, repo, data, protocol, _, _, pool = f
    before = copy.deepcopy(protocol)
    frozen = freeze(f, rows)
    reg, recipe = frozen["registration"], frozen["recipe"]
    assert reg["measurement_profile"] == recipe["measurement_profile"] == before["measurement_profile"]
    assert reg["registration_sha256"] == content_hash(
        {k: v for k, v in reg.items() if k != "registration_sha256"}
    )
    family, _ = panel_identities(4, rows)
    assert json.loads((archive.root / f"panels/{family}.json").read_text()) == frozen
    owner, growth = panel_authorities(repo, protocol)
    validate_definition(recipe, reg, owner, growth=growth, protocol=protocol, pool_ids=pool)
    assert protocol == before
    # Published definitions must not retain a mutable alias to the caller's protocol.
    protocol["measurement_profile"]["queue_depth"] = 8
    assert reg["measurement_profile"] == recipe["measurement_profile"] == before["measurement_profile"]
    assert not data.exists()


@pytest.mark.parametrize(
    "profile",
    [
        None,
        [],
        {},
        {**measurement_profile(), "schema": "unregistered-version"},
        {**measurement_profile(), "schedule": "node-panel"},
        {**measurement_profile(), "slot_count": True},
        {**measurement_profile(), "queue_depth": 0},
        {**measurement_profile(), "minimum_reliable_completion_rate": 1.1},
        {**measurement_profile(), "unknown": "not-registered"},
    ],
)
def test_actual_freezer_refuses_malformed_profile_without_writing(tmp_path, profile):
    f = fixture(tmp_path, profile=profile)
    archive, _, data, _, _, _, _ = f
    before = {str(p): p.read_bytes() for p in archive.root.rglob("*") if p.is_file()}
    with pytest.raises(PolicyError, match="measurement|finite|reliability"):
        freeze(f)
    assert not (archive.root / "panels").exists()
    assert {str(p): p.read_bytes() for p in archive.root.rglob("*") if p.is_file()} == before
    assert not data.exists()


@pytest.mark.parametrize("target", ["protocol", "registration", "recipe"])
@pytest.mark.parametrize("fault", ["missing", "conflicting", "malformed"])
def test_actual_freezer_output_refuses_changed_measurement_binding(tmp_path, target, fault):
    from speech_aware_evidence_acquisition.analysis.system_text_panel import validate_definition

    f = fixture(tmp_path, profile=measurement_profile())
    _, repo, _, protocol, _, _, pool = f
    frozen = freeze(f)
    reg, recipe = frozen["registration"], frozen["recipe"]
    owner, growth = panel_authorities(repo, protocol)
    changed = {"protocol": protocol, "registration": reg, "recipe": recipe}[target]
    if fault == "missing":
        changed.pop("measurement_profile")
    elif fault == "conflicting":
        changed["measurement_profile"]["queue_depth"] = 8
    else:
        changed["measurement_profile"] = None
    with pytest.raises(PolicyError, match="measurement profile differs"):
        validate_definition(recipe, reg, owner, growth=growth, protocol=protocol, pool_ids=pool)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-slot",
        "missing-aa",
        "wrong-bundle",
        "wrong-parent",
        "wrong-config-hash",
        "same-attempt",
        "changed-input",
        "changed-response",
        "no-compilation",
        "old-compilation",
        "invalid",
        "unmetered",
        "too-many-tokens",
        "reused-session",
        "blind-feedback",
        "context-edit",
        "missing-review",
        "changed-review",
        "wrong-review",
        "unreviewed",
        "prior-run",
        "prior-attempt",
        "pending-owner",
        "spent-mutation",
        "wrong-round",
    ],
)
def test_freeze_refuses_incomplete_changed_or_post_contact_sources(tmp_path, fault):
    f = fixture(tmp_path)
    archive, repo, data, protocol, members, review, pool = f

    def change(folder, key, edit):
        path = archive.root / f"{folder}/{key}.json"
        d = json.loads(path.read_text())
        edit(d)
        path.write_text(json.dumps(d))

    if fault == "missing-slot":
        (archive.root / "imports/L-4-1.json").unlink()
    elif fault == "missing-aa":
        members.pop("L-parent-aa")
    elif fault == "wrong-bundle":
        members["L-candidate-1"]["bundle_id"] = members["L-parent"]["bundle_id"]
    elif fault == "wrong-parent":
        members["L-parent"]["bundle_id"] = members["L-candidate-1"]["bundle_id"]
    elif fault == "wrong-config-hash":
        members["L-parent"]["config_hash"] = "not-a-hash"
    elif fault == "same-attempt":
        members["B-parent"]["attempt_id"] = members["L-parent"]["attempt_id"]
    elif fault == "changed-input":
        change("inputs", "L-4-1", lambda d: d.update(session_id="changed"))
    elif fault == "changed-response":
        change("responses", "L-4-1", lambda d: d.update(raw_response="changed"))
    elif fault == "no-compilation":
        (archive.root / "compilations/L-4-1.json").unlink()
    elif fault == "old-compilation":
        change("compilations", "L-4-1", lambda d: d.update(allocation=["L", 3, 1]))
    elif fault == "invalid":
        change("imports", "L-4-1", lambda d: d.update(status="invalid"))
    elif fault in {"unmetered", "too-many-tokens", "reused-session"}:
        change(
            "responses",
            "L-4-1",
            lambda d: d.update(
                **(
                    {"input_tokens": None}
                    if fault == "unmetered"
                    else {"input_tokens": 40000}
                    if fault == "too-many-tokens"
                    else {"session_id": "B-4-1"}
                )
            ),
        )
    elif fault == "blind-feedback":

        def contaminate(d):
            d["feedback"] = {"forbidden": True}
            d["input_sha256"] = content_hash(
                {k: v for k, v in d.items() if k != "input_sha256"}
            )

        change("inputs", "B-4-1", contaminate)
    elif fault == "context-edit":
        change(
            "proposals", "L-4-1", lambda d: d["proposal"]["changes"].update(supply={})
        )
    elif fault == "missing-review":
        (repo / review["relpath"]).unlink()
    elif fault == "changed-review":
        (repo / review["relpath"]).write_text("{}")
    elif fault in {"wrong-review", "unreviewed"}:
        d = json.loads((repo / review["relpath"]).read_text())
        d.update(family_id="another") if fault == "wrong-review" else d.update(
            status="pending"
        )
        review.update(write_pin(repo, review["relpath"], d))
    elif fault in {"prior-run", "prior-attempt"}:
        (
            data
            / ("runs" if fault == "prior-run" else "attempts")
            / members["B-parent"]["run_id"]
        ).mkdir(parents=True)
    elif fault == "pending-owner":
        (repo / protocol["allocation_extension"]["owner"]["relpath"]).write_text("{}")
    elif fault == "spent-mutation":
        change("imports", "B-2-1", lambda d: d.update(status="provisional"))
    else:
        protocol["updates"] = 5
    # Keep the root review matched for membership-negative cases; validate the actual source too.
    if fault in {
        "missing-aa",
        "wrong-bundle",
        "wrong-parent",
        "wrong-config-hash",
        "same-attempt",
    }:
        d = json.loads((repo / review["relpath"]).read_text())
        d["member_bindings_sha256"] = content_hash(members)
        review.update(write_pin(repo, review["relpath"], d))
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        freeze(f)
    assert not (archive.root / "panels").exists()


@pytest.mark.parametrize("rows", [50, 100, 200])
@pytest.mark.parametrize("measured", [False, True])
def test_cli_freezes_only_definition_and_never_invents_read_authority(
    tmp_path, capsys, rows, measured
):
    from test_system_text_search_cli import cli, write
    from speech_aware_evidence_acquisition.analysis.system_text_panel import (
        validate_registration,
    )

    f = fixture(tmp_path, rows, profile=measurement_profile() if measured else UNSET)
    archive, repo, data, protocol, members, review, pool = f
    args = [
        "--archive",
        str(archive.root),
        "freeze-panel",
        "--round",
        "4",
        "--rows",
        str(rows),
        "--protocol",
        write(tmp_path / "protocol.json", protocol),
        "--member-bindings",
        write(tmp_path / "members.json", members),
        "--root-review",
        write(tmp_path / "review-pin.json", review),
        "--repo-root",
        str(repo),
        "--data-root",
        str(data),
    ]
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    cli.main(args)
    result = json.loads(capsys.readouterr().out)
    family, _ = panel_identities(4, rows)
    frozen = json.loads((archive.root / f"panels/{family}.json").read_text())
    assert result["members"] == 8 and result["trajectory_cap"] == rows * 8
    assert (
        result["runtime_admission"] == "separate-required"
        and result["contacts_added"] == 0
    )
    assert all(Path(p).read_bytes() == raw for p, raw in before.items())
    assert len(protocol["stages"][0]["sample_ids"]) == 20
    plan = json.loads(
        (repo / protocol["optimization_panel"]["plan"]["relpath"]).read_text()
    )
    owner = json.loads((repo / plan["owner"]["relpath"]).read_text())
    growth = json.loads(
        (repo / protocol["allocation_extension"]["owner"]["relpath"]).read_text()
    )
    with pytest.raises(PolicyError, match="READ authority"):
        validate_registration(
            frozen["recipe"],
            frozen["registration"],
            owner,
            None,
            growth=growth,
            protocol=protocol,
            pool_ids=pool,
        )
    assert not data.exists()


@pytest.mark.parametrize(
    "fault",
    [
        "unmetered",
        "too-many-tokens",
        "reused-session",
        "runtime-edit",
        "wrong-compiled-bundle",
    ],
)
def test_rehashing_dispositions_cannot_hide_invalid_response_or_compilation(
    tmp_path, fault
):
    f = fixture(tmp_path)
    archive, repo, data, protocol, members, review, pool = f
    key = "L-4-1"
    paths = {
        k: archive.root / f"{k}/{key}.json"
        for k in ["inputs", "responses", "imports", "proposals", "compilations"]
    }
    d = {k: json.loads(v.read_text()) for k, v in paths.items()}
    if fault == "wrong-compiled-bundle":
        d["compilations"]["bundle_id"] = members["L-parent"]["bundle_id"]
        members["L-candidate-1"]["bundle_id"] = members["L-parent"]["bundle_id"]
        r = json.loads((repo / review["relpath"]).read_text())
        r["member_bindings_sha256"] = content_hash(members)
        review.update(write_pin(repo, review["relpath"], r))
    else:
        if fault == "unmetered":
            d["responses"]["input_tokens"] = None
        elif fault == "too-many-tokens":
            d["responses"]["input_tokens"] = 40000
        elif fault == "reused-session":
            d["responses"]["session_id"] = d["inputs"]["session_id"] = "B-4-1"
            d["inputs"]["input_sha256"] = content_hash(
                {k: v for k, v in d["inputs"].items() if k != "input_sha256"}
            )
            d["responses"]["input_sha256"] = d["inputs"]["input_sha256"]
        else:
            proposal = json.loads(d["responses"]["raw_response"])
            proposal["changes"] = {"supply": {"max_values_per_call": 1}}
            d["responses"]["raw_response"] = json.dumps(proposal)
            d["proposals"]["proposal"] = proposal
        d["proposals"]["receipt"] = d["responses"]
        d["imports"].update(
            receipt_sha256=content_hash(d["responses"]),
            input_sha256=d["inputs"]["input_sha256"],
        )
        d["compilations"].update(
            import_sha256=content_hash(d["imports"]),
            input_sha256=d["inputs"]["input_sha256"],
        )
    for k, p in paths.items():
        p.write_text(json.dumps(d[k]))
    with pytest.raises(PolicyError):
        freeze(f)
    assert not (archive.root / "panels").exists()
