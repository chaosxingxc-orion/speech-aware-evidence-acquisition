"""Register bounded extra text proposals without resetting an existing search.

These records allocate proposal slots only. They do not admit a provider contact,
GPU flight, retry, scientific read, larger sample panel, or new feedback source.
"""

from __future__ import annotations

import hashlib
import json

from .hashing import content_hash
from .system_text_policy import _pin, _read_pin, require, sha

OWNER223 = "docs/receipts/owner/2026-10-02-decision223-progressive-learning-ladder.json"
SCHEMA = "saea-system-search-allocation-extension-v1"
FIELDS = {
    "schema",
    "round",
    "owner",
    "previous_protocol",
    "earlier_allocations",
    "model_version",
    "seed_bundle_id",
    "input_token_cap",
    "output_token_cap",
    "contact_cap",
    "editable",
    "no_runtime_authority",
}


def require_round(round_index, extension=None):
    """Keep the original three rounds closed unless an exact extension is supplied."""
    require(type(round_index) is int and round_index > 0, "invalid proposal round")
    if round_index <= 3:
        require(extension is None, "original round cannot borrow an extension")
        return
    from .system_search_successor import SCHEMAS as SUCCESSORS, require_successor
    if isinstance(extension, dict) and extension.get("schema") in SUCCESSORS:
        require_successor(round_index, extension)
        return
    require(
        isinstance(extension, dict)
        and set(extension) == FIELDS
        and extension.get("schema") == SCHEMA
        and type(extension.get("round")) is int
        and extension["round"] == round_index,
        "registered round extension required",
    )
    require(
        extension["no_runtime_authority"] is True
        and extension["editable"] == ["role_text"],
        "extension is role-text proposal allocation only",
    )
    _pin(extension["owner"])
    _pin(extension["previous_protocol"])
    require(
        extension["owner"]["relpath"] == OWNER223, "exact owner223 authority required"
    )
    require(
        isinstance(extension["model_version"], str) and extension["model_version"],
        "pin extension proposer",
    )
    sha(extension["seed_bundle_id"])
    require(
        all(
            type(extension[k]) is int and extension[k] > 0
            for k in ("input_token_cap", "output_token_cap", "contact_cap")
        ),
        "invalid extension budget",
    )
    expected = {
        f"{b}-{r}-{s}"
        for r in range(1, round_index)
        for b in ("L", "B")
        for s in (1, 2)
    }
    require(
        isinstance(extension["earlier_allocations"], dict)
        and set(extension["earlier_allocations"]) == expected,
        "complete spent allocation history required",
    )
    for pins in extension["earlier_allocations"].values():
        require(
            isinstance(pins, dict) and set(pins) == {"input", "response", "import"},
            "invalid spent allocation pins",
        )
        for digest in pins.values():
            sha(digest)


def require_packet_allocation(packet, protocol):
    """Join a packaged allocation digest to a trusted registered protocol."""
    round_index = packet["round"]
    extension = protocol.get("allocation_extension") if round_index > 3 else None
    require_round(round_index, extension)
    require(
        packet.get("allocation_extension_sha256")
        == (content_hash(extension) if extension else None),
        "proposal allocation extension differs",
    )
    if extension:
        require(
            packet["model_version"] == extension["model_version"]
            and packet["seed_bundle_id"] == extension["seed_bundle_id"]
            and packet["input_token_cap"] == extension["input_token_cap"]
            and packet["output_token_cap"] == extension["output_token_cap"],
            "extension model or budgets differ",
        )
        if "optimization_scope" in packet:
            scope = packet["optimization_scope"]
            require(scope["editable"] == extension["editable"]
                    and scope.get("context_authority_sha256") == extension.get("context_authority", {}).get("sha256"),
                    "extension context scope differs")


def require_packet_round_shape(packet):
    """Validate packaging syntax only; dispatch independently resolves authority."""
    index = packet.get("round")
    require(type(index) is int and index > 0, "invalid proposal round")
    if index <= 3:
        require(
            "allocation_extension_sha256" not in packet, "original round has extension"
        )
    else:
        sha(packet.get("allocation_extension_sha256", ""))


