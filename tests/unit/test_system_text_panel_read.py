"""Registered fixed-pool panels keep every arm, official count and exposure."""

from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.analysis import system_text_panel as panel
from speech_aware_evidence_acquisition.analysis import system_text_pilot as pilot
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)
from test_system_text_update_read import fixture as update_fixture


def fixture(tmp_path, rows=50):
    protocol, reference, original_recipe, all_roster = update_fixture(tmp_path)
    d = reference.as_json()
    pool = [g["sample_id"] for g in d["feedback"]["groups"]]
    d["feedback"]["groups"] = d["feedback"]["groups"][:rows]
    ids = pool[:rows]
    family, read_id = panel.identities(5, rows)
    bindings = original_recipe["system_search_evaluation"]["member_bindings"]
    for cid, b in bindings.items():
        b["run_id"] = panel.member_run_id(5, rows, cid)
        b["attempt_id"] = "attempt-" + b["run_id"].lower()
    members = {cid: b["run_id"] for cid, b in bindings.items()}
    for source in d["feedback"]["sources"]:
        source.update(
            {
                k: bindings[source["candidate_id"]][k]
                for k in ("run_id", "attempt_id", "config_hash")
            }
        )
    for g in d["feedback"]["groups"]:
        for m in g["members"]:
            m["native_counts"].update(slot_f1_exact_fp=0, slot_f1_exact_fn=0)
    for cid, s in d["summaries"].items():
        s.update(
            slu_f1=(6000 / 6200 if cid.endswith("candidate-1") else 5400 / 6200)
            if rows == 400
            else (1.0 if cid.endswith("candidate-1") else 0.9),
            model_calls=6 * rows,
        )
    protocol = {
        "updates": 5,
        "seed_bundle": {"bundle_id": bindings["B-parent"]["bundle_id"]},
    }
    owner = {
        "decision_id": 224,
        "status": "approved",
        "progressive_sizes": [20, 50, 100, 200, 400],
        "sample_ids_sha256": content_hash(pool),
    }
    growth = {
        "decision_id": 223,
        "status": "approved",
        "stage_ladder": [20, 50, 100, 200, 400],
    }
    registration = {
        "schema": panel.REGISTRATION_SCHEMA,
        "family_id": family,
        "proposal_round": 5,
        "expected_members": members,
        "member_bindings": bindings,
        "rows_per_member": rows,
        "trajectory_cap": rows * 8,
        "official_score_jobs_cap": 8,
        "new_proposal_opportunities": 0,
        "owner_decisions": [223, 224],
        "read_id": read_id,
        "root_stage_review": "completed",
        "independent_validation": False,
        "automatic_expansion": False,
        "scientific_role": "optimization-only",
        "proposal_protocol_sha256": content_hash(protocol),
        "pool_sample_ids_sha256": content_hash(pool),
        "prefix_sample_ids_sha256": content_hash(ids),
    }
    seal(registration)
    recipe = {
        "family_id": family,
        "expected_members": members,
        "sample_ids": ids,
        "required_rows_per_member": rows,
        "run_ids": {"read": read_id},
    }
    authority = {"read_run_id": read_id, "ledger_row_sha256": "a" * 64}
    d.update(
        schema=panel.SCHEMA,
        family_id=family,
        read_authority=authority,
        registration_sha256=registration["registration_sha256"],
        panel_scope=panel.scope_record(registration, owner, growth),
    )
    roster = {s: all_roster[s] for s in ids}
    supplement = {"resampling": original_recipe["resampling"]}
    return (
        d,
        recipe,
        registration,
        owner,
        authority,
        roster,
        supplement,
        growth,
        protocol,
        pool,
        reference,
    )


def seal(reg):
    reg["registration_sha256"] = content_hash(
        {k: v for k, v in reg.items() if k != "registration_sha256"}
    )


