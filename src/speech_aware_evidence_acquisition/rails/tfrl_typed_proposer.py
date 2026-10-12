"""The typed proposer seam of the autonomous SLURP loop (decision 263-A, E-T1).

Design: ``docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md``
sections 1.2, 1.4, 2, 3 and 4.1. Owner rulings 263 A and 264 A (2026-10-11).

The frozen core is asked, text only, to emit ONE candidate edit of the typed
system state under a closed JSON schema (``saea-tfrl-typed-candidate-v1``).
The model proposes and never judges: the schema has no free-text field and no
effect field, and a deterministic validator (:func:`validate_candidate`)
accepts or refuses the candidate and computes the predicted effect itself
(invariant I-OBJ).

This module owns:

* the candidate schema, the wire response formats for the typed proposer and
  for the ACE reflector, and the closed argument spaces of every operator;
* the prompt renderer, which reads ONLY the aggregate tables artefact
  (:func:`load_tables`), the refused-candidate buffer and the proposer-side
  meta summary (:func:`load_context`) -- never an utterance, a transcript, a
  gold label or a model output;
* :func:`validate_candidate`, with the edit budget L_t, the archive legality
  checks, the decision-245 refusal and the predicted-effect gate (decision
  192, 1.5 pp);
* :func:`candidate_id`, the sha256 of the canonical JSON;
* the flight-time material resolvers for the two program ids, dispatched from
  ``core.flight.runtime._default_construction_material``;
* :func:`draft_exposure_row`, the ledger row drafted before the first contact.

INPUT CONTRACT: THE TABLES ARTEFACT (written by E-T3, ``tfrl_contrast_tables.py``)
-------------------------------------------------------------------------------
A UTF-8 JSON object::

    {"schema": "saea-tfrl-contrast-tables-v1",
     "iteration": 1,
     "tables_sha256": "<see below>",
     "enums": {"slot_types": [...], "intents": [...], "scenarios": [18 names]},
     "tables": {
       "failure_cube": {"columns": [...], "rows": [[...], ...]},
       "scenario_summary": {...}, "state_credit": {...}, "exchange_rates": {...},
       "pool_after_selector": {...}        # optional
     }}

Required columns per table (extra columns are allowed, in any order):

* ``failure_cube``: ``failure_class, slot_type, value_in_supply, scenario,
  n_rows, mass_pp``
* ``scenario_summary``: ``scenario, n_rows, slu, intent_acc, empty_share``
* ``state_credit``: ``state_id, operator_class, operator, status, d_slu_pp,
  d_slu_lo_pp, d_slu_hi_pp, d_intent_pp`` (the archive, refused siblings
  included)
* ``exchange_rates``: ``name, pp``
* ``pool_after_selector`` (optional): ``scenario, selector, theta, pool_size``;
  without it the validator refuses an exemplar-selection candidate as
  ``pool-size-unknown`` (fail closed).

A cell is an int, a float, null, or a short identifier-like string
(``[A-Za-z0-9_.:+/<>=@-]``, at most 48 characters). The literal ``"<3"``
suppresses a count under three rows. A long string, a string with a space and
any column or key whose normalised name is, or contains, a forbidden token
(``text``, ``transcript``, ``utterance``, ``gold``, ``sentence``, ``reference``,
``query``, ``answer``, ``filler``) is refused: the renderer cannot carry
utterance-bearing content.

``tables_sha256`` is the sha256 of the canonical JSON (``sort_keys=True``,
separators ``(",", ":")``, ``ensure_ascii=True``) of the whole document with the
``tables_sha256`` key removed (:func:`canonical_tables_sha256`). The flight
fragment additionally pins the file bytes by sha256.

CONTEXT ARTEFACT (written by the driver / E-T4)::

    {"schema": "saea-tfrl-proposer-context-v1", "iteration": 1,
     "parent_state_id": "...", "archive_sha256": "...",
     "refused_buffer": [{"candidate_id", "operator_class", "operator",
                         "refusal_code", "predicted_slu_pp"?, "realised_d_slu_pp"?}],
     "meta_summary": {"<class>": {"proposed", "valid", "flown", "accepted",
                                   "refused", "mean_realised_minus_predicted_pp"}}}

ARCHIVE VIEW (the validator's input, :class:`ArchiveView`) is a plain mapping
documented at :meth:`ArchiveView.from_mapping`.

ACE REFLECTOR INTERFACE (implemented by E-T2 in ``rails/tfrl_ace_material.py``,
imported lazily; this module owns no second copy of its schema)::

    render_reflector_request(material_path: Path, playbook_path: Path,
                             token_cap: int) -> dict
        one request for ONE scenario's material file: ``messages`` (one user
        message whose content is the rendered instruction string),
        ``response_format``, ``prompt_sha256``, ``material_sha256`` ...
    parse_reflector_response(payload: dict) -> list[dict]
        ``payload`` is the decoded ``{"deltas": [...]}`` object.
    response_format() -> dict
        the ``saea-ace-delta-items-v1`` json_schema registered on the wire.

Nothing in this module reads a dataset, a model or the network.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, NamedTuple, Protocol, Sequence

from .errors import RailsError

# ---------------------------------------------------------------------------
# Identities.
# ---------------------------------------------------------------------------

CANDIDATE_SCHEMA_ID = "saea-tfrl-typed-candidate-v1"
TABLES_SCHEMA_ID = "saea-tfrl-contrast-tables-v1"
CONTEXT_SCHEMA_ID = "saea-tfrl-proposer-context-v1"
PREDICTIONS_SCHEMA_ID = "saea-tfrl-predictions-v1"
MATERIAL_SCHEMA = "saea-tfrl-proposer-material-v1"
CONTACT_SCHEMA = "saea-tfrl-proposer-contact-v1"
TYPED_RECEIPT_SCHEMA = "saea-tfrl-typed-candidate-receipt-v1"
ACE_RECEIPT_SCHEMA = "saea-tfrl-ace-reflector-receipt-v1"
ACE_REQUEST_SCHEMA = "saea-tfrl-ace-reflector-request-v1"

#: Program ids (``configs/policy/``) and registered response-format ids.
TFRL_TYPED_PROGRAM_ID = "phase-tfrl-typed-proposer-v1"
TFRL_ACE_PROGRAM_ID = "phase-tfrl-ace-reflector-v1"
TFRL_TYPED_RESPONSE_FORMAT_ID = "saea-tfrl-typed-candidate-v1"
TFRL_ACE_RESPONSE_FORMAT_ID = "saea-ace-delta-items-v1"
TFRL_TYPED_PHASE_NAME = "propose"
TFRL_ACE_PHASE_NAME = "reflect"
TFRL_TYPED_TEMPLATE_RELPATH = "probes/tfrl/typed-proposer-v1.txt"

#: ``construction_targets`` carries this constant for every carrier row: the
#: contact needs no per-row gold (spec 3.1), but the frozen-core client refuses
#: an empty target list, so the carrier is bound with a constant, non-gold text.
AGGREGATE_ONLY_TARGET = "aggregate-only contact; no row gold is shown"

#: Decision 192: a candidate under this predicted SLU-F1 gain is refused.
PREDICTED_SLU_FLOOR_PP = 1.5

# ---------------------------------------------------------------------------
# The closed vocabularies (spec 2 and 3.2).
# ---------------------------------------------------------------------------

FAILURE_CLASSES = (
    "SPURIOUS",
    "MISSING",
    "WRONG-TYPE",
    "BOUNDARY",
    "NEAR",
    "WRONG-VALUE",
    "FORMAT",
    "EMPTY-GOLD-FILL",
)
VALUE_IN_SUPPLY = ("E1", "E2", "E3", "none", "any")
HYPOTHESIS_CODES = (
    "fewer-copied-pairs",
    "more-printed-values",
    "type-inventory",
    "empty-signal",
    "rule-filter",
    "scope-narrow",
)
OPERATOR_CLASSES = ("construction", "supply", "delivery", "scope")
OPERATORS_BY_CLASS: Mapping[str, tuple[str, ...]] = {
    "construction": ("exemplar-selection", "slot-card-subset"),
    "supply": ("knob-set",),
    "delivery": ("deliver-rule",),
    "scope": ("scope-restrict",),
}
ALL_OPERATORS = tuple(op for ops in OPERATORS_BY_CLASS.values() for op in ops)
#: Named so the refusal says why (spec 2 table).
DISABLED_OPERATORS: Mapping[str, str] = {
    "key-source": "DISABLED in 263: a Solver arm cannot vary the first phase",
    "per-scenario-k": "DEFERRED: knob tails are global",
}
SCENARIOS = (
    "alarm", "audio", "calendar", "cooking", "datetime", "email", "general",
    "iot", "lists", "music", "news", "play", "qa", "recommendation", "social",
    "takeaway", "transport", "weather",
)
EXEMPLAR_SELECTORS = (
    "all",
    "entity-free-only",
    "slot-bearing-only",
    "drop-slot-bearing-if-entity-free-share",
)
THETA_SELECTOR = "drop-slot-bearing-if-entity-free-share"
SELECTOR_THETAS = (0.4, 0.5, 0.6, 0.7, 0.8)
#: Knob tail -> inclusive admissible range at the Solver (S1 spec 1.2:
#: positive integers within the fit; ``max_candidates`` is 1 or 2 only).
KNOB_RANGES: Mapping[str, tuple[int, int]] = {
    "train-exemplars.phase_supply.solver.k": (1, 60),
    "train-exemplars.phase_supply.solver.fuse_coverage.m": (1, 60),
    "train-exemplars.phase_supply.solver.fuse_coverage.c": (1, 20),
    "train-exemplars.phase_supply.solver.fuse_coverage.top_l": (1, 60),
    "slot-contracts.candidate_supply.solver.max_candidates": (1, 2),
}
DELIVERY_FAMILIES = (
    "fx-article", "fx-oclock", "fx-month-ordinal", "scope", "ti0", "ti1",
    "vs-type", "vs-any", "ee5", "ee10",
)
DELIVERY_GUARDS = ("none", "wilson")
ENTRY_KINDS = ("deliver-rule", "slot-card")
STORE_EXEMPLARS = "train-exemplars"
STORE_SLOT_CONTRACTS = "slot-contracts"

_ID_PATTERN = "^[a-z0-9_]{1,40}$"
_IDENT_RE = re.compile(r"^[A-Za-z0-9_.:+/<>=@-]{1,48}$")
_SAFE_CELL_RE = re.compile(r"^[A-Za-z0-9_.:+/<>=@-]{0,48}$")

#: Keys that signal a node-prompt, template or free-text edit (decision 245).
_FORBIDDEN_245_FRAGMENTS = (
    "prompt", "template", "instruction", "note_contract", "notecontract",
    "node_text", "note", "statement", "free_text", "freetext", "rationale", "reason",
    "explanation", "summary", "comment",
)
#: Tokens that make a table column or key utterance-bearing.
_FORBIDDEN_TABLE_FRAGMENTS = (
    "text", "transcript", "utterance", "gold", "sentence", "reference",
    "query", "answer", "filler",
)


class TfrlProposerError(RailsError):
    """An input artefact, a fragment declaration or a rendering step is
    malformed. :func:`validate_candidate` never raises this; it returns a
    :class:`ValidationResult` carrying named refusals."""


class Refusal(NamedTuple):
    code: str
    detail: str


def edit_budget(iteration: int) -> int:
    """The textual learning rate L_t: 2 at iteration 1, 1 afterwards."""

    return 2 if int(iteration) == 1 else 1


def _canonical(document: object) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def candidate_id(candidate: Mapping[str, object]) -> str:
    """The deterministic id: sha256 of the canonical JSON of the candidate."""

    return _sha256_text(_canonical(candidate))


def _safe(value: object) -> str:
    """Echo a value in a refusal detail only when it is identifier-like."""

    text = str(value)
    return text if _IDENT_RE.match(text) else "<non-identifier>"


# ---------------------------------------------------------------------------
# Enumerations generated from the pinned tables.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnumContext:
    """The enumerations that depend on pinned TRAIN tables."""

    slot_types: tuple[str, ...]
    intents: tuple[str, ...]
    scenarios: tuple[str, ...] = SCENARIOS

    def as_json(self) -> dict[str, object]:
        return {
            "slot_types": list(self.slot_types),
            "intents": list(self.intents),
            "scenarios": list(self.scenarios),
        }


def _string_schema(values: Sequence[str] | None) -> dict[str, object]:
    if values:
        return {"type": "string", "enum": list(values)}
    return {"type": "string", "pattern": _ID_PATTERN}


def candidate_schema(
    enums: EnumContext | None = None, iteration: int | None = None
) -> dict[str, object]:
    """The wire JSON schema of ``saea-tfrl-typed-candidate-v1``.

    With ``enums`` every identifier field is a closed enumeration. Without it
    (the registered default) the slot-type, intent and entry identifiers are
    constrained to a lowercase identifier pattern on the wire and closed by
    :func:`validate_candidate` against the pinned tables. With ``iteration`` the
    iteration is a constant and ``applications`` is capped at L_t.
    """

    scenarios = list(enums.scenarios) if enums else list(SCENARIOS)
    slot_types = enums.slot_types if enums else None
    intents = enums.intents if enums else None

    def array(item: dict[str, object], *, min_items: int, max_items: int) -> dict[str, object]:
        return {
            "type": "array",
            "items": item,
            "minItems": min_items,
            "maxItems": max_items,
            "uniqueItems": True,
        }

    scenario_item = {"type": "string", "enum": scenarios}
    application_shapes = [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["scenario", "selector", "theta"],
            "properties": {
                "scenario": scenario_item,
                "selector": {"type": "string", "enum": list(EXEMPLAR_SELECTORS)},
                "theta": {"enum": [*SELECTOR_THETAS, None]},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["intent", "drop_types"],
            "properties": {
                "intent": _string_schema(intents),
                "drop_types": array(_string_schema(slot_types), min_items=1, max_items=8),
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["tail", "value"],
            "properties": {
                "tail": {"type": "string", "enum": list(KNOB_RANGES)},
                "value": {"type": "integer", "minimum": 1, "maximum": 60},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["family", "guard", "types", "intents"],
            "properties": {
                "family": {"type": "string", "enum": list(DELIVERY_FAMILIES)},
                "guard": {"type": "string", "enum": list(DELIVERY_GUARDS)},
                "types": array(_string_schema(slot_types), min_items=0, max_items=8),
                "intents": array(_string_schema(intents), min_items=0, max_items=8),
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["entry_kind", "entry_id", "scenarios"],
            "properties": {
                "entry_kind": {"type": "string", "enum": list(ENTRY_KINDS)},
                "entry_id": {"type": "string", "pattern": "^[A-Za-z0-9_.:-]{1,64}$"},
                "scenarios": array(scenario_item, min_items=1, max_items=len(scenarios)),
            },
        },
    ]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema", "iteration", "parent_state_id", "operator_class", "operator",
            "target", "hypothesis_code", "applications",
        ],
        "properties": {
            "schema": {"type": "string", "enum": [CANDIDATE_SCHEMA_ID]},
            "iteration": (
                {"type": "integer", "enum": [int(iteration)]}
                if iteration is not None
                else {"type": "integer", "minimum": 1, "maximum": 3}
            ),
            "parent_state_id": {"type": "string", "pattern": "^[A-Za-z0-9_.:-]{1,64}$"},
            "operator_class": {"type": "string", "enum": list(OPERATOR_CLASSES)},
            "operator": {"type": "string", "enum": list(ALL_OPERATORS)},
            "target": {
                "type": "object",
                "additionalProperties": False,
                "required": ["failure_class", "slot_types", "scenarios", "value_in_supply"],
                "properties": {
                    "failure_class": {"type": "string", "enum": list(FAILURE_CLASSES)},
                    "slot_types": array(_string_schema(slot_types), min_items=0, max_items=8),
                    "scenarios": array(scenario_item, min_items=0, max_items=len(scenarios)),
                    "value_in_supply": {"type": "string", "enum": list(VALUE_IN_SUPPLY)},
                },
            },
            "hypothesis_code": {"type": "string", "enum": list(HYPOTHESIS_CODES)},
            "applications": {
                "type": "array",
                "minItems": 1,
                "maxItems": edit_budget(iteration) if iteration is not None else 2,
                "items": {"anyOf": application_shapes},
            },
        },
    }


def typed_candidate_response_format(
    _lock: Mapping[str, object], _root: Path, **params: object
) -> Mapping[str, object]:
    """The registered structured-decoding contract
    (:data:`TFRL_TYPED_RESPONSE_FORMAT_ID`), ``json_schema`` on the wire."""

    enums = params.get("enums")
    context = enums if isinstance(enums, EnumContext) else None
    iteration = params.get("iteration")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "saea_tfrl_typed_candidate_v1",
            "strict": True,
            "schema": candidate_schema(
                context, iteration if isinstance(iteration, int) else None
            ),
        },
    }


def ace_delta_items_response_format(
    _lock: Mapping[str, object], _root: Path, **_params: object
) -> Mapping[str, object]:
    """The registered structured-decoding contract
    (:data:`TFRL_ACE_RESPONSE_FORMAT_ID`): E-T2's own ``response_format`` (one
    schema, one owner), imported lazily."""

    from . import tfrl_ace_material  # noqa: PLC0415 (lazy)

    return tfrl_ace_material.response_format()


# ---------------------------------------------------------------------------
# The tables artefact and the context artefact.
# ---------------------------------------------------------------------------

_REQUIRED_TABLES: Mapping[str, tuple[str, ...]] = {
    "failure_cube": (
        "failure_class", "slot_type", "value_in_supply", "scenario", "n_rows", "mass_pp",
    ),
    "scenario_summary": ("scenario", "n_rows", "slu", "intent_acc", "empty_share"),
    "state_credit": (
        "state_id", "operator_class", "operator", "status", "d_slu_pp",
        "d_slu_lo_pp", "d_slu_hi_pp", "d_intent_pp",
    ),
    "exchange_rates": ("name", "pp"),
}
_OPTIONAL_TABLES: Mapping[str, tuple[str, ...]] = {
    "pool_after_selector": ("scenario", "selector", "theta", "pool_size"),
}
_REFUSED_BUFFER_KEYS = frozenset(
    {"candidate_id", "operator_class", "operator", "refusal_code",
     "predicted_slu_pp", "realised_d_slu_pp", "iteration",
     "archived_state_id", "archived_status"}
)
_META_KEYS = frozenset(
    {"proposed", "valid", "flown", "accepted", "refused",
     "mean_realised_minus_predicted_pp"}
)


def canonical_tables_sha256(document: Mapping[str, object]) -> str:
    """The content hash E-T3 must write into ``tables_sha256``."""

    body = {key: value for key, value in document.items() if key != "tables_sha256"}
    return _sha256_text(_canonical(body))


def _forbidden_name(name: str) -> str | None:
    lowered = re.sub(r"[^a-z0-9]", "", str(name).lower())
    for fragment in _FORBIDDEN_TABLE_FRAGMENTS:
        if fragment in lowered:
            return fragment
    return None


def _scan_keys(node: object, *, where: str, fragments: Iterable[str]) -> str | None:
    """The first forbidden key name found anywhere under ``node``."""

    frags = tuple(fragments)
    if isinstance(node, Mapping):
        for key, value in node.items():
            lowered = re.sub(r"[^a-z0-9_]", "", str(key).lower())
            squashed = lowered.replace("_", "")
            if any(f in lowered or f in squashed for f in frags):
                return f"{where}: key {_safe(key)}"
            found = _scan_keys(value, where=where, fragments=frags)
            if found:
                return found
    elif isinstance(node, (list, tuple)):
        for value in node:
            found = _scan_keys(value, where=where, fragments=frags)
            if found:
                return found
    return None


def _check_cell(value: object, *, table: str, column: str) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        return
    if isinstance(value, str) and (value == "<3" or _SAFE_CELL_RE.match(value)):
        return
    raise TfrlProposerError(
        f"tables artefact cell in {table}.{column} is not a number, null or an "
        "identifier-like string; an utterance-bearing cell is refused"
    )


def _validate_table(name: str, table: object, required: tuple[str, ...]) -> None:
    if not isinstance(table, Mapping):
        raise TfrlProposerError(f"tables[{name!r}] must be an object with columns and rows")
    columns = table.get("columns")
    rows = table.get("rows")
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise TfrlProposerError(f"tables[{name!r}].columns must be a list of strings")
    for column in columns:
        bad = _forbidden_name(column)
        if bad:
            raise TfrlProposerError(
                f"tables[{name!r}] column {_safe(column)} carries the forbidden token "
                f"{bad!r}; the proposer reads aggregates only"
            )
    missing = [c for c in required if c not in columns]
    if missing:
        raise TfrlProposerError(f"tables[{name!r}] lacks required columns {missing}")
    if not isinstance(rows, list):
        raise TfrlProposerError(f"tables[{name!r}].rows must be a list")
    for row in rows:
        if not isinstance(row, list) or len(row) != len(columns):
            raise TfrlProposerError(f"tables[{name!r}] has a row that does not match its columns")
        for column, cell in zip(columns, row):
            _check_cell(cell, table=name, column=column)


@dataclass(frozen=True)
class TablesArtefact:
    """A verified aggregate-tables artefact (the proposer's only content)."""

    document: Mapping[str, object]
    file_sha256: str
    tables_sha256: str
    enums: EnumContext
    iteration: int

    def table(self, name: str) -> Mapping[str, object]:
        return self.document["tables"][name]  # type: ignore[index]

    def pool_sizes(self) -> dict[tuple[str, str, float | None], int]:
        """``{(scenario, selector, theta): pool_size}`` from the optional table."""

        table = self.document["tables"].get("pool_after_selector")  # type: ignore[union-attr]
        if not table:
            return {}
        cols = table["columns"]
        out: dict[tuple[str, str, float | None], int] = {}
        for row in table["rows"]:
            record = dict(zip(cols, row))
            theta = record["theta"]
            out[(str(record["scenario"]), str(record["selector"]),
                 None if theta is None else float(theta))] = int(record["pool_size"])
        return out


def parse_tables(document: object, *, file_sha256: str = "") -> TablesArtefact:
    """Verify a tables document (already decoded) against the input contract."""

    if not isinstance(document, Mapping):
        raise TfrlProposerError("the tables artefact must be a JSON object")
    if document.get("schema") != TABLES_SCHEMA_ID:
        raise TfrlProposerError(f"the tables artefact schema must be {TABLES_SCHEMA_ID!r}")
    bad_key = _scan_keys(document, where="tables artefact", fragments=_FORBIDDEN_TABLE_FRAGMENTS)
    if bad_key:
        raise TfrlProposerError(
            f"{bad_key} is utterance-bearing; the proposer reads aggregates only"
        )
    declared = document.get("tables_sha256")
    measured = canonical_tables_sha256(document)
    if declared != measured:
        raise TfrlProposerError(
            "tables_sha256 does not match the canonical content hash of the artefact"
        )
    iteration = document.get("iteration")
    if not isinstance(iteration, int) or isinstance(iteration, bool) or not 1 <= iteration <= 3:
        raise TfrlProposerError("the tables artefact iteration must be 1, 2 or 3")
    raw_enums = document.get("enums")
    if not isinstance(raw_enums, Mapping):
        raise TfrlProposerError("the tables artefact must carry an 'enums' object")
    lists: dict[str, tuple[str, ...]] = {}
    for key in ("slot_types", "intents", "scenarios"):
        values = raw_enums.get(key)
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(v, str) and _IDENT_RE.match(v) for v in values)
            or len(set(values)) != len(values)
        ):
            raise TfrlProposerError(f"enums.{key} must be a non-empty list of unique identifiers")
        lists[key] = tuple(values)
    tables = document.get("tables")
    if not isinstance(tables, Mapping):
        raise TfrlProposerError("the tables artefact must carry a 'tables' object")
    for name, required in _REQUIRED_TABLES.items():
        if name not in tables:
            raise TfrlProposerError(f"tables[{name!r}] is required")
        _validate_table(name, tables[name], required)
    for name, required in _OPTIONAL_TABLES.items():
        if name in tables:
            _validate_table(name, tables[name], required)
    unknown = sorted(set(tables) - set(_REQUIRED_TABLES) - set(_OPTIONAL_TABLES))
    if unknown:
        raise TfrlProposerError(f"tables carries unregistered tables {unknown}")
    return TablesArtefact(
        document=document,
        file_sha256=file_sha256,
        tables_sha256=measured,
        enums=EnumContext(
            slot_types=lists["slot_types"],
            intents=lists["intents"],
            scenarios=lists["scenarios"],
        ),
        iteration=iteration,
    )


