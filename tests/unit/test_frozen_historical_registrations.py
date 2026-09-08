"""WAVE R7 Group C: every retired A2T AgentLoop config id resolves, and refuses.

The engineering-base ratchet used to list 36 ``configs/`` values resolving in no
``core.base`` registry (``scripts/checks/engineering_base_baseline.json`` at
commit ``bd366feb``). All 36 now resolve as
``core.base.FrozenHistoricalComponent`` entries -- accounted for, never
runnable. These tests pin both halves of that claim, plus the provenance each
entry carries.
"""

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import evidence, policies  # noqa: F401
from speech_aware_evidence_acquisition.core.base import (
    AGENT_CONTROLLERS,
    EVIDENCE_SOURCES,
    POLICIES,
    CoreError,
    FrozenHistoricalComponent,
)
from speech_aware_evidence_acquisition.core.frozen_historical import (
    FROZEN_HISTORICAL_AGENT_CONTROLLERS,
    FROZEN_HISTORICAL_EVIDENCE_SOURCES,
    FROZEN_HISTORICAL_POLICIES,
    frozen_policy,
)
from speech_aware_evidence_acquisition.rails import controllers  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The 36 baseline entries, verbatim from the ratchet baseline captured at
#: ``bd366feb1347e0b43a647598c23993fc2e0793a2``. Written out here rather than
#: read from the (now-empty) baseline rule, so shrinking the baseline can never
#: shrink this test with it.
RETIRED_BASELINE_ENTRIES = (
    "configs/baseline/a2t-construction-semantic-ground-diagnostic.json::evidence_source=query-independent-construction-semantic-handbook",
    "configs/baseline/a2t-construction-semantic-ground-diagnostic.json::policy=fixed-construction-semantic-ground-v2",
    "configs/baseline/a2t-contract-preserving-cascade-agentloop.json::evidence_source=same-core-self-transcript-content-bm25-top5",
    "configs/baseline/a2t-contract-preserving-cascade-agentloop.json::policy=training-free-contract-preserving-self-transcript-cascade-v2",
    "configs/baseline/a2t-executable-ground-qualification.json::evidence_source=query-independent-full-executable-handbook",
    "configs/baseline/a2t-executable-ground-qualification.json::policy=fixed-full-executable-ground-qualification-v1",
    "configs/baseline/a2t-factor-top1-agentloop.json::evidence_source=semantic-factor-registry-top1-stripped",
    "configs/baseline/a2t-factor-top1-agentloop.json::policy=training-free-factor-top1-v1",
    "configs/baseline/a2t-g3-plain-english-agentloop.json::evidence_source=task-blind-English-OBS-to-construction-BM25-k32",
    "configs/baseline/a2t-g3-plain-english-agentloop.json::policy=a2t-g3-plain-english-k32-hard-validity-v1",
    "configs/baseline/a2t-g4-executable-microground-agentloop.json::evidence_source=sealed-English-state-to-deterministic-semantic-microground",
    "configs/baseline/a2t-g4-executable-microground-agentloop.json::policy=saea-a2t-g4-executable-microground-single-contact-v1",
    "configs/baseline/a2t-g5-exhaustive-family-agentloop.json::evidence_source=closed-English-family-taxonomy-to-deterministic-full-unranked-family-contract-bundle",
    "configs/baseline/a2t-g5-exhaustive-family-agentloop.json::policy=saea-a2t-g5-plan-compile-execute-v1",
    "configs/baseline/a2t-g6-exhaustive-family-sweep-agentloop.json::evidence_source=exhaustive-family-local-reference-scan-then-evidence-bound-resolution",
    "configs/baseline/a2t-g6-exhaustive-family-sweep-agentloop.json::policy=saea-a2t-g6-exhaustive-family-sweep-v1",
    "configs/baseline/a2t-g7-exhaustive-example-ground-agentloop.json::evidence_source=exhaustive-construction-example-family-assessment",
    "configs/baseline/a2t-g7-exhaustive-example-ground-agentloop.json::policy=saea-a2t-g7-multimodal-exhaustive-example-ground-v2",
    "configs/baseline/a2t-g8-action-support-reachability-agentloop.json::evidence_source=shared-g7-normalized-assessments-with-complete-macro-actions",
    "configs/baseline/a2t-g8-action-support-reachability-agentloop.json::policy=saea-a2t-g8-action-support-reachability-v1",
    "configs/baseline/a2t-g8b-action-support-reachability-agentloop.json::evidence_source=shared-g7-normalized-assessments-with-complete-macro-actions",
    "configs/baseline/a2t-g8b-action-support-reachability-agentloop.json::policy=saea-a2t-g8b-action-support-reachability-v1",
    "configs/baseline/a2t-g8c-action-support-reachability-agentloop.json::evidence_source=shared-g7-normalized-assessments-with-complete-macro-actions",
    "configs/baseline/a2t-g8c-action-support-reachability-agentloop.json::policy=saea-a2t-g8c-action-support-reachability-v1",
    "configs/baseline/a2t-native-structured-action.json::evidence_source=paired-complete-registry-or-values-stripped-executable-handbook",
    "configs/baseline/a2t-native-structured-action.json::policy=native-structured-action-screen-v1",
    "configs/baseline/a2t-self-consistency-agentloop.json::evidence_source=registry-resolved-union-stripped",
    "configs/baseline/a2t-self-consistency-agentloop.json::policy=training-free-self-consistency-v1",
    "configs/baseline/a2t-self-transcript-cascade-agentloop.json::evidence_source=same-core-self-transcript-content-bm25-top5",
    "configs/baseline/a2t-self-transcript-cascade-agentloop.json::policy=training-free-self-transcript-cascade-v1",
    "configs/baseline/a2t-semantic-agentloop-select-fill-top32.json::evidence_source=local-qwen3-embedding-transcript-to-build-only-tool-tier-centroids",
    "configs/baseline/a2t-semantic-agentloop-select-fill-top32.json::policy=semantic-agentloop-select-fill-top32-v1",
    "configs/baseline/a2t-semantic-agentloop-top16.json::evidence_source=local-qwen3-embedding-tool-tier-centroids-and-same-core-retrieval-query",
    "configs/baseline/a2t-semantic-agentloop-top16.json::policy=semantic-agentloop-top16-v1",
    "configs/experiment/a2t-g5-exhaustive-family-fixed16-v1.json::frozen_components.controller_policy_id=saea-a2t-g5-plan-compile-execute-v1",
    "configs/experiment/a2t-g6-exhaustive-family-sweep-fixed16-v1.json::frozen_components.controller_policy_id=saea-a2t-g6-exhaustive-family-sweep-v1",
)


