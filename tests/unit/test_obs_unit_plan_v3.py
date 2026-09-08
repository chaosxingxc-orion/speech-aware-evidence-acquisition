"""The OBS-E1b seam: a v3 plan's units are DELIVERED with context and STITCHED
by ownership.

Four things are proved here, all on synthetic worlds and none of them touching
a model, a socket or a sealed artifact.

1. **A v1 or v2 plan is byte-identical to what it was.** The context branch is
   key-gated on the plan's own schema, so a plan without context bounds cuts
   its turns, stitches its responses and writes the same derivation receipt it
   always did -- asserted here by running the SAME world twice, once through a
   v2 plan and once through the same plan re-labelled v3 with context bounds
   that equal its turns.
2. **A v3 plan cuts the delivered span**, so the ``SliceRecord`` carries the
   context bounds, ``audio_seconds`` still equals the span (the rail that
   would refuse a seam which moved a cut), and the OBS record carries the TURN
   bounds beside them.
3. **The stitch is the ownership stitch**: each unit's OBS record declares
   ``obs_delivered_text`` and the four ownership fields, the sample's outcome
   text is the join of those, and the derivation receipt names the protocol.
4. **Every new refusal fires fail-closed, before a window is cut**: context
   outside the call, context that does not cover its own turn, a delivered cut
   under the minimum, a delivered cut over the slot's budget, context bounds on
   a non-v3 plan, a boundary outside the audio both units received, and a
   context-bearing plan on the sequential path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    OBS_UNIT_PLAN_SCHEMA_V2,
    OBS_UNIT_PLAN_SCHEMA_V3,
    ObsAgentLoopPolicy,
    ObsLoopConfig,
    ObsLoopError,
)
from speech_aware_evidence_acquisition.reproduction.obs_ownership import (
    OWNERSHIP_PROTOCOL,
    RULE_ANCHOR,
    RULE_NO_OVERLAP,
)

from test_obs_loop_policy import (  # noqa: E402
    RATE,
    RUN_ID,
    SAMPLE_ID,
    _World,
    _noise,
    _obs_payloads,
)
from test_obs_unit_plan import (  # noqa: E402
    PLAN_RELPATH,
    _load,
    _plan_bytes,
    _plan_document,
    _plan_values,
    _plan_world,
)

DURATION = 120.0
EDGES = [40.0, 80.0]
MARGIN = 5.0


def _with_context(document: dict, *, margin: float = MARGIN, duration: float = DURATION) -> dict:
    """The same plan, relabelled v3, with a symmetric margin on every unit."""

    document = json.loads(json.dumps(document))
    document["schema"] = OBS_UNIT_PLAN_SCHEMA_V3
    for block in document["calls"]:
        span = float(block["decoded_duration_seconds"])
        for unit in block["units"]:
            low = max(0.0, float(unit["start_seconds"]) - margin)
            high = min(span, float(unit["end_seconds"]) + margin)
            unit["context_start_seconds"] = low
            unit["context_end_seconds"] = high
            unit["delivered_cut_seconds"] = high - low
            unit["delivered_seconds"] = high - low + 2.0
    return document


def _v2() -> dict:
    return _plan_document(duration=DURATION, edges=EDGES, schema=OBS_UNIT_PLAN_SCHEMA_V2)


def _v3(**kwargs) -> dict:
    return _with_context(_v2(), **kwargs)


def _run(tmp_path, monkeypatch, document, **overrides):
    world = _plan_world(
        tmp_path,
        monkeypatch,
        pcm=_noise(DURATION),
        document=document,
        obs_batch_slices=overrides.pop("obs_batch_slices", 3),
        **overrides,
    )
    outcome = ObsAgentLoopPolicy().run_sample(world.ctx)
    return world, outcome


def _derivation(world) -> dict:
    path = world.run_dir / f"{RUN_ID}.obs-derivation.{world.sample_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. A plan without context bounds is untouched
# ---------------------------------------------------------------------------


class TestByteIdentityOfV2:
    def test_a_v2_plan_still_cuts_its_turns_and_stitches_its_responses(
        self, tmp_path, monkeypatch
    ):
        world, outcome = _run(tmp_path / "v2", monkeypatch, _v2())
        payloads = list(_obs_payloads(world).values())
        assert len(payloads) == 3
        assert [
            (record["obs_window_start_seconds"], record["obs_window_end_seconds"])
            for record in payloads
        ] == [(0.0, 40.0), (40.0, 80.0), (80.0, 120.0)]
        assert all("obs_delivered_text" not in record for record in payloads)
        assert all("obs_ownership_protocol" not in record for record in payloads)
        assert all("obs_unit_turn_start_seconds" not in record for record in payloads)
        assert outcome.text == "unit 1 unit 2 unit 3"
        assert _derivation(world)["text_ownership"] is None

    def test_a_v3_plan_whose_context_equals_its_turns_cuts_the_same_audio(
        self, tmp_path, monkeypatch
    ):
        world, outcome = _run(
            tmp_path / "v3zero", monkeypatch, _v3(margin=0.0)
        )
        payloads = list(_obs_payloads(world).values())
        assert [
            (record["obs_window_start_seconds"], record["obs_window_end_seconds"])
            for record in payloads
        ] == [(0.0, 40.0), (40.0, 80.0), (80.0, 120.0)]
        # Every boundary takes the no-overlap branch, which is the v1/v2 rule.
        assert [record["obs_ownership_left_rule"] for record in payloads[1:]] == [
            RULE_NO_OVERLAP,
            RULE_NO_OVERLAP,
        ]
        assert outcome.text == "unit 1 unit 2 unit 3"


# ---------------------------------------------------------------------------
# 2 and 3. A v3 plan delivers context and stitches ownership
# ---------------------------------------------------------------------------


class TestContextDelivery:
    def test_the_cut_is_the_delivered_span_and_the_turn_rides_beside_it(
        self, tmp_path, monkeypatch
    ):
        world, _outcome = _run(tmp_path / "ctx", monkeypatch, _v3())
        payloads = list(_obs_payloads(world).values())
        assert [
            (record["obs_window_start_seconds"], record["obs_window_end_seconds"])
            for record in payloads
        ] == [(0.0, 45.0), (35.0, 85.0), (75.0, 120.0)]
        assert [
            (record["obs_unit_turn_start_seconds"], record["obs_unit_turn_end_seconds"])
            for record in payloads
        ] == [(0.0, 40.0), (40.0, 80.0), (80.0, 120.0)]
        assert [record["obs_unit_context_left_seconds"] for record in payloads] == [
            0.0,
            5.0,
            5.0,
        ]
        for payload in payloads:
            relpath = payload["obs_slice_relpath"]
            record = world.registry.lookup(world.sample_id, relpath)
            assert record.start_seconds == payload["obs_window_start_seconds"]
            assert record.end_seconds == payload["obs_window_end_seconds"]
            assert record.audio_seconds == pytest.approx(
                record.end_seconds - record.start_seconds
            )

    def test_the_last_unit_is_cut_even_when_an_earlier_cut_reached_the_call_end(
        self, tmp_path, monkeypatch
    ):
        """Regression, caught by the OBS-E1b wire check on calls 4387332 and
        4392809: a context-bearing unit's cut runs PAST its turn, so the
        cursor can reach the call's end while units remain. A clock loop
        condition dropped the last one silently -- 49 contacts for 50 planned
        units, and a falsifier that failed only afterwards. The plan's own
        length is the loop bound now."""

        # Unit 3 ends at the call end, so unit 2's cut (80 + 5) already
        # reaches past where a clock condition would stop.
        world, outcome = _run(tmp_path / "last", monkeypatch, _v3())
        payloads = list(_obs_payloads(world).values())
        assert len(payloads) == 3
        assert len(world.adapter.payloads) == 3
        assert payloads[-1]["obs_final_window"] is True
        assert payloads[-1]["obs_unit_turn_end_seconds"] == DURATION
        assert outcome.text.split()[-1] == "3"

    def test_every_unit_declares_what_it_delivered_and_the_run_stitches_that(
        self, tmp_path, monkeypatch
    ):
        world, outcome = _run(tmp_path / "own", monkeypatch, _v3())
        payloads = list(_obs_payloads(world).values())
        for payload in payloads:
            assert payload["obs_ownership_protocol"] == OWNERSHIP_PROTOCOL
            assert "obs_delivered_text" in payload
            assert payload["obs_ownership_keep_from"] <= payload["obs_ownership_keep_to"]
        delivered = [payload["obs_delivered_text"] for payload in payloads]
        assert outcome.text == " ".join(piece for piece in delivered if piece)
        assert _derivation(world)["text_ownership"] == OWNERSHIP_PROTOCOL

    def test_an_agreeing_overlap_anchors_and_gives_each_unit_its_own_words(
        self, tmp_path, monkeypatch
    ):
        # The scripted responses are built so unit k's tail repeats unit k+1's
        # head, which is what a real context margin produces.
        import hashlib

        document = _v3()
        raw = _plan_bytes(document)
        world = _World(
            tmp_path / "anchor",
            monkeypatch,
            pcm=_noise(DURATION),
            texts=[
                "alpha bravo charlie delta echo foxtrot",
                "delta echo foxtrot golf hotel india",
                "golf hotel india juliett kilo lima",
            ],
            values=_plan_values(
                PLAN_RELPATH, hashlib.sha256(raw).hexdigest(), obs_batch_slices=3
            ),
            sample_id=SAMPLE_ID,
        )
        path = world.repo_root / PLAN_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        outcome = ObsAgentLoopPolicy().run_sample(world.ctx)
        payloads = list(_obs_payloads(world).values())
        assert {record["obs_ownership_left_rule"] for record in payloads[1:]} == {
            RULE_ANCHOR
        }
        # Whatever the anchor chose, every spoken word appears exactly once.
        words = outcome.text.split()
        assert words == sorted(set(words), key=words.index)
        assert "alpha" in words and "lima" in words


# ---------------------------------------------------------------------------
# 4. The refusals
# ---------------------------------------------------------------------------


class TestRefusals:
    def _mutate(self, tmp_path, mutate, **overrides):
        document = _v3()
        mutate(document)
        return _load(tmp_path, document, obs_batch_slices=3, **overrides)

    def test_context_outside_the_call_is_refused(self, tmp_path):
        def mutate(document):
            document["calls"][0]["units"][0]["context_start_seconds"] = -1.0

        with pytest.raises(ObsLoopError, match="outside its call"):
            self._mutate(tmp_path, mutate)

    def test_context_that_does_not_cover_its_own_turn_is_refused(self, tmp_path):
        def mutate(document):
            document["calls"][0]["units"][1]["context_start_seconds"] = 41.0

        with pytest.raises(ObsLoopError, match="does not cover its own turn"):
            self._mutate(tmp_path, mutate)

    def test_a_delivered_cut_under_the_minimum_is_refused(self, tmp_path):
        def mutate(document):
            unit = document["calls"][0]["units"][1]
            unit["start_seconds"] = 40.0
            unit["end_seconds"] = 42.0
            unit["context_start_seconds"] = 40.0
            unit["context_end_seconds"] = 42.0
            following = document["calls"][0]["units"][2]
            following["start_seconds"] = 42.0
            following["context_start_seconds"] = 37.0

        with pytest.raises(ObsLoopError, match="minimum a context-bearing plan"):
            self._mutate(tmp_path, mutate)

    def test_a_delivered_cut_over_the_slot_budget_is_refused(self, tmp_path):
        # Every turn is well under 90 s; only the DELIVERED span breaks it.
        def mutate(document):
            unit = document["calls"][0]["units"][1]
            unit["context_start_seconds"] = 0.0
            unit["context_end_seconds"] = 95.0

        with pytest.raises(ObsLoopError, match="longer than the slot's audio"):
            self._mutate(tmp_path, mutate, obs_buffer_seconds=90)

    def test_context_bounds_on_a_v2_plan_are_refused(self, tmp_path):
        document = _with_context(_v2())
        document["schema"] = OBS_UNIT_PLAN_SCHEMA_V2
        with pytest.raises(ObsLoopError, match="carries context bounds"):
            _load(tmp_path, document, obs_batch_slices=3)

    def test_every_boundary_of_the_committed_plan_is_inside_both_units_audio(self):
        """The property the ownership stitch needs, on the real plan.

        It is DERIVED, not independent: a unit's context covers its own turn,
        so ``context_start_{k+1} <= boundary <= context_end_k`` always holds
        once the per-unit checks pass -- which is why the loader's own
        ``assert_context`` can never reach this clause on a plan that got past
        them, and why it is asserted here on the committed bytes instead of
        provoked with a synthetic violation that cannot be constructed."""

        repo_root = Path(__file__).resolve().parents[2]
        document = json.loads(
            (repo_root / "docs/receipts/obs/e21-speaker-turn-units-v3.json").read_text(
                encoding="utf-8"
            )
        )
        boundaries = 0
        for block in document["calls"]:
            units = block["units"]
            for left, right in zip(units, units[1:]):
                boundaries += 1
                low = max(left["context_start_seconds"], right["context_start_seconds"])
                high = min(left["context_end_seconds"], right["context_end_seconds"])
                assert low - 1e-6 <= left["end_seconds"] <= high + 1e-6
        assert boundaries == 5122 - 44

    def test_a_context_bearing_plan_on_the_sequential_path_is_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="requires obs_batch_slices > 1"):
            _load(tmp_path, _v3(), obs_batch_slices=1)

    def test_a_v3_plan_is_an_accepted_schema(self, tmp_path):
        config = _load(tmp_path, _v3(), obs_batch_slices=3)
        assert config.unit_plan is not None
        assert config.unit_plan.schema == OBS_UNIT_PLAN_SCHEMA_V3
        assert config.unit_plan.has_context is True
        units = config.unit_plan.units_for(SAMPLE_ID, DURATION)
        assert [unit.cut_start_seconds for unit in units] == [0.0, 35.0, 75.0]
        assert [unit.cut_end_seconds for unit in units] == [45.0, 85.0, 120.0]
        assert all(unit.has_context for unit in units)


def test_the_committed_v3_plan_loads_and_declares_context(tmp_path) -> None:
    """The real plan, at its committed bytes, through the real loader."""

    import hashlib

    repo_root = Path(__file__).resolve().parents[2]
    relpath = "docs/receipts/obs/e21-speaker-turn-units-v3.json"
    raw = (repo_root / relpath).read_bytes()
    from test_obs_unit_plan import _plan_values  # noqa: PLC0415

    values = _plan_values(relpath, hashlib.sha256(raw).hexdigest(), obs_batch_slices=8)
    config = ObsLoopConfig.from_values(values, repo_root)
    assert config.unit_plan is not None
    assert config.unit_plan.schema == OBS_UNIT_PLAN_SCHEMA_V3
    assert config.unit_plan.has_context is True
    assert config.unit_plan.unit_count == 5122
    assert len(config.unit_plan.units_by_sample) == 44
    assert all(
        unit.has_context
        for units in config.unit_plan.units_by_sample.values()
        for unit in units
    )


def test_the_plan_relpath_constant_is_the_one_the_helpers_install() -> None:
    assert PLAN_RELPATH.endswith(".json")
    assert RATE == 16000