def _read_pinned_json(path: Path, expected_sha256: str, *, what: str) -> tuple[object, str]:
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise TfrlProposerError(f"{what} is missing: {path}") from error
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise TfrlProposerError(f"{what} {path} hashes to {digest}, not the pinned {expected_sha256}")
    try:
        return json.loads(raw.decode("utf-8")), digest
    except (UnicodeError, json.JSONDecodeError) as error:
        raise TfrlProposerError(f"{what} {path} is not valid UTF-8 JSON") from error


def load_tables(path: Path, expected_sha256: str = "") -> TablesArtefact:
    """Read, hash-verify and contract-verify the tables artefact."""

    document, digest = _read_pinned_json(path, expected_sha256, what="the tables artefact")
    return parse_tables(document, file_sha256=digest)


@dataclass(frozen=True)
class ProposerContext:
    """Refused buffer and meta summary: counts, codes and identifiers only."""

    iteration: int
    parent_state_id: str
    archive_sha256: str
    refused_buffer: tuple[Mapping[str, object], ...]
    meta_summary: Mapping[str, Mapping[str, object]]
    file_sha256: str = ""


def parse_context(document: object, *, file_sha256: str = "") -> ProposerContext:
    if not isinstance(document, Mapping) or document.get("schema") != CONTEXT_SCHEMA_ID:
        raise TfrlProposerError(f"the context artefact schema must be {CONTEXT_SCHEMA_ID!r}")
    bad_key = _scan_keys(document, where="context artefact", fragments=_FORBIDDEN_TABLE_FRAGMENTS)
    if bad_key:
        raise TfrlProposerError(f"{bad_key} is utterance-bearing")
    iteration = document.get("iteration")
    parent = document.get("parent_state_id")
    if not isinstance(iteration, int) or isinstance(iteration, bool) or not 1 <= iteration <= 3:
        raise TfrlProposerError("the context iteration must be 1, 2 or 3")
    if not isinstance(parent, str) or not _IDENT_RE.match(parent):
        raise TfrlProposerError("the context parent_state_id must be an identifier")
    archive_sha = str(document.get("archive_sha256") or "")
    buffer = document.get("refused_buffer", [])
    if not isinstance(buffer, list):
        raise TfrlProposerError("refused_buffer must be a list")
    rows: list[Mapping[str, object]] = []
    for entry in buffer:
        if not isinstance(entry, Mapping) or not set(entry) <= _REFUSED_BUFFER_KEYS:
            raise TfrlProposerError(
                f"a refused_buffer entry may carry only {sorted(_REFUSED_BUFFER_KEYS)}"
            )
        for key, value in entry.items():
            _check_cell(value, table="refused_buffer", column=key)
        rows.append(dict(entry))
    meta = document.get("meta_summary", {})
    if not isinstance(meta, Mapping):
        raise TfrlProposerError("meta_summary must be an object")
    for name, counters in meta.items():
        if name not in OPERATOR_CLASSES or not isinstance(counters, Mapping) or not set(
            counters
        ) <= _META_KEYS:
            raise TfrlProposerError(
                "meta_summary is keyed by operator class and carries only "
                f"{sorted(_META_KEYS)}"
            )
        for key, value in counters.items():
            _check_cell(value, table="meta_summary", column=key)
    return ProposerContext(
        iteration=iteration,
        parent_state_id=parent,
        archive_sha256=archive_sha,
        refused_buffer=tuple(rows),
        meta_summary={k: dict(v) for k, v in meta.items()},
        file_sha256=file_sha256,
    )


