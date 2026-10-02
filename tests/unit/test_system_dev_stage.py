"""Bind final development evaluation to common-cohort winners, without new search."""
import copy
import json

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_protocol import stage_for
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_selection_stage import history_fixture, freeze, common_feedback


def finalists_fixture(tmp_path):
    args = history_fixture(tmp_path, (1, 1))
    archive, protocol = args[:2]
    selection = freeze(*args)
    feedback = common_feedback(selection, protocol)
    for branch in ("L", "B"):
        archive.retain_feedback(protocol=protocol, stage_name="selection", feedback=feedback,
            evaluation=selection["evaluation"], branch=branch,
            selected_ids=selection["survivors"][branch])
    finalists = archive.freeze_finalists(protocol=protocol, feedback=feedback)
    members = {cid: {"bundle_id": identity, "run_id": "DEV-" + cid,
                     "config_hash": content_hash({"config": cid})}
               for cid, identity in finalists["members"].items()}
    return archive, protocol, feedback, finalists, members, args[-1]


def freeze_dev(args):
    from speech_aware_evidence_acquisition.rails.system_dev_stage import freeze_dev_stage
    a, p, f, _, m, data = args
    return freeze_dev_stage(a, protocol=p, selection_feedback=f, member_bindings=m, data_root=data)


