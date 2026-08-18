"""P-A2T Stage-2c form-robustness probe flight orchestration -- REGISTERED
probe (Stage-2c, ``bounded-discovery-probe``):
``docs/readiness/2026-08-18-pa2t-stage2c-preregistration-REGISTERED.md``.

Three arms over the SAME 120-sample Stage-2 headroom set (C1/C2/C3), each a
PRESENTATION-AXIS variant of Stage-2b's own B1 arm
(``rails.probes.a2t_s2b_flight``) rather than a fresh construction --
prereg intro: "the SAME 120 headroom ids ... decode config identical to
Stage-2/2b ... so robustness must be probed on the *presentation axis*, not
by re-flying B1". Every arm supplies the SAME CONTENT as B1 (the correct
tool's registry row(s), ``argument_defaults`` STRIPPED, reused verbatim
from Stage-2's own ``s1p_tool_names`` -- never re-derived, mirrors
``rails.probes.a2t_s2b_flight``'s own "mapping reuse" discipline exactly):

- ``C1`` -- permuted: B1's content, rendered with a SEEDED PERMUTATION of
  each row's own JSON field order and its ``argument_constraints`` clause
  order (deterministic from ``(seed, sample_id)`` -- never from response
  content, never re-seeded per call) -- REPLACING form, like B1 (prereg
  design table).
- ``C2`` -- verbalized: B1's content, with ``argument_constraints``
  VERBALIZED as English prose sentence(s) covering the SAME clauses (no
  new values -- :func:`verbalize_constraints` is a small, pure,
  deterministic function; no LLM involvement) -- REPLACING form, like B1.
- ``C3`` -- augmented right row: A0's EXACT full 152-row registry system
  prompt, PLUS B1's own content (stripped, unpermuted, unverbalized)
  appended under Stage-2b's OWN hash-pinned "particularly relevant" header
  (``rails.probes.a2t_s2b_flight.B2_HIGHLIGHT_HEADER``, REUSED directly,
  never re-typed -- prereg: "the SAME 'particularly relevant' header as
  Stage-2b's B2 used") -- AUGMENTING form, the direct right-row contrast to
  B2's wrong-row augment.

NEW MODULE, not an in-place extension of ``rails.probes.a2t_s2b_flight``
(the same reasoning that module's own docstring gives for not extending
``a2t_s2_flight``: B1/B2 are a REGISTERED, already-flown probe's frozen
machinery -- touching that module risks perturbing byte-identical
rendering guarantees an already-consumed flight relies on). This module
REUSES ``rails.probes.a2t_s2b_flight.B2_HIGHLIGHT_HEADER`` /
``B2_HIGHLIGHT_HEADER_SHA256`` directly (the exact same pinned constant,
never a second header string) and ``render_b1_tool_schemas`` (C3's own
appended block is byte-identical to what B1 itself renders), plus
``rails.probes.a2t_s2_flight``'s own re-exported primitives
(``A2tS2ArmResult``, ``HeadroomManifest``, ``assemble_roster_prompt``,
``load_headroom_manifest``, ``result_to_json``, ``write_outputs_jsonl``),
re-exported here so a caller needs only this one module -- mirrors
``rails.probes.a2t_s2b_flight``'s own re-export discipline exactly.

MAPPING REUSE: every arm's per-sample roster is Stage-2's OWN
``s1p_tool_names`` (the SAME mapping ``rails.probes.a2t_s2b_flight``'s own
B1 arm already sources it from), loaded verbatim via an ALREADY-LOADED
``ArmPlan`` object passed into :func:`build_flight_plan` (never a path --
the same "caller loads, this module only resolves" split both
``a2t_s2_flight`` and ``a2t_s2b_flight`` already use); this module's own
top level stays free of any import from the ``analysis`` package (the
``ArmPlan`` type itself is imported only under ``TYPE_CHECKING``, never at
runtime).

FAIL-CLOSED MAPPING VALIDATION: :func:`build_flight_plan` re-checks, at
plan-build time, every invariant this module needs -- a headroom sample
absent from Stage-2's own ``s1p_tool_names`` map, or a named tool absent
from the loaded registry -- and raises :class:`A2tS2cFlightError` rather
than silently proceeding. This module never touches ``s4_tool_name`` /
``s4_derangement`` at all: no C-arm supplies a wrong tool, so the S4
derangement's own no-fixed-point invariant is out of scope here (unlike
``rails.probes.a2t_s2b_flight``'s B2 arm).

Zero live model contact, engineering only: every test in this repository's
own suite for this module drives ``rails.core_client.MockCoreClient``.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Mapping, Sequence

from ...data.audio2tool import render_registry_row
from ..adapters.audio2tool import Audio2ToolSample
from .a2t_s2_flight import (
    DEFAULT_SEED,
    A2tS2ArmResult,
    HeadroomManifest,
    assemble_roster_prompt,
    load_headroom_manifest,
    result_to_json,
    write_outputs_jsonl,
)
from .a2t_s2b_flight import B2_HIGHLIGHT_HEADER, B2_HIGHLIGHT_HEADER_SHA256, render_b1_tool_schemas

if TYPE_CHECKING:  # pragma: no cover -- type-only, see module docstring
    from ...analysis.a2t_s2_read import ArmPlan

_PROBE_ID = "P-A2T"

C1_ARM = "C1"
C2_ARM = "C2"
C3_ARM = "C3"
A2T_S2C_ARMS: tuple[str, ...] = (C1_ARM, C2_ARM, C3_ARM)

# Engineering-interpretation choice (module docstring: undocumented
# upstream, flagged here rather than guessed silently): the registry's own
# multi-constraint shape is not specified anywhere upstream, so a row
# naming more than one argument's constraints is assumed to separate them
# with this delimiter -- the one surveyed real shape, "mode: [Home,
# Armed_Away]", is a single clause and is unaffected either way.
_CONSTRAINT_CLAUSE_DELIMITER = ";"
_ENUM_CLAUSE_PATTERN = re.compile(r"^(?P<param>[^:\[\]]+):\s*\[(?P<values>[^\[\]]*)\]$")


class A2tS2cFlightError(RuntimeError):
    """A Stage-2c flight input is malformed, Stage-2's own reused arm-plan
    is missing a required per-sample ``s1p_tool_names`` entry, or the
    flight loop is asked to run over a sample set that does not match its
    own precomputed plan."""


# ---------------------------------------------------------------------------
# C1: seeded field-order / constraint-clause-order permutation.
# ---------------------------------------------------------------------------


def _sample_permutation_seed(seed: int, sample_id: str) -> int:
    """A deterministic per-``(seed, sample_id)`` integer seed for C1's own
    permutation RNG -- sha256-derived so it never depends on Python's own
    process-level hash randomization (``hash()`` is salted per-process;
    this must reproduce ACROSS processes -- a real flight vs. a later
    read/test run)."""

    digest = hashlib.sha256(f"{seed}:{sample_id}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def split_constraint_clauses(argument_constraints: str) -> tuple[str, ...]:
    """``argument_constraints`` split into individual clauses on
    :data:`_CONSTRAINT_CLAUSE_DELIMITER`. Blank/whitespace-only clauses are
    dropped; a 0- or 1-clause string round-trips with nothing to split."""

    return tuple(
        clause.strip()
        for clause in argument_constraints.split(_CONSTRAINT_CLAUSE_DELIMITER)
        if clause.strip()
    )


def _permute_constraint_clauses(argument_constraints: str, rng: random.Random) -> str:
    """A seeded permutation of ``argument_constraints``' own clause order --
    content-preserving (the SAME clause texts, just reordered). 0 or 1
    clause is returned byte-identical (nothing to permute)."""

    clauses = list(split_constraint_clauses(argument_constraints))
    if len(clauses) < 2:
        return argument_constraints
    order = list(range(len(clauses)))
    rng.shuffle(order)
    return f"{_CONSTRAINT_CLAUSE_DELIMITER} ".join(clauses[i] for i in order)


def _permute_key_order(payload: Mapping[str, object], rng: random.Random) -> dict[str, object]:
    """A seeded permutation of ``payload``'s own top-level key order --
    content-preserving (the SAME ``{key: value}`` pairs, just reordered);
    the caller renders this with plain ``json.dumps`` (no ``sort_keys``) so
    the permuted order actually survives serialization."""

    keys = list(payload.keys())
    rng.shuffle(keys)
    return {key: payload[key] for key in keys}


def render_c1_tool_schemas(rows: Sequence[Mapping[str, str]], *, seed: int, sample_id: str) -> str:
    """C1's own ``{tool_schemas}`` fill: B1's content (``argument_defaults``
    STRIPPED, ``data.audio2tool.render_registry_row``'s own
    ``strip_defaults=True`` -- reused via that function, never
    reimplemented), each row's JSON field order AND its own
    ``argument_constraints`` clause order seeded-permuted from
    ``(seed, sample_id)``. ONE :class:`random.Random` drives every row of
    this sample IN ORDER (mirrors ``rails.probes.a2t_s2_flight.
    build_flight_plan``'s own "one RNG consumed across a fixed, sorted
    iteration order" reproducibility contract), so a multi-intent sample's
    several rows each get their own, still fully deterministic,
    permutation rather than an identical one repeated per row.
    Content-preserving: for every rendered line,
    ``json.loads(line) == json.loads(render_registry_row(row,
    strip_defaults=True))`` -- the SAME field multiset, only the key/clause
    ORDER differs."""

    rng = random.Random(_sample_permutation_seed(seed, sample_id))
    lines: list[str] = []
    for row in rows:
        stripped = json.loads(render_registry_row(row, strip_defaults=True))
        if "argument_constraints" in stripped:
            stripped["argument_constraints"] = _permute_constraint_clauses(
                stripped["argument_constraints"], rng
            )
        permuted = _permute_key_order(stripped, rng)
        lines.append(json.dumps(permuted, ensure_ascii=False))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# C2: deterministic English-prose verbalization of argument_constraints.
# ---------------------------------------------------------------------------


def verbalize_constraint_clause(clause: str) -> str:
    """One constraint clause as an English sentence -- SAME content, no
    value added: the enumerated-type shape (``"param: [v1, v2]"``, the one
    surveyed real registry shape) becomes "The param argument must be one
    of: v1, v2."; any other shape is wrapped, verbatim, as
    "Constraint: <clause>." (never invents a value the clause did not
    already carry)."""

    clause = clause.strip()
    if not clause:
        return ""
    match = _ENUM_CLAUSE_PATTERN.match(clause)
    if match:
        param = match.group("param").strip()
        values = [v.strip() for v in match.group("values").split(",") if v.strip()]
        if param and values:
            return f"The {param} argument must be one of: {', '.join(values)}."
    return f"Constraint: {clause}."


def verbalize_constraints(argument_constraints: str) -> str:
    """``argument_constraints`` rendered as one or more English prose
    sentences, one per clause (:func:`split_constraint_clauses`), in their
    ORIGINAL order (verbalization changes FORM only; C1 alone changes
    order -- keeping the two manipulations orthogonal, mirroring the
    prereg's own "C1/C2 perturb only presentation ... content identical"
    framing). Blank input returns ``""``."""

    clauses = split_constraint_clauses(argument_constraints)
    return " ".join(verbalize_constraint_clause(clause) for clause in clauses)


def render_c2_row(row: Mapping[str, str]) -> str:
    """One row's C2 rendering: B1's stripped JSON shape
    (``data.audio2tool.render_registry_row``'s own ``strip_defaults=True``),
    with ``argument_constraints`` replaced by its verbalized prose
    (:func:`verbalize_constraints`) -- every other key/value and the
    sorted-key JSON formatting convention stay byte-identical to B1's own
    rendering."""

    stripped = json.loads(render_registry_row(row, strip_defaults=True))
    if "argument_constraints" in stripped:
        stripped["argument_constraints"] = verbalize_constraints(stripped["argument_constraints"])
    return json.dumps(stripped, ensure_ascii=False, sort_keys=True)


def render_c2_tool_schemas(rows: Sequence[Mapping[str, str]]) -> str:
    """C2's own ``{tool_schemas}`` fill: :func:`render_c2_row` newline-
    joined over every row -- mirrors ``rails.probes.a2t_s2b_flight.
    render_b1_tool_schemas``'s own join convention exactly."""

    return "\n".join(render_c2_row(row) for row in rows)


# ---------------------------------------------------------------------------
# C3: full registry + B1's content appended under B2's OWN pinned header.
# ---------------------------------------------------------------------------


def render_c3_tool_schemas(full_registry_text: str, rows: Sequence[Mapping[str, str]]) -> str:
    """C3's own ``{tool_schemas}`` fill: A0's EXACT full-registry text
    (byte-identical, passed in unchanged -- never re-rendered by this
    function), PLUS Stage-2b's OWN pinned "particularly relevant" header
    (``B2_HIGHLIGHT_HEADER``, reused directly), PLUS B1's own content
    (``rails.probes.a2t_s2b_flight.render_b1_tool_schemas``, reused
    directly -- stripped, unpermuted, unverbalized) -- the direct right-row
    contrast to B2's wrong-row augment (module docstring). Byte-precise
    composition:
    ``f"{full_registry_text}\\n\\n{B2_HIGHLIGHT_HEADER}\\n{rendered_rows}"``,
    identical in SHAPE to ``render_b2_tool_schemas``'s own composition."""

    return f"{full_registry_text}\n\n{B2_HIGHLIGHT_HEADER}\n{render_b1_tool_schemas(rows)}"


def _supplied_tool_label(tool_names: Sequence[str]) -> str:
    """Mirrors ``rails.probes.a2t_s2b_flight._supplied_tool_label`` exactly
    (a private, module-scoped helper there; re-implemented here rather than
    imported across the module boundary, consistent with that module's own
    leading-underscore-stays-private convention): sorted, comma-joined tool
    names."""

    return ",".join(sorted(set(tool_names)))


# ---------------------------------------------------------------------------
# The flight plan: every arm's per-sample roster, precomputed once and
# independently auditable/testable before any request is ever issued.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2cFlightPlan:
    """Every arm's fully-resolved, precomputed per-sample content -- built
    ONCE from ``(headroom, arm_plan, registry_rows, full_registry_text,
    seed)``. C1/C2/C3 all draw from the SAME
    ``correct_tool_names_by_sample`` (Stage-2's own ``s1p_tool_names``,
    reused verbatim) -- no NEW randomization anywhere in this module
    decides WHICH tool is supplied, only HOW it is presented."""

    headroom_ids: tuple[str, ...]
    correct_tool_names_by_sample: Mapping[str, tuple[str, ...]]
    registry_index: Mapping[str, Mapping[str, str]]
    full_registry_text: str
    seed: int


def build_flight_plan(
    headroom: HeadroomManifest,
    arm_plan: "ArmPlan",
    registry_rows: Sequence[Mapping[str, str]],
    full_registry_text: str,
    *,
    seed: int = DEFAULT_SEED,
) -> A2tS2cFlightPlan:
    """Resolve every arm's per-sample roster deterministically from Stage-2's
    OWN already-loaded ``arm_plan`` (module docstring: the caller loads it,
    e.g. via ``analysis.a2t_s2_read.load_arm_plan``, and passes it in here
    unchanged -- this function never touches a path). Fail-closed if the
    registry has a duplicate/missing ``tool_name``, if ``arm_plan``'s own
    ``headroom_ids`` does not match ``headroom.sample_ids`` exactly, or if
    any headroom sample is missing from ``s1p_tool_names`` or names a tool
    absent from the loaded registry."""

    registry_index: dict[str, Mapping[str, str]] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not name:
            raise A2tS2cFlightError("registry row is missing tool_name")
        if name in registry_index:
            raise A2tS2cFlightError(f"registry has a duplicate tool_name {name!r}")
        registry_index[name] = row

    headroom_ids = tuple(sorted(headroom.sample_ids))
    arm_plan_headroom_set = set(arm_plan.headroom_ids)
    if set(headroom_ids) != arm_plan_headroom_set:
        missing = set(headroom_ids) - arm_plan_headroom_set
        extra = arm_plan_headroom_set - set(headroom_ids)
        raise A2tS2cFlightError(
            "Stage-2 arm-plan headroom_ids does not match this flight's own headroom manifest "
            f"exactly (missing={sorted(missing)[:5]}, extra={sorted(extra)[:5]})"
        )

    by_sample: dict[str, tuple[str, ...]] = {}
    for sample_id in headroom_ids:
        names = arm_plan.s1p_tool_names.get(sample_id)
        if not names:
            raise A2tS2cFlightError(
                f"{sample_id}: Stage-2 arm-plan s1p_tool_names has no entry -- every C-arm's "
                "content is reused verbatim from S1p/B1 and cannot be built without it"
            )
        unknown = set(names) - registry_index.keys()
        if unknown:
            raise A2tS2cFlightError(
                f"{sample_id}: tool(s) {sorted(unknown)} absent from the loaded registry"
            )
        by_sample[sample_id] = names

    return A2tS2cFlightPlan(
        headroom_ids=headroom_ids,
        correct_tool_names_by_sample=by_sample,
        registry_index=registry_index,
        full_registry_text=full_registry_text,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2cFlightSummary:
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


def run_a2t_s2c_flight(
    *,
    core_client,
    samples: Sequence[Audio2ToolSample],
    plan: A2tS2cFlightPlan,
    decoding_params: Mapping[str, object] | None = None,
    now: Callable[[], float] = time.time,
) -> A2tS2cFlightSummary:
    """Execute the full three-arm P-A2T Stage-2c flight: C1 then C2 then C3,
    one request per sample per arm, over ``plan.headroom_ids`` sorted --
    mirrors ``rails.probes.a2t_s2b_flight.run_a2t_s2b_flight``'s own
    per-arm ordering discipline. ``core_client`` is duck-typed against
    ``rails.core_client.CoreClient`` (never imported/annotated directly --
    the same "no forced import" discipline the other probe flight modules
    already use)."""

    if not samples:
        raise A2tS2cFlightError("run_a2t_s2c_flight requires at least one sample")
    by_id = {sample.sample_id: sample for sample in samples}
    missing = set(plan.headroom_ids) - set(by_id)
    if missing:
        raise A2tS2cFlightError(
            f"plan names {len(missing)} headroom sample id(s) not present in samples: "
            f"{sorted(missing)[:5]}"
        )

    results: list[A2tS2ArmResult] = []

    for sample_id in plan.headroom_ids:
        sample = by_id[sample_id]
        names = plan.correct_tool_names_by_sample[sample_id]
        rows = [plan.registry_index[name] for name in names]
        supplied_tool = _supplied_tool_label(names)

        c1_block = render_c1_tool_schemas(rows, seed=plan.seed, sample_id=sample_id)
        results.append(
            _complete_and_record(
                core_client,
                arm=C1_ARM,
                sample_id=sample_id,
                supplied_tool=supplied_tool,
                messages=assemble_roster_prompt(sample, c1_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

        c2_block = render_c2_tool_schemas(rows)
        results.append(
            _complete_and_record(
                core_client,
                arm=C2_ARM,
                sample_id=sample_id,
                supplied_tool=supplied_tool,
                messages=assemble_roster_prompt(sample, c2_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

        c3_block = render_c3_tool_schemas(plan.full_registry_text, rows)
        results.append(
            _complete_and_record(
                core_client,
                arm=C3_ARM,
                sample_id=sample_id,
                supplied_tool=supplied_tool,
                messages=assemble_roster_prompt(sample, c3_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

    return A2tS2cFlightSummary(results=tuple(results))


def _assert_header_hash_pinned() -> None:  # pragma: no cover -- exercised by the test suite
    computed = hashlib.sha256(B2_HIGHLIGHT_HEADER.encode("utf-8")).hexdigest()
    if computed != B2_HIGHLIGHT_HEADER_SHA256:
        raise A2tS2cFlightError(
            f"B2_HIGHLIGHT_HEADER text drifted from its pinned hash: computed={computed!r}, "
            f"pinned={B2_HIGHLIGHT_HEADER_SHA256!r}"
        )


__all__ = [
    "A2T_S2C_ARMS",
    "C1_ARM",
    "C2_ARM",
    "C3_ARM",
    # Re-exported from rails.probes.a2t_s2_flight / a2t_s2b_flight (module
    # docstring: a caller of this Stage-2c module needs only this one
    # import site).
    "A2tS2ArmResult",
    "B2_HIGHLIGHT_HEADER",
    "B2_HIGHLIGHT_HEADER_SHA256",
    "HeadroomManifest",
    "assemble_roster_prompt",
    "load_headroom_manifest",
    "render_b1_tool_schemas",
    "result_to_json",
    "write_outputs_jsonl",
    "A2tS2cFlightError",
    "A2tS2cFlightPlan",
    "A2tS2cFlightSummary",
    "build_flight_plan",
    "render_c1_tool_schemas",
    "render_c2_row",
    "render_c2_tool_schemas",
    "render_c3_tool_schemas",
    "run_a2t_s2c_flight",
    "split_constraint_clauses",
    "verbalize_constraint_clause",
    "verbalize_constraints",
]
