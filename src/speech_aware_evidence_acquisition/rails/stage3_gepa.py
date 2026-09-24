"""Stage-3 layer A, the GEPA arm: the reflective per-(scenario, node) proposal
contact (`docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md`;
the family record ``core.stage3_algorithms.GEPA_REFLECTIVE_PARETO_V1``,
arXiv:2507.19457).

What changes against ADV-1 (`rails.stage3_advantage`) is the unit of credit
assignment and the unit of update, and nothing else:

* ADV-1 makes ONE contact per disagreeing ROW and asks what distinguished that
  row's best rollout sample from its worst.
* GEPA makes ONE contact per (SCENARIO, NODE) GROUP and asks the frozen core to
  REFLECT over that scenario's best- and worst-outcome rows -- their whole
  sealed trajectories -- together with the node's CURRENT delta statements, and
  to propose one to five revised or new statements for that node.

Everything else is deliberately identical, because the point of the arm is that
the three training-free RL families differ in the delta store they release and
in nothing else (owner decision 101): the same construction-visible arm
(``construction-advantage-text``), the same text-only one-contact dispatch, the
same four-line block grammar, the same curator, the same store id route and the
same derangement twin.

Three model-free pieces live here:

* :func:`parse_gepa_proposal` -- the closed-form, line-keyed parser. A sibling
  of ``rails.stage3_advantage.parse_advantage_statements_v2`` with two
  differences: up to :data:`MAX_GEPA_BLOCKS` blocks instead of three, and an
  optional ``node`` invariant (a contact is addressed to ONE node, so a block
  naming another node is retained and marked illegal rather than silently
  re-routed). It never raises; curation drops illegal blocks, counted.
* :func:`render_group_row_block` / :func:`render_current_deltas` /
  :func:`render_gepa_instruction` -- the ONLY place a group's rendered
  trajectories, construction gold and current delta statements are combined.
  The return value is a flight-time instruction, never a receipt field.
* :func:`stage3_gepa_response_format_v1` -- the registered structured-decoding
  contract, read by the same parser, so schema and parser are one contract.

What this module deliberately does NOT do: it does not read a seal, does not
decide what a group IS (that is `rails.stage3_gepa_material` over the prepared
groups artifact `scripts/build_slurp_stage3_gepa_groups.py` writes) and does not
dispatch a contact.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .errors import RailsError
from .stage3_advantage import (
    LEGAL_DELTA_KINDS_V2,
    LEGAL_DELTA_NODES,
    MAX_STATEMENT_WORDS,
    STAGE3_ADVANTAGE_ARM,
)

#: The GEPA cell flies the SAME construction-visible arm ADV-1 flies. A third
#: arm would need its own D2 receipt (``e0.d2_leakage._construction_visibility``
#: is a strict bare-core-plus-one-field equality) and would buy nothing: the
#: field set, the gate and the text-only transport branch are identical. What
#: separates the two cells is the PROGRAM id below, which is what
#: ``core.flight.runtime._default_construction_material`` dispatches on.
STAGE3_GEPA_ARM = STAGE3_ADVANTAGE_ARM
STAGE3_GEPA_PROGRAM_ID = "phase-stage3-gepa-v1"
STAGE3_GEPA_RESPONSE_FORMAT_ID = "stage3-gepa-proposal-v1"
STAGE3_GEPA_PHASE_NAME = "gepa"
STAGE3_GEPA_TEMPLATE_RELPATH = "probes/slurp_stage3_gepa_v1.txt"
STAGE3_GEPA_SYSTEM_TEMPLATE_RELPATH = "probes/slurp_stage3_gepa_system_v1.txt"

#: At most five blocks per contact. ADV-1 asks about ONE row and is capped at
#: three; a GEPA contact reflects over a whole scenario's rows for one node, so
#: the form admits five. A sixth and later block is RETAINED and marked illegal,
#: never silently dropped -- curation drops it, counted.
MAX_GEPA_BLOCKS = 5

#: The legal vocabulary is ADV-1's, unchanged: the store the GEPA arm releases
#: is read by exactly the same supply route, so a kind it could not express
#: would be a kind the route could not carry.
LEGAL_GEPA_NODES = LEGAL_DELTA_NODES
LEGAL_GEPA_DELTA_KINDS = LEGAL_DELTA_KINDS_V2

_KEY_LINE = re.compile(
    r"^\s*(NODE|DELTA-KIND|TARGET|STATEMENT)\s*:\s*(.*)$", re.IGNORECASE
)
_REQUIRED_KEYS = ("NODE", "DELTA-KIND", "TARGET", "STATEMENT")
_JSON_FIELDS = {"node", "delta_kind", "target", "statement"}

#: What a rendered section says when the sealed material carries nothing of a
#: kind. Stated rather than omitted, the discipline
#: ``rails.stage3_advantage_material._NOTHING_TO_SHOW`` documents: an empty
#: section that reads as an absent one makes the contact guess.
NOTHING_TO_SHOW = "(none recorded in the sealed trajectory)"
NO_CURRENT_DELTAS = "(this node currently carries no statement for this scenario)"


class Stage3GepaError(RailsError):
    """A rendering input or a response-format request is malformed. NEVER
    raised by :func:`parse_gepa_proposal`, which is total by contract."""


# ---------------------------------------------------------------------------
# The closed-form, line-keyed proposal parser -- never raises.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GepaProposalBlock:
    """One four-line block of a GEPA proposal response, retained."""

    block_index: int
    node: str
    delta_kind: str
    target: str
    statement: str
    legal: bool
    illegal_reasons: tuple

    def word_count(self) -> int:
        return len(self.statement.split())

    def statement_sha256(self) -> str:
        return hashlib.sha256(self.statement.encode("utf-8")).hexdigest()

    def task_target(self) -> str:
        """``NODE:DELTA-KIND:TARGET`` -- S3-5's row key, unchanged."""

        return f"{self.node}:{self.delta_kind}:{self.target}"

    def receipt(self) -> dict:
        """Identities, counts and digests ONLY -- never ``statement`` text."""

        return {
            "schema": "saea-stage3-gepa-block-receipt-v1",
            "block_index": self.block_index,
            "node": self.node,
            "delta_kind": self.delta_kind,
            "target": self.target,
            "legal": self.legal,
            "illegal_reasons": list(self.illegal_reasons),
            "statement_word_count": self.word_count(),
            "statement_sha256": self.statement_sha256(),
        }


