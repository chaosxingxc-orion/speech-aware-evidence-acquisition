"""Whole-family update statistics keep registered counts, nulls and custody."""

import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.system_text_update import analyze_update
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)
from test_system_search_selection import selection_fixture
from speech_aware_evidence_acquisition.rails.system_search_protocol import stage_for


def fixture(tmp_path, stage_name="update-1"):
    _, protocol, feedback, evaluation = selection_fixture(
        tmp_path, stage_name=stage_name
    )
    d = feedback.as_json()
    metadata = {}
    for i, group in enumerate(d["feedback"]["groups"]):
        sid = group["sample_id"]
        metadata[sid] = {
            "sample_id": sid,
            "utterance_id": str(i // 2),
            "stratum": "a" if i < 300 else "b",
        }
        for member in group["members"]:
            cid = member["candidate_id"]
            # Different entity volumes make mean per-row F1 the wrong endpoint.
            tp, fp, fn = (9, 1, 1) if i < 300 else (0, 1, 1)
            if cid.endswith("candidate-1"):
                tp, fp, fn = (10, 0, 0) if i < 300 else (0, 1, 1)
            member["native_counts"] = {
                f"slu_f1_{axis}_{kind}": value
                for axis in ("word", "char")
                for kind, value in zip(("tp", "fp", "fn"), (tp, fp, fn))
            }
            member["native_counts"]["scenario_action_exact"] = int(i % 5 != 0)
            member["execution"] = {
                "model_calls": 6,
                "tool_calls": 0,
                "prompt_tokens": 100,
                "completion_tokens": None if i == 0 else 5,
                "delivery_kind": "accepted",
                "reliable_completion": True,
                "abstained": False,
                "role_contacts": {"solver": 2, "reviewer": 2, "planner": 2},
                "tool_events": {"attempt": 0, "result": 0},
            }
    for cid, summary in d["summaries"].items():
        summary.update(
            slu_f1=(6000 / 6200 if cid.endswith("candidate-1") else 5400 / 6200),
            intent=0.8,
            model_calls=2400,
            tool_calls=0,
        )
    recipe = {
        "family_id": stage_name,
        "expected_members": {
            cid: b["run_id"] for cid, b in evaluation["member_bindings"].items()
        },
        "system_search_evaluation": evaluation,
        "resampling": {
            "bootstrap_draws": 20,
            "confidence": 0.95,
            "seed": 20261001,
            "unit": "paired utterance; keep all recording variants together",
        },
    }
    return protocol, CompleteSystemFeedback(canonical(d)), recipe, metadata


def test_report_uses_pooled_counts_own_null_all_rows_and_unknown_cost(tmp_path):
    protocol, feedback, recipe, metadata = fixture(tmp_path)
    report = analyze_update(feedback, protocol=protocol, recipe=recipe, roster=metadata)
    assert report["status"] == "DESCRIPTIVE-ROOT-REVIEW-REQUIRED"
    assert report["sample_count"] == 400 and report["cluster_count"] == 200
    assert report["official_summaries"]["L-parent"]["slu_f1"] == pytest.approx(
        5400 / 6200
    )
    assert report["equal_stratum_macro"]["L-parent"]["slu_f1"] == pytest.approx(0.45)
    assert report["execution"]["L-parent"]["completion_tokens"] is None
    assert report["execution"]["L-parent"]["prompt_tokens"] == 40000
    assert report["execution"]["L-parent"]["wall_time_seconds"] is None
    assert report["execution"]["L-parent"]["role_contacts"]["solver"] == 800
    assert set(report["branches"]) == {"L", "B"}
    for branch, result in report["branches"].items():
        null = result["comparisons"]["same-request-null"]
        assert (
            null["left"] == branch + "-parent"
            and null["right"] == branch + "-parent-aa"
        )
        assert null["intent"]["ci_low"] == null["intent"]["ci_high"] == 0
        assert result["own_null_half_width"]["intent"] == 0
        assert len(result["measurements"]) == 4
        assert all(
            row["candidate_id"].startswith(branch + "-") for row in result["frontier"]
        )
        assert set(result["comparisons"]) == {
            "same-request-null",
            "candidate-1-minus-parent",
            "candidate-1-minus-aa",
            "candidate-2-minus-parent",
            "candidate-2-minus-aa",
        }
    assert "active_ids" not in report and "guard_passed" not in canonical(report)


@pytest.mark.parametrize(
    "fault",
    [
        "unread",
        "family",
        "protocol",
        "roster",
        "duplicate",
        "member",
        "summary",
        "negative",
        "intent",
        "count-cost",
        "aa",
        "source",
        "resampling",
    ],
)
def test_invalid_or_unregistered_analysis_is_refused(tmp_path, fault):
    protocol, feedback, recipe, metadata = fixture(tmp_path)
    d = feedback.as_json()
    if fault == "unread":
        d.pop("read_authority")
    elif fault == "family":
        d["family_id"] = "dev"
    elif fault == "protocol":
        recipe["system_search_evaluation"]["protocol_sha256"] = "f" * 64
    elif fault == "roster":
        metadata.pop(next(iter(metadata)))
    elif fault == "duplicate":
        d["feedback"]["groups"].append(d["feedback"]["groups"][0])
    elif fault == "member":
        d["feedback"]["groups"][0]["members"].pop()
    elif fault == "summary":
        d["summaries"]["L-parent"]["slu_f1"] = 0.1
    elif fault == "negative":
        d["feedback"]["groups"][0]["members"][0]["native_counts"]["slu_f1_word_tp"] = -1
    elif fault == "intent":
        d["feedback"]["groups"][0]["members"][0]["native_counts"][
            "scenario_action_exact"
        ] = 0.5
    elif fault == "count-cost":
        d["feedback"]["groups"][0]["members"][0]["execution"]["model_calls"] = 5
    elif fault == "aa":
        recipe["system_search_evaluation"]["member_bindings"]["L-parent-aa"][
            "bundle_id"
        ] = "f" * 64
    elif fault == "source":
        d["feedback"]["sources"][0]["config_hash"] = "f" * 64
    elif fault == "resampling":
        recipe["resampling"]["unit"] = "independent recording"
    with pytest.raises((PolicyError, ValueError)):
        analyze_update(
            CompleteSystemFeedback(canonical(d)),
            protocol=protocol,
            recipe=recipe,
            roster=metadata,
        )


def test_no_candidates_keeps_null_and_every_parent_replicate(tmp_path):
    protocol, feedback, recipe, metadata = fixture(tmp_path)
    # Bind an admitted stage with no generated candidate; no post-contact exclusion.
    d = feedback.as_json()
    keep = {cid for cid in d["summaries"] if "parent" in cid}
    d["summaries"] = {k: v for k, v in d["summaries"].items() if k in keep}
    d["feedback"]["sources"] = [
        r for r in d["feedback"]["sources"] if r["candidate_id"] in keep
    ]
    for g in d["feedback"]["groups"]:
        g["members"] = [m for m in g["members"] if m["candidate_id"] in keep]
    stage_for(protocol, "update-1")["member_slots"] = sorted(keep)
    recipe["expected_members"] = {
        k: v for k, v in recipe["expected_members"].items() if k in keep
    }
    evaluation = recipe["system_search_evaluation"]
    evaluation["member_bindings"] = {
        k: v for k, v in evaluation["member_bindings"].items() if k in keep
    }
    evaluation["protocol_sha256"] = content_hash(protocol)
    report = analyze_update(
        CompleteSystemFeedback(canonical(d)),
        protocol=protocol,
        recipe=recipe,
        roster=metadata,
    )
    assert all(
        list(b["comparisons"]) == ["same-request-null"]
        for b in report["branches"].values()
    )


ROOT = Path(__file__).resolve().parents[2]


def reader():
    spec = importlib.util.spec_from_file_location(
        "system_update_read_fixture",
        ROOT / "scripts/analysis/system_text_update_read.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def operator_fixture(tmp_path, monkeypatch):
    protocol, feedback, recipe, metadata = fixture(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()

    def write_pin(name, document):
        p = repo / name
        p.write_text(json.dumps(document))
        import hashlib

        return {"relpath": name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}

    source = stage_for(protocol, "update-1")["source_roster"]
    protocol["source_rosters"] = {
        source: write_pin("roster.json", {"items": list(metadata.values())})
    }
    recipe["system_search_evaluation"]["protocol_sha256"] = content_hash(protocol)
    pin = write_pin("recipe.json", recipe)
    write_pin("protocol.json", protocol)
    family = {"read_registration": pin}
    family_path = tmp_path / "family.json"
    family_path.write_text(json.dumps(family))
    d = feedback.as_json()
    d["read_authority"]["recipe"] = pin
    feedback = CompleteSystemFeedback(canonical(d))
    module = reader()
    calls = []

    def read_family(path, *, repo_root):
        assert Path(path) == family_path and repo_root == repo
        calls.append("fresh-complete-family")
        return feedback

    monkeypatch.setattr(module.CLI, "read_family", read_family)
    monkeypatch.setattr(
        module.CLI, "require_read_registration", lambda *a, **k: d["read_authority"]
    )
    return module, repo, family_path, tmp_path / "data", calls


def test_operator_freshly_gates_before_statistics_and_never_writes_archive(
    tmp_path, monkeypatch
):
    module, repo, family, data, calls = operator_fixture(tmp_path, monkeypatch)
    output = data / "analysis/update1"
    report = module.run(
        family,
        protocol_path=repo / "protocol.json",
        repo_root=repo,
        data_root=data,
        output=output,
    )
    assert calls == ["fresh-complete-family"]
    assert (output / "report.json").is_file() and (output / "README.md").is_file()
    assert "DESCRIPTIVE" in (output / "README.md").read_text()
    assert report["source_pins"]["roster"]["relpath"] == "roster.json"
    assert not (data / "system-text-search").exists()
    with pytest.raises(PolicyError, match="exists"):
        module.run(
            family,
            protocol_path=repo / "protocol.json",
            repo_root=repo,
            data_root=data,
            output=output,
        )


@pytest.mark.parametrize(
    "fault",
    ["unsigned", "bad-roster-hash", "authority-change", "outside", "protocol-change"],
)
def test_operator_refuses_before_publishing_on_read_or_source_failure(
    tmp_path, monkeypatch, fault
):
    module, repo, family, data, calls = operator_fixture(tmp_path, monkeypatch)
    output = data / "analysis/update1"
    if fault == "unsigned":

        def reject(*a, **k):
            raise PolicyError("unsigned READ")

        monkeypatch.setattr(module.CLI, "read_family", reject)
        monkeypatch.setattr(
            module,
            "analyze_update",
            lambda *a, **k: pytest.fail("analysis must not run"),
        )
    elif fault == "bad-roster-hash":
        (repo / "roster.json").write_text("{}")
    elif fault == "authority-change":
        monkeypatch.setattr(module.CLI, "require_read_registration", lambda *a, **k: {})
    elif fault == "outside":
        output = data / "system-text-search/update1"
    elif fault == "protocol-change":
        p = repo / "protocol.json"
        d = json.loads(p.read_text())
        d["seed"] = 0
        p.write_text(json.dumps(d))
    with pytest.raises(PolicyError):
        module.run(
            family,
            protocol_path=repo / "protocol.json",
            repo_root=repo,
            data_root=data,
            output=output,
        )
    assert not output.exists()


def test_zero_entity_counts_and_absent_cost_breakdowns_are_explicit(tmp_path):
    protocol, feedback, recipe, metadata = fixture(tmp_path)
    d = feedback.as_json()
    for group in d["feedback"]["groups"]:
        for member in group["members"]:
            for key in member["native_counts"]:
                if key.startswith("slu_f1_"):
                    member["native_counts"][key] = 0
            member["execution"].pop("role_contacts")
            member["execution"].pop("tool_events")
            member["execution"]["wall_time_seconds"] = 0.5
    for summary in d["summaries"].values():
        summary["slu_f1"] = 0
    report = analyze_update(
        CompleteSystemFeedback(canonical(d)),
        protocol=protocol,
        recipe=recipe,
        roster=metadata,
    )
    assert report["execution"]["L-parent"]["wall_time_seconds"] == 200
    assert report["execution"]["L-parent"]["role_contacts"] is None
    assert (
        report["branches"]["L"]["comparisons"]["same-request-null"]["slu_f1"][
            "point_estimate"
        ]
        == 0
    )


def test_cli_routes_only_to_the_gated_operator(tmp_path, monkeypatch, capsys):
    module = reader()
    calls = []

    def run(family, **kwargs):
        calls.append((family, kwargs))
        return {"family_id": "update-2", "status": "DESCRIPTIVE"}

    monkeypatch.setattr(module, "run", run)
    module.main(
        [
            "--family",
            str(tmp_path / "family"),
            "--protocol",
            str(tmp_path / "protocol"),
            "--data-root",
            str(tmp_path / "data"),
            "--output",
            str(tmp_path / "data/analysis/out"),
        ]
    )
    assert calls[0][0] == tmp_path / "family"
    assert '"family_id": "update-2"' in capsys.readouterr().out


@pytest.mark.parametrize("stage_name", ["update-2", "update-3"])
def test_later_updates_keep_their_own_cohort_and_same_analysis(tmp_path, stage_name):
    protocol, feedback, recipe, metadata = fixture(tmp_path, stage_name)
    report = analyze_update(feedback, protocol=protocol, recipe=recipe, roster=metadata)
    assert report["family_id"] == stage_name
    assert report["branches"]["L"]["measurements"][0]["cohort_id"] == content_hash(
        stage_for(protocol, stage_name)["sample_ids"]
    )
    assert report["feedback_sha256"] == content_hash(feedback.as_json())
