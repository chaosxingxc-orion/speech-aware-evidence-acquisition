"""Stage-3 S3-4: the semantic-advantage contact (Training-Free GRPO's
group-relative semantic advantage, `docs/superpowers/specs/2026-09-22-
stage3-tfrl-base-loop-engineering.md` section S3-4).

One contact per disagreeing construction row. The contact sees the row's
speech, the BEST and WORST rollout samples of that row (model outputs from a
sealed S3-2 rollout, never receipted -- custodied bytes only, exactly the
discipline ``rails.evolution.ProposerContact`` documents for the proposer
arm), and the row's own CONSTRUCTION GOLD (owner decision 82; the
``construction-advantage-text`` arm registered beside
``construction-proposer-text`` in ``e0.d2_leakage.ARM_VISIBLE_FIELDS`` /
``contracts.CONSTRUCTION_VISIBLE_ARMS``). It answers with a fixed three-line
form:

.. code-block::

    DELTA-KIND: <intent-boundary | slot-contract | exemplar-note>
    TARGET: <scenario_action or slot type the statement is about>
    STATEMENT: <one sentence, <= 40 words>

This module holds three independent, model-free pieces:

* :func:`parse_advantage_statement` -- the closed-form, line-keyed parser.
  Line-keyed exactly like the E37 primitive Reviewer verdict: it never
  raises on malformed text, it RETAINS whatever it could read and MARKS the
  statement illegal (S3-5's curator drops illegal statements, counted, never
  the parser).
* :func:`load_advantage_pairs` -- the prepared per-row material artifact
  loader for S3-3's ``pairs.json`` (``{rows: [{sample_id, best: {...},
  worst: {...}}]}``), pinned by SHA-256 and bound to the rollout run id
  S3-3 scored.
* :func:`render_advantage_instruction` -- the ONLY place a row's best/worst
  answer text and construction gold are rendered into a contact's
  instruction. Nothing this module returns for a receipt ever carries that
  rendered text; :func:`advantage_statement_receipt` and
  :func:`advantage_pair_receipt` seal identities, counts and digests only,
  the same discipline ``rails.evolution.ProposerContact.as_json`` documents.

What this module deliberately does NOT do: it does not dispatch a model
contact, and it does not wire a ``core.flight.FlightRuntime.
bind_phase_program_material`` override end to end -- that binding is the
launcher's job, on real S3-1/S3-2/S3-3 outputs that do not exist yet in this
worktree (a sibling deliverable). :func:`build_advantage_instruction_for_row`
is the reusable per-row unit such a launcher's ``material_for_phase`` would
call once real outputs exist; wiring it into ``bind_phase_program_material``
is left as a documented root follow-up (readiness package
``docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1/README.md``).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .errors import RailsError

STAGE3_ADVANTAGE_ARM = "construction-advantage-text"
STAGE3_ADVANTAGE_PROGRAM_ID = "phase-stage3-advantage-v1"
STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID = "stage3-advantage-statement-v1"
STAGE3_ADVANTAGE_PHASE_NAME = "advantage"

#: The three legal ``DELTA-KIND`` values (S3-4/S3-5). Order is the canonical
#: display order; membership, not order, is what the parser checks.
LEGAL_DELTA_KINDS: tuple[str, ...] = (
    "intent-boundary",
    "slot-contract",
    "exemplar-note",
)
MAX_STATEMENT_WORDS = 40

_SHA256 = re.compile(r"[0-9a-f]{64}")
_KEY_LINE = re.compile(r"^\s*(DELTA-KIND|TARGET|STATEMENT)\s*:\s*(.*)$", re.IGNORECASE)
_REQUIRED_KEYS = ("DELTA-KIND", "TARGET", "STATEMENT")


class Stage3AdvantageError(RailsError):
    """A ``pairs.json`` artifact, a rendered instruction input, or a response
    format request is malformed. Never raised by the STATEMENT parser
    itself (see :func:`parse_advantage_statement`'s own contract)."""


# ---------------------------------------------------------------------------
# The closed-form, line-keyed statement parser -- never raises.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdvantageStatement:
    """One parsed (or partially parsed) advantage contact response.

    ``legal`` is ``True`` only when all three keys were found exactly once
    each, ``delta_kind`` is one of :data:`LEGAL_DELTA_KINDS`, ``target`` is
    non-empty, and ``statement`` is non-empty and at most
    :data:`MAX_STATEMENT_WORDS` words. An illegal statement is RETAINED
    (every field the parser could read stays populated with its best
    reading, defaulting to ``""`` for a missing key) and
    ``illegal_reasons`` names every violation found, so S3-5's curator can
    drop it with a counted, auditable reason rather than a silent loss.
    """

    delta_kind: str
    target: str
    statement: str
    legal: bool
    illegal_reasons: tuple[str, ...]
    raw_text_sha256: str

    def word_count(self) -> int:
        return len(self.statement.split())

    def statement_sha256(self) -> str:
        return hashlib.sha256(self.statement.encode("utf-8")).hexdigest()

    def receipt(self) -> dict[str, object]:
        """Identities, counts and digests ONLY -- never ``statement`` text
        itself, exactly the discipline
        ``rails.evolution.ProposerContact.as_json`` documents for its own
        rendered instruction."""

        return {
            "schema": "saea-stage3-advantage-statement-receipt-v1",
            "delta_kind": self.delta_kind,
            "target": self.target,
            "legal": self.legal,
            "illegal_reasons": list(self.illegal_reasons),
            "statement_word_count": self.word_count(),
            "statement_sha256": self.statement_sha256(),
            "raw_text_sha256": self.raw_text_sha256,
        }


def parse_advantage_statement(
    text: object, *, max_words: int = MAX_STATEMENT_WORDS
) -> AdvantageStatement:
    """Parse one advantage contact's raw response text.

    Line-keyed: the FIRST line (after stripping leading/trailing
    whitespace) starting with ``DELTA-KIND:``, ``TARGET:`` or
    ``STATEMENT:`` (case-insensitive on the key) supplies that field; a
    repeated key is ignored past its first occurrence, so the parse is
    deterministic on a response that (against instructions) repeats a line.
    ``STATEMENT`` may itself contain a colon (its value is everything after
    the FIRST colon on that line).

    Never raises: a non-string ``text``, an empty response, a response
    missing one or more keys, an out-of-vocabulary ``DELTA-KIND``, an empty
    ``TARGET``, an empty ``STATEMENT`` or a ``STATEMENT`` over ``max_words``
    words all come back as an illegal (but populated) ``AdvantageStatement``
    -- retained, never dropped here. Curation (S3-5) is what drops an
    illegal statement, counted.
    """

    raw = text if isinstance(text, str) else ""
    raw_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    found: dict[str, str] = {}
    for line in raw.splitlines():
        match = _KEY_LINE.match(line)
        if match is None:
            continue
        key = match.group(1).upper()
        if key in found:
            continue
        found[key] = match.group(2).strip()

    reasons: list[str] = []
    missing = [key for key in _REQUIRED_KEYS if key not in found]
    if not isinstance(text, str):
        reasons.append("response text is not a string")
    if missing:
        reasons.append(f"missing keys: {', '.join(missing)}")

    delta_kind = found.get("DELTA-KIND", "")
    target = found.get("TARGET", "")
    statement = found.get("STATEMENT", "")

    if delta_kind and delta_kind not in LEGAL_DELTA_KINDS:
        reasons.append(f"illegal delta-kind: {delta_kind!r}")
    if "TARGET" in found and not target:
        reasons.append("empty target")
    if "STATEMENT" in found and not statement:
        reasons.append("empty statement")
    word_count = len(statement.split())
    if statement and word_count > max_words:
        reasons.append(f"statement exceeds {max_words} words ({word_count})")

    legal = not reasons
    return AdvantageStatement(
        delta_kind=delta_kind,
        target=target,
        statement=statement,
        legal=legal,
        illegal_reasons=tuple(reasons),
        raw_text_sha256=raw_sha256,
    )


# ---------------------------------------------------------------------------
# The prepared per-row material artifact loader -- S3-3's pairs.json.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdvantagePairSample:
    sample_index: int
    response_text_sha256: str

    def validate(self) -> "AdvantagePairSample":
        if isinstance(self.sample_index, bool) or not isinstance(self.sample_index, int) or self.sample_index < 0:
            raise Stage3AdvantageError("sample_index must be a non-negative integer")
        if not isinstance(self.response_text_sha256, str) or _SHA256.fullmatch(
            self.response_text_sha256
        ) is None:
            raise Stage3AdvantageError(
                "response_text_sha256 must be a lowercase 64-hex SHA-256"
            )
        return self


@dataclass(frozen=True)
class AdvantagePair:
    """One S3-3-selected disagreeing row: its best and worst rollout sample."""

    sample_id: str
    best: AdvantagePairSample
    worst: AdvantagePairSample

    def validate(self) -> "AdvantagePair":
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise Stage3AdvantageError("sample_id must be a non-empty string")
        self.best.validate()
        self.worst.validate()
        if self.best.sample_index == self.worst.sample_index:
            raise Stage3AdvantageError(
                f"row {self.sample_id!r}: best and worst sample_index must differ"
            )
        return self


@dataclass(frozen=True)
class AdvantagePairs:
    """The whole ``pairs.json`` artifact, pinned by its own SHA-256 and
    (when the file declares one) bound to the rollout run id it scored."""

    source_relpath: str
    source_sha256: str
    rollout_run_id: str | None
    pairs: tuple[AdvantagePair, ...]

    def by_sample(self) -> Mapping[str, AdvantagePair]:
        return {pair.sample_id: pair for pair in self.pairs}

    def receipt(self) -> dict[str, object]:
        return {
            "schema": "saea-stage3-advantage-pairs-binding-v1",
            "source": {"relpath": self.source_relpath, "sha256": self.source_sha256},
            "rollout_run_id": self.rollout_run_id,
            "row_count": len(self.pairs),
            "sample_ids": sorted(pair.sample_id for pair in self.pairs),
        }


def load_advantage_pairs(
    path: Path | str,
    *,
    repo_root: Path | str,
    expected_sha256: str | None = None,
    expected_rollout_run_id: str | None = None,
) -> AdvantagePairs:
    """Load and pin S3-3's ``pairs.json`` (``rails.stage3_advantage`` owns
    the loader; the file itself is S3-3's own output, produced by a sibling
    deliverable and never authored here).

    A RELATIVE ``path`` is confined under ``repo_root`` (no ``..`` escape,
    matching every other pinned artifact loader in this study). An ABSOLUTE
    ``path`` is trusted as given without a ``repo_root`` containment check
    -- S3-3's own ``pairs.json`` lives under ``SPEECHRL_DATA_DIR`` (large
    per-row artifacts never enter the umbrella's Git repo), not under the
    study's ``repo_root``, so confining every caller to one root would
    refuse the real artifact this loader exists to read.
    ``expected_sha256``, when given, must match the file's own bytes
    exactly -- this is the "pinned by sha256" half of S3-4's material
    identity. ``expected_rollout_run_id``, when given, must match the
    file's own ``rollout_run_id`` field (when the file declares one) -- the
    "bound to the rollout run id" half.
    """

    root = Path(repo_root).resolve()
    if Path(path).is_absolute():
        resolved = Path(path).resolve()
    else:
        resolved = (root / path).resolve()
        if resolved == root or root not in resolved.parents:
            raise Stage3AdvantageError("pairs.json path escapes repo_root")
    try:
        raw = resolved.read_bytes()
    except OSError as error:
        raise Stage3AdvantageError(f"cannot read pairs.json: {resolved}") from error
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise Stage3AdvantageError(
            f"pairs.json SHA-256 mismatch: expected {expected_sha256}, got {digest}"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise Stage3AdvantageError(f"pairs.json is not valid UTF-8 JSON: {error}") from error
    if not isinstance(document, Mapping) or "rows" not in document:
        raise Stage3AdvantageError("pairs.json must be an object with a 'rows' array")
    rows = document["rows"]
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise Stage3AdvantageError("pairs.json 'rows' must be a non-empty array")

    file_run_id = document.get("rollout_run_id")
    if file_run_id is not None and not isinstance(file_run_id, str):
        raise Stage3AdvantageError("pairs.json rollout_run_id must be a string when present")
    if (
        expected_rollout_run_id is not None
        and file_run_id is not None
        and file_run_id != expected_rollout_run_id
    ):
        raise Stage3AdvantageError(
            "pairs.json rollout_run_id disagrees with the expected rollout run: "
            f"{file_run_id!r} != {expected_rollout_run_id!r}"
        )
    bound_run_id = file_run_id if file_run_id is not None else expected_rollout_run_id

    pairs: list[AdvantagePair] = []
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(rows):
        if not isinstance(raw_row, Mapping) or set(raw_row) - {"sample_id", "best", "worst"}:
            raise Stage3AdvantageError(f"pairs.json rows[{index}] has the wrong fields")
        for key in ("sample_id", "best", "worst"):
            if key not in raw_row:
                raise Stage3AdvantageError(f"pairs.json rows[{index}] is missing {key!r}")
        pair = AdvantagePair(
            sample_id=raw_row["sample_id"],
            best=_pair_sample(raw_row["best"], f"rows[{index}].best"),
            worst=_pair_sample(raw_row["worst"], f"rows[{index}].worst"),
        ).validate()
        if pair.sample_id in seen_ids:
            raise Stage3AdvantageError(f"pairs.json duplicate sample_id {pair.sample_id!r}")
        seen_ids.add(pair.sample_id)
        pairs.append(pair)

    try:
        relpath = resolved.relative_to(root).as_posix()
    except ValueError:
        relpath = resolved.as_posix()
    return AdvantagePairs(
        source_relpath=relpath,
        source_sha256=digest,
        rollout_run_id=bound_run_id,
        pairs=tuple(pairs),
    )


def _pair_sample(raw: object, field: str) -> AdvantagePairSample:
    if not isinstance(raw, Mapping) or set(raw) != {"sample_index", "response_text_sha256"}:
        raise Stage3AdvantageError(f"pairs.json {field} has the wrong fields")
    return AdvantagePairSample(
        sample_index=raw["sample_index"],
        response_text_sha256=raw["response_text_sha256"],
    )


# ---------------------------------------------------------------------------
# Instruction rendering -- the ONLY place best/worst answers + gold appear.
# ---------------------------------------------------------------------------

_TEMPLATE_PLACEHOLDERS = ("{best_answer}", "{worst_answer}", "{gold}")


def render_advantage_instruction(
    template_text: str,
    *,
    best_answer_text: str,
    worst_answer_text: str,
    gold_text: str,
) -> str:
    """Fill ``configs/probes/slurp_stage3_advantage_v1.txt`` (or a byte-
    identical sibling template) with this row's rendered material.

    This is the ONE function in this module that ever combines rollout
    answer text and construction gold into one string. Its return value is
    a flight-time instruction, never a receipt field: nothing else in this
    module accepts an :class:`AdvantageStatement`'s ``statement`` or this
    function's return value and writes it anywhere -- callers own that
    boundary, exactly as ``rails.evolution.ProposerContact.instruction``
    documents for the proposer arm's own rendered text.
    """

    if not isinstance(template_text, str) or not template_text.strip():
        raise Stage3AdvantageError("template_text must be a non-empty string")
    missing = [key for key in _TEMPLATE_PLACEHOLDERS if key not in template_text]
    if missing:
        raise Stage3AdvantageError(
            f"advantage template is missing placeholder(s): {missing}"
        )
    return template_text.format(
        best_answer=best_answer_text,
        worst_answer=worst_answer_text,
        gold=gold_text,
    )


def build_advantage_instruction_for_row(
    template_text: str,
    pair: AdvantagePair,
    *,
    best_answer_text: str,
    worst_answer_text: str,
    gold_text: str,
) -> str:
    """The reusable per-row unit a future flight launcher's
    ``material_for_phase`` override would call once (``pair`` identifies
    WHICH sample indices supplied ``best_answer_text``/``worst_answer_text``,
    so a caller can assert it read the right custodied bytes before calling
    this). Wiring this into
    ``core.flight.FlightRuntime.bind_phase_program_material`` is a launcher
    concern this module does not perform (module docstring)."""

    pair.validate()
    return render_advantage_instruction(
        template_text,
        best_answer_text=best_answer_text,
        worst_answer_text=worst_answer_text,
        gold_text=gold_text,
    )


# ---------------------------------------------------------------------------
# The registered response format (structured-decoding contract).
# ---------------------------------------------------------------------------


def stage3_advantage_response_format_v1(
    _lock: Mapping[str, object], _root: Path, **_params: object
) -> Mapping[str, object]:
    """The JSON-schema response-format thunk registered under
    :data:`STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID` (``rails.controllers.
    register_response_formats_v1``, the shape every ``RESPONSE_FORMATS``
    entry in this study uses: ``(lock, root, **params) -> Mapping``).

    This schema mirrors the fixed three-line form's THREE FIELDS as a
    strict JSON object -- ``delta_kind`` (enum-closed to
    :data:`LEGAL_DELTA_KINDS`), ``target`` and ``statement`` -- for native
    structured decoding. :func:`parse_advantage_statement` stays the
    closed-form parser of record for whatever text a contact actually
    returns (this study's line-keyed convention, matched by every other
    primitive-verdict-shaped phase): a structured JSON reply that satisfies
    this schema also satisfies that parser once rendered back through the
    fixed three-line form, so registering the schema and keeping the
    line-keyed parser are complementary, not two competing formats.
    """

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "saea_stage3_advantage_statement_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["delta_kind", "target", "statement"],
                "properties": {
                    "delta_kind": {"type": "string", "enum": list(LEGAL_DELTA_KINDS)},
                    "target": {"type": "string", "minLength": 1},
                    "statement": {"type": "string", "minLength": 1},
                },
            },
        },
    }



