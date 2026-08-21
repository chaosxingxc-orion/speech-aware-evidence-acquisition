"""Speech-native GPU-profile flight through the existing ``saea-driver``.

This is a driver module, not a standalone experiment script. It reuses the
repository's receipt-pinned session, frozen gate, attempt accounting,
speech-feature client, bounded matcher dispatcher, resource sampler, and
trace machinery. Profile flights are engineering-only: response text is
hashed in process and never copied into the profile receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

from ...contracts import ExecutionPlan
from ...data.lock import asset_dir, data_root, load_lock, umbrella_lock_path
from ...e0.artifacts import REPO_ROOT
from ...rails import FrozenCoreClient, build_payload_binding
from ...rails.probes.pslu_flight import (
    KeyCardV1,
    SpeechNativeMatchTask,
    load_speech_native_engineering_gate,
    run_speech_native_match_tasks,
)
from ..attempts import AttemptStore
from ..base import TRANSPORTS
from ..config import (
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_lock_key,
    model_materialization_root,
    protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from ..resources import resolve_resource_sampler
from ..session import load_runtime_receipt, start_session, stop_session
from .run import load_split
from .smoke import _server_args, _server_env, _write_inference_process_audit

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ORDER_BUILDERS = {
    "canonical": lambda cards: cards,
    "reverse": lambda cards: tuple(reversed(cards)),
    "rotate-1": lambda cards: cards[1:] + cards[:1],
    "rotate-7": lambda cards: cards[7:] + cards[:7],
}
_OOM_MARKERS = (
    "out of memory",
    "cuda error out of memory",
    "failed to allocate",
    "cuda_malloc failed",
)
_HOST_SPILL_MARKERS = (
    "offloaded to cpu",
    "offloading layer to cpu",
    "host buffer fallback",
)
_RUNAWAY_MARKERS = ("truncated = 1", "context shift", "slot context shift")


class SpeechNativeProfileError(RuntimeError):
    """A profile input, flight, or receipt failed closed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(document: object) -> str:
    raw = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_string(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise SpeechNativeProfileError(f"profile config {key} must be a non-empty string")
    return value


def _require_positive_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SpeechNativeProfileError(f"profile config {key} must be a positive integer")
    return value


def _load_binding_document(path: Path, expected_sha256: str) -> dict[str, object]:
    if _SHA256.fullmatch(expected_sha256) is None:
        raise SpeechNativeProfileError("speech-native binding SHA-256 is malformed")
    if _sha256_file(path) != expected_sha256:
        raise SpeechNativeProfileError("speech-native binding file SHA-256 mismatch")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(f"cannot read speech-native binding: {error}") from error
    if not isinstance(document, dict):
        raise SpeechNativeProfileError("speech-native binding must be a JSON object")
    claimed = document.get("binding_sha256")
    unsigned = dict(document)
    unsigned.pop("binding_sha256", None)
    if claimed != _canonical_sha256(unsigned):
        raise SpeechNativeProfileError("speech-native binding self-hash mismatch")
    return document


def _load_key_cards(path: Path, expected_sha256: str) -> tuple[KeyCardV1, ...]:
    document = _load_binding_document(path, expected_sha256)
    raw_cards = document.get("key_cards")
    if not isinstance(raw_cards, list) or len(raw_cards) != 18:
        raise SpeechNativeProfileError("profile requires exactly 18 frozen key cards")
    cards: list[KeyCardV1] = []
    for raw in raw_cards:
        if not isinstance(raw, dict) or set(raw) != {
            "key_id",
            "definition",
            "positive_examples",
            "contrastive_boundary",
            "value_label",
        }:
            raise SpeechNativeProfileError("speech-native key card has unexpected fields")
        examples = raw["positive_examples"]
        if not isinstance(examples, list) or not all(
            isinstance(item, str) for item in examples
        ):
            raise SpeechNativeProfileError("speech-native key examples must be strings")
        cards.append(
            KeyCardV1(
                key_id=str(raw["key_id"]),
                definition=str(raw["definition"]),
                positive_examples=tuple(examples),
                contrastive_boundary=(
                    str(raw["contrastive_boundary"])
                    if raw["contrastive_boundary"] is not None
                    else None
                ),
                value_label=str(raw["value_label"]),
            ).validate()
        )
    return tuple(cards)


def read_speech_native_predictions(
    *,
    attempt_dirs: Sequence[Path],
    binding_path: Path,
    binding_sha256: str,
    split_name: str,
) -> dict[str, object]:
    """Score prediction-only flight artifacts after every server has stopped.

    Gold labels enter only this model-free reader. Flight receipts and
    decision rows are hash-verified before scoring; no runtime prompt or
    trace is modified.
    """

    if not attempt_dirs:
        raise SpeechNativeProfileError("speech-native read requires at least one attempt")
    binding = _load_binding_document(binding_path, binding_sha256)
    splits = binding.get("splits")
    split = splits.get(split_name) if isinstance(splits, Mapping) else None
    raw_items = split.get("items") if isinstance(split, Mapping) else None
    if not isinstance(raw_items, list) or not raw_items:
        raise SpeechNativeProfileError(f"binding lacks split {split_name!r}")
    gold: dict[str, str] = {}
    for item in raw_items:
        if not isinstance(item, Mapping):
            raise SpeechNativeProfileError("binding split item must be an object")
        sample_id = item.get("sample_id")
        value_label = item.get("value_label")
        if (
            not isinstance(sample_id, str)
            or not isinstance(value_label, str)
            or sample_id in gold
        ):
            raise SpeechNativeProfileError("binding split labels are malformed or duplicate")
        gold[sample_id] = value_label

    cards = _load_key_cards(binding_path, binding_sha256)
    label_by_key = {card.key_id: card.value_label for card in cards}
    key_by_label = {card.value_label: card.key_id for card in cards}
    aggregates: list[dict[str, object]] = []
    correctness_by_cell: dict[str, dict[str, bool]] = {}
    source_receipts: list[dict[str, str]] = []
    for attempt_dir_value in attempt_dirs:
        attempt_dir = Path(attempt_dir_value)
        receipt_path = attempt_dir / "flight-receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SpeechNativeProfileError(f"cannot read flight receipt: {error}") from error
        if (
            not isinstance(receipt, dict)
            or receipt.get("status") != "COMPLETED"
            or receipt.get("request_failures") != []
            or receipt.get("split_identity_hash") is None
        ):
            raise SpeechNativeProfileError("flight receipt is not a completed readable result")
        profile = receipt.get("profile")
        decisions_ref = receipt.get("decisions")
        if not isinstance(profile, Mapping) or not isinstance(decisions_ref, Mapping):
            raise SpeechNativeProfileError("flight receipt lacks prediction metadata")
        key_representation_id = profile.get("key_representation_id")
        matcher_policy_id = profile.get("matcher_policy_id")
        if not isinstance(key_representation_id, str) or not isinstance(
            matcher_policy_id, str
        ):
            raise SpeechNativeProfileError("flight cell identity is malformed")
        cell_id = f"{key_representation_id}-{matcher_policy_id}"
        if matcher_policy_id == "M3":
            top_k = profile.get("top_k")
            if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
                raise SpeechNativeProfileError("M3 flight receipt lacks a valid top_k")
            cell_id = f"{cell_id}-k{top_k}"
            prompt_policy_id = profile.get(
                "matcher_prompt_policy_id", "speech-native-json-copy-v2"
            )
            prompt_suffix = {
                "speech-native-json-copy-v2": "",
                "speech-native-json-copy-v3": "-v3",
            }.get(prompt_policy_id)
            if prompt_suffix is None:
                raise SpeechNativeProfileError(
                    "M3 flight receipt has an unknown matcher prompt policy"
                )
            cell_id += prompt_suffix
            verifier_policy_id = profile.get(
                "matcher_verifier_policy_id", "speech-native-compatibility-v1"
            )
            verifier_suffix = {
                "speech-native-compatibility-v1": "",
                "speech-native-contrastive-verifier-v2": "-verify-contrastive-v2",
            }.get(verifier_policy_id)
            if verifier_suffix is None:
                raise SpeechNativeProfileError(
                    "M3 flight receipt has an unknown verifier policy"
                )
            cell_id += verifier_suffix
        order_ids = profile.get("key_order_ids", ["canonical"])
        if (
            not isinstance(order_ids, list)
            or len(order_ids) != 1
            or not isinstance(order_ids[0], str)
        ):
            raise SpeechNativeProfileError(
                "prediction flight must carry exactly one key order"
            )
        if order_ids[0] != "canonical":
            cell_id += f"-order-{order_ids[0]}"
        mechanism_control_id = profile.get("mechanism_control_id", "matched")
        control_suffix = {
            "matched": "",
            "speech-swap-v1": "-control-speech-swap-v1",
            "key-text-shuffle-v1": "-control-key-text-shuffle-v1",
        }.get(mechanism_control_id)
        if control_suffix is None:
            raise SpeechNativeProfileError(
                "flight receipt has an unknown mechanism control"
            )
        cell_id += control_suffix
        if cell_id in correctness_by_cell:
            raise SpeechNativeProfileError(f"duplicate flight cell {cell_id!r}")
        decisions_name = decisions_ref.get("path")
        decisions_sha256 = decisions_ref.get("sha256")
        if (
            not isinstance(decisions_name, str)
            or Path(decisions_name).name != decisions_name
            or not isinstance(decisions_sha256, str)
            or _SHA256.fullmatch(decisions_sha256) is None
        ):
            raise SpeechNativeProfileError("flight decisions reference is malformed")
        decisions_path = attempt_dir / decisions_name
        if _sha256_file(decisions_path) != decisions_sha256:
            raise SpeechNativeProfileError("flight decisions SHA-256 mismatch")
        rows: list[Mapping[str, object]] = []
        try:
            with decisions_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    if not isinstance(row, Mapping):
                        raise SpeechNativeProfileError("decision row must be an object")
                    rows.append(row)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SpeechNativeProfileError(f"cannot read decisions: {error}") from error
        if len(rows) != decisions_ref.get("count") or len(rows) != len(gold):
            raise SpeechNativeProfileError("decision count does not match receipt or split")
        seen: set[str] = set()
        correctness: dict[str, bool] = {}
        parse_failures = 0
        top_k_reachable_count = 0
        for row in rows:
            if row.get("schema") != "saea-speech-native-decision-v1":
                raise SpeechNativeProfileError("decision schema mismatch")
            sample_id = row.get("sample_id")
            if not isinstance(sample_id, str) or sample_id not in gold or sample_id in seen:
                raise SpeechNativeProfileError("decision sample set is malformed")
            seen.add(sample_id)
            key_id = row.get("key_id")
            predicted = row.get("predicted_value_label")
            parse_failure = row.get("parse_failure")
            if not isinstance(parse_failure, bool):
                raise SpeechNativeProfileError("decision parse_failure must be boolean")
            if key_id is None:
                if predicted is not None or not parse_failure:
                    raise SpeechNativeProfileError("empty decision mapping is inconsistent")
            elif (
                not isinstance(key_id, str)
                or key_id not in label_by_key
                or predicted != label_by_key[key_id]
                or parse_failure
            ):
                raise SpeechNativeProfileError("decision key-to-label mapping is inconsistent")
            parse_failures += int(parse_failure)
            correctness[sample_id] = predicted == gold[sample_id]
            raw_top_key_ids = row.get("top_key_ids", [])
            if (
                not isinstance(raw_top_key_ids, list)
                or not all(
                    isinstance(top_key_id, str) and top_key_id in label_by_key
                    for top_key_id in raw_top_key_ids
                )
                or len(set(raw_top_key_ids)) != len(raw_top_key_ids)
            ):
                raise SpeechNativeProfileError("decision top_key_ids are malformed")
            if matcher_policy_id == "M3":
                assert isinstance(top_k, int)
                if len(raw_top_key_ids) > top_k:
                    raise SpeechNativeProfileError(
                        "decision top_key_ids exceed the registered top_k"
                    )
                top_k_reachable_count += int(
                    key_by_label[gold[sample_id]] in raw_top_key_ids
                )
        if seen != set(gold):
            raise SpeechNativeProfileError("decision sample set does not equal the frozen split")
        correct = sum(correctness.values())
        aggregates.append(
            {
                "cell_id": cell_id,
                "correct": correct,
                "count": len(gold),
                "accuracy": correct / len(gold),
                "parse_failure_count": parse_failures,
                "top_k_reachable_count": (
                    top_k_reachable_count if matcher_policy_id == "M3" else None
                ),
                "top_k_reachability": (
                    top_k_reachable_count / len(gold)
                    if matcher_policy_id == "M3"
                    else None
                ),
                "actual_contact_count": profile.get("actual_contact_count"),
                "aggregate_tokens_per_second": (
                    receipt.get("timing", {}).get("aggregate_tokens_per_second")
                    if isinstance(receipt.get("timing"), Mapping)
                    else None
                ),
            }
        )
        correctness_by_cell[cell_id] = correctness
        source_receipts.append(
            {
                "run_id": str(receipt.get("run_id")),
                "flight_receipt_sha256": _sha256_file(receipt_path),
                "decisions_sha256": decisions_sha256,
            }
        )

    baseline_id = str(aggregates[0]["cell_id"])
    baseline = correctness_by_cell[baseline_id]
    pairwise: list[dict[str, object]] = []
    for aggregate in aggregates:
        cell_id = str(aggregate["cell_id"])
        current = correctness_by_cell[cell_id]
        wrong_to_correct = sum(
            1 for sample_id in gold if not baseline[sample_id] and current[sample_id]
        )
        correct_to_wrong = sum(
            1 for sample_id in gold if baseline[sample_id] and not current[sample_id]
        )
        aggregate["wrong_to_correct_vs_baseline"] = wrong_to_correct
        aggregate["correct_to_wrong_vs_baseline"] = correct_to_wrong
        pairwise.append(
            {
                "baseline_cell_id": baseline_id,
                "cell_id": cell_id,
                "wrong_to_correct": wrong_to_correct,
                "correct_to_wrong": correct_to_wrong,
                "net_change": wrong_to_correct - correct_to_wrong,
            }
        )
    winner = min(
        aggregates,
        key=lambda item: (
            -int(item["correct"]),
            int(item["correct_to_wrong_vs_baseline"]),
            int(item["parse_failure_count"]),
            str(item["cell_id"]),
        ),
    )
    return {
        "schema": "saea-speech-native-read-v1",
        "study": "speech-aware-evidence-acquisition",
        "split_name": split_name,
        "binding_file_sha256": binding_sha256,
        "baseline_cell_id": baseline_id,
        "aggregates": aggregates,
        "pairwise": pairwise,
        "selected_cell_id": winner["cell_id"],
        "source_receipts": source_receipts,
    }


def _load_packet_index(
    receipt_path: Path,
    expected_sha256: str,
) -> dict[str, dict[str, str]]:
    if _SHA256.fullmatch(expected_sha256) is None:
        raise SpeechNativeProfileError("packet promotion receipt SHA-256 is malformed")
    if _sha256_file(receipt_path) != expected_sha256:
        raise SpeechNativeProfileError("packet promotion receipt SHA-256 mismatch")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(f"cannot read packet promotion receipt: {error}") from error
    if not isinstance(receipt, dict) or receipt.get("schema") != (
        "saea-speech-packet-promotion-receipt-v1"
    ):
        raise SpeechNativeProfileError("packet promotion receipt schema mismatch")
    packets = receipt.get("packets")
    if not isinstance(packets, list):
        raise SpeechNativeProfileError("packet promotion receipt lacks packets")
    by_packet_id: dict[str, dict[str, str]] = {}
    for packet in packets:
        if not isinstance(packet, dict):
            raise SpeechNativeProfileError("packet receipt entry must be an object")
        packet_id = packet.get("packet_id")
        packet_sha256 = packet.get("packet_sha256")
        if (
            not isinstance(packet_id, str)
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
            or packet_id in by_packet_id
        ):
            raise SpeechNativeProfileError("packet receipt contains malformed or duplicate ids")
        by_packet_id[packet_id] = {"packet_id": packet_id, "sha256": packet_sha256}
    return by_packet_id


def _load_packet_bindings(
    receipt_path: Path,
    expected_sha256: str,
    samples: Sequence[object],
) -> dict[str, dict[str, str]]:
    by_packet_id = _load_packet_index(receipt_path, expected_sha256)
    bindings: dict[str, dict[str, str]] = {}
    for sample in samples:
        descriptor = by_packet_id.get(sample.packet_id)
        if descriptor is None:
            raise SpeechNativeProfileError(
                f"packet promotion receipt does not materialize {sample.sample_id!r}"
            )
        bindings[sample.sample_id] = descriptor
    return bindings


def _packet_id_from_sample_id(sample_id: object) -> str:
    if not isinstance(sample_id, str):
        raise SpeechNativeProfileError("audio-key source sample id must be a string")
    parts = sample_id.split(":")
    if len(parts) != 4 or parts[0] != "slurp" or parts[1] != "train":
        raise SpeechNativeProfileError("audio-key source sample id is malformed")
    return "/".join(parts)


def _build_audio_key_bindings(
    binding: Mapping[str, object],
    packet_index: Mapping[str, Mapping[str, str]],
    key_cards: Sequence[KeyCardV1],
) -> dict[str, dict[str, str]]:
    raw_material = binding.get("key_material")
    if not isinstance(raw_material, list):
        raise SpeechNativeProfileError("speech-native binding lacks key material")
    source_by_key: dict[str, str] = {}
    for item in raw_material:
        if not isinstance(item, Mapping):
            raise SpeechNativeProfileError("speech-native key material must be objects")
        key_id = item.get("key_id")
        if not isinstance(key_id, str) or key_id in source_by_key:
            raise SpeechNativeProfileError("speech-native key material ids are malformed")
        source_by_key[key_id] = _packet_id_from_sample_id(
            item.get("audio_key_source_sample_id")
        )
    expected_keys = {card.key_id for card in key_cards}
    if set(source_by_key) != expected_keys:
        raise SpeechNativeProfileError("audio-key material does not match frozen key cards")
    bindings: dict[str, dict[str, str]] = {}
    for key_id in sorted(expected_keys):
        descriptor = packet_index.get(source_by_key[key_id])
        if (
            not isinstance(descriptor, Mapping)
            or set(descriptor) != {"packet_id", "sha256"}
        ):
            raise SpeechNativeProfileError(
                f"audio-key packet is not materialized for {key_id!r}"
            )
        bindings[key_id] = {
            "packet_id": str(descriptor["packet_id"]),
            "sha256": str(descriptor["sha256"]),
        }
    return bindings


def _shuffle_key_text(key_cards: tuple[KeyCardV1, ...]) -> tuple[KeyCardV1, ...]:
    donors = key_cards[1:] + key_cards[:1]
    return tuple(
        KeyCardV1(
            key_id=target.key_id,
            definition=donor.definition,
            positive_examples=donor.positive_examples,
            contrastive_boundary=donor.contrastive_boundary,
            value_label=target.value_label,
        ).validate()
        for target, donor in zip(key_cards, donors, strict=True)
    )


def build_profile_tasks(
    *,
    samples: Sequence[object],
    packet_bindings: Mapping[str, Mapping[str, str]],
    key_cards: tuple[KeyCardV1, ...],
    order_ids: Sequence[str],
    decoding_params: Mapping[str, object],
    key_representation_id: str,
    matcher_policy_id: str,
    top_k: int = 3,
    prompt_policy_id: str = "speech-native-json-copy-v2",
    verifier_policy_id: str = "speech-native-compatibility-v1",
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None = None,
    mechanism_control_id: str = "matched",
) -> tuple[SpeechNativeMatchTask, ...]:
    """Build the registered maximum-card prompt tasks without reading labels."""

    if mechanism_control_id not in {
        "matched",
        "speech-swap-v1",
        "key-text-shuffle-v1",
    }:
        raise SpeechNativeProfileError("unknown speech-native mechanism control")
    frozen_samples = tuple(samples)
    if mechanism_control_id == "speech-swap-v1" and len(frozen_samples) < 2:
        raise SpeechNativeProfileError("speech-swap control requires at least two samples")
    controlled_cards = key_cards
    if mechanism_control_id == "key-text-shuffle-v1":
        if key_representation_id not in {"K1", "K2", "K4"}:
            raise SpeechNativeProfileError(
                "key-text shuffle requires a text-bearing key representation"
            )
        controlled_cards = _shuffle_key_text(key_cards)
    source_samples = (
        frozen_samples[1:] + frozen_samples[:1]
        if mechanism_control_id == "speech-swap-v1"
        else frozen_samples
    )
    tasks: list[SpeechNativeMatchTask] = []
    for order_id in order_ids:
        builder = _ORDER_BUILDERS.get(order_id)
        if builder is None:
            raise SpeechNativeProfileError(f"unknown profile key order {order_id!r}")
        ordered_cards = builder(controlled_cards)
        for target_sample, source_sample in zip(
            frozen_samples, source_samples, strict=True
        ):
            descriptor = packet_bindings.get(source_sample.sample_id)
            if descriptor is None:
                raise SpeechNativeProfileError(
                    f"profile sample {source_sample.sample_id!r} lacks a packet binding"
                )
            tasks.append(
                SpeechNativeMatchTask(
                    task_id=f"{order_id}:{target_sample.sample_id}",
                    sample=source_sample,
                    scoring_sample_id=target_sample.sample_id,
                    mechanism_control_id=mechanism_control_id,
                    query_descriptor={**descriptor, "role": "query"},
                    key_cards=ordered_cards,
                    key_representation_id=key_representation_id,
                    matcher_policy_id=matcher_policy_id,
                    prompt_policy_id=prompt_policy_id,
                    verifier_policy_id=verifier_policy_id,
                    decoding_params=dict(decoding_params),
                    top_k=top_k,
                    audio_key_bindings=audio_key_bindings,
                )
            )
    return tuple(tasks)


def profile_timing_metrics(
    timings: Sequence[Mapping[str, object]],
    *,
    slot_count: int,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, float]:
    """Derive request-window throughput and mean slot occupancy."""

    if not timings:
        raise SpeechNativeProfileError("profile produced no request timings")
    starts: list[float] = []
    ends: list[float] = []
    latency_sum = 0.0
    for timing in timings:
        started_at = timing.get("started_at")
        latency = timing.get("latency_seconds")
        if (
            not isinstance(started_at, str)
            or isinstance(latency, bool)
            or not isinstance(latency, (int, float))
            or not math.isfinite(float(latency))
            or float(latency) < 0
        ):
            raise SpeechNativeProfileError("profile timing row is malformed")
        start = datetime.fromisoformat(started_at).timestamp()
        starts.append(start)
        ends.append(start + float(latency))
        latency_sum += float(latency)
    wall = max(ends) - min(starts)
    if wall <= 0:
        raise SpeechNativeProfileError("profile request window is not positive")
    return {
        "request_window_seconds": wall,
        "slot_occupancy_pct": min(100.0, 100.0 * latency_sum / (slot_count * wall)),
        "aggregate_tokens_per_second": (prompt_tokens + completion_tokens) / wall,
    }


def _trace_usage_summary(path: Path) -> dict[str, int]:
    request_count = 0
    response_count = 0
    cost_count = 0
    max_prompt_tokens = 0
    max_completion_tokens = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                channel = record.get("channel")
                if channel == "MODEL_REQUEST":
                    request_count += 1
                elif channel == "MODEL_RESPONSE":
                    response_count += 1
                    usage = record.get("payload", {}).get("usage", {})
                    if isinstance(usage, dict):
                        max_prompt_tokens = max(
                            max_prompt_tokens, int(usage.get("prompt_tokens", 0))
                        )
                        max_completion_tokens = max(
                            max_completion_tokens, int(usage.get("completion_tokens", 0))
                        )
                elif channel == "COST":
                    cost_count += 1
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise SpeechNativeProfileError(f"cannot verify profile trace usage: {error}") from error
    return {
        "model_request_count": request_count,
        "model_response_count": response_count,
        "cost_record_count": cost_count,
        "max_prompt_tokens": max_prompt_tokens,
        "max_completion_tokens": max_completion_tokens,
    }


def _scan_server_log(path: Path) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").casefold()
    except OSError as error:
        raise SpeechNativeProfileError(f"cannot read profile server log: {error}") from error

    def hits(markers: Sequence[str]) -> list[str]:
        return [marker for marker in markers if marker in text]

    return {
        "oom_marker_hits": hits(_OOM_MARKERS),
        "host_spill_marker_hits": hits(_HOST_SPILL_MARKERS),
        "runaway_marker_hits": hits(_RUNAWAY_MARKERS),
        "mmproj_free_chunk_count": text.count("decoded mmproj-free speech feature chunk"),
    }


def _profile_geometry(values: Mapping[str, object], slot_count: int) -> dict[str, int]:
    args = _server_args(values)
    try:
        np_index = args.index("-np")
        context_index = args.index("-c")
        configured_slots = int(args[np_index + 1])
        context_tokens = int(args[context_index + 1])
    except (ValueError, IndexError) as error:
        raise SpeechNativeProfileError(
            "profile server_args must carry integer -np and -c values"
        ) from error
    if configured_slots != slot_count or context_tokens <= 0:
        raise SpeechNativeProfileError(
            "profile_slot_count must equal server_args -np and context must be positive"
        )
    return {
        "context_tokens_total": context_tokens,
        "context_tokens_per_slot": context_tokens // configured_slots,
    }


def _write_exclusive_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    except FileExistsError as error:
        raise SpeechNativeProfileError(f"profile artifact already exists: {path}") from error


def _write_exclusive_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
    except FileExistsError as error:
        raise SpeechNativeProfileError(f"profile artifact already exists: {path}") from error


def _cli_speech_native_profile(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    root = data_root()
    lock = load_lock(umbrella_lock_path())
    composed = compose(repo_root, args.model, args.dataset, args.baseline, args.experiment)
    values = composed.values
    plan = ExecutionPlan(**json.loads(Path(args.plan).read_text(encoding="utf-8"))).validate()
    split_ids, split_hash, split_role = load_split(
        repo_root, _require_string(values, "split_name"), lock, root
    )
    expected_protocol = protocol_hash(composed.config_hash, str(values["arm"]), split_hash)
    if (
        plan.split_identity_hash != split_hash
        or plan.split_role != split_role
        or plan.protocol_hash != expected_protocol
        or plan.carrier_lock_key != values.get("carrier_lock_key")
    ):
        raise SpeechNativeProfileError("execution plan does not match the composed profile")
    run_dir = Path(args.run_dir).resolve()
    if run_dir.name != plan.attempt_id:
        raise SpeechNativeProfileError("profile run_dir basename must equal plan.attempt_id")
    run_dir.mkdir(parents=True, exist_ok=False)
    plan_copy_path = run_dir / f"{plan.run_id}.plan.json"
    _write_exclusive_json(plan_copy_path, asdict(plan))

    dataset_path = repo_root / "configs" / "dataset" / f"{args.dataset}.json"
    gate_view = load_speech_native_engineering_gate(
        dataset_path,
        data_root=root,
        expected_count=_require_positive_int(values, "count"),
        expected_split_name=_require_string(values, "split_name"),
        workers=_require_positive_int(values, "profile_validation_workers"),
    )
    if {sample.sample_id for sample in gate_view.samples} != split_ids:
        raise SpeechNativeProfileError("runtime view ids do not match the verified split")
    binding_relpath = _require_string(values, "speech_native_binding")
    binding_path = repo_root / binding_relpath
    if binding_path.resolve() == repo_root.resolve() or not binding_path.resolve().is_relative_to(
        repo_root.resolve()
    ):
        raise SpeechNativeProfileError("speech-native binding must stay under the repository")
    binding_sha256 = _require_string(values, "speech_native_binding_file_sha256")
    binding_document = _load_binding_document(binding_path, binding_sha256)
    key_cards = _load_key_cards(
        binding_path, binding_sha256
    )
    packet_receipt_path = Path(_require_string(values, "speech_packet_promotion_receipt"))
    packet_bindings = _load_packet_bindings(
        packet_receipt_path,
        _require_string(values, "speech_packet_promotion_receipt_sha256"),
        gate_view.samples,
    )
    key_representation_id = _require_string(values, "key_representation_id")
    audio_key_bindings = None
    if key_representation_id in {"K3", "K4"}:
        audio_key_bindings = _build_audio_key_bindings(
            binding_document,
            _load_packet_index(
                packet_receipt_path,
                _require_string(values, "speech_packet_promotion_receipt_sha256"),
            ),
            key_cards,
        )
    feature_root = Path(_require_string(values, "speech_feature_root"))
    if packet_receipt_path.parent.resolve() != feature_root.resolve():
        raise SpeechNativeProfileError("packet promotion receipt must live at speech_feature_root")
    raw_order_ids = values.get("profile_key_order_ids")
    if not isinstance(raw_order_ids, list) or not raw_order_ids or not all(
        isinstance(item, str) for item in raw_order_ids
    ):
        raise SpeechNativeProfileError("profile_key_order_ids must be a non-empty string list")
    slot_count = _require_positive_int(values, "profile_slot_count")
    geometry = _profile_geometry(values, slot_count)
    queue_multiplier = _require_positive_int(values, "profile_queue_depth_multiplier")
    result_mode = values.get("speech_native_result_mode", "hash-only")
    if result_mode not in {"hash-only", "predictions"}:
        raise SpeechNativeProfileError(
            "speech_native_result_mode must be 'hash-only' or 'predictions'"
        )
    contact_ceiling = values.get("speech_native_contact_ceiling_per_task", 1)
    if (
        isinstance(contact_ceiling, bool)
        or not isinstance(contact_ceiling, int)
        or contact_ceiling <= 0
    ):
        raise SpeechNativeProfileError(
            "speech_native_contact_ceiling_per_task must be a positive integer"
        )
    top_k = values.get("speech_native_top_k", 3)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise SpeechNativeProfileError("speech_native_top_k must be a positive integer")
    prompt_policy_id = values.get(
        "matcher_prompt_policy_id", "speech-native-json-copy-v2"
    )
    if not isinstance(prompt_policy_id, str) or not prompt_policy_id:
        raise SpeechNativeProfileError(
            "matcher_prompt_policy_id must be a non-empty string"
        )
    verifier_policy_id = values.get(
        "matcher_verifier_policy_id", "speech-native-compatibility-v1"
    )
    if not isinstance(verifier_policy_id, str) or not verifier_policy_id:
        raise SpeechNativeProfileError(
            "matcher_verifier_policy_id must be a non-empty string"
        )
    dispatch_granularity = values.get("speech_native_dispatch_granularity", "task")
    if dispatch_granularity not in {"task", "contact"}:
        raise SpeechNativeProfileError(
            "speech_native_dispatch_granularity must be 'task' or 'contact'"
        )
    mechanism_control_id = values.get("speech_native_mechanism_control_id", "matched")
    if mechanism_control_id not in {
        "matched",
        "speech-swap-v1",
        "key-text-shuffle-v1",
    }:
        raise SpeechNativeProfileError("unknown speech-native mechanism control")
    tasks = build_profile_tasks(
        samples=gate_view.samples,
        packet_bindings=packet_bindings,
        key_cards=key_cards,
        order_ids=raw_order_ids,
        decoding_params=values.get("decoding_params", {}),
        key_representation_id=key_representation_id,
        matcher_policy_id=_require_string(values, "matcher_policy_id"),
        top_k=top_k,
        prompt_policy_id=prompt_policy_id,
        verifier_policy_id=verifier_policy_id,
        audio_key_bindings=audio_key_bindings,
        mechanism_control_id=mechanism_control_id,
    )
    planned_contact_ceiling = len(tasks) * contact_ceiling
    if planned_contact_ceiling != plan.planned_model_calls:
        raise SpeechNativeProfileError(
            f"profile expands to a {planned_contact_ceiling}-contact ceiling but plan registers "
            f"{plan.planned_model_calls}"
        )

    runtime_receipt = load_runtime_receipt(resolve_runtime_receipt_path(repo_root, values))
    model_root_value = model_materialization_root(values)
    model_root = Path(model_root_value) if model_root_value is not None else None
    from ...contracts import FrozenCoreGate

    frozen_gate = FrozenCoreGate.for_study_repo(
        repo_root,
        root,
        Path(args.runtime_root),
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
        model_root=model_root,
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values),
    )
    session_receipt_path = run_dir / f"{plan.run_id}.session-receipt.json"
    stop_receipt_path = run_dir / f"{plan.run_id}.session-stop-receipt.json"
    audit_path = run_dir / f"{plan.run_id}.mmproj-audit.json"
    server_log_path = run_dir / f"{plan.run_id}.server.log"
    flight_receipt_path = run_dir / "flight-receipt.json"
    decisions_path = run_dir / "decisions.jsonl"
    session = start_session(
        runtime_root=Path(args.runtime_root),
        data_root=root,
        runtime_receipt=runtime_receipt,
        host=args.host,
        port=args.port,
        session_id=f"{plan.run_id}-{plan.attempt_id}",
        extra_argv=_server_args(values),
        extra_env=_server_env(values),
        receipt_path=session_receipt_path,
        server_log_path=server_log_path,
        role=runtime_receipt.get("role", "legacy"),
        model_root=model_root,
    )
    client: FrozenCoreClient | None = None
    close_summary: dict[str, object] | None = None
    sampler = resolve_resource_sampler()
    resource_summary: Mapping[str, object] = {}
    outcomes = ()
    failure: BaseException | None = None
    request_started = False
    try:
        _write_inference_process_audit(session, audit_path)
        transport_factory = TRANSPORTS.resolve(str(values["transport"]))
        transport = transport_factory(
            values,
            root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=Path(args.runtime_root),
        )
        binding = build_payload_binding(
            carrier_lock_key=plan.carrier_lock_key,
            samples=gate_view.samples,
            data_root=root,
            carrier_root=asset_dir(lock, plan.carrier_lock_key, root),
        )
        client = FrozenCoreClient(
            plan=plan,
            gate=frozen_gate,
            transport=transport,
            run_dir=run_dir,
            binding=binding,
            arm="speech-feature-query",
            request_id_prefix="speech-native-profile",
            speech_feature_root=feature_root,
            speech_packet_bindings=packet_bindings,
        )
        sampler.start()
        sampler.begin_request_window()
        request_started = True
        outcomes = run_speech_native_match_tasks(
            core_client=client,
            tasks=tasks,
            slot_count=slot_count,
            queue_depth=slot_count * queue_multiplier,
            dispatch_granularity=dispatch_granularity,
            trace_run_id=plan.run_id,
            trace_flusher=client.flush_trace_buffer,
        )
    except BaseException as error:  # one-shot: record, stop, abort, re-raise
        failure = error
    finally:
        if request_started:
            sampler.end_request_window()
        sampler.stop()
        resource_summary = sampler.summary()
        if client is not None:
            try:
                close_summary = client.close()
            except BaseException as close_error:
                if failure is None:
                    failure = close_error
        stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=Path(args.runtime_root),
            force_after_timeout=True,
            receipt_path=stop_receipt_path,
        )

    attempt = AttemptStore(Path(root) / "attempts").handle(plan.run_id, str(plan.attempt_id))
    attempt_exists = attempt.path.is_file()
    gpu_seconds = resource_summary.get("gpu_seconds")
    if (
        attempt_exists
        and isinstance(gpu_seconds, (int, float))
        and not isinstance(gpu_seconds, bool)
    ):
        attempt.record_gpu_seconds(float(gpu_seconds))
    server_scan = _scan_server_log(server_log_path)
    actual_contact_count = sum(outcome.decision.calls for outcome in outcomes)
    if result_mode == "predictions" and failure is None:
        task_by_id = {task.task_id: task for task in tasks}
        _write_exclusive_jsonl(
            decisions_path,
            tuple(
                {
                    "schema": "saea-speech-native-decision-v1",
                    "task_id": outcome.task_id,
                    "sample_id": (
                        task_by_id[outcome.task_id].scoring_sample_id
                        or task_by_id[outcome.task_id].sample.sample_id
                    ),
                    "query_sample_id": task_by_id[outcome.task_id].sample.sample_id,
                    "mechanism_control_id": task_by_id[
                        outcome.task_id
                    ].mechanism_control_id,
                    "speech_packet_sha256": task_by_id[outcome.task_id].query_descriptor[
                        "sha256"
                    ],
                    "key_representation_id": outcome.decision.key_representation_id,
                    "matcher_policy_id": outcome.decision.matcher_policy_id,
                    "key_id": outcome.decision.key_id,
                    "predicted_value_label": outcome.decision.value_label,
                    "top_key_ids": list(outcome.decision.top_key_ids),
                    "calls": outcome.decision.calls,
                    "parse_failure": outcome.decision.parse_failure,
                    "response_text_sha256": [
                        hashlib.sha256(text.encode("utf-8")).hexdigest()
                        for text in outcome.decision.raw_responses
                    ],
                }
                for outcome in outcomes
            ),
        )
    receipt: dict[str, object] = {
        "schema": "saea-speech-native-profile-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "FAILED" if failure is not None else "COMPLETED",
        "run_id": plan.run_id,
        "attempt_id": plan.attempt_id,
        "config_hash": composed.config_hash,
        "protocol_hash": plan.protocol_hash,
        "split_identity_hash": plan.split_identity_hash,
        "profile": {
            "slot_count": slot_count,
            "queue_depth": slot_count * queue_multiplier,
            "task_count": len(tasks),
            "key_card_count": len(key_cards),
            "key_order_ids": list(raw_order_ids),
            "key_representation_id": values["key_representation_id"],
            "matcher_policy_id": values["matcher_policy_id"],
            "matcher_prompt_policy_id": prompt_policy_id,
            "matcher_verifier_policy_id": verifier_policy_id,
            "dispatch_granularity": dispatch_granularity,
            "mechanism_control_id": mechanism_control_id,
            "query_mapping_sha256": _canonical_sha256(
                {
                    (task.scoring_sample_id or task.sample.sample_id): task.sample.sample_id
                    for task in tasks
                }
            ),
            "key_text_mapping_sha256": (
                _canonical_sha256(
                    {
                        card.key_id: key_cards[(index + 1) % len(key_cards)].key_id
                        for index, card in enumerate(key_cards)
                    }
                )
                if mechanism_control_id == "key-text-shuffle-v1"
                else None
            ),
            "semantic_result_read": False,
            "result_mode": result_mode,
            "contact_ceiling_per_task": contact_ceiling,
            "planned_contact_ceiling": planned_contact_ceiling,
            "actual_contact_count": actual_contact_count,
            "top_k": top_k,
            **geometry,
        },
        "resource": dict(resource_summary),
        "server_log_scan": server_scan,
        "process_audit_sha256": _sha256_file(audit_path),
        "session_receipt_sha256": _sha256_file(session_receipt_path),
        "session_stop_receipt_sha256": _sha256_file(stop_receipt_path),
        "packet_promotion_receipt_sha256": _sha256_file(packet_receipt_path),
        "binding_file_sha256": _sha256_file(binding_path),
        "response_text_sha256": [
            hashlib.sha256(text.encode("utf-8")).hexdigest()
            for outcome in outcomes
            for text in outcome.decision.raw_responses
        ],
        "parse_failure_count": sum(
            1 for outcome in outcomes if outcome.decision.parse_failure
        ),
        "request_failures": [] if failure is None else [f"{type(failure).__name__}: {failure}"],
        "close": close_summary,
    }
    if decisions_path.is_file():
        receipt["decisions"] = {
            "path": decisions_path.name,
            "sha256": _sha256_file(decisions_path),
            "count": len(outcomes),
            "contains_gold_labels": False,
        }
    if close_summary is not None:
        cost = close_summary.get("cost", {})
        if not isinstance(cost, Mapping):
            raise SpeechNativeProfileError("profile close summary cost is malformed")
        trace_path = run_dir / f"{plan.run_id}.trace.jsonl"
        timing_rows = close_summary.get("timings", [])
        if trace_path.is_file():
            trace_usage = _trace_usage_summary(trace_path)
            receipt["trace_usage"] = trace_usage
            receipt["trace_sha256"] = _sha256_file(trace_path)
        receipt["trace_manifest_sha256"] = _sha256_file(
            run_dir / f"{plan.run_id}.trace-manifest.json"
        )
        if timing_rows and trace_path.is_file():
            timing = profile_timing_metrics(
                timing_rows,
                slot_count=slot_count,
                prompt_tokens=int(cost.get("prompt_tokens_total", 0)),
                completion_tokens=int(cost.get("completion_tokens_total", 0)),
            )
            receipt["timing"] = timing
            median_util = resource_summary.get("request_gpu_utilization_median_pct")
            p10_util = resource_summary.get("request_gpu_utilization_p10_pct")
            receipt["eligibility"] = {
                "maximum_prompt_fits_one_slot": (
                    trace_usage["max_prompt_tokens"]
                    + trace_usage["max_completion_tokens"]
                    <= geometry["context_tokens_per_slot"]
                ),
                "zero_request_failures": failure is None,
                "zero_oom_markers": not server_scan["oom_marker_hits"],
                "zero_host_spill_markers": not server_scan["host_spill_marker_hits"],
                "zero_runaway_markers": not server_scan["runaway_marker_hits"],
                "gpu_median_at_least_95": (
                    isinstance(median_util, (int, float))
                    and not isinstance(median_util, bool)
                    and float(median_util) >= 95.0
                ),
                "gpu_p10_at_least_90": (
                    isinstance(p10_util, (int, float))
                    and not isinstance(p10_util, bool)
                    and float(p10_util) >= 90.0
                ),
                "slot_occupancy_at_least_90": timing["slot_occupancy_pct"] >= 90.0,
            }
            eligibility = receipt["eligibility"]
            assert isinstance(eligibility, Mapping)
            receipt["eligible"] = all(bool(value) for value in eligibility.values())
    _write_exclusive_json(flight_receipt_path, receipt)

    if failure is not None:
        if attempt_exists:
            attempt.mark_aborted(
                f"speech-native profile failed: {type(failure).__name__}: {failure}"
            )
        raise failure
    if not attempt_exists:
        raise SpeechNativeProfileError(
            "profile completed without opening its durable attempt accounting record"
        )
    assert close_summary is not None
    cost = close_summary["cost"]
    assert isinstance(cost, Mapping)
    if (
        int(cost.get("calls_used", -1)) != actual_contact_count
        or actual_contact_count < len(tasks)
        or actual_contact_count > planned_contact_ceiling
        or receipt["request_failures"]
        or server_scan["oom_marker_hits"]
        or server_scan["host_spill_marker_hits"]
        or server_scan["runaway_marker_hits"]
        or int(server_scan["mmproj_free_chunk_count"]) < actual_contact_count
    ):
        attempt.mark_aborted("speech-native profile completion checks failed")
        raise SpeechNativeProfileError("profile completion checks failed; see flight receipt")
    attempt.mark_finalized()
    print(
        json.dumps(
            {
                "run_id": plan.run_id,
                "attempt_id": plan.attempt_id,
                "flight_receipt": str(flight_receipt_path),
                "status": "FINALIZED",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cli_speech_native_read(args: argparse.Namespace) -> int:
    report = read_speech_native_predictions(
        attempt_dirs=tuple(Path(path) for path in args.attempt_dir),
        binding_path=Path(args.binding),
        binding_sha256=args.binding_sha256,
        split_name=args.split_name,
    )
    output = Path(args.output)
    _write_exclusive_json(output, report)
    print(
        json.dumps(
            {
                "output": str(output),
                "selected_cell_id": report["selected_cell_id"],
                "aggregates": report["aggregates"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


__all__ = [
    "SpeechNativeProfileError",
    "_cli_speech_native_profile",
    "_cli_speech_native_read",
    "build_profile_tasks",
    "profile_timing_metrics",
    "read_speech_native_predictions",
]
