"""Offline, hash-pinned links from finalized TRAIN runs to experience sources.

The current ExperienceSource runtime carrier mapping is deliberately narrow: only SLURP construction rosters with slurp:train:* identities are accepted. Stage-2 plans may use other split roles; membership comes from this pinned construction roster.
This module prepares provenance for a later, human-controlled memory admission step. It never creates or updates provisional or admitted memory records.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..contracts import TraceRecord
from ..core.bundle.verify import verify_bundle
from ..core.roster import CONSTRUCTION_ROSTER_ROLE, read_roster
from ..core.scoring_receipt import SavedScoreReceiptRef, verify_complete_score_receipt
from .experience_memory import ExperienceSource
from .hashing import content_hash

REWARD_LINK_SCHEMA = "saea-reward-link-v1"
REWARD_PROJECTION_SCHEMA = "saea-reward-projection-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FORBIDDEN_SCORERS = frozenset({"cost", "cost-v1", "cost-scorer"})
_REQUEST_AXES = frozenset({"request", "model_request", "prompt"})
_RESPONSE_AXES = frozenset({"response", "model_response", "answer"})
_COST_AXES = frozenset({"cost", "latency"})
_MANIFEST_KEYS = frozenset({"tool_id", "tool_manifest_sha256", "manifest_sha256", "tool_manifest_id"})


class RewardLinkError(ValueError):
    """A reward link cannot be built or re-verified."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RewardLinkError(f"{field} must be non-empty text")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise RewardLinkError(f"{field} must be a lowercase SHA-256")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RewardLinkError(f"{field} must be an object")
    return value


def _path(value: Mapping[str, object], name: str) -> object:
    current: object = value
    for part in name.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise RewardLinkError(f"declared score field {name!r} is absent")
        current = current[part]
    return current


