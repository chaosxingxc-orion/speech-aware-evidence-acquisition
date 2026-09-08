"""The frozen-historical component table (WAVE R7, owner Decision 12-F).

Group C of the reuse map in
``docs/readiness/2026-09-08-openjiuwen-implementation-assessment-v1.md`` §6.3:
**36 ``configs/`` values that resolve in no ``core.base`` registry**, listed
verbatim in ``scripts/checks/engineering_base_baseline.json`` under
``unregistered_config_values``. They are 31 distinct ids -- 17 ``policy``
values, 14 ``evidence_source`` values, and two of the policy ids repeated as an
experiment fragment's ``frozen_components.controller_policy_id``.

What the R7 scan found, and why this module exists rather than a set of live
registrations
--------------------------------------------------------------------------

The assessment expected each name to be "resolved by its own probe module's
constant instead", and proposed registering them by pointing a
``POLICIES``/``EVIDENCE_SOURCES`` entry at the probe function that implements
it. A full-tree scan of the 31 ids says otherwise:

* **28 of 31 appear nowhere in ``src/`` at all.** They are declarative labels
  inside their own baseline fragment, read by nothing. The probe launcher that
  flew the cell hard-codes the behaviour and never resolves the config value.
* **3 appear in ``src/``** -- ``saea-a2t-g4-executable-microground-single-
  contact-v1``, ``saea-a2t-g5-plan-compile-execute-v1`` and
  ``saea-a2t-g6-exhaustive-family-sweep-v1`` -- and each only as a
  ``CONTROLLER_POLICY_ID`` string constant inside its own
  ``rails/probes/*`` module, used as a receipt label, never registered and
  never resolved.
* **No id names a callable with its registry's protocol.** An
  ``EVIDENCE_SOURCES`` entry is ``(sample, carrier_lock_key, values) ->
  EvidenceItem`` (``core/evidence.py``); the Audio2Tool "evidence sources" are
  handbook renderers with an entirely different shape, and pointing the name at
  one would be a claim the bytes do not support.

The second half of the finding decides the disposition. **Every one of the 19
fragments carrying these ids is cited by a sealed receipt directory under
``docs/checks/``, and 15 of them by ``docs/exposure-ledger.md``.** A sealed
row's fragment is immutable: it may not be archived, and it may not be edited
to say something the flight did not say. So the ids stay where they are, and
what changes is that the base now KNOWS them.

Each entry is a :class:`~.base.FrozenHistoricalComponent`: it resolves (so the
value is no longer a name the engineering base cannot account for, and
``scripts/checks/engineering_base_check.py`` reads it out of the canonical
registration sites like every other component id), it carries the fragment and
the sealed receipt that consumed it, and it REFUSES every call and every
component-like attribute read. Registering an id here is bookkeeping, never
rehabilitation: an A2T G-series cell that must fly again is re-expressed as a
registered phase program on ``rails.controllers.EvidenceAgentController``, the
way ``a2t-hard-validity-repair-v1`` was in this same wave.
"""

from __future__ import annotations

from typing import Mapping

from .base import CoreError, FrozenHistoricalComponent

#: Where a receipt lives, so the table below stays readable.
_CHECKS = "docs/checks/speech-aware-evidence-acquisition"

#: The shared note every A2T AgentLoop id carries: what the id meant, and
#: what replaces it.
_A2T_NOTE = (
    "Audio2Tool AgentLoop cell of the 2026-09-01..09-03 G-series. Its behaviour "
    "lived in a rails/probes launcher, not behind this name; the September audit "
    "(owner recovery plan 2026-09-03) retired that tier. Re-fly only as a "
    "registered phase program on rails.controllers.EvidenceAgentController."
)


def _entry(
    component_id: str,
    registry_kind: str,
    fragment: str,
    receipt: str,
) -> FrozenHistoricalComponent:
    return FrozenHistoricalComponent(
        component_id=component_id,
        registry_kind=registry_kind,
        fragment=f"configs/baseline/{fragment}",
        receipt=f"{_CHECKS}/{receipt}",
        note=_A2T_NOTE,
    ).validate()


