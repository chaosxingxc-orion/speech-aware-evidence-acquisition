"""Deterministic DELIVERY normalisers: the delivery-time node of the native
episode (E11, 2026-09-18, owner directive 26).

Owner directive 26 of 2026-09-18 ("analyses into nodes"): an offline analysis
this program trusts must be placed INSIDE an agent node, not only reported
beside the number. Owner decision 23 of 2026-09-18 fixes the bar and every
final evaluation on the OFFICIAL, unprojected SLURP ``evaluate.py`` number.
Together those two make the SLURP USE projection v3 (module M3) a runtime
question rather than a scorer question: while the rule lives in the scorer
(``slurp-slu-official-projected-v3[-train]``, item E4) the official scorer
does not credit it, and the same rule applied INSIDE the episode, before the
answer is delivered, is credited by the official scorer like any other
answer the system produced.

This module is the canonical registration site for
``core.base.DELIVERY_NORMALISERS``, mirroring ``rails/commit_policies.py``'s
relationship to ``core.base.COMMIT_POLICIES``: the registry lives in
``core.base``, the concrete entry lives beside its implementation, and a
caller resolves the registered id through a function-local deferred import
(``rails.native_episode_config.load_native_episode_config``).

ONE IMPLEMENTATION, TWO CALLERS. The entry registered here does NOT restate
projection v3. It calls
:func:`rails.slurp_projection_v3.apply_slurp_projection_v3_delivery`, which
is the same pair of functions
(:func:`rails.slurp_projection_v3.project_slu_label_v3`,
:func:`rails.slurp_projection_v3.normalize_filler_p2`) the v3 SCORER applies
in ``reproduction.slurp_official_eval``. A second implementation of the rule
is exactly what would let the runtime form and the scorer form drift apart,
and the E11 byte-equality test
(``tests/unit/test_deliver_normaliser_node.py``) pins that they do not.

ZERO CONTACT. Applying the node makes no model, tokenizer, encoder, tool,
server or network contact of any kind, and reads no gold for the row it is
rewriting: the label half needs the 60-id legal intent inventory (mined from
TRAIN, the same closed list the task contract already renders into the
prompt) and the filler half needs nothing beyond the text. It therefore
changes no request byte, spends no budget and is replayable offline from
sealed bytes (``analysis.deliver_normaliser_replay``).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..core.base import DELIVERY_NORMALISERS, DeliveryNormalisation, DeliveryNormaliserError
from .solver_citation import (
    DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1,
    DELIVER_CITED_ANSWER_NORMALISE_V3_V1,
    DELIVER_CITED_ANSWER_V1,
    SolverCitationError,
    parse_cited_answer,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..reproduction.slurp_scoring import LegalIntentInventory

#: The receipt schema the episode seals under
#: ``native_episode_receipt.deliver_normaliser``. Bumped only when the
#: receipt's FIELD SET changes; the rule's own identity travels in
#: ``rule_id`` / ``normaliser_id`` / ``version``.
DELIVER_NORMALISER_RECEIPT_SCHEMA = "saea-deliver-normaliser-v1"

#: The one normaliser this module registers (E11). A
#: ``native_episode.deliver_normaliser.normaliser`` value resolves to this id
#: in ``core.base.DELIVERY_NORMALISERS``.
DELIVER_NORMALISE_V3 = "saea-deliver-normalise-v3"

#: Bumped when the RULE changes, never when this file is merely edited: an
#: admission receipt and a preregistration quote it.
DELIVER_NORMALISE_V3_VERSION = "1"

#: Item E35 (owner decision 89, 2026-09-21): the Earnings21+ConEC delivery
#: normaliser this module registers alongside the SLURP one. A
#: ``native_episode.deliver_normaliser.normaliser`` value of this id resolves
#: here in ``core.base.DELIVERY_NORMALISERS``.
DELIVER_NORMALISE_EARNINGS_TEXT_V1 = "saea-deliver-earnings-text-v1"

#: Bumped when the HYGIENE RULE changes, never when this file is merely
#: edited: an admission receipt and a preregistration quote it.
DELIVER_NORMALISE_EARNINGS_TEXT_V1_VERSION = "1"

#: Separate carrier identity for the same transcript hygiene, not an E22
#: measurement or admission. Existing E21 receipts retain their original id.
DELIVER_NORMALISE_EARNINGS22_TEXT_V1 = "saea-deliver-earnings22-text-v1"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SlurpProjectionV3DeliveryNormaliser:
    """``saea-deliver-normalise-v3``: SLURP USE projection v3, applied once to
    the accepted answer, immediately before delivery.

    Pure and deterministic. The input is the delivered structured answer of
    the native episode (``{"scenario", "action", "entities": [{type,
    filler}]}``, the shape
    :func:`reproduction.slurp_scoring.parse_slu_response` parses); the output
    is the same answer after the label rule ``R_action`` then the registered
    legal-label projection v2, and then the filler normalisation P2 (case,
    whitespace, punctuation, meridiem, numeric words; NO support filter,
    rejected by the A1 audit). An answer the parser refuses is returned
    byte-identically, with ``applied: false`` and the reason recorded --
    there is no label or filler to project, and inventing one would be the
    node writing an answer rather than normalising one.

    IDEMPOTENT by construction and pinned by test: the label rule leaves an
    already-legal pair alone and the filler rule is a fixed point on its own
    output, so re-applying the node (or running the v3 SCORER over an
    already-normalised row) changes nothing.

    ONE FACTOR, DOWN TO THE BYTE: when the rule repairs neither a label nor a
    filler, the accepted answer is delivered VERBATIM rather than re-rendered
    in the canonical JSON shape (see :meth:`__call__`), so an ON arm differs
    from its comparator exactly on the rows the rule repairs.
    """

    id = DELIVER_NORMALISE_V3
    version = DELIVER_NORMALISE_V3_VERSION
    #: The ONE carrier this rule is defined for. ``rails.native_episode_config``
    #: refuses a fragment that arms it on any other carrier, before contact.
    carrier_lock_key = "slurp"

    def __call__(
        self, text: str, *, inventory: "LegalIntentInventory | None" = None
    ) -> DeliveryNormalisation:
        """Normalise one delivered answer.

        ``inventory`` is an optional injection point for tests and for the
        offline replay: left ``None`` (every runtime call) the rule loads the
        real TRAIN-mined legal intent inventory once per process, exactly as
        the v3 scorer does.
        """

        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        # Deferred: rails.slurp_projection_v3 pulls reproduction.slurp_scoring,
        # and this module is imported for its REGISTRATION side effect from
        # config loading and bundle verification, which must stay import-light.
        from .slurp_projection_v3 import (  # noqa: PLC0415
            apply_slurp_projection_v3_delivery,
        )

        outcome = apply_slurp_projection_v3_delivery(
            text, carrier_lock_key=self.carrier_lock_key, inventory=inventory
        )
        metadata = dict(outcome.metadata)
        applied = bool(metadata.get("applied"))
        labels_changed = int(bool(metadata.get("label_changed"))) if applied else 0
        fillers_changed = int(metadata.get("fillers_changed") or 0) if applied else 0
        # ONE FACTOR, DOWN TO THE BYTE. ``apply_slurp_projection_v3_delivery``
        # always RE-RENDERS the answer it parsed, so on a row the rule does
        # not repair it still returns different bytes -- the model's own JSON
        # spacing and key order replaced by the canonical rendering. On the
        # sealed B1 arm that is 1,076 of 1,080 rows against 24 repaired
        # labels and 82 repaired fillers, i.e. almost the whole arm changed
        # for no reason a verdict could read. The NODE therefore delivers the
        # accepted answer VERBATIM whenever the rule moved neither a label
        # nor a filler, so the ON arm differs from its comparator exactly on
        # the rows the rule actually repairs, and ``changed`` means "the rule
        # repaired this row" rather than "the serialiser disagreed". The
        # scored triple is identical either way -- the official scorer parses
        # both renderings to the same (scenario, action, entities) -- which is
        # why suppressing the re-render costs nothing and is pinned by the
        # sealed-byte equality test. The SEAL-time E4 transform keeps its own
        # behaviour; only this node suppresses.
        rendering_suppressed = bool(outcome.changed) and not (
            labels_changed or fillers_changed
        )
        delivered = text if rendering_suppressed else outcome.text
        changed = delivered != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": str(metadata.get("rule_id")),
            "carrier_lock_key": self.carrier_lock_key,
            "applied": applied,
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            # Intent accuracy may move ONLY through the label half and the
            # entity block never changes labels (the A1 audit's own contract),
            # so the two counts are kept apart rather than summed.
            "labels_changed": labels_changed,
            "label_branch": metadata.get("label_branch") if applied else None,
            "fillers_changed": fillers_changed,
            # True when the rule repaired nothing and the accepted answer was
            # therefore delivered verbatim rather than re-rendered.
            "rendering_suppressed": rendering_suppressed,
            "reason": None if applied else str(metadata.get("reason")),
        }
        return DeliveryNormalisation(
            text=delivered, changed=changed, receipt=receipt
        ).validate()


class EarningsTextDeliveryNormaliser:
    """``saea-deliver-earnings-text-v1``: deterministic Earnings21+ConEC
    delivery hygiene, applied once to the delivered transcript text,
    immediately before delivery.

    Item E35 (owner decision 89, 2026-09-21): the Earnings21+ConEC carrier's
    own delivery-time node, so it can fly the same six-node native episode
    SLURP flies through the shared harness. Unlike the SLURP v3 rule, this
    normaliser applies NO scoring-adjacent transform at all: the standard
    Earnings scorer (``asr-wer-whisper``) already owns Whisper text
    normalisation, and no entity or numeric rewriting belongs in an agent
    node (study CLAUDE.md's OBS/ORG/SUPPLY/USE separation). It removes only
    deterministic, documented TEXT HYGIENE the episode's own role-graph
    markup may have added around the Solver's final transcript, IN ORDER:

    1. strip one leading role/label wrapper the episode's own instruction
       vocabulary might add (``"Transcript:"``, ``"Answer:"``, ``"Final:"``,
       case-insensitive, at most once, only at the very start);
    2. strip one surrounding pair of XML-ish tags, if the WHOLE remaining
       text is wrapped (``<transcript>...</transcript>``,
       ``<answer>...</answer>``, case-insensitive);
    3. strip one surrounding pair of Markdown code fences, if the WHOLE
       remaining text is wrapped (```` ```...``` ````, with or without a
       language tag on the opening fence);
    4. collapse every run of ASCII whitespace (spaces, tabs, newlines) to a
       single space and strip leading/trailing whitespace.

    Byte-identical passthrough when none of the above matches anything: the
    delivered text equals the input exactly, and ``changed`` is false.

    E13 (``deliver-latest-or-abstain``): if the hygiene above leaves nothing
    (the input was empty, or contained only wrapper markup and whitespace),
    this normaliser REFUSES rather than deliver a blank transcript as if it
    were content -- the episode's own finite-completion policy is the layer
    authorized to decide an abstain outcome, not this node inventing one.
    """

    id = DELIVER_NORMALISE_EARNINGS_TEXT_V1
    version = DELIVER_NORMALISE_EARNINGS_TEXT_V1_VERSION
    #: The ONE carrier this rule is defined for. ``rails.native_episode_config``
    #: refuses a fragment that arms it on any other carrier, before contact.
    carrier_lock_key = "earnings21-original"

    _LABEL_PREFIX = re.compile(
        r"^\s*(transcript|answer|final)\s*:\s*", re.IGNORECASE
    )
    _TAG_WRAPPER = re.compile(
        r"^\s*<(transcript|answer)>(.*)</" r"\1" r">\s*$",
        re.IGNORECASE | re.DOTALL,
    )
    _FENCE_WRAPPER = re.compile(
        r"^\s*```(?:[A-Za-z0-9_-]*" "\n" r")?(.*?)```\s*$", re.DOTALL
    )
    _WHITESPACE_RUN = re.compile(r"\s+")

    def __call__(self, text: str) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        hygiened = self._LABEL_PREFIX.sub("", text, count=1)
        tag_match = self._TAG_WRAPPER.match(hygiened)
        if tag_match is not None:
            hygiened = tag_match.group(2)
        fence_match = self._FENCE_WRAPPER.match(hygiened)
        if fence_match is not None:
            hygiened = fence_match.group(1)
        hygiened = self._WHITESPACE_RUN.sub(" ", hygiened).strip()
        if not hygiened:
            raise DeliveryNormaliserError(
                f"{self.id}: delivered text is empty after hygiene; abstain "
                "(E13 deliver-latest-or-abstain) rather than deliver a blank "
                "transcript"
            )
        changed = hygiened != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": "earnings-text-hygiene-v1",
            "carrier_lock_key": self.carrier_lock_key,
            "applied": changed,
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(hygiened),
            "reason": None,
        }
        return DeliveryNormalisation(text=hygiened, changed=changed, receipt=receipt).validate()


class Earnings22TextDeliveryNormaliser(EarningsTextDeliveryNormaliser):
    """Reuse transcript hygiene with E22 custody; add no sources or scoring rules."""

    id = DELIVER_NORMALISE_EARNINGS22_TEXT_V1
    carrier_lock_key = "earnings22-original"


#: Bumped when the UNWRAP RULE changes, never when this file is merely
#: edited: an admission receipt and a preregistration quote it.
DELIVER_CITED_ANSWER_V1_VERSION = "1"
DELIVER_CITED_ANSWER_NORMALISE_V3_V1_VERSION = "1"


class CitedAnswerUnwrapDeliveryNormaliser:
    """``saea-deliver-cited-answer-v1``: deliver the ANSWER of a cited-answer
    envelope (``rails.solver_citation``), applied once, immediately before
    delivery.

    Gap G1 plumbing. Under the cited-answer contract the Solver's model
    response is ``{"schema", "answer", "citations"}``; the answer the row
    delivers is the ``answer`` member's OWN BYTES, cut from the raw response
    by :func:`rails.solver_citation.answer_span` -- the model's spacing and
    key order, never a re-serialisation -- so the citation is metadata beside
    the answer and never part of the delivered text. Pure and deterministic:
    the same recorded response always yields the same bytes, which is what
    invariant I7n replays at the seal and in the bundle.

    Text the contract's parser refuses is delivered VERBATIM with
    ``applied: false`` and the reason recorded, exactly as the v3 rule treats
    an unparsed answer: the only way such text reaches delivery is the
    finite-completion path (a truncated envelope the episode's own policy
    chose to deliver), and a normaliser that invented an answer would be the
    node writing one rather than unwrapping one.
    ``rails.native_episode_config`` refuses a fragment that arms this rule
    without the contract, or the contract without this rule (or its v3
    composition below), so an envelope is never delivered as an answer.
    """

    id = DELIVER_CITED_ANSWER_V1
    version = DELIVER_CITED_ANSWER_V1_VERSION
    #: The contract cites intents and entities, the SLURP task's own shape.
    carrier_lock_key = "slurp"

    def __call__(self, text: str) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        try:
            parsed = parse_cited_answer(text)
        except SolverCitationError as error:
            delivered, applied, reason, cited = text, False, str(error), ()
        else:
            delivered, applied, reason, cited = (
                parsed.answer_text, True, None, parsed.cited_value_ids
            )
        changed = delivered != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": "cited-answer-unwrap-v1",
            "carrier_lock_key": self.carrier_lock_key,
            "applied": applied,
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            # Counts and a digest only; the ids themselves are sealed on the
            # Solver state's ``cited_value_ids`` and in the row's
            # ``solver_citations`` receipt block.
            "cited_value_ids_count": len(cited),
            "cited_value_ids_sha256": _sha256(json.dumps(list(cited))),
            "reason": reason,
        }
        return DeliveryNormalisation(text=delivered, changed=changed, receipt=receipt).validate()


class CitedAnswerNormaliseV3DeliveryNormaliser:
    """``saea-deliver-cited-answer-normalise-v3-v1``: the unwrap above, then
    the locked plan's own ``saea-deliver-normalise-v3`` over the unwrapped
    answer, as ONE registered rule.

    ``native_episode.deliver_normaliser`` names exactly one normaliser and the
    v2.0 lock already spends it on projection v3, so a cell that arms the
    cited-answer contract on the locked plan needs the composition under one
    id. It composes the two REGISTERED callables rather than restating either
    rule (one implementation, two callers, the discipline this module states
    for v3 itself); the receipt carries both stage receipts under ``stages``
    beside the top-level input/output digests I7n binds.
    """

    id = DELIVER_CITED_ANSWER_NORMALISE_V3_V1
    version = DELIVER_CITED_ANSWER_NORMALISE_V3_V1_VERSION
    carrier_lock_key = "slurp"

    def __call__(
        self, text: str, *, inventory: "LegalIntentInventory | None" = None
    ) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        unwrap = DELIVERY_NORMALISERS.resolve(DELIVER_CITED_ANSWER_V1)(text)
        projected = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)(
            unwrap.text, inventory=inventory
        )
        delivered = projected.text
        changed = delivered != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": "cited-answer-unwrap-then-slurp-use-projection-v3",
            "carrier_lock_key": self.carrier_lock_key,
            "applied": bool(unwrap.receipt["applied"]) or bool(projected.receipt["applied"]),
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            "labels_changed": projected.receipt["labels_changed"],
            "label_branch": projected.receipt["label_branch"],
            "fillers_changed": projected.receipt["fillers_changed"],
            "stages": [dict(unwrap.receipt), dict(projected.receipt)],
            "reason": None,
        }
        return DeliveryNormalisation(text=delivered, changed=changed, receipt=receipt).validate()


# ---------------------------------------------------------------------------
# The do-not-tag SCOPE-RULE stage (evidence-consumption module, migration
# step 3; owner decision 195 = B; coordinator ruling R5).
# ---------------------------------------------------------------------------

#: The stage's registered id. A deliver-normaliser STAGE: it takes the
#: delivered answer text like every normaliser, and it is composed AFTER
#: ``saea-deliver-normalise-v3`` under one registered id (below), because
#: ``native_episode.deliver_normaliser`` names exactly one normaliser.
DELIVER_SCOPE_RULE_V1 = "saea-deliver-scope-rule-v1"
#: Bumped when the RULE or its pinned table changes, never when this file is
#: merely edited.
DELIVER_SCOPE_RULE_V1_VERSION = "1"
#: The sub-receipt's rule id (receipt ``rule_id``).
SCOPE_RULE_ID = "slurp-do-not-tag-scope-rule-v1"
#: The pinned pool-statistics table (``scripts/build_slurp_scope_rule_table.py``,
#: receipt ``docs/receipts/knowledge/slurp-scope-rule-table-v1.json``, exposure
#: row ``SAEA-SLURP-SCOPE-RULE-TABLE-BUILD-V1``). Built model-free from TRAIN
#: minus Fold A, minus Fold B, minus R01/R01C (ruling R5). It lives under the
#: data root (its keys are TRAIN phrases, never committed); its sha256 is the
#: stage's identity and every receipt carries it.
SCOPE_RULE_TABLE_SCHEMA = "saea-slurp-scope-rule-table-v1"
SCOPE_RULE_TABLE_RELPATH = "prepared/SAEA-SLURP-SCOPE-RULE-TABLE-V1/table-v1.json"
SCOPE_RULE_TABLE_SHA256 = "fcff0c42ca0e3c30ed56cc1f137d85b255d0ecea876ea4fe8efae560f2c58df5"
#: The rule's registered thresholds, fixed by the offline read
#: (``docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md``)
#: before its first run: drop a delivered entity whose phrase occurs in at
#: least 5 pool exemplars and is untagged in at least 80 % of them.
SCOPE_RULE_MIN_POOL_OCCURRENCES = 5
SCOPE_RULE_UNTAGGED_SHARE = 0.8

#: The composed ids (one registered rule each, the cited-v3 precedent).
DELIVER_NORMALISE_V3_SCOPE_RULE_V1 = "saea-deliver-normalise-v3-scope-rule-v1"
DELIVER_NORMALISE_V3_SCOPE_RULE_V1_VERSION = "1"
DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1_VERSION = "1"
#: ``{base normaliser id: the base composed with the scope stage}`` -- what
#: the module's ``scope-rule`` component compiles the deliver node to.
SCOPE_RULE_COMPOSITIONS: dict[str, str] = {}

#: The exact key set of the stage's sub-receipt (``validate_scope_rule_receipt``).
SCOPE_RULE_RECEIPT_KEYS = frozenset({
    "schema", "normaliser_id", "version", "rule_id", "carrier_lock_key", "applied",
    "changed", "input_sha256", "output_sha256", "table_relpath", "table_sha256",
    "min_pool_occurrences", "untagged_share", "entities_in", "dropped_entity_indices",
    "reason",
})


class ScopeRuleTable:
    """The pinned pool statistics: ``phrase -> (pool occurrences, tagged
    occurrences)``, keyed by the space-joined folded tokens
    (``analysis.sealed_credit.entity_states.fold``). Rows below the table's own
    occurrence floor are absent (an absent phrase is never dropped)."""

    __slots__ = ("rows", "sha256", "floor")

    def __init__(self, rows: dict[str, tuple[int, int]], *, sha256: str, floor: int) -> None:
        self.rows = rows
        self.sha256 = sha256
        self.floor = floor

    @classmethod
    def from_bytes(cls, data: bytes, *, expected_sha256: str | None) -> "ScopeRuleTable":
        digest = hashlib.sha256(data).hexdigest()
        if expected_sha256 is not None and digest != expected_sha256:
            raise DeliveryNormaliserError(
                f"{DELIVER_SCOPE_RULE_V1}: the scope-rule table hashes to {digest[:12]}..., "
                f"not the pinned {expected_sha256[:12]}..."
            )
        document = json.loads(data.decode("utf-8"))
        if not isinstance(document, dict) or document.get("schema") != SCOPE_RULE_TABLE_SCHEMA:
            raise DeliveryNormaliserError(
                f"{DELIVER_SCOPE_RULE_V1}: the table schema must be {SCOPE_RULE_TABLE_SCHEMA!r}"
            )
        floor = document.get("min_pool_occurrences_floor")
        raw = document.get("rows")
        if not isinstance(floor, int) or floor < 1 or not isinstance(raw, dict):
            raise DeliveryNormaliserError(f"{DELIVER_SCOPE_RULE_V1}: malformed scope-rule table")
        rows: dict[str, tuple[int, int]] = {}
        for phrase, counts in raw.items():
            if (
                not isinstance(counts, list) or len(counts) != 2
                or not all(isinstance(c, int) for c in counts)
                or counts[0] < floor or not 0 <= counts[1] <= counts[0]
            ):
                raise DeliveryNormaliserError(f"{DELIVER_SCOPE_RULE_V1}: malformed table row")
            rows[phrase] = (counts[0], counts[1])
        return cls(rows, sha256=digest, floor=floor)


_DEFAULT_SCOPE_RULE_TABLE: list[ScopeRuleTable] = []


def default_scope_rule_table() -> ScopeRuleTable:
    """The pinned table under ``SPEECHRL_DATA_DIR``, loaded once per process
    and refused unless it hashes to :data:`SCOPE_RULE_TABLE_SHA256`."""

    if not _DEFAULT_SCOPE_RULE_TABLE:
        from ..data.lock import data_root  # noqa: PLC0415

        path = data_root() / SCOPE_RULE_TABLE_RELPATH
        _DEFAULT_SCOPE_RULE_TABLE.append(
            ScopeRuleTable.from_bytes(path.read_bytes(), expected_sha256=SCOPE_RULE_TABLE_SHA256)
        )
    return _DEFAULT_SCOPE_RULE_TABLE[0]


def scope_rule_phrase(filler: str) -> str:
    """The table key of one delivered filler: its folded tokens, space-joined
    -- the offline read's ``tuple(fold(filler).split())``."""

    from ..analysis.sealed_credit.entity_states import fold  # noqa: PLC0415

    return " ".join(fold(filler).split())


def scope_rule_drops(
    fillers: "list[str] | tuple[str, ...]",
    table: ScopeRuleTable,
    *,
    min_pool_occurrences: int = SCOPE_RULE_MIN_POOL_OCCURRENCES,
    untagged_share: float = SCOPE_RULE_UNTAGGED_SHARE,
) -> tuple[int, ...]:
    """The indices of the delivered entities the rule drops: phrase in at
    least ``min_pool_occurrences`` pool exemplars and untagged in at least
    ``untagged_share`` of them (the offline read's arithmetic, operand for
    operand: ``1.0 - tagged / occurrences >= share``)."""

    if min_pool_occurrences < table.floor:
        raise DeliveryNormaliserError(
            f"{DELIVER_SCOPE_RULE_V1}: min_pool_occurrences {min_pool_occurrences} is below "
            f"the table's floor {table.floor}"
        )
    drops = []
    for index, filler in enumerate(fillers):
        counts = table.rows.get(scope_rule_phrase(filler))
        if counts is None:
            continue
        occurrences, tagged = counts
        if occurrences >= min_pool_occurrences and 1.0 - tagged / occurrences >= untagged_share:
            drops.append(index)
    return tuple(drops)


class ScopeRuleDeliveryStage:
    """``saea-deliver-scope-rule-v1``: the do-not-tag scope rule, applied once
    to the delivered answer after the projection.

    Pure and deterministic given its pinned table. It parses the delivered
    answer with the SAME parser the official scorer's adapter uses
    (:func:`reproduction.slurp_scoring.parse_slu_response`), drops every
    entity the rule selects (:func:`scope_rule_drops`) and re-renders the
    answer canonically (:func:`rails.slurp_projection_v3.render_slurp_answer`)
    ONLY when it dropped something: a row it leaves alone is delivered
    VERBATIM (one factor, down to the byte, as the v3 node). An unparsed
    answer is delivered verbatim with ``applied: false``. Never changes a
    label; never adds an entity. Zero contact.
    """

    id = DELIVER_SCOPE_RULE_V1
    version = DELIVER_SCOPE_RULE_V1_VERSION
    carrier_lock_key = "slurp"

    def __call__(self, text: str, *, table: ScopeRuleTable | None = None) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        from ..reproduction.slurp_scoring import parse_slu_response  # noqa: PLC0415
        from .slurp_projection_v3 import render_slurp_answer  # noqa: PLC0415

        if table is None:
            table = default_scope_rule_table()
        scenario, action, entities, parsed = parse_slu_response(text)
        drops: tuple[int, ...] = ()
        delivered = text
        if parsed:
            drops = scope_rule_drops([entity.filler for entity in entities], table)
            if drops:
                kept = [entity for i, entity in enumerate(entities) if i not in drops]
                delivered = render_slurp_answer(scenario, action, kept)
        changed = delivered != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": SCOPE_RULE_ID,
            "carrier_lock_key": self.carrier_lock_key,
            "applied": bool(parsed),
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            "table_relpath": SCOPE_RULE_TABLE_RELPATH,
            "table_sha256": table.sha256,
            "min_pool_occurrences": SCOPE_RULE_MIN_POOL_OCCURRENCES,
            "untagged_share": SCOPE_RULE_UNTAGGED_SHARE,
            "entities_in": len(entities),
            # Indices into the parsed entity list, never the fillers.
            "dropped_entity_indices": list(drops),
            "reason": None if parsed else "unparsed",
        }
        return DeliveryNormalisation(text=delivered, changed=changed, receipt=receipt).validate()


