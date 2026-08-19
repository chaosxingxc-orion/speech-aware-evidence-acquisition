"""``rails.probes.pkey_flight``: the P-KEY five-pass factorial flight
orchestration (docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test drives a
``MockCoreClient``.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.model import SliceRegistry
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pkey_flight import (
    AUD_NOSUP_ARM,
    AUD_SUP_ARM,
    EXPECTED_SPLIT_IDENTITY_HASH,
    PKEY_ARMS,
    SILENCE_SWAP_ARM,
    T0_ARM,
    T0_INSTRUCTION,
    TXT_DUPLICATE_ARM,
    TXT_NOSUP_ARM,
    TXT_SUP_ARM,
    TXT_TRANSCRIPT_TEMPLATE,
    PKeyArmResult,
    PKeyFlightError,
    PKeyFlightSummary,
    TranscriptRecord,
    assemble_t0_messages,
    assemble_txt_messages,
    assert_pinned_text_matches_config,
    assert_split_identity_hash,
    build_transcript_record,
    content_has_audio,
    content_text_parts,
    extract_txt_transcript_from_rendered,
    render_txt_transcript_block,
    run_pkey_flight,
    t0_instruction_sha256,
    transcript_registry_as_json,
    txt_duplicate_content_matches,
    txt_template_sha256,
    validate_pkey_flight_summary,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import PsluRosters
from speech_aware_evidence_acquisition.rails.silence_swap import build_silence_swap_slice
from speech_aware_evidence_acquisition.rails.supply import (
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
)

_ROSTERS = PsluRosters(
    scenario_rosters={"iot": (("house_place", "kitchen"),), "email": (("email_folder", "inbox"),)},
    global_types=("house_place", "email_folder"),
    full_roster=(("house_place", "kitchen"), ("time", "six")),
    derangement={"iot": "email", "email": "iot"},
)
_G0_BINDING_DIR = Path(__file__).resolve().parents[2] / "configs" / "probes" / "g0-binding"
_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "pkey-flight.json"


def _adapter(slurp_world) -> SlurpAdapter:
    lock = load_lock(slurp_world.lock_path)
    return SlurpAdapter(lock, slurp_world.data_root)


def _flight_world(slurp_world):
    adapter = _adapter(slurp_world)
    devel = adapter.load_split("devel")
    s_iot = devel[0]  # slurp:devel:000101:audio-101-headset (or similar) -- gold scenario "iot"
    s_email = devel[2]  # slurp:devel:000102:audio-102 -- gold scenario "email"
    return adapter, s_iot, s_email


# ---------------------------------------------------------------------------
# render/extract round trip, config/code parity.
# ---------------------------------------------------------------------------


def test_render_and_extract_round_trip():
    rendered = render_txt_transcript_block("turn on the kitchen lights")
    assert rendered == "The user said: turn on the kitchen lights"
    assert extract_txt_transcript_from_rendered(rendered) == "turn on the kitchen lights"


def test_extract_rejects_a_rendered_block_missing_the_pinned_prefix():
    with pytest.raises(PKeyFlightError, match="pinned template prefix"):
        extract_txt_transcript_from_rendered("something else entirely")


def test_render_handles_an_empty_transcript():
    assert extract_txt_transcript_from_rendered(render_txt_transcript_block("")) == ""


def test_pinned_text_hashes_are_self_consistent():
    assert t0_instruction_sha256() == __import__("hashlib").sha256(T0_INSTRUCTION.encode("utf-8")).hexdigest()
    assert txt_template_sha256() == __import__("hashlib").sha256(TXT_TRANSCRIPT_TEMPLATE.encode("utf-8")).hexdigest()


def test_assert_pinned_text_matches_config_accepts_the_real_registered_config():
    document = json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))
    assert_pinned_text_matches_config(document)  # does not raise


def test_assert_pinned_text_matches_config_rejects_a_drifted_template():
    document = json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))
    document = dict(document)
    document["txt_template"] = "Something drifted: {transcript}"
    with pytest.raises(PKeyFlightError, match="txt_template"):
        assert_pinned_text_matches_config(document)


def test_assert_pinned_text_matches_config_rejects_a_drifted_instruction_hash():
    document = json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))
    document = dict(document)
    document["t0_instruction_sha256"] = "0" * 64
    with pytest.raises(PKeyFlightError, match="t0_instruction_sha256"):
        assert_pinned_text_matches_config(document)


# ---------------------------------------------------------------------------
# split identity hash.
# ---------------------------------------------------------------------------


def test_assert_split_identity_hash_accepts_the_registered_value():
    assert_split_identity_hash(EXPECTED_SPLIT_IDENTITY_HASH)  # does not raise


def test_assert_split_identity_hash_rejects_anything_else():
    with pytest.raises(PKeyFlightError, match="does not match"):
        assert_split_identity_hash("a" * 64)


# ---------------------------------------------------------------------------
# no-gold-parameter structural check (legality: gold text never enters any
# prompt path).
# ---------------------------------------------------------------------------


def test_assemble_functions_carry_no_gold_or_reference_parameter():
    for fn in (assemble_t0_messages, assemble_txt_messages):
        names = " ".join(inspect.signature(fn).parameters.keys()).lower()
        assert "gold" not in names
        assert "reference" not in names
        assert "sentence" not in names


# ---------------------------------------------------------------------------
# assemble_t0_messages / assemble_txt_messages.
# ---------------------------------------------------------------------------


def test_assemble_t0_messages_is_audio_only_zero_supply(slurp_world):
    _, s_iot, _ = _flight_world(slurp_world)
    messages = assemble_t0_messages(s_iot)
    assert messages[0] == {"role": "system", "content": T0_INSTRUCTION}
    assert messages[1]["content"] == [{"type": "input_audio", "media_relpath": s_iot.media_relpath}]
    assert content_has_audio(messages) is True
    assert content_text_parts(messages) == ()


def test_assemble_txt_messages_refuses_without_a_registered_transcript(slurp_world):
    """Ordering-dependency enforcement (hard requirement): a TXT arm cannot
    build a prompt before pass 0 (T0) has completed and hash-recorded this
    sample's own transcript."""

    _, s_iot, _ = _flight_world(slurp_world)
    with pytest.raises(PKeyFlightError, match="require pass 0"):
        assemble_txt_messages(s_iot, None, {})