@pytest.mark.parametrize("rows", [20, 50, 100, 200, 400])
def test_whole_panel_uses_shared_statistics_and_projects_only_learning(tmp_path, rows):
    (
        d,
        recipe,
        reg,
        owner,
        authority,
        roster,
        supp,
        growth,
        protocol,
        pool,
        reference,
    ) = fixture(tmp_path, rows)
    panel.validate_registration(
        recipe, reg, owner, authority, growth=growth, protocol=protocol, pool_ids=pool
    )
    evidence = panel.CompletePanelEvidence(canonical(d))
    report = panel.analyze(
        evidence, recipe=recipe, registration=reg, roster=roster, supplement=supp
    )
    assert report["sample_count"] == rows
    assert report["status"] == "EXPLORATORY-FIXED-POOL-NO-ADOPTION"
    assert (
        not report["automatic_expansion"] and not report["optimizer_feedback_allowed"]
    )
    assert set(report["branches"]) == {"L", "B"}
    assert report["execution"]["L-parent"]["model_calls"] == rows * 6
    own = evidence.learning_projection(amendment=growth, reference=reference).as_json()
    assert own["reference"] == reference.as_json()["reference"]
    assert own["read_gate_family_sha256"] == content_hash(d)
    assert len(own["feedback"]["groups"]) == rows
    assert {
        s["candidate_id"] for s in own["feedback"]["sources"]
    } == panel.LEARNING_MEMBERS
    assert set(own["summaries"]) == panel.LEARNING_MEMBERS
    assert all(len(g["members"]) == 4 for g in own["feedback"]["groups"])
    assert all("B-" not in canonical(g) for g in own["feedback"]["groups"])
    assert all(
        "utility" in m and "relative_return" in m
        for g in own["feedback"]["groups"]
        for m in g["members"]
    )
    assert (
        d["feedback"]["groups"][0]["members"]
        == evidence.as_json()["feedback"]["groups"][0]["members"]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "owner",
        "growth",
        "size",
        "pool",
        "prefix",
        "test",
        "member",
        "run",
        "attempt",
        "aa",
        "seed",
        "protocol",
        "budget",
        "review",
        "adoption",
        "read",
        "hash",
        "family",
        "round",
    ],
)
def test_bad_registration_refuses_before_read(tmp_path, monkeypatch, fault):
    d, recipe, reg, owner, authority, _, _, growth, protocol, pool, _ = fixture(
        tmp_path
    )
    if fault == "owner":
        owner["status"] = "pending"
    elif fault == "growth":
        growth["status"] = "pending"
    elif fault == "size":
        reg["rows_per_member"] = 40
    elif fault == "pool":
        pool[-1] = "slurp:train:other:audio"
    elif fault == "prefix":
        recipe["sample_ids"] = list(reversed(recipe["sample_ids"]))
    elif fault == "test":
        pool[0] = "slurp:test:0:audio"
    elif fault == "member":
        reg["expected_members"].pop("B-candidate-2")
    elif fault == "run":
        reg["member_bindings"]["L-parent"]["run_id"] = "old-run"
    elif fault == "attempt":
        reg["member_bindings"]["L-parent-aa"]["attempt_id"] = reg["member_bindings"][
            "L-parent"
        ]["attempt_id"]
    elif fault == "aa":
        reg["member_bindings"]["L-parent-aa"]["bundle_id"] = "changed"
    elif fault == "seed":
        protocol["seed_bundle"]["bundle_id"] = "changed"
    elif fault == "protocol":
        reg["proposal_protocol_sha256"] = "0" * 64
    elif fault == "budget":
        reg["trajectory_cap"] += 1
    elif fault == "review":
        reg["root_stage_review"] = "pending"
    elif fault == "adoption":
        reg["independent_validation"] = True
    elif fault == "read":
        authority["read_run_id"] = "old-READ"
    elif fault == "family":
        recipe["family_id"] = pilot.FAMILY
    elif fault == "round":
        reg["proposal_round"] = True
    seal(reg)
    if fault == "hash":
        reg["registration_sha256"] = "0" * 64
    monkeypatch.setattr(
        panel, "_read_complete_evidence", lambda *a, **k: pytest.fail("results opened")
    )
    with pytest.raises(PolicyError):
        panel.read_evidence(
            [],
            recipe=recipe,
            registration=reg,
            owner=owner,
            authority=authority,
            growth=growth,
            protocol=protocol,
            pool_ids=pool,
        )


