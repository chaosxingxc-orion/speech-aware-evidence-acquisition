#!/usr/bin/env python3
"""CLI: build the Audio2Tool KNOWLEDGE INDEX construction view.

Item E28 (2026-09-21; design
``docs/superpowers/specs/2026-09-21-a2t-engineering-base-index-design.md``
sections 3 and 4, the paragraph beginning "E28 --"). Modelled directly on
``scripts/build_slurp_knowledge_index_view.py`` (item E21/E24): same
three-file release shape, same ``--twin-seed`` derangement-twin contract,
same refusal discipline. This is the AUDIO2TOOL instance: the 152-tool
registry, grouped by its 3 domains, as a knowledge INDEX.

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
tokenizer, scorer, GPU or network contacts. Every byte this script reads is
either the pinned ``tools_registry.csv`` (construction data: tool names,
signatures, descriptions, domains -- never a query, never a gold tool call)
or the two RELEASED knowledge stores ``tool-activation-scope-v1`` and
``parameter-meaning-v1``, each read through its own declared sha256 pin.
Nothing is embedded, nothing is re-encoded, and no server is contacted. The
union-4000 sealed roster and the calibration-400 roster -- and their gold
tool calls -- are NEVER read by this script (the design's construction
exclusion): it has no code path that opens a probe-sample receipt, a tier
manifest or an official-gold reader.

The output is the pinned view the constant index is built from
(``rails.knowledge_index``), in the three-file shape every released semantic
view already uses::

    <out-root>/knowledge/audio2tool/semantic/a2t-knowledge-index-v1/snapshot.json
    .../release.json
    .../completion.json

``--out-root`` is REQUIRED and has no default, for the same reason the SLURP
builder's is: the release job passes ``$SPEECHRL_DATA_DIR``; every other run
passes a scratch directory, so this builder can never write into the
controlled data root by accident.

WHAT THE VIEW CARRIES, and where each field comes from:

* ``domain`` entries (3, one per ``tools_registry.csv`` domain column value:
  ``smart_car``, ``smart_home``, ``wearables``). L0 line is the domain header
  text (``SMART CAR`` etc, ``data.audio2tool_tools.render_registry_grouped``'s
  own header spelling); no L1 or L2 content for v1 -- the ``l1`` mapping this
  builder writes carries one placeholder section ("Header") the object model
  requires to be non-empty but that the profile's ``domain`` default
  granularity (``L0``) never asks a renderer to read.
* ``tool`` entries (152, one per registry row). ``group`` is the tool's
  domain. ``l1`` carries ``Activation boundary`` (the ``tool-activation-
  scope-v1`` store's own value text for this tool, read verbatim) and
  ``Admissible arguments`` (this builder's own rendering of the registry's
  parsed signature types and constraint brackets, via the same parsing
  ``data.audio2tool_tools`` already uses for the OpenAI tool schema). The
  L2 card (``residue``) is this builder's own text: the registry description,
  the raw constraints, and the ``parameter-meaning-v1`` store's own value
  text for this tool, verbatim.
* ``edge`` entries -- GOLD-FREE, authored from the registry STRUCTURE alone
  (the design's own rule, pinned here as ``EDGE_RULE`` and recorded in the
  release under ``edge_rule``): two tools of the SAME domain form an edge
  when their signatures share at least one argument name, OR their
  descriptions share at least three CONTENT TOKENS (lowercased, alphabetic,
  length >= 4, stopwords removed). Exactly one edge per unordered pair
  (the lexicographically smaller ``tool_name`` is the edge's ``source``);
  the L0 line and the folded ``Confusable exclusions`` line both name the
  two tools and the shared signal (argument names, or shared tokens).
* the ``exemplar`` kind is NOT built in v1 (owner decision 66, recommended):
  no construction-exemplar store is read or referenced.

Ordering: ``domain-alphabetical-v1`` (``rails.knowledge_index.
domain_alphabetical_order``) -- every entry's ``group``/``entry_id`` pair
sorts consistently: a domain's own entry, its edges and its tools interleave
by plain string order within the group, and groups sort by domain name.

THE DERANGEMENT TWIN (item E24's contract, reused verbatim for this carrier).
``--twin-seed <int>`` builds ``a2t-knowledge-index-twin-v1`` instead: the SAME
entries, ids, groups, ranks and ordering as the source view, with ONLY the
per-entry L1 lines and their L2 cards permuted ACROSS IDS WITHIN EACH KIND by
a Sattolo derangement seeded by that integer (domain/tool/edge deranged
separately; zero fixed points). Before it writes a byte the twin build proves
T1 (zero fixed points, by content), T2 (the per-kind multiset of L1 lines and
L2 cards is unchanged) and T3 (this builder's own rendering, at the profile's
default granularity, has the SAME character count on both arms, because the
header states the SOURCE view id on both -- ``KnowledgeIndexTable.
header_view_id``).

Refuses to overwrite an existing release directory unless ``--force`` is
given (deliberately stricter than the SLURP builder, whose release job never
re-runs against a populated directory by convention alone).

Usage::

    python scripts/build_a2t_knowledge_index_view.py --out-root <dir>
    python scripts/build_a2t_knowledge_index_view.py --out-root <dir> --check
    python scripts/build_a2t_knowledge_index_view.py --out-root <dir> \\
        --twin-seed 20260921
    python scripts/build_a2t_knowledge_index_view.py --out-root <dir> \\
        --twin-seed 20260921 --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    load_tool_registry_with_sha256,
)
from speech_aware_evidence_acquisition.data.audio2tool_tools import (  # noqa: E402
    _build_parameter_schema,
    _parse_constraints,
    _parse_signature,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    lock_entry,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.knowledge_index import (  # noqa: E402
    KNOWLEDGE_INDEX_COMPLETION_SCHEMA,
    KNOWLEDGE_INDEX_RELEASE_SCHEMA,
    KNOWLEDGE_INDEX_VIEW_SCHEMA,
    DOMAIN_ALPHABETICAL_ORDERING,
    IndexEntry,
    derange_snapshot,
    domain_alphabetical_order,
    domain_id,
    edge_id,
    knowledge_index_profile,
    table_from_snapshot,
    tool_id,
    twin_line_multisets,
)

GENERATOR = "scripts/build_a2t_knowledge_index_view.py"
AUTHORITY = (
    "docs/superpowers/specs/2026-09-21-a2t-engineering-base-index-design.md "
    "sections 3 and 4 (item E28)"
)
LEDGER_ROW = "SAEA-A2T-E28-KNOWLEDGE-INDEX-VIEW-V1"
TWIN_LEDGER_ROW = "SAEA-A2T-E28-KNOWLEDGE-INDEX-TWIN-V1"

PROFILE = knowledge_index_profile("audio2tool")
VIEW_ID = "a2t-knowledge-index-v1"
TWIN_VIEW_ID = "a2t-knowledge-index-twin-v1"
NAMESPACE = f"knowledge/audio2tool/semantic/{VIEW_ID}"

EXPECTED_TOOLS = 152
EXPECTED_DOMAINS = 3

#: Item E28's pinned edge rule (design section 3): recorded verbatim in every
#: release so a reader never has to re-derive it from this script's body.
MIN_SHARED_TOKENS = 3
MIN_TOKEN_LENGTH = 4
EDGE_RULE = {
    "rule_id": "a2t-registry-structure-edge-v1",
    "statement": (
        "Two tools of the SAME domain form an edge when (a) their signatures "
        "share at least one argument name, OR (b) their descriptions share at "
        "least MIN_SHARED_TOKENS content tokens (lowercased, alphabetic only, "
        "length >= MIN_TOKEN_LENGTH, stopwords removed). Exactly one edge per "
        "unordered pair; the lexicographically smaller tool_name is the edge's "
        "source. Authored from the registry structure alone -- no evaluation "
        "roster, no gold tool call, ever enters this rule."
    ),
    "min_shared_tokens": MIN_SHARED_TOKENS,
    "min_token_length": MIN_TOKEN_LENGTH,
    "gold_free": True,
}

#: A small, fixed English stopword list -- deterministic, no external corpus,
#: no tokenizer. Only content tokens (length >= MIN_TOKEN_LENGTH already
#: excludes most function words) pass through, so this list only needs to
#: catch the common length->=4 function/generic words that would otherwise
#: manufacture spurious edges (e.g. two unrelated tools both mentioning
#: "this", "that", "with").
STOPWORDS = frozenset({
    "this", "that", "these", "those", "with", "from", "into", "onto", "than",
    "then", "when", "what", "which", "while", "will", "would", "could",
    "should", "there", "their", "they", "them", "your", "you're", "have",
    "has", "had", "does", "done", "being", "been", "were", "was", "are",
    "the", "and", "for", "not", "can", "its", "it's", "over", "under",
    "between", "current", "specific", "specified", "given", "provided",
    "sets", "set", "gets", "get", "changes", "change", "value", "values",
    "target", "based", "using", "used", "also", "only", "each", "such",
    "about", "within", "across", "before", "after", "returns", "return",
})
_TOKEN_RE = re.compile(r"[a-z]+")


def content_tokens(text: str) -> frozenset[str]:
    return frozenset(
        token for token in _TOKEN_RE.findall(text.lower())
        if len(token) >= MIN_TOKEN_LENGTH and token not in STOPWORDS
    )


def signature_arg_names(tool_name: str, signature: str) -> tuple[str, ...]:
    params = _parse_signature(tool_name, signature)
    return tuple(name for name, _base_type, _optional in params)


def admissible_arguments_text(row: dict[str, str]) -> str:
    """This builder's own rendering of ``Admissible arguments`` -- the
    parameter names/types/enumerations of the registry's parsed signature and
    constraint bracket, reusing ``data.audio2tool_tools``'s own signature and
    constraint parser (the same 152-row registry, the same quirks: HsbColor's
    compound constraint, quoted-comma defaults, the ``?`` nullable marker)."""

    tool_name = row["tool_name"]
    params = _parse_signature(tool_name, row["signature"])
    constraints = _parse_constraints(row["argument_constraints"])
    if not params:
        return "(no arguments)"
    pieces: list[str] = []
    for name, base_type, optional in params:
        schema = _build_parameter_schema(
            name=name, base_type=base_type, optional=optional,
            defaults={}, constraints=constraints,
        )
        piece = f"{name}: {base_type}{'?' if optional else ''}"
        if "enum" in schema:
            piece += " [" + ", ".join(str(v) for v in schema["enum"]) + "]"
        elif "minimum" in schema:
            piece += f" [{schema['minimum']}-{schema['maximum']}]"
        elif schema.get("type") == "array" and "items" in schema:
            items = schema["items"]
            if "enum" in items:
                piece += " [" + ", ".join(str(v) for v in items["enum"]) + "]"
            elif "minimum" in items:
                piece += f" [{items['minimum']}-{items['maximum']}]"
        elif name in constraints:
            piece += f" [{constraints[name]}]"
        pieces.append(piece)
    return "; ".join(pieces)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(document: object) -> bytes:
    return json.dumps(
        document, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(document: object) -> str:
    return hashlib.sha256(_canonical_bytes(document)).hexdigest()


def relpaths(view_id: str) -> dict[str, str]:
    namespace = f"knowledge/audio2tool/semantic/{view_id}"
    return {
        "snapshot": f"{namespace}/snapshot.json",
        "release": f"{namespace}/release.json",
        "completion": f"{namespace}/completion.json",
    }


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def read_named_store(root: Path, store_dir_name: str) -> tuple[dict[str, str], dict[str, object]]:
    """One released ``knowledge/audio2tool/<store_dir_name>/`` store: its
    per-tool ``values[].content`` text, keyed by ``tool_name``, and the pin
    record this build cites in its own release.

    The store's release lives at ``knowledge/audio2tool/<store_dir_name>/
    release.json``; its ACTUAL bulk content (the ``KnowledgeSnapshot``
    document ``release.json`` names by content hash) is materialised under
    ``prepared/<SOURCE-NAME>/knowledge-snapshot.json`` per the
    ``completion.json`` alongside the release -- the standard
    consolidate-then-dispose layout this repository's compiled knowledge
    stores use. Both files are read through their own declared sha256 before
    a byte of content is trusted.
    """

    store_root = root / "knowledge" / "audio2tool" / store_dir_name
    release_path = store_root / "release.json"
    completion_path = store_root / "completion.json"
    if not release_path.is_file() or not completion_path.is_file():
        raise SystemExit(
            f"REFUSED: released store {store_dir_name!r} is missing its release/"
            f"completion under {store_root}"
        )
    release_sha256 = _sha256_path(release_path)
    release = _read_json(release_path)
    completion_sha256 = _sha256_path(completion_path)
    completion = _read_json(completion_path)
    if not isinstance(release, dict) or not isinstance(completion, dict):
        raise SystemExit(f"REFUSED: {store_dir_name} release/completion is not a JSON object")
    if completion.get("release", {}).get("sha256") != release_sha256:
        raise SystemExit(
            f"REFUSED: {store_dir_name} completion.json does not pin the release "
            "bytes actually on disk"
        )
    snapshot_pin = completion.get("snapshot")
    if not isinstance(snapshot_pin, dict) or "relpath" not in snapshot_pin:
        raise SystemExit(f"REFUSED: {store_dir_name} completion.json carries no snapshot pin")
    snapshot_path = root / str(snapshot_pin["relpath"])
    if not snapshot_path.is_file():
        raise SystemExit(f"REFUSED: {store_dir_name} snapshot missing: {snapshot_path}")
    snapshot_file_sha256 = _sha256_path(snapshot_path)
    if snapshot_file_sha256 != completion.get("snapshot_file_sha256"):
        raise SystemExit(
            f"REFUSED: {store_dir_name} knowledge-snapshot.json hashes to "
            f"{snapshot_file_sha256}, not the completion-pinned "
            f"{completion.get('snapshot_file_sha256')}"
        )
    from speech_aware_evidence_acquisition.rails.knowledge_stores import (
        KnowledgeSnapshot,
    )

    snapshot_document = _read_json(snapshot_path)
    measured_content_hash = KnowledgeSnapshot.from_frozen_json(
        snapshot_document
    ).content_hash()
    if measured_content_hash != release.get("snapshot_sha256"):
        raise SystemExit(
            f"REFUSED: {store_dir_name} snapshot content hashes to "
            f"{measured_content_hash}, not the release-pinned "
            f"{release.get('snapshot_sha256')}"
        )
    values_by_tool: dict[str, str] = {}
    prefix, suffix = "a2t-native-card:", ":value"
    for value in snapshot_document["values"]:
        value_id = str(value["value_id"])
        if not (value_id.startswith(prefix) and value_id.endswith(suffix)):
            raise SystemExit(
                f"REFUSED: {store_dir_name} value id {value_id!r} is not the "
                f"expected {prefix}<tool_name>{suffix} shape"
            )
        tool_name = value_id[len(prefix): -len(suffix)]
        if tool_name in values_by_tool:
            raise SystemExit(f"REFUSED: {store_dir_name} has a duplicate tool {tool_name!r}")
        values_by_tool[tool_name] = str(value["content"])
    pin_record = {
        "store_role": str(release.get("store_role", store_dir_name)),
        "release": {
            "relpath": f"knowledge/audio2tool/{store_dir_name}/release.json",
            "root": "data", "sha256": release_sha256,
        },
        "snapshot": {
            "relpath": str(snapshot_pin["relpath"]), "root": "data",
            "sha256": snapshot_file_sha256,
        },
        "snapshot_content_hash": measured_content_hash,
    }
    return values_by_tool, pin_record


def build_edges(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Every gold-free edge the registry structure admits (design section 3,
    ``EDGE_RULE``): one per unordered same-domain pair sharing an argument
    name or >= MIN_SHARED_TOKENS content tokens. Deterministic: pairs are
    walked in sorted ``tool_name`` order within each domain."""

    by_domain: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_domain.setdefault(row["domain"], []).append(row)
    edges: list[dict[str, object]] = []
    for _domain, domain_rows in sorted(by_domain.items()):
        ordered = sorted(domain_rows, key=lambda row: row["tool_name"])
        arg_names = {
            row["tool_name"]: frozenset(
                signature_arg_names(row["tool_name"], row["signature"])
            )
            for row in ordered
        }
        tokens = {
            row["tool_name"]: content_tokens(row["description"])
            for row in ordered
        }
        for index, left in enumerate(ordered):
            left_name = left["tool_name"]
            for right in ordered[index + 1:]:
                right_name = right["tool_name"]
                shared_args = sorted(arg_names[left_name] & arg_names[right_name])
                shared_tokens = sorted(tokens[left_name] & tokens[right_name])
                if not shared_args and len(shared_tokens) < MIN_SHARED_TOKENS:
                    continue
                source, neighbour = sorted((left_name, right_name))
                edges.append({
                    "source": source,
                    "neighbour": neighbour,
                    "domain": left["domain"],
                    "shared_arguments": shared_args,
                    "shared_tokens": (
                        shared_tokens if len(shared_tokens) >= MIN_SHARED_TOKENS else []
                    ),
                })
    return edges


