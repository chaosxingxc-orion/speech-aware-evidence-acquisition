"""``rails.probes.a2t_s2_flight``: the P-A2T Stage-2 four-arm supply-probe
flight orchestration
(docs/readiness/2026-08-18-pa2t-stage2-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test here drives
``rails.core_client.MockCoreClient`` or plain synthetic fixtures; the real
attempt directory under ``SPEECHRL_DATA_DIR`` is never touched.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.audio2tool import render_registry_row
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    Audio2ToolAdapter,
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (
    A2T_S2_ARMS,
    DEFAULT_SEED,
    HEADROOM_N,
    N0R_ARM,
    N0R_TARGET_N,
    S1P_ARM,
    S2_ARM,
    S2_TOTAL_ROSTER_SIZE,
    S4_ARM,
    A2tS2FlightError,
    HeadroomManifest,
    assemble_roster_prompt,
    build_flight_plan,
    build_s4_derangement,
    derive_a0_selected_tools,
    load_headroom_manifest,
    n0r_seeded_draw,
    render_roster_prompt_block,
    result_to_json,
    roster_supply_packet,
    run_a2t_s2_flight,
    s1p_tool_names,
    s2_distractor_pool,
    s2_tool_names,
    write_outputs_jsonl,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import _INSTRUCTION_TEMPLATE

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_HEADROOM_PATH = (
    _REPO_ROOT
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-08-18-pa2t-a0-read"
    / "headroom.json"
)


def _row(tool_id: int, name: str, *, domain: str = "smart_home") -> dict:
    return {
        "tool_id": str(tool_id),
        "domain": domain,
        "category": "misc",
        "tool_name": name,
        "signature": f"{name}(deviceId: String)",
        "description": f"{name} description",
        "argument_defaults": "",
        "argument_constraints": "",
    }


_REGISTRY_ROWS = tuple(_row(i, f"tool{i:02d}") for i in range(1, 13))  # 12 distinct tools


# ---------------------------------------------------------------------------
# s1p_tool_names
# ---------------------------------------------------------------------------


def test_s1p_tool_names_single_selection():
    assert s1p_tool_names(["tool01"]) == ("tool01",)


def test_s1p_tool_names_dedups_and_sorts_multi_intent_selection():
    assert s1p_tool_names(["tool03", "tool01", "tool03"]) == ("tool01", "tool03")


# ---------------------------------------------------------------------------
# s2_distractor_pool / s2_tool_names
# ---------------------------------------------------------------------------


def test_s2_distractor_pool_excludes_correct_tools():
    all_names = tuple(row["tool_name"] for row in _REGISTRY_ROWS)
    pool = s2_distractor_pool(("tool01",), all_names)
    assert "tool01" not in pool
    assert len(pool) == len(all_names) - 1


def test_s2_tool_names_single_correct_gives_total_nine():
    all_names = tuple(row["tool_name"] for row in _REGISTRY_ROWS)
    rng = random.Random(DEFAULT_SEED)
    names = s2_tool_names(("tool01",), all_names, rng)
    assert len(names) == S2_TOTAL_ROSTER_SIZE == 9
    assert "tool01" in names
    assert names == tuple(sorted(names))


def test_s2_tool_names_multi_intent_keeps_total_dose_fixed_at_nine():
    all_names = tuple(row["tool_name"] for row in _REGISTRY_ROWS)
    rng = random.Random(DEFAULT_SEED)
    names = s2_tool_names(("tool01", "tool02", "tool03"), all_names, rng)
    assert len(names) == S2_TOTAL_ROSTER_SIZE
    assert {"tool01", "tool02", "tool03"} <= set(names)


def test_s2_tool_names_is_deterministic_given_the_same_seed():
    all_names = tuple(row["tool_name"] for row in _REGISTRY_ROWS)
    first = s2_tool_names(("tool01",), all_names, random.Random(DEFAULT_SEED))
    second = s2_tool_names(("tool01",), all_names, random.Random(DEFAULT_SEED))
    assert first == second


def test_s2_tool_names_raises_when_registry_too_small():
    rng = random.Random(DEFAULT_SEED)
    with pytest.raises(A2tS2FlightError, match="distractor"):
        s2_tool_names(("tool01",), ("tool01", "tool02"), rng)


# ---------------------------------------------------------------------------
# build_s4_derangement
# ---------------------------------------------------------------------------


def test_build_s4_derangement_has_no_fixed_points():
    names = [f"tool{i:02d}" for i in range(1, 9)]
    mapping = build_s4_derangement(names, seed=DEFAULT_SEED)
    assert set(mapping) == set(names)
    for tool, deranged in mapping.items():
        assert deranged != tool
    # Bijection: every value is also a distinct key.
    assert set(mapping.values()) == set(names)


def test_build_s4_derangement_is_deterministic():
    names = [f"tool{i:02d}" for i in range(1, 9)]
    first = build_s4_derangement(names, seed=DEFAULT_SEED)
    second = build_s4_derangement(list(reversed(names)), seed=DEFAULT_SEED)
    assert first == second


def test_build_s4_derangement_dedups_input():
    names = ["a", "b", "a", "b", "c"]
    mapping = build_s4_derangement(names, seed=DEFAULT_SEED)
    assert set(mapping) == {"a", "b", "c"}


def test_build_s4_derangement_requires_at_least_two_distinct_tools():
    with pytest.raises(A2tS2FlightError, match="at least 2 distinct"):
        build_s4_derangement(["only-one"], seed=DEFAULT_SEED)


def test_s4_wrong_tool_chases_the_cycle_past_a_multi_intent_collision():
    """A forced collision: derangement maps "a" straight to "b", but "b" is
    ALSO one of this (multi-intent) sample's own correctly-selected tools --
    _s4_wrong_tool_for_sample must chase the cycle to "c" instead of handing
    back a tool the sample itself already selected."""

    from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (
        _s4_wrong_tool_for_sample,
    )

    derangement = {"a": "b", "b": "c", "c": "a"}
    wrong = _s4_wrong_tool_for_sample("a", ["a", "b"], derangement)
    assert wrong == "c"


def test_s4_wrong_tool_returns_the_direct_derangement_when_no_collision():
    from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (
        _s4_wrong_tool_for_sample,
    )

    derangement = {"a": "b", "b": "a"}
    assert _s4_wrong_tool_for_sample("a", ["a"], derangement) == "b"


def test_s4_wrong_tool_fails_closed_when_own_tools_cover_the_whole_cycle():
    from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (
        _s4_wrong_tool_for_sample,
    )

    derangement = {"a": "b", "b": "a"}
    with pytest.raises(A2tS2FlightError, match="could not find a wrong tool"):
        _s4_wrong_tool_for_sample("a", ["a", "b"], derangement)


# ---------------------------------------------------------------------------
# n0r_seeded_draw
# ---------------------------------------------------------------------------


def _synthetic_headroom_ids() -> tuple[str, ...]:
    """The REGISTERED tier distribution (23/17/29/3/12/12/8/16 = 120)."""

    counts = {
        "tier1_direct": 23,
        "tier2_parametric": 17,
        "tier3_multi_intent": 29,
        "tier4_implicit": 3,
        "tier5_needle": 12,
        "tier6_correction": 12,
        "tier7_multiturn": 8,
        "tier8_intent_blending": 16,
    }
    ids: list[str] = []
    for tier, count in counts.items():
        ids.extend(f"{tier}:{i:06d}" for i in range(count))
    assert len(ids) == HEADROOM_N
    return tuple(ids)


def test_n0r_seeded_draw_produces_forty_ids_from_the_registered_tier_shape():
    ids = _synthetic_headroom_ids()
    draw = n0r_seeded_draw(ids, seed=DEFAULT_SEED, target_n=N0R_TARGET_N)
    assert len(draw) == N0R_TARGET_N
    assert set(draw) <= set(ids)
    assert len(set(draw)) == N0R_TARGET_N  # no duplicates


def test_n0r_seeded_draw_is_tier_proportional_within_rounding():
    ids = _synthetic_headroom_ids()
    draw = n0r_seeded_draw(ids, seed=DEFAULT_SEED, target_n=N0R_TARGET_N)
    total = len(ids)
    from collections import Counter

    tier_counts = Counter(sample_id.split(":", 1)[0] for sample_id in ids)
    draw_counts = Counter(sample_id.split(":", 1)[0] for sample_id in draw)
    for tier, count in tier_counts.items():
        exact = count * N0R_TARGET_N / total
        got = draw_counts.get(tier, 0)
        assert abs(got - exact) < 1.0 + 1e-9


def test_n0r_seeded_draw_is_deterministic():
    ids = _synthetic_headroom_ids()
    first = n0r_seeded_draw(ids, seed=DEFAULT_SEED, target_n=N0R_TARGET_N)
    second = n0r_seeded_draw(tuple(reversed(ids)), seed=DEFAULT_SEED, target_n=N0R_TARGET_N)
    assert first == second


def test_n0r_seeded_draw_rejects_empty_input():
    with pytest.raises(A2tS2FlightError, match="at least one"):
        n0r_seeded_draw((), seed=DEFAULT_SEED)


def test_n0r_seeded_draw_against_the_real_registered_headroom_list():
    """Proves this function actually works against the mission's own
    committed artifact, not merely a hand-shrunk synthetic fixture (mirrors
    ``test_load_pslu_rosters_against_the_real_binding_table``'s own
    precedent) -- read-only against a small, already-committed JSON file,
    never the real (large, external) attempt outputs.jsonl."""

    manifest = load_headroom_manifest(_REAL_HEADROOM_PATH)
    draw = n0r_seeded_draw(manifest.sample_ids, seed=DEFAULT_SEED, target_n=N0R_TARGET_N)
    assert len(draw) == N0R_TARGET_N
    assert set(draw) <= set(manifest.sample_ids)


# ---------------------------------------------------------------------------
# render_roster_prompt_block / roster_supply_packet
# ---------------------------------------------------------------------------


def test_render_roster_prompt_block_matches_render_registry_row_joined():
    rows = [_REGISTRY_ROWS[0], _REGISTRY_ROWS[1]]
    block = render_roster_prompt_block(rows)
    assert block == render_registry_row(rows[0]) + "\n" + render_registry_row(rows[1])


def test_roster_supply_packet_dose_matches_the_rows():
    rows = list(_REGISTRY_ROWS[:1])
    packet = roster_supply_packet(S1P_ARM, "sample-1", rows)
    assert packet.dose.n_items == 1
    assert packet.dose.token_count == len(packet.prompt_block.split())
    assert len(packet.items) == 1


def test_roster_supply_packet_nine_rows_dose_is_far_below_full_registry():
    """The bridge mission's own required check: a narrowed roster's token
    estimate must shrink sharply relative to A0's full-152-row prefill."""

    rows = list(_REGISTRY_ROWS[:9])
    packet = roster_supply_packet(S2_ARM, "sample-1", rows)
    assert packet.dose.n_items == 9
    single_row_packet = roster_supply_packet(S1P_ARM, "sample-1", rows[:1])
    # 9 rows costs roughly 9x a single row's dose, and both are tiny next to
    # A0's real measured ~12693-token full-registry prefill.
    assert packet.dose.token_count == pytest.approx(9 * single_row_packet.dose.token_count, rel=0.5)
    assert packet.dose.token_count < 2000