@pytest.mark.parametrize(
    "fault",
    [
        "family",
        "scope",
        "registration",
        "read",
        "member",
        "source",
        "group",
        "duplicate",
        "allowance",
    ],
)
def test_projection_and_report_reject_mixed_or_partial_evidence(tmp_path, fault):
    (
        d,
        recipe,
        reg,
        owner,
        authority,
        roster,
        supp,
        growth,
        protocol,
        pool,
        reference,
    ) = fixture(tmp_path)
    if fault == "family":
        d["family_id"] = pilot.FAMILY
    elif fault == "scope":
        d["panel_scope"]["rows"] = 20
    elif fault == "registration":
        d["registration_sha256"] = "0" * 64
    elif fault == "read":
        d["read_authority"]["read_run_id"] = "other"
    elif fault == "member":
        d["summaries"].pop("B-parent")
    elif fault == "source":
        d["feedback"]["sources"].pop()
    elif fault == "group":
        d["feedback"]["groups"][0]["members"].pop()
    elif fault == "duplicate":
        d["feedback"]["groups"][1]["sample_id"] = d["feedback"]["groups"][0][
            "sample_id"
        ]
    elif fault == "allowance":
        growth["status"] = "pending"
    evidence = panel.CompletePanelEvidence(canonical(d))
    with pytest.raises(PolicyError):
        evidence.learning_projection(amendment=growth, reference=reference)
    if fault != "allowance":
        with pytest.raises(PolicyError):
            panel.analyze(
                evidence,
                recipe=recipe,
                registration=reg,
                roster=roster,
                supplement=supp,
            )


def test_large_prefix_reader_checks_all_seals_before_rewards(tmp_path, monkeypatch):
    d, recipe, reg, owner, authority, _, _, growth, protocol, pool, _ = fixture(
        tmp_path
    )
    bindings = [
        {
            "candidate_id": c,
            "config": {"manifest": {"path": c}, "construction_roster": {}},
        }
        for c in reg["member_bindings"]
    ]
    metadata = [
        (
            {
                "run_id": b["run_id"],
                "config": {"config_hash": b["config_hash"]},
                "attempt": {"attempt_id": b["attempt_id"]},
                "split": {"count": 50, "ids": recipe["sample_ids"]},
            },
            {},
        )
        for b in reg["member_bindings"].values()
    ]
    monkeypatch.setattr(pilot, "preflight_family", lambda *a: metadata)
    monkeypatch.setattr(
        pilot,
        "_absolute_json",
        lambda *a: {"items": [{"sample_id": s} for s in recipe["sample_ids"]]},
    )
    monkeypatch.setattr(panel, "_job_metadata", lambda *a: {})
    seen = []

    def verify(path):
        seen.append(str(path))
        return SimpleNamespace(
            attempt_state="OPENED" if len(seen) == 8 else "FINALIZED"
        )

    monkeypatch.setattr(pilot, "verify_bundle", verify)
    monkeypatch.setattr(
        pilot,
        "build_group_relative_feedback",
        lambda *a: pytest.fail("rewards before all seals"),
    )
    with pytest.raises(PolicyError, match="seal"):
        panel.read_evidence(
            bindings,
            recipe=recipe,
            registration=reg,
            owner=owner,
            authority=authority,
            growth=growth,
            protocol=protocol,
            pool_ids=pool,
        )
    assert len(seen) == 8