def load_context(path: Path, expected_sha256: str = "") -> ProposerContext:
    document, digest = _read_pinned_json(path, expected_sha256, what="the context artefact")
    return parse_context(document, file_sha256=digest)


# ---------------------------------------------------------------------------
# The prompt renderer.
# ---------------------------------------------------------------------------

TEMPLATE_PLACEHOLDERS = (
    "{{ITERATION}}", "{{PARENT_STATE_ID}}", "{{EDIT_BUDGET}}", "{{ALLOWED_CLASSES}}",
    "{{SCHEMA_JSON}}", "{{ENUMS}}", "{{TABLES_SHA256}}", "{{TABLES}}",
    "{{REFUSED_BUFFER}}", "{{META_SUMMARY}}",
)


def _fmt_cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_tables(artefact: TablesArtefact, *, max_rows_per_table: int = 60) -> str:
    """Render every table as fixed-grid text, rows in the artefact's order."""

    chunks: list[str] = []
    tables = artefact.document["tables"]  # type: ignore[index]
    for name in (*_REQUIRED_TABLES, *_OPTIONAL_TABLES):
        table = tables.get(name)  # type: ignore[union-attr]
        if table is None:
            continue
        rows = table["rows"]
        shown = rows[:max_rows_per_table]
        lines = [f"TABLE {name} ({len(rows)} rows)", " | ".join(table["columns"])]
        lines.extend(" | ".join(_fmt_cell(cell) for cell in row) for row in shown)
        if len(rows) > len(shown):
            lines.append(f"({len(rows) - len(shown)} further rows omitted)")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def render_refused_buffer(buffer: Sequence[Mapping[str, object]]) -> str:
    if not buffer:
        return "(none)"
    lines = []
    for entry in buffer:
        cells = [f"{key}={_fmt_cell(entry[key])}" for key in sorted(entry)]
        lines.append(" ".join(cells))
    return "\n".join(lines)


