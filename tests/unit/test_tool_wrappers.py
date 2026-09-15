"""Byte equivalence: the wrapped path IS the direct path (WAVE W3, 2026-09-08).

One test per catalog tool. Each builds a synthetic input, calls the existing
repository function DIRECTLY, calls the registered wrapper with the same
arguments, and asserts the two results are equal object for object and byte
for byte. That equality is the whole claim of the catalog: registering a
function as a tool changes who decides to call it, never what it does.

Where a sealed receipt ships in this repository, the same equivalence is
re-run on the receipt's own inputs -- the SLURP legal-intent inventory comes
out of the committed projection-v2 receipt rather than being invented here.

The diarization tool never runs a model: its Sortformer pass is a separate,
already-ledgered batch contact and nothing in this module can reach it. It is
exercised through the DRY RUN and through a synthetic sealed artifact only,
which the last test in its group asserts by inspecting the wrapper module's
imports.

Zero model contacts, zero GPU, zero network (the prompt-fit client's socket
is replaced by an in-process fake connection, so the real ``request_json``
body still runs end to end).
"""

from __future__ import annotations

import hashlib
import inspect
import io
import json
import wave
from array import array
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.e21_speaker_turn_units import (
    Pause,
    plan_units_v2,
)
from speech_aware_evidence_acquisition.core.flag_sources import roster_band_flags
from speech_aware_evidence_acquisition.core.repair_alignment import accept_entity_repair
from speech_aware_evidence_acquisition.core.replay_signals import flag_spans
from speech_aware_evidence_acquisition.rails import tools
from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_vectors
from speech_aware_evidence_acquisition.rails.tool_wrappers import (
    diarization as diarization_wrapper,
)
from speech_aware_evidence_acquisition.rails.tool_wrappers import (
    flagged_spans as flagged_spans_wrapper,
)
from speech_aware_evidence_acquisition.rails.tool_wrappers import (
    prompt_fit_tokens as prompt_fit_wrapper,
)
from speech_aware_evidence_acquisition.reproduction.diarization import (
    SpeakerSegment,
    load_diarization,
)
from speech_aware_evidence_acquisition.reproduction.obs_audio import encode_slice
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    legal_intent_inventory,
    project_slu_label_v2,
)

EXPECTED_TOOL_IDS = (
    "saea-tool-diarization-artifact-v1",
    "saea-tool-flagged-spans-v1",
    "saea-tool-legal-label-projection-v2",
    "saea-tool-prompt-fit-tokens-v1",
    "saea-tool-repair-alignment-v1",
    "saea-tool-sealed-vector-query-v1",
    "saea-tool-slice-encode-v1",
    "saea-tool-speaker-turn-units-v2",
)


# ---------------------------------------------------------------------------
# The catalog as registered.
# ---------------------------------------------------------------------------


def test_catalog_retains_legacy_wrappers_and_explicit_registered_actions():
    """Retain eight legacy wrappers, eighteen A2T renderers and explicit phase actions."""

    registered = tuple(tools.catalog_ids())
    assert set(EXPECTED_TOOL_IDS) <= set(registered)
    actions = {
        "saea-tool-task-contract-v1",
        "saea-tool-phase-knowledge-v1",
        "saea-tool-knowledge-target-lookup-v1",
        "saea-tool-corrective-memory-v1",
        "saea-tool-prepared-speech-observation-v1",
        "saea-tool-live-speech-observation-v1",
        "saea-tool-live-speech-span-v1",
        "saea-tool-candidate-contract-lookup-v1",
    }
    assert actions <= set(registered)
    others = set(registered) - set(EXPECTED_TOOL_IDS) - actions
    assert all(tool_id.startswith("saea-tool-a2t-") for tool_id in others), sorted(others)
    assert len(others) == 18


