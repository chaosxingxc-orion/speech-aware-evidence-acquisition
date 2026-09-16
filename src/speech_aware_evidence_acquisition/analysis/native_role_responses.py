"""Select exact post-seal native role responses from verified episode sources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from .native_episode_diagnostics import (
    NativeEpisodeDiagnosticError,
    join_native_role_contact_response,
)
from .native_episode_source import VerifiedNativeEpisodeSource


class NativeRoleResponseSelectionError(ValueError):
    """A requested role response lacks exact verified receipt/trace custody."""


@dataclass(frozen=True)
class NativeRoleResponseSelection:
    """One role execution's final contact, or an explicit unavailable status."""

    sample_id: str
    role_id: str
    status: Literal["completed", "finite", "missing"]
    visit_index: int | None
    contact_index: int | None
    response_text: str | None
    agent_contact_id: str | None
    request_id: str | None
    request_sha256: str | None
    response_sha256: str | None
    response_text_sha256: str | None

    def source_json(self) -> dict[str, object]:
        """Return custody fields without copying response text into a sidecar."""
        return {
            "status": self.status,
            "role_id": self.role_id,
            "visit_index": self.visit_index,
            "contact_index": self.contact_index,
            "agent_contact_id": self.agent_contact_id,
            "request_id": self.request_id,
            "request_sha256": self.request_sha256,
            "response_sha256": self.response_sha256,
            "response_text_sha256": self.response_text_sha256,
        }


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise NativeRoleResponseSelectionError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise NativeRoleResponseSelectionError(f"{label} must be an ordered sequence")
    return value


def _missing(sample_id: str, role_id: str) -> NativeRoleResponseSelection:
    return NativeRoleResponseSelection(
        sample_id=sample_id,
        role_id=role_id,
        status="missing",
        visit_index=None,
        contact_index=None,
        response_text=None,
        agent_contact_id=None,
        request_id=None,
        request_sha256=None,
        response_sha256=None,
        response_text_sha256=None,
    )


def select_verified_native_role_response(
    source: VerifiedNativeEpisodeSource,
    *,
    sample_id: str,
    role_id: str,
    visit_index: int | None = None,
) -> NativeRoleResponseSelection:
    """Select a completed role visit or the latest finite interruption.

    ``visit_index`` is an absolute index into ``role_visits``. When it is
    ``None``, the latest matching actual occurrence is selected; an
    ``interrupted_role`` follows every completed visit and returns ``finite``.
    Only ``completed`` responses are suitable for task-level parsing.
    """
    if not isinstance(source, VerifiedNativeEpisodeSource):
        raise NativeRoleResponseSelectionError(
            "source must be a VerifiedNativeEpisodeSource from the shared loader"
        )
    if (
        not isinstance(sample_id, str)
        or not sample_id
        or sample_id not in source.sample_ids
        or sample_id not in source.phase_results
        or sample_id not in source.output_rows
    ):
        raise NativeRoleResponseSelectionError("sample_id is outside the verified source")
    if not isinstance(role_id, str) or not role_id:
        raise NativeRoleResponseSelectionError("role_id must be nonempty text")
    if visit_index is not None and (
        isinstance(visit_index, bool) or not isinstance(visit_index, int)
    ):
        raise NativeRoleResponseSelectionError("visit_index must be an integer or None")

    phase_result = _mapping(
        source.phase_results[sample_id], f"phase result {sample_id!r}"
    )
    episode = _mapping(
        phase_result.get("native_episode_receipt"),
        f"native episode receipt {sample_id!r}",
    )
    visits = _sequence(episode.get("role_visits"), f"native role visits {sample_id!r}")
    interrupted = episode.get("interrupted_role")
    selected: Mapping[str, object] | None = None
    selected_index: int | None = None
    status: Literal["completed", "finite", "missing"] = "missing"
    if visit_index is not None:
        if not 0 <= visit_index < len(visits):
            raise NativeRoleResponseSelectionError("visit_index is outside role_visits")
        candidate = _mapping(visits[visit_index], f"role visit {visit_index}")
        if candidate.get("role_id") != role_id:
            raise NativeRoleResponseSelectionError(
                f"role visit {visit_index} is not role {role_id!r}"
            )
        selected, selected_index, status = candidate, visit_index, "completed"
    else:
        completed = [
            (index, _mapping(visit, f"role visit {index}"))
            for index, visit in enumerate(visits)
            if isinstance(visit, Mapping) and visit.get("role_id") == role_id
        ]
        if isinstance(interrupted, Mapping) and interrupted.get("role_id") == role_id:
            selected, selected_index, status = interrupted, None, "finite"
        elif completed:
            selected_index, selected = completed[-1]
            status = "completed"
    if selected is None:
        return _missing(sample_id, role_id)

    execution = _mapping(selected.get("execution_receipt"), "role execution receipt")
    contacts = _sequence(execution.get("contacts"), "role execution contacts")
    final_contact = execution.get("final_contact")
    if not contacts or not isinstance(final_contact, Mapping) or final_contact != contacts[-1]:
        raise NativeRoleResponseSelectionError(
            "role execution final contact must equal its last contact"
        )
    joined = []
    try:
        for index, contact in enumerate(contacts):
            joined.append(
                join_native_role_contact_response(
                    sample_id=sample_id,
                    role_id=role_id,
                    contact=contact,
                    trace_records=source.bundle.trace_records,
                    label=f"selected role contact {sample_id!r}[{index}]",
                )
            )
    except NativeEpisodeDiagnosticError as error:
        raise NativeRoleResponseSelectionError(str(error)) from error

    phase_contacts = _sequence(
        phase_result.get("contacts"), f"phase contacts {sample_id!r}"
    )
    for contact, _request, response, _use in joined:
        matching = []
        for raw_phase_contact in phase_contacts:
            phase_contact = _mapping(raw_phase_contact, "phase contact")
            plan = phase_contact.get("plan")
            if isinstance(plan, Mapping) and plan.get("contact_id") == contact["agent_contact_id"]:
                matching.append(phase_contact)
        if len(matching) != 1 or (
            matching[0].get("response_sha256")
            != response.get("response_text_sha256")
        ):
            raise NativeRoleResponseSelectionError(
                "selected role response differs from serialized phase contacts"
            )

    contact, _request, response, _use = joined[-1]
    response_text = response.get("text")
    if not isinstance(response_text, str):  # guarded by the shared join
        raise NativeRoleResponseSelectionError("selected role response text is unavailable")
    return NativeRoleResponseSelection(
        sample_id=sample_id,
        role_id=role_id,
        status=status,
        visit_index=selected_index,
        contact_index=len(joined) - 1,
        response_text=response_text,
        agent_contact_id=contact["agent_contact_id"],
        request_id=contact["request_id"],
        request_sha256=contact["request_sha256"],
        response_sha256=contact["response_sha256"],
        response_text_sha256=contact["response_text_sha256"],
    )


__all__ = [
    "NativeRoleResponseSelection",
    "NativeRoleResponseSelectionError",
    "select_verified_native_role_response",
]