def render_meta_summary(meta: Mapping[str, Mapping[str, object]]) -> str:
    if not meta:
        return "(none)"
    lines = []
    for name in OPERATOR_CLASSES:
        counters = meta.get(name)
        if counters:
            cells = [f"{key}={_fmt_cell(counters[key])}" for key in sorted(counters)]
            lines.append(f"{name}: " + " ".join(cells))
    return "\n".join(lines) if lines else "(none)"


def render_typed_proposer_request(
    template_text: str,
    *,
    tables: TablesArtefact,
    context: ProposerContext,
    allowed_classes: Sequence[str] = OPERATOR_CLASSES,
    max_rows_per_table: int = 60,
) -> str:
    """Render the text-only proposer instruction.

    Reads ONLY the aggregate tables, the refused buffer and the meta summary.
    Refuses a template that lacks a placeholder or keeps one unfilled, and an
    iteration mismatch between tables and context.
    """

    if tables.iteration != context.iteration:
        raise TfrlProposerError(
            f"tables iteration {tables.iteration} and context iteration "
            f"{context.iteration} disagree"
        )
    classes = tuple(allowed_classes)
    if not classes or not set(classes) <= set(OPERATOR_CLASSES):
        raise TfrlProposerError("allowed_classes must be a non-empty subset of the operator classes")
    for placeholder in TEMPLATE_PLACEHOLDERS:
        if placeholder not in template_text:
            raise TfrlProposerError(f"the proposer template lacks {placeholder}")
    values = {
        "{{ITERATION}}": str(context.iteration),
        "{{PARENT_STATE_ID}}": context.parent_state_id,
        "{{EDIT_BUDGET}}": str(edit_budget(context.iteration)),
        "{{ALLOWED_CLASSES}}": ", ".join(classes),
        "{{SCHEMA_JSON}}": json.dumps(
            candidate_schema(tables.enums, context.iteration), indent=1, sort_keys=True
        ),
        "{{ENUMS}}": json.dumps(tables.enums.as_json(), sort_keys=True),
        "{{TABLES_SHA256}}": tables.tables_sha256,
        "{{TABLES}}": render_tables(tables, max_rows_per_table=max_rows_per_table),
        "{{REFUSED_BUFFER}}": render_refused_buffer(context.refused_buffer),
        "{{META_SUMMARY}}": render_meta_summary(context.meta_summary),
    }
    rendered = template_text
    for placeholder, value in values.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


# ---------------------------------------------------------------------------
# The archive view and the predictor seam.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArchiveView:
    """What :func:`validate_candidate` needs of the archive (written by E-T4).

    Mapping form (see :meth:`from_mapping`)::

        {"iteration": 2, "parent_state_id": "s1-...",
         "known_state_ids": [...], "archived_candidate_ids": [...],
         "masked_classes": ["supply"],
         "entry_ids": {"deliver-rule": [...], "slot-card": [...]},
         "parent_stores": ["train-exemplars"],
         "parent_knobs": {"<tail>": int},
         "parent_selection": {"<scenario>": "all"},
         "release_swaps_supported": false}

    ``archived_candidate_ids`` contains the parent's own candidate id and the id
    of every archived sibling. ``release_swaps_supported`` flips to true when
    E-T6 lands multi-store ``release_swaps``.
    """

    iteration: int
    parent_state_id: str
    known_state_ids: frozenset[str]
    archived_candidate_ids: frozenset[str] = frozenset()
    masked_classes: frozenset[str] = frozenset()
    entry_ids: Mapping[str, frozenset[str]] = field(default_factory=dict)
    parent_stores: frozenset[str] = frozenset()
    parent_knobs: Mapping[str, int] = field(default_factory=dict)
    parent_selection: Mapping[str, str] = field(default_factory=dict)
    release_swaps_supported: bool = False

    @classmethod
    def from_mapping(cls, document: Mapping[str, object]) -> "ArchiveView":
        entry_ids = document.get("entry_ids") or {}
        return cls(
            iteration=int(document["iteration"]),  # type: ignore[arg-type]
            parent_state_id=str(document["parent_state_id"]),
            known_state_ids=frozenset(map(str, document.get("known_state_ids") or ())),  # type: ignore[arg-type]
            archived_candidate_ids=frozenset(
                map(str, document.get("archived_candidate_ids") or ())  # type: ignore[arg-type]
            ),
            masked_classes=frozenset(map(str, document.get("masked_classes") or ())),  # type: ignore[arg-type]
            entry_ids={str(k): frozenset(map(str, v)) for k, v in entry_ids.items()},  # type: ignore[union-attr]
            parent_stores=frozenset(map(str, document.get("parent_stores") or ())),  # type: ignore[arg-type]
            parent_knobs={str(k): int(v) for k, v in (document.get("parent_knobs") or {}).items()},  # type: ignore[union-attr]
            parent_selection={
                str(k): str(v) for k, v in (document.get("parent_selection") or {}).items()  # type: ignore[union-attr]
            },
            release_swaps_supported=bool(document.get("release_swaps_supported", False)),
        )


@dataclass(frozen=True)
class Prediction:
    """A predicted SLU-F1 effect in points, computed by a script."""

    slu_pp: float
    basis: str = ""


class PredictionUnavailable(Exception):
    """The predictor has no prediction for this candidate."""


class Predictor(Protocol):
    """The pluggable predicted-effect interface.

    The real predictor (offline re-retrieval over pinned vectors times the M1
    printing conversion and the class exchange rates) is E-T3 / E-T6 work. It
    must return a :class:`Prediction` or raise :class:`PredictionUnavailable`.
    """

    def predict(self, candidate: Mapping[str, object], candidate_id: str) -> Prediction: ...