def build_entries(
    rows: list[dict[str, str]],
    activation: dict[str, str],
    parameter_meaning: dict[str, str],
) -> list[IndexEntry]:
    domains = sorted({row["domain"] for row in rows})
    entries: list[IndexEntry] = []
    for domain in domains:
        entries.append(
            IndexEntry(
                entry_id=domain_id(domain),
                kind="domain",
                group=domain,
                rank=sum(1 for row in rows if row["domain"] == domain),
                l1={"Header": domain.upper().replace("_", " ")},
            )
        )
    for row in sorted(rows, key=lambda row: row["tool_name"]):
        tool_name = row["tool_name"]
        activation_text = activation.get(tool_name)
        if activation_text is None:
            raise SystemExit(
                f"REFUSED: tool-activation-scope-v1 carries no value for {tool_name!r}"
            )
        parameter_text = parameter_meaning.get(tool_name)
        if parameter_text is None:
            raise SystemExit(
                f"REFUSED: parameter-meaning-v1 carries no value for {tool_name!r}"
            )
        residue = (
            f"Description: {row['description']}\n"
            f"Constraints: {row['argument_constraints'] or '(none)'}\n"
            f"Parameter meaning:\n{parameter_text}"
        )
        entries.append(
            IndexEntry(
                entry_id=tool_id(tool_name),
                kind="tool",
                group=row["domain"],
                rank=0,
                l1={
                    "Activation boundary": activation_text,
                    "Admissible arguments": admissible_arguments_text(row),
                },
                residue=residue,
            )
        )
    for edge in build_edges(rows):
        signal = (
            f"shared argument(s): {', '.join(edge['shared_arguments'])}"
            if edge["shared_arguments"]
            else f"shared description token(s): {', '.join(edge['shared_tokens'])}"
        )
        statement = f"{edge['source']} vs {edge['neighbour']}: {signal}."
        entries.append(
            IndexEntry(
                entry_id=edge_id(edge["source"], edge["neighbour"]),
                kind="edge",
                group=edge["domain"],
                rank=len(edge["shared_arguments"]) + len(edge["shared_tokens"]),
                l1={"Confusable exclusions": statement},
            )
        )
    return entries