def validate_scope_rule_receipt(receipt: object) -> "dict[str, object]":
    """Refuse a scope-stage sub-receipt that is not exactly the stage's shape
    or that does not bind the pinned table and thresholds."""

    if not isinstance(receipt, dict) or set(receipt) != SCOPE_RULE_RECEIPT_KEYS:
        raise DeliveryNormaliserError(
            f"a {DELIVER_SCOPE_RULE_V1} receipt carries exactly {sorted(SCOPE_RULE_RECEIPT_KEYS)}"
        )
    expected = {
        "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA, "normaliser_id": DELIVER_SCOPE_RULE_V1,
        "rule_id": SCOPE_RULE_ID, "table_relpath": SCOPE_RULE_TABLE_RELPATH,
        "min_pool_occurrences": SCOPE_RULE_MIN_POOL_OCCURRENCES,
        "untagged_share": SCOPE_RULE_UNTAGGED_SHARE,
    }
    for key, value in expected.items():
        if receipt[key] != value:
            raise DeliveryNormaliserError(f"{DELIVER_SCOPE_RULE_V1} receipt {key} must be {value!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(receipt["table_sha256"])):
        raise DeliveryNormaliserError(f"{DELIVER_SCOPE_RULE_V1} receipt table_sha256 must be 64-hex")
    indices = receipt["dropped_entity_indices"]
    if (
        not isinstance(indices, list) or indices != sorted(set(indices))
        or not all(isinstance(i, int) and 0 <= i < int(receipt["entities_in"]) for i in indices)
    ):
        raise DeliveryNormaliserError(
            f"{DELIVER_SCOPE_RULE_V1} receipt dropped_entity_indices must be sorted, unique "
            "indices into the parsed entities"
        )
    if bool(indices) != bool(receipt["changed"]):
        raise DeliveryNormaliserError(
            f"{DELIVER_SCOPE_RULE_V1} receipt: changed must hold exactly when an entity was dropped"
        )
    return receipt


class _ScopeRuleComposition:
    """A registered base normaliser, then the scope stage, as ONE registered
    rule. It composes the two REGISTERED callables (one implementation, two
    callers); the receipt carries the base's own stage receipts (or the base
    receipt itself) and the scope sub-receipt under ``stages``, beside the
    top-level input/output digests I7n binds."""

    id = ""
    version = ""
    base_id = ""
    carrier_lock_key = "slurp"

    def __call__(
        self,
        text: str,
        *,
        inventory: "LegalIntentInventory | None" = None,
        table: ScopeRuleTable | None = None,
    ) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        base = DELIVERY_NORMALISERS.resolve(self.base_id)(text, inventory=inventory)
        scoped = DELIVERY_NORMALISERS.resolve(DELIVER_SCOPE_RULE_V1)(base.text, table=table)
        delivered = scoped.text
        base_stages = base.receipt.get("stages")
        stages = (
            [dict(r) for r in base_stages] if isinstance(base_stages, list)
            else [dict(base.receipt)]
        )
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": f"{base.receipt['rule_id']}-then-{SCOPE_RULE_ID}",
            "carrier_lock_key": self.carrier_lock_key,
            "applied": bool(base.receipt["applied"]) or bool(scoped.receipt["applied"]),
            "changed": delivered != text,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            "labels_changed": base.receipt["labels_changed"],
            "label_branch": base.receipt["label_branch"],
            "fillers_changed": base.receipt["fillers_changed"],
            "entities_dropped": len(scoped.receipt["dropped_entity_indices"]),
            "stages": [*stages, dict(scoped.receipt)],
            "reason": None,
        }
        return DeliveryNormalisation(
            text=delivered, changed=delivered != text, receipt=receipt
        ).validate()


