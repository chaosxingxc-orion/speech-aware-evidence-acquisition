"""Model-free adversarial checks for isolated system-text proposal inputs."""
import hashlib
import json
import os

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import proposal_input
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError, SystemTextPolicyBundle, TextPolicyUpdateProposal
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import (
    ProposerCapsule, ProposalDispatch, attest_outbound, input_references,
)
from test_system_text_policy import seed_document


def fixture(tmp_path, branch="B"):
    raw = seed_document()
    data = tmp_path / "data"
    data.mkdir()
    for name in ("snapshot", "release"):
        text = json.dumps({"kind": name, "note": "Frozen English knowledge."})
        (data / f"{name}.json").write_text(text)
        raw["knowledge"][name] = {"relpath": f"{name}.json", "sha256": hashlib.sha256(text.encode()).hexdigest()}
    seed = SystemTextPolicyBundle.from_json(raw)
    packet = proposal_input(branch="B", round_index=1, slot=1, seed=seed, parent=seed,
        model_version="gpt-6-sol", session_id="isolated-1", input_token_cap=32768, output_token_cap=4096)
    if branch == "L":
        packet.update(branch="L", complementary_policies=[], learning_history=[], feedback={
            "summaries": {"seed": {}, "seed-aa": {}}, "reference": {"sample_ids": ["slurp:train:1"]},
            "feedback": {"candidate_ids": ["seed", "seed-aa"], "groups": [
                {"sample_id": "slurp:train:1", "members": [
                    {"candidate_id": name, "execution": {}, "utility": 0} for name in ("seed", "seed-aa")]}]}})
    packet["input_sha256"] = content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
    return packet, {"data": data, "archive": tmp_path / "archive"}


def reseal(packet):
    packet["input_sha256"] = content_hash({k: v for k, v in packet.items() if k != "input_sha256"})


@pytest.mark.parametrize("paged", [False, True])
def test_released_snapshot_keeps_semantic_pin_and_exact_file_bytes(tmp_path, paged):
    from test_rails_runner import _knowledge_snapshot
    packet, roots = fixture(tmp_path)
    snapshot = _knowledge_snapshot()
    raw = json.dumps(snapshot.frozen_json(), indent=2).encode()
    (roots["data"] / "snapshot.json").write_bytes(raw)
    packet["parent_policy"]["knowledge"]["snapshot"]["sha256"] = snapshot.content_hash()
    packet["parent_bundle_id"] = packet["seed_bundle_id"] = content_hash(packet["parent_policy"])
    reseal(packet)
    capsule = ProposerCapsule.from_packet(packet, roots=roots,
        cache_root=tmp_path / "cache" if paged else None)
    artifact = next(a for a in capsule.as_json()["artifacts"] if a["kind"] == "knowledge-snapshot")
    assert artifact["source"]["sha256"] == snapshot.content_hash()
    assert artifact["sha256"] == hashlib.sha256(raw).hexdigest()
    page = capsule.read_artifact({"artifact_id": artifact["artifact_id"], "offset": 0, "limit": 16384})
    assert page["text"].encode() == raw


@pytest.mark.parametrize("mutation", ["body", "claim", "extra"])
def test_snapshot_semantic_pin_does_not_accept_tampering(tmp_path, mutation):
    from test_rails_runner import _knowledge_snapshot
    packet, roots = fixture(tmp_path)
    snapshot = _knowledge_snapshot()
    document = snapshot.frozen_json()
    packet["parent_policy"]["knowledge"]["snapshot"]["sha256"] = snapshot.content_hash()
    packet["parent_bundle_id"] = packet["seed_bundle_id"] = content_hash(packet["parent_policy"])
    reseal(packet)
    if mutation == "body":
        document["builder_policy_id"] = "changed"
    elif mutation == "claim":
        document["snapshot_sha256"] = "0" * 64
    else:
        document["unregistered"] = "extra context"
    (roots["data"] / "snapshot.json").write_text(json.dumps(document))
    with pytest.raises(PolicyError, match="snapshot|hash"):
        ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")


def test_blind_capsule_snapshots_only_registered_knowledge(tmp_path):
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    document = capsule.as_json()
    assert len(document["artifacts"]) == 3
    identity = document["artifacts"][0]["artifact_id"]
    (roots["data"] / "snapshot.json").write_text("Changed after packaging.")
    page = capsule.read_artifact({"artifact_id": identity, "offset": 0, "limit": 4096})
    assert "Frozen English knowledge" in page["text"]
    assert page["eof"] is True
    assert "path" not in page
    assert capsule.access_log[-1]["status"] == "supplied"