def test_every_registered_manifest_is_system_invoked_and_complete():
    for tool_id in tools.catalog_ids():
        entry = tools.resolve_tool(tool_id)
        manifest = entry.manifest
        assert manifest.system_invoked is True
        assert manifest.tool_id == tool_id
        assert manifest.axis in tools.TOOL_AXES
        assert manifest.cost_class in tools.COST_CLASSES
        assert manifest.ledger_row_type in tools.LEDGER_ROW_TYPES
        manifest.validate()
        assert callable(entry.body)


def test_every_registered_manifest_pins_its_wrapped_source():
    for tool_id in tools.catalog_ids():
        manifest = tools.resolve_tool(tool_id).manifest
        target = tools.load_source_target(manifest.source_ref)
        expected = hashlib.sha256(inspect.getsource(target).encode("utf-8")).hexdigest()
        assert manifest.pinned_sha256 == expected, tool_id
        tools.assert_pinned_hash(manifest)


def test_only_the_slice_encoder_changes_bytes():
    """One byte-changing tool, and it is the one that names a derivation
    record. Every other manifest declares neither."""

    changing = [
        tool_id
        for tool_id in tools.catalog_ids()
        if tools.resolve_tool(tool_id).manifest.changes_bytes
    ]
    assert changing == ["saea-tool-slice-encode-v1"]
    for tool_id in tools.catalog_ids():
        manifest = tools.resolve_tool(tool_id).manifest
        assert (manifest.derivation_record is not None) == manifest.changes_bytes


def test_no_manifest_claims_a_model_contact():
    """The frozen core is reached through the single door and is never a
    tool, so no catalog entry may cost a generation."""

    for tool_id in tools.catalog_ids():
        manifest = tools.resolve_tool(tool_id).manifest
        assert manifest.ledger_row_type != "model-contact"
        if manifest.cost_class == "contact":
            if tool_id in {
                "saea-tool-live-speech-observation-v1",
                "saea-tool-live-speech-span-v1",
            }:
                assert manifest.ledger_row_type == "tool-contact"
            else:
                assert manifest.ledger_row_type == "service-contact"


# ---------------------------------------------------------------------------
# 1. saea-tool-diarization-artifact-v1
# ---------------------------------------------------------------------------


def _sealed_diarization_document() -> dict:
    """A minimal self-consistent ``saea-diarization-v1`` artifact: two
    speakers over one 90 s window, whose derived facts the loader re-computes
    and compares against the claim."""

    return {
        "schema": "saea-diarization-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": "SAEA-TEST-DIARIZATION-V1",
        "carrier_lock_key": "earnings21-original",
        "window_seconds": 90.0,
        "tool": {
            "lock_key": "sortformer-test",
            "model_sha256": "a" * 64,
            "runtime": "test",
            "runtime_binary_sha256": "b" * 64,
            "device": "cpu",
        },
        "calls": [
            {
                "sample_id": "call-1",
                "audio_seconds": 90.0,
                "segments": [
                    {"speaker": "speaker_0", "start_seconds": 0.0, "end_seconds": 60.0},
                    {"speaker": "speaker_1", "start_seconds": 60.0, "end_seconds": 90.0},
                ],
                "windows": [
                    {
                        "window_id": "call-1#w1",
                        "window_index": 1,
                        "start_seconds": 0.0,
                        "end_seconds": 90.0,
                        "speaker_count": 2,
                        "dominant_speaker": "speaker_0",
                        "dominant_share": 60.0 / 90.0,
                        "overlap_share": 0.0,
                        "speaker_seconds": {"speaker_0": 60.0, "speaker_1": 30.0},
                    }
                ],
            }
        ],
    }


def test_diarization_dry_run_plans_the_read_and_touches_nothing(tmp_path):
    """A dry run reports the contact the Planner would make -- artifact,
    schema, ledger row -- for a path that does not even exist."""

    missing = tmp_path / "not-written.json"
    result = tools.resolve_tool("saea-tool-diarization-artifact-v1").call(
        missing, dry_run=True
    )
    assert not missing.exists()
    assert result.derivation is None
    plan = result.result
    assert isinstance(plan, diarization_wrapper.DiarizationReadPlan)
    assert plan.artifact_path == str(missing)
    assert plan.schema == "saea-diarization-v1"
    assert plan.ledger_row_type == "tool-contact"


