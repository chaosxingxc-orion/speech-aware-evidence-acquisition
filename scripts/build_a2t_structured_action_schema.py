"""Build the full Audio2Tool structured-action response format offline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[1]
for import_root in (REPO / "src", REPO / "scripts"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import build_a2t_g4_semantic_cards as g4_builder  # noqa: E402
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (  # noqa: E402
    ExecutableSemanticCardCorpus,
)
from speech_aware_evidence_acquisition.rails.a2t_response_schema import (  # noqa: E402
    audio2tool_call_array_response_format,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)


RUN_ID = "SAEA-A2T-MF-STRUCTURED-ACTION-SCHEMA-BUILD-V1"
PARTITION_SEED = 20260807
EXPECTED_REGISTRY_TOOLS = 152
EXPECTED_SCHEMA_BRANCHES = 338
EXPECTED_COMPATIBILITY_RULES = 43
EXPECTED_PATTERN_FAMILIES = 354
EXPECTED_ARGUMENT_KEYS = 85
PROPOSED_EVAL_IDENTITY = (
    "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
)
PARTITION_PROPOSAL = REPO / "docs/receipts/knowledge/a2t-partition-proposal.json"
PARTITION_PROPOSAL_SHA256 = (
    "3bbf77a328c2983fb6299bcfe34a975624fee330a9325614dc1f84a7338678a1"
)
REGISTRY_SHA256 = "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4"
G4_BUILDER = REPO / "scripts/build_a2t_g4_semantic_cards.py"
G4_BUILDER_SHA256 = "e49c5b71348efbfdcb284d17b847efb341a3a5898324ef2432ebe9e880da080e"
G4_CORPUS = REPO / "knowledge/audio2tool/g4-executable-semantic-cards-v1/corpus.txt"
G4_CORPUS_SHA256 = "85a04fc72c49802853d0da3785f30a266a90d88275901c8292231442ef4a294f"
G4_RECEIPT = (
    REPO / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g4-semantic-cards-build-v1/build-receipt.json"
)
G4_RECEIPT_SHA256 = "f2da2a1b77a59ff7f5d9e74c2fabe1e04c87d560f4ca066c573f3d65803680fa"
RESPONSE_SCHEMA_BUILDER = (
    REPO / "src/speech_aware_evidence_acquisition/rails/a2t_response_schema.py"
)
DEFAULT_SCHEMA_RELPATH = Path(
    "knowledge/audio2tool/structured-action-schema-v1/response-format.json"
)
DEFAULT_RECEIPT_OUTPUT = (
    REPO / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-structured-action-schema-build-v1/build-receipt.json"
)

_CORPUS_ZERO_FIELDS = (
    "source_utterances_rendered",
    "source_argument_values_rendered",
    "source_sample_ids_rendered",
    "reference_transcripts_rendered",
    "gold_values_rendered",
    "evaluation_samples_consumed",
)
_COMPATIBILITY_ZERO_FIELDS = (
    "source_utterances_rendered",
    "source_sample_ids_rendered",
    "call_renders_rendered",
    "concrete_argument_values_rendered",
    "reference_transcripts_rendered",
    "evaluation_rows_consumed",
)


class StructuredActionSchemaBuildError(RuntimeError):
    """The model-free structured-action schema build refused input drift."""


@dataclass(frozen=True)
class StructuredActionSchemaArtifact:
    """Canonical response-format bytes plus their structural audit."""

    response_format: Mapping[str, object]
    text: str
    sha256: str
    utf8_bytes: int
    tool_count: int
    branch_count: int
    compatibility_rule_count: int
    safety: Mapping[str, int]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Mapping[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise StructuredActionSchemaBuildError(f"{path} must contain a JSON object")
    return value


def _require_count(
    report: Mapping[str, object], field: str, expected: int, label: str
) -> None:
    if report.get(field) != expected:
        raise StructuredActionSchemaBuildError(
            f"G4 identity drift: expected {expected} {label}"
        )


def _schema_branch_count(response_format: Mapping[str, object]) -> int:
    try:
        wrapper = response_format["json_schema"]
        document = wrapper["schema"]  # type: ignore[index]
        items = document["items"]  # type: ignore[index]
        branches = items["oneOf"]  # type: ignore[index]
    except (KeyError, TypeError) as error:
        raise StructuredActionSchemaBuildError(
            "response format lacks the strict oneOf action branches"
        ) from error
    if not isinstance(branches, list):
        raise StructuredActionSchemaBuildError(
            "response-format branches must be a list"
        )
    return len(branches)


def _poison_non_schema_card_fields(corpus: ExecutableSemanticCardCorpus):
    """Replace every card field that must remain unreachable from the schema."""

    return tuple(
        replace(
            card,
            choose_semantics="SYNTHETIC_SOURCE_VALUE_MUST_NOT_RENDER",
            avoid_semantics="SYNTHETIC_EVAL_VALUE_MUST_NOT_RENDER",
            role_guidance=("SYNTHETIC_ROLE_VALUE_MUST_NOT_RENDER",),
            examples=("SYNTHETIC_EXAMPLE_VALUE_MUST_NOT_RENDER",),
            text="SYNTHETIC_CARD_TEXT_MUST_NOT_RENDER",
        )
        for card in corpus.tool_cards
    )


def build_structured_action_schema(
    registry_rows: Sequence[Mapping[str, str]],
    corpus: ExecutableSemanticCardCorpus,
    g4_audit: Mapping[str, object],
) -> StructuredActionSchemaArtifact:
    """Build canonical schema bytes from G4's public structure-only surfaces."""

    if not isinstance(corpus, ExecutableSemanticCardCorpus):
        raise StructuredActionSchemaBuildError(
            "G4 corpus has the wrong structured type"
        )
    report = corpus.report
    _require_count(report, "registry_tool_count", EXPECTED_REGISTRY_TOOLS, "152 tools")
    _require_count(report, "tool_card_count", EXPECTED_REGISTRY_TOOLS, "152 tools")
    _require_count(
        report,
        "legal_argument_key_set_count",
        EXPECTED_SCHEMA_BRANCHES,
        "338 branches",
    )
    _require_count(
        report,
        "compatibility_rule_count",
        EXPECTED_COMPATIBILITY_RULES,
        "43 compatibility rules",
    )
    if (
        len(registry_rows) != EXPECTED_REGISTRY_TOOLS
        or len(corpus.tool_cards) != EXPECTED_REGISTRY_TOOLS
    ):
        raise StructuredActionSchemaBuildError("G4 identity drift: expected 152 tools")
    actual_skeletons = sum(
        len(card.legal_argument_key_sets) for card in corpus.tool_cards
    )
    actual_rules = sum(len(card.compatibility_rules) for card in corpus.tool_cards)
    if actual_skeletons != EXPECTED_SCHEMA_BRANCHES:
        raise StructuredActionSchemaBuildError(
            "G4 identity drift: expected 338 branches"
        )
    if actual_rules != EXPECTED_COMPATIBILITY_RULES:
        raise StructuredActionSchemaBuildError(
            "G4 identity drift: expected 43 compatibility rules"
        )

    compatibility = g4_audit.get("compatibility")
    if not isinstance(compatibility, Mapping):
        raise StructuredActionSchemaBuildError("G4 compatibility audit is missing")
    _require_count(
        compatibility,
        "rule_count",
        EXPECTED_COMPATIBILITY_RULES,
        "43 compatibility rules",
    )
    for field in _CORPUS_ZERO_FIELDS:
        if report.get(field) != 0:
            raise StructuredActionSchemaBuildError(
                f"G4 corpus is not value-free: {field} must be zero"
            )
    for field in _COMPATIBILITY_ZERO_FIELDS:
        if compatibility.get(field) != 0:
            raise StructuredActionSchemaBuildError(
                f"G4 compatibility derivation is not value-free: {field} must be zero"
            )

    response_format = audio2tool_call_array_response_format(
        registry_rows, corpus.tool_cards
    )
    reversed_format = audio2tool_call_array_response_format(
        tuple(reversed(registry_rows)), tuple(reversed(corpus.tool_cards))
    )
    poisoned_format = audio2tool_call_array_response_format(
        registry_rows, _poison_non_schema_card_fields(corpus)
    )
    if response_format != reversed_format:
        raise StructuredActionSchemaBuildError("response schema is order-dependent")
    if response_format != poisoned_format:
        raise StructuredActionSchemaBuildError(
            "response schema consumed examples, card text, or semantic prose"
        )
    branch_count = _schema_branch_count(response_format)
    if branch_count != EXPECTED_SCHEMA_BRANCHES:
        raise StructuredActionSchemaBuildError("schema does not contain 338 branches")
    text = (
        json.dumps(
            response_format,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    if not text.isascii() or "SYNTHETIC_" in text:
        raise StructuredActionSchemaBuildError(
            "schema must be canonical ASCII without synthetic values"
        )
    rendered = text.encode("ascii")
    safety = {
        "card_examples_consumed": 0,
        "card_text_consumed": 0,
        "source_utterances_rendered": 0,
        "source_argument_values_rendered": 0,
        "source_sample_ids_rendered": 0,
        "reference_transcripts_rendered": 0,
        "gold_values_rendered": 0,
        "evaluation_rows_consumed": 0,
    }
    return StructuredActionSchemaArtifact(
        response_format=response_format,
        text=text,
        sha256=hashlib.sha256(rendered).hexdigest(),
        utf8_bytes=len(rendered),
        tool_count=EXPECTED_REGISTRY_TOOLS,
        branch_count=branch_count,
        compatibility_rule_count=actual_rules,
        safety=safety,
    )


def _validate_g4_sources() -> Mapping[str, object]:
    expected = (
        (PARTITION_PROPOSAL, PARTITION_PROPOSAL_SHA256, "partition proposal"),
        (G4_BUILDER, G4_BUILDER_SHA256, "G4 builder"),
        (G4_CORPUS, G4_CORPUS_SHA256, "G4 corpus"),
        (G4_RECEIPT, G4_RECEIPT_SHA256, "G4 receipt"),
    )
    for path, sha256, label in expected:
        if _sha256_file(path) != sha256:
            raise StructuredActionSchemaBuildError(f"{label} SHA-256 drift")
    receipt = _read_json(G4_RECEIPT)
    source_hashes = receipt.get("source_hashes")
    corpus = receipt.get("corpus")
    if (
        not isinstance(source_hashes, Mapping)
        or source_hashes.get("builder") != G4_BUILDER_SHA256
        or source_hashes.get("registry") != REGISTRY_SHA256
        or not isinstance(corpus, Mapping)
        or corpus.get("sha256") != G4_CORPUS_SHA256
    ):
        raise StructuredActionSchemaBuildError("G4 receipt identity drift")
    return receipt


def run_build(root: Path) -> tuple[StructuredActionSchemaArtifact, dict[str, object]]:
    """Run the clean-tree, hash-pinned, zero-contact production build."""

    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()
    _validate_g4_sources()
    lock = load_lock(umbrella_lock_path(REPO))
    registry_path = asset_dir(lock, "audio2tool", root) / "tools_registry.csv"
    if _sha256_file(registry_path) != REGISTRY_SHA256:
        raise StructuredActionSchemaBuildError("registry SHA-256 drift")
    registry = load_tool_registry(lock, root)
    rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(REPO)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    if partition.split_identity_hash() != PROPOSED_EVAL_IDENTITY:
        raise StructuredActionSchemaBuildError("proposed evaluation identity drift")
    evaluation_ids = frozenset(partition.eval_sample_ids)
    construction_ids = frozenset(
        sample_id for row in partition.construction for sample_id in row.sample_ids
    )
    forbidden_intersection = construction_ids & (exposed | evaluation_ids)
    if forbidden_intersection:
        raise StructuredActionSchemaBuildError("construction decontamination drift")

    corpus, audit = g4_builder.build_from_partition(registry, partition.construction)
    if corpus.sha256 != G4_CORPUS_SHA256:
        raise StructuredActionSchemaBuildError("rebuilt G4 corpus identity drift")
    if (
        audit.get("construction_argument_pattern_family_count")
        != EXPECTED_PATTERN_FAMILIES
    ):
        raise StructuredActionSchemaBuildError("G4 construction pattern identity drift")
    if audit.get("construction_argument_key_count") != EXPECTED_ARGUMENT_KEYS:
        raise StructuredActionSchemaBuildError("G4 construction key identity drift")
    artifact = build_structured_action_schema(registry, corpus, audit)
    if offline.count != 0:
        raise StructuredActionSchemaBuildError(
            "offline guard observed an outbound attempt"
        )

    receipt = {
        "schema": "saea-a2t-structured-action-schema-build-receipt-v1",
        "experiment_id": RUN_ID,
        "study_commit": study_commit,
        "execution_profile": "model-free-check",
        "source_hashes": {
            "partition_proposal": PARTITION_PROPOSAL_SHA256,
            "registry": REGISTRY_SHA256,
            "g4_builder": G4_BUILDER_SHA256,
            "g4_corpus": G4_CORPUS_SHA256,
            "g4_receipt": G4_RECEIPT_SHA256,
            "response_schema_builder": _sha256_file(RESPONSE_SCHEMA_BUILDER),
            "builder": _sha256_file(Path(__file__)),
        },
        "partition": {
            "policy_id": partition.policy_id,
            "seed": partition.seed,
            "construction_unit_count": len(partition.construction),
            "construction_sample_count": len(construction_ids),
            "construction_identity_sha256": _identity(
                tuple(row.unit_id for row in partition.construction)
            ),
            "exposed_sample_count": len(exposed),
            "proposed_eval_sample_count": len(evaluation_ids),
            "proposed_eval_identity_sha256": partition.split_identity_hash(),
            "construction_forbidden_intersection_count": len(forbidden_intersection),
        },
        "carrier_inventory": {
            "pool_items": inventory["pool_items"],
            "pool_units": inventory["pool_units"],
            "usable_units": inventory["usable_units"],
        },
        "g4_rebuild": {
            "corpus_sha256": corpus.sha256,
            "deterministic_rebuild_equal": audit["deterministic_rebuild_equal"],
            "argument_pattern_family_count": audit[
                "construction_argument_pattern_family_count"
            ],
            "argument_key_count": audit["construction_argument_key_count"],
            "compatibility_rule_count": artifact.compatibility_rule_count,
        },
        "schema_artifact": {
            "path": "$SPEECHRL_DATA_DIR/" + DEFAULT_SCHEMA_RELPATH.as_posix(),
            "sha256": artifact.sha256,
            "utf8_bytes": artifact.utf8_bytes,
            "ascii_only": artifact.text.isascii(),
            "canonical_json": True,
            "tool_count": artifact.tool_count,
            "branch_count": artifact.branch_count,
            "compatibility_rule_count": artifact.compatibility_rule_count,
            "safety": dict(artifact.safety),
        },
        "contacts": {
            "frozen_core": 0,
            "network": 0,
            "retriever": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "scorer": 0,
            "audio_seconds": 0,
            "gpu_hours": 0,
        },
        "offline_guard": {
            "outbound_connection_attempts": offline.count,
            "targets": [],
        },
        "scope": {
            "model_flight_authorized": False,
            "launcher_created": False,
            "config_created": False,
            "exposure_row_created": False,
            "evaluation_or_fresh_rows_rendered": 0,
        },
    }
    return artifact, receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-output", type=Path)
    parser.add_argument("--receipt-output", type=Path, default=DEFAULT_RECEIPT_OUTPUT)
    args = parser.parse_args(argv)
    root = data_root()
    schema_output = args.schema_output or root / DEFAULT_SCHEMA_RELPATH
    artifact, receipt = run_build(root)
    schema_output.parent.mkdir(parents=True, exist_ok=True)
    schema_output.write_text(artifact.text, encoding="ascii", newline="\n")
    args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    args.receipt_output.write_text(rendered, encoding="ascii", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