@pytest.mark.parametrize("name", ["feedback", "learning_history", "complementary_policies", "hidden_context"])
def test_blind_extra_context_rejected_before_read(tmp_path, name):
    packet, roots = fixture(tmp_path)
    packet[name] = {"path": "/unreadable/forbidden"}
    reseal(packet)
    with pytest.raises(PolicyError, match="blind|fields"):
        ProposerCapsule.from_packet(packet, roots=roots)


def test_missing_extra_and_changed_files_fail_closed(tmp_path):
    packet, roots = fixture(tmp_path)
    (roots["data"] / "release.json").write_text("Changed.")
    with pytest.raises(PolicyError, match="hash"):
        ProposerCapsule.from_packet(packet, roots=roots)
    packet["instructions"] += " Changed."
    with pytest.raises(PolicyError, match="fingerprint"):
        input_references(packet)


@pytest.mark.parametrize("path", ["../outside.json", "/etc/passwd", "C:/private/file", "dir\\file", "x/./file"])
def test_path_traversal_refused(tmp_path, path):
    packet, roots = fixture(tmp_path)
    packet["parent_policy"]["knowledge"]["snapshot"]["relpath"] = path
    packet["parent_bundle_id"] = content_hash(packet["parent_policy"])
    packet["seed_bundle_id"] = packet["parent_bundle_id"]
    reseal(packet)
    with pytest.raises(PolicyError, match="relative|path"):
        ProposerCapsule.from_packet(packet, roots=roots)


def test_symlink_refused_even_if_hash_matches(tmp_path):
    packet, roots = fixture(tmp_path)
    path = roots["data"] / "snapshot.json"
    outside = tmp_path / "outside.json"
    path.rename(outside)
    path.symlink_to(outside)
    with pytest.raises(PolicyError, match="link"):
        ProposerCapsule.from_packet(packet, roots=roots)


def test_learning_feedback_index_retains_all_cases_and_separates_context(tmp_path):
    packet, roots = fixture(tmp_path, "L")
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    initial = capsule.initial_input()
    assert "feedback" not in initial["packet"]
    evidence = next(a for a in initial["artifacts"] if a["kind"] == "complete-feedback")
    full = capsule.read_artifact({"artifact_id": evidence["artifact_id"], "offset": 0, "limit": 16384})
    assert json.loads(full["text"]) == packet["feedback"]
    assert initial["packet"]["input_sha256"] == packet["input_sha256"]
    assert initial["omissions"] == []


def test_large_ancestry_is_indexed_without_loss_or_blind_feedback(tmp_path):
    packet, roots = fixture(tmp_path)
    ids = [f"slurp:train:{i}" for i in range(20000)]
    packet["parent_policy"]["cumulative_sources"] = [{"kind": "knowledge", "sha256": "a" * 64, "sample_ids": ids}]
    packet["parent_bundle_id"] = packet["seed_bundle_id"] = content_hash(packet["parent_policy"])
    reseal(packet)
    capsule = ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
    initial = capsule.initial_input()
    assert len(json.dumps(capsule.request())) < 16000
    assert "feedback_summary" not in initial
    reference = next(a for a in initial["artifacts"] if a["kind"] == "complete-proposal-packet")
    full = "".join(capsule.read_artifact({"artifact_id": reference["artifact_id"], "offset": offset, "limit": 16384})["text"]
                   for offset in range(0, reference["characters"], 16384))
    assert json.loads(full) == packet
    assert initial["source_index"][0]["sources"][0]["sample_count"] == 20000
    assert initial["response_contract"]["example"]["parent_ids"] == [packet["parent_bundle_id"]]
    assert TextPolicyUpdateProposal.from_json(initial["response_contract"]["example"])


