"""Frozen flight mechanics for full Audio2Tool executable-ground qualification."""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from threading import Lock
from typing import Mapping, Sequence

from ..adapters.audio2tool import Audio2ToolAdapter, Audio2ToolSample
from ..adapters.audio2tool import render_audio2tool_instruction


SPLIT_ID = "A2T-GROUND-QUAL-104"
REGISTRY_DIRECT = "M0_REGISTRY_DIRECT"
FULL_EXECUTABLE_GROUND = "G1_FULL_EXECUTABLE_GROUND"
RESEND_SELECTION_NAMESPACE = "a2t-executable-ground-qualification-resend-v1"
EXPECTED_TIERS = 8
ROWS_PER_TIER = 13
RESENDS_PER_TIER = 2


class GroundQualificationFlightError(RuntimeError):
    """A frozen identity, knowledge, or request invariant drifted."""


def _rank(sample_id: str) -> str:
    return hashlib.sha256(
        f"{RESEND_SELECTION_NAMESPACE}\0{sample_id}".encode("utf-8")
    ).hexdigest()


def select_resend_ids(sample_tiers: Mapping[str, str]) -> tuple[str, ...]:
    """Select two stable identities per tier without response information."""

    if not isinstance(sample_tiers, Mapping) or not sample_tiers:
        raise GroundQualificationFlightError("resend selection requires sample tiers")
    by_tier: dict[str, list[str]] = {}
    for sample_id, tier in sample_tiers.items():
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(tier, str)
            or not tier
        ):
            raise GroundQualificationFlightError(
                "sample and tier identities must be non-empty text"
            )
        by_tier.setdefault(tier, []).append(sample_id)
    if len(by_tier) != EXPECTED_TIERS or any(
        len(sample_ids) != ROWS_PER_TIER for sample_ids in by_tier.values()
    ):
        raise GroundQualificationFlightError(
            "resend selection requires eight tiers with thirteen rows each"
        )
    selected: list[str] = []
    for tier in sorted(by_tier):
        ranked = sorted(by_tier[tier], key=lambda value: (_rank(value), value))
        selected.extend(ranked[:RESENDS_PER_TIER])
    return tuple(selected)


def render_qualification_contract(
    *, mode: str, registry_contract: str, handbook: str
) -> str:
    """Return exactly one of the two preregistered knowledge surfaces."""

    if mode not in {REGISTRY_DIRECT, FULL_EXECUTABLE_GROUND}:
        raise GroundQualificationFlightError(f"unknown qualification mode {mode!r}")
    if not isinstance(registry_contract, str) or not registry_contract.strip():
        raise GroundQualificationFlightError("registry contract must be non-empty text")
    if not isinstance(handbook, str) or not handbook.strip():
        raise GroundQualificationFlightError("handbook must be non-empty text")
    if not handbook.isascii():
        raise GroundQualificationFlightError("handbook must be ASCII English")
    return (
        render_audio2tool_instruction(registry_contract)
        if mode == REGISTRY_DIRECT
        else handbook
    )


class GroundQualificationAdapter(Audio2ToolAdapter):
    """Receipt-filtered, scoring-deferred adapter for one frozen knowledge arm."""

    def __init__(
        self,
        lock: Mapping[str, object],
        root: Path,
        *,
        repo_root: Path,
        receipt_items: Sequence[Mapping[str, object]],
        mode: str,
        handbook: str,
    ) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        by_id: dict[str, Mapping[str, object]] = {}
        for item in receipt_items:
            sample_id = item.get("sample_id")
            if not isinstance(sample_id, str) or not sample_id or sample_id in by_id:
                raise GroundQualificationFlightError(
                    "receipt sample ids must be unique non-empty strings"
                )
            by_id[sample_id] = item
        if not by_id:
            raise GroundQualificationFlightError("receipt cannot be empty")
        self._mode = mode
        self._handbook = handbook
        self._by_id = by_id
        self._cache: tuple[Audio2ToolSample, ...] | None = None

    def load_split(self, split_id: str) -> tuple[Audio2ToolSample, ...]:
        if split_id != SPLIT_ID:
            raise GroundQualificationFlightError(
                f"adapter serves only {SPLIT_ID!r}, not {split_id!r}"
            )
        if self._cache is None:
            exposed = super().load_split("discovery")
            picked = tuple(
                sorted(
                    (sample for sample in exposed if sample.sample_id in self._by_id),
                    key=lambda sample: sample.sample_id,
                )
            )
            if {sample.sample_id for sample in picked} != set(self._by_id):
                raise GroundQualificationFlightError(
                    "carrier does not resolve the exact receipt identities"
                )
            for sample in picked:
                item = self._by_id[sample.sample_id]
                if (
                    sample.media_relpath != item.get("media_relpath")
                    or sample.audio_ref.sha256 != item.get("audio_sha256")
                ):
                    raise GroundQualificationFlightError(
                        f"media identity drift for {sample.sample_id!r}"
                    )
            self._cache = picked
        return self._cache

    def _contract(self) -> str:
        registry = super().build_task_contract(None, None)  # type: ignore[arg-type]
        return render_qualification_contract(
            mode=self._mode,
            registry_contract=registry,
            handbook=self._handbook,
        )

    def build_task_contract(self, sample: Audio2ToolSample, obs: object) -> str:
        del sample, obs
        return self._contract()

    def assemble_prompt(
        self, sample: Audio2ToolSample, supply: object
    ) -> tuple[Mapping[str, object], ...]:
        if supply is not None:
            raise GroundQualificationFlightError(
                "qualification arms reject a separate supply channel"
            )
        return (
            {"role": "system", "content": self._contract()},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "media_relpath": sample.media_relpath}
                ],
            },
        )

    def score(self, sample: Audio2ToolSample, response: str) -> Mapping[str, object]:
        del sample, response
        return {"scoring_deferred": True}


