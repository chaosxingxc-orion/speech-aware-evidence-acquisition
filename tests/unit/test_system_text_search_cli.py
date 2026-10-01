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


def test_blind_session_import_and_shared_compilation_without_model_contacts(tmp_path, monkeypatch, capsys):
    archive = tmp_path / "archive"
    prefix = ["--archive", str(archive)]
    seed = SystemTextPolicyBundle.from_json(seed_document())
    cli.main(prefix + ["import-seed", "--bundle", write(tmp_path / "seed.json", seed.as_json())])
    protocol = write(tmp_path / "protocol.json", {"proposer_exact_version": "GPT6-fixture-pinned",
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
    cli.main(compile_args)
    result = cli.read(output)
    assert "prepared_phase_supply" not in result
    text = (tmp_path / "worker/configs" / result["phase_material"]["reviewer"]["instruction_template"]).read_text()
    assert text == response["changes"]["role_text"]["reviewer"]
    assert '"runtime_admission": "pending"' in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        cli.main(compile_args)
    # The second blind slot refuses feedback before opening its nonexistent path.
    with pytest.raises(PolicyError, match="blind"):
        cli.main(args + ["--family", str(tmp_path / "not-present.json")])


def test_read_family_refuses_partial_spec_and_cycles(tmp_path):
    bad = tmp_path / "family.json"
    write(bad, {"bindings": []})
    with pytest.raises(PolicyError, match="fields"):
        cli.read_family(bad)
    write(bad, {"family_id": "fixture", "bindings": [], "expected_members": {},
                "initial_reference_member": None, "reference_family": str(bad)})
    with pytest.raises(PolicyError, match="cyclic"):
        cli.read_family(bad)
