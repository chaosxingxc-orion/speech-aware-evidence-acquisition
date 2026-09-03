#!/usr/bin/env python3
"""Seal zero-contact successors for the completed semantic AgentLoop flight.

The source flight completed every registered model and embedding contact, then
failed while verifying its first run manifest because the roster receipt used
a noncanonical split digest.  This recovery never starts a service, contacts a
model, embeds text, opens gold, or invokes a scorer.  It first hash-seals the
immutable source bytes, then derives the missing output and trace-manifest
artifacts mechanically and writes separate successor bundles.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    TraceRecord,
)
from speech_aware_evidence_acquisition.core.bundle import verify_bundle  # noqa: E402
from speech_aware_evidence_acquisition.core.config import protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)


RUN_ID = "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1"
MISSION_ID = "mission-20260903t190000z-semantic104-v1"
FAILED_RECOVERY_DIRNAME = "zero-contact-recovery-v1"
RECOVERY_DIRNAME = "zero-contact-recovery-v2"
FAILED_RECOVERY_SOURCE_SEAL_SHA256 = (
    "28a7d2f38f433ed86301944b4f830007d971d3d3946ba6c3e50b25e591378642"
)
FAILED_RECOVERY_DIRECT_MANIFEST_SHA256 = (
    "4dfa112f965225d0916eabc254733aadf5704e30235f122af6db42489fac1b6c"
)
ROSTER_PATH = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-fresh-agentloop-roster/flight-roster-receipt.json"
)
ROSTER_SHA256 = "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e"
DECLARED_SPLIT_IDENTITY = (
    "84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0"
)
CANONICAL_SPLIT_IDENTITY = (
    "8aa80c0b24c42bba812ad8060bc7e89817f54e5401b6cfb98b029ed8a6311670"
)
CONFIG_HASH = "b35b37829cef7fb792980c4099efb6a5efb34605c0b1da5be97a5b12aed38113"
ARM = "speech-feature-query"
DECLARED_PROTOCOL_HASH = (
    "6d793633efd6d7222d9b1cf0811520c116fca90e9043b3a3222284350f499c38"
)
CANONICAL_PROTOCOL_HASH = (
    "b96cbc07d54c7f0f20bc15b4c160c1f3a740a07aeaa93b661ecae42bdc57378e"
)
SOURCE_AUTHORITY_SHA256 = (
    "b397b56700d76987a3c1b504fe611019f35c7c1a433bea1010211db1096e283b"
)
SOURCE_FAILURE_SHA256 = (
    "0b28034db707cc4e560b356f8e51b3605c87a0b00361f60e5784e825ee14b976"
)
SOURCE_DIRECT_MANIFEST_SHA256 = (
    "c18c215e9676497d941b25c3c180e1a487586349b1e6638f3b0ed4ebdd6fabb5"
)
SOURCE_DIRECT_OUTPUTS_SHA256 = (
    "f0dce515dcf65c5c81b0f92fd2d1478a0d3e6ecc33e71065535d101eb5315caf"
)
SOURCE_DIRECT_TRACE_MANIFEST_SHA256 = (
    "99e6614a72c40bb5a333952a7e9eb0f2ef22626c3035c7b0f13a49ae4fe47441"
)
SOURCE_DIRECT_RUNTIME_RECEIPT_SHA256 = (
    "8356f718fcaab6bec7de7facda3c7231175b8a9c1a4cd01d17c7ca713c0e4e01"
)
SOURCE_DIRECT_SEMANTIC_TRACE_SHA256 = (
    "a40906b3f90452e3f2b36567d814cf3c4a49f5bb518d08287f0fff0f5028e869"
)
UMBRELLA_LOCK_SHA256 = (
    "fe843e1b4789d3f3b47731ddf5b1bb42d430b05afe74292afc9ca0a6368e2864"
)
SAMPLE_COUNT = 104
EXPECTED_SCORERS = ("a2t-toolcall", "cost")
EMBEDDING_RUN_ID = f"{RUN_ID}-EMBED"
EMBEDDING_ATTEMPT_ID = "attempt-20260903t190000z-semantic104-embedding"
EMBEDDING_ATTEMPT_SHA256 = (
    "0a1458e3729e9a32d09ce086527d2b6f7ae0e977dc27c39d5e6fdb1fbacbe540"
)


class RecoveryError(RuntimeError):
    """The immutable source or zero-contact successor failed closed."""


ROLE_ORDER = (
    "direct_m0",
    "obs_semantic_retrieval",
    "transcript_top16_use",
    "model_query_top16_use",
    "rrf_fused_top16_use",
    "same_stratum_shuffled_fused_use",
)

ROLE_SPECS: Mapping[str, Mapping[str, object]] = {
    "direct_m0": {
        "attempt_id": "attempt-20260903t190000z-semantic104-direct",
        "attempt_sha256": "92d50bb6a1c7a49c6e6f617c231d5ae828fd569004e6aa739a93ee65e6c9d6fd",
        "trace_sha256": "a0aea3237f47f6dc9a543abfc733b2b4177d5b4f9eb75de3d00c3180933456d0",
        "trace_bytes": 5_944_771,
        "trace_records": 312,
        "session_window": "generation-pre-embedding",
    },
    "obs_semantic_retrieval": {
        "attempt_id": "attempt-20260903t190000z-semantic104-obs",
        "attempt_sha256": "0d9406def0273f8bca103d993df3f6b65f70d9841332a1bc11ec6b41dba8aa22",
        "trace_sha256": "9ac8a33527fbbdae943030ed4e2b6ea9dc33bd9d361376ab86158662b43346fc",
        "trace_bytes": 1_101_617,
        "trace_records": 728,
        "session_window": "generation-pre-embedding",
    },
    "transcript_top16_use": {
        "attempt_id": "attempt-20260903t190000z-semantic104-transcript",
        "attempt_sha256": "6e7b106131d17dfe8183e9ef240dc8878839f7269d04761d2ac91231a4d9c819",
        "trace_sha256": "c09d2c25418b0088fd81e1cedc784b7c5a45bcc1563ebbfe46a12d304954cc82",
        "trace_bytes": 6_715_491,
        "trace_records": 728,
        "session_window": "generation-post-embedding",
    },
    "model_query_top16_use": {
        "attempt_id": "attempt-20260903t190000z-semantic104-query",
        "attempt_sha256": "a8198e20e7d44e4d4748ce6192e84c6fa6c6930350a64a4c36cba3f6bd4ac1a1",
        "trace_sha256": "760688c0785c3a8ad431bf2b99c94063ba35455d261bb165f5b90ccde7202007",
        "trace_bytes": 6_498_347,
        "trace_records": 728,
        "session_window": "generation-post-embedding",
    },
    "rrf_fused_top16_use": {
        "attempt_id": "attempt-20260903t190000z-semantic104-fused",
        "attempt_sha256": "b0c5b200dfb14534f835a5c07be68e538b0325bb93e0dd0874f71bbc5847c178",
        "trace_sha256": "239f1285c3cbe2463af491fab3023bd2fadefb3f067d171ce3c8ca615e66b425",
        "trace_bytes": 6_668_241,
        "trace_records": 728,
        "session_window": "generation-post-embedding",
    },
    "same_stratum_shuffled_fused_use": {
        "attempt_id": "attempt-20260903t190000z-semantic104-shuffled",
        "attempt_sha256": "ab0cff6dfb011aef5968d20fdf410687560752ce7807c10884933022cd490201",
        "trace_sha256": "47ec0126ed245a5fd13c13b70b60bdd8cf797601f04f27d031d34eab0b3500a6",
        "trace_bytes": 6_665_134,
        "trace_records": 728,
        "session_window": "generation-post-embedding",
    },
}

SERVICE_HASHES = {
    "services/embedding/governed-tool-receipt.json": (
        "0471e9d5a79b7152a77b93f014cefef20a88b4c65b29dd9ed8cd6d6948e3c2a9"
    ),
    "services/embedding/session-receipt.json": (
        "ccbdcb14cb4a7662a402a379b4387e9d315cc93c4234d1cec586f53be7aa4985"
    ),
    "services/embedding/stop-receipt.json": (
        "4da9696e4a5e81d3237e5b31db03224ca671b3002d1756d705ec7eaa85c5a9d7"
    ),
    "services/generation-post-embedding/session-receipt.json": (
        "7a7c144c94e7914ef672bbf07bb8f2609fc747d802d044143a72593555c37b5d"
    ),
    "services/generation-post-embedding/stop-receipt.json": (
        "3fc3d0a7b8a0727cf30e1354cc7a53cbadf589183bede9a5ffcbb609ee8b4ba0"
    ),
    "services/generation-pre-embedding/session-receipt.json": (
        "ad40055ae682da67efc75c202e6873f07c64894cb3b471c4a8cd40117f2a8f33"
    ),
    "services/generation-pre-embedding/stop-receipt.json": (
        "b80443e2046d2fccdb7f09a918361784207dc4550da9dd84f2f175e5e39207f0"
    ),
}

EXPECTED_OUTPUT_HASHES = {
    "direct_m0": "f0dce515dcf65c5c81b0f92fd2d1478a0d3e6ecc33e71065535d101eb5315caf",
    "obs_semantic_retrieval": "07ec28ceb229aa0130fec145026b00a6164d7d09d311cfaaea02101c993f5def",
    "transcript_top16_use": "07727c82946387bcc17b856c276a0774f11d539482c4b3b9db7e72cc3a343242",
    "model_query_top16_use": "512bd571e9c3fefed75b38b718403d40dad0eccbdedb9d5086133737abaceea8",
    "rrf_fused_top16_use": "11bca0e5847fb738e55171fee4a4d129fdb90f2545d8f7262fd641bc1d7e005d",
    "same_stratum_shuffled_fused_use": (
        "ccbd2d70a29228a74af4b4416c2fcb5008b42ed7b3c6094d4c051001559c90a0"
    ),
}

EXPECTED_TRACE_MANIFEST_HASHES = {
    "direct_m0": "99e6614a72c40bb5a333952a7e9eb0f2ef22626c3035c7b0f13a49ae4fe47441",
    "obs_semantic_retrieval": "da630b2fe1934972d5fae7afc0148206b8e4a06c13682283917afe2b5482df13",
    "transcript_top16_use": "462ca4d8fd7713405b7ae113121a261a9d9c15195bc1bbdce2380b2d18519cf0",
    "model_query_top16_use": "1c1bf052401c30ef51f8eb77cac8e0e9be949090b6cb0b7ea7a1913d89381afc",
    "rrf_fused_top16_use": "121bec8b7cf93d4bd114ad65e5d61dea2c32b61141023df2434757a4bddf60bb",
    "same_stratum_shuffled_fused_use": (
        "76693bdd9825837745469ac2326480344ab6a802f01f522838905c3e3dfa6132"
    ),
}

_PLAN_FIELDS = (
    "run_id",
    "execution_profile",
    "carrier_lock_key",
    "split_role",
    "split_identity_hash",
    "planned_model_calls",
    "planned_gpu_hours",
    "planned_speech_audio_seconds",
    "protocol_hash",
    "attempt_id",
    "schema",
    "study",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RecoveryError(f"{label} is not readable UTF-8 JSON: {error}") from error
    if not isinstance(document, dict):
        raise RecoveryError(f"{label} must be a JSON object")
    return document


def _require_hash(path: Path, expected: str, label: str) -> Path:
    path = Path(path)
    if not path.is_file() or _sha256(path) != expected:
        raise RecoveryError(f"{label} SHA-256 drift")
    return path


def _artifact(path: Path) -> dict[str, str]:
    return {"path": str(Path(path).resolve()), "sha256": _sha256(path)}


def _exclusive_json(path: Path, document: Mapping[str, object]) -> None:
    raw = json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _exclusive_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    raw = "".join(
        json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _mission(data_root: Path) -> Path:
    return Path(data_root) / "runs" / RUN_ID / MISSION_ID


def _attempt_path(data_root: Path, attempt_id: str) -> Path:
    return Path(data_root) / "attempts" / RUN_ID / f"{attempt_id}.json"


def _embedding_attempt_path(data_root: Path) -> Path:
    return (
        Path(data_root) / "attempts" / EMBEDDING_RUN_ID / f"{EMBEDDING_ATTEMPT_ID}.json"
    )


def _source_trace(mission: Path, role: str) -> Path:
    return mission / role / f"{RUN_ID}.trace.jsonl"


def _binary_line_count(path: Path) -> int:
    raw = Path(path).read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise RecoveryError(f"source trace lacks its terminal LF: {path}")
    return raw.count(b"\n")


def _load_roster() -> tuple[dict[str, object], tuple[str, ...]]:
    _require_hash(ROSTER_PATH, ROSTER_SHA256, "fresh roster")
    roster = _read_object(ROSTER_PATH, "fresh roster")
    items = roster.get("items")
    if not isinstance(items, list) or len(items) != SAMPLE_COUNT:
        raise RecoveryError("fresh roster must contain exactly 104 items")
    sample_ids = tuple(
        item.get("sample_id") if isinstance(item, Mapping) else None for item in items
    )
    if (
        any(not isinstance(sample_id, str) or not sample_id for sample_id in sample_ids)
        or len(set(sample_ids)) != SAMPLE_COUNT
    ):
        raise RecoveryError("fresh roster sample identities are malformed")
    canonical = split_identity_hash(prefixed("audio2tool", sample_ids))
    if canonical != CANONICAL_SPLIT_IDENTITY:
        raise RecoveryError("fresh roster canonical split identity drift")
    if protocol_hash(CONFIG_HASH, ARM, canonical) != CANONICAL_PROTOCOL_HASH:
        raise RecoveryError("canonical bundle protocol identity drift")
    return roster, tuple(str(sample_id) for sample_id in sample_ids)


def validate_source_bytes(data_root: Path) -> dict[str, object]:
    """Validate all source bytes without parsing any model response trace."""

    mission = _mission(data_root)
    authority_path = _require_hash(
        mission / "authority-binding.json", SOURCE_AUTHORITY_SHA256, "source authority"
    )
    failure_path = _require_hash(
        mission / "failure-receipt.json", SOURCE_FAILURE_SHA256, "source failure"
    )
    direct_dir = mission / "direct_m0"
    direct_manifest = _require_hash(
        direct_dir / f"{RUN_ID}.run-manifest.json",
        SOURCE_DIRECT_MANIFEST_SHA256,
        "source direct manifest",
    )
    _require_hash(
        direct_dir / f"{RUN_ID}.outputs.jsonl",
        SOURCE_DIRECT_OUTPUTS_SHA256,
        "source direct outputs",
    )
    _require_hash(
        direct_dir / f"{RUN_ID}.trace-manifest.json",
        SOURCE_DIRECT_TRACE_MANIFEST_SHA256,
        "source direct trace manifest",
    )
    _require_hash(
        direct_dir / "phase-runtime-receipt.json",
        SOURCE_DIRECT_RUNTIME_RECEIPT_SHA256,
        "source direct runtime receipt",
    )
    _require_hash(
        direct_dir / "semantic-trace.json",
        SOURCE_DIRECT_SEMANTIC_TRACE_SHA256,
        "source direct semantic trace",
    )
    for relpath, digest in SERVICE_HASHES.items():
        _require_hash(mission / relpath, digest, f"source {relpath}")

    authority = _read_object(authority_path, "source authority")
    plans = authority.get("plans")
    if not isinstance(plans, Mapping) or set(plans) != set(ROLE_ORDER):
        raise RecoveryError("source authority execution-plan set drift")
    failure = _read_object(failure_path, "source failure")
    if (
        failure.get("status") != "ABORTED"
        or "split.identity_hash" not in str(failure.get("reason", ""))
        or DECLARED_SPLIT_IDENTITY[:12] not in str(failure.get("reason", ""))
        or CANONICAL_SPLIT_IDENTITY[:12] not in str(failure.get("reason", ""))
    ):
        raise RecoveryError("source failure is not the registered split-digest refusal")

    trace_seals: dict[str, object] = {}
    attempt_seals: dict[str, object] = {}
    for role in ROLE_ORDER:
        spec = ROLE_SPECS[role]
        trace = _require_hash(
            _source_trace(mission, role), str(spec["trace_sha256"]), f"{role} trace"
        )
        if trace.stat().st_size != spec["trace_bytes"]:
            raise RecoveryError(f"{role} trace byte count drift")
        line_count = _binary_line_count(trace)
        if line_count != spec["trace_records"]:
            raise RecoveryError(f"{role} trace record count drift")
        trace_seals[role] = {
            "path": str(trace.resolve()),
            "bytes": trace.stat().st_size,
            "records": line_count,
            "sha256": spec["trace_sha256"],
        }

        attempt_id = str(spec["attempt_id"])
        attempt_path = _require_hash(
            _attempt_path(data_root, attempt_id),
            str(spec["attempt_sha256"]),
            f"{role} source attempt",
        )
        attempt = _read_object(attempt_path, f"{role} source attempt")
        actual = attempt.get("actual")
        if (
            attempt.get("run_id") != RUN_ID
            or attempt.get("attempt_id") != attempt_id
            or attempt.get("state") != "ABORTED"
            or not isinstance(actual, Mapping)
            or actual.get("calls") != SAMPLE_COUNT
            or abs(float(actual.get("audio_seconds", -1)) - 554.255707) > 1e-9
        ):
            raise RecoveryError(
                f"{role} source attempt is not the terminal 104-call source"
            )
        source_plan = plans.get(role)
        if (
            not isinstance(source_plan, Mapping)
            or source_plan.get("attempt_id") != attempt_id
            or source_plan.get("split_identity_hash") != DECLARED_SPLIT_IDENTITY
            or source_plan.get("protocol_hash") != DECLARED_PROTOCOL_HASH
        ):
            raise RecoveryError(f"{role} source execution plan drift")
        attempt_seals[role] = {
            "path": str(attempt_path.resolve()),
            "sha256": spec["attempt_sha256"],
            "state": "ABORTED",
            "actual_calls": SAMPLE_COUNT,
            "actual_audio_seconds": 554.255707,
        }

    embedding = _read_object(
        mission / "services/embedding/governed-tool-receipt.json",
        "governed embedding receipt",
    )
    if (
        embedding.get("status") != "FINALIZED"
        or embedding.get("logical_contact_count") != 208
        or embedding.get("physical_request_count") != 7
    ):
        raise RecoveryError(
            "governed embedding receipt is not the completed 208/7 source"
        )
    embedding_attempt_path = _require_hash(
        _embedding_attempt_path(data_root),
        EMBEDDING_ATTEMPT_SHA256,
        "source embedding attempt",
    )
    embedding_attempt = _read_object(embedding_attempt_path, "source embedding attempt")
    embedding_actual = embedding_attempt.get("actual")
    if (
        embedding_attempt.get("run_id") != EMBEDDING_RUN_ID
        or embedding_attempt.get("attempt_id") != EMBEDDING_ATTEMPT_ID
        or embedding_attempt.get("state") != "FINALIZED"
        or not isinstance(embedding_actual, Mapping)
        or embedding_actual.get("calls") != 208
        or float(embedding_actual.get("audio_seconds", -1)) != 0.0
    ):
        raise RecoveryError(
            "source embedding attempt is not the finalized 208-contact source"
        )

    failed_recovery = mission / FAILED_RECOVERY_DIRNAME
    failed_source_seal = _require_hash(
        failed_recovery / "source-seal.json",
        FAILED_RECOVERY_SOURCE_SEAL_SHA256,
        "failed V1 recovery source seal",
    )
    failed_direct_manifest = _require_hash(
        failed_recovery / "direct_m0" / f"{RUN_ID}.run-manifest.json",
        FAILED_RECOVERY_DIRECT_MANIFEST_SHA256,
        "failed V1 recovery direct manifest",
    )

    manifest = _read_object(direct_manifest, "source direct manifest")
    plan = manifest.get("plan")
    split = manifest.get("split")
    if (
        manifest.get("status") != "COMPLETED"
        or manifest.get("protocol_hash") != DECLARED_PROTOCOL_HASH
        or manifest.get("scorers") != ["a2t-toolcall", "cost"]
        or not isinstance(plan, Mapping)
        or plan.get("split_identity_hash") != DECLARED_SPLIT_IDENTITY
        or not isinstance(split, Mapping)
        or split.get("identity_hash") != DECLARED_SPLIT_IDENTITY
    ):
        raise RecoveryError("source direct manifest defect surface drift")
    return {
        "schema": "saea-a2t-semantic-agentloop-104-source-seal-v1",
        "run_id": RUN_ID,
        "mission_id": MISSION_ID,
        "source_authority": _artifact(authority_path),
        "source_failure": _artifact(failure_path),
        "source_direct_manifest": _artifact(direct_manifest),
        "failed_recovery_v1": {
            "status": "TERMINAL_ZERO_CONTACT_ASSERTION_FAILURE",
            "reason": (
                "AgentLoop traces contain two USE records and no OBS record per "
                "sample; the failed assertion expected one of each"
            ),
            "source_seal": _artifact(failed_source_seal),
            "verified_direct_manifest": _artifact(failed_direct_manifest),
            "model_contacts": 0,
            "embedding_contacts": 0,
            "scorer_contacts": 0,
            "gold_opened": False,
        },
        "source_traces": trace_seals,
        "source_attempts": attempt_seals,
        "source_embedding_attempt": {
            **_artifact(embedding_attempt_path),
            "state": "FINALIZED",
            "actual_calls": 208,
            "actual_audio_seconds": 0.0,
        },
        "service_receipts": {
            relpath: {"path": str((mission / relpath).resolve()), "sha256": digest}
            for relpath, digest in sorted(SERVICE_HASHES.items())
        },
        "source_generation_contacts": 624,
        "source_embedding_logical_contacts": 208,
        "source_embedding_physical_requests": 7,
        "source_speech_audio_seconds": 6 * 554.255707,
        "model_contacts_during_source_seal": 0,
        "embedding_contacts_during_source_seal": 0,
        "scorer_contacts_during_source_seal": 0,
        "gold_opened_during_source_seal": False,
        "response_meanings_opened_during_source_seal": False,
    }


def _trace_documents(path: Path, role: str) -> tuple[dict[str, object], ...]:
    documents: list[dict[str, object]] = []
    record_ids: set[str] = set()
    for number, line in enumerate(
        path.read_text(encoding="utf-8").split("\n"), start=1
    ):
        if number > int(ROLE_SPECS[role]["trace_records"]):
            if line:
                raise RecoveryError(f"{role} trace has an unexpected trailing record")
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise RecoveryError(
                f"{role} trace line {number} is malformed: {error}"
            ) from error
        if not isinstance(document, dict) or set(document) != {
            "channel",
            "record_id",
            "payload",
        }:
            raise RecoveryError(f"{role} trace line {number} has an invalid shape")
        record_id = document.get("record_id")
        if not isinstance(record_id, str) or record_id in record_ids:
            raise RecoveryError(f"{role} trace has a malformed or duplicate record id")
        TraceRecord(
            channel=str(document.get("channel")),
            record_id=record_id,
            payload=document.get("payload"),  # type: ignore[arg-type]
        ).validate()
        record_ids.add(record_id)
        documents.append(document)
    if len(documents) != ROLE_SPECS[role]["trace_records"]:
        raise RecoveryError(f"{role} trace row count drift after parse")
    return tuple(documents)


def _derive_bundle_material(
    documents: Sequence[Mapping[str, object]],
    *,
    role: str,
    expected_sample_ids: Sequence[str],
) -> tuple[
    tuple[dict[str, object], ...], dict[str, object], dict[str, str], Counter[str]
]:
    channels: dict[str, dict[str, Mapping[str, object]]] = {
        "MODEL_REQUEST": {},
        "MODEL_RESPONSE": {},
        "COST": {},
    }
    record_hashes: dict[str, str] = {}
    channel_counts: Counter[str] = Counter()
    suffixes = {
        "MODEL_REQUEST": "/request",
        "MODEL_RESPONSE": "/response",
        "COST": "/cost",
    }
    for document in documents:
        channel = str(document["channel"])
        record_id = str(document["record_id"])
        payload = document["payload"]
        if not isinstance(payload, Mapping):
            raise RecoveryError(f"{role} trace payload is not an object")
        record_hashes[record_id] = TraceRecord(
            channel, record_id, payload
        ).content_hash()
        channel_counts[channel] += 1
        if channel not in channels:
            continue
        suffix = suffixes[channel]
        if not record_id.endswith(suffix):
            raise RecoveryError(f"{role} transport record suffix drift")
        request_id = record_id[: -len(suffix)]
        if not request_id or request_id in channels[channel]:
            raise RecoveryError(f"{role} transport request identity drift")
        channels[channel][request_id] = payload

    expected_channel_counts = Counter(
        {
            "MODEL_REQUEST": SAMPLE_COUNT,
            "MODEL_RESPONSE": SAMPLE_COUNT,
            "COST": SAMPLE_COUNT,
        }
    )
    if role != "direct_m0":
        expected_channel_counts.update(
            {"ORG": SAMPLE_COUNT, "SUPPLY": SAMPLE_COUNT, "USE": SAMPLE_COUNT * 2}
        )
    if channel_counts != expected_channel_counts:
        raise RecoveryError(
            f"{role} trace channel counts drift: {dict(channel_counts)}"
        )

    requests = channels["MODEL_REQUEST"]
    responses = channels["MODEL_RESPONSE"]
    costs = channels["COST"]
    if set(requests) != set(responses) or set(requests) != set(costs):
        raise RecoveryError(f"{role} request, response, and cost identities differ")
    request_by_sample: dict[str, str] = {}
    for request_id, request in requests.items():
        inner = request.get("payload")
        sample_id = inner.get("sample_id") if isinstance(inner, Mapping) else None
        if (
            not isinstance(sample_id, str)
            or sample_id in request_by_sample
            or request.get("arm") != ARM
        ):
            raise RecoveryError(f"{role} request sample or arm identity drift")
        request_by_sample[sample_id] = request_id
    if set(request_by_sample) != set(expected_sample_ids):
        raise RecoveryError(f"{role} trace sample set differs from the sealed roster")

    rows: list[dict[str, object]] = []
    totals: dict[str, int | float | str] = {
        "calls_used": 0,
        "audio_seconds_used": 0.0,
        "latency_seconds_total": 0.0,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
    }
    for sample_id in sorted(request_by_sample):
        request_id = request_by_sample[sample_id]
        request = requests[request_id]
        response = responses[request_id]
        text = response.get("text")
        if not isinstance(text, str):
            raise RecoveryError(f"{role}/{sample_id} response text is not text")
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if response.get("response_text_sha256") != text_hash:
            raise RecoveryError(f"{role}/{sample_id} response text hash drift")
        request_hash = request.get("payload_sha256")
        response_hash = response.get("response_sha256")
        if not all(
            isinstance(value, str) and len(value) == 64
            for value in (request_hash, response_hash)
        ):
            raise RecoveryError(f"{role}/{sample_id} transport hash is malformed")
        rows.append(
            {
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": "audio2tool",
                "arm": ARM,
                "text": text,
                "admitted": True,
                "request_sha256": request_hash,
                "response_sha256": response_hash,
                "response_text_sha256": text_hash,
                "phase": role,
            }
        )

    for cost in costs.values():
        fields = (
            "calls",
            "audio_seconds",
            "latency_seconds",
            "prompt_tokens",
            "completion_tokens",
        )
        for field in fields:
            value = cost.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                raise RecoveryError(f"{role} cost field {field!r} is invalid")
        if cost["calls"] != 1:
            raise RecoveryError(f"{role} cost trace is not one call per sample")
        totals["calls_used"] = int(totals["calls_used"]) + 1
        totals["audio_seconds_used"] = float(totals["audio_seconds_used"]) + float(
            cost["audio_seconds"]
        )
        totals["latency_seconds_total"] = float(
            totals["latency_seconds_total"]
        ) + float(cost["latency_seconds"])
        totals["prompt_tokens_total"] = int(totals["prompt_tokens_total"]) + int(
            cost["prompt_tokens"]
        )
        totals["completion_tokens_total"] = int(
            totals["completion_tokens_total"]
        ) + int(cost["completion_tokens"])
    if (
        totals["calls_used"] != SAMPLE_COUNT
        or abs(float(totals["audio_seconds_used"]) - 554.255707) > 1e-6
    ):
        raise RecoveryError(f"{role} recovered cost total drift")
    totals.update({"tool_calls": 0, "umbrella_lock_sha256": UMBRELLA_LOCK_SHA256})
    return tuple(rows), totals, record_hashes, channel_counts


def _normalized_plan(source_plan: Mapping[str, object]) -> dict[str, object]:
    normalized = {field: source_plan[field] for field in _PLAN_FIELDS}
    normalized["split_identity_hash"] = CANONICAL_SPLIT_IDENTITY
    normalized["protocol_hash"] = CANONICAL_PROTOCOL_HASH
    ExecutionPlan(**normalized).validate()
    return normalized


def _build_successor_manifest(
    *,
    template: Mapping[str, object],
    authority: Mapping[str, object],
    role: str,
    sample_ids: Sequence[str],
    outputs: Path,
    raw_trace: Path,
    trace_manifest: Path,
    session_receipt: Path,
    cost: Mapping[str, object],
    source_trace: Path,
    source_failure: Path,
    source_authority: Path,
    source_attempt: Path,
) -> dict[str, object]:
    manifest = copy.deepcopy(dict(template))
    plans = authority["plans"]
    if not isinstance(plans, Mapping) or not isinstance(plans.get(role), Mapping):
        raise RecoveryError(f"source authority lacks plan {role!r}")
    source_plan = dict(plans[role])
    normalized_plan = _normalized_plan(source_plan)
    manifest.update(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "COMPLETED",
            "failure_reason": None,
            "protocol_hash": CANONICAL_PROTOCOL_HASH,
            "plan": normalized_plan,
            "split": {
                "name": "",
                "role": "discovery",
                "carrier_lock_key": "audio2tool",
                "identity_hash": CANONICAL_SPLIT_IDENTITY,
                "count": SAMPLE_COUNT,
                "ids": sorted(sample_ids),
            },
            "session_receipt": _artifact(session_receipt),
            "outputs": _artifact(outputs),
            "raw_trace": _artifact(raw_trace),
            "trace_manifest": _artifact(trace_manifest),
            "scores": None,
            "scorers": list(EXPECTED_SCORERS),
            "cost": dict(cost),
            "attempt": {
                "run_id": RUN_ID,
                "attempt_id": ROLE_SPECS[role]["attempt_id"],
                "state_path": str(source_attempt.resolve()),
            },
            "semantic_role": role,
            "recovery_provenance": {
                "schema": "saea-a2t-semantic-agentloop-104-zero-contact-successor-v1",
                "status": "EXTERNALLY_SEALED_SOURCE",
                "source_attempt_state": "ABORTED",
                "source_attempt": _artifact(source_attempt),
                "source_execution_plan": source_plan,
                "source_trace": _artifact(source_trace),
                "source_failure": _artifact(source_failure),
                "source_authority": _artifact(source_authority),
                "declared_split_identity_hash": DECLARED_SPLIT_IDENTITY,
                "canonical_split_identity_hash": CANONICAL_SPLIT_IDENTITY,
                "declared_protocol_hash": DECLARED_PROTOCOL_HASH,
                "canonical_protocol_hash": CANONICAL_PROTOCOL_HASH,
                "identity_corrections": [
                    "canonical carrier-prefixed split identity",
                    "bundle protocol recomputed from canonical split identity",
                ],
                "artifact_materialization": (
                    "role-specific outputs and trace manifest derived from the exact "
                    "source trace without state-machine replay or text normalization"
                ),
                "model_contacts": 0,
                "embedding_contacts": 0,
                "scorer_contacts": 0,
                "gold_opened": False,
                "response_bytes_programmatically_materialized": True,
                "response_meanings_interpreted_by_investigator": False,
            },
        }
    )
    return manifest


def recover(data_root: Path) -> dict[str, object]:
    source_seal = validate_source_bytes(data_root)
    _roster, sample_ids = _load_roster()
    mission = _mission(data_root)
    target = mission / RECOVERY_DIRNAME
    if target.exists():
        raise RecoveryError(f"zero-contact recovery target already exists: {target}")
    target.mkdir(parents=False, exist_ok=False)
    source_seal_path = target / "source-seal.json"
    _exclusive_json(source_seal_path, source_seal)

    source_authority_path = mission / "authority-binding.json"
    source_failure_path = mission / "failure-receipt.json"
    authority = _read_object(source_authority_path, "source authority")
    template = _read_object(
        mission / "direct_m0" / f"{RUN_ID}.run-manifest.json",
        "source direct manifest",
    )
    descriptors: list[dict[str, object]] = []
    for role in ROLE_ORDER:
        role_dir = target / role
        role_dir.mkdir(parents=False, exist_ok=False)
        source_trace = _source_trace(mission, role)
        copied_trace = role_dir / f"{RUN_ID}.trace.jsonl"
        shutil.copyfile(source_trace, copied_trace)
        _require_hash(
            copied_trace, str(ROLE_SPECS[role]["trace_sha256"]), f"copied {role} trace"
        )

        documents = _trace_documents(copied_trace, role)
        rows, cost, record_hashes, channel_counts = _derive_bundle_material(
            documents, role=role, expected_sample_ids=sample_ids
        )
        outputs = role_dir / f"{RUN_ID}.outputs.jsonl"
        _exclusive_jsonl(outputs, rows)
        if _sha256(outputs) != EXPECTED_OUTPUT_HASHES[role]:
            raise RecoveryError(f"{role} recovered outputs hash drift")
        trace_manifest = role_dir / f"{RUN_ID}.trace-manifest.json"
        _exclusive_json(trace_manifest, {"run_id": RUN_ID, "records": record_hashes})
        if _sha256(trace_manifest) != EXPECTED_TRACE_MANIFEST_HASHES[role]:
            raise RecoveryError(f"{role} recovered trace manifest hash drift")

        window = str(ROLE_SPECS[role]["session_window"])
        session = mission / "services" / window / "session-receipt.json"
        attempt = _attempt_path(data_root, str(ROLE_SPECS[role]["attempt_id"]))
        manifest_document = _build_successor_manifest(
            template=template,
            authority=authority,
            role=role,
            sample_ids=sample_ids,
            outputs=outputs,
            raw_trace=copied_trace,
            trace_manifest=trace_manifest,
            session_receipt=session,
            cost=cost,
            source_trace=source_trace,
            source_failure=source_failure_path,
            source_authority=source_authority_path,
            source_attempt=attempt,
        )
        manifest = role_dir / f"{RUN_ID}.run-manifest.json"
        _exclusive_json(manifest, manifest_document)
        verified = verify_bundle(manifest)
        if (
            len(verified.outputs_rows) != SAMPLE_COUNT
            or verified.attempt_state != "ABORTED"
        ):
            raise RecoveryError(
                f"{role} successor is not a verified terminal 104-row source"
            )
        audit = role_dir / "recovery-audit.json"
        _exclusive_json(
            audit,
            {
                "schema": "saea-a2t-semantic-agentloop-104-role-recovery-audit-v1",
                "role": role,
                "source_trace_sha256": ROLE_SPECS[role]["trace_sha256"],
                "copied_trace_sha256": _sha256(copied_trace),
                "trace_records": len(documents),
                "channel_counts": dict(sorted(channel_counts.items())),
                "complete_rows": len(verified.outputs_rows),
                "attempt_state": verified.attempt_state,
                "manifest_sha256": _sha256(manifest),
                "outputs_sha256": _sha256(outputs),
                "trace_manifest_sha256": _sha256(trace_manifest),
                "model_contacts": 0,
                "embedding_contacts": 0,
                "scorer_contacts": 0,
                "gold_opened": False,
            },
        )
        descriptors.append(
            {
                "role": role,
                "manifest": str(manifest.resolve()),
                "manifest_sha256": _sha256(manifest),
                "outputs_sha256": _sha256(outputs),
                "raw_trace_sha256": _sha256(copied_trace),
                "trace_manifest_sha256": _sha256(trace_manifest),
                "complete_rows": SAMPLE_COUNT,
                "attempt_state": verified.attempt_state,
            }
        )

    # Re-measure every immutable source after successor construction.
    final_source_seal = validate_source_bytes(data_root)
    if final_source_seal != source_seal:
        raise RecoveryError("immutable source seal changed during recovery")

    receipt = {
        "schema": "saea-a2t-semantic-agentloop-104-zero-contact-recovery-receipt-v1",
        "status": "SEALED",
        "run_id": RUN_ID,
        "mission_id": MISSION_ID,
        "source_seal": _artifact(source_seal_path),
        "source_generation_contacts": 624,
        "source_embedding_logical_contacts": 208,
        "source_embedding_physical_requests": 7,
        "recovery_model_contacts": 0,
        "recovery_embedding_contacts": 0,
        "recovery_scorer_contacts": 0,
        "gold_opened": False,
        "source_attempt_states": ["ABORTED"],
        "declared_split_identity_hash": DECLARED_SPLIT_IDENTITY,
        "canonical_split_identity_hash": CANONICAL_SPLIT_IDENTITY,
        "declared_protocol_hash": DECLARED_PROTOCOL_HASH,
        "canonical_protocol_hash": CANONICAL_PROTOCOL_HASH,
        "manifests": descriptors,
        "scoring_authorized_only_after_this_receipt": True,
        "sealed_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path = target / "recovery-receipt.json"
    _exclusive_json(receipt_path, receipt)
    return {**receipt, "recovery_receipt": _artifact(receipt_path)}


def prepare_score_jobs(data_root: Path) -> dict[str, object]:
    """Write scorer descriptors only after the recovery receipt and bundles verify."""

    target = _mission(data_root) / RECOVERY_DIRNAME
    receipt_path = target / "recovery-receipt.json"
    receipt = _read_object(receipt_path, "zero-contact recovery receipt")
    if receipt.get("status") != "SEALED" or receipt.get("gold_opened") is not False:
        raise RecoveryError("zero-contact recovery receipt is not sealed")
    descriptors = receipt.get("manifests")
    if not isinstance(descriptors, list) or len(descriptors) != len(ROLE_ORDER):
        raise RecoveryError("zero-contact recovery receipt lacks six manifests")
    by_role = {
        item.get("role"): item for item in descriptors if isinstance(item, Mapping)
    }
    if set(by_role) != set(ROLE_ORDER):
        raise RecoveryError("zero-contact recovery manifest role set drift")
    for role in ROLE_ORDER:
        descriptor = by_role[role]
        manifest = Path(str(descriptor.get("manifest", "")))
        if _sha256(manifest) != descriptor.get("manifest_sha256"):
            raise RecoveryError(f"{role} recovery manifest hash drift")
        verified = verify_bundle(manifest)
        if (
            len(verified.outputs_rows) != SAMPLE_COUNT
            or verified.attempt_state != "ABORTED"
        ):
            raise RecoveryError(f"{role} recovery manifest no longer verifies")
    score_jobs = target / "score-jobs.jsonl"
    if score_jobs.exists():
        raise RecoveryError(f"score job file already exists: {score_jobs}")
    scored_roles = tuple(
        role for role in ROLE_ORDER if role != "obs_semantic_retrieval"
    )
    _exclusive_jsonl(
        score_jobs,
        tuple(
            {
                "job_id": role.replace("_", "-"),
                "manifest": by_role[role]["manifest"],
            }
            for role in scored_roles
        ),
    )
    return {
        "status": "OFFICIAL_SCORE_JOBS_READY",
        "job_count": len(scored_roles),
        "jobs": _artifact(score_jobs),
        "workers": 4,
        "whole_manifest_only": True,
        "model_contacts": 0,
        "scorer_contacts": 0,
        "gold_opened": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")),
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--preflight-only", action="store_true")
    action.add_argument("--recover", action="store_true")
    action.add_argument("--prepare-score-jobs", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    data_root = Path(args.data_root)
    if not str(data_root) or not data_root.is_dir():
        raise RecoveryError(
            "SPEECHRL_DATA_DIR or --data-root must name the existing data root"
        )
    target = _mission(data_root) / RECOVERY_DIRNAME
    if args.prepare_score_jobs:
        result = prepare_score_jobs(data_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    source_seal = validate_source_bytes(data_root)
    _load_roster()
    if target.exists():
        raise RecoveryError(f"zero-contact recovery target already exists: {target}")
    if args.preflight_only:
        print(
            json.dumps(
                {
                    "status": "ZERO_CONTACT_RECOVERY_READY",
                    "run_id": RUN_ID,
                    "source_trace_count": len(source_seal["source_traces"]),  # type: ignore[arg-type]
                    "source_generation_contacts": 624,
                    "source_embedding_logical_contacts": 208,
                    "target_absent": True,
                    "model_contacts": 0,
                    "scorer_contacts": 0,
                    "gold_opened": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    result = recover(data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
