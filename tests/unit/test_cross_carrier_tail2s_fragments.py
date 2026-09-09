"""Model-free coverage for the cross-carrier ``@ts2`` fragments and wire check.

Reads committed config fragments and receipts only. No data root, no model,
network, tokenizer or scorer contact, and no gold, evaluation query or score of
any carrier is opened.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FRAGMENTS = REPO / "scripts/build_cross_carrier_tail2s_fragments.py"
WIRE = REPO / "docs/checks/speech-aware-evidence-acquisition/2026-09-07-cross-carrier-tail2s-wire-check/wire-check.json"


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _module(FRAGMENTS, "cross_carrier_ts2_fragments_test")


def _json(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The emitted fragments reproduce
# ---------------------------------------------------------------------------


def test_emitting_twice_reproduces_every_committed_fragment() -> None:
    """The generator is the authority: what is committed is what it emits."""

    for relpath, digest in MOD.emit(write=False):
        committed = hashlib.sha256((REPO / relpath).read_bytes()).hexdigest()
        assert committed == digest, relpath


def test_smoke_subsets_are_exactly_four_distinct_ids() -> None:
    for relpath in (
        "configs/dataset/slurp-speech-native-dev1000-tail2s-smoke4.json",
        "configs/dataset/audio2tool-calibration-400-tail2s-smoke4.json",
    ):
        fragment = _json(relpath)
        count = fragment.get("count", fragment.get("a2t_calibration_count"))
        assert count == MOD.SMOKE_SIZE, relpath


def test_smoke_ids_top_up_when_a_view_has_one_stratum() -> None:
    view = {
        "items": [
            {"sample_id": f"x{index:02d}", "stratum": "only"} for index in range(10)
        ]
    }
    picked = MOD.smoke_ids(view)
    assert len(picked) == MOD.SMOKE_SIZE == len(set(picked))
    assert picked == sorted(picked)


def test_smoke_ids_take_one_per_stratum_when_there_are_enough() -> None:
    view = {
        "items": [
            {"sample_id": f"{name}-{index}", "stratum": name}
            for name in ("a", "b", "c", "d", "e")
            for index in range(3)
        ]
    }
    picked = MOD.smoke_ids(view)
    assert len(picked) == MOD.SMOKE_SIZE
    assert len({identifier.split("-")[0] for identifier in picked}) == MOD.SMOKE_SIZE


# ---------------------------------------------------------------------------
# What the fragments must say
# ---------------------------------------------------------------------------


def test_slurp_view_declares_the_supplement_the_sealed_view_could_omit() -> None:
    """The @ts2 files are NEW media outside the base D1 SLURP closure."""

    variant = _json("configs/dataset/slurp-speech-native-dev1000-tail2s.json")
    sealed = _json("configs/dataset/slurp-speech-native-dev1000.json")
    assert sealed["d1_media_supplement"] is None
    assert variant["d1_media_supplement"] == "receipts/artifacts/d1-slurp-dev1000-tail2s.json"
    supplement = _json("docs/" + str(variant["d1_media_supplement"]))
    assert variant["d1_media_supplement_sha256"] == hashlib.sha256(
        (REPO / "docs" / str(variant["d1_media_supplement"])).read_bytes()
    ).hexdigest()
    assert supplement["count"] == variant["count"] == 1000


def test_slurp_variant_identity_differs_from_the_sealed_view() -> None:
    variant = _json("configs/dataset/slurp-speech-native-dev1000-tail2s.json")
    sealed = _json("configs/dataset/slurp-speech-native-dev1000.json")
    assert variant["split_identity_hash"] != sealed["split_identity_hash"]
    assert variant["split_name"] == "DEV-1000-TAIL2S"
    assert variant["split_role"] == sealed["split_role"] == "dev"
    assert all(str(item["sample_id"]).endswith("@ts2") for item in variant["items"])
    assert all(str(item["packet_id"]).endswith("@ts2") for item in variant["items"])


def test_slurp_model_fragment_differs_from_the_comparator_only_in_the_packet_root() -> None:
    """The single-factor claim, checked field by field rather than asserted."""

    variant = _json(
        "configs/model/q4km-mmproj-free-speech-native-np8-ts2-packets-max64.json"
    )
    sealed = _json(
        "configs/model/q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64.json"
    )
    differing = {
        key
        for key in set(variant) | set(sealed)
        if variant.get(key) != sealed.get(key)
    }
    assert differing == {"speech_feature_root", "server_env", "variant_basis"}
    assert variant["server_args"] == sealed["server_args"]
    assert variant["decoding_params"] == sealed["decoding_params"]
    assert variant["prompt_order"] == sealed["prompt_order"]
    assert variant["runtime_receipt"] == sealed["runtime_receipt"]
    # server_env differs in exactly one key, and the decoder pin is carried over.
    assert set(variant["server_env"]) == set(sealed["server_env"])
    assert (
        variant["server_env"]["LLAMA_SPEECH_DECODER_SHA256"]
        == sealed["server_env"]["LLAMA_SPEECH_DECODER_SHA256"]
    )
    assert variant["server_env"]["LLAMA_SPEECH_FEATURE_ROOT"] == variant[
        "speech_feature_root"
    ]
    assert variant["speech_feature_root"] != sealed["speech_feature_root"]


def test_a2t_fragment_declares_the_24khz_rate_and_the_derived_root() -> None:
    fragment = _json("configs/dataset/audio2tool-calibration-400-tail2s.json")
    assert fragment["a2t_calibration_sample_rate_hz"] == 24000
    assert (
        fragment["a2t_calibration_derived_subdir"]
        == "derived/a2t-calibration-400-tail2s-v1"
    )
    sealed = _json("configs/dataset/audio2tool-calibration-400.json")
    assert (
        fragment["a2t_calibration_split_identity_hash"]
        != sealed["a2t_calibration_split_identity_hash"]
    )
    assert (
        fragment["a2t_calibration_flight_split_identity_hash"]
        != sealed["a2t_calibration_flight_split_identity_hash"]
    )
    assert fragment["a2t_calibration_count"] == 400


@pytest.mark.parametrize(
    "relpath",
    [
        "configs/experiment/slurp-dev1000-closed-list-tail2s-v1.json",
        "configs/experiment/slurp-dev1000-closed-list-tail2s-smoke-4-v1.json",
        "configs/experiment/a2t-official-protocol-tail2s-400-v1.json",
        "configs/experiment/a2t-official-protocol-tail2s-400-smoke-v1.json",
    ],
)
def test_every_experiment_fragment_authorizes_nothing_and_names_its_blockers(
    relpath: str,
) -> None:
    fragment = _json(relpath)
    assert "nothing" in str(fragment["authorizes"]).lower()
    assert fragment["preregistration"] == (
        "docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md"
    )
    assert (REPO / fragment["preregistration"]).is_file()
    blockers = fragment["open_preconditions"]
    assert blockers and all(isinstance(entry, str) and entry for entry in blockers)
    assert any("SCORER ID RAIL" in entry for entry in blockers)


def test_smoke_fragments_pin_their_rows_in_the_registered_fragment() -> None:
    """A smoke can never quietly fly four rows its exposure row does not name."""

    for relpath in (
        "configs/experiment/slurp-dev1000-closed-list-tail2s-smoke-4-v1.json",
        "configs/experiment/a2t-official-protocol-tail2s-400-smoke-v1.json",
    ):
        fragment = _json(relpath)
        populations = fragment["populations"]
        assert len(populations) == 1
        ids = populations[0]["ids"]
        assert len(ids) == MOD.SMOKE_SIZE == len(set(ids))
        assert all(str(identifier).endswith("@ts2") for identifier in ids)
        assert populations[0]["dataset_fragment"] == fragment["cells"][0][
            "dataset_fragment"
        ]


def test_no_earnings21_fragment_was_emitted() -> None:
    """Earnings-21 deliberately has no cell; see the preregistration's section 6.3."""

    emitted = {relpath for relpath, _ in MOD.emit(write=False)}
    assert not any("e21" in relpath or "earnings21" in relpath for relpath in emitted)


