"""Model-free tests for the G6 family-local reference renderer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.probes.a2t_g6_corpus_renderer import (
    FAMILY_REFERENCE_ASCII_BYTE_CAP,
    G6CorpusRenderer,
    G6CorpusRendererError,
)


REPO = Path(__file__).resolve().parents[2]
CORPUS = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g5-exhaustive-family-contracts-v1"
    / "corpus.json"
)


def test_loads_the_complete_frozen_registry_without_changing_its_bytes() -> None:
    before = CORPUS.read_bytes()

    renderer = G6CorpusRenderer.from_path(CORPUS)

    assert renderer.corpus_sha256 == hashlib.sha256(before).hexdigest()
    assert len(renderer.family_tags) == 28
    assert len(renderer.contract_ids) == 152
    assert len(renderer.tool_names) == 152
    assert all(
        len(renderer.render_family(tag).encode("ascii"))
        <= FAMILY_REFERENCE_ASCII_BYTE_CAP
        for tag in renderer.family_tags
    )
    assert CORPUS.read_bytes() == before


def test_rendered_family_is_ascii_reference_only_and_contract_complete() -> None:
    renderer = G6CorpusRenderer.from_path(CORPUS)

    rendered = renderer.render_family("smart-car-media-cabin")

    assert rendered == renderer.render_family("smart-car-media-cabin")
    assert rendered.isascii()
    assert "REFERENCE-ONLY" in rendered
    assert "Tool: adjustVolume" in rendered
    assert "direction: UpDown" in rendered
    assert "steps: Int" in rendered
    assert "direction: [Up, Down], steps: [1-10]" in rendered
    assert "Canonicalizers:" in rendered
    assert rendered.count("Canonicalizers:") == 1
    assert "Defaults:" not in rendered
    assert "default" not in rendered.casefold()
    assert "Example" not in rendered
    assert "final call" not in rendered.casefold()
    assert "Operation:" not in rendered
    assert len(rendered.encode("ascii")) <= FAMILY_REFERENCE_ASCII_BYTE_CAP


def test_shared_canonicalizers_are_rendered_once_and_all_families_stay_compact() -> None:
    renderer = G6CorpusRenderer.from_path(CORPUS)

    rendered = {tag: renderer.render_family(tag) for tag in renderer.family_tags}

    assert all(text.count("Canonicalizers:") == 1 for text in rendered.values())
    assert max(len(text.encode("ascii")) for text in rendered.values()) < 8_192


def test_exact_nominations_and_legal_key_sets_are_deterministic_and_family_bound() -> None:
    renderer = G6CorpusRenderer.from_path(CORPUS)
    family = "smart-car-media-cabin"

    nominated = renderer.nominated_contracts(
        family, ("adjustVolume", "controlPlayback")
    )

    assert [contract.tool_name for contract in nominated] == [
        "adjustVolume",
        "controlPlayback",
    ]
    assert renderer.legal_key_sets(family, "adjustVolume") == (
        ("direction", "steps"),
    )
    assert renderer.legal_key_sets(family, "controlPlayback") == (
        (),
        ("action",),
        ("action", "deviceId"),
    )
    assert renderer.legal_key_sets_for_nominations(family, ("adjustVolume",)) == {
        "adjustVolume": (("direction", "steps"),)
    }


@pytest.mark.parametrize(
    ("family_tag", "candidate_tools", "message"),
    [
        ("not-a-family", ("adjustVolume",), "unknown family"),
        ("smart-car-media-cabin", ("not-a-tool",), "unregistered"),
        ("smart-car-media-cabin", ("activateRoutine",), "outside family"),
        ("smart-car-media-cabin", ("adjustVolume", "adjustVolume"), "duplicated"),
    ],
)
def test_nominations_fail_closed_for_invalid_candidates(
    family_tag: str, candidate_tools: tuple[str, ...], message: str
) -> None:
    renderer = G6CorpusRenderer.from_path(CORPUS)

    with pytest.raises(G6CorpusRendererError, match=message):
        renderer.nominated_contracts(family_tag, candidate_tools)


def test_empty_nominations_are_a_family_local_scan_abstention() -> None:
    renderer = G6CorpusRenderer.from_path(CORPUS)

    assert renderer.nominated_contracts("smart-car-media-cabin", ()) == ()


@pytest.mark.parametrize(
    "candidate",
    [
        {"tool_name": "adjustVolume", "score": 1},
        {"tool_name": "adjustVolume", "sample_id": "discovery:1"},
        {"tool_name": "adjustVolume", "gold": "adjustVolume"},
        {"tool_name": "adjustVolume", "evaluation": True},
        {"tool_name": "adjustVolume", "unexpected": True},
    ],
)
def test_structured_candidates_reject_evaluation_and_non_nomination_fields(
    candidate: dict[str, object],
) -> None:
    renderer = G6CorpusRenderer.from_path(CORPUS)

    with pytest.raises(G6CorpusRendererError, match="candidate"):
        renderer.nominated_contracts("smart-car-media-cabin", (candidate,))


def test_loader_rejects_registry_drift_and_prohibited_contract_fields(tmp_path: Path) -> None:
    document = json.loads(CORPUS.read_text(encoding="ascii"))
    document["contracts"][0]["score"] = 1
    drifted = tmp_path / "drifted.json"
    drifted.write_text(json.dumps(document), encoding="ascii")

    with pytest.raises(G6CorpusRendererError, match="prohibited"):
        G6CorpusRenderer.from_path(drifted)

    document = json.loads(CORPUS.read_text(encoding="ascii"))
    document["families"][0]["sample_id"] = "forbidden"
    prohibited_family = tmp_path / "prohibited-family.json"
    prohibited_family.write_text(json.dumps(document), encoding="ascii")

    with pytest.raises(G6CorpusRendererError, match="prohibited"):
        G6CorpusRenderer.from_path(prohibited_family)

    document = json.loads(CORPUS.read_text(encoding="ascii"))
    document["families"][0]["tool_names"].append("duplicate")
    mismatched = tmp_path / "mismatched.json"
    mismatched.write_text(json.dumps(document), encoding="ascii")

    with pytest.raises(G6CorpusRendererError, match="family registry drift"):
        G6CorpusRenderer.from_path(mismatched)
