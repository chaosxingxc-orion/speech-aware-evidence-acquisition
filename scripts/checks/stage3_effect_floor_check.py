#!/usr/bin/env python3
"""Model-free gate: a Stage-3 cell's design must be able to SEE its effect.

The measurement instrument note
``docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md``
(section 2d, the floor table; section 3, the six rules; section 6, this gate)
is binding for every Stage-3 claim from 2026-09-26. Its finding: two
request-identical flights of the SAME 625 rows differ by +1.87 pp SLU with a
CI95 that excludes zero while intent moves -1.28 pp, so a cross-flight
contrast at n = 625 cannot see an effect below about 3 pp, and the only
0.67 pp instrument the rig has is an offline read over one sealed sample pool.

This script refuses a preregistration whose DECLARED design cannot see its
DECLARED effect, before the GPU hours are spent rather than after.

**The declaration block.** A Stage-3 cell declares three facts in a top-level
``stage3_measurement`` object::

    "stage3_measurement": {
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "expected_effect_pp": 3.2,
      "rows": 625,
      "primary_metric": "official SLURP pooled SLU-F1 (micro)",
      "claims_benefit": true,
      "replicate_run_id": "SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1",
      "note": "one sentence naming what the cell expects and why"
    }

* ``measurement_design`` -- one of :data:`DESIGNS`: ``offline-sealed-pool``,
  ``same-flight-paired``, ``cross-flight-with-in-chain-replicate``,
  ``cross-flight-no-replicate``, ``form-proof``.
* ``expected_effect_pp`` -- a number: the effect, in percentage points on the
  cell's primary metric, the cell is registered to LOOK FOR. Not a hope and
  not a bound; the size the mechanism is believed to produce.
* ``rows`` -- the population count. Optional: it falls back to the experiment
  fragment's ``population.count``, which is where the harness reads it.
* ``primary_metric``, ``note`` -- free text, reported, never enforced.
* ``claims_benefit`` -- optional, default ``true``. ``false`` says the cell
  proves FORM, not benefit, and is the only legal value for ``form-proof``
  and for a cell under :data:`MIN_BENEFIT_ROWS` rows.
* ``replicate_run_id`` -- required by
  ``cross-flight-with-in-chain-replicate``: the run id of the
  request-identical replicate that flies in the SAME chain (rule 3).

**Where the block may live**, in this precedence:

1. ``docs/readiness/<package>/registered-facts-v*.json``, top level -- the
   file that already holds every number a cell registers before contact;
2. a ``docs/readiness/*preregistration*.md``, inside a fenced ``json`` block
   whose object carries ``stage3_measurement`` at its top level;
3. the experiment fragment itself
   (``configs/experiment/<fragment>.json``, top level) -- legal, and the
   natural place for a cell minted after this gate landed, but an edit to a
   fragment moves the composed hash its readiness package pinned, so an
   ALREADY pinned cell declares in (1) or (2) instead.

A file in (1) or (2) applies to a cell when its text names that cell's
``run_id`` (preferred) or ``cell_id``; one package therefore registers a whole
family. When several cells of a family want different numbers, the block may
be a mapping of run id -> block instead of one block.

**The floor table** (:data:`FLOOR_TABLE`, sourced from
:data:`INSTRUMENT_NOTE` section 2d -- change the note and this table is the
one line that follows):

===================================== ======================================
design                                floor at n rows (CI95 half-width, pp)
===================================== ======================================
``offline-sealed-pool``               ``0.67 * sqrt(625 / rows)``
``same-flight-paired``                ``0.735 * sqrt(200 / rows)``
``cross-flight-with-in-chain-replicate`` ``max(sampling, admission bar)``
``cross-flight-no-replicate``         refused outright (rule 4)
``form-proof``                        none; must claim no benefit (rule 5)
===================================== ======================================

The cross-flight sampling half-width and the rule-3 admission bar are each
anchored at the n the note measured them at (sampling 1.474 at 625, 1.2525 at
1,000, 1.2485 at 1,080; bar about 3 pp at 625 and 2.5 pp at 1,080) and scaled
to the cell's own n by ``anchor * sqrt(anchor_n / rows)`` from the anchor
NEAREST in log n, so an anchored n reproduces the note's own number exactly
instead of being re-derived from a neighbour.

**Scope.** A cell is in scope when all three hold: its experiment fragment is
a Stage-3 fragment by exactly the test
``scripts/checks/stage3_algorithm_label_check.py`` applies
(``is_stage3_fragment``: the ``stage3`` token in the stem or the
``experiment_id``, a named Stage-3 spec, or that gate's explicit list); its
``readiness.state`` is live (:data:`LIVE_READINESS_STATES`); and its run id has
a row in ``docs/exposure-ledger.md``. Everything else is out of scope and
counted in the summary: a cell with no ledger row has no registration to
enforce against, and a retired / superseded / preparation-pending cell will
never fly in that form.

An in-scope cell whose ledger row says it is CONSUMED is reported and never a
finding: those bytes already flew and this repository does not rewrite them.

**Advisory or blocking** (section 6: "advisory for cells already flown and
blocking for new ones"). A finding is BLOCKING when the cell's registration
date is on or after :data:`STRICT_FROM_DEFAULT` (2026-09-27), and ADVISORY
otherwise. Every cell registered on 2026-09-26 predates the note by hours --
the note and this gate landed that day -- so the law's own day is advisory and
the gate blocks from the next day. The registration date is the cell's
exposure-ledger ``date``, else its fragment's ``date``, else the date prefix of
its readiness package; a date none of those yield leaves the cell advisory and
says so. ``--strict-from`` moves the boundary for a caller that wants to see
what the law would refuse.

**Findings**, one printed line each; each is a FAIL when blocking:

``missing-declaration``
    No ``stage3_measurement`` anywhere this gate looks. An undeclared cell of
    fewer than :data:`MIN_BENEFIT_ROWS` rows is NOT a finding: under rule 5 a
    batch that small is a form proof by size and declares nothing.
``unparsable-declaration``
    A block exists and is not readable: an unknown design, a non-numeric
    ``expected_effect_pp``, an unresolvable or non-positive ``rows``, a
    non-boolean ``claims_benefit``, or a JSON fence carrying the key that does
    not parse.
``cross-flight-no-replicate``
    Rule 4: never claim from a single cross-flight contrast against an older
    sealed comparator with no in-chain replicate. Refused outright.
``missing-in-chain-replicate``
    ``cross-flight-with-in-chain-replicate`` naming no ``replicate_run_id``:
    the design's whole content is that the replicate flies too.
``underpowered-benefit-claim``
    Rule 5: fewer than :data:`MIN_BENEFIT_ROWS` rows together with a benefit
    claim.
``form-proof-claims-benefit``
    ``form-proof`` with ``claims_benefit`` true -- the floor table's own
    condition on that row.
``effect-below-floor``
    ``expected_effect_pp`` below the design's floor at the cell's own n. The
    printed line carries the arithmetic.

Exit 0 when no blocking finding remains (advisory lines are still printed);
exit 1 on a blocking finding or an unreadable tree. ``--explain CELL`` prints
the floor table and one cell's arithmetic and never changes the exit code of a
gate run, so a registering agent can see the bar BEFORE writing the
preregistration.

Zero model contacts, zero GPU, no network, no ``SPEECHRL_DATA_DIR`` read.

Flags: ``--repo-root``, ``--ledger``, ``--json``, ``--explain [CELL]``,
``--strict-from YYYY-MM-DD``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]

EXPOSURE_LEDGER = Path("docs/exposure-ledger.md")
EXPERIMENT_DIR = Path("configs/experiment")
READINESS = Path("docs/readiness")

#: The note whose section 2d IS the floor table below.
INSTRUMENT_NOTE = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"

#: The key of the declaration block, wherever it is carried.
MEASUREMENT_KEY = "stage3_measurement"

#: Rule 5: a batch under this many rows is a form proof, never evidence.
MIN_BENEFIT_ROWS = 200

#: The law landed 2026-09-26; a cell registered that day predates it by hours.
LAW_DATE = dt.date(2026, 9, 26)
STRICT_FROM_DEFAULT = LAW_DATE + dt.timedelta(days=1)

#: The readiness states of a cell that is still on the queue -- the same two
#: words ``finite_completion_policy_check.py`` enforces against.
LIVE_READINESS_STATES = ("ready", "held")
NO_READINESS_STATE = "<no readiness block>"

RUN_COLUMN = "run/experiment id"
CONSUMED_COLUMN = "consumed"
DATE_COLUMN = "date"

DATE_PREFIX = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
JSON_FENCE = re.compile(r"```(?:json)?[^\n]*\n(.*?)\n```", re.DOTALL)
RUN_ID_SHAPE = re.compile(r"^SAEA[-A-Z0-9]*$")


@dataclass(frozen=True)
class Floor:
    """One row of the note's floor table.

    ``sampling`` and ``bar`` are ``(n, half-width in pp)`` anchors measured at
    that n; the floor at another n scales each by ``sqrt(anchor_n / rows)``
    from the anchor nearest in log n and takes the larger of the two families.
    """

    source: str
    sampling: tuple[tuple[int, float], ...] = ()
    bar: tuple[tuple[int, float], ...] = ()
    refused: str | None = None
    requires_replicate: bool = False
    forbids_benefit: bool = False


#: Section 2d of :data:`INSTRUMENT_NOTE`, verbatim in numbers.
FLOOR_TABLE: dict[str, Floor] = {
    "offline-sealed-pool": Floor(
        source=(
            f"{INSTRUMENT_NOTE} section 2c/2d row 1: the F1 aggregation read over the "
            "sealed ROLL-1 samples, medoid rule +0.03 pp CI95 [-0.63, +0.71] at n = 625"
        ),
        sampling=((625, 0.67),),
    ),
    "same-flight-paired": Floor(
        source=(
            f"{INSTRUMENT_NOTE} section 2a/2d row 2: cell ROLL-AA, two passes inside one "
            "flight, h_within 0.735 SLU / 0.000 intent at n = 200"
        ),
        sampling=((200, 0.735),),
    ),
    "cross-flight-with-in-chain-replicate": Floor(
        source=(
            f"{INSTRUMENT_NOTE} section 2b/2d rows 3-5 (sampling half-widths 1.474 at 625, "
            "1.2525 at 1,000, 1.2485 at 1,080) and section 3 rule 3 (the admission bar: "
            "about 3 pp at 625, 2.5 pp at 1,080)"
        ),
        sampling=((625, 1.474), (1000, 1.2525), (1080, 1.2485)),
        bar=((625, 3.0), (1080, 2.5)),
        requires_replicate=True,
    ),
    "cross-flight-no-replicate": Floor(
        source=f"{INSTRUMENT_NOTE} section 3 rule 4",
        refused=(
            "rule 4: never claim from a single cross-flight contrast against an older "
            "sealed comparator with no in-chain replicate -- a pure A/A pair at n = 625 "
            "read +1.87 pp with a CI95 that excludes zero"
        ),
    ),
    "form-proof": Floor(
        source=f"{INSTRUMENT_NOTE} section 3 rule 5 and section 2d row 6",
        forbids_benefit=True,
    ),
}

DESIGNS = tuple(FLOOR_TABLE)


class Stage3EffectFloorCheckError(RuntimeError):
    """The gate could not read something it must read."""


# --------------------------------------------------------------------------
# the arithmetic
# --------------------------------------------------------------------------


def _nearest_anchor(
    anchors: tuple[tuple[int, float], ...], rows: int
) -> tuple[int, float]:
    """The anchor nearest ``rows`` in log n -- exact at an anchored n."""

    return min(anchors, key=lambda anchor: abs(math.log(anchor[0] / rows)))


def _scaled(
    anchors: tuple[tuple[int, float], ...], rows: int
) -> tuple[float, str]:
    anchor_n, anchor_h = _nearest_anchor(anchors, rows)
    value = anchor_h * math.sqrt(anchor_n / rows)
    return value, (
        f"{anchor_h:g} * sqrt({anchor_n} / {rows}) = {value:.4f} pp"
        if anchor_n != rows
        else f"{anchor_h:g} pp, measured at n = {rows}"
    )


def floor_for(design: str, rows: int) -> tuple[float | None, list[str]]:
    """``(floor in pp, the arithmetic as lines)``.

    ``None`` means the design carries no numeric floor (``form-proof``);
    ``math.inf`` means the design is refused outright.
    """

    rule = FLOOR_TABLE[design]
    if rule.refused is not None:
        return math.inf, [f"refused outright -- {rule.refused}"]
    lines: list[str] = []
    parts: list[float] = []
    if rule.sampling:
        value, shown = _scaled(rule.sampling, rows)
        lines.append(f"sampling half-width: {shown}")
        parts.append(value)
    if rule.bar:
        value, shown = _scaled(rule.bar, rows)
        lines.append(f"rule-3 admission bar: {shown}")
        parts.append(value)
    if not parts:
        lines.append("no numeric floor: this design may not claim a benefit at all")
        return None, lines
    floor = max(parts)
    if len(parts) > 1:
        lines.append(f"floor = max of the two = {floor:.4f} pp")
    else:
        lines.append(f"floor = {floor:.4f} pp")
    return floor, lines


# --------------------------------------------------------------------------
# reading the tree
# --------------------------------------------------------------------------


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Stage3EffectFloorCheckError(f"cannot read {label}: {error}") from error


def _parse_ledger(repo_root: Path, ledger: Path) -> dict[str, dict[str, str]]:
    """``{run id: row}`` with the repository's own exposure-ledger parser."""

    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from speech_aware_evidence_acquisition.contracts import (  # noqa: PLC0415
            _parse_ledger_tables,
        )
    except Exception as error:  # pragma: no cover - import environment problem
        raise Stage3EffectFloorCheckError(
            f"cannot import the repository's exposure-ledger parser from {src}: {error}"
        ) from error
    path = repo_root / ledger
    if not path.is_file():
        raise Stage3EffectFloorCheckError(f"missing {ledger.as_posix()}")
    try:
        parsed = _parse_ledger_tables(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as error:
        raise Stage3EffectFloorCheckError(
            f"cannot parse {ledger.as_posix()}: {error}"
        ) from error
    rows: dict[str, dict[str, str]] = {}
    for row in parsed:
        run_id = str(row.get(RUN_COLUMN, "")).strip()
        if run_id:
            rows.setdefault(run_id, dict(row))
    return rows


def _stage3_predicate(repo_root: Path):
    """``is_stage3_fragment`` of the algorithm-label gate, so scope agrees."""

    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        import stage3_algorithm_label_check as label_gate  # noqa: PLC0415
    except Exception as error:  # pragma: no cover - import environment problem
        raise Stage3EffectFloorCheckError(
            f"cannot import stage3_algorithm_label_check from {here}: {error}"
        ) from error
    return label_gate.is_stage3_fragment


def _consumed(row: dict[str, str]) -> str:
    """The ``consumed`` cell reduced to its leading verdict word."""

    cell = str(row.get(CONSUMED_COLUMN, "")).replace("*", "").strip().lower()
    return cell.split(";")[0].split("(")[0].strip()


def _date_in(text: Any) -> dt.date | None:
    match = DATE_PREFIX.search(str(text or ""))
    if match is None:
        return None
    try:
        return dt.date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        return None


def _readiness_state(cell: dict[str, Any]) -> str:
    readiness = cell.get("readiness")
    if not isinstance(readiness, dict):
        return NO_READINESS_STATE
    state = readiness.get("state")
    return state if isinstance(state, str) and state.strip() else NO_READINESS_STATE


@dataclass
class DeclarationFile:
    """One file that may carry a declaration, read once."""

    relpath: str
    kind: str
    text: str
    blocks: Any = None
    parse_error: str | None = None


def _blocks_from_json_document(document: Any) -> Any:
    if isinstance(document, dict) and MEASUREMENT_KEY in document:
        return document[MEASUREMENT_KEY]
    return None


def _declaration_files(repo_root: Path) -> list[DeclarationFile]:
    """Every readiness file that carries a ``stage3_measurement``, in order.

    ``registered-facts`` JSON first, preregistration markdown second: the
    precedence the docstring promises.
    """

    files: list[DeclarationFile] = []
    root = repo_root / READINESS
    if not root.is_dir():
        return files
    for path in sorted(root.glob("*/registered-facts*.json")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if MEASUREMENT_KEY not in text:
            continue
        entry = DeclarationFile(
            relpath=path.relative_to(repo_root).as_posix(), kind="registered-facts", text=text
        )
        try:
            entry.blocks = _blocks_from_json_document(json.loads(text))
        except json.JSONDecodeError as error:
            entry.parse_error = f"not readable JSON: {error}"
        if entry.blocks is None and entry.parse_error is None:
            entry.parse_error = (
                f"names {MEASUREMENT_KEY!r} but carries no such key at its top level"
            )
        files.append(entry)
    for path in sorted(root.glob("*preregistration*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if MEASUREMENT_KEY not in text:
            continue
        entry = DeclarationFile(
            relpath=path.relative_to(repo_root).as_posix(), kind="preregistration", text=text
        )
        errors: list[str] = []
        for fence in JSON_FENCE.findall(text):
            if MEASUREMENT_KEY not in fence:
                continue
            try:
                blocks = _blocks_from_json_document(json.loads(fence))
            except json.JSONDecodeError as error:
                errors.append(f"a fenced json block carrying the key does not parse: {error}")
                continue
            if blocks is not None:
                entry.blocks = blocks
                break
        if entry.blocks is None:
            entry.parse_error = (
                "; ".join(errors)
                if errors
                else (
                    f"names {MEASUREMENT_KEY!r} but no fenced json block carries it at "
                    "top level"
                )
            )
        files.append(entry)
    return files


def _block_for(blocks: Any, run_id: str | None, cell_id: str | None) -> Any:
    """One cell's block out of a file's ``stage3_measurement`` value.

    A block is either the object itself or a mapping of run / cell id ->
    object, which is how one package registers a family whose cells want
    different numbers.
    """

    if not isinstance(blocks, dict):
        return blocks
    if "measurement_design" in blocks or "expected_effect_pp" in blocks:
        return blocks
    for key in (run_id, cell_id):
        if key and key in blocks:
            return blocks[key]
    if all(isinstance(value, dict) for value in blocks.values()) and blocks:
        return None  # a keyed mapping that does not name this cell
    return blocks


@dataclass
class Declaration:
    """One cell's parsed declaration, or the reason it is not one."""

    source: str | None = None
    design: str | None = None
    effect_pp: float | None = None
    rows: int | None = None
    rows_source: str | None = None
    claims_benefit: bool = True
    replicate_run_id: str | None = None
    primary_metric: str | None = None
    note: str | None = None
    problems: list[str] = field(default_factory=list)


def _parse_declaration(
    block: Any, source: str, fragment_rows: int | None
) -> Declaration:
    parsed = Declaration(source=source)
    if not isinstance(block, dict):
        parsed.problems.append(f"{MEASUREMENT_KEY} must be a JSON object, not {type(block).__name__}")
        return parsed

    design = block.get("measurement_design")
    if design in DESIGNS:
        parsed.design = design
    else:
        parsed.problems.append(
            f"measurement_design is {design!r}; the designs are {', '.join(DESIGNS)}"
        )

    effect = block.get("expected_effect_pp")
    if isinstance(effect, bool) or not isinstance(effect, (int, float)):
        parsed.problems.append(
            f"expected_effect_pp is {effect!r}; it must be a number of percentage points"
        )
    else:
        parsed.effect_pp = float(effect)

    declared_rows = block.get("rows")
    if declared_rows is None:
        if isinstance(fragment_rows, int) and fragment_rows > 0:
            parsed.rows = fragment_rows
            parsed.rows_source = "the fragment's population.count"
        else:
            parsed.problems.append(
                "rows is absent and the experiment fragment declares no positive "
                "population.count, so no floor can be computed"
            )
    elif isinstance(declared_rows, bool) or not isinstance(declared_rows, int) or declared_rows <= 0:
        parsed.problems.append(f"rows is {declared_rows!r}; it must be a positive integer")
    else:
        parsed.rows = declared_rows
        parsed.rows_source = "the declaration"

    claims = block.get("claims_benefit", True)
    if not isinstance(claims, bool):
        parsed.problems.append(f"claims_benefit is {claims!r}; it must be true or false")
    else:
        parsed.claims_benefit = claims

    replicate = block.get("replicate_run_id")
    if replicate is not None and not isinstance(replicate, str):
        parsed.problems.append(f"replicate_run_id is {replicate!r}; it must be a run id string")
    elif isinstance(replicate, str) and replicate.strip():
        parsed.replicate_run_id = replicate.strip()

    for key in ("primary_metric", "note"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            setattr(parsed, key, value.strip())
    return parsed


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------


def _find_declaration(
    files: list[DeclarationFile],
    run_id: str | None,
    cell_id: str | None,
    fragment: dict[str, Any],
    fragment_relpath: str,
    fragment_rows: int | None,
) -> Declaration | None:
    """The cell's declaration, in the docstring's precedence, or ``None``."""

    for entry in files:
        names_it = bool(run_id and run_id in entry.text) or bool(
            cell_id and cell_id in entry.text
        )
        if not names_it:
            continue
        if entry.parse_error is not None:
            parsed = Declaration(source=entry.relpath)
            parsed.problems.append(entry.parse_error)
            return parsed
        block = _block_for(entry.blocks, run_id, cell_id)
        if block is None:
            continue
        return _parse_declaration(block, entry.relpath, fragment_rows)
    if MEASUREMENT_KEY in fragment:
        block = _block_for(fragment[MEASUREMENT_KEY], run_id, cell_id)
        if block is not None:
            return _parse_declaration(block, fragment_relpath, fragment_rows)
    return None


def _findings_for(record: dict[str, Any], parsed: Declaration | None) -> list[dict[str, Any]]:
    """Every rule, applied to one in-scope unconsumed cell."""

    cell = record["cell_id"]
    rows = record["rows"]
    findings: list[dict[str, Any]] = []

    if parsed is None:
        if isinstance(rows, int) and rows < MIN_BENEFIT_ROWS:
            return []
        findings.append(
            {
                "kind": "missing-declaration",
                "message": (
                    f"{cell}: no {MEASUREMENT_KEY} block in its readiness package, its "
                    f"preregistration or its fragment "
                    f"({record['fragment_relpath']}); a live Stage-3 cell of "
                    f"{rows if rows is not None else 'an undeclared number of'} row(s) must "
                    f"declare measurement_design, expected_effect_pp and rows "
                    f"(see {INSTRUMENT_NOTE} section 2d)"
                ),
            }
        )
        return findings

    if parsed.problems:
        for problem in parsed.problems:
            findings.append(
                {
                    "kind": "unparsable-declaration",
                    "message": (
                        f"{cell}: {MEASUREMENT_KEY} in {parsed.source} is not readable: "
                        f"{problem}"
                    ),
                }
            )
        return findings

    design = parsed.design
    rule = FLOOR_TABLE[str(design)]
    rows = parsed.rows or rows

    if rule.refused is not None:
        findings.append(
            {
                "kind": "cross-flight-no-replicate",
                "message": (
                    f"{cell}: measurement_design {design!r} is refused outright -- "
                    f"{rule.refused}. Fly a request-identical replicate in the same chain "
                    f"and declare cross-flight-with-in-chain-replicate, or read the action "
                    f"offline over a sealed sample pool."
                ),
            }
        )
        return findings

    if rule.forbids_benefit and parsed.claims_benefit:
        findings.append(
            {
                "kind": "form-proof-claims-benefit",
                "message": (
                    f"{cell}: measurement_design {design!r} may prove form only, but the "
                    f"declaration claims a benefit (claims_benefit true, "
                    f"expected_effect_pp {parsed.effect_pp:g}); set claims_benefit false or "
                    f"declare the design that can see the effect"
                ),
            }
        )

    if rule.requires_replicate and parsed.replicate_run_id is None:
        findings.append(
            {
                "kind": "missing-in-chain-replicate",
                "message": (
                    f"{cell}: measurement_design {design!r} names no replicate_run_id; "
                    f"rule 3 admits a cross-flight arm only when a request-identical "
                    f"replicate flies in the SAME chain"
                ),
            }
        )

    if isinstance(rows, int) and rows < MIN_BENEFIT_ROWS and parsed.claims_benefit:
        findings.append(
            {
                "kind": "underpowered-benefit-claim",
                "message": (
                    f"{cell}: {rows} row(s) with a benefit claim; rule 5 makes a batch under "
                    f"{MIN_BENEFIT_ROWS} rows a FORM proof, never evidence of benefit "
                    f"(terminal feedback on 4-16 trajectories cannot distinguish any effect "
                    f"this program is chasing)"
                ),
            }
        )

    floor, arithmetic = floor_for(str(design), int(rows))
    if floor is not None and parsed.effect_pp is not None and parsed.effect_pp < floor:
        findings.append(
            {
                "kind": "effect-below-floor",
                "message": (
                    f"{cell}: expected_effect_pp {parsed.effect_pp:g} is below the "
                    f"{design} floor {floor:.4f} pp at n = {rows} "
                    f"[{'; '.join(arithmetic)}]; this design cannot see the effect the cell "
                    f"is registered to look for -- source: {rule.source}"
                ),
            }
        )
    return findings


def evaluate(
    repo_root: Path,
    ledger: Path = EXPOSURE_LEDGER,
    strict_from: dt.date = STRICT_FROM_DEFAULT,
) -> dict[str, Any]:
    ledger_rows = _parse_ledger(repo_root, ledger)
    is_stage3 = _stage3_predicate(repo_root)
    files = _declaration_files(repo_root)

    directory = repo_root / EXPERIMENT_DIR
    if not directory.is_dir():
        raise Stage3EffectFloorCheckError(f"missing {EXPERIMENT_DIR.as_posix()}")

    cells: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    out_of_scope = {
        "not_stage3_fragments": 0,
        "no_ledger_row": [],
        "not_live_cells": [],
    }
    consumed_cells: list[str] = []
    form_proof_by_size: list[str] = []
    scanned = 0

    for path in sorted(directory.glob("*.json")):
        scanned += 1
        text = path.read_text(encoding="utf-8")
        fragment = _read_json(path, path.name)
        if not isinstance(fragment, dict):
            raise Stage3EffectFloorCheckError(
                f"{EXPERIMENT_DIR.as_posix()}/{path.name}: a fragment must be a JSON object"
            )
        in_scope, why = is_stage3(path.stem, fragment, text)
        if not in_scope:
            out_of_scope["not_stage3_fragments"] += 1
            continue
        fragment_relpath = f"{EXPERIMENT_DIR.as_posix()}/{path.name}"
        population = fragment.get("population")
        fragment_rows = (
            population.get("count") if isinstance(population, dict) else None
        )
        if isinstance(fragment_rows, bool) or not isinstance(fragment_rows, int):
            fragment_rows = None

        for cell in fragment.get("cells") or []:
            if not isinstance(cell, dict):
                continue
            cell_id = cell.get("cell_id") or path.stem
            run_id = cell.get("run_id") if isinstance(cell.get("run_id"), str) else None
            state = _readiness_state(cell)
            row = ledger_rows.get(run_id or "")
            if state not in LIVE_READINESS_STATES:
                out_of_scope["not_live_cells"].append({"cell": cell_id, "state": state})
                continue
            if row is None:
                out_of_scope["no_ledger_row"].append(cell_id)
                continue

            registered = _date_in(row.get(DATE_COLUMN))
            date_source = f"{ledger.as_posix()} date column"
            if registered is None:
                registered = _date_in(fragment.get("date"))
                date_source = "the fragment's date"
            if registered is None:
                registered = _date_in(str(cell.get("readiness", {})))
                date_source = "a date named in the cell's readiness block"
            if registered is None:
                date_source = "unresolved"

            record = {
                "cell_id": cell_id,
                "run_id": run_id,
                "fragment": path.stem,
                "fragment_relpath": fragment_relpath,
                "in_scope_because": why,
                "readiness_state": state,
                "rows": fragment_rows,
                "consumed": _consumed(row),
                "registered_date": registered.isoformat() if registered else None,
                "registered_date_source": date_source,
            }
            severity = (
                "blocking"
                if registered is not None and registered >= strict_from
                else "advisory"
            )
            if record["consumed"] != "no":
                record["severity"] = "reported (already flown)"
                record["declaration"] = None
                consumed_cells.append(cell_id)
                cells.append(record)
                continue

            parsed = _find_declaration(
                files, run_id, cell_id, fragment, fragment_relpath, fragment_rows
            )
            record["severity"] = severity
            record["declaration"] = (
                None
                if parsed is None
                else {
                    "source": parsed.source,
                    "measurement_design": parsed.design,
                    "expected_effect_pp": parsed.effect_pp,
                    "rows": parsed.rows,
                    "rows_source": parsed.rows_source,
                    "claims_benefit": parsed.claims_benefit,
                    "replicate_run_id": parsed.replicate_run_id,
                    "primary_metric": parsed.primary_metric,
                    "note": parsed.note,
                    "problems": list(parsed.problems),
                }
            )
            cell_findings = _findings_for(record, parsed)
            if parsed is None and not cell_findings:
                form_proof_by_size.append(cell_id)
            for finding in cell_findings:
                finding.update(
                    {
                        "cell": cell_id,
                        "run_id": run_id,
                        "severity": severity,
                        "registered_date": record["registered_date"],
                    }
                )
            findings.extend(cell_findings)
            cells.append(record)

    blocking = [finding for finding in findings if finding["severity"] == "blocking"]
    advisory = [finding for finding in findings if finding["severity"] == "advisory"]
    return {
        "schema": "saea-stage3-effect-floor-check-v1",
        "repo_root": str(repo_root),
        "instrument_note": INSTRUMENT_NOTE,
        "ledger": ledger.as_posix(),
        "strict_from": strict_from.isoformat(),
        "declaration_key": MEASUREMENT_KEY,
        "designs": list(DESIGNS),
        "min_benefit_rows": MIN_BENEFIT_ROWS,
        "declaration_files": [entry.relpath for entry in files],
        "scanned_fragments": scanned,
        "in_scope_cells": cells,
        "consumed_cells": sorted(consumed_cells),
        "form_proof_by_size": sorted(form_proof_by_size),
        "out_of_scope": {
            "not_stage3_fragments": out_of_scope["not_stage3_fragments"],
            "no_ledger_row": sorted(out_of_scope["no_ledger_row"]),
            "not_live_cells": sorted(
                out_of_scope["not_live_cells"], key=lambda row: (row["state"], row["cell"])
            ),
        },
        "findings": findings,
        "blocking_findings": blocking,
        "advisory_findings": advisory,
        "passed": not blocking,
    }


def render_floor_table(rows: int | None = None) -> list[str]:
    """The floor table, and at ``rows`` its arithmetic, as printable lines."""

    lines = [
        f"floor table (source: {INSTRUMENT_NOTE} sections 2d and 3)",
        f"  a batch under {MIN_BENEFIT_ROWS} rows is a form proof, never evidence (rule 5)",
    ]
    for design, rule in FLOOR_TABLE.items():
        lines.append(f"  {design}:")
        if rule.refused is not None:
            lines.append(f"      refused outright -- {rule.refused}")
        if rule.sampling:
            lines.append(
                "      sampling anchors (n, half-width pp): "
                + ", ".join(f"({n}, {h:g})" for n, h in rule.sampling)
            )
        if rule.bar:
            lines.append(
                "      rule-3 admission bar anchors: "
                + ", ".join(f"({n}, {h:g})" for n, h in rule.bar)
            )
        if rule.forbids_benefit:
            lines.append("      may prove form only: claims_benefit must be false")
        if rule.requires_replicate:
            lines.append("      must name replicate_run_id (rule 3)")
        if rows is not None and rule.refused is None:
            floor, arithmetic = floor_for(design, rows)
            lines.append(
                f"      at n = {rows}: " + "; ".join(arithmetic)
                if floor is not None
                else f"      at n = {rows}: no numeric floor"
            )
        lines.append(f"      source: {rule.source}")
    return lines


def explain(data: dict[str, Any], cell: str | None) -> list[str]:
    """``--explain``: the table, and one named cell's own arithmetic."""

    if cell is None:
        return render_floor_table()
    matches = [
        row
        for row in data["in_scope_cells"]
        if cell in (row["cell_id"], row["run_id"], row["fragment"])
    ]
    if not matches:
        return [
            f"no in-scope Stage-3 cell matches {cell!r}; in-scope cell ids are in --json",
            *render_floor_table(),
        ]
    lines: list[str] = []
    for row in matches:
        rows_n = row["rows"]
        declaration = row["declaration"]
        lines.append(f"cell {row['cell_id']} (run id {row['run_id']})")
        lines.append(
            f"  fragment {row['fragment_relpath']}, in scope because {row['in_scope_because']}, "
            f"readiness {row['readiness_state']}, consumed {row['consumed']}, "
            f"registered {row['registered_date']} (from {row['registered_date_source']}), "
            f"severity {row['severity']}"
        )
        lines.append(f"  population.count from the fragment: {rows_n}")
        if declaration is None:
            lines.append(f"  no {MEASUREMENT_KEY} declaration found")
        else:
            lines.append(
                f"  declared in {declaration['source']}: design "
                f"{declaration['measurement_design']!r}, expected_effect_pp "
                f"{declaration['expected_effect_pp']}, rows {declaration['rows']} "
                f"(from {declaration['rows_source']}), claims_benefit "
                f"{declaration['claims_benefit']}, replicate_run_id "
                f"{declaration['replicate_run_id']}"
            )
            if declaration["problems"]:
                lines.append(f"  unreadable: {'; '.join(declaration['problems'])}")
            design = declaration["measurement_design"]
            n = declaration["rows"] or rows_n
            if design in FLOOR_TABLE and isinstance(n, int) and n > 0:
                floor, arithmetic = floor_for(design, n)
                for step in arithmetic:
                    lines.append(f"      {step}")
                effect = declaration["expected_effect_pp"]
                if floor is not None and isinstance(effect, (int, float)):
                    verdict = "BELOW the floor" if effect < floor else "clears the floor"
                    lines.append(
                        f"      expected {effect:g} pp vs floor "
                        f"{'infinite' if floor == math.inf else format(floor, '.4f')} pp: "
                        f"{verdict}"
                    )
    first_rows = matches[0]["rows"]
    lines.extend(render_floor_table(first_rows if isinstance(first_rows, int) else None))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--ledger", type=Path, default=EXPOSURE_LEDGER)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--explain",
        nargs="?",
        const="",
        default=None,
        metavar="CELL",
        help=(
            "print the floor table (and, with a cell id / run id / fragment stem, that "
            "cell's own arithmetic) instead of gating"
        ),
    )
    parser.add_argument(
        "--strict-from",
        default=STRICT_FROM_DEFAULT.isoformat(),
        metavar="YYYY-MM-DD",
        help="the registration date from which a finding blocks instead of advising",
    )
    args = parser.parse_args(argv)

    strict_from = _date_in(args.strict_from)
    if strict_from is None:
        print(
            f"stage3 effect floor check: FAIL: --strict-from {args.strict_from!r} is not a "
            "YYYY-MM-DD date",
            file=sys.stderr,
        )
        return 1

    try:
        data = evaluate(args.repo_root.resolve(), args.ledger, strict_from)
    except Stage3EffectFloorCheckError as error:
        print(f"stage3 effect floor check: FAIL: {error}", file=sys.stderr)
        return 1

    if args.explain is not None:
        for line in explain(data, args.explain or None):
            print(line)
        return 0

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for finding in data["findings"]:
        label = "FAIL" if finding["severity"] == "blocking" else "advisory"
        print(f"stage3 effect floor check: {label}: [{finding['kind']}] {finding['message']}")

    out_of_scope = data["out_of_scope"]
    summary = (
        f"{len(data['in_scope_cells'])} in-scope Stage-3 cell(s) of "
        f"{data['scanned_fragments']} fragment(s); {len(data['consumed_cells'])} already "
        f"flown (reported only), {len(data['form_proof_by_size'])} undeclared under "
        f"{MIN_BENEFIT_ROWS} rows (form proof by size); "
        f"{len(data['blocking_findings'])} blocking, "
        f"{len(data['advisory_findings'])} advisory finding(s); blocking from "
        f"{data['strict_from']}; out of scope: "
        f"{out_of_scope['not_stage3_fragments']} non-Stage-3 fragment(s), "
        f"{len(out_of_scope['no_ledger_row'])} cell(s) with no ledger row, "
        f"{len(out_of_scope['not_live_cells'])} not-live cell(s)"
    )
    if data["passed"]:
        print(f"stage3 effect floor check: PASS ({summary})")
        return 0
    print(f"stage3 effect floor check: FAIL ({summary})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