class FilePredictor:
    """Deterministic stub: reads a prediction file keyed by candidate id.

    ``{"schema": "saea-tfrl-predictions-v1",
       "predictions": {"<candidate_id>": {"slu_pp": 1.8, "basis": "..."}}}``
    """

    def __init__(self, path: Path) -> None:
        document, _ = _read_pinned_json(Path(path), "", what="the predictions file")
        if not isinstance(document, Mapping) or document.get("schema") != PREDICTIONS_SCHEMA_ID:
            raise TfrlProposerError(f"the predictions file schema must be {PREDICTIONS_SCHEMA_ID!r}")
        predictions = document.get("predictions")
        if not isinstance(predictions, Mapping):
            raise TfrlProposerError("the predictions file must carry a 'predictions' object")
        self._predictions = predictions

    def predict(self, candidate: Mapping[str, object], candidate_id: str) -> Prediction:
        entry = self._predictions.get(candidate_id)
        if not isinstance(entry, Mapping) or not isinstance(entry.get("slu_pp"), (int, float)):
            raise PredictionUnavailable(candidate_id)
        return Prediction(slu_pp=float(entry["slu_pp"]), basis=str(entry.get("basis") or ""))


FitChecker = Callable[[Mapping[str, object], ArchiveView], "str | None"]


# ---------------------------------------------------------------------------
# Parsing and validation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    candidate_id: str
    refusals: tuple[Refusal, ...]
    read: str = ""  # "sf" (same-flight arm) or "offline"
    prediction: Prediction | None = None

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(r.code for r in self.refusals)


def parse_candidate(text: "str | bytes | Mapping[str, object]") -> "Mapping[str, object] | None":
    """Total parser: the decoded object, or ``None`` when it is not a JSON object."""

    if isinstance(text, Mapping):
        return text
    try:
        raw = text.decode("utf-8") if isinstance(text, bytes) else str(text)
        document = json.loads(raw)
    except (UnicodeError, ValueError):
        return None
    return document if isinstance(document, Mapping) else None


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _id_list(value: object, *, allowed: Sequence[str], min_items: int, max_items: int) -> str | None:
    if not isinstance(value, list) or not min_items <= len(value) <= max_items:
        return "list-size"
    if len(set(map(str, value))) != len(value):
        return "list-duplicates"
    if not all(isinstance(v, str) and v in allowed for v in value):
        return "enum"
    return None


def _check_application(
    operator: str, application: object, enums: EnumContext, index: int
) -> list[Refusal]:
    out: list[Refusal] = []
    at = f"applications[{index}]"
    if not isinstance(application, Mapping):
        return [Refusal("schema", f"{at} must be an object")]
    keys = set(application)

    def need(expected: set[str]) -> bool:
        if keys != expected:
            out.append(Refusal("schema", f"{at} keys must be exactly {sorted(expected)}"))
            return False
        return True

    if operator == "exemplar-selection":
        if need({"scenario", "selector", "theta"}):
            if application["scenario"] not in enums.scenarios:
                out.append(Refusal("enum", f"{at}.scenario"))
            if application["selector"] not in EXEMPLAR_SELECTORS:
                out.append(Refusal("enum", f"{at}.selector"))
            theta = application["theta"]
            if application["selector"] == THETA_SELECTOR:
                if theta not in SELECTOR_THETAS:
                    out.append(Refusal("enum", f"{at}.theta"))
            elif theta is not None:
                out.append(Refusal("schema", f"{at}.theta must be null for this selector"))
    elif operator == "slot-card-subset":
        if need({"intent", "drop_types"}):
            if application["intent"] not in enums.intents:
                out.append(Refusal("enum", f"{at}.intent"))
            problem = _id_list(application["drop_types"], allowed=enums.slot_types,
                               min_items=1, max_items=8)
            if problem:
                out.append(Refusal(problem if problem == "enum" else "schema", f"{at}.drop_types"))
    elif operator == "knob-set":
        if need({"tail", "value"}):
            tail = application["tail"]
            value = application["value"]
            if tail not in KNOB_RANGES:
                out.append(Refusal("enum", f"{at}.tail"))
            elif not _is_int(value) or not KNOB_RANGES[tail][0] <= value <= KNOB_RANGES[tail][1]:
                out.append(Refusal("knob-range", f"{at}.value outside {KNOB_RANGES[tail]}"))
    elif operator == "deliver-rule":
        if need({"family", "guard", "types", "intents"}):
            if application["family"] not in DELIVERY_FAMILIES:
                out.append(Refusal("enum", f"{at}.family"))
            if application["guard"] not in DELIVERY_GUARDS:
                out.append(Refusal("enum", f"{at}.guard"))
            for field_name, allowed in (("types", enums.slot_types), ("intents", enums.intents)):
                problem = _id_list(application[field_name], allowed=allowed, min_items=0, max_items=8)
                if problem:
                    out.append(Refusal("enum" if problem == "enum" else "schema", f"{at}.{field_name}"))
            if not out and not (application["types"] or application["intents"]):
                out.append(Refusal("schema", f"{at} needs at least one type or intent"))
    elif operator == "scope-restrict":
        if need({"entry_kind", "entry_id", "scenarios"}):
            if application["entry_kind"] not in ENTRY_KINDS:
                out.append(Refusal("enum", f"{at}.entry_kind"))
            if not isinstance(application["entry_id"], str) or not re.match(
                r"^[A-Za-z0-9_.:-]{1,64}$", application["entry_id"]
            ):
                out.append(Refusal("schema", f"{at}.entry_id"))
            problem = _id_list(application["scenarios"], allowed=enums.scenarios,
                               min_items=1, max_items=len(enums.scenarios))
            if problem:
                out.append(Refusal("enum" if problem == "enum" else "schema", f"{at}.scenarios"))
    return out


def _shape_refusals(candidate: Mapping[str, object], enums: EnumContext) -> list[Refusal]:
    out: list[Refusal] = []
    expected = {
        "schema", "iteration", "parent_state_id", "operator_class", "operator",
        "target", "hypothesis_code", "applications",
    }
    if set(candidate) != expected:
        missing = sorted(expected - set(candidate))
        extra = sorted(str(k) for k in set(candidate) - expected)
        return [Refusal("schema", f"keys must be exactly the schema keys; missing {missing}, "
                                  f"extra {[_safe(k) for k in extra]}")]
    if candidate["schema"] != CANDIDATE_SCHEMA_ID:
        out.append(Refusal("schema", "schema id"))
    if not _is_int(candidate["iteration"]) or not 1 <= candidate["iteration"] <= 3:  # type: ignore[operator]
        out.append(Refusal("schema", "iteration must be 1..3"))
    parent = candidate["parent_state_id"]
    if not isinstance(parent, str) or not re.match(r"^[A-Za-z0-9_.:-]{1,64}$", parent):
        out.append(Refusal("schema", "parent_state_id"))
    if candidate["operator_class"] not in OPERATOR_CLASSES:
        out.append(Refusal("enum", f"operator_class {_safe(candidate['operator_class'])}"))
    if candidate["operator"] not in ALL_OPERATORS:
        out.append(Refusal("enum", f"operator {_safe(candidate['operator'])}"))
    if candidate["hypothesis_code"] not in HYPOTHESIS_CODES:
        out.append(Refusal("enum", f"hypothesis_code {_safe(candidate['hypothesis_code'])}"))
    target = candidate["target"]
    if not isinstance(target, Mapping) or set(target) != {
        "failure_class", "slot_types", "scenarios", "value_in_supply"
    }:
        out.append(Refusal("schema", "target keys"))
    else:
        if target["failure_class"] not in FAILURE_CLASSES:
            out.append(Refusal("enum", "target.failure_class"))
        if target["value_in_supply"] not in VALUE_IN_SUPPLY:
            out.append(Refusal("enum", "target.value_in_supply"))
        for key, allowed, cap in (
            ("slot_types", enums.slot_types, 8),
            ("scenarios", enums.scenarios, len(enums.scenarios)),
        ):
            problem = _id_list(target[key], allowed=allowed, min_items=0, max_items=cap)
            if problem:
                out.append(Refusal("enum" if problem == "enum" else "schema", f"target.{key}"))
    applications = candidate["applications"]
    if not isinstance(applications, list) or not applications:
        out.append(Refusal("schema", "applications must be a non-empty list"))
    elif candidate["operator"] in ALL_OPERATORS:
        for index, application in enumerate(applications):
            out.extend(_check_application(str(candidate["operator"]), application, enums, index))
    return out


def scan_decision_245(candidate: object) -> str | None:
    """The first sign of a node-prompt, template or free-text edit, or ``None``."""

    found = _scan_keys(candidate, where="candidate", fragments=_FORBIDDEN_245_FRAGMENTS)
    if found:
        return found
    if isinstance(candidate, Mapping):
        operator = str(candidate.get("operator") or "").lower()
        if any(word in operator for word in ("prompt", "template", "note", "instruction")):
            return f"candidate: operator {_safe(operator)}"
    return None