@dataclass(frozen=True)
class GepaProposalSet:
    """One GEPA contact's whole response: its blocks, retained."""

    blocks: tuple
    legal: bool
    illegal_reasons: tuple
    raw_text_sha256: str
    source_form: str
    expected_node: str | None

    def legal_blocks(self) -> tuple:
        return tuple(block for block in self.blocks if block.legal)

    def receipt(self) -> dict:
        return {
            "schema": "saea-stage3-gepa-proposal-receipt-v1",
            "legal": self.legal,
            "illegal_reasons": list(self.illegal_reasons),
            "source_form": self.source_form,
            "expected_node": self.expected_node,
            "block_count": len(self.blocks),
            "legal_block_count": len(self.legal_blocks()),
            "blocks": [block.receipt() for block in self.blocks],
            "raw_text_sha256": self.raw_text_sha256,
        }


def _blocks_from_json(raw: str):
    """Normalise a STRUCTURED reply into the four-line block fields.

    Byte-for-byte the reading ``rails.stage3_advantage._v2_blocks_from_json``
    performs, because the registered response format is the same JSON shape with
    a different ``maxItems``. Anything that is not a JSON array/object of the
    declared shape returns ``None`` and falls through to the line-keyed reading.
    """

    stripped = raw.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        document = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(document, Mapping):
        rows = document.get("blocks", document.get("proposals"))
        if rows is None:
            rows = [document]
    else:
        rows = document
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        return None
    blocks = []
    for row in rows:
        if not isinstance(row, Mapping) or not _JSON_FIELDS & set(row):
            return None
        blocks.append(
            {
                "NODE": str(row.get("node", "")).strip(),
                "DELTA-KIND": str(row.get("delta_kind", "")).strip(),
                "TARGET": str(row.get("target", "")).strip(),
                "STATEMENT": str(row.get("statement", "")).strip(),
            }
        )
    return blocks


