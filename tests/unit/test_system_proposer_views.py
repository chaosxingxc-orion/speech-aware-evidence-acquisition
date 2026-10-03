"""Compact views retain every case and exact source addresses, without model calls."""
import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError, canonical
from test_system_proposer_capsule import fixture, reseal
from test_system_text_feedback import counts


PROFILE = "compact-feedback-v1"


def learning_fixture(tmp_path, size=5):
    packet, roots = fixture(tmp_path, "L")
    groups = []
    ids = [f"slurp:train:{i}" for i in range(size)]
    # Exercise repair, damage, unchanged, changed-but-unresolved, and failure.
    good = counts(scenario_action_exact=1, slot_f1_exact_tp=1,
                  slu_f1_word_tp=1, slu_f1_char_tp=1)
    bad = counts(scenario_action_exact=1, slot_f1_exact_fn=1,
                 slu_f1_word_fn=1, slu_f1_char_fn=1)
    worse = {**bad, "slot_f1_exact_fp": 1, "slu_f1_word_fp": 1}
    alternatives = [(bad, good), (good, bad), (good, good), (bad, worse), (bad, bad)]
    pins = {}
    for cid in ("seed", "seed-aa"):
        terminals, trace = [], []
        for i, sid in enumerate(ids):
            request = f"{cid}-{i}"
            terminals.append({"sample_id": sid, "text": "Frozen final answer.", "native_episode_receipt": {
                "role_visits": [{"role_id": "solver", "execution_receipt": {"contacts": [{"request_id": request}]}}],
                "planner_routes": [{"action": "ACCEPT"}]}})
            # A large request body must remain addressable without entering the preview.
            trace.append({"record_id": request + "/request", "channel": "MODEL_REQUEST",
                          "payload": {"text": "Complete unchanged prompt. " * 200}})
            trace.append({"record_id": request + "/response", "channel": "MODEL_RESPONSE",
                          "payload": {"text": "Observed English response. " * 20}})
        pins[cid] = {}
        for field, rows in (("terminal_output", terminals), ("trace", trace)):
            p = roots["data"] / f"{cid}-{field}.jsonl"
            text = "".join(canonical(r) + "\r\n" for r in rows)
            p.write_text(text, newline="")
            pins[cid][field] = {"path": str(p), "sha256": hashlib.sha256(text.encode()).hexdigest()}
    for i, sid in enumerate(ids):
        members = []
        for j, cid in enumerate(("seed", "seed-aa")):
            members.append({"candidate_id": cid, "native_counts": copy.deepcopy(alternatives[i % 5][j]),
                "utility": float(j), "relative_return": float(j), "execution": {
                    **pins[cid], "reliable_completion": i % 5 != 4, "delivery_kind": "accepted",
                    "model_calls": 1, "tool_calls": 0, "role_contacts": {"solver": 1}}})
        groups.append({"sample_id": sid, "members": members})
    packet["feedback"].update(family_id="initial")
    packet["feedback"]["feedback"]["groups"] = groups
    packet["feedback"]["reference"]["sample_ids"] = ids
    reseal(packet)
    return packet, roots


def read_all(capsule, identity):
    parts, offset = [], 0
    while True:
        page = capsule.read_artifact({"artifact_id": identity, "offset": offset, "limit": 2048})
        parts.append(page["text"])
        if page["eof"]:
            return "".join(parts)
        offset = page["next_offset"]


@pytest.mark.parametrize("paged", [False, True])
def test_every_case_and_outcome_is_indexed_and_originals_roundtrip(tmp_path, paged):
    packet, roots = learning_fixture(tmp_path)
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE,
        cache_root=tmp_path / "cache" if paged else None)
    overview = c.initial_input()["feedback_overview"]
    assert overview["sample_count"] == 5
    comparison = overview["comparisons"]["seed-aa"]
    assert comparison["counts"] == dict.fromkeys([
        "correct_answer_repaired", "correct_answer_damaged", "native_counts_unchanged",
        "changed_not_resolved", "unreliable_execution"], 1)
    assert comparison["interpretation"] == "A/A variation, not a treatment effect"
    index = json.loads(read_all(c, overview["case_index"]["artifact_id"]))
    assert [r["sample_id"] for r in index["cases"]] == [g["sample_id"] for g in packet["feedback"]["feedback"]["groups"]]
    for entry, group in zip(index["cases"], packet["feedback"]["feedback"]["groups"], strict=True):
        view = json.loads(read_all(c, entry["artifact_id"]))
        brief = json.loads(read_all(c, entry["brief_artifact_ids"]["seed-aa"]))
        assert brief["details_artifact_id"] == entry["artifact_id"]
        assert brief["omissions"]
        assert view["sample_id"] == group["sample_id"]
        assert view["omissions"]
        for member, original, small in zip(view["members"], group["members"], brief["members"], strict=True):
            assert member["native_counts"] == original["native_counts"]
            assert dict(zip(brief["count_fields"], small["counts"], strict=True)) == original["native_counts"]
            assert member["utility"] == original["utility"]
            address = member["terminal"]["source"]
            raw = read_all(c, address["artifact_id"])
            exact = json.loads(raw[address["offset"]:address["offset"] + address["characters"]])
            assert exact["sample_id"] == group["sample_id"]
            response = member["role_responses"][0]
            loc = response["source"]
            exact = json.loads(read_all(c, loc["artifact_id"])[loc["offset"]:loc["offset"] + loc["characters"]])
            assert exact["payload"]["text"].startswith(response["text_prefix"])
            assert len(exact["payload"]["text"]) == response["text_characters"]
    full = next(a for a in c.as_json()["artifacts"] if a["kind"] == "complete-proposal-packet")
    assert json.loads(read_all(c, full["artifact_id"])) == packet
    restored = ProposerCapsule.from_json(c.as_json())
    assert restored.request() == c.request()