def test_roster_supply_packet_rejects_empty_rows():
    with pytest.raises(A2tS2FlightError, match="at least one row"):
        roster_supply_packet(S1P_ARM, "sample-1", [])


# ---------------------------------------------------------------------------
# assemble_roster_prompt
# ---------------------------------------------------------------------------


def _sample(sample_id: str = "tier1_direct:000001") -> Audio2ToolSample:
    return Audio2ToolSample(
        sample_id=sample_id,
        audio_ref=AudioRef(path="unused", sha256="0" * 64).validate(),
        audio_seconds=1.0,
        media_relpath=f"datasets/audio2tool/public/{sample_id.replace(':', '_')}.wav",
    )


def test_assemble_roster_prompt_uses_the_frozen_instruction_template():
    sample = _sample()
    block = render_roster_prompt_block([_REGISTRY_ROWS[0]])
    messages = assemble_roster_prompt(sample, block)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == _INSTRUCTION_TEMPLATE.format(tool_schemas=block)
    assert "{tool_schemas}" not in messages[0]["content"]
    user_content = messages[1]["content"]
    assert len(user_content) == 1
    assert user_content[0] == {"type": "input_audio", "media_relpath": sample.media_relpath}


def test_assemble_roster_prompt_never_adds_a_text_content_part():
    sample = _sample()
    block = render_roster_prompt_block(list(_REGISTRY_ROWS[:9]))
    messages = assemble_roster_prompt(sample, block)
    assert all(part["type"] != "text" for part in messages[1]["content"])