class NormaliseV3ScopeRuleDeliveryNormaliser(_ScopeRuleComposition):
    """``saea-deliver-normalise-v3-scope-rule-v1``: projection v3, then the
    scope stage (the module's ``scope-rule`` component over the lock's
    deliver node)."""

    id = DELIVER_NORMALISE_V3_SCOPE_RULE_V1
    version = DELIVER_NORMALISE_V3_SCOPE_RULE_V1_VERSION
    base_id = DELIVER_NORMALISE_V3


class CitedAnswerNormaliseV3ScopeRuleDeliveryNormaliser(_ScopeRuleComposition):
    """``saea-deliver-cited-answer-normalise-v3-scope-rule-v1``: the cited
    unwrap, projection v3, then the scope stage (``scope-rule`` over the
    citation contract's deliver node)."""

    id = DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1
    version = DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1_VERSION
    base_id = DELIVER_CITED_ANSWER_NORMALISE_V3_V1


SCOPE_RULE_COMPOSITIONS.update({
    DELIVER_NORMALISE_V3: DELIVER_NORMALISE_V3_SCOPE_RULE_V1,
    DELIVER_CITED_ANSWER_NORMALISE_V3_V1: DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1,
})


# ---------------------------------------------------------------------------
# Projection v4 (NX round R0.4, 2026-10-09): ``saea-deliver-normalise-v4``.
#
# Selected offline on cell A2 and confirmed once on TRAIN Fold A
# (``docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md``,
# driver ``scripts/analysis/slurp_nx_postproc_v4_search.py``): v3, then a
# deterministic ENTITY stage of five rules in a fixed order. Its TRAIN
# statistics are frozen as four pinned tables
# (``scripts/build_slurp_v4_train_statistics.py``, receipt
# ``docs/receipts/knowledge/slurp-v4-train-statistics-v1.json``, exposure row
# ``SAEA-SLURP-V4-TRAIN-STATISTICS-BUILD-V1``), built model-free from the same
# R5 pool the scope table was built from. They live under the data root, like
# the scope table, and each table's sha256 is part of the rule's identity.
#
# REGISTERED, NOT ARMED. The id resolves in ``core.base.DELIVERY_NORMALISERS``
# so a config CAN name it and the bundle verifier CAN replay it. No cell,
# fragment or lock names it yet: which cells use v4 is the owner's lock
# decision and a separate wiring step. The audio attribution
# (``docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md``)
# must be read before that decision.
#
# Statistics may still be INJECTED (``stats=``), for tests. A call without
# them loads the pinned tables, and refuses any table that does not hash to
# its pin.
# ---------------------------------------------------------------------------