def cli_fixture(tmp_path, monkeypatch):
    import json
    from test_system_text_pilot_read import cli_fixture as base
    from test_system_optimization import pin

    made = fixture(tmp_path)
    (
        d,
        recipe,
        reg,
        owner,
        authority,
        roster,
        supp,
        growth,
        protocol,
        pool,
        reference,
    ) = made
    cli, repo, data, _, _, calls, _ = base(
        tmp_path,
        monkeypatch,
        fixture_factory=lambda _: (d, recipe, reg, owner, authority, roster, supp),
    )
    protocol["allocation_extension"] = {
        "round": 5,
        "owner": pin(repo, "growth.json", growth),
    }
    protocol["optimization_panel"] = {
        "plan": {"relpath": "plan.json", "sha256": "e" * 64},
        "stages": ["update-5"],
        "editable": ["role_text"],
    }
    owner_pin = pin(repo, "owner.json", owner)
    reg["proposal_protocol_sha256"] = content_hash(protocol)
    seal(reg)
    recipe["system_panel_registration"] = pin(repo, "registration.json", reg)
    recipe.pop("pilot_registration")
    recipe_pin = pin(repo, "recipe.json", recipe)
    supp.update(
        schema="saea-system-panel-analysis-supplement-v1",
        recipe=recipe_pin,
        growth_owner_decision=protocol["allocation_extension"]["owner"],
        proposal_protocol=pin(repo, "protocol.json", protocol),
    )
    supp_pin = pin(repo, "supplement.json", supp)
    d.update(
        registration_sha256=reg["registration_sha256"],
        panel_scope=panel.scope_record(reg, owner, growth),
    )
    # The shared loader already tests the immutable pool/runtime identity in its own suite.
    # This fixture isolates the official source-custody and CLI routing contract.
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.system_optimization.load_optimization_panel",
        lambda *a, **k: ({"owner": owner_pin}, pool),
    )
    for path in (data / "runs").glob("*/*/run-manifest.json"):
        value = json.loads(path.read_text())
        value["split"]["count"] = 50
        path.write_text(json.dumps(value))
    monkeypatch.setattr(
        panel,
        "read_evidence",
        lambda *a, **k: panel.CompletePanelEvidence(canonical(d)),
    )
    (tmp_path / "reference.json").write_text(json.dumps({"family_id": "initial"}))
    monkeypatch.setattr(cli.CLI, "read_family", lambda *a, **k: reference)
    return cli, repo, data, recipe_pin, supp_pin, calls, d, supp


def test_panel_cli_routes_exact_family_and_exports_learning_only(tmp_path, monkeypatch):
    import json

    cli, repo, data, recipe_pin, supp_pin, calls, d, supp = cli_fixture(
        tmp_path, monkeypatch
    )
    output = data / "analysis/panel50"
    report = cli.run(
        recipe_pin=recipe_pin,
        supplement_pin=supp_pin,
        repo_root=repo,
        data_root=data,
        output=output,
        learning_amendment_pin=supp["growth_owner_decision"],
        reference_family_path=tmp_path / "reference.json",
    )
    assert report["sample_count"] == 50
    assert len(calls["reuse"]) == len(calls["artifacts"]) == 8
    assert "50" in (output / "README.md").read_text()
    feedback = json.loads((output / "learning-feedback.json").read_text())
    assert len(feedback["feedback"]["groups"]) == 50
    assert set(feedback["summaries"]) == panel.LEARNING_MEMBERS
    assert len(json.loads((output / "family.json").read_text())["bindings"]) == 8


