"""Hash-first, no-contact bridge for the sealed SELECT/FILL flight.

The input-sealing phase reads only structural metadata and hashes response
artifacts as opaque bytes.  The analysis phase revalidates every sealed byte,
checks the completed mixed official-scoring batch and state lineage, and only
then accepts a caller-supplied scorer-side gold loader.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Callable, Mapping, Sequence

from ..reproduction.toolcall_scoring import ToolCall, parse_tool_calls_text
from .a2t_select_fill_comparison import (
    ARM_ORDER,
    DIRECT_M0,
    JOINT_DRAFT_REVISE,
    JOINT_ONE_CALL,
    SELECT_THEN_FILL,
    analyze_select_fill_comparison,
    distinct_name_set_equal,
    name_multiplicity_equal,
)


ROW_COUNT = 104
TOP_K = 32
OFFICIAL_SCORER = "a2t-toolcall"
COST_SCORER = "cost"
SEAL_SCHEMA = "saea-a2t-select-fill-postseal-input-seal-v1"
ROLE_ORDER = (
    "direct_m0",
    "joint_one_call",
    "joint_draft_revise",
    "select_then_fill",
)
ROLE_TO_ARM = dict(zip(ROLE_ORDER, ARM_ORDER, strict=True))
PHASE_ORDER = (
    "JOINT_ONE_CALL",
    "SELECT",
    "JOINT_DRAFT_REVISE",
    "FILL",
)
LINEAGE_PHASES = {
    "joint_one_call": "JOINT_ONE_CALL",
    "joint_draft_revise": "JOINT_DRAFT_REVISE",
    "select_then_fill": "FILL",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z", flags=re.ASCII)


class PostsealError(RuntimeError):
    """A seal, lineage, score batch, or post-seal input is invalid."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise PostsealError("artifact is not canonical ASCII JSON data") from error