def _spent(archive, round_index, model_version):
    pins = {}
    for r in range(1, round_index):
        for branch in ("L", "B"):
            for slot in (1, 2):
                key = f"{branch}-{r}-{slot}"
                documents, hashes = {}, {}
                for kind, folder in (
                    ("input", "inputs"),
                    ("response", "responses"),
                    ("import", "imports"),
                ):
                    path = archive.root / folder / (key + ".json")
                    require(path.is_file(), "prior proposal allocation is not closed")
                    raw = path.read_bytes()
                    documents[kind] = json.loads(raw)
                    hashes[kind] = hashlib.sha256(raw).hexdigest()
                packet, response, imported = (
                    documents[k] for k in ("input", "response", "import")
                )
                require(
                    (packet["branch"], packet["round"], packet["slot"])
                    == (branch, r, slot)
                    and packet["input_sha256"]
                    == content_hash(
                        {k: v for k, v in packet.items() if k != "input_sha256"}
                    )
                    and packet["model_version"] == model_version
                    and imported["proposal_allocation"] == [branch, r, slot]
                    and imported["input_sha256"] == packet["input_sha256"]
                    and imported["receipt_sha256"] == content_hash(response)
                    and imported["status"]
                    in {"invalid", "no-change", "duplicate", "provisional"},
                    "prior allocation identity or disposition differs",
                )
                if imported["status"] != "invalid":
                    require(
                        response.get("model_version") == packet["model_version"]
                        and response.get("input_sha256") == packet["input_sha256"]
                        and response.get("session_id") == packet["session_id"],
                        "accepted response identity differs",
                    )
                pins[key] = hashes
    return pins


def validate_extension(archive, extension, *, repo_root=None):
    """Recheck authority when supplied and retain every prior input/response/disposition."""
    require_round(extension.get("round"), extension)
    from .system_search_successor import SCHEMAS as SUCCESSORS, validate_successor
    if extension["schema"] in SUCCESSORS:
        return validate_successor(archive, extension, repo_root=repo_root)
    require(
        extension["earlier_allocations"]
        == _spent(archive, extension["round"], extension["model_version"]),
        "spent allocation evidence changed",
    )
    if repo_root is not None:
        owner = json.loads(_read_pin(extension["owner"], repo_root))
        require(
            owner.get("decision_id") == 223 and owner.get("status") == "approved",
            "owner223 is not approved",
        )
        previous = json.loads(_read_pin(extension["previous_protocol"], repo_root))
        require(
            previous["proposer_exact_version"] == extension["model_version"]
            and previous["seed_bundle"]["bundle_id"] == extension["seed_bundle_id"]
            and previous["proposal_input_token_cap"] == extension["input_token_cap"]
            and previous["proposal_output_token_cap"] == extension["output_token_cap"]
            and previous["proposal_contact_cap"] == extension["contact_cap"],
            "extension changes proposer or budgets",
        )
        previous_extension = previous.get("allocation_extension")
        if extension["round"] > 4:
            require(
                previous_extension
                == archive.allocation_extension(extension["round"] - 1),
                "extension must continue the preceding registered round",
            )
        else:
            require(
                previous_extension is None,
                "first extension cannot reset a prior extension",
            )
    return extension


def build_extension(archive, *, round_index, owner, previous_protocol, repo_root):
    """Prepare a reviewable allocation record without writing or spending a slot."""
    require(
        type(round_index) is int and round_index > 3,
        "extension starts after original rounds",
    )
    previous = json.loads(_read_pin(previous_protocol, repo_root))
    document = {
        "schema": SCHEMA,
        "round": round_index,
        "owner": owner,
        "previous_protocol": previous_protocol,
        "earlier_allocations": _spent(
            archive, round_index, previous["proposer_exact_version"]
        ),
        "model_version": previous["proposer_exact_version"],
        "seed_bundle_id": previous["seed_bundle"]["bundle_id"],
        "input_token_cap": previous["proposal_input_token_cap"],
        "output_token_cap": previous["proposal_output_token_cap"],
        "contact_cap": previous["proposal_contact_cap"],
        "editable": ["role_text"],
        "no_runtime_authority": True,
    }
    return validate_extension(archive, document, repo_root=repo_root)


def register_extension(archive, extension, *, repo_root):
    """Create a prospective record; reject any already-opened slot or prior mutation."""
    validate_extension(archive, extension, repo_root=repo_root)
    r = extension["round"]
    for folder in (
        "inputs",
        "responses",
        "imports",
        "proposals",
        "compilations",
        "dispatch",
    ):
        for branch in ("L", "B"):
            require(
                not list((archive.root / folder).glob(f"{branch}-{r}-*")),
                "extension round already opened",
            )
    archive._write(f"allocations/round-{r}.json", extension)
