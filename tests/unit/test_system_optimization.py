"""Repeated optimization stays distinct from held-out evaluation and blind input."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)
from speech_aware_evidence_acquisition.rails.system_optimization import (
    assert_policy_roster,
    load_optimization_panel,
    exploratory_selection,
    require_exploratory_packet,
    require_context_only_changes,
)


def pin(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    return {"relpath": relative, "sha256": hashlib.sha256(raw).hexdigest()}


def fixture(tmp_path):
    ids = [f"slurp:train:{i:06}:audio" for i in range(400)]
    roster = pin(tmp_path, "roster.json", {"sample_ids": ids, "count": 400})
    view = pin(
        tmp_path, "view.json", {"items": [{"sample_id": s} for s in ids], "count": 400}
    )
    owner = pin(
        tmp_path,
        "docs/receipts/owner/2026-10-02-decision224-fixed400-context-postcall.json",
        {
            "decision_id": 224,
            "status": "approved",
            "fixed_roster": roster,
            "fixed_runtime_view": view,
            "sample_ids_sha256": content_hash(ids),
            "progressive_sizes": [20, 50, 100, 200, 400],
        },
    )
    plan = pin(
        tmp_path,
        "plan.json",
        {
            "schema": "saea-fixed-optimization-panel-plan-v1",
            "owner": owner,
            "source_roster": roster,
            "source_runtime_view": view,
            "source_rows": 400,
            "sample_ids_sha256": content_hash(ids),
            "scientific_role": "optimization-only",
            "no_runtime_authority": True,
            "stages": [
                {
                    "rows": n,
                    "start": 0,
                    "stop_exclusive": n,
                    "selection": "existing-ordered-roster-prefix",
                    "sample_ids_sha256": content_hash(ids[:n]),
                    "purpose": "reused-optimization-panel",
                    "independent_validation": False,
                }
                for n in [20, 50, 100, 200, 400]
            ],
        },
    )
    protocol = {
        "optimization_panel": {
            "plan": plan,
            "stages": ["update-3"],
            "editable": ["role_text"],
        },
        "stages": [
            {"stage": "update-3", "sample_ids": ids[:20]},
            {"stage": "dev", "sample_ids": ["slurp:devel:0:audio"]},
        ],
        "exploratory_learning": {"relpath": "binding.json", "sha256": "b" * 64},
    }
    return protocol, ids


def source(kind, sid):
    return {"kind": kind, "sample_ids": [sid], "sha256": "a" * 64}


@pytest.mark.parametrize("kind", ["feedback", "proposal", "selection"])
def test_fixed_pool_allows_reused_learning_and_retains_sources(tmp_path, kind):
    protocol, ids = fixture(tmp_path)
    sources = [source(kind, ids[0]), source("knowledge", "slurp:train:900000:audio")]
    before = copy.deepcopy(sources)
    result = assert_policy_roster(
        sources, ids[:20], protocol=protocol, stage="update-3", repo_root=tmp_path
    )
    assert result["purpose"] == "reused-optimization-panel"
    assert result["overlap_utterances"] == ["slurp:train:000000"]
    assert result["independent_validation"] is False and sources == before


@pytest.mark.parametrize("kind", ["knowledge", "construction"])
def test_runtime_knowledge_overlap_never_relaxes_even_recording_alias(tmp_path, kind):
    protocol, ids = fixture(tmp_path)
    with pytest.raises(PolicyError, match="knowledge|construction"):
        assert_policy_roster(
            [source(kind, ids[0].replace(":audio", ":other"))],
            ids[:20],
            protocol=protocol,
            stage="update-3",
            repo_root=tmp_path,
        )


@pytest.mark.parametrize(
    "fault", ["shuffle", "outside", "size", "owner", "changed-pin", "dev-stage"]
)
def test_panel_admission_refuses_unregistered_reinterpretation(tmp_path, fault):
    protocol, ids = fixture(tmp_path)
    chosen = ids[:20]
    if fault == "shuffle":
        chosen = chosen[::-1]
    elif fault == "outside":
        chosen[-1] = "slurp:train:999999:audio"
    elif fault == "size":
        chosen = chosen[:-1]
    elif fault == "changed-pin":
        (tmp_path / "roster.json").write_text("{}")
    elif fault == "owner":
        owner_path = (
            tmp_path
            / "docs/receipts/owner/2026-10-02-decision224-fixed400-context-postcall.json"
        )
        owner_path.write_text("{}")
    else:
        protocol["optimization_panel"]["stages"] = ["dev"]
    with pytest.raises(PolicyError):
        assert_policy_roster(
            [], chosen, protocol=protocol, stage="update-3", repo_root=tmp_path
        )


def test_formal_or_unamended_overlap_is_still_refused(tmp_path):
    protocol, ids = fixture(tmp_path)
    with pytest.raises(PolicyError, match="overlaps"):
        assert_policy_roster(
            [source("feedback", ids[0])],
            ids[:20],
            protocol={},
            stage="update-1",
            repo_root=tmp_path,
        )
    with pytest.raises(PolicyError, match="overlaps"):
        assert_policy_roster(
            [source("feedback", ids[0])],
            ids[:20],
            protocol=protocol,
            stage="selection",
            repo_root=tmp_path,
        )
    assert load_optimization_panel(protocol, "dev", repo_root=tmp_path) is None


def test_context_scope_preserves_knowledge_and_existing_legacy_edits(tmp_path):
    protocol, _ = fixture(tmp_path)
    require_context_only_changes(
        {"role_text": {"solver": "Deliver task JSON."}},
        protocol=protocol,
        stage="update-3",
        repo_root=tmp_path,
    )
    require_context_only_changes(
        {}, protocol=protocol, stage="update-3", repo_root=tmp_path
    )
    for field in ["slot_value_edits", "construction_instruction", "supply", "code"]:
        with pytest.raises(PolicyError, match="context"):
            require_context_only_changes(
                {field: {}}, protocol=protocol, stage="update-3", repo_root=tmp_path
            )
    require_context_only_changes(
        {"supply": {}}, protocol={}, stage="update-1", repo_root=tmp_path
    )


def learning_fixture(tmp_path):
    from test_system_text_pilot_read import fixture as pilot_fixture, update_fixture
    from speech_aware_evidence_acquisition.analysis.system_text_pilot import (
        CompleteSystemPilotEvidence,
    )

    d, recipe, reg, _, _, _, _ = pilot_fixture(tmp_path)
    _, reference, _, _ = update_fixture(tmp_path)
    amendment = {
        "decision_id": 222,
        "status": "approved",
        "family_id": "pilot20-owner220",
        "allow_learning_feedback": True,
        "recipient_branch": "L",
        "complete_family_required": True,
        "formal_adoption": False,
    }
    feedback = CompleteSystemPilotEvidence(canonical(d)).learning_projection(
        amendment=amendment, reference=reference
    )
    parent_id = reg["member_bindings"]["L-parent"]["bundle_id"]
    protocol = {"exploratory_learning": {"relpath": "binding.json", "sha256": "b" * 64}}
    binding = {"next_round": 3, "parent_id": parent_id, "complementary_ids": []}
    parents = [{"cumulative_sources": []}]
    selection = exploratory_selection(
        feedback, registration=reg, binding=binding, protocol=protocol, parents=parents
    )
    packet = {
        "branch": "L",
        "round": 3,
        "parent_bundle_id": parent_id,
        "complementary_policies": [],
        "protocol_sha256": content_hash(protocol),
        "feedback": feedback.as_json(),
        "selection": selection,
    }
    return protocol, packet


def test_exploratory_selection_keeps_own_cases_and_frozen_reference(tmp_path):
    protocol, packet = learning_fixture(tmp_path)
    require_exploratory_packet(packet, protocol=protocol)
    selection = packet["selection"]
    assert (
        selection["stage"] == "pilot20-owner220"
        and selection["formal_adoption"] is False
    )
    assert set(selection["member_bindings"]) == {
        "L-parent",
        "L-parent-aa",
        "L-candidate-1",
        "L-candidate-2",
    }
    exposed = {sid for s in selection["cumulative_sources"] for sid in s["sample_ids"]}
    assert set(packet["feedback"]["reference"]["sample_ids"]) <= exposed
    assert {g["sample_id"] for g in packet["feedback"]["feedback"]["groups"]} <= exposed


@pytest.mark.parametrize(
    "fault",
    ["blind", "hash", "family", "binding", "round", "parent", "missing-aa", "claim"],
)
def test_exploratory_packet_cannot_borrow_formal_or_other_branch_authority(
    tmp_path, fault
):
    protocol, packet = learning_fixture(tmp_path)
    if fault == "blind":
        packet["feedback"]["summaries"]["B-parent"] = {}
    elif fault == "hash":
        packet["selection"]["selection_sha256"] = "0" * 64
    elif fault == "family":
        packet["feedback"]["family_id"] = "update-2"
    elif fault == "binding":
        protocol["exploratory_learning"]["sha256"] = "0" * 64
    elif fault == "round":
        packet["round"] = 2
    elif fault == "parent":
        packet["parent_bundle_id"] = "0" * 64
    elif fault == "missing-aa":
        packet["feedback"]["feedback"]["groups"][0]["members"].pop()
    else:
        packet["feedback"]["formal_adoption"] = True
    with pytest.raises(PolicyError):
        require_exploratory_packet(packet, protocol=protocol)


def reader_fixture(tmp_path, monkeypatch):
    from test_system_text_search_cli import cli
    from test_system_text_pilot_read import fixture as pilot_fixture, update_fixture
    from speech_aware_evidence_acquisition.analysis import system_text_pilot as pilot
    from speech_aware_evidence_acquisition.rails.system_search_archive import (
        SystemSearchArchive,
    )
    from speech_aware_evidence_acquisition.rails.system_text_policy import (
        SystemTextPolicyBundle,
    )
    from test_system_text_policy import seed_document

    protocol, pool = fixture(tmp_path)
    d, recipe, registration, owner, authority, _, _ = pilot_fixture(tmp_path)
    _, reference, _, _ = update_fixture(tmp_path)
    archive = SystemSearchArchive(tmp_path / "archive")
    parent = SystemTextPolicyBundle.from_json(seed_document())
    archive.store_policy(parent)
    for member in registration["member_bindings"].values():
        member["bundle_id"] = parent.bundle_id
    registration["registration_sha256"] = content_hash(
        {k: v for k, v in registration.items() if k != "registration_sha256"}
    )
    recipe["pilot_registration"] = pin(tmp_path, "registration.json", registration)
    recipe_pin = pin(tmp_path, "recipe.json", recipe)
    owner_pin = pin(tmp_path, "owner220.json", owner)
    supplement = pin(
        tmp_path,
        "supplement.json",
        {
            "schema": "saea-pilot-analysis-supplement-v1",
            "recipe": recipe_pin,
            "owner_decision": owner_pin,
        },
    )
    family = {
        "family_id": pilot.FAMILY,
        "expected_members": recipe["expected_members"],
        "read_registration": recipe_pin,
        "bindings": list(registration["member_bindings"]),
    }

    def absolute(relative, value):
        saved = pin(tmp_path, relative, value)
        return {"path": str(tmp_path / relative), "sha256": saved["sha256"]}

    family_pin = absolute("family.json", family)
    reference_pin = absolute("reference.json", {"family_id": "initial"})
    amendment = {
        "decision_id": 222,
        "status": "approved",
        "family_id": pilot.FAMILY,
        "allow_learning_feedback": True,
        "recipient_branch": "L",
        "complete_family_required": True,
        "formal_adoption": False,
    }
    amendment_pin = pin(tmp_path, "owner222.json", amendment)
    projected = pilot.CompleteSystemPilotEvidence(canonical(d)).learning_projection(
        amendment=amendment, reference=reference
    )
    binding = {
        "schema": "saea-exploratory-learning-binding-v1",
        "family": family_pin,
        "analysis_supplement": supplement,
        "owner_learning": amendment_pin,
        "reference_family": reference_pin,
        "next_round": 3,
        "parent_id": parent.bundle_id,
        "complementary_ids": [],
        "optimization_plan": protocol["optimization_panel"]["plan"],
        "expected_projection_sha256": content_hash(projected.as_json()),
    }
    protocol["exploratory_learning"] = pin(tmp_path, "binding.json", binding)
    protocol["seed_bundle"] = {"bundle_id": parent.bundle_id}
    protocol.update(
        proposer_exact_version="synthetic",
        proposal_input_token_cap=32768,
        proposal_output_token_cap=4096,
    )
    events = []

    def gate(*a, **k):
        events.append("gate")
        return authority

    def read_evidence(bindings, **k):
        assert events[-1] == "gate" and len(bindings) == 8
        events.append("all-eight-verified")
        return pilot.CompleteSystemPilotEvidence(canonical(d))

    def read_reference(path, **k):
        assert "all-eight-verified" in events
        events.append("reference")
        return reference

    monkeypatch.setattr(cli, "require_read_registration", gate)
    monkeypatch.setattr(pilot, "read_pilot_evidence", read_evidence)
    monkeypatch.setattr(cli, "read_family", read_reference)
    # Fixture source identities are unrelated to the production ordered pool.
    # The reader validates feedback-source ancestry; the next panel is pinned separately.
    return cli, protocol, archive, parent, family_pin, events


def test_exploratory_reader_reverifies_family_then_projects_before_packaging(
    tmp_path, monkeypatch
):
    cli, protocol, archive, parent, family, events = reader_fixture(
        tmp_path, monkeypatch
    )
    feedback, selection = cli.read_pilot_learning(
        protocol,
        round_index=3,
        family_path=family["path"],
        repo_root=tmp_path,
        archive=archive,
        parent_id=parent.bundle_id,
        complementary_ids=[],
    )
    assert events == ["gate", "all-eight-verified", "reference", "gate"]
    assert "reused optimization" in feedback.as_json()["interpretation"]
    assert selection["stage"] == "pilot20-owner220"
    assert set(feedback.as_json()["summaries"]) == {
        "L-parent",
        "L-parent-aa",
        "L-candidate-1",
        "L-candidate-2",
    }


@pytest.mark.parametrize(
    "fault",
    ["family-pin", "binding-pin", "reference-pin", "parent", "round", "unsigned"],
)
def test_exploratory_reader_never_trusts_cached_feedback(tmp_path, monkeypatch, fault):
    cli, protocol, archive, parent, family, events = reader_fixture(
        tmp_path, monkeypatch
    )
    parent_id, round_index = parent.bundle_id, 3
    if fault == "family-pin":
        Path(family["path"]).write_text("{}")
    elif fault == "binding-pin":
        (tmp_path / "binding.json").write_text("{}")
    elif fault == "reference-pin":
        (tmp_path / "reference.json").write_text("{}")
    elif fault == "parent":
        parent_id = "0" * 64
    elif fault == "round":
        round_index = 2
    else:

        def closed(*a, **k):
            raise PolicyError("unsigned read")

        monkeypatch.setattr(cli, "require_read_registration", closed)
    with pytest.raises(PolicyError):
        cli.read_pilot_learning(
            protocol,
            round_index=round_index,
            family_path=family["path"],
            repo_root=tmp_path,
            archive=archive,
            parent_id=parent_id,
            complementary_ids=[],
        )
    assert "reference" not in events


def test_learning_cli_uses_pilot_without_formal_stage_relaxation(tmp_path, monkeypatch):
    cli, protocol, archive, parent, family, events = reader_fixture(
        tmp_path, monkeypatch
    )
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol))
    args = [
        "--archive",
        str(archive.root),
        "proposal-input",
        "--branch",
        "L",
        "--round",
        "3",
        "--slot",
        "1",
        "--seed-id",
        parent.bundle_id,
        "--parent-id",
        parent.bundle_id,
        "--model-version",
        "synthetic",
        "--session-id",
        "fresh-synthetic",
        "--protocol",
        str(path),
        "--family",
        family["path"],
        "--repo-root",
        str(tmp_path),
    ]
    for cid in sorted(LEARNING_IDS):
        args += ["--learning-member", cid]
    cli.main(args)
    packet = cli.read(archive.root / "inputs/L-3-1.json")
    require_exploratory_packet(packet, protocol=protocol)
    with pytest.raises(PolicyError, match="consumed|exists"):
        cli.main(args)
    blind_args = list(args)
    blind_args[blind_args.index("--branch") + 1] = "B"
    events.clear()
    with pytest.raises(PolicyError, match="blind"):
        cli.main(blind_args)
    assert events == []


LEARNING_IDS = {"L-parent", "L-parent-aa", "L-candidate-1", "L-candidate-2"}


def capsule_learning_packet(tmp_path):
    from test_system_proposer_capsule import fixture as capsule_fixture, reseal

    protocol, learned = learning_fixture(tmp_path)
    packet, roots = capsule_fixture(tmp_path, "L")
    learned["parent_bundle_id"] = packet["parent_bundle_id"]
    learned["selection"]["active_ids"] = [packet["parent_bundle_id"]]
    for b in learned["selection"]["member_bindings"].values():
        b["bundle_id"] = packet["parent_bundle_id"]
    learned["selection"]["selection_sha256"] = content_hash(
        {k: v for k, v in learned["selection"].items() if k != "selection_sha256"}
    )
    packet.update(learned)
    reseal(packet)
    return protocol, packet, roots


def test_capsule_accepts_only_typed_complete_pilot_selection(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import (
        input_references,
    )
    from test_system_proposer_capsule import reseal

    _, packet, _ = capsule_learning_packet(tmp_path)
    input_references(packet)
    del packet["selection"]
    reseal(packet)
    with pytest.raises(PolicyError, match="exploratory"):
        input_references(packet)


@pytest.mark.parametrize("branch", ["L", "B"])
def test_context_scope_is_visible_in_the_actual_proposer_contract(tmp_path, branch):
    from test_system_proposer_capsule import fixture as capsule_fixture, reseal
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import (
        ProposerCapsule,
    )

    packet, roots = capsule_fixture(tmp_path, branch)
    packet["optimization_scope"] = {
        "purpose": "reused-optimization-panel",
        "editable": ["role_text"],
        "plan_sha256": "a" * 64,
    }
    reseal(packet)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    contract = capsule.initial_input()["response_contract"]
    assert set(contract["editable_changes"]) == {"role_text"}
    assert "slot_edit_fields" not in contract
    assert "frozen" in contract["rules"]
    packet["optimization_scope"]["editable"].append("supply")
    reseal(packet)
    with pytest.raises(PolicyError, match="optimization"):
        ProposerCapsule.from_packet(packet, roots=roots)


def test_transport_rechecks_exploratory_protocol_and_context_scope(tmp_path):
    from test_system_proposer_round import runner

    protocol, packet, _ = capsule_learning_packet(tmp_path)
    runner.require_feedback_transition(packet, protocol=protocol, round_index=3)
    protocol["exploratory_learning"]["sha256"] = "0" * 64
    with pytest.raises(PolicyError, match="binding|protocol"):
        runner.require_feedback_transition(packet, protocol=protocol, round_index=3)


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"supply": {"mode": "reread", "value_limit": 2}}, "invalid"),
        (
            {
                "role_text": {
                    "solver": "Return the exact task JSON without tool-call markup."
                }
            },
            "provisional",
        ),
    ],
)
def test_response_scope_violation_spends_the_allocation_without_activation(
    tmp_path, changes, expected
):
    from test_system_proposer_capsule import fixture as capsule_fixture, reseal
    from speech_aware_evidence_acquisition.rails.system_search_archive import (
        SystemSearchArchive,
    )

    packet, _ = capsule_fixture(tmp_path)
    packet["optimization_scope"] = {
        "purpose": "reused-optimization-panel",
        "editable": ["role_text"],
        "plan_sha256": "a" * 64,
    }
    reseal(packet)
    archive = SystemSearchArchive(tmp_path / "archive")
    archive.store_input(packet)
    response = {
        "schema": "saea-text-policy-update-proposal-v1",
        "branch": "B",
        "round": 1,
        "slot": 1,
        "parent_ids": [packet["parent_bundle_id"]],
        "changes": changes,
        "rationale": "Test the stated context.",
        "hypotheses": [],
        "evidence": [],
    }
    receipt = {
        "raw_response": json.dumps(response),
        "input_tokens": 100,
        "output_tokens": 100,
        **{k: packet[k] for k in ("session_id", "model_version", "input_sha256")},
    }
    result = archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)
    assert result["status"] == expected and result["activation"] == "none"
    if expected == "invalid":
        assert "scope" in str(result["errors"])
    with pytest.raises(PolicyError, match="consumed|exists"):
        archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)


def test_extended_fixed_panel_needs_the_exact_extra_round_authority(tmp_path):
    from test_system_search_allocations import fixture as allocation_fixture
    protocol, _ = fixture(tmp_path)
    _, repo, _, extension = allocation_fixture(tmp_path / "extension")
    # Copy only the explicitly pinned owner authority into this synthetic repo.
    owner_path = tmp_path / extension["owner"]["relpath"]
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    owner_path.write_bytes((repo / extension["owner"]["relpath"]).read_bytes())
    protocol["allocation_extension"] = extension
    protocol["optimization_panel"]["stages"] = ["update-4"]
    assert load_optimization_panel(protocol, "update-4", repo_root=tmp_path) is not None
    protocol["optimization_panel"]["stages"] = ["update-5"]
    with pytest.raises(PolicyError):
        load_optimization_panel(protocol, "update-5", repo_root=tmp_path)
    protocol["optimization_panel"]["stages"] = ["update-4"]
    del protocol["allocation_extension"]
    with pytest.raises(PolicyError):
        load_optimization_panel(protocol, "update-4", repo_root=tmp_path)


def test_extended_learning_cannot_borrow_a_digest_without_protocol_authority(tmp_path):
    from test_system_search_allocations import fixture as allocation_fixture
    protocol, packet = learning_fixture(tmp_path)
    _, _, _, extension = allocation_fixture(tmp_path / "extension")
    protocol["allocation_extension"] = extension
    packet.update(round=4, allocation_extension_sha256=content_hash(extension),
                  protocol_sha256=content_hash(protocol), model_version=extension["model_version"],
                  seed_bundle_id=extension["seed_bundle_id"], input_token_cap=extension["input_token_cap"],
                  output_token_cap=extension["output_token_cap"])
    packet["selection"].update(next_round=4, protocol_sha256=content_hash(protocol))
    packet["selection"]["selection_sha256"] = content_hash({k: v for k,v in packet["selection"].items() if k != "selection_sha256"})
    require_exploratory_packet(packet, protocol=protocol)
    protocol.pop("allocation_extension")
    with pytest.raises(PolicyError):
        require_exploratory_packet(packet, protocol=protocol)