# ---------------------------------------------------------------------------
# load_headroom_manifest
# ---------------------------------------------------------------------------


def _write_headroom(path: Path, **overrides) -> None:
    document = {
        "schema": "saea-a2t-a0-headroom-v1",
        "attempt_dir": "/fake/attempt/dir",
        "count": HEADROOM_N,
        "sample_ids": [f"tier1_direct:{i:06d}" for i in range(HEADROOM_N)],
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_load_headroom_manifest_happy_path(tmp_path):
    path = tmp_path / "headroom.json"
    _write_headroom(path)
    manifest = load_headroom_manifest(path)
    assert len(manifest.sample_ids) == HEADROOM_N
    assert manifest.sample_ids == tuple(sorted(manifest.sample_ids))
    assert manifest.attempt_dir == "/fake/attempt/dir"


def test_load_headroom_manifest_rejects_wrong_schema(tmp_path):
    path = tmp_path / "headroom.json"
    _write_headroom(path, schema="wrong-schema")
    with pytest.raises(A2tS2FlightError, match="schema"):
        load_headroom_manifest(path)


def test_load_headroom_manifest_rejects_wrong_count(tmp_path):
    path = tmp_path / "headroom.json"
    _write_headroom(path, sample_ids=["tier1_direct:000001"])
    with pytest.raises(A2tS2FlightError, match="120"):
        load_headroom_manifest(path)


def test_load_headroom_manifest_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "headroom.json"
    ids = [f"tier1_direct:{i:06d}" for i in range(HEADROOM_N - 1)] + ["tier1_direct:000000"]
    _write_headroom(path, sample_ids=ids)
    with pytest.raises(A2tS2FlightError, match="duplicate"):
        load_headroom_manifest(path)


def test_load_headroom_manifest_rejects_missing_attempt_dir(tmp_path):
    path = tmp_path / "headroom.json"
    _write_headroom(path, attempt_dir="")
    with pytest.raises(A2tS2FlightError, match="attempt_dir"):
        load_headroom_manifest(path)


def test_load_headroom_manifest_against_the_real_registered_artifact():
    manifest = load_headroom_manifest(_REAL_HEADROOM_PATH)
    assert len(manifest.sample_ids) == HEADROOM_N == 120


# ---------------------------------------------------------------------------
# derive_a0_selected_tools
# ---------------------------------------------------------------------------


def _write_attempt_outputs(path: Path, rows: list[dict]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _a0_row(sample_id: str, response_text: str, *, arm: str = "zero-supply") -> dict:
    return {
        "arm": arm,
        "sample_id": sample_id,
        "messages": [],
        "response_text": response_text,
        "metrics": {},
        "consumption": {},
    }


def test_derive_a0_selected_tools_happy_path(tmp_path):
    rows = [
        _a0_row("tier1_direct:000001", json.dumps([{"name": "setLighting", "arguments": {}}])),
        _a0_row(
            "tier3_multi_intent:000004",
            json.dumps(
                [
                    {"name": "setSecurityMode", "arguments": {}},
                    {"name": "setTargetTemperature", "arguments": {}},
                    {"name": "setSecurityMode", "arguments": {"mode": "Home"}},
                ]
            ),
        ),
    ]
    _write_attempt_outputs(tmp_path, rows)
    result = derive_a0_selected_tools(tmp_path, ["tier1_direct:000001", "tier3_multi_intent:000004"])
    assert result["tier1_direct:000001"] == ("setLighting",)
    assert result["tier3_multi_intent:000004"] == ("setSecurityMode", "setTargetTemperature")


def test_derive_a0_selected_tools_missing_sample_raises(tmp_path):
    _write_attempt_outputs(
        tmp_path, [_a0_row("tier1_direct:000001", json.dumps([{"name": "setLighting"}]))]
    )
    with pytest.raises(A2tS2FlightError, match="no zero-supply row"):
        derive_a0_selected_tools(tmp_path, ["tier1_direct:000001", "tier1_direct:999999"])


def test_derive_a0_selected_tools_wrong_arm_raises(tmp_path):
    _write_attempt_outputs(
        tmp_path,
        [_a0_row("tier1_direct:000001", json.dumps([{"name": "setLighting"}]), arm="supplied")],
    )
    with pytest.raises(A2tS2FlightError, match="arm"):
        derive_a0_selected_tools(tmp_path, ["tier1_direct:000001"])


def test_derive_a0_selected_tools_duplicate_row_raises(tmp_path):
    rows = [
        _a0_row("tier1_direct:000001", json.dumps([{"name": "setLighting"}])),
        _a0_row("tier1_direct:000001", json.dumps([{"name": "setLighting"}])),
    ]
    _write_attempt_outputs(tmp_path, rows)
    with pytest.raises(A2tS2FlightError, match="duplicate"):
        derive_a0_selected_tools(tmp_path, ["tier1_direct:000001"])


def test_derive_a0_selected_tools_empty_prediction_raises(tmp_path):
    _write_attempt_outputs(tmp_path, [_a0_row("tier1_direct:000001", "not valid json")])
    with pytest.raises(A2tS2FlightError, match="tool_accuracy == 1.0"):
        derive_a0_selected_tools(tmp_path, ["tier1_direct:000001"])


# ---------------------------------------------------------------------------
# build_flight_plan
# ---------------------------------------------------------------------------


def _small_headroom(n0r_n: int = 4) -> tuple[HeadroomManifest, dict]:
    sample_ids = tuple(f"tier1_direct:{i:06d}" for i in range(10)) + tuple(
        f"tier3_multi_intent:{i:06d}" for i in range(2)
    )
    manifest = HeadroomManifest(sample_ids=tuple(sorted(sample_ids)), attempt_dir="/fake", split_identity_hash=None)
    selected_tools = {sid: ("tool01",) for sid in sample_ids[:10]}
    selected_tools.update({sid: ("tool02", "tool03") for sid in sample_ids[10:]})
    return manifest, selected_tools


def test_build_flight_plan_happy_path_resolves_every_arm():
    manifest, selected = _small_headroom()
    plan = build_flight_plan(manifest, selected, _REGISTRY_ROWS, seed=DEFAULT_SEED, n0r_target_n=4)
    assert set(plan.headroom_ids) == set(manifest.sample_ids)
    for sample_id in plan.headroom_ids:
        assert len(plan.s2_tool_names_by_sample[sample_id]) == S2_TOTAL_ROSTER_SIZE
        s1p_names = plan.s1p_tool_names_by_sample[sample_id]
        wrong = plan.s4_tool_name_by_sample[sample_id]
        # S4's wrong tool is never ANY of this sample's own correctly
        # selected tools (not just the canonical one) -- see
        # _s4_wrong_tool_for_sample's own docstring for the multi-intent
        # collision this guards against.
        assert wrong not in s1p_names
    assert len(plan.n0r_sample_ids) == 4
    assert set(plan.n0r_sample_ids) <= set(plan.headroom_ids)


def test_build_flight_plan_is_reproducible():
    manifest, selected = _small_headroom()
    plan1 = build_flight_plan(manifest, selected, _REGISTRY_ROWS, seed=DEFAULT_SEED, n0r_target_n=4)
    plan2 = build_flight_plan(manifest, selected, _REGISTRY_ROWS, seed=DEFAULT_SEED, n0r_target_n=4)
    assert plan1.s2_tool_names_by_sample == plan2.s2_tool_names_by_sample
    assert plan1.s4_tool_name_by_sample == plan2.s4_tool_name_by_sample
    assert plan1.n0r_sample_ids == plan2.n0r_sample_ids


def test_build_flight_plan_rejects_sample_mismatch():
    manifest, selected = _small_headroom()
    del selected[manifest.sample_ids[0]]
    with pytest.raises(A2tS2FlightError, match="does not match"):
        build_flight_plan(manifest, selected, _REGISTRY_ROWS, n0r_target_n=4)


def test_build_flight_plan_rejects_unknown_tool_name():
    manifest, selected = _small_headroom()
    selected[manifest.sample_ids[0]] = ("not-a-real-tool",)
    with pytest.raises(A2tS2FlightError, match="not present in the"):
        build_flight_plan(manifest, selected, _REGISTRY_ROWS, n0r_target_n=4)


def test_build_flight_plan_rejects_duplicate_registry_tool_name():
    manifest, selected = _small_headroom()
    dup_rows = list(_REGISTRY_ROWS) + [_row(99, "tool01")]
    with pytest.raises(A2tS2FlightError, match="duplicate tool_name"):
        build_flight_plan(manifest, selected, dup_rows, n0r_target_n=4)


# ---------------------------------------------------------------------------
# End-to-end: run_a2t_s2_flight over a MockCoreClient, tiny fixture set.
# ---------------------------------------------------------------------------


class _TinyAudio2ToolWorld:
    """Just enough for ``Audio2ToolAdapter.assemble_prompt``/N0r's own
    full-registry rendering: a lock + a tools_registry.csv under a synthetic
    data root. No wav files, no probe-sample receipt -- this flight never
    calls ``adapter.load_split``/``adapter.score``, so none of that
    machinery is needed; ``Audio2ToolSample`` objects are hand-built."""

    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "data"
        self.lock_path = tmp_path / "lock.json"
        carrier_dir = self.data_root / "datasets" / "audio2tool"
        carrier_dir.mkdir(parents=True, exist_ok=True)
        header = (
            "tool_id,domain,category,tool_name,signature,description,"
            "argument_defaults,argument_constraints\n"
        )
        lines = [header]
        for row in _REGISTRY_ROWS:
            lines.append(
                f"{row['tool_id']},{row['domain']},{row['category']},{row['tool_name']},"
                f'"{row["signature"]}","{row["description"]}",'
                f'"{row["argument_defaults"]}","{row["argument_constraints"]}"\n'
            )
        (carrier_dir / "tools_registry.csv").write_text("".join(lines), encoding="utf-8")
        self.lock_path.write_text(
            json.dumps(
                {
                    "asset_catalog": [
                        {
                            "name": "audio2tool",
                            "kind": "dataset",
                            "local_subdir": "datasets/audio2tool",
                            "license": "CC-BY-NC-4.0",
                            "lifecycle": "STAGE2_CANDIDATE",
                            "profiles": ["speech-aware-secondary"],
                        }
                    ],
                    "models": [],
                }
            ),
            encoding="utf-8",
        )

    def adapter(self) -> Audio2ToolAdapter:
        lock = load_lock(self.lock_path)
        return Audio2ToolAdapter(lock, self.data_root, repo_root=self.data_root)


@pytest.fixture()
def tiny_a2t_world(tmp_path):
    return _TinyAudio2ToolWorld(tmp_path)


def _mock_responder(messages):
    return json.dumps([{"name": "tool01", "arguments": {}}])


def test_run_a2t_s2_flight_end_to_end_with_mock_client(tiny_a2t_world):
    manifest, selected = _small_headroom(n0r_n=3)
    plan = build_flight_plan(manifest, selected, _REGISTRY_ROWS, seed=DEFAULT_SEED, n0r_target_n=3)
    adapter = tiny_a2t_world.adapter()
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)

    counter = {"t": 0.0}

    def fake_now():
        counter["t"] += 1.0
        return counter["t"]

    summary = run_a2t_s2_flight(
        adapter=adapter, core_client=client, samples=samples, plan=plan, now=fake_now
    )

    n = len(plan.headroom_ids)
    assert len(summary.results) == 3 * n + 3
    by_arm = {}
    for result in summary.results:
        by_arm.setdefault(result.arm, []).append(result)
    assert {arm: len(rows) for arm, rows in by_arm.items()} == {
        S1P_ARM: n,
        S2_ARM: n,
        S4_ARM: n,
        N0R_ARM: 3,
    }
    assert set(by_arm) == set(A2T_S2_ARMS)

    # N0r requests are byte-identical to Audio2ToolAdapter.assemble_prompt(sample, None).
    # client.calls is in EXACTLY the same order run_a2t_s2_flight issued them
    # (module docstring: S1p/S2/S4 per sample for every headroom sample, in
    # order, THEN N0r) -- so the first N0r call sits at index 3*n.
    n0r_sample_id = plan.n0r_sample_ids[0]
    expected_messages = adapter.assemble_prompt(_sample(n0r_sample_id), None)
    first_n0r_call_messages = client.calls[3 * n][0]
    assert first_n0r_call_messages == expected_messages
    assert summary.results[3 * n].arm == N0R_ARM
    assert summary.results[3 * n].sample_id == n0r_sample_id

    # S4's supplied_tool is never one of the sample's own S1p-selected tools.
    s4_results = {r.sample_id: r for r in by_arm[S4_ARM]}
    for sample_id in plan.headroom_ids:
        assert s4_results[sample_id].supplied_tool == plan.s4_tool_name_by_sample[sample_id]
        assert s4_results[sample_id].supplied_tool not in plan.s1p_tool_names_by_sample[sample_id]

    # N0r rows carry no supplied_tool.
    assert all(r.supplied_tool is None for r in by_arm[N0R_ARM])


def test_run_a2t_s2_flight_s1p_prompt_is_narrower_than_full_registry(tiny_a2t_world):
    manifest, selected = _small_headroom(n0r_n=1)
    plan = build_flight_plan(manifest, selected, _REGISTRY_ROWS, seed=DEFAULT_SEED, n0r_target_n=1)
    adapter = tiny_a2t_world.adapter()
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)

    run_a2t_s2_flight(adapter=adapter, core_client=client, samples=samples, plan=plan)

    full_registry_len = len(adapter.assemble_prompt(samples[0], None)[0]["content"])
    s1p_sample_id = plan.headroom_ids[0]
    s1p_messages = assemble_roster_prompt(
        _sample(s1p_sample_id),
        render_roster_prompt_block(
            [plan.registry_index[name] for name in plan.s1p_tool_names_by_sample[s1p_sample_id]]
        ),
    )
    assert len(s1p_messages[0]["content"]) < full_registry_len / 5


