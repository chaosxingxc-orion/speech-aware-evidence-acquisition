"""Model-free preparation of governed SLURP semantic-authoring support.

This preparation releases source support for later human authoring. It does
not author semantic rules or publish a runtime knowledge store.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..data.lock import load_lock
from ..rails.knowledge_build import (
    KbRow,
    governed_train_jsonl_relpath,
    slurp_kb_rows,
)
from .preparation import prepare_artifact
from .roster import (
    CONSTRUCTION_ROSTER_ROLE,
    RosterItem,
    canonical_receipt_bytes,
    freeze_roster,
    read_roster,
    write_roster,
)

CONFIG_SCHEMA = "saea-slurp-semantic-authoring-support-config-v1"
REGISTRATION_SCHEMA = "saea-semantic-authoring-read-registration-v1"
SUPPORT_SCHEMA = "saea-slurp-semantic-authoring-support-v1"
POLICY_ID = "semantic-authoring-v1"


class SemanticAuthoringSupportError(RuntimeError):
    """Registered support preparation is malformed or source-inconsistent."""


def _selection_key(policy_id: str, utterance_id: str) -> str:
    return hashlib.sha256(f"{policy_id}:{utterance_id}".encode()).hexdigest()


@dataclass(frozen=True)
class SemanticSupportSelection:
    eligible_rows: tuple[KbRow, ...]
    intent_rows: tuple[KbRow, ...]
    slot_rows: tuple[KbRow, ...]
    slot_pairs_by_utterance: Mapping[str, tuple[str, ...]]
    policy_id: str

    @property
    def eligible_sample_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(sample_id for row in self.eligible_rows for sample_id in row.sample_ids)
        )

    def render_row(self, row: KbRow) -> dict[str, object]:
        return {
            "utterance_id": row.utterance_id,
            "selection_sha256": _selection_key(self.policy_id, row.utterance_id),
            "text": row.content,
            "scenario": row.scenario,
            "action": row.action,
            "intent_id": row.intent,
            "recording_ids": list(row.sample_ids),
            "tokens": [
                {"token_id": token.token_id, "surface": token.surface}
                for token in row.source_tokens
            ],
            "entities": [
                {
                    "entity_type": mention.entity_type,
                    "token_span_ids": list(mention.token_ids),
                    "filler": mention.filler,
                }
                for mention in row.entity_mentions
            ],
        }


def select_semantic_authoring_support(
    rows: Sequence[KbRow],
    *,
    intent_limit: int,
    slot_pair_limit: int,
    policy_id: str,
    forbidden_sample_ids: Collection[str] = (),
) -> SemanticSupportSelection:
    """Select bounded support after excluding every touched utterance."""
    if not isinstance(policy_id, str) or not policy_id:
        raise SemanticAuthoringSupportError("policy_id must be non-empty text")
    for name, value in (("intent_limit", intent_limit), ("slot_pair_limit", slot_pair_limit)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise SemanticAuthoringSupportError(f"{name} must be a positive integer")
    forbidden = frozenset(forbidden_sample_ids)
    eligible = tuple(
        sorted(
            (row for row in rows if not forbidden.intersection(row.sample_ids)),
            key=lambda row: row.utterance_id,
        )
    )
    if not eligible:
        raise SemanticAuthoringSupportError("support pool is empty after exclusion")
    ids = [row.utterance_id for row in eligible]
    if len(ids) != len(set(ids)):
        raise SemanticAuthoringSupportError("support pool repeats an utterance id")

    by_intent: dict[str, list[KbRow]] = defaultdict(list)
    by_pair: dict[tuple[str, str], list[KbRow]] = defaultdict(list)
    for row in eligible:
        by_intent[row.intent].append(row)
        for entity_type in sorted(set(row.entity_types)):
            by_pair[(row.intent, entity_type)].append(row)
    def order(row: KbRow) -> tuple[str, str]:
        return _selection_key(policy_id, row.utterance_id), row.utterance_id
    intent_rows = tuple(
        row
        for intent in sorted(by_intent)
        for row in sorted(by_intent[intent], key=order)[:intent_limit]
    )
    selected_slot: dict[str, KbRow] = {}
    pairs: dict[str, set[str]] = defaultdict(set)
    for intent, entity_type in sorted(by_pair):
        pair_id = f"{intent}:{entity_type}"
        for row in sorted(by_pair[(intent, entity_type)], key=order)[:slot_pair_limit]:
            selected_slot[row.utterance_id] = row
            pairs[row.utterance_id].add(pair_id)
    slot_rows = tuple(sorted(selected_slot.values(), key=order))
    return SemanticSupportSelection(
        eligible_rows=eligible,
        intent_rows=intent_rows,
        slot_rows=slot_rows,
        slot_pairs_by_utterance={
            utterance_id: tuple(sorted(values)) for utterance_id, values in pairs.items()
        },
        policy_id=policy_id,
    )


def _read_pinned(path: Path, sha256: str, name: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise SemanticAuthoringSupportError(f"unable to read {name}") from error
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise SemanticAuthoringSupportError(f"{name} differs from its registered SHA-256")
    return raw


def _pin(value: object, name: str) -> tuple[Path, str]:
    if not isinstance(value, Mapping) or set(value) != {"path", "sha256"}:
        raise SemanticAuthoringSupportError(f"{name} must contain path and sha256")
    path, sha256 = value["path"], value["sha256"]
    if not isinstance(path, str) or not isinstance(sha256, str) or len(sha256) != 64:
        raise SemanticAuthoringSupportError(f"{name} pin is malformed")
    return Path(path), sha256


def _snapshot_pin(value: object) -> tuple[Path, str, str]:
    if not isinstance(value, Mapping) or set(value) != {
        "path", "sha256", "content_sha256"
    }:
        raise SemanticAuthoringSupportError(
            "pool_snapshot must contain path, sha256 and content_sha256"
        )
    path = value["path"]
    sha256 = value["sha256"]
    content_sha256 = value["content_sha256"]
    if (
        not isinstance(path, str)
        or not isinstance(sha256, str)
        or len(sha256) != 64
        or not isinstance(content_sha256, str)
        or len(content_sha256) != 64
    ):
        raise SemanticAuthoringSupportError("pool_snapshot pin is malformed")
    return Path(path), sha256, content_sha256


def _roster_document(
    rows: Sequence[KbRow], *, roster_id: str, support_pairs: Mapping[str, tuple[str, ...]] | None = None
) -> dict[str, object]:
    candidates = []
    for row in rows:
        for sample_id in row.sample_ids:
            extra: dict[str, object] = {"utterance_id": row.utterance_id}
            if support_pairs is not None:
                extra["support_pairs"] = list(support_pairs[row.utterance_id])
            candidates.append(RosterItem(sample_id, row.intent, extra))
    quotas = Counter(item.stratum for item in candidates)
    return freeze_roster(
        carrier_lock_key="slurp",
        candidates=tuple(candidates),
        per_stratum=quotas,
        seed=0,
        split_role="discovery",
        roster_id=roster_id,
        roster_role=CONSTRUCTION_ROSTER_ROLE,
    )


def _write_or_verify_roster(path: Path, document: Mapping[str, object]) -> dict[str, str]:
    raw = canonical_receipt_bytes(document)
    if path.exists():
        if path.read_bytes() != raw:
            raise SemanticAuthoringSupportError(f"roster output collision at {path.name}")
        read_roster(path)
    else:
        write_roster(document, path)
    return {"relpath": path.name, "sha256": hashlib.sha256(raw).hexdigest()}


def _validate_snapshot(
    snapshot: Mapping[str, Any],
    selection: SemanticSupportSelection,
    *,
    expected_content_sha256: str,
    expected_source_identity: str,
) -> None:
    if (
        snapshot.get("source_partition_role") != "train"
        or snapshot.get("source_split_identity_hash") != expected_source_identity
        or snapshot.get("snapshot_sha256") != expected_content_sha256
    ):
        raise SemanticAuthoringSupportError("pool snapshot identity differs")
    if tuple(sorted(snapshot.get("source_sample_ids", ()))) != selection.eligible_sample_ids:
        raise SemanticAuthoringSupportError("pool snapshot recording membership differs")
    values = snapshot.get("values")
    if not isinstance(values, list):
        raise SemanticAuthoringSupportError("pool snapshot values must be a list")
    by_id = {value.get("value_id"): value for value in values if isinstance(value, Mapping)}
    if len(by_id) != len(selection.eligible_rows):
        raise SemanticAuthoringSupportError("pool snapshot utterance membership differs")
    for row in selection.eligible_rows:
        value = by_id.get(f"value:{row.utterance_id}")
        if (
            not isinstance(value, Mapping)
            or tuple(value.get("source_sample_ids", ())) != tuple(row.sample_ids)
            or value.get("task_target") != row.intent
        ):
            raise SemanticAuthoringSupportError(
                f"pool snapshot membership differs for utterance {row.utterance_id}"
            )


def prepare_slurp_semantic_authoring_support(
    config_path: Path, *, repo_root: Path, data_root: Path
) -> Mapping[str, object]:
    """Prepare the exact registered support and three construction rosters."""
    config_raw = Path(config_path).read_bytes()
    config = json.loads(config_raw)
    if not isinstance(config, Mapping) or set(config) != {
        "schema", "registration", "selection_policy_id"
    }:
        raise SemanticAuthoringSupportError("support config fields differ")
    if config["schema"] != CONFIG_SCHEMA or config["selection_policy_id"] != POLICY_ID:
        raise SemanticAuthoringSupportError("support config identity differs")
    registration_pin = config["registration"]
    if not isinstance(registration_pin, Mapping) or set(registration_pin) != {"relpath", "sha256"}:
        raise SemanticAuthoringSupportError("registration pin is malformed")
    registration_path = repo_root / str(registration_pin["relpath"])
    registration_raw = _read_pinned(
        registration_path, str(registration_pin["sha256"]), "registration"
    )
    registration = json.loads(registration_raw)
    if not isinstance(registration, Mapping) or registration.get("schema") != REGISTRATION_SCHEMA:
        raise SemanticAuthoringSupportError("registration schema differs")
    if Path(str(registration.get("data_root"))).resolve() != data_root.resolve():
        raise SemanticAuthoringSupportError("data_root differs from registration")

    lock_path, lock_sha = _pin(registration.get("lock"), "lock")
    _read_pinned(lock_path, lock_sha, "dataset lock")
    lock = load_lock(lock_path)
    for index, value in enumerate(registration.get("loader_sources", ())):
        path, sha256 = _pin(value, f"loader_sources[{index}]")
        _read_pinned(path, sha256, f"loader_sources[{index}]")
    pool_receipt_path, pool_receipt_sha = _pin(registration.get("pool_receipt"), "pool_receipt")
    _read_pinned(pool_receipt_path, pool_receipt_sha, "pool receipt")

    forbidden_ids: set[str] = set()
    forbidden_pins = []
    for index, value in enumerate(registration.get("forbidden_rosters", ())):
        path, sha256 = _pin(value, f"forbidden_rosters[{index}]")
        _read_pinned(path, sha256, f"forbidden_rosters[{index}]")
        forbidden_pins.append({"path": str(path), "sha256": sha256})
        document = json.loads(path.read_bytes())
        if document.get("schema") == "saea-roster-receipt-v1":
            forbidden_ids.update(
                str(item["sample_id"]) for item in read_roster(path)["items"]
            )

    rows = slurp_kb_rows(lock, data_root)
    selection = registration.get("selection")
    if not isinstance(selection, Mapping):
        raise SemanticAuthoringSupportError("registration selection is missing")
    selected = select_semantic_authoring_support(
        rows,
        intent_limit=8,
        slot_pair_limit=3,
        policy_id=POLICY_ID,
        forbidden_sample_ids=forbidden_ids,
    )
    expected = registration.get("expected_pool")
    if not isinstance(expected, Mapping):
        raise SemanticAuthoringSupportError("expected_pool is missing")
    observed = {
        "utterances": len(selected.eligible_rows),
        "recordings": len(selected.eligible_sample_ids),
        "intents": len({row.intent for row in selected.eligible_rows}),
        "entity_types": len(
            {entity_type for row in selected.eligible_rows for entity_type in row.entity_types}
        ),
        "source_split_identity_hash": hashlib.sha256(
            "\n".join(selected.eligible_sample_ids).encode("utf-8")
        ).hexdigest(),
    }
    if any(observed.get(key) != expected.get(key) for key in observed):
        raise SemanticAuthoringSupportError("remaining pool differs from registration")

    snapshot_pin = registration.get("pool_snapshot")
    snapshot_path, snapshot_sha, snapshot_content_sha = _snapshot_pin(snapshot_pin)
    snapshot_raw = _read_pinned(snapshot_path, snapshot_sha, "pool snapshot")
    snapshot = json.loads(snapshot_raw)
    _validate_snapshot(
        snapshot,
        selected,
        expected_content_sha256=snapshot_content_sha,
        expected_source_identity=str(expected["source_split_identity_hash"]),
    )

    namespace = data_root / str(registration["outputs"]["namespace"])
    namespace.mkdir(parents=True, exist_ok=True)
    outer = _roster_document(selected.eligible_rows, roster_id="slurp-semantic-authoring-outer-v1")
    intent = _roster_document(selected.intent_rows, roster_id="slurp-semantic-authoring-intent-support-v1")
    slot = _roster_document(
        selected.slot_rows,
        roster_id="slurp-semantic-authoring-slot-support-v1",
        support_pairs=selected.slot_pairs_by_utterance,
    )
    roster_pins = {
        "outer": _write_or_verify_roster(namespace / "outer-construction-roster.json", outer),
        "intent": _write_or_verify_roster(namespace / "intent-support-construction-roster.json", intent),
        "slot": _write_or_verify_roster(namespace / "slot-support-construction-roster.json", slot),
    }
    provenance = {
        "registration": dict(registration_pin),
        "config_sha256": hashlib.sha256(config_raw).hexdigest(),
        "lock": {"path": str(lock_path), "sha256": lock_sha},
        "pool_receipt": {"path": str(pool_receipt_path), "sha256": pool_receipt_sha},
        "pool_snapshot": dict(snapshot_pin),
        "forbidden_rosters": forbidden_pins,
        "source_metadata_relpath": governed_train_jsonl_relpath(lock, data_root),
        "selection_policy_id": POLICY_ID,
    }
    support_output = {
        "schema": SUPPORT_SCHEMA,
        "provenance": provenance,
        "intent_support": [selected.render_row(row) for row in selected.intent_rows],
        "slot_support": [
            {
                **selected.render_row(row),
                "support_pairs": list(selected.slot_pairs_by_utterance[row.utterance_id]),
            }
            for row in selected.slot_rows
        ],
    }
    support_receipt = prepare_artifact(
        namespace / "support.json",
        kind="slurp-semantic-authoring-support",
        inputs={"provenance": provenance, "rosters": roster_pins},
        producer=lambda: support_output,
        contact_class="model-free",
    )
    support_pin = {
        "relpath": "support.json",
        "sha256": str(support_receipt["sha256"]),
    }
    aggregate = {
        "schema": "saea-slurp-semantic-authoring-support-receipt-v1",
        "registration_id": registration["registration_id"],
        "pool": observed,
        "exclusion_trigger_recordings": len(forbidden_ids),
        "excluded_utterances": len(rows) - len(selected.eligible_rows),
        "excluded_recordings": sum(len(row.sample_ids) for row in rows)
        - len(selected.eligible_sample_ids),
        "intent_support_utterances": len(selected.intent_rows),
        "intent_support_recordings": sum(len(row.sample_ids) for row in selected.intent_rows),
        "slot_support_utterances": len(selected.slot_rows),
        "slot_support_recordings": sum(len(row.sample_ids) for row in selected.slot_rows),
        "observed_intent_entity_pairs": len(
            {pair for pairs in selected.slot_pairs_by_utterance.values() for pair in pairs}
        ),
        "rosters": roster_pins,
        "support": support_pin,
        "contacts": {"model": 0, "encoder": 0, "tokenizer": 0, "gpu": 0, "tool_backend": 0, "scorer": 0},
        "runtime_store_released": False,
    }
    receipt = prepare_artifact(
        namespace / "receipt.json",
        kind="slurp-semantic-authoring-support-receipt",
        inputs={"support": support_pin, "rosters": roster_pins},
        producer=lambda: aggregate,
        contact_class="model-free",
    )
    return {"support": support_receipt, "receipt": receipt, "aggregate": aggregate}


__all__ = [
    "SemanticAuthoringSupportError",
    "SemanticSupportSelection",
    "prepare_slurp_semantic_authoring_support",
    "select_semantic_authoring_support",
]
