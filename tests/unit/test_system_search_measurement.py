"""Measured workflow latency cannot be replaced by call counts or partial timing."""

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.system_search_measurement import (
    validate_profile,
    measured_rows,
    measured_frontier,
)
from test_system_search_selection import selection_fixture
from test_system_text_feedback import _cost_fixture


def profile():
    return {
        "schema": "saea-system-search-measurement-v2",
        "latency_scope": "sample-admission-to-settled-workflow-v1",
        "schedule": "sequential-trajectory",
        "slot_count": 4,
        "queue_depth": 4,
        "minimum_reliable_completion_rate": 1.0,
    }


def timing(ids, seconds=10, *, failed=False):
    from speech_aware_evidence_acquisition.analysis.system_cache_cost import (
        summarize_sample_execution_timing,
    )

    return summarize_sample_execution_timing(
        [
            {
                "schema": "saea-sample-execution-timing-v1",
                "sample_id": sid,
                "execution_unit_id": None,
                "admission_index": i,
                "expected_samples": len(ids),
                "slot_count": 4,
                "queue_depth": 4,
                "batch_started_ns": 0,
                "admitted_ns": i * 1000000000,
                "finished_ns": int((i + seconds) * 1000000000),
                "status": "failed" if failed and i == 0 else "completed",
                "error_type": "RuntimeError" if failed and i == 0 else None,
            }
            for i, sid in enumerate(ids)
        ],
        expected_sample_ids=ids,
    )


def measured_fixture(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    p = profile()
    protocol["measurement_profile"] = p
    evaluation["protocol_sha256"] = content_hash(protocol)
    d = feedback.as_json()
    ids = [g["sample_id"] for g in d["feedback"]["groups"]]
    for cid, row in d["summaries"].items():
        row["sample_timing"] = timing(ids)
        row["timing_session_sha256"] = "a" * 64
    d["measurement_profile"] = p
    return archive, protocol, CompleteSystemFeedback(canonical(d)), evaluation


def test_actual_trace_timing_joins_terminal_without_changing_legacy_output(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_text_feedback import (
        _row_cost_and_terminal,
    )

    def add(records, outputs):
        sid = outputs[0]["sample_id"]
        row = {
            "schema": "saea-sample-execution-timing-v1",
            "sample_id": sid,
            "execution_unit_id": None,
            "admission_index": 0,
            "expected_samples": 1,
            "slot_count": 4,
            "queue_depth": 4,
            "batch_started_ns": 0,
            "admitted_ns": 3000000000,
            "finished_ns": 10000000000,
            "status": "completed",
            "error_type": None,
        }
        records.append(
            {
                "channel": "USE",
                "record_id": sid + "/native/sample-execution-timing",
                "payload": {"use_sample_execution_timing": row},
            }
        )

    manifest, sid = _cost_fixture(tmp_path, add)
    legacy = _row_cost_and_terminal(manifest)[sid]
    assert legacy["wall_time_seconds"] is None and "sample_timing" not in legacy
    row = _row_cost_and_terminal(manifest, include_sample_timing=True)[sid]
    assert row["wall_time_seconds"] == 7
    assert row["sample_timing"]["admission_wait_seconds"] == 3
    assert row["sample_timing"]["status"] == "completed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("slot_count", True),
        ("queue_depth", 0),
        ("schedule", "node-panel"),
        ("latency_scope", "whole-business-end-to-end"),
        ("minimum_reliable_completion_rate", float("nan")),
        ("unknown", "value"),
    ],
)
def test_profile_rejects_unsupported_or_ambiguous_semantics(field, value):
    p = profile()
    p[field] = value
    with pytest.raises(PolicyError):
        validate_profile(p)