def test_assemble_txt_messages_nosup_is_audio_free_single_text_part(slurp_world):
    _, s_iot, _ = _flight_world(slurp_world)
    registry = {s_iot.sample_id: build_transcript_record(s_iot.sample_id, "turn on the kitchen light")}
    messages = assemble_txt_messages(s_iot, None, registry)
    assert content_has_audio(messages) is False  # legality: TXT arms carry no audio attachment
    texts = content_text_parts(messages)
    assert texts == ("The user said: turn on the kitchen light",)


def test_assemble_txt_messages_sup_prepends_the_roster_then_the_transcript(slurp_world):
    _, s_iot, _ = _flight_world(slurp_world)
    registry = {s_iot.sample_id: build_transcript_record(s_iot.sample_id, "turn on the kitchen light")}
    supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=1, token_count=1),
        prompt_block="house_place=kitchen",
        assembly_template_id="pkey-A3-roster-v1",
        items=(SupplyItem(item_id="A3-000", text="house_place=kitchen"),),
    ).validate()
    messages = assemble_txt_messages(s_iot, supply, registry)
    assert content_has_audio(messages) is False
    texts = content_text_parts(messages)
    assert texts == ("house_place=kitchen", "The user said: turn on the kitchen light")


def test_assemble_txt_messages_never_uses_a_different_samples_transcript(slurp_world):
    _, s_iot, s_email = _flight_world(slurp_world)
    registry = {
        s_iot.sample_id: build_transcript_record(s_iot.sample_id, "iot transcript"),
        s_email.sample_id: build_transcript_record(s_email.sample_id, "email transcript"),
    }
    messages = assemble_txt_messages(s_iot, None, registry)
    assert content_text_parts(messages) == ("The user said: iot transcript",)


# ---------------------------------------------------------------------------
# transcript_registry_as_json.
# ---------------------------------------------------------------------------


def test_transcript_registry_as_json():
    record = build_transcript_record("sid-1", "hello world")
    registry = {"sid-1": record}
    assert transcript_registry_as_json(registry) == {"sid-1": record.as_json()}
    assert record.sha256 == __import__("hashlib").sha256(b"hello world").hexdigest()


