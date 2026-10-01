"""Prospective common-cohort nomination, with synthetic complete history only."""

import json

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_protocol import (
    stage_for,
    require_stage_feedback,
)
from speech_aware_evidence_acquisition.rails.system_search_stage import (
    validate_stage_registration,
)
from speech_aware_evidence_acquisition.rails.system_selection_stage import (
    freeze_selection_stage,
)
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    SystemTextPolicyBundle,
    canonical,
)
from test_system_search_selection import selection_fixture


def history_fixture(tmp_path, counts=(1, 2)):
    archive, protocol, _, _ = selection_fixture(tmp_path)
    histories, retained = {}, {}
    seed_id = protocol["seed_bundle"]["bundle_id"]
    seed = archive.load_policy(seed_id)
    for index in (1, 2, 3):
        stage = f"update-{index}"
        _, p, feedback, evaluation = selection_fixture(tmp_path / stage, stage)
        assert p == protocol
        value = feedback.as_json()
        for cid, binding in evaluation["member_bindings"].items():
            binding["run_id"] = stage + "-" + cid
            if "candidate" in cid:
                d = seed.as_json()
                d["parent_ids"] = [seed_id]
                d["role_text"]["solver"] += f"\nSynthetic {stage} {cid}."
                bundle = SystemTextPolicyBundle.from_json(d, parents=[seed])
                archive.store_policy(bundle)
                binding["bundle_id"] = bundle.bundle_id
            source = next(
                s for s in value["feedback"]["sources"] if s["candidate_id"] == cid
            )
            source["run_id"] = binding["run_id"]
        histories[stage] = CompleteSystemFeedback(canonical(value))
        retained[stage] = {}
        for branch in ("L", "B"):
            retained[stage][branch] = archive.retain_feedback(
                protocol=protocol,
                stage_name=stage,
                feedback=histories[stage],
                evaluation=evaluation,
                branch=branch,
                selected_ids=[
                    evaluation["member_bindings"][f"{branch}-candidate-{s}"][
                        "bundle_id"
                    ]
                    for s in (1, 2)
                ],
            )
    members = {
        cid: {
            "bundle_id": seed_id,
            "run_id": "COMMON-" + cid,
            "config_hash": content_hash(cid),
        }
        for cid in stage_for(protocol, "selection")["member_slots"]
    }
    for branch, count in zip(("L", "B"), counts):
        # Include an early survivor; do not silently restrict eligibility to round three.
        members[branch + "-1"]["bundle_id"] = retained["update-1"][branch][
            "active_ids"
        ][0]
        members[branch + "-2"].update(
            bundle_id=retained["update-3"][branch]["active_ids"][1]
            if count == 2
            else None,
            config_hash=content_hash(branch + "-2") if count == 2 else None,
        )
    return archive, protocol, histories, retained, members, tmp_path / "data"


def freeze(archive, protocol, histories, retained, members, data):
    return freeze_selection_stage(
        archive,
        protocol=protocol,
        update_feedback=histories,
        member_bindings=members,
        data_root=data,
    )


@pytest.mark.parametrize("counts", [(1, 1), (1, 2), (2, 1), (2, 2)])
def test_freeze_selects_one_or_two_historical_survivors_on_a_common_cohort(
    tmp_path, counts
):
    args = history_fixture(tmp_path, counts)
    result = freeze(*args)
    assert result["trajectory_cap"] == 400 * (2 + sum(counts))
    assert result["official_score_jobs_cap"] == 2 + sum(counts)
    assert result["survivors"]["L"][0] == args[3]["update-1"]["L"]["active_ids"][0]
    assert set(result["expected_members"]) == {"seed", "seed-aa", "L-1", "B-1"} | {
        b + "-2" for b, n in zip(("L", "B"), counts) if n == 2
    }
    assert not args[-1].exists()
    assert result["runtime_admission"] == "separate-required"
    validate_stage_registration(result, protocol=args[1])
    with pytest.raises(PolicyError, match="exists"):
        freeze(*args)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-history",
        "partial-history",
        "unbound-history",
        "changed-feedback",
        "changed-retention",
        "missing-retention",
        "unretained",
        "foreign-branch",
        "duplicate",
        "missing-aa",
        "wrong-seed",
        "prior-run",
        "excluded-run",
        "overlap",
    ],
)
def test_nomination_refuses_unqualified_history_or_changed_membership(tmp_path, fault):
    archive, p, h, r, m, data = history_fixture(tmp_path)
    if fault == "missing-history":
        h.pop("update-2")
    elif fault in {"partial-history", "unbound-history", "changed-feedback"}:
        d = h["update-2"].as_json()
        if fault == "partial-history":
            d["summaries"].pop("B-candidate-2")
        elif fault == "unbound-history":
            d.pop("read_authority")
        else:
            d["summaries"]["L-candidate-1"]["slu_f1"] += 0.01
        h["update-2"] = CompleteSystemFeedback(canonical(d))
    elif fault == "changed-retention":
        path = archive.root / "retentions/update-1/L.json"
        d = json.loads(path.read_text())
        d["active_ids"].reverse()
        path.write_text(json.dumps(d))
    elif fault == "missing-retention":
        (archive.root / "retentions/update-1/B.json").unlink()
    elif fault == "unretained":
        m["L-1"]["bundle_id"] = p["seed_bundle"]["bundle_id"]
    elif fault == "foreign-branch":
        m["L-1"]["bundle_id"] = m["B-1"]["bundle_id"]
    elif fault == "duplicate":
        m["B-2"]["bundle_id"] = m["B-1"]["bundle_id"]
    elif fault == "missing-aa":
        m.pop("seed-aa")
    elif fault == "wrong-seed":
        m["seed"]["bundle_id"] = m["L-1"]["bundle_id"]
    elif fault in {"prior-run", "excluded-run"}:
        (data / "runs" / m["seed" if fault == "prior-run" else "L-2"]["run_id"]).mkdir(
            parents=True
        )
    else:
        # A hash-consistent earlier selection exposed the future evaluation roster.
        path = archive.root / "retentions/update-1/L.json"
        d = json.loads(path.read_text())
        d["cumulative_sources"].append(
            {
                "kind": "selection",
                "sha256": "f" * 64,
                "sample_ids": [stage_for(p, "selection")["sample_ids"][0]],
            }
        )
        d["selection_sha256"] = content_hash(
            {k: v for k, v in d.items() if k != "selection_sha256"}
        )
        path.write_text(json.dumps(d))
    with pytest.raises((PolicyError, FileNotFoundError)):
        freeze_selection_stage(
            archive, protocol=p, update_feedback=h, member_bindings=m, data_root=data
        )
    assert not (archive.root / "stages/selection.json").exists()


