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
]