def _split(entry: str) -> tuple[str, str, str]:
    fragment, rest = entry.split("::", 1)
    key, value = rest.split("=", 1)
    return fragment, key, value


def test_every_retired_baseline_entry_now_resolves_in_a_core_base_registry():
    unresolved = []
    for entry in RETIRED_BASELINE_ENTRIES:
        _fragment, key, value = _split(entry)
        if key == "policy":
            resolved = value in POLICIES.names() or value in AGENT_CONTROLLERS.names()
        elif key == "evidence_source":
            resolved = value in EVIDENCE_SOURCES.names()
        else:
            resolved = value in AGENT_CONTROLLERS.names()
        if not resolved:
            unresolved.append(entry)
    assert unresolved == []


def test_the_registered_object_is_frozen_historical_never_a_live_component():
    for entry in RETIRED_BASELINE_ENTRIES:
        _fragment, key, value = _split(entry)
        registry = {
            "policy": POLICIES,
            "evidence_source": EVIDENCE_SOURCES,
        }.get(key, AGENT_CONTROLLERS)
        if key == "policy" and value not in registry.names():
            registry = AGENT_CONTROLLERS
        assert isinstance(registry.resolve(value), FrozenHistoricalComponent)


def test_the_three_tables_cover_exactly_the_retired_ids():
    policy_ids = {v for _f, k, v in map(_split, RETIRED_BASELINE_ENTRIES) if k == "policy"}
    evidence_ids = {
        v for _f, k, v in map(_split, RETIRED_BASELINE_ENTRIES) if k == "evidence_source"
    }
    controller_ids = {
        v
        for _f, k, v in map(_split, RETIRED_BASELINE_ENTRIES)
        if k == "frozen_components.controller_policy_id"
    }
    assert set(FROZEN_HISTORICAL_POLICIES) == policy_ids
    assert set(FROZEN_HISTORICAL_EVIDENCE_SOURCES) == evidence_ids
    assert set(FROZEN_HISTORICAL_AGENT_CONTROLLERS) == controller_ids
    assert len(policy_ids) == 17
    assert len(evidence_ids) == 14