DELIVER_NORMALISE_V4 = "saea-deliver-normalise-v4"
#: Bumped when the RULE or a pinned table changes, never when this file is
#: merely edited.
DELIVER_NORMALISE_V4_VERSION = "1"
V4_RULE_ID = "slurp-use-projection-v4"
#: The entity stage, in its one application order (the offline read's order).
V4_STAGES: tuple[str, ...] = ("fx-article", "fx-oclock", "scope", "ti1", "ee10")
#: The determiners fx-article may strip (the offline read's candidate set).
V4_DETERMINERS: tuple[str, ...] = (
    "the", "a", "an", "my", "this", "next", "at", "in", "on", "to", "for", "your", "our",
)
V4_ARTICLE_MAX_INCLUDED_SHARE = 0.10
V4_ARTICLE_MIN_OPPORTUNITIES = 10
V4_OCLOCK_MIN_OPPORTUNITIES = 5
V4_OCLOCK_TOKENS = ("o'clock", "oclock")
V4_TI_MIN_SHARE = 0.01
V4_EE_MIN_ENTITY_RATE = 0.10
V4_STATS_SCHEMA = "saea-slurp-v4-train-statistics-v1"

#: The pinned TRAIN statistics (``scripts/build_slurp_v4_train_statistics.py``).
V4_STATS_ARTIFACT_ID = "SAEA-SLURP-V4-TRAIN-STATISTICS-V1"
#: The pool the tables were built from: the R5 pool of the scope table
#: (TRAIN minus Fold A, Fold B, R01 and R01C), by content hash.
V4_STATS_CONSTRUCTION_POOL = {
    "relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
    "content_sha256": "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63",
}
#: One table per TRAIN statistic, in a fixed order.
V4_TABLES: tuple[str, ...] = ("article-strip", "oclock", "type-by-intent", "intent-entity-rate")
V4_TABLE_SCHEMAS = {name: f"saea-slurp-v4-{name}-table-v1" for name in V4_TABLES}
V4_TABLE_RELPATHS = {name: f"prepared/{V4_STATS_ARTIFACT_ID}/{name}-v1.json" for name in V4_TABLES}
V4_TABLE_SHA256 = {
    "article-strip": "db42bf10a08ae9ccc51c656fd5cbbf8a636ee88a12b4c37100b5d69cf4d51b79",
    "oclock": "36779d582b0da541f55b90d3dcfc55ef7d3cfd6c4e3dfbec402daec5226399c7",
    "type-by-intent": "41a57d45bc434a3e42f3950590985d86f8598c38fdd8aba443d161c57059329d",
    "intent-entity-rate": "bd43804dd23868d2e4d6531f2ff305c1b0fd7a3a96cef4afaa28ab63793fac59",
}
#: The digest of the statistics the four pinned tables load into
#: (:attr:`SlurpV4Statistics.sha256`), recorded beside the table pins.
V4_STATS_SHA256 = "01e6a019c91f52bcd2941f593cfec9e8db120543334d46b9e643c29e4023f223"