def _stores_of(candidate: Mapping[str, object]) -> set[str]:
    operator = candidate["operator"]
    if operator == "exemplar-selection":
        return {STORE_EXEMPLARS}
    if operator == "slot-card-subset":
        return {STORE_SLOT_CONTRACTS}
    if operator == "scope-restrict" and any(
        isinstance(a, Mapping) and a.get("entry_kind") == "slot-card"
        for a in candidate["applications"]  # type: ignore[union-attr]
    ):
        return {STORE_SLOT_CONTRACTS}
    return set()


def _selection_key(application: Mapping[str, object]) -> str:
    selector = str(application["selector"])
    return selector if application["theta"] is None else f"{selector}@{application['theta']}"


def _is_predicted(candidate: Mapping[str, object]) -> bool:
    """Construction and supply candidates -- and scope on a slot card -- are
    predicted; delivery and scope-on-rule candidates are measured offline."""

    cls = candidate["operator_class"]
    if cls in ("construction", "supply"):
        return True
    return cls == "scope" and any(
        a.get("entry_kind") == "slot-card" for a in candidate["applications"]  # type: ignore[union-attr]
    )


def validate_candidate(
    candidate: "str | bytes | Mapping[str, object]",
    *,
    enums: EnumContext,
    archive: ArchiveView,
    predictor: Predictor | None = None,
    allowed_classes: Sequence[str] | None = None,
    pool_sizes: Mapping[tuple[str, str, float | None], int] | None = None,
    fit_checker: FitChecker | None = None,
) -> ValidationResult:
    """Accept or refuse one candidate, by name (spec 3.4). Never raises on input.

    Refusal codes: ``not-json``, ``node-prompt-change-245``, ``disabled-operator``,
    ``schema``, ``enum``, ``knob-range``, ``iteration-mismatch``, ``unknown-parent``,
    ``class-operator-mismatch``, ``class-not-allowed``, ``class-masked``,
    ``edit-budget``, ``second-store-swap``, ``pool-size-unknown``, ``empty-pool``,
    ``fit``, ``duplicate-archived``, ``no-op-vs-parent``, ``prediction-missing``,
    ``refused-prediction``.
    """

    document = parse_candidate(candidate)
    if document is None:
        return ValidationResult(False, "", (Refusal("not-json", "not a JSON object"),))
    try:
        cid = candidate_id(document)
    except (TypeError, ValueError):
        return ValidationResult(False, "", (Refusal("not-json", "not canonicalisable"),))

    found_245 = scan_decision_245(document)
    if found_245:
        return ValidationResult(
            False, cid, (Refusal("node-prompt-change-245", found_245),)
        )
    operator = document.get("operator")
    if isinstance(operator, str) and operator in DISABLED_OPERATORS:
        return ValidationResult(
            False, cid, (Refusal("disabled-operator", f"{operator}: {DISABLED_OPERATORS[operator]}"),)
        )

    shape = _shape_refusals(document, enums)
    if shape:
        return ValidationResult(False, cid, tuple(shape))

    refusals: list[Refusal] = []
    cls = str(document["operator_class"])
    if str(document["operator"]) not in OPERATORS_BY_CLASS[cls]:
        refusals.append(Refusal("class-operator-mismatch", f"{cls} / {document['operator']}"))
    if document["iteration"] != archive.iteration:
        refusals.append(Refusal("iteration-mismatch", f"candidate {document['iteration']}, "
                                                      f"archive {archive.iteration}"))
    if document["parent_state_id"] != archive.parent_state_id or (
        document["parent_state_id"] not in archive.known_state_ids
    ):
        refusals.append(Refusal("unknown-parent", _safe(document["parent_state_id"])))
    if allowed_classes is not None and cls not in set(allowed_classes):
        refusals.append(Refusal("class-not-allowed", cls))
    if cls in archive.masked_classes:
        refusals.append(Refusal("class-masked", cls))
    applications: list[Mapping[str, object]] = list(document["applications"])  # type: ignore[arg-type]
    budget = edit_budget(archive.iteration)
    if len(applications) > budget:
        refusals.append(Refusal("edit-budget", f"{len(applications)} applications, L_t = {budget}"))

    op = str(document["operator"])
    if op == "scope-restrict":
        for application in applications:
            known = archive.entry_ids.get(str(application["entry_kind"]), frozenset())
            if application["entry_id"] not in known:
                refusals.append(Refusal("enum", "scope entry_id is not an entry of the parent state"))
                break

    stores_after = set(archive.parent_stores) | _stores_of(document)
    if len(stores_after) > 1 and not archive.release_swaps_supported:
        refusals.append(Refusal("second-store-swap", ", ".join(sorted(stores_after))))

    if op == "exemplar-selection":
        sizes = pool_sizes or {}
        for application in applications:
            theta = application["theta"]
            key = (str(application["scenario"]), str(application["selector"]),
                   None if theta is None else float(theta))  # type: ignore[arg-type]
            if key not in sizes:
                refusals.append(Refusal("pool-size-unknown", f"{key[0]} / {key[1]}"))
            elif sizes[key] <= 0:
                refusals.append(Refusal("empty-pool", f"{key[0]} / {key[1]}"))

    if cid in archive.archived_candidate_ids:
        refusals.append(Refusal("duplicate-archived", "identical to the parent or an archived candidate"))
    elif applications:
        if op == "knob-set" and all(
            archive.parent_knobs.get(str(a["tail"])) == a["value"] for a in applications
        ):
            refusals.append(Refusal("no-op-vs-parent", "every knob already holds this value"))
        if op == "exemplar-selection" and all(
            archive.parent_selection.get(str(a["scenario"]), "all") == _selection_key(a)
            for a in applications
        ):
            refusals.append(Refusal("no-op-vs-parent", "every scenario already holds this selector"))

    if fit_checker is not None and not refusals:
        problem = fit_checker(document, archive)
        if problem:
            refusals.append(Refusal("fit", _safe(problem)))

    prediction: Prediction | None = None
    read = "sf" if _stores_of(document) or cls == "supply" else "offline"
    if _is_predicted(document) and not refusals:
        if predictor is None:
            refusals.append(Refusal("prediction-missing", "no predictor supplied"))
        else:
            try:
                prediction = predictor.predict(document, cid)
            except PredictionUnavailable:
                refusals.append(Refusal("prediction-missing", cid[:12]))
            else:
                if prediction.slu_pp < PREDICTED_SLU_FLOOR_PP:
                    refusals.append(Refusal(
                        "refused-prediction",
                        f"predicted {prediction.slu_pp:.3f} pp is under {PREDICTED_SLU_FLOOR_PP} pp",
                    ))
    return ValidationResult(not refusals, cid, tuple(refusals), read, prediction)


# ---------------------------------------------------------------------------
# Response readers (delivery-time receipts: no model text beyond enums).
# ---------------------------------------------------------------------------


def read_typed_candidate_receipt(text: str) -> dict[str, object]:
    """The phase reader of the typed proposer. Total: never raises.

    The candidate is composed of closed enumerations and identifiers, so it is
    safe to seal; a non-conforming answer is sealed as ``legal: false`` with the
    schema refusal codes and its digest only.
    """

    digest = _sha256_text(text if isinstance(text, str) else repr(text))
    document = parse_candidate(text)
    receipt: dict[str, object] = {
        "schema": TYPED_RECEIPT_SCHEMA,
        "response_sha256": digest,
        "legal": False,
        "refusal_codes": [],
    }
    if document is None:
        receipt["refusal_codes"] = ["not-json"]
        return receipt
    if scan_decision_245(document):
        receipt["refusal_codes"] = ["node-prompt-change-245"]
        return receipt
    # Schema-level legality needs only the static vocabularies: identifier
    # fields are pattern-checked here and closed by validate_candidate later.
    open_enums = _OpenEnums()
    shape = _shape_refusals(document, open_enums)  # type: ignore[arg-type]
    if shape:
        receipt["refusal_codes"] = sorted({r.code for r in shape})
        return receipt
    receipt.update(
        legal=True,
        candidate_id=candidate_id(document),
        operator_class=document["operator_class"],
        operator=document["operator"],
        application_count=len(document["applications"]),  # type: ignore[arg-type]
        candidate=json.loads(_canonical(document)),
    )
    return receipt


class _OpenEnums:
    """Pattern-only enumerations for the delivery-time reader: any identifier
    string passes (``__contains__`` by pattern); the validator closes them."""

    class _Any(tuple):
        def __contains__(self, item: object) -> bool:
            return isinstance(item, str) and bool(re.match(_ID_PATTERN, item))

        def __iter__(self):  # pragma: no cover - not iterated
            return iter(())

    slot_types = _Any()
    intents = _Any()
    scenarios = SCENARIOS