def test_diarization_wrapper_is_equivalent_on_a_sealed_artifact(tmp_path):
    path = tmp_path / "diarization.json"
    path.write_text(json.dumps(_sealed_diarization_document()), encoding="utf-8")

    direct = load_diarization(path)
    wrapped = tools.resolve_tool("saea-tool-diarization-artifact-v1").call(path)

    assert wrapped.tool_id == "saea-tool-diarization-artifact-v1"
    assert wrapped.derivation is None
    assert wrapped.result == direct


def test_the_diarization_wrapper_cannot_reach_a_diarizer_runtime():
    """The model is a pinned tool contact and must never run in a unit test:
    this wrapper reads a sealed artifact and imports nothing that could."""

    source = inspect.getsource(diarization_wrapper)
    imports = [
        line
        for line in source.splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    joined = " ".join(imports).lower()
    for forbidden in ("nemo", "torch", "sortformer", "subprocess", "onnx"):
        assert forbidden not in joined


# ---------------------------------------------------------------------------
# 2. saea-tool-slice-encode-v1
# ---------------------------------------------------------------------------


def _tone(samples: int = 800) -> array:
    return array("h", [((index * 37) % 2001) - 1000 for index in range(samples)])


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"preprocess": ("rms-norm",)},
        {"tail_silence_seconds": 0.5},
        {"preprocess": ("rms-norm",), "tail_silence_seconds": 2.0},
    ],
)
def test_slice_encode_wrapper_is_byte_equivalent(kwargs):
    samples = _tone()
    direct = encode_slice(samples, 16000, **kwargs)
    wrapped = tools.resolve_tool("saea-tool-slice-encode-v1").call(
        samples, 16000, **kwargs
    )

    assert wrapped.result == direct
    assert wrapped.result[0] == direct[0]  # the bytes themselves
    assert wrapped.result[1] == direct[1]
    assert wrapped.result[2] == direct[2]


def test_slice_encode_wrapper_emits_a_faithful_derivation_record():
    samples = _tone()
    direct_bytes, direct_transforms, direct_pre = encode_slice(
        samples, 16000, preprocess=("rms-norm",), tail_silence_seconds=2.0
    )
    wrapped = tools.resolve_tool("saea-tool-slice-encode-v1").call(
        samples, 16000, preprocess=("rms-norm",), tail_silence_seconds=2.0
    )

    record = wrapped.derivation
    assert record is not None
    assert record.tool_id == "saea-tool-slice-encode-v1"
    assert record.transforms == direct_transforms
    assert record.pre_sha256 == direct_pre
    assert record.post_sha256 == hashlib.sha256(direct_bytes).hexdigest()


def test_slice_encode_derivation_record_says_so_when_nothing_changed():
    wrapped = tools.resolve_tool("saea-tool-slice-encode-v1").call(_tone(), 16000)
    record = wrapped.derivation
    assert record is not None
    assert record.transforms == ()
    assert record.pre_sha256 is None
    assert record.post_sha256 == hashlib.sha256(wrapped.result[0]).hexdigest()


def test_the_untransformed_slice_is_still_the_historical_wav():
    """The default path stays byte-identical to ``write_wav_bytes``, which is
    what keeps every sealed Earnings run reproducible."""

    samples = _tone()
    wrapped = tools.resolve_tool("saea-tool-slice-encode-v1").call(samples, 16000)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(samples.tobytes())
    assert wrapped.result[0] == buffer.getvalue()


# ---------------------------------------------------------------------------
# 3. saea-tool-speaker-turn-units-v2
# ---------------------------------------------------------------------------