def _blocks_from_lines(raw: str):
    """Line-keyed segmentation: a ``NODE:`` line opens a new block.

    A repeated key inside one block is ignored past its first occurrence. A
    keyed line seen BEFORE the first ``NODE:`` line opens an implicit block 0,
    so a response that merely forgot the NODE line is retained (illegal,
    missing key) rather than discarded.
    """

    blocks = []
    current = None
    for line in raw.splitlines():
        match = _KEY_LINE.match(line)
        if match is None:
            continue
        key = match.group(1).upper()
        value = match.group(2).strip()
        if key == "NODE" or current is None:
            current = {}
            blocks.append(current)
        if key in current:
            continue
        current[key] = value
    return blocks


def parse_gepa_proposal(
    text: object,
    *,
    node: str | None = None,
    max_words: int = MAX_STATEMENT_WORDS,
    max_blocks: int = MAX_GEPA_BLOCKS,
) -> GepaProposalSet:
    """Parse one GEPA contact's raw response into one to ``max_blocks`` blocks.

    Closed-form and total: it never raises. A non-string ``text``, an empty
    response, a block missing a key, an out-of-vocabulary ``NODE`` or
    ``DELTA-KIND``, an empty ``TARGET``/``STATEMENT``, an over-long
    ``STATEMENT`` and a block past the form all come back RETAINED and marked
    illegal.

    ``node`` is the GROUP's node, and is the one invariant this parser adds to
    its ADV-1 sibling: a GEPA contact is addressed to exactly one node, so a
    block that names a different one is marked illegal rather than silently
    accepted into that other node's slice of the store. Passing ``None``
    disables the check (the reading a generic consumer performs).
    """

    raw = text if isinstance(text, str) else ""
    raw_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    structured = _blocks_from_json(raw)
    source_form = "json" if structured is not None else "lines"
    found_blocks = structured if structured is not None else _blocks_from_lines(raw)

    set_reasons = []
    if not isinstance(text, str):
        set_reasons.append("response text is not a string")
    if not found_blocks:
        set_reasons.append("no NODE/DELTA-KIND/TARGET/STATEMENT block was found")
    if len(found_blocks) > max_blocks:
        set_reasons.append(
            f"{len(found_blocks)} blocks exceed the {max_blocks}-block form"
        )
    if node is not None and node not in LEGAL_GEPA_NODES:
        set_reasons.append(f"the group's node {node!r} is not a legal node")

    blocks = []
    for index, found in enumerate(found_blocks):
        reasons = []
        missing = [key for key in _REQUIRED_KEYS if key not in found]
        if missing:
            reasons.append(f"missing keys: {', '.join(missing)}")
        block_node = found.get("NODE", "")
        delta_kind = found.get("DELTA-KIND", "")
        target = found.get("TARGET", "")
        statement = found.get("STATEMENT", "")
        if block_node and block_node not in LEGAL_GEPA_NODES:
            reasons.append(f"illegal node: {block_node!r}")
        elif node is not None and block_node and block_node != node:
            reasons.append(
                f"block node {block_node!r} is not this group's node {node!r}"
            )
        if delta_kind and delta_kind not in LEGAL_GEPA_DELTA_KINDS:
            reasons.append(f"illegal delta-kind: {delta_kind!r}")
        if "TARGET" in found and not target:
            reasons.append("empty target")
        if "STATEMENT" in found and not statement:
            reasons.append("empty statement")
        word_count = len(statement.split())
        if statement and word_count > max_words:
            reasons.append(f"statement exceeds {max_words} words ({word_count})")
        if index >= max_blocks:
            reasons.append(f"block {index} is past the {max_blocks}-block form")
        blocks.append(
            GepaProposalBlock(
                block_index=index,
                node=block_node,
                delta_kind=delta_kind,
                target=target,
                statement=statement,
                legal=not reasons,
                illegal_reasons=tuple(reasons),
            )
        )

    legal = not set_reasons and bool(blocks) and all(block.legal for block in blocks)
    return GepaProposalSet(
        blocks=tuple(blocks),
        legal=legal,
        illegal_reasons=tuple(set_reasons),
        raw_text_sha256=raw_sha256,
        source_form=source_form,
        expected_node=node,
    )