# ---------------------------------------------------------------------------
# run_pkey_flight -- end to end.
# ---------------------------------------------------------------------------


def _responder(transcript_by_media_relpath: dict[str, str]):
    def responder(messages):
        system_content = messages[0]["content"]
        if system_content == T0_INSTRUCTION:
            for part in messages[1]["content"]:
                if part.get("type") == "input_audio":
                    return transcript_by_media_relpath[part["media_relpath"]]
            raise AssertionError("T0 request carries no input_audio part")
        return json.dumps({"scenario": "iot", "action": "hue_lighton", "entities": []})

    return responder


def test_run_pkey_flight_produces_the_five_passes_in_registered_order(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    transcripts = {
        s_iot.media_relpath: "turn on the kitchen light",
        s_email.media_relpath: "how many unread emails",
    }
    client = MockCoreClient(responder=_responder(transcripts))

    summary = run_pkey_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )

    assert [r.arm for r in summary.results] == [
        T0_ARM, T0_ARM,
        AUD_NOSUP_ARM, AUD_NOSUP_ARM,
        AUD_SUP_ARM, AUD_SUP_ARM,
        TXT_NOSUP_ARM, TXT_NOSUP_ARM,
        TXT_SUP_ARM, TXT_SUP_ARM,
    ]
    assert len(client.calls) == 10
    assert set(PKEY_ARMS) == {T0_ARM, AUD_NOSUP_ARM, AUD_SUP_ARM, TXT_NOSUP_ARM, TXT_SUP_ARM}


def test_run_pkey_flight_aud_arms_mirror_the_consumed_pslu_a0_and_a3_construction(slurp_world):
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import pslu_supply_packet

    adapter, s_iot, s_email = _flight_world(slurp_world)
    transcripts = {s_iot.media_relpath: "t", s_email.media_relpath: "t2"}
    client = MockCoreClient(responder=_responder(transcripts))
    summary = run_pkey_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )

    aud_nosup = next(r for r in summary.results if r.arm == AUD_NOSUP_ARM and r.sample_id == s_iot.sample_id)
    aud_sup = next(r for r in summary.results if r.arm == AUD_SUP_ARM and r.sample_id == s_iot.sample_id)
    assert list(aud_nosup.messages) == list(adapter.assemble_prompt(s_iot, None))
    a3 = pslu_supply_packet("A3", scenario=None, rosters=_ROSTERS)
    assert list(aud_sup.messages) == list(adapter.assemble_prompt(s_iot, a3))


def test_run_pkey_flight_txt_arms_reuse_t0s_own_transcript_byte_identically(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    transcripts = {s_iot.media_relpath: "turn on the kitchen light", s_email.media_relpath: "check email"}
    client = MockCoreClient(responder=_responder(transcripts))
    summary = run_pkey_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )

    t0_iot = next(r for r in summary.results if r.arm == T0_ARM and r.sample_id == s_iot.sample_id)
    txt_nosup_iot = next(r for r in summary.results if r.arm == TXT_NOSUP_ARM and r.sample_id == s_iot.sample_id)
    txt_sup_iot = next(r for r in summary.results if r.arm == TXT_SUP_ARM and r.sample_id == s_iot.sample_id)

    assert t0_iot.response_text == "turn on the kitchen light"
    assert content_text_parts(txt_nosup_iot.messages)[-1] == render_txt_transcript_block("turn on the kitchen light")
    assert content_text_parts(txt_sup_iot.messages)[-1] == render_txt_transcript_block("turn on the kitchen light")
    assert content_has_audio(txt_nosup_iot.messages) is False
    assert content_has_audio(txt_sup_iot.messages) is False
    expected_sha256 = build_transcript_record(s_iot.sample_id, "turn on the kitchen light").sha256
    assert txt_nosup_iot.transcript_sha256_used == expected_sha256
    assert txt_sup_iot.transcript_sha256_used == expected_sha256
    assert summary.transcript_registry[s_iot.sample_id].text == "turn on the kitchen light"


