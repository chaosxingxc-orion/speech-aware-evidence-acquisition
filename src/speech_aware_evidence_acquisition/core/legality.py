"""Legality-tier declaration enforcement (E1-prime): the machine-checked
counterpart to the either-field rule that, until now, lived only as prose in
arms-file headers (``docs/arms/p2-rladder-resume.arms``'s own header comment
is the precedent this closes -- "ALL ARMS CEILING-TIER: span_source=roster-
band-flag (legal) but reference_source=oracle lineage (gold-selected) -
either-field rule applies").

Doctrine source (single source of truth for the vocabulary and the rule
itself, never re-derived or duplicated here): ``docs/readiness/2026-08-15-
legality-doctrine.md``'s "Per-arm provenance schema" section, plus
``docs/p2-branch-rule-pins.md``'s worked usage. Three OPTIONAL baseline
-config keys, merged into ``core.config.compose``'s flat ``values`` mapping
like every other baseline key (declaring them already changes
``config_hash`` -> ``protocol_hash``, no separate wiring needed):

- ``span_source``: how the SPAN a targeted-delivery arm supplies was
  selected. ``"gold-aligned"`` is the one CEILING-tier marker; every other
  declared value (``"roster-band-flag"`` or another system-computed flag) is
  legal-tier.
- ``reference_source``: where the REFERENCE content came from.
  ``"oracle-lineage"`` is the one CEILING-tier marker (p1-oracle-v1/-v2 and
  their derivatives); every other declared value (a ConEC call-keyed
  document via S1 matching, a metadata roster, a pinned tier-3
  materialization, an own-draft product) is legal-tier.
- ``legality_tier``: the arm's own self-declared tier, ``"legal"`` or
  ``"ceiling"`` -- cross-checked against the two fields above, never trusted
  alone.

THE EITHER-FIELD RULE (doctrine, dimension 1): a ``legality_tier="legal"``
declaration alongside EITHER field's CEILING marker is REFUSED
(:func:`resolve_legality_declaration`) -- gold-guided selection is a
leakage channel equal to content, so a legal-tier claim can never coexist
with a gold-derived span or reference.

ORACLE-LINEAGE CONSISTENCY: an arm whose ``evidence_materialization_id`` is
itself oracle lineage (:func:`is_oracle_lineage_materialization` below,
never a ``"p1-oracle"`` prefix/substring guess) and that DOES declare
``reference_source`` must declare it consistent with that lineage (one of
``GOLD_DERIVED_REFERENCE_SOURCES``) -- a declared-but-wrong value is
refused. An arm that declares NOTHING is not refused here (see
grandfathering below); a materialization the detector cannot place at all
is likewise not asserted either way.

GRANDFATHERING: every evidence-bearing arm registered before this control
existed (every P1/P2/D4/D7 baseline fragment shipped in ``configs/
baseline/`` as of this module's introduction, oracle-lineage ones
included) declares none of these three fields. Refusing them outright
would both violate "do not edit existing config files" and retroactively
void already-consumed, already-audited runs. An evidence-bearing arm
(``evidence_source != "none"``) that does not declare all three fields
therefore only WARNS -- loudly, to stderr
(:func:`assert_legality_declaration_legal`), and into the run manifest
(``core.bundle.manifest`` calls :func:`describe_legality_for_manifest`) --
rather than refusing. Refusal is reserved for a declaration that actively
CONTRADICTS what is already known (the two rules above); silence is
tolerated, for now, never endorsed.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class LegalityError(RuntimeError):
    """A span_source/reference_source/legality_tier declaration is malformed,
    or actively contradicts the either-field rule or a known oracle-lineage
    materialization's reference_source requirement."""


# The either-field rule's two CEILING markers (module docstring) -- a
# closed, explicit vocabulary, never a substring/prefix test: a legal-tier
# value is free to contain a similar-looking word (e.g. a future
# "roster-band-flag-oracle-fallback" system flag) without tripping this
# rule, and any declared value this module does not recognise is always
# treated as legal-tier rather than silently matched as gold-derived.
GOLD_DERIVED_SPAN_SOURCES = frozenset({"gold-aligned"})
GOLD_DERIVED_REFERENCE_SOURCES = frozenset({"oracle-lineage"})

