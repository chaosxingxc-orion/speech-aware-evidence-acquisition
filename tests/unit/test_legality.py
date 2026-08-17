"""``core.legality``: the machine-checked span_source/reference_source/
legality_tier either-field rule (E1-prime, docs/readiness/2026-08-15-
legality-doctrine.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.legality import (
    GOLD_DERIVED_REFERENCE_SOURCES,
    GOLD_DERIVED_SPAN_SOURCES,
    KNOWN_ORACLE_LINEAGE_MATERIALIZATION_IDS,
    LegalityError,
    assert_legality_declaration_legal,
    describe_legality_for_manifest,
    is_oracle_lineage_materialization,
    resolve_legality_declaration,
)
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

BASELINE_CONFIG_DIR = REPO_ROOT / "configs" / "baseline"


# ---------------------------------------------------------------------------
# is_oracle_lineage_materialization: registry + manifest detection, never a
# "p1-oracle" prefix/substring guess.
# ---------------------------------------------------------------------------


def test_known_oracle_lineage_ids_are_the_real_p1_oracle_family():
    assert KNOWN_ORACLE_LINEAGE_MATERIALIZATION_IDS == {
        "p1-oracle-v1",
        "p1-oracle-v2",
        "p1-oracle-v2-shuffled",
    }


def test_is_oracle_lineage_materialization_true_via_registry_alone(tmp_path):
    # No manifest.json on disk at all -- the registry hit alone is enough.
    assert is_oracle_lineage_materialization("p1-oracle-v2", tmp_path) is True


def test_is_oracle_lineage_materialization_false_for_an_unrelated_id(tmp_path):
    assert is_oracle_lineage_materialization("p1-metadata-v2", tmp_path) is False


def test_is_oracle_lineage_materialization_never_string_guesses_a_similar_name(tmp_path):
    """A materialization merely NAMED with an "oracle" substring, not present
    in the registry and with no manifest.json marking it, must NOT be swept
    in -- proves this is not a prefix/substring test."""

    assert is_oracle_lineage_materialization("oracle-smoke-fixture-v1", tmp_path) is False


def _write_manifest(root: Path, materialization_id: str, document: dict) -> None:
    out_dir = root / "derived" / "evidence-candidates" / materialization_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(document), encoding="utf-8")


def test_is_oracle_lineage_materialization_true_via_manifest_marker_not_in_registry(tmp_path):
    """A FUTURE oracle materialization, not yet added to the explicit
    registry, is still caught the moment its own manifest.json is present
    and carries the offline materializer's oracle_ceiling_probe marker."""

    _write_manifest(
        tmp_path, "p1-oracle-v3-not-yet-registered",
        {"materialization_id": "p1-oracle-v3-not-yet-registered", "oracle_ceiling_probe": "gold used offline"},
    )
    assert is_oracle_lineage_materialization("p1-oracle-v3-not-yet-registered", tmp_path) is True


def test_is_oracle_lineage_materialization_true_via_based_on_chain(tmp_path):
    """p1-oracle-v2-shuffled's real manifest carries no oracle_ceiling_probe
    key of its own -- only a based_on.materialization_id pointer to
    p1-oracle-v2, whose manifest carries the marker directly."""

    _write_manifest(
        tmp_path, "child-mat",
        {"based_on": {"materialization_id": "parent-mat"}},
    )
    _write_manifest(
        tmp_path, "parent-mat",
        {"oracle_ceiling_probe": "gold used offline at construction"},
    )
    assert is_oracle_lineage_materialization("child-mat", tmp_path) is True


def test_is_oracle_lineage_materialization_false_when_manifest_present_but_silent(tmp_path):
    _write_manifest(
        tmp_path, "p1-metadata-v3-kb34",
        {"deployment_legality": "LEGAL: all terms verbatim from metadata"},
    )
    assert is_oracle_lineage_materialization("p1-metadata-v3-kb34", tmp_path) is False