def _artifact_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256_file(path: Path, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise PostsealError(f"cannot read {label}: {error}") from error


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PostsealError(f"{label} must be a lowercase SHA-256")
    return value


def _object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PostsealError(f"{label} must be an object")
    return value


def _read_json(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PostsealError(f"cannot read {label}: {error}") from error
    return _object(value, label)


def _read_jsonl(path: Path, label: str) -> tuple[Mapping[str, object], ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = tuple(json.loads(line) for line in lines)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PostsealError(f"cannot read {label}: {error}") from error
    if not values or any(not isinstance(value, Mapping) for value in values):
        raise PostsealError(f"{label} must be non-empty JSON objects")
    return values  # type: ignore[return-value]


def _resolve(path: object, *, base: Path, label: str) -> Path:
    if not isinstance(path, (str, Path)) or not str(path):
        raise PostsealError(f"{label} path is missing")
    candidate = Path(path)
    return (candidate if candidate.is_absolute() else base / candidate).resolve()


def _exact_ids(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) != ROW_COUNT:
        raise PostsealError(f"{label} must contain exactly 104 identities")
    ids = tuple(value)
    if len(set(ids)) != ROW_COUNT or any(
        not isinstance(item, str) or not item for item in ids
    ):
        raise PostsealError(f"{label} identities are malformed or duplicate")
    return ids  # type: ignore[return-value]


def reconstruct_pre_score_manifest_sha256(manifest_path: Path) -> str:
    """Reconstruct the exact hash of a manifest immediately before finalization."""

    document = dict(_read_json(Path(manifest_path), "finalized manifest"))
    scores = document.get("scores")
    if not isinstance(scores, Mapping):
        raise PostsealError("finalized manifest has no attached scores metadata")
    document["scores"] = None
    return hashlib.sha256(_artifact_bytes(document)).hexdigest()


def _manifest_inputs(
    receipt: Mapping[str, object], *, base: Path
) -> tuple[dict[str, dict[str, object]], tuple[str, ...]]:
    raw = receipt.get("manifests")
    if not isinstance(raw, list) or len(raw) != len(ROLE_ORDER):
        raise PostsealError("flight receipt must list exactly four manifests")
    descriptors: dict[str, dict[str, object]] = {}
    expected_ids: tuple[str, ...] | None = None
    for index, value in enumerate(raw):
        descriptor = _object(value, f"flight manifest[{index}]")
        role = descriptor.get("role")
        if role not in ROLE_ORDER or role in descriptors:
            raise PostsealError("flight manifest roles are missing or duplicate")
        if descriptor.get("status") != "COMPLETE" or descriptor.get(
            "complete_rows"
        ) != ROW_COUNT:
            raise PostsealError(f"{role} is not a complete 104-row manifest")
        path = _resolve(descriptor.get("manifest"), base=base, label=f"{role} manifest")
        digest = _hash(descriptor.get("manifest_sha256"), f"{role} manifest hash")
        if _sha256_file(path, f"{role} manifest") != digest:
            raise PostsealError(f"{role} manifest hash drift")
        document = _read_json(path, f"{role} manifest")
        split = _object(document.get("split"), f"{role} manifest split")
        ids = _exact_ids(split.get("ids"), f"{role} manifest split")
        if split.get("count") != ROW_COUNT or document.get("status") != "COMPLETED":
            raise PostsealError(f"{role} manifest is not complete")
        if document.get("scores") is not None:
            raise PostsealError(f"{role} manifest was already scored before input sealing")
        if expected_ids is None:
            expected_ids = ids
        elif ids != expected_ids:
            raise PostsealError(
                "the four manifests do not share one exact ordered roster"
            )
        outputs = _object(document.get("outputs"), f"{role} outputs metadata")
        output_path = _resolve(outputs.get("path"), base=path.parent, label=f"{role} outputs")
        output_hash = _hash(outputs.get("sha256"), f"{role} outputs hash")
        if _sha256_file(output_path, f"{role} opaque outputs") != output_hash:
            raise PostsealError(f"{role} outputs hash drift")
        descriptors[str(role)] = {
            "manifest": str(path),
            "manifest_sha256": digest,
            "outputs": str(output_path),
            "outputs_sha256": output_hash,
        }
    if set(descriptors) != set(ROLE_ORDER) or expected_ids is None:
        raise PostsealError("flight manifest roles are incomplete")
    return descriptors, expected_ids


def _validate_k32(
    path: Path, *, expected_hash: object, ids: Sequence[str], run_id: object
) -> None:
    digest = _hash(expected_hash, "K32 checkpoint hash")
    if _sha256_file(path, "K32 checkpoint") != digest:
        raise PostsealError("K32 checkpoint hash drift")
    document = _read_json(path, "K32 checkpoint")
    rows = document.get("rows")
    if (
        document.get("schema") != "saea-a2t-select-fill-post-embedding-k32-v1"
        or document.get("run_id") != run_id
        or document.get("count") != ROW_COUNT
        or document.get("top_k") != TOP_K
        or not isinstance(rows, list)
        or len(rows) != ROW_COUNT
    ):
        raise PostsealError("K32 checkpoint header is invalid")
    by_id = {}
    for value in rows:
        row = _object(value, "K32 row")
        sample_id = row.get("sample_id")
        names = row.get("candidate_tool_names")
        scores = row.get("candidate_scores")
        if (
            not isinstance(sample_id, str)
            or sample_id in by_id
            or not isinstance(names, list)
            or len(names) != TOP_K
            or len(set(names)) != TOP_K
            or any(not isinstance(name, str) or not name for name in names)
            or not isinstance(scores, list)
            or len(scores) != TOP_K
            or any(
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(float(score))
                for score in scores
            )
            or row.get("observation_state_sha256")
            != row.get("candidate_query_state_sha256")
            or row.get("candidate_set_sha256")
            != candidate_set_sha256(
                sample_id=sample_id,
                tool_names=names,
                scores=scores,
                query_state_sha256=row.get("candidate_query_state_sha256"),
            )
        ):
            raise PostsealError("K32 row identity or lineage drift")
        by_id[sample_id] = row
    if set(by_id) != set(ids):
        raise PostsealError("K32 checkpoint roster drift")


def candidate_set_sha256(
    *,
    sample_id: str,
    tool_names: Sequence[str],
    scores: Sequence[int | float],
    query_state_sha256: object,
) -> str:
    """Rebuild the launcher's complete CandidateSet identity hash."""

    _hash(query_state_sha256, "candidate query-state hash")
    return _sha256_json(
        {
            "sample_id": sample_id,
            "tool_names": list(tool_names),
            "scores": list(scores),
            "query_state_sha256": query_state_sha256,
        }
    )


def _validate_preflights(
    paths: Mapping[str, object], *, base: Path, ids: Sequence[str]
) -> tuple[dict[str, dict[str, object]], dict[tuple[str, str], frozenset[str]]]:
    if set(paths) != set(PHASE_ORDER):
        raise PostsealError("preflights must cover all four post-embedding phases")
    sealed = {}
    allowed = {}
    for phase in PHASE_ORDER:
        path = _resolve(paths[phase], base=base, label=f"{phase} preflight")
        document = _read_json(path, f"{phase} preflight")
        phase_ids = _exact_ids(document.get("sample_ids"), f"{phase} preflight")
        audits = document.get("audits")
        slots = document.get("allowed_body_hashes_by_slot")
        if (
            document.get("phase") != phase
            or document.get("status") != "COMPLETE_NO_GENERATION_SENT"
            or tuple(phase_ids) != tuple(ids)
            or not isinstance(audits, list)
            or len(audits) != ROW_COUNT
            or not isinstance(slots, list)
            or len(slots) != 2
            or any(not isinstance(slot, list) or len(slot) != ROW_COUNT for slot in slots)
        ):
            raise PostsealError(f"{phase} preflight is incomplete")
        body = {
            "schema": "saea-a2t-whole-phase-request-preflight-v1",
            "status": document["status"],
            "phase": phase,
            "sample_ids": list(phase_ids),
            "allowed_body_hashes_by_slot": slots,
            "audits": audits,
        }
        if document.get("receipt_sha256") != _sha256_json(body):
            raise PostsealError(f"{phase} preflight receipt hash drift")
        for index, sample_id in enumerate(phase_ids):
            audit = _object(audits[index], f"{phase} preflight audit")
            hashes = frozenset(
                _hash(slots[slot][index], f"{phase} body hash") for slot in range(2)
            )
            if audit.get("phase") != phase or audit.get("sample_id") != sample_id:
                raise PostsealError(f"{phase} preflight audit roster drift")
            allowed[(phase, sample_id)] = hashes
        sealed[phase] = {"path": str(path), "sha256": _sha256_file(path, f"{phase} preflight")}
    return sealed, allowed


def _validate_sends(
    path: Path,
    *,
    ids: Sequence[str],
    allowed: Mapping[tuple[str, str], frozenset[str]],
) -> None:
    rows = _read_jsonl(path, "generation send accounting")
    if len(rows) != ROW_COUNT * len(PHASE_ORDER):
        raise PostsealError("send accounting must contain exactly 416 post-embedding rows")
    seen = set()
    for row in rows:
        key = (row.get("phase"), row.get("sample_id"))
        body_hash = row.get("body_sha256")
        if (
            key in seen
            or key not in allowed
            or row.get("status") != "CONSUMED_BEFORE_IO"
            or body_hash not in allowed[key]
        ):
            raise PostsealError("send accounting does not match preflight allowlists")
        seen.add(key)
    expected = {(phase, sample_id) for phase in PHASE_ORDER for sample_id in ids}
    if seen != expected:
        raise PostsealError("send accounting phase roster is incomplete")


def _lineage_rows(
    paths: Mapping[str, object], *, base: Path, ids: Sequence[str]
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, Mapping[str, object]]]]:
    if set(paths) != set(LINEAGE_PHASES):
        raise PostsealError("state lineage must cover joint, revision, and fill")
    sealed = {}
    indexed = {}
    for role, phase in LINEAGE_PHASES.items():
        path = _resolve(paths[role], base=base, label=f"{role} lineage")
        document = _read_json(path, f"{role} lineage")
        rows = document.get("rows")
        if (
            document.get("schema") != "saea-a2t-select-fill-score-ready-lineage-v1"
            or document.get("role") != role
            or document.get("phase") != phase
            or not isinstance(rows, list)
            or len(rows) != ROW_COUNT
        ):
            raise PostsealError(f"{role} lineage header is invalid")
        by_id = {}
        for value in rows:
            row = _object(value, f"{role} lineage row")
            sample_id = row.get("sample_id")
            if not isinstance(sample_id, str) or sample_id in by_id:
                raise PostsealError(f"{role} lineage identities are invalid")
            request_hash = row.get("request_body_sha256")
            if request_hash is None:
                request_hash = row.get("source_request_body_sha256")
            response_hash = row.get("response_text_sha256")
            if response_hash is None:
                response_hash = row.get("source_response_text_sha256")
            _hash(request_hash, f"{role} request hash")
            _hash(response_hash, f"{role} response hash")
            by_id[sample_id] = row
        if set(by_id) != set(ids):
            raise PostsealError(f"{role} lineage roster drift")
        indexed[role] = by_id
        sealed[role] = {"path": str(path), "sha256": _sha256_file(path, f"{role} lineage")}
    return sealed, indexed


def _validate_select_fill_lineage(
    lineage: Mapping[str, Mapping[str, Mapping[str, object]]], ids: Sequence[str]
) -> None:
    fill_rows = lineage["select_then_fill"]
    for sample_id in ids:
        fill = fill_rows[sample_id]
        predecessor = fill.get("predecessor_response_text_sha256")
        if predecessor is None:
            predecessor = fill.get("select_response_text_sha256")
        if predecessor is None:
            predecessor = fill.get("source_select_response_sha256")
        _hash(predecessor, "FILL predecessor response hash")


def seal_inputs(
    source: Mapping[str, object], *, output_path: Path
) -> Mapping[str, object]:
    """Seal all no-meaning inputs before any scorer or gold access."""

    destination = Path(output_path)
    if destination.exists():
        raise PostsealError(f"refusing to overwrite input seal: {destination}")
    if set(source) == {"recovery_receipt"}:
        return _seal_recovery_inputs(
            _resolve(
                source["recovery_receipt"],
                base=Path.cwd(),
                label="recovery receipt",
            ),
            destination,
        )
    if set(source) != {
        "flight_receipt",
        "preflights",
        "send_accounting",
        "state_lineage",
    }:
        raise PostsealError("seal source has missing or extra fields")
    receipt_path = _resolve(source["flight_receipt"], base=Path.cwd(), label="flight receipt")
    receipt = _read_json(receipt_path, "flight receipt")
    if (
        receipt.get("schema") != "saea-a2t-select-fill-agentloop-104-flight-receipt-v1"
        or receipt.get("status") != "SEALED"
        or receipt.get("gold_opened") is not False
        or receipt.get("scorer_started") is not False
        or receipt.get("generation_contacts") != 416
        or receipt.get("inherited_generation_contacts") != 208
        or receipt.get("full_flight_generation_contacts") != 624
        or receipt.get("embedding_logical_items") != ROW_COUNT
        or receipt.get("embedding_physical_requests") != 4
    ):
        raise PostsealError("flight receipt is not the exact unscored sealed flight")
    base = receipt_path.parent
    manifests, ids = _manifest_inputs(receipt, base=base)
    checkpoint = _object(receipt.get("post_embedding_checkpoint"), "K32 receipt")
    k32_path = _resolve(checkpoint.get("path"), base=base, label="K32 checkpoint")
    _validate_k32(
        k32_path,
        expected_hash=checkpoint.get("checkpoint_sha256"),
        ids=ids,
        run_id=receipt.get("run_id"),
    )
    preflight_paths = _object(source["preflights"], "preflights")
    preflights, allowed = _validate_preflights(preflight_paths, base=base, ids=ids)
    send_path = _resolve(source["send_accounting"], base=base, label="send accounting")
    _validate_sends(send_path, ids=ids, allowed=allowed)
    lineage_paths = _object(source["state_lineage"], "state lineage")
    lineages, lineage_rows = _lineage_rows(lineage_paths, base=base, ids=ids)
    _validate_select_fill_lineage(lineage_rows, ids)
    document = {
        "schema": SEAL_SCHEMA,
        "status": "SEALED_BEFORE_SCORE_OR_GOLD",
        "run_id": receipt.get("run_id"),
        "sample_ids": list(ids),
        "flight_receipt": {"path": str(receipt_path), "sha256": _sha256_file(receipt_path, "flight receipt")},
        "manifests": manifests,
        "post_embedding_k32": {"path": str(k32_path), "sha256": _sha256_file(k32_path, "K32 checkpoint")},
        "preflights": preflights,
        "send_accounting": {"path": str(send_path), "sha256": _sha256_file(send_path, "send accounting")},
        "state_lineage": lineages,
        "response_meanings_opened": False,
        "gold_opened": False,
        "scorer_started": False,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(_artifact_bytes(document))
    return document


def _sealed_artifact(
    value: object, *, base: Path, label: str
) -> tuple[Path, dict[str, object]]:
    item = _object(value, label)
    path = _resolve(item.get("path"), base=base, label=label)
    digest = _hash(item.get("sha256"), f"{label} hash")
    if _sha256_file(path, label) != digest:
        raise PostsealError(f"{label} hash drift")
    return path, {"path": str(path), "sha256": digest}


def _seal_recovery_inputs(
    receipt_path: Path, destination: Path
) -> Mapping[str, object]:
    receipt = _read_json(receipt_path, "V5 recovery receipt")
    if (
        receipt.get("schema")
        != "saea-a2t-select-fill-zero-contact-seal-recovery-receipt-v1"
        or receipt.get("status") != "SEALED"
        or receipt.get("score_ready_manifest_count") != 4
        or receipt.get("recovery_model_contacts") != 0
        or receipt.get("recovery_embedding_contacts") != 0
        or receipt.get("recovery_scorer_contacts") != 0
        or receipt.get("gold_opened") is not False
        or receipt.get("scorer_started") is not False
        or receipt.get("response_meanings_opened") is not False
    ):
        raise PostsealError("V5 recovery receipt is not sealed before score and gold")
    base = receipt_path.parent
    manifests, ids = _manifest_inputs(receipt, base=base)
    source_seal_path, source_seal_meta = _sealed_artifact(
        receipt.get("source_seal"), base=base, label="V5 source seal"
    )
    source_seal = _read_json(source_seal_path, "V5 source seal")
    artifacts = _object(source_seal.get("artifacts"), "V5 source artifacts")
    checkpoint_path, checkpoint_meta = _sealed_artifact(
        artifacts.get("checkpoint"), base=base, label="K32 checkpoint"
    )
    _validate_k32(
        checkpoint_path,
        expected_hash=checkpoint_meta["sha256"],
        ids=ids,
        run_id=receipt.get("run_id"),
    )
    preflight_paths = {
        phase: _object(
            artifacts.get(f"{phase}:preflight"), f"{phase} preflight artifact"
        ).get("path")
        for phase in PHASE_ORDER
    }
    preflights, allowed = _validate_preflights(preflight_paths, base=base, ids=ids)
    send_path, send_meta = _sealed_artifact(
        artifacts.get("send_accounting"), base=base, label="send accounting"
    )
    _validate_sends(send_path, ids=ids, allowed=allowed)
    raw_manifests = receipt.get("manifests")
    assert isinstance(raw_manifests, list)
    manifest_by_role = {
        str(item["role"]): item for item in raw_manifests if isinstance(item, Mapping)
    }
    lineage_paths = {
        role: _object(manifest_by_role[role], f"{role} descriptor").get("lineage")
        for role in LINEAGE_PHASES
    }
    lineages, lineage_rows = _lineage_rows(lineage_paths, base=base, ids=ids)
    _validate_select_fill_lineage(lineage_rows, ids)
    select_trace_path, select_trace_meta = _sealed_artifact(
        artifacts.get("SELECT:trace"), base=base, label="SELECT trace"
    )
    document = {
        "schema": SEAL_SCHEMA,
        "status": "SEALED_BEFORE_SCORE_OR_GOLD",
        "run_id": receipt.get("run_id"),
        "sample_ids": list(ids),
        "flight_receipt": {
            "path": str(receipt_path),
            "sha256": _sha256_file(receipt_path, "V5 recovery receipt"),
        },
        "source_seal": source_seal_meta,
        "manifests": manifests,
        "post_embedding_k32": checkpoint_meta,
        "preflights": preflights,
        "send_accounting": send_meta,
        "state_lineage": lineages,
        "select_trace": select_trace_meta,
        "response_meanings_opened": False,
        "gold_opened": False,
        "scorer_started": False,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(_artifact_bytes(document))
    return document


def _rehash_seal(seal_path: Path) -> Mapping[str, object]:
    seal = _read_json(seal_path, "input seal")
    if (
        seal.get("schema") != SEAL_SCHEMA
        or seal.get("status") != "SEALED_BEFORE_SCORE_OR_GOLD"
        or seal.get("response_meanings_opened") is not False
        or seal.get("gold_opened") is not False
        or seal.get("scorer_started") is not False
    ):
        raise PostsealError("input seal header is invalid")
    for section in (
        "flight_receipt",
        "source_seal",
        "post_embedding_k32",
        "send_accounting",
        "select_trace",
    ):
        if section not in seal:
            continue
        item = _object(seal.get(section), f"seal {section}")
        path = _resolve(item.get("path"), base=seal_path.parent, label=section)
        if _sha256_file(path, section) != _hash(item.get("sha256"), f"{section} hash"):
            raise PostsealError(f"sealed {section} hash drift")
    for section in ("manifests", "preflights", "state_lineage"):
        items = _object(seal.get(section), f"seal {section}")
        for name, value in items.items():
            item = _object(value, f"seal {section}.{name}")
            path_key = "manifest" if section == "manifests" else "path"
            hash_key = "manifest_sha256" if section == "manifests" else "sha256"
            path = _resolve(item.get(path_key), base=seal_path.parent, label=f"{section}.{name}")
            expected = _hash(item.get(hash_key), f"{section}.{name} hash")
            if section == "manifests" and name != "direct_m0":
                current = _sha256_file(path, f"{section}.{name}")
                if current != expected and reconstruct_pre_score_manifest_sha256(
                    path
                ) != expected:
                    raise PostsealError(f"sealed {name} pre-score manifest hash drift")
            elif _sha256_file(path, f"{section}.{name}") != expected:
                raise PostsealError(f"sealed {section}.{name} hash drift")
            if section == "manifests":
                output = _resolve(item.get("outputs"), base=path.parent, label=f"{name} outputs")
                if _sha256_file(output, f"{name} outputs") != _hash(item.get("outputs_sha256"), f"{name} outputs hash"):
                    raise PostsealError(f"sealed {name} outputs hash drift")
    return seal


def validate_mixed_score_batch(
    summary: Mapping[str, object],
    *,
    sealed_manifests: Mapping[str, Mapping[str, object]],
    base_dir: Path,
) -> Mapping[str, Path]:
    """Validate one of the two exact four-job whole-manifest operation patterns."""

    jobs = summary.get("jobs")
    if (
        summary.get("schema") != "saea-parallel-score-batch-v1"
        or summary.get("operation") != "per-job"
        or summary.get("parallelism_boundary")
        != "one-complete-verified-manifest-per-process"
        or "no dataset sharding" not in str(summary.get("aggregation_rule"))
        or summary.get("job_count") != 4
        or summary.get("succeeded") != 4
        or summary.get("failed") != 0
        or not isinstance(jobs, list)
        or len(jobs) != 4
    ):
        raise PostsealError("score batch is not four successful whole-manifest jobs")
    for field in ("requested_max_workers", "effective_max_workers"):
        workers = summary.get(field)
        if type(workers) is not int or not 1 <= workers <= 4:
            raise PostsealError("score batch workers must be within [1, 4]")
    if set(sealed_manifests) != set(ROLE_ORDER):
        raise PostsealError("sealed manifests must cover exactly four roles")
    result = {}
    operations = {}
    for value in jobs:
        job = _object(value, "score batch job")
        role = job.get("job_id")
        if role not in ROLE_ORDER or role in result:
            raise PostsealError("score batch job identities are invalid")
        sealed = sealed_manifests[str(role)]
        expected_manifest = _resolve(sealed.get("manifest"), base=base_dir, label=f"{role} manifest")
        if (
            job.get("operation") not in {"score", "finalize"}
            or job.get("status") != "succeeded"
            or job.get("returncode") != 0
            or _resolve(job.get("manifest"), base=base_dir, label=f"{role} batch manifest") != expected_manifest
        ):
            raise PostsealError(f"{role} score job operation or manifest drift")
        operations[str(role)] = str(job["operation"])
        result_path = _resolve(job.get("result_file"), base=base_dir, label=f"{role} result")
        if _sha256_file(result_path, f"{role} result") != _hash(job.get("result_sha256"), f"{role} result hash"):
            raise PostsealError(f"{role} score result hash drift")
        result[str(role)] = result_path
    if set(result) != set(ROLE_ORDER):
        raise PostsealError("score batch does not cover exactly four roles")
    all_score = {role: "score" for role in ROLE_ORDER}
    legacy_mixed = {
        role: "score" if role == "direct_m0" else "finalize"
        for role in ROLE_ORDER
    }
    if operations not in (all_score, legacy_mixed):
        raise PostsealError(
            "score batch operation pattern must be all-score or legacy mixed"
        )
    return result


def normalize_mixed_score_payloads(
    *,
    sealed_manifests: Mapping[str, Mapping[str, object]],
    result_files: Mapping[str, Path],
) -> Mapping[str, Mapping[str, object]]:
    """Normalize direct score output and finalizer score-file output."""

    if set(sealed_manifests) != set(ROLE_ORDER) or set(result_files) != set(ROLE_ORDER):
        raise PostsealError("mixed score inputs must cover exactly four roles")
    normalized = {}
    for role in ROLE_ORDER:
        sealed = sealed_manifests[role]
        manifest = Path(str(sealed.get("manifest", ""))).resolve()
        pre_hash = _hash(sealed.get("manifest_sha256"), f"{role} manifest hash")
        payload = _read_json(Path(result_files[role]), f"{role} score result")
        if payload.get("verified") is not True or Path(str(payload.get("manifest", ""))).resolve() != manifest:
            raise PostsealError(f"{role} score result is unverified or misbound")
        score_value = payload.get("scores")
        if isinstance(score_value, Mapping):
            if _sha256_file(manifest, f"{role} manifest") != pre_hash:
                raise PostsealError(
                    f"{role} manifest changed during score-only operation"
                )
            scores = score_value
        elif isinstance(score_value, str) and score_value:
            if reconstruct_pre_score_manifest_sha256(manifest) != pre_hash:
                raise PostsealError(f"{role} finalized manifest does not reconstruct to its seal")
            if payload.get("attempt_state") != "FINALIZED":
                raise PostsealError(f"{role} finalizer did not report FINALIZED")
            scores_path = Path(score_value).resolve()
            manifest_scores = _object(_read_json(manifest, f"{role} manifest").get("scores"), f"{role} scores metadata")
            if scores_path != Path(str(manifest_scores.get("path", ""))).resolve() or _sha256_file(scores_path, f"{role} scores") != _hash(manifest_scores.get("sha256"), f"{role} scores hash"):
                raise PostsealError(f"{role} scores artifact does not match finalized manifest")
            scores = _read_json(scores_path, f"{role} scores")
        else:
            raise PostsealError(f"{role} score result has no supported scores payload")
        scores_map = _object(scores, f"{role} scores")
        if set(scores_map) != {OFFICIAL_SCORER, COST_SCORER}:
            raise PostsealError(
                f"{role} registered scorer set must be exactly "
                f"{OFFICIAL_SCORER!r} and {COST_SCORER!r}"
            )
        cost = _object(scores_map[COST_SCORER], f"{role} cost score")
        if not isinstance(cost.get("aggregate"), Mapping) or cost.get(
            "per_sample"
        ) != []:
            raise PostsealError(
                f"{role} cost score must contain an aggregate object and empty per_sample"
            )
        official = _object(scores_map[OFFICIAL_SCORER], f"{role} official score")
        if not isinstance(official.get("aggregate"), Mapping) or not isinstance(official.get("per_sample"), list):
            raise PostsealError(f"{role} official score payload is malformed")
        normalized[role] = official
    return normalized


def _names(calls: Sequence[object]) -> tuple[str, ...]:
    result = []
    for call in calls:
        name = call.get("name") if isinstance(call, Mapping) else getattr(call, "name", None)
        if not isinstance(name, str) or not name:
            raise PostsealError("tool call has no valid name")
        result.append(name)
    return tuple(result)


def sum_phase_efficiency(
    costs: Sequence[Mapping[str, object]],
) -> Mapping[str, int | float]:
    """Sum sequential phase costs without calling raw latency wall time."""

    if isinstance(costs, (str, bytes)) or not costs:
        raise PostsealError("efficiency requires at least one phase cost")
    totals: dict[str, int | float] = {
        "prompt_tokens": 0,
        "contacts": 0,
        "raw_total_latency_seconds": 0.0,
    }
    for cost in costs:
        prompt = cost.get("prompt_tokens_total")
        contacts = cost.get("calls_used")
        latency = cost.get("latency_seconds_total")
        if (
            type(prompt) is not int
            or prompt < 0
            or type(contacts) is not int
            or contacts < 0
            or isinstance(latency, bool)
            or not isinstance(latency, (int, float))
            or not math.isfinite(float(latency))
            or latency < 0
        ):
            raise PostsealError("phase efficiency cost is invalid")
        totals["prompt_tokens"] = int(totals["prompt_tokens"]) + prompt
        totals["contacts"] = int(totals["contacts"]) + contacts
        totals["raw_total_latency_seconds"] = float(
            totals["raw_total_latency_seconds"]
        ) + float(latency)
    return totals


def _outputs(path: Path, ids: Sequence[str], label: str) -> Mapping[str, tuple[ToolCall, ...]]:
    rows = _read_jsonl(path, f"{label} outputs")
    result = {}
    for row in rows:
        sample_id, text = row.get("sample_id"), row.get("text")
        if not isinstance(sample_id, str) or sample_id in result or not isinstance(text, str):
            raise PostsealError(f"{label} output rows are malformed")
        calls, _parsed = parse_tool_calls_text(text)
        result[sample_id] = tuple(calls)
    if set(result) != set(ids):
        raise PostsealError(f"{label} output roster drift")
    return result


def _official_views(
    scores: Mapping[str, Mapping[str, object]], ids: Sequence[str]
) -> tuple[dict[str, Sequence[Mapping[str, object]]], dict[str, Mapping[str, object]]]:
    outcomes = {}
    metrics = {}
    for role, arm in ROLE_TO_ARM.items():
        official = scores[role]
        aggregate = _object(official["aggregate"], f"{role} aggregate")
        per_sample = official["per_sample"]
        if not isinstance(per_sample, list):
            raise PostsealError(f"{role} per-sample scores are malformed")
        per_tier = _object(aggregate.get("per_tier"), f"{role} per-tier scores")
        by_id = {}
        for value in per_sample:
            row = _object(value, f"{role} per-sample score")
            sample_id = row.get("sample_id")
            if not isinstance(sample_id, str) or sample_id in by_id:
                raise PostsealError(f"{role} score identities are invalid")
            if row.get("tier") != sample_id.rsplit(":", 1)[0]:
                raise PostsealError(f"{role} score tier identity drift")
            for metric in ("exact_match", "tool_accuracy", "slot_f1"):
                number = row.get(metric)
                if (
                    isinstance(number, bool)
                    or not isinstance(number, (int, float))
                    or not math.isfinite(float(number))
                    or not 0 <= float(number) <= 1
                ):
                    raise PostsealError(f"{role}/{sample_id} {metric} is invalid")
            if type(row.get("parsed")) is not bool:
                raise PostsealError(f"{role}/{sample_id} parsed is invalid")
            by_id[sample_id] = row
        if set(by_id) != set(ids) or aggregate.get("samples") != ROW_COUNT:
            raise PostsealError(f"{role} official scores do not cover the sealed roster")
        tier_counts = Counter(sample_id.rsplit(":", 1)[0] for sample_id in ids)
        if len(tier_counts) != 8 or set(tier_counts.values()) != {13} or set(per_tier) != set(tier_counts):
            raise PostsealError(f"{role} official tier population is invalid")
        groups = {"overall": tuple(ids)}
        groups.update(
            {
                tier: tuple(
                    sample_id
                    for sample_id in ids
                    if sample_id.rsplit(":", 1)[0] == tier
                )
                for tier in tier_counts
            }
        )
        for group, group_ids in groups.items():
            metrics_value = aggregate if group == "overall" else per_tier[group]
            metrics_row = _object(metrics_value, f"{role}/{group} official metrics")
            if metrics_row.get("samples") != len(group_ids):
                raise PostsealError(f"{role}/{group} official sample count drift")
            for metric in (
                "exact_match",
                "tool_accuracy",
                "slot_precision",
                "slot_recall",
                "slot_f1",
            ):
                number = metrics_row.get(metric)
                if (
                    isinstance(number, bool)
                    or not isinstance(number, (int, float))
                    or not math.isfinite(float(number))
                    or not 0 <= float(number) <= 1
                ):
                    raise PostsealError(f"{role}/{group} official {metric} is invalid")
            for metric in ("exact_match", "tool_accuracy"):
                item_mean = sum(float(by_id[item][metric]) for item in group_ids) / len(
                    group_ids
                )
                if abs(float(metrics_row[metric]) - item_mean) > 1e-12:
                    raise PostsealError(
                        f"{role}/{group} official {metric} disagrees with rows"
                    )
        metrics[arm] = {
            "overall": {key: value for key, value in aggregate.items() if key != "per_tier"},
            "per_tier": per_tier,
        }
        outcomes[arm] = per_sample  # type: ignore[assignment]
    return outcomes, metrics


def _selected_names_from_lineage(
    seal: Mapping[str, object], ids: Sequence[str]
) -> tuple[Mapping[str, tuple[str, ...]], Mapping[str, int | float]]:
    trace_meta = _object(seal.get("select_trace"), "sealed SELECT trace")
    rows = _read_jsonl(Path(str(trace_meta.get("path", ""))), "SELECT trace")
    requests = {}
    responses = {}
    costs = {}
    for row in rows:
        record_id = row.get("record_id")
        payload = row.get("payload")
        if not isinstance(record_id, str) or not isinstance(payload, Mapping):
            continue
        if row.get("channel") == "MODEL_REQUEST" and record_id.endswith("/request"):
            inner = payload.get("payload")
            sample_id = inner.get("sample_id") if isinstance(inner, Mapping) else None
            request_id = inner.get("request_id") if isinstance(inner, Mapping) else None
            if isinstance(sample_id, str) and isinstance(request_id, str):
                requests[sample_id] = request_id
        elif row.get("channel") == "MODEL_RESPONSE" and record_id.endswith("/response"):
            responses[record_id.removesuffix("/response")] = payload
        elif row.get("channel") == "COST" and record_id.endswith("/cost"):
            costs[record_id.removesuffix("/cost")] = payload
    result = {}
    response_hashes = {}
    totals: dict[str, int | float] = {
        "calls_used": 0,
        "prompt_tokens_total": 0,
        "latency_seconds_total": 0.0,
    }
    for sample_id in ids:
        request_id = requests.get(sample_id)
        response = responses.get(request_id)
        cost = costs.get(request_id)
        if not isinstance(response, Mapping) or not isinstance(cost, Mapping):
            raise PostsealError("SELECT trace request/response/cost lineage is incomplete")
        text = response.get("text")
        if (
            not isinstance(text, str)
            or response.get("response_text_sha256")
            != hashlib.sha256(text.encode("ascii")).hexdigest()
        ):
            raise PostsealError("SELECT response text hash drift")
        parsed, ok = parse_tool_calls_text(text)
        if not ok or not parsed:
            raise PostsealError("SELECT canonical state is not parseable")
        result[sample_id] = _names(parsed)
        response_hashes[sample_id] = str(response["response_text_sha256"])
        for field in ("calls", "prompt_tokens", "latency_seconds"):
            number = cost.get(field)
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(float(number))
                or number < 0
            ):
                raise PostsealError(f"SELECT cost {field} is invalid")
        if cost["calls"] != 1:
            raise PostsealError("SELECT cost must record one call per sample")
        totals["calls_used"] = int(totals["calls_used"]) + 1
        totals["prompt_tokens_total"] = int(totals["prompt_tokens_total"]) + int(
            cost["prompt_tokens"]
        )
        totals["latency_seconds_total"] = float(
            totals["latency_seconds_total"]
        ) + float(cost["latency_seconds"])
    if set(result) != set(ids):
        raise PostsealError("SELECT canonical state roster drift")
    lineages = _object(seal.get("state_lineage"), "sealed state lineage")
    fill_meta = _object(lineages.get("select_then_fill"), "sealed FILL lineage")
    fill_document = _read_json(Path(str(fill_meta.get("path", ""))), "FILL lineage")
    fill_rows = fill_document.get("rows")
    if not isinstance(fill_rows, list):
        raise PostsealError("FILL lineage rows are missing")
    bind_select_fill_lineage(response_hashes, fill_rows, ids=ids)
    return result, totals


def bind_select_fill_lineage(
    select_response_hashes: Mapping[str, str],
    fill_rows: Sequence[Mapping[str, object]],
    *,
    ids: Sequence[str],
) -> None:
    """Bind every recovered FILL predecessor to its exact SELECT response."""

    by_id = {}
    for value in fill_rows:
        row = _object(value, "FILL lineage row")
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or sample_id in by_id:
            raise PostsealError("FILL lineage identities are invalid")
        by_id[sample_id] = row
    if set(by_id) != set(ids) or set(select_response_hashes) != set(ids):
        raise PostsealError("SELECT/FILL lineage roster drift")
    for sample_id in ids:
        select_hash = _hash(
            select_response_hashes[sample_id], "SELECT response text hash"
        )
        if by_id[sample_id].get("predecessor_phase") != "SELECT" or by_id[
            sample_id
        ].get("predecessor_response_text_sha256") != select_hash:
            raise PostsealError(
                f"FILL predecessor does not bind SELECT for {sample_id}"
            )


def analyze_sealed_inputs(
    *,
    seal_path: Path,
    batch_summary_path: Path,
    gold_loader: Callable[[], Mapping[str, Sequence[object]]],
    population_mode: bool = True,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 20260903,
) -> Mapping[str, object]:
    """Analyze only after every hash, score, and state-lineage check passes."""

    seal_path = Path(seal_path).resolve()
    seal = _rehash_seal(seal_path)
    manifests = _object(seal.get("manifests"), "sealed manifests")
    summary_path = Path(batch_summary_path).resolve()
    summary = _read_json(summary_path, "score batch summary")
    result_files = validate_mixed_score_batch(
        summary,
        sealed_manifests=manifests,  # type: ignore[arg-type]
        base_dir=summary_path.parent,
    )
    scores = normalize_mixed_score_payloads(
        sealed_manifests=manifests,  # type: ignore[arg-type]
        result_files=result_files,
    )
    ids = _exact_ids(seal.get("sample_ids"), "input seal roster")
    outcomes, official = _official_views(scores, ids)
    calls_by_role = {
        role: _outputs(Path(str(manifests[role]["outputs"])), ids, role)  # type: ignore[index]
        for role in ROLE_ORDER
    }
    selected_names_by_id, select_cost = _selected_names_from_lineage(seal, ids)
    for sample_id in ids:
        if _names(calls_by_role["select_then_fill"][sample_id]) != selected_names_by_id[
            sample_id
        ]:
            raise PostsealError("SELECT to FILL call-name lineage drift")
    expected = gold_loader()
    if not isinstance(expected, Mapping) or set(ids) - set(expected):
        raise PostsealError("gold loader did not cover the sealed roster")
    k32_meta = _object(seal["post_embedding_k32"], "sealed K32")
    k32 = _read_json(Path(str(k32_meta["path"])), "sealed K32")
    candidates = {
        str(row["sample_id"]): tuple(row["candidate_tool_names"])
        for row in k32["rows"]  # type: ignore[index]
    }
    reachability = []
    selector = []
    joint = []
    for sample_id in ids:
        tier = sample_id.rsplit(":", 1)[0]
        gold_names = _names(expected[sample_id])
        selected_names = selected_names_by_id[sample_id]
        one_names = _names(calls_by_role["joint_one_call"][sample_id])
        revised_names = _names(calls_by_role["joint_draft_revise"][sample_id])
        reachability.append({
            "sample_id": sample_id,
            "tier": tier,
            "sealed": True,
            "required_tools_reachable": set(gold_names).issubset(candidates[sample_id]),
        })
        selector.append({
            "sample_id": sample_id,
            "tier": tier,
            "sealed": True,
            "distinct_name_set_correct": distinct_name_set_equal(gold_names, selected_names),
            "multiplicity_correct": name_multiplicity_equal(gold_names, selected_names),
            "gold_call_count": len(gold_names),
        })
        joint.append({
            "sample_id": sample_id,
            "tier": tier,
            "sealed": True,
            "one_call_distinct_name_set_correct": distinct_name_set_equal(gold_names, one_names),
            "one_call_multiplicity_correct": name_multiplicity_equal(gold_names, one_names),
            "draft_distinct_name_set_correct": distinct_name_set_equal(gold_names, one_names),
            "draft_multiplicity_correct": name_multiplicity_equal(gold_names, one_names),
            "revised_distinct_name_set_correct": distinct_name_set_equal(gold_names, revised_names),
            "revised_multiplicity_correct": name_multiplicity_equal(gold_names, revised_names),
        })
    costs = {}
    for role in ROLE_ORDER:
        manifest = _read_json(Path(str(manifests[role]["manifest"])), f"{role} manifest")  # type: ignore[index]
        costs[role] = _object(manifest.get("cost"), f"{role} cost")

    def efficiency(*roles: str) -> Mapping[str, int | float]:
        return sum_phase_efficiency(tuple(costs[role] for role in roles))

    split_efficiency = sum_phase_efficiency(
        (select_cost, costs["select_then_fill"])
    )

    report = analyze_select_fill_comparison(
        outcomes_by_arm=outcomes,
        official_metrics_by_arm=official,
        candidate_reachability=reachability,
        selector_diagnostics=selector,
        joint_diagnostics=joint,
        efficiency_by_arm={
            DIRECT_M0: efficiency("direct_m0"),
            JOINT_ONE_CALL: efficiency("joint_one_call"),
            JOINT_DRAFT_REVISE: efficiency("joint_one_call", "joint_draft_revise"),
            SELECT_THEN_FILL: split_efficiency,
        },
        post_seal=True,
        population_mode=population_mode,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
    )
    return {
        **report,
        "input_seal": {"path": str(seal_path), "sha256": _sha256_file(seal_path, "input seal")},
        "score_batch": {"path": str(summary_path), "sha256": _sha256_file(summary_path, "score batch summary")},
        "gold_load_calls": 1,
    }


__all__ = [
    "LINEAGE_PHASES",
    "PHASE_ORDER",
    "PostsealError",
    "ROLE_ORDER",
    "SEAL_SCHEMA",
    "analyze_sealed_inputs",
    "bind_select_fill_lineage",
    "candidate_set_sha256",
    "normalize_mixed_score_payloads",
    "reconstruct_pre_score_manifest_sha256",
    "seal_inputs",
    "sum_phase_efficiency",
    "validate_mixed_score_batch",
]