LEGALITY_TIERS = frozenset({"legal", "ceiling"})

# Explicit, curated registry of evidence_materialization_id values known, by
# direct owner/engineering review, to be gold/oracle lineage (docs/
# readiness/2026-08-15-legality-doctrine.md): p1-oracle-v1 is the FAST-3
# pilot, p1-oracle-v2 extends it to the frozen ten (byte-identical FAST-3
# candidates, manifest-asserted at construction time), p1-oracle-v2-shuffled
# is its derangement-only derivative (content verbatim from p1-oracle-v2,
# core.candidate_materializer's own module docstring). Deliberately NOT a
# "p1-oracle*" prefix/substring test -- a materialization named with an
# unrelated "oracle" substring (e.g. a fixture exercising core.evidence.
# _oracle_refusal) must never be swept in by accident. See
# :func:`is_oracle_lineage_materialization` for the second, independent
# detection path this registry is cross-checked against.
KNOWN_ORACLE_LINEAGE_MATERIALIZATION_IDS = frozenset(
    {"p1-oracle-v1", "p1-oracle-v2", "p1-oracle-v2-shuffled"}
)

# The offline materializer's own explicit marker key (present verbatim on
# every real p1-oracle-* manifest.json today -- core.candidate_materializer
# writes no such key for a legal materialization, e.g. its own
# MANIFEST_SCHEMA-carrying e003r-lex-*/p1-metadata-* outputs).
_ORACLE_MANIFEST_MARKER_KEY = "oracle_ceiling_probe"
_MAX_BASED_ON_HOPS = 4


def _materialization_manifest_path(root: Path, materialization_id: str) -> Path:
    return Path(root) / "derived" / "evidence-candidates" / materialization_id / "manifest.json"


def _read_materialization_manifest(root: Path, materialization_id: str) -> Mapping[str, object] | None:
    """Best-effort: ``None`` for anything short of a cleanly parsed JSON
    object (absent file, unreadable bytes, malformed JSON). This manifest is
    a SUPPLEMENTARY oracle-lineage signal (module docstring), never a
    required one, so its absence must never itself raise -- contrast
    ``core.exemplars.load_exemplar_manifest``, which fails closed on a
    missing manifest because ITS feature cannot function without one; this
    detector still has :data:`KNOWN_ORACLE_LINEAGE_MATERIALIZATION_IDS` to
    fall back on."""

    path = _materialization_manifest_path(root, materialization_id)
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return document if isinstance(document, Mapping) else None


def _manifest_declares_oracle_lineage(root: Path, materialization_id: str, *, _hop: int = 0) -> bool:
    """Whether ``materialization_id``'s own on-disk manifest.json declares
    oracle lineage -- directly (the offline materializer's own
    ``oracle_ceiling_probe`` key, module-level constant above) or one
    ``based_on`` hop up (``p1-oracle-v2-shuffled``'s manifest names no
    ``oracle_ceiling_probe`` key of its own, but its ``based_on.
    materialization_id`` chain points at ``p1-oracle-v2``, whose manifest
    carries the key directly). Bounded hop count so a malformed or cyclical
    ``based_on`` chain can never loop."""

    if _hop > _MAX_BASED_ON_HOPS:
        return False
    manifest = _read_materialization_manifest(root, materialization_id)
    if manifest is None:
        return False
    if _ORACLE_MANIFEST_MARKER_KEY in manifest:
        return True
    based_on = manifest.get("based_on")
    if isinstance(based_on, Mapping):
        parent_id = based_on.get("materialization_id")
        if isinstance(parent_id, str) and parent_id and parent_id != materialization_id:
            return _manifest_declares_oracle_lineage(root, parent_id, _hop=_hop + 1)
    return False