def test_is_oracle_lineage_materialization_tolerates_a_malformed_manifest(tmp_path):
    out_dir = tmp_path / "derived" / "evidence-candidates" / "broken-mat"
    out_dir.mkdir(parents=True)
    (out_dir / "manifest.json").write_text("{not valid json", encoding="utf-8")
    assert is_oracle_lineage_materialization("broken-mat", tmp_path) is False


# ---------------------------------------------------------------------------
# resolve_legality_declaration: shape validation.
# ---------------------------------------------------------------------------


def test_resolve_legality_declaration_defaults_to_all_none_when_undeclared(tmp_path):
    declaration = resolve_legality_declaration({"evidence_source": "none"}, tmp_path)
    assert declaration.span_source is None
    assert declaration.reference_source is None
    assert declaration.legality_tier is None
    assert declaration.oracle_lineage_materialization is False
    assert declaration.declaration_warning is None  # not evidence-bearing


@pytest.mark.parametrize("key", ["span_source", "reference_source", "legality_tier"])
def test_resolve_legality_declaration_refuses_an_empty_string(tmp_path, key):
    with pytest.raises(LegalityError, match=key):
        resolve_legality_declaration({key: ""}, tmp_path)


@pytest.mark.parametrize("key", ["span_source", "reference_source", "legality_tier"])
def test_resolve_legality_declaration_refuses_a_non_string(tmp_path, key):
    with pytest.raises(LegalityError, match=key):
        resolve_legality_declaration({key: 7}, tmp_path)


def test_resolve_legality_declaration_refuses_an_unknown_legality_tier(tmp_path):
    with pytest.raises(LegalityError, match="legality_tier"):
        resolve_legality_declaration({"legality_tier": "sort-of-legal"}, tmp_path)


def test_resolve_legality_declaration_accepts_ceiling_tier(tmp_path):
    declaration = resolve_legality_declaration({"legality_tier": "ceiling"}, tmp_path)
    assert declaration.legality_tier == "ceiling"


# ---------------------------------------------------------------------------
# Negative control 1: legal tier + gold-derived field => refused.
# ---------------------------------------------------------------------------


def test_legal_tier_with_oracle_reference_source_is_refused(tmp_path):
    with pytest.raises(LegalityError, match="either-field rule"):
        resolve_legality_declaration(
            {"legality_tier": "legal", "reference_source": "oracle-lineage"}, tmp_path
        )


def test_legal_tier_with_gold_aligned_span_source_is_refused(tmp_path):
    with pytest.raises(LegalityError, match="either-field rule"):
        resolve_legality_declaration(
            {"legality_tier": "legal", "span_source": "gold-aligned"}, tmp_path
        )


def test_legal_tier_with_both_fields_gold_derived_is_refused(tmp_path):
    with pytest.raises(LegalityError, match="either-field rule"):
        resolve_legality_declaration(
            {
                "legality_tier": "legal",
                "span_source": "gold-aligned",
                "reference_source": "oracle-lineage",
            },
            tmp_path,
        )


def test_legal_tier_with_legal_flagged_fields_is_accepted(tmp_path):
    declaration = resolve_legality_declaration(
        {
            "legality_tier": "legal",
            "span_source": "roster-band-flag",
            "reference_source": "metadata-roster",
            "evidence_source": "conec-contexts",
        },
        tmp_path,
    )
    assert declaration.legality_tier == "legal"
    assert declaration.declaration_warning is None


def test_ceiling_tier_with_gold_derived_fields_is_never_refused(tmp_path):
    """The either-field rule only refuses legality_tier='legal' -- a
    ceiling-tier declaration alongside a gold-derived field is exactly what
    the doctrine expects, never a refusal."""

    declaration = resolve_legality_declaration(
        {
            "legality_tier": "ceiling",
            "span_source": "gold-aligned",
            "reference_source": "oracle-lineage",
        },
        tmp_path,
    )
    assert declaration.legality_tier == "ceiling"


