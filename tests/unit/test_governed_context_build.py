"""Pure governed builder: source fidelity, view policy and identity."""
from dataclasses import replace
import hashlib

import pytest

from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.governed_context_build import (
    GovernedContextRecord, GovernedContextBuildSpec, build_governed_context_snapshot,
    LEXICAL_SELECTION_POLICY_ID,
)


def record(content="Jane Doe - CFO\nJohn Roe\n", kind="participant-roster", scope="call-a"):
    return GovernedContextRecord(
        source_id="conec://" + kind + "/" + scope,
        source_sha256=hashlib.sha256(content.encode()).hexdigest(),
        scope_sample_id=scope, source_kind=kind, content=content,
    )


def build(records, *, role="participant-roster", limit=128):
    return build_governed_context_snapshot(records, spec=GovernedContextBuildSpec(
        snapshot_id="synthetic-governed", source_split_identity_hash="a" * 64,
        store_role=role, lexical_limit=limit,
    ))


def test_roster_keeps_names_roles_newlines_and_external_provenance():
    source = record()
    snapshot = build([source])
    value = snapshot.values[0]
    assert "Jane Doe ; role: CFO\n- John Roe ; no role supplied" in value.content
    assert "not evidence that any listed name was spoken" in value.content
    assert "\\n" not in value.content
    assert snapshot.facets[0].representation == source.scope_sample_id
    assert value.source_sample_ids == snapshot.facets[0].source_sample_ids
    assert value.source_sample_ids != (source.scope_sample_id,)
    assert value.provenance_refs == (source.source_id, "sha256:" + source.source_sha256)
    assert value.task_target is None and value.prior_score is None


def test_lexicon_selects_source_form_and_keeps_case_without_numeric_facts():
    source = record(
        "lower 1\nAlpha 2\n123 3\nC.L. 1\nUPPER 2\nlower 1\nalpha 1\nA-10 1\n",
        "document-lexicon",
    )
    snapshot = build([source], role="document-lexicon", limit=6)
    value = snapshot.values[0]
    assert value.content.endswith("- Alpha\n- UPPER\n- lower\n- C.L.\n- alpha\n- A-10")
    assert LEXICAL_SELECTION_POLICY_ID in value.content
    assert "123" not in value.content
    assert build([source], role="document-lexicon", limit=6).frozen_json() == snapshot.frozen_json()
    assert build([source], role="document-lexicon", limit=0).values[0].content.endswith(
        "No lexical terms were selected."
    )
    assert build([source], role="document-lexicon", limit=1).content_hash() != snapshot.content_hash()


def test_source_content_and_scope_change_bound_identity():
    first = record()
    second = record("Jane Doe - CEO\n", scope="call-b")
    left, right = build([first]), build([second])
    assert left.content_hash() != right.content_hash()
    together = build([second, first])
    assert [facet.representation for facet in together.facets] == ["call-a", "call-b"]
    assert together.values[1].provenance_refs[0] == second.source_id


@pytest.mark.parametrize("fault", ["sha", "scope-source", "duplicate", "mixed", "empty-name", "empty", "bad-token"])
def test_malformed_or_unbound_sources_refuse(fault):
    source = record()
    records = [source]
    if fault == "sha":
        records = [replace(source, source_sha256="0" * 64)]
    elif fault == "scope-source":
        records = [replace(source, source_id=source.scope_sample_id)]
    elif fault == "duplicate":
        records += records
    elif fault == "mixed":
        records += [record("Alpha 1\n", "document-lexicon", "call-b")]
    elif fault == "empty-name":
        records = [record(" - CFO\n")]
    elif fault == "empty":
        records = [record("")]
    else:
        with pytest.raises((RailsError, ValueError)):
            build([record("malformed\n", "document-lexicon")], role="document-lexicon")
        return
    with pytest.raises((RailsError, ValueError)):
        build(records)