# ---------------------------------------------------------------------------
# The runner seam
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "runner,key",
    [
        ("scripts/flights/run_calibration_cell.py", "a2t_calibration_derived_subdir"),
        ("scripts/flights/run_slurp_closed_list_cell.py", "derived_media_subdir"),
    ],
)
def test_derived_root_seam_is_inert_without_the_key(runner: str, key: str) -> None:
    """Every fragment that existed before the key keeps the carrier root."""

    source = (REPO / runner).read_text(encoding="utf-8")
    assert "carrier_root_resolver" in source
    assert key in source
    # The resolver is only added when the key is present.
    assert "return {}" in source


@pytest.mark.parametrize(
    "runner",
    [
        "scripts/flights/run_calibration_cell.py",
        "scripts/flights/run_slurp_closed_list_cell.py",
        "scripts/flights/run_e22_esb_cell.py",
    ],
)
def test_flight_runners_resolve_their_own_checkout(runner: str) -> None:
    """A worktree must dry-run against its OWN configs, not the main checkout's."""

    source = (REPO / runner).read_text(encoding="utf-8")
    assert "REPO = Path(__file__).resolve().parents[2]" in source
    assert "/mnt/d/chao_workspace/exploring-l4-intelligence" not in source


def test_only_the_declared_configs_name_a_derived_root() -> None:
    """No pre-existing fragment silently picks the new seam up."""

    a2t = [
        path
        for path in (REPO / "configs/dataset").glob("*.json")
        if "a2t_calibration_derived_subdir" in path.read_text(encoding="utf-8")
    ]
    slurp = [
        path
        for path in (REPO / "configs/dataset").glob("*.json")
        if '"derived_media_subdir"' in path.read_text(encoding="utf-8")
    ]
    # The allowlist is explicit on purpose: a fragment reaches this set only by
    # being named here. The four input-rate fragments (2026-09-07,
    # scripts/build_a2t_input_rate_16k_fragments.py) declare the same seam
    # deliberately, each against its own derived root, so they are added rather
    # than the assertion being loosened.
    assert {path.name for path in a2t} == {
        "audio2tool-calibration-400-tail2s.json",
        "audio2tool-calibration-400-tail2s-smoke4.json",
        "audio2tool-calibration-400-16k.json",
        "audio2tool-calibration-400-16k-smoke4.json",
        "audio2tool-calibration-400-16k-tail2s.json",
        "audio2tool-calibration-400-16k-tail2s-smoke4.json",
    }
    assert {path.name for path in slurp} == {
        "slurp-speech-native-dev1000-tail2s.json",
        "slurp-speech-native-dev1000-tail2s-smoke4.json",
    }


