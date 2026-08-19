"""P-A2T abstention-asymmetry 2x2 flight orchestration -- REGISTERED probe
(``bounded-discovery-probe``): ``docs/readiness/
2026-08-19-a2t-abst-preregistration-REGISTERED.md`` (``SAEA-PROBE-a2t-abst-44``).

Four cells (``TP-A``/``TP-S``/``TW-A``/``TW-S``) over a seeded n=11 draw from
the frozen A2T 400's own already-exposed 120-id headroom list -- a within-
carrier 2x2 crossing ACTION-space presence (full registry vs. the sample's
own correct tool structurally REMOVED) against EVIDENCE presence (real audio
vs. a matched-duration silence swap):

- ``TP-A`` -- real audio, full 152-row registry (A0's own prompt form,
  reused UNCHANGED via ``rails.adapters.audio2tool.Audio2ToolAdapter.
  assemble_prompt(sample, None)``).
- ``TP-S`` -- silence swap (same duration), full registry.
- ``TW-A`` -- real audio, registry with the sample's own correct tool
  REMOVED (the tool-removal render, see :func:`render_registry_minus_tools`).
- ``TW-S`` -- silence swap, correct tool removed.

TOOL-REMOVAL RENDER (prereg section 1: "S4's structural withholding, minus
the derangement"): ``rails.probes.a2t_s2_flight``'s own S4 arm withholds a
sample's correct tool from what is supplied AND substitutes a seeded
DERANGED wrong tool's row in its place -- two separable ingredients. TW's
own registry keeps ONLY the first ("structural withholding": the correct
tool is absent) and drops the second (no derangement, no substitute row):
:func:`render_registry_minus_tools` renders the FULL 152-row registry with
exactly the sample's own correct tool row(s) removed -- every OTHER tool
stays present, unlike S4's own single-row narrowed roster. The "correct
tool" itself is never re-derived a second way: it is
``rails.probes.a2t_s2_flight.derive_a0_selected_tools``'s own output over
this probe's own 11-id draw (self-supplied, deployment-legal, gold-free --
on headroom ids, A0's own selection IS the correct tool by that set's own
defining criterion), reused directly, never gold.

SILENCE-SWAP WIRING (prereg section 4: "silence swaps constructed by the
established silence-swap machinery"): mirrors
``rails.probes.pslu_flight``'s own documented split exactly -- the ACTUAL
silent-audio slice is NOT generated or registered here (that is
``rails.silence_swap.build_silence_swap_slice`` + ``FrozenCoreClient.
register_slice``'s job, since only a REAL ``FrozenCoreClient`` has a slice
registry at all; ``MockCoreClient`` does not). This module's own job is
narrower and generic over ANY ``CoreClient``: given a caller-supplied
``sample_id -> already-registered silent media_relpath`` mapping (REQUIRED
for every one of this probe's own 11 sample ids -- unlike P-SLU's own
OPTIONAL subset, every one of the 4 cells here needs its own silence
counterpart), :func:`_swap_audio_media_relpath` (re-implemented locally,
mirrors ``rails.probes.pslu_flight``'s own private helper of the identical
name and shape) swaps the ``input_audio`` content part's ``media_relpath``
for the silent one, keeping the SAME system-prompt/roster text.

RESULT SHAPE REUSE: this module reuses
``rails.probes.a2t_s2_flight.A2tS2ArmResult`` for its own per-request
records -- its ``arm`` field carries this probe's own CELL name
(``TP-A``/``TP-S``/``TW-A``/``TW-S``, never a Stage-2 arm name), and its
``supplied_tool`` field carries the WITHHELD tool label on ``TW-A``/``TW-S``
rows (``None`` on ``TP-A``/``TP-S`` -- nothing is withheld there), a
documented repurposing rather than a new, parallel dataclass (mirrors
``rails.probes.a2t_pop_flight``'s own identical reuse for its R0/R1 rows).

Zero live model contact, engineering only: every test in this repository's
own suite for this module drives ``rails.core_client.MockCoreClient``.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..adapters.audio2tool import Audio2ToolAdapter, Audio2ToolSample
from .a2t_s2_flight import (
    DEFAULT_SEED,
    A2tS2ArmResult,
    assemble_roster_prompt,
    derive_a0_selected_tools,
    render_roster_prompt_block,
    result_to_json,
    write_outputs_jsonl,
)

_PROBE_ID = "P-A2T-ABST"

TP_A_CELL = "TP-A"
TP_S_CELL = "TP-S"
TW_A_CELL = "TW-A"
TW_S_CELL = "TW-S"
A2T_ABST_CELLS: tuple[str, ...] = (TP_A_CELL, TP_S_CELL, TW_A_CELL, TW_S_CELL)

ABST_N = 11


class A2tAbstFlightError(RuntimeError):
    """An abstention-asymmetry flight input is malformed, the seeded n=11
    draw cannot be satisfied, the tool-removal render is asked to remove a
    tool absent from the registry, or the flight loop is asked to run over a
    sample set that does not match its own precomputed plan."""


# ---------------------------------------------------------------------------
# Seeded n=11 draw from the frozen A2T 400's headroom list.
# ---------------------------------------------------------------------------


def seeded_abst_draw(
    headroom_ids: Sequence[str], *, seed: int = DEFAULT_SEED, n: int = ABST_N
) -> tuple[str, ...]:
    """Prereg section 1: "seeded (seed 20260807) n=11 from the frozen A2T
    400's headroom list" -- a single, flat seeded draw without replacement
    (no tier-proportional apportionment is named anywhere in this prereg,
    unlike Stage-2's own N0r arm), over ``sorted(set(headroom_ids))`` for
    reproducibility. Deterministic given ``(headroom_ids, seed, n)``."""

    ids = sorted(set(headroom_ids))
    if len(ids) < n:
        raise A2tAbstFlightError(f"seeded_abst_draw needs at least {n} headroom id(s), got {len(ids)}")
    rng = random.Random(seed)
    return tuple(sorted(rng.sample(ids, n)))


# ---------------------------------------------------------------------------
# Tool-removal render: S4's structural withholding, minus the derangement.
# ---------------------------------------------------------------------------


def render_registry_minus_tools(
    registry_rows: Sequence[Mapping[str, str]], remove_tool_names: Sequence[str]
) -> str:
    """The TW cells' own ``{tool_schemas}`` fill (module docstring): the FULL
    registry with exactly ``remove_tool_names`` removed, every other row
    rendered UNCHANGED (byte-identical rendering to the full-registry form,
    reusing ``rails.probes.a2t_s2_flight.render_roster_prompt_block`` --
    never a hand-rolled join). Fail-closed if any name in
    ``remove_tool_names`` is absent from ``registry_rows`` (a defense-in-
    depth check: this should never happen for a genuinely correct A0
    selection, since it is itself drawn from the same registry)."""

    all_names = {row.get("tool_name") for row in registry_rows}
    remove = set(remove_tool_names)
    unknown = remove - all_names
    if unknown:
        raise A2tAbstFlightError(
            f"cannot remove unknown tool name(s) {sorted(unknown)} -- not present in the registry"
        )
    kept = [row for row in registry_rows if row.get("tool_name") not in remove]
    return render_roster_prompt_block(kept)


# ---------------------------------------------------------------------------
# The flight plan: every sample's own correct tool(s) + TW registry text,
# precomputed once and independently auditable/testable before any request
# is ever issued.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tAbstFlightPlan:
    sample_ids: tuple[str, ...]
    correct_tool_names_by_sample: Mapping[str, tuple[str, ...]]
    registry_index: Mapping[str, Mapping[str, str]]
    tw_registry_text_by_sample: Mapping[str, str]


def build_flight_plan(
    sample_ids: Sequence[str],
    correct_tool_names: Mapping[str, tuple[str, ...]],
    registry_rows: Sequence[Mapping[str, str]],
) -> A2tAbstFlightPlan:
    """Resolve every sample's own TW registry text deterministically --
    fail-closed if the registry has a duplicate/missing ``tool_name``, if
    ``correct_tool_names`` does not carry EXACTLY ``sample_ids``, or if any
    named tool is absent from the registry. ``correct_tool_names`` is the
    caller's own already-derived ``rails.probes.a2t_s2_flight.
    derive_a0_selected_tools`` output (module docstring: "the caller
    loads/derives, this module only resolves" split every sibling probe
    module already uses)."""

    registry_index: dict[str, Mapping[str, str]] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not name:
            raise A2tAbstFlightError("registry row is missing tool_name")
        if name in registry_index:
            raise A2tAbstFlightError(f"registry has a duplicate tool_name {name!r}")
        registry_index[name] = row

    ids = tuple(sorted(sample_ids))
    have = set(correct_tool_names)
    want = set(ids)
    if have != want:
        missing = want - have
        extra = have - want
        raise A2tAbstFlightError(
            f"correct_tool_names does not match sample_ids exactly "
            f"(missing={sorted(missing)[:5]}, extra={sorted(extra)[:5]})"
        )

    tw_text_by_sample: dict[str, str] = {}
    for sample_id in ids:
        names = correct_tool_names[sample_id]
        if not names:
            raise A2tAbstFlightError(f"sample {sample_id!r} carries no correct tool name(s)")
        unknown = set(names) - registry_index.keys()
        if unknown:
            raise A2tAbstFlightError(
                f"sample {sample_id!r} names tool(s) {sorted(unknown)} not present in the registry"
            )
        tw_text_by_sample[sample_id] = render_registry_minus_tools(registry_rows, names)

    return A2tAbstFlightPlan(
        sample_ids=ids,
        correct_tool_names_by_sample=dict(correct_tool_names),
        registry_index=registry_index,
        tw_registry_text_by_sample=tw_text_by_sample,
    )


def build_flight_plan_from_attempt(
    sample_ids: Sequence[str], attempt_dir: Path, registry_rows: Sequence[Mapping[str, str]]
) -> A2tAbstFlightPlan:
    """Convenience wrapper: derives every sample's own correct tool(s) via
    ``rails.probes.a2t_s2_flight.derive_a0_selected_tools`` (reused
    directly, module docstring) over ``sample_ids`` from the SAME consumed
    A0 attempt, then resolves via :func:`build_flight_plan`."""

    correct_tool_names = derive_a0_selected_tools(Path(attempt_dir), sample_ids)
    return build_flight_plan(sample_ids, correct_tool_names, registry_rows)


# ---------------------------------------------------------------------------
# Silence-swap wiring (module docstring: mirrors rails.probes.pslu_flight's
# own private helper of the identical name and shape).
# ---------------------------------------------------------------------------


def _swap_audio_media_relpath(
    messages: Sequence[Mapping[str, object]], media_relpath: str
) -> tuple[Mapping[str, object], ...]:
    """A silence-swap variant of ``messages``: same system+text content,
    audio content part's ``media_relpath`` replaced. Never mutates the
    input."""

    system_message, user_message = messages
    new_content = []
    for part in user_message["content"]:  # type: ignore[union-attr]
        if isinstance(part, Mapping) and part.get("type") == "input_audio":
            new_content.append({**part, "media_relpath": media_relpath})
        else:
            new_content.append(dict(part))
    return (dict(system_message), {"role": "user", "content": new_content})


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


def _withheld_tool_label(tool_names: Sequence[str]) -> str:
    """Mirrors ``rails.probes.a2t_s2b_flight._supplied_tool_label`` exactly
    (a private, module-scoped helper there; re-implemented here rather than
    imported across the module boundary, consistent with that module's own
    leading-underscore-stays-private convention): sorted, comma-joined tool
    names."""

    return ",".join(sorted(set(tool_names)))


@dataclass(frozen=True)
class A2tAbstFlightSummary:
    results: tuple[A2tS2ArmResult, ...]


def _iso(epoch_seconds: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _complete_and_record(
    core_client,
    *,
    cell: str,
    sample_id: str,
    withheld_tool: str | None,
    messages: Sequence[Mapping[str, object]],
    decoding_params: Mapping[str, object] | None,
    now: Callable[[], float],
) -> A2tS2ArmResult:
    started_at = _iso(now())
    t0 = now()
    response = core_client.complete(messages, decoding_params=decoding_params)
    latency_seconds = now() - t0
    return A2tS2ArmResult(
        arm=cell,
        sample_id=sample_id,
        supplied_tool=withheld_tool,
        response=response,
        timing={"started_at": started_at, "latency_seconds": latency_seconds},
    )


def run_a2t_abst_flight(
    *,
    adapter: Audio2ToolAdapter,
    core_client,
    samples: Sequence[Audio2ToolSample],
    plan: A2tAbstFlightPlan,
    silence_swap_media_relpaths: Mapping[str, str],
    decoding_params: Mapping[str, object] | None = None,
    now: Callable[[], float] = time.time,
) -> A2tAbstFlightSummary:
    """Execute the full four-cell 2x2 flight: TP-A, TP-S, TW-A, TW-S (the
    prereg's own table order), one request per sample per cell, over
    ``plan.sample_ids`` sorted. ``silence_swap_media_relpaths`` (``sample_id
    -> already-registered silent media_relpath``) is REQUIRED for every one
    of ``plan.sample_ids`` (module docstring: unlike P-SLU's own optional
    subset, every sample here needs its own silence counterpart for TP-S/
    TW-S). ``core_client`` is duck-typed against ``rails.core_client.
    CoreClient`` (never imported/annotated directly -- the same "no forced
    import" discipline the sibling probe flight modules already use)."""

    if not samples:
        raise A2tAbstFlightError("run_a2t_abst_flight requires at least one sample")
    by_id = {sample.sample_id: sample for sample in samples}
    missing = set(plan.sample_ids) - set(by_id)
    if missing:
        raise A2tAbstFlightError(
            f"plan names {len(missing)} sample id(s) not present in samples: {sorted(missing)[:5]}"
        )
    missing_silence = set(plan.sample_ids) - set(silence_swap_media_relpaths)
    if missing_silence:
        raise A2tAbstFlightError(
            f"silence_swap_media_relpaths is missing {len(missing_silence)} sample id(s) this flight "
            f"needs a silence counterpart for: {sorted(missing_silence)[:5]}"
        )

    results: list[A2tS2ArmResult] = []

    for sample_id in plan.sample_ids:
        sample = by_id[sample_id]
        silence_relpath = silence_swap_media_relpaths[sample_id]
        withheld_label = _withheld_tool_label(plan.correct_tool_names_by_sample[sample_id])

        tp_a_messages = adapter.assemble_prompt(sample, None)
        results.append(
            _complete_and_record(
                core_client, cell=TP_A_CELL, sample_id=sample_id, withheld_tool=None,
                messages=tp_a_messages, decoding_params=decoding_params, now=now,
            )
        )

        tp_s_messages = _swap_audio_media_relpath(tp_a_messages, silence_relpath)
        results.append(
            _complete_and_record(
                core_client, cell=TP_S_CELL, sample_id=sample_id, withheld_tool=None,
                messages=tp_s_messages, decoding_params=decoding_params, now=now,
            )
        )

        tw_text = plan.tw_registry_text_by_sample[sample_id]
        tw_a_messages = assemble_roster_prompt(sample, tw_text)
        results.append(
            _complete_and_record(
                core_client, cell=TW_A_CELL, sample_id=sample_id, withheld_tool=withheld_label,
                messages=tw_a_messages, decoding_params=decoding_params, now=now,
            )
        )

        tw_s_messages = _swap_audio_media_relpath(tw_a_messages, silence_relpath)
        results.append(
            _complete_and_record(
                core_client, cell=TW_S_CELL, sample_id=sample_id, withheld_tool=withheld_label,
                messages=tw_s_messages, decoding_params=decoding_params, now=now,
            )
        )

    return A2tAbstFlightSummary(results=tuple(results))


__all__ = [
    "A2T_ABST_CELLS",
    "ABST_N",
    "DEFAULT_SEED",
    "TP_A_CELL",
    "TP_S_CELL",
    "TW_A_CELL",
    "TW_S_CELL",
    # Re-exported from rails.probes.a2t_s2_flight (a caller of this module
    # needs only this one import site).
    "A2tS2ArmResult",
    "assemble_roster_prompt",
    "derive_a0_selected_tools",
    "render_roster_prompt_block",
    "result_to_json",
    "write_outputs_jsonl",
    "A2tAbstFlightError",
    "A2tAbstFlightPlan",
    "A2tAbstFlightSummary",
    "build_flight_plan",
    "build_flight_plan_from_attempt",
    "render_registry_minus_tools",
    "run_a2t_abst_flight",
    "seeded_abst_draw",
]
