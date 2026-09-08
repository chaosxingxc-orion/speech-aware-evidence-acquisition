"""Pure identities and selector-state bindings for the SELECT/FILL factorial.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``bind_factorial_predecessors`` is catalog id
``saea-tool-a2t-select-fill-factorial-binding-v1`` on the ``ORG`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from .a2t_stage_state import SELECT_STAGE, StageStateEnvelope


ROUTING_SELECT = "R0_ROUTING_ONLY"
INTERFACE_SELECT = "R1_INTERFACE_SHAPE"
DEFAULT_FILL = "F0_DEFAULT_COMPLETION"
SPARSE_FILL = "F1_EVIDENCE_SPARSE"

_SELECT_GROUNDS = frozenset({ROUTING_SELECT, INTERFACE_SELECT})
_FILL_POLICIES = frozenset({DEFAULT_FILL, SPARSE_FILL})
_IDENTIFIER = re.compile(r"[A-Z][A-Z0-9_]*", flags=re.ASCII)
_SHA256 = re.compile(r"[0-9a-f]{64}", flags=re.ASCII)


class FactorialBindingError(ValueError):
    """The prospective cell identity or selector lineage is not exact."""


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
        raise FactorialBindingError("factorial binding must be canonical JSON") from error


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class FactorialCell:
    """One prospectively named SELECT-ground by FILL-policy cell."""

    cell_id: str
    select_ground: str
    fill_policy: str
    execution_id: str
    manifest_role: str

    def __post_init__(self) -> None:
        if self.cell_id not in {"Y00", "Y01", "Y10", "Y11"}:
            raise FactorialBindingError("factorial cell id is unknown")
        if self.select_ground not in _SELECT_GROUNDS:
            raise FactorialBindingError("factorial SELECT ground is unknown")
        if self.fill_policy not in _FILL_POLICIES:
            raise FactorialBindingError("factorial FILL policy is unknown")
        if (
            _IDENTIFIER.fullmatch(self.execution_id) is None
            or _IDENTIFIER.fullmatch(self.manifest_role) is None
        ):
            raise FactorialBindingError(
                "factorial execution and manifest identities must be ASCII identifiers"
            )


FACTORIAL_CELLS = (
    FactorialCell(
        "Y00",
        ROUTING_SELECT,
        DEFAULT_FILL,
        "FILL_R0_F0",
        "SELECT_ROUTING_FILL_DEFAULT",
    ),
    FactorialCell(
        "Y01",
        ROUTING_SELECT,
        SPARSE_FILL,
        "FILL_R0_F1",
        "SELECT_ROUTING_FILL_SPARSE",
    ),
    FactorialCell(
        "Y10",
        INTERFACE_SELECT,
        DEFAULT_FILL,
        "FILL_R1_F0",
        "SELECT_INTERFACE_FILL_DEFAULT",
    ),
    FactorialCell(
        "Y11",
        INTERFACE_SELECT,
        SPARSE_FILL,
        "FILL_R1_F1",
        "SELECT_INTERFACE_FILL_SPARSE",
    ),
)


@dataclass(frozen=True)
class FactorialPredecessorBinding:
    """Hash-only proof that one FILL cell reuses one sealed SELECT map."""

    cell_id: str
    select_ground: str
    fill_policy: str
    selector_state_map_sha256: str
    sample_ids: tuple[str, ...]
    selector_envelope_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.cell_id not in {cell.cell_id for cell in FACTORIAL_CELLS}:
            raise FactorialBindingError("predecessor binding cell is unknown")
        if self.select_ground not in _SELECT_GROUNDS:
            raise FactorialBindingError("predecessor SELECT ground is unknown")
        if self.fill_policy not in _FILL_POLICIES:
            raise FactorialBindingError("predecessor FILL policy is unknown")
        if _SHA256.fullmatch(self.selector_state_map_sha256) is None:
            raise FactorialBindingError("selector state map hash is malformed")
        if (
            not self.sample_ids
            or len(self.sample_ids) != len(self.selector_envelope_sha256s)
            or len(self.sample_ids) != len(set(self.sample_ids))
            or any(not item or not item.isascii() for item in self.sample_ids)
            or any(
                _SHA256.fullmatch(value) is None
                for value in self.selector_envelope_sha256s
            )
        ):
            raise FactorialBindingError("selector predecessor rows are malformed")
        rows = [
            {"sample_id": sample_id, "envelope_sha256": envelope_sha256}
            for sample_id, envelope_sha256 in zip(
                self.sample_ids,
                self.selector_envelope_sha256s,
                strict=True,
            )
        ]
        if _hash(rows) != self.selector_state_map_sha256:
            raise FactorialBindingError("selector state map hash does not match rows")


def bind_factorial_predecessors(
    selector_states: Mapping[str, Mapping[str, StageStateEnvelope]],
    *,
    sample_ids: Sequence[str],
    expected_ground_sha256: Mapping[str, Mapping[str, str]],
    split_identity_sha256: str,
    expected_row_count: int = 128,
) -> tuple[FactorialPredecessorBinding, ...]:
    """Validate both SELECT barriers and bind four FILL cells without reruns."""

    if (
        isinstance(expected_row_count, bool)
        or not isinstance(expected_row_count, int)
        or expected_row_count <= 0
    ):
        raise FactorialBindingError("expected row count must be a positive integer")
    if not isinstance(sample_ids, Sequence) or isinstance(sample_ids, (str, bytes)):
        raise FactorialBindingError("sample ids must be a sequence")
    ordered_ids = tuple(sample_ids)
    if (
        len(ordered_ids) != expected_row_count
        or len(ordered_ids) != len(set(ordered_ids))
        or any(
            not isinstance(sample_id, str)
            or not sample_id
            or not sample_id.isascii()
            for sample_id in ordered_ids
        )
    ):
        raise FactorialBindingError(
            f"sample ids must contain exactly {expected_row_count} unique ASCII values"
        )
    if _SHA256.fullmatch(split_identity_sha256) is None:
        raise FactorialBindingError("split identity hash is malformed")
    if set(selector_states) != _SELECT_GROUNDS:
        raise FactorialBindingError("selector states must cover both SELECT grounds")
    if set(expected_ground_sha256) != _SELECT_GROUNDS:
        raise FactorialBindingError("expected ground must cover both SELECT grounds")

    state_hashes: dict[str, tuple[str, ...]] = {}
    for select_ground in (ROUTING_SELECT, INTERFACE_SELECT):
        states = selector_states[select_ground]
        expected_ground = expected_ground_sha256[select_ground]
        if set(states) != set(ordered_ids) or set(expected_ground) != set(ordered_ids):
            raise FactorialBindingError(
                "each SELECT ground must cover the sample roster exactly"
            )
        hashes: list[str] = []
        for sample_id in ordered_ids:
            state = states[sample_id]
            ground_hash = expected_ground[sample_id]
            if not isinstance(state, StageStateEnvelope) or state.stage != SELECT_STAGE:
                raise FactorialBindingError("selector state is not a sealed SELECT envelope")
            if (
                state.sample_identity_sha256
                != hashlib.sha256(sample_id.encode("ascii")).hexdigest()
                or state.split_identity_sha256 != split_identity_sha256
                or state.predecessor_envelope_sha256 is not None
            ):
                raise FactorialBindingError("selector state identity lineage drift")
            if _SHA256.fullmatch(ground_hash) is None or state.ground_sha256 != ground_hash:
                raise FactorialBindingError("selector ground lineage drift")
            hashes.append(state.envelope_sha256)
        state_hashes[select_ground] = tuple(hashes)

    routing_states = selector_states[ROUTING_SELECT]
    interface_states = selector_states[INTERFACE_SELECT]
    for sample_id in ordered_ids:
        routing = routing_states[sample_id]
        interface = interface_states[sample_id]
        if (
            routing.speech_packet_sha256 != interface.speech_packet_sha256
            or routing.observation_state_sha256 != interface.observation_state_sha256
            or routing.observation_source_response_sha256
            != interface.observation_source_response_sha256
            or routing.candidate_set_sha256 != interface.candidate_set_sha256
            or routing.response_schema_sha256 != interface.response_schema_sha256
        ):
            raise FactorialBindingError(
                "SELECT grounds do not share speech, OBS, candidates, and schema"
            )
        if routing.ground_sha256 == interface.ground_sha256:
            raise FactorialBindingError("SELECT treatment ground did not change")

    bindings: list[FactorialPredecessorBinding] = []
    for cell in FACTORIAL_CELLS:
        hashes = state_hashes[cell.select_ground]
        rows = [
            {"sample_id": sample_id, "envelope_sha256": envelope_sha256}
            for sample_id, envelope_sha256 in zip(ordered_ids, hashes, strict=True)
        ]
        bindings.append(
            FactorialPredecessorBinding(
                cell_id=cell.cell_id,
                select_ground=cell.select_ground,
                fill_policy=cell.fill_policy,
                selector_state_map_sha256=_hash(rows),
                sample_ids=ordered_ids,
                selector_envelope_sha256s=hashes,
            )
        )
    return tuple(bindings)


__all__ = [
    "DEFAULT_FILL",
    "FACTORIAL_CELLS",
    "INTERFACE_SELECT",
    "ROUTING_SELECT",
    "SPARSE_FILL",
    "FactorialBindingError",
    "FactorialCell",
    "FactorialPredecessorBinding",
    "bind_factorial_predecessors",
]
