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
CONTEXT_BUNDLE_SCHEMA = "saea-system-text-policy-bundle-v2"
CONTEXT_LAYOUT_FIELD = "native_role_query_placement"
PROPOSAL_SCHEMA = "saea-text-policy-update-proposal-v1"
CONTEXT_PROPOSAL_SCHEMA = "saea-text-policy-update-proposal-v2"
TEXT_CHARACTER_CAP = 32768
PROPOSAL_KEYS = frozenset({"schema", "branch", "round", "slot", "parent_ids",
                           "changes", "rationale", "hypotheses", "evidence"})
EDITABLE = frozenset({"construction_instruction", "role_text", "supply", "slot_value_edits"})
CONTEXT_EDITABLE = frozenset({"role_text", "context_layout"})
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
    require(len(value) <= TEXT_CHARACTER_CAP, "text exceeds registered character ceiling")
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


def _context_layout(value):
    require(isinstance(value, dict) and set(value) == {CONTEXT_LAYOUT_FIELD},
            "context layout fields differ")
    placement = value[CONTEXT_LAYOUT_FIELD]
    require(placement is None or (isinstance(placement, str) and placement == "before-speech-v1"),
            "context layout must select the historical or implemented before-speech placement")


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
        context_version = isinstance(document, dict) and document.get("schema") == CONTEXT_BUNDLE_SCHEMA
        fields = BUNDLE_KEYS | {"context_layout"} if context_version else BUNDLE_KEYS
        require(isinstance(document, dict) and set(document) == fields
                and document["schema"] in (BUNDLE_SCHEMA, CONTEXT_BUNDLE_SCHEMA), "policy bundle fields differ")
        d = copy.deepcopy(document)
        if context_version:
            _context_layout(d["context_layout"])
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
            require(old["schema"] != CONTEXT_BUNDLE_SCHEMA or context_version,
                    "context policy schema cannot downgrade; select historical layout explicitly")
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

    @staticmethod
    def schema_for_packet(packet):
        """Do not grant expanded proposal syntax to a historical input."""
        from .system_optimization import CONTEXT_SCOPE_SCHEMA, require_optimization_scope
        require_optimization_scope(packet)
        return (CONTEXT_PROPOSAL_SCHEMA
                if packet.get("optimization_scope", {}).get("schema") == CONTEXT_SCOPE_SCHEMA
                else PROPOSAL_SCHEMA)

    @staticmethod
    def response_contract(packet):
        """Describe exact proposal field types without repeating task evidence.

        This prospective description shares schema, field names and text limits
        with the validator. It never converts or repairs an old response.
        """
        editable = {
            "role_text": "object: optional solver/reviewer/planner keys, each an EnglishText replacement",
            "supply": "object: exactly mode (targeted|reread string), value_limit (integer1|2)",
            "construction_instruction": "EnglishText; requires a materialized knowledge release",
            "slot_value_edits": "object: schema string, base_rows_sha256 SHA256, edits array<object>; follow the indexed slot edit contract"}
        schema = TextPolicyUpdateProposal.schema_for_packet(packet)
        if schema == CONTEXT_PROPOSAL_SCHEMA:
            editable["context_layout"] = (
                "object: exactly native_role_query_placement; null keeps historical placement, "
                "before-speech-v1 places the complete role query before speech at user authority; "
                "no other ordering, truncation or generated code is implemented")
        allowed = packet.get("optimization_scope", {}).get("editable", sorted(EDITABLE))
        fields = {
            "schema": "string = example", "branch": "string = example",
            "round": "integer = example", "slot": "integer = example",
            "parent_ids": "nonempty array<SHA256>; allowed IDs; first as example",
            "changes": "object: optional editable_changes fields; {} means no change",
            "rationale": "EnglishText",
            "hypotheses": "array<EnglishText>; [] valid; never objects",
            "evidence": "array<JSON>; English text; cite sources; invent no evidence"}
        require(set(fields) == PROPOSAL_KEYS, "proposal field description differs from validator")
        example = {"schema": schema, "branch": packet["branch"], "round": packet["round"],
            "slot": packet["slot"], "parent_ids": [packet["parent_bundle_id"]], "changes": {},
            "rationale": "No supported revision.", "hypotheses": [], "evidence": []}
        rules = "Keep parent boundaries/control syntax. Invalid, duplicate and no-change spend the slot. Omni owns answers. No sample answers in runtime text."
        if schema == CONTEXT_PROPOSAL_SCHEMA:
            rules += (" Joint role text and declared context layout changes are allowed; knowledge, supply and code stay frozen. "
                      "Cache reuse is a measured cost, not an eligibility gate. Reused pool means optimization, not validation.")
        elif "optimization_scope" in packet:
            rules += " Only role text changes; knowledge, supply and code stay frozen. Reused pool means optimization, not validation."
        return {"contract_version": "typed-context-fields-v2" if schema == CONTEXT_PROPOSAL_SCHEMA else "typed-fields-v1",
            "format": "One JSON object, exactly the example fields; no Markdown.",
            "types": {"EnglishText": f"nonblank English string,1..{TEXT_CHARACTER_CAP} characters",
                "SHA256": "64 lowercase hexadecimal characters",
                "JSON": "object|array|string|number|boolean|null"},
            "field_types": fields, "editable_changes": {k: editable[k] for k in allowed},
            "example": example, "rules": rules}

    @classmethod
    def from_json(cls, d, *, allocation_extension=None):
        require(isinstance(d, dict) and set(d) == PROPOSAL_KEYS
                and d["schema"] in (PROPOSAL_SCHEMA, CONTEXT_PROPOSAL_SCHEMA), "proposal fields differ")
        from .system_search_allocations import require_round
        require_round(d["round"], allocation_extension)
        if allocation_extension is not None:
            expanded = allocation_extension["editable"] == ["role_text", "context_layout"]
            require((d["schema"] == CONTEXT_PROPOSAL_SCHEMA) == expanded,
                    "proposal schema differs from registered allocation scope")
        require(d["branch"] in {"L", "B"}
                and type(d["slot"]) is int and d["slot"] in (1, 2), "invalid proposal allocation")
        allowed = CONTEXT_EDITABLE if d["schema"] == CONTEXT_PROPOSAL_SCHEMA else EDITABLE
        require(isinstance(d["changes"], dict) and set(d["changes"]) <= allowed,
                "proposal changes an undeclared editable surface")
        if "context_layout" in d["changes"]:
            _context_layout(d["changes"]["context_layout"])
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
    if "context_layout" in changes:
        d["schema"] = CONTEXT_BUNDLE_SCHEMA
        d["context_layout"] = copy.deepcopy(changes["context_layout"])
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
    if "context_layout" in d:
        placement = d["context_layout"][CONTEXT_LAYOUT_FIELD]
        if placement is None:
            result.pop(CONTEXT_LAYOUT_FIELD, None)
        else:
            result[CONTEXT_LAYOUT_FIELD] = placement
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


