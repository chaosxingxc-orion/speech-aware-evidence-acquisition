"""Zero-contact post-seal evaluation for the native structured-action fixed eight.

The module is intentionally phase separated.  Historical artifacts cannot be
opened without the capability returned by :func:`prove_strict_cells_sealed`.
That capability is created only after the two new strict bundles survive the
authoritative bundle verifier, exact identity checks, and independent artifact
rehashing.  The module invokes neither a model nor the official scorer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..contracts import ExecutionPlan
from ..core.base import RunResult
from ..core.bundle import (
    STATUS_COMPLETED,
    VerifiedBundle,
    build_manifest,
    verify_bundle,
)
from ..core.config import ComposedConfig, protocol_hash
from ..core.scoring_batch import ScoreJob
from ..core.split_receipt import VerifiedSplit
from ..core.tracing import TraceSink
from ..data.splits import prefixed, split_identity_hash
from ..rails.a2t_hard_validity import validate_hard_validity
from ..reproduction.toolcall_scoring import parse_tool_calls_text
from .a2t_g8_post_score_oracle import (
    build_oracle_artifacts as build_g8_oracle_artifacts,
    select_oracle_rows as select_g8_oracle_rows,
)


EXPERIMENT_ID = "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1"
OFFICIAL_SCORER = "a2t-toolcall"
CELL_ORDER = (
    "REGISTRY_NO_SCHEMA",
    "REGISTRY_STRICT_ACTION",
    "HANDBOOK_NO_SCHEMA",
    "HANDBOOK_STRICT_ACTION",
)
STRICT_CELLS = ("REGISTRY_STRICT_ACTION", "HANDBOOK_STRICT_ACTION")
HISTORICAL_CELLS = ("REGISTRY_NO_SCHEMA", "HANDBOOK_NO_SCHEMA")
EXPECTED_SAMPLE_COUNT = 8
_AUTHORITY_SENTINEL = object()
_REGISTRY_RECOVERY_V2_RECEIPT_SCHEMA = (
    "saea-a2t-native-structured-action-fixed8-recovery-v2-flight-v1"
)
_REGISTRY_RECOVERY_V2_RUN_ID = (
    "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-RECOVERY-V2"
)
_REGISTRY_ORIGINAL_RUN_ID = "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1"
_REGISTRY_RECOVERY_V2_SPLIT_IDENTITY = (
    "b15cf0c0874f7af7d10af6cc9801aae4535bbe57b5a6dc3add50bcdb40fd93aa"
)
_REGISTRY_RECOVERY_V2_PROTOCOL = (
    "a2f24da7254a62020d4dff5d681c873af0ff11e71126dae7b72b7b9b2a7158d0"
)


class NativeStructuredActionPostsealError(RuntimeError):
    """A post-seal ordering, identity, hash, or completeness rule failed."""


@dataclass(frozen=True)
class PostsealAuthorization:
    """Capability proving both new cells were complete before protected access."""

    sample_ids: tuple[str, ...]
    strict_bundles: Mapping[str, VerifiedBundle]
    _sentinel: object


@dataclass(frozen=True)
class MaterializedSubset:
    cell: str
    manifest: Path
    outputs: Path
    outputs_sha256: str
    source_manifest_sha256: str
    model_contacts: int = 0


@dataclass(frozen=True)
class FourJobPlan:
    jobs: tuple[ScoreJob, ...]
    jobs_path: Path
    score_output_dir: Path
    command: tuple[str, ...]
    workers: int = 4
    dataset_sharding: bool = False
    shard_metric_averaging: bool = False


@dataclass(frozen=True)
class CellMetrics:
    parse_count: int
    exact_count: int
    tool_count: int
    slot_micro_precision: float
    slot_micro_recall: float
    slot_micro_f1: float
    hard_valid_count: int
    legal_key_set_count: int


@dataclass(frozen=True)
class PairedExact:
    wins: int
    harms: int
    ties: int


@dataclass(frozen=True)
class FourCellReport:
    sample_ids: tuple[str, ...]
    cells: Mapping[str, CellMetrics]
    per_sample: Mapping[str, Mapping[str, Mapping[str, object]]]
    paired: Mapping[str, PairedExact]


@dataclass(frozen=True)
class FourCellOracleSelection:
    sample_id: str
    cell: str
    text: str
    exact_match: float
    slot_f1: float
    tool_accuracy: float


@dataclass(frozen=True)
class MechanismGateVerdict:
    passed: bool
    outcome: str
    selected_strict_cell: str | None
    qualifying_strict_cells: tuple[str, ...]
    gates: Mapping[str, bool]


def _sha256_file(path: Path, label: str) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as error:
        raise NativeStructuredActionPostsealError(
            f"cannot read {label}: {error}"
        ) from error


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise NativeStructuredActionPostsealError(f"{label} must be lowercase 64-hex")
    return value


def _exact_ids(sample_ids: Sequence[str]) -> tuple[str, ...]:
    ids = tuple(sample_ids)
    if (
        len(ids) != EXPECTED_SAMPLE_COUNT
        or len(set(ids)) != EXPECTED_SAMPLE_COUNT
        or any(not isinstance(sample_id, str) or not sample_id for sample_id in ids)
    ):
        raise NativeStructuredActionPostsealError(
            "the fixed-eight evaluator requires exactly eight unique sample identities"
        )
    return ids


def _exact_keys(
    value: Mapping[str, object], expected: Sequence[str], label: str
) -> None:
    if set(value) != set(expected):
        raise NativeStructuredActionPostsealError(
            f"{label} must name exactly {list(expected)}"
        )


def _authorized(value: object) -> PostsealAuthorization:
    if (
        not isinstance(value, PostsealAuthorization)
        or value._sentinel is not _AUTHORITY_SENTINEL
    ):
        raise NativeStructuredActionPostsealError(
            "protected post-seal access requires a valid strict-cell seal authorization"
        )
    return value


def _artifact_meta(bundle: VerifiedBundle, key: str, cell: str) -> Mapping[str, object]:
    meta = bundle.manifest.get(key)
    if not isinstance(meta, Mapping):
        raise NativeStructuredActionPostsealError(f"{cell} verified bundle lacks {key}")
    return meta


def _validate_aborted_registry_recovery(
    *, bundle: VerifiedBundle, descriptor: Mapping[str, object]
) -> None:
    """Admit the one registered no-recontact recovery boundary, or refuse."""

    if descriptor.get("recovered_from_aborted_attempt") is not True:
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION must be sealed and unscored (attempt state OPENED)"
        )
    receipt_value = descriptor.get("recovery_receipt")
    if not isinstance(receipt_value, (str, Path)):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt path is missing"
        )
    receipt_path = Path(receipt_value).resolve()
    expected_receipt_hash = _require_sha256(
        descriptor.get("recovery_receipt_sha256"),
        "REGISTRY_STRICT_ACTION recovery receipt SHA-256",
    )
    if _sha256_file(receipt_path, "REGISTRY_STRICT_ACTION recovery receipt") != expected_receipt_hash:
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt SHA-256 drift"
        )
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NativeStructuredActionPostsealError(
            f"cannot read REGISTRY_STRICT_ACTION recovery receipt: {error}"
        ) from error
    if not isinstance(receipt, Mapping):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt must be an object"
        )
    manifest = bundle.manifest
    attempt = manifest.get("attempt")
    if not isinstance(attempt, Mapping):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION sealed manifest lacks an attempt binding"
        )
    attempt_id = attempt.get("attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id:
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION sealed manifest attempt id is missing"
        )
    recovery = receipt.get("registry_recovery")
    if (
        receipt.get("schema") != _REGISTRY_RECOVERY_V2_RECEIPT_SCHEMA
        or receipt.get("run_id") != _REGISTRY_RECOVERY_V2_RUN_ID
        or not isinstance(recovery, Mapping)
        or recovery.get("cell") != "REGISTRY_STRICT_ACTION"
        or recovery.get("recovered_from_attempt_id") != attempt_id
        or recovery.get("recovered_from_attempt_state") != "ABORTED"
        or recovery.get("completed_rows") != EXPECTED_SAMPLE_COUNT
    ):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt has invalid recovery facts"
        )
    split = manifest.get("split")
    if (
        manifest.get("run_id") != _REGISTRY_ORIGINAL_RUN_ID
        or recovery.get("successor_run_id") != _REGISTRY_RECOVERY_V2_RUN_ID
        or recovery.get("verified_manifest_run_id") != manifest.get("run_id")
        or recovery.get("successor_split_identity_hash")
        != _REGISTRY_RECOVERY_V2_SPLIT_IDENTITY
        or recovery.get("successor_protocol_hash") != _REGISTRY_RECOVERY_V2_PROTOCOL
        or not isinstance(split, Mapping)
        or split.get("identity_hash") != _REGISTRY_RECOVERY_V2_SPLIT_IDENTITY
        or manifest.get("protocol_hash") != _REGISTRY_RECOVERY_V2_PROTOCOL
    ):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION V2 successor correction binding drift"
        )
    if recovery.get("registry_recontacted") is not False:
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt registry_recontacted must be false"
        )
    if recovery.get("registry_model_contacts") != 0:
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt registry_model_contacts must be zero"
        )
    if (
        recovery.get("successor_manifest_path") != str(bundle.manifest_path.resolve())
        or recovery.get("successor_manifest_sha256")
        != _sha256_file(bundle.manifest_path, "REGISTRY_STRICT_ACTION successor manifest")
    ):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt successor manifest lineage drift"
        )
    source_attempt = recovery.get("source_attempt")
    state_path_value = attempt.get("state_path")
    if (
        not isinstance(source_attempt, Mapping)
        or source_attempt.get("attempt_id") != attempt_id
        or source_attempt.get("state") != "ABORTED"
        or not isinstance(state_path_value, str)
        or source_attempt.get("sha256")
        != _sha256_file(Path(state_path_value), "REGISTRY_STRICT_ACTION source attempt")
    ):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt source attempt lineage drift"
        )
    original_source_artifacts = recovery.get("original_source_artifacts")
    if (
        not isinstance(original_source_artifacts, Mapping)
        or not isinstance(original_source_artifacts.get("manifest_path"), str)
        or original_source_artifacts.get("manifest_sha256")
        != _sha256_file(
            Path(str(original_source_artifacts["manifest_path"])),
            "REGISTRY_STRICT_ACTION original source manifest",
        )
    ):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt original source lineage drift"
        )
    source_artifacts = recovery.get("source_artifacts")
    if not isinstance(source_artifacts, Mapping):
        raise NativeStructuredActionPostsealError(
            "REGISTRY_STRICT_ACTION recovery receipt lacks source artifact hashes"
        )
    for artifact_key, path_key, hash_key in (
        ("outputs", "outputs_path", "outputs_sha256"),
        ("raw_trace", "raw_trace_path", "raw_trace_sha256"),
        ("trace_manifest", "trace_manifest_path", "trace_manifest_sha256"),
    ):
        artifact = _artifact_meta(bundle, artifact_key, "REGISTRY_STRICT_ACTION")
        if (
            source_artifacts.get(path_key) != artifact.get("path")
            or source_artifacts.get(hash_key) != artifact.get("sha256")
            or original_source_artifacts.get(hash_key) != artifact.get("sha256")
        ):
            raise NativeStructuredActionPostsealError(
                "REGISTRY_STRICT_ACTION recovery receipt source artifact hash drift"
            )


def prove_strict_cells_sealed(
    *,
    strict_seals: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    verifier: Callable[[Path], VerifiedBundle] = verify_bundle,
) -> PostsealAuthorization:
    """Return protected-access authority only after both strict bundles seal."""

    ids = _exact_ids(sample_ids)
    _exact_keys(
        strict_seals, STRICT_CELLS, "strict_seals (exactly the two strict cells)"
    )
    verified: dict[str, VerifiedBundle] = {}
    for cell in STRICT_CELLS:
        descriptor = strict_seals[cell]
        if not isinstance(descriptor, Mapping):
            raise NativeStructuredActionPostsealError(
                f"{cell} seal descriptor is malformed"
            )
        manifest_value = descriptor.get("manifest")
        if not isinstance(manifest_value, (str, Path)):
            raise NativeStructuredActionPostsealError(
                f"{cell} manifest path is missing"
            )
        manifest_path = Path(manifest_value).resolve()
        expected_manifest_hash = _require_sha256(
            descriptor.get("manifest_sha256"), f"{cell} manifest SHA-256"
        )
        if _sha256_file(manifest_path, f"{cell} manifest") != expected_manifest_hash:
            raise NativeStructuredActionPostsealError(f"{cell} manifest SHA-256 drift")
        try:
            bundle = verifier(manifest_path)
        except Exception as error:
            raise NativeStructuredActionPostsealError(
                f"{cell} failed authoritative bundle verification: {error}"
            ) from error
        manifest = bundle.manifest
        if manifest.get("status") != STATUS_COMPLETED:
            raise NativeStructuredActionPostsealError(
                f"{cell} manifest is not COMPLETED"
            )
        if bundle.attempt_state == "ABORTED" and cell == "REGISTRY_STRICT_ACTION":
            _validate_aborted_registry_recovery(bundle=bundle, descriptor=descriptor)
        elif bundle.attempt_state != "OPENED":
            raise NativeStructuredActionPostsealError(
                f"{cell} must be sealed and unscored (attempt state OPENED)"
            )
        split = manifest.get("split")
        if (
            not isinstance(split, Mapping)
            or split.get("count") != EXPECTED_SAMPLE_COUNT
            or set(split.get("ids", ())) != set(ids)
            or len(bundle.outputs_rows) != EXPECTED_SAMPLE_COUNT
            or bundle.split_ids != frozenset(ids)
        ):
            raise NativeStructuredActionPostsealError(
                f"{cell} does not carry the exact eight-row identity"
            )
        for key, descriptor_key, label in (
            ("outputs", "outputs_sha256", "outputs SHA-256"),
            ("raw_trace", "raw_trace_sha256", "raw trace SHA-256"),
            ("trace_manifest", "trace_manifest_sha256", "trace manifest SHA-256"),
        ):
            meta = _artifact_meta(bundle, key, cell)
            expected = _require_sha256(
                descriptor.get(descriptor_key), f"{cell} {label}"
            )
            if meta.get("sha256") != expected:
                raise NativeStructuredActionPostsealError(
                    f"{cell} {label} differs from seal"
                )
            artifact_path = meta.get("path")
            if (
                not isinstance(artifact_path, str)
                or _sha256_file(Path(artifact_path), f"{cell} {key}") != expected
            ):
                raise NativeStructuredActionPostsealError(f"{cell} {label} drift")
        if not bundle.trace_records:
            raise NativeStructuredActionPostsealError(f"{cell} sealed trace is empty")
        verified[cell] = bundle
    return PostsealAuthorization(ids, verified, _AUTHORITY_SENTINEL)


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _derived_context(parent: VerifiedBundle, ids: tuple[str, ...]):
    manifest = parent.manifest
    split_identity = split_identity_hash(prefixed("audio2tool", ids))
    arm = str(manifest.get("arm", ""))
    config_meta = manifest.get("config")
    plan_meta = manifest.get("plan")
    if (
        not arm
        or not isinstance(config_meta, Mapping)
        or not isinstance(plan_meta, Mapping)
    ):
        raise NativeStructuredActionPostsealError(
            "historical parent lacks reusable bundle identity"
        )
    config_hash = _require_sha256(
        config_meta.get("config_hash"), "historical config hash"
    )
    fragments = config_meta.get("fragments", {})
    if not isinstance(fragments, Mapping):
        raise NativeStructuredActionPostsealError(
            "historical config fragments are malformed"
        )
    composed = ComposedConfig(
        values={
            "arm": arm,
            "carrier_lock_key": "audio2tool",
            "split_name": "A2T-NATIVE-STRUCTURED-ACTION-FIXED8",
            "scorers": [OFFICIAL_SCORER],
        },
        config_hash=config_hash,
        fragments=dict(fragments),
    )
    plan_values = dict(plan_meta)
    plan_values["split_identity_hash"] = split_identity
    plan_values["split_role"] = "discovery"
    plan_values["protocol_hash"] = protocol_hash(config_hash, arm, split_identity)
    try:
        plan = ExecutionPlan(**plan_values)
        plan.validate()
    except Exception as error:
        raise NativeStructuredActionPostsealError(
            f"historical parent plan cannot bind the fixed-eight derivative: {error}"
        ) from error
    split = VerifiedSplit(
        name="A2T-NATIVE-STRUCTURED-ACTION-FIXED8",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        ids=tuple(sorted(ids)),
        prefixed_ids=prefixed("audio2tool", tuple(sorted(ids))),
        identity_hash=split_identity,
    )
    return composed, plan, split


def materialize_historical_subsets(
    *,
    authorization: object,
    historical_sources: Mapping[str, Mapping[str, object]],
    output_root: Path,
    verifier: Callable[[Path], VerifiedBundle] = verify_bundle,
    manifest_builder: Callable[..., Path] = build_manifest,
) -> Mapping[str, MaterializedSubset]:
    """Materialize the two exact-identity historical derivatives after seal."""

    authority = _authorized(authorization)
    _exact_keys(historical_sources, HISTORICAL_CELLS, "historical_sources")
    root = Path(output_root)
    if root.exists() and any(root.iterdir()):
        raise NativeStructuredActionPostsealError(
            f"historical subset directory is not empty: {root}"
        )
    root.mkdir(parents=True, exist_ok=True)
    result: dict[str, MaterializedSubset] = {}
    for cell in HISTORICAL_CELLS:
        source = historical_sources[cell]
        manifest_value = source.get("manifest")
        if not isinstance(manifest_value, (str, Path)):
            raise NativeStructuredActionPostsealError(
                f"{cell} historical manifest is missing"
            )
        parent_path = Path(manifest_value).resolve()
        manifest_hash = _require_sha256(
            source.get("manifest_sha256"),
            f"{cell} configured historical manifest SHA-256",
        )
        if _sha256_file(parent_path, f"{cell} historical manifest") != manifest_hash:
            raise NativeStructuredActionPostsealError(
                f"{cell} historical manifest hash differs from config"
            )
        try:
            parent = verifier(parent_path)
        except Exception as error:
            raise NativeStructuredActionPostsealError(
                f"{cell} historical parent failed authoritative verification: {error}"
            ) from error
        if parent.attempt_state != "FINALIZED":
            raise NativeStructuredActionPostsealError(
                f"{cell} historical parent attempt must be FINALIZED"
            )
        if parent.outputs_path is None:
            raise NativeStructuredActionPostsealError(
                f"{cell} historical parent lacks outputs"
            )
        outputs_hash = _require_sha256(
            source.get("outputs_sha256"),
            f"{cell} configured historical outputs SHA-256",
        )
        if (
            _sha256_file(parent.outputs_path, f"{cell} historical outputs")
            != outputs_hash
        ):
            raise NativeStructuredActionPostsealError(
                f"{cell} historical outputs hash differs from config"
            )
        rows_by_id = {str(row.get("sample_id")): row for row in parent.outputs_rows}
        if len(rows_by_id) != len(parent.outputs_rows) or not set(
            authority.sample_ids
        ) <= set(rows_by_id):
            raise NativeStructuredActionPostsealError(
                f"{cell} historical parent cannot supply the exact fixed-eight identity"
            )
        cell_dir = root / cell
        cell_dir.mkdir()
        composed, plan, verified_split = _derived_context(parent, authority.sample_ids)
        sink = TraceSink(cell_dir, plan.run_id)
        derived_rows: list[dict[str, object]] = []
        try:
            for index, sample_id in enumerate(sorted(authority.sample_ids), start=1):
                source_row = rows_by_id[sample_id]
                text = source_row.get("text")
                if not isinstance(text, str) or source_row.get(
                    "response_text_sha256"
                ) != _sha256_text(text):
                    raise NativeStructuredActionPostsealError(
                        f"{cell}/{sample_id} historical response text hash drift"
                    )
                request_id = f"historical-fixed8-{index:02d}"
                provenance = {
                    "source_artifact_path": str(parent.outputs_path.resolve()),
                    "source_artifact_sha256": outputs_hash,
                    "source_manifest_path": str(parent_path),
                    "source_manifest_sha256": manifest_hash,
                    "parent_request_id": source_row.get("request_id"),
                }
                request = {
                    "tool_id": "saea-a2t-fixed8-historical-subset-v1",
                    "sample_id": sample_id,
                    "source": provenance,
                }
                request_hash = hashlib.sha256(_canonical_bytes(request)).hexdigest()
                response = {
                    "tool_id": request["tool_id"],
                    "sample_id": sample_id,
                    "source": provenance,
                    "text_sha256": _sha256_text(text),
                }
                response_hash = hashlib.sha256(_canonical_bytes(response)).hexdigest()
                sink.emit(
                    "TOOL",
                    f"{request_id}/request",
                    {**request, "payload_sha256": request_hash},
                )
                sink.emit(
                    "TOOL",
                    f"{request_id}/response",
                    {
                        **response,
                        "text": text,
                        "response_sha256": response_hash,
                        "response_text_sha256": _sha256_text(text),
                    },
                )
                derived_rows.append(
                    {
                        "request_id": request_id,
                        "sample_id": sample_id,
                        "carrier_lock_key": "audio2tool",
                        "arm": composed.values["arm"],
                        "text": text,
                        "admitted": True,
                        "request_sha256": request_hash,
                        "response_sha256": response_hash,
                        "response_text_sha256": _sha256_text(text),
                        "historical_source": provenance,
                    }
                )
            trace_hash = sink.close()
        except Exception:
            sink.close()
            raise
        outputs = cell_dir / f"{plan.run_id}.historical-fixed8.outputs.jsonl"
        _write_jsonl(outputs, derived_rows)
        session_meta = parent.manifest.get("session_receipt")
        session_path = (
            Path(str(session_meta["path"]))
            if isinstance(session_meta, Mapping)
            and isinstance(session_meta.get("path"), str)
            else None
        )
        manifest = manifest_builder(
            repo_root=Path(__file__).resolve().parents[3],
            data_root=Path(plan_meta_path(parent)),
            composed=composed,
            plan=plan,
            verified_split=verified_split,
            session_receipt_path=session_path,
            run_dir=cell_dir,
            status=STATUS_COMPLETED,
            result=RunResult(
                run_id=plan.run_id,
                arm=str(composed.values["arm"]),
                outputs_path=outputs,
                trace_manifest_hash=trace_hash,
                cost={
                    "calls_used": 0,
                    "new_model_contacts": 0,
                    "parent_physical_contacts_inherited": parent.manifest.get("cost"),
                },
            ),
        )
        result[cell] = MaterializedSubset(
            cell=cell,
            manifest=Path(manifest).resolve(),
            outputs=outputs.resolve(),
            outputs_sha256=_sha256_file(outputs, f"{cell} subset outputs"),
            source_manifest_sha256=manifest_hash,
        )
    return result


def plan_meta_path(parent: VerifiedBundle) -> Path:
    """Infer the attempt-store data root used by a verified parent manifest."""

    attempt = parent.manifest.get("attempt")
    state_path = attempt.get("state_path") if isinstance(attempt, Mapping) else None
    if isinstance(state_path, str):
        path = Path(state_path).resolve()
        for ancestor in path.parents:
            if ancestor.name == "attempts":
                return ancestor.parent
    # Tests can use a manifest builder stub; the real path always has an attempt binding.
    return parent.manifest_path.resolve().parent


def build_four_job_plan(
    *,
    authorization: object,
    manifests: Mapping[str, Mapping[str, object]],
    jobs_path: Path,
    score_output_dir: Path,
    verifier: Callable[[Path], VerifiedBundle] = verify_bundle,
) -> FourJobPlan:
    """Write the exact four whole-manifest jobs consumed by evaluate_parallel.sh."""

    authority = _authorized(authorization)
    _exact_keys(manifests, CELL_ORDER, "four-cell manifests")
    jobs: list[ScoreJob] = []
    seen_paths: set[Path] = set()
    for cell in CELL_ORDER:
        descriptor = manifests[cell]
        raw_ids = tuple(descriptor.get("sample_ids", ()))
        if len(raw_ids) != EXPECTED_SAMPLE_COUNT or set(raw_ids) != set(
            authority.sample_ids
        ):
            raise NativeStructuredActionPostsealError(
                f"{cell} scorer job is not one whole exact eight-row manifest"
            )
        manifest_value = descriptor.get("manifest")
        if not isinstance(manifest_value, (str, Path)):
            raise NativeStructuredActionPostsealError(
                f"{cell} scorer manifest is missing"
            )
        manifest = Path(manifest_value).resolve()
        if not manifest.is_file():
            raise NativeStructuredActionPostsealError(
                f"{cell} scorer manifest does not exist"
            )
        if manifest in seen_paths:
            raise NativeStructuredActionPostsealError("duplicate scorer job manifest")
        seen_paths.add(manifest)
        try:
            bundle = verifier(manifest)
        except Exception as error:
            raise NativeStructuredActionPostsealError(
                f"{cell} scorer manifest failed authoritative verification: {error}"
            ) from error
        split = bundle.manifest.get("split")
        if (
            bundle.manifest.get("status") != STATUS_COMPLETED
            or not isinstance(split, Mapping)
            or split.get("count") != EXPECTED_SAMPLE_COUNT
            or set(split.get("ids", ())) != set(authority.sample_ids)
            or len(bundle.outputs_rows) != EXPECTED_SAMPLE_COUNT
            or bundle.split_ids != frozenset(authority.sample_ids)
        ):
            raise NativeStructuredActionPostsealError(
                f"{cell} scorer job is not a complete verified whole eight-row manifest"
            )
        jobs.append(ScoreJob(job_id=cell, manifest=manifest, operation="score"))
    jobs_file = Path(jobs_path)
    jobs_file.parent.mkdir(parents=True, exist_ok=True)
    if jobs_file.exists():
        raise NativeStructuredActionPostsealError(
            f"refusing to overwrite score jobs: {jobs_file}"
        )
    _write_jsonl(
        jobs_file,
        tuple(
            {"job_id": job.job_id, "manifest": str(job.manifest)}
            for job in jobs
        ),
    )
    output_dir = Path(score_output_dir).resolve()
    return FourJobPlan(
        jobs=tuple(jobs),
        jobs_path=jobs_file.resolve(),
        score_output_dir=output_dir,
        command=(
            "scripts/evaluate_parallel.sh",
            "--jobs",
            str(jobs_file.resolve()),
            "--output-dir",
            str(output_dir),
            "--workers",
            "4",
            "--include-per-sample",
        ),
    )


def _metric(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise NativeStructuredActionPostsealError(f"{label} must be finite numeric")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise NativeStructuredActionPostsealError(f"{label} must be within [0, 1]")
    return result


def _validated_scores(
    payloads: Mapping[str, Mapping[str, object]],
    sealed_cells: Mapping[str, Mapping[str, object]],
    ids: tuple[str, ...],
) -> Mapping[str, tuple[Mapping[str, object], Mapping[str, Mapping[str, object]]]]:
    _exact_keys(payloads, CELL_ORDER, "score payloads")
    _exact_keys(sealed_cells, CELL_ORDER, "sealed cells")
    result = {}
    seen_manifests: set[Path] = set()
    for cell in CELL_ORDER:
        seal = sealed_cells[cell]
        manifest = Path(str(seal.get("manifest", ""))).resolve()
        if not manifest.is_file():
            raise NativeStructuredActionPostsealError(
                f"{cell} sealed manifest is unavailable"
            )
        if manifest in seen_manifests:
            raise NativeStructuredActionPostsealError("duplicate scorer job manifest")
        seen_manifests.add(manifest)
        expected_manifest_hash = _require_sha256(
            seal.get("manifest_sha256"), f"{cell} manifest SHA-256"
        )
        if _sha256_file(manifest, f"{cell} manifest") != expected_manifest_hash:
            raise NativeStructuredActionPostsealError(f"{cell} manifest hash drift")
        outputs = Path(str(seal.get("outputs", ""))).resolve()
        expected_outputs_hash = _require_sha256(
            seal.get("outputs_sha256"), f"{cell} outputs SHA-256"
        )
        if _sha256_file(outputs, f"{cell} outputs") != expected_outputs_hash:
            raise NativeStructuredActionPostsealError(f"{cell} outputs hash drift")
        payload = payloads[cell]
        if (
            payload.get("verified") is not True
            or Path(str(payload.get("manifest", ""))).resolve() != manifest
        ):
            raise NativeStructuredActionPostsealError(
                f"{cell} score is unverified or has a manifest identity mismatch"
            )
        scores = payload.get("scores")
        if not isinstance(scores, Mapping) or set(scores) != {OFFICIAL_SCORER}:
            raise NativeStructuredActionPostsealError(
                f"{cell} score must contain only {OFFICIAL_SCORER}"
            )
        official = scores[OFFICIAL_SCORER]
        if not isinstance(official, Mapping):
            raise NativeStructuredActionPostsealError(
                f"{cell} official score is malformed"
            )
        aggregate = official.get("aggregate")
        details = official.get("per_sample")
        if (
            not isinstance(aggregate, Mapping)
            or aggregate.get("samples") != EXPECTED_SAMPLE_COUNT
        ):
            raise NativeStructuredActionPostsealError(
                f"{cell} score aggregate is partial"
            )
        if not isinstance(details, list) or len(details) != EXPECTED_SAMPLE_COUNT:
            raise NativeStructuredActionPostsealError(
                f"{cell} lacks complete per-sample scores"
            )
        by_id: dict[str, Mapping[str, object]] = {}
        for detail in details:
            if not isinstance(detail, Mapping):
                raise NativeStructuredActionPostsealError(
                    f"{cell} per-sample score is malformed"
                )
            sample_id = detail.get("sample_id")
            if not isinstance(sample_id, str) or sample_id in by_id:
                raise NativeStructuredActionPostsealError(
                    f"{cell} per-sample identities are invalid"
                )
            for metric in ("exact_match", "slot_f1", "tool_accuracy"):
                _metric(detail.get(metric), f"{cell}/{sample_id} {metric}")
            if not isinstance(detail.get("parsed"), bool):
                raise NativeStructuredActionPostsealError(
                    f"{cell}/{sample_id} parsed is not boolean"
                )
            by_id[sample_id] = detail
        if set(by_id) != set(ids):
            raise NativeStructuredActionPostsealError(
                f"{cell} complete per-sample identity mismatch"
            )
        result[cell] = (aggregate, by_id)
    return result


def _read_outputs(path: Path, ids: tuple[str, ...], cell: str) -> Mapping[str, str]:
    try:
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").split("\n")
            if line
        ]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NativeStructuredActionPostsealError(
            f"cannot read {cell} sealed outputs: {error}"
        ) from error
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise NativeStructuredActionPostsealError(f"{cell} output row is malformed")
        sample_id, text = row.get("sample_id"), row.get("text")
        if (
            not isinstance(sample_id, str)
            or sample_id in result
            or not isinstance(text, str)
        ):
            raise NativeStructuredActionPostsealError(
                f"{cell} output identities are malformed"
            )
        if row.get("response_text_sha256") != _sha256_text(text):
            raise NativeStructuredActionPostsealError(
                f"{cell}/{sample_id} response text hash drift"
            )
        result[sample_id] = text
    if set(result) != set(ids):
        raise NativeStructuredActionPostsealError(f"{cell} output identity mismatch")
    return result


def analyze_four_cells(
    *,
    authorization: object,
    score_payloads: Mapping[str, Mapping[str, object]],
    sealed_cells: Mapping[str, Mapping[str, object]],
    registry_rows: Sequence[Mapping[str, str]],
    legal_key_sets_by_tool: Mapping[str, Sequence[Sequence[str]]],
) -> FourCellReport:
    """Report official metrics plus frozen label-free validity diagnostics."""

    authority = _authorized(authorization)
    ids = authority.sample_ids
    scores = _validated_scores(score_payloads, sealed_cells, ids)
    per_sample: dict[str, Mapping[str, Mapping[str, object]]] = {}
    metrics: dict[str, CellMetrics] = {}
    for cell in CELL_ORDER:
        aggregate, details = scores[cell]
        outputs = _read_outputs(Path(str(sealed_cells[cell]["outputs"])), ids, cell)
        hard_valid = 0
        legal_rows = 0
        for sample_id in ids:
            text = outputs[sample_id]
            hard_valid += int(
                validate_hard_validity(text, registry_rows).status == "valid"
            )
            calls, parsed = parse_tool_calls_text(text)
            legal = bool(parsed and calls) and all(
                call.name in legal_key_sets_by_tool
                and tuple(sorted(call.arguments))
                in {tuple(sorted(keys)) for keys in legal_key_sets_by_tool[call.name]}
                for call in calls
            )
            legal_rows += int(legal)
        exact_count = sum(
            _metric(row["exact_match"], "exact_match") == 1.0
            for row in details.values()
        )
        tool_count = sum(
            _metric(row["tool_accuracy"], "tool_accuracy") == 1.0
            for row in details.values()
        )
        parse_count = sum(bool(row["parsed"]) for row in details.values())
        metrics[cell] = CellMetrics(
            parse_count=parse_count,
            exact_count=exact_count,
            tool_count=tool_count,
            slot_micro_precision=_metric(
                aggregate.get("slot_precision"), f"{cell} slot precision"
            ),
            slot_micro_recall=_metric(
                aggregate.get("slot_recall"), f"{cell} slot recall"
            ),
            slot_micro_f1=_metric(aggregate.get("slot_f1"), f"{cell} slot F1"),
            hard_valid_count=hard_valid,
            legal_key_set_count=legal_rows,
        )
        per_sample[cell] = details
    paired: dict[str, PairedExact] = {}
    for left in CELL_ORDER:
        for right in CELL_ORDER:
            if left == right:
                continue
            wins = harms = 0
            for sample_id in ids:
                left_exact = _metric(
                    per_sample[left][sample_id]["exact_match"], "exact_match"
                )
                right_exact = _metric(
                    per_sample[right][sample_id]["exact_match"], "exact_match"
                )
                wins += int(left_exact > right_exact)
                harms += int(left_exact < right_exact)
            paired[f"{left}_vs_{right}"] = PairedExact(
                wins, harms, len(ids) - wins - harms
            )
    return FourCellReport(ids, metrics, per_sample, paired)


def select_four_cell_oracle(
    *,
    authorization: object,
    score_payloads: Mapping[str, Mapping[str, object]],
    sealed_cells: Mapping[str, Mapping[str, object]],
) -> tuple[tuple[FourCellOracleSelection, ...], Mapping[str, object]]:
    """Choose existing sealed rows by the preregistered G8 comparator."""

    authority = _authorized(authorization)
    ids = authority.sample_ids
    # Reuse the already-tested G8 post-score oracle implementation; only the
    # frozen branch names and expected row count differ for this successor.
    selected, g8_summary = select_g8_oracle_rows(
        score_payloads=score_payloads,
        sealed_branches=sealed_cells,
        sample_ids=ids,
        expected_sample_count=EXPECTED_SAMPLE_COUNT,
        branch_order=CELL_ORDER,
    )
    selections = tuple(
        FourCellOracleSelection(
            row.sample_id,
            row.branch,
            row.text,
            row.exact_match,
            row.slot_f1,
            row.tool_accuracy,
        )
        for row in selected
    )
    return selections, {
        "samples": g8_summary["samples"],
        "selected_by_cell": g8_summary["selected_by_branch"],
        "selection_rule": "exact_match > slot_f1 > tool_accuracy > frozen_cell_order",
        "new_model_contacts": 0,
    }


def build_four_cell_oracle_artifacts(
    *,
    authorization: object,
    score_payloads: Mapping[str, Mapping[str, object]],
    sealed_cells: Mapping[str, Mapping[str, object]],
    run_dir: Path,
    parent_composed: object,
    parent_plan: object,
    parent_verified_split: object,
    data_root: Path,
    session_receipt_path: Path,
) -> Mapping[str, object]:
    """Build the zero-contact oracle bundle for its one later official score."""

    authority = _authorized(authorization)
    return build_g8_oracle_artifacts(
        score_payloads=score_payloads,
        sealed_branches=sealed_cells,
        sample_ids=authority.sample_ids,
        expected_sample_count=EXPECTED_SAMPLE_COUNT,
        parent_physical_contacts_once=16,
        run_dir=run_dir,
        parent_composed=parent_composed,
        parent_plan=parent_plan,
        parent_verified_split=parent_verified_split,
        data_root=data_root,
        session_receipt_path=session_receipt_path,
        branch_order=CELL_ORDER,
    )


def _oracle_aggregate(payload: Mapping[str, object]) -> Mapping[str, object]:
    scores = payload.get("scores")
    official = scores.get(OFFICIAL_SCORER) if isinstance(scores, Mapping) else None
    aggregate = official.get("aggregate") if isinstance(official, Mapping) else None
    if (
        not isinstance(aggregate, Mapping)
        or aggregate.get("samples") != EXPECTED_SAMPLE_COUNT
    ):
        raise NativeStructuredActionPostsealError(
            "oracle official score is missing or partial"
        )
    return aggregate


def evaluate_mechanism_gates(
    *, report: FourCellReport, oracle_score_payload: Mapping[str, object]
) -> MechanismGateVerdict:
    """Evaluate the exact frozen thresholds without fitting or tuning anything."""

    if (
        tuple(report.sample_ids) == ()
        or len(report.sample_ids) != EXPECTED_SAMPLE_COUNT
    ):
        raise NativeStructuredActionPostsealError(
            "four-cell report is not fixed-eight complete"
        )
    oracle = _oracle_aggregate(oracle_score_payload)
    oracle_exact = round(
        _metric(oracle.get("exact_match"), "oracle exact") * EXPECTED_SAMPLE_COUNT
    )
    oracle_tool = round(
        _metric(oracle.get("tool_accuracy"), "oracle tool") * EXPECTED_SAMPLE_COUNT
    )
    oracle_slot = _metric(oracle.get("slot_f1"), "oracle slot F1")
    strict_syntax_validity = all(
        report.cells[cell].parse_count == 8
        and report.cells[cell].hard_valid_count == 8
        and report.cells[cell].legal_key_set_count == 8
        for cell in STRICT_CELLS
    )
    qualifying = []
    parents = {
        "REGISTRY_STRICT_ACTION": "REGISTRY_NO_SCHEMA",
        "HANDBOOK_STRICT_ACTION": "HANDBOOK_NO_SCHEMA",
    }
    for cell in STRICT_CELLS:
        value = report.cells[cell]
        paired = report.paired[f"{cell}_vs_{parents[cell]}"]
        if (
            value.exact_count >= 7
            and value.tool_count == 8
            and value.slot_micro_f1 >= 0.9
            and paired.wins >= 3
            and paired.harms == 0
        ):
            qualifying.append(cell)
    oracle_reachability = oracle_exact == 8 and oracle_tool == 8 and oracle_slot >= 0.9
    best_strict = max(report.cells[cell].exact_count for cell in STRICT_CELLS)
    oracle_gap = oracle_exact - best_strict <= 1
    selected: str | None = None
    if qualifying:
        selected = qualifying[0]
        if set(qualifying) == set(STRICT_CELLS):
            handbook_pair = report.paired[
                "HANDBOOK_STRICT_ACTION_vs_REGISTRY_STRICT_ACTION"
            ]
            selected = (
                "HANDBOOK_STRICT_ACTION"
                if handbook_pair.wins >= 2 and handbook_pair.harms == 0
                else "REGISTRY_STRICT_ACTION"
            )
    gates = {
        "both_strict_syntax_and_hard_validity": strict_syntax_validity,
        "oracle_reachability": oracle_reachability,
        "at_least_one_strict_cell_qualifies": bool(qualifying),
        "oracle_best_strict_exact_gap_at_most_one": oracle_gap,
        "frozen_tie_rule_applied": selected is not None,
    }
    passed = all(gates.values())
    outcome = (
        "pass" if passed else ("syntax-only" if strict_syntax_validity else "failure")
    )
    return MechanismGateVerdict(passed, outcome, selected, tuple(qualifying), gates)


__all__ = [
    "CELL_ORDER",
    "HISTORICAL_CELLS",
    "STRICT_CELLS",
    "CellMetrics",
    "FourCellOracleSelection",
    "FourCellReport",
    "FourJobPlan",
    "MaterializedSubset",
    "MechanismGateVerdict",
    "NativeStructuredActionPostsealError",
    "PairedExact",
    "PostsealAuthorization",
    "analyze_four_cells",
    "build_four_cell_oracle_artifacts",
    "build_four_job_plan",
    "evaluate_mechanism_gates",
    "materialize_historical_subsets",
    "prove_strict_cells_sealed",
    "select_four_cell_oracle",
]