@pytest.mark.parametrize(
    "fault",
    [
        "growth",
        "protocol",
        "pool-owner",
        "unsigned",
        "failed-score",
        "duplicate-score",
        "manifest-count",
        "seal",
        "owner-learning",
    ],
)
def test_panel_cli_refuses_before_any_saved_quality_read(tmp_path, monkeypatch, fault):
    import json

    cli, repo, data, rp, sp, calls, d, supp = cli_fixture(tmp_path, monkeypatch)
    learning = supp["growth_owner_decision"]
    if fault in {"growth", "protocol"}:
        (repo / (fault + ".json")).write_text("{}")
    elif fault == "pool-owner":
        (repo / "owner.json").write_text("{}")
    elif fault == "unsigned":

        def closed(*a, **k):
            raise PolicyError("unsigned")

        monkeypatch.setattr(cli.CLI, "require_read_registration", closed)
    elif fault in {"failed-score", "duplicate-score"}:
        p = next((data / "runs").glob("*/*/score-batch/batch-summary.json"))
        value = json.loads(p.read_text())
        if fault == "failed-score":
            value["failed"] = 1
        else:
            value["jobs"] *= 2
        p.write_text(json.dumps(value))
    elif fault == "manifest-count":
        p = next((data / "runs").glob("*/*/run-manifest.json"))
        value = json.loads(p.read_text())
        value["split"]["count"] = 20
        p.write_text(json.dumps(value))
    elif fault == "seal":
        monkeypatch.setattr(
            cli, "verify_bundle", lambda *a: SimpleNamespace(attempt_state="OPENED")
        )
    else:
        learning = {"relpath": "wrong.json", "sha256": "f" * 64}
    with pytest.raises((PolicyError, OSError)):
        cli.run(
            recipe_pin=rp,
            supplement_pin=sp,
            repo_root=repo,
            data_root=data,
            output=data / "analysis/refused",
            learning_amendment_pin=learning,
            reference_family_path=tmp_path / "reference.json",
        )
    assert not calls["reuse"] and not calls["artifacts"]
    assert not (data / "analysis/refused").exists()


def packet_fixture(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        exploratory_selection,
    )
    from test_system_search_allocations import fixture as allocations

    d, _, reg, _, _, _, _, growth, _, _, reference = fixture(tmp_path)
    feedback = panel.CompletePanelEvidence(canonical(d)).learning_projection(
        amendment=growth, reference=reference
    )
    _, _, _, ext = allocations(tmp_path / "allocations")
    ext["round"] = 6
    ext["earlier_allocations"] = {
        f"{b}-{r}-{s}": {k: "a" * 64 for k in ("input", "response", "import")}
        for r in range(1, 6)
        for b in ("L", "B")
        for s in (1, 2)
    }
    protocol = {
        "exploratory_learning": {"relpath": "binding.json", "sha256": "b" * 64},
        "allocation_extension": ext,
    }
    parent_id = reg["member_bindings"]["L-parent"]["bundle_id"]
    selection = exploratory_selection(
        feedback,
        registration=reg,
        binding={"next_round": 6, "parent_id": parent_id, "complementary_ids": []},
        protocol=protocol,
        parents=[{"cumulative_sources": []}],
    )
    packet = {
        "branch": "L",
        "round": 6,
        "parent_bundle_id": parent_id,
        "complementary_policies": [],
        "protocol_sha256": content_hash(protocol),
        "allocation_extension_sha256": content_hash(ext),
        "feedback": feedback.as_json(),
        "selection": selection,
        "model_version": ext["model_version"],
        "seed_bundle_id": ext["seed_bundle_id"],
        "input_token_cap": ext["input_token_cap"],
        "output_token_cap": ext["output_token_cap"],
    }
    return protocol, packet


def test_panel_learning_packet_retains_scope_sources_and_all_exposure(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        require_exploratory_packet,
    )

    protocol, p = packet_fixture(tmp_path)
    require_exploratory_packet(p, protocol=protocol)
    assert p["selection"]["stage"] == panel.identities(5, 50)[0]
    assert "B-parent" not in canonical(p) and "B-candidate" not in canonical(p)
    exposed = {
        sid for s in p["selection"]["cumulative_sources"] for sid in s["sample_ids"]
    }
    assert {g["sample_id"] for g in p["feedback"]["feedback"]["groups"]} <= exposed