def test_run_pkey_flight_silence_swap_adds_one_extra_aud_sup_row(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    transcripts = {s_iot.media_relpath: "t", s_email.media_relpath: "t2"}
    client = MockCoreClient(responder=_responder(transcripts))
    registry = SliceRegistry(
        data_root=slurp_world.data_root,
        run_id="run-x",
        parent_facts={s_iot.sample_id: (s_iot.media_relpath, s_iot.audio_seconds)},
    )
    silence_record = build_silence_swap_slice(
        registry=registry, data_root=slurp_world.data_root, sample_id=s_iot.sample_id,
        parent_media_relpath=s_iot.media_relpath, duration_seconds=s_iot.audio_seconds, sample_rate_hz=16000,
    )
    registry.register(silence_record)

    summary = run_pkey_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        silence_swap_media_relpaths={s_iot.sample_id: silence_record.media_relpath},
    )

    assert len(summary.results) == 11  # 10 base + 1 silence-swap
    swapped = [r for r in summary.results if r.silence_swapped]
    assert len(swapped) == 1
    assert swapped[0].arm == AUD_SUP_ARM
    assert swapped[0].sample_id == s_iot.sample_id
    assert swapped[0].messages[1]["content"][-1] == {
        "type": "input_audio", "media_relpath": silence_record.media_relpath,
    }
    normal_aud_sup = next(
        r for r in summary.results if r.arm == AUD_SUP_ARM and r.sample_id == s_iot.sample_id and not r.silence_swapped
    )
    assert swapped[0].messages[1]["content"][0] == normal_aud_sup.messages[1]["content"][0]


# ---------------------------------------------------------------------------
# txt_duplicate sub-block (2026-08-19 amendment item 4).
# ---------------------------------------------------------------------------


class _RecordingClient:
    """Wraps a MockCoreClient and additionally records the
    ``text_only_sample_id`` kwarg every ``complete()`` call carried --
    MockCoreClient itself accepts-and-discards it (module docstring, "THE
    TEST LESSON"), so a test that wants to assert run_pkey_flight actually
    PASSES this kwarg for TXT arms needs its own thin recorder."""

    def __init__(self, responder):
        self._mock = MockCoreClient(responder=responder)
        self.text_only_sample_ids: list[str | None] = []

    def complete(self, messages, *, decoding_params=None, text_only_sample_id=None):
        self.text_only_sample_ids.append(text_only_sample_id)
        return self._mock.complete(messages, decoding_params=decoding_params)

    @property
    def calls(self):
        return self._mock.calls


def test_run_pkey_flight_txt_arms_and_duplicate_block_use_text_only_mode(slurp_world):
    """rails/probes/pkey_flight.py's TXT passes (3, 4, and the duplicate
    sub-block) use the real-client text-mode capability -- pass 0/1/2 (audio
    arms) never do."""

    adapter, s_iot, s_email = _flight_world(slurp_world)
    transcripts = {s_iot.media_relpath: "turn on the kitchen light", s_email.media_relpath: "check email"}
    client = _RecordingClient(_responder(transcripts))

    run_pkey_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        txt_duplicate_sample_ids=[s_iot.sample_id],
    )

    # Registered order: T0(2) AUD-NOSUP(2) AUD-SUP(2) TXT-NOSUP(2) TXT-SUP(2) DUP(1).
    assert client.text_only_sample_ids == [
        None, None,  # T0
        None, None,  # AUD-NOSUP
        None, None,  # AUD-SUP
        s_iot.sample_id, s_email.sample_id,  # TXT-NOSUP
        s_iot.sample_id, s_email.sample_id,  # TXT-SUP
        s_iot.sample_id,  # duplicate sub-block
    ]


def test_run_pkey_flight_txt_duplicate_adds_one_extra_byte_identical_row_per_named_sample(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    transcripts = {s_iot.media_relpath: "turn on the kitchen light", s_email.media_relpath: "check email"}
    client = MockCoreClient(responder=_responder(transcripts))

    summary = run_pkey_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        txt_duplicate_sample_ids=[s_iot.sample_id],
    )

    assert len(summary.results) == 11  # 10 base + 1 duplicate
    duplicates = [r for r in summary.results if r.txt_duplicate]
    assert len(duplicates) == 1
    dup = duplicates[0]
    assert dup.arm == TXT_DUPLICATE_ARM == TXT_NOSUP_ARM
    assert dup.sample_id == s_iot.sample_id
    assert content_has_audio(dup.messages) is False

    original = next(
        r for r in summary.results
        if r.arm == TXT_NOSUP_ARM and r.sample_id == s_iot.sample_id and not r.txt_duplicate
    )
    assert txt_duplicate_content_matches(dup.messages, original.messages) is True
    assert content_text_parts(dup.messages) == content_text_parts(original.messages)
    assert dup.transcript_sha256_used == original.transcript_sha256_used