def _v4_span_preceded_by(words: list, tokens: list, word: str) -> bool:
    n = len(tokens)
    return any(words[i:i + n] == tokens and words[i - 1] == word for i in range(1, len(words) - n + 1))


def _v4_span_followed_by(words: list, tokens: list, following: tuple) -> bool:
    n = len(tokens)
    return any(words[i:i + n] == tokens and words[i + n] in following for i in range(0, len(words) - n))


def v4_pool_counts(values) -> dict:
    """The raw TRAIN counts every v4 statistic is derived from, over an
    annotated exemplar pool in ``load_exemplar_pool``'s ``values`` shape. Slot
    TYPE names, determiner words and intent ids only; no filler, utterance or
    value survives. The arithmetic is the offline driver's ``TrainStats``,
    operand for operand (pinned by test)."""

    intent_n: dict[str, int] = {}
    with_entities: dict[str, int] = {}
    intent_type: dict[str, dict[str, int]] = {}
    included: dict[tuple, int] = {}
    excluded: dict[tuple, int] = {}
    oclock_in = oclock_out = 0
    for value in values.values():
        intent = value["intent"]
        intent_n[intent] = intent_n.get(intent, 0) + 1
        with_entities[intent] = with_entities.get(intent, 0) + int(bool(value["fillers"]))
        words = value["utterance"].split()
        for slot_type, fillers in value["fillers"].items():
            types = intent_type.setdefault(intent, {})
            types[slot_type] = types.get(slot_type, 0) + 1
            for filler in fillers:
                tokens = filler.split()
                if not tokens:
                    continue
                for word in V4_DETERMINERS:
                    key = (slot_type, word)
                    if tokens[0] == word and len(tokens) > 1:
                        included[key] = included.get(key, 0) + 1
                    elif _v4_span_preceded_by(words, tokens, word):
                        excluded[key] = excluded.get(key, 0) + 1
                if slot_type == "time":
                    if tokens[-1] in V4_OCLOCK_TOKENS:
                        oclock_in += 1
                    elif _v4_span_followed_by(words, tokens, V4_OCLOCK_TOKENS):
                        oclock_out += 1
    return {"intent_n": intent_n, "intent_with_entities": with_entities, "intent_type": intent_type,
            "article_included": included, "article_excluded": excluded,
            "oclock_included": oclock_in, "oclock_excluded": oclock_out}


def _v4_article_strip(rows: "dict[tuple, tuple[int, int]]") -> set:
    """``{(type, word)}`` whose pool span includes the word in < 10 % of >= 10
    opportunities; ``rows`` maps ``(type, word) -> (included, excluded)``."""

    strip = set()
    for key, (inc, exc) in rows.items():
        n = inc + exc
        if n >= V4_ARTICLE_MIN_OPPORTUNITIES and inc / n < V4_ARTICLE_MAX_INCLUDED_SHARE:
            strip.add(key)
    return strip


def _v4_oclock_strip(inc: int, exc: int) -> bool:
    n = inc + exc
    return n >= V4_OCLOCK_MIN_OPPORTUNITIES and inc / n < V4_ARTICLE_MAX_INCLUDED_SHARE