#: ``policy`` ids. Seventeen, one per Audio2Tool AgentLoop baseline fragment.
FROZEN_HISTORICAL_POLICIES: Mapping[str, FrozenHistoricalComponent] = {
    entry.component_id: entry
    for entry in (
        _entry(
            "fixed-construction-semantic-ground-v2",
            "policy",
            "a2t-construction-semantic-ground-diagnostic.json",
            "2026-09-02-a2t-construction-semantic-ground-diagnostic-104-v1",
        ),
        _entry(
            "training-free-contract-preserving-self-transcript-cascade-v2",
            "policy",
            "a2t-contract-preserving-cascade-agentloop.json",
            "2026-09-01-a2t-contract-preserving-cascade-104-v2",
        ),
        _entry(
            "fixed-full-executable-ground-qualification-v1",
            "policy",
            "a2t-executable-ground-qualification.json",
            "2026-09-02-a2t-executable-ground-qualification-104-v1",
        ),
        _entry(
            "training-free-factor-top1-v1",
            "policy",
            "a2t-factor-top1-agentloop.json",
            "2026-09-01-a2t-factor-top1-104-v1",
        ),
        _entry(
            "a2t-g3-plain-english-k32-hard-validity-v1",
            "policy",
            "a2t-g3-plain-english-agentloop.json",
            "2026-09-02-a2t-g3-plain-english-v1",
        ),
        _entry(
            "saea-a2t-g4-executable-microground-single-contact-v1",
            "policy",
            "a2t-g4-executable-microground-agentloop.json",
            "2026-09-02-a2t-g4-executable-microground-e16",
        ),
        _entry(
            "saea-a2t-g5-plan-compile-execute-v1",
            "policy",
            "a2t-g5-exhaustive-family-agentloop.json",
            "2026-09-02-a2t-g5-exhaustive-family-fixed16-v1",
        ),
        _entry(
            "saea-a2t-g6-exhaustive-family-sweep-v1",
            "policy",
            "a2t-g6-exhaustive-family-sweep-agentloop.json",
            "2026-09-02-a2t-g6-exhaustive-family-sweep-fixed16-v1",
        ),
        _entry(
            "saea-a2t-g7-multimodal-exhaustive-example-ground-v2",
            "policy",
            "a2t-g7-exhaustive-example-ground-agentloop.json",
            "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1",
        ),
        _entry(
            "saea-a2t-g8-action-support-reachability-v1",
            "policy",
            "a2t-g8-action-support-reachability-agentloop.json",
            "2026-09-03-a2t-g8-action-support-reachability-fixed16-v1",
        ),
        _entry(
            "saea-a2t-g8b-action-support-reachability-v1",
            "policy",
            "a2t-g8b-action-support-reachability-agentloop.json",
            "2026-09-03-a2t-g8b-action-support-reachability-fixed16-v1",
        ),
        _entry(
            "saea-a2t-g8c-action-support-reachability-v1",
            "policy",
            "a2t-g8c-action-support-reachability-agentloop.json",
            "2026-09-03-a2t-g8c-action-support-reachability-fixed12-v1",
        ),
        _entry(
            "native-structured-action-screen-v1",
            "policy",
            "a2t-native-structured-action.json",
            "2026-09-03-a2t-native-structured-action-fixed8-v1",
        ),
        _entry(
            "training-free-self-consistency-v1",
            "policy",
            "a2t-self-consistency-agentloop.json",
            "2026-09-01-a2t-self-consistency-104-v1",
        ),
        _entry(
            "training-free-self-transcript-cascade-v1",
            "policy",
            "a2t-self-transcript-cascade-agentloop.json",
            "2026-09-01-a2t-self-transcript-cascade-104-v1",
        ),
        _entry(
            "semantic-agentloop-select-fill-top32-v1",
            "policy",
            "a2t-semantic-agentloop-select-fill-top32.json",
            "2026-09-03-a2t-select-fill-agentloop-104-v1",
        ),
        _entry(
            "semantic-agentloop-top16-v1",
            "policy",
            "a2t-semantic-agentloop-top16.json",
            "2026-09-03-a2t-semantic-agentloop-104-v1",
        ),
    )
}