# ---------------------------------------------------------------------------
# The wire-check receipt
# ---------------------------------------------------------------------------


def test_wire_check_receipt_records_zero_contacts_on_every_cell() -> None:
    receipt = json.loads(WIRE.read_text(encoding="utf-8"))
    assert receipt["schema"] == "saea-cross-carrier-ts2-wire-check-v1"
    for field in (
        "frozen_core",
        "servers_started",
        "sockets_opened",
        "gpu_hours",
        "paid_api_spend",
    ):
        assert receipt["contacts"][field] == 0, field
    assert len(receipt["cells"]) == 4
    for row in receipt["cells"]:
        for mode in ("preflight", "wire_check"):
            assert row[mode]["model_contacts"] == 0
            assert row[mode]["opened_a_socket"] is False


def test_every_wire_check_stop_is_one_of_the_named_preconditions() -> None:
    """No surprises: each cell stops where the preregistration says it stops.

    UPDATED 2026-09-07, when the gold-id rail of section 6.2 landed: both
    Audio2Tool cells used to stop at ``a2t-gold-id-rail-missing`` and now run
    the whole request path.

    UPDATED AGAIN 2026-09-09. SLURP used to stop at
    ``slurp-packet-root-missing``, and the condition this test's own comment
    named as the release -- "the encode of section 1.2 has run and the cell's
    baseline fragment pins the new promotion receipt" -- happened in
    ``c1f63599``: SAEA-SN-DEV1000-TS2-PREPROCESS-V1 promoted all 1,000 @ts2
    packets and both SLURP experiment fragments moved to the
    ``slurp-direct-closed-list-tail2s`` baseline. The receipt ``cf566cb6``
    landed records all four cells reaching the seal. So the assertion is no
    longer carrier-specific: it is ONE rule for every cell, the one that
    actually matters.

    A cell that exits 0 is green only when its own ``seal_and_score`` line says
    OK. Which of the two admissible states a given receipt records is an
    ENVIRONMENT fact -- whether another flight held the flight lock while the
    check ran -- so it is not pinned here; the preregistration's section 6
    names the measurement and the commit it was taken at.

    UPDATED 2026-09-09, after both SLURP ``@ts2`` rows were marked consumed. The
    real gate refuses a run whose exposure row is consumed, so a flown cell's
    preflight now stops at ``consumed`` (the ledger doing its job) rather
    than at ``gate-not-authorized``; a cell that was never registered still
    stops at ``gate-not-authorized``. Both are admissible preflight stops;
    which one a receipt records is a fact about the ledger at the commit it
    was taken at, and the sealed ``cf566cb6`` receipt is not rewritten.
    """

    receipt = json.loads(WIRE.read_text(encoding="utf-8"))
    stops = {
        (row["cell"], mode): row[mode]["stop_class"]
        for row in receipt["cells"]
        for mode in ("preflight", "wire_check")
    }
    assert "UNEXPECTED" not in set(stops.values())
    assert all(
        stops[(cell, "preflight")] in {"gate-not-authorized", "consumed"}
        for cell in {row["cell"] for row in receipt["cells"]}
    )
    by_cell = {row["cell"]: row["wire_check"] for row in receipt["cells"]}

    for cell, entry in by_cell.items():
        # Audio2Tool: the gold-id rail is in. SLURP: the @ts2 packets are
        # promoted and pinned. Neither cell may stop at its old blocker.
        assert entry["stop_class"] != "a2t-gold-id-rail-missing", cell
        assert entry["stop_class"] != "slurp-packet-root-missing", cell
        # A green here REQUIRES the seal to have said OK: a run that exits 0
        # with a refused or failed seal is recorded as its own stop class, so
        # "none" can never hide the link section 8 item 4 exists to prove.
        if entry["stop_class"] == "none":
            assert entry["seal_and_score"] == "OK", cell
            assert entry["reached_the_end"] is True, cell
        else:
            # REFUSED is the only non-OK status this test tolerates, and the
            # distinction is the whole point. core.flight refuses to BUILD a
            # COMPLETED manifest at all when the load-bearing surface (src/,
            # configs/, docs/arms/, scripts/) is dirty or another flight holds
            # $SPEECHRL_DATA_DIR/locks/flight.lock with a different HEAD, and it
            # RECORDS that refusal rather than raising -- so this check can be
            # re-run during someone else's campaign without either lying about
            # the result or touching their lock. SCORING_FAILED is the
            # opposite: a
            # manifest that sealed COMPLETED and then would not score, which is
            # exactly what section 8 item 4 exists to catch and is never
            # tolerated here.
            assert entry["stop_class"] == "seal-and-score-not-ok", cell
            assert entry["seal_and_score"] == "REFUSED", cell
            assert entry["reached_the_end"] is False, cell


