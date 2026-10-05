"""Qualify all registered source cohorts before a private population feedback read.

Reuse the existing complete-family reader. This adapter neither scores nor
exports a learner view, allocates proposals, pools returns, or grants runtime
admission. A projection configuration describes the source join only; it never
retrofits the historical execution configuration of a source family.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from ..rails import system_context_learning as learning
from ..rails.experiment_population import load_population_config
from ..rails.system_text_policy import _read_pin, require


def _reader(root):
    spec = importlib.util.spec_from_file_location(
        "_abstract_population_complete_reader", root / "scripts/analysis/system_text_pilot_read.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _external(pin, data_root, *, parse=True):
    require(isinstance(pin, dict) and set(pin) == {"path", "sha256"},
            "exact external source pin required")
    path = Path(pin["path"]).resolve()
    require(path.is_relative_to(data_root), "source escaped registered data root")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin["sha256"], "external source changed")
    return json.loads(raw) if parse else None


def read_registered_population_sources(*, source_registration_pin, repo_root, data_root):
    """Return private, freshly qualified families only after the entire join passes.

    First verify every source scope, READ and attempt. Then independently verify
    every seal and unique complete score. Only then open saved family bindings
    and call the existing source-bound feedback reader. Do not persist or expose
    partial results when a later source fails.
    """
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    manifest = json.loads(_read_pin(source_registration_pin, root))
    require(set(manifest) == {"schema", "status", "scope", "runtime_admission",
                             "projection_config", "families"}
            and manifest["schema"] == "saea-abstract-population-source-registration-v1"
            and manifest["status"] == "ROOT_REGISTERED"
            and manifest["scope"] == "abstract-feedback-source-join-only"
            and manifest["runtime_admission"] is False,
            "registered projection-only source join required")
    config = load_population_config(manifest["projection_config"], repo_root=root)
    sources, cohorts = manifest["families"], config["cohorts"]
    require(isinstance(sources, list)
            and [s.get("cohort_id") for s in sources] == [c["cohort_id"] for c in cohorts],
            "every configured source cohort in registered order required")
    reader = _reader(root)
    prepared, repo_pins, external_pins, attempt_pins = [], [source_registration_pin,
                                                          manifest["projection_config"]], [], []
    family_ids = set()
    for source, cohort in zip(sources, cohorts, strict=True):
        require(set(source) == {"cohort_id", "recipe", "frozen_check", "saved_family"},
                "exact source-family bindings required")
        recipe = json.loads(_read_pin(source["recipe"], root))
        reg_pin = recipe["context_learning_registration"]
        reg = json.loads(_read_pin(reg_pin, root))
        protocol = json.loads(_read_pin(reg["protocol"], root))
        candidates, controls = learning._validate_scope(recipe, reg, protocol, root=root)
        require(candidates == cohort["candidate_ids"] and controls == cohort["control_ids"]
                and recipe["sample_ids"] == cohort["sample_ids"],
                "source policy membership or ordered inputs differ from projection config")
        require(recipe["family_id"] not in family_ids, "duplicate source family")
        family_ids.add(recipe["family_id"])
        spec = {"family_id": recipe["family_id"], "expected_members": reg["expected_members"],
                "read_registration": source["recipe"]}
        authority = reader.CLI.require_read_registration(spec, repo_root=root)
        frozen = _external(source["frozen_check"], data)
        _external(source["saved_family"], data, parse=False)
        repo_pins.extend([source["recipe"], reg_pin, reg["protocol"]])
        external_pins.extend([source["frozen_check"], source["saved_family"]])
        for member in reg["member_bindings"].values():
            path = (data / "attempts" / member["run_id"] / (member["attempt_id"] + ".json")).resolve()
            require(path.parent.parent == data / "attempts", "source attempt escaped data root")
            raw = path.read_bytes()
            require(json.loads(raw).get("state") == "FINALIZED",
                    "every source attempt must finalize before any family quality read")
            attempt_pins.append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
        prepared.append((source, frozen, spec, authority))

    def recheck():
        for pin in repo_pins:
            _read_pin(pin, root)
        for pin in external_pins + attempt_pins:
            _external(pin, data, parse=False)
        for _, _, spec, authority in prepared:
            require(reader.CLI.require_read_registration(spec, repo_root=root) == authority,
                    "source READ authority changed during join")

    qualifications = {}
    for source, frozen, _, _ in prepared:
        q = reader.qualify_registered_context_family(recipe_pin=source["recipe"],
            repo_root=root, data_root=data, frozen_check=frozen)
        require(q["status"] == "ALL_MEMBERS_OPERATIONALLY_QUALIFIED",
                "all source families must qualify before any quality read")
        qualifications[source["cohort_id"]] = q
        external_pins.extend(q["attempt_metadata_pins"] + q["job_metadata_pins"]
                             + [m["manifest"] for m in q["members"]])
    recheck()
    private = {}
    for source, _, _, _ in prepared:
        bindings = _external(source["saved_family"], data)["bindings"]
        private[source["cohort_id"]] = learning._qualified_feedback(
            bindings, recipe_pin=source["recipe"], repo_root=root)
    recheck()
    return {"schema": "saea-private-population-source-join-v1",
            "source_registration": source_registration_pin,
            "projection_config": manifest["projection_config"],
            "qualifications": qualifications, "private_families": private,
            "learner_exported": False, "runtime_admission": False,
            "model_contacts": 0, "scorer_contacts": 0}