# ---------------------------------------------------------------------------
# S3-4s (owner decision 106, 2026-09-23): the SYSTEM-level v2 contact.
#
# v1 above is frozen, byte for byte: every v1 id, parser, renderer and
# response format keeps working and is still reachable. v2 is purely
# additive. The one contact now sees the whole trajectory -- the Perception
# candidate list, ANSWER A / ANSWER B, the DELIVERED answer with the
# Reviewer's verdict and the Planner's route, and the construction gold --
# and answers with one to three FOUR-line blocks, each naming the NODE the
# statement is about. The node is what S3-5 stores as ``node_target`` and
# what S3-6 routes on.
# ---------------------------------------------------------------------------

STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID_V2 = "stage3-advantage-statement-v2"
STAGE3_ADVANTAGE_PROGRAM_ID_V2 = "phase-stage3-advantage-v2"
#: The committed v2 templates, named here so a launcher and a fragment
#: cannot drift apart silently.
STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2 = "probes/slurp_stage3_advantage_v2.txt"
STAGE3_ADVANTAGE_SYSTEM_TEMPLATE_RELPATH_V2 = (
    "probes/slurp_stage3_advantage_system_v2.txt"
)

#: The four nodes of the locked plan's episode, in program order. These are
#: PHASE names (``configs/policy/phase-native-candidates-review-revise-v1
#: .json``), which is what a ``context_supply`` route keys on -- not the
#: episode's internal STAGE names (where the reviewer phase's stage is
#: spelled ``"review"``).
LEGAL_DELTA_NODES = ("perception", "solver", "reviewer", "planner")