def is_oracle_lineage_materialization(materialization_id: str, root: Path) -> bool:
    """Whether ``materialization_id`` is gold/oracle lineage (module
    docstring) -- via the EXPLICIT registry above, OR the materialization's
    own on-disk manifest.json (when present, following one ``based_on`` hop
    for a derivative), never a ``materialization_id.startswith("p1-
    oracle")``-style string guess. Fail-closed toward "is oracle": either
    signal saying yes is enough, so a stale/incomplete registry can never
    silently downgrade a materialization the manifest itself already flags,
    and a materialization not yet added to the registry is still caught the
    moment its own manifest is available on disk."""

    if materialization_id in KNOWN_ORACLE_LINEAGE_MATERIALIZATION_IDS:
        return True
    return _manifest_declares_oracle_lineage(root, materialization_id)


@dataclass(frozen=True)
class LegalityDeclaration:
    """One arm's resolved legality-tier declaration -- the exact shape
    ``core.bundle.manifest`` records verbatim (module docstring, deliverable
    3)."""

    span_source: str | None
    reference_source: str | None
    legality_tier: str | None
    evidence_materialization_id: str | None
    oracle_lineage_materialization: bool
    declaration_warning: str | None

    def as_manifest_dict(self) -> dict[str, object]:
        return {
            "span_source": self.span_source,
            "reference_source": self.reference_source,
            "legality_tier": self.legality_tier,
            "evidence_materialization_id": self.evidence_materialization_id,
            "oracle_lineage_materialization": self.oracle_lineage_materialization,
            "declaration_warning": self.declaration_warning,
        }


def _require_optional_nonempty_string(values: Mapping[str, object], key: str) -> str | None:
    if key not in values or values[key] is None:
        return None
    value = values[key]
    if not isinstance(value, str) or not value:
        raise LegalityError(
            f"baseline config {key} must be a non-empty string when declared, got {value!r}"
        )
    return value


def resolve_legality_declaration(values: Mapping[str, object], root: Path) -> LegalityDeclaration:
    """Pure resolution (module docstring): validates shape and the two
    refusal rules, and computes the grandfathering warning message -- but
    never PRINTS the warning itself (that side effect belongs to the one
    call site that should say it exactly once,
    :func:`assert_legality_declaration_legal`; ``core.bundle.manifest``'s
    :func:`describe_legality_for_manifest` calls this a SECOND time,
    independently, purely to record the fields, and must never print a
    duplicate warning for the same attempt).

    Raises :class:`LegalityError` for either refusal rule; never raises for
    a merely-missing declaration (grandfathering, module docstring)."""

    span_source = _require_optional_nonempty_string(values, "span_source")
    reference_source = _require_optional_nonempty_string(values, "reference_source")
    legality_tier = _require_optional_nonempty_string(values, "legality_tier")
    if legality_tier is not None and legality_tier not in LEGALITY_TIERS:
        raise LegalityError(
            f"baseline config legality_tier must be one of {sorted(LEGALITY_TIERS)}, "
            f"got {legality_tier!r}"
        )

    raw_materialization_id = values.get("evidence_materialization_id")
    materialization_id = (
        raw_materialization_id
        if isinstance(raw_materialization_id, str) and raw_materialization_id
        else None
    )
    oracle_lineage = (
        is_oracle_lineage_materialization(materialization_id, root)
        if materialization_id is not None
        else False
    )

    # Oracle-lineage consistency: only a DECLARED-but-wrong reference_source
    # is refused (module docstring) -- an UNDECLARED reference_source on an
    # oracle-lineage arm falls through to the grandfathering warning below,
    # never a refusal, so every already-registered p1-oracle-v1/-v2 config
    # (none of which declares this field) keeps loading unchanged.
    if (
        oracle_lineage
        and reference_source is not None
        and reference_source not in GOLD_DERIVED_REFERENCE_SOURCES
    ):
        raise LegalityError(
            f"evidence_materialization_id {materialization_id!r} is oracle lineage "
            "(docs/readiness/2026-08-15-legality-doctrine.md); this arm must declare "
            "reference_source consistent with oracle lineage (one of "
            f"{sorted(GOLD_DERIVED_REFERENCE_SOURCES)}), got "
            f"reference_source={reference_source!r}"
        )

    span_gold = span_source in GOLD_DERIVED_SPAN_SOURCES
    reference_gold = reference_source in GOLD_DERIVED_REFERENCE_SOURCES
    if legality_tier == "legal" and (span_gold or reference_gold):
        raise LegalityError(
            "legality_tier='legal' is refused: the either-field rule (docs/readiness/"
            "2026-08-15-legality-doctrine.md) makes ANY gold-derived field ceiling-tier, "
            f"never legal -- span_source={span_source!r} reference_source={reference_source!r}"
        )

    evidence_bearing = str(values.get("evidence_source", "none")) != "none"
    declared_all = span_source is not None and reference_source is not None and legality_tier is not None
    warning = None
    if evidence_bearing and not declared_all:
        missing = [
            name
            for name, value in (
                ("span_source", span_source),
                ("reference_source", reference_source),
                ("legality_tier", legality_tier),
            )
            if value is None
        ]
        warning = (
            "GRANDFATHERED legality declaration: evidence-bearing arm "
            f"{values.get('arm')!r} does not declare {missing} "
            "(docs/readiness/2026-08-15-legality-doctrine.md's either-field rule); "
            "this run's provenance tier is UNVERIFIED -- see the run manifest's "
            "'legality' block"
        )

    return LegalityDeclaration(
        span_source=span_source,
        reference_source=reference_source,
        legality_tier=legality_tier,
        evidence_materialization_id=materialization_id,
        oracle_lineage_materialization=oracle_lineage,
        declaration_warning=warning,
    )