def test_latency_frontier_keeps_balanced_candidate_and_ignores_call_count(tmp_path):
    _, protocol, feedback, evaluation = measured_fixture(tmp_path)
    d = feedback.as_json()
    ids = [g["sample_id"] for g in d["feedback"]["groups"]]
    a, b, c = "L-parent", "L-candidate-1", "L-candidate-2"
    for cid, quality, seconds in [(a, 0.9, 30), (b, 0.7, 10), (c, 0.8, 20)]:
        d["summaries"][cid].update(
            slu_f1=quality, sample_timing=timing(ids, seconds), model_calls=100000
        )
    rows = measured_rows(d, [a, b, c], evaluation["member_bindings"], profile=profile())
    assert len(measured_frontier(rows, profile=profile())) == 3
    d["summaries"][c]["sample_timing"] = timing(ids, 35)
    rows = measured_rows(d, [a, b, c], evaluation["member_bindings"], profile=profile())
    assert {r["candidate_id"] for r in measured_frontier(rows, profile=profile())} == {
        a,
        b,
    }


@pytest.mark.parametrize(
    "fault", ["missing", "partial", "session", "queue", "profile", "changed-hash"]
)
def test_comparison_refuses_missing_or_mixed_measurements(tmp_path, fault):
    _, _, feedback, evaluation = measured_fixture(tmp_path)
    d = feedback.as_json()
    first = d["summaries"]["L-parent"]
    if fault == "missing":
        first.pop("sample_timing")
    elif fault == "partial":
        first["sample_timing"]["samples"].pop()
    elif fault == "session":
        first["timing_session_sha256"] = "b" * 64
    elif fault == "queue":
        first["sample_timing"]["queue_depth"] = 20
    elif fault == "profile":
        d["measurement_profile"]["slot_count"] = 2
    else:
        first["sample_timing"]["all_samples"]["mean_seconds"] = 0
    with pytest.raises(PolicyError):
        measured_rows(
            d,
            ["L-parent", "L-candidate-1"],
            evaluation["member_bindings"],
            profile=profile(),
        )


def test_unreliable_fast_candidate_is_recorded_but_not_selected(tmp_path):
    _, _, feedback, evaluation = measured_fixture(tmp_path)
    d = feedback.as_json()
    row = d["summaries"]["L-candidate-1"]
    row["reliable_completion_rate"] = 0.5
    rows = measured_rows(
        d,
        ["L-parent", "L-candidate-1"],
        evaluation["member_bindings"],
        profile=profile(),
    )
    assert rows[1]["eligible"] is False
    assert [r["candidate_id"] for r in measured_frontier(rows, profile=profile())] == [
        "L-parent"
    ]


def test_retention_uses_latency_profile_and_keeps_branch_projection(tmp_path):
    archive, protocol, feedback, evaluation = measured_fixture(tmp_path)
    d = feedback.as_json()
    ids = [g["sample_id"] for g in d["feedback"]["groups"]]
    # Candidate2 has fewer calls but is slower and less accurate than Candidate1.
    d["summaries"]["L-candidate-2"]["sample_timing"] = timing(ids, 30)
    feedback = CompleteSystemFeedback(canonical(d))
    selected = evaluation["member_bindings"]["L-candidate-1"]["bundle_id"]
    record = archive.retain_feedback(
        protocol=protocol,
        stage_name="update-1",
        feedback=feedback,
        evaluation=evaluation,
        branch="L",
        selected_ids=[selected],
    )
    assert record["measurement_profile"] == profile()
    assert len(record["frontier"]) == 1
    assert record["frontier"][0]["mean_sample_seconds"] == 10
    assert "B-candidate" not in canonical(record)
    own = feedback.learning_view(
        [cid for cid in d["summaries"] if cid.startswith("L-")]
    ).as_json()
    assert own["measurement_profile"] == profile()
    assert "B-candidate" not in canonical(own)


