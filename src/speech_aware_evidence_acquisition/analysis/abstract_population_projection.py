"""Project qualified complete source cohorts without semantic summarizer calls.

Keep raw source custody private. Return an in-memory learner representation only
when every configured cohort and every candidate projection passes. This module
neither publishes that representation nor allocates proposals or runtime work.
"""
from __future__ import annotations

import json
from pathlib import Path

from .abstract_population_sources import read_registered_population_sources, _external, _reader
from .abstract_node_feedback import abstract_episode, abstract_partitioned_population_feedback, FEEDBACK_SCHEMA
from .native_episode_source import verify_native_episode_source
from .system_cache_cost import export_system_node_timing
from ..rails import system_context_learning as learning
from ..rails.experiment_population import load_population_config
from ..rails.hashing import content_hash
from ..rails.system_text_policy import _read_pin, require


def project_registered_population(*, projection_pin, repo_root, data_root):
    """Bind native outputs/costs to qualified official rewards, then erase contents.

    Qualify the complete source join before opening any native episode. Validate
    every backend binding before projecting the first candidate. Read only one
    verified native bundle at a time; do not retain raw responses in the return.
    Missing contacts, unregistered inputs and source changes refuse the entire
    return rather than producing a partial learner packet.
    """
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    request = json.loads(_read_pin(projection_pin, root))
    require(set(request) == {"schema", "status", "source_join", "source_specifications", "runtime_admission"}
            and request["schema"] == "saea-abstract-population-projection-v1"
            and request["status"] == "ROOT_REGISTERED" and request["runtime_admission"] is False,
            "registered offline projection required")
    joined = read_registered_population_sources(source_registration_pin=request["source_join"],
                                                repo_root=root, data_root=data)
    manifest = json.loads(_read_pin(request["source_join"], root))
    require(joined["projection_config"] == manifest["projection_config"], "projection configuration differs")
    config = load_population_config(joined["projection_config"], repo_root=root)
    tags = [c["cohort_id"] for c in config["cohorts"]]
    require(isinstance(request["source_specifications"], dict)
            and set(request["source_specifications"]) == set(tags)
            and list(joined["private_families"]) == tags, "all configured source backends required")
    external_pins, prepared, authorities, repo_pins = [], [], [], []
    reader = _reader(root)
    for entry, cohort in zip(manifest["families"], config["cohorts"], strict=True):
        tag = cohort["cohort_id"]
        require(entry["cohort_id"] == tag, "source order differs")
        family = joined["private_families"][tag]
        evidence, recipe, reg, _, candidates, controls, reference = family
        repo_pins.extend([entry["recipe"], recipe["context_learning_registration"], reg["protocol"]])
        require(candidates == cohort["candidate_ids"] and controls == cohort["control_ids"]
                and recipe["sample_ids"] == cohort["sample_ids"], "qualified population scope differs")
        saved = _external(entry["saved_family"], data)
        backend_pin = request["source_specifications"][tag]
        backend = _external(backend_pin, data)
        require(isinstance(backend, dict) and set(backend) == set(candidates + controls),
                "exact complete backend membership required")
        bindings = saved["bindings"]
        require(len(bindings) == len(candidates + controls)
                and {b["candidate_id"] for b in bindings} == set(candidates + controls),
                "exact saved family membership required")
        by_id = {b["candidate_id"]: b for b in bindings}
        external_pins.extend([entry["saved_family"], backend_pin])
        for cid in candidates + controls:
            b = backend[cid]
            require(isinstance(b, dict) and set(b) == {"phase", "repo_root"}, "exact native backend required")
            for pin in (b["phase"], by_id[cid]["config"]["manifest"]):
                _external(pin, data, parse=False)
                external_pins.append(pin)
        q = joined["qualifications"][tag]
        external_pins.extend(q["attempt_metadata_pins"] + q["job_metadata_pins"]
                             + [m["manifest"] for m in q["members"]])
        spec = {"family_id": recipe["family_id"], "expected_members": reg["expected_members"],
                "read_registration": entry["recipe"]}
        authorities.append((spec, reader.CLI.require_read_registration(spec, repo_root=root)))
        groups = learning._candidate_groups(evidence, recipe, reg, candidates, reference)
        require([g["sample_id"] for g in groups] == cohort["sample_ids"], "ordered reward roster differs")
        prepared.append((cohort, family, by_id, backend, groups))

    def recheck():
        for pin in [projection_pin, request["source_join"], joined["projection_config"], *repo_pins]:
            _read_pin(pin, root)
        for pin in external_pins:
            _external(pin, data, parse=False)
        for spec, authority in authorities:
            require(reader.CLI.require_read_registration(spec, repo_root=root) == authority,
                    "source READ changed during projection")

    recheck()
    views, contracts, custody = {}, {}, []
    for cohort, family, by_id, backend, groups in prepared:
        evidence, recipe, reg, _, candidates, _, reference = family
        tag, ids = cohort["cohort_id"], cohort["sample_ids"]
        templates = []
        for cid in candidates:
            mp, native = by_id[cid]["config"]["manifest"], backend[cid]
            phase = native["phase"]
            source = verify_native_episode_source(manifest_path=Path(mp["path"]),
                expected_manifest_sha256=mp["sha256"], phase_artifact_path=Path(phase["path"]),
                expected_phase_sha256=phase["sha256"], repo_root=Path(native["repo_root"]), data_root=data)
            require(len(source.sample_ids) == len(ids) and set(source.sample_ids) == set(ids),
                    "complete native roster differs")
            timing = export_system_node_timing(source)
            indexed, requests = {sid: [] for sid in ids}, set()
            for contact in timing["contacts"]:
                sid, rid = contact["sample_id"], contact["request_id"]
                require(sid in indexed and rid not in requests, "foreign input or repeated native request")
                requests.add(rid)
                indexed[sid].append(contact)
            rows = []
            for ordinal, sid in enumerate(ids):
                matches = [m for m in groups[ordinal]["members"] if m["candidate_id"] == cid]
                require(len(matches) == 1, "one qualified reward per input/candidate required")
                member = matches[0]
                contacts = [{"role": c["role_id"], "visit": c["visit_index"],
                    "interrupted": c["interrupted"],
                    "text": source.bundle.trace_records[c["request_id"] + "/response"]["text"],
                    "measurements": c["measurements"]} for c in indexed[sid]]
                execution = member["execution"]
                abstract = abstract_episode(contacts, counts=member["native_counts"], reference_f1=reference["f1"],
                    reliable=execution["reliable_completion"], abstained=execution["abstained"],
                    elapsed_seconds=execution["wall_time_seconds"])
                require(abstract["terminal"]["utility"] == member["utility"]
                        and len(contacts) == execution["model_calls"], "complete native contact/reward accounting differs")
                rows.append({"input_index": ordinal, **abstract})
            summary = evidence["summaries"][cid]
            templates.append({"candidate_id": cid, "bundle_id": reg["member_bindings"][cid]["bundle_id"],
                "official_summary": {"slu_f1": summary["slu_f1"],
                                     "intent": summary.get("intent_accuracy", summary.get("intent"))}, "samples": rows})
            custody.append({"cohort_id": tag, "candidate_id": cid, "manifest": mp, "phase": phase,
                "source_root": native["repo_root"], "node_timing_content_sha256": timing["content_sha256"],
                "contacts": len(requests), "rows": len(ids)})
            del contacts, source, timing, indexed
        roster_hash = content_hash(ids)
        views[tag] = {"source_batch": tag, "family_id": recipe["family_id"], "reference_f1": reference["f1"],
                      "templates": templates, "sample_order_sha256": roster_hash}
        contracts[tag] = {"expected_bundles": {cid: reg["member_bindings"][cid]["bundle_id"] for cid in candidates},
                         "expected_family_id": recipe["family_id"], "expected_source_batch": tag,
                         "reference_f1": reference["f1"], "sample_order_sha256": roster_hash}
    population = abstract_partitioned_population_feedback(views, expected_partitions=contracts, population_config=config)
    recheck()
    return {"learner_view": {"schema": "saea-abstract-population-learning-view-v1",
                            "representation": FEEDBACK_SCHEMA, "population": population},
            "private_custody": {"projection_registration": projection_pin,
                                "source_join": request["source_join"], "sources": custody},
            "learner_exported": False, "runtime_admission": False, "model_contacts": 0, "scorer_contacts": 0}
