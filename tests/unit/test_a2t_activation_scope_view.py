"""Public registry scope projection for Audio2Tool activation knowledge."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_compile_a2t as compilation
from speech_aware_evidence_acquisition.rails.errors import RailsError
from test_a2t_semantic_card_compilation import (
    _compile_native_view,
    _native_source,
    _registry_rows,
    _row,
)


SCOPE_VIEW = "tool-activation-scope-v1"


def _scope_world():
    registry = list(_registry_rows())
    registry[0] = {
        **registry[0],
        "domain": "home_media",
        "category": "AudioDevice_Control",
        "tool_name": "playMedia",
        "signature": "playMedia(secretArgument: String?)",
        "description": "Play the selected public media service.",
        "argument_defaults": "secretArgument: private-default",
        "argument_constraints": "secretArgument: [private construction detail]",
    }
    construction = replace(
        _row(),
        tool_name="playMedia",
        arg_signature=("secretArgument",),
        arg_pairs=(("secretArgument", '"PRIVATE VALUE"'),),
        call_render='playMedia(secretArgument="PRIVATE VALUE")',
    )
    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        tuple(registry), (construction,)
    )
    return tuple(registry), corpus


def _scope_snapshot(corpus, registry_rows, *, registry_sha256: str = "3" * 64):
    source = _native_source(corpus, value_view=SCOPE_VIEW)
    source["tool_registry_sha256"] = registry_sha256
    return compilation.build_native_compatible_knowledge_snapshot(
        corpus,
        compilation_source=source,
        value_view=SCOPE_VIEW,
        registry_rows=registry_rows,
    )


def _content(snapshot, tool_name: str) -> str:
    return next(
        value.content for value in snapshot.values if value.task_target == tool_name
    )


def test_scope_view_covers_all_tools_and_preserves_positive_keys() -> None:
    registry, corpus = _scope_world()
    scope = _scope_snapshot(corpus, registry)
    reversed_scope = _scope_snapshot(corpus, tuple(reversed(registry)))
    historical = compilation.build_native_compatible_knowledge_snapshot(
        corpus,
        compilation_source=_native_source(corpus, value_view="tool-activation"),
        value_view="tool-activation",
    )

    assert scope.frozen_json() == reversed_scope.frozen_json()
    assert len(scope.facets) == len(scope.values) == 152
    assert {value.task_target for value in scope.values} == {
        card.tool_name for card in corpus.tool_cards
    }
    assert [(facet.facet_id, facet.representation) for facet in scope.facets] == [
        (facet.facet_id, facet.representation) for facet in historical.facets
    ]
    assert scope.snapshot_id != historical.snapshot_id
    assert scope.source_split_identity_hash != historical.source_split_identity_hash


def test_scope_changes_affect_values_and_snapshot_but_not_keys() -> None:
    registry, corpus = _scope_world()
    changed_registry = list(registry)
    changed_registry[0] = {
        **changed_registry[0],
        "domain": "home_entertainment",
        "category": "AudioDevice_Zone",
    }

    first = _scope_snapshot(corpus, registry, registry_sha256="3" * 64)
    changed = _scope_snapshot(
        corpus, tuple(changed_registry), registry_sha256="4" * 64
    )

    assert _content(first, "playMedia") != _content(changed, "playMedia")
    assert first.content_hash() != changed.content_hash()
    assert first.snapshot_id != changed.snapshot_id
    assert [facet.representation for facet in first.facets] == [
        facet.representation for facet in changed.facets
    ]


def test_scope_value_is_only_public_name_scope_and_complete_description() -> None:
    registry, corpus = _scope_world()
    content = _content(_scope_snapshot(corpus, registry), "playMedia")

    assert content.splitlines() == [
        "TOOL ACTIVATION SCOPE playMedia",
        "Exact tool name: playMedia",
        "Public domain: home media",
        "Public category: AudioDevice Control",
        (
            "Operation and scope (public description): "
            "Play the selected public media service."
        ),
    ]
    for forbidden in (
        "secretArgument",
        "private-default",
        "PRIVATE VALUE",
        "Avoid when:",
        "Related operations",
        "Public signature:",
        "Public constraints:",
        "synthetic JSON",
        "Observed native task forms:",
        "construction support",
        "expected outcome",
        "correct answer",
    ):
        assert forbidden not in content


@pytest.mark.parametrize(
    "defect",
    (
        "empty",
        "foreign",
        "duplicate",
        "signature",
        "description",
        "empty-domain",
        "empty-category",
        "non-ascii-domain",
        "non-ascii-category",
    ),
)
def test_scope_view_rejects_invalid_public_registry_bindings(defect: str) -> None:
    registry, corpus = _scope_world()
    rows = list(registry)
    if defect == "empty":
        rows = []
    elif defect == "foreign":
        rows[0] = {
            **rows[0],
            "tool_name": "foreignTool",
            "signature": "foreignTool(secretArgument: String?)",
        }
    elif defect == "duplicate":
        rows[1] = dict(rows[0])
    elif defect == "signature":
        rows[0] = {**rows[0], "signature": "playMedia(other: String?)"}
    elif defect == "description":
        rows[0] = {**rows[0], "description": "A different public description."}
    elif defect == "empty-domain":
        rows[0] = {**rows[0], "domain": ""}
    elif defect == "empty-category":
        rows[0] = {**rows[0], "category": ""}
    elif defect == "non-ascii-domain":
        rows[0] = {**rows[0], "domain": "media-caf\u00e9"}
    else:
        rows[0] = {**rows[0], "category": "audio-\u00e9lite"}

    with pytest.raises(compilation.SemanticCardCompilationError, match="registry"):
        _scope_snapshot(corpus, tuple(rows))


def test_scope_view_requires_public_registry_rows() -> None:
    _registry, corpus = _scope_world()

    with pytest.raises(compilation.SemanticCardCompilationError, match="registry"):
        _scope_snapshot(corpus, None)


def test_shared_compiler_binds_scope_policy_and_tool_activation_role(
    tmp_path: Path,
) -> None:
    receipt, snapshot = _compile_native_view(tmp_path, SCOPE_VIEW)
    snapshot_path = tmp_path / "outputs" / "snapshot.json"
    snapshot_file_sha256 = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()

    metadata = compilation.validate_compiled_knowledge_snapshot(
        receipt,
        snapshot,
        store_role="tool-activation",
        snapshot_file_sha256=snapshot_file_sha256,
        snapshot_path=snapshot_path,
    )

    assert metadata["value_view"] == SCOPE_VIEW
    assert receipt["knowledge_snapshot"]["value_view"] == SCOPE_VIEW
    assert receipt["knowledge_snapshot"]["value_view_policy"] == (
        compilation._ACTIVATION_SCOPE_POLICY_V1
    )
    assert f"a2t-native-card-value-view:{SCOPE_VIEW}" in (
        snapshot.values[0].provenance_refs
    )
    tampered = deepcopy(receipt)
    tampered["knowledge_snapshot"]["value_view_policy"] = "different policy"
    with pytest.raises(RailsError, match="compiled store role or compiler schema differs"):
        compilation.validate_compiled_knowledge_snapshot(
            tampered,
            snapshot,
            store_role="tool-activation",
            snapshot_file_sha256=snapshot_file_sha256,
            snapshot_path=snapshot_path,
        )
    with pytest.raises(RailsError, match="compiled store role or compiler schema differs"):
        compilation.validate_compiled_knowledge_snapshot(
            receipt,
            snapshot,
            store_role="parameter-meaning",
            snapshot_file_sha256=snapshot_file_sha256,
            snapshot_path=snapshot_path,
        )


@pytest.mark.parametrize(
    ("value_view", "snapshot_sha256", "file_sha256"),
    (
        (
            None,
            "d88f144e5273c9497318a9fe568ff7d9b93e3b277256fffdeca7f3047bb21a2e",
            "8d476d35537c4fd5292571026fa268b20950dde965d324e262c65baf5a591c2e",
        ),
        (
            "full",
            "d88f144e5273c9497318a9fe568ff7d9b93e3b277256fffdeca7f3047bb21a2e",
            "8d476d35537c4fd5292571026fa268b20950dde965d324e262c65baf5a591c2e",
        ),
        (
            "tool-activation",
            "e89bc437121edf2fe9da3a2dc3ed37341c4d48af30695983320ff4707617718a",
            "c29734c4ab278776b1e8deff517715975b27e59b441349bd5336052217ba5668",
        ),
        (
            "parameter-meaning",
            "fa9b919c1a837d21928217c2d16a5da75da97a78a1eee3e731b2a6fa36bbc3cf",
            "50dfb64784cd7c005909ed67463e74548760564ec0262e9155d5902e53463905",
        ),
        (
            "tool-activation-contrast-v1",
            "b22db9fa6cd4665dc1f58986ce2ab5844c742126abd8b0ebf0d32aa15fcc7e79",
            "572857bd3e37ba195244fd5f869ce1807d01c266edf1913bd200df1c0ace4463",
        ),
    ),
)
def test_scope_extension_preserves_historical_snapshot_identities(
    tmp_path: Path,
    value_view: str | None,
    snapshot_sha256: str,
    file_sha256: str,
) -> None:
    _receipt, snapshot = _compile_native_view(tmp_path, value_view)
    snapshot_path = tmp_path / "outputs" / "snapshot.json"

    assert snapshot.content_hash() == snapshot_sha256
    assert hashlib.sha256(snapshot_path.read_bytes()).hexdigest() == file_sha256