def assert_legality_declaration_legal(values: Mapping[str, object], root: Path) -> LegalityDeclaration:
    """The one call site that both enforces (module docstring's two refusal
    rules, via :func:`resolve_legality_declaration`) AND announces the
    grandfathering warning -- called once, early, in ``core.driver.run.
    run_experiment``, the same "resolved and validated HERE, before any
    other per-run work" placement ``core.evidence.assert_evidence_
    materialization_id_legal``/``core.exemplars.assert_exemplar_manifest_id_
    legal`` already established, so a refusal here spends no attempt budget
    and touches the frozen core zero times."""

    declaration = resolve_legality_declaration(values, root)
    if declaration.declaration_warning:
        print(f"WARNING: {declaration.declaration_warning}", file=sys.stderr)
    return declaration


def describe_legality_for_manifest(values: Mapping[str, object], root: Path) -> dict[str, object]:
    """The ``"legality"`` block ``core.bundle.manifest`` embeds in every run
    manifest (deliverable 3): the three fields VERBATIM off ``values`` --
    read directly, the same way ``core.bundle.manifest._manifest_document``
    already reads its own ``"arm"`` field straight off ``composed.values``
    -- so this can NEVER raise, and a manifest is always produced whether or
    not :func:`assert_legality_declaration_legal` already accepted, warned
    about, or REFUSED this same config earlier in ``run_experiment``: an
    ABORTED manifest for a refused declaration must still be writable
    (``core.driver.bundled.run_experiment_bundled``'s "a manifest is always
    produced, win or lose" contract).

    Re-runs :func:`resolve_legality_declaration` best-effort purely to
    attach the independently-recomputed oracle-lineage verdict and (when the
    declaration is otherwise legal) the grandfathering warning text; a
    validation failure is recorded as its own ``declaration_warning`` string
    (prefixed ``"REFUSED: "``) rather than propagated -- this function never
    prints anything (module docstring: printing the warning is
    :func:`assert_legality_declaration_legal`'s job alone, so a completed
    run's stderr never carries the SAME warning twice)."""

    document: dict[str, object] = {
        "span_source": values.get("span_source"),
        "reference_source": values.get("reference_source"),
        "legality_tier": values.get("legality_tier"),
        "evidence_materialization_id": values.get("evidence_materialization_id"),
        "oracle_lineage_materialization": None,
        "declaration_warning": None,
    }
    try:
        declaration = resolve_legality_declaration(values, root)
    except LegalityError as error:
        document["declaration_warning"] = f"REFUSED: {error}"
        return document
    document["oracle_lineage_materialization"] = declaration.oracle_lineage_materialization
    document["declaration_warning"] = declaration.declaration_warning
    return document