# ---------------------------------------------------------------------------
# Instruction rendering -- the ONLY place trajectories + gold + delta text meet.
# ---------------------------------------------------------------------------

#: The template's placeholders, in the order the template states them.
#: Substituted LITERALLY (``str.replace``), never through ``str.format``: a
#: rendered answer is JSON and a template that ever grew a literal brace must
#: not turn a contact into a ``KeyError``.
TEMPLATE_PLACEHOLDERS = (
    "{scenario}",
    "{node}",
    "{current_deltas}",
    "{worst_rows}",
    "{best_rows}",
)


def render_current_deltas(statements: Sequence[str]) -> str:
    """The node's CURRENT statements for this scenario, numbered.

    This is the "instruction text to mutate" half of a GEPA reflection. The
    statements are the study's OWN authored delta rows (curated under the
    six-token containment rule, so none of them repeats a construction
    transcript span); they are rendered into the instruction and nowhere else.
    """

    kept = [str(item).strip() for item in statements if str(item).strip()]
    if not kept:
        return NO_CURRENT_DELTAS
    return "\n".join(f"{index + 1}. {item}" for index, item in enumerate(kept))


def render_group_row_block(
    *,
    position: int,
    label: str,
    candidate_list_text: str,
    best_answer_text: str,
    worst_answer_text: str,
    delivered_answer_text: str,
    reviewer_verdicts_text: str,
    planner_route_text: str,
    gold_text: str,
) -> str:
    """ONE row of a group, rendered from already-rendered parts.

    Every argument is text the caller produced from custodied bytes through
    ``rails.stage3_advantage_material``'s own renderers -- the same four
    rendering functions ADV-1 uses, so a row reads identically in both arms and
    neither arm owns a second copy of the grammar. ``label`` is the row's
    outcome side (``"WORSE OUTCOME"`` / ``"BETTER OUTCOME"``), never a score.
    """

    return "\n".join(
        (
            f"--- ROW {position} ({label}) ---",
            "PERCEPTION CANDIDATES:",
            candidate_list_text,
            "SOLVER SAMPLE A (better, by the official score):",
            best_answer_text,
            "SOLVER SAMPLE B (worse, by the official score):",
            worst_answer_text,
            "DELIVERED ANSWER:",
            delivered_answer_text,
            "REVIEWER VERDICTS:",
            reviewer_verdicts_text,
            "PLANNER ROUTE:",
            planner_route_text,
            "CORRECT ANSWER:",
            gold_text,
        )
    )


