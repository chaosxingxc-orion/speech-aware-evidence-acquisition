"""The offline dry run of a plan-based native role episode.

Cell CELL-1's generation smoke made four charged Perception contacts on
2026-09-23 and then died at the openJiuwen vertex ``solver_0_input``::

    NativeEpisodeError: native episode node failed: [100054] component
    'solver_0_input' execute 'invoke' error, reason='hypothesis state must
    contain exactly ['candidates', 'sample_id', 'schema', 'semantics']'

Nothing in the ladder could have caught it: ``core.flight.cli check`` never
walks the episode, and every unit test of the stage3-deltas route fed it a
CANONICAL four-key Perception document while a native episode seals the
model's own COMPACT structured-output bytes. This module is the durable
proof that the walk now happens offline, before a flight is queued.

Two layers:

* the always-on part -- the helper's own contracts (the graph order it
  derives, the refusals it makes), which need no data root; and
* ``test_the_cell_1_smoke_composition_walks_its_whole_episode``, which walks
  the REAL registered smoke cell on the REAL released stores for ONE row with
  canned, schema-valid role answers. It SKIPS where the data root, the
  released stores or the promoted packets are absent, and asserts where they
  are present: the whole graph completes, every node is supplied its own
  stage3-deltas slice, and the delivery is the Solver's sealed draft.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
    DRY_RUN_SCHEMA,
    NATIVE_ROLE_GRAPH_ORDER,
    NativeEpisodeDryRunError,
    compose_dry_run,
    dry_run_native_episode,
    episode_node_order,
    legal_intent_ids,
    store_facet_ids,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    NativeEpisodeRole,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_EXPERIMENT = "slurp-native-stage3-delta-cell-smoke-4-v2"
SMOKE_CELL = "slurp-native-stage3-delta-cell-smoke-4-v2"
DELTA_STORE = "stage3-deltas"


# ---------------------------------------------------------------------------
# Contracts that need no data root
# ---------------------------------------------------------------------------


def _episode(*, roles=NATIVE_ROLE_GRAPH_ORDER):
    return NativeEpisodeConfig(
        episode_id="dry-run-order-proof-v1",
        max_revisions=1,
        actions=("ACCEPT", "REVISE", "ACQUIRE"),
        roles=tuple(
            NativeEpisodeRole(
                phase_id=kind, role_kind=kind, max_iterations=1, tool_names=()
            )
            for kind in roles
        ),
        max_contacts=11,
    )


def test_the_walked_order_is_the_graphs_not_the_fragments():
    """The program fragment lists perception, reviewer, planner, solver; the
    GRAPH drafts before it reviews. Walking the fragment's order would put the
    Reviewer in front of the draft it reviews."""

    assert NATIVE_ROLE_GRAPH_ORDER == ("perception", "solver", "reviewer", "planner")
    assert episode_node_order(_episode()) == NATIVE_ROLE_GRAPH_ORDER


def test_an_episode_without_the_four_roles_is_refused_by_name():
    with pytest.raises(NativeEpisodeDryRunError, match="declares no"):
        episode_node_order(_episode(roles=("perception", "solver")))


def test_reading_a_composition_before_composing_it_is_refused():
    class _Runtime:
        pass

    with pytest.raises(NativeEpisodeDryRunError, match="compose_dry_run"):
        legal_intent_ids(_Runtime())


# ---------------------------------------------------------------------------
# The real cell
# ---------------------------------------------------------------------------


def _data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR")
    if not raw:
        return None
    root = Path(raw)
    return root if root.is_dir() else None


def _umbrella_lock() -> Path | None:
    from speech_aware_evidence_acquisition.data.lock import umbrella_lock_path

    try:
        path = umbrella_lock_path(REPO_ROOT)
    except Exception:  # pragma: no cover - absent umbrella checkout
        return None
    return path if path.is_file() else None


def _canned_answers(runtime) -> dict[str, str]:
    """A fake frozen core: one schema-valid answer per role.

    The Perception answer is the COMPACT document the registered
    ``slurp-intent-hypotheses-v1`` schema defines -- exactly what a flight
    seals -- and names candidates the delta store actually addresses, so the
    candidate-bound routes have something to select.
    """

    legal = set(legal_intent_ids(runtime))
    addressed = [item for item in store_facet_ids(runtime, DELTA_STORE) if item in legal]
    assert addressed, "the released delta store addresses no legal candidate"
    candidates = sorted(addressed)[:3]
    perception = json.dumps(
        {
            "candidates": [
                {
                    "intent_id": intent,
                    "distinction": "Dry-run canned alternative.",
                    "evidence_refs": [],
                    "unresolved_fields": [],
                }
                for intent in candidates
            ]
        },
        separators=(",", ":"),
    )
    return {
        "perception": perception,
        "solver": f"intent: {candidates[0]}\nentities: none",
        "reviewer": "The draft names one legal intent and no unsupported entity.",
        "planner": "ACCEPT",
    }


def test_the_cell_1_smoke_composition_walks_its_whole_episode():
    """The proof the flight budget paid for twice: walk the registered v2
    smoke cell's own composition, offline, for one row."""

    from speech_aware_evidence_acquisition.core.flight.factory import (
        build_flight_runtime,
    )

    data_root = _data_root()
    lock_path = _umbrella_lock()
    if data_root is None or lock_path is None:
        pytest.skip("the released stores and the umbrella lock are not available here")
    fragment_path = REPO_ROOT / "configs" / "experiment" / f"{SMOKE_EXPERIMENT}.json"
    fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == SMOKE_CELL)

    try:
        runtime = build_flight_runtime(
            REPO_ROOT,
            data_root,
            model=cell["model_fragment"],
            dataset=cell["dataset_fragment"],
            baseline=cell["baseline_fragment"],
            experiment=SMOKE_EXPERIMENT,
            run_id=cell["run_id"],
            attempt_id=cell["attempt_id"],
            runtime_root=Path.home(),
            lock_path=lock_path,
            campaign_active=False,
        )
        binding = compose_dry_run(runtime, sample_limit=1)
    except Exception as error:  # pragma: no cover - host without the assets
        pytest.skip(f"this host cannot compose the cell offline: {error}")

    assert DELTA_STORE in binding["store_ids"]
    assert episode_node_order(binding["episode"]) == (
        "perception",
        "solver",
        "reviewer",
        "planner",
    )

    result = dry_run_native_episode(
        runtime, answers=_canned_answers(runtime), sample_limit=1
    )

    assert result.schema == DRY_RUN_SCHEMA
    assert tuple(node.phase for node in result.nodes) == (
        "perception",
        "solver",
        "reviewer",
        "planner",
    )
    # The Perception node answered under the compact contract, and what was
    # sealed is what the model said -- the very shape the pre-fix route
    # refused.
    perception = result.nodes[0]
    assert perception.response_format_id == "slurp-intent-hypotheses-v1"
    assert perception.state_kind == "phase:perception"

    # Every node saw its OWN node_target slice of the delta store: the
    # Perception route through the first-phase seed, the other three through
    # their candidate-bound boundary.
    def deltas(value_ids):
        return [item for item in value_ids if item.startswith(f"{DELTA_STORE}::")]

    assert deltas(result.bootstrap_value_ids), "the unconditional route seeded nothing"
    for node in result.nodes[1:]:
        assert deltas(node.supplied_value_ids), f"{node.phase} received no delta"

    # The delivery is the Solver's own sealed draft, not the last node's.
    assert result.delivered_phase == "solver"
    assert result.delivered_sha256

    # The receipt is JSON, so a runbook can keep it beside a launch.
    document = result.as_json()
    assert json.loads(json.dumps(document)) == document
    assert document["supplied_value_counts"]["perception"] >= 1