def test_small_panel_selection_and_capsule_guard_use_the_same_profile(tmp_path):
    from test_system_optimization import learning_fixture
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        exploratory_selection,
        require_exploratory_packet,
    )

    protocol, packet = learning_fixture(tmp_path)
    protocol["measurement_profile"] = profile()
    d = packet["feedback"]
    d["measurement_profile"] = profile()
    ids = [g["sample_id"] for g in d["feedback"]["groups"]]
    for summary in d["summaries"].values():
        summary.update(sample_timing=timing(ids), timing_session_sha256="a" * 64)
    registration = {"member_bindings": packet["selection"]["member_bindings"]}
    selected = exploratory_selection(
        CompleteSystemFeedback(canonical(d)),
        registration=registration,
        binding={
            "next_round": 3,
            "parent_id": packet["parent_bundle_id"],
            "complementary_ids": [],
        },
        protocol=protocol,
        parents=[{"cumulative_sources": []}],
    )
    assert selected["retain_parent"] is True
    assert selected["measurement_profile"] == profile()
    assert "B-candidate" not in canonical(selected)
    packet.update(selection=selected, protocol_sha256=content_hash(protocol))
    require_exploratory_packet(packet, protocol=protocol)
    protocol["measurement_profile"]["slot_count"] = 2
    with pytest.raises(PolicyError):
        require_exploratory_packet(packet, protocol=protocol)


def test_panel_definition_binds_profile_to_protocol_recipe_and_registration(tmp_path):
    from test_system_text_panel_read import fixture, seal
    from speech_aware_evidence_acquisition.analysis.system_text_panel import (
        validate_definition,
    )

    _, recipe, registration, owner, _, _, _, growth, protocol, pool, _ = fixture(
        tmp_path, 20
    )
    protocol["measurement_profile"] = profile()
    recipe["measurement_profile"] = profile()
    registration["measurement_profile"] = profile()
    registration["proposal_protocol_sha256"] = content_hash(protocol)
    seal(registration)
    validate_definition(
        recipe, registration, owner, growth=growth, protocol=protocol, pool_ids=pool
    )
    recipe["measurement_profile"]["slot_count"] = 2
    with pytest.raises(PolicyError, match="measurement"):
        validate_definition(
            recipe, registration, owner, growth=growth, protocol=protocol, pool_ids=pool
        )


def test_bad_measurement_profile_refuses_before_any_family_read(monkeypatch):
    from speech_aware_evidence_acquisition.analysis import system_text_pilot as pilot

    monkeypatch.setattr(
        pilot, "preflight_family", lambda *a: pytest.fail("unregistered source read")
    )
    with pytest.raises(PolicyError, match="profile"):
        pilot._read_complete_evidence(
            [],
            recipe={"measurement_profile": profile()},
            registration={},
            authority={},
            family="held",
            schema="held",
            evidence_type=CompleteSystemFeedback,
        )


def test_legacy_duplicate_candidate_keeps_parent_first_and_aa_separate(tmp_path):
    from test_system_optimization import learning_fixture
    from speech_aware_evidence_acquisition.rails.system_optimization import exploratory_selection
    protocol, packet = learning_fixture(tmp_path)
    protocol["measurement_profile"] = profile()
    d = packet["feedback"]
    d["measurement_profile"] = profile()
    ids = [g["sample_id"] for g in d["feedback"]["groups"]]
    for summary in d["summaries"].values():
        summary.update(sample_timing=timing(ids), timing_session_sha256="a" * 64)
    bindings = packet["selection"]["member_bindings"]
    bindings["L-candidate-1"]["bundle_id"] = bindings["L-parent"]["bundle_id"]
    selected = exploratory_selection(CompleteSystemFeedback(canonical(d)), registration={"member_bindings": bindings},
        binding={"next_round": 3, "parent_id": packet["parent_bundle_id"], "complementary_ids": []},
        protocol=protocol, parents=[{"cumulative_sources": []}])
    assert [r["candidate_id"] for r in selected["measurements"]] == ["L-parent", "L-candidate-2"]
    assert [r["candidate_id"] for r in selected["repeated_measurements"]] == ["L-candidate-1"]
    assert selected["same_chain_aa"]["candidate_id"] == "L-parent-aa"