def _unit_plan_inputs():
    segments = (
        SpeakerSegment(speaker="speaker_0", start_seconds=0.0, end_seconds=45.0),
        SpeakerSegment(speaker="speaker_1", start_seconds=45.0, end_seconds=120.0),
        SpeakerSegment(speaker="speaker_0", start_seconds=120.0, end_seconds=200.0),
    )
    pauses = (
        Pause(start_seconds=44.0, end_seconds=45.5),
        Pause(start_seconds=119.0, end_seconds=120.5),
    )
    frame_seconds = 0.5
    active = [True] * int(200.0 / frame_seconds)
    return segments, pauses, active, frame_seconds


def test_speaker_turn_units_wrapper_is_equivalent():
    segments, pauses, active, frame_seconds = _unit_plan_inputs()
    direct = plan_units_v2(
        "call-1", segments, 200.0, pauses, active, frame_seconds
    )
    wrapped = tools.resolve_tool("saea-tool-speaker-turn-units-v2").call(
        "call-1", segments, 200.0, pauses, active, frame_seconds
    )

    assert wrapped.derivation is None
    assert wrapped.result == direct
    assert [unit.as_dict() for unit in wrapped.result] == [
        unit.as_dict() for unit in direct
    ]


def test_speaker_turn_units_wrapper_passes_the_knobs_through():
    segments, pauses, active, frame_seconds = _unit_plan_inputs()
    direct = plan_units_v2(
        "call-1",
        segments,
        200.0,
        pauses,
        active,
        frame_seconds,
        max_seconds=60.0,
        min_seconds=2.0,
        snap_radius=1.0,
    )
    wrapped = tools.resolve_tool("saea-tool-speaker-turn-units-v2").call(
        "call-1",
        segments,
        200.0,
        pauses,
        active,
        frame_seconds,
        max_seconds=60.0,
        min_seconds=2.0,
        snap_radius=1.0,
    )
    assert wrapped.result == direct
    assert wrapped.result != plan_units_v2(
        "call-1", segments, 200.0, pauses, active, frame_seconds
    )


# ---------------------------------------------------------------------------
# 4. saea-tool-legal-label-projection-v2
# ---------------------------------------------------------------------------

#: The committed projection-v2 receipt. Its ``projection_map_closed_list``
#: records the real ``source -> target`` label pairs the sealed flight
#: produced, so the equivalence below runs on inputs a flight actually
#: emitted rather than only on invented ones.
_PROJECTION_RECEIPT = (
    Path(__file__).resolve().parents[2]
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-slurp-legal-label-projection-v2/result-summary.json"
)


def _split_intent(intent: str) -> tuple[str, str]:
    """``"locations_query"`` -> ``("locations", "query")``.

    Split at the FIRST underscore, which is exactly right for SLURP: every
    scenario is a single token and it is the ACTION that may carry underscores
    (``iot`` + ``hue_lightdown``). Same composition
    ``LabelProjection.source_intent`` uses in the other direction.
    """

    scenario, _, action = intent.partition("_")
    return scenario, action


def _synthetic_inventory():
    return legal_intent_inventory(
        {
            "email": ("query", "sendemail"),
            "lists": ("createoradd", "query"),
            "recommendation": ("locations", "events"),
        },
        {
            "email_query": 300,
            "email_sendemail": 120,
            "lists_createoradd": 200,
            "lists_query": 90,
            "recommendation_locations": 150,
            "recommendation_events": 60,
        },
    )


@pytest.mark.parametrize(
    "scenario,action,parsed",
    [
        ("email", "query", True),  # already legal
        ("locations", "query", True),  # 4-PROMOTE
        ("emial", "querry", True),  # 4-FALLBACK edit distance
        (None, "query", True),  # no label half
        ("email", "query", False),  # unparsed
    ],
)
def test_legal_label_projection_wrapper_is_equivalent(scenario, action, parsed):
    inventory = _synthetic_inventory()
    direct = project_slu_label_v2(scenario, action, inventory, parsed=parsed)
    wrapped = tools.resolve_tool("saea-tool-legal-label-projection-v2").call(
        scenario, action, inventory, parsed=parsed
    )

    assert wrapped.derivation is None
    assert wrapped.result == direct
    assert wrapped.result.branch == direct.branch
    assert wrapped.result.projected_intent == direct.projected_intent