#: ``evidence_source`` ids. Fourteen; two fragments share
#: ``same-core-self-transcript-content-bm25-top5`` and three share
#: ``shared-g7-normalized-assessments-with-complete-macro-actions``, so the
#: fragment named below is the FIRST declaring one, alphabetically.
FROZEN_HISTORICAL_EVIDENCE_SOURCES: Mapping[str, FrozenHistoricalComponent] = {
    entry.component_id: entry
    for entry in (
        _entry(
            "query-independent-construction-semantic-handbook",
            "evidence source",
            "a2t-construction-semantic-ground-diagnostic.json",
            "2026-09-02-a2t-construction-semantic-ground-diagnostic-104-v1",
        ),
        _entry(
            "same-core-self-transcript-content-bm25-top5",
            "evidence source",
            "a2t-contract-preserving-cascade-agentloop.json",
            "2026-09-01-a2t-contract-preserving-cascade-104-v2",
        ),
        _entry(
            "query-independent-full-executable-handbook",
            "evidence source",
            "a2t-executable-ground-qualification.json",
            "2026-09-02-a2t-executable-ground-qualification-104-v1",
        ),
        _entry(
            "semantic-factor-registry-top1-stripped",
            "evidence source",
            "a2t-factor-top1-agentloop.json",
            "2026-09-01-a2t-factor-top1-104-v1",
        ),
        _entry(
            "task-blind-English-OBS-to-construction-BM25-k32",
            "evidence source",
            "a2t-g3-plain-english-agentloop.json",
            "2026-09-02-a2t-g3-plain-english-v1",
        ),
        _entry(
            "sealed-English-state-to-deterministic-semantic-microground",
            "evidence source",
            "a2t-g4-executable-microground-agentloop.json",
            "2026-09-02-a2t-g4-executable-microground-e16",
        ),
        _entry(
            "closed-English-family-taxonomy-to-deterministic-full-unranked-"
            "family-contract-bundle",
            "evidence source",
            "a2t-g5-exhaustive-family-agentloop.json",
            "2026-09-02-a2t-g5-exhaustive-family-fixed16-v1",
        ),
        _entry(
            "exhaustive-family-local-reference-scan-then-evidence-bound-resolution",
            "evidence source",
            "a2t-g6-exhaustive-family-sweep-agentloop.json",
            "2026-09-02-a2t-g6-exhaustive-family-sweep-fixed16-v1",
        ),
        _entry(
            "exhaustive-construction-example-family-assessment",
            "evidence source",
            "a2t-g7-exhaustive-example-ground-agentloop.json",
            "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1",
        ),
        _entry(
            "shared-g7-normalized-assessments-with-complete-macro-actions",
            "evidence source",
            "a2t-g8-action-support-reachability-agentloop.json",
            "2026-09-03-a2t-g8-action-support-reachability-fixed16-v1",
        ),
        _entry(
            "paired-complete-registry-or-values-stripped-executable-handbook",
            "evidence source",
            "a2t-native-structured-action.json",
            "2026-09-03-a2t-native-structured-action-fixed8-v1",
        ),
        _entry(
            "registry-resolved-union-stripped",
            "evidence source",
            "a2t-self-consistency-agentloop.json",
            "2026-09-01-a2t-self-consistency-104-v1",
        ),
        _entry(
            "local-qwen3-embedding-transcript-to-build-only-tool-tier-centroids",
            "evidence source",
            "a2t-semantic-agentloop-select-fill-top32.json",
            "2026-09-03-a2t-select-fill-agentloop-104-v1",
        ),
        _entry(
            "local-qwen3-embedding-tool-tier-centroids-and-same-core-retrieval-query",
            "evidence source",
            "a2t-semantic-agentloop-top16.json",
            "2026-09-03-a2t-semantic-agentloop-104-v1",
        ),
    )
}

#: The two policy ids an EXPERIMENT fragment also declares as
#: ``frozen_components.controller_policy_id``, which
#: ``scripts/checks/engineering_base_check.py`` resolves in
#: ``core.base.AGENT_CONTROLLERS`` rather than in ``POLICIES``. Registered from
#: ``rails/controllers.py``, the canonical site for that registry.
FROZEN_HISTORICAL_AGENT_CONTROLLERS: Mapping[str, FrozenHistoricalComponent] = {
    component_id: FrozenHistoricalComponent(
        component_id=component_id,
        registry_kind="Agent controller",
        fragment=fragment,
        receipt=FROZEN_HISTORICAL_POLICIES[component_id].receipt,
        note=_A2T_NOTE,
    ).validate()
    for component_id, fragment in (
        (
            "saea-a2t-g5-plan-compile-execute-v1",
            "configs/experiment/a2t-g5-exhaustive-family-fixed16-v1.json",
        ),
        (
            "saea-a2t-g6-exhaustive-family-sweep-v1",
            "configs/experiment/a2t-g6-exhaustive-family-sweep-fixed16-v1.json",
        ),
    )
}


def frozen_policy(component_id: str) -> FrozenHistoricalComponent:
    """The frozen-historical ``policy`` entry for ``component_id``."""

    return _lookup(FROZEN_HISTORICAL_POLICIES, component_id, "policy")


def frozen_evidence_source(component_id: str) -> FrozenHistoricalComponent:
    """The frozen-historical ``evidence_source`` entry for ``component_id``."""

    return _lookup(
        FROZEN_HISTORICAL_EVIDENCE_SOURCES, component_id, "evidence source"
    )


def frozen_agent_controller(component_id: str) -> FrozenHistoricalComponent:
    """The frozen-historical ``controller_policy_id`` entry for ``component_id``."""

    return _lookup(
        FROZEN_HISTORICAL_AGENT_CONTROLLERS, component_id, "Agent controller"
    )


def _lookup(
    table: Mapping[str, FrozenHistoricalComponent], component_id: str, kind: str
) -> FrozenHistoricalComponent:
    try:
        return table[component_id]
    except KeyError:
        raise CoreError(
            f"no frozen-historical {kind} entry for {component_id!r}; "
            f"known: {sorted(table)}"
        ) from None


__all__ = [
    "FROZEN_HISTORICAL_AGENT_CONTROLLERS",
    "FROZEN_HISTORICAL_EVIDENCE_SOURCES",
    "FROZEN_HISTORICAL_POLICIES",
    "frozen_agent_controller",
    "frozen_evidence_source",
    "frozen_policy",
]