def test_write_outputs_jsonl_round_trips_the_minimal_row_shape(tmp_path, tiny_a2t_world):
    manifest, selected = _small_headroom(n0r_n=2)
    plan = build_flight_plan(manifest, selected, _REGISTRY_ROWS, seed=DEFAULT_SEED, n0r_target_n=2)
    adapter = tiny_a2t_world.adapter()
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)
    summary = run_a2t_s2_flight(adapter=adapter, core_client=client, samples=samples, plan=plan)

    out_path = tmp_path / "outputs.jsonl"
    write_outputs_jsonl(out_path, summary.results)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(summary.results)
    for line, result in zip(lines, summary.results):
        document = json.loads(line)
        assert set(document) == {"arm", "sample_id", "supplied_tool", "response", "timing"}
        assert document == result_to_json(result)
        assert set(document["timing"]) == {"started_at", "latency_seconds"}


def test_run_a2t_s2_flight_rejects_plan_sample_mismatch(tiny_a2t_world):
    manifest, selected = _small_headroom(n0r_n=1)
    plan = build_flight_plan(manifest, selected, _REGISTRY_ROWS, seed=DEFAULT_SEED, n0r_target_n=1)
    adapter = tiny_a2t_world.adapter()
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids[:-1]]  # drop one
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tS2FlightError, match="not present in samples"):
        run_a2t_s2_flight(adapter=adapter, core_client=client, samples=samples, plan=plan)