@pytest.mark.skipif(
    not _PROJECTION_RECEIPT.is_file(),
    reason="the projection-v2 receipt is not in this checkout",
)
def test_legal_label_projection_wrapper_is_equivalent_on_the_sealed_receipt():
    """Equivalence on the SEALED flight's own labels.

    The legal space is rebuilt from the receipt's projection TARGETS (a
    subset of the real 60-pair TRAIN inventory, which is built from the
    pinned corpus and is not committed), so this does not re-derive the
    receipt's targets -- it asserts that the tool and the direct call decide
    identically on every source label the flight actually emitted, which is
    the only claim a wrapper is entitled to make.
    """

    document = json.loads(_PROJECTION_RECEIPT.read_text(encoding="utf-8"))
    mapping = document["projection_map_closed_list"]["v2"]["map"]
    pairs = [key.split(" -> ") for key in mapping]
    assert pairs, "the receipt records no projected rows"

    actions_by_scenario: dict[str, set[str]] = {}
    for _, target in pairs:
        scenario, action = _split_intent(target)
        actions_by_scenario.setdefault(scenario, set()).add(action)
    inventory = legal_intent_inventory(
        {scenario: tuple(sorted(actions)) for scenario, actions in actions_by_scenario.items()}
    )

    entry = tools.resolve_tool("saea-tool-legal-label-projection-v2")
    for source, _ in pairs:
        scenario, action = _split_intent(source)
        direct = project_slu_label_v2(scenario, action, inventory)
        wrapped = entry.call(scenario, action, inventory)
        assert wrapped.result == direct, source
        assert wrapped.result.branch == direct.branch, source


# ---------------------------------------------------------------------------
# 5. saea-tool-repair-alignment-v1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "predecessor,response",
    [
        (
            "the chief executive mister smith joined the call",
            "the chief executive mister smyth joined the call",
        ),
        ("", "anything at all"),  # empty predecessor -> refusal
        ("a real predecessor line", ""),  # empty response -> refusal
        (
            "the chief executive mister smith joined the call",
            "completely different text with nothing in common whatsoever here",
        ),
        (
            "the chief executive mister smith joined the call",
            "the chief executive mister smith joined the call",
        ),
    ],
)
def test_repair_alignment_wrapper_is_equivalent(predecessor, response):
    direct = accept_entity_repair(predecessor, response)
    wrapped = tools.resolve_tool("saea-tool-repair-alignment-v1").call(
        predecessor, response
    )

    assert wrapped.derivation is None
    assert wrapped.result == direct
    assert wrapped.result.trace_view() == direct.trace_view()


def test_repair_alignment_wrapper_passes_the_bounds_through():
    predecessor = "the chief executive mister smith joined the call today"
    response = "the chief executive mister smyth joined the call today"
    direct = accept_entity_repair(
        predecessor,
        response,
        max_span_tokens=1,
        min_anchor_ratio=0.9,
        max_substituted_fraction=0.01,
    )
    wrapped = tools.resolve_tool("saea-tool-repair-alignment-v1").call(
        predecessor,
        response,
        max_span_tokens=1,
        min_anchor_ratio=0.9,
        max_substituted_fraction=0.01,
    )
    assert wrapped.result == direct


# ---------------------------------------------------------------------------
# 6. saea-tool-flagged-spans-v1 (two pinned sources, one tool)
# ---------------------------------------------------------------------------