# ---------------------------------------------------------------------------
# Negative control 2: an oracle-lineage arm declaring itself correctly.
# ---------------------------------------------------------------------------


def test_oracle_lineage_arm_declaring_itself_correctly_is_accepted_and_recorded(tmp_path):
    declaration = resolve_legality_declaration(
        {
            "evidence_source": "derived-candidates",
            "evidence_materialization_id": "p1-oracle-v2",
            "span_source": "roster-band-flag",
            "reference_source": "oracle-lineage",
            "legality_tier": "ceiling",
        },
        tmp_path,
    )
    assert declaration.oracle_lineage_materialization is True
    assert declaration.reference_source == "oracle-lineage"
    assert declaration.legality_tier == "ceiling"
    assert declaration.declaration_warning is None


def test_oracle_lineage_arm_declaring_a_wrong_reference_source_is_refused(tmp_path):
    with pytest.raises(LegalityError, match="oracle lineage"):
        resolve_legality_declaration(
            {
                "evidence_source": "derived-candidates",
                "evidence_materialization_id": "p1-oracle-v2",
                "reference_source": "metadata-roster",
            },
            tmp_path,
        )


def test_oracle_lineage_arm_with_undeclared_reference_source_is_not_refused(tmp_path):
    """Grandfathering wins over the consistency rule when reference_source is
    simply ABSENT (never declared, as opposed to declared wrong) -- this is
    exactly the shape of every already-registered p1-oracle-v1/-v2 config."""

    declaration = resolve_legality_declaration(
        {
            "evidence_source": "derived-candidates",
            "evidence_materialization_id": "p1-oracle-v2",
        },
        tmp_path,
    )
    assert declaration.oracle_lineage_materialization is True
    assert declaration.reference_source is None
    assert declaration.declaration_warning is not None
    assert "GRANDFATHERED" in declaration.declaration_warning


# ---------------------------------------------------------------------------
# Negative control 3: missing declarations on an evidence-bearing arm warn.
# ---------------------------------------------------------------------------


def test_missing_declarations_on_an_evidence_bearing_arm_warns(tmp_path):
    declaration = resolve_legality_declaration({"evidence_source": "conec-contexts", "arm": "fixed-legal-context"}, tmp_path)
    assert declaration.declaration_warning is not None
    assert "GRANDFATHERED" in declaration.declaration_warning
    assert "span_source" in declaration.declaration_warning


def test_missing_declarations_on_a_non_evidence_bearing_arm_does_not_warn(tmp_path):
    declaration = resolve_legality_declaration({"evidence_source": "none", "arm": "bare-core"}, tmp_path)
    assert declaration.declaration_warning is None


def test_partial_declaration_on_an_evidence_bearing_arm_still_warns(tmp_path):
    declaration = resolve_legality_declaration(
        {
            "evidence_source": "conec-contexts",
            "span_source": "roster-band-flag",
            "reference_source": "metadata-roster",
        },
        tmp_path,
    )
    assert declaration.declaration_warning is not None
    assert "'legality_tier'" in declaration.declaration_warning
    assert "'span_source'" not in declaration.declaration_warning
    assert "'reference_source'" not in declaration.declaration_warning


def test_assert_legality_declaration_legal_prints_the_warning_to_stderr(tmp_path, capsys):
    declaration = assert_legality_declaration_legal({"evidence_source": "conec-contexts"}, tmp_path)
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "GRANDFATHERED" in captured.err
    assert declaration.declaration_warning is not None


def test_assert_legality_declaration_legal_is_silent_when_fully_declared(tmp_path, capsys):
    assert_legality_declaration_legal(
        {
            "evidence_source": "conec-contexts",
            "span_source": "roster-band-flag",
            "reference_source": "metadata-roster",
            "legality_tier": "legal",
        },
        tmp_path,
    )
    captured = capsys.readouterr()
    assert captured.err == ""


