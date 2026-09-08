"""Load the frozen, label-free Audio2Tool semantic runtime assets.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``load_frozen_semantic_runtime_assets`` is catalog id
``saea-tool-a2t-frozen-semantic-assets-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re

from .a2t_executable_semantic_cards import CompatibilityRule
from .a2t_semantic_router import ToolTierSemanticIndex


SOURCE_RECEIPT_SHA256 = (
    "571ab8179a426ea9a41383d8b44f6bb99986ba5bab7be36646aee1a812d8fb61"
)
SOURCE_VECTOR_SHA256 = (
    "00a7ebe9b8325ffc2c7b8e45ac4f0c8475b2d3e76994cc0f539f7b5ad5740f45"
)
SOURCE_RECEIPT_RELPATH = (
    "docs/receipts/knowledge/a2t-kb-size-full-embeddings.json"
)
CONSTRUCTION_ROWS_SHA256 = (
    "4d8e90b61c14bada2ad04308068b6033ba6e6721f29b84b7eb2c1c987bd1d141"
)
CONSTRUCTION_PARTITION_IDENTITY_SHA256 = (
    "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
)
SEMANTIC_INDEX_SHA256 = (
    "40b275636675adda1d185a13d0ed76d07b18c90b0d7e164535486c7374448fdb"
)
EXPECTED_RULE_COUNT = 43
EXPECTED_CENTROID_COUNT = 1095
EXPECTED_DIMENSION = 1024
DEFAULT_RECEIPT_RELPATH = Path(
    "docs/receipts/knowledge/a2t-semantic-agentloop-runtime-v1.json"
)

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_VALUE_FORMS = frozenset(
    {
        "boolean",
        "boolean-string",
        "integer",
        "list",
        "map",
        "nullable-string",
        "number",
        "string",
    }
)


class FrozenSemanticAssetError(RuntimeError):
    """A frozen runtime asset is missing, malformed, or hash-inconsistent."""


@dataclass(frozen=True)
class FrozenSemanticRuntimeAssets:
    """The frozen retrieval index and aggregate decision-card rules."""

    index: ToolTierSemanticIndex
    compatibility_rules: tuple[CompatibilityRule, ...]
    receipt: Mapping[str, object]
    centroid_artifact_path: Path
    compatibility_rules_path: Path


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _read_json(path: Path) -> tuple[Mapping[str, object], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FrozenSemanticAssetError(f"invalid ASCII JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise FrozenSemanticAssetError(f"JSON root must be an object: {path}")
    return value, raw


def _confined_file(root: Path, relative: object, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise FrozenSemanticAssetError(f"{label} path is missing")
    candidate = Path(relative)
    if candidate.is_absolute():
        raise FrozenSemanticAssetError(f"{label} path must be relative")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
        raise FrozenSemanticAssetError(f"{label} path is unavailable or escapes its root")
    return resolved


def _artifact_record(receipt: Mapping[str, object], name: str) -> Mapping[str, object]:
    artifacts = receipt.get("artifacts")
    record = artifacts.get(name) if isinstance(artifacts, Mapping) else None
    if not isinstance(record, Mapping):
        raise FrozenSemanticAssetError(f"receipt lacks {name!r} artifact record")
    return record


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise FrozenSemanticAssetError(f"{label} is not a lowercase SHA-256")
    return value


def _hash_field(digest: object, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _semantic_index_hash(
    *,
    dimension: int,
    registry_names: tuple[str, ...],
    centroid_names: tuple[str, ...],
    centroid_tiers: tuple[str, ...],
    centroid_matrix: object,
) -> str:
    import numpy as np

    digest = hashlib.sha256()
    _hash_field(digest, b"saea-a2t-tool-tier-semantic-index-v1")
    _hash_field(digest, dimension.to_bytes(8, "big"))
    for name in registry_names:
        _hash_field(digest, name.encode("utf-8"))
    for index, (name, tier) in enumerate(zip(centroid_names, centroid_tiers)):
        _hash_field(digest, name.encode("utf-8"))
        _hash_field(digest, tier.encode("utf-8"))
        _hash_field(
            digest,
            np.asarray(centroid_matrix[index], dtype=">f8").tobytes(),
        )
    return digest.hexdigest()


def _load_index(path: Path, receipt: Mapping[str, object]) -> ToolTierSemanticIndex:
    import numpy as np

    record = _artifact_record(receipt, "centroids")
    raw = path.read_bytes()
    if _sha256_bytes(raw) != _require_sha256(record.get("sha256"), label="centroid hash"):
        raise FrozenSemanticAssetError("centroid artifact SHA-256 drift")
    if len(raw) != record.get("bytes"):
        raise FrozenSemanticAssetError("centroid artifact byte count drift")
    try:
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != {
                "centroid_tiers",
                "centroid_tool_names",
                "centroid_vectors",
                "registry_tool_names",
            }:
                raise FrozenSemanticAssetError("centroid archive field set drift")
            matrix = np.asarray(archive["centroid_vectors"], dtype=np.float64)
            centroid_names = tuple(str(value) for value in archive["centroid_tool_names"])
            centroid_tiers = tuple(str(value) for value in archive["centroid_tiers"])
            registry_names = tuple(str(value) for value in archive["registry_tool_names"])
    except (OSError, ValueError) as error:
        raise FrozenSemanticAssetError("centroid archive cannot be decoded") from error

    if (
        matrix.shape != (EXPECTED_CENTROID_COUNT, EXPECTED_DIMENSION)
        or matrix.dtype != np.dtype("float64")
        or len(centroid_names) != EXPECTED_CENTROID_COUNT
        or len(centroid_tiers) != EXPECTED_CENTROID_COUNT
        or record.get("count") != EXPECTED_CENTROID_COUNT
        or record.get("dimension") != EXPECTED_DIMENSION
        or record.get("dtype") != "float64"
    ):
        raise FrozenSemanticAssetError("centroid artifact shape or metadata drift")
    if (
        len(registry_names) != 152
        or registry_names != tuple(sorted(registry_names))
        or len(registry_names) != len(set(registry_names))
        or any(_IDENTIFIER.fullmatch(value) is None for value in registry_names)
    ):
        raise FrozenSemanticAssetError("registry names are malformed or incomplete")
    keys = tuple(zip(centroid_names, centroid_tiers))
    if (
        keys != tuple(sorted(keys))
        or len(keys) != len(set(keys))
        or any(name not in registry_names for name in centroid_names)
        or any(
            _IDENTIFIER.fullmatch(name) is None
            or _IDENTIFIER.fullmatch(tier) is None
            for name, tier in keys
        )
    ):
        raise FrozenSemanticAssetError("centroid identities are malformed or unordered")
    norms = np.linalg.norm(matrix, axis=1)
    if (
        not bool(np.isfinite(matrix).all())
        or not bool(np.isfinite(norms).all())
        or any(not math.isclose(float(value), 1.0, abs_tol=1e-12) for value in norms)
    ):
        raise FrozenSemanticAssetError("centroid vectors are not finite unit vectors")
    observed_hash = _semantic_index_hash(
        dimension=EXPECTED_DIMENSION,
        registry_names=registry_names,
        centroid_names=centroid_names,
        centroid_tiers=centroid_tiers,
        centroid_matrix=matrix,
    )
    if observed_hash != receipt.get("semantic_index_sha256"):
        raise FrozenSemanticAssetError("semantic index hash differs from receipt")
    if observed_hash != SEMANTIC_INDEX_SHA256:
        raise FrozenSemanticAssetError("semantic index differs from the admitted index")
    return ToolTierSemanticIndex(
        construction_rows=(),
        registry_tool_names=registry_names,
        dimension=EXPECTED_DIMENSION,
        centroid_rows=tuple(matrix),
        centroid_tool_names=centroid_names,
        index_sha256=observed_hash,
    )


def _load_rules(
    path: Path,
    receipt: Mapping[str, object],
    registry_names: tuple[str, ...],
) -> tuple[CompatibilityRule, ...]:
    record = _artifact_record(receipt, "compatibility_rules")
    document, raw = _read_json(path)
    if _sha256_bytes(raw) != _require_sha256(record.get("sha256"), label="rule file hash"):
        raise FrozenSemanticAssetError("compatibility-rule file SHA-256 drift")
    if len(raw) != record.get("bytes"):
        raise FrozenSemanticAssetError("compatibility-rule byte count drift")
    if set(document) != {"rules", "schema"} or document.get("schema") != (
        "saea-a2t-aggregate-compatibility-rules-v1"
    ):
        raise FrozenSemanticAssetError("compatibility-rule document schema drift")
    payload = document.get("rules")
    if not isinstance(payload, list) or len(payload) != EXPECTED_RULE_COUNT:
        raise FrozenSemanticAssetError("compatibility-rule count must be exactly 43")
    if record.get("count") != EXPECTED_RULE_COUNT:
        raise FrozenSemanticAssetError("compatibility-rule receipt count drift")
    payload_hash = _sha256_bytes(_canonical_json_bytes(payload))
    if payload_hash != _require_sha256(
        record.get("compatibility_payload_sha256"),
        label="compatibility payload hash",
    ):
        raise FrozenSemanticAssetError("compatibility payload SHA-256 drift")

    rules: list[CompatibilityRule] = []
    for item in payload:
        if not isinstance(item, Mapping) or set(item) != {
            "construction_support_count",
            "legal_argument_key_set",
            "tool_name",
            "value_forms",
        }:
            raise FrozenSemanticAssetError("compatibility rule field set drift")
        tool_name = item.get("tool_name")
        keys = item.get("legal_argument_key_set")
        forms = item.get("value_forms")
        support = item.get("construction_support_count")
        if (
            not isinstance(tool_name, str)
            or tool_name not in registry_names
            or not isinstance(keys, list)
            or keys != sorted(keys)
            or len(keys) != len(set(keys))
            or any(not isinstance(key, str) or _IDENTIFIER.fullmatch(key) is None for key in keys)
            or not isinstance(forms, list)
            or type(support) is not int
            or support < 2
        ):
            raise FrozenSemanticAssetError("compatibility rule identity or support is malformed")
        parsed_forms: list[tuple[str, str]] = []
        for form in forms:
            if (
                not isinstance(form, list)
                or len(form) != 2
                or not isinstance(form[0], str)
                or form[0] not in keys
                or not isinstance(form[1], str)
                or form[1] not in _VALUE_FORMS
            ):
                raise FrozenSemanticAssetError("compatibility value form is malformed")
            parsed_forms.append((form[0], form[1]))
        if parsed_forms != sorted(parsed_forms) or len(parsed_forms) != len(set(parsed_forms)):
            raise FrozenSemanticAssetError("compatibility value forms are unordered or duplicated")
        rules.append(
            CompatibilityRule(
                tool_name=tool_name,
                legal_argument_key_set=tuple(keys),
                value_forms=tuple(parsed_forms),
                construction_support_count=support,
            )
        )
    ordered = tuple(
        sorted(
            rules,
            key=lambda rule: (
                rule.tool_name,
                len(rule.legal_argument_key_set),
                rule.legal_argument_key_set,
                rule.value_forms,
            ),
        )
    )
    if tuple(rules) != ordered:
        raise FrozenSemanticAssetError("compatibility rules are not canonically ordered")
    return ordered


def load_frozen_semantic_runtime_assets(
    *,
    repo: Path,
    data_root: Path,
    receipt_relpath: Path = DEFAULT_RECEIPT_RELPATH,
) -> FrozenSemanticRuntimeAssets:
    """Load only frozen aggregate assets and verify every transitive binding."""

    resolved_repo = repo.resolve()
    resolved_data_root = data_root.resolve()
    receipt_path = _confined_file(resolved_repo, str(receipt_relpath), label="receipt")
    receipt, _raw = _read_json(receipt_path)
    if receipt.get("schema") != "saea-a2t-frozen-semantic-runtime-assets-receipt-v1":
        raise FrozenSemanticAssetError("semantic runtime receipt schema drift")
    sources = receipt.get("sources")
    expected_sources = {
        "construction_partition_identity_sha256": (
            CONSTRUCTION_PARTITION_IDENTITY_SHA256
        ),
        "construction_rows_sha256": CONSTRUCTION_ROWS_SHA256,
        "embedding_receipt_relpath": SOURCE_RECEIPT_RELPATH,
        "embedding_receipt_sha256": SOURCE_RECEIPT_SHA256,
        "embedding_vector_sha256": SOURCE_VECTOR_SHA256,
    }
    if not isinstance(sources, Mapping) or dict(sources) != expected_sources:
        raise FrozenSemanticAssetError("semantic runtime source identity drift")
    if receipt.get("semantic_index_sha256") != SEMANTIC_INDEX_SHA256:
        raise FrozenSemanticAssetError("receipt does not name the admitted semantic index")
    privacy = receipt.get("privacy_boundary")
    expected_privacy = {
        "concrete_argument_values_emitted": 0,
        "evaluation_rows_consumed": 0,
        "reference_transcripts_emitted": 0,
        "sample_identifiers_emitted": 0,
        "source_utterances_emitted": 0,
    }
    if not isinstance(privacy, Mapping) or dict(privacy) != expected_privacy:
        raise FrozenSemanticAssetError("semantic runtime privacy boundary is not closed")
    contacts = receipt.get("contacts")
    expected_contacts = {
        "embedding_tool": 0,
        "frozen_core": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    if not isinstance(contacts, Mapping) or dict(contacts) != expected_contacts:
        raise FrozenSemanticAssetError("semantic runtime receipt records a contact")

    centroid_record = _artifact_record(receipt, "centroids")
    rules_record = _artifact_record(receipt, "compatibility_rules")
    centroid_path = _confined_file(
        resolved_data_root,
        centroid_record.get("path"),
        label="centroid artifact",
    )
    rules_path = _confined_file(
        resolved_repo,
        rules_record.get("path"),
        label="compatibility rules",
    )
    index = _load_index(centroid_path, receipt)
    rules = _load_rules(rules_path, receipt, index.registry_tool_names)
    return FrozenSemanticRuntimeAssets(
        index=index,
        compatibility_rules=rules,
        receipt=receipt,
        centroid_artifact_path=centroid_path,
        compatibility_rules_path=rules_path,
    )


__all__ = [
    "CONSTRUCTION_ROWS_SHA256",
    "CONSTRUCTION_PARTITION_IDENTITY_SHA256",
    "DEFAULT_RECEIPT_RELPATH",
    "FrozenSemanticAssetError",
    "FrozenSemanticRuntimeAssets",
    "SEMANTIC_INDEX_SHA256",
    "SOURCE_RECEIPT_SHA256",
    "SOURCE_RECEIPT_RELPATH",
    "SOURCE_VECTOR_SHA256",
    "load_frozen_semantic_runtime_assets",
]