def test_flagged_spans_wrapper_is_equivalent_on_the_logprob_source():
    words = ["the", "chief", "executive", "mister", "smith", "joined"]
    scores = [-0.1, -0.2, -4.0, -3.5, -3.9, -0.3]
    direct = flag_spans(words, scores, -3.0, 2)
    wrapped = tools.resolve_tool("saea-tool-flagged-spans-v1").call(
        "logprob", words, scores, -3.0, 2
    )

    assert wrapped.derivation is None
    assert wrapped.result == direct
    assert wrapped.result == [(2, 5)]


def test_flagged_spans_wrapper_is_equivalent_on_the_roster_band_source():
    words = ["the", "chief", "executive", "mister", "smyth", "joined", "the", "call"]
    candidates = ["smith", "hathaway", "bernstein"]
    direct = roster_band_flags(words, candidates, 3)
    wrapped = tools.resolve_tool("saea-tool-flagged-spans-v1").call(
        "roster-band", words, candidates, 3
    )

    assert wrapped.result == direct
    assert [flag.span for flag in wrapped.result] == [flag.span for flag in direct]


def test_flagged_spans_wrapper_refuses_an_unknown_source():
    with pytest.raises(tools.ToolCatalogError):
        tools.resolve_tool("saea-tool-flagged-spans-v1").call("vibes", [], [], -3.0, 2)


def test_the_second_flag_source_is_pinned_too():
    """A manifest carries one ``source_ref``; this tool dispatches to two
    bodies, so the second is pinned in the wrapper module."""

    extra = flagged_spans_wrapper.ADDITIONAL_PINNED_SOURCES
    assert extra
    for source_ref, pinned in extra.items():
        assert tools.source_sha256(source_ref) == pinned
    assert set(flagged_spans_wrapper.FLAG_SOURCES) == {"logprob", "roster-band"}


# ---------------------------------------------------------------------------
# 7. saea-tool-sealed-vector-query-v1
# ---------------------------------------------------------------------------


def _sealed_vector_file(tmp_path: Path) -> tuple[Path, str]:
    lines = [
        json.dumps({"id": "row-1", "vectors": {"content": [0.5, -0.25, 0.125]}}),
        json.dumps({"id": "row-2", "vectors": {"content": [-1.0, 0.0, 0.75]}}),
    ]
    path = tmp_path / "query-vectors.jsonl"
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(payload)
    return path, hashlib.sha256(payload).hexdigest()


def test_sealed_vector_query_wrapper_is_equivalent(tmp_path):
    path, digest = _sealed_vector_file(tmp_path)
    direct = load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))
    wrapped = tools.resolve_tool("saea-tool-sealed-vector-query-v1").call(
        path, expected_sha256=digest, dimensions=("content",)
    )

    assert wrapped.derivation is None
    assert wrapped.result == direct
    assert wrapped.result["row-1"]["content"] == (0.5, -0.25, 0.125)


def test_sealed_vector_query_wrapper_stays_fail_closed_on_a_wrong_hash(tmp_path):
    path, _ = _sealed_vector_file(tmp_path)
    with pytest.raises(Exception):
        tools.resolve_tool("saea-tool-sealed-vector-query-v1").call(
            path, expected_sha256="f" * 64, dimensions=("content",)
        )


