"""Create-only, source-verified persistence for native reward links."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import test_reward_links as reward_fixtures

from speech_aware_evidence_acquisition.rails.reward_link_io import (
    REWARD_LINK_ARTIFACT_CONFIG_SCHEMA,
    REWARD_LINK_ARTIFACT_SCHEMA,
    RewardLinkArtifactError,
    build_reward_link_artifact,
    read_reward_link_artifact,
    read_verified_reward_link_artifact,
)
from speech_aware_evidence_acquisition.rails.reward_links import RewardProjection

pytest_plugins = ("test_bundle",)


@pytest.fixture
def reward_completed_source(synthetic_world, bundled_repo, tmp_path):
    return reward_fixtures.completed_source.__wrapped__(
        synthetic_world, bundled_repo, tmp_path,
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _config(source_fixture) -> dict[str, object]:
    manifest, receipt, roster, _, _ = source_fixture
    return {
        "schema": REWARD_LINK_ARTIFACT_CONFIG_SCHEMA,
        "manifest": {"path": str(manifest), "sha256": _sha(manifest)},
        "complete_score_receipt": {
            "cell_id": receipt.cell_id,
            "path": str(receipt.path),
            "sha256": receipt.sha256,
        },
        "construction_roster": {"path": str(roster), "sha256": _sha(roster)},
        "projection": reward_fixtures._projection().as_json(),
    }


def test_create_read_round_trip_reverifies_sources_without_answer_text(
    reward_completed_source, tmp_path,
):
    config = _config(reward_completed_source)
    output = tmp_path / "reward-links.json"

    receipt = build_reward_link_artifact(config, output)
    sources = read_reward_link_artifact(config, output)
    document = json.loads(output.read_text(encoding="utf-8"))

    assert receipt == {"path": str(output.resolve()), "sha256": _sha(output)}
    assert document["schema"] == REWARD_LINK_ARTIFACT_SCHEMA
    assert document["source_pins"] == {
        key: config[key]
        for key in ("manifest", "complete_score_receipt", "construction_roster")
    }
    assert document["projection"] == config["projection"]
    assert [source.source_sample_id for source in sources] == [
        row["source"]["source_sample_id"] for row in document["links"]
    ]
    serialized = output.read_text(encoding="utf-8").lower()
    for forbidden in ("gold", "reference_text", "reference transcript", "target_text"):
        assert forbidden not in serialized


@pytest.mark.parametrize("source_name", ["manifest", "complete_score_receipt"])
def test_reader_refuses_changed_authoritative_source(reward_completed_source, tmp_path, source_name):
    config = _config(reward_completed_source)
    output = tmp_path / "reward-links.json"
    build_reward_link_artifact(config, output)
    path = Path(config[source_name]["path"])
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(RewardLinkArtifactError, match="hash"):
        read_reward_link_artifact(config, output)


def test_builder_refuses_wrong_config_pin(reward_completed_source, tmp_path):
    config = _config(reward_completed_source)
    config["construction_roster"]["sha256"] = "f" * 64

    with pytest.raises(RewardLinkArtifactError, match="hash"):
        build_reward_link_artifact(config, tmp_path / "reward-links.json")


def test_builder_never_overwrites_existing_output(reward_completed_source, tmp_path):
    config = _config(reward_completed_source)
    output = tmp_path / "reward-links.json"
    output.write_text("sentinel", encoding="utf-8")

    with pytest.raises(RewardLinkArtifactError, match="already exists"):
        build_reward_link_artifact(config, output)
    assert output.read_text(encoding="utf-8") == "sentinel"


def test_reader_refuses_cross_binding_and_artifact_tamper(reward_completed_source, tmp_path):
    config = _config(reward_completed_source)
    output = tmp_path / "reward-links.json"
    build_reward_link_artifact(config, output)

    other = copy.deepcopy(config)
    other["projection"] = RewardProjection(
        "other-rule", "asr-wer", ("samples",),
        ("wer", "hits", "substitutions", "deletions", "insertions"),
    ).as_json()
    with pytest.raises(RewardLinkArtifactError, match="binding"):
        read_reward_link_artifact(other, output)

    document = json.loads(output.read_text(encoding="utf-8"))
    document["links"][0]["native_score_vector"]["aggregate"]["samples"] += 1
    output.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises((RewardLinkArtifactError, ValueError), match="hash|differ"):
        read_reward_link_artifact(config, output)

@pytest.mark.parametrize(
    "mutation, match",
    [
        (lambda config: config.update(extra=True), "missing or unknown"),
        (lambda config: config.update(schema="wrong"), "unsupported"),
        (lambda config: config.update(manifest=[]), "must be an object"),
        (
            lambda config: config.update(
                manifest={"path": config["manifest"]["path"], "sha256": "BAD"}
            ),
            "SHA-256",
        ),
    ],
)
def test_config_and_pin_schema_fail_closed(reward_completed_source, tmp_path, mutation, match):
    config = _config(reward_completed_source)
    mutation(config)

    with pytest.raises(RewardLinkArtifactError, match=match):
        build_reward_link_artifact(config, tmp_path / "reward-links.json")


@pytest.mark.parametrize("mutation, match", [
    (lambda document: document.update(schema="wrong"), "schema"),
    (lambda document: document.update(links=[]), "ordered links"),
    (lambda document: document["links"][0].update(extra=True), "stored reward link"),
])
def test_reader_refuses_malformed_artifact(reward_completed_source, tmp_path, mutation, match):
    config = _config(reward_completed_source)
    output = tmp_path / "reward-links.json"
    build_reward_link_artifact(config, output)
    document = json.loads(output.read_text(encoding="utf-8"))
    mutation(document)
    output.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(RewardLinkArtifactError, match=match):
        read_reward_link_artifact(config, output)


def test_reader_refuses_missing_artifact_after_source_preflight(reward_completed_source, tmp_path):
    with pytest.raises(RewardLinkArtifactError, match="cannot read reward-link artifact"):
        read_reward_link_artifact(_config(reward_completed_source), tmp_path / "missing.json")



def test_relative_source_pin_is_refused(reward_completed_source, tmp_path):
    config = _config(reward_completed_source)
    config["manifest"]["path"] = "relative/manifest.json"

    with pytest.raises(RewardLinkArtifactError, match="absolute"):
        build_reward_link_artifact(config, tmp_path / "reward-links.json")


def test_builder_preserves_existing_dangling_output_link(reward_completed_source, tmp_path):
    config = _config(reward_completed_source)
    output = tmp_path / "reward-links.json"
    target = tmp_path / "missing-target.json"
    output.symlink_to(target)

    with pytest.raises(RewardLinkArtifactError, match="already exists"):
        build_reward_link_artifact(config, output)
    assert output.is_symlink()
    assert output.readlink() == target
    assert not target.exists()


def test_verified_link_reader_returns_authoritatively_rebuilt_links(
    reward_completed_source, tmp_path,
):
    config = _config(reward_completed_source)
    output = tmp_path / "reward-links.json"
    build_reward_link_artifact(config, output)

    links = read_verified_reward_link_artifact(config, output)
    sources = read_reward_link_artifact(config, output)

    assert links
    assert tuple(link.source for link in links) == sources
    assert [link.link_sha256 for link in links] == [
        row["link_sha256"]
        for row in json.loads(output.read_text(encoding="utf-8"))["links"]
    ]