def read_ace_reflector_receipt(text: str) -> dict[str, object]:
    """The phase reader of the ACE reflector: counts and digests, never text.

    The answer is read by E-T2's strict ``parse_reflector_response``; a refusal
    seals ``legal: false``. Total over model output.
    """

    digest = _sha256_text(text if isinstance(text, str) else repr(text))
    receipt: dict[str, object] = {
        "schema": ACE_RECEIPT_SCHEMA,
        "response_sha256": digest,
        "legal": False,
        "delta_count": 0,
        "deltas": [],
    }
    payload = parse_candidate(text)
    if payload is None:
        return receipt
    from . import tfrl_ace_material  # noqa: PLC0415 (lazy: written by E-T2)

    try:
        deltas = tfrl_ace_material.parse_reflector_response(dict(payload))
    except (RailsError, ValueError, KeyError, TypeError):
        return receipt
    receipt.update(
        legal=True,
        delta_count=len(deltas),
        deltas=[
            {
                "op": str(item.get("op", "")),
                "section": str(item.get("section", "")),
                "delta_sha256": _sha256_text(_canonical(item)),
            }
            for item in deltas
        ],
    )
    return receipt


# ---------------------------------------------------------------------------
# Flight-time material (the construction_material_resolver seam).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TfrlProposerContact:
    """One rendered, flyable proposer or reflector contact."""

    contact_id: str
    kind: str  # "typed" | "ace"
    sample_id: str
    group: str
    instruction: str
    prompt_sha256: str
    construction_target_ids: tuple[str, ...]
    inputs: Mapping[str, str]

    @property
    def draw_id(self) -> str:
        return self.contact_id

    def as_json(self) -> dict[str, object]:
        """Identities, counts and digests only -- never the rendered text."""

        return {
            "schema": CONTACT_SCHEMA,
            "draw_id": self.draw_id,
            "contact_id": self.contact_id,
            "kind": self.kind,
            "sample_id": self.sample_id,
            "group": self.group,
            "prompt_sha256": self.prompt_sha256,
            "prompt_characters": len(self.instruction),
            "declared_construction_targets": len(self.construction_target_ids),
            "inputs": dict(self.inputs),
        }


@dataclass(frozen=True)
class TfrlProposerMaterial:
    """Every contact one proposer or reflector flight makes."""

    kind: str
    contacts: tuple[TfrlProposerContact, ...]
    bound_targets: tuple[Mapping[str, str], ...]
    inputs: Mapping[str, str]

    def by_sample(self) -> dict[str, TfrlProposerContact]:
        return {contact.sample_id: contact for contact in self.contacts}

    def instruction_by_sample(self) -> dict[str, str]:
        return {contact.sample_id: contact.instruction for contact in self.contacts}

    def as_json(self) -> dict[str, object]:
        return {
            "schema": MATERIAL_SCHEMA,
            "kind": self.kind,
            "inputs": dict(self.inputs),
            "contacts": [contact.as_json() for contact in self.contacts],
            "bound_target_count": len(self.bound_targets),
            "bound_target_sample_ids": [str(e["sample_id"]) for e in self.bound_targets],
        }


def _pin(block: object, name: str) -> tuple[str, str]:
    entry = block.get(name) if isinstance(block, Mapping) else None
    if not isinstance(entry, Mapping) or not entry.get("relpath") or not entry.get("sha256"):
        raise TfrlProposerError(f"the fragment block must pin {name!r} as {{relpath, sha256}}")
    relpath = str(entry["relpath"])
    if Path(relpath).is_absolute() or ".." in Path(relpath).parts:
        raise TfrlProposerError(f"{name}.relpath {relpath!r} is not a plain relative path")
    return relpath, str(entry["sha256"])


def _verify_file(path: Path, expected_sha256: str, what: str) -> None:
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise TfrlProposerError(f"{what} is missing: {path}") from error
    if digest != expected_sha256:
        raise TfrlProposerError(f"{what} {path} hashes to {digest}, not the pinned {expected_sha256}")


def _flown_ids(samples: Sequence[object]) -> list[str]:
    ids = [getattr(s, "sample_id", None) for s in samples]
    if not ids or not all(isinstance(i, str) and i for i in ids):
        raise TfrlProposerError("every flown sample must carry a non-empty sample_id")
    if len(set(ids)) != len(ids):
        raise TfrlProposerError("this flight's split repeats a sample id")
    return list(ids)  # type: ignore[arg-type]


def _bound(carriers: Iterable[str]) -> tuple[dict[str, str], ...]:
    return tuple({"sample_id": c, "target": AGGREGATE_ONLY_TARGET} for c in carriers)


def build_typed_proposer_material(
    values: Mapping[str, object],
    *,
    lock: Mapping[str, object] | None,
    data_root: Path,
    repo_root: Path,
    samples: Sequence[object],
) -> TfrlProposerMaterial:
    """Render every typed-proposer contact this flight makes.

    Fragment block ``tfrl_proposer``::

        {"tables": {"relpath", "sha256"}, "context": {"relpath", "sha256"},
         "carriers": [{"sample_id", "allowed_classes": [...]}, ...]}

    ``relpath`` values resolve under the data root. The flown population must
    equal the carrier rows exactly.
    """

    block = values.get("tfrl_proposer")
    if not isinstance(block, Mapping):
        raise TfrlProposerError("a typed-proposer flight must declare a 'tfrl_proposer' block")
    phase = (values.get("phase_material") or {}).get(TFRL_TYPED_PHASE_NAME)  # type: ignore[union-attr]
    declared = phase.get("instruction_template") if isinstance(phase, Mapping) else None
    if declared != TFRL_TYPED_TEMPLATE_RELPATH:
        raise TfrlProposerError(
            f"phase_material[{TFRL_TYPED_PHASE_NAME!r}].instruction_template must be "
            f"{TFRL_TYPED_TEMPLATE_RELPATH!r}"
        )
    template_path = Path(repo_root) / "configs" / declared
    try:
        template_raw = template_path.read_bytes()
    except OSError as error:
        raise TfrlProposerError(f"the proposer template is missing: {template_path}") from error
    template_text = template_raw.decode("utf-8")
    template_sha = hashlib.sha256(template_raw).hexdigest()

    tables_rel, tables_sha = _pin(block, "tables")
    context_rel, context_sha = _pin(block, "context")
    tables = load_tables(Path(data_root) / tables_rel, tables_sha)
    context = load_context(Path(data_root) / context_rel, context_sha)

    carriers = block.get("carriers")
    if not isinstance(carriers, list) or not carriers:
        raise TfrlProposerError("tfrl_proposer.carriers must be a non-empty list")
    by_carrier: dict[str, tuple[str, ...]] = {}
    for entry in carriers:
        if not isinstance(entry, Mapping) or not entry.get("sample_id"):
            raise TfrlProposerError("every carrier needs a sample_id")
        classes = tuple(entry.get("allowed_classes") or ())
        if not classes or not set(classes) <= set(OPERATOR_CLASSES):
            raise TfrlProposerError("every carrier needs allowed_classes within the operator classes")
        by_carrier[str(entry["sample_id"])] = classes
    flown = _flown_ids(samples)
    if sorted(flown) != sorted(by_carrier):
        raise TfrlProposerError("the flown rows must be exactly the declared carrier rows")

    inputs = {
        "tables_sha256": tables.tables_sha256,
        "tables_file_sha256": tables.file_sha256,
        "context_file_sha256": context.file_sha256,
        "archive_sha256": context.archive_sha256,
        "template_sha256": template_sha,
    }
    contacts = []
    for sample_id in flown:
        classes = by_carrier[sample_id]
        instruction = render_typed_proposer_request(
            template_text, tables=tables, context=context, allowed_classes=classes
        )
        contacts.append(TfrlProposerContact(
            contact_id=f"tfrl-typed:i{context.iteration}:{'+'.join(classes)}",
            kind="typed",
            sample_id=sample_id,
            group="+".join(classes),
            instruction=instruction,
            prompt_sha256=_sha256_text(instruction),
            construction_target_ids=(sample_id,),
            inputs=inputs,
        ))
    return TfrlProposerMaterial("typed", tuple(contacts), _bound(flown), inputs)