def _v4_table_bytes(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def v4_table_bytes(counts: dict, construction_pool: dict) -> "dict[str, bytes]":
    """The four pinned tables, as the bytes the builder writes, from
    :func:`v4_pool_counts`. Counts, thresholds and the derived decision only;
    the runtime re-derives every decision from the counts and refuses a table
    whose listed decision disagrees."""

    pool = {"relpath": str(construction_pool["relpath"]),
            "content_sha256": str(construction_pool["content_sha256"])}
    keys = set(counts["article_included"]) | set(counts["article_excluded"])
    rows = {k: (counts["article_included"].get(k, 0), counts["article_excluded"].get(k, 0)) for k in keys}
    common = {"artifact_id": V4_STATS_ARTIFACT_ID, "construction_pool": pool}
    intent_n = dict(sorted(counts["intent_n"].items()))
    documents = {
        "article-strip": {
            **common, "schema": V4_TABLE_SCHEMAS["article-strip"],
            "determiners": list(V4_DETERMINERS),
            "max_included_share": V4_ARTICLE_MAX_INCLUDED_SHARE,
            "min_opportunities": V4_ARTICLE_MIN_OPPORTUNITIES,
            "row_key": "slot type|determiner -> [included, excluded]",
            "rows": {f"{t}|{w}": list(rows[(t, w)]) for t, w in sorted(rows)},
            "strip": sorted([t, w] for t, w in _v4_article_strip(rows)),
        },
        "oclock": {
            **common, "schema": V4_TABLE_SCHEMAS["oclock"],
            "tokens": list(V4_OCLOCK_TOKENS), "slot_type": "time",
            "max_included_share": V4_ARTICLE_MAX_INCLUDED_SHARE,
            "min_opportunities": V4_OCLOCK_MIN_OPPORTUNITIES,
            "included": int(counts["oclock_included"]), "excluded": int(counts["oclock_excluded"]),
            "strip": _v4_oclock_strip(counts["oclock_included"], counts["oclock_excluded"]),
        },
        "type-by-intent": {
            **common, "schema": V4_TABLE_SCHEMAS["type-by-intent"],
            "min_share": V4_TI_MIN_SHARE, "intent_n": intent_n,
            "intent_type": {i: dict(sorted(t.items())) for i, t in sorted(counts["intent_type"].items())},
        },
        "intent-entity-rate": {
            **common, "schema": V4_TABLE_SCHEMAS["intent-entity-rate"],
            "min_entity_rate": V4_EE_MIN_ENTITY_RATE, "intent_n": intent_n,
            "intent_with_entities": dict(sorted(counts["intent_with_entities"].items())),
        },
    }
    return {name: _v4_table_bytes(documents[name]) for name in V4_TABLES}


def _v4_refuse(message: str) -> DeliveryNormaliserError:
    return DeliveryNormaliserError(f"{DELIVER_NORMALISE_V4}: {message}")


def _v4_counts_map(raw, label: str) -> "dict[str, int]":
    if not isinstance(raw, dict) or not all(
        isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) and v >= 0 for k, v in raw.items()
    ):
        raise _v4_refuse(f"malformed {label}")
    return dict(raw)