@pytest.mark.parametrize(
    "table",
    [
        FROZEN_HISTORICAL_POLICIES,
        FROZEN_HISTORICAL_EVIDENCE_SOURCES,
        FROZEN_HISTORICAL_AGENT_CONTROLLERS,
    ],
)
def test_every_entry_keys_itself_and_points_at_a_real_sealed_receipt(table):
    for key, entry in table.items():
        assert entry.component_id == key
        receipt = REPO_ROOT / entry.receipt
        assert receipt.is_dir(), f"{key}: missing sealed receipt {entry.receipt}"
        fragment = REPO_ROOT / entry.fragment
        assert fragment.is_file(), f"{key}: missing fragment {entry.fragment}"


def test_every_fragment_really_declares_the_id_it_is_credited_with():
    for table in (FROZEN_HISTORICAL_POLICIES, FROZEN_HISTORICAL_EVIDENCE_SOURCES):
        for key, entry in table.items():
            document = json.loads(
                (REPO_ROOT / entry.fragment).read_text(encoding="utf-8")
            )
            declared = {document.get("policy"), document.get("evidence_source")}
            assert key in declared, f"{entry.fragment} does not declare {key}"


def test_calling_a_frozen_historical_entry_refuses_and_names_its_receipt():
    entry = frozen_policy("saea-a2t-g5-plan-compile-execute-v1")
    with pytest.raises(CoreError) as excinfo:
        entry(object())
    message = str(excinfo.value)
    assert "FROZEN-HISTORICAL" in message
    assert entry.receipt in message
    assert entry.fragment in message


def test_reading_a_component_like_attribute_refuses_too():
    entry = frozen_policy("training-free-self-consistency-v1")
    with pytest.raises(CoreError, match="FROZEN-HISTORICAL"):
        entry.run  # noqa: B018 -- the read itself is what must refuse
    # Private/dunder lookups keep raising AttributeError so dataclass, copy and
    # pickle machinery behave normally.
    with pytest.raises(AttributeError):
        entry._not_a_field  # noqa: B018


def test_frozen_historical_never_shadows_a_live_registration():
    live_policies = {
        name
        for name in POLICIES.names()
        if not isinstance(POLICIES.resolve(name), FrozenHistoricalComponent)
    }
    live_sources = {
        name
        for name in EVIDENCE_SOURCES.names()
        if not isinstance(EVIDENCE_SOURCES.resolve(name), FrozenHistoricalComponent)
    }
    assert live_policies & set(FROZEN_HISTORICAL_POLICIES) == set()
    assert live_sources & set(FROZEN_HISTORICAL_EVIDENCE_SOURCES) == set()
    # "fixed" and the four obs-loop policies are still live and still runnable.
    assert "fixed" in live_policies
    assert "conec-contexts" in live_sources


def test_the_ratchet_rule_this_wave_cleared_is_empty_and_the_others_are_not():
    baseline = json.loads(
        (REPO_ROOT / "scripts/checks/engineering_base_baseline.json").read_text(
            encoding="utf-8"
        )
    )
    rules = baseline["rules"]
    assert rules["unregistered_config_values"] == []
    # Ratchets move DOWN only: the other four rules keep their entries until
    # their own wave clears them.
    assert rules["probe_modules"]
    assert rules["adapter_subclasses_outside_adapters"]