def test_run_pkey_flight_txt_duplicate_empty_by_default(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    transcripts = {s_iot.media_relpath: "t", s_email.media_relpath: "t2"}
    client = MockCoreClient(responder=_responder(transcripts))
    summary = run_pkey_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )
    assert len(summary.results) == 10  # unchanged when txt_duplicate_sample_ids is omitted
    assert not any(r.txt_duplicate for r in summary.results)


def test_run_pkey_flight_rejects_unknown_txt_duplicate_sample_ids(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "t"}))
    with pytest.raises(PKeyFlightError, match="outside this flight"):
        run_pkey_flight(
            adapter=adapter, core_client=client, samples=[s_iot], rosters=_ROSTERS,
            split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
            txt_duplicate_sample_ids=["bogus-sample-id"],
        )


def test_run_pkey_flight_rejects_a_duplicate_id_within_txt_duplicate_sample_ids(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "t"}))
    with pytest.raises(PKeyFlightError, match="txt_duplicate_sample_ids carries a duplicate"):
        run_pkey_flight(
            adapter=adapter, core_client=client, samples=[s_iot], rosters=_ROSTERS,
            split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
            txt_duplicate_sample_ids=[s_iot.sample_id, s_iot.sample_id],
        )


# ---------------------------------------------------------------------------
# txt_duplicate_content_matches -- direct.
# ---------------------------------------------------------------------------


def test_txt_duplicate_content_matches_true_for_identical_audio_free_content():
    messages = (
        {"role": "system", "content": "x"},
        {"role": "user", "content": [{"type": "text", "text": "The user said: hello"}]},
    )
    other = (
        {"role": "system", "content": "different system text -- irrelevant to this check"},
        {"role": "user", "content": [{"type": "text", "text": "The user said: hello"}]},
    )
    assert txt_duplicate_content_matches(messages, other) is True


def test_txt_duplicate_content_matches_false_when_text_diverges():
    original = (
        {"role": "system", "content": "x"},
        {"role": "user", "content": [{"type": "text", "text": "The user said: hello"}]},
    )
    diverged = (
        {"role": "system", "content": "x"},
        {"role": "user", "content": [{"type": "text", "text": "The user said: goodbye"}]},
    )
    assert txt_duplicate_content_matches(diverged, original) is False


def test_txt_duplicate_content_matches_false_when_either_side_carries_audio():
    text_only = (
        {"role": "system", "content": "x"},
        {"role": "user", "content": [{"type": "text", "text": "The user said: hello"}]},
    )
    with_audio = (
        {"role": "system", "content": "x"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "The user said: hello"},
                {"type": "input_audio", "media_relpath": "s1.flac"},
            ],
        },
    )
    assert txt_duplicate_content_matches(with_audio, text_only) is False
    assert txt_duplicate_content_matches(text_only, with_audio) is False


def test_run_pkey_flight_rejects_empty_samples(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    with pytest.raises(PKeyFlightError, match="at least one sample"):
        run_pkey_flight(
            adapter=adapter, core_client=MockCoreClient(), samples=(), rosters=_ROSTERS,
            split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_run_pkey_flight_rejects_unknown_silence_swap_sample_ids(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "t"}))
    with pytest.raises(PKeyFlightError, match="outside this flight"):
        run_pkey_flight(
            adapter=adapter, core_client=client, samples=[s_iot], rosters=_ROSTERS,
            split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
            silence_swap_media_relpaths={"bogus-sample-id": "x.wav"},
        )


def test_run_pkey_flight_rejects_a_wrong_split_identity_hash(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "t"}))
    with pytest.raises(PKeyFlightError, match="does not match"):
        run_pkey_flight(
            adapter=adapter, core_client=client, samples=[s_iot], rosters=_ROSTERS,
            split_identity_hash="b" * 64,
        )