def test_catalog_size_does_not_expand_with_all_400_case_bodies(tmp_path):
    packet, roots = learning_fixture(tmp_path, size=400)
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    initial = c.initial_input()
    assert len(initial["artifacts"]) < 12
    assert len(canonical(initial)) < 10000
    assert initial["packet"]["parent_policy"]["role_text"] == packet["parent_policy"]["role_text"]
    catalogue = json.loads(read_all(c, initial["artifact_catalog"]["artifact_id"]))
    assert sum(a["kind"] == "feedback-case-view" for a in catalogue["artifacts"]) == 400
    assert len(json.loads(read_all(c, initial["feedback_overview"]["case_index"]["artifact_id"]))["cases"]) == 400


def test_blind_compact_profile_has_no_feedback_or_learning_derived_views(tmp_path):
    packet, roots = fixture(tmp_path, "B")
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    assert "feedback_overview" not in c.initial_input()
    assert not any(a["kind"].startswith("feedback-") for a in c.as_json()["artifacts"])
    assert c.request()["tools"][0]["parameters"]["properties"]["limit"]["maximum"] == 2048
    with pytest.raises(PolicyError, match="page"):
        c.read_artifact({"artifact_id": c.as_json()["artifacts"][0]["artifact_id"], "offset": 0, "limit": 2049})


@pytest.mark.parametrize("mutation", ["missing-member", "duplicate-sample", "unknown-count", "missing-terminal", "duplicate-response"])
def test_incomplete_derived_views_fail_before_export(tmp_path, mutation):
    packet, roots = learning_fixture(tmp_path)
    if mutation == "missing-member":
        packet["feedback"]["feedback"]["groups"][0]["members"].pop()
    elif mutation == "duplicate-sample":
        packet["feedback"]["feedback"]["groups"][1]["sample_id"] = "slurp:train:0"
    elif mutation == "unknown-count":
        packet["feedback"]["feedback"]["groups"][0]["members"][0]["native_counts"]["slu_f1_word_fp"] = float("inf")
    else:
        field = "terminal_output" if mutation == "missing-terminal" else "trace"
        p = roots["data"] / f"seed-{field}.jsonl"
        lines = p.read_text().splitlines(keepends=True)
        p.write_text("".join(lines[1:] if field == "terminal_output" else lines + [lines[1]]))
        for group in packet["feedback"]["feedback"]["groups"]:
            group["members"][0]["execution"][field]["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises((PolicyError, ValueError)):
        reseal(packet)
        ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)


def test_legacy_profile_request_is_unchanged_and_unknown_profile_refused(tmp_path):
    packet, roots = fixture(tmp_path)
    original = ProposerCapsule.from_packet(packet, roots=roots)
    assert ProposerCapsule.from_json(original.as_json()).request() == original.request()
    with pytest.raises(PolicyError, match="profile"):
        ProposerCapsule.from_packet(packet, roots=roots, view_profile="unregistered")


def test_representatives_are_stable_and_missing_response_is_visible(tmp_path):
    packet, roots = learning_fixture(tmp_path, size=15)
    trace = roots["data"] / "seed-trace.jsonl"
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    trace.write_text("".join(canonical(r) + "\n" for r in rows if r["record_id"] != "seed-0/response"))
    for group in packet["feedback"]["feedback"]["groups"]:
        group["members"][0]["execution"]["trace"]["sha256"] = hashlib.sha256(trace.read_bytes()).hexdigest()
    reseal(packet)
    a = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    view = next(x for x in a.as_json()["artifacts"] if x["kind"] == "feedback-case-view" and x["source"]["sample_id"] == "slurp:train:0")
    assert json.loads(view["text"])["members"][0]["role_responses"][0]["missing_response"] is True
    packet["feedback"]["feedback"]["groups"].reverse()
    reseal(packet)
    b = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    def choices(capsule):
        comparison = capsule.initial_input()["feedback_overview"]["comparisons"]["seed-aa"]
        return {k: v["sample_id"] for k, v in comparison["representatives"].items()}
    assert choices(a) == choices(b)


