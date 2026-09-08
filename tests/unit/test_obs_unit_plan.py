"""``obs_unit_plan`` / ``obs_unit_plan_sha256``: the OBS-E1 obs seam.

Section 8 of ``docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-
preregistration.md``. Two thin keys on the already-registered
``obs-agent-loop`` policy replace the clock-derived fixed windows with the
hash-pinned SPEAKER-TURN UNITS of a ``saea-e21-speaker-turn-units-v1`` plan.
Both default to ``None``, and ``None`` must be the historical cutter byte for
byte -- every sealed Earnings run depends on it.

Four things are proved here.

1. **The units are consumed, in order, on BOTH executor paths** -- the
   sequential loop and ``_slice_parallel_pass`` -- with the plan's own spans
   on the ``SliceRecord``, ``iteration = unit_index - 1`` (so slice relpaths
   and request ids keep their historical shape), ``obs_final_window`` on the
   call's last unit, and the unit's id / speaker / end cut in the OBS trace.
2. **The tail is applied ONCE**, by the existing
   ``obs_slice_tail_silence_seconds`` knob through the existing
   ``obs_audio.encode_slice``: no second tail implementation exists, the cut
   span is untouched, and ``audio_seconds`` still equals the span (which is
   the rail that would refuse a seam that silently moved a cut).
3. **Every refusal fires, fail-closed, before a window is cut**: a missing
   plan, a SHA-256 mismatch, a foreign schema, a call with no units, a unit
   outside its call's audio, a unit longer than the slot's audio budget, a
   unit id collision, a plan that does not tile, a roster call the plan does
   not cover, a plan cut against different audio, and each of the three knobs
   a plan is incompatible with.
4. **With the keys null nothing moves at all** -- proved twice: on a
   synthetic world against the historical key-absent path, and against the
   COMMITTED window hashes of the sealed full-44 direct baseline, by replaying
   one real call's own sealed 90-second cut through the seam-carrying cutter.

The data-backed tests SKIP (never soften) when ``$SPEECHRL_DATA_DIR`` or the
sealed slices are absent; everything else is pure and runs anywhere.
"""

from __future__ import annotations

import hashlib
import json
import wave
from array import array
from dataclasses import replace
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.reproduction.obs_audio import (
    SLICE_TAIL_SILENCE_TRANSFORM,
    append_tail_silence,
    write_wav_bytes,
)
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    OBS_UNIT_PLAN_BOUNDARY_MODE,
    OBS_UNIT_PLAN_SCHEMA,
    OBS_UNIT_PLAN_SCHEMA_V2,
    OBS_UNIT_PLAN_SCHEMAS,
    ObsLoopConfig,
    ObsLoopError,
)

from test_obs_loop_policy import (  # noqa: E402
    RATE,
    RUN_ID,
    SAMPLE_ID,
    _World,
    _fixed_mode_skip_values,
    _noise,
    _obs_payloads,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_RELPATH = "docs/receipts/obs/synthetic-units.json"

#: The committed OBS-E1 plan and the sealed run its units were cut against.
REAL_PLAN_RELPATH = "docs/receipts/obs/e21-speaker-turn-units-v1.json"
REAL_PLAN = REPO_ROOT / REAL_PLAN_RELPATH
TS2_ROSTER = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-buf90-tail2s-media"
    / "roster/flight-roster-receipt.json"
)
#: The sealed ``saea-diarization-v1`` inputs receipt, whose per-call
#: ``audio_sha256`` is the WAV hash of that call's whole decoded audio -- the
#: oracle section 6 of the preregistration names for the seam's falsifier.
DIARIZATION_INPUTS = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-diarization-obs"
    / "inputs.json"
)
#: The call the data-backed falsifiers replay: the SHORTEST of the frozen 44
#: (1,097.1 s, 13 sealed windows, 34 planned units), so the proof is the full
#: one -- every window and every unit of a real call -- at 34 MB of reads.
REAL_CALL = "4386541"

#: The 2.0-second tail, in samples at the slice rate.
TAIL_SAMPLES = 2 * RATE


# ---------------------------------------------------------------------------
# Synthetic plan helpers
# ---------------------------------------------------------------------------