@pytest.mark.parametrize(
    "fault",
    [
        "scope",
        "prefix",
        "source",
        "selection-family",
        "blind",
        "missing-aa",
        "same-round",
        "allowance",
        "exposure",
        "reference",
        "extra-scope",
    ],
)
def test_panel_transport_rejects_mixed_feedback_even_when_rehashed(tmp_path, fault):
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        require_exploratory_packet,
    )

    protocol, p = packet_fixture(tmp_path)
    d, s = p["feedback"], p["selection"]
    if fault == "scope":
        d["panel_scope"]["rows"] = 100
    elif fault == "prefix":
        d["feedback"]["groups"].reverse()
    elif fault == "source":
        d["feedback"]["sources"][0]["attempt_id"] = "another-attempt"
    elif fault == "selection-family":
        s["stage"] = pilot.FAMILY
    elif fault == "blind":
        d["summaries"]["B-parent"] = {}
    elif fault == "missing-aa":
        d["feedback"]["groups"][0]["members"].pop()
    elif fault == "same-round":
        p["round"] = 5
        s["next_round"] = 5
    elif fault == "allowance":
        d["learning_allowance_sha256"] = "0" * 64
    elif fault == "exposure":
        s["cumulative_sources"] = []
    elif fault == "reference":
        d["reference"]["sample_ids"] = ["slurp:test:0:audio"]
    elif fault == "extra-scope":
        d["panel_scope"]["blind_results"] = {"slu_f1": 1.0}
    s["learning_feedback_sha256"] = content_hash(d)
    s["selection_sha256"] = content_hash(
        {k: v for k, v in s.items() if k != "selection_sha256"}
    )
    with pytest.raises(PolicyError):
        require_exploratory_packet(p, protocol=protocol)


def test_scope_loader_resolves_real_pinned_pool_and_runtime(tmp_path):
    import json
    from test_system_optimization import fixture as optimization, pin
    from test_system_search_allocations import fixture as allocations

    protocol, ids = optimization(tmp_path)
    _, other, _, ext = allocations(tmp_path / "allocations")
    growth = {
        "decision_id": 223,
        "status": "approved",
        "stage_ladder": [20, 50, 100, 200, 400],
    }
    ext["owner"] = pin(tmp_path, ext["owner"]["relpath"], growth)
    protocol["allocation_extension"] = ext
    protocol["optimization_panel"]["stages"] = ["update-4"]
    supp = {
        "proposal_protocol": pin(tmp_path, "proposal-protocol.json", protocol),
        "growth_owner_decision": ext["owner"],
    }
    plan = json.loads((tmp_path / "plan.json").read_text())
    owner = json.loads((tmp_path / plan["owner"]["relpath"]).read_text())
    kwargs = panel.load_scope({"proposal_round": 4}, owner, supp, repo_root=tmp_path)
    assert kwargs["pool_ids"] == ids and kwargs["growth"] == growth
    (tmp_path / "view.json").write_text("{}")
    with pytest.raises(PolicyError):
        panel.load_scope({"proposal_round": 4}, owner, supp, repo_root=tmp_path)


def test_panel_direct_reader_requires_complete_successful_job_metadata(
    tmp_path, monkeypatch
):
    import json

    cli, repo, data, rp, sp, calls, d, supp = cli_fixture(tmp_path, monkeypatch)
    recipe, reg, owner, _ = cli.load_documents(rp, sp, repo)
    prelim, _ = cli.source_bindings(reg, cli.pin(repo / "roster.json"), data)
    pins = panel._job_metadata(prelim)
    assert len(pins) == 16
    p = next((data / "runs").glob("*/*/score-batch/batch-summary.json"))
    value = json.loads(p.read_text())
    value["failed"] = 1
    p.write_text(json.dumps(value))
    with pytest.raises(PolicyError):
        panel._job_metadata(prelim)


