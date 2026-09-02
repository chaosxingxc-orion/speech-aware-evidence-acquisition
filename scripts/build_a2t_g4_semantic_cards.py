"""Build the frozen Audio2Tool G4 executable semantic-card corpus offline."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

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
    CompatibilityRule,
    ExecutableSemanticCardCorpus,
    build_executable_semantic_card_corpus,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    A2tKbRow,
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)

RUN_ID = "SAEA-A2T-MF-G4-SEMANTIC-CARDS-BUILD-V1"
PARTITION_SEED = 20260807
MINIMUM_COMPATIBILITY_SUPPORT = 2
EXPECTED_REGISTRY_TOOLS = 152
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
DEFAULT_CORPUS_OUTPUT = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g4-executable-semantic-cards-v1"
    / "corpus.txt"
)
DEFAULT_RECEIPT_OUTPUT = (
    REPO
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-02-a2t-g4-semantic-cards-build-v1"
    / "build-receipt.json"
)

_LEGAL_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_VALUE_FORM_TO_COMPATIBILITY = {
    "boolean": "boolean",
    "integer": "integer",
    "list": "list",
    "map": "map",
    "number": "number",
    "string": "string",
}


class G4SemanticCardBuildError(RuntimeError):
    """The deterministic G4 corpus build refused unsafe or drifting input."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _split_signature_arguments(text: str) -> tuple[str, ...]:
    if not text.strip():
        return ()
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(text):
        if character in "<[{(":
            depth += 1
        elif character in ">]})":
            depth -= 1
        elif character == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if depth != 0:
        raise G4SemanticCardBuildError("registry signature brackets are malformed")
    parts.append(text[start:].strip())
    return tuple(parts)


def _registry_argument_types(
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        signature = row.get("signature")
        if not isinstance(name, str) or not name or name in registry:
            raise G4SemanticCardBuildError("registry tool names are empty or duplicated")
        if not isinstance(signature, str):
            raise G4SemanticCardBuildError(f"registry signature is missing for {name!r}")
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", signature)
        if match is None or match.group(1) != name:
            raise G4SemanticCardBuildError(
                f"registry signature identity drift for {name!r}"
            )
        arguments: dict[str, str] = {}
        for raw in _split_signature_arguments(match.group(2)):
            argument = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\??", raw
            )
            if argument is None or argument.group(1) in arguments:
                raise G4SemanticCardBuildError(
                    f"registry signature arguments are malformed for {name!r}"
                )
            arguments[argument.group(1)] = argument.group(2).rstrip("?").strip()
        registry[name] = arguments
    return registry


def _serialized_value_form(value: str) -> str:
    """Classify a serialized construction value without retaining its literal."""

    if not isinstance(value, str):
        raise G4SemanticCardBuildError(
            "construction summaries must carry serialized values as text"
        )
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return "string"
    if decoded is None:
        return "null"
    if isinstance(decoded, bool):
        return "boolean"
    if isinstance(decoded, int):
        return "integer"
    if isinstance(decoded, float):
        return "number"
    if isinstance(decoded, list):
        return "list"
    if isinstance(decoded, dict):
        return "map"
    return "string"


def _extra_key_form(forms: Counter[str]) -> tuple[str, int] | None:
    non_null = {name for name, count in forms.items() if name != "null" and count}
    null_count = forms.get("null", 0)
    if null_count and (not non_null or non_null == {"string"}):
        return "nullable-string", sum(forms.values())
    if non_null <= {"integer", "number"} and non_null:
        return (
            "number" if "number" in non_null else "integer",
            sum(forms.values()),
        )
    if len(non_null) == 1 and not null_count:
        form = next(iter(non_null))
        compatible = _VALUE_FORM_TO_COMPATIBILITY.get(form)
        if compatible is not None:
            return compatible, sum(forms.values())
    return None