def test_declared_latency_never_silently_falls_back_when_trace_is_missing(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_text_feedback import (
        _row_cost_and_terminal,
    )

    manifest, _ = _cost_fixture(tmp_path)
    with pytest.raises(PolicyError, match="complete roster"):
        _row_cost_and_terminal(manifest, include_sample_timing=True)


@pytest.mark.parametrize("failed", [True, False])
def test_failure_denominator_and_profile_cannot_be_reinterpreted(tmp_path, failed):
    _, _, feedback, evaluation = measured_fixture(tmp_path)
    d = feedback.as_json()
    ids = [g["sample_id"] for g in d["feedback"]["groups"]]
    d["summaries"]["L-candidate-1"]["sample_timing"] = timing(ids, failed=failed)
    rows = measured_rows(
        d,
        ["L-parent", "L-candidate-1"],
        evaluation["member_bindings"],
        profile=profile(),
    )
    assert rows[1]["eligible"] is (not failed)
    other = profile()
    other["minimum_reliable_completion_rate"] = 0.5
    with pytest.raises(PolicyError, match="profile"):
        measured_frontier(rows, profile=other)


def test_official_counts_and_source_timing_join_without_manual_latency(tmp_path):
    import hashlib
    import json
    from speech_aware_evidence_acquisition.rails.system_text_feedback import (
        _official_family_rows,
    )

    bindings, metadata = [], []
    sid = None

    def pin(path):
        return {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    for cid in ("L-parent", "L-parent-aa"):
        folder = tmp_path / cid
        folder.mkdir()

        def add(records, outputs):
            current = outputs[0]["sample_id"]
            record = {
                "schema": "saea-sample-execution-timing-v1",
                "sample_id": current,
                "execution_unit_id": None,
                "admission_index": 0,
                "expected_samples": 1,
                "slot_count": 4,
                "queue_depth": 4,
                "batch_started_ns": 0,
                "admitted_ns": 0,
                "finished_ns": 7000000000,
                "status": "completed",
                "error_type": None,
            }
            records.append(
                {
                    "channel": "USE",
                    "record_id": current + "/native/sample-execution-timing",
                    "payload": {"use_sample_execution_timing": record},
                }
            )

        manifest, sid = _cost_fixture(folder, add)
        manifest["session_receipt"] = {"sha256": "a" * 64}
        score = folder / "score.json"
        score.write_text(
            json.dumps(
                {
                    "scores": {
                        "slurp-slu-official-train": {
                            "aggregate": {
                                "official": {"slu_f1": 0.75},
                                "port_micro": {"intent_accuracy": 1},
                                "identity_check": {"passed": True},
                            }
                        }
                    }
                }
            )
        )
        receipt = folder / "receipt.json"
        receipt.write_text(json.dumps({"job_id": cid, "score_result": pin(score)}))
        bindings.append(
            {
                "candidate_id": cid,
                "config": {
                    "projection": {"scorer": "slurp-slu-official-train"},
                    "complete_score_receipt": pin(receipt),
                },
            }
        )
        metadata.append((manifest, {"job_id": cid}))
    rows, summaries = _official_family_rows(
        bindings,
        metadata,
        {"groups": [{"sample_id": sid}]},
        measurement_profile=profile(),
    )
    assert all(r[sid]["wall_time_seconds"] == 7 for r in rows.values())
    assert all(
        s["sample_timing"]["all_samples"]["mean_seconds"] == 7
        for s in summaries.values()
    )
    assert all(
        s["slu_f1"] == 0.75 and s["reliable_completion_rate"] == 1
        for s in summaries.values()
    )
    metadata[1][0]["session_receipt"]["sha256"] = "b" * 64
    with pytest.raises(PolicyError, match="session"):
        _official_family_rows(
            bindings,
            metadata,
            {"groups": [{"sample_id": sid}]},
            measurement_profile=profile(),
        )


def test_complete_panel_reader_exports_measured_learning_only_after_all_seals(
    tmp_path, monkeypatch
):
    import copy
    from types import SimpleNamespace
    from test_system_text_panel_read import fixture, seal
    from speech_aware_evidence_acquisition.analysis import system_text_pilot as pilot
    from speech_aware_evidence_acquisition.analysis.system_text_panel import (
        read_evidence,
    )

    d, recipe, reg, owner, authority, _, _, growth, protocol, pool, reference = fixture(
        tmp_path, 20
    )
    p = profile()
    protocol["measurement_profile"] = p
    recipe["measurement_profile"] = p
    reg["measurement_profile"] = p
    reg["proposal_protocol_sha256"] = content_hash(protocol)
    seal(reg)
    ids = recipe["sample_ids"]
    bindings = [
        {
            "candidate_id": cid,
            "config": {
                "manifest": {"path": "/synthetic/" + cid},
                "construction_roster": {},
            },
        }
        for cid in reg["expected_members"]
    ]
    import json

    for b in bindings:
        folder = tmp_path / b["candidate_id"]
        (folder / "score-batch").mkdir(parents=True)
        manifest = str(folder / "run.json")
        b["config"]["manifest"]["path"] = manifest
        job = {
            "job_id": b["candidate_id"],
            "manifest": manifest,
            "status": "succeeded",
            "returncode": 0,
            "operation": "finalize",
        }
        (folder / "score-jobs.jsonl").write_text(json.dumps(job) + "\n")
        (folder / "score-batch/batch-summary.json").write_text(
            json.dumps(
                {
                    "job_count": 1,
                    "succeeded": 1,
                    "failed": 0,
                    "include_per_sample": True,
                    "jobs": [job],
                }
            )
        )
    metadata = []
    for b in bindings:
        known = reg["member_bindings"][b["candidate_id"]]
        metadata.append(
            (
                {
                    "run_id": known["run_id"],
                    "config": {"config_hash": known["config_hash"]},
                    "attempt": {"attempt_id": known["attempt_id"]},
                    "split": {"count": 20, "ids": ids},
                },
                {},
            )
        )
    events = []
    monkeypatch.setattr(pilot, "preflight_family", lambda *a: metadata)
    monkeypatch.setattr(
        pilot,
        "_absolute_json",
        lambda *a: {"items": [{"sample_id": sid} for sid in ids]},
    )

    def verify(*a):
        events.append("seal")
        return SimpleNamespace(attempt_state="FINALIZED")

    monkeypatch.setattr(pilot, "verify_bundle", verify)

    def grouped(*a):
        assert events == ["seal"] * 8
        events.append("counts")
        return {"carrier_lock_key": "slurp", **copy.deepcopy(d["feedback"])}

    monkeypatch.setattr(pilot, "build_group_relative_feedback", grouped)

    def official(*a, measurement_profile):
        assert measurement_profile == p and events[-1] == "counts"
        events.append("official-timing")
        summaries = copy.deepcopy(d["summaries"])
        rows = {cid: {} for cid in summaries}
        for g in d["feedback"]["groups"]:
            for m in g["members"]:
                rows[m["candidate_id"]][g["sample_id"]] = m["execution"]
        for summary in summaries.values():
            summary.update(sample_timing=timing(ids), timing_session_sha256="a" * 64)
        return rows, summaries

    monkeypatch.setattr(pilot, "_official_family_rows", official)
    result = read_evidence(
        bindings,
        recipe=recipe,
        registration=reg,
        owner=owner,
        authority=authority,
        growth=growth,
        protocol=protocol,
        pool_ids=pool,
    )
    assert result.as_json()["measurement_profile"] == p
    own = result.learning_projection(amendment=growth, reference=reference).as_json()
    assert own["measurement_profile"] == p
    assert set(own["summaries"]) == {
        "L-parent",
        "L-parent-aa",
        "L-candidate-1",
        "L-candidate-2",
    }
    assert "B-candidate" not in canonical(own)
    assert events == ["seal"] * 8 + ["counts", "official-timing"]