def _numeric(value: object, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RewardLinkError(f"{field} must be numeric")
    if isinstance(value, float) and not math.isfinite(value):
        raise RewardLinkError(f"{field} must be finite")
    return value


def _fields(value: object, field: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or not value:
        raise RewardLinkError(f"{field} must be a non-empty sequence")
    result = tuple(_text(item, f"{field}[{index}]") for index, item in enumerate(value))
    if len(result) != len(set(result)):
        raise RewardLinkError(f"{field} must contain unique paths")
    if any(path.startswith(".") or path.endswith(".") for path in result):
        raise RewardLinkError(f"{field} contains an invalid dotted path")
    return result


@dataclass(frozen=True)
class RewardProjection:
    """Frozen declaration of the numeric fields copied from an official score."""

    reward_rule_id: str
    scorer: str
    aggregate_fields: tuple[str, ...]
    per_sample_fields: tuple[str, ...]
    schema: str = REWARD_PROJECTION_SCHEMA

    def __post_init__(self) -> None:
        _text(self.reward_rule_id, "reward rule ID")
        _text(self.scorer, "scorer")
        if self.scorer.lower() in _FORBIDDEN_SCORERS:
            raise RewardLinkError("cost scorers cannot be reward projections")
        _fields(self.aggregate_fields, "aggregate_fields")
        _fields(self.per_sample_fields, "per_sample_fields")
        if self.schema != REWARD_PROJECTION_SCHEMA:
            raise RewardLinkError("unsupported reward projection schema")

    def as_json(self) -> dict[str, object]:
        return {"schema": self.schema, "reward_rule_id": self.reward_rule_id, "scorer": self.scorer,
                "aggregate_fields": list(self.aggregate_fields), "per_sample_fields": list(self.per_sample_fields)}

    @classmethod
    def from_json(cls, value: object) -> "RewardProjection":
        row = _mapping(value, "reward projection")
        return cls(_text(row.get("reward_rule_id"), "reward_rule_id"), _text(row.get("scorer"), "scorer"),
                   _fields(row.get("aggregate_fields"), "aggregate_fields"),
                   _fields(row.get("per_sample_fields"), "per_sample_fields"),
                   _text(row.get("schema"), "projection schema"))


@dataclass(frozen=True)
class RewardLink:
    """One immutable sample-level binding and its proposal-safe numeric vector."""

    source: ExperienceSource
    carrier_lock_key: str
    construction_roster_sha256: str
    projection: RewardProjection
    native_score_vector: Mapping[str, object]
    provenance: Mapping[str, object]
    link_sha256: str
    schema: str = REWARD_LINK_SCHEMA

    def unsigned_json(self) -> dict[str, object]:
        return {"schema": self.schema, "source": self.source.as_json(), "carrier_lock_key": self.carrier_lock_key,
                "construction_roster_sha256": self.construction_roster_sha256, "projection": self.projection.as_json(),
                "native_score_vector": dict(self.native_score_vector), "provenance": dict(self.provenance)}

    def validate(self) -> None:
        if self.schema != REWARD_LINK_SCHEMA:
            raise RewardLinkError("unsupported reward link schema")
        self.source.validate()
        if self.source.partition_role != "train":
            raise RewardLinkError("reward links must target the TRAIN source partition")
        _text(self.carrier_lock_key, "carrier lock key")
        _sha(self.construction_roster_sha256, "construction roster SHA-256")
        self.projection.__post_init__()
        _sha(self.link_sha256, "reward link SHA-256")
        if content_hash(self.unsigned_json()) != self.link_sha256:
            raise RewardLinkError("reward link hash does not match its immutable contents")

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {**self.unsigned_json(), "link_sha256": self.link_sha256}

    def to_experience_source(self) -> ExperienceSource:
        self.validate()
        return self.source


def _artifact_pin(manifest: Mapping[str, object], key: str) -> dict[str, str]:
    value = _mapping(manifest.get(key), f"manifest {key}")
    path = _text(value.get("path"), f"manifest {key}.path")
    digest = _sha(value.get("sha256"), f"manifest {key}.sha256")
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual != digest:
        raise RewardLinkError(f"{key} changed after bundle verification")
    return {"path": str(Path(path).resolve()), "sha256": digest}


def _sample_for(record_id: str, payload: Mapping[str, object], sample_ids: set[str]) -> str:
    candidates = {sample for sample in sample_ids if sample in record_id}
    for value in (payload.get("sample_id"), payload.get("request_id")):
        if isinstance(value, str):
            candidates.update(sample for sample in sample_ids if sample in value)
    if len(candidates) != 1:
        raise RewardLinkError(f"trace record {record_id!r} does not map to exactly one roster sample")
    return next(iter(candidates))


def _manifest_identities(payload: object) -> dict[str, object]:
    found: dict[str, object] = {}
    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if isinstance(key, str) and (key in _MANIFEST_KEYS or key.endswith("_manifest_sha256")):
                    if isinstance(child, (str, int, float, bool)) or child is None:
                        found[key] = child
                visit(child)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for child in value:
                visit(child)
    visit(payload)
    return dict(sorted(found.items()))


def _trace(manifest: Mapping[str, object], sample_ids: set[str]) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
    meta = _mapping(manifest.get("raw_trace"), "manifest raw_trace")
    path = Path(_text(meta.get("path"), "raw_trace.path"))
    expected = _sha(meta.get("sha256"), "raw_trace.sha256")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise RewardLinkError("raw trace changed after bundle verification")
    by_sample: dict[str, list[dict[str, object]]] = {sample: [] for sample in sample_ids}
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise RewardLinkError(f"raw trace line {line_number} is invalid") from error
        record = _mapping(row, f"trace line {line_number}")
        axis = _text(record.get("channel"), "trace channel")
        record_id = _text(record.get("record_id"), "trace record_id")
        payload = _mapping(record.get("payload"), "trace payload")
        sample = _sample_for(record_id, payload, sample_ids)
        by_sample[sample].append({"axis": axis, "record_id": record_id,
                                  "event_sha256": TraceRecord(channel=axis, record_id=record_id, payload=payload).content_hash(),
                                  "tool_manifest_identity": _manifest_identities(payload)})
    actions: dict[str, list[dict[str, object]]] = {}
    for sample, events in by_sample.items():
        if not events:
            raise RewardLinkError(f"sample {sample!r} has no trace events")
        if not any(event["axis"].lower() in _RESPONSE_AXES for event in events):
            raise RewardLinkError(f"sample {sample!r} has no response event")
        selected = [event for event in events if event["axis"].lower() not in _REQUEST_AXES
                    and event["axis"].lower() not in _RESPONSE_AXES and event["axis"].lower() not in _COST_AXES]
        if not selected:
            raise RewardLinkError(f"sample {sample!r} has no ordered action events")
        actions[sample] = selected
    return by_sample, actions


def _score_vector(receipt: Mapping[str, object], projection: RewardProjection, sample_ids: set[str]) -> tuple[dict[str, object], str]:
    result_meta = _mapping(receipt.get("score_result"), "score receipt score_result")
    result_path = Path(_text(result_meta.get("path"), "score_result.path"))
    result_sha = _sha(result_meta.get("sha256"), "score_result.sha256")
    raw = result_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != result_sha:
        raise RewardLinkError("score result changed after score receipt verification")
    result = _mapping(json.loads(raw.decode("utf-8")), "score result")
    scores = _mapping(result.get("scores"), "score result scores")
    score = _mapping(scores.get(projection.scorer), f"scores[{projection.scorer}]")
    aggregate = _mapping(score.get("aggregate"), "score aggregate")
    rows = score.get("per_sample")
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise RewardLinkError("score per_sample must be a sequence")
    by_id: dict[str, Mapping[str, object]] = {}
    for row in rows:
        item = _mapping(row, "score per_sample row")
        sample = _text(item.get("sample_id"), "score sample_id")
        if sample in by_id:
            raise RewardLinkError(f"duplicate score row for {sample!r}")
        by_id[sample] = item
    if set(by_id) != sample_ids:
        raise RewardLinkError("score rows do not exactly match the construction roster")
    aggregate_vector = {field: _numeric(_path(aggregate, field), f"aggregate.{field}") for field in projection.aggregate_fields}
    per_sample = {sample: {field: _numeric(_path(by_id[sample], field), f"{sample}.{field}") for field in projection.per_sample_fields}
                  for sample in sorted(sample_ids)}
    return {"aggregate": aggregate_vector, "per_sample": per_sample}, result_sha


def _build_one(bundle: Any, roster: Mapping[str, object], roster_sha: str, receipt: Mapping[str, object],
               projection: RewardProjection, score_vector: Mapping[str, object], score_result_sha: str,
               events: Mapping[str, list[dict[str, object]]], actions: Mapping[str, list[dict[str, object]]], sample: str) -> RewardLink:
    outputs = [row for row in bundle.outputs_rows if row.get("sample_id") == sample]
    if len(outputs) != 1:
        raise RewardLinkError(f"sample {sample!r} must have exactly one output row")
    output = _mapping(outputs[0], f"output for {sample}")
    response = _sha(output.get("response_text_sha256"), f"response hash for {sample}")
    per = _mapping(score_vector["per_sample"], "per_sample")
    row_vector = {"aggregate": score_vector["aggregate"], "per_sample": {sample: per[sample]}}
    trajectory = content_hash({"events": events[sample]})
    action = content_hash({"actions": actions[sample]})
    outcome = content_hash({"partition_role": "train", "sample_id": sample, "carrier_lock_key": roster.get("carrier_lock_key"),
                            "construction_roster_sha256": roster_sha,
                            "reward_rule_id": projection.reward_rule_id, "scorer": projection.scorer,
                            "projection": projection.as_json(), "native_score_vector": row_vector,
                            "score_result_sha256": score_result_sha})
    source = ExperienceSource("train", sample, trajectory, action, response, outcome)
    manifest_path = Path(bundle.manifest_path).resolve()
    provenance = {"manifest": {"path": str(manifest_path), "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()},
                  "outputs": _artifact_pin(bundle.manifest, "outputs"), "raw_trace": _artifact_pin(bundle.manifest, "raw_trace"),
                  "trace_manifest": _artifact_pin(bundle.manifest, "trace_manifest"), "score_result_sha256": score_result_sha,
                  "score_receipt_identity": receipt.get("identity"), "ordered_events": events[sample], "ordered_actions": actions[sample]}
    unsigned = {"schema": REWARD_LINK_SCHEMA, "source": source.as_json(),
                "carrier_lock_key": _text(roster.get("carrier_lock_key"), "carrier_lock_key"),
                "construction_roster_sha256": roster_sha, "projection": projection.as_json(),
                "native_score_vector": row_vector, "provenance": provenance}
    return RewardLink(source, unsigned["carrier_lock_key"], roster_sha, projection, row_vector, provenance, content_hash(unsigned))


def build_reward_links(manifest_path: Path, score_receipt: SavedScoreReceiptRef, construction_roster_path: Path,
                       projection: RewardProjection) -> tuple[RewardLink, ...]:
    """Verify a complete TRAIN bundle and score, then build immutable links."""
    if not isinstance(projection, RewardProjection):
        raise RewardLinkError("projection must be a RewardProjection")
    bundle = verify_bundle(Path(manifest_path))
    if bundle.manifest.get("status") != "COMPLETED" or bundle.attempt_state != "FINALIZED":
        raise RewardLinkError("reward links require a COMPLETED bundle with FINALIZED attempt")
    roster = read_roster(Path(construction_roster_path))
    if roster.get("roster_role") != CONSTRUCTION_ROSTER_ROLE:
        raise RewardLinkError("reward links require a construction roster")
    carrier = _text(roster.get("carrier_lock_key"), "roster carrier_lock_key")
    split = _mapping(bundle.manifest.get("split"), "bundle split")
    if split.get("carrier_lock_key") != carrier:
        raise RewardLinkError("bundle and construction roster carriers differ")
    items = roster.get("items")
    if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
        raise RewardLinkError("construction roster lacks items")
    ids = [item.get("sample_id") for item in items if isinstance(item, Mapping)]
    roster_ids = tuple(_text(item, "roster sample ID") for item in ids)
    if len(set(roster_ids)) != len(roster_ids) or set(roster_ids) != set(bundle.split_ids):
        raise RewardLinkError("bundle split is not exactly the construction roster")
    if carrier != "slurp":
        raise RewardLinkError("ExperienceSource conversion currently supports only SLURP TRAIN construction")
    if carrier == "slurp" and any(not sample.startswith("slurp:train:") for sample in roster_ids):
        raise RewardLinkError("SLURP construction sources must use slurp:train:* identities")
    scorers = bundle.manifest.get("scorers")
    if not isinstance(scorers, Sequence) or projection.scorer not in set(scorers):
        raise RewardLinkError("declared scorer is not pinned in the bundle")
    receipt = verify_complete_score_receipt(score_receipt, bundle)
    vector, result_sha = _score_vector(receipt, projection, set(roster_ids))
    events, actions = _trace(bundle.manifest, set(roster_ids))
    roster_sha = hashlib.sha256(Path(construction_roster_path).read_bytes()).hexdigest()
    return tuple(_build_one(bundle, roster, roster_sha, receipt, projection, vector, result_sha, events, actions, sample)
                 for sample in roster_ids)


def verify_reward_links(links: Sequence[RewardLink], manifest_path: Path, score_receipt: SavedScoreReceiptRef,
                        construction_roster_path: Path, projection: RewardProjection) -> tuple[RewardLink, ...]:
    """Re-run every upstream verifier and require byte-identical links."""
    expected = build_reward_links(manifest_path, score_receipt, construction_roster_path, projection)
    given = tuple(links)
    for link in given:
        link.validate()
    if len(given) != len(expected) or {link.source.source_sample_id: link.as_json() for link in given} != {link.source.source_sample_id: link.as_json() for link in expected}:
        raise RewardLinkError("reward link does not match current verified artifacts")
    return expected


def build_experience_sources(manifest_path: Path, score_receipt: SavedScoreReceiptRef, construction_roster_path: Path,
                             projection: RewardProjection) -> tuple[ExperienceSource, ...]:
    """Convert only freshly re-verified links to source records."""
    links = build_reward_links(manifest_path, score_receipt, construction_roster_path, projection)
    return tuple(link.to_experience_source() for link in verify_reward_links(links, manifest_path, score_receipt, construction_roster_path, projection))


build_reward_link = build_reward_links
build_reward_link_sources = build_experience_sources

__all__ = ["REWARD_LINK_SCHEMA", "REWARD_PROJECTION_SCHEMA", "RewardLink", "RewardLinkError", "RewardProjection",
           "build_experience_sources", "build_reward_link", "build_reward_link_sources", "build_reward_links", "verify_reward_links"]