"""The proposed owner225 recovery admits only its exact new complete family."""

import json
from types import SimpleNamespace

import pytest
from test_system_text_context_read import fixture as context_fixture
from speech_aware_evidence_acquisition.analysis import system_text_context as context
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.reward_links import RewardProjection, SLURP_NATIVE_FIELDS
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)

FAMILY = "fixed400-context20-recovery1-v1"
READ = "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-RECOVERY1-READ-V1"
RUNS = {
    "B-parent": "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-SEED-RECOVERY1-V1",
    "B-parent-aa": "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-SEED-AA-RECOVERY1-V1",
    "B-candidate-1": "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-PLANNER-V1",
    "B-candidate-2": "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-SOLVER-V1",
}


def rehash(reg):
    reg["registration_sha256"] = content_hash(
        {k: v for k, v in reg.items() if k != "registration_sha256"}
    )


def fixture(tmp_path):
    d, r, g, o, a, roster, s = context_fixture(tmp_path)
    g.update(
        family_id=FAMILY,
        expected_members=RUNS.copy(),
        read_id=READ,
        owner_decisions=[224, 225],
    )
    for cid, b in g["member_bindings"].items():
        b["run_id"] = RUNS[cid]
    rehash(g)
    r.update(family_id=FAMILY, expected_members=RUNS.copy(), run_ids={"read": READ})
    a["read_run_id"] = READ
    recovery = {
        "schema": "saea-fixed400-seed-binding-recovery-authority-v1",
        "decision_id": 225,
        "status": "approved",
        "family_id": FAMILY,
        "previous_family_id": context.FAMILY,
        "read_id": READ,
        "expected_members": RUNS.copy(),
        "rows_per_member": 20,
        "trajectory_cap": 80,
        "pool_sample_ids_sha256": g["pool_sample_ids_sha256"],
        "prefix_sample_ids_sha256": g["prefix_sample_ids_sha256"],
        "preserve_previous_family": True,
        "old_generation_or_score_replay_allowed": False,
        "automatic_failure_recovery": False,
    }
    d.update(
        family_id=FAMILY,
        read_authority=a,
        registration_sha256=g["registration_sha256"],
        recovery_authority=recovery,
    )
    for source in d["feedback"]["sources"]:
        source["run_id"] = RUNS[source["candidate_id"]]
    return d, r, g, o, a, roster, s, recovery


def test_recovery_reuses_complete_reader_and_preserves_exact_authority(
    tmp_path, monkeypatch
):
    d, r, g, o, a, roster, s, recovery = fixture(tmp_path)
    seen = []

    def read(bindings, **kwargs):
        seen.append(kwargs["family"])
        return context.CompleteContextEvidence(canonical(d))

    monkeypatch.setattr(context, "_read_complete_evidence", read)
    evidence = context.read_evidence(
        [], recipe=r, registration=g, owner=o, authority=a, recovery=recovery
    )
    assert seen == [FAMILY]
    assert evidence.as_json()["recovery_authority"] == recovery
    report = context.analyze(
        evidence, recipe=r, registration=g, roster=roster, supplement=s
    )
    assert report["sample_count"] == 20
    assert (
        not report["optimizer_feedback_allowed"] and not report["automatic_expansion"]
    )
    assert report["recovery_authority_sha256"] == content_hash(recovery)


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "pending",
        "decision",
        "scope",
        "old-parent",
        "missing-aa",
        "pool",
        "prefix",
        "budget",
        "replay",
        "automatic",
        "old-read",
        "family",
        "test",
        "unsigned",
    ],
)
def test_recovery_refuses_before_complete_sources(tmp_path, monkeypatch, fault):
    _, r, g, o, a, _, _, recovery = fixture(tmp_path)
    if fault == "missing":
        recovery = None
    elif fault == "pending":
        recovery["status"] = "pending-owner"
    elif fault == "decision":
        recovery["decision_id"] = 224
    elif fault == "scope":
        recovery["family_id"] = "another-family"
    elif fault == "old-parent":
        run = "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-SEED-V1"
        r["expected_members"]["B-parent"] = g["expected_members"][
            "B-parent"
        ] = recovery["expected_members"]["B-parent"] = run
        g["member_bindings"]["B-parent"]["run_id"] = run
    elif fault == "missing-aa":
        g["member_bindings"].pop("B-parent-aa")
    elif fault == "pool":
        recovery["pool_sample_ids_sha256"] = "b" * 64
    elif fault == "prefix":
        recovery["prefix_sample_ids_sha256"] = "b" * 64
    elif fault == "budget":
        recovery["trajectory_cap"] = 160
    elif fault == "replay":
        recovery["old_generation_or_score_replay_allowed"] = True
    elif fault == "automatic":
        recovery["automatic_failure_recovery"] = True
    elif fault == "old-read":
        a["read_run_id"] = context.READ_ID
    elif fault == "family":
        r["family_id"] = "fixed400-context20-recovery2-v1"
    elif fault == "test":
        r["sample_ids"][0] = "slurp:test:1"
    elif fault == "unsigned":
        a["ledger_row_sha256"] = ""
    rehash(g)
    monkeypatch.setattr(
        context,
        "_read_complete_evidence",
        lambda *a, **k: pytest.fail("sources opened"),
    )
    with pytest.raises(PolicyError):
        context.read_evidence(
            [], recipe=r, registration=g, owner=o, authority=a, recovery=recovery
        )