def verify_system_text_binding(baseline, binding, *, repo_root, data_root):
    """Verify the actual role inputs against a pinned complete policy, before contact.

    This reads policy metadata and role templates only, never feedback or task
    outputs. It grants no execution or recovery authority. A seed must use the
    same compiler as a candidate; matching two stale baseline copies is not proof.
    """
    require(isinstance(binding, dict) and set(binding) == {"schema", "bundle_id", "bundle"}
            and binding["schema"] == "saea-system-text-role-binding-v1",
            "system text binding fields differ")
    require(isinstance(baseline, dict), "bound baseline must be an object")
    sha(binding["bundle_id"])
    document = json.loads(_read_pin(binding["bundle"], data_root))
    require(content_hash(document) == binding["bundle_id"], "bound policy identity differs")
    from .system_search_archive import SystemSearchArchive
    policy_path = Path(data_root) / binding["bundle"]["relpath"]
    require(policy_path.parent.name == "policies"
            and policy_path.name == binding["bundle_id"] + ".json",
            "bound policy must name its immutable archive identity")
    bundle = SystemSearchArchive(policy_path.parent.parent).load_policy(binding["bundle_id"])
    require(bundle.as_json() == document, "bound policy changed during verification")
    expected_layout = document.get("context_layout", {CONTEXT_LAYOUT_FIELD: None})
    require(baseline.get(CONTEXT_LAYOUT_FIELD) == expected_layout[CONTEXT_LAYOUT_FIELD],
            "bound context layout differs from actual runtime configuration")
    role_hashes = {}
    for role, text in document["role_text"].items():
        material = baseline.get("phase_material", {}).get(role, {})
        relative = f"probes/system-text-policy/{bundle.bundle_id}/{role}.txt"
        require(material.get("instruction_template") == relative,
                f"{role} role template does not bind the declared policy")
        role_path = (Path(repo_root) / "configs" / relative).resolve()
        require(role_path.is_relative_to(Path(repo_root).resolve()),
                "role template escaped repository")
        raw = role_path.read_bytes()
        require(raw == text.encode("utf-8"), f"{role} role bytes differ from declared policy")
        role_hashes[role] = hashlib.sha256(raw).hexdigest()
    from .consumption_module import ConsumptionModuleConfigError, verify_declared_module
    block = baseline.get("native_episode", {}).get("consumption_module", {})
    try:
        verify_declared_module(block, baseline, repo_root=Path(repo_root))
    except ConsumptionModuleConfigError as error:
        raise PolicyError(str(error)) from error
    components = [c for c in block.get("components", [])
                  if c.get("component_id") == "knowledge-consumption-opportunity"]
    require(len(components) == 1 and components[0].get("state") == "on",
            "bound knowledge opportunity is missing")
    params = components[0]["params"]
    require(all(params.get(role + "_template")
                == baseline["phase_material"][role]["instruction_template"]
                for role in role_hashes), "module and effective role templates differ")
    require(all(params.get(k) == v for k, v in document["supply"].items()),
            "bound supply configuration differs")
    store = baseline.get("knowledge_stores", {}).get(params["store_id"], {})
    require(all(store.get(k) == v for k, v in document["knowledge"].items()),
            "bound knowledge configuration differs")
    receipt = {"bundle_id": bundle.bundle_id, "role_sha256": role_hashes}
    if "context_layout" in document:
        receipt["context_layout"] = copy.deepcopy(expected_layout)
    return receipt