def render_gepa_instruction(
    template_text: str,
    *,
    scenario: str,
    node: str,
    current_deltas_text: str,
    worst_rows_text: str,
    best_rows_text: str,
) -> str:
    """Fill ``configs/probes/slurp_stage3_gepa_v1.txt``.

    The ONE function in this module that combines a scenario's rendered
    trajectories, its construction gold and the node's current delta text. Its
    return value is a flight-time instruction, never a receipt field -- exactly
    the boundary ``rails.stage3_advantage.render_advantage_instruction_v2``
    documents for ADV-1.
    """

    if not isinstance(template_text, str) or not template_text.strip():
        raise Stage3GepaError("template_text must be a non-empty string")
    missing = [key for key in TEMPLATE_PLACEHOLDERS if key not in template_text]
    if missing:
        raise Stage3GepaError(f"gepa template is missing placeholder(s): {missing}")
    if not isinstance(node, str) or node not in LEGAL_GEPA_NODES:
        raise Stage3GepaError(f"node must be one of {list(LEGAL_GEPA_NODES)}; got {node!r}")
    if not isinstance(scenario, str) or not scenario.strip():
        raise Stage3GepaError("scenario must be a non-empty string")
    values = {
        "{scenario}": scenario,
        "{node}": node,
        "{current_deltas}": current_deltas_text,
        "{worst_rows}": worst_rows_text,
        "{best_rows}": best_rows_text,
    }
    rendered = template_text
    for placeholder, value in values.items():
        if not isinstance(value, str):
            raise Stage3GepaError(f"gepa material {placeholder} must be text")
        rendered = rendered.replace(placeholder, value)
    return rendered


def gepa_group_id(scenario: str, node: str) -> str:
    """The stable id of one (scenario, node) group -- the unit of a contact."""

    return f"gepa:{scenario}:{node}"


# ---------------------------------------------------------------------------
# The registered response format (structured-decoding contract).
# ---------------------------------------------------------------------------


def stage3_gepa_response_format_v1(
    _lock: Mapping[str, object], _root: Path, **_params: object
) -> Mapping[str, object]:
    """The structured-decoding contract registered under
    :data:`STAGE3_GEPA_RESPONSE_FORMAT_ID`.

    One to :data:`MAX_GEPA_BLOCKS` blocks, each carrying the four fields of the
    four-line form. :func:`parse_gepa_proposal` stays the parser of record and
    reads this JSON shape directly (:func:`_blocks_from_json`), so the schema
    and the parser are one contract rather than two. The ``node`` enum is the
    whole vocabulary rather than the group's single node: the group's node is a
    property of the CONTACT, not of the registered format, and a format that
    varied per contact would not be a registered format at all.
    """

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "saea_stage3_gepa_proposal_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["blocks"],
                "properties": {
                    "blocks": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_GEPA_BLOCKS,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["node", "delta_kind", "target", "statement"],
                            "properties": {
                                "node": {
                                    "type": "string",
                                    "enum": list(LEGAL_GEPA_NODES),
                                },
                                "delta_kind": {
                                    "type": "string",
                                    "enum": list(LEGAL_GEPA_DELTA_KINDS),
                                },
                                "target": {"type": "string", "minLength": 1},
                                "statement": {"type": "string", "minLength": 1},
                            },
                        },
                    }
                },
            },
        },
    }


__all__ = [
    "LEGAL_GEPA_DELTA_KINDS",
    "LEGAL_GEPA_NODES",
    "MAX_GEPA_BLOCKS",
    "NOTHING_TO_SHOW",
    "NO_CURRENT_DELTAS",
    "STAGE3_GEPA_ARM",
    "STAGE3_GEPA_PHASE_NAME",
    "STAGE3_GEPA_PROGRAM_ID",
    "STAGE3_GEPA_RESPONSE_FORMAT_ID",
    "STAGE3_GEPA_SYSTEM_TEMPLATE_RELPATH",
    "STAGE3_GEPA_TEMPLATE_RELPATH",
    "TEMPLATE_PLACEHOLDERS",
    "GepaProposalBlock",
    "GepaProposalSet",
    "Stage3GepaError",
    "gepa_group_id",
    "parse_gepa_proposal",
    "render_current_deltas",
    "render_gepa_instruction",
    "render_group_row_block",
    "stage3_gepa_response_format_v1",
]
