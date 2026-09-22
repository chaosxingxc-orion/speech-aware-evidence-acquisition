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


__all__ = [
    "LEGAL_DELTA_KINDS",
    "MAX_STATEMENT_WORDS",
    "STAGE3_ADVANTAGE_ARM",
    "STAGE3_ADVANTAGE_PHASE_NAME",
    "STAGE3_ADVANTAGE_PROGRAM_ID",
    "STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID",
    "AdvantagePair",
    "AdvantagePairSample",
    "AdvantagePairs",
    "AdvantageStatement",
    "Stage3AdvantageError",
    "build_advantage_instruction_for_row",
    "load_advantage_pairs",
    "parse_advantage_statement",
    "render_advantage_instruction",
    "stage3_advantage_response_format_v1",
]