def derive_compatibility_rules(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    minimum_support: int = MINIMUM_COMPATIBILITY_SUPPORT,
) -> tuple[tuple[CompatibilityRule, ...], dict[str, object]]:
    """Derive aggregate schema/value-form rules without retaining any literal."""

    if (
        isinstance(minimum_support, bool)
        or not isinstance(minimum_support, int)
        or minimum_support < 2
    ):
        raise G4SemanticCardBuildError("compatibility minimum support must be at least two")
    registry = _registry_argument_types(registry_rows)
    pattern_support: Counter[tuple[str, tuple[str, ...]]] = Counter()
    value_forms: dict[
        tuple[str, tuple[str, ...], str], Counter[str]
    ] = defaultdict(Counter)
    for row in construction_rows:
        if row.tool_name not in registry:
            raise G4SemanticCardBuildError(
                f"construction tool {row.tool_name!r} is outside the registry"
            )
        skeleton = tuple(sorted(row.arg_signature))
        identity = (row.tool_name, skeleton)
        pattern_support[identity] += 1
        for key, value in row.arg_pairs:
            if key not in skeleton:
                raise G4SemanticCardBuildError(
                    "construction argument pairs disagree with their key skeleton"
                )
            value_forms[(row.tool_name, skeleton, key)][
                _serialized_value_form(value)
            ] += 1

    rules: list[CompatibilityRule] = []
    singleton_excluded = 0
    malformed_excluded = 0
    ambiguous_excluded = 0
    public_boolean_rules = 0
    nullable_rules = 0
    extension_rules = 0
    for (tool_name, skeleton), support in sorted(pattern_support.items()):
        if support < minimum_support:
            singleton_excluded += 1
            continue
        if any(_LEGAL_KEY.fullmatch(key) is None for key in skeleton):
            malformed_excluded += 1
            continue
        public = registry[tool_name]
        extensions = tuple(sorted(set(skeleton) - set(public)))
        forms: dict[str, str] = {}
        supports: list[int] = [support]
        safe_extensions = True
        for key in extensions:
            inferred = _extra_key_form(value_forms[(tool_name, skeleton, key)])
            if inferred is None or inferred[1] < minimum_support:
                safe_extensions = False
                break
            forms[key] = inferred[0]
            supports.append(inferred[1])
        if not safe_extensions:
            ambiguous_excluded += 1
            continue
        for key in sorted(set(skeleton).intersection(public)):
            observed = value_forms[(tool_name, skeleton, key)]
            type_name = public[key].lower()
            null_count = observed.get("null", 0)
            boolean_count = observed.get("boolean", 0)
            if null_count >= minimum_support:
                forms[key] = "nullable-string"
                supports.append(null_count)
                nullable_rules += 1
            elif type_name in {"boolean", "bool"} and boolean_count >= minimum_support:
                forms[key] = "boolean-string"
                supports.append(boolean_count)
                public_boolean_rules += 1
        if not extensions and not forms:
            continue
        if extensions:
            extension_rules += 1
        rules.append(
            CompatibilityRule(
                tool_name=tool_name,
                legal_argument_key_set=skeleton,
                value_forms=tuple(sorted(forms.items())),
                construction_support_count=min(supports),
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
    report = {
        "schema": "saea-a2t-g4-compatibility-derivation-v1",
        "minimum_support": minimum_support,
        "rule_count": len(ordered),
        "tool_count": len({rule.tool_name for rule in ordered}),
        "extension_rule_count": extension_rules,
        "public_boolean_lexical_rule_count": public_boolean_rules,
        "nullable_lexical_rule_count": nullable_rules,
        "singleton_skeletons_excluded": singleton_excluded,
        "malformed_key_skeletons_excluded": malformed_excluded,
        "ambiguous_extension_skeletons_excluded": ambiguous_excluded,
        "source_utterances_rendered": 0,
        "source_sample_ids_rendered": 0,
        "call_renders_rendered": 0,
        "concrete_argument_values_rendered": 0,
        "reference_transcripts_rendered": 0,
        "evaluation_rows_consumed": 0,
    }
    return ordered, report


def _compatible_construction_rows(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    rules: Sequence[CompatibilityRule],
) -> tuple[A2tKbRow, ...]:
    registry = _registry_argument_types(registry_rows)
    extensions = {
        (rule.tool_name, rule.legal_argument_key_set) for rule in rules
    }
    kept = []
    for row in construction_rows:
        skeleton = tuple(sorted(row.arg_signature))
        public_keys = set(registry[row.tool_name])
        if set(skeleton).issubset(public_keys) or (row.tool_name, skeleton) in extensions:
            kept.append(row)
    return tuple(kept)


def build_from_partition(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
) -> tuple[ExecutableSemanticCardCorpus, dict[str, object]]:
    """Build twice under reversed input and return the byte-identity audit."""

    rules, derivation = derive_compatibility_rules(registry_rows, construction_rows)
    safe_rows = _compatible_construction_rows(registry_rows, construction_rows, rules)
    first = build_executable_semantic_card_corpus(
        registry_rows,
        safe_rows,
        compatibility_rules=rules,
    )
    reversed_rules, reversed_derivation = derive_compatibility_rules(
        tuple(reversed(registry_rows)), tuple(reversed(construction_rows))
    )
    reversed_safe_rows = _compatible_construction_rows(
        tuple(reversed(registry_rows)),
        tuple(reversed(construction_rows)),
        reversed_rules,
    )
    second = build_executable_semantic_card_corpus(
        tuple(reversed(registry_rows)),
        reversed_safe_rows,
        compatibility_rules=reversed_rules,
    )
    if derivation != reversed_derivation or rules != reversed_rules:
        raise G4SemanticCardBuildError("compatibility derivation is order-dependent")
    if first.text != second.text or first.sha256 != second.sha256:
        raise G4SemanticCardBuildError("semantic-card corpus is not byte deterministic")
    pattern_families = {
        (row.tool_name, tuple(sorted(row.arg_signature))) for row in construction_rows
    }
    argument_keys = {key for row in construction_rows for key in row.arg_signature}
    report = {
        "deterministic_rebuild_equal": True,
        "construction_argument_pattern_family_count": len(pattern_families),
        "construction_argument_key_count": len(argument_keys),
        "safe_construction_row_count": len(safe_rows),
        "excluded_construction_row_count": len(construction_rows) - len(safe_rows),
        "compatibility": derivation,
    }
    return first, report


def run_build(root: Path) -> tuple[str, dict[str, object]]:
    """Run the hash-pinned, model-free build on the frozen construction partition."""

    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()
    if _sha256_file(PARTITION_PROPOSAL) != PARTITION_PROPOSAL_SHA256:
        raise G4SemanticCardBuildError("partition proposal SHA-256 drift")
    lock = load_lock(umbrella_lock_path(REPO))
    registry_path = asset_dir(lock, "audio2tool", root) / "tools_registry.csv"
    if _sha256_file(registry_path) != REGISTRY_SHA256:
        raise G4SemanticCardBuildError("registry SHA-256 drift")
    registry = load_tool_registry(lock, root)
    rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(REPO)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    if partition.split_identity_hash() != PROPOSED_EVAL_IDENTITY:
        raise G4SemanticCardBuildError("proposed evaluation identity drift")
    evaluation_ids = frozenset(partition.eval_sample_ids)
    construction_ids = frozenset(
        sample_id
        for row in partition.construction
        for sample_id in row.sample_ids
    )
    forbidden_intersection = construction_ids & (exposed | evaluation_ids)
    if forbidden_intersection:
        raise G4SemanticCardBuildError("construction decontamination drift")

    corpus, audit = build_from_partition(registry, partition.construction)
    if len(registry) != EXPECTED_REGISTRY_TOOLS:
        raise G4SemanticCardBuildError("registry tool-count drift")
    if audit["construction_argument_pattern_family_count"] != EXPECTED_PATTERN_FAMILIES:
        raise G4SemanticCardBuildError("construction argument-pattern count drift")
    if audit["construction_argument_key_count"] != EXPECTED_ARGUMENT_KEYS:
        raise G4SemanticCardBuildError("construction argument-key count drift")
    expected_corpus_report = {
        "registry_tool_count": EXPECTED_REGISTRY_TOOLS,
        "tool_card_count": EXPECTED_REGISTRY_TOOLS,
        "task_card_count": 4,
        "examples_validated": True,
        "ascii_only": True,
        "source_utterances_rendered": 0,
        "reference_transcripts_rendered": 0,
        "source_argument_values_rendered": 0,
        "gold_values_rendered": 0,
        "source_sample_ids_rendered": 0,
        "evaluation_samples_consumed": 0,
    }
    if any(corpus.report.get(key) != value for key, value in expected_corpus_report.items()):
        raise G4SemanticCardBuildError("semantic-card static safety gate failed")
    compatibility = dict(audit["compatibility"])
    if compatibility["minimum_support"] != MINIMUM_COMPATIBILITY_SUPPORT:
        raise G4SemanticCardBuildError("compatibility support threshold drift")
    if compatibility["concrete_argument_values_rendered"] != 0:
        raise G4SemanticCardBuildError("compatibility derivation rendered values")
    if offline.count != 0:
        raise G4SemanticCardBuildError("offline guard observed an outbound attempt")

    receipt = {
        "schema": "saea-a2t-g4-semantic-card-build-receipt-v1",
        "experiment_id": RUN_ID,
        "study_commit": study_commit,
        "execution_profile": "model-free-check",
        "source_hashes": {
            "partition_proposal": PARTITION_PROPOSAL_SHA256,
            "registry": REGISTRY_SHA256,
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
        "construction_summary": {
            "argument_pattern_family_count": audit[
                "construction_argument_pattern_family_count"
            ],
            "argument_key_count": audit["construction_argument_key_count"],
            "safe_construction_row_count": audit["safe_construction_row_count"],
            "excluded_construction_row_count": audit[
                "excluded_construction_row_count"
            ],
            "source_utterances_rendered": 0,
            "source_sample_ids_rendered": 0,
            "call_renders_rendered": 0,
            "concrete_argument_values_rendered": 0,
        },
        "compatibility": compatibility,
        "corpus": {
            "path": str(DEFAULT_CORPUS_OUTPUT.relative_to(REPO)).replace("\\", "/"),
            "sha256": corpus.sha256,
            "report": dict(corpus.report),
            "deterministic_rebuild_equal": audit["deterministic_rebuild_equal"],
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
            "exposure_row_created": False,
            "evaluation_or_fresh_rows_rendered": 0,
            "network_jitter_testing": False,
        },
    }
    return corpus.text, receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-output", type=Path, default=DEFAULT_CORPUS_OUTPUT)
    parser.add_argument("--receipt-output", type=Path, default=DEFAULT_RECEIPT_OUTPUT)
    args = parser.parse_args(argv)
    text, receipt = run_build(data_root())
    args.corpus_output.parent.mkdir(parents=True, exist_ok=True)
    args.corpus_output.write_text(text, encoding="utf-8", newline="\n")
    args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    args.receipt_output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