def common_feedback(registration, protocol):
    bindings = registration["evaluation"]["member_bindings"]
    d = {
        "family_id": "selection",
        "reference": {
            "f1": 0.7,
            "sample_ids": stage_for(protocol, "initial")["sample_ids"],
        },
        "summaries": {
            cid: {
                "slu_f1": 0.7 if cid.startswith("seed") else 0.8,
                "intent": 0.9,
                "model_calls": 2000,
                "tool_calls": 100,
                "reliable_completion_rate": 1,
            }
            for cid in bindings
        },
        "feedback": {
            "sources": [
                {
                    "candidate_id": cid,
                    "run_id": b["run_id"],
                    "config_hash": b["config_hash"],
                }
                for cid, b in bindings.items()
            ],
            "candidate_ids": list(bindings),
            "groups": [
                {"sample_id": sid, "members": []}
                for sid in stage_for(protocol, "selection")["sample_ids"]
            ],
        },
        "read_authority": {
            "read_run_id": "SYNTHETIC-READ",
            "stage_registration": registration,
        },
    }
    return CompleteSystemFeedback(canonical(d))


def test_reduced_common_family_preserves_all_nomination_exposure_through_dev_freeze(
    tmp_path,
):
    args = history_fixture(tmp_path, (1, 1))
    archive, p = args[:2]
    registration = freeze(*args)
    feedback = common_feedback(registration, p)
    require_stage_feedback(p, "selection", feedback)
    for branch in ("L", "B"):
        record = archive.retain_feedback(
            protocol=p,
            stage_name="selection",
            feedback=feedback,
            evaluation=registration["evaluation"],
            branch=branch,
            selected_ids=registration["survivors"][branch],
        )
        used = {sid for s in record["cumulative_sources"] for sid in s["sample_ids"]}
        for index in (1, 2, 3):
            assert set(stage_for(p, f"update-{index}")["sample_ids"]) <= used
    final = archive.freeze_finalists(protocol=p, feedback=feedback)
    assert final["members"]["L-frozen"] == registration["survivors"]["L"][0]
    used = {sid for s in final["cumulative_sources"] for sid in s["sample_ids"]}
    assert set(stage_for(p, "selection")["sample_ids"]) <= used
    assert not used.intersection(stage_for(p, "dev")["sample_ids"])
    partial = feedback.as_json()
    partial["summaries"].pop("B-1")
    with pytest.raises(PolicyError):
        require_stage_feedback(
            p, "selection", CompleteSystemFeedback(canonical(partial))
        )


@pytest.mark.parametrize(
    "fault",
    [
        "seed-aa",
        "required-branch",
        "exclusion",
        "budget",
        "binding",
        "roster",
        "history",
        "lost-exposure",
    ],
)
def test_rehashed_selection_registration_cannot_relax_the_complete_family(
    tmp_path, fault
):
    args = history_fixture(tmp_path)
    d = freeze(*args)
    if fault == "seed-aa":
        d["expected_members"].pop("seed-aa")
    elif fault == "required-branch":
        d["expected_members"].pop("L-1")
    elif fault == "exclusion":
        d["exclusions"]["L-2"]["status"] = "failed-after-contact"
    elif fault == "budget":
        d["trajectory_cap"] += 400
    elif fault == "binding":
        d["evaluation"]["member_bindings"]["B-1"]["bundle_id"] = "f" * 64
    elif fault == "roster":
        d["roster_sha256"] = "f" * 64
    elif fault == "history":
        d["retentions"]["L"].pop("update-2")
    else:
        d["cumulative_sources"]["L"] = []
    d["registration_sha256"] = content_hash(
        {k: v for k, v in d.items() if k != "registration_sha256"}
    )
    with pytest.raises(PolicyError):
        validate_stage_registration(d, protocol=args[1])