# ---------------------------------------------------------------------------
# validate_pkey_flight_summary -- structural + byte-identity fixtures.
# ---------------------------------------------------------------------------


def _empty_consumption():
    from speech_aware_evidence_acquisition.rails.consumption import ConsumptionTrace

    return ConsumptionTrace(records=(), copy_rate=0.0, dose_realized=0)


def _valid_two_sample_summary() -> tuple[PKeyFlightSummary, list[str]]:
    sample_ids = ["s1", "s2"]
    results: list[PKeyArmResult] = []
    registry: dict[str, TranscriptRecord] = {}
    for sid in sample_ids:
        transcript_text = f"transcript for {sid}"
        record = build_transcript_record(sid, transcript_text)
        registry[sid] = record
        t0_messages = ({"role": "system", "content": T0_INSTRUCTION}, {"role": "user", "content": [{"type": "input_audio", "media_relpath": f"{sid}.flac"}]})
        results.append(
            PKeyArmResult(arm=T0_ARM, sample_id=sid, messages=t0_messages, response_text=transcript_text, metrics={}, consumption=_empty_consumption())
        )
    for arm in (AUD_NOSUP_ARM, AUD_SUP_ARM):
        for sid in sample_ids:
            messages = ({"role": "system", "content": "x"}, {"role": "user", "content": [{"type": "input_audio", "media_relpath": f"{sid}.flac"}]})
            results.append(
                PKeyArmResult(arm=arm, sample_id=sid, messages=messages, response_text="{}", metrics={}, consumption=_empty_consumption())
            )
    for arm in (TXT_NOSUP_ARM, TXT_SUP_ARM):
        for sid in sample_ids:
            rendered = render_txt_transcript_block(registry[sid].text)
            messages = ({"role": "system", "content": "x"}, {"role": "user", "content": [{"type": "text", "text": rendered}]})
            results.append(
                PKeyArmResult(
                    arm=arm, sample_id=sid, messages=messages, response_text="{}", metrics={}, consumption=_empty_consumption(),
                    transcript_sha256_used=registry[sid].sha256,
                )
            )
    return PKeyFlightSummary(results=tuple(results), transcript_registry=registry), sample_ids


def test_validate_pkey_flight_summary_accepts_a_well_formed_summary():
    summary, sample_ids = _valid_two_sample_summary()
    validate_pkey_flight_summary(summary, expected_sample_ids=sample_ids)  # does not raise


def test_validate_pkey_flight_summary_refuses_when_txt_transcript_differs_from_t0_output():
    """Transcript-reuse byte-identity enforcement fixture (mission
    requirement): a TXT-NOSUP row whose own rendered transcript differs from
    its sample's own T0 response must refuse."""

    summary, sample_ids = _valid_two_sample_summary()
    results = list(summary.results)
    for index, row in enumerate(results):
        if row.arm == TXT_NOSUP_ARM and row.sample_id == "s1":
            corrupted_rendered = render_txt_transcript_block("a completely different transcript")
            corrupted_messages = (row.messages[0], {"role": "user", "content": [{"type": "text", "text": corrupted_rendered}]})
            results[index] = PKeyArmResult(
                arm=row.arm, sample_id=row.sample_id, messages=corrupted_messages, response_text=row.response_text,
                metrics=row.metrics, consumption=row.consumption, transcript_sha256_used=row.transcript_sha256_used,
            )
    corrupted_summary = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match="byte-identity violated"):
        validate_pkey_flight_summary(corrupted_summary, expected_sample_ids=sample_ids)


def test_validate_pkey_flight_summary_refuses_when_recorded_hash_disagrees_with_t0():
    """A row's own transcript_sha256_used field disagreeing with the T0 hash
    it should have come from is caught even when the RENDERED text itself
    happens to still match (defense in depth)."""

    summary, sample_ids = _valid_two_sample_summary()
    results = list(summary.results)
    for index, row in enumerate(results):
        if row.arm == TXT_SUP_ARM and row.sample_id == "s2":
            results[index] = PKeyArmResult(
                arm=row.arm, sample_id=row.sample_id, messages=row.messages, response_text=row.response_text,
                metrics=row.metrics, consumption=row.consumption, transcript_sha256_used="0" * 64,
            )
    corrupted_summary = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match="disagrees with the T0 hash"):
        validate_pkey_flight_summary(corrupted_summary, expected_sample_ids=sample_ids)


