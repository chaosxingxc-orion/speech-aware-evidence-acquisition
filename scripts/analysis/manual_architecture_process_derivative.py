#!/usr/bin/env python3
"""Root-only post-READ process derivative; preserve business authority and originals."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
from unittest.mock import patch

from speech_aware_evidence_acquisition.analysis import (
    system_architecture_read as architecture,
)
from speech_aware_evidence_acquisition.analysis.native_episode_source import (
    verify_native_episode_source,
)
from speech_aware_evidence_acquisition.analysis.native_intent_support import (
    validate_initial_intent_support_spec,
)
from speech_aware_evidence_acquisition.analysis.slurp_process_metrics import (
    build_slurp_process_metrics,
    validate_solver_stage_statistics_declaration,
)
from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli import (
    load_verified_slurp_reference_records,
)
from speech_aware_evidence_acquisition.analysis.system_cache_cost import (
    export_system_sample_timing,
    export_system_node_timing,
)
from speech_aware_evidence_acquisition.analysis.system_process_report import (
    render_process_comparison,
)
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    SavedScoreReceiptRef,
    verify_complete_score_receipt,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.slurp import (
    load_slurp_split,
    load_slurp_ontology,
)
from speech_aware_evidence_acquisition.rails.reward_links import (
    RewardProjection,
    SLURP_NATIVE_FIELDS,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    preflight_family,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    _read_pin,
    require,
)

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "_manual_process_business_reader",
    ROOT / "scripts/analysis/system_text_pilot_read.py",
)
reader = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = reader
_spec.loader.exec_module(reader)


def pin(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def read_absolute(binding):
    require(set(binding) == {"path", "sha256"}, "exact absolute raw pin required")
    require(pin(binding["path"]) == binding, "absolute source pin differs")
    return json.loads(Path(binding["path"]).read_bytes())


def implementation_pins():
    """Expose source-only pins so root can bind execution before reading quality."""
    functions = [
        verify_native_episode_source,
        build_slurp_process_metrics,
    validate_solver_stage_statistics_declaration,
        load_verified_slurp_reference_records,
        export_system_sample_timing,
        export_system_node_timing,
        render_process_comparison,
        verify_complete_score_receipt,
        load_slurp_split,
        load_slurp_ontology,
        architecture.combine_process,
    ]
    paths = {Path(inspect.getfile(f)).resolve() for f in functions}
    paths.update([Path(__file__).resolve(), Path(reader.__file__).resolve()])
    for name in (
        "slurp_solver_stage_attribution",
        "native_candidate_stage_projections",
        "native_intent_support",
        "review_findings",
        "slurp_topn_diagnostics",
    ):
        paths.add(
            ROOT / "src/speech_aware_evidence_acquisition/analysis" / (name + ".py")
        )
    paths.add(ROOT / "src/speech_aware_evidence_acquisition/rails/reward_links.py")
    return {
        p.relative_to(ROOT).as_posix(): {
            "relpath": p.relative_to(ROOT).as_posix(),
            "sha256": pin(p)["sha256"],
        }
        for p in sorted(paths)
    }


def normalize_inputs(bindings, execution, *, data_root):
    """Adapt immutable root operational metadata without rewriting its bytes."""
    require(
        bindings.get("schema") == "saea-manual-process-operational-inputs-v1"
        and bindings.get("optimizer_export") is False
        and bindings.get("contacts") == 0
        and bindings.get("quality_values_parsed") is False
        and bindings.get("reference_records_loaded") is False,
        "pre-business whole-family operational bindings required",
    )
    require(
        execution.get("schema") == "saea-root-manual-process-execution-v1"
        and execution.get("learner_export") is False
        and execution.get("runtime_gold") is False,
        "root offline execution binding required",
    )

    def relative(binding):
        path = Path(binding["path"]).resolve()
        require(
            path.is_relative_to(data_root / "coordination"),
            "root metadata must remain confined",
        )
        require(pin(path) == binding, "root metadata raw pin differs")
        return {
            "relpath": path.relative_to(data_root).as_posix(),
            "sha256": binding["sha256"],
        }

    return {
        "diagnostic_scope": relative(bindings["root_diagnostic_scope"]),
        "root_read_authority": relative(execution["root_read_authority"]),
        "worker_commit": bindings["frozen_worker_commit"],
        "frozen_worker_root": bindings["frozen_worker_root"],
        "reference_binding": bindings["reference_binding"],
        "implementation": execution["implementation"],
        "members": {
            label: {
                **row,
                "phase": row["phase_artifact"],
                "original_score": row["original_score_result"],
                "intent_support_configuration": execution.get("intent_support", {}).get(
                    label
                ),
            }
            for label, row in bindings["members"].items()
        },
    }


def resolve_supplement(fixed_scope, root_read, execution, *, repo_root, data_root):
    """Allow only a raw-pinned root successor of the failed projection metadata."""
    original = fixed_scope["supplement"]
    require(
        root_read.get("supplement") == original, "original supplement authority differs"
    )
    successor_pin = execution.get("supplement_successor")
    if successor_pin is None:
        return original
    successor = read_absolute(successor_pin)
    expected_scope = {
        "path": str(data_root / execution["diagnostic_scope"]["relpath"]),
        "sha256": execution["diagnostic_scope"]["sha256"],
    }
    expected_inputs = {
        "path": str(data_root / execution["operational_inputs"]["relpath"]),
        "sha256": execution["operational_inputs"]["sha256"],
    }
    require(
        successor.get("schema") == "saea-root-analysis-supplement-successor-v1"
        and successor.get("status")
        == "APPROVED_EXACT_NATIVE_PROJECTION_SCHEMA_CORRECTION"
        and successor.get("owner_authority") == 227
        and successor.get("allowed_changes") == ["projection"]
        and successor.get("learner_export") is False
        and successor.get("metrics_and_scope_changed") is False
        and successor.get("source_and_read_authority_changed") is False
        and successor.get("model_contacts_added") == 0
        and successor.get("official_score_jobs_added") == 0
        and successor["prospective_diagnostic_scope"] == expected_scope
        and successor["root_read_authority_receipt"] == execution["root_read_authority"]
        and successor["operational_inputs"] == expected_inputs
        and successor["authority"] == root_read["authority"]
        and successor["recipe"] == fixed_scope["recipe"]
        and successor["old_supplement"] == original,
        "explicit predecessor and unchanged root READ required",
    )
    for source in [
        successor["first_reader_exit"],
        *successor["failed_derivative_files"],
    ]:
        require(
            pin(source["path"]) == source, "preserved failed derivative pin differs"
        )
    _read_pin(successor["original_intent"], repo_root)
    selected = successor["new_supplement"]
    old, new = (json.loads(_read_pin(p, repo_root)) for p in (original, selected))
    require(
        {k: v for k, v in old.items() if k != "projection"}
        == {k: v for k, v in new.items() if k != "projection"},
        "supplement successor changes fields outside projection",
    )
    require(
        successor["old_projection"] == old["projection"]
        and successor["new_projection"] == new["projection"],
        "declared projection successor differs",
    )
    projection = RewardProjection.from_json(new["projection"])
    require(
        projection.scorer == old["projection"]["scorer"]
        and set(projection.per_sample_fields) == set(SLURP_NATIVE_FIELDS),
        "supplement successor changes scorer or native sufficient counts",
    )
    return selected


def verify_support_binding(execution, sources):
    """Bind declared support mapping to exact verified source configs, not outcomes."""
    support = execution.get("intent_support", {})
    if not support:
        require(
            execution.get("intent_support_receipt") is None,
            "support receipt without mapping",
        )
        return
    receipt = read_absolute(execution["intent_support_receipt"])
    require(
        receipt.get("schema") == "saea-root-intent-support-configuration-binding-v1"
        and receipt.get("model_contacts_added") == 0
        and receipt.get("task_outcomes_used") is False
        and receipt["intent_support"] == support
        and set(support) == set(receipt["proof"]) == set(sources),
        "full source-only intent support binding differs",
    )
    for label, configuration in support.items():
        spec = validate_initial_intent_support_spec(configuration["specification"])
        require(
            set(configuration)
            == {"max_candidates", "projection_policy", "specification"},
            "exact declared support configuration required",
        )
        source, proof = sources[label], receipt["proof"][label]
        stores = source.composed.values["knowledge_stores"]
        store = stores[spec["store_id"]]
        supply = proof["candidate_supply"]
        require(
            proof["config_hash"] == source.composed.config_hash
            and proof["store_role"] == store["store_role"] == "intent-boundaries"
            and proof["snapshot"] == store["snapshot"]
            and proof["release"] == store["release"]
            and type(configuration["max_candidates"]) is int
            and configuration["max_candidates"] == supply["max_candidates"] > 0
            and configuration["projection_policy"] == supply["projection_policy"]
            and any(
                supply == declared
                for entry in stores.values()
                for declared in entry.get("candidate_supply", {}).values()
            ),
            "intent support mapping differs from frozen composed store/supply",
        )


@contextmanager
def no_contacts():
    def refuse(*args, **kwargs):
        raise RuntimeError("Process derivative refuses network/model/scorer transport")

    with (
        patch("socket.socket.connect", refuse),
        patch("socket.socket.connect_ex", refuse),
        patch("socket.create_connection", refuse),
    ):
        yield


def run(
    bindings,
    *,
    bindings_pin,
    business_report_pin,
    business_family_pin,
    execution_pin,
    repo_root,
    data_root,
    output,
):
    """Verify the full original family and unchanged READ before offline joins.

    The root fixes bindings and algorithm scope before business reading. Business
    pins are later inputs, not hashes embedded in their own authority recipe.
    """
    repo_root, data_root, output = map(
        lambda p: Path(p).resolve(), (repo_root, data_root, output)
    )
    require(
        output.is_relative_to(data_root / "analysis")
        and output != data_root / "analysis"
        and not output.exists(),
        "fresh root-only analysis output required",
    )
    raw_bindings = bindings
    require(
        json.loads(_read_pin(bindings_pin, data_root)) == raw_bindings,
        "operational input receipt differs",
    )
    execution = read_absolute(execution_pin)
    require(
        execution["operational_inputs"] == bindings_pin,
        "execution names other original inputs",
    )
    bindings = normalize_inputs(raw_bindings, execution, data_root=data_root)
    fixed_scope = json.loads(_read_pin(bindings["diagnostic_scope"], data_root))
    root_read = json.loads(_read_pin(bindings["root_read_authority"], data_root))
    stage_declaration = fixed_scope.get("solver_stage_statistics")
    require(stage_declaration == execution.get("solver_stage_statistics"),
            "prospective scope and execution stage declaration differ")
    retain_stages = validate_solver_stage_statistics_declaration(stage_declaration)
    validate_solver_stage_statistics_declaration(execution.get("solver_stage_statistics"))
    require(
        fixed_scope.get("schema")
        == "saea-manual-family-prospective-root-diagnostic-scope-v1"
        and fixed_scope.get("status")
        == "SCOPE_FIXED_BEFORE_QUALITY_READ_EXECUTION_AFTER_FULL_FAMILY_READ"
        and fixed_scope.get("learner_export") is False
        and fixed_scope.get("runtime_gold") is False
        and root_read.get("schema") == "saea-manual-family-root-read-authority-v1"
        and root_read.get("status") == "ROOT_COUNTERSIGNED_COMPLETE_FAMILY"
        and root_read.get("diagnostic_scope") == bindings["diagnostic_scope"],
        "prospective diagnostic scope or signed whole-family root authority differs",
    )
    require(
        raw_bindings["read_authority"] == root_read["authority"],
        "operational READ differs",
    )
    require(
        read_absolute(raw_bindings["family_qualification"]) is not None,
        "qualification required",
    )
    require(
        execution["diagnostic_scope"] == bindings["diagnostic_scope"],
        "execution changes original metric scope",
    )
    qualification_pin = raw_bindings["family_qualification"]
    require(
        root_read["qualification"]
        == {
            "relpath": Path(qualification_pin["path"])
            .relative_to(data_root)
            .as_posix(),
            "sha256": qualification_pin["sha256"],
        },
        "qualified family raw binding differs",
    )
    recipe_pin = fixed_scope["recipe"]
    supplement_pin = resolve_supplement(
        fixed_scope, root_read, execution, repo_root=repo_root, data_root=data_root
    )
    recipe, registration, owner, supplement = reader.load_documents(
        recipe_pin, supplement_pin, repo_root
    )
    require(
        "manual_architecture_registration" in recipe
        and recipe.get("process_diagnostics") is None,
        "unchanged manual business recipe must not self-pin this derivative",
    )
    family = {
        "family_id": recipe["family_id"],
        "expected_members": recipe["expected_members"],
        "read_registration": recipe_pin,
    }
    authority = reader.CLI.require_read_registration(family, repo_root=repo_root)
    require(
        authority == root_read["authority"]
        and root_read.get("recipe") == recipe_pin
        and raw_bindings["read_authority"] == authority,
        "exact signed READ recipe or ledger row changed",
    )
    scope = architecture.validate_registration(
        recipe, registration, owner, authority, repo_root=repo_root, data_root=data_root
    )
    require(
        set(bindings["members"]) == set(scope["labels"]),
        "full configured process family required",
    )
    require(
        bindings["implementation"] == implementation_pins(),
        "executing process implementation differs",
    )
    for source in fixed_scope["source_modules"].values():
        require(
            _read_pin(source, repo_root) == (ROOT / source["relpath"]).read_bytes(),
            "prospectively fixed process module differs from executing source",
        )
    roster_path = repo_root / recipe["analysis_roster"]["relpath"]
    originals, job_pins = reader.source_bindings(
        registration, pin(roster_path), data_root
    )
    metadata = preflight_family(originals, recipe["expected_members"])
    require(
        len({b["config"]["manifest"]["path"] for b in originals})
        == len(scope["labels"]),
        "duplicate original process manifests",
    )
    for original, (manifest, job) in zip(originals, metadata, strict=True):
        label = original["candidate_id"]
        bound = bindings["members"][label]
        member = registration["member_bindings"][label]
        require(
            bound["manifest"] == original["config"]["manifest"]
            and manifest["config"]["config_hash"] == member["config_hash"]
            and manifest.get("study_commit")
            == member["source_commit"]
            == bindings["worker_commit"]
            and manifest["attempt"]["attempt_id"]
            == member["attempt_id"]
            == bound["attempt_id"]
            and bound["run_id"] == member["run_id"]
            and bound["config_hash"] == member["config_hash"]
            and bound["runtime_sample_ids"] == scope["runtime_sample_ids"][label]
            and manifest["scores"] == bound["original_score"]
            and manifest["split"]["count"] == len(recipe["sample_ids"])
            and set(manifest["split"]["ids"]) == set(recipe["sample_ids"]),
            "original complete member source, score or roster differs",
        )
        # Only hash task artifacts here; qualify all members before opening content.
        for name in ("manifest", "phase", "original_score"):
            require(
                pin(bound[name]["path"]) == bound[name], "original artifact pin differs"
            )
    reference_binding = bindings["reference_binding"]
    require(
        reference_binding.get("kind") == "slurp-split"
        and reference_binding.get("allow_heldout", False) is False
        and reference_binding.get("allow_synthetic", False) is False
        and Path(reference_binding["data_root"]).resolve() == data_root,
        "offline references must retain exact nonheldout original carrier binding",
    )
    require(
        pin(reference_binding["lock"]["path"]) == reference_binding["lock"],
        "reference lock differs",
    )
    saved_family = read_absolute(business_family_pin)
    require(
        saved_family["family_id"] == family["family_id"]
        and saved_family["expected_members"] == family["expected_members"]
        and saved_family["read_registration"] == recipe_pin
        and len(saved_family["bindings"]) == len(scope["labels"])
        and {b["candidate_id"] for b in saved_family["bindings"]}
        == set(scope["labels"]),
        "business saved family differs from registered originals",
    )
    sources = {}
    for label in scope["labels"]:
        bound = bindings["members"][label]
        source = verify_native_episode_source(
            manifest_path=Path(bound["manifest"]["path"]),
            expected_manifest_sha256=bound["manifest"]["sha256"],
            phase_artifact_path=Path(bound["phase"]["path"]),
            expected_phase_sha256=bound["phase"]["sha256"],
            repo_root=Path(bindings["frozen_worker_root"]),
            data_root=data_root,
        )
        require(
            list(source.sample_ids) == scope["runtime_sample_ids"][label]
            and source.composed.config_hash
            == registration["member_bindings"][label]["config_hash"],
            "native process production order or config differs",
        )
        sources[label] = source
    verify_support_binding(execution, sources)
    # All original members are now native-verified; no partial family is analyzed.
    business = read_absolute(business_report_pin)
    require(
        business.get("read_authority") == authority
        and business.get("family_id") == family["family_id"]
        and business.get("learner_export") is False,
        "completed business report READ or no-export scope differs",
    )
    members, timing, score_sources, prepared = {}, {}, {}, {}
    saved_bindings = {b["candidate_id"]: b for b in saved_family["bindings"]}
    score_result_paths = set()
    lock = load_lock(Path(reference_binding["lock"]["path"]))
    ontology = load_slurp_ontology(lock, data_root)
    legal_slot_types = tuple(sorted(ontology.entity_types))
    require(legal_slot_types, "authoritative slot inventory is empty")
    for label in scope["labels"]:
        source, bound = sources[label], bindings["members"][label]
        saved = saved_bindings[label]["config"]
        require(
            saved["manifest"] == bound["manifest"],
            "business receipt names another manifest",
        )
        reference = saved["complete_score_receipt"]
        receipt = verify_complete_score_receipt(
            SavedScoreReceiptRef(
                reference["cell_id"], Path(reference["path"]), reference["sha256"]
            ),
            source.bundle,
        )
        score_pin = receipt["score_result"]
        require(
            score_pin["path"] not in score_result_paths,
            "duplicate saved complete score results",
        )
        score_result_paths.add(score_pin["path"])
        payload = read_absolute(score_pin)
        require(
            payload["scores"] == read_absolute(bound["original_score"]),
            "reused score envelope differs from original attached official score",
        )
        rows = payload["scores"][supplement["projection"]["scorer"]]["per_sample"]
        by_id = {r["sample_id"]: r for r in rows}
        require(
            len(rows) == len(by_id) == len(source.sample_ids)
            and set(by_id) == set(source.sample_ids),
            "saved official score rows are partial or duplicated",
        )
        records = load_verified_slurp_reference_records(
            reference_binding, source.sample_ids, loader=load_slurp_split
        )
        support = bound.get("intent_support_configuration")
        if support is not None:
            support = {**support, "legal_candidate_ids": frozenset(ontology.intents)}
        clock = export_system_sample_timing(source)
        nodes = export_system_node_timing(source)
        require(
            clock.get("available") is True
            and [r["sample_id"] for r in clock["samples"]] == list(source.sample_ids)
            and all(
                clock[k] == recipe["measurement_profile"][k]
                for k in ("slot_count", "queue_depth")
            ),
            "complete actual admission timing differs from registered source",
        )
        require(
            clock["first_admitted_sample"] == clock["samples"][0],
            "first sample must be actual first admission",
        )
        timing[label] = {**clock, "by_role": nodes["by_role"], "node_timing": nodes}
        score_sources[label] = {
            "manifest": bound["manifest"],
            "score_result": score_pin,
            "attempt_id": registration["member_bindings"][label]["attempt_id"],
        }
        if retain_stages:
            require(source.phase_artifact_sha256 == bound["phase"]["sha256"],
                    "verified stage phase custody differs")
            score_sources[label]["stage_source"] = {
                "phase_artifact_sha256": bound["phase"]["sha256"],
                "reference_binding_sha256": content_hash(reference_binding),
                "official_score_result_sha256": score_pin["sha256"],
                "config_hash": source.composed.config_hash,
                "protocol_hash": source.plan.protocol_hash,
                "split_identity_hash": source.plan.split_identity_hash,
                "ordered_sample_ids_sha256": content_hash(list(source.sample_ids)),
                "run_id": source.plan.run_id,
                "attempt_id": source.plan.attempt_id,
            }
        prepared[label] = (
            source,
            records,
            tuple(by_id[sid] for sid in source.sample_ids),
            support,
            score_pin,
        )
    # Close every official score/reference/timing join before deriving any member metrics.
    for label in scope["labels"]:
        source, records, official_rows, support, score_pin = prepared[label]
        members[label] = build_slurp_process_metrics(
            source,
            reference_records=records,
            official_final_rows=official_rows,
            reference_binding_sha256=content_hash(reference_binding),
            official_score_result_sha256=score_pin["sha256"],
            legal_slot_types=legal_slot_types,
            intent_support_configuration=support,
            review_applicability=scope["review_applicability"][label],
            solver_stage_statistics=retain_stages,
        )
    process = {
        "schema": "saea-manual-architecture-process-derivative-v1",
        "read_id": authority["read_run_id"],
        "read_authority": authority,
        "source_bindings": score_sources,
        "members": members,
        "timing": timing,
        "learner_export_allowed": False,
        "contacts_added": {"model": 0, "official_scorer": 0},
    }
    if retain_stages:
        process["solver_stage_statistics_declaration"] = stage_declaration
    combined = architecture.combine_process(
        recipe=recipe,
        business=business,
        process=process,
        timing=timing,
        scope=scope,
        score_sources=score_sources,
        solver_stage_statistics_declaration=stage_declaration,
    )
    require(
        reader.CLI.require_read_registration(family, repo_root=repo_root) == authority,
        "exact root READ changed during diagnostic joins",
    )
    require(
        architecture.validate_registration(
            recipe,
            registration,
            owner,
            authority,
            repo_root=repo_root,
            data_root=data_root,
        )
        == scope,
        "registered family changed during diagnostics",
    )
    reader.load_documents(recipe_pin, supplement_pin, repo_root)
    require(
        json.loads(_read_pin(bindings_pin, data_root)) == raw_bindings
        and read_absolute(execution_pin) == execution
        and bindings["implementation"] == implementation_pins(),
        "process bindings or implementation changed during diagnostics",
    )
    for source in [
        business_report_pin,
        business_family_pin,
        execution_pin,
        execution["root_read_authority"],
        raw_bindings["root_diagnostic_scope"],
        raw_bindings["family_qualification"],
        reference_binding["lock"],
        *job_pins,
        *[
            p
            for b in bindings["members"].values()
            for p in (b["manifest"], b["phase"], b["original_score"])
        ],
    ]:
        require(
            pin(source["path"]) == source,
            "source changed before derivative persistence",
        )
    for label in scope["labels"]:
        reference = saved_bindings[label]["config"]["complete_score_receipt"]
        verify_complete_score_receipt(
            SavedScoreReceiptRef(
                reference["cell_id"], Path(reference["path"]), reference["sha256"]
            ),
            sources[label].bundle,
        )
    provenance = {
        "diagnostic_scope": bindings["diagnostic_scope"],
        "input_bindings": bindings_pin,
        "root_read_authority": bindings["root_read_authority"],
        "business_report": business_report_pin,
        "business_family": business_family_pin,
        "reference_binding": reference_binding,
        "reference_binding_content_sha256": content_hash(reference_binding),
        "legal_slot_types_sha256": content_hash(list(legal_slot_types)),
        "legal_intents_sha256": content_hash(sorted(ontology.intents)),
        "execution": execution_pin,
        "supplement": supplement_pin,
        "implementation": bindings["implementation"],
        "source_bindings": score_sources,
        "business_report_modified": False,
        "ledger_modified": False,
        "runtime_gold": False,
        "learner_export": False,
        "model_contacts": 0,
        "scorer_contacts": 0,
    }
    # Reverify raw trace/output custody as well as envelope pins before persistence.
    for label in scope["labels"]:
        bound = bindings["members"][label]
        verify_native_episode_source(
            manifest_path=Path(bound["manifest"]["path"]),
            expected_manifest_sha256=bound["manifest"]["sha256"],
            phase_artifact_path=Path(bound["phase"]["path"]),
            expected_phase_sha256=bound["phase"]["sha256"],
            repo_root=Path(bindings["frozen_worker_root"]),
            data_root=data_root,
        )
    resolve_supplement(
        fixed_scope, root_read, execution, repo_root=repo_root, data_root=data_root
    )
    verify_support_binding(execution, sources)
    if execution.get("intent_support_receipt") is not None:
        provenance["intent_support_receipt"] = execution["intent_support_receipt"]
    output.mkdir(parents=True, exist_ok=False)
    for name, value in [
        ("process-v2.json", process),
        ("comparison-v2.json", combined),
        ("provenance-v1.json", provenance),
    ]:
        reader.CLI.write_new(output / name, value)
    with (output / "report.md").open("x") as stream:
        stream.write(render_process_comparison(combined))
    return {
        "output": str(output),
        "members": list(scope["labels"]),
        "read_authority": authority,
        "model_contacts": 0,
        "scorer_contacts": 0,
        "learner_export": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--implementation-pins", action="store_true")
    for name in (
        "bindings",
        "execution",
        "business-report",
        "business-family",
        "output",
        "data-root",
    ):
        p.add_argument("--" + name, type=Path)
    p.add_argument("--bindings-sha256")
    p.add_argument("--execution-sha256")
    p.add_argument("--business-report-sha256")
    p.add_argument("--business-family-sha256")
    p.add_argument("--repo-root", type=Path, default=ROOT)
    args = p.parse_args()
    if args.implementation_pins:
        print(json.dumps(implementation_pins(), sort_keys=True))
        return
    require(
        all(
            getattr(args, n) is not None
            for n in (
                "bindings",
                "execution",
                "business_report",
                "business_family",
                "output",
                "data_root",
            )
        ),
        "exact process bindings and completed business pins required",
    )
    require(
        args.bindings.resolve().is_relative_to(
            args.data_root.resolve() / "coordination"
        ),
        "bindings must be root coordination metadata",
    )
    bindings_pin = {
        "relpath": args.bindings.resolve()
        .relative_to(args.data_root.resolve())
        .as_posix(),
        "sha256": args.bindings_sha256,
    }
    report_pin = {
        "path": str(args.business_report.resolve()),
        "sha256": args.business_report_sha256,
    }
    family_pin = {
        "path": str(args.business_family.resolve()),
        "sha256": args.business_family_sha256,
    }
    with no_contacts():
        result = run(
            json.loads(_read_pin(bindings_pin, args.data_root)),
            bindings_pin=bindings_pin,
            execution_pin={
                "path": str(args.execution.resolve()),
                "sha256": args.execution_sha256,
            },
            business_report_pin=report_pin,
            business_family_pin=family_pin,
            repo_root=args.repo_root,
            data_root=args.data_root,
            output=args.output,
        )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
