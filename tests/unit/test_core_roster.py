"""``core.roster``: the one carrier-agnostic roster freezer (C4d).

Also proves the three historical split-identity-hash implementations
(``data.splits.split_identity_hash`` -- canonical, ``reproduction.sampling
.split_identity_hash``, and the inline ASCII sha256 call in
``analysis.a2t_fresh_agentloop_roster.build_receipt``) compute the SAME
digest for the same sorted, ASCII, carrier-prefixed id list.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.roster import (
    RECEIPT_SCHEMA,
    RosterError,
    RosterItem,
    as_probe_sample_receipt,
    canonical_receipt_bytes,
    freeze_roster,
    hash_matches_legacy_receipt,
    mixture_quotas,
    read_roster,
    verify_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.audio2tool import audio2tool_receipts
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.reproduction.sampling import (
    split_identity_hash as sampling_split_identity_hash,
)


# ---------------------------------------------------------------------------
# The three historical hash implementations agree.
# ---------------------------------------------------------------------------


def _legacy_inline_hash(keys: list[str]) -> str:
    """The exact inline call in ``a2t_fresh_agentloop_roster.build_receipt``."""

    return hashlib.sha256("\n".join(sorted(keys)).encode("ascii")).hexdigest()


def test_three_hash_implementations_agree_on_the_same_input():
    keys = [
        "audio2tool:tier1_direct:000074",
        "audio2tool:tier1_direct:000077",
        "audio2tool:tier2_parametric:000012",
    ]
    canonical = split_identity_hash(keys)
    sampling = sampling_split_identity_hash(keys)
    inline = _legacy_inline_hash(keys)
    assert canonical == sampling == inline


def test_sampling_hash_additionally_refuses_duplicates_but_agrees_otherwise():
    keys = ["a/1", "b/2", "c/3"]
    assert sampling_split_identity_hash(keys) == split_identity_hash(keys)
    with pytest.raises(ValueError, match="duplicate"):
        sampling_split_identity_hash(["a/1", "a/1"])
    # the canonical function has no such guard -- a duplicate id is simply
    # joined twice, changing the hash rather than raising -- which is
    # exactly why freeze_roster below enforces uniqueness itself before
    # ever calling split_identity_hash.
    assert split_identity_hash(["a/1", "a/1"]) != split_identity_hash(["a/1"])


# ---------------------------------------------------------------------------
# freeze_roster: happy path, determinism, and receipt shape.
# ---------------------------------------------------------------------------


def _candidates(n_per_tier: int = 5) -> list[RosterItem]:
    items = []
    for tier in ("tier1", "tier2"):
        for index in range(n_per_tier):
            items.append(
                RosterItem(
                    sample_id=f"{tier}:{index:03d}",
                    stratum=tier,
                    extra={"audio_seconds": float(index)},
                )
            )
    return items


def test_freeze_roster_basic_shape_and_hash():
    receipt = freeze_roster(
        carrier_lock_key="audio2tool-test",
        candidates=_candidates(),
        per_stratum=2,
        seed=1,
        split_role="discovery",
        roster_id="TEST-ROSTER",
    )
    assert receipt["schema"] == RECEIPT_SCHEMA
    assert receipt["roster_id"] == "TEST-ROSTER"
    assert receipt["carrier_lock_key"] == "audio2tool-test"
    assert receipt["split_role"] == "discovery"
    assert receipt["seed"] == 1
    assert receipt["per_stratum"] == {"tier1": 2, "tier2": 2}
    assert receipt["strata_counts"] == {"tier1": 2, "tier2": 2}
    assert receipt["excluded_count"] == 0
    ids = [item["sample_id"] for item in receipt["items"]]
    assert ids == sorted(ids)
    assert len(ids) == 4
    assert receipt["split_identity_hash"] == split_identity_hash(
        prefixed("audio2tool-test", ids)
    )
    # extra fields are flattened onto each item
    assert all("audio_seconds" in item for item in receipt["items"])


def test_freeze_roster_per_stratum_mapping():
    receipt = freeze_roster(
        carrier_lock_key="audio2tool-test",
        candidates=_candidates(),
        per_stratum={"tier1": 1, "tier2": 3},
        seed=1,
        split_role="discovery",
        roster_id="TEST-ROSTER",
    )
    assert receipt["strata_counts"] == {"tier1": 1, "tier2": 3}


def test_freeze_roster_same_seed_gives_the_same_receipt():
    kwargs = dict(
        carrier_lock_key="audio2tool-test",
        candidates=_candidates(),
        per_stratum=2,
        split_role="discovery",
        roster_id="TEST-ROSTER",
    )
    receipt_a = freeze_roster(seed=7, **kwargs)
    receipt_b = freeze_roster(seed=7, **kwargs)
    assert receipt_a == receipt_b


def test_freeze_roster_different_seed_gives_a_different_draw():
    kwargs = dict(
        carrier_lock_key="audio2tool-test",
        candidates=_candidates(n_per_tier=8),
        per_stratum=2,
        split_role="discovery",
        roster_id="TEST-ROSTER",
    )
    receipt_a = freeze_roster(seed=1, **kwargs)
    receipt_b = freeze_roster(seed=2, **kwargs)
    assert receipt_a["items"] != receipt_b["items"]
    assert receipt_a["split_identity_hash"] != receipt_b["split_identity_hash"]


# ---------------------------------------------------------------------------
# Refusals.
# ---------------------------------------------------------------------------


def test_freeze_roster_refuses_a_short_stratum():
    with pytest.raises(RosterError, match="cannot fill its quota"):
        freeze_roster(
            carrier_lock_key="audio2tool-test",
            candidates=_candidates(n_per_tier=1),
            per_stratum=2,
            seed=1,
            split_role="discovery",
            roster_id="TEST-ROSTER",
        )


def test_freeze_roster_refuses_when_exclusion_starves_a_stratum():
    candidates = _candidates(n_per_tier=2)
    excluded = {"tier1:000"}
    with pytest.raises(RosterError, match="cannot fill its quota"):
        freeze_roster(
            carrier_lock_key="audio2tool-test",
            candidates=candidates,
            per_stratum=2,
            seed=1,
            split_role="discovery",
            roster_id="TEST-ROSTER",
            exclude_sample_ids=excluded,
        )


def test_freeze_roster_excluded_sample_id_never_appears_in_the_output():
    candidates = _candidates(n_per_tier=5)
    excluded = {"tier1:000"}
    receipt = freeze_roster(
        carrier_lock_key="audio2tool-test",
        candidates=candidates,
        per_stratum=2,
        seed=1,
        split_role="discovery",
        roster_id="TEST-ROSTER",
        exclude_sample_ids=excluded,
    )
    ids = {item["sample_id"] for item in receipt["items"]}
    assert ids.isdisjoint(excluded)
    assert receipt["excluded_count"] == 1


def test_freeze_roster_refuses_when_group_uniqueness_starves_a_stratum():
    # Both candidates in tier1 share group "twin"; quota 2 can never be met
    # while keeping at most one member of a group.
    candidates = [
        RosterItem(sample_id="tier1:000000", stratum="tier1"),
        RosterItem(sample_id="tier1:000001", stratum="tier1"),
    ]
    groups = {"tier1:000000": "twin", "tier1:000001": "twin"}
    with pytest.raises(RosterError, match="cannot fill its quota"):
        freeze_roster(
            carrier_lock_key="audio2tool-test",
            candidates=candidates,
            per_stratum=2,
            seed=1,
            split_role="discovery",
            roster_id="TEST-ROSTER",
            exclude_groups=groups,
        )


def test_freeze_roster_never_selects_two_members_of_the_same_group():
    candidates = [
        RosterItem(sample_id="tier1:000000", stratum="tier1"),
        RosterItem(sample_id="tier1:000001", stratum="tier1"),
        RosterItem(sample_id="tier1:000002", stratum="tier1"),
    ]
    groups = {"tier1:000000": "twin", "tier1:000001": "twin"}
    for seed in range(10):
        receipt = freeze_roster(
            carrier_lock_key="audio2tool-test",
            candidates=candidates,
            per_stratum=2,
            seed=seed,
            split_role="discovery",
            roster_id="TEST-ROSTER",
            exclude_groups=groups,
        )
        ids = {item["sample_id"] for item in receipt["items"]}
        assert not {"tier1:000000", "tier1:000001"}.issubset(ids)
        assert len(ids) == 2


def test_freeze_roster_group_exclusion_propagates_from_an_excluded_id():
    # tier1:000000 is excluded directly; tier1:000001 shares its group and
    # must be excluded too, even though it is not itself in exclude_sample_ids.
    candidates = [
        RosterItem(sample_id="tier1:000000", stratum="tier1"),
        RosterItem(sample_id="tier1:000001", stratum="tier1"),
    ]
    groups = {"tier1:000000": "twin", "tier1:000001": "twin"}
    with pytest.raises(RosterError, match="cannot fill its quota"):
        freeze_roster(
            carrier_lock_key="audio2tool-test",
            candidates=candidates,
            per_stratum=1,
            seed=1,
            split_role="discovery",
            roster_id="TEST-ROSTER",
            exclude_sample_ids={"tier1:000000"},
            exclude_groups=groups,
        )


def test_freeze_roster_refuses_empty_candidates():
    with pytest.raises(RosterError, match="non-empty"):
        freeze_roster(
            carrier_lock_key="audio2tool-test",
            candidates=[],
            per_stratum=1,
            seed=1,
            split_role="discovery",
            roster_id="TEST-ROSTER",
        )


def test_freeze_roster_refuses_duplicate_candidate_sample_ids():
    candidates = [
        RosterItem(sample_id="tier1:000000", stratum="tier1"),
        RosterItem(sample_id="tier1:000000", stratum="tier1"),
    ]
    with pytest.raises(RosterError, match="duplicate"):
        freeze_roster(
            carrier_lock_key="audio2tool-test",
            candidates=candidates,
            per_stratum=1,
            seed=1,
            split_role="discovery",
            roster_id="TEST-ROSTER",
        )


# ---------------------------------------------------------------------------
# verify_roster / write_roster / read_roster.
# ---------------------------------------------------------------------------


def _valid_receipt():
    return freeze_roster(
        carrier_lock_key="audio2tool-test",
        candidates=_candidates(),
        per_stratum=2,
        seed=3,
        split_role="discovery",
        roster_id="TEST-ROSTER",
    )


def test_verify_roster_accepts_its_own_output():
    receipt = _valid_receipt()
    assert verify_roster(receipt) == receipt["split_identity_hash"]


def test_verify_roster_fails_closed_on_a_tampered_id():
    receipt = dict(_valid_receipt())
    items = [dict(item) for item in receipt["items"]]
    items[0]["sample_id"] = "tier1:999999"
    receipt = {**receipt, "items": items}
    with pytest.raises(RosterError, match="mismatch"):
        verify_roster(receipt)


def test_verify_roster_fails_closed_on_a_tampered_hash():
    receipt = dict(_valid_receipt())
    receipt["split_identity_hash"] = "0" * 64
    with pytest.raises(RosterError, match="mismatch"):
        verify_roster(receipt)


def test_write_roster_then_read_roster_round_trips(tmp_path):
    receipt = _valid_receipt()
    path = tmp_path / "roster.json"
    write_roster(receipt, path)
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == receipt
    assert path.read_text(encoding="utf-8").endswith("\n")
    read_back = read_roster(path)
    assert read_back == receipt


def test_write_roster_refuses_to_overwrite(tmp_path):
    receipt = _valid_receipt()
    path = tmp_path / "roster.json"
    write_roster(receipt, path)
    with pytest.raises(RosterError, match="refusing to overwrite"):
        write_roster(receipt, path)


def test_read_roster_fails_closed_on_a_tampered_file(tmp_path):
    receipt = _valid_receipt()
    path = tmp_path / "roster.json"
    write_roster(receipt, path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["items"][0]["sample_id"] = "tier1:999999"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(RosterError, match="mismatch"):
        read_roster(path)


# ---------------------------------------------------------------------------
# hash_matches_legacy_receipt.
# ---------------------------------------------------------------------------


def test_hash_matches_legacy_receipt_true_on_the_key_field_convention(tmp_path):
    keys = ["audio2tool:tier1_direct:000074", "audio2tool:tier1_direct:000077"]
    document = {
        "items": [{"key": key, "sample_id": key.split(":", 1)[1]} for key in keys],
        "split_identity_hash": split_identity_hash(keys),
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert hash_matches_legacy_receipt(path) is True


def test_hash_matches_legacy_receipt_false_on_a_tampered_hash(tmp_path):
    keys = ["audio2tool:tier1_direct:000074", "audio2tool:tier1_direct:000077"]
    document = {
        "items": [{"key": key} for key in keys],
        "split_identity_hash": "0" * 64,
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert hash_matches_legacy_receipt(path) is False


def test_hash_matches_legacy_receipt_false_on_a_different_prefixing_convention(tmp_path):
    # The canonical_family_secondary receipt hashes f"audio2tool/{sample_id}",
    # NOT item["key"] -- this function checks the key-field convention only,
    # so it correctly reports False rather than silently agreeing.
    sample_ids = ["tier1_direct:000074", "tier1_direct:000077"]
    document = {
        "items": [
            {"key": f"audio2tool:{sid}", "sample_id": sid} for sid in sample_ids
        ],
        "split_identity_hash": split_identity_hash(
            [f"audio2tool/{sid}" for sid in sample_ids]
        ),
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert hash_matches_legacy_receipt(path) is False


# ---------------------------------------------------------------------------
# roster_role and the legacy probe-sample view (E2.3).
# ---------------------------------------------------------------------------


def _a2t_candidates(n_per_tier: int = 4) -> list[RosterItem]:
    """Audio2Tool-shaped candidates: the ``extra`` fields the legacy
    probe-sample shape needs (``id``, ``key``, ``tier``, ``query_idx``)."""

    items: list[RosterItem] = []
    item_id = 0
    for tier in ("tier1_direct", "tier2_parametric"):
        for index in range(n_per_tier):
            item_id += 1
            sample_id = f"{tier}:{item_id:06d}"
            items.append(
                RosterItem(
                    sample_id=sample_id,
                    stratum=tier,
                    extra={
                        "id": item_id,
                        "key": f"audio2tool:{sample_id}",
                        "query_idx": 500 + index,
                        "tier": tier,
                    },
                )
            )
    return items


def _a2t_roster(roster_role: str = "construction") -> dict:
    return freeze_roster(
        carrier_lock_key="audio2tool",
        candidates=_a2t_candidates(),
        per_stratum=3,
        seed=11,
        split_role="discovery",
        roster_id="A2T-TEST-ROSTER",
        roster_role=roster_role,
    )


def test_roster_role_defaults_to_evaluation_and_lands_in_the_receipt():
    receipt = freeze_roster(
        carrier_lock_key="audio2tool-test",
        candidates=_candidates(),
        per_stratum=2,
        seed=1,
        split_role="discovery",
        roster_id="TEST-ROSTER",
    )
    assert receipt["roster_role"] == "evaluation"
    assert _a2t_roster("construction")["roster_role"] == "construction"


def test_freeze_roster_refuses_an_unknown_roster_role():
    with pytest.raises(RosterError, match="roster_role"):
        freeze_roster(
            carrier_lock_key="audio2tool-test",
            candidates=_candidates(),
            per_stratum=2,
            seed=1,
            split_role="discovery",
            roster_id="TEST-ROSTER",
            roster_role="calibration",
        )


def test_verify_roster_checks_the_role_and_tolerates_a_legacy_receipt():
    receipt = dict(_a2t_roster())
    assert verify_roster(receipt) == receipt["split_identity_hash"]
    receipt.pop("roster_role")
    assert verify_roster(receipt) == receipt["split_identity_hash"]
    receipt["roster_role"] = "something-else"
    with pytest.raises(RosterError, match="roster_role"):
        verify_roster(receipt)


def test_probe_sample_view_matches_the_legacy_hash_convention(tmp_path):
    roster = _a2t_roster()
    view = as_probe_sample_receipt(
        roster, carrier="audio2tool", design="construction role; gold may be read"
    )

    # The roster receipt's own hash is the core.roster convention...
    ids = [str(item["sample_id"]) for item in roster["items"]]
    assert roster["split_identity_hash"] == split_identity_hash(
        prefixed("audio2tool", ids)
    )
    # ...and the view's hash is the legacy probe-receipt convention, over the
    # already carrier-prefixed keys. The two are different digests of the
    # same identities, which is exactly why both documents exist.
    assert view["split_identity_hash"] == split_identity_hash(
        [f"audio2tool:{sample_id}" for sample_id in ids]
    )
    assert view["split_identity_hash"] != roster["split_identity_hash"]
    assert view["roster_split_identity_hash"] == roster["split_identity_hash"]

    path = tmp_path / "view.json"
    path.write_text(
        json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    assert hash_matches_legacy_receipt(path) is True


def test_probe_sample_view_carries_the_roles_and_its_parent_hash():
    roster = _a2t_roster()
    view = as_probe_sample_receipt(
        roster, carrier="audio2tool", design="construction role; gold may be read"
    )
    assert view["split_role"] == "discovery"
    assert view["roster_role"] == "construction"
    assert view["derived_from_roster_id"] == "A2T-TEST-ROSTER"
    assert view["derived_from_roster_sha256"] == hashlib.sha256(
        canonical_receipt_bytes(roster)
    ).hexdigest()
    assert view["n_items"] == len(roster["items"])
    assert {item["key"] for item in view["items"]} == {
        f"audio2tool:{item['sample_id']}" for item in roster["items"]
    }
    # identity fields only: the roster's own bookkeeping never leaks into the
    # loadable view.
    assert not any("sample_id" in item or "stratum" in item for item in view["items"])


def test_the_probe_sample_view_is_loadable_by_the_audio2tool_reader(tmp_path):
    """The point of the view: ``data.audio2tool`` must accept it. That reader
    verifies split_role, per-item id/tier/key agreement and the legacy hash,
    and fails closed on anything it cannot verify -- which is why a
    ``saea-roster-receipt-v1`` file must never be dropped into that
    directory."""

    view = as_probe_sample_receipt(
        _a2t_roster(), carrier="audio2tool", design="construction role"
    )
    probes = tmp_path / "docs" / "receipts" / "probe-samples"
    probes.mkdir(parents=True)
    (probes / "a2t-test-roster.json").write_text(
        json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    loaded = audio2tool_receipts(tmp_path)
    assert set(loaded) == {"a2t-test-roster"}
    assert len(loaded["a2t-test-roster"]["items"]) == 6


def test_probe_sample_view_refuses_a_roster_without_the_key_extra():
    roster = freeze_roster(
        carrier_lock_key="audio2tool",
        candidates=_candidates(),
        per_stratum=2,
        seed=1,
        split_role="discovery",
        roster_id="NO-KEYS",
    )
    with pytest.raises(RosterError, match="carries no 'key' extra"):
        as_probe_sample_receipt(roster, carrier="audio2tool", design="x")


def test_probe_sample_view_refuses_a_key_that_disagrees_with_its_sample_id():
    roster = dict(_a2t_roster())
    items = [dict(item) for item in roster["items"]]
    items[0]["key"] = "audio2tool:tier1_direct:999999"
    roster["items"] = items
    with pytest.raises(RosterError, match="disagrees with the carrier-prefixed"):
        as_probe_sample_receipt(roster, carrier="audio2tool", design="x")


# ---------------------------------------------------------------------------
# mixture_quotas: reproduce a reference mixture on a depleted pool (MF-3)
# ---------------------------------------------------------------------------


def test_mixture_quotas_matches_the_reference_mixture_when_capacity_allows():
    quotas = mixture_quotas(
        100, {"a": 50, "b": 30, "c": 20}, {"a": 500, "b": 500, "c": 500}
    )
    assert quotas == {"a": 50, "b": 30, "c": 20}


def test_mixture_quotas_water_fills_a_saturated_stratum():
    """``c`` wants 20 of 100 but holds 4, so it takes 4 and the 16-seat
    shortfall is redistributed across ``a`` and ``b`` at 50:30."""

    quotas = mixture_quotas(100, {"a": 50, "b": 30, "c": 20}, {"a": 500, "b": 500, "c": 4})
    assert quotas["c"] == 4
    assert sum(quotas.values()) == 100
    assert quotas["a"] == 60 and quotas["b"] == 36


def test_mixture_quotas_gives_an_empty_stratum_a_zero_quota():
    quotas = mixture_quotas(10, {"a": 1, "b": 1}, {"a": 10, "b": 0})
    assert quotas == {"a": 10, "b": 0}


def test_mixture_quotas_is_order_independent_and_deterministic():
    weights = {"c": 20, "a": 50, "b": 30}
    capacities = {"b": 7, "c": 500, "a": 500}
    first = mixture_quotas(97, weights, capacities)
    second = mixture_quotas(97, dict(reversed(list(weights.items()))), capacities)
    assert first == second
    assert sum(first.values()) == 97


def test_mixture_quotas_refuses_a_total_above_the_summed_capacity():
    with pytest.raises(RosterError, match="exceeds the summed capacity"):
        mixture_quotas(10, {"a": 1}, {"a": 9})


def test_mixture_quotas_refuses_when_the_surviving_strata_carry_no_weight():
    with pytest.raises(RosterError, match="zero reference weight"):
        mixture_quotas(5, {"a": 1, "b": 0}, {"a": 0, "b": 50})


def test_freeze_roster_accepts_a_zero_quota_for_a_drained_stratum():
    """The SLURP DEV-500-B case: five devel scenarios have no surviving
    candidate after the DEV ladder, and the honest quota for them is zero."""

    receipt = freeze_roster(
        carrier_lock_key="slurp-test",
        candidates=_candidates(),
        per_stratum={"tier1": 3, "tier2": 0},
        seed=1,
        split_role="dev",
        roster_id="TEST-ZERO",
    )
    assert receipt["per_stratum"] == {"tier1": 3, "tier2": 0}
    assert receipt["strata_counts"] == {"tier1": 3}
    assert len(receipt["items"]) == 3


def test_freeze_roster_still_refuses_an_all_zero_quota_mapping():
    with pytest.raises(RosterError, match="sum to zero"):
        freeze_roster(
            carrier_lock_key="slurp-test",
            candidates=_candidates(),
            per_stratum={"tier1": 0, "tier2": 0},
            seed=1,
            split_role="dev",
            roster_id="TEST-EMPTY",
        )


def test_freeze_roster_still_refuses_a_negative_quota():
    with pytest.raises(RosterError, match="non-negative integer"):
        freeze_roster(
            carrier_lock_key="slurp-test",
            candidates=_candidates(),
            per_stratum={"tier1": -1, "tier2": 3},
            seed=1,
            split_role="dev",
            roster_id="TEST-NEGATIVE",
        )
