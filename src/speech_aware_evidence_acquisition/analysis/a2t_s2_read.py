"""P-A2T Stage-2 supply-probe offline read suite (pinned, pre-registered).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written attempt's
``outputs.jsonl`` / ``{RUN_ID}.arm-plan.json`` / ``flight-receipt.json``
(``rails.probes.a2t_s2_flight.run_a2t_s2_flight`` / the flight launcher's
own write shape, see ``docs/checks/speech-aware-evidence-acquisition/
2026-08-18-a2t-s2-flight/launcher/launch_pa2t_s2.py``) through the SAME
frozen scorer primitives every other consumer of this carrier uses
(``reproduction.toolcall_scoring.score_item``/``aggregate``/
``parse_tool_calls_text``, ``data.audio2tool.load_expected_calls`` --
reused directly here, never re-derived).

Purpose (``docs/readiness/2026-08-18-pa2t-stage2-preregistration-
REGISTERED.md`` sections 3-4): on the 120 samples where the frozen core
already selects the correct tool (A0) but fails the full call, does
prompt-level supply of tool-schema knowledge convert failures into exact
matches -- and is the effect knowledge or format? This suite computes every
ingredient number section 3 names (per arm AND per tier -- pooled is never
the headline) and mechanically evaluates section 4's branch rules in the
registered order: VOID -> COPY-TRAP -> SCHEMA-ONLY -> SUPPLY-CONVERTS ->
INERT, with the DOSE point reported alongside as a secondary, descriptive
signal.

Sources of truth this module implements EXACTLY (never re-derives on its
own authority):

- ``reproduction.toolcall_scoring.score_item``/``aggregate`` for every
  per-row/per-arm tool_accuracy/exact_match/slot metric -- the SAME two
  calls ``rails.adapters.audio2tool.Audio2ToolAdapter.score`` itself makes
  internally (note 6 below explains why this module calls them directly
  rather than through that adapter's own wrapper).
- ``reproduction.toolcall_scoring.parse_tool_calls_text`` for the predicted
  tool-call list, and ``data.audio2tool.load_expected_calls`` for the
  scorer-side gold -- the SAME scorer-side-only discipline every other
  consumer of this carrier already applies.
- ``rails.probes.a2t_s2_flight``'s own arm-name constants
  (``S1P_ARM``/``S2_ARM``/``S4_ARM``/``N0R_ARM``/``A2T_S2_ARMS``/
  ``A2T_S2_SUPPLY_ARMS``/``HEADROOM_SCHEMA``) -- never a second, hand-typed
  spelling of an arm name.
- ``docs/readiness/2026-08-18-pa2t-stage2-preregistration-REGISTERED.md``
  sections 3 (metrics) and 4 (branch rules), with their bound thresholds
  quoted verbatim in each clause's own detail text below.

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried, because the
mission brief and the preregistration are genuinely underspecified on these
exact points -- each is a documented, reviewable choice, not a silent
guess):

1. Harness-defect checks (structurally malformed input AND cross-artifact
   consistency: row counts, arm counts, duplicate (arm, sample_id) pairs,
   the headroom-id set matching both ``{RUN_ID}.arm-plan.json`` and the
   frozen ``headroom.json``, the S4 derangement no-fixed-point recheck, and
   the flight receipt's own ``split_identity_hash`` against the frozen
   discovery-split probe receipt ``analysis.a2t_read._load_split_receipt``
   resolves) are ALL hard, fail-closed refusals (:class:`A2tS2ReadError`)
   raised BEFORE any scoring happens -- mirrors ``analysis.a2t_read``'s own
   convention (its module docstring note 2), not ``analysis.pslu_read``'s
   soft VOID-clause convention, because the mission's own "harness checks
   fail-closed" instruction and the preregistration's own section 4 VOID
   wording ("harness defect (completeness/duplicate/arm checks
   fail-closed)") both read the SAME way ``a2t_read`` already does: these
   are refusals, not a branch-rule outcome. The mechanical branch
   evaluator's own VOID case (:func:`evaluate_branch_rules`) is reserved
   purely for the one remaining, genuinely scored-data condition the
   preregistration names: N0r EM-flip rate > 25%.
2. Neither the arm-plan filename convention (``f"{RUN_ID}.arm-plan.json"``)
   nor ``RUN_ID`` itself is importable from library code -- both are
   defined only inside the archived, non-package flight launcher script
   (``docs/checks/.../launcher/flight_identity.py`` /
   ``launch_pa2t_s2.py``). ``RUN_ID`` is therefore re-stated here as a
   local constant (it also names the exposure-ledger row and the
   preregistration's own run id, so it is not at risk of silent drift);
   the arm-plan path itself stays overridable via the CLI for testability.
3. This suite deliberately does NOT reuse
   ``rails.probes.a2t_s2_flight.load_headroom_manifest`` (which hard-
   enforces exactly ``HEADROOM_N=120`` sample ids -- an OWNER RULING about
   what the FLIGHT is allowed to spend model calls on, not a generic
   read-time identity concern) to load the frozen ``headroom.json``. A read
   suite's job is to score and structurally validate whatever was actually
   flown, not re-assert a write-time spend ceiling; :func:`load_headroom_identity`
   reuses ONLY the public ``HEADROOM_SCHEMA`` constant and otherwise
   accepts any non-empty, duplicate-free ``sample_ids`` list. For the one
   real, pinned attempt this suite will eventually read, ``headroom.json``
   is 120 ids regardless (fixed upstream by that same owner ruling), so
   this changes nothing about the real read while keeping this module
   honestly testable against small synthetic fixtures.
4. For the identical reason, arm row-count expectations (S1p/S2/S4 ==
   ``len(headroom_ids)``, N0r == ``len(n0r_sample_ids)``, total ==
   ``3 * len(headroom_ids) + len(n0r_sample_ids)``) are derived from
   ``{RUN_ID}.arm-plan.json``'s own declared id lists, never hardcoded to
   "120"/"40"/"400" -- exactly ``analysis.a2t_read``'s own documented
   design principle ("never a hardcoded sample count ... enforces exact
   identity with whichever receipt it is pointed at"). For the real flight
   these numbers ARE 120/120/120/40/400 by construction (the arm plan is
   itself built under ``HEADROOM_N=120``/``N0R_TARGET_N=40``), so this
   distinction never bites the real read.
5. ``outputs.jsonl`` for this probe carries NO embedded metrics field at
   all (``rails.probes.a2t_s2_flight`` module docstring: "scoring is a
   SEPARATELY-registered later read mission's job" -- deliberately
   narrower than ``analysis.a2t_read``'s/``analysis.pslu_read``'s own row
   shape). There is therefore no recheck-mismatch section in this report:
   every number here is a first, fresh computation, never a cross-check
   against a flight-time value.
6. Per-row scoring calls ``reproduction.toolcall_scoring.score_item`` /
   ``parse_tool_calls_text`` and ``data.audio2tool.load_expected_calls``
   directly -- the exact three primitives
   ``rails.adapters.audio2tool.Audio2ToolAdapter.score`` itself calls
   internally -- rather than through that adapter's own wrapper, and
   ``reproduction.toolcall_scoring.aggregate`` (also public, unmodified)
   micro-sums the raw per-row ``ItemScore`` ingredients into each arm's
   slot precision/recall/F1, exactly the module's own documented
   aggregation convention ("corpus-level aggregation sums the raw counts
   across items (micro)"). ``Audio2ToolAdapter.score``'s own return value
   discards those raw counts (only the already-divided ratios survive),
   which would make a correct MICRO slot-F1 -- a mandatory section 3
   guardrail metric -- impossible to reconstruct without re-deriving it a
   second way; ``load_expected_calls`` is also called ONCE for the whole
   attempt rather than per row (``a2t_read``'s own adapter-per-row pattern
   reloads the receipt-scoped manifests on every call, a cost its own note
   6 explicitly flags but does not fix), since nothing here needs the
   adapter object at all.
7. "Induced-substitution" (mission brief: "supplied argument VALUES
   appearing in the predicted call where the aligned gold argument
   differs") is operationalized at ARGUMENT-KEY granularity, scoped to one
   sample's own row: the "aligned gold argument" for a predicted
   ``(argument_key, value)`` pair is the gold value(s) recorded under that
   SAME key across every gold ``ToolCall`` this sample carries (a bare-key
   alignment, deliberately NOT also scoped by tool name -- see below); a
   key with no gold entry at all for this sample has no aligned reference
   and is excluded (mirrors ``analysis.pslu_read``'s own
   ``count_induced_substitutions`` exclusion rule). Scoping ALSO by tool
   name (the way ``toolcall_scoring._slot_triples`` keys its own official
   Slot-F1 triples) was considered and rejected: S4 supplies exactly ONE
   tool's row, and that tool is BY CONSTRUCTION never the sample's own
   gold tool (the Sattolo derangement), so a ``(tool_name, key)``-scoped
   alignment would make S4's induced-substitution count structurally zero
   on every possible response -- silently disabling COPY-TRAP's own named
   disjunct for exactly the arm it exists to catch (a wrong tool's literal
   default value dragging the response toward IT). Key-only alignment
   stays low-risk in practice: it is evaluated per sample (typically 1-4
   gold calls) against that (arm, sample)'s own small supplied roster (1
   tool for S1p/S4, a handful for S2), never against the full 152-row
   registry at once. "Supplied argument VALUES" are read as the parsed
   ``argument_defaults`` column of the tool row(s) THIS (arm, sample)'s
   own arm-plan roster actually names (``s1p_tool_names`` /
   ``s2_tool_names`` / ``s4_tool_name``) -- never ``argument_constraints``,
   whose one surveyed real shape ("mode: [Home, Armed_Away]") is a
   free-text enumerated-type description with no fixed key=value grammar,
   unlike ``argument_defaults``' literal assignment shape
   ("deviceId='light_1'"), which parses with the SAME call-argument
   grammar ``reproduction.toolcall_gold._parse_kwargs`` already applies to
   gold call-strings (reused directly, wrapped in parentheses). N0r is not
   a supply arm (its request is byte-identical to A0's own full registry,
   no manipulation) -- its supplied-tool set is always empty, so its
   induced-substitution count is 0 by construction, mirroring
   ``analysis.pslu_read``'s own "A2 supplies no values ... 0 by
   construction" note.
8. A non-empty ``argument_defaults`` string that fails to parse under the
   reused grammar contributes zero supplied values for that row and is
   recorded as an informational, non-fatal warning in the report (never a
   hard refusal) -- undercounting a guardrail metric on a real 152-row
   registry shape this suite was never developed against is the fail-safe
   direction; refusing the whole read over one unfamiliar-but-benign
   registry cell is not.
9. COPY-TRAP's "induced-substitutions >= EM-flips" disjunct requires the
   EM-flip count to be strictly positive before it can fire, mirroring
   ``analysis.pslu_read``'s own module docstring note 9 (cited by this
   mission as the branch-evaluator pattern to reuse): a bare ">=" is
   vacuously true at 0 vs 0, which would make COPY-TRAP fire on every arm
   that converts nothing at all, colliding with the INERT branch the SAME
   rule set names for exactly that case.
10. Branch rules (section 4) are evaluated on POOLED (whole-arm) aggregates
    only -- the preregistration's own section 4 text names no tier-scoped
    variant of any clause. "PER-TIER REPORTING MANDATORY; pooled never the
    headline" (section 3) is read as a REPORTING obligation (the per-tier
    table always accompanies the pooled verdict, in both the JSON and the
    rendered report) rather than a second, tier-scoped branch evaluation
    the preregistration never defines. The four tiers carrying
    interpretive weight vs. the four thin, small-n-caveat tiers (section
    7) are flagged generically by each (arm, tier) cell's OWN row count
    against a >=16 threshold, never by a hardcoded tier-name list.
11. "Tool-selection retention" and "EM conversion rate" both reduce to an
    arm's raw mean ``tool_accuracy`` / ``exact_match``: the A0 baseline is
    fixed at ``tool_accuracy=1.0``, ``exact_match=0.0`` for every one of
    the headroom ids by that set's own defining criterion (no re-fly, no
    re-load of ``2026-08-18-pa2t-a0-read/verdict.json``'s own aggregate
    numbers is needed); N0r's "EM-flip rate" is the identical formula
    applied to its own zero-supply re-fly, and the preregistration's
    literal "1/40" noise-floor term is read as ``1 / (N0r's own arm
    size)`` -- identical to 1/40 for the real, pinned flight (N0r size
    fixed at ``N0R_TARGET_N=40``), while staying well-defined for a
    smaller synthetic N0r arm in this suite's own tests.

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_a2t_s2_read.py``). This module is never run against the
real flight attempt directory
(``$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/``) by the task that wrote
it; a later, separately-registered one-shot read session points
``build_a2t_s2_report``/the CLI at the real COMPLETED attempt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..reproduction.toolcall_scoring import ItemScore, ToolCall, aggregate, parse_tool_calls_text, score_item
from ..rails.probes.a2t_s2_flight import (
    A2T_S2_ARMS,
    A2T_S2_SUPPLY_ARMS,
    HEADROOM_SCHEMA,
    N0R_ARM,
    S1P_ARM,
    S2_ARM,
    S4_ARM,
)
from .a2t_read import is_empty_tool_call

REPORT_SCHEMA = "saea-a2t-s2-read-v1"
# Mirrors the (non-importable, archived-launcher) flight's own RUN_ID -- see
# note 2 above. Also names the exposure-ledger row / the preregistration's
# own run id.
RUN_ID = "SAEA-PROBE-a2t-s2-120"
DEFAULT_SPLIT_ROLE = "discovery"

INTERPRETIVE_WEIGHT_MIN_N = 16  # preregistration section 7

# Preregistration section 4 thresholds, quoted verbatim in each clause's own
# detail text below.
VOID_N0R_FLIP_CEILING = 0.25
COPY_TRAP_S4_RETENTION_FLOOR = 0.90
SUPPLY_CONVERTS_S1P_MIN = 0.15
SUPPLY_CONVERTS_S1P_RETENTION_FLOOR = 0.95
MIN_NOISE_FLOOR_PCT = 0.05  # the literal "5%" in max(2x noise, 5%)

ClauseVerdict = Literal["met", "not_met"]


class A2tS2ReadError(RuntimeError):
    """Malformed attempt-dir/arm-plan/headroom input, or a harness defect
    the mission's own "machine harness checks, fail-closed" requires
    refusing on -- never raised for an ordinary, structurally clean read."""


# ---------------------------------------------------------------------------
# Loading: outputs.jsonl / flight-receipt.json / {RUN_ID}.arm-plan.json /
# the frozen headroom.json.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutputRow:
    """Mirrors ``rails.probes.a2t_s2_flight.result_to_json``'s own row
    shape exactly: ``{arm, sample_id, supplied_tool, response, timing}`` --
    deliberately narrower than ``analysis.a2t_read``'s ``OutputRow`` (note
    5 above: no embedded ``messages``/``metrics``/``consumption``)."""

    arm: str
    sample_id: str
    supplied_tool: str | None
    response: str
    timing: Mapping[str, object]

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "OutputRow":
        return cls(
            arm=str(document["arm"]),
            sample_id=str(document["sample_id"]),
            supplied_tool=document.get("supplied_tool"),
            response=str(document["response"]),
            timing=document["timing"],
        )


def load_attempt_rows(attempt_dir: Path) -> tuple[tuple[OutputRow, ...], tuple[str, ...]]:
    """``(valid_rows, malformed_row_reasons)`` -- mirrors
    ``analysis.a2t_read.load_attempt_rows``'s own malformed-row-collection
    pattern exactly, over this probe's own (different) row shape."""

    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise A2tS2ReadError(f"no outputs.jsonl under attempt dir {attempt_dir}")
    rows: list[OutputRow] = []
    malformed: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
            if not isinstance(document, Mapping):
                raise ValueError(f"row must be a JSON object, got {type(document).__name__}")
            row = OutputRow.from_json(document)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            malformed.append(f"outputs.jsonl line {line_no}: malformed row: {error!r}")
            continue
        rows.append(row)
    if not rows and not malformed:
        raise A2tS2ReadError(f"{path}: zero rows")
    return tuple(rows), tuple(malformed)