class SlurpV4Statistics:
    """The TRAIN statistics v4's entity stage consults: the fx-article strip
    set, the fx-oclock decision, the per-intent type counts (ti1) and the
    per-intent entity-carrying counts (ee10). Pure counts: no filler,
    utterance or value is retained, only slot TYPE names, determiner words and
    intent ids.

    Two constructors. :meth:`from_pool_values` computes them from an annotated
    pool (tests, the builder). :meth:`from_table_bytes` loads the four pinned
    tables, checks each against its pin, schema and the rule's own thresholds,
    and re-derives every decision from the counts. ``tables`` records the
    table digests a loaded instance came from (empty when computed).
    """

    __slots__ = ("article_strip", "oclock_strip", "intent_n", "intent_with_entities", "intent_type", "sha256",
                 "tables")

    def __init__(self, *, article_strip, oclock_strip: bool, intent_n: dict, intent_with_entities: dict,
                 intent_type: dict, tables: "dict[str, str] | None" = None) -> None:
        self.article_strip = frozenset((str(t), str(w)) for t, w in article_strip)
        self.oclock_strip = bool(oclock_strip)
        self.intent_n = {str(k): int(v) for k, v in intent_n.items()}
        self.intent_with_entities = {str(k): int(v) for k, v in intent_with_entities.items()}
        self.intent_type = {str(i): {str(t): int(n) for t, n in types.items()} for i, types in intent_type.items()}
        self.tables = dict(sorted((tables or {}).items()))
        self.sha256 = hashlib.sha256(
            json.dumps(self.to_document(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @classmethod
    def from_pool_values(cls, values) -> "SlurpV4Statistics":
        counts = v4_pool_counts(values)
        keys = set(counts["article_included"]) | set(counts["article_excluded"])
        rows = {k: (counts["article_included"].get(k, 0), counts["article_excluded"].get(k, 0)) for k in keys}
        return cls(article_strip=_v4_article_strip(rows),
                   oclock_strip=_v4_oclock_strip(counts["oclock_included"], counts["oclock_excluded"]),
                   intent_n=counts["intent_n"], intent_with_entities=counts["intent_with_entities"],
                   intent_type=counts["intent_type"])

    @classmethod
    def from_table_bytes(
        cls,
        blobs: "dict[str, bytes]",
        *,
        expected_sha256: "dict[str, str] | None",
    ) -> "SlurpV4Statistics":
        """Load the four tables. ``expected_sha256`` is the pin map (the
        registered :data:`V4_TABLE_SHA256`); ``None`` skips the pin check
        (tests of table construction only)."""

        if set(blobs) != set(V4_TABLES):
            raise _v4_refuse(f"the statistics are exactly the tables {list(V4_TABLES)}")
        documents, digests = {}, {}
        for name in V4_TABLES:
            digest = hashlib.sha256(blobs[name]).hexdigest()
            if expected_sha256 is not None and digest != expected_sha256.get(name):
                raise _v4_refuse(
                    f"the {name} table hashes to {digest[:12]}..., not the pinned "
                    f"{str(expected_sha256.get(name))[:12]}..."
                )
            try:
                document = json.loads(blobs[name].decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as error:
                raise _v4_refuse(f"the {name} table is not JSON: {error}") from error
            if not isinstance(document, dict) or document.get("schema") != V4_TABLE_SCHEMAS[name]:
                raise _v4_refuse(f"the {name} table schema must be {V4_TABLE_SCHEMAS[name]!r}")
            if document.get("artifact_id") != V4_STATS_ARTIFACT_ID:
                raise _v4_refuse(f"the {name} table is not artifact {V4_STATS_ARTIFACT_ID}")
            documents[name], digests[name] = document, digest
        pools = {json.dumps(d.get("construction_pool"), sort_keys=True) for d in documents.values()}
        if len(pools) != 1:
            raise _v4_refuse("the four tables were not built from one construction pool")
        # fx-article: thresholds are the rule's; the strip set is re-derived.
        art = documents["article-strip"]
        if (art.get("determiners") != list(V4_DETERMINERS)
                or art.get("max_included_share") != V4_ARTICLE_MAX_INCLUDED_SHARE
                or art.get("min_opportunities") != V4_ARTICLE_MIN_OPPORTUNITIES):
            raise _v4_refuse("the article-strip table does not carry the rule's determiners and thresholds")
        rows: dict[tuple, tuple[int, int]] = {}
        raw_rows = art.get("rows")
        if not isinstance(raw_rows, dict):
            raise _v4_refuse("malformed article-strip rows")
        for key, pair in raw_rows.items():
            slot_type, sep, word = str(key).partition("|")
            if (not sep or word not in V4_DETERMINERS or not isinstance(pair, list) or len(pair) != 2
                    or not all(isinstance(c, int) and not isinstance(c, bool) and c >= 0 for c in pair)):
                raise _v4_refuse("malformed article-strip row")
            rows[(slot_type, word)] = (pair[0], pair[1])
        strip = _v4_article_strip(rows)
        if sorted([t, w] for t, w in strip) != art.get("strip"):
            raise _v4_refuse("the article-strip table's listed strip set does not follow from its counts")
        # fx-oclock
        ocl = documents["oclock"]
        if (ocl.get("tokens") != list(V4_OCLOCK_TOKENS) or ocl.get("slot_type") != "time"
                or ocl.get("max_included_share") != V4_ARTICLE_MAX_INCLUDED_SHARE
                or ocl.get("min_opportunities") != V4_OCLOCK_MIN_OPPORTUNITIES):
            raise _v4_refuse("the oclock table does not carry the rule's tokens and thresholds")
        inc, exc = ocl.get("included"), ocl.get("excluded")
        if not all(isinstance(c, int) and not isinstance(c, bool) and c >= 0 for c in (inc, exc)):
            raise _v4_refuse("malformed oclock counts")
        oclock = _v4_oclock_strip(inc, exc)
        if ocl.get("strip") is not oclock:
            raise _v4_refuse("the oclock table's listed decision does not follow from its counts")
        # ti1
        tbi = documents["type-by-intent"]
        if tbi.get("min_share") != V4_TI_MIN_SHARE:
            raise _v4_refuse("the type-by-intent table does not carry the rule's 1 % threshold")
        intent_n = _v4_counts_map(tbi.get("intent_n"), "type-by-intent intent_n")
        raw_types = tbi.get("intent_type")
        if not isinstance(raw_types, dict) or not set(raw_types) <= set(intent_n):
            raise _v4_refuse("malformed type-by-intent counts")
        intent_type = {i: _v4_counts_map(t, "type-by-intent row") for i, t in raw_types.items()}
        if any(c > intent_n[i] for i, t in intent_type.items() for c in t.values()):
            raise _v4_refuse("a type count exceeds its intent's exemplar count")
        # ee10
        rate = documents["intent-entity-rate"]
        if rate.get("min_entity_rate") != V4_EE_MIN_ENTITY_RATE:
            raise _v4_refuse("the intent-entity-rate table does not carry the rule's 10 % threshold")
        if _v4_counts_map(rate.get("intent_n"), "intent-entity-rate intent_n") != intent_n:
            raise _v4_refuse("the two intent tables disagree on the intent exemplar counts")
        with_entities = _v4_counts_map(rate.get("intent_with_entities"), "intent_with_entities")
        if set(with_entities) != set(intent_n) or any(with_entities[i] > intent_n[i] for i in intent_n):
            raise _v4_refuse("malformed intent-entity-rate counts")
        return cls(article_strip=strip, oclock_strip=oclock, intent_n=intent_n,
                   intent_with_entities=with_entities, intent_type=intent_type, tables=digests)

    def to_document(self) -> dict:
        return {
            "schema": V4_STATS_SCHEMA,
            "article_strip": sorted([t, w] for t, w in self.article_strip),
            "oclock_strip": self.oclock_strip,
            "intent_n": dict(sorted(self.intent_n.items())),
            "intent_with_entities": dict(sorted(self.intent_with_entities.items())),
            "intent_type": {i: dict(sorted(t.items())) for i, t in sorted(self.intent_type.items())},
        }

    def type_share(self, intent: str, slot_type: str) -> "float | None":
        n = self.intent_n.get(intent, 0)
        return None if n == 0 else self.intent_type.get(intent, {}).get(slot_type, 0) / n

    def entity_rate(self, intent: str) -> "float | None":
        n = self.intent_n.get(intent, 0)
        return None if n == 0 else self.intent_with_entities.get(intent, 0) / n


_DEFAULT_V4_STATISTICS: list[SlurpV4Statistics] = []


def default_v4_statistics() -> SlurpV4Statistics:
    """The four pinned tables under ``SPEECHRL_DATA_DIR``, loaded once per
    process and refused unless each hashes to its :data:`V4_TABLE_SHA256` pin
    and the loaded statistics hash to :data:`V4_STATS_SHA256`."""

    if not _DEFAULT_V4_STATISTICS:
        from ..data.lock import data_root  # noqa: PLC0415

        root = data_root()
        blobs = {name: (root / V4_TABLE_RELPATHS[name]).read_bytes() for name in V4_TABLES}
        stats = SlurpV4Statistics.from_table_bytes(blobs, expected_sha256=V4_TABLE_SHA256)
        if stats.sha256 != V4_STATS_SHA256:
            raise _v4_refuse(
                f"the pinned tables load into statistics {stats.sha256[:12]}..., not the pinned "
                f"{V4_STATS_SHA256[:12]}..."
            )
        _DEFAULT_V4_STATISTICS.append(stats)
    return _DEFAULT_V4_STATISTICS[0]


@dataclass(frozen=True)
class V4Guards:
    """The two TRAIN-only guards of v4g (audio attribution note
    ``docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md``).

    ``ti1_min_exemplars``: ti1 fires only on an intent with at least this many
    pool exemplars (1 / V4_TI_MIN_SHARE = 100), i.e. where "< 1 %" differs from
    "never seen". ``ee_wilson_max_upper`` / ``ee_wilson_z``: ee10 fires only when
    the Wilson upper bound of the intent's entity-carrying rate, at ``z``, is
    below ``ee_wilson_max_upper`` (the rule's own 10 % threshold)."""

    ti1_min_exemplars: int
    ee_wilson_max_upper: float
    ee_wilson_z: float

    def to_document(self) -> dict:
        return {
            "ti-expressible": {"ti1_min_pool_exemplars": self.ti1_min_exemplars},
            "ee-wilson": {"max_upper_bound": self.ee_wilson_max_upper, "z": self.ee_wilson_z,
                          "interval": "wilson-score-upper"},
        }


def wilson_upper_bound(successes: int, n: int, z: float) -> float:
    """The Wilson score interval's upper bound for ``successes`` of ``n`` (1.0 when n = 0)."""

    if n == 0:
        return 1.0
    p = successes / n
    centre = p + z * z / (2 * n)
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (centre + half) / (1 + z * z / n)


def v4_entity_stage(scenario, action, entities, stats: SlurpV4Statistics, table: ScopeRuleTable,
                    guards: "V4Guards | None" = None):
    """The five-rule entity stage over one parsed (v3-normalised) answer.

    Returns ``(entities_out, counts)``. Never changes a label and never adds an
    entity; an empty entity list is returned as is (owner decision 199).

    ``guards`` is ``None`` for v4 (the rules as selected) and a :class:`V4Guards`
    for v4g, which narrows ti1 and ee10 to the intents whose TRAIN statistics
    resolve their thresholds (see :data:`V4G_GUARDS`)."""

    from ..analysis.sealed_credit.entity_states import fold  # noqa: PLC0415
    from ..reproduction.slurp_scoring import SlotEntity  # noqa: PLC0415

    counts = {"fillers_rewritten": 0, "dropped_scope": 0, "dropped_ti1": 0, "dropped_ee10": 0}
    current = list(entities)
    if not current:
        return current, counts
    intent = f"{scenario}_{action}" if scenario is not None and action is not None else None
    # fx-article, then fx-oclock (filler rewrites)
    rewritten = []
    for entity in current:
        tokens = entity.filler.split()
        new = entity
        if len(tokens) > 1 and (entity.type, fold(tokens[0])) in stats.article_strip:
            new = SlotEntity(type=entity.type, filler=" ".join(tokens[1:]))
        tokens = new.filler.split()
        if (stats.oclock_strip and new.type == "time" and len(tokens) > 1
                and tokens[-1].lower() in V4_OCLOCK_TOKENS):
            new = SlotEntity(type=new.type, filler=" ".join(tokens[:-1]))
        counts["fillers_rewritten"] += int(new != entity)
        rewritten.append(new)
    current = rewritten
    # scope
    drops = set(scope_rule_drops([e.filler for e in current], table))
    counts["dropped_scope"] = len(drops)
    current = [e for i, e in enumerate(current) if i not in drops]
    if intent is None or stats.intent_n.get(intent, 0) == 0:
        return current, counts
    # ti1 (v4g: only on an intent whose pool is large enough for "< 1 %" to be expressible)
    if guards is None or stats.intent_n[intent] >= guards.ti1_min_exemplars:
        kept = [e for e in current if stats.type_share(intent, e.type) >= V4_TI_MIN_SHARE]
        counts["dropped_ti1"] = len(current) - len(kept)
        current = kept
    # ee10 (v4g: only when the entity-carrying rate is RESOLVED below the threshold)
    if guards is None:
        fires = stats.entity_rate(intent) < V4_EE_MIN_ENTITY_RATE
    else:
        fires = wilson_upper_bound(
            stats.intent_with_entities.get(intent, 0), stats.intent_n[intent], guards.ee_wilson_z
        ) < guards.ee_wilson_max_upper
    if current and fires:
        counts["dropped_ee10"] = len(current)
        current = []
    return current, counts


class SlurpProjectionV4DeliveryNormaliser:
    """``saea-deliver-normalise-v4``: the registered
    ``saea-deliver-normalise-v3`` first, then :func:`v4_entity_stage` over the
    pinned TRAIN statistics (:func:`default_v4_statistics`) and the pinned
    scope table (:func:`default_scope_rule_table`).

    One implementation per rule: v3 is resolved from the registry, the scope
    step is :func:`scope_rule_drops` over the pinned table. A row the entity
    stage leaves alone is delivered as v3 delivered it (byte-identical, so a
    v4 arm differs from a v3 arm exactly on the rows the stage edits); an
    edited row is re-rendered canonically. An unparsed answer is delivered
    verbatim with ``applied: false``. Zero contact.
    """

    id = DELIVER_NORMALISE_V4
    version = DELIVER_NORMALISE_V4_VERSION
    rule_id = V4_RULE_ID
    carrier_lock_key = "slurp"
    #: ``None`` = the rules as selected; v4g overrides with :data:`V4G_GUARDS`.
    guards: "V4Guards | None" = None

    def __call__(
        self,
        text: str,
        *,
        stats: "SlurpV4Statistics | None" = None,
        table: ScopeRuleTable | None = None,
        inventory: "LegalIntentInventory | None" = None,
    ) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        if stats is None:
            stats = default_v4_statistics()
        if not isinstance(stats, SlurpV4Statistics):
            raise _v4_refuse("stats must be a SlurpV4Statistics")
        from ..reproduction.slurp_scoring import parse_slu_response  # noqa: PLC0415
        from .slurp_projection_v3 import render_slurp_answer  # noqa: PLC0415

        if table is None:
            table = default_scope_rule_table()
        base = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)(text, inventory=inventory)
        scenario, action, entities, parsed = parse_slu_response(base.text)
        counts = {"fillers_rewritten": 0, "dropped_scope": 0, "dropped_ti1": 0, "dropped_ee10": 0}
        delivered = base.text
        if parsed:
            kept, counts = v4_entity_stage(scenario, action, entities, stats, table, self.guards)
            if list(kept) != list(entities):
                delivered = render_slurp_answer(scenario, action, kept)
        changed = delivered != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": self.rule_id,
            "carrier_lock_key": self.carrier_lock_key,
            "applied": bool(parsed),
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            "labels_changed": base.receipt["labels_changed"],
            "label_branch": base.receipt["label_branch"],
            "fillers_changed": base.receipt["fillers_changed"],
            "entity_stage": list(V4_STAGES),
            "entity_stage_counts": dict(counts),
            "stats_schema": V4_STATS_SCHEMA,
            "stats_sha256": stats.sha256,
            # The pinned table digests the statistics were loaded from; empty
            # only for injected (test) statistics.
            "stats_tables": dict(stats.tables),
            "table_sha256": table.sha256,
            "stages": [dict(base.receipt)],
            "reason": None if parsed else "unparsed",
        }
        if self.guards is not None:
            receipt["guards"] = self.guards.to_document()
        return DeliveryNormalisation(text=delivered, changed=changed, receipt=receipt).validate()


# ---------------------------------------------------------------------------
# Projection v4g (NX, 2026-10-09): ``saea-deliver-normalise-v4g``.
#
# v4 with the two TRAIN-only guards of the audio attribution note
# (``docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md``):
# ee-wilson (ee10 fires only when the Wilson 95 % upper bound of the intent's
# pool entity-carrying rate is below 0.10) and ti-expressible (ti1 fires only
# on intents with >= 100 pool exemplars). Everything else, including the
# pinned tables (the Wilson bound needs only the intent exemplar and
# entity-carrying counts the intent-entity-rate table already carries), is v4.
# Receipt: ``docs/receipts/knowledge/slurp-v4g-registration-v1.json``.
#
# REGISTERED, NOT ARMED: no config, fragment, cell or lock names it.
# ---------------------------------------------------------------------------

DELIVER_NORMALISE_V4G = "saea-deliver-normalise-v4g"
#: Bumped when the RULE, a guard constant or a pinned table changes.
DELIVER_NORMALISE_V4G_VERSION = "1"
V4G_RULE_ID = "slurp-use-projection-v4g"
V4G_WILSON_Z = 1.959963984540054
V4G_GUARDS = V4Guards(
    ti1_min_exemplars=round(1 / V4_TI_MIN_SHARE),
    ee_wilson_max_upper=V4_EE_MIN_ENTITY_RATE,
    ee_wilson_z=V4G_WILSON_Z,
)


class SlurpProjectionV4GuardedDeliveryNormaliser(SlurpProjectionV4DeliveryNormaliser):
    """``saea-deliver-normalise-v4g``: :class:`SlurpProjectionV4DeliveryNormaliser`
    with :data:`V4G_GUARDS`. The receipt adds a ``guards`` field."""

    id = DELIVER_NORMALISE_V4G
    version = DELIVER_NORMALISE_V4G_VERSION
    rule_id = V4G_RULE_ID
    guards = V4G_GUARDS


DELIVERY_NORMALISERS.register(
    DELIVER_NORMALISE_V3, SlurpProjectionV3DeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(
    DELIVER_NORMALISE_EARNINGS_TEXT_V1, EarningsTextDeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(
    DELIVER_NORMALISE_EARNINGS22_TEXT_V1, Earnings22TextDeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(
    DELIVER_CITED_ANSWER_V1, CitedAnswerUnwrapDeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(
    DELIVER_CITED_ANSWER_NORMALISE_V3_V1, CitedAnswerNormaliseV3DeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(DELIVER_SCOPE_RULE_V1, ScopeRuleDeliveryStage())
DELIVERY_NORMALISERS.register(
    DELIVER_NORMALISE_V3_SCOPE_RULE_V1, NormaliseV3ScopeRuleDeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(
    DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1,
    CitedAnswerNormaliseV3ScopeRuleDeliveryNormaliser(),
)
DELIVERY_NORMALISERS.register(DELIVER_NORMALISE_V4, SlurpProjectionV4DeliveryNormaliser())
DELIVERY_NORMALISERS.register(DELIVER_NORMALISE_V4G, SlurpProjectionV4GuardedDeliveryNormaliser())


__all__ = [
    "DELIVER_NORMALISER_RECEIPT_SCHEMA",
    "DELIVER_NORMALISE_V3",
    "DELIVER_NORMALISE_V3_VERSION",
    "DELIVER_NORMALISE_EARNINGS_TEXT_V1",
    "DELIVER_NORMALISE_EARNINGS_TEXT_V1_VERSION",
    "DELIVER_NORMALISE_EARNINGS22_TEXT_V1",
    "DELIVER_CITED_ANSWER_V1",
    "DELIVER_CITED_ANSWER_V1_VERSION",
    "DELIVER_CITED_ANSWER_NORMALISE_V3_V1",
    "DELIVER_CITED_ANSWER_NORMALISE_V3_V1_VERSION",
    "SlurpProjectionV3DeliveryNormaliser",
    "EarningsTextDeliveryNormaliser",
    "Earnings22TextDeliveryNormaliser",
    "CitedAnswerUnwrapDeliveryNormaliser",
    "CitedAnswerNormaliseV3DeliveryNormaliser",
    "DELIVER_SCOPE_RULE_V1",
    "DELIVER_NORMALISE_V3_SCOPE_RULE_V1",
    "DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1",
    "SCOPE_RULE_COMPOSITIONS",
    "SCOPE_RULE_MIN_POOL_OCCURRENCES",
    "SCOPE_RULE_TABLE_RELPATH",
    "SCOPE_RULE_TABLE_SHA256",
    "SCOPE_RULE_UNTAGGED_SHARE",
    "ScopeRuleDeliveryStage",
    "ScopeRuleTable",
    "NormaliseV3ScopeRuleDeliveryNormaliser",
    "CitedAnswerNormaliseV3ScopeRuleDeliveryNormaliser",
    "default_scope_rule_table",
    "scope_rule_drops",
    "scope_rule_phrase",
    "validate_scope_rule_receipt",
    "DELIVER_NORMALISE_V4",
    "DELIVER_NORMALISE_V4_VERSION",
    "DELIVER_NORMALISE_V4G",
    "DELIVER_NORMALISE_V4G_VERSION",
    "V4G_GUARDS",
    "V4G_RULE_ID",
    "V4G_WILSON_Z",
    "V4Guards",
    "SlurpProjectionV4GuardedDeliveryNormaliser",
    "wilson_upper_bound",
    "V4_STAGES",
    "V4_STATS_ARTIFACT_ID",
    "V4_STATS_SHA256",
    "V4_TABLES",
    "V4_TABLE_RELPATHS",
    "V4_TABLE_SHA256",
    "SlurpV4Statistics",
    "SlurpProjectionV4DeliveryNormaliser",
    "default_v4_statistics",
    "v4_entity_stage",
    "v4_pool_counts",
    "v4_table_bytes",
]
