"""E12: the construction-data SLOT AUDIT view and its deterministic flags.

Owner directive 26 of 2026-09-18 ("analyses into nodes"): an offline analysis
this program trusts belongs INSIDE an agent node rather than only in a report.
Cell B8b is the read-side instance of that directive -- the A3 coverage /
slot-loss audits placed at the Reviewer boundary as declared context. This
module is the ANALYSIS half of it: the pinned table the block is rendered
from, and the four flags a harness (never a model) computes against one draft.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
section 16 (the B8b row and the boundary that makes it legal). Evidence base:
``docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md`` (T5/T6:
81 of 135 gold-``date`` rows emit no date at all, 46 of 72 ``time`` rows emit
a non-exact filler) and ``docs/results/2026-09-14-slurp-train-a-entity-loss-
attribution-v1.md`` (184 of the 414 empty-gold rows emit an entity anyway).

THE BOUNDARY, and it is the whole licence for this node:

* The table is mined from the CONSTRUCTION POOL only -- the governed SLURP
  TRAIN split minus every utterance with a recording in TRAIN Fold A, Fold B
  or DEV-1000 (the 2026-09-13 exclusion). No gold of an evaluated row is read,
  keyed on, or conditioned upon, at build time or at runtime.
* The table carries COUNTS and SHARES per (intent, entity type), plus the two
  representation conventions already released in slot store v2. It carries NO
  filler text, no sentence, no utterance id and no recording.
* Rendering the block makes ZERO contacts of any kind -- no model, tokenizer,
  encoder, scorer, tool, server or network. It is a pure function of the
  draft under review, the pinned table and the declared thresholds.
* The only text of an evaluated row that can appear in the block is the
  draft's own entity TYPE names, which the consumer already holds in the draft
  block immediately above it. Fillers never reach the audit block, not even
  the ones a REPRESENTATION flag fires on.

The table is a committed repository artifact (``knowledge/slurp/semantic/
slot-audit-v1/``) rather than a ``SPEECHRL_DATA_DIR`` store, for the same
reason ``knowledge/audio2tool/`` is committed and the exemplar snapshots are
not: it holds aggregate construction statistics and no speech, no sentence and
no gold span, so its pin is a git blob hash an auditor can check offline.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

#: The registered identity of this view; the value a fragment's
#: ``native_episode.reviewer_audit.view`` must carry.
SLOT_AUDIT_VIEW_ID = "slot-audit-v1"

#: Document schemas of the two released files.
SLOT_AUDIT_RELEASE_SCHEMA = "saea-slot-audit-release-v1"
SLOT_AUDIT_VIEW_SCHEMA = "saea-slot-audit-view-v1"

#: The per-contact receipt block ``rails.node_context_policy`` seals beside the
#: boundary's own ``saea-node-context-policy-v1`` row.
SLOT_AUDIT_RECEIPT_SCHEMA = "saea-reviewer-slot-audit-v1"

#: The builder that produced the released table
#: (``scripts/build_slurp_slot_audit_view.py``).
SLOT_AUDIT_BUILDER_POLICY_ID = "saea-slot-audit-construction-profile-v1"

#: The one representation rule this view defines, and the characters it
#: refuses. Both released slot store v2 cards say the same thing in their own
#: ``Admissible formats`` sentence -- ``time``: "never digits and never a
#: colon"; ``date``: "do not resolve it to an ISO date or invent a year" --
#: so ONE predicate serves both: a spoken filler carries no ASCII digit, no
#: colon and no slash. The card sentences travel in the table as the rule's
#: quoted authority.
SPOKEN_FORM_RULE_ID = "saea-spoken-form-v1"
SPOKEN_FORM_FORBIDDEN_CHARACTERS = "0123456789:/"

#: The four flags, in the fixed order they are rendered. A flag name is a
#: closed token: it is never composed, translated or abbreviated.
FLAG_TYPE_UNSEEN = "TYPE-UNSEEN"
FLAG_EMPTY_DRAFT = "EMPTY-DRAFT"
FLAG_MISSING_COMMON = "MISSING-COMMON"
FLAG_REPRESENTATION = "REPRESENTATION"
SLOT_AUDIT_FLAGS: tuple[str, ...] = (
    FLAG_TYPE_UNSEEN,
    FLAG_EMPTY_DRAFT,
    FLAG_MISSING_COMMON,
    FLAG_REPRESENTATION,
)

#: Threshold names, their defaults and their meanings. Every one is a SHARE of
#: the intent's own construction rows, in ``[0, 1]``.
#:
#: * ``profile_min_row_share`` -- a type is LISTED in the rendered profile when
#:   at least this share of the intent's rows carry it. It bounds the block's
#:   length; it never gates a flag, because TYPE-UNSEEN reads "attested at all"
#:   and MISSING-COMMON has its own threshold.
#: * ``missing_common_min_row_share`` -- MISSING-COMMON fires for a type above
#:   this share that the draft omits.
#: * ``empty_draft_min_entity_row_share`` -- EMPTY-DRAFT fires when the draft
#:   declares no entity while at least this share of the intent's rows carry
#:   one.
SLOT_AUDIT_THRESHOLD_KEYS: tuple[str, ...] = (
    "empty_draft_min_entity_row_share",
    "missing_common_min_row_share",
    "profile_min_row_share",
)
SLOT_AUDIT_DEFAULT_THRESHOLDS: Mapping[str, float] = {
    "empty_draft_min_entity_row_share": 0.5,
    "missing_common_min_row_share": 0.5,
    "profile_min_row_share": 0.05,
}

#: Decimal places a stored share keeps. The FILTERS always run on the exact
#: integer ratio; only the recorded and rendered number is rounded, exactly as
#: ``data.slurp`` does for its own mention shares.
_SHARE_DIGITS = 6

_PIN_KEYS = frozenset({"relpath", "sha256"})


class SlotAuditError(ValueError):
    """A slot-audit table, pin, threshold set or flag input is invalid."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _share(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, _SHARE_DIGITS)


