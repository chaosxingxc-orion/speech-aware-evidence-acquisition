"""SupplyPacket: the SUPPLY-axis prompt-level delivery contract.

Prompt-level supply ONLY (owner ruling: no logit_bias anywhere in this
study) -- a ``SupplyPacket``'s ``prompt_block`` is exactly the text a
``TaskAdapter`` renders into the model's prompt; there is no field anywhere
in this module for a decoding-time bias.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .errors import RailsError
from .hashing import content_hash

SUPPLY_PACKET_VERSION = "supply-packet-v1"


class SupplyForm(str, Enum):
    ROSTER = "roster"
    TEXT = "text"
    KV = "kv"


@dataclass(frozen=True)
class SupplyItem:
    """One evidence item as actually rendered into ``prompt_block`` -- the
    unit ``rails.consumption.ConsumptionTrace`` attributes an outcome to.
    ``evidence_id`` optionally names the ``rails.evidence.EvidenceItem`` this
    rendering came from (``None`` for supply assembled from a non-EvidenceItem
    source, e.g. a static roster line with no per-item legality provenance)."""

    item_id: str
    text: str
    evidence_id: str | None = None

    def validate(self) -> "SupplyItem":
        if not isinstance(self.item_id, str) or not self.item_id:
            raise RailsError("SupplyItem.item_id must be a non-empty string")
        if not isinstance(self.text, str) or not self.text:
            raise RailsError("SupplyItem.text must be a non-empty string")
        if self.evidence_id is not None and not isinstance(self.evidence_id, str):
            raise RailsError("SupplyItem.evidence_id must be a string or None")
        return self

    def as_json(self) -> dict[str, object]:
        return {"item_id": self.item_id, "text": self.text, "evidence_id": self.evidence_id}

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "SupplyItem":
        return cls(
            item_id=document["item_id"],
            text=document["text"],
            evidence_id=document.get("evidence_id"),
        ).validate()


@dataclass(frozen=True)
class SupplyDose:
    n_items: int
    token_count: int

    def validate(self) -> "SupplyDose":
        for label, value in (("n_items", self.n_items), ("token_count", self.token_count)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise RailsError(f"SupplyDose.{label} must be a non-negative integer, got {value!r}")
        return self

    def as_json(self) -> dict[str, object]:
        return {"n_items": self.n_items, "token_count": self.token_count}

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "SupplyDose":
        return cls(n_items=document["n_items"], token_count=document["token_count"]).validate()


@dataclass(frozen=True)
class SupplyPacket:
    form: SupplyForm
    dose: SupplyDose
    prompt_block: str
    assembly_template_id: str
    # Not part of the mission's original three-field sketch -- added so
    # rails.consumption.build_consumption_trace has a well-defined,
    # per-supplied-item unit to attribute a USE/COPY/IGNORE outcome to,
    # rather than only a flattened prompt_block string with no per-item
    # boundaries. Optional/defaulted empty: a SupplyPacket built without
    # per-item granularity (dose known, items not tracked) stays legal, it
    # simply cannot feed extract_consumption anything but an empty trace.
    items: tuple[SupplyItem, ...] = ()
    supply_packet_version: str = SUPPLY_PACKET_VERSION

    def validate(self) -> "SupplyPacket":
        if not isinstance(self.form, SupplyForm):
            raise RailsError(f"SupplyPacket.form must be a SupplyForm, got {self.form!r}")
        self.dose.validate()
        if not isinstance(self.prompt_block, str):
            raise RailsError("SupplyPacket.prompt_block must be a string")
        if not isinstance(self.assembly_template_id, str) or not self.assembly_template_id:
            raise RailsError("SupplyPacket.assembly_template_id must be a non-empty string")
        seen: set[str] = set()
        for item in self.items:
            if not isinstance(item, SupplyItem):
                raise RailsError("SupplyPacket.items entries must be SupplyItem instances")
            item.validate()
            if item.item_id in seen:
                raise RailsError(f"SupplyPacket.items has a duplicate item_id {item.item_id!r}")
            seen.add(item.item_id)
        if self.items and self.dose.n_items != len(self.items):
            raise RailsError(
                f"SupplyPacket.dose.n_items ({self.dose.n_items}) does not match len(items) "
                f"({len(self.items)}) -- when items is populated it must agree with the "
                "declared dose"
            )
        if not isinstance(self.supply_packet_version, str) or not self.supply_packet_version:
            raise RailsError("SupplyPacket.supply_packet_version must be a non-empty string")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "form": self.form.value,
            "dose": self.dose.as_json(),
            "prompt_block": self.prompt_block,
            "assembly_template_id": self.assembly_template_id,
            "items": [item.as_json() for item in self.items],
            "supply_packet_version": self.supply_packet_version,
        }

    def content_hash(self) -> str:
        return content_hash(self.validate().as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "SupplyPacket":
        return cls(
            form=SupplyForm(document["form"]),
            dose=SupplyDose.from_json(document["dose"]),
            prompt_block=document["prompt_block"],
            assembly_template_id=document["assembly_template_id"],
            items=tuple(SupplyItem.from_json(item) for item in document.get("items", [])),
            supply_packet_version=document.get("supply_packet_version", SUPPLY_PACKET_VERSION),
        ).validate()