def build_ace_reflector_material(
    values: Mapping[str, object],
    *,
    lock: Mapping[str, object] | None,
    data_root: Path,
    repo_root: Path,
    samples: Sequence[object],
) -> TfrlProposerMaterial:
    """Render every ACE reflector contact via E-T2's renderer (lazy import).

    Fragment block ``tfrl_ace_reflector``::

        {"playbook": {"relpath", "sha256"}, "token_cap": int,
         "carriers": [{"sample_id", "scenario", "material": {"relpath", "sha256"}}, ...]}

    One carrier row and one reflector material file per scenario; ``relpath``
    values resolve under the data root. The flown population must equal the
    carrier rows exactly. The contact's instruction is the single user message
    of E-T2's request.
    """

    block = values.get("tfrl_ace_reflector")
    if not isinstance(block, Mapping):
        raise TfrlProposerError("an ACE reflector flight must declare a 'tfrl_ace_reflector' block")
    playbook_rel, playbook_sha = _pin(block, "playbook")
    token_cap = block.get("token_cap")
    if not _is_int(token_cap) or token_cap <= 0:  # type: ignore[operator]
        raise TfrlProposerError("tfrl_ace_reflector.token_cap must be a positive integer")
    playbook_path = Path(data_root) / playbook_rel
    _verify_file(playbook_path, playbook_sha, "the ACE playbook")

    carriers = block.get("carriers")
    if not isinstance(carriers, list) or not carriers:
        raise TfrlProposerError("tfrl_ace_reflector.carriers must be a non-empty list")
    declared: list[tuple[str, str, Path, str]] = []
    scenarios_seen: set[str] = set()
    for entry in carriers:
        if not isinstance(entry, Mapping) or not entry.get("sample_id") or not entry.get("scenario"):
            raise TfrlProposerError("every ACE carrier needs a sample_id and a scenario")
        scenario = str(entry["scenario"])
        if scenario in scenarios_seen:
            raise TfrlProposerError(f"scenario {_safe(scenario)} has two carriers")
        scenarios_seen.add(scenario)
        material_rel, material_sha = _pin(entry, "material")
        material_path = Path(data_root) / material_rel
        _verify_file(material_path, material_sha, "the ACE reflector material")
        declared.append((str(entry["sample_id"]), scenario, material_path, material_sha))
    flown = _flown_ids(samples)
    if sorted(flown) != sorted(sid for sid, _, _, _ in declared):
        raise TfrlProposerError("the flown rows must be exactly the declared carrier rows")

    from . import tfrl_ace_material  # noqa: PLC0415 (lazy: written by E-T2)

    by_sample: dict[str, TfrlProposerContact] = {}
    for sample_id, scenario, material_path, material_sha in declared:
        request = tfrl_ace_material.render_reflector_request(
            material_path, playbook_path, int(token_cap)  # type: ignore[arg-type]
        )
        messages = request.get("messages") if isinstance(request, Mapping) else None
        instruction = (
            messages[-1].get("content")
            if isinstance(messages, list) and messages and isinstance(messages[-1], Mapping)
            else None
        )
        if not isinstance(instruction, str) or not instruction:
            raise TfrlProposerError(
                "render_reflector_request must return a request whose last message "
                "content is the rendered instruction string"
            )
        by_sample[sample_id] = TfrlProposerContact(
            contact_id=f"tfrl-ace:{scenario}",
            kind="ace",
            sample_id=sample_id,
            group=scenario,
            instruction=instruction,
            prompt_sha256=_sha256_text(instruction),
            construction_target_ids=(sample_id,),
            inputs={
                "material_file_sha256": material_sha,
                "playbook_file_sha256": playbook_sha,
                "request_sha256": str(request.get("request_sha256", "")),
            },
        )
    contacts = tuple(by_sample[sid] for sid in flown)
    return TfrlProposerMaterial(
        "ace",
        contacts,
        _bound(flown),
        {"playbook_file_sha256": playbook_sha, "token_cap": str(token_cap)},
    )


# ---------------------------------------------------------------------------
# The exposure-ledger row (spec 3.5).
# ---------------------------------------------------------------------------

#: The header of the ``docs/exposure-ledger.md`` table every NX / GEPA
#: registration writer fills (see ``contracts.ledger``).
LEDGER_COLUMNS = (
    "date", "run/experiment id", "execution profile", "scope", "model/tool",
    "speech carrier + split", "split role", "split identity hash", "consumed",
    "calls", "speech audio seconds", "gpu hours", "inherited exposure",
    "artifacts", "notes",
)
RETRIES_PER_CARRIER = 2


def planned_model_calls(carriers: int, retries: int = RETRIES_PER_CARRIER) -> int:
    """Run-cumulative plan budget: carriers x (1 + retries) (spec 3.5)."""

    return int(carriers) * (1 + int(retries))


def draft_exposure_row(
    *,
    date: str,
    run_id: str,
    carrier_roster_id: str,
    split_identity_hash: str,
    carriers: int,
    model_files_sha256: Mapping[str, str],
    llama_cpp_build_commit: str,
    prompt_sha256: str,
    tables_sha256: str,
    archive_sha256: str,
    geometry: str,
    kind: str = "typed",
    output_sha256: str = "",
    split_role: str = "discovery",
    carrier_lock_key: str = "slurp",
    inherited_exposure: str = "All prior SLURP exposure carried forward unchanged.",
    gpu_hours: str = "0.1",
    retries: int = RETRIES_PER_CARRIER,
) -> dict[str, str]:
    """A ledger row dict keyed by :data:`LEDGER_COLUMNS`, ``consumed = no``.

    Written and countersigned before the first contact. The output hash is
    ``pending`` until the sealed result exists; the writer then records it. The
    row states that no per-row gold, utterance text or output text is involved.
    """

    if kind not in ("typed", "ace"):
        raise TfrlProposerError("kind must be 'typed' or 'ace'")
    files = ", ".join(f"{name}={digest}" for name, digest in sorted(model_files_sha256.items()))
    label = "typed proposer" if kind == "typed" else "ACE reflector"
    return {
        "date": date,
        "run/experiment id": run_id,
        "execution profile": "bounded-discovery-probe",
        "scope": (
            f"REGISTERED -- {label} contact(s), decision 263-A / 264-A: text-only seam of the "
            "frozen core, no audio part; aggregates of the sealed construction-source lock column "
            "(R01C, TRAIN rows outside both folds) credit; no per-row gold, "
            "no utterance text, no output text."
        ),
        "model/tool": (
            f"Frozen core text-only seam; model files sha256 [{files}]; llama.cpp build "
            f"{llama_cpp_build_commit}; geometry {geometry}."
        ),
        "speech carrier + split": f"{carrier_lock_key} {carrier_roster_id} TRAIN construction {carriers}",
        "split role": split_role,
        "split identity hash": split_identity_hash,
        "consumed": "no",
        "calls": str(planned_model_calls(carriers, retries)),
        "speech audio seconds": "0",
        "gpu hours": gpu_hours,
        "inherited exposure": inherited_exposure,
        "artifacts": (
            f"prompt sha256 {prompt_sha256}; tables sha256 {tables_sha256}; "
            f"archive sha256 {archive_sha256}; output sha256 {output_sha256 or 'pending'}"
        ),
        "notes": (
            f"{carriers} carrier(s) x (1 + {retries} retries) = "
            f"{planned_model_calls(carriers, retries)} planned calls, run-cumulative. "
            "Temperature 0, pinned seed, one contact per registered row, no re-sampling "
            "beyond the registered retries. The exposure row precedes reading the result."
        ),
    }


def ledger_markdown_row(row: Mapping[str, str]) -> str:
    """One markdown table row in the writers' own form (pipes and newlines
    in a cell are replaced, as the NX registration writers do)."""

    missing = [c for c in LEDGER_COLUMNS if c not in row]
    if missing:
        raise TfrlProposerError(f"the ledger row lacks columns {missing}")
    cells = [str(row[c]).replace("|", "/").replace("\n", " ") for c in LEDGER_COLUMNS]
    return "| " + " | ".join(cells) + " |"


__all__ = [
    "ACE_RECEIPT_SCHEMA",
    "AGGREGATE_ONLY_TARGET",
    "ArchiveView",
    "CANDIDATE_SCHEMA_ID",
    "DISABLED_OPERATORS",
    "EnumContext",
    "FilePredictor",
    "KNOB_RANGES",
    "LEDGER_COLUMNS",
    "PREDICTED_SLU_FLOOR_PP",
    "Prediction",
    "PredictionUnavailable",
    "ProposerContext",
    "Refusal",
    "TFRL_ACE_PHASE_NAME",
    "TFRL_ACE_PROGRAM_ID",
    "TFRL_ACE_RESPONSE_FORMAT_ID",
    "TFRL_TYPED_PHASE_NAME",
    "TFRL_TYPED_PROGRAM_ID",
    "TFRL_TYPED_RESPONSE_FORMAT_ID",
    "TFRL_TYPED_TEMPLATE_RELPATH",
    "TablesArtefact",
    "TfrlProposerContact",
    "TfrlProposerError",
    "TfrlProposerMaterial",
    "ValidationResult",
    "ace_delta_items_response_format",
    "build_ace_reflector_material",
    "build_typed_proposer_material",
    "candidate_id",
    "candidate_schema",
    "canonical_tables_sha256",
    "draft_exposure_row",
    "edit_budget",
    "ledger_markdown_row",
    "load_context",
    "load_tables",
    "parse_candidate",
    "parse_context",
    "parse_tables",
    "planned_model_calls",
    "read_ace_reflector_receipt",
    "read_typed_candidate_receipt",
    "render_typed_proposer_request",
    "scan_decision_245",
    "typed_candidate_response_format",
    "validate_candidate",
]
