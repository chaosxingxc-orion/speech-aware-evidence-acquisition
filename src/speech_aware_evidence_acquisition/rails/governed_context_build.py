"""Pure construction of source-bound, external-governed call context stores."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from collections.abc import Sequence

from ..core.class_lists import ClassListError, context_tokens, roster_entries
from .errors import RailsError
from .knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)


GOVERNED_CONTEXT_BUILD_POLICY_ID = "saea-governed-context-store-v1"
LEXICAL_SELECTION_POLICY_ID = "source-order-letter-bearing-case-first-v1"
EXTERNAL_SOURCE_ID_PREFIX = "external-governed-source:"
PARTICIPANT_ROSTER_KIND = "participant-roster"
DOCUMENT_LEXICON_KIND = "document-lexicon"
GOVERNED_CONTEXT_STORE_ROLES = frozenset(
    {PARTICIPANT_ROSTER_KIND, DOCUMENT_LEXICON_KIND}
)
DEFAULT_LEXICAL_LIMIT = 128
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class GovernedContextRecord:
    """One governed source and the call whose context it describes."""

    source_id: str
    source_sha256: str
    scope_sample_id: str
    source_kind: str
    content: str

    def validate(self) -> "GovernedContextRecord":
        _text(self.source_id, "source_id")
        _sha(self.source_sha256, "source_sha256")
        _text(self.scope_sample_id, "scope_sample_id")
        if self.source_id == self.scope_sample_id:
            raise RailsError("governed context source_id must differ from scope_sample_id")
        if self.source_kind not in GOVERNED_CONTEXT_STORE_ROLES:
            raise RailsError(
                "governed context source_kind must be participant-roster or document-lexicon"
            )
        if not isinstance(self.content, str):
            raise RailsError("governed context content must be text")
        measured = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if measured != self.source_sha256:
            raise RailsError("governed context content differs from source_sha256")
        return self


@dataclass(frozen=True)
class GovernedContextBuildSpec:
    """Identity and bounded view policy for one governed context store."""

    snapshot_id: str
    source_split_identity_hash: str
    store_role: str
    lexical_limit: int = DEFAULT_LEXICAL_LIMIT

    def validate(self) -> "GovernedContextBuildSpec":
        _text(self.snapshot_id, "snapshot_id")
        _sha(self.source_split_identity_hash, "source_split_identity_hash")
        if self.store_role not in GOVERNED_CONTEXT_STORE_ROLES:
            raise RailsError(
                "governed context store_role must be participant-roster or document-lexicon"
            )
        if (
            isinstance(self.lexical_limit, bool)
            or not isinstance(self.lexical_limit, int)
            or self.lexical_limit < 0
        ):
            raise RailsError("governed context lexical_limit must be a nonnegative integer")
        return self


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RailsError(f"governed context {field} must be nonempty text")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise RailsError(f"governed context {field} must be a lowercase SHA-256")
    return value


def _external_source_identity(record: GovernedContextRecord) -> str:
    return f"{EXTERNAL_SOURCE_ID_PREFIX}{record.source_kind}:{record.source_id}"


def _participant_content(content: str) -> str:
    for line in content.splitlines():
        name, separator, _role = line.partition(" - ")
        if separator and not name.strip():
            raise RailsError("participant-roster context contains an empty name")
    entries = roster_entries(content)
    if not entries:
        raise RailsError("participant-roster context must list at least one person")
    lines = []
    for name, role in entries:
        if not name:
            raise RailsError("participant-roster context contains an empty name")
        lines.append(
            f"- {name} ; role: {role}"
            if role
            else f"- {name} ; no role supplied by the source."
        )
    return (
        "Source-listed participants for this call, in original source order:\n"
        + "\n".join(lines)
        + "\nUse explicit source-listed roles only to distinguish listed people. "
        "This roster is not evidence that any listed name was spoken."
    )


def _lexical_selection(content: str, limit: int) -> tuple[str, ...]:
    """Apply source-order-letter-bearing-case-first-v1 without semantic inference."""

    distinct = []
    seen = set()
    try:
        tokens = context_tokens(content)
    except ClassListError as error:
        raise RailsError(str(error)) from error
    for token in tokens:
        if token in seen or not any(character.isalpha() for character in token):
            continue
        seen.add(token)
        distinct.append(token)
    marked = [
        token
        for token in distinct
        if token.isalpha() and any(character.isupper() for character in token)
    ]
    marked_set = set(marked)
    remainder = [token for token in distinct if token not in marked_set]
    return tuple((marked + remainder)[:limit])


def _lexicon_content(content: str, limit: int) -> str:
    selected = _lexical_selection(content, limit)
    heading = (
        f"Document lexicon selected by source-form policy "
        f"{LEXICAL_SELECTION_POLICY_ID}. The selection uses token form only and "
        "does not identify proper names or assert that a term was spoken."
    )
    if not selected:
        return heading + "\nNo lexical terms were selected."
    return heading + "\nSelected source terms, preserving exact case:\n- " + "\n- ".join(
        selected
    )


def build_governed_context_snapshot(
    records: Sequence[GovernedContextRecord],
    *,
    spec: GovernedContextBuildSpec,
) -> KnowledgeSnapshot:
    """Build one external-governed scope facet and value per source-bound call."""

    if not isinstance(spec, GovernedContextBuildSpec):
        raise RailsError("governed context builder requires GovernedContextBuildSpec")
    spec.validate()
    if (
        not isinstance(records, Sequence)
        or isinstance(records, (str, bytes))
        or not records
    ):
        raise RailsError("governed context builder requires nonempty records")

    validated = []
    source_ids = set()
    scopes = set()
    kinds = set()
    for record in records:
        if not isinstance(record, GovernedContextRecord):
            raise RailsError("governed context records must be GovernedContextRecord values")
        record.validate()
        if record.source_id in source_ids:
            raise RailsError("governed context source IDs must be unique")
        if record.scope_sample_id in scopes:
            raise RailsError("governed context scopes must be unique")
        source_ids.add(record.source_id)
        scopes.add(record.scope_sample_id)
        kinds.add(record.source_kind)
        validated.append(record)
    if len(kinds) != 1:
        raise RailsError("governed context records cannot mix source kinds")
    if kinds != {spec.store_role}:
        raise RailsError("governed context records do not match the configured store_role")

    facets = []
    values = []
    external_ids = []
    for record in sorted(validated, key=lambda item: item.scope_sample_id):
        external_id = _external_source_identity(record)
        external_ids.append(external_id)
        facet_id = f"source-scope:{spec.store_role}:{record.scope_sample_id}"
        value_id = f"governed-context:{spec.store_role}:{record.scope_sample_id}"
        content = (
            _participant_content(record.content)
            if spec.store_role == PARTICIPANT_ROSTER_KIND
            else _lexicon_content(record.content, spec.lexical_limit)
        )
        facets.append(
            KeyFacet(
                facet_id=facet_id,
                dimension="source-scope",
                representation_kind="parent-sample-id",
                representation=record.scope_sample_id,
                source_sample_ids=(external_id,),
            ).validate()
        )
        values.append(
            ValueBundle(
                value_id=value_id,
                content=content,
                associated_facet_ids=(facet_id,),
                source_sample_ids=(external_id,),
                provenance_refs=(record.source_id, f"sha256:{record.source_sha256}"),
            ).validate()
        )

    return KnowledgeSnapshot(
        snapshot_id=spec.snapshot_id,
        source_split_identity_hash=spec.source_split_identity_hash,
        source_sample_ids=tuple(sorted(external_ids)),
        builder_policy_id=GOVERNED_CONTEXT_BUILD_POLICY_ID,
        source_partition_role=EXTERNAL_GOVERNED_PARTITION_ROLE,
        facets=tuple(facets),
        values=tuple(values),
    ).validate()



__all__ = [
    "DEFAULT_LEXICAL_LIMIT",
    "DOCUMENT_LEXICON_KIND",
    "EXTERNAL_SOURCE_ID_PREFIX",
    "GOVERNED_CONTEXT_BUILD_POLICY_ID",
    "GOVERNED_CONTEXT_STORE_ROLES",
    "GovernedContextBuildSpec",
    "GovernedContextRecord",
    "LEXICAL_SELECTION_POLICY_ID",
    "PARTICIPANT_ROSTER_KIND",
    "build_governed_context_snapshot",
]