def test_cli_reverifies_three_families_and_writes_only_prospective_registration(
    tmp_path, monkeypatch, capsys
):
    from test_system_text_search_cli import cli, write

    archive, p, h, r, m, data = history_fixture(tmp_path)
    calls = []

    def read_family(path, *, repo_root):
        name = cli.read(path)["family_id"]
        calls.append(name)
        return h[name]

    monkeypatch.setattr(cli, "read_family", read_family)
    args = [
        "--archive",
        str(archive.root),
        "freeze-selection",
        "--protocol",
        write(tmp_path / "protocol.json", p),
        "--member-bindings",
        write(tmp_path / "bindings.json", m),
        "--data-root",
        str(data),
    ]
    for name in ("update-1", "update-2", "update-3"):
        args.extend(
            ["--update-family", write(tmp_path / (name + ".json"), {"family_id": name})]
        )
    cli.main(args)
    assert calls == ["update-1", "update-2", "update-3"]
    assert '"members": 5' in capsys.readouterr().out
    assert not data.exists()
    assert (archive.root / "stages/selection.json").exists()


@pytest.mark.parametrize("last_family", ["update-1", "milestone", "dev", "selection"])
def test_cli_refuses_wrong_family_specs_before_any_result_read(
    tmp_path, monkeypatch, last_family
):
    from test_system_text_search_cli import cli, write

    archive, p, h, r, m, data = history_fixture(tmp_path)
    monkeypatch.setattr(
        cli, "read_family", lambda *a, **k: pytest.fail("opened a result source")
    )
    args = [
        "--archive",
        str(archive.root),
        "freeze-selection",
        "--protocol",
        write(tmp_path / "protocol.json", p),
        "--member-bindings",
        write(tmp_path / "bindings.json", m),
        "--data-root",
        str(data),
    ]
    for index, name in enumerate(("update-1", "update-2", last_family)):
        args.extend(
            [
                "--update-family",
                write(tmp_path / f"family-{index}.json", {"family_id": name}),
            ]
        )
    with pytest.raises(PolicyError, match="distinct"):
        cli.main(args)
    assert not (archive.root / "stages/selection.json").exists()


@pytest.mark.parametrize("changed_members", [False, True])
def test_common_recipe_checks_members_before_opening_results(
    tmp_path, monkeypatch, changed_members
):
    import hashlib
    from test_system_text_search_cli import cli, read_fixture, write

    args = history_fixture(tmp_path)
    registration = freeze(*args)
    spec, ledger, path = read_fixture(tmp_path)
    spec.update(
        family_id="selection", expected_members=dict(registration["expected_members"])
    )
    recipe = {
        "read_run_id": "FIXTURE-READ",
        "family_id": "selection",
        "expected_members": dict(registration["expected_members"]),
        "system_search_stage": registration,
        "system_search_evaluation": registration["evaluation"],
    }
    if changed_members:
        spec["expected_members"].pop("B-1")
        recipe["expected_members"].pop("B-1")
        spec["reference_family"] = str(tmp_path / "DO-NOT-OPEN.json")
    path.write_text(json.dumps(recipe))
    spec["read_registration"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    called = []

    def complete(*a, **k):
        called.append(k)
        return common_feedback(registration, args[1])

    monkeypatch.setattr(cli.CompleteSystemFeedback, "from_family", complete)
    source = write(tmp_path / "common-family.json", spec)
    if changed_members:
        with pytest.raises(PolicyError, match="frozen stage"):
            cli.read_family(source, repo_root=tmp_path)
        assert not called
    else:
        feedback = cli.read_family(source, repo_root=tmp_path)
        require_stage_feedback(args[1], "selection", feedback)
        assert called[0]["expected_members"] == registration["expected_members"]


def test_common_freeze_refuses_historical_dev_exposure_before_registration(tmp_path):
    archive, p, h, r, m, data = history_fixture(tmp_path)
    path = archive.root / "retentions/update-1/L.json"
    d = json.loads(path.read_text())
    d["cumulative_sources"].append(
        {
            "kind": "selection",
            "sha256": "e" * 64,
            "sample_ids": [stage_for(p, "dev")["sample_ids"][0]],
        }
    )
    d["selection_sha256"] = content_hash(
        {k: v for k, v in d.items() if k != "selection_sha256"}
    )
    path.write_text(json.dumps(d))
    # The shared TRAIN-only boundary refuses DEV exposure even earlier than
    # the final roster-overlap check; never relax it to defer the rejection.
    with pytest.raises(PolicyError, match="TRAIN ancestry"):
        freeze_selection_stage(
            archive, protocol=p, update_feedback=h, member_bindings=m, data_root=data
        )
    assert not (archive.root / "stages/selection.json").exists()
