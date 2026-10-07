"""Synthetic complete-family orchestration; no actual task data or contacts."""

import copy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import socket

import pytest
from test_slurp_solver_stage_attribution import _source, _reference, _saved_row, _answer
from speech_aware_evidence_acquisition.analysis import (
    slurp_topn_diagnostics_cli as references,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "process_producer_test",
    ROOT / "scripts/analysis/manual_architecture_process_derivative.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(tmp_path, monkeypatch):
    data = tmp_path / "data"
    coord = data / "coordination"
    repo = tmp_path / "repo"
    coord.mkdir(parents=True)
    repo.mkdir()

    def save(path, value):
        path.write_text(json.dumps(value))
        return m.pin(path)

    def relative(path, value):
        p = save(path, value)
        return {"relpath": path.relative_to(repo).as_posix(), "sha256": p["sha256"]}

    ids = ["slurp:devel:first", "slurp:devel:second"]
    runtime = ids[::-1]
    labels = ["seed", "seed-aa", "review-off", "solver-lookup"]
    cfg = {label: content_hash(label) for label in labels}
    run_ids = {label: "run-" + label for label in labels}
    scope = {
        "labels": labels,
        "runtime_sample_ids": {label: runtime for label in labels},
        "review_applicability": {
            label: {
                "schema": "saea-review-applicability-v1",
                "config_sha256": cfg[label],
                "review_loop": "off" if label == "review-off" else "on",
            }
            for label in labels
        },
    }
    recipe = {
        "manual_architecture_registration": {},
        "family_id": "synthetic-family",
        "expected_members": run_ids,
        "sample_ids": ids,
        "run_ids": {"read": "ROOT-READ"},
        "analysis_roster": relative(repo / "roster.json", {"sample_ids": ids}),
        "measurement_profile": {"slot_count": 2, "queue_depth": 2},
    }
    recipe_pin = relative(repo / "recipe.json", recipe)
    supplement = {
        "projection": {"scorer": "slurp-slu-official-train"},
        "fixed": "unchanged",
    }
    supplement_pin = relative(repo / "supplement.json", supplement)
    authority = {
        "read_run_id": "ROOT-READ",
        "recipe": recipe_pin,
        "ledger_row_sha256": "a" * 64,
    }
    fixed = {
        "schema": "saea-manual-family-prospective-root-diagnostic-scope-v1",
        "status": "SCOPE_FIXED_BEFORE_QUALITY_READ_EXECUTION_AFTER_FULL_FAMILY_READ",
        "learner_export": False,
        "runtime_gold": False,
        "recipe": recipe_pin,
        "supplement": supplement_pin,
        "source_modules": {},
    }
    scope_abs = save(coord / "scope.json", fixed)
    scope_pin = {"relpath": "coordination/scope.json", "sha256": scope_abs["sha256"]}
    qualification = save(coord / "qualified.json", {"status": "QUALIFIED"})
    root_read = {
        "schema": "saea-manual-family-root-read-authority-v1",
        "status": "ROOT_COUNTERSIGNED_COMPLETE_FAMILY",
        "authority": authority,
        "recipe": recipe_pin,
        "supplement": supplement_pin,
        "diagnostic_scope": scope_pin,
        "qualification": {
            "relpath": "coordination/qualified.json",
            "sha256": qualification["sha256"],
        },
    }
    root_pin = save(coord / "authority.json", root_read)
    lock = save(repo / "lock.json", {})
    reference_binding = {
        "kind": "slurp-split",
        "split_id": "devel",
        "split_identity_hash": split_identity_hash(prefixed("slurp", runtime)),
        "lock": lock,
        "data_root": str(data),
        "allow_heldout": False,
        "allow_synthetic": False,
    }
    inputs = {
        "schema": "saea-manual-process-operational-inputs-v1",
        "optimizer_export": False,
        "contacts": 0,
        "quality_values_parsed": False,
        "reference_records_loaded": False,
        "frozen_worker_root": str(repo),
        "frozen_worker_commit": "f" * 40,
        "root_diagnostic_scope": scope_abs,
        "family_qualification": qualification,
        "read_authority": authority,
        "reference_binding": reference_binding,
        "members": {},
    }
    registration = {"member_bindings": {}}
    originals, metadata, saved_bindings, sources, receipts = [], [], [], {}, {}
    correct = _answer("weather", "query", ("city", "paris"))
    wrong = _answer("calendar", "remove", ("date", "tomorrow"))
    for label in labels:
        answers = {
            sid: ([correct] if label == "review-off" else [wrong, correct])
            for sid in runtime
        }
        source = _source(answers)
        loop = scope["review_applicability"][label]["review_loop"]
        source = replace(
            source,
            composed=SimpleNamespace(
                config_hash=cfg[label],
                values={
                    "policy": "native-test",
                    "native_episode": {
                        "review_loop": loop,
                        "roles": {
                            "reviewer": {"max_iterations": int(loop == "on")},
                            "planner": {"max_iterations": int(loop == "on")},
                        },
                        "max_revisions": int(loop == "on"),
                    },
                },
            ),
            plan=SimpleNamespace(
                **{
                    **vars(source.plan),
                    "run_id": run_ids[label],
                    "attempt_id": "attempt-" + label,
                }
            ),
        )
        sources[label] = source
        scores = {
            "slurp-slu-official-train": {
                "per_sample": [_saved_row(_reference(sid), correct) for sid in runtime]
            }
        }
        score = save(coord / (label + "-scores.json"), scores)
        manifest_value = {
            "study_commit": "f" * 40,
            "config": {"config_hash": cfg[label]},
            "attempt": {"attempt_id": "attempt-" + label},
            "scores": score,
            "split": {"count": len(ids), "ids": ids},
        }
        manifest = save(coord / (label + "-manifest.json"), manifest_value)
        phase = save(coord / (label + "-phase.json"), {"synthetic": True})
        inputs["members"][label] = {
            "run_id": run_ids[label],
            "attempt_id": "attempt-" + label,
            "config_hash": cfg[label],
            "runtime_sample_ids": runtime,
            "manifest": manifest,
            "phase_artifact": phase,
            "original_score_result": score,
        }
        registration["member_bindings"][label] = {
            "run_id": run_ids[label],
            "attempt_id": "attempt-" + label,
            "config_hash": cfg[label],
            "source_commit": "f" * 40,
        }
        originals.append({"candidate_id": label, "config": {"manifest": manifest}})
        metadata.append((manifest_value, {}))
        envelope = save(
            coord / (label + "-reused.json"),
            {"manifest": manifest["path"], "verified": True, "scores": scores},
        )
        receipt = save(coord / (label + "-receipt.json"), {"score_result": envelope})
        receipts[receipt["path"]] = {"score_result": envelope}
        saved_bindings.append(
            {
                "candidate_id": label,
                "config": {
                    "manifest": manifest,
                    "complete_score_receipt": {"cell_id": label, **receipt},
                },
            }
        )
    input_abs = save(coord / "inputs.json", inputs)
    input_pin = {"relpath": "coordination/inputs.json", "sha256": input_abs["sha256"]}
    implementation = {"synthetic-reviewed-source": "exact"}
    execution = {
        "schema": "saea-root-manual-process-execution-v1",
        "operational_inputs": input_pin,
        "root_read_authority": root_pin,
        "diagnostic_scope": scope_pin,
        "implementation": implementation,
        "runtime_gold": False,
        "learner_export": False,
    }
    exec_pin = save(coord / "execution.json", execution)
    family_pin = save(
        coord / "family.json",
        {
            "family_id": recipe["family_id"],
            "expected_members": run_ids,
            "read_registration": recipe_pin,
            "bindings": saved_bindings,
        },
    )
    business = {
        "family_id": recipe["family_id"],
        "read_authority": authority,
        "learner_export": False,
        "official_summaries": {
            label: {
                "slu_f1": 1.0,
                "intent": 1.0,
                "reliable_completion_rate": 1.0,
                "model_calls": 2,
                "tool_calls": 0,
            }
            for label in labels
        },
        "branches": {"architecture": {"aa": "preserved"}},
        "per_stratum": {"weather": "preserved"},
        "equal_stratum_macro": {"value": "preserved"},
        "execution": {"complete": True},
    }
    business_pin = save(coord / "business.json", business)
    events = []
    monkeypatch.setattr(m, "implementation_pins", lambda: implementation)
    monkeypatch.setattr(
        m.reader, "load_documents", lambda *a: (recipe, registration, {}, supplement)
    )
    monkeypatch.setattr(
        m.reader.CLI, "require_read_registration", lambda *a, **k: authority
    )
    monkeypatch.setattr(m.architecture, "validate_registration", lambda *a, **k: scope)
    monkeypatch.setattr(m.reader, "source_bindings", lambda *a: (originals, []))
    monkeypatch.setattr(m, "preflight_family", lambda *a: metadata)

    def verify(**kw):
        label = next(
            label
            for label in labels
            if inputs["members"][label]["manifest"]["path"] == str(kw["manifest_path"])
        )
        events.append(("native", label))
        return sources[label]

    monkeypatch.setattr(m, "verify_native_episode_source", verify)
    monkeypatch.setattr(
        m, "verify_complete_score_receipt", lambda ref, bundle: receipts[str(ref.path)]
    )
    monkeypatch.setattr(m, "load_lock", lambda *a: {})
    monkeypatch.setattr(references, "load_lock", lambda *a: {})
    monkeypatch.setattr(
        m,
        "load_slurp_ontology",
        lambda *a: SimpleNamespace(
            entity_types={"city": ()}, intents=("weather_query",)
        ),
    )
    records = [_reference(sid) for sid in ids]

    def loader(*a, **kw):
        assert events[: len(labels)] == [("native", label) for label in labels]
        events.append(("reference", None))
        return records

    monkeypatch.setattr(m, "load_slurp_split", loader)

    def clock(source):
        samples = [
            {"sample_id": sid, "elapsed_seconds": float(i + 2)}
            for i, sid in enumerate(source.sample_ids)
        ]
        return {
            "available": True,
            "samples": samples,
            "first_admitted_sample": samples[0],
            "all_samples": {"mean_seconds": 2.5},
            "excluding_first": {"mean_seconds": 3.0},
            "completed_samples": len(ids),
            "failed_samples": 0,
            "slot_count": 2,
            "queue_depth": 2,
            "timing_scope": "synthetic",
            "cold_start_limit": "no warm claim",
        }

    monkeypatch.setattr(m, "export_system_sample_timing", clock)
    monkeypatch.setattr(
        m,
        "export_system_node_timing",
        lambda source: {"by_role": {"solver": {"contacts": 2}}},
    )
    args = {
        "bindings_pin": input_pin,
        "execution_pin": exec_pin,
        "business_report_pin": business_pin,
        "business_family_pin": family_pin,
        "repo_root": repo,
        "data_root": data,
        "output": data / "analysis" / "derivative",
    }
    return SimpleNamespace(
        inputs=inputs,
        args=args,
        save=save,
        events=events,
        sources=sources,
        records=records,
        scope=scope,
        recipe=recipe,
        root_read=root_read,
        execution=execution,
        business=business,
        receipts=receipts,
        metadata=metadata,
    )


def repin(f):
    p = Path(f.args["data_root"]) / f.args["bindings_pin"]["relpath"]
    f.args["bindings_pin"]["sha256"] = f.save(p, f.inputs)["sha256"]
    f.execution["operational_inputs"] = f.args["bindings_pin"]
    f.args["execution_pin"] = f.save(Path(f.args["execution_pin"]["path"]), f.execution)


def test_complete_offline_derivative_reuses_real_metrics_combiner_renderer(
    tmp_path, monkeypatch
):
    f = fixture(tmp_path, monkeypatch)
    result = m.run(f.inputs, **f.args)
    out = f.args["output"]
    process = json.loads((out / "process-v2.json").read_text())
    combined = json.loads((out / "comparison-v2.json").read_text())
    assert result["model_contacts"] == result["scorer_contacts"] == 0
    assert combined["business"]["paired_comparisons"] == f.business["branches"]
    assert combined["business"]["per_stratum"] == f.business["per_stratum"]
    assert (
        process["members"]["review-off"]["metrics"]["review_valid"]["applicability"]
        == "not-applicable-by-design"
    )
    assert process["members"]["seed"]["recall_status"]
    assert (
        process["timing"]["seed"]["first_admitted_sample"]["sample_id"]
        == f.scope["runtime_sample_ids"]["seed"][0]
    )
    assert combined["resources"]["seed"]["non_first_mean_seconds"] == 3.0
    assert "Raw retrieval pool" in (out / "report.md").read_text()
    assert m.read_absolute(f.args["business_report_pin"]) == f.business
    assert not combined["adoption_decided"] and not combined["learner_exported"]


@pytest.mark.parametrize(
    "defect",
    [
        "missing-member",
        "wrong-order",
        "wrong-source",
        "wrong-score-pin",
        "export",
        "gold",
    ],
)
def test_metadata_refuses_before_native_or_reference_content(
    tmp_path, monkeypatch, defect
):
    f = fixture(tmp_path, monkeypatch)
    if defect == "missing-member":
        f.inputs["members"].pop("solver-lookup")
    if defect == "wrong-order":
        f.inputs["members"]["seed"]["runtime_sample_ids"] = f.recipe["sample_ids"]
    if defect == "wrong-source":
        f.inputs["frozen_worker_commit"] = "d" * 40
    if defect == "wrong-score-pin":
        f.inputs["members"]["seed"]["original_score_result"]["sha256"] = "0" * 64
    if defect == "export":
        f.inputs["optimizer_export"] = True
    if defect == "gold":
        f.execution["runtime_gold"] = True
    repin(f)
    with pytest.raises((PolicyError, AssertionError)):
        m.run(f.inputs, **f.args)
    assert not f.events and not f.args["output"].exists()


@pytest.mark.parametrize(
    "defect",
    [
        "partial-score",
        "duplicate-score",
        "changed-score",
        "duplicate-reference",
        "changed-authority",
        "late-phase-mutation",
    ],
)
def test_custody_refusals_never_persist_partial_derivative(
    tmp_path, monkeypatch, defect
):
    f = fixture(tmp_path, monkeypatch)
    if defect in {"partial-score", "duplicate-score", "changed-score"}:
        p = Path(f.inputs["members"]["seed"]["original_score_result"]["path"])
        score = json.loads(p.read_text())
        rows = score["slurp-slu-official-train"]["per_sample"]
        if defect == "partial-score":
            rows.pop()
        if defect == "duplicate-score":
            rows[1] = rows[0]
        if defect == "changed-score":
            rows[0]["scenario_action_exact"] = 0
        # The altered bytes must not pass the original source pin.
        p.write_text(json.dumps(score))
    if defect == "duplicate-reference":
        f.records.append(f.records[0])
    if defect == "changed-authority":
        calls = [0]

        def authority(*a, **k):
            calls[0] += 1
            return (
                f.business["read_authority"]
                if calls[0] == 1
                else {"read_run_id": "changed"}
            )

        monkeypatch.setattr(m.reader.CLI, "require_read_registration", authority)
    if defect == "late-phase-mutation":
        old = m.export_system_node_timing

        def nodes(source):
            Path(
                f.inputs["members"]["solver-lookup"]["phase_artifact"]["path"]
            ).write_text("changed")
            return old(source)

        monkeypatch.setattr(m, "export_system_node_timing", nodes)
    with pytest.raises((PolicyError, ValueError, AssertionError)):
        m.run(f.inputs, **f.args)
    assert not f.args["output"].exists()


def test_network_transport_is_fenced():
    with m.no_contacts(), pytest.raises(RuntimeError, match="refuses"):
        socket.create_connection(("example.invalid", 80))


@pytest.mark.parametrize("defect", ["partial", "duplicate", "different-final"])
def test_raw_bound_saved_score_coverage_and_final_alignment_refused(
    tmp_path, monkeypatch, defect
):
    f = fixture(tmp_path, monkeypatch)
    label = "seed"
    bound = f.inputs["members"][label]
    score = json.loads(Path(bound["original_score_result"]["path"]).read_text())
    rows = score["slurp-slu-official-train"]["per_sample"]
    if defect == "partial":
        rows.pop()
    if defect == "duplicate":
        rows[1] = rows[0]
    if defect == "different-final":
        rows[0]["scenario_action_exact"] = 0
    bound["original_score_result"] = f.save(
        Path(bound["original_score_result"]["path"]), score
    )
    manifest, _ = f.metadata[0]
    manifest["scores"] = bound["original_score_result"]
    bound["manifest"].update(f.save(Path(bound["manifest"]["path"]), manifest))
    for path, receipt in f.receipts.items():
        if Path(path).name == label + "-receipt.json":
            result = receipt["score_result"]
            result.update(
                f.save(
                    Path(result["path"]),
                    {
                        "manifest": bound["manifest"]["path"],
                        "verified": True,
                        "scores": score,
                    },
                )
            )
    family_path = Path(f.args["business_family_pin"]["path"])
    family = json.loads(family_path.read_text())
    family["bindings"][0]["config"]["manifest"] = bound["manifest"]
    f.args["business_family_pin"] = f.save(family_path, family)
    repin(f)
    with pytest.raises((PolicyError, ValueError)):
        m.run(f.inputs, **f.args)
    assert not f.args["output"].exists()


@pytest.mark.parametrize(
    "defect",
    [None, "other-field", "scorer", "missing-count", "authority", "scope", "implicit"],
)
def test_explicit_projection_successor_preserves_all_other_authority(
    tmp_path, monkeypatch, defect
):
    f = fixture(tmp_path, monkeypatch)
    data, repo = f.args["data_root"], f.args["repo_root"]
    fixed = m.read_absolute(f.inputs["root_diagnostic_scope"])
    original = json.loads((repo / fixed["supplement"]["relpath"]).read_text())
    new = copy.deepcopy(original)
    new["projection"] = {
        "schema": "saea-reward-projection-v1",
        "reward_rule_id": "native-counts",
        "scorer": original["projection"]["scorer"],
        "aggregate_fields": ["port_micro.slu_f1"],
        "per_sample_fields": list(m.SLURP_NATIVE_FIELDS),
    }
    if defect == "other-field":
        new["fixed"] = "changed"
    if defect == "scorer":
        new["projection"]["scorer"] = "slurp-slu-official-devel"
    if defect == "missing-count":
        new["projection"]["per_sample_fields"].pop()
    new_path = repo / "supplement-v2.json"
    new_abs = f.save(new_path, new)
    new_pin = {"relpath": new_path.name, "sha256": new_abs["sha256"]}
    failed = f.save(data / "coordination" / "failed.json", {"preserved": True})
    intent = f.save(repo / "intent.json", {"fixed": True})
    successor = {
        "schema": "saea-root-analysis-supplement-successor-v1",
        "status": "APPROVED_EXACT_NATIVE_PROJECTION_SCHEMA_CORRECTION",
        "owner_authority": 227,
        "allowed_changes": ["projection"],
        "learner_export": False,
        "metrics_and_scope_changed": False,
        "source_and_read_authority_changed": False,
        "model_contacts_added": 0,
        "official_score_jobs_added": 0,
        "prospective_diagnostic_scope": f.inputs["root_diagnostic_scope"],
        "root_read_authority_receipt": f.execution["root_read_authority"],
        "operational_inputs": {
            "path": str(data / f.args["bindings_pin"]["relpath"]),
            "sha256": f.args["bindings_pin"]["sha256"],
        },
        "authority": f.root_read["authority"],
        "recipe": fixed["recipe"],
        "old_supplement": fixed["supplement"],
        "new_supplement": new_pin,
        "old_projection": original["projection"],
        "new_projection": new["projection"],
        "first_reader_exit": failed,
        "failed_derivative_files": [failed],
        "original_intent": {"relpath": "intent.json", "sha256": intent["sha256"]},
    }
    if defect == "authority":
        successor["authority"] = {"read_run_id": "ROOT-READ"}
    if defect == "scope":
        successor["prospective_diagnostic_scope"] = failed
    execution = copy.deepcopy(f.execution)
    execution["supplement_successor"] = f.save(
        data / "coordination" / "successor.json", successor
    )
    if defect == "implicit":
        execution.pop("supplement_successor")
    if defect is None or defect == "implicit":
        selected = m.resolve_supplement(
            fixed, f.root_read, execution, repo_root=repo, data_root=data
        )
        assert selected == (fixed["supplement"] if defect == "implicit" else new_pin)
    else:
        with pytest.raises((PolicyError, ValueError)):
            m.resolve_supplement(
                fixed, f.root_read, execution, repo_root=repo, data_root=data
            )


@pytest.mark.parametrize(
    "defect", [None, "wrong-mapping", "wrong-config", "wrong-store", "outcomes"]
)
def test_support_mapping_is_pinned_to_frozen_source_not_outcomes(
    tmp_path, monkeypatch, defect
):
    f = fixture(tmp_path, monkeypatch)
    support = {
        "max_candidates": 3,
        "projection_policy": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1",
        "specification": {
            "schema": "saea-initial-intent-support-projection-v1",
            "policy_id": "initial-perception-request-intent-value-id-suffix-v1",
            "store_id": "intent-boundaries",
            "value_id_prefix": "intent-boundary:",
        },
    }
    supply = {"max_candidates": 3, "projection_policy": support["projection_policy"]}
    store = {
        "store_role": "intent-boundaries",
        "release": {"sha256": "a" * 64, "relpath": "release.json"},
        "snapshot": {"sha256": "b" * 64, "relpath": "snapshot.json"},
        "candidate_supply": {"solver": supply},
    }
    f.execution["intent_support"] = {
        label: copy.deepcopy(support) for label in f.sources
    }
    proof = {}
    for label, source in f.sources.items():
        source.composed.values["knowledge_stores"] = {
            "intent-boundaries": copy.deepcopy(store)
        }
        proof[label] = {
            "config_hash": source.composed.config_hash,
            "store_role": store["store_role"],
            "release": store["release"],
            "snapshot": store["snapshot"],
            "candidate_supply": supply,
        }
    receipt = {
        "schema": "saea-root-intent-support-configuration-binding-v1",
        "model_contacts_added": 0,
        "task_outcomes_used": False,
        "intent_support": copy.deepcopy(f.execution["intent_support"]),
        "proof": proof,
    }
    if defect == "wrong-mapping":
        f.execution["intent_support"]["seed"]["max_candidates"] = 4
    if defect == "wrong-config":
        proof["seed"]["config_hash"] = "wrong"
    if defect == "wrong-store":
        f.sources["seed"].composed.values["knowledge_stores"]["intent-boundaries"][
            "snapshot"
        ] = {"sha256": "changed"}
    if defect == "outcomes":
        receipt["task_outcomes_used"] = True
    f.execution["intent_support_receipt"] = f.save(
        f.args["data_root"] / "coordination" / "support.json", receipt
    )
    if defect is None:
        m.verify_support_binding(f.execution, f.sources)
    else:
        with pytest.raises(PolicyError):
            m.verify_support_binding(f.execution, f.sources)


def test_second_native_custody_refusal_prevents_write(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    original = m.verify_native_episode_source
    calls = [0]

    def verify(**kwargs):
        calls[0] += 1
        if calls[0] > len(f.sources):
            raise ValueError("late native trace corruption")
        return original(**kwargs)

    monkeypatch.setattr(m, "verify_native_episode_source", verify)
    with pytest.raises(ValueError, match="late native"):
        m.run(f.inputs, **f.args)
    assert not f.args["output"].exists()