def build_documents(root: Path, lock_path: Path) -> dict[str, object]:
    started = time.monotonic()
    lock = load_lock(lock_path)
    entry = lock_entry(lock, AUDIO2TOOL_LOCK_KEY)
    carrier_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    registry_path = carrier_dir / "tools_registry.csv"
    rows, registry_sha256 = load_tool_registry_with_sha256(lock, root)
    if len(rows) != EXPECTED_TOOLS:
        raise SystemExit(
            f"REFUSED: tools_registry.csv carries {len(rows)} tools, not the "
            f"registered {EXPECTED_TOOLS}"
        )
    domains = sorted({row["domain"] for row in rows})
    if len(domains) != EXPECTED_DOMAINS:
        raise SystemExit(
            f"REFUSED: tools_registry.csv carries {len(domains)} domains "
            f"{domains}, not the registered {EXPECTED_DOMAINS}"
        )

    activation, activation_pin = read_named_store(root, "tool-activation-scope-v1")
    parameter_meaning, parameter_pin = read_named_store(root, "parameter-meaning-v1")

    entries = build_entries(list(rows), activation, parameter_meaning)
    counts = totals_from_entries(entries)
    if counts.get("domain", 0) != EXPECTED_DOMAINS or counts.get("tool", 0) != EXPECTED_TOOLS:
        raise SystemExit(
            f"REFUSED: built {counts.get('domain', 0)} domain and "
            f"{counts.get('tool', 0)} tool entries, not the registered "
            f"{EXPECTED_DOMAINS} and {EXPECTED_TOOLS}"
        )

    registry_relpath = f"{str(entry['local_subdir']).rstrip('/')}/tools_registry.csv"

    snapshot = {
        "schema": KNOWLEDGE_INDEX_VIEW_SCHEMA,
        "view_id": VIEW_ID,
        "builder_policy_id": "saea-a2t-knowledge-index-construction-v1",
        "carrier": "audio2tool",
        "ordering": DOMAIN_ALPHABETICAL_ORDERING,
        "source_split": "train",
        "source_split_identity_hash": registry_sha256,
        "construction_utterance_count": 0,
        "legal_intents": [],
        "legal_slot_types": [],
        "store_pins": {
            "tools_registry": {
                "relpath": registry_relpath, "root": "data", "sha256": registry_sha256,
            },
            "tool-activation-scope-v1": activation_pin,
            "parameter-meaning-v1": parameter_pin,
        },
        "shared_sections": [],
        "entries": [entry_obj.as_json() for entry_obj in entries],
    }
    return {"snapshot": snapshot, "timing_seconds": round(time.monotonic() - started, 3)}