def learning_reader_fixture(tmp_path, monkeypatch):
    import json
    from test_system_optimization import pin

    cli, repo, data, rp, sp, calls, d, supp = cli_fixture(tmp_path, monkeypatch)
    search = cli.CLI
    recipe, reg, owner, _ = cli.load_documents(rp, sp, repo)
    prelim, _ = cli.source_bindings(reg, cli.pin(repo / "roster.json"), data)
    family = {
        "family_id": recipe["family_id"],
        "expected_members": recipe["expected_members"],
        "read_registration": rp,
        "bindings": prelim,
    }
    fp = data / "family.json"
    fp.write_text(json.dumps(family))
    growth = json.loads((repo / "growth.json").read_text())
    reference = search.read_family(tmp_path / "reference.json")
    expected = panel.CompletePanelEvidence(canonical(d)).learning_projection(
        amendment=growth, reference=reference
    )
    protocol = {
        "allocation_extension": {"round": 6},
        "optimization_panel": {
            "plan": {"relpath": "plan.json", "sha256": "e" * 64},
            "stages": ["update-6"],
            "editable": ["role_text"],
        },
    }
    parent = reg["member_bindings"]["L-parent"]["bundle_id"]
    binding = {
        "schema": "saea-exploratory-learning-binding-v1",
        "family": cli.pin(fp),
        "analysis_supplement": sp,
        "owner_learning": supp["growth_owner_decision"],
        "reference_family": cli.pin(tmp_path / "reference.json"),
        "next_round": 6,
        "parent_id": parent,
        "complementary_ids": [],
        "optimization_plan": protocol["optimization_panel"]["plan"],
        "expected_projection_sha256": content_hash(expected.as_json()),
    }
    protocol["exploratory_learning"] = pin(repo, "binding.json", binding)
    archive = SimpleNamespace(
        allocation_extension=lambda r: protocol["allocation_extension"],
        load_policy=lambda b: SimpleNamespace(
            as_json=lambda: {"cumulative_sources": []}
        ),
    )
    events = []
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.system_search_allocations.validate_extension",
        lambda *a, **k: events.append("allocation"),
    )

    def gate(*a, **k):
        events.append("gate")
        return d["read_authority"]

    monkeypatch.setattr(search, "require_read_registration", gate)

    def evidence(bindings, **kwargs):
        assert events[-1] == "gate" and len(bindings) == 8
        panel.validate_registration(
            kwargs["recipe"],
            kwargs["registration"],
            kwargs["owner"],
            kwargs["authority"],
            growth=kwargs["growth"],
            protocol=kwargs["protocol"],
            pool_ids=kwargs["pool_ids"],
        )
        panel._job_metadata(bindings)
        events.append("all-eight")
        return panel.CompletePanelEvidence(canonical(d))

    monkeypatch.setattr(panel, "read_evidence", evidence)

    def ref(*a, **k):
        assert "all-eight" in events
        events.append("reference")
        return reference

    monkeypatch.setattr(search, "read_family", ref)
    return search, protocol, archive, parent, fp, repo, events


def test_next_round_reader_reverifies_panel_before_own_learning_projection(
    tmp_path, monkeypatch
):
    search, protocol, archive, parent, fp, repo, events = learning_reader_fixture(
        tmp_path, monkeypatch
    )
    feedback, selection = search.read_pilot_learning(
        protocol,
        round_index=6,
        family_path=fp,
        repo_root=repo,
        archive=archive,
        parent_id=parent,
        complementary_ids=[],
    )
    assert events == ["allocation", "gate", "all-eight", "reference", "gate"]
    assert feedback.as_json()["panel_scope"]["rows"] == 50
    assert selection["stage"] == panel.identities(5, 50)[0]
    assert "B-parent" not in canonical(selection) and "B-parent" not in canonical(
        feedback.as_json()
    )