def _unit(sample_id: str, index: int, start: float, end: float, **overrides) -> dict:
    unit = {
        "unit_id": f"{sample_id}#u{index:04d}",
        "sample_id": sample_id,
        "unit_index": index,
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": end - start,
        "delivered_seconds": end - start + 2.0,
        "speaker": "speaker_1" if index % 2 else "speaker_2",
        "speaker_share": 1.0,
        "speaker_count": 1,
        "start_cut": "call-start" if index == 1 else "pause",
        "end_cut": "pause",
        "ends_on_active_frame": False,
        "flags": [],
    }
    unit.update(overrides)
    return unit


def _plan_document(
    *, sample_id: str = SAMPLE_ID, duration: float, edges, schema: str = OBS_UNIT_PLAN_SCHEMA
) -> dict:
    """A plan whose one call is cut at ``edges`` (interior boundaries)."""

    bounds = [0.0, *edges, duration]
    units = [
        _unit(sample_id, index, bounds[index - 1], bounds[index])
        for index in range(1, len(bounds))
    ]
    units[-1]["end_cut"] = "call-end"
    return {
        "schema": schema,
        "calls": [
            {
                "sample_id": sample_id,
                "decoded_duration_seconds": duration,
                "units": units,
            }
        ],
    }


def _plan_bytes(document) -> bytes:
    return json.dumps(document, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")


def _install_plan(repo_root: Path, document, relpath: str = PLAN_RELPATH) -> str:
    """Write ``document`` under ``repo_root`` and return its SHA-256."""

    raw = _plan_bytes(document)
    path = Path(repo_root) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _plan_values(relpath: str, sha256: str, **overrides) -> dict:
    """Fixed-mode config values carrying the two seam keys.

    ``obs_buffer_seconds`` stays the sealed 90 so the plan's 90-second cap and
    the slot's audio budget are the same number, exactly as the drafted
    ``configs/baseline/e21-units-obse1-scored7.json`` leaves them.
    """

    values = _fixed_mode_skip_values(
        obs_buffer_seconds=90,
        obs_min_advance_seconds=90,
        obs_max_advance_seconds=90,
        obs_fallback_advance_seconds=90,
        obs_unit_plan=relpath,
        obs_unit_plan_sha256=sha256,
    )
    values.update(overrides)
    return values


def _load(tmp_path: Path, document, **overrides) -> ObsLoopConfig:
    """Compose a config over a freshly installed synthetic plan."""

    repo_root = tmp_path / "repo"
    sha256 = _install_plan(repo_root, document)
    return ObsLoopConfig.from_values(_plan_values(PLAN_RELPATH, sha256, **overrides), repo_root)


def _slice_facts(world):
    """(record, delivered bytes) per emitted slice, in request order."""

    facts = []
    for payload in world.adapter.payloads:
        relpath = payload["media_relpath"]
        record = world.registry.lookup(world.sample_id, relpath)
        facts.append((record, (world.data_root / relpath).read_bytes()))
    return facts


def _derivation(world) -> dict:
    path = world.run_dir / f"{RUN_ID}.obs-derivation.{world.sample_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _plan_world(tmp_path, monkeypatch, *, pcm, document, sha256=None, **overrides):
    """A ``_World`` whose repo root carries ``document`` as the unit plan."""

    call = str(document["calls"][0]["sample_id"])
    units = sum(len(block["units"]) for block in document["calls"])
    raw = _plan_bytes(document)
    values = _plan_values(
        PLAN_RELPATH, sha256 or hashlib.sha256(raw).hexdigest(), **overrides
    )
    world = _World(
        tmp_path,
        monkeypatch,
        pcm=pcm,
        texts=[f"unit {index}" for index in range(1, units + 1)],
        values=values,
        sample_id=call,
    )
    path = world.repo_root / PLAN_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return world


# ---------------------------------------------------------------------------
# 1. The two keys, and the pairing rule
# ---------------------------------------------------------------------------


def test_the_keys_default_to_none_and_the_cutter_is_the_historical_one(tmp_path) -> None:
    config = ObsLoopConfig.from_values(_fixed_mode_skip_values(), tmp_path)
    assert config.unit_plan_relpath is None
    assert config.unit_plan_sha256 is None
    assert config.unit_plan is None


def test_one_key_without_the_other_is_refused(tmp_path) -> None:
    with pytest.raises(ObsLoopError, match="must be set together"):
        ObsLoopConfig.from_values(
            _fixed_mode_skip_values(obs_unit_plan=PLAN_RELPATH), tmp_path
        )
    with pytest.raises(ObsLoopError, match="must be set together"):
        ObsLoopConfig.from_values(
            _fixed_mode_skip_values(obs_unit_plan_sha256="0" * 64), tmp_path
        )


def test_a_typo_in_either_key_still_fails_closed(tmp_path) -> None:
    with pytest.raises(ObsLoopError, match="unknown obs-loop config keys"):
        ObsLoopConfig.from_values(
            _fixed_mode_skip_values(obs_unit_plans="x", obs_unit_plan_sha256="0" * 64),
            tmp_path,
        )


# ---------------------------------------------------------------------------
# 2. Every refusal, fail-closed, before a window is cut
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_a_missing_plan_is_refused(self, tmp_path) -> None:
        with pytest.raises(ObsLoopError, match="does not resolve to a file"):
            ObsLoopConfig.from_values(
                _plan_values(PLAN_RELPATH, "0" * 64), tmp_path / "repo"
            )

    def test_a_sha256_mismatch_is_refused(self, tmp_path) -> None:
        repo_root = tmp_path / "repo"
        _install_plan(repo_root, _plan_document(duration=100.0, edges=[40.0, 70.0]))
        with pytest.raises(ObsLoopError, match="but obs_unit_plan_sha256 pins"):
            ObsLoopConfig.from_values(_plan_values(PLAN_RELPATH, "0" * 64), repo_root)

    def test_a_malformed_pin_is_refused(self, tmp_path) -> None:
        repo_root = tmp_path / "repo"
        sha256 = _install_plan(repo_root, _plan_document(duration=100.0, edges=[40.0]))
        with pytest.raises(ObsLoopError, match="64-character SHA-256"):
            ObsLoopConfig.from_values(_plan_values(PLAN_RELPATH, sha256[:32]), repo_root)

    def test_a_foreign_schema_is_refused(self, tmp_path) -> None:
        document = _plan_document(duration=100.0, edges=[40.0], schema="some-other-plan-v9")
        with pytest.raises(ObsLoopError, match="declares schema"):
            _load(tmp_path, document)

    def test_a_v2_schema_plan_loads_exactly_like_a_v1_one(self, tmp_path) -> None:
        """OBS-E1 v2 (the coordinator's 2026-09-08 minimum-duration rule): the
        seam accepts EITHER schema, v1's own default default stays accepted,
        and v2's extra per-unit ``absorbed_units`` key -- unknown to this
        loader's narrow ``PlannedUnit`` view -- is harmless."""

        assert OBS_UNIT_PLAN_SCHEMA in OBS_UNIT_PLAN_SCHEMAS
        assert OBS_UNIT_PLAN_SCHEMA_V2 in OBS_UNIT_PLAN_SCHEMAS
        assert OBS_UNIT_PLAN_SCHEMA != OBS_UNIT_PLAN_SCHEMA_V2

        document = _plan_document(duration=100.0, edges=[40.0], schema=OBS_UNIT_PLAN_SCHEMA_V2)
        document["calls"][0]["units"][0]["absorbed_units"] = [
            {"start_seconds": 39.5, "end_seconds": 40.0, "speaker": "speaker_2"}
        ]
        config = _load(tmp_path, document)
        assert config.unit_plan is not None
        assert config.unit_plan.schema == OBS_UNIT_PLAN_SCHEMA_V2
        assert config.unit_plan.unit_count == 2

    def test_a_call_with_no_units_is_refused(self, tmp_path) -> None:
        document = _plan_document(duration=100.0, edges=[40.0])
        document["calls"][0]["units"] = []
        with pytest.raises(ObsLoopError, match="carries no units"):
            _load(tmp_path, document)

    def test_a_unit_outside_its_calls_audio_is_refused(self, tmp_path) -> None:
        document = _plan_document(duration=100.0, edges=[40.0])
        document["calls"][0]["units"][-1]["end_seconds"] = 140.0
        with pytest.raises(ObsLoopError, match="lies outside its call's own"):
            _load(tmp_path, document)

    def test_a_unit_longer_than_the_slot_budget_is_refused(self, tmp_path) -> None:
        # One 100-second unit against the sealed 90-second slot budget: the
        # cap the slot receipt certified, re-checked on the plan's own bytes.
        document = _plan_document(duration=100.0, edges=[])
        with pytest.raises(ObsLoopError, match="longer than the slot's audio budget"):
            _load(tmp_path, document)

    def test_a_unit_id_collision_is_refused(self, tmp_path) -> None:
        document = _plan_document(duration=100.0, edges=[40.0])
        document["calls"].append(json.loads(json.dumps(document["calls"][0])))
        with pytest.raises(ObsLoopError, match="appears twice"):
            _load(tmp_path, document)

    def test_a_minted_unit_id_is_required(self, tmp_path) -> None:
        document = _plan_document(duration=100.0, edges=[40.0])
        document["calls"][0]["units"][1]["unit_id"] = f"{SAMPLE_ID}#u9999"
        with pytest.raises(ObsLoopError, match="not the minted"):
            _load(tmp_path, document)

    def test_units_out_of_index_order_are_refused(self, tmp_path) -> None:
        document = _plan_document(duration=100.0, edges=[40.0])
        document["calls"][0]["units"].reverse()
        with pytest.raises(ObsLoopError, match="units must be listed in unit_index order"):
            _load(tmp_path, document)

    def test_a_plan_with_a_gap_does_not_tile_and_is_refused(self, tmp_path) -> None:
        document = _plan_document(duration=100.0, edges=[40.0, 70.0])
        document["calls"][0]["units"][1]["start_seconds"] = 45.0
        with pytest.raises(ObsLoopError, match="does not tile its own"):
            _load(tmp_path, document)

    def test_a_plan_that_stops_short_of_the_call_is_refused(self, tmp_path) -> None:
        document = _plan_document(duration=100.0, edges=[40.0, 70.0])
        document["calls"][0]["units"][-1]["end_seconds"] = 95.0
        with pytest.raises(ObsLoopError, match="does not tile its own"):
            _load(tmp_path, document)

    def test_a_roster_call_the_plan_does_not_cover_is_refused(self, tmp_path) -> None:
        config = _load(tmp_path, _plan_document(duration=100.0, edges=[40.0]))
        with pytest.raises(ObsLoopError, match="has no block for roster sample"):
            config.unit_plan.units_for("9999999", 100.0)

    def test_a_plan_cut_against_different_audio_is_refused(self, tmp_path) -> None:
        config = _load(tmp_path, _plan_document(duration=100.0, edges=[40.0]))
        with pytest.raises(ObsLoopError, match="the decode is the authority"):
            config.unit_plan.units_for(SAMPLE_ID, 100.001)
        # The runtime decode itself still resolves, to the digit.
        assert len(config.unit_plan.units_for(SAMPLE_ID, 100.0)) == 2

    @pytest.mark.parametrize(
        "override, message",
        [
            ({"obs_boundary_mode": "model", "obs_boundary_prompt": "probes/x.txt"},
             "requires obs_boundary_mode 'fixed'"),
            ({"obs_condition_tail_chars": 400}, "requires obs_condition_tail_chars 0"),
            ({"obs_vad_trim_min_seconds": 5.0}, "requires obs_vad_trim_min_seconds 0"),
        ],
        ids=["model-boundary", "rolling-tail", "vad-trim"],
    )
    def test_the_three_incompatible_knobs_are_refused(
        self, tmp_path, override, message
    ) -> None:
        with pytest.raises(ObsLoopError, match=message):
            _load(tmp_path, _plan_document(duration=100.0, edges=[40.0]), **override)


def test_slice_batching_stays_legal_under_a_plan(tmp_path) -> None:
    """The plan fixes every position before the first contact, which IS the
    independence condition ``obs_batch_slices > 1`` already requires."""

    config = _load(
        tmp_path, _plan_document(duration=100.0, edges=[40.0, 70.0]), obs_batch_slices=8
    )
    assert config.batch_slices == 8
    assert config.unit_plan is not None
    assert config.unit_plan.unit_count == 3


# ---------------------------------------------------------------------------
# 3. The cut: units in order, on both executor paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("batch_slices", [1, 4], ids=["sequential", "parallel"])
def test_the_units_are_consumed_in_order_on_both_executor_paths(
    tmp_path, monkeypatch, batch_slices
) -> None:
    edges = [17.5, 40.0, 61.25]
    document = _plan_document(duration=100.0, edges=edges)
    world = _plan_world(
        tmp_path,
        monkeypatch,
        pcm=_noise(100.0),
        document=document,
        obs_batch_slices=batch_slices,
    )
    world.run()

    planned = document["calls"][0]["units"]
    facts = _slice_facts(world)
    assert len(facts) == len(planned) == 4

    payloads = _obs_payloads(world)
    for index, (unit, (record, _bytes)) in enumerate(zip(planned, facts)):
        # The span is the PLAN's, to the frame, and audio_seconds still equals
        # it -- SliceRegistry.register's own assertion, and the rail that
        # would refuse a seam that silently moved a cut.
        assert record.start_seconds == pytest.approx(unit["start_seconds"], abs=1e-9)
        assert record.end_seconds == pytest.approx(unit["end_seconds"], abs=1e-9)
        assert record.audio_seconds == pytest.approx(
            unit["duration_seconds"], abs=1e-9
        )
        assert record.audio_seconds == record.end_seconds - record.start_seconds
        # iteration = unit_index - 1, so relpaths and request ids keep their
        # historical i%04d shape.
        assert record.iteration == unit["unit_index"] - 1
        assert record.media_relpath.endswith("i%04d.wav" % (unit["unit_index"] - 1))
        payload = payloads[f"req-0001-i{index:04d}/obs"]
        assert payload["obs_unit_id"] == unit["unit_id"]
        assert payload["obs_unit_speaker"] == unit["speaker"]
        assert payload["obs_unit_end_cut"] == unit["end_cut"]
        assert payload["obs_window_start_seconds"] == record.start_seconds
        assert payload["obs_window_end_seconds"] == record.end_seconds
        assert payload["obs_final_window"] is (index == len(planned) - 1)


@pytest.mark.parametrize("batch_slices", [1, 4], ids=["sequential", "parallel"])
def test_the_tail_rides_on_the_unit_cut_exactly_once(
    tmp_path, monkeypatch, batch_slices
) -> None:
    document = _plan_document(duration=100.0, edges=[17.5, 40.0, 61.25])
    pcm = _noise(100.0)
    plain = _plan_world(
        tmp_path / "plain",
        monkeypatch,
        pcm=pcm,
        document=document,
        obs_batch_slices=batch_slices,
    )
    plain.run()
    tailed = _plan_world(
        tmp_path / "tailed",
        monkeypatch,
        pcm=pcm,
        document=document,
        obs_batch_slices=batch_slices,
        obs_slice_tail_silence_seconds=2.0,
    )
    tailed.run()

    for (plain_record, plain_bytes), (tailed_record, tailed_bytes) in zip(
        _slice_facts(plain), _slice_facts(tailed)
    ):
        # The unit cut is identical; only the delivered bytes grow.
        assert tailed_record.start_seconds == plain_record.start_seconds
        assert tailed_record.end_seconds == plain_record.end_seconds
        assert tailed_record.audio_seconds == plain_record.audio_seconds
        assert tailed_bytes == write_wav_bytes(
            append_tail_silence(array("h", plain_bytes[44:]), RATE, 2.0), RATE
        )
        assert tailed_record.bytes == plain_record.bytes + 2 * 32000
        # ONE tail, declared once, chained to the raw unit cut. There is no
        # second tail implementation, and the plan's own tail_silence_seconds
        # rule is NOT re-applied by the cutter.
        assert tailed_record.preprocess == (f"{SLICE_TAIL_SILENCE_TRANSFORM}-2s",)
        assert tailed_record.pre_sha256 == plain_record.sha256


def test_the_derivation_receipt_names_the_plan_it_was_cut_by(
    tmp_path, monkeypatch
) -> None:
    document = _plan_document(duration=100.0, edges=[40.0])
    world = _plan_world(tmp_path, monkeypatch, pcm=_noise(100.0), document=document)
    world.run()
    receipt = _derivation(world)
    assert receipt["boundary_mode"] == OBS_UNIT_PLAN_BOUNDARY_MODE
    assert receipt["unit_plan_path"] == PLAN_RELPATH
    assert receipt["unit_plan_sha256"] == hashlib.sha256(_plan_bytes(document)).hexdigest()
    assert len(receipt["slices"]) == 2


# ---------------------------------------------------------------------------
# 4. Null keys move nothing -- the synthetic half
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("batch_slices", [1, 4], ids=["sequential", "parallel"])
def test_null_keys_are_byte_identical_to_the_historical_path(
    tmp_path, monkeypatch, batch_slices
) -> None:
    """The keys ABSENT and the keys explicitly ``null`` must produce the same
    bytes, the same records, the same trace and the same outcome -- otherwise
    no sealed Earnings run is reproducible on this tree."""

    pcm = _noise(240.0)
    texts = [f"span {index}" for index in range(8)]
    absent = _World(
        tmp_path / "absent",
        monkeypatch,
        pcm=pcm,
        texts=list(texts),
        values=_fixed_mode_skip_values(
            obs_buffer_seconds=90,
            obs_min_advance_seconds=90,
            obs_max_advance_seconds=90,
            obs_fallback_advance_seconds=90,
            obs_batch_slices=batch_slices,
        ),
    )
    absent_outcome = absent.run()
    explicit = _World(
        tmp_path / "explicit",
        monkeypatch,
        pcm=pcm,
        texts=list(texts),
        values=_fixed_mode_skip_values(
            obs_buffer_seconds=90,
            obs_min_advance_seconds=90,
            obs_max_advance_seconds=90,
            obs_fallback_advance_seconds=90,
            obs_batch_slices=batch_slices,
            obs_unit_plan=None,
            obs_unit_plan_sha256=None,
        ),
    )
    explicit_outcome = explicit.run()

    absent_facts = _slice_facts(absent)
    explicit_facts = _slice_facts(explicit)
    assert len(absent_facts) == len(explicit_facts) == 3
    for (record_a, bytes_a), (record_b, bytes_b) in zip(absent_facts, explicit_facts):
        assert bytes_a == bytes_b
        assert record_a.trace_view() == record_b.trace_view()
    assert _obs_payloads(absent) == _obs_payloads(explicit)
    assert _derivation(absent) == _derivation(explicit)
    assert _derivation(absent)["unit_plan_path"] is None
    assert _derivation(absent)["unit_plan_sha256"] is None
    assert _derivation(absent)["boundary_mode"] == "fixed"
    assert absent_outcome.response_sha256 == explicit_outcome.response_sha256
    assert absent_outcome.request_sha256 == explicit_outcome.request_sha256
    # No unit field leaks onto a fixed-window record.
    for payload in _obs_payloads(absent).values():
        assert "obs_unit_id" not in payload
        assert "obs_unit_speaker" not in payload
        assert "obs_unit_end_cut" not in payload


# ---------------------------------------------------------------------------
# 5. The other executor consumes the plan through the same functions
# ---------------------------------------------------------------------------


def test_the_ojw_executor_cuts_the_plan_units_not_the_clock(
    tmp_path, monkeypatch
) -> None:
    """Drift #1 of the 2026-09-08 openJiuwen assessment, closed the same day.

    ``ObsSampleState.window_frames`` used to be clock-derived by construction,
    so a plan reaching that executor would have been silently ignored and the
    two executors would have delivered different media for the same config;
    the refusal that stood in its place was an honest stop-gap, not a design.
    The port consumes the plan through the SAME ``UnitPlan.units_for`` the
    plain policy calls, and the byte-level proof that the two executors agree
    is the ``unit-plan`` scenario of ``tests/unit/test_obs_loop_ojw.py``'s
    equivalence suite; this test pins the state the port introduces.
    """

    policy = pytest.importorskip(
        "speech_aware_evidence_acquisition.reproduction.ojw.policy"
    )
    document = _plan_document(duration=100.0, edges=[40.0])
    world = _plan_world(tmp_path, monkeypatch, pcm=_noise(100.0), document=document)
    config = ObsLoopConfig.from_values(
        world.ctx.extras["config_values"], world.repo_root
    )
    state = policy._prepare_state(world.ctx, config)

    assert state.plan_units is not None
    assert [unit.unit_index for unit in state.plan_units] == [1, 2]
    assert [unit.end_seconds for unit in state.plan_units] == [40.0, 100.0]
    # The plan's own length is the iteration bound; the clock-derived one
    # describes a cutter that is not running.
    assert state.max_iterations == len(state.plan_units) + 8
    # The first window is the first UNIT, not the first 90 clock-seconds.
    assert state.window_frames() == (0, int(round(40.0 * state.rate)))
    # An exhausted plan is a degenerate window, which is how the loop exits.
    state.iteration = len(state.plan_units)
    assert state.window_frames() == (0, 0)
    assert state.should_continue() is False
    assert state.unit_for(0) is state.plan_units[0]


def test_the_ojw_executor_refuses_a_roster_call_the_plan_does_not_cover(
    tmp_path, monkeypatch
) -> None:
    """The refusals stay where they were: ``units_for`` is called once per
    sample on BOTH executors, so a call the plan has no block for stops the
    ojw path with the identical message, before the parent is decoded."""

    policy = pytest.importorskip(
        "speech_aware_evidence_acquisition.reproduction.ojw.policy"
    )
    document = _plan_document(sample_id="other-call", duration=100.0, edges=[40.0])
    world = _plan_world(tmp_path, monkeypatch, pcm=_noise(100.0), document=document)
    world.ctx.sample = replace(world.ctx.sample, sample_id="uncovered-call")
    config = ObsLoopConfig.from_values(
        world.ctx.extras["config_values"], world.repo_root
    )
    with pytest.raises(ObsLoopError, match="has no block for roster sample"):
        policy._prepare_state(world.ctx, config)


# ---------------------------------------------------------------------------
# 6. THE FALSIFIER: the committed window hashes of a real sealed call
# ---------------------------------------------------------------------------


def _data_root() -> Path:
    from speech_aware_evidence_acquisition.data.lock import data_root

    try:
        return data_root()
    except Exception as error:  # noqa: BLE001 -- environment, not behaviour
        pytest.skip(f"$SPEECHRL_DATA_DIR is not resolvable here: {error}")


def _read_wav_16k_mono(path: Path) -> array:
    with wave.open(str(path), "rb") as handle:
        assert (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) == (
            16000,
            1,
            2,
        ), f"{path} is not 16 kHz mono int16"
        return array("h", handle.readframes(handle.getnframes()))


def _sealed_call_windows() -> tuple[list[dict], array]:
    """The sealed 90-second window rows of :data:`REAL_CALL`, in window order,
    and the call PCM their concatenation reconstructs.

    The sealed slices ARE the comparator's own cut of that call, so their
    concatenation is exactly the PCM ``decode_parent_pcm`` produced for it --
    which is what makes replaying them through the cutter a byte-level oracle
    rather than a re-decode.
    """

    if not TS2_ROSTER.is_file():
        pytest.skip(f"the sealed @ts2 roster receipt is absent ({TS2_ROSTER})")
    receipt = json.loads(TS2_ROSTER.read_text(encoding="utf-8"))
    rows = sorted(
        (row for row in receipt["items"] if str(row["call_sample_id"]) == REAL_CALL),
        key=lambda row: int(row["obs_iteration"]),
    )
    if not rows:
        pytest.skip(f"the sealed roster carries no window for call {REAL_CALL}")
    root = _data_root()
    first = root / str(rows[0]["source_media_relpath"])
    if not first.is_file():
        pytest.skip(
            "the sealed SAEA-E21-FULL44-DIRECT-BASELINE-V2 obs-slices are absent on "
            f"this machine ({first})"
        )
    pcm = array("h")
    for row in rows:
        pcm.extend(_read_wav_16k_mono(root / str(row["source_media_relpath"])))
    return rows, pcm


def test_null_keys_reproduce_every_committed_window_hash_of_a_sealed_call(
    tmp_path, monkeypatch
) -> None:
    """The byte-identity proof, against COMMITTED hashes rather than against a
    second in-memory copy: with the seam present and its keys null, the cutter
    re-cuts one real call into exactly the sealed 90-second windows the
    comparator itself sent, hash for hash."""

    rows, pcm = _sealed_call_windows()
    world = _World(
        tmp_path,
        monkeypatch,
        pcm=pcm,
        texts=[f"window {index}" for index in range(len(rows))],
        values=_fixed_mode_skip_values(
            obs_buffer_seconds=90,
            obs_min_advance_seconds=90,
            obs_max_advance_seconds=90,
            obs_fallback_advance_seconds=90,
            obs_batch_slices=4,
            obs_unit_plan=None,
            obs_unit_plan_sha256=None,
        ),
        sample_id=REAL_CALL,
    )
    world.run()
    facts = _slice_facts(world)
    assert len(facts) == len(rows)
    mismatched = [
        str(row["source_sample_id"])
        for row, (record, _bytes) in zip(rows, facts)
        if record.sha256 != str(row["source_audio_sha256"])
        or record.start_seconds != float(row["window_start_seconds"])
        or record.end_seconds != float(row["window_end_seconds"])
        or record.preprocess != ()
    ]
    assert mismatched == []


def test_the_plan_recuts_the_same_sealed_call_and_the_tail_rides_on_top(
    tmp_path, monkeypatch
) -> None:
    """Section 8.6 of the preregistration, on real bytes: the plan's units
    reproduce their own declared spans, concatenating the delivered slices with
    the 2.0-second tails removed reproduces the call's own audio exactly (which
    holds if and only if the units tile and the cut is byte-exact), and
    ``pre_sha256`` chains to the untailed cut."""

    if not REAL_PLAN.is_file():
        pytest.skip(f"the committed unit plan is absent ({REAL_PLAN})")
    _rows, pcm = _sealed_call_windows()
    document = json.loads(REAL_PLAN.read_text(encoding="utf-8"))
    block = next(
        call for call in document["calls"] if str(call["sample_id"]) == REAL_CALL
    )
    assert block["decoded_duration_seconds"] == pytest.approx(
        len(pcm) / RATE, abs=1e-6
    ), "the committed plan was cut against different audio than the sealed slices"

    units = block["units"]
    world = _World(
        tmp_path,
        monkeypatch,
        pcm=pcm,
        texts=[f"unit {index}" for index in range(len(units))],
        values=_plan_values(
            REAL_PLAN_RELPATH,
            hashlib.sha256(REAL_PLAN.read_bytes()).hexdigest(),
            obs_batch_slices=4,
            obs_slice_tail_silence_seconds=2.0,
        ),
        sample_id=REAL_CALL,
    )
    # The plan the cutter loads is the COMMITTED file, copied byte for byte
    # into this world's repo root so the pin is the real one.
    installed = world.repo_root / REAL_PLAN_RELPATH
    installed.parent.mkdir(parents=True, exist_ok=True)
    installed.write_bytes(REAL_PLAN.read_bytes())
    world.run()

    facts = _slice_facts(world)
    assert len(facts) == len(units)
    rebuilt = array("h")
    for unit, (record, delivered) in zip(units, facts):
        assert record.start_seconds == pytest.approx(unit["start_seconds"], abs=1e-6)
        assert record.end_seconds == pytest.approx(unit["end_seconds"], abs=1e-6)
        assert record.audio_seconds == pytest.approx(
            unit["duration_seconds"], abs=1e-6
        )
        assert record.preprocess == (f"{SLICE_TAIL_SILENCE_TRANSFORM}-2s",)
        untailed = array("h", delivered[44:])[:-TAIL_SAMPLES]
        assert record.pre_sha256 == hashlib.sha256(
            write_wav_bytes(untailed, RATE)
        ).hexdigest()
        rebuilt.extend(untailed)
    assert rebuilt == pcm
    # The COMMITTED oracle, not a second in-memory copy: the sealed
    # `saea-diarization-v1` inputs receipt records this call's whole decoded
    # audio as a 16 kHz mono WAV hash. Concatenating the delivered unit slices
    # with the tails removed must reproduce it exactly, which holds if and only
    # if the units tile and every cut is byte-exact.
    if DIARIZATION_INPUTS.is_file():
        inputs = json.loads(DIARIZATION_INPUTS.read_text(encoding="utf-8"))
        sealed = next(
            call
            for call in inputs["calls"]
            if str(call["sample_id"]) == REAL_CALL
        )
        assert (
            hashlib.sha256(write_wav_bytes(rebuilt, RATE)).hexdigest()
            == str(sealed["audio_sha256"])
        )