@dataclass(frozen=True)
class GroundDirectResult:
    sample_id: str
    final_response_text: str


@dataclass(frozen=True)
class GroundDirectSummary:
    results: tuple[GroundDirectResult, ...]
    direct_single_call: bool = True


def run_direct_qualification_phase(
    *,
    adapter: object,
    core_client: object,
    split_id: str,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    slot_count: int,
    decoding_params: Mapping[str, object],
    key_representation_id: str,
    matcher_policy_id: str,
    slot_by_sample: Mapping[str, int] | None = None,
) -> GroundDirectSummary:
    """Run one frozen direct call per sample over an exact receipt subset."""

    if isinstance(slot_count, bool) or not isinstance(slot_count, int) or slot_count < 1:
        raise GroundQualificationFlightError("slot_count must be a positive integer")
    if not isinstance(decoding_params, Mapping) or "id_slot" in decoding_params:
        raise GroundQualificationFlightError("decoding params must omit id_slot")
    if not key_representation_id or not matcher_policy_id:
        raise GroundQualificationFlightError("request provenance ids must be non-empty")
    samples = tuple(adapter.load_split(split_id))
    sample_ids = [sample.sample_id for sample in samples]
    if (
        not samples
        or len(set(sample_ids)) != len(sample_ids)
        or set(sample_ids) != set(speech_packet_bindings)
    ):
        raise GroundQualificationFlightError(
            "sample and packet-binding identities must match uniquely"
        )
    registered_slots = dict(slot_by_sample or {})
    if registered_slots and (
        set(registered_slots) != set(sample_ids)
        or any(
            isinstance(slot, bool)
            or not isinstance(slot, int)
            or not 0 <= slot < slot_count
            for slot in registered_slots.values()
        )
    ):
        raise GroundQualificationFlightError(
            "registered source slots must cover every sample inside slot geometry"
        )
    slots: Queue[int] = Queue()
    for slot in range(slot_count):
        slots.put(slot)
    slot_locks = {slot: Lock() for slot in range(slot_count)}

    def invoke(sample: object) -> GroundDirectResult:
        packet = speech_packet_bindings[sample.sample_id]
        packet_id = packet.get("packet_id")
        packet_sha256 = packet.get("sha256")
        if (
            not isinstance(packet_id, str)
            or not packet_id
            or not isinstance(packet_sha256, str)
            or len(packet_sha256) != 64
        ):
            raise GroundQualificationFlightError(
                f"malformed packet binding for {sample.sample_id!r}"
            )
        base = tuple(adapter.assemble_prompt(sample, None))
        messages = (
            dict(base[0]),
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_speech_features",
                        "speech_features": {
                            "packet_id": packet_id,
                            "sha256": packet_sha256,
                            "role": "query",
                        },
                    }
                ],
            },
        )
        slot = (
            registered_slots[sample.sample_id]
            if registered_slots
            else slots.get()
        )
        lock = slot_locks[slot]
        try:
            lock.acquire()
            decoding = dict(decoding_params)
            decoding["id_slot"] = slot
            response = core_client.complete(
                messages,
                decoding_params=decoding,
                speech_feature_sample_id=sample.sample_id,
                key_representation_id=key_representation_id,
                matcher_policy_id=matcher_policy_id,
            )
        finally:
            lock.release()
            if not registered_slots:
                slots.put(slot)
        if not isinstance(response, str) or not response:
            raise GroundQualificationFlightError(
                f"model returned no response for {sample.sample_id!r}"
            )
        return GroundDirectResult(sample.sample_id, response)

    with ThreadPoolExecutor(max_workers=slot_count) as executor:
        results = tuple(executor.map(invoke, samples))
    return GroundDirectSummary(
        results=tuple(sorted(results, key=lambda result: result.sample_id))
    )


__all__ = [
    "FULL_EXECUTABLE_GROUND",
    "REGISTRY_DIRECT",
    "SPLIT_ID",
    "GroundDirectResult",
    "GroundDirectSummary",
    "GroundQualificationAdapter",
    "GroundQualificationFlightError",
    "render_qualification_contract",
    "run_direct_qualification_phase",
    "select_resend_ids",
]