@pytest.mark.parametrize("tamper", [False, True])
def test_construction_source_is_release_bound_and_ancestry_checked(tmp_path, tamper):
    from test_semantic_knowledge_edits import rows
    packet, roots = fixture(tmp_path)
    source = {"schema": "saea-authored-semantic-knowledge-source-v1", "builder_policy_id": "fixture",
              "source_split_identity_hash": "b" * 64, "rows": rows()}
    raw = json.dumps(source).encode()
    (roots["data"] / "construction.json").write_bytes(raw)
    release = {"schema": "saea-knowledge-store-release-v1", "builder_policy_id": "fixture",
        "source_split_identity_hash": "b" * 64, "snapshot_sha256": packet["parent_policy"]["knowledge"]["snapshot"]["sha256"],
        "source": {"relpath": "construction.json", "sha256": hashlib.sha256(raw).hexdigest()}}
    raw = json.dumps(release).encode()
    (roots["data"] / "release.json").write_bytes(raw)
    packet["parent_policy"]["knowledge"]["release"]["sha256"] = hashlib.sha256(raw).hexdigest()
    packet["parent_policy"]["cumulative_sources"] = [{"kind": "knowledge", "sha256": "b" * 64,
        "sample_ids": [] if tamper else ["slurp:train:base"]}]
    packet["parent_bundle_id"] = packet["seed_bundle_id"] = content_hash(packet["parent_policy"])
    reseal(packet)
    if tamper:
        with pytest.raises(PolicyError, match="ancestry"):
            ProposerCapsule.from_packet(packet, roots=roots)
    else:
        capsule = ProposerCapsule.from_packet(packet, roots=roots)
        contract = next(a for a in capsule.as_json()["artifacts"] if a["kind"] == "slot-value-edit-context")
        assert json.loads(contract["text"])["base_rows_sha256"] == content_hash(rows())


@pytest.mark.parametrize("mutation", [
    lambda p: p["feedback"]["feedback"]["groups"][0].update(sample_id="slurp:test:1"),
    lambda p: p["feedback"]["feedback"]["groups"][0]["members"][0].update(candidate_id="B-candidate-1"),
    lambda p: p["feedback"]["summaries"].update({"B-parent": {}}),
])
def test_learning_refuses_test_or_other_branch_feedback(tmp_path, mutation):
    packet, roots = fixture(tmp_path, "L")
    mutation(packet)
    reseal(packet)
    with pytest.raises(PolicyError, match="TRAIN|branch"):
        ProposerCapsule.from_packet(packet, roots=roots)


@pytest.mark.parametrize("arguments", [
    {"artifact_id": "../../secret", "offset": 0, "limit": 100},
    {"artifact_id": "0" * 64, "offset": 0, "limit": 100},
    {"artifact_id": "0" * 64, "offset": -1, "limit": 100},
    {"artifact_id": "0" * 64, "offset": 0, "limit": 1000000},
    {"artifact_id": "0" * 64, "offset": 0, "limit": 100, "path": "/etc/passwd"},
])
def test_broker_denies_unlisted_access_and_keeps_audit(tmp_path, arguments):
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    with pytest.raises(PolicyError):
        capsule.read_artifact(arguments)
    assert capsule.access_log[-1]["status"] == "denied"


def test_outbound_gate_checks_nested_tools_and_all_context(tmp_path):
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    expected = capsule.request()
    assert attest_outbound(expected, expected)["matched"] is True
    for field, value in (("model", "different"), ("input", expected["input"] + [{"type": "additional_tools", "tools": []}]),
                         ("tools", expected["tools"] + [{"type": "function", "name": "shell"}]),
                         ("instructions", "Unregistered instructions.")):
        actual = {**expected, field: value}
        with pytest.raises(PolicyError, match="outbound"):
            attest_outbound(actual, expected)


def test_dispatch_reserves_before_transport_and_never_retries(tmp_path):
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    dispatch = ProposalDispatch(tmp_path / "dispatch", capsule)
    calls = []
    def failed_transport(request):
        calls.append(request)
        raise OSError("Synthetic connection failure.")
    with pytest.raises(OSError):
        dispatch.run(failed_transport)
    assert len(calls) == 1
    with pytest.raises(PolicyError, match="consumed"):
        ProposalDispatch(tmp_path / "dispatch", capsule).run(failed_transport)
    assert len(calls) == 1
    assert json.loads((tmp_path / "dispatch/B-1-1/outcome.json").read_text())["status"] == "failed"


