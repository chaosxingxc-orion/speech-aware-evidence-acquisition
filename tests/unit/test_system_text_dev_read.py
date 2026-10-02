"""Exercise the four-member endpoint gate without opening scientific data."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.system_search_protocol import stage_for
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.core.scoring_receipt import ScoreReceiptError
from test_system_dev_stage import finalists_fixture, freeze_dev
from test_system_text_search_cli import cli, read_fixture


def write(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d) + "\n")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def module():
    path = (
        Path(__file__).resolve().parents[2] / "scripts/analysis/system_text_dev_read.py"
    )
    spec = importlib.util.spec_from_file_location("_test_system_text_dev_read", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def world(tmp_path, module):
    a = finalists_fixture(tmp_path / "archive-fixture")
    registration = freeze_dev(a)
    protocol, data = a[1], a[-1]
    repo = tmp_path / "repo"
    spec, ledger, recipe_path = read_fixture(repo)
    ids = stage_for(protocol, "dev")["sample_ids"]
    roster = {
        "carrier_lock_key": "slurp",
        "split_role": "dev",
        "items": [
            {"sample_id": sid, "utterance_id": sid.rsplit(":", 1)[0]} for sid in ids
        ],
    }
    from speech_aware_evidence_acquisition.data.splits import (
        prefixed,
        split_identity_hash,
    )

    roster["split_identity_hash"] = split_identity_hash(prefixed("slurp", ids))

    def repo_pin(name, d):
        p = write(repo / name, d)
        return {"relpath": name, "sha256": p["sha256"]}

    recipe = {
        "read_run_id": "FIXTURE-READ",
        "family_id": "dev",
        "expected_members": registration["expected_members"],
        "system_search_stage": registration,
        "system_search_evaluation": registration["evaluation"],
        "protocol": repo_pin("protocol.json", protocol),
        "roster": repo_pin("roster.json", roster),
        "attempts": {cid: "attempt-" + cid for cid in registration["expected_members"]},
        "comparisons": module.COMPARISONS,
        "analysis": {
            "cluster_key": "utterance_id",
            "seed": 20261001,
            "draws": 10000,
            "gold_bank": {
                "data_relpath": "offline/dev-bank.jsonl",
                "sha256": "a" * 64,
                "roster": "dev2000-added",
            },
        },
    }
    spec = {
        "family_id": "dev",
        "expected_members": recipe["expected_members"],
        "bindings": {},
        "read_registration": repo_pin(str(recipe_path.relative_to(repo)), recipe),
    }
    ledger.write_text(ledger.read_text().replace("| discovery |", "| dev |"))
    for cid, run in spec["expected_members"].items():
        attempt = recipe["attempts"][cid]
        root = data / "runs" / run / attempt
        state = data / "attempts" / run / (attempt + ".json")
        write(state, {"state": "FINALIZED", "run_id": run, "attempt_id": attempt})
        manifest = {
            "status": "COMPLETED",
            "run_id": run,
            "plan": {"split_role": "dev"},
            "attempt": {"attempt_id": attempt, "state_path": str(state)},
            "config": {
                "config_hash": registration["evaluation"]["member_bindings"][cid][
                    "config_hash"
                ]
            },
            "split": {
                "role": "dev",
                "count": 1000,
                "ids": sorted(ids),
                "carrier_lock_key": "slurp",
                "identity_hash": roster["split_identity_hash"],
            },
            "scorers": ["slurp-slu-official", "cost"],
        }
        pin = write(root / (run + ".run-manifest.json"), manifest)
        write(root / "score-jobs.jsonl", {"job_id": attempt, "manifest": pin["path"]})
        receipt = write(
            root / "saved/receipt.json",
            {
                "status": "complete",
                "job_id": attempt,
                "schema": "saea-complete-score-receipt-v1",
                "operation": "score",
                "include_per_sample": True,
                "manifest": pin,
                "outputs": {},
                "identity": {},
                "scorers": manifest["scorers"],
                "score_result": {},
            },
        )
        batch = write(
            root / "score-batch/batch-summary.json",
            {
                "job_count": 1,
                "succeeded": 1,
                "failed": 0,
                "jobs": [
                    {
                        "job_id": attempt,
                        "manifest": pin["path"],
                        "status": "succeeded",
                        "returncode": 0,
                    }
                ],
            },
        )
        spec["bindings"][cid] = {
            "manifest": pin,
            "complete_score_receipt": {**receipt, "cell_id": attempt},
            "score_batch": batch,
        }
    return SimpleNamespace(
        repo=repo,
        data=data,
        family=spec,
        recipe=recipe,
        ledger=ledger,
        recipe_path=recipe_path,
    )


def repin_recipe(w):
    pin = write(w.recipe_path, w.recipe)
    w.family["read_registration"]["sha256"] = pin["sha256"]


@pytest.mark.parametrize(
    "fault",
    [
        "unsigned",
        "wrong-role",
        "test",
        "missing-aa",
        "missing-member",
        "wrong-config",
        "wrong-cohort",
        "not-finalized",
        "wrong-attempt",
        "duplicate-score",
        "failed-score",
        "incomplete-receipt",
        "recipe-pin",
        "wrong-comparison",
        "wrong-protocol",
        "future-feedback",
    ],
)
def test_every_member_passes_before_any_result_or_seal_read(
    tmp_path, monkeypatch, module, fault
):
    w = world(tmp_path, module)
    b = w.family["bindings"]["B-frozen"]
    path = Path(b["manifest"]["path"])
    m = json.loads(path.read_text())
    if fault == "unsigned":
        w.ledger.write_text(w.ledger.read_text().replace("ROOT COUNTERSIGNED", "DRAFT"))
    elif fault == "wrong-role":
        w.ledger.write_text(w.ledger.read_text().replace("| dev |", "| discovery |"))
    elif fault == "test":
        m["plan"]["split_role"] = "final-report"
    elif fault == "missing-aa":
        w.family["expected_members"] = {
            k: v for k, v in w.family["expected_members"].items() if k != "seed-aa"
        }
    elif fault == "missing-member":
        w.family["bindings"].pop("B-frozen")
    elif fault == "wrong-config":
        m["config"]["config_hash"] = "f" * 64
    elif fault == "wrong-cohort":
        m["split"]["ids"][0] = "slurp:devel:unregistered"
    elif fault == "not-finalized":
        s = Path(m["attempt"]["state_path"])
        d = json.loads(s.read_text())
        d["state"] = "OPENED"
        write(s, d)
    elif fault == "wrong-attempt":
        w.recipe["attempts"]["B-frozen"] = "attempt-other"
        repin_recipe(w)
    elif fault == "duplicate-score":
        p = path.parent / "score-jobs.jsonl"
        p.write_text(p.read_text() * 2)
    elif fault == "failed-score":
        p = Path(b["score_batch"]["path"])
        d = json.loads(p.read_text())
        d["failed"] = 1
        b["score_batch"] = write(p, d)
    elif fault == "incomplete-receipt":
        p = Path(b["complete_score_receipt"]["path"])
        d = json.loads(p.read_text())
        d["status"] = "pending"
        b["complete_score_receipt"].update(write(p, d))
    elif fault == "recipe-pin":
        w.recipe_path.write_text(w.recipe_path.read_text() + " ")
    elif fault == "wrong-comparison":
        w.recipe["comparisons"] = {"primary": ["seed", "L-frozen"]}
        repin_recipe(w)
    elif fault == "wrong-protocol":
        w.recipe["protocol"]["sha256"] = "f" * 64
        repin_recipe(w)
    else:
        w.family["reference_family"] = "test-results.json"
    if m != json.loads(path.read_text()):
        b["manifest"] = write(path, m)
    monkeypatch.setattr(
        module,
        "verify_bundle",
        lambda *a: pytest.fail("seal opened before all metadata passed"),
    )
    monkeypatch.setattr(
        module,
        "verify_complete_score_receipt",
        lambda *a: pytest.fail("score opened before family passed"),
    )
    with pytest.raises((PolicyError, ScoreReceiptError)):
        module.preflight(w.family, repo_root=w.repo, data_root=w.data)


def stub_verifiers(module, monkeypatch, events):
    def seal(path):
        events.append(("seal", str(path)))
        return SimpleNamespace(
            attempt_state="FINALIZED", manifest=json.loads(path.read_text())
        )

    def score(ref, bundle):
        events.append(("score", ref.cell_id))
        return json.loads(ref.path.read_text())

    monkeypatch.setattr(module, "verify_bundle", seal)
    monkeypatch.setattr(module, "verify_complete_score_receipt", score)


def test_full_gate_checks_all_seals_before_scores_and_no_feedback_object(
    tmp_path, monkeypatch, module
):
    w = world(tmp_path, module)
    events = []
    stub_verifiers(module, monkeypatch, events)
    ctx = module.preflight(w.family, repo_root=w.repo, data_root=w.data)
    assert [e[0] for e in events] == ["seal"] * 4 + ["score"] * 4
    assert ctx["authority"]["stage_registration"]["stage"] == "dev"
    with pytest.raises(PolicyError):
        cli.require_read_registration(w.family, repo_root=w.repo)
    from speech_aware_evidence_acquisition.rails.system_text_feedback import (
        CompleteSystemFeedback,
    )

    with pytest.raises(PolicyError):
        CompleteSystemFeedback.from_family(
            [
                {"candidate_id": cid, "config": {"manifest": b["manifest"]}}
                for cid, b in w.family["bindings"].items()
            ],
            expected_members=w.family["expected_members"],
            family_id="dev",
        )


def test_bad_seal_stops_before_any_score(tmp_path, monkeypatch, module):
    w = world(tmp_path, module)
    monkeypatch.setattr(
        module, "verify_bundle", lambda p: SimpleNamespace(attempt_state="OPENED")
    )
    monkeypatch.setattr(
        module, "verify_complete_score_receipt", lambda *a: pytest.fail("score read")
    )
    with pytest.raises(PolicyError, match="seal"):
        module.preflight(w.family, repo_root=w.repo, data_root=w.data)


def test_report_uses_shared_pairs_and_keeps_missing_cost_unknown(
    tmp_path, monkeypatch, module
):
    w = world(tmp_path, module)
    events = []
    stub_verifiers(module, monkeypatch, events)
    pairs = []

    def run_pair(args, ext):
        pairs.append((args.left.label, args.right.label))
        assert (
            args.expected_split_role == "dev" and args.scorer_id == "slurp-slu-official"
        )
        assert ext.per_scenario and ext.frontier and not ext.delivery
        assert ext.strata_source == "gold-bank" and ext.gold_bank_sha256 == "a" * 64
        write(args.analysis_root / "verdict.json", {"status": "DESCRIPTIVE"})
        write(args.analysis_root / "per-scenario-tables.json", {"status": "AVAILABLE", "strata_rows": {"synthetic": 1000}})
        write(args.analysis_root / "frontier.json", {side: {"official_slu_pct": 60, "official_intent_pct": 80} for side in ("left", "right")})
        return {"status": "DESCRIPTIVE"}

    monkeypatch.setattr(module.PAIRED, "run_pair", run_pair)
    ids = stage_for(json.loads((w.repo / "protocol.json").read_text()), "dev")[
        "sample_ids"
    ]
    monkeypatch.setattr(
        module,
        "_row_cost_and_terminal",
        lambda m: {
            sid: {
                "model_calls": 4,
                "tool_calls": 0,
                "prompt_tokens": None,
                "completion_tokens": 20,
                "missing_model_responses": 1,
                "role_contacts": {"solver": 2},
                "tool_events": {"attempt": 0},
                "reliable_completion": True,
                "abstained": False,
            }
            for sid in ids
        },
    )
    out = w.data / "analysis/endpoint"
    result = module.run(w.family, repo_root=w.repo, data_root=w.data, output=out)
    assert pairs == list(map(tuple, module.COMPARISONS.values()))
    assert result["status"] == "DESCRIPTIVE_ROOT_INTERPRETATION_REQUIRED"
    assert (
        result["optimizer_feedback_allowed"] is False
        and result["scorer_contacts_added"] == 0
    )
    assert result["execution"]["seed"]["prompt_tokens"] is None
    assert result["execution"]["seed"]["completion_tokens"] == 20000
    assert (out / "report.json").is_file()
    with pytest.raises(PolicyError, match="exists"):
        module.run(w.family, repo_root=w.repo, data_root=w.data, output=out)


def test_changed_authority_during_read_does_not_publish_report(
    tmp_path, monkeypatch, module
):
    w = world(tmp_path, module)
    events = []
    stub_verifiers(module, monkeypatch, events)

    def change(*args):
        w.ledger.write_text(w.ledger.read_text().replace("ROOT COUNTERSIGNED", "DRAFT"))
        return {}

    monkeypatch.setattr(module, "_row_cost_and_terminal", change)
    out = w.data / "analysis/endpoint"
    with pytest.raises(PolicyError):
        module.run(w.family, repo_root=w.repo, data_root=w.data, output=out)
    assert not (out / "report.json").exists()


def test_report_cannot_write_into_optimizer_archive(tmp_path, monkeypatch, module):
    monkeypatch.setattr(
        module,
        "preflight",
        lambda *a, **k: pytest.fail("read before output confinement"),
    )
    with pytest.raises(PolicyError, match="analysis"):
        module.run(
            {},
            repo_root=tmp_path,
            data_root=tmp_path,
            output=tmp_path / "system-text-search/feedback",
        )


def test_endpoint_frontier_preserves_replicates_and_balanced_points():
    from speech_aware_evidence_acquisition.rails.system_search_archive import pareto_frontier
    points = [{"member": name, "bundle_id": bundle, "cohort_id": "dev", "slu_f1": quality,
               "intent": .8, "model_calls": cost, "tool_calls": 0}
              for name, bundle, quality, cost in [("seed", "same", .7, 10), ("aa", "same", .7, 10),
                 ("balanced", "other", .8, 20), ("quality", "last", .9, 40), ("bad", "bad", .7, 30)]]
    assert {r["member"] for r in pareto_frontier(points, identity_key="member")} == {"seed", "aa", "balanced", "quality"}
    with pytest.raises(PolicyError, match="duplicate"):
        pareto_frontier(points)


def test_endpoint_runs_real_standard_paired_driver_on_synthetic_complete_roster(
    tmp_path, monkeypatch, module
):
    from test_stage3_paired_read import World, _score_row, _sha, _write

    w = world(tmp_path, module)
    events = []
    stub_verifiers(module, monkeypatch, events)
    ids = stage_for(json.loads((w.repo / "protocol.json").read_text()), "dev")[
        "sample_ids"
    ]
    synth = World(
        tmp_path / "pair-fixture",
        ids=ids,
        split_role="dev",
        stratum=False,
        bank_roster="dev2000-added",
        roster_id="SLURP-DEV-2000-ADDED-V1",
    )
    bank = synth.data / module.PAIRED.DEFAULT_BANK
    bank_dest = w.data / w.recipe["analysis"]["gold_bank"]["data_relpath"]
    bank_dest.parent.mkdir(parents=True)
    bank_dest.write_text("\n".join(json.dumps({**json.loads(line), "stratum": json.loads(line)["gold_intent"].split("_", 1)[0]}) for line in bank.read_text().splitlines()) + "\n")
    w.recipe["analysis"]["gold_bank"]["sha256"] = _sha(bank_dest)
    w.recipe["analysis"]["draws"] = 30
    roster_path = w.repo / w.recipe["roster"]["relpath"]
    roster = json.loads(roster_path.read_text())
    roster.update(roster_id="SLURP-DEV-2000-ADDED-V1", stratum_withheld_per_item=True)
    w.recipe["roster"]["sha256"] = write(roster_path, roster)["sha256"]
    repin_recipe(w)
    core = module.PAIRED.CORE
    for j, (cid, binding) in enumerate(w.family["bindings"].items()):
        run = w.family["expected_members"][cid]
        path = Path(binding["manifest"]["path"])
        root = path.parent
        manifest = json.loads(path.read_text())
        rows = [_score_row(sid, i % (j + 2) == 0) for i, sid in enumerate(ids)]
        table = {r["sample_id"]: r for r in rows}
        scores = {
            "slurp-slu-official": {
                "per_sample": rows,
                "aggregate": {
                    "official": {
                        "slu_f1": core.pooled_f1(
                            table, ids, core.MICRO_METRICS["slu_f1_micro"]
                        ),
                        "span_f1": core.pooled_f1(
                            table, ids, core.MICRO_METRICS["span_f1_micro"]
                        ),
                        "intent_accuracy": sum(r["scenario_action_exact"] for r in rows)
                        / len(rows),
                    }
                },
            }
        }
        manifest["scores"] = write(root / f"{run}.scores.json", scores)
        manifest["study_repo_dirt"] = []
        binding["manifest"] = write(path, manifest)
        receipt_path = Path(binding["complete_score_receipt"]["path"])
        receipt = json.loads(receipt_path.read_text())
        receipt["manifest"] = binding["manifest"]
        binding["complete_score_receipt"].update(write(receipt_path, receipt))
        _write(
            root / f"{run}.outputs.jsonl",
            "\n".join(
                json.dumps(
                    {
                        "sample_id": sid,
                        "admitted": True,
                        "text": "SYNTHETIC-SECRET-ANSWER",
                        "response_text_sha256": "0" * 64,
                    }
                )
                for sid in ids
            ),
        )
        write(
            root / f"{run}.generation-manifest.json",
            {
                "cost": {
                    "calls_used": 4000,
                    "prompt_tokens_total": 100000,
                    "completion_tokens_total": 10000,
                    "tool_calls": 0,
                    "audio_seconds_used": 1000,
                }
            },
        )
        write(
            root / "flight-receipts.json",
            {
                "stages": {
                    "seal": {
                        "serving_monitor_summary": {
                            "active_seconds": 100,
                            "wall_seconds": 120,
                        }
                    }
                }
            },
        )
        _write(root / f"{run}.trace.jsonl", "")
    monkeypatch.setattr(
        module,
        "_row_cost_and_terminal",
        lambda m: {
            sid: {
                "model_calls": 4,
                "tool_calls": 0,
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "missing_model_responses": 0,
                "role_contacts": {"solver": 2, "reviewer": 1, "planner": 1},
                "tool_events": {"attempt": 0},
                "reliable_completion": True,
                "abstained": False,
            }
            for sid in ids
        },
    )
    family_path = tmp_path / "family.json"
    write(family_path, w.family)
    out = w.data / "analysis/synthetic-endpoint"
    module.main(
        [
            "--family",
            str(family_path),
            "--repo-root",
            str(w.repo),
            "--data-root",
            str(w.data),
            "--output",
            str(out),
        ]
    )
    report = json.loads((out / "report.json").read_text())
    assert len(report["comparisons"]) == 5
    for name in module.COMPARISONS:
        strata = json.loads((out / name / "per-scenario-tables.json").read_text())
        assert (
            strata["status"] == "AVAILABLE"
            and "equal_scenario" in strata
            and "natural_mixture" in strata
        )
    assert all(
        "SYNTHETIC-SECRET-ANSWER" not in p.read_text()
        for p in out.rglob("*")
        if p.is_file()
    )