def load_flight_receipt(attempt_dir: Path) -> Mapping[str, object] | None:
    """``None`` when the file is missing entirely (itself a harness defect:
    the launcher writes this file unconditionally once it starts)."""

    path = Path(attempt_dir) / "flight-receipt.json"
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise A2tS2ReadError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(document, Mapping):
        raise A2tS2ReadError(f"{path}: must be a JSON object")
    return document


@dataclass(frozen=True)
class ArmPlan:
    """``{RUN_ID}.arm-plan.json`` -- the flight's own seeded, precomputed
    per-sample roster (``rails.probes.a2t_s2_flight.launch_pa2t_s2``'s own
    write, see the flight archive's README "For the read mission" section).
    No production loader exists for this file (note 2 above); this
    dataclass/loader is this suite's own, structurally strict parse."""

    seed: int
    headroom_ids: tuple[str, ...]
    n0r_sample_ids: tuple[str, ...]
    selected_tools: Mapping[str, tuple[str, ...]]
    s1p_tool_names: Mapping[str, tuple[str, ...]]
    s2_tool_names: Mapping[str, tuple[str, ...]]
    s4_derangement: Mapping[str, str]
    s4_tool_name: Mapping[str, str]


def _id_list(document: Mapping[str, object], key: str, path: Path) -> tuple[str, ...]:
    raw = document.get(key)
    if not isinstance(raw, list) or not raw or not all(isinstance(x, str) for x in raw):
        raise A2tS2ReadError(f"{path}: {key!r} must be a non-empty list of strings")
    if len(set(raw)) != len(raw):
        raise A2tS2ReadError(f"{path}: {key!r} contains duplicate id(s)")
    return tuple(raw)


