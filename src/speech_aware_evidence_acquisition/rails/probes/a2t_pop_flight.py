"""P-A2T whole-population regression-arm flight orchestration -- REGISTERED
probe (``bounded-discovery-probe``): ``docs/readiness/
2026-08-19-a2t-pop-preregistration-REGISTERED.md`` (``SAEA-PROBE-a2t-pop-194``).

Two arms over the 97 EM-CORRECT ids of the frozen A2T 400 -- the samples
where the consumed A0 attempt already scored ``tool_accuracy == 1.0 AND
exact_match == 1.0`` (the only EM-REGRESSION-eligible ids: the prereg's own
"missing regression term of the signed law", the complement of the already-
consumed 120-id headroom set within the 217 tool-correct ids -- 217 - 120 =
97):

- ``R0`` -- zero-supply re-fly (in-session comparator; doubles as this
  population's own first EM-stability measurement): BYTE-IDENTICAL to A0's
  own request, reusing ``rails.adapters.audio2tool.Audio2ToolAdapter.
  assemble_prompt(sample, None)`` unchanged -- the SAME "A0 comparator
  stability" replay ``rails.probes.a2t_s2_flight``'s own N0r arm already
  established.
- ``R1`` -- B1-form values-stripped self-supplied row of the core's own
  A0-selected tool: on these 97 ids the A0 selection IS the correct tool (by
  this population's own defining criterion, ``tool_accuracy == 1.0``), so
  R1's roster is derived via ``rails.probes.a2t_s2_flight.
  derive_a0_selected_tools`` (reused directly, never re-derived a second
  way) and rendered via ``rails.probes.a2t_s2b_flight.render_b1_tool_schemas``
  (the SAME ``strip_defaults=True`` rendering Stage-2b's own B1 arm uses) --
  deployment-legal, gold-free, self-supplied.

ROSTER SOURCING (prereg section 2, "source them the way the headroom list
was sourced ... via the consumed read archive's published artifacts, never
re-scoring"): the 97-id roster is NEVER hand-curated or re-derived by a
second scoring implementation. :func:`load_headroom_source` reads the
consumed A0 read's own published ``headroom.json`` artifact
(``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/
headroom.json``) purely for its ``attempt_dir``/``split_identity_hash``
fields -- the SAME attempt the headroom list itself was sourced from.
:func:`derive_em_correct_ids` then reuses ``analysis.a2t_read.
load_attempt_rows``/``score_row`` (the EXACT same frozen scorer pipeline
``analysis.a2t_read.stage2_headroom_ids`` itself was built on) over that
SAME attempt, filtering for the complementary predicate
(``tool_accuracy == 1.0 AND exact_match == 1.0`` rather than
``... AND exact_match == 0.0``) -- reusing the frozen scorer, never a
second, independently-authored one; this is a READ of an already-flown,
already-consumed attempt's own recorded output (mirrors
``rails.probes.a2t_s2_flight.derive_a0_selected_tools``'s own module
docstring: "not a new model contact"), not a re-scoring on this module's own
authority.

Zero live model contact, engineering only: every test in this repository's
own suite for this module drives ``rails.core_client.MockCoreClient``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..adapters.audio2tool import Audio2ToolAdapter, Audio2ToolSample
from ..runner import ZERO_SUPPLY_ARM
from .a2t_s2_flight import (
    DEFAULT_SEED,
    HEADROOM_SCHEMA,
    A2tS2ArmResult,
    assemble_roster_prompt,
    derive_a0_selected_tools,
    result_to_json,
    write_outputs_jsonl,
)
from .a2t_s2b_flight import render_b1_tool_schemas

_PROBE_ID = "P-A2T-POP"

R0_ARM = "R0"
R1_ARM = "R1"
A2T_POP_ARMS: tuple[str, ...] = (R0_ARM, R1_ARM)

EM_CORRECT_N = 97

# Mirrors ``analysis.a2t_read.DEFAULT_SPLIT_ROLE`` verbatim -- kept as this
# module's own local constant rather than a top-level ``analysis`` import
# (mirrors ``rails.probes.a2t_s2_flight``'s own documented "rails' package
# top level stays free of analysis/scoring-stack imports for any caller that
# never actually needs this" discipline; :func:`derive_em_correct_ids` still
# imports the analysis-package primitives it genuinely needs, function-local).
DEFAULT_SPLIT_ROLE = "discovery"

# 2026-08-18 pa2t-a0-read's own frozen discovery-split receipt hash (recorded
# verbatim in BOTH headroom.json and this probe's own exposure-ledger row) --
# pinned here, mirroring ``rails.probes.a2t_s2b_flight.B2_HIGHLIGHT_HEADER_SHA256``'s
# own "pin the constant, assert it never drifted silently" discipline, rather
# than re-typing the literal at every call site.
SPLIT_IDENTITY_HASH = "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"


class A2tPopFlightError(RuntimeError):
    """A whole-population regression-arm flight input is malformed, the
    consumed A0 read's own published headroom artifact fails its own
    load-time checks, the EM-correct roster derived from it does not match
    its own registered count (97), or the flight loop is asked to run over a
    sample set that does not match its own precomputed plan."""


# ---------------------------------------------------------------------------
# Roster sourcing: headroom.json's own published (attempt_dir,
# split_identity_hash) + the EM-correct id derivation over that SAME attempt.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeadroomSource:
    """The two fields this module needs out of the consumed A0 read's own
    published ``headroom.json`` artifact -- ``attempt_dir`` (which attempt
    the 97-id EM-correct roster must be sourced from, module docstring) and
    ``split_identity_hash`` (carried through for the fail-closed pinned-hash
    check, :func:`assert_split_identity_hash_pinned`). Deliberately NOT the
    full ``rails.probes.a2t_s2_flight.HeadroomManifest`` (that dataclass
    hard-enforces exactly 120 headroom ids -- an owner ruling about the
    HEADROOM flight's own spend, orthogonal to this module's own 97-id
    EM-correct population)."""

    attempt_dir: str
    split_identity_hash: str
    headroom_sample_ids: tuple[str, ...]


def load_headroom_source(path: Path) -> HeadroomSource:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schema") != HEADROOM_SCHEMA:
        raise A2tPopFlightError(
            f"{path}: schema must be {HEADROOM_SCHEMA!r}, got {document.get('schema')!r}"
        )
    attempt_dir = document.get("attempt_dir")
    if not isinstance(attempt_dir, str) or not attempt_dir:
        raise A2tPopFlightError(f"{path}: attempt_dir must be a non-empty string")
    split_identity_hash = document.get("split_identity_hash")
    if not isinstance(split_identity_hash, str) or not split_identity_hash:
        raise A2tPopFlightError(f"{path}: split_identity_hash must be a non-empty string")
    sample_ids = document.get("sample_ids")
    if not isinstance(sample_ids, list) or not all(isinstance(sid, str) for sid in sample_ids):
        raise A2tPopFlightError(f"{path}: sample_ids must be a list of strings")
    return HeadroomSource(
        attempt_dir=attempt_dir,
        split_identity_hash=split_identity_hash,
        headroom_sample_ids=tuple(sorted(sample_ids)),
    )


def assert_split_identity_hash_pinned(split_identity_hash: str) -> None:
    """Fail-closed guard a real launcher calls before spending any request:
    the consumed A0 read's own published split identity must equal the
    pinned :data:`SPLIT_IDENTITY_HASH` this probe was registered against."""

    if split_identity_hash != SPLIT_IDENTITY_HASH:
        raise A2tPopFlightError(
            f"split_identity_hash {split_identity_hash!r} does not match the pinned "
            f"{SPLIT_IDENTITY_HASH!r} this probe was registered against"
        )


def derive_em_correct_ids(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    split_role: str = DEFAULT_SPLIT_ROLE,
    expected_n: int = EM_CORRECT_N,
) -> tuple[str, ...]:
    """The 97-id EM-correct roster (module docstring: sourced the SAME way
    the Stage-2 headroom list itself was sourced -- reusing
    ``analysis.a2t_read.load_attempt_rows``/``score_row`` directly over the
    consumed A0 attempt, never a second scorer implementation). Fail-closed:
    a malformed row, a row on an arm other than ``zero-supply`` (this
    attempt is meant to carry ONLY A0's own zero-supply arm), a duplicate
    sample_id row, or a derived roster whose size does not equal
    ``expected_n`` all raise :class:`A2tPopFlightError`."""

    from ...analysis.a2t_read import load_attempt_rows, score_row

    rows, malformed = load_attempt_rows(Path(attempt_dir))
    if malformed:
        raise A2tPopFlightError(
            f"{attempt_dir}: {len(malformed)} malformed outputs.jsonl row(s), e.g. {malformed[0]!r}"
        )
    wrong_arm = [row.sample_id for row in rows if row.arm != ZERO_SUPPLY_ARM]
    if wrong_arm:
        raise A2tPopFlightError(
            f"{attempt_dir}: {len(wrong_arm)} row(s) on an arm other than {ZERO_SUPPLY_ARM!r}, "
            f"e.g. {wrong_arm[:5]} -- this attempt is expected to carry only A0's own zero-supply arm"
        )
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        if row.sample_id in seen:
            duplicates.append(row.sample_id)
        seen.add(row.sample_id)
    if duplicates:
        raise A2tPopFlightError(f"{attempt_dir}: duplicate sample_id row(s): {sorted(set(duplicates))[:5]}")

    adapter = Audio2ToolAdapter(lock, root, repo_root=repo_root)
    scores = [score_row(adapter, row) for row in rows]
    ids = tuple(
        sorted(
            s.row.sample_id
            for s in scores
            if float(s.metrics["tool_accuracy"]) == 1.0 and float(s.metrics["exact_match"]) == 1.0
        )
    )
    if len(set(ids)) != len(ids):  # pragma: no cover -- precluded by the duplicate-row check above
        raise A2tPopFlightError(f"{attempt_dir}: derived EM-correct roster carries duplicate ids")
    if len(ids) != expected_n:
        raise A2tPopFlightError(
            f"{attempt_dir}: derived {len(ids)} EM-correct id(s), expected exactly {expected_n} "
            "(97/97 fail-closed check)"
        )
    return ids


# ---------------------------------------------------------------------------
# The flight plan: R1's per-sample self-supplied roster, precomputed once and
# independently auditable/testable before any request is ever issued.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tPopFlightPlan:
    sample_ids: tuple[str, ...]
    r1_tool_names_by_sample: Mapping[str, tuple[str, ...]]
    registry_index: Mapping[str, Mapping[str, str]]


def build_flight_plan(
    sample_ids: Sequence[str],
    r1_tool_names: Mapping[str, tuple[str, ...]],
    registry_rows: Sequence[Mapping[str, str]],
) -> A2tPopFlightPlan:
    """Resolve R1's per-sample roster deterministically -- fail-closed if the
    registry has a duplicate/missing ``tool_name``, if ``r1_tool_names`` does
    not carry EXACTLY ``sample_ids``, or if any named tool is absent from the
    registry. ``r1_tool_names`` is the caller's own already-derived
    ``rails.probes.a2t_s2_flight.derive_a0_selected_tools`` output (module
    docstring: "the caller loads/derives, this module only resolves" split
    every sibling probe module already uses)."""

    registry_index: dict[str, Mapping[str, str]] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not name:
            raise A2tPopFlightError("registry row is missing tool_name")
        if name in registry_index:
            raise A2tPopFlightError(f"registry has a duplicate tool_name {name!r}")
        registry_index[name] = row

    ids = tuple(sorted(sample_ids))
    have = set(r1_tool_names)
    want = set(ids)
    if have != want:
        missing = want - have
        extra = have - want
        raise A2tPopFlightError(
            f"r1_tool_names does not match sample_ids exactly "
            f"(missing={sorted(missing)[:5]}, extra={sorted(extra)[:5]})"
        )
    for sample_id, names in r1_tool_names.items():
        if not names:
            raise A2tPopFlightError(f"sample {sample_id!r} carries no R1 tool name(s)")
        unknown = set(names) - registry_index.keys()
        if unknown:
            raise A2tPopFlightError(
                f"sample {sample_id!r} names tool(s) {sorted(unknown)} not present in the registry"
            )

    return A2tPopFlightPlan(
        sample_ids=ids,
        r1_tool_names_by_sample=dict(r1_tool_names),
        registry_index=registry_index,
    )


def build_flight_plan_from_attempt(
    sample_ids: Sequence[str], attempt_dir: Path, registry_rows: Sequence[Mapping[str, str]]
) -> A2tPopFlightPlan:
    """Convenience wrapper: derives R1's roster via
    ``rails.probes.a2t_s2_flight.derive_a0_selected_tools`` (reused directly,
    module docstring) over ``sample_ids`` from the SAME consumed A0 attempt,
    then resolves via :func:`build_flight_plan`."""

    r1_tool_names = derive_a0_selected_tools(Path(attempt_dir), sample_ids)
    return build_flight_plan(sample_ids, r1_tool_names, registry_rows)


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


def _supplied_tool_label(tool_names: Sequence[str]) -> str:
    """Mirrors ``rails.probes.a2t_s2b_flight._supplied_tool_label`` exactly
    (a private, module-scoped helper there; re-implemented here rather than
    imported across the module boundary, consistent with that module's own
    leading-underscore-stays-private convention): sorted, comma-joined tool
    names."""

    return ",".join(sorted(set(tool_names)))


@dataclass(frozen=True)
class A2tPopFlightSummary:
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


def run_a2t_pop_flight(
    *,
    adapter: Audio2ToolAdapter,
    core_client,
    samples: Sequence[Audio2ToolSample],
    plan: A2tPopFlightPlan,
    decoding_params: Mapping[str, object] | None = None,
    now: Callable[[], float] = time.time,
) -> A2tPopFlightSummary:
    """Execute the full two-arm whole-population regression flight: R0 then
    R1, one request per sample per arm, over ``plan.sample_ids`` sorted --
    mirrors ``rails.probes.a2t_s2b_flight.run_a2t_s2b_flight``'s own per-arm
    ordering discipline. ``core_client`` is duck-typed against
    ``rails.core_client.CoreClient`` (never imported/annotated directly --
    the same "no forced import" discipline the sibling probe flight modules
    already use)."""

    if not samples:
        raise A2tPopFlightError("run_a2t_pop_flight requires at least one sample")
    by_id = {sample.sample_id: sample for sample in samples}
    missing = set(plan.sample_ids) - set(by_id)
    if missing:
        raise A2tPopFlightError(
            f"plan names {len(missing)} sample id(s) not present in samples: {sorted(missing)[:5]}"
        )

    results: list[A2tS2ArmResult] = []

    for sample_id in plan.sample_ids:
        sample = by_id[sample_id]

        results.append(
            _complete_and_record(
                core_client,
                arm=R0_ARM,
                sample_id=sample_id,
                supplied_tool=None,
                messages=adapter.assemble_prompt(sample, None),
                decoding_params=decoding_params,
                now=now,
            )
        )

        r1_names = plan.r1_tool_names_by_sample[sample_id]
        r1_rows = [plan.registry_index[name] for name in r1_names]
        r1_block = render_b1_tool_schemas(r1_rows)
        results.append(
            _complete_and_record(
                core_client,
                arm=R1_ARM,
                sample_id=sample_id,
                supplied_tool=_supplied_tool_label(r1_names),
                messages=assemble_roster_prompt(sample, r1_block),
                decoding_params=decoding_params,
                now=now,
            )
        )

    return A2tPopFlightSummary(results=tuple(results))


__all__ = [
    "A2T_POP_ARMS",
    "DEFAULT_SEED",
    "EM_CORRECT_N",
    "R0_ARM",
    "R1_ARM",
    "SPLIT_IDENTITY_HASH",
    # Re-exported from rails.probes.a2t_s2_flight (a caller of this module
    # needs only this one import site).
    "A2tS2ArmResult",
    "assemble_roster_prompt",
    "derive_a0_selected_tools",
    "render_b1_tool_schemas",
    "result_to_json",
    "write_outputs_jsonl",
    "A2tPopFlightError",
    "A2tPopFlightPlan",
    "A2tPopFlightSummary",
    "HeadroomSource",
    "assert_split_identity_hash_pinned",
    "build_flight_plan",
    "build_flight_plan_from_attempt",
    "derive_em_correct_ids",
    "load_headroom_source",
    "run_a2t_pop_flight",
]
