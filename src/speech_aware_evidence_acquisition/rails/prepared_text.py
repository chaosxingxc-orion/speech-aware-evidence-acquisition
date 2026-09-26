"""Explicit text-only input for registered, scoreless TRAIN artifact stages.

The original speech identity remains a custody anchor, not a fresh observation.
Prepared contexts are verified by FlightRuntime before entering the shared runner.
"""

from collections.abc import Mapping

PREPARED_TEXT_ARM = "prepared-context-text"
PREPARED_TEXT_SCHEMA = "saea-prepared-text-v1"
PREPARED_TEXT_INSTRUCTION = (
    "Analyze only the registered prepared context and follow the current phase "
    "instruction. Produce the requested artifact; do not answer the original "
    "spoken task. No fresh speech or task knowledge is supplied."
)


def validate_prepared_text_payload(payload: Mapping[str, object]) -> None:
    """Refuse extra modalities, fresh supply or an unbound history shape."""
    from ..e0.d2_leakage import ARM_VISIBLE_FIELDS

    if set(payload) != set(ARM_VISIBLE_FIELDS[PREPARED_TEXT_ARM]):
        raise ValueError("prepared text payload has undeclared fields")
    if payload.get("prepared_text") != PREPARED_TEXT_SCHEMA:
        raise ValueError("prepared text schema is invalid")
    if payload.get("task_instruction") != PREPARED_TEXT_INSTRUCTION:
        raise ValueError("prepared text requires its fixed input contract")
    history = payload.get("history")
    if not isinstance(history, list) or len(history) != 2:
        raise ValueError("prepared text requires one prepared state and one control")
    state, control = history
    if (
        not isinstance(state, Mapping) or not isinstance(control, Mapping)
        or state.get("role") != "agent_state"
        or state.get("state_kind") != "prepared-training-feedback"
        or control.get("role") != "control"
    ):
        raise ValueError("prepared text requires one prepared state and one control")