def _str_tuple_map(document: Mapping[str, object], key: str, path: Path) -> dict[str, tuple[str, ...]]:
    raw = document.get(key)
    if not isinstance(raw, Mapping):
        raise A2tS2ReadError(f"{path}: {key!r} must be an object")
    result: dict[str, tuple[str, ...]] = {}
    for sample_id, names in raw.items():
        if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
            raise A2tS2ReadError(f"{path}: {key!r}[{sample_id!r}] must be a non-empty list of strings")
        result[str(sample_id)] = tuple(names)
    return result


def _str_str_map(document: Mapping[str, object], key: str, path: Path) -> dict[str, str]:
    raw = document.get(key)
    if not isinstance(raw, Mapping) or not all(isinstance(v, str) for v in raw.values()):
        raise A2tS2ReadError(f"{path}: {key!r} must be an object of string -> string")
    return {str(k): str(v) for k, v in raw.items()}


def load_arm_plan(path: Path) -> ArmPlan:
    path = Path(path)
    if not path.is_file():
        raise A2tS2ReadError(f"arm-plan.json missing: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise A2tS2ReadError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(document, Mapping):
        raise A2tS2ReadError(f"{path}: must be a JSON object")

    seed = document.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise A2tS2ReadError(f"{path}: 'seed' must be an int")

    return ArmPlan(
        seed=seed,
        headroom_ids=_id_list(document, "headroom_ids", path),
        n0r_sample_ids=_id_list(document, "n0r_sample_ids", path),
        selected_tools=_str_tuple_map(document, "selected_tools", path),
        s1p_tool_names=_str_tuple_map(document, "s1p_tool_names", path),
        s2_tool_names=_str_tuple_map(document, "s2_tool_names", path),
        s4_derangement=_str_str_map(document, "s4_derangement", path),
        s4_tool_name=_str_str_map(document, "s4_tool_name", path),
    )


@dataclass(frozen=True)
class HeadroomIdentity:
    """The frozen 120-id Stage-2 headroom list
    (``docs/checks/.../2026-08-18-pa2t-a0-read/headroom.json``), read
    LENIENTLY (note 3 above: no ``==120`` gate, unlike the flight's own
    ``load_headroom_manifest``) -- used here purely to bind sample
    identity."""

    sample_ids: tuple[str, ...]
    attempt_dir: str | None


def load_headroom_identity(path: Path) -> HeadroomIdentity:
    path = Path(path)
    if not path.is_file():
        raise A2tS2ReadError(f"headroom manifest missing: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise A2tS2ReadError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(document, Mapping):
        raise A2tS2ReadError(f"{path}: must be a JSON object")
    if document.get("schema") != HEADROOM_SCHEMA:
        raise A2tS2ReadError(f"{path}: schema must be {HEADROOM_SCHEMA!r}, got {document.get('schema')!r}")
    sample_ids = _id_list(document, "sample_ids", path)
    attempt_dir = document.get("attempt_dir")
    return HeadroomIdentity(
        sample_ids=tuple(sorted(sample_ids)),
        attempt_dir=attempt_dir if isinstance(attempt_dir, str) else None,
    )


def _tier_of(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


# ---------------------------------------------------------------------------
# Registry parsing: argument_defaults -> supplied argument VALUES (note 7).
# ---------------------------------------------------------------------------


def parse_argument_defaults(tool_name: str, defaults_text: str) -> tuple[dict[str, object], str | None]:
    """``(kwargs, warning)`` -- note 7/8: reuses
    ``reproduction.toolcall_gold._parse_kwargs`` (the SAME call-argument
    grammar gold call-strings already parse under) by wrapping the defaults
    text in parentheses. ``{}``/``None`` for blank text; ``{}``/a warning
    string for non-blank text that fails to parse (never a hard
    refusal -- note 8)."""

    from ..reproduction.toolcall_gold import _parse_kwargs

    text = defaults_text.strip()
    if not text:
        return {}, None
    kwargs = _parse_kwargs(f"({text})")
    if kwargs is None:
        return (
            {},
            f"tool {tool_name!r}: argument_defaults {defaults_text!r} did not parse as key=value "
            "assignment(s); contributing zero supplied values for this row (informational, non-fatal)",
        )
    return kwargs, None


def supplied_argument_values(
    tool_names: Sequence[str], registry_index: Mapping[str, Mapping[str, str]]
) -> tuple[dict[str, set], tuple[str, ...]]:
    """``{argument_key: {canonical_value, ...}}`` for every tool this (arm,
    sample)'s own arm-plan roster names -- KEY-only, deliberately not also
    scoped by tool name (note 7 explains why), plus any non-fatal parse
    warnings (note 8)."""

    from ..reproduction.toolcall_scoring import _canonical_value

    values: dict[str, set] = {}
    warnings: list[str] = []
    for name in tool_names:
        row = registry_index.get(name)
        if row is None:
            warnings.append(f"tool {name!r} is named in the arm plan but absent from the loaded registry")
            continue
        kwargs, warning = parse_argument_defaults(name, row.get("argument_defaults", ""))
        if warning:
            warnings.append(warning)
        for key, value in kwargs.items():
            values.setdefault(key, set()).add(_canonical_value(value))
    return values, tuple(warnings)


def count_induced_substitutions(
    predicted: Sequence[ToolCall],
    expected: Sequence[ToolCall],
    supplied_values: Mapping[str, set],
) -> int:
    """Note 7, mission brief verbatim: "supplied argument VALUES appearing
    in the predicted call where the aligned gold argument differs" --
    aligned by argument KEY only, across every gold call this sample
    carries (note 7 explains why tool-name scoping was rejected)."""

    from ..reproduction.toolcall_scoring import _canonical_value

    gold_map: dict[str, set] = {}
    for call in expected:
        for key, value in call.arguments.items():
            gold_map.setdefault(key, set()).add(_canonical_value(value))

    count = 0
    for call in predicted:
        for key, value in call.arguments.items():
            gold_values = gold_map.get(key)
            if gold_values is None:
                continue  # no aligned gold argument -- excluded (note 7)
            predicted_canonical = _canonical_value(value)
            if predicted_canonical in gold_values:
                continue  # matches gold -- not a divergence
            if predicted_canonical in supplied_values.get(key, ()):
                count += 1
    return count


def _supplied_tool_names_for_row(row: OutputRow, arm_plan: ArmPlan) -> tuple[str, ...]:
    if row.arm == S1P_ARM:
        return arm_plan.s1p_tool_names.get(row.sample_id, ())
    if row.arm == S2_ARM:
        return arm_plan.s2_tool_names.get(row.sample_id, ())
    if row.arm == S4_ARM:
        name = arm_plan.s4_tool_name.get(row.sample_id)
        return (name,) if name else ()
    return ()  # N0r: not a supply arm (note 7) -- always empty by construction


# ---------------------------------------------------------------------------
# Per-row scoring (note 6: score_item/parse_tool_calls_text/
# load_expected_calls reused directly).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RowScore:
    row: OutputRow
    tier: str
    item: ItemScore
    parsed: bool
    empty_tool_call: bool
    induced_substitutions: int
    registry_warnings: tuple[str, ...]


def score_row(
    row: OutputRow,
    *,
    expected_by_id: Mapping[str, tuple[ToolCall, ...]],
    registry_index: Mapping[str, Mapping[str, str]],
    supplied_tool_names: Sequence[str],
) -> RowScore:
    predicted, parsed = parse_tool_calls_text(row.response)
    expected = expected_by_id[row.sample_id]
    item = score_item(expected, predicted)
    supplied_values, warnings = supplied_argument_values(supplied_tool_names, registry_index)
    induced = count_induced_substitutions(predicted, expected, supplied_values)
    return RowScore(
        row=row,
        tier=_tier_of(row.sample_id),
        item=item,
        parsed=parsed,
        empty_tool_call=is_empty_tool_call(row.response),
        induced_substitutions=induced,
        registry_warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Harness-defect checks (note 1: fail-closed refusal, never a soft flag).
# ---------------------------------------------------------------------------


def _harness_defect_reasons(
    *,
    malformed_row_reasons: Sequence[str],
    flight_receipt: Mapping[str, object] | None,
    rows_by_arm: Mapping[str, Sequence[OutputRow]],
    unknown_arm_rows: Sequence[OutputRow],
    duplicate_pairs: Sequence[tuple[str, str]],
    arm_plan: ArmPlan,
    headroom_identity: HeadroomIdentity,
    split_identity_hash: str,
    expected_by_id: Mapping[str, tuple[ToolCall, ...]],
) -> tuple[str, ...]:
    reasons: list[str] = list(malformed_row_reasons)

    if flight_receipt is None:
        reasons.append("flight-receipt.json missing")
    else:
        status = flight_receipt.get("status")
        if status != "COMPLETED":
            reasons.append(
                f"flight-receipt status={status!r} (expected 'COMPLETED'); error={flight_receipt.get('error')!r}"
            )
        failures = flight_receipt.get("request_failures")
        if failures:
            reasons.append(f"flight-receipt request_failures non-empty: {len(failures)} failure(s)")
        arms = flight_receipt.get("arms")
        if arms != list(A2T_S2_ARMS):
            reasons.append(f"flight-receipt arms={arms!r}, expected {list(A2T_S2_ARMS)!r}")
        receipt_hash = flight_receipt.get("split_identity_hash")
        if receipt_hash != split_identity_hash:
            reasons.append(
                f"split_identity_hash mismatch: flight-receipt={receipt_hash!r} "
                f"vs. frozen probe receipt={split_identity_hash!r}"
            )

    for row in unknown_arm_rows:
        reasons.append(f"row on unknown arm {row.arm!r} (sample {row.sample_id!r})")
    for pair in duplicate_pairs:
        reasons.append(f"duplicate row for (arm, sample_id)={pair!r}")

    headroom_set = set(headroom_identity.sample_ids)
    arm_plan_headroom_set = set(arm_plan.headroom_ids)
    if arm_plan_headroom_set != headroom_set:
        missing = headroom_set - arm_plan_headroom_set
        extra = arm_plan_headroom_set - headroom_set
        reasons.append(
            "arm-plan headroom_ids does not match the frozen headroom manifest's sample_ids "
            f"(missing={sorted(missing)[:5]}, extra={sorted(extra)[:5]})"
        )

    n0r_set = set(arm_plan.n0r_sample_ids)
    if not n0r_set <= arm_plan_headroom_set:
        reasons.append(
            f"arm-plan n0r_sample_ids is not a subset of headroom_ids: "
            f"{sorted(n0r_set - arm_plan_headroom_set)[:5]}"
        )

    for key, mapping in (
        ("selected_tools", arm_plan.selected_tools),
        ("s1p_tool_names", arm_plan.s1p_tool_names),
        ("s2_tool_names", arm_plan.s2_tool_names),
        ("s4_tool_name", arm_plan.s4_tool_name),
    ):
        keys = set(mapping)
        if keys != arm_plan_headroom_set:
            reasons.append(
                f"arm-plan {key!r} key set does not match headroom_ids exactly "
                f"(missing={sorted(arm_plan_headroom_set - keys)[:5]}, extra={sorted(keys - arm_plan_headroom_set)[:5]})"
            )

    fixed_points = sorted(tool for tool, deranged in arm_plan.s4_derangement.items() if tool == deranged)
    if fixed_points:
        reasons.append(f"arm-plan s4_derangement has fixed point(s) (tool maps to itself): {fixed_points[:5]}")

    expected_counts = {
        S1P_ARM: len(arm_plan.headroom_ids),
        S2_ARM: len(arm_plan.headroom_ids),
        S4_ARM: len(arm_plan.headroom_ids),
        N0R_ARM: len(arm_plan.n0r_sample_ids),
    }
    total_rows = sum(len(rows) for rows in rows_by_arm.values()) + len(unknown_arm_rows)
    expected_total = sum(expected_counts.values())
    if total_rows != expected_total:
        reasons.append(
            f"total row count {total_rows} != expected {expected_total} "
            f"(3 x len(headroom_ids) + len(n0r_sample_ids))"
        )

    for arm in A2T_S2_ARMS:
        rows = rows_by_arm.get(arm, ())
        got_ids = [row.sample_id for row in rows]
        if len(got_ids) != len(set(got_ids)):
            dupes = sorted({sid for sid in got_ids if got_ids.count(sid) > 1})
            reasons.append(f"arm {arm}: duplicate sample_id row(s) within the arm: {dupes[:5]}")
        if len(rows) != expected_counts[arm]:
            reasons.append(f"arm {arm}: row count {len(rows)} != expected {expected_counts[arm]}")
        want_ids = set(arm_plan.headroom_ids) if arm != N0R_ARM else set(arm_plan.n0r_sample_ids)
        got_set = set(got_ids)
        missing = want_ids - got_set
        extra = got_set - want_ids
        if missing:
            reasons.append(f"arm {arm}: missing {len(missing)} sample id(s): {sorted(missing)[:5]}")
        if extra:
            reasons.append(f"arm {arm}: {len(extra)} sample id(s) not in its own expected set: {sorted(extra)[:5]}")

    missing_gold = sorted(sid for sid in arm_plan.headroom_ids if sid not in expected_by_id)
    if missing_gold:
        reasons.append(
            f"{len(missing_gold)} headroom sample id(s) have no resolvable gold via load_expected_calls: "
            f"{missing_gold[:5]}"
        )

    return tuple(reasons)


# ---------------------------------------------------------------------------
# Per-arm / per-tier aggregation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmAggregate:
    arm: str
    n_samples: int
    tool_accuracy: float  # == tool-selection retention
    em_conversion_rate: float  # == EM conversion / EM-flip rate (note 11)
    em_flip_count: int
    slot_precision: float
    slot_recall: float
    slot_f1: float
    empty_call_rate: float
    parse_failure_rate: float
    induced_substitution_count: int
    interpretive_weight: bool  # note 10: n_samples >= INTERPRETIVE_WEIGHT_MIN_N


def build_arm_aggregate(arm: str, scores: Sequence[RowScore]) -> ArmAggregate:
    n = len(scores)
    agg = aggregate([s.item for s in scores])
    empty_count = sum(1 for s in scores if s.empty_tool_call)
    parse_failures = sum(1 for s in scores if not s.parsed)
    em_flip_count = sum(1 for s in scores if s.item.exact_match == 1.0)
    induced_total = sum(s.induced_substitutions for s in scores)
    return ArmAggregate(
        arm=arm,
        n_samples=n,
        tool_accuracy=agg.tool_accuracy,
        em_conversion_rate=agg.exact_match,
        em_flip_count=em_flip_count,
        slot_precision=agg.slot_precision,
        slot_recall=agg.slot_recall,
        slot_f1=agg.slot_f1,
        empty_call_rate=(empty_count / n) if n else 0.0,
        parse_failure_rate=(parse_failures / n) if n else 0.0,
        induced_substitution_count=induced_total,
        interpretive_weight=n >= INTERPRETIVE_WEIGHT_MIN_N,
    )


@dataclass(frozen=True)
class PerArmReport:
    overall: ArmAggregate
    by_tier: Mapping[str, ArmAggregate]


# ---------------------------------------------------------------------------
# Mechanical branch-rule evaluator (section 4, quoted verbatim below).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClauseResult:
    clause_text: str
    verdict: ClauseVerdict
    detail: str


@dataclass(frozen=True)
class BranchVerdict:
    noise_floor: float
    conversion_floor: float
    void_clause: ClauseResult
    voided: bool
    copy_trap_clauses: tuple[ClauseResult, ...]
    copy_trap: bool
    schema_only_clauses: tuple[ClauseResult, ...]
    schema_only: bool
    supply_converts_clauses: tuple[ClauseResult, ...]
    supply_converts: bool
    inert_clause: ClauseResult
    inert: bool
    dose_point: ClauseResult
    overall: str


def evaluate_branch_rules(per_arm: Mapping[str, PerArmReport]) -> BranchVerdict:
    """The mechanical evaluator, checked in the REGISTERED order: VOID,
    COPY-TRAP, SCHEMA-ONLY, SUPPLY-CONVERTS, INERT (note 10: on POOLED
    arm-level aggregates only). DOSE point is secondary/descriptive and
    never competes with the primary branch."""

    s1p = per_arm[S1P_ARM].overall
    s2 = per_arm[S2_ARM].overall
    s4 = per_arm[S4_ARM].overall
    n0r = per_arm[N0R_ARM].overall

    noise_floor = max(n0r.em_conversion_rate, (1.0 / n0r.n_samples) if n0r.n_samples else 1.0)
    floor = max(2 * noise_floor, MIN_NOISE_FLOOR_PCT)

    void_clause = ClauseResult(
        "N0r EM-flip rate > 25% (unstable A0 comparator)",
        "met" if n0r.em_conversion_rate > VOID_N0R_FLIP_CEILING else "not_met",
        f"N0r EM-flip rate={n0r.em_conversion_rate:.4f} ({n0r.em_flip_count}/{n0r.n_samples}), "
        f"ceiling={VOID_N0R_FLIP_CEILING:.2f}",
    )
    voided = void_clause.verdict == "met"

    copy_trap_clauses: list[ClauseResult] = []
    for arm_name in A2T_S2_SUPPLY_ARMS:
        agg = per_arm[arm_name].overall
        fires = agg.em_flip_count > 0 and agg.induced_substitution_count >= agg.em_flip_count
        copy_trap_clauses.append(
            ClauseResult(
                f"{arm_name}: induced-substitutions >= EM-flips",
                "met" if fires else "not_met",
                "note 9 (requires EM-flip count > 0 -- a bare >= is vacuous at 0 vs 0): "
                f"induced={agg.induced_substitution_count}, em_flips={agg.em_flip_count}",
            )
        )
    copy_trap_clauses.append(
        ClauseResult(
            "S4 tool-selection retention < 90%",
            "met" if s4.tool_accuracy < COPY_TRAP_S4_RETENTION_FLOOR else "not_met",
            f"S4 tool_accuracy={s4.tool_accuracy:.4f} ({s4.n_samples} samples), "
            f"floor={COPY_TRAP_S4_RETENTION_FLOOR:.2f}",
        )
    )
    copy_trap = (not voided) and any(c.verdict == "met" for c in copy_trap_clauses)

    schema_only_clauses = (
        ClauseResult(
            "|S1' conversion - S4 conversion| <= 2x noise floor",
            "met" if abs(s1p.em_conversion_rate - s4.em_conversion_rate) <= 2 * noise_floor else "not_met",
            f"S1'={s1p.em_conversion_rate:.4f}, S4={s4.em_conversion_rate:.4f}, "
            f"|diff|={abs(s1p.em_conversion_rate - s4.em_conversion_rate):.4f}, 2xnoise={2 * noise_floor:.4f}",
        ),
        ClauseResult(
            "both S1' and S4 conversion >= max(2x noise, 5%)",
            "met" if (s1p.em_conversion_rate >= floor and s4.em_conversion_rate >= floor) else "not_met",
            f"S1'={s1p.em_conversion_rate:.4f}, S4={s4.em_conversion_rate:.4f}, floor={floor:.4f}",
        ),
    )
    schema_only = (not voided) and (not copy_trap) and all(c.verdict == "met" for c in schema_only_clauses)

    supply_converts_clauses = (
        ClauseResult(
            "S1' conversion >= 15% of 120",
            "met" if s1p.em_conversion_rate >= SUPPLY_CONVERTS_S1P_MIN else "not_met",
            f"S1'={s1p.em_conversion_rate:.4f}, floor={SUPPLY_CONVERTS_S1P_MIN:.2f}",
        ),
        ClauseResult(
            "S4 conversion <= max(2x noise, 5%)",
            "met" if s4.em_conversion_rate <= floor else "not_met",
            f"S4={s4.em_conversion_rate:.4f}, ceiling={floor:.4f}",
        ),
        ClauseResult(
            "S1' tool-selection retention >= 95%",
            "met" if s1p.tool_accuracy >= SUPPLY_CONVERTS_S1P_RETENTION_FLOOR else "not_met",
            f"S1' tool_accuracy={s1p.tool_accuracy:.4f}, floor={SUPPLY_CONVERTS_S1P_RETENTION_FLOOR:.2f}",
        ),
    )
    supply_converts = (
        (not voided)
        and (not copy_trap)
        and (not schema_only)
        and all(c.verdict == "met" for c in supply_converts_clauses)
    )

    inert_clause = ClauseResult(
        "every supply arm conversion < max(2x noise, 5%)",
        "met" if all(agg.em_conversion_rate < floor for agg in (s1p, s2, s4)) else "not_met",
        f"S1'={s1p.em_conversion_rate:.4f}, S2={s2.em_conversion_rate:.4f}, S4={s4.em_conversion_rate:.4f}, "
        f"floor={floor:.4f}",
    )
    inert = (
        (not voided)
        and (not copy_trap)
        and (not schema_only)
        and (not supply_converts)
        and inert_clause.verdict == "met"
    )

    dose_point = ClauseResult(
        "S2 underperforms S1' (dilution to K=9 costs conversion; secondary, descriptive)",
        "met" if s2.em_conversion_rate < s1p.em_conversion_rate else "not_met",
        f"S2={s2.em_conversion_rate:.4f}, S1'={s1p.em_conversion_rate:.4f}",
    )

    if voided:
        overall = "VOID"
    elif copy_trap:
        overall = "COPY-TRAP"
    elif schema_only:
        overall = "SCHEMA-ONLY"
    elif supply_converts:
        overall = "SUPPLY-CONVERTS"
    elif inert:
        overall = "INERT"
    else:
        overall = "UNRESOLVED (no branch rule fired mechanically)"
    if dose_point.verdict == "met":
        overall += " + DOSE point (secondary, descriptive)"

    return BranchVerdict(
        noise_floor=noise_floor,
        conversion_floor=floor,
        void_clause=void_clause,
        voided=voided,
        copy_trap_clauses=tuple(copy_trap_clauses),
        copy_trap=copy_trap,
        schema_only_clauses=schema_only_clauses,
        schema_only=schema_only,
        supply_converts_clauses=supply_converts_clauses,
        supply_converts=supply_converts,
        inert_clause=inert_clause,
        inert=inert,
        dose_point=dose_point,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2ReadReport:
    attempt_dir: Path
    flight_status: str | None
    split_identity_hash: str
    arm_plan_path: Path
    headroom_path: Path
    per_arm: Mapping[str, PerArmReport]
    branch_verdict: BranchVerdict
    registry_warnings: tuple[str, ...]


def build_a2t_s2_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    headroom_path: Path,
    arm_plan_path: Path | None = None,
    split_role: str = DEFAULT_SPLIT_ROLE,
) -> A2tS2ReadReport:
    attempt_dir = Path(attempt_dir)
    repo_root = Path(repo_root)
    resolved_arm_plan_path = Path(arm_plan_path) if arm_plan_path else attempt_dir / f"{RUN_ID}.arm-plan.json"

    from ..data.audio2tool import load_expected_calls, load_tool_registry
    from .a2t_read import _load_split_receipt

    rows, malformed_row_reasons = load_attempt_rows(attempt_dir)
    flight_receipt = load_flight_receipt(attempt_dir)
    headroom_identity = load_headroom_identity(headroom_path)
    arm_plan = load_arm_plan(resolved_arm_plan_path)

    split_receipt = _load_split_receipt(repo_root, split_role)
    split_identity_hash = str(split_receipt["split_identity_hash"])

    expected_by_id = load_expected_calls(lock, root, repo_root=repo_root)
    registry_index = {row["tool_name"]: row for row in load_tool_registry(lock, root)}

    rows_by_arm: dict[str, list[OutputRow]] = {arm: [] for arm in A2T_S2_ARMS}
    unknown_arm_rows: list[OutputRow] = []
    duplicate_pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        pair = (row.arm, row.sample_id)
        if pair in seen:
            duplicate_pairs.append(pair)
            continue
        seen.add(pair)
        if row.arm not in A2T_S2_ARMS:
            unknown_arm_rows.append(row)
            continue
        rows_by_arm[row.arm].append(row)

    defect_reasons = _harness_defect_reasons(
        malformed_row_reasons=malformed_row_reasons,
        flight_receipt=flight_receipt,
        rows_by_arm=rows_by_arm,
        unknown_arm_rows=unknown_arm_rows,
        duplicate_pairs=duplicate_pairs,
        arm_plan=arm_plan,
        headroom_identity=headroom_identity,
        split_identity_hash=split_identity_hash,
        expected_by_id=expected_by_id,
    )
    if defect_reasons:
        raise A2tS2ReadError(
            "harness defect(s) detected; refusing to score:\n  " + "\n  ".join(defect_reasons)
        )

    per_arm: dict[str, PerArmReport] = {}
    all_warnings: list[str] = []
    for arm in A2T_S2_ARMS:
        scores = []
        for row in sorted(rows_by_arm[arm], key=lambda r: r.sample_id):
            supplied_names = _supplied_tool_names_for_row(row, arm_plan)
            score = score_row(
                row,
                expected_by_id=expected_by_id,
                registry_index=registry_index,
                supplied_tool_names=supplied_names,
            )
            scores.append(score)
            all_warnings.extend(score.registry_warnings)

        scores_by_tier: dict[str, list[RowScore]] = {}
        for score in scores:
            scores_by_tier.setdefault(score.tier, []).append(score)
        per_arm[arm] = PerArmReport(
            overall=build_arm_aggregate(arm, scores),
            by_tier={
                tier: build_arm_aggregate(arm, tier_scores)
                for tier, tier_scores in sorted(scores_by_tier.items())
            },
        )

    branch_verdict = evaluate_branch_rules(per_arm)

    return A2tS2ReadReport(
        attempt_dir=attempt_dir,
        flight_status=None if flight_receipt is None else flight_receipt.get("status"),
        split_identity_hash=split_identity_hash,
        arm_plan_path=resolved_arm_plan_path,
        headroom_path=Path(headroom_path),
        per_arm=per_arm,
        branch_verdict=branch_verdict,
        registry_warnings=tuple(sorted(set(all_warnings))),
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _arm_aggregate_json(agg: ArmAggregate) -> dict[str, object]:
    return {
        "arm": agg.arm,
        "n_samples": agg.n_samples,
        "tool_selection_retention": agg.tool_accuracy,
        "em_conversion_rate": agg.em_conversion_rate,
        "em_flip_count": agg.em_flip_count,
        "slot_precision": agg.slot_precision,
        "slot_recall": agg.slot_recall,
        "slot_f1": agg.slot_f1,
        "empty_call_rate": agg.empty_call_rate,
        "parse_failure_rate": agg.parse_failure_rate,
        "induced_substitution_count": agg.induced_substitution_count,
        "interpretive_weight": agg.interpretive_weight,
    }


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def report_to_json(report: A2tS2ReadReport) -> dict[str, object]:
    verdict = report.branch_verdict
    return {
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "split_identity_hash": report.split_identity_hash,
        "arm_plan_path": str(report.arm_plan_path),
        "headroom_path": str(report.headroom_path),
        "registry_defaults_parse_warnings": list(report.registry_warnings),
        "per_arm": {
            arm: {
                "overall": _arm_aggregate_json(per_arm_report.overall),
                "by_tier": {
                    tier: _arm_aggregate_json(agg) for tier, agg in per_arm_report.by_tier.items()
                },
            }
            for arm, per_arm_report in report.per_arm.items()
        },
        "branch_verdict": {
            "noise_floor": verdict.noise_floor,
            "conversion_floor": verdict.conversion_floor,
            "void_clause": _clause_json(verdict.void_clause),
            "voided": verdict.voided,
            "copy_trap_clauses": [_clause_json(c) for c in verdict.copy_trap_clauses],
            "copy_trap": verdict.copy_trap,
            "schema_only_clauses": [_clause_json(c) for c in verdict.schema_only_clauses],
            "schema_only": verdict.schema_only,
            "supply_converts_clauses": [_clause_json(c) for c in verdict.supply_converts_clauses],
            "supply_converts": verdict.supply_converts,
            "inert_clause": _clause_json(verdict.inert_clause),
            "inert": verdict.inert,
            "dose_point": _clause_json(verdict.dose_point),
            "overall": verdict.overall,
        },
    }


def render_report(report: A2tS2ReadReport) -> str:
    verdict = report.branch_verdict
    lines = [
        "P-A2T Stage-2 supply-probe pinned offline read "
        "(docs/readiness/2026-08-18-pa2t-stage2-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r}",
        f"split identity hash: {report.split_identity_hash}",
        f"arm plan: {report.arm_plan_path}",
        f"headroom manifest: {report.headroom_path}",
        "",
        "Per-arm aggregates (pooled)",
    ]
    header = (
        f"  {'arm':<6}{'n':>4}{'retention':>11}{'conv_rate':>11}{'em_flips':>9}"
        f"{'slot_f1':>9}{'empty':>7}{'parse_fail':>11}{'induced':>9}"
    )
    lines.append(header)
    for arm in A2T_S2_ARMS:
        agg = report.per_arm[arm].overall
        lines.append(
            f"  {arm:<6}{agg.n_samples:>4}{agg.tool_accuracy:>11.4f}{agg.em_conversion_rate:>11.4f}"
            f"{agg.em_flip_count:>9}{agg.slot_f1:>9.4f}{agg.empty_call_rate:>7.4f}"
            f"{agg.parse_failure_rate:>11.4f}{agg.induced_substitution_count:>9}"
        )
    lines.append("")

    lines.append("Per-tier breakdown (PER-TIER REPORTING MANDATORY -- pooled is never the headline)")
    for arm in A2T_S2_ARMS:
        lines.append(f"  arm {arm}:")
        for tier in sorted(report.per_arm[arm].by_tier):
            agg = report.per_arm[arm].by_tier[tier]
            weight = "interpretive-weight" if agg.interpretive_weight else "small-n caveat"
            lines.append(
                f"    {tier:<22}{agg.n_samples:>4} conv_rate={agg.em_conversion_rate:.4f} "
                f"retention={agg.tool_accuracy:.4f} slot_f1={agg.slot_f1:.4f} induced={agg.induced_substitution_count} "
                f"({weight})"
            )
    lines.append("")

    if report.registry_warnings:
        lines.append(f"registry_defaults parse warnings (informational, non-fatal): {len(report.registry_warnings)}")
        for warning in report.registry_warnings[:10]:
            lines.append(f"  {warning}")
        if len(report.registry_warnings) > 10:
            lines.append(f"  ... (+{len(report.registry_warnings) - 10} more)")
        lines.append("")

    lines.append(f"noise floor: {verdict.noise_floor:.4f}  conversion floor (max(2x noise, 5%)): {verdict.conversion_floor:.4f}")
    lines.append("")

    lines.append(f"VOID (checked FIRST): {'MET' if verdict.voided else 'not met'}")
    lines.append(f"  [{verdict.void_clause.verdict.upper():>8}] {verdict.void_clause.clause_text}")
    lines.append(f"           {verdict.void_clause.detail}")
    lines.append("")

    lines.append(f"COPY-TRAP: {'MET' if verdict.copy_trap else 'not met'}")
    for clause in verdict.copy_trap_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append("")

    lines.append(f"SCHEMA-ONLY: {'MET' if verdict.schema_only else 'not met'}")
    for clause in verdict.schema_only_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append("")

    lines.append(f"SUPPLY-CONVERTS: {'MET' if verdict.supply_converts else 'not met'}")
    for clause in verdict.supply_converts_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append("")

    lines.append(f"INERT: {'MET' if verdict.inert else 'not met'}")
    lines.append(f"  [{verdict.inert_clause.verdict.upper():>8}] {verdict.inert_clause.clause_text}")
    lines.append(f"           {verdict.inert_clause.detail}")
    lines.append("")

    lines.append(f"DOSE point (secondary, descriptive): {verdict.dose_point.verdict.upper()}")
    lines.append(f"  {verdict.dose_point.detail}")
    lines.append("")

    lines.append(f"OVERALL: {verdict.overall}")
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="a2t-s2-read",
        description=(
            "P-A2T Stage-2 supply-probe pinned offline read suite: per-arm and per-tier "
            "EM-conversion/tool-selection-retention/slot-P-R-F1/empty-call/induced-substitution/"
            "parse-failure metrics and the mechanical VOID/COPY-TRAP/SCHEMA-ONLY/SUPPLY-CONVERTS/"
            "INERT branch evaluator. Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the flight's own attempt directory (carries outputs.jsonl)")
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write verdict.json / report.txt")
    parser.add_argument(
        "--headroom-manifest", type=Path, default=None,
        help="override headroom.json's path (default: docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-18-pa2t-a0-read/headroom.json)",
    )
    parser.add_argument(
        "--arm-plan", type=Path, default=None,
        help=f"override the arm-plan.json path (default: <attempt_dir>/{RUN_ID}.arm-plan.json)",
    )
    parser.add_argument(
        "--split-role", default=DEFAULT_SPLIT_ROLE,
        help=f"the frozen probe receipt's split_role to read against (default: {DEFAULT_SPLIT_ROLE!r})",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to resolve the umbrella lock and the frozen receipts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    headroom_path = args.headroom_manifest or (
        repo_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-08-18-pa2t-a0-read"
        / "headroom.json"
    )

    output_dir = Path(args.output_dir)
    verdict_path = output_dir / "verdict.json"
    if verdict_path.exists():
        print(
            f"REFUSED: {verdict_path} already exists -- this suite refuses to run twice against the same "
            "output dir (one-shot read discipline); choose a fresh --output-dir if a genuinely new read is "
            "intended",
            file=sys.stderr,
        )
        return 1

    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()

    try:
        report = build_a2t_s2_report(
            args.attempt_dir,
            lock,
            root,
            repo_root=repo_root,
            headroom_path=headroom_path,
            arm_plan_path=args.arm_plan,
            split_role=args.split_role,
        )
    except A2tS2ReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, report_to_json(report))
    rendered = render_report(report)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
