"""Build a protected identity-only Audio2Tool factorial roster."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sys
from typing import Mapping
import wave


REPO = Path(__file__).resolve().parents[4]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speech_aware_evidence_acquisition.analysis.a2t_factorial_roster import (  # noqa: E402
    IdentityCandidate,
    build_factorial_roster_receipt,
)
from speech_aware_evidence_acquisition.analysis.a2t_fresh_agentloop_roster import (  # noqa: E402
    TIERS,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    audio2tool_receipts,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    load_lock,
    lock_entry,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.scoring.normalize import (  # noqa: E402
    normalize_text_v1,
)


CHECK_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = CHECK_DIR / "flight-roster-receipt.json"
PARTITION_PROPOSAL = REPO / "docs/receipts/knowledge/a2t-partition-proposal.json"
PARTITION_PROPOSAL_SHA256 = (
    "3bbf77a328c2983fb6299bcfe34a975624fee330a9325614dc1f84a7338678a1"
)
PARTITION_IDENTITY_SHA256 = (
    "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
)
PRIOR_ROSTERS = (
    (
        REPO
        / "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-03-a2t-fresh-agentloop-roster/flight-roster-receipt.json",
        "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e",
    ),
    (
        REPO
        / "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-03-a2t-select-fill-fresh-roster-v1/flight-roster-receipt.json",
        "dea74114430ed5e45e29d908dc2ecebf41788edfa2704435a2966f260de5bc4f",
    ),
)
NAMESPACE = "speech-aware-evidence-acquisition-a2t-select-fill-factorial-128-v1"
TARGET_PER_TIER = 16
MANIFEST_DURATION_ROUNDING_SECONDS = 0.0005


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot load JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON artifact {path} must contain one object")
    return value


def _load_manifest(path: Path) -> tuple[Mapping[str, object], ...]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot load tier manifest {path}: {error}") from error
    if not isinstance(value, list) or not value:
        raise RuntimeError(f"tier manifest {path} must contain a nonempty list")
    rows: list[Mapping[str, object]] = []
    seen: set[int] = set()
    for entry in value:
        if not isinstance(entry, Mapping):
            raise RuntimeError(f"tier manifest {path} contains a malformed row")
        item_id = entry.get("id")
        if (
            isinstance(item_id, bool)
            or not isinstance(item_id, int)
            or item_id < 0
            or item_id in seen
        ):
            raise RuntimeError(f"tier manifest {path} has a malformed item identity")
        seen.add(item_id)
        rows.append(entry)
    return tuple(rows)


def _entry_text(tier: str, entry: Mapping[str, object]) -> str:
    value = entry.get("user_request") if tier == "tier7_multiturn" else entry.get("query")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{tier} row lacks invocation text")
    return value.strip()


def _entry_media(
    tier: str,
    entry: Mapping[str, object],
) -> tuple[str, float]:
    path = entry.get("path")
    duration = entry.get("duration")
    if not isinstance(path, str) or not path:
        history = entry.get("chat_history")
        if not isinstance(history, list) or not history:
            raise RuntimeError(f"{tier} row lacks request media")
        final = history[-1]
        if not isinstance(final, Mapping) or final.get("role") != "user":
            raise RuntimeError(f"{tier} final turn is not a user request")
        path = final.get("path")
        duration = final.get("duration")
    if not isinstance(path, str) or not path:
        raise RuntimeError(f"{tier} row media path is malformed")
    candidate = PurePosixPath(path)
    if (
        candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.suffix.casefold() != ".wav"
    ):
        raise RuntimeError(f"{tier} row media path is not confined")
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or duration <= 0
    ):
        raise RuntimeError(f"{tier} row media duration is malformed")
    return path, float(duration)


def _project_manifest_entry(
    tier: str,
    entry: Mapping[str, object],
) -> dict[str, object]:
    """Project one mixed-source row without returning task text or annotations."""

    item_id = entry.get("id")
    query_idx = entry.get("query_idx")
    if (
        isinstance(item_id, bool)
        or not isinstance(item_id, int)
        or item_id < 0
        or isinstance(query_idx, bool)
        or not isinstance(query_idx, int)
        or query_idx < 0
    ):
        raise RuntimeError(f"{tier} row identity is malformed")
    path, duration = _entry_media(tier, entry)
    normalized = normalize_text_v1(_entry_text(tier, entry))
    if not normalized:
        raise RuntimeError(f"{tier} row has an empty normalized invocation")
    return {
        "id": item_id,
        "query_idx": query_idx,
        "normalized_token_class_sha256": _sha256_text(normalized),
        "audio_relpath_in_public": path,
        "audio_seconds": duration,
    }


def _wav_metadata(path: Path, expected_seconds: float) -> tuple[str, float]:
    if not path.is_file():
        raise RuntimeError(f"candidate WAV is missing: {path}")
    try:
        with wave.open(str(path), "rb") as handle:
            frame_rate = handle.getframerate()
            frame_count = handle.getnframes()
    except (OSError, EOFError, wave.Error) as error:
        raise RuntimeError(f"cannot inspect candidate WAV {path}: {error}") from error
    if frame_rate <= 0 or frame_count <= 0:
        raise RuntimeError(f"candidate WAV has invalid header metadata: {path}")
    header_seconds = frame_count / frame_rate
    if abs(header_seconds - expected_seconds) > MANIFEST_DURATION_ROUNDING_SECONDS:
        raise RuntimeError(f"candidate WAV duration disagrees with manifest: {path}")
    return _sha256_file(path), header_seconds


def _receipt_exclusions() -> tuple[set[str], set[int], set[str]]:
    exposed_samples: set[str] = set()
    excluded_queries: set[int] = set()
    excluded_classes: set[str] = set()
    for payload in audio2tool_receipts(REPO).values():
        for item in payload["items"]:
            exposed_samples.add(f"{item['tier']}:{int(item['id']):06d}")
            query_idx = item.get("query_idx")
            class_hash = item.get("normalized_token_class_sha256")
            if isinstance(query_idx, int) and not isinstance(query_idx, bool):
                excluded_queries.add(query_idx)
            if isinstance(class_hash, str) and len(class_hash) == 64:
                excluded_classes.add(class_hash)
    for path, expected_hash in PRIOR_ROSTERS:
        if _sha256_file(path) != expected_hash:
            raise RuntimeError(f"prior roster bytes drift: {path}")
        payload = _load_json_object(path)
        items = payload.get("items")
        if not isinstance(items, list) or len(items) != 104:
            raise RuntimeError(f"prior roster shape drift: {path}")
        for item in items:
            if not isinstance(item, Mapping):
                raise RuntimeError(f"prior roster item is malformed: {path}")
            sample_id = item.get("sample_id")
            query_idx = item.get("query_idx")
            class_hash = item.get("normalized_token_class_sha256")
            if not isinstance(sample_id, str) or not sample_id:
                raise RuntimeError(f"prior roster sample identity is malformed: {path}")
            exposed_samples.add(sample_id)
            if isinstance(query_idx, int) and not isinstance(query_idx, bool):
                excluded_queries.add(query_idx)
            if isinstance(class_hash, str) and len(class_hash) == 64:
                excluded_classes.add(class_hash)
    return exposed_samples, excluded_queries, excluded_classes


def build(*, data_root: Path) -> dict[str, object]:
    if _sha256_file(PARTITION_PROPOSAL) != PARTITION_PROPOSAL_SHA256:
        raise RuntimeError("partition proposal bytes drift")
    proposal = _load_json_object(PARTITION_PROPOSAL)
    if proposal.get("proposed_eval_split_identity_hash") != PARTITION_IDENTITY_SHA256:
        raise RuntimeError("partition proposal identity drift")
    proposed = proposal.get("proposed_eval_items")
    eval_blocks = proposal.get("eval_blocks")
    reserved_blocks = proposal.get("reserved_exposed_blocks")
    if (
        not isinstance(proposed, list)
        or len(proposed) != 400
        or not isinstance(eval_blocks, list)
        or len(eval_blocks) != 400
        or not isinstance(reserved_blocks, list)
    ):
        raise RuntimeError("partition proposal shape drift")
    proposal_sample_ids = sorted(
        f"{item.get('tier')}:{int(item.get('id', -1)):06d}"
        for item in proposed
        if isinstance(item, Mapping)
    )
    if (
        len(proposal_sample_ids) != 400
        or _sha256_text("\n".join(proposal_sample_ids)) != PARTITION_IDENTITY_SHA256
    ):
        raise RuntimeError("partition proposal item identity drift")

    lock = load_lock(umbrella_lock_path(REPO))
    carrier = asset_dir(lock, "audio2tool", data_root)
    local_subdir = str(lock_entry(lock, "audio2tool")["local_subdir"]).rstrip("/")
    public = carrier / "public"
    manifests = {
        tier: _load_manifest(public / f"{tier}_data" / f"{tier}.json")
        for tier in TIERS
    }
    by_tier_id = {
        tier: {int(entry["id"]): entry for entry in rows}
        for tier, rows in manifests.items()
    }
    eval_block_set = {int(value) for value in eval_blocks}
    reserved_block_set = {int(value) for value in reserved_blocks}
    construction_queries: set[int] = set()
    construction_classes: set[str] = set()
    for tier, rows in manifests.items():
        for entry in rows:
            query_idx = entry.get("query_idx")
            if isinstance(query_idx, bool) or not isinstance(query_idx, int):
                raise RuntimeError(f"{tier} row query identity is malformed")
            if query_idx in eval_block_set or query_idx in reserved_block_set:
                continue
            construction_queries.add(query_idx)
            construction_classes.add(
                _sha256_text(normalize_text_v1(_entry_text(tier, entry)))
            )

    candidates: list[IdentityCandidate] = []
    for item in proposed:
        if not isinstance(item, Mapping):
            raise RuntimeError("partition proposal item is malformed")
        tier = item.get("tier")
        item_id = item.get("id")
        key = item.get("key")
        if (
            tier not in TIERS
            or isinstance(item_id, bool)
            or not isinstance(item_id, int)
            or key != f"audio2tool:{tier}:{item_id:06d}"
        ):
            raise RuntimeError("partition proposal item identity is malformed")
        entry = by_tier_id[str(tier)].get(item_id)
        if entry is None:
            raise RuntimeError("partition proposal item is absent from its manifest")
        projected = _project_manifest_entry(str(tier), entry)
        query_idx = int(projected["query_idx"])
        if query_idx not in eval_block_set:
            raise RuntimeError("partition proposal item is outside eval blocks")
        audio_relpath = str(projected["audio_relpath_in_public"])
        wav = (public / PurePosixPath(audio_relpath)).resolve()
        if not wav.is_relative_to(public.resolve()):
            raise RuntimeError("candidate WAV escapes the public directory")
        audio_hash, header_seconds = _wav_metadata(
            wav,
            float(projected["audio_seconds"]),
        )
        candidates.append(
            IdentityCandidate(
                sample_id=f"{tier}:{item_id:06d}",
                tier=str(tier),
                item_id=item_id,
                query_idx=query_idx,
                normalized_token_class_sha256=str(
                    projected["normalized_token_class_sha256"]
                ),
                media_relpath=(
                    f"{local_subdir}/public/{audio_relpath}"
                ),
                audio_sha256=audio_hash,
                audio_seconds=header_seconds,
            )
        )

    exposed_samples, prior_queries, prior_classes = _receipt_exclusions()
    excluded_queries = prior_queries | construction_queries
    excluded_classes = prior_classes | construction_classes
    eligible = tuple(
        row
        for row in candidates
        if row.sample_id not in exposed_samples
        and row.query_idx not in excluded_queries
        and row.normalized_token_class_sha256 not in excluded_classes
    )
    eligible_keys = sorted(f"audio2tool:{row.sample_id}" for row in eligible)
    receipt = build_factorial_roster_receipt(
        tuple(candidates),
        source_path=PARTITION_PROPOSAL.relative_to(REPO).as_posix(),
        source_sha256=PARTITION_PROPOSAL_SHA256,
        source_split_identity_sha256=PARTITION_IDENTITY_SHA256,
        excluded_sample_ids=exposed_samples,
        excluded_query_indices=excluded_queries,
        excluded_normalized_class_sha256s=excluded_classes,
        target_per_tier=TARGET_PER_TIER,
        namespace=NAMESPACE,
    )
    receipt["protected_projection"] = {
        "source_candidate_count": len(candidates),
        "eligible_before_internal_equivalence_deduplication": len(eligible),
        "eligible_by_tier": dict(Counter(row.tier for row in eligible)),
        "eligible_identity_sha256": _sha256_text("\n".join(eligible_keys)),
        "construction_query_count": len(construction_queries),
        "construction_normalized_class_count": len(construction_classes),
        "loaded_exposure_sample_count": len(exposed_samples),
        "projected_field_set": [
            "id",
            "query_idx",
            "normalized_token_class_sha256",
            "audio_relpath_in_public",
            "audio_seconds",
        ],
        "task_text_emitted": False,
        "annotation_fields_projected": 0,
    }
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    receipt = build(data_root=args.data_root.resolve())
    if args.check_only:
        print(
            json.dumps(
                {
                    "count": receipt["count"],
                    "split_identity_hash": receipt["split_identity_hash"],
                    "tier_counts": receipt["tier_counts"],
                    "audio_seconds_total": receipt["audio_seconds_total"],
                    "protected_projection": receipt["protected_projection"],
                    "contacts": receipt["contacts"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing roster receipt: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": _sha256_file(output),
                "count": receipt["count"],
                "split_identity_hash": receipt["split_identity_hash"],
                "contacts": receipt["contacts"],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
