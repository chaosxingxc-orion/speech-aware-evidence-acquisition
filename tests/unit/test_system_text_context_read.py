"""The owner224 four-member comparison stays inside its fixed optimization pool."""

import copy
import json
from types import SimpleNamespace
import pytest
from test_system_text_pilot_read import fixture as pilot_fixture
from speech_aware_evidence_acquisition.analysis import system_text_context as context
from speech_aware_evidence_acquisition.analysis import system_text_pilot as pilot
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.reward_links import RewardProjection, SLURP_NATIVE_FIELDS
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)


def fixture(tmp_path):
    d, recipe, reg, owner, authority, roster, supplement = pilot_fixture(tmp_path)
    members = {k: v for k, v in reg["expected_members"].items() if k.startswith("B-")}
    bindings = {k: v for k, v in reg["member_bindings"].items() if k in members}
    reg.update(
        schema=context.REGISTRATION_SCHEMA,
        family_id=context.FAMILY,
        expected_members=members,
        member_bindings=bindings,
        trajectory_cap=80,
        official_score_jobs_cap=4,
        owner_decisions=[224],
        read_id=context.READ_ID,
        pool_sample_ids_sha256="a" * 64,
        prefix_sample_ids_sha256=content_hash(recipe["sample_ids"]),
        independent_validation=False,
        optimizer_feedback_allowed=False,
    )
    reg["registration_sha256"] = content_hash(
        {k: v for k, v in reg.items() if k != "registration_sha256"}
    )
    recipe.update(
        family_id=context.FAMILY,
        expected_members=members,
        run_ids={"read": context.READ_ID},
    )
    owner = {
        "decision_id": 224,
        "status": "approved",
        "sample_ids_sha256": "a" * 64,
        "progressive_sizes": [20, 50, 100, 200, 400],
    }
    authority["read_run_id"] = context.READ_ID
    d.update(schema=context.SCHEMA, family_id=context.FAMILY, read_authority=authority)
    d["summaries"] = {k: v for k, v in d["summaries"].items() if k in members}
    d["feedback"]["sources"] = [
        s for s in d["feedback"]["sources"] if s["candidate_id"] in members
    ]
    for g in d["feedback"]["groups"]:
        g["members"] = [m for m in g["members"] if m["candidate_id"] in members]
    return d, recipe, reg, owner, authority, roster, supplement


def test_four_members_reuse_statistics_without_learning_or_adoption(tmp_path):
    d, r, g, o, a, roster, s = fixture(tmp_path)
    context.validate_registration(r, g, o, a)
    report = context.analyze(
        context.CompleteContextEvidence(canonical(d)),
        recipe=r,
        registration=g,
        roster=roster,
        supplement=s,
    )
    assert set(report["branches"]) == {"B"}
    assert report["sample_count"] == 20
    assert len(report["per_stratum"]) == 2
    assert len(report["branches"]["B"]["comparisons"]) == 5
    assert not report["optimizer_feedback_allowed"]
    assert not report["claims_feedback_learning_advantage"]
    assert not report["independent_validation"]
    assert not hasattr(
        context.CompleteContextEvidence(canonical(d)), "learning_projection"
    )
    with pytest.raises(PolicyError):
        pilot.validate_pilot_registration(r, g, o, a)


@pytest.mark.parametrize(
    "fault",
    [
        "owner",
        "pool",
        "prefix",
        "read",
        "members",
        "aa",
        "identity",
        "budget",
        "rows",
        "test",
        "hash",
        "future",
        "learning",
    ],
)
def test_refuse_scope_before_any_results(tmp_path, monkeypatch, fault):
    _, r, g, o, a, _, _ = fixture(tmp_path)
    if fault == "owner":
        o["status"] = "pending"
    elif fault == "pool":
        g["pool_sample_ids_sha256"] = "b" * 64
    elif fault == "prefix":
        g["prefix_sample_ids_sha256"] = "b" * 64
    elif fault == "read":
        a["read_run_id"] = "OTHER"
    elif fault == "members":
        g["member_bindings"].pop("B-parent-aa")
    elif fault == "aa":
        g["member_bindings"]["B-parent-aa"]["bundle_id"] = "different"
    elif fault == "identity":
        g["member_bindings"]["B-parent"]["run_id"] = "different"
    elif fault == "budget":
        g["trajectory_cap"] = 160
    elif fault == "rows":
        r["required_rows_per_member"] = 400
    elif fault == "test":
        r["sample_ids"][0] = "slurp:test:1"
    elif fault == "future":
        g["independent_validation"] = True
    elif fault == "learning":
        g["optimizer_feedback_allowed"] = True
    if fault != "hash":
        g["registration_sha256"] = content_hash(
            {k: v for k, v in g.items() if k != "registration_sha256"}
        )
    else:
        g["registration_sha256"] = "b" * 64
    monkeypatch.setattr(
        pilot, "preflight_family", lambda *a: pytest.fail("results reached")
    )
    with pytest.raises(PolicyError):
        context.read_evidence([], recipe=r, registration=g, owner=o, authority=a)