def test_larger_learning_family_keeps_every_member_but_each_brief_is_one_comparison(tmp_path):
    packet, roots = learning_fixture(tmp_path)
    for group in packet["feedback"]["feedback"]["groups"]:
        for cid in ("L-candidate-1", "L-candidate-2"):
            other = copy.deepcopy(group["members"][1])
            other["candidate_id"] = cid
            group["members"].append(other)
    packet["feedback"]["summaries"].update({"L-candidate-1": {}, "L-candidate-2": {}})
    reseal(packet)
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    index = json.loads(read_all(c, c.initial_input()["feedback_overview"]["case_index"]["artifact_id"]))
    assert len(c.initial_input()["feedback_overview"]["comparisons"]) == 3
    for entry in index["cases"]:
        assert len(json.loads(read_all(c, entry["artifact_id"]))["members"]) == 4
        for cid, identity in entry["brief_artifact_ids"].items():
            brief = json.loads(read_all(c, identity))
            assert {m["candidate_id"] for m in brief["members"]} == {"seed", cid}
            assert brief["details_artifact_id"] == entry["artifact_id"]


def test_three_contact_compact_lookup_and_submission_keeps_the_actual_budget_gate(tmp_path):
    from test_system_proposer_responses import server, reply, completed, call
    from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesHTTP, ResponsesProposer
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposalDispatch
    from test_system_proposer_round import runner
    packet, roots = learning_fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    identity = capsule.initial_input()["feedback_overview"]["comparisons"]["seed-aa"]["representatives"]["correct_answer_damaged"]["artifact_id"]
    args = {"artifact_id": identity, "offset": 0, "limit": 1024}
    first = call(identity, arguments=canonical(args), call_id="read-first")
    second = call(identity, arguments=canonical({**args, "offset": 1024}), call_id="read-tail")
    reservations = []
    with server([reply(completed([first])), reply(completed([second])), reply(completed())]) as (endpoint, requests):
        transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
            audit_dir=tmp_path / "transport", input_counter=runner.request_bound,
            before_contact=reservations.append, contact_cap=4)
        result = ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert len(requests) == len(reservations) == 3
    assert result["input_tokens"] == 300  # Synthetic server usage, never a provider cost claim.
    assert "32768 tokens" in requests[0]["body"]["instructions"]
    assert "32568 tokens" in requests[2]["body"]["instructions"]
    assert reservations[2]["input_token_bound"] + 200 <= 32768
    for request, reservation in zip(requests, reservations, strict=True):
        assert f"bound: {reservation['input_token_bound']} tokens" in request["body"]["instructions"]
    assert "previous contact actually used 100 input tokens" in requests[2]["body"]["instructions"]
    assert "Contacts left including this one: 2" in requests[2]["body"]["instructions"]
    assert len(capsule.access_log) == 2
    assert requests[2]["body"]["input"][-1]["call_id"] == "read-tail"


EVIDENCE_PROFILE = "source-examples-v1"


@pytest.mark.parametrize("paged", [False, True])
def test_source_examples_inline_all_outcome_types_with_exact_source_ranges(tmp_path, paged):
    packet, roots = learning_fixture(tmp_path)
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=EVIDENCE_PROFILE,
        cache_root=tmp_path / "cache" if paged else None)
    initial = c.initial_input()
    evidence = initial["feedback_examples"]
    assert len(canonical(evidence).encode()) <= 8192
    assert set(evidence["covered_categories"]) == {
        "correct_answer_repaired", "correct_answer_damaged", "native_counts_unchanged",
        "changed_not_resolved", "unreliable_execution", "parent_correct", "parent_incorrect"}
    assert evidence["omissions"] and evidence["examples"]
    for example in evidence["examples"]:
        detail = json.loads(read_all(c, example["details_artifact_id"]))
        assert detail["sample_id"] == example["sample_id"]
        for member in example["members"]:
            assert len(member["counts"]) == len(evidence["count_fields"])
            for response in member["responses"]:
                role, prefix, text_chars, omitted, location = response
                identity = evidence["sources"][location[0]]
                original = json.loads(read_all(c, identity)[location[1]:location[1] + location[2]])
                text = original["payload"]["text"]
                assert text.startswith(prefix) and len(text) == text_chars
                assert omitted == text_chars - len(prefix)
                assert role == "solver"
    assert c.access_log  # Assertions used the normal audited broker.
    restored = ProposerCapsule.from_json(c.as_json())
    assert restored.request() == c.request()
    assert "Examine the inline source examples" in c.request()["instructions"]


