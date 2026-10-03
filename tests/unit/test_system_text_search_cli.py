"""Offline lifecycle integration, including fresh blind packets and refusal paths."""
import importlib.util
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError, SystemTextPolicyBundle
from test_system_text_policy import ROOT, BASE, seed_document

spec = importlib.util.spec_from_file_location("system_text_search_cli", ROOT / "scripts/system_text_search.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def write(path, data):
    path.write_text(json.dumps(data))
    return str(path)


def test_import_corrected_seed_keeps_and_verifies_ancestry(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
    archive = tmp_path / "archive"
    prefix = ["--archive", str(archive), "import-seed", "--bundle"]
    parent = SystemTextPolicyBundle.from_json(seed_document())
    child = parent.as_json()
    child["parent_ids"] = [parent.bundle_id]
    child["role_text"]["planner"] += " Return one exact legal control token."
    child_path = write(tmp_path / "child.json", child)
    with pytest.raises((ValueError, FileNotFoundError)):
        cli.main(prefix + [child_path])
    cli.main(prefix + [write(tmp_path / "parent.json", parent.as_json())])
    cli.main(prefix + [child_path])
    loaded = SystemSearchArchive(archive).load_policy(cli.content_hash(child))
    assert loaded.as_json() == child
    child["cumulative_sources"] = []
    with pytest.raises(PolicyError, match="ancestry"):
        cli.main(prefix + [write(tmp_path / "shrunk.json", child)])


def test_blind_session_import_and_shared_compilation_without_model_contacts(tmp_path, monkeypatch, capsys):
    archive = tmp_path / "archive"
    prefix = ["--archive", str(archive)]
    seed = SystemTextPolicyBundle.from_json(seed_document())
    cli.main(prefix + ["import-seed", "--bundle", write(tmp_path / "seed.json", seed.as_json())])
    protocol = write(tmp_path / "protocol.json", {"proposer_exact_version": "GPT6-fixture-pinned",
                        "seed_bundle": {"bundle_id": seed.bundle_id},
                        "proposal_input_token_cap": 32768, "proposal_output_token_cap": 4096,
                        "stages": [{"stage": "update-1", "sample_ids": ["slurp:train:held"]}]})
    args = prefix + ["proposal-input", "--branch", "B", "--round", "1", "--slot", "1",
        "--seed-id", seed.bundle_id, "--parent-id", seed.bundle_id, "--model-version", "GPT6-fixture-pinned",
        "--session-id", "fresh-fixture", "--protocol", protocol]
    cli.main(args)
    packet = cli.read(archive / "inputs/B-1-1.json")
    assert "feedback" not in packet
    response = {"schema": "saea-text-policy-update-proposal-v1", "branch": "B", "round": 1,
        "slot": 1, "parent_ids": [seed.bundle_id], "changes": {"role_text": {"reviewer": "Identify a concrete unsupported slot boundary."}},
        "rationale": "Check the whole-system effect of explicit uncertainty.", "hypotheses": [], "evidence": []}
    receipt = {"raw_response": json.dumps(response), "session_id": "fresh-fixture", "model_version": "GPT6-fixture-pinned",
               "input_sha256": packet["input_sha256"], "input_tokens": 500, "output_tokens": 200}
    cli.main(prefix + ["import-response", "--branch", "B", "--round", "1", "--slot", "1",
                      "--receipt", write(tmp_path / "response.json", receipt)])
    # Real knowledge verification has its own integration tests. This test uses
    # synthetic custody while exercising the real shared consumption compiler.
    monkeypatch.setattr("speech_aware_evidence_acquisition.rails.knowledge_stores.load_knowledge_store_binding",
        lambda *a, **k: SimpleNamespace(stores={"slot-contracts": SimpleNamespace(snapshot=SimpleNamespace(
            values=[SimpleNamespace(source_sample_ids=["slurp:train:900:audio-1"])]))}))
    output = tmp_path / "compiled.json"
    compile_args = prefix + ["compile-candidate", "--branch", "B", "--round", "1", "--slot", "1",
        "--seed-config", str(ROOT / BASE), "--repo-root", str(ROOT), "--staging-root", str(tmp_path / "worker"),
        "--evaluation-roster", write(tmp_path / "roster.json", {"items": [{"sample_id": "slurp:train:held"}]}),
        "--data-root", str(tmp_path), "--output", str(output), "--protocol", protocol]
    with pytest.raises(PolicyError, match="cohort binding"):
        cli.main(compile_args)
    assert not output.exists() and not (tmp_path / "worker").exists()
    def bind_cohort(compiled, binding, **context):
        assert binding == {"fixture": "registered-inputs"}
        assert context["stage"] == "update-1" and context["protocol"] == cli.read(protocol)
        assert context["repo_root"] == ROOT and context["data_root"] == tmp_path
        compiled.pop("native_contact_fit", None)
        compiled["preparation_source_receipts"] = []
        return compiled
    monkeypatch.setattr("speech_aware_evidence_acquisition.rails.system_text_cohort.bind_system_text_cohort", bind_cohort)
    compile_args += ["--cohort-binding", write(tmp_path / "cohort.json", {"fixture": "registered-inputs"})]
    cli.main(compile_args)
    result = cli.read(output)
    assert "prepared_phase_supply" not in result and "native_contact_fit" not in result
    assert result["preparation_source_receipts"] == []
    text = (tmp_path / "worker/configs" / result["phase_material"]["reviewer"]["instruction_template"]).read_text()
    assert text == response["changes"]["role_text"]["reviewer"]
    assert '"runtime_admission": "pending"' in capsys.readouterr().out
    compilation = cli.read(archive / "compilations/B-1-1.json")
    assert compilation["configuration_sha256"] == cli.content_hash(result)
    assert compilation["input_sha256"] == packet["input_sha256"]
    with pytest.raises(PolicyError, match="compilation already exists"):
        cli.main(compile_args)
    # The second blind slot refuses feedback before opening its nonexistent path.
    with pytest.raises(PolicyError, match="blind"):
        cli.main(args + ["--family", str(tmp_path / "not-present.json")])


def test_read_family_refuses_partial_spec_and_cycles(tmp_path, monkeypatch):
    bad = tmp_path / "family.json"
    write(bad, {"bindings": []})
    with pytest.raises(PolicyError, match="fields"):
        cli.read_family(bad)
    monkeypatch.setattr(cli, "require_read_registration", lambda *a, **k: {})
    write(bad, {"family_id": "fixture", "bindings": [], "expected_members": {},
                "initial_reference_member": None, "reference_family": str(bad), "read_registration": {}})
    with pytest.raises(PolicyError, match="cyclic"):
        cli.read_family(bad)


@pytest.mark.parametrize("profile", ["full-index-v1", "compact-feedback-v1", "coherent-feedback-v1"])
def test_blind_capsule_cli_exports_immutable_allowlist_and_refuses_feedback(tmp_path, capsys, profile):
    from test_system_proposer_capsule import fixture, reseal
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
    packet, roots = fixture(tmp_path)
    protocol = {"proposer_exact_version": "gpt-6-sol", "seed_bundle": {"bundle_id": packet["seed_bundle_id"]}}
    packet["protocol_sha256"] = content_hash(protocol)
    reseal(packet)
    archive = SystemSearchArchive(roots["archive"])
    archive.store_input(packet)
    args = ["--archive", str(roots["archive"]), "proposal-capsule", "--branch", "B", "--round", "1", "--slot", "1",
            "--protocol", write(tmp_path / "protocol.json", protocol), "--data-root", str(roots["data"]), "--view-profile", profile]
    with pytest.raises(PolicyError, match="blind"):
        cli.main(args + ["--family", str(tmp_path / "never-open.json")])
    cli.main(args)
    saved = cli.read(roots["archive"] / "capsules/B-1-1.json")
    assert len(saved["artifacts"]) == (3 if profile == "full-index-v1" else 4)
    assert saved["packet"]["input_sha256"] == packet["input_sha256"]
    assert '"invoked": false' in capsys.readouterr().out
    with pytest.raises(PolicyError, match="exists"):
        cli.main(args)


@pytest.mark.parametrize("profile", ["full-index-v1", "compact-feedback-v1", "coherent-feedback-v1"])
def test_learning_capsule_cli_requalifies_family_before_any_artifact_read(tmp_path, monkeypatch, profile):
    from test_system_proposer_capsule import fixture, reseal
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
    packet, roots = fixture(tmp_path, "L")
    protocol = {"proposer_exact_version": "gpt-6-sol", "seed_bundle": {"bundle_id": packet["seed_bundle_id"]}}
    packet["protocol_sha256"] = content_hash(protocol)
    reseal(packet)
    SystemSearchArchive(roots["archive"]).store_input(packet)
    args = ["--archive", str(roots["archive"]), "proposal-capsule", "--branch", "L", "--round", "1", "--slot", "1",
            "--protocol", write(tmp_path / "protocol.json", protocol), "--data-root", str(roots["data"]), "--view-profile", profile]
    with pytest.raises(PolicyError, match="complete family"):
        cli.main(args)
    def unqualified(_path):
        raise PolicyError("Synthetic family is not finalized.")
    monkeypatch.setattr(cli, "read_family", unqualified)
    with pytest.raises(PolicyError, match="finalized"):
        cli.main(args + ["--family", "synthetic-family", "--learning-member", "seed", "--learning-member", "seed-aa"])
    assert not (roots["archive"] / "capsules").exists()


@pytest.mark.parametrize("command", ["proposal-input", "proposal-capsule"])
def test_cli_refuses_a_different_seed_even_when_packet_hash_matches(tmp_path, command):
    from test_system_proposer_capsule import fixture, reseal
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
    packet, roots = fixture(tmp_path)
    protocol = {"proposer_exact_version": "gpt-6-sol", "seed_bundle": {"bundle_id": "f" * 64},
                "proposal_input_token_cap": 32768, "proposal_output_token_cap": 4096}
    packet["protocol_sha256"] = content_hash(protocol)
    reseal(packet)
    SystemSearchArchive(roots["archive"]).store_input(packet)
    args = ["--archive", str(roots["archive"]), command, "--branch", "B", "--round", "1", "--slot", "1",
            "--protocol", write(tmp_path / "protocol.json", protocol)]
    if command == "proposal-input":
        args += ["--seed-id", packet["seed_bundle_id"], "--parent-id", packet["parent_bundle_id"],
                 "--model-version", "gpt-6-sol", "--session-id", "synthetic"]
    else:
        args += ["--data-root", str(roots["data"])]
    with pytest.raises(PolicyError, match="seed"):
        cli.main(args)


def read_fixture(tmp_path, *, notes="ROOT COUNTERSIGNED after complete-family qualification."):
    import hashlib
    recipe_path = tmp_path / "docs/readiness/fixture/analysis-recipe.json"
    recipe_path.parent.mkdir(parents=True)
    recipe = {"read_run_id": "FIXTURE-READ", "initial_members": {"seed": "RUN-A", "seed-aa": "RUN-B"}}
    write(recipe_path, recipe)
    relpath = str(recipe_path.relative_to(tmp_path))
    row = ["FIXTURE-READ", "model-free-check", "discovery", "0", relpath, notes]
    header = "| run/experiment id | execution profile | split role | calls | artifacts | notes |\n|---|---|---|---|---|---|\n"
    ledger = tmp_path / "docs/exposure-ledger.md"
    ledger.write_text(header + "| " + " | ".join(row) + " |\n")
    spec = {"family_id": "initial", "bindings": [], "expected_members": recipe["initial_members"],
            "initial_reference_member": "seed", "reference_family": None,
            "read_registration": {"relpath": relpath, "sha256": hashlib.sha256(recipe_path.read_bytes()).hexdigest()}}
    return spec, ledger, recipe_path


@pytest.mark.parametrize("fault", ["unsigned", "pending", "other-read", "duplicate", "recipe-pin", "members", "artifact", "profile", "split", "contacts", "missing"])
def test_read_authority_refuses_before_any_feedback_or_reference_read(tmp_path, monkeypatch, fault):
    spec, ledger, recipe = read_fixture(tmp_path)
    text = ledger.read_text()
    if fault == "unsigned":
        text = text.replace("ROOT COUNTERSIGNED", "DRAFT")
    elif fault == "pending":
        text = text.replace("after complete-family qualification.", "but countersignature pending.")
    elif fault == "other-read":
        text = text.replace("FIXTURE-READ", "OTHER-READ")
    elif fault == "duplicate":
        text += text.splitlines()[-1] + "\n"
    elif fault == "recipe-pin":
        recipe.write_text(recipe.read_text() + " ")
    elif fault == "members":
        spec["expected_members"] = {"seed": "OTHER-RUN", "seed-aa": "RUN-B"}
    elif fault == "artifact":
        text = text.replace(spec["read_registration"]["relpath"], "docs/readiness/other.json")
    elif fault == "profile":
        text = text.replace("model-free-check", "bounded-discovery-probe")
    elif fault == "split":
        text = text.replace("discovery", "final-report")
    elif fault == "contacts":
        text = text.replace("| 0 |", "| 1 |")
    elif fault == "missing":
        spec.pop("read_registration")
    ledger.write_text(text)
    # Even an earlier valid family's scores must not be opened by an unsigned read.
    spec["reference_family"] = str(tmp_path / "MUST-NOT-OPEN.json")
    path = tmp_path / "family.json"
    write(path, spec)
    monkeypatch.setattr(cli.CompleteSystemFeedback, "from_family", lambda *a, **k: pytest.fail("feedback read before authority"))
    with pytest.raises(PolicyError):
        cli.read_family(path, repo_root=tmp_path)


def test_exact_signed_read_reaches_existing_complete_family_reader_and_records_authority(tmp_path, monkeypatch):
    spec, ledger, recipe = read_fixture(tmp_path)
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    calls = []
    def read_complete(bindings, **kwargs):
        calls.append(kwargs)
        return cli.CompleteSystemFeedback(canonical({"family_id": "initial", "verified_fixture": True}))
    monkeypatch.setattr(cli.CompleteSystemFeedback, "from_family", read_complete)
    path = tmp_path / "family.json"
    write(path, spec)
    result = cli.read_family(path, repo_root=tmp_path).as_json()
    assert calls[0]["expected_members"] == spec["expected_members"]
    assert result["read_authority"]["read_run_id"] == "FIXTURE-READ"
    assert result["read_authority"]["recipe"] == spec["read_registration"]
    assert len(result["read_authority"]["ledger_row_sha256"]) == 64


def test_authority_change_during_read_cannot_publish_feedback(tmp_path, monkeypatch):
    spec, ledger, _ = read_fixture(tmp_path)
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    def changed(*args, **kwargs):
        ledger.write_text(ledger.read_text().replace("after complete-family qualification.", "with amended scope."))
        return cli.CompleteSystemFeedback(canonical({"family_id": "initial"}))
    monkeypatch.setattr(cli.CompleteSystemFeedback, "from_family", changed)
    path = tmp_path / "family.json"
    write(path, spec)
    with pytest.raises(PolicyError, match="authority changed"):
        cli.read_family(path, repo_root=tmp_path)


def test_signed_row_does_not_replace_the_full_seal_and_scoring_gate(tmp_path, monkeypatch):
    spec, _, _ = read_fixture(tmp_path)
    def unsealed(*args, **kwargs):
        raise PolicyError("Synthetic A/A member is not finalized.")
    monkeypatch.setattr(cli.CompleteSystemFeedback, "from_family", unsealed)
    path = tmp_path / "family.json"
    write(path, spec)
    with pytest.raises(PolicyError, match="not finalized"):
        cli.read_family(path, repo_root=tmp_path)


def test_future_family_recipe_must_name_its_own_stage(tmp_path):
    import hashlib
    spec, _, path = read_fixture(tmp_path)
    spec["family_id"] = "update-1"
    with pytest.raises(PolicyError, match="another stage"):
        cli.require_read_registration(spec, repo_root=tmp_path)
    write(path, {"read_run_id": "FIXTURE-READ", "family_id": "update-1", "expected_members": spec["expected_members"]})
    spec["read_registration"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert cli.require_read_registration(spec, repo_root=tmp_path)["read_run_id"] == "FIXTURE-READ"
    spec["family_id"] = "update-2"
    with pytest.raises(PolicyError, match="family identity"):
        cli.require_read_registration(spec, repo_root=tmp_path)


def test_retention_cli_reverifies_family_and_reads_its_pinned_policy_map(tmp_path, monkeypatch):
    from test_system_search_selection import selection_fixture
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    import hashlib
    archive, protocol, value, evaluation = selection_fixture(tmp_path)
    recipe = tmp_path / "recipe.json"
    write(recipe, {"system_search_evaluation": evaluation})
    d = value.as_json()
    d["read_authority"]["recipe"] = {"relpath": "recipe.json", "sha256": hashlib.sha256(recipe.read_bytes()).hexdigest()}
    value = cli.CompleteSystemFeedback(canonical(d))
    calls = []
    def qualified(path, *, repo_root):
        calls.append((path, repo_root))
        return value
    monkeypatch.setattr(cli, "read_family", qualified)
    selected = evaluation["member_bindings"]["L-candidate-1"]["bundle_id"]
    args = ["--archive", str(archive.root), "retain-feedback", "--protocol", write(tmp_path / "protocol.json", protocol),
        "--family", "synthetic-complete-family", "--repo-root", str(tmp_path), "--stage", "update-1",
        "--branch", "L", "--selected-id", selected]
    cli.main(args)
    assert len(calls) == 1
    record = cli.read(archive.root / "retentions/update-1/L.json")
    assert record["active_ids"] == [selected]
    assert record["feedback_sha256"] == content_hash(value.as_json())
    # A changed registration cannot populate the other branch's retention.
    recipe.write_text(recipe.read_text() + " ")
    args[args.index("L")] = "B"
    with pytest.raises(PolicyError, match="hash"):
        cli.main(args)
    assert not (archive.root / "retentions/update-1/B.json").exists()


@pytest.mark.parametrize("command", ["retain-feedback", "freeze-finalists"])
def test_selection_cli_refuses_unqualified_family_before_publishing(tmp_path, monkeypatch, command):
    def unqualified(*args, **kwargs):
        raise PolicyError("Synthetic complete-family seal is missing.")
    monkeypatch.setattr(cli, "read_family", unqualified)
    args = ["--archive", str(tmp_path / "archive"), command, "--protocol", write(tmp_path / "p.json", {}),
            "--family", "unsigned-family", "--repo-root", str(tmp_path)]
    if command == "retain-feedback":
        args += ["--stage", "update-1", "--branch", "L", "--selected-id", "a" * 64]
    with pytest.raises(PolicyError, match="seal"):
        cli.main(args)
    assert not (tmp_path / "archive").exists()


def test_later_learning_input_cannot_choose_unrecorded_parent(tmp_path, monkeypatch):
    from test_system_search_selection import selection_fixture, retain
    archive, protocol, value, evaluation = selection_fixture(tmp_path)
    monkeypatch.setattr(cli, "read_family", lambda *_: value)
    args = ["--archive", str(archive.root), "proposal-input", "--branch", "L", "--round", "2", "--slot", "1",
        "--seed-id", protocol["seed_bundle"]["bundle_id"], "--parent-id", evaluation["member_bindings"]["L-candidate-1"]["bundle_id"],
        "--model-version", "GPT6-fixture-pinned", "--session-id", "fresh-learning-fixture",
        "--protocol", write(tmp_path / "protocol.json", protocol), "--family", "synthetic-family"]
    for cid in ("L-parent", "L-parent-aa", "L-candidate-1", "L-candidate-2"):
        args += ["--learning-member", cid]
    with pytest.raises(PolicyError, match="selection"):
        cli.main(args)
    assert not (archive.root / "inputs").exists()
    record = retain(archive, protocol, value, evaluation)
    cli.main(args)
    packet = cli.read(archive.root / "inputs/L-2-1.json")
    assert packet["selection"] == record
    assert "B-candidate" not in json.dumps(packet)


def test_learning_input_cannot_hide_a_losing_own_branch_member(tmp_path, monkeypatch):
    from test_system_search_selection import selection_fixture, retain
    archive, protocol, value, evaluation = selection_fixture(tmp_path)
    record = retain(archive, protocol, value, evaluation)
    monkeypatch.setattr(cli, "read_family", lambda *_: value)
    args = ["--archive", str(archive.root), "proposal-input", "--branch", "L", "--round", "2", "--slot", "1",
        "--seed-id", protocol["seed_bundle"]["bundle_id"], "--parent-id", record["active_ids"][0],
        "--model-version", "GPT6-fixture-pinned", "--session-id", "fresh-learning-fixture",
        "--protocol", write(tmp_path / "protocol.json", protocol), "--family", "synthetic-family",
        "--learning-member", "L-parent", "--learning-member", "L-parent-aa"]
    with pytest.raises(PolicyError, match="every learning"):
        cli.main(args)
    assert not (archive.root / "inputs").exists()


def test_common_selection_cli_freezes_exact_two_branch_choices(tmp_path, monkeypatch):
    from test_system_search_selection import selection_fixture
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    import hashlib
    archive, protocol, value, evaluation = selection_fixture(tmp_path, "selection")
    recipe = tmp_path / "recipe.json"
    write(recipe, {"system_search_evaluation": evaluation})
    d = value.as_json()
    d["read_authority"]["recipe"] = {"relpath": "recipe.json", "sha256": hashlib.sha256(recipe.read_bytes()).hexdigest()}
    value = cli.CompleteSystemFeedback(canonical(d))
    monkeypatch.setattr(cli, "read_family", lambda *a, **kw: value)
    prefix = ["--archive", str(archive.root)]
    common = ["--protocol", write(tmp_path / "protocol.json", protocol), "--family", "qualified-selection",
              "--repo-root", str(tmp_path)]
    for branch in ("L", "B"):
        cli.main(prefix + ["retain-feedback", *common, "--stage", "selection", "--branch", branch,
            "--selected-id", evaluation["member_bindings"][branch + "-1"]["bundle_id"]])
    cli.main(prefix + ["freeze-finalists", *common])
    assert cli.read(archive.root / "finalists.json")["runtime_admission"] == "separate-required"


def test_retention_cli_rejects_unregistered_policy_map(tmp_path, monkeypatch):
    from test_system_search_selection import selection_fixture
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    import hashlib
    archive, protocol, value, _ = selection_fixture(tmp_path)
    recipe = tmp_path / "recipe.json"
    write(recipe, {"not-a-policy-binding": {}})
    d = value.as_json()
    d["read_authority"]["recipe"] = {"relpath": "recipe.json", "sha256": hashlib.sha256(recipe.read_bytes()).hexdigest()}
    monkeypatch.setattr(cli, "read_family", lambda *a, **kw: cli.CompleteSystemFeedback(canonical(d)))
    with pytest.raises(PolicyError, match="registered policy"):
        cli.main(["--archive", str(archive.root), "retain-feedback", "--stage", "update-1", "--branch", "L",
            "--selected-id", protocol["seed_bundle"]["bundle_id"], "--protocol", write(tmp_path / "p.json", protocol),
            "--family", "qualified-family", "--repo-root", str(tmp_path)])
    assert not (archive.root / "retentions").exists()
