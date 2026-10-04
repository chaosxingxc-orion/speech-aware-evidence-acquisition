"""Prospective equal-budget sequence transition with immutable predecessor custody.

Copy only already closed allocation records. Held predecessor inputs stay at their
original address and never become spent, responses, or replacement opportunities.
A transition allocates four new proposals; provider and runtime admission remain separate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from .hashing import content_hash
from .system_text_policy import _pin, _read_pin, require, sha

OWNER227 = "docs/receipts/owner/2026-10-03-decision227-autonomous-engineering-before-8x400.json"
SCHEMA = "saea-system-search-successor-sequence-v1"
CONTEXT_SCHEMA = "saea-system-search-successor-sequence-v2"
NODE_SCHEMA = "saea-system-search-successor-sequence-v3"
SEED_SCHEMA = "saea-system-search-successor-sequence-v4"
SCHEMAS = (SCHEMA, CONTEXT_SCHEMA, NODE_SCHEMA, SEED_SCHEMA)
FIELDS = {"schema", "round", "owner", "transition", "previous_protocol", "earlier_allocations",
    "held_allocations", "model_version", "seed_bundle_id", "input_token_cap", "output_token_cap",
    "contact_cap", "editable", "no_runtime_authority", "sequence_id", "predecessor_archive",
    "successor_archive", "snapshot_files", "allocations"}
FOLDERS = {"input": "inputs", "response": "responses", "import": "imports"}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_successor(index, document):
    node_version = isinstance(document, dict) and document.get("schema") in (NODE_SCHEMA, SEED_SCHEMA)
    context_version = node_version or (isinstance(document, dict) and document.get("schema") == CONTEXT_SCHEMA)
    fields = FIELDS | {"context_authority"} if context_version else FIELDS
    if isinstance(document, dict) and document.get("schema") == SEED_SCHEMA:
        fields = fields | {"seed_transition"}
        _require_seed_transition(document["seed_transition"])
    require(isinstance(document, dict) and set(document) == fields
        and document["schema"] in SCHEMAS and type(index) is int and index > 3
        and type(document["round"]) is int and document["round"] == index, "registered successor sequence required")
    require(document["no_runtime_authority"] is True
        and document["editable"] == (["role_text", "context_layout", "node_context"] if node_version else
                                 ["role_text", "context_layout"] if context_version else ["role_text"]),
        "successor is declared text/context proposal preparation only")
    if context_version:
        from .system_optimization import CONTEXT_AUTHORITY, NODE_AUTHORITY
        _pin(document["context_authority"])
        require(document["context_authority"]["relpath"] == (NODE_AUTHORITY if node_version else CONTEXT_AUTHORITY),
                "exact context-space owner receipt required")
    for key in ("owner", "transition", "previous_protocol"):
        _pin(document[key])
    require(document["owner"]["relpath"] == OWNER227, "exact owner227 authority required")
    require(isinstance(document["sequence_id"], str) and document["sequence_id"]
        and document["sequence_id"].isascii()
        and all(c.isalnum() or c in "-_" for c in document["sequence_id"]), "invalid sequence identity")
    sha(document["seed_bundle_id"])
    require(bool(document["model_version"]) and all(type(document[k]) is int and document[k] > 0
        for k in ("input_token_cap", "output_token_cap", "contact_cap")), "invalid successor bounds")
    expected = {f"{b}-{r}-{s}" for r in range(1, index) for b in ("L", "B") for s in (1, 2)}
    closed, held = document["earlier_allocations"], document["held_allocations"]
    require(isinstance(closed, dict) and isinstance(held, dict) and held
        and not (closed.keys() & held.keys()) and closed.keys() | held.keys() == expected,
        "closed and held allocations must partition the predecessor")
    for record in closed.values():
        require(isinstance(record, dict) and set(record) == set(FOLDERS), "invalid closed custody")
        for value in record.values():
            sha(value)
    for record in held.values():
        require(isinstance(record, dict) and set(record) == {"input"}, "held is not spent")
        sha(record["input"])
    require(document["allocations"] == [f"{b}-{index}-{s}" for s in (1, 2) for b in ("L", "B")],
        "successor allocates exactly four prospective slots")
    before, after = (Path(document[k]) for k in ("predecessor_archive", "successor_archive"))
    require(before.is_absolute() and after.is_absolute() and before.resolve() != after.resolve()
        and before.resolve() not in after.resolve().parents and after.resolve() not in before.resolve().parents,
        "successor requires a distinct isolated archive")
    require(isinstance(document["snapshot_files"], dict), "invalid immutable snapshot")
    for relative, value in document["snapshot_files"].items():
        path = Path(relative)
        require(not path.is_absolute() and ".." not in path.parts
            and path.parts[0] in {"inputs", "responses", "imports", "proposals", "policies", "allocations"}
            and len(path.parts) == 2 and path.suffix == ".json", "invalid snapshot path")
        sha(value)


def partition(predecessor, index, model):
    closed, held, files = {}, {}, {}
    # A later successor carries already verified HELD addresses transitively;
    # never copy a held input or invent a response merely to fill a round gap.
    inherited = {}
    prior_sequences = []
    for path in (predecessor.root / "allocations").glob("round-*.json"):
        candidate = json.loads(path.read_bytes())
        if candidate.get("schema") in SCHEMAS:
            require(type(candidate.get("round")) is int and candidate["round"] < index
                and path.name == f"round-{candidate['round']}.json", "invalid predecessor sequence order")
            prior_sequences.append(candidate)
    if prior_sequences:
        latest = max(prior_sequences, key=lambda d: d["round"])
        validate_successor(predecessor, latest)
        inherited = latest["held_allocations"]
    for r in range(1, index):
        for branch in ("L", "B"):
            for slot in (1, 2):
                key = f"{branch}-{r}-{slot}"
                path = predecessor.root / f"inputs/{key}.json"
                if not path.is_file():
                    require(key in inherited, "predecessor input is missing")
                    held[key] = dict(inherited[key])
                    continue
                packet = json.loads(path.read_bytes())
                require((packet.get("branch"), packet.get("round"), packet.get("slot")) == (branch, r, slot)
                    and packet.get("model_version") == model
                    and packet.get("input_sha256") == content_hash({k: v for k, v in packet.items() if k != "input_sha256"}),
                    "predecessor input identity differs")
                response_path = predecessor.root / f"responses/{key}.json"
                import_path = predecessor.root / f"imports/{key}.json"
                if not response_path.exists() and not import_path.exists():
                    require(not any((predecessor.root / folder / key).exists() for folder in ("dispatch",))
                        and not any((predecessor.root / folder / (key + ".json")).exists()
                            for folder in ("proposals", "compilations")), "held allocation has a reservation or outcome")
                    held[key] = {"input": digest(path)}
                    continue
                require(response_path.is_file() and import_path.is_file(), "predecessor allocation is not closed")
                response, imported = json.loads(response_path.read_bytes()), json.loads(import_path.read_bytes())
                require(imported.get("proposal_allocation") == [branch, r, slot]
                    and imported.get("input_sha256") == packet["input_sha256"]
                    and imported.get("receipt_sha256") == content_hash(response)
                    and imported.get("status") in {"invalid", "no-change", "duplicate", "provisional"},
                    "predecessor disposition differs")
                if imported["status"] != "invalid":
                    require(all(response.get(k) == packet[k] for k in ("model_version", "input_sha256", "session_id")),
                        "accepted predecessor response identity differs")
                closed[key] = {kind: digest(predecessor.root / folder / (key + ".json"))
                    for kind, folder in FOLDERS.items()}
                for kind, folder in FOLDERS.items():
                    files[f"{folder}/{key}.json"] = closed[key][kind]
                proposal = predecessor.root / f"proposals/{key}.json"
                if proposal.exists():
                    files[f"proposals/{key}.json"] = digest(proposal)
    for folder in ("policies", "allocations"):
        for path in sorted((predecessor.root / folder).glob("*.json")):
            files[f"{folder}/{path.name}"] = digest(path)
    return closed, held, files


def _require_seed_transition(value):
    require(isinstance(value, dict) and set(value) == {
        "receipt", "source_archive", "parent_bundle_id", "bundle_sha256"},
        "exact seed transition custody required")
    _pin(value["receipt"])
    sha(value["parent_bundle_id"])
    sha(value["bundle_sha256"])
    require(isinstance(value["source_archive"], str) and Path(value["source_archive"]).is_absolute(),
            "seed source archive must be absolute")


def transitioned_seed(predecessor, document, *, repo_root=None):
    """Verify an explicit behavior-preserving seed without modifying old archives."""
    from .system_search_archive import SystemSearchArchive
    from .system_text_policy import NODE_BUNDLE_SCHEMA, bind_four_node_seed
    desc = document["seed_transition"]
    _require_seed_transition(desc)
    source = SystemSearchArchive(desc["source_archive"])
    for target in (predecessor.root, Path(document["successor_archive"])):
        require(source.root.resolve() != target.resolve()
                and source.root.resolve() not in target.resolve().parents
                and target.resolve() not in source.root.resolve().parents,
                "seed source must be isolated from the sequence archives")
    path = source.root / "policies" / (document["seed_bundle_id"] + ".json")
    require(digest(path) == desc["bundle_sha256"], "seed source bytes changed")
    child = source.load_policy(document["seed_bundle_id"])
    parent = predecessor.load_policy(desc["parent_bundle_id"])
    d, old = child.as_json(), parent.as_json()
    require(d["schema"] == NODE_BUNDLE_SCHEMA and d["parent_ids"] == [parent.bundle_id]
            and not d["optimizer_experience"]
            and all(v["kind"] == "knowledge" for v in d["cumulative_sources"])
            and all(d[k] == v for k, v in old.items()
                    if k not in {"schema", "parent_ids", "role_text"})
            and all(d["role_text"].get(k) == v for k, v in old["role_text"].items()),
            "seed transition changed ancestry, old role bytes or blind evidence")
    if repo_root is not None:
        receipt = json.loads(_read_pin(desc["receipt"], repo_root))
        require(receipt.get("schema") == "saea-four-node-seed-transition-v1"
                and receipt.get("status") == "frozen-offline-seed"
                and receipt.get("runtime_admission") is False
                and receipt.get("parent_bundle_id") == parent.bundle_id
                and receipt.get("bundle_id") == child.bundle_id
                and receipt.get("authority") == document["context_authority"]
                and receipt.get("seed_bundle", {}).get("sha256") == desc["bundle_sha256"],
                "seed transition receipt differs")
        baseline = json.loads(_read_pin(receipt["original_seed_config"], repo_root))
        perception = _read_pin(receipt["source_perception"], repo_root)
        require(perception == d["role_text"]["perception"].encode("utf-8")
                and receipt["source_perception"]["relpath"] ==
                "configs/" + baseline["phase_material"]["perception"]["instruction_template"]
                and bind_four_node_seed(parent, baseline, repo_root=repo_root).as_json() == d,
                "seed transition is not the exact historical runtime policy")
    return child


def validate_successor(archive, document, *, repo_root=None, preparing=False):
    from .system_search_archive import SystemSearchArchive
    require_successor(document.get("round"), document)
    require(archive.root.resolve() == Path(document["successor_archive"]).resolve(), "successor archive differs")
    predecessor = SystemSearchArchive(document["predecessor_archive"])
    closed, held, files = partition(predecessor, document["round"], document["model_version"])
    require((closed, held, files) == (document["earlier_allocations"], document["held_allocations"], document["snapshot_files"]),
        "predecessor custody changed")
    for key in held:
        require(not any((archive.root / folder / (key + ".json")).exists()
            for folder in ("inputs", "responses", "imports", "proposals", "compilations"))
            and not (archive.root / "dispatch" / key).exists(), "held allocation cannot enter the successor")
    if not preparing:
        require(all((archive.root / p).is_file() and digest(archive.root / p) == value for p, value in files.items()),
            "successor snapshot changed")
    if document["schema"] == SEED_SCHEMA:
        seed = transitioned_seed(predecessor, document, repo_root=repo_root)
        if not preparing:
            require(archive.load_policy(seed.bundle_id).as_json() == seed.as_json(),
                    "published transitioned seed differs")
    elif document["schema"] == NODE_SCHEMA:
        from .system_text_policy import NODE_BUNDLE_SCHEMA
        seed = predecessor.load_policy(document["seed_bundle_id"])
        require(seed.as_json()["schema"] == NODE_BUNDLE_SCHEMA,
                "node successor requires an explicitly registered four-role seed; no implicit rebase")
    if repo_root is not None:
        owner = json.loads(_read_pin(document["owner"], repo_root))
        require(owner.get("decision_id") == 227 and owner.get("status") == "approved", "owner227 is not approved")
        previous = json.loads(_read_pin(document["previous_protocol"], repo_root))
        require(previous["proposer_exact_version"] == document["model_version"]
            and previous["seed_bundle"]["bundle_id"] == (document["seed_transition"]["parent_bundle_id"]
                if document["schema"] == SEED_SCHEMA else document["seed_bundle_id"])
            and previous["proposal_output_token_cap"] == document["output_token_cap"]
            and previous["proposal_contact_cap"] == document["contact_cap"], "successor changes a fixed factor")
        ancestor = previous.get("allocation_extension", {})
        if ancestor.get("schema") in SCHEMAS:
            path = predecessor.root / f"allocations/round-{ancestor['round']}.json"
            require(json.loads(path.read_bytes()) == ancestor, "pinned predecessor sequence differs")
        decision = json.loads(_read_pin(document["transition"], repo_root))
        require(decision.get("status") == "root-selected-for-preparation" and decision.get("dispatch_authority") is False
            and all(decision.get(k) == document[k] for k in ("round", "sequence_id", "input_token_cap", "output_token_cap", "contact_cap"))
            and set(decision.get("held_allocations", [])) == set(held)
            and decision.get("new_allocations") == document["allocations"], "exact root transition disposition required")
        require(decision.get("seed_transition") == document.get("seed_transition"),
                "successor seed transition differs from root disposition")
        require(decision.get("context_authority") == document.get("context_authority"),
                "successor context scope differs from root transition")
        if document["schema"] in (CONTEXT_SCHEMA, NODE_SCHEMA, SEED_SCHEMA):
            from .system_optimization import validate_context_authority
            validate_context_authority(document["context_authority"], repo_root=repo_root,
                                       node_version=document["schema"] in (NODE_SCHEMA, SEED_SCHEMA))
    return document


def build_successor(predecessor, successor, *, round_index, owner, transition, previous_protocol, repo_root, sequence_id):
    previous = json.loads(_read_pin(previous_protocol, repo_root))
    decision = json.loads(_read_pin(transition, repo_root))
    closed, held, files = partition(predecessor, round_index, previous["proposer_exact_version"])
    document = {"schema": SCHEMA, "round": round_index, "owner": owner, "transition": transition,
        "previous_protocol": previous_protocol, "earlier_allocations": closed, "held_allocations": held,
        "model_version": previous["proposer_exact_version"], "seed_bundle_id": previous["seed_bundle"]["bundle_id"],
        "input_token_cap": decision["input_token_cap"], "output_token_cap": previous["proposal_output_token_cap"],
        "contact_cap": previous["proposal_contact_cap"], "editable": ["role_text"], "no_runtime_authority": True,
        "sequence_id": sequence_id, "predecessor_archive": str(predecessor.root.resolve()),
        "successor_archive": str(successor.root.resolve()), "snapshot_files": files,
        "allocations": [f"{b}-{round_index}-{s}" for s in (1, 2) for b in ("L", "B")]}
    if "context_authority" in decision:
        from .system_optimization import NODE_AUTHORITY
        node_version = decision["context_authority"]["relpath"] == NODE_AUTHORITY
        document.update(schema=NODE_SCHEMA if node_version else CONTEXT_SCHEMA,
                        editable=["role_text", "context_layout", "node_context"] if node_version else ["role_text", "context_layout"],
                        context_authority=decision["context_authority"])
    if "seed_transition" in decision:
        require(document["schema"] == NODE_SCHEMA, "seed transition needs four-node scope")
        desc = decision["seed_transition"]
        _require_seed_transition(desc)
        receipt = json.loads(_read_pin(desc["receipt"], repo_root))
        document.update(schema=SEED_SCHEMA, seed_transition=desc, seed_bundle_id=receipt["bundle_id"])
    return validate_successor(successor, document, repo_root=repo_root, preparing=True)


def register_successor(predecessor, successor, document, *, repo_root):
    require(predecessor.root.resolve() == Path(document["predecessor_archive"]).resolve(), "predecessor archive differs")
    validate_successor(successor, document, repo_root=repo_root, preparing=True)
    require(not successor.root.exists(), "successor archive already exists")
    successor.root.mkdir(parents=True)
    for relative in document["snapshot_files"]:
        destination = successor.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with (predecessor.root / relative).open("rb") as source, destination.open("xb") as output:
            shutil.copyfileobj(source, output)
    if document["schema"] == SEED_SCHEMA:
        successor.store_policy(transitioned_seed(predecessor, document, repo_root=repo_root))
    validate_successor(successor, document, repo_root=repo_root)
    successor._write(f"allocations/round-{document['round']}.json", document)