@pytest.mark.parametrize(
    "fault",
    [
        "growth",
        "protocol",
        "family",
        "recipe",
        "reference",
        "unsigned",
        "wrong-projection",
        "changed-during-read",
    ],
)
def test_next_panel_reader_never_trusts_cached_or_mutable_feedback(
    tmp_path, monkeypatch, fault
):
    import json

    search, protocol, archive, parent, fp, repo, events = learning_reader_fixture(
        tmp_path, monkeypatch
    )
    if fault in {"growth", "protocol", "recipe"}:
        (repo / (fault + ".json")).write_text("{}")
    elif fault == "family":
        fp.write_text("{}")
    elif fault == "reference":
        (tmp_path / "reference.json").write_text("{}")
    elif fault == "unsigned":

        def closed(*a, **k):
            raise PolicyError("unsigned")

        monkeypatch.setattr(search, "require_read_registration", closed)
    elif fault == "wrong-projection":
        from test_system_optimization import pin

        binding = json.loads((repo / "binding.json").read_text())
        binding["expected_projection_sha256"] = "0" * 64
        protocol["exploratory_learning"] = pin(repo, "binding.json", binding)
    else:
        original = search.read_family

        def changed(*a, **k):
            result = original(*a, **k)
            (repo / "growth.json").write_text("{}")
            return result

        monkeypatch.setattr(search, "read_family", changed)
    with pytest.raises(PolicyError):
        search.read_pilot_learning(
            protocol,
            round_index=6,
            family_path=fp,
            repo_root=repo,
            archive=archive,
            parent_id=parent,
            complementary_ids=[],
        )
    if fault not in {"wrong-projection", "changed-during-read"}:
        assert "reference" not in events


@pytest.mark.parametrize("changed", [False, True])
def test_panel_reader_binds_scope_and_rechecks_jobs_after_complete_read(
    tmp_path, monkeypatch, changed
):
    d, recipe, reg, owner, authority, _, _, growth, protocol, pool, _ = fixture(
        tmp_path
    )
    calls = []

    def jobs(bindings):
        calls.append("jobs")
        return {"summary": "changed" if changed and len(calls) > 1 else "pinned"}

    monkeypatch.setattr(panel, "_job_metadata", jobs)

    def shared(*a, **kwargs):
        assert calls == ["jobs"]
        calls.append("read")
        return panel.CompletePanelEvidence(canonical(d))

    monkeypatch.setattr(panel, "_read_complete_evidence", shared)
    if changed:
        with pytest.raises(PolicyError, match="changed"):
            panel.read_evidence(
                [],
                recipe=recipe,
                registration=reg,
                owner=owner,
                authority=authority,
                growth=growth,
                protocol=protocol,
                pool_ids=pool,
            )
    else:
        result = panel.read_evidence(
            [],
            recipe=recipe,
            registration=reg,
            owner=owner,
            authority=authority,
            growth=growth,
            protocol=protocol,
            pool_ids=pool,
        )
        assert result.as_json()["panel_scope"] == panel.scope_record(reg, owner, growth)
    assert calls == ["jobs", "read", "jobs"]


def test_panel_feedback_reuses_existing_isolated_capsule(tmp_path):
    from test_system_proposer_capsule import fixture as capsule_fixture, reseal
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import (
        ProposerCapsule,
    )

    packet, roots = capsule_fixture(tmp_path, "L")
    _, learned = packet_fixture(tmp_path / "panel")
    learned["parent_bundle_id"] = packet["parent_bundle_id"]
    learned["selection"]["active_ids"] = [packet["parent_bundle_id"]]
    for value in learned["selection"]["member_bindings"].values():
        value["bundle_id"] = packet["parent_bundle_id"]
    learned["selection"]["selection_sha256"] = content_hash(
        {k: v for k, v in learned["selection"].items() if k != "selection_sha256"}
    )
    packet.update(learned)
    reseal(packet)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    value = capsule.as_json()
    assert len(value["packet"]["feedback"]["feedback"]["groups"]) == 50
    assert "B-parent" not in canonical(value["packet"])
    assert value["packet"]["feedback"]["panel_scope"]["rows"] == 50