#: The v2 DELTA-KIND vocabulary: v1's three plus one per newly addressable
#: node (spec section S3-4s). Membership, not order, is what the parser
#: checks; the order below is the canonical display order.
LEGAL_DELTA_KINDS_V2 = (
    *LEGAL_DELTA_KINDS,
    "perception-hint",
    "reviewer-criterion",
    "planner-rule",
)

#: At most three blocks per contact (spec section S3-4s: "one to three
#: blocks"). A fourth and later block is RETAINED and marked illegal, never
#: silently dropped -- curation drops it, counted.
MAX_ADVANTAGE_BLOCKS = 3

_V2_KEY_LINE = re.compile(
    r"^\s*(NODE|DELTA-KIND|TARGET|STATEMENT)\s*:\s*(.*)$", re.IGNORECASE
)
_V2_REQUIRED_KEYS = ("NODE", "DELTA-KIND", "TARGET", "STATEMENT")
_V2_JSON_FIELDS = {"node", "delta_kind", "target", "statement"}


@dataclass(frozen=True)
class AdvantageBlock:
    """One four-line block of a v2 advantage response.

    Retained exactly as :class:`AdvantageStatement` is: an illegal block
    keeps every field the parser could read and names every violation in
    ``illegal_reasons``, so S3-5's curator drops it with a counted,
    auditable reason rather than a silent loss.
    """

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
        """``NODE:DELTA-KIND:TARGET`` -- S3-5's row key (spec S3-4s)."""

        return f"{self.node}:{self.delta_kind}:{self.target}"

    def receipt(self) -> dict:
        """Identities, counts and digests ONLY -- never ``statement`` text."""

        return {
            "schema": "saea-stage3-advantage-block-receipt-v1",
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
class AdvantageStatementSet:
    """One v2 advantage contact's whole response: its blocks, retained."""

    blocks: tuple
    legal: bool
    illegal_reasons: tuple
    raw_text_sha256: str
    source_form: str

    def legal_blocks(self) -> tuple:
        return tuple(block for block in self.blocks if block.legal)

    def receipt(self) -> dict:
        return {
            "schema": "saea-stage3-advantage-statement-receipt-v2",
            "legal": self.legal,
            "illegal_reasons": list(self.illegal_reasons),
            "source_form": self.source_form,
            "block_count": len(self.blocks),
            "legal_block_count": len(self.legal_blocks()),
            "blocks": [block.receipt() for block in self.blocks],
            "raw_text_sha256": self.raw_text_sha256,
        }


def _v2_blocks_from_json(raw: str):
    """Normalise a STRUCTURED reply into the four-line block fields.

    The registered v2 response format is a JSON schema (native structured
    decoding), so a compliant contact answers with JSON rather than with the
    literal four lines. Returning the same field mapping from both shapes is
    what makes :func:`parse_advantage_statements_v2` the single parser of
    record. Anything that is not a JSON array/object of the declared shape
    returns ``None`` and falls through to the line-keyed reading.
    """

    stripped = raw.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        document = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(document, Mapping):
        rows = document.get("blocks", document.get("statements"))
        if rows is None:
            rows = [document]
    else:
        rows = document
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        return None
    blocks = []
    for row in rows:
        if not isinstance(row, Mapping) or not _V2_JSON_FIELDS & set(row):
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


def _v2_blocks_from_lines(raw: str):
    """Line-keyed block segmentation: a ``NODE:`` line opens a new block.

    A repeated key inside one block is ignored past its first occurrence
    (the v1 rule, per block). A keyed line seen BEFORE the first ``NODE:``
    line opens an implicit block 0, so a response that merely forgot the
    NODE line is retained (illegal, missing key) rather than discarded.
    """

    blocks = []
    current = None
    for line in raw.splitlines():
        match = _V2_KEY_LINE.match(line)
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


def parse_advantage_statements_v2(
    text: object, *, max_words: int = MAX_STATEMENT_WORDS
) -> AdvantageStatementSet:
    """Parse one v2 advantage contact's raw response into one to three blocks.

    Closed-form and total, exactly like :func:`parse_advantage_statement`:
    it never raises. A non-string ``text``, an empty response, a block
    missing a key, an out-of-vocabulary ``NODE`` or ``DELTA-KIND``, an empty
    ``TARGET``/``STATEMENT``, an over-long ``STATEMENT`` and a fourth or
    later block all come back RETAINED and marked illegal. Curation (S3-5)
    is what drops an illegal block, counted.
    """

    raw = text if isinstance(text, str) else ""
    raw_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    structured = _v2_blocks_from_json(raw)
    source_form = "json" if structured is not None else "lines"
    found_blocks = structured if structured is not None else _v2_blocks_from_lines(raw)

    set_reasons = []
    if not isinstance(text, str):
        set_reasons.append("response text is not a string")
    if not found_blocks:
        set_reasons.append("no NODE/DELTA-KIND/TARGET/STATEMENT block was found")
    if len(found_blocks) > MAX_ADVANTAGE_BLOCKS:
        set_reasons.append(
            f"{len(found_blocks)} blocks exceed the {MAX_ADVANTAGE_BLOCKS}-block form"
        )

    blocks = []
    for index, found in enumerate(found_blocks):
        reasons = []
        missing = [key for key in _V2_REQUIRED_KEYS if key not in found]
        if missing:
            reasons.append(f"missing keys: {', '.join(missing)}")
        node = found.get("NODE", "")
        delta_kind = found.get("DELTA-KIND", "")
        target = found.get("TARGET", "")
        statement = found.get("STATEMENT", "")
        if node and node not in LEGAL_DELTA_NODES:
            reasons.append(f"illegal node: {node!r}")
        if delta_kind and delta_kind not in LEGAL_DELTA_KINDS_V2:
            reasons.append(f"illegal delta-kind: {delta_kind!r}")
        if "TARGET" in found and not target:
            reasons.append("empty target")
        if "STATEMENT" in found and not statement:
            reasons.append("empty statement")
        word_count = len(statement.split())
        if statement and word_count > max_words:
            reasons.append(f"statement exceeds {max_words} words ({word_count})")
        if index >= MAX_ADVANTAGE_BLOCKS:
            reasons.append(
                f"block {index} is past the {MAX_ADVANTAGE_BLOCKS}-block form"
            )
        blocks.append(
            AdvantageBlock(
                block_index=index,
                node=node,
                delta_kind=delta_kind,
                target=target,
                statement=statement,
                legal=not reasons,
                illegal_reasons=tuple(reasons),
            )
        )

    legal = not set_reasons and bool(blocks) and all(block.legal for block in blocks)
    return AdvantageStatementSet(
        blocks=tuple(blocks),
        legal=legal,
        illegal_reasons=tuple(set_reasons),
        raw_text_sha256=raw_sha256,
        source_form=source_form,
    )


# ---------------------------------------------------------------------------
# v2 instruction rendering -- the ONLY place trajectory text + gold appear.
# ---------------------------------------------------------------------------

#: The v2 template's placeholders, in the order the template states them.
#: Rendering substitutes them LITERALLY (``str.replace``) rather than through
#: ``str.format``: a rendered answer is JSON and a template that ever grew a
#: literal brace must not turn a contact into a ``KeyError``.
V2_TEMPLATE_PLACEHOLDERS = (
    "{candidate_list}",
    "{best_answer}",
    "{worst_answer}",
    "{delivered_answer}",
    "{reviewer_verdicts}",
    "{planner_route}",
    "{gold}",
)


def render_advantage_instruction_v2(
    template_text: str,
    *,
    candidate_list_text: str,
    best_answer_text: str,
    worst_answer_text: str,
    delivered_answer_text: str,
    reviewer_verdicts_text: str,
    planner_route_text: str,
    gold_text: str,
) -> str:
    """Fill ``configs/probes/slurp_stage3_advantage_v2.txt``.

    The ONE function in this module that combines the row's whole rendered
    trajectory with the construction gold. Its return value is a flight-time
    instruction, never a receipt field -- exactly the boundary
    :func:`render_advantage_instruction` documents for v1.

    Every argument is already RENDERED text supplied by the caller from
    custodied bytes (``candidate_list_text`` from the Perception candidate
    ids of S3-3's ``trajectory`` block; the three answers from the sealed
    rollout's own custody; ``reviewer_verdicts_text`` / ``planner_route_text``
    from the sealed episode receipt's labels). This module neither opens a
    seal nor decides what a label means.
    """

    if not isinstance(template_text, str) or not template_text.strip():
        raise Stage3AdvantageError("template_text must be a non-empty string")
    missing = [key for key in V2_TEMPLATE_PLACEHOLDERS if key not in template_text]
    if missing:
        raise Stage3AdvantageError(
            f"advantage v2 template is missing placeholder(s): {missing}"
        )
    values = {
        "{candidate_list}": candidate_list_text,
        "{best_answer}": best_answer_text,
        "{worst_answer}": worst_answer_text,
        "{delivered_answer}": delivered_answer_text,
        "{reviewer_verdicts}": reviewer_verdicts_text,
        "{planner_route}": planner_route_text,
        "{gold}": gold_text,
    }
    rendered = template_text
    for placeholder, value in values.items():
        if not isinstance(value, str):
            raise Stage3AdvantageError(
                f"advantage v2 material {placeholder} must be text"
            )
        rendered = rendered.replace(placeholder, value)
    return rendered


def build_advantage_instruction_for_row_v2(
    template_text: str, pair: AdvantagePair, **material: str
) -> str:
    """The reusable per-row unit a v2 launcher's ``material_for_phase``
    override calls once (``pair`` identifies WHICH sample indices supplied
    the two answers, so a caller can assert it read the right custodied
    bytes before calling this)."""

    pair.validate()
    return render_advantage_instruction_v2(template_text, **material)


def stage3_advantage_response_format_v2(
    _lock: Mapping[str, object], _root: Path, **_params: object
) -> Mapping[str, object]:
    """The v2 structured-decoding contract registered under
    :data:`STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID_V2`.

    One to three blocks, each carrying the four fields of the four-line
    form. :func:`parse_advantage_statements_v2` stays the parser of record
    and reads this JSON shape directly (``_v2_blocks_from_json``), so the
    schema and the parser are one contract rather than two.
    """

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "saea_stage3_advantage_statement_v2",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["blocks"],
                "properties": {
                    "blocks": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_ADVANTAGE_BLOCKS,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["node", "delta_kind", "target", "statement"],
                            "properties": {
                                "node": {"type": "string", "enum": list(LEGAL_DELTA_NODES)},
                                "delta_kind": {
                                    "type": "string",
                                    "enum": list(LEGAL_DELTA_KINDS_V2),
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
    "LEGAL_DELTA_KINDS",
    "LEGAL_DELTA_KINDS_V2",
    "LEGAL_DELTA_NODES",
    "MAX_ADVANTAGE_BLOCKS",
    "MAX_STATEMENT_WORDS",
    "STAGE3_ADVANTAGE_ARM",
    "STAGE3_ADVANTAGE_PHASE_NAME",
    "STAGE3_ADVANTAGE_PROGRAM_ID",
    "STAGE3_ADVANTAGE_PROGRAM_ID_V2",
    "STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID",
    "STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID_V2",
    "STAGE3_ADVANTAGE_SYSTEM_TEMPLATE_RELPATH_V2",
    "STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2",
    "V2_TEMPLATE_PLACEHOLDERS",
    "AdvantageBlock",
    "AdvantagePair",
    "AdvantagePairSample",
    "AdvantagePairs",
    "AdvantageStatement",
    "AdvantageStatementSet",
    "Stage3AdvantageError",
    "build_advantage_instruction_for_row",
    "build_advantage_instruction_for_row_v2",
    "load_advantage_pairs",
    "parse_advantage_statement",
    "parse_advantage_statements_v2",
    "render_advantage_instruction",
    "render_advantage_instruction_v2",
    "stage3_advantage_response_format_v1",
    "stage3_advantage_response_format_v2",
]