def test_context_seals_all_four_before_rewards(tmp_path, monkeypatch):
    d, r, g, o, a, _, _ = fixture(tmp_path)
    bindings = []
    metadata = []
    for cid, b in g["member_bindings"].items():
        path = tmp_path / (cid + ".json")
        path.write_text(
            json.dumps({"items": [{"sample_id": s} for s in r["sample_ids"]]})
        )
        import hashlib

        bindings.append(
            {
                "candidate_id": cid,
                "config": {
                    "manifest": {"path": "/fake/" + cid},
                    "construction_roster": {
                        "path": str(path),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    },
                },
            }
        )
        metadata.append(
            (
                {
                    "run_id": b["run_id"],
                    "config": {"config_hash": b["config_hash"]},
                    "attempt": {"attempt_id": b["attempt_id"]},
                    "split": {"count": 20, "ids": r["sample_ids"]},
                },
                {},
            )
        )
    monkeypatch.setattr(pilot, "preflight_family", lambda *a: metadata)
    seen = []

    def verify(path):
        seen.append(path)
        return SimpleNamespace(attempt_state="FINALIZED")

    monkeypatch.setattr(pilot, "verify_bundle", verify)

    def read(_):
        assert len(seen) == 4
        return {**copy.deepcopy(d["feedback"]), "carrier_lock_key": "slurp"}

    monkeypatch.setattr(pilot, "build_group_relative_feedback", read)
    monkeypatch.setattr(
        pilot,
        "_official_family_rows",
        lambda *a: (
            {
                cid: {
                    x["sample_id"]: next(
                        m["execution"] for m in x["members"] if m["candidate_id"] == cid
                    )
                    for x in d["feedback"]["groups"]
                }
                for cid in g["member_bindings"]
            },
            d["summaries"],
        ),
    )
    e = context.read_evidence(bindings, recipe=r, registration=g, owner=o, authority=a)
    assert e.as_json()["schema"] == context.SCHEMA
    monkeypatch.setattr(
        pilot, "verify_bundle", lambda *a: SimpleNamespace(attempt_state="OPENED")
    )
    with pytest.raises(PolicyError, match="seal"):
        context.read_evidence(bindings, recipe=r, registration=g, owner=o, authority=a)


def test_context_cli_reuses_saved_scores_and_refuses_wrong_pool(tmp_path, monkeypatch):
    from test_system_text_pilot_read import cli_fixture

    cli, repo, data, _, _, calls, _ = cli_fixture(tmp_path, monkeypatch)
    d, r, g, o, a, roster, s = fixture(tmp_path)

    def save(name, value):
        path = repo / name
        path.write_text(json.dumps(value))
        return {"relpath": name, "sha256": cli.pin(path)["sha256"]}

    pool = r["sample_ids"] + ["slurp:train:extra:" + str(i) for i in range(380)]
    o.update(
        fixed_roster=save("pool.json", {"sample_ids": pool}),
        sample_ids_sha256=content_hash(pool),
    )
    g["pool_sample_ids_sha256"] = content_hash(pool)
    g["registration_sha256"] = content_hash(
        {k: v for k, v in g.items() if k != "registration_sha256"}
    )
    r.update(
        pilot_registration=save("registration.json", g),
        analysis_roster=save("roster.json", {"items": list(roster.values())}),
    )
    rp = save("recipe.json", r)
    s.update(
        schema="saea-context-analysis-supplement-v1",
        recipe=rp,
        owner_decision=save("owner.json", o),
        stratum_metadata=save("strata.json", {"items": list(roster.values())}),
        projection=RewardProjection(
            "synthetic-official-counts-v1", "slurp-slu-official-train",
            ("port_micro.slu_f1", "port_micro.intent_accuracy"), SLURP_NATIVE_FIELDS,
        ).as_json(),
    )
    sp = save("supplement.json", s)
    monkeypatch.setattr(cli.CLI, "require_read_registration", lambda *args, **kwargs: a)
    monkeypatch.setattr(
        cli.context,
        "read_evidence",
        lambda *args, **kwargs: context.CompleteContextEvidence(canonical(d)),
    )

    def reuse(path, *, job_id, verified_bundle):
        assert len(calls["verify"]) == 4
        calls["reuse"].append(job_id)
        path.mkdir(parents=True)
        p = path / "receipt.json"
        p.write_text("{}")
        return SimpleNamespace(path=p, sha256=cli.pin(p)["sha256"], cell_id=job_id)

    monkeypatch.setattr(cli, "write_complete_saved_score_receipt", reuse)
    output = data / "analysis/context"
    report = cli.run(
        recipe_pin=rp, supplement_pin=sp, repo_root=repo, data_root=data, output=output
    )
    assert report["status"] == "EXPLORATORY-FIXED-POOL-NO-ADOPTION"
    assert len(calls["reuse"]) == len(calls["artifacts"]) == 4
    assert not (output / "learning-feedback.json").exists()
    # A self-consistent but reordered prefix still refuses before opening sources.
    r["sample_ids"] = list(reversed(r["sample_ids"]))
    g["prefix_sample_ids_sha256"] = content_hash(r["sample_ids"])
    g["registration_sha256"] = content_hash(
        {k: v for k, v in g.items() if k != "registration_sha256"}
    )
    r["pilot_registration"] = save("registration.json", g)
    rp = save("recipe.json", r)
    s["recipe"] = rp
    sp = save("supplement.json", s)
    monkeypatch.setattr(
        cli, "source_bindings", lambda *args: pytest.fail("source opened")
    )
    with pytest.raises(PolicyError, match="first twenty"):
        cli.run(
            recipe_pin=rp,
            supplement_pin=sp,
            repo_root=repo,
            data_root=data,
            output=data / "analysis/wrong",
        )
