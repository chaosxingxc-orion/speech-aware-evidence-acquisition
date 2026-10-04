"""Historical own-L feedback is prior evidence, never new latency measurement."""

import copy
import pytest
from test_system_optimization import learning_fixture
from test_system_seed_successor import prepared
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    canonical,
    PolicyError,
)
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.system_search_successor import (
    build_successor,
)
from speech_aware_evidence_acquisition.rails.system_optimization import (
    exploratory_selection,
    require_exploratory_packet,
)

PROFILE = {
    "schema": "saea-system-search-measurement-v2",
    "latency_scope": "sample-admission-to-settled-workflow-v1",
    "schedule": "sequential-trajectory",
    "slot_count": 4,
    "queue_depth": 4,
    "minimum_reliable_completion_rate": 1.0,
}


def bootstrap(tmp_path):
    old, new, repo, seed, child, args, desc = prepared(tmp_path / "sequence")
    extension = build_successor(old, new, **args)
    protocol, packet = learning_fixture(tmp_path / "evidence")
    feedback = CompleteSystemFeedback(canonical(packet["feedback"]))
    own = copy.deepcopy(packet["selection"]["member_bindings"])
    own["L-parent"]["bundle_id"] = seed.bundle_id
    own["L-parent-aa"]["bundle_id"] = seed.bundle_id
    descriptor = {
        "schema": "saea-historical-seed-bootstrap-v1",
        "round": 4,
        "seed_transition": desc["receipt"],
        "previous_parent_id": seed.bundle_id,
        "seed_bundle_id": child.bundle_id,
        "source_projection_sha256": content_hash(feedback.as_json()),
        "prospective_measurement_profile": PROFILE,
    }
    protocol.update(
        historical_bootstrap=descriptor,
        measurement_profile=PROFILE,
        allocation_extension=extension,
    )
    binding = {"next_round": 4, "parent_id": child.bundle_id, "complementary_ids": []}
    selection = exploratory_selection(
        feedback,
        registration={"member_bindings": own},
        binding=binding,
        protocol=protocol,
        parents=[child.as_json()],
    )
    packet.update(
        round=4,
        parent_bundle_id=child.bundle_id,
        parent_policy=child.as_json(),
        seed_bundle_id=child.bundle_id,
        protocol_sha256=content_hash(protocol),
        selection=selection,
        allocation_extension_sha256=content_hash(extension),
        model_version=extension["model_version"],
        input_token_cap=extension["input_token_cap"],
        output_token_cap=extension["output_token_cap"],
    )
    return protocol, packet, feedback.as_json(), binding, own


def test_historical_bootstrap_keeps_original_evidence_and_no_frontier(tmp_path):
    protocol, packet, original, _, _ = bootstrap(tmp_path)
    require_exploratory_packet(packet, protocol=protocol)
    require_exploratory_packet(packet)
    assert packet["feedback"] == original
    s = packet["selection"]
    assert s["schema"] == "saea-historical-seed-selection-v1"
    assert (
        "measurement_profile" not in s
        and "frontier" not in s
        and "measurements" not in s
    )
    assert s["member_bindings"]["L-parent"]["bundle_id"] != s["active_ids"][0]
    assert s["historical_bootstrap"]["prospective_measurement_profile"] == PROFILE
    assert s["formal_adoption"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "feedback-timing",
        "profile-mismatch",
        "fake-frontier",
        "blind",
        "new-parent",
        "relabel-observed",
        "missing-protocol-authority",
        "receipt",
        "future-round",
        "projection",
        "extra-candidate",
    ],
)
def test_bootstrap_cannot_relax_standard_measurement_or_identity_guards(
    tmp_path, fault
):
    protocol, packet, _, _, _ = bootstrap(tmp_path)
    s = packet["selection"]
    if fault == "feedback-timing":
        packet["feedback"]["measurement_profile"] = PROFILE
    elif fault == "profile-mismatch":
        protocol["measurement_profile"] = {**PROFILE, "queue_depth": 8}
    elif fault == "fake-frontier":
        s["frontier"] = []
    elif fault == "blind":
        packet["branch"] = "B"
    elif fault == "new-parent":
        packet["parent_policy"]["role_text"]["solver"] = "Changed policy."
    elif fault == "relabel-observed":
        s["member_bindings"]["L-parent"]["bundle_id"] = packet["parent_bundle_id"]
    elif fault == "missing-protocol-authority":
        protocol.pop("historical_bootstrap")
    elif fault == "receipt":
        s["historical_bootstrap"]["seed_transition"]["sha256"] = "a" * 64
    elif fault == "future-round":
        s["historical_bootstrap"]["round"] = 5
    elif fault == "projection":
        s["historical_bootstrap"]["source_projection_sha256"] = "a" * 64
    else:
        packet["complementary_policies"] = [packet["parent_policy"]]
    # Refresh ordinary integrity hashes so semantic checks must reject the mutation.
    s["learning_feedback_sha256"] = content_hash(packet["feedback"])
    packet["protocol_sha256"] = content_hash(protocol)
    s["protocol_sha256"] = packet["protocol_sha256"]
    s["selection_sha256"] = content_hash(
        {k: v for k, v in s.items() if k != "selection_sha256"}
    )
    with pytest.raises(PolicyError):
        require_exploratory_packet(packet, protocol=protocol)


def test_unregistered_profile_mismatch_still_refuses(tmp_path):
    protocol, packet = learning_fixture(tmp_path)
    protocol["measurement_profile"] = PROFILE
    with pytest.raises(PolicyError, match="measurement"):
        require_exploratory_packet(packet, protocol=protocol)


@pytest.mark.parametrize("profile", ["full-index-v1", "typed-coherent-feedback-v1"])
def test_bootstrap_is_visible_before_any_optional_evidence_read(tmp_path, profile):
    from test_system_proposer_views import learning_fixture as view_fixture
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule

    _, bootstrap_packet, _, _, _ = bootstrap(tmp_path / "bootstrap")
    (tmp_path / "view").mkdir()
    packet, roots = view_fixture(tmp_path / "view")
    capsule = ProposerCapsule.from_packet(packet, roots=roots, view_profile=profile)
    original = copy.deepcopy(packet)
    packet["selection"] = bootstrap_packet["selection"]
    view_capsule = ProposerCapsule(packet, capsule._artifacts, view_profile=profile)
    view = view_capsule.initial_input()
    notice = view["historical_bootstrap"]
    binding = packet["selection"]["historical_bootstrap"]
    assert notice["binding"] == binding
    assert "not measurements of the new seed" in notice["interpretation"]
    assert "latency" in notice["interpretation"]
    assert notice["original_utility_reference_preserved"] is True
    assert packet["feedback"] == original["feedback"]
    assert "historical_bootstrap" not in capsule.initial_input()


def test_blind_initial_view_contains_no_historical_bootstrap(tmp_path):
    from test_system_proposer_capsule import fixture
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule

    packet, roots = fixture(tmp_path)
    for profile in ("full-index-v1", "typed-coherent-feedback-v1"):
        view = ProposerCapsule.from_packet(packet, roots=roots, view_profile=profile).initial_input()
        assert "historical_bootstrap" not in view
