"""Canonical TRAIN-derived SLURP contracts for model-selected candidates.

The provider exposes observed intent/slot profiles and request-relative
contrasts. It supplies no filler values, reference sentences, current-sample
gold, or mandatory-slot claims. Its canonical source is suitable for a
disjoint evaluation lookup only when the surrounding admission establishes
the required construction/evaluation split boundary; a TRAIN-derived catalog
is not automatically valid for TRAIN reward-fold use.

Construction is intentionally separate from native dispatch. The SLURP
adapter builds this immutable catalog lazily only when the optional provider
hook is requested during configured preparation. A caller may construct a
fold-safe catalog by excluding canonical TRAIN utterance IDs; the exclusion
set and retained source identity are then part of the catalog hash.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from ..data.slurp import SlurpIntentSlotSchema, load_slurp_intent_slot_schema
from .candidate_contract_lookup import (
    CandidateContractEvidence,
    CandidateContractLookupError,
    CandidateContractLookupResult,
    CandidateContractRequest,
    canonical_sha256,
)

PROVIDER_SCHEMA = "saea-slurp-candidate-contract-catalog-v1"
PROJECTION_VERSION = "saea-slurp-candidate-contract-projection-v1"
_SCHEMA_TYPE = "observed TRAIN string slot"


@dataclass(frozen=True)
class SlurpObservedSlotType:
    """One retained TRAIN mention profile without any example filler."""

    name: str
    count: int
    share: float

    def as_json(self) -> dict[str, object]:
        return {"name": self.name, "count": self.count, "share": self.share}


@dataclass(frozen=True)
class SlurpCandidateProfile:
    """One legal intent's filler-free observed TRAIN profile."""

    candidate_id: str
    utterances: int
    slot_mentions: int
    types: tuple[SlurpObservedSlotType, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "utterances": self.utterances,
            "slot_mentions": self.slot_mentions,
            "types": [item.as_json() for item in self.types],
        }


def _plural(count: int, singular: str) -> str:
    return singular if count == 1 else f"{singular}s"


def _names(names: tuple[str, ...]) -> str:
    return ", ".join(names) if names else "none"


def _comparative_contrast(
    profile: SlurpCandidateProfile,
    alternatives: tuple[SlurpCandidateProfile, ...],
) -> str:
    prefix = (
        f"Observed TRAIN profile: {profile.utterances} "
        f"{_plural(profile.utterances, 'utterance')}, {profile.slot_mentions} "
        f"{_plural(profile.slot_mentions, 'slot mention')}."
    )
    if not alternatives:
        return (
            f"{prefix} No alternative was requested, so this lookup makes no "
            "candidate-relative distinction. These are observed associations, "
            "not required or forbidden fields."
        )
    other_types = {
        item.name for alternative in alternatives for item in alternative.types
    }
    own = tuple(item.name for item in profile.types)
    shared = tuple(name for name in own if name in other_types)
    candidate_only = tuple(name for name in own if name not in other_types)
    return (
        f"{prefix} Compared with the requested alternatives, shared observed "
        f"slot types: {_names(shared)}; observed only for this candidate: "
        f"{_names(candidate_only)}. These are observed associations, not "
        "required or forbidden fields."
    )


@dataclass(frozen=True)
class SlurpCandidateContractProvider:
    """Immutable canonical catalog with request-relative lookup projection."""

    profiles: tuple[SlurpCandidateProfile, ...]
    source_sha256: str
    _source_document_json: str
    _by_id: Mapping[str, SlurpCandidateProfile]

    @property
    def source_document(self) -> Mapping[str, object]:
        """A detached JSON-safe copy of the immutable source projection."""

        return json.loads(self._source_document_json)

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        """The complete ordered legal ID inventory for pre-invocation checks."""

        return tuple(profile.candidate_id for profile in self.profiles)

    def lookup(
        self, candidate_ids: tuple[str, ...]
    ) -> CandidateContractLookupResult:
        request = CandidateContractRequest.from_ids(candidate_ids)
        unknown = tuple(
            candidate_id
            for candidate_id in request.candidate_ids
            if candidate_id not in self._by_id
        )
        if unknown:
            raise CandidateContractLookupError(
                f"unknown candidate IDs in canonical SLURP catalog: {list(unknown)}"
            )
        requested = tuple(self._by_id[candidate_id] for candidate_id in request.candidate_ids)
        evidence: list[CandidateContractEvidence] = []
        for profile in requested:
            alternatives = tuple(
                item for item in requested if item.candidate_id != profile.candidate_id
            )
            evidence.append(
                CandidateContractEvidence(
                    candidate_id=profile.candidate_id,
                    operation=profile.candidate_id,
                    schema=tuple((item.name, _SCHEMA_TYPE) for item in profile.types),
                    contrast=_comparative_contrast(profile, alternatives),
                ).validate()
            )
        return CandidateContractLookupResult(
            request=request,
            source_sha256=self.source_sha256,
            candidates=tuple(evidence),
        ).validate()


def _profiles(schema: SlurpIntentSlotSchema) -> tuple[SlurpCandidateProfile, ...]:
    profiles: list[SlurpCandidateProfile] = []
    for candidate_id in schema.intent_ids:
        source = schema.intents[candidate_id]
        profiles.append(
            SlurpCandidateProfile(
                candidate_id=candidate_id,
                utterances=source.n,
                slot_mentions=source.mentions,
                types=tuple(
                    SlurpObservedSlotType(name=name, count=count, share=share)
                    for name, count, share in source.types
                ),
            )
        )
    return tuple(profiles)


def build_slurp_candidate_contract_provider(
    lock: Mapping[str, object],
    root: Path,
    *,
    excluded_train_utterance_ids: Sequence[str] | None = None,
) -> SlurpCandidateContractProvider:
    """Build from retained TRAIN utterances while keeping all legal labels."""

    schema = load_slurp_intent_slot_schema(
        lock,
        root,
        examples_per_type=0,
        excluded_train_utterance_ids=excluded_train_utterance_ids,
    )
    profiles = _profiles(schema)
    source_document: dict[str, object] = {
        "schema": PROVIDER_SCHEMA,
        "projection_version": PROJECTION_VERSION,
        "source_schema_id": schema.schema_id,
        "source_schema_sha256": schema.content_hash(),
        "source_split": schema.source_split,
        "source_identity_sha256": schema.source_identity_hash,
        "source_utterance_count": schema.utterance_count,
        "retention": {
            "min_share": schema.min_share,
            "examples_per_type": schema.examples_per_type,
        },
        "profiles": [profile.as_json() for profile in profiles],
    }
    if schema.excluded_train_utterance_ids:
        source_document["construction_exclusions"] = {
            "train_utterance_ids": list(schema.excluded_train_utterance_ids),
        }
    by_id = MappingProxyType(
        {profile.candidate_id: profile for profile in profiles}
    )
    return SlurpCandidateContractProvider(
        profiles=profiles,
        source_sha256=canonical_sha256(source_document),
        _source_document_json=json.dumps(
            source_document,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ),
        _by_id=by_id,
    )


__all__ = [
    "PROJECTION_VERSION",
    "PROVIDER_SCHEMA",
    "SlurpCandidateContractProvider",
    "SlurpCandidateProfile",
    "SlurpObservedSlotType",
    "build_slurp_candidate_contract_provider",
]
