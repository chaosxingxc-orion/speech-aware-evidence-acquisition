"""Pure, reference-only rendering of the frozen G6 action-family corpus.

``G6CorpusRenderer.from_path`` validates the complete frozen construction
registry before making it available.  ``render_family`` produces exactly one
ASCII family reference for a SCAN contact; it deliberately excludes operations,
defaults, examples, and any final-call instruction.  ``nominated_contracts``
and ``legal_key_sets`` are small adapter-facing lookups for validating a scan's
registered nominations without retrieval, ranking, model, network, scorer,
audio, or tokenizer work.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


_SCHEMA = "saea-action-family-contract-corpus-v1"
_PROHIBITED_FIELD_PARTS = ("evaluation", "sample", "gold", "score")
FAMILY_REFERENCE_ASCII_BYTE_CAP = 18_432


class G6CorpusRendererError(ValueError):
    """Raised when frozen corpus or scan-nomination invariants are violated."""


@dataclass(frozen=True)
class G6Contract:
    """One exact registered contract exposed to the G6 SCAN/RESOLVE adapter."""

    contract_id: str
    family_tag: str
    tool_name: str
    types: tuple[tuple[str, str], ...]
    constraints: str
    legal_key_skeletons: tuple[tuple[str, ...], ...]
    canonicalization_rules: tuple[str, ...]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise G6CorpusRendererError(f"{label} must be non-empty text")
    if not value.isascii():
        raise G6CorpusRendererError(f"{label} must be ASCII")
    return value


def _has_prohibited_field(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str) and any(
                part in key.casefold() for part in _PROHIBITED_FIELD_PARTS
            ):
                return True
            if _has_prohibited_field(nested):
                return True
    elif isinstance(value, list):
        return any(_has_prohibited_field(item) for item in value)
    return False


def _read_ascii_json(path: Path) -> tuple[bytes, Mapping[str, object]]:
    raw = Path(path).read_bytes()
    try:
        document = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise G6CorpusRendererError("corpus must be ASCII JSON") from error
    if not isinstance(document, Mapping):
        raise G6CorpusRendererError("corpus must be a JSON object")
    return raw, document


def _family_bundle_bytes(
    corpus: Mapping[str, object], *, tag: str, label: str, contracts: list[Mapping[str, object]]
) -> bytes:
    """Rebuild the committed G5 per-family aggregate for an identity check."""

    canonicalizers = corpus["canonicalizers"]
    payload = {
        "schema": "saea-exhaustive-action-family-bundle-v1",
        "families": [{"tag": tag, "label": label}],
        "output": "Return only a JSON array of exact registered tool calls.",
        "canonicalizers": dict(canonicalizers),
        "contracts": contracts,
    }
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


class G6CorpusRenderer:
    """Validated, deterministic adapter surface over all frozen corpus families.

    The renderer never reads speech, samples, scores, evaluation material, or
    model outputs.  A caller supplies only a family tag and optional exact tool
    names already nominated by that family-local SCAN report.
    """

    def __init__(
        self,
        *,
        corpus_sha256: str,
        labels: Mapping[str, str],
        contracts_by_family: Mapping[str, tuple[G6Contract, ...]],
        canonicalizers: Mapping[str, str],
    ) -> None:
        self.corpus_sha256 = corpus_sha256
        self._labels = dict(labels)
        self._contracts_by_family = dict(contracts_by_family)
        self._canonicalizers = dict(canonicalizers)
        self.family_tags = tuple(self._labels)
        self.contract_ids = tuple(
            contract.contract_id
            for family in self.family_tags
            for contract in self._contracts_by_family[family]
        )
        self.tool_names = tuple(
            contract.tool_name
            for family in self.family_tags
            for contract in self._contracts_by_family[family]
        )
        self._by_tool = {contract.tool_name: contract for contracts in self._contracts_by_family.values() for contract in contracts}

    @classmethod
    def from_path(cls, path: Path) -> "G6CorpusRenderer":
        """Load and fail-closed validate all 28 families and 152 contracts."""

        raw, corpus = _read_ascii_json(path)
        if corpus.get("schema") != _SCHEMA:
            raise G6CorpusRendererError("corpus schema drift")
        taxonomy = corpus.get("taxonomy")
        families = corpus.get("families")
        contracts = corpus.get("contracts")
        canonicalizers = corpus.get("canonicalizers")
        if not all(isinstance(value, list) for value in (taxonomy, families, contracts)):
            raise G6CorpusRendererError("corpus collections are malformed")
        if not isinstance(canonicalizers, Mapping) or not canonicalizers:
            raise G6CorpusRendererError("canonicalizers are malformed")
        canonicalizer_text = {
            _require_text(key, label="canonicalizer name"): _require_text(
                value, label="canonicalizer description"
            )
            for key, value in canonicalizers.items()
        }
        if len(canonicalizer_text) != len(canonicalizers):
            raise G6CorpusRendererError("canonicalizer names are duplicated")

        labels: dict[str, str] = {}
        for row in taxonomy:
            if not isinstance(row, Mapping):
                raise G6CorpusRendererError("taxonomy row is malformed")
            tag = _require_text(row.get("tag"), label="family tag")
            label = _require_text(row.get("label"), label="family label")
            if tag in labels:
                raise G6CorpusRendererError("family tags are duplicated")
            labels[tag] = label
        if len(labels) != 28:
            raise G6CorpusRendererError("corpus must register exactly 28 families")

        family_rows: dict[str, Mapping[str, object]] = {}
        for row in families:
            if not isinstance(row, Mapping):
                raise G6CorpusRendererError("family row is malformed")
            if _has_prohibited_field(row):
                raise G6CorpusRendererError(
                    "family contains prohibited evaluation/sample/gold/score field"
                )
            tag = _require_text(row.get("tag"), label="family row tag")
            if tag in family_rows:
                raise G6CorpusRendererError("family rows are duplicated")
            family_rows[tag] = row
        if set(family_rows) != set(labels):
            raise G6CorpusRendererError("taxonomy and family registry disagree")

        grouped: dict[str, list[Mapping[str, object]]] = {tag: [] for tag in labels}
        parsed: dict[str, list[G6Contract]] = {tag: [] for tag in labels}
        seen_ids: set[str] = set()
        seen_tools: set[str] = set()
        for row in contracts:
            if not isinstance(row, Mapping):
                raise G6CorpusRendererError("contract row is malformed")
            if _has_prohibited_field(row):
                raise G6CorpusRendererError("contract contains prohibited evaluation/sample/gold/score field")
            contract_id = _require_text(row.get("contract_id"), label="contract id")
            tag = _require_text(row.get("family_tag"), label="contract family tag")
            tool_name = _require_text(row.get("tool_name"), label="tool name")
            if tag not in grouped:
                raise G6CorpusRendererError("contract has unknown family")
            if contract_id in seen_ids or tool_name in seen_tools:
                raise G6CorpusRendererError("registered contracts are duplicated")
            seen_ids.add(contract_id)
            seen_tools.add(tool_name)
            types = row.get("types")
            skeletons = row.get("legal_key_skeletons")
            rules = row.get("canonicalization_rules")
            constraints = _require_text(row.get("constraints"), label="constraints")
            if not isinstance(types, list) or not isinstance(skeletons, list) or not isinstance(rules, list):
                raise G6CorpusRendererError("contract interface is malformed")
            typed = tuple(
                (_require_text(item[0], label="argument key"), _require_text(item[1], label="argument type"))
                for item in types
                if isinstance(item, list) and len(item) == 2
            )
            if len(typed) != len(types) or len({key for key, _kind in typed}) != len(typed):
                raise G6CorpusRendererError("contract types are malformed")
            legal_sets = tuple(
                tuple(_require_text(key, label="legal key") for key in skeleton)
                for skeleton in skeletons
                if isinstance(skeleton, list)
            )
            if len(legal_sets) != len(skeletons) or len(set(legal_sets)) != len(legal_sets):
                raise G6CorpusRendererError("legal key skeletons are malformed")
            typed_keys = {key for key, _kind in typed}
            if any(len(set(keys)) != len(keys) or not set(keys).issubset(typed_keys) for keys in legal_sets):
                raise G6CorpusRendererError("legal key skeleton is outside declared types")
            canonicalization_rules = tuple(
                _require_text(rule, label="canonicalization rule") for rule in rules
            )
            if not set(canonicalization_rules).issubset(canonicalizer_text):
                raise G6CorpusRendererError("contract names an unknown canonicalizer")
            grouped[tag].append(row)
            parsed[tag].append(
                G6Contract(contract_id, tag, tool_name, typed, constraints, legal_sets, canonicalization_rules)
            )
        if len(seen_ids) != 152:
            raise G6CorpusRendererError("corpus must register exactly 152 contracts")

        for tag, label in labels.items():
            row = family_rows[tag]
            declared_tools = row.get("tool_names")
            bundle_hash = row.get("bundle_sha256")
            bundle_bytes = _family_bundle_bytes(corpus, tag=tag, label=label, contracts=grouped[tag])
            if (
                not isinstance(declared_tools, list)
                or tuple(declared_tools) != tuple(contract.tool_name for contract in parsed[tag])
                or row.get("label") != label
                or row.get("bundle_utf8_bytes") != len(bundle_bytes)
                or bundle_hash != _sha256(bundle_bytes)
            ):
                raise G6CorpusRendererError("family registry drift")
        return cls(
            corpus_sha256=_sha256(raw),
            labels=labels,
            contracts_by_family={tag: tuple(parsed[tag]) for tag in labels},
            canonicalizers=canonicalizer_text,
        )

    def render_family(self, family_tag: str) -> str:
        """Render exactly one bounded ASCII reference, never task-value guidance."""

        if family_tag not in self._contracts_by_family:
            raise G6CorpusRendererError("unknown family")
        lines = [
            "REFERENCE-ONLY FAMILY MATERIAL",
            f"Family: {self._labels[family_tag]} ({family_tag})",
            "This material describes registered interfaces only; it supplies no task values.",
            "Canonicalizers:",
        ]
        lines.extend(
            f"- {name}: {description}"
            for name, description in self._canonicalizers.items()
        )
        for contract in self._contracts_by_family[family_tag]:
            lines.extend(("", f"Contract: {contract.contract_id}", f"Tool: {contract.tool_name}"))
            type_text = "; ".join(f"{key}: {kind}" for key, kind in contract.types) or "(none)"
            sets_text = " | ".join("{" + ", ".join(keys) + "}" for keys in contract.legal_key_skeletons)
            rules_text = ", ".join(contract.canonicalization_rules) or "(none)"
            lines.extend(
                (
                    f"Key types: {type_text}",
                    f"Legal key sets: {sets_text}",
                    f"Constraints: {contract.constraints}",
                    f"Applicable canonicalizers: {rules_text}",
                )
            )
        rendered = "\n".join(lines) + "\n"
        if not rendered.isascii():
            raise G6CorpusRendererError("rendered reference is not ASCII")
        if len(rendered.encode("ascii")) > FAMILY_REFERENCE_ASCII_BYTE_CAP:
            raise G6CorpusRendererError("rendered reference exceeds the byte cap")
        return rendered

    def nominated_contracts(
        self, family_tag: str, candidates: Sequence[str | Mapping[str, object]]
    ) -> tuple[G6Contract, ...]:
        """Return exact family-local contracts for unranked SCAN nominations.

        Empty candidates represent a SCAN abstention.  Structured candidates may
        contain only ``tool_name``; score, sample, gold, and evaluation material
        is rejected before any registry lookup.
        """

        if family_tag not in self._contracts_by_family:
            raise G6CorpusRendererError("unknown family")
        if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
            raise G6CorpusRendererError("candidates must be a sequence")
        names: list[str] = []
        for candidate in candidates:
            if isinstance(candidate, str):
                name = candidate
            elif isinstance(candidate, Mapping):
                if _has_prohibited_field(candidate) or set(candidate) != {"tool_name"}:
                    raise G6CorpusRendererError("candidate contains prohibited or non-nomination field")
                name = candidate.get("tool_name")
            else:
                raise G6CorpusRendererError("candidate must name a tool")
            names.append(_require_text(name, label="candidate tool name"))
        if len(set(names)) != len(names):
            raise G6CorpusRendererError("candidate tools are duplicated")
        family_tools = {contract.tool_name: contract for contract in self._contracts_by_family[family_tag]}
        result: list[G6Contract] = []
        for name in names:
            if name not in self._by_tool:
                raise G6CorpusRendererError("candidate tool is unregistered")
            if name not in family_tools:
                raise G6CorpusRendererError("candidate tool is outside family")
            result.append(family_tools[name])
        return tuple(result)

    def legal_key_sets(self, family_tag: str, tool_name: str) -> tuple[tuple[str, ...], ...]:
        """Return the exact registered legal argument-key sets for one tool."""

        return self.nominated_contracts(family_tag, (tool_name,))[0].legal_key_skeletons

    def legal_key_sets_for_nominations(
        self, family_tag: str, candidates: Sequence[str | Mapping[str, object]]
    ) -> dict[str, tuple[tuple[str, ...], ...]]:
        """Return deterministic legal key sets for the exact nominated tools."""

        return {contract.tool_name: contract.legal_key_skeletons for contract in self.nominated_contracts(family_tag, candidates)}


__all__ = [
    "FAMILY_REFERENCE_ASCII_BYTE_CAP",
    "G6Contract",
    "G6CorpusRenderer",
    "G6CorpusRendererError",
]