@pytest.mark.parametrize("fault", ["authority", "registration", "family"])
def test_recovery_analyzer_refuses_mixed_evidence(tmp_path, fault):
    d, r, g, _, _, roster, s, _ = fixture(tmp_path)
    if fault == "authority":
        d.pop("recovery_authority")
    elif fault == "registration":
        d["registration_sha256"] = "b" * 64
    else:
        d["family_id"] = context.FAMILY
    with pytest.raises(PolicyError):
        context.analyze(
            context.CompleteContextEvidence(canonical(d)),
            recipe=r,
            registration=g,
            roster=roster,
            supplement=s,
        )


@pytest.mark.parametrize(
    "state", ["approved", "pending", "pin-mismatch", "failed-score", "opened-aa"]
)
def test_recovery_cli_checks_authority_before_sources_and_reuses_scores(
    tmp_path, monkeypatch, state
):
    from test_system_text_pilot_read import cli_fixture

    cli, repo, data, _, _, calls, d = cli_fixture(
        tmp_path, monkeypatch, lambda p: fixture(p)[:7]
    )
    _, r, g, o, a, roster, supplement, recovery = fixture(tmp_path)

    def save(name, value):
        path = repo / name
        path.write_text(json.dumps(value))
        return {"relpath": name, "sha256": cli.pin(path)["sha256"]}

    pool = r["sample_ids"] + ["slurp:train:extra:" + str(i) for i in range(380)]
    o.update(
        fixed_roster=save("pool.json", {"sample_ids": pool}),
        sample_ids_sha256=content_hash(pool),
    )
    g["pool_sample_ids_sha256"] = recovery["pool_sample_ids_sha256"] = content_hash(
        pool
    )
    if state == "pending":
        recovery["status"] = "pending-owner"
    recovery_pin = save("recovery-owner.json", recovery)
    g["recovery_owner_decision"] = recovery_pin
    rehash(g)
    r.update(
        pilot_registration=save("registration.json", g),
        analysis_roster=save("roster.json", {"items": list(roster.values())}),
    )
    rp = save("recipe.json", r)
    supplement.update(
        schema="saea-context-analysis-supplement-v1",
        recipe=rp,
        owner_decision=save("owner.json", o),
        recovery_owner_decision=recovery_pin,
        stratum_metadata=save("strata.json", {"items": list(roster.values())}),
        projection=RewardProjection(
            "synthetic-official-counts-v1", "slurp-slu-official-train",
            ("port_micro.slu_f1", "port_micro.intent_accuracy"), SLURP_NATIVE_FIELDS,
        ).as_json(),
    )
    if state == "pin-mismatch":
        supplement["recovery_owner_decision"] = save("other-recovery.json", recovery)
    sp = save("supplement.json", supplement)
    d.update(registration_sha256=g["registration_sha256"], recovery_authority=recovery)

    def read(*args, **kwargs):
        assert kwargs["recovery"] == recovery
        return context.CompleteContextEvidence(canonical(d))

    monkeypatch.setattr(cli.context, "read_evidence", read)

    def reuse(path, *, job_id, verified_bundle):
        assert len(calls["verify"]) == 4
        calls["reuse"].append(job_id)
        path.mkdir(parents=True)
        p = path / "receipt.json"
        p.write_text("{}")
        return SimpleNamespace(path=p, sha256=cli.pin(p)["sha256"], cell_id=job_id)

    monkeypatch.setattr(cli, "write_complete_saved_score_receipt", reuse)
    kwargs = dict(
        recipe_pin=rp,
        supplement_pin=sp,
        repo_root=repo,
        data_root=data,
        output=data / "analysis/recovery",
    )
    if state in {"pending", "pin-mismatch"}:
        monkeypatch.setattr(
            cli,
            "source_bindings",
            lambda *a: pytest.fail("source opened before recovery authority"),
        )
        with pytest.raises(
            PolicyError,
            match="owner225" if state == "pending" else "recovery decision pin",
        ):
            cli.run(**kwargs)
        assert not calls["verify"] and not calls["reuse"]
    elif state in {"failed-score", "opened-aa"}:
        aa = g["member_bindings"]["B-parent-aa"]
        directory = data / "runs" / aa["run_id"] / aa["attempt_id"]
        if state == "failed-score":
            path = directory / "score-batch/batch-summary.json"
            summary = json.loads(path.read_text())
            summary.update(failed=1, succeeded=0)
            path.write_text(json.dumps(summary))
        else:
            verify = cli.verify_bundle
            monkeypatch.setattr(
                cli,
                "verify_bundle",
                lambda path: (
                    SimpleNamespace(attempt_state="OPENED")
                    if path.parent == directory
                    else verify(path)
                ),
            )
        with pytest.raises(
            PolicyError, match="successful complete official job|seal must verify"
        ):
            cli.run(**kwargs)
        assert not calls["reuse"] and not calls["artifacts"]
        assert not kwargs["output"].exists()
    else:
        report = cli.run(**kwargs)
        assert len(calls["verify"]) == len(calls["reuse"]) == 4
        assert report["source_pins"]["recovery_authority"] == recovery_pin
        assert report["recovery_authority_sha256"] == content_hash(recovery)
        assert not (data / "analysis/recovery/learning-feedback.json").exists()