def render_share(numerator: int, denominator: int) -> str:
    """``"47.5 % (28 of 59 rows)"`` -- the one rendering of a share.

    Integer-exact: the percentage is formatted from the integer ratio and the
    counts travel beside it, so a reader can re-derive the number and no float
    ever crosses a platform boundary unrounded.
    """

    if denominator <= 0:
        return f"0.0 % (0 of {denominator} rows)"
    return (
        f"{100.0 * numerator / denominator:.1f} % "
        f"({numerator} of {denominator} rows)"
    )


def violates_spoken_form(filler: str) -> bool:
    """Whether ``filler`` breaks the released spoken-form convention.

    The predicate is exactly :data:`SPOKEN_FORM_FORBIDDEN_CHARACTERS`: an
    ASCII digit, a colon or a slash. It looks at characters alone and makes no
    judgment about meaning -- a harness check, never a model's opinion.
    """

    if not isinstance(filler, str):
        raise SlotAuditError("a slot filler must be text")
    return any(character in SPOKEN_FORM_FORBIDDEN_CHARACTERS for character in filler)


@dataclass(frozen=True)
class SlotAuditConvention:
    """One entity type's released representation convention."""

    entity_type: str
    rule_id: str
    statement: str
    forbidden_characters: str

    def as_json(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "rule_id": self.rule_id,
            "statement": self.statement,
            "forbidden_characters": self.forbidden_characters,
        }


@dataclass(frozen=True)
class SlotAuditIntentProfile:
    """One intent's row-level construction profile, as the table stores it."""

    intent: str
    rows: int
    rows_with_entity: int
    #: ``(entity_type, rows, row_share)``, most frequent first, ties by name.
    #: EVERY attested type is listed, however rare: absence from this table is
    #: what TYPE-UNSEEN reads.
    types: tuple[tuple[str, int, float], ...]

    @property
    def rows_without_entity(self) -> int:
        return self.rows - self.rows_with_entity

    @property
    def type_rows(self) -> Mapping[str, int]:
        return {entity_type: rows for entity_type, rows, _share in self.types}

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "rows": self.rows,
            "rows_with_entity": self.rows_with_entity,
            "empty_row_share": _share(self.rows_without_entity, self.rows),
            "entity_row_share": _share(self.rows_with_entity, self.rows),
            "types": [
                {"entity_type": entity_type, "rows": rows, "row_share": row_share}
                for entity_type, rows, row_share in self.types
            ],
        }


@dataclass(frozen=True)
class SlotAuditThresholds:
    """The declared thresholds, validated and canonically ordered."""

    empty_draft_min_entity_row_share: float
    missing_common_min_row_share: float
    profile_min_row_share: float

    def as_json(self) -> dict[str, float]:
        return {
            "empty_draft_min_entity_row_share": self.empty_draft_min_entity_row_share,
            "missing_common_min_row_share": self.missing_common_min_row_share,
            "profile_min_row_share": self.profile_min_row_share,
        }