def test_source_examples_are_deterministic_bounded_and_never_enter_blind_input(tmp_path):
    packet, roots = learning_fixture(tmp_path, size=400)
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=EVIDENCE_PROFILE)
    examples = c.initial_input()["feedback_examples"]
    choices = [(e["sample_id"], e["comparison"], e["categories"]) for e in examples["examples"]]
    packet["feedback"]["feedback"]["groups"].reverse()
    reseal(packet)
    reversed_c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=EVIDENCE_PROFILE)
    assert choices == [(e["sample_id"], e["comparison"], e["categories"])
                       for e in reversed_c.initial_input()["feedback_examples"]["examples"]]
    assert len(canonical(examples).encode()) <= 8192
    assert examples["sample_count"] == 400
    assert len(examples["examples"]) <= 7
    other = tmp_path / "blind"
    other.mkdir()
    blind, blind_roots = fixture(other, "B")
    b = ProposerCapsule.from_packet(blind, roots=blind_roots, view_profile=EVIDENCE_PROFILE)
    assert "feedback_examples" not in b.initial_input()
    assert not any(a["kind"].startswith("feedback-") for a in b.as_json()["artifacts"])
    legacy = ProposerCapsule.from_packet(blind, roots=blind_roots, view_profile=PROFILE)
    assert b.request() == legacy.request()


def test_inline_evidence_is_explicitly_opt_in_and_missing_responses_stay_visible(tmp_path):
    packet, roots = learning_fixture(tmp_path)
    legacy = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    assert "feedback_examples" not in legacy.initial_input()
    trace = roots["data"] / "seed-trace.jsonl"
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    trace.write_text("".join(canonical(r) + "\n" for r in rows if r["channel"] != "MODEL_RESPONSE"))
    for group in packet["feedback"]["feedback"]["groups"]:
        group["members"][0]["execution"]["trace"]["sha256"] = hashlib.sha256(trace.read_bytes()).hexdigest()
    reseal(packet)
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=EVIDENCE_PROFILE)
    evidence = c.initial_input()["feedback_examples"]
    assert all(m["missing_responses"] == 1 for e in evidence["examples"]
               for m in e["members"] if m["candidate_id"] == "seed")


@pytest.mark.parametrize("mutation, message", [("empty", "complete comparison"),
    ("source", "differs from indexed source"), ("large", "presentation bound")])
def test_inline_examples_fail_closed_on_missing_sources_or_excessive_view(tmp_path, mutation, message):
    from speech_aware_evidence_acquisition.rails.system_proposer_views import inline_feedback_examples
    packet, roots = learning_fixture(tmp_path)
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    overview = c.initial_input()["feedback_overview"]
    artifacts = {a["artifact_id"]: a for a in c.as_json()["artifacts"]}
    for a in artifacts.values():
        if a["kind"] == "feedback-case-index" and mutation == "empty":
            d = json.loads(a["text"])
            d["cases"] = []
            a["text"] = canonical(d)
            a["characters"] = len(a["text"])
        if a["kind"] == "feedback-case-view" and mutation in {"large", "source"}:
            d = json.loads(a["text"])
            for m in d["members"]:
                if mutation == "large":
                    m["role_responses"] *= 200
                else:
                    m["role_responses"][0]["text_characters"] += 1
            a["text"] = canonical(d)
            a["characters"] = len(a["text"])
    with pytest.raises(PolicyError, match=message):
        inline_feedback_examples(overview, artifacts, ProposerCapsule._page)


def test_one_contact_response_transport_receives_inline_examples_without_broker_read(tmp_path):
    from test_system_proposer_responses import server, reply, completed
    from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesHTTP, ResponsesProposer
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposalDispatch
    from test_system_proposer_round import runner
    packet, roots = learning_fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots, view_profile=EVIDENCE_PROFILE)
    reservations = []
    with server([reply(completed())]) as (endpoint, requests):
        transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
            audit_dir=tmp_path / "transport", input_counter=runner.request_bound,
            before_contact=reservations.append, contact_cap=4)
        ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert len(requests) == len(reservations) == 1
    assert not capsule.access_log
    payload = json.loads(requests[0]["body"]["input"][0]["content"])
    assert payload["feedback_examples"]["examples"]
    assert reservations[0]["input_token_bound"] <= 32768