def test_dev_freeze_binds_exact_four_members_and_all_exposure(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_search_stage import validate_stage_registration
    args = finalists_fixture(tmp_path)
    d = freeze_dev(args)
    assert set(d["expected_members"]) == {"seed", "seed-aa", "L-frozen", "B-frozen"}
    assert d["rows"] == 1000 and d["trajectory_cap"] == 4000 and d["official_score_jobs_cap"] == 4
    assert d["finalists"] == args[3]
    assert d["runtime_admission"] == "separate-required"
    assert not args[-1].exists()
    validate_stage_registration(d, protocol=args[1])
    with pytest.raises(PolicyError, match="exists"):
        freeze_dev(args)


@pytest.mark.parametrize("fault", ["missing-aa", "extra", "other-winner", "same-run", "bad-run",
    "prior-run", "prior-attempt", "finalists-tamper", "selection-tamper", "wrong-family", "roster", "config"])
def test_dev_refuses_unfrozen_or_changed_inputs_before_registration(tmp_path, fault):
    args = list(finalists_fixture(tmp_path))
    archive, protocol, feedback, _, members, data = args
    if fault == "missing-aa":
        members.pop("seed-aa")
    elif fault == "extra":
        members["another-candidate"] = copy.deepcopy(members["L-frozen"])
    elif fault == "other-winner":
        members["L-frozen"]["bundle_id"] = members["seed"]["bundle_id"]
    elif fault == "same-run":
        members["seed-aa"]["run_id"] = members["seed"]["run_id"]
    elif fault == "bad-run":
        members["seed"]["run_id"] = "../escape"
    elif fault in {"prior-run", "prior-attempt"}:
        (data / ("runs" if fault == "prior-run" else "attempts") / members["seed"]["run_id"]).mkdir(parents=True)
    elif fault == "finalists-tamper":
        path = archive.root / "finalists.json"
        d = json.loads(path.read_text())
        d["members"]["L-frozen"] = d["members"]["seed"]
        d["freeze_sha256"] = content_hash({k: v for k, v in d.items() if k != "freeze_sha256"})
        path.write_text(json.dumps(d))
    elif fault == "selection-tamper":
        path = archive.root / "retentions/selection/L.json"
        d = json.loads(path.read_text())
        d["active_ids"] = [members["seed"]["bundle_id"]]
        d["selection_sha256"] = content_hash({k: v for k, v in d.items() if k != "selection_sha256"})
        path.write_text(json.dumps(d))
    elif fault == "wrong-family":
        from speech_aware_evidence_acquisition.rails.system_text_feedback import CompleteSystemFeedback
        from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
        d = feedback.as_json()
        d["family_id"] = "dev"
        args[2] = CompleteSystemFeedback(canonical(d))
    elif fault == "roster":
        stage_for(protocol, "dev")["sample_ids"].reverse()
    else:
        members["seed"]["config_hash"] = "not-a-hash"
    with pytest.raises((PolicyError, FileNotFoundError)):
        freeze_dev(args)
    assert not (archive.root / "stages/dev.json").exists()


@pytest.mark.parametrize("fault", ["missing-member", "winner", "budget", "roster", "exposure", "protocol"])
def test_dev_recipe_rehash_does_not_relax_frozen_endpoint(tmp_path, fault):
    from speech_aware_evidence_acquisition.rails.system_search_stage import validate_stage_registration
    args = finalists_fixture(tmp_path)
    d = freeze_dev(args)
    if fault == "missing-member":
        d["expected_members"].pop("seed-aa")
    elif fault == "winner":
        d["evaluation"]["member_bindings"]["L-frozen"]["bundle_id"] = "f" * 64
    elif fault == "budget":
        d["trajectory_cap"] += 1000
    elif fault == "roster":
        d["roster_sha256"] = "f" * 64
    elif fault == "protocol":
        d["finalists"]["protocol_sha256"] = "f" * 64
    else:
        d["finalists"]["cumulative_sources"] = []
    d["finalists"]["freeze_sha256"] = content_hash({k: v for k, v in d["finalists"].items() if k != "freeze_sha256"})
    d["registration_sha256"] = content_hash({k: v for k, v in d.items() if k != "registration_sha256"})
    with pytest.raises(PolicyError):
        validate_stage_registration(d, protocol=args[1])


def test_cli_dev_freeze_reverifies_only_common_selection_and_adds_no_contacts(tmp_path, monkeypatch, capsys):
    from test_system_text_search_cli import cli, write
    args = finalists_fixture(tmp_path)
    archive, protocol, feedback, _, members, data = args
    calls = []
    def read_family(path, *, repo_root):
        calls.append(cli.read(path)["family_id"])
        return feedback
    monkeypatch.setattr(cli, "read_family", read_family)
    cli.main(["--archive", str(archive.root), "freeze-dev", "--protocol", write(tmp_path / "protocol.json", protocol),
        "--family", write(tmp_path / "family.json", {"family_id": "selection"}),
        "--member-bindings", write(tmp_path / "members.json", members), "--data-root", str(data)])
    assert calls == ["selection"]
    assert '"trajectory_cap": 4000' in capsys.readouterr().out
    assert not data.exists()


@pytest.mark.parametrize("family", ["dev", "initial", "update-3", "milestone"])
def test_cli_dev_freeze_refuses_other_family_before_read(tmp_path, monkeypatch, family):
    from test_system_text_search_cli import cli, write
    monkeypatch.setattr(cli, "read_family", lambda *a, **k: pytest.fail("result read before stage check"))
    with pytest.raises(PolicyError, match="selection"):
        cli.main(["--archive", str(tmp_path / "archive"), "freeze-dev", "--protocol", "unused.json",
            "--family", write(tmp_path / "family.json", {"family_id": family}),
            "--member-bindings", "unused.json", "--data-root", str(tmp_path / "data")])


@pytest.mark.parametrize("member", ["seed", "seed-aa", "L-frozen", "B-frozen"])
def test_compile_dev_member_uses_frozen_bundle_and_shared_compiler(tmp_path, monkeypatch, member):
    from speech_aware_evidence_acquisition.rails import system_dev_stage as module
    from speech_aware_evidence_acquisition.rails import system_text_policy, system_text_cohort
    from test_system_text_search_cli import cli, write
    archive, protocol, feedback, finalists, _, data = finalists_fixture(tmp_path)
    seen = []
    def compile_policy(baseline, bundle, **kwargs):
        seen.append(("compile", bundle.bundle_id, kwargs))
        return {"compiled_policy": bundle.bundle_id}
    def bind(compiled, binding, **kwargs):
        seen.append(("bind", binding, kwargs))
        return {**compiled, "cohort": kwargs["stage"], "scorers": ["slurp-slu-official", "cost"]}
    monkeypatch.setattr(system_text_policy, "compile_system_text_policy", compile_policy)
    monkeypatch.setattr(system_text_cohort, "bind_system_text_cohort", bind)
    monkeypatch.setattr(cli, "read_family", lambda *a, **k: feedback)
    output = tmp_path / "compiled.json"
    cli.main(["--archive", str(archive.root), "compile-dev-member", "--member", member,
        "--protocol", write(tmp_path / "protocol.json", protocol),
        "--family", write(tmp_path / "selection.json", {"family_id": "selection"}),
        "--seed-config", write(tmp_path / "seed.json", {"seed": True}),
        "--cohort-binding", write(tmp_path / "binding.json", {"stage": "dev"}),
        "--repo-root", str(tmp_path), "--staging-root", str(tmp_path / "staging"),
        "--data-root", str(data), "--output", str(output)])
    assert seen[0][0:2] == ("compile", finalists["members"][member])
    assert seen[1][0] == "bind" and seen[1][2]["stage"] == "dev"
    assert json.loads(output.read_text())["compiled_policy"] == finalists["members"][member]
    assert not (archive.root / "stages/dev.json").exists()
    assert not data.exists()
    with pytest.raises(PolicyError, match="member"):
        module.compile_dev_member(archive, protocol=protocol, selection_feedback=feedback,
            member="new-candidate", baseline={}, cohort_binding={}, repo_root=tmp_path,
            staging_root=tmp_path, data_root=data)