#: The two Audio2Tool ``@ts2`` dataset fragments MOVED on 2026-09-09, and the
#: sealed 2026-09-07 receipt is never rewritten to hide it. Each gained the
#: plain ``d1_media_supplement`` / ``d1_media_supplement_sha256`` pair the media
#: identity gate reads -- the D1 declaration fix of ``docs/readiness/
#: 2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md``. The SLURP ``@ts2``
#: view always carried the plain pair and is deliberately NOT here: it must
#: still match the live bytes exactly, which is what makes this list a bound on
#: the change rather than an excuse for it.
SUPERSEDED_BY_THE_D1_DECLARATION_FIX = {
    "configs/dataset/audio2tool-calibration-400-tail2s.json": (
        "c06eaabd4b88c0511adf2b0d5d936fe0be54d1f4b101b2451b06f4a68acac9d9"
    ),
    "configs/dataset/audio2tool-calibration-400-tail2s-smoke4.json": (
        "6970b65bf38b1bad9ce12eefde963b8edbc2264c6ca907450b68012373ad5d25"
    ),
}


def test_wire_check_receipt_pins_the_fragments_it_drove() -> None:
    receipt = json.loads(WIRE.read_text(encoding="utf-8"))
    for relpath, digest in receipt["fragments"].items():
        if relpath in SUPERSEDED_BY_THE_D1_DECLARATION_FIX:
            assert digest == SUPERSEDED_BY_THE_D1_DECLARATION_FIX[relpath], relpath
            continue
        assert hashlib.sha256((REPO / relpath).read_bytes()).hexdigest() == digest, relpath


@pytest.mark.parametrize("relpath", sorted(SUPERSEDED_BY_THE_D1_DECLARATION_FIX))
def test_every_superseded_fragment_moved_for_exactly_the_declaration_fix(
    relpath: str,
) -> None:
    """The supersession above is bounded: each listed fragment now declares the
    D1 media supplement under BOTH spellings, in agreement."""

    values = _json(relpath)
    assert (
        values["d1_media_supplement"] == values["a2t_calibration_d1_media_supplement"]
    )
    assert (
        values["d1_media_supplement_sha256"]
        == values["a2t_calibration_d1_media_supplement_sha256"]
    )
    assert hashlib.sha256((REPO / relpath).read_bytes()).hexdigest() != (
        SUPERSEDED_BY_THE_D1_DECLARATION_FIX[relpath]
    )


def test_wire_check_receipt_says_why_earnings21_has_no_cell() -> None:
    receipt = json.loads(WIRE.read_text(encoding="utf-8"))
    note = str(receipt["earnings21"])
    assert "obs_loop" in note and "oracle" in note


def test_receipt_manifest_covers_the_directory() -> None:
    directory = WIRE.parent
    lines = (directory / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    listed = {line.split(" *", 1)[1] for line in lines if line}
    present = {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    }
    assert listed == present
    for line in lines:
        digest, name = line.split(" *", 1)
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