# ---------------------------------------------------------------------------
# 8. saea-tool-prompt-fit-tokens-v1
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.status = 200
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class _FakeConnection:
    """Stands in for the client's own ``http.client.HTTPConnection`` so the
    REAL ``request_json`` body runs -- headers, status check, JSON decode --
    with no socket and no server."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str, bytes | None]] = []

    def request(self, method, path, body=None, headers=None):
        self.calls.append((method, path, body))

    def getresponse(self):
        return _FakeResponse(json.dumps(self.payload).encode("utf-8"))


def _client_with_fake_connection(payload: dict):
    from speech_aware_evidence_acquisition.core.driver.speech_native import (
        _LoopbackPromptAuditClient,
    )

    client = _LoopbackPromptAuditClient(host="127.0.0.1", port=8080, timeout_seconds=5.0)
    client.local.connection = _FakeConnection(payload)
    return client


def test_prompt_fit_wrapper_is_equivalent_on_tokenize():
    payload = {"tokens": [1, 2, 3, 4, 5]}
    direct_client = _client_with_fake_connection(payload)
    wrapped_client = _client_with_fake_connection(payload)
    request = {"content": "a brief line", "add_special": False, "parse_special": True}

    direct = direct_client.request_json("POST", "/tokenize", request)
    wrapped = tools.resolve_tool("saea-tool-prompt-fit-tokens-v1").call(
        wrapped_client, "POST", "/tokenize", request
    )

    assert wrapped.derivation is None
    assert wrapped.result == direct
    assert len(wrapped.result["tokens"]) == 5
    # The same wire bytes reached the same route both ways.
    assert wrapped_client.local.connection.calls == direct_client.local.connection.calls


def test_prompt_fit_wrapper_is_equivalent_on_props_and_apply_template():
    for route, payload, request in (
        ("/props", {"media_marker": "<|audio|>"}, None),
        ("/apply-template", {"prompt": "rendered"}, {"messages": []}),
    ):
        direct_client = _client_with_fake_connection(payload)
        wrapped_client = _client_with_fake_connection(payload)
        direct = direct_client.request_json("POST", route, request)
        wrapped = tools.resolve_tool("saea-tool-prompt-fit-tokens-v1").call(
            wrapped_client, "POST", route, request
        )
        assert wrapped.result == direct


def test_prompt_fit_wrapper_refuses_a_generative_route():
    """The single door stays the single door: no catalog tool may reach a
    route that generates."""

    client = _client_with_fake_connection({"content": "never"})
    for route in ("/completion", "/v1/chat/completions", "/completions"):
        with pytest.raises(tools.ToolCatalogError):
            tools.resolve_tool("saea-tool-prompt-fit-tokens-v1").call(
                client, "POST", route, {}
            )
    assert prompt_fit_wrapper.ALLOWED_ROUTES == ("/props", "/apply-template", "/tokenize")


def test_prompt_fit_wrapper_refuses_a_client_without_the_method():
    with pytest.raises(tools.ToolCatalogError):
        tools.resolve_tool("saea-tool-prompt-fit-tokens-v1").call(
            object(), "POST", "/tokenize", {}
        )


# ---------------------------------------------------------------------------
# The framework surface, over a real registered entry.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not openjiuwen_available(), reason="needs the pinned openjiuwen runtime"
)
def test_to_tool_card_carries_the_manifest_in_properties():
    for tool_id in tools.catalog_ids():
        manifest = tools.resolve_tool(tool_id).manifest
        card = tools.to_tool_card(tool_id)
        assert card.id == manifest.tool_id
        assert card.name == manifest.tool_id
        assert card.description == manifest.description
        assert card.properties == manifest.as_dict()
        assert card.properties["system_invoked"] is True
        assert card.properties["invocation"] == "system"
        assert card.parallel_safe == manifest.parallel_safe
        assert card.stateless == manifest.stateless
        assert card.idempotent == manifest.idempotent
        assert card.input_params == tools.tool_input_params(manifest)


@pytest.mark.skipif(
    not openjiuwen_available(), reason="needs the pinned openjiuwen runtime"
)
def test_to_local_function_binds_the_wrapper_body():
    """The framework object wraps OUR body and nothing else.

    ``LocalFunction.__init__`` re-wraps a callable that declares
    ``*args`` through its own ``support_args_param`` adapter (the
    flagged-span dispatcher is the one such body here), and that adapter
    carries ``functools.wraps``, so the bound body is reachable through
    ``__wrapped__``. Either way it is our function and never a framework
    substitute.
    """

    for tool_id in tools.catalog_ids():
        entry = tools.resolve_tool(tool_id)
        local = tools.to_local_function(tool_id)
        assert local.card.id == tool_id
        bound = local._func
        assert bound is entry.body or getattr(bound, "__wrapped__", None) is entry.body