def totals_from_entries(entries: list[IndexEntry]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.kind] = counts.get(entry.kind, 0) + 1
    return counts


def totals(snapshot: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in snapshot["entries"]:
        counts[entry["kind"]] = counts.get(entry["kind"], 0) + 1
    return counts


def render_a2t_constant_index(snapshot: dict, *, render_label: str = "") -> str:
    """This builder's OWN deterministic, model-free rendering of the view at
    the profile's default granularity (``tool`` L1 / ``domain`` L0 /
    ``edge`` L0). NOT ``rails.knowledge_index.render_constant_index``: that
    function is the SLURP prompt-fill renderer and item E28 declines to
    invent Audio2Tool prompt prose inside it (design section 4; a live
    episode's Audio2Tool rendering is item E29/E30). This function exists
    only to give the release a reproducible character count and sha256, and
    to prove the derangement twin's T3 (equal rendered length)."""

    table = table_from_snapshot(snapshot, render_label=render_label)
    tools_by_domain: dict[str, list] = {}
    edges_by_domain: dict[str, list] = {}
    domains: list = []
    for e in table.entries:
        if e.kind == "domain":
            domains.append(e)
        elif e.kind == "tool":
            tools_by_domain.setdefault(e.group, []).append(e)
        elif e.kind == "edge":
            edges_by_domain.setdefault(e.group, []).append(e)
    lines = [
        f"== Audio2Tool knowledge index ({table.header_view_id}), "
        f"ordering {table.ordering} =="
    ]
    for domain_entry in sorted(domains, key=lambda e: e.entry_id):
        from speech_aware_evidence_acquisition.rails.knowledge_index import (
            parse_index_id,
        )

        domain_name = parse_index_id(domain_entry.entry_id)[1][0]
        lines.append("")
        lines.append(f"{domain_entry.entry_id}  {domain_name.upper().replace('_', ' ')}")
        for tool_entry in sorted(tools_by_domain.get(domain_name, ()), key=lambda e: e.entry_id):
            lines.append(tool_entry.line(level="L1", section="Activation boundary"))
        for edge_entry in sorted(edges_by_domain.get(domain_name, ()), key=lambda e: e.entry_id):
            lines.append(edge_entry.line(level="L0", section=""))
    return "\n".join(lines)


def release_document(
    snapshot_sha256: str, snapshot: dict, *, builder_sha256: str, twin: dict | None = None,
) -> dict[str, object]:
    view_id = str(snapshot["view_id"])
    document: dict[str, object] = {
        "schema": KNOWLEDGE_INDEX_RELEASE_SCHEMA,
        "view_id": view_id,
        "builder_policy_id": snapshot["builder_policy_id"],
        "carrier": snapshot["carrier"],
        "ordering": snapshot["ordering"],
        "snapshot": {"relpath": relpaths(view_id)["snapshot"], "root": "data"},
        "snapshot_sha256": snapshot_sha256,
        "source": {
            "carrier": snapshot["carrier"],
            "split": snapshot["source_split"],
            "stores": snapshot["store_pins"],
        },
        "source_split_identity_hash": snapshot["source_split_identity_hash"],
        "edge_rule": EDGE_RULE,
        "builder": {
            "relpath": "scripts/build_a2t_knowledge_index_view.py",
            "sha256": builder_sha256,
        },
    }
    if twin is not None:
        document["twin_of"] = dict(twin["twin_of"])
        document["derangement"] = dict(twin["derangement"])
        document["gold_read"] = False
    return document


def completion_document(
    snapshot_sha256: str, release_sha256: str, snapshot: dict, *, twin: dict | None = None,
) -> dict[str, object]:
    view_id = str(snapshot["view_id"])
    paths = relpaths(view_id)
    statement = (
        "Authored from the pinned tools_registry.csv (152 tools, 3 domains) plus "
        "the two released knowledge stores tool-activation-scope-v1 and "
        "parameter-meaning-v1, each read through its own declared sha256 pin. "
        "Domain entries carry a header line only. Tool entries carry the "
        "activation-scope store's own text as their Activation boundary and "
        "this builder's own rendering of the registry's parsed signature and "
        "constraints as their Admissible arguments; their L2 card carries the "
        "registry description, the raw constraints and the parameter-meaning "
        "store's own text. Edges are authored from the registry STRUCTURE "
        "alone (edge_rule): no evaluation roster, no gold tool call and no "
        "construction-exemplar text is read, keyed on or conditioned upon "
        "anywhere in this build."
    )
    document: dict[str, object] = {
        "schema": KNOWLEDGE_INDEX_COMPLETION_SCHEMA,
        "view_id": view_id,
        "generator": GENERATOR if twin is None else f"{GENERATOR} --twin-seed",
        "authority": AUTHORITY,
        "exposure_ledger_row": LEDGER_ROW if twin is None else TWIN_LEDGER_ROW,
        "execution_profile": "model-free-check",
        "contacts": {"model": 0, "tool": 0, "scorer": 0, "encoder": 0, "tokenizer": 0},
        "release": {"relpath": paths["release"], "root": "data", "sha256": release_sha256},
        "snapshot": {"relpath": paths["snapshot"], "root": "data", "sha256": snapshot_sha256},
        "entry_counts": totals(snapshot),
        "source_split_identity_hash": snapshot["source_split_identity_hash"],
        "statement": statement if twin is None else (
            statement + " This view is the DERANGEMENT TWIN of "
            f"{twin['twin_of']['view_id']}: the same entries, ids, groups, "
            "ranks and rendered length, with the L1 lines and their L2 cards "
            "permuted across ids within each kind by a Sattolo derangement of "
            "the recorded seed (zero fixed points). It reads no gold and adds "
            "no knowledge: it destroys correspondence and holds form."
        ),
    }
    if twin is not None:
        document["twin_of"] = dict(twin["twin_of"])
        document["derangement"] = dict(twin["derangement"])
        document["gold_read"] = False
        document["form_match"] = dict(twin["form_match"])
    return document


def build_twin(source_snapshot: dict, *, seed: int) -> dict[str, object]:
    twin_snapshot, derangement = derange_snapshot(
        source_snapshot, seed=seed, view_id=TWIN_VIEW_ID,
        deranged_kinds=PROFILE.constant_index_kinds,
    )

    before = twin_line_multisets(source_snapshot)
    after = twin_line_multisets(twin_snapshot)
    if before != after:
        raise SystemExit(
            "REFUSED: the derangement changed a kind's multiset of L1 lines or "
            "L2 cards"
        )
    for field in ("id", "kind", "group", "rank"):
        if [row[field] for row in source_snapshot["entries"]] != [
            row[field] for row in twin_snapshot["entries"]
        ]:
            raise SystemExit(f"REFUSED: the derangement moved the entries' {field!r}")

    source_text = render_a2t_constant_index(source_snapshot)
    twin_text = render_a2t_constant_index(
        twin_snapshot, render_label=str(source_snapshot["view_id"])
    )
    if len(source_text) != len(twin_text):
        raise SystemExit(
            f"REFUSED: the twin renders {len(twin_text)} characters against the "
            f"source's {len(source_text)}"
        )
    if source_text == twin_text:
        raise SystemExit("REFUSED: the twin renders the SOURCE's text; nothing was deranged")
    source_lines = source_text.split("\n")
    twin_lines = twin_text.split("\n")
    moved = sum(1 for left, right in zip(source_lines, twin_lines) if left != right)
    return {
        "snapshot": twin_snapshot,
        "twin_of": {
            "view_id": str(source_snapshot["view_id"]),
            "snapshot_content_hash": _canonical_sha256(source_snapshot),
        },
        "derangement": derangement,
        "form_match": {
            "rendered_chars": len(twin_text),
            "source_rendered_chars": len(source_text),
            "rendered_lines": len(twin_lines),
            "reassigned_lines": moved,
            "rendered_sha256": hashlib.sha256(twin_text.encode("utf-8")).hexdigest(),
            "source_rendered_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "granularity": "the profile's default granularity (tool L1 / domain L0 / edge L0)",
        },
    }


def _write(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical_bytes(document)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--force", action="store_true",
                         help="overwrite an existing release directory")
    parser.add_argument("--twin-seed", type=int, default=None)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--lock", type=Path, default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    lock_path = (
        Path(args.lock).resolve() if args.lock is not None
        else umbrella_lock_path(repo_root)
    )
    root = data_root()
    out_root = Path(args.out_root).resolve()
    builder_sha256 = _sha256_path(Path(__file__).resolve())

    built = build_documents(root, lock_path)
    snapshot = built["snapshot"]
    twin: dict | None = None
    if args.twin_seed is not None:
        twin = build_twin(snapshot, seed=int(args.twin_seed))
        snapshot = twin["snapshot"]
    counts = totals(snapshot)

    paths = relpaths(str(snapshot["view_id"]))
    snapshot_path = out_root / paths["snapshot"]
    release_path = out_root / paths["release"]
    completion_path = out_root / paths["completion"]

    if args.check:
        for path in (snapshot_path, release_path, completion_path):
            if not path.is_file():
                print(f"MISSING: {path} is not released")
                return 1
        if json.loads(snapshot_path.read_text(encoding="utf-8")) != snapshot:
            print("DIFFERS: the released snapshot is not what this build produces")
            return 1
        snapshot_sha256 = _sha256_path(snapshot_path)
        if json.loads(release_path.read_text(encoding="utf-8")) != release_document(
            snapshot_sha256, snapshot, builder_sha256=builder_sha256, twin=twin
        ):
            print("DIFFERS: the released release is not what this build produces")
            return 1
        release_sha256 = _sha256_path(release_path)
        if json.loads(completion_path.read_text(encoding="utf-8")) != completion_document(
            snapshot_sha256, release_sha256, snapshot, twin=twin
        ):
            print("DIFFERS: the released completion is not what this build produces")
            return 1
        print(f"OK  entries={counts}  snapshot_sha256={snapshot_sha256[:16]}...")
        return 0

    if not args.force and (snapshot_path.is_file() or release_path.is_file() or completion_path.is_file()):
        print(
            f"REFUSED: {snapshot_path.parent} already carries a release; pass "
            "--force to overwrite"
        )
        return 1

    snapshot_sha256 = _write(snapshot_path, snapshot)
    release_sha256 = _write(
        release_path,
        release_document(snapshot_sha256, snapshot, builder_sha256=builder_sha256, twin=twin),
    )
    completion_sha256 = _write(
        completion_path,
        completion_document(snapshot_sha256, release_sha256, snapshot, twin=twin),
    )
    rendered = render_a2t_constant_index(
        snapshot, render_label="" if twin is None else str(twin["twin_of"]["view_id"])
    )
    print(f"wrote {paths['snapshot']}  sha256={snapshot_sha256}")
    print(f"wrote {paths['release']}  sha256={release_sha256}")
    print(f"wrote {paths['completion']}  sha256={completion_sha256}")
    print(f"  content_hash={_canonical_sha256(snapshot)}")
    print(f"  entries={counts}")
    print(f"  rendered_chars={len(rendered)}  rendered_sha256={hashlib.sha256(rendered.encode('utf-8')).hexdigest()}")
    print(f"  timing_seconds={built['timing_seconds']}")
    if twin is not None:
        record = twin["derangement"]
        form = twin["form_match"]
        print(f"  twin_of={twin['twin_of']['view_id']}@{twin['twin_of']['snapshot_content_hash']}")
        print(f"  derangement seed={record['seed']} kinds={record['kinds']} fixed_points={record['fixed_points']}")
        print(f"  permutation_sha256={record['permutation_sha256']}")
        print(f"  T3 rendered {form['rendered_chars']} chars against the source's {form['source_rendered_chars']}")
        print(f"  reassigned_lines={form['reassigned_lines']} of {form['rendered_lines']}")
    print(
        "  NOTE: no release-pins registration file was written; registering the "
        "release is a separate, zero-contact job."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
