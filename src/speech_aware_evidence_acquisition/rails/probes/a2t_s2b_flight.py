"""P-A2T Stage-2b supply-arm flight orchestration -- REGISTERED follow-up
probe (``bounded-discovery-probe``):
``docs/readiness/2026-08-18-pa2t-stage2b-preregistration-REGISTERED.md``.

Two arms over the SAME 120-sample Stage-2 headroom set (B1/B2), each one a
mechanical variant of a Stage-2 arm rather than a fresh construction:

- ``B1`` -- nodefaults: S1p's EXACT roster (the tool(s) the core itself
  named in its own A0 response, one row per distinct tool), rendered with
  ``argument_defaults`` STRIPPED (:func:`~data.audio2tool.render_registry_row`'s
  own ``strip_defaults=True``) -- the corruption-channel probe (prereg
  section 1, Q-A): Stage-2's S1p converted 16/120 but injected 34 supplied
  DEFAULT VALUES; B1 asks whether the clean supply form "row minus
  defaults" still converts without inducing substitutions.
- ``B2`` -- augmented wrong row: A0's EXACT full 152-row registry system
  prompt, PLUS the Stage-2-deranged WRONG tool's row appended under a
  clearly-marked, hash-pinned "particularly relevant" header -- the
  schema-vs-knowledge probe (prereg section 1, Q-B): the correct tool stays
  PRESENT in the registry, the wrong tool is merely highlighted, so a
  conversion here cannot be knowledge-tied to the correct row's own
  content.

NEW MODULE, not an in-place extension of ``rails.probes.a2t_s2_flight``
(mission instruction: "your call, state it"): Stage-2's own four arms
(S1p/S2/S4/N0r) are a REGISTERED, already-flown probe's frozen machinery --
touching that module risks silently perturbing byte-identical rendering
guarantees an already-consumed flight already relies on. This module
instead REUSES Stage-2's public primitives directly
(:func:`~rails.probes.a2t_s2_flight.assemble_roster_prompt`,
:class:`~rails.probes.a2t_s2_flight.A2tS2ArmResult`,
:func:`~rails.probes.a2t_s2_flight.result_to_json`,
:func:`~rails.probes.a2t_s2_flight.write_outputs_jsonl`,
:func:`~rails.probes.a2t_s2_flight.load_headroom_manifest`,
:class:`~rails.probes.a2t_s2_flight.HeadroomManifest`, re-exported here so
a caller needs only this one module) and
``data.audio2tool.render_registry_row`` (the same per-row JSON renderer,
its new ``strip_defaults`` parameter).

MAPPING REUSE (mission instruction, item 1): B1's per-sample roster and
B2's per-sample wrong tool are NEVER re-derived by this module -- they are
LOADED VERBATIM from Stage-2's own already-flown, already-written
``{RUN_ID}.arm-plan.json`` (``s1p_tool_names`` / ``s4_tool_name`` /
``s4_derangement`` / ``selected_tools``), via
``analysis.a2t_s2_read.load_arm_plan`` (reused, never a second parser of
that file). This module's own :func:`build_flight_plan` takes an
ALREADY-LOADED ``ArmPlan`` object (never a path) -- the SAME "caller loads,
this module only resolves" split ``rails.probes.a2t_s2_flight.build_flight_plan``
itself uses for ``selected_tools`` (loaded by
``derive_a0_selected_tools``, passed in, never re-derived inside
``build_flight_plan``) -- so this module's own top level stays free of any
import from the ``analysis`` package (mirrors that module's own documented
"rails' package top level stays free of analysis/scoring-stack imports for
any caller that never actually needs this" discipline; the ``ArmPlan``
type itself is imported only under ``TYPE_CHECKING``, never at runtime).
Reusing S1p's roster verbatim (rather than re-deriving from
``derive_a0_selected_tools`` a second time) guarantees B1's tool SET is
IDENTICAL to S1p's own, not merely "should be identical by construction" --
the only difference between the two arms' prompts is the presence/absence
of ``argument_defaults`` text. Reusing S4's derangement verbatim is the
mission's own explicit requirement ("for direct comparability with S4").

FAIL-CLOSED MAPPING VALIDATION: :func:`build_flight_plan` re-checks, at
plan-build time, every invariant the mission names -- a headroom sample
absent from Stage-2's own ``s1p_tool_names``/``s4_tool_name`` maps, a
global derangement fixed point (a tool mapping to itself), or a PER-SAMPLE
fixed point (the reused wrong tool coinciding with that sample's own
correctly-selected tool set) -- all raise :class:`A2tS2bFlightError` rather
than silently proceeding. Stage-2's own preflight already confirmed these
invariants hold for the real, pinned arm-plan (0 fixed points, 0 samples
supplied one of their own selections); this is defense-in-depth on a
VERBATIM reuse, not a new derivation that could newly violate them.

Zero live model contact, engineering only: every test in this repository's
own suite for this module drives ``rails.core_client.MockCoreClient``.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Mapping, Sequence

from ...data.audio2tool import render_registry_row
from ..adapters.audio2tool import Audio2ToolSample
from .a2t_s2_flight import (
    A2tS2ArmResult,
    HeadroomManifest,
    assemble_roster_prompt,
    load_headroom_manifest,
    result_to_json,
    write_outputs_jsonl,
)

if TYPE_CHECKING:  # pragma: no cover -- type-only, see module docstring
    from ...analysis.a2t_s2_read import ArmPlan

_PROBE_ID = "P-A2T"

B1_ARM = "B1"
B2_ARM = "B2"
A2T_S2B_ARMS: tuple[str, ...] = (B1_ARM, B2_ARM)

# Pinned, mission-required ("pin the header text as a hashed constant"):
# B2_HIGHLIGHT_HEADER_SHA256 == hashlib.sha256(B2_HIGHLIGHT_HEADER.encode
# ("utf-8")).hexdigest() -- reasserted by
# tests/unit/test_a2t_s2b_flight.py so a silent edit to the header text is
# caught immediately rather than quietly reshaping every B2 prompt.
B2_HIGHLIGHT_HEADER = "The following tool is particularly relevant to this request:"
B2_HIGHLIGHT_HEADER_SHA256 = (
    "befe65146a5abaa18b7d3446dfcdfeb5ed665f73e5b8564ba8b7d6916a71ebdf"
)


class A2tS2bFlightError(RuntimeError):
    """A Stage-2b flight input is malformed, Stage-2's own reused arm-plan
    is missing a required per-sample mapping or carries a fixed point (
    global or per-sample), or the flight loop is asked to run over a sample
    set that does not match its own precomputed plan."""


# ---------------------------------------------------------------------------
# The flight plan: both arms' per-sample roster/wrong-tool, precomputed once
# from Stage-2's own reused ArmPlan and independently auditable/testable
# before any request is ever issued.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2bFlightPlan:
    """Both arms' fully-resolved, precomputed per-sample content -- built
    ONCE from ``(headroom, arm_plan, registry_rows, full_registry_text)``,
    entirely deterministic and model-free (module docstring: no NEW
    randomization happens anywhere in this module -- both mappings are
    loaded verbatim from Stage-2's own already-seeded arm-plan)."""

    headroom_ids: tuple[str, ...]
    b1_tool_names_by_sample: Mapping[str, tuple[str, ...]]
    b2_wrong_tool_by_sample: Mapping[str, str]
    registry_index: Mapping[str, Mapping[str, str]]
    full_registry_text: str


def build_flight_plan(
    headroom: HeadroomManifest,
    arm_plan: "ArmPlan",
    registry_rows: Sequence[Mapping[str, str]],
    full_registry_text: str,
) -> A2tS2bFlightPlan:
    """Resolve both arms' per-sample content deterministically from Stage-2's
    OWN already-loaded ``arm_plan`` (module docstring: the caller loads it,
    e.g. via ``analysis.a2t_s2_read.load_arm_plan``, and passes it in here
    unchanged -- this function never touches a path). Fail-closed if the
    registry has a duplicate/missing ``tool_name``, if ``arm_plan``'s own
    ``headroom_ids`` does not match ``headroom.sample_ids`` exactly, if the
    reused ``s4_derangement`` carries a global fixed point, if any headroom
    sample is missing from ``s1p_tool_names``/``s4_tool_name``, or if any
    sample's reused wrong tool coincides with that sample's own correctly
    selected tool set (a per-sample fixed point)."""

    registry_index: dict[str, Mapping[str, str]] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not name:
            raise A2tS2bFlightError("registry row is missing tool_name")
        if name in registry_index:
            raise A2tS2bFlightError(f"registry has a duplicate tool_name {name!r}")
        registry_index[name] = row

    headroom_ids = tuple(sorted(headroom.sample_ids))
    arm_plan_headroom_set = set(arm_plan.headroom_ids)
    if set(headroom_ids) != arm_plan_headroom_set:
        missing = set(headroom_ids) - arm_plan_headroom_set
        extra = arm_plan_headroom_set - set(headroom_ids)
        raise A2tS2bFlightError(
            "Stage-2 arm-plan headroom_ids does not match this flight's own headroom manifest "
            f"exactly (missing={sorted(missing)[:5]}, extra={sorted(extra)[:5]})"
        )

    fixed_points = sorted(tool for tool, deranged in arm_plan.s4_derangement.items() if tool == deranged)
    if fixed_points:
        raise A2tS2bFlightError(
            f"Stage-2 arm-plan s4_derangement carries fixed point(s) (tool maps to itself), "
            f"refusing to reuse it verbatim: {fixed_points}"
        )

    b1_by_sample: dict[str, tuple[str, ...]] = {}
    b2_by_sample: dict[str, str] = {}
    for sample_id in headroom_ids:
        b1_names = arm_plan.s1p_tool_names.get(sample_id)
        if not b1_names:
            raise A2tS2bFlightError(
                f"{sample_id}: Stage-2 arm-plan s1p_tool_names has no entry -- B1's roster is "
                "reused verbatim from S1p and cannot be built without it"
            )
        unknown_b1 = set(b1_names) - registry_index.keys()
        if unknown_b1:
            raise A2tS2bFlightError(
                f"{sample_id}: B1 tool(s) {sorted(unknown_b1)} absent from the loaded registry"
            )
        b1_by_sample[sample_id] = b1_names

        wrong = arm_plan.s4_tool_name.get(sample_id)
        if not wrong:
            raise A2tS2bFlightError(
                f"{sample_id}: Stage-2 arm-plan s4_tool_name has no entry -- B2's wrong row is "
                "reused verbatim from S4 and cannot be built without it"
            )
        if wrong not in registry_index:
            raise A2tS2bFlightError(
                f"{sample_id}: B2 wrong tool {wrong!r} absent from the loaded registry"
            )
        own = set(arm_plan.selected_tools.get(sample_id, ()))
        if wrong in own:
            raise A2tS2bFlightError(
                f"{sample_id}: B2 wrong tool {wrong!r} coincides with this sample's own "
                "correctly selected tool set -- a per-sample fixed point, refusing to reuse it "
                "verbatim"
            )
        b2_by_sample[sample_id] = wrong

    return A2tS2bFlightPlan(
        headroom_ids=headroom_ids,
        b1_tool_names_by_sample=b1_by_sample,
        b2_wrong_tool_by_sample=b2_by_sample,
        registry_index=registry_index,
        full_registry_text=full_registry_text,
    )


# ---------------------------------------------------------------------------
# Prompt-content rendering.
# ---------------------------------------------------------------------------


def render_b1_tool_schemas(rows: Sequence[Mapping[str, str]]) -> str:
    """B1's own ``{tool_schemas}`` fill: S1p's exact roster (one or more
    rows, module docstring), rendered with ``argument_defaults`` REMOVED
    (``data.audio2tool.render_registry_row``'s own ``strip_defaults=True``)
    -- schema structure + constraints only, no values."""

    return "\n".join(render_registry_row(row, strip_defaults=True) for row in rows)


def render_b2_tool_schemas(full_registry_text: str, wrong_row: Mapping[str, str]) -> str:
    """B2's own ``{tool_schemas}`` fill: A0's EXACT full-registry text
    (byte-identical, passed in unchanged -- never re-rendered by this
    function), PLUS the pinned "particularly relevant" header, PLUS the
    deranged wrong tool's row (rendered WITH its defaults -- module
    docstring: this arm probes schema/attention, not the default-value
    channel B1 probes, so the wrong row is rendered exactly like any other
    ordinary registry row). Byte-precise composition:
    ``f"{full_registry_text}\\n\\n{B2_HIGHLIGHT_HEADER}\\n{rendered_wrong_row}"``."""

    return f"{full_registry_text}\n\n{B2_HIGHLIGHT_HEADER}\n{render_registry_row(wrong_row)}"


def _supplied_tool_label(tool_names: Sequence[str]) -> str:
    """B1's own ``supplied_tool`` label -- mirrors
    ``rails.probes.a2t_s2_flight._supplied_tool_label`` exactly (a private,
    module-scoped helper there; re-implemented here rather than imported
    across the module boundary, consistent with that module's own
    leading-underscore-stays-private convention): sorted, comma-joined tool
    names."""

    return ",".join(sorted(set(tool_names)))


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2bFlightSummary:
    results: tuple[A2tS2ArmResult, ...]


def _iso(epoch_seconds: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _complete_and_record(
    core_client,
    *,
    arm: str,
    sample_id: str,
    supplied_tool: str | None,
    messages: Sequence[Mapping[str, object]],
    decoding_params: Mapping[str, object] | None,
    now: Callable[[], float],
) -> A2tS2ArmResult:
    started_at = _iso(now())
    t0 = now()
    response = core_client.complete(messages, decoding_params=decoding_params)
    latency_seconds = now() - t0
    return A2tS2ArmResult(
        arm=arm,
        sample_id=sample_id,
        supplied_tool=supplied_tool,
        response=response,
        timing={"started_at": started_at, "latency_seconds": latency_seconds},
    )


def run_a2t_s2b_flight(
    *,
    core_client,
    samples: Sequence[Audio2ToolSample],
    plan: A2tS2bFlightPlan,
    decoding_params: Mapping[str, object] | None = None,
    now: Callable[[], float] = time.time,
) -> A2tS2bFlightSummary:
    """Execute the full two-arm P-A2T Stage-2b flight: B1 then B2, one
    request per sample per arm, over ``plan.headroom_ids`` sorted --
    mirrors ``rails.probes.a2t_s2_flight.run_a2t_s2_flight``'s own per-arm
    ordering discipline. No ``adapter`` parameter (unlike Stage-2's own
    orchestrator): neither arm reuses ``Audio2ToolAdapter.assemble_prompt``
    unchanged the way Stage-2's N0r does, so nothing here needs the
    adapter object. ``core_client`` is duck-typed against
    ``rails.core_client.CoreClient`` (never imported/annotated directly --
    the same "no forced import" discipline ``rails.probes.a2t_s2_flight``
    itself already uses)."""

    if not samples:
        raise A2tS2bFlightError("run_a2t_s2b_flight requires at least one sample")
    by_id = {sample.sample_id: sample for sample in samples}
    missing = set(plan.headroom_ids) - set(by_id)
    if missing:
        raise A2tS2bFlightError(
            f"plan names {len(missing)} headroom sample id(s) not present in samples: "
            f"{sorted(missing)[:5]}"
        )

    results: list[A2tS2ArmResult] = []

    for sample_id in plan.headroom_ids:
        sample = by_id[sample_id]

        b1_names = plan.b1_tool_names_by_sample[sample_id]
        b1_rows = [plan.registry_index[name] for name in b1_names]
        b1_block = render_b1_tool_schemas(b1_rows)
        results.append(
            _complete_and_record(
                core_client,
                arm=B1_ARM,
                sample_id=sample_id,
                supplied_tool=_supplied_tool_label(b1_names),
                messages=assemble_roster_prompt(sample, b1_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

        wrong_name = plan.b2_wrong_tool_by_sample[sample_id]
        wrong_row = plan.registry_index[wrong_name]
        b2_block = render_b2_tool_schemas(plan.full_registry_text, wrong_row)
        results.append(
            _complete_and_record(
                core_client,
                arm=B2_ARM,
                sample_id=sample_id,
                supplied_tool=wrong_name,
                messages=assemble_roster_prompt(sample, b2_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

    return A2tS2bFlightSummary(results=tuple(results))


def _assert_header_hash_pinned() -> None:  # pragma: no cover -- exercised by the test suite
    computed = hashlib.sha256(B2_HIGHLIGHT_HEADER.encode("utf-8")).hexdigest()
    if computed != B2_HIGHLIGHT_HEADER_SHA256:
        raise A2tS2bFlightError(
            f"B2_HIGHLIGHT_HEADER text drifted from its pinned hash: computed={computed!r}, "
            f"pinned={B2_HIGHLIGHT_HEADER_SHA256!r}"
        )


__all__ = [
    "A2T_S2B_ARMS",
    "B1_ARM",
    "B2_ARM",
    "B2_HIGHLIGHT_HEADER",
    "B2_HIGHLIGHT_HEADER_SHA256",
    # Re-exported from rails.probes.a2t_s2_flight (module docstring: a
    # caller of this Stage-2b module needs only this one import site).
    "A2tS2ArmResult",
    "HeadroomManifest",
    "assemble_roster_prompt",
    "load_headroom_manifest",
    "result_to_json",
    "write_outputs_jsonl",
    "A2tS2bFlightError",
    "A2tS2bFlightPlan",
    "A2tS2bFlightSummary",
    "build_flight_plan",
    "render_b1_tool_schemas",
    "render_b2_tool_schemas",
    "run_a2t_s2b_flight",
]