def test_validate_pkey_flight_summary_refuses_a_txt_row_carrying_audio():
    summary, sample_ids = _valid_two_sample_summary()
    results = list(summary.results)
    for index, row in enumerate(results):
        if row.arm == TXT_NOSUP_ARM and row.sample_id == "s1":
            leaked_messages = (row.messages[0], {"role": "user", "content": [{"type": "input_audio", "media_relpath": "s1.flac"}]})
            results[index] = PKeyArmResult(
                arm=row.arm, sample_id=row.sample_id, messages=leaked_messages, response_text=row.response_text,
                metrics=row.metrics, consumption=row.consumption, transcript_sha256_used=row.transcript_sha256_used,
            )
    corrupted_summary = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match="audio-free"):
        validate_pkey_flight_summary(corrupted_summary, expected_sample_ids=sample_ids)


def test_validate_pkey_flight_summary_refuses_a_missing_sample_row():
    summary, sample_ids = _valid_two_sample_summary()
    results = tuple(row for row in summary.results if not (row.arm == AUD_SUP_ARM and row.sample_id == "s2"))
    trimmed_summary = PKeyFlightSummary(results=results, transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match="does not match the expected"):
        validate_pkey_flight_summary(trimmed_summary, expected_sample_ids=sample_ids)


def test_validate_pkey_flight_summary_refuses_a_duplicate_row():
    summary, sample_ids = _valid_two_sample_summary()
    results = list(summary.results)
    duplicate = next(row for row in results if row.arm == T0_ARM and row.sample_id == "s1")
    results.append(duplicate)
    dup_summary = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match="duplicate sample_id"):
        validate_pkey_flight_summary(dup_summary, expected_sample_ids=sample_ids)


def test_validate_pkey_flight_summary_silence_swap_must_be_on_aud_sup():
    summary, sample_ids = _valid_two_sample_summary()
    results = list(summary.results)
    t0_s1 = next(row for row in results if row.arm == T0_ARM and row.sample_id == "s1")
    mislabeled = PKeyArmResult(
        arm=T0_ARM, sample_id="s1", messages=t0_s1.messages, response_text=t0_s1.response_text,
        metrics=t0_s1.metrics, consumption=t0_s1.consumption, silence_swapped=True,
    )
    results.append(mislabeled)
    bad_summary = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match=f"expected {SILENCE_SWAP_ARM!r}"):
        validate_pkey_flight_summary(bad_summary, expected_sample_ids=sample_ids, expected_silence_swap_sample_ids=["s1"])


# ---------------------------------------------------------------------------
# validate_pkey_flight_summary -- txt_duplicate sub-block (2026-08-19
# amendment item 4): fail-closed byte-identity fixtures.
# ---------------------------------------------------------------------------


def _duplicate_row_for(summary: PKeyFlightSummary, sample_id: str) -> PKeyArmResult:
    original = next(
        row for row in summary.results
        if row.arm == TXT_NOSUP_ARM and row.sample_id == sample_id and not row.txt_duplicate
    )
    return PKeyArmResult(
        arm=TXT_NOSUP_ARM, sample_id=sample_id, messages=original.messages, response_text=original.response_text,
        metrics=original.metrics, consumption=original.consumption,
        transcript_sha256_used=original.transcript_sha256_used, txt_duplicate=True,
    )


def test_validate_pkey_flight_summary_accepts_a_matching_txt_duplicate_row():
    summary, sample_ids = _valid_two_sample_summary()
    results = list(summary.results) + [_duplicate_row_for(summary, "s1")]
    extended = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    validate_pkey_flight_summary(
        extended, expected_sample_ids=sample_ids, expected_txt_duplicate_sample_ids=["s1"]
    )  # does not raise


