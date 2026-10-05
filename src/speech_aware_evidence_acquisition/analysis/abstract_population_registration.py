"""Bind a prospective complete-source plan after operational READ qualification.

Return registration documents in memory. Never write files, sign a READ, open
task quality, export learner feedback, or admit model/scorer work here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import abstract_population_sources as sources
from ..rails.experiment_population import load_population_config
from ..rails.system_text_policy import _read_pin, require


def prepare_population_source_registration(*, plan_pin, repo_root, data_root):
    """Materialize future source hashes only after all planned sources exist.

    Check every scope, READ and finalized attempt before seal qualification.
    Recheck all pinned inputs and authorities after qualification. The existing
    source reader and projection must still independently requalify these
    documents when the root explicitly persists and consumes them.
    """
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    plan = json.loads(_read_pin(plan_pin, root))
    require(set(plan) == {"schema", "status", "at_utc", "scope", "projection_config",
                         "families", "runtime_admission", "source_complete_required",
                         "policy_update_before_all_sources_complete"}
            and plan["schema"] == "saea-abstract-population-source-plan-v1"
            and plan["status"] == "ROOT_PLAN_REGISTERED_NOT_EXPORTED"
            and plan["runtime_admission"] is False
            and plan["source_complete_required"] is True
            and plan["policy_update_before_all_sources_complete"] is False,
            "complete offline source plan required")
    config = load_population_config(plan["projection_config"], repo_root=root)
    entries = plan["families"]
    require(isinstance(entries, list)
            and [e.get("cohort_id") for e in entries] == [c["cohort_id"] for c in config["cohorts"]],
            "all configured source cohorts required in order")
    # Discover all expected artifacts before opening even operational sources.
    for entry in entries:
        require(set(entry) == {"cohort_id", "recipe", "read_id", "frozen_check",
                              "expected_saved_family", "expected_source_specifications"},
                "exact planned source fields required")
        for key in ("expected_saved_family", "expected_source_specifications"):
            path = Path(entry[key]).resolve()
            require(path.is_relative_to(data), "planned source escaped data root")
            require(path.is_file(), "complete saved source artifacts are not available")
    reader = sources._reader(root)
    repo_pins = [plan_pin, plan["projection_config"]]
    external_pins, prepared, families, backends, family_ids = [], [], [], {}, set()

    def bind(path):
        resolved = Path(path).resolve()
        require(resolved.is_relative_to(data), "source escaped data root")
        pin = {"path": str(resolved), "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest()}
        external_pins.append(pin)
        return pin

    for entry, cohort in zip(entries, config["cohorts"], strict=True):
        recipe = json.loads(_read_pin(entry["recipe"], root))
        reg_pin = recipe["context_learning_registration"]
        reg = json.loads(_read_pin(reg_pin, root))
        protocol = json.loads(_read_pin(reg["protocol"], root))
        candidates, controls = sources.learning._validate_scope(recipe, reg, protocol, root=root)
        require(candidates == cohort["candidate_ids"] and controls == cohort["control_ids"]
                and recipe["sample_ids"] == cohort["sample_ids"], "planned source scope differs")
        require(recipe["family_id"] not in family_ids, "duplicate planned family")
        family_ids.add(recipe["family_id"])
        spec = {"family_id": recipe["family_id"], "expected_members": reg["expected_members"],
                "read_registration": entry["recipe"]}
        authority = reader.CLI.require_read_registration(spec, repo_root=root)
        require(authority["read_run_id"] == entry["read_id"], "planned READ identity differs")
        frozen = sources._external(entry["frozen_check"], data)
        external_pins.append(entry["frozen_check"])
        repo_pins.extend([entry["recipe"], reg_pin, reg["protocol"]])
        for member in reg["member_bindings"].values():
            path = (data / "attempts" / member["run_id"] / (member["attempt_id"] + ".json")).resolve()
            require(path.parent.parent == data / "attempts", "attempt escaped registered namespace")
            pin = bind(path)
            require(sources._external(pin, data).get("state") == "FINALIZED",
                    "all planned attempts must be finalized")
        families.append({"cohort_id": entry["cohort_id"], "recipe": entry["recipe"],
                         "frozen_check": entry["frozen_check"],
                         "saved_family": bind(entry["expected_saved_family"])})
        backends[entry["cohort_id"]] = bind(entry["expected_source_specifications"])
        prepared.append((entry, spec, authority, frozen))

    for entry, _, _, frozen in prepared:
        qualified = reader.qualify_registered_context_family(
            recipe_pin=entry["recipe"], repo_root=root, data_root=data, frozen_check=frozen)
        require(qualified["status"] == "ALL_MEMBERS_OPERATIONALLY_QUALIFIED",
                "all planned families must qualify")
        external_pins.extend(qualified["attempt_metadata_pins"] + qualified["job_metadata_pins"]
                             + [m["manifest"] for m in qualified["members"]])
    for pin in repo_pins:
        _read_pin(pin, root)
    for pin in external_pins:
        sources._external(pin, data, parse=False)
    for _, spec, authority, _ in prepared:
        require(reader.CLI.require_read_registration(spec, repo_root=root) == authority,
                "source READ authority changed during registration")
    return {
        "source_registration": {
            "schema": "saea-abstract-population-source-registration-v1",
            "status": "ROOT_REGISTERED", "scope": "abstract-feedback-source-join-only",
            "runtime_admission": False, "projection_config": plan["projection_config"],
            "families": families,
        },
        "source_specifications": backends,
        "learner_exported": False, "runtime_admission": False,
        "model_contacts": 0, "scorer_contacts": 0,
    }