def test_assert_legality_declaration_legal_raises_and_prints_nothing_on_refusal(tmp_path, capsys):
    with pytest.raises(LegalityError):
        assert_legality_declaration_legal(
            {"legality_tier": "legal", "reference_source": "oracle-lineage"}, tmp_path
        )
    captured = capsys.readouterr()
    assert captured.err == ""


# ---------------------------------------------------------------------------
# describe_legality_for_manifest: never raises, records the raw fields
# verbatim even for a declaration that would be REFUSED.
# ---------------------------------------------------------------------------


def test_describe_legality_for_manifest_never_raises_for_a_refused_declaration(tmp_path):
    document = describe_legality_for_manifest(
        {"legality_tier": "legal", "reference_source": "oracle-lineage"}, tmp_path
    )
    assert document["span_source"] is None
    assert document["reference_source"] == "oracle-lineage"
    assert document["legality_tier"] == "legal"
    assert document["declaration_warning"].startswith("REFUSED:")


def test_describe_legality_for_manifest_records_a_clean_declaration(tmp_path):
    document = describe_legality_for_manifest(
        {
            "evidence_source": "derived-candidates",
            "evidence_materialization_id": "p1-oracle-v2",
            "span_source": "roster-band-flag",
            "reference_source": "oracle-lineage",
            "legality_tier": "ceiling",
        },
        tmp_path,
    )
    assert document == {
        "span_source": "roster-band-flag",
        "reference_source": "oracle-lineage",
        "legality_tier": "ceiling",
        "evidence_materialization_id": "p1-oracle-v2",
        "oracle_lineage_materialization": True,
        "declaration_warning": None,
    }


def test_describe_legality_for_manifest_records_the_grandfathering_warning(tmp_path):
    document = describe_legality_for_manifest({"evidence_source": "conec-contexts"}, tmp_path)
    assert document["declaration_warning"] is not None
    assert "GRANDFATHERED" in document["declaration_warning"]


def test_describe_legality_for_manifest_never_prints(tmp_path, capsys):
    describe_legality_for_manifest({"evidence_source": "conec-contexts"}, tmp_path)
    captured = capsys.readouterr()
    assert captured.err == ""


# ---------------------------------------------------------------------------
# Legacy-config compatibility: every existing configs/baseline/*.json
# fragment must still resolve without raising -- these tests must NEVER
# edit a config file to make this pass.
# ---------------------------------------------------------------------------


def _load_baseline_fragments():
    paths = sorted(BASELINE_CONFIG_DIR.glob("*.json"))
    assert paths, "expected at least one baseline config fragment"
    return [(path.name, json.loads(path.read_text(encoding="utf-8"))) for path in paths]


_BASELINE_FRAGMENTS = _load_baseline_fragments()


@pytest.mark.parametrize(
    "name,values", _BASELINE_FRAGMENTS, ids=[name for name, _ in _BASELINE_FRAGMENTS]
)
def test_every_existing_baseline_config_resolves_without_raising(tmp_path, name, values):
    # Every existing fragment predates span_source/reference_source/
    # legality_tier; resolve_legality_declaration must accept every one of
    # them unchanged (grandfathering), never refuse.
    declaration = resolve_legality_declaration(values, tmp_path)
    assert declaration.span_source is None
    assert declaration.reference_source is None
    assert declaration.legality_tier is None


def test_every_oracle_lineage_baseline_config_is_detected_as_oracle_lineage(tmp_path):
    """Cross-check: every SHIPPED config naming a KNOWN_ORACLE_LINEAGE_
    MATERIALIZATION_IDS materialization is actually detected as such by the
    registry path (no manifest.json needed -- these fragments never declare
    reference_source, so this only proves detection, not consistency)."""

    detected_any = False
    for _name, values in _BASELINE_FRAGMENTS:
        materialization_id = values.get("evidence_materialization_id")
        if materialization_id in KNOWN_ORACLE_LINEAGE_MATERIALIZATION_IDS:
            detected_any = True
            assert is_oracle_lineage_materialization(materialization_id, tmp_path) is True
    assert detected_any, "expected at least one shipped config to name a known oracle materialization"
