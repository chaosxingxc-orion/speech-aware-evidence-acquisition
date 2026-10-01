"""Immutable, jointly edited text policies compiled into the existing controller.

This module grants no execution, data-read, scoring or adoption authority. Runtime
knowledge and optimizer experience have separate entries and separate consumers.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .hashing import content_hash
from .prepared_feedback import reject_non_latin_scripts

BUNDLE_SCHEMA = "saea-system-text-policy-bundle-v1"
PROPOSAL_SCHEMA = "saea-text-policy-update-proposal-v1"
EDITABLE = frozenset({"construction_instruction", "role_text", "supply", "slot_value_edits"})
BUNDLE_KEYS = frozenset({"schema", "parent_ids", "seed_config_sha256", "construction_instruction",
                        "role_text", "supply", "knowledge", "construction_receipt",
                        "cumulative_sources", "optimizer_experience"})


class PolicyError(ValueError):
    """A policy, proposal, provenance or compilation violates its declared scope."""


def require(condition, message):
    if not condition:
        raise PolicyError(message)


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value), "invalid SHA-256")
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _text(value):
    require(isinstance(value, str) and bool(value.strip()), "nonempty English text is required")
    require(len(value) <= 32768, "text exceeds registered character ceiling")
    try:
        reject_non_latin_scripts(value)
    except ValueError as error:
        raise PolicyError(str(error)) from error


def _pin(pin):
    require(isinstance(pin, dict) and set(pin) == {"relpath", "sha256"}, "invalid artifact pin")
    path = pin["relpath"]
    require(isinstance(path, str) and path and not path.startswith("/")
            and ":" not in path and "\\" not in path
            and not {"", ".", ".."}.intersection(path.split("/")), "invalid relative artifact path")
    sha(pin["sha256"])


def validate_sources(sources):
    require(isinstance(sources, list), "cumulative sources must be a list")
    seen = set()
    for source in sources:
        require(isinstance(source, dict) and set(source) == {"kind", "sha256", "sample_ids"},
                "source fields differ")
        require(source["kind"] in {"knowledge", "feedback", "proposal", "selection", "construction"},
                "unknown source purpose")
        sha(source["sha256"])
        ids = source["sample_ids"]
        require(isinstance(ids, list) and all(isinstance(s, str) and s.startswith("slurp:train:") for s in ids)
                and len(ids) == len(set(ids)), "only unique TRAIN ancestry may enter optimization")
        identity = (source["kind"], source["sha256"])
        require(identity not in seen, "duplicate cumulative source")
        seen.add(identity)
    return sources


def cumulative_sources(parents, additions=()):
    """Keep every transitive source even when knowledge or experience is deleted."""
    result = {}
    for source in [s for p in parents for s in p.as_json()["cumulative_sources"]] + list(additions):
        validate_sources([source])
        key = (source["kind"], source["sha256"])
        require(key not in result or result[key] == source, "one source hash has conflicting ancestry")
        result[key] = copy.deepcopy(source)
    return [result[k] for k in sorted(result)]


def assert_roster_disjoint(sources, sample_ids):
    validate_sources(list(sources))
    def utterance(sid):
        return ":".join(sid.split(":")[:3])
    used = {utterance(sid) for s in sources for sid in s["sample_ids"]}
    overlap = used.intersection(utterance(sid) for sid in sample_ids)
    require(not overlap, "evaluation overlaps cumulative feedback/construction ancestry")


@dataclass(frozen=True)
class SystemTextPolicyBundle:
    """Canonical JSON gives deep immutability, including nested configuration."""
    document_json: str

    @property
    def bundle_id(self):
        return content_hash(self.as_json())

    def as_json(self):
        return json.loads(self.document_json)

    @classmethod
    def from_json(cls, document, *, parents=()):
        require(isinstance(document, dict) and set(document) == BUNDLE_KEYS
                and document["schema"] == BUNDLE_SCHEMA, "policy bundle fields differ")
        d = copy.deepcopy(document)
        sha(d["seed_config_sha256"])
        require(isinstance(d["parent_ids"], list) and len(set(d["parent_ids"])) == len(d["parent_ids"]),
                "invalid parent identities")
        for identity in d["parent_ids"]:
            sha(identity)
        require(set(d["parent_ids"]) == {p.bundle_id for p in parents}, "all parents must be supplied")
        _text(d["construction_instruction"])
        require(isinstance(d["role_text"], dict) and set(d["role_text"]) == {"solver", "reviewer", "planner"},
                "only Solver, Reviewer and Planner texts are editable")
        for text in d["role_text"].values():
            _text(text)
        supply = d["supply"]
        require(isinstance(supply, dict) and set(supply) == {"mode", "value_limit"}
                and supply["mode"] in {"targeted", "reread"}
                and type(supply["value_limit"]) is int and 1 <= supply["value_limit"] <= 2,
                "supply must use implemented bounded selection")
        require(isinstance(d["knowledge"], dict) and set(d["knowledge"]) == {"snapshot", "release"},
                "knowledge requires an actual released snapshot")
        for pin in d["knowledge"].values():
            _pin(pin)
        if d["construction_receipt"] is not None:
            _pin(d["construction_receipt"])
        validate_sources(d["cumulative_sources"])
        for parent in parents:
            old = parent.as_json()
            require(old["seed_config_sha256"] == d["seed_config_sha256"], "seed system changed")
            require(all(s in d["cumulative_sources"] for s in old["cumulative_sources"]),
                    "cumulative ancestry cannot be removed")
            if old["construction_instruction"] != d["construction_instruction"]:
                require(d["knowledge"] != old["knowledge"] and d["construction_receipt"] is not None,
                        "changed construction instructions require materialized knowledge")
        require(isinstance(d["optimizer_experience"], list), "experience must be an indexed list")
        for pin in d["optimizer_experience"]:
            _pin(pin)
        return cls(canonical(d))


@dataclass(frozen=True)
class TextPolicyUpdateProposal:
    """A provisional joint edit. Validation never activates or repairs a proposal."""
    document_json: str

    def as_json(self):
        return json.loads(self.document_json)

    @classmethod
    def from_json(cls, d):
        require(isinstance(d, dict) and set(d) == {"schema", "branch", "round", "slot", "parent_ids",
                                                 "changes", "rationale", "hypotheses", "evidence"}
                and d["schema"] == PROPOSAL_SCHEMA, "proposal fields differ")
        require(d["branch"] in {"L", "B"} and type(d["round"]) is int and d["round"] in (1, 2, 3)
                and type(d["slot"]) is int and d["slot"] in (1, 2), "invalid proposal allocation")
        require(isinstance(d["changes"], dict) and set(d["changes"]) <= EDITABLE,
                "proposal changes an undeclared editable surface")
        if "slot_value_edits" in d["changes"]:
            from .semantic_knowledge_edits import PROPOSAL_SCHEMA as SLOT_EDIT_SCHEMA
            edits = d["changes"]["slot_value_edits"]
            require(isinstance(edits, dict) and set(edits) == {"schema", "base_rows_sha256", "edits"}
                    and edits["schema"] == SLOT_EDIT_SCHEMA and isinstance(edits["edits"], list),
                    "slot value changes require the existing exact edit proposal schema")
            sha(edits["base_rows_sha256"])
        require(isinstance(d["parent_ids"], list) and bool(d["parent_ids"]), "parent IDs are required")
        for identity in d["parent_ids"]:
            sha(identity)
        _text(d["rationale"])
        require(isinstance(d["hypotheses"], list) and isinstance(d["evidence"], list), "invalid evidence index")
        for text in d["hypotheses"]:
            _text(text)
        reject_non_latin_scripts(d)
        return cls(canonical(d))


def _read_pin(pin, root):
    _pin(pin)
    path = (Path(root) / pin["relpath"]).resolve()
    require(path.is_relative_to(Path(root).resolve()), "artifact escaped its root")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin["sha256"], "artifact hash mismatch")
    return raw


def apply_text_proposal(proposal, *, parents, added_sources, knowledge=None, construction_receipt=None,
                        optimizer_experience=None):
    """Materialize a whole candidate; construction edits wait for a real build.

    Source custody is checked when packaging the proposal and again on release.
    This pure materializer cannot drop transitive parent or proposal ancestry.
    """
    p = proposal.as_json()
    require(parents and p["parent_ids"] == [b.bundle_id for b in parents], "proposal parent binding differs")
    d = parents[0].as_json()
    changes = p["changes"]
    if "slot_value_edits" in changes or "construction_instruction" in changes:
        require(knowledge is not None and construction_receipt is not None,
                "joint construction edits need a verified materialized construction release")
    if "role_text" in changes:
        require(isinstance(changes["role_text"], dict)
                and set(changes["role_text"]) <= {"solver", "reviewer", "planner"}, "unknown role text")
        d["role_text"].update(changes["role_text"])
    for key in ("construction_instruction", "supply"):
        if key in changes:
            d[key] = changes[key]
    if knowledge is not None:
        d["knowledge"] = knowledge
        d["construction_receipt"] = construction_receipt
    d["parent_ids"] = p["parent_ids"]
    d["cumulative_sources"] = cumulative_sources(parents, added_sources)
    if optimizer_experience is not None:
        d["optimizer_experience"] = optimizer_experience
    return SystemTextPolicyBundle.from_json(d, parents=parents)


def compile_system_text_policy(baseline, bundle, *, repo_root, output_root, enabled=True, data_root=None):
    """Stage content-addressed role texts and compile with the shared module.

    output_root is an isolated checkout/staging root. Its configs/probes subtree must be
    included in the frozen worker before ordinary runtime admission. The disabled
    path is exactly the historical fragment, without adding trace-only keys.
    """
    if not enabled:
        return copy.deepcopy(baseline)
    from . import consumption_module as cm
    d = bundle.as_json()
    require(content_hash(baseline) == d["seed_config_sha256"], "seed configuration hash differs")
    block = copy.deepcopy(baseline["native_episode"]["consumption_module"])
    opportunity = next(c for c in block["components"] if c["component_id"] == cm.KNOWLEDGE_CONSUMPTION_OPPORTUNITY)
    require(opportunity["state"] == "on", "seed must have the bounded opportunity enabled")
    params = opportunity["params"]
    knowledge_changed = d["knowledge"] != {k: baseline["knowledge_stores"][params["store_id"]][k] for k in ("snapshot", "release")}
    if knowledge_changed or d["construction_receipt"] is not None:
        require(data_root is not None and d["construction_receipt"] is not None,
                "materialized construction receipt and data root required")
        receipt = json.loads(_read_pin(d["construction_receipt"], data_root))
        require(receipt.get("schema") == "saea-system-text-construction-link-v1"
                and receipt.get("instruction_sha256") == content_hash(d["construction_instruction"])
                and receipt.get("knowledge") == d["knowledge"], "construction receipt does not bind policy")
        from .system_text_construction import verify_released_slot_construction
        generated = verify_released_slot_construction(receipt, instruction=d["construction_instruction"],
                                                       data_root=data_root, repo_root=repo_root)
        covered = {sid for s in d["cumulative_sources"] for sid in s["sample_ids"]}
        require(set(generated["optimizer_construction_sample_ids"]) <= covered,
                "construction feedback ancestry is missing from policy")
        params["knowledge_binding"] = d["knowledge"]
    params["mode"] = d["supply"]["mode"]
    params["value_limit"] = d["supply"]["value_limit"]
    staged = []
    for role, text in d["role_text"].items():
        rel = f"probes/system-text-policy/{bundle.bundle_id}/{role}.txt"
        path = Path(output_root) / "configs" / rel
        raw = text.encode("utf-8")
        require(not path.exists() or path.read_bytes() == raw, "refuse to overwrite frozen role text")
        staged.append((path, raw))
        params[role + "_template"] = rel
    result = cm.compile_module(block, cm.resolve_carrier_hooks(block["profile"], repo_root=Path(repo_root)),
                               repo_root=Path(repo_root)).apply_to(baseline)
    result["native_episode"]["consumption_module"] = block
    cm.verify_declared_module(block, result, repo_root=Path(repo_root))
    if data_root is not None:
        from .knowledge_stores import load_knowledge_store_binding
        binding = load_knowledge_store_binding(result, data_root=Path(data_root))
        covered = {sid for s in d["cumulative_sources"] for sid in s["sample_ids"]}
        require(all(sid in covered for store in binding.stores.values()
                    for value in store.snapshot.values for sid in value.source_sample_ids),
                "released knowledge ancestry is missing from policy")
    # Compilation happens before publication, so invalid joint edits leave no artifacts.
    for path, raw in staged:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(raw)
    return result