def test_dispatch_raw_receipt_is_compatible_with_existing_archive(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    raw = json.dumps({"schema": "saea-text-policy-update-proposal-v1", "branch": "B", "round": 1,
        "slot": 1, "parent_ids": [packet["parent_bundle_id"]], "changes": {},
        "rationale": "Retain the seed.", "hypotheses": [], "evidence": []})
    result = ProposalDispatch(tmp_path / "dispatch", capsule).run(lambda request: {
        "raw_response": raw, "model_version": "gpt-6-sol", "input_tokens": 100, "output_tokens": 60})
    archive = SystemSearchArchive(tmp_path / "archive")
    archive.store_input(packet)
    assert archive.import_response(branch="B", round_index=1, slot=1, receipt=result)["status"] == "no-change"


def test_wrong_model_and_over_budget_receipts_remain_preserved(tmp_path):
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    with pytest.raises(PolicyError, match="model|budget"):
        ProposalDispatch(tmp_path / "dispatch", capsule).run(lambda request: {
            "raw_response": "Exact unusable response.", "model_version": "wrong", "input_tokens": 90000, "output_tokens": 3})
    raw = json.loads((tmp_path / "dispatch/B-1-1/transport-response.json").read_text())
    assert raw["raw_response"] == "Exact unusable response."


@pytest.mark.parametrize("change", ["model_version", "session_id"])
def test_sequence_model_and_fresh_session_checked_before_contact(tmp_path, change):
    packet, roots = fixture(tmp_path)
    result = {"raw_response": "Synthetic.", "model_version": "gpt-6-sol", "input_tokens": 10, "output_tokens": 3}
    ProposalDispatch(tmp_path / "dispatch", ProposerCapsule.from_packet(packet, roots=roots)).run(lambda _: result)
    packet["slot"] = 2
    if change == "model_version":
        packet["model_version"] = "different"
        packet["session_id"] = "different-session"
    reseal(packet)
    calls = []
    with pytest.raises(PolicyError, match="model|session"):
        ProposalDispatch(tmp_path / "dispatch", ProposerCapsule.from_packet(packet, roots=roots)).run(lambda r: calls.append(r))
    assert calls == []


@pytest.mark.parametrize("metering", [(None, 3), (10, None), (40000, 3), (10, 4097), (True, 3)])
def test_no_unverified_or_excess_budget_response_is_admitted(tmp_path, metering):
    packet, roots = fixture(tmp_path)
    with pytest.raises(PolicyError, match="budget"):
        ProposalDispatch(tmp_path / "dispatch", ProposerCapsule.from_packet(packet, roots=roots)).run(lambda _: {
            "raw_response": "Preserve this rejected output.", "model_version": "gpt-6-sol",
            "input_tokens": metering[0], "output_tokens": metering[1]})
    assert (tmp_path / "dispatch/B-1-1/transport-response.json").exists()


def test_complete_learning_traces_are_typed_pins_and_absolute_escape_is_denied(tmp_path):
    packet, roots = fixture(tmp_path, "L")
    trace = roots["data"] / "trace.jsonl"
    trace.write_text('{"message":"All success, harm and failure evidence is retained."}\n')
    pin = {"path": str(trace), "sha256": hashlib.sha256(trace.read_bytes()).hexdigest()}
    for member in packet["feedback"]["feedback"]["groups"][0]["members"]:
        member["execution"].update(trace=pin, terminal_output=pin)
    reseal(packet)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    assert len([a for a in capsule.as_json()["artifacts"] if a["kind"].startswith("feedback-")]) == 2
    outside = tmp_path / "outside.jsonl"
    trace.rename(outside)
    pin["path"] = str(outside)
    reseal(packet)
    with pytest.raises(PolicyError, match="root"):
        ProposerCapsule.from_packet(packet, roots=roots)


@pytest.mark.parametrize("disk_backed", [False, True])
def test_archived_learning_inputs_expand_only_earlier_registered_evidence(tmp_path, disk_backed):
    packet, roots = fixture(tmp_path, "L")
    archive = roots["archive"]
    entries = {"input": packet, "response": {"raw_response": "Invalid historical proposal."}, "import": {"status": "invalid"}}
    record = {"cumulative_sources": packet["parent_policy"]["cumulative_sources"]}
    for kind, doc in entries.items():
        folder = {"input": "inputs", "response": "responses", "import": "imports"}[kind]
        path = archive / folder / "L-1-1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc))
        record[kind] = {"relpath": f"{folder}/L-1-1.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    packet["round"] = 2
    packet["learning_history"] = [record]
    reseal(packet)
    capsule = ProposerCapsule.from_packet(packet, roots=roots,
        cache_root=tmp_path / "cache" if disk_backed else None)
    assert {"history-input", "history-response", "history-import"} <= {a["kind"] for a in capsule.as_json()["artifacts"]}
    record["input"]["relpath"] = "inputs/B-1-1.json"
    reseal(packet)
    with pytest.raises(PolicyError, match="branch"):
        ProposerCapsule.from_packet(packet, roots=roots)


def test_non_english_and_hardlinked_material_are_refused(tmp_path):
    packet, roots = fixture(tmp_path)
    path = roots["data"] / "snapshot.json"
    os.link(path, roots["data"] / "alias.json")
    with pytest.raises(PolicyError, match="linked"):
        ProposerCapsule.from_packet(packet, roots=roots)
    (roots["data"] / "alias.json").unlink()
    path.write_text("\u4e2d\u6587")
    packet["parent_policy"]["knowledge"]["snapshot"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    packet["parent_bundle_id"] = packet["seed_bundle_id"] = content_hash(packet["parent_policy"])
    reseal(packet)
    with pytest.raises(ValueError):
        ProposerCapsule.from_packet(packet, roots=roots)


def test_page_boundaries_are_replayable_and_mutating_returned_state_is_harmless(tmp_path):
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    doc = capsule.as_json()
    identity = doc["artifacts"][0]["artifact_id"]
    expected = doc["artifacts"][0]["text"]
    doc["artifacts"][0]["text"] = "Do not affect the snapshot."
    start = capsule.read_artifact({"artifact_id": identity, "offset": 0, "limit": 12})
    end = capsule.read_artifact({"artifact_id": identity, "offset": 12, "limit": 1000})
    assert start["text"] + end["text"] == expected
    assert start["eof"] is False and end["eof"] is True
    with pytest.raises(PolicyError, match="offset"):
        capsule.read_artifact({"artifact_id": identity, "offset": 100000, "limit": 3})


@pytest.mark.parametrize("mode", ["disk", "memory", "over-limit", "tampered"])
def test_large_history_has_separate_bounded_disk_custody(tmp_path, monkeypatch, mode):
    from speech_aware_evidence_acquisition.rails import system_proposer_capsule as module
    packet, roots = fixture(tmp_path, "L")
    record = {"cumulative_sources": packet["parent_policy"]["cumulative_sources"]}
    docs = {"input": packet, "response": {"raw_response": "No change."}, "import": {"status": "no-change"}}
    for kind, doc in docs.items():
        folder = {"input": "inputs", "response": "responses", "import": "imports"}[kind]
        path = roots["archive"] / folder / "L-1-1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc))
        record[kind] = {"relpath": f"{folder}/L-1-1.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    history_path = roots["archive"] / "inputs/L-1-1.json"
    original = history_path.read_text()
    size = history_path.stat().st_size
    monkeypatch.setattr(module, "MAX_ARTIFACT_BYTES", size - 1)
    monkeypatch.setattr(module, "MAX_DISK_HISTORY_BYTES", size - 1 if mode == "over-limit" else size + 100)
    packet["round"] = 2
    packet["learning_history"] = [record]
    reseal(packet)
    if mode == "tampered":
        history_path.write_text(original + " ")
    if mode != "disk":
        with pytest.raises(PolicyError, match="size|hash"):
            ProposerCapsule.from_packet(packet, roots=roots, cache_root=None if mode == "memory" else tmp_path / "cache")
    else:
        c = ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
        a = next(a for a in c.as_json()["artifacts"] if a["kind"] == "history-input")
        assert c._page(a, 0, a["characters"]) == original



def test_disk_history_diamond_parses_each_pinned_ancestor_once(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.rails import system_proposer_capsule as module
    packet, roots = fixture(tmp_path, "L")
    history = []
    for round_index in (1, 2):
        packet.update(round=round_index, learning_history=list(history))
        reseal(packet)
        record = {"cumulative_sources": packet["parent_policy"]["cumulative_sources"]}
        for kind, doc in {"input": packet, "response": {"raw_response": "No change."}, "import": {"status": "no-change"}}.items():
            folder = {"input": "inputs", "response": "responses", "import": "imports"}[kind]
            rel = f"{folder}/L-{round_index}-1.json"
            path = roots["archive"] / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(doc))
            record[kind] = {"relpath": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        history.append(record)
    packet.update(round=3, learning_history=history)
    reseal(packet)
    reads = []
    original = module._read_registered
    def observed(reference, roots, **kwargs):
        if reference["kind"] == "history-input":
            reads.append(reference["pin"]["relpath"])
        return original(reference, roots, **kwargs)
    monkeypatch.setattr(module, "_read_registered", observed)
    c = ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
    assert sorted(reads) == ["inputs/L-1-1.json", "inputs/L-2-1.json"]
    assert len([a for a in c.as_json()["artifacts"] if a["kind"] == "history-input"]) == 2