def test_validate_pkey_flight_summary_refuses_a_txt_duplicate_row_that_diverges_from_its_pass3_original():
    """The FAIL-CLOSED byte-identity check (mission requirement, work item
    2): a resend that differs from its own pass-3 original must refuse."""

    summary, sample_ids = _valid_two_sample_summary()
    diverged = _duplicate_row_for(summary, "s1")
    diverged_messages = (
        diverged.messages[0],
        {"role": "user", "content": [{"type": "text", "text": "The user said: a totally different resend"}]},
    )
    diverged = PKeyArmResult(
        arm=diverged.arm, sample_id=diverged.sample_id, messages=diverged_messages,
        response_text=diverged.response_text, metrics=diverged.metrics, consumption=diverged.consumption,
        transcript_sha256_used=diverged.transcript_sha256_used, txt_duplicate=True,
    )
    results = list(summary.results) + [diverged]
    corrupted = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match="duplicate-block byte-identity violated"):
        validate_pkey_flight_summary(
            corrupted, expected_sample_ids=sample_ids, expected_txt_duplicate_sample_ids=["s1"]
        )


def test_validate_pkey_flight_summary_refuses_a_txt_duplicate_row_carrying_audio():
    summary, sample_ids = _valid_two_sample_summary()
    original = _duplicate_row_for(summary, "s1")
    leaked_messages = (
        original.messages[0],
        {"role": "user", "content": [
            {"type": "text", "text": original.messages[1]["content"][0]["text"]},
            {"type": "input_audio", "media_relpath": "s1.flac"},
        ]},
    )
    leaked = PKeyArmResult(
        arm=original.arm, sample_id=original.sample_id, messages=leaked_messages,
        response_text=original.response_text, metrics=original.metrics, consumption=original.consumption,
        transcript_sha256_used=original.transcript_sha256_used, txt_duplicate=True,
    )
    results = list(summary.results) + [leaked]
    corrupted = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match="duplicate-block byte-identity violated"):
        validate_pkey_flight_summary(
            corrupted, expected_sample_ids=sample_ids, expected_txt_duplicate_sample_ids=["s1"]
        )


def test_validate_pkey_flight_summary_txt_duplicate_must_be_on_txt_nosup_arm():
    summary, sample_ids = _valid_two_sample_summary()
    t0_s1 = next(row for row in summary.results if row.arm == T0_ARM and row.sample_id == "s1")
    mislabeled = PKeyArmResult(
        arm=T0_ARM, sample_id="s1", messages=t0_s1.messages, response_text=t0_s1.response_text,
        metrics=t0_s1.metrics, consumption=t0_s1.consumption, txt_duplicate=True,
    )
    results = list(summary.results) + [mislabeled]
    bad_summary = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    with pytest.raises(PKeyFlightError, match=f"expected {TXT_NOSUP_ARM!r}"):
        validate_pkey_flight_summary(
            bad_summary, expected_sample_ids=sample_ids, expected_txt_duplicate_sample_ids=["s1"]
        )


def test_validate_pkey_flight_summary_refuses_a_missing_txt_duplicate_row():
    summary, sample_ids = _valid_two_sample_summary()
    with pytest.raises(PKeyFlightError, match="does not match the expected"):
        validate_pkey_flight_summary(
            summary, expected_sample_ids=sample_ids, expected_txt_duplicate_sample_ids=["s1"]
        )  # named but never added


def test_validate_pkey_flight_summary_rejects_a_duplicate_expected_txt_duplicate_id():
    summary, sample_ids = _valid_two_sample_summary()
    with pytest.raises(PKeyFlightError, match="expected_txt_duplicate_sample_ids carries a duplicate"):
        validate_pkey_flight_summary(
            summary, expected_sample_ids=sample_ids, expected_txt_duplicate_sample_ids=["s1", "s1"]
        )


def test_validate_pkey_flight_summary_ordinary_txt_nosup_rows_stay_60_even_with_duplicates_present():
    """The duplicate bucket is kept SEPARATE from the ordinary per-sample
    TXT-NOSUP bucket -- a duplicate row must never be miscounted as a second
    (illegally duplicate) TXT-NOSUP row for the same sample id."""

    summary, sample_ids = _valid_two_sample_summary()
    results = list(summary.results) + [_duplicate_row_for(summary, "s1"), _duplicate_row_for(summary, "s2")]
    extended = PKeyFlightSummary(results=tuple(results), transcript_registry=summary.transcript_registry)
    validate_pkey_flight_summary(
        extended, expected_sample_ids=sample_ids, expected_txt_duplicate_sample_ids=["s1", "s2"]
    )  # does not raise -- ordinary TXT-NOSUP arm still has exactly 2 rows