def slot_audit_thresholds(declared: object = None) -> SlotAuditThresholds:
    """Resolve a declared threshold object, or the registered defaults.

    Fail-closed: an unknown key, a non-numeric value, a boolean and a value
    outside ``[0, 1]`` are each refused by name, before any contact.
    """

    values = dict(SLOT_AUDIT_DEFAULT_THRESHOLDS)
    if declared is not None:
        if not isinstance(declared, Mapping):
            raise SlotAuditError("reviewer_audit.thresholds must be an object")
        unknown = sorted(set(declared) - set(SLOT_AUDIT_THRESHOLD_KEYS))
        if unknown:
            raise SlotAuditError(
                f"reviewer_audit.thresholds carries unknown key(s) {unknown}; the "
                f"declared set is {list(SLOT_AUDIT_THRESHOLD_KEYS)}"
            )
        for name, value in declared.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SlotAuditError(
                    f"reviewer_audit.thresholds.{name} must be a number"
                )
            if not 0.0 <= float(value) <= 1.0:
                raise SlotAuditError(
                    f"reviewer_audit.thresholds.{name} must lie in [0, 1]"
                )
            values[name] = float(value)
    return SlotAuditThresholds(**values)


@dataclass(frozen=True)
class SlotAuditTable:
    """The released, pinned construction table the Reviewer block renders."""

    view_id: str
    builder_policy_id: str
    source_split: str
    source_split_identity_hash: str
    construction_utterance_count: int
    intents: Mapping[str, SlotAuditIntentProfile]
    conventions: Mapping[str, SlotAuditConvention]
    release_sha256: str
    snapshot_sha256: str

    @property
    def intent_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.intents))

    @property
    def convention_types(self) -> tuple[str, ...]:
        return tuple(sorted(self.conventions))

    def profile(self, intent_id: str) -> SlotAuditIntentProfile | None:
        return self.intents.get(intent_id)

    def content_hash(self) -> str:
        """Canonical-JSON sha256 of the table's own content, independent of
        the two files' byte framing."""

        return _sha256_bytes(
            json.dumps(
                {
                    "view_id": self.view_id,
                    "builder_policy_id": self.builder_policy_id,
                    "source_split": self.source_split,
                    "source_split_identity_hash": self.source_split_identity_hash,
                    "construction_utterance_count": self.construction_utterance_count,
                    "conventions": [
                        self.conventions[name].as_json()
                        for name in self.convention_types
                    ],
                    "intents": [
                        self.intents[intent].as_json() for intent in self.intent_ids
                    ],
                },
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )

    def pins(self) -> dict[str, str]:
        return {
            "release_sha256": self.release_sha256,
            "snapshot_sha256": self.snapshot_sha256,
            "table_content_hash": self.content_hash(),
        }


@dataclass(frozen=True)
class SlotAuditFlag:
    """One fired flag: a closed name, the entity type it concerns, the
    deterministic detail line, and the counts it was computed from."""

    flag: str
    entity_type: str | None
    detail: str
    rows: int | None = None
    of_rows: int | None = None

    def as_json(self) -> dict[str, object]:
        document: dict[str, object] = {"flag": self.flag, "detail": self.detail}
        if self.entity_type is not None:
            document["entity_type"] = self.entity_type
        if self.rows is not None:
            document["rows"] = self.rows
            document["of_rows"] = self.of_rows
        return document


# -- the four flag detail forms, as closed templates ------------------------
#
# Every rendered detail is one of these four sentences with a type name, a
# share rendering or a released convention sentence substituted in. Nothing
# else is ever emitted, which is what makes the "adds no information" property
# test over this block a finite check.
DETAIL_TYPE_UNSEEN = "{entity_type} is not attested with this intent in the construction pool"
DETAIL_EMPTY_DRAFT = "the draft declares no entity; {share} of this intent's construction rows carry one"
DETAIL_MISSING_COMMON = "{entity_type} is absent from the draft; {share} of this intent's construction rows carry it"
DETAIL_REPRESENTATION = "{entity_type} filler is not in the released spoken convention -- {statement}"


def _pin(value: object, *, field_name: str) -> Mapping[str, str]:
    if (
        not isinstance(value, Mapping)
        or set(value) != _PIN_KEYS
        or not isinstance(value["relpath"], str)
        or not isinstance(value["sha256"], str)
    ):
        raise SlotAuditError(
            f"{field_name} must be a pin declaring exactly relpath and sha256"
        )
    relpath = value["relpath"]
    digest = value["sha256"]
    if (
        not relpath
        or relpath.startswith("/")
        or "\\" in relpath
        or ".." in Path(relpath).parts
    ):
        raise SlotAuditError(
            f"{field_name}.relpath must be a plain relative POSIX path inside the "
            "repository"
        )
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise SlotAuditError(f"{field_name}.sha256 must be a lower-case sha256")
    return {"relpath": relpath, "sha256": digest}


def _read_pinned(repo_root: Path, pin: Mapping[str, str], *, field_name: str) -> object:
    root = Path(repo_root).resolve()
    path = (root / pin["relpath"]).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise SlotAuditError(f"{field_name} escapes the repository root") from None
    if not path.is_file():
        raise SlotAuditError(f"{field_name} names no file: {path}")
    raw = path.read_bytes()
    measured = _sha256_bytes(raw)
    if measured != pin["sha256"]:
        raise SlotAuditError(
            f"{field_name} hashes to {measured}, not the pinned {pin['sha256']}"
        )
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise SlotAuditError(f"{field_name} is not JSON: {error}") from error


def load_slot_audit_table(
    repo_root: Path, *, release: object, snapshot: object, view_id: str,
) -> SlotAuditTable:
    """Load the released table from its two pinned repository files.

    Fail-closed on every axis: each file's bytes must hash to its declared pin,
    the release must name this view id and the snapshot's own pin, and the two
    documents must agree on the builder policy and the construction identity.
    No network, no data root, no model.
    """

    release_pin = _pin(release, field_name="reviewer_audit.release")
    snapshot_pin = _pin(snapshot, field_name="reviewer_audit.snapshot")
    release_document = _read_pinned(
        repo_root, release_pin, field_name="reviewer_audit.release"
    )
    snapshot_document = _read_pinned(
        repo_root, snapshot_pin, field_name="reviewer_audit.snapshot"
    )
    if (
        not isinstance(release_document, Mapping)
        or release_document.get("schema") != SLOT_AUDIT_RELEASE_SCHEMA
        or release_document.get("view_id") != view_id
        or release_document.get("snapshot_sha256") != snapshot_pin["sha256"]
    ):
        raise SlotAuditError(
            "reviewer_audit.release is not this view's release, or does not pin "
            "the declared snapshot"
        )
    if (
        not isinstance(snapshot_document, Mapping)
        or snapshot_document.get("schema") != SLOT_AUDIT_VIEW_SCHEMA
        or snapshot_document.get("view_id") != view_id
    ):
        raise SlotAuditError("reviewer_audit.snapshot is not this view's snapshot")
    if release_document.get("builder_policy_id") != snapshot_document.get(
        "builder_policy_id"
    ) or release_document.get("source_split_identity_hash") != snapshot_document.get(
        "source_split_identity_hash"
    ):
        raise SlotAuditError(
            "reviewer_audit release and snapshot disagree on the construction identity"
        )
    return _table_from_documents(
        release_document, snapshot_document,
        release_sha256=release_pin["sha256"],
        snapshot_sha256=snapshot_pin["sha256"],
    )


def _table_from_documents(
    release: Mapping[str, object],
    snapshot: Mapping[str, object],
    *,
    release_sha256: str,
    snapshot_sha256: str,
) -> SlotAuditTable:
    conventions: dict[str, SlotAuditConvention] = {}
    declared_conventions = snapshot.get("conventions")
    if not isinstance(declared_conventions, list) or not declared_conventions:
        raise SlotAuditError("reviewer_audit snapshot declares no convention")
    for entry in declared_conventions:
        if not isinstance(entry, Mapping) or set(entry) != {
            "entity_type", "rule_id", "statement", "forbidden_characters",
        }:
            raise SlotAuditError("reviewer_audit convention has unknown fields")
        entity_type = entry["entity_type"]
        if not isinstance(entity_type, str) or not entity_type or entity_type in conventions:
            raise SlotAuditError("reviewer_audit convention entity_type is invalid")
        if entry["rule_id"] != SPOKEN_FORM_RULE_ID:
            raise SlotAuditError(
                f"reviewer_audit convention rule must be {SPOKEN_FORM_RULE_ID!r}"
            )
        if entry["forbidden_characters"] != SPOKEN_FORM_FORBIDDEN_CHARACTERS:
            raise SlotAuditError(
                "reviewer_audit convention forbidden characters differ from the "
                "registered predicate"
            )
        statement = entry["statement"]
        if not isinstance(statement, str) or not statement.strip():
            raise SlotAuditError("reviewer_audit convention statement must be text")
        conventions[entity_type] = SlotAuditConvention(
            entity_type=entity_type,
            rule_id=SPOKEN_FORM_RULE_ID,
            statement=statement,
            forbidden_characters=SPOKEN_FORM_FORBIDDEN_CHARACTERS,
        )
    intents: dict[str, SlotAuditIntentProfile] = {}
    declared_intents = snapshot.get("intents")
    if not isinstance(declared_intents, list) or not declared_intents:
        raise SlotAuditError("reviewer_audit snapshot declares no intent profile")
    for entry in declared_intents:
        if not isinstance(entry, Mapping):
            raise SlotAuditError("reviewer_audit intent profile must be an object")
        intent = entry.get("intent")
        if not isinstance(intent, str) or not intent or intent in intents:
            raise SlotAuditError("reviewer_audit intent profile id is invalid")
        rows = entry.get("rows")
        with_entity = entry.get("rows_with_entity")
        if (
            isinstance(rows, bool)
            or not isinstance(rows, int)
            or rows < 0
            or isinstance(with_entity, bool)
            or not isinstance(with_entity, int)
            or not 0 <= with_entity <= rows
        ):
            raise SlotAuditError(
                f"reviewer_audit intent {intent!r} carries impossible row counts"
            )
        types: list[tuple[str, int, float]] = []
        declared_types = entry.get("types")
        if not isinstance(declared_types, list):
            raise SlotAuditError(
                f"reviewer_audit intent {intent!r} types must be a list"
            )
        seen: set[str] = set()
        for row in declared_types:
            if not isinstance(row, Mapping) or set(row) != {
                "entity_type", "rows", "row_share",
            }:
                raise SlotAuditError(
                    f"reviewer_audit intent {intent!r} type row has unknown fields"
                )
            entity_type = row["entity_type"]
            type_rows = row["rows"]
            if (
                not isinstance(entity_type, str)
                or not entity_type
                or entity_type in seen
                or isinstance(type_rows, bool)
                or not isinstance(type_rows, int)
                or not 1 <= type_rows <= rows
            ):
                raise SlotAuditError(
                    f"reviewer_audit intent {intent!r} type row is invalid"
                )
            seen.add(entity_type)
            types.append((entity_type, type_rows, _share(type_rows, rows)))
        intents[intent] = SlotAuditIntentProfile(
            intent=intent,
            rows=rows,
            rows_with_entity=with_entity,
            types=tuple(types),
        )
    count = snapshot.get("construction_utterance_count")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise SlotAuditError("reviewer_audit construction_utterance_count is invalid")
    split = snapshot.get("source_split")
    if split != "train":
        raise SlotAuditError(
            "reviewer_audit snapshot must be mined from the TRAIN construction pool"
        )
    return SlotAuditTable(
        view_id=str(snapshot["view_id"]),
        builder_policy_id=str(snapshot["builder_policy_id"]),
        source_split=split,
        source_split_identity_hash=str(snapshot["source_split_identity_hash"]),
        construction_utterance_count=count,
        intents=intents,
        conventions=conventions,
        release_sha256=release_sha256,
        snapshot_sha256=snapshot_sha256,
    )


def profile_rows(
    profile: SlotAuditIntentProfile | None, thresholds: SlotAuditThresholds,
) -> tuple[tuple[str, int, int], ...]:
    """The ``(entity_type, rows, intent_rows)`` triples the block LISTS.

    Filtered by ``profile_min_row_share`` on the exact integer ratio, in the
    table's own order (descending rows, ties by type name).
    """

    if profile is None or profile.rows <= 0:
        return ()
    return tuple(
        (entity_type, rows, profile.rows)
        for entity_type, rows, _row_share in profile.types
        if rows / profile.rows >= thresholds.profile_min_row_share
    )


def slot_audit_flags(
    *,
    intent_id: str,
    entities: Sequence[tuple[str, str]],
    table: SlotAuditTable,
    thresholds: SlotAuditThresholds,
) -> tuple[SlotAuditFlag, ...]:
    """Every flag that fires on one draft, in :data:`SLOT_AUDIT_FLAGS` order.

    Pure, deterministic and zero-contact. ``entities`` is the draft's own
    ``(type, filler)`` list, in the Solver's order; a filler is read ONLY by
    the spoken-form predicate and never reaches a rendered detail.
    """

    if not isinstance(intent_id, str) or not intent_id:
        raise SlotAuditError("slot audit requires the draft's intent id")
    profile = table.profile(intent_id)
    draft_types: list[str] = []
    for entry in entities:
        entity_type, filler = entry
        if not isinstance(entity_type, str) or not isinstance(filler, str):
            raise SlotAuditError("a draft entity must be a (type, filler) text pair")
        if entity_type not in draft_types:
            draft_types.append(entity_type)
    flags: list[SlotAuditFlag] = []

    # TYPE-UNSEEN -- in the draft's own order, one flag per distinct type.
    if profile is not None:
        attested = profile.type_rows
        for entity_type in draft_types:
            if entity_type not in attested:
                flags.append(SlotAuditFlag(
                    flag=FLAG_TYPE_UNSEEN,
                    entity_type=entity_type,
                    detail=DETAIL_TYPE_UNSEEN.format(entity_type=entity_type),
                ))

    # EMPTY-DRAFT -- at most one, and only when the intent has a profile.
    if profile is not None and not draft_types and profile.rows > 0:
        if profile.rows_with_entity / profile.rows >= (
            thresholds.empty_draft_min_entity_row_share
        ):
            flags.append(SlotAuditFlag(
                flag=FLAG_EMPTY_DRAFT,
                entity_type=None,
                detail=DETAIL_EMPTY_DRAFT.format(
                    share=render_share(profile.rows_with_entity, profile.rows)
                ),
                rows=profile.rows_with_entity,
                of_rows=profile.rows,
            ))

    # MISSING-COMMON -- in the table's own order (descending rows, then name).
    if profile is not None and profile.rows > 0:
        for entity_type, rows, _row_share in profile.types:
            if entity_type in draft_types:
                continue
            if rows / profile.rows <= thresholds.missing_common_min_row_share:
                continue
            flags.append(SlotAuditFlag(
                flag=FLAG_MISSING_COMMON,
                entity_type=entity_type,
                detail=DETAIL_MISSING_COMMON.format(
                    entity_type=entity_type,
                    share=render_share(rows, profile.rows),
                ),
                rows=rows,
                of_rows=profile.rows,
            ))

    # REPRESENTATION -- in the draft's own order, at most one per type. It
    # needs no profile: the convention is a property of the type, not of the
    # intent, so a draft naming an intent outside the table is still checked.
    flagged: set[str] = set()
    for entity_type, filler in entities:
        if entity_type in flagged or entity_type not in table.conventions:
            continue
        if not violates_spoken_form(filler):
            continue
        flagged.add(entity_type)
        convention = table.conventions[entity_type]
        flags.append(SlotAuditFlag(
            flag=FLAG_REPRESENTATION,
            entity_type=entity_type,
            detail=DETAIL_REPRESENTATION.format(
                entity_type=entity_type, statement=convention.statement,
            ),
        ))
    return tuple(flags)


def flag_counts(flags: Sequence[SlotAuditFlag]) -> dict[str, int]:
    """Every registered flag name mapped to how often it fired -- including
    the zeros, so a receipt row has the same shape on every contact."""

    counts = {name: 0 for name in SLOT_AUDIT_FLAGS}
    for flag in flags:
        counts[flag.flag] += 1
    return counts


__all__ = [
    "DETAIL_EMPTY_DRAFT",
    "DETAIL_MISSING_COMMON",
    "DETAIL_REPRESENTATION",
    "DETAIL_TYPE_UNSEEN",
    "FLAG_EMPTY_DRAFT",
    "FLAG_MISSING_COMMON",
    "FLAG_REPRESENTATION",
    "FLAG_TYPE_UNSEEN",
    "SLOT_AUDIT_BUILDER_POLICY_ID",
    "SLOT_AUDIT_DEFAULT_THRESHOLDS",
    "SLOT_AUDIT_FLAGS",
    "SLOT_AUDIT_RECEIPT_SCHEMA",
    "SLOT_AUDIT_RELEASE_SCHEMA",
    "SLOT_AUDIT_THRESHOLD_KEYS",
    "SLOT_AUDIT_VIEW_ID",
    "SLOT_AUDIT_VIEW_SCHEMA",
    "SPOKEN_FORM_FORBIDDEN_CHARACTERS",
    "SPOKEN_FORM_RULE_ID",
    "SlotAuditConvention",
    "SlotAuditError",
    "SlotAuditFlag",
    "SlotAuditIntentProfile",
    "SlotAuditTable",
    "SlotAuditThresholds",
    "flag_counts",
    "load_slot_audit_table",
    "profile_rows",
    "render_share",
    "slot_audit_flags",
    "slot_audit_thresholds",
    "violates_spoken_form",
]
