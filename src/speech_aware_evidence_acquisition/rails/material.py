"""PhaseMaterial: one model-contact's fixed instruction + response-shape
material, kept as its own small, content-hashable record.

C2 consolidation ("one task base, thin adapters"): this is a standalone
building block -- not yet wired into ``TaskAdapter`` or any concrete
adapter -- that a later mission can use to carry one contact's instruction
material (what ``rails.runner.AgentContactPlan.instruction`` ends up being
built from) independently of the sample/supply plumbing ``assemble_prompt``
already owns. Deliberately minimal: no ``TaskSample``/``SupplyPacket``
coupling, so it can be constructed, validated and content-hashed in
isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .errors import RailsError
from .hashing import content_hash

PHASE_MATERIAL_VERSION = "phase-material-v1"


@dataclass(frozen=True)
class PhaseMaterial:
    """One phase's fixed contact material.

    ``instruction``: the fixed instruction text for this contact/phase.
    ``response_format``: an optional structured response-shape declaration
    (e.g. a JSON schema fragment); ``None`` when the phase expects free text.
    ``contact_id``: the stable id this material is bound to (mirrors
    ``rails.runner.AgentContactPlan.contact_id``'s own non-empty-string
    discipline).
    ``purpose``: a short, stable label for why this contact exists (e.g.
    ``"acquire"``, ``"answer"``).
    """

    instruction: str
    response_format: Mapping[str, object] | None
    contact_id: str
    purpose: str

    def validate(self) -> "PhaseMaterial":
        for field_name in ("instruction", "contact_id", "purpose"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise RailsError(f"PhaseMaterial.{field_name} must be a non-empty string")
        if self.response_format is not None and not isinstance(self.response_format, Mapping):
            raise RailsError("PhaseMaterial.response_format must be a mapping or None")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "instruction": self.instruction,
            "response_format": (
                dict(self.response_format) if self.response_format is not None else None
            ),
            "contact_id": self.contact_id,
            "purpose": self.purpose,
            "phase_material_version": PHASE_MATERIAL_VERSION,
        }

    def content_hash(self) -> str:
        """SHA-256 over ``json.dumps(..., sort_keys=True)``'s canonical
        bytes (``rails.hashing.content_hash``, the one place this study
        canonicalizes JSON for hashing -- reused here rather than a second,
        independent ``json.dumps`` call)."""

        return content_hash(self.validate().as_json())


__all__ = ["PHASE_MATERIAL_VERSION", "PhaseMaterial"]
